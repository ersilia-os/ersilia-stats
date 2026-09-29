# Ersilia in numbers

Aggregate statistics for the [Ersilia Open Source Initiative](https://ersilia.io), published as a
static site: **[Ersilia in numbers](https://ersilia-os.github.io/ersilia-stats/)**.

Ersilia's organisational data lives in Airtable — the Model Hub, projects, community, publications,
repositories, partner organisations, events, blog posts and countries. Usage and code activity come
from public APIs: GitHub, Docker Hub, OpenAlex and PyPI. This repository holds the code that fetches
all of it and turns it into a published dashboard, and no data of its own.

```
Airtable, GitHub,  ──fetch──> data/*/  ──export──> site/data/ ──> GitHub Pages
Docker Hub,                   in the CI runner     aggregate-only
OpenAlex, PyPI                only, never committed
```

Everything is **read-only** with respect to every source.

## What is not in this repository

The data. CI fetches every source afresh on each deploy (`.github/workflows/pages.yml`), builds
`site/data/` from it and publishes the result. Neither the fetched snapshots nor the built
aggregates are committed (see `.gitignore`); the Airtable community table in raw form contains
personal data, and a public repository has no business holding a copy of the source records.

Three things under `data/` *are* committed, because CI cannot fetch them:

- `data/airtable_api_identifiers.csv` — the base and table ids, which are configuration;
- `data/pypi_geo/` — PyPI downloads by country, from a manual BigQuery export
  (`scripts/convert_pypi_geo.py` explains why there is no API for it);
- `data/air_tables_sample/` and `data/collected_sample/` — a synthetic fixture, so pull requests
  can be checked without any secret (`scripts/make_fixture.py`).

Grants, donations, contacts, news and videos are never fetched.

## Disclosure rules, enforced in code

- **Aggregates only.** The community table's identifying columns (`Email`, `Name`, `LinkedIn`,
  `Twitter Handle`, `GitHub Handle`, and the free-text `Description` / `Contribution` fields that
  embed names) are dropped when snapshots are fetched (`scripts/fetch_airtable.py`), dropped again
  when they are read (`scripts/site_data/load.py`), and the export **aborts** if anything
  email-shaped reaches the output.
- **A count is not disclosure, a name is.** Repository counts, dates, types and totals cover *all*
  repositories including the private ones — excluding them made the totals quietly wrong. Anything
  that names a repository or a contributor covers the public ones only. The public/private split is
  published rather than hidden.
- **The deploy re-checks the artifact** before publishing: no raw snapshot, no address, or the job
  fails.

Percentages are suppressed below n=10, where a share invites a conclusion the sample cannot support.

## The site

| Route | What it answers |
|---|---|
| `#/` | Headline figures, and how Ersilia has grown across four measures on one indexed axis |
| `#/models` | The Model Hub: growth, task mix, pathogens targeted, wrap lag, scaling limit, footprint |
| `#/projects` | The project portfolio as a timeline — concurrency, overrun, status |
| `#/publications` | Output and accumulated citations, venue impact, African collaboration |
| `#/repositories` | Public code: popularity against activity, commit concentration, contributors |
| `#/pypi` | Ersilia's PyPI packages: releases, Python support, a rolling download window. Not yet split into Model Hub or Code |
| `#/community` | Who has taken part: people over time, concurrent involvement, tenure, roles, countries. Aggregates only |
| `#/reach` | "Countries & partners" — where Ersilia works, how that maps onto its Global South mission, and who its partners are |
| `#/outreach` | "Events & writing" — events, the blog, and the conferences Ersilia tracks |
| `#/downloads` | Every aggregate as CSV, plus the full dataset as JSON |

Field completeness and the other data-quality caveats live in the **Methods** dialog rather than in a
view of their own — they are caveats about the numbers, so they belong beside the definitions.

Each chart carries a **takeaway computed at build time** — so it cannot go stale — a methodology note
behind the ⓘ, and a table view of the same numbers. Definitions and provenance live in the **Methods**
dialog.

## Running it locally

Fetch everything, build, and serve — the same steps `pages.yml` runs. Tokens can also go in a
local `.env`, which is gitignored:

```bash
pip install -r requirements.txt
export AIRTABLE_API_KEY=...    # read-only Airtable personal access token
export GH_STATS_TOKEN=...      # GitHub token; traffic also needs Administration: Read-only
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
```

Or build from the synthetic fixture with no secrets at all, as `check.yml` does:

```bash
mkdir -p /tmp/fixture-root
cp -r data/air_tables_sample /tmp/fixture-root/air_tables
cp -r data/collected_sample/. /tmp/fixture-root/
python scripts/export_site_data.py --data-dir /tmp/fixture-root/air_tables
```

Each fetch writes `<table>_<YYYYMMDD>.csv` and prunes the snapshot it supersedes, so exactly one
snapshot per table is kept.

### What the legacy Streamlit app had, and what was taken from it

The predecessor (`ersilia-stats-capstone`, private, archived) was re-read in full against
this dashboard — every section, `scripts/plots.py`, and all 57 notebook cells including the
markdown ones that state intentions never implemented. **It is now the thinner dashboard**;
almost everything it draws, this site draws in a better form. Three things were missing and
have been added: the most-cited publications table, partner engagement depth, and licence
openness.

The more useful outcome was a list of tempting analyses the data does not support, recorded
so they are not rebuilt:

- **Composite indices are rejected on principle.** The capstone's headline publications
  chart was `0.25·citations_percentile + 0.20·senior + 0.35·african_collaboration +
  0.20·research`, with the weights as live sliders — a metric invented rather than measured,
  and a ranking the viewer can dial to taste. The notebook proposes a *different* weighting
  for the same idea, which is the argument against both. The same applies to the never-built
  "repository health score".
- **Repository health scatters** are outlier artefacts: Pearson stars-vs-subscribers is 0.88
  but Spearman is 0.43. The log-log stars-vs-commits scatter here is the honest version.
- **Repository age vs attention**: Spearman 0.36 / 0.43 / 0.13. Too weak to chart.
- **Open-issue counts** carry no signal — 162 of 178 repositories have exactly zero — and
  Ersilia uses issues as a task tracker, so "many open issues" means active, not unhealthy.
- **The stakeholder network map** the notebook wanted is infeasible on the data, not for
  want of plumbing: only 6 of 36 projects list two organisations and none lists more, so the
  graph is 6 disjoint edges over 12 of 320 nodes and "most central partner" is undefined.
- **Linking contributors to their outputs** is impossible by design: the community table has
  no person identifier at all, since name, email, handle and contribution are dropped at
  fetch. That is the privacy rule working as intended.

## Deploying

`.github/workflows/pages.yml` is the whole pipeline in one job: fetch, check, build, deploy. It runs
weekly, on demand, and on pushes to `main` that touch the site, the scripts, `data/` or
`requirements.txt`. Repository secrets:

| Secret | |
|---|---|
| `AIRTABLE_API_KEY` | required; a read-only personal access token |
| `GH_STATS_TOKEN` | required; read access to `ersilia-os` metadata, plus **Administration: Read-only** (fine-grained) or `repo` (classic) for the traffic endpoints |
| `DOCKERHUB_USERNAME`, `DOCKERHUB_TOKEN` | optional; lift Docker Hub's anonymous pagination cap |

GitHub keeps only a 14-day traffic window, so `fetch_github_traffic.py` accumulates a history by
merging each fetch into the previous snapshot. The workflow carries that snapshot between runs in
the Actions cache. A cache unused for seven days is evicted, and with it the history, so the weekly
schedule has to keep running.

Only two fetches are required: Airtable, and the GitHub inventory the public/private check reads.
Every other collector is non-blocking. If one fails, the run shows a warning, its cards show their
empty state, and the rest of the site still refreshes; the next run fills them back in. An empty
chart is likewise a warning, not a failure, because it means a source changed rather than the code
broke.

What does stop a deploy, leaving the previous deployment live:

| Step | Fails the build when |
|---|---|
| `pip install -r requirements.txt` | — (but the pin matters: see the note in that file) |
| `fetch_airtable.py` | any table fails to fetch |
| `fetch_github.py` | the public inventory cannot be fetched |
| `check_github_airtable_sync.py` | GitHub and Airtable disagree about which repositories exist or which are public |
| `node --check` on `config.js` and `js/*.js` | any shipped script does not parse |
| `export_site_data.py` | a PII guard trips, or an email-shaped string reaches the output |
| `check_config_paths.py` | a chart points at a metric that does not exist, or a table row key that does not |
| `verify_site.mjs` | a route renders no cards, logs a console error, has a row not summing to 12, has a caption that does not fit, or scrolls sideways at 390px |
| the artifact grep | a raw snapshot or an address is inside `site/` |

`verify_site.mjs` exists because none of the Python checks can see broken JavaScript: a single stray
character in `config.js` used to deploy a page stuck on "Loading figures…" while the workflow
reported success. It is self-contained — it serves `site/`, drives headless Chrome over the DevTools
protocol using Node 22's built-in WebSocket, and needs no `npm install`. Run it locally the same way
CI does:

```bash
node scripts/verify_site.mjs
```

`.github/workflows/check.yml` runs on every pull request and needs no secrets: it lints with ruff,
checks the fixture matches `make_fixture.py`, builds the site from the fixture, and runs
`check_config_paths.py --fail-on-empty` (the fixture is built to give every chart data, so an empty
one there is a bug), `check_degradation.py` (a missing column must empty a card, never crash
the build) and `verify_site.mjs` against it. The fixture is invented, so this proves the code
works, not that the real numbers are right.

**The site's citation figures come from OpenAlex, not Airtable.** OpenAlex is a more conservative
index than Google Scholar, which counts preprints and theses, so some individual counts are lower
than the ones stored in Airtable even though the total is higher.

### Keeping GitHub and Airtable in step

The site decides **which repository names it may publish** by reading Airtable's `Visibility`
column, and nothing used to check that column against GitHub. A repository marked `Public` in
Airtable and private on GitHub would have its name published, and no test could have noticed —
from the site's point of view nothing would be wrong.

`scripts/check_github_airtable_sync.py` is that check, and it runs in `pages.yml` **before the
build**, so a disagreement stops a deploy rather than being discovered afterwards.

The two tables split cleanly, which is what makes this tractable: all 243 rows of `models` have
an `Identifier` matching `^eos[0-9][0-9a-z]{3}$`, the 179 rows of `repositories` hold **zero**
model repositories, and the two sets do not intersect. So `github_api.MODEL_RE` is the whole
distinction. It is deliberately stricter than `^eos[0-9a-z]{4}$` because **ten repositories
begin with `eos` and are not models** — `eos-template`, `eosbench`, `eosdev`, `eos-demo`,
`eos-analysis-template`, `eos-lite-chem`, `eos-python-package`, `eosframes`, `eosquality`,
`eosvc`.

**CI uses public data only, and that is a feature.** Two model repositories are private, so
comparing against a public-only listing would invent drift; the fix is not a private-scoped
token in CI, because Actions logs on a public repository are world-readable. Instead the
default mode exempts models whose status is `In progress` from needing a public repository —
the only two models without one are both `In progress`, so it has zero false alarms while
enumerating nothing private. Run it locally for the rest:

```bash
export GH_STATS_TOKEN=...
PYTHONPATH=scripts python3 scripts/check_github_airtable_sync.py --include-private
```

That mode writes no file, ever. It finds two more things CI cannot see — a private model
repository with no Airtable row, and a private repository absent from the table.

One category is treated as a **warning** rather than a failure: Airtable saying `Private`
while GitHub says public. The site over-hides, which is the harmless direction.

### The Repositories table no longer stores GitHub figures

Seven columns were deleted from the Airtable Repositories table — `Stars`, `Forks`,
`Open Issues`, `Subscribers`, `Total Commits`, `Contributors` and `Contributor Names` — because
a standing total copied into a spreadsheet is precisely the thing that goes stale unnoticed.
That table now holds only what a person decides: `Name`, `Title`, `Description`, `Status`,
`Type`, `Visibility`, `Projects` and `Creation Date`.

**This is not a cosmetic change: it broke the build.** `repositories.py` did
`int(row["stars"])`, which on the new schema raises `cannot convert float NaN to integer`.
Every count now comes from `data/github/` and is joined onto the Airtable frame by repository
name in `repositories.attach_github_counts()`.

Two consequences worth knowing, both stated on the affected cards:

* **Commit concentration is now public-only.** The collected GitHub snapshot is public by
  design, so a private repository has no commit count to contribute and drops out of the
  Lorenz curve. It covered every repository while the figure lived in Airtable.
* **The star KPI still covers private repositories**, via `org_totals_<date>.csv` — two
  integers, `private_repositories` and `private_stars`, and **no names**. That is what lets
  the total include private work without a private repository name ever being written or
  logged. Measured: 664 stars public, 5 private across 40 repositories.

`Creation Date` was deliberately retained, and it is the GitHub repository creation date —
verified, 139 of 141 rows match `created_at` exactly. Two do not: `chembl-antimicrobial-models`,
and `ersilia-stats`, whose 2023-12-08 is the *capstone* repository's creation date. That is the
same contamination that gave the row 310 commits.

The contributor ranking now comes from GitHub's contributors endpoint rather than the deleted
column, which also ends its hand-maintenance. It publishes **public handles attached to public
commits** — the decision to show them was already taken; the community table's own handles are
still dropped at load and never reach the site. Anonymous contributors are excluded, because
GitHub identifies them by an email address rather than a login and no address is ever fetched.

### A partial fetch cannot be trusted to announce itself

`fetch_airtable.py` writes what it got and prunes superseded files **before** it raises, so a table
that failed keeps its previous CSV. `load.newest_snapshots()` then takes the newest stamp *per table*,
which will happily pair today's Community with last month's Repositories. In CI this is harmless —
the runner starts empty, the job stops and the previous deployment stays live — but a local
working copy can hold mixed-age data.

`meta.snapshot_dates` therefore records one date per table and `meta.stale_tables` names any that are
behind, which the sidebar prints next to the snapshot date. `snapshot_date` on its own is the **max**
across tables, so it always reports the freshest one and can never reveal a stale one.

## What is deliberately not plotted

Every column in every source was cross-referenced against every `scripts/site_data/*.py`, and the
distribution of each unreferenced one measured. What survived is on the site. What did not is
recorded here so it is not proposed again.

**Unusable as recorded** — the numbers are the reason, not taste:

| Field | Measured | Verdict |
|---|---|---|
| `Input Dimension` (models) | **all 234 values are "1"** | zero variance |
| `Model Size`, `Environment Size` | **mixed units** — 47 models at "1", 5 at "2728" | not comparable; Docker image size answers the real question |
| `topics` (GitHub) | **7 of 384** repositories have any | too sparse to chart |
| `star_count` (Docker Hub) | max 2, non-zero on 7 of 271 | no signal |
| `Interpretation` (models) | free text, ~236 near-distinct values | not a distribution |
| `Focus Region` (organisations) | **three spellings of one region** — "Subsaharan Africa" 64, "Africa" 31, "Sub-Saharan Africa" 26 | needs cleaning before it can be counted |

**Excluded on policy, not merit.** `Opportunities` (organisations) is a fundraising pipeline —
Grants 181, In-kind 109, Fellowship 42 — and grants and donations are never published here.
`Team` (projects), `Authors`, `Abstract` and `Senior` (publications) are personal data or curated
narrative.

**Correctly redundant.** Airtable formula duplicates of dates already in use
(`Incorporation Quarter`/`Year`, `Start`/`End Quarter`/`Year`/`Month`, `Year Web`); scholar
`is_open_access` (superseded by `oa_status`, which also distinguishes closed),
`institution_count` (a weaker form of the countries-per-paper chart), `referenced_works_count`,
`publication_date`; GitHub `fork`, `size_kb`, `has_issues`, `default_branch`, and `created_at`
(the Airtable `Creation Date` already drives that series).

**Three model-level analyses that looked good and are wrong.** All measured on the 237 models that
resolve in Airtable, GitHub and Docker Hub together; the detail is in
`scripts/site_data/model_activity.py`:

* **effort per model by incorporation year** — raw median commits fall 60 → 30 from the 2021 cohort
  to 2026, which reads as declining effort. Normalising by months since incorporation *inverts* it,
  1.03 → 10.06 per month. Both are exposure artefacts, because a model's commits arrive in a burst
  around packaging. Neither measures effort.
* **effort by biomedical area** — 35 to 55 median commits, groups as small as eight, confounded by
  cohort age.
* **pull counts against commits** — Spearman 0.52, which looks like attention following effort and
  is almost certainly CI rebuilding busier repositories more often. Pulls appear as a table column
  so no relationship is implied.

Note that `check_config_paths.py`'s "exported but unused" list is **not** a to-do list. Most entries
are components of a `growthcombo` pair (`models.cumulative` + `models.per_quarter` feed
`models.growth`) or forms superseded by a better one (`repositories.top_by_stars` by
`repositories.ranked`). It cannot tell those from real orphans.

### Data-quality figures, computed and kept off the site

`quality.completeness`, `quality.thin_fields`, `quality.table_sizes` and
`quality.project_repo_status` are computed on every build and charted nowhere, by decision. They are
useful internally:

* mean populated cells per table — **countries 51.8%**, organisations 62.9%, events 81.6%
* **29 fields are under 80% populated**
* 1,296 rows across 10 source tables
* **55 public repositories are linked to no project**; 2 links pair a finished project with a
  still-open repository

Five things worth fixing at source, which no chart can compensate for: the mixed units in
`Model Size`/`Environment Size` across 226 models; the three spellings of Sub-Saharan Africa in
`Focus Region`; only 7 of 384 repositories carrying GitHub topics (a cheap discoverability win);
21 of 243 models with no `Last Packaging Date`; and the 51.8%-populated `countries` table.

## Layout

```
site/
  index.html          app shell: fixed sidebar, route outlet, Methods dialog, footer
  config.js           declarative dashboard — views, charts, spans, methodology notes
  js/
    tokens.js         design tokens read from CSS at run time (no hex in JS)
    format.js         number formatting and the small-n guard
    charts.js         ECharts option builders
    cards.js          card shell: caption, ⓘ, metric toggles, drill-down table
    router.js         hash router; charts init and dispose per route
    app.js            loads stats.json, renders the landing page and each view
  styles.css          site layer over assets/ersilia.css
  assets/ersilia.css  the Ersilia house stylesheet, verbatim
  vendor/             echarts.min.js, world.geo.json — no CDN, same-origin only
  data/               built by CI, not committed: stats.json + one CSV per chart
scripts/
  collect_common.py            shared snapshot/retry/prune plumbing for the collectors
  github_api.py                shared GitHub access: inventory, batched metrics, contributors
  dockerhub_api.py             shared Docker Hub login, which lifts the pagination cap
  fetch_airtable.py            read-only Airtable -> CSV, with the identifying-column denylist
  fetch_github.py              the public inventory, commit activity, stars, contributors
  fetch_github_releases.py     every release of every model repository
  fetch_github_traffic.py      referrers and popular pages, accumulated past GitHub's 14 days
  fetch_model_packages.py      each model's pinned packages, from its install.yml
  fetch_dockerhub.py           model image pull counts
  fetch_docker_tags.py         per-architecture tags, sizes and last-pulled times
  fetch_openalex.py            citations, open access and author-institution countries, by DOI
  fetch_pypi.py                package metadata and pypistats.org's rolling download window
  convert_pypi_geo.py          manual: a BigQuery export -> data/pypi_geo/
  check_github_airtable_sync.py  fails the deploy when GitHub and Airtable disagree
  export_site_data.py          CLI: snapshots -> site/data, with the disclosure guards
  site_data/                   one module per section, plus parsing, insights and KPIs
  check_config_paths.py        fails if a chart's metric is missing, empty, or names a
                               row key that does not exist
  check_degradation.py         drops every column of every source one at a time and rebuilds:
                               a missing column must empty a card, never crash
  make_fixture.py              the synthetic snapshot the secret-free PR check builds from
  stamp_assets.py              content-hash stamps on asset URLs, so a deploy cannot
                               serve a half-updated page
  verify_site.mjs              headless smoke test: renders every route, checks rows,
                               captions and axis-label collisions
data/airtable_api_identifiers.csv   base/table id configuration
data/pypi_geo/                      PyPI downloads by country (manual BigQuery export)
data/air_tables_sample/             synthetic Airtable fixture (see make_fixture.py)
data/collected_sample/              synthetic github/dockerhub/scholar/pypi fixture
ruff.toml                           the pinned lint rule set, enforced in CI
```

## Design notes

The page follows Ersilia's house HTML standard: a single light theme, brand tokens only, quiet
sentence-case chrome, and progressive disclosure (caption → hover note → Methods dialog).
`site/assets/ersilia.css` is that standard verbatim; `site/styles.css` adds only what a dashboard
needs on top.

**Navigation carries colour; charts carry the palette.** Each sidebar entry has its own light tint,
but only in the fill behind it — the label text stays plain ink, because eight coloured words in a
column read as decoration. Charts do *not* inherit the section hue: painting a whole page one colour
made every page monochrome, which is the opposite of using a palette.

Chart colour is one global categorical set, assigned in a fixed order:

| slot | 1 | 2 | 3 | 4 | 5 | 6 |
|---|---|---|---|---|---|---|
| | periwinkle `#6d5de7` | amber `#e2a72e` | cobalt `#247dad` | lime `#6cbf5a` | orchid `#af5cc7` | crimson `#e63745` |

**Crimson is last on purpose, and that is the most important thing about this list.** It used to be
slot 2, so every two-series chart came out periwinkle-versus-red and half the dashboard read as an
alarm: "Left", "External", "Blog posts", "Featurization" and "Science" were all painted the same red
as a failure. Red carries a verdict whether or not one is meant, so it now sits where only a genuine
sixth category reaches it — and `slotColor()` stops at slot 5, so chrome can never reach it at all.
Green, amber and red are otherwise reserved for real states (a model's curation status, a project's
status) via the `semantics` mechanism.

The order is also the colour-vision safety mechanism, and it is **adjacency-sensitive**: cobalt in
slot 2 fails the normal-vision floor beside periwinkle (ΔE 14.7 — both read blue) and orchid beside
cobalt fails deuteranopia (ΔE 5.8). This order clears adjacent CVD ΔE 20.0 against a target of 8 and
normal-vision ΔE 20.6 against a floor of 15.

**These thresholds were measured with an external tool, not one in this repository.** The validator
lives in the `dataviz` Claude skill (`scripts/validate_palette.js`) and is not vendored here, so the
numbers above are the reference values to reproduce rather than something a clone can re-run. If you
change the palette and cannot run that validator, the fallback is to keep the hues and only permute
their order, then check the adjacent pairs by hand in OKLab — the gates that bite are adjacent-pair
CVD ΔE ≥ 8 and adjacent-pair normal-vision ΔE ≥ 15.

Amber and lime sit below 3:1 contrast on white; every value is labelled directly and every chart has
a table view, which is the documented relief. Text is a separate matter: `--faint` (2.96:1) is for
marks only, and anything that paints glyphs uses `--muted` (5.55:1) or `--ink` (10.98:1).

**Type and spacing come from scales, not from taste.** Six font sizes with a 12px floor
(`--fs-meta` … `--fs-hero`) and IBM Carbon's spacing scale (`--sp-1` … `--sp-7` = 2/4/8/12/16/24/32).
Before this there were nineteen font sizes, eleven of them between 8px and 14px, and 22 spacing
values of which 13 were off any 4px grid. Do not add a seventh size or an off-scale margin; if
something does not fit, show less of it.

**Chart form is deliberately varied.** An earlier version was 62% bar charts, 26 of them the
identical horizontal bar, which is why it read as a wall of purple. The horizontal bar is now a
lollipop (a dot and a hairline), three rankings on the Code page are one compact table, and ratios
that do not need a chart are meter rows. Bars are down to about a tenth of the forms. Layout is
explicit: `config.js` groups charts into rows whose spans must sum to 12, cards in a row share one
height, and the charts inside flex to fill it, so each page tessellates instead of ending in a ragged
edge.

**Where something grows, the rate and the total are drawn together** — per-period bars over a
cumulative line, two panels sharing one time axis (`growth_pair()` in `parse.py`, rendered as
`facets`). A cumulative curve only ever rises, so on its own it hides whether the rate is rising or
falling; these used to sit behind a Cumulative/Per-quarter toggle, which meant you could only ever
see one of them.

**Four Model Hub figures are derived rather than recorded**, and each states its derivation in
Methods: years from a model's publication to its incorporation; the largest input batch a model
completed (inferred from the five Computational Performance columns, where `-1` marks a failure at
that size); Docker image size; and ARM64 coverage. "Pathogens targeted" excludes `Any` and
`Homo sapiens` — both real answers, but they describe organism-agnostic chemistry and human-property
prediction, and together they would fill the ranking without saying anything about pathogen coverage.

**The Community section is about participation, not attrition.** It used to lead with a churn ledger
(joiners vs leavers vs net change, in green and red) and a cohort-retention heatmap. Both were
correct arithmetic and both were the wrong question: they framed a growing community as a leak, and
the retention grid's colour scale was set by a single 2020 member at 100%, which squashed every real
cohort into the pale end. A contributor whose collaboration ended is not a loss — most were students,
interns and fellows on fixed terms. Both charts are gone.

**Data tables open in a dialog, not in the card.** Inline, a table added its own height to one card,
which grew the grid row, which stretched every chart beside it — asking to see one chart's numbers
visibly ballooned its neighbours. Relatedly, `.chart` is `flex: 1 1 0%` and not `auto`: with `auto`
the chart's rendered height counted as its own flex basis, so ECharts resizing the canvas grew the
card, which grew the row, which grew the chart again, without bound.

Three charts are deliberately *not* what you might expect. Publications-versus-citations is two
stacked panels sharing one x axis rather than a dual-axis chart, because the scales are unrelated and
overlaying them would invent a correlation. Repository popularity uses logarithmic axes, because a
handful of repositories account for most of every metric and on linear axes the rest collapse into
the corner. Two-category splits are single split bars, not two-slice pie charts.

The stylesheet and scripts are linked same-origin files rather than inlined, which is a deliberate
departure from the house standard's inline-everything rule: that rule exists so a page survives as a
Claude Artifact under CSP, and this is a hosted site where inlining ~2 MB of chart library and world
geometry would cost real page weight for portability we do not need. Nothing loads from an
off-document host.

---

Brought to you by the [Ersilia Open Source Initiative](https://ersilia.io) — a tech-nonprofit
fueling sustainable research in the Global South.
