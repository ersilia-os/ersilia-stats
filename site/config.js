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

   2. LAYOUT IS EXPLICIT AND COMPLETE. Charts are grouped into `rows`, and the spans
      in every row MUST sum to 12. Cards in a row stretch to one height and their
      charts flex to fill it, so the page tessellates with no gaps and no ragged
      edges — which is what makes it read as a dashboard rather than a pile of
      cards. `h` sets the row height. Pick spans from the shape of the data: a time
      series wants width, a ranking wants height, a ratio wants very little.

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
    rows: [
      { h: "h-xl", cells: [
        {
          title: "Models added over time", span: 12, data: "models.growth", type: "facets",
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
          title: "Where models can be run", span: 3, data: "models.coverage", type: "meters",
          desc: "How many models have each distribution route on file — a Docker image, an S3 bundle, or source code. Presence of a value is the signal: an empty DockerHub cell means the model was never pushed there.",
        },
      ] },
      { h: "h-md", cells: [
        {
          title: "Years from paper to Hub", span: 3, data: "models.publication_lag", type: "histogram",
          desc: "Incorporation year minus the model's original publication year — how quickly the Hub tracks the literature. Rows where incorporation precedes publication are dropped, since a negative lag means one of the two dates is wrong.",
        },
        {
          title: "How far models scale", span: 3, data: "models.scaling_limit", type: "ordinallollipop",
          desc: "The largest input batch each model actually completed. Derived, not recorded: the five Computational Performance columns hold runtimes at increasing batch sizes, and a value of -1 means the model failed at that size, so the largest column with a positive number is the largest batch it got through.",
        },
        {
          title: "Docker image size", span: 3, data: "models.image_size", type: "histogram",
          desc: "How heavy each model's Docker image is, in gigabytes. Relevant to running the Hub on modest hardware, where pull size and disk are the binding constraints.",
        },
        {
          title: "How models are built", span: 3, type: "shares",
          blurb: "Wrapped work, and ARM support.",
          sources: [
            { label: "Wraps external work", data: "models.by_source_type", highlight: "External" },
            { label: "Also builds for ARM64", data: "models.on_arm", highlight: "ARM64 and AMD64" },
          ],
          desc: "Two things about how the Hub is assembled: how much of it packages externally published models rather than Ersilia's own, and how much of it builds for ARM64 as well as AMD64 — ARM being the cheap, low-power hardware.",
        },
      ] },
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
          title: "Projects started over time", span: 12, data: "projects.growth", type: "facets",
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
    blurb: "Peer-reviewed papers and preprints linked to Ersilia, and how far they reach.",
    links: [{ label: "Publications", href: "https://ersilia.io/publications" }],
    headlineKpi: "publications",
    rows: [
      { h: "h-xl", cells: [
        {
          title: "Output and accumulated citations", span: 12, data: "publications.output_and_impact",
          type: "facets",
          desc: "Publications per year (top) against citations accumulated to date (bottom), sharing one time axis. Deliberately two panels rather than two y-axes: the scales are unrelated, and overlaying them would invent a correlation that is not in the data.",
        },
      ] },
      { h: "h-md", cells: [
        {
          title: "Highest-impact venues", span: 7, data: "publications.top_journals", type: "lollipop",
          desc: "Mean citations per Ersilia article, for venues with at least two Ersilia articles. The two-article floor stops one lucky paper topping the ranking.",
        },
        {
          title: "How the work is framed", span: 5, type: "shares",
          blurb: "Three splits that say what kind of body of work this is.",
          sources: [
            { label: "Direct Ersilia affiliation", data: "publications.affiliation", highlight: "Yes" },
            { label: "African collaboration", data: "publications.by_african_collab", highlight: "Yes" },
            { label: "Primary research", data: "publications.by_type", highlight: "Research" },
          ],
          desc: "Three splits that say what kind of body of work this is. African collaboration is recorded on some papers only; the share is of those where it is recorded.",
        },
      ] },
      { h: "h-md", cells: [
        {
          title: "Research topics", span: 4, data: "publications.by_topic", type: "lollipop",
          desc: "Publications grouped by research topic. A multi-select, so a paper spanning two topics counts in both. Drawn as a ranking rather than a ring because the topic names are long enough that a donut wrapped them into unreadable stacks.",
        },
        {
          title: "Ersilia-affiliated against external, per year", span: 8,
          data: "publications.affiliation_by_year", type: "stackbar",
          desc: "Publications per year split by whether they carry a direct Ersilia affiliation.",
        },
      ] },
    ],
  },
  {
    id: "repositories",
    title: "Code",
    blurb: "Ersilia's open-source repositories. Counts, dates and totals cover all of them; " +
           "anything that names a repository or a contributor covers the public ones only.",
    links: [{ label: "ersilia-os on GitHub", href: "https://github.com/ersilia-os" }],
    headlineKpi: "repositories",
    rows: [
      { h: "h-xl", cells: [
        {
          title: "Popularity against activity", span: 12, data: "repositories.scatter", type: "logscatter",
          scatter: { x: "stars", y: "commits", xLabel: "Stars", yLabel: "Commits" },
          desc: "One dot per public repository: stars against commits, both on logarithmic axes because a handful of repositories account for most of every metric — on linear axes the other 130 collapse into the corner. Dashed lines mark the medians, so the quadrants separate 'popular but quiet' from 'busy but unknown'. Only outliers are labelled.",
        },
      ] },
      { h: "h-xl", cells: [
        {
          title: "Repositories created over time", span: 8, data: "repositories.growth", type: "facets",
          desc: "Every repository by the quarter it was created, public and private alike: new repositories on top, the running total below.",
        },
        {
          title: "Repository make-up", span: 4, type: "shares",
          blurb: "How the repositories split, public against private.",
          sources: [
            { label: "Public", data: "repositories.visibility", highlight: "Public" },
            { label: "Currently in progress", data: "repositories.by_status", highlight: "In progress" },
          ],
          desc: "How the repositories split. The public/private ratio is published deliberately: the honest way to handle an exclusion is to state its size rather than hide it. Private repositories are counted everywhere on this page and named nowhere.",
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
          desc: "One table rather than three ranking charts, so a repository's whole profile sits on one row. Ranked by stars.",
        },
        {
          title: "Commit concentration", span: 5, data: "repositories.contributor_concentration",
          type: "lorenz",
          desc: "Cumulative share of all commits held by the least active repositories. The dashed diagonal is perfect evenness; the further the curve sits below it, the more the work concentrates in a few repositories.",
        },
      ] },
      { h: "h-lg", cells: [
        {
          title: "Contributors by repository count", span: 6, data: "repositories.top_contributors",
          type: "lollipop",
          desc: "Public GitHub handles by how many public Ersilia repositories they have contributed to. Public repository metadata, not community records.",
        },
        {
          title: "Repository type", span: 6, data: "repositories.by_type", type: "treemap",
          desc: "Every repository grouped by type; area is proportional to count. Seven categories with a long tail is more than a donut can carry legibly.",
        },
      ] },
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
          title: "People involved over time", span: 12, data: "community.participation", type: "facets",
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
      { h: "h-lg", cells: [
        {
          title: "What partners work on", span: 5, data: "organisations.by_focus", type: "treemap",
          desc: "Focus areas across the partner network; area is proportional to count. A multi-select, so one organisation contributes to several.",
        },
        {
          title: "Partner organisations", span: 4, data: "organisations.by_type", type: "lollipop",
          desc: "Network organisations grouped by type — foundation, academia, corporate, civil society and so on.",
        },
        {
          title: "How partners are involved", span: 3, data: "organisations.by_classification",
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
          title: "Events over time", span: 7, data: "events.growth", type: "facets",
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
