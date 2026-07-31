"""Export aggregate statistics for the static site (site/data/stats.json).

Reads the committed Airtable CSV snapshots in data/air_tables/ and writes a compact
JSON of pre-computed aggregates, plus one downloadable CSV per chart. This is the
data source for the static HTML site in site/.

HARD RULE — PUBLIC SITE: emit AGGREGATES ONLY, never row-level personal data.
Nothing from the community table at the individual level (no names, emails,
GitHub/LinkedIn/Twitter handles), and no private repository names. Those columns are
dropped when the snapshots are loaded (scripts/site_data/load.py) and again when they
are fetched (scripts/fetch_airtable.py); the guards at the end of this script abort
the build if anything slips through.

The aggregation itself lives in scripts/site_data/ — one module per section.

Usage:
    python scripts/export_site_data.py [--data-dir data/air_tables]
                                       [--out site/data/stats.json]
                                       [--today YYYY-MM-DD]
"""
import argparse
import csv
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from site_data import build_all  # noqa: E402

EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")

# Keys that would indicate an identifying column reached the payload.
FORBIDDEN_KEYS = {"email", "linkedin", "twitter_handle", "github_handle"}


# ---------------------------------------------------------------------------
# Per-chart CSVs
# ---------------------------------------------------------------------------
def _rows_for(metric):
    """Return ``(header, rows)`` for a metric, or ``None`` if it is not tabular."""
    if not isinstance(metric, dict):
        return None

    if "points" in metric and isinstance(metric["points"], list) and metric["points"]:
        first = metric["points"][0]
        if isinstance(first, dict):
            header = sorted(first)
            return header, [[point.get(k, "") for k in header] for point in metric["points"]]
        # Positional scatter: [stars, forks, contributors, name]
        return ["stars", "forks", "contributors", "name"], [
            [p[0], p[1], p[2], p[3]] for p in metric["points"] if len(p) >= 4
        ]

    if "cells" in metric:  # heatmap / matrix
        x_labels, y_labels = metric.get("x", []), metric.get("y", [])
        rows = []
        for cell in metric["cells"]:
            if len(cell) < 3:
                continue
            x_index, y_index, value = cell[0], cell[1], cell[2]
            rows.append([
                y_labels[y_index] if y_index < len(y_labels) else y_index,
                x_labels[x_index] if x_index < len(x_labels) else x_index,
                value,
            ])
        return ["row", "column", "value"], rows

    if "rows" in metric and isinstance(metric["rows"], list) and metric["rows"]:
        header = sorted(metric["rows"][0])
        return header, [[row.get(k, "") for k in header] for row in metric["rows"]]

    if "tree" in metric:  # sunburst: flatten to parent/child/value
        rows = []
        for parent in metric["tree"]:
            for child in parent.get("children", []):
                rows.append([parent.get("name", ""), child.get("name", ""), child.get("value", "")])
        return ["parent", "child", "value"], rows

    if "series" in metric:
        names = [s["name"] for s in metric["series"]]
        labels = metric.get("labels", [])
        rows = []
        for index, label in enumerate(labels):
            rows.append([label] + [
                s["values"][index] if index < len(s["values"]) else "" for s in metric["series"]
            ])
        return ["label"] + names, rows

    if "labels" in metric:
        labels, values = metric.get("labels", []), metric.get("values", [])
        return ["label", "value"], list(zip(labels, values))

    return None


def write_tables(payload, tables_dir):
    os.makedirs(tables_dir, exist_ok=True)
    written = 0
    for section, metrics in payload["sections"].items():
        for name, metric in metrics.items():
            prepared = _rows_for(metric)
            if not prepared:
                continue
            header, rows = prepared
            path = os.path.join(tables_dir, "%s_%s.csv" % (section, name))
            with open(path, "w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                writer.writerow(header)
                writer.writerows(rows)
            written += 1

    with open(os.path.join(tables_dir, "kpis.csv"), "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["metric", "value", "change_last_12_months"])
        for key, kpi in payload["kpis"].items():
            writer.writerow([key, kpi["value"], kpi.get("delta_12m", "")])
    return written + 1


def prune_stale_tables(tables_dir, payload):
    """Delete chart CSVs from a previous run whose metric no longer exists."""
    if not os.path.isdir(tables_dir):
        return []
    expected = {"kpis.csv"}
    for section, metrics in payload["sections"].items():
        for name, metric in metrics.items():
            if _rows_for(metric):
                expected.add("%s_%s.csv" % (section, name))
    removed = []
    for fname in sorted(os.listdir(tables_dir)):
        if fname.endswith(".csv") and fname not in expected:
            os.remove(os.path.join(tables_dir, fname))
            removed.append(fname)
    return removed


# ---------------------------------------------------------------------------
# Disclosure guards
# ---------------------------------------------------------------------------
def assert_no_pii(text, where):
    match = EMAIL_RE.search(text)
    if match:
        raise SystemExit(
            "ABORT: an email-like string (%s) reached %s. Check the aggregation before publishing."
            % (match.group(0), where)
        )


def assert_no_forbidden_keys(node, path="payload"):
    if isinstance(node, dict):
        for key, value in node.items():
            if str(key).strip().lower() in FORBIDDEN_KEYS:
                raise SystemExit("ABORT: identifying key %r reached %s." % (key, path))
            assert_no_forbidden_keys(value, "%s.%s" % (path, key))
    elif isinstance(node, list):
        for index, value in enumerate(node):
            assert_no_forbidden_keys(value, "%s[%d]" % (path, index))


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Export aggregate stats for the static site")
    parser.add_argument("--data-dir", default="data/air_tables")
    parser.add_argument("--out", default="site/data/stats.json")
    parser.add_argument("--today", default=None,
                        help="Reference date for 'now' (YYYY-MM-DD). Defaults to today.")
    args = parser.parse_args()

    payload = build_all(args.data_dir, today=args.today)
    text = json.dumps(payload, indent=2, ensure_ascii=False)

    assert_no_pii(text, "site/data/stats.json")
    assert_no_forbidden_keys(payload)

    out_dir = os.path.dirname(args.out) or "."
    os.makedirs(out_dir, exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as handle:
        handle.write(text + "\n")

    tables_dir = os.path.join(out_dir, "tables")
    removed = prune_stale_tables(tables_dir, payload)
    count = write_tables(payload, tables_dir)

    for fname in sorted(os.listdir(tables_dir)):
        with open(os.path.join(tables_dir, fname), encoding="utf-8") as handle:
            assert_no_pii(handle.read(), "site/data/tables/%s" % fname)

    excluded = payload["meta"]["private_repositories_excluded"]
    print("Wrote %s (%s bytes) + %d chart CSVs; snapshot %s." % (
        args.out, format(len(text), ","), count, payload["snapshot_date"]))
    if removed:
        print("Removed %d stale chart CSV(s): %s" % (len(removed), ", ".join(removed)))
    print("Excluded %d private repositories. Models table: %s." % (
        excluded, "present" if payload["meta"]["models_available"] else "ABSENT (run fetch_airtable.py)"))


if __name__ == "__main__":
    main()
