"""Community section — AGGREGATES ONLY.

The community table is the one place in this dataset with real personal data. Names,
emails and social handles are dropped at load time (``load.PII_COLUMNS`` /
``NARRATIVE_COLUMNS``) and the export's regex guard aborts the build if anything
email-shaped survives. Everything below is a count, a share or a distribution — no
row ever reaches the site.

The framing is deliberate. This section used to lead with a churn ledger
(joiners vs leavers vs net change) and a cohort-retention heatmap. Both were correct
arithmetic and both were the wrong question: they made a growing community read as an
attrition problem, and the retention grid's colour scale was set by a single 2020
member sitting at 100%, which squashed every real cohort into the pale end. A
contributor whose collaboration ended is not a loss — most were students, interns and
fellows whose placements were always going to end.

So what this measures now is participation: how many people have been involved, how
many are involved at once, how long they stay, and where they come from.
"""
import pandas as pd

from . import insights as ins
from .parse import (
    EMPTY,
    col,
    cumulative,
    dense_quarters,
    growth_pair,
    metric,
    multi_counts,
    quarter_counts,
    value_counts,
)

DAYS_PER_MONTH = 30.44


def build(community, today):
    if community is None or community.empty:
        return dict(
            {k: dict(EMPTY) for k in (
                "roles", "growth", "joined_per_quarter", "duration_buckets",
                "by_country", "active_status", "by_gender", "by_organisation",
                "active_over_time",
            )},
            participation={"labels": [], "series": [], "n": 0},
        )

    start = pd.to_datetime(col(community, "start_date"), errors="coerce")
    end = pd.to_datetime(col(community, "end_date"), errors="coerce")
    country = col(community, "country_(from_country)", "country")

    return {
        "roles": _roles(community),
        "growth": _growth(start),
        "joined_per_quarter": _joined_per_quarter(start),
        "participation": _participation(start),
        "active_over_time": _active_over_time(start, end, today),
        "duration_buckets": _duration_buckets(start, end),
        "active_status": _active_status(end),
        # Short form: this sits in a 4-column card, where the full
        # "leads with N of M recorded member countries (P%)" is clipped.
        "by_country": multi_counts(country, top=12,
                                   insight=ins.leader_short(multi_counts(country))),
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
        out["insight"] = ins.leader(out, "role assignments")
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


def _joined_per_quarter(start):
    """People joining per quarter — the rate that pairs with the running total."""
    dense = dense_quarters(quarter_counts(start))
    if not len(dense):
        return dict(EMPTY)
    labels = [str(i) for i in dense.index]
    return metric(labels, dense.values,
                  ins.busiest(labels, list(dense.values), "person", "people"))


def _participation(start):
    """The section's lead: people joining each quarter over the running total.

    Both panels come from the same column. The rate answers "are we still growing"
    and the total answers "how many people has this involved" — a cumulative curve
    alone hides the first, which is why they are drawn together.
    """
    dense = dense_quarters(quarter_counts(start))
    if not len(dense):
        return {"labels": [], "series": [], "n": 0}
    labels = [str(i) for i in dense.index]
    running = list(dense.cumsum().values)
    total = int(running[-1])
    return growth_pair(
        labels, list(dense.values), running, "people",
        insight="%s people have contributed to Ersilia since %s." % (
            ins.num(total), labels[0],
        ),
    )


def _active_over_time(start, end, today):
    """How many people were involved AT ONCE in each quarter.

    Joined and not yet ended, counted per quarter — the same shape as
    ``projects.active_over_time``. This is the honest measure of how big the
    community is at a given moment, as opposed to how many have ever passed through
    it, and unlike a churn ledger it does not treat a finished placement as a loss.
    """
    valid = start.notna()
    if not valid.any():
        return dict(EMPTY)
    span = pd.period_range(start[valid].min(), max(start[valid].max(), today), freq="Q")
    closed = end.fillna(today)
    labels, values = [], []
    for quarter in span:
        edge = quarter.end_time
        active = valid & (start <= edge) & (closed >= quarter.start_time)
        labels.append(str(quarter))
        values.append(int(active.sum()))
    peak = max(range(len(values)), key=lambda i: values[i])
    out = metric(labels, values,
                 "%s people involved at once now; the peak was %s in %s." % (
                     ins.num(values[-1]), ins.num(values[peak]), labels[peak],
                 ))
    out["n"] = int(values[-1])
    return out


def _duration_buckets(start, end):
    """How long completed collaborations ran.

    Stated as the most common length rather than as a share "under six months". The
    two say the same thing about the same numbers, but the second reads as a
    shortfall, and there is no standard here to fall short of: most of these are
    internships, fellowships and student placements with a term fixed before anyone
    arrived. Only ended collaborations are binned — counting current members would
    censor every long one downwards.
    """
    finished = end.notna() & start.notna()
    months = ((end - start)[finished].dt.days / DAYS_PER_MONTH)
    buckets = [("< 3 months", 0, 3), ("3–6 months", 3, 6), ("6–12 months", 6, 12),
               ("> 1 year", 12, float("inf"))]
    labels = [b[0] for b in buckets]
    values = [int(((months >= b[1]) & (months < b[2])).sum()) for b in buckets]
    total = sum(values)
    if not total:
        return metric(labels, values, None)
    most = max(range(len(values)), key=lambda i: values[i])
    out = metric(
        labels, values,
        "%s of %s completed collaborations ran %s, the most common length." % (
            ins.num(values[most]), ins.num(total), labels[most].replace("> ", "over "),
        ),
    )
    out["ordinal"] = True
    return out


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
