/* Hash router.

   Each view renders on its own, and its ECharts instances are disposed on exit.
   The previous build initialised all 31 charts of a single long page at once;
   here only the charts you are looking at exist. Deep links (#/community) work,
   and so do browser back/forward. */

const Router = (() => {
  const routes = new Map();
  let charts = [];
  let outlet = null;
  let onAfterRender = null;

  function currentPath() {
    const hash = window.location.hash.replace(/^#/, "");
    if (!hash || hash === "/") return "/";
    return hash.startsWith("/") ? hash : "/" + hash;
  }

  function disposeCharts() {
    charts.forEach((c) => {
      // Disconnect the observer before disposing, or it fires on a dead instance.
      if (c.__observer) { try { c.__observer.disconnect(); } catch (e) { /* gone */ } }
      try { c.dispose(); } catch (e) { /* already gone */ }
    });
    charts = [];
  }

  function markNav(path) {
    document.querySelectorAll("#nav-list a").forEach((a) => {
      const target = a.getAttribute("href").replace(/^#/, "");
      if (target === path) a.setAttribute("aria-current", "page");
      else a.removeAttribute("aria-current");
    });
  }

  function render() {
    const path = currentPath();
    const view = routes.get(path) || routes.get("/");
    disposeCharts();
    outlet.innerHTML = "";
    markNav(routes.has(path) ? path : "/");
    view(outlet, charts);
    // Restart the entrance animation. Removing and re-adding the attribute on
    // separate frames is what forces the browser to replay it — without the reflow
    // in between, the class change is coalesced and nothing animates.
    outlet.removeAttribute("data-entering");
    void outlet.offsetWidth;
    outlet.setAttribute("data-entering", "");
    // Charts initialise while the flex rows are still resolving; re-fit once the
    // layout has been flushed. The per-chart ResizeObserver catches the rest.
    requestAnimationFrame(() => charts.forEach((c) => c.resize()));
    document.title = (view.title ? view.title + " · " : "") + "Ersilia in numbers";
    if (onAfterRender) onAfterRender(path);
    // Jump, not glide: a smooth scroll competing with the entrance animation reads
    // as lag. The animation supplies the sense of movement.
    window.scrollTo({ top: 0, behavior: "auto" });
  }

  function debounce(fn, ms) {
    let timer;
    return () => { clearTimeout(timer); timer = setTimeout(fn, ms); };
  }

  return {
    add(path, view, title) {
      view.title = title;
      routes.set(path, view);
    },
    start(outletEl, afterRender) {
      outlet = outletEl;
      onAfterRender = afterRender || null;
      window.addEventListener("hashchange", render);
      window.addEventListener("resize", debounce(() => charts.forEach((c) => c.resize()), 140));
      render();
    },
    has(path) { return routes.has(path); },
    current: currentPath,
    /* Re-run the current view. Used when an async dependency the view needed (the
       map geometry) arrives after the first paint. Safe against recursion only
       because the caller flips its own "already loaded" flag first. */
    rerender() { if (outlet) render(); },
  };
})();
