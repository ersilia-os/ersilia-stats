#!/usr/bin/env python3
"""One-off: work out a DOI for every publication, for a human to review.

WHY THIS IS NOT PART OF CI
--------------------------
A DOI is the key to every scholarly API, and the publications table has no DOI field.
Two thirds of the DOIs can be read straight out of the `url` column; the rest need a
title search, and a title search can be *confidently wrong*. Attaching another group's
citation count to an Ersilia paper is the one failure mode here that actually matters, so
this script proposes and a person decides. It is run once, not weekly.

    python3 scripts/resolve_dois.py                     # writes the review CSV
    python3 scripts/resolve_dois.py --out /tmp/doi.csv

Then paste the reviewed DOIs into a new **DOI field in Airtable**, so the answer is stored
where the rest of the publication metadata lives and never has to be guessed again.
`fetch_openalex.py` reads that field and skips any row without one.

The `source` and `confidence` columns are the point of the output:

    url          the DOI was embedded in the recorded URL. Trustworthy.
    title-exact  OpenAlex returned a work whose title matches after normalisation.
    title-fuzzy  OpenAlex returned something similar. READ THIS ROW BEFORE ACCEPTING IT.
    none         nothing found. Needs a DOI by hand, or the paper has none.
"""
import argparse
import csv
import logging
import re
import sys
import time
import urllib.parse

sys.path.insert(0, "scripts")
from collect_common import CONTACT, get_json                      # noqa: E402

OPENALEX = "https://api.openalex.org"

# A DOI is `10.` then a registrant code, then anything up to whitespace or a URL delimiter.
DOI_RE = re.compile(r"\b(10\.\d{4,9}/[^\s\"&?#<>]+)", re.I)

# Publisher URLs often append a view suffix to the DOI path. `10.1515/psr-2024-0015/html`
# is a real example from this dataset: the `/html` is the page, not the identifier.
TRAILING_JUNK = ("/html", "/full", "/abstract", "/pdf", "/meta")

FIELDS = ["title", "year", "doi", "source", "confidence", "matched_title", "stored_citations",
          "openalex_citations"]


def normalise(text):
    """Lowercase, strip punctuation and collapse spaces, for comparing titles."""
    return re.sub(r"[^a-z0-9 ]+", " ", (text or "").lower()).strip()


def clean_doi(raw):
    doi = raw.strip().rstrip(".,);:")
    lowered = doi.lower()
    for suffix in TRAILING_JUNK:
        if lowered.endswith(suffix):
            doi = doi[: -len(suffix)]
            break
    return doi


def from_url(row):
    for field in ("url", "abstract"):
        match = DOI_RE.search(str(row.get(field) or ""))
        if match:
            return clean_doi(match.group(1))
    return None


def from_title(title):
    """Ask OpenAlex for the work, and say how sure the match is."""
    words = " ".join(str(title).split()[:14])
    url = "%s/works?search=%s&per_page=1&mailto=%s" % (
        OPENALEX, urllib.parse.quote(words), CONTACT)
    payload = get_json(url)
    results = (payload or {}).get("results") or []
    if not results:
        return None, "none", "", ""
    work = results[0]
    doi = (work.get("doi") or "").replace("https://doi.org/", "")
    matched = work.get("display_name") or ""
    a, b = normalise(title), normalise(matched)
    exact = a == b or (len(a) > 30 and (a.startswith(b[:30]) or b.startswith(a[:30])))
    return doi or None, ("title-exact" if exact else "title-fuzzy"), matched, work.get("cited_by_count")


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--data-dir", default="data/air_tables")
    parser.add_argument("--out", default="data/scholar/doi_map_review.csv")
    args = parser.parse_args()

    from site_data import load                                     # noqa: E402
    tables = load.load_tables(args.data_dir)
    pubs = tables.get("publications")
    if pubs is None or pubs.empty:
        logging.error("no publications table in %s", args.data_dir)
        return 1

    import pandas as pd
    stored = pd.to_numeric(pubs.get("citations"), errors="coerce").fillna(0)

    rows = []
    for i in range(len(pubs)):
        row = pubs.iloc[i]
        title = str(row.get("title") or "").strip()
        if not title:
            continue
        doi = from_url(row)
        source, matched, live = "url", "", ""
        if doi:
            confidence = "high"
        else:
            doi, source, matched, live = from_title(title)
            confidence = {"title-exact": "medium", "title-fuzzy": "low",
                          "none": "none"}[source]
            time.sleep(0.3)                                        # be polite
        rows.append({
            "title": title, "year": row.get("year") or "", "doi": doi or "",
            "source": source, "confidence": confidence, "matched_title": matched,
            "stored_citations": int(stored.iloc[i]), "openalex_citations": live,
        })

    import os
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    by_source = {}
    for row in rows:
        by_source[row["source"]] = by_source.get(row["source"], 0) + 1
    logging.info("wrote %s (%d publications)", args.out, len(rows))
    for source in ("url", "title-exact", "title-fuzzy", "none"):
        if by_source.get(source):
            logging.info("  %-12s %d", source, by_source[source])
    needs_eyes = [r for r in rows if r["confidence"] in ("low", "none")]
    if needs_eyes:
        logging.warning("%d row(s) need reading before you trust them:", len(needs_eyes))
        for row in needs_eyes[:10]:
            logging.warning("   %-46s -> %s", row["title"][:46], row["doi"] or "(none)")
    return 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    sys.exit(main())
