/* KaushalSetu assistant: one floating chat window for the public site and the dashboard.
   The site's own engine (LmisChat.answer) answers from what is already on the page: on the dashboard from window.DASH4 (the dashboard's core data and alerts: forecasts,
   ranges, Demand Index, capacity gap and flags), on the public site from window.SITE_DATA, window.MAP_DATA and the page text. When the server has a Gemini key (GET api/chat says enabled), the window
   also sends the question and a text summary of those same facts (LmisChat.facts) to api/chat, and Gemini words the answer from them. The key lives on the
   server only. If the server, the key or the network is missing, the engine's own answer is shown instead. The engine has no DOM code, so it runs under node. */
(function (root) {
  "use strict";
  var IS_DASH = function () { return !!root.DASH4; };
  var AI = { enabled: false, on: true, model: "" };                   // set from GET api/chat; "on" is the visitor's own switch
  var aiOn = function () { return AI.enabled && AI.on; };

  /* ---------- text helpers ---------- */
  var norm = function (s) { return " " + String(s).toLowerCase().replace(/[^a-z0-9\-% ]+/g, " ").replace(/\s+/g, " ").trim() + " "; };
  var any = function (q, list) { return list.some(function (w) { return q.indexOf(w.charAt(0) === "=" ? " " + w.slice(1) + " " : " " + w) >= 0; }); };  // "=it" matches the whole word only
  var fmt = function (n, d) { return Number(n).toLocaleString("en-IN", { minimumFractionDigits: d || 0, maximumFractionDigits: d || 0 }); };
  var compact = function (n) { var a = Math.abs(n), s = n < 0 ? "-" : ""; return a >= 1e7 ? s + (a / 1e7).toFixed(2) + " Cr" : a >= 1e5 ? s + (a / 1e5).toFixed(2) + " L" : a >= 1e3 ? s + (a / 1e3).toFixed(1) + "K" : s + Math.round(a); };
  var signed = function (v) { return (v > 0.05 ? "+" : v < -0.05 ? "-" : "") + Math.abs(v).toFixed(1) + "%"; };
  var ord = function (n) { var k = Math.round(n), t = k % 100, u = k % 10; return k + (t >= 11 && t <= 13 ? "th" : u === 1 ? "st" : u === 2 ? "nd" : u === 3 ? "rd" : "th"); };
  var cap = function (s) { return s.charAt(0).toUpperCase() + s.slice(1); };
  var MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  var ml = function (ym) { var p = ym.split("-"); return MON[+p[1] - 1] + " " + p[0]; };
  var last = function (a) { return a[a.length - 1]; };
  var reply = function (text, o) { o = o || {}; return { text: text, list: o.list || [], links: o.links || [], src: o.src || "", chips: o.chips || [] }; };

  /* ---------- where the pages live (links are built from the script's own address) ---------- */
  var BASE = (function () {
    try { var s = document.currentScript || document.querySelector('script[src*="assets/chat.js"]'); return new URL("../", s.src).href; } catch (e) { return ""; }
  })();
  var site = function (path, label) { return { label: label, href: BASE + path }; };

  /* ---------- the knowledge shared by both sites ---------- */
  var DX = function () { return root.DASH4; };               // the dashboard's core data (dashboard only)
  var SDATA = function () { return root.SITE_DATA; };        // the public site's data (public pages only)
  var NAME3 = { E: "Employed workers", V: "Job vacancies", S: "Registered job seekers" };
  var pc = function (x) { return fmt(x * 100, 0) + "%"; };
  function counts() {
    var D = DX() && DX().meta, M = SDATA() && SDATA().meta;
    if (D) return { series: D.series, districts: D.districts.length, states: D.states.length, sectors: D.sectors.length, trades: D.trades.length, sectorList: D.sectors, stateList: D.states };
    if (M) return { series: M.series, districts: M.districts, states: M.states, sectors: M.sectors, trades: M.trades, sectorList: M.sector_list || [], stateList: M.state_list || [] };
    return null;
  }
  var join = function (a) { return a.length > 1 ? a.slice(0, -1).join(", ") + " and " + last(a) : a.join(""); };

  function accuracyReply() {
    var S = SDATA(), A = S && S.accuracy, D = DX();
    if (A) {
      var t = A.test, st = A.stress, cv = A.coverage.test;
      var rows = ["E", "V", "S"].map(function (k) { return NAME3[k] + ": typical error " + t[k].model + "% against " + t[k].baseline + "% for the best simple forecast, " + t[k].gain_pct + "% closer"; });
      return reply("Accuracy was measured once, on years the model never saw (2015 to 2019). The error is WAPE, the size of the misses as a share of the actual values, averaged over one to sixty months ahead.",
        { list: rows.concat(["The shock years 2020 to 2025 were scored separately: employed workers were still " + st.E.gain_pct + "% closer than the baseline, but job seekers were under-forecast by " + Math.abs(st.S.bias_pct) + "% and did not beat it.",
          "The usual 90% range held for " + pc(cv.E) + " of employed-worker outcomes, " + pc(cv.V) + " of vacancies and " + pc(cv.S) + " of job seekers, so a wider range is shown as well.",
          "Job seekers are the least reliable measure, and the fifth year is looser than the first."]), links: [site("about.html#evaluation", "Model evaluation")], src: "site_data.js (reports/v4/evaluation)" });
    }
    if (D) {
      var c = D.coverage.series;
      return reply("In testing, the usual 90% range held for " + pc(c["test|E|validation"]) + " of employed-worker outcomes, " + pc(c["test|V|validation"]) + " of vacancies and " + pc(c["test|S|validation"]) + " of job seekers in 2015 to 2019. In the shock years 2020 to 2025 it held far less, which is why a wider range is drawn too.",
        { links: [dashLink("data", {}, "Open Data and notes")], src: "interval_coverage.csv" });
    }
    return reply("The model is scored on held-out years. See the model evaluation section of the About page for the figures.", { links: [site("about.html#evaluation", "Model evaluation")] });
  }

  var KB = [
    { k: ["what is this", "about the project", "about this", "what does this", "what do you do", "purpose", "tell me about", "overview of", "lmis", "project", "what is lmis", "kaushalsetu"], a: function () {
      var c = counts(), n = c ? " for " + c.districts + " districts in " + c.states + " states, " + c.sectors + " sectors and " + c.trades + " trades (" + fmt(c.series) + " series)" : "";
      return reply("KaushalSetu forecasts three things for the next five years" + n + ": how many people are employed, how many jobs are open and how many job seekers are registered. It adds a Demand Index, a comparison of forecast openings with training seats (the capacity gap) and early-warning flags for districts heading towards a shortage of workers or a surplus.", { links: [site("about.html", "About the project")] }); } },
    { k: ["real", "simulated", "synthetic", "official", "fake", "genuine", "demo", "actual data", "true data"], a: function () {
      return reply("No. Every figure is simulated for demonstration. It behaves like official statistics but describes no real district, and it is not an official statistic.", { links: [site("resources.html#datasets", "Data sources")] }); } },
    { k: ["sector", "state", "district", "covered", "coverage", "which places", "where", "trade", "how many"], when: "pub", a: function () {
      var c = counts();
      return reply(c && c.sectorList.length ? "The data covers " + c.districts + " districts in " + join(c.stateList) + ", across " + c.sectors + " sectors (" + join(c.sectorList) + ") and " + c.trades + " trades, five per sector." : "The dataset section of the About page lists the states, districts and sectors.", { links: [site("about.html#dataset", "Dataset details")] }); } },
    { k: ["accura", "error", "wape", "how good", "reliable", "trust", "baseline", "evaluat", "performance", "test result"], a: function () { return accuracyReply(); } },
    { k: ["confidence", "how sure", "uncertain", "interval", "range", "90%", "band", "wide range", "usual range"], a: function () {
      return reply("Every forecast carries a confidence label and two 90% ranges. The label (high, up to 8% typical error; medium, up to 20%; low, above) comes from the error of earlier forecasts for the same trade and horizon band, one level lower for small series. The usual range was calibrated on 2010 to 2019; the wide range also uses the shock years 2020 to 2025 and is the one to read for totals of many series, because their errors move together.", { links: [site("about.html#engine", "How the engine works")] }); } },
    { k: ["how does", "how is", "how are", "how do you", "method", "model", "xgboost", "machine learning", "algorithm", "train", "forecast made", "engine", "architecture", "seeds"], a: function () {
      return reply("One XGBoost model per measure (employed workers, vacancies, job seekers) forecasts the change in the log of the level, with the number of months ahead as an input, for every horizon from 1 to 60 and averaged over three random starts. Its 82 inputs use only data known at the forecast date. Settings were tuned on 2010 to 2014 and scored once on 2015 to 2019 and once on 2020 to 2025. The five trades of a sector are reconciled so that totals add up.", { links: [site("about.html#engine", "Machine learning engine")] }); } },
    { k: ["demand index", "index", "0 to 100", "hiring demand"], a: function () {
      return reply("The Demand Index is a number from 0 to 100 for a district and trade in a month. It compares openings per worker (from vacancies, job-portal postings and the National Career Service) with the other districts of the same trade, plus a national level term so that it moves over the years. 50 is the median district at the 2018 to 2019 level; 84 is one standard deviation above and 16 one below. Forecast months use the forecast vacancies only.", { links: [dashLink("index", {}, "Open the Demand Index"), site("about.html#measures", "How it is built")] }); } },
    { k: ["severity", "severe", "undersupply", "oversupply", "undersupplied", "oversupplied", "ranked by", "worst gap"], a: function () {
      return reply("The severity ranking orders trades and places by how far trained supply is from the openings: score = ln(expected certified per year / average monthly openings). Below 0 is undersupply (fewer people finish training than there are openings), above 0 oversupply. Severe means a ratio of 2 or more either way, high 1.5, moderate 1.25. You can rank trades, states, state and trade, districts, district and sector, or district and trade, for any year to 2030, on the Rankings page or at /api/severity.", { links: [dashLink("ranking", {}, "Open the severity ranking"), site("about.html#measures", "How it is built")] }); } },
    { k: ["capacity", "seats", "certified", "training seats", "gap", "supply of trained"], a: function () {
      return reply("The capacity gap sets forecast openings for each year against the training seats sanctioned in 2025 to 2026, held flat because no seat plans are forecast, and the trainees expected to be certified (seats times the 2023 to 2025 certification rate). Seats fall short where a district's share of seats is under 0.6 times its share of openings in the trade, and exceed demand above 1.65 times. Read it as a ranking of where capacity is stretched.", { links: [dashLink("capacity", {}, "Open the Capacity gap"), site("about.html#measures", "How it is built")] }); } },
    { k: ["alert", "watch", "flag", "early warning", "early-warning", "warning", "decile", "percentile", "tightest", "loosest", "relative"], a: function () {
      return reply("In each trade and month, districts are ranked by forecast vacancies per registered seeker. The top tenth is a shortage alert and the bottom tenth an oversupply alert; the next fifteen per cent on either side is a watch. A flag is relative: it says which districts stand out, not that openings exceed seekers. In testing, alerts one to twelve months ahead were right about seven times in ten, against a base rate of one in ten.", { links: [dashLink("warnings", {}, "Open Early warnings")] }); } },
    { k: ["dashboard", "open the dash", "where can i see", "pages"], when: "pub", a: function () {
      return reply("The dashboard has eight pages: Overview, Map, Forecast, Demand Index, Capacity gap, Rankings, Early warnings, and Data and notes. Filters for sector, trade, state and district stay in the address, so any view can be shared, and every page can be downloaded as CSV or JSON.", { links: [site("dashboard/index.html", "Open the dashboard")] }); } },
    { k: ["data source", "where from", "where does the data", "dataset", "columns", "variables", "resource", "acquired", "download data"], when: "pub", a: function () {
      return reply("The Resources page lists the data behind the project and the websites it was modelled on, and the About page describes the dataset and its columns.", { links: [site("resources.html#datasets", "Data sources"), site("about.html#dataset", "Dataset details")] }); } },
    { k: ["language", "hindi", "text size", "font", "dark", "light", "theme", "display"], a: function () {
      return reply("English and Hindi are available on the website and the dashboard. On the website the round Display button in the header sets the text size, the theme (light or dark) and the language; on the dashboard use the language and theme buttons in the top bar. Your choice stays on your device. This assistant answers in English.", {}); } },
    { k: ["map", "zoom"], when: "pub", a: function () {
      return reply("On the home page the map shows all 317 districts. Choose a sector and a measure (employed workers, vacancies, job seekers or the Demand Index) and 12, 36 or 60 months ahead; hover or tap a district for its numbers and use the state buttons to zoom.", { links: [site("index.html#map", "Open the map")] }); } },
    { k: ["cookie", "privacy", "track", "analytics", "contact", "email", "feedback", "personal"], a: function () {
      return reply("The site sets no cookies and has no analytics. " + (aiOn() ? "When AI answers are on, your question and a summary of this page's data are sent to Google's Gemini through this site's server so that it can word the answer; switch AI off in this window to keep everything in your browser." : "Everything here runs in your browser."), {}); } },
    { k: ["limit", "weak", "caveat", "cannot", "can't", "problem", "not good", "wrong", "assumption"], a: function () {
      return reply("The main limits: the data is simulated; job-seeker forecasts are the least reliable and long horizons are looser; the 2020 to 2025 shock was not foreseen, so ranges for totals need the wide band; training seats are held flat in the capacity gap; and for some filter combinations no checked range exists, so only the forecast is shown.", { links: [site("about.html#limits", "What to keep in mind")] }); } },
    { fact: false, k: ["who are you", "are you ai", "are you a bot", "chatbot", "are you real", "language model", "gpt", "claude", "gemini"], a: function () {
      return reply(aiOn() ? "I am the assistant built into this site. I use Google's Gemini to word my answers, but only from this site's own pages and forecast data; I cannot look anything up elsewhere, and I can be wrong." : "I am the assistant built into this site. I answer from this site's own pages and forecast data, in your browser, and I can be wrong.", {}); } },
    { fact: false, k: ["hello", "hi ", "hey", "namaste", "good morning", "good evening"], a: function () { return reply("Hello. What would you like to know?", { chips: suggestions() }); } },
    { fact: false, k: ["thank"], a: function () { return reply("You are welcome.", {}); } },
    { fact: false, k: ["help", "what can you", "what can i ask", "options"], a: function () { return reply("You can ask me about the project, the data, how accurate the forecasts are, the Demand Index, the capacity gap and what the flags mean" + (IS_DASH() ? ", and look up figures: employed workers, vacancies or seekers by sector, trade, state or district, the Demand Index, seats against openings, and alerts." : ", and look up a district or India's totals."), { chips: suggestions() }); } }
  ];

  /* ---------- the dashboard: questions answered from window.DASH4 and DASH4_ALERTS ---------- */
  var PAGE_HELP = {
    overview: "Employed workers, vacancies, job seekers and the Demand Index with their forecasts to 2030, a states table, the early-warning summary and a table of trades. Click a state or a trade to filter.",
    map: "The 317 districts on a map, coloured by vacancies, employed workers, job seekers or the Demand Index 12, 36 or 60 months ahead, with the states, the highest and lowest districts and where the alerts are.",
    forecast: "Five-year forecasts of employed workers, vacancies or seekers with a usual and a wider 90% range, December values and a trade table.",
    index: "The Demand Index (0 to 100) over time, states by sector or trade, and the districts with the highest and lowest index in a sector.",
    capacity: "Forecast openings against training seats and expected certified trainees by year, and by trade or state, with a seat scenario: change the seats and see the ratio, the severity and the seats a target needs.",
    ranking: "The severity ranking (trades, states, districts and district-trades ordered by how far trained supply is from the openings, filterable and downloadable) and fixed all-India lists: fastest and slowest vacancy growth, where trained supply is most stretched or in surplus, and the districts with the highest Demand Index per sector.",
    warnings: "Every shortage and oversupply alert 12, 36 or 60 months ahead, with confidence labels, for the current filters.",
    data: "Coverage of the dataset, how often the ranges held in testing, how accurate the alerts were, definitions and the notes on limits."
  };
  var PAGE_NAMES = { overview: ["overview", "home"], map: ["map"], forecast: ["forecast"], index: ["demand index", "index"], capacity: ["capacity", "capacity gap"], ranking: ["rankings", "ranking"], warnings: ["warnings", "early warnings", "alerts page"], data: ["data and notes", "notes", "data page"] };

  function hashState() {
    var h = (root.location ? root.location.hash : "").replace(/^#\/?/, ""), q = h.split("?"), p = {};
    (q[1] || "").split("&").forEach(function (kv) { if (!kv) return; var a = kv.split("="); try { p[decodeURIComponent(a[0])] = decodeURIComponent((a[1] || "").replace(/\+/g, " ")); } catch (e) { /* skip */ } });
    return { page: PAGE_HELP[q[0]] ? q[0] : "overview", p: p };
  }
  function dashLink(page, f, label) {
    var parts = [];
    ["sector", "trade", "state", "district", "k", "h", "t", "c"].forEach(function (k) { if (f && f[k] !== "" && f[k] != null) parts.push(k + "=" + encodeURIComponent(f[k])); });
    return { label: label, href: (IS_DASH() ? "" : BASE + "dashboard/index.html") + "#/" + page + (parts.length ? "?" + parts.join("&") : "") };
  }

  function entities(qraw, ctx) {
    var M = DX().meta, q = qraw, out = { sector: "", trade: "", state: "", district: "", said: {} };
    var dist = {};
    var names = M.districts.map(function (d) { dist[d[0]] = { c: String(d[0]), name: d[1], state: M.states[d[2]] }; return { c: String(d[0]), n: norm(d[1]).trim(), s: M.states[d[2]] }; }).sort(function (a, b) { return b.n.length - a.n.length; });
    var hit = names.filter(function (d) { return q.indexOf(" " + d.n + " ") >= 0; })[0];
    if (hit) { out.district = hit.c; out.said.district = true; q = q.replace(" " + hit.n + " ", " "); }
    else {
      var words = {}, reserved = " north south east west central new city rural urban " + M.states.concat(M.sectors).map(function (x) { return norm(x); }).join(" ") + " ";
      names.forEach(function (d) { var w = d.n.split(" ")[0]; if (w.length > 3 && reserved.indexOf(" " + w + " ") < 0) (words[w] = words[w] || []).push(d); });
      var found = Object.keys(words).filter(function (w) { return q.indexOf(" " + w + " ") >= 0; });
      if (found.length) { var cand = words[found[0]]; if (cand.length === 1) { out.district = cand[0].c; out.said.district = true; } else out.ambiguous = cand.map(function (d) { return dist[d.c].name; }); }
    }
    M.states.forEach(function (st) {
      var n = norm(st), parts = n.trim().split(" ").filter(function (w) { return w.length >= 5; });
      if (q.indexOf(n) >= 0 || parts.some(function (w) { return q.indexOf(" " + w) >= 0; })) { out.state = st; out.said.state = true; }
    });
    // trades: the whole name, or a word of its name that no other trade uses
    var tw = {}, sw = " " + M.sectors.map(function (x) { return norm(x); }).join(" ") + " ";        // a word of a sector's name (construction, healthcare) names the sector, not one trade
    M.trades.forEach(function (x) { norm(x.n).trim().split(" ").forEach(function (w) { if (w.length >= 6 && sw.indexOf(" " + w + " ") < 0) (tw[w] = tw[w] || {})[x.c] = 1; }); });
    var tr = M.trades.filter(function (x) { return q.indexOf(norm(x.n)) >= 0 || q.indexOf(" " + x.c.toLowerCase()) >= 0; })[0];
    if (!tr) {
      var ws = Object.keys(tw).filter(function (w) { return Object.keys(tw[w]).length === 1 && (q.indexOf(" " + w) >= 0 || q.indexOf(" " + w.replace(/s$/, "") + " ") >= 0); });
      if (ws.length) tr = M.trades.filter(function (x) { return x.c === Object.keys(tw[ws[0]])[0]; })[0];
    }
    if (tr) { out.trade = tr.c; out.sector = tr.s; out.said.trade = true; out.said.sector = true; }
    M.sectors.forEach(function (sec) {
      if (out.said.trade) return;
      var n = norm(sec).trim(), stem = n.split(/[ \-]/)[0];
      var it = n.indexOf("it-ites") === 0 ? any(q, ["it-ites", "ites", "=it sector", "in it ", "for it ", "=it industry", "information tech"]) : false;
      if (it || (n.indexOf("it-ites") !== 0 && stem.length >= 5 && q.indexOf(" " + stem.slice(0, 5)) >= 0) || (n.indexOf("textiles") === 0 && any(q, ["apparel", "garment"]))) { out.sector = sec; out.said.sector = true; }
    });
    if (out.district) out.state = dist[out.district].state;
    var f = (ctx && ctx.p) || {};
    if (!out.said.trade && !out.said.sector) { if (f.trade && !out.said.sector) { out.trade = f.trade; } if (f.sector) out.sector = f.sector; }
    if (!out.said.state && !out.said.district) { if (f.state) out.state = f.state; if (f.district && dist[f.district]) { out.district = f.district; out.state = dist[f.district].state; } }
    return out;
  }
  function horizonOf(q) {
    var y = q.match(/\b(202[6-9]|2030)\b/);
    if (y) return (+y[1] - 2025) * 12;
    var yr = q.match(/(\d)\s*-?\s*years?/);
    if (yr && +yr[1] >= 1 && +yr[1] <= 5) return +yr[1] * 12;
    var m = q.match(/(\d{1,2})\s*-?\s*months?/);
    if (m && +m[1] >= 1 && +m[1] <= 60) return +m[1];
    if (any(q, ["next month"])) return 1;
    if (any(q, ["next year", "twelve months"])) return 12;
    if (any(q, ["five years", "end of the forecast", "long term"])) return 60;
    return 0;                                               // not said: the answers give both 12 and 60 months
  }
  var scopeName = function (D, e) { var M = D.meta; return [e.district ? M.districts.filter(function (d) { return String(d[0]) === e.district; })[0][1] : e.state || "all states", e.trade ? M.trades.filter(function (x) { return x.c === e.trade; })[0].n : e.sector || "all sectors"].join(", "); };
  var urlFilters = function (e) { return { sector: e.sector, trade: e.trade, state: e.district ? "" : e.state, district: e.district }; };

  /* the numbers of a scope from the core file; null where they live in a state's shard (a district, or one trade across a state) */
  function groupOf(D, e) {
    var g = D.groups;
    if (!e.state && !e.district) return e.trade ? { G: g.trade[e.trade], level: "trade" } : e.sector ? { G: g.sector[e.sector], level: "sector" } : { G: g.india[""], level: "india" };
    if (e.state && !e.district && !e.trade) return e.sector ? { G: g.state_sector[e.state + "|" + e.sector], level: "state_sector" } : { G: g.state[e.state], level: "state" };
    return null;
  }
  var HC = function (D) { return D.meta.hist_core[2]; };
  function rangeAt(D, level, k, v, h, wide) {
    var c = D.cal_levels[level][k], lo = Math.min(c[wide ? "lo_wide" : "lo"][h - 1], 0), hi = Math.max(c[wide ? "hi_wide" : "hi"][h - 1], 0);
    return [Math.round(v * Math.exp(lo)), Math.round(v * Math.exp(hi))];
  }
  function valueReply(D, q, e, h) {
    var s = groupOf(D, e), hs = h ? [h] : [12, 60];
    if (!s) return reply("For " + scopeName(D, e) + " the figures come from the state's data file, which this assistant does not load. Open the dashboard with these filters to read them, and the 90% range where one exists.",
      { links: [dashLink("forecast", urlFilters(e), "Open the Forecast page")] });
    var ks = [];
    if (any(q, ["employ", "worker", "job holder"])) ks.push("E");
    if (any(q, ["vacanc", "opening", "job open", "demand"])) ks.push("V");
    if (any(q, ["seeker", "supply", "registered", "unemploy", "looking for"])) ks.push("S");
    if (!ks.length) ks = ["E", "V", "S"];
    var n0 = HC(D), list = [];
    ks.forEach(function (k) {
      var now = s.G[k][n0 - 1], line = NAME3[k] + ": " + compact(now) + " in " + ml(D.meta.hist_core[1]);
      hs.forEach(function (hh) {
        var f = s.G[k][n0 + hh - 1], u = rangeAt(D, s.level, k, f, hh, false), w = rangeAt(D, s.level, k, f, hh, true);
        line += "; " + compact(f) + " forecast for " + ml(addM(D.meta.fc[0], hh - 1)) + " (" + signed((f / now - 1) * 100) + "; usual 90% range " + compact(u[0]) + " to " + compact(u[1]) + ", wide " + compact(w[0]) + " to " + compact(w[1]) + ")";
      });
      list.push(line);
    });
    return reply("For " + scopeName(D, e) + ":", { list: list.concat(["Point forecasts add up across trades; the ranges do not, and for totals the wide range is the one to read."]), links: [dashLink("forecast", urlFilters(e), "Open the Forecast page")], src: "forecast_rollups.csv.gz, aggregate_interval_calibration.csv" });
  }
  var addM = function (ym, n) { var p = ym.split("-"), i = (+p[0]) * 12 + (+p[1] - 1) + n; return Math.floor(i / 12) + "-" + ("0" + ((i % 12) + 1)).slice(-2); };

  function indexReply(D, e, h) {
    var s = groupOf(D, e), n0 = HC(D), lk = [dashLink("index", urlFilters(e), "Open the Demand Index")];
    if (s) {
      var hs = h ? [h] : [12, 60], parts = hs.map(function (hh) { return fmt(s.G.DI[n0 + hh - 1], 1) + " in " + ml(addM(D.meta.fc[0], hh - 1)); });
      return reply("Demand Index for " + scopeName(D, e) + ": " + fmt(s.G.DI[n0 - 1], 1) + " in " + ml(D.meta.hist_core[1]) + ", then " + parts.join(" and ") + ". 50 is the median district of a trade at the 2018 to 2019 level.", { links: lk, src: "demand_index.parquet (employed-weighted)" });
    }
    var y = h ? Math.min(4, Math.max(0, Math.ceil(h / 12) - 1)) : 4, ys = 2026 + y;
    if (e.district && e.sector) { var v = D.di_district_sector[e.district + "|" + e.sector]; if (v) return reply("Demand Index for " + scopeName(D, e) + ": " + fmt(v[0], 1) + " on average in 2026 and " + fmt(v[y], 1) + " in " + ys + ".", { links: lk, src: "demand_index.parquet" }); }
    if (e.state && e.trade) { var w = D.di_state_trade[e.state + "|" + e.trade]; if (w) return reply("Demand Index for " + scopeName(D, e) + ": " + fmt(w[0], 1) + " on average in 2026 and " + fmt(w[y], 1) + " in " + ys + ".", { links: lk, src: "demand_index.parquet" }); }
    return reply("For this combination, choose a sector (for a district) or a trade (for a state) to read the Demand Index, or open the page.", { links: lk });
  }

  function capacityReply(D, e, h) {
    var C = D.capacity, pick = function (rows, f) { return rows.filter(f).sort(function (a, b) { return a.year - b.year; }); }, rows;
    if (e.district) return reply("Seats and openings for a single district come from the state's data file. Open the Capacity gap page with this district chosen.", { links: [dashLink("capacity", urlFilters(e), "Open the Capacity gap")] });
    if (e.state) rows = e.trade ? pick(C.state_trade, function (r) { return r.State_Name === e.state && r.Trade_Code === e.trade; }) : e.sector ? pick(C.state_sector, function (r) { return r.State_Name === e.state && r.Sector_Name === e.sector; }) : pick(C.state, function (r) { return r.State_Name === e.state; });
    else rows = e.trade ? pick(C.trade, function (r) { return r.Trade_Code === e.trade; }) : e.sector ? pick(C.sector, function (r) { return r.Sector_Name === e.sector; }) : C.india.slice();
    if (!rows.length) return reply("There is no capacity figure for that combination.", {});
    var a = rows[0], b = rows[4], y = h ? Math.min(4, Math.max(0, Math.ceil(h / 12) - 1)) : 4, c = rows[y];
    return reply("Capacity for " + scopeName(D, e) + ": " + fmt(a.avg_vacancies) + " average openings in 2026 against " + fmt(a.seats) + " seats (held flat) and " + fmt(a.expected_certified) + " expected certified a year, so " + fmt(a.supply_per_opening, 2) + " certified per opening. In " + c.year + " that is " + fmt(c.supply_per_opening, 2) + " certified per opening (" + fmt(c.openings_per_seat, 2) + " openings per seat)." + (c.supply_per_opening < 1 ? " Fewer people finish training in a year than there are openings." : " More people finish training in a year than there are openings."),
      { links: [dashLink("capacity", urlFilters(e), "Open the Capacity gap")], src: "capacity_gap_*.csv" });
  }

  /* the severity ranking: trades (or the trades of a state) by ln(expected certified per opening); below 0 undersupply, above 0 oversupply */
  function severityReply(D, q, e, h) {
    var C = D.capacity, y = h ? Math.min(2030, 2025 + Math.ceil(h / 12)) : 2030, over = any(q, ["oversuppl", "surplus", "too many"]), bands = D.meta.severity_bands;
    var tab = e.state && !e.district ? C.state_trade.filter(function (r) { return r.State_Name === e.state; }) : C.trade;
    var rows = tab.filter(function (r) { return r.year === y && (!e.sector || D.meta.trades.filter(function (x) { return x.c === r.Trade_Code; })[0].s === e.sector) && (!e.trade || r.Trade_Code === e.trade); })
      .map(function (r) { var sc = Math.log(Math.max(r.supply_per_opening, 1e-3)), a = Math.abs(sc), b = "balanced"; for (var i = 0; i < bands.length; i++) if (a >= bands[i][1]) { b = bands[i][0]; break; } return { r: r, sc: sc, b: b }; })
      .sort(function (a, b) { return over ? b.sc - a.sc : a.sc - b.sc; });
    var name = function (r) { return D.meta.trades.filter(function (x) { return x.c === r.Trade_Code; })[0].n + (r.State_Name ? " (" + r.State_Name + ")" : ""); };
    return reply((over ? "Most oversupplied" : "Most undersupplied") + " trades in " + y + (e.state ? " in " + e.state : "") + (e.sector ? ", " + e.sector : "") + " (certified trainees per opening; below 1 is undersupply):",
      { list: rows.slice(0, 5).map(function (x, i) { return "#" + (i + 1) + " " + name(x.r) + ": " + fmt(x.r.supply_per_opening, 2) + " per opening, " + x.b + " " + (x.sc < 0 ? "undersupply" : "oversupply"); }), links: [dashLink("ranking", urlFilters(e), "Open the severity ranking")], src: "capacity_gap_trade.csv, capacity_gap_state_trade.csv" });
  }

  function alertsReply(D, q, e, h) {
    var A = root.DASH4_ALERTS, hz = !h ? 0 : h <= 24 ? 0 : h <= 48 ? 1 : 2, hn = [12, 36, 60][hz], M = D.meta;
    var rows = A.rows.filter(function (r) { var tr = M.trades[r[4]]; return r[1] === hz && (!e.state || M.states[r[2]] === e.state) && (!e.district || String(r[3]) === e.district) && (!e.trade || tr.c === e.trade) && (!e.sector || tr.s === e.sector); });
    var nS = rows.filter(function (r) { return r[0] === 0; }).length, want = any(q, ["oversupply", "surplus", "too many seekers"]) ? 1 : any(q, ["shortage", "scarce", "not enough workers", "tight"]) ? 0 : -1;
    var pool = rows.filter(function (r) { return want < 0 || r[0] === want; }).sort(function (a, b) { return (a[0] - b[0]) || (a[0] === 0 ? b[5] - a[5] : a[5] - b[5]); }).slice(0, 5);
    var name = function (r) { var d = M.districts.filter(function (x) { return x[0] === r[3]; })[0]; return d[1]; };
    return reply(hn + " months ahead, for " + scopeName(D, e) + ": " + nS + " shortage alerts and " + (rows.length - nS) + " oversupply alerts (series in the top or bottom tenth of their trade).",
      { list: pool.map(function (r) { var tr = M.trades[r[4]]; return name(r) + " (" + M.states[r[2]] + "), " + tr.n + ": " + (r[0] === 0 ? "shortage" : "oversupply") + " alert, " + ord(r[5]) + " percentile, vacancy confidence " + (CONFW[r[8]] || r[8]) + ", seeker confidence " + (CONFW[r[9]] || r[9]); }),
        links: [dashLink("warnings", Object.assign(urlFilters(e), { h: hn, t: want < 0 ? "" : want }), "Open in Early warnings")], src: "flag_alerts.csv" });
  }
  var CONFW = { H: "high", M: "medium", L: "low" };

  function rankingReply(D, q, e) {
    var R = D.rankings, pickRank = function (frag) { return R.filter(function (r) { return r.ranking.toLowerCase().indexOf(frag) >= 0; }); };
    var key = any(q, ["slowest"]) ? "slowest vacancy" : any(q, ["fastest", "growing", "growth", "grow"]) ? "fastest vacancy" : any(q, ["surplus", "most capacity", "oversupplied"]) ? "most surplus" : any(q, ["stretched", "short of", "shortage of trained", "least supply"]) ? "most stretched in 2030 (certified" : null;
    if (any(q, ["demand index"]) && e.sector) key = "highest demand index in 2030: " + e.sector.toLowerCase();
    if (any(q, ["state", "states"]) && key && key.indexOf("demand") < 0) key = null;                      // "which states ..." is answered from the state totals below
    if (key) {
      var rows = pickRank(key).slice(0, 5), key2 = rows.length ? rows[0].ranking : "";
      if (rows.length) return reply(key2 + ":", { list: rows.map(function (r) { return "#" + r.rank + " " + r.key.split(" | ").map(function (x) { var t = D.meta.trades.filter(function (y) { return y.c === x; })[0]; return t ? t.n + " (" + x + ")" : x; }).join(", ") + ": " + fmt(r.value, 2) + (r.detail ? " (" + r.detail.replace("employed_growth_pct_2026_2030=", "employed workers grow ").replace("openings_per_seat=", "openings per seat ").replace(/_/g, " ") + (r.detail.indexOf("growth") >= 0 ? "%" : "") + ")" : ""); }), links: [dashLink("ranking", {}, "Open Rankings")], src: "rankings.csv" });
    }
    // states by growth in employed workers
    var n0 = HC(D), rows2 = D.meta.states.map(function (s) { var G = e.sector ? D.groups.state_sector[s + "|" + e.sector] : D.groups.state[s]; return { s: s, g: (G.E[n0 + 59] / G.E[n0 - 1] - 1) * 100 }; }).sort(function (a, b) { return b.g - a.g; });
    return reply("States by growth in employed workers from December 2025 to December 2030" + (e.sector ? " in " + e.sector : "") + ":", { list: rows2.slice(0, 5).map(function (r, i) { return "#" + (i + 1) + " " + r.s + ": " + signed(r.g); }), links: [dashLink("overview", urlFilters(e), "Open the Overview")], src: "forecast_rollups.csv.gz" });
  }

  function dashAnswer(raw, q, ctx) {
    ctx = ctx || hashState();
    var D = DX(), e = entities(q, ctx), h = horizonOf(q);
    if (e.ambiguous) return reply("Which district do you mean: " + join(e.ambiguous) + "?", { chips: e.ambiguous.slice(0, 3) });
    var data = e.said.sector || e.said.state || e.said.district || e.said.trade;
    var isDef = any(q, ["what is", "what are", "what does", "mean", "define", "explain", "how is"]) && !data;
    if (any(q, ["this page", "current page", "what am i", "where am i", "page show"])) return reply(cap(PAGE_NAMES[ctx.page][0]) + ": " + PAGE_HELP[ctx.page], {});
    var pageHit = Object.keys(PAGE_NAMES).filter(function (p) { return PAGE_NAMES[p].some(function (n) { return q.indexOf(" go to " + n) >= 0 || q.indexOf(" open " + n) >= 0 || q.indexOf(" take me to " + n) >= 0; }); })[0];
    if (pageHit) return reply(cap(PAGE_NAMES[pageHit][0]) + ": " + PAGE_HELP[pageHit], { links: [dashLink(pageHit, (ctx && ctx.p) || {}, "Go to " + cap(PAGE_NAMES[pageHit][0]))] });
    if (any(q, ["download", "csv", "json", "export", "save"])) return reply("Use CSV or JSON above the page for the table you are looking at; both follow the current filters.", {});
    if (any(q, ["filter", "reset", "clear"])) return reply("The Sector, Trade, State and District filters sit above every page and are kept in the address, so a view can be shared. Reset filters clears all four.", {});
    if (any(q, ["exit", "leave", "log out", "logout", "sign out", "close the dash"])) return reply("Use Exit in the top bar or the sidebar to return to the public site. There is no login.", {});
    if (!isDef && any(q, ["entering", "leaving", "newly flagged", "new alert", "about to become", "will become", "start to"])) {
      var lv = any(q, ["leaving", "exit", "stop being"]) ? "leave" : "enter";
      return reply("Alerts that begin or end are on the Early warnings page: choose Entering an alert or Leaving an alert, a horizon of 12, 36 or 60 months, and the filters. A series is entering when it is not in the top or bottom tenth of its trade now (December 2025, actual) but is at the horizon; leaving is the reverse. Most alerts persist: about one in eight of today's alerts is out of its tail 12 months ahead, and about as many move in.", { links: [dashLink("warnings", Object.assign(urlFilters(e), { c: lv, h: h ? [12, 36, 60][h <= 24 ? 0 : h <= 48 ? 1 : 2] : 12 }), "Open " + (lv === "enter" ? "entering" : "leaving") + " alerts")] });
    }
    if (!isDef && any(q, ["alert", "watch", "shortage", "oversupply", "warning", "flag", "risk"])) return alertsReply(D, q, e, h);
    if (!isDef && any(q, ["demand index", "hiring demand", "index of"])) return indexReply(D, e, h);
    if (any(q, ["scenario", "what if", "add seats", "more seats", "fewer seats", "seats needed", "how many seats", "increase seats", "reduce seats"])) {
      return reply("The seat scenario is on the Capacity gap page, below the table: choose a percentage change in seats, the year it starts, the year to evaluate and a target for certified trainees per opening. It shows the ratio and the severity before and after, and the seats each trade or place would need to reach the target. The same is at /api/scenario. It assumes the certification rate and the forecast openings stay as they are, with no delay between sanctioning a seat and certifying a trainee.", { links: [dashLink("capacity", urlFilters(e), "Open the seat scenario")] });
    }
    if (!isDef && any(q, ["undersuppl", "oversuppl", "severity", "severe", "most short"])) return severityReply(D, q, e, h);
    if (!isDef && any(q, ["stretched", "most surplus"])) return rankingReply(D, q, e);
    if (!isDef && any(q, ["capacity", "seats", "certified", "training seat", "trained"])) return capacityReply(D, e, h);
    if (!isDef && any(q, ["rank", "fastest", "slowest", "top ", "highest", "lowest", "worst", "best", "most ", "stretched", "growing"])) return rankingReply(D, q, e);
    if (!isDef && (data || any(q, ["forecast", "predict", "expect", "how many", "how much", "latest", "current", "total", "number of"]))) return valueReply(D, q, e, h);
    if (any(q, ["source", "files", "sha", "hash", "origin", "latest forecast", "forecast from"])) return reply("The figures come from the phase 6 exports (forecast_rollups.csv.gz, capacity_gap_*.csv, flag_alerts.csv, rankings.csv) and the per-state data files, built from a forecast made in " + ml(D.meta.origin) + " with data to that month. File hashes are on the Data and notes page.", { links: [dashLink("data", {}, "Open Data and notes")] });
    return null;
  }

  /* ---------- the public site: India's totals, capacity and a district, from site_data.js and map_data.js ---------- */
  function pubAnswer(raw, q) {
    var S = SDATA(), M = root.MAP_DATA;
    if (!S) return null;
    var H = S.headline, n = function (k) { return NAME3[k]; };
    if (any(q, ["india", "overall", "total", "national", "all districts", "all states"]) && any(q, ["employ", "worker", "vacanc", "opening", "seeker", "forecast", "how many"]) && !(M && districtIn(M, q))) {
      var ks = []; if (any(q, ["employ", "worker"])) ks.push("E"); if (any(q, ["vacanc", "opening"])) ks.push("V"); if (any(q, ["seeker"])) ks.push("S"); if (!ks.length) ks = ["E", "V", "S"];
      return reply("Across all ten states: ", { list: ks.map(function (k) { var a = H.h60[k]; return n(k) + ": " + compact(H.now[k]) + " in " + S.meta.origin_label + ", forecast " + compact(a.point) + " in December 2030 (usual 90% range " + compact(a.usual[0]) + " to " + compact(a.usual[1]) + ", wide " + compact(a.wide[0]) + " to " + compact(a.wide[1]) + ")"; }).concat(["Demand Index " + fmt(H.h12.DI, 1) + " in December 2026 and " + fmt(H.h60.DI, 1) + " in December 2030."]), links: [site("dashboard/index.html#/forecast", "Open the dashboard")], src: "site_data.js (forecast_rollups.csv.gz)" });
    }
    var isDef = any(q, ["what is", "what are", "what does", "mean", "define", "explain", "how is"]);
    if (!isDef && !(M && districtIn(M, q)) && any(q, ["capacity", "seats", "certified", "trained"]) && H.capacity) {
      var sec = Object.keys(H.capacity).filter(function (s) { return q.indexOf(" " + norm(s).trim().slice(0, 5)) >= 0; })[0];
      var secs = sec ? [sec] : Object.keys(H.capacity);
      return reply("Certified trainees per opening (below 1 means fewer people finish training in a year than there are openings), seats held flat:", { list: secs.map(function (s) { var c = H.capacity[s]; return s + ": " + fmt(c["2026"].supply_per_opening, 2) + " in 2026 and " + fmt(c["2030"].supply_per_opening, 2) + " in 2030"; }), links: [site("dashboard/index.html#/capacity", "Open the Capacity gap")], src: "site_data.js (capacity_gap_sector.csv)" });
    }
    var d = !isDef && M && districtIn(M, q);
    if (d) {
      var vals = M.values[d.c], si = M.sectors.map(function (s, i) { return q.indexOf(" " + norm(s).trim().slice(0, 5)) >= 0 ? i : -1; }).filter(function (i) { return i >= 0; })[0];
      var sis = si == null ? M.sectors.map(function (_, i) { return i; }) : [si];
      var sum = function (ti, idx) { return sis.reduce(function (a, i) { return a + vals[i][ti][idx]; }, 0); };
      var sName = si == null ? "all sectors" : M.sectors[si];
      return reply(d.n + ", " + d.s + " (" + sName + "):", { list: [0, 1, 2].map(function (ti) { return n(["E", "V", "S"][ti]) + ": " + compact(sum(ti, 0)) + " in " + S.meta.origin_label + ", " + compact(sum(ti, 1)) + " in 12 months, " + compact(sum(ti, 2)) + " in 36 months, " + compact(sum(ti, 3)) + " in 60 months"; }), links: [site("dashboard/index.html#/forecast?district=" + d.c + (si != null ? "&sector=" + encodeURIComponent(M.sectors[si]) : ""), "Open this district on the dashboard")], src: "map_data.js (forecast_rollups.csv.gz)" });
    }
    return null;
  }
  function districtIn(M, q) {
    var hit = M.districts.map(function (d) { return { d: d, n: norm(d.n).trim() }; }).sort(function (a, b) { return b.n.length - a.n.length; }).filter(function (x) { return q.indexOf(" " + x.n + " ") >= 0; })[0];
    return hit ? hit.d : null;
  }

  function suggestions() {
    if (IS_DASH()) {
      var ctx = hashState(), f = ctx.p, sec = f.sector || "Healthcare", st = ["What does this page show?", "Shortage alerts" + (f.state ? " in " + f.state : ""), "Which trades are growing fastest?", "Capacity gap in " + sec, "Demand Index for " + sec + " in " + (f.state || "Kerala")];
      return st;
    }
    return ["What is this project?", "Is the data real?", "How accurate is it?", "What is the capacity gap?"];
  }

  /* ---------- the facts sent with a question when Gemini words the answer ---------- */
  var asText = function (r) { return r.text + (r.list && r.list.length ? "\n- " + r.list.join("\n- ") : ""); };
  function facts(raw, ctx) {
    var q = norm(raw), mode = IS_DASH() ? "dash" : "pub", out = [];
    KB.forEach(function (e) { if (e.fact === false || (e.when && e.when !== mode)) return; try { out.push(asText(e.a())); } catch (x) { /* skip an entry that has no data here */ } });
    if (IS_DASH()) {
      var D = DX(); ctx = ctx || hashState();
      var e = entities(q, ctx), h = horizonOf(q), f = ctx.p || {};
      out.unshift("The visitor is on the dashboard page '" + ctx.page + "' (" + PAGE_HELP[ctx.page] + ") with filters: sector " + (f.sector || "all") + ", trade " + (f.trade || "all") + ", state " + (f.state || "all") + ", district " + (f.district || "all") + ". Forecast made from " + ml(D.meta.origin) + "; data is simulated.");
      out.push("The page descriptions: " + Object.keys(PAGE_HELP).map(function (k) { return cap(k) + ": " + PAGE_HELP[k]; }).join(" "));
      var add = function (fn) { try { var r = fn(); if (r) out.push(asText(r)); } catch (x) { /* skip */ } };
      add(function () { return valueReply(D, " employed vacancies seekers ", e, h); });
      add(function () { return indexReply(D, e, h); });
      add(function () { return capacityReply(D, e, h); });
      add(function () { return alertsReply(D, "", e, h); });
      add(function () { return rankingReply(D, " fastest ", e); });
    } else {
      var add2 = function (fn) { try { var r = fn(); if (r) out.push(asText(r)); } catch (x) { /* skip */ } };
      add2(function () { return pubAnswer(raw, " india total employed vacancies seekers forecast "); });
      add2(function () { return pubAnswer(raw, " capacity "); });
      add2(function () { return pubAnswer(raw, q); });
      if (typeof document !== "undefined") {
        var hs = Array.prototype.map.call(document.querySelectorAll("main h2"), function (n) { return n.textContent.trim(); });
        out.unshift("The visitor is on the page '" + document.title + "'. Its sections: " + hs.join("; ") + ".");
      }
    }
    return out.join("\n\n").slice(0, 7800);
  }

  /* ---------- search the page text (public site fallback) ---------- */
  var STOP = " what which where when does this that with from have about into your their there would could should please tell show give more than then them also been being were will the and for are you can how why who whom ";
  function pageHits(q) {
    if (typeof document === "undefined") return [];
    var words = q.trim().split(" ").filter(function (w) { return w.length > 3 && STOP.indexOf(" " + w + " ") < 0; });
    if (!words.length) return [];
    var out = [];
    Array.prototype.forEach.call(document.querySelectorAll("main h2, main h3"), function (h) {
      var sec = h.closest("section[id], [id]"), id = (h.id || (sec && sec.id) || ""), nxt = h.nextElementSibling, body = h.textContent + " " + (nxt ? nxt.textContent : ""), t = norm(body), score = 0;
      words.forEach(function (w) { if (t.indexOf(" " + w.slice(0, Math.max(4, w.length - 2))) >= 0) score++; });
      if (score && id) out.push({ score: score, label: h.textContent.trim(), href: "#" + id });
    });
    return out.sort(function (a, b) { return b.score - a.score; }).slice(0, 3);
  }

  /* ---------- the engine ---------- */
  function answer(raw, ctx) {
    var q = norm(raw);
    if (q.trim().length < 2) return reply("Ask me about the project, the data or the forecasts.", { chips: suggestions() });
    if (IS_DASH()) { var d = dashAnswer(raw, q, ctx || hashState()); if (d) return d; }
    else { var p = pubAnswer(raw, q); if (p) return p; }
    var mode = IS_DASH() ? "dash" : "pub", best = null, bestScore = 0;
    KB.forEach(function (e) {
      if (e.when && e.when !== mode) return;
      var sc = 0; e.k.forEach(function (w) { if (q.indexOf(" " + w) >= 0 || (w.slice(-1) === " " && q.indexOf(" " + w) >= 0)) sc += w.length > 6 ? 2 : 1; });
      if (sc > bestScore) { bestScore = sc; best = e; }
    });
    if (best) return best.a();
    var hits = pageHits(q);
    if (hits.length) return reply("I do not have a direct answer, but these parts of this page may help:", { links: hits.map(function (h) { return { label: h.label, href: h.href }; }) });
    return reply("I cannot answer that. I can explain the project, the data, the accuracy, the Demand Index, the capacity gap and the flags" + (IS_DASH() ? ", and look up figures such as employed workers, vacancies, seekers, seats against openings and shortage alerts for a sector, trade, state or district." : ", and look up India's totals or a district's forecast."), { chips: suggestions() });
  }

  var api = { answer: answer, suggestions: suggestions, hashState: hashState, facts: facts, AI: AI };
  root.LmisChat = api;
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  if (typeof document === "undefined") return;

  /* ---------- the window ---------- */
  var KEY = "lmis-chat", API = BASE + "api/chat", msgs = [], open = false, fab, panel, log, input, chipsEl, subEl, noteEl, aiBtn, busy = false;
  function store() { try { sessionStorage.setItem(KEY, JSON.stringify({ open: open, ai: AI.on, msgs: msgs.slice(-40) })); } catch (e) { /* the chat still works */ } }
  function load() { try { var d = JSON.parse(sessionStorage.getItem(KEY) || "{}"); msgs = Array.isArray(d.msgs) ? d.msgs : []; open = !!d.open; AI.on = d.ai !== false; } catch (e) { msgs = []; } }
  function paint() {
    if (!subEl) return;
    subEl.textContent = aiOn() ? "AI answers by Gemini, from this site's own data." : AI.enabled ? "AI is off: answers come from this site's own data, in your browser." : "Answers from this site's own data. Runs in your browser.";
    noteEl.textContent = aiOn() ? "Your question and a summary of this page's data are sent to Google Gemini through this site's server. Answers can be wrong; check figures on the dashboard." : "";
    noteEl.hidden = !aiOn(); aiBtn.hidden = !AI.enabled; aiBtn.setAttribute("aria-pressed", String(AI.on)); aiBtn.textContent = AI.on ? "AI on" : "AI off";
  }
  function probe() {
    if (typeof fetch !== "function" || !/^https?:/.test(API)) return;
    var ctl = new AbortController(), t = setTimeout(function () { ctl.abort(); }, 4000);
    fetch(API, { headers: { Accept: "application/json" }, signal: ctl.signal }).then(function (r) { return r.ok && /json/.test(r.headers.get("content-type") || "") ? r.json() : null; })
      .then(function (j) { clearTimeout(t); if (j && j.enabled === true) { AI.enabled = true; AI.model = String(j.model || ""); } paint(); }).catch(function () { clearTimeout(t); });
  }
  var AI_ERR = { rate: "You are asking quickly; please wait a minute.", daily_cap: "The assistant has reached its daily limit.", upstream_quota: "The AI service is busy right now.", upstream_auth: "The AI service is not set up correctly.", model_not_found: "The AI model is not available.", timeout: "The AI service did not answer in time.", blocked: "The AI service did not answer that question." };
  function aiText(t) {      // Gemini sometimes sends markdown: keep paragraphs and hyphen lists, drop the emphasis marks
    var lines = String(t).replace(/\*\*|__|`/g, "").split(/\n+/), text = [], list = [];
    lines.forEach(function (l) { var m = l.match(/^\s*(?:[-*\u2022]|\d+[.)])\s+(.*)$/); if (m) list.push(m[1].trim()); else if (l.trim()) { if (list.length) list.push(l.trim()); else text.push(l.trim()); } });
    return { text: text.join(" "), list: list };
  }
  function askAI(question, local) {
    var hist = msgs.slice(0, -1).slice(-12).map(function (m) { return { role: m.me ? "user" : "model", text: m.text + (m.list && m.list.length ? " " + m.list.join("; ") : "") }; });
    var ctx = IS_DASH() ? hashState() : null, ctl = new AbortController(), t = setTimeout(function () { ctl.abort(); }, 28000);
    return fetch(API, { method: "POST", headers: { "Content-Type": "application/json" }, signal: ctl.signal,
      body: JSON.stringify({ question: question, history: hist, facts: facts(question, ctx), draft: asText(local), page: IS_DASH() ? "dashboard " + hashState().page : document.title }) })
      .then(function (r) { return r.json().catch(function () { return { ok: false, error: "upstream" }; }); }).then(function (j) { clearTimeout(t); return j; });
  }
  function node(tag, cls, text) { var n = document.createElement(tag); if (cls) n.className = cls; if (text != null) n.textContent = text; return n; }
  function render(m) {
    var row = node("div", "lc-msg " + (m.me ? "me" : "bot"));
    if (m.me) { row.textContent = m.text; return row; }
    row.appendChild(node("p", "", m.text));
    if (m.list && m.list.length) { var ul = node("ul"); m.list.forEach(function (t) { ul.appendChild(node("li", "", t)); }); row.appendChild(ul); }
    if (m.links && m.links.length) { var lw = node("div", "lc-links"); m.links.forEach(function (l) { var a = node("a", "", l.label); a.href = l.href; if (l.href.charAt(0) === "#" && IS_DASH()) a.addEventListener("click", function () { if (window.matchMedia("(max-width: 560px)").matches) toggle(false); }); lw.appendChild(a); }); row.appendChild(lw); }
    if (m.src) row.appendChild(node("small", "", "Source: " + m.src));
    return row;
  }
  function chipRow(list) { chipsEl.textContent = ""; (list || []).forEach(function (t) { var b = node("button", "lc-chip", t); b.type = "button"; b.addEventListener("click", function () { ask(t); }); chipsEl.appendChild(b); }); }
  function push(m) { msgs.push(m); log.appendChild(render(m)); log.scrollTop = log.scrollHeight; store(); }
  function ask(text) {
    text = String(text).trim(); if (!text || busy) return;
    push({ me: true, text: text }); input.value = ""; chipRow([]);
    var r; try { r = answer(text, IS_DASH() ? hashState() : null); } catch (e) { r = reply("Something went wrong while looking that up.", {}); if (window.console) console.error(e); }
    var local = function (note) { push({ text: r.text, list: r.list, links: r.links, src: r.src + (note ? (r.src ? " · " : "") + note : "") }); chipRow(r.chips && r.chips.length ? r.chips : []); };
    if (!aiOn()) return local("");
    busy = true; var wait = node("div", "lc-msg bot lc-wait", "Thinking…"); log.appendChild(wait); log.scrollTop = log.scrollHeight;
    askAI(text, r).then(function (j) {
      busy = false; wait.remove();
      if (j && j.ok && j.text) { var a = aiText(j.text); push({ text: a.text || j.text, list: a.list, links: r.links, src: "Gemini" + (j.model ? " (" + j.model + ")" : "") + ", from this site's data" }); chipRow([]); }
      else local((AI_ERR[j && j.error] || "The AI service is unavailable") + " Answered from this site's own data.");
    }).catch(function () { busy = false; wait.remove(); local("The AI service is unavailable. Answered from this site's own data."); });
  }
  function toggle(force) {
    open = force == null ? !open : force; panel.hidden = !open; fab.setAttribute("aria-expanded", String(open)); fab.classList.toggle("on", open); store();
    if (open) { if (!msgs.length) { push({ text: aiOn() ? "Hello. I answer from this site's own " + (IS_DASH() ? "pages and forecast data" : "pages and data") + ", using Google's Gemini to word the answer. Your question and a summary of the page's data are sent to Google through this site's server; switch AI off above to keep everything in your browser." : "Hello. I answer from this site's own " + (IS_DASH() ? "pages and forecast data" : "pages and data") + ". I am not a language model and nothing you type leaves your browser.", list: [], links: [], src: "" }); chipRow(suggestions()); } setTimeout(function () { input.focus(); }, 30); }
  }
  function build() {
    var wrap = node("div", "lc-root"); wrap.setAttribute("lang", "en"); wrap.setAttribute("translate", "no");
    fab = node("button", "lc-fab"); fab.type = "button"; fab.setAttribute("aria-label", "Ask the assistant"); fab.setAttribute("aria-expanded", "false"); fab.setAttribute("aria-controls", "lc-panel");
    fab.innerHTML = '<svg class="i-chat" viewBox="0 0 24 24" aria-hidden="true"><path d="M5 5h14a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2h-7l-4.500 3.500V17H5a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2z"/><path d="M8 10h8M8 13h5"/></svg><svg class="i-x" viewBox="0 0 24 24" aria-hidden="true"><path d="M6 6l12 12M18 6L6 18"/></svg>';
    panel = node("section", "lc-panel"); panel.id = "lc-panel"; panel.hidden = true; panel.setAttribute("role", "dialog"); panel.setAttribute("aria-label", "KaushalSetu assistant");
    var head = node("header", "lc-head"), t = node("div"); t.appendChild(node("b", "", "Ask KaushalSetu")); subEl = node("span", "", ""); t.appendChild(subEl);
    var clear = node("button", "lc-clear", "Clear"); clear.type = "button"; clear.addEventListener("click", function () { msgs = []; log.textContent = ""; store(); toggle(true); });
    aiBtn = node("button", "lc-clear lc-ai", "AI on"); aiBtn.type = "button"; aiBtn.hidden = true; aiBtn.title = "Use Google Gemini to word the answers (your question is sent to Google through this site's server)";
    aiBtn.addEventListener("click", function () { AI.on = !AI.on; paint(); store(); });
    var tools = node("div", "lc-tools"); tools.appendChild(aiBtn); tools.appendChild(clear);
    head.appendChild(t); head.appendChild(tools);
    log = node("div", "lc-log"); log.setAttribute("role", "log"); log.setAttribute("aria-live", "polite"); chipsEl = node("div", "lc-chips");
    var form = node("form", "lc-form"); input = node("input"); input.type = "text"; input.placeholder = IS_DASH() ? "Ask about a district, sector or flag" : "Ask about the project"; input.setAttribute("aria-label", "Your question"); input.autocomplete = "off"; input.maxLength = 200;
    var send = node("button", "lc-send", "Send"); send.type = "submit"; form.appendChild(input); form.appendChild(send);
    form.addEventListener("submit", function (ev) { ev.preventDefault(); ask(input.value); });
    panel.addEventListener("keydown", function (ev) { if (ev.key === "Escape") { toggle(false); fab.focus(); } });
    noteEl = node("p", "lc-note", ""); noteEl.hidden = true;
    panel.appendChild(head); panel.appendChild(log); panel.appendChild(chipsEl); panel.appendChild(noteEl); panel.appendChild(form);
    wrap.appendChild(panel); wrap.appendChild(fab); document.body.appendChild(wrap); document.documentElement.classList.add("lc-on");
    fab.addEventListener("click", function () { toggle(); });
    load(); paint(); probe(); msgs.forEach(function (m) { log.appendChild(render(m)); }); log.scrollTop = log.scrollHeight;
    if (open) { panel.hidden = false; fab.setAttribute("aria-expanded", "true"); fab.classList.add("on"); chipRow(msgs.length > 1 ? [] : suggestions()); } else chipRow([]);
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", build); else build();
})(typeof window !== "undefined" ? window : globalThis);
