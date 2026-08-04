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
            { label: "Permissively licensed", data: "models.licence_openness", highlight: "Permissive" },
          ],
          desc: "Three things about how the Hub is assembled and who can reuse it. How much packages externally published models rather than Ersilia's own; how much builds for ARM64 as well as AMD64, ARM being the cheap low-power hardware; and how much carries a permissive licence — MIT, Apache, BSD or CC0/CC-BY — as against a licence that imposes conditions, which covers GPL, AGPL, LGPL, proprietary and the non-commercial or no-derivatives Creative Commons variants. The share is of the models that record a licence at all; 40 record none, which for a reuser is the most restrictive state of the three.",
        },
      ] },
      { h: "h-md", cells: [
        {
          title: "Same answer twice?", span: 4, data: "models.output_consistency", type: "donut",
          desc: "Whether a model returns the same output for the same input on a re-run, as recorded in the registry. This is arguably the most consequential property on this page and it was previously shown nowhere: everything else here says what a model is for, this says whether you can rely on what it tells you. Variable is not a defect — a generative model that samples is supposed to vary — so no verdict is attached to it; for a property predictor the same value would be a problem. Ten models record no value and are excluded from the share.",
        },
        {
          title: "Is the science peer-reviewed?", span: 4, data: "models.publication_type",
          type: "lollipop",
          desc: "The publication type of the work each model is based on. Provenance rather than popularity, and the counterpart to the wrapped-work figure above: that says whether Ersilia packaged somebody else's model, this says how well established that model's science is. Preprints are counted separately from peer-reviewed work rather than folded in with it.",
        },
        {
          title: "Licences of the underlying models", span: 4, data: "models.by_license",
          type: "treemap",
          desc: "The licence of each wrapped model as recorded in the registry — NOT the licence of Ersilia's wrapper repository, which is GPL-3.0 on 227 of 241 model repositories and is shown on the Code page. The two answer different questions and genuinely differ: the upstream models spread across MIT, both GPL-3.0 variants, Apache-2.0 and BSD-3-Clause, and it is the upstream terms that govern what a reuser may do with the underlying science. 40 models record no licence, which for a reuser is the most restrictive state of all.",
        },
      ] },
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
          title: "When images were last built", span: 3, data: "model_activity.image_freshness",
          type: "column",
          desc: "The year each model's Docker image was last pushed. This is BUILD recency and not maintenance or demand: the pull-count evidence elsewhere on this page shows that continuous integration pulls every image on a schedule, and that same schedule is what rebuilds them. It sits beside the push chart because the two can disagree, and the disagreement is the useful part — a model whose repository changed this year but whose image is a year old has a packaging problem that neither figure reveals alone.",
        },
      ] },
      { h: "h-lg", cells: [
        {
          title: "Models with an outside contribution", span: 5,
          data: "model_activity.outside_contribution", type: "donut",
          desc: "Counted per model, not per pull request, and that is the point: '78% of merged pull requests come from outside Ersilia' could in principle be a handful of models attracting all the outside work. This counts the models themselves, so it measures how far community contribution actually reaches into the Hub. Only the most recent 30 merged pull requests per repository are sampled, so a model whose only outside contribution is older reads as internal — the figure is a floor, not a ceiling.",
        },
        {
          title: "Busiest model repositories", span: 7, data: "model_activity.most_active_models",
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
          title: "Most pulled models", span: 5, data: "usage.most_pulled_models",
          type: "ranked", nameLabel: "Model", top: 10,
          columns: [
            { key: "pulls", label: "Pulls" },
            { key: "times_baseline", label: "× baseline", raw: true },
          ],
          desc: "Docker Hub pull counts, ranked by how far each model exceeds the automated baseline rather than by raw pulls — ranking by raw pulls would rank the build schedule. Only models clearly above the baseline appear. A pull is not a user: mirrors pull images, and one person testing in a loop pulls repeatedly. It is a floor on interest, not a headcount, and Docker Hub publishes no history, so these are totals to date and cannot be turned into a rate.",
        },
        {
          title: "Pull count distribution", span: 4, data: "usage.pull_distribution",
          type: "histogram",
          desc: "Why the headline pull total is not a usage figure, shown rather than asserted. Across the model images the counts cluster in one narrow band with a standard deviation of about 400 — human demand does not look like that, it follows a power law, which is exactly what the same organisation's GitHub stars do. A near-uniform floor on almost every image is the signature of continuous integration pulling every image on a schedule. The thin tail above the cluster is the part that reflects interest.",
        },
        {
          title: "Models with a published image", span: 3, data: "usage.image_coverage",
          type: "donut",
          desc: "Whether each model in the registry has a matching Docker image on Docker Hub. A model with no image cannot be run by the usual route, so this is a completeness check on the Hub rather than a popularity measure. The mismatch runs both ways and both directions are worth knowing: a handful of published images have no model record at all, which means they are undocumented rather than missing. Infrastructure images — base, conda, shell — are excluded from every figure here: they are pulled as a side effect of running a model rather than chosen, and base alone would inflate the total by roughly 14%.",
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
    blurb: "Peer-reviewed papers and preprints linked to Ersilia, and how far they reach.",
    links: [{ label: "Publications", href: "https://ersilia.io/publications" }],
    headlineKpi: "publications",
    rows: [
      { h: "h-lg", cells: [
        {
          title: "Publications over time", span: 7, data: "publications.growth", type: "growthcombo",
          desc: "Papers and preprints by year of publication: bars for the year, a line for the running total. The bars can be hidden from the legend to read the total on its own.",
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
          desc: "Publications per year split by whether they carry a direct Ersilia affiliation.",
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
          desc: "Individual papers ranked by citation count. The Ersilia column is the point of this table rather than an aside: the four most-cited papers here carry no direct Ersilia affiliation — they are earlier work by people who later founded or joined Ersilia — and the most-cited affiliated paper has 53 citations. Ranking by citations alone under an Ersilia heading would claim credit the data does not support, and quietly dropping the unaffiliated papers would hide that the distinction exists.",
        },
      ] },
    ],
  },
  {
    id: "repositories",
    title: "Code",
    blurb: "Ersilia's open-source repositories, and what is actually happening inside them. " +
           "Counts, dates and totals cover all of them; anything that names a repository or a " +
           "contributor covers the public ones only. The activity figures come from GitHub " +
           "directly rather than from a stored total, which is why they can be shown by quarter.",
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
          title: "When each repository last released", span: 5, data: "code.release_recency",
          type: "ordinallollipop",
          desc: "Repositories by the year of their most recent release. Read this carefully, because the obvious reading is wrong: 164 repositories last releasing in 2025 against 72 in 2026 looks like releasing is slowing, and it is not evidence of that. 139 of 384 repositories have never cut a release at all, and most that do release do so rarely — a repository sitting on a 2025 tag is usually one that ships when there is something to ship, not one that stopped. The never-released group is a bar here rather than an omission, because without it the chart would describe 245 repositories while appearing to describe all of them.",
        },
        {
          title: "Contributors by repository count", span: 7, data: "repositories.top_contributors",
          type: "lollipop",
          desc: "Public GitHub handles by how many public Ersilia repositories they have contributed to. Public repository metadata, not community records.",
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
          title: "Work behind each model", span: 4, data: "code.model_commit_effort",
          type: "histogram",
          desc: "Commits per per-model repository, bucketed. Included to answer a fair question about a hub of a few hundred models: is each one a file drop? The distribution is the answer.",
        },
        {
          title: "Languages", span: 4, data: "code.by_language", type: "lollipop",
          desc: "GitHub's detected primary language per repository, which is a guess based on file extensions and counts one language per repository however many it contains. Repositories with no detectable language are excluded, so the total is smaller than the repository count.",
        },
        {
          title: "How the code is licensed", span: 4, data: "code.by_licence", type: "donut",
          desc: "SPDX identifiers as GitHub reports them, read from each repository's licence file rather than from any hand-entered field. Ersilia standardises on GPL-3.0 across both the tooling and the per-model repositories — 227 of 241 model repositories carry it. Do not read this as the models' own licensing: the Model Hub page reports licence openness from the registry, and that describes the terms of the upstream model being wrapped, which is a different question with a genuinely different answer.",
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
