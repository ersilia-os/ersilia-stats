"""Snapshot loading for the static-site export.

`fetch_airtable.py` writes a fresh ``<table>_<YYYYMMDD>.csv`` on every run, so more
than one stamp per table can be present in ``data/air_tables/``. The previous loader
keyed on ``fname.split("_")[0]`` alone, which let ``os.listdir`` order decide which
snapshot won — a non-deterministic build. Here the newest stamp always wins.
"""
import os
import re

import pandas as pd

SNAPSHOT_RE = re.compile(r"^(?P<name>.+)_(?P<stamp>\d{8})\.csv$")

# Columns that must never reach the repo or the site. The fetch script drops these
# too (scripts/fetch_airtable.py); this is the second line of defence, so an older
# snapshot that still carries them cannot leak into the export.
PII_COLUMNS = {
    "email",
    "linkedin",
    "twitter_handle",
    "github_handle",
}

# Free-text fields that embed personal names ("Anna Homs Riba, Trustee, …").
# Nothing on the site uses them.
NARRATIVE_COLUMNS = {
    "community": {"name", "description", "contribution"},
}

# Airtable scratch columns from abandoned imports.
JUNK_COLUMNS = {"table_15", "imported_table"}


def _slug(value):
    return str(value).strip().lower().replace(" ", "_").replace("-", "_")


def newest_snapshots(data_dir):
    """Return ``{table_name: (stamp, path)}`` keeping only the newest stamp each."""
    best = {}
    for fname in sorted(os.listdir(data_dir)):
        if not fname.endswith(".csv"):
            continue
        match = SNAPSHOT_RE.match(fname)
        if match:
            name, stamp = match.group("name"), match.group("stamp")
        else:
            name, stamp = fname[:-4], ""  # undated file: lowest precedence
        name = _slug(name)
        if name not in best or stamp >= best[name][0]:
            best[name] = (stamp, os.path.join(data_dir, fname))
    return best


def load_tables(data_dir):
    """Load the newest snapshot per table into ``{table_name: DataFrame}``.

    Column names are normalised to ``lower_snake_case``; PII, narrative and junk
    columns are dropped on the way in.
    """
    tables = {}
    for name, (_stamp, path) in newest_snapshots(data_dir).items():
        df = pd.read_csv(path)
        df.columns = [_slug(c) for c in df.columns]
        drop = (PII_COLUMNS | JUNK_COLUMNS | NARRATIVE_COLUMNS.get(name, set()))
        keep = [c for c in df.columns if c not in drop]
        tables[name] = df[keep]
    return tables


def load_collected(root="data"):
    """Load the committed PUBLIC snapshots: Docker Hub, GitHub and OpenAlex.

    Kept separate from ``load_tables`` because these are a different kind of source. The
    Airtable snapshot is gitignored, refetched on every deploy, and carries personal data
    that has to be stripped. These are committed, public, and need no filtering — so
    treating them the same would mean either running PII rules over data that has none, or
    weakening the rules that protect the data that does.

    A missing directory is not an error. If a collector has never run, or its snapshot was
    removed, the section builders fall back to the Airtable figures and the site still
    builds — which is the whole reason these are separate directories.
    """
    out = {}
    for key, subdir in (("dockerhub", "dockerhub"), ("github", "github"),
                        ("scholar", "scholar")):
        path = os.path.join(root, subdir)
        if not os.path.isdir(path):
            continue
        for name, (stamp, file_path) in newest_snapshots(path).items():
            # Dated files only. An undated CSV in one of these directories is a working
            # artefact, not a snapshot — `doi_map_review.csv` is there for a person to
            # read, and loading it as data would be a category error.
            if not stamp:
                continue
            frame = pd.read_csv(file_path)
            frame.columns = [_slug(c) for c in frame.columns]
            out["%s_%s" % (key, name)] = frame
    return out


def collected_dates(root="data"):
    """``{source: YYYY-MM-DD}`` for each collected source, for the Methods note.

    The site names its sources, so it has to be able to say when each was last read.
    """
    dates = {}
    for key, subdir in (("dockerhub", "dockerhub"), ("github", "github"),
                        ("scholar", "scholar")):
        path = os.path.join(root, subdir)
        stamps = [s for s, _ in newest_snapshots(path).values() if s] if os.path.isdir(path) else []
        if stamps:
            newest = max(stamps)
            dates[key] = "%s-%s-%s" % (newest[:4], newest[4:6], newest[6:])
    return dates


def snapshot_date(data_dir):
    """Newest snapshot stamp across all tables, as ``YYYY-MM-DD``."""
    stamps = [s for s, _ in newest_snapshots(data_dir).values() if s]
    if not stamps:
        return None
    newest = max(stamps)
    return "%s-%s-%s" % (newest[:4], newest[4:6], newest[6:])


def snapshot_dates(data_dir):
    """``{table_name: "YYYY-MM-DD"}`` — the stamp of the snapshot ACTUALLY read.

    ``snapshot_date()`` returns the max across tables, so it reports the freshest
    table and structurally cannot reveal a stale one. That matters because a partial
    fetch leaves a mixed-age directory: ``fetch_airtable.py`` writes and prunes before
    it raises, so a table that failed keeps its previous CSV, and
    ``newest_snapshots()`` will happily pair today's Community with last month's
    Repositories — published under today's date, with nothing to say otherwise.

    Emitting one stamp per table is what lets the page and the maintainer see that.
    """
    out = {}
    for name, (stamp, _path) in newest_snapshots(data_dir).items():
        if stamp:
            out[name] = "%s-%s-%s" % (stamp[:4], stamp[4:6], stamp[6:])
    return out


def stale_tables(data_dir):
    """Tables whose snapshot is older than the newest one present."""
    dates = snapshot_dates(data_dir)
    if not dates:
        return {}
    newest = max(dates.values())
    return {name: date for name, date in dates.items() if date != newest}

