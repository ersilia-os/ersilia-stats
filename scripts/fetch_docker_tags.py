#!/usr/bin/env python3
"""Docker Hub tag/architecture history for the ersiliaos namespace.

WHY THIS IS SEPARATE FROM fetch_dockerhub.py
---------------------------------------------
`fetch_dockerhub.py` reads the repository-LIST endpoint: one row per image, with a
lifetime pull count that never goes down and says nothing about recency. This reads the
per-repository TAGS endpoint instead, one request per model, and gets three things a
lifetime count cannot:

  1. Per-ARCHITECTURE last-pulled time. Docker Hub attributes a pull to an image
     DIGEST, and amd64/arm64 are always separate digests inside a multi-arch tag, so
     "when was the arm64 build last asked for" is a real, separable demand signal.
  2. Per-architecture SIZE, so the arm64/amd64 weight gap is measurable per model
     rather than assumed from the single "latest" size fetch_dockerhub.py records.
  3. Every dated build tag, so a model's size history across rebuilds is recoverable
     (Ersilia tags each rebuild YYYY-MM-DD).

The honest unit of analysis is the DIGEST, not the tag name: `latest`, `dev` and the
newest dated tag usually point at the same digest and so report an identical
last-pulled time. Nothing downstream should read a tag NAME as evidence of who pulled
it — only architecture is safely separable, and even that is one recency-biased sample
per digest (Docker Hub exposes only the MOST RECENT pull per digest, never a series).

Images Docker Hub reports as architecture "unknown" are attestation/provenance blobs
(a few tens of kilobytes), not runnable images, and are dropped so they cannot skew a
size or architecture count.

    python3 scripts/fetch_docker_tags.py -o data/dockerhub/
    python3 scripts/fetch_docker_tags.py --check          # freshness gate for CI
"""
import argparse
import csv
import logging
import os
import re
import sys

from collect_common import (check_freshness, newest_stamp, paginate_url,
                            prune_superseded, write_snapshot)
from dockerhub_api import auth_headers

NAMESPACE = "ersiliaos"
IMAGES_DIR_DEFAULT = "data/dockerhub"
TAGS_API = "https://hub.docker.com/v2/namespaces/%s/repositories/%s/tags?page_size=100"

FIELDS = ["repo", "tag", "tag_kind", "architecture", "digest", "size_bytes",
         "pushed_at", "pulled_at"]

TAG_KIND_PATTERNS = [
    (re.compile(r"^v?\d+\.\d+\.\d+$"), "version"),
    (re.compile(r"^\d{4}-\d{2}-\d{2}$"), "dated"),
]


def classify_tag(tag_name):
    """Ersilia's image tagging convention, as it appears on Docker Hub.

    'rolling' - `latest`, what `ersilia fetch` resolves to.
    'dev'     - `dev`, `dev-amd64`, `dev-arm64`: CI build artefacts.
    'version' - `v1.0.0`: pinned to a GitHub Release.
    'dated'   - `2025-11-24`: a build snapshot, one per rebuild.
    'other'   - anything else.
    """
    name = (tag_name or "").strip().lower()
    if name == "latest":
        return "rolling"
    if name == "dev" or name.startswith("dev-"):
        return "dev"
    for pattern, kind in TAG_KIND_PATTERNS:
        if pattern.match(name):
            return kind
    return "other"


def model_repo_names(images_dir):
    """Model repo names from the images_<date>.csv fetch_dockerhub.py wrote, so this collector needs
    no repo-list call of its own — one request per model instead of one plus a list."""
    stamp = newest_stamp(images_dir)
    if not stamp:
        return []
    path = os.path.join(images_dir, "images_%s.csv" % stamp)
    names = []
    with open(path, newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if row.get("is_model") == "yes":
                names.append(row["name"])
    return names


def fetch_repo_tags(namespace, repo, headers):
    tags = []
    for page in paginate_url(TAGS_API % (namespace, repo), headers=headers):
        tags.extend(page.get("results", []))
    return tags


def collect(namespace, repos, headers):
    rows = []
    skipped = 0
    for i, repo in enumerate(repos, start=1):
        try:
            tags = fetch_repo_tags(namespace, repo, headers)
        except RuntimeError as error:
            logging.warning("giving up on %s: %s", repo, error)
            skipped += 1
            continue
        for tag in tags:
            tag_name = tag.get("name")
            tag_kind = classify_tag(tag_name)
            for image in tag.get("images") or []:
                architecture = image.get("architecture")
                if architecture in (None, "unknown"):
                    continue
                pushed = image.get("last_pushed") or tag.get("tag_last_pushed") or ""
                pulled = image.get("last_pulled") or tag.get("tag_last_pulled") or ""
                rows.append({
                    "repo": repo,
                    "tag": tag_name,
                    "tag_kind": tag_kind,
                    "architecture": architecture,
                    "digest": image.get("digest"),
                    "size_bytes": image.get("size") or 0,
                    "pushed_at": pushed[:19],
                    "pulled_at": pulled[:19],
                })
        if i % 25 == 0:
            logging.info("fetched tags for %d/%d repos", i, len(repos))
    if skipped:
        logging.warning("%d of %d repos could not be fetched and are absent from this "
                        "snapshot, not zeroed", skipped, len(repos))
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("-o", "--out-dir", default=IMAGES_DIR_DEFAULT)
    parser.add_argument("-n", "--namespace", default=NAMESPACE)
    parser.add_argument("--check", action="store_true",
                        help="Do not fetch; fail if the local snapshot is stale.")
    parser.add_argument("--max-age-days", type=int, default=21)
    args = parser.parse_args()

    if args.check:
        return check_freshness(args.out_dir, args.max_age_days, "dockerhub-tags")

    repos = model_repo_names(args.out_dir)
    if not repos:
        logging.error("no model repos found in %s — run fetch_dockerhub.py first", args.out_dir)
        return 1
    logging.info("fetching tags for %d model repos", len(repos))

    rows = collect(args.namespace, repos, auth_headers())
    if not rows:
        logging.error("no tags returned for any repo — refusing to write an empty snapshot")
        return 1
    rows.sort(key=lambda r: (r["repo"], r["tag"] or "", r["architecture"]))
    written = write_snapshot(args.out_dir, "tags", FIELDS, rows)
    prune_superseded(args.out_dir, [written])
    return 0


if __name__ == "__main__":
    sys.exit(main())
