/* Entry point: load stats.json, register the routes, render.

   Views, in order of hierarchy:
     #/            landing — four headline tiles, one flagship chart, jump cards
     #/<section>    one section: lead chart, then supporting charts
     #/downloads    every aggregate as CSV
   Plus a Methods modal, reachable from every view. */

let DATA = null;

/* ------------------------------------------------------------- landing */
function renderLanding(outlet, registry) {
  const head = el("div", "viewhead");
  head.appendChild(el("h2", null, "Ersilia in numbers"));
  head.appendChild(el("p", "lede",
    "Aggregate statistics for the Ersilia Open Source Initiative — the Model Hub, " +
    "the people behind it, the code, the science and the countries it reaches. " +
    "Figures are a snapshot; nothing here identifies an individual."));
  outlet.appendChild(head);

  const primary = DATA.kpis.models ? PRIMARY_KPIS : PRIMARY_KPIS_FALLBACK;
  outlet.appendChild(statRow(DATA.kpis, primary, "primary", "hero"));

  // Flagship chart: four measures of wildly different magnitude, indexed to a
  // common base (share of today's total) so they share one honest axis.
  const growth = buildGrowthIndex();
  if (growth) {
    const card = chartCard({
      title: "How Ersilia has grown",
      type: "growth", lead: true, span: 12, height: "h-lg",
      desc: "Each measure as a share of its own total today, so four series of very " +
            "different size share one axis. A steep line means that measure grew fast " +
            "in that period; a flat one means it stalled.",
      data: "__growth",
    }, { sections: { __growth: growth } }, registry);
    const grid = el("div", "chart-grid");
    grid.appendChild(card);
    outlet.appendChild(grid);
  }

  const secondary = el("div", "section");
  secondary.appendChild(el("h2", null, "Also tracked"));
  secondary.appendChild(statRow(DATA.kpis, SECONDARY_KPIS, "", "small"));
  outlet.appendChild(secondary);

  const explore = el("div", "section");
  explore.appendChild(el("h2", null, "Explore"));
  const jumps = el("div", "jump-grid");
  VIEWS.forEach((view) => {
    const link = el("a", "jump");
    link.href = "#/" + view.id;
    const title = el("div", "t");
    title.appendChild(el("span", null, view.title));
    const kpi = view.headlineKpi && DATA.kpis[view.headlineKpi];
    if (kpi) title.appendChild(el("span", "n", fmtNum(kpi.value)));
    link.appendChild(title);
    link.appendChild(el("div", "s", viewTakeaway(view)));
    jumps.appendChild(link);
  });
  explore.appendChild(jumps);
  outlet.appendChild(explore);
}

/* The jump card's one-liner: prefer the lead chart's computed takeaway over the
   static blurb, so the landing page says something current. */
function viewTakeaway(view) {
  const lead = view.charts.find((c) => c.lead) || view.charts[0];
  const metric = lead && getByPath(DATA.sections, lead.data);
  if (metric && metric.insight) return metric.insight;
  return view.blurb;
}

/* Index each cumulative series to its own final value. */
function buildGrowthIndex() {
  const wanted = [
    { key: "models", name: "Models" },
    { key: "repositories", name: "Repositories" },
    { key: "community_members", name: "People" },
    { key: "projects", name: "Projects" },
  ];
  const available = wanted.filter((w) => {
    const kpi = DATA.kpis[w.key];
    return kpi && kpi.series && kpi.series.labels && kpi.series.labels.length > 2;
  });
  if (available.length < 2) return null;

  // Union of every quarter label, in order, so the series share one axis.
  const labels = Array.from(new Set(
    available.flatMap((w) => DATA.kpis[w.key].series.labels)
  )).sort();

  const series = available.map((w) => {
    const source = DATA.kpis[w.key].series;
    const lookup = new Map(source.labels.map((l, i) => [l, source.values[i]]));
    const total = source.values[source.values.length - 1] || 1;
    let carried = null;
    const values = labels.map((label) => {
      if (lookup.has(label)) carried = lookup.get(label);
      // Before a measure starts, leave a gap rather than drawing a false zero.
      return carried == null ? null : Math.round(1000 * carried / total) / 10;
    });
    return { name: w.name, values: values };
  });

  return {
    labels: labels,
    series: series,
    n: available.length,
    insight: "Each line is that measure as a percentage of where it stands today (" +
      available.map((w) => w.name.toLowerCase() + " " + fmtNum(DATA.kpis[w.key].value)).join(", ") + ").",
  };
}

/* ------------------------------------------------------------- sections */
function renderView(view) {
  return function (outlet, registry) {
    const head = el("div", "viewhead");
    head.appendChild(el("h2", null, view.title));
    head.appendChild(el("p", null, view.blurb));
    outlet.appendChild(head);

    if (view.id === "models" && !DATA.meta.models_available) {
      const note = el("div", "wip",
        "The Models table has not been fetched into this snapshot yet, so this view is empty.");
      note.style.marginBottom = "16px";
      outlet.appendChild(note);
    }

    if (view.id === "data") {
      const note = el("div", "wip", "Snapshot " + (DATA.snapshot_date || "unknown") +
        " · " + DATA.meta.tables.length + " source tables");
      note.style.marginBottom = "16px";
      outlet.appendChild(note);
    }

    const grid = el("div", "chart-grid");
    view.charts.forEach((chart) => grid.appendChild(chartCard(chart, DATA, registry)));
    outlet.appendChild(grid);

    if (view.id === "repositories" && DATA.meta.private_repositories_excluded) {
      outlet.appendChild(el("p", "insight",
        DATA.meta.private_repositories_excluded +
        " private repositories are excluded from every figure on this page."));
    }
  };
}

/* ------------------------------------------------------------ downloads */
function renderDownloads(outlet) {
  const head = el("div", "viewhead");
  head.appendChild(el("h2", null, "Downloads"));
  head.appendChild(el("p", null,
    "The aggregate table behind every chart, as CSV, plus the full dataset as JSON. " +
    "Aggregates only — the same guarantee as the charts."));
  outlet.appendChild(head);

  const card = el("div", "card");
  const grid = el("div", "dl-grid");

  const overview = el("div", "dl-group");
  overview.appendChild(el("h4", null, "Everything"));
  const links = el("div", "dl-links");
  links.appendChild(downloadLink("data/tables/kpis.csv", "Headline figures"));
  links.appendChild(downloadLink("data/stats.json", "Full dataset (JSON)"));
  overview.appendChild(links);
  grid.appendChild(overview);

  VIEWS.forEach((view) => {
    const group = el("div", "dl-group");
    group.appendChild(el("h4", null, view.title));
    const list = el("div", "dl-links");
    const seen = new Set();
    view.charts.forEach((chart) => {
      const sources = chart.toggles && chart.toggles.length
        ? chart.toggles
        : [{ label: null, data: chart.data }];
      sources.forEach((source) => {
        if (!source.data || seen.has(source.data)) return;
        const metric = getByPath(DATA.sections, source.data);
        if (!hasData(chart, metric)) return;
        seen.add(source.data);
        list.appendChild(downloadLink(csvFor(source.data),
          source.label ? chart.title + " — " + source.label : chart.title));
      });
    });
    if (!list.childNodes.length) return;
    group.appendChild(list);
    grid.appendChild(group);
  });

  card.appendChild(grid);
  outlet.appendChild(card);
}

function downloadLink(href, label) {
  const link = el("a", "dl", label);
  link.href = href;
  link.setAttribute("download", "");
  return link;
}

/* -------------------------------------------------------------- methods */
function fillMethods() {
  const body = document.getElementById("methods-body");
  const rows = [
    ["Source", "Every figure comes from Ersilia's own Airtable — projects, community, " +
      "publications, repositories, organisations, events, blog posts and countries — " +
      "exported read-only to CSV snapshots held in the repository. Snapshot: " +
      (DATA.snapshot_date || "unknown") + ". Built: " + (DATA.generated_at || "unknown") + "."],
    ["Aggregates only", "Nothing on this site is row-level personal data. The community " +
      "table's names, emails and social handles are dropped when the snapshot is fetched, " +
      "dropped again when it is read, and the build aborts if anything email-shaped reaches " +
      "the output."],
    ["Private repositories", "The repository figures cover public repositories only. " +
      DATA.meta.private_repositories_excluded + " private repositories are excluded, because " +
      "a private repository's name is itself disclosure."],
    ["Multi-select fields", "Roles, tags, topics, categories and focus areas allow several " +
      "values per record. Those charts count assignments, not records, so their shares can " +
      "sum above 100%. Each chart says so where it matters."],
    ["Journal ranking", "Venues are ranked by mean citations per Ersilia article and need at " +
      "least two Ersilia articles to appear. Without that floor a single well-cited paper " +
      "tops the ranking and says nothing about the venue."],
    ["Global South", "Taken from the World Bank income group on the Countries table: LIC, " +
      "LMIC and UMIC counted as Global South, HIC as Global North. Countries with no income " +
      "group recorded are excluded rather than assumed."],
    ["Retention", "A joining cohort counts towards a retention horizon only once it is old " +
      "enough to judge — someone who joined two months ago is not evidence about 3-month " +
      "retention. Cells with no judgeable members are left blank."],
    ["Small numbers", "Percentages are suppressed below n=10, where a share invites a " +
      "conclusion the sample cannot support."],
    ["Colour", "The chart palette is derived from the Ersilia brand hues and validated for " +
      "colour-vision deficiency (worst adjacent pair ΔE 15.8 against a target of 8). Every " +
      "chart also has a table view, so no value is conveyed by colour alone."],
    ["Corrections", "If a figure looks wrong it is usually the registry, not the chart — " +
      "the Data quality view shows which fields are thin."],
  ];
  rows.forEach((row) => {
    const block = el("div", "mrow");
    const label = el("b", null, row[0] + ". ");
    block.appendChild(label);
    block.appendChild(document.createTextNode(row[1]));
    body.appendChild(block);
  });
}

function wireMethods() {
  const modal = document.getElementById("methods");
  const scrim = document.getElementById("scrim");
  const open = document.getElementById("methods-open");
  const close = document.getElementById("methods-close");
  let lastFocus = null;

  function show() {
    lastFocus = document.activeElement;
    modal.hidden = false;
    scrim.hidden = false;
    close.focus();
  }
  function hide() {
    modal.hidden = true;
    scrim.hidden = true;
    if (lastFocus) lastFocus.focus();
  }
  open.addEventListener("click", show);
  close.addEventListener("click", hide);
  scrim.addEventListener("click", hide);
  document.addEventListener("keydown", (e) => { if (e.key === "Escape" && !modal.hidden) hide(); });
}

/* ----------------------------------------------------------------- nav */
function renderNav() {
  const list = document.getElementById("nav-list");
  const add = (path, label) => {
    const item = el("li");
    const link = el("a", null, label);
    link.href = "#" + path;
    item.appendChild(link);
    list.appendChild(item);
  };
  add("/", "Overview");
  VIEWS.forEach((view) => add("/" + view.id, view.title));
  add("/downloads", "Downloads");
}

/* ---------------------------------------------------------------- boot */
async function main() {
  const outlet = document.getElementById("view");
  try {
    const response = await fetch("data/stats.json", { cache: "no-cache" });
    if (!response.ok) throw new Error("HTTP " + response.status);
    DATA = await response.json();
  } catch (e) {
    outlet.innerHTML = "";
    const error = el("div", "empty",
      "Could not load data/stats.json. Run: python scripts/export_site_data.py");
    outlet.appendChild(error);
    return;
  }

  if (DATA.snapshot_date) {
    document.getElementById("snapshot").textContent = "Snapshot " + DATA.snapshot_date;
  }

  // World geometry is only needed by the reach view, but registering it once up
  // front is simpler than coordinating a lazy load with the router.
  try {
    const geo = await (await fetch("vendor/world.geo.json", { cache: "force-cache" })).json();
    echarts.registerMap("world", geo);
  } catch (e) {
    console.warn("World map geometry unavailable; the map card will show an empty state.", e);
  }

  renderNav();
  fillMethods();
  wireMethods();

  Router.add("/", renderLanding, null);
  VIEWS.forEach((view) => Router.add("/" + view.id, renderView(view), view.title));
  Router.add("/downloads", renderDownloads, "Downloads");
  Router.start(outlet);
}

main();
