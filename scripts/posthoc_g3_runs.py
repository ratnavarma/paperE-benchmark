"""Development, post hoc, added after the G3 review: the three added runs.

Reads results/f0r_extra/rows.jsonl.gz (seeds 61000-61099, written by scripts/run_posthoc_g3.py)
and results/TUNING_FROZEN.json (only to name the frozen best oblivious policy of each floor
cell, as paper_numbers does), and writes results/posthoc_g3_runs.json in the paper_numbers schema.
Every statistic is a paired bootstrap over seeds with papere.analysis.Bootstrap (n_boot 10000,
seed 20261020, 95% percentile), the same settings as paper_numbers. None is pre-declared.

Keys (prefix posthoc_runs/):
  sllf/M3_rho{rho}/dA{d}/R_avoid_{policy}            mean R_avoid, kWh per 100 per event
  sllf/.../planning_sllf                            R_avoid(sllf) - R_avoid(mpc_ce), paired
  sllf/.../sllf_minus_cellf                         R_avoid(sllf) - R_avoid(ce_llf), paired
  sllf/.../deadline_miss_count_per100_{sllf,ce_llf} mean misses per 100 per event
  het/split{share}_q{q}/M3_rho{rho}/dA2/{hedging,targeting,oracle_targeting,total_mpcce,
      recovery_share, R_avoid_{policy}, mean_stuck_probability}
  floor_flagged/M3_rho{rho}/dA{d}/{event_shortfall, net_recovery_gain_vs_best_oblivious,
      floor_all_event_shortfall, floor_all_net_recovery_gain, R_avoid_*}

  factorial/M3_rho{rho}/dA{d}/{belief_ce_to_pop_in_llf, belief_pop_to_e1_in_llf,
      belief_ce_to_pop_in_mpc, belief_pop_to_e1_in_mpc, rule_llf_to_mpc_given_ce,
      rule_llf_to_mpc_given_pop, rule_llf_to_mpc_given_e1}, delta_A in {0,1,2,4}. The 2 x 3
      design: rule LLF or MPC, belief CE, population or e1 (CE-LLF = ce_llf, POP-LLF = llf_pop,
      E1-LLF = llf_post, CE-MPC = mpc_ce, POP-MPC = pop_mpc, E1-MPC = guarded_mpc_e1). All in
      the GAIN convention: positive means the second scheduler has the lower R_avoid.
  floor_flagged/M3_rho{rho}/dA{d}/candidate_minus_floor_flagged, delta_A in {2,4}:
      R_avoid(guarded_mpc_e1) - R_avoid(floor_flagged), positive means the flagged floor has
      the lower avoidable residual (floored participants are never stuck, so the floor's R*
      differs from the candidate's).

Run from a clean commit so that meta.git.dirty is false:
  uv run python scripts/posthoc_g3_runs.py
"""
from __future__ import annotations

import gzip
import hashlib
import json
import math
import subprocess
from collections import defaultdict
from pathlib import Path

import numpy as np

from papere.analysis import Bootstrap, Stat, safe_ratio, frozen_best
from papere.generator import generate_f0r
from papere.instance import Cell

ROWS = Path("results/f0r_extra/rows.jsonl.gz")
FROZEN = Path("results/TUNING_FROZEN.json")
OUT = Path("results/posthoc_g3_runs.json")
LABEL = "development, post hoc, added after the G3 review"
PREFIX = "posthoc_runs"
SEEDS = list(range(61000, 61100))
RHOS = (0.95, 1.15)
UNIT = "kWh per 100 per event"
R = "R_avoid_kwh_per100"
MISS = "deadline_miss_count_per100"
SHORT = "event_shortfall_kwh_per100"
METRICS = (R, MISS, SHORT)

SLLF_POLICIES = ("sllf", "ce_llf", "mpc_ce", "pop_mpc", "guarded_mpc_e1", "oracle_mpc")
HET_POLICIES = ("ce_llf", "mpc_ce", "pop_mpc", "guarded_mpc_e1", "oracle_mpc")
# (key label, share, q); the baseline is the default generator (no split fields set)
SPLITS = (("split0.15_q0.88", 0.15, 0.88), ("split0.333_q0.4", None, None),
          ("split0.5_q0.27", 0.5, 0.27))
FACTORIAL = {   # key: (first, second) scheduler; value = R(first) - R(second), gain of moving first -> second
    "belief_ce_to_pop_in_llf": ("ce_llf", "llf_pop"),
    "belief_pop_to_e1_in_llf": ("llf_pop", "llf_post"),
    "belief_ce_to_pop_in_mpc": ("mpc_ce", "pop_mpc"),
    "belief_pop_to_e1_in_mpc": ("pop_mpc", "guarded_mpc_e1"),
    "rule_llf_to_mpc_given_ce": ("ce_llf", "mpc_ce"),
    "rule_llf_to_mpc_given_pop": ("llf_pop", "pop_mpc"),
    "rule_llf_to_mpc_given_e1": ("llf_post", "guarded_mpc_e1"),
}
FACTORIAL_POLICIES = ("ce_llf", "llf_pop", "llf_post", "mpc_ce", "pop_mpc", "guarded_mpc_e1")
FLOOR_NOTE = ("Floored participants are never stuck, so the floor's R* (computed on the "
              "availability its own run faced) differs from the candidate's R*: this is a "
              "difference of avoidable residuals, each against its own run's bound, not a "
              "difference of raw residuals against one common benchmark.")
GIT_SCOPE = ["src", "run_study.py", "scripts/posthoc_g3_runs.py", "scripts/run_posthoc_g3.py",
             "results/f0r_extra", "results/TUNING_FROZEN.json", "results/population_params.json"]


def cid(dA: int, rho: float, split: tuple | None = None) -> str:
    c = Cell(family="F0R", M=3, delta_A=dA, delta_b=0, rho=rho, r=0.3,
             intol_share=None if split is None else split[0],
             q_intol=None if split is None else split[1])
    return c.cell_id


def load_rows() -> dict[tuple[str, str], dict[str, dict[int, float]]]:
    vals: dict = defaultdict(lambda: defaultdict(dict))
    seen = set()
    with gzip.open(ROWS, "rt") as fh:
        for line in fh:
            r = json.loads(line)
            if r.get("mode") != "frozen" or r.get("kind") == "bound":
                continue
            key = (r["cell_id"], r["policy"], r["seed"])
            if key in seen:
                raise SystemExit(f"duplicate row {key}")
            seen.add(key)
            if r["study_family"] != "F0R" or r["N"] != 30:
                raise SystemExit(f"unexpected row {key}")
            if not 61000 <= r["seed"] <= 61099:
                raise SystemExit(f"seed outside the development range: {key}")
            for m in METRICS:
                vals[(r["cell_id"], r["policy"])][m][r["seed"]] = r[m]
    return vals


def vec(vals, cell: str, pol: str, metric: str) -> np.ndarray:
    try:
        d = vals[(cell, pol)][metric]
        v = np.array([d[s] for s in SEEDS], dtype=float)
    except KeyError:
        raise SystemExit(f"missing rows: {cell} {pol} {metric}") from None
    if not np.isfinite(v).all():
        raise SystemExit(f"non-finite values: {cell} {pol} {metric}")
    return v


class Numbers:
    def __init__(self) -> None:
        self.items: dict[str, dict] = {}

    def add(self, key: str, st: Stat, *, cell: str, statistic: str, unit: str = UNIT,
            policies: tuple = (), n: int = len(SEEDS), **extra) -> None:
        key = f"{PREFIX}/{key}"
        if key in self.items:
            raise SystemExit(f"duplicate key {key}")
        flt = (f"mode == frozen and cell_id == {cell} and seed in 61000..61099"
               + (f" and policy in {list(policies)}" if policies else ""))
        self.items[key] = {"value": st.value, "ci_lo": st.lo, "ci_hi": st.hi, "n_seeds": n,
                           "label": LABEL, "unit": unit, "statistic": statistic,
                           "cell_id": cell, "source_file": str(ROWS), "row_filter": flt, **extra}


def clean(o):
    if isinstance(o, dict):
        return {k: clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [clean(v) for v in o]
    if isinstance(o, (np.floating, float)):
        f = float(o)
        return f if math.isfinite(f) else None
    if isinstance(o, np.integer):
        return int(o)
    return o


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_meta() -> dict:
    def run(*a):
        return subprocess.run(["git", *a], capture_output=True, text=True).stdout.strip()
    dirty = bool(run("status", "--porcelain", "--untracked-files=all", "--", *GIT_SCOPE))
    return {"commit": run("rev-parse", "HEAD"), "dirty": dirty, "dirty_scope": GIT_SCOPE}


# ---------------------------------------------------------------------------- sections
def sllf_section(vals, boot: Bootstrap, nums: Numbers) -> None:
    for rho in RHOS:
        for d in (0, 1, 2, 4):
            c = cid(d, rho)
            v = {p: vec(vals, c, p, R) for p in SLLF_POLICIES}
            base = f"sllf/M3_rho{rho:g}/dA{d}"
            res = boot.run(
                dict(v),
                {**{f"R_{p}": (lambda m, p=p: m[p]) for p in SLLF_POLICIES},
                 "planning_sllf": lambda m: m["sllf"] - m["mpc_ce"],
                 "sllf_minus_cellf": lambda m: m["sllf"] - m["ce_llf"]})
            for p in SLLF_POLICIES:
                nums.add(f"{base}/R_avoid_{p}", res[f"R_{p}"], cell=c, policies=(p,),
                         statistic=f"mean {R} of {p}")
            nums.add(f"{base}/planning_sllf", res["planning_sllf"], cell=c,
                     policies=("sllf", "mpc_ce"),
                     statistic=f"mean paired {R}(sllf) - {R}(mpc_ce); positive means "
                               "mpc_ce is better (the gain of planning over smoothed LLF)")
            nums.add(f"{base}/sllf_minus_cellf", res["sllf_minus_cellf"], cell=c,
                     policies=("sllf", "ce_llf"),
                     statistic=f"mean paired {R}(sllf) - {R}(ce_llf); negative means sllf "
                               "is better than ce_llf")
            for p in ("sllf", "ce_llf"):
                m = boot.mean_ci(vec(vals, c, p, MISS))
                nums.add(f"{base}/deadline_miss_count_per100_{p}", m, cell=c, policies=(p,),
                         unit="misses per 100 per event",
                         statistic=f"mean {MISS} of {p}")


def het_means(split: tuple | None) -> np.ndarray:
    """Realized mean stuck probability per instance (instance generation only)."""
    c = Cell(family="F0R", M=3, delta_A=2, delta_b=0, rho=0.95, r=0.3,
             intol_share=None if split is None else split[0],
             q_intol=None if split is None else split[1])
    return np.array([generate_f0r(s, c).q.mean() for s in SEEDS])


def het_section(vals, boot: Bootstrap, nums: Numbers) -> dict:
    exact = {}
    for label, share, q in SPLITS:
        split = None if share is None else (share, q)
        mq = het_means(split)
        st = boot.mean_ci(mq)
        exact[label] = {"mean_stuck_probability": float(mq.mean()), "min": float(mq.min()),
                        "max": float(mq.max()),
                        "nominal": (share if share else 1 / 3) * (q if q else 0.40)
                        + (1 - (share if share else 1 / 3)) * 0.01}
        for rho in RHOS:
            c = cid(2, rho, split)
            v = {p: vec(vals, c, p, R) for p in HET_POLICIES}
            base = f"het/{label}/M3_rho{rho:g}/dA2"
            res = boot.run(
                {**v},
                {**{f"R_{p}": (lambda m, p=p: m[p]) for p in HET_POLICIES},
                 "hedging": lambda m: m["mpc_ce"] - m["pop_mpc"],
                 "targeting": lambda m: m["pop_mpc"] - m["guarded_mpc_e1"],
                 "oracle_targeting": lambda m: m["pop_mpc"] - m["oracle_mpc"],
                 "total_mpcce": lambda m: m["mpc_ce"] - m["guarded_mpc_e1"],
                 "share": lambda m: safe_ratio(m["pop_mpc"] - m["guarded_mpc_e1"],
                                               m["pop_mpc"] - m["oracle_mpc"])})
            terms = {"hedging": ("mpc_ce", "pop_mpc"), "targeting": ("pop_mpc", "guarded_mpc_e1"),
                     "oracle_targeting": ("pop_mpc", "oracle_mpc"),
                     "total_mpcce": ("mpc_ce", "guarded_mpc_e1")}
            for k, (a, b) in terms.items():
                nums.add(f"{base}/{k}", res[k], cell=c, policies=(a, b),
                         statistic=f"mean paired {R}({a}) - {R}({b})")
            den = res["oracle_targeting"]
            defined = bool(math.isfinite(den.lo) and (den.lo > 0 or den.hi < 0))
            sh = res["share"]
            if not defined:
                sh = Stat(sh.value, math.nan, math.nan)
            nums.add(f"{base}/recovery_share", sh, cell=c,
                     policies=("pop_mpc", "guarded_mpc_e1", "oracle_mpc"), unit="ratio",
                     statistic="ratio of means targeting / oracle_targeting, jointly "
                               "resampled; interval withheld (null) when the interval of "
                               "oracle_targeting includes 0",
                     interval_defined=defined)
            for p in HET_POLICIES:
                nums.add(f"{base}/R_avoid_{p}", res[f"R_{p}"], cell=c, policies=(p,),
                         statistic=f"mean {R} of {p}")
            nums.add(f"{base}/mean_stuck_probability", st, cell=c, unit="probability",
                     statistic="mean over instances of the mean per-participant stuck "
                               "probability q (instance generation only; same for both rho)",
                     note=f"nominal mean {exact[label]['nominal']:.4f}")
    return exact


def floor_section(vals, boot: Bootstrap, nums: Numbers, frozen: dict) -> dict:
    bests = {}
    for rho in RHOS:
        for d in (2, 4):
            c = cid(d, rho)
            best = frozen_best(frozen, c)["best"]
            bests[c] = best
            v = {"best": vec(vals, c, best, R), "floor": vec(vals, c, "floor", R),
                 "ff": vec(vals, c, "floor_flagged", R),
                 "s_ff": vec(vals, c, "floor_flagged", SHORT),
                 "s_fl": vec(vals, c, "floor", SHORT)}
            res = boot.run(v, {
                "R_best": lambda m: m["best"], "R_floor": lambda m: m["floor"],
                "R_ff": lambda m: m["ff"],
                "gain_ff": lambda m: m["best"] - m["ff"],
                "gain_fl": lambda m: m["best"] - m["floor"],
                "short_ff": lambda m: m["s_ff"], "short_fl": lambda m: m["s_fl"]})
            base = f"floor_flagged/M3_rho{rho:g}/dA{d}"
            pol = (best, "floor", "floor_flagged")
            nums.add(f"{base}/event_shortfall", res["short_ff"], cell=c, policies=pol,
                     statistic="mean event_shortfall_kwh_per100 of floor_flagged "
                               "(2 units per floored participant); beside, never summed with, "
                               "R_avoid", best_oblivious=best)
            nums.add(f"{base}/net_recovery_gain_vs_best_oblivious", res["gain_ff"], cell=c,
                     policies=pol,
                     statistic=f"mean paired {R}({best}) - {R}(floor_flagged); positive means "
                               "the flagged floor recovers more than the best oblivious policy "
                               "(frozen choice); beside the event shortfall",
                     best_oblivious=best)
            nums.add(f"{base}/floor_all_event_shortfall", res["short_fl"], cell=c, policies=pol,
                     statistic="mean event_shortfall_kwh_per100 of floor (everyone)",
                     best_oblivious=best)
            nums.add(f"{base}/floor_all_net_recovery_gain", res["gain_fl"], cell=c, policies=pol,
                     statistic=f"mean paired {R}({best}) - {R}(floor); same statistic as "
                               "secondary/floor/<cell>/net_recovery_gain in paper_numbers.json",
                     best_oblivious=best)
            for nm, k in (("best_oblivious", "R_best"), ("floor", "R_floor"),
                          ("floor_flagged", "R_ff")):
                nums.add(f"{base}/R_avoid_{nm}", res[k], cell=c,
                         policies=(best if nm == "best_oblivious" else nm,),
                         statistic=f"mean {R} of {best if nm == 'best_oblivious' else nm}",
                         best_oblivious=best)
    return bests


def factorial_section(vals, boot: Bootstrap, nums: Numbers) -> None:
    for rho in RHOS:
        for d in (0, 1, 2, 4):
            c = cid(d, rho)
            v = {p: vec(vals, c, p, R) for p in FACTORIAL_POLICIES}
            res = boot.run(dict(v), {k: (lambda m, a=a, b=b: m[a] - m[b])
                                     for k, (a, b) in FACTORIAL.items()})
            for k, (a, b) in FACTORIAL.items():
                nums.add(f"factorial/M3_rho{rho:g}/dA{d}/{k}", res[k], cell=c, policies=(a, b),
                         statistic=f"mean paired {R}({a}) - {R}({b}); gain convention, "
                                   f"positive means {b} has the lower R_avoid")


def floor_candidate_section(vals, boot: Bootstrap, nums: Numbers) -> None:
    for rho in RHOS:
        for d in (2, 4):
            c = cid(d, rho)
            v = {"cand": vec(vals, c, "guarded_mpc_e1", R),
                 "ff": vec(vals, c, "floor_flagged", R)}
            res = boot.run(v, {"d": lambda m: m["cand"] - m["ff"]})
            nums.add(f"floor_flagged/M3_rho{rho:g}/dA{d}/candidate_minus_floor_flagged",
                     res["d"], cell=c, policies=("guarded_mpc_e1", "floor_flagged"),
                     statistic=f"mean paired {R}(guarded_mpc_e1) - {R}(floor_flagged); "
                               "positive means the flagged floor has the lower avoidable "
                               "residual (gain convention)",
                     note=FLOOR_NOTE)


def main() -> None:
    vals = load_rows()
    frozen = json.loads(FROZEN.read_text())
    boot = Bootstrap()
    nums = Numbers()
    sllf_section(vals, boot, nums)
    exact = het_section(vals, boot, nums)
    bests = floor_section(vals, boot, nums, frozen)
    factorial_section(vals, boot, nums)
    floor_candidate_section(vals, boot, nums)
    meta = {"label": LABEL, "git": git_meta(),
            "input_sha256": {str(ROWS): sha(ROWS), str(FROZEN): sha(FROZEN),
                             "results/f0r_extra/manifest.json": sha(ROWS.parent / "manifest.json")},
            "bootstrap": {"n_boot": boot.n_boot, "seed": boot.seed, "level": boot.level,
                          "method": "paired percentile bootstrap over seeds (analysis.Bootstrap)"},
            "seeds": [SEEDS[0], SEEDS[-1]], "n_seeds": len(SEEDS),
            "het_split_means": exact, "floor_best_oblivious": bests,
            "note": "None of these numbers is a pre-declared endpoint. e1 population prior and "
                    "frozen configurations were fitted on the baseline split; the off-baseline "
                    "splits test a mis-specified prior."}
    OUT.write_text(json.dumps(clean({"meta": meta, "numbers": nums.items}), indent=1))
    print(f"wrote {OUT}: {len(nums.items)} numbers, dirty={meta['git']['dirty']}")
    for k, v in nums.items.items():
        if any(s in k for s in ("planning_sllf", "sllf_minus_cellf", "targeting", "hedging",
                                "total_mpcce", "recovery_share", "event_shortfall",
                                "net_recovery", "R_avoid_sllf", "mean_stuck",
                                "factorial", "candidate_minus")):
            lo, hi = v["ci_lo"], v["ci_hi"]
            f = lambda x: "null" if x is None or not math.isfinite(x) else f"{x:.3f}"
            print(f"{k}: {v['value']:.3f} [{f(lo)}, {f(hi)}]")


if __name__ == "__main__":
    main()
