"""Shared plumbing for the public-data collectors.

`fetch_airtable.py` established the pattern these follow: write one dated CSV per
dataset, prune the snapshot it supersedes so exactly one survives, and exit non-zero on
failure rather than leaving a half-written directory that looks complete.

The three collectors that use this — Docker Hub, GitHub and OpenAlex — differ from the
Airtable one in a way that matters: **their sources are public, so their output is
committed.** That makes the build reproducible without any secret and gives the figures
an audit trail. It also means the disclosure rules apply at the point of writing: no
personal names, and no private repository names (see `fetch_github.py`, which reads only
public repositories for exactly this reason).

Nothing here writes outside its output directory, and nothing here makes a request that
is not a GET.
"""
import csv
import json
import logging
import os
import re
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

SNAPSHOT_RE = re.compile(r"^(?P<name>.+?)_(?P<stamp>\d{8})\.csv$")

# Identifies this client to the APIs that ask for one. OpenAlex in particular routes
# requests with a contact address to a faster pool, and it is simply good manners.
USER_AGENT = "ersilia-stats-collector (+https://github.com/ersilia-os/ersilia-stats)"
CONTACT = "miquel@ersilia.io"


def stamp(now=None):
    """Today's UTC date as YYYYMMDD. Passed in by tests so output is deterministic."""
    return (now or datetime.now(timezone.utc)).strftime("%Y%m%d")


def get_json(url, headers=None, retries=4, backoff=1.5, accept_empty=False):
    """GET and parse JSON, retrying on transient failures.

    `accept_empty` exists for GitHub's statistics endpoints, which answer **202 with an
    empty body** the first time they are asked while the numbers are computed, and only
    return data on a later call. Treating that empty body as "no commits" would silently
    report zero activity for every repository, so callers that can receive a 202 must
    say so and handle `None`.
    """
    request = urllib.request.Request(url, headers={
        "User-Agent": USER_AGENT,
        "Accept": "application/json",
        **(headers or {}),
    })
    last = None
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(request, timeout=45) as response:
                body = response.read()
                if not body:
                    if accept_empty:
                        return None            # 202: computing, ask again later
                    raise ValueError("empty response body")
                return json.loads(body)
        except urllib.error.HTTPError as error:
            last = error
            # 404 is an answer, not a failure: a repository or work may simply be gone.
            if error.code == 404:
                return None
            if error.code == 202 and accept_empty:
                return None
            # 403 from GitHub is usually the rate limit; wait for the reset if told.
            if error.code in (403, 429):
                reset = error.headers.get("X-RateLimit-Reset")
                wait = 60.0
                if reset:
                    wait = max(1.0, float(reset) - time.time()) + 1
                logging.warning("rate limited, waiting %.0fs", min(wait, 300))
                time.sleep(min(wait, 300))
                continue
            if error.code < 500:
                raise
        except (urllib.error.URLError, ValueError, TimeoutError) as error:
            last = error
        time.sleep(backoff * (attempt + 1))
    raise RuntimeError("GET failed after %d attempts: %s (%s)" % (retries, url, last))


def paginate_url(first_url, headers=None, next_key="next"):
    """Follow a JSON API's own `next` link. Used by Docker Hub."""
    url = first_url
    while url:
        payload = get_json(url, headers=headers)
        if payload is None:
            return
        yield payload
        url = payload.get(next_key)


def write_snapshot(out_dir, name, fieldnames, rows, now=None):
    """Write `<name>_<YYYYMMDD>.csv` and return its path.

    Rows are written in the order given; the caller decides the sort, because a stable
    order is what keeps a committed file's diff readable between runs.
    """
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "%s_%s.csv" % (name, stamp(now)))
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    logging.info("wrote %s (%d rows)", path, len(rows))
    return path


def prune_superseded(out_dir, written):
    """Delete older dated snapshots for any dataset written in this run.

    Without this the directory accumulates one CSV per dataset per run and the loader
    has to guess which is current. Only datasets written NOW are pruned, so a collector
    that failed leaves its previous snapshot in place rather than losing it.
    """
    if not os.path.isdir(out_dir):
        return []
    fresh = {os.path.basename(p) for p in written}
    current = set()
    for fname in fresh:
        match = SNAPSHOT_RE.match(fname)
        if match:
            current.add(match.group("name"))

    removed = []
    for fname in sorted(os.listdir(out_dir)):
        if fname in fresh or not fname.endswith(".csv"):
            continue
        match = SNAPSHOT_RE.match(fname)
        if match and match.group("name") in current:
            path = os.path.join(out_dir, fname)
            os.remove(path)
            removed.append(path)
    if removed:
        logging.info("pruned %d superseded snapshot(s)", len(removed))
    return removed


def newest_stamp(out_dir):
    """The newest snapshot stamp in a directory, as YYYYMMDD, or None."""
    if not os.path.isdir(out_dir):
        return None
    stamps = []
    for fname in os.listdir(out_dir):
        match = SNAPSHOT_RE.match(fname)
        if match:
            stamps.append(match.group("stamp"))
    return max(stamps) if stamps else None


def check_freshness(out_dir, max_age_days, label):
    """Exit non-zero if the committed snapshot is missing or too old.

    This is what lets CI nag about stale data without being given permission to write
    any: the workflow runs the collectors in --check mode, and a human refreshes and
    commits. Returns a process exit code.
    """
    found = newest_stamp(out_dir)
    if not found:
        logging.error("%s: no snapshot in %s", label, out_dir)
        return 1
    age = (datetime.now(timezone.utc) - datetime.strptime(found, "%Y%m%d")
           .replace(tzinfo=timezone.utc)).days
    if age > max_age_days:
        logging.error("%s: snapshot %s is %d days old (limit %d). Re-run the collector "
                      "and commit the result.", label, found, age, max_age_days)
        return 1
    logging.info("%s: snapshot %s is %d day(s) old.", label, found, age)
    return 0
