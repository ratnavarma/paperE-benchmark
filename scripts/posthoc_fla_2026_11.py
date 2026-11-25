"""Numbers for the Applied Energy revision of 2026-11-18 (review plan P7, P8, P9, P11; author decisions D1, D2).

Read-only on rows that already exist. No policy is run and no seed is drawn. Output: results/posthoc_fla.json,
merged into the build by paper/build.py (EXTRA_NUMBERS). Intervals: the analysis module's paired Bootstrap
(10,000 resamples, 95% percentile, fixed seed), as in posthoc_oblivious_share.py.

D1 (confirmation, descriptive; the frozen protocol, section 3, promised these): per-cell means on the reserved
   seeds 500000-500199, read from results/f0r_confirm/rows.jsonl as written by the frozen run. Five policies:
   ce_llf, mpc_ce, pop_mpc, guarded_mpc_e1, oracle_mpc (sym_margin equals ce_llf at margin 0 and llf_post is in
   the release). Metrics: R_avoid (kWh per 100 per event), deadline misses (count per 100 per event) and limit
   excess (feeder kWh per event, violation_kwslot x 0.25). Also the gap (best oblivious fixed on tuning seeds
   minus Targeted MPC) per delay, the quantity behind C1 and C2. Not a test.
D2 (development seeds 61000-61099, post hoc, descriptive):
   fla/obligation/*      mean obligation E in kWh per 100 participants per event at the reference cell, and the
                         total gain and targeting gain as a percent of it (ratio of means x 100)
   fla/split_share/*     the reliability-blind share (ce_llf - pop_mpc)/(ce_llf - guarded_mpc_e1) under the three
                         failure splits at delta 2 (baseline split from f0r_dev, others from f0r_extra)
   fla/cempc_share/*     the same share with CE-MPC as the base: (mpc_ce - pop_mpc)/(mpc_ce - guarded_mpc_e1)
   fla/scale_share/*     the share at N = 300 (results/scale_dev, seeds 63000-63019)
   fla/ranker_vs_mpc/*   paired R_avoid(greedy_ev_pop) - R_avoid(pop_mpc), the shared-rate ranker against
                         Shared-rate MPC (results/f0r_posthoc_ranker)
"""
from __future__ import annotations

import gzip
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from papere.analysis import Bootstrap, safe_ratio  # noqa: E402

OUT = ROOT / "results" / "posthoc_fla.json"
KWH_PER_KWSLOT = 0.25
RHOS = ("0.95", "1.15")
DELTAS = (0, 1, 2, 4)
D1_POLICIES = ("ce_llf", "mpc_ce", "pop_mpc", "guarded_mpc_e1", "oracle_mpc")
BEST_OBLIVIOUS = {0: "ce_llf", 1: "pop_mpc", 2: "pop_mpc", 4: "pop_mpc"}  # frozen on tuning seeds; sym_margin at
# delta 0 is ce_llf with margin 0 (identical rows, checked below)
SPLITS = {"split0.333_q0.4": "", "split0.15_q0.88": "_split0.15_q0.88", "split0.5_q0.27": "_split0.5_q0.27"}
METRICS = ("R_avoid_kwh_per100", "deadline_miss_count_per100", "violation_kwslot", "E_kwh_per100")


def open_rows(d: Path):
    p = d / "rows.jsonl"
    return open(p, encoding="utf-8") if p.exists() else gzip.open(d / "rows.jsonl.gz", "rt", encoding="utf-8")


def load(d: Path, seed_range: tuple[int, int]) -> dict:
    """{(cell, policy): {metric: {seed: value}}} for frozen rows inside seed_range."""
    vals: dict = defaultdict(lambda: defaultdict(dict))
    with open_rows(d) as fh:
        for line in fh:
            r = json.loads(line)
            if r.get("mode", "frozen") != "frozen" or not seed_range[0] <= r["seed"] <= seed_range[1]:
                continue
            for m in METRICS:
                if m in r:
                    vals[(r["cell_id"], r["policy"])][m][r["seed"]] = r[m]
    return vals


def aligned(vals, cell, pols, metric):
    seeds = sorted(set.intersection(*(set(vals[(cell, p)][metric]) for p in pols)))
    if not seeds:
        raise SystemExit(f"no aligned seeds for {cell} {pols} {metric}")
    return seeds, {p: np.array([vals[(cell, p)][metric][s] for s in seeds], dtype=float) for p in pols}


def entry(st, n, unit, statistic, source, label, cell):
    return {"value": st.value, "ci_lo": st.lo, "ci_hi": st.hi, "n_seeds": n, "unit": unit, "statistic": statistic,
            "source_file": source, "label": label, "cell_id": cell}


def main() -> None:
    boot = Bootstrap()
    nums: dict = {}

    # ---------------------------------------------------------------- D1: confirmation per-cell means
    conf_dir = ROOT / "results" / "f0r_confirm"
    conf = load(conf_dir, (500000, 500199))
    lab1 = "confirmation, descriptive (frozen protocol section 3), reserved seeds 500000-500199, not a test"
    src1 = "results/f0r_confirm/rows.jsonl"
    for rho in RHOS:
        for d in DELTAS:
            cell = f"F0R_M3_dA{d}_db0_rho{rho}_r0.3"
            if d == 0:  # sym_margin at margin 0 must equal ce_llf, row for row
                _, v = aligned(conf, cell, ("ce_llf", "sym_margin"), "R_avoid_kwh_per100")
                assert np.array_equal(v["ce_llf"], v["sym_margin"]), cell
            for p in D1_POLICIES:
                for m, unit, scale in (("R_avoid_kwh_per100", "kWh per 100 per event", 1.0),
                                       ("deadline_miss_count_per100", "misses per 100 per event", 1.0),
                                       ("violation_kwslot", "kWh per event, feeder total", KWH_PER_KWSLOT)):
                    seeds, v = aligned(conf, cell, (p,), m)
                    st = boot.mean_ci(v[p] * scale)
                    name = {"violation_kwslot": "violation_kwh"}.get(m, m)
                    nums[f"confirm_cell/M3_rho{rho}/dA{d}/{p}/{name}"] = entry(
                        st, len(seeds), unit, f"mean of {m}" + (" x 0.25" if scale != 1 else ""), src1, lab1, cell)
            comp = BEST_OBLIVIOUS[d]
            seeds, v = aligned(conf, cell, (comp, "guarded_mpc_e1"), "R_avoid_kwh_per100")
            st = boot.mean_ci(v[comp] - v["guarded_mpc_e1"])
            nums[f"confirm_cell/M3_rho{rho}/dA{d}/gap"] = entry(
                st, len(seeds), "kWh per 100 per event", f"mean paired R_avoid({comp}) - R_avoid(guarded_mpc_e1)",
                src1, lab1, cell)

    # ---------------------------------------------------------------- D2: development rows
    lab2 = "development seeds, post hoc, descriptive (Applied Energy revision 2026-11-18)"
    dev = load(ROOT / "results" / "f0r_dev", (61000, 61099))
    extra = load(ROOT / "results" / "f0r_extra", (61000, 61099))
    rank = load(ROOT / "results" / "f0r_posthoc_ranker", (61000, 61099))
    scale = load(ROOT / "results" / "scale_dev", (63000, 63019))

    def share(vals, cell, base, src, key, n_note=""):
        pols = (base, "pop_mpc", "guarded_mpc_e1")
        seeds, v = aligned(vals, cell, pols, "R_avoid_kwh_per100")
        res = boot.run({"obl": v[base] - v["pop_mpc"], "tot": v[base] - v["guarded_mpc_e1"]},
                       {"share": lambda m: safe_ratio(m["obl"], m["tot"])})
        nums[key] = entry(res["share"], len(seeds), "ratio",
                          f"ratio of means ({base} - pop_mpc) / ({base} - guarded_mpc_e1){n_note}", src, lab2, cell)

    for rho in RHOS:
        ref = f"F0R_M3_dA2_db0_rho{rho}_r0.3"
        # obligation and gains as a percent of it
        pols = ("ce_llf", "pop_mpc", "guarded_mpc_e1")
        seeds, r = aligned(dev, ref, pols, "R_avoid_kwh_per100")
        _, e = aligned(dev, ref, ("ce_llf",), "E_kwh_per100")
        res = boot.run({"E": e["ce_llf"], "tot": r["ce_llf"] - r["guarded_mpc_e1"],
                        "tgt": r["pop_mpc"] - r["guarded_mpc_e1"]},
                       {"E": lambda m: m["E"], "total_pct": lambda m: 100 * safe_ratio(m["tot"], m["E"]),
                        "targeting_pct": lambda m: 100 * safe_ratio(m["tgt"], m["E"])})
        nums[f"fla/obligation/M3_rho{rho}/dA2/E_kwh_per100"] = entry(
            res["E"], len(seeds), "kWh per 100 per event", "mean obligation E_kwh_per100", "results/f0r_dev", lab2, ref)
        for k in ("total_pct", "targeting_pct"):
            nums[f"fla/obligation/M3_rho{rho}/dA2/{k}"] = entry(
                res[k], len(seeds), "percent of the obligation",
                "100 x mean gain / mean obligation; total = ce_llf - guarded_mpc_e1, targeting = pop_mpc - "
                "guarded_mpc_e1", "results/f0r_dev", lab2, ref)
        # share under the three splits
        for name, suffix in SPLITS.items():
            vals, src = (dev, "results/f0r_dev") if not suffix else (extra, "results/f0r_extra")
            share(vals, ref + suffix, "ce_llf", src, f"fla/split_share/{name}/M3_rho{rho}/dA2/share")
        # CE-MPC as the base
        share(dev, ref, "mpc_ce", "results/f0r_dev", f"fla/cempc_share/M3_rho{rho}/dA2/share")
        # shared-rate ranker against Shared-rate MPC
        seeds, v = aligned(rank, ref, ("greedy_ev_pop", "pop_mpc"), "R_avoid_kwh_per100")
        nums[f"fla/ranker_vs_mpc/M3_rho{rho}/dA2/greedy_ev_pop_minus_pop_mpc"] = entry(
            boot.mean_ci(v["greedy_ev_pop"] - v["pop_mpc"]), len(seeds), "kWh per 100 per event",
            "mean paired R_avoid(greedy_ev_pop) - R_avoid(pop_mpc)", "results/f0r_posthoc_ranker", lab2, ref)
    share(scale, "SCALE_M3_dA2_db0_rho0.95_r0.3", "ce_llf", "results/scale_dev",
          "fla/scale_share/M3_rho0.95/dA2/share", ", N = 300, 20 seeds")

    # the baseline split must reproduce the published development share
    pub = json.loads((ROOT / "results" / "posthoc_oblivious_share.json").read_text())["numbers"]
    for rho in RHOS:
        a = nums[f"fla/split_share/split0.333_q0.4/M3_rho{rho}/dA2/share"]["value"]
        b = pub[f"posthoc/oblivious_share/M3_rho{rho}/dA2/share"]["value"]
        assert abs(a - b) < 1e-12, (rho, a, b)

    meta = {"script": "scripts/posthoc_fla_2026_11.py", "bootstrap": {"n_boot": boot.n_boot, "seed": boot.seed,
            "level": boot.level, "interval": "percentile"}, "keys": len(nums)}
    OUT.write_text(json.dumps({"meta": meta, "numbers": nums}, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {OUT} ({len(nums)} numbers)")


if __name__ == "__main__":
    main()
