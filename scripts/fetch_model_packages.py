#!/usr/bin/env python3
"""Every model's pinned install command, from install.yml.

WHY THIS EXISTS
----------------
Docker image size (fetch_docker_tags.py) says HOW heavy a model's image is; nothing
already collected says WHY. `install.yml` is the ersilia-model-template's own install
manifest — a `python` version and a `commands` list of `[manager, package, version]`,
sometimes with more: a channel on a `conda` row, or extra pip arguments on a `pip` one,
commonly `"--index-url", "https://download.pytorch.org/whl/cpu"`. Everything after the
version is kept, space-joined, in `extra`. It used to keep only the fourth element, which
recorded a bare `--index-url` and dropped the URL after it — the one part that says
whether torch is the CPU-only build. One
fixed path per model repository, so this is one GitHub Contents API call per model
rather than a clone.

Joining this against the Docker Hub size reading turns "some models are heavy" into
"these specific packages are the ones showing up in the heavy ones" — see
scripts/site_data/packages.py.

NOT EVERY LINE IN `commands` IS A PACKAGE. A bare string entry (e.g. a model that
runs a post-install setup script) is not a `[manager, package, version]` triple and
is skipped rather than guessed at; only list-shaped commands are parsed.

    python3 scripts/fetch_model_packages.py -o data/github/
    python3 scripts/fetch_model_packages.py --check          # freshness gate for CI
"""
import argparse
import ast
import base64
import logging
import re
import sys

from collect_common import check_freshness, get_json, prune_superseded, write_snapshot
from github_api import API, MODEL_RE, ORG, auth_headers, list_repos

FIELDS = ["repo", "manager", "package", "version", "extra"]

# Matches a YAML sequence item that is itself a Python/JSON list literal, e.g.
# `    - ["pip", "rdkit", "2026.3.4"]`. `ast.literal_eval` then parses the bracketed
# part directly rather than pulling in a YAML library for one fixed, narrow shape —
# this project pins exactly three dependencies (see requirements.txt) and PyYAML
# would be a fourth for something a dozen lines of stdlib already does.
COMMAND_RE = re.compile(r"^\s*-\s*(\[.*\])\s*$")


def parse_install_yml(text):
    """``[(manager, package, version, extra)]`` from an install.yml's `commands`
    list. Non-list entries (a bare setup-script string) are skipped."""
    rows = []
    for line in text.splitlines():
        match = COMMAND_RE.match(line)
        if not match:
            continue
        try:
            parsed = ast.literal_eval(match.group(1))
        except (ValueError, SyntaxError):
            continue
        if not isinstance(parsed, list) or len(parsed) < 3:
            continue
        manager = str(parsed[0]).strip().lower()
        package = str(parsed[1]).strip()
        version = str(parsed[2]).strip()
        # Every element after the version: a flag and its value are separate list items
        # (`"--index-url", "https://…/whl/cpu"`), and the value is the informative half.
        extra = " ".join(str(x).strip() for x in parsed[3:] if str(x).strip())
        if manager and package:
            rows.append((manager, package, version, extra))
    return rows


def fetch_install_yml(org, repo, headers):
    """The raw text of ``install.yml`` at a repository's default branch, or ``None``
    if the repository has no such file (a template variant, or one mid-incorporation).
    """
    url = "%s/repos/%s/%s/contents/install.yml" % (API, org, repo)
    payload = get_json(url, headers=headers)
    if not payload or "content" not in payload:
        return None
    try:
        return base64.b64decode(payload["content"]).decode("utf-8", errors="replace")
    except (ValueError, TypeError):
        return None


def collect(org, repos, headers):
    rows = []
    skipped = 0
    for i, repo in enumerate(repos, start=1):
        text = fetch_install_yml(org, repo, headers)
        if text is None:
            skipped += 1
        else:
            for manager, package, version, extra in parse_install_yml(text):
                rows.append({"repo": repo, "manager": manager, "package": package,
                            "version": version, "extra": extra})
        if i % 25 == 0:
            logging.info("fetched install.yml for %d/%d repos", i, len(repos))
    if skipped:
        logging.warning("%d of %d repos have no install.yml and are absent from this "
                        "snapshot, not zeroed", skipped, len(repos))
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("-o", "--out-dir", default="data/github")
    parser.add_argument("--org", default=ORG)
    parser.add_argument("--check", action="store_true",
                        help="Do not fetch; fail if the local snapshot is stale.")
    parser.add_argument("--max-age-days", type=int, default=21)
    args = parser.parse_args()

    if args.check:
        return check_freshness(args.out_dir, args.max_age_days, "model-packages")

    headers = auth_headers()
    raw = list_repos(args.org, headers, visibility="public")
    repos = [r.get("name", "") for r in raw if MODEL_RE.match(r.get("name") or "")]
    if not repos:
        logging.error("no model repos found for %s", args.org)
        return 1
    logging.info("fetching install.yml for %d model repos", len(repos))

    rows = collect(args.org, repos, headers)
    if not rows:
        logging.error("no install.yml commands parsed for any repo — refusing to "
                      "write an empty snapshot")
        return 1
    written = write_snapshot(args.out_dir, "model_packages", FIELDS, rows)
    prune_superseded(args.out_dir, [written])
    return 0


if __name__ == "__main__":
    sys.exit(main())
