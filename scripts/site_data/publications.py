"""Publications section — output and its reach.

Two deliberate changes from the previous export:

* the journal ranking now requires **at least two** Ersilia articles before a venue
  can appear. Ranking by mean citations with a single article let one lucky paper
  top the chart, which said nothing about the venue.
* publications per year and cumulative citations share one combo chart, so the
  two series can actually be compared.
"""
from collections import Counter

import pandas as pd

from . import insights as ins
from .parse import (EMPTY, as_text, col, growth_pair, metric, multi_counts,
                    series_metric, to_num, value_counts)

# ISO codes are not readable on an axis. Only the codes that actually appear need naming;
# anything unmapped falls through as its code rather than being dropped.
COUNTRY_NAMES = {
    "ES": "Spain", "US": "United States", "GB": "United Kingdom", "ZA": "South Africa",
    "DE": "Germany", "AT": "Austria", "CM": "Cameroon", "IL": "Israel",
    "MZ": "Mozambique", "IT": "Italy", "FR": "France", "NL": "Netherlands",
    "CH": "Switzerland", "SE": "Sweden", "BE": "Belgium", "PT": "Portugal",
    "IN": "India", "CN": "China", "JP": "Japan", "AU": "Australia", "CA": "Canada",
    "BR": "Brazil", "KE": "Kenya", "NG": "Nigeria", "GH": "Ghana", "UG": "Uganda",
    "TZ": "Tanzania", "ET": "Ethiopia", "ZM": "Zambia", "MW": "Malawi",
    "SN": "Senegal", "ML": "Mali", "BF": "Burkina Faso", "CI": "Côte d'Ivoire",
    "DK": "Denmark", "NO": "Norway", "FI": "Finland", "IE": "Ireland", "PL": "Poland",
}

MIN_ARTICLES_FOR_JOURNAL_RANK = 2
YES = {"yes", "true", "1"}


def build(pubs, collected=None):
    if pubs is None or pubs.empty:
        empty_series = {"labels": [], "series": [], "n": 0}
        return dict(
            {k: dict(EMPTY) for k in (
                "per_year", "citations_per_year", "output_and_impact", "by_topic",
                "affiliation", "affiliation_by_year", "by_type", "by_african_collab",
                "top_journals", "open_access", "oa_routes", "collaboration_countries",
            )},
            growth=dict(empty_series), citation_growth=dict(empty_series),
            most_cited={"rows": [], "n": 0},
            citation_accrual={"labels": [], "series": [], "n": 0},
        )

    # OpenAlex citation counts, keyed by DOI, replace the hand-maintained column where
    # they exist. The manual figures understate the total by 31% — 1,305 against 1,713 —
    # and 38 of 42 papers differ, which is what happens to a number that is written down
    # once and then goes on being true for a while.
    live = _openalex_citations(collected)
    citations = _merge_citations(pubs, live)
    years = pd.to_numeric(col(pubs, "year"), errors="coerce")

    return {
        "per_year": _per_year(years),
        "citations_per_year": _citations_per_year(years, citations),
        "output_and_impact": _output_and_impact(years, citations),
        "growth": _growth(years),
        "citation_accrual": _citation_accrual(collected),
        "open_access": _open_access(collected),
        "oa_routes": _oa_routes(collected),
        "collaboration_countries": _collaboration_countries(collected),
        "most_cited": _most_cited(pubs, citations),
        "citation_growth": _citation_growth(years, citations),
        # Short form: a 4-column card clips the full leader sentence.
        "by_topic": multi_counts(col(pubs, "topic"), top=12,
                                 insight=ins.leader_short(multi_counts(col(pubs, "topic")))),
        "affiliation": _affiliation(pubs),
        "affiliation_by_year": _affiliation_by_year(pubs, years),
        "by_type": value_counts(col(pubs, "type"),
                                insight=ins.leader(value_counts(col(pubs, "type")), "publications")),
        "by_african_collab": _african(pubs),
        "top_journals": _top_journals(pubs, citations),
    }


def _per_year(years):
    counts = years.dropna().astype(int)
    counts = counts[counts > 1990].value_counts().sort_index()
    labels = [str(int(y)) for y in counts.index]
    return metric(labels, counts.values,
                  ins.busiest(labels, list(counts.values), "publication", "publications",
                              period="year"))


def _citations_per_year(years, citations):
    frame = pd.DataFrame({"year": years, "citations": citations}).dropna(subset=["year"])
    frame = frame[frame["year"] > 1990]
    grouped = frame.groupby(frame["year"].astype(int))["citations"].sum().sort_index()
    labels = [str(int(y)) for y in grouped.index]
    total = int(grouped.sum())
    insight = None
    if labels:
        peak = grouped.idxmax()
        insight = "%s citations in total; the %s cohort has accrued the most (%s)." % (
            ins.num(total), int(peak), ins.num(int(grouped.max())),
        )
    return metric(labels, grouped.values, insight)


def _output_and_impact(years, citations):
    """Papers per year (bars) against cumulative citations (line)."""
    frame = pd.DataFrame({"year": years, "citations": citations}).dropna(subset=["year"])
    frame = frame[frame["year"] > 1990]
    if frame.empty:
        return dict(EMPTY)
    frame["year"] = frame["year"].astype(int)
    full = range(int(frame["year"].min()), int(frame["year"].max()) + 1)
    per_year = [int((frame["year"] == y).sum()) for y in full]
    cites = [int(frame.loc[frame["year"] == y, "citations"].sum()) for y in full]
    running, cumulative_cites = 0, []
    for value in cites:
        running += value
        cumulative_cites.append(running)
    return series_metric(
        [str(y) for y in full],
        [{"name": "Publications", "values": per_year},
         {"name": "Cumulative citations", "values": cumulative_cites}],
        insight="%s publications have accrued %s citations to date." % (
            ins.num(sum(per_year)), ins.num(running),
        ),
        axes=["left", "right"],
        kinds=["bar", "line"],
        n=int(sum(per_year)),
    )


def _openalex_citations(collected):
    """``{doi: citations}`` from the collected OpenAlex snapshot, or empty."""
    works = (collected or {}).get("scholar_works")
    if works is None or works.empty or "doi" not in works.columns:
        return {}
    counts = to_num(works.get("citations"))
    return {_bare_doi(works["doi"].iloc[i]): int(counts.iloc[i])
            for i in range(len(works))}


def _bare_doi(value):
    """A DOI with any resolver prefix stripped. Airtable stores the full URL form."""
    text = str(value or "").strip()
    for prefix in ("https://doi.org/", "http://doi.org/", "doi:"):
        if text.lower().startswith(prefix):
            text = text[len(prefix):]
    return text.strip().lower()


def _merge_citations(pubs, live):
    """OpenAlex where the DOI resolves, the stored column where it does not.

    Falling back rather than blanking matters: if the collector has not run, or a paper
    has no DOI, the page should show the older number rather than zero. A zero would read
    as "never cited", which is a different and false claim.
    """
    stored = to_num(col(pubs, "citations"))
    if not live:
        return stored
    dois = as_text(col(pubs, "doi"))
    merged = []
    for i in range(len(pubs)):
        key = _bare_doi(dois.iloc[i]) if i < len(dois) else ""
        merged.append(live.get(key, stored.iloc[i] if i < len(stored) else 0))
    import pandas as _pd
    return _pd.Series(merged, index=pubs.index)


def _open_access(collected):
    """Whether Ersilia's own papers can be read without paying.

    Mission-relevant rather than decorative: an organisation whose purpose is to serve
    researchers in low-resource settings has a direct interest in whether its own output
    is behind a paywall. OpenAlex classifies each work as gold, green, hybrid, bronze or
    closed; the first four are all readable, so the split is readable against not.
    """
    works = (collected or {}).get("scholar_works")
    if works is None or works.empty or "oa_status" not in works.columns:
        return dict(EMPTY)
    status = as_text(works["oa_status"]).str.lower()
    status = status[status != ""]
    if status.empty:
        return dict(EMPTY)
    closed = int((status == "closed").sum())
    openly = int(len(status) - closed)
    return metric(
        ["Open access", "Paywalled"], [openly, closed],
        ins.share_of(openly, len(status), "papers", "can be read without a subscription"),
        n=int(len(status)),
    )


def _oa_routes(collected):
    """How the open ones are open: gold, green, hybrid, bronze.

    Worth separating because the routes are not equivalent. Gold is published open;
    bronze is readable at the publisher's discretion and can be withdrawn.
    """
    works = (collected or {}).get("scholar_works")
    if works is None or works.empty or "oa_status" not in works.columns:
        return dict(EMPTY)
    status = as_text(works["oa_status"]).str.lower()
    counts = status[(status != "") & (status != "closed")].value_counts()
    if counts.empty:
        return dict(EMPTY)
    labels = [str(k).title() for k in counts.index]
    return metric(labels, [int(v) for v in counts.values],
                  "%s is the most common route to open access." % labels[0])


def _collaboration_countries(collected):
    """Countries of the author institutions, across all papers.

    This measures international collaboration instead of asserting it. The publications
    table carries a hand-set "African collaboration" yes/no; this counts the institutions,
    so South Africa, Cameroon and Mozambique appear as themselves rather than as a flag.
    Institution countries only — author names are never collected.
    """
    works = (collected or {}).get("scholar_works")
    if works is None or works.empty or "institution_countries" not in works.columns:
        return dict(EMPTY)
    counter = Counter()
    for value in as_text(works["institution_countries"]):
        for code in value.split():
            if code:
                counter[code.upper()] += 1
    if not counter:
        return dict(EMPTY)
    items = counter.most_common(12)
    out = metric([COUNTRY_NAMES.get(k, k) for k, _ in items], [v for _, v in items])
    out["n"] = len(counter)
    out["insight"] = "%s countries appear among the author institutions; %s on the most papers." % (
        ins.num(len(counter)), COUNTRY_NAMES.get(items[0][0], items[0][0]))
    return out


def _citation_accrual(collected):
    """Citations by the year they were MADE, with the running total.

    This is the honest version of a chart the site already had. The existing one attributes
    citations to the year the paper was published, because that is all the source held,
    which forced a caveat: recent years necessarily look thin. OpenAlex records when each
    citation happened, so the curve can show real accrual and the caveat can go.
    """
    years = (collected or {}).get("scholar_citations_by_year")
    if years is None or years.empty:
        return {"labels": [], "series": [], "n": 0}
    totals = {}
    counts = to_num(years.get("citations"))
    for i in range(len(years)):
        year = str(years["year"].iloc[i]).strip()[:4]
        if year.isdigit():
            totals[int(year)] = totals.get(int(year), 0) + int(counts.iloc[i])
    if not totals:
        return {"labels": [], "series": [], "n": 0}
    span = range(min(totals), max(totals) + 1)
    per_year = [totals.get(y, 0) for y in span]
    running, total = [], 0
    for value in per_year:
        total += value
        running.append(total)
    return growth_pair(
        [str(y) for y in span], per_year, running, "citations", period="year",
        insight="%s citations to date, %s of them in %s." % (
            ins.num(total), ins.num(max(per_year)),
            str(list(span)[per_year.index(max(per_year))])),
    )


def _most_cited(pubs, citations):
    """The individual papers, named, ranked by citations.

    The site aggregates publications six ways and never named a single one, which for a
    research organisation's statistics page is a conspicuous gap.

    THE AFFILIATION COLUMN IS WHY THIS IS PUBLISHABLE, not decoration. Ranked by
    citations alone the top four papers all carry ``Ersilia Affiliation = No`` — 389,
    123, 66 and 54 citations, which are the founders' pre-Ersilia careers. The most
    cited *affiliated* paper has 53. A bare citation ranking under an Ersilia heading
    would therefore claim credit the data does not support, so the flag is shown as a
    column and the caption says what it means. Filtering the unaffiliated papers out
    silently would be the less honest fix, since it hides that the distinction exists.

    Titles, journals and years are public bibliographic facts. No author names are
    emitted, so this adds no disclosure surface.
    """
    if pubs is None or pubs.empty:
        return {"rows": [], "n": 0}
    titles = as_text(col(pubs, "title"))
    if titles.empty:
        return {"rows": [], "n": 0}
    years = pd.to_numeric(col(pubs, "year"), errors="coerce")
    affiliation = as_text(col(pubs, "ersilia_affiliation"))

    rows = []
    for i in range(len(pubs)):
        title = titles.iloc[i] if i < len(titles) else ""
        if not title:
            continue
        cites = citations.iloc[i] if i < len(citations) else 0
        year = years.iloc[i] if i < len(years) else None
        flag = (affiliation.iloc[i] if i < len(affiliation) else "").strip().lower()
        rows.append({
            "title": title,
            "year": int(year) if pd.notna(year) else "",
            "citations": int(cites) if pd.notna(cites) else 0,
            "ersilia": "Yes" if flag in YES else "No",
        })
    if not rows:
        return {"rows": [], "n": 0}
    rows.sort(key=lambda r: (-r["citations"], r["title"]))

    affiliated = [r for r in rows if r["ersilia"] == "Yes"]
    top_affiliated = affiliated[0]["citations"] if affiliated else 0
    return {
        "rows": rows[:12],
        "n": len(rows),
        "insight": "Most cited overall is %s citations; most cited with a direct Ersilia "
                   "affiliation is %s." % (ins.num(rows[0]["citations"]),
                                           ins.num(top_affiliated)),
    }


def _growth(years):
    """Publications per year with the running total — same measure, so one identity."""
    frame = years.dropna()
    frame = frame[frame > 1990]
    if frame.empty:
        return {"labels": [], "series": [], "n": 0}
    full = range(int(frame.min()), int(frame.max()) + 1)
    per_year = [int((frame == y).sum()) for y in full]
    running, total = [], 0
    for value in per_year:
        total += value
        running.append(total)
    return growth_pair([str(y) for y in full], per_year, running, "publications",
                       period="year")


def _citation_growth(years, citations):
    """Citations earned per publication year, with the running total.

    Kept SEPARATE from publication counts rather than sharing one plot with them.
    Publications and citations are different measures, and a dual axis across two
    different measures is exactly the chart that invites a reader to see a
    relationship the data does not assert — "citations track output" — when the only
    honest statement is that each accumulates. Within this chart the two series are one
    measure and the total is the running sum, which is what makes its second axis fair.

    Citations are attributed to the year the PAPER was published, not the year the
    citation was made, because that is what the source records. So the recent years are
    necessarily low: a 2025 paper has had months to be cited, a 2018 paper has had years.
    """
    frame = pd.DataFrame({"year": years, "citations": citations}).dropna(subset=["year"])
    frame = frame[frame["year"] > 1990]
    if frame.empty:
        return {"labels": [], "series": [], "n": 0}
    frame["year"] = frame["year"].astype(int)
    full = range(int(frame["year"].min()), int(frame["year"].max()) + 1)
    per_year = [int(frame.loc[frame["year"] == y, "citations"].sum()) for y in full]
    running, total = [], 0
    for value in per_year:
        total += value
        running.append(total)
    return growth_pair([str(y) for y in full], per_year, running, "citations",
                       period="year",
                       insight="%s citations to date, most for work published in %s." % (
                           ins.num(total),
                           str(list(full)[per_year.index(max(per_year))]),
                       ))


def _affiliation(pubs):
    out = value_counts(col(pubs, "ersilia_affiliation"))
    values = dict(zip(out["labels"], out["values"]))
    yes = values.get("Yes", 0)
    out["insight"] = ins.share_of(yes, sum(out["values"]), "publications",
                                  "carry a direct Ersilia affiliation")
    out["semantics"] = {"Yes": "brand", "No": "neutral"}
    return out


def _affiliation_by_year(pubs, years):
    frame = pd.DataFrame({
        "year": years,
        "aff": as_text(col(pubs, "ersilia_affiliation")).str.lower(),
    }).dropna(subset=["year"])
    frame = frame[frame["year"] > 1990]
    if frame.empty:
        return dict(EMPTY)
    frame["year"] = frame["year"].astype(int)
    span = sorted(frame["year"].unique())
    ersilia = [int(((frame["year"] == y) & (frame["aff"] == "yes")).sum()) for y in span]
    external = [int(((frame["year"] == y) & (frame["aff"] != "yes")).sum()) for y in span]
    return series_metric(
        [str(y) for y in span],
        [{"name": "Ersilia-affiliated", "values": ersilia},
         {"name": "External", "values": external}],
        insight=ins.latest_change([str(y) for y in span],
                                  [a + b for a, b in zip(ersilia, external)], "publications"),
    )


def _african(pubs):
    raw = as_text(col(pubs, "african_collaboration"))
    recorded = raw[(raw != "") & (raw.str.lower() != "nan")]
    out = value_counts(recorded)
    yes = int(recorded.str.lower().isin(YES).sum())
    out["insight"] = ins.share_of(yes, len(recorded), "recorded publications",
                                  "involve an African collaboration")
    # Neutral rather than crimson for "No": the absence of an African
    # collaboration is not a failure state, and a red bar would say it was.
    out["semantics"] = {"Yes": "brand", "No": "neutral"}
    return out


def _top_journals(pubs, citations):
    """Venues ranked by mean citations per Ersilia article, minimum two articles."""
    if "journal" not in pubs.columns:
        return dict(EMPTY)
    frame = pd.DataFrame({
        "journal": as_text(pubs["journal"]),
        "citations": citations,
    })
    frame = frame[(frame["journal"] != "") & (frame["journal"].str.lower() != "nan")]
    if frame.empty:
        return dict(EMPTY)
    grouped = frame.groupby("journal")["citations"].agg(["mean", "count", "sum"])
    eligible = grouped[grouped["count"] >= MIN_ARTICLES_FOR_JOURNAL_RANK]
    excluded = int(len(grouped) - len(eligible))
    ranked = eligible.sort_values("mean", ascending=False).head(10)
    if ranked.empty:
        return {
            "labels": [], "values": [], "n": 0,
            "insight": "No venue yet has %d or more Ersilia articles to rank on." %
                       MIN_ARTICLES_FOR_JOURNAL_RANK,
        }
    out = metric(ranked.index, ranked["mean"].round(1), None, n=int(len(ranked)))
    out["counts"] = [int(c) for c in ranked["count"]]
    out["totals"] = [int(s) for s in ranked["sum"]]
    out["unit"] = "mean citations per article"
    out["insight"] = "%s leads at %s citations per article." % (
        ranked.index[0], round(float(ranked["mean"].iloc[0]), 1),
    )
    return out
