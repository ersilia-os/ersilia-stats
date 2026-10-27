"""Which packages the Hub's models install, from install.yml (fetch_model_packages.py).

WHY THIS EXISTS
----------------
`install.yml` pins exactly what a model's Docker build installs — pip and conda
packages, with version — one file per model repository. Counting it across the Hub says
what the models are built on, which nothing else on the site can: Docker image size says
how heavy a model is, not why.

One count across every active model rather than a cut by image size or by pulls. The
earlier pair of charts, over the heavy (>= 3 GB) and the 25 most-pulled models, each
described a few dozen models chosen by a threshold, and the two lists were dominated by
the same packages anyway.
"""
from . import insights as ins
from .parse import EMPTY, active_repo_names, as_text, metric

# Below this many models with a parsed install.yml, "most common package" is two or
# three repos' dependency list, not a pattern — the same n=10 floor the rest of the site
# applies to a share.
MIN_MODELS = 10

# How many packages the chart ranks.
TOP_PACKAGES = 15

# Left out of the count. `ersilia-pack-utils` is Ersilia's own packaging dependency,
# installed by the model template itself rather than chosen for the model, so it would
# top the list while saying nothing about what any model is built on.
IGNORED_PACKAGES = {"ersilia-pack-utils"}

EMPTY_SECTION = {
    "most_common": dict(EMPTY),
}


def build(collected, models=None):
    collected = collected or {}
    return {
        "most_common": _most_common(
            collected.get("github_model_packages"), models, collected.get("github_repos")),
    }


def _most_common(packages, models, repos):
    """Most common installed packages across every active model with a parsed
    install.yml — what the Hub is built on.

    Restricted to the Hub's currently active population — status Ready or In
    maintenance, repository not archived — through `active_repo_names`, as the rest of
    the Versioning section. A model without a parsed install.yml (a legacy-template
    repository whose dependencies live in its Dockerfile) cannot contribute a package,
    so it is not in the denominator either.
    """
    if packages is None or packages.empty or not {"repo", "package"}.issubset(packages.columns):
        return dict(EMPTY)
    covered = active_repo_names(models, repos, set(as_text(packages["repo"])) - {""})
    if len(covered) < MIN_MODELS:
        return dict(EMPTY)

    counts = _package_counts(packages, covered)
    if counts is None:
        return dict(EMPTY)
    total = len(covered)
    return metric(
        counts.index, counts.values,
        "%s appears in %s of the %s models with an install.yml (%s)." % (
            counts.index[0], ins.num(int(counts.iloc[0])), ins.num(total),
            ins.pct(int(counts.iloc[0]), total),
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
