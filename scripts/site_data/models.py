"""Model Hub section — the Ersilia Model Hub's own numbers.

The Models table lives in a different Airtable base from everything else
(``appR6ZwgLgG8RTdoU`` / ``tblAfOWRbA7bI1VTB``) and was missing from the fetch
config entirely, so the site had nothing to say about Ersilia's flagship. The id
that *was* recorded elsewhere in the repo (``appgxpCzCDNyGjWc8``) 403s — it is
stale. Every builder here degrades to an empty metric when the table is absent,
so the site still renders before a fetch that includes it.
"""
from collections import Counter, defaultdict

import pandas as pd

from . import insights as ins
from .parse import (
    EMPTY,
    col,
    cumulative,
    dense_quarters,
    first_value,
    metric,
    multi_counts,
    parse_multi,
    quarter_counts,
    series_metric,
    value_counts,
)

# Curation states, in lifecycle order, so the stacked cohort chart reads
# left-to-right as progress rather than alphabetically.
STATUS_ORDER = ["Ready", "In progress", "In maintenance", "To do", "Test", "Archived"]

# Status -> house semantic token, so a state keeps one colour across the site.
STATUS_SEMANTICS = {
    "ready": "good",
    "in progress": "brand",
    "in maintenance": "warn",
    "to do": "neutral",
    "test": "neutral",
    "archived": "neutral",
}


def _ordered_statuses(present):
    known = [s for s in STATUS_ORDER if s in present]
    return known + sorted(s for s in present if s not in STATUS_ORDER)


def build(models):
    if models is None or models.empty:
        return {
            "cumulative": dict(EMPTY),
            "per_quarter": dict(EMPTY),
            "task_tree": {"tree": [], "n": 0},
            "cohorts_by_status": {"labels": [], "series": [], "n": 0},
            "by_status": dict(EMPTY),
            "by_biomedical_area": dict(EMPTY),
            "by_license": dict(EMPTY),
            "coverage": dict(EMPTY),
            "by_source_type": dict(EMPTY),
        }

    incorporated = col(models, "incorporation_date")
    quarters = quarter_counts(incorporated)
    dense = dense_quarters(quarters)

    labels = [str(i) for i in dense.index]
    running = list(dense.cumsum().values)
    cum = cumulative(
        quarters,
        ins.join(
            ins.span(labels, running, "models"),
            ins.busiest(labels, list(dense.values), "model", "models"),
        ),
    )
    cum["n"] = int(running[-1]) if running else 0
    per_quarter = metric(
        labels, dense.values,
        ins.latest_change(labels, list(dense.values), "models incorporated"),
    )

    status = col(models, "status").apply(first_value)
    by_status = value_counts(status, insight=None)
    ready = int((status.astype(str).str.strip().str.lower() == "ready").sum())
    by_status["insight"] = ins.share_of(ready, len(models), "models", "are ready to run")
    by_status["semantics"] = {
        label: STATUS_SEMANTICS.get(str(label).strip().lower(), "neutral")
        for label in by_status["labels"]
    }

    return {
        "cumulative": cum,
        "per_quarter": per_quarter,
        "task_tree": _task_tree(models),
        "cohorts_by_status": _cohorts_by_status(models, incorporated, status),
        "by_status": by_status,
        "by_biomedical_area": _by_biomedical_area(models),
        "by_license": _by_license(models),
        "coverage": _coverage(models),
        "by_source_type": _by_source_type(models),
    }


def _task_tree(models):
    """Two-level Task -> Subtask hierarchy for the sunburst.

    Both fields are single-valued, so every model lands on exactly one leaf and the
    leaf values sum to the model count. (Tag was the obvious candidate for the
    outer ring, but it is a multi-select — models would have been counted several
    times over and the ring would not have summed to anything meaningful.)
    """
    nested = defaultdict(Counter)
    task_col = col(models, "task")
    subtask_col = col(models, "subtask")
    for i in range(len(models)):
        task = (first_value(task_col.iloc[i]) if len(task_col) else None) or "Unspecified"
        subtask = (first_value(subtask_col.iloc[i]) if len(subtask_col) else None) or "Unspecified"
        nested[task][subtask] += 1

    tree = []
    for task, subtasks in sorted(nested.items(), key=lambda kv: -sum(kv[1].values())):
        tree.append({
            "name": task,
            "children": [
                {"name": subtask, "value": int(count)}
                for subtask, count in subtasks.most_common()
            ],
        })
    total = sum(sum(t.values()) for t in nested.values())
    leader = max(nested.items(), key=lambda kv: sum(kv[1].values())) if nested else None
    insight = None
    if leader:
        biggest_leaf = leader[1].most_common(1)[0]
        insight = "%s is the largest task family (%s of models); its biggest subtask is %s with %s." % (
            leader[0], ins.pct(sum(leader[1].values()), total),
            biggest_leaf[0], ins.num(biggest_leaf[1]),
        )
    return {"tree": tree, "n": int(total), "insight": insight}


def _by_biomedical_area(models):
    """What the Hub is actually for.

    This is the most mission-relevant cut available: Ersilia works on
    antimicrobial and antipathogen drug discovery for the Global South, and this
    field says how much of the Hub serves that versus general-purpose chemistry.
    A multi-select, so a model spanning two areas counts in both.
    """
    areas = col(models, "biomedical_area")
    out = multi_counts(areas, top=14)
    if not out["labels"]:
        return dict(EMPTY)
    counts = multi_counts(areas)
    generic = dict(zip(counts["labels"], counts["values"])).get("Any", 0)
    disease_specific = counts["n"] - generic
    out["insight"] = ins.join(
        ins.share_of(disease_specific, counts["n"], "area assignments",
                     "name a specific disease or property rather than 'Any'"),
        "Biomedical area is a multi-select, so a model spanning two areas counts in both.",
    )
    return out


def _by_source_type(models):
    """Whether a model was built in-house or wrapped from external work."""
    out = value_counts(col(models, "source_type").apply(first_value))
    if not out["labels"]:
        return dict(EMPTY)
    external = dict(zip(out["labels"], out["values"])).get("External", 0)
    out["insight"] = ins.share_of(external, sum(out["values"]), "models",
                                 "wrap externally published work rather than being built in-house")
    return out


def _cohorts_by_status(models, incorporated, status):
    """Incorporation quarter x curation status — is the backlog growing?"""
    dates = pd.to_datetime(incorporated, errors="coerce")
    valid = dates.notna()
    if not valid.any():
        return {"labels": [], "series": [], "n": 0}

    periods = dates[valid].dt.to_period("Q")
    states = status[valid].fillna("Unspecified").astype(str).str.strip()
    full = pd.period_range(periods.min(), periods.max(), freq="Q")
    present = _ordered_statuses(set(states.unique()))

    series = []
    for state in present:
        mask = states == state
        series.append({
            "name": state,
            "values": [int(((periods == q) & mask).sum()) for q in full],
        })

    not_ready = sum(
        sum(s["values"]) for s in series if s["name"].strip().lower() != "ready"
    )
    return series_metric(
        [str(q) for q in full], series,
        insight=ins.share_of(not_ready, int(valid.sum()), "incorporated models",
                             "are not yet marked ready"),
        n=int(valid.sum()),
        # Aligned to the series order, so "Ready" is the same green here as in the
        # status donut. Without this the two charts on this page gave one state
        # two different colours.
        semantics=[STATUS_SEMANTICS.get(s["name"].strip().lower(), "neutral") for s in series],
    )


def _by_license(models):
    licences = col(models, "license").apply(first_value)
    out = value_counts(licences, top=10)
    if out["labels"]:
        out["insight"] = ins.join(
            ins.leader(out, "models with a licence on file"),
            ins.share_of(int(licences.notna().sum()), len(models), "models", "record a licence"),
        )
    return out


def _coverage(models):
    """Deployment reach: how many models are actually runnable, and where.

    Presence of a value is the signal — an empty DockerHub cell means the model
    was never pushed there.
    """
    checks = [
        ("Docker image", "dockerhub"),
        ("S3 bundle", "s3"),
        ("Hosted API", "host_url"),
        ("Source code", "source_code"),
    ]
    labels, values = [], []
    for label, column in checks:
        series = col(models, column)
        if series.empty:
            continue
        filled = series.astype(str).str.strip()
        labels.append(label)
        values.append(int(((filled != "") & (filled.str.lower() != "nan")).sum()))
    if not labels:
        return dict(EMPTY)
    best = max(range(len(values)), key=lambda i: values[i])
    return metric(
        labels, values,
        insight="%s reaches the most models: %s of %s." % (
            labels[best], ins.num(values[best]), ins.num(len(models)),
        ),
    )
