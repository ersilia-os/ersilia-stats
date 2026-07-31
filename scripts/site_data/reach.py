"""Global reach — where Ersilia actually works, and how that maps onto equity.

The previous site shaded a world map by raw counts and separately showed all 197
countries by region and income group. Counting every country in the reference table
answers nothing: Ersilia does not work in 197 countries. What matters for a
tech-nonprofit with an explicit Global South mission is the **income-group and
region composition of the countries it genuinely engages with**, so that is the
primary framing here; the map keeps the raw counts.

Global South / North is taken from the World Bank income group on the Countries
table: LIC, LMIC and UMIC are counted as Global South, HIC as Global North. That
choice is stated on the page (Methods) rather than left implicit.
"""
from collections import Counter

from . import insights as ins
from .parse import EMPTY, as_text, col, metric, parse_multi
from .organisations import country_lookup, resolve_countries

GLOBAL_SOUTH_GROUPS = {"LIC", "LMIC", "UMIC"}
GLOBAL_NORTH_GROUPS = {"HIC"}
INCOME_ORDER = ["LIC", "LMIC", "UMIC", "HIC"]


def _attribute_map(countries, attribute):
    """``{country_name: attribute_value}`` from the Countries reference table."""
    if countries is None or countries.empty:
        return {}
    if "country" not in countries.columns or attribute not in countries.columns:
        return {}
    names = as_text(countries["country"])
    values = as_text(countries[attribute])
    return {
        name: value for name, value in zip(names, values)
        # A row with no country name would otherwise become an "" key that nothing
        # can ever look up.
        if name and value and value.lower() != "nan"
    }


def _counter_from_multi(series):
    counter = Counter()
    if series is None or series.empty:
        return counter
    for value in series.dropna():
        for token in parse_multi(value):
            counter[token] += 1
    return counter


def build(countries, orgs, community, events):
    income = _attribute_map(countries, "income_group")
    region = _attribute_map(countries, "region")

    org_counts = resolve_countries(orgs, country_lookup(countries))
    community_counts = _counter_from_multi(col(community, "country_(from_country)", "country")
                                           if community is not None else None)
    event_counts = _counter_from_multi(col(events, "country_(from_country)")
                                       if events is not None else None)

    footprint = Counter()
    for counts in (org_counts, community_counts, event_counts):
        footprint.update(counts)

    engaged = sorted(footprint)
    return {
        "footprint_by_country": _footprint(footprint),
        "organisations_by_country": _sorted_metric(org_counts, "partner organisations"),
        "community_by_country": _sorted_metric(community_counts, "member records"),
        "events_by_country": _sorted_metric(event_counts, "located events"),
        "engagement_by_income_group": _by_income(engaged, income),
        "engagement_by_region": _by_region(engaged, region),
        "south_north": _south_north(engaged, income),
        "reference_by_income_group": _reference(countries, "income_group"),
    }


def _sorted_metric(counter, noun="records"):
    """Every metric carries a caption — these feed the map's toggles, and a card must
    never render with an empty caption line."""
    items = counter.most_common()
    if not items:
        return dict(EMPTY)
    return metric([k for k, _ in items], [v for _, v in items],
                  "%s leads with %s of %s %s." % (
                      items[0][0], ins.num(items[0][1]),
                      ins.num(sum(v for _, v in items)), noun))


def _footprint(footprint):
    items = footprint.most_common()
    if not items:
        return dict(EMPTY)
    return metric(
        [k for k, _ in items], [v for _, v in items],
        "%s countries with at least one partner organisation, community member or event." % (
            ins.num(len(items)),
        ),
        n=len(items),
    )


def _by_income(engaged, income):
    counter = Counter()
    unknown = 0
    for country in engaged:
        group = income.get(country)
        if group in INCOME_ORDER:
            counter[group] += 1
        else:
            unknown += 1
    if not counter:
        return dict(EMPTY)
    labels = [g for g in INCOME_ORDER if g in counter]
    values = [counter[g] for g in labels]
    south = sum(counter[g] for g in labels if g in GLOBAL_SOUTH_GROUPS)
    out = metric(
        labels, values,
        ins.share_of(south, sum(values), "engaged countries", "are Global South"),
    )
    out["ordinal"] = True
    return out


def _by_region(engaged, region):
    counter = Counter(region[c] for c in engaged if c in region)
    if not counter:
        return dict(EMPTY)
    items = counter.most_common()
    return metric(
        [k for k, _ in items], [v for _, v in items],
        ins.leader({"labels": [k for k, _ in items], "values": [v for _, v in items]},
                   "engaged countries"),
    )


def _south_north(engaged, income):
    south = sum(1 for c in engaged if income.get(c) in GLOBAL_SOUTH_GROUPS)
    north = sum(1 for c in engaged if income.get(c) in GLOBAL_NORTH_GROUPS)
    if not (south or north):
        return dict(EMPTY)
    return metric(
        ["Global South", "Global North"], [south, north],
        # The full definition (which income groups count as which) is in the ⓘ note and
        # in Methods; the caption has one line in a 4-column card.
        ins.share_of(south, south + north, "engaged countries", "are Global South"),
        semantics={"Global South": "brand", "Global North": "neutral"},
    )


def _reference(countries, attribute):
    """The full reference table's composition, for context in the appendix."""
    values = as_text(col(countries, attribute)) if countries is not None else None
    if values is None or values.empty:
        return dict(EMPTY)
    values = values[(values != "") & (values.str.lower() != "nan")]
    counts = values.value_counts()
    labels = [g for g in INCOME_ORDER if g in counts.index]
    labels += [g for g in counts.index if g not in labels]
    return metric(labels, [int(counts[g]) for g in labels],
                  "All %s countries in the reference table, for comparison with Ersilia's footprint." %
                  ins.num(int(counts.sum())))
