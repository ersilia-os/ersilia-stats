"""Which packages the Hub's heaviest and most-pulled models install, from install.yml
(fetch_model_packages.py).

WHY THIS EXISTS
----------------
Docker image size (usage.py) says HOW heavy a model is; nothing else says WHY.
`install.yml` pins exactly what a model's Docker build installs — pip and conda
packages, with version — one file per model repository. Joining that against the
same AMD64 image-size reading `usage.size_swings` uses turns "some models are
heavy" into "these specific packages are the ones showing up in the heavy ones",
which is the actionable form of the question.

The same count over the most-PULLED models asks the complementary question: what the
models people actually run are built on. Read side by side, a package that leads the
heavy list but not the popular one is weight few users pay for.
"""
from . import insights as ins
from .parse import EMPTY, active_repo_names, as_text, metric

# A model's image at or above this size counts as "heavy" for this chart. Chosen
# because it is roughly the Hub's 90th percentile (see models.image_size) — high
# enough that "heavy" means something, not so high the sample collapses to a
# handful of repos.
HEAVY_THRESHOLD_GB = 3.0

# Below this many heavy models, "most common package" is two or three repos'
# dependency list, not a pattern — the same n=10 floor the rest of the site
# applies to a share (see traffic.py's MIN_UNIQUES).
MIN_HEAVY_MODELS = 10

# "Most used" is the top this-many models by lifetime Docker Hub pulls, among the active
# models with a parsed install.yml. A count rather than a pull threshold because pulls are
# flat across most of the Hub (median ~5,200, interquartile range ~4,500-5,800), so any
# threshold would be arbitrary; 25 is roughly the top quarter of models with an install.yml.
TOP_PULLED_MODELS = 25

# How many packages each chart ranks.
TOP_PACKAGES = 15

# Left out of every count. `ersilia-pack-utils` is Ersilia's own packaging dependency,
# installed by the model template itself rather than chosen for the model, so it tops
# every list (27 of 37 heavy models) while saying nothing about what makes one heavy.
IGNORED_PACKAGES = {"ersilia-pack-utils"}

EMPTY_SECTION = {
    "heaviest_common": dict(EMPTY),
    "most_pulled_common": dict(EMPTY),
}


def build(collected, models=None, threshold_gb=HEAVY_THRESHOLD_GB):
    collected = collected or {}
    packages = collected.get("github_model_packages")
    repos = collected.get("github_repos")
    return {
        "heaviest_common": _heaviest_common(
            packages, collected.get("dockerhub_tags"), models, repos, threshold_gb),
        "most_pulled_common": _most_pulled_common(
            packages, collected.get("dockerhub_images"), models, repos),
    }


def _latest_amd64_size_gb(tags):
    """``{repo: GB}`` from each repository's most recently pushed AMD64 tag — the
    same reading `usage.size_swings` uses for a model's CURRENT size."""
    import pandas as pd

    if tags is None or tags.empty or not \
            {"repo", "architecture", "size_bytes", "pushed_at"}.issubset(tags.columns):
        return {}
    df = tags[as_text(tags["architecture"]) == "amd64"].copy()
    df["pushed_at"] = pd.to_datetime(df["pushed_at"], errors="coerce", utc=True)
    df = df.dropna(subset=["pushed_at", "size_bytes"]).sort_values("pushed_at")
    if df.empty:
        return {}
    latest = df.groupby("repo").last()
    return {repo: float(row["size_bytes"]) / 1e9 for repo, row in latest.iterrows()}


def _heaviest_common(packages, tags, models, repos, threshold_gb):
    """Most common installed packages among models whose Docker image is at
    least `threshold_gb` — which packages show up disproportionately in the
    Hub's heaviest images, not which ones exist hub-wide.

    Counted per MODEL, not per install.yml line: a package listed twice for one
    repository (unusual, but not impossible) would otherwise inflate its count
    without describing a second heavy model.

    Restricted to the Hub's currently active population — status Ready or In
    maintenance, repository not archived — the same `active_repo_names` filter as
    the rest of the Versioning page: a heavy archived model's dependencies
    describe work that has stopped, not the footprint the Hub carries today.
    """
    if packages is None or packages.empty or not {"repo", "package"}.issubset(packages.columns):
        return dict(EMPTY)
    sizes = _latest_amd64_size_gb(tags)
    if not sizes:
        return dict(EMPTY)

    # Heavy AND has a known package list — a model without a parsed install.yml
    # cannot contribute to a package count, so it must not inflate "heavy" either;
    # otherwise the denominator would count models this chart has no data for.
    have_packages = set(as_text(packages["repo"]))
    heavy = {repo for repo, gb in sizes.items() if gb >= threshold_gb} & have_packages
    if not heavy:
        return dict(EMPTY)

    heavy = active_repo_names(models, repos, heavy)
    if len(heavy) < MIN_HEAVY_MODELS:
        return dict(EMPTY)

    counts = _package_counts(packages, heavy)
    if counts is None:
        return dict(EMPTY)
    total = len(heavy)
    return metric(
        counts.index, counts.values,
        "%s appears in %s of %s models at or above %sGB." % (
            counts.index[0], ins.num(int(counts.iloc[0])), ins.num(total), threshold_gb,
        ),
        countNoun="models",
        # Each count is out of the same models, so the chart must not sum a tail.
        nonAdditive=True,
        n=total,
    )


def _most_pulled_common(packages, images, models, repos, top_n=TOP_PULLED_MODELS):
    """Most common installed packages among the `top_n` most-pulled models — what the
    models people actually run are built on.

    Ranked on Docker Hub's lifetime `pull_count`, restricted to models that are active
    (the same `active_repo_names` filter as `heaviest_common`) AND have a parsed
    install.yml, and only then cut to the top `top_n`: cutting first would let a
    legacy-template model with no install.yml take a slot and shrink the sample.
    Suppressed below `MIN_HEAVY_MODELS`, the same floor as the heavy chart.
    """
    if packages is None or packages.empty or not {"repo", "package"}.issubset(packages.columns):
        return dict(EMPTY)
    if images is None or images.empty or not {"name", "pull_count"}.issubset(images.columns):
        return dict(EMPTY)
    import pandas as pd

    names = as_text(images["name"])
    flag = as_text(images.get("is_model")).str.lower() if "is_model" in images.columns \
        else pd.Series(["yes"] * len(images), index=images.index)
    pulls = pd.to_numeric(images["pull_count"], errors="coerce")
    frame = pd.DataFrame({"name": names, "is_model": flag, "pulls": pulls}).dropna()
    frame = frame[frame["is_model"] == "yes"]

    eligible = active_repo_names(models, repos, set(as_text(packages["repo"])))
    frame = frame[frame["name"].isin(eligible)].sort_values(
        ["pulls", "name"], ascending=[False, True])
    top = list(frame["name"].head(top_n))
    if len(top) < MIN_HEAVY_MODELS:
        return dict(EMPTY)

    counts = _package_counts(packages, set(top))
    if counts is None:
        return dict(EMPTY)
    total = len(top)
    return metric(
        counts.index, counts.values,
        "%s appears in %s of the %s most-pulled models." % (
            counts.index[0], ins.num(int(counts.iloc[0])), ins.num(total),
        ),
        countNoun="models",
        # Each count is out of the same models, so the chart must not sum a tail.
        nonAdditive=True,
        n=total,
    )


def _package_counts(packages, repo_names):
    """The `TOP_PACKAGES` most common packages across `repo_names`, as a Series of
    per-MODEL counts, or ``None`` when there is nothing to count.

    Counted per model, not per install.yml line: a package listed twice for one
    repository would otherwise inflate its count without describing a second model.
    `IGNORED_PACKAGES` are dropped. A pip extras spec ("lazyqsar[descriptors]") is
    stripped so it counts under the base package rather than splintering into its own
    label.
    """
    subset = packages[as_text(packages["repo"]).isin(repo_names)].copy()
    if subset.empty:
        return None
    subset["repo"] = as_text(subset["repo"])
    subset["package"] = as_text(subset["package"]).str.lower().str.replace(
        r"\[.*\]", "", regex=True)
    pairs = subset[["repo", "package"]].drop_duplicates()
    pairs = pairs[(pairs["package"] != "") & ~pairs["package"].isin(IGNORED_PACKAGES)]
    counts = pairs["package"].value_counts()
    if counts.empty:
        return None
    return counts.head(TOP_PACKAGES)
