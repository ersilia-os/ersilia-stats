# Ersilia in numbers

Aggregate statistics for the [Ersilia Open Source Initiative](https://ersilia.io), published as a
static site: **[Ersilia in numbers](https://ersilia-os.github.io/ersilia-stats/)**.

The site answers two kinds of question: **what Ersilia is** (models, projects, publications, code,
community, partners) and **how it is used** (Docker pulls, PyPI downloads, citations, GitHub traffic).
This repository holds only the code that collects that data and turns it into the dashboard. It holds
no data of its own: every number is fetched again on each deploy.

## How it works

```
 Airtable  ─┐
 GitHub    ─┤                    data/<source>/           site/data/              GitHub Pages
 Docker Hub─┼── fetch_*.py ──>   one CSV snapshot   ──>   stats.json +    ──>     (static site,
 OpenAlex  ─┤   read-only        per table, in the       one CSV per chart       ECharts)
 PyPI      ─┘                    CI runner only          aggregates only
                                 never committed
                                        │
                                        └── checks: GitHub/Airtable agree, no personal data,
                                            every chart has data, every page renders
```

1. **Fetch.** One script per source writes a dated CSV snapshot into `data/<source>/`. Every
   collector is read-only.
2. **Build.** `scripts/export_site_data.py` reads the newest snapshot of each table and computes
   every figure in `scripts/site_data/` (one module per section). It writes `site/data/stats.json`
   and one CSV per chart. Each chart's takeaway sentence is computed here, so it cannot go stale.
3. **Check.** The build stops if personal data reaches the output, a chart points at a missing
   metric, or a page fails to render (see [What stops a deploy](#what-stops-a-deploy)).
4. **Publish.** `.github/workflows/pages.yml` runs all of the above in one job and deploys `site/`
   to GitHub Pages. It runs **every Monday at 06:00 UTC**, on demand, and on pushes to `main` that
   touch the site, the scripts, `data/` or `requirements.txt`.

The site itself has no backend: `site/config.js` declares every page and chart, and the JavaScript
in `site/js/` renders them from `stats.json` in the browser.

## Data sources

| Source | Script | What it gives | Required |
|---|---|---|---|
| Airtable, *Ersilia Content* and *Ersilia Model Hub* bases | `fetch_airtable.py` | Models, projects, community, publications, repositories, organisations, events, blog posts, videos, countries | Yes |
| GitHub API | `fetch_github.py` | Repository inventory (public/private), commit activity, stars, contributors | Yes |
| GitHub API | `fetch_github_releases.py` | Every release of every model repository | No |
| GitHub (raw files) | `fetch_model_packages.py` | Pinned packages in each model's `install.yml` | No |
| GitHub traffic API | `fetch_github_traffic.py` | Referrers and most-visited pages, accumulated beyond GitHub's 14-day window | No |
| Docker Hub | `fetch_dockerhub.py`, `fetch_docker_tags.py` | Pull counts; per-architecture image size and last-pulled time | No |
| OpenAlex | `fetch_openalex.py` | Citations, open-access status, author-institution countries, by DOI | No |
| PyPI and pypistats.org | `fetch_pypi.py` | Package metadata, releases, rolling download window | No |
| BigQuery (manual) | `convert_pypi_geo.py` | PyPI downloads by country | Committed in `data/pypi_geo/` |

The Airtable table ids are in `data/airtable_api_identifiers.csv`. The `news`, `grants`, `donations`
and `contacts` tables are never fetched (`EXCLUDE_TABLE_SLUGS` in `fetch_airtable.py`).

Citations come from **OpenAlex, not Airtable**. OpenAlex is more conservative than Google Scholar,
so some individual counts are lower than the ones stored in Airtable.

## What the site shows

| Route | Page | What it answers |
|---|---|---|
| `#/` | Home | Headline figures and how Ersilia has grown across four measures |
| `#/models` | Model Hub | Growth and task mix, pathogens and biomedical areas, origins and licences, runtime and image size, ARM64 support, Docker Hub demand, development activity, versioning, most common packages |
| `#/projects` | Projects | The portfolio as a timeline: what ran when, overlap, overrun, status |
| `#/publications` | Publications | Papers with an Ersilia affiliation, citations, open access, collaboration, plus the blog and videos |
| `#/repositories` | Code | Repository composition, commit activity, contributors, most-visited repositories, and Ersilia's PyPI packages and downloads |
| `#/community` | Community | People over time, concurrent involvement, tenure, roles, countries. Aggregates only |
| `#/partners` | Partners | Organisations Ersilia has run projects with, where they are, and the events Ersilia takes part in |
| `#/downloads` | Download the data | Every aggregate as CSV, plus the full dataset as JSON |

Every chart has a caption, a methodology note behind the ⓘ, and a table view of the same numbers.
Definitions, provenance and data-quality caveats live in the **Methods** dialog.

## Privacy rules, enforced in code

- **Aggregates only.** Identifying columns of the community table (`Email`, `Name`, `LinkedIn`,
  `Twitter Handle`, `GitHub Handle`, and free-text fields that embed names) are dropped at fetch
  (`fetch_airtable.py`), dropped again at load (`site_data/load.py`), and the build **aborts** if
  anything email-shaped reaches the output.
- **A count is not disclosure, a name is.** Counts and totals include private repositories; anything
  that names a repository or a contributor covers public ones only. Which repositories are public is
  read from Airtable's `Visibility` column, and `check_github_airtable_sync.py` stops the deploy if
  GitHub disagrees.
- **Private projects stay out.** Only Projects rows whose Airtable `Visibility` is `Public` are
  published; `Private` and blank rows are withheld at fetch (`fetch_airtable.py`), removed again at
  load (`site_data/load.py`), and their ids are stripped from every other table's links, so an
  organisation whose only project is private does not count as a partner. If the `Visibility` field
  is missing, the build fails rather than publishing everything.
- **No data in the repository.** Fetched snapshots and built aggregates are gitignored. The deploy
  re-checks the artifact: a raw snapshot or an email address inside `site/` fails the job.
- **Small numbers.** Percentages are suppressed below n = 10.

Only three things under `data/` are committed, because CI cannot fetch them: the Airtable table ids,
the PyPI-by-country export (`data/pypi_geo/`), and a synthetic fixture (`data/air_tables_sample/`,
`data/collected_sample/`) so pull requests can be checked without secrets.

## Running it locally

```bash
pip install -r requirements.txt          # pandas is pinned on purpose: see the note in the file
export AIRTABLE_API_KEY=...              # read-only Airtable personal access token
export GH_STATS_TOKEN=...                # GitHub token; traffic also needs Administration: Read-only
# (or put both in a local .env, which is gitignored)

python scripts/fetch_airtable.py -t data/airtable_api_identifiers.csv -o data/air_tables/
python scripts/fetch_github.py          -o data/github/
python scripts/fetch_github_releases.py -o data/github/
python scripts/fetch_model_packages.py  -o data/github/
python scripts/fetch_github_traffic.py  -o data/github/
python scripts/fetch_dockerhub.py       -o data/dockerhub/
python scripts/fetch_docker_tags.py     -o data/dockerhub/
python scripts/fetch_openalex.py        -o data/scholar/
python scripts/fetch_pypi.py            -o data/pypi/
python scripts/export_site_data.py      # data/ -> site/data/
python scripts/check_config_paths.py    # every chart still has data behind it
python -m http.server -d site 8000      # http://localhost:8000
node scripts/verify_site.mjs            # headless smoke test, needs Node 22 and Chrome
```

Without any secret, build from the synthetic fixture, as the pull-request check does:

```bash
mkdir -p /tmp/fixture-root
cp -r data/air_tables_sample /tmp/fixture-root/air_tables
cp -r data/collected_sample/. /tmp/fixture-root/
python scripts/export_site_data.py --data-dir /tmp/fixture-root/air_tables
```

Each fetch writes `<table>_<YYYYMMDD>.csv` and deletes the snapshot it replaces. If a fetch fails
halfway, a local folder can mix dates across tables; the sidebar then lists the stale tables.

## Deployment and CI

### Secrets

| Secret | |
|---|---|
| `AIRTABLE_API_KEY` | Required. Read-only personal access token with access to both bases |
| `GH_STATS_TOKEN` | Required. Read access to `ersilia-os` metadata, plus **Administration: Read-only** (fine-grained) or `repo` (classic) for traffic |
| `DOCKERHUB_USERNAME`, `DOCKERHUB_TOKEN` | Optional. Lift Docker Hub's anonymous pagination cap |

### What stops a deploy

Only Airtable and the GitHub inventory are required. Every other collector is non-blocking: if one
fails, the run shows a warning, its cards show an empty state, and the next run fills them back in.
When a deploy fails, the previous version of the site stays live.

| Step | Fails the build when |
|---|---|
| `fetch_airtable.py` | any listed table fails to fetch |
| `fetch_github.py` | the public inventory cannot be fetched |
| `check_github_airtable_sync.py` | GitHub and Airtable disagree about which repositories exist or are public |
| `node --check` | any shipped script does not parse |
| `export_site_data.py` | a privacy guard trips |
| `check_config_paths.py` | a chart points at a metric or row key that does not exist |
| `verify_site.mjs` | a page renders no cards, logs a console error, a row does not sum to 12 columns, a caption overflows, or the page scrolls sideways at 390 px |
| artifact check | a raw snapshot or an email address is inside `site/` |

`.github/workflows/check.yml` runs on every pull request without secrets: ruff, fixture consistency,
a build from the fixture, `check_config_paths.py --fail-on-empty`, `check_degradation.py` (a missing
column must empty a card, never crash the build) and `verify_site.mjs`. It proves the code works, not
that the real numbers are right.

## Maintenance

**Routine (nothing to do).** The weekly run refreshes everything. Check the
[Actions tab](https://github.com/ersilia-os/ersilia-stats/actions) after a Monday run if the site
looks out of date.

**Keep the weekly run alive.** GitHub keeps only 14 days of traffic, so `fetch_github_traffic.py`
merges each fetch into the previous snapshot, carried between runs in the Actions cache. A cache
unused for 7 days is evicted, and the accumulated history with it. Repeated failed runs therefore
reset the traffic history.

**When Airtable changes.** A renamed, deleted or unshared table makes `fetch_airtable.py` fail with
`403 INVALID_PERMISSIONS_OR_MODEL_NOT_FOUND`, and every deploy fails until the table is removed from
`data/airtable_api_identifiers.csv` (and from `scripts/site_data/` if a page reads it). This is what
happened with the Conferences table between 12 and 26 October 2026.

**When GitHub and Airtable disagree.** Fix the Airtable `Visibility` or add the missing repository
row; the deploy check names the repository. Run the full check, including private repositories,
locally only (Actions logs on a public repository are world-readable):

```bash
PYTHONPATH=scripts python3 scripts/check_github_airtable_sync.py --include-private
```

**PyPI downloads by country (manual).** There is no API for it. Export from BigQuery's public
`bigquery-public-data.pypi.file_downloads` dataset, convert with
`python scripts/convert_pypi_geo.py <export.json> -o data/pypi_geo/`, and commit the result. The
script's docstring explains the dataset and the expected export.

**Adding a chart.** Compute the figure in the relevant `scripts/site_data/<section>.py`, then declare
the chart in `site/config.js`; the cards in a row must sum to 12 columns. Run the build,
`check_config_paths.py` and `verify_site.mjs` before pushing. Read
[`docs/design-notes.md`](docs/design-notes.md) first: it lists analyses already tried and rejected,
and the colour and layout rules.

**Adding a data source.** Add a `fetch_<source>.py` using `collect_common.py` (snapshots, retries,
pruning), a fetch step in `pages.yml` with `continue-on-error: true`, and matching data in
`make_fixture.py` so the pull-request check still covers every chart.

## Layout

```
site/
  index.html          app shell: sidebar, route outlet, Methods dialog
  config.js           declarative dashboard: pages, charts, spans, methodology notes
  js/                 router, chart builders, cards, formatting, design tokens
  styles.css          site layer over assets/ersilia.css (Ersilia house stylesheet)
  vendor/             echarts.min.js, world.geo.json (no CDN)
  data/               built by CI, not committed
scripts/
  fetch_*.py          one collector per source (see Data sources)
  collect_common.py, github_api.py, dockerhub_api.py   shared plumbing
  export_site_data.py snapshots -> site/data, with the privacy guards
  site_data/          one module per section, plus parsing, insights and KPIs
  check_*.py          GitHub/Airtable sync, chart paths, degradation
  make_fixture.py     synthetic data for the secret-free pull-request check
  stamp_assets.py     content-hash stamps on asset URLs
  verify_site.mjs     headless smoke test of every page
  convert_pypi_geo.py manual BigQuery export -> data/pypi_geo/
data/                 table ids, PyPI geography, synthetic fixture (everything else is gitignored)
docs/design-notes.md  design decisions, rejected analyses, data-quality findings
```

## Further reading

[`docs/design-notes.md`](docs/design-notes.md) records the reasoning behind the site: the GitHub/Airtable
visibility rules, why the Repositories table no longer stores GitHub figures, what the legacy
Streamlit app had, which fields and analyses were deliberately left out (with the measurements), the
data-quality findings worth fixing at source, and the visual design rules (palette order, type and
spacing scales, chart forms).

---

Brought to you by the [Ersilia Open Source Initiative](https://ersilia.io), a tech nonprofit
fueling sustainable research in the Global South.
