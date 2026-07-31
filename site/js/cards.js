/* Card shell, stat tiles, and the three HTML components.

   Not every ratio deserves a canvas. Three forms here are plain HTML — a meter
   list, a ranked table with inline microbars, and a stack of share bars. They are
   lighter to read than a chart, they scale to any card width, and between them
   they collapse what used to be nine separate bar charts into three cards.

   Progressive disclosure, three tiers (house rule):
     1. surface  — title, one number, the computed takeaway
     2. hover    — the methodology note on the ⓘ
     3. Methods  — the dialog, one click away, for definitions and provenance */

function el(tag, cls, text) {
  const node = document.createElement(tag);
  if (cls) node.className = cls;
  if (text != null) node.textContent = text;
  return node;
}

function getByPath(obj, path) {
  return String(path).split(".").reduce((o, k) => (o && o[k] != null ? o[k] : undefined), obj);
}

/* ------------------------------------------------------------ stat tiles */
/* Inline SVG sparkline. Cheaper than an ECharts instance per tile. */
function sparkline(values, color, height) {
  const w = 100, h = height || 24, pad = 1.5;
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("viewBox", "0 0 " + w + " " + h);
  svg.setAttribute("class", "spark");
  svg.setAttribute("preserveAspectRatio", "none");
  svg.setAttribute("aria-hidden", "true");
  if (!values || values.length < 2) return svg;

  const max = Math.max.apply(null, values);
  const min = Math.min.apply(null, values);
  const range = max - min || 1;
  const x = (i) => (i / (values.length - 1)) * w;
  const y = (v) => h - pad - ((v - min) / range) * (h - pad * 2);
  const line = values.map((v, i) => (i ? "L" : "M") + x(i).toFixed(2) + " " + y(v).toFixed(2)).join(" ");

  const area = document.createElementNS("http://www.w3.org/2000/svg", "path");
  area.setAttribute("d", line + " L" + w + " " + h + " L0 " + h + " Z");
  area.setAttribute("fill", color);
  area.setAttribute("opacity", "0.11");
  svg.appendChild(area);

  const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
  path.setAttribute("d", line);
  path.setAttribute("fill", "none");
  path.setAttribute("stroke", color);
  path.setAttribute("stroke-width", "1.4");
  // preserveAspectRatio:none stretches the geometry, which would also stretch the
  // stroke; this keeps it an even hairline at any card width.
  path.setAttribute("vector-effect", "non-scaling-stroke");
  path.setAttribute("stroke-linejoin", "round");
  svg.appendChild(path);
  return svg;
}

function statTile(kpi, spec, size) {
  const tile = el("div", "stat " + (size || ""));
  // Each headline tile takes its own palette slot, so the row is polychrome rather
  // than four copies of one accent.
  const hue = spec.slot != null ? slotColor(spec.slot) : accent();
  tile.appendChild(el("div", "k", spec.label));
  tile.appendChild(el("div", "v", fmtNum(kpi.value)));

  const sub = el("div", "d");
  const delta = fmtDelta(kpi.delta_12m);
  if (delta && kpi.series && kpi.series.values && kpi.series.values.length > 1) {
    sub.appendChild(el("span", "delta " + delta.cls, delta.text));
  } else if (spec.note) {
    sub.appendChild(el("span", "delta flat", spec.note));
  }
  if (sub.childNodes.length) tile.appendChild(sub);

  if (size === "hero" && kpi.series && kpi.series.values && kpi.series.values.length > 1) {
    tile.appendChild(sparkline(kpi.series.values, hue));
  }
  return tile;
}

function statRow(kpis, specs, cls, size) {
  const row = el("div", "stat-row " + (cls || ""));
  specs.forEach((spec) => {
    const kpi = kpis[spec.key];
    if (!kpi) return;
    row.appendChild(statTile(kpi, spec, size));
  });
  return row;
}

/* One flat strip of secondary numbers — less furniture than six more cards. */
function statStrip(kpis, specs) {
  const strip = el("div", "strip");
  specs.forEach((spec) => {
    const kpi = kpis[spec.key];
    if (!kpi) return;
    const cell = el("div", "cell");
    cell.appendChild(el("div", "k", spec.label));
    cell.appendChild(el("div", "v", fmtNum(kpi.value)));
    strip.appendChild(cell);
  });
  return strip;
}

/* -------------------------------------------------------- HTML components */
/* Meters: label, value, thin bar. For "how many of the whole" figures where a
   chart would be more furniture than information. */
function meterRow(metric) {
  const wrap = el("div", "meters");
  // A percentage is only meaningful when the metric declares what the whole IS.
  // Without `total`, these are just magnitudes — "18.4 months, 100%" was nonsense,
  // because the bar was scaled against the largest value rather than a whole.
  const total = metric.total;
  const scale = total || Math.max.apply(null, metric.values.map(Number)) || 1;
  metric.labels.forEach((label, i) => {
    const value = Number(metric.values[i]);
    const row = el("div", "meter");
    const top = el("div", "top");
    top.appendChild(el("span", "lbl", label));
    const readout = total
      ? fmtNum(value) + "  " + fmtPct(value, total)
      : fmtNum(value) + (metric.unit ? " " + metric.unit : "");
    top.appendChild(el("span", "val", readout));
    row.appendChild(top);
    const track = el("div", "track");
    const fill = el("div", "fill");
    fill.style.width = Math.max(1, 100 * value / scale) + "%";
    track.appendChild(fill);
    row.appendChild(track);
    wrap.appendChild(row);
  });
  return wrap;
}

/* A ranked table with an inline microbar. One of these replaces three separate
   ranking charts, and it shows the secondary columns a bar chart has to hide. */
function rankedTable(metric, spec) {
  const columns = spec.columns || [{ key: "value", label: "Value" }];
  const table = el("table", "ranked");
  const thead = el("thead");
  const headRow = el("tr");
  headRow.appendChild(el("th", null, spec.nameLabel || "Name"));
  columns.forEach((c) => headRow.appendChild(el("th", null, c.label)));
  headRow.appendChild(el("th", null, ""));
  thead.appendChild(headRow);
  table.appendChild(thead);

  const body = el("tbody");
  const primary = columns[0].key;
  const rows = metric.rows || metric.labels.map((label, i) => {
    const row = { name: label, value: metric.values[i] };
    (metric.extra || []).forEach((ex) => { row[ex.key] = ex.values[i]; });
    return row;
  });
  const max = Math.max.apply(null, rows.map((r) => Number(r[primary]) || 0));

  rows.slice(0, spec.top || 12).forEach((row) => {
    const tr = el("tr");
    const name = el("td", "name");
    name.appendChild(el("span", null, String(row.name)));
    name.title = String(row.name);
    tr.appendChild(name);
    columns.forEach((c) => tr.appendChild(el("td", "num", fmtNum(row[c.key]))));
    const barCell = el("td", "barcell");
    const bar = el("div", "microbar");
    bar.style.width = (max ? Math.max(2, 100 * (Number(row[primary]) || 0) / max) : 0) + "%";
    barCell.appendChild(bar);
    tr.appendChild(barCell);
    body.appendChild(tr);
  });
  table.appendChild(body);
  return table;
}

/* Several two-category splits in one card. Publications had three separate yes/no
   charts; this is all three, and shorter than any one of them was. */
function shareRow(sources, data) {
  const wrap = el("div", "shares");
  sources.forEach((source) => {
    const metric = getByPath(data.sections, source.data);
    if (!metric || !metric.labels || metric.labels.length < 2) return;
    const total = metric.values.reduce((a, b) => a + Number(b), 0);
    if (!total) return;
    // The affirmative side is whichever label the config names, else the first.
    let index = source.highlight ? metric.labels.indexOf(source.highlight) : 0;
    if (index < 0) index = 0;
    const value = Number(metric.values[index]);
    const other = total - value;

    const row = el("div", "share");
    const top = el("div", "top");
    top.appendChild(el("span", "lbl", source.label));
    top.appendChild(el("span", "pct", fmtPct(value, total)));
    row.appendChild(top);

    const track = el("div", "track");
    const a = el("div", "a");
    a.style.width = (100 * value / total) + "%";
    const b = el("div", "b");
    b.style.width = (100 * other / total) + "%";
    track.appendChild(a);
    track.appendChild(b);
    row.appendChild(track);

    const legend = el("div", "legend");
    const one = el("span", null, metric.labels[index] + " ");
    one.appendChild(el("b", null, fmtNum(value)));
    const two = el("span", null, (metric.labels[1 - index] || "Other") + " ");
    two.appendChild(el("b", null, fmtNum(other)));
    legend.appendChild(one);
    legend.appendChild(two);
    row.appendChild(legend);
    wrap.appendChild(row);
  });
  return wrap;
}

/* ---------------------------------------------------------- drill-down */
function drillTable(metric) {
  const wrap = el("div", "scrollwrap");
  const table = el("table", "data");
  const thead = el("thead");
  const headRow = el("tr");
  const body = el("tbody");

  let headers = [];
  let rows = [];

  if (metric.series) {
    headers = ["Period"].concat(metric.series.map((s) => s.name));
    rows = metric.labels.map((label, i) =>
      [label].concat(metric.series.map((s) => s.values[i])));
  } else if (metric.cells) {
    headers = ["Row", "Column", metric.unit || "Value"];
    rows = metric.cells.map((c) => [metric.y[c[1]], metric.x[c[0]], c[2]]);
  } else if (metric.rows) {
    headers = Object.keys(metric.rows[0] || {});
    rows = metric.rows.map((r) => headers.map((h) => r[h]));
  } else if (metric.tree) {
    headers = ["Task", "Subtask", "Models"];
    rows = [];
    metric.tree.forEach((parent) => {
      (parent.children || []).forEach((child) => rows.push([parent.name, child.name, child.value]));
    });
  } else if (metric.points) {
    const first = metric.points[0];
    if (Array.isArray(first)) {
      headers = ["Repository", "Stars", "Forks", "Contributors"];
      rows = metric.points.map((p) => [p[3], p[0], p[1], p[2]]);
    } else {
      headers = Object.keys(first);
      rows = metric.points.map((p) => headers.map((h) => p[h]));
    }
  } else {
    headers = ["Label", metric.unit || "Value"];
    rows = (metric.labels || []).map((label, i) => [label, metric.values[i]]);
  }

  headers.forEach((h) => headRow.appendChild(el("th", null, titleCase(h))));
  thead.appendChild(headRow);
  table.appendChild(thead);

  rows.forEach((cells) => {
    const tr = el("tr");
    cells.forEach((cell, i) => {
      const isNumber = i > 0 && typeof cell === "number";
      tr.appendChild(el("td", isNumber ? "num" : null,
        isNumber ? fmtNum(cell) : String(cell == null ? "" : cell)));
    });
    body.appendChild(tr);
  });
  table.appendChild(body);
  wrap.appendChild(table);
  return wrap;
}

function drillDown(chart, metric, csvPath) {
  const details = el("details", "drill");
  const summary = el("summary", null, "Table");
  summary.setAttribute("aria-label", "Show the data behind " + chart.title + " as a table");
  details.appendChild(summary);

  // Built on first open: 35 tables' worth of DOM is not worth pre-rendering.
  let built = false;
  details.addEventListener("toggle", () => {
    if (!details.open || built) return;
    built = true;
    details.appendChild(drillTable(metric));
    if (csvPath) {
      const link = el("a", "dl", "Download CSV");
      link.href = csvPath;
      link.setAttribute("download", "");
      details.appendChild(link);
    }
  });
  return details;
}

/* ----------------------------------------------------------- span logic */
/* How many columns a chart occupies, derived from the DATA rather than editorial
   rank alone. v2 set spans by importance, which stretched a 7-category chart
   across 1100px (seven thin bars adrift in white) while squeezing an 18-row
   ranking into a narrow card until its labels truncated. */
function spanFor(chart, metric) {
  if (chart.span) return chart.span;            // explicit wins, for lead charts
  const n = countCategories(chart, metric);
  if (chart.type === "lollipop" || chart.type === "ordinallollipop" || chart.type === "ranked") {
    // A ranking needs vertical room, never horizontal.
    return n > 12 ? 6 : (n > 6 ? 5 : 4);
  }
  if (chart.type === "column" || chart.type === "histogram") {
    return n > 16 ? 12 : (n > 9 ? 8 : (n > 5 ? 6 : 4));
  }
  if (chart.type === "donut" || chart.type === "shares" || chart.type === "meters") return 4;
  if (chart.type === "treemap" || chart.type === "treehierarchy") return 5;
  return 6;
}

function countCategories(chart, metric) {
  if (!metric) return 0;
  if (metric.tree) return metric.tree.length;
  if (metric.cells) return (metric.x || []).length;
  if (metric.points) return metric.points.length;
  if (metric.rows) return metric.rows.length;
  return (metric.labels || []).length;
}

/* Rows should not end with a lone card beside a void. Widen the last card of a
   short row so every row of 12 columns is filled. */
function packSpans(cards) {
  let row = [];
  let used = 0;
  const flush = () => {
    if (!row.length) return;
    const slack = 12 - used;
    // Cap the stretch. Widening a share-bar card from 4 columns to 12 filled the
    // row but left tracks running the whole page width, which looks worse than the
    // gap it was fixing. Two columns of give is enough to tidy a row.
    if (slack > 0) {
      const last = row[row.length - 1];
      setSpan(last, last._span + Math.min(slack, 2));
    }
    row = [];
    used = 0;
  };
  cards.forEach((card) => {
    if (card._span >= 12) { flush(); return; }
    if (used + card._span > 12) flush();
    row.push(card);
    used += card._span;
  });
  flush();
  return cards;
}

function setSpan(card, span) {
  card.classList.remove("span-" + card._span);
  card._span = Math.min(12, span);
  card.classList.add("span-" + card._span);
}

/* --------------------------------------------------------------- card */
function chartCard(chart, data, registry) {
  const sources = chart.toggles && chart.toggles.length
    ? chart.toggles
    : [{ label: null, data: chart.data }];
  // `shares` composes several metrics of its own, so it has no single source.
  const metric = chart.type === "shares"
    ? { labels: ["_"], values: [1] }
    : getByPath(data.sections, sources[0].data);

  const span = chart.type === "shares" ? (chart.span || 4) : spanFor(chart, metric);
  const card = el("div", "card span-" + span + (chart.lead ? " lead" : ""));
  card._span = span;

  const head = el("div", "phead");
  head.appendChild(el("h3", null, chart.title));
  const meta = el("div", "pmeta");
  head.appendChild(meta);
  card.appendChild(head);

  if (chart.type !== "shares" && !hasData(chart, metric)) {
    card.appendChild(el("div", "empty", chart.emptyNote || "No data in this snapshot yet."));
    return card;
  }

  if (metric && metric.n != null && chart.type !== "shares") {
    meta.appendChild(el("span", "pcount", "n=" + fmtNum(metric.n)));
  }

  const insight = el("p", "insight", (metric && metric.insight) || chart.blurb || "");
  if ((metric && metric.insight) || chart.blurb) card.appendChild(insight);

  if (chart.desc) {
    const info = el("button", "info hovertip", "i");
    info.type = "button";
    info.setAttribute("data-tip", chart.desc);
    info.setAttribute("aria-label", "How this is measured: " + chart.desc);
    meta.appendChild(info);
  }

  // HTML forms need no canvas and no ECharts instance.
  if (HTML_TYPES[chart.type]) {
    if (chart.type === "meters") card.appendChild(meterRow(metric));
    else if (chart.type === "ranked") card.appendChild(rankedTable(metric, chart));
    else if (chart.type === "shares") card.appendChild(shareRow(chart.sources || [], data));
    if (chart.type !== "shares") {
      card.appendChild(drillDown(chart, metric, csvFor(sources[0].data)));
    }
    return card;
  }

  const canvas = el("div", "chart " + (chart.height || heightFor(chart, metric)));
  canvas.setAttribute("role", "img");
  canvas.setAttribute("aria-label", chart.title + ". " + ((metric && metric.insight) || "") +
    " The same data is available as a table below this chart.");
  card.appendChild(canvas);

  let drill = drillDown(chart, metric, csvFor(sources[0].data));
  card.appendChild(drill);

  const instance = echarts.init(canvas, null, { renderer: "canvas" });
  instance.setOption(buildOption(chart, metric));
  registry.push(instance);

  // Metric toggles change WHICH measure the card encodes. They are not filters —
  // a filter would belong in one row above everything it scopes.
  if (sources.length > 1) {
    const toggle = el("div", "toggle");
    let active = 0;
    sources.forEach((source, i) => {
      const button = el("button", null, source.label);
      button.type = "button";
      button.setAttribute("aria-pressed", String(i === 0));
      button.addEventListener("click", () => {
        if (i === active) return;
        active = i;
        toggle.querySelectorAll("button").forEach((b, j) => b.setAttribute("aria-pressed", String(i === j)));
        const next = getByPath(data.sections, source.data);
        if (!hasData(chart, next)) return;
        instance.setOption(buildOption(chart, next), true);
        insight.textContent = next.insight || "";
        canvas.setAttribute("aria-label", chart.title + " — " + source.label + ". " + (next.insight || ""));
        const fresh = drillDown(chart, next, csvFor(source.data));
        drill.replaceWith(fresh);
        drill = fresh;
      });
      toggle.appendChild(button);
    });
    meta.insertBefore(toggle, meta.firstChild);
  }

  return card;
}

/* Height from the form and the row count, so a 15-row lollipop is not squeezed
   into the same box as a 4-row one. */
function heightFor(chart, metric) {
  const n = countCategories(chart, metric);
  if (chart.type === "lollipop" || chart.type === "ordinallollipop") {
    if (n > 13) return "h-lg";
    if (n > 8) return "h-md";
    return "h-sm";
  }
  if (chart.lead) return "h-lg";
  return "h-md";
}

function csvFor(path) {
  // Synthetic, client-side metrics (the landing growth index) have no exported
  // CSV, so they get no download link rather than a broken one.
  if (!path || String(path).indexOf("__") === 0) return null;
  return "data/tables/" + String(path).replace(/\./g, "_") + ".csv";
}
