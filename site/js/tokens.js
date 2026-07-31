/* Design tokens, read from CSS at runtime.

   No colour is written twice. Everything comes from the custom properties in
   assets/ersilia.css (brand) and styles.css (validated chart steps), so the
   stylesheet is the single source of truth and the two cannot drift apart. */

const T = (() => {
  const css = getComputedStyle(document.documentElement);

  /* A custom property's value comes back as written, so a token defined with
     color-mix() would reach ECharts as the literal string "color-mix(…)" and fail
     to parse. Painting it onto a probe element makes the browser resolve it to
     rgb() first, which lets tokens be derived rather than hard-coded. */
  const probe = document.createElement("span");
  probe.style.display = "none";
  document.documentElement.appendChild(probe);
  const resolve = (value) => {
    if (!value || value.indexOf("(") === -1) return value;
    probe.style.color = "";
    probe.style.color = value;
    const resolved = getComputedStyle(probe).color;
    return resolved || value;
  };

  const v = (name, fallback) => resolve(css.getPropertyValue(name).trim()) || fallback;

  return {
    ink: v("--ink", "#2C3E50"),
    muted: v("--muted", "#6B6675"),
    faint: v("--faint", "#9A93A6"),
    border: v("--border", "#E6E6EE"),
    surface: v("--surface", "#FFFFFF"),
    surface2: v("--surface-2", "#F4F4F8"),
    brand: v("--brand", "#6C5CE7"),
    plum: v("--plum", "#50285A"),
    good: v("--good", "#3F9D6B"),
    warn: v("--warn", "#C98A1E"),
    bad: v("--bad", "#D9534F"),
    axis: v("--chart-axis", "#E9E9F1"),
    nullFill: v("--chart-null", "#EDEDF3"),
    sans: v("--sans", 'system-ui, sans-serif'),
    mono: v("--mono", "ui-monospace, Menlo, monospace"),

    /* Categorical identity. FIXED ORDER — this ordering is what makes the palette
       colour-vision safe (adjacent ΔE 15.8). Never reorder it, and never cycle
       past the end: a 7th series folds into "Other" or the chart gets faceted. */
    cat: [1, 2, 3, 4, 5, 6].map((i) => v("--chart-" + i)),

    /* Sequential, light -> dark. Magnitude only. */
    seq: [1, 2, 3, 4, 5].map((i) => v("--seq-" + i)),
  };
})();

/* Semantic names the exporter emits alongside status metrics, so "in progress"
   is the same colour in every chart on the site. */
const SEMANTIC = {
  good: T.good,
  bad: T.bad,
  warn: T.warn,
  brand: T.brand,
  neutral: T.faint,
};

/* Series colour by slot. Beyond slot 6 we deliberately return the neutral rather
   than inventing a hue — an over-long series list is a chart problem, not a
   palette problem. */
function catColor(index) {
  return index < T.cat.length ? T.cat[index] : T.faint;
}

function semanticColor(name, fallbackIndex) {
  return SEMANTIC[name] || catColor(fallbackIndex || 0);
}

/* Interpolate the sequential ramp at t in [0,1] — for choropleth/heatmap stops. */
function seqAt(t) {
  const steps = T.seq;
  const clamped = Math.max(0, Math.min(1, t));
  const pos = clamped * (steps.length - 1);
  return steps[Math.round(pos)];
}

/* Alpha-blended fill for area charts: hex + 2-digit alpha. */
function alpha(hex, a) {
  const value = Math.round(Math.max(0, Math.min(1, a)) * 255).toString(16).padStart(2, "0");
  return hex.length === 7 ? hex + value : hex;
}
