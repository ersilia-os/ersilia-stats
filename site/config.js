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
  { key: "pypi_downloads", label: "PyPI downloads (incl. CI)" },
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
              desc: "Models by the quarter they were incorporated. Top: added per quarter. Bottom: running total.",
            },
          ] },
          { h: "h-lg", cells: [
            {
              title: "What the models do", span: 8, data: "models.task_tree", type: "treehierarchy",
              desc: "Outer blocks are the model's task, inner blocks its subtask. Each model has one task and one subtask.",
            },
            {
              title: "Curation status", span: 4, data: "models.by_status", type: "donut",
              desc: "Every model in the registry by curation status, including Archived and In progress.",
            },
          ] },
          { h: "h-lg", cells: [
            {
              title: "Pathogens targeted", span: 6, data: "models.by_target_organism", type: "lollipop",
              desc: "Models by target organism. 'Any' and 'Homo sapiens' are left out.",
            },
            {
              title: "Biomedical area", span: 6, data: "models.by_biomedical_area", type: "lollipop",
              desc: "Models by biomedical area. A model can have more than one area and counts in each.",
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
              desc: "Incorporation year minus the publication year of the model's paper. Models incorporated before their publication year count as 0.",
            },
            {
              title: "Is the science peer-reviewed?", span: 4, data: "models.publication_type",
              type: "donut",
              desc: "Publication type of the paper each model is based on.",
            },
            {
              title: "Wraps external work?", span: 4, data: "models.by_source_type", type: "donut",
              desc: "Where each model comes from. Internal: built by Ersilia. External: a third-party model packaged as is. Replicated: a third-party model retrained by Ersilia.",
            },
          ] },
          { h: "h-md", cells: [
            {
              title: "Licences of the underlying models", span: 12, data: "models.by_license",
              type: "treemap",
              desc: "Licence of the original model, not the licence of Ersilia's model repository.",
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
              desc: "Median runtime at each batch size, with the 25th-75th percentile band. Log scale. Runs stopped for taking too long count as slower than any finished run; the 'Not finished' row shows how many at each size.",
            },
          ] },
          { h: "h-lg", cells: [
            {
              title: "The slowest models", span: 12, data: "models.slowest_models",
              type: "runtimelines",
              desc: "Runtime at 10, 100, 1,000 and 10,000 molecules for the six slowest models. Dashed line: Hub median. Triangles: runs that did not finish. Log scales.",
            },
          ] },
          { h: "h-md", cells: [
            {
              title: "When images were last built", span: 3, data: "model_activity.image_freshness",
              type: "column",
              desc: "Year each model's Docker image was last pushed to Docker Hub.",
            },
            {
              title: "How heavy is a model?", span: 6, data: "models.image_size", type: "histogram",
              desc: "Docker image size. Dashed line: mean.",
            },
            {
              title: "ARM64 support", span: 3, type: "shares",
              blurb: "How many models also build for ARM64?",
              sources: [
                { label: "Also builds for ARM64", data: "models.on_arm", highlight: "ARM64 and AMD64" },
              ],
              desc: "Models that publish an ARM64 image in addition to the AMD64 one.",
            },
          ] },
        ],
      },
      {
        title: "Docker Hub demand",
        blurb: "Pull counts from Docker Hub: a floor on interest, not a headcount.",
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
              desc: "Docker Hub pulls to date, ranked by how far each model is above the automated baseline. Only models clearly above it are shown. 'CI test model': pulled by Ersilia's CI on every test run.",
            },
          ] },
          { h: "h-md", cells: [
            {
              title: "Time since last pull", span: 7, data: "usage.pull_dormancy",
              type: "ordinallollipop",
              desc: "Model images by time since their last pull on any tag or architecture, from Docker Hub.",
            },
            {
              title: "ARM64 vs. AMD64 image size", span: 5, data: "usage.arm_vs_amd_size",
              type: "categoryscatter",
              scatter: {
                x: "amd64", y: "arm64", xUnit: "GB", yUnit: "GB",
                xLabel: "AMD64 size (GB)", yLabel: "ARM64 size (GB)",
              },
              desc: "Size of the newest AMD64 image against the newest ARM64 image, for models that publish both.",
            },
          ] },
          { h: "h-md", cells: [
            {
              title: "Last pull, by day of the week", span: 12,
              data: "usage.pull_rhythm_weekday", type: "ordinallollipop",
              desc: "Day of the week (UTC) of each image's most recent pull. Docker Hub only reports the latest pull per digest, so this is not a volume.",
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
              desc: "Commits to the model repositories per quarter, with the running total. The current quarter is partial.",
            },
            {
              title: "Models with an outside contribution", span: 4,
              data: "model_activity.outside_contribution", type: "donut",
              desc: "Models with at least one merged pull request from outside: not a member of the ersilia-os GitHub organisation, not a credited model contributor, not a bot. Based on the last 30 merged pull requests per repository.",
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
              desc: "Commits, pull requests and issues from GitHub, and pulls from Docker Hub, per model repository. Ranked by commits.",
            },
          ] },
          { h: "h-lg", cells: [
            {
              title: "Who gets credited for incorporating a model", span: 12,
              data: "models.top_contributors", type: "lollipop",
              desc: "Models per person in the registry's Contributor field (GitHub handle). A model with two contributors counts for both.",
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
              desc: "Semver bump type (major, minor or patch) of every model release after the first.",
            },
            {
              title: "Model releases over time, hub-wide", span: 7, data: "releases.growth",
              type: "growthcombo",
              desc: "Model releases per quarter since 2026, with the running total. The end-2025 quarter, when every model got its first release, is left out.",
            },
          ] },
          { h: "h-md", cells: [
            {
              title: "Time between a model's releases", span: 12, data: "releases.cadence",
              type: "ordinallollipop",
              desc: "Time between consecutive GitHub releases of the same model.",
            },
          ] },
          { h: "h-lg", cells: [
            {
              title: "Most common packages", span: 12,
              data: "packages.most_common", type: "lollipop",
              desc: "Packages in each model's install.yml, counted once per model. ersilia-pack-utils is left out, and so are models whose install.yml could not be read.",
            },
          ] },
        ],
      },
      {
        title: "Community requests",
        blurb: "How often people ask Ersilia to add a model, and how quickly those requests get answered, from the flagship repository's issue tracker, independent of which models exist yet.",
        rows: [
          { h: "h-lg", cells: [
            {
              title: "Requests to add a model, over time", span: 7,
              data: "model_activity.requests_growth", type: "growthcombo",
              desc: "Model-request issues on the ersilia repository by the quarter they were opened, with the running total.",
            },
            {
              title: "How long a model request takes to close", span: 5,
              data: "model_activity.request_lead_time", type: "ordinallollipop",
              desc: "Days from opening to closing a model-request issue. Closed requests only.",
            },
          ] },
        ],
      },
    ],
  },
  {
    id: "projects",
    title: "Projects",
    blurb: "The project portfolio: what ran when, what overlapped, and what is still open.",
    links: [{ label: "Our work", href: "https://ersilia.io/work" }],
    headlineKpi: "projects",
    rows: [
      { h: "h-tall", cells: [
        {
          title: "Project timeline", span: 12, data: "projects.timeline", type: "gantt",
          desc: "One bar per project from start to end date, coloured by status. Projects with no end date run to today.",
        },
      ] },
      { h: "h-xl", cells: [
        {
          title: "Projects started over time", span: 12, data: "projects.growth", type: "growthcombo",
          desc: "Projects by start year. Top: new per year. Bottom: running total.",
        },
      ] },
      { h: "h-lg", cells: [
        {
          title: "What each project produced", span: 12, data: "projects.outputs",
          type: "ranked", nameLabel: "Project", top: 10, barLabel: "Repos",
          columns: [
            { key: "repositories", label: "Repos" },
            { key: "public", label: "Public" },
            { key: "publications", label: "Papers" },
          ],
          desc: "Repositories and publications linked to each project in Airtable. Bars: repositories, public and private. Projects with neither are left out.",
        },
      ] },
      { h: "h-md", cells: [
        {
          title: "Running at the same time", span: 5, data: "projects.active_over_time", type: "area",
          desc: "Projects running in each quarter: started and not yet ended.",
        },
        {
          title: "Status", span: 4, data: "projects.status", type: "donut",
          desc: "Projects by current status.",
        },
        {
          title: "Median run length", span: 3, data: "projects.duration", type: "meters",
          desc: "Median project length in months, for finished and ongoing projects. Ongoing projects are measured to today.",
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
              desc: "Ersilia-affiliated papers and preprints per year, with the running total.",
            },
            {
              title: "How the work is framed", span: 5, type: "shares",
              blurb: "Two splits that say what kind of body of work this is.",
              sources: [
                { label: "African collaboration", data: "publications.by_african_collab", highlight: "Yes" },
                { label: "Primary research", data: "publications.by_type", highlight: "Research" },
              ],
              desc: "Two splits of the Ersilia-affiliated papers.",
            },
          ] },
          { h: "h-lg", cells: [
            {
              title: "Citations accumulated", span: 7, data: "publications.citation_accrual",
              type: "growthcombo",
              desc: "Citations by the year they were made, from OpenAlex.",
            },
            {
              title: "Research topics", span: 5, data: "publications.by_topic", type: "lollipop",
              desc: "Publications by research topic. A paper can have more than one topic and counts in each.",
            },
          ] },
          { h: "h-lg", cells: [
            {
              title: "Who can read it", span: 4, type: "shares",
              blurb: "Whether the work is behind a paywall.",
              sources: [
                { label: "Open access", data: "publications.open_access", highlight: "Open access" },
              ],
              desc: "Whether each paper is free to read, from OpenAlex.",
            },
            {
              title: "Routes to open access", span: 4, data: "publications.oa_routes", type: "lollipop",
              desc: "How the open papers are open. Gold: published open access. Green: repository copy. Hybrid: open article in a subscription journal. Bronze: free to read at the publisher's discretion.",
            },
            {
              title: "How many countries per paper", span: 4,
              data: "publications.collaboration_breadth", type: "histogram",
              desc: "Papers by the number of distinct countries among their authors' institutions.",
            },
          ] },
          { h: "h-md", cells: [
            {
              title: "Where co-authors are based", span: 12,
              data: "publications.collaboration_countries", type: "lollipop",
              desc: "Countries of the author institutions on Ersilia-affiliated papers, from OpenAlex.",
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
              desc: "Ersilia-affiliated papers ranked by citation count.",
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
              desc: "Papers by people who founded or joined Ersilia that carry no Ersilia affiliation. They are not counted elsewhere on this page.",
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
              desc: "Blog posts per year. Top: per year. Bottom: running total.",
            },
            {
              title: "Post topics", span: 5, data: "blogposts.by_category", type: "treemap",
              desc: "Blog posts by topic category. A post can have more than one category and counts in each.",
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
              desc: "Videos per year by recording date. Top: per year. Bottom: running total.",
            },
            {
              title: "Video topics", span: 5, data: "videos.by_domain", type: "lollipop",
              desc: "Videos by domain. A video can have more than one domain and counts in each.",
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
        blurb: "What the repositories are (type, counts, language), not what they have done.",
        rows: [
          { h: "h-md", cells: [
            {
              title: "Repository type", span: 12, data: "repositories.by_type", type: "treemap",
              desc: "Repositories by type.",
            },
          ] },
          { h: "h-xl", cells: [
            {
              title: "Repositories created over time", span: 8, data: "repositories.growth", type: "growthcombo",
              desc: "Repositories by the quarter they were created, public and private. Top: new per quarter. Bottom: running total.",
            },
            {
              title: "In progress vs completed", span: 4, data: "repositories.progress", type: "donut",
              desc: "Repositories with Airtable status In progress or Completed, public and private. Other statuses are left out.",
            },
          ] },
          { h: "h-md", cells: [
            {
              title: "Languages", span: 12, data: "code.by_language", type: "lollipop",
              desc: "Primary language of each repository as detected by GitHub. Repositories with no detected language are left out.",
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
              desc: "Recently merged pull requests by author, in model repositories and in other repositories. Organisation: a member or collaborator of ersilia-os, in Ersilia's community records, a credited model contributor, or a bot. Outside: everyone else. Based on the last 30 merged pull requests per repository.",
            },
            {
              title: "Commits per quarter", span: 7, data: "code.commit_growth", type: "growthcombo",
              desc: "Commits to every non-archived public repository per quarter, with the running total. The current quarter is partial.",
            },
          ] },
          { h: "h-lg", cells: [
            {
              title: "Stars gained over time", span: 7, data: "code.star_growth", type: "growthcombo",
              desc: "Stars by the quarter they were given, for repositories with more than five stars.",
            },
            {
              title: "When each repository was last updated", span: 5, data: "code.activity_recency",
              type: "ordinallollipop", darkFirst: true,
              desc: "Public repositories, excluding model repositories, by time since their last push. Archived repositories are shown separately.",
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
              desc: "Public repositories, excluding model repositories, ranked by commits. Contributor counts include anonymous contributors.",
            },
            {
              title: "How long issues stay open", span: 5, data: "code.issue_resolution",
              type: "histogram",
              desc: "Repositories by median days to close an issue, over their last 30 closed issues. Repositories with no closed issues are left out.",
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
              desc: "Public repositories ranked by stars, from GitHub.",
            },
            {
              title: "Contributors by repository count", span: 6, data: "repositories.top_contributors",
              type: "lollipop",
              desc: "GitHub users by how many public Ersilia repositories they have contributed to, model repositories included. Bots and anonymous contributors are left out.",
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
              title: "Every package (incl. CI)", span: 12, data: "pypi.packages",
              type: "ranked", nameLabel: "Package", top: 12,
              columns: [
                { key: "window_total", label: "Downloads (window)" },
                { key: "version", label: "Version", raw: true },
                { key: "releases", label: "Releases" },
                { key: "last_30d", label: "Last 30d" },
                { key: "last_7d", label: "Last 7d" },
              ],
              desc: "Downloads include CI: automated installs from test pipelines, Ersilia's and other people's, so they count installs, not people. 'Downloads (window)' is a rolling total from pypistats.org, not a lifetime figure.",
            },
          ] },
          { h: "h-md", cells: [
            {
              title: "Share of downloads", span: 5, data: "pypi.download_share", type: "donut",
              desc: "Each package's share of the download window total in the table above.",
            },
            {
              title: "Downloads, last 30 vs last 7 days", span: 7, data: "pypi.recent_downloads",
              type: "groupbar",
              desc: "Downloads per package in the last 30 and the last 7 days.",
            },
          ] },
          { h: "h-md", cells: [
            {
              title: "First published", span: 6, data: "pypi.first_release_year",
              type: "ordinallollipop",
              desc: "Packages by the year of their first PyPI release.",
            },
            {
              title: "Most recently released", span: 6, data: "pypi.release_recency",
              type: "ordinallollipop",
              desc: "Packages by the year of their latest PyPI release.",
            },
          ] },
          { h: "h-map", cells: [
            {
              title: "Where downloads come from (incl. CI)", span: 12, data: "pypi.downloads_by_country",
              type: "map", mapLabel: "downloads",
              desc: "Downloads include CI: automated installs from test pipelines, Ersilia's and other people's, so they count installs, not people. Covers ersilia and ersilia-pack-utils. Hong Kong and Taiwan do not show on the map; see the list below.",
            },
          ] },
          { h: "h-md", cells: [
            {
              title: "Top countries", span: 12, data: "pypi.top_countries", type: "lollipop",
              desc: "The map's download counts, ranked. Includes Hong Kong and Taiwan, which the map cannot show.",
            },
          ] },
        ],
      },
      {
        title: "Web traffic",
        blurb: "Which repositories GitHub visitors look at, org-wide. GitHub keeps no history here, only a rolling 14-day window.",
        rows: [
          { h: "h-lg", cells: [
            {
              title: "Most-visited repositories", span: 12, data: "traffic.most_visited_repos",
              type: "lollipop",
              desc: "Page views per repository across the organisation, over the last 14 days GitHub reports.",
            },
          ] },
        ],
      },
    ],
  },
  {
    id: "community",
    title: "Community",
    blurb: "The people who have contributed to Ersilia. Aggregate figures only: " +
           "no individual is identifiable anywhere on this site.",
    links: [{ label: "The team", href: "https://ersilia.io/team" }],
    headlineKpi: "community_members",
    rows: [
      { h: "h-xl", cells: [
        {
          title: "People involved over time", span: 12, data: "community.participation", type: "growthcombo",
          desc: "People by the quarter they joined. Top: new per quarter. Bottom: running total.",
        },
      ] },
      { h: "h-lg", cells: [
        {
          title: "Engagement duration", span: 5, data: "community.duration_buckets", type: "ordinallollipop",
          desc: "Completed collaborations by length. Current members are not counted.",
        },
        {
          title: "Roles held", span: 4, data: "community.roles", type: "lollipop",
          desc: "Roles across the community. A person can hold more than one role and counts in each.",
        },
        {
          title: "Composition", span: 3, type: "shares",
          blurb: "Aggregate composition only.",
          sources: [
            { label: "Still involved", data: "community.active_status", highlight: "Active" },
            { label: "Female", data: "community.by_gender", highlight: "Female" },
          ],
          desc: "Share of community members still involved, and share who are female.",
        },
      ] },
      { h: "h-lg", cells: [
        {
          title: "Countries represented", span: 6, data: "community.by_country", type: "lollipop",
          desc: "Community members by country of residence.",
        },
        {
          title: "Home organisations", span: 6, data: "community.by_organisation", type: "lollipop",
          desc: "Organisations community members came from.",
        },
      ] },
    ],
  },
  {
    id: "partners",
    title: "Partners",
    blurb: "The organisations Ersilia has run projects with, where they and the community " +
           "are, and the events Ersilia takes part in, many of them co-organised with partners.",
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
              desc: "Countries by the number of partners, community members or events there. A partner is an organisation Ersilia has done a project with.",
            },
          ] },
          { h: "h-sm", cells: [
            {
              title: "Global South and North", span: 4, data: "reach.south_north", type: "shares",
              blurb: "Engaged countries by World Bank income group.",
              sources: [{ label: "Global South", data: "reach.south_north", highlight: "Global South" }],
              desc: "Countries with partners, community members or events, by World Bank income group: LIC, LMIC and UMIC as Global South, HIC as Global North. Countries with no income group are left out.",
            },
            {
              title: "By income group", span: 4, data: "reach.engagement_by_income_group",
              type: "ordinallollipop",
              desc: "Countries with partners, community members or events, by World Bank income group.",
            },
            {
              title: "By world region", span: 4, data: "reach.engagement_by_region", type: "donut",
              desc: "Countries with partners, community members or events, by world region.",
            },
          ] },
          { h: "h-md", cells: [
            {
              title: "By subregion", span: 12, data: "reach.engagement_by_subregion",
              type: "lollipop",
              desc: "Countries with partners, community members or events, by UN subregion.",
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
              desc: "Events per year. Top: per year. Bottom: running total.",
            },
            {
              title: "Online or in person", span: 4, data: "events.by_format", type: "donut",
              desc: "Events by format.",
            },
          ] },
          { h: "h-lg", cells: [
            {
              title: "Type of event", span: 4, data: "events.by_type", type: "lollipop",
              desc: "Events by type: talk, conference, training or other.",
            },
            {
              title: "Where events took place", span: 4, data: "events.by_country", type: "lollipop",
              desc: "Events by country.",
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
