"""Model usage, from Docker Hub pull counts.

THE GAP THIS FILLS
------------------
Everything else on this site describes what Ersilia has *made*. Fifteen ways of counting
240 models, and not one of them says whether anybody runs them. That was the largest hole
in the dashboard, and it turned out to be three HTTP requests wide: the models are
distributed as Docker images, and Docker Hub publishes a pull count for each.

AND THEN THE DATA SAID SOMETHING ELSE
-------------------------------------
The headline that fell out first was "1,035,531 pulls across 247 model images". It is not a
usage figure, and publishing it as one would be the most misleading number on the site.

The distribution gives it away. Across 247 models: 10th percentile 3,462, median 4,154, 90th
percentile 4,820 — 224 models inside a 2,500-5,000 band with a standard deviation of **404**.
Human demand does not look like that. Real attention follows a power law, which is exactly
what the same organisation's GitHub stars do: 306, 92, 45, 35, 13. A near-uniform floor of
about four thousand pulls on almost every model is the signature of something pulling every
image on a schedule — continuous integration, most likely Ersilia's own.

So this module reports the BASELINE and the EXCESS OVER IT, separately, and never presents
the total as evidence of interest:

* the baseline is infrastructure. It says images are built and tested, which is worth
  knowing and is not demand.
* the excess is the signal. `eos3b5e` at 29,293 is seven times the median; 17 models sit
  above 5,000. Those numbers mean something the baseline does not.

TWO FURTHER LIMITS, both stated on the cards.

**A pull count is a running total with no history.** Docker Hub exposes no per-day series,
so these are "to date" figures and cannot be turned into a rate.

**A pull is still not a user**, even above the baseline: mirrors pull images and one person
testing in a loop pulls repeatedly. It is a floor on interest, not a headcount.

Infrastructure images (`base`, `conda`, `shell`) are excluded from every figure here. They
are pulled *as a side effect* of running a model rather than chosen, and `base` alone has
31,704 pulls — including them would inflate the headline by roughly 14% with something
nobody asked for.
"""
from . import insights as ins
from .parse import EMPTY, as_text, metric, to_num


def _model_images(images):
    """Model images only, as ``[(name, pulls)]`` sorted by pulls."""
    if images is None or images.empty or "name" not in images.columns:
        return []
    flag = as_text(images.get("is_model")).str.lower()
    pulls = to_num(images.get("pull_count"))
    rows = [(str(images["name"].iloc[i]).strip(), int(pulls.iloc[i]))
            for i in range(min(len(images), len(flag), len(pulls)))
            if flag.iloc[i] == "yes"]
    rows.sort(key=lambda r: (-r[1], r[0]))
    return rows


def build(collected, models=None):
    """Metrics from ``data/dockerhub/images_<date>.csv``.

    Every key degrades to an empty metric when the collector has not run, so the site
    builds from a clone with no Docker Hub data at all.
    """
    images = (collected or {}).get("dockerhub_images")
    rows = _model_images(images)
    if not rows:
        return {
            "model_pulls_total": dict(EMPTY),
            "most_pulled_models": {"rows": [], "n": 0},
            "pull_distribution": dict(EMPTY),
            "image_coverage": dict(EMPTY),
        }

    total = sum(p for _, p in rows)
    counts = sorted(p for _, p in rows)
    median = counts[len(counts) // 2]

    return {
        "model_pulls_total": _total(rows, total, median),
        "most_pulled_models": _ranked(rows, median),
        "pull_distribution": _distribution(counts, median),
        "image_coverage": _coverage(rows, models),
    }


def _total(rows, total, median):
    """The three numbers together, because no one of them stands alone.

    The total is deliberately labelled as including automated pulls. Reporting it as
    "pulls" full stop would let a reader take a million as a million acts of interest,
    when the near-uniform baseline says most of it is a scheduled build.
    """
    above = sum(1 for _, pulls in rows if pulls > median * 1.5)
    return metric(
        ["Image pulls, automated included", "Models with an image",
         "Pulled well above the baseline"],
        [total, len(rows), above],
        "%s image pulls to date, but %s models sit within a narrow band around %s — a "
        "scheduled build, not demand. %s stand clearly above it." % (
            ins.num(total), ins.num(sum(1 for _, p in rows if median * 0.6 <= p <= median * 1.25)),
            ins.num(median), ins.num(above),
        ),
        unit="pulls",
        n=len(rows),
    )


def _ranked(rows, median):
    """Models pulled measurably more than the baseline.

    Ranked by the MULTIPLE of the baseline rather than by raw pulls, because raw pulls
    ranks the schedule. A model at 1.0x has been pulled exactly as often as everything
    else, which is the same as saying nothing about it.
    """
    scored = [(name, pulls, round(pulls / median, 1)) for name, pulls in rows
              if median and pulls > median * 1.5]
    scored.sort(key=lambda r: -r[1])
    if not scored:
        return {"rows": [], "n": 0,
                "insight": "No model stands clearly above the automated baseline."}
    return {
        "rows": [{"name": name, "pulls": pulls, "times_baseline": mult}
                 for name, pulls, mult in scored[:12]],
        "n": len(scored),
        "insight": "%s models exceed the ~%s baseline; %s leads at %sx it." % (
            ins.num(len(scored)), ins.num(median), scored[0][0], scored[0][2],
        ),
    }


def _distribution(counts, median):
    """The shape, which is the actual finding.

    This chart exists to show the reader the baseline directly rather than asking them to
    take the caveat on trust: a spike of models at one pull count, and a thin tail above
    it. Anyone who sees it will draw the right conclusion without being told.
    """
    # Short labels: this card is four columns wide and the histogram draws every label
    # horizontally, so "under 1k" and "1k-2.5k" ran into each other.
    bands = [(0, 1000, "<1k"), (1000, 2500, "1\u20132.5k"), (2500, 5000, "2.5\u20135k"),
             (5000, 10000, "5\u201310k"), (10000, float("inf"), "10k+")]
    labels, values = [], []
    for low, high, label in bands:
        labels.append(label)
        values.append(sum(1 for c in counts if low <= c < high))
    clustered = sum(1 for c in counts if median * 0.6 <= c <= median * 1.25)
    out = metric(
        labels, values,
        # Kept short deliberately: this card is four columns wide and the full argument
        # is in its methodology note. A caption that overflows is a caption nobody reads.
        "%s of %s model images cluster in one band — the automated build." % (
            ins.num(clustered), ins.num(len(counts)),
        ),
        countNoun="models",
        n=len(counts),
    )
    out["ordinal"] = True
    return out


def _coverage(rows, models):
    """Do the registry and the registry of images agree?

    Two ways they can disagree, and both are worth publishing: a model with no image
    cannot be run, and an image with no model row is undocumented. Neither is a
    catastrophe; both are the sort of thing that quietly drifts.
    """
    if models is None or models.empty or "identifier" not in models.columns:
        return dict(EMPTY)
    listed = {i.strip() for i in as_text(models["identifier"]) if i.strip()}
    published = {name for name, _ in rows}
    with_image = len(listed & published)
    return metric(
        ["Model has an image", "No image published"],
        [with_image, len(listed) - with_image],
        # Three columns wide, so this has room for one clause. The count of images with
        # no matching model record is in the methodology note instead.
        ins.share_of(with_image, len(listed), "models", "have a published image"),
        n=len(listed),
    )
