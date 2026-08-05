"""Read-only Airtable -> CSV snapshot exporter.

Writes one ``<table>_<YYYYMMDD>.csv`` per table into the output directory and prunes
the snapshots it supersedes, so exactly one snapshot per table survives. Never writes
to Airtable.

Two disclosure rules are enforced here, at the point data enters the repository:

* whole tables that are confidential or unused are skipped (``EXCLUDE_TABLE_SLUGS``);
* identifying columns are dropped from the rows (``PII_COLUMNS``,
  ``NARRATIVE_COLUMNS``). ``scripts/site_data/load.py`` drops them again on the way
  out, and ``export_site_data.py`` aborts if anything email-shaped survives — but the
  repository itself should never hold them in the first place.
"""
import os
import csv
import argparse
import logging
import re
from datetime import datetime, timezone

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

# pyairtable is imported lazily in main() so the column rules and helpers below can be
# imported and tested without the dependency installed.

# Never export these to CSV: confidential (financial data, contact lists) or unused.
# `models` used to be here, which left the Ersilia Model Hub — the flagship, and the
# richest table available — entirely absent from the site.
EXCLUDE_TABLE_SLUGS = {"news", "videos", "grants", "donations", "contacts"}

# Columns dropped from every table. Direct identifiers and contact routes: the site
# only ever shows community figures in aggregate, so there is no reason to commit
# these to the repo.
PII_COLUMNS = {"email", "linkedin", "twitter handle", "github handle"}

# Free-text columns that embed personal names, per table. Nothing on the site reads them.
#
# This note used to add that repository contributor handles were deliberately kept, as
# public GitHub metadata attached to public repositories. That decision stands, but the
# column no longer exists: `Contributor Names` was deleted from the Repositories table
# along with the other GitHub-derived fields, and the handles now come from GitHub itself
# via `github_api.contributor_logins`. Nothing in this file carries them any more.
NARRATIVE_COLUMNS = {
    "community": {"name", "description", "contribution"},
}

# Airtable scratch columns left over from abandoned imports.
JUNK_COLUMNS = {"table 15", "imported table"}

def read_table_list(csv_path):
    tables = []
    with open(csv_path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            base_id = (row.get("base_id") or row.get("base") or "").strip()
            table_id = (row.get("table_id") or row.get("table") or "").strip()
            # prefer human-readable 'table' column (or 'table_name' / 'name')
            table_name = (row.get("table") or row.get("table_name") or row.get("name")
                              or "").strip()
            filename = (row.get("filename") or "").strip()
            if not base_id or not table_id:
                logging.warning("Skipping row without base_id or table_id: %s", row)
                continue
            tables.append({"base_id": base_id, "table_id": table_id, "table_name": table_name,
                          "filename": filename})
    return tables


def fetch_all_records(api, base_id, table_id):
    table = api.table(base_id, table_id)
    # pyairtable's .all() handles pagination
    return table.all()


def dropped_columns(table_slug):
    """Column names (lowercased) to withhold from this table's CSV."""
    return PII_COLUMNS | JUNK_COLUMNS | NARRATIVE_COLUMNS.get(table_slug, set())


def records_to_rows(records, table_slug=""):
    """Flatten Airtable records to CSV rows, withholding identifying columns."""
    withhold = dropped_columns(table_slug)
    all_keys = set()
    for r in records:
        all_keys.update(r.get("fields", {}).keys())

    kept = sorted(k for k in all_keys if k.strip().lower() not in withhold)
    removed = sorted(k for k in all_keys if k.strip().lower() in withhold)
    if removed:
        logging.info("  withheld %d column(s): %s", len(removed), ", ".join(removed))

    header = ["airtable_id", *kept]
    rows = []
    for r in records:
        fields = r.get("fields", {})
        row = {"airtable_id": r.get("id", "")}
        for k in kept:
            row[k] = fields.get(k, "")
        rows.append(row)
    return header, rows


def write_csv(path, header, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=header)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)


def slugify(value: str) -> str:
    """Create a filesystem-friendly slug from value."""
    if not value:
        return ""
    value = value.strip().lower()
    # replace non-alphanumeric with hyphens
    value = re.sub(r"[^\w]+", "-", value)
    # collapse multiple hyphens
    value = re.sub(r"-{2,}", "-", value)
    return value.strip("-")


def ensure_csv_extension(name: str) -> str:
    if not name.lower().endswith(".csv"):
        return f"{name}.csv"
    return name


SNAPSHOT_RE = re.compile(r"^(?P<name>.+)_(?P<stamp>\d{8})\.csv$")


def prune_superseded(out_dir, written):
    """Delete older dated snapshots for any table written in this run.

    Each run stamps a new filename, so without this the directory accumulates one
    CSV per table per week and the exporter has to guess which is current.
    """
    if not os.path.isdir(out_dir):
        return []
    fresh = {os.path.basename(p) for p in written}
    current_tables = set()
    for fname in fresh:
        match = SNAPSHOT_RE.match(fname)
        if match:
            current_tables.add(match.group("name"))

    removed = []
    for fname in sorted(os.listdir(out_dir)):
        if fname in fresh or not fname.endswith(".csv"):
            continue
        match = SNAPSHOT_RE.match(fname)
        table = match.group("name") if match else fname[:-4]
        if table in current_tables:
            os.remove(os.path.join(out_dir, fname))
            removed.append(fname)
    return removed


def main():
    from pyairtable import Api

    parser = argparse.ArgumentParser(description="Fetch Airtable tables to CSV files")
    parser.add_argument("--api-key", "-k", required=False,
                        help="Airtable API key (or set AIRTABLE_API_KEY)")
    parser.add_argument("--tables-file", "-t", required=True,
                        help="CSV file listing base_id,table_id,optional filename")
    parser.add_argument("--out-dir", "-o", required=True, help="Output directory for CSV files")
    args = parser.parse_args()

    api_key = args.api_key or os.environ.get("AIRTABLE_API_KEY")
    if not api_key:
        parser.error("Airtable API key required via --api-key or AIRTABLE_API_KEY env var")

    tables = read_table_list(args.tables_file)
    if not tables:
        logging.error("No tables found in %s", args.tables_file)
        return

    api = Api(api_key)
    written, failed = [], []

    for t in tables:
        base_id = t["base_id"]
        table_id = t["table_id"]
        table_name = t.get("table_name", "")
        provided_filename = t["filename"]
        table_slug = slugify(table_name)

        if table_slug in EXCLUDE_TABLE_SLUGS:
            logging.info("Skipping excluded table: %s", table_name or table_id)
            continue

        if provided_filename:
            filename = ensure_csv_extension(provided_filename)
        else:
            # short timestamp + slugified table name (or slugified table_id)
            ts = datetime.now(timezone.utc).strftime("%Y%m%d")
            safe_name = table_slug or slugify(table_id)
            filename = f"{safe_name}_{ts}.csv"

        out_path = os.path.join(args.out_dir, filename)
        logging.info("Fetching base=%s table=%s -> %s", base_id, table_id, out_path)
        try:
            records = fetch_all_records(api, base_id, table_id)
            header, rows = records_to_rows(records, table_slug)
            write_csv(out_path, header, rows)
            written.append(out_path)
            logging.info("Wrote %d records to %s", len(rows), out_path)
        except Exception as e:  # noqa: BLE001 - one table must not abort the run
            failed.append(table_name or table_id)
            logging.error("Failed to fetch/write %s/%s: %s", base_id, table_id, e)

    removed = prune_superseded(args.out_dir, written)
    if removed:
        logging.info("Pruned %d superseded snapshot(s): %s", len(removed), ", ".join(removed))
    logging.info("Fetched %d table(s) into %s", len(written), args.out_dir)
    if failed:
        # Surface a partial fetch as a failure: a silently short snapshot set would
        # publish a site that quietly under-reports.
        raise SystemExit("Failed to fetch: %s" % ", ".join(failed))


if __name__ == "__main__":
    main()
