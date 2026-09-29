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
    as_text,
    col,
    cumulative,
    dense_quarters,
    first_value,
    growth_pair,
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
            "by_target_organism": dict(EMPTY),
            "publication_lag": dict(EMPTY),
            "performance_by_scale": {"labels": [], "series": [], "n": 0},
            "image_size": dict(EMPTY),
            "on_arm": dict(EMPTY),
            "licence_openness": dict(EMPTY),
            "output_consistency": dict(EMPTY),
            "publication_type": dict(EMPTY),
            "growth": {"labels": [], "series": [], "n": 0},
            "task_by_area": {"x": [], "y": [], "cells": [], "n": 0},
            "image_composition": {"labels": [], "series": [], "n": 0},
            "top_contributors": dict(EMPTY),
            "contributor_concentration": dict(EMPTY),
            "template_migration": dict(EMPTY),
        }

    incorporated = col(models, "incorporation_date")
    quarters = quarter_counts(incorporated)
    dense = dense_quarters(quarters)

    labels = [str(i) for i in dense.index]
    running = list(dense.cumsum().values)
    cum = cumulative(quarters, ins.span(labels, running, "models"))
    cum["n"] = int(running[-1]) if running else 0
    per_quarter = metric(
        labels, dense.values,
        ins.latest_change(labels, list(dense.values), "models incorporated"),
    )

    status = col(models, "status").apply(first_value)
    by_status = value_counts(status, insight=None)
    ready = int((as_text(status).str.lower() == "ready").sum())
    by_status["insight"] = ins.share_of(ready, len(models), "models", "are ready to run")
    by_status["semantics"] = {
        label: STATUS_SEMANTICS.get(str(label).strip().lower(), "neutral")
        for label in by_status["labels"]
    }

    return {
        "cumulative": cum,
        "per_quarter": per_quarter,
        # Rate and running total on one shared axis, so "how fast" and "how many"
        # are never a click apart.
        "growth": growth_pair(labels, list(dense.values), running, "models"),
        "task_tree": _task_tree(models),
        "by_target_organism": _by_target_organism(models),
        "publication_lag": _publication_lag(models, incorporated),
        "performance_by_scale": _performance_by_scale(models),
        "image_size": _image_size(models),
        "on_arm": _on_arm(models),
        "cohorts_by_status": _cohorts_by_status(incorporated, status),
        "by_status": by_status,
        "by_biomedical_area": _by_biomedical_area(models),
        "by_license": _by_license(models),
        "licence_openness": _licence_openness(models),
        "coverage": _coverage(models),
        "by_source_type": _by_source_type(models),
        "output_consistency": _output_consistency(models),
        "publication_type": _publication_type(models),
        "task_by_area": _task_by_area(models),
        "image_composition": _image_composition(models),
        "top_contributors": _top_contributors(models),
        "contributor_concentration": _contributor_concentration(models),
        "template_migration": _template_migration(models),
    }


def _output_consistency(models):
    """Does the model return the same answer twice?

    THE MOST IMPORTANT PROPERTY ON THIS PAGE, and it was not shown anywhere. Everything
    else here describes what a model is *for*; this describes whether you can rely on what
    it says. A `Variable` model gives a different answer on a re-run — legitimate for a
    generative model that samples, and a problem for a property predictor — so the figure is
    reported without a verdict attached to it.

    A near-binary field: 215 `Fixed` against 18 `Variable`, recorded for 233 of 243 models.
    """
    values = col(models, "output_consistency").apply(first_value)
    out = value_counts(values)
    if not out["labels"]:
        return dict(EMPTY)
    recorded = int(values.notna().sum())
    fixed = 0
    for label, value in zip(out["labels"], out["values"]):
        if str(label).strip().lower() == "fixed":
            fixed = int(value)
    out["insight"] = ins.share_of(fixed, recorded, "models with a value",
                                 "give the same answer on a re-run")
    # `Fixed` is the reproducible case and reads as the good one; `Variable` is not a
    # failure, so it takes a neutral rather than a warning colour.
    out["semantics"] = {"Fixed": "brand", "Variable": "neutral"}
    return out


def _publication_type(models):
    """Was the science behind the model peer-reviewed?

    Provenance rather than popularity, and the counterpart to `by_source_type`: that says
    whether Ersilia wrapped somebody else's work, this says how well established that work
    is. 172 peer-reviewed, 25 preprints, 36 other across 233 recorded.
    """
    values = col(models, "publication_type").apply(first_value)
    out = value_counts(values)
    if not out["labels"]:
        return dict(EMPTY)
    recorded = int(values.notna().sum())
    reviewed = 0
    for label, value in zip(out["labels"], out["values"]):
        if "peer" in str(label).strip().lower():
            reviewed = int(value)
    # Four columns wide: keep it to one clause.
    out["insight"] = ins.share_of(reviewed, recorded, "models with a recorded type",
                                 "are peer-reviewed")
    return out


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
    unrecorded = 0
    for i in range(len(models)):
        task = first_value(task_col.iloc[i]) if len(task_col) else None
        if not task:
            # Models with no task recorded are left OUT rather than given an
            # "Unspecified" family: as a block it was too small to label and rendered
            # as a slice of colour at the edge captioned "Un". The count is stated in
            # the caption instead, which is honest and legible.
            unrecorded += 1
            continue
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
        insight = "%s is the largest task family, %s of the %s with a task recorded." % (
            leader[0], ins.pct(sum(leader[1].values()), total), ins.num(total),
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
    out["insight"] = ins.share_of(disease_specific, counts["n"], "area assignments",
                                  "name a specific disease rather than 'Any'")
    return out


def _by_target_organism(models):
    """Which pathogens the Hub can say something about.

    The most mission-relevant field in the table and it was going unread. Ersilia
    works on antimicrobial and antipathogen drug discovery, and this names the actual
    organisms.

    ``Any`` (133 models) and ``Homo sapiens`` (41) are EXCLUDED deliberately. Both
    are true answers and both would dominate the ranking while saying nothing about
    pathogen coverage: "Any" means the model is organism-agnostic chemistry, and
    Homo sapiens means it predicts a human property (toxicity, permeability) rather
    than acting on a pathogen. What is left is the pathogen-specific Hub.
    """
    NOT_A_PATHOGEN = {"any", "homo sapiens"}
    counts = Counter()
    organisms = col(models, "target_organism")
    for value in organisms.dropna() if len(organisms) else []:
        for token in parse_multi(value):
            if token.strip().lower() not in NOT_A_PATHOGEN:
                counts[token.strip()] += 1
    if not counts:
        return dict(EMPTY)
    items = counts.most_common(12)
    out = metric([k for k, _ in items], [v for _, v in items])
    out["n"] = sum(counts.values())
    out["insight"] = "%s models target a named pathogen; %s leads with %s." % (
        ins.num(sum(counts.values())), items[0][0], ins.num(items[0][1]),
    )
    return out


def _task_by_area(models):
    """Coverage: task family x biomedical area, crossed.

    The task-tree and biomedical-area charts above answer "what" and "for what disease"
    separately and never together. Task is single-valued, so every model with one recorded
    contributes to exactly one row; biomedical area is multi-select, so a model naming two
    areas contributes to both columns it touches. Capped to the 8 largest task families and
    10 largest areas so the matrix stays legible.
    """
    task_col = col(models, "task")
    area_col = col(models, "biomedical_area")
    if task_col.empty or area_col.empty:
        return {"x": [], "y": [], "cells": [], "n": 0}

    cross, task_totals, area_totals = Counter(), Counter(), Counter()
    n = 0
    for i in range(len(models)):
        task = first_value(task_col.iloc[i]) if i < len(task_col) else None
        if not task:
            continue
        areas = parse_multi(area_col.iloc[i]) if i < len(area_col) else []
        for area in areas:
            cross[(task, area)] += 1
            task_totals[task] += 1
            area_totals[area] += 1
            n += 1
    if not cross:
        return {"x": [], "y": [], "cells": [], "n": 0}

    tasks = [t for t, _ in task_totals.most_common(8)]
    areas = [a for a, _ in area_totals.most_common(10)]
    cells = [
        [xi, yi, cross[(task, area)]]
        for yi, task in enumerate(tasks)
        for xi, area in enumerate(areas)
        if cross.get((task, area))
    ]
    top_task, top_count = task_totals.most_common(1)[0]
    return {
        "x": areas, "y": tasks, "cells": cells, "n": n,
        "insight": "%s task-area pairings recorded across %s task families and %s biomedical "
                   "areas; %s leads with %s." % (
                       ins.num(n), len(tasks), len(areas), top_task, ins.num(top_count),
                   ),
    }


def _publication_lag(models, incorporated):
    """How long a published model waits before Ersilia wraps it.

    This is the Hub's responsiveness to the literature, and it is the kind of number
    that only exists once you subtract two columns nobody had subtracted.

    Rows where the incorporation year precedes the stated publication year are
    dropped (3 of them) — a negative lag means one of the two dates is wrong, not
    that Ersilia wrapped a paper before it existed.
    """
    years = pd.to_numeric(col(models, "publication_year"), errors="coerce")
    dates = pd.to_datetime(incorporated, errors="coerce")
    if years.empty or dates.empty:
        return dict(EMPTY)
    lag = (dates.dt.year - years).dropna()
    lag = lag[lag >= 0]
    if lag.empty:
        return dict(EMPTY)

    # Open-ended top bin: the tail runs to 33 years and fixed-width bins would be
    # almost all empty. The en dash and the "+" are load-bearing — optHistogram
    # parses them to place the mean rule.
    bins = [(0, 1, "0"), (1, 2, "1"), (2, 3, "2"), (3, 5, "3–4"),
            (5, 10, "5–9"), (10, float("inf"), "10+")]
    labels, values = [], []
    for low, high, label in bins:
        labels.append(label)
        values.append(int(((lag >= low) & (lag < high)).sum()))
    same_year = int((lag == 0).sum())
    return metric(
        labels, values,
        "%s of %s wrapped the same year; mean wait %s years." % (
            ins.num(same_year), ins.num(len(lag)), round(float(lag.mean()), 1)),
        mean=round(float(lag.mean()), 1),
        median=round(float(lag.median()), 1),
        # No `unit`: the card's title already says "Years", and six bins in a span-4
        # card have no room for a suffix — "5–9" ran into "10+ years".
        countNoun="models",
        n=len(lag),
    )


# The five Computational Performance columns are runtimes (seconds) at increasing
# batch sizes. Plain numeric strings, not "1 input" — the chart parses these back
# into numbers for a log-scale axis, so anything non-numeric would drop off it.
SCALE_STEPS = [
    ("1", "computational_performance_1"),
    ("10", "computational_performance_2"),
    ("100", "computational_performance_3"),
    ("1,000", "computational_performance_4"),
    ("10,000", "computational_performance_5"),
]


def _performance_by_scale(models):
    """Runtime at each batch size the Hub benchmarks: 1, 10, 100, 1,000 and 10,000
    molecules in one call, as a median with its 25th-75th percentile band — the same
    plot entry_project draws (median line, shaded IQR, log-log axes).

    A value of ``-1`` in a Computational Performance column means the model FAILED
    at that size, so it is excluded from the runtime figures rather than counted as
    an instant run — a real effect here, not a theoretical one: 74 of 234 models
    (32%) fail at the largest size, and leaving ``-1`` in would drag the median
    toward zero rather than showing the runtime of the models that actually
    completed. Models drop out of later batch sizes as they fail, so the sample
    shrinks left to right; the count benchmarked at each size is in the drill-down.
    """
    labels, medians, p25s, p75s, counts = [], [], [], [], []
    for label, column in SCALE_STEPS:
        values = pd.to_numeric(col(models, column), errors="coerce")
        values = values[values > 0]
        if values.empty:
            continue
        labels.append(label)
        medians.append(round(float(values.median()), 4))
        p25s.append(round(float(values.quantile(0.25)), 4))
        p75s.append(round(float(values.quantile(0.75)), 4))
        counts.append(int(values.count()))
    if not labels:
        return {"labels": [], "series": [], "n": 0}

    out = series_metric(
        labels,
        [{"name": "p25", "values": p25s},
         {"name": "Median runtime (s)", "values": medians},
         {"name": "p75", "values": p75s}],
        "Median runtime goes from %ss at %s molecule to %ss at %s molecules — %s "
        "models still completing a run there." % (
            _fmt_seconds(medians[0]), labels[0], _fmt_seconds(medians[-1]), labels[-1],
            ins.num(counts[-1]),
        ),
    )
    out["n"] = counts[-1]
    return out


def _fmt_seconds(value):
    if value < 1:
        return "%.3f" % value
    if value < 10:
        return "%.2f" % value
    return "%.1f" % value


def _image_size(models):
    """How heavy a model is to pull and run — the low-resource deployment question."""
    sizes = pd.to_numeric(col(models, "image_size"), errors="coerce").dropna()
    sizes = sizes[sizes > 0]
    if sizes.empty:
        return dict(EMPTY)
    gb = sizes / 1024.0
    bins = [(0, 1, "0–1"), (1, 2, "1–2"), (2, 4, "2–4"),
            (4, 8, "4–8"), (8, float("inf"), "8+")]
    labels, values = [], []
    for low, high, label in bins:
        labels.append(label)
        values.append(int(((gb >= low) & (gb < high)).sum()))
    under_two = int((gb < 2).sum())
    return metric(
        labels, values,
        "%s of %s images are under 2 GB; mean %s GB." % (
            ins.num(under_two), ins.num(len(gb)), round(float(gb.mean()), 1)),
        mean=round(float(gb.mean()), 1),
        unit="GB",
        countNoun="models",
        n=len(gb),
    )


def _on_arm(models):
    """ARM64 coverage: whether a model runs on cheap and low-power hardware.

    Two categories so it can drive a share row. Every model records AMD64, so AMD64
    alone is the uninteresting case; ARM64 is the one that says something.
    """
    arch = col(models, "docker_architecture")
    if arch.empty:
        return dict(EMPTY)
    with_arch, on_arm = 0, 0
    for value in arch.dropna():
        tokens = {t.strip().upper() for t in parse_multi(value)}
        if not tokens:
            continue
        with_arch += 1
        if "ARM64" in tokens:
            on_arm += 1
    if not with_arch:
        return dict(EMPTY)
    return metric(
        ["ARM64 and AMD64", "AMD64 only"], [on_arm, with_arch - on_arm],
        ins.share_of(on_arm, with_arch, "models with a recorded architecture",
                     "also build for ARM64"),
        n=with_arch,
    )


def _image_composition(models):
    """Model weights vs. installed environment vs. everything else, for the heaviest images.

    A packaging-efficiency question `_image_size`'s distribution doesn't break down: how much
    of an image is the checkpoint itself against the environment it runs in. All three sizes
    are recorded in the same unit (MB), so no conversion is needed. "Other" folds in the base
    OS layer, package caches and anything else the two named parts don't account for; it is
    clipped at zero rather than shown negative, since a negative would mean the two recorded
    parts overstate the whole rather than something real.
    """
    image = pd.to_numeric(col(models, "image_size"), errors="coerce")
    weight = pd.to_numeric(col(models, "model_size"), errors="coerce")
    env = pd.to_numeric(col(models, "environment_size"), errors="coerce")
    if image.empty or weight.empty or env.empty:
        return {"labels": [], "series": [], "n": 0}

    title = as_text(col(models, "title"))
    identifier = as_text(col(models, "identifier"))
    label = title.where(title != "", identifier)

    df = pd.DataFrame({"image": image, "weight": weight, "env": env, "label": label}).dropna(
        subset=["image", "weight", "env"]
    )
    df = df[(df["image"] > 0) & (df["weight"] >= 0) & (df["env"] >= 0)]
    if df.empty:
        return {"labels": [], "series": [], "n": 0}
    df["other"] = (df["image"] - df["weight"] - df["env"]).clip(lower=0)
    top = df.sort_values("image", ascending=False).head(12)

    out = series_metric(
        list(top["label"]),
        [
            {"name": "Model weights", "values": [round(v, 1) for v in top["weight"]]},
            {"name": "Environment", "values": [round(v, 1) for v in top["env"]]},
            {"name": "Other", "values": [round(v, 1) for v in top["other"]]},
        ],
        "Environment accounts for %s of uncompressed image size, across the %s models that "
        "record model, environment and image size together — the heaviest %s shown here." % (
            ins.pct(int(df["env"].sum()), int(df["image"].sum())) or "n/a", len(df), len(top),
        ),
    )
    out["n"] = len(df)
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


def _cohorts_by_status(incorporated, status):
    """Incorporation quarter x curation status — is the backlog growing?"""
    dates = pd.to_datetime(incorporated, errors="coerce")
    valid = dates.notna()
    if not valid.any():
        return {"labels": [], "series": [], "n": 0}

    periods = dates[valid].dt.to_period("Q")
    states = as_text(status[valid]).replace("", "Unspecified")
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


# A permissive licence imposes no condition on a downstream user beyond attribution.
# For a model hub the distinction is practical rather than ideological: it decides who can
# build on a model, and whether they can ship the result.
#
# The two exclusions matter and were both caught misclassifying real rows. A prefix test
# alone put CC-BY-NC-ND-4.0 in the permissive bucket, when non-commercial plus
# no-derivatives is the MOST restrictive Creative Commons combination there is — the
# opposite of the claim. And "Proprietary" is not copyleft; it is not a share-alike
# obligation but a closed licence, so the other bucket cannot be called "Copyleft"
# either. It is "Conditions apply", which is true of all of GPL, AGPL, LGPL,
# proprietary and the NC/ND variants.
PERMISSIVE_LICENCES = ("mit", "apache", "bsd", "isc", "unlicense", "cc0", "cc-by")
RESTRICTIVE_MARKERS = ("-nc", "-nd")


def _is_permissive(licence):
    text = licence.lower()
    if not text.startswith(PERMISSIVE_LICENCES):
        return False
    return not any(marker in text for marker in RESTRICTIVE_MARKERS)


def _licence_openness(models):
    """Permissive against copyleft, over the models that record a licence at all.

    Two categories so it can sit as a row in the "how the Hub is built" share card.
    Models with no licence recorded are excluded from the ratio and named in the caption
    rather than folded into either side — an unrecorded licence is not a permissive one,
    and for a reuser it is the most restrictive state of all.
    """
    licences = col(models, "license").apply(first_value)
    if licences.empty:
        return dict(EMPTY)
    text = as_text(licences).str.lower()
    recorded = text[text != ""]
    if recorded.empty:
        return dict(EMPTY)
    permissive = int(recorded.apply(_is_permissive).sum())
    total = len(recorded)
    unrecorded = int(len(text) - total)
    return metric(
        ["Permissive", "Conditions apply"], [permissive, total - permissive],
        ins.join(
            ins.share_of(permissive, total, "models with a licence on file",
                         "carry a permissive licence"),
            "%s record no licence." % ins.num(unrecorded) if unrecorded else None,
        ),
        n=total,
    )


def _by_license(models):
    licences = col(models, "license").apply(first_value)
    out = value_counts(licences, top=10)
    if out["labels"]:
        out["insight"] = ins.leader(out, "licensed models")
    return out


def _coverage(models):
    """Deployment reach: how many models are actually runnable, and where.

    Presence of a value is the signal — an empty DockerHub cell means the model
    was never pushed there.
    """
    # No "Hosted API" row: it used to look for a `host_url` column that does not
    # exist in the table, so the meter was silently absent from every build. The
    # nearest real field is `deployment`, but it is Local for 233 of 236 models —
    # no variance, nothing to show.
    checks = [
        ("Docker image", "dockerhub"),
        ("S3 bundle", "s3"),
        ("Source code", "source_code"),
    ]
    labels, values = [], []
    for label, column in checks:
        series = col(models, column)
        if series.empty:
            continue
        filled = as_text(series)
        labels.append(label)
        values.append(int(((filled != "") & (filled.str.lower() != "nan")).sum()))
    if not labels:
        return dict(EMPTY)
    best = max(range(len(values)), key=lambda i: values[i])
    return metric(
        labels, values,
        # Short on purpose: this lands in a 3-column card, where a longer sentence is
        # clipped by the one-line caption clamp.
        insight="%s reaches the most models: %s of %s." % (
            labels[best], ins.num(values[best]), ins.num(len(models)),
        ),
        # The whole is every model, so the meters can show a real percentage.
        total=len(models),
    )


def _top_contributors(models):
    """People credited with incorporating a model, by how many they've done.

    `Contributor` records the GitHub handle of whoever wrapped the model — the same kind of
    public identifier already published for commit authorship elsewhere on the site (see
    `repositories.py`'s `_top_contributors`), not a narrative name field. Multi-select, so a
    model credited to two people counts for both.
    """
    out = multi_counts(col(models, "contributor"), top=12)
    if not out["labels"]:
        return dict(EMPTY)
    out["insight"] = ins.leader(out, "models incorporated")
    return out


def _contributor_concentration(models):
    """Lorenz curve of models incorporated per contributor — the bus-factor question for
    the Hub's own incorporation work, alongside `repositories.py`'s equivalent for commits.

    x = cumulative share of contributors (least active first), y = cumulative share of
    models incorporated. A curve hugging the bottom-right means a handful of people have
    done almost all of the incorporation.
    """
    counts = Counter()
    for value in col(models, "contributor").dropna():
        for name in parse_multi(value):
            name = name.strip()
            if name:
                counts[name] += 1
    if not counts:
        return dict(EMPTY)

    ordered = sorted(counts.values())
    total = sum(ordered)
    labels, values, running = ["0"], [0.0], 0
    for index, value in enumerate(ordered, start=1):
        running += value
        labels.append(str(round(100.0 * index / len(ordered), 1)))
        values.append(round(100.0 * running / total, 1))
    # Gini via the trapezoid area under the Lorenz curve.
    area = 0.0
    for i in range(1, len(values)):
        width = (float(labels[i]) - float(labels[i - 1])) / 100.0
        area += width * (values[i] + values[i - 1]) / 200.0
    gini = round(max(0.0, min(1.0, 1 - 2 * area)), 2)
    top_decile = sum(ordered[-max(1, len(ordered) // 10):])
    return metric(
        labels, values,
        "The busiest 10%% of contributors have incorporated %s of all credited models "
        "(Gini %s)." % (ins.pct(top_decile, total), gini),
        gini=gini, unit="% of models", n=len(ordered),
    )


def _template_migration(models):
    """Whether a model repository declares its Python version and dependencies via
    ``install.yml`` — the current ersilia-model-template — or still carries them
    baked into its Dockerfile, the legacy layout every model shipped with before it.

    `install_python_version` is read straight off ``install.yml`` at collection
    time; a blank cell means the file was never found, not that the version is
    literally unset.
    """
    versions = col(models, "install_python_version")
    if versions.empty:
        return dict(EMPTY)
    has = as_text(versions)
    has = has[(has != "") & (has.str.lower() != "nan")]
    current = len(has)
    total = len(models)
    if not total:
        return dict(EMPTY)
    return metric(
        ["Current template (install.yml)", "Legacy template (deps in Dockerfile)"],
        [current, total - current],
        ins.share_of(current, total, "model repositories",
                     "declare their Python version and dependencies via install.yml"),
        n=total,
    )
