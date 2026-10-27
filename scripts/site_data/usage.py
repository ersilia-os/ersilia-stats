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
import pandas as pd

from . import insights as ins
from .parse import EMPTY, as_text, metric, to_num

# Models that Ersilia's own CI pulls from Docker Hub on every test run, so their pull
# counts are inflated by automated testing rather than demand: the ersilia package's
# `tests_and_cleanup.yml` workflow runs the playground suite with `--fetch from_dockerhub`
# on the models in `test/playground/config.yml` — eos3b5e as the single model, and
# eos5axz, eos4e40 and eos2r5a as the multiple-model set. eos3b5e is also the default
# test model across ersilia-pack. Re-check that config if it changes.
CI_TEST_MODELS = {"eos3b5e", "eos5axz", "eos4e40", "eos2r5a"}

WEEKDAY_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


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


def build(collected, today=None):
    """Metrics from ``data/dockerhub/images_<date>.csv``.

    Every key degrades to an empty metric when the collector has not run, so the site
    builds from a clone with no Docker Hub data at all.
    """
    images = (collected or {}).get("dockerhub_images")
    tags = (collected or {}).get("dockerhub_tags")
    rows = _model_images(images)

    # The tags-based recency metrics come from a separate collector
    # (fetch_docker_tags.py) and degrade independently of the images snapshot.
    recency = {
        "pull_dormancy": _pull_dormancy(tags, today),
        "arm_vs_amd_size": _arm_vs_amd_size(tags),
        "pull_rhythm_weekday": _pull_rhythm_weekday(tags),
    }

    if not rows:
        return {
            "model_pulls_total": dict(EMPTY),
            "most_pulled_models": {"rows": [], "n": 0},
            **recency,
        }

    total = sum(p for _, p in rows)
    counts = sorted(p for _, p in rows)
    median = counts[len(counts) // 2]

    return {
        "model_pulls_total": _total(rows, total, median),
        "most_pulled_models": _ranked(rows, median),
        **recency,
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

    Each row also says whether the model is one of Ersilia's CI test models
    (`CI_TEST_MODELS`), whose pulls are inflated by automated testing on top of the
    baseline — they top this list for that reason, not for demand.
    """
    scored = [(name, pulls, round(pulls / median, 1)) for name, pulls in rows
              if median and pulls > median * 1.5]
    scored.sort(key=lambda r: -r[1])
    if not scored:
        return {"rows": [], "n": 0,
                "insight": "No model stands clearly above the automated baseline."}
    return {
        "rows": [{"name": name, "pulls": pulls, "times_baseline": mult,
                  "ci_test": "Yes" if name in CI_TEST_MODELS else ""}
                 for name, pulls, mult in scored[:12]],
        "n": len(scored),
        "insight": _ranked_insight(scored, median),
    }


def _ranked_insight(scored, median):
    """Name the leader, and say so when it is a CI test model."""
    leader = scored[0]
    tests = sum(1 for name, _, _ in scored[:10] if name in CI_TEST_MODELS)
    text = "%s models exceed the ~%s baseline; %s leads at %sx it" % (
        ins.num(len(scored)), ins.num(median), leader[0], leader[2])
    if leader[0] in CI_TEST_MODELS:
        text += ", but it is a CI test model"
    elif tests:
        text += "; %s of the top ten are CI test models" % ins.num(tests)
    return text + "."


# ---------------------------------------------------------------------------
# Pull recency, from data/dockerhub/tags_<date>.csv (fetch_docker_tags.py).
#
# `images_<date>.csv` gives a lifetime pull count per repository — a running total
# that never goes down, so an image abandoned a year ago and one pulled this morning
# look identical in it. The tags snapshot instead carries `tag_last_pulled` per TAG
# and per ARCHITECTURE (Docker Hub attributes a pull to an image digest, and amd64 and
# arm64 are always separate digests inside a multi-arch tag), which is what makes
# "when" measurable rather than just "how many, ever".
#
# The honest caveat, stated on every card below: Docker Hub exposes only the MOST
# RECENT pull per digest, never a series, so a repo with many tags contributes many
# recency samples but no volume — this is suggestive of a pattern, not a measurement
# of how much traffic there is.
# ---------------------------------------------------------------------------
def _pull_dormancy(tags, today=None):
    """Time since each model image was last pulled, on ANY tag or architecture.

    One row per repo: the most recent `pulled_at` across every tag and architecture
    that repo publishes. A cumulative pull count never decays; this does.
    """
    if tags is None or tags.empty or "pulled_at" not in tags.columns or "repo" not in tags.columns:
        return dict(EMPTY)
    pulled = pd.to_datetime(tags["pulled_at"], errors="coerce", utc=True)
    last_pull = pulled.groupby(tags["repo"]).max()
    now = pd.Timestamp(today, tz="UTC") if today is not None else pd.Timestamp.now(tz="UTC")
    days = ((now - last_pull).dt.total_seconds() / 86400).dropna()
    if days.empty:
        return dict(EMPTY)

    bins = [(0, 1, "≤1 day"), (1, 7, "2–7 days"), (7, 30, "8–30 days"),
            (30, 90, "1–3 months"), (90, float("inf"), "3 months+")]
    labels = [b[2] for b in bins]
    values = [int(((days >= lo) & (days < hi)).sum()) for lo, hi, _ in bins]
    fresh = values[0] + values[1]
    out = metric(
        labels, values,
        ins.share_of(fresh, len(days), "images", "were pulled within the last week"),
        countNoun="images",
        n=len(days),
    )
    out["ordinal"] = True
    return out


def _arm_vs_amd_size(tags):
    """Per-model points: the newest AMD64 image size against the newest ARM64 one.

    Points below the diagonal are lighter on ARM — usually a leaner base image with
    no x86-only CUDA/MKL wheels pulled in. Both axes are log because sizes span two
    orders of magnitude across the Hub, same reasoning as the other size scatter.
    """
    if tags is None or tags.empty or not {"repo", "architecture", "size_bytes", "pushed_at"} \
            .issubset(tags.columns):
        return {"points": [], "n": 0}
    df = tags.copy()
    df["pushed_at"] = pd.to_datetime(df["pushed_at"], errors="coerce", utc=True)
    df = df.dropna(subset=["pushed_at"]).sort_values("pushed_at")
    # The newest pushed image per (repo, architecture) is the one a fresh pull lands on.
    newest = df.groupby(["repo", "architecture"], as_index=False).last()
    pivot = newest.pivot(index="repo", columns="architecture", values="size_bytes")
    if "amd64" not in pivot.columns or "arm64" not in pivot.columns:
        return {"points": [], "n": 0}
    pivot = pivot.dropna(subset=["amd64", "arm64"])
    pivot = pivot[(pivot["amd64"] > 0) & (pivot["arm64"] > 0)]
    if pivot.empty:
        return {"points": [], "n": 0}

    points = [
        {"name": repo, "amd64": round(float(row["amd64"]) / 1e9, 3),
         "arm64": round(float(row["arm64"]) / 1e9, 3)}
        for repo, row in pivot.iterrows()
    ]
    ratio = float((pivot["arm64"] / pivot["amd64"]).median())
    insight = "The median ARM64 build is %s the size of its AMD64 twin, across %s models " \
             "that publish both." % ("{:.0%}".format(ratio), ins.num(len(points)))
    return {"points": points, "n": len(points), "insight": insight}


def _pull_rhythm_weekday(tags):
    """Every digest's last-pull timestamp, by day of the week (UTC).

    Scheduled automation is flat across the week; human work collapses at the
    weekend. One recency-biased sample per digest, not a volume — stated in the
    card's methodology note.
    """
    if tags is None or tags.empty or "pulled_at" not in tags.columns:
        return dict(EMPTY)
    pulled = pd.to_datetime(tags["pulled_at"], errors="coerce", utc=True).dropna()
    if pulled.empty:
        return dict(EMPTY)
    counts = pulled.dt.day_name().value_counts().reindex(WEEKDAY_ORDER, fill_value=0)
    weekend = int(counts["Saturday"] + counts["Sunday"])
    total = int(counts.sum())
    out = metric(
        WEEKDAY_ORDER, counts.values,
        "%s of last-pull timestamps fall at the weekend, against the 28.6%% an evenly "
        "scheduled automation would produce." % (ins.pct(weekend, total) or "0%"),
        countNoun="digests",
        n=total,
    )
    out["ordinal"] = True
    return out


