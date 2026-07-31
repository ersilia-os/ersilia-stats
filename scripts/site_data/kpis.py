"""Headline KPIs.

Each KPI carries more than a number: a quarterly cumulative ``series`` for the tile's
sparkline, and ``delta_12m`` — how much it moved in the last four quarters. A bare
total says how big Ersilia is; the delta says whether it is still growing.
"""
import pandas as pd

from .parse import col, dense_quarters, quarter_counts, to_num

QUARTERS_PER_YEAR = 4


def _cumulative_series(dates):
    """Quarterly cumulative counts from a date-ish series."""
    counts = dense_quarters(quarter_counts(dates))
    if counts.empty:
        return {"labels": [], "values": []}
    running = counts.cumsum()
    return {"labels": [str(i) for i in running.index],
            "values": [int(v) for v in running.values]}


def _yearly_cumulative(years, weights=None):
    """Cumulative series keyed by year — for measures with no usable date column.

    Publications carry a year but no publication date, and citations are a weight
    on those years rather than events of their own.
    """
    values = pd.to_numeric(years, errors="coerce")
    frame = pd.DataFrame({"year": values})
    frame["w"] = 1 if weights is None else to_num(weights).values
    frame = frame.dropna(subset=["year"])
    frame = frame[frame["year"] > 1990]
    if frame.empty:
        return {"labels": [], "values": []}
    grouped = frame.groupby(frame["year"].astype(int))["w"].sum().sort_index()
    full = range(int(grouped.index.min()), int(grouped.index.max()) + 1)
    running, labels, out = 0, [], []
    for year in full:
        running += int(grouped.get(year, 0))
        labels.append(str(year))
        out.append(running)
    return {"labels": labels, "values": out}


def _kpi(value, series=None, per_period=QUARTERS_PER_YEAR):
    series = series or {"labels": [], "values": []}
    values = series.get("values", [])
    delta = None
    if len(values) > per_period:
        delta = int(values[-1] - values[-1 - per_period])
    elif values:
        delta = int(values[-1])
    return {"value": int(value), "series": series, "delta_12m": delta}


def build(tables, repos_public, models):
    projects = tables.get("projects", pd.DataFrame())
    pubs = tables.get("publications", pd.DataFrame())
    community = tables.get("community", pd.DataFrame())
    orgs = tables.get("organisations", pd.DataFrame())
    events = tables.get("events", pd.DataFrame())
    blogposts = tables.get("blogposts", pd.DataFrame())

    # Countries with any Ersilia presence, not the 197-row reference table.
    from .parse import parse_multi
    footprint = set()
    for frame, column in ((community, "country_(from_country)"), (events, "country_(from_country)")):
        if frame is not None and not frame.empty and column in frame.columns:
            for value in frame[column].dropna():
                footprint.update(parse_multi(value))

    citations = int(to_num(col(pubs, "citations")).sum()) if not pubs.empty else 0
    stars = int(to_num(col(repos_public, "stars")).sum()) if repos_public is not None and not repos_public.empty else 0

    out = {
        "community_members": _kpi(len(community), _cumulative_series(col(community, "start_date"))),
        "repositories": _kpi(len(repos_public) if repos_public is not None else 0,
                             _cumulative_series(col(repos_public, "creation_date")
                                                if repos_public is not None else pd.Series(dtype=object))),
        # Yearly, not quarterly: publications only carry a year. One year back,
        # accordingly.
        "publications": _kpi(len(pubs), _yearly_cumulative(col(pubs, "year")), per_period=1),
        "total_citations": _kpi(
            citations,
            _yearly_cumulative(col(pubs, "year"), col(pubs, "citations")),
            per_period=1,
        ),
        "projects": _kpi(len(projects), _cumulative_series(col(projects, "start_date"))),
        "organisations": _kpi(len(orgs)),
        "countries_represented": _kpi(len(footprint)),
        "total_stars": _kpi(stars),
        "events": _kpi(len(events), _cumulative_series(col(events, "date"))),
        "blogposts": _kpi(len(blogposts), _cumulative_series(col(blogposts, "date"))),
    }

    if models is not None and not models.empty:
        out["models"] = _kpi(len(models), _cumulative_series(col(models, "incorporation_date")))

    return out
