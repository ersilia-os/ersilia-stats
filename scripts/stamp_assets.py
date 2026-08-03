#!/usr/bin/env python3
"""Stamp a content hash onto every asset URL in index.html, so a deploy cannot serve
a half-updated page.

WHY THIS EXISTS
---------------
GitHub Pages sends ``cache-control: max-age=600`` for everything, including the
stylesheet and the scripts. A returning visitor can therefore hold an old
``styles.css`` while fetching a new ``js/cards.js``, or the reverse — and the page is
then a mixture of two builds.

That is not hypothetical. A fix in this repo moved the chart into a wrapper element
(``js/cards.js``) and positioned it out of flow (``styles.css``). With the new script
and the old stylesheet the wrapper has no styling, the chart is back in flow, and the
bug the change fixed reappears exactly as before — which is precisely what happened,
and it cost a round of "it is still broken" against a build that was correct.

The fix is per-file content hashing: ``styles.css?v=a1b2c3d4``. A changed file gets a
new URL and is refetched; an unchanged file keeps its URL and stays cached. Only
``index.html`` needs to be revalidated, and it is the one document browsers are most
willing to revalidate.

Idempotent: an existing ``?v=`` is replaced, so running it twice is a no-op and running
it after an edit updates only what changed. Deterministic: the stamp is a hash of the
file's bytes, not a timestamp, so an unchanged site produces an unchanged index.html
and CI can assert that.

    python3 scripts/stamp_assets.py            # stamp site/index.html in place
    python3 scripts/stamp_assets.py --check     # exit 1 if any stamp is missing/stale
"""
import argparse
import hashlib
import os
import re
import sys

# Local asset references in index.html. Anything with a scheme (https://) is skipped.
PATTERN = re.compile(r'(?P<attr>href|src)="(?P<url>[^"#?:][^"]*?)(?:\?v=[0-9a-f]+)?"')

# Only these are worth stamping: the ones that define behaviour and appearance. The
# favicon and the vendored geometry change essentially never, but including them costs
# nothing and closes the same hole.
STAMPABLE = (".css", ".js", ".png", ".svg")


def short_hash(path):
    with open(path, "rb") as handle:
        return hashlib.sha256(handle.read()).hexdigest()[:8]


def stamp(site_dir, check_only=False):
    index = os.path.join(site_dir, "index.html")
    with open(index, encoding="utf-8") as handle:
        original = handle.read()

    missing = []

    def replace(match):
        url = match.group("url")
        if not url.lower().endswith(STAMPABLE):
            return match.group(0)
        target = os.path.join(site_dir, url)
        if not os.path.exists(target):
            missing.append(url)
            return match.group(0)
        return '%s="%s?v=%s"' % (match.group("attr"), url, short_hash(target))

    updated = PATTERN.sub(replace, original)

    if missing:
        for url in missing:
            print("error: index.html references a file that does not exist: %s" % url,
                  file=sys.stderr)
        return 1

    stamped = len(re.findall(r"\?v=[0-9a-f]{8}", updated))
    if check_only:
        if updated != original:
            print("error: site/index.html asset stamps are missing or stale.\n"
                  "       Run: python3 scripts/stamp_assets.py", file=sys.stderr)
            return 1
        print("index.html: %d asset stamps present and current." % stamped)
        return 0

    if updated == original:
        print("index.html: %d asset stamps already current." % stamped)
        return 0
    with open(index, "w", encoding="utf-8") as handle:
        handle.write(updated)
    print("index.html: stamped %d asset URLs." % stamped)
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--site", default="site", help="Site directory.")
    parser.add_argument("--check", action="store_true",
                        help="Do not write; fail if any stamp is missing or stale.")
    args = parser.parse_args()
    raise SystemExit(stamp(args.site, check_only=args.check))


if __name__ == "__main__":
    main()
