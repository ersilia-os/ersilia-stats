"""Check that every chart in site/config.js has data in site/data/stats.json.

The site renders a card only if its metric exists and is non-empty. That used to
fail silently: a renamed metric left a hole in the grid, and a whole page of charts
once disappeared from the deployed site without anything erroring. This turns that
class of mistake into a failing build.

Reports three things:
  * config paths with no matching metric in stats.json        (error)
  * config paths whose metric is present but empty            (warning)
  * exported metrics no chart references                      (warning)

Usage:
    python scripts/check_config_paths.py [--config site/config.js]
                                         [--stats site/data/stats.json]
                                         [--strict]
"""
import argparse
import json
import re
import sys

# `data: "section.metric"` and the same key inside a toggle's source list.
DATA_PATH_RE = re.compile(r"""\bdata:\s*["']([A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+)+)["']""")


def config_paths(text):
    """Ordered, de-duplicated dot paths referenced by config.js."""
    seen, out = set(), []
    for match in DATA_PATH_RE.finditer(text):
        path = match.group(1)
        if path.startswith("__"):
            continue  # synthetic, built in the client (the landing growth index)
        if path not in seen:
            seen.add(path)
            out.append(path)
    return out


def resolve(sections, path):
    node = sections
    for key in path.split("."):
        if not isinstance(node, dict) or key not in node:
            return None
        node = node[key]
    return node


def is_empty(metric):
    if not isinstance(metric, dict):
        return True
    for key in ("labels", "points", "cells", "rows", "tree", "series"):
        value = metric.get(key)
        if isinstance(value, list) and value:
            return False
    return True


def exported_paths(sections):
    out = []
    for section, metrics in sections.items():
        if not isinstance(metrics, dict):
            continue
        for name, metric in metrics.items():
            if isinstance(metric, dict):
                out.append("%s.%s" % (section, name))
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--config", default="site/config.js")
    parser.add_argument("--stats", default="site/data/stats.json")
    parser.add_argument("--strict", action="store_true",
                        help="Also fail on empty metrics AND unused exports.")
    parser.add_argument("--fail-on-empty", action="store_true",
                        help="Fail on empty metrics only. This is the CI gate: an empty "
                             "metric means a table came back with no usable rows, and the "
                             "card would deploy showing its empty state. Unused exports are "
                             "deliberate — they are the CSVs offered on the Downloads view — "
                             "so --strict is too blunt for a build gate.")
    args = parser.parse_args()

    with open(args.config, encoding="utf-8") as handle:
        paths = config_paths(handle.read())
    with open(args.stats, encoding="utf-8") as handle:
        stats = json.load(handle)
    sections = stats.get("sections", {})

    missing, empty = [], []
    for path in paths:
        metric = resolve(sections, path)
        if metric is None:
            missing.append(path)
        elif is_empty(metric):
            empty.append(path)

    unused = sorted(set(exported_paths(sections)) - set(paths))

    print("Checked %d chart data paths against %s" % (len(paths), args.stats))
    if missing:
        print("\nMISSING from stats.json (%d) — these charts cannot render:" % len(missing))
        for path in missing:
            print("  - %s" % path)
    if empty:
        print("\nEMPTY in this snapshot (%d) — the card will show its empty state:" % len(empty))
        for path in empty:
            print("  - %s" % path)
    if unused:
        print("\nEXPORTED but unused by any chart (%d):" % len(unused))
        for path in unused:
            print("  - %s" % path)
    if not (missing or empty or unused):
        print("All paths resolve and every exported metric is used.")

    if missing:
        raise SystemExit("FAIL: %d chart data path(s) missing from stats.json." % len(missing))
    if args.strict and (empty or unused):
        raise SystemExit("FAIL (strict): %d empty, %d unused." % (len(empty), len(unused)))
    if args.fail_on_empty and empty:
        raise SystemExit("FAIL: %d chart(s) point at an empty metric." % len(empty))
    return 0


if __name__ == "__main__":
    sys.exit(main())
