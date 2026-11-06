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

So what this measures now is participation: how many people have been involved, how long
they stay, and where they come from.
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
    parse_multi,
    quarter_counts,
    value_counts,
)

DAYS_PER_MONTH = 30.44


def build(community):
    if community is None or community.empty:
        return dict(
            {k: dict(EMPTY) for k in (
                "roles", "growth", "joined_per_quarter", "duration_buckets",
                "by_country", "active_status", "by_gender", "by_organisation",
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
        "duration_buckets": _duration_buckets(start, end, col(community, "role")),
        "active_status": _active_status(end),
        # Short form: this sits in a 4-column card, where the full
        # "leads with N of M recorded member countries (P%)" is clipped.
        "by_country": multi_counts(country, top=12,
                                   insight=ins.leader_short(multi_counts(country))),
        "by_gender": _gender(community),
        "by_organisation": multi_counts(
            col(community, "name_(from_org)", "organisation"), top=10,
            insight="Home institutions of community members.",
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


def _duration_buckets(start, end, role=None):
    """How long completed collaborations ran.

    A bare share "under six months" reads as a shortfall, and there is no standard here
    to fall short of: most of these are volunteers and interns with a short term by
    design. So the share is only stated together with who held those roles; without
    roles the insight falls back to the most common length. In the 26 Oct 2026
    snapshot, 83 of the 93 short ones were volunteers (49) or interns (34). Computed
    rather than written into the description, so it stays true when the table changes.

    Only ended collaborations are binned — counting current members would censor every
    long one downwards.
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
    # Who the short ones were, when the roles say; otherwise the most common length.
    # One sentence either way: the card clips a summary at two lines.
    insight = _short_by_role(months, role)
    if not insight:
        most = max(range(len(values)), key=lambda i: values[i])
        insight = "%s of %s completed collaborations ran %s, the most common length." % (
            ins.num(values[most]), ins.num(total), labels[most].replace("> ", "over "),
        )
    out = metric(labels, values, insight)
    out["ordinal"] = True
    return out


def _short_by_role(months, role):
    """"N of T completed collaborations ran under six months: V volunteers, I interns."
    or "" when no role is recorded.

    `months` is indexed like the community table, so the roles line up by index. A
    person holding both roles counts in both, as everywhere roles are counted.
    """
    if role is None or len(role) == 0:
        return ""
    short = months[months < 6].index
    roles = [{r.strip().lower() for r in parse_multi(role.get(i))} for i in short]
    if not roles:
        return ""
    volunteers = sum("volunteer" in r for r in roles)
    interns = sum("intern" in r for r in roles)
    if not volunteers and not interns:
        return ""
    return "%s of %s completed collaborations ran under six months: %s volunteers, %s interns." % (
        ins.num(len(roles)), ins.num(len(months)), ins.num(volunteers), ins.num(interns))


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
        out["insight"] = ins.leader(out, "members")
    return out
