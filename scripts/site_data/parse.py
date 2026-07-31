"""Parsing and aggregation primitives shared by the section builders.

Every builder returns *metric* dicts in one of a few shapes, which
``site/js/charts.js`` knows how to draw:

``{labels, values}``        categorical / time series
``{labels, series:[…]}``    multi-series (stacked, grouped, combo)
``{points:[…]}``            scatter
``{x, y, cells:[[xi,yi,v]]}``  heatmap / matrix
``{rows:[…]}``              gantt
``{labels, values, mean}``  histogram

All of them may carry ``insight`` (a computed one-line takeaway) and ``n``.
"""
import ast
from collections import Counter

import pandas as pd


# ---------------------------------------------------------------------------
# Cell parsing
# ---------------------------------------------------------------------------
def parse_multi(value):
    """Return a clean list of strings from an Airtable cell.

    Handles list-repr strings like ``"['A', 'B']"`` (how linked records and
    multi-selects arrive), comma-separated strings like ``"a, b, c"``, and plain
    single values. Empty/NaN -> ``[]``.
    """
    if value is None:
        return []
    text = str(value).strip()
    if text == "" or text.lower() == "nan":
        return []
    if text.startswith("[") and text.endswith("]"):
        try:
            parsed = ast.literal_eval(text)
            if isinstance(parsed, (list, tuple)):
                return [str(x).strip() for x in parsed if str(x).strip()]
        except (ValueError, SyntaxError):
            pass
        text = text.strip("[]")
    return [p.strip().strip("'\"") for p in text.split(",") if p.strip().strip("'\"")]


def first_value(value):
    """First entry of a multi-value cell, or ``None``."""
    items = parse_multi(value)
    return items[0] if items else None


def col(df, *names):
    """First column present in ``df`` among ``names``, as a Series (else empty)."""
    for name in names:
        if name in df.columns:
            return df[name]
    return pd.Series(dtype=object)


def to_num(series):
    return pd.to_numeric(series, errors="coerce").fillna(0)


def as_text(series):
    """A guaranteed-string, stripped Series. Missing values become ``""``.

    ``series.astype(str)`` is NOT safe here: whether it renders a missing value as
    the string ``"nan"`` or leaves it as a float differs between pandas versions,
    and ``.str.strip()`` then reintroduces NaN for any non-string element. That is
    exactly how a build that passed on pandas 2.3 died on 2.2 with
    ``'float' object has no attribute 'lower'``. Filling before converting removes
    the ambiguity, so downstream ``.lower()`` and ``.str`` calls are always safe.
    """
    if series is None:
        return pd.Series(dtype=object)
    return series.fillna("").astype(str).str.strip()


# ---------------------------------------------------------------------------
# Metric constructors
# ---------------------------------------------------------------------------
def metric(labels, values, insight=None, **extra):
    out = {"labels": [str(x) for x in labels], "values": [_clean(v) for v in values]}
    out["n"] = int(sum(v for v in out["values"] if isinstance(v, (int, float))))
    if insight:
        out["insight"] = insight
    out.update(extra)
    return out


def _clean(value):
    """Coerce to a JSON-native number: ints stay ints, floats round to 2dp.

    pandas hands back numpy scalars (``int64``, ``float64``), which ``json`` refuses
    to serialise — ``.item()`` unwraps them to Python types.
    """
    if hasattr(value, "item"):  # numpy scalar
        value = value.item()
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, float):
        return int(value) if float(value).is_integer() else round(value, 2)
    if isinstance(value, int):
        return int(value)
    return value


EMPTY = {"labels": [], "values": [], "n": 0}


def multi_counts(series, top=None, insight=None):
    """Count occurrences across (possibly multi-value) cells."""
    counter = Counter()
    for value in series.dropna():
        for item in parse_multi(value):
            counter[item] += 1
    items = counter.most_common(top)
    out = metric([k for k, _ in items], [v for _, v in items], insight)
    out["n"] = int(sum(counter.values()))
    out["distinct"] = len(counter)
    return out


def value_counts(series, top=None, insight=None):
    """Count plain single-value cells (no multi-value splitting)."""
    clean = as_text(series)
    clean = clean[(clean != "") & (clean.str.lower() != "nan")]
    counts = clean.value_counts()
    if top:
        counts = counts.head(top)
    return metric(counts.index, counts.values, insight)


def year_counts(series, insight=None):
    """Counts by integer year, ascending. Years <= 1990 are treated as strays."""
    years = pd.to_numeric(series, errors="coerce").dropna().astype(int)
    years = years[years > 1990]
    counts = years.value_counts().sort_index()
    return metric([str(int(i)) for i in counts.index], counts.values, insight)


def quarter_counts(series):
    """Datetime-ish series -> counts per calendar quarter, ascending."""
    dates = pd.to_datetime(series, errors="coerce").dropna()
    if dates.empty:
        return pd.Series(dtype=int)
    return dates.dt.to_period("Q").value_counts().sort_index()


def dense_quarters(counts):
    """Reindex a quarterly Series over every quarter in its range (zero-filled).

    The raw ``value_counts`` skips quarters with no activity, which makes a
    cumulative curve lie about its slope and a bar chart hide the gaps.
    """
    if counts.empty:
        return counts
    full = pd.period_range(counts.index.min(), counts.index.max(), freq="Q")
    return counts.reindex(full, fill_value=0)


def cumulative(counts, insight=None):
    counts = dense_quarters(counts)
    running = counts.cumsum()
    return metric([str(i) for i in running.index], running.values, insight)


def series_metric(labels, series, insight=None, **extra):
    """Multi-series metric: ``series`` is ``[{"name": …, "values": […]}, …]``."""
    out = {
        "labels": [str(x) for x in labels],
        "series": [
            {"name": s["name"], "values": [_clean(v) for v in s["values"]]}
            for s in series
        ],
    }
    out["n"] = int(sum(sum(s["values"]) for s in out["series"]))
    if insight:
        out["insight"] = insight
    out.update(extra)
    return out


def top_by(df, value_col, name_col, n=12, insight=None):
    """Top-n rows by a numeric column, dropping zeroes."""
    if value_col not in df.columns or name_col not in df.columns:
        return dict(EMPTY)
    ranked = df.copy()
    ranked["_v"] = to_num(ranked[value_col])
    ranked = ranked.sort_values("_v", ascending=False).head(n)
    ranked = ranked[ranked["_v"] > 0]
    # n is the number of ranked entries, not the sum of a "top N" column, which
    # would read as a total the chart does not show.
    return metric(as_text(ranked[name_col]), ranked["_v"], insight, n=int(len(ranked)))
