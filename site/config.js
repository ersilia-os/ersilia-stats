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
        runtimelines a few named log-log curves against a dashed median — the
                   individual outliers behind a bandline.
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
  { key: "pypi_downloads", label: "PyPI downloads" },
];

const VIEWS = [
  {
    id: "models",
    title: "Model Hub",
    blurb: "What is in the Ersilia Model Hub and what it is for. Every chart counts the models that are Ready or In maintenance, except Curation status, which shows the whole registry.",
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
              title: "What the models do", span: 8, data: "models.task_tree", type: "treehierarchy",
              desc: "Outer blocks are the model's task, inner ones its subtask. Both are single-valued, so every model sits in exactly one block and the areas sum to the model count.",
            },
            {
              title: "Curation status", span: 4, data: "models.by_status", type: "donut",
              desc: "Every model in the registry by curation status, including Archived and In progress — the only chart on this page that goes beyond the models Ready or In maintenance. Colours follow the house status scale, so 'ready' is the same green wherever it appears.",
            },
          ] },
          { h: "h-lg", cells: [
            {
              title: "Pathogens targeted", span: 6, data: "models.by_target_organism", type: "lollipop",
              desc: "Models that act on a named organism. 'Any' and 'Homo sapiens' are excluded on purpose: both are real answers but they describe organism-agnostic chemistry and human-property prediction respectively, and together they would fill the ranking without saying anything about pathogen coverage.",
            },
            {
              title: "Biomedical area", span: 6, data: "models.by_biomedical_area", type: "lollipop",
              desc: "What each model is for. Ersilia works on antimicrobial and antipathogen drug discovery, and this says how much of the Hub serves a named disease versus general-purpose chemistry. A multi-select, so a model spanning two areas counts in both.",
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
              type: "donut",
              desc: "The publication type of the work each model is based on. Provenance rather than popularity, and the counterpart to the source-type figure ('Wraps external work?') beside it: that says whether Ersilia packaged somebody else's model, this says how well established that model's science is. Preprints are counted separately from peer-reviewed work rather than folded in with it.",
            },
            {
              title: "Wraps external work?", span: 4, data: "models.by_source_type", type: "donut",
              desc: "Where each model comes from, as recorded in the registry's Source Type field. Internal: built by Ersilia's own team. External: a model published by a third party and packaged as is. Replicated: a third party's published model that Ersilia re-trained itself.",
            },
          ] },
          { h: "h-md", cells: [
            {
              title: "Licences of the underlying models", span: 12, data: "models.by_license",
              type: "treemap",
              desc: "The licence of each wrapped model as recorded in the registry — NOT the licence of Ersilia's wrapper repository, which is GPL-3.0 on 224 of the 237 model repositories. The two answer different questions and genuinely differ: the upstream models spread across MIT, both GPL-3.0 variants, Apache-2.0 and BSD-3-Clause, and it is the upstream terms that govern what a reuser may do with the underlying science. 'None' is the models that record no licence, which for a reuser is the most restrictive state of all.",
            },
          ] },
        ],
      },
      {
        title: "Where and how models run",
        blurb: "Runtime at scale, and the Docker images models ship in.",
        rows: [
          { h: "h-lg", cells: [
            {
              title: "Computational performance", span: 12, data: "models.performance_by_scale",
              type: "bandline",
              desc: "Median runtime as the batch size grows tenfold at each step, with the 25th-75th percentile band — the same plot as entry_project's Engineering tab, redrawn here. The runtime axis is log scale because the measure spans orders of magnitude: a model taking fractions of a second on one input can take minutes on ten thousand. A run that takes too long is stopped and no runtime is recorded for it (a -1 in the registry's Computational Performance column). Those models are not dropped: each counts as slower than every model that finished, so it pushes the median and the band up — leaving them out would make the larger batch sizes look faster than they are, because the slowest models are exactly the ones that get stopped. The number stopped at each size is marked on the 'Not finished' row at the top. Where more than a quarter of models were stopped, the 75th percentile has no runtime either and the band runs to the top of the chart.",
            },
          ] },
          { h: "h-lg", cells: [
            {
              title: "The slowest models", span: 12, data: "models.slowest_models",
              type: "runtimelines",
              desc: "Runtime at 10, 100, 1,000 and 10,000 molecules for the six slowest models, with the Hub median at each size as a dashed line — the named outliers behind the median curve above. A value of -1 means the run did not finish, which counts as infinitely slow: a model that stopped finishing at a smaller batch ranks slower than one that stopped at a larger batch, and both rank slower than any model that finished every size. Ties go to the runtime at the largest batch the model did finish. A run that did not finish is drawn as a triangle at the top of the chart, where the line stops. The median covers every model benchmarked at all four sizes, with unfinished runs counted the same way. Both axes are log scale: one step right is ten times the molecules, one step up ten times the time.",
            },
          ] },
          { h: "h-lg", cells: [
            {
              title: "When images were last built", span: 12, data: "model_activity.image_freshness",
              type: "column",
              desc: "The year each model's Docker image was last pushed. This is BUILD recency and not maintenance or demand: the pull-count evidence elsewhere on this page shows that continuous integration pulls every image on a schedule, and that same schedule is what rebuilds them.",
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
              desc: "Every model records an AMD64 build; this is whether it also publishes an ARM64 one — the cheap, low-power hardware.",
            },
          ] },
        ],
      },
      {
        title: "Docker Hub demand",
        blurb: "Pull counts from Docker Hub — a floor on interest, not a headcount.",
        rows: [
          { h: "h-lg", cells: [
            {
              title: "Most pulled models", span: 12, data: "usage.most_pulled_models",
              type: "ranked", nameLabel: "Model", top: 10,
              columns: [
                { key: "pulls", label: "Pulls" },
                { key: "times_baseline", label: "× baseline", raw: true },
                { key: "ci_test", label: "CI test model", raw: true },
              ],
              desc: "Docker Hub pull counts, ranked by how far each model exceeds the automated baseline rather than by raw pulls — ranking by raw pulls would rank the build schedule. Only models clearly above the baseline appear. Read the top of this list with care: eos3b5e, eos5axz, eos4e40 and eos2r5a are the models Ersilia's own continuous integration pulls from Docker Hub on every test run of the ersilia package (marked 'Yes' in the CI test model column), and eos3b5e is also the default test model across Ersilia's tooling. Their counts are inflated by automated testing, not demand. A pull is not a user: mirrors pull images, and one person testing in a loop pulls repeatedly. It is a floor on interest, not a headcount, and Docker Hub publishes no history, so these are totals to date and cannot be turned into a rate.",
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
              title: "Last pull, by day of the week", span: 12,
              data: "usage.pull_rhythm_weekday", type: "ordinallollipop",
              desc: "Every image's most recent pull, by the UTC day of the week it landed on. Scheduled automation is flat across the week; human work collapses at the weekend — so a real weekend dip is evidence some of this traffic is not a machine. One recency-biased sample per digest, not a volume: Docker Hub exposes only the most recent pull per digest, never a series.",
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
              title: "Work on the Hub, by quarter", span: 8, data: "model_activity.hub_commit_growth",
              type: "growthcombo",
              desc: "Commits to the per-model repositories only, by calendar quarter, with the running total. Separate from the organisation-wide series on the Code page because it answers a different question: how much work goes into the Hub itself as against Ersilia's tooling. Both come from the same collection pass, filtered differently. The current quarter is partial.",
            },
            {
              title: "Models with an outside contribution", span: 4,
              data: "model_activity.outside_contribution", type: "donut",
              desc: "Counted per model, not per pull request, and that is the point: a high share of outside pull requests could in principle be a handful of models attracting all of them. 'Outside' means anyone who is not a current member of the ersilia-os GitHub organisation, not credited as a model contributor in the Model Hub registry, and not a bot. This counts the models themselves, so it measures how far community contribution actually reaches into the Hub. Only the most recent 30 merged pull requests per repository are sampled, so a model whose only outside contribution is older reads as internal — the figure is a floor, not a ceiling.",
            },
          ] },
          { h: "h-lg", cells: [
            {
              title: "Busiest model repositories", span: 12, data: "model_activity.most_active_models",
              type: "ranked", nameLabel: "Model", nameKey: "title", top: 10,
              columns: [
                { key: "name", label: "EOS ID", raw: true },
                { key: "total_commits", label: "Commits" },
                { key: "merged_prs", label: "PRs" },
                { key: "closed_issues", label: "Issues" },
                { key: "pulls", label: "Pulls" },
              ],
              desc: "The three sources on one row: commits, pull requests and issues from GitHub, pull counts from Docker Hub, joined on the shared eosXXXX identifier — every one of the 237 models resolves in all three. Ranked by commits. Pulls are a column rather than a ranking deliberately: they correlate with commits at Spearman 0.52, but that almost certainly measures continuous integration rebuilding busier repositories more often rather than anyone choosing them, so no relationship is implied here.",
            },
          ] },
          { h: "h-lg", cells: [
            {
              title: "Who gets credited for incorporating a model", span: 12,
              data: "models.top_contributors", type: "lollipop",
              desc: "The registry's `Contributor` field, by how many models each person is credited with — a public GitHub handle, the same kind of identifier already published for commit authorship on the Code page. Multi-select, so a model credited to two people counts for both.",
            },
          ] },
        ],
      },
      {
        title: "Versioning",
        blurb: "Version history per model from GitHub Releases: is a model maintained past its first v1.0.0?",
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
              desc: "Every model release, by the quarter it was published, with the running total, from 2026. GitHub Releases were introduced across the Hub at the end of 2025, when every existing model got its first release at once, so that quarter is a one-off backfill rather than activity and is left out. It counts every release, so a model re-packaged five times counts five times.",
            },
          ] },
          { h: "h-md", cells: [
            {
              title: "Time between a model's releases", span: 12, data: "releases.cadence",
              type: "ordinallollipop",
              desc: "The gap between one GitHub Release and the next, for the same model — not whether a model gets re-released (the release-count chart above answers that), but how often. Only gaps between two releases of the same repository count; a repo's first release has nothing before it to measure a gap against, so it is excluded rather than counted as zero or infinite.",
            },
          ] },
          { h: "h-lg", cells: [
            {
              title: "Most common packages", span: 12,
              data: "packages.most_common", type: "lollipop",
              desc: "The packages installed most often across the Hub's models, from install.yml, the model template's own pinned install list. Counted per model, not per install.yml line, so a package listed twice for one repository cannot inflate its own count. ersilia-pack-utils is left out: it is the model template's own packaging dependency, installed in almost every model rather than chosen for one. Models whose install.yml could not be fetched, mostly legacy-template repositories whose dependencies still live in a Dockerfile, are absent from the count rather than assumed to install nothing, so the total beside the title is smaller than the model count.",
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
          title: "What each project produced", span: 12, data: "projects.outputs",
          type: "ranked", nameLabel: "Project", top: 10,
          columns: [
            { key: "repositories", label: "Repos" },
            { key: "public", label: "Public" },
            { key: "publications", label: "Papers" },
          ],
          desc: "Repositories and publications linked to each project, from the Airtable link columns. Repository counts cover public and private alike — a count is not disclosure — and the public column says how many can be named; no private repository name is ever resolved. Projects with neither are omitted.",
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
    blurb: "Peer-reviewed papers and preprints carrying an Ersilia affiliation and how far they reach, plus the blog and videos.",
    links: [{ label: "Publications", href: "https://ersilia.io/publications" }],
    headlineKpi: "publications",
    groups: [
      {
        title: "Papers",
        rows: [
          { h: "h-lg", cells: [
            {
              title: "Publications over time", span: 7, data: "publications.growth", type: "growthcombo",
              desc: "Ersilia-affiliated papers and preprints by year of publication: bars for the year, a line for the running total. The bars can be hidden from the legend to read the total on its own. Unaffiliated work by the team is excluded here and shown at the foot of the page.",
            },
            {
              title: "How the work is framed", span: 5, type: "shares",
              blurb: "Two splits that say what kind of body of work this is.",
              sources: [
                { label: "African collaboration", data: "publications.by_african_collab", highlight: "Yes" },
                { label: "Primary research", data: "publications.by_type", highlight: "Research" },
              ],
              desc: "Two splits that say what kind of body of work this is, over the Ersilia-affiliated papers. African collaboration is recorded on some papers only; that share is of those where it is recorded.",
            },
          ] },
          { h: "h-lg", cells: [
            {
              title: "Citations accumulated", span: 7, data: "publications.citation_accrual",
              type: "growthcombo",
              desc: "Citations by the year each citation was MADE, from OpenAlex — real accrual, not citations attributed to their paper's publication year. That distinction used to require a caveat here, because the previous source only recorded the paper's year and made recent years look artificially thin. Kept separate from the publication count above rather than sharing a plot with it: publications and citations are different measures, and two different measures on two axes is what invites a reader to see a relationship the data does not assert.",
            },
            {
              title: "Research topics", span: 5, data: "publications.by_topic", type: "lollipop",
              desc: "Publications grouped by research topic. A multi-select, so a paper spanning two topics counts in both.",
            },
          ] },
          { h: "h-lg", cells: [
            {
              title: "Who can read it", span: 4, type: "shares",
              blurb: "Whether the work is behind a paywall.",
              sources: [
                { label: "Open access", data: "publications.open_access", highlight: "Open access" },
              ],
              desc: "Whether each paper can be read without a subscription, classified by OpenAlex. This is a mission figure rather than a vanity one: an organisation whose purpose is to serve researchers in low-resource settings has a direct interest in whether its own output is reachable by them. The routes are not equivalent — gold means published open, while bronze is readable at the publisher's discretion and can be withdrawn — and the breakdown is in the next card.",
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
              desc: "Countries of the author institutions across the Ersilia-affiliated papers, from OpenAlex. This measures international collaboration instead of asserting it: the publications table also carries a hand-set African-collaboration flag, and this counts the institutions, so South Africa, Cameroon and Mozambique appear as themselves. Institution countries only — no author names are collected or published.",
            },
          ] },
          { h: "h-lg", cells: [
            {
              title: "Most cited publications", span: 12, data: "publications.most_cited",
              type: "ranked", nameLabel: "Title", nameKey: "title", top: 10,
              columns: [
                { key: "citations", label: "Citations" },
                { key: "year", label: "Year", raw: true },
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
        title: "Blogposts",
        blurb: "Posts on Ersilia's blog and elsewhere.",
        rows: [
          { h: "h-lg", cells: [
            {
              title: "Posts over time", span: 7, data: "blogposts.growth", type: "growthcombo",
              desc: "Blog posts per year on top, the running total below.",
            },
            {
              title: "Post topics", span: 5, data: "blogposts.by_category", type: "treemap",
              desc: "Blog posts grouped by topic category; area is proportional to count. A multi-select, so a post carrying two categories counts in both.",
            },
          ] },
        ],
      },
      {
        title: "Videos",
        blurb: "Recorded talks, trainings and media appearances.",
        rows: [
          { h: "h-lg", cells: [
            {
              title: "Videos over time", span: 7, data: "videos.growth", type: "growthcombo",
              desc: "Videos per year by recording date on top, the running total below.",
            },
            {
              title: "Video topics", span: 5, data: "videos.by_domain", type: "lollipop",
              desc: "Videos by domain. A multi-select, so a video in two domains counts in both.",
            },
          ] },
        ],
      },
    ],
  },
  {
    id: "repositories",
    title: "Code",
    blurb: "Ersilia's open-source repositories: counts cover public and private alike, " +
           "while anything measured from the code itself covers the public ones only.",
    links: [
      { label: "ersilia-os on GitHub", href: "https://github.com/ersilia-os" },
      { label: "ersilia on PyPI", href: "https://pypi.org/project/ersilia/" },
    ],
    headlineKpi: "repositories",
    groups: [
      {
        title: "Repository composition",
        blurb: "What the repositories are — type, counts, language — not what they have done.",
        rows: [
          { h: "h-md", cells: [
            {
              title: "Repository type", span: 12, data: "repositories.by_type", type: "treemap",
              desc: "Every repository grouped by type; area is proportional to count. Seven categories with a long tail is more than a donut can carry legibly.",
            },
          ] },
          { h: "h-xl", cells: [
            {
              title: "Repositories created over time", span: 8, data: "repositories.growth", type: "growthcombo",
              desc: "Every repository by the quarter it was created, public and private alike: new repositories on top, the running total below.",
            },
            {
              title: "In progress vs completed", span: 4, data: "repositories.progress", type: "donut",
              desc: "Repositories whose Airtable status is In progress against those marked Completed, public and private alike. The other statuses — Archived, Discontinued, Idle and Todo — are left out, so the total is smaller than the repository count.",
            },
          ] },
          { h: "h-md", cells: [
            {
              title: "Languages", span: 12, data: "code.by_language", type: "lollipop",
              desc: "GitHub's detected primary language per repository, which is a guess based on file extensions and counts one language per repository however many it contains. Repositories with no detectable language are excluded, so the total is smaller than the repository count.",
            },
          ] },
        ],
      },
      {
        title: "Popularity and activity",
        blurb: "Stars, commits and who is writing the code.",
        rows: [
          { h: "h-lg", cells: [
            {
              title: "Who writes the code", span: 5, data: "code.contribution_origin", type: "stackbar",
              desc: "Recently merged pull requests, split by who wrote them. 'From the organisation' means the author is a current member or collaborator of the ersilia-os GitHub organisation, is listed in Ersilia's community records or credited as a model contributor in the Model Hub registry, or is a bot such as dependabot or Claude, which act on the organisation's behalf. Everyone else is outside. GitHub's own membership label is not enough on its own: it reflects membership today, so staff who were never added to the GitHub organisation and interns whose membership has ended would read as outside. 'Model repos' are the per-model eosXXXX repositories; 'Other repos' are every other public repository — ersilia itself, ersilia-pack, ersilia-hub, eos-template and the rest of the tooling. The most recent 30 merged pull requests per repository are sampled, so this describes current practice rather than all history. Only counts are kept — no author login is stored, so none can be published.",
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
              desc: "One row per repository rather than five ranking charts, so a project's whole profile stays together — 33 releases on lazy-qsar against 32 on ersilia describe very different projects, and only the surrounding columns distinguish them. Ranked by commits. Public repositories only, and the per-model eosXXXX repositories are left out — they belong to the Model Hub page. Contributor counts include anonymous contributors.",
            },
            {
              title: "How long issues stay open", span: 5, data: "code.issue_resolution",
              type: "histogram",
              desc: "One value per repository: the median days between opening and closing an issue, over its most recent 30 closed issues, then bucketed. Per repository rather than per issue on purpose — a pooled distribution would be dominated by whichever repository files the most issues, which answers a different question. Repositories that have never closed an issue are absent rather than counted as instant.",
            },
          ] },
          { h: "h-lg", cells: [
            {
              title: "Most starred public repositories", span: 6, data: "repositories.ranked", type: "ranked", nameLabel: "Repository", top: 10,
              columns: [
                { key: "stars", label: "Stars" },
                { key: "forks", label: "Forks" },
                { key: "contributors", label: "People" },
              ],
              desc: "One table rather than three ranking charts, so a repository's whole profile sits on one row. Ranked by stars. Every figure here is read from GitHub at collection time; these used to be hand-maintained columns in Airtable and have been removed from it, because a standing total copied into a spreadsheet is precisely the thing that goes stale unnoticed.",
            },
            {
              title: "Contributors by repository count", span: 6, data: "repositories.top_contributors",
              type: "lollipop",
              desc: "Public GitHub handles by how many public Ersilia repositories they have contributed to, read from GitHub's contributors endpoint. The numbers are much larger than they used to be, and the reason is coverage rather than activity: this now spans all 386 public repositories including the per-model ones, where the Airtable column it replaced tracked only the 141 curated repositories. Automation accounts are excluded — ersilia-bot alone had committed to 245 repositories and would rank third, which describes CI rather than people. Anonymous contributors are also excluded, because GitHub identifies those by an email address rather than a login and no address is ever collected. Public handles attached to public commits: repository metadata, not community records, and the community table's own handles are dropped before they can reach this site. One repository counts once per person however many commits they made to it.",
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
              desc: "PyPI downloads by the country pip's request came from, for ersilia and ersilia-pack-utils combined; the other four packages are not in this export. From a manual BigQuery export (see scripts/convert_pypi_geo.py), not the live pypistats.org figures elsewhere on this page, and covering a different window. Hong Kong and Taiwan have real totals — 516 and 105 downloads — but no shape in this site's simplified world map; see the ranked list below for those. Downloads with no reliably reported country are excluded rather than guessed at.",
            },
          ] },
          { h: "h-md", cells: [
            {
              title: "Top countries", span: 12, data: "pypi.top_countries", type: "lollipop",
              desc: "The same download counts as the map, ranked — the form that does not depend on a country having a shape to shade. Hong Kong and Taiwan place 3rd and 12th here despite being invisible on the map above.",
            },
          ] },
        ],
      },
      {
        title: "Web traffic",
        blurb: "Which repositories GitHub visitors look at, org-wide — GitHub keeps no history here, only a rolling 14-day window.",
        rows: [
          { h: "h-lg", cells: [
            {
              title: "Most-visited repositories", span: 12, data: "traffic.most_visited_repos",
              type: "lollipop",
              desc: "Which repositories carry the page-view traffic in the most recently fetched 14-day window — scope is the whole organisation rather than just the per-model repositories, because the flagship ersilia repository is where most inbound traffic lands.",
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
          title: "Engagement duration", span: 5, data: "community.duration_buckets", type: "ordinallollipop",
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
          title: "Countries represented", span: 6, data: "community.by_country", type: "lollipop",
          desc: "Community members by country of residence, as recorded.",
        },
        {
          title: "Home organisations", span: 6, data: "community.by_organisation", type: "lollipop",
          desc: "The institutions community members came from, as recorded on their entry.",
        },
      ] },
    ],
  },
  {
    id: "partners",
    title: "Partners",
    blurb: "The organisations Ersilia has run projects with, where they and the community " +
           "are, and the events Ersilia takes part in — many of them co-organised with partners.",
    links: [{ label: "About Ersilia", href: "https://ersilia.io/about" }],
    headlineKpi: "organisations",
    groups: [
      {
        title: "Where Ersilia works",
        blurb: "Partners, community members and events by country, against the Global South mission.",
        rows: [
          { h: "h-map", cells: [
            {
              title: "Where Ersilia works", span: 12, data: "reach.footprint_by_country", type: "map", mapLabel: "records",
              toggles: [
                { label: "All", data: "reach.footprint_by_country" },
                { label: "Partners", data: "reach.organisations_by_country" },
                { label: "Community", data: "reach.community_by_country" },
                { label: "Events", data: "reach.events_by_country" },
              ],
              desc: "Countries shaded by how many partners, community members or events are recorded there. A partner is an organisation Ersilia has done, or is doing, a project with; the rest of the organisations directory is left out. Countries with no record keep the neutral fill rather than being shaded as though they were a zero.",
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
        ],
      },
      {
        title: "Events",
        blurb: "Talks, conferences and trainings Ersilia takes part in, many co-organised with partners.",
        rows: [
          { h: "h-xl", cells: [
            {
              title: "Events over time", span: 8, data: "events.growth", type: "growthcombo",
              desc: "Events per year on top, the running total below, so the rate of activity and the accumulated total read together.",
            },
            {
              title: "Online or in person", span: 4, data: "events.by_format", type: "donut",
              desc: "Each event by its recorded format.",
            },
          ] },
          { h: "h-lg", cells: [
            {
              title: "Type of event", span: 4, data: "events.by_type", type: "lollipop",
              desc: "Events by type — talk, conference, training or other.",
            },
            {
              title: "Where events took place", span: 4, data: "events.by_country", type: "lollipop",
              desc: "Events by country. Events with no country recorded are left out.",
            },
            {
              title: "Who convened the events", span: 4, data: "events.by_organiser", type: "lollipop",
              desc: "Organisations that convened the most events Ersilia took part in.",
            },
          ] },
        ],
      },
    ],
  },
];
