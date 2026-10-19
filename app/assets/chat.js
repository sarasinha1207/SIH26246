/* KaushalSetu assistant: one floating chat window for the public site and the dashboard.
   The site's own engine (LmisChat.answer) answers from what is already on the page: on the dashboard from window.DASH (the forecast_long.csv and
   flags.csv data), on the public site from window.SITE_DATA and the page text. When the server has a Gemini key (GET api/chat says enabled), the window
   also sends the question and a text summary of those same facts (LmisChat.facts) to api/chat, and Gemini words the answer from them. The key lives on the
   server only. If the server, the key or the network is missing, the engine's own answer is shown instead. The engine has no DOM code, so it runs under node. */
(function (root) {
  "use strict";
  var IS_DASH = function () { return !!root.DASH; };
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
  function counts() {
    var D = root.DASH, M = root.SITE_DATA && root.SITE_DATA.meta;
    if (D) { var d = {}; D.series.forEach(function (s) { d[s.code] = 1; }); return { series: D.series.length, districts: Object.keys(d).length, states: D.meta.states.length, sectors: D.meta.sectors.length, sectorList: D.meta.sectors, stateList: D.meta.states }; }
    if (M) return { series: M.series, districts: M.districts, states: M.states, sectors: M.sectors, sectorList: M.sector_list || [], stateList: M.state_list || [] };
    return null;
  }
  var join = function (a) { return a.length > 1 ? a.slice(0, -1).join(", ") + " and " + last(a) : a.join(""); };

  function accuracyReply() {
    var A = root.SITE_DATA && root.SITE_DATA.accuracy && root.SITE_DATA.accuracy.original, D = root.DASH, names = { E: "Employed workers", V: "Job vacancies", S: "Registered job seekers" };
    if (A) {
      var rows = ["E", "V", "S"].map(function (k) { var gain = (A[k].baseline - A[k].model) / A[k].baseline * 100; return { k: k, gain: gain, line: names[k] + ": typical error " + A[k].model + "% against " + A[k].baseline + "% for a simple baseline (" + A[k].baseline_name.toLowerCase() + "), " + Math.round(gain) + "% better." }; });
      var least = rows.slice().sort(function (a, b) { return a.gain - b.gain; })[0];
      return reply("Accuracy was measured once, on a test period the model never saw (" + A.label.toLowerCase().replace("test period ", "") + "). The error is WAPE, the size of the misses as a share of the actual values.",
        { list: rows.map(function (r) { return r.line; }).concat([names[least.k] + " gains the least over the baseline, so treat that forecast with the most caution."]), links: [site("about.html#evaluation", "Model evaluation")], src: "site_data.js (reports/evaluation)" });
    }
    if (D) {
      var med = function (a) { var b = a.slice().sort(function (x, y) { return x - y; }); return b[Math.floor(b.length / 2)]; };
      return reply("The typical test error is a column of forecast_long.csv. For the 12-month forecasts, the middle value across all series is:", { list: ["E", "V", "S"].map(function (k) { return names[k] + ": " + fmt(med(D.fc[k].err.map(function (r) { return r[11]; })), 1) + "% (" + D.meta.manifest.confidence_rules[{ E: "employed", V: "vacancies", S: "seekers" }[k]].split(";")[0] + " confidence)"; }), links: [dashLink("data", {}, "Data and notes")], src: "forecast_long.csv" });
    }
    return reply("The model is scored on held-out data. See the model evaluation section of the About page for the figures.", { links: [site("about.html#evaluation", "Model evaluation")] });
  }

  var KB = [
    { k: ["what is this", "about the project", "about this", "what does this", "what do you do", "purpose", "tell me about", "overview of", "lmis", "project", "what is lmis"], a: function () {
      var c = counts(), n = c ? " for " + c.districts + " districts in " + c.states + " states and " + c.sectors + " sectors (" + c.series + " series)" : "";
      return reply("KaushalSetu forecasts three things for the next twelve months" + n + ": how many people are employed, how many jobs are open and how many job seekers are registered. It also flags where the demand for workers and the supply of job seekers are drifting apart, early enough to act on it.", { links: [site("about.html", "About the project"), site("dashboard/index.html", "Open the dashboard")] }); } },
    { k: ["real", "simulated", "synthetic", "official", "fake", "genuine", "demo", "actual data", "true data"], a: function () {
      return reply("No. Every figure is simulated for demonstration. It behaves like official statistics but describes no real district, and it is not an official statistic.", { links: [site("resources.html#datasets", "Data sources")] }); } },
    { k: ["sector", "state", "district", "covered", "coverage", "which places", "where"], when: "pub", a: function () {
      var c = counts();
      return reply(c && c.sectorList.length ? "The data covers " + c.districts + " districts in " + join(c.stateList) + ", across " + c.sectors + " sectors: " + join(c.sectorList) + "." : "The dataset section of the About page lists the states, districts and sectors.", { links: [site("index.html#map", "District map"), site("about.html#dataset", "Dataset used")] }); } },
    { k: ["accura", "error", "wape", "how good", "reliable", "trust", "baseline", "evaluat", "performance", "test result"], a: function () { return accuracyReply(); } },
    { k: ["confidence", "how sure", "uncertain", "interval", "range", "90%", "band"], a: function () {
      var D = root.DASH, r = D ? D.meta.manifest.confidence_rules : null;
      return reply("Every forecast carries a confidence label earned in testing" + (r ? ": employed workers " + r.employed + "; job seekers " + r.seekers + "; vacancies " + r.vacancies + "." : ": employed workers high, job seekers medium, job vacancies low.") + " The shaded 90% range on a chart is the lo90 to hi90 pair from the forecast file, built to hold about nine in ten outcomes.", { src: D ? "manifest.json, forecast_long.csv" : "" }); } },
    { k: ["how does", "how is", "how are", "how do you", "method", "model", "xgboost", "machine learning", "algorithm", "train", "forecast made", "engine", "architecture", "seeds"], a: function () {
      var D = root.DASH;
      return reply("A separate gradient-boosted tree model (XGBoost) is trained for each measure, with several random seeds averaged. Features come from each series' own history and calendar. The models are tuned on a validation period and scored once on a held-out test period, then refitted on all data to make the forecast." + (D ? " This forecast was made with " + D.meta.model + " from " + D.meta.origin_label + "." : ""), { links: [site("about.html#engine", "Machine learning engine"), site("about.html#timeline", "How it works")] }); } },
    { k: ["relative status", "tightest", "decile", "percentile", "relative"], a: function () {
      var D = root.DASH;
      return reply("Relative status compares a district with the other districts of its own sector in the same month: " + (D ? D.meta.status.join(", ").toLowerCase() : "tightest decile, tight, typical, loose, loosest decile") + ". It always sorts some districts to the top, so it is shown beside the absolute context, which says whether openings really exceed seekers.", { src: D ? "flags.csv" : "" }); } },
    { k: ["absolute context", "openings exceed", "oversupplied", "deep surplus", "moderate", "per 100"], a: function () {
      var D = root.DASH, t = D && D.meta.thresholds, p = function (x) { return fmt(x * 100, 0); };
      return reply(t ? "Absolute context comes from vacancies divided by registered seekers: openings exceed seekers (" + p(t.exceed) + " or more openings per 100 seekers), moderate (" + p(t.moderate) + " to " + p(t.exceed) + "), oversupplied (" + p(t.oversupplied) + " to " + p(t.moderate) + ") and deep surplus (under " + p(t.oversupplied) + ")." : "Absolute context comes from vacancies divided by registered seekers: openings exceed seekers, moderate, oversupplied or deep surplus.", { src: t ? "flags.csv" : "" }); } },
    { k: ["alert", "watch", "flag", "early warning", "early-warning", "warning"], a: function () {
      var D = root.DASH, lk = D ? dashLink("warnings", {}, "Open Early warnings") : site("dashboard/index.html#/warnings", "Early warnings on the dashboard");
      return reply("An early-warning flag says a district is drifting towards a shortage of workers or a surplus of them. Within a sector, the tightest or loosest decile of districts is an alert and the tight or loose class beside it is a watch. Flags are the weakest part of the model, so they carry low confidence.", { links: [lk], src: D ? "flags.csv, manifest.json" : "" }); } },
    { k: ["dashboard", "open the dash", "where can i see"], when: "pub", a: function () {
      return reply("The dashboard has seven pages: Overview, Demand, Supply, Gap, District ranking, Early warnings, and Data and notes. Filters for sector, state and district stay in the address, and any view can be downloaded as CSV.", { links: [site("dashboard/index.html", "Open the dashboard")] }); } },
    { k: ["data source", "where from", "where does the data", "dataset", "columns", "variables", "resource", "acquired", "download data"], when: "pub", a: function () {
      return reply("The Resources page lists the data behind the project and the websites it was modelled on, and the About page describes the dataset and its columns.", { links: [site("resources.html#datasets", "Data used"), site("about.html#dataset", "Dataset details")] }); } },
    { k: ["language", "hindi", "text size", "font", "dark", "light", "theme", "display"], when: "pub", a: function () {
      return reply("The round Display button in the header sets the text size (A-, A, A+), the theme (light or dark) and the language (English or Hindi). Your choice stays on your device.", {}); } },
    { k: ["map", "zoom"], when: "pub", a: function () {
      return reply("On the home page the map shows every forecast district. Hover or tap a district for its details, use the state buttons to zoom to a state, and the plus, minus and reset controls to move around. Districts in pale outline have no forecast data.", { links: [site("index.html#map", "Go to the map")] }); } },
    { k: ["cookie", "privacy", "track", "analytics", "contact", "email", "feedback", "personal"], a: function () {
      return reply("The site sets no cookies and has no analytics. " + (aiOn() ? "When AI answers are on, your question and a summary of this page's data are sent to Google's Gemini through this site's server so it can word the answer; the site does not store them. Switch AI off in the chat window to keep everything in your browser." : "This assistant runs entirely in your browser: what you type is not sent anywhere.") + " To reach the team, write to feedback@lmis-demo.example.", {}); } },
    { k: ["limit", "weak", "caveat", "cannot", "can't", "problem", "not good", "wrong"], a: function () {
      return reply("Three limits matter most: the data is simulated; vacancy forecasts add little over a simple baseline, so they are marked low confidence; and the early-warning flags are the weakest part of the model.", { links: [site("about.html#evaluation", "Model evaluation")] }); } },
    { fact: false, k: ["who are you", "are you ai", "are you a bot", "chatbot", "are you real", "language model", "gpt", "claude", "gemini"], a: function () {
      return reply(aiOn() ? "I am the assistant built into this site. I use Google's Gemini to word my answers, but only from this site's own pages and forecast data; I cannot look anything up elsewhere, and I can be wrong, so check figures on the dashboard." : "I am a small assistant built into this site. I am not a language model: I answer from the site's own pages and data, and I cannot look anything up elsewhere.", {}); } },
    { fact: false, k: ["hello", "hi ", "hey", "namaste", "good morning", "good evening"], a: function () { return reply("Hello. What would you like to know?", { chips: suggestions() }); } },
    { fact: false, k: ["thank"], a: function () { return reply("You are welcome.", {}); } },
    { fact: false, k: ["help", "what can you", "what can i ask", "options"], a: function () { return reply("You can ask me about the project, the data, how accurate the forecasts are and what the flags mean." + (IS_DASH() ? " On the dashboard I can also look up figures: for example, shortage alerts in Healthcare, the tightest districts in Construction, or the forecast for Pune in Manufacturing." : ""), { chips: suggestions() }); } }
  ];

  /* ---------- the dashboard: questions answered from window.DASH ---------- */
  var PAGE_HELP = {
    overview: "Four KPIs, the district map coloured by absolute context, openings against seekers over time, the early-warning summary, coverage by sector and a sector table. Click a district or a sector to filter every page.",
    demand: "Employed workers and job vacancies with their forecasts, plus the average wage and the unemployment rate (history only).",
    supply: "Registered job seekers with the e-Shram break marked, and training seats against certified trainees.",
    gap: "Coverage (openings per 100 seekers) and the net gap over time, and coverage by sector.",
    ranking: "The districts of one sector ranked by forecast coverage, with relative status always beside absolute context. Small-count series are greyed.",
    warnings: "Shortage and oversupply flags, alert and watch, for 3, 6 or 12 months ahead.",
    data: "Coverage of the dataset, caveats, definitions, where the numbers come from, and the CSV downloads."
  };
  var PAGE_NAMES = { overview: ["overview", "home"], demand: ["demand"], supply: ["supply"], gap: ["gap", "coverage page"], ranking: ["ranking", "rank page"], warnings: ["warnings", "early warnings", "alerts page"], data: ["data and notes", "notes"] };

  function hashState() {
    var h = (root.location ? root.location.hash : "").replace(/^#\/?/, ""), q = h.split("?"), p = {};
    (q[1] || "").split("&").forEach(function (kv) { if (!kv) return; var a = kv.split("="); try { p[decodeURIComponent(a[0])] = decodeURIComponent((a[1] || "").replace(/\+/g, " ")); } catch (e) { /* skip */ } });
    return { page: PAGE_HELP[q[0]] ? q[0] : "overview", p: p };
  }
  function dashLink(page, f, label) {
    var parts = [];
    ["sector", "state", "district", "h", "t", "lv"].forEach(function (k) { if (f && f[k] !== "" && f[k] != null) parts.push(k + "=" + encodeURIComponent(f[k])); });
    return { label: label, href: "#/" + page + (parts.length ? "?" + parts.join("&") : "") };
  }

  function entities(qraw, ctx) {
    var D = root.DASH, q = qraw, out = { sector: "", state: "", district: "", said: {} };
    // district: whole name first, then an unambiguous first word
    var dist = {};
    D.series.forEach(function (s) { dist[s.code] = s; });
    var names = Object.keys(dist).map(function (c) { return { c: c, n: norm(dist[c].district).trim(), s: dist[c].state }; }).sort(function (a, b) { return b.n.length - a.n.length; });
    var hit = names.filter(function (d) { return q.indexOf(" " + d.n + " ") >= 0; })[0];
    if (hit) { out.district = hit.c; out.said.district = true; q = q.replace(" " + hit.n + " ", " "); }
    else {
      var words = {}, reserved = " north south east west central new city rural urban " + D.meta.states.concat(D.meta.sectors).map(function (x) { return norm(x); }).join(" ") + " ";
      names.forEach(function (d) { var w = d.n.split(" ")[0]; if (w.length > 3 && reserved.indexOf(" " + w + " ") < 0) (words[w] = words[w] || []).push(d); });
      var found = Object.keys(words).filter(function (w) { return q.indexOf(" " + w + " ") >= 0; });
      if (found.length) { var cand = words[found[0]]; if (cand.length === 1) { out.district = cand[0].c; out.said.district = true; } else out.ambiguous = cand.map(function (d) { return dist[d.c].district; }); }
    }
    D.meta.states.forEach(function (st) {
      var n = norm(st), parts = n.trim().split(" ").filter(function (w) { return w.length >= 5; });
      if (q.indexOf(n) >= 0 || parts.some(function (w) { return q.indexOf(" " + w) >= 0; })) { out.state = st; out.said.state = true; }
    });
    D.meta.sectors.forEach(function (sec) {
      var n = norm(sec).trim(), stem = n.split(/[ \-]/)[0];
      var it = n.indexOf("it-ites") === 0 ? any(q, ["it-ites", "ites", "=it sector", "in it ", "for it ", "=it industry", "information tech"]) : false;
      if (it || (n.indexOf("it-ites") !== 0 && stem.length >= 5 && q.indexOf(" " + stem.slice(0, 5)) >= 0) || (n.indexOf("textiles") === 0 && any(q, ["apparel", "garment"]))) { out.sector = sec; out.said.sector = true; }
    });
    if (out.district) out.state = dist[out.district].state;
    // what the page filters say, for whatever the question did not name
    var f = (ctx && ctx.p) || {};
    if (!out.said.sector && f.sector) out.sector = f.sector;
    if (!out.said.state && !out.said.district) { if (f.state) out.state = f.state; if (f.district && dist[f.district]) { out.district = f.district; out.state = dist[f.district].state; } }
    return out;
  }
  function horizonOf(q) {
    var m = q.match(/(\d{1,2})\s*-?\s*months?/);
    if (m && +m[1] >= 1 && +m[1] <= 12) return +m[1];
    if (any(q, ["next month"])) return 1;
    if (any(q, ["quarter", "three months"])) return 3;
    if (any(q, ["half year", "six months"])) return 6;
    return 12;
  }
  var inScope = function (D, e, ignore) {
    var out = [];
    D.series.forEach(function (s, i) { if (e.sector && s.sector !== e.sector && ignore !== "sector") return; if (e.state && s.state !== e.state) return; if (e.district && s.code !== e.district) return; out.push(i); });
    return out;
  };
  var scopeName = function (D, e) { var d = e.district ? D.series.filter(function (s) { return s.code === e.district; })[0].district : ""; return [d || e.state || "all states", e.sector || "all sectors"].join(", "); };
  var urlFilters = function (e) { return { sector: e.sector, state: e.district ? "" : e.state, district: e.district }; };
  function sumAt(D, k, idx, kind, h) { var t = 0; idx.forEach(function (i) { t += kind === "hist" ? last(D.hist[k][i]) : D.fc[k].f[i][h - 1]; }); return t; }
  function confWord(D, k, idx) { var c = {}; idx.forEach(function (i) { c[D.fc[k].conf[i]] = 1; }); var ks = Object.keys(c); return ks.length === 1 ? ks[0] : "mixed"; }

  function alertsReply(D, q, e, h) {
    var idx = inScope(D, e), want = any(q, ["oversupply", "surplus", "too many seekers"]) ? "oversupply" : any(q, ["shortage", "scarce", "not enough workers", "tight"]) ? "shortage" : "", lv = any(q, ["alert"]) && !any(q, ["watch"]) ? "alert" : any(q, ["watch"]) && !any(q, ["alert"]) ? "watch" : "";
    var rows = [], c = { "shortage alert": 0, "shortage watch": 0, "oversupply alert": 0, "oversupply watch": 0 };
    idx.forEach(function (i) { var f = D.fl[i][h - 1], k = D.meta.flag_class[f[1]]; if (!k) return; c[k.join(" ")]++; if ((!want || k[0] === want) && (!lv || k[1] === lv)) rows.push({ i: i, k: k, f: f }); });
    rows.sort(function (a, b) { return (a.k[1] === b.k[1] ? 0 : a.k[1] === "alert" ? -1 : 1) || Math.abs(b.f[0] - 50) - Math.abs(a.f[0] - 50); });
    var shown = rows.slice(0, 5);
    return reply(h + " months ahead, for " + scopeName(D, e) + ": " + c["shortage alert"] + " shortage alerts, " + c["shortage watch"] + " shortage watches, " + c["oversupply alert"] + " oversupply alerts and " + c["oversupply watch"] + " oversupply watches." + (rows.length ? " The " + (rows.length > 5 ? "five most extreme " : "") + (want ? want + " " : "") + (lv ? lv + (rows.length === 1 ? "" : "s") : "flags") + ":" : " Nothing is flagged that way."),
      { list: shown.map(function (r) { var s = D.series[r.i]; return s.district + ", " + s.sector + ": " + r.k.join(" ") + ", " + D.meta.status[r.f[1]].toLowerCase() + " (" + ord(r.f[0]) + " percentile), " + D.meta.context[r.f[2]] + (s.low ? " (very small counts)" : ""); }),
        links: [dashLink("warnings", Object.assign(urlFilters(e), { h: [3, 6, 12].indexOf(h) >= 0 ? h : 12, t: want, lv: lv }), "Open in Early warnings")], src: "flags.csv" });
  }
  function rankingReply(D, q, e, h) {
    if (!e.sector) return reply("Rankings are within one sector. Which sector: " + join(D.meta.sectors) + "?", { chips: D.meta.sectors.slice(0, 3).map(function (s) { return "Tightest districts in " + s; }) });
    var asc = any(q, ["loosest", "lowest", "least", "most surplus", "most oversupplied", "worst", "bottom"]);
    var rows = [];
    D.series.forEach(function (s, i) { if (s.sector === e.sector) { var f = D.fl[i][h - 1]; rows.push({ i: i, f: f }); } });
    rows.sort(function (a, b) { return b.f[0] - a.f[0]; }); rows.forEach(function (r, k) { r.rank = k + 1; });
    var pool = rows.filter(function (r) { return (!e.state || D.series[r.i].state === e.state); });
    if (asc) pool = pool.slice().reverse();
    return reply((asc ? "Loosest" : "Tightest") + " districts in " + e.sector + (e.state ? ", " + e.state : "") + ", " + h + " months ahead (rank among " + rows.length + " districts; rank 1 has the most openings per seeker):",
      { list: pool.slice(0, 5).map(function (r) { var s = D.series[r.i]; return "#" + r.rank + " " + s.district + " (" + s.state + "): " + D.meta.status[r.f[1]].toLowerCase() + ", " + fmt(r.f[6] * 100, 1) + " openings per 100 seekers, " + D.meta.context[r.f[2]] + (s.low ? " (very small counts)" : ""); }),
        links: [dashLink("ranking", { sector: e.sector, state: e.state, h: [3, 6, 12].indexOf(h) >= 0 ? h : 12 }, "Open the ranking")], src: "flags.csv" });
  }
  function coverageReply(D, e, h) {
    var idx = inScope(D, e); if (!idx.length) return reply("There is no series for that combination.", {});
    var V0 = sumAt(D, "V", idx, "hist"), S0 = sumAt(D, "S", idx, "hist"), V1 = sumAt(D, "V", idx, "fc", h), S1 = sumAt(D, "S", idx, "fc", h), t = D.meta.thresholds;
    var ctx = function (r) { return D.meta.context[r >= t.exceed ? 0 : r >= t.moderate ? 1 : r >= t.oversupplied ? 2 : 3]; };
    return reply("For " + scopeName(D, e) + ": " + fmt(V0 / S0 * 100, 1) + " openings per 100 registered seekers now (" + ctx(V0 / S0) + "), and " + fmt(V1 / S1 * 100, 1) + " in " + h + " months (" + ctx(V1 / S1) + "). Vacancies " + compact(V0) + ", seekers " + compact(S0) + ". Vacancy forecasts carry " + confWord(D, "V", idx) + " confidence.",
      { links: [dashLink("gap", urlFilters(e), "Open the Gap page")], src: "panel_monthly.parquet, forecast_long.csv" });
  }
  function valueReply(D, q, e, h) {
    var idx = inScope(D, e); if (!idx.length) return reply("There is no series for that combination.", {});
    var ks = [];
    if (any(q, ["employ", "worker", "job holder"])) ks.push("E");
    if (any(q, ["vacanc", "opening", "job open", "demand"])) ks.push("V");
    if (any(q, ["seeker", "supply", "registered", "unemploy", "looking for"])) ks.push("S");
    if (!ks.length) ks = ["E", "V", "S"];
    var name = { E: "Employed workers", V: "Job vacancies", S: "Registered job seekers" }, one = idx.length === 1 ? idx[0] : -1, list = [];
    ks.forEach(function (k) {
      var a = sumAt(D, k, idx, "hist"), b = sumAt(D, k, idx, "fc", h), line = name[k] + ": " + compact(a) + " in " + ml(last(D.meta.months)) + ", forecast " + compact(b) + " in " + ml(D.meta.fmonths[h - 1]) + " (" + signed((b / a - 1) * 100) + "), " + confWord(D, k, idx) + " confidence";
      if (one >= 0) line += "; 90% range " + compact(D.fc[k].lo[one][h - 1]) + " to " + compact(D.fc[k].hi[one][h - 1]) + ", typical test error " + fmt(D.fc[k].err[one][h - 1], 1) + "%";
      list.push(line);
    });
    var pg = ks.length === 1 && ks[0] === "S" ? "supply" : "demand";
    return reply("For " + scopeName(D, e) + ":", { list: list.concat(one < 0 ? ["The 90% range is shown only for a single district and sector."] : []), links: [dashLink(pg, urlFilters(e), "Open the " + cap(pg) + " page")], src: "panel_monthly.parquet, forecast_long.csv" });
  }

  function dashAnswer(raw, q, ctx) {
    ctx = ctx || hashState();
    var D = root.DASH, e = entities(q, ctx), h = horizonOf(q);
    if (e.ambiguous) return reply("Which district do you mean: " + join(e.ambiguous) + "?", { chips: e.ambiguous.slice(0, 3) });
    var data = e.said.sector || e.said.state || e.said.district;
    var isDef = any(q, ["what is", "what are", "what does", "mean", "define", "explain"]) && !data;
    if (any(q, ["this page", "current page", "what am i", "where am i", "page show"])) return reply(cap(PAGE_NAMES[ctx.page][0]) + ": " + PAGE_HELP[ctx.page], {});
    var pageHit = Object.keys(PAGE_NAMES).filter(function (p) { return PAGE_NAMES[p].some(function (n) { return q.indexOf(" go to " + n) >= 0 || q.indexOf(" open " + n) >= 0 || q.indexOf(" take me to " + n) >= 0 || q.indexOf(" show " + n) >= 0; }); })[0];
    if (pageHit) return reply(cap(PAGE_NAMES[pageHit][0]) + ": " + PAGE_HELP[pageHit], { links: [dashLink(pageHit, (ctx && ctx.p) || {}, "Go to " + cap(PAGE_NAMES[pageHit][0]))] });
    if (any(q, ["download", "csv", "export", "save"])) return reply("Use Download CSV above the page for the view you are looking at, or the three files on Data and notes (forecasts, flags, history) for the current filters.", { links: [dashLink("data", (ctx && ctx.p) || {}, "Data and notes")] });
    if (any(q, ["filter", "reset", "clear"])) return reply("The Sector, State and District filters sit above every page and are kept in the address, so a view can be shared. Clicking a district on the map or a sector bar sets them too. Reset filters clears all three.", {});
    if (any(q, ["exit", "leave", "log out", "logout", "sign out", "close the dash"])) return reply("Use Exit in the top bar or the sidebar to return to the public site. There is no login.", { links: [{ label: "Back to the website", href: BASE + "index.html" }] });
    if (!isDef && any(q, ["alert", "watch", "shortage", "oversupply", "warning", "flag", "risk"])) return alertsReply(D, q, e, h);
    if (!isDef && any(q, ["rank", "tightest", "loosest", "top ", "highest", "lowest", "worst", "best", "most "])) return rankingReply(D, q, e, h);
    if (!isDef && any(q, ["gap", "coverage", "per 100", "balance", "ratio", "shortfall"])) return coverageReply(D, e, h);
    if (!isDef && (data || any(q, ["forecast", "predict", "expect", "how many", "how much", "latest", "current", "total", "number of"]))) return valueReply(D, q, e, h);
    if (any(q, ["source", "files", "sha", "hash", "origin", "latest forecast", "forecast from"])) return reply("The figures come from forecast_long.csv (forecasts and 90% ranges), flags.csv (early-warning fields) and the monthly panel (history). The forecast was made from " + D.meta.origin_label + " with " + D.meta.model + ".", { links: [dashLink("data", {}, "Where the numbers come from")] });
    return null;
  }

  function suggestions() {
    if (IS_DASH()) {
      var ctx = hashState(), f = ctx.p, sec = f.sector || "Healthcare", st = ["What does this page show?", "Shortage alerts" + (f.sector ? " in " + f.sector : ""), "Tightest districts in " + sec, "What is relative status?"];
      return st;
    }
    return ["What is this project?", "Is the data real?", "How accurate is it?", "What do the flags mean?"];
  }

  /* ---------- the facts sent with a question when Gemini words the answer ---------- */
  var asText = function (r) { return r.text + (r.list && r.list.length ? "\n- " + r.list.join("\n- ") : ""); };
  function facts(raw, ctx) {
    var q = norm(raw), mode = IS_DASH() ? "dash" : "pub", out = [];
    KB.forEach(function (e) { if (e.fact === false || (e.when && e.when !== mode)) return; try { out.push(asText(e.a())); } catch (x) { /* skip an entry that has no data here */ } });
    if (IS_DASH()) {
      var D = root.DASH; ctx = ctx || hashState();
      var e = entities(q, ctx), h = horizonOf(q), f = ctx.p || {};
      out.unshift("The visitor is on the dashboard page '" + ctx.page + "' (" + PAGE_HELP[ctx.page] + ") with filters: sector " + (f.sector || "all") + ", state " + (f.state || "all") + ", district " + (f.district || "all") + ". Question scope: " + scopeName(D, e) + ", " + h + " months ahead.");
      out.push("The page descriptions: " + Object.keys(PAGE_HELP).map(function (k) { return cap(k) + ": " + PAGE_HELP[k]; }).join(" "));
      var add = function (fn) { try { var r = fn(); if (r) out.push(asText(r)); } catch (x) { /* skip */ } };
      add(function () { return valueReply(D, " employed vacancies seekers ", e, h); });
      add(function () { return coverageReply(D, e, h); });
      add(function () { return alertsReply(D, "", e, h); });
      if (e.sector) { add(function () { return rankingReply(D, " tightest ", e, h); }); add(function () { return rankingReply(D, " loosest ", e, h); }); }
    } else if (typeof document !== "undefined") {
      var hs = Array.prototype.map.call(document.querySelectorAll("main h2"), function (n) { return n.textContent.trim(); });
      out.unshift("The visitor is on the page '" + document.title + "'. Its sections: " + hs.join("; ") + ".");
    }
    return out.join("\n\n").slice(0, 7800);
  }

  /* ---------- search the page text (public site fallback) ---------- */
  var STOP = " what which where when does this that with from have about into your their there would could should please tell show give more than then them also been being were will the and for are you can how why who ";
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
    var mode = IS_DASH() ? "dash" : "pub", best = null, bestScore = 0;
    KB.forEach(function (e) {
      if (e.when && e.when !== mode) return;
      var sc = 0; e.k.forEach(function (w) { if (q.indexOf(" " + w) >= 0 || (w.slice(-1) === " " && q.indexOf(" " + w) >= 0)) sc += w.length > 6 ? 2 : 1; });
      if (sc > bestScore) { bestScore = sc; best = e; }
    });
    if (best) return best.a();
    var hits = pageHits(q);
    if (hits.length) return reply("I do not have a direct answer, but these parts of this page may help:", { links: hits.map(function (h) { return { label: h.label, href: h.href }; }) });
    return reply("I cannot answer that. I can explain the project, the data, the accuracy and the flags" + (IS_DASH() ? ", and look up figures such as shortage alerts, the tightest districts of a sector, or the forecast for a district and sector" : "") + ".", { chips: suggestions() });
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
