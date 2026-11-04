/* A small accessibility audit that runs in the page (paste into the browser console, or run through the browser tool).  It reports what can be found by looking at the DOM:
   names of buttons, links, form fields and images, labels of landmarks and charts, heading order, duplicate ids, positive tabindex, mouse-only click handlers on rows,
   text contrast against the background actually behind it (WCAG AA: 4.5 for normal text, 3 for large), and small touch targets.  It does not replace a screen-reader pass.
   Returns an object of lists; every list should be empty. */
(function () {
  var out = { no_name: [], no_label: [], img_no_alt: [], dup_ids: [], heading_jumps: [], positive_tabindex: [], mouse_only_rows: [], low_contrast: [], small_targets: [], no_lang: [], svg_unlabelled: [], table_no_header: [] };
  var vis = function (e) { var r = e.getBoundingClientRect(), s = getComputedStyle(e); return r.width > 0 && r.height > 0 && s.visibility !== "hidden" && s.display !== "none" && !e.closest("[hidden]"); };
  var short = function (e) { return e.tagName.toLowerCase() + (e.id ? "#" + e.id : "") + (e.className && typeof e.className === "string" ? "." + e.className.split(" ")[0] : "") + ' "' + (e.textContent || "").trim().slice(0, 30) + '"'; };
  var name = function (e) {
    var t = (e.getAttribute("aria-label") || "").trim(); if (t) return t;
    var lb = e.getAttribute("aria-labelledby"); if (lb) { t = lb.split(" ").map(function (i) { var n = document.getElementById(i); return n ? n.textContent : ""; }).join(" ").trim(); if (t) return t; }
    if (e.labels && e.labels.length) { t = Array.prototype.map.call(e.labels, function (l) { return l.textContent; }).join(" ").trim(); if (t) return t; }
    t = (e.textContent || "").trim(); if (t) return t;
    var im = e.querySelector("img[alt]"); if (im && im.alt.trim()) return im.alt.trim();
    return (e.getAttribute("title") || "").trim();
  };
  Array.prototype.forEach.call(document.querySelectorAll("button, a[href], [role=button], [role=tab]"), function (e) { if (vis(e) && !name(e)) out.no_name.push(short(e)); });
  Array.prototype.forEach.call(document.querySelectorAll("input:not([type=hidden]), select, textarea"), function (e) { if (vis(e) && !name(e)) out.no_label.push(short(e)); });
  Array.prototype.forEach.call(document.querySelectorAll("img"), function (e) { if (!e.hasAttribute("alt")) out.img_no_alt.push(short(e)); });
  Array.prototype.forEach.call(document.querySelectorAll("svg[role=img]"), function (e) { if (!name(e) && !e.querySelector("title")) out.svg_unlabelled.push(short(e)); });
  var seen = {}; Array.prototype.forEach.call(document.querySelectorAll("[id]"), function (e) { if (seen[e.id]) out.dup_ids.push(e.id); seen[e.id] = 1; });
  var last = 0; Array.prototype.forEach.call(document.querySelectorAll("h1, h2, h3, h4, h5, h6"), function (h) { if (!vis(h)) return; var n = +h.tagName[1]; if (last && n > last + 1) out.heading_jumps.push("h" + last + " -> h" + n + " " + short(h)); last = n; });
  Array.prototype.forEach.call(document.querySelectorAll("[tabindex]"), function (e) { if (+e.getAttribute("tabindex") > 0) out.positive_tabindex.push(short(e)); });
  Array.prototype.forEach.call(document.querySelectorAll("tr.click"), function (e) { if (!e.hasAttribute("tabindex")) out.mouse_only_rows.push(short(e)); });
  if (!document.documentElement.lang) out.no_lang.push("html");
  Array.prototype.forEach.call(document.querySelectorAll("table"), function (t) { if (vis(t) && !t.querySelector("th")) out.table_no_header.push(short(t)); });
  /* contrast */
  var parse = function (c) { var m = c.match(/rgba?\(([^)]+)\)/); if (!m) return null; var p = m[1].split(/[ ,/]+/).filter(Boolean).map(Number); return { r: p[0], g: p[1], b: p[2], a: p.length > 3 ? p[3] : 1 }; };
  var lum = function (c) { var f = function (v) { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); }; return 0.2126 * f(c.r) + 0.7152 * f(c.g) + 0.0722 * f(c.b); };
  var over = function (top, bot) { var a = top.a; return { r: top.r * a + bot.r * (1 - a), g: top.g * a + bot.g * (1 - a), b: top.b * a + bot.b * (1 - a), a: 1 }; };
  var bg = function (e) {
    var chain = [], n = e; while (n && n.nodeType === 1) { var c = parse(getComputedStyle(n).backgroundColor); if (c && c.a > 0) chain.push(c); if (c && c.a >= 1) break; n = n.parentElement; }
    var base = { r: 255, g: 255, b: 255, a: 1 }; var t = parse(getComputedStyle(document.body).backgroundColor); if (t && t.a > 0) base = t;
    for (var i = chain.length - 1; i >= 0; i--) base = over(chain[i], base);
    return base;
  };
  var checked = 0, bad = {};
  Array.prototype.forEach.call(document.querySelectorAll("body *"), function (e) {
    if (!vis(e) || e.closest("svg, script, style, .lc-root, .tip, .toast")) return;
    var own = Array.prototype.filter.call(e.childNodes, function (n) { return n.nodeType === 3 && n.nodeValue.trim().length > 1; }).length;
    if (!own) return;
    var cs = getComputedStyle(e), fg = parse(cs.color); if (!fg) return;
    var b = bg(e); if (fg.a < 1) fg = over(fg, b);
    var op = 1, n = e; while (n && n.nodeType === 1) { op *= +getComputedStyle(n).opacity; n = n.parentElement; }
    if (op < 1) fg = over({ r: fg.r, g: fg.g, b: fg.b, a: op }, b);
    var l1 = lum(fg), l2 = lum(b), ratio = (Math.max(l1, l2) + 0.05) / (Math.min(l1, l2) + 0.05), px = parseFloat(cs.fontSize), large = px >= 24 || (px >= 18.66 && +cs.fontWeight >= 700);
    checked++;
    if (ratio < (large ? 3 : 4.5)) { var key = short(e) + " " + ratio.toFixed(2); if (!bad[key]) { bad[key] = 1; out.low_contrast.push(key); } }
  });
  /* touch targets: 24 by 24 CSS pixels is the WCAG 2.2 minimum */
  Array.prototype.forEach.call(document.querySelectorAll("button, a[href], select, input:not([type=hidden]), [role=tab]"), function (e) {
    if (!vis(e)) return; var r = e.getBoundingClientRect();
    if ((r.width < 24 || r.height < 24) && getComputedStyle(e).display !== "inline") out.small_targets.push(short(e) + " " + Math.round(r.width) + "x" + Math.round(r.height));
  });
  out.contrast_checked = checked;
  return out;
})();
