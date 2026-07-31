/* ECharts option builders — light-ink house style.

   The governing rule here is MINIMAL INK. v2 of this site was 62% bar charts, 26
   of them the identical horizontal bar, which is why it read as a wall of purple.
   So:

     - `optLollipop` replaces the horizontal bar almost everywhere. A dot with a
       hairline leader carries the same comparison with a fraction of the ink, and
       it does not turn into a 1000px smear when the card is wide.
     - Axis lines are gone. Gridlines are gone or reduced to one faint baseline.
       Values are labelled on the mark, so the axis often has nothing left to do.
     - Colour lives in the DATA, never in the chrome. A one-series chart takes the
       single `accent()`; anything categorical takes the fixed palette order. The
       navigation and headers stay grey.
     - No dual-axis charts ever: two measures of different scale become stacked
       facets sharing one x, or an index to a common base.
     - Text wears ink tokens, never the series colour.

   Every chart also ships a drill-down table (cards.js), which is the accessible
   equivalent for a canvas and the documented contrast relief for the two palette
   slots that sit below 3:1 on white. */

/* ---------------------------------------------------------------- basics */
/* Is the chart being drawn into a narrow box?
 *
 * ECharts has no media queries, and the geometry that makes a chart legible at 1100px
 * makes it unreadable at 390px: a 210px label gutter is a comfortable fifth of a wide
 * card and almost the entire width of a phone, which pushed every dot and value off
 * the right edge — labels with no data beside them.
 *
 * cards.js sets this from the measured container width before building the option, and
 * rebuilds when the answer changes. Builders read it for gutters and tick density only;
 * nothing about WHAT is drawn depends on it. */
// Below this container width a chart is treated as narrow. 460px is just above a
// phone-width card (390px viewport minus padding), and just below the narrowest
// desktop card (a 3-of-12 span in a 1080px column is ~250px, so those are narrow too —
// which is correct, they had the same problem in miniature).
const NARROW_WIDTH = 460;
let NARROW = false;
function setNarrow(value) { NARROW = !!value; }
function isNarrow() { return NARROW; }

function base() {
  return {
    animationDuration: T.calm ? 0 : 240,
    textStyle: { fontFamily: T.sans, color: T.ink, fontSize: T.fs.body },
    grid: { left: 2, right: 12, top: 10, bottom: 0, containLabel: true },
    tooltip: {
      backgroundColor: T.ink,
      borderWidth: 0,
      padding: [7, 10],
      textStyle: { color: "#fff", fontSize: T.fs.body, fontFamily: T.sans },
      extraCssText: "box-shadow:0 6px 20px rgba(44,62,80,.16);border-radius:8px;",
    },
  };
}

/* A category axis with nothing but labels — no line, no ticks, no grid.

   Time axes are YEAR-AWARE. Thinning a 24-quarter axis with `interval: 1` dropped
   every other quarter and rotating what was left made it unreadable, so most of the
   time labels on this site were effectively invisible. Instead: mark each year once,
   at its first quarter, horizontally. The reader gets an unambiguous year scale, the
   series keeps its quarterly resolution, and nothing is rotated. */
function catAxis(labels, extra) {
  const strings = labels.map(String);
  const quarterly = strings.length > 0 && strings.every((l) => /^\d{4}Q[1-4]$/.test(l));
  const yearly = !quarterly && strings.length > 0 && strings.every((l) => /^\d{4}$/.test(l));

  let axisLabel;
  if (quarterly) {
    // One label per year, at the first quarter present for that year.
    const firstOfYear = new Set();
    const seen = new Set();
    strings.forEach((l) => {
      const year = l.slice(0, 4);
      if (!seen.has(year)) { seen.add(year); firstOfYear.add(l); }
    });
    // Which year labels can actually be drawn without touching.
    //
    // The naive rule — label the first quarter of every year — collides whenever a
    // series starts mid-year: 2020Q4 and 2021Q1 are ADJACENT columns, so "2020" and
    // "2021" were printed one column apart and ran together into "20202021". That is
    // a function of column spacing, not of screen width, so it happened at 1024px on
    // a wide card too.
    //
    // Instead: keep a year only if it is far enough along the axis from the last one
    // kept. `gap` is in columns, and a 4-character mono label needs roughly three
    // quarter-columns of room at 12px — more when the whole axis is narrow.
    const gap = NARROW ? 5 : 3;
    const candidates = strings
      .map((label, index) => ({ label, index }))
      .filter((c) => firstOfYear.has(c.label));

    // If the FIRST year is a stub — the series begins in 2020Q4, so "2020" owns one
    // column — drop it rather than the year after it. Thinning forwards kept 2020 and
    // dropped 2021, leaving "2020, 2022, 2023…", a sequence with a hole in it that
    // reads as a mistake. Dropping the stub gives an unbroken run of full years, and
    // the axis loses nothing: the first bar is still there, just unlabelled.
    if (candidates.length > 1 && candidates[1].index - candidates[0].index < gap) {
      candidates.shift();
    }

    const keep = new Set();
    let lastKept = -Infinity;
    candidates.forEach((c) => {
      if (c.index - lastKept < gap) return;
      keep.add(c.label);
      lastKept = c.index;
    });
    axisLabel = {
      color: T.muted, fontSize: T.fs.meta, fontFamily: T.mono,
      interval: 0, rotate: 0, margin: 9,
      formatter: (value) => (keep.has(value) ? value.slice(0, 4) : ""),
    };
  } else if (yearly) {
    axisLabel = {
      color: T.muted, fontSize: T.fs.meta, fontFamily: T.mono,
      // Every year, horizontal, unless there are so many that they would collide.
      interval: strings.length > 18 ? 1 : 0, rotate: 0, margin: 8,
    };
  } else {
    // Plain categories: keep them all, truncate rather than rotate.
    axisLabel = {
      color: T.muted, fontSize: T.fs.meta, fontFamily: T.sans,
      interval: 0, rotate: strings.length > 8 ? 30 : 0,
      width: 92, overflow: "truncate", margin: 8,
    };
  }

  return Object.assign({
    type: "category",
    data: strings,
    axisLine: { show: false },
    axisTick: { show: false },
    splitLine: { show: false },
    // A faint tick per year on a quarterly axis, so the year labels have anchors.
    axisLabel: axisLabel,
  }, extra || {});
}

/* A value axis reduced to faint horizontal rules. Often hidden entirely. */
function valAxis(extra) {
  return Object.assign({
    type: "value",
    // A stacked facet panel is ~110px tall on a phone; the default tick count put six
    // labels in it, which merged into a single column of digits.
    splitNumber: NARROW ? 3 : 5,
    axisLine: { show: false },
    axisTick: { show: false },
    splitLine: { lineStyle: { color: T.axis, type: "solid", width: 1 } },
    axisLabel: { color: T.muted, fontSize: T.fs.meta, fontFamily: T.mono, formatter: fmtCompact },
  }, extra || {});
}

function legend(names) {
  return {
    top: 0, right: 0, itemWidth: 8, itemHeight: 8, itemGap: 12, icon: "circle",
    data: names,
    textStyle: { color: T.muted, fontSize: T.fs.meta, fontFamily: T.sans },
  };
}

function valueLabel(position, formatter) {
  return {
    show: true, position: position || "right",
    color: T.muted, fontSize: T.fs.meta, fontFamily: T.mono,
    formatter: formatter || ((p) => fmtNum(p.value)),
  };
}

/* Multi-series colours, in order of preference:

   1. Semantics the exporter named (joined/left, done/stuck) — so a state keeps one
      colour everywhere on the site.
   2. Otherwise the fixed categorical slots, whose ORDER is what makes them
      colour-vision safe. */
function seriesColors(metric, count) {
  const semantics = metric && metric.semantics;
  if (Array.isArray(semantics)) return semantics.map((s, i) => semanticColor(s, i));
  return Array.from({ length: count }, (_, i) => catColor(i));
}

/* -------------------------------------------------------------- lollipop */
/* The workhorse. Replaces the horizontal bar: a dot at the value with a hairline
   leader back to the label. Reads as a ranking, costs almost no ink, and stays
   legible at any card width. */
function optLollipop(d) {
  const prepared = capRows(collapseTies(d), 9);
  const labels = prepared.labels.slice().reverse();
  const values = prepared.values.slice().reverse();
  const color = accent();
  const max = Math.max.apply(null, values.map(Number));

  const o = base();
  // Room on the right for the value, and a wide label gutter so names like
  // "Bill and Melinda Gates Foundation" stop truncating to an ellipsis.
  o.grid = { left: 2, right: NARROW ? 38 : 54, top: 6, bottom: 2, containLabel: true };
  // A category axis spreads its rows over the WHOLE plot height, so three or four
  // rows in a tall card came out as dots marooned in white space with ~90px between
  // them — it read as a broken chart rather than a short list. Pad the grid so a
  // short ranking clusters at a sane row pitch and sits centred instead.
  if (labels.length <= 5) {
    const pad = Math.round((1 - labels.length / 6) * 50);
    o.grid.top = pad + "%";
    o.grid.bottom = pad + "%";
  }
  o.tooltip.trigger = "item";
  o.tooltip.formatter = (p) =>
    p.name + ": <b>" + fmtNum(p.value) + "</b>" + (d.unit ? " " + d.unit : "");
  o.xAxis = { type: "value", show: false, max: max * 1.04 };
  o.yAxis = {
    type: "category", data: labels,
    axisLine: { show: false }, axisTick: { show: false }, splitLine: { show: false },
    axisLabel: {
      color: T.ink, fontSize: T.fs.body, fontFamily: T.sans,
      // interval 0 = label EVERY row, never thin. ECharts drops alternate category
      // labels when it thinks the axis is crowded, which silently deleted the LIC and
      // UMIC rows from the income-group chart — four dots, two labels, and no way to
      // tell which was which. A ranking must name every row it draws.
      interval: 0,
      // One line, ellipsised. "break" wrapped long organisation names onto a second
      // line that overlapped the row below it — two labels on top of each other is
      // worse than one shortened label, and the full text is in the tooltip.
      width: NARROW ? 104 : 210, overflow: "truncate", ellipsis: "…", lineHeight: 15,
    },
  };
  o.series = [
    // The leader: a hairline from the axis to the dot.
    {
      type: "bar", data: values, barWidth: 1, silent: true,
      itemStyle: { color: alpha(color, 0.28) },
      z: 1,
    },
    // The dot, carrying the value. A folded "+N more" row is drawn in the neutral:
    // its value is a SUM, so it can sit further right than any real category and
    // would otherwise read as the largest one.
    {
      type: "scatter",
      data: values.map((v, i) => ({
        value: [v, i],
        itemStyle: /^\+\d+ more/.test(String(labels[i]))
          ? { color: T.faint, borderColor: T.surface, borderWidth: 1.5 }
          : undefined,
      })),
      symbolSize: 8, z: 2,
      itemStyle: { color: color, borderColor: T.surface, borderWidth: 1.5 },
      // The bare number only. Repeating a unit like "mean citations per article" on
      // every row is noise, and it clipped on the widest value; the unit belongs in
      // the caption and the tooltip.
      label: valueLabel("right", (p) => fmtNum(p.value[0])),
      emphasis: { scale: 1.4 },
    },
  ];
  return o;
}

/* An ordered lollipop (income bands, tenure bands): the dot takes its step from the
   sequential ramp, so the reader sees the order in the colour as well as the
   position. One hue, light to dark — that is what a ramp is for. */
function optOrdinalLollipop(d) {
  const o = optLollipop(d);
  const n = d.labels.length;
  // Re-colour the dots along the sequential ramp, keeping whatever shape optLollipop
  // produced. It emits `{value: [v, i], itemStyle}` objects (so a folded "+N more" row
  // can be greyed), and this used to wrap that object in ANOTHER `{value: …}`, giving
  // ECharts `{value: {value: [...]}}` — a nested shape it cannot read.
  // Reversed, because optLollipop reverses to draw top-down.
  o.series[1].data = o.series[1].data.map((point, i) => {
    const pair = point && point.value !== undefined ? point.value : point;
    return {
      value: pair,
      itemStyle: {
        color: seqAt(n > 1 ? (n - 1 - i) / (n - 1) : 0),
        borderColor: T.surface, borderWidth: 1.5,
      },
    };
  });
  return o;
}

/* More rows than the card can give them turns a ranking into overlapping text. Keep
   the top N and summarise the tail, so a lollipop is legible whatever height it
   lands in. */
function capRows(d, max) {
  const labels = d.labels || [];
  if (labels.length <= max) return d;
  const values = d.values || [];
  const kept = max - 1;
  const rest = values.slice(kept).reduce((a, b) => a + Number(b), 0);
  return {
    labels: labels.slice(0, kept).concat(["+" + (labels.length - kept) + " more"]),
    values: values.slice(0, kept).concat([rest]),
    unit: d.unit,
  };
}

/* Treemap tiles, capped. Returns `[{name, value}]` with the tail folded into one
   "Other" tile, sorted largest first so the palette runs in size order. Unlike
   capRows this names the remainder "Other" rather than "+N more": in a treemap the
   tile IS the category, and "+3 more" reads as a chart artefact where "Other" reads
   as a category — which is what it is. */
function capTiles(d, max) {
  const pairs = (d.labels || [])
    .map((label, i) => ({ name: label, value: Number((d.values || [])[i]) || 0 }))
    .sort((a, b) => b.value - a.value);
  if (pairs.length <= max) return pairs;
  const kept = pairs.slice(0, max);
  const rest = pairs.slice(max).reduce((sum, p) => sum + p.value, 0);
  // Flagged, not just named. "Other" is a remainder rather than a category with an
  // identity, so it must not take a palette slot — as the 6th tile it was landing on
  // crimson, which made the leftovers look like a warning.
  if (rest > 0) kept.push({ name: "Other", value: rest, residual: true });
  return kept;
}

/* A long tail of identical values is noise: seven countries each with one event
   is seven identical rows. Fold them into a single summary row. */
function collapseTies(d, minTies) {
  const floor = minTies || 4;
  const labels = d.labels || [];
  const values = (d.values || []).map(Number);
  if (labels.length < floor + 2) return { labels: labels, values: values };
  const last = values[values.length - 1];
  let ties = 0;
  for (let i = values.length - 1; i >= 0 && values[i] === last; i--) ties++;
  if (ties < floor) return { labels: labels, values: values };
  const keep = values.length - ties;
  return {
    labels: labels.slice(0, keep).concat(["+" + ties + " more at " + fmtNum(last)]),
    values: values.slice(0, keep).concat([last]),
  };
}

/* ------------------------------------------------------- bars and columns */
/* Kept for genuine time series, where a column reads as "an amount per period".
   Not used for rankings any more — that is what the lollipop is for. */
function optColumn(d) {
  const o = base();
  o.grid.top = 22;
  o.tooltip.trigger = "axis";
  o.tooltip.axisPointer = { type: "shadow", shadowStyle: { color: alpha(accent(), 0.06) } };
  o.tooltip.valueFormatter = fmtNum;
  o.xAxis = catAxis(d.labels);
  o.yAxis = valAxis({ show: false });
  o.series = [{
    type: "bar", data: d.values, barMaxWidth: 26,
    itemStyle: { color: accent(), borderRadius: [3, 3, 0, 0] },
    // Every column labelled: with the axis hidden, the label IS the value.
    label: valueLabel("top", (p) => fmtCompact(p.value)),
  }];
  return o;
}

function optMultiBar(d, stacked) {
  const o = base();
  o.grid.top = 28;
  o.tooltip.trigger = "axis";
  o.tooltip.axisPointer = { type: "shadow", shadowStyle: { color: alpha(accent(), 0.06) } };
  o.tooltip.valueFormatter = fmtNum;
  o.legend = legend(d.series.map((s) => s.name));
  o.xAxis = catAxis(d.labels);
  o.yAxis = valAxis();
  const colors = seriesColors(d, d.series.length);
  const kinds = d.kinds || [];
  o.series = d.series.map((s, i) => {
    if (kinds[i] === "line") {
      return {
        type: "line", name: s.name, data: s.values, smooth: 0.2,
        symbol: "circle", symbolSize: 7, z: 3,
        lineStyle: { color: colors[i], width: 2 },
        itemStyle: { color: colors[i], borderColor: T.surface, borderWidth: 1.5 },
      };
    }
    return {
      type: "bar", name: s.name, data: s.values, stack: stacked ? "s" : undefined,
      barMaxWidth: 26, barGap: "16%",
      itemStyle: {
        color: colors[i],
        // A 2px surface gap between fills rather than an outline on each.
        borderColor: T.surface, borderWidth: stacked ? 1.5 : 0,
        borderRadius: stacked ? 0 : [3, 3, 0, 0],
      },
    };
  });
  return o;
}

/* --------------------------------------------------------- lines and areas */
function optArea(d) {
  const o = base();
  // Room for the end label, or the number clips to its first digit.
  o.grid.right = 44;
  o.tooltip.trigger = "axis";
  o.tooltip.axisPointer = { type: "line", lineStyle: { color: T.border, width: 1 } };
  o.tooltip.valueFormatter = fmtNum;
  o.xAxis = catAxis(d.labels, { boundaryGap: false });
  o.yAxis = valAxis();
  const color = accent();
  o.series = [{
    type: "line", data: d.values, smooth: 0.24, showSymbol: false, symbolSize: 8,
    lineStyle: { color: color, width: 2 },
    itemStyle: { color: color, borderColor: T.surface, borderWidth: 2 },
    areaStyle: {
      color: {
        type: "linear", x: 0, y: 0, x2: 0, y2: 1,
        colorStops: [{ offset: 0, color: alpha(color, 0.2) }, { offset: 1, color: alpha(color, 0.01) }],
      },
    },
    // A cumulative curve is about where it ends, so only the endpoint is labelled.
    endLabel: {
      show: true, color: T.muted, fontSize: T.fs.meta, fontFamily: T.mono,
      formatter: (p) => fmtNum(p.value),
    },
  }];
  return o;
}

/* Several measures of very different magnitude on ONE axis, indexed to a common
   base (share of today's total). The sanctioned alternative to a dual axis. */
function optIndexedGrowth(d) {
  const o = base();
  o.grid.top = 26;
  o.grid.right = 20;
  o.tooltip.trigger = "axis";
  o.tooltip.axisPointer = { type: "line", lineStyle: { color: T.border, width: 1 } };
  o.tooltip.valueFormatter = (v) => (v == null ? "—" : Number(v).toFixed(0) + "% of today");
  o.legend = legend(d.series.map((s) => s.name));
  o.xAxis = catAxis(d.labels, { boundaryGap: false });
  o.yAxis = valAxis({
    max: 100,
    axisLabel: { color: T.muted, fontSize: T.fs.meta, fontFamily: T.mono, formatter: "{value}%" },
  });
  o.series = d.series.map((s, i) => ({
    type: "line", name: s.name, data: s.values, smooth: 0.24,
    showSymbol: false, symbolSize: 8,
    lineStyle: { color: catColor(i), width: 2 },
    itemStyle: { color: catColor(i), borderColor: T.surface, borderWidth: 1.5 },
  }));
  return o;
}

/* Two measures whose scales do not compare: stacked facets sharing one x axis,
   each with its own y. No scale alignment is invented. */
function optFacets(d) {
  const o = base();
  const names = d.series.map((s) => s.name);
  o.tooltip.trigger = "axis";
  o.tooltip.axisPointer = { type: "line", lineStyle: { color: T.border, width: 1 } };
  o.axisPointer = { link: [{ xAxisIndex: "all" }] };
  o.tooltip.valueFormatter = fmtNum;
  const nameStyle = { color: T.muted, fontSize: T.fs.meta, align: "left" };
  o.grid = [
    { left: 2, right: 14, top: 20, height: "34%", containLabel: true },
    { left: 2, right: 14, top: "58%", height: "32%", containLabel: true },
  ];
  o.xAxis = [
    catAxis(d.labels, { gridIndex: 0, axisLabel: { show: false } }),
    catAxis(d.labels, { gridIndex: 1 }),
  ];
  o.yAxis = [
    valAxis({ gridIndex: 0, name: names[0], nameLocation: "end", nameGap: 7, nameTextStyle: nameStyle }),
    valAxis({ gridIndex: 1, name: names[1], nameLocation: "end", nameGap: 7, nameTextStyle: nameStyle }),
  ];
  const color = accent();
  o.series = [
    {
      type: "bar", name: names[0], data: d.series[0].values,
      xAxisIndex: 0, yAxisIndex: 0, barMaxWidth: 22,
      itemStyle: { color: color, borderRadius: [3, 3, 0, 0] },
    },
    {
      type: "line", name: names[1], data: d.series[1].values,
      xAxisIndex: 1, yAxisIndex: 1, smooth: 0.24, showSymbol: false,
      lineStyle: { color: color, width: 2 },
      itemStyle: { color: color },
      areaStyle: {
        color: {
          type: "linear", x: 0, y: 0, x2: 0, y2: 1,
          colorStops: [{ offset: 0, color: alpha(color, 0.18) }, { offset: 1, color: alpha(color, 0.01) }],
        },
      },
    },
  ];
  return o;
}

/* ------------------------------------------------------------ composition */
/* Part-to-whole at a glance, <= 6 segments, labels on the ring rather than in a
   legend box (which cost a third of the card and repeated the same words). */
function optDonut(d) {
  const o = base();
  o.tooltip.trigger = "item";
  const total = d.values.reduce((a, b) => a + Number(b), 0);
  const withPct = showsPercentages(d.n == null ? total : d.n);
  o.tooltip.formatter = (p) =>
    p.name + "<br/><b>" + fmtNum(p.value) + "</b>" + (withPct ? " · " + fmtPct(p.value, total) : "");

  const bySemantics = d.semantics && !Array.isArray(d.semantics);
  // A dominant slice crowds every small one into the same corner. Label only the
  // slices with room for a label; the rest are in the tooltip and the table.
  const minShare = 0.045;
  o.series = [{
    type: "pie", radius: ["60%", "80%"], center: ["50%", "52%"], avoidLabelOverlap: true,
    // 2px surface gap between segments instead of an outline.
    itemStyle: { borderColor: T.surface, borderWidth: 2 },
    label: {
      show: true, position: "outer", alignTo: "edge", edgeDistance: 2,
      color: T.muted, fontSize: T.fs.meta, fontFamily: T.sans,
      // alignTo:edge pins labels to the card's inner edge and wraps them, instead
      // of letting them run past it and clip to "In progr…".
      width: 78, overflow: "break", lineHeight: 12,
      formatter: (p) => (p.value / total >= minShare ? p.name + "  " + fmtNum(p.value) : ""),
    },
    labelLine: {
      length: 5, length2: 7, lineStyle: { color: T.border },
      // Suppress the leader for an unlabelled slice, or the chart sprouts stubs.
      show: true,
    },
    data: d.labels.map((label, i) => ({
      name: label,
      value: d.values[i],
      // No leader line where there is no label to lead to.
      labelLine: { show: d.values[i] / total >= minShare },
      itemStyle: {
        // Semantics win; otherwise shade the section hue so a composition reads
        // as one family rather than six unrelated accents.
        // Semantics win; otherwise the categorical palette, so a composition is
        // legible as a set of distinct categories rather than shades of one hue.
        color: bySemantics ? semanticColor(d.semantics[label], i) : catColor(i),
      },
    })),
  }];
  // The total in the hole: the ring shows proportion, the centre shows scale.
  o.graphic = [{
    type: "text", left: "center", top: "middle", silent: true,
    style: {
      text: fmtNum(total), fill: T.ink, fontFamily: T.mono, fontSize: T.fs.view,
      textAlign: "center", textVerticalAlign: "middle",
    },
  }];
  return o;
}

function optTreemap(d) {
  const o = base();
  o.tooltip.trigger = "item";
  o.tooltip.formatter = (p) => p.name + ": <b>" + fmtNum(p.value) + "</b>";
  const color = accent();
  o.series = [{
    type: "treemap", roam: false, nodeClick: false, breadcrumb: { show: false },
    width: "100%", height: "100%", top: 0, left: 0, right: 0, bottom: 0,
    itemStyle: { borderColor: T.surface, borderWidth: 2, gapWidth: 2 },
    label: {
      show: true, fontFamily: T.sans, fontSize: T.fs.body,
      formatter: (p) => p.name + "\n" + fmtNum(p.value),
      overflow: "truncate", lineHeight: 13,
    },
    // Capped at 5 named tiles plus "Other". The palette stops at slot 6 (a 7th
    // category rendered T.faint grey), and beyond five tiles the small ones are
    // narrower than their own labels — "Networking" came out as "Ne…". Folding the
    // tail into one honest tile beats five illegible ones.
    data: capTiles(d, 5).map((tile, i) => ({
      name: tile.name, value: tile.value,
      itemStyle: { color: tile.residual ? T.faint : catColor(i) },
      label: { color: "#fff" },
    })),
  }];
  return o;
}

/* A two-level hierarchy as a nested treemap.

   This was a sunburst. A sunburst has to draw its outer labels along a curve, and
   with subtask names like "Property calculation or prediction" they came out
   rotated, overlapping and clipped — unreadable. Rectangles hold horizontal text,
   so the same hierarchy is legible in the same space. Parents take tints of the
   section hue and children a lighter tint of their parent, so the grouping is what
   the colour encodes. */
function optTreeMap(d) {
  const o = base();
  o.tooltip.trigger = "item";
  o.tooltip.formatter = (p) =>
    (p.treePathInfo && p.treePathInfo.length > 2
      ? p.treePathInfo[1].name + " · " + p.name
      : p.name) + ": <b>" + fmtNum(p.value) + "</b>";
  const tree = d.tree || [];
  o.series = [{
    type: "treemap", roam: false, nodeClick: false, breadcrumb: { show: false },
    width: "100%", height: "100%", top: 0, left: 0, right: 0, bottom: 0,
    visibleMin: 1, childrenVisibleMin: 0,
    levels: [
      { itemStyle: { borderColor: T.surface, borderWidth: 3, gapWidth: 3 } },
      {
        itemStyle: { borderColor: T.surface, borderWidth: 1.5, gapWidth: 1.5 },
        upperLabel: {
          show: true, height: 17, color: T.ink, fontFamily: T.sans, fontSize: T.fs.meta,
          overflow: "truncate",
        },
      },
    ],
    label: {
      show: true, fontFamily: T.sans, fontSize: T.fs.meta,
      formatter: (p) => p.name + "\n" + fmtNum(p.value),
      overflow: "truncate", lineHeight: 13,
    },
    data: tree.map((parent, i) => {
      // One palette slot per parent, then lighter tints for its children: the colour
      // encodes which family a block belongs to, the tint distinguishes within it.
      const parentColor = catColor(i);
      const children = parent.children || [];
      return {
        name: parent.name,
        itemStyle: { color: parentColor },
        children: children.map((child, j) => {
          const tint = 0.10 + 0.30 * (j / Math.max(children.length - 1, 1));
          return {
            name: child.name,
            value: child.value,
            itemStyle: { color: mixWithWhite(parentColor, tint) },
            // The tint decides whether ink or white stays readable on the tile. This
            // used to be compared against a `parentTint` constant of 0, which made
            // the test `tint > 0.40` on a range that stops AT 0.40 — never true, so
            // every child label was white, including on the palest tiles where it
            // vanished into the fill.
            label: { color: tint > 0.26 ? T.ink : "#fff" },
          };
        }),
      };
    }),
  }];
  return o;
}

/* --------------------------------------------------------------- scatter */
/* Log-log, for a distribution with a long tail. 140 repositories at ~100:1 skew
   collapse into one corner on linear axes — the previous version of this chart
   was unreadable for exactly that reason. Quadrant guides sit at the medians, so
   "popular but inactive" and "active but unknown" become visible regions. */
function optLogScatter(d, conf) {
  const c = conf || {};
  const rows = (d.points || [])
    .map((p) => (Array.isArray(p)
      ? { x: p[0], y: p[1], name: p[3] }
      : { x: Number(p[c.x]), y: Number(p[c.y]), name: p.name }))
    // A log axis cannot show zero; shift by one so "0 stars" stays on the chart
    // rather than being silently dropped. Stated in the axis label.
    .map((r) => ({ x: (r.x || 0) + 1, y: (r.y || 0) + 1, name: r.name, rawX: r.x || 0, rawY: r.y || 0 }));
  if (!rows.length) return base();

  const median = (arr) => {
    const s = arr.slice().sort((a, b) => a - b);
    return s[Math.floor(s.length / 2)] || 1;
  };
  const mx = median(rows.map((r) => r.x));
  const my = median(rows.map((r) => r.y));
  // The six repositories furthest out on both measures at once. Fixed count, so
  // the chart stays legible whatever the distribution does.
  const named = new Set(
    rows.slice()
      .sort((a, b) => (b.rawX + 1) * (b.rawY + 1) - (a.rawX + 1) * (a.rawY + 1))
      .slice(0, 6)
      .map((r) => r.name)
  );
  const color = accent();
  const nameStyle = { color: T.muted, fontFamily: T.sans, fontSize: T.fs.meta };

  const o = base();
  // top: the outermost point carries a label ABOVE its mark, and at 14 the highest
  // one ("eos") was clipped off the plot area entirely.
  o.grid = { left: 6, right: 18, top: 24, bottom: 4, containLabel: true };
  o.tooltip.trigger = "item";
  o.tooltip.formatter = (p) =>
    "<b>" + p.data[2] + "</b><br/>" + c.xLabel + " " + fmtNum(p.data[3]) +
    " · " + c.yLabel + " " + fmtNum(p.data[4]);
  const logAxis = (name, gap) => ({
    type: "log", logBase: 10, min: 1,
    name: name, nameLocation: "middle", nameGap: gap, nameTextStyle: nameStyle,
    axisLine: { show: false }, axisTick: { show: false },
    splitLine: { lineStyle: { color: T.axis, type: "solid" } },
    axisLabel: {
      color: T.muted, fontSize: T.fs.meta, fontFamily: T.mono,
      // Undo the +1 shift in the tick labels so the axis tells the truth.
      formatter: (v) => fmtCompact(v - 1),
    },
  });
  o.xAxis = logAxis(c.xLabel + " (log)", 26);
  o.yAxis = logAxis(c.yLabel + " (log)", 34);
  o.series = [{
    type: "scatter",
    data: rows.map((r) => [r.x, r.y, r.name, r.rawX, r.rawY]),
    symbolSize: 8,
    itemStyle: { color: alpha(color, 0.6), borderColor: T.surface, borderWidth: 1 },
    emphasis: { itemStyle: { color: color }, scale: 1.5 },
    // Label only a handful of genuine outliers. A threshold relative to the median
    // labelled dozens of points and turned the chart into a pile of overlapping
    // text, so this takes a fixed top-N by the product of both measures instead.
    label: {
      show: true, position: "top", color: T.muted, fontSize: T.fs.meta, fontFamily: T.sans,
      formatter: (p) => (named.has(p.data[2]) ? p.data[2] : ""),
    },
    // Quadrant guides, unlabelled. A rotated "median" caption on a vertical rule
    // reads as debris; the tooltip and the methodology note carry the meaning.
    markLine: {
      symbol: ["none", "none"], symbolSize: 0, silent: true,
      label: { show: false },
      lineStyle: { color: T.border, width: 1, type: "dashed" },
      data: [{ xAxis: mx }, { yAxis: my }],
    },
  }];
  return o;
}

/* ------------------------------------------------------- distribution */
function optHistogram(d) {
  const o = base();
  o.grid.top = 24;
  o.tooltip.trigger = "axis";
  o.tooltip.axisPointer = { type: "shadow", shadowStyle: { color: alpha(accent(), 0.06) } };
  // The counted thing is not always people — these bins now hold models by wrap lag
  // and by image size too, where "3 people" was simply wrong. `countNoun` names the
  // rows; `unit` describes the x axis and belongs in the caption, not here.
  const noun = d.countNoun || "";
  o.tooltip.valueFormatter = (v) => fmtNum(v) + (noun ? " " + noun : "");
  o.xAxis = catAxis(d.labels, { axisLabel: { color: T.muted, fontSize: T.fs.meta, fontFamily: T.mono, interval: 0, rotate: 0 } });
  o.yAxis = valAxis({ show: false });
  o.series = [{
    type: "bar", data: d.values, barCategoryGap: "18%",
    itemStyle: { color: accent(), borderRadius: [3, 3, 0, 0], borderColor: T.surface, borderWidth: 1 },
    label: valueLabel("top", (p) => (p.value ? fmtNum(p.value) : "")),
  }];
  if (d.mean != null) {
    const index = d.labels.findIndex((label) => {
      const parts = String(label).split(/[–+]/);
      const low = parseFloat(parts[0]);
      const high = parts[1] === "" || parts[1] == null ? Infinity : parseFloat(parts[1]);
      return d.mean >= low && d.mean < high;
    });
    if (index >= 0) {
      o.series[0].markLine = {
        symbol: ["none", "none"], symbolSize: 0, silent: true,
        lineStyle: { color: T.ink, width: 1, type: "dashed" },
        label: { show: false },
        data: [{ xAxis: index }],
      };
    }
  }
  return o;
}

/* How unevenly a total is spread. The diagonal is perfect evenness. */
function optLorenz(d) {
  const o = base();
  o.grid = { left: 4, right: 12, top: 10, bottom: 4, containLabel: true };
  o.tooltip.trigger = "axis";
  o.tooltip.axisPointer = { type: "line", lineStyle: { color: T.border, width: 1 } };
  const nameStyle = { color: T.muted, fontFamily: T.sans, fontSize: T.fs.meta };
  o.tooltip.formatter = (params) => {
    const p = params[params.length - 1];
    return "Least active " + Number(p.axisValue).toFixed(0) + "%<br/>hold <b>" +
      Number(p.data[1] != null ? p.data[1] : p.data).toFixed(0) + "%</b> of commits";
  };
  const pctAxis = (name, gap) => ({
    type: "value", max: 100, name: name, nameLocation: "middle", nameGap: gap,
    nameTextStyle: nameStyle,
    axisLine: { show: false }, axisTick: { show: false },
    splitLine: { lineStyle: { color: T.axis, type: "solid" } },
    axisLabel: { color: T.muted, fontSize: T.fs.meta, fontFamily: T.mono, formatter: "{value}%" },
  });
  o.xAxis = pctAxis("% of repositories", 25);
  o.yAxis = pctAxis("% of commits", 34);
  const color = accent();
  o.series = [
    {
      type: "line", name: "Even", data: [[0, 0], [100, 100]],
      showSymbol: false, silent: true,
      lineStyle: { color: T.border, width: 1, type: "dashed" },
    },
    {
      type: "line", name: "Commits", showSymbol: false, smooth: 0,
      data: d.labels.map((label, i) => [Number(label), d.values[i]]),
      lineStyle: { color: color, width: 2 },
      areaStyle: { color: alpha(color, 0.12) },
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
  const percent = isPercentUnit(d);

  const o = base();
  o.grid = { left: 2, right: 6, top: 8, bottom: 2, containLabel: true };
  o.tooltip.trigger = "item";
  o.tooltip.formatter = (p) => {
    const detail = counts[p.value[0] + ":" + p.value[1]];
    const head = d.y[p.value[1]] + " · " + d.x[p.value[0]];
    const value = percent ? p.value[2] + "%" : fmtNum(p.value[2]);
    return head + "<br/><b>" + value + "</b>" +
      (detail ? " (" + fmtNum(detail[2]) + " of " + fmtNum(detail[3]) + ")" : "");
  };
  const catStyle = {
    axisLine: { show: false }, axisTick: { show: false }, splitLine: { show: false },
    axisLabel: { color: T.muted, fontSize: T.fs.meta, fontFamily: T.sans },
  };
  o.xAxis = Object.assign({ type: "category", data: d.x }, catStyle, {
    axisLabel: Object.assign({}, catStyle.axisLabel, { rotate: d.x.length > 5 ? 26 : 0 }),
  });
  o.yAxis = Object.assign({ type: "category", data: d.y }, catStyle);
  o.visualMap = {
    min: 0, max: max,
    // Hidden on purpose. Every cell carries its own value as a label, so a colour
    // legend is redundant ink — and at a narrow card width it collided with the
    // cells it was meant to explain. The mapping still applies; only the key goes.
    show: false,
    inRange: { color: T.seq },
  };
  o.series = [{
    type: "heatmap",
    // A cell with no judgeable data has no mark at all, which is why every
    // present cell is labelled: otherwise a genuine 0 (the palest step) is
    // indistinguishable from an absent cell.
    data: cells.map((c) => ({
      value: c,
      label: { color: c[2] >= max * 0.6 ? "#fff" : T.ink },
    })),
    itemStyle: { borderColor: T.surface, borderWidth: 2, borderRadius: 3 },
    label: {
      show: true, fontSize: T.fs.meta, fontFamily: T.mono,
      formatter: (p) => (percent ? p.value[2] + "%" : fmtNum(p.value[2])),
    },
    emphasis: { itemStyle: { borderColor: T.ink, borderWidth: 2 } },
  }];
  return o;
}

/* ------------------------------------------------------------- timeline */
/* One bar per project between start and end, plus a "today" rule. Shows
   concurrency and overrun, which a per-quarter count cannot. */
function optGantt(d) {
  const rows = (d.rows || []).slice();
  const names = rows.map((r) => r.name);
  const toDay = (iso) => new Date(iso + "T00:00:00Z").getTime();
  const semantics = d.semantics || {};

  const o = base();
  // Top padding clears the "today" label, which sits above the plot area.
  o.grid = { left: 2, right: 16, top: 20, bottom: 2, containLabel: true };
  o.tooltip.trigger = "item";
  o.tooltip.formatter = (p) => {
    const r = rows[p.dataIndex];
    return "<b>" + r.name + "</b><br/>" + r.status + " · " + r.months + " months<br/>" +
      r.start + " → " + (r.open ? "open" : r.end);
  };
  o.xAxis = {
    type: "time",
    axisLine: { show: false }, axisTick: { show: false },
    splitLine: { lineStyle: { color: T.axis, type: "solid" } },
    axisLabel: { color: T.muted, fontSize: T.fs.meta, fontFamily: T.mono },
  };
  o.yAxis = {
    type: "category", data: names, inverse: true,
    axisLine: { show: false }, axisTick: { show: false }, splitLine: { show: false },
    axisLabel: {
      // interval 0 forces a label on every row; without it ECharts thins them and
      // half the projects become unlabelled bars.
      interval: 0,
      color: T.ink, fontSize: names.length > 28 ? 9.5 : 10.5, fontFamily: T.sans,
      width: NARROW ? 116 : 224, overflow: "truncate",
    },
  };
  o.series = [{
    type: "custom",
    renderItem: (params, api) => {
      const index = api.value(3);
      const start = api.coord([api.value(0), index]);
      const end = api.coord([api.value(1), index]);
      const height = Math.max(6, api.size([0, 1])[1] * 0.5);
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
      symbol: ["none", "none"], symbolSize: 0, silent: true,
      lineStyle: { color: T.ink, width: 1, type: "dashed" },
      label: {
        show: true, position: "start", color: T.ink, fontSize: T.fs.meta,
        fontFamily: T.sans, formatter: "today",
      },
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
  "viet nam": "Vietnam", "syrian arab republic": "Syria",
  "lao people's democratic republic": "Laos", "iran, islamic republic of": "Iran",
  "moldova, republic of": "Moldova", "north macedonia": "Macedonia",
  "eswatini": "Swaziland", "cabo verde": "Cape Verde",
};
function mapName(name) {
  const key = String(name).trim().toLowerCase();
  return MAP_ALIAS[key] || String(name).trim();
}

function optMap(d, label) {
  const max = Math.max(1, ...d.values.map(Number));
  // Magnitude is a single-hue ramp, light to dark — the documented sequential steps.
  const color = accent();
  const ramp = T.seq;

  /* Piecewise buckets rather than a continuous scale. One country with 208 records
     against a median of 2 flattens a linear ramp: everything except the outlier
     renders the same pale tint. Roughly geometric breaks, clipped to the data, keep
     the small counts distinguishable — and a bucketed legend states the ranges
     instead of asking the reader to interpolate a gradient. */
  const breaks = [1, 2, 5, 20, 50].filter((b) => b < max);
  const pieces = breaks.map((low, i) => {
    const next = breaks[i + 1];
    return next
      ? { gte: low, lt: next, label: low + "–" + (next - 1), color: ramp[Math.min(i, ramp.length - 1)] }
      : { gte: low, label: low + "+", color: ramp[Math.min(i, ramp.length - 1)] };
  });
  return {
    textStyle: { fontFamily: T.sans, color: T.ink },
    animationDuration: T.calm ? 0 : 240,
    tooltip: {
      trigger: "item", backgroundColor: T.ink, borderWidth: 0, padding: [7, 10],
      textStyle: { color: "#fff", fontSize: T.fs.body, fontFamily: T.sans },
      extraCssText: "box-shadow:0 6px 20px rgba(44,62,80,.16);border-radius:8px;",
      formatter: (p) => p.name + "<br/><b>" +
        (p.value == null || Number.isNaN(p.value)
          ? "none recorded"
          : fmtNum(p.value) + " " + (label || "")) + "</b>",
    },
    visualMap: {
      type: "piecewise", left: 4, bottom: 4, orient: "horizontal",
      pieces: pieces,
      itemWidth: 13, itemHeight: 9, itemGap: 7,
      // No `text`: with pieces, a text array duplicates the endpoint labels and the
      // two sets overlap.
      textStyle: { color: T.muted, fontSize: T.fs.meta, fontFamily: T.mono },
    },
    series: [{
      type: "map", map: "world", roam: false,
      data: d.labels.map((l, i) => ({ name: mapName(l), value: d.values[i] })),
      // Countries with no record keep the neutral fill rather than being shaded
      // as though they were a zero.
      itemStyle: { areaColor: T.nullFill, borderColor: T.surface, borderWidth: 0.6 },
      emphasis: { label: { show: false }, itemStyle: { areaColor: color } },
      select: { disabled: true },
    }],
  };
}

/* ------------------------------------------------------------ dispatch */
const BUILDERS = {
  lollipop: optLollipop,
  ordinallollipop: optOrdinalLollipop,
  column: optColumn,
  area: optArea,
  line: optArea,
  growth: optIndexedGrowth,
  donut: optDonut,
  treemap: optTreemap,
  treehierarchy: optTreeMap,
  stackbar: (d) => optMultiBar(d, true),
  groupbar: (d) => optMultiBar(d, false),
  facets: optFacets,
  histogram: optHistogram,
  lorenz: optLorenz,
  heatmap: optHeatmap,
  gantt: optGantt,
};

function buildOption(chart, d) {
  if (chart.type === "logscatter") return optLogScatter(d, chart.scatter || {});
  if (chart.type === "map") return optMap(d, chart.mapLabel);
  const builder = BUILDERS[chart.type] || optLollipop;
  return builder(d);
}

/* Chart types that are rendered as HTML rather than a canvas (see cards.js). */
const HTML_TYPES = { meters: 1, ranked: 1, shares: 1 };

/* Does this metric have anything to draw? */
function hasData(chart, d) {
  if (!d) return false;
  if (chart.type === "logscatter") return Array.isArray(d.points) && d.points.length > 0;
  // A ranked table is row-shaped, not label/value-shaped — checking labels here is
  // what left "Most starred public repositories" showing an empty state.
  if (chart.type === "ranked") {
    return (Array.isArray(d.rows) && d.rows.length > 0) ||
           (Array.isArray(d.labels) && d.labels.length > 0);
  }
  if (chart.type === "gantt") return Array.isArray(d.rows) && d.rows.length > 0;
  if (chart.type === "heatmap") return Array.isArray(d.cells) && d.cells.length > 0;
  if (chart.type === "treehierarchy") return Array.isArray(d.tree) && d.tree.length > 0;
  if (d.series) return Array.isArray(d.labels) && d.labels.length > 0 && d.series.length > 0;
  return Array.isArray(d.labels) && d.labels.length > 0;
}
