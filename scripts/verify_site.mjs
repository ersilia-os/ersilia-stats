#!/usr/bin/env node
/* Smoke-test the built site in a real browser, and fail the build if it is broken.
 *
 * WHY THIS EXISTS. The deploy pipeline validated the Python and the data and then
 * shipped the JavaScript unexamined. Nothing parsed it, nothing ran it. A single
 * stray character in config.js deploys a page that renders "Loading figures…"
 * forever, and the workflow reports success — which happened twice during
 * development, caught only because someone happened to look.
 *
 * WHAT IT CHECKS, per route:
 *   1. the view renders at least one card          (catches any JS that throws)
 *   2. no uncaught exception and no console error   (catches silent breakage)
 *   3. every chart row's spans sum to 12            (the config.js invariant)
 *   4. every card carries a caption that fits       (the layout contract)
 *   5. exactly one <h1>                             (document structure)
 *
 * DELIBERATELY SELF-CONTAINED: no npm install, no package.json, no Playwright. It
 * serves site/ itself, drives Chrome over the DevTools protocol using the WebSocket
 * built into Node 22+, and cleans both up. The only external requirement is a Chrome
 * or Chromium binary, which ubuntu-latest already has.
 *
 *   node scripts/verify_site.mjs [--site site] [--keep-open]
 */
import { createServer } from "node:http";
import { spawn } from "node:child_process";
import { readFile, mkdtemp, rm } from "node:fs/promises";
import { existsSync, readFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, extname, normalize } from "node:path";

const args = process.argv.slice(2);
const argOf = (flag, fallback) => {
  const i = args.indexOf(flag);
  return i >= 0 && args[i + 1] ? args[i + 1] : fallback;
};
const SITE = argOf("--site", "site");

// Every view in config.js, plus the two routes that are not views. Derived rather than
// listed, because a hand-maintained list silently skips whatever was just added — the
// `activity` view was written, deployed and never verified until this changed.
const EXTRA_ROUTES = ["/", "/downloads"];

function discoverRoutes(siteDir) {
  const source = readFileSync(join(siteDir, "config.js"), "utf8");
  const views = source.slice(source.indexOf("const VIEWS"));
  const ids = [...views.matchAll(/^\s+id:\s*"([a-z0-9-]+)"/gm)].map((m) => m[1]);
  if (!ids.length) throw new Error("no view ids found in config.js — the regex is stale");
  // Cross-check against a second marker that appears exactly once per view. Matching `id:`
  // alone is indentation-sensitive, so a reformat could find SOME views and silently leave
  // the rest untested — which is the failure this function exists to prevent, reappearing
  // in a subtler form. Disagreement means the parse is wrong, not that a view is missing.
  const headlines = (views.match(/^\s+headlineKpi:/gm) || []).length;
  if (headlines && headlines !== ids.length) {
    throw new Error(`config.js parse mismatch: ${ids.length} view id(s) but ${headlines} `
                    + `headlineKpi entries. Routes would be under-tested; fix the regex.`);
  }
  return [EXTRA_ROUTES[0], ...ids.map((id) => "/" + id), EXTRA_ROUTES[1]];
}

const ROUTES = discoverRoutes(SITE);

const MIME = {
  ".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8", ".json": "application/json; charset=utf-8",
  ".csv": "text/csv; charset=utf-8", ".png": "image/png", ".svg": "image/svg+xml",
};

/* ----------------------------------------------------------- static server */
function serve(root) {
  const server = createServer(async (req, res) => {
    // Strip the query and the hash; "?bust=" is how we defeat the HTTP cache.
    const path = decodeURIComponent(req.url.split("?")[0].split("#")[0]);
    const rel = normalize(path === "/" ? "/index.html" : path).replace(/^(\.\.[/\\])+/, "");
    const file = join(root, rel);
    try {
      const body = await readFile(file);
      res.writeHead(200, {
        "content-type": MIME[extname(file)] || "application/octet-stream",
        "cache-control": "no-store",
      });
      res.end(body);
    } catch {
      res.writeHead(404).end("not found");
    }
  });
  return new Promise((resolve) => {
    server.listen(0, "127.0.0.1", () => resolve({ server, port: server.address().port }));
  });
}

/* ------------------------------------------------------------------ chrome */
const CHROME_CANDIDATES = [
  process.env.CHROME_PATH,
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
  "google-chrome-stable", "google-chrome", "chromium-browser", "chromium",
].filter(Boolean);

function chromeBinary() {
  for (const c of CHROME_CANDIDATES) {
    if (c.includes("/") ? existsSync(c) : true) return c;
  }
  return "google-chrome";
}

async function launchChrome(port, profile) {
  const child = spawn(chromeBinary(), [
    "--headless=new", "--remote-debugging-port=" + port,
    "--user-data-dir=" + profile,
    "--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage",
    "--hide-scrollbars", "--window-size=1440,1200", "about:blank",
  ], { stdio: "ignore" });

  // Poll the DevTools endpoint rather than sleeping a fixed time.
  for (let i = 0; i < 100; i++) {
    try {
      const r = await fetch(`http://127.0.0.1:${port}/json/list`);
      const targets = await r.json();
      const page = targets.find((t) => t.type === "page");
      if (page) return { child, page };
    } catch { /* not up yet */ }
    await new Promise((r) => setTimeout(r, 150));
  }
  throw new Error("Chrome did not expose a DevTools page within 15s");
}

/* --------------------------------------------------------------------- cdp */
function connect(wsUrl) {
  // Node 22+ ships a global WebSocket, so this needs no dependency.
  if (typeof WebSocket !== "function") {
    throw new Error("Node 22+ required (needs the built-in WebSocket)");
  }
  const ws = new WebSocket(wsUrl);
  let id = 0;
  const pending = new Map();
  const problems = [];

  ws.addEventListener("message", (event) => {
    const msg = JSON.parse(event.data);
    if (msg.id && pending.has(msg.id)) {
      pending.get(msg.id)(msg);
      pending.delete(msg.id);
    }
    if (msg.method === "Runtime.exceptionThrown") {
      const d = msg.params.exceptionDetails;
      problems.push("exception: " + (d.exception?.description || d.text || "?").split("\n")[0]);
    }
    if (msg.method === "Runtime.consoleAPICalled" && msg.params.type === "error") {
      problems.push("console.error: " +
        msg.params.args.map((a) => a.value ?? a.description ?? "?").join(" "));
    }
  });

  const ready = new Promise((resolve, reject) => {
    ws.addEventListener("open", resolve);
    ws.addEventListener("error", () => reject(new Error("CDP socket failed")));
  });

  const send = (method, params = {}) => new Promise((resolve) => {
    const i = ++id;
    pending.set(i, resolve);
    ws.send(JSON.stringify({ id: i, method, params }));
  });

  const evaluate = async (expression) => {
    const r = await send("Runtime.evaluate", {
      expression: `JSON.stringify(${expression})`,
      returnByValue: true, awaitPromise: true,
    });
    const value = r.result?.result?.value;
    if (value === undefined) {
      throw new Error("evaluate failed: " + JSON.stringify(r).slice(0, 300));
    }
    return JSON.parse(value);
  };

  return { ws, ready, send, evaluate, problems };
}

/* -------------------------------------------------------------------- main */
let failures = 0;
const check = (name, ok, detail) => {
  if (!ok) failures++;
  console.log(`${ok ? "PASS" : "FAIL"}  ${name}${detail ? "  — " + detail : ""}`);
};

const profile = await mkdtemp(join(tmpdir(), "ersilia-verify-"));
const { server, port } = await serve(SITE);
const { child, page } = await launchChrome(9411, profile);
const cdp = connect(page.webSocketDebuggerUrl);
await cdp.ready;

try {
  await cdp.send("Runtime.enable");
  await cdp.send("Page.enable");
  await cdp.send("Network.enable");
  // MANDATORY. Without it the checks run against a cached bundle and report failures
  // that are not real, or worse, pass on stale code.
  await cdp.send("Network.setCacheDisabled", { cacheDisabled: true });

  // ---- layout stability -------------------------------------------------------
  // Charts once grew a pixel per animation frame, without bound: echarts.init() writes
  // an explicit height onto an IN-FLOW inner div, fractional card heights meant every
  // resize() rounded it up, and that pixel grew the row, which grew the chart's share,
  // which rounded up again. One row went from 309px past 800px while being watched.
  // Nothing in a static snapshot can catch that, so measure twice and compare.
  await cdp.send("Page.navigate", {
    url: `http://127.0.0.1:${port}/index.html?v=${Date.now()}#/models`,
  });
  await new Promise((r) => setTimeout(r, 2500));
  const shot = () => cdp.evaluate(
    `[...document.querySelectorAll('.crow')].map(r => Math.round(r.getBoundingClientRect().height)).join(',')`);
  const first = await shot();
  await new Promise((r) => setTimeout(r, 2500));
  const second = await shot();
  check("row heights are stable over time", first === second,
    first === second ? `steady at ${first}` : `${first} -> ${second} (growing)`);

  // Two widths. The desktop pass checks structure and content; the phone pass exists
  // because a layout can be perfect at 1440 and scroll sideways at 390 — which it did.
  for (const route of ROUTES) {
    cdp.problems.length = 0;
    // A fresh query string per route so nothing can be served from memory cache.
    await cdp.send("Page.navigate", {
      url: `http://127.0.0.1:${port}/index.html?v=${Date.now()}${route === "/" ? "" : "#" + route}`,
    });

    // Poll until the app has mounted rather than sleeping a fixed time — but give up
    // quickly, because the failure mode this test exists to catch (JS that throws)
    // leaves ".loading" on screen forever, and waiting the full window for each of
    // nine routes turned a known-broken build into a two-minute run.
    let state = null;
    for (let i = 0; i < 14; i++) {
      await new Promise((r) => setTimeout(r, 250));
      try {
        state = await cdp.evaluate(`(() => {
          // Two different populations. All cards prove the page rendered at all;
          // only cards inside a chart row carry the caption contract, because the
          // Downloads view's single card is a list of links.
          const cards = [...document.querySelectorAll('.card')];
          const chartCards = [...document.querySelectorAll('.crow > .card')];
          const rows = [...document.querySelectorAll('.crow')].map(row =>
            [...row.children].reduce((sum, card) => {
              const m = /span-(\\d+)/.exec(card.className);
              return sum + (m ? Number(m[1]) : 0);
            }, 0));
          return {
            loading: !!document.querySelector('.loading'),
            cards: cards.length,
            h1: document.querySelectorAll('h1').length,
            badRows: rows.filter(n => n !== 12),
            noCaption: chartCards.filter(c => {
              if (c.querySelector('.empty')) return false;
              const p = c.querySelector('.insight');
              return !p || !p.textContent.trim();
            }).length,
            // Titles, not a count. "2 overflowing" on a thirteen-card page means
            // measuring every caption by hand to find which two.
            overflowing: chartCards.filter(c => {
              const p = c.querySelector('.insight');
              return p && p.scrollHeight > p.clientHeight + 1;
            }).map(c => (c.querySelector('h3,h2,.card-title') || {}).textContent || '?'),
            overflowX: document.documentElement.scrollWidth > window.innerWidth + 1,
            collidingLabels: (() => {
              // CATEGORY AXIS LABELS THAT RUN INTO EACH OTHER. This cannot be done
              // through the DOM: the charts render to canvas, so the labels are pixels
              // and there is no element to measure. So measure the text instead and
              // compare it against the slot each label actually gets.
              //
              // Several builders force 'interval: 0' — show EVERY label, never thin
              // them — which is what makes collisions possible at all. That is the
              // right default for a five-bucket histogram, where a hidden label is a
              // missing bucket; it just has to be checked rather than assumed.
              const ctx = document.createElement('canvas').getContext('2d');
              const bad = [];
              for (const el of document.querySelectorAll('.chart')) {
                const inst = window.echarts && echarts.getInstanceByDom(el);
                if (!inst) continue;
                let opt; try { opt = inst.getOption(); } catch { continue; }
                const axis = ((opt || {}).xAxis || [])[0];
                if (!axis || axis.type !== 'category') continue;
                const data = axis.data || [];
                if (data.length < 2) continue;
                const lab = axis.axisLabel || {};
                if (lab.show === false || lab.rotate) continue;   // rotated: not this failure
                const step = lab.interval === 1 ? 2 : 1;          // 'every other label'
                ctx.font = (lab.fontSize || 12) + 'px ' + (lab.fontFamily || 'sans-serif');
                // MEASURE WHAT IS DRAWN, NOT WHAT IS IN THE DATA. The time axes carry a
                // formatter that blanks most quarters and prints only the year, so
                // measuring the raw '2019Q3' labels reported collisions on every single
                // time series — all of them false.
                const shown = (value, index) => {
                  const raw = value == null ? '' : String(value.value ?? value);
                  if (typeof lab.formatter === 'function') {
                    try { return String(lab.formatter(raw, index) ?? ''); } catch { return raw; }
                  }
                  return raw;
                };
                // The plot is narrower than the chart by the y-axis gutter. 56px is a
                // deliberate under-estimate of that gutter, which makes the slot width
                // an OVER-estimate and this check conservative: it reports collisions
                // that are certain, not ones that are merely close.
                const perCategory = Math.max(1, inst.getWidth() - 56) / data.length;
                // Only the labels actually drawn, with the category index each sits on —
                // two labels four categories apart have four category widths between
                // them, which is why a sparse axis is fine with long labels.
                const drawn = [];
                for (let i = 0; i < data.length; i += step) {
                  const text = shown(data[i], i).trim();
                  if (text) drawn.push({ text, index: i });
                }
                for (let k = 0; k + 1 < drawn.length; k++) {
                  const a = drawn[k], b = drawn[k + 1];
                  const available = perCategory * (b.index - a.index);
                  const need = ctx.measureText(a.text).width / 2
                             + ctx.measureText(b.text).width / 2 + 4;
                  if (need > available) {
                    const card = el.closest('.card');
                    const title = card && card.querySelector('h3,h2,.card-title');
                    bad.push((title ? title.textContent.trim() : '?')
                             + ' [' + a.text + '|' + b.text + ']');
                    break;
                  }
                }
              }
              return bad;
            })(),
          };
        })()`);
      } catch { /* context still swapping */ }
      if (state && !state.loading && state.cards > 0) break;
    }

    const label = route.padEnd(15);
    if (!state) { check(label + "renders", false, "no state could be read"); continue; }

    // /downloads is a list, not a chart grid, so it legitimately has one card.
    check(label + "renders cards", state.cards > 0, `${state.cards} cards`);
    check(label + "no console errors", cdp.problems.length === 0,
      cdp.problems.slice(0, 2).join(" | ") || "clean");
    check(label + "rows sum to 12", state.badRows.length === 0,
      state.badRows.length ? "bad rows: " + state.badRows.join(",") : "all rows exact");
    check(label + "captions present and fit",
      state.noCaption === 0 && state.overflowing.length === 0,
      `${state.noCaption} missing, ${state.overflowing.length} overflowing` +
      (state.overflowing.length ? ": " + state.overflowing.join(" / ") : ""));
    check(label + "one h1, no h-overflow", state.h1 === 1 && !state.overflowX,
      `h1=${state.h1} overflowX=${state.overflowX}`);
    check(label + "axis labels do not collide", state.collidingLabels.length === 0,
      state.collidingLabels.length ? state.collidingLabels.join(" / ") : "clear");
  }
  // ---- narrow pass -------------------------------------------------------------
  await cdp.send("Emulation.setDeviceMetricsOverride",
                 { width: 390, height: 844, deviceScaleFactor: 1, mobile: true });
  for (const route of ["/", "/models", "/community", "/projects", "/reach"]) {
    cdp.problems.length = 0;
    await cdp.send("Page.navigate", {
      url: `http://127.0.0.1:${port}/index.html?v=${Date.now()}${route === "/" ? "" : "#" + route}`,
    });
    let narrow = null;
    for (let i = 0; i < 14; i++) {
      await new Promise((r) => setTimeout(r, 250));
      try {
        narrow = await cdp.evaluate(`(() => {
          const vw = document.documentElement.clientWidth;
          const wide = [];
          document.querySelectorAll('.shell *').forEach(el => {
            const r = el.getBoundingClientRect();
            if (r.width > 0 && r.right > vw + 1) {
              wide.push(el.tagName.toLowerCase() +
                (typeof el.className === 'string' && el.className
                  ? '.' + el.className.split(' ')[0] : ''));
            }
          });
          return {
            loading: !!document.querySelector('.loading'),
            cards: document.querySelectorAll('.card').length,
            scrollW: document.documentElement.scrollWidth, vw,
            wide: [...new Set(wide)].slice(0, 4),
          };
        })()`);
      } catch { /* context swapping */ }
      if (narrow && !narrow.loading && narrow.cards > 0) break;
    }
    const label = ("390px " + route).padEnd(15);
    if (!narrow) { check(label + "renders", false, "no state"); continue; }
    check(label + "no sideways scroll",
      narrow.scrollW <= narrow.vw + 1 && narrow.wide.length === 0,
      narrow.wide.length ? `${narrow.scrollW}>${narrow.vw} via ${narrow.wide.join(", ")}`
                         : `scrollWidth ${narrow.scrollW} = viewport`);
    check(label + "renders cards", narrow.cards > 0, `${narrow.cards} cards`);
  }
  await cdp.send("Emulation.clearDeviceMetricsOverride");

} finally {
  cdp.ws.close();
  child.kill();
  server.close();
  // Let Chrome actually exit before removing its profile: deleting the directory
  // underneath a live browser threw ENOENT and masked the real result. And a failure
  // to clean up a temp directory must never fail the build.
  await new Promise((resolve) => {
    child.once("exit", resolve);
    setTimeout(resolve, 3000);
  });
  try {
    await rm(profile, { recursive: true, force: true, maxRetries: 3 });
  } catch { /* a leftover temp profile is not a build failure */ }
}

console.log(failures ? `\n${failures} check(s) failed` : "\nAll checks passed");
process.exit(failures ? 1 : 0);
