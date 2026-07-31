/* ECharts option builders.

   Follows the `dataviz` craft rules, with colours from the Ersilia tokens:
     - thin marks, 4px rounded data-ends anchored to the baseline, 2px lines
     - SOLID hairline grid one shade off the surface (never dashed)
     - selective direct labels only (the extreme and the endpoint), never a value
       on every point; a legend whenever there are >= 2 series
     - a 2px surface gap between adjacent/stacked fills instead of mark borders
     - NO dual-axis charts: two measures of different scale become either two
       stacked facets sharing one x, or an index to a common base
     - text always wears ink tokens, never the series colour
   Every chart also ships a drill-down table (see cards.js), which is both the
   accessible equivalent for these canvases and the documented contrast relief
   for the two sub-3:1 palette slots. */

/* ---------------------------------------------------------------- basics */
function base() {
  return {
    animationDuration: 260,
    textStyle: { fontFamily: T.sans, color: T.ink, fontSize: 11 },
    grid: { left: 4, right: 14, top: 14, bottom: 2, containLabel: true },
    tooltip: {
      backgroundColor: T.ink,
      borderWidth: 0,
      padding: [7, 10],
      textStyle: { color: "#fff", fontSize: 11.5, fontFamily: T.sans },
      extraCssText: "box-shadow:0 6px 20px rgba(44,62,80,.18);border-radius:8px;",
    },
  };
}

/* Recessive axis: solid hairlines, no dashes, no ticks. */
function axis(extra) {
  return Object.assign({
    axisLine: { lineStyle: { color: T.axis } },
    axisTick: { show: false },
    axisLabel: { color: T.faint, fontSize: 10, fontFamily: T.mono },
    splitLine: { lineStyle: { color: T.axis, type: "solid" } },
  }, extra || {});
}

function catAxis(labels, extra) {
  const compact = labels.length > 10;
  // A long quarterly axis becomes a wall of rotated text; show every other tick
  // past 20 and every third past 40, and let the tooltip carry the rest.
  const stride = labels.length > 40 ? 2 : (labels.length > 20 ? 1 : 0);
  return Object.assign(axis({
    type: "category",
    data: labels.map(String),
    splitLine: { show: false },
    axisLabel: {
      color: T.faint, fontSize: 10, fontFamily: T.mono,
      interval: stride,
      rotate: labels.length > 8 ? 38 : 0,
      formatter: compact ? shortQuarter : undefined,
    },
  }), extra || {});
}

function valAxis(extra) {
  return Object.assign(axis({
    type: "value",
    axisLine: { show: false },
    axisLabel: { color: T.faint, fontSize: 10, fontFamily: T.mono, formatter: fmtCompact },
  }), extra || {});
}

function legend(names) {
  return {
    top: 0, right: 0, itemWidth: 9, itemHeight: 9, itemGap: 12, icon: "roundRect",
    data: names,
    textStyle: { color: T.muted, fontSize: 11, fontFamily: T.sans },
  };
}

/* Selective direct labels: only the largest value and the final value get a
   number. Everything else is carried by the axis, the tooltip and the table. */
function selectiveLabel(values, position) {
  const max = Math.max.apply(null, values.map(Number));
  const lastIndex = values.length - 1;
  return {
    show: true,
    position: position || "top",
    color: T.muted,
    fontSize: 10,
    fontFamily: T.mono,
    formatter: (p) => (Number(p.value) === max || p.dataIndex === lastIndex ? fmtCompact(p.value) : ""),
  };
}

function seriesColors(metric, count) {
  // The exporter can name status semantics for a metric; honour them so a state
  // keeps one colour everywhere. Otherwise take fixed categorical slots.
  const semantics = metric && metric.semantics;
  if (Array.isArray(semantics)) return semantics.map((s, i) => semanticColor(s, i));
  return Array.from({ length: count }, (_, i) => catColor(i));
}

/* ------------------------------------------------------- bars and columns */
function optBar(d) {
  const o = base();
  o.grid.top = 24; // headroom for the label above the tallest bar
  o.tooltip.trigger = "axis";
  o.tooltip.axisPointer = { type: "shadow", shadowStyle: { color: alpha(T.brand, 0.06) } };
  o.tooltip.valueFormatter = fmtNum;
  o.xAxis = catAxis(d.labels);
  o.yAxis = valAxis();
  o.series = [{
    type: "bar", data: d.values, barMaxWidth: 34,
    // Rounded data-end only; the baseline end stays square so the bar sits on the axis.
    itemStyle: { color: catColor(0), borderRadius: [4, 4, 0, 0] },
    label: selectiveLabel(d.values, "top"),
  }];
  return o;
}

function optHBar(d) {
  const o = base();
  o.grid.right = 30;
  o.tooltip.trigger = "axis";
  o.tooltip.axisPointer = { type: "shadow", shadowStyle: { color: alpha(T.brand, 0.06) } };
  o.tooltip.valueFormatter = (v) => fmtNum(v) + (d.unit ? " " + d.unit : "");
  const labels = d.labels.slice().reverse();
  const values = d.values.slice().reverse();
  o.xAxis = valAxis({ axisLabel: { show: false }, splitLine: { show: false } });
  o.yAxis = axis({
    type: "category", data: labels, splitLine: { show: false }, axisLine: { show: false },
    axisLabel: { color: T.ink, fontSize: 11, fontFamily: T.sans, width: 150, overflow: "truncate" },
  });
  o.series = [{
    type: "bar", data: values, barMaxWidth: 15,
    itemStyle: { color: catColor(0), borderRadius: [0, 4, 4, 0] },
    // A horizontal bar chart is a ranking: every value label sits outside the
    // bar end where it always fits, so no label is ever clipped.
    label: {
      show: true, position: "right", color: T.muted, fontSize: 10, fontFamily: T.mono,
      formatter: (p) => fmtNum(p.value),
    },
  }];
  return o;
}

/* Ordered buckets (tenure bands, income groups): one hue, monotone ramp, so the
   order is visible in the colour. Not a value-ramp — the ramp follows position. */
function optOrdinalBar(d) {
  const o = optBar(d);
  const n = d.labels.length;
  o.series[0].data = d.values.map((v, i) => ({
    value: v,
    itemStyle: { color: seqAt(n > 1 ? i / (n - 1) : 0), borderRadius: [4, 4, 0, 0] },
  }));
  return o;
}

/* --------------------------------------------------------- lines and areas */
function optArea(d) {
  const o = base();
  // The end label sits past the last point, so the plot needs room for it or the
  // number gets clipped to its first digit.
  o.grid.right = 48;
  o.tooltip.trigger = "axis";
  o.tooltip.axisPointer = { type: "line", lineStyle: { color: T.border, width: 1 } };
  o.tooltip.valueFormatter = fmtNum;
  o.xAxis = catAxis(d.labels, { boundaryGap: false });
  o.yAxis = valAxis();
  const color = catColor(0);
  o.series = [{
    type: "line", data: d.values, smooth: 0.25, showSymbol: false, symbolSize: 9,
    lineStyle: { color: color, width: 2 },
    itemStyle: { color: color, borderColor: T.surface, borderWidth: 2 },
    areaStyle: {
      color: {
        type: "linear", x: 0, y: 0, x2: 0, y2: 1,
        colorStops: [{ offset: 0, color: alpha(color, 0.22) }, { offset: 1, color: alpha(color, 0.02) }],
      },
    },
    // Only the endpoint is labelled — the point of a cumulative curve is where it ends.
    endLabel: { show: true, color: T.muted, fontSize: 10, fontFamily: T.mono, formatter: (p) => fmtNum(p.value) },
  }];
  return o;
}

/* Several measures of different magnitude on ONE axis, indexed to a common base
   (share of today's total). This is the sanctioned alternative to a dual axis. */
function optIndexedGrowth(d) {
  const o = base();
  o.grid.top = 28;
  o.tooltip.trigger = "axis";
  o.tooltip.axisPointer = { type: "line", lineStyle: { color: T.border, width: 1 } };
  o.tooltip.valueFormatter = (v) => (v == null ? "—" : Number(v).toFixed(0) + "% of today");
  o.legend = legend(d.series.map((s) => s.name));
  o.xAxis = catAxis(d.labels, { boundaryGap: false });
  o.yAxis = valAxis({ max: 100, axisLabel: { color: T.faint, fontSize: 10, fontFamily: T.mono, formatter: "{value}%" } });
  o.series = d.series.map((s, i) => ({
    type: "line", name: s.name, data: s.values, smooth: 0.25, showSymbol: false, symbolSize: 9,
    lineStyle: { color: catColor(i), width: 2 },
    itemStyle: { color: catColor(i), borderColor: T.surface, borderWidth: 2 },
  }));
  return o;
}

/* -------------------------------------------------------------- composites */
function optMultiBar(d, stacked) {
  const o = base();
  o.grid.top = 30;
  o.tooltip.trigger = "axis";
  o.tooltip.axisPointer = { type: "shadow", shadowStyle: { color: alpha(T.brand, 0.06) } };
  o.tooltip.valueFormatter = fmtNum;
  o.legend = legend(d.series.map((s) => s.name));
  o.xAxis = catAxis(d.labels);
  o.yAxis = valAxis();
  const colors = seriesColors(d, d.series.length);
  const kinds = d.kinds || [];
  o.series = d.series.map((s, i) => {
    const asLine = kinds[i] === "line";
    if (asLine) {
      return {
        type: "line", name: s.name, data: s.values, smooth: 0.2,
        symbol: "circle", symbolSize: 8, z: 3,
        lineStyle: { color: colors[i], width: 2 },
        itemStyle: { color: colors[i], borderColor: T.surface, borderWidth: 2 },
      };
    }
    return {
      type: "bar", name: s.name, data: s.values, stack: stacked ? "s" : undefined,
      barMaxWidth: 34, barGap: "12%",
      itemStyle: {
        color: colors[i],
        // 2px surface gap instead of a border around each segment.
        borderColor: T.surface, borderWidth: stacked ? 2 : 0,
        borderRadius: stacked ? 0 : [3, 3, 0, 0],
      },
    };
  });
  return o;
}

/* Two measures whose scales don't compare: stacked facets sharing one x axis.
   Each panel keeps its own y, so no scale alignment is invented. */
function optFacets(d) {
  const o = base();
  const names = d.series.map((s) => s.name);
  o.tooltip.trigger = "axis";
  o.tooltip.axisPointer = { type: "line", lineStyle: { color: T.border, width: 1 } };
  o.axisPointer = { link: [{ xAxisIndex: "all" }] };
  o.tooltip.valueFormatter = fmtNum;
  o.grid = [
    { left: 4, right: 16, top: 24, height: "36%", containLabel: true },
    { left: 4, right: 16, top: "58%", height: "34%", containLabel: true },
  ];
  o.xAxis = [
    catAxis(d.labels, { gridIndex: 0, axisLabel: { show: false } }),
    catAxis(d.labels, { gridIndex: 1 }),
  ];
  o.yAxis = [
    valAxis({ gridIndex: 0, name: names[0], nameLocation: "end", nameGap: 6,
              nameTextStyle: { color: T.muted, fontSize: 10, align: "left" } }),
    valAxis({ gridIndex: 1, name: names[1], nameLocation: "end", nameGap: 6,
              nameTextStyle: { color: T.muted, fontSize: 10, align: "left" } }),
  ];
  o.series = [
    {
      type: "bar", name: names[0], data: d.series[0].values,
      xAxisIndex: 0, yAxisIndex: 0, barMaxWidth: 30,
      itemStyle: { color: catColor(0), borderRadius: [4, 4, 0, 0] },
    },
    {
      type: "line", name: names[1], data: d.series[1].values,
      xAxisIndex: 1, yAxisIndex: 1, smooth: 0.25, showSymbol: false,
      lineStyle: { color: catColor(2), width: 2 },
      itemStyle: { color: catColor(2) },
      areaStyle: {
        color: {
          type: "linear", x: 0, y: 0, x2: 0, y2: 1,
          colorStops: [{ offset: 0, color: alpha(catColor(2), 0.2) }, { offset: 1, color: alpha(catColor(2), 0.02) }],
        },
      },
    },
  ];
  return o;
}

/* ------------------------------------------------------------ part-to-whole */
function optDonut(d) {
  const o = base();
  o.tooltip.trigger = "item";
  const total = d.values.reduce((a, b) => a + Number(b), 0);
  const withPct = showsPercentages(d.n == null ? total : d.n);
  o.tooltip.formatter = (p) =>
    p.name + "<br/><b>" + fmtNum(p.value) + "</b>" + (withPct ? " · " + fmtPct(p.value, total) : "");
  o.legend = {
    type: "scroll", orient: "vertical", right: 0, top: "middle",
    itemWidth: 9, itemHeight: 9, itemGap: 9, icon: "roundRect",
    textStyle: { color: T.muted, fontSize: 11, fontFamily: T.sans },
  };
  const bySemantics = d.semantics && !Array.isArray(d.semantics);
  o.series = [{
    type: "pie", radius: ["52%", "76%"], center: ["34%", "50%"], avoidLabelOverlap: true,
    // 2px surface gap between segments rather than an outline.
    itemStyle: { borderColor: T.surface, borderWidth: 2 },
    label: { show: false }, labelLine: { show: false },
    data: d.labels.map((label, i) => ({
      name: label,
      value: d.values[i],
      itemStyle: { color: bySemantics ? semanticColor(d.semantics[label], i) : catColor(i) },
    })),
  }];
  return o;
}

/* Two categories are not a pie: one 100%-wide split bar with both values
   written on it reads instantly and never needs a legend. */
function optShare(d) {
  const o = base();
  o.grid = { left: 0, right: 0, top: 30, bottom: 30 };
  o.tooltip.trigger = "item";
  const total = d.values.reduce((a, b) => a + Number(b), 0);
  o.tooltip.formatter = (p) => p.seriesName + ": <b>" + fmtNum(p.value) + "</b> · " + fmtPct(p.value, total);
  o.xAxis = { type: "value", max: total, show: false };
  o.yAxis = { type: "category", data: [""], show: false };
  const bySemantics = d.semantics && !Array.isArray(d.semantics);
  o.series = d.labels.map((label, i) => ({
    type: "bar", name: label, stack: "s", data: [d.values[i]], barWidth: 42,
    itemStyle: {
      color: bySemantics ? semanticColor(d.semantics[label], i) : catColor(i),
      borderColor: T.surface, borderWidth: 2,
      borderRadius: i === 0 ? [6, 0, 0, 6] : (i === d.labels.length - 1 ? [0, 6, 6, 0] : 0),
    },
    label: {
      show: true, position: "inside", color: "#fff", fontFamily: T.sans, fontSize: 11, fontWeight: 600,
      // Only write inside the segment when it is wide enough to hold the text.
      formatter: (p) => (p.value / total > 0.14 ? fmtPct(p.value, total) : ""),
    },
  }));
  o.legend = {
    bottom: 0, left: "center", itemWidth: 9, itemHeight: 9, itemGap: 14, icon: "roundRect",
    textStyle: { color: T.muted, fontSize: 11, fontFamily: T.sans },
    formatter: (name) => {
      const i = d.labels.indexOf(name);
      return name + "  " + fmtNum(d.values[i]);
    },
  };
  return o;
}

function optTreemap(d) {
  const o = base();
  o.tooltip.trigger = "item";
  o.tooltip.formatter = (p) => p.name + ": <b>" + fmtNum(p.value) + "</b>";
  o.series = [{
    type: "treemap", roam: false, nodeClick: false, breadcrumb: { show: false },
    width: "100%", height: "100%", top: 2, left: 0, right: 0, bottom: 0,
    itemStyle: { borderColor: T.surface, borderWidth: 2, gapWidth: 2 },
    label: { show: true, color: "#fff", fontFamily: T.sans, fontSize: 11.5, formatter: "{b}\n{c}" },
    data: d.labels.map((label, i) => ({
      name: label, value: d.values[i], itemStyle: { color: catColor(i % 6) },
    })),
  }];
  return o;
}

/* Two-level hierarchy (task -> tag). Parents take categorical slots; children
   inherit the parent hue, so the grouping is what the colour encodes. */
function optSunburst(d) {
  const o = base();
  o.tooltip.trigger = "item";
  o.tooltip.formatter = (p) => p.name + ": <b>" + fmtNum(p.value) + "</b>";
  // Leave a margin inside the canvas: outer-ring labels are drawn radially and
  // would otherwise run past the edge and be clipped by the card.
  o.series = [{
    type: "sunburst", radius: [14, "72%"], center: ["50%", "50%"], nodeClick: false,
    itemStyle: { borderColor: T.surface, borderWidth: 2 },
    emphasis: { focus: "ancestor" },
    levels: [
      {},
      { r0: 14, r: "44%",
        label: { rotate: 0, color: "#fff", fontSize: 10.5, fontFamily: T.sans,
                 width: 62, overflow: "truncate" } },
      { r0: "46%", r: "72%",
        label: { color: T.ink, fontSize: 9.5, fontFamily: T.sans,
                 // Only label a leaf wide enough to read; the rest are in the
                 // tooltip and the table.
                 minAngle: 14, width: 76, overflow: "truncate" } },
    ],
    data: (d.tree || []).map((parent, i) => ({
      name: parent.name,
      itemStyle: { color: catColor(i % 6) },
      children: (parent.children || []).map((child) => ({
        name: child.name, value: child.value,
        itemStyle: { color: alpha(catColor(i % 6), 0.55) },
      })),
    })),
  }];
  return o;
}

/* --------------------------------------------------------------- scatter */
/* Single hue: identity is the label, magnitude is position and size. An
   all-pairs form can only carry two categorical hues, so it carries none. */
function optScatter(d, opts) {
  const conf = opts || {};
  const points = d.points || [];
  const xKey = conf.x || "stars";
  const yKey = conf.y || "forks";
  const sizeKey = conf.size || "contributors";
  const rows = points.map((p) => (Array.isArray(p)
    ? { x: p[0], y: p[1], size: p[2], name: p[3] }
    : { x: p[xKey], y: p[yKey], size: p[sizeKey], name: p.name }));
  const maxSize = Math.max(1, ...rows.map((r) => Number(r.size) || 0));

  const o = base();
  o.grid = { left: 6, right: 20, top: 18, bottom: 4, containLabel: true };
  o.tooltip.trigger = "item";
  o.tooltip.formatter = (p) => {
    const r = p.data;
    return "<b>" + r[3] + "</b><br/>" + conf.xLabel + " " + fmtNum(r[0]) +
      " · " + conf.yLabel + " " + fmtNum(r[1]) +
      (conf.sizeLabel ? " · " + conf.sizeLabel + " " + fmtNum(r[2]) : "");
  };
  const nameStyle = { color: T.muted, fontFamily: T.sans, fontSize: 10 };
  o.xAxis = valAxis({ name: conf.xLabel, nameLocation: "middle", nameGap: 24, nameTextStyle: nameStyle });
  o.yAxis = valAxis({ name: conf.yLabel, nameLocation: "middle", nameGap: 32, nameTextStyle: nameStyle });
  const color = catColor(0);
  const topX = Math.max(...rows.map((r) => Number(r.x) || 0));
  const topY = Math.max(...rows.map((r) => Number(r.y) || 0));
  o.series = [{
    type: "scatter",
    data: rows.map((r) => [r.x, r.y, r.size, r.name]),
    symbolSize: (v) => 8 + Math.sqrt((Number(v[2]) || 0) / maxSize) * 26,
    itemStyle: { color: alpha(color, 0.72), borderColor: T.surface, borderWidth: 2 },
    emphasis: { itemStyle: { color: color } },
    // Label only the extremes; a name on all 141 dots is unreadable.
    label: {
      show: true, position: "top", color: T.muted, fontSize: 9.5, fontFamily: T.sans,
      formatter: (p) => (p.data[0] === topX || p.data[1] === topY ? p.data[3] : ""),
    },
  }];
  return o;
}

/* 2x2 small multiples: the same repositories under four metric pairs. */
function optSmallMultiples(d) {
  const points = d.points || [];
  const pairs = (d.pairs || []).slice(0, 4);
  const o = base();
  o.tooltip.trigger = "item";
  o.tooltip.formatter = (p) => "<b>" + p.data[2] + "</b><br/>" + p.seriesName + ": " +
    fmtNum(p.data[0]) + " / " + fmtNum(p.data[1]);
  o.grid = [];
  o.xAxis = [];
  o.yAxis = [];
  o.series = [];
  const color = catColor(0);
  const nameStyle = { color: T.muted, fontFamily: T.sans, fontSize: 9.5 };
  pairs.forEach((pair, i) => {
    const left = i % 2 === 0 ? "5%" : "55%";
    const top = i < 2 ? "6%" : "56%";
    o.grid.push({ left: left, top: top, width: "36%", height: "34%", containLabel: true });
    o.xAxis.push(valAxis({
      gridIndex: i, name: pair.xLabel, nameLocation: "middle", nameGap: 20, nameTextStyle: nameStyle,
    }));
    o.yAxis.push(valAxis({
      gridIndex: i, name: pair.yLabel, nameLocation: "middle", nameGap: 26, nameTextStyle: nameStyle,
    }));
    o.series.push({
      type: "scatter", name: pair.xLabel + " vs " + pair.yLabel,
      xAxisIndex: i, yAxisIndex: i, symbolSize: 8,
      data: points.map((p) => [p[pair.x], p[pair.y], p.name]),
      itemStyle: { color: alpha(color, 0.55), borderColor: T.surface, borderWidth: 1 },
      emphasis: { itemStyle: { color: color } },
      // Name only the panel's own outlier, so each panel says which repository is
      // driving its shape without 141 overlapping labels.
      label: {
        show: true, position: "left", color: T.muted, fontSize: 9, fontFamily: T.sans,
        formatter: (p) => {
          const maxX = Math.max(...points.map((q) => q[pair.x] || 0));
          return p.data[0] === maxX && maxX > 0 ? p.data[2] : "";
        },
      },
    });
  });
  return o;
}

/* ------------------------------------------------------- distribution */
function optHistogram(d) {
  const o = optBar(d);
  o.grid.top = 26; // room for the mean marker's label above the tallest bar
  o.series[0].barMaxWidth = 46;
  // Adjacent bars still get the 2px surface gap; a histogram reads as contiguous
  // bins, so the gap is small rather than absent.
  o.series[0].barCategoryGap = "16%";
  o.series[0].itemStyle.borderColor = T.surface;
  o.series[0].itemStyle.borderWidth = 1;
  o.series[0].label = { show: false };
  o.tooltip.valueFormatter = (v) => fmtNum(v) + " people";
  if (d.mean != null) {
    // Where the mean falls between bucket edges, so the marker lands honestly.
    const index = d.labels.findIndex((label) => {
      const parts = String(label).split(/[–+]/);
      const low = parseFloat(parts[0]);
      const high = parts[1] === "" || parts[1] == null ? Infinity : parseFloat(parts[1]);
      return d.mean >= low && d.mean < high;
    });
    if (index >= 0) {
      o.series[0].markLine = {
        symbol: "none", silent: true,
        lineStyle: { color: T.bad, width: 1.5 },
        label: {
          show: true, position: "end",
          // ECharts rotates a vertical mark-line label by default, which renders
          // it sideways across the bars and unreadable.
          rotate: 0, distance: 4, align: "center", verticalAlign: "bottom",
          color: T.bad, fontSize: 10, fontFamily: T.mono, backgroundColor: T.surface,
          padding: [2, 3],
          formatter: "mean " + d.mean + (d.unit ? " " + d.unit : ""),
        },
        data: [{ xAxis: index }],
      };
    }
  }
  return o;
}

/* Lorenz curve: how unevenly a total is spread. The diagonal is perfect equality. */
function optLorenz(d) {
  const o = base();
  o.tooltip.trigger = "axis";
  o.tooltip.axisPointer = { type: "line", lineStyle: { color: T.border, width: 1 } };
  const nameStyle = { color: T.muted, fontFamily: T.sans, fontSize: 10 };
  o.tooltip.formatter = (params) => {
    const p = params[0];
    return "Least active " + Number(p.axisValue).toFixed(0) + "% of repositories<br/>hold <b>" +
      Number(p.data).toFixed(0) + "%</b> of commits";
  };
  o.xAxis = valAxis({
    type: "value", max: 100, name: "% of repositories", nameLocation: "middle",
    nameGap: 24, nameTextStyle: nameStyle, axisLabel: { color: T.faint, fontSize: 10, fontFamily: T.mono, formatter: "{value}%" },
  });
  o.yAxis = valAxis({
    max: 100, name: "% of commits", nameLocation: "middle", nameGap: 34, nameTextStyle: nameStyle,
    axisLabel: { color: T.faint, fontSize: 10, fontFamily: T.mono, formatter: "{value}%" },
  });
  const color = catColor(0);
  o.series = [
    {
      type: "line", name: "Equality", data: [[0, 0], [100, 100]],
      showSymbol: false, silent: true, lineStyle: { color: T.border, width: 1.5 },
    },
    {
      type: "line", name: "Commits", showSymbol: false, smooth: 0,
      data: d.labels.map((label, i) => [Number(label), d.values[i]]),
      lineStyle: { color: color, width: 2 },
      areaStyle: { color: alpha(color, 0.14) },
    },
  ];
  return o;
}

/* ----------------------------------------------------------- matrices */
function isPercentUnit(d) {
  return (d.unit || "").indexOf("%") >= 0;
}

function optHeatmap(d) {
  const cells = d.cells || [];
  const max = Math.max(1, ...cells.map((c) => c[2]));
  const counts = {};
  (d.counts || []).forEach((c) => { counts[c[0] + ":" + c[1]] = c; });

  const o = base();
  o.grid = { left: 4, right: 8, top: 10, bottom: 44, containLabel: true };
  o.tooltip.trigger = "item";
  // Cells are objects (each carries its own label colour), so read p.value —
  // p.data is the wrapper, not the [x, y, v] triple.
  o.tooltip.formatter = (p) => {
    const detail = counts[p.value[0] + ":" + p.value[1]];
    const head = d.y[p.value[1]] + " · " + d.x[p.value[0]];
    const value = isPercentUnit(d) ? p.value[2] + "%" : fmtNum(p.value[2]);
    return head + "<br/><b>" + value + "</b>" +
      (detail ? " (" + fmtNum(detail[2]) + " of " + fmtNum(detail[3]) + ")" : "");
  };
  o.xAxis = axis({
    type: "category", data: d.x, splitLine: { show: false }, axisLine: { show: false },
    axisLabel: { color: T.muted, fontSize: 10.5, fontFamily: T.sans, rotate: d.x.length > 5 ? 30 : 0 },
  });
  o.yAxis = axis({
    type: "category", data: d.y, splitLine: { show: false }, axisLine: { show: false },
    axisLabel: { color: T.muted, fontSize: 10.5, fontFamily: T.sans },
  });
  o.visualMap = {
    min: 0, max: max, orient: "horizontal", left: "center", bottom: 0, calculable: false,
    itemWidth: 11, itemHeight: 74,
    inRange: { color: T.seq },
    text: [d.unit || "more", ""],
    textStyle: { color: T.muted, fontSize: 10, fontFamily: T.sans },
  };
  o.series = [{
    type: "heatmap", data: cells,
    // 2px surface gap between cells; a cell with no judgeable data has no mark at
    // all, which is why every present cell is labelled — otherwise a genuine 0
    // (lightest ramp step) is indistinguishable from an absent cell.
    itemStyle: { borderColor: T.surface, borderWidth: 2, borderRadius: 3 },
    label: {
      show: true, fontSize: 10, fontFamily: T.mono,
      formatter: (p) => (isPercentUnit(d) ? p.value[2] + "%" : fmtNum(p.value[2])),
      color: T.ink,
    },
    emphasis: { itemStyle: { borderColor: T.ink, borderWidth: 2 } },
  }];
  // Per-cell label colour, since ECharts has no conditional label colour.
  o.series[0].data = cells.map((c) => ({
    value: c,
    label: { color: c[2] >= max * 0.62 ? "#fff" : T.ink },
  }));
  return o;
}

/* ------------------------------------------------------------- timeline */
/* Gantt via a custom series: one bar per project between start and end, plus a
   "today" rule. Shows concurrency and overrun, which a per-quarter count cannot. */
function optGantt(d) {
  const rows = (d.rows || []).slice();
  const names = rows.map((r) => r.name);
  const toDay = (iso) => new Date(iso + "T00:00:00Z").getTime();
  const semantics = d.semantics || {};

  const o = base();
  // Top padding clears the "today" label, which sits above the plot area.
  o.grid = { left: 4, right: 20, top: 22, bottom: 4, containLabel: true };
  o.tooltip.trigger = "item";
  o.tooltip.formatter = (p) => {
    const r = rows[p.dataIndex];
    return "<b>" + r.name + "</b><br/>" + r.status + " · " + r.months + " months<br/>" +
      r.start + " → " + (r.open ? "open" : r.end);
  };
  o.xAxis = axis({
    type: "time", splitLine: { lineStyle: { color: T.axis, type: "solid" } },
    axisLabel: { color: T.faint, fontSize: 10, fontFamily: T.mono },
  });
  o.yAxis = axis({
    type: "category", data: names, inverse: true, splitLine: { show: false }, axisLine: { show: false },
    axisLabel: {
      // interval 0 forces a label on every row. Without it ECharts thins them to
      // fit and half the projects end up as unlabelled bars.
      interval: 0,
      color: T.ink, fontSize: names.length > 28 ? 9.5 : 10.5, fontFamily: T.sans,
      width: 148, overflow: "truncate",
    },
  });
  o.series = [{
    type: "custom",
    renderItem: (params, api) => {
      const index = api.value(3);
      const start = api.coord([api.value(0), index]);
      const end = api.coord([api.value(1), index]);
      const height = Math.max(7, api.size([0, 1])[1] * 0.52);
      const shape = echarts.graphic.clipRectByRect({
        x: start[0], y: start[1] - height / 2,
        width: Math.max(end[0] - start[0], 2), height: height,
      }, {
        x: params.coordSys.x, y: params.coordSys.y,
        width: params.coordSys.width, height: params.coordSys.height,
      });
      return shape && {
        type: "rect", shape: Object.assign(shape, { r: 3 }),
        style: api.style({ fill: api.visual("color") }),
      };
    },
    encode: { x: [0, 1], y: 3 },
    data: rows.map((r, i) => ({
      value: [toDay(r.start), toDay(r.end), r.name, i],
      itemStyle: { color: semanticColor(semantics[r.status], 0) },
    })),
    markLine: d.today ? {
      symbol: "none", silent: true,
      lineStyle: { color: T.bad, width: 1.5 },
      label: { show: true, position: "start", color: T.bad, fontSize: 10, fontFamily: T.sans, formatter: "today" },
      data: [{ xAxis: toDay(d.today) }],
    } : undefined,
  }];
  return o;
}

/* ------------------------------------------------------------------ map */
/* Data-table country names -> world.geo.json feature names (short forms). */
const MAP_ALIAS = {
  "united states of america": "United States", "usa": "United States", "u.s.a.": "United States",
  "czech republic": "Czech Rep.", "czechia": "Czech Rep.",
  "russian federation": "Russia", "south korea": "Korea", "republic of korea": "Korea",
  "democratic republic of the congo": "Dem. Rep. Congo", "republic of the congo": "Congo",
  "bosnia and herzegovina": "Bosnia and Herz.", "dominican republic": "Dominican Rep.",
  "tanzania, united republic of": "Tanzania", "ivory coast": "Côte d'Ivoire",
  "central african republic": "Central African Rep.", "south sudan": "S. Sudan",
  "equatorial guinea": "Eq. Guinea", "solomon islands": "Solomon Is.",
  "united kingdom": "United Kingdom", "viet nam": "Vietnam", "syrian arab republic": "Syria",
  "lao people's democratic republic": "Laos", "iran, islamic republic of": "Iran",
  "moldova, republic of": "Moldova", "north macedonia": "Macedonia",
  "eswatini": "Swaziland", "myanmar": "Myanmar", "cabo verde": "Cape Verde",
};
function mapName(name) {
  const key = String(name).trim().toLowerCase();
  return MAP_ALIAS[key] || String(name).trim();
}

function optMap(d, label) {
  const max = Math.max(1, ...d.values.map(Number));
  return {
    textStyle: { fontFamily: T.sans, color: T.ink },
    animationDuration: 260,
    tooltip: {
      trigger: "item", backgroundColor: T.ink, borderWidth: 0, padding: [7, 10],
      textStyle: { color: "#fff", fontSize: 11.5, fontFamily: T.sans },
      extraCssText: "box-shadow:0 6px 20px rgba(44,62,80,.18);border-radius:8px;",
      formatter: (p) => p.name + "<br/><b>" +
        (p.value == null || Number.isNaN(p.value) ? "none recorded" : fmtNum(p.value) + " " + (label || "")) + "</b>",
    },
    visualMap: {
      min: 0, max: max, left: 6, bottom: 10, orient: "horizontal", calculable: false,
      itemWidth: 11, itemHeight: 80,
      // One hue, light -> dark. Countries with no record keep the neutral fill.
      inRange: { color: T.seq },
      text: [fmtNum(max), "1"],
      textStyle: { color: T.muted, fontSize: 10, fontFamily: T.mono },
    },
    series: [{
      type: "map", map: "world", roam: false,
      data: d.labels.map((l, i) => ({ name: mapName(l), value: d.values[i] })),
      itemStyle: { areaColor: T.nullFill, borderColor: T.surface, borderWidth: 0.6 },
      emphasis: { label: { show: false }, itemStyle: { areaColor: T.plum } },
      select: { disabled: true },
    }],
  };
}

/* ------------------------------------------------------------ dispatch */
const BUILDERS = {
  bar: optBar,
  ordinalbar: optOrdinalBar,
  hbar: optHBar,
  area: optArea,
  line: optArea,
  growth: optIndexedGrowth,
  donut: optDonut,
  share: optShare,
  stackbar: (d) => optMultiBar(d, true),
  groupbar: (d) => optMultiBar(d, false),
  facets: optFacets,
  treemap: optTreemap,
  sunburst: optSunburst,
  histogram: optHistogram,
  lorenz: optLorenz,
  heatmap: optHeatmap,
  gantt: optGantt,
};

function buildOption(chart, d) {
  if (chart.type === "scatter") return optScatter(d, chart.scatter || {});
  if (chart.type === "smallmultiples") return optSmallMultiples(d);
  if (chart.type === "map") return optMap(d, chart.mapLabel);
  const builder = BUILDERS[chart.type] || optBar;
  return builder(d);
}

/* Does this metric have anything to draw? */
function hasData(chart, d) {
  if (!d) return false;
  if (chart.type === "scatter" || chart.type === "smallmultiples") {
    return Array.isArray(d.points) && d.points.length > 0;
  }
  if (chart.type === "gantt") return Array.isArray(d.rows) && d.rows.length > 0;
  if (chart.type === "heatmap") return Array.isArray(d.cells) && d.cells.length > 0;
  if (chart.type === "sunburst") return Array.isArray(d.tree) && d.tree.length > 0;
  if (d.series) return Array.isArray(d.labels) && d.labels.length > 0 && d.series.length > 0;
  return Array.isArray(d.labels) && d.labels.length > 0;
}
