#!/usr/bin/env python3
"""GitHub traffic — where visitors come from and what they look at, org-wide.

REQUIRES A DIFFERENT TOKEN FROM EVERY OTHER COLLECTOR HERE
------------------------------------------------------------
`fetch_github.py` reads public repository metadata, which needs nothing more than a
read-only token. GitHub's traffic endpoints (`/repos/{org}/{repo}/traffic/popular/...`)
require **push-access-equivalent permission**: a classic PAT with the `repo` scope, or a
fine-grained PAT with "Administration: Read-only" granted on the target repositories.
`GH_STATS_TOKEN` here is documented read-only metadata access — this will 403 against it
unless that token is reissued with the elevated scope. A per-repo 403 is treated as "no
data for this repo", not a fatal error, so a token missing that scope on some repos still
produces a partial, honest snapshot rather than an empty one.

WHY THIS APPENDS INSTEAD OF OVERWRITING, UNLIKE EVERY OTHER COLLECTOR HERE
----------------------------------------------------------------------------
GitHub's traffic API exposes only a rolling 14-day window and keeps no history at all —
run it today and last month's numbers are simply gone. Every other collector's fetch IS
the whole truth as of now; this one is a fragment, and the only way to build a real series
is to keep every fragment a run has ever seen. So this reads the most recent previous
snapshot (carried between CI runs in the Actions cache, see pages.yml), unions it with
today's fetch, dedupes on (repo, kind, source, the DATE fetched), and writes the union
back out as today's snapshot — the file grows across runs even
though each run's own view of GitHub is 14 days wide. Skipping a run for months loses
that gap's data forever; there is no way to backfill it later.

SCOPE IS THE WHOLE ORG, NOT JUST eos* MODEL REPOS
----------------------------------------------------
The flagship `ersilia` repository is where most inbound traffic lands, and an `eos*`
filter drops it entirely — the one repo this data would be least useful without.

    python3 scripts/fetch_github_traffic.py -o data/github/
    python3 scripts/fetch_github_traffic.py --check          # freshness gate for CI
"""
import argparse
import logging
import os
import sys
from datetime import datetime, timezone

import pandas as pd

from collect_common import (SNAPSHOT_RE, check_freshness, get_json,
                            prune_superseded, write_snapshot)
from github_api import API, ORG, auth_headers, list_repos

FIELDS = ["repo", "kind", "source", "title", "count", "uniques", "fetched_at"]


def _newest_traffic_snapshot(out_dir):
    """The most recent `traffic_sources_<date>.csv`, or ``None``.

    Scoped to this one dataset name, unlike `collect_common.newest_stamp`, which
    would return whichever file in `data/github/` happens to be newest — the wrong
    date when `repos`/`stars`/etc. were refreshed more recently than traffic.
    """
    if not os.path.isdir(out_dir):
        return None
    best = None
    for fname in os.listdir(out_dir):
        match = SNAPSHOT_RE.match(fname)
        if match and match.group("name") == "traffic_sources" \
                and (best is None or match.group("stamp") > best[0]):
            best = (match.group("stamp"), os.path.join(out_dir, fname))
    return best


def fetch_repo_traffic_sources(org, repo, headers, fetched_at):
    """Referring sites and most-visited paths for one repo, as long-format rows.

    Returns [] both for a repo nobody visited (GitHub answers 200 with an empty list)
    and for a repo the token cannot read (403) — the two are indistinguishable from the
    outside, and neither is a reason to stop the run.
    """
    rows = []
    for kind, endpoint, key in (("referrer", "referrers", "referrer"), ("path", "paths", "path")):
        try:
            items = get_json("%s/repos/%s/%s/traffic/popular/%s" % (API, org, repo, endpoint),
                             headers=headers)
        except RuntimeError as error:
            logging.warning("could not read %s traffic for %s: %s", kind, repo, error)
            continue
        for item in items or []:
            rows.append({
                "repo": repo,
                "kind": kind,
                "source": item.get(key),
                "title": (item.get("title") or "")[:200],
                "count": item.get("count") or 0,
                "uniques": item.get("uniques") or 0,
                "fetched_at": fetched_at,
            })
    return rows


def collect(org, headers, repos):
    fetched_at = datetime.now(timezone.utc).isoformat()
    rows = []
    for i, repo in enumerate(repos, start=1):
        rows.extend(fetch_repo_traffic_sources(org, repo, headers, fetched_at))
        if i % 25 == 0:
            logging.info("fetched traffic for %d/%d repos", i, len(repos))
    return rows


def merge_with_previous(out_dir, new_rows):
    """Union today's fetch with the most recent previous snapshot, deduped on
    (repo, kind, source, the DATE fetched) so re-running on the same day replaces
    that day's rows instead of double-counting them."""
    new_df = pd.DataFrame(new_rows, columns=FIELDS)
    existing = _newest_traffic_snapshot(out_dir)
    if existing:
        _stamp, path = existing
        if os.path.exists(path):
            old_df = pd.read_csv(path)
            new_df = pd.concat([old_df, new_df], ignore_index=True)

    fetched = pd.to_datetime(new_df["fetched_at"], utc=True, format="mixed", errors="coerce")
    new_df["fetch_date"] = fetched.dt.date.astype(str)
    new_df = new_df.drop_duplicates(subset=["repo", "kind", "source", "fetch_date"], keep="last")
    return new_df.drop(columns="fetch_date").sort_values(["fetched_at", "repo", "kind", "count"])


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("-o", "--out-dir", default="data/github")
    parser.add_argument("--org", default=ORG)
    parser.add_argument("--check", action="store_true",
                        help="Do not fetch; fail if the local snapshot is stale.")
    parser.add_argument("--max-age-days", type=int, default=14,
                        help="Traffic's own window is 14 days; a snapshot older than "
                        "that is not just stale, it has a real gap in it.")
    args = parser.parse_args()

    if args.check:
        return check_freshness(args.out_dir, args.max_age_days, "github-traffic")

    headers = auth_headers()
    if "Authorization" not in headers:
        logging.error("GH_STATS_TOKEN is not set. Traffic endpoints 403 unauthenticated "
                      "even for public repositories, unlike every other collector here.")
        return 1

    raw = list_repos(args.org, headers, visibility="public")
    repos = [r.get("name", "") for r in raw if r.get("name") and not r.get("archived")]
    if not repos:
        logging.error("no public repositories found for %s", args.org)
        return 1
    logging.info("fetching traffic for %d public repos", len(repos))

    new_rows = collect(args.org, headers, repos)
    if not new_rows:
        logging.error("no traffic data returned for any repo — check the token has "
                      "'Administration: Read-only' (fine-grained) or 'repo' scope (classic)")
        return 1

    combined = merge_with_previous(args.out_dir, new_rows)
    written = write_snapshot(args.out_dir, "traffic_sources", FIELDS,
                             combined.to_dict("records"))
    prune_superseded(args.out_dir, [written])
    windows = combined["fetched_at"].str[:10].nunique()
    logging.info("%d rows across %d fetched window(s)", len(combined), windows)
    return 0


if __name__ == "__main__":
    sys.exit(main())
