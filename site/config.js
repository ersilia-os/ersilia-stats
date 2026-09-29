/* Declarative dashboard definition.

   One entry per view: a lead chart answering the view's primary question, then a
   handful of supporting charts. `data` is a dot path under `sections` in
   data/stats.json; `type` picks a builder in js/charts.js (or an HTML component in
   js/cards.js); `desc` is the methodology note behind the ⓘ.

   ── Two rules this file exists to enforce ────────────────────────────────────

   1. FORM VARIETY. v2 was 62% bar charts and 26 of them were the identical
      horizontal bar, which is precisely why it read as a wall of purple. Every
      section here uses a different form for each of its charts. Before adding a
      chart, check what the section already has:

        lollipop   a ranking. The default. Replaces the horizontal bar.
        column     an amount per period, on a time axis. Not for rankings.
        area       a running total over time.
        facets     two measures whose scales do not compare (never a 2nd y-axis).
        donut      part-to-whole at a glance, <= 6 segments.
        treemap    a composition where the sizes matter more than the order.
        treehierarchy a two-level hierarchy, as a nested treemap.
        heatmap    a matrix.
        histogram  a distribution.
        logscatter two measures with a long tail (linear axes would collapse it).
        categoryscatter two measures on linear axes, split into a fixed set of colour
                   categories — the categories are the point, not the tail.
        bandline   a median line with its 25th-75th percentile band, log-scale y —
                   a measure spanning orders of magnitude across a few known steps.
        lorenz     how unevenly a total is spread.
        gantt      spans in time.
        map        geography.
        shares     several two-category splits, compactly (HTML).
        meters     "how many of the whole" figures (HTML).
        ranked     a top-N table with several columns and a microbar (HTML).

   2. LAYOUT IS EXPLICIT AND COMPLETE. Charts are grouped into `rows`, and the spans
      in every row MUST sum to 12. Cards in a row stretch to one height and their
      charts flex to fill it, so the page tessellates with no gaps and no ragged
      edges — which is what makes it read as a dashboard rather than a pile of
      cards. `h` sets the row height. Pick spans from the shape of the data: a time
      series wants width, a ranking wants height, a ratio wants very little.

   A view is either `rows` directly, or `groups`: topic sections, each `{ title,
   blurb?, rows }`, rendered with a heading before its rows. Use `groups` once a
   view mixes sources or subjects that answer different questions — Model Hub
   licensing, Docker distribution and GitHub activity are three such subjects, and
   a chart from one must never share a row, let alone a card, with a chart from
   another. `rows` alone is still fine for a view with one coherent subject.

   Colour: the chrome is neutral and the palette belongs to the marks. A one-series
   chart takes the single accent; anything categorical takes the palette in order.
   Nothing here needs to name a colour. */

/* `slot` picks a palette slot for the tile's sparkline, so the headline row is
   polychrome. Chrome elsewhere stays neutral. */
const PRIMARY_KPIS = [
  { key: "models", label: "Models in the Hub", slot: 0 },
  { key: "community_members", label: "People involved", slot: 2 },
  { key: "repositories", label: "Repositories", slot: 3 },
  { key: "total_citations", label: "Citations", slot: 4 },
];

// Shown when the Models table has not been fetched yet, so the hero row still has
// four tiles rather than a gap.
const PRIMARY_KPIS_FALLBACK = [
  { key: "community_members", label: "People involved", slot: 0 },
  { key: "repositories", label: "Repositories", slot: 2 },
  { key: "publications", label: "Publications", slot: 3 },
  { key: "total_citations", label: "Citations", slot: 4 },
];

const SECONDARY_KPIS = [
  { key: "projects", label: "Projects" },
  { key: "publications", label: "Publications" },
  { key: "organisations", label: "Partner organisations" },
  { key: "countries_represented", label: "Countries with people or events" },
  { key: "total_stars", label: "GitHub stars" },
  { key: "events", label: "Events" },
  { key: "blogposts", label: "Blog posts" },
  { key: "pypi_downloads", label: "PyPI downloads (recent window)" },
];

const VIEWS = [
  {
    id: "models",
    title: "Model Hub",
    blurb: "What is in the Ersilia Model Hub, what it is for, and how much of it is ready to run.",
    links: [
      { label: "Browse the catalogue", href: "https://catalog.ersilia.io" },
      { label: "Model Hub", href: "https://ersilia.io/model-hub" },
    ],
    headlineKpi: "models",
    groups: [
      {
        title: "Growth and composition",
        blurb: "What is in the Hub, and how it has grown.",
        rows: [
          { h: "h-xl", cells: [
            {
              title: "Models added over time", span: 12, data: "models.growth", type: "growthcombo",
              desc: "Models by the quarter they were incorporated: the top panel is how many were added in each quarter, the lower one the running total. Both are drawn together because a cumulative curve only ever goes up and so hides whether the rate is rising or falling.",
            },
          ] },
          { h: "h-lg", cells: [
            {
              title: "What the models do", span: 7, data: "models.task_tree", type: "treehierarchy",
              desc: "Outer blocks are the model's task, inner ones its subtask. Both are single-valued, so every model sits in exactly one block and the areas sum to the model count.",
            },
            {
              title: "Pathogens targeted", span: 5, data: "models.by_target_organism", type: "lollipop",
              desc: "Models that act on a named organism. 'Any' and 'Homo sapiens' are excluded on purpose: both are real answers but they describe organism-agnostic chemistry and human-property prediction respectively, and together they would fill the ranking without saying anything about pathogen coverage.",
            },
          ] },
          { h: "h-lg", cells: [
            {
              title: "Biomedical area", span: 5, data: "models.by_biomedical_area", type: "lollipop",
              desc: "What each model is for. Ersilia works on antimicrobial and antipathogen drug discovery, and this says how much of the Hub serves a named disease versus general-purpose chemistry. A multi-select, so a model spanning two areas counts in both.",
            },
            {
              title: "Curation status", span: 4, data: "models.by_status", type: "donut",
              desc: "Every model by curation status. Colours follow the house status scale, so 'ready' is the same green wherever it appears.",
            },
            {
              title: "Same answer twice?", span: 3, data: "models.output_consistency", type: "donut",
              desc: "Whether a model returns the same output for the same input on a re-run, as recorded in the registry. This is arguably the most consequential property on this page and it was previously shown nowhere: everything else here says what a model is for, this says whether you can rely on what it tells you. Variable is not a defect — a generative model that samples is supposed to vary — so no verdict is attached to it; for a property predictor the same value would be a problem. Ten models record no value and are excluded from the share.",
            },
          ] },
          { h: "h-lg", cells: [
            {
              title: "Coverage: task × biomedical area", span: 12, data: "models.task_by_area", type: "heatmap",
              desc: "The task and biomedical-area charts above, crossed — which task types actually serve which diseases. Task is single-valued, so every model with one recorded lands in exactly one row; biomedical area is multi-select, so a model naming two areas is counted in both columns it touches. Capped to the 8 largest task families and 10 largest areas so the matrix stays legible.",
            },
          ] },
        ],
      },
      {
        title: "Origins and licensing",
        blurb: "Where each model's science came from, and the terms it and its wrapper carry.",
        rows: [
          { h: "h-md", cells: [
            {
              title: "Years from paper to Hub", span: 4, data: "models.publication_lag", type: "histogram",
              desc: "Incorporation year minus the model's original publication year — how quickly the Hub tracks the literature. Rows where incorporation precedes publication are dropped, since a negative lag means one of the two dates is wrong.",
            },
            {
              title: "Is the science peer-reviewed?", span: 4, data: "models.publication_type",
              type: "lollipop",
              desc: "The publication type of the work each model is based on. Provenance rather than popularity, and the counterpart to the wrapped-work figure ('Wraps external work') beside it: that says whether Ersilia packaged somebody else's model, this says how well established that model's science is. Preprints are counted separately from peer-reviewed work rather than folded in with it.",
            },
            {
              title: "Wraps external work", span: 4, type: "shares",
              blurb: "Packages an external model, or Ersilia's own?",
              sources: [
                { label: "Wraps external work", data: "models.by_source_type", highlight: "External" },
              ],
              desc: "Whether each model packages an externally published model rather than one built by Ersilia's own team.",
            },
          ] },
          { h: "h-md", cells: [
            {
              title: "Licences of the underlying models", span: 8, data: "models.by_license",
              type: "treemap",
              desc: "The licence of each wrapped model as recorded in the registry — NOT the licence of Ersilia's wrapper repository, which is GPL-3.0 on 227 of 241 model repositories and is shown on the Code page. The two answer different questions and genuinely differ: the upstream models spread across MIT, both GPL-3.0 variants, Apache-2.0 and BSD-3-Clause, and it is the upstream terms that govern what a reuser may do with the underlying science. 40 models record no licence, which for a reuser is the most restrictive state of all.",
            },
            {
              title: "Permissively licensed", span: 4, type: "shares",
              blurb: "Permissive licence share, of models that record one.",
              sources: [
                { label: "Permissively licensed", data: "models.licence_openness", highlight: "Permissive" },
              ],
              desc: "How much of the Hub carries a permissive licence — MIT, Apache, BSD or CC0/CC-BY — as against a licence that imposes conditions, which covers GPL, AGPL, LGPL, proprietary and the non-commercial or no-derivatives Creative Commons variants. The share is of the models that record a licence at all; 40 record none, which for a reuser is the most restrictive state of all.",
            },
          ] },
        ],
      },
      {
        title: "Where and how models run",
        blurb: "Distribution and runtime: where models can run, pull demand per image, and computational performance at scale.",
        rows: [
          { h: "h-md", cells: [
            {
              title: "Where models can be run", span: 6, data: "models.coverage", type: "meters",
              desc: "How many models have each distribution route on file — a Docker image, an S3 bundle, or source code. Presence of a value is the signal: an empty DockerHub cell means the model was never pushed there.",
            },
            {
              title: "Median pulls by architecture", span: 6, data: "usage.pulls_by_arch",
              type: "lollipop",
              desc: "Median Docker Hub pull count for images that also build for ARM64 — the cheap, low-power hardware — against images that only build for AMD64, joined on the model registry's Docker Architecture field. Everything else on this page counts images and pulls separately; this is the one chart asking whether the two interact, or whether ARM64 support is as invisible in the pull counts as it is in most Docker Hub browsing. A pull count is a running total with no history: mirrors and repeat CI builds inflate it, so this is a floor on interest, not a headcount.",
            },
          ] },
          { h: "h-lg", cells: [
            {
              title: "Computational performance", span: 12, data: "models.performance_by_scale",
              type: "bandline",
              desc: "Median runtime as the batch size grows tenfold at each step, with the 25th-75th percentile band — the same plot as entry_project's Engineering tab, redrawn here. The runtime axis is log scale because the measure spans orders of magnitude: a model taking fractions of a second on one input can take minutes on ten thousand. A value of -1 in the underlying Computational Performance column means the model FAILED at that size rather than ran instantly, so failed runs are excluded from the runtime figures rather than pulling the median toward zero — which is also why fewer models are represented at the larger batch sizes; the drill-down table has the count benchmarked at each one. Replaces the single-number \"largest batch reached\" chart with the runtime curve behind it.",
            },
          ] },
          { h: "h-lg", cells: [
            {
              title: "When images were last built", span: 7, data: "model_activity.image_freshness",
              type: "column",
              desc: "The year each model's Docker image was last pushed. This is BUILD recency and not maintenance or demand: the pull-count evidence elsewhere on this page shows that continuous integration pulls every image on a schedule, and that same schedule is what rebuilds them. Read together with 'Are models still maintained?' in the development-activity section below: the two can disagree, and the disagreement is the useful part — a model whose repository changed this year but whose image is a year old has a packaging problem that neither figure reveals alone.",
            },
            {
              title: "Models with a published image", span: 5, data: "usage.image_coverage",
              type: "donut",
              desc: "Whether each model in the registry has a matching Docker image on Docker Hub. A model with no image cannot be run by the usual route, so this is a completeness check on the Hub rather than a popularity measure. The mismatch runs both ways and both directions are worth knowing: a handful of published images have no model record at all, which means they are undocumented rather than missing. Infrastructure images — base, conda, shell — are excluded from every figure here: they are pulled as a side effect of running a model rather than chosen, and base alone would inflate the total by roughly 14%.",
            },
          ] },
          { h: "h-md", cells: [
            {
              title: "How heavy is a model?", span: 7, data: "models.image_size", type: "histogram",
              desc: "Docker image size, as recorded in the registry — the low-resource deployment question. A dashed rule marks the mean. Heavier images cost more to pull on slow or metered connections, which matters directly for the low-bandwidth settings the Hub targets.",
            },
            {
              title: "ARM64 support", span: 5, type: "shares",
              blurb: "Of models that record an architecture, how many also build for ARM64?",
              sources: [
                { label: "Also builds for ARM64", data: "models.on_arm", highlight: "ARM64 and AMD64" },
              ],
              desc: "Every model records an AMD64 build; this is whether it also publishes an ARM64 one — the cheap, low-power hardware. 'Median pulls by architecture', to the left, asks whether that support actually gets pulled more.",
            },
          ] },
          { h: "h-lg", cells: [
            {
              title: "Docker image composition", span: 12, data: "models.image_composition", type: "stackbar",
              desc: "Checkpoint weights vs. installed environment vs. everything else, for the models that record all three sizes — a packaging-efficiency question the size histogram above doesn't break down. The heaviest images by total size, so the worst bloat candidates surface first. All three sizes come from the same registry fields, in the same unit, so no conversion happens here.",
            },
          ] },
        ],
      },
      {
        title: "Docker Hub demand",
        blurb: "Pull counts from Docker Hub — a floor on interest, not a headcount.",
        rows: [
          { h: "h-md", cells: [
            {
              title: "How Docker pulls are distributed", span: 12,
              data: "usage.pull_distribution", type: "ordinallollipop",
              desc: "Every model image, bucketed by lifetime Docker Hub pull count. This is the chart the rest of the page's caveats are about, shown directly rather than left as an assertion: 224 of 247 models sit inside one narrow 2.5k–5k band, with almost nothing above or below it. Real human demand does not cluster like that — it follows a power law, the same shape as this organisation's GitHub stars (306, 92, 45, 35, 13…). A near-uniform floor of about four thousand pulls on almost every model is the signature of something pulling every image on a schedule, most likely Ersilia's own continuous integration — which is why the total pull count is never read as a demand figure anywhere on this page.",
            },
          ] },
          { h: "h-lg", cells: [
            {
              title: "Most pulled models", span: 12, data: "usage.most_pulled_models",
              type: "ranked", nameLabel: "Model", top: 10,
              columns: [
                { key: "pulls", label: "Pulls" },
                { key: "times_baseline", label: "× baseline", raw: true },
              ],
              desc: "Docker Hub pull counts, ranked by how far each model exceeds the automated baseline rather than by raw pulls — ranking by raw pulls would rank the build schedule. Only models clearly above the baseline appear. A pull is not a user: mirrors pull images, and one person testing in a loop pulls repeatedly. It is a floor on interest, not a headcount, and Docker Hub publishes no history, so these are totals to date and cannot be turned into a rate.",
            },
          ] },
          { h: "h-xl", cells: [
            {
              title: "Image size vs. pulls, by architecture support", span: 12,
              data: "usage.size_vs_pulls", type: "categoryscatter",
              scatter: {
                x: "size", y: "pulls", category: "category", xUnit: "GB",
                xLabel: "Docker image size (GB)", yLabel: "Docker pulls",
                categories: [
                  { key: "ARM64 and AMD64", label: "AMD64 + ARM64" },
                  { key: "AMD64 only", label: "AMD64 only" },
                ],
              },
              desc: "One dot per model image: Docker image size against Docker Hub pulls, coloured by whether the image also builds for ARM64 — the cheap, low-power hardware. Both axes are linear, unlike the other scatter on this page: pulls have a long tail organisation-wide, but within model images the range is narrow enough that a log axis would only compress it. No causal claim is made either way — 'Most pulled models' above and the module note on this page both explain why the pull baseline is continuous integration rather than demand.",
            },
          ] },
          { h: "h-md", cells: [
            {
              title: "Time since last pull", span: 7, data: "usage.pull_dormancy",
              type: "ordinallollipop",
              desc: "Every model image, by how long ago it was last pulled on ANY tag or architecture — Docker Hub's lifetime pull count never goes down, so an image abandoned a year ago and one pulled this morning look identical in it; this is the part that decays. From a separate collector (fetch_docker_tags.py) that reads the per-tag endpoint rather than the repository summary, one request per model.",
            },
            {
              title: "ARM64 vs. AMD64 image size", span: 5, data: "usage.arm_vs_amd_size",
              type: "categoryscatter",
              scatter: {
                x: "amd64", y: "arm64", xUnit: "GB", yUnit: "GB",
                xLabel: "AMD64 size (GB)", yLabel: "ARM64 size (GB)",
              },
              desc: "The newest AMD64 build's size against the newest ARM64 build's size, for models that publish both — points below the diagonal implied by matching axes are lighter on ARM, usually a leaner base image with no x86-only CUDA/MKL wheels pulled in. Linear axes: unlike Docker pulls elsewhere on this page, image size does not span orders of magnitude, so a log axis would only make the cluster harder to read.",
            },
          ] },
          { h: "h-md", cells: [
            {
              title: "Last pull, by day of the week", span: 6,
              data: "usage.pull_rhythm_weekday", type: "ordinallollipop",
              desc: "Every image's most recent pull, by the UTC day of the week it landed on. Scheduled automation is flat across the week; human work collapses at the weekend — so a real weekend dip is evidence some of this traffic is not a machine. One recency-biased sample per digest, not a volume: Docker Hub exposes only the most recent pull per digest, never a series.",
            },
            {
              title: "Last pull, by hour (UTC)", span: 6,
              data: "usage.pull_rhythm_hour", type: "column",
              desc: "The same last-pull timestamps as the weekday chart beside it, by hour of day instead. Suggestive of a rhythm, not a measurement of volume, for the same reason: one sample per digest.",
            },
          ] },
        ],
      },
      {
        title: "Development activity",
        blurb: "Commits, maintenance and outside contribution, from GitHub.",
        rows: [
          { h: "h-lg", cells: [
            {
              title: "Work on the Hub, by quarter", span: 6, data: "model_activity.hub_commit_growth",
              type: "growthcombo",
              desc: "Commits to the per-model repositories only, by calendar quarter, with the running total. Separate from the organisation-wide series on the Code page because it answers a different question: how much work goes into the Hub itself as against Ersilia's tooling. Both come from the same collection pass, filtered differently. The current quarter is partial.",
            },
            {
              title: "Are models still maintained?", span: 3, data: "model_activity.maintenance",
              type: "ordinallollipop",
              desc: "Each model repository by the year of its last push, with archived ones counted separately. This exists to answer the fair question a sceptic asks of any large model collection — is most of it abandoned? Archived repositories are a deliberate retirement rather than neglect, which is why they are not folded into the oldest year.",
            },
            {
              title: "Models with an outside contribution", span: 3,
              data: "model_activity.outside_contribution", type: "donut",
              desc: "Counted per model, not per pull request, and that is the point: '78% of merged pull requests come from outside Ersilia' could in principle be a handful of models attracting all the outside work. This counts the models themselves, so it measures how far community contribution actually reaches into the Hub. Only the most recent 30 merged pull requests per repository are sampled, so a model whose only outside contribution is older reads as internal — the figure is a floor, not a ceiling.",
            },
          ] },
          { h: "h-lg", cells: [
            {
              title: "Busiest model repositories", span: 12, data: "model_activity.most_active_models",
              type: "ranked", nameLabel: "Model", nameKey: "title", top: 10,
              columns: [
                { key: "total_commits", label: "Commits" },
                { key: "merged_prs", label: "PRs" },
                { key: "closed_issues", label: "Issues" },
                { key: "pulls", label: "Pulls" },
              ],
              desc: "The three sources on one row: commits, pull requests and issues from GitHub, pull counts from Docker Hub, joined on the shared eosXXXX identifier — 237 of 243 models resolve in all three. Ranked by commits. Pulls are a column rather than a ranking deliberately: they correlate with commits at Spearman 0.52, but that almost certainly measures continuous integration rebuilding busier repositories more often rather than anyone choosing them, so no relationship is implied here.",
            },
          ] },
          { h: "h-lg", cells: [
            {
              title: "Who gets credited for incorporating a model", span: 7,
              data: "models.top_contributors", type: "lollipop",
              desc: "The registry's `Contributor` field, by how many models each person is credited with — a public GitHub handle, the same kind of identifier already published for commit authorship on the Code page. Multi-select, so a model credited to two people counts for both.",
            },
            {
              title: "Contributor concentration (models incorporated)", span: 5,
              data: "models.contributor_concentration", type: "lorenz",
              desc: "Lorenz curve of models incorporated per contributor — the bus-factor question for the Hub's own incorporation work, alongside the Code page's equivalent for commits. X is the cumulative share of contributors, least active first; Y is the cumulative share of models. A curve hugging the bottom-right means a handful of people have done almost all of the incorporation.",
            },
          ] },
        ],
      },
      {
        title: "Versioning",
        blurb: "Version history per model, from GitHub Releases — whether a model is a file drop or something actively maintained past its first v1.0.0. Every chart on this page is restricted to the Hub's currently active models: registry status Ready or In maintenance, on a repository that has not been archived. An archived repository's release history describes work that has stopped, not the Hub's current versioning discipline, and a model still In progress has not settled into a release rhythm yet.",
        rows: [
          { h: "h-lg", cells: [
            {
              title: "How models get updated", span: 5, data: "releases.bump_types",
              type: "donut",
              desc: "The semver bump type of every release after a model's first — major, minor or patch — hub-wide. The first release of each repo is excluded: it is not a bump from anything, and counting it would dilute the read on ongoing maintenance with releases that only ever happened once.",
            },
            {
              title: "Model releases over time, hub-wide", span: 7, data: "releases.growth",
              type: "growthcombo",
              desc: "Every model release, by the quarter it was published, with the running total. The Code page's 'When each repository last released' shows only the most recent release per repository; this counts every one, so a model re-packaged five times counts five times.",
            },
          ] },
          { h: "h-md", cells: [
            {
              title: "Time between a model's releases", span: 7, data: "releases.cadence",
              type: "ordinallollipop",
              desc: "The gap between one GitHub Release and the next, for the same model — not whether a model gets re-released (the chart to the left answers that), but how often. Only gaps between two releases of the same repository count; a repo's first release has nothing before it to measure a gap against, so it is excluded rather than counted as zero or infinite.",
            },
            {
              title: "Has a semver-tagged Docker image", span: 5, type: "shares",
              blurb: "Docker Hub tags include a proper version, not just dev, rolling or dated ones.",
              sources: [
                { label: "Has a semver-tagged image", data: "usage.tag_versioning", highlight: "Has a semver-tagged image" },
              ],
              desc: "The Docker Hub counterpart to 'Past v1.0.0?' on the release-history table below — whether a model's published tags include at least one proper semver version, rather than only dev, rolling ('latest') or dated-snapshot tags. The two can disagree: a GitHub release does not by itself republish the image under a matching Docker tag, and a repository can be re-tagged on Docker Hub with no GitHub release to go with it.",
            },
          ] },
          { h: "h-lg", cells: [
            {
              title: "Biggest size swings, first build to latest", span: 12,
              data: "usage.size_swings",
              type: "ranked", nameLabel: "Model", top: 12,
              columns: [
                { key: "swing_abs", label: "Swing (GB)" },
                { key: "direction", label: "Direction", raw: true },
                { key: "first_size", label: "First build (GB)", raw: true },
                { key: "latest_size", label: "Latest build (GB)", raw: true },
              ],
              desc: "Docker image size, a model's FIRST recorded build against its LATEST — not how big a model is today (the size histogram elsewhere on this page answers that), but how much it has changed. AMD64 only, so architecture is never conflated with the swing itself. Repositories with only one recorded build are excluded: there is nothing to swing against. Ranked by the size of the swing in either direction, so a model that quietly shed several gigabytes of bloat surfaces here exactly as readily as one that grew.",
            },
          ] },
          { h: "h-lg", cells: [
            {
              title: "Most common packages in the most-pulled models", span: 6,
              data: "packages.most_pulled_common", type: "lollipop",
              desc: "Of the 25 most-pulled models on Docker Hub, the packages installed most often — from install.yml, the model template's own pinned install list. What the models people actually run are built on; read it beside the heavy-model chart next to it, where a package that leads there but not here is weight few users pay for. ersilia-pack-utils, the model template's own packaging dependency, is left out of both. Ranked on lifetime pulls, which include CI rebuilds as well as people, and restricted to the Hub's currently active models that have an install.yml before the top 25 are taken, so a legacy-template model with no install.yml never takes a slot. Counted per model, not per install.yml line, and suppressed below 10 qualifying models.",
            },
            {
              title: "Most common packages in heavy models", span: 6,
              data: "packages.heaviest_common", type: "lollipop",
              desc: "Of the models whose Docker image is at least 3GB, the packages installed most often — from install.yml, the model template's own pinned install list, joined on the same AMD64 image size reading as the size-swing table above. Not which packages exist hub-wide: a package that is near-universal says little by appearing here, so read this beside 'How heavy is a model?' rather than alone. ersilia-pack-utils is left out: it is the model template's own packaging dependency, installed in almost every model rather than chosen for one. Counted per model, not per install.yml line, so a package listed twice for one repository cannot inflate its own count. Restricted to the Hub's currently active models, same as the rest of this section, and suppressed entirely below 10 qualifying models — the same floor the rest of the site applies to a share. The count beside each chart title is a floor on coverage, not a census: a repository whose install.yml could not be fetched is absent from it rather than assumed light.",
            },
          ] },
          { h: "h-lg", cells: [
            {
              title: "Most actively versioned models", span: 12, data: "releases.most_versioned",
              type: "lollipop",
              desc: "Models ranked by how many GitHub Releases they carry — updated most often since their first v1.0.0. Not the same ranking as commits or pulls: a model can be re-packaged repeatedly with small patch bumps and lead here while sitting well down those other rankings.",
            },
          ] },
          { h: "h-lg", cells: [
            {
              title: "Release history, model by model", span: 12, data: "releases.summary",
              type: "ranked", nameLabel: "Model", nameKey: "title", top: 12,
              columns: [
                { key: "num_releases", label: "Releases" },
                { key: "latest_tag", label: "Latest tag", raw: true },
                { key: "progressed", label: "Past v1.0.0?", raw: true },
              ],
              desc: "Every model with release history, ranked by release count, with its most recent tag. 'Past v1.0.0?' is 'Yes' for any model with two or more releases — updated at least once since it was first incorporated.",
            },
          ] },
        ],
      },
      {
        title: "Community requests",
        blurb: "How often people ask Ersilia to add a model, and how quickly those requests get answered — from the flagship repository's issue tracker, independent of which models exist yet.",
        rows: [
          { h: "h-lg", cells: [
            {
              title: "Requests to add a model, over time", span: 7,
              data: "model_activity.requests_growth", type: "growthcombo",
              desc: "Every GitHub issue labelled a model request on the flagship ersilia repository, by the quarter it was opened, with the running total. Counted at OPEN rather than at close, so this measures how much the community is asking for — the chart beside it, 'How long a model request takes to close', answers the separate question of how fast Ersilia keeps up.",
            },
            {
              title: "How long a model request takes to close", span: 5,
              data: "model_activity.request_lead_time", type: "ordinallollipop",
              desc: "Days from a model-request issue opening to closing, for closed requests only — an open request has no lead time yet, so it is excluded rather than counted as zero. Bucketed because lead times run from hours to years: a linear scale would flatten the whole picture into one bar near zero.",
            },
          ] },
        ],
      },
      {
        title: "Coverage gaps",
        blurb: "Where the registry, GitHub and Docker Hub disagree with each other — three ways the Hub can quietly drift out of sync with itself.",
        rows: [
          { h: "h-lg", cells: [
            {
              title: "Models without a published Docker image", span: 6,
              data: "model_activity.missing_docker_image",
              type: "ranked", nameLabel: "Model", nameKey: "title", top: 12,
              columns: [
                { key: "status", label: "Status", raw: true },
                { key: "contributor", label: "Contributor", raw: true },
                { key: "incorporation_date", label: "Incorporated", raw: true },
              ],
              desc: "Real model repositories in the GitHub org with no matching Docker Hub image — incorporated but not yet packaged and published, or a packaging step that broke. Most recently incorporated first: the same gap on a years-old model is the more surprising finding.",
            },
            {
              title: "Docker images with no matching GitHub repo", span: 6,
              data: "model_activity.orphaned_docker_images",
              type: "ranked", nameLabel: "Image", nameKey: "title", top: 12,
              columns: [
                { key: "pull_count", label: "Pulls" },
                { key: "last_updated", label: "Last updated", raw: true },
                { key: "description", label: "Description", raw: true },
              ],
              desc: "On Docker Hub, with real pull counts, but no repository left in the ersilia-os GitHub org — the repo was likely renamed, moved or deleted after the image was pushed, orphaning it. Ranked by pulls, so the images anyone might still be depending on surface first.",
            },
          ] },
          { h: "h-lg", cells: [
            {
              title: "In progress / in maintenance", span: 12,
              data: "model_activity.in_flight",
              type: "ranked", nameLabel: "Model", nameKey: "title", top: 12,
              columns: [
                { key: "status", label: "Status", raw: true },
                { key: "contributor", label: "Contributor", raw: true },
                { key: "incorporation_date", label: "Incorporated", raw: true },
              ],
              desc: "Every model whose own metadata records status In progress or In maintenance — not yet Ready, or Ready and now being revisited. From the registry alone, so this is independent of whether GitHub or Docker Hub data resolves for that model at all.",
            },
          ] },
        ],
      },
    ],
  },
  {
    id: "projects",
    title: "Projects",
    blurb: "The project portfolio — what ran when, what overlapped, and what is still open.",
    links: [{ label: "Our work", href: "https://ersilia.io/work" }],
    headlineKpi: "projects",
    rows: [
      { h: "h-tall", cells: [
        {
          title: "Project timeline", span: 12, data: "projects.timeline", type: "gantt",
          desc: "One bar per project from start to end date, coloured by status, against a 'today' rule. Projects with no end date are drawn to today and marked open.",
        },
      ] },
      { h: "h-xl", cells: [
        {
          title: "Projects started over time", span: 12, data: "projects.growth", type: "growthcombo",
          desc: "Projects by the year they started: new starts on top, the running total below. The Gantt above says when each ran; this says whether the portfolio is still growing.",
        },
      ] },
      { h: "h-lg", cells: [
        {
          title: "What each project produced", span: 7, data: "projects.outputs",
          type: "ranked", nameLabel: "Project", top: 10,
          columns: [
            { key: "repositories", label: "Repos" },
            { key: "public", label: "Public" },
            { key: "publications", label: "Papers" },
          ],
          desc: "Repositories and publications linked to each project, from the Airtable link columns. Repository counts cover public and private alike — a count is not disclosure — and the public column says how many can be named; no private repository name is ever resolved. Projects with neither are omitted.",
        },
        {
          title: "Repository coverage", span: 5, type: "shares",
          blurb: "How much of the code is tied to a project.",
          sources: [
            { label: "Repositories linked to a project", data: "quality.repo_project_link", highlight: "Linked" },
            { label: "Projects with an output recorded", data: "projects.has_outputs", highlight: "With an output" },
          ],
          desc: "Public repositories that are linked to a project against those that are not. An unlinked repository is not wrong — plenty of tooling stands on its own — but it does mean the portfolio view cannot see it.",
        },
      ] },
      { h: "h-md", cells: [
        {
          title: "Running at the same time", span: 5, data: "projects.active_over_time", type: "area",
          desc: "Projects started and not yet ended, counted in each quarter. The peak is how much was in flight at once.",
        },
        {
          title: "Status", span: 4, data: "projects.status", type: "donut",
          desc: "Every project by current status, on the same colour scale as the timeline above.",
        },
        {
          title: "Median run length", span: 3, data: "projects.duration", type: "meters",
          desc: "Median months per project, split between finished projects and those still running. Running projects are measured to today, so their figure is a floor.",
        },
      ] },
    ],
  },
  {
    id: "publications",
    title: "Publications",
    blurb: "Peer-reviewed papers and preprints carrying an Ersilia affiliation, and how far " +
           "they reach. Every figure here covers those 25 papers only. The team has 17 more " +
           "tracked here without an Ersilia affiliation \u2014 earlier work, holding more " +
           "citations than the affiliated set \u2014 and they are shown in their own right at " +
           "the foot of the page rather than folded into totals labelled Ersilia.",
    links: [{ label: "Publications", href: "https://ersilia.io/publications" }],
    headlineKpi: "publications",
    rows: [
      { h: "h-lg", cells: [
        {
          title: "Publications over time", span: 7, data: "publications.growth", type: "growthcombo",
          desc: "Ersilia-affiliated papers and preprints by year of publication: bars for the year, a line for the running total. The bars can be hidden from the legend to read the total on its own. Unaffiliated work by the team is excluded here and shown at the foot of the page.",
        },
        {
          title: "How the work is framed", span: 5, type: "shares",
          blurb: "Three splits that say what kind of body of work this is.",
          sources: [
            { label: "Direct Ersilia affiliation", data: "publications.affiliation", highlight: "Yes" },
            { label: "African collaboration", data: "publications.by_african_collab", highlight: "Yes" },
            { label: "Primary research", data: "publications.by_type", highlight: "Research" },
          ],
          desc: "Three splits that say what kind of body of work this is. The affiliation share is computed over ALL tracked papers, since it is the figure that describes the split itself \u2014 unlike every other number on this page, which covers the affiliated papers only. African collaboration is recorded on some papers only; that share is of those where it is recorded.",
        },
      ] },
      { h: "h-lg", cells: [
        {
          title: "Citations accumulated", span: 7, data: "publications.citation_accrual",
          type: "growthcombo",
          desc: "Citations by the year each citation was MADE, from OpenAlex — real accrual, not citations attributed to their paper's publication year. That distinction used to require a caveat here, because the previous source only recorded the paper's year and made recent years look artificially thin. Kept separate from the publication count above rather than sharing a plot with it: publications and citations are different measures, and two different measures on two axes is what invites a reader to see a relationship the data does not assert.",
        },
        {
          title: "Highest-impact venues", span: 5, data: "publications.top_journals", type: "lollipop",
          desc: "Mean citations per Ersilia article, for venues with at least two Ersilia articles. The two-article floor stops one lucky paper topping the ranking.",
        },
      ] },
      { h: "h-md", cells: [
        {
          title: "Research topics", span: 4, data: "publications.by_topic", type: "lollipop",
          desc: "Publications grouped by research topic. A multi-select, so a paper spanning two topics counts in both.",
        },
        {
          title: "Ersilia-affiliated against external, per year", span: 8,
          data: "publications.affiliation_by_year", type: "stackbar",
          desc: "All tracked publications per year, split by whether they carry a direct Ersilia affiliation. One of the two charts on this page deliberately covering the whole set rather than the affiliated subset, because its subject IS the split \u2014 it shows how much of the team\u2019s recorded output is Ersilia work and how that has changed.",
        },
      ] },
      { h: "h-lg", cells: [
        {
          title: "Who can read it", span: 4, type: "shares",
          blurb: "Whether the work is behind a paywall.",
          sources: [
            { label: "Open access", data: "publications.open_access", highlight: "Open access" },
            { label: "Direct Ersilia affiliation", data: "publications.affiliation", highlight: "Yes" },
          ],
          desc: "Whether each paper can be read without a subscription, classified by OpenAlex. This is a mission figure rather than a vanity one: an organisation whose purpose is to serve researchers in low-resource settings has a direct interest in whether its own output is reachable by them. The routes are not equivalent — gold means published open, while bronze is readable at the publisher's discretion and can be withdrawn — and the breakdown is in the table.",
        },
        {
          title: "Routes to open access", span: 4, data: "publications.oa_routes", type: "lollipop",
          desc: "How the open papers are open. Gold is published open access; green is a repository copy; hybrid is an open article in a subscription journal; bronze is free to read at the publisher's discretion and can be withdrawn without notice.",
        },
        {
          title: "How many countries per paper", span: 4,
          data: "publications.collaboration_breadth", type: "histogram",
          desc: "Each paper by the number of distinct countries its author institutions span. This answers a different question from the country ranking below, and the difference matters: a long country list can come from one fourteen-partner consortium paper, which would read as broad collaboration across the whole body of work when it was a single paper. Papers with no recorded institution are excluded rather than counted as one country.",
        },
      ] },
      { h: "h-md", cells: [
        {
          title: "Where co-authors are based", span: 12,
          data: "publications.collaboration_countries", type: "lollipop",
          desc: "Countries of the author institutions across all papers, from OpenAlex. This measures international collaboration instead of asserting it: the publications table also carries a hand-set African-collaboration flag, and this counts the institutions, so South Africa, Cameroon and Mozambique appear as themselves. Institution countries only — no author names are collected or published.",
        },
      ] },
      { h: "h-lg", cells: [
        {
          title: "Most cited publications", span: 12, data: "publications.most_cited",
          type: "ranked", nameLabel: "Title", nameKey: "title", top: 10,
          columns: [
            { key: "citations", label: "Citations" },
            { key: "year", label: "Year", raw: true },
            { key: "ersilia", label: "Ersilia", raw: true },
          ],
          desc: "Ersilia-affiliated papers ranked by citation count. Ranked over everything tracked instead, the top four would all be unaffiliated — 420, 132, 101 and 69 citations, the team's earlier careers — against 115 for the most-cited affiliated paper, so a bare ranking under an Ersilia heading would claim credit the data does not support. Those papers are not dropped silently: they are the card below. Titles, journals and years are public bibliographic facts; no author names are published.",
        },
      ] },
      { h: "h-lg", cells: [
        {
          title: "Other relevant work by the team, outside Ersilia", span: 12,
          data: "publications.external_work", type: "ranked", nameLabel: "Title",
          nameKey: "title", top: 10,
          columns: [
            { key: "citations", label: "Citations" },
            { key: "year", label: "Year", raw: true },
            { key: "journal", label: "Journal", raw: true },
          ],
          desc: "Research by people who founded or joined Ersilia, carrying no Ersilia affiliation — mostly earlier in their careers, and closely related in subject. This card exists so that the filtering applied to the rest of the page is visible rather than silent: these 17 papers hold more citations between them than the 25 affiliated ones, and the most-cited has 420 against 115. Excluding them from figures labelled Ersilia is the only way those figures can describe Ersilia; excluding them from the page altogether would hide both the work and the choice.",
        },
      ] },
    ],
  },
  {
    id: "repositories",
    title: "Code",
    blurb: "Ersilia's open-source repositories, and what is actually happening inside them. " +
           "How many there are and when they were created covers all of them, public and " +
           "private. Everything measured from the code itself — commits, stars, issues, " +
           "contributors — comes from GitHub and therefore covers the public repositories " +
           "only; the exception is the star total in the headline figures, which adds a " +
           "private aggregate carrying no names. The packages published from that code to " +
           "PyPI are tracked here too, as a second distribution channel alongside GitHub.",
    links: [
      { label: "ersilia-os on GitHub", href: "https://github.com/ersilia-os" },
      { label: "ersilia on PyPI", href: "https://pypi.org/project/ersilia/" },
    ],
    headlineKpi: "repositories",
    groups: [
      {
        title: "Popularity and activity",
        blurb: "Stars, commits and who is writing the code.",
        rows: [
          { h: "h-xl", cells: [
            {
              title: "Popularity against activity", span: 12, data: "repositories.scatter", type: "logscatter",
              scatter: { x: "stars", y: "commits", xLabel: "Stars", yLabel: "Commits" },
              desc: "One dot per public repository: stars against commits, both on logarithmic axes because a handful of repositories account for most of every metric — on linear axes the other 130 collapse into the corner. Dashed lines mark the medians, so the quadrants separate 'popular but quiet' from 'busy but unknown'. Only outliers are labelled. Both measures now come from GitHub directly rather than from a stored column, so they cannot drift from what the repository actually shows.",
            },
          ] },
          { h: "h-lg", cells: [
            {
              title: "Who writes the code", span: 5, data: "code.contribution_origin", type: "stackbar",
              desc: "Recently merged pull requests, split by whether their author belongs to the Ersilia organisation, from GitHub's own authorAssociation field. This is the most important chart on this page and it corrects a mistake: the per-model repositories were previously dismissed as carrying no signal, judged from their stars — eos4e40 has 2, eos2gw4 has 0. Nobody stars an individual model; they contribute one, through a pull request. Model repositories and everything else are shown separately because they are different kinds of work: a model repository is usually a submission, while ersilia itself is a codebase. The most recent 30 merged pull requests per repository are sampled, so this describes current practice rather than all history. Counts by association only — no author login is collected, so none can be published.",
            },
            {
              title: "Commits per quarter", span: 7, data: "code.commit_growth", type: "growthcombo",
              desc: "Commits to every non-archived public repository, by calendar quarter, with the running total. Collected through GitHub's GraphQL API as an exact count per window rather than through the REST statistics endpoint, which returns 202 and an empty body indefinitely for repositories with nothing to report. The current quarter is partial, as everywhere else on this site. Model repositories are included: an earlier version excluded them on the grounds that they carried no signal, which made this series cover a third of the commits while the rest of the page quoted the full figure.",
            },
          ] },
          { h: "h-lg", cells: [
            {
              title: "Stars gained over time", span: 7, data: "code.star_growth", type: "growthcombo",
              desc: "Every star on the repositories with more than five of them, by the quarter it was given. GitHub records the date each star was awarded, so this whole curve comes from one collection and needs no accumulated history. Restricted to the better-known repositories because a curve through three points is decoration. A star is not a user and not a download — it is a bookmark, and the honest reading is relative interest over time rather than a size.",
            },
            {
              title: "When each repository was last touched", span: 5, data: "code.activity_recency",
              type: "ordinallollipop",
              desc: "Every public repository by time since its last push. Archived repositories are counted separately rather than falling into the oldest band: archiving is a deliberate retirement, and filing it as neglect would report a decision as a failure.",
            },
          ] },
        ],
      },
      {
        title: "Rankings and contributors",
        blurb: "Whole-repository profiles: commits, PRs, issues, releases, stars and contributors.",
        rows: [
          { h: "h-lg", cells: [
            {
              title: "Where the work happens", span: 7, data: "code.most_active",
              type: "ranked", nameLabel: "Repository", top: 10,
              columns: [
                { key: "total_commits", label: "Commits" },
                { key: "merged_prs", label: "PRs" },
                { key: "closed_issues", label: "Issues closed" },
                { key: "releases", label: "Releases" },
                { key: "contributors", label: "People" },
                { key: "watchers", label: "Watching" },
              ],
              desc: "One row per repository rather than five ranking charts, so a project's whole profile stays together — 33 releases on lazy-qsar against 32 on ersilia describe very different projects, and only the surrounding columns distinguish them. Ranked by commits. Contributor counts include anonymous contributors.",
            },
            {
              title: "How long issues stay open", span: 5, data: "code.issue_resolution",
              type: "histogram",
              desc: "One value per repository: the median days between opening and closing an issue, over its most recent 30 closed issues, then bucketed. Per repository rather than per issue on purpose — a pooled distribution would be dominated by whichever repository files the most issues, which answers a different question. Repositories that have never closed an issue are absent rather than counted as instant.",
            },
          ] },
          { h: "h-lg", cells: [
            {
              title: "Most starred public repositories", span: 7, data: "repositories.ranked", type: "ranked", nameLabel: "Repository", top: 10,
              columns: [
                { key: "stars", label: "Stars" },
                { key: "forks", label: "Forks" },
                { key: "contributors", label: "People" },
              ],
              desc: "One table rather than three ranking charts, so a repository's whole profile sits on one row. Ranked by stars. Every figure here is read from GitHub at collection time; these used to be hand-maintained columns in Airtable and have been removed from it, because a standing total copied into a spreadsheet is precisely the thing that goes stale unnoticed.",
            },
            {
              title: "Commit concentration", span: 5, data: "repositories.contributor_concentration",
              type: "lorenz",
              desc: "Cumulative share of commits held by the least active repositories. The dashed diagonal is perfect evenness; the further the curve sits below it, the more the work concentrates in a few. Public repositories only — commit counts come from the GitHub snapshot, which is public by design, so a private repository has no count to contribute. This covered every repository while the figure was stored in Airtable.",
            },
          ] },
          { h: "h-lg", cells: [
            {
              title: "When each repository last released", span: 5, data: "code.release_recency",
              type: "ordinallollipop",
              desc: "Repositories by the year of their most recent release. Read this carefully, because the obvious reading is wrong: 164 repositories last releasing in 2025 against 72 in 2026 looks like releasing is slowing, and it is not evidence of that. 139 of 384 repositories have never cut a release at all, and most that do release do so rarely — a repository sitting on a 2025 tag is usually one that ships when there is something to ship, not one that stopped. The never-released group is a bar here rather than an omission, because without it the chart would describe 245 repositories while appearing to describe all of them.",
            },
            {
              title: "Contributors by repository count", span: 7, data: "repositories.top_contributors",
              type: "lollipop",
              desc: "Public GitHub handles by how many public Ersilia repositories they have contributed to, read from GitHub's contributors endpoint. The numbers are much larger than they used to be, and the reason is coverage rather than activity: this now spans all 386 public repositories including the per-model ones, where the Airtable column it replaced tracked only the 141 curated repositories. Automation accounts are excluded — ersilia-bot alone had committed to 245 repositories and would rank third, which describes CI rather than people. Anonymous contributors are also excluded, because GitHub identifies those by an email address rather than a login and no address is ever collected. Public handles attached to public commits: repository metadata, not community records, and the community table's own handles are dropped before they can reach this site. One repository counts once per person however many commits they made to it.",
            },
          ] },
        ],
      },
      {
        title: "Repository composition",
        blurb: "What the repositories are — counts, type, language — not what they have done.",
        rows: [
          { h: "h-xl", cells: [
            {
              title: "Repositories created over time", span: 8, data: "repositories.growth", type: "growthcombo",
              desc: "Every repository by the quarter it was created, public and private alike: new repositories on top, the running total below.",
            },
            {
              title: "Repository make-up", span: 4, type: "shares",
              blurb: "How the repositories split, public against private.",
              sources: [
                { label: "Public", data: "repositories.visibility", highlight: "Public" },
                { label: "Currently in progress", data: "repositories.by_status", highlight: "In progress" },
                {
                  label: "Model repos on current template (install.yml)",
                  data: "models.template_migration", highlight: "Current template (install.yml)",
                },
              ],
              desc: "How the repositories split. The public/private ratio is published deliberately: the honest way to handle an exclusion is to state its size rather than hide it. Private repositories are counted everywhere on this page and named nowhere. The template row is scoped to model repositories only: whether a model declares its Python version and dependencies via the current ersilia-model-template's install.yml, or still carries them baked into its Dockerfile — the legacy layout every model shipped with before it.",
            },
          ] },
          { h: "h-md", cells: [
            {
              title: "Repository type", span: 12, data: "repositories.by_type", type: "treemap",
              desc: "Every repository grouped by type; area is proportional to count. Seven categories with a long tail is more than a donut can carry legibly.",
            },
          ] },
          { h: "h-md", cells: [
            {
              title: "Work behind each model", span: 6, data: "code.model_commit_effort",
              type: "histogram",
              desc: "Commits per per-model repository, bucketed. Included to answer a fair question about a hub of a few hundred models: is each one a file drop? The distribution is the answer.",
            },
            {
              title: "Languages", span: 6, data: "code.by_language", type: "lollipop",
              desc: "GitHub's detected primary language per repository, which is a guess based on file extensions and counts one language per repository however many it contains. Repositories with no detectable language are excluded, so the total is smaller than the repository count.",
            },
          ] },
        ],
      },
      {
        title: "PyPI packages",
        blurb: "The same code, distributed a second way: what Ersilia has published to the " +
               "Python Package Index, and who is installing it.",
        rows: [
          { h: "h-lg", cells: [
            {
              title: "Every package", span: 12, data: "pypi.packages",
              type: "ranked", nameLabel: "Package", top: 12,
              columns: [
                { key: "window_total", label: "Downloads (window)" },
                { key: "version", label: "Version", raw: true },
                { key: "releases", label: "Releases" },
                { key: "last_30d", label: "Last 30d" },
                { key: "last_7d", label: "Last 7d" },
              ],
              desc: "Every package Ersilia publishes to PyPI, from PyPI's own package API. 'Downloads (window)' is a rolling total from pypistats.org — commonly 90 to 180 days of history, never a lifetime figure, because PyPI itself exposes no per-day download series and pypistats.org is the only public source that keeps one at all. Ranked by that window total.",
            },
          ] },
          { h: "h-md", cells: [
            {
              title: "Share of downloads", span: 5, data: "pypi.download_share", type: "donut",
              desc: "The same window total as the table above, as a share across packages. Six packages fits the donut's six-segment limit exactly, so nothing here is folded into an 'other' slice.",
            },
            {
              title: "Downloads, last 30 vs last 7 days", span: 7, data: "pypi.recent_downloads",
              type: "groupbar",
              desc: "Recent momentum rather than the window total beside it: the last 7 days against the last 30, per package. A package whose 7-day count is high relative to its 30-day one is picking up pace; one whose is low has gone quiet.",
            },
          ] },
          { h: "h-md", cells: [
            {
              title: "First published", span: 6, data: "pypi.first_release_year",
              type: "ordinallollipop",
              desc: "Packages by the year they first appeared on PyPI — the organisation's packaging history, not its current activity. With six packages this is a timeline of when each one shipped, not a distribution to be read for shape.",
            },
            {
              title: "Most recently released", span: 6, data: "pypi.release_recency",
              type: "ordinallollipop",
              desc: "Packages by the year of their most recent release — is each one still maintained, or shipped once and left. Read it beside the table above: a package can carry many releases and still not have shipped recently, or the reverse.",
            },
          ] },
          { h: "h-map", cells: [
            {
              title: "Where downloads come from", span: 12, data: "pypi.downloads_by_country",
              type: "map", mapLabel: "downloads",
              desc: "PyPI downloads by the country pip's request came from, for ersilia, ersilia-pack-utils and stylia — the three packages with enough volume to appear in a Google BigQuery sample of this size; isaura, eosce and olinda are too lightly downloaded to register. From a manual BigQuery export (see scripts/convert_pypi_geo.py), not the live pypistats.org figures elsewhere on this page, and covering a different window. Hong Kong and Taiwan have real totals — 498 and 118 downloads — but no shape in this site's simplified world map; see the ranked list beside it for those. Only 15% of downloads report a country reliably enough to place; the rest are proxies, mirrors or unidentifiable clients and are excluded here rather than guessed at.",
            },
          ] },
          { h: "h-md", cells: [
            {
              title: "Top countries", span: 12, data: "pypi.top_countries", type: "lollipop",
              desc: "The same download counts as the map, ranked — the form that does not depend on a country having a shape to shade. Hong Kong and Taiwan place 2nd and 10th here despite being invisible on the map above.",
            },
          ] },
        ],
      },
      {
        title: "Web traffic",
        blurb: "Where GitHub visitors come from and what they look at, org-wide — GitHub keeps no history here, only a rolling 14-day window.",
        rows: [
          { h: "h-lg", cells: [
            {
              title: "Visits by referrer type", span: 5, data: "traffic.referrer_categories",
              type: "donut",
              desc: "Referring visits over the most recently fetched 14-day window, bucketed by where the referrer sits: Ersilia's own sites, a search engine, scientific literature (a journal, preprint server or scholarly index), code/docs hosts, social platforms, an AI assistant, or other. 'Scientific literature' is the one worth watching — it means a reader arrived via a paper rather than by browsing GitHub's own UI.",
            },
            {
              title: "Top referring sites", span: 7, data: "traffic.top_referrers",
              type: "lollipop",
              desc: "The individual sites behind the ring beside it, ranked by referred visits in the same window.",
            },
          ] },
          { h: "h-lg", cells: [
            {
              title: "Views by page type", span: 5, data: "traffic.page_types",
              type: "lollipop",
              desc: "What a visitor was looking at when they landed, from the most-visited-paths endpoint, reduced to a coarse type. A visitor reading source files is evaluating the code; one sitting in issues or pull requests is contributing.",
            },
            {
              title: "Most-visited repositories", span: 7, data: "traffic.most_visited_repos",
              type: "lollipop",
              desc: "Which repositories carry the page-view traffic in the same window — scope is the whole organisation rather than just the per-model repositories, because the flagship ersilia repository is where most inbound traffic lands.",
            },
          ] },
          { h: "h-lg", cells: [
            {
              title: "Which pages draw people back", span: 12,
              data: "traffic.page_type_repeat", type: "lollipop",
              desc: "Page views per unique visitor in the same window, by page type — a ratio near 1 is a visitor who looked once; well above it is the same visitor returning repeatedly. 'Views by page type', to the left, counts raw views; this uses GitHub's per-path unique-visitor count instead, which is otherwise unused on this site. Page types with fewer than 10 unique visitors in the window are excluded, the same floor the rest of the site applies to a share.",
            },
          ] },
        ],
      },
      {
        title: "Licensing",
        blurb: "How the code itself is licensed, kept apart from GitHub activity and PyPI distribution.",
        rows: [
          { h: "h-md", cells: [
            {
              title: "How the code is licensed", span: 12, data: "code.by_licence", type: "donut",
              desc: "SPDX identifiers as GitHub reports them, read from each repository's licence file rather than from any hand-entered field. Ersilia standardises on GPL-3.0 across both the tooling and the per-model repositories — 227 of 241 model repositories carry it. Do not read this as the models' own licensing: the Model Hub page reports licence openness from the registry, and that describes the terms of the upstream model being wrapped, which is a different question with a genuinely different answer.",
            },
          ] },
        ],
      },
    ],
  },
  {
    id: "community",
    title: "Community",
    blurb: "The people who have contributed to Ersilia. Aggregate figures only — " +
           "no individual is identifiable anywhere on this site.",
    links: [{ label: "The team", href: "https://ersilia.io/team" }],
    headlineKpi: "community_members",
    rows: [
      { h: "h-xl", cells: [
        {
          title: "People involved over time", span: 12, data: "community.participation", type: "growthcombo",
          desc: "People by the quarter they joined: new joiners on top, the running total below. This section used to lead with a churn ledger and a cohort-retention grid; both were correct arithmetic and both framed a growing community as an attrition problem, when most collaborations here are internships and fellowships with a term fixed before anyone arrived.",
        },
      ] },
      { h: "h-lg", cells: [
        {
          title: "How long people stay", span: 5, data: "community.duration_buckets", type: "ordinallollipop",
          desc: "Completed collaborations by length. Only ended collaborations are counted — including current members would censor every long one downwards. Read it as the shape of the placements Ersilia runs, not as a target being missed.",
        },
        {
          title: "Roles held", span: 4, data: "community.roles", type: "lollipop",
          desc: "Roles across the community. A multi-select — someone who was both mentor and maintainer counts in both, so the shares sum above 100%.",
        },
        {
          title: "Composition", span: 3, type: "shares",
          blurb: "Aggregate composition only.",
          sources: [
            { label: "Still involved", data: "community.active_status", highlight: "Active" },
            { label: "Recorded as female", data: "community.by_gender", highlight: "Female" },
          ],
          desc: "Aggregate composition only. Gender is reported because representation is something Ersilia holds itself to.",
        },
      ] },
      { h: "h-lg", cells: [
        {
          title: "People involved at once", span: 4, data: "community.active_over_time", type: "area",
          desc: "People who had joined and not yet finished, counted each quarter. This is how large the community was at a given moment, as against how many have passed through it in total — the two are different questions and this page shows both.",
        },
        {
          title: "Countries represented", span: 4, data: "community.by_country", type: "lollipop",
          desc: "Community members by country of residence, as recorded.",
        },
        {
          title: "Home organisations", span: 4, data: "community.by_organisation", type: "lollipop",
          desc: "The institutions community members came from, as recorded on their entry.",
        },
      ] },
    ],
  },
  {
    id: "reach",
    title: "Countries & partners",
    blurb: "The countries Ersilia works in, how that maps onto its Global South mission, " +
           "and the organisations it works with.",
    links: [{ label: "About Ersilia", href: "https://ersilia.io/about" }],
    headlineKpi: "countries_represented",
    rows: [
      { h: "h-map", cells: [
        {
          title: "Where Ersilia works", span: 12, data: "reach.footprint_by_country", type: "map", mapLabel: "records",
          toggles: [
            { label: "All", data: "reach.footprint_by_country" },
            { label: "Organisations", data: "reach.organisations_by_country" },
            { label: "Community", data: "reach.community_by_country" },
            { label: "Events", data: "reach.events_by_country" },
          ],
          desc: "Countries shaded by how many partner organisations, community members or events are recorded there. Countries with no record keep the neutral fill rather than being shaded as though they were a zero.",
        },
      ] },
      { h: "h-sm", cells: [
        {
          title: "Global South and North", span: 4, data: "reach.south_north", type: "shares",
          blurb: "Engaged countries by World Bank income group.",
          sources: [{ label: "Global South", data: "reach.south_north", highlight: "Global South" }],
          desc: "Engaged countries split by World Bank income group: LIC, LMIC and UMIC counted as Global South, HIC as Global North. Countries with no income group recorded are excluded rather than assumed.",
        },
        {
          title: "By income group", span: 4, data: "reach.engagement_by_income_group",
          type: "ordinallollipop",
          desc: "Countries Ersilia engages with, by World Bank income group, ordered low to high income so the colour ramp follows the order.",
        },
        {
          title: "By world region", span: 4, data: "reach.engagement_by_region", type: "donut",
          desc: "Countries Ersilia engages with, grouped by world region.",
        },
      ] },
      { h: "h-md", cells: [
        {
          title: "By subregion", span: 12, data: "reach.engagement_by_subregion",
          type: "lollipop",
          desc: "Engaged countries grouped by UN subregion — the cut that matters most for this organisation, and the one the region donut above cannot show: a region chart collapses Sub-Saharan and Northern Africa into a single 'Africa' segment, when 14 of the 42 engaged countries are Sub-Saharan and exactly one is Northern African. Counted over engaged countries rather than over the reference table: that table lists 45 Sub-Saharan countries and Ersilia's engagement reaches 14 of them, so quoting the larger figure here would describe the world instead of the reach. Full width because several subregion names are too long to read in a narrow card.",
        },
      ] },
      { h: "h-lg", cells: [
        {
          title: "What partners work on", span: 7, data: "organisations.by_focus", type: "treemap",
          desc: "Focus areas across the partner network; area is proportional to count. A multi-select, so one organisation contributes to several.",
        },
        {
          title: "Partner organisations", span: 5, data: "organisations.by_type", type: "lollipop",
          desc: "Network organisations grouped by type — foundation, academia, corporate, civil society and so on.",
        },
      ] },
      { h: "h-lg", cells: [
        {
          title: "How much partners are involved", span: 7, data: "organisations.engagement_depth",
          type: "ordinallollipop",
          desc: "How many KINDS of recorded activity each partner has, out of four: a linked project, event, conference or community member. Read it alongside the three charts above, which count all 320 organisations equally — most of them have no recorded activity of any kind, so the directory is either largely prospective or the link fields are unfilled. Grants are a fifth link type and are deliberately excluded, since grant data is out of scope for this site.",
        },
        {
          title: "How partners are involved", span: 5, data: "organisations.by_classification",
          type: "lollipop",
          desc: "Whether an organisation funds the work, collaborates on it, or belongs to a network Ersilia is part of. A multi-select: an organisation can be both a funder and a collaborator, and several are.",
        },
      ] },
    ],
  },
  {
    id: "outreach",
    title: "Events & writing",
    blurb: "What Ersilia shows up to and what it publishes — talks, workshops and " +
           "conferences, and the blog.",
    links: [{ label: "Blog", href: "https://ersilia.io/blog" }],
    headlineKpi: "events",
    rows: [
      { h: "h-lg", cells: [
        {
          title: "Events and blog posts per year", span: 12, data: "__outreach_per_year", type: "groupbar",
          desc: "Both measures are yearly counts, so they share one axis and one chart rather than sitting in two — which makes them comparable instead of merely adjacent.",
        },
      ] },
      { h: "h-xl", cells: [
        {
          title: "Events over time", span: 7, data: "events.growth", type: "growthcombo",
          desc: "Events per year on top, the running total below, so the rate of activity and the accumulated total read together.",
        },
        {
          title: "Post topics", span: 5, data: "blogposts.by_category", type: "treemap",
          desc: "Blog posts grouped by topic category; area is proportional to count. A multi-select, so a post carrying two categories counts in both.",
        },
      ] },
      { h: "h-lg", cells: [
        {
          title: "Who convened the events", span: 5, data: "events.by_organiser", type: "lollipop",
          desc: "Organisations that convened the most events Ersilia took part in.",
        },
        {
          title: "Conferences tracked", span: 4, data: "conferences.by_cadence", type: "lollipop",
          desc: "The conferences Ersilia keeps an eye on, by how often they come round. A small, deliberately curated list rather than everything that exists.",
        },
        {
          title: "Reach of what we publish", span: 3, type: "shares",
          blurb: "Where posts appear, and remote access.",
          sources: [
            { label: "On Ersilia's own channels", data: "blogposts.by_publisher", highlight: "Ersilia" },
            { label: "Conferences joinable remotely", data: "conferences.remote", highlight: "Remote option" },
          ],
          desc: "Where the writing appears, and how many tracked conferences can be attended without travelling — which decides whether a researcher without travel funding can take part at all.",
        },
      ] },
    ],
  },
];
