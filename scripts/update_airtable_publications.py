#!/usr/bin/env python3
"""Write collected citation counts back into the Airtable Publications table.

WHY
---
The site's citation figures are now correct — 1,712 from OpenAlex against the 1,305 the
Airtable column held — but **the team works in Airtable, and Airtable is still wrong.**
38 of 42 records disagree with what the site publishes. Fixing the website did not fix the
place people actually look.

THE ORDER MATTERS, AND IT IS NOT THE OBVIOUS ONE
    1. fetch_openalex.py                   OpenAlex -> data/scholar/works_<date>.csv
    2. update_airtable_publications.py     that CSV -> Airtable `Citations`
    3. fetch_airtable.py                   (optional) refresh the local snapshot
    4. export_site_data.py                 build

Collection comes FIRST, because collection is what produces the new numbers. And step 2
reads the CSV that step 1 wrote rather than calling OpenAlex again: two separate calls could
return different values, and then Airtable and the site would disagree for a reason nobody
could explain. Reusing the file makes the number in Airtable provably the number on the site.

THE SITE DOES NOT READ CITATIONS FROM AIRTABLE, and this script does not change that. It
exists for the humans browsing the base. So if it fails, or is never run, the published
figures are unaffected — there is no round trip in the build path.

THIS SCRIPT CAN DAMAGE THE SOURCE OF TRUTH, so:

* it is a **dry run by default** and needs `--apply` to write anything;
* it writes exactly **one field**, `Citations`, from an allow-list — not a denylist, because
  a denylist grows a hole every time someone adds a column;
* it never creates and never deletes a record;
* it refuses in four situations that all look like a successful update and are not (see
  `check_refusals`).

Fields it must never touch, verified as `singleSelect` human judgement in the live base:
`African collaboration`, `Ersilia Affiliation`, `Senior`, `Topic`, `Type`, `Status`. The
African-collaboration flag in particular carries information OpenAlex does not have — it
marks papers *about* Africa, which is not the same as papers with an African author
institution, and the two disagree on real records.

    export AIRTABLE_API_KEY=...          # needs data.records:write on the base
    python3 scripts/update_airtable_publications.py            # look at the diff
    python3 scripts/update_airtable_publications.py --apply    # write it
"""
import argparse
import csv
import glob
import logging
import os
import sys
from datetime import datetime, timezone

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

# The ONLY field this script is permitted to write.
CITATIONS_FIELD = "Citations"

# Present in the table and never written. Listed for the reader, not used as logic — the
# allow-list above is the mechanism; this is the explanation.
CURATED_FIELDS = ("African collaboration", "Ersilia Affiliation", "Senior", "Topic",
                  "Type", "Status", "Title", "Journal", "Authors", "Abstract", "DOI", "URL")

BATCH = 10          # Airtable's per-request limit for record updates


def bare_doi(value):
    """A DOI with any resolver prefix stripped, lowercased.

    The Airtable `DOI` field is of type `url`, so its values arrive as
    `https://doi.org/10.xxxx/yyy` while OpenAlex is keyed on the bare form.
    """
    text = str(value or "").strip()
    for prefix in ("https://doi.org/", "http://doi.org/", "doi:"):
        if text.lower().startswith(prefix):
            text = text[len(prefix):]
    return text.strip().lower()


def newest_works_csv(scholar_dir):
    """The most recent `works_<date>.csv`, and its date."""
    paths = sorted(glob.glob(os.path.join(scholar_dir, "works_*.csv")))
    if not paths:
        return None, None
    path = paths[-1]
    stamp = os.path.basename(path).rsplit("_", 1)[-1][:8]
    return path, stamp


def read_collected(path):
    """`{bare_doi: citations}` from the OpenAlex snapshot."""
    live = {}
    with open(path, newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            doi = bare_doi(row.get("doi"))
            if not doi:
                continue
            try:
                live[doi] = int(float(row.get("citations") or 0))
            except (TypeError, ValueError):
                continue
    return live


def build_plan(records, live):
    """Compare Airtable against the collected data.

    `records` is what the API returned: `[{"id":..., "fields": {...}}]`. Returns
    `(changes, unchanged, no_doi, unknown)` where `changes` is
    `[(record_id, doi, stored, wanted)]`.
    """
    changes, unchanged, no_doi, unknown = [], 0, [], []
    for record in records:
        fields = record.get("fields") or {}
        doi = bare_doi(fields.get("DOI"))
        if not doi:
            no_doi.append(fields.get("Title") or record.get("id"))
            continue
        if doi not in live:
            unknown.append(doi)
            continue
        stored = fields.get(CITATIONS_FIELD)
        stored = int(stored) if isinstance(stored, (int, float)) else None
        wanted = live[doi]
        if stored == wanted:
            unchanged += 1
        else:
            changes.append((record["id"], doi, stored, wanted))
    return changes, unchanged, no_doi, unknown


def check_refusals(stamp, changes, unknown, no_doi, total_records, args):
    """The four situations that look like a successful update and are not.

    Returns a list of reasons. A non-empty list means do not write, whatever the flags say
    (except where a flag is explicitly named).
    """
    reasons = []

    # 1. Stale collected data. Writing three-week-old counts over fresher ones is a
    #    regression dressed as an update.
    if stamp:
        age = (datetime.now(timezone.utc)
               - datetime.strptime(stamp, "%Y%m%d").replace(tzinfo=timezone.utc)).days
        if age > args.max_age_days:
            reasons.append("the collected snapshot is %d days old (limit %d). Re-run "
                           "fetch_openalex.py first." % (age, args.max_age_days))

    # 2. Partial collection. A half-finished collect looks exactly like "most papers lost
    #    their citations", and this would write that.
    resolvable = total_records - len(no_doi)
    if resolvable:
        matched = resolvable - len(unknown)
        share = matched / float(resolvable)
        if share < args.min_match:
            reasons.append("only %d of %d records with a DOI were found in the collected "
                           "data (%.0f%%, floor %.0f%%). The collection looks incomplete."
                           % (matched, resolvable, share * 100, args.min_match * 100))

    # 3. Large decreases. Citation counts essentially only rise; small dips are real (44->43,
    #    10->7 were both measured) but a big drop means a wrong DOI or a reindex, not a
    #    discovery.
    drops = []
    for _rid, doi, stored, wanted in changes:
        if stored is None or wanted >= stored:
            continue
        fall = stored - wanted
        if fall > max(10, stored * 0.2):
            drops.append((doi, stored, wanted))
    if drops and not args.force:
        listed = ", ".join("%s %d->%d" % d for d in drops[:5])
        reasons.append("%d record(s) would lose a large number of citations (%s). Pass "
                       "--force only if you have checked the DOIs." % (len(drops), listed))
    return reasons


def report(changes, unchanged, no_doi, unknown, total_records):
    if changes:
        print("%-42s %8s %8s %8s" % ("DOI", "stored", "live", "change"))
        for _rid, doi, stored, wanted in sorted(changes, key=lambda c: -(c[3] - (c[2] or 0))):
            shown = "-" if stored is None else str(stored)
            delta = wanted - (stored or 0)
            print("%-42s %8s %8d %+8d" % (doi[:42], shown, wanted, delta))
        before = sum(c[2] or 0 for c in changes)
        after = sum(c[3] for c in changes)
        print("\n%d of %d records would change; total across them %s -> %s"
              % (len(changes), total_records, format(before, ","), format(after, ",")))
    else:
        print("No changes: Airtable already matches the collected data.")
    print("%d unchanged, %d skipped (no DOI), %d unknown to OpenAlex"
          % (unchanged, len(no_doi), len(unknown)))
    if no_doi:
        print("  no DOI: " + ", ".join(str(t)[:44] for t in no_doi[:5]))
    if unknown:
        print("  unknown: " + ", ".join(unknown[:5]))


def apply_changes(table, changes):
    """Write `Citations` only, ten records per request."""
    payload = [{"id": rid, "fields": {CITATIONS_FIELD: wanted}}
               for rid, _doi, _stored, wanted in changes]
    written = 0
    for offset in range(0, len(payload), BATCH):
        chunk = payload[offset:offset + BATCH]
        table.batch_update(chunk)
        written += len(chunk)
        logging.info("  wrote %d/%d", written, len(payload))
    return written


def resolve_table_ids(config_path):
    with open(config_path, newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if "publication" in (row.get("table") or "").lower():
                return row.get("base_id"), row.get("table_id")
    return None, None


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--scholar-dir", default="data/scholar")
    parser.add_argument("--config", default="data/airtable_api_identifiers.csv")
    parser.add_argument("--apply", action="store_true",
                        help="Actually write. Without this, nothing is changed.")
    parser.add_argument("--force", action="store_true",
                        help="Permit large citation decreases. Check the DOIs first.")
    parser.add_argument("--max-age-days", type=int, default=21)
    parser.add_argument("--min-match", type=float, default=0.8)
    args = parser.parse_args()

    works_path, stamp = newest_works_csv(args.scholar_dir)
    if not works_path:
        logging.error("no works_*.csv in %s — run fetch_openalex.py first", args.scholar_dir)
        return 1
    live = read_collected(works_path)
    if not live:
        logging.error("%s has no usable rows", works_path)
        return 1
    logging.info("collected data: %s (%d works, stamped %s)",
                 works_path, len(live), stamp or "undated")

    key = os.environ.get("AIRTABLE_API_KEY")
    if not key:
        logging.error("AIRTABLE_API_KEY is not set. It needs data.records:write on the base.")
        return 1
    base_id, table_id = resolve_table_ids(args.config)
    if not base_id or not table_id:
        logging.error("no Publications row in %s", args.config)
        return 1

    try:
        from pyairtable import Api
    except ImportError:
        logging.error("pyairtable is not installed: pip install -r requirements.txt")
        return 1

    table = Api(key).table(base_id, table_id)
    try:
        records = table.all()
    except Exception as error:                        # noqa: BLE001 - message matters more
        logging.error("could not read the Publications table: %s", error)
        return 1
    logging.info("Airtable: %d records", len(records))

    changes, unchanged, no_doi, unknown = build_plan(records, live)
    reasons = check_refusals(stamp, changes, unknown, no_doi, len(records), args)

    report(changes, unchanged, no_doi, unknown, len(records))

    if reasons:
        print()
        for reason in reasons:
            logging.error("refusing to write: %s", reason)
        return 1

    if not changes:
        return 0
    if not args.apply:
        print("\nDry run. Re-run with --apply to write %d record(s)." % len(changes))
        return 0

    logging.info("writing %s to %d record(s)", CITATIONS_FIELD, len(changes))
    try:
        written = apply_changes(table, changes)
    except Exception as error:                        # noqa: BLE001
        text = str(error)
        if "403" in text or "NOT_AUTHORIZED" in text or "INVALID_PERMISSIONS" in text:
            logging.error("Airtable refused the write. The personal access token needs "
                          "the data.records:write scope on base %s. Read-only tokens can "
                          "fetch but not update.", base_id)
        else:
            logging.error("write failed: %s", text)
        return 1
    logging.info("updated %d record(s). Only %s was written; %s and every other curated "
                 "field are untouched.", written, CITATIONS_FIELD, CURATED_FIELDS[0])
    return 0


if __name__ == "__main__":
    sys.exit(main())
