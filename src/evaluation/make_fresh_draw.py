#!/usr/bin/env python3
"""
Phase 8 (A6) - build a fresh synthetic evaluation draw: the same generator, cleaning and split code, run in an isolated copy of the project with a different random seed.
Nothing in the main project is touched: the copy lives in data/fresh_draws/seed_<seed>/ (a new world: new district effects, noise and shock paths; same structural design).
Steps inside the copy: generate_lmis_master_dataset.py (SEED patched) -> clean_panel.py -> make_splits.py (same 70/5/25 windows, same Phase 5 feature set).
Run: python src/evaluation/make_fresh_draw.py <seed>
"""
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main(seed):
    out = ROOT / "data" / "fresh_draws" / f"seed_{seed}"
    if out.exists():
        raise SystemExit(f"{out} exists; remove it first")
    shutil.copytree(ROOT / "src", out / "src", ignore=shutil.ignore_patterns("__pycache__"))
    (out / "docs" / "reference").mkdir(parents=True)
    shutil.copy(ROOT / "docs" / "reference" / "DATA_DICTIONARY.csv", out / "docs" / "reference")
    (out / "data" / "processed" / "features").mkdir(parents=True)
    shutil.copy(ROOT / "data" / "processed" / "features" / "feature_sets.json", out / "data" / "processed" / "features")
    (out / "reports").mkdir()
    gen = out / "src" / "data_generation" / "generate_lmis_master_dataset.py"
    txt = gen.read_text(encoding="utf-8")
    new, n = re.subn(r"^SEED = 42\b", f"SEED = {seed}", txt, flags=re.M)
    assert n == 1
    gen.write_text(new, encoding="utf-8")
    for script in ("data_generation/generate_lmis_master_dataset.py", "preprocessing/clean_panel.py", "splits/make_splits.py"):
        print("running", script, flush=True)
        r = subprocess.run([sys.executable, str(out / "src" / script)], cwd=out, capture_output=True, text=True)
        if r.returncode:
            print(r.stdout[-1500:], r.stderr[-1500:])
            raise SystemExit(f"{script} failed")
        print(r.stdout[-400:], flush=True)
    print("fresh draw ready:", out)


if __name__ == "__main__":
    main(int(sys.argv[1]))
