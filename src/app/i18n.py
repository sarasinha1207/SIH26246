"""
Hindi text for the public site.

inject(html)  finds every element of a built page that holds visible English text, looks its inner HTML up in i18n_hi.PAGE and adds the Hindi as a
              data-hi attribute (the page script swaps it in when the visitor chooses Hindi, and swaps the English back).  The page text itself is left
              exactly as written.  Elements without a translation are returned so the build can list them.
write_js(p)   writes assets/i18n-hi.js: the strings the page script builds at run time (charts, tooltips, map), names, months and page titles.
"""
import html as _html
import json
import re
from pathlib import Path

from bs4 import BeautifulSoup, Tag, NavigableString, Comment

import i18n_hi

SKIP = {"script", "style", "svg", "noscript", "head", "title", "meta", "link", "template"}
FORM = {"select", "input", "textarea"}


def norm(s):
    return re.sub(r"\s+", " ", s).strip()


def _letters(s):
    return re.search(r"[A-Za-z]", s) is not None


def _direct_text(tag):
    return any(isinstance(c, NavigableString) and not isinstance(c, Comment) and _letters(str(c)) for c in tag.children)


def units(src):
    """Return [(tag, key)] for every translatable element of the page, outermost first."""
    soup = BeautifulSoup(src, "html.parser")
    out, aria = [], []

    def walk(node):
        for tag in node.children:
            if not isinstance(tag, Tag):
                continue
            if tag.has_attr("aria-label") and norm(tag["aria-label"]) in i18n_hi.ATTR:
                aria.append(tag)
            if tag.name in SKIP or tag.get("translate") == "no":
                continue
            if _direct_text(tag):
                if tag.has_attr("id") or tag.has_attr("data-fill"):
                    continue                                   # its text is written by the page script
                for d in tag.descendants:
                    if isinstance(d, Tag) and ((d.has_attr("id") and not d.has_attr("data-fill")) or d.name in FORM):
                        raise ValueError(f"translatable text contains a script-bound element: <{tag.name}> {norm(str(tag))[:80]}")
                out.append((tag, norm("".join(str(c) for c in tag.contents))))
            else:
                walk(tag)

    walk(soup)
    return out, aria


def inject(src):
    items, aria = units(src)
    starts = [0]
    for line in src.split("\n")[:-1]:
        starts.append(starts[-1] + len(line) + 1)
    edits, missing = [], []

    def at(tag):
        off = starts[tag.sourceline - 1] + tag.sourcepos
        assert src[off] == "<" and src[off + 1:off + 1 + len(tag.name)] == tag.name, (tag.name, off)
        return off + 1 + len(tag.name)

    for tag, key in items:
        hi = i18n_hi.PAGE.get(key)
        if hi is None:
            missing.append(key)
        else:
            edits.append((at(tag), f' data-hi="{_html.escape(hi, quote=True)}"'))
    for tag in aria:
        edits.append((at(tag), f' data-hi-aria="{_html.escape(i18n_hi.ATTR[norm(tag["aria-label"])], quote=True)}"'))
    for pos, text in sorted(edits, reverse=True):
        src = src[:pos] + text + src[pos:]
    return src, missing


def write_js(path):
    data = {"s": i18n_hi.JS, "names": i18n_hi.NAMES, "months": i18n_hi.MONTHS, "titles": i18n_hi.TITLES}
    Path(path).write_text("window.HI = " + json.dumps(data, ensure_ascii=False, separators=(",", ":")) + ";\n", encoding="utf-8")
