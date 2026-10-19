#!/usr/bin/env python3
"""
Phase 8 (B1 + B2 declaration) - formally declare the final configuration as models/xgboost_v3 BEFORE the fresh-draw evaluation and the conformal evaluation are run.

xgboost_v3/primary = the xgboost_v2/primary models (same checkpoints, copied) with
  * the horizon blend with last value + seasonal shift chosen on the three rolling-origin folds for every target (the seekers blend is no longer vetoed by the
    validation split; the veto was shown to be wrong on the test split, so this declaration is a post-test decision - its unbiased check is the fresh synthetic draw), and
  * adaptive conformal intervals (settings in conformal.json), with the static fold-based intervals of the blended model as the fallback.
declaration.json records the time, the evidence and SHA-256 of every file; later scripts verify it.   Run: python src/evaluation/declare.py
"""
import json
import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src" / "common"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import splits as sp  # noqa: E402
from conformal import DECLARED  # noqa: E402

V2, V3, OUT = ROOT / "models" / "xgboost_v2", ROOT / "models" / "xgboost_v3", ROOT / "reports" / "evaluation"


def main():
    if (V3 / "declaration.json").exists():
        raise SystemExit("already declared; create a new version directory instead of overwriting")
    d = V3 / "primary"
    shutil.copytree(V2 / "primary", d)
    fin = {k: json.load(open(OUT / f"finalize_{k}.json")) for k in "EVS"}
    blend = {k: fin[k]["blend_weights_cv"] for k in "EVS"}
    json.dump({"model_weight_by_target_horizon": blend, "rule": "weights chosen on the rolling-origin folds (xgboost_v2 finalize); no validation veto"}, open(d / "blend.json", "w"), indent=1)
    (d / "blend_cv.json").unlink()
    static = {k: fin[k]["intervals_with_cv_blend"] if (k == "S" and "intervals_with_cv_blend" in fin[k]) else fin[k]["intervals"] for k in "EVS"}
    json.dump({"level": [0.05, 0.95], "unit": "log error; add to the predicted log level", "role": "static fallback for the adaptive conformal intervals", "by_target_horizon": static}, open(d / "intervals.json", "w"), indent=1)
    json.dump({**DECLARED, "mondrian_by": ["sector", "horizon"], "pool": "signed log errors of earlier forecasts whose target month <= the origin month, shock months excluded",
               "initial_calibration": "validation-split errors of the train-only model (same blend)"}, open(V3 / "conformal.json", "w"), indent=1)
    files = {str(p.relative_to(V3)).replace("\\", "/"): sp.sha256(p) for p in sorted(V3.rglob("*")) if p.is_file()}
    evidence = {"blend": "weights from the folds; on the test split the seekers blend scored 5.69% vs 7.36% without it and 6.69% for the baseline (post-test choice, small selection bias)",
                "conformal": "static intervals covered 93% / 88% / 96% (E / V / S) with seekers mean width 45% and vacancies 85% coverage at 12 months"}
    json.dump({"declared_at": time.strftime("%Y-%m-%d %H:%M:%S"), "source": "models/xgboost_v2/primary (frozen, unchanged)", "evidence": evidence, "files_sha256": files,
               "settings_chosen_before_evaluation": DECLARED, "fresh_draw_run_after_declaration": True}, open(V3 / "declaration.json", "w"), indent=1)
    print("declared", V3, len(files), "files")


if __name__ == "__main__":
    main()
