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
    const crow = el("div", "crow h-lg");
    crow.appendChild(chartCard({
      title: "How Ersilia has grown", data: "__growth", type: "growth",
      lead: true, span: 12,
      desc: "Each measure as a share of its own total today, so four series of very " +
            "different size can share one axis. A steep line means that measure grew " +
            "fast in that period; a flat one means it stalled.",
    }, DATA, registry));
    grid.appendChild(crow);
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
  // The first chart of the first row is the view's lead.
  const lead = view.rows && view.rows[0] && view.rows[0].cells[0];
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
    // The section's hue, so header links pick it up on hover exactly as the nav does.
    outlet.style.setProperty("--tab", "var(--tab-" + view.id + ")");
    const head = el("div", "viewhead");
    head.appendChild(el("h2", null, view.title));
    head.appendChild(el("p", null, view.blurb));
    // A statistics page should point at the thing it counts, so each view carries
    // links to where you can go and actually see it.
    if (view.links && view.links.length) {
      const links = el("div", "headlinks");
      view.links.forEach((link) => {
        const a = el("a", null, link.label + " ↗");
        a.href = link.href;
        a.target = "_blank";
        a.rel = "noopener";
        links.appendChild(a);
      });
      head.appendChild(links);
    }
    outlet.appendChild(head);

    if (view.id === "models" && !DATA.meta.models_available) {
      outlet.appendChild(el("div", "note",
        "The Models table is not in this snapshot yet, so this view is empty."));
    }

    const grid = el("div", "chart-grid");
    // One .crow per configured row: spans sum to 12, cards share a height, and the
    // charts inside flex to fill it.
    view.rows.forEach((row) => {
      const crow = el("div", "crow " + (row.h || "h-md"));
      row.cells.forEach((chart) => crow.appendChild(chartCard(chart, DATA, registry)));
      grid.appendChild(crow);
    });
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
  card.style.animation = "none";
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
    ["Snapshot dates", "Each table is fetched separately, so the date in the sidebar is " +
      "the newest stamp across all of them. If a fetch fails for one table its previous " +
      "snapshot is kept, and any table behind the others is named next to that date " +
      "rather than left to look current."],
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
    ["Citations come from OpenAlex", "Citation counts, the per-year accrual, open-access " +
      "status and the countries of author institutions are collected from OpenAlex against " +
      "each paper's DOI, not entered by hand. That matters because citation counts are " +
      "source-dependent — one paper reads 43 in OpenAlex, 37 in Semantic Scholar and 44 in " +
      "the older manual record — so the source is named rather than a bare number printed. " +
      "The manual figures understated the total by 31%, 1,305 against 1,712, with 38 of 42 " +
      "papers differing. Google Scholar is not used: it has no API and its robots.txt " +
      "disallows the paths that carry per-paper counts, so the Scholar links here point at " +
      "its citing-works page rather than being read from it."],
    ["African collaboration, two ways", "The publications table carries a hand-set " +
      "African-collaboration flag, and OpenAlex separately gives the countries of the author " +
      "institutions. They agree on 24 of the 26 papers where the flag is set, and the two " +
      "disagreements show the flag means something slightly different: one paper is about " +
      "drug discovery for Africa with no African author institution, and one has a South " +
      "African institution and no flag. 16 of 42 papers have at least one African author " +
      "institution. Neither figure is wrong; they answer different questions."],
    ["Journal ranking", "Venues are ranked by mean citations per Ersilia article and need at " +
      "least two Ersilia articles to appear. Without that floor a single well-cited paper " +
      "tops the ranking and says nothing about the venue."],
    ["Global South", "Taken from the World Bank income group on the Countries table: LIC, " +
      "LMIC and UMIC counted as Global South, HIC as Global North. Countries with no income " +
      "group recorded are excluded rather than assumed."],
    ["How long people stay", "Only ENDED collaborations are binned by length; including " +
      "current members would censor every long one downwards. Read the distribution as the " +
      "shape of the placements Ersilia runs — most are internships, fellowships and student " +
      "placements with a term fixed before anyone arrived — rather than as a target missed. " +
      "This section previously led with a churn ledger and a cohort-retention grid; both " +
      "were correct arithmetic and both framed a growing community as attrition."],
    ["Pathogens targeted", "Counts models whose target organism is a named pathogen. " +
      "'Any' and 'Homo sapiens' are excluded: both are real answers, but they describe " +
      "organism-agnostic chemistry and human-property prediction respectively, and together " +
      "they would fill the ranking without saying anything about pathogen coverage."],
    ["Years from paper to Hub", "Incorporation year minus the model's recorded publication " +
      "year. Models whose incorporation year precedes their publication year are dropped: a " +
      "negative lag means one of the two dates is wrong, not that a paper was wrapped before " +
      "it existed."],
    ["How far models scale", "DERIVED, not recorded. The five Computational Performance " +
      "columns hold runtimes at increasing input batch sizes, and a value of -1 means the " +
      "model failed at that size. The largest column holding a positive number is therefore " +
      "the largest batch the model actually completed. Models with no benchmark are absent."],
    ["Growth charts", "Where something grows over time, the rate and the running total are " +
      "drawn as two panels sharing one time axis, never as two y-axes on one plot. A " +
      "cumulative curve only ever rises, so on its own it hides whether the rate is rising " +
      "or falling; the two panels are the same data asked two different questions."],
    ["Log axes", "The repository popularity chart uses logarithmic axes because a few " +
      "repositories account for most of every metric; on linear axes the rest collapse into " +
      "the corner. The axis ticks show the real values."],
    ["Small numbers", "Percentages are suppressed below n=10, where a share invites a " +
      "conclusion the sample cannot support."],
    ["Registry consistency", (() => {
      const prs = (DATA.sections.quality || {}).project_repo_status || {};
      const thin = (DATA.sections.quality || {}).thin_fields || {};
      const parts = [];
      if (prs.insight) parts.push(prs.insight);
      if (thin.labels && thin.labels.length) {
        parts.push("Fields under " + (thin.threshold || 80) + "% filled, thinnest first: " +
          thin.labels.slice(0, 8).join(", ") +
          (thin.labels.length > 8 ? ", and " + (thin.labels.length - 8) + " more" : "") + ".");
      }
      parts.push("These are caveats about the records rather than findings about the work, " +
        "which is why they are here and not on a page of their own.");
      return parts.join(" ");
    })()],
    ["Keyboard", "Up and Down walk the section list once it has focus, Home and End jump " +
      "to its ends, [ and ] step between views from anywhere on the page, and ? opens " +
      "this dialog. Every chart also has a Table button that opens its numbers as a " +
      "table, and the ⓘ beside each title opens the note explaining how that figure " +
      "is measured."],
    ["Colour", "One categorical set, shared by every chart on every page, assigned in a " +
      "fixed order. Derived from the Ersilia brand palette and validated for colour-vision " +
      "deficiency (worst adjacent pair ΔE 20.0 against a target of 8). Red sits last in that " +
      "order on purpose: it carries a verdict whether or not one is meant, so only a genuine " +
      "sixth category reaches it. Green, amber and red are otherwise reserved for real " +
      "states — a model's curation status, a project's status. Every chart also has a table " +
      "view, so no value is conveyed by colour alone."],
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

/* Is any dialog currently open? The keyboard handler needs to know: stepping the
   route from under an open dialog leaves it showing a table for a card that no
   longer exists, with `lastFocus` pointing at a detached node. */
function dialogOpen() {
  return Array.from(document.querySelectorAll(".modal")).some((m) => !m.hidden);
}

const FOCUSABLE =
  'a[href], button:not([disabled]), input, select, textarea, [tabindex]:not([tabindex="-1"])';

/* One dialog mechanism, used by both the Methods panel and the per-chart data table.
   Returns `{show, hide}`; the caller decides what opens it.

   These are divs with role="dialog" aria-modal="true" rather than <dialog>, so the
   three things the platform would give us for free have to be done by hand — and
   until now only one of them was. `aria-modal="true"` on a background that is still
   focusable and still in the accessibility tree is a claim that isn't true. */
function makeDialog(modalId, closeId) {
  const modal = document.getElementById(modalId);
  const scrim = document.getElementById("scrim");
  const close = document.getElementById(closeId);
  const shell = document.querySelector(".shell");
  let lastFocus = null;

  function show() {
    lastFocus = document.activeElement;
    modal.hidden = false;
    scrim.hidden = false;
    // Take the page behind out of the tab order AND out of the accessibility tree.
    // `inert` does both; aria-hidden covers browsers without it.
    if (shell) {
      shell.inert = true;
      shell.setAttribute("aria-hidden", "true");
    }
    // Stop the page behind scrolling under the dialog on wheel/trackpad.
    document.body.style.overflow = "hidden";
    close.focus();
  }

  function hide() {
    modal.hidden = true;
    // Only drop the scrim, the inert flag and the scroll lock if no OTHER dialog is
    // still using them.
    const others = Array.from(document.querySelectorAll(".modal"))
      .filter((m) => m !== modal && !m.hidden);
    if (!others.length) {
      scrim.hidden = true;
      if (shell) {
        shell.inert = false;
        shell.removeAttribute("aria-hidden");
      }
      document.body.style.overflow = "";
    }
    // The node may have been detached while the dialog was open.
    if (lastFocus && lastFocus.focus && lastFocus.isConnected) lastFocus.focus();
    else if (shell) (shell.querySelector("#methods-open") || document.body).focus();
  }

  close.addEventListener("click", hide);
  scrim.addEventListener("click", () => { if (!modal.hidden) hide(); });

  document.addEventListener("keydown", (e) => {
    if (modal.hidden) return;
    if (e.key === "Escape") { hide(); return; }
    // Focus trap. Without this, Tab walked out of the dialog and straight into the
    // nav and every chart's Table button behind the scrim, all still clickable.
    if (e.key !== "Tab") return;
    const items = Array.from(modal.querySelectorAll(FOCUSABLE))
      .filter((el) => el.offsetParent !== null);
    if (!items.length) return;
    const first = items[0];
    const last = items[items.length - 1];
    if (e.shiftKey && document.activeElement === first) {
      e.preventDefault();
      last.focus();
    } else if (!e.shiftKey && document.activeElement === last) {
      e.preventDefault();
      first.focus();
    }
  });
  return { show: show, hide: hide };
}

function wireMethods() {
  const dialog = makeDialog("methods", "methods-close");
  document.getElementById("methods-open").addEventListener("click", dialog.show);
}

/* The per-chart data table lives in a dialog rather than expanding inside its card.
   Inline, a <details> that opened added ~240px of table to one card, which grew the
   grid row, which stretched EVERY chart in that row — the panels visibly ballooned.
   A dialog cannot move the page, and a wide table finally gets room to be read. */
function wireDataDialog() {
  const dialog = makeDialog("datamodal", "datamodal-close");
  const title = document.getElementById("datamodal-title");
  const body = document.getElementById("datamodal-body");

  // The ⓘ methodology note, in the same dialog. Kept separate from openDataTable so
  // the caller does not have to build a node just to show a sentence.
  window.openNote = function (heading, text) {
    title.textContent = heading;
    body.textContent = "";
    const para = el("p", "notetext", text);
    body.appendChild(para);
    dialog.show();
  };

  window.openDataTable = function (heading, node, csvPath) {
    title.textContent = heading;
    body.textContent = "";
    body.appendChild(node);
    if (csvPath) {
      const link = el("a", "dl", "Download CSV");
      link.href = csvPath;
      link.setAttribute("download", "");
      body.appendChild(link);
    }
    dialog.show();
  };
}

/* ----------------------------------------------------------------- nav */
function renderNav() {
  const list = document.getElementById("nav-list");
  // Each tab carries its own hue via --tab; styles.css keeps it light. No dots.
  const add = (path, label, id) => {
    const item = el("li");
    const link = el("a", null, label);
    link.href = "#" + path;
    link.style.setProperty("--tab", "var(--tab-" + id + ")");
    item.appendChild(link);
    list.appendChild(item);
  };
  add("/", "Overview", "overview");
  VIEWS.forEach((view) => add("/" + view.id, view.title, view.id));
}

/* ------------------------------------------------------------ keyboard */
/* The sidebar is a real list of links, so Tab and Enter already work. This adds the
   conventions people expect of a vertical nav: Up/Down to walk it, Home/End to jump
   to the ends, and left/right bracket to move between views from anywhere on the
   page without having to focus the nav first. */
/* The skip link must NOT be allowed to set location.hash: this is a hash-routed
   page, so "#main" would be read as an unknown route and bounce the reader to the
   Overview. Focus the region directly and leave the URL alone. */
function wireSkipLink() {
  const link = document.querySelector("a.skip");
  const main = document.getElementById("main");
  if (!link || !main) return;
  link.addEventListener("click", (e) => {
    e.preventDefault();
    main.focus();
    main.scrollIntoView({ block: "start", behavior: "auto" });
  });
}

/* Announce the view after a route change. Activating a nav link previously changed
   the whole content area with no announcement and no focus move, so a screen-reader
   user heard nothing happen. */
function announceView() {
  const live = document.getElementById("route-status");
  const heading = document.querySelector("#view .viewhead h2");
  if (live && heading) live.textContent = heading.textContent + " — view loaded";
}

function wireKeyboard() {
  const links = () => Array.from(document.querySelectorAll("#nav-list a"));

  document.addEventListener("keydown", (e) => {
    // A dialog owns the keyboard while it is open. Without this, "]" behind an open
    // data dialog re-rendered the view underneath it, leaving the dialog showing a
    // table for a card that no longer existed.
    if (dialogOpen()) return;

    // AltGr is reported as ctrlKey+altKey, and on most European layouts "[" and "]"
    // ARE AltGr combinations — so bailing on any modifier silently removed the
    // view-stepping shortcuts for anyone not on a US layout. Let AltGr through and
    // only bail on a real Ctrl/Cmd/Alt chord.
    const altGr = typeof e.getModifierState === "function" && e.getModifierState("AltGraph");
    if (!altGr && (e.metaKey || e.ctrlKey || e.altKey)) return;
    if (e.metaKey) return;

    const tag = (e.target.tagName || "").toLowerCase();
    if (tag === "input" || tag === "textarea" || e.target.isContentEditable) return;

    const all = links();
    const current = all.findIndex((a) => a.hasAttribute("aria-current"));
    const focused = all.indexOf(document.activeElement);

    // Within the nav: move focus.
    if (focused >= 0 && (e.key === "ArrowDown" || e.key === "ArrowUp")) {
      e.preventDefault();
      const next = e.key === "ArrowDown"
        ? Math.min(focused + 1, all.length - 1)
        : Math.max(focused - 1, 0);
      all[next].focus();
      return;
    }
    if (focused >= 0 && (e.key === "Home" || e.key === "End")) {
      e.preventDefault();
      (e.key === "Home" ? all[0] : all[all.length - 1]).focus();
      return;
    }

    // Anywhere: step between views.
    if (e.key === "[" || e.key === "]") {
      e.preventDefault();
      const from = current < 0 ? 0 : current;
      const to = e.key === "]"
        ? Math.min(from + 1, all.length - 1)
        : Math.max(from - 1, 0);
      if (to !== from) window.location.hash = all[to].getAttribute("href").slice(1);
      return;
    }

    // "?" opens Methods, matching the convention for help.
    if (e.key === "?") {
      e.preventDefault();
      document.getElementById("methods-open").click();
    }
  });
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
    const el0 = document.getElementById("snapshot");
    el0.textContent = "Snapshot " + DATA.snapshot_date;
    // A partial fetch leaves one table older than the rest, and the headline date is
    // the NEWEST stamp — so without this the page would present mixed-age data under
    // today's date and say nothing. Name the stale tables where the date is shown.
    const stale = (DATA.meta && DATA.meta.stale_tables) || {};
    const names = Object.keys(stale);
    if (names.length) {
      const warn = el("span", "stalewarn",
        names.length + (names.length === 1 ? " table is" : " tables are") + " older: " +
        names.map((n) => n + " (" + stale[n] + ")").join(", "));
      warn.title = "The snapshot date above is the newest across all tables. These are behind it.";
      el0.appendChild(warn);
    }
  }

  renderNav();
  fillMethods();
  wireMethods();
  wireDataDialog();
  wireKeyboard();
  wireSkipLink();

  Router.add("/", renderLanding, null);
  VIEWS.forEach((view) => Router.add("/" + view.id, renderView(view), view.title));
  Router.add("/downloads", renderDownloads, "Downloads");
  // The router's afterRender hook existed and had never been used. It does two jobs:
  // announce the new view, and pull in the map geometry only for the view that needs it.
  Router.start(outlet, (path) => {
    announceView();
    if (path === "/reach") ensureWorldMap(outlet);
  });
}

/* 1 MB of world geometry, fetched once, on demand.

   This used to be awaited in main() BEFORE anything rendered — so every visitor
   downloaded and JSON-parsed a megabyte of coastlines to look at the Overview page,
   which has no map, and saw nothing at all until it finished. It is 43% of the
   Overview page's transferred bytes for a chart that appears on one of eight views.

   Now: the reach view renders immediately with the map card in its empty state, the
   geometry arrives, and that one card is re-rendered. Every other view never asks
   for it. */
let worldMapState = null;   // null = untried, "loading", "ready", "failed"

async function ensureWorldMap(outlet) {
  if (worldMapState === "ready" || worldMapState === "loading") return;
  worldMapState = "loading";
  try {
    const geo = await (await fetch("vendor/world.geo.json", { cache: "force-cache" })).json();
    echarts.registerMap("world", geo);
    worldMapState = "ready";
    // Re-render so the map card picks up the now-registered geometry. Guard on the
    // route: the reader may have navigated away while the megabyte was in flight.
    if (Router.current() === "/reach") Router.rerender();
  } catch (e) {
    worldMapState = "failed";
    console.warn("World map geometry unavailable; the map card shows an empty state.", e);
  }
}

main();
