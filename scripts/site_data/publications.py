"""Publications section — output and its reach.

Two deliberate changes from the previous export:

* the journal ranking now requires **at least two** Ersilia articles before a venue
  can appear. Ranking by mean citations with a single article let one lucky paper
  top the chart, which said nothing about the venue.
* publications per year and cumulative citations share one combo chart, so the
  two series can actually be compared.
"""
import pandas as pd

from . import insights as ins
from .parse import (EMPTY, as_text, col, growth_pair, metric, multi_counts,
                    series_metric, to_num, value_counts)

MIN_ARTICLES_FOR_JOURNAL_RANK = 2
YES = {"yes", "true", "1"}


def build(pubs):
    if pubs is None or pubs.empty:
        empty_series = {"labels": [], "series": [], "n": 0}
        return dict(
            {k: dict(EMPTY) for k in (
                "per_year", "citations_per_year", "output_and_impact", "by_topic",
                "affiliation", "affiliation_by_year", "by_type", "by_african_collab",
                "top_journals",
            )},
            growth=dict(empty_series), citation_growth=dict(empty_series),
        )

    citations = to_num(col(pubs, "citations"))
    years = pd.to_numeric(col(pubs, "year"), errors="coerce")

    return {
        "per_year": _per_year(years),
        "citations_per_year": _citations_per_year(years, citations),
        "output_and_impact": _output_and_impact(years, citations),
        "growth": _growth(years),
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
