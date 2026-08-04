"""Repositories section — open-source output and its health.

DISCLOSURE RULE, and it is a distinction worth being precise about: **a count is
not disclosure, a name is.**

So this module splits the two:

* **Aggregates cover every repository**, public and private — how many there are,
  when they were created, the type and status mix, how commits concentrate, the
  totals. Knowing that Ersilia has 38 private repositories reveals nothing about
  any of them, and excluding them made the totals quietly wrong.
* **Anything that names a repository or a contributor covers public repositories
  only** — the rankings, the scatter points, the contributor handles. A private
  repository's *name* is disclosure, and so is who works on it.

The public/private split is itself published (``visibility``), because the honest
way to handle the exclusion is to state its size rather than hide it.
"""

from . import insights as ins
from .parse import (
    EMPTY,
    as_text,
    col,
    cumulative,
    dense_quarters,
    growth_pair,
    first_value,
    metric,
    multi_counts,
    quarter_counts,
    to_num,
    top_by,
    value_counts,
)

NUMERIC_FIELDS = ("stars", "forks", "subscribers", "total_commits", "open_issues", "contributors")


def public_only(repos):
    """Split into ``(public_frame, private_count)``."""
    if repos is None or repos.empty:
        return repos, 0
    if "visibility" not in repos.columns:
        return repos, 0
    visibility = as_text(repos["visibility"]).str.lower()
    public = repos[visibility == "public"].copy()
    return public, int(len(repos) - len(public))


def _numeric(frame):
    """Coerce the count columns so arithmetic is safe."""
    out = frame.copy()
    for field in NUMERIC_FIELDS:
        out[field] = to_num(col(out, field)).astype(int)
    return out


def build(repos):
    public_raw, private_count = public_only(repos)
    if repos is None or repos.empty:
        return dict(
            {k: dict(EMPTY) for k in (
                "per_quarter", "cumulative", "by_type", "by_status", "visibility",
                "growth",
                "top_by_stars", "top_by_forks", "most_collaborative", "top_contributors",
                "contributor_concentration", "ranked",
            )},
            scatter={"points": [], "n": 0},
        )

    every = _numeric(repos)                        # aggregates: all repositories
    public = _numeric(public_raw) if public_raw is not None and not public_raw.empty else every.head(0)
    name_col = "name" if "name" in every.columns else "title"

    created = quarter_counts(col(every, "creation_date"))
    dense = dense_quarters(created)
    labels = [str(i) for i in dense.index]
    running = list(dense.cumsum().values)

    cumulative_metric = cumulative(
        created,
        ins.span(labels, running, "repositories"),
    )
    cumulative_metric["n"] = int(running[-1]) if running else 0

    return {
        # ---- aggregates: every repository -------------------------------------
        "per_quarter": metric(
            labels, dense.values,
            ins.busiest(labels, list(dense.values), "repository", "repositories"),
        ),
        "cumulative": cumulative_metric,
        "growth": growth_pair(labels, list(dense.values), running, "repositories"),
        "by_type": _by_type(every),
        "by_status": _by_status(every),
        "visibility": _visibility(every, private_count),
        "contributor_concentration": _concentration_curve(every),
        # ---- name-bearing: public repositories only ---------------------------
        "ranked": _ranked(public, name_col),
        "top_by_stars": top_by(public, "stars", name_col,
                               insight=ins.concentration(list(public["stars"]), "stars")
                               if len(public) else None),
        "top_by_forks": top_by(public, "forks", name_col),
        "most_collaborative": top_by(public, "contributors", name_col),
        "top_contributors": _top_contributors(public),
        "scatter": _scatter(public, name_col),
    }


def _visibility(every, private_count):
    """Published deliberately: the honest way to handle an exclusion is to size it."""
    public_count = int(len(every) - private_count)
    out = metric(
        ["Public", "Private"], [public_count, private_count],
        ins.share_of(public_count, len(every), "repositories", "are public"),
        semantics={"Public": "brand", "Private": "neutral"},
    )
    return out


def _by_type(every):
    kinds = col(every, "type").apply(first_value)
    out = value_counts(kinds, top=12)
    if out["labels"]:
        out["insight"] = ins.leader(value_counts(kinds), "repositories")
    return out


def _by_status(every):
    status = col(every, "status").apply(first_value)
    out = value_counts(status, top=12)
    if out["labels"]:
        active = int(as_text(status).str.lower().isin({"in progress", "idle"}).sum())
        out["insight"] = ins.share_of(active, len(every), "repositories",
                                      "are in progress or idle rather than closed out")
    return out


def _ranked(public, name_col):
    """One table replacing three ranking charts: stars, forks and contributors
    side by side, so a repository's whole profile is on one row."""
    if public is None or public.empty or name_col not in public.columns:
        return dict(EMPTY)
    ranked = public.sort_values("stars", ascending=False).head(12)
    rows = []
    for _, row in ranked.iterrows():
        name = str(row.get(name_col, "")).strip()
        if not name:
            continue
        rows.append({
            "name": name,
            "stars": int(row["stars"]),
            "forks": int(row["forks"]),
            "contributors": int(row["contributors"]),
            "commits": int(row["total_commits"]),
        })
    return {
        "rows": rows,
        "n": len(rows),
        "insight": ins.concentration(list(public["stars"]), "stars"),
    }


def _top_contributors(public):
    """GitHub handles by number of public repositories touched.

    Public handles on public repositories, so already public information — unlike
    the community table's handles, which are dropped at load.
    """
    if public is None or public.empty:
        return dict(EMPTY)
    counts = multi_counts(col(public, "contributor_names"), top=12)
    everyone = multi_counts(col(public, "contributor_names"))
    if counts["labels"]:
        counts["insight"] = "%s distinct contributors; the top 3 hold %s of contributions." % (
            ins.num(everyone.get("distinct", 0)),
            ins.pct(sum(sorted(everyone["values"], reverse=True)[:3]), sum(everyone["values"])),
        )
    return counts


def _concentration_curve(every):
    """Lorenz curve of commits across repositories — the bus-factor question.

    No names involved, so this covers every repository.

    x = cumulative share of repositories (least active first), y = cumulative
    share of commits. A curve hugging the bottom-right means a few repositories
    carry almost everything.
    """
    commits = sorted(int(v) for v in every["total_commits"] if v > 0)
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
        gini=gini, unit="% of commits", n=len(commits),
    )


def _scatter(public, name_col):
    """Per-repository points for the log-log popularity/activity chart.

    Public only: each point carries a name in its tooltip.
    """
    if public is None or public.empty:
        return {"points": [], "n": 0}
    points = []
    for _, row in public.iterrows():
        name = str(row.get(name_col, "")).strip()
        if not name:
            continue
        points.append({
            "name": name,
            "stars": int(row["stars"]),
            "forks": int(row["forks"]),
            "commits": int(row["total_commits"]),
            "issues": int(row["open_issues"]),
            "contributors": int(row["contributors"]),
        })
    insight = None
    if points:
        quiet = [p for p in points if p["commits"] >= 50 and p["stars"] == 0]
        insight = "%s public repositories with 50+ commits have no stars." % ins.num(len(quiet))
    return {"points": points, "n": len(points), "insight": insight}
