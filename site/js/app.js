/* Entry point: load stats.json, register the routes, render.

     #/            landing — headline stats, one flagship chart, section cards
     #/<section>   one section: lead chart, then supporting charts
     #/downloads   every aggregate as CSV

   Plus a Methods dialog reachable from the sidebar. There is deliberately no
   "Data quality" view any more: field completeness is a caveat about the numbers,
   so it belongs in Methods beside the definitions, which is where someone
   questioning a figure actually looks. */

let DATA = null;

/* Two metrics are composed in the client rather than exported, because each only
   makes sense as a combination of others. Both are prefixed "__" so csvFor() knows
   not to offer a download that does not exist. */
function syntheticSections() {
  return {
    __growth: buildGrowthIndex(),
    __outreach_per_year: buildOutreachPerYear(),
  };
}

/* ------------------------------------------------------------- landing */
function renderLanding(outlet, registry) {
  const head = el("div", "viewhead");
  head.appendChild(el("h2", null, "Overview"));
  head.appendChild(el("p", null,
    "Aggregate statistics for the Ersilia Open Source Initiative — the Model Hub, " +
    "the people behind it, the code, the science, and the countries it reaches."));
  outlet.appendChild(head);

  const primary = DATA.kpis.models ? PRIMARY_KPIS : PRIMARY_KPIS_FALLBACK;
  outlet.appendChild(statRow(DATA.kpis, primary, "primary", "hero"));

  // Flagship: four measures of very different magnitude, indexed to a common base
  // so they can share one honest axis.
  if (DATA.sections.__growth) {
    const grid = el("div", "chart-grid");
    grid.appendChild(chartCard({
      title: "How Ersilia has grown", data: "__growth", type: "growth",
      lead: true, span: 12, height: "h-lg",
      desc: "Each measure as a share of its own total today, so four series of very " +
            "different size can share one axis. A steep line means that measure grew " +
            "fast in that period; a flat one means it stalled.",
    }, DATA, registry));
    outlet.appendChild(grid);
  }

  outlet.appendChild(el("div", "section-label", "Also tracked"));
  outlet.appendChild(statStrip(DATA.kpis, SECONDARY_KPIS));

  outlet.appendChild(el("div", "section-label", "Explore"));
  const jumps = el("div", "jump-grid");
  VIEWS.forEach((view, index) => {
    const hue = slotColor(index);
    const link = el("a", "jump");
    link.href = "#/" + view.id;
    link.style.setProperty("--slot", hue);

    const title = el("div", "t");
    title.appendChild(el("span", null, view.title));
    const kpi = view.headlineKpi && DATA.kpis[view.headlineKpi];
    if (kpi) title.appendChild(el("span", "n", fmtNum(kpi.value)));
    link.appendChild(title);
    link.appendChild(el("div", "s", viewTakeaway(view)));
    if (kpi && kpi.series && kpi.series.values && kpi.series.values.length > 1) {
      link.appendChild(sparkline(kpi.series.values, hue, 20));
    }
    jumps.appendChild(link);
  });
  outlet.appendChild(jumps);
}

/* The card's one-liner: prefer the lead chart's computed takeaway over the static
   blurb, so the landing page says something current. */
function viewTakeaway(view) {
  const lead = view.charts.find((c) => c.lead) || view.charts[0];
  const metric = lead && lead.data && getByPath(DATA.sections, lead.data);
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

/* Events and blog posts are both counts per year, so they belong on one axis in
   one chart rather than in two charts that merely sit next to each other. */
function buildOutreachPerYear() {
  const events = DATA.sections.events && DATA.sections.events.per_year;
  const posts = DATA.sections.blogposts && DATA.sections.blogposts.per_year;
  if (!events || !events.labels || !events.labels.length) return null;

  const labels = Array.from(new Set(
    events.labels.concat(posts && posts.labels ? posts.labels : [])
  )).sort();
  const pick = (metric) => {
    if (!metric) return labels.map(() => 0);
    const lookup = new Map(metric.labels.map((l, i) => [l, metric.values[i]]));
    return labels.map((l) => lookup.get(l) || 0);
  };
  const eventValues = pick(events);
  const postValues = pick(posts);
  const peak = labels[eventValues.indexOf(Math.max.apply(null, eventValues))];

  return {
    labels: labels,
    series: [
      { name: "Events", values: eventValues },
      { name: "Blog posts", values: postValues },
    ],
    n: eventValues.reduce((a, b) => a + b, 0) + postValues.reduce((a, b) => a + b, 0),
    insight: "Busiest year for events was " + peak + ". Both are counts per year, so " +
      "they are directly comparable.",
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
      outlet.appendChild(el("div", "note",
        "The Models table is not in this snapshot yet, so this view is empty."));
    }

    const grid = el("div", "chart-grid");
    const cards = view.charts.map((chart) => chartCard(chart, DATA, registry));
    // Widen the last card of any short row so no view ends beside a void.
    packSpans(cards);
    cards.forEach((card) => grid.appendChild(card));
    outlet.appendChild(grid);
  };
}

/* ------------------------------------------------------------ downloads */
function renderDownloads(outlet) {
  const head = el("div", "viewhead");
  head.appendChild(el("h2", null, "Downloads"));
  head.appendChild(el("p", null,
    "The aggregate table behind every chart, as CSV, plus the full dataset as JSON. " +
    "Aggregates only — the same guarantee as the charts. Some tables are exported but " +
    "not charted; they are all here."));
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

  // Grouped by exported section rather than by view, so metrics the site no
  // longer charts are still reachable.
  Object.keys(DATA.sections).sort().forEach((section, index) => {
    if (section.indexOf("__") === 0) return;
    const metrics = DATA.sections[section];
    const group = el("div", "dl-group");
    group.style.setProperty("--slot", slotColor(index));
    group.appendChild(el("h4", null, titleCase(section)));
    const list = el("div", "dl-links");
    Object.keys(metrics).sort().forEach((name) => {
      const metric = metrics[name];
      if (!metric || typeof metric !== "object") return;
      const has = ["labels", "points", "cells", "rows", "tree", "series"]
        .some((k) => Array.isArray(metric[k]) && metric[k].length);
      if (!has) return;
      list.appendChild(downloadLink(csvFor(section + "." + name), titleCase(name)));
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
  const kpi = (key) => (DATA.kpis[key] ? fmtNum(DATA.kpis[key].value) : "0");
  const rows = [
    ["Source", "Every figure comes from Ersilia's own Airtable — the Model Hub, projects, " +
      "community, publications, repositories, organisations, events, blog posts and " +
      "countries — read only. Snapshot: " + (DATA.snapshot_date || "unknown") +
      ". Built: " + (DATA.generated_at || "unknown") + "."],
    ["Aggregates only", "Nothing here is row-level personal data. The community table's " +
      "names, emails and social handles are dropped when the snapshot is fetched, dropped " +
      "again when it is read, and the build aborts if anything email-shaped reaches the " +
      "output."],
    ["Repositories", "Counts, dates, types and totals cover all " + kpi("repositories") +
      " repositories, including the " + fmtNum(DATA.meta.private_repositories || 0) +
      " private ones — a count is not disclosure. Anything that names a repository or a " +
      "contributor covers the " + kpi("repositories_public") + " public ones only, because " +
      "a private repository's name is disclosure."],
    ["Multi-select fields", "Roles, tags, topics, categories, biomedical areas and focus " +
      "areas allow several values per record. Those charts count assignments, not records, " +
      "so their shares can sum above 100%. Each chart says so where it matters."],
    ["Journal ranking", "Venues are ranked by mean citations per Ersilia article and need at " +
      "least two Ersilia articles to appear. Without that floor a single well-cited paper " +
      "tops the ranking and says nothing about the venue."],
    ["Global South", "Taken from the World Bank income group on the Countries table: LIC, " +
      "LMIC and UMIC counted as Global South, HIC as Global North. Countries with no income " +
      "group recorded are excluded rather than assumed."],
    ["Retention", "A joining cohort counts towards a retention horizon only once it is old " +
      "enough to judge — someone who joined two months ago is not evidence about 3-month " +
      "retention. Cells with no judgeable members are left blank, not zero."],
    ["Log axes", "The repository popularity chart uses logarithmic axes because a few " +
      "repositories account for most of every metric; on linear axes the rest collapse into " +
      "the corner. The axis ticks show the real values."],
    ["Small numbers", "Percentages are suppressed below n=10, where a share invites a " +
      "conclusion the sample cannot support."],
    ["Colour", "Each section owns a hue, which also colours its charts. The set is derived " +
      "from the Ersilia brand palette and validated for colour-vision deficiency (worst " +
      "adjacent pair ΔE 23.1 against a target of 8). Every chart also has a table view, so " +
      "no value is conveyed by colour alone."],
  ];
  rows.forEach((row) => {
    const block = el("div", "mrow");
    block.appendChild(el("b", null, row[0] + ". "));
    block.appendChild(document.createTextNode(row[1]));
    body.appendChild(block);
  });

  // Field completeness lives here rather than in a view of its own.
  const completeness = DATA.sections.quality && DATA.sections.quality.completeness;
  if (completeness && completeness.labels && completeness.labels.length) {
    body.appendChild(el("h3", null, "How complete is the registry?"));
    const note = el("div", "mrow");
    note.appendChild(document.createTextNode(
      (completeness.insight || "") +
      " Every chart on this site is only as good as what is filled in."));
    body.appendChild(note);
    body.appendChild(meterRow({
      labels: completeness.labels,
      values: completeness.values,
      total: 100,
    }));
  }
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
  // A plain list. No colour dots: they encoded nothing the reader could act on.
  const add = (path, label) => {
    const item = el("li");
    const link = el("a", null, label);
    link.href = "#" + path;
    item.appendChild(link);
    list.appendChild(item);
  };
  add("/", "Overview");
  VIEWS.forEach((view) => add("/" + view.id, view.title));
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
    outlet.appendChild(el("div", "empty",
      "Could not load data/stats.json. Run: python scripts/export_site_data.py"));
    return;
  }

  Object.assign(DATA.sections, syntheticSections());

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
