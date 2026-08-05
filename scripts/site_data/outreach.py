"""Events, blog activity, and the conferences Ersilia tracks.

The conferences table was loaded but never read by anything — nine columns and 21
rows of recorded intent (which meetings matter, how often they come round, whether
you can attend without flying) sitting unused while this page ran out of content
halfway down.
"""

from . import insights as ins
from .parse import (EMPTY, col, growth_pair, metric, multi_counts, value_counts, year_counts)


def build_events(events):
    if events is None or events.empty:
        return {"per_year": dict(EMPTY), "by_country": dict(EMPTY),
                "by_organiser": dict(EMPTY),
                "growth": {"labels": [], "series": [], "n": 0}}

    country = col(events, "country_(from_country)")
    located = multi_counts(country)

    per_year = year_counts(col(events, "year"))
    if per_year["labels"]:
        per_year["insight"] = ins.busiest(per_year["labels"], per_year["values"],
                                          "event", "events", period="year")

    by_country = multi_counts(country, top=12)
    if by_country["labels"]:
        by_country["insight"] = ins.leader(located, "located events")

    return {
        "per_year": per_year,
        "growth": _year_growth(per_year, "events"),
        "by_country": by_country,
        "by_organiser": multi_counts(col(events, "organiser"), top=10,
                                     insight="Organisations that convened the most "
                                                 "events Ersilia took part in."),
    }


def build_blogposts(blogposts):
    if blogposts is None or blogposts.empty:
        return {"per_year": dict(EMPTY), "by_category": dict(EMPTY),
                "by_publisher": dict(EMPTY),
                "growth": {"labels": [], "series": [], "n": 0}}

    per_year = year_counts(col(blogposts, "year"))
    if per_year["labels"]:
        per_year["insight"] = ins.busiest(per_year["labels"], per_year["values"],
                                          "post", "posts", period="year")

    by_category = multi_counts(col(blogposts, "category"), top=12)
    if by_category["labels"]:
        by_category["insight"] = ins.leader(by_category, "category assignments")

    publisher = value_counts(col(blogposts, "publisher"))
    if publisher["labels"]:
        own = dict(zip(publisher["labels"], publisher["values"])).get("Ersilia", 0)
        publisher["insight"] = ins.share_of(own, sum(publisher["values"]), "posts",
                                            "were published on Ersilia's own channels")
        publisher["semantics"] = {"Ersilia": "brand", "Other": "neutral"}

    return {
        "per_year": per_year,
        "growth": _year_growth(per_year, "posts"),
        "by_category": by_category,
        "by_publisher": publisher,
    }


def _year_growth(per_year, noun_plural):
    """Turn an already-built per-year metric into a rate-plus-total pair."""
    if not per_year["labels"]:
        return {"labels": [], "series": [], "n": 0}
    running, total = [], 0
    for value in per_year["values"]:
        total += value
        running.append(total)
    return growth_pair(per_year["labels"], per_year["values"], running,
                       noun_plural, period="year")


def build_conferences(conferences):
    """Conferences Ersilia tracks: how often they run and how reachable they are.

    Small (21 rows), so these are shares rather than rankings. `remote_option` is the
    mission-relevant one: a conference you can join remotely is a conference a
    researcher without travel funding can actually attend.
    """
    if conferences is None or conferences.empty:
        return {"by_cadence": dict(EMPTY), "remote": dict(EMPTY)}

    cadence = value_counts(col(conferences, "cadence"))
    if cadence["labels"]:
        cadence["insight"] = ins.leader(cadence, "tracked conferences")

    remote = col(conferences, "remote_option")
    yes = no = 0
    for value in (remote.dropna() if len(remote) else []):
        token = str(value).strip().lower()
        if token in ("yes", "true"):
            yes += 1
        elif token in ("no", "false"):
            no += 1
    remote_metric = dict(EMPTY)
    if yes or no:
        remote_metric = metric(
            ["Remote option", "In person only"], [yes, no],
            ins.share_of(yes, yes + no, "conferences recording the answer",
                         "can be attended remotely"),
        )
    return {"by_cadence": cadence, "remote": remote_metric}
