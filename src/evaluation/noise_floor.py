#!/usr/bin/env python3
"""
Phase 8 (A1) - the noise floor of the synthetic data: the WAPE that an oracle would reach if it knew the generator's whole structural part (levels, district
effects, seasonality, sector cycles, shocks) exactly and only the random noise was left.  No model can beat this on this simulator.

Noise in src/data_generation/generate_lmis_master_dataset.py (all multiplicative, on the log scale), each a stationary AR(1) plus white noise:
    employment : AR(0.90, innovation sd 0.006) + white sd 0.008
    vacancies  : own AR(0.93, 0.035) + white 0.04, and they are proportional to realised employment, so they also carry the employment noise
    seekers    : own AR(0.95, 0.02) + white 0.035, and they also carry the employment noise (the unemployment-rate noise, a few percent of the level, is ignored,
                 so the seekers floor is slightly too low)
The oracle sees each past noisy value, so it can filter the AR state (Kalman filter) and forecast it ahead: the error at horizon h is the unforecastable part of the AR
state plus the white noise.  WAPE_h = E|exp(e) - 1| / E exp(e) with e ~ N(0, var_h), by Monte Carlo; a simulation of the filter checks the formula.
Writes reports/evaluation/noise_floor.csv and noise_floor.json; compares with the test WAPE of the frozen model by horizon.
Run: python src/evaluation/noise_floor.py
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "reports" / "evaluation"
PARTS = {"E": [(0.90, 0.006, 0.008)], "V": [(0.93, 0.035, 0.04), (0.90, 0.006, 0.008)], "S": [(0.95, 0.02, 0.035), (0.90, 0.006, 0.008)]}


def filtered_var(phi, q, w):
    P = q / (1 - phi ** 2)
    for _ in range(500):
        pred = phi ** 2 * P + q
        P = pred * w * w / (pred + w * w)
    return P


def var_h(phi, sig, w, h):
    q = sig * sig
    P = filtered_var(phi, q, w)
    ar = phi ** (2 * h) * P + q * (1 - phi ** (2 * h)) / (1 - phi ** 2)
    return ar + w * w


def wape_from_var(v, rng, n=2_000_000):
    e = rng.normal(0, np.sqrt(v), n)
    return 100 * np.abs(np.exp(e) - 1).mean() / np.exp(e).mean()


def simulate_check(phi, sig, w, horizons=(1, 6, 12), n=3000, T=300, seed=1):
    rng = np.random.default_rng(seed)
    x = np.zeros((n, T))
    x[:, 0] = rng.normal(0, sig / np.sqrt(1 - phi ** 2), n)
    for t in range(1, T):
        x[:, t] = phi * x[:, t - 1] + rng.normal(0, sig, n)
    y = x + rng.normal(0, w, (n, T))
    m, P = np.zeros(n), sig * sig / (1 - phi ** 2)
    mh = {h: np.zeros((n, T)) for h in horizons}
    for t in range(T):
        pm, pP = (phi * m, phi * phi * P + sig * sig) if t else (m, P)
        K = pP / (pP + w * w)
        m, P = pm + K * (y[:, t] - pm), (1 - K) * pP
        for h in horizons:
            mh[h][:, t] = phi ** h * m
    out = {}
    for h in horizons:
        err = (y[:, h:] - mh[h][:, :-h])[:, 60:]
        out[h] = float(100 * np.abs(np.exp(err) - 1).mean() / np.exp(err).mean())
    return out


def main():
    rng = np.random.default_rng(0)
    rows = []
    for k, parts in PARTS.items():
        for h in range(1, 13):
            v = sum(var_h(phi, s, w, h) for phi, s, w in parts)
            rows.append(dict(target=k, horizon=h, log_error_sd=float(np.sqrt(v)), floor_wape=wape_from_var(v, rng)))
    F = pd.DataFrame(rows)
    chk = {}
    for k in "EV":
        phi, s, w = PARTS[k][0]
        sim = simulate_check(phi, s, w)
        chk[k] = {h: dict(simulated=sim[h], formula=float(F[(F.target == k) & (F.horizon == h)].floor_wape.iloc[0]) if k == "E" else wape_from_var(var_h(phi, s, w, h), rng)) for h in sim}
    bh = pd.read_csv(OUT / "test" / "by_horizon.csv")
    mdl = bh[bh.model == "primary"].rename(columns={"wape": "model_wape"})[["target", "horizon", "model_wape"]]
    bl = bh[bh.model == "cv_blend"].rename(columns={"wape": "blend_wape"})[["target", "horizon", "blend_wape"]]
    F = F.merge(mdl, on=["target", "horizon"]).merge(bl, on=["target", "horizon"])
    F["model_over_floor"] = F.model_wape / F.floor_wape
    F["blend_over_floor"] = F.blend_wape / F.floor_wape
    F.to_csv(OUT / "noise_floor.csv", index=False)
    mean = F.groupby("target")[["floor_wape", "model_wape", "blend_wape"]].mean()
    json.dump(dict(mean_over_horizons=mean.to_dict("index"), simulation_check=chk, parameters=PARTS,
                   note="lower bound on this simulator: oracle knows the structure exactly; the unemployment-rate noise in seekers is ignored"), open(OUT / "noise_floor.json", "w"), indent=1)
    pd.set_option("display.width", 200)
    print(mean.round(2)); print(json.dumps(chk, indent=1)); print(F[F.horizon.isin([1, 6, 12])].round(2).to_string(index=False))


if __name__ == "__main__":
    main()
