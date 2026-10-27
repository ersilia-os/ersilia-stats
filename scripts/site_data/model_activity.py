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
from . import insights as ins
from .code import quarter_commits
from .parse import (EMPTY, as_text, col, growth_pair, metric, quarter_totals,
                    to_num)

EMPTY_SECTION = {
    "hub_commit_growth": {"labels": [], "series": [], "n": 0},
    "outside_contribution": dict(EMPTY),
    "most_active_models": {"rows": [], "n": 0},
    "image_freshness": dict(EMPTY),
    "request_lead_time": dict(EMPTY),
    "requests_growth": {"labels": [], "series": [], "n": 0},
}


def build(models, collected):
    collected = collected or {}
    out = dict(EMPTY_SECTION)
    # From the flagship repository's issues, not the per-model repositories the rest
    # of this function joins against, so it populates independently of them.
    out["request_lead_time"] = _request_lead_time(collected)
    out["requests_growth"] = _requests_growth(collected)

    repos = collected.get("github_repos")
    if repos is None or repos.empty or "name" not in repos.columns:
        return out

    model_rows = _model_repos(repos)
    if not model_rows:
        return out

    model_names = {str(r.get("name", "")).strip() for r in model_rows}
    out.update({
        "hub_commit_growth": _commit_growth(
            collected.get("github_commit_activity"), model_names),
        "outside_contribution": _outside_contribution(model_rows),
        "most_active_models": _most_active(model_rows, collected, models),
        "image_freshness": _image_freshness(collected),
    })
    return out


def _request_lead_time(collected):
    """Days from a model-request issue opening to closing, for CLOSED requests only.

    Bucketed the same way entry_project's prototype did: lead times run from hours
    to years, so a linear scale would flatten the whole picture into one bar near
    zero. An open request has no lead time yet, so it is excluded rather than
    counted as zero.
    """
    requests = (collected or {}).get("github_model_requests")
    if requests is None or requests.empty or "state" not in requests.columns:
        return dict(EMPTY)

    import pandas as pd

    closed = requests[as_text(requests["state"]).str.lower() == "closed"]
    if closed.empty:
        return dict(EMPTY)
    created = pd.to_datetime(col(closed, "created_at"), errors="coerce")
    closed_at = pd.to_datetime(col(closed, "closed_at"), errors="coerce")
    if created.empty or closed_at.empty:
        return dict(EMPTY)
    days = ((closed_at - created).dt.total_seconds() / 86400).dropna()
    days = days[days >= 0]
    if days.empty:
        return dict(EMPTY)

    bins = [(0, 1, "<1d"), (1, 7, "1–6d"), (7, 30, "1–4wk"),
            (30, 90, "1–3mo"), (90, 365, "3–12mo"), (365, float("inf"), "1yr+")]
    labels = [b[2] for b in bins]
    values = [int(((days >= low) & (days < high)).sum()) for low, high, _label in bins]
    total = int(sum(values))
    within_month = sum(v for v, (_low, high, _label) in zip(values, bins) if high <= 30)
    out = metric(
        labels, values,
        ins.join(
            ins.share_of(within_month, total, "closed requests", "clear within a month"),
            "Median %s days to close." % round(float(days.median()), 1),
        ),
        countNoun="requests",
        n=total,
    )
    out["ordinal"] = True
    return out


def _requests_growth(collected):
    """Model-request issues opened on the flagship repository, per quarter, with the
    running total.

    Counted at OPEN rather than at close, and every issue counts once regardless of
    whether it has since been closed — this measures DEMAND, how much the community
    is asking for. `request_lead_time`, beside it, measures the separate question of
    how fast those requests get answered. Same source, same independence from the
    per-model repositories the rest of this module joins against.
    """
    requests = (collected or {}).get("github_model_requests")
    if requests is None or requests.empty or "created_at" not in requests.columns:
        return {"labels": [], "series": [], "n": 0}
    dates = as_text(requests["created_at"])
    pairs = []
    for value in dates:
        text = value.strip()
        if len(text) < 7:
            continue
        try:
            year, month = int(text[:4]), int(text[5:7])
        except ValueError:
            continue
        pairs.append(("%dQ%d" % (year, (month - 1) // 3 + 1), 1))
    labels, per_quarter, running = quarter_totals(pairs)
    if not labels:
        return {"labels": [], "series": [], "n": 0}
    return growth_pair(
        labels, per_quarter, running, "model requests",
        insight="%s model requests opened across %d quarters; %s still open." % (
            ins.num(running[-1]), len(labels),
            ins.num(int((as_text(requests["state"]).str.lower() == "open").sum()))
            if "state" in requests.columns else "an unknown number",
        ),
    )


def _image_freshness(collected):
    """Model Docker images by the year their image was last pushed.

    NOT A MAINTENANCE FIGURE, AND NOT A DEMAND FIGURE. `usage.py` establishes that the pull
    baseline on these images is continuous integration pulling every one on a schedule; the
    same schedule is what rebuilds and re-pushes them. So this is **build recency**: evidence
    that the images are still being produced, which is worth knowing and is not evidence that
    anybody chose to update a model.
    """
    images = (collected or {}).get("dockerhub_images")
    if images is None or images.empty or "last_updated" not in images.columns:
        return dict(EMPTY)
    flag = as_text(images.get("is_model")).str.lower()
    dates = as_text(images["last_updated"])
    years = {}
    for i in range(len(images)):
        if i >= len(flag) or flag.iloc[i] != "yes":
            continue
        raw = dates.iloc[i].strip()
        if len(raw) < 4 or not raw[:4].isdigit():
            continue
        years[raw[:4]] = years.get(raw[:4], 0) + 1
    if not years:
        return dict(EMPTY)
    labels = sorted(years)
    values = [years[y] for y in labels]
    total = sum(values)
    newest = labels[-1]
    out = metric(
        labels, values,
        "%s of %s model images were last rebuilt in %s." % (
            ins.num(years[newest]), ins.num(total), newest,
        ),
        countNoun="model images",
        n=total,
    )
    out["ordinal"] = True
    return out


def _model_repos(repos):
    """`[{column: value}]` for the per-model repositories only."""
    flag = as_text(repos.get("is_model")).str.lower()
    out = []
    for i in range(len(repos)):
        name = str(repos["name"].iloc[i] or "").strip()
        if not name or i >= len(flag) or flag.iloc[i] != "yes":
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


def _commit_growth(activity, model_names):
    """Commits to model repositories per quarter, with the running total.

    Separate from the organisation-wide series on the Code page because it answers a
    different question — how much work goes into the Hub itself as against Ersilia's
    tooling. Same collection pass, different filter, and the aggregation is shared rather
    than copied.

    The model repositories are identified by the collector's own `is_model` column rather
    than by re-deriving the identifier pattern here. One definition of "model", in
    `github_api.MODEL_RE`, applied once at collection time.
    """
    labels, per_quarter, running = quarter_commits(activity, keep=model_names)
    if not labels:
        return {"labels": [], "series": [], "n": 0}
    return growth_pair(
        labels, per_quarter, running, "commits",
        insight="%s commits to model repositories across %d quarters. %s" % (
            ins.num(running[-1]), len(labels),
            ins.busiest(labels, per_quarter, "commit", "commits"),
        ),
    )


def _outside_contribution(model_rows):
    """How many models have had a merged pull request from outside the organisation.

    Per MODEL rather than per pull request, and that is the point. A high share of
    external pull requests could in principle be a handful of models attracting all the
    outside work; this counts the models themselves, so it measures how far into the Hub
    community contribution actually reaches. "Outside" uses the same definition as the
    Code page (`github_api.is_internal`).

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
        # Three columns wide: the longer wording overflowed two lines in CI.
        "%s of %s models merged an outside pull request." % (
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
        # Both are EMPTY when their column is absent, so the loop is bounded by the
        # shortest of the three rather than by `images`.
        for i in range(min(len(images), len(flag), len(counts))):
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
