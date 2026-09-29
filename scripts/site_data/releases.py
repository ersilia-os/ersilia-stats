"""Model version history, from GitHub Releases (fetch_github_releases.py).

WHAT THIS ADDS THAT `code.py`'s "release_recency" AND model_activity's join CANNOT
------------------------------------------------------------------------------------
Every other release-shaped figure on this site comes from `github_repos.csv`'s
`latest_release` and `releases` (a bare count) — the CURRENT state, not the history.
Model repos get a new GitHub Release each time a maintainer re-packages or updates
them, so the full sequence of tags, in order, with the semver bump between each one
and the last, answers a different question: is a model a file drop (one release,
ever) or something actively maintained past its first `v1.0.0`?

`bump_type` follows semver precedence (major > minor > patch) and is computed at
fetch time, once, against the previous release's own parsed version — not
recomputed here, so this module only ever aggregates what the collector already
classified.
"""
from . import insights as ins
from .parse import (EMPTY, active_repo_names, as_text, dense_quarters, growth_pair,
                    metric, quarter_counts)

EMPTY_SECTION = {
    "bump_types": dict(EMPTY),
    "growth": {"labels": [], "series": [], "n": 0},
    "most_versioned": dict(EMPTY),
    "cadence": dict(EMPTY),
    "summary": {"rows": [], "n": 0},
}

REQUIRED_COLUMNS = {"repo", "release_index", "bump_type", "published_at", "tag_name"}


def _titles_by_identifier(models):
    if models is None or models.empty or "identifier" not in models.columns:
        return {}
    ids = as_text(models["identifier"])
    titles = as_text(models["title"]) if "title" in models.columns else as_text(ids)
    return {ident: (title or ident) for ident, title in zip(ids, titles) if ident}


def build(models, collected):
    collected = collected or {}
    releases = collected.get("github_releases")
    if releases is None or releases.empty or not REQUIRED_COLUMNS.issubset(releases.columns):
        return dict(EMPTY_SECTION)

    # Every figure here is about the Hub's CURRENT versioning discipline, so it is
    # restricted to models the registry calls Ready or In maintenance, on a
    # repository that has not been archived — see `active_repo_names`.
    active = active_repo_names(models, collected.get("github_repos"),
                               set(as_text(releases["repo"])))
    releases = releases[as_text(releases["repo"]).isin(active)]
    if releases.empty:
        return dict(EMPTY_SECTION)

    titles = _titles_by_identifier(models)
    return {
        "bump_types": _bump_types(releases),
        "growth": _growth(releases),
        "most_versioned": _most_versioned(releases, titles),
        "cadence": _cadence(releases),
        "summary": _summary(releases, titles),
    }


def _bump_types(releases):
    """How a model gets updated — the bump type of every release after a repo's
    first, hub-wide. The first release of each repo is 'initial', not a bump from
    anything, and is excluded so it cannot dilute the read on ongoing maintenance."""
    bumps = as_text(releases["bump_type"])
    bumps = bumps[~bumps.isin(["", "initial"])]
    if bumps.empty:
        return dict(EMPTY)
    counts = bumps.value_counts()
    order = [b for b in ("major", "minor", "patch", "other") if b in counts.index]
    order += [b for b in counts.index if b not in order]
    labels = [b.capitalize() for b in order]
    values = [int(counts[b]) for b in order]
    total = sum(values)
    patch_share = ins.pct(counts.get("patch", 0), total)
    insight = "%s releases tracked past each model's first; %s are patch bumps." % (
        ins.num(total), patch_share or "0%",
    )
    return metric(labels, values, insight, countNoun="releases", n=total)


def _growth(releases):
    """Releases published per quarter, hub-wide, with the running total —
    maintenance activity across the whole Hub over time, not any one model's."""
    quarters = quarter_counts(releases["published_at"])
    if quarters.empty:
        return {"labels": [], "series": [], "n": 0}
    dense = dense_quarters(quarters)
    labels = [str(i) for i in dense.index]
    running = list(dense.cumsum().values)
    return growth_pair(labels, list(dense.values), running, "releases")


def _most_versioned(releases, titles):
    """Models ranked by how many releases they carry — the ones updated most since
    their first `v1.0.0`, not the ones pulled most or committed to most."""
    counts = releases.groupby("repo")["release_index"].max()
    if counts.empty:
        return dict(EMPTY)
    counts = counts.sort_values(ascending=False).head(10)
    labels = [titles.get(repo, repo) for repo in counts.index]
    return metric(
        labels, counts.values,
        "%s leads with %s releases." % (labels[0], ins.num(int(counts.iloc[0]))),
        countNoun="releases",
        n=int(counts.sum()),
    )


def _cadence(releases):
    """Days between a model's CONSECUTIVE releases — not whether it gets re-released
    (`most_versioned` already answers that), but how often.

    Only repositories with two or more releases contribute a gap: a repo's first
    release has nothing before it to measure a gap against, so it drops out rather
    than counting as a zero-day or infinite gap. Bucketed for the same reason every
    other elapsed-time figure on this site is: gaps run from hours to a year, so a
    linear scale would flatten almost everything into one bar near zero.
    """
    import pandas as pd

    df = releases.copy()
    df["published_at"] = pd.to_datetime(df["published_at"], errors="coerce")
    df = df.dropna(subset=["published_at"]).sort_values(["repo", "release_index"])
    gaps = df.groupby("repo")["published_at"].diff().dt.total_seconds() / 86400
    gaps = gaps.dropna()
    gaps = gaps[gaps >= 0]
    if gaps.empty:
        return dict(EMPTY)

    bins = [(0, 7, "<1wk"), (7, 30, "1–4wk"), (30, 90, "1–3mo"),
            (90, 180, "3–6mo"), (180, 365, "6–12mo"), (365, float("inf"), "1yr+")]
    labels = [b[2] for b in bins]
    values = [int(((gaps >= low) & (gaps < high)).sum()) for low, high, _label in bins]
    total = int(sum(values))
    out = metric(
        labels, values,
        "Median %s days between a model's releases, across %s gaps." % (
            round(float(gaps.median()), 1), ins.num(total),
        ),
        countNoun="gaps",
        n=total,
    )
    out["ordinal"] = True
    return out


def _summary(releases, titles):
    """One row per model with release history: how many releases, and its most
    recent tag — the static equivalent of picking one model to inspect, for every
    model at once rather than one at a time."""
    counts = releases.groupby("repo")["release_index"].max()
    if counts.empty:
        return {"rows": [], "n": 0}
    latest = releases.sort_values("release_index").groupby("repo").tail(1).set_index("repo")

    rows = []
    for repo, num_releases in counts.items():
        rows.append({
            "name": repo,
            "title": titles.get(repo, repo),
            "num_releases": int(num_releases),
            "progressed": "Yes" if num_releases > 1 else "No",
            "latest_tag": str(latest.loc[repo, "tag_name"]) if repo in latest.index else "",
        })
    rows.sort(key=lambda r: (-r["num_releases"], r["name"]))
    progressed = sum(1 for r in rows if r["progressed"] == "Yes")
    return {
        "rows": rows[:12],
        "n": len(rows),
        "insight": ins.share_of(progressed, len(rows), "models with release history",
                                "have been updated at least once past their first release"),
    }
