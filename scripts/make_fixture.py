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
        # Citations missing entirely: to_num must coerce rather than crash. Unaffiliated,
        # so it exercises the external-work card and must stay out of every other figure.
        ("A fixture review", 2025, "", "Sample Reviews",
         ["Medical informatics"], "Review", "No", "", "No"),
    ]
    out = []
    for i, (title, year, cites, journal, topic, typ, affil, african, senior) in enumerate(rows):
        out.append({
            "airtable_id": PUB[i], "Title": title, "Year": year, "Citations": cites,
            # A DOI is REQUIRED, not decorative: the publications figures are filtered to
            # affiliated DOIs and joined to OpenAlex on them. Without this column the build
            # raised `single positional indexer is out-of-bounds`, which is precisely the
            # bug this fixture caught before it reached a deploy.
            "DOI": "https://doi.org/10.5555/fixture.%d" % (i + 1),
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



# ---------------------------------------------------------------- collected snapshots
#
# WHY THE FIXTURE HAS TO CARRY THESE NOW. It used to fabricate the ten Airtable tables and
# nothing else, which was enough while the repository counts and citation figures lived in
# Airtable columns. They no longer do: those columns were deleted and the site reads
# `data/github/`, `data/dockerhub/` and `data/scholar/` instead. A fixture of Airtable alone
# therefore joined synthetic names against the REAL collected snapshots, matched nothing, and
# left six charts empty — so the check either failed or, worse, stopped exercising them.
#
# These rows deliberately reuse the same names, identifiers and DOIs as the Airtable tables
# above, because the join is exactly what needs testing.

def github_repos():
    """One row per PUBLIC fixture repository, plus the five model repositories.

    `internal-fixture` is absent on purpose: the real collector writes public repositories
    only, and the check asserts that name appears nowhere in the output.
    """
    rows = [
        # name, created, pushed, lang, licence, stars, forks, subs, open, commits,
        # closed, merged, releases, latest, sampled, external, median, contributors
        ("fixture-hub", "2021-02-01", "2026-01-01", "Python", "GPL-3.0",
         120, 40, 9, 3, 2400, 180, 95, 12, "2025-11-02", 20, 15, 4, 7),
        ("fixture-tools", "2022-05-10", "2025-10-15", "Python", "MIT",
         18, 4, 2, 1, 310, 24, 18, 3, "2025-07-19", 10, 6, 12, 3),
        ("sample-cascade", "2022-09-01", "2025-06-01", "Jupyter Notebook", "MIT",
         6, 1, 1, 0, 95, 8, 4, 0, "", 4, 1, 30, 2),
        # 60+ commits and zero stars: the "busy but unknown" quadrant of the scatter.
        ("test-amr-models", "2023-04-01", "2024-02-01", "Python", "GPL-3.0",
         0, 0, 0, 2, 140, 12, 7, 1, "2024-01-10", 6, 5, 95, 1),
    ]
    model_rows = [
        ("eos1aaa", "2021-06-01", "2026-01-01", 40, 6, 3, 2, 1, "2025-12-01", 4, 4, 5, 3),
        ("eos2bbb", "2022-03-01", "2025-12-10", 62, 9, 5, 1, 0, "", 5, 3, 18, 4),
        ("eos3ccc", "2023-01-15", "2025-11-20", 28, 4, 2, 1, 1, "2025-09-09", 3, 3, 40, 2),
        ("eos4ddd", "2024-07-01", "2025-08-05", 15, 2, 1, 0, 0, "", 2, 0, 60, 2),
        ("eos5eee", "2025-02-01", "2026-01-01", 8, 1, 0, 0, 0, "", 1, 1, 2, 1),
    ]
    out = []
    for (name, created, pushed, lang, lic, stars, forks, subs, openi, commits,
         closed, merged, rel, latest, sampled, external, median, contribs) in rows:
        out.append({
            "name": name, "is_model": "no", "created_at": created, "pushed_at": pushed,
            "archived": "no", "fork": "no", "language": lang, "license": lic,
            "topics": "", "size_kb": 900, "stars": stars, "forks": forks,
            "watchers": subs, "open_issues": openi, "has_issues": "yes",
            "default_branch": "main", "total_commits": commits,
            "closed_issues": closed, "merged_prs": merged, "releases": rel,
            "latest_release": latest, "prs_sampled": sampled, "prs_external": external,
            "median_days_to_close": median, "contributors": contribs,
        })
    for (name, created, pushed, commits, closed, merged, rel, reln, latest,
         sampled, external, median, contribs) in model_rows:
        out.append({
            "name": name, "is_model": "yes", "created_at": created, "pushed_at": pushed,
            "archived": "no", "fork": "no", "language": "Python", "license": "GPL-3.0",
            "topics": "", "size_kb": 300, "stars": 0, "forks": 0, "watchers": 1,
            "open_issues": 0, "has_issues": "yes", "default_branch": "main",
            "total_commits": commits, "closed_issues": closed, "merged_prs": merged,
            "releases": reln, "latest_release": latest, "prs_sampled": sampled,
            "prs_external": external, "median_days_to_close": median,
            "contributors": contribs,
        })
    return out


def github_contributors():
    """The handles the Airtable `Contributor Names` column used to hold.

    No bot appears here. The real collector filters them, and a fixture that smuggled one
    in would let the contributors chart regress without the check noticing.
    """
    return [{"login": "alpha-dev", "repositories": 3},
            {"login": "beta-dev", "repositories": 2},
            {"login": "gamma-dev", "repositories": 2},
            {"login": "delta-dev", "repositories": 1}]


def github_org_totals():
    """The private aggregate: counts only, never a name."""
    return [{"metric": "private_repositories", "value": 1},
            {"metric": "private_stars", "value": 0}]


def github_commit_activity():
    quarters = ["2024Q3", "2024Q4", "2025Q1", "2025Q2", "2025Q3", "2025Q4"]
    counts = {"fixture-hub": [90, 120, 140, 110, 160, 95],
              "fixture-tools": [20, 15, 30, 25, 10, 8],
              "eos1aaa": [4, 6, 2, 3, 5, 1],
              "eos2bbb": [8, 5, 9, 4, 6, 3]}
    return [{"name": name, "week_start": quarter, "commits": values[i]}
            for name, values in sorted(counts.items())
            for i, quarter in enumerate(quarters) if values[i]]


def github_stars():
    dates = ["2024-08-11", "2024-11-02", "2025-01-20", "2025-03-14", "2025-05-30",
             "2025-07-07", "2025-09-19", "2025-12-01"]
    rows = [{"name": "fixture-hub", "starred_at": d} for d in dates]
    rows += [{"name": "fixture-tools", "starred_at": d} for d in dates[:4]]
    return rows


def dockerhub_images():
    """Model images, plus the infrastructure images that must be excluded from every figure."""
    pulls = {"eos1aaa": 4200, "eos2bbb": 4100, "eos3ccc": 29000, "eos4ddd": 4300,
             "eos5eee": 900}
    rows = [{"name": n, "is_model": "yes", "pull_count": p, "star_count": 0,
             "last_updated": "2025-11-%02dT00:00:00" % (i + 1), "description": ""}
            for i, (n, p) in enumerate(sorted(pulls.items()))]
    for infra in ("base", "conda"):
        rows.append({"name": infra, "is_model": "no", "pull_count": 31000,
                     "star_count": 1, "last_updated": "2025-12-01T00:00:00",
                     "description": ""})
    return rows


def scholar_works():
    """One row per fixture publication, keyed on the same DOI.

    The unaffiliated third paper is the most cited, mirroring the real data, so the
    affiliation filter is doing visible work in the check rather than passing trivially.
    """
    rows = [
        ("10.5555/fixture.1", "A fixture paper on antimicrobial models", 2021, 42,
         "Journal of Fixtures", "gold", "ES US ZA", 4),
        ("10.5555/fixture.2", "A second fixture paper", 2023, 7,
         "Journal of Fixtures", "green", "ES", 1),
        ("10.5555/fixture.3", "A fixture review", 2025, 310,
         "Sample Reviews", "closed", "US GB CM MZ", 6),
    ]
    return [{"doi": doi, "title": title, "year": year, "publication_date": "%d-06-01" % year,
             "type": "article", "venue": venue, "publisher": "Fixture Press",
             "citations": cites, "is_open_access": "no" if oa == "closed" else "yes",
             "oa_status": oa, "institution_countries": countries_, "institution_count": n,
             "referenced_works_count": 30}
            for doi, title, year, cites, venue, oa, countries_, n in rows]


def scholar_citations_by_year():
    series = {"10.5555/fixture.1": {2022: 10, 2023: 14, 2024: 12, 2025: 6},
              "10.5555/fixture.2": {2024: 3, 2025: 4},
              "10.5555/fixture.3": {2025: 310}}
    return [{"doi": doi, "year": year, "citations": n}
            for doi, per_year in sorted(series.items())
            for year, n in sorted(per_year.items())]


# source subdirectory -> {dataset name: builder}
COLLECTED = {
    "github": {"repos": github_repos, "contributors": github_contributors,
               "org_totals": github_org_totals, "commit_activity": github_commit_activity,
               "stars": github_stars},
    "dockerhub": {"images": dockerhub_images},
    "scholar": {"works": scholar_works, "citations_by_year": scholar_citations_by_year},
}


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
                        help="Where to write the Airtable fixture CSVs.")
    parser.add_argument("-c", "--collected-dir", default="data/collected_sample",
                        help="Where to write the synthetic github/dockerhub/scholar "
                             "snapshots. The site reads its repository counts and citation "
                             "figures from these, so a fixture without them cannot "
                             "exercise most of the build.")
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

    for source, datasets in sorted(COLLECTED.items()):
        target = os.path.join(args.collected_dir, source)
        os.makedirs(target, exist_ok=True)
        for name, builder in sorted(datasets.items()):
            rows = builder()
            fields = []
            for row in rows:
                for key in row:
                    if key not in fields:
                        fields.append(key)
            path = os.path.join(target, "%s_%s.csv" % (name, STAMP))
            with open(path, "w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=fields)
                writer.writeheader()
                for row in rows:
                    writer.writerow(row)
            print("wrote %s (%d rows, %d columns)" % (path, len(rows), len(fields)))


if __name__ == "__main__":
    main()
