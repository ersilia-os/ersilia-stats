"""Organisations section — the partner network."""
from collections import Counter

from . import insights as ins
from .parse import EMPTY, col, metric, multi_counts, parse_multi, value_counts


def country_lookup(countries):
    """``{airtable_record_id: country_name}`` for resolving linked-record cells."""
    if countries is None or countries.empty:
        return {}
    if "airtable_id" not in countries.columns or "country" not in countries.columns:
        return {}
    return dict(zip(countries["airtable_id"].astype(str), countries["country"].astype(str)))


def resolve_countries(frame, id_to_name, column="country"):
    """Count organisations per country, resolving record ids to names."""
    counter = Counter()
    if frame is None or frame.empty or column not in frame.columns:
        return counter
    for value in frame[column].dropna():
        for token in parse_multi(value):
            counter[id_to_name.get(token, token)] += 1
    return counter


def build(orgs, countries):
    if orgs is None or orgs.empty:
        return {"by_type": dict(EMPTY), "by_country": dict(EMPTY),
                "by_classification": dict(EMPTY), "by_focus": dict(EMPTY)}

    per_country = resolve_countries(orgs, country_lookup(countries))
    top = per_country.most_common(12)
    full = per_country.most_common()
    unresolved = int(len(orgs) - sum(per_country.values()))

    by_country = metric(
        [k for k, _ in top], [v for _, v in top],
        ins.join(
            ins.leader({"labels": [k for k, _ in full], "values": [v for _, v in full]},
                       "organisations with a country on file"),
            "%s countries represented." % ins.num(len(per_country)),
            ("No country recorded for %s." % ins.count_of(unresolved, "organisation", "organisations"))
            if unresolved > 0 else None,
        ),
    )

    by_type = value_counts(col(orgs, "type"), top=12)
    if by_type["labels"]:
        by_type["insight"] = ins.leader(by_type, "organisations")

    return {
        "by_type": by_type,
        "by_country": by_country,
        "by_classification": multi_counts(
            col(orgs, "classification"), top=8,
            insight="How each organisation relates to Ersilia — funder, network or collaborator."),
        "by_focus": multi_counts(col(orgs, "focus_areas"), top=12,
                                 insight="Focus areas are a multi-select, so one organisation contributes to several."),
    }
