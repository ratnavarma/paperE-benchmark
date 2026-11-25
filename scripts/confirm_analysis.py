"""Frozen confirmation analysis for the Track E PGAI4E note (docs/PROTOCOL_CONFIRMATION_E.md).

Computes exactly the five declared tests C1–C5 from F0-R rows and nothing else. Intervals are
paired bootstrap percentile intervals at level 1 − 0.05/5 = 0.99 (Bonferroni over the family),
10,000 resamples, seed 20261020, unit = seed. A test is "supported" when its 99% interval lies
wholly on the predicted side of its threshold; otherwise "not supported at this size".

Run on development rows to check it reproduces the development values (point estimates):
    uv run python scripts/confirm_analysis.py --rows results/f0r_dev/rows.jsonl.gz \
        --seeds 61000-61099 --out results/confirm_check_dev.json
Run on the confirmation rows (only after Varma's typed "run"):
    uv run python scripts/confirm_analysis.py --rows results/f0r_confirm/rows.jsonl \
        --seeds 500000-500199 --out results/confirm_numbers.json

This file is frozen by docs/MANIFEST_CONFIRMATION.json. Never edit it after the freeze.
"""

from __future__ import annotations

import argparse
import gzip
import json
from collections import defaultdict
from pathlib import Path

import numpy as np

from papere.analysis import Bootstrap, safe_ratio

LEVEL = 1.0 - 0.05 / 5
N_BOOT = 10_000
BOOT_SEED = 20261020
CAND = "guarded_mpc_e1"
# Best oblivious scheduler per delay, fixed on the tuning seeds (paper_numbers e1/primary/M3_*):
# sym_margin (identical to CE-LLF, zero margin) at delta 0, the population MPC at delta >= 1.
BEST_OBLIVIOUS = {0: "sym_margin", 1: "pop_mpc", 2: "pop_mpc", 4: "pop_mpc"}
POLICIES = ("ce_llf", "sym_margin", "mpc_ce", "pop_mpc", "llf_post", CAND)


def cell(rho: str, d: int) -> str:
    return f"F0R_M3_dA{d}_db0_rho{rho}_r0.3"


def load(path: Path, lo: int, hi: int) -> dict[tuple[str, str], dict[int, float]]:
    opener = gzip.open if path.suffix == ".gz" else open
    vals: dict[tuple[str, str], dict[int, float]] = defaultdict(dict)
    with opener(path, "rt") as fh:
        for line in fh:
            r = json.loads(line)
            if r.get("mode") != "frozen" or r["policy"] not in POLICIES:
                continue
            if not (lo <= r["seed"] <= hi) or not r["cell_id"].startswith("F0R_M3_"):
                continue
            key = (r["cell_id"], r["policy"])
            if r["seed"] in vals[key]:
                raise SystemExit(f"duplicate row {key} seed {r['seed']}")
            vals[key][r["seed"]] = float(r["R_avoid_kwh_per100"])
    return vals


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", type=Path, required=True)
    ap.add_argument("--seeds", required=True, help="A-B inclusive")
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    lo, hi = (int(x) for x in a.seeds.split("-"))
    seeds = list(range(lo, hi + 1))
    vals = load(a.rows, lo, hi)

    def v(c: str, p: str) -> np.ndarray:
        got = vals.get((c, p), {})
        missing = [s for s in seeds if s not in got]
        if missing:
            raise SystemExit(f"missing {len(missing)} seeds for {c} / {p} (first {missing[0]})")
        return np.array([got[s] for s in seeds])

    boot = Bootstrap(n_boot=N_BOOT, seed=BOOT_SEED, level=LEVEL)
    out: dict[str, dict] = {}

    def record(name, st, statistic, threshold, side, prediction):
        supported = (st.lo > threshold) if side == ">" else (st.hi < threshold)
        out[name] = {"value": st.value, "ci_lo": st.lo, "ci_hi": st.hi, "level": LEVEL,
                     "n_seeds": len(seeds), "statistic": statistic, "threshold": threshold,
                     "predicted_side": side, "development_prediction": prediction,
                     "verdict": "supported" if supported else "not supported at this size"}

    # C1, C2: E1 at M = 3 for rho 1.15 and 0.95
    for name, rho, pred in (("C1", "1.15", 1.05), ("C2", "0.95", 0.31)):
        gaps = {d: v(cell(rho, d), BEST_OBLIVIOUS[d]) - v(cell(rho, d), CAND) for d in (0, 1, 2, 4)}
        e1 = (gaps[2] + gaps[4]) / 2 - (gaps[0] + gaps[1]) / 2
        st = boot.run({"e1": e1}, {"e1": lambda m: m["e1"]})["e1"]
        record(name, st, f"E1 at M = 3, rho = {rho}: mean gap over delta {{2,4}} minus over {{0,1}}; "
               "gap = R_avoid(best oblivious fixed on tuning seeds) - R_avoid(candidate)", 0.0, ">", pred)

    # C3: gate ratio at M = 3, delta = 2, rho = 0.95
    c = cell("0.95", 2)
    st = boot.run({"obl": v(c, "ce_llf") - v(c, "pop_mpc"), "tot": v(c, "ce_llf") - v(c, CAND)},
                  {"r": lambda m: safe_ratio(m["obl"], m["tot"])})["r"]
    record("C3", st, "ratio of means (ce_llf - pop_mpc)/(ce_llf - candidate), M = 3, delta = 2, rho = 0.95",
           0.5, ">", 0.83)

    # C4: belief-by-rule interaction at delta = 2, rho = 0.95 (residual scale, as declared)
    st = boot.run({"a": v(c, "ce_llf"), "b": v(c, "mpc_ce"), "c": v(c, "llf_post"), "d": v(c, CAND)},
                  {"i": lambda m: (m["a"] - m["b"]) - (m["c"] - m["d"])})["i"]
    record("C4", st, "(ce_llf - mpc_ce) - (llf_post - candidate) on R_avoid, M = 3, delta = 2, rho = 0.95",
           0.0, "<", -4.85)

    # C5: fall of the reliability-blind share under the tight limit, delta 1 minus delta 4, rho = 1.15
    c1, c4 = cell("1.15", 1), cell("1.15", 4)
    st = boot.run({"o1": v(c1, "ce_llf") - v(c1, "pop_mpc"), "t1": v(c1, "ce_llf") - v(c1, CAND),
                   "o4": v(c4, "ce_llf") - v(c4, "pop_mpc"), "t4": v(c4, "ce_llf") - v(c4, CAND)},
                  {"d": lambda m: safe_ratio(m["o1"], m["t1"]) - safe_ratio(m["o4"], m["t4"])})["d"]
    record("C5", st, "share(delta 1) - share(delta 4) at M = 3, rho = 1.15; share = (ce_llf - pop_mpc)/"
           "(ce_llf - candidate), ratios of means, jointly resampled", 0.0, ">", 0.53)

    a.out.write_text(json.dumps({"meta": {"rows": str(a.rows), "seeds": [lo, hi], "level": LEVEL,
                                          "n_boot": N_BOOT, "boot_seed": BOOT_SEED,
                                          "best_oblivious": BEST_OBLIVIOUS},
                                 "tests": out}, indent=1))
    for k, t in out.items():
        print(f"{k}: {t['value']:.3f} [{t['ci_lo']:.3f}, {t['ci_hi']:.3f}]  {t['verdict']}")


if __name__ == "__main__":
    main()
