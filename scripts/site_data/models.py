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
            "scaling_limit": dict(EMPTY),
            "image_size": dict(EMPTY),
            "on_arm": dict(EMPTY),
            "licence_openness": dict(EMPTY),
            "output_consistency": dict(EMPTY),
            "publication_type": dict(EMPTY),
            "growth": {"labels": [], "series": [], "n": 0},
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
        "scaling_limit": _scaling_limit(models),
        "image_size": _image_size(models),
        "on_arm": _on_arm(models),
        "cohorts_by_status": _cohorts_by_status(models, incorporated, status),
        "by_status": by_status,
        "by_biomedical_area": _by_biomedical_area(models),
        "by_license": _by_license(models),
        "licence_openness": _licence_openness(models),
        "coverage": _coverage(models),
        "by_source_type": _by_source_type(models),
        "output_consistency": _output_consistency(models),
        "publication_type": _publication_type(models),
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
    out["insight"] = ins.share_of(reviewed, recorded, "models",
                                 "are based on peer-reviewed work")
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
        unit="years",
        countNoun="models",
        n=int(len(lag)),
    )


# The five Computational Performance columns are runtimes at increasing input sizes.
SCALE_STEPS = [
    ("1 input", "computational_performance_1"),
    ("10", "computational_performance_2"),
    ("100", "computational_performance_3"),
    ("1,000", "computational_performance_4"),
    ("10,000", "computational_performance_5"),
]


def _scaling_limit(models):
    """The largest batch each model actually completed.

    DERIVED, NOT RECORDED, and the derivation rests on one convention: a value of
    ``-1`` in a Computational Performance column means the model FAILED at that
    input size. So the largest column holding a positive number is the largest batch
    the model got through. This is stated in Methods because a reader cannot infer
    it from the chart.
    """
    present = [(label, column) for label, column in SCALE_STEPS
               if not col(models, column).empty]
    if not present:
        return dict(EMPTY)
    numeric = [(label, pd.to_numeric(col(models, column), errors="coerce"))
               for label, column in present]

    counts = Counter()
    for i in range(len(models)):
        best = None
        for label, series in numeric:
            value = series.iloc[i] if i < len(series) else None
            if pd.notna(value) and value > 0:
                best = label
        if best is not None:
            counts[best] += 1
    if not counts:
        return dict(EMPTY)

    labels = [label for label, _ in numeric if label in counts]
    values = [counts[label] for label in labels]
    total = sum(values)
    top = labels[-1]
    out = metric(
        labels, values,
        "%s of %s reached the largest batch, %s inputs." % (
            ins.num(counts[top]), ins.num(total), top),
        n=total,
    )
    out["ordinal"] = True
    return out


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
        n=int(len(gb)),
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
    total = int(len(recorded))
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
        total=int(len(models)),
    )
