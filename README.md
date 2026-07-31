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

## Deploying

`.github/workflows/pages.yml` is the whole pipeline in one job. Weekly, on demand, and on pushes that
touch the site, the scripts or `requirements.txt`. It needs `AIRTABLE_API_KEY` in repository secrets.

Each step is a gate, and everything before the upload can stop a deploy:

| Step | Fails the build when |
|---|---|
| `pip install -r requirements.txt` | — (but the pin matters: see the note in that file) |
| `fetch_airtable.py` | any table fails to fetch |
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

### A partial fetch cannot be trusted to announce itself

`fetch_airtable.py` writes what it got and prunes superseded files **before** it raises, so a table
that failed keeps its previous CSV. `load.newest_snapshots()` then takes the newest stamp *per table*,
which will happily pair today's Community with last month's Repositories. In CI this is harmless —
the job stops and the previous deployment stays live — but a local `fetch → export → commit → push`
would publish mixed-age data.

`meta.snapshot_dates` therefore records one date per table and `meta.stale_tables` names any that are
behind, which the sidebar prints next to the snapshot date. `snapshot_date` on its own is the **max**
across tables, so it always reports the freshest one and can never reveal a stale one.

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
