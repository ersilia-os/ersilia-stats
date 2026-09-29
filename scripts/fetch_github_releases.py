#!/usr/bin/env python3
"""Every GitHub Release for each model repo — full version history.

WHY THIS IS SEPARATE FROM fetch_github.py
------------------------------------------
`fetch_github.py`'s `repos` snapshot carries only the LATEST release per repo
(`latest_release`), which answers "what version is it on" but not "how did it get
there". Model repos get a new Release each time a maintainer re-packages or updates
them, so the full history — every tag, in order, with the semver bump between each
one and the last — is what lets the site show whether a model is a file drop (one
release, ever) or something actively maintained past its first v1.0.0.

    python3 scripts/fetch_github_releases.py -o data/github/
    python3 scripts/fetch_github_releases.py --check          # freshness gate for CI
"""
import argparse
import logging
import re
import sys

from collect_common import check_freshness, get_json, prune_superseded, write_snapshot
from github_api import API, MODEL_RE, ORG, auth_headers, list_repos

FIELDS = ["repo", "release_index", "tag_name", "release_name", "published_at",
         "is_prerelease", "major", "minor", "patch", "bump_type"]

SEMVER_RE = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)")


def parse_semver(tag):
    if not tag:
        return None
    match = SEMVER_RE.match(tag.strip())
    return tuple(int(g) for g in match.groups()) if match else None


def classify_bump(prev, curr):
    """Which part changed vs. the previous release, by semver precedence. ``None``
    when either side has no parseable version; ``"other"`` for a same-version re-tag
    or a non-monotonic (downgrade) one."""
    if prev is None or curr is None:
        return None
    if curr[0] != prev[0]:
        return "major"
    if curr[1] != prev[1]:
        return "minor"
    if curr[2] != prev[2]:
        return "patch"
    return "other"


def fetch_repo_releases(org, repo, headers):
    releases = []
    page = 1
    while page <= 20:  # 2,000 releases is far more headroom than any model needs
        batch = get_json("%s/repos/%s/%s/releases?per_page=100&page=%d" % (API, org, repo, page),
                         headers=headers)
        if not batch:
            break
        releases.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    releases.sort(key=lambda r: r.get("published_at") or r.get("created_at") or "")
    return releases


def collect(org, repos, headers):
    rows = []
    skipped = 0
    for i, repo in enumerate(repos, start=1):
        try:
            releases = fetch_repo_releases(org, repo, headers)
        except RuntimeError as error:
            logging.warning("could not fetch releases for %s: %s", repo, error)
            skipped += 1
            continue
        prev_version = None
        for index, rel in enumerate(releases, start=1):
            tag = rel.get("tag_name")
            version = parse_semver(tag)
            bump = "initial" if index == 1 else (classify_bump(prev_version, version) or "")
            rows.append({
                "repo": repo,
                "release_index": index,
                "tag_name": tag or "",
                "release_name": rel.get("name") or "",
                "published_at": (rel.get("published_at") or rel.get("created_at") or "")[:19],
                "is_prerelease": "yes" if rel.get("prerelease") else "no",
                "major": version[0] if version else "",
                "minor": version[1] if version else "",
                "patch": version[2] if version else "",
                "bump_type": bump,
            })
            if version:
                prev_version = version
        if i % 25 == 0:
            logging.info("fetched releases for %d/%d repos", i, len(repos))
    if skipped:
        logging.warning("%d of %d repos could not be fetched and are absent from this "
                        "snapshot, not zeroed", skipped, len(repos))
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("-o", "--out-dir", default="data/github")
    parser.add_argument("--org", default=ORG)
    parser.add_argument("--check", action="store_true",
                        help="Do not fetch; fail if the local snapshot is stale.")
    parser.add_argument("--max-age-days", type=int, default=21)
    args = parser.parse_args()

    if args.check:
        return check_freshness(args.out_dir, args.max_age_days, "github-releases")

    headers = auth_headers()
    raw = list_repos(args.org, headers, visibility="public")
    repos = [r.get("name", "") for r in raw if MODEL_RE.match(r.get("name") or "")]
    if not repos:
        logging.error("no model repos found for %s", args.org)
        return 1
    logging.info("fetching release history for %d model repos", len(repos))

    rows = collect(args.org, repos, headers)
    if not rows:
        logging.error("no releases returned for any repo — refusing to write an empty snapshot")
        return 1
    written = write_snapshot(args.out_dir, "releases", FIELDS, rows)
    prune_superseded(args.out_dir, [written])
    return 0


if __name__ == "__main__":
    sys.exit(main())
