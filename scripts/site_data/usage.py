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
from .parse import EMPTY, active_repo_names, as_text, metric, parse_multi, to_num

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


def build(collected, models=None, today=None):
    """Metrics from ``data/dockerhub/images_<date>.csv``.

    Every key degrades to an empty metric when the collector has not run, so the site
    builds from a clone with no Docker Hub data at all.
    """
    images = (collected or {}).get("dockerhub_images")
    tags = (collected or {}).get("dockerhub_tags")
    rows = _model_images(images)

    # The tags-based recency metrics come from a separate collector
    # (fetch_docker_tags.py) and degrade independently of the images snapshot.
    repos = (collected or {}).get("github_repos")
    recency = {
        "pull_dormancy": _pull_dormancy(tags, today),
        "arm_vs_amd_size": _arm_vs_amd_size(tags),
        "pull_rhythm_weekday": _pull_rhythm_weekday(tags),
        "pull_rhythm_hour": _pull_rhythm_hour(tags),
        "tag_versioning": _tag_versioning(tags, models, repos),
        "size_swings": _size_swings(tags, models, repos),
    }

    if not rows:
        return {
            "model_pulls_total": dict(EMPTY),
            "most_pulled_models": {"rows": [], "n": 0},
            "pull_distribution": dict(EMPTY),
            "pulls_by_arch": dict(EMPTY),
            "image_coverage": dict(EMPTY),
            "size_vs_pulls": {"points": [], "n": 0},
            **recency,
        }

    total = sum(p for _, p in rows)
    counts = sorted(p for _, p in rows)
    median = counts[len(counts) // 2]

    return {
        "model_pulls_total": _total(rows, total, median),
        "most_pulled_models": _ranked(rows, median),
        "pull_distribution": _distribution(counts, median),
        "pulls_by_arch": _pulls_by_arch(rows, models),
        "image_coverage": _coverage(rows, models),
        "size_vs_pulls": _size_vs_pulls(rows, models),
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


def _arch_by_id(models):
    """``{identifier: "ARM64 and AMD64" | "AMD64 only"}``, from the registry's
    Docker Architecture field. Shared by every chart that splits on architecture
    support, so the category names and the AMD64-only default live in one place.
    """
    if models is None or models.empty or "identifier" not in models.columns \
            or "docker_architecture" not in models.columns:
        return {}
    ids = as_text(models["identifier"])
    archs = models["docker_architecture"]
    arch_by_id = {}
    for i in range(min(len(ids), len(archs))):
        ident = ids.iloc[i].strip()
        if not ident:
            continue
        tokens = {t.strip().upper() for t in parse_multi(archs.iloc[i])}
        if not tokens:
            continue
        arch_by_id[ident] = "ARM64 and AMD64" if "ARM64" in tokens else "AMD64 only"
    return arch_by_id


def _pulls_by_arch(rows, models):
    """Median Docker Hub pulls, split by whether the image also builds for ARM64.

    Joined on the model identifier against the same Airtable Docker Architecture
    column ``models.on_arm`` reads. The rest of this page says how many images
    exist and how much they are pulled; this is the one chart that asks whether
    those two questions interact — whether a multi-architecture image is pulled
    any differently from an AMD64-only one, or whether ARM64 support is as
    invisible in the pull counts as it is in most Docker Hub browsing.
    """
    arch_by_id = _arch_by_id(models)
    if not arch_by_id:
        return dict(EMPTY)

    groups = {"ARM64 and AMD64": [], "AMD64 only": []}
    for name, pulls in rows:
        category = arch_by_id.get(name)
        if category:
            groups[category].append(pulls)
    groups = {label: pulls for label, pulls in groups.items() if pulls}
    if not groups:
        return dict(EMPTY)

    labels = list(groups.keys())
    medians = {label: sorted(pulls)[len(pulls) // 2] for label, pulls in groups.items()}
    values = [medians[label] for label in labels]
    total_n = sum(len(pulls) for pulls in groups.values())

    both, amd_only = groups.get("ARM64 and AMD64"), groups.get("AMD64 only")
    if both and amd_only:
        insight = (
            "Median %s pulls for images that also build for ARM64, against %s for "
            "AMD64-only, across %s images with a recorded architecture." % (
                ins.num(medians["ARM64 and AMD64"]), ins.num(medians["AMD64 only"]),
                ins.num(total_n),
            )
        )
    else:
        insight = "%s images with a recorded architecture; median %s pulls." % (
            ins.num(total_n), ins.num(values[0]),
        )
    return metric(labels, values, insight, n=total_n)


def _size_vs_pulls(rows, models):
    """Per-model points: image size (GB) against Docker Hub pulls, split by whether
    the image also builds for ARM64.

    Both axes are LINEAR, unlike every other scatter on this site: pulls have a long
    tail org-wide, but within one model's images the range is narrow enough that a log
    axis would only compress it, and image size does not span orders of magnitude at
    all. Coloured by architecture support because that is the one trait already known
    to matter for low-bandwidth, low-resource deployments — the question this asks is
    whether it also shows up as a pull-count difference, not whether size itself does.
    """
    if models is None or models.empty or "identifier" not in models.columns \
            or "image_size" not in models.columns:
        return {"points": [], "n": 0}

    arch_by_id = _arch_by_id(models)
    ids = as_text(models["identifier"])
    sizes = to_num(models["image_size"])
    size_by_id = {}
    for i in range(min(len(ids), len(sizes))):
        ident = ids.iloc[i].strip()
        size = float(sizes.iloc[i])
        if ident and size > 0:
            # Registry records image_size in MB; GB matches the size-distribution card.
            size_by_id[ident] = round(size / 1024.0, 2)

    points = [
        {"name": name, "size": size_by_id[name], "pulls": pulls, "category": arch_by_id[name]}
        for name, pulls in rows if name in size_by_id and name in arch_by_id
    ]
    if not points:
        return {"points": [], "n": 0}

    both = [p["pulls"] for p in points if p["category"] == "ARM64 and AMD64"]
    amd_only = [p["pulls"] for p in points if p["category"] == "AMD64 only"]
    insight = "%s model images with a size, a pull count and a recorded architecture." % (
        ins.num(len(points)),
    )
    if both and amd_only:
        both_median = ins.num(sorted(both)[len(both) // 2])
        amd_only_median = ins.num(sorted(amd_only)[len(amd_only) // 2])
        insight = "Median %s pulls for images that also build for ARM64, against %s for " \
                  "AMD64-only, across %s images." % (
                      both_median, amd_only_median, ins.num(len(points)),
                  )
    return {"points": points, "n": len(points), "insight": insight}


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


def _tag_versioning(tags, models=None, repos=None):
    """Whether each model's Docker Hub tags include a proper semver-style version
    tag, or only ``dev``, ``rolling`` (``latest``) and dated snapshot tags.

    The collector classifies every tag into one of five kinds at fetch time
    (``dated``, ``dev``, ``version``, ``rolling``, ``other``); this asks a per-MODEL
    question of that classification, the Docker Hub counterpart to the GitHub-side
    'Past v1.0.0?' column on the Versioning section's release-history table. A model
    can satisfy one without the other: a GitHub release does not by itself republish
    the image under a matching Docker tag, and a repository can be re-tagged on
    Docker Hub without a GitHub release to go with it.

    Restricted to the Hub's currently active population — status Ready or In
    maintenance, repository not archived — via the same `active_repo_names` filter
    as the Versioning page's GitHub-side figures, so the two describe the same set
    of models.
    """
    if tags is None or tags.empty or not {"repo", "tag_kind"}.issubset(tags.columns):
        return dict(EMPTY)
    active = active_repo_names(models, repos, set(as_text(tags["repo"])))
    tags = tags[as_text(tags["repo"]).isin(active)]
    if tags.empty:
        return dict(EMPTY)
    kinds = tags.groupby("repo")["tag_kind"].apply(lambda s: set(as_text(s)))
    if kinds.empty:
        return dict(EMPTY)
    has_version = kinds.apply(lambda s: "version" in s)
    versioned, unversioned = int(has_version.sum()), int((~has_version).sum())
    total = versioned + unversioned
    if not total:
        return dict(EMPTY)
    return metric(
        ["Has a semver-tagged image", "Dev/rolling/dated tags only"],
        [versioned, unversioned],
        ins.share_of(versioned, total, "models with a Docker image",
                     "publish at least one semver-tagged version"),
        n=total,
    )


def _size_swings(tags, models=None, repos=None):
    """Docker image size, a model's FIRST recorded build against its LATEST —
    which models have grown or shrunk the most since Docker Hub started tracking
    them, not just how big they are today.

    AMD64 only: architecture is a separate question (`arm_vs_amd_size`, elsewhere
    on this page), and mixing two architectures' sizes into one 'first vs latest'
    figure would compare builds that were never meant to match. Repositories with
    only one recorded build have nothing to swing against and are excluded, same
    reasoning as `releases.cadence`'s single-release repos.

    Restricted to the Hub's currently active population, the same
    `active_repo_names` filter as the rest of the Versioning page: a swing on an
    archived or not-yet-Ready model describes work that has since stopped, not
    the Hub's current packaging trend.
    """
    if tags is None or tags.empty or not \
            {"repo", "architecture", "size_bytes", "pushed_at"}.issubset(tags.columns):
        return {"rows": [], "n": 0}
    df = tags[as_text(tags["architecture"]) == "amd64"].copy()
    df["pushed_at"] = pd.to_datetime(df["pushed_at"], errors="coerce", utc=True)
    df = df.dropna(subset=["pushed_at", "size_bytes"]).sort_values("pushed_at")

    active = active_repo_names(models, repos, set(as_text(df["repo"])))
    df = df[as_text(df["repo"]).isin(active)]

    rows = []
    for repo, group in df.groupby("repo"):
        if len(group) < 2:
            continue
        first_gb = float(group.iloc[0]["size_bytes"]) / 1e9
        latest_gb = float(group.iloc[-1]["size_bytes"]) / 1e9
        if first_gb <= 0:
            continue
        swing = latest_gb - first_gb
        rows.append({
            "name": repo,
            "swing_abs": round(abs(swing), 2),
            "direction": "Grew" if swing > 0 else ("Shrank" if swing < 0 else "Unchanged"),
            "first_size": round(first_gb, 2),
            "latest_size": round(latest_gb, 2),
        })
    if not rows:
        return {"rows": [], "n": 0}
    rows.sort(key=lambda r: -r["swing_abs"])

    grown = sum(1 for r in rows if r["direction"] == "Grew")
    shrunk = sum(1 for r in rows if r["direction"] == "Shrank")
    biggest = rows[0]
    return {
        "rows": rows[:12],
        "n": len(rows),
        "insight": "%s models have grown and %s have shrunk since their first recorded "
                  "build; %s swung the most, %s to %s GB." % (
                      ins.num(grown), ins.num(shrunk), biggest["name"],
                      biggest["first_size"], biggest["latest_size"],
                  ),
    }


def _pull_rhythm_hour(tags):
    """Every digest's last-pull timestamp, by hour of day (UTC)."""
    if tags is None or tags.empty or "pulled_at" not in tags.columns:
        return {"labels": [], "values": [], "n": 0}
    pulled = pd.to_datetime(tags["pulled_at"], errors="coerce", utc=True).dropna()
    if pulled.empty:
        return {"labels": [], "values": [], "n": 0}
    counts = pulled.dt.hour.value_counts().reindex(range(24), fill_value=0)
    peak = int(counts.values.argmax())
    return metric(
        [str(h) for h in range(24)], counts.values,
        "Busiest hour is %02d:00 UTC, across %s last-pull timestamps." % (
            peak, ins.num(int(counts.sum())),
        ),
        countNoun="digests",
        n=int(counts.sum()),
    )
