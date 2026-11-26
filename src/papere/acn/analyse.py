"""ACN T2 analysis: H1 share, secondary contrast, T2-emp and real-limit variant.

Implements protocol section 3 analysis from saved ``rows.jsonl`` files:
- Metric: ``R_avoid_kwh_per100`` (release v1.0 convention, matching ``papere.analysis``
  and ``scripts/confirm_analysis.py``); also reports raw ``R_avoid_kwh`` as a diagnostic.
- Primary (H1): ``share = (mean(ce_llf) - mean(pop_mpc)) / (mean(ce_llf) - mean(guarded_mpc_e1))``
  at ``M = 3, delta = 2, rho = 0.95`` (``F0R_M3_dA2_db0_rho0.95_r0.3``), 95% paired
  bootstrap interval over seeds (10,000 resamples, generator seed 711000). H1 supported
  when ``ci_lo > 0.5``.
- Secondary contrast: ``share(delta = 1) - share(delta = 4)`` at ``M = 3, rho = 1.15``,
  jointly resampled with the same bootstrap (no threshold).
- T2-emp: same statistics on T2-emp rows (descriptive, not a hypothesis test).
- Real-limit variant: reported if at least 50 instances are feasible.
"""
from __future__ import annotations

from collections import defaultdict
import gzip
import json
import math
from pathlib import Path
from typing import Mapping, Sequence

import numpy as np

from papere.analysis import Bootstrap, safe_ratio

T2_BOOT_SEED = 711_000
T2_N_BOOT = 10_000
T2_LEVEL = 0.95
H1_THRESHOLD = 0.5
REAL_LIMIT_MIN_FEASIBLE = 50

H1_CELL_ID = "F0R_M3_dA2_db0_rho0.95_r0.3"
SEC_CELL_D1 = "F0R_M3_dA1_db0_rho1.15_r0.3"
SEC_CELL_D4 = "F0R_M3_dA4_db0_rho1.15_r0.3"

PRIMARY_METRIC = "R_avoid_kwh_per100"
DIAGNOSTIC_METRIC = "R_avoid_kwh"
REQUIRED_POLICIES: tuple[str, ...] = ("ce_llf", "pop_mpc", "guarded_mpc_e1")


def load_rows_file(path: Path | str) -> list[dict]:
    """Read complete JSONL rows from ``path`` (plain or ``.gz``)."""
    p = Path(path)
    opener = gzip.open if p.suffix == ".gz" else open
    rows: list[dict] = []
    with opener(p, "rt", encoding="utf-8") as fh:
        for line in fh:
            if not line.endswith("\n"):
                break
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def _index_rows(
    rows: Sequence[dict],
) -> tuple[
    dict[tuple[str, str], dict[int, dict]],
    list[str],
]:
    """Group frozen policy rows by ``(cell_id, policy) -> {seed: row}``."""
    by_cp: dict[tuple[str, str], dict[int, dict]] = defaultdict(dict)
    cells: set[str] = set()
    for r in rows:
        if r.get("mode", "frozen") != "frozen":
            continue
        pol = r.get("policy")
        if pol not in REQUIRED_POLICIES:
            continue
        cid = str(r["cell_id"])
        seed = int(r["seed"])
        by_cp[(cid, pol)][seed] = r
        cells.add(cid)
    return by_cp, sorted(cells)


def _common_seeds(
    by_cp: Mapping[tuple[str, str], Mapping[int, dict]],
    cell_ids: Sequence[str],
    allowed_seeds: set[int] | None = None,
) -> list[int]:
    sets: list[set[int]] = []
    for cid in cell_ids:
        for pol in REQUIRED_POLICIES:
            s = set(by_cp.get((cid, pol), {}).keys())
            if allowed_seeds is not None:
                s &= allowed_seeds
            sets.append(s)
    if not sets:
        return []
    return sorted(set.intersection(*sets))


def _cell_share(
    by_cp: Mapping[tuple[str, str], Mapping[int, dict]],
    cell_id: str,
    boot: Bootstrap,
    *,
    metric: str = PRIMARY_METRIC,
    allowed_seeds: set[int] | None = None,
) -> dict | None:
    seeds = _common_seeds(by_cp, [cell_id], allowed_seeds=allowed_seeds)
    if not seeds:
        return None
    v = {
        pol: np.array([float(by_cp[(cell_id, pol)][s][metric]) for s in seeds], dtype=np.float64)
        for pol in REQUIRED_POLICIES
    }
    res = boot.run(
        {
            "obl": v["ce_llf"] - v["pop_mpc"],
            "tot": v["ce_llf"] - v["guarded_mpc_e1"],
            "ce": v["ce_llf"],
            "pop": v["pop_mpc"],
            "targ": v["guarded_mpc_e1"],
        },
        {
            "share": lambda m: safe_ratio(m["obl"], m["tot"]),
            "oblivious_gain": lambda m: m["obl"],
            "total_gain": lambda m: m["tot"],
            "mean_ce_llf": lambda m: m["ce"],
            "mean_pop_mpc": lambda m: m["pop"],
            "mean_guarded_mpc_e1": lambda m: m["targ"],
        },
    )
    st_share = res["share"]
    return {
        "cell_id": cell_id,
        "metric": metric,
        "n_seeds": len(seeds),
        "share": st_share.value,
        "share_ci": [st_share.lo, st_share.hi],
        "oblivious_gain": res["oblivious_gain"].value,
        "oblivious_gain_ci": [res["oblivious_gain"].lo, res["oblivious_gain"].hi],
        "total_gain": res["total_gain"].value,
        "total_gain_ci": [res["total_gain"].lo, res["total_gain"].hi],
        "mean_ce_llf": res["mean_ce_llf"].value,
        "mean_pop_mpc": res["mean_pop_mpc"].value,
        "mean_guarded_mpc_e1": res["mean_guarded_mpc_e1"].value,
    }


def _secondary_contrast(
    by_cp: Mapping[tuple[str, str], Mapping[int, dict]],
    boot: Bootstrap,
    *,
    metric: str = PRIMARY_METRIC,
    allowed_seeds: set[int] | None = None,
) -> dict | None:
    seeds = _common_seeds(by_cp, [SEC_CELL_D1, SEC_CELL_D4], allowed_seeds=allowed_seeds)
    if not seeds:
        return None
    v1 = {
        pol: np.array([float(by_cp[(SEC_CELL_D1, pol)][s][metric]) for s in seeds], dtype=np.float64)
        for pol in REQUIRED_POLICIES
    }
    v4 = {
        pol: np.array([float(by_cp[(SEC_CELL_D4, pol)][s][metric]) for s in seeds], dtype=np.float64)
        for pol in REQUIRED_POLICIES
    }
    res = boot.run(
        {
            "o1": v1["ce_llf"] - v1["pop_mpc"],
            "t1": v1["ce_llf"] - v1["guarded_mpc_e1"],
            "o4": v4["ce_llf"] - v4["pop_mpc"],
            "t4": v4["ce_llf"] - v4["guarded_mpc_e1"],
        },
        {
            "share_d1": lambda m: safe_ratio(m["o1"], m["t1"]),
            "share_d4": lambda m: safe_ratio(m["o4"], m["t4"]),
            "contrast": lambda m: safe_ratio(m["o1"], m["t1"]) - safe_ratio(m["o4"], m["t4"]),
        },
    )
    return {
        "cell_d1": SEC_CELL_D1,
        "cell_d4": SEC_CELL_D4,
        "metric": metric,
        "n_seeds": len(seeds),
        "share_d1": res["share_d1"].value,
        "share_d1_ci": [res["share_d1"].lo, res["share_d1"].hi],
        "share_d4": res["share_d4"].value,
        "share_d4_ci": [res["share_d4"].lo, res["share_d4"].hi],
        "contrast_d1_minus_d4": res["contrast"].value,
        "contrast_ci": [res["contrast"].lo, res["contrast"].hi],
    }


def _feasibility_sets(
    by_cp: Mapping[tuple[str, str], Mapping[int, dict]],
    cell_id: str,
) -> dict[str, set[int]]:
    seeds = _common_seeds(by_cp, [cell_id])
    strict_ok: set[int] = set()
    cap_ok: set[int] = set()
    headroom_ok: set[int] = set()
    for s in seeds:
        r = by_cp[(cell_id, "ce_llf")][s]
        if r.get("feasible_strict", True):
            strict_ok.add(s)
        if r.get("feasible_cap", True):
            cap_ok.add(s)
        if r.get("feasible_headroom", True):
            headroom_ok.add(s)
    return {
        "all": set(seeds),
        "feasible_strict": strict_ok,
        "feasible_cap": cap_ok,
        "feasible_headroom": headroom_ok,
    }


def analyse_variant_rows(
    rows: Sequence[dict],
    *,
    variant: str = "t2",
    n_boot: int = T2_N_BOOT,
    boot_seed: int = T2_BOOT_SEED,
    level: float = T2_LEVEL,
    min_feasible: int = REAL_LIMIT_MIN_FEASIBLE,
    metric: str = PRIMARY_METRIC,
) -> dict:
    """Analyse one variant's rows (``t2``, ``t2_emp``, or ``real_limit``)."""
    by_cp, cell_ids = _index_rows(rows)
    boot = Bootstrap(n_boot=n_boot, seed=boot_seed, level=level)

    allowed: set[int] | None = None
    feas_report: dict | None = None

    if variant == "real_limit":
        ref_cell = H1_CELL_ID if H1_CELL_ID in cell_ids else (cell_ids[0] if cell_ids else None)
        if ref_cell is None:
            return {
                "variant": variant,
                "reported": False,
                "reason": "no complete cells present",
                "n_feasible": 0,
                "min_feasible": int(min_feasible),
            }
        fsets = _feasibility_sets(by_cp, ref_cell)
        n_feas_cap = len(fsets["feasible_cap"])
        n_feas_strict = len(fsets["feasible_strict"])
        n_feas_headroom = len(fsets["feasible_headroom"])
        feas_report = {
            "reference_cell": ref_cell,
            "n_total": len(fsets["all"]),
            "n_feasible_cap": n_feas_cap,
            "n_feasible_strict": n_feas_strict,
            "n_feasible_headroom": n_feas_headroom,
            "min_feasible": int(min_feasible),
            "gate_passed": bool(n_feas_cap >= int(min_feasible)),
        }
        if n_feas_cap < int(min_feasible):
            return {
                "variant": variant,
                "reported": False,
                "reason": f"only {n_feas_cap} cap-feasible instances (< {min_feasible})",
                "feasibility": feas_report,
            }
        allowed = fsets["feasible_cap"]

    h1 = _cell_share(by_cp, H1_CELL_ID, boot, metric=metric, allowed_seeds=allowed)
    if h1 is not None and variant == "t2":
        lo = h1["share_ci"][0]
        h1["threshold"] = H1_THRESHOLD
        h1["h1_supported"] = bool(math.isfinite(lo) and lo > H1_THRESHOLD)

    h1_raw_kwh = _cell_share(
        by_cp, H1_CELL_ID, boot, metric=DIAGNOSTIC_METRIC, allowed_seeds=allowed
    )
    secondary = _secondary_contrast(by_cp, boot, metric=metric, allowed_seeds=allowed)
    per_cell = {}
    for cid in cell_ids:
        st = _cell_share(by_cp, cid, boot, metric=metric, allowed_seeds=allowed)
        if st is not None:
            per_cell[cid] = st

    out = {
        "variant": variant,
        "reported": True,
        "meta": {
            "metric": metric,
            "diagnostic_metric": DIAGNOSTIC_METRIC,
            "n_boot": int(n_boot),
            "boot_seed": int(boot_seed),
            "level": float(level),
            "is_hypothesis_test": bool(variant == "t2"),
        },
        "h1": h1,
        "h1_raw_kwh_diagnostic": h1_raw_kwh,
        "secondary_contrast": secondary,
        "cells": per_cell,
    }
    if feas_report is not None:
        out["feasibility"] = feas_report
    return out


def analyse_files(
    t2_rows_path: Path | str,
    *,
    t2_emp_rows_path: Path | str | None = None,
    real_limit_rows_path: Path | str | None = None,
    n_boot: int = T2_N_BOOT,
    boot_seed: int = T2_BOOT_SEED,
    min_feasible: int = REAL_LIMIT_MIN_FEASIBLE,
) -> dict:
    """Analyse T2, and optionally T2-emp and real-limit, from JSONL files."""
    out: dict = {
        "t2": analyse_variant_rows(
            load_rows_file(t2_rows_path),
            variant="t2",
            n_boot=n_boot,
            boot_seed=boot_seed,
            min_feasible=min_feasible,
        )
    }
    if t2_emp_rows_path is not None and Path(t2_emp_rows_path).exists():
        out["t2_emp"] = analyse_variant_rows(
            load_rows_file(t2_emp_rows_path),
            variant="t2_emp",
            n_boot=n_boot,
            boot_seed=boot_seed,
            min_feasible=min_feasible,
        )
    if real_limit_rows_path is not None and Path(real_limit_rows_path).exists():
        out["real_limit"] = analyse_variant_rows(
            load_rows_file(real_limit_rows_path),
            variant="real_limit",
            n_boot=n_boot,
            boot_seed=boot_seed,
            min_feasible=min_feasible,
        )
    return out
