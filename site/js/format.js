/* Number and label formatting.

   Every number on the site is mono + tabular-nums (house rule), so the job here
   is only to decide digits and units — never to style. */

const LOW_N = 10; // below this, percentages mislead; show counts only.

function fmtNum(value) {
  if (value == null || value === "" || Number.isNaN(Number(value))) return "—";
  const n = Number(value);
  if (!Number.isInteger(n)) return n.toLocaleString(undefined, { maximumFractionDigits: 1 });
  return n.toLocaleString();
}

/* Compact form for tight spots (axis labels, tile deltas). */
function fmtCompact(value) {
  const n = Number(value);
  if (Number.isNaN(n)) return "—";
  const abs = Math.abs(n);
  if (abs >= 1e6) return (n / 1e6).toFixed(abs >= 1e7 ? 0 : 1) + "M";
  if (abs >= 1e4) return Math.round(n / 1e3) + "k";
  if (abs >= 1e3) return (n / 1e3).toFixed(1) + "k";
  return String(n);
}

function fmtPct(part, whole, digits) {
  if (!whole) return "—";
  return (100 * part / whole).toFixed(digits == null ? 0 : digits) + "%";
}

/* A KPI's 12-month movement. Returns null when there is nothing to say. */
function fmtDelta(delta) {
  if (delta == null) return null;
  const n = Number(delta);
  if (!n) return { text: "no change in 12 months", cls: "flat" };
  const sign = n > 0 ? "+" : "−";
  return { text: sign + fmtNum(Math.abs(n)) + " in 12 months", cls: n > 0 ? "up" : "down" };
}

/* Percentages are only honest above a floor: with n = 7, "43%" invites a
   conclusion the sample cannot support. Charts below the floor show counts. */
function showsPercentages(n) {
  return Number(n || 0) >= LOW_N;
}

/* Quarter labels ("2026Q2") are long on a dense axis; drop the century. */
function shortQuarter(label) {
  const match = /^(\d{4})Q(\d)$/.exec(String(label));
  return match ? "'" + match[1].slice(2) + " Q" + match[2] : String(label);
}

function titleCase(text) {
  return String(text).replace(/_/g, " ").replace(/^\w/, (c) => c.toUpperCase());
}
