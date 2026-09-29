#!/usr/bin/env python3
"""PyPI package metadata and download counts for Ersilia's published packages.

WHAT THIS COVERS, AND WHAT IT DELIBERATELY DOES NOT
-----------------------------------------------------
Two PyPI questions have a free, keyless, per-package API: **what has been released**
(pypi.org's JSON API — version, licence, release dates, release count) and **how much
of it gets downloaded** (pypistats.org, which mirrors the public BigQuery download
dataset over a rolling window). Both are fetched here.

A THIRD question — which country, OS and CPU architecture those downloads come from —
has no public API. It exists only in Google BigQuery's public dataset
(``bigquery-public-data.pypi.file_downloads``), queryable only with a GCP project, run
by hand in the BigQuery console. That is a manual, occasional snapshot rather than
something a scheduled collector can refresh, so it is out of scope for this script.
If it is ever wanted, it belongs beside this file as its own manually-refreshed
snapshot — not force-fit into the freshness gate this script exists to satisfy.

PyPI has no "list packages by organisation" endpoint, so the package list below is
maintained by hand — checked against ersilia-os by author, summary and project URL.
Update it when a new package ships.

    python3 scripts/fetch_pypi.py -o data/pypi/
    python3 scripts/fetch_pypi.py --check          # freshness gate for CI
"""
import argparse
import logging
import sys
import time

from collect_common import check_freshness, get_json, prune_superseded, write_snapshot

PYPI_API = "https://pypi.org/pypi"
PYPISTATS_API = "https://pypistats.org/api"
SLEEP_BETWEEN_CALLS = 3  # pypistats.org rate-limits aggressively (HTTP 429)

DEFAULT_PACKAGES = ["ersilia", "isaura", "ersilia-pack-utils", "stylia", "eosce", "olinda"]

FIELDS = ["package", "summary", "license", "requires_python", "latest_version",
          "repository_url", "total_releases", "first_release_date", "latest_release_date",
          "downloads_window_days", "downloads_window_total", "downloads_last_30d",
          "downloads_last_7d"]


def fetch_package_info(package):
    """Metadata + release history from PyPI's JSON API. ``None`` if the package is gone."""
    payload = get_json("%s/%s/json" % (PYPI_API, package))
    if not payload:
        return None
    info = payload.get("info") or {}
    releases = payload.get("releases") or {}
    upload_times = [
        f["upload_time_iso_8601"]
        for files in releases.values() for f in files
        if f.get("upload_time_iso_8601")
    ]
    project_urls = info.get("project_urls") or {}
    repository_url = next(
        (url for url in project_urls.values() if "github.com" in (url or "").lower()),
        info.get("home_page") or "",
    )
    return {
        "package": package,
        "summary": (info.get("summary") or "").replace("\n", " ").strip()[:200],
        # The raw field can carry a full licence TEXT, not a name — GPL's own file is
        # multiple KB. First line only; the SPDX-ish name is what a reader wants here,
        # not the licence body.
        "license": (info.get("license") or "").strip().split("\n")[0][:80],
        "requires_python": info.get("requires_python") or "",
        "latest_version": info.get("version") or "",
        "repository_url": repository_url,
        "total_releases": len(releases),
        "first_release_date": min(upload_times) if upload_times else "",
        "latest_release_date": max(upload_times) if upload_times else "",
    }


def fetch_downloads(package):
    """Rolling-window download counts from pypistats.org.

    pypistats.org mirrors the same public BigQuery dataset over whatever window it has
    chosen to retain — commonly around 90-180 days — which is the maximum history its
    public API exposes. There is no way to ask it for more, so these are window totals,
    never a lifetime figure, and the site must say so.
    """
    payload = get_json("%s/packages/%s/overall?mirrors=false" % (PYPISTATS_API, package))
    rows = sorted((payload or {}).get("data") or [], key=lambda r: r.get("date", ""))
    return {
        "downloads_window_days": len(rows),
        "downloads_window_total": sum(r.get("downloads", 0) for r in rows),
        "downloads_last_30d": sum(r.get("downloads", 0) for r in rows[-30:]),
        "downloads_last_7d": sum(r.get("downloads", 0) for r in rows[-7:]),
    }


def collect(packages):
    rows = []
    for package in packages:
        info = fetch_package_info(package)
        if info is None:
            logging.warning("%s: not found on PyPI, skipped", package)
            continue
        time.sleep(1)
        info.update(fetch_downloads(package))
        rows.append(info)
        time.sleep(SLEEP_BETWEEN_CALLS)
    rows.sort(key=lambda r: (-r["downloads_window_total"], r["package"]))
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("-o", "--out-dir", default="data/pypi")
    parser.add_argument("-p", "--packages", nargs="+", default=DEFAULT_PACKAGES)
    parser.add_argument("--check", action="store_true",
                        help="Do not fetch; fail if the local snapshot is stale.")
    parser.add_argument("--max-age-days", type=int, default=21)
    args = parser.parse_args()

    if args.check:
        return check_freshness(args.out_dir, args.max_age_days, "pypi")

    rows = collect(args.packages)
    if not rows:
        logging.error("no packages resolved — refusing to write an empty snapshot")
        return 1
    written = write_snapshot(args.out_dir, "packages", FIELDS, rows)
    prune_superseded(args.out_dir, [written])

    total = sum(r["downloads_window_total"] for r in rows)
    logging.info("%d packages, %s downloads across the pypistats window",
                 len(rows), format(total, ","))
    return 0


if __name__ == "__main__":
    sys.exit(main())
