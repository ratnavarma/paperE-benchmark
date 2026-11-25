"""Post hoc, descriptive: share of the candidate's gain over CE-LLF that reliability-oblivious layers carry.

share = (R_avoid(ce_llf) - R_avoid(pop_mpc)) / (R_avoid(ce_llf) - R_avoid(guarded_mpc_e1)),
a ratio of means with a paired bootstrap over seeds (the analysis module's Bootstrap, same
settings). Added on 2026-10-20 after DEV_REPORT_E, for the manuscript's title claim. It is
not a pre-declared endpoint.

Run: uv run python scripts/posthoc_oblivious_share.py
Writes results/posthoc_oblivious_share.json in the paper_numbers schema. Also (G3 review): the
second decomposition path and a Shapley split over belief x rule, the simple per-participant rules
against the candidate at the gate cell, and the paired violation difference.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import subprocess
from collections import defaultdict
from pathlib import Path

import numpy as np

from papere.analysis import Bootstrap, safe_ratio

ROWS = Path("results/f0r_dev/rows.jsonl.gz")
OUT = Path("results/posthoc_oblivious_share.json")
POLICIES = ("ce_llf", "pop_mpc", "guarded_mpc_e1")
ALL_POLICIES = ("ce_llf", "pop_mpc", "guarded_mpc_e1", "mpc_ce", "llf_post", "persistence",
                "uncorr_pes", "user_flag", "rwdf_e", "oracle_mpc")
LABEL = "descriptive, post hoc, added after DEV_REPORT_E"


def main() -> None:
    vals: dict[tuple[str, str], dict[int, float]] = defaultdict(dict)
    viol: dict[tuple[str, str], dict[int, float]] = defaultdict(dict)
    with gzip.open(ROWS, "rt") as fh:
        for line in fh:
            r = json.loads(line)
            if r.get("mode") != "frozen" or r["policy"] not in ALL_POLICIES:
                continue
            vals[(r["cell_id"], r["policy"])][r["seed"]] = r["R_avoid_kwh_per100"]
            viol[(r["cell_id"], r["policy"])][r["seed"]] = r["violation_kwslot"]
    boot = Bootstrap()
    numbers = {}
    for rho in ("0.95", "1.15"):
        for dA in (1, 2, 4):
            cell = f"F0R_M3_dA{dA}_db0_rho{rho}_r0.3"
            seeds = sorted(set.intersection(*(set(vals[(cell, p)]) for p in POLICIES)))
            v = {p: np.array([vals[(cell, p)][s] for s in seeds]) for p in POLICIES}
            res = boot.run(
                {"obl": v["ce_llf"] - v["pop_mpc"], "tot": v["ce_llf"] - v["guarded_mpc_e1"]},
                {"share": lambda m: safe_ratio(m["obl"], m["tot"]),
                 "oblivious_gain": lambda m: m["obl"], "total_gain": lambda m: m["tot"]})
            for name, st in res.items():
                numbers[f"posthoc/oblivious_share/M3_rho{rho}/dA{dA}/{name}"] = {
                    "value": st.value, "ci_lo": st.lo, "ci_hi": st.hi, "n_seeds": len(seeds),
                    "label": LABEL, "unit": "ratio" if name == "share" else "kWh per 100 per event",
                    "source_file": str(ROWS), "cell_id": cell,
                    "statistic": "ratio of means (ce_llf - pop_mpc) / (ce_llf - guarded_mpc_e1)"
                    if name == "share" else f"mean paired difference ({name})"}
    def put(key, st, n, unit, statistic, cell):
        numbers[key] = {"value": st.value, "ci_lo": st.lo, "ci_hi": st.hi, "n_seeds": n,
                        "label": LABEL, "unit": unit, "source_file": str(ROWS),
                        "cell_id": cell, "statistic": statistic}

    def vec(cell, pols, src=vals):
        seeds = sorted(set.intersection(*(set(src[(cell, q)]) for q in pols)))
        return seeds, {q: np.array([src[(cell, q)][s] for s in seeds]) for q in pols}

    kwh = "kWh per 100 per event"
    for rho in ("0.95", "1.15"):
        for dA in (1, 2, 4):
            cell = f"F0R_M3_dA{dA}_db0_rho{rho}_r0.3"
            pre = f"posthoc/order/M3_rho{rho}/dA{dA}"
            seeds, v = vec(cell, ("ce_llf", "mpc_ce", "llf_post", "guarded_mpc_e1"))
            # 2 x 2: belief {CE, posterior} x rule {LLF, MPC}; the candidate is posterior-MPC
            res = boot.run(
                {"a": v["ce_llf"], "b": v["mpc_ce"], "c": v["llf_post"], "d": v["guarded_mpc_e1"]},
                {"path2_belief_first": lambda m: m["a"] - m["c"],
                 "path2_rule_second": lambda m: m["c"] - m["d"],
                 "shapley_rule": lambda m: 0.5 * ((m["a"] - m["b"]) + (m["c"] - m["d"])),
                 "shapley_belief": lambda m: 0.5 * ((m["a"] - m["c"]) + (m["b"] - m["d"])),
                 "interaction": lambda m: (m["a"] - m["b"]) - (m["c"] - m["d"])})
            for name, st in res.items():
                put(f"{pre}/{name}", st, len(seeds), kwh,
                    {"path2_belief_first": "ce_llf - llf_post", "path2_rule_second": "llf_post - candidate",
                     "shapley_rule": "mean of (ce_llf - mpc_ce) and (llf_post - candidate)",
                     "shapley_belief": "mean of (ce_llf - llf_post) and (mpc_ce - candidate)",
                     "interaction": "(ce_llf - mpc_ce) - (llf_post - candidate)"}[name], cell)
    cell = "F0R_M3_dA2_db0_rho0.95_r0.3"
    for rule in ("persistence", "uncorr_pes", "user_flag", "rwdf_e", "llf_post"):
        seeds, v = vec(cell, (rule, "guarded_mpc_e1"))
        st = boot.run({"x": v[rule] - v["guarded_mpc_e1"]}, {"x": lambda m: m["x"]})["x"]
        put(f"posthoc/rules/gate/{rule}_minus_candidate", st, len(seeds), kwh,
            f"mean paired R_avoid({rule}) - R_avoid(guarded_mpc_e1)", cell)
    seeds, v = vec(cell, ("guarded_mpc_e1", "ce_llf"), viol)
    st = boot.run({"x": v["guarded_mpc_e1"] - v["ce_llf"]}, {"x": lambda m: m["x"]})["x"]
    put("posthoc/violation/gate/candidate_minus_ce_llf", st, len(seeds), "kW·slot per event",
        "mean paired violation_kwslot(guarded_mpc_e1) - violation_kwslot(ce_llf)", cell)

    # Violation-discounted gains (referee report, major 2): energy above the realized limit counts
    # as undelivered. 1 kW·slot = 0.25 kWh; per 100 participants = x 100 / N.
    def discounted_rows(path):
        d = defaultdict(dict)
        opener = gzip.open if str(path).endswith(".gz") else open
        with opener(path, "rt") as fh:
            for line in fh:
                r = json.loads(line)
                if r.get("mode") != "frozen" or r["policy"] not in ("ce_llf", "pop_mpc", "guarded_mpc_e1"):
                    continue
                d[(r["cell_id"], r["policy"])][r["seed"]] = (
                    r["R_avoid_kwh_per100"] + r["violation_kwslot"] * 0.25 * 100.0 / r["N"])
        return d

    for tag, path in (("dev", ROWS), ("confirm", Path("results/f0r_confirm/rows.jsonl"))):
        if not Path(path).exists():
            continue
        dd = discounted_rows(path)
        for rho in ("0.95", "1.15"):
            cell = f"F0R_M3_dA2_db0_rho{rho}_r0.3"
            seeds, v = vec(cell, ("ce_llf", "pop_mpc", "guarded_mpc_e1"), dd)
            res = boot.run({"t": v["ce_llf"] - v["guarded_mpc_e1"], "g": v["pop_mpc"] - v["guarded_mpc_e1"]},
                           {"total": lambda m: m["t"], "targeting": lambda m: m["g"]})
            for name, st in res.items():
                put(f"posthoc/discounted/{tag}/M3_rho{rho}/dA2/{name}", st, len(seeds), kwh,
                    "violation-discounted gain: R_avoid + violation energy, "
                    + ("ce_llf - candidate" if name == "total" else "pop_mpc - candidate"), cell)
                numbers[f"posthoc/discounted/{tag}/M3_rho{rho}/dA2/{name}"]["source_file"] = str(path)

    commit = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    dirty = bool(subprocess.run(["git", "status", "--porcelain", "src", "scripts"],
                                capture_output=True, text=True).stdout.strip())
    meta = {"label": LABEL, "git": {"commit": commit, "dirty": dirty},
            "input_sha256": hashlib.sha256(ROWS.read_bytes()).hexdigest(),
            "bootstrap": {"n_boot": boot.n_boot, "seed": boot.seed, "level": boot.level}}
    OUT.write_text(json.dumps({"meta": meta, "numbers": numbers}, indent=1))
    for k, v in numbers.items():
        print(k, round(v["value"], 3), round(v["ci_lo"], 3), round(v["ci_hi"], 3))


if __name__ == "__main__":
    main()
