#!/usr/bin/env python3
"""Generate a small SYNTHETIC snapshot set, so the build can be validated without secrets.

WHY THIS EXISTS
---------------
``data/air_tables/`` is gitignored — it holds the raw Airtable extract, which carries
personal data and private repository names. That is the right call, and it had one
unfortunate consequence: **nothing could build the site without an Airtable key**, so
there was no pull-request check. Every regression was found in production, after merge.

This writes a fixture with the same *shape* as a real snapshot — the same columns, the
same awkward encodings (multi-select values arrive as Python list-repr strings,
linked records as ``recXXXXXXXXXXXXXX`` ids, dates as ``YYYY-MM-DD``) — and entirely
invented contents. Names are obviously fake. No row corresponds to a real person,
organisation, repository or project.

It deliberately exercises the cases that have broken this pipeline before:

* missing values in text columns    (``as_text`` must not turn NaN into "nan")
* missing values in numeric columns (``to_num`` must coerce)
* multi-select cells with one value and several
* a ``-1`` sentinel in the model performance columns (means "failed at this size")
* a private repository, so the public/private split is non-trivial
* a project linked to both a public and a private repository
* an open-ended project and an open-ended community record (no end date)
* a country that no organisation references, and an organisation whose country id
  does not resolve

Deterministic: no randomness, no clock. Re-running it produces byte-identical files,
so a diff means someone changed the generator.

    python3 scripts/make_fixture.py -o data/air_tables_sample/
"""
import argparse
import csv
import os

# A fixed stamp. Using today's date would make the output change daily and turn every
# run into a diff; the site derives "snapshot date" from this filename.
STAMP = "20260101"

# Airtable ids are 17 characters beginning "rec". These are synthetic but well-formed,
# because parse_multi and the join code both key on that shape.
def rec(prefix, n):
    return "rec%s%09d" % (prefix, n)


def listrepr(values):
    """How Airtable multi-selects and linked records actually arrive: the *string*
    repr of a Python list. Every module goes through parse_multi() because of this."""
    if not values:
        return ""
    return "[" + ", ".join("'%s'" % v for v in values) + "]"


COUNTRY = [rec("CTRY", i) for i in range(1, 6)]
ORG = [rec("ORGX", i) for i in range(1, 6)]
PROJ = [rec("PROJ", i) for i in range(1, 5)]
REPO = [rec("REPO", i) for i in range(1, 6)]
PUB = [rec("PUBL", i) for i in range(1, 4)]


def countries():
    rows = [
        # country, income group, region, subregion, population
        ("Testland", "LIC", "Africa", "Eastern Africa", 12000000),
        ("Sampleia", "LMIC", "Africa", "Western Africa", 34000000),
        ("Fixtureland", "UMIC", "Americas", "South America", 8000000),
        ("Exampleland", "HIC", "Europe", "Southern Europe", 47000000),
        # Referenced by nothing: the footprint must not invent engagement.
        ("Unusedia", "", "Asia", "Southern Asia", 900000),
    ]
    out = []
    for i, (name, income, region, sub, pop) in enumerate(rows):
        out.append({
            "airtable_id": COUNTRY[i], "Country": name, "Income Group": income,
            "Region": region, "Subregion": sub, "Population": pop,
            "Collaborators": "", "Community": "", "Conferences": "",
            "Donations": "", "Events": "",
        })
    return out


def organisations():
    rows = [
        ("Testland Research Institute", "TRI", "Academia", ["Collaborator"], COUNTRY[0], ["Science"]),
        ("Sampleia Health Foundation", "SHF", "Foundation", ["Funder"], COUNTRY[1], ["Capacity building", "Science"]),
        ("Fixture Pharma", "FP", "Corporate", ["Collaborator"], COUNTRY[2], ["Healthcare"]),
        ("Example Open Network", "EON", "Civil Society", ["Network", "Funder"], COUNTRY[3], ["Open Source"]),
        # An unresolvable country id: resolve_countries must pass it through and count it.
        ("Orphan Org", "OO", "Academia", ["Collaborator"], "recMISSING000001", []),
    ]
    out = []
    for i, (name, acr, typ, classification, country, focus) in enumerate(rows):
        out.append({
            "airtable_id": ORG[i], "Name": name, "Acronym": acr, "Type": typ,
            "Classification": listrepr(classification),
            "Country": listrepr([country]),
            "Focus Areas": listrepr(focus),
            "Focus Region": listrepr(["Global"]),
            "Community": "", "Conferences": "", "Contacts": "", "Description": "",
            "Events": "", "Grants": "", "Opportunities": "", "Website": "",
            "Projects": "", "Workshops": "",
        })
    return out


def projects():
    rows = [
        # name, status, start, end, repos, publications
        ("Fixture Model Hub", "In progress", "2021-01-01", "", [REPO[0], REPO[1], REPO[4]], [PUB[0]]),
        ("Sample Screening Cascade", "Done", "2022-03-01", "2024-06-30", [REPO[2]], [PUB[1]]),
        ("Test Antimicrobials", "Done", "2023-01-15", "2025-01-14", [REPO[3]], []),
        # No outputs at all: outputs_table must omit it and has_outputs must count it.
        ("Unlinked Effort", "Stuck", "2024-02-01", "", [], []),
    ]
    out = []
    for i, (name, status, start, end, repos, pubs) in enumerate(rows):
        out.append({
            "airtable_id": PROJ[i], "Name": name, "Status": status,
            "Start Date": start, "End Date": end,
            "Repositories": listrepr(repos), "Publications": listrepr(pubs),
            "Collaborator": "", "Description": "", "Drive": "", "Grant": "",
            "Organization": listrepr([ORG[i % len(ORG)]]), "Team": "",
            "Start Quarter": "", "Start Year": "", "End Quarter": "", "End Year": "",
        })
    return out


def repositories():
    rows = [
        # name, visibility, created, stars, forks, subs, commits, issues, contributors,
        # type, status, contributor names, project
        ("fixture-hub", "public", "2021-02-01", 120, 40, 9, 2400, 3, 7, "Package",
         "In progress", "alpha-dev, beta-dev, gamma-dev", [PROJ[0]]),
        ("fixture-tools", "public", "2022-05-10", 18, 4, 2, 310, 1, 3, "Analysis",
         "Completed", "alpha-dev, delta-dev", [PROJ[0]]),
        ("sample-cascade", "public", "2022-09-01", 6, 1, 1, 95, 0, 2, "Analysis",
         "Completed", "beta-dev", [PROJ[1]]),
        # 60+ commits and zero stars: the "busy but unknown" quadrant.
        ("test-amr-models", "public", "2023-04-01", 0, 0, 0, 140, 2, 1, "Package",
         "Idle", "gamma-dev", [PROJ[2]]),
        # Private, and linked to a project: aggregates include it, names never do.
        ("internal-fixture", "private", "2023-11-01", 0, 0, 0, 55, 0, 2, "Automation",
         "In progress", "alpha-dev", [PROJ[0]]),
    ]
    out = []
    for i, r in enumerate(rows):
        (name, vis, created, stars, forks, subs, commits, issues, contribs,
         typ, status, names, proj) = r
        out.append({
            "airtable_id": REPO[i], "Name": name, "Title": name,
            "Visibility": vis, "Creation Date": created,
            "Stars": stars, "Forks": forks, "Subscribers": subs,
            "Total Commits": commits, "Open Issues": issues, "Contributors": contribs,
            "Type": listrepr([typ]), "Status": status,
            "Contributor Names": names, "Projects": listrepr(proj),
            "Description": "", "URL": "https://example.invalid/%s" % name,
        })
    return out


def publications():
    rows = [
        ("A fixture paper on antimicrobial models", 2021, 42, "Journal of Fixtures",
         ["Chemoinformatics"], "Research", "Yes", "Yes", "Yes"),
        ("A second fixture paper", 2023, 7, "Journal of Fixtures",
         ["Bioinformatics"], "Research", "Yes", "No", "No"),
        # Citations missing entirely: to_num must coerce rather than crash.
        ("A fixture review", 2025, "", "Sample Reviews",
         ["Medical informatics"], "Review", "No", "", "No"),
    ]
    out = []
    for i, (title, year, cites, journal, topic, typ, affil, african, senior) in enumerate(rows):
        out.append({
            "airtable_id": PUB[i], "Title": title, "Year": year, "Citations": cites,
            "Journal": journal, "Topic": listrepr(topic), "Type": typ,
            "Ersilia Affiliation": affil, "African collaboration": african,
            "Senior": senior, "Status": "Peer reviewed",
            "Abstract": "", "Authors": "", "Google Scholar ID": "", "Projects": "",
            "Slug": "", "URL": "", "Year Web": year,
        })
    return out


def community():
    rows = [
        # role, gender, country, org, start, end
        (["Intern"], "Female", "Testland", "Testland Research Institute", "2021-03-01", "2021-09-01"),
        (["Volunteer", "Mentor"], "Male", "Sampleia", "Sampleia Health Foundation", "2022-01-10", "2022-07-10"),
        (["Employee"], "Female", "Exampleland", "Example Open Network", "2022-06-01", ""),
        (["Volunteer"], "Male", "Fixtureland", "Fixture Pharma", "2023-02-01", "2024-08-01"),
        # No end date, so still involved; and no gender recorded.
        (["Trustee"], "", "Exampleland", "Example Open Network", "2023-09-15", ""),
        (["Intern"], "Female", "Testland", "Testland Research Institute", "2024-01-08", "2024-04-08"),
    ]
    out = []
    for i, (role, gender, country, org, start, end) in enumerate(rows):
        out.append({
            "airtable_id": rec("COMM", i + 1),
            "Role": listrepr(role), "Gender": gender,
            "Country (from Country)": listrepr([country]), "Country": "",
            "Name (from Org)": listrepr([org]), "Organisation": "",
            "Start Date": start, "End Date": end,
            "Start Month": "", "Start Quarter": "", "Start Year": "",
            "End Month": "", "End Quarter": "", "End Year": "",
            "Blogposts": "", "Projects": "",
        })
    return out


def events():
    rows = [
        ("Fixture Symposium", "2022-04-05", "Testland", "Testland Research Institute"),
        ("Sample Workshop", "2023-06-12", "Sampleia", "Sampleia Health Foundation"),
        ("Example Conference", "2024-02-20", "Exampleland", "Example Open Network"),
        # No country recorded: the "located events" count must exclude it.
        ("Remote Fixture Talk", "2025-05-01", "", "Example Open Network"),
    ]
    out = []
    for i, (name, date, country, organiser) in enumerate(rows):
        out.append({
            "airtable_id": rec("EVNT", i + 1), "Name": name, "Date": date,
            "Country (from Country)": listrepr([country] if country else []),
            "Country": "", "Organiser": listrepr([organiser]),
            "Year": date[:4], "Quarter": "", "Description": "",
            "Event URL": "", "Organisations": "", "Videos": "",
        })
    return out


def blogposts():
    rows = [
        ("A fixture blog post", "2022-08-01", ["Technology"], "Ersilia"),
        ("Another fixture post", "2023-03-15", ["Training", "Global Health"], "Ersilia"),
        ("A guest fixture post", "2024-11-02", ["Science"], "Other"),
    ]
    out = []
    for i, (title, date, cats, publisher) in enumerate(rows):
        out.append({
            "airtable_id": rec("BLOG", i + 1), "Title": title, "Date": date,
            "Category": listrepr(cats), "Publisher": publisher,
            "Year": date[:4], "Quarter": "", "Author": "",
            "Name (from Author)": "", "Intro": "", "Slug": "", "URL": "",
        })
    return out


def conferences():
    rows = [
        ("Fixture Summit", "Annual", "Yes", "2026-09-01"),
        ("Sample Symposium", "Recurring", "No", ""),
        ("Example Plenary", "Biannual", "", "2026-11-15"),
    ]
    out = []
    for i, (name, cadence, remote, upcoming) in enumerate(rows):
        out.append({
            "airtable_id": rec("CONF", i + 1), "Name": name, "Cadence": cadence,
            "Remote option": remote, "Upcoming date": upcoming,
            "Countries": listrepr([COUNTRY[i]]), "Focus": "",
            "Organiser": listrepr([ORG[i]]), "Website": "",
        })
    return out


def models():
    """Includes the -1 sentinel, so the derived "largest working batch" is exercised."""
    rows = [
        # id, area, task, subtask, status, source type, tag, organism, arch,
        # incorporation, publication year, image MB, perf 1..5
        ("eos1aaa", ["Antimicrobial resistance"], "Annotation", "Activity prediction",
         "Ready", "External", ["Antimicrobial activity"], "Mycobacterium tuberculosis",
         ["AMD64", "ARM64"], "2021-05-01", 2020, 1400.5, [30, 28, 35, 90, 260]),
        ("eos2bbb", ["Any"], "Representation", "Featurization",
         "Ready", "Internal", ["Descriptor"], "Any",
         ["AMD64"], "2022-02-14", 2022, 780.0, [26, 24, 30, 120, -1]),
        ("eos3ccc", ["Malaria"], "Annotation", "Property calculation",
         "In progress", "External", ["ADME"], "Plasmodium falciparum",
         ["AMD64", "ARM64"], "2023-07-20", 2019, 5200.25, [40, 300, -1, -1, -1]),
        ("eos4ddd", ["Any"], "Sampling", "Generation",
         "Archived", "Replicated", ["Compound generation"], "Homo sapiens",
         ["AMD64"], "2024-11-05", 2024, 2100.0, [55, 60, 70, -1, -1]),
        # No publication year and no image size: both must be skipped, not zeroed.
        ("eos5eee", ["Tuberculosis"], "Annotation", "Activity prediction",
         "Ready", "External", ["ChEMBL"], "Escherichia coli",
         ["AMD64", "ARM64"], "2025-06-30", "", "", [33, 31, 38, 95, 280]),
    ]
    out = []
    for i, r in enumerate(rows):
        (ident, area, task, subtask, status, source, tag, organism, arch,
         inc, pub_year, image, perf) = r
        row = {
            "airtable_id": rec("MODL", i + 1), "Identifier": ident, "Slug": ident,
            "Title": "Fixture model %s" % ident,
            "Biomedical Area": listrepr(area),
            "Task": listrepr([task]), "Subtask": listrepr([subtask]),
            "Status": listrepr([status]), "Source Type": listrepr([source]),
            "Tag": listrepr(tag), "Target Organism": listrepr([organism]),
            "Docker Architecture": listrepr(arch),
            "Incorporation Date": inc, "Incorporation Year": inc[:4] if inc else "",
            "Incorporation Quarter": "", "Publication Year": pub_year,
            "Image Size": image, "Model Size": 120, "Environment Size": 2100,
            "License": listrepr(["MIT"]), "Deployment": listrepr(["Local"]),
            "DockerHub": "https://example.invalid/%s" % ident,
            "S3": "https://example.invalid/%s.zip" % ident,
            "Source Code": "https://example.invalid/%s-src" % ident,
            "Contributor": listrepr(["alpha-dev"]), "Contributor Profile": "",
            "Description": "", "GitHub": "", "Input": listrepr(["Compound"]),
            "Input Dimension": 1, "Interpretation": "", "Last Packaging Date": inc,
            "Output": listrepr(["Value"]), "Output Consistency": "Fixed",
            "Output Dimension": 1, "Publication": "", "Publication Type": "Paper",
            "Release": "", "Repository": "", "Source": "",
        }
        for n, value in enumerate(perf, start=1):
            row["Computational Performance %d" % n] = value
        out.append(row)
    return out


TABLES = {
    "blogposts": blogposts, "community": community, "conferences": conferences,
    "countries": countries, "events": events, "models": models,
    "organisations": organisations, "projects": projects,
    "publications": publications, "repositories": repositories,
}


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("-o", "--out-dir", default="data/air_tables_sample",
                        help="Where to write the fixture CSVs.")
    args = parser.parse_args()
    os.makedirs(args.out_dir, exist_ok=True)

    for name, builder in sorted(TABLES.items()):
        rows = builder()
        # Union of keys, in first-seen order, so a row missing a key still writes blank.
        fields = []
        for row in rows:
            for key in row:
                if key not in fields:
                    fields.append(key)
        path = os.path.join(args.out_dir, "%s_%s.csv" % (name, STAMP))
        with open(path, "w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            for row in rows:
                writer.writerow(row)
        print("wrote %s (%d rows, %d columns)" % (path, len(rows), len(fields)))


if __name__ == "__main__":
    main()
