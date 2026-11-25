"""Descriptive, post hoc, added 2026-11-02 at the referee's request: the greedy expected-value
hedge ranker against the planners and LLF (docs/RANKER_POSTHOC.md).

Reads
  results/f0r_posthoc_ranker/rows.jsonl.gz  greedy_ev, greedy_ev_pop, greedy_ev_ce (frozen from
      results/TUNING_FROZEN_posthoc_ranker.json) and the rerun comparators ce_llf, pop_mpc,
      guarded_mpc_e1 (written by scripts/run_posthoc_ranker.py run)
  results/f0r_extra/rows.jsonl.gz           ce_llf, llf_pop, llf_post, mpc_ce, pop_mpc,
      guarded_mpc_e1 (the factorial's rows)
  results/posthoc_g3_runs.json              the factorial's published numbers (checked equal)
and writes results/posthoc_ranker.json in the paper_numbers schema. Seeds 61000-61099 only.
Every interval is a paired percentile bootstrap over seeds with papere.analysis.Bootstrap at
its defaults (n_boot 10000, seed 20261020, 95%), the settings of paper_numbers. Nothing here is
pre-declared.

Checks (the script stops if one fails): the rerun comparators equal the f0r_extra rows seed by
seed (R_avoid, violations, deadline misses, realized availability hash); the recomputed LLF and
MPC factorial steps equal results/posthoc_g3_runs.json.

Keys (prefix posthoc_ranker/, cell M3_rho{rho}/dA{d}, delta_A in {0,1,2,4}, rho in {0.95,1.15}):
  R_avoid_{greedy_ev,greedy_ev_pop,greedy_ev_ce}           mean R_avoid, kWh per 100 per event
  greedy_ev_minus_ce_llf                                   R(greedy_ev) - R(ce_llf)
  greedy_ev_minus_targeted_mpc                             R(greedy_ev) - R(guarded_mpc_e1)
  greedy_ev_pop_minus_shared_rate_mpc                      R(greedy_ev_pop) - R(pop_mpc)
      (difference convention: negative means the ranker has the lower R_avoid)
  belief_{ce_to_pop,pop_to_e1}_in_{greedy,llf,mpc}         gain convention as the factorial:
      R(first) - R(second), positive means the second belief has the lower R_avoid
  belief_step_greedy_minus_llf, belief_step_mpc_minus_greedy   differences of the pop -> e1 step
  rule_llf_to_greedy_given_{ce,pop,e1}, rule_greedy_to_mpc_given_{ce,pop,e1}   gain convention
  violation_kwslot_{greedy_ev,greedy_ev_pop}, violation_greedy_ev_minus_ce_llf   kW·slot per event
  deadline_miss_count_per100_{greedy_ev,greedy_ev_pop}

Run: uv run python scripts/posthoc_ranker.py
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

from papere.analysis import Bootstrap, Stat
from papere.instance import Cell

ROWS = Path("results/f0r_posthoc_ranker/rows.jsonl.gz")
EXTRA_ROWS = Path("results/f0r_extra/rows.jsonl.gz")
G3 = Path("results/posthoc_g3_runs.json")
FROZEN = Path("results/TUNING_FROZEN_posthoc_ranker.json")
OUT = Path("results/posthoc_ranker.json")
LABEL = "descriptive, post hoc, added 2026-11-02 at the referee's request"
PREFIX = "posthoc_ranker"
SEEDS = list(range(61000, 61100))
RHOS = (0.95, 1.15)
DELTAS = (0, 1, 2, 4)
UNIT = "kWh per 100 per event"
R = "R_avoid_kwh_per100"
VIOL = "violation_kwslot"
MISS = "deadline_miss_count_per100"
METRICS = (R, VIOL, MISS, "A_sha256")
RANKERS = ("greedy_ev", "greedy_ev_pop", "greedy_ev_ce")
RERUN = ("ce_llf", "pop_mpc", "guarded_mpc_e1")
FACTORIAL = ("ce_llf", "llf_pop", "llf_post", "mpc_ce", "pop_mpc", "guarded_mpc_e1")
# the 3 x 3 design: rule (llf, greedy, mpc) x belief (ce, pop, e1)
SCHED = {("llf", "ce"): "ce_llf", ("llf", "pop"): "llf_pop", ("llf", "e1"): "llf_post",
         ("greedy", "ce"): "greedy_ev_ce", ("greedy", "pop"): "greedy_ev_pop",
         ("greedy", "e1"): "greedy_ev",
         ("mpc", "ce"): "mpc_ce", ("mpc", "pop"): "pop_mpc", ("mpc", "e1"): "guarded_mpc_e1"}
GIT_SCOPE = ["src", "run_study.py", "scripts/posthoc_ranker.py", "scripts/run_posthoc_ranker.py",
             "results/f0r_posthoc_ranker", "results/TUNING_FROZEN_posthoc_ranker.json",
             "results/TUNING_FROZEN.json", "results/population_params.json"]


def cid(dA: int, rho: float) -> str:
    return Cell(family="F0R", M=3, delta_A=dA, delta_b=0, rho=rho, r=0.3).cell_id


def load(path: Path, policies: tuple) -> dict:
    vals: dict = defaultdict(lambda: defaultdict(dict))
    seen = set()
    with gzip.open(path, "rt") as fh:
        for line in fh:
            r = json.loads(line)
            if r.get("mode") != "frozen" or r.get("kind") == "bound" or r["policy"] not in policies:
                continue
            key = (r["cell_id"], r["policy"], r["seed"])
            if key in seen:
                raise SystemExit(f"duplicate row {key} in {path}")
            seen.add(key)
            if r["study_family"] != "F0R" or r["N"] != 30:
                raise SystemExit(f"unexpected row {key}")
            if not 61000 <= r["seed"] <= 61099:
                raise SystemExit(f"seed outside the development range: {key}")
            for m in METRICS:
                vals[(r["cell_id"], r["policy"])][m][r["seed"]] = r[m]
    return vals


def vec(vals, cell: str, pol: str, metric: str = R) -> np.ndarray:
    try:
        d = vals[(cell, pol)][metric]
        v = np.array([d[s] for s in SEEDS], dtype=float)
    except KeyError:
        raise SystemExit(f"missing rows: {cell} {pol} {metric}") from None
    if not np.isfinite(v).all():
        raise SystemExit(f"non-finite values: {cell} {pol} {metric}")
    return v


def check_rerun(new, old) -> int:
    n = 0
    for rho in RHOS:
        for d in DELTAS:
            c = cid(d, rho)
            for p in RERUN:
                for m in METRICS:
                    a, b = new[(c, p)][m], old[(c, p)][m]
                    if set(a) != set(SEEDS) or any(a[s] != b[s] for s in SEEDS):
                        raise SystemExit(f"rerun differs from f0r_extra: {c} {p} {m}")
                    n += len(SEEDS)
    return n


class Numbers:
    def __init__(self) -> None:
        self.items: dict[str, dict] = {}

    def add(self, key: str, st: Stat, *, cell: str, statistic: str, unit: str = UNIT,
            policies: tuple = (), source: str = str(ROWS), **extra) -> None:
        key = f"{PREFIX}/{key}"
        if key in self.items:
            raise SystemExit(f"duplicate key {key}")
        flt = (f"mode == frozen and cell_id == {cell} and seed in 61000..61099"
               + (f" and policy in {list(policies)}" if policies else ""))
        self.items[key] = {"value": st.value, "ci_lo": st.lo, "ci_hi": st.hi,
                           "n_seeds": len(SEEDS), "label": LABEL, "unit": unit,
                           "statistic": statistic, "cell_id": cell, "source_file": source,
                           "row_filter": flt, **extra}


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


def section(ranker, extra, boot: Bootstrap, nums: Numbers, g3: dict) -> int:
    n_checked = 0
    both = f"{ROWS} (rankers) and {EXTRA_ROWS} (LLF and MPC rows)"
    for rho in RHOS:
        for d in DELTAS:
            c = cid(d, rho)
            base = f"M3_rho{rho:g}/dA{d}"
            v = {s: vec(ranker if s in RANKERS else extra, c, s) for s in SCHED.values()}
            stats = {f"R_{p}": (lambda m, p=p: m[p]) for p in RANKERS}
            stats.update({
                "greedy_ev_minus_ce_llf": lambda m: m["greedy_ev"] - m["ce_llf"],
                "greedy_ev_minus_targeted_mpc": lambda m: m["greedy_ev"] - m["guarded_mpc_e1"],
                "greedy_ev_pop_minus_shared_rate_mpc": lambda m: m["greedy_ev_pop"] - m["pop_mpc"],
                "belief_step_greedy_minus_llf": lambda m: ((m["greedy_ev_pop"] - m["greedy_ev"])
                                                           - (m["llf_pop"] - m["llf_post"])),
                "belief_step_mpc_minus_greedy": lambda m: ((m["pop_mpc"] - m["guarded_mpc_e1"])
                                                           - (m["greedy_ev_pop"] - m["greedy_ev"])),
            })
            for rule in ("greedy", "llf", "mpc"):
                for a, b in (("ce", "pop"), ("pop", "e1")):
                    x, y = SCHED[(rule, a)], SCHED[(rule, b)]
                    stats[f"belief_{a}_to_{b}_in_{rule}"] = (lambda m, x=x, y=y: m[x] - m[y])
            for bel in ("ce", "pop", "e1"):
                for r1, r2 in (("llf", "greedy"), ("greedy", "mpc")):
                    x, y = SCHED[(r1, bel)], SCHED[(r2, bel)]
                    stats[f"rule_{r1}_to_{r2}_given_{bel}"] = (lambda m, x=x, y=y: m[x] - m[y])
            res = boot.run(v, stats)
            for p in RANKERS:
                nums.add(f"{base}/R_avoid_{p}", res[f"R_{p}"], cell=c, policies=(p,),
                         statistic=f"mean {R} of {p}")
            for k, (a, b) in {"greedy_ev_minus_ce_llf": ("greedy_ev", "ce_llf"),
                              "greedy_ev_minus_targeted_mpc": ("greedy_ev", "guarded_mpc_e1"),
                              "greedy_ev_pop_minus_shared_rate_mpc": ("greedy_ev_pop", "pop_mpc")
                              }.items():
                nums.add(f"{base}/{k}", res[k], cell=c, policies=(a, b),
                         source=f"{both}; the {b} rows are identical in both files (checked)",
                         statistic=f"mean paired {R}({a}) - {R}({b}); negative means {a} "
                                   "has the lower R_avoid")
            for rule in ("greedy", "llf", "mpc"):
                for a, b in (("ce", "pop"), ("pop", "e1")):
                    k = f"belief_{a}_to_{b}_in_{rule}"
                    x, y = SCHED[(rule, a)], SCHED[(rule, b)]
                    extra_kw = {}
                    if rule != "greedy":
                        ref = g3[f"posthoc_runs/factorial/{base}/{k}"]
                        st = res[k]
                        if not all(abs(p - q) < 1e-12 for p, q in
                                   ((st.value, ref["value"]), (st.lo, ref["ci_lo"]),
                                    (st.hi, ref["ci_hi"]))):
                            raise SystemExit(f"{k} at {base} differs from {G3}")
                        n_checked += 1
                        extra_kw = {"same_as": f"posthoc_runs/factorial/{base}/{k}"}
                    nums.add(f"{base}/{k}", res[k], cell=c, policies=(x, y),
                             source=str(ROWS) if rule == "greedy" else str(EXTRA_ROWS),
                             statistic=f"mean paired {R}({x}) - {R}({y}); gain convention, "
                                       f"positive means {y} has the lower R_avoid", **extra_kw)
            nums.add(f"{base}/belief_step_greedy_minus_llf", res["belief_step_greedy_minus_llf"],
                     cell=c, policies=("greedy_ev_pop", "greedy_ev", "llf_pop", "llf_post"),
                     source=both,
                     statistic="(R(greedy_ev_pop) - R(greedy_ev)) - (R(llf_pop) - R(llf_post)), "
                               "means jointly resampled; positive means the per-participant "
                               "belief gains more inside the greedy ranker than inside LLF")
            nums.add(f"{base}/belief_step_mpc_minus_greedy", res["belief_step_mpc_minus_greedy"],
                     cell=c, policies=("pop_mpc", "guarded_mpc_e1", "greedy_ev_pop", "greedy_ev"),
                     source=both,
                     statistic="(R(pop_mpc) - R(guarded_mpc_e1)) - (R(greedy_ev_pop) - "
                               "R(greedy_ev)), means jointly resampled; positive means the "
                               "per-participant belief gains more inside MPC than inside the "
                               "greedy ranker")
            for bel in ("ce", "pop", "e1"):
                for r1, r2 in (("llf", "greedy"), ("greedy", "mpc")):
                    x, y = SCHED[(r1, bel)], SCHED[(r2, bel)]
                    k = f"rule_{r1}_to_{r2}_given_{bel}"
                    nums.add(f"{base}/{k}", res[k], cell=c, policies=(x, y), source=both,
                             statistic=f"mean paired {R}({x}) - {R}({y}); gain convention, "
                                       f"positive means {y} has the lower R_avoid")
            w = {"g": vec(ranker, c, "greedy_ev", VIOL), "gp": vec(ranker, c, "greedy_ev_pop", VIOL),
                 "ce": vec(ranker, c, "ce_llf", VIOL),
                 "mg": vec(ranker, c, "greedy_ev", MISS), "mgp": vec(ranker, c, "greedy_ev_pop", MISS)}
            rv = boot.run(w, {"g": lambda m: m["g"], "gp": lambda m: m["gp"],
                              "d": lambda m: m["g"] - m["ce"], "mg": lambda m: m["mg"],
                              "mgp": lambda m: m["mgp"]})
            vu = "kW·slot per event"
            nums.add(f"{base}/violation_kwslot_greedy_ev", rv["g"], cell=c, unit=vu,
                     policies=("greedy_ev",), statistic=f"mean {VIOL} of greedy_ev (per seed, N = 30)")
            nums.add(f"{base}/violation_kwslot_greedy_ev_pop", rv["gp"], cell=c, unit=vu,
                     policies=("greedy_ev_pop",),
                     statistic=f"mean {VIOL} of greedy_ev_pop (per seed, N = 30)")
            nums.add(f"{base}/violation_greedy_ev_minus_ce_llf", rv["d"], cell=c, unit=vu,
                     policies=("greedy_ev", "ce_llf"),
                     statistic=f"mean paired {VIOL}(greedy_ev) - {VIOL}(ce_llf) (per seed, N = 30)")
            nums.add(f"{base}/deadline_miss_count_per100_greedy_ev", rv["mg"], cell=c,
                     unit="misses per 100 per event", policies=("greedy_ev",),
                     statistic=f"mean {MISS} of greedy_ev")
            nums.add(f"{base}/deadline_miss_count_per100_greedy_ev_pop", rv["mgp"], cell=c,
                     unit="misses per 100 per event", policies=("greedy_ev_pop",),
                     statistic=f"mean {MISS} of greedy_ev_pop")
    return n_checked


def main() -> None:
    ranker = load(ROWS, RANKERS + RERUN)
    extra = load(EXTRA_ROWS, FACTORIAL)
    n_rerun = check_rerun(ranker, extra)
    g3 = json.loads(G3.read_text())["numbers"]
    boot = Bootstrap()
    nums = Numbers()
    n_g3 = section(ranker, extra, boot, nums, g3)
    frozen = json.loads(FROZEN.read_text())
    cfg = {f: {cid(d, rho): frozen[f][cid(d, rho)]["config"] for rho in RHOS for d in DELTAS}
           for f in RANKERS}
    meta = {"label": LABEL, "git": git_meta(),
            "input_sha256": {str(p): sha(p) for p in (ROWS, EXTRA_ROWS, G3, FROZEN)}
            | {"results/f0r_posthoc_ranker/manifest.json": sha(ROWS.parent / "manifest.json")},
            "bootstrap": {"n_boot": boot.n_boot, "seed": boot.seed, "level": boot.level,
                          "method": "paired percentile bootstrap over seeds (analysis.Bootstrap)"},
            "seeds": [SEEDS[0], SEEDS[-1]], "n_seeds": len(SEEDS),
            "frozen_configs": cfg,
            "checks": {"rerun_comparators_equal_f0r_extra": n_rerun,
                       "factorial_numbers_equal_posthoc_g3_runs": n_g3},
            "note": "None of these numbers is pre-declared. The ranker is the guarded MPC with a "
                    "one-slot horizon solved greedily (tests/test_ranker.py checks the equality); "
                    "its configurations were tuned on seeds 60000-60049 with the runner's "
                    "selection rule and frozen in results/TUNING_FROZEN_posthoc_ranker.json, "
                    "which was not committed before the development run (allow_dirty in the "
                    "manifest)."}
    OUT.write_text(json.dumps(clean({"meta": meta, "numbers": nums.items}), indent=1))
    print(f"wrote {OUT}: {len(nums.items)} numbers, dirty={meta['git']['dirty']}, "
          f"rerun checks {n_rerun}, factorial checks {n_g3}")
    f = lambda x: "null" if x is None or not math.isfinite(x) else f"{x:.2f}"
    for k, v in nums.items.items():
        print(f"{k}: {v['value']:.2f} [{f(v['ci_lo'])}, {f(v['ci_hi'])}]")


if __name__ == "__main__":
    main()
