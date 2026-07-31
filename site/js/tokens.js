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

    /* Categorical identity, for charts that carry several series at once. FIXED
       ORDER — the ordering is what makes the palette colour-vision safe (adjacent
       ΔE 15.8). Never reorder it, and never cycle past the end: a 7th series
       folds into "Other" or the chart gets faceted. A one-series chart takes
       slot 1 via accent(). */
    cat: [1, 2, 3, 4, 5, 6].map((i) => v("--chart-" + i)),

    /* Sequential, light -> dark. Magnitude only. */
    seq: [1, 2, 3, 4, 5].map((i) => v("--seq-" + i)),

    /* The type scale, read from CSS so the stylesheet stays the single source of
       truth. Two levels for chart text and nothing else: `meta` for axis and value
       labels, `body` for anything that must be read first. Charts previously set
       9.5/10/10.5/11/11.5px inline — five sizes, all below the 12px floor every
       mainstream design system uses for body text. */
    fs: {
      meta: parseFloat(v("--fs-meta", "12px")),
      body: parseFloat(v("--fs-body", "13px")),
      title: parseFloat(v("--fs-title", "15px")),
      view: parseFloat(v("--fs-view", "20px")),
    },

    /* True for a visitor who has asked for less motion. Read once at load: ECharts
       takes a duration at option-build time, so there is nothing to react to later. */
    calm: typeof matchMedia === "function" &&
          matchMedia("(prefers-reduced-motion: reduce)").matches,

  };
})();

/* The chrome is NEUTRAL and colour lives in the data.

   An earlier version gave each section its own hue and painted that section's charts
   with it. It made every page monochrome, which is the opposite of using a palette:
   one colour per page reads as a restriction, not as a system. So the palette is now
   global — any chart may draw on the full categorical set — and the navigation,
   headers and cards stay grey. That is the convention good dashboards follow, and it
   keeps colour meaning "this is a category" rather than "this is page four". */

/* The single accent for a one-series chart. Consistent everywhere, so a bar chart
   never changes colour just because it moved page. */
function accent() {
  return catColor(0);
}

/* Distinct palette slots for a set of sibling items (hero tiles, section cards).
   Uses the categorical order rather than one hue — but STOPS BEFORE THE LAST SLOT.

   Slot 6 is crimson, reserved so that only a genuine sixth data category reaches it.
   Chrome is never a data category, so it must never reach it either: with the full
   length here, the "Repositories" hero sparkline and the "Countries & partners" card
   came out red, which is precisely the false alarm the palette order exists to
   prevent. Five hues are plenty for eight tiles. */
const CHROME_SLOTS = 5;

function slotColor(index) {
  return catColor(index % Math.min(CHROME_SLOTS, T.cat.length));
}

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

/* Mix a colour towards white. `amount` is how much WHITE to add, so 0 returns the
   colour untouched and 1 returns white. Used to build tints of a section hue for
   compositions (donut segments, treemap tiles, choropleth ramps) — a composition
   should read as one family rather than as several unrelated accents.

   Opaque tints rather than alpha, so marks stay solid over gridlines. */
function mixWithWhite(color, amount) {
  const rgb = toRgb(color);
  if (!rgb) return color;
  const t = Math.max(0, Math.min(1, amount));
  const mixed = rgb.map((c) => Math.round(c + (255 - c) * t));
  return "#" + mixed.map((c) => c.toString(16).padStart(2, "0")).join("");
}

/* Accepts "#rgb", "#rrggbb" and the "rgb(r, g, b)" that getComputedStyle returns
   once a color-mix() token has been resolved. */
function toRgb(color) {
  const text = String(color).trim();
  const hex = /^#([0-9a-f]{3}|[0-9a-f]{6})$/i.exec(text);
  if (hex) {
    const h = hex[1].length === 3 ? hex[1].replace(/./g, (c) => c + c) : hex[1];
    const n = parseInt(h, 16);
    return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
  }
  const fn = /rgba?\(([^)]+)\)/i.exec(text);
  if (fn) {
    const parts = fn[1].split(/[,\s/]+/).filter(Boolean).slice(0, 3).map(Number);
    if (parts.length === 3 && parts.every((p) => !Number.isNaN(p))) return parts;
  }
  return null;
}
