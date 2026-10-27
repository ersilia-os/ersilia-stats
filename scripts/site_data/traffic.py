"""GitHub traffic — which repositories visitors look at.

From ``data/github/traffic_sources_<date>.csv`` (``fetch_github_traffic.py``), which is
unlike every other collected source on this site: GitHub's traffic API exposes only a
rolling 14-day window and keeps no history, so the collector APPENDS each run's fetch to
what it already had rather than overwriting. This module always reads the LATEST fetched
window only (never older accumulated ones) — a chart mixing several 14-day windows would
double-count a visitor who showed up in more than one of them.

The collector also records referrers; the site no longer charts them, so only the
popular-paths rows are read here.
"""
from . import insights as ins
from .parse import EMPTY, metric

EMPTY_SECTION = {
    "most_visited_repos": dict(EMPTY),
}


def _latest_window(df):
    """Rows from the most recently fetched window only — never several accumulated
    14-day windows at once, which would double-count a repeat visitor."""
    dates = df["fetched_at"].astype(str).str.slice(0, 10)
    return df[dates == dates.max()]


def build(collected):
    df = (collected or {}).get("github_traffic_sources")
    required = {"repo", "kind", "source", "count", "fetched_at"}
    if df is None or df.empty or not required.issubset(df.columns):
        return dict(EMPTY_SECTION)

    latest = _latest_window(df)
    if latest.empty:
        return dict(EMPTY_SECTION)

    return {
        "most_visited_repos": _most_visited_repos(latest),
    }


def _most_visited_repos(latest):
    """Which repositories carry the traffic, from the popular-paths endpoint."""
    paths = latest[latest["kind"] == "path"]
    if paths.empty:
        return dict(EMPTY)
    by_all_repos = paths.groupby("repo")["count"].sum()
    by_repo = by_all_repos.sort_values(ascending=False).head(12)
    if by_repo.empty:
        return dict(EMPTY)
    return metric(
        by_repo.index, by_repo.values,
        ins.concentration(list(by_all_repos.values), "repositories' page views"),
        countNoun="views",
        n=int(paths["count"].sum()),
    )
