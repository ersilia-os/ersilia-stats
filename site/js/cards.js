/* Card shell and stat tiles.

   Progressive disclosure, three tiers (house rule):
     1. surface  — title, one number, the computed takeaway
     2. hover    — the .hovertip methodology note on the ⓘ
     3. Methods  — the modal, one click away, for definitions and provenance

   Every chart card also carries a <details> drill-down holding the same
   aggregate as a table.data plus its CSV link. That is the accessible twin of a
   canvas chart, and the documented relief for the two sub-3:1 palette slots. */

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
/* Inline SVG sparkline. Cheaper than an ECharts instance per tile, and it keeps
   the tile purely decorative-free: no axis, no labels, just the shape. */
function sparkline(values, color) {
  const w = 100, h = 26, pad = 2;
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

  const line = values.map((v, i) => (i ? "L" : "M") + x(i).toFixed(1) + " " + y(v).toFixed(1)).join(" ");
  const area = document.createElementNS("http://www.w3.org/2000/svg", "path");
  area.setAttribute("d", line + " L" + w + " " + h + " L0 " + h + " Z");
  area.setAttribute("fill", color);
  area.setAttribute("opacity", "0.12");
  svg.appendChild(area);

  const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
  path.setAttribute("d", line);
  path.setAttribute("fill", "none");
  path.setAttribute("stroke", color);
  path.setAttribute("stroke-width", "1.6");
  path.setAttribute("stroke-linejoin", "round");
  svg.appendChild(path);
  return svg;
}

function statTile(kpi, spec, size) {
  const tile = el("div", "stat " + (size || ""));
  tile.appendChild(el("div", "k", spec.label));

  const value = el("div", "v", fmtNum(kpi.value));
  // Proportional figures at display size: tabular-nums makes a large standalone
  // number look loose. Tabular alignment is for table rows and axis ticks.
  value.style.fontVariantNumeric = "normal";
  tile.appendChild(value);

  const sub = el("div", "d");
  const delta = fmtDelta(kpi.delta_12m);
  if (delta && kpi.series && kpi.series.values && kpi.series.values.length > 1) {
    sub.appendChild(el("span", "delta " + delta.cls, delta.text));
  } else if (spec.note) {
    sub.appendChild(el("span", null, spec.note));
  }
  if (sub.childNodes.length) tile.appendChild(sub);

  if (size === "hero" && kpi.series && kpi.series.values && kpi.series.values.length > 1) {
    tile.appendChild(sparkline(kpi.series.values, T.brand));
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
    headers = ["Task", "Tag", "Models"];
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
      tr.appendChild(el("td", isNumber ? "num" : null, isNumber ? fmtNum(cell) : String(cell == null ? "" : cell)));
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

  // Built on first open: 40-odd tables' worth of DOM is not worth pre-rendering.
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

/* --------------------------------------------------------------- card */
function chartCard(chart, data, registry) {
  const card = el("div", "card span-" + (chart.span || 6) + (chart.lead ? " lead" : ""));

  const head = el("div", "phead");
  head.appendChild(el("h3", null, chart.title));
  const meta = el("div", "pmeta");
  head.appendChild(meta);
  card.appendChild(head);

  // Resolve the metric — either a plain path or the first of several toggle sources.
  const sources = chart.toggles && chart.toggles.length
    ? chart.toggles
    : [{ label: null, data: chart.data }];
  let active = 0;
  let metric = getByPath(data.sections, sources[0].data);

  if (!hasData(chart, metric)) {
    // An empty card that says why beats a hole in the grid.
    const note = el("div", "empty",
      chart.emptyNote || "No data in this snapshot yet.");
    card.appendChild(note);
    return card;
  }

  if (metric.n != null) {
    const count = el("span", "pcount", "n=" + fmtNum(metric.n));
    meta.appendChild(count);
  }

  const insight = el("p", "insight", metric.insight || "");
  if (metric.insight) card.appendChild(insight);

  if (chart.desc) {
    const info = el("button", "info hovertip", "i");
    info.type = "button";
    info.setAttribute("data-tip", chart.desc);
    info.setAttribute("aria-label", "How this is measured: " + chart.desc);
    meta.appendChild(info);
  }

  const canvas = el("div", "chart " + (chart.height || (chart.lead ? "h-lg" : "h-md")));
  canvas.setAttribute("role", "img");
  canvas.setAttribute("aria-label", chart.title + ". " + (metric.insight || "") +
    " The same data is available as a table below this chart.");
  card.appendChild(canvas);

  let drill = drillDown(chart, metric, csvFor(sources[0].data));
  card.appendChild(drill);

  const instance = echarts.init(canvas, null, { renderer: "canvas" });
  instance.setOption(buildOption(chart, metric));
  registry.push(instance);

  // Metric toggles change WHICH measure the card encodes — they are not filters
  // (a filter would belong in one row above everything it scopes).
  if (sources.length > 1) {
    const toggle = el("div", "toggle");
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
        // Rebuild the drill-down against the new measure.
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

function csvFor(path) {
  // Synthetic, client-side metrics (the landing page's growth index) have no
  // exported CSV, so they get no download link rather than a broken one.
  if (!path || String(path).indexOf("__") === 0) return null;
  return "data/tables/" + String(path).replace(/\./g, "_") + ".csv";
}
