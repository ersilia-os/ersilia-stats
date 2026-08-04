"""Shared GitHub access: the inventory, the batched metrics query, contributor counts.

WHY THIS IS A MODULE AND NOT PART OF `fetch_github.py`
------------------------------------------------------
Three callers need the same GitHub reads, and they need them with *different* visibility:

* `fetch_github.py`         public repositories only, because its output is committed
* `check_github_airtable_sync.py`  all repositories, to avoid false alarms on private ones
* `update_airtable_repositories.py`  all repositories, because 38 Airtable rows are private

Keeping one implementation means the three cannot drift into disagreeing about what a
"model repository" is or how a subscriber is counted — which is the whole point of a
synchronisation check.

TWO RULES THIS MODULE ENFORCES, not merely follows
--------------------------------------------------
**No personal data is ever returned.** `repo_metrics` reads pull-request author
*associations* and returns counts by association; it never returns a login. The stargazer
and contributor endpoints both carry logins, and both are reduced to a number here so a
caller cannot accidentally write one to disk.

**`list_repos` makes visibility explicit.** There is no default. A caller that writes a
committed file must pass `visibility="public"` and be seen to do it, because a private
repository's *name* is a disclosure even when its numbers are not.

WHAT A METRICS BATCH COSTS
--------------------------
Measured, not estimated: one GraphQL request covering 40 repositories with counts on six
connections costs **1 point** of a 5,000/hour budget. All 424 repositories in the
organisation therefore cost about 11 points. The REST contributor count is the expensive
one at one request per repository, and it is optional for that reason.
"""
import logging
import os
import re
import statistics
import urllib.error
import urllib.request
from datetime import datetime

from collect_common import get_json

ORG = "ersilia-os"
API = "https://api.github.com"
GRAPHQL = "https://api.github.com/graphql"

# A per-model repository: `eos`, a digit, then three alphanumerics.
#
# TIGHTER THAN IT LOOKS, AND DELIBERATELY. The loose form `^eos[0-9a-z]{4}$` agrees with
# this one on every repository that exists today, but **10 repositories begin with `eos`
# and are not models** — `eos-template`, `eosbench`, `eosdev`, `eos-demo`,
# `eos-analysis-template`, `eos-lite-chem`, `eos-python-package`, `eosframes`,
# `eosquality`, `eosvc`. All 243 identifiers in the Airtable `models` table match the
# strict form, and none of those 10 do.
MODEL_RE = re.compile(r"^eos[0-9][0-9a-z]{3}$")

# GitHub's own vocabulary for "is this person part of the organisation?". Splitting it
# here rather than at each call site means the site cannot end up with two different
# definitions of an external contributor.
INTERNAL_ASSOCIATIONS = {"OWNER", "MEMBER", "COLLABORATOR"}

# A repository name that is safe to interpolate into a GraphQL string literal. GitHub
# allows only these characters, so anything else means the caller built a name rather
# than reading one from the API.
SAFE_NAME_RE = re.compile(r"^[A-Za-z0-9._-]+$")


def auth_headers(require=False):
    """Standard GitHub headers, with the token when one is set.

    `require=True` for callers that cannot do anything useful unauthenticated — the
    synchronisation check needs to see private repositories, and silently checking only
    the public ones would report drift that is not there.
    """
    token = os.environ.get("GH_STATS_TOKEN") or os.environ.get("GITHUB_TOKEN")
    headers = {"Accept": "application/vnd.github+json",
               "X-GitHub-Api-Version": "2022-11-28"}
    if token:
        headers["Authorization"] = "Bearer " + token
    elif require:
        raise RuntimeError(
            "GH_STATS_TOKEN is not set. This needs a token with read access to "
            "repository metadata on the organisation, including private repositories.")
    else:
        logging.warning("no GH_STATS_TOKEN set — unauthenticated, 60 requests/hour")
    return headers


def list_repos(org, headers, visibility):
    """Every repository of the given `visibility`, as raw API payloads.

    `visibility` is required and must be "public" or "all". There is no default: the
    difference decides whether private repository names enter the process, and that is
    not a decision to make by omission.
    """
    if visibility not in ("public", "all"):
        raise ValueError('visibility must be "public" or "all", not %r' % (visibility,))
    payloads, page = [], 1
    while True:
        batch = get_json("%s/orgs/%s/repos?type=%s&per_page=100&page=%d"
                         % (API, org, visibility, page), headers=headers)
        if not batch:
            break
        payloads.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    payloads.sort(key=lambda r: (r.get("name") or ""))
    return payloads


def post_graphql(query, headers, variables=None, allow_missing=False):
    """One GraphQL POST. The only non-GET request in any collector, and it is a read.

    `allow_missing` matters more than it looks. A batched query naming 20 repositories
    gets a **top-level error** for each one that cannot be resolved, alongside perfectly
    good data for the other 19. Raising on that would mean a single deleted repository —
    `eos`, right now — takes down the whole batch, and the synchronisation check whose job
    is to *report* deleted repositories would be the first thing to break.

    So with `allow_missing` a `NOT_FOUND` error is data: the alias is absent from the
    result and the caller sees the gap. Any other error still raises, because a bad field
    or a revoked token must not be mistaken for a missing repository.
    """
    import json as _json
    payload = _json.dumps({"query": query, "variables": variables or {}}).encode()
    request = urllib.request.Request(GRAPHQL, data=payload, headers={
        **headers, "Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=90) as response:
        body = _json.loads(response.read())
    errors = body.get("errors") or []
    if errors:
        unresolved = [e for e in errors if (e.get("type") or "") == "NOT_FOUND"]
        if not (allow_missing and len(unresolved) == len(errors)):
            raise RuntimeError("GraphQL: %s" % errors[0].get("message"))
    return body.get("data") or {}


_METRICS_FRAGMENT = """
  r%(i)d: repository(owner: $o, name: "%(name)s") {
    isPrivate
    stargazerCount
    forkCount
    subscribers: watchers { totalCount }
    openIssues: issues(states: OPEN) { totalCount }
    closedIssues: issues(states: CLOSED) { totalCount }
    mergedPRs: pullRequests(states: MERGED) { totalCount }
    releases { totalCount }
    latestRelease { publishedAt }
    prSample: pullRequests(states: MERGED, last: %(sample)d) {
      nodes { authorAssociation }
    }
    issueSample: issues(states: CLOSED, last: %(sample)d) {
      nodes { createdAt closedAt }
    }
    defaultBranchRef { target { ... on Commit { history { totalCount } } } }
  }
"""


def repo_metrics(org, names, headers, batch=20, sample=30, progress=True):
    """Per-repository counts that the REST list endpoint does not carry.

    Returns `{name: {...}}`. A repository that GraphQL cannot resolve — deleted, renamed,
    or outside the token's scope — is simply absent from the result, which is what lets
    the synchronisation check tell "missing" from "zero".

    WHY THIS EXISTS AT ALL, given the REST inventory already runs:

    * `subscribers_count` is **absent from the list endpoint**. `fetch_github.py` used to
      record 0 for every repository because of it, and that column disagreed with Airtable
      on 96 of 141 rows purely as an artefact.
    * total commits is not in any list payload, and it is the number that drifts fastest —
      3 of 25 sampled repositories were already behind in the hand-maintained table.

    NO LOGINS ARE RETURNED. `prSample` reads `authorAssociation` and is reduced to two
    integers here; the nodes never leave this function.
    """
    out = {}
    for offset in range(0, len(names), batch):
        chunk = [n for n in names[offset:offset + batch] if SAFE_NAME_RE.match(n)]
        if not chunk:
            continue
        parts = [_METRICS_FRAGMENT % {"i": i, "name": name, "sample": sample}
                 for i, name in enumerate(chunk)]
        query = "query($o: String!) { %s rateLimit { cost remaining } }" % "".join(parts)
        data = post_graphql(query, headers, {"o": org}, allow_missing=True)

        for index, name in enumerate(chunk):
            repo = data.get("r%d" % index)
            if not repo:
                continue
            out[name] = _flatten_metrics(repo)
        if progress:
            logging.info("  metrics: %d/%d repositories",
                         min(offset + batch, len(names)), len(names))
    return out


def _flatten_metrics(repo):
    """One GraphQL repository payload reduced to plain numbers."""
    internal = external = 0
    for node in ((repo.get("prSample") or {}).get("nodes") or []):
        if (node or {}).get("authorAssociation") in INTERNAL_ASSOCIATIONS:
            internal += 1
        else:
            external += 1

    spans = []
    for node in ((repo.get("issueSample") or {}).get("nodes") or []):
        opened, closed = (node or {}).get("createdAt"), (node or {}).get("closedAt")
        if not opened or not closed:
            continue
        try:
            start = datetime.fromisoformat(opened.replace("Z", "+00:00"))
            end = datetime.fromisoformat(closed.replace("Z", "+00:00"))
        except ValueError:
            continue
        spans.append(max(0, (end - start).days))

    branch = repo.get("defaultBranchRef") or {}
    target = branch.get("target") or {}
    history = target.get("history") or {}
    latest = repo.get("latestRelease") or {}

    return {
        "private": bool(repo.get("isPrivate")),
        "stars": repo.get("stargazerCount") or 0,
        "forks": repo.get("forkCount") or 0,
        "subscribers": (repo.get("subscribers") or {}).get("totalCount") or 0,
        "open_issues": (repo.get("openIssues") or {}).get("totalCount") or 0,
        "closed_issues": (repo.get("closedIssues") or {}).get("totalCount") or 0,
        "merged_prs": (repo.get("mergedPRs") or {}).get("totalCount") or 0,
        "releases": (repo.get("releases") or {}).get("totalCount") or 0,
        "latest_release": (latest.get("publishedAt") or "")[:10],
        # An empty repository has no default branch, so no commit count exists. None
        # rather than 0, so a caller never writes "0 commits" for "not applicable".
        "total_commits": history.get("totalCount"),
        "prs_sampled": internal + external,
        "prs_external": external,
        "median_days_to_close": int(statistics.median(spans)) if spans else "",
    }


def contributor_counts(org, names, headers, progress=True):
    """`{name: count}` of contributors, including anonymous ones.

    ONE REQUEST PER REPOSITORY, which makes this the most expensive thing here — hence a
    separate function the caller opts into rather than part of `repo_metrics`.

    The response body carries contributor **logins**, which are personal data. This asks
    for `per_page=1` and takes the count from the `Link` header's last page, so for any
    repository with more than one contributor the body is never parsed at all. Verified
    against the hand-maintained Airtable column: 12 of 12 exact.
    """
    out = {}
    for position, name in enumerate(names, start=1):
        if not SAFE_NAME_RE.match(name):
            continue
        url = ("%s/repos/%s/%s/contributors?per_page=1&anon=1" % (API, org, name))
        try:
            count = _contributor_count(url, headers)
        except Exception as error:               # noqa: BLE001 - one repo must not stop the run
            logging.warning("  contributors: %s failed (%s)", name, error)
            continue
        if count is not None:
            out[name] = count
        if progress and position % 50 == 0:
            logging.info("  contributors: %d/%d repositories", position, len(names))
    return out


def _contributor_count(url, headers):
    request = urllib.request.Request(url, headers={
        "User-Agent": "ersilia-stats-collector (+https://github.com/ersilia-os/ersilia-stats)",
        **headers})
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            link = response.headers.get("Link") or ""
            body = response.read()
    except urllib.error.HTTPError as error:
        if error.code == 404:
            return None
        # 204 No Content: a repository with no commits at all.
        if error.code == 204:
            return 0
        raise
    match = re.search(r'[?&]page=(\d+)>;\s*rel="last"', link)
    if match:
        return int(match.group(1))
    # No `last` link means one page. Only here is the body read, and only its length.
    import json as _json
    try:
        return len(_json.loads(body) or [])
    except ValueError:
        return 0
