"""Organisations section — the partner network."""
import re
from collections import Counter

from . import insights as ins
from .parse import EMPTY, as_text, col, metric, multi_counts, parse_multi, value_counts


# Airtable record ids look like recXXXXXXXXXXXXXX. Used to tell an unresolved link
# from a table that stores the country name directly.
RECORD_ID_RE = re.compile(r"^rec[A-Za-z0-9]{10,}$")


def country_lookup(countries):
    """``{airtable_record_id: country_name}`` for resolving linked-record cells."""
    if countries is None or countries.empty:
        return {}
    if "airtable_id" not in countries.columns or "country" not in countries.columns:
        return {}
    return dict(zip(as_text(countries["airtable_id"]), as_text(countries["country"])))


def resolve_countries(frame, id_to_name, column="country"):
    """Count organisations per country, resolving record ids to names.

    An id that does NOT resolve is dropped rather than used as its own label. It used to
    fall through unchanged, which put a raw ``recXXXXXXXXXXXXXX`` on the axis of the
    country ranking and shaded nothing on the map — a database key presented to the
    reader as though it were a place. The count of unresolved ids is still published in
    the insight, so the gap is stated rather than hidden.
    """
    counter = Counter()
    if frame is None or frame.empty or column not in frame.columns:
        return counter
    for value in frame[column].dropna():
        for token in parse_multi(value):
            name = id_to_name.get(token)
            if name:
                counter[name] += 1
            elif not RECORD_ID_RE.match(token):
                # Not an id at all — some tables hold the country name directly.
                counter[token] += 1
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
        # Short form: this lands in a 3-column card, which fits about forty characters
        # on the single caption line. The full definition is in the ⓘ note.
        "by_classification": multi_counts(
            col(orgs, "classification"), top=8,
            insight=ins.leader_short(multi_counts(col(orgs, "classification")))),
        "by_focus": multi_counts(
            col(orgs, "focus_areas"), top=12,
            insight=ins.leader(multi_counts(col(orgs, "focus_areas")), "focus-area assignments")),
    }
