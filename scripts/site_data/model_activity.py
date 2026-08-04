"""Aggregate activity across the Model Hub, joining Airtable, GitHub and Docker Hub.

WHY A JOIN, AND WHY IT LIVES HERE RATHER THAN IN AIRTABLE
--------------------------------------------------------
Three sources describe the same 240-odd models and none of them can answer a question
about the Hub as a whole:

    Airtable `models`   curated judgement — task, biomedical area, status, licence
    data/github/        activity — commits, pull requests, issues, releases, last push
    data/dockerhub/     pull counts

They key on the same identifier (`eosXXXX`), so joining them is trivial and the result is
worth having: **237 of 243 models resolve in all three.** The two absent from GitHub are
`eos6ru5` and `eos6wdw`, both `In progress`.

These statistics are **derived, so they are not stored in Airtable.** Airtable holds facts
a person decided; this holds facts a script computed from committed snapshots. Writing them
back would create a third copy to keep in sync, and the numbers would start disagreeing
with the snapshots they came from the moment either side moved. The join happens at build
time and is deliberately not persisted for the same reason.

WHAT THIS DOES NOT REPORT, AND WHY — measured, then rejected
------------------------------------------------------------
**Effort per model by incorporation year.** Raw median commits fall from 60 for the 2021
cohort to 30 for 2026, which reads as declining effort. Normalising by months since
incorporation inverts it completely — 1.03 to 10.06 commits per month. Both are artefacts
of exposure: a model's commits arrive in a burst around packaging, so a recent model has all
of them inside a short window and an old one has the same burst spread over years. Neither
number measures effort, so neither is published. An honest version would count commits
inside a fixed window after incorporation, which needs a longer quarterly history than the
twelve quarters collected.

**Effort by biomedical area.** Median commits run 35 (antimicrobial resistance) to 55
(ADMET), on groups as small as eight, and confounded by cohort age. Too weak to publish.

**Pull counts against commits.** Spearman 0.52 across 237 models, which looks like
"attention follows effort" and almost certainly is not: continuous integration pulls every
image on every build, so a repository with more commits gets more builds and therefore more
pulls. It measures the build schedule. `usage.py` already establishes that the pull baseline
is CI; this would quietly contradict it.
"""
import re

from . import insights as ins
from .parse import EMPTY, as_text, growth_pair, metric, to_num

MODEL_RE = re.compile(r"^eos[0-9][0-9a-z]{3}$")

EMPTY_SECTION = {
    "hub_commit_growth": {"labels": [], "series": [], "n": 0},
    "maintenance": dict(EMPTY),
    "outside_contribution": dict(EMPTY),
    "most_active_models": {"rows": [], "n": 0},
}


def build(models, collected, today=None):
    collected = collected or {}
    repos = collected.get("github_repos")
    if repos is None or repos.empty or "name" not in repos.columns:
        return dict(EMPTY_SECTION)

    model_rows = _model_repos(repos)
    if not model_rows:
        return dict(EMPTY_SECTION)

    return {
        "hub_commit_growth": _commit_growth(collected.get("github_commit_activity")),
        "maintenance": _maintenance(model_rows, today),
        "outside_contribution": _outside_contribution(model_rows),
        "most_active_models": _most_active(model_rows, collected, models),
    }


def _model_repos(repos):
    """`[{column: value}]` for the per-model repositories only."""
    flag = as_text(repos.get("is_model")).str.lower()
    out = []
    for i in range(len(repos)):
        name = str(repos["name"].iloc[i] or "").strip()
        if not name or flag.iloc[i] != "yes":
            continue
        out.append({c: repos[c].iloc[i] for c in repos.columns})
    return out


def _int(row, key):
    raw = str(row.get(key, "")).strip()
    if raw in ("", "nan"):
        return None
    try:
        return int(float(raw))
    except ValueError:
        return None


def _quarter_key(label):
    try:
        year, quarter = str(label).split("Q")
        return (int(year), int(quarter))
    except (ValueError, AttributeError):
        return (0, 0)


def _commit_growth(activity):
    """Commits to model repositories per quarter, with the running total.

    Separate from the organisation-wide series on the Code page, because this answers a
    different question: how much work is going into the Hub itself, as against Ersilia's
    tooling. The two are collected in the same pass and simply filtered differently.
    """
    if activity is None or activity.empty:
        return {"labels": [], "series": [], "n": 0}
    label_col = "week_start" if "week_start" in activity.columns else "quarter"
    if label_col not in activity.columns or "commits" not in activity.columns:
        return {"labels": [], "series": [], "n": 0}

    names = as_text(activity["name"])
    labels_raw = as_text(activity[label_col])
    values = to_num(activity["commits"])
    counts = {}
    for i in range(len(activity)):
        if not MODEL_RE.match(names.iloc[i].strip()):
            continue
        label = labels_raw.iloc[i].strip()
        if label:
            counts[label] = counts.get(label, 0) + int(values.iloc[i] or 0)
    if not counts:
        return {"labels": [], "series": [], "n": 0}

    labels = sorted(counts, key=_quarter_key)
    per_quarter = [counts[q] for q in labels]
    running, total = [], 0
    for value in per_quarter:
        total += value
        running.append(total)
    return growth_pair(
        labels, per_quarter, running, "commits",
        insight="%s commits to model repositories across %d quarters. %s" % (
            ins.num(total), len(labels),
            ins.busiest(labels, per_quarter, "commit", "commits"),
        ),
    )


def _maintenance(model_rows, today):
    """Model repositories by the YEAR of their last push.

    The question this answers is the one a sceptic asks about any large model collection:
    is most of it abandoned? By year rather than by elapsed-time band because the answer is
    stark enough that bands would blur it — the great majority were touched this year.
    """
    import pandas as pd

    now = pd.Timestamp(today) if today is not None else pd.Timestamp.today().normalize()
    counts = {}
    archived = 0
    for row in model_rows:
        if str(row.get("archived", "")).strip().lower() == "yes":
            archived += 1
            continue
        pushed = str(row.get("pushed_at", "")).strip()[:4]
        if len(pushed) == 4 and pushed.isdigit():
            counts[pushed] = counts.get(pushed, 0) + 1
    if not counts:
        return dict(EMPTY)

    labels = sorted(counts)
    values = [counts[y] for y in labels]
    if archived:
        labels.append("archived")
        values.append(archived)
    current = str(now.year)
    this_year = counts.get(current, 0)
    total = sum(values)
    out = metric(
        labels, values,
        "%s of %s model repositories were pushed to in %s — the Hub is maintained rather "
        "than archived." % (ins.num(this_year), ins.num(total), current),
        countNoun="model repositories",
        n=total,
    )
    out["ordinal"] = True
    return out


def _outside_contribution(model_rows):
    """How many models have had a merged pull request from outside the organisation.

    Per MODEL rather than per pull request, and that is the point. "78% of merged pull
    requests are external" could in principle be a handful of models attracting all the
    outside work; this counts the models themselves, so it measures how far into the Hub
    community contribution actually reaches.

    Only the most recent 30 merged pull requests per repository are sampled, so a model
    whose only outside contribution is older than that reads as internal. The figure is
    therefore a floor.
    """
    outside = internal = none = 0
    for row in model_rows:
        sampled, external = _int(row, "prs_sampled"), _int(row, "prs_external")
        if not sampled:
            none += 1
        elif external:
            outside += 1
        else:
            internal += 1
    total = outside + internal + none
    if not total:
        return dict(EMPTY)
    return metric(
        ["Has an outside contribution", "Only internal pull requests",
         "No merged pull requests"],
        [outside, internal, none],
        "%s of %s models have taken a merged pull request from outside Ersilia." % (
            ins.num(outside), ins.num(total),
        ),
        countNoun="models",
        n=total,
    )


def _most_active(model_rows, collected, models):
    """The busiest model repositories, with the pull count beside the work.

    THE PAYOFF OF THE JOIN: commits, pull requests and issues come from GitHub, pulls from
    Docker Hub, and the row exists only because both key on the same identifier. Pulls are
    shown as a column rather than a ranking so that no relationship is implied between
    them — see the module docstring on why the correlation is not published.
    """
    pulls = {}
    images = collected.get("dockerhub_images")
    if images is not None and not images.empty and "name" in images.columns:
        flag = as_text(images.get("is_model")).str.lower()
        counts = to_num(images.get("pull_count"))
        for i in range(len(images)):
            if flag.iloc[i] == "yes":
                pulls[str(images["name"].iloc[i]).strip()] = int(counts.iloc[i] or 0)

    titles = {}
    if models is not None and not models.empty and "identifier" in models.columns:
        has_title = "title" in models.columns
        for i in range(len(models)):
            key = str(models["identifier"].iloc[i] or "").strip()
            if key and has_title:
                titles[key] = str(models["title"].iloc[i] or "").strip()

    rows = []
    for row in model_rows:
        name = str(row.get("name", "")).strip()
        commits = _int(row, "total_commits")
        if commits is None:
            continue
        rows.append({
            "name": name,
            "title": titles.get(name, "") or name,
            "total_commits": commits,
            "merged_prs": _int(row, "merged_prs") or 0,
            "closed_issues": _int(row, "closed_issues") or 0,
            "pulls": pulls.get(name, 0),
        })
    if not rows:
        return {"rows": [], "n": 0}
    rows.sort(key=lambda r: (-r["total_commits"], r["name"]))
    total = sum(r["total_commits"] for r in rows)
    return {
        "rows": rows[:10],
        "n": len(rows),
        "insight": "%s commits across %s model repositories; the busiest carries %s." % (
            ins.num(total), ins.num(len(rows)), ins.num(rows[0]["total_commits"]),
        ),
    }
