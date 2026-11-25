"""Negative controls NC1, NC2, NC3' and NC4 (PLAN_PGAI4E_E Section 6, FORMULATION_E_v2 8.3).

Usage: uv run python scripts/negative_controls.py [--workers 4] [--seeds 60000-60049]
       uv run python scripts/negative_controls.py --nc3-extended [--workers 4]   (seeds 64000-64249)

Seeds: ONLY the tuning block 60000-60049 (SEED_LEDGER). ``check_seeds`` refuses anything
else. Everything reported is a development number.

Controls
--------
* NC1  deterministic availability, delta_A = 0, delta_b = 0, rho = 0.7, M = 3, r = 0.3.
       Every family of ``papere.policies.catalog.FAMILIES`` at its default configuration.
       Pre-declared pass rule (plan, literal): R_avoid = 0 EXACTLY for every family and
       seed. Also reported, with its own verdict: R_avoid_sp = 0 (OPEN_QUESTIONS row 31,
       the bound under the enforced setpoint cap).
* NC2  all 22 F0R_CELLS x seeds x (W, m, gamma) in {(24,0,0), (24,0,1), (8,1,0.5), (2,2,2)}:
       guarded_mpc(CEBelief, W, m, gamma) against mpc_ce(W, m, k = 0), same policy name (so
       the same tie-break stream). Every slot action and every re-dispatch round is compared.
       Pass = zero mismatches.
* NC3' homogeneous q, memoryless availability (homogeneous_iid=True) on the 16 primary
       cells: guarded_mpc_e1 minus pop_mpc, R_avoid_kwh_per100, paired bootstrap 95% CI
       (10,000 resamples, unit = seed). Pass per cell = CI inside [-0.5, +0.5]; overall pass =
       every cell passes.
* NC4  the 8 primary M = 0 cells (normal chain availability, heterogeneous classes): same
       statistic and pass rule. At M = 0 the e1 and population beliefs coincide
       (OPEN_QUESTIONS row 36), so the two policies decide identically up to the tie-break
       stream, which is keyed by policy name; the number of identical seeds is reported
       both with the catalog names (as in the study) and with the names matched.

Outputs: results/negative_controls/nc_results.json and docs/NC_REPORT.md.
"""
from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import multiprocessing as mp
import platform
import subprocess
import sys
import time
from dataclasses import replace
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:          # allow running without an editable install
    sys.path.insert(0, str(ROOT / "src"))

from papere.fit import RESULT_PATH as PARAMS_PATH, load_population_params  # noqa: E402
from papere.generator import F0R_CELLS, generate_f0r  # noqa: E402
from papere.instance import Cell  # noqa: E402
from papere.ledger import BoundViolation, evaluate  # noqa: E402
from papere.policies.catalog import FAMILIES  # noqa: E402
from papere.sim import simulate  # noqa: E402

SEED_LO, SEED_HI = 60000, 60049
OUT_DIR = ROOT / "results" / "negative_controls"
OUT_JSON = OUT_DIR / "nc_results.json"
OUT_MD = ROOT / "docs" / "NC_REPORT.md"
OUT_EXT_JSON = OUT_DIR / "nc3_extended.json"

TOL_KWH_PER100 = 0.5          # practically meaningful effect (plan Section 6)
N_BOOT = 10_000
BOOT_SEED = 20261020          # fixed rng seed of the bootstrap (not a simulation seed)
NC2_NAME = "nc2_shared"       # same name => same tie-break stream for both policies
NC2_CONFIGS = ((24, 0, 0.0), (24, 0, 1.0), (8, 1, 0.5), (2, 2, 2.0))   # (W, m, gamma)

NC1_CELL = Cell(family="F0R", M=3, delta_A=0, delta_b=0, rho=0.7, r=0.3, deterministic=True)
NC2_CELLS: list[Cell] = list(F0R_CELLS)
NC3_CELLS: list[Cell] = [replace(c, homogeneous_iid=True) for c in F0R_CELLS[:16]]
NC4_CELLS: list[Cell] = [c for c in F0R_CELLS[:16] if c.M == 0]
NC1_FAMILY_NAMES: list[str] | None = None      # None = every family (tests may narrow it)

CONTROLS = ("NC1", "NC2", "NC3p", "NC4")


# ---------------------------------------------------------------------------- seeds
EXT_LO, EXT_HI = 64000, 64249     # NC3' extended only (SEED_LEDGER, added 2026-10-20)


def check_seeds(seeds, lo: int = SEED_LO, hi: int = SEED_HI) -> list[int]:
    seeds = [int(s) for s in seeds]
    bad = [s for s in seeds if not lo <= s <= hi]
    if bad:
        raise SystemExit(f"refusing seeds outside {lo}-{hi}: {bad[:5]}")
    if not seeds:
        raise SystemExit("no seeds")
    return seeds


def parse_seeds(spec: str, lo: int = SEED_LO, hi: int = SEED_HI) -> list[int]:
    a, _, b = spec.partition("-")
    a = int(a)
    b = int(b) if b else a
    if b < a:
        raise SystemExit(f"bad seed range {spec!r}")
    return check_seeds(range(a, b + 1), lo, hi)


# ---------------------------------------------------------------------------- stats
def paired_bootstrap(diffs, n_boot: int = N_BOOT, rng_seed: int = BOOT_SEED,
                     level: float = 0.95) -> dict:
    """Percentile paired bootstrap of the mean of per-seed differences (unit = seed)."""
    d = np.asarray(diffs, dtype=np.float64)
    n = d.size
    if n == 0:
        raise ValueError("no differences")
    rng = np.random.default_rng(rng_seed)
    idx = rng.integers(0, n, size=(n_boot, n))
    means = d[idx].mean(axis=1)
    a = (1.0 - level) / 2.0
    lo, hi = np.quantile(means, [a, 1.0 - a])
    return {"mean": float(d.mean()), "lo": float(lo), "hi": float(hi), "n": int(n),
            "n_boot": int(n_boot), "rng_seed": rng_seed}


# ---------------------------------------------------------------------------- compare
def compare_trajectories(ta, tb) -> dict:
    """Count differences between two trajectories' actions.

    Compares the final setpoints of every slot, the number of act() rounds per slot and every
    re-dispatch round (``redispatch_log``: slot, round, setpoints, revealed mask). Returns
    counts; all zero means the two policies acted identically.
    """
    xa, xb = np.asarray(ta.x), np.asarray(tb.x)
    if xa.shape != xb.shape:
        raise ValueError("trajectory shapes differ")
    slot_mismatch = int((xa != xb).any(axis=0).sum())
    entry_mismatch = int((xa != xb).sum())
    round_mismatch = int((np.asarray(ta.rounds) != np.asarray(tb.rounds)).sum())
    la, lb = list(ta.redispatch_log), list(tb.redispatch_log)
    log_mismatch = abs(len(la) - len(lb))
    for ea, eb in zip(la, lb):
        same = (ea[0] == eb[0] and ea[1] == eb[1] and np.array_equal(ea[2], eb[2])
                and np.array_equal(ea[3], eb[3]))
        log_mismatch += 0 if same else 1
    first = None
    bad = np.nonzero((xa != xb).any(axis=0))[0]
    if bad.size:
        first = int(bad[0])
    return {"actions_compared": int(xa.shape[1]) + max(len(la), len(lb)),
            "slot_mismatch": slot_mismatch, "entry_mismatch": entry_mismatch,
            "round_mismatch": round_mismatch, "log_mismatch": int(log_mismatch),
            "mismatches": slot_mismatch + round_mismatch + log_mismatch,
            "first_bad_slot": first}


# ---------------------------------------------------------------------------- worker
_PARAMS = None


def _params():
    global _PARAMS
    if _PARAMS is None:
        _PARAMS = load_population_params()
    return _PARAMS


def _family(name: str):
    for f in FAMILIES:
        if f.name == name:
            return f
    raise KeyError(name)


def _run(inst, cell, policy, seed):
    traj = simulate(inst, cell, policy, seed)
    return traj, evaluate(inst, traj)


def exact_base_instance(inst):
    """NC1-exact diagnostic instance: base load constant at B0 = N (no ramp, no noise), so the
    last-value forecast is exact. Built by post-processing a generated instance (the generator
    is not touched). L is rebuilt with the generator's rule, so rho keeps its meaning:
    L = (sum E / rho + sum b_mean) / H. Availability is unchanged (deterministic)."""
    N, H = inst.N, inst.H
    b = np.full((1, H), float(N))
    L = np.full((1, H), (float(inst.E.sum()) / inst.cell.rho + b.sum()) / H)
    for a in (b, L):
        a.flags.writeable = False
    return dataclasses.replace(inst, b=b, b_mean=b.copy(), L=L)


def run_nc1(seed: int) -> list[dict]:
    cell = NC1_CELL
    inst = generate_f0r(seed, cell)
    inst_x = exact_base_instance(inst)
    rows = []
    fams = FAMILIES if NC1_FAMILY_NAMES is None else [_family(n) for n in NC1_FAMILY_NAMES]
    for fam in fams:
        row = {"control": "NC1", "family": fam.name, "kind": fam.kind, "seed": seed,
               "cell_id": cell.cell_id}
        try:
            _, ev = _run(inst, cell, fam.make(dict(fam.default), _params()), seed)
            row.update(R_avoid_u=ev["R_avoid_u"], R_avoid_sp_u=ev["R_avoid_sp_u"],
                       exceeds_bound=bool(ev["exceeds_bound"]),
                       overshoot_u=ev["bound_overshoot_u"],               # (a)
                       cap_gap_u=ev["R_avoid_sp_u"] - ev["R_avoid_u"],    # R*_sp - R*
                       violation_count=ev["violation_count"],
                       deadline_miss_count=ev["deadline_miss_count"], error=None)
        except BoundViolation as e:          # an impossible state is a failure, not a crash
            row.update(R_avoid_u=None, R_avoid_sp_u=None, exceeds_bound=None, overshoot_u=None,
                       cap_gap_u=None, violation_count=None, deadline_miss_count=None,
                       error=str(e))
        try:                                 # diagnostic: exact forecast, (c)
            _, ex = _run(inst_x, cell, fam.make(dict(fam.default), _params()), seed)
            row.update(exact_R_avoid_u=ex["R_avoid_u"], exact_R_avoid_sp_u=ex["R_avoid_sp_u"],
                       exact_error=None)
        except BoundViolation as e:
            row.update(exact_R_avoid_u=None, exact_R_avoid_sp_u=None, exact_error=str(e))
        rows.append(row)
    return rows


def run_nc2(seed: int) -> list[dict]:
    from papere.policies.beliefs import CEBelief
    from papere.policies.mpc import guarded_mpc, mpc_ce
    rows = []
    for cell in NC2_CELLS:
        inst = generate_f0r(seed, cell)
        for (W, m, gamma) in NC2_CONFIGS:
            pg = guarded_mpc(CEBelief(), W, m, gamma, name=NC2_NAME)
            pc = mpc_ce(W, m, 0, name=NC2_NAME)
            tg = simulate(inst, cell, pg, seed)
            tc = simulate(inst, cell, pc, seed)
            cmp = compare_trajectories(tg, tc)
            rows.append({"control": "NC2", "cell_id": cell.cell_id, "seed": seed,
                         "W": W, "m": m, "gamma": gamma,
                         "redispatch_entries": len(tg.redispatch_log), **cmp})
    return rows


def _pair_rows(control: str, cells, seed: int) -> list[dict]:
    e1f, popf = _family("guarded_mpc_e1"), _family("pop_mpc")
    rows = []
    for cell in cells:
        inst = generate_f0r(seed, cell)
        p1 = e1f.make(dict(e1f.default), _params())
        pp = popf.make(dict(popf.default), _params())
        t1, ev1 = _run(inst, cell, p1, seed)
        tp, evp = _run(inst, cell, pp, seed)
        same_cat = compare_trajectories(t1, tp)["mismatches"] == 0
        row = {"control": control, "cell_id": cell.cell_id, "seed": seed,
               "e1_R_avoid_kwh_per100": ev1["R_avoid_kwh_per100"],
               "pop_R_avoid_kwh_per100": evp["R_avoid_kwh_per100"],
               "e1_R_avoid_u": ev1["R_avoid_u"], "pop_R_avoid_u": evp["R_avoid_u"],
               "diff_kwh_per100": ev1["R_avoid_kwh_per100"] - evp["R_avoid_kwh_per100"],
               "identical_catalog_names": bool(same_cat)}
        if cell.M == 0:
            # M = 0: e1 and population beliefs coincide, so with the tie-break stream matched
            # (pop_mpc renamed to e1's name) the decisions must be identical. Supplementary
            # diagnostic only; the pre-declared pass rule uses the catalog names above.
            pm = popf.make(dict(popf.default), _params())
            pm.name = e1f.name
            tm = simulate(inst, cell, pm, seed)
            row["identical_matched_names"] = compare_trajectories(t1, tm)["mismatches"] == 0
            row["diff_matched_kwh_per100"] = (
                ev1["R_avoid_kwh_per100"] - evaluate(inst, tm)["R_avoid_kwh_per100"])
        rows.append(row)
    return rows


def run_seed(seed: int) -> dict:
    """All controls for one seed (the multiprocessing unit)."""
    t0 = time.time()
    out = {"seed": seed, "NC1": run_nc1(seed), "NC2": run_nc2(seed),
           "NC3p": _pair_rows("NC3p", NC3_CELLS, seed),
           "NC4": _pair_rows("NC4", NC4_CELLS, seed)}
    out["seconds"] = time.time() - t0
    return out


# ---------------------------------------------------------------------------- summaries
def _mean(v):
    return float(np.mean(v)) if len(v) else None


def _max(v):
    return float(np.max(v)) if len(v) else None


def _min(v):
    return float(np.min(v)) if len(v) else None


def summarize_nc1(rows: list[dict], family_order: list[str] | None = None) -> dict:
    """Per-family NC1 statistics and the two verdicts (literal R_avoid, and R_avoid_sp)."""
    order = family_order or list(dict.fromkeys(r["family"] for r in rows))
    fams = {}
    for name in order:
        rs = [r for r in rows if r["family"] == name]
        errs = [r for r in rs if r["error"]]
        ok = [r for r in rs if not r["error"]]
        ra = np.array([r["R_avoid_u"] for r in ok], dtype=float)
        rsp = np.array([r["R_avoid_sp_u"] for r in ok], dtype=float)
        fams[name] = {
            "kind": rs[0]["kind"] if rs else None, "n_seeds": len(rs), "n_errors": len(errs),
            "max_R_avoid_u": float(ra.max()) if ra.size else None,
            "min_R_avoid_u": float(ra.min()) if ra.size else None,
            "mean_R_avoid_u": float(ra.mean()) if ra.size else None,
            "max_R_avoid_sp_u": float(rsp.max()) if rsp.size else None,
            "min_R_avoid_sp_u": float(rsp.min()) if rsp.size else None,
            "mean_R_avoid_sp_u": float(rsp.mean()) if rsp.size else None,
            "n_nonzero_R_avoid": int((ra != 0).sum()) + len(errs),
            "n_nonzero_R_avoid_sp": int((rsp != 0).sum()) + len(errs),
            # decomposition of R_avoid: (a) overshoot, (b) shortfall vs the setpoint-cap bound
            "mean_overshoot_u": _mean([r["overshoot_u"] for r in ok if r.get("overshoot_u") is not None]),
            "max_overshoot_u": _max([r["overshoot_u"] for r in ok if r.get("overshoot_u") is not None]),
            "mean_cap_gap_u": _mean([r["cap_gap_u"] for r in ok if r.get("cap_gap_u") is not None]),
            # (c) diagnostic NC1-exact (constant, noise-free base load)
            "exact_max_R_avoid_u": _max([r["exact_R_avoid_u"] for r in rs
                                         if r.get("exact_R_avoid_u") is not None]),
            "exact_min_R_avoid_u": _min([r["exact_R_avoid_u"] for r in rs
                                         if r.get("exact_R_avoid_u") is not None]),
            "exact_mean_R_avoid_u": _mean([r["exact_R_avoid_u"] for r in rs
                                           if r.get("exact_R_avoid_u") is not None]),
            "exact_max_R_avoid_sp_u": _max([r["exact_R_avoid_sp_u"] for r in rs
                                            if r.get("exact_R_avoid_sp_u") is not None]),
            "exact_n_nonzero_R_avoid": sum(1 for r in rs if r.get("exact_error")
                                           or (r.get("exact_R_avoid_u") not in (None, 0))),
            "exact_n_nonzero_R_avoid_sp": sum(1 for r in rs if r.get("exact_error")
                                              or (r.get("exact_R_avoid_sp_u") not in (None, 0))),
            "n_negative_R_avoid": int((ra < 0).sum()),
            "n_positive_R_avoid": int((ra > 0).sum()),
            "n_exceeds_bound": int(sum(bool(r["exceeds_bound"]) for r in ok)),
            "failing_seeds_R_avoid": sorted(r["seed"] for r in ok if r["R_avoid_u"] != 0)
                                     + sorted(r["seed"] for r in errs),
            "failing_seeds_R_avoid_sp": sorted(r["seed"] for r in ok if r["R_avoid_sp_u"] != 0)
                                        + sorted(r["seed"] for r in errs),
        }
    fail_lit = [n for n, f in fams.items() if f["n_nonzero_R_avoid"] > 0]
    fail_sp = [n for n, f in fams.items() if f["n_nonzero_R_avoid_sp"] > 0]
    fail_x = [n for n, f in fams.items() if f["exact_n_nonzero_R_avoid"] > 0]
    return {"families": fams,
            "verdict_exact_R_avoid_diagnostic": "PASS" if not fail_x else "FAIL",
            "failing_families_exact": fail_x,
            "verdict_literal_R_avoid": "PASS" if not fail_lit else "FAIL",
            "verdict_R_avoid_sp": "PASS" if not fail_sp else "FAIL",
            "failing_families_literal": fail_lit, "failing_families_sp": fail_sp}


def summarize_nc2(rows: list[dict]) -> dict:
    """NC2 counts per (W, m, gamma) config, per cell, and the verdict."""
    by_cfg: dict = {}
    by_cell: dict = {}
    for r in rows:
        key = f"W{r['W']}_m{r['m']:g}_g{r['gamma']:g}"
        c = by_cfg.setdefault(key, {"sims": 0, "actions_compared": 0, "mismatches": 0,
                                    "sims_with_mismatch": 0})
        c["sims"] += 1
        c["actions_compared"] += r["actions_compared"]
        c["mismatches"] += r["mismatches"]
        c["sims_with_mismatch"] += int(r["mismatches"] > 0)
        k2 = by_cell.setdefault(r["cell_id"], {}).setdefault(key, 0)
        by_cell[r["cell_id"]][key] = k2 + int(r["mismatches"] > 0)
    bad = [{k: r[k] for k in ("cell_id", "seed", "W", "m", "gamma", "slot_mismatch",
                              "round_mismatch", "log_mismatch", "first_bad_slot")}
           for r in rows if r["mismatches"] > 0]
    total = sum(c["mismatches"] for c in by_cfg.values())
    return {"configs": by_cfg, "sims_with_mismatch_by_cell": by_cell,
            "total_sims": len(rows),
            "total_actions_compared": sum(c["actions_compared"] for c in by_cfg.values()),
            "total_mismatches": total, "n_failing_sims": len(bad), "failing": bad,
            "verdict": "PASS" if total == 0 else "FAIL"}


def cell_label(lo: float, hi: float, tol: float = TOL_KWH_PER100) -> str:
    """'pass' only if the whole CI lies inside the band; a wider cell is never a pass."""
    if lo >= -tol and hi <= tol:
        return "pass" if (lo <= 0 <= hi) else "pass (difference detected, below the threshold)"
    if lo <= 0 <= hi:
        return f"no difference detected at this size (interval [{lo:+.3f}, {hi:+.3f}])"
    return f"difference detected (interval [{lo:+.3f}, {hi:+.3f}])"


def summarize_pairs(rows: list[dict], cell_order: list[str] | None = None,
                    tol: float = TOL_KWH_PER100, n_boot: int = N_BOOT) -> dict:
    """NC3'/NC4: per-cell paired (e1 - pop) mean and bootstrap CI; pass = CI inside +-tol."""
    order = cell_order or list(dict.fromkeys(r["cell_id"] for r in rows))
    cells = {}
    for ci, cid in enumerate(order):
        rs = sorted((r for r in rows if r["cell_id"] == cid), key=lambda r: r["seed"])
        d = np.array([r["diff_kwh_per100"] for r in rs])
        bs = paired_bootstrap(d, n_boot=n_boot, rng_seed=BOOT_SEED + ci)
        cells[cid] = {
            "n_seeds": len(rs), "mean_diff": bs["mean"], "ci_lo": bs["lo"], "ci_hi": bs["hi"],
            "mean_e1": float(np.mean([r["e1_R_avoid_kwh_per100"] for r in rs])),
            "mean_pop": float(np.mean([r["pop_R_avoid_kwh_per100"] for r in rs])),
            "max_abs_seed_diff": float(np.abs(d).max()),
            "n_identical_catalog_names": int(sum(r["identical_catalog_names"] for r in rs)),
            "n_identical_matched_names": (int(sum(r["identical_matched_names"] for r in rs))
                                          if rs and "identical_matched_names" in rs[0] else None),
            "pass": bool(bs["lo"] >= -tol and bs["hi"] <= tol),
            "label": cell_label(bs["lo"], bs["hi"], tol),
            "detected_nonzero": bool(bs["lo"] > 0 or bs["hi"] < 0),
            "candidate_gain_detected": bool(bs["hi"] < 0),   # e1 - pop < 0: e1 leaves less unserved
            "candidate_loss_detected": bool(bs["lo"] > 0),
            "boot_rng_seed": bs["rng_seed"]}
        if rs and "diff_matched_kwh_per100" in rs[0]:       # supplementary, names matched
            bm = paired_bootstrap([r["diff_matched_kwh_per100"] for r in rs], n_boot=n_boot,
                                  rng_seed=BOOT_SEED + ci)
            cells[cid].update(matched_mean_diff=bm["mean"], matched_ci_lo=bm["lo"],
                              matched_ci_hi=bm["hi"],
                              matched_pass=bool(bm["lo"] >= -tol and bm["hi"] <= tol))
    fail = [c for c, v in cells.items() if not v["pass"]]
    return {"cells": cells, "tolerance_kwh_per100": tol, "n_boot": n_boot,
            "failing_cells": fail, "verdict": "PASS" if not fail else "FAIL"}


# ---------------------------------------------------------------------------- provenance
def _git() -> dict:
    def run(*a):
        return subprocess.run(["git", "-C", str(ROOT), *a], capture_output=True, text=True,
                              timeout=60)
    try:
        head = run("rev-parse", "HEAD").stdout.strip()
        dirty = run("status", "--porcelain", "--untracked-files=all", "--", "src", "scripts",
                    "tests", "results/population_params.json").stdout.strip()
        return {"commit": head or None, "dirty_paths": dirty.splitlines(),
                "working_tree_dirty": bool(dirty)}
    except (OSError, subprocess.SubprocessError):
        return {"commit": None, "dirty_paths": None, "working_tree_dirty": None}


def _versions() -> dict:
    import networkx
    import scipy
    return {"python": platform.python_version(), "numpy": np.__version__,
            "scipy": scipy.__version__, "networkx": networkx.__version__}


def _params_sha() -> str:
    return hashlib.sha256(Path(PARAMS_PATH).read_bytes()).hexdigest()


# ---------------------------------------------------------------------------- driver
def collect(results: list[dict]) -> dict:
    results = sorted(results, key=lambda r: r["seed"])
    return {c: [row for r in results for row in r[c]] for c in CONTROLS}


def build_summaries(rows: dict) -> dict:
    fam_order = [f.name for f in FAMILIES
                 if NC1_FAMILY_NAMES is None or f.name in NC1_FAMILY_NAMES]
    s = {"NC1": summarize_nc1(rows["NC1"], fam_order),
         "NC2": summarize_nc2(rows["NC2"]),
         "NC3p": summarize_pairs(rows["NC3p"], [c.cell_id for c in NC3_CELLS]),
         "NC4": summarize_pairs(rows["NC4"], [c.cell_id for c in NC4_CELLS])}
    s["verdicts"] = {"NC1_literal_R_avoid": s["NC1"]["verdict_literal_R_avoid"],
                     "NC1_R_avoid_sp": s["NC1"]["verdict_R_avoid_sp"],
                     "NC1_exact_R_avoid_diagnostic": s["NC1"]["verdict_exact_R_avoid_diagnostic"],
                     "NC2": s["NC2"]["verdict"], "NC3p": s["NC3p"]["verdict"],
                     "NC4": s["NC4"]["verdict"]}
    return s


def _map(fn, seeds, workers):
    if workers <= 1:
        return [fn(s) for s in seeds]
    ctx = mp.get_context("fork")              # workers inherit module state (and test patches)
    with ctx.Pool(workers) as pool:
        return list(pool.imap_unordered(fn, seeds))


EXT_RULE = ("Pre-declared (OPEN_QUESTIONS 58): the same 16 NC3' cells, statistic and rule as "
            "NC3'. Statistic: mean paired (guarded_mpc_e1 - pop_mpc) R_avoid_kwh_per100, "
            "paired bootstrap, 10,000 resamples, 95%, unit = seed. A cell passes only if its "
            "whole interval lies inside [-0.5, +0.5]. A cell with a wider interval is never "
            "reported as a pass: it is 'no difference detected at this size' with its "
            "interval if the interval includes 0, and 'difference detected' if it excludes 0. "
            "Overall pass = every cell passes. The names-matched column (M = 0) is "
            "supplementary.")


def run_ext_seed(seed: int) -> list[dict]:
    return _pair_rows("NC3p", NC3_CELLS, seed)


def run_extended(seeds: list[int], workers: int, lo: int = EXT_LO, hi: int = EXT_HI) -> dict:
    seeds = check_seeds(seeds, lo, hi)
    t0 = time.time()
    chunks = _map(run_ext_seed, seeds, workers)
    runtime = time.time() - t0
    rows = [r for ch in sorted(chunks, key=lambda c: c[0]["seed"]) for r in ch]
    summ = summarize_pairs(rows, [c.cell_id for c in NC3_CELLS])
    return {"label": "development", "mode": "nc3_extended",
            "seeds": {"first": min(seeds), "last": max(seeds), "count": len(seeds),
                      "list": sorted(seeds)},
            "git": _git(), "package_versions": _versions(),
            "population_params_sha256": _params_sha(),
            "population_params_path": str(Path(PARAMS_PATH).relative_to(ROOT)),
            "runtime_seconds": runtime, "workers": workers,
            "finished_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "spec": {"pass_rule": EXT_RULE, "cells": [c.cell_id for c in NC3_CELLS],
                     "tolerance_kwh_per100": TOL_KWH_PER100, "n_boot": N_BOOT,
                     "boot_seed": BOOT_SEED},
            "rows": rows, "summary": summ}


def run_all(seeds: list[int], workers: int) -> dict:
    seeds = check_seeds(seeds)
    t0 = time.time()
    results = _map(run_seed, seeds, workers)
    runtime = time.time() - t0
    rows = collect(results)
    summ = build_summaries(rows)
    return {
        "label": "development", "seeds": {"first": min(seeds), "last": max(seeds),
                                          "count": len(seeds), "list": sorted(seeds)},
        "git": _git(), "package_versions": _versions(),
        "population_params_sha256": _params_sha(),
        "population_params_path": str(Path(PARAMS_PATH).relative_to(ROOT)),
        "runtime_seconds": runtime, "workers": workers,
        "finished_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "spec": {
            "pass_rules": PASS_RULES,
            "nc1_cell": NC1_CELL.cell_id, "nc2_cells": [c.cell_id for c in NC2_CELLS],
            "nc2_configs": [list(c) for c in NC2_CONFIGS],
            "nc3_cells": [c.cell_id for c in NC3_CELLS],
            "nc4_cells": [c.cell_id for c in NC4_CELLS],
            "tolerance_kwh_per100": TOL_KWH_PER100, "n_boot": N_BOOT, "boot_seed": BOOT_SEED},
        "rows": rows, "summaries": summ}


# ---------------------------------------------------------------------------- report
PASS_RULES = {
    "NC1_literal": "R_avoid = 0 exactly (unit energy) for every family in FAMILIES (default "
                   "configuration) and every seed, on the deterministic cell (plan Section 6).",
    "NC1_sp": "R_avoid_sp = 0 exactly for every family and seed (OPEN_QUESTIONS row 31: bound "
              "under the enforced setpoint cap). Reported as a second verdict, not a replacement.",
    "NC2": "Zero mismatches between guarded_mpc(CEBelief, W, m, gamma) and mpc_ce(W, m, k=0), "
           "same policy name, over every slot action and every re-dispatch round.",
    "NC3p": "Paired bootstrap 95% CI (10,000 resamples, unit = seed) of the mean "
            "(e1 - pop) R_avoid_kwh_per100 inside [-0.5, +0.5] in every one of 16 cells.",
    "NC4": "Same statistic and rule as NC3' on the 8 primary M = 0 cells.",
}


def _f(x, nd=3):
    return "n/a" if x is None else f"{x:.{nd}f}"


PLANNING = ("mpc_ce", "mpc_pes", "pop_mpc", "guarded_mpc_e1", "oracle_mpc")


def _rulings_section(res: dict) -> list[str]:
    S = res["summaries"]
    n1, n3 = S["NC1"], S["NC3p"]
    V = S["verdicts"]
    fams = n1["families"]
    L = ["## Owner-side rulings (ruled by the owner side on 2026-10-20)", "",
         "OPEN_QUESTIONS rows 57 and 58. The pre-declared verdicts are not relabelled.", "",
         f"- **NC1 and NC1_sp stay FAIL** (literal: {V['NC1_literal_R_avoid']}; R_avoid_sp: "
         f"{V['NC1_R_avoid_sp']}). Reason: the plan's NC1 left base-load noise in, so "
         "forecast-capped policies can neither match nor be held to the realized-headroom "
         "bound exactly; a specification error on the owner side."]
    have = [p for p in PLANNING if p in fams and "exact_n_nonzero_R_avoid" in fams[p]]
    if len(have) == len([p for p in PLANNING if p in fams]) and have:
        bad = [p for p in have if fams[p]["exact_n_nonzero_R_avoid"] > 0]
        verdict = "PASS" if not bad else "FAIL"
        cnt = ", ".join(f"{p} {fams[p]['exact_n_nonzero_R_avoid']}" for p in have)
        L += [f"- **NC1-exact (constant, noise-free base load) is the code check for the planning "
              f"policies** ({', '.join(PLANNING)}). Verdict: **{verdict}** (PASS iff R_avoid = 0 "
              f"on every seed for all five). Seeds with R_avoid != 0 out of "
              f"{seeds_n(res)}: {cnt}."]
        greedy = [(n, f) for n, f in fams.items() if n not in PLANNING
                  and f.get("exact_n_nonzero_R_avoid", 0) > 0]
        if greedy:
            L += ["- The greedy rules' NC1-exact shortfall is reported as a finding consistent "
                  "with LLF failing feasible instances under a shared limit (Chen et al., "
                  "sLLF), not as a defect: "
                  + "; ".join(f"{n} (R_avoid != 0 on {f['exact_n_nonzero_R_avoid']} seeds, max "
                              f"{f['exact_max_R_avoid_u']:.0f} units)" for n, f in greedy) + "."]
        else:
            L += ["- No greedy rule shows an NC1-exact shortfall in this run."]
    else:
        L += ["- NC1-exact results are not present in this results file (it predates the "
              "diagnostic); rerun the script to compute the planning-policy check."]
    gain = [c for c, v in n3["cells"].items() if v.get("candidate_gain_detected")]
    loss = [c for c, v in n3["cells"].items() if v.get("candidate_loss_detected")]
    L += [f"- **NC3' ({res['seeds']['count']}-seed) verdict stays {V['NC3p']}** on interval "
          "width. " + ("No cell shows a candidate gain whose interval excludes zero."
                       if not gain else
                       f"CORRECTION: {len(gain)} cell(s) show a candidate gain whose interval "
                       f"excludes zero: {', '.join(gain)}.")
          + (f" Cells where the interval excludes zero in the other direction (e1 leaves more "
             f"unserved than pop): {', '.join(loss)}." if loss else
             " No cell has an interval excluding zero in either direction.")]
    L += ["- A larger NC3' (250 seeds, 64000-64249) is pre-declared; see its section below if "
          "it has been run.", ""]
    return L


def seeds_n(res: dict) -> str:
    return f"{res['seeds']['count']} seeds"


def _ext_section(ext: dict) -> list[str]:
    sm, sp = ext["summary"], ext["spec"]
    sd = ext["seeds"]
    L = ["## NC3' extended (seeds 64000-64249)", "", "**Pre-declared rule.** " + sp["pass_rule"], "",
         f"Development results, seeds {sd['first']}-{sd['last']} ({sd['count']} seeds). "
         "Same 16 cells as NC3'. Values are R_avoid in kWh per 100 participants per event.", "",
         "| cell | mean e1 | mean pop | mean diff (e1 - pop) | 95% CI | label |", "|---|---|---|---|---|---|"]
    for cid in sp["cells"]:
        c = sm["cells"][cid]
        L += [f"| {cid} | {c['mean_e1']:.3f} | {c['mean_pop']:.3f} | {c['mean_diff']:+.3f} "
              f"| [{c['ci_lo']:+.3f}, {c['ci_hi']:+.3f}] | {c['label']} |"]
    npass = sum(c["pass"] for c in sm["cells"].values())
    L += ["", f"Overall: **{sm['verdict']}** ({npass} of {len(sp['cells'])} cells pass).", ""]
    m0 = [cid for cid in sp["cells"] if sm["cells"][cid]["n_identical_matched_names"] is not None]
    if m0:
        L += ["Supplementary, M = 0 cells: trajectories identical between e1 and pop.", "",
              "| cell | identical (catalog names) | identical (names matched) | CI (names matched) |",
              "|---|---|---|---|"]
        same = True
        for cid in m0:
            c = sm["cells"][cid]
            same &= c["n_identical_catalog_names"] == c["n_identical_matched_names"]
            L += [f"| {cid} | {c['n_identical_catalog_names']}/{c['n_seeds']} "
                  f"| {c['n_identical_matched_names']}/{c['n_seeds']} "
                  f"| [{c['matched_ci_lo']:+.3f}, {c['matched_ci_hi']:+.3f}] |"]
        L += ["", ("The simulator now shares one tie-break stream across policies, so the "
                   "names-matched column is redundant: both columns are identical in every "
                   "M = 0 cell." if same else
                   "The two columns differ in at least one M = 0 cell, so the names-matched "
                   "column still carries information."), ""]
    g = ext["git"]
    L += ["Provenance: git commit " f"`{g['commit']}`, working tree dirty: {g.get('working_tree_dirty')}, "
          f"population params sha256 `{ext['population_params_sha256']}`, seeds "
          f"{sd['first']}-{sd['last']}, runtime {ext['runtime_seconds']:.0f} s, "
          f"finished {ext['finished_utc']}.", ""]
    return L


def render_report(res: dict, ext: dict | None = None) -> str:
    S, V = res["summaries"], res["summaries"]["verdicts"]
    n1, n2, n3, n4 = S["NC1"], S["NC2"], S["NC3p"], S["NC4"]
    seeds = res["seeds"]
    L: list[str] = []
    L += ["# Negative controls report (NC1, NC2, NC3', NC4)", "",
          "All numbers below are DEVELOPMENT results on tuning seeds "
          f"{seeds['first']}-{seeds['last']} ({seeds['count']} seeds). "
          "Generated by `scripts/negative_controls.py` from "
          "`results/negative_controls/nc_results.json`; do not edit by hand.", ""]
    fails = [k for k, v in V.items() if v == "FAIL" and "diagnostic" not in k]
    L += ["## Verdicts", ""]
    if fails:
        L += [f"**FAILURES: {', '.join(fails)}.** Details are in the sections below; "
              "no policy code was changed.", ""]
    else:
        L += ["No control failed.", ""]
    L += ["| Control | Pass rule | Verdict |", "|---|---|---|",
          f"| NC1 (literal) | R_avoid = 0 exactly, every family and seed | **{V['NC1_literal_R_avoid']}** |",
          f"| NC1 (R_avoid_sp) | R_avoid_sp = 0 exactly, every family and seed | **{V['NC1_R_avoid_sp']}** |",
          f"| NC1-exact (diagnostic) | R_avoid = 0 exactly with constant noise-free base load "
          f"(forecast exact); not a pre-declared rule | {V['NC1_exact_R_avoid_diagnostic']} |",
          f"| NC2 | zero action mismatches, guarded(CE) vs MPC-CE | **{V['NC2']}** |",
          f"| NC3' | all 16 CIs inside +-{TOL_KWH_PER100} kWh/100 | **{V['NC3p']}** |",
          f"| NC4 | all 8 CIs inside +-{TOL_KWH_PER100} kWh/100 | **{V['NC4']}** |", ""]

    L += _rulings_section(res)

    # ---- failure detail first
    if fails:
        L += ["## Failures in detail", ""]
        if V["NC1_literal_R_avoid"] == "FAIL":
            L += [f"- NC1 literal: families with R_avoid != 0 on some seed: "
                  f"{', '.join(n1['failing_families_literal'])}."]
        if V["NC1_R_avoid_sp"] == "FAIL":
            L += [f"- NC1 R_avoid_sp: families with R_avoid_sp != 0 on some seed: "
                  f"{', '.join(n1['failing_families_sp'])}."]
        if V["NC2"] == "FAIL":
            by = {}
            for b in n2["failing"]:
                by.setdefault((b["W"], b["m"], b["gamma"]), []).append(b)
            for (W, m, g), bs in sorted(by.items()):
                cells = sorted({b["cell_id"] for b in bs})
                sds = sorted({b["seed"] for b in bs})
                L += [f"- NC2 config (W={W}, m={m:g}, gamma={g:g}): {len(bs)} of "
                      f"{n2['configs'][f'W{W}_m{m:g}_g{g:g}']['sims']} runs mismatch; "
                      f"cells: {', '.join(cells[:8])}{' ...' if len(cells) > 8 else ''}; "
                      f"seeds: {sds[:12]}{' ...' if len(sds) > 12 else ''}."]
        for tag, nn in (("NC3'", n3), ("NC4", n4)):
            if nn["verdict"] == "FAIL":
                L += [f"- {tag}: failing cells: {', '.join(nn['failing_cells'])}."]
        L += [""]

    L += ["## Pre-declared pass rules", ""]
    for k, v in PASS_RULES.items():
        L += [f"- **{k}**: {v}"]
    L += ["", "Practically meaningful effect: 0.5 kWh per 100 participants per event. "
          "Bootstrap: percentile, 10,000 resamples, 95%, unit = seed, fixed rng seed "
          f"{res['spec']['boot_seed']} (+ cell index).", ""]

    # ---- NC1
    L += ["## NC1: deterministic availability", "",
          f"Cell `{res['spec']['nc1_cell']}`; every family at its default configuration; "
          f"{seeds['count']} seeds. Values are in energy units (1 unit = 0.25 kWh), raw "
          "(R_avoid may be negative, OPEN_QUESTIONS 31). `n!=0` counts seeds with a value "
          "different from zero (either sign).", "",
          "| Family | kind | max R_avoid | min R_avoid | mean R_avoid | max R_avoid_sp | mean R_avoid_sp "
          "| n!=0 R_avoid | n>0 R_avoid | n!=0 R_avoid_sp | exceeds_bound |",
          "|---|---|---|---|---|---|---|---|---|---|---|"]
    for name, f in n1["families"].items():
        L += [f"| {name} | {f['kind']} | {_f(f['max_R_avoid_u'], 1)} | {_f(f['min_R_avoid_u'], 1)} "
              f"| {_f(f['mean_R_avoid_u'], 2)} | {_f(f['max_R_avoid_sp_u'], 1)} "
              f"| {_f(f['mean_R_avoid_sp_u'], 2)} | {f['n_nonzero_R_avoid']} "
              f"| {f['n_positive_R_avoid']} | {f['n_nonzero_R_avoid_sp']} "
              f"| {f['n_exceeds_bound']} |"]
    L += ["", f"Literal verdict (R_avoid = 0 for all families and seeds): "
          f"**{V['NC1_literal_R_avoid']}**"
          + (f" (failing: {', '.join(n1['failing_families_literal'])})."
             if n1['failing_families_literal'] else "."),
          f"R_avoid_sp verdict: **{V['NC1_R_avoid_sp']}**"
          + (f" (failing: {', '.join(n1['failing_families_sp'])})."
             if n1['failing_families_sp'] else "."), ""]
    L += ["### NC1 decomposition and NC1-exact (diagnostic, not pre-declared)", "",
          "R_avoid = (b) R_avoid_sp - cap gap, where the cap gap = R*_sp - R* arises because "
          "policies are capped by the forecast headroom floor(L - last base load) while the "
          "primary bound uses the realized headroom. (a) overshoot = max(0, -R_avoid) "
          "(`exceeds_bound`); (b) shortfall against the setpoint-cap bound = R_avoid_sp >= 0; "
          "(c) the same two quantities on NC1-exact, the same instance with base load constant "
          "at B0 = N, no ramp and no noise (L rebuilt for rho = 0.7), where the last-value "
          "forecast is exact and R_avoid = R_avoid_sp. Per-seed values are in the JSON "
          "(`overshoot_u`, `cap_gap_u`, `exact_R_avoid_u`, `exact_R_avoid_sp_u`).", "",
          "| Family | (a) mean overshoot | (a) max overshoot | mean cap gap | (b) mean R_avoid_sp "
          "| (b) max R_avoid_sp | (c) exact: max R_avoid | (c) exact: min R_avoid "
          "| (c) exact: n!=0 R_avoid | (c) exact: n!=0 R_avoid_sp |",
          "|---|---|---|---|---|---|---|---|---|---|"]
    for name, f in n1["families"].items():
        L += [f"| {name} | {_f(f.get('mean_overshoot_u'), 2)} | {_f(f.get('max_overshoot_u'), 1)} "
              f"| {_f(f.get('mean_cap_gap_u'), 2)} | {_f(f['mean_R_avoid_sp_u'], 2)} "
              f"| {_f(f['max_R_avoid_sp_u'], 1)} | {_f(f.get('exact_max_R_avoid_u'), 1)} "
              f"| {_f(f.get('exact_min_R_avoid_u'), 1)} | {f.get('exact_n_nonzero_R_avoid', 'n/a')} "
              f"| {f.get('exact_n_nonzero_R_avoid_sp', 'n/a')} |"]
    L += ["", f"NC1-exact R_avoid verdict (DIAGNOSTIC): **{V['NC1_exact_R_avoid_diagnostic']}**"
          + (f" (failing: {', '.join(n1['failing_families_exact'])})."
             if n1.get("failing_families_exact") else "."), ""]
    errs = [(n, f["n_errors"]) for n, f in n1["families"].items() if f["n_errors"]]
    if errs:
        L += [f"Ledger errors (counted as failures): {errs}", ""]

    # ---- NC2
    L += ["## NC2: guarded MPC with CE posterior vs MPC-CE", "",
          f"22 cells x {seeds['count']} seeds x 4 configs; both policies carry the same name "
          f"(`{NC2_NAME}`), hence the same tie-break stream. Compared: the setpoint vector of every slot, the number of "
          "act() rounds per slot and every re-dispatch round of the audit log.", "",
          "| (W, m, gamma) | runs | actions compared | mismatches | runs with a mismatch |",
          "|---|---|---|---|---|"]
    for key, c in n2["configs"].items():
        L += [f"| {key} | {c['sims']} | {c['actions_compared']} | {c['mismatches']} "
              f"| {c['sims_with_mismatch']} |"]
    L += ["", f"Total: {n2['total_sims']} runs, {n2['total_actions_compared']} actions "
          f"compared, **{n2['total_mismatches']} mismatches**. Verdict **{V['NC2']}**.", ""]
    if n2["n_failing_sims"]:
        L += ["Runs with mismatches by cell (count of seeds):", "",
              "| cell | " + " | ".join(n2["configs"]) + " |",
              "|---|" + "---|" * len(n2["configs"])]
        for cid, d in n2["sims_with_mismatch_by_cell"].items():
            L += [f"| {cid} | " + " | ".join(str(d.get(k, 0)) for k in n2["configs"]) + " |"]
        L += [""]

    # ---- NC3' / NC4
    def pair_table(nn, spec_cells):
        extra = any(nn["cells"][c]["n_identical_matched_names"] is not None
                    for c in spec_cells)
        t = ["| cell | mean e1 | mean pop | mean diff (e1 - pop) | 95% CI | max abs seed diff "
             + ("| identical (catalog names) | identical (names matched) | CI (names matched) "
                if extra else "")
             + "| pass |", "|---|---|---|---|---|---|" + ("---|---|---|" if extra else "") + "---|"]
        for cid in spec_cells:
            c = nn["cells"][cid]
            row = (f"| {cid} | {c['mean_e1']:.3f} | {c['mean_pop']:.3f} | {c['mean_diff']:+.3f} "
                   f"| [{c['ci_lo']:+.3f}, {c['ci_hi']:+.3f}] | {c['max_abs_seed_diff']:.3f} ")
            if extra:
                if c["n_identical_matched_names"] is None:
                    row += "| n/a | n/a | n/a "
                else:
                    row += (f"| {c['n_identical_catalog_names']}/{c['n_seeds']} "
                            f"| {c['n_identical_matched_names']}/{c['n_seeds']} "
                            f"| [{c['matched_ci_lo']:+.3f}, {c['matched_ci_hi']:+.3f}] ")
            t += [row + f"| {'yes' if c['pass'] else 'NO'} |"]
        return t

    L += ["## NC3': homogeneous q, memoryless availability", "",
          "`homogeneous_iid=True` on the 16 primary cells (M in {0,3} x delta_A in {0,1,2,4} x "
          "rho in {0.95,1.15}, r = 0.3, delta_b = 0). guarded_mpc_e1 vs pop_mpc, default "
          "configurations. Values are R_avoid in kWh per 100 participants per event. At M = 0 "
          "the supplementary names-matched columns apply as in NC4.", ""]
    L += pair_table(n3, res["spec"]["nc3_cells"])
    L += ["", f"Verdict **{V['NC3p']}** ({len(n3['failing_cells'])} failing cells).", ""]
    L += ["## NC4: M = 0, heterogeneous classes", "",
          "The 8 primary M = 0 cells with normal chain availability. At M = 0 the e1 and the "
          "population belief coincide by construction (OPEN_QUESTIONS 36), so the two "
          "policies decide identically when they share the tie-break stream. The catalog "
          "names differ (`guarded_mpc_e1`, `pop_mpc`), which changes the stream; the "
          "'names matched' column reruns pop_mpc under e1's name to isolate the decision "
          "identity. The matched-name columns are supplementary; the verdict uses the catalog "
          "names, as pre-declared. Seed-level differences under the catalog names come from "
          "the tie-break stream alone.", ""]
    L += pair_table(n4, res["spec"]["nc4_cells"])
    L += ["", f"Verdict **{V['NC4']}** ({len(n4['failing_cells'])} failing cells).", ""]

    if ext is not None:
        L += _ext_section(ext)

    # ---- provenance
    g = res["git"]
    L += ["## Provenance", "",
          f"- git commit: `{g['commit']}`; modified or untracked paths under src, scripts, "
          f"tests, params: {len(g['dirty_paths'] or [])}",
          f"- population params: `{res['population_params_path']}` sha256 "
          f"`{res['population_params_sha256']}`",
          f"- versions: {res['package_versions']}",
          f"- seeds: {seeds['first']}-{seeds['last']} ({seeds['count']}); workers "
          f"{res['workers']}; runtime {res['runtime_seconds']:.0f} s; finished {res['finished_utc']}",
          "- label: development", ""]
    return "\n".join(L)


# ---------------------------------------------------------------------------- main
def write_outputs(res: dict, out_json: Path = OUT_JSON, out_md: Path = OUT_MD,
                  ext: dict | None = None) -> None:
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(res, indent=1) + "\n")
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(render_report(res, ext))


def _load_ext():
    return json.loads(OUT_EXT_JSON.read_text()) if OUT_EXT_JSON.exists() else None


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--seeds", default=None,
                    help=f"default {SEED_LO}-{SEED_HI}; with --nc3-extended {EXT_LO}-{EXT_HI}")
    ap.add_argument("--render-only", action="store_true",
                    help="re-render docs/NC_REPORT.md from the existing JSON files")
    ap.add_argument("--nc3-extended", action="store_true",
                    help=f"run ONLY the 16 NC3' cells on seeds {EXT_LO}-{EXT_HI}")
    a = ap.parse_args(argv)
    if a.render_only:
        OUT_MD.write_text(render_report(json.loads(OUT_JSON.read_text()), _load_ext()))
        print(f"re-rendered {OUT_MD}")
        return 0
    if a.nc3_extended:
        seeds = parse_seeds(a.seeds or f"{EXT_LO}-{EXT_HI}", EXT_LO, EXT_HI)
        ext = run_extended(seeds, a.workers)
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        OUT_EXT_JSON.write_text(json.dumps(ext, indent=1) + "\n")
        if OUT_JSON.exists():
            OUT_MD.write_text(render_report(json.loads(OUT_JSON.read_text()), ext))
        print(json.dumps({"NC3p_extended": ext["summary"]["verdict"]}, indent=1))
        print(f"runtime {ext['runtime_seconds']:.0f} s; wrote {OUT_EXT_JSON} and {OUT_MD}")
        return 0
    seeds = parse_seeds(a.seeds or f"{SEED_LO}-{SEED_HI}")
    res = run_all(seeds, a.workers)
    write_outputs(res, ext=_load_ext())
    print(json.dumps(res["summaries"]["verdicts"], indent=1))
    print(f"runtime {res['runtime_seconds']:.0f} s; wrote {OUT_JSON} and {OUT_MD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
