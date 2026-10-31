"""/api/forecast: see _v4api.py and the API page (docs/api.html).  Standard library only."""
import sys
from http.server import BaseHTTPRequestHandler
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _v4api  # noqa: E402


class handler(BaseHTTPRequestHandler, _v4api.EndpointMixin):
    endpoint = "forecast"
