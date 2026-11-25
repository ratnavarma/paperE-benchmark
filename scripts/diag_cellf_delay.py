"""Diagnostic: why CE-LLF leaves less avoidable residual at delta 4 than at delta 1 (review plan P11, author D3,
2026-11-18).

A policy run on the 50 tuning seeds 60000-60049 only, at M = 3, r = 0.3, delta_b = 0, both stress levels, for CE-LLF
and CE-MPC with their frozen configurations (results/TUNING_FROZEN.json). No development or reserved seed is used.
Nothing is written to a rows file; the output is results/diag_cellf_delay.json, merged into the build.

Per run it counts, in units of 0.25 kWh:
  sent          all setpoint units
  to_stuck      setpoint units sent to a participant who is unavailable in that slot (they deliver nothing)
  retry_stuck   to_stuck units sent to a participant whose earlier setpoint in this event had already failed
  delivered     delivered units
and R_avoid in kWh per 100 participants per event (the ledger's own evaluate). Statistics: paired delta 4 minus
delta 1 per seed, analysis-module Bootstrap (95% percentile). Labelled tuning seeds, post hoc, diagnostic.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from papere import runner  # noqa: E402
from papere.analysis import Bootstrap  # noqa: E402
from papere.ledger import evaluate  # noqa: E402
from papere.sim import simulate  # noqa: E402

SEEDS = range(60000, 60050)
POLICIES = ("ce_llf", "mpc_ce")
OUT = ROOT / "results" / "diag_cellf_delay.json"
PER100 = 100.0 / 30.0


def counts(traj) -> dict:
    x, A, y = np.asarray(traj.x), np.asarray(traj.A), np.asarray(traj.y)
    stuck_send = (x > 0) & (A == 0)
    earlier_fail = np.cumsum(stuck_send, axis=1) - stuck_send  # failed setpoints before slot t
    return {"sent": float(x.sum()), "to_stuck": float((x * (A == 0)).sum()),
            "retry_stuck": float((x * ((A == 0) & (earlier_fail > 0))).sum()), "delivered": float(y.sum())}


def main() -> None:
    fams = runner.load_families()
    params = runner.load_params(ROOT / "results" / "population_params.json")
    frozen = json.loads((ROOT / "results" / "TUNING_FROZEN.json").read_text())
    frozen = frozen.get("frozen", frozen)
    runner._CTX.update({"f0r_N": 30, "params": params})
    by_name = {f.name: f for f in fams}
    cells = {c.cell_id: c for c in runner.study_cells("F0R")}
    data: dict = {}
    for rho in ("0.95", "1.15"):
        for d in (1, 4):
            cid = f"F0R_M3_dA{d}_db0_rho{rho}_r0.3"
            cell = cells[cid]
            units = runner.plan_units(fams, "frozen", cell, frozen, set(POLICIES))
            for seed in SEEDS:
                inst = runner._make_instance("F0R", seed, cell)
                for fam_name, sim_name, cfg_fam, cfg_idx in units:
                    src = by_name[cfg_fam]
                    cfg = src.default if cfg_idx < 0 else src.grid[cfg_idx]
                    traj = simulate(inst, cell, runner._Named(by_name[fam_name].make(cfg, params), sim_name), seed)
                    row = evaluate(inst, traj)
                    c = counts(traj)
                    c["R_avoid"] = float(row["R_avoid_kwh"]) * PER100
                    data[(rho, d, sim_name, seed)] = c
    boot = Bootstrap()
    nums = {}
    lab = "tuning seeds 60000-60049, post hoc diagnostic (Applied Energy revision 2026-11-18), not a test"
    for rho in ("0.95", "1.15"):
        for pol in POLICIES:
            for m in ("R_avoid", "sent", "to_stuck", "retry_stuck", "delivered"):
                for d in (1, 4):
                    v = np.array([data[(rho, d, pol, s)][m] for s in SEEDS])
                    v = v if m == "R_avoid" else v * 0.25 * PER100  # units -> kWh per 100 per event
                    st = boot.mean_ci(v)
                    nums[f"diag_cellf/M3_rho{rho}/{pol}/dA{d}/{m}"] = {
                        "value": st.value, "ci_lo": st.lo, "ci_hi": st.hi, "n_seeds": len(SEEDS),
                        "unit": "kWh per 100 per event", "label": lab, "statistic": f"mean {m}"}
                dv = np.array([data[(rho, 4, pol, s)][m] - data[(rho, 1, pol, s)][m] for s in SEEDS])
                dv = dv if m == "R_avoid" else dv * 0.25 * PER100
                st = boot.mean_ci(dv)
                nums[f"diag_cellf/M3_rho{rho}/{pol}/dA4_minus_dA1/{m}"] = {
                    "value": st.value, "ci_lo": st.lo, "ci_hi": st.hi, "n_seeds": len(SEEDS),
                    "unit": "kWh per 100 per event", "label": lab, "statistic": f"mean paired {m}(delta 4) - {m}(delta 1)"}
    OUT.write_text(json.dumps({"meta": {"script": "scripts/diag_cellf_delay.py", "seeds": [60000, 60049]},
                               "numbers": nums}, indent=1) + "\n", encoding="utf-8")
    print(f"wrote {OUT} ({len(nums)} numbers)")


if __name__ == "__main__":
    main()
