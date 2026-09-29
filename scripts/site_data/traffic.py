"""GitHub traffic — where visitors come from, and what they look at.

From ``data/github/traffic_sources_<date>.csv`` (``fetch_github_traffic.py``), which is
unlike every other collected source on this site: GitHub's traffic API exposes only a
rolling 14-day window and keeps no history, so the collector APPENDS each run's fetch to
what it already had rather than overwriting. This module always reads the LATEST fetched
window only (never older accumulated ones) — a chart mixing several 14-day windows would
double-count a visitor who showed up in more than one of them.

The two questions this answers that a Docker pull count cannot:

* **Where visitors come from** — a referrer, classified into a handful of categories.
  'Scientific literature' is the one worth watching: someone arriving from a publisher's
  page came via a paper, a different kind of interest from a click through GitHub's UI.
* **What they look at once they arrive** — a page path, reduced to its coarse type. A
  visitor reading source files is evaluating the code; one sitting in issues and pull
  requests is contributing.
"""
from . import insights as ins
from .parse import EMPTY, metric

EMPTY_SECTION = {
    "referrer_categories": dict(EMPTY),
    "top_referrers": dict(EMPTY),
    "page_types": dict(EMPTY),
    "page_type_repeat": dict(EMPTY),
    "most_visited_repos": dict(EMPTY),
}

# Below this many unique visitors, a views-per-visitor ratio is one or two people's
# browsing habit rather than a pattern — the same n=10 floor the rest of the site
# applies to shares.
MIN_UNIQUES = 10

# Order matters: the first category whose rule matches wins, so the specific rules come
# before the loose ones. Ersilia's own properties are checked before anything else, and
# search engines last, because GitHub reports the big ones as a bare product name
# ("Google", "Bing") rather than a host, and a substring rule for "google" would
# otherwise swallow colab.research.google.com and scholar.google.com.
REFERRER_CATEGORIES = [
    ("Ersilia site", ("ersilia.io", "ersilia-os.github.io", "ersilia.gitbook.io")),
    ("AI assistant", ("chatgpt.com", "chat.openai.com", "claude.ai", "perplexity.ai",
                      "gemini.google.com", "copilot.microsoft.com", "phind.com",
                      "doubao.com", "kimi.moonshot.cn", "you.com")),
    ("Scientific literature", ("link.springer.com", "springer.com", "nature.com", "doi.org",
                               "biorxiv.org", "chemrxiv.org", "arxiv.org", "ncbi.nlm.nih.gov",
                               "sciencedirect.com", "acs.org", "rsc.org", "wiley.com",
                               "onlinelibrary.wiley.com", "mdpi.com", "plos.org",
                               "researchgate.net", "semanticscholar.org", "frontiersin.org",
                               "biomedcentral.com", "europepmc.org", "scholar.google.com",
                               "zenodo.org", "elifesciences.org", "oup.com", "cell.com")),
    ("Code & docs hosting", ("github.com", "gitlab.com", "readthedocs.io", "readthedocs.org",
                             "pypi.org", "hub.docker.com", "colab.research.google.com",
                             "kaggle.com", "huggingface.co", "stackoverflow.com",
                             "nbviewer.org", "app.gitbook.com", "gitbook.com",
                             "anaconda.org", "conda.io", "bitbucket.org")),
    ("Social & community", ("t.co", "twitter.com", "x.com", "linkedin.com", "reddit.com",
                            "slack.com", "news.ycombinator.com", "youtube.com", "medium.com",
                            "mastodon.social", "facebook.com", "discord.com", "bsky.app",
                            "telegram.org", "substack.com")),
    ("Search engine", ("google.com", "bing.com", "duckduckgo.com", "yandex.ru", "yandex.com",
                       "baidu.com", "sogou.com", "ecosia.org", "search.brave.com",
                       "startpage.com", "yahoo.com", "naver.com", "qwant.com")),
]

# GitHub reports the major search engines by product name, not by host, so these are
# matched against the whole referrer string instead of the host-suffix rules above.
SEARCH_ENGINE_NAMES = {
    "google", "bing", "duckduckgo", "yahoo", "baidu", "yandex", "ecosia",
    "brave", "startpage", "naver", "sogou", "qwant", "searx", "ask",
}

# Order matters: the first matching path segment wins, so a page is typed by its most
# specific part rather than by the repo it sits under.
PAGE_TYPE_SEGMENTS = {
    "issues": "Issues", "pull": "Pull requests", "pulls": "Pull requests",
    "discussions": "Discussions", "blob": "Source file", "tree": "Source tree",
    "releases": "Releases", "commits": "Commits", "commit": "Commits",
    "actions": "CI runs", "wiki": "Wiki", "graphs": "Insights", "pulse": "Insights",
    "network": "Insights", "stargazers": "Stargazers", "compare": "Compare",
    "search": "Search", "blame": "Source file", "raw": "Source file",
}


def _normalise_referrer(referrer):
    """Lowercase host, with reverse-DNS mobile-app referrers turned back into hosts:
    GitHub reports an Android/iOS app as e.g. ``com.linkedin.android``, which no host
    rule would ever match."""
    host = str(referrer).strip().lower().strip(".")
    parts = host.split(".")
    if len(parts) >= 2 and parts[0] in ("com", "org", "net", "io", "co"):
        host = ".".join(reversed(parts))
    return host


def classify_referrer(referrer):
    if not referrer or (isinstance(referrer, float) and referrer != referrer):
        return "Other"
    raw = str(referrer).strip().lower()
    if raw in SEARCH_ENGINE_NAMES:
        return "Search engine"
    host = _normalise_referrer(raw)
    for category, needles in REFERRER_CATEGORIES:
        for needle in needles:
            if host == needle or host.endswith("." + needle):
                return category
    return "Other"


def classify_page(path):
    if not isinstance(path, str):
        return "Other"
    parts = [p for p in path.strip("/").split("/") if p]
    # /org/repo/... -> the type lives from the third segment onward.
    for part in parts[2:]:
        hit = PAGE_TYPE_SEGMENTS.get(part.lower())
        if hit:
            return hit
    if len(parts) <= 2:
        return "Repo overview"
    return "Other"


def _latest_window(df):
    """Rows from the most recently fetched window only — never several accumulated
    14-day windows at once, which would double-count a repeat visitor."""
    dates = df["fetched_at"].astype(str).str.slice(0, 10)
    return df[dates == dates.max()]


def build(collected):
    df = (collected or {}).get("github_traffic_sources")
    required = {"repo", "kind", "source", "count", "fetched_at"}
    if df is None or df.empty or not required.issubset(df.columns):
        return dict(EMPTY_SECTION)

    latest = _latest_window(df)
    if latest.empty:
        return dict(EMPTY_SECTION)

    return {
        "referrer_categories": _referrer_categories(latest),
        "top_referrers": _top_referrers(latest),
        "page_types": _page_types(latest),
        "page_type_repeat": _page_type_repeat(latest),
        "most_visited_repos": _most_visited_repos(latest),
    }


def _referrer_categories(latest):
    """Visits by where the referrer sits — the ring, not the list."""
    referrers = latest[latest["kind"] == "referrer"]
    if referrers.empty:
        return dict(EMPTY)
    categories = referrers["source"].apply(classify_referrer)
    by_category = referrers.groupby(categories)["count"].sum().sort_values(ascending=False)
    if by_category.empty:
        return dict(EMPTY)
    total = int(by_category.sum())
    lit = int(by_category.get("Scientific literature", 0))
    summary = {"labels": list(by_category.index), "values": list(by_category.values)}
    insight = (
        "%s visits (%s) arrived from a journal, preprint server or scholarly index." % (
            ins.num(lit), ins.pct(lit, total) or "0%",
        ) if lit else ins.leader_short(summary)
    )
    return metric(by_category.index, by_category.values, insight, countNoun="visits", n=total)


def _top_referrers(latest):
    """The individual sites, ranked — the counterpart to the category ring."""
    referrers = latest[latest["kind"] == "referrer"]
    if referrers.empty:
        return dict(EMPTY)
    by_source = referrers.groupby("source")["count"].sum().sort_values(ascending=False).head(12)
    if by_source.empty:
        return dict(EMPTY)
    total_referred = int(referrers["count"].sum())
    return metric(
        by_source.index, by_source.values,
        "%s leads with %s of the %s referred visits in this window." % (
            by_source.index[0], ins.num(int(by_source.iloc[0])), ins.num(total_referred),
        ),
        countNoun="visits",
        n=total_referred,
    )


def _page_types(latest):
    """What a visitor was looking at when they landed — reading code against
    contributing to it."""
    paths = latest[latest["kind"] == "path"]
    if paths.empty:
        return dict(EMPTY)
    types = paths["source"].apply(classify_page)
    by_type = paths.groupby(types)["count"].sum().sort_values(ascending=False)
    if by_type.empty:
        return dict(EMPTY)
    return metric(
        by_type.index, by_type.values,
        ins.leader({"labels": list(by_type.index), "values": list(by_type.values)}, "page views"),
        countNoun="views",
        n=int(by_type.sum()),
    )


def _page_type_repeat(latest):
    """Views per unique visitor, by page type — which kind of page draws people BACK,
    as against a one-time look.

    `page_types` beside this counts raw views; ``uniques`` (GitHub's own per-path
    visitor count) is otherwise unused anywhere on the site. A ratio near 1 is a
    visitor who looked once; well above it is the same visitor returning repeatedly,
    which for something like CI-run or issue pages is what checking back on
    in-progress work looks like from the outside.
    """
    paths = latest[latest["kind"] == "path"]
    if paths.empty or "uniques" not in paths.columns:
        return dict(EMPTY)
    types = paths["source"].apply(classify_page)
    grouped = paths.groupby(types)[["count", "uniques"]].sum()
    grouped = grouped[grouped["uniques"] >= MIN_UNIQUES]
    if grouped.empty:
        return dict(EMPTY)
    ratio = (grouped["count"] / grouped["uniques"]).sort_values(ascending=False)
    total_views = int(grouped["count"].sum())
    return metric(
        ratio.index, [round(float(v), 2) for v in ratio.values],
        "%s draws %sx as many views as unique visitors, the most repeat traffic of "
        "any page type with enough visitors to compare; %s is the least, at %sx." % (
            ratio.index[0], round(float(ratio.iloc[0]), 1),
            ratio.index[-1], round(float(ratio.iloc[-1]), 1),
        ),
        unit="views per visitor",
        n=total_views,
    )


def _most_visited_repos(latest):
    """Which repositories carry the traffic, from the popular-paths endpoint."""
    paths = latest[latest["kind"] == "path"]
    if paths.empty:
        return dict(EMPTY)
    by_all_repos = paths.groupby("repo")["count"].sum()
    by_repo = by_all_repos.sort_values(ascending=False).head(12)
    if by_repo.empty:
        return dict(EMPTY)
    return metric(
        by_repo.index, by_repo.values,
        ins.concentration(list(by_all_repos.values), "repositories' page views"),
        countNoun="views",
        n=int(paths["count"].sum()),
    )
