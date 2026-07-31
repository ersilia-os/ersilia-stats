"""Community section — AGGREGATES ONLY.

The community table is the one place in this dataset with real personal data. Names,
emails and social handles are dropped at load time (``load.PII_COLUMNS`` /
``NARRATIVE_COLUMNS``) and the export's regex guard aborts the build if anything
email-shaped survives. Everything below is a count, a share or a distribution — no
row ever reaches the site.

Beyond the counts the previous site had, this adds the two views that answer what a
community section is actually for: **churn** (are we compounding or recycling
people?) and **retention** (how long do cohorts stay?).
"""
import pandas as pd

from . import insights as ins
from .parse import (
    EMPTY,
    col,
    cumulative,
    dense_quarters,
    metric,
    multi_counts,
    quarter_counts,
    series_metric,
    value_counts,
)

# Months since joining at which we measure survival.
RETENTION_HORIZONS = [3, 6, 12, 24]
DAYS_PER_MONTH = 30.44


def build(community, today):
    if community is None or community.empty:
        return dict(
            {k: dict(EMPTY) for k in (
                "roles", "growth", "duration_buckets", "by_country",
                "active_status", "by_gender", "by_organisation", "tenure",
            )},
            flow={"labels": [], "series": [], "n": 0},
            retention={"x": [], "y": [], "cells": [], "n": 0},
        )

    start = pd.to_datetime(col(community, "start_date"), errors="coerce")
    end = pd.to_datetime(col(community, "end_date"), errors="coerce")
    country = col(community, "country_(from_country)", "country")

    return {
        "roles": _roles(community),
        "growth": _growth(start),
        "flow": _flow(start, end),
        "tenure": _tenure(start, end),
        "retention": _retention(start, end, today),
        "duration_buckets": _duration_buckets(start, end),
        "active_status": _active_status(end),
        "by_country": multi_counts(country, top=12,
                                   insight=ins.leader(multi_counts(country),
                                                      "recorded member countries")),
        "by_gender": _gender(community),
        "by_organisation": multi_counts(
            col(community, "name_(from_org)", "organisation"), top=10,
            insight="Home institutions of community members, as recorded.",
        ),
    }


def _roles(community):
    """Roles are a multi-select: a member holding two roles counts in both.

    Shares therefore sum above 100%. The Methods modal says so explicitly.
    """
    out = multi_counts(col(community, "role"))
    if out["labels"]:
        out["insight"] = ins.join(
            ins.leader(out, "role assignments"),
            "Members can hold more than one role, so shares sum above 100%.",
        )
    return out


def _growth(start):
    quarters = quarter_counts(start)
    dense = dense_quarters(quarters).cumsum()
    out = cumulative(
        quarters,
        ins.span([str(i) for i in dense.index], list(dense.values), "people"),
    )
    out["n"] = int(dense.values[-1]) if len(dense) else 0
    return out


def _flow(start, end):
    """Joiners vs leavers vs net change, per quarter — the churn ledger."""
    joined = start.dropna().dt.to_period("Q")
    left = end.dropna().dt.to_period("Q")
    if joined.empty and left.empty:
        return {"labels": [], "series": [], "n": 0}
    span = pd.period_range(
        min([p for p in [joined.min() if not joined.empty else None,
                         left.min() if not left.empty else None] if p is not None]),
        max([p for p in [joined.max() if not joined.empty else None,
                         left.max() if not left.empty else None] if p is not None]),
        freq="Q",
    )
    joins = [int((joined == q).sum()) for q in span]
    exits = [int((left == q).sum()) for q in span]
    net = [j - e for j, e in zip(joins, exits)]
    total_joins, total_exits = sum(joins), sum(exits)
    retention = ins.pct(total_joins - total_exits, total_joins)
    negative = sum(1 for value in net if value < 0)
    return series_metric(
        [str(q) for q in span],
        [{"name": "Joined", "values": joins},
         {"name": "Left", "values": exits},
         {"name": "Net change", "values": net}],
        insight="%s joined and %s left; %s of joiners are still involved. %s quarters saw a net loss." % (
            ins.num(total_joins), ins.num(total_exits), retention, ins.num(negative),
        ),
        kinds=["bar", "bar", "line"],
        semantics=["good", "bad", "brand"],
        n=int(total_joins),
    )


def _tenure(start, end):
    """Distribution of completed tenures, in months, with the mean marked.

    Only members whose involvement has ended are binned — including still-active
    members would censor every long tenure downwards.
    """
    finished = start.notna() & end.notna()
    if not finished.any():
        return dict(EMPTY)
    months = ((end - start)[finished].dt.days / DAYS_PER_MONTH).clip(lower=0)
    edges = [0, 3, 6, 9, 12, 18, 24, 36, 60]
    labels, values = [], []
    for i in range(len(edges) - 1):
        low, high = edges[i], edges[i + 1]
        labels.append("%d–%d" % (low, high))
        values.append(int(((months >= low) & (months < high)).sum()))
    tail = int((months >= edges[-1]).sum())
    if tail:
        labels.append("%d+" % edges[-1])
        values.append(tail)
    mean, median = float(months.mean()), float(months.median())
    out = metric(
        labels, values,
        "Median completed collaboration lasted %s months (mean %s). Still-active members are excluded." % (
            round(median, 1), round(mean, 1),
        ),
    )
    out["mean"] = round(mean, 1)
    out["median"] = round(median, 1)
    out["unit"] = "months"
    out["n"] = int(finished.sum())
    return out


def _retention(start, end, today):
    """Cohort survival: share of each joining year still involved at N months.

    A member counts in a horizon's denominator only once we can *know* the answer:
    they either already left, or they have been around at least that long. Someone
    who joined two months ago is not evidence about 3-month retention.
    """
    valid = start.notna()
    if not valid.any():
        return {"x": [], "y": [], "cells": [], "n": 0}

    cohorts = sorted(start[valid].dt.year.unique())
    tenure_days = (end.fillna(today) - start).dt.days
    elapsed_days = (today - start).dt.days
    has_left = end.notna()

    x_labels = ["%d mo" % h for h in RETENTION_HORIZONS]
    y_labels = [str(int(c)) for c in cohorts]
    cells, counts = [], []
    for y_index, year in enumerate(cohorts):
        in_cohort = valid & (start.dt.year == year)
        for x_index, horizon in enumerate(RETENTION_HORIZONS):
            threshold = horizon * DAYS_PER_MONTH
            observable = in_cohort & (has_left | (elapsed_days >= threshold))
            denominator = int(observable.sum())
            if denominator == 0:
                continue
            retained = int((observable & (tenure_days >= threshold)).sum())
            cells.append([x_index, y_index, round(100.0 * retained / denominator, 1)])
            counts.append([x_index, y_index, retained, denominator])

    insight = None
    one_year = [c for c in cells if c[0] == RETENTION_HORIZONS.index(12)]
    if one_year:
        average = sum(c[2] for c in one_year) / len(one_year)
        insight = "Across cohorts, %s of members reach one year. Blank cells are cohorts too recent to judge." % (
            ins.pct(average, 100),
        )
    return {
        "x": x_labels, "y": y_labels, "cells": cells, "counts": counts,
        "n": int(valid.sum()), "unit": "% still involved", "insight": insight,
    }


def _duration_buckets(start, end):
    finished = end.notna() & start.notna()
    months = ((end - start)[finished].dt.days / DAYS_PER_MONTH)
    buckets = [("< 3 months", 0, 3), ("3–6 months", 3, 6), ("6–12 months", 6, 12),
               ("> 1 year", 12, float("inf"))]
    labels = [b[0] for b in buckets]
    values = [int(((months >= b[1]) & (months < b[2])).sum()) for b in buckets]
    total = sum(values)
    short = values[0] + values[1]
    return metric(labels, values,
                  ins.share_of(short, total, "completed collaborations",
                               "lasted under six months") if total else None)


def _active_status(end):
    active, past = int(end.isna().sum()), int(end.notna().sum())
    return metric(["Active", "Past"], [active, past],
                  ins.share_of(active, active + past, "people who have joined",
                               "are still involved"),
                  semantics={"Active": "good", "Past": "neutral"})


def _gender(community):
    """Aggregate gender counts only — two numbers, no rows."""
    out = value_counts(col(community, "gender"))
    if out["labels"]:
        out["insight"] = ins.leader(out, "members with a recorded gender")
    return out
