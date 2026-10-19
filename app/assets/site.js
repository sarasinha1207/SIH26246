/* KaushalSetu public site: dependency-free. All numbers come from data/site_data.js and data/map_data.js (built from the project outputs).
   Text the page builds itself goes through t() / nm() so the same code can speak English or Hindi (assets/i18n-hi.js). */
(function () {
  "use strict";
  var D = window.SITE_DATA, M = window.MAP_DATA;
  var HI = window.HI || { s: {}, names: {}, months: [], titles: {} };
  var root = document.documentElement;
  var NS = "http://www.w3.org/2000/svg";
  var MONTHS_EN = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };
  var fmt = function (n, d) { return Number(n).toLocaleString("en-IN", { minimumFractionDigits: d || 0, maximumFractionDigits: d || 0 }); };
  var sign = function (n, d) { return (n > 0.0001 ? "+" : n < -0.0001 ? "−" : "") + Math.abs(n).toFixed(d == null ? 0 : d) + "%"; };
  var reduced = function () { return root.dataset.motion === "reduced"; };
  var css = function (n) { return getComputedStyle(root).getPropertyValue(n).trim(); };
  var colors = function () { return { demand: css("--demand"), demandDeep: css("--demand-deep"), supply: css("--supply"), supplyInk: css("--supply-ink"), ink: css("--ink"), ink2: css("--ink-2"), line: css("--line"), employed: css("--employed"), band2: css("--band-2"), surface: css("--surface") }; };

  /* ---------- language ---------- */
  var isHi = function () { return root.dataset.lang === "hi"; };
  function t(s, v) {
    var o = (isHi() && HI.s[s]) || s;
    return v ? o.replace(/\{(\w+)\}/g, function (m, k) { return v[k] != null ? v[k] : m; }) : o;
  }
  function nm(s) { return (isHi() && HI.names[s]) || s; }
  var NAME = { E: "Employed workers", V: "Job vacancies", S: "Registered job seekers" };
  var nameOf = function (k) { return t(NAME[k]); };
  var mon = function (i) { return isHi() && HI.months[i] ? HI.months[i] : MONTHS_EN[i]; };
  var mlabel = function (ym) { var p = ym.split("-"); return mon(+p[1] - 1) + " " + p[0]; };
  var longDate = function (s) { var m = /^([A-Za-z]+) (\d{4})$/.exec(s); return m ? nm(m[1]) + " " + m[2] : s; };
  var plural = function (n) { return n + " " + t(n === 1 ? "month" : "months"); };
  var addMonths = function (ym, n) { var p = ym.split("-"), i = (+p[0]) * 12 + (+p[1] - 1) + n; return Math.floor(i / 12) + "-" + ("0" + ((i % 12) + 1)).slice(-2); };

  function el(tag, attrs, parent) {
    var e = document.createElementNS(NS, tag);
    for (var k in attrs) e.setAttribute(k, attrs[k]);
    if (parent) parent.appendChild(e);
    return e;
  }
  function inView(node, fn) {
    if (!("IntersectionObserver" in window)) { fn(node); return; }
    var io = new IntersectionObserver(function (es) { es.forEach(function (e) { if (e.isIntersecting) { fn(e.target); io.unobserve(e.target); } }); }, { threshold: 0.2 });
    io.observe(node);
  }
  function ease(t_) { return 1 - Math.pow(1 - t_, 3); }
  function tween(ms, step, done) {
    if (reduced()) { step(1); if (done) done(); return; }
    var t0 = null;
    function f(ts) { if (t0 === null) t0 = ts; var p = Math.min(1, (ts - t0) / ms); step(ease(p)); if (p < 1) requestAnimationFrame(f); else if (done) done(); }
    requestAnimationFrame(f);
  }
  function drawLine(path, ms, delay) {
    return new Promise(function (res) {
      if (reduced()) { res(); return; }
      var len = path.getTotalLength();
      path.style.strokeDasharray = len; path.style.strokeDashoffset = len;
      var a = path.animate([{ strokeDashoffset: len }, { strokeDashoffset: 0 }], { duration: ms, delay: delay || 0, easing: "cubic-bezier(.4,.1,.2,1)", fill: "forwards" });
      a.onfinish = function () { path.style.strokeDasharray = path.getAttribute("data-dash") || "none"; path.style.strokeDashoffset = 0; res(); };
    });
  }
  function fade(node, ms, delay) {
    return new Promise(function (res) {
      if (reduced()) { node.style.opacity = 1; res(); return; }
      node.style.opacity = 0;
      var a = node.animate([{ opacity: 0 }, { opacity: 1 }], { duration: ms, delay: delay || 0, fill: "forwards", easing: "ease-out" });
      a.onfinish = function () { node.style.opacity = 1; res(); };
    });
  }

  /* ---------- tooltip ---------- */
  var tip = $("#tip");
  function showTip(html, x, y) {
    if (!tip) return;
    tip.innerHTML = html; tip.hidden = false;
    var w = tip.offsetWidth, h = tip.offsetHeight;
    var left = Math.min(Math.max(8, x + 14), window.innerWidth - w - 8), top = y - h - 14 < 8 ? y + 18 : y - h - 14;
    tip.style.left = left + "px"; tip.style.top = top + "px";
  }
  function hideTip() { if (tip) tip.hidden = true; }
  document.addEventListener("pointermove", function (e) {
    var n = e.target.closest ? e.target.closest("[data-tip]") : null;
    if (n) showTip(n.getAttribute("data-tip"), e.clientX, e.clientY); else if (!document.body.classList.contains("tip-chart")) hideTip();
  });
  document.addEventListener("pointerleave", hideTip);
  document.addEventListener("focusin", function (e) {
    var n = e.target.closest ? e.target.closest("[data-tip]") : null;
    if (n) { var r = n.getBoundingClientRect(); showTip(n.getAttribute("data-tip"), r.left + r.width / 2, r.top); }
  });
  document.addEventListener("focusout", hideTip);

  /* ---------- display options: text size, theme, language ---------- */
  var STORE = "lmis-display", SIZES = ["s", "m", "l", "xl"];
  var settings = {};
  try { settings = JSON.parse(localStorage.getItem(STORE) || "{}"); } catch (e) { settings = {}; }
  var sysReduce = window.matchMedia && matchMedia("(prefers-reduced-motion: reduce)").matches;
  var ENTITLE = document.title;
  function ensureHindiFont() {
    if (document.getElementById("font-hi")) return;
    var l = document.createElement("link"); l.rel = "stylesheet"; l.id = "font-hi"; l.href = "https://fonts.googleapis.com/css2?family=Noto+Sans+Devanagari:wght@400..800&display=swap"; l.media = "print"; l.onload = function () { l.media = "all"; };
    document.head.appendChild(l);
  }
  function applyLang() {
    var hi = isHi();
    root.lang = hi ? "hi" : "en";
    $$("[data-hi]").forEach(function (n) { if (n.getAttribute("data-en") === null) n.setAttribute("data-en", n.innerHTML); n.innerHTML = hi ? n.getAttribute("data-hi") : n.getAttribute("data-en"); });
    $$("[data-hi-aria]").forEach(function (n) { if (n.getAttribute("data-en-aria") === null) n.setAttribute("data-en-aria", n.getAttribute("aria-label")); n.setAttribute("aria-label", hi ? n.getAttribute("data-hi-aria") : n.getAttribute("data-en-aria")); });
    document.title = (hi && HI.titles[ENTITLE]) || ENTITLE;
    if (hi) ensureHindiFont();
  }
  function applySettings(rerender) {
    root.dataset.theme = settings.theme === "light" ? "light" : "dark";
    root.dataset.size = SIZES.indexOf(settings.size) >= 0 ? settings.size : "m";
    root.dataset.lang = settings.lang === "hi" ? "hi" : "en";
    root.dataset.motion = sysReduce ? "reduced" : "full";
    var idx = SIZES.indexOf(root.dataset.size);
    $$(".display-panel button[data-opt]").forEach(function (b) { b.setAttribute("aria-pressed", root.dataset[b.dataset.opt] === b.dataset.val); });
    $$(".display-panel button[data-size-step]").forEach(function (b) {
      var st = +b.dataset.sizeStep;
      b.disabled = (st < 0 && idx === 0) || (st > 0 && idx === SIZES.length - 1);
      b.classList.toggle("is-default", st === 0 && root.dataset.size === "m");
    });
    var meta = $('meta[name="theme-color"]');
    if (meta) meta.setAttribute("content", root.dataset.theme === "dark" ? "#0A0E16" : "#F4F7FC");
    applyLang();
    if (rerender) { fills(); refresh(); }
  }
  function save() { try { localStorage.setItem(STORE, JSON.stringify(settings)); } catch (e) { /* storage unavailable: the choice lasts for this visit */ } }
  var dBtn = $(".display-btn"), dPanel = $("#display-panel");
  function setPanel(open) {
    if (!dBtn || !dPanel) return;
    dBtn.setAttribute("aria-expanded", open); dPanel.hidden = !open;
  }
  if (dBtn) {
    dBtn.addEventListener("click", function (e) { e.stopPropagation(); setPanel(dPanel.hidden); });
    document.addEventListener("click", function (e) { if (!dPanel.hidden && !e.target.closest(".display")) setPanel(false); });
    document.addEventListener("keydown", function (e) { if (e.key === "Escape" && !dPanel.hidden) { setPanel(false); dBtn.focus(); } });
    $$("button[data-opt]", dPanel).forEach(function (b) {
      b.addEventListener("click", function () { settings[b.dataset.opt] = b.dataset.val; save(); applySettings(true); });
    });
    $$("button[data-size-step]", dPanel).forEach(function (b) {
      b.addEventListener("click", function () {
        var i = SIZES.indexOf(root.dataset.size), st = +b.dataset.sizeStep;
        settings.size = st === 0 ? "m" : SIZES[Math.max(0, Math.min(SIZES.length - 1, i + st))];
        save(); applySettings(false);
      });
    });
  }

  /* ---------- header: progress, shadow, back to top, mobile menu ---------- */
  var header = $(".site-header"), prog = $(".progress"), toTop = $(".to-top");
  function onScroll() {
    var y = window.scrollY || root.scrollTop, h = root.scrollHeight - window.innerHeight;
    if (prog) prog.style.setProperty("--p", h > 0 ? Math.min(1, y / h) : 0);
    if (header) header.classList.toggle("scrolled", y > 8);
    if (toTop) toTop.classList.toggle("show", y > 700);
  }
  window.addEventListener("scroll", onScroll, { passive: true }); onScroll();
  if (toTop) toTop.addEventListener("click", function () { window.scrollTo({ top: 0, behavior: reduced() ? "auto" : "smooth" }); });
  var nav = $(".nav"), toggle = $(".nav-toggle");
  if (toggle) toggle.addEventListener("click", function () { var open = nav.classList.toggle("open"); toggle.setAttribute("aria-expanded", open); });

  /* ---------- card spotlight: a soft glow follows the pointer ---------- */
  document.addEventListener("pointermove", function (e) {
    if (reduced()) return;
    var c = e.target.closest ? e.target.closest(".card") : null;
    if (!c) return;
    var r = c.getBoundingClientRect();
    c.style.setProperty("--mx", (e.clientX - r.left) + "px"); c.style.setProperty("--my", (e.clientY - r.top) + "px");
  });

  /* ---------- scroll reveal ---------- */
  var REVEAL = ".card, .stats-grid, .map-panel, .how-steps > li, .how-stage, .cta-card, .timeline, .chart-card, .table-wrap, .hero-chips li, .page-head .wrap > *, .sec-intro, .sec-head, .note, h2";
  function reveal() {
    $$(REVEAL).forEach(function (n) {
      if (n.classList.contains("reveal") || n.closest(".hero") || n.closest(".map-details")) return;
      var sibs = n.parentNode ? Array.prototype.indexOf.call(n.parentNode.children, n) : 0;
      n.style.setProperty("--i", Math.min(sibs, 6));
      n.classList.add("reveal");
      if (reduced()) n.classList.add("in"); else inView(n, function (x) { x.classList.add("in"); });
    });
  }

  /* ---------- hero chart ---------- */
  var heroState = { V: true, S: true, range: true };
  function heroChart(intro) {
    var host = $("#hero-chart");
    if (!host || !D) return;
    host.innerHTML = "";
    var C = colors(), H = D.hero, W = 700, HT = 430, m = { l: 44, r: 150, t: 30, b: 48 };
    var nh = H.V.history.length, nf = H.V.forecast.length, n = nh + nf - 1;
    var all = [].concat(H.V.history, H.S.history, H.V.lo, H.V.hi, H.S.lo, H.S.hi);
    var lo = Math.floor((Math.min.apply(null, all) - 4) / 10) * 10, hi = Math.ceil((Math.max.apply(null, all) + 4) / 10) * 10;
    var x = function (i) { return m.l + (i / n) * (W - m.l - m.r); };
    var y = function (v) { return m.t + (1 - (v - lo) / (hi - lo)) * (HT - m.t - m.b); };
    var svg = el("svg", { viewBox: "0 0 " + W + " " + HT, class: "chart-svg", role: "img", "aria-labelledby": "hc-t hc-d" }, host);
    el("title", { id: "hc-t" }, svg).textContent = t("Forecast of job vacancies and registered job seekers with 90% ranges");
    el("desc", { id: "hc-d" }, svg).textContent = t("Example: {district}, {sector}. Vacancies are forecast to change by {v} and job seekers by {s} by {m}, relative to {m0}.",
      { district: nm(H.district), sector: nm(H.sector), v: sign(H.V.forecast[nf - 1] - 100), s: sign(H.S.forecast[nf - 1] - 100), m: mlabel(H.V.forecast_months[nf - 1]), m0: mlabel(H.V.history_months[nh - 1]) });
    var cp = el("clipPath", { id: "fanclip" }, el("defs", {}, svg));
    var clipRect = el("rect", { x: x(nh - 1), y: 0, width: (intro && !reduced()) ? 0 : W, height: HT }, cp);
    for (var g = Math.ceil(lo / 25) * 25; g <= hi; g += 25) {
      el("line", { x1: m.l, x2: W - m.r, y1: y(g), y2: y(g), stroke: g === 100 ? C.ink2 : C.line, "stroke-dasharray": g === 100 ? "none" : "3 5" }, svg);
      el("text", { x: m.l - 10, y: y(g) + 4, "text-anchor": "end", class: "small" }, svg).textContent = g;
    }
    [[0, "start"], [nh - 1, "middle"], [n, "end"]].forEach(function (tk, i) {
      el("text", { x: x(tk[0]), y: HT - 16, "text-anchor": tk[1], class: "small" }, svg).textContent = mlabel(i < 2 ? H.V.history_months[tk[0]] : H.V.forecast_months[nf - 1]);
    });
    var series = { V: el("g", {}, svg), S: el("g", {}, svg) };
    var parts = {};
    ["V", "S"].forEach(function (k) {
      var S = H[k], color = k === "V" ? C.demand : C.supply, grp = series[k];
      var pts = ["" + x(nh - 1) + "," + y(100)];
      S.hi.forEach(function (v, i) { pts.push(x(nh + i) + "," + y(v)); });
      for (var i = nf - 1; i >= 0; i--) pts.push(x(nh + i) + "," + y(S.lo[i]));
      var fan = el("g", { "clip-path": "url(#fanclip)", class: "fan-g" }, grp);
      el("polygon", { points: pts.join(" "), fill: color, "fill-opacity": ".18" }, fan);
      var path = function (arr, from) { return arr.map(function (v, i) { return (i ? "L" : "M") + x(from + i).toFixed(1) + " " + y(v).toFixed(1); }).join(""); };
      var hist = el("path", { d: path(S.history, 0), fill: "none", stroke: color, "stroke-width": 3, "stroke-linecap": "round", "stroke-linejoin": "round" }, grp);
      var fc = el("path", { d: path([100].concat(S.forecast), nh - 1), fill: "none", stroke: color, "stroke-width": 3, "stroke-linecap": "round", "stroke-dasharray": "7 6", "data-dash": "7 6" }, grp);
      parts[k] = { fan: fan, hist: hist, fc: fc };
    });
    var today = el("g", {}, svg);
    el("line", { x1: x(nh - 1), x2: x(nh - 1), y1: m.t - 6, y2: HT - m.b, stroke: C.ink, "stroke-width": 1.2, "stroke-dasharray": "4 4" }, today);
    el("text", { x: x(nh - 1) - 8, y: m.t + 6, "text-anchor": "end", class: "small" }, today).textContent = t("What happened");
    el("text", { x: x(nh - 1) + 8, y: m.t + 6, class: "small" }, today).textContent = t("What we forecast");
    el("circle", { cx: x(nh - 1), cy: y(100), r: 5, fill: C.ink }, today);
    if (!reduced()) el("circle", { cx: x(nh - 1), cy: y(100), r: 5, fill: C.demand, class: "pulse" }, today);
    var labels = el("g", {}, svg);
    var ev = H.V.forecast[nf - 1], es = H.S.forecast[nf - 1], yv = y(ev), ys = y(es);
    if (Math.abs(yv - ys) < 48) { if (yv < ys) { yv -= 18; ys += 18; } else { yv += 18; ys -= 18; } }
    var lab = { V: el("g", {}, labels), S: el("g", {}, labels) };
    el("text", { x: x(n) + 10, y: yv, class: "lbl-v" }, lab.V).textContent = t("Vacancies {v}", { v: sign(ev - 100) });
    el("text", { x: x(n) + 10, y: yv + 18, class: "small" }, lab.V).textContent = t("range {a} to {b}", { a: sign(H.V.lo[nf - 1] - 100), b: sign(H.V.hi[nf - 1] - 100) });
    el("text", { x: x(n) + 10, y: ys, class: "lbl-s" }, lab.S).textContent = t("Job seekers {v}", { v: sign(es - 100) });
    el("text", { x: x(n) + 10, y: ys + 18, class: "small" }, lab.S).textContent = t("range {a} to {b}", { a: sign(H.S.lo[nf - 1] - 100), b: sign(H.S.hi[nf - 1] - 100) });
    var cap = $("#hero-caption");
    if (cap) cap.innerHTML = t("<strong>Example: {district}, {sector} ({state}).</strong> Both lines show change relative to {m}. Shaded bands hold nine in ten expected outcomes. This series was chosen because it is {rule}; it is an illustration, not a typical case. Simulated data.",
      { district: nm(H.district), sector: nm(H.sector), state: nm(H.state), m: mlabel(H.V.history_months[nh - 1]), rule: t(H.rule) });

    function applyToggles() {
      ["V", "S"].forEach(function (k) {
        series[k].style.display = heroState[k] ? "" : "none"; lab[k].style.display = heroState[k] ? "" : "none";
        parts[k].fan.style.display = heroState.range ? "" : "none";
      });
    }
    applyToggles();

    var hoverG = el("g", { style: "display:none", "pointer-events": "none" }, svg);
    var hl = el("line", { y1: m.t, y2: HT - m.b, stroke: C.ink, "stroke-width": 1 }, hoverG);
    var hv = el("circle", { r: 6, fill: C.demand, stroke: C.surface, "stroke-width": 2 }, hoverG), hs = el("circle", { r: 6, fill: C.supply, stroke: C.surface, "stroke-width": 2 }, hoverG);
    var catcher = el("rect", { x: m.l, y: m.t, width: W - m.l - m.r, height: HT - m.t - m.b, fill: "transparent", style: "cursor:crosshair" }, svg);
    function at(i) {
      var f = i - (nh - 1), isF = f > 0;
      var vv = isF ? H.V.forecast[f - 1] : H.V.history[i], ss = isF ? H.S.forecast[f - 1] : H.S.history[i];
      var month = isF ? H.V.forecast_months[f - 1] : H.V.history_months[i];
      var html = "<b>" + mlabel(month) + (isF ? " " + t("(forecast)") : "") + "</b>";
      if (heroState.V) html += "<br>" + t("Vacancies {v}", { v: sign(vv - 100) }) + (isF ? " (" + t("{a} to {b}", { a: sign(H.V.lo[f - 1] - 100), b: sign(H.V.hi[f - 1] - 100) }) + ")" : "");
      if (heroState.S) html += "<br>" + t("Job seekers {v}", { v: sign(ss - 100) }) + (isF ? " (" + t("{a} to {b}", { a: sign(H.S.lo[f - 1] - 100), b: sign(H.S.hi[f - 1] - 100) }) + ")" : "");
      return { vv: vv, ss: ss, html: html };
    }
    function move(e) {
      var r = svg.getBoundingClientRect(), px = (e.clientX - r.left) / r.width * W;
      var i = Math.max(0, Math.min(n, Math.round((px - m.l) / (W - m.l - m.r) * n)));
      var d = at(i);
      hoverG.style.display = ""; hl.setAttribute("x1", x(i)); hl.setAttribute("x2", x(i));
      hv.setAttribute("cx", x(i)); hv.setAttribute("cy", y(d.vv)); hs.setAttribute("cx", x(i)); hs.setAttribute("cy", y(d.ss));
      hv.style.display = heroState.V ? "" : "none"; hs.style.display = heroState.S ? "" : "none";
      document.body.classList.add("tip-chart"); showTip(d.html, e.clientX, e.clientY);
    }
    catcher.addEventListener("pointermove", move);
    catcher.addEventListener("pointerdown", move);
    catcher.addEventListener("pointerleave", function () { hoverG.style.display = "none"; document.body.classList.remove("tip-chart"); hideTip(); });

    if (intro && !reduced()) {
      [today, labels].forEach(function (n_) { n_.style.opacity = 0; });
      ["V", "S"].forEach(function (k) { parts[k].fan.style.opacity = 0; parts[k].fc.style.opacity = 0; });
      Promise.all([drawLine(parts.V.hist, 1500), drawLine(parts.S.hist, 1500, 150)]).then(function () { return fade(today, 350); }).then(function () {
        ["V", "S"].forEach(function (k, i) { parts[k].fc.style.opacity = 1; parts[k].fan.style.opacity = 1; drawLine(parts[k].fc, 1000, i * 100); });
        tween(1100, function (p) { clipRect.setAttribute("width", p * (W - x(nh - 1))); });
        return new Promise(function (r) { setTimeout(r, 900); });
      }).then(function () { return fade(labels, 500); });
    }
  }
  function heroControls() {
    $$(".chart-tools .chip[data-show]").forEach(function (b) {
      b.addEventListener("click", function () {
        var k = b.dataset.show; heroState[k] = !heroState[k]; b.setAttribute("aria-pressed", heroState[k]); b.classList.toggle("on", heroState[k]);
        heroChart(false);
      });
    });
    var rp = $("#replay-btn"); if (rp) rp.addEventListener("click", function () { heroChart(true); });
  }

  /* ---------- count-up numbers ---------- */
  function counters() {
    $$("[data-count]").forEach(function (b) {
      var target = +b.getAttribute("data-count");
      if (reduced()) { b.textContent = fmt(target); return; }
      b.textContent = "0";
      inView(b, function () { tween(1200, function (p) { b.textContent = fmt(Math.round(p * target)); }); });
    });
  }

  /* ---------- how it works: four steps, one picture each ---------- */
  function how() {
    var wrap = $(".how");
    if (!wrap) return;
    var steps = $$(".how-step", wrap), panels = $$(".how-panel", wrap), cur = 0, timer = null, MS = 6500, started = 0, left = MS, hold = false, seen = false;
    wrap.style.setProperty("--how-ms", MS + "ms");
    function arm() {
      clearTimeout(timer);
      if (reduced() || hold || !seen) return;
      started = Date.now();
      timer = setTimeout(function () { go((cur + 1) % steps.length, false); }, left);
    }
    function go(i, byUser) {
      cur = i; left = MS;
      steps.forEach(function (s, j) { var on = j === i; s.classList.toggle("on", on); s.setAttribute("aria-selected", on); s.tabIndex = on ? 0 : -1; });
      panels.forEach(function (p, j) { p.classList.toggle("on", j === i); });
      if (byUser) { hold = false; wrap.classList.remove("paused"); }
      arm();
    }
    function pause() { if (hold) return; hold = true; wrap.classList.add("paused"); clearTimeout(timer); left = Math.max(800, left - (Date.now() - started)); }
    function resume() { if (!hold) return; hold = false; wrap.classList.remove("paused"); arm(); }
    steps.forEach(function (s, j) {
      s.addEventListener("click", function () { go(j, true); });
      s.addEventListener("keydown", function (e) {
        var k = e.key, n = steps.length, to = k === "ArrowDown" || k === "ArrowRight" ? (j + 1) % n : k === "ArrowUp" || k === "ArrowLeft" ? (j + n - 1) % n : k === "Home" ? 0 : k === "End" ? n - 1 : -1;
        if (to >= 0) { e.preventDefault(); go(to, true); steps[to].focus(); }
      });
    });
    wrap.addEventListener("pointerenter", pause); wrap.addEventListener("pointerleave", resume);
    wrap.addEventListener("focusin", pause); wrap.addEventListener("focusout", resume);
    if ("IntersectionObserver" in window) new IntersectionObserver(function (es) { seen = es[0].isIntersecting; if (seen) { left = Math.max(left, 1500); arm(); } else { clearTimeout(timer); } }, { threshold: 0.35 }).observe(wrap);
    else seen = true;
    go(0, false);
  }

  /* ---------- the map: 56 districts, five sectors, three measures ---------- */
  var mapSt = { si: -1, k: "V", h: 12, state: "all", sel: null, hover: null }, mapEls = null, mapVB = null;
  var TI = { E: 0, V: 1, S: 2 };
  function mapValue(code) {
    var v = M.values[code], j = M.horizons.indexOf(mapSt.h), fi = 1 + j, lo = 4 + 2 * j, hi = 5 + 2 * j;
    var sis = mapSt.si < 0 ? M.sectors.map(function (_, i) { return i; }) : [mapSt.si];
    function sum(ti, idx) { return sis.reduce(function (a, si) { return a + v[si][ti][idx]; }, 0); }
    if (mapSt.k === "R") {
      var nowR = 100 * sum(1, 0) / sum(2, 0), fcR = 100 * sum(1, fi) / sum(2, fi);
      return { val: fcR, now: nowR, fc: fcR };
    }
    var ti = TI[mapSt.k], now = sum(ti, 0), fc = sum(ti, fi);
    var r = { val: (fc / now - 1) * 100, now: now, fc: fc };
    if (mapSt.si >= 0) { r.lo = sum(ti, lo); r.hi = sum(ti, hi); }
    return r;
  }
  function mapFill(cls) {
    if (mapSt.k === "R") return ["var(--supply)", "color-mix(in srgb, var(--supply) 55%, var(--surface))", "color-mix(in srgb, var(--ink-2) 40%, var(--surface))", "color-mix(in srgb, var(--demand) 55%, var(--surface))", "var(--demand)"][cls];
    var base = mapSt.k === "E" ? "var(--employed)" : mapSt.k === "V" ? "var(--demand)" : "var(--supply)";
    return "color-mix(in srgb, " + base + " " + [30, 48, 66, 84, 100][cls] + "%, var(--surface))";
  }
  var mapFmt = function (v) { return mapSt.k === "R" ? fmt(v, 1) : sign(v, 1); };
  var mapMeasureName = function () { return mapSt.k === "R" ? t("Openings per 100 job seekers") : nameOf(mapSt.k); };
  var mapSectorName = function () { return mapSt.si < 0 ? t("All sectors") : nm(M.sectors[mapSt.si]); };
  function mapConf() {
    if (mapSt.k === "R") return t("low");
    if (mapSt.si >= 0) return t(M.confidence[M.sectors[mapSt.si]][mapSt.k]);
    return mapSt.k === "E" ? t("high") : mapSt.k === "V" ? t("low") : t("medium (low for IT-ITeS)");
  }
  function mapTip(d, r) {
    var tgt = longDate(mlabelLong(addMonths(M.origin, mapSt.h)));
    var s = "<b>" + nm(d.n) + "</b> · " + nm(d.s) + "<br>" + mapMeasureName() + " (" + mapSectorName() + "): <b>" + mapFmt(r.val) + "</b>";
    if (mapSt.k === "R") s += "<br>" + t("{a} now, {b} in {m}", { a: fmt(r.now, 1), b: fmt(r.fc, 1), m: tgt });
    else s += "<br>" + t("{a} now, {b} in {m}", { a: fmt(Math.round(r.now)), b: fmt(Math.round(r.fc)), m: tgt });
    if (r.lo != null) s += "<br>" + t("90% range: {a} to {b}", { a: fmt(Math.round(r.lo)), b: fmt(Math.round(r.hi)) });
    return s + "<br>" + t("Confidence: {c}", { c: mapConf() });
  }
  var LONG = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
  function mlabelLong(ym) { var p = ym.split("-"); return LONG[+p[1] - 1] + " " + p[0]; }
  var mapPx = function () { var st = $(".map-stage"); return mapVB && st.clientWidth > 0 && st.clientHeight > 0 ? Math.min(st.clientWidth / mapVB[2], st.clientHeight / mapVB[3]) : 1; };
  function mapSetVB(vb) {
    if (!vb.every(isFinite) || vb[2] <= 0 || vb[3] <= 0) return;
    mapVB = vb; var svg = $("#map-svg");
    svg.setAttribute("viewBox", vb.map(function (n) { return n.toFixed(1); }).join(" "));
    var k = mapPx();
    $$(".mstate", svg).forEach(function (tx) {
      tx.setAttribute("font-size", (13 / k).toFixed(1)); tx.setAttribute("stroke-width", (3.5 / k).toFixed(1));
      var dx = +tx.dataset.dx || 0;
      tx.setAttribute("x", (+tx.dataset.x + dx / k).toFixed(1)); tx.setAttribute("y", (+tx.dataset.y).toFixed(1));
      if (dx) tx.style.textAnchor = "start";
    });
  }
  function mapTarget() {
    var st = $(".map-stage"), r = st.clientWidth > 0 && st.clientHeight > 0 ? st.clientWidth / st.clientHeight : 1, b;
    if (mapSt.state === "all") b = M.viewBox.slice(); else {
      var ds = M.districts.concat(M.others || []).filter(function (d) { return d.s === mapSt.state; }), x0 = 1e9, y0 = 1e9, x1 = -1e9, y1 = -1e9;
      ds.forEach(function (d) { x0 = Math.min(x0, d.bb[0]); y0 = Math.min(y0, d.bb[1]); x1 = Math.max(x1, d.bb[2]); y1 = Math.max(y1, d.bb[3]); });
      var pad = Math.max(x1 - x0, y1 - y0) * 0.14; b = [x0 - pad, y0 - pad, x1 - x0 + 2 * pad, y1 - y0 + 2 * pad];
    }
    var cx = b[0] + b[2] / 2, cy = b[1] + b[3] / 2, w = b[2], h = b[3];
    if (w / h < r) w = h * r; else h = w / r;
    return [cx - w / 2, cy - h / 2, w, h];
  }
  function mapZoom(animate) {
    var to = mapTarget(), from = mapVB || to;
    if (!animate || reduced()) { mapSetVB(to); return; }
    tween(750, function (p) { mapSetVB(from.map(function (a, i) { return a + (to[i] - a) * p; })); });
  }
  function mapBuild() {
    var svg = $("#map-svg");
    if (!svg || !M) return;
    svg.innerHTML = ""; svg.setAttribute("class", "map-svg intro");
    el("path", { d: M.backdrop, class: "mbackdrop" }, svg);
    mapEls = { dist: {}, state: {}, extra: [] };
    var og = el("g", {}, svg);
    (M.others || []).forEach(function (o, i) {
      var q = el("path", { d: o.d, class: "mextra", "data-state": o.s, style: "--i:" + i }, og);
      q.addEventListener("click", function () { if (mapSt.state === "all") { mapSt.state = o.s; mapSt.sel = null; mapZoom(true); mapRender(); } });
      mapEls.extra.push({ o: o, p: q });
    });
    var g = el("g", {}, svg);
    M.districts.forEach(function (d, i) {
      var p = el("path", { d: d.d, class: "mdist", "data-code": d.c, style: "--i:" + i }, g);
      p.addEventListener("pointerenter", function () { mapSt.hover = d.c; mapHL(); });
      p.addEventListener("pointerleave", function () { mapSt.hover = null; mapHL(); });
      p.addEventListener("click", function () {
        if (mapSt.state === "all") { mapSt.state = d.s; mapSt.sel = null; mapZoom(true); } else mapSt.sel = mapSt.sel === d.c ? null : d.c;
        mapRender();
      });
      mapEls.dist[d.c] = p;
    });
    mapEls.hl = el("path", { class: "mhl", d: "" }, svg);
    var names = {};
    M.districts.concat(M.others || []).forEach(function (d) { (names[d.s] = names[d.s] || []).push(d); });
    Object.keys(names).forEach(function (s) {
      var ds = names[s], x = ds.reduce(function (a, d) { return a + (d.bb[0] + d.bb[2]) / 2; }, 0) / ds.length, y = ds.reduce(function (a, d) { return a + (d.bb[1] + d.bb[3]) / 2; }, 0) / ds.length;
      var tx = el("text", { class: "mstate", "data-x": x, "data-y": y, "data-dx": s === "Delhi" ? 16 : 0 }, svg);
      mapEls.state[s] = tx;
    });
    mapSetVB(mapTarget());
    setTimeout(function () { svg.setAttribute("class", "map-svg"); }, 2600);
  }
  function mapHL() {
    if (!mapEls) return;
    var code = mapSt.hover || mapSt.sel, d = code && mapEls.dist[code];
    mapEls.hl.setAttribute("d", d ? d.getAttribute("d") : "");
    $$("#map-side [data-code]").forEach(function (b) { b.classList.toggle("on", b.dataset.code === code); });
  }
  function mapControls() {
    var sel = $("#map-sector"), meas = $("#map-measure"), hs = $("#map-h"), sts = $("#map-state");
    if (!sel) return;
    sel.innerHTML = ""; meas.innerHTML = ""; hs.innerHTML = ""; sts.innerHTML = "";
    sel.setAttribute("aria-label", t("Sector"));
    [["-1", t("All sectors")]].concat(M.sectors.map(function (s, i) { return [String(i), nm(s)]; })).forEach(function (o) { var op = document.createElement("option"); op.value = o[0]; op.textContent = o[1]; sel.appendChild(op); });
    sel.value = String(mapSt.si);
    if (!sel.dataset.bound) { sel.dataset.bound = "1"; sel.addEventListener("change", function () { mapSt.si = +sel.value; mapRender(); }); }
    meas.setAttribute("aria-label", t("Show"));
    [["E", nameOf("E")], ["V", nameOf("V")], ["S", nameOf("S")], ["R", t("Openings per seeker")]].forEach(function (o) {
      var b = document.createElement("button"); b.type = "button"; b.className = "tab"; b.setAttribute("role", "tab"); b.dataset.k = o[0]; b.textContent = o[1];
      b.addEventListener("click", function () { mapSt.k = o[0]; mapRender(); }); meas.appendChild(b);
    });
    hs.setAttribute("aria-label", t("Months ahead"));
    M.horizons.forEach(function (h) {
      var b = document.createElement("button"); b.type = "button"; b.className = "chip"; b.dataset.h = h; b.textContent = plural(h);
      b.addEventListener("click", function () { mapSt.h = h; mapRender(); }); hs.appendChild(b);
    });
    sts.setAttribute("aria-label", t("State"));
    [["all", t("All four states")]].concat(["Maharashtra", "Delhi", "West Bengal", "Tamil Nadu"].map(function (s) { return [s, nm(s)]; })).forEach(function (o) {
      var b = document.createElement("button"); b.type = "button"; b.className = "chip"; b.dataset.s = o[0]; b.textContent = o[1];
      b.addEventListener("click", function () { mapSt.state = o[0]; mapSt.sel = null; mapZoom(true); mapRender(); }); sts.appendChild(b);
    });
  }
  function mapRender() {
    if (!M || !mapEls) return;
    $$("#map-measure .tab").forEach(function (b) { b.setAttribute("aria-selected", b.dataset.k === mapSt.k); });
    $$("#map-h .chip").forEach(function (b) { b.setAttribute("aria-pressed", +b.dataset.h === mapSt.h); });
    $$("#map-state .chip").forEach(function (b) { b.setAttribute("aria-pressed", b.dataset.s === mapSt.state); });
    var rows = M.districts.map(function (d) { var r = mapValue(d.c); r.d = d; return r; });
    var order = rows.slice().sort(function (a, b) { return a.val - b.val; });
    order.forEach(function (r, i) { r.cls = Math.min(4, Math.floor(i * 5 / order.length)); });
    rows.forEach(function (r) {
      var p = mapEls.dist[r.d.c];
      p.style.fill = mapFill(r.cls); p.setAttribute("data-tip", mapTip(r.d, r));
      p.classList.toggle("dim", mapSt.state !== "all" && r.d.s !== mapSt.state);
      p.setAttribute("aria-label", nm(r.d.n) + ": " + mapFmt(r.val));
    });
    mapEls.extra.forEach(function (e) {
      e.p.setAttribute("data-tip", "<b>" + nm(e.o.n) + "</b> \u00b7 " + nm(e.o.s) + "<br>" + t("No forecast data for this district in this demonstration"));
      e.p.classList.toggle("dim", mapSt.state !== "all" && e.o.s !== mapSt.state);
    });
    $$(".mstate", $("#map-svg")).forEach(function (tx) { var s = Object.keys(mapEls.state).filter(function (k) { return mapEls.state[k] === tx; })[0]; tx.textContent = nm(s); tx.style.display = mapSt.state === "all" || mapSt.state === s ? "" : "none"; });
    $("#map-svg").setAttribute("aria-label", t("Map of the 56 districts, coloured by {m} for {s}, {n} ahead", { m: mapMeasureName(), s: mapSectorName(), n: plural(mapSt.h) }));
    // legend: the value range of each fifth
    var lg = $("#map-legend"), ranges = [];
    for (var c = 0; c < 5; c++) { var vs = order.filter(function (r) { return r.cls === c; }).map(function (r) { return r.val; }); ranges.push([Math.min.apply(null, vs), Math.max.apply(null, vs)]); }
    lg.innerHTML = '<div class="lg-t">' + t("{m}, {n} ahead. Five equal groups of districts, lowest to highest", { m: mapMeasureName(), n: plural(mapSt.h) }) + '</div><div class="lg-row">' +
      ranges.map(function (r, c) { return '<span class="lg"><i style="background:' + mapFill(c) + '"></i>' + mapFmt(r[0]) + " → " + mapFmt(r[1]) + "</span>"; }).join("") + '<span class="lg"><i class="lg-none"></i>' + t("Other districts of these states: no forecast data") + "</span></div>";
    // side panel
    var inReg = rows.filter(function (r) { return mapSt.state === "all" || r.d.s === mapSt.state; });
    var tgt = longDate(mlabelLong(addMonths(M.origin, mapSt.h)));
    var side = $("#map-side"), sel = mapSt.sel && rows.filter(function (r) { return r.d.c === mapSt.sel; })[0], html = "";
    if (sel) {
      html += '<div class="map-sum"><div class="lbl">' + nm(sel.d.n) + " · " + nm(sel.d.s) + '</div><span class="big">' + mapFmt(sel.val) + '</span><p class="sub">' + mapMeasureName() + ", " + mapSectorName() + '</p><p class="sub">' +
        (mapSt.k === "R" ? t("{a} now, {b} in {m}", { a: fmt(sel.now, 1), b: fmt(sel.fc, 1), m: tgt }) : t("{a} now, {b} in {m}", { a: fmt(Math.round(sel.now)), b: fmt(Math.round(sel.fc)), m: tgt })) +
        (sel.lo != null ? "<br>" + t("90% range: {a} to {b}", { a: fmt(Math.round(sel.lo)), b: fmt(Math.round(sel.hi)) }) : "") + "<br>" + t("Confidence: {c}", { c: mapConf() }) + "</p>" +
        '<p class="sub"><button type="button" class="ulink" id="map-clear">' + t("Show the whole region again") + "</button></p></div>";
    } else {
      var now = 0, fc = 0, nowV = 0, nowS = 0, fcV = 0, fcS = 0;
      inReg.forEach(function (r) {
        if (mapSt.k === "R") { var sis = mapSt.si < 0 ? M.sectors.map(function (_, i) { return i; }) : [mapSt.si], j = 1 + M.horizons.indexOf(mapSt.h); sis.forEach(function (si) { var v = M.values[r.d.c][si]; nowV += v[1][0]; nowS += v[2][0]; fcV += v[1][j]; fcS += v[2][j]; }); } else { now += r.now; fc += r.fc; }
      });
      var region = mapSt.state === "all" ? t("{n} districts in four states", { n: inReg.length }) : t("{n} districts in {s}", { n: inReg.length, s: nm(mapSt.state) });
      if (mapSt.k === "R") html += '<div class="map-sum"><div class="lbl">' + region + '</div><span class="big">' + fmt(100 * fcV / fcS, 1) + '</span><p class="sub">' + mapMeasureName() + ", " + mapSectorName() + '</p><p class="sub">' + t("{a} now, {b} in {m}", { a: fmt(100 * nowV / nowS, 1), b: fmt(100 * fcV / fcS, 1), m: tgt }) + "</p></div>";
      else html += '<div class="map-sum"><div class="lbl">' + region + '</div><span class="big">' + sign((fc / now - 1) * 100, 1) + '</span><p class="sub">' + mapMeasureName() + ", " + mapSectorName() + '</p><p class="sub">' + t("{a} now, {b} in {m}", { a: fmt(Math.round(now)), b: fmt(Math.round(fc)), m: tgt }) + "</p></div>";
    }
    var srt = inReg.slice().sort(function (a, b) { return b.val - a.val; });
    var item = function (r) { return '<li><button type="button" data-code="' + r.d.c + '"><span>' + nm(r.d.n) + "<small>" + nm(r.d.s) + '</small></span><span class="v">' + mapFmt(r.val) + "</span></button></li>"; };
    if (srt.length <= 10) html += '<div class="map-list"><h3>' + t("All districts, highest to lowest") + "</h3><ol>" + srt.map(item).join("") + "</ol></div>";
    else html += '<div class="map-list"><h3>' + t("Highest five districts") + "</h3><ol>" + srt.slice(0, 5).map(item).join("") + '</ol></div><div class="map-list"><h3>' + t("Lowest five districts") + "</h3><ol>" + srt.slice(-5).reverse().map(item).join("") + "</ol></div>";
    side.innerHTML = html;
    $$("#map-side [data-code]").forEach(function (b) {
      b.addEventListener("pointerenter", function () { mapSt.hover = b.dataset.code; mapHL(); }); b.addEventListener("pointerleave", function () { mapSt.hover = null; mapHL(); });
      b.addEventListener("focus", function () { mapSt.hover = b.dataset.code; mapHL(); }); b.addEventListener("blur", function () { mapSt.hover = null; mapHL(); });
      b.addEventListener("click", function () { var d = M.districts.filter(function (x) { return x.c === b.dataset.code; })[0]; if (mapSt.state === "all") { mapSt.state = d.s; mapZoom(true); } mapSt.sel = d.c; mapRender(); });
    });
    var clr = $("#map-clear"); if (clr) clr.addEventListener("click", function () { mapSt.sel = null; mapRender(); });
    mapHL();
  }
  function mapInit() {
    if (!$("#map-svg") || !M) return;
    mapBuild(); mapControls(); mapRender();
    var rz; window.addEventListener("resize", function () { clearTimeout(rz); rz = setTimeout(function () { mapZoom(false); }, 120); });
  }

  function fills() {
    if (!D) return;
    $$("[data-fill]").forEach(function (n) {
      var v = D; n.getAttribute("data-fill").split(".").forEach(function (p) { v = v && v[p]; });
      if (v != null) n.textContent = typeof v === "number" ? fmt(v) : longDate(v);
    });
  }

  /* ---------- redraw what depends on colours, language or motion when a Display option changes ---------- */
  function refresh() {
    heroChart(false);
    if (M && mapEls) { mapControls(); mapRender(); }
    $$(".reveal").forEach(function (n) { if (reduced()) n.classList.add("in"); });
  }

  applySettings(false);
  fills(); heroChart(true); heroControls(); counters(); how(); mapInit(); reveal();
})();
