#!/usr/bin/env python3
"""GitHub inventory and activity for the ersilia-os organisation.

WHY: the Airtable repositories table is a snapshot of standing totals, and it was left
stale when the nightly job that maintained it stopped running. It listed `eos` as the
second most-starred repository with 92 stars and 190 forks while
`GET /repos/ersilia-os/eos` returned **404** — the repository did not exist, and nothing
noticed because nothing was checking. `check_github_airtable_sync.py` is now that check,
and `update_airtable_repositories.py` maintains the numbers.

GitHub also holds what Airtable structurally cannot: `pushed_at` (is this alive?),
`archived` (was it retired on purpose?), and a real commit series over time. A single
cell can hold "3,017 commits"; it cannot hold when they happened.

WHAT IT COLLECTS
    repos            the public inventory, one row each, with per-repository counts
    commit_activity  commits per calendar quarter, for every non-archived repository
    stars            starred_at for the most-starred repositories, i.e. star history

FOUR THINGS THAT MATTER

**Public repositories only.** This output is committed, and a private repository's *name*
is disclosure even when its numbers are not. `github_api.list_repos` takes the visibility as
a required argument so that this file can be seen to ask for "public"; the scripts that
legitimately need private repositories — the synchronisation check and the Airtable writer —
ask for "all" and write nothing to disk.

**The repositories are not all comparable.** Most are `eos####` per-model repositories and
the rest are not, split by `github_api.MODEL_RE`. Both kinds are collected throughout. An
earlier version skipped the model repositories for commit activity on the grounds that they
carried no signal; that was judged from their stars, and it was wrong — see the comment in
`main`.

**The REST statistics endpoints do not work here at all.** They answer 202 with an empty
body while GitHub computes, and for a repository with nothing to report they appear never to
populate: 20 of 20 stayed on 202 after a 40-second wait and two retries. `commit_activity`
uses GraphQL instead — see its docstring for the evidence.

**Some columns the list endpoint cannot give.** `subscribers_count` is absent from it, and
this file used to record 0 for every repository as a result; total commits is in no list
payload. Both now come from one batched GraphQL query at about 1 point per 40 repositories.

    export GH_STATS_TOKEN=...        # fine-grained, read-only, metadata on ersilia-os
    python3 scripts/fetch_github.py -o data/github/
    python3 scripts/fetch_github.py --check
"""
import argparse
import logging
import sys
import time
from datetime import datetime, timedelta, timezone

from collect_common import check_freshness, get_json, prune_superseded, write_snapshot
from github_api import (API, MODEL_RE, ORG, auth_headers, contributor_counts, list_repos,
                        post_graphql, repo_metrics)

REPO_FIELDS = ["name", "is_model", "created_at", "pushed_at", "archived", "fork",
               "language", "license", "topics", "size_kb", "stars", "forks",
               "watchers", "open_issues", "has_issues", "default_branch",
               # From the batched GraphQL query and the contributor endpoint.
               "total_commits", "closed_issues", "merged_prs", "releases",
               "latest_release", "prs_sampled", "prs_external",
               "median_days_to_close", "contributors"]
# `week_start` is now a quarter label ("2026Q2"); the column name is kept so the
# committed file's shape does not change.
ACTIVITY_FIELDS = ["name", "week_start", "commits"]
STAR_FIELDS = ["name", "starred_at"]


def inventory(org, headers):
    """The public inventory as CSV rows, from the REST list endpoint.

    The counts this endpoint cannot supply — subscribers, total commits, releases, closed
    issues, merged PRs — are filled in by `enrich`. Kept separate so a run without a token
    still produces the inventory.
    """
    rows = []
    for repo in list_repos(org, headers, visibility="public"):
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
            # Filled in by `enrich`. `subscribers_count` is absent from this payload and
            # `watchers_count` here is a stars alias, so neither can be used.
            "watchers": "",
            "open_issues": repo.get("open_issues_count") or 0,
            "has_issues": "yes" if repo.get("has_issues") else "no",
            "default_branch": repo.get("default_branch") or "",
        })
    rows.sort(key=lambda r: r["name"])
    return rows


def enrich(org, rows, headers, with_contributors=True):
    """Add the batched GraphQL counts, and optionally contributor counts, in place.

    `watchers` is the reason this exists. It is the real subscriber count from
    `watchers.totalCount`, and it agrees with the Airtable column on 140 of 141 public rows
    — where the old list-endpoint reading disagreed on 96 of them, because that endpoint does
    not return `subscribers_count` and the field was silently recorded as 0.
    """
    names = [r["name"] for r in rows]
    metrics = repo_metrics(org, names, headers)
    logging.info("metrics resolved for %d of %d repositories", len(metrics), len(names))

    counts = {}
    if with_contributors:
        counts = contributor_counts(org, names, headers)
        logging.info("contributor counts for %d of %d repositories", len(counts), len(names))

    for row in rows:
        found = metrics.get(row["name"]) or {}
        row["watchers"] = found.get("subscribers", "")
        # An empty repository has no default branch and so no commit count. Blank, never
        # 0 — "no commits recorded" and "not applicable" must not look the same.
        commits = found.get("total_commits")
        row["total_commits"] = "" if commits is None else commits
        for key in ("closed_issues", "merged_prs", "releases", "latest_release",
                    "prs_sampled", "prs_external", "median_days_to_close"):
            row[key] = found.get(key, "")
        row["contributors"] = counts.get(row["name"], "")
    return rows


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
    quarterly, and 52 weekly buckets across 343 repositories would be mostly zeros.
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
        # allow_missing: a repository deleted between the inventory and this call must not
        # take down the other 19 in the batch.
        data = post_graphql(query, headers, {"o": org}, allow_missing=True)

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

    def total(rows, key):
        return sum(int(r[key]) for r in rows if str(r.get(key) or "").strip().isdigit())

    logging.info("commits %s, releases %s, closed issues %s, merged PRs %s",
                 format(total(repos, "total_commits"), ","), format(total(repos, "releases"), ","),
                 format(total(repos, "closed_issues"), ","),
                 format(total(repos, "merged_prs"), ","))
    # The contribution signal, reported at collection time so a bad sample is visible
    # before anything is plotted from it.
    for label, rows in (("model", models), ("other", others)):
        sampled, external = total(rows, "prs_sampled"), total(rows, "prs_external")
        if sampled:
            logging.info("%s repositories: %d of %d recent merged PRs from outside the "
                         "organisation (%.0f%%)", label, external, sampled,
                         100.0 * external / sampled)
    return others


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("-o", "--out-dir", default="data/github")
    parser.add_argument("--org", default=ORG)
    parser.add_argument("--skip-activity", action="store_true",
                        help="Inventory and stars only. Useful without a token.")
    parser.add_argument("--skip-contributors", action="store_true",
                        help="Skip contributor counts: one REST request per repository, "
                             "which is by far the slowest part of a run.")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--max-age-days", type=int, default=21)
    args = parser.parse_args()

    if args.check:
        return check_freshness(args.out_dir, args.max_age_days, "github")

    headers = auth_headers()
    repos = inventory(args.org, headers)
    if not repos:
        logging.error("no repositories returned for %s — refusing to write", args.org)
        return 1
    enrich(args.org, repos, headers, with_contributors=not args.skip_contributors)
    summarise(repos)          # logs the inventory breakdown; return value unused

    written = [write_snapshot(args.out_dir, "repos", REPO_FIELDS, repos)]

    stars = star_history(args.org, repos, headers)
    if stars:
        written.append(write_snapshot(args.out_dir, "stars", STAR_FIELDS, stars))
        logging.info("star history: %d dated stars across %d repositories",
                     len(stars), len({r["name"] for r in stars}))

    if not args.skip_activity:
        # EVERY non-archived repository, model repositories included. This used to skip the
        # model repositories on the grounds that they "carry almost no signal", judged from
        # their stars — `eos4e40` has 2, `eos2gw4` has 0. That judgement was wrong: the
        # median model repository holds 49 commits and 78% of recently merged pull requests
        # on them come from outside the organisation. Nobody stars a model, they contribute
        # one, and excluding them made the quarterly series cover 7,349 of 23,428 commits
        # while the rest of the page quoted the larger figure.
        names = [r["name"] for r in repos if r["archived"] == "no"]
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
