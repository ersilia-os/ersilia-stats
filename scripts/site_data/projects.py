"""Projects section — lifecycle, concurrency and status.

The lead chart is a Gantt timeline. The previous site only had "active projects per
quarter", which flattens away exactly what a portfolio view is for: which projects
overlap, which ran long, and what is running right now.
"""
import pandas as pd

from . import insights as ins
from .parse import as_text, col, growth_pair, metric, series_metric, value_counts

# Airtable's project states mapped onto the house semantic tokens, so "in progress"
# is the same colour in every chart on the site.
STATUS_SEMANTICS = {
    "done": "good",
    "in progress": "brand",
    "stuck": "bad",
    "todo": "neutral",
    "to do": "neutral",
}


def build(projects, today):
    if projects is None or projects.empty:
        empty = {"labels": [], "values": [], "n": 0}
        return {"status": empty, "per_year": empty, "active_over_time": empty,
                "timeline": {"rows": [], "n": 0}, "duration": empty,
                "growth": {"labels": [], "series": [], "n": 0}}

    start = pd.to_datetime(col(projects, "start_date"), errors="coerce")
    end = pd.to_datetime(col(projects, "end_date"), errors="coerce")
    status = as_text(col(projects, "status"))

    return {
        "status": _status(projects, status),
        "per_year": _per_year(start),
        "growth": _growth(start),
        "active_over_time": _active_over_time(start, end, today),
        "timeline": _timeline(projects, start, end, status, today),
        "duration": _duration(start, end, status, today),
    }


def _status(projects, status):
    out = value_counts(status)
    in_progress = int((status.str.lower() == "in progress").sum())
    out["insight"] = ins.share_of(in_progress, len(projects), "projects", "are currently running")
    out["semantics"] = {
        label: STATUS_SEMANTICS.get(label.strip().lower(), "neutral")
        for label in out["labels"]
    }
    return out


def _per_year(start):
    years = start.dropna().dt.year
    counts = years.value_counts().sort_index()
    labels = [str(int(y)) for y in counts.index]
    return metric(labels, counts.values,
                  ins.busiest(labels, list(counts.values), "project", "projects", period="year"))


def _growth(start):
    """Projects started per year over the running total."""
    years = start.dropna().dt.year
    if years.empty:
        return {"labels": [], "series": [], "n": 0}
    counts = years.value_counts().sort_index()
    full = range(int(counts.index.min()), int(counts.index.max()) + 1)
    per_year = [int(counts.get(y, 0)) for y in full]
    running, total = [], 0
    for value in per_year:
        total += value
        running.append(total)
    return growth_pair([str(y) for y in full], per_year, running, "projects",
                       period="year")


def _active_over_time(start, end, today):
    """Projects started and not yet ended, per quarter."""
    if not start.notna().any():
        return {"labels": [], "values": [], "n": 0}
    quarters = pd.period_range(start.dropna().min().to_period("Q"), today.to_period("Q"), freq="Q")
    labels, values = [], []
    for quarter in quarters:
        q_start, q_end = quarter.start_time, quarter.end_time
        live = (start <= q_end) & (end.isna() | (end >= q_start)) & start.notna()
        labels.append(str(quarter))
        values.append(int(live.sum()))
    peak = max(range(len(values)), key=lambda i: values[i]) if values else 0
    insight = None
    if values:
        insight = "Peak concurrency was %s in %s; %s running now." % (
            ins.count_of(values[peak], "project", "projects"), labels[peak], ins.num(values[-1]),
        )
    return metric(labels, values, insight, n=int(values[-1]) if values else 0)


def _timeline(projects, start, end, status, today):
    """Gantt rows, sorted by start date. Open-ended projects run to today.

    Project names are organisational, not personal, so they are safe to publish —
    unlike anything from the community table.
    """
    names = as_text(col(projects, "name"))
    rows = []
    for i in range(len(projects)):
        if pd.isna(start.iloc[i]):
            continue
        finish = end.iloc[i]
        open_ended = pd.isna(finish)
        finish = today if open_ended else finish
        rows.append({
            "name": names.iloc[i] if i < len(names) else "",
            "start": start.iloc[i].strftime("%Y-%m-%d"),
            "end": pd.Timestamp(finish).strftime("%Y-%m-%d"),
            "status": status.iloc[i] if i < len(status) else "",
            "open": bool(open_ended),
            "months": round(max((pd.Timestamp(finish) - start.iloc[i]).days, 0) / 30.44, 1),
        })
    rows.sort(key=lambda r: r["start"])
    overdue = sum(
        1 for r in rows
        if r["status"].strip().lower() != "done" and r["end"] < today.strftime("%Y-%m-%d")
    )
    insight = None
    if rows:
        insight = "%s projects, %s to %s%s." % (
            ins.num(len(rows)), rows[0]["start"][:7], max(r["end"] for r in rows)[:7],
            ("; %s past its end date" % ins.num(overdue)) if overdue else "",
        )
    return {
        "rows": rows,
        "n": len(rows),
        "today": today.strftime("%Y-%m-%d"),
        "semantics": {
            s: STATUS_SEMANTICS.get(s.strip().lower(), "neutral")
            for s in {r["status"] for r in rows}
        },
        "insight": insight,
    }


def _duration(start, end, status, today):
    """Median run length of finished vs still-running projects."""
    finished = start.notna() & end.notna()
    running = start.notna() & end.isna()
    labels, values = [], []
    if finished.any():
        labels.append("Completed")
        values.append(round(((end - start)[finished].dt.days / 30.44).median(), 1))
    if running.any():
        labels.append("Still running")
        values.append(round(((today - start)[running].dt.days / 30.44).median(), 1))
    if not labels:
        return {"labels": [], "values": [], "n": 0}
    # A caption that restates its own title tells the reader nothing; give the figures.
    # Running projects are measured to today, so their median is a floor, not a length.
    pairs = dict(zip(labels, values))
    if "Completed" in pairs and "Still running" in pairs:
        insight = ("Median %s months once finished; %s so far for those running."
                   % (pairs["Completed"], pairs["Still running"]))
    else:
        insight = "Median run length: %s months." % values[0]
    # No `total`: these are magnitudes in months, not parts of a whole, so the
    # meters must show the unit rather than a meaningless percentage.
    out = metric(labels, values, insight)
    out["n"] = int(finished.sum() + running.sum())
    out["unit"] = "months"
    return out
