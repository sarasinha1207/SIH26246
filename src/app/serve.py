#!/usr/bin/env python3
"""
Local server for the website.   Run:  python src/app/serve.py [port]      (default port 8080; stop with Ctrl+C)

* Serves the app/ folder, and tells the browser never to keep a copy, so a refresh always shows the latest files.
* Watches the dashboard files too and rebuilds its shell when one changes.
* Watches the page sources (src/app/pages, build_pages.py, the Hindi text) and the stylesheet and script, and rebuilds the pages when one changes,
  so you only edit and refresh.  Rebuilding the data files (site_data.js, map_data.js) is still a separate command, see app/README.md.
* Serves the assistant's endpoint, /api/chat, which forwards questions to Gemini (app/api/chat.py). The key is read from the environment or a git-ignored .env file
  and never reaches the browser. Without a key the assistant answers from the site's own data.  Restart the server once after pulling a change to this file.
* Refuses to start if the port is already taken, instead of quietly sharing it.
"""
import functools
import http.server
import json
import importlib.util
import socketserver
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SITE = ROOT / "app"
SRC = Path(__file__).resolve().parent
sys.path.insert(0, str(SITE / "api"))
import chat as chat_proxy  # noqa: E402,E501   (app/api/chat.py: the same file Vercel runs at /api/chat)
DASH_WATCH = [SRC / "logo.py", SRC / "dashboard" / "shell.html", SITE / "dashboard" / "dashboard.css", SITE / "dashboard" / "dashboard.js", SITE / "dashboard" / "data" / "dash_data.js", SITE / "assets" / "chat.js", SITE / "assets" / "chat.css"]
WATCH = [SRC / "logo.py", *SRC.glob("pages/*.html"), SRC / "build_pages.py", SRC / "i18n.py", SRC / "i18n_hi.py", SITE / "assets" / "styles.css", SITE / "assets" / "site.js", SITE / "assets" / "chat.js", SITE / "assets" / "chat.css"]


class Handler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def _json(self, code, obj):
        data = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        path = self.path.split("?")[0]
        if path.rstrip("/") == "/api/chat":
            return self._json(200, chat_proxy.status())
        if path.endswith(".py"):                      # source files are not part of the site (Vercel does not serve them either)
            return self.send_error(404)
        super().do_GET()

    def do_POST(self):
        if self.path.split("?")[0].rstrip("/") != "/api/chat":
            return self._json(404, {"ok": False, "error": "not_found"})
        n = min(int(self.headers.get("Content-Length") or 0), chat_proxy.LIMIT["body"] + 1)
        code, obj = chat_proxy.answer(self.rfile.read(n), self.client_address[0], self.headers.get("Origin"), self.headers.get("Host"))
        self._json(code, obj)

    def log_message(self, fmt, *args):
        if "404" in fmt % args:
            sys.stderr.write("  " + fmt % args + "\n")


class Server(socketserver.ThreadingMixIn, http.server.HTTPServer):
    allow_reuse_address = False           # on Windows this would let a second server share a busy port
    daemon_threads = True


def stamp():
    return [p.stat().st_mtime for p in WATCH if p.exists()]


def dash_stamp():
    return [p.stat().st_mtime for p in DASH_WATCH if p.exists()]


def watch():
    last, dlast = stamp(), dash_stamp()
    while True:
        time.sleep(1)
        dnow = dash_stamp()
        if dnow != dlast:
            try:
                spec = importlib.util.spec_from_file_location("build_dashboard_live", SRC / "build_dashboard.py")
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                mod.shell()
                print(time.strftime("%H:%M:%S"), "dashboard rebuilt", flush=True)
            except Exception as e:  # noqa: BLE001
                print(time.strftime("%H:%M:%S"), "dashboard rebuild failed:", type(e).__name__, e, flush=True)
            dlast = dash_stamp()
        now = stamp()
        if now != last:
            last = now
            try:
                spec = importlib.util.spec_from_file_location("build_pages_live", SRC / "build_pages.py")
                mod = importlib.util.module_from_spec(spec)
                for name in ("i18n", "i18n_hi"):
                    sys.modules.pop(name, None)              # pick up edits to the Hindi text too
                spec.loader.exec_module(mod)
                mod.main()
                print(time.strftime("%H:%M:%S"), "pages rebuilt", flush=True)
            except Exception as e:  # noqa: BLE001  keep serving whatever the last good build was
                print(time.strftime("%H:%M:%S"), "rebuild failed:", type(e).__name__, e, flush=True)
            last = stamp()


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    try:
        server = Server(("127.0.0.1", port), functools.partial(Handler, directory=str(SITE)))
    except OSError as e:
        sys.exit(f"Port {port} is already in use ({e}). Close the other server, or choose another port:  python src/app/serve.py 8081")
    threading.Thread(target=watch, daemon=True).start()
    st = chat_proxy.status()
    print(f"KaushalSetu site: http://localhost:{port}   (Ctrl+C to stop)", flush=True)
    print("Assistant: " + (f"Gemini answers on ({st['model']})" if st["enabled"] else "answers from the site's own data only; add GEMINI_API_KEY to .env to switch Gemini on"), flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")


if __name__ == "__main__":
    main()
