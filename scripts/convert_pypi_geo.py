#!/usr/bin/env python3
"""Turn a manual BigQuery PyPI-download export into a committed geography snapshot.

WHY THIS IS MANUAL, NOT FETCHED
--------------------------------
Country, OS and CPU-architecture detail for PyPI downloads exists only in Google
BigQuery's public ``bigquery-public-data.pypi.file_downloads`` dataset, queryable only
with a GCP project. There is no free, keyless HTTP API for it the way there is for the
release and download-count data in ``fetch_pypi.py``. So there is no scheduled
collector here: someone runs a query against that dataset in the BigQuery console by
hand, exports the result as JSON, and this script turns it into the dated CSV the site
reads. It carries no ``--check`` and no freshness gate, because nothing schedules it —
see the note in ``fetch_pypi.py``. It is the one data source CI cannot fetch, which is
why ``data/pypi_geo/`` is committed.

EXPECTED INPUT SHAPE: a JSON array, one object per (package, country, OS, CPU
architecture, Python version, file type) combination, grouped and counted, with at
least these keys:

    package, country_code, os_name, cpu_architecture, python_version, file_type,
    downloads, ci_downloads

matching a ``GROUP BY`` over ``file.project``, ``country_code``,
``details.system.name``, ``details.cpu``, ``details.python`` and ``file.type`` against
that dataset. ``country_code`` is ISO 3166-1 alpha-2; this script resolves it to a
full country name (needed for the site's map chart) and writes both.

    python3 scripts/convert_pypi_geo.py bigquery-export.json -o data/pypi_geo/
"""
import argparse
import json
import logging
import sys

import pycountry

from collect_common import prune_superseded, write_snapshot

FIELDS = ["package", "country_code", "country_name", "os_name", "cpu_architecture",
          "python_version", "file_type", "downloads", "ci_downloads"]


# pycountry's `.name` is the formal ISO short name, which for several countries is
# an inverted "X, Y of" form (`Korea, Republic of`) — fine as data, awkward as a
# chart label. Overridden to the common form these countries are known by, which
# also happens to be what site/js/charts.js's own MAP_ALIAS table normalises map
# tooltips to, so a country reads the same way on the ranked list and the map.
DISPLAY_NAME_OVERRIDES = {
    "KR": "Korea", "IR": "Iran", "MD": "Moldova", "TW": "Taiwan",
    "RU": "Russia", "VN": "Vietnam", "VG": "British Virgin Islands",
}


def country_name(code):
    if code in DISPLAY_NAME_OVERRIDES:
        return DISPLAY_NAME_OVERRIDES[code]
    country = pycountry.countries.get(alpha_2=str(code).upper())
    return country.name if country else str(code)


def convert(rows):
    out = []
    for row in rows:
        code = str(row.get("country_code") or "").strip().upper()
        out.append({
            "package": row.get("package", ""),
            "country_code": code,
            "country_name": country_name(code) if code else "",
            "os_name": row.get("os_name") or "",
            "cpu_architecture": row.get("cpu_architecture") or "",
            "python_version": row.get("python_version") or "",
            "file_type": row.get("file_type") or "",
            "downloads": int(row.get("downloads") or 0),
            "ci_downloads": int(row.get("ci_downloads") or 0),
        })
    out.sort(key=lambda r: (r["package"], -r["downloads"]))
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("input", help="The BigQuery JSON export.")
    parser.add_argument("-o", "--out-dir", default="data/pypi_geo")
    args = parser.parse_args()

    with open(args.input, encoding="utf-8") as handle:
        raw = json.load(handle)
    if not raw:
        logging.error("%s has no rows — refusing to write an empty snapshot", args.input)
        return 1

    rows = convert(raw)
    written = write_snapshot(args.out_dir, "downloads", FIELDS, rows)
    prune_superseded(args.out_dir, [written])

    total = sum(r["downloads"] for r in rows)
    packages = sorted({r["package"] for r in rows})
    countries = sorted({r["country_code"] for r in rows if r["country_code"]})
    logging.info("%s downloads across %d package(s) and %d countries: %s",
                 format(total, ","), len(packages), len(countries), ", ".join(packages))
    return 0


if __name__ == "__main__":
    sys.exit(main())
