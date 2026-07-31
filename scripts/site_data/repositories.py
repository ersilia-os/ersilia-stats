"""Repositories section — open-source output and its health.

PUBLIC REPOSITORIES ONLY. The Airtable table tracks private repos too (38 of 179 in
the July 2026 snapshot), and the previous export published their names in the
top-by-stars, top-by-forks, most-collaborative and scatter charts, plus their
contributors. A private repository's *name* is itself disclosure, so everything here
is filtered to ``visibility == "Public"`` and the excluded count is reported instead.
"""
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
    quarter_counts,
    to_num,
    top_by,
    value_counts,
)

NUMERIC_FIELDS = ("stars", "forks", "subscribers", "total_commits", "open_issues", "contributors")

# Pairs for the repo-health small-multiples panel. Popularity and activity are
# different things; plotting them against each other is the only way to see a repo
# with 400 commits and no stars, or 40 stars and no maintenance.
HEALTH_PAIRS = [
    {"x": "stars", "y": "forks", "xLabel": "Stars", "yLabel": "Forks"},
    {"x": "stars", "y": "subscribers", "xLabel": "Stars", "yLabel": "Watchers"},
    {"x": "total_commits", "y": "open_issues", "xLabel": "Commits", "yLabel": "Open issues"},
    {"x": "stars", "y": "total_commits", "xLabel": "Stars", "yLabel": "Commits"},
]


def public_only(repos):
    """Filter to public repositories, returning ``(frame, excluded_count)``."""
    if repos is None or repos.empty:
        return repos, 0
    if "visibility" not in repos.columns:
        return repos, 0
    visibility = repos["visibility"].astype(str).str.strip().str.lower()
    public = repos[visibility == "public"].copy()
    return public, int(len(repos) - len(public))


def build(repos):
    public, private_count = public_only(repos)
    if public is None or public.empty:
        return dict(
            {k: dict(EMPTY) for k in (
                "per_quarter", "cumulative", "top_by_stars", "top_by_forks",
                "most_collaborative", "top_contributors", "by_type", "by_status",
                "contributor_concentration",
            )},
            scatter={"points": [], "n": 0},
            health={"points": [], "pairs": HEALTH_PAIRS, "n": 0},
        )

    frame = public.copy()
    for field in NUMERIC_FIELDS:
        frame[field] = to_num(col(frame, field)).astype(int)
    name_col = "name" if "name" in frame.columns else "title"

    created = quarter_counts(col(frame, "creation_date"))
    dense = dense_quarters(created)
    labels = [str(i) for i in dense.index]
    running = list(dense.cumsum().values)
    undated = int(len(frame) - int(dense.sum()))

    cumulative_metric = cumulative(
        created,
        ins.join(
            ins.span(labels, running, "public repositories"),
            ("%s has no creation date on file." % ins.count_of(undated, "repository", "repositories"))
            if undated else None,
        ),
    )
    cumulative_metric["n"] = int(running[-1]) if running else 0

    return {
        "per_quarter": metric(
            labels, dense.values,
            ins.busiest(labels, list(dense.values), "repository", "repositories"),
        ),
        "cumulative": cumulative_metric,
        "top_by_stars": top_by(frame, "stars", name_col,
                              insight=ins.concentration(list(frame["stars"]), "stars")),
        "top_by_forks": top_by(frame, "forks", name_col,
                               insight=ins.share_of(
                                   int((frame["forks"] > 0).sum()), len(frame),
                                   "public repositories", "have ever been forked")),
        "most_collaborative": top_by(frame, "contributors", name_col,
                                     insight=ins.share_of(
                                         int((frame["contributors"] <= 1).sum()), len(frame),
                                         "public repositories",
                                         "have a single listed contributor")),
        "top_contributors": _top_contributors(frame),
        "contributor_concentration": _concentration_curve(frame),
        "by_type": value_counts(col(frame, "type").apply(first_value), top=12,
                                insight=ins.leader(
                                    value_counts(col(frame, "type").apply(first_value)),
                                    "public repositories")),
        "by_status": _by_status(frame),
        "scatter": _scatter(frame, name_col),
        "health": _health(frame, name_col),
    }


def _top_contributors(frame):
    """GitHub handles by number of public repositories touched.

    These are public GitHub handles attached to public repositories, so they are
    already public information — unlike the community table's handles, which are
    dropped at load.
    """
    counts = multi_counts(col(frame, "contributor_names"), top=15)
    everyone = multi_counts(col(frame, "contributor_names"))
    if counts["labels"]:
        counts["insight"] = ins.join(
            "%s distinct contributors across %s public repositories." % (
                ins.num(everyone.get("distinct", 0)), ins.num(len(frame)),
            ),
            ins.concentration(everyone["values"], "repository contributions"),
        )
    return counts


def _concentration_curve(frame):
    """Lorenz curve of commits across repositories — the bus-factor question.

    x = cumulative share of repositories (least active first), y = cumulative share
    of commits. A curve hugging the bottom-right means a few repositories carry
    almost everything.
    """
    commits = sorted(int(v) for v in frame["total_commits"] if v > 0)
    total = sum(commits)
    if not commits or total == 0:
        return dict(EMPTY)
    labels, values, running = ["0"], [0.0], 0
    for index, value in enumerate(commits, start=1):
        running += value
        labels.append(str(round(100.0 * index / len(commits), 1)))
        values.append(round(100.0 * running / total, 1))
    # Gini via the trapezoid area under the Lorenz curve.
    area = 0.0
    for i in range(1, len(values)):
        width = (float(labels[i]) - float(labels[i - 1])) / 100.0
        area += width * (values[i] + values[i - 1]) / 200.0
    gini = round(max(0.0, min(1.0, 1 - 2 * area)), 2)
    top_decile = sum(commits[-max(1, len(commits) // 10):])
    return metric(
        labels, values,
        "The busiest 10%% of repositories hold %s of all commits (Gini %s)." % (
            ins.pct(top_decile, total), gini,
        ),
        gini=gini,
        unit="% of commits",
        n=len(commits),
    )


def _by_status(frame):
    status = col(frame, "status").apply(first_value)
    out = value_counts(status, top=12)
    if out["labels"]:
        active = int(status.astype(str).str.strip().str.lower().isin(
            {"in progress", "idle"}).sum())
        out["insight"] = ins.share_of(active, len(frame), "public repositories",
                                      "are in progress or idle rather than closed out")
    return out


def _scatter(frame, name_col):
    """[stars, forks, contributors, name] per repository."""
    points = []
    for _, row in frame.iterrows():
        name = str(row.get(name_col, "")).strip()
        stars, forks, contributors = int(row["stars"]), int(row["forks"]), int(row["contributors"])
        if name and (stars or forks or contributors):
            points.append([stars, forks, contributors, name])
    insight = None
    if points:
        loudest = max(points, key=lambda p: p[0])
        insight = "%s of %s public repositories have any stars, forks or listed contributors; %s leads on stars." % (
            ins.num(len(points)), ins.num(len(frame)), loudest[3],
        )
    return {"points": points, "n": len(points), "insight": insight}


def _health(frame, name_col):
    """Per-repo metric bundle; the client builds the four scatter panels from it."""
    points = []
    for _, row in frame.iterrows():
        name = str(row.get(name_col, "")).strip()
        if not name:
            continue
        record = {"name": name}
        for field in NUMERIC_FIELDS:
            record[field] = int(row[field])
        if any(record[f] for f in NUMERIC_FIELDS):
            points.append(record)
    insight = None
    if points:
        quiet = [p for p in points if p["total_commits"] >= 50 and p["stars"] == 0]
        insight = "%s repositories with 50+ commits have no stars — activity and visibility are not the same thing." % (
            ins.num(len(quiet)),
        )
    return {"points": points, "pairs": HEALTH_PAIRS, "n": len(points), "insight": insight}
