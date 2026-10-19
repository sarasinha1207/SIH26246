"""Helpers for the tests that check a write-up or an artifact the repository does not carry.

The phase write-ups (docs/phases/), the superseded model versions (models/xgboost_v1, models/xgboost_v2) and the quarantined prototype are kept on disk but are
git-ignored.  A test that needs one of them skips with a clear message on a clone that lacks it, instead of crashing."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _rel(p):
    try:
        return str(Path(p).resolve().relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(p)


def skip_module_unless(*paths, why="checks a document or artifact that is not in the repository"):
    """Call at the top of a test module: stops the whole module (exit 0 with a [SKIP] line, or a pytest module skip) when any path is missing."""
    missing = [_rel(p) for p in paths if not Path(p).exists()]
    if not missing:
        return
    msg = f"{why} (missing: {', '.join(missing)})"
    if sys._getframe(1).f_globals.get("__name__") == "__main__":
        print(f"[SKIP] {Path(sys.argv[0]).name}: {msg}")
        sys.exit(0)
    import pytest
    pytest.skip(msg, allow_module_level=True)


def read_doc(path):
    """The text of a write-up, or a skipped test when the write-up is not in this checkout."""
    p = Path(path)
    if not p.exists():
        raise unittest.SkipTest(f"{_rel(p)} is not in the repository (kept locally)")
    return p.read_text(encoding="utf-8")
