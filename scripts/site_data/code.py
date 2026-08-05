"""Development activity, from the committed GitHub snapshots.

THE GAP THIS FILLS
------------------
The Code page described a *shelf*: how many repositories exist, which have the most stars,
who has touched the most of them. Every number on it was a standing total. Nothing said
whether the work was still happening, who was doing it, or how fast — because Airtable
holds one scalar per repository and a scalar cannot answer that.

The collected GitHub snapshots can. Three files, and each one carries a dimension Airtable
structurally cannot store:

    repos_<date>.csv            per-repository counts, including commits, releases,
                                closed issues, merged PRs and PR author associations
    commit_activity_<date>.csv  commits per calendar quarter per repository
    stars_<date>.csv            one row per star, WITH THE DATE IT WAS GIVEN

THE FINDING THAT REORGANISED THIS PAGE
--------------------------------------
**78% of recently merged pull requests on model repositories come from outside the
organisation** — and a similar share on the other repositories. Measured across every public
repository rather than a sample; the exact counts are recomputed on each build and appear in
the caption, so they are not repeated here to go stale.

That number matters because of a mistake it corrects. Per-model repositories were dismissed
here as carrying "almost no signal", on the evidence of stars: `eos4e40` has 2, `eos2gw4`
has 0. That was true and it was the wrong measurement. Nobody stars a single model — they
*contribute* one, through a pull request, and **208 of 243 model repositories have at least
one merged, 127 of them from outside the organisation.** The contribution signal was there
the whole time, in a field nobody had read.

So this module treats external contribution as the headline rather than a footnote, and
reports it separately for model and non-model repositories, because they are different
kinds of work: a model repository is a submission, and `ersilia` itself is a codebase.

WHAT IS DELIBERATELY NOT HERE
-----------------------------
**No author names, ever.** `prs_external` is a count derived from GitHub's
`authorAssociation` enum; no login is collected, so none can be published. The existing
contributor ranking on this page comes from the Airtable `Contributor Names` column, which
is a separate, deliberate decision documented in `fetch_airtable.py`.

**Public repositories only**, because that is all the snapshots contain — `fetch_github.py`
asks for public repositories precisely so this file cannot leak a private name.

TWO LIMITS STATED ON THE CARDS
------------------------------
A **star count is not a user count**, and the star curve is restricted to the repositories
with more than five stars because a curve through three points is decoration.

**`median_days_to_close` is computed from the last 30 closed issues** per repository, so it
describes recent practice rather than all history. A repository that has closed fewer than
that contributes the median of what it has.
"""
import pandas as pd

from . import insights as ins
from .parse import EMPTY, as_text, growth_pair, metric, quarter_totals, to_num

# Bands for "when was this last touched", in days. Ordered, and rendered as ordered.
RECENCY_BANDS = [
    (0, 30, "this month"),
    (30, 90, "1–3 months"),
    (90, 180, "3–6 months"),
    (180, 365, "6–12 months"),
    (365, 730, "1–2 years"),
    (730, float("inf"), "over 2 years"),
]

# Bands for median days to close an issue.
# Short deliberately. The histogram builder renders every label horizontally with no
# rotation, so "same day or next" / "within a month" collided into each other at the
# width this card actually gets.
RESOLUTION_BANDS = [
    (0, 2, "\u2264 1 day"),
    (2, 8, "\u2264 1 week"),
    (8, 31, "\u2264 1 month"),
    (31, 91, "1\u20133 mo"),
    (91, float("inf"), "> 3 mo"),
]

COMMIT_BANDS = [
    (0, 11, "< 10"),
    (11, 26, "10\u201325"),
    (26, 51, "26\u201350"),
    (51, 101, "51\u2013100"),
    (101, float("inf"), "> 100"),
]

EMPTY_SECTION = {
    "commit_growth": {"labels": [], "series": [], "n": 0},
    "star_growth": {"labels": [], "series": [], "n": 0},
    "contribution_origin": {"labels": [], "series": [], "n": 0},
    "activity_recency": dict(EMPTY),
    "by_language": dict(EMPTY),
    "by_licence": dict(EMPTY),
    "issue_resolution": dict(EMPTY),
    "model_commit_effort": dict(EMPTY),
    "most_active": {"rows": [], "n": 0},
    "release_recency": dict(EMPTY),
}


def build(collected, today=None):
    """Metrics from ``data/github/``.

    Every key degrades to an empty metric when the collector has not run, so the site
    builds from a clone with no GitHub data at all.
    """
    collected = collected or {}
    repos = collected.get("github_repos")
    activity = collected.get("github_commit_activity")
    stars = collected.get("github_stars")

    if repos is None or repos.empty or "name" not in repos.columns:
        return dict(EMPTY_SECTION)

    out = dict(EMPTY_SECTION)
    out["commit_growth"] = _commit_growth(activity)
    out["star_growth"] = _star_growth(stars)
    out["contribution_origin"] = _contribution_origin(repos)
    out["activity_recency"] = _activity_recency(repos, today)
    out["by_language"] = _by_language(repos)
    out["by_licence"] = _by_licence(repos)
    out["issue_resolution"] = _issue_resolution(repos)
    out["model_commit_effort"] = _model_commit_effort(repos)
    out["most_active"] = _most_active(repos)
    out["release_recency"] = _release_recency(repos)
    return out


def _release_recency(repos):
    """Repositories by the year of their most recent release.

    READ THIS ONE CAREFULLY, because the obvious reading is wrong. 164 repositories last
    released in 2025 against 72 in 2026 looks like releasing is slowing down. It is not
    evidence of that: **139 of 386 repositories have never cut a release at all**, and most
    of those that do release do so rarely, so a repository sitting on a 2025 tag is usually
    one that ships when there is something to ship rather than one that stopped.

    That is why the never-released group is a bar here rather than an omission. Without it
    the chart would describe 245 repositories and imply it described all of them.
    """
    if "latest_release" not in repos.columns or "releases" not in repos.columns:
        return dict(EMPTY)
    years = {}
    never = 0
    for i in range(len(repos)):
        raw = str(repos["latest_release"].iloc[i]).strip()
        if raw in ("", "nan") or len(raw) < 4 or not raw[:4].isdigit():
            never += 1
            continue
        years[raw[:4]] = years.get(raw[:4], 0) + 1
    if not years:
        return dict(EMPTY)
    labels = sorted(years)
    values = [years[y] for y in labels]
    with_release = sum(values)
    if never:
        labels.append("never released")
        values.append(never)
    out = metric(
        labels, values,
        "%s of %s repositories have ever published a release." % (
            ins.num(with_release), ins.num(len(repos))),
        countNoun="repositories",
        n=len(repos),
    )
    out["ordinal"] = True
    return out


def _commit_growth(activity):
    """Commits per calendar quarter across every repository, with the running total."""
    labels, per_quarter, running = quarter_commits(activity)
    if not labels:
        return {"labels": [], "series": [], "n": 0}
    return growth_pair(
        labels, per_quarter, running, "commits",
        insight="%s commits across the %d quarters collected. %s" % (
            ins.num(running[-1]), len(labels),
            ins.latest_change(labels, per_quarter, "commits"),
        ),
    )


def quarter_commits(activity, keep=None):
    """`(labels, per_quarter, running)` from a commit-activity frame.

    `keep` is an optional set of repository names; without it every repository counts.
    Shared with `model_activity.py`, which passes the model repositories so the Hub gets
    its own series without a second copy of this aggregation.
    """
    if activity is None or activity.empty:
        return [], [], []
    label_col = "week_start" if "week_start" in activity.columns else "quarter"
    if label_col not in activity.columns or "commits" not in activity.columns:
        return [], [], []
    names = as_text(activity["name"]) if "name" in activity.columns else None
    labels_raw = as_text(activity[label_col])
    values = to_num(activity["commits"])
    pairs = []
    for i in range(len(activity)):
        if keep is not None and (names is None or names.iloc[i].strip() not in keep):
            continue
        pairs.append((labels_raw.iloc[i], values.iloc[i]))
    return quarter_totals(pairs)


def _star_growth(stars):
    """Stars per quarter and cumulative, from the date each star was given.

    This is why a star curve needs no accumulated history: GitHub records `starred_at`,
    so the whole past is available from one collection.
    """
    if stars is None or stars.empty or "starred_at" not in stars.columns:
        return {"labels": [], "series": [], "n": 0}

    # One star per row, so each contributes 1 to the quarter it was given in. The
    # aggregation is `quarter_totals`, shared with the commit series.
    pairs = []
    dates = as_text(stars["starred_at"])
    for i in range(len(stars)):
        text = dates.iloc[i].strip()
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

    repos = len(set(as_text(stars["name"]))) if "name" in stars.columns else 0
    return growth_pair(
        labels, per_quarter, running, "stars",
        insight="%s dated stars across %s repositories. %s" % (
            ins.num(running[-1]), ins.num(repos),
            ins.busiest(labels, per_quarter, "star", "stars"),
        ),
    )


def _split_models(repos):
    """`(is_model, is_other)` boolean masks aligned to `repos`.

    A mask built from an absent column is EMPTY, and pandas rejects it as an indexer with
    "Unalignable boolean Series". Falling back to all-False for models keeps every figure
    that splits on this from raising, and reports no model repositories rather than
    guessing.
    """
    flag = as_text(repos.get("is_model")).str.lower()
    if len(flag) != len(repos):
        empty = pd.Series(False, index=repos.index)
        return empty, ~empty
    return flag == "yes", flag != "yes"


def _contribution_origin(repos):
    """Merged pull requests by whether their author is in the organisation.

    THE MOST IMPORTANT CHART ON THIS PAGE. Split by repository kind because the two mean
    different things: a pull request against a model repository is usually a model
    *submission*, and one against `ersilia` is work on the tool itself.

    Counts come from GitHub's `authorAssociation`: OWNER, MEMBER and COLLABORATOR are
    inside the organisation, everything else is outside. Only the most recent 30 merged
    pull requests per repository are sampled, so this describes current practice.
    """
    if "prs_sampled" not in repos.columns or "prs_external" not in repos.columns:
        return {"labels": [], "series": [], "n": 0}

    is_model, is_other = _split_models(repos)
    sampled, external = to_num(repos["prs_sampled"]), to_num(repos["prs_external"])

    groups = []
    # Short labels: at five columns wide "Model repositories" was truncated to
    # "Model reposit…" on the axis.
    for label, mask in (("Model repos", is_model), ("Everything else", is_other)):
        total = int(sampled[mask].sum())
        outside = int(external[mask].sum())
        groups.append((label, outside, total - outside, total))

    labels = [g[0] for g in groups]
    series = [
        {"name": "From outside Ersilia", "values": [g[1] for g in groups]},
        {"name": "From the organisation", "values": [g[2] for g in groups]},
    ]
    overall_out = sum(g[1] for g in groups)
    overall = sum(g[3] for g in groups)
    shares = ["%s%% on %s" % (round(100.0 * outside / total), label.lower())
              for label, outside, _inside, total in groups if total]
    # Short: five columns wide, and the runner's fonts are wider than this machine's.
    # The per-kind shares are in the methodology note.
    insight = "%s of %s recent merged PRs came from outside Ersilia%s." % (
        ins.num(overall_out), ins.num(overall),
        " — %s" % shares[0] if shares else "")
    return {"labels": labels, "series": series, "n": overall, "insight": insight}


def _activity_recency(repos, today):
    """Repositories by how long since the last push, archived counted separately.

    An archived repository is not neglected — it was retired deliberately — so putting it
    in a "two years untouched" bucket would report a decision as a failure.
    """
    if "pushed_at" not in repos.columns:
        return dict(EMPTY)
    now = pd.Timestamp(today) if today is not None else pd.Timestamp.today().normalize()
    pushed = pd.to_datetime(repos["pushed_at"], errors="coerce")
    archived = as_text(repos.get("archived")).str.lower() == "yes"

    labels = [band[2] for band in RECENCY_BANDS] + ["archived"]
    values = [0] * len(labels)
    for i in range(len(repos)):
        # `archived` is empty when the column is absent; treat that as "not archived"
        # rather than indexing past the end.
        if i < len(archived) and bool(archived.iloc[i]):
            values[-1] += 1
            continue
        when = pushed.iloc[i] if i < len(pushed) else None
        if pd.isna(when):
            continue
        age = (now - when).days
        for index, (low, high, _name) in enumerate(RECENCY_BANDS):
            if low <= age < high:
                values[index] += 1
                break

    live = sum(values[:3])                       # pushed within six months
    out = metric(
        labels, values,
        "%s of %s repositories pushed to within six months; %s archived." % (
            ins.num(live), ins.num(len(repos)), ins.num(values[-1]),
        ),
        countNoun="repositories",
        n=len(repos),
    )
    out["ordinal"] = True
    return out


def _by_language(repos):
    if "language" not in repos.columns:
        return dict(EMPTY)
    counts = {}
    for value in as_text(repos["language"]):
        name = value.strip()
        if name:
            counts[name] = counts.get(name, 0) + 1
    if not counts:
        return dict(EMPTY)
    ranked = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:10]
    total = sum(counts.values())
    return metric(
        [name for name, _ in ranked], [count for _, count in ranked],
        "%s of %s repositories with a detected language are %s." % (
            ins.num(ranked[0][1]), ins.num(total), ranked[0][0],
        ),
        countNoun="repositories",
        # The whole population, not the sum of the bars shown: `metric` would otherwise
        # report the top ten's total and disagree with the sentence above.
        n=total,
    )


def _by_licence(repos):
    """SPDX identifiers as GitHub reports them, read from the licence file.

    A CORRECTION IS RECORDED HERE because the wrong version nearly shipped. This was
    written claiming the organisation's tooling was "largely GPL-3.0 while the model
    repositories are overwhelmingly MIT". That is false, and checking it took one query:
    **229 of 243 model repositories are GPL-3.0** and 7 are MIT; the non-model
    repositories are 107 GPL-3.0 and 25 MIT. GPL-3.0 dominates both kinds, so there is no
    model-versus-tooling split to report.

    The confusion is worth naming, because the site shows both numbers. The Models page
    reports `licence_openness` from the Airtable `License` column, and that describes the
    **upstream model's** licence — the terms of the thing being wrapped. This describes the
    licence of Ersilia's own wrapper repository. They answer different questions and they
    genuinely differ; treating one as evidence about the other is the mistake.
    """
    if "license" not in repos.columns:
        return dict(EMPTY)
    counts = {}
    for value in as_text(repos["license"]):
        name = value.strip()
        if name and name.upper() not in ("NOASSERTION",):
            counts[name] = counts.get(name, 0) + 1
    if not counts:
        return dict(EMPTY)
    ranked = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:8]
    total = sum(counts.values())
    return metric(
        [name for name, _ in ranked], [count for _, count in ranked],
        # One clause: four columns wide. The licence count is in the note.
        ins.share_of(ranked[0][1], total, "licensed repositories",
                     "use %s" % ranked[0][0]),
        countNoun="repositories",
    )


def _issue_resolution(repos):
    """How long issues stay open, bucketed, one row per repository.

    Per repository rather than per issue, because the median of medians answers "is this
    project responsive" while a pooled distribution is dominated by whichever repository
    files the most issues.
    """
    if "median_days_to_close" not in repos.columns:
        return dict(EMPTY)
    days = to_num(repos["median_days_to_close"])
    labels = [band[2] for band in RESOLUTION_BANDS]
    values = [0] * len(labels)
    counted = 0
    for i in range(len(repos)):
        value = days.iloc[i]
        if value is None or (isinstance(value, float) and value != value):
            continue
        raw = str(repos["median_days_to_close"].iloc[i]).strip()
        if raw in ("", "nan"):
            continue
        counted += 1
        for index, (low, high, _name) in enumerate(RESOLUTION_BANDS):
            if low <= float(value) < high:
                values[index] += 1
                break
    if not counted:
        return dict(EMPTY)
    quick = values[0] + values[1]
    out = metric(
        labels, values,
        "%s of %s repositories with closed issues resolve them within a week." % (
            ins.num(quick), ins.num(counted)),
        countNoun="repositories",
        n=counted,
    )
    out["ordinal"] = True
    return out


def _model_commit_effort(repos):
    """Commits per model repository, bucketed.

    The point: a model is not a file drop. The distribution shows how much work sits
    behind a typical entry in the Model Hub.
    """
    if "total_commits" not in repos.columns:
        return dict(EMPTY)
    is_model, _ = _split_models(repos)
    commits = to_num(repos["total_commits"])[is_model]
    counted = [int(v) for v in commits if v is not None and v == v]
    if not counted:
        return dict(EMPTY)

    labels = [band[2] for band in COMMIT_BANDS]
    values = [0] * len(labels)
    for value in counted:
        for index, (low, high, _name) in enumerate(COMMIT_BANDS):
            if low <= value < high:
                values[index] += 1
                break
    counted.sort()
    median = counted[len(counted) // 2]
    out = metric(
        labels, values,
        "The median model repository carries %s commits; %s of %s have more than 50." % (
            ins.num(median), ins.num(values[3] + values[4]), ins.num(len(counted)),
        ),
        countNoun="model repositories",
        n=len(counted),
    )
    out["ordinal"] = True
    return out


def _rows_by(repos, sort_key, columns, top=10):
    """`[{name, ...columns}]` for the top repositories by `sort_key`."""
    frame = repos
    rows = []
    for i in range(len(frame)):
        name = str(frame["name"].iloc[i] or "").strip()
        if not name:
            continue
        entry = {"name": name}
        ok = True
        for key in columns:
            if key not in frame.columns:
                ok = False
                break
            raw = str(frame[key].iloc[i]).strip()
            entry[key] = int(float(raw)) if raw not in ("", "nan") else 0
        if ok:
            rows.append(entry)
    rows.sort(key=lambda r: (-r.get(sort_key, 0), r["name"]))
    return rows[:top]


def _most_active(repos):
    """The repositories where the work actually happens, on one row each.

    Columns rather than a ranking chart each. Releases sit here instead of on their own card
    because "how many releases" is only interesting beside the commit and pull-request counts
    — 33 releases on `lazy-qsar` and 32 on `ersilia` describe very different projects, and the
    row is what distinguishes them.

    `watchers` is the real subscriber count, and it corrects the stars figures elsewhere on
    this page: **158 of 386 repositories have more subscribers than stars.** Subscribers ask
    to be told when something changes, which is a stronger signal than a bookmark, and by
    that measure the star counts understate attention rather than overstating it. It arrives
    as a column rather than a chart because the absolute numbers are small — 19 at most.
    """
    columns = ["total_commits", "merged_prs", "closed_issues", "releases", "contributors",
               "watchers"]
    if any(c not in repos.columns for c in columns):
        return {"rows": [], "n": 0}
    rows = _rows_by(repos, "total_commits", columns, top=10)
    if not rows:
        return {"rows": [], "n": 0}
    total = int(to_num(repos["total_commits"]).sum())
    releases = to_num(repos["releases"])
    with_releases = int(sum(1 for v in releases if v and v > 0))
    leader = rows[0]
    return {
        "rows": rows,
        "n": len(rows),
        # `ins.join` separates with a space only, so each fragment carries its own
        # full stop — without it the two sentences run together.
        "insight": ins.join(
            "%s alone holds %s of the %s commits across all public repositories." % (
                leader["name"], ins.pct(leader["total_commits"], total), ins.num(total),
            ),
            "%s repositories publish releases." % ins.num(with_releases)
            if with_releases else None,
        ),
    }
