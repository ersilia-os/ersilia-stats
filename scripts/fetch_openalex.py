#!/usr/bin/env python3
"""Publication metrics from OpenAlex, keyed by DOI.

WHY: the stored citation counts are wrong. Checked against OpenAlex, **nine of ten
differ**, mean drift **+11 citations**, worst case **28 stored against 92 live**. A
hand-maintained number decays the moment it is written down, and a citation count decays
faster than most.

OpenAlex was chosen over the alternatives for reasons that are practical, not ideological:
free, no key, one request per work, and it carries three things nothing else here does —
citations **per year**, open-access status, and the **countries of the author
institutions**.

ON GOOGLE SCHOLAR. Scholar has no API, and its robots.txt disallows `/scholar` and
`/citations?` — exactly the paths that carry per-paper citation counts; only author profile
pages are permitted. So Scholar's numbers cannot be collected without either violating that
or paying a proxy. The publications table already stores a Scholar cluster ID per paper, and
those are used as outbound "see citing works" links instead: linking is not fetching.

CITATION COUNTS ARE SOURCE-DEPENDENT. For one paper: Airtable 44, OpenAlex 43, Semantic
Scholar 37. None is "the" answer, so the site must name its source. It says OpenAlex.

WHAT IS DELIBERATELY NOT COLLECTED: author names. The country codes of author institutions
measure international collaboration; the author list is personal data, and this site is
aggregates-only.

    python3 scripts/fetch_openalex.py -o data/scholar/
    python3 scripts/fetch_openalex.py --check
"""
import argparse
import logging
import re
import sys
import time
import urllib.parse

from collect_common import (CONTACT, check_freshness, get_json, prune_superseded,
                            write_snapshot)

OPENALEX = "https://api.openalex.org"

WORK_FIELDS = ["doi", "title", "year", "publication_date", "type", "venue", "publisher",
               "citations", "is_open_access", "oa_status", "institution_countries",
               "institution_count", "referenced_works_count"]
# Citations per year, one row per (doi, year). This is why no accumulated history is
# needed for a citation curve: OpenAlex records the series itself.
YEAR_FIELDS = ["doi", "year", "citations"]


def read_dois(data_dir):
    """DOIs from the publications table.

    Prefers a real `doi` column — the durable answer, entered once in Airtable. Falls
    back to extracting one from the recorded URL, which covers about half the rows, and
    NEVER guesses from a title: a title search belongs in `resolve_dois.py`, where a
    person reads the result before it is trusted.
    """
    from site_data import load
    tables = load.load_tables(data_dir)
    pubs = tables.get("publications")
    if pubs is None or pubs.empty:
        return [], 0

    doi_re = re.compile(r"\b(10\.\d{4,9}/[^\s\"&?#<>]+)", re.I)
    have_column = "doi" in pubs.columns
    if not have_column:
        logging.warning("no DOI column in the publications table — falling back to the "
                        "URL field. Add a DOI field in Airtable to make this exact; see "
                        "scripts/resolve_dois.py.")

    entries, missing = [], 0
    for i in range(len(pubs)):
        row = pubs.iloc[i]
        title = str(row.get("title") or "").strip()
        doi = ""
        if have_column:
            doi = str(row.get("doi") or "").strip()
        if not doi:
            match = doi_re.search(str(row.get("url") or ""))
            if match:
                doi = match.group(1).rstrip(".,);:")
                for suffix in ("/html", "/full", "/abstract", "/pdf", "/meta"):
                    if doi.lower().endswith(suffix):
                        doi = doi[: -len(suffix)]
                        break
        doi = doi.replace("https://doi.org/", "").replace("http://doi.org/", "").strip()
        if doi:
            entries.append((doi, title))
        else:
            missing += 1
    return entries, missing


def fetch_work(doi):
    url = "%s/works/doi:%s?mailto=%s" % (OPENALEX, urllib.parse.quote(doi), CONTACT)
    return get_json(url)


def flatten(doi, title, work):
    source = ((work.get("primary_location") or {}).get("source") or {})
    open_access = work.get("open_access") or {}
    countries, institutions = set(), 0
    for authorship in work.get("authorships") or []:
        for institution in authorship.get("institutions") or []:
            institutions += 1
            code = institution.get("country_code")
            if code:
                countries.add(code)
    row = {
        "doi": doi,
        # OpenAlex's own title, so a mismatch against the stored one is visible in the diff.
        "title": (work.get("display_name") or title or "").replace("\n", " ")[:300],
        "year": work.get("publication_year") or "",
        "publication_date": work.get("publication_date") or "",
        "type": work.get("type") or "",
        "venue": (source.get("display_name") or "")[:160],
        "publisher": (source.get("host_organization_name") or "")[:120],
        "citations": work.get("cited_by_count") or 0,
        "is_open_access": "yes" if open_access.get("is_oa") else "no",
        "oa_status": open_access.get("oa_status") or "",
        "institution_countries": " ".join(sorted(countries)),
        "institution_count": institutions,
        "referenced_works_count": len(work.get("referenced_works") or []),
    }
    years = [{"doi": doi, "year": entry.get("year"), "citations": entry.get("cited_by_count") or 0}
             for entry in (work.get("counts_by_year") or []) if entry.get("year")]
    return row, years


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("-o", "--out-dir", default="data/scholar")
    parser.add_argument("--data-dir", default="data/air_tables")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--max-age-days", type=int, default=21)
    args = parser.parse_args()

    if args.check:
        return check_freshness(args.out_dir, args.max_age_days, "openalex")

    entries, missing = read_dois(args.data_dir)
    if not entries:
        logging.error("no DOIs available — run scripts/resolve_dois.py and add a DOI "
                      "field in Airtable")
        return 1
    if missing:
        logging.warning("%d publication(s) have no DOI and are skipped", missing)

    rows, year_rows, unresolved = [], [], []
    for doi, title in entries:
        work = fetch_work(doi)
        if not work:
            unresolved.append(doi)                 # 404: OpenAlex does not know it
            continue
        row, years = flatten(doi, title, work)
        rows.append(row)
        year_rows.extend(years)
        time.sleep(0.15)

    if not rows:
        logging.error("no works resolved — refusing to write an empty snapshot")
        return 1

    rows.sort(key=lambda r: (-r["citations"], r["doi"]))
    year_rows.sort(key=lambda r: (r["doi"], r["year"]))

    written = [write_snapshot(args.out_dir, "works", WORK_FIELDS, rows),
               write_snapshot(args.out_dir, "citations_by_year", YEAR_FIELDS, year_rows)]
    prune_superseded(args.out_dir, written)

    total = sum(r["citations"] for r in rows)
    open_access = sum(1 for r in rows if r["is_open_access"] == "yes")
    countries = {c for r in rows for c in r["institution_countries"].split() if c}
    logging.info("%d works resolved, %s citations total", len(rows), format(total, ","))
    logging.info("open access: %d of %d (%.0f%%)", open_access, len(rows),
                 100.0 * open_access / len(rows))
    logging.info("%d distinct author-institution countries", len(countries))
    if unresolved:
        logging.warning("OpenAlex has no record of %d DOI(s): %s",
                        len(unresolved), ", ".join(unresolved[:5]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
