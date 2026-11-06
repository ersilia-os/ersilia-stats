# Design notes and decisions

Why the dashboard looks and computes the way it does, and what was tried and rejected. Moved out of the README so the README can stay a how-it-works guide. Read this before proposing a new chart, a new colour or a new metric.

## Disclosure decisions in detail

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

One consequence worth knowing, stated on the affected card:

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

## What the legacy Streamlit app had, and what was taken from it

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

## Visual design

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
Methods: years from a model's publication to its incorporation; runtime at each input batch size (the five
Computational Performance columns, where `-1` marks a run that did not finish at that size and is
counted as infinitely slow, not dropped); Docker image size; and ARM64 coverage. "Pathogens targeted" excludes `Any` and
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
