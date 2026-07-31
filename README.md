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
| `#/models` | The Model Hub: growth, task/subtask mix, biomedical area, curation status |
| `#/projects` | The project portfolio as a timeline — concurrency, overrun, status |
| `#/publications` | Output and accumulated citations, venue impact, African collaboration |
| `#/repositories` | Public code: popularity against activity, commit concentration, contributors |
| `#/community` | Joiners, leavers and net change; tenure; cohort retention. Aggregates only |
| `#/reach` | Where Ersilia works, and how that maps onto its Global South mission |
| `#/outreach` | Events and blog activity |
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

`.github/workflows/pages.yml` is the whole pipeline in one job — fetch → build → check → verify →
deploy. Weekly, on demand, and on pushes that touch the site or the scripts. It needs
`AIRTABLE_API_KEY` in repository secrets.

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

**Each section owns a hue**, which marks its sidebar entry *and* colours its charts, so a page reads
as itself:

| Section | Hue | Section | Hue |
|---|---|---|---|
| Model Hub | periwinkle `#6d5de7` | Community | orchid `#af5cc7` |
| Projects | turquoise `#22bbad` | Global reach | amber `#d19710` |
| Publications | plum `#734080` | Outreach | cobalt `#1c7db0` |
| Code | lime `#67bb55` | | |

Those are the brand hues snapped into the legible OKLCH band and then **assigned to the nav order by
optimisation** — in a sidebar the dots are adjacent, so neighbours have to be tellable apart. The
obvious assignment put lime beside amber, which is ΔE 5.0 under deuteranopia. This order clears
adjacent CVD ΔE 23.1 against a target of 8. **Re-run
`dataviz/scripts/validate_palette.js` over the sequence if you reorder the nav or add a section.**

Turquoise, lime and amber sit below 3:1 contrast on white; the light-ink style labels every value
directly and every chart has a table view, which is the documented relief.

**Chart form is deliberately varied.** An earlier version was 62% bar charts, 26 of them the
identical horizontal bar, which is why it read as a wall of purple. The horizontal bar is now a
lollipop (a dot and a hairline), three rankings on the Code page are one compact table, and ratios
that do not need a chart are meter rows. Bars are down to about a tenth of the forms. Card width is
derived from how many categories a metric has, not from editorial rank — a seven-category chart in a
full-width card is seven bars adrift in whitespace.

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
