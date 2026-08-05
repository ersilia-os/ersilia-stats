#!/usr/bin/env python3
"""A missing column must empty a card, never crash the build.

WHY THIS EXISTS
---------------
`parse.col()` and `DataFrame.get()` both return an **empty** object when a column is absent.
Any loop bounded by `len(frame)` that then indexes one of them raises

    IndexError: single positional indexer is out-of-bounds

and takes down the whole export rather than emptying one card. That is not hypothetical: it
reached CI once, from a publications table with no `DOI` column, and when the general case was
finally tested — every column of every source dropped one at a time — it found **eight more**,
including a `to_num(None)` that crashed the entire build if Docker Hub omitted `pull_count`.

The instructive part was that several were *partially* guarded. `projects._timeline` checked
`i < len(names)` and `i < len(status)` on the same line as an unchecked `start.iloc[i]`. A
guard applied by hand to some of a function's Series and not others is barely a guard, and
only an exhaustive sweep finds the gaps.

So this is the invariant, enforced rather than remembered.

WHAT IT DOES
------------
For every column of every Airtable table and every collected snapshot, drop that one column
and run every section builder. Then empty each table entirely, and drop each collected
source entirely. Any exception is a failure; an empty metric is a pass, because degrading is
the whole point.

It runs against the committed **fixture** by default, so it needs no secrets and no network
and can run on a pull request. Point it at `data/air_tables` to sweep the real snapshot.

    PYTHONPATH=scripts python3 scripts/check_degradation.py
    PYTHONPATH=scripts python3 scripts/check_degradation.py \\
        --data-dir data/air_tables --collected-root data
"""
import argparse
import sys
import traceback

import pandas as pd

from site_data import (code, community, kpis, load, model_activity, models, organisations,
                       outreach, projects, publications, quality, reach, repositories, usage)

TODAY = pd.Timestamp("2026-01-01")


def build_everything(tables, collected):
    """Run every section builder. Raises exactly what the real export would raise.

    Deliberately mirrors `site_data.build_all` rather than calling it, because `build_all`
    reads its inputs from disk and this needs to pass in mutated frames.
    """
    def table(name):
        return tables.get(name, pd.DataFrame())

    with_counts = repositories.attach_github_counts(table("repositories"), collected)
    public, _private = repositories.public_only(with_counts)

    repositories.build(with_counts, collected)
    publications.build(table("publications"), collected)
    models.build(table("models"))
    code.build(collected)
    model_activity.build(table("models"), collected)
    usage.build(collected, models=table("models"))
    reach.build(table("countries"), table("organisations"), table("community"),
                table("events"))
    quality.build(tables, public)
    community.build(table("community"), TODAY)
    organisations.build(table("organisations"), table("countries"))
    projects.build(table("projects"), TODAY, repos=table("repositories"),
                   publications=table("publications"))
    outreach.build_events(table("events"))
    outreach.build_blogposts(table("blogposts"))
    outreach.build_conferences(table("conferences"))
    kpis.build(tables, public, table("models"), repos_all=with_counts, collected=collected)


def scenarios(tables, collected):
    """Yield `(label, tables, collected)` for every degradation worth checking."""
    for name, frame in sorted(tables.items()):
        for column in frame.columns:
            if column == "airtable_id":
                continue
            patched = dict(tables)
            patched[name] = frame.drop(columns=[column])
            yield ("airtable %s is missing %r" % (name, column), patched, collected)

    for key, frame in sorted(collected.items()):
        for column in frame.columns:
            patched = dict(collected)
            patched[key] = frame.drop(columns=[column])
            yield ("collected %s is missing %r" % (key, column), tables, patched)

    # Whole sources gone, which is the fresh-clone and failed-collector case.
    for name in sorted(tables):
        patched = dict(tables)
        patched[name] = pd.DataFrame()
        yield ("airtable %s is empty" % name, patched, collected)
    for key in sorted(collected):
        patched = dict(collected)
        patched.pop(key)
        yield ("collected %s is absent" % key, tables, patched)
    yield ("no collected data at all", tables, {})
    yield ("every table empty", {k: pd.DataFrame() for k in tables}, collected)
    yield ("nothing at all", {k: pd.DataFrame() for k in tables}, {})


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0],
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--data-dir", default="data/air_tables_sample",
                        help="Airtable snapshot to sweep. Defaults to the committed fixture, "
                             "so this needs no secrets.")
    parser.add_argument("--collected-root", default="data/collected_sample",
                        help="Directory holding github/, dockerhub/ and scholar/.")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="Print every scenario, not just the failures.")
    args = parser.parse_args()

    tables = load.load_tables(args.data_dir)
    collected = load.load_collected(args.collected_root)
    if not tables:
        print("No tables in %s — nothing to check." % args.data_dir)
        return 1
    if not collected:
        print("WARNING: no collected snapshots under %s. The GitHub, Docker Hub and OpenAlex "
              "paths will not be exercised." % args.collected_root)

    failures, checked = [], 0
    for label, patched_tables, patched_collected in scenarios(tables, collected):
        checked += 1
        try:
            build_everything(patched_tables, patched_collected)
        except Exception as error:              # noqa: BLE001 - any exception is the failure
            failures.append((label, error, traceback.format_exc()))
        else:
            if args.verbose:
                print("  ok   %s" % label)

    print("Checked %d degradation scenario(s) from %s + %s"
          % (checked, args.data_dir, args.collected_root))
    if not failures:
        print("Every scenario degrades gracefully: a missing column empties a card, never "
              "raises.")
        return 0

    print("\n%d scenario(s) RAISED — the build would crash rather than empty a card:"
          % len(failures))
    for label, error, tb in failures:
        site_frames = [line.strip() for line in tb.split("\n") if "site_data" in line]
        where = site_frames[-1] if site_frames else "?"
        print("  - %s\n      %s: %s\n      %s" % (label, type(error).__name__, error, where))
    raise SystemExit("FAIL: %d degradation scenario(s) crash the build." % len(failures))


if __name__ == "__main__":
    sys.exit(main())
