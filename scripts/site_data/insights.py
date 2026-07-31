"""Computed takeaways.

Every chart on the site carries a one-line "so what" caption. These are *derived
from the data at build time*, never written by hand, so they cannot drift out of
date when the snapshot changes. Keep them factual and plain — the house voice is
technical, not salesy, and never claims more than the numbers support.

Callers always pass nouns in the form they should appear. Nothing here guesses a
plural: "repository" would become "repositorys", and the captions are user-facing
prose, so the caller owns the wording.
"""


def num(value):
    """Thousands-separated integer."""
    try:
        return "{:,}".format(int(round(float(value))))
    except (TypeError, ValueError):
        return str(value)


def pct(part, whole, digits=0):
    """``part`` as a percentage of ``whole``; empty string when undefined."""
    try:
        whole = float(whole)
        if whole <= 0:
            return ""
        value = 100.0 * float(part) / whole
    except (TypeError, ValueError, ZeroDivisionError):
        return ""
    return ("{:." + str(digits) + "f}%").format(value)


def count_of(count, singular, plural):
    """``"1 project"`` / ``"14 projects"`` — caller supplies both forms."""
    return "%s %s" % (num(count), singular if abs(count) == 1 else plural)


def leader(metric_dict, noun_plural, of_total=None):
    """"Volunteer leads with 55 of 121 role assignments (45%)."""
    labels, values = metric_dict.get("labels", []), metric_dict.get("values", [])
    if not labels:
        return None
    total = of_total if of_total is not None else sum(values)
    share = pct(values[0], total)
    tail = " (%s)" % share if share else ""
    return "%s leads with %s of %s %s%s." % (
        labels[0], num(values[0]), num(total), noun_plural, tail,
    )


def concentration(values, noun_plural, top=3):
    """How much of the total the biggest few account for."""
    ordered = sorted((v for v in values if isinstance(v, (int, float))), reverse=True)
    if len(ordered) <= top:
        return None
    share = pct(sum(ordered[:top]), sum(ordered))
    if not share:
        return None
    return "The top %d account for %s of all %s." % (top, share, noun_plural)


def latest_change(labels, values, noun_plural):
    """Movement between the last two periods of a time series."""
    if len(values) < 2:
        return None
    previous, current = values[-2], values[-1]
    if previous == current:
        return "%s held steady at %s in %s." % (noun_plural.capitalize(), num(current), labels[-1])
    direction = "up from" if current > previous else "down from"
    return "%s in %s: %s, %s %s in %s." % (
        noun_plural.capitalize(), labels[-1], num(current), direction, num(previous), labels[-2],
    )


def span(labels, values, noun_plural):
    """"Grew from 1 to 140 public repositories between 2019Q3 and 2026Q2."""
    if len(labels) < 2 or not values:
        return None
    return "Grew from %s to %s %s between %s and %s." % (
        num(values[0]), num(values[-1]), noun_plural, labels[0], labels[-1],
    )


def busiest(labels, values, singular, plural, period="quarter"):
    if not values:
        return None
    peak = max(range(len(values)), key=lambda i: values[i])
    return "Busiest %s was %s with %s." % (
        period, labels[peak], count_of(values[peak], singular, plural),
    )


def share_of(part, whole, noun_plural, description):
    """"25 of 42 publications (60%) carry a direct Ersilia affiliation."""
    share = pct(part, whole)
    tail = " (%s)" % share if share else ""
    return "%s of %s %s%s %s." % (num(part), num(whole), noun_plural, tail, description)


def join(*parts):
    """Join the non-empty fragments into one caption."""
    return " ".join(p for p in parts if p) or None
