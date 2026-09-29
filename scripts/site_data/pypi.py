"""PyPI packages — releases, download counts (rolling window), Python support.

From ``scripts/fetch_pypi.py``, itself two free, keyless PyPI APIs: the package JSON
API (releases, licence, ``requires_python``) and pypistats.org (a rolling download
window, commonly 90-180 days — never a lifetime total, because PyPI exposes no
per-day history beyond what pypistats.org itself retains). Every caption here says
"window", not "total", for exactly that reason.

Six packages, hand-maintained in ``fetch_pypi.py`` because PyPI has no "list by
organisation" endpoint. Every metric below is one point per package, not a
distribution — six packages is a ranking, not a population large enough to bucket.

Country, OS and CPU-architecture detail comes from a SEPARATE, manual source: Google
BigQuery's public dataset, queried by hand and converted with
``scripts/convert_pypi_geo.py`` (see its docstring for why this one is not fetched).
It currently covers 3 of the 6 packages — ``isaura``, ``eosce`` and ``olinda`` simply
have too little volume to appear in a BigQuery sample of this size — so every caption
that uses it says which packages, rather than implying it describes all six.
"""
from . import insights as ins
from .parse import EMPTY, as_text, metric, series_metric, to_num

EMPTY_SECTION = {
    "packages": {"rows": [], "n": 0},
    "download_share": dict(EMPTY),
    "recent_downloads": {"labels": [], "series": [], "n": 0},
    "first_release_year": dict(EMPTY),
    "release_recency": dict(EMPTY),
    "downloads_by_country": dict(EMPTY),
    "top_countries": dict(EMPTY),
}


def build(collected):
    """Metrics from ``data/pypi/packages_<date>.csv`` and, independently,
    ``data/pypi_geo/downloads_<date>.csv``.

    The two sources refresh on different schedules (one fetched, one manual) and
    either can be absent without the other being affected, so every key degrades to
    an empty metric on its own rather than the whole section going blank together.
    """
    out = dict(EMPTY_SECTION)

    packages = (collected or {}).get("pypi_packages")
    if packages is not None and not packages.empty and "package" in packages.columns:
        rows = _rows(packages)
        if rows:
            out["packages"] = _ranked(rows)
            out["download_share"] = _download_share(rows)
            out["recent_downloads"] = _recent_downloads(rows)
            out["first_release_year"] = _first_release_year(rows)
            out["release_recency"] = _release_recency(rows)

    geo = (collected or {}).get("pypi_geo_downloads")
    if geo is not None and not geo.empty and "country_code" in geo.columns:
        by_country, geo_packages = _by_country(geo)
        if by_country:
            out["downloads_by_country"] = _downloads_by_country(by_country, geo_packages)
            out["top_countries"] = _top_countries(by_country, geo_packages)

    return out


def _rows(packages):
    """One dict per package, numeric fields coerced and the release dates trimmed to
    their year — nothing downstream needs more precision than that."""
    names = as_text(packages["package"])
    versions = as_text(packages.get("latest_version"))
    releases = to_num(packages.get("total_releases"))
    window_total = to_num(packages.get("downloads_window_total"))
    last_30d = to_num(packages.get("downloads_last_30d"))
    last_7d = to_num(packages.get("downloads_last_7d"))
    first = as_text(packages.get("first_release_date"))
    latest = as_text(packages.get("latest_release_date"))

    out = []
    for i in range(len(packages)):
        name = names.iloc[i]
        if not name:
            continue
        out.append({
            "name": name,
            "version": versions.iloc[i] if i < len(versions) else "",
            "releases": int(releases.iloc[i]) if i < len(releases) else 0,
            "window_total": int(window_total.iloc[i]) if i < len(window_total) else 0,
            "last_30d": int(last_30d.iloc[i]) if i < len(last_30d) else 0,
            "last_7d": int(last_7d.iloc[i]) if i < len(last_7d) else 0,
            "first_release": (first.iloc[i] if i < len(first) else "")[:4],
            "latest_release": (latest.iloc[i] if i < len(latest) else "")[:4],
        })
    # Every chart on this page orders packages the same way — by window downloads —
    # so a reader who has placed one bar can find the same package in the next chart.
    out.sort(key=lambda r: (-r["window_total"], r["name"]))
    return out


def _ranked(rows):
    """One row per package: releases, latest version, and the three download windows
    together, so a reader can see recent momentum (7d, 30d) against the tracked
    window total on one line rather than across separate cards."""
    return {
        "rows": [{
            "name": r["name"], "version": r["version"], "releases": r["releases"],
            "window_total": r["window_total"], "last_30d": r["last_30d"],
            "last_7d": r["last_7d"],
        } for r in rows],
        "n": len(rows),
        "insight": "%s packages on PyPI; %s leads with %s downloads in the tracked window." % (
            ins.num(len(rows)), rows[0]["name"], ins.num(rows[0]["window_total"]),
        ),
    }


def _download_share(rows):
    """Part-to-whole of the SAME window total the ranked table shows — six packages
    is inside the donut's six-segment limit, so nothing here is grouped as 'other'."""
    labels = [r["name"] for r in rows]
    values = [r["window_total"] for r in rows]
    total = sum(values)
    if not total:
        return dict(EMPTY)
    return metric(
        labels, values,
        ins.share_of(values[0], total, "window downloads", "are " + labels[0]),
    )


def _recent_downloads(rows):
    """Last 30 days against last 7 days, per package — recent momentum, distinct from
    the window-total figure elsewhere on the page, which spans several months."""
    labels = [r["name"] for r in rows]
    last_30 = [r["last_30d"] for r in rows]
    last_7 = [r["last_7d"] for r in rows]
    if not any(last_30):
        return {"labels": [], "series": [], "n": 0}
    return series_metric(
        labels,
        [{"name": "Last 30 days", "values": last_30}, {"name": "Last 7 days", "values": last_7}],
        "%s leads recent downloads with %s in the last 30 days." % (
            labels[0], ins.num(last_30[0]),
        ),
    )


def _year_phrase(labels):
    if not labels:
        return ""
    if labels[0] == labels[-1]:
        return "in %s" % labels[0]
    return "between %s and %s" % (labels[0], labels[-1])


def _first_release_year(rows):
    """Packages by the year they first appeared on PyPI — the org's packaging
    history, not its current activity."""
    years = {}
    for r in rows:
        y = r["first_release"]
        if y.isdigit():
            years[y] = years.get(y, 0) + 1
    if not years:
        return dict(EMPTY)
    labels = sorted(years)
    values = [years[y] for y in labels]
    out = metric(
        labels, values,
        "%s packages on PyPI, first published %s." % (ins.num(sum(values)), _year_phrase(labels)),
        countNoun="packages",
    )
    out["ordinal"] = True
    return out


def _release_recency(rows):
    """Packages by the year of their MOST RECENT release — is each one still
    maintained, or shipped once and left. With six packages this is six data points,
    not a trend; read alongside the ranked table's version and release count."""
    years = {}
    for r in rows:
        y = r["latest_release"]
        if y.isdigit():
            years[y] = years.get(y, 0) + 1
    if not years:
        return dict(EMPTY)
    labels = sorted(years)
    values = [years[y] for y in labels]
    current_year = labels[-1]
    out = metric(
        labels, values,
        "%s of %s packages last released in %s." % (
            ins.num(years[current_year]), ins.num(sum(values)), current_year,
        ),
        countNoun="packages",
    )
    out["ordinal"] = True
    return out


def _by_country(geo):
    """``({country_name: downloads}, [package, ...])`` from the geo snapshot.

    Keyed by the resolved full name rather than the ISO code, because that is what
    the map chart and the front-end's country-name alias table expect — matching the
    convention every other map-fed metric on this site already follows (see
    ``reach.py``). Falls back to the bare code for anything ``convert_pypi_geo.py``
    could not resolve, so a row is never silently dropped for want of a name.
    """
    names = as_text(geo.get("country_name"))
    codes = as_text(geo.get("country_code"))
    downloads = to_num(geo.get("downloads"))
    counts = {}
    for i in range(min(len(geo), len(downloads))):
        name = names.iloc[i] if i < len(names) else ""
        code = codes.iloc[i] if i < len(codes) else ""
        label = name or code
        if not label:
            continue
        counts[label] = counts.get(label, 0) + int(downloads.iloc[i])
    packages = sorted(set(as_text(geo.get("package")))) if "package" in geo.columns else []
    packages = [p for p in packages if p]
    return counts, packages


def _coverage_note(packages):
    if not packages:
        return ""
    named = packages[0] if len(packages) == 1 else ", ".join(packages[:-1]) + " and " + packages[-1]
    return "Covers %s only — the rest have too little BigQuery-sampled volume to appear." % named


def _downloads_by_country(counts, packages):
    """Every country with a recorded download, for the map. Hong Kong and Taiwan
    have real totals here but no shape in the site's simplified world map — see
    ``top_countries`` for a form that does not depend on map geometry."""
    items = sorted(counts.items(), key=lambda kv: -kv[1])
    labels = [k for k, _ in items]
    values = [v for _, v in items]
    return metric(
        labels, values,
        ins.join("%s countries recorded a download." % ins.num(len(items)),
                 _coverage_note(packages) or None),
    )


def _top_countries(counts, packages):
    """The same counts as a ranking, so a country the map cannot shade — Hong Kong
    and Taiwan are absent from this site's simplified world geometry — still appears
    somewhere on the page."""
    items = sorted(counts.items(), key=lambda kv: -kv[1])[:12]
    if not items:
        return dict(EMPTY)
    labels = [k for k, _ in items]
    values = [v for _, v in items]
    total = sum(counts.values())
    return metric(
        labels, values,
        ins.join(
            ins.leader({"labels": labels, "values": values}, "downloads", of_total=total),
            _coverage_note(packages) or None,
        ),
    )
