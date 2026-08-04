#!/usr/bin/env python3
"""Docker Hub pull counts for the ersiliaos namespace.

WHY THIS IS THE MOST VALUABLE COLLECTOR
---------------------------------------
The dashboard describes 240 models in fifteen different ways and never once says whether
anyone runs them. Docker Hub answers that, because the models ARE Docker images, and it
answers it in **three requests with no authentication**: 245 model images and roughly a
million pulls between them.

Two things this must get right.

**Infrastructure images are not models.** The namespace also holds `base`, `conda`,
`shell` and similar — 24 images with 143,302 pulls between them, including 31,665 for
`base` alone. Counting those as model pulls would inflate the headline by about 14% with
images nobody chose to run for their own sake. They are kept in the CSV, flagged, and
excluded from the model figure.

**`pull_count` is a running total with no history.** Docker Hub exposes no per-day
series, so this can only ever report "pulls to date". The site must say so rather than
imply a rate. (Dated snapshots leave the door open: if a history is ever wanted, it is an
append instead of an overwrite.)

    python3 scripts/fetch_dockerhub.py -o data/dockerhub/
    python3 scripts/fetch_dockerhub.py --check          # freshness gate for CI
"""
import argparse
import logging
import sys

from collect_common import (check_freshness, paginate_url, prune_superseded,
                            write_snapshot)
from github_api import MODEL_RE

NAMESPACE = "ersiliaos"
API = "https://hub.docker.com/v2/repositories/%s/?page_size=100"

# Imported rather than redefined. This file used to carry its own looser copy,
# `^eos[0-9a-z]{4}$`, which meant the Docker collector and the GitHub collector could
# disagree about what counts as a model. They agree on every name that exists today, so
# nothing was ever misclassified — but two definitions of the same thing is a bug waiting
# for the first repository called `eosbench` to be pushed as an image.

FIELDS = ["name", "is_model", "pull_count", "star_count", "last_updated", "description"]


def collect(namespace=NAMESPACE):
    rows = []
    for page in paginate_url(API % namespace):
        for repo in page.get("results", []):
            name = (repo.get("name") or "").strip()
            if not name:
                continue
            rows.append({
                "name": name,
                "is_model": "yes" if MODEL_RE.match(name) else "no",
                "pull_count": repo.get("pull_count") or 0,
                "star_count": repo.get("star_count") or 0,
                "last_updated": (repo.get("last_updated") or "")[:19],
                # Short, factual, written by Ersilia. No personal data here.
                "description": (repo.get("description") or "").replace("\n", " ")[:200],
            })
    # Sorted by pulls so the committed diff is stable and the interesting rows are first.
    rows.sort(key=lambda r: (-r["pull_count"], r["name"]))
    return rows


def summarise(rows):
    models = [r for r in rows if r["is_model"] == "yes"]
    infra = [r for r in rows if r["is_model"] == "no"]
    model_pulls = sum(r["pull_count"] for r in models)
    logging.info("%d model images, %s pulls", len(models), format(model_pulls, ","))
    logging.info("%d infrastructure images, %s pulls (excluded from the model figure)",
                 len(infra), format(sum(r["pull_count"] for r in infra), ","))
    if models:
        counts = sorted(r["pull_count"] for r in models)
        logging.info("median %s pulls per model; most-pulled is %s with %s",
                     format(counts[len(counts) // 2], ","),
                     models[0]["name"], format(models[0]["pull_count"], ","))
    return len(models), model_pulls


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("-o", "--out-dir", default="data/dockerhub")
    parser.add_argument("-n", "--namespace", default=NAMESPACE)
    parser.add_argument("--check", action="store_true",
                        help="Do not fetch; fail if the committed snapshot is stale.")
    parser.add_argument("--max-age-days", type=int, default=21)
    args = parser.parse_args()

    if args.check:
        return check_freshness(args.out_dir, args.max_age_days, "dockerhub")

    rows = collect(args.namespace)
    if not rows:
        logging.error("no images returned for %s — refusing to write an empty snapshot",
                      args.namespace)
        return 1
    models, _ = summarise(rows)
    if not models:
        # A namespace with images but no eos#### names means the naming changed, and
        # writing that would silently zero the model pull figure.
        logging.error("no model images matched %s — refusing to write", MODEL_RE.pattern)
        return 1
    written = write_snapshot(args.out_dir, "images", FIELDS, rows)
    prune_superseded(args.out_dir, [written])
    return 0


if __name__ == "__main__":
    sys.exit(main())
