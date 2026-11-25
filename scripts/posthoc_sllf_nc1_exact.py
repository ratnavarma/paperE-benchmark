"""Development, post hoc, added after the G3 review: sLLF on NC1-exact, beside ce_llf.

NC1-exact (NC_REPORT): deterministic availability (every participant available every slot),
base load constant at B0 = N and noise free (the last-value forecast is exact), cell
F0R_M3_dA0_db0_rho0.7_r0.3_det, tuning seeds 60000-60049. A feasible schedule exists.
Reports on how many of the 50 seeds R_avoid != 0 for sllf and ce_llf (units of 0.25 kWh).

Run: uv run python scripts/posthoc_sllf_nc1_exact.py
Writes results/posthoc_sllf_nc1_exact.json.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import numpy as np

import negative_controls as nc
from papere.generator import generate_f0r
from papere.ledger import evaluate
from papere.policies.catalog import FAMILIES
from papere.policies.posthoc import SmoothedLLF
from papere.runner import load_params
from papere.sim import simulate

OUT = Path("results/posthoc_sllf_nc1_exact.json")
LABEL = "development, post hoc, added after the G3 review"
SEEDS = range(60000, 60050)


def main() -> None:
    params = load_params("results/population_params.json")
    ce = next(f for f in FAMILIES if f.name == "ce_llf")
    res: dict[str, list[float]] = {"sllf": [], "ce_llf": []}
    for seed in SEEDS:
        inst = nc.exact_base_instance(generate_f0r(seed, nc.NC1_CELL))
        for name, pol in (("sllf", SmoothedLLF()),
                          ("ce_llf", ce.make(dict(ce.default), params))):
            ev = evaluate(inst, simulate(inst, nc.NC1_CELL, pol, seed))
            res[name].append(float(ev["R_avoid_u"]))
    out = {"label": LABEL, "cell_id": nc.NC1_CELL.cell_id, "seeds": [SEEDS[0], SEEDS[-1]],
           "note": "NC1-exact instance built by negative_controls.exact_base_instance; "
                   "R_avoid in units (1 unit = 0.25 kWh)", "policies": {}}
    for name, v in res.items():
        a = np.array(v)
        out["policies"][name] = {"n_seeds": len(v), "n_R_avoid_zero": int((a == 0).sum()),
                                 "n_R_avoid_nonzero": int((a != 0).sum()),
                                 "max": float(a.max()), "min": float(a.min()),
                                 "mean": float(a.mean()), "R_avoid_u": v}
    out["git_commit"] = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                                       text=True).stdout.strip()
    OUT.write_text(json.dumps(out, indent=1))
    for name, d in out["policies"].items():
        print(name, "R_avoid == 0 on", d["n_R_avoid_zero"], "of", d["n_seeds"],
              "| nonzero", d["n_R_avoid_nonzero"], "max", d["max"], "mean", round(d["mean"], 3))


if __name__ == "__main__":
    main()
