#!/usr/bin/env python3
"""Fail loudly when GitHub and the Airtable registry disagree.

WHY THIS IS A GATE AND NOT A REPORT
-----------------------------------
The site decides which repository names it may publish by reading Airtable's `Visibility`
column. Nothing checks that column against GitHub. So a repository that is `Public` in
Airtable and private on GitHub would have its **name published**, and the failure would be
silent — there is no test that could notice, because from the site's point of view nothing
is wrong.

That is the case this exists for. It has not happened yet; every other category here is a
consequence of the same absence of checking, and one of them is live today: `eos` is listed
on the site with 92 stars and 190 forks, and `GET /repos/ersilia-os/eos` returns **404**.

THE TWO TABLES SPLIT CLEANLY, WHICH IS WHAT MAKES THIS TRACTABLE
    models        243 rows, `Identifier` -> a repository named `eos` + digit + 3 alphanumerics
    repositories  179 rows, `Name`       -> everything else, and ZERO model repositories

Verified: all 243 identifiers match `github_api.MODEL_RE`, no `repositories` row does, and
the two sets do not intersect. So the regex is the whole distinction between the two, and
the check can treat them as separate namespaces.

PUBLIC BY DEFAULT, AND THAT IS A FEATURE
----------------------------------------
Two model repositories are private (`eos6wdw`, `eos7ack`), so comparing Airtable against a
public-only listing invents drift that is not there. The fix is not a private token in CI:
GitHub Actions logs on a public repository are world-readable, and a redaction rule that has
to hold in every future edit of this file is a bad way to keep a name secret.

Instead the default mode uses only public data, and exempts models whose Airtable status is
`In progress` from needing a public repository. `eos6wdw` and `eos6ru5` are the only two
models with no public repository and **both** are `In progress`, so the default mode has
zero false alarms while enumerating nothing private.

`--include-private` then does the complete job locally, where the output goes to a terminal
rather than a log. It writes no file, ever.

    # locally, the full picture
    export GH_STATS_TOKEN=...
    PYTHONPATH=scripts python3 scripts/check_github_airtable_sync.py --include-private

    # what CI runs: committed public inventory vs the Airtable snapshot, no GitHub token
    PYTHONPATH=scripts python3 scripts/check_github_airtable_sync.py
"""
import argparse
import csv
import glob
import logging
import os
import sys

from github_api import MODEL_RE, ORG, auth_headers, list_repos

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

# Repositories that exist on GitHub and are deliberately not curated in Airtable.
# `.github` holds organisation-level community health files; it is a GitHub convention,
# not a project. Anything added here must be justified in a comment.
IGNORED = {".github"}

# A model with one of these statuses is expected to have a public repository. `In progress`
# and anything unrecognised is exempt: a model still being built may legitimately have no
# repository yet, or a private one.
PUBLIC_EXPECTED_STATUSES = {"Ready", "Archived", "In maintenance"}


def newest_repos_csv(github_dir):
    paths = sorted(glob.glob(os.path.join(github_dir, "repos_*.csv")))
    return paths[-1] if paths else None


def read_public_inventory(github_dir):
    """`{name: row}` from the committed public inventory.

    Reading the CSV rather than calling GitHub is what lets the default mode need no token
    at all: the file is public-only by construction, because `fetch_github.py` asks
    `list_repos` for `visibility="public"`.
    """
    path = newest_repos_csv(github_dir)
    if not path:
        return None, None
    with open(path, newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    return {(r.get("name") or "").strip(): r for r in rows if (r.get("name") or "").strip()}, path


def read_live_inventory(org, headers):
    """`{name: {"private": bool}}` for every repository the token can see."""
    out = {}
    for repo in list_repos(org, headers, visibility="all"):
        name = (repo.get("name") or "").strip()
        if name:
            out[name] = {"private": bool(repo.get("private"))}
    return out


def read_airtable(data_dir):
    """The two registries, as plain dicts.

    `load_tables` normalises columns to lower_snake_case, so `Identifier` is `identifier`
    and `Visibility` is `visibility`.
    """
    from site_data import load
    tables = load.load_tables(data_dir)

    models = {}
    frame = tables.get("models")
    if frame is not None and "identifier" in frame.columns:
        for i in range(len(frame)):
            identifier = str(frame["identifier"].iloc[i] or "").strip()
            if identifier:
                status = ""
                if "status" in frame.columns:
                    status = str(frame["status"].iloc[i] or "").strip()
                models[identifier] = {"status": status}

    repos = {}
    frame = tables.get("repositories")
    if frame is not None and "name" in frame.columns:
        for i in range(len(frame)):
            name = str(frame["name"].iloc[i] or "").strip()
            if not name:
                continue
            visibility = ""
            if "visibility" in frame.columns:
                visibility = str(frame["visibility"].iloc[i] or "").strip()
            repos[name] = {"visibility": visibility}
    return models, repos


def compare(models, repos, github, include_private):
    """Every disagreement, as `(severity, category, name, message)`.

    Severity is `"error"` or `"warning"`. `github` maps name -> info; in public-only mode
    every entry is public by definition, and `private` is absent.
    """
    findings = []
    gh_names = set(github)
    gh_models = {n for n in gh_names if MODEL_RE.match(n)}
    gh_other = gh_names - gh_models

    def is_private(name):
        return bool((github.get(name) or {}).get("private"))

    # --- models: Airtable -> GitHub ------------------------------------------------
    for identifier, info in sorted(models.items()):
        status = info["status"]
        if identifier in gh_names:
            if is_private(identifier) and status in PUBLIC_EXPECTED_STATUSES:
                findings.append(("error", "model-private", identifier,
                                 "model is '%s' in Airtable but its repository is PRIVATE "
                                 "on GitHub. Either publish the repository or change the "
                                 "status." % status))
            continue
        if status in PUBLIC_EXPECTED_STATUSES:
            findings.append(("error", "model-missing", identifier,
                             "model is '%s' in Airtable but has no public repository. It "
                             "was deleted, renamed, or the identifier is wrong." % status))
        elif include_private:
            # Only reportable when private repositories were listed; otherwise "no public
            # repo" is the expected state for an in-progress model and says nothing.
            findings.append(("warning", "model-in-progress", identifier,
                             "model is '%s' in Airtable and has no repository at all, not "
                             "even a private one." % (status or "unset")))

    # --- models: GitHub -> Airtable ------------------------------------------------
    for name in sorted(gh_models - set(models)):
        findings.append(("error", "model-undocumented", name,
                         "a %s model repository exists on GitHub with no row in the "
                         "Airtable models table."
                         % ("private" if is_private(name) else "public")))

    # --- other repositories: Airtable -> GitHub ------------------------------------
    for name, info in sorted(repos.items()):
        visibility = info["visibility"]
        if name not in gh_names:
            if visibility == "Public":
                findings.append(("error", "repo-missing", name,
                                 "Airtable lists this as Public but there is no public "
                                 "repository. The site publishes its name and its stale "
                                 "numbers."))
            elif include_private:
                findings.append(("error", "repo-missing", name,
                                 "Airtable lists this as %s but no repository exists."
                                 % (visibility or "unset")))
            continue
        if visibility == "Public" and is_private(name):
            findings.append(("error", "repo-disclosure", name,
                             "Airtable says Public, GitHub says PRIVATE. The site would "
                             "publish the name of a private repository."))
        elif visibility == "Private" and not is_private(name) and name in github:
            # The harmless direction: the site over-hides. Worth knowing, not worth failing.
            findings.append(("warning", "repo-overhidden", name,
                             "Airtable says Private but the repository is public on "
                             "GitHub, so the site hides work that is already visible."))

    # --- other repositories: GitHub -> Airtable ------------------------------------
    for name in sorted(gh_other - set(repos) - IGNORED):
        findings.append(("error", "repo-undocumented", name,
                         "a %s repository exists on GitHub with no row in the Airtable "
                         "repositories table." % ("private" if is_private(name) else "public")))
    return findings


HINTS = {
    "model-missing": "Check whether the repository was renamed. If the model was never "
                     "published, set its status to 'In progress' in Airtable.",
    "model-private": "The models table has no visibility column, so a private repository "
                     "with a public status is indistinguishable from a mistake.",
    "model-undocumented": "Add a row to the Airtable models table, or delete the repository.",
    "repo-missing": "Delete the Airtable row, or restore the repository. Until then the "
                    "site reports numbers for something that does not exist.",
    "repo-disclosure": "THIS IS THE ONE THAT MATTERS. Set Visibility to Private in Airtable "
                       "before the next deploy.",
    "repo-undocumented": "Add a row to the Airtable repositories table with its Type, or "
                         "add the name to IGNORED in this script with a reason.",
    "repo-overhidden": "Set Visibility to Public in Airtable if the repository is meant "
                       "to be visible.",
    "model-in-progress": "No action needed unless the identifier is a typo.",
}


def report(findings, mode):
    errors = [f for f in findings if f[0] == "error"]
    warnings = [f for f in findings if f[0] == "warning"]

    if not findings:
        print("GitHub and Airtable agree (%s)." % mode)
        return 0

    by_category = {}
    for severity, category, name, message in findings:
        by_category.setdefault((severity, category), []).append((name, message))

    print("")
    print("=" * 78)
    print(" GITHUB AND AIRTABLE DISAGREE — %d error(s), %d warning(s)"
          % (len(errors), len(warnings)))
    print(" mode: %s" % mode)
    print("=" * 78)
    for (severity, category), entries in sorted(by_category.items()):
        print("")
        print("%s  %s  (%d)" % ("ERROR  " if severity == "error" else "warning",
                                category, len(entries)))
        for name, message in entries:
            print("    %-34s %s" % (name, message))
        hint = HINTS.get(category)
        if hint:
            print("    -> %s" % hint)

    print("")
    print("-" * 78)
    if errors:
        print("Fix the errors in Airtable, or in GitHub, then re-run this check.")
    if mode == "public only":
        print("This ran on public data only. Private repositories are not checked; run")
        print("  PYTHONPATH=scripts python3 scripts/check_github_airtable_sync.py "
              "--include-private")
        print("locally, with GH_STATS_TOKEN set, for the complete picture.")
    print("-" * 78)
    return 1 if errors else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--data-dir", default="data/air_tables",
                        help="Airtable snapshot directory.")
    parser.add_argument("--github-dir", default="data/github",
                        help="Committed public inventory, used unless --include-private.")
    parser.add_argument("--include-private", action="store_true",
                        help="List private repositories too, live from GitHub. Needs a "
                             "token. Writes nothing; run this locally, not in CI.")
    parser.add_argument("--warnings-only", action="store_true",
                        help="Report everything but always exit 0.")
    args = parser.parse_args()

    models, repos = read_airtable(args.data_dir)
    if not models and not repos:
        logging.error("no Airtable data in %s. Run scripts/fetch_airtable.py first.",
                      args.data_dir)
        return 1
    logging.info("Airtable: %d models, %d other repositories", len(models), len(repos))

    if args.include_private:
        headers = auth_headers(require=True)
        github = read_live_inventory(ORG, headers)
        private = sum(1 for v in github.values() if v["private"])
        logging.info("GitHub (live, all): %d repositories, %d private",
                     len(github), private)
        mode = "public and private"
    else:
        github, path = read_public_inventory(args.github_dir)
        if github is None:
            logging.error("no repos_*.csv in %s. Run scripts/fetch_github.py first.",
                          args.github_dir)
            return 1
        logging.info("GitHub (committed inventory %s): %d public repositories",
                     os.path.basename(path), len(github))
        mode = "public only"

    findings = compare(models, repos, github, args.include_private)
    code = report(findings, mode)
    return 0 if args.warnings_only else code


if __name__ == "__main__":
    sys.exit(main())
