"""
Forecast API, server side - a read-only JSON view of the v4 forecast: /api/forecast, /api/flags, /api/demand-index, /api/capacity-gap and /api/meta.

One module serves the five Vercel functions (app/api/forecast.py and its siblings) and the local server (src/app/serve.py).  Standard library only.
Data: the files the dashboard already loads (app/dashboard/data/core.js, alerts.js and the per-state shards), so the API and the dashboard can never disagree.
The data is SIMULATED and every response says so.  Point forecasts are whole persons; ranges are the usual and the wide 90% range of the dashboard, computed
with the same calibration tables (a range exists only where the table has one for the level asked for, otherwise it is null).

Protections (as for /api/chat): GET and OPTIONS only; unknown or malformed parameters are refused; every parameter is checked against the lists in core.js; the size of a
reply is capped (rows, horizons, series); a per-address rate limit and a daily cap for the whole site, in memory; no cookies, no logging of queries.
Settings (environment): API_RATE_PER_MINUTE (default 60), API_DAILY_CAP (default 20000).
"""
import json
import os
import re
import threading
import time
from collections import deque
from functools import lru_cache
from http.server import BaseHTTPRequestHandler
from math import exp
from pathlib import Path
from urllib.parse import parse_qs, urlparse

DATA = Path(__file__).resolve().parents[1] / "dashboard" / "data"
VERSION = "1"
MEASURES = {"E": "employed_workers", "V": "job_vacancies", "S": "registered_job_seekers"}
FLAG_HORIZONS = (12, 36, 60)
LIMIT = {"query": 1500, "rows": 20000, "horizons": 60, "series": 200, "alerts": 1000}
NOTE = "Simulated data: it behaves like official statistics but describes no real district. Not an official statistic."


class ApiError(Exception):
    def __init__(self, code, error, message):
        super().__init__(message)
        self.code, self.error, self.message = code, error, message


def bad(message, error="bad_parameter", code=400):
    return ApiError(code, error, message)


# ---- the data ---------------------------------------------------------------------------------------------------------------------------------------
def _js(name, var):
    t = (DATA / name).read_text(encoding="utf-8")
    return json.loads(t[t.index("{"):t.rindex("}") + 1])


@lru_cache(maxsize=1)
def core():
    return _js("core.js", "DASH4")


@lru_cache(maxsize=1)
def alerts():
    return _js("alerts.js", "DASH4_ALERTS")


@lru_cache(maxsize=4)
def shard(state):
    return json.loads((DATA / "shards" / (re.sub(r"[^a-z0-9]+", "-", state.lower()).strip("-") + ".json")).read_text(encoding="utf-8"))


def add_month(ym, n):
    y, m = int(ym[:4]), int(ym[5:]) - 1 + n
    return f"{y + m // 12}-{m % 12 + 1:02d}"


# ---- parameters -------------------------------------------------------------------------------------------------------------------------------------
def parse_query(qs, allowed):
    if len(qs) > LIMIT["query"]:
        raise bad("The query string is too long.")
    q = parse_qs(qs, keep_blank_values=False, max_num_fields=20)
    unknown = sorted(set(q) - set(allowed))
    if unknown:
        raise bad(f"Unknown parameter: {', '.join(unknown)}. Allowed: {', '.join(sorted(allowed))}.")
    out = {}
    for k, v in q.items():
        if len(v) > 1:
            raise bad(f"Parameter {k} was given more than once.")
        out[k] = v[0].strip()
    return out


def pick(value, options, what):
    """The option that equals value ignoring case."""
    for o in options:
        if o.lower() == value.lower():
            return o
    raise bad(f"Unknown {what} '{value[:60]}'. See /api/meta for the valid values.")


def scope(q):
    """state, district (LGD code), sector and trade from the query, checked against core.js and against each other."""
    M = core()["meta"]
    s = {"state": None, "district": None, "sector": None, "trade": None}
    if "district" in q:
        v = q["district"]
        hit = [d for d in M["districts"] if (v.isdigit() and d[0] == int(v)) or (not v.isdigit() and d[1].lower() == v.lower())]
        if len(hit) != 1:
            raise bad(f"Unknown or ambiguous district '{v[:60]}': use the LGD code (see /api/meta).")
        s["district"], s["state"] = hit[0][0], M["states"][hit[0][2]]
    if "state" in q:
        st = pick(q["state"], M["states"], "state")
        if s["state"] and s["state"] != st:
            raise bad(f"District {s['district']} is not in {st}.")
        s["state"] = st
    if "trade" in q:
        v = q["trade"]
        hit = [t for t in M["trades"] if t["c"].lower() == v.lower() or t["n"].lower() == v.lower()]
        if len(hit) != 1:
            raise bad(f"Unknown trade '{v[:60]}': use the trade code, for example HLT-2221 (see /api/meta).")
        s["trade"], s["sector"] = hit[0]["c"], hit[0]["s"]
    if "sector" in q:
        sec = pick(q["sector"], M["sectors"], "sector")
        if s["sector"] and s["sector"] != sec:
            raise bad(f"Trade {s['trade']} is not in {sec}.")
        s["sector"] = sec
    return s


def name_of(s):
    M = core()["meta"]
    d = [x[1] for x in M["districts"] if x[0] == s["district"]]
    t = [x["n"] for x in M["trades"] if x["c"] == s["trade"]]
    return {"state": s["state"], "district_lgd": s["district"], "district": d[0] if d else None, "sector": s["sector"], "trade": s["trade"], "trade_name": t[0] if t else None}


def int_list(v, lo, hi, what, default, every=None):
    if v is None:
        return list(default)
    if v.lower() == "all":
        return list(range(lo, hi + 1)) if every is None else list(every)
    try:
        out = sorted({int(x) for x in v.split(",")})
    except ValueError:
        raise bad(f"{what} must be whole numbers separated by commas, or 'all'.")
    if not out or out[0] < lo or out[-1] > hi or len(out) > LIMIT["horizons"]:
        raise bad(f"{what} must be between {lo} and {hi}.")
    return out


def measures(v):
    if v is None or v.lower() == "all":
        return ["E", "V", "S"]
    ks = [x.strip().upper() for x in v.split(",")]
    if not ks or any(k not in MEASURES for k in ks):
        raise bad("measure must be E, V or S (employed workers, job vacancies, registered job seekers), separated by commas, or 'all'.")
    return list(dict.fromkeys(ks))


def paging(q, default, cap):
    try:
        limit = int(q.get("limit", default))
        offset = int(q.get("offset", 0))
    except ValueError:
        raise bad("limit and offset must be whole numbers.")
    if not 1 <= limit <= cap or offset < 0:
        raise bad(f"limit must be between 1 and {cap} and offset at least 0.")
    return limit, offset


# ---- numbers ----------------------------------------------------------------------------------------------------------------------------------------
def group(s):
    """(group dict of 180 months, level name) from core.js where the scope is one of India, a sector, a trade, a state or a state-sector; otherwise None."""
    g = core()["groups"]
    if s["district"] is None and s["state"] is None:
        return (g["trade"][s["trade"]], "trade") if s["trade"] else (g["sector"][s["sector"]], "sector") if s["sector"] else (g["india"][""], "india")
    if s["district"] is None and s["trade"] is None:
        return (g["state_sector"][f"{s['state']}|{s['sector']}"], "state_sector") if s["sector"] else (g["state"][s["state"]], "state")
    return None


def ranges(level, k, point, h, sector=None):
    """usual and wide 90% range of a point forecast at horizon h: exp(offset) of the calibration table, with the point always inside; None where no table exists."""
    C = core()
    if level == "series":
        c = C["cal_series"][k]["all" if k == "S" else sector]
    elif level in C["cal_levels"]:
        c = C["cal_levels"][level][k]
    else:
        return None, None

    def one(lo, hi):
        return [int(round(point * exp(min(c[lo][h - 1], 0)))), int(round(point * exp(max(c[hi][h - 1], 0))))]
    return one("lo", "hi"), one("lo_wide", "hi_wide")


def cell(k, point, level, h, sector=None):
    u, w = ranges(level, k, point, h, sector)
    return {"point": int(point), "usual_90": u, "wide_90": w}


def forecast_rows(hist, fc, ks, hs, level, sector, last_month):
    """hist: {k: last observed}, fc: {k: 60 values}."""
    out = []
    for h in hs:
        row = {"horizon": h, "month": add_month("2026-01", h - 1)}
        for k in ks:
            row[MEASURES[k]] = cell(k, fc[k][h - 1], level, h, sector)
        out.append(row)
    return out


# ---- endpoints --------------------------------------------------------------------------------------------------------------------------------------
def api_meta(q):
    parse_query(q, ())
    C = core()
    M = C["meta"]
    return {"version": VERSION, "forecast_origin": M["origin"], "forecast_months": M["fc"][:2], "horizons": [1, 60], "states": M["states"], "sectors": M["sectors"],
            "trades": [{"code": t["c"], "name": t["n"], "sector": t["s"]} for t in M["trades"]], "districts": [{"lgd": d[0], "name": d[1], "state": M["states"][d[2]]} for d in M["districts"]],
            "measures": MEASURES, "files": M["files"], "built_from": M["manifest"]}


def api_forecast(q):
    q = parse_query(q, ("state", "district", "sector", "trade", "measure", "horizon", "detail", "limit", "offset"))
    s = scope(q)
    ks, hs = measures(q.get("measure")), int_list(q.get("horizon"), 1, 60, "horizon", (12, 36, 60))
    detail = q.get("detail", "aggregate")
    if detail not in ("aggregate", "series"):
        raise bad("detail must be 'aggregate' or 'series'.")
    C = core()
    n0 = C["meta"]["hist_core"][2]
    g = group(s)
    if g and detail == "aggregate":
        G, level = g
        data = forecast_rows(None, {k: G[k][n0:] for k in ks}, ks, hs, level, s["sector"], None)
        return {"scope": name_of(s), "level": level, "last_observed": {"month": C["meta"]["hist_core"][1], **{MEASURES[k]: G[k][n0 - 1] for k in ks}}, "data": data,
                "notes": ["Point forecasts add up across trades, districts and states; the ranges do not."]}
    if s["state"] is None:
        raise bad("detail=series needs a state or a district.")
    sh = shard(s["state"])
    trades = C["meta"]["trades"]
    idx = [i for i in range(len(sh["ids"])) if (s["district"] is None or sh["d"][i] == s["district"]) and (s["trade"] is None or trades[sh["t"][i]]["c"] == s["trade"])
           and (s["sector"] is None or trades[sh["t"][i]]["s"] == s["sector"])]
    if not idx:
        raise bad("No series for that combination.", "not_found", 404)
    last_m = C["meta"]["hist_shard"][1]
    if detail == "aggregate":
        level = "series" if s["district"] is not None and s["trade"] is not None else "district_sector" if s["district"] is not None and s["sector"] is not None and s["trade"] is None else None
        fc = {k: [sum(sh["fc"][k][i][m] for i in idx) for m in range(60)] for k in ks}
        last = {MEASURES[k]: sum(sh["hist"][k][i][-1] for i in idx) for k in ks}
        data = forecast_rows(None, fc, ks, hs, level, s["sector"], None)
        notes = ["Point forecasts add up across trades, districts and states; the ranges do not."]
        if level is None:
            notes.append("No checked 90% range exists for this combination of filters, so only the point forecast is given: choose a district with a sector or a trade, or a sector, trade, state or state with sector.")
        return {"scope": name_of(s), "level": level or "state_subset", "series_count": len(idx), "last_observed": {"month": last_m, **last}, "data": data, "notes": notes}
    limit, offset = paging(q, 50, LIMIT["series"])
    page = idx[offset:offset + limit]
    items = []
    for i in page:
        t = trades[sh["t"][i]]
        fc = {k: sh["fc"][k][i] for k in ks}
        items.append({"series_id": sh["ids"][i], "district_lgd": sh["d"][i], "trade": t["c"], "trade_name": t["n"], "sector": t["s"], "last_observed": {MEASURES[k]: sh["hist"][k][i][-1] for k in ks},
                      "confidence_by_12_month_band": {MEASURES[k]: {b: {"H": "high", "M": "medium", "L": "low"}[c] for b, c in zip(C["meta"]["bands"], sh["conf"][k][i])} for k in ks},
                      "data": forecast_rows(None, fc, ks, hs, "series", t["s"], None)})
    if len(items) * len(hs) * len(ks) > LIMIT["rows"]:
        raise bad("Too many values requested: lower limit or the number of horizons.")
    return {"scope": name_of(s), "level": "series", "series_total": len(idx), "limit": limit, "offset": offset, "last_observed_month": last_m, "series": items}


def api_flags(q):
    q = parse_query(q, ("state", "district", "sector", "trade", "horizon", "type", "limit", "offset", "months"))
    s = scope(q)
    C = core()
    M = C["meta"]
    if s["district"] is not None and s["trade"] is not None:
        sh = shard(s["state"])
        i = [j for j in range(len(sh["ids"])) if sh["d"][j] == s["district"] and M["trades"][sh["t"][j]]["c"] == s["trade"]][0]
        hs = int_list(q.get("months"), 1, 60, "months", range(1, 61), every=range(1, 61))
        names = {int(k): v for k, v in M["flag_names"].items()}
        return {"scope": name_of(s), "series_id": sh["ids"][i], "note": "Flags are relative: the percentile of forecast vacancies per registered seeker among the districts of the same trade in the same month. 90 or more is a shortage alert, 75 or more a watch, 25 or less an oversupply watch, 10 or less an oversupply alert.",
                "data": [{"horizon": h, "month": add_month("2026-01", h - 1), "flag": names[sh["flag"][i][h - 1]], "flag_code": sh["flag"][i][h - 1], "percentile": sh["cov"][i][h - 1]} for h in hs]}
    hz = q.get("horizon", "12")
    if not hz.isdigit() or int(hz) not in FLAG_HORIZONS:
        raise bad("horizon must be 12, 36 or 60 for the list of alerts (or give a district and a trade for the flag of every month).")
    ty = q.get("type", "all")
    if ty not in ("all", "shortage", "oversupply"):
        raise bad("type must be all, shortage or oversupply.")
    limit, offset = paging(q, 100, LIMIT["alerts"])
    A = alerts()
    hi = FLAG_HORIZONS.index(int(hz))
    rows = [r for r in A["rows"] if r[1] == hi and (ty == "all" or r[0] == (0 if ty == "shortage" else 1)) and (s["state"] is None or M["states"][r[2]] == s["state"])
            and (s["district"] is None or r[3] == s["district"]) and (s["trade"] is None or M["trades"][r[4]]["c"] == s["trade"]) and (s["sector"] is None or M["trades"][r[4]]["s"] == s["sector"])]
    rows.sort(key=lambda r: (r[0], -r[5] if r[0] == 0 else r[5], r[3]))
    dn = {d[0]: d[1] for d in M["districts"]}
    lab = {"H": "high", "M": "medium", "L": "low"}
    data = [{"alert": "shortage" if r[0] == 0 else "oversupply", "state": M["states"][r[2]], "district_lgd": r[3], "district": dn[r[3]], "trade": M["trades"][r[4]]["c"], "trade_name": M["trades"][r[4]]["n"],
             "sector": M["trades"][r[4]]["s"], "percentile": r[5], "job_vacancies": r[6], "registered_job_seekers": r[7], "vacancy_confidence": lab[r[8]], "seeker_confidence": lab[r[9]]} for r in rows[offset:offset + limit]]
    return {"scope": name_of(s), "horizon": int(hz), "month": add_month("2026-01", int(hz) - 1), "total": len(rows), "limit": limit, "offset": offset, "data": data,
            "notes": ["Alerts are series in the top (shortage) or bottom (oversupply) tenth of their trade in that month; the percentile is the position among the districts of the trade.",
                      "In testing, alerts one to twelve months ahead were right about seven times in ten, against a base rate of one in ten."]}


def api_demand_index(q):
    q = parse_query(q, ("state", "district", "sector", "trade", "from", "to", "resolution"))
    s = scope(q)
    C = core()
    M = C["meta"]
    res = q.get("resolution", "annual")
    if res not in ("annual", "monthly"):
        raise bad("resolution must be annual (December of each year) or monthly.")
    g = group(s)
    if g:
        series, start = g[0]["DI"], M["hist_core"][0]
        level = g[1]
    elif s["district"] is not None and s["trade"] is not None:
        series, start = shard(s["state"])["DI"][[j for j in range(len(shard(s["state"])["ids"])) if shard(s["state"])["d"][j] == s["district"] and M["trades"][shard(s["state"])["t"][j]]["c"] == s["trade"]][0]], M["hist_shard"][0]
        level = "series"
    elif s["district"] is not None and s["sector"] and s["trade"] is None:
        v = C["di_district_sector"][f"{s['district']}|{s['sector']}"]
        return {"scope": name_of(s), "level": "district_sector", "note": "Employed-weighted annual mean of the Demand Index over the forecast months.", "data": [{"year": 2026 + i, "demand_index": x} for i, x in enumerate(v)]}
    elif s["state"] is not None and s["trade"] and s["district"] is None:
        v = C["di_state_trade"][f"{s['state']}|{s['trade']}"]
        return {"scope": name_of(s), "level": "state_trade", "note": "Employed-weighted annual mean of the Demand Index over the forecast months.", "data": [{"year": 2026 + i, "demand_index": x} for i, x in enumerate(v)]}
    else:
        raise bad("For a district give a sector or a trade as well; for a state give a sector, a trade or neither.")
    months = [add_month(start, i) for i in range(len(series))]
    lo, hi = q.get("from", "2025-12"), q.get("to", "2030-12")
    for v in (lo, hi):
        if not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", v):
            raise bad("from and to must be months like 2026-12.")
    sel = [(m, x) for m, x in zip(months, series) if lo <= m <= hi and (res == "monthly" or m.endswith("-12"))]
    if not sel:
        raise bad(f"No months between {lo} and {hi}: the index runs from {months[0]} to {months[-1]}.", "not_found", 404)
    return {"scope": name_of(s), "level": level, "note": "0 to 100; 50 is the median district of a trade at the 2018-2019 demand level. Months after 2025-12 are forecasts (from forecast vacancies only).",
            "data": [{"month": m, "demand_index": x, "forecast": m > M["origin"]} for m, x in sel]}


def api_capacity_gap(q):
    q = parse_query(q, ("state", "district", "sector", "trade", "year"))
    s = scope(q)
    C = core()
    cap = C["capacity"]
    ys = int_list(q.get("year"), 2026, 2030, "year", range(2026, 2031))
    if s["district"] is None:
        if s["state"] is None:
            rows, level = (cap["trade"], "trade") if s["trade"] else (cap["sector"], "sector") if s["sector"] else (cap["india"], "india")
            rows = [r for r in rows if (not s["trade"] or r["Trade_Code"] == s["trade"]) and (not s["sector"] or s["trade"] or r["Sector_Name"] == s["sector"])]
        else:
            rows, level = (cap["state_trade"], "state_trade") if s["trade"] else (cap["state_sector"], "state_sector") if s["sector"] else (cap["state"], "state")
            rows = [r for r in rows if r["State_Name"] == s["state"] and (not s["trade"] or r["Trade_Code"] == s["trade"]) and (not s["sector"] or s["trade"] or r["Sector_Name"] == s["sector"])]
        out = [{"year": r["year"], "average_monthly_openings": r["avg_vacancies"], "seats": r["seats"], "expected_certified": r["expected_certified"], "openings_per_seat": r["openings_per_seat"],
                "certified_per_opening": r["supply_per_opening"]} for r in rows if r["year"] in ys]
    else:
        sh = shard(s["state"])
        trades = C["meta"]["trades"]
        idx = [i for i in range(len(sh["ids"])) if sh["d"][i] == s["district"] and (s["trade"] is None or trades[sh["t"][i]]["c"] == s["trade"]) and (s["sector"] is None or trades[sh["t"][i]]["s"] == s["sector"])]
        if not idx:
            raise bad("No series for that combination.", "not_found", 404)
        level = "series" if s["trade"] else "district_subset"
        seats, cert = sum(sh["cap"]["seats"][i] for i in idx), sum(sh["cap"]["cert"][i] for i in idx)
        out = []
        for y in ys:
            v = sum(sh["cap"]["vac"][i][y - 2026] for i in idx)
            out.append({"year": y, "average_monthly_openings": round(v, 1), "seats": seats, "expected_certified": round(cert, 1), "openings_per_seat": round(v / seats, 4) if seats else None,
                        "certified_per_opening": round(cert / v, 4) if v else None})
    return {"scope": name_of(s), "level": level, "data": out,
            "notes": ["Seats are the 2025-26 sanctioned seats, held flat to 2030 (an assumption: no seat plans are forecast).", "Below 1 certified per opening, fewer people finish training in a year than there are openings; read the ratios as a ranking of where capacity is stretched."]}


ENDPOINTS = {"forecast": api_forecast, "flags": api_flags, "demand-index": api_demand_index, "capacity-gap": api_capacity_gap, "meta": api_meta}


# ---- protection and transport -----------------------------------------------------------------------------------------------------------------------
class Limiter:
    """Requests per visitor address per minute, and a daily cap for the whole site.  In memory: a restart or a second instance starts again."""

    def __init__(self, per_minute=None, per_day=None):
        self.per_minute = per_minute or int(os.environ.get("API_RATE_PER_MINUTE", 60))
        self.per_day = per_day or int(os.environ.get("API_DAILY_CAP", 20000))
        self.hits, self.day, self.count, self.lock = {}, None, 0, threading.Lock()

    def allow(self, ip, now):
        with self.lock:
            d = int(now // 86400)
            if d != self.day:
                self.day, self.count = d, 0
            q = self.hits.setdefault(ip, deque())
            while q and now - q[0] > 60:
                q.popleft()
            if len(q) >= self.per_minute:
                return "rate"
            if self.count >= self.per_day:
                return "daily_cap"
            q.append(now)
            self.count += 1
            if len(self.hits) > 5000:
                for k in [k for k, v in self.hits.items() if not v or now - v[-1] > 60]:
                    self.hits.pop(k, None)
            return None


LIMITER = Limiter()
HEADERS = {"Content-Type": "application/json; charset=utf-8", "Access-Control-Allow-Origin": "*", "Access-Control-Allow-Methods": "GET, OPTIONS", "X-Content-Type-Options": "nosniff",
           "Cache-Control": "public, max-age=300, s-maxage=3600"}


def respond(endpoint, qs, ip="", method="GET", limiter=None, now=None):
    """(status, headers, body bytes) for one request."""
    h = dict(HEADERS)
    if method == "OPTIONS":
        return 204, {**h, "Access-Control-Max-Age": "86400"}, b""
    if method != "GET":
        h["Allow"] = "GET, OPTIONS"
        body = {"ok": False, "error": "method_not_allowed", "message": "This API is read-only: use GET."}
        return 405, {**h, "Cache-Control": "no-store"}, json.dumps(body).encode()
    why = (limiter or LIMITER).allow(ip or "unknown", now if now is not None else time.time())
    if why:
        body = {"ok": False, "error": why, "message": "Too many requests: please wait a minute." if why == "rate" else "The daily limit of this API has been reached."}
        return 429, {**h, "Cache-Control": "no-store", "Retry-After": "60"}, json.dumps(body).encode()
    try:
        out = ENDPOINTS[endpoint](qs)
        body = {"ok": True, "data_simulated": True, "data_notice": NOTE, "forecast_origin": core()["meta"]["origin"], **out}
        return 200, h, json.dumps(body, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    except ApiError as e:
        return e.code, {**h, "Cache-Control": "no-store"}, json.dumps({"ok": False, "error": e.error, "message": e.message}).encode()
    except (OSError, KeyError, ValueError) as e:                      # a missing file or an unexpected shape: say so without leaking paths
        return 500, {**h, "Cache-Control": "no-store"}, json.dumps({"ok": False, "error": "server_error", "message": "The data could not be read."}).encode()


def make_handler(endpoint):
    class handler(BaseHTTPRequestHandler):
        """Vercel's Python runtime loads this class for every request to /api/<endpoint>."""

        def _go(self, method):
            u = urlparse(self.path)
            ip = (self.headers.get("X-Forwarded-For") or self.client_address[0]).split(",")[0].strip()
            code, headers, body = respond(endpoint, u.query, ip, method)
            self.send_response(code)
            for k, v in headers.items():
                self.send_header(k, v)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            if body:
                self.wfile.write(body)

        def do_GET(self):
            self._go("GET")

        def do_OPTIONS(self):
            self._go("OPTIONS")

        def do_POST(self):
            self._go("POST")

        do_PUT = do_DELETE = do_PATCH = do_POST

        def log_message(self, fmt, *args):                       # the platform keeps its own request log; nothing a visitor asked is written here
            pass
    return handler
