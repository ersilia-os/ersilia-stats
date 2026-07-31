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
    charts.forEach((c) => { try { c.dispose(); } catch (e) { /* already gone */ } });
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
    // Charts initialise while the grid is still resolving; re-fit once the
    // layout has been flushed, or wide cards render at the wrong width.
    requestAnimationFrame(() => charts.forEach((c) => c.resize()));
    document.title = (view.title ? view.title + " · " : "") + "Ersilia in numbers";
    if (onAfterRender) onAfterRender(path);
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
  };
})();
