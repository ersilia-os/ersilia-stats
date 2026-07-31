"""Events and blog activity."""
import pandas as pd

from . import insights as ins
from .parse import EMPTY, col, metric, multi_counts, quarter_counts, value_counts, year_counts


def build_events(events):
    if events is None or events.empty:
        return {"per_year": dict(EMPTY), "by_country": dict(EMPTY),
                "by_organiser": dict(EMPTY)}

    country = col(events, "country_(from_country)")
    located = multi_counts(country)
    missing = int(len(events) - located["n"])

    per_year = year_counts(col(events, "year"))
    if per_year["labels"]:
        per_year["insight"] = ins.join(
            ins.busiest(per_year["labels"], per_year["values"], "event", "events", period="year"),
            ins.latest_change(per_year["labels"], per_year["values"], "events"),
        )

    by_country = multi_counts(country, top=12)
    if by_country["labels"]:
        by_country["insight"] = ins.join(
            ins.leader(located, "events with a country on file"),
            ("No country recorded for %s — many are online." %
             ins.count_of(missing, "event", "events")) if missing > 0 else None,
        )

    return {
        "per_year": per_year,
        "by_country": by_country,
        "by_organiser": multi_counts(col(events, "organiser"), top=10,
                                     insight="Organisations that convened the most events Ersilia took part in."),
    }


def build_blogposts(blogposts):
    if blogposts is None or blogposts.empty:
        return {"per_year": dict(EMPTY), "by_category": dict(EMPTY),
                "by_publisher": dict(EMPTY)}

    per_year = year_counts(col(blogposts, "year"))
    if per_year["labels"]:
        per_year["insight"] = ins.join(
            ins.busiest(per_year["labels"], per_year["values"], "post", "posts", period="year"),
            ins.latest_change(per_year["labels"], per_year["values"], "posts"),
        )

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
        "by_category": by_category,
        "by_publisher": publisher,
    }
