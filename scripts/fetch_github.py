#!/usr/bin/env python3
"""GitHub inventory and activity for the ersilia-os organisation.

WHY: the Airtable repositories table is a hand-maintained snapshot, and a hand-maintained
snapshot decays. The site currently lists `eos` as its second most-starred repository with
92 stars and 190 forks; `GET /repos/ersilia-os/eos` returns **404**. It does not exist.
Nothing noticed, because nothing was checking.

GitHub also holds three things Airtable structurally cannot: `pushed_at` (is this alive?),
`archived` (was it retired on purpose?), and a real weekly commit series. Today the site
reports one number — total commits — for all time.

WHAT IT COLLECTS
    repos            the public inventory: 382 repositories, one row each
    commit_activity  52 weekly commit totals per repository
    stars            starred_at for the most-starred repositories, i.e. star history

THREE THINGS THAT MATTER

**Public repositories only.** This output is committed, and a private repository's *name*
is disclosure even when its numbers are not. Airtable keeps supplying the private count.

**The 382 are not all comparable.** 239 are `eos####` per-model repositories and 143 are
not. Airtable curates the 143 (139 of its 140 match), which is a deliberate choice and not
an omission — so this does not "fix" anything by importing the model repos. Commit activity
is collected for the non-model repositories only, because the model repos carry almost no
signal: `eos4e40` has 2 stars, `eos2gw4` has 0.

**The statistics endpoints answer 202 with an empty body** the first time they are asked,
while GitHub computes them, and return data on a later call. Treating that as "no commits"
would report zero activity for every repository. Verified both halves: `{}` first, then 52
weeks on retry.

    export GH_STATS_TOKEN=...        # fine-grained, read-only, metadata on ersilia-os
    python3 scripts/fetch_github.py -o data/github/
    python3 scripts/fetch_github.py --check
"""
import argparse
import logging
import os
import re
import sys
import time
import urllib.request
from datetime import datetime, timedelta, timezone

from collect_common import (CONTACT, check_freshness, get_json, prune_superseded,
                            write_snapshot)

ORG = "ersilia-os"
API = "https://api.github.com"

# A per-model repository: `eos` plus four alphanumerics.
MODEL_RE = re.compile(r"^eos[0-9a-z]{4}$")

REPO_FIELDS = ["name", "is_model", "created_at", "pushed_at", "archived", "fork",
               "language", "license", "topics", "size_kb", "stars", "forks",
               "watchers", "open_issues", "has_issues", "default_branch"]
# `week_start` is now a quarter label ("2026Q2"); the column name is kept so the
# committed file's shape does not change.
ACTIVITY_FIELDS = ["name", "week_start", "commits"]
STAR_FIELDS = ["name", "starred_at"]


def auth_headers():
    token = os.environ.get("GH_STATS_TOKEN") or os.environ.get("GITHUB_TOKEN")
    headers = {"Accept": "application/vnd.github+json",
               "X-GitHub-Api-Version": "2022-11-28"}
    if token:
        headers["Authorization"] = "Bearer " + token
    else:
        # 60 requests/hour unauthenticated is enough for the inventory alone, and not
        # enough for commit activity across 143 repositories.
        logging.warning("no GH_STATS_TOKEN set — unauthenticated, 60 requests/hour")
    return headers


def list_public_repos(org, headers):
    """Every public repository, one page of 100 at a time."""
    rows, page = [], 1
    while True:
        payload = get_json("%s/orgs/%s/repos?type=public&per_page=100&page=%d"
                           % (API, org, page), headers=headers)
        if not payload:
            break
        for repo in payload:
            name = repo.get("name") or ""
            rows.append({
                "name": name,
                "is_model": "yes" if MODEL_RE.match(name) else "no",
                "created_at": (repo.get("created_at") or "")[:10],
                "pushed_at": (repo.get("pushed_at") or "")[:10],
                "archived": "yes" if repo.get("archived") else "no",
                "fork": "yes" if repo.get("fork") else "no",
                "language": repo.get("language") or "",
                # SPDX from GitHub is authoritative, unlike the hand-entered column.
                "license": ((repo.get("license") or {}) or {}).get("spdx_id") or "",
                "topics": " ".join(repo.get("topics") or []),
                "size_kb": repo.get("size") or 0,
                "stars": repo.get("stargazers_count") or 0,
                "forks": repo.get("forks_count") or 0,
                # `subscribers_count` is absent from the list endpoint; watchers_count
                # in this payload is a stars alias, so neither is trustworthy here and
                # the real value would cost one request per repository. Left at 0.
                "watchers": repo.get("subscribers_count") or 0,
                "open_issues": repo.get("open_issues_count") or 0,
                "has_issues": "yes" if repo.get("has_issues") else "no",
                "default_branch": repo.get("default_branch") or "",
            })
        if len(payload) < 100:
            break
        page += 1
    rows.sort(key=lambda r: r["name"])
    return rows


GRAPHQL = "https://api.github.com/graphql"


def post_graphql(query, headers, variables=None):
    """One GraphQL POST. The only non-GET request in any collector, and it is a read."""
    import json as _json
    payload = _json.dumps({"query": query, "variables": variables or {}}).encode()
    request = urllib.request.Request(GRAPHQL, data=payload, headers={
        **headers, "Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=60) as response:
        body = _json.loads(response.read())
    if body.get("errors"):
        raise RuntimeError("GraphQL: %s" % body["errors"][0].get("message"))
    return body.get("data") or {}


def quarter_windows(quarters):
    """`[(label, since_iso, until_iso)]`, most recent first, aligned to calendar quarters.

    The FIRST window is the current quarter, partial. Excluding it would leave the most
    recent activity off the chart, and every other time series on this site shows its
    current quarter partial too.
    """
    now = datetime.now(timezone.utc)
    edge = now
    windows = []
    for _ in range(quarters):
        quarter_start = datetime(edge.year, ((edge.month - 1) // 3) * 3 + 1, 1,
                                 tzinfo=timezone.utc)
        windows.append(("%dQ%d" % (quarter_start.year, (quarter_start.month - 1) // 3 + 1),
                        quarter_start.isoformat().replace("+00:00", "Z"),
                        edge.isoformat().replace("+00:00", "Z")))
        edge = quarter_start - timedelta(seconds=1)
    return windows


def commit_activity(org, names, headers, quarters=12, batch=20):
    """Commits per calendar quarter per repository, via GraphQL.

    THIS USED TO USE THE REST `stats/commit_activity` ENDPOINT AND IT DID NOT WORK.
    That endpoint computes on demand and answers 202 with an empty body until the cache is
    warm — so the obvious fix was to warm it and wait. It was not the answer: 20 of 20
    repositories returned 202 after a 40-second wait and two retries, and the one
    repository that ever produced data was the one whose cache had been warmed by hand.

    GraphQL showed why. `ersilia` has 60 commits since May and 42 the quarter before;
    `ersilia-app` and `3d-analogues` have **0 and 0**. The repositories stuck on 202 are the
    ones with nothing to report, and GitHub appears never to populate a cache for those. So
    "still computing" was mostly "nothing to compute", and no amount of waiting would have
    fixed it.

    `history(since:, until:) { totalCount }` is exact, needs no precomputation, and costs
    almost nothing: 3 repositories over 2 windows cost **1 point** of a 5,000/hour budget,
    so all 143 repositories over 12 quarters fit in a handful of requests.

    Quarterly rather than weekly on purpose — every other time series on this site is
    quarterly, and 52 weekly buckets across 143 repositories is mostly zeros.
    """
    windows = quarter_windows(quarters)
    rows, missing = [], []

    for offset in range(0, len(names), batch):
        chunk = names[offset:offset + batch]
        parts = []
        for index, name in enumerate(chunk):
            fields = " ".join(
                'w%d: history(since: "%s", until: "%s") { totalCount }' % (w, since, until)
                for w, (_label, since, until) in enumerate(windows))
            parts.append(
                'r%d: repository(owner: $o, name: "%s") { '
                'defaultBranchRef { target { ... on Commit { %s } } } }' % (index, name, fields))
        query = "query($o: String!) { %s rateLimit { cost remaining } }" % " ".join(parts)
        data = post_graphql(query, headers, {"o": org})

        for index, name in enumerate(chunk):
            repo = data.get("r%d" % index) or {}
            branch = (repo.get("defaultBranchRef") or {})
            target = branch.get("target") or {}
            if not target:
                missing.append(name)          # empty repository, or no default branch
                continue
            for w, (label, _since, _until) in enumerate(windows):
                total = (target.get("w%d" % w) or {}).get("totalCount") or 0
                if total:
                    rows.append({"name": name, "week_start": label, "commits": total})
        logging.info("  commits: %d/%d repositories", min(offset + batch, len(names)), len(names))

    rows.sort(key=lambda r: (r["name"], r["week_start"]))
    return rows, missing


def star_history(org, repos, headers, top=20):
    """`starred_at` per star, for the most-starred repositories.

    This is why a star *curve* needs no accumulated history: GitHub records when each
    star was given. Restricted to the top repositories because everything else has too
    few stars for a curve to mean anything.
    """
    ranked = sorted((r for r in repos if r["stars"] > 5),
                    key=lambda r: -r["stars"])[:top]
    rows = []
    for repo in ranked:
        page = 1
        while page <= 12:                          # 1,200 stars is plenty of headroom
            payload = get_json(
                "%s/repos/%s/%s/stargazers?per_page=100&page=%d" % (API, org, repo["name"], page),
                headers={**headers, "Accept": "application/vnd.github.star+json"})
            if not payload:
                break
            for entry in payload:
                when = entry.get("starred_at") if isinstance(entry, dict) else None
                if when:
                    # The stargazer's login is deliberately NOT recorded: the date is
                    # what makes a curve, and the identity would be personal data.
                    rows.append({"name": repo["name"], "starred_at": when[:10]})
            if len(payload) < 100:
                break
            page += 1
    rows.sort(key=lambda r: (r["name"], r["starred_at"]))
    return rows


def summarise(repos):
    models = [r for r in repos if r["is_model"] == "yes"]
    others = [r for r in repos if r["is_model"] == "no"]
    archived = [r for r in repos if r["archived"] == "yes"]
    today = time.time()
    def dormant(row):
        if row["archived"] == "yes" or not row["pushed_at"]:
            return False
        pushed = time.mktime(time.strptime(row["pushed_at"], "%Y-%m-%d"))
        return (today - pushed) / 86400 > 180
    logging.info("%d public repositories: %d model, %d other",
                 len(repos), len(models), len(others))
    logging.info("%d archived, %d dormant (no push in 180 days), %d active",
                 len(archived), sum(1 for r in repos if dormant(r)),
                 len(repos) - len(archived) - sum(1 for r in repos if dormant(r)))
    return others


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("-o", "--out-dir", default="data/github")
    parser.add_argument("--org", default=ORG)
    parser.add_argument("--skip-activity", action="store_true",
                        help="Inventory and stars only. Useful without a token.")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--max-age-days", type=int, default=21)
    args = parser.parse_args()

    if args.check:
        return check_freshness(args.out_dir, args.max_age_days, "github")

    headers = auth_headers()
    repos = list_public_repos(args.org, headers)
    if not repos:
        logging.error("no repositories returned for %s — refusing to write", args.org)
        return 1
    non_model = summarise(repos)

    written = [write_snapshot(args.out_dir, "repos", REPO_FIELDS, repos)]

    stars = star_history(args.org, repos, headers)
    if stars:
        written.append(write_snapshot(args.out_dir, "stars", STAR_FIELDS, stars))
        logging.info("star history: %d dated stars across %d repositories",
                     len(stars), len({r["name"] for r in stars}))

    if not args.skip_activity:
        names = [r["name"] for r in non_model if r["archived"] == "no"]
        activity, missed = commit_activity(args.org, names, headers)
        if activity:
            written.append(write_snapshot(args.out_dir, "commit_activity",
                                          ACTIVITY_FIELDS, activity))
            logging.info("commit activity: %d non-empty quarters across %d repositories",
                         len(activity), len({r["name"] for r in activity}))
        if missed:
            logging.info("%d repositories have no default branch (empty): %s",
                         len(missed), ", ".join(missed[:6]))

    prune_superseded(args.out_dir, written)
    return 0


if __name__ == "__main__":
    sys.exit(main())
