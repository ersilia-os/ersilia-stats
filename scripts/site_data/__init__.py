"""Aggregate-only statistics for the Ersilia static site.

``scripts/export_site_data.py`` is the CLI over this package. Section builders live
in one module each and all return the metric shapes documented in ``parse.py``.

HARD RULE — PUBLIC SITE: emit AGGREGATES ONLY, never row-level personal data. The
community table's identifying columns are dropped at load (``load.py``), the
repositories section is filtered to public repositories (``repositories.py``), and the
CLI aborts the build if anything email-shaped survives into the output.
"""
from datetime import datetime, timezone

import pandas as pd

from . import (
    community as community_section,
    kpis as kpis_section,
    load,
    models as models_section,
    organisations as organisations_section,
    outreach,
    projects as projects_section,
    publications as publications_section,
    quality as quality_section,
    reach as reach_section,
    repositories as repositories_section,
)

__all__ = ["build_all", "load"]


def build_all(data_dir, today=None):
    """Load the newest snapshots and return the full ``stats.json`` payload."""
    tables = load.load_tables(data_dir)
    today = pd.Timestamp(today) if today is not None else pd.Timestamp.today().normalize()

    def table(name):
        return tables.get(name, pd.DataFrame())

    models = table("models")
    repos_public, private_excluded = repositories_section.public_only(table("repositories"))

    sections = {
        "models": models_section.build(models),
        # Projects needs the repositories and publications tables to resolve its own
        # link columns — the only cross-table roll-up in the build.
        "projects": projects_section.build(table("projects"), today,
                                           repos=table("repositories"),
                                           publications=table("publications")),
        "publications": publications_section.build(table("publications")),
        "repositories": repositories_section.build(table("repositories")),
        "community": community_section.build(table("community"), today),
        "organisations": organisations_section.build(table("organisations"), table("countries")),
        "reach": reach_section.build(table("countries"), table("organisations"),
                                     table("community"), table("events")),
        "events": outreach.build_events(table("events")),
        "blogposts": outreach.build_blogposts(table("blogposts")),
        "conferences": outreach.build_conferences(table("conferences")),
        "quality": quality_section.build(tables, repos_public),
    }

    return {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "snapshot_date": load.snapshot_date(data_dir),
        "meta": {
            "tables": sorted(tables),
            # One stamp per table, not just the max. `snapshot_date` above is the
            # NEWEST stamp across all tables, so on a mixed-age directory it reports
            # the most optimistic date available and hides the stale table completely.
            "snapshot_dates": load.snapshot_dates(data_dir),
            "stale_tables": load.stale_tables(data_dir),
            "models_available": bool(models is not None and not models.empty),
            "private_repositories": private_excluded,
            "aggregates_only": True,
        },
        "kpis": kpis_section.build(tables, repos_public, models, repos_all=table("repositories")),
        "sections": sections,
    }
