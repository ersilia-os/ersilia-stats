"""Data-quality appendix — how trustworthy is the registry behind these charts?

Two views the site never had:

* **Field completeness** per table, so a thin field is visible rather than silently
  producing a short chart.
* **Project x repository status**, a contingency table that surfaces registry
  inconsistencies — repositories still in progress under projects marked done, and
  repositories linked to no project at all.

This is the honest counterpart to the rest of the site: every chart elsewhere is only
as good as what is filled in here.
"""

from . import insights as ins
from .parse import EMPTY, as_text, col, first_value, metric, parse_multi

# Columns that exist for Airtable's own bookkeeping, not as data.
SKIP_COLUMNS = {"airtable_id"}
THIN_THRESHOLD = 80.0


def build(tables, repos_public):
    return {
        "completeness": _completeness(tables),
        "thin_fields": _thin_fields(tables),
        "project_repo_status": _project_repo_status(tables.get("projects"), repos_public),
        "repo_project_link": _repo_project_link(repos_public),
        "table_sizes": _table_sizes(tables),
    }


def _column_completeness(df):
    rows = len(df)
    if rows == 0:
        return []
    out = []
    for column in df.columns:
        if column in SKIP_COLUMNS:
            continue
        values = as_text(df[column])
        filled = int(((values != "") & (values.str.lower() != "nan")).sum())
        out.append({"column": column, "filled": filled, "total": rows,
                    "pct": round(100.0 * filled / rows, 1)})
    return out


def _completeness(tables):
    """Mean completeness per table, worst first."""
    labels, values, detail = [], [], {}
    for name in sorted(tables):
        columns = _column_completeness(tables[name])
        if not columns:
            continue
        mean = sum(c["pct"] for c in columns) / len(columns)
        labels.append(name.replace("_", " "))
        values.append(round(mean, 1))
        detail[name] = columns
    if not labels:
        return dict(EMPTY)
    order = sorted(range(len(labels)), key=lambda i: values[i])
    labels = [labels[i] for i in order]
    values = [values[i] for i in order]
    out = metric(
        labels, values,
        "Mean share of populated cells per table. The thinnest is %s at %s%%." % (
            labels[0], values[0],
        ),
    )
    out["unit"] = "% of cells populated"
    out["detail"] = detail
    out["n"] = len(labels)
    return out


def _thin_fields(tables, top=18):
    """Every column below the threshold, thinnest first, as a chartable ranking.

    Emitted as labels/values ("table · column" -> % populated) so it can be drawn
    directly rather than only read as a table.
    """
    found = []
    for name in sorted(tables):
        for column in _column_completeness(tables[name]):
            if column["pct"] < THIN_THRESHOLD:
                found.append((
                    "%s · %s" % (name.replace("_", " "), column["column"].replace("_", " ")),
                    column["pct"], column["filled"], column["total"],
                ))
    found.sort(key=lambda r: r[1])
    shown = found[:top]
    out = metric([r[0] for r in shown], [r[1] for r in shown],
                 ("%s fields are under %s%% populated%s." % (
                     ins.num(len(found)), int(THIN_THRESHOLD),
                     "; the %d thinnest are shown" % len(shown) if len(found) > len(shown) else "",
                 )) if found else "Every field is at least %s%% populated." % int(THIN_THRESHOLD),
                 n=len(found))
    out["unit"] = "% populated"
    out["threshold"] = THIN_THRESHOLD
    return out


def _repo_project_link(repos):
    """Public repositories linked to a project, against those that are not.

    The orphan count already existed inside the project/repo heatmap's insight, which
    no chart used, so a real coverage figure was being computed and thrown away. It is
    not a fault to be unlinked — plenty of tooling stands alone — but it does mean the
    portfolio view cannot see that repository.
    """
    if repos is None or repos.empty or "projects" not in repos.columns:
        return dict(EMPTY)
    linked = 0
    for i in range(len(repos)):
        if parse_multi(repos["projects"].iloc[i]):
            linked += 1
    total = len(repos)
    if not total:
        return dict(EMPTY)
    return metric(
        ["Linked", "Not linked"], [linked, total - linked],
        ins.share_of(linked, total, "public repositories", "are linked to a project"),
    )


def _project_repo_status(projects, repos):
    """Repository status against the status of the project it belongs to."""
    if projects is None or projects.empty or repos is None or repos.empty:
        return {"x": [], "y": [], "cells": [], "n": 0}
    if "projects" not in repos.columns or "airtable_id" not in projects.columns:
        return {"x": [], "y": [], "cells": [], "n": 0}

    project_status = dict(zip(as_text(projects["airtable_id"]),
                              as_text(col(projects, "status"))))
    repo_status = col(repos, "status").apply(first_value)

    pairs = []
    orphans = 0
    for i in range(len(repos)):
        linked = parse_multi(repos["projects"].iloc[i])
        if not linked:
            orphans += 1
            continue
        their_status = repo_status.iloc[i]
        for record in linked:
            owner = project_status.get(record)
            if owner and their_status:
                pairs.append((owner, their_status))

    if not pairs:
        return {"x": [], "y": [], "cells": [], "n": 0, "orphans": orphans}

    y_labels = sorted({p[0] for p in pairs})
    x_labels = sorted({p[1] for p in pairs})
    counts = {}
    for owner, their in pairs:
        counts[(owner, their)] = counts.get((owner, their), 0) + 1
    cells = [[x_labels.index(x), y_labels.index(y), value]
             for (y, x), value in sorted(counts.items())]

    # The inconsistency worth naming: live repositories under a finished project.
    live = {"in progress", "idle", "todo", "to do"}
    stale = sum(
        value for (owner, their), value in counts.items()
        if owner.strip().lower() == "done" and their.strip().lower() in live
    )
    return {
        "x": x_labels, "y": y_labels, "cells": cells,
        "n": len(pairs), "orphans": orphans,
        "insight": ins.join(
            "%s repository-project links." % ins.num(len(pairs)),
            ("%s links pair a finished project with a repository that is still "
                 "open." % ins.num(stale))
            if stale else None,
            ("%s public repositories are linked to no project."
                 % ins.num(orphans)) if orphans else None,
        ),
    }


def _table_sizes(tables):
    items = sorted(((name.replace("_", " "), len(df)) for name, df in tables.items()),
                   key=lambda kv: -kv[1])
    if not items:
        return dict(EMPTY)
    return metric([k for k, _ in items], [v for _, v in items],
                  "%s rows across %d source tables in this snapshot." % (
                      ins.num(sum(v for _, v in items)), len(items)),
                  n=len(items))
