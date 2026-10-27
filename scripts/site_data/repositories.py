"""Repositories section — open-source output and its health.

DISCLOSURE RULE, and it is a distinction worth being precise about: **a count is
not disclosure, a name is.**

So this module splits the two:

* **Aggregates cover every repository**, public and private — how many there are,
  when they were created, the type and status mix, the totals. Knowing that Ersilia
  has 38 private repositories reveals nothing about any of them, and excluding them
  made the totals quietly wrong.
* **Anything that names a repository or a contributor covers public repositories
  only** — the rankings and the contributor handles. A private
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


def attach_github_counts(repos, collected):
    """Fill the count columns from the collected GitHub snapshot, keyed on repository name.

    WHY THIS EXISTS. These counts used to be columns in the Airtable Repositories table —
    `Stars`, `Forks`, `Open Issues`, `Subscribers`, `Total Commits`, `Contributors` — and
    those columns have been **deleted**, deliberately, because a standing total copied into
    a spreadsheet is exactly the thing that goes stale. `int(row["stars"])` on the new
    schema raises `cannot convert float NaN to integer`, so this is not optional.

    The join is by name and only public repositories can match, because the committed
    snapshot is public-only by design. A private repository therefore ends up at 0 for
    every count. That is correct for every figure that names a repository, and it is why
    the star KPI adds the separate private aggregate rather than summing this frame.
    """
    if repos is None or repos.empty:
        return repos
    out = repos.copy()
    frame = (collected or {}).get("github_repos")
    lookup = {}
    if frame is not None and not frame.empty and "name" in frame.columns:
        for i in range(len(frame)):
            lookup[str(frame["name"].iloc[i] or "").strip()] = i
    names = as_text(col(out, "name")) if "name" in out.columns else None
    # One index per Airtable row, resolved once rather than per column.
    matched = [lookup.get(names.iloc[i].strip()) if names is not None else None
               for i in range(len(out))]

    for field, source in (("stars", "stars"), ("forks", "forks"),
                          ("open_issues", "open_issues"), ("subscribers", "watchers"),
                          ("total_commits", "total_commits"),
                          ("contributors", "contributors")):
        has_source = frame is not None and source in frame.columns
        values = []
        for row in matched:
            raw = str(frame[source].iloc[row]).strip() if has_source and row is not None else ""
            values.append(raw if raw not in ("", "nan") else 0)
        out[field] = values
    return out


def build(repos, collected=None):
    """Build the section. `repos` must ALREADY carry the GitHub counts.

    The caller attaches them with `attach_github_counts`, because `build_all` needs the same
    joined frame for its public/private split — doing the join here as well produced
    identical output from two passes over the collected frame.

    `collected` is still required, for the contributor handles, which are a separate
    snapshot rather than a column on this frame.
    """
    public_raw, private_count = public_only(repos)
    if repos is None or repos.empty:
        return {k: dict(EMPTY) for k in (
            "per_quarter", "cumulative", "by_type", "by_status", "visibility",
            "growth",
            "top_by_stars", "top_by_forks", "most_collaborative", "top_contributors",
            "progress", "ranked",
        )}

    every = _numeric(repos)                        # aggregates: all repositories
    public = (_numeric(public_raw)
              if public_raw is not None and not public_raw.empty else every.head(0))
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
        "progress": _progress(every),
        # ---- name-bearing: public repositories only ---------------------------
        "ranked": _ranked(public, name_col),
        "top_by_stars": top_by(public, "stars", name_col,
                               insight=ins.concentration(list(public["stars"]), "stars")
                               if len(public) else None),
        "top_by_forks": top_by(public, "forks", name_col),
        "most_collaborative": top_by(public, "contributors", name_col),
        "top_contributors": _top_contributors(collected),
    }


def _visibility(every, private_count):
    """Published deliberately: the honest way to handle an exclusion is to size it."""
    public_count = int(len(every) - private_count)
    return metric(
        ["Public", "Private"], [public_count, private_count],
        ins.share_of(public_count, len(every), "repositories", "are public"),
        semantics={"Public": "brand", "Private": "neutral"},
    )


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


def _progress(every):
    """Repositories in progress against those completed, every other status left out.

    Archived, Discontinued, Idle and Todo are not part of the question this answers —
    how much of the work under way has been finished — so they are counted in `n` of
    `by_status` but not here.
    """
    status = as_text(col(every, "status").apply(first_value)).str.strip().str.lower()
    in_progress = int((status == "in progress").sum())
    completed = int((status == "completed").sum())
    total = in_progress + completed
    if not total:
        return dict(EMPTY)
    return metric(
        ["In progress", "Completed"], [in_progress, completed],
        ins.share_of(in_progress, total, "repositories", "are still in progress"),
        countNoun="repositories",
        n=total,
    )


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


def _is_bot(login):
    text = str(login or "").strip()
    return text.lower() in {"ersilia-bot"} or text.endswith("[bot]")


def _top_contributors(collected):
    """GitHub handles by number of public repositories touched.

    Now read from `data/github/contributors_<date>.csv` rather than from Airtable, whose
    `Contributor Names` column was deleted along with the other GitHub-derived fields.
    Collecting them directly also ends the hand-maintenance.

    Public handles on public repositories, so already public information — unlike the
    community table's handles, which are dropped at load and never reach the site. The
    collector excludes anonymous contributors, who are identified by an email rather than
    a login, so no address is ever fetched.
    """
    frame = (collected or {}).get("github_contributors")
    if frame is None or frame.empty or "login" not in frame.columns:
        return dict(EMPTY)
    counts = to_num(col(frame, "repositories"))
    # `counts` is empty when the column is absent; bound the loop by the shorter of the two.
    pairs = sorted(((str(frame["login"].iloc[i]).strip(), int(counts.iloc[i] or 0))
                    for i in range(min(len(frame), len(counts)))),
                   key=lambda kv: (-kv[1], kv[0]))
    # Second line of defence, matching how PII columns are dropped at fetch AND at load:
    # a snapshot collected before the bot filter existed must not put CI on the chart.
    pairs = [p for p in pairs if p[0] and p[1] > 0 and not _is_bot(p[0])]
    if not pairs:
        return dict(EMPTY)
    top = pairs[:12]
    total = sum(v for _, v in pairs)
    return metric(
        [k for k, _ in top], [v for _, v in top],
        "%s distinct contributors; the top 3 hold %s of all repository contributions." % (
            ins.num(len(pairs)),
            ins.pct(sum(v for _, v in pairs[:3]), total),
        ),
        countNoun="repositories",
        n=len(pairs),
    )

