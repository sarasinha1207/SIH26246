/* LMIS India dashboard: dependency-free. Everything comes from data/dash_data.js (history, forecasts, flags) and ../data/map_data.js (district shapes).
   The filters (sector, state, district) live in the URL hash, so every view can be bookmarked and shared:  #/overview?sector=Healthcare&state=Delhi  */
(function () {
  "use strict";
  var D = window.DASH, M = window.MAP_DATA, root = document.documentElement;
  var NS = "http://www.w3.org/2000/svg";
  var S = D.series, MONTHS = D.meta.months, FM = D.meta.fmonths, H = MONTHS.length, SECTORS = D.meta.sectors, STATES = D.meta.states;
  var STATUS = D.meta.status, CONTEXT = D.meta.context, CHANGE = D.meta.change;
  var CTX_NAME = ["Openings exceed seekers", "Moderate", "Oversupplied", "Deep surplus"];
  var PAGES = {
    overview: ["Overview", "Where demand and supply are drifting apart"], demand: ["Demand", "Employed workers and vacancies, with forecasts"], supply: ["Supply", "Registered job seekers and training"],
    gap: ["Gap", "Openings against seekers over time"], ranking: ["District ranking", "56 districts ranked within one sector"], warnings: ["Early warnings", "Shortage and oversupply flags from the forecast"], data: ["Data and notes", "Coverage, caveats, definitions and downloads"]
  };
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };
  var esc = function (s) { return String(s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); };
  var fmt = function (n, d) { return Number(n).toLocaleString("en-IN", { minimumFractionDigits: d || 0, maximumFractionDigits: d || 0 }); };
  var compact = function (n) { var a = Math.abs(n), s = n < 0 ? "−" : ""; return a >= 1e7 ? s + (a / 1e7).toFixed(2) + " Cr" : a >= 1e5 ? s + (a / 1e5).toFixed(2) + " L" : a >= 1e3 ? s + (a / 1e3).toFixed(1) + "K" : s + Math.round(a); };
  var pct = function (n, d) { return (n > 0.0005 ? "+" : n < -0.0005 ? "−" : "") + Math.abs(n).toFixed(d == null ? 1 : d) + "%"; };
  var MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  var ml = function (ym) { var p = ym.split("-"); return MON[+p[1] - 1] + " " + p[0]; };
  var css = function (n) { return getComputedStyle(root).getPropertyValue(n).trim(); };
  var reduced = window.matchMedia && matchMedia("(prefers-reduced-motion: reduce)").matches;
  var last = function (a) { return a[a.length - 1]; };
  var ctxOf = function (r) { return r >= 1 ? 0 : r >= 0.2 ? 1 : r >= 0.1 ? 2 : 3; };
  var byCode = {};
  S.forEach(function (s, i) { (byCode[s.code] = byCode[s.code] || []).push(i); });
  var DISTRICTS = {};
  S.forEach(function (s) { DISTRICTS[s.code] = { code: s.code, name: s.district, state: s.state }; });
  var DLIST = Object.keys(DISTRICTS).map(function (c) { return DISTRICTS[c]; }).sort(function (a, b) { return a.name < b.name ? -1 : 1; });

  function el(tag, attrs, parent) { var e = document.createElementNS(NS, tag); for (var k in attrs) e.setAttribute(k, attrs[k]); if (parent) parent.appendChild(e); return e; }

  /* ---------- tooltip ---------- */
  var tip = $("#tip");
  function showTip(html, x, y) {
    tip.innerHTML = html; tip.hidden = false;
    var w = tip.offsetWidth, h = tip.offsetHeight;
    tip.style.left = Math.min(Math.max(8, x + 14), window.innerWidth - w - 8) + "px"; tip.style.top = (y - h - 14 < 8 ? y + 18 : y - h - 14) + "px";
  }
  function hideTip() { tip.hidden = true; }
  document.addEventListener("pointermove", function (e) { var t = e.target.closest ? e.target.closest("[data-tip]") : null; if (t) showTip(t.getAttribute("data-tip"), e.clientX, e.clientY); else if (!document.body.classList.contains("tip-chart")) hideTip(); });

  /* ---------- URL state ---------- */
  var cur = { page: "overview", p: {}, csv: null };
  function parse() {
    var h = location.hash.replace(/^#\/?/, ""), q = h.split("?"), page = PAGES[q[0]] ? q[0] : "overview", p = {};
    (q[1] || "").split("&").forEach(function (kv) { if (!kv) return; var a = kv.split("="); p[decodeURIComponent(a[0])] = decodeURIComponent((a[1] || "").replace(/\+/g, " ")); });
    if (p.sector && SECTORS.indexOf(p.sector) < 0) delete p.sector;
    if (p.state && STATES.indexOf(p.state) < 0) delete p.state;
    if (p.district) { var d = DISTRICTS[p.district]; if (!d) delete p.district; else if (p.state && p.state !== d.state) delete p.district; else p.state = d.state; }
    return { page: page, p: p };
  }
  function url(page, patch) {
    var p = Object.assign({}, cur.p, patch), parts = [];
    if (patch && patch.district) p.state = DISTRICTS[patch.district].state;
    if (patch && patch.state && !patch.district && p.district && DISTRICTS[p.district].state !== patch.state) delete p.district;
    Object.keys(p).forEach(function (k) { if (p[k] !== "" && p[k] != null) parts.push(encodeURIComponent(k) + "=" + encodeURIComponent(p[k])); });
    return "#/" + page + (parts.length ? "?" + parts.join("&") : "");
  }
  function go(patch, page) { location.hash = url(page || cur.page, patch); }
  function sel(p, ignore) {
    ignore = ignore || [];
    var out = [];
    S.forEach(function (s, i) {
      if (p.sector && ignore.indexOf("sector") < 0 && s.sector !== p.sector) return;
      if (p.state && ignore.indexOf("state") < 0 && s.state !== p.state) return;
      if (p.district && ignore.indexOf("district") < 0 && s.code !== p.district) return;
      out.push(i);
    });
    return out;
  }
  var scopeText = function (p) { return [p.district ? DISTRICTS[p.district].name : p.state || "All states", p.sector || "all sectors"].join(", "); };

  /* ---------- aggregation ---------- */
  function sumH(k, idx) { var out = new Array(H).fill(0); idx.forEach(function (i) { var a = D.hist[k][i]; for (var m = 0; m < H; m++) out[m] += a[m]; }); return out; }
  function sumF(k, nm, idx) { var out = new Array(12).fill(0); idx.forEach(function (i) { var a = D.fc[k][nm][i]; for (var m = 0; m < 12; m++) out[m] += a[m]; }); return out; }
  function wavg(k, idx) {
    var num = new Array(H).fill(0), den = new Array(H).fill(0), sc = k === "U" ? 10 : 1;
    idx.forEach(function (i) { var a = D.hist[k][i], e = D.hist.E[i]; for (var m = 0; m < H; m++) { num[m] += a[m] / sc * e[m]; den[m] += e[m]; } });
    return num.map(function (v, m) { return den[m] ? v / den[m] : 0; });
  }
  function roll12(a) { return a.map(function (_, m) { if (m < 11) return null; var s = 0; for (var j = m - 11; j <= m; j++) s += a[j]; return s; }); }
  function div(a, b) { return a.map(function (v, i) { return b[i] ? v / b[i] : 0; }); }
  function confOf(k, idx) {
    if (k === "E") return "high"; if (k === "V") return "low";
    var c = {}; idx.forEach(function (i) { c[D.fc.S.conf[i]] = 1; }); var ks = Object.keys(c);
    return ks.length === 1 ? ks[0] : "medium";
  }
  var confChip = function (c) { return '<span class="conf ' + c + '">' + c + " confidence</span>"; };
  var deltaHtml = function (v, label) { return '<span class="delta ' + (v >= 0 ? "up" : "down") + '">' + pct(v) + "</span>" + (label ? " <span>" + label + "</span>" : ""); };

  /* ---------- the line chart ---------- */
  function timeline(p) { var w = p.r === "all" ? H : 60, start = Math.max(0, H - w); return { start: start, T: MONTHS.slice(start).concat(FM), nh: H - start }; }
  function ticks(lo, hi, n) {
    if (hi - lo < 1e-9) { hi = lo + 1; }
    var span = hi - lo, step = Math.pow(10, Math.floor(Math.log10(span / n))), err = span / n / step;
    step *= err >= 7 ? 10 : err >= 3 ? 5 : err >= 1.5 ? 2 : 1;
    var a = Math.floor(lo / step) * step, b = Math.ceil(hi / step) * step, out = [];
    for (var v = a; v <= b + step / 2; v += step) out.push(+v.toFixed(10));
    return out;
  }
  function legend(items) { return '<div class="legend">' + items.map(function (l) { return '<span style="--c:' + l.color + '"><i class="' + (l.cls || "") + '"></i>' + esc(l.name) + "</span>"; }).join("") + "</div>"; }
  function lineChart(host, o) {
    host.innerHTML = "";
    var W = 780, HT = o.height || 290, two = o.lines.some(function (l) { return l.axis === 1; }), m = { l: 64, r: two ? 64 : 16, t: 16, b: 32 }, nT = o.T.length, nh = o.nh;
    var rng = [[Infinity, -Infinity], [Infinity, -Infinity]];
    o.lines.forEach(function (l) {
      var r = rng[l.axis || 0], all = l.hist.concat(l.fc || []).concat(l.band ? l.band.lo.concat(l.band.hi) : []);
      all.forEach(function (v) { if (v != null && isFinite(v)) { if (v < r[0]) r[0] = v; if (v > r[1]) r[1] = v; } });
    });
    (o.hlines || []).forEach(function (hl) { var r = rng[hl.axis || 0]; if (hl.v < r[0]) r[0] = hl.v; if (hl.v > r[1]) r[1] = hl.v; });
    var sc = rng.map(function (r, ax) {
      if (!isFinite(r[0])) return null;
      var pad = (r[1] - r[0]) * 0.08 || Math.abs(r[1]) * 0.1 || 1, lo = o.zero ? Math.min(0, r[0]) : r[0] - pad, hi = r[1] + pad, t = ticks(lo, hi, 5);
      return { lo: t[0], hi: t[t.length - 1], t: t };
    });
    var x = function (i) { return m.l + (i / (nT - 1)) * (W - m.l - m.r); };
    var y = function (v, ax) { var s = sc[ax || 0]; return m.t + (1 - (v - s.lo) / (s.hi - s.lo)) * (HT - m.t - m.b); };
    var svg = el("svg", { viewBox: "0 0 " + W + " " + HT, role: "img", "aria-label": o.label || "chart" }, host);
    (o.regions || []).forEach(function (r) {
      var i0 = Math.max(0, o.T.indexOf(r.from)), i1 = o.T.indexOf(r.to); if (i1 < 0) i1 = nh - 1; if (i1 < 0 || i0 > nh - 1) return;
      el("rect", { x: x(i0), y: m.t, width: Math.max(2, x(Math.min(i1, nT - 1)) - x(i0)), height: HT - m.t - m.b, fill: r.color || css("--ink-2"), "fill-opacity": ".09" }, svg);
      el("text", { x: x(i0) + 4, y: m.t + 11, class: "axis-l" }, svg).textContent = r.label;
    });
    sc.forEach(function (s, ax) {
      if (!s) return;
      s.t.forEach(function (v) {
        if (ax === 0) el("line", { x1: m.l, x2: W - m.r, y1: y(v, 0), y2: y(v, 0), stroke: css("--line"), "stroke-dasharray": v === 0 ? "none" : "3 5" }, svg);
        el("text", { x: ax === 0 ? m.l - 8 : W - m.r + 8, y: y(v, ax) + 4, "text-anchor": ax === 0 ? "end" : "start", style: two ? "fill:" + (o.axisColors ? o.axisColors[ax] : "") : "" }, svg).textContent = (o.fmtAxis && o.fmtAxis[ax] || compact)(v);
      });
    });
    var lastYear = "";
    o.T.forEach(function (ym, i) { var yr = ym.slice(0, 4); if (ym.slice(5) === "01" && yr !== lastYear && (o.T.length < 90 || +yr % 2 === 1 || i === 0)) { lastYear = yr; el("text", { x: x(i), y: HT - 10, "text-anchor": "middle" }, svg).textContent = yr; } });
    (o.hlines || []).forEach(function (hl) {
      el("line", { x1: m.l, x2: W - m.r, y1: y(hl.v, hl.axis), y2: y(hl.v, hl.axis), stroke: hl.color || css("--ink-2"), "stroke-dasharray": "5 4", "stroke-opacity": ".7" }, svg);
      if (hl.label) el("text", { x: m.l + 6, y: y(hl.v, hl.axis) - 4, class: "mark-t" }, svg).textContent = hl.label;
    });
    (o.marks || []).forEach(function (mk) {
      var i = o.T.indexOf(mk.ym); if (i < 0) return;
      el("line", { x1: x(i), x2: x(i), y1: m.t, y2: HT - m.b, stroke: css("--ink"), "stroke-width": 1.2, "stroke-dasharray": "4 4", "stroke-opacity": ".7" }, svg);
      el("text", { x: x(i) + 5, y: m.t + 24, class: "mark-t" }, svg).textContent = mk.label;
    });
    el("line", { x1: x(nh - 1), x2: x(nh - 1), y1: m.t, y2: HT - m.b, stroke: css("--ink-2"), "stroke-dasharray": "2 4" }, svg);
    el("text", { x: x(nh - 1) + 6, y: HT - m.b - 6, class: "axis-l" }, svg).textContent = "forecast →";
    o.lines.forEach(function (l) {
      var ax = l.axis || 0, path = function (arr, from) { var d = "", started = false; arr.forEach(function (v, j) { if (v == null) return; d += (started ? "L" : "M") + x(from + j).toFixed(1) + " " + y(v, ax).toFixed(1); started = true; }); return d; };
      if (l.band) {
        var up = l.band.hi.map(function (v, j) { return x(nh + j).toFixed(1) + "," + y(v, ax).toFixed(1); }), dn = l.band.lo.map(function (v, j) { return x(nh + j).toFixed(1) + "," + y(v, ax).toFixed(1); }).reverse();
        el("polygon", { points: x(nh - 1).toFixed(1) + "," + y(last(l.hist), ax).toFixed(1) + " " + up.join(" ") + " " + dn.join(" "), fill: l.color, "fill-opacity": ".18" }, svg);
      }
      el("path", { d: path(l.hist, 0), fill: "none", stroke: l.color, "stroke-width": 2.4, "stroke-linejoin": "round", "stroke-linecap": "round" }, svg);
      if (l.fc) el("path", { d: path([last(l.hist)].concat(l.fc), nh - 1), fill: "none", stroke: l.color, "stroke-width": 2.4, "stroke-dasharray": "6 5", "stroke-linecap": "round" }, svg);
    });
    var hg = el("g", { style: "display:none", "pointer-events": "none" }, svg), hl = el("line", { y1: m.t, y2: HT - m.b, stroke: css("--ink"), "stroke-opacity": ".6" }, hg);
    var dots = o.lines.map(function (l) { return el("circle", { r: 4.5, fill: l.color, stroke: css("--surface"), "stroke-width": 2 }, hg); });
    var cap = el("rect", { x: m.l, y: m.t, width: W - m.l - m.r, height: HT - m.t - m.b, fill: "transparent", style: "cursor:crosshair" }, svg);
    function at(e) {
      var r = svg.getBoundingClientRect(), px = (e.clientX - r.left) / r.width * W, i = Math.max(0, Math.min(nT - 1, Math.round((px - m.l) / (W - m.l - m.r) * (nT - 1))));
      hg.style.display = ""; hl.setAttribute("x1", x(i)); hl.setAttribute("x2", x(i));
      var isF = i >= nh, html = "<b>" + ml(o.T[i]) + (isF ? " (forecast)" : "") + "</b>";
      o.lines.forEach(function (l, j) {
        var v = isF ? (l.fc ? l.fc[i - nh] : null) : l.hist[i];
        if (v == null) { dots[j].style.display = "none"; return; }
        dots[j].style.display = ""; dots[j].setAttribute("cx", x(i)); dots[j].setAttribute("cy", y(v, l.axis || 0));
        var f = (o.fmtTip && o.fmtTip[j]) || fmt;
        html += "<br>" + esc(l.name) + ": " + f(v) + (isF && l.band ? " (" + f(l.band.lo[i - nh]) + " to " + f(l.band.hi[i - nh]) + ")" : "");
      });
      document.body.classList.add("tip-chart"); showTip(html, e.clientX, e.clientY);
    }
    cap.addEventListener("pointermove", at); cap.addEventListener("pointerdown", at);
    cap.addEventListener("pointerleave", function () { hg.style.display = "none"; document.body.classList.remove("tip-chart"); hideTip(); });
  }
  function chartCard(title, sub, right, id) { return '<section class="card"><div class="card-h"><div><h2>' + title + "</h2>" + (sub ? "<p>" + sub + "</p>" : "") + "</div>" + (right || "") + '</div><div id="' + id + '-lg"></div><div class="chart" id="' + id + '"></div></section>'; }
  function draw(id, o) { var host = document.getElementById(id); lineChart(host, o); document.getElementById(id + "-lg").innerHTML = legend(o.lines.map(function (l) { return { name: l.name, color: l.color }; }).concat(o.lines.some(function (l) { return l.band; }) ? [{ name: "90% range", color: o.lines[0].color, cls: "box" }] : [])); }
  function rangeToggle(p) { return '<div class="seg-row" role="group" aria-label="Time range"><button type="button" data-r="60" aria-pressed="' + (p.r !== "all") + '">Last 5 years</button><button type="button" data-r="all" aria-pressed="' + (p.r === "all") + '">Since 2011</button></div>'; }
  function bindRange(view) { $$("[data-r]", view).forEach(function (b) { b.addEventListener("click", function () { go({ r: b.dataset.r === "all" ? "all" : "" }); }); }); }
  var COV = function () { return [{ ym: D.meta.covid[0], to: D.meta.covid[1], label: "COVID" }]; };
  var regionsCovid = function () { return [{ from: D.meta.covid[0], to: D.meta.covid[1], label: "COVID period" }]; };

  /* ---------- CSV ---------- */
  function slug(s) { return String(s).toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, ""); }
  function download(name, head, rows) {
    var q = function (v) { v = v == null ? "" : String(v); return /[",\n]/.test(v) ? '"' + v.replace(/"/g, '""') + '"' : v; };
    var text = [head].concat(rows).map(function (r) { return r.map(q).join(","); }).join("\r\n") + "\r\n";
    var a = document.createElement("a"); a.href = URL.createObjectURL(new Blob([text], { type: "text/csv;charset=utf-8" })); a.download = name + ".csv"; document.body.appendChild(a); a.click();
    setTimeout(function () { URL.revokeObjectURL(a.href); a.remove(); }, 500);
    toast("Downloaded " + name + ".csv (" + fmt(rows.length) + " rows)");
  }
  function toast(t) { var n = document.createElement("div"); n.className = "toast"; n.textContent = t; document.body.appendChild(n); setTimeout(function () { n.remove(); }, 2600); }
  function fname(page) { return "lmis_" + page + "_" + slug(cur.p.sector || "all-sectors") + "_" + slug(cur.p.district ? DISTRICTS[cur.p.district].name : cur.p.state || "all-states"); }
  function rowsForecast(idx) {
    var out = [];
    idx.forEach(function (i) { ["E", "V", "S"].forEach(function (k) { for (var h = 0; h < 12; h++) out.push([S[i].id, S[i].district, S[i].state, S[i].sector, { E: "Total_Employed_Workers", V: "Active_Job_Vacancies", S: "eShram_Registered_Seekers" }[k], h + 1, FM[h], D.fc[k].f[i][h], D.fc[k].lo[i][h], D.fc[k].hi[i][h], D.fc[k].conf[i]]); }); });
    return out;
  }
  var HEAD_F = ["series_id", "district", "state", "sector", "measure", "horizon_months", "target_month", "forecast", "lo90", "hi90", "confidence"];
  function rowsFlags(idx) { var out = []; idx.forEach(function (i) { for (var h = 0; h < 12; h++) { var f = D.fl[i][h]; out.push([S[i].id, S[i].district, S[i].state, S[i].sector, h + 1, FM[h], f[6], f[0], STATUS[f[1]], CONTEXT[f[2]], STATUS[f[3]], CHANGE[f[4]], f[5] < 0 ? "" : f[5], S[i].low ? "yes" : "no"]); } }); return out; }
  var HEAD_L = ["series_id", "district", "state", "sector", "horizon_months", "target_month", "forecast_openings_per_seeker", "percentile_in_sector", "relative_status", "absolute_context", "current_status", "change", "historical_precision", "small_count_series"];
  function rowsHistory(idx) {
    var out = []; idx.forEach(function (i) { for (var m = 0; m < H; m++) out.push([S[i].id, S[i].district, S[i].state, S[i].sector, MONTHS[m], D.hist.E[i][m], D.hist.V[i][m], D.hist.S[i][m], D.hist.W[i][m], D.hist.U[i][m] / 10, D.hist.T[i][m], D.hist.C[i][m]]); });
    return out;
  }
  var HEAD_H = ["series_id", "district", "state", "sector", "month", "employed_workers", "job_vacancies", "registered_seekers", "avg_monthly_wage_inr", "unemployment_rate_pct", "training_seats_sanctioned", "trainees_certified"];

  /* ---------- warnings ---------- */
  function warnRows(idx, hz) {
    var out = [];
    idx.forEach(function (i) {
      var f = D.fl[i][hz - 1], st = f[1]; if (st !== 0 && st !== 4) return;
      var type = st === 0 ? "shortage" : "oversupply", ok = type === "shortage" ? f[2] === 0 : f[2] >= 2;
      out.push({ i: i, type: type, level: ok ? "alert" : "watch", pct: f[0], status: st, ctx: f[2], cur: f[3], chg: f[4], prec: f[5], ratio: f[6] });
    });
    out.sort(function (a, b) { return (a.level === b.level ? 0 : a.level === "alert" ? -1 : 1) || Math.abs(b.pct - 50) - Math.abs(a.pct - 50); });
    return out;
  }
  var horizonOf = function (p) { return [3, 6, 12].indexOf(+p.h) >= 0 ? +p.h : 12; };
  function hzSeg(p, key) { var h = horizonOf(p); return '<div class="seg-row" role="group" aria-label="Months ahead">' + [3, 6, 12].map(function (v) { return '<button type="button" data-hz="' + v + '" aria-pressed="' + (v === h) + '">' + v + " months</button>"; }).join("") + "</div>"; }
  function bindHz(view, key) { $$("[data-hz]", view).forEach(function (b) { b.addEventListener("click", function () { var o = {}; o[key || "h"] = b.dataset.hz; go(o); }); }); }

  /* ---------- the districts: map ---------- */
  var mapVB = null;
  function mapView(host, p) {
    var mh = [0, 3, 6, 12].indexOf(+p.mh) >= 0 ? +p.mh : 0, counts = [0, 0, 0, 0];
    host.innerHTML = '<div class="m-chips" id="m-states" role="group" aria-label="State"></div><svg id="m-svg" role="img" aria-label="Map of the 56 districts coloured by absolute context"></svg>';
    var svg = $("#m-svg", host), box = host;
    var chips = $("#m-states", host);
    [["", "All states"]].concat(STATES.map(function (s) { return [s, s]; })).forEach(function (o) { var b = document.createElement("button"); b.type = "button"; b.textContent = o[1]; b.setAttribute("aria-pressed", (p.state || "") === o[0]); b.addEventListener("click", function () { go({ state: o[0], district: "" }); }); chips.appendChild(b); });
    el("path", { d: M.backdrop, class: "mbackdrop" }, svg);
    var og = el("g", {}, svg);
    (M.others || []).forEach(function (o) { var q = el("path", { d: o.d, class: "mextra" + (p.state && p.state !== o.s ? " dim" : "") }, og); q.setAttribute("data-tip", "<b>" + esc(o.n) + "</b> · " + esc(o.s) + "<br>No forecast data for this district"); });
    var g = el("g", {}, svg), hl;
    M.districts.forEach(function (d) {
      var idx = (byCode[d.c] || []).filter(function (i) { return !p.sector || S[i].sector === p.sector; }), v = 0, s = 0;
      idx.forEach(function (i) { if (mh === 0) { v += D.hist.V[i][H - 1]; s += D.hist.S[i][H - 1]; } else { v += D.fc.V.f[i][mh - 1]; s += D.fc.S.f[i][mh - 1]; } });
      var r = s ? v / s : 0, c = ctxOf(r); counts[c]++;
      var path = el("path", { d: d.d, class: "mdist" + (p.state && p.state !== d.s ? " dim" : ""), style: "fill:var(--ctx" + c + ")", "data-code": d.c }, g);
      path.setAttribute("data-tip", "<b>" + esc(d.n) + "</b> · " + esc(d.s) + "<br>" + CTX_NAME[c] + "<br>Openings per 100 seekers: " + fmt(r * 100, 1) + "<br>Vacancies " + fmt(v) + ", seekers " + fmt(s) + (mh ? "<br>" + mh + " months ahead" : "<br>Latest month"));
      path.addEventListener("click", function () { go(p.district === d.c ? { district: "" } : { district: d.c }); });
      if (p.district === d.c) { hl = d.d; }
    });
    var hp = el("path", { class: "mhl", d: hl || "" }, svg);
    var labels = {};
    STATES.forEach(function (s) { var ds = M.districts.concat(M.others).filter(function (d) { return d.s === s; }); if (!ds.length) return; labels[s] = el("text", { class: "mstate", "data-x": ds.reduce(function (a, d) { return a + (d.bb[0] + d.bb[2]) / 2; }, 0) / ds.length, "data-y": ds.reduce(function (a, d) { return a + (d.bb[1] + d.bb[3]) / 2; }, 0) / ds.length, "data-dx": s === "Delhi" ? 16 : 0 }, svg); labels[s].textContent = s; if (p.state && p.state !== s) labels[s].style.display = "none"; });
    function target() {
      var r = box.clientWidth > 0 && box.clientHeight > 0 ? box.clientWidth / box.clientHeight : 1, b;
      if (!p.state) b = M.viewBox.slice(); else { var x0 = 1e9, y0 = 1e9, x1 = -1e9, y1 = -1e9; M.districts.concat(M.others).filter(function (d) { return d.s === p.state; }).forEach(function (d) { x0 = Math.min(x0, d.bb[0]); y0 = Math.min(y0, d.bb[1]); x1 = Math.max(x1, d.bb[2]); y1 = Math.max(y1, d.bb[3]); }); var pad = Math.max(x1 - x0, y1 - y0) * 0.14; b = [x0 - pad, y0 - pad, x1 - x0 + 2 * pad, y1 - y0 + 2 * pad]; }
      var cx = b[0] + b[2] / 2, cy = b[1] + b[3] / 2, w = b[2], h = b[3]; if (w / h < r) w = h * r; else h = w / r; return [cx - w / 2, cy - h / 2, w, h];
    }
    function setVB(vb) {
      if (!vb.every(isFinite) || vb[2] <= 0) return; mapVB = vb; svg.setAttribute("viewBox", vb.map(function (n) { return n.toFixed(1); }).join(" "));
      var k = Math.min(box.clientWidth / vb[2], box.clientHeight / vb[3]) || 1;
      Object.keys(labels).forEach(function (s) { var t = labels[s]; t.setAttribute("font-size", (12 / k).toFixed(1)); t.setAttribute("stroke-width", (3.5 / k).toFixed(1)); var dx = +t.getAttribute("data-dx"); t.setAttribute("x", (+t.getAttribute("data-x") + dx / k).toFixed(1)); t.setAttribute("y", t.getAttribute("data-y")); if (dx) t.style.textAnchor = "start"; });
    }
    var to = target(), from = mapVB || to;
    if (reduced || !mapVB) setVB(to); else { var t0 = null; (function f(ts) { if (t0 === null) t0 = ts; var q = Math.min(1, (ts - t0) / 650), e = 1 - Math.pow(1 - q, 3); setVB(from.map(function (a, i) { return a + (to[i] - a) * e; })); if (q < 1) requestAnimationFrame(f); })(performance.now()); }
    return counts;
  }
  function ctxLegend(counts) { return '<div class="ctx-legend">' + CTX_NAME.map(function (n, c) { return '<span style="--c:var(--ctx' + c + ')"><i></i>' + n + " (" + counts[c] + ")</span>"; }).join("") + '<span style="--c:var(--surface-2)"><i style="border:1px solid var(--line)"></i>No forecast data</span></div>'; }

  /* ---------- sector rows (shared by the overview table and the bar charts) ---------- */
  function sectorRows(p) {
    return SECTORS.map(function (sec) {
      var idx = sel(p, ["sector"]).filter(function (i) { return S[i].sector === sec; });
      if (!idx.length) return { sec: sec, empty: true };
      var E = sumH("E", idx), V = sumH("V", idx), Sk = sumH("S", idx), fV = sumF("V", "f", idx), fS = sumF("S", "f", idx), r0 = last(V) / last(Sk), r12 = fV[11] / fS[11];
      return { sec: sec, idx: idx, E: last(E), V: last(V), S: last(Sk), r0: r0, r12: r12, ctx: ctxOf(r0), dV: (fV[11] / last(V) - 1) * 100, dS: (fS[11] / last(Sk) - 1) * 100, conf: confOf("S", idx) };
    });
  }
  function sectorBars(rows, p) {
    var max = Math.max.apply(null, rows.filter(function (r) { return !r.empty; }).map(function (r) { return Math.max(r.r0, r.r12); })) * 1.1 || 1;
    return '<div class="bars">' + rows.map(function (r) {
      if (r.empty) return "";
      return '<div class="bar-row' + (p.sector === r.sec ? " on" : "") + '" data-sec="' + esc(r.sec) + '" data-tip="<b>' + esc(r.sec) + "</b><br>" + CTX_NAME[r.ctx] + "<br>Now: " + fmt(r.r0 * 100, 1) + " openings per 100 seekers<br>In 12 months: " + fmt(r.r12 * 100, 1) + '"><span>' + esc(r.sec) + '</span><span class="tr"><span class="fi" style="width:' + (r.r0 / max * 100).toFixed(1) + "%;--c:var(--ctx" + r.ctx + ')"></span><span class="tk" style="left:' + (r.r12 / max * 100).toFixed(1) + '%"></span></span><b>' + fmt(r.r0 * 100, 1) + "</b></div>";
    }).join("") + '</div><p class="note">Openings per 100 registered seekers, latest month. The dark tick marks the forecast for twelve months ahead.</p>';
  }
  function bindBars(view, p) { $$(".bar-row", view).forEach(function (b) { b.addEventListener("click", function () { go({ sector: p.sector === b.dataset.sec ? "" : b.dataset.sec }); }); }); }

  /* ---------- pages ---------- */
  var render = {};

  render.overview = function (p, view) {
    var idx = sel(p), E = sumH("E", idx), V = sumH("V", idx), Sk = sumH("S", idx), fE = sumF("E", "f", idx), fV = sumF("V", "f", idx), fS = sumF("S", "f", idx);
    var r0 = last(V) / last(Sk), r12 = fV[11] / fS[11];
    var kpi = function (lbl, color, val, dv, k) { return '<div class="card kpi" style="--c:' + color + '"><div class="lbl"><i></i>' + lbl + '</div><span class="val">' + val + '</span><div class="sub">' + dv + (k ? " " + confChip(confOf(k, idx)) : "") + "</div></div>"; };
    var w = warnRows(idx, 12), cnt = function (t, l) { return w.filter(function (r) { return r.type === t && r.level === l; }).length; };
    var tile = function (t, l, lbl) { return '<a class="ew-tile' + (l === "alert" ? " a" : "") + '" href="' + url("warnings", { t: t, lv: l, h: 12 }) + '"><span>' + lbl + "</span><b>" + cnt(t, l) + "</b><span>series at 12 months</span></a>"; };
    var rows = sectorRows(p), top = w.filter(function (r) { return r.level === "alert"; }).slice(0, 5);
    view.innerHTML = '<div class="grid g4">' +
      kpi("Employed workers", "var(--employed)", compact(last(E)), deltaHtml((fE[11] / last(E) - 1) * 100, "in 12 months"), "E") +
      kpi("Job vacancies", "var(--demand)", compact(last(V)), deltaHtml((fV[11] / last(V) - 1) * 100, "in 12 months"), "V") +
      kpi("Registered job seekers", "var(--supply)", compact(last(Sk)), deltaHtml((fS[11] / last(Sk) - 1) * 100, "in 12 months"), "S") +
      kpi("Openings per 100 seekers", "var(--ctx" + ctxOf(r0) + ")", fmt(r0 * 100, 1), '<span class="pill c' + ctxOf(r0) + '">' + CTX_NAME[ctxOf(r0)] + "</span> <span>" + fmt(r12 * 100, 1) + " in 12 months</span>", null) + "</div>" +
      '<div class="grid g-map mt"><section class="card"><div class="card-h"><div><h2>District map</h2><p>Coloured by absolute context. Click a district to filter every page.</p></div>' +
      '<div class="seg-row" role="group" aria-label="Map month">' + [[0, "Latest"], [3, "+3 months"], [6, "+6"], [12, "+12"]].map(function (o) { return '<button type="button" data-mh="' + o[0] + '" aria-pressed="' + (o[0] === ([0, 3, 6, 12].indexOf(+p.mh) >= 0 ? +p.mh : 0)) + '">' + o[1] + "</button>"; }).join("") + '</div></div><div class="mapbox" id="mapbox"></div><div id="m-leg"></div></section>' +
      '<div class="grid"><section class="card"><div class="card-h"><div><h2>Openings vs seekers</h2><p>' + esc(scopeText(p)) + "</p></div>" + rangeToggle(p) + '</div><div id="c-ovs-lg"></div><div class="chart" id="c-ovs"></div></section>' +
      '<section class="card"><div class="card-h"><div><h2>Early-warning summary</h2><p>Forecast flags twelve months ahead for ' + esc(scopeText(p)) + '</p></div><a class="chip-btn" href="' + url("warnings", {}) + '">Open</a></div><div class="ew-tiles">' + tile("shortage", "alert", "Shortage alerts") + tile("shortage", "watch", "Shortage watch") + tile("oversupply", "alert", "Oversupply alerts") + tile("oversupply", "watch", "Oversupply watch") + "</div>" +
      '<ul class="list">' + (top.length ? top.map(function (r) { return "<li><span>" + esc(S[r.i].district) + " · " + esc(S[r.i].sector) + "</span><small>" + r.type + "</small></li>"; }).join("") : "<li><span>No alerts in this view.</span></li>") + "</ul></section></div></div>" +
      '<div class="grid g2 mt"><section class="card"><div class="card-h"><div><h2>Coverage by sector</h2><p>Selected state and district; click a bar to filter the sector</p></div></div>' + sectorBars(rows, p) + "</section>" +
      '<section class="card"><div class="card-h"><div><h2>Sector table</h2><p>Latest month and the twelve-month forecast</p></div></div><div class="tbl-wrap"><table class="tbl"><thead><tr><th>Sector</th><th class="num">Employed</th><th class="num">Vacancies</th><th class="num">Seekers</th><th class="num">Per 100</th><th>Context</th><th class="num">Vac. 12m</th><th class="num">Seek. 12m</th></tr></thead><tbody>' +
      rows.map(function (r) { return r.empty ? "" : '<tr class="click' + (p.sector === r.sec ? " on" : "") + '" data-sec="' + esc(r.sec) + '"><td>' + esc(r.sec) + '</td><td class="num">' + compact(r.E) + '</td><td class="num">' + compact(r.V) + '</td><td class="num">' + compact(r.S) + '</td><td class="num">' + fmt(r.r0 * 100, 1) + '</td><td><span class="pill c' + r.ctx + '">' + CTX_NAME[r.ctx] + '</span></td><td class="num">' + pct(r.dV) + '</td><td class="num">' + pct(r.dS) + "</td></tr>"; }).join("") + "</tbody></table></div></section></div>";
    var counts = mapView($("#mapbox", view), p); $("#m-leg", view).innerHTML = ctxLegend(counts);
    $$("[data-mh]", view).forEach(function (b) { b.addEventListener("click", function () { go({ mh: b.dataset.mh === "0" ? "" : b.dataset.mh }); }); });
    var tl = timeline(p), fl = idx.length === 1 ? idx[0] : -1;
    draw("c-ovs", { T: tl.T, nh: tl.nh, label: "Vacancies and registered seekers, history and forecast", axisColors: [css("--demand"), css("--supply")], lines: [
      { name: "Job vacancies (left)", color: css("--demand"), hist: V.slice(tl.start), fc: fV, axis: 0, band: fl >= 0 ? { lo: D.fc.V.lo[fl], hi: D.fc.V.hi[fl] } : null },
      { name: "Registered seekers (right)", color: css("--supply"), hist: Sk.slice(tl.start), fc: fS, axis: 1, band: fl >= 0 ? { lo: D.fc.S.lo[fl], hi: D.fc.S.hi[fl] } : null }], regions: regionsCovid(), marks: [{ ym: D.meta.eshram.launch, label: "e-Shram" }], height: 300 });
    bindRange(view); bindBars(view, p);
    $$("tr.click", view).forEach(function (tr) { tr.addEventListener("click", function () { go({ sector: p.sector === tr.dataset.sec ? "" : tr.dataset.sec }); }); });
    cur.csv = function () { return { name: fname("overview"), head: ["sector", "employed_workers", "job_vacancies", "registered_seekers", "openings_per_100_seekers", "absolute_context", "vacancies_change_12m_pct", "seekers_change_12m_pct", "openings_per_100_seekers_12m"], rows: rows.filter(function (r) { return !r.empty; }).map(function (r) { return [r.sec, r.E, r.V, r.S, (r.r0 * 100).toFixed(2), CTX_NAME[r.ctx], r.dV.toFixed(2), r.dS.toFixed(2), (r.r12 * 100).toFixed(2)]; }) }; };
  };

  function seriesCsv(page, idx, tl, cols) {
    return function () {
      var T = MONTHS.concat(FM), rows = T.map(function (m, i) { return [m, i < H ? "history" : "forecast"].concat(cols.map(function (c) { return c.v[i] == null ? "" : +(+c.v[i]).toFixed(c.d == null ? 2 : c.d); })); });
      return { name: fname(page), head: ["month", "type"].concat(cols.map(function (c) { return c.n; })), rows: rows };
    };
  }
  var full = function (hist, fc) { return hist.concat(fc || new Array(12).fill(null)); };

  render.demand = function (p, view) {
    var idx = sel(p), E = sumH("E", idx), V = sumH("V", idx), W = wavg("W", idx), U = wavg("U", idx), fE = sumF("E", "f", idx), fV = sumF("V", "f", idx), tl = timeline(p), one = idx.length === 1 ? idx[0] : -1;
    var info = function (a, f, k) { return '<div class="sub">' + deltaHtml((f[11] / last(a) - 1) * 100, "in 12 months") + " " + confChip(confOf(k, idx)) + "</div>"; };
    view.innerHTML = '<div class="card-h"><div><h2 style="font-size:1.05rem">' + esc(scopeText(p)) + '</h2></div>' + rangeToggle(p) + "</div>" + (one < 0 ? '<p class="note" style="margin:-4px 0 12px">The 90% range appears when one district and one sector are selected; sums over several series would overstate it.</p>' : "") +
      '<div class="grid g2">' + chartCard("Employed workers", "Latest " + compact(last(E)), info(E, fE, "E"), "c-e") + chartCard("Job vacancies", "Latest " + compact(last(V)), info(V, fV, "V"), "c-v") +
      chartCard("Average monthly wage", "Employment-weighted, rupees. Latest " + fmt(last(W)), "", "c-w") + chartCard("Unemployment rate", "Employment-weighted, per cent. Latest " + fmt(last(U), 1) + "%", "", "c-u") + "</div>" +
      '<p class="note">Wage and unemployment are history only; the forecast engine does not project them.</p>';
    var base = { T: tl.T, nh: tl.nh, regions: regionsCovid() };
    draw("c-e", Object.assign({ label: "Employed workers", lines: [{ name: "Employed workers", color: css("--employed"), hist: E.slice(tl.start), fc: fE, band: one >= 0 ? { lo: D.fc.E.lo[one], hi: D.fc.E.hi[one] } : null }] }, base));
    draw("c-v", Object.assign({ label: "Job vacancies", lines: [{ name: "Job vacancies", color: css("--demand"), hist: V.slice(tl.start), fc: fV, band: one >= 0 ? { lo: D.fc.V.lo[one], hi: D.fc.V.hi[one] } : null }] }, base));
    draw("c-w", Object.assign({ label: "Average wage", fmtAxis: [compact], lines: [{ name: "Average monthly wage", color: css("--supply"), hist: W.slice(tl.start), fc: null }] }, base));
    draw("c-u", Object.assign({ label: "Unemployment rate", fmtAxis: [function (v) { return v.toFixed(1) + "%"; }], fmtTip: [function (v) { return v.toFixed(1) + "%"; }], lines: [{ name: "Unemployment rate", color: css("--low"), hist: U.slice(tl.start), fc: null }] }, base));
    bindRange(view);
    cur.csv = seriesCsv("demand", idx, tl, [{ n: "employed_workers", v: full(E, fE), d: 0 }, { n: "job_vacancies", v: full(V, fV), d: 0 }, { n: "avg_monthly_wage_inr", v: full(W), d: 0 }, { n: "unemployment_rate_pct", v: full(U), d: 2 }]);
  };

  render.supply = function (p, view) {
    var idx = sel(p), Sk = sumH("S", idx), fS = sumF("S", "f", idx), T = sumH("T", idx), C = sumH("C", idx), C12 = roll12(C), tl = timeline(p), one = idx.length === 1 ? idx[0] : -1;
    var util = last(T) ? last(C12) / last(T) * 100 : 0;
    var kpi = function (l, v, s, c) { return '<div class="card kpi" style="--c:' + c + '"><div class="lbl"><i></i>' + l + '</div><span class="val">' + v + '</span><div class="sub">' + s + "</div></div>"; };
    view.innerHTML = '<div class="card-h"><div><h2 style="font-size:1.05rem">' + esc(scopeText(p)) + "</h2></div>" + rangeToggle(p) + "</div>" +
      '<div class="grid g4">' + kpi("Registered seekers", compact(last(Sk)), deltaHtml((fS[11] / last(Sk) - 1) * 100, "in 12 months") + " " + confChip(confOf("S", idx)), "var(--supply)") + kpi("Training seats sanctioned", compact(last(T)), "Annual capacity, latest month", "var(--demand)") + kpi("Certified, last 12 months", compact(last(C12)), "People who completed training", "var(--employed)") + kpi("Certified per seat", fmt(util, 0) + "%", "Last 12 months against seats", "var(--ctx1)") + "</div>" +
      '<div class="grid g2 mt">' + chartCard("Registered job seekers", "The e-Shram registry launched in August 2021; the rise that follows is a break in the series, not a labour-market change.", confChip(confOf("S", idx)), "c-s") +
      chartCard("Training seats and certified trainees", "Seats are annual capacity; certified trainees are summed over the last 12 months.", "", "c-t") + "</div>" + (one < 0 ? '<p class="note">The 90% range appears when one district and one sector are selected.</p>' : "");
    var base = { T: tl.T, nh: tl.nh };
    draw("c-s", Object.assign({ label: "Registered job seekers with the e-Shram break marked", lines: [{ name: "Registered seekers", color: css("--supply"), hist: Sk.slice(tl.start), fc: fS, band: one >= 0 ? { lo: D.fc.S.lo[one], hi: D.fc.S.hi[one] } : null }],
      regions: [{ from: D.meta.eshram.ramp[0], to: D.meta.eshram.ramp[1], label: "e-Shram ramp", color: css("--supply") }], marks: [{ ym: D.meta.eshram.launch, label: "e-Shram launch" }] }, base));
    draw("c-t", Object.assign({ label: "Training seats and certified trainees", lines: [{ name: "Seats sanctioned", color: css("--demand"), hist: T.slice(tl.start), fc: null }, { name: "Certified, last 12 months", color: css("--employed"), hist: C12.slice(tl.start), fc: null }], regions: regionsCovid() }, base));
    bindRange(view);
    cur.csv = seriesCsv("supply", idx, tl, [{ n: "registered_seekers", v: full(Sk, fS), d: 0 }, { n: "training_seats_sanctioned", v: full(T), d: 0 }, { n: "certified_trainees_monthly", v: full(C), d: 0 }, { n: "certified_last_12_months", v: full(C12), d: 0 }]);
  };

  render.gap = function (p, view) {
    var idx = sel(p), V = sumH("V", idx), Sk = sumH("S", idx), fV = sumF("V", "f", idx), fS = sumF("S", "f", idx), tl = timeline(p), rows = sectorRows(p);
    var cov = div(V, Sk).map(function (v) { return v * 100; }), fcov = div(fV, fS).map(function (v) { return v * 100; }), gap = V.map(function (v, i) { return v - Sk[i]; }), fgap = fV.map(function (v, i) { return v - fS[i]; });
    view.innerHTML = '<div class="card-h"><div><h2 style="font-size:1.05rem">' + esc(scopeText(p)) + '</h2></div>' + rangeToggle(p) + "</div>" +
      '<div class="grid g2">' + chartCard("Coverage: openings per 100 seekers", "Vacancies divided by registered seekers. Above 100 openings exceed seekers.", confChip("low"), "c-cov") + chartCard("Net gap: vacancies minus seekers", "Below zero there are more seekers than openings.", confChip("low"), "c-gap") + "</div>" +
      '<section class="card mt"><div class="card-h"><div><h2>Coverage by sector</h2><p>Selected state and district; click a bar to filter the sector</p></div></div>' + sectorBars(rows, p) + "</section>" +
      '<p class="note">Coverage and the gap rest on the vacancy forecast, which adds little over a simple baseline, so they carry low confidence.</p>';
    var base = { T: tl.T, nh: tl.nh, regions: regionsCovid() };
    draw("c-cov", Object.assign({ label: "Coverage over time", fmtAxis: [function (v) { return fmt(v, v < 10 ? 1 : 0); }], fmtTip: [function (v) { return fmt(v, 1); }], lines: [{ name: "Openings per 100 seekers", color: css("--demand"), hist: cov.slice(tl.start), fc: fcov }],
      hlines: [{ v: 10, label: "10: deep surplus below", color: css("--ctx3") }, { v: 20, label: "20: moderate above", color: css("--ctx1") }] }, base));
    draw("c-gap", Object.assign({ label: "Net gap over time", fmtTip: [function (v) { return fmt(v); }], lines: [{ name: "Vacancies minus seekers", color: css("--supply"), hist: gap.slice(tl.start), fc: fgap }], hlines: [{ v: 0, label: "zero", color: css("--ink") }] }, base));
    bindRange(view); bindBars(view, p);
    cur.csv = seriesCsv("gap", idx, tl, [{ n: "job_vacancies", v: full(V, fV), d: 0 }, { n: "registered_seekers", v: full(Sk, fS), d: 0 }, { n: "openings_per_100_seekers", v: full(cov, fcov), d: 2 }, { n: "net_gap", v: full(gap, fgap), d: 0 }]);
  };

  render.ranking = function (p, view) {
    var sector = p.sector || SECTORS[0], hz = horizonOf(p), order = p.o || "rank";
    var rows = S.map(function (s, i) { return i; }).filter(function (i) { return S[i].sector === sector; }).map(function (i) { var f = D.fl[i][hz - 1]; return { i: i, pct: f[0], st: f[1], ctx: f[2], cur: f[3], chg: f[4], prec: f[5], ratio: f[6] }; });
    rows.sort(function (a, b) { return b.pct - a.pct; }); rows.forEach(function (r, k) { r.rank = k + 1; });
    var shown = rows.filter(function (r) { return (!p.state || S[r.i].state === p.state) && (!p.district || S[r.i].code === p.district); });
    if (order === "name") shown.sort(function (a, b) { return S[a.i].district < S[b.i].district ? -1 : 1; }); else if (order === "ratio") shown.sort(function (a, b) { return b.ratio - a.ratio; });
    var th = function (key, label, cls) { return '<th class="' + (cls || "") + '"><button type="button" data-o="' + key + '">' + label + (order === key ? " ▾" : "") + "</button></th>"; };
    view.innerHTML = (p.sector ? "" : '<div class="banner">Ranking is within one sector. Showing ' + esc(sector) + "; choose another in the Sector filter.</div>") +
      '<section class="card"><div class="card-h"><div><h2>' + esc(sector) + ": " + rows.length + ' districts ranked</h2><p>Rank 1 has the most openings per seeker in the sector, ' + hz + " months ahead. Greyed rows are small-count series.</p></div>" + hzSeg(p) + '</div><div class="tbl-wrap"><table class="tbl"><thead><tr>' + th("rank", "Rank", "num") + th("name", "District") + "<th>State</th><th>Relative status</th><th>Absolute context</th>" + th("ratio", "Per 100 seekers", "num") + "<th>Today</th><th>Change</th><th class=\"num\">Flag precision</th></tr></thead><tbody>" +
      shown.map(function (r) { var s = S[r.i]; return '<tr class="click' + (s.low ? " grey" : "") + (p.district === s.code ? " on" : "") + '" data-code="' + s.code + '"><td class="num">' + r.rank + "</td><td>" + esc(s.district) + (s.low ? ' <small title="Very small counts">small count</small>' : "") + "</td><td>" + esc(s.state) + '</td><td><span class="pill s' + r.st + '">' + STATUS[r.st] + " · " + fmt(r.pct, 0) + '</span></td><td><span class="pill c' + r.ctx + '">' + CTX_NAME[r.ctx] + '</span></td><td class="num">' + fmt(r.ratio * 100, 1) + "</td><td>" + STATUS[r.cur] + "</td><td>" + (r.chg ? CHANGE[r.chg] : "no change") + '</td><td class="num">' + (r.prec < 0 ? "–" : fmt(r.prec * 100, 0) + "%") + "</td></tr>"; }).join("") + "</tbody></table></div>" +
      '<p class="note">Relative status compares a district with the others in its sector in the same month; the absolute context says whether openings really exceed seekers. Both are shown together on purpose: the tightest districts of a sector can still be in surplus.</p></section>';
    bindHz(view); $$("[data-o]", view).forEach(function (b) { b.addEventListener("click", function () { go({ o: b.dataset.o === "rank" ? "" : b.dataset.o }); }); });
    $$("tr.click", view).forEach(function (tr) { tr.addEventListener("click", function () { go({ district: p.district === tr.dataset.code ? "" : tr.dataset.code, sector: sector }); }); });
    cur.csv = function () { return { name: fname("ranking") + "_" + hz + "m", head: ["rank", "district", "state", "sector", "horizon_months", "percentile_in_sector", "relative_status", "absolute_context", "forecast_openings_per_100_seekers", "current_status", "change", "historical_precision", "small_count_series"], rows: shown.map(function (r) { var s = S[r.i]; return [r.rank, s.district, s.state, sector, hz, r.pct, STATUS[r.st], CONTEXT[r.ctx], (r.ratio * 100).toFixed(2), STATUS[r.cur], CHANGE[r.chg], r.prec < 0 ? "" : r.prec, s.low ? "yes" : "no"]; }) }; };
  };

  render.warnings = function (p, view) {
    var idx = sel(p), hz = horizonOf(p), all = warnRows(idx, hz), t = p.t || "", lv = p.lv || "";
    var n = function (ty, l) { return all.filter(function (r) { return r.type === ty && r.level === l; }).length; };
    var rows = all.filter(function (r) { return (!t || r.type === t) && (!lv || r.level === lv); });
    var seg = function (key, opts, curv) { return '<div class="seg-row" role="group">' + opts.map(function (o) { return '<button type="button" data-k="' + key + '" data-v="' + o[0] + '" aria-pressed="' + (o[0] === curv) + '">' + o[1] + "</button>"; }).join("") + "</div>"; };
    view.innerHTML = '<div class="grid g4"><div class="card kpi" style="--c:var(--demand)"><div class="lbl"><i></i>Shortage alerts</div><span class="val">' + n("shortage", "alert") + '</span><div class="sub">Tightest tenth and openings exceed seekers</div></div>' +
      '<div class="card kpi" style="--c:var(--ctx1)"><div class="lbl"><i></i>Shortage watch</div><span class="val">' + n("shortage", "watch") + '</span><div class="sub">Tightest tenth, but still in surplus</div></div>' +
      '<div class="card kpi" style="--c:var(--low)"><div class="lbl"><i></i>Oversupply alerts</div><span class="val">' + n("oversupply", "alert") + '</span><div class="sub">Loosest tenth and oversupplied</div></div>' +
      '<div class="card kpi" style="--c:var(--supply)"><div class="lbl"><i></i>Oversupply watch</div><span class="val">' + n("oversupply", "watch") + '</span><div class="sub">Loosest tenth, but not oversupplied</div></div></div>' +
      '<section class="card mt"><div class="card-h"><div><h2>' + rows.length + " flagged series</h2><p>For " + esc(scopeText(p)) + ", " + hz + ' months ahead. All flags carry low confidence; the precision column shows how often such flags were right in testing.</p></div><div style="display:flex;gap:8px;flex-wrap:wrap">' + hzSeg(p) + seg("t", [["", "Both"], ["shortage", "Shortage"], ["oversupply", "Oversupply"]], t) + seg("lv", [["", "All levels"], ["alert", "Alert"], ["watch", "Watch"]], lv) + "</div></div>" +
      '<div class="tbl-wrap"><table class="tbl"><thead><tr><th>Flag</th><th>District</th><th>State</th><th>Sector</th><th>Relative status</th><th>Absolute context</th><th class="num">Per 100 seekers</th><th>Change</th><th class="num">Precision</th></tr></thead><tbody>' +
      (rows.length ? rows.map(function (r) { var s = S[r.i]; return '<tr class="click' + (s.low ? " grey" : "") + '" data-code="' + s.code + '" data-sec="' + esc(s.sector) + '"><td><span class="pill ' + r.level + '">' + r.type + " " + r.level + "</span></td><td>" + esc(s.district) + "</td><td>" + esc(s.state) + "</td><td>" + esc(s.sector) + '</td><td><span class="pill s' + r.status + '">' + STATUS[r.status] + " · " + fmt(r.pct, 0) + '</span></td><td><span class="pill c' + r.ctx + '">' + CTX_NAME[r.ctx] + '</span></td><td class="num">' + fmt(r.ratio * 100, 1) + "</td><td>" + (r.chg ? CHANGE[r.chg] : "no change") + '</td><td class="num">' + (r.prec < 0 ? "–" : fmt(r.prec * 100, 0) + "%") + "</td></tr>"; }).join("") : '<tr><td colspan="9">No flags for this selection.</td></tr>') + "</tbody></table></div>" +
      '<p class="note"><b>Alert</b>: in the tightest tenth with openings exceeding seekers (shortage), or in the loosest tenth and oversupplied or in deep surplus (oversupply). <b>Watch</b>: in the tightest or loosest tenth of its sector, but the absolute context does not agree. Flags come from the forecast and are the weakest part of the model.</p></section>';
    bindHz(view); $$("[data-k]", view).forEach(function (b) { b.addEventListener("click", function () { var o = {}; o[b.dataset.k] = b.dataset.v; go(o); }); });
    $$("tr.click", view).forEach(function (tr) { tr.addEventListener("click", function () { go({ district: tr.dataset.code, sector: tr.dataset.sec }, "demand"); }); });
    cur.csv = function () { return { name: fname("warnings") + "_" + hz + "m", head: ["flag", "level", "district", "state", "sector", "horizon_months", "percentile_in_sector", "relative_status", "absolute_context", "forecast_openings_per_100_seekers", "change", "historical_precision", "small_count_series"], rows: rows.map(function (r) { var s = S[r.i]; return [r.type, r.level, s.district, s.state, s.sector, hz, r.pct, STATUS[r.status], CONTEXT[r.ctx], (r.ratio * 100).toFixed(2), CHANGE[r.chg], r.prec < 0 ? "" : r.prec, s.low ? "yes" : "no"]; }) }; };
  };

  render.data = function (p, view) {
    var idx = sel(p), dset = {}; idx.forEach(function (i) { dset[S[i].code] = 1; });
    var st = STATES.map(function (s) { var ds = {}; S.forEach(function (x) { if (x.state === s) ds[x.code] = 1; }); return [s, Object.keys(ds).length]; });
    view.innerHTML = '<div class="grid g2"><section class="card"><div class="card-h"><div><h2>Coverage</h2><p>Current filters and the whole dataset</p></div></div><div class="tbl-wrap"><table class="tbl"><tbody>' +
      [["Series in this view", fmt(idx.length) + " of " + S.length], ["Districts in this view", Object.keys(dset).length + " of 56"], ["Sectors", SECTORS.join(", ")], ["States", st.map(function (x) { return x[0] + " (" + x[1] + ")"; }).join(", ")], ["History", ml(MONTHS[0]) + " to " + ml(last(MONTHS)) + " (" + H + " months)"], ["Forecast", ml(FM[0]) + " to " + ml(last(FM)) + " (12 months, made from " + D.meta.origin_label + ")"], ["Forecast rows", fmt(D.meta.forecast_rows) + " (280 series, 3 measures, 12 horizons)"], ["Flag rows", fmt(D.meta.flag_rows)], ["Economic tiers", D.meta.tiers], ["Model", D.meta.model]].map(function (r) { return "<tr><td><b>" + r[0] + "</b></td><td>" + esc(r[1]) + "</td></tr>"; }).join("") + "</tbody></table></div></section>" +
      '<section class="card"><div class="card-h"><div><h2>Caveats</h2></div></div><ul class="plain"><li><b>The data is simulated.</b> It behaves like official statistics but describes no real district.</li><li><b>Vacancy forecasts are low confidence.</b> In testing they beat a simple baseline by only 2 to 4%.</li><li><b>Early-warning flags are low confidence.</b> They are a little better than repeating today\'s flag.</li><li><b>Job seekers have a break</b> at the e-Shram launch in August 2021; the ramp to early 2023 is registration, not labour demand.</li><li><b>COVID</b> (March 2020 to February 2022) distorts the history and is shaded on the charts.</li><li><b>Four series have very small counts</b> (for example New Delhi construction); they are greyed in tables.</li><li><b>IT-ITeS</b> forecasts for seekers carry low confidence.</li><li><b>Only 5 of West Bengal\'s 23 and 4 of Tamil Nadu\'s 38 districts</b> are forecast.</li></ul></section></div>' +
      '<section class="card mt"><div class="card-h"><div><h2>Definitions</h2></div></div><dl class="defs"><dt>Coverage</dt><dd>Job vacancies divided by registered job seekers. The charts show it as openings per 100 seekers.</dd><dt>Net gap</dt><dd>Vacancies minus registered seekers. Negative means more seekers than openings.</dd><dt>Absolute context</dt><dd>From coverage: openings exceed seekers (100 or more per 100), moderate (20 to 100), oversupplied (10 to 20) and deep surplus (under 10).</dd><dt>Relative status</dt><dd>A district\'s coverage percentile among the 56 districts of its sector in the same month: tightest tenth, tight, typical, loose, loosest tenth.</dd><dt>Alert and watch</dt><dd>Alert: an extreme tenth whose absolute context agrees. Watch: an extreme tenth whose absolute context does not.</dd><dt>90% range</dt><dd>The range that held about nine in ten outcomes in testing. Shown for a single district and sector.</dd><dt>Confidence</dt><dd>High for employed workers, medium for job seekers, low for vacancies, flags and IT-ITeS seekers, earned in testing.</dd><dt>WAPE</dt><dd>Weighted absolute percentage error: the size of the misses divided by the size of the actual values.</dd></dl></section>' +
      '<section class="card mt"><div class="card-h"><div><h2>Downloads</h2><p>CSV files for the current filters (' + esc(scopeText(p)) + ")</p></div></div><div class=\"dl-row\"><button class=\"chip-btn primary\" style=\"margin-left:0\" data-dl=\"f\">Forecasts</button><button class=\"chip-btn primary\" style=\"margin-left:0\" data-dl=\"l\">Flags</button><button class=\"chip-btn primary\" style=\"margin-left:0\" data-dl=\"h\">History</button></div></section>";
    $$("[data-dl]", view).forEach(function (b) { b.addEventListener("click", function () { var k = b.dataset.dl; if (k === "f") download(fname("forecasts"), HEAD_F, rowsForecast(idx)); else if (k === "l") download(fname("flags"), HEAD_L, rowsFlags(idx)); else download(fname("history"), HEAD_H, rowsHistory(idx)); }); });
    cur.csv = function () { return { name: fname("forecasts"), head: HEAD_F, rows: rowsForecast(idx) }; };
  };

  /* ---------- frame: filters, sidebar, router ---------- */
  function renderFilters(p) {
    var fs = $("#f-sector"), fa = $("#f-state"), fd = $("#f-district");
    fs.innerHTML = '<option value="">All sectors</option>' + SECTORS.map(function (s) { return '<option value="' + esc(s) + '">' + esc(s) + "</option>"; }).join(""); fs.value = p.sector || "";
    fa.innerHTML = '<option value="">All states</option>' + STATES.map(function (s) { return '<option value="' + esc(s) + '">' + esc(s) + "</option>"; }).join(""); fa.value = p.state || "";
    fd.innerHTML = '<option value="">All districts</option>' + DLIST.filter(function (d) { return !p.state || d.state === p.state; }).map(function (d) { return '<option value="' + d.code + '">' + esc(d.name) + (p.state ? "" : " (" + d.state + ")") + "</option>"; }).join(""); fd.value = p.district || "";
  }
  function route() {
    var r = parse(); cur.page = r.page; cur.p = r.p; cur.csv = null;
    var meta = PAGES[r.page]; $("#page-title").textContent = meta[0]; $("#page-sub").textContent = meta[1]; document.title = meta[0] + " | LMIS India Dashboard";
    $$("#nav a").forEach(function (a) { a.setAttribute("aria-current", a.dataset.page === r.page ? "page" : "false"); a.href = url(a.dataset.page, {}); });
    renderFilters(r.p);
    var view = $("#view"); hideTip();
    try { render[r.page](r.p, view); } catch (e) { view.innerHTML = '<div class="banner">This page could not be drawn: ' + esc(e.message) + "</div>"; if (window.console) console.error(e); }
    $("#main").scrollTop = 0; document.body.classList.remove("sb-open"); $("#scrim").hidden = true;
  }
  function init() {
    $("#tb-origin").textContent = "Forecast from " + D.meta.origin_label; $("#foot-origin").textContent = D.meta.origin_label;
    ["sector", "state", "district"].forEach(function (k) { $("#f-" + k).addEventListener("change", function (e) { var o = {}; o[k] = e.target.value; if (k === "state") o.district = ""; go(o); }); });
    $("#f-reset").addEventListener("click", function () { go({ sector: "", state: "", district: "" }); });
    $("#f-csv").addEventListener("click", function () { if (!cur.csv) return; var c = cur.csv(); download(c.name, c.head, c.rows); });
    var tog = $("#sb-toggle"), small = function () { return window.matchMedia("(max-width: 900px)").matches; };
    tog.addEventListener("click", function () {
      if (small()) { var o = document.body.classList.toggle("sb-open"); $("#scrim").hidden = !o; tog.setAttribute("aria-expanded", o); return; }
      var c = root.classList.toggle("sb-collapsed"); tog.setAttribute("aria-expanded", !c); tog.setAttribute("aria-label", c ? "Expand the menu" : "Collapse the menu");
      try { var d = JSON.parse(localStorage.getItem("lmis-dash") || "{}"); d.collapsed = c; localStorage.setItem("lmis-dash", JSON.stringify(d)); } catch (e) { /* the choice lasts for this visit */ }
      setTimeout(function () { window.dispatchEvent(new Event("resize")); }, 320);
    });
    $("#scrim").addEventListener("click", function () { document.body.classList.remove("sb-open"); $("#scrim").hidden = true; });
    $("#theme-toggle").addEventListener("click", function () {
      var t = root.dataset.theme === "dark" ? "light" : "dark"; root.dataset.theme = t;
      try { var s = JSON.parse(localStorage.getItem("lmis-display") || "{}"); s.theme = t; localStorage.setItem("lmis-display", JSON.stringify(s)); } catch (e) { /* ignore */ }
      route();
    });
    if (root.classList.contains("sb-collapsed")) { tog.setAttribute("aria-expanded", "false"); tog.setAttribute("aria-label", "Expand the menu"); }
    var rz; window.addEventListener("resize", function () { clearTimeout(rz); rz = setTimeout(function () { if (cur.page === "overview" && !document.hidden) route(); }, 220); });
    window.addEventListener("hashchange", route);
    route();
  }
  init();
})();
