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
                "collaboration_breadth",
            )},
            growth=dict(empty_series), citation_growth=dict(empty_series),
            most_cited={"rows": [], "n": 0}, external_work={"rows": [], "n": 0},
            citation_accrual={"labels": [], "series": [], "n": 0},
        )

    # OpenAlex citation counts, keyed by DOI, replace the hand-maintained column where
    # they exist. The manual figures understate the total by 31% — 1,305 against 1,713 —
    # and 38 of 42 papers differ, which is what happens to a number that is written down
    # once and then goes on being true for a while.
    live = _openalex_citations(collected)
    citations = _merge_citations(pubs, live)

    # EVERY FIGURE BELOW COVERS ERSILIA-AFFILIATED PAPERS ONLY, except the two that are
    # about the split itself. 17 of the 42 tracked papers carry no Ersilia affiliation and
    # hold 1,019 of the 1,713 citations — they are the team's earlier careers, and counting
    # them under an Ersilia heading claims credit the data does not support. They are not
    # hidden: they get their own card at the foot of the page.
    flags = as_text(col(pubs, "ersilia_affiliation")).str.strip().str.lower()
    # When the column is absent `col()` returns an EMPTY Series, and a boolean mask built
    # from it is the wrong length — the shape of bug that crashed the build from
    # `kpis._affiliated_dois`. With no way to tell affiliated from external, show everything
    # rather than nothing; the affiliation chart then reports the absence itself.
    is_ersilia = (flags.isin(YES) if len(flags) == len(pubs)
                  else pd.Series(True, index=pubs.index))
    affiliated = pubs[is_ersilia.values]
    external = pubs[(~is_ersilia).values]
    aff_citations = citations[is_ersilia.values]
    ext_citations = citations[(~is_ersilia).values]
    aff_dois = {_bare_doi(v) for v in as_text(col(affiliated, "doi"))} - {""}
    aff_collected = _affiliated_collected(collected, aff_dois)
    years = pd.to_numeric(col(affiliated, "year"), errors="coerce")
    all_years = pd.to_numeric(col(pubs, "year"), errors="coerce")

    return {
        "per_year": _per_year(years),
        "citations_per_year": _citations_per_year(years, aff_citations),
        "output_and_impact": _output_and_impact(years, aff_citations),
        "growth": _growth(years),
        "external_work": _external_work(external, ext_citations),
        "citation_accrual": _citation_accrual(aff_collected),
        "open_access": _open_access(aff_collected),
        "oa_routes": _oa_routes(aff_collected),
        "collaboration_countries": _collaboration_countries(aff_collected),
        "collaboration_breadth": _collaboration_breadth(aff_collected),
        "most_cited": _most_cited(affiliated, aff_citations),
        "citation_growth": _citation_growth(years, aff_citations),
        # Short form: a 4-column card clips the full leader sentence.
        "by_topic": multi_counts(col(affiliated, "topic"), top=12,
                                 insight=ins.leader_short(multi_counts(col(affiliated, "topic")))),
        "affiliation": _affiliation(pubs),
        "affiliation_by_year": _affiliation_by_year(pubs, all_years),
        "by_type": value_counts(col(affiliated, "type"),
                                insight=ins.leader(value_counts(col(affiliated, "type")),
                                                   "affiliated publications")),
        "by_african_collab": _african(affiliated),
        "top_journals": _top_journals(affiliated, aff_citations),
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


def _affiliated_collected(collected, dois):
    """A `collected`-shaped dict whose OpenAlex frames hold only the given DOIs.

    Everything on the Publications page that reads OpenAlex directly — open access, the
    routes, co-author countries, collaboration breadth, citation accrual — took the whole
    snapshot. That silently mixed in the team's pre-Ersilia work, which is 17 of the 42
    papers and **1,019 of the 1,713 citations**, including the single most-cited paper at
    420. Those figures were therefore not describing Ersilia.

    Filtering here rather than inside each helper keeps their signatures and their logic
    untouched: they still receive a `collected` mapping and cannot tell the difference.
    """
    out = dict(collected or {})
    for key in ("scholar_works", "scholar_citations_by_year"):
        frame = out.get(key)
        if frame is None or frame.empty or "doi" not in frame.columns:
            continue
        keep = [_bare_doi(frame["doi"].iloc[i]) in dois for i in range(len(frame))]
        out[key] = frame[keep].copy()
    return out


def _openalex_citations(collected):
    """``{doi: citations}`` from the collected OpenAlex snapshot, or empty."""
    works = (collected or {}).get("scholar_works")
    if works is None or works.empty or "doi" not in works.columns:
        return {}
    counts = to_num(works.get("citations"))
    return {_bare_doi(works["doi"].iloc[i]): int(counts.iloc[i])
            for i in range(min(len(works), len(counts)))}


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
        n=len(status),
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


def _collaboration_breadth(collected):
    """Papers by HOW MANY countries their author institutions span.

    `_collaboration_countries` answers "which countries"; this answers "how many at once",
    and the two are not the same claim. A country list can be long because one paper had
    fourteen partners, and that would read as broad collaboration across the whole body of
    work when it was one consortium paper.

    It is worth publishing because the answer is strong on its own terms: **20 of the 25
    Ersilia-affiliated papers involve institutions in two or more countries**, and
    single-country papers are the minority. For an organisation whose purpose is
    collaborative research with under-resourced groups, that is a mission figure rather
    than a vanity one.

    Banded, because the raw counts run 1, 2, 3, 4, 5, 6, 7, 9, 10, 13, 14 with one or two
    papers in most of the upper values — a bar per distinct value would be mostly noise.
    """
    works = (collected or {}).get("scholar_works")
    if works is None or works.empty or "institution_countries" not in works.columns:
        return dict(EMPTY)

    # Numerals, not words: the card title already says these are countries, and
    # "one country" beside "two" collided at the width this card gets.
    bands = [(1, 1, "1"), (2, 2, "2"), (3, 4, "3\u20134"),
             (5, 9, "5\u20139"), (10, 10 ** 6, "10+")]
    labels = [band[2] for band in bands]
    values = [0] * len(labels)
    counted = 0
    for value in as_text(works["institution_countries"]):
        countries = len({code for code in value.split() if code})
        if not countries:
            continue                      # no institution recorded, not "one country"
        counted += 1
        for index, (low, high, _name) in enumerate(bands):
            if low <= countries <= high:
                values[index] += 1
                break
    if not counted:
        return dict(EMPTY)

    multi = counted - values[0]
    out = metric(
        labels, values,
        "%s of %s papers with a recorded institution span two or more countries." % (
            ins.num(multi), ins.num(counted),
        ),
        countNoun="papers",
        n=counted,
    )
    out["ordinal"] = True
    return out


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
    if "year" not in years.columns:
        return {"labels": [], "series": [], "n": 0}
    for i in range(min(len(years), len(counts))):
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

    # The caption quotes the AUTHORITATIVE total, not the sum of the plotted series.
    # OpenAlex cannot date every citation, so the dated series is a citation or two short of
    # each work's own `cited_by_count`. Quoting the series total here made the caption read
    # 1,712 while the headline tile beside it read 1,713 — a gap of one that no reader could
    # account for and that would look like a bug in the arithmetic.
    works = (collected or {}).get("scholar_works")
    authoritative = total
    if works is not None and not works.empty and "citations" in works.columns:
        authoritative = int(to_num(works["citations"]).sum()) or total
    undated = authoritative - total
    return growth_pair(
        [str(y) for y in span], per_year, running, "citations", period="year",
        insight=ins.join(
            "%s citations to date, %s of them in %s." % (
                ins.num(authoritative), ins.num(max(per_year)),
                str(list(span)[per_year.index(max(per_year))])),
            "%s cannot be dated and is not plotted." % ins.num(undated) if undated == 1 else
            ("%s cannot be dated and are not plotted." % ins.num(undated) if undated else None),
        ),
    )


def _external_work(external, citations):
    """The team's relevant work that carries no Ersilia affiliation.

    THIS CARD EXISTS SO THE FILTERING IS HONEST. Every other figure on the page now covers
    affiliated papers only, and quietly dropping 17 papers holding 1,019 citations would
    hide both the work and the choice. So they are shown, once, in their own right and
    under their own heading — related research by the same people, done elsewhere.

    Keeping them out of the main figures is not a judgement on the work; it is the only way
    an Ersilia statistics page can describe Ersilia. The most-cited paper here has 420
    citations, six times the most-cited affiliated one, which is exactly why it cannot sit
    inside a total labelled "Ersilia".
    """
    if external is None or external.empty:
        return {"rows": [], "n": 0}
    titles = as_text(col(external, "title"))
    if titles.empty:
        return {"rows": [], "n": 0}
    years = pd.to_numeric(col(external, "year"), errors="coerce")
    journals = as_text(col(external, "journal"))

    rows = []
    for i in range(len(external)):
        title = titles.iloc[i] if i < len(titles) else ""
        if not title:
            continue
        cites = citations.iloc[i] if i < len(citations) else 0
        year = years.iloc[i] if i < len(years) else None
        rows.append({
            "title": title,
            "year": int(year) if pd.notna(year) else "",
            "journal": (journals.iloc[i] if i < len(journals) else "")[:40],
            "citations": int(cites) if pd.notna(cites) else 0,
        })
    if not rows:
        return {"rows": [], "n": 0}
    rows.sort(key=lambda r: (-r["citations"], r["title"]))
    total = sum(r["citations"] for r in rows)
    return {
        "rows": rows[:10],
        "n": len(rows),
        "insight": "%s related papers by the team without an Ersilia affiliation, holding "
                   "%s citations between them." % (ins.num(len(rows)), ins.num(total)),
    }


def _most_cited(pubs, citations):
    """The individual papers, named, ranked by citations.

    The site aggregates publications six ways and never named a single one, which for a
    research organisation's statistics page is a conspicuous gap.

    ERSILIA-AFFILIATED PAPERS ONLY. Ranked over everything tracked, the top four all carry
    ``Ersilia Affiliation = No`` — 420, 132, 101 and 69 citations, the team's earlier
    careers — while the most-cited affiliated paper has 115. A bare ranking under an Ersilia
    heading would claim credit the data does not support.

    The unaffiliated papers are NOT dropped silently, which would hide that the distinction
    exists: they have their own card, `external_work`, at the foot of the page. The
    ``ersilia`` column here is consequently all "Yes" and is retained only so the table
    still states its own scope.

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

    # The old caption contrasted "most cited overall" with "most cited affiliated". Both
    # figures now describe the same paper, because the table is affiliated-only, so the
    # sentence contradicted itself. The comparison it was making lives on the card below.
    total = sum(r["citations"] for r in rows)
    return {
        "rows": rows[:12],
        "n": len(rows),
        "insight": "%s affiliated papers holding %s citations; the most cited has %s." % (
            ins.num(len(rows)), ins.num(total), ins.num(rows[0]["citations"]),
        ),
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
    ranked = eligible.sort_values("mean", ascending=False).head(10)
    if ranked.empty:
        return {
            "labels": [], "values": [], "n": 0,
            "insight": "No venue yet has %d or more Ersilia articles to rank on." %
                       MIN_ARTICLES_FOR_JOURNAL_RANK,
        }
    out = metric(ranked.index, ranked["mean"].round(1), None, n=len(ranked))
    out["counts"] = [int(c) for c in ranked["count"]]
    out["totals"] = [int(s) for s in ranked["sum"]]
    out["unit"] = "mean citations per article"
    out["insight"] = "%s leads at %s citations per article." % (
        ranked.index[0], round(float(ranked["mean"].iloc[0]), 1),
    )
    return out
