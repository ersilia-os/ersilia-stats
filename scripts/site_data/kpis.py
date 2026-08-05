"""Headline KPIs.

Each KPI carries more than a number: a quarterly cumulative ``series`` for the tile's
sparkline, and ``delta_12m`` — how much it moved in the last four quarters. A bare
total says how big Ersilia is; the delta says whether it is still growing.
"""
import pandas as pd

from .parse import as_text, col, dense_quarters, quarter_counts, to_num

YES = {"yes", "true", "1"}

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


def _affiliated_dois(pubs):
    """Bare DOIs of the Ersilia-AFFILIATED publications.

    The headline "Citations" tile has to agree with the Publications page, and that page now
    reports affiliated work only: 17 of the 42 tracked papers carry no Ersilia affiliation
    and hold **1,019 of the 1,713 citations**, the largest being a 420-citation paper from
    before Ersilia existed. A tile labelled "Citations" beside an Ersilia logo cannot count
    those and stay honest, so this restricts it. The excluded work is published in its own
    right at the foot of the Publications page.
    """
    if pubs is None or pubs.empty or "ersilia_affiliation" not in pubs.columns:
        return None
    flags = as_text(col(pubs, "ersilia_affiliation")).str.strip().str.lower()
    dois = as_text(col(pubs, "doi"))
    keep = set()
    # `col()` returns an EMPTY Series when the column is absent, so a `range(len(pubs))`
    # loop over it is an IndexError waiting for a table without a `doi` column. The
    # synthetic fixture is exactly such a table, and this is what it caught.
    for i in range(min(len(pubs), len(flags))):
        if i >= len(dois):
            break
        if flags.iloc[i] in YES:
            bare = str(dois.iloc[i] or "").strip().lower()
            for prefix in ("https://doi.org/", "http://doi.org/", "doi:"):
                if bare.startswith(prefix):
                    bare = bare[len(prefix):]
            if bare:
                keep.add(bare.strip())
    return keep


def _bare(value):
    text = str(value or "").strip().lower()
    for prefix in ("https://doi.org/", "http://doi.org/", "doi:"):
        if text.startswith(prefix):
            text = text[len(prefix):]
    return text.strip()


def _openalex_totals(collected, dois=None):
    """``(per_year, total)`` from the collected OpenAlex citation series, or ``(None, None)``."""
    years = (collected or {}).get("scholar_citations_by_year")
    if years is None or years.empty:
        return None, None
    if dois is not None and "doi" in years.columns:
        years = years[[_bare(years["doi"].iloc[i]) in dois for i in range(len(years))]]
        if years.empty:
            return None, None
    counts = to_num(years.get("citations"))
    totals = {}
    if "year" not in years.columns:
        return None, None
    for i in range(min(len(years), len(counts))):
        year = str(years["year"].iloc[i]).strip()[:4]
        if year.isdigit():
            totals[int(year)] = totals.get(int(year), 0) + int(counts.iloc[i])
    if not totals:
        return None, None
    return totals, sum(totals.values())


def _star_total(collected):
    """Stars across every repository in the organisation, public and private.

    Summed from the collected GitHub snapshot plus the private aggregate, not from
    Airtable — the `Stars` column was deleted from that table, so the old
    `to_num(col(every_repo, "stars")).sum()` would now return 0 and the KPI would read
    zero stars.

    PRIVATE REPOSITORIES ARE INCLUDED, and doing it this way is the point: `org_totals`
    carries two integers and no names, so the total can cover private work without CI
    ever holding a token that can list private repositories. Measured when written: 664
    public + 5 private across 40 private repositories. If the aggregate is missing —
    a collector run without private access — the total silently covers public
    repositories only, which is the safe direction for a figure like this.
    """
    total = 0
    frame = (collected or {}).get("github_repos")
    if frame is not None and not frame.empty and "stars" in frame.columns:
        total += int(to_num(frame["stars"]).sum())
    totals = (collected or {}).get("github_org_totals")
    if totals is not None and not totals.empty and {"metric", "value"} <= set(totals.columns):
        values = to_num(totals["value"])
        for i in range(len(totals)):
            if str(totals["metric"].iloc[i]).strip() == "private_stars":
                total += int(values.iloc[i] or 0)
    return total


def _citation_total(pubs, collected):
    """The headline total: the sum of each work's own `cited_by_count`.

    NOT the sum of the per-year series, which is one citation short — OpenAlex cannot date
    every citation, so `counts_by_year` omits a few that `cited_by_count` includes. Using
    the series here made the site say 1,712 while Airtable, written from the same snapshot,
    said 1,713. A one-citation gap nobody can explain is worse than either number alone, so
    the authoritative per-work figure is the headline and the series is used only for the
    shape of the curve.
    """
    dois = _affiliated_dois(pubs)
    works = (collected or {}).get("scholar_works")
    if works is not None and not works.empty and "citations" in works.columns:
        frame = works
        if dois is not None and "doi" in works.columns:
            frame = works[[_bare(works["doi"].iloc[i]) in dois for i in range(len(works))]]
        total = int(to_num(frame["citations"]).sum())
        if total:
            return total
    if dois is not None and "ersilia_affiliation" in pubs.columns:
        flags = as_text(col(pubs, "ersilia_affiliation")).str.strip().str.lower()
        return int(to_num(col(pubs, "citations"))[flags.isin(YES).values].sum())
    return int(to_num(col(pubs, "citations")).sum())


def _citation_series(pubs, collected):
    """Cumulative citations by the year the citation happened, affiliated papers only."""
    per_year, _total = _openalex_totals(collected, _affiliated_dois(pubs))
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
    for frame, column in ((community, "country_(from_country)"), (events,
                          "country_(from_country)")):
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
    stars = _star_total(collected)

    # Ersilia-affiliated papers only, so the tile agrees with the Publications page and with
    # the citation total beside it. The other 17 tracked papers are the team's earlier work
    # and get their own card there; counting them here would make "Publications" mean
    # "papers we keep a record of", which is not what a reader takes it to mean.
    if pubs is not None and not pubs.empty and "ersilia_affiliation" in pubs.columns:
        aff_flags = as_text(col(pubs, "ersilia_affiliation")).str.strip().str.lower()
        affiliated_pubs = pubs[aff_flags.isin(YES).values]
    else:
        affiliated_pubs = pubs

    out = {
        "community_members": _kpi(len(community), _cumulative_series(col(community, "start_date"))),
        "repositories": _kpi(len(every_repo) if has_repos else 0,
                             _cumulative_series(col(every_repo, "creation_date")
                                                if has_repos else pd.Series(dtype=object))),
        "repositories_public": _kpi(len(repos_public) if repos_public is not None else 0),
        # Yearly, not quarterly: publications only carry a year. One year back,
        # accordingly.
        "publications": _kpi(len(affiliated_pubs),
                             _yearly_cumulative(col(affiliated_pubs, "year")), per_period=1),
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
