/* Declarative dashboard definition.

   One entry per view; each view has ONE lead chart answering its primary
   question, then supporting charts on a 12-column grid (span 4 / 6 / 8 / 12).
   `data` is a dot path under `sections` in data/stats.json; `type` picks a
   builder in js/charts.js; `desc` is the methodology note behind the ⓘ.

   Colour note: sections no longer carry a decorative hue. Periwinkle carries all
   interaction and plum is the identity signature; the data hues live inside the
   charts, where they encode a variable. Six flat accent colours spread across the
   chrome read as noise, which is the house rule this replaces.

   Form notes worth keeping in mind when editing:
     - two categories are a `share` bar, never a 2-slice donut;
     - more than ~6 categories is an `hbar`, not a donut;
     - ordered buckets use `ordinalbar` (one-hue ramp) so the order shows;
     - two measures of different scale use `facets`, never a second y-axis. */

const PRIMARY_KPIS = [
  { key: "models", label: "Models in the Hub" },
  { key: "community_members", label: "People involved" },
  { key: "repositories", label: "Public repositories" },
  { key: "total_citations", label: "Citations", note: "across all publications" },
];

// Shown when the Models table has not been fetched yet, so the hero row still
// has four tiles rather than a gap.
const PRIMARY_KPIS_FALLBACK = [
  { key: "community_members", label: "People involved" },
  { key: "repositories", label: "Public repositories" },
  { key: "publications", label: "Publications" },
  { key: "total_citations", label: "Citations", note: "across all publications" },
];

const SECONDARY_KPIS = [
  { key: "projects", label: "Projects" },
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
    blurb: "The Ersilia Model Hub — what is in it, and how ready it is to run.",
    headlineKpi: "models",
    takeaway: "models published for reuse",
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
        title: "What the models do", data: "models.task_tree", type: "sunburst",
        span: 6, height: "h-lg",
        desc: "Inner ring is the model's task, outer ring its subtask. Both are single-valued, so every model sits on exactly one leaf and the rings sum to the model count.",
      },
      {
        title: "Curation status by cohort", data: "models.cohorts_by_status", type: "stackbar",
        span: 6, height: "h-lg",
        desc: "Each quarter's incorporated models, split by curation status. Shows whether older cohorts were finished or left behind.",
      },
      {
        title: "Biomedical area", data: "models.by_biomedical_area", type: "hbar",
        span: 8, height: "h-lg",
        desc: "What each model is for. This is the most mission-relevant cut the Hub records: Ersilia works on antimicrobial and antipathogen drug discovery, and this says how much of the Hub serves a named disease versus general-purpose chemistry. A multi-select, so a model spanning two areas counts in both.",
      },
      {
        title: "Status", data: "models.by_status", type: "donut", span: 4,
        desc: "All models grouped by curation status. Colours follow the house status scale.",
      },
      {
        title: "Licences", data: "models.by_license", type: "hbar", span: 4,
        desc: "Licence recorded for each model. Models with no licence on file are not counted.",
      },
      {
        title: "Where models can be run", data: "models.coverage", type: "hbar", span: 4,
        desc: "How many models have each distribution route on file — a Docker image, an S3 bundle, or source code.",
      },
      {
        title: "Built in-house or wrapped", data: "models.by_source_type", type: "hbar",
        span: 4,
        desc: "Whether a model was developed by Ersilia or packaged from externally published work. Wrapping external models is much of what the Hub is for.",
      },
    ],
  },
  {
    id: "projects",
    title: "Projects",
    blurb: "Ersilia's research and delivery projects, and how they overlap.",
    headlineKpi: "projects",
    takeaway: "projects tracked end to end",
    charts: [
      {
        title: "Project timeline", data: "projects.timeline", type: "gantt",
        lead: true, span: 12, height: "h-tall",
        desc: "One bar per project from start to end date, coloured by status, against a 'today' rule. Projects with no end date are drawn to today and marked open.",
      },
      {
        title: "Projects running concurrently", data: "projects.active_over_time", type: "area",
        span: 8, desc: "Projects started and not yet ended, counted in each quarter.",
      },
      {
        title: "Status", data: "projects.status", type: "donut", span: 4,
        desc: "All projects by current status. Colours follow the house status scale and match the timeline.",
      },
      {
        title: "Projects started per year", data: "projects.per_year", type: "bar", span: 6,
        desc: "Projects by the calendar year they started.",
      },
      {
        title: "Median run length", data: "projects.duration", type: "bar", span: 6,
        desc: "Median months per project, split between finished projects and those still running. Running projects are measured to today, so their figure is a floor.",
      },
    ],
  },
  {
    id: "publications",
    title: "Publications",
    blurb: "Peer-reviewed papers and preprints linked to Ersilia, and their reach.",
    headlineKpi: "publications",
    takeaway: "papers and preprints",
    charts: [
      {
        title: "Output and accumulated citations", data: "publications.output_and_impact", type: "facets",
        lead: true, span: 12, height: "h-xl",
        desc: "Publications per year (top) against citations accumulated to date (bottom), sharing one time axis. Deliberately two panels rather than two y-axes: the scales are unrelated, and overlaying them would invent a correlation.",
      },
      {
        title: "Citations by publication year", data: "publications.citations_per_year", type: "bar",
        span: 8, desc: "Citations summed by the year the cited paper appeared — older cohorts have had longer to accrue them.",
      },
      {
        title: "Ersilia affiliation", data: "publications.affiliation", type: "share", span: 4,
        height: "h-xs", desc: "Share of publications with a direct Ersilia affiliation, versus work by collaborators and advisors.",
      },
      {
        title: "Highest-impact venues", data: "publications.top_journals", type: "hbar",
        span: 8, desc: "Mean citations per Ersilia article, for venues with at least two Ersilia articles. The two-article floor keeps a single lucky paper from topping the ranking.",
      },
      {
        title: "African collaboration", data: "publications.by_african_collab", type: "share",
        span: 4, height: "h-xs",
        desc: "Publications involving an African collaboration, among those where the field is recorded. Not recorded on every paper.",
      },
      {
        title: "Ersilia-affiliated vs external, per year", data: "publications.affiliation_by_year",
        type: "stackbar", span: 8,
        desc: "Publications per year split by whether they carry a direct Ersilia affiliation.",
      },
      {
        title: "Research topics", data: "publications.by_topic", type: "hbar", span: 4,
        desc: "Publications grouped by research topic. Topic is a multi-select.",
      },
      {
        title: "Publications per year", data: "publications.per_year", type: "bar", span: 6,
        desc: "Papers and preprints by year of publication — the top panel of the lead chart, on its own scale.",
      },
      {
        title: "Research versus review", data: "publications.by_type", type: "share",
        span: 6, height: "h-xs",
        desc: "Split between primary research and review articles.",
      },
    ],
  },
  {
    id: "repositories",
    title: "Code",
    blurb: "Ersilia's public open-source repositories, their reach and their health. " +
           "Private repositories are excluded — their names alone would be disclosure.",
    headlineKpi: "repositories",
    takeaway: "public repositories on GitHub",
    charts: [
      {
        title: "Popularity against activity", data: "repositories.health", type: "smallmultiples",
        lead: true, span: 12, height: "h-tall",
        desc: "The same repositories under four metric pairs. Popularity (stars, forks, watchers) and development activity (commits, open issues) are different things; plotting them against each other exposes the repositories where they disagree. Both distributions are heavily skewed — a handful of repositories account for most of every metric — so most points cluster near the origin and the axes are linear rather than rescaled to hide that.",
      },
      {
        title: "Repositories over time", data: "repositories.cumulative", type: "area",
        span: 8,
        toggles: [
          { label: "Cumulative", data: "repositories.cumulative" },
          { label: "Per quarter", data: "repositories.per_quarter" },
        ],
        desc: "Public repositories by the quarter they were created.",
      },
      {
        title: "Commit concentration", data: "repositories.contributor_concentration", type: "lorenz",
        span: 4, desc: "Cumulative share of all commits held by the least active repositories. The straight line is perfect evenness; the further the curve sits below it, the more the work concentrates in a few repositories.",
      },
      {
        title: "Most starred", data: "repositories.top_by_stars", type: "hbar", span: 6,
        desc: "Public repositories ranked by GitHub stars.",
      },
      {
        title: "Most forked", data: "repositories.top_by_forks", type: "hbar", span: 6,
        desc: "Public repositories ranked by forks — a better signal of reuse than stars, which cost nothing.",
      },
      {
        title: "Stars, forks and contributors", data: "repositories.scatter", type: "scatter",
        span: 6, height: "h-lg",
        scatter: { x: "stars", y: "forks", size: "contributors", xLabel: "Stars", yLabel: "Forks", sizeLabel: "contributors" },
        desc: "One dot per public repository: stars against forks, sized by number of contributors. Only the extremes are labelled; hover or open the table for the rest.",
      },
      {
        title: "Contributors by repository count", data: "repositories.top_contributors", type: "hbar",
        span: 6, desc: "Public GitHub handles by how many public Ersilia repositories they have contributed to. These are public repository contributions, not community records.",
      },
      {
        title: "Most collaborative repositories", data: "repositories.most_collaborative", type: "hbar",
        span: 6, desc: "Public repositories with the most individual contributors.",
      },
      {
        title: "Repository type", data: "repositories.by_type", type: "hbar", span: 6,
        desc: "Public repositories grouped by type — package, model, analysis, app, template and so on.",
      },
      {
        title: "Maintenance status", data: "repositories.by_status", type: "hbar", span: 6,
        desc: "Public repositories grouped by maintenance status.",
      },
    ],
  },
  {
    id: "community",
    title: "Community",
    blurb: "The people who have contributed to Ersilia. Aggregate figures only — " +
           "no individual is identifiable anywhere on this site.",
    headlineKpi: "community_members",
    takeaway: "people have contributed",
    charts: [
      {
        title: "Joiners, leavers and net change", data: "community.flow", type: "groupbar",
        lead: true, span: 12, height: "h-lg",
        desc: "People who joined versus people whose involvement ended, each quarter, with the net change as a line. Answers whether the community is compounding or recycling.",
      },
      {
        title: "Community over time", data: "community.growth", type: "area", span: 8,
        desc: "Cumulative count of everyone who has ever joined, by the quarter they started. It only goes up — it is a total, not a headcount.",
      },
      {
        title: "Still involved", data: "community.active_status", type: "share", span: 4,
        height: "h-xs", desc: "People currently involved versus those whose collaboration has ended.",
      },
      {
        title: "How long collaborations last", data: "community.tenure", type: "histogram",
        span: 8, desc: "Completed collaborations binned by length in months, with the mean marked. People still involved are excluded — including them would drag every long tenure down.",
      },
      {
        title: "Involvement length", data: "community.duration_buckets", type: "ordinalbar",
        span: 4, desc: "Completed collaborations in four bands. Ordered bands, so the colour ramp follows the order.",
      },
      {
        title: "Cohort retention", data: "community.retention", type: "heatmap",
        span: 8, height: "h-lg",
        desc: "For each joining year, the share still involved at 3, 6, 12 and 24 months. A cohort only counts towards a horizon once it is old enough to judge, so recent years have blank cells rather than misleading zeroes.",
      },
      {
        title: "Roles held", data: "community.roles", type: "hbar", span: 4,
        desc: "Roles across the community. Roles are a multi-select — someone who was both mentor and maintainer counts in both, so shares sum above 100%.",
      },
      {
        title: "Countries represented", data: "community.by_country", type: "hbar", span: 6,
        desc: "Community members grouped by country of residence, as recorded.",
      },
      {
        title: "Gender", data: "community.by_gender", type: "share", span: 6, height: "h-xs",
        desc: "Recorded gender across the community, in aggregate only. Reported because representation is something Ersilia holds itself to.",
      },
      {
        title: "Home institutions", data: "community.by_organisation", type: "hbar", span: 12,
        desc: "Where community members come from. Institution names only — no individual is named.",
      },
    ],
  },
  {
    id: "reach",
    title: "Global reach",
    blurb: "Where Ersilia actually works, and how that maps onto the Global South " +
           "mission it states.",
    headlineKpi: "countries_represented",
    takeaway: "countries with people or events",
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
        desc: "Countries shaded by how many partner organisations, community members or events are recorded there. Countries with no record keep the neutral fill rather than being shaded as zero.",
      },
      {
        title: "Global South and North", data: "reach.south_north", type: "share",
        span: 6, height: "h-xs",
        desc: "Engaged countries split by World Bank income group: LIC, LMIC and UMIC counted as Global South, HIC as Global North. Countries with no income group recorded are excluded.",
      },
      {
        title: "By income group", data: "reach.engagement_by_income_group", type: "ordinalbar",
        span: 6, desc: "Countries Ersilia engages with, by World Bank income group. Ordered from low to high income, so the ramp follows the order.",
      },
      {
        title: "By world region", data: "reach.engagement_by_region", type: "hbar", span: 6,
        desc: "Countries Ersilia engages with, grouped by world region.",
      },
      {
        title: "Partner organisations by country", data: "organisations.by_country", type: "hbar",
        span: 6, desc: "Organisations in Ersilia's network, by the country on file.",
      },
      {
        title: "Organisation type", data: "organisations.by_type", type: "hbar", span: 6,
        desc: "Network organisations grouped by type — foundation, academia, corporate, civil society and so on.",
      },
      {
        title: "Focus areas", data: "organisations.by_focus", type: "hbar", span: 6,
        desc: "What partner organisations work on. A multi-select, so one organisation contributes to several.",
      },
      {
        title: "How partners relate to Ersilia", data: "organisations.by_classification",
        type: "hbar", span: 6,
        desc: "Each organisation classified as funder, network or collaborator.",
      },
    ],
  },
  {
    id: "outreach",
    title: "Outreach",
    blurb: "Events Ersilia convened or took part in, and what it publishes.",
    headlineKpi: "events",
    takeaway: "events attended or hosted",
    charts: [
      {
        title: "Events per year", data: "events.per_year", type: "bar",
        lead: true, span: 12, height: "h-lg",
        desc: "Talks, workshops and conferences per year. Counted from the event date on file.",
      },
      {
        title: "Events by host country", data: "events.by_country", type: "hbar", span: 6,
        desc: "Events grouped by host country. Many events are online and have no country recorded.",
      },
      {
        title: "Who convened them", data: "events.by_organiser", type: "hbar", span: 6,
        desc: "Organisations that convened the most events Ersilia took part in.",
      },
      {
        title: "Blog posts per year", data: "blogposts.per_year", type: "bar", span: 6,
        desc: "Posts published per year, on Ersilia's own channels and elsewhere.",
      },
      {
        title: "Where posts appear", data: "blogposts.by_publisher", type: "share", span: 6,
        height: "h-xs", desc: "Posts on Ersilia's own channels versus those published by others.",
      },
      {
        title: "Post topics", data: "blogposts.by_category", type: "hbar", span: 12,
        desc: "Blog posts grouped by topic category. Category is a multi-select.",
      },
    ],
  },
  {
    id: "data",
    title: "Data quality",
    blurb: "Every chart on this site is only as good as the registry behind it. " +
           "This is what that registry looks like.",
    headlineKpi: null,
    charts: [
      {
        title: "Field completeness by table", data: "quality.completeness", type: "hbar",
        lead: true, span: 12, height: "h-lg", unit: "%",
        desc: "Mean share of populated cells per source table, thinnest first. A thin table produces short charts elsewhere on this site.",
      },
      {
        title: "Project status against repository status", data: "quality.project_repo_status",
        type: "heatmap", span: 8, height: "h-lg",
        desc: "Every repository-to-project link, cross-tabulated by both statuses. Off-diagonal cells are inconsistencies worth fixing — an open repository under a finished project, for instance.",
      },
      {
        title: "Rows per table", data: "quality.table_sizes", type: "hbar", span: 4,
        height: "h-lg", desc: "Record count per source table in this snapshot.",
      },
      {
        title: "Thinnest fields", data: "quality.thin_fields", type: "hbar",
        span: 12, height: "h-xl", unit: "%",
        desc: "Every field under 80% populated, thinnest first. These are the fields to fix in Airtable if a chart elsewhere looks short.",
        emptyNote: "Every field is at least 80% populated.",
      },
      {
        title: "All countries by income group", data: "reach.reference_by_income_group",
        type: "ordinalbar", span: 6,
        desc: "The full reference table's composition, for comparison with the countries Ersilia actually engages with on the Global reach view.",
      },
    ],
  },
];
