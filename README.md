# Ersilia in numbers

Aggregate statistics for the [Ersilia Open Source Initiative](https://ersilia.io), published as a
static site: **[Ersilia in numbers](https://ersilia-os.github.io/ersilia-stats/)**.

Ersilia's organisational data lives in Airtable — the Model Hub, projects, community, publications,
repositories, partner organisations, events, blog posts and countries. This repository holds the
pipeline that turns it into a published dashboard, and nothing else.

```
Airtable ──fetch──> data/air_tables/*.csv ──export──> site/data/ ──> GitHub Pages
           read-only, never committed              aggregate-only, committed
```

Everything is **read-only** with respect to Airtable — nothing here ever writes back.

## What is not in this repository

The registry itself. `data/air_tables/` is gitignored: the community table in raw form contains
personal data, and a public repository has no business holding a copy of the source records. The
snapshots exist only in a developer's working copy and, for the length of a deploy, in the CI runner.

What *is* committed is `site/data/` — the aggregates the page actually reads. Those are safe by
construction, so a plain clone serves the whole site with no Airtable access at all.

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

Serve what is already committed — no Airtable access needed:

```bash
python -m http.server -d site 8000     # http://localhost:8000
```

Rebuild `site/data/` from a fresh snapshot:

```bash
pip install -r requirements.txt
export AIRTABLE_API_KEY=...             # a read-only personal access token is enough
python scripts/fetch_airtable.py -t data/airtable_api_identifiers.csv -o data/air_tables/
python scripts/export_site_data.py      # data/air_tables/ -> site/data/
python scripts/check_config_paths.py    # every chart still has data behind it
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

`.github/workflows/pages.yml` is the whole pipeline in one job. Weekly, on demand, and on pushes that
touch the site, the scripts or `requirements.txt`. It needs `AIRTABLE_API_KEY` in repository secrets.

Each step is a gate, and everything before the upload can stop a deploy:

| Step | Fails the build when |
|---|---|
| `pip install -r requirements.txt` | — (but the pin matters: see the note in that file) |
| `fetch_airtable.py` | any table fails to fetch |
| `check_github_airtable_sync.py` | GitHub and Airtable disagree about which repositories exist or which are public |
| `node --check` on `config.js` and `js/*.js` | any shipped script does not parse |
| `export_site_data.py` | a PII guard trips, or an email-shaped string reaches the output |
| `check_config_paths.py --fail-on-empty` | a chart points at a missing **or empty** metric |
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

**There is still no `pull_request` trigger**, and there cannot easily be one: the build needs
`data/air_tables/`, which is gitignored, so a fork cannot build. Committing a small synthetic
fixture snapshot would unlock a secret-free PR check; that has not been done.

### Writing citations back into Airtable

The site's citation figures come from OpenAlex, but the team works in Airtable, so fixing
the site did not fix the place people look. `scripts/update_airtable_publications.py` pushes
the collected counts into the Publications table. It moved the Airtable total from 1,305 to
1,713 across 40 of 42 records.

The order is not the obvious one — collection comes first, because collection is what
produces the numbers:

```bash
export AIRTABLE_API_KEY=...                                  # needs data.records:write
PYTHONPATH=scripts python3 scripts/fetch_openalex.py -o data/scholar/
PYTHONPATH=scripts python3 scripts/update_airtable_publications.py           # read the diff
PYTHONPATH=scripts python3 scripts/update_airtable_publications.py --apply
```

Step three reads the CSV step two wrote rather than calling OpenAlex again: two calls could
return different numbers, and then Airtable and the site would disagree for a reason nobody
could explain.

**The site does not read citations from Airtable and will not start.** The writeback is for
the humans browsing the base. So a failed write cannot affect a published figure, and the
per-year accrual (199 rows) and co-author countries (a list per paper) stay in the collected
CSVs, where they fit, needing no Airtable schema at all.

Because this script can damage the source of truth it is **run by hand, never in CI**, it is
a **dry run unless given `--apply`**, and it writes exactly one field, `Citations`, from an
allow-list rather than a denylist — a denylist grows a hole every time someone adds a column.
It refuses in four situations that all look like a successful update:

| Refusal | Why |
|---|---|
| collected snapshot older than 21 days | writing stale counts over fresher ones is a regression dressed as an update |
| fewer than 80% of DOIs resolved | a half-finished collect looks exactly like "most papers lost their citations" |
| any single count falling by more than 20% or 10 citations | counts essentially only rise; a big drop means a wrong DOI, not a discovery. `--force` overrides |
| token without `data.records:write` | says which scope is missing rather than printing a traceback |

Note that switching to OpenAlex **lowers** some individual counts even though the total rises:
OpenAlex is a more conservative index than Google Scholar, which counts preprints and theses.
Seven papers went down, the largest by 10.

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

### Writing GitHub figures back into Airtable

`scripts/update_airtable_repositories.py` maintains the numeric columns of the Repositories
table. Its own description says the table "is automatically completed with a nightly cron
action"; **that cron no longer runs**, and this replaces it.

The evidence that it stopped rather than never having worked is that the columns are *almost*
right — small, recent, one-directional drift:

| Column | Agreed with live GitHub | Source |
|---|---|---|
| `Stars` | 140 / 141 | REST `stargazers_count` |
| `Subscribers` | 140 / 141 | GraphQL `watchers.totalCount` |
| `Forks` | 140 / 141 | REST `forks_count` |
| `Open Issues` | 131 / 141 | GraphQL `issues(states:OPEN)` |
| `Contributors` | 122 / 141 | REST `contributors?anon=1`, `Link` last page |
| `Total Commits` | 118 / 141 | GraphQL `history.totalCount` — drifts fastest |

Those six are the entire **allow-list**, and it is an allow-list rather than a denylist because
a denylist grows a hole every time someone adds a column. `Visibility` is never written — it is
the field the site trusts to decide what may be named. Neither are `Type`, `Status`,
`Contributor Names` (personal data), `Title`, `Description`, `Projects`, or `URL` (a formula).

It resolves private repositories **live and in memory**, because 38 of the 179 rows are private
and updating only the public ones would leave a fifth of the work undone. `data/github/*.csv`
stays public-only regardless. **Its output names private repositories, so run it locally, never
in a workflow on this repository.**

Structural drift is reported and never fixed: it never creates a record (adding a row needs a
`Type`, a judgement) and never deletes one.

```bash
export AIRTABLE_API_KEY=...      # needs data.records:write
export GH_STATS_TOKEN=...        # needs to see private repositories
PYTHONPATH=scripts python3 scripts/update_airtable_repositories.py           # read the diff
PYTHONPATH=scripts python3 scripts/update_airtable_repositories.py --apply
```

On its first real run the sharp-fall refusal earned its place: the `ersilia-stats` row claimed
310 commits and 9 contributors, but that repository is days old and has 21 commits — the row had
been seeded with figures from the *capstone* repository, a different and private repository that
really does have about 310. A guard meant to catch a broken collector caught bad stored data
instead.

### A partial fetch cannot be trusted to announce itself

`fetch_airtable.py` writes what it got and prunes superseded files **before** it raises, so a table
that failed keeps its previous CSV. `load.newest_snapshots()` then takes the newest stamp *per table*,
which will happily pair today's Community with last month's Repositories. In CI this is harmless —
the job stops and the previous deployment stays live — but a local `fetch → export → commit → push`
would publish mixed-age data.

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
  data/               generated: stats.json + one CSV per chart
scripts/
  fetch_airtable.py       read-only Airtable -> CSV, with the identifying-column denylist
  export_site_data.py     CLI: snapshots -> site/data, with the disclosure guards
  site_data/              one module per section, plus parsing, insights and KPIs
  check_config_paths.py   fails if a chart's metric is missing from stats.json
data/airtable_api_identifiers.csv   base/table id configuration
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
