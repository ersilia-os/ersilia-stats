#!/usr/bin/env python3
"""Keep the numeric columns of the Airtable Repositories table current from GitHub.

WHAT THIS REPLACES
------------------
The table's own description says it "is automatically completed with a nightly cron
action". That cron **no longer runs**, and the description is now stale documentation of a
retired job. This script is its replacement.

The evidence that it stopped, rather than never having worked: the columns are *almost*
right. Measured against live GitHub across the 141 public rows —

    Stars           140 / 141 exact
    Subscribers     140 / 141
    Forks           140 / 141
    Open Issues     131 / 141
    Contributors    122 / 141
    Total Commits   118 / 141          <- drifts fastest, by +2 to +6 commits

That is the signature of a job that ran correctly and then stopped: small, recent,
one-directional drift. It is not a table that was ever hand-entered, and it is not a table
that has been unmaintained for long.

SIX FIELDS, AND NOTHING ELSE
----------------------------
Every one is a plain `number` in the live schema, verified before this was written:
`Stars`, `Forks`, `Open Issues`, `Subscribers`, `Total Commits`, `Contributors`.

An **allow-list**, not a denylist, because a denylist grows a hole every time somebody adds
a column. Deliberately outside it:

    Visibility          singleSelect, and the field the SITE trusts to decide which
                        repository names it may publish. Writing it could publish the name
                        of a private repository. Human judgement, permanently.
    Type, Status        multipleSelects — human classification (Package, Analysis, …)
    Contributor Names   the GitHub handles. This script collects a contributor *count*
                        and never a login; see github_api.contributor_counts.
    Title, Description  curated prose
    URL                 a formula, and therefore not writable at all
    Projects            record links

STRUCTURAL DRIFT IS REPORTED, NEVER FIXED. This never creates a record and never deletes
one. A row whose repository has been deleted (`eos`, today) and a repository with no row
(`tuimux`, today) are both printed and left alone — adding a row requires a `Type`, which
is a judgement, and deleting one destroys history. `scripts/check_github_airtable_sync.py`
is the tool for that, and it fails CI when it finds any.

RUN THIS LOCALLY. **Its output names private repositories** — it has to, because 38 of the
179 rows are private and the point is to update them. That output belongs in a terminal.
GitHub Actions logs on a public repository are world-readable, so this script must not be
put in a workflow on this repository without redacting its report first.

WHAT IT CAUGHT ON ITS FIRST REAL RUN, as an illustration of why the refusals exist: the
`ersilia-stats` row claimed 310 commits and 9 contributors. That repository is four days
old and has 21 commits — the row had been seeded with the figures from the *capstone*
repository, which is a different, private repository that really does have ~310. The
sharp-fall refusal stopped the write and named the row.

    export AIRTABLE_API_KEY=...      # needs data.records:write on the Ersilia Content base
    export GH_STATS_TOKEN=...        # needs to see private repositories
    PYTHONPATH=scripts python3 scripts/update_airtable_repositories.py           # look
    PYTHONPATH=scripts python3 scripts/update_airtable_repositories.py --apply   # write
"""
import argparse
import csv
import logging
import os
import sys

from github_api import ORG, auth_headers, contributor_counts, repo_metrics

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

# Airtable field -> the key `collect()` produces. The only fields this script may write.
WRITABLE = {
    "Stars": "stars",
    "Forks": "forks",
    "Open Issues": "open_issues",
    "Subscribers": "subscribers",
    "Total Commits": "total_commits",
    "Contributors": "contributors",
}

# Present in the table and never written. Listed for the reader; the allow-list above is
# the mechanism.
CURATED = ("Visibility", "Type", "Status", "Contributor Names", "Title", "Description",
           "Projects", "URL", "Creation Date", "Name")

BATCH = 10            # Airtable's per-request limit for record updates


def resolve_table_ids(config_path, table_name="Repositories"):
    with open(config_path, newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if (row.get("table") or "").strip().lower() == table_name.lower():
                return row.get("base_id"), row.get("table_id")
    return None, None


def collect(org, names, headers, with_contributors=True):
    """`{name: {field_key: value}}` for the named repositories, live from GitHub.

    Deliberately does NOT read `data/github/repos_*.csv`. That file is public-only by
    construction, and 38 of the 179 rows in this table are private — updating only the
    public ones would leave a fifth of the job undone. Nothing fetched here is written to
    disk, so the committed inventory stays public-only.
    """
    metrics = repo_metrics(org, names, headers)
    counts = contributor_counts(org, list(metrics), headers) if with_contributors else {}

    out = {}
    for name, found in metrics.items():
        row = {
            "stars": found["stars"],
            "forks": found["forks"],
            "open_issues": found["open_issues"],
            "subscribers": found["subscribers"],
        }
        # An empty repository has no default branch and so no commit count. Omitted rather
        # than zeroed: writing 0 would assert "no commits", which is a different claim.
        if found.get("total_commits") is not None:
            row["total_commits"] = found["total_commits"]
        if name in counts:
            row["contributors"] = counts[name]
        out[name] = row
    return out


def as_int(value):
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def build_plan(records, live, fields):
    """Compare Airtable against GitHub.

    Returns `(changes, unchanged, unresolved)`, where `changes` is
    `[(record_id, name, {field: (stored, wanted)})]`.
    """
    changes, unchanged, unresolved = [], 0, []
    for record in records:
        stored_fields = record.get("fields") or {}
        name = str(stored_fields.get("Name") or "").strip()
        if not name:
            continue
        found = live.get(name)
        if found is None:
            unresolved.append(name)
            continue
        diff = {}
        for field in fields:
            key = WRITABLE[field]
            if key not in found:
                continue
            stored, wanted = as_int(stored_fields.get(field)), found[key]
            if stored != wanted:
                diff[field] = (stored, wanted)
        if diff:
            changes.append((record["id"], name, diff))
        else:
            unchanged += 1
    return changes, unchanged, unresolved


def check_refusals(changes, unresolved, total, args):
    """The situations that look like a successful update and are not."""
    reasons = []

    # 1. Most of the table did not resolve. A revoked token, a wrong org, or an outage all
    #    look exactly like "every repository lost its numbers", and this would write that.
    resolved = total - len(unresolved)
    if total:
        share = resolved / float(total)
        if share < args.min_match:
            reasons.append(
                "only %d of %d rows resolved on GitHub (%.0f%%, floor %.0f%%). Check that "
                "GH_STATS_TOKEN can see private repositories; a public-only token cannot "
                "resolve the %d private rows."
                % (resolved, total, share * 100, args.min_match * 100, 38))

    # 2. Wholesale zeroing. This is the failure this script was most likely to cause: the
    #    old `subscribers` collection read a field the list endpoint does not return and
    #    produced 0 for every repository. Writing that would have destroyed the column.
    zeroed = [(name, field, stored) for _rid, name, diff in changes
              for field, (stored, wanted) in diff.items()
              if wanted == 0 and (stored or 0) > 0]
    if zeroed and not args.force:
        by_field = {}
        for _name, field, _stored in zeroed:
            by_field[field] = by_field.get(field, 0) + 1
        worst = max(by_field.values())
        if worst > max(3, args.max_zeroed * max(1, resolved)):
            listed = ", ".join("%s on %d row(s)" % (f, n) for f, n in sorted(by_field.items()))
            reasons.append(
                "a positive value would be replaced by 0 too often (%s). That is what a "
                "broken source field looks like, not a real change. Verify the collector "
                "before overriding with --force." % listed)

    # 3. Implausible collapses. Stars can fall; commit counts essentially cannot, absent a
    #    force-push. A large drop means the wrong repository, not a discovery.
    drops = []
    for _rid, name, diff in changes:
        for field, (stored, wanted) in diff.items():
            if stored is None or wanted >= stored:
                continue
            if stored - wanted > max(10, stored * 0.2):
                drops.append((name, field, stored, wanted))
    if drops and not args.force:
        listed = ", ".join("%s %s %d->%d" % d for d in drops[:5])
        reasons.append("%d value(s) would fall sharply (%s). Pass --force only if you have "
                       "checked them." % (len(drops), listed))
    return reasons


def report(changes, unchanged, unresolved, fields):
    if changes:
        print("")
        print("%-34s %-14s %8s %8s %8s" % ("repository", "field", "stored", "live", "change"))
        print("-" * 76)
        for _rid, name, diff in sorted(changes, key=lambda c: c[1]):
            first = True
            for field in fields:
                if field not in diff:
                    continue
                stored, wanted = diff[field]
                shown = "-" if stored is None else str(stored)
                delta = "" if stored is None else "%+d" % (wanted - stored)
                print("%-34s %-14s %8s %8d %8s"
                      % (name if first else "", field, shown, wanted, delta))
                first = False
    totals = {}
    for _rid, _name, diff in changes:
        for field in diff:
            totals[field] = totals.get(field, 0) + 1
    print("")
    print("%d row(s) would change, %d already correct." % (len(changes), unchanged))
    if totals:
        print("  by field: " + ", ".join("%s %d" % (f, totals[f]) for f in fields if f in totals))
    if unresolved:
        print("")
        print("%d row(s) have NO repository on GitHub — reported, never changed, never "
              "deleted:" % len(unresolved))
        for name in sorted(unresolved):
            print("    %s" % name)
        print("  -> These publish stale numbers on the site. Remove the row in Airtable, or")
        print("     restore the repository. See scripts/check_github_airtable_sync.py.")


def apply_changes(table, changes, fields):
    """Write the allow-listed fields only, ten records per request."""
    payload = []
    for rid, _name, diff in changes:
        values = {f: diff[f][1] for f in fields if f in diff}
        if values:
            payload.append({"id": rid, "fields": values})
    written = 0
    for offset in range(0, len(payload), BATCH):
        chunk = payload[offset:offset + BATCH]
        table.batch_update(chunk)
        written += len(chunk)
        logging.info("  wrote %d/%d", written, len(payload))
    return written


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config", default="data/airtable_api_identifiers.csv")
    parser.add_argument("--org", default=ORG)
    parser.add_argument("--apply", action="store_true",
                        help="Actually write. Without this, nothing is changed.")
    parser.add_argument("--force", action="store_true",
                        help="Permit zeroing and sharp falls. Check the source first.")
    parser.add_argument("--fields", default="",
                        help="Comma-separated subset of: " + ", ".join(WRITABLE))
    parser.add_argument("--skip-contributors", action="store_true",
                        help="Skip contributor counts: one REST request per repository.")
    parser.add_argument("--min-match", type=float, default=0.8)
    parser.add_argument("--max-zeroed", type=float, default=0.05)
    args = parser.parse_args()

    fields = list(WRITABLE)
    if args.fields:
        chosen = [f.strip() for f in args.fields.split(",") if f.strip()]
        unknown = [f for f in chosen if f not in WRITABLE]
        if unknown:
            logging.error("not writable by this script: %s. Allowed: %s",
                          ", ".join(unknown), ", ".join(WRITABLE))
            return 1
        fields = [f for f in WRITABLE if f in chosen]

    key = os.environ.get("AIRTABLE_API_KEY")
    if not key:
        logging.error("AIRTABLE_API_KEY is not set. It needs data.records:write on the base.")
        return 1
    base_id, table_id = resolve_table_ids(args.config)
    if not base_id or not table_id:
        logging.error("no Repositories row in %s", args.config)
        return 1

    try:
        from pyairtable import Api
    except ImportError:
        logging.error("pyairtable is not installed: pip install -r requirements.txt")
        return 1

    table = Api(key).table(base_id, table_id)
    try:
        records = table.all()
    except Exception as error:                        # noqa: BLE001 - the message matters
        logging.error("could not read the Repositories table: %s", error)
        return 1
    names = [str((r.get("fields") or {}).get("Name") or "").strip() for r in records]
    names = [n for n in names if n]
    logging.info("Airtable: %d records, %d with a name", len(records), len(names))

    headers = auth_headers(require=True)
    live = collect(args.org, names, headers,
                   with_contributors=not args.skip_contributors)
    logging.info("GitHub: resolved %d of %d", len(live), len(names))

    changes, unchanged, unresolved = build_plan(records, live, fields)
    reasons = check_refusals(changes, unresolved, len(names), args)
    report(changes, unchanged, unresolved, fields)

    if reasons:
        print("")
        for reason in reasons:
            logging.error("refusing to write: %s", reason)
        return 1
    if not changes:
        return 0
    if not args.apply:
        print("")
        print("Dry run. Re-run with --apply to write %d record(s)." % len(changes))
        return 0

    logging.info("writing %s to %d record(s)", ", ".join(fields), len(changes))
    try:
        written = apply_changes(table, changes, fields)
    except Exception as error:                        # noqa: BLE001
        text = str(error)
        if "403" in text or "NOT_AUTHORIZED" in text or "INVALID_PERMISSIONS" in text:
            logging.error("Airtable refused the write. The personal access token needs the "
                          "data.records:write scope on base %s. Read-only tokens can fetch "
                          "but not update.", base_id)
        else:
            logging.error("write failed: %s", text)
        return 1
    logging.info("updated %d record(s). Only %s were written; %s and every other curated "
                 "field are untouched.", written, ", ".join(fields), CURATED[0])
    return 0


if __name__ == "__main__":
    sys.exit(main())
