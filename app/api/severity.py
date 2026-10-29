"""/api/severity: see _v4api.py and the API page (docs/api.html).  Standard library only."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _v4api  # noqa: E402

handler = _v4api.make_handler("severity")
