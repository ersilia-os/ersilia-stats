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


def _openalex_totals(collected):
    """``(per_year, total)`` from the collected OpenAlex citation series, or ``(None, None)``."""
    years = (collected or {}).get("scholar_citations_by_year")
    if years is None or years.empty:
        return None, None
    counts = to_num(years.get("citations"))
    totals = {}
    for i in range(len(years)):
        year = str(years["year"].iloc[i]).strip()[:4]
        if year.isdigit():
            totals[int(year)] = totals.get(int(year), 0) + int(counts.iloc[i])
    if not totals:
        return None, None
    return totals, sum(totals.values())


def _citation_total(pubs, collected):
    """The headline total: the sum of each work's own `cited_by_count`.

    NOT the sum of the per-year series, which is one citation short — OpenAlex cannot date
    every citation, so `counts_by_year` omits a few that `cited_by_count` includes. Using
    the series here made the site say 1,712 while Airtable, written from the same snapshot,
    said 1,713. A one-citation gap nobody can explain is worse than either number alone, so
    the authoritative per-work figure is the headline and the series is used only for the
    shape of the curve.
    """
    works = (collected or {}).get("scholar_works")
    if works is not None and not works.empty and "citations" in works.columns:
        total = int(to_num(works["citations"]).sum())
        if total:
            return total
    return int(to_num(col(pubs, "citations")).sum())


def _citation_series(pubs, collected):
    """Cumulative citations by the year the citation happened."""
    per_year, _total = _openalex_totals(collected)
    if not per_year:
        return _yearly_cumulative(col(pubs, "year"), col(pubs, "citations"))
    labels, values, running = [], [], 0
    for year in range(min(per_year), max(per_year) + 1):
        running += per_year.get(year, 0)
        labels.append(str(year))
        values.append(running)
    return {"labels": labels, "values": values}


def build(tables, repos_public, models, repos_all=None, collected=None):
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

    # Counts and totals cover every repository — a count is not disclosure. Only
    # figures that would name a repository are restricted to the public ones.
    every_repo = repos_all if repos_all is not None else repos_public
    has_repos = every_repo is not None and not every_repo.empty

    # The headline citation figure comes from OpenAlex when it is available, so it agrees
    # with the Publications page. The stored column understates the total by 31% — 1,305
    # against 1,713 — and a site that prints both numbers in two places is worse than one
    # that prints the wrong one consistently.
    citations = _citation_total(pubs, collected)
    stars = int(to_num(col(every_repo, "stars")).sum()) if has_repos else 0

    out = {
        "community_members": _kpi(len(community), _cumulative_series(col(community, "start_date"))),
        "repositories": _kpi(len(every_repo) if has_repos else 0,
                             _cumulative_series(col(every_repo, "creation_date")
                                                if has_repos else pd.Series(dtype=object))),
        "repositories_public": _kpi(len(repos_public) if repos_public is not None else 0),
        # Yearly, not quarterly: publications only carry a year. One year back,
        # accordingly.
        "publications": _kpi(len(pubs), _yearly_cumulative(col(pubs, "year")), per_period=1),
        # The series is the REAL accrual — citations by the year they were made, which
        # OpenAlex records — not citations attributed to their paper's publication year.
        # The two differ a lot at the recent end, and only one of them is what a reader
        # assumes a citation curve means.
        "total_citations": _kpi(citations, _citation_series(pubs, collected), per_period=1),
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
