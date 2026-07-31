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
        lorenz     how unevenly a total is spread.
        gantt      spans in time.
        map        geography.
        shares     several two-category splits, compactly (HTML).
        meters     "how many of the whole" figures (HTML).
        ranked     a top-N table with several columns and a microbar (HTML).

   2. SIZE FOLLOWS THE DATA. Do not set `span` except on a lead chart. cards.js
      derives it from how many categories the metric actually has, because a
      seven-category chart in a full-width card is seven bars adrift in white.

   Colour: the chrome is neutral and the palette belongs to the marks. A one-series
   chart takes the single accent; anything categorical takes the palette in order.
   Nothing here needs to name a colour. */

/* `slot` picks a palette slot for the tile's sparkline, so the headline row is
   polychrome. Chrome elsewhere stays neutral. */
const PRIMARY_KPIS = [
  { key: "models", label: "Models in the Hub", slot: 0 },
  { key: "community_members", label: "People involved", slot: 2 },
  { key: "repositories", label: "Repositories", slot: 5 },
  { key: "total_citations", label: "Citations", slot: 4 },
];

// Shown when the Models table has not been fetched yet, so the hero row still has
// four tiles rather than a gap.
const PRIMARY_KPIS_FALLBACK = [
  { key: "community_members", label: "People involved", slot: 0 },
  { key: "repositories", label: "Repositories", slot: 2 },
  { key: "publications", label: "Publications", slot: 5 },
  { key: "total_citations", label: "Citations", slot: 4 },
];

const SECONDARY_KPIS = [
  { key: "projects", label: "Projects" },
  { key: "publications", label: "Publications" },
  { key: "organisations", label: "Partner organisations" },
  { key: "countries_represented", label: "Countries" },
  { key: "total_stars", label: "GitHub stars" },
  { key: "events", label: "Events" },
  { key: "blogposts", label: "Blog posts" },
];

const VIEWS = [
  {
    id: "models",
    title: "Model Hub",
    blurb: "What is in the Ersilia Model Hub, what it is for, and how much of it is ready to run.",
    headlineKpi: "models",
    charts: [
      {
        title: "Models incorporated over time", data: "models.cumulative", type: "area",
        lead: true, span: 12, height: "h-lg",
        toggles: [
          { label: "Cumulative", data: "models.cumulative" },
          { label: "Per quarter", data: "models.per_quarter" },
        ],
        desc: "Models in the Hub by the quarter they were incorporated. Cumulative shows total size; per quarter shows the rate of addition.",
      },
      {
        title: "Biomedical area", data: "models.by_biomedical_area", type: "lollipop",
        desc: "What each model is for. The most mission-relevant cut the Hub records: Ersilia works on antimicrobial and antipathogen drug discovery, and this says how much of the Hub serves a named disease versus general-purpose chemistry. A multi-select, so a model spanning two areas counts in both.",
      },
      {
        title: "What the models do", data: "models.task_tree", type: "treehierarchy",
        desc: "Outer blocks are the model's task, inner ones its subtask. Both are single-valued, so every model sits in exactly one block and the areas sum to the model count.",
      },
      {
        title: "Curation status", data: "models.by_status", type: "donut",
        desc: "Every model by curation status. Colours follow the house status scale, so 'ready' is the same green wherever it appears.",
      },
      {
        title: "Where models can be run", data: "models.coverage", type: "meters",
        desc: "How many models have each distribution route on file — a Docker image, an S3 bundle, or source code.",
      },
      {
        title: "Built in-house or wrapped", data: "models.by_source_type", type: "lollipop",
        desc: "Whether a model was developed by Ersilia or packaged from externally published work. Wrapping external models is much of what the Hub is for.",
      },
    ],
  },
  {
    id: "projects",
    title: "Projects",
    blurb: "The project portfolio — what ran when, what overlapped, and what is still open.",
    headlineKpi: "projects",
    charts: [
      {
        title: "Project timeline", data: "projects.timeline", type: "gantt",
        lead: true, span: 12, height: "h-tall",
        desc: "One bar per project from start to end date, coloured by status, against a 'today' rule. Projects with no end date are drawn to today and marked open.",
      },
      {
        title: "Running at the same time", data: "projects.active_over_time", type: "area",
        span: 8,
        desc: "Projects started and not yet ended, counted in each quarter. The peak is how much was in flight at once.",
      },
      {
        title: "Status", data: "projects.status", type: "donut",
        desc: "Every project by current status, on the same colour scale as the timeline above.",
      },
      {
        title: "Median run length", data: "projects.duration", type: "meters",
        desc: "Median months per project, split between finished projects and those still running. Running projects are measured to today, so their figure is a floor.",
      },
    ],
  },
  {
    id: "publications",
    title: "Publications",
    blurb: "Peer-reviewed papers and preprints linked to Ersilia, and how far they reach.",
    headlineKpi: "publications",
    charts: [
      {
        title: "Output and accumulated citations", data: "publications.output_and_impact",
        type: "facets", lead: true, span: 12, height: "h-xl",
        desc: "Publications per year (top) against citations accumulated to date (bottom), sharing one time axis. Deliberately two panels rather than two y-axes: the scales are unrelated, and overlaying them would invent a correlation that is not in the data.",
      },
      {
        title: "Highest-impact venues", data: "publications.top_journals", type: "lollipop",
        span: 7,
        desc: "Mean citations per Ersilia article, for venues with at least two Ersilia articles. The two-article floor stops one lucky paper topping the ranking.",
      },
      {
        title: "How the work is framed", type: "shares", span: 5,
        sources: [
          { label: "Direct Ersilia affiliation", data: "publications.affiliation", highlight: "Yes" },
          { label: "African collaboration", data: "publications.by_african_collab", highlight: "Yes" },
          { label: "Primary research", data: "publications.by_type", highlight: "Research" },
        ],
        desc: "Three splits that say what kind of body of work this is. African collaboration is recorded on some papers only; the share is of those where it is recorded.",
      },
      {
        title: "Research topics", data: "publications.by_topic", type: "donut",
        desc: "Publications grouped by research topic. Topic is a multi-select. Four categories where one is very small: a treemap gave the smallest an unlabelled sliver, so this is a ring.",
      },
      {
        title: "Ersilia-affiliated against external, per year",
        data: "publications.affiliation_by_year", type: "stackbar", span: 7,
        desc: "Publications per year split by whether they carry a direct Ersilia affiliation.",
      },
    ],
  },
  {
    id: "repositories",
    title: "Code",
    blurb: "Ersilia's open-source repositories. Counts, dates and totals cover all of them; " +
           "anything that names a repository or a contributor covers the public ones only.",
    headlineKpi: "repositories",
    charts: [
      {
        title: "Popularity against activity", data: "repositories.scatter", type: "logscatter",
        lead: true, span: 12, height: "h-xl",
        scatter: { x: "stars", y: "commits", xLabel: "Stars", yLabel: "Commits" },
        desc: "One dot per public repository: stars against commits, both on logarithmic axes because a handful of repositories account for most of every metric — on linear axes the other 130 collapse into the corner. Dashed lines mark the medians, so the quadrants separate 'popular but quiet' from 'busy but unknown'. Only outliers are labelled.",
      },
      {
        title: "Repositories over time", data: "repositories.cumulative", type: "area",
        span: 8,
        toggles: [
          { label: "Cumulative", data: "repositories.cumulative" },
          { label: "Per quarter", data: "repositories.per_quarter" },
        ],
        desc: "Every repository by the quarter it was created, public and private alike.",
      },
      {
        title: "Public and private", data: "repositories.visibility", type: "shares", span: 4,
        sources: [{ label: "Public", data: "repositories.visibility", highlight: "Public" }],
        desc: "How the repositories split. Published deliberately: the honest way to handle an exclusion is to state its size rather than hide it.",
      },
      {
        title: "Most starred public repositories", data: "repositories.ranked", type: "ranked",
        span: 7, nameLabel: "Repository", top: 10,
        columns: [
          { key: "stars", label: "Stars" },
          { key: "forks", label: "Forks" },
          { key: "contributors", label: "People" },
        ],
        desc: "One table rather than three ranking charts, so a repository's whole profile sits on one row. Ranked by stars.",
      },
      {
        title: "Commit concentration", data: "repositories.contributor_concentration",
        type: "lorenz", span: 5,
        desc: "Cumulative share of all commits held by the least active repositories. The dashed diagonal is perfect evenness; the further the curve sits below it, the more the work concentrates in a few repositories.",
      },
      {
        title: "Contributors by repository count", data: "repositories.top_contributors",
        type: "lollipop",
        desc: "Public GitHub handles by how many public Ersilia repositories they have contributed to. Public repository metadata, not community records.",
      },
      {
        title: "Repository type", data: "repositories.by_type", type: "treemap",
        desc: "Every repository grouped by type; area is proportional to count. Seven categories with a long tail is more than a donut can carry legibly.",
      },
    ],
  },
  {
    id: "community",
    title: "Community",
    blurb: "The people who have contributed to Ersilia. Aggregate figures only — " +
           "no individual is identifiable anywhere on this site.",
    headlineKpi: "community_members",
    charts: [
      {
        title: "Joiners, leavers and net change", data: "community.flow", type: "groupbar",
        lead: true, span: 12, height: "h-lg",
        desc: "People who joined against people whose involvement ended, each quarter, with the net change as a line. Answers whether the community is compounding or recycling.",
      },
      {
        title: "Cohort retention", data: "community.retention", type: "heatmap",
        span: 7, height: "h-md",
        desc: "For each joining year, the share still involved at 3, 6, 12 and 24 months. A cohort only counts towards a horizon once it is old enough to judge, so recent years have blank cells rather than misleading zeroes.",
      },
      {
        title: "How long collaborations last", data: "community.tenure", type: "histogram",
        span: 5,
        desc: "Completed collaborations binned by length in months, with the mean marked. People still involved are excluded — including them would drag every long tenure down.",
      },
      {
        title: "Roles held", data: "community.roles", type: "lollipop",
        desc: "Roles across the community. A multi-select — someone who was both mentor and maintainer counts in both, so the shares sum above 100%.",
      },
      {
        title: "Countries represented", data: "community.by_country", type: "lollipop",
        desc: "Community members by country of residence, as recorded.",
      },
      {
        title: "Composition", type: "shares", span: 4,
        sources: [
          { label: "Still involved", data: "community.active_status", highlight: "Active" },
          { label: "Recorded as female", data: "community.by_gender", highlight: "Female" },
        ],
        desc: "Aggregate composition only. Gender is reported because representation is something Ersilia holds itself to.",
      },
    ],
  },
  {
    id: "reach",
    title: "Global reach",
    blurb: "Where Ersilia actually works, and how that maps onto the Global South mission it states.",
    headlineKpi: "countries_represented",
    charts: [
      {
        title: "Where Ersilia works", data: "reach.footprint_by_country", type: "map",
        lead: true, span: 12, height: "h-map", mapLabel: "records",
        toggles: [
          { label: "All", data: "reach.footprint_by_country" },
          { label: "Organisations", data: "reach.organisations_by_country" },
          { label: "Community", data: "reach.community_by_country" },
          { label: "Events", data: "reach.events_by_country" },
        ],
        desc: "Countries shaded by how many partner organisations, community members or events are recorded there. Countries with no record keep the neutral fill rather than being shaded as though they were a zero.",
      },
      {
        title: "Global South and North", data: "reach.south_north", type: "shares", span: 4,
        sources: [{ label: "Global South", data: "reach.south_north", highlight: "Global South" }],
        desc: "Engaged countries split by World Bank income group: LIC, LMIC and UMIC counted as Global South, HIC as Global North. Countries with no income group recorded are excluded rather than assumed.",
      },
      {
        title: "By income group", data: "reach.engagement_by_income_group",
        type: "ordinallollipop", span: 4,
        desc: "Countries Ersilia engages with, by World Bank income group, ordered low to high income so the colour ramp follows the order.",
      },
      {
        title: "By world region", data: "reach.engagement_by_region", type: "donut", span: 4,
        desc: "Countries Ersilia engages with, grouped by world region.",
      },
      {
        title: "What partners work on", data: "organisations.by_focus", type: "treemap",
        span: 7,
        desc: "Focus areas across the partner network; area is proportional to count. A multi-select, so one organisation contributes to several.",
      },
      {
        title: "Partner organisations", data: "organisations.by_type", type: "lollipop",
        span: 5,
        desc: "Network organisations grouped by type — foundation, academia, corporate, civil society and so on.",
      },
    ],
  },
  {
    id: "outreach",
    title: "Outreach",
    blurb: "Events Ersilia convened or took part in, and what it publishes.",
    headlineKpi: "events",
    charts: [
      {
        title: "Events and blog posts per year", data: "__outreach_per_year", type: "groupbar",
        lead: true, span: 12, height: "h-lg",
        desc: "Both measures are yearly counts, so they share one axis and one chart rather than sitting in two — which makes them comparable instead of merely adjacent.",
      },
      {
        title: "Post topics", data: "blogposts.by_category", type: "treemap", span: 5,
        desc: "Blog posts grouped by topic category; area is proportional to count. A multi-select.",
      },
      {
        title: "Who convened the events", data: "events.by_organiser", type: "lollipop",
        span: 7,
        desc: "Organisations that convened the most events Ersilia took part in.",
      },
      {
        title: "Where posts appear", data: "blogposts.by_publisher", type: "shares", span: 4,
        sources: [{ label: "On Ersilia's own channels", data: "blogposts.by_publisher", highlight: "Ersilia" }],
        desc: "Posts on Ersilia's own channels against those published by others.",
      },
    ],
  },
];
