"""ACN T2 study runner (protocol section 3).

Runs the three named release v1.0 schedulers (``ce_llf``, ``pop_mpc``,
``guarded_mpc_e1``) with frozen settings from ``results/TUNING_FROZEN.json`` and
``results/population_params.json`` on a seed range and cell list, writing rows in the
exact format of ``results/f0r_confirm/rows.jsonl`` alongside a provenance manifest.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import multiprocessing as mp
from pathlib import Path
import sys
import time
from typing import Mapping, Sequence

from papere.instance import Cell
from papere.ledger import a_sha256, bound_row, clair_for, evaluate
from papere.policies.base import Family, PopulationParams
from papere.runner import (
    DEFAULT_FROZEN_PATH,
    DEFAULT_PARAMS_PATH,
    REPO_ROOT,
    RowStore,
    _Named,
    _cfg_json,
    _file_sha,
    _finish,
    _git,
    _timing,
    _versions,
    _write_json_atomic,
    cfg_hash,
    load_families,
    load_frozen,
    load_params,
    plan_units,
    resolve_extra_family_names,
    unit_config,
)
from papere.sim import simulate

from .instances import T2SiteDayData, build_acn_instance, instance_feasibility, pick_site_day

DEFAULT_PROTOCOL_PATH = REPO_ROOT / "acn" / "PROTOCOL_ACN.md"
T2_POLICIES: tuple[str, ...] = ("ce_llf", "pop_mpc", "guarded_mpc_e1")


def t2_cells() -> list[Cell]:
    """The 16 protocol section 3 cells: M in {0, 3} x delta in {0, 1, 2, 4} x rho in {0.95, 1.15}."""
    return [
        Cell(family="F0R", M=M, delta_A=dA, delta_b=0, rho=rho, r=0.3)
        for M in (0, 3)
        for dA in (0, 1, 2, 4)
        for rho in (0.95, 1.15)
    ]


T2_CELLS: list[Cell] = t2_cells()


def resolve_t2_cells(cell_ids: Sequence[str] | None = None) -> list[Cell]:
    """Resolve cell IDs against the 16 protocol T2 cells (default: all 16)."""
    if not cell_ids:
        return list(T2_CELLS)
    by_id = {c.cell_id: c for c in T2_CELLS}
    unknown = [cid for cid in cell_ids if cid not in by_id]
    if unknown:
        raise ValueError(f"unknown T2 cell ids: {unknown}; known: {sorted(by_id)}")
    return [by_id[cid] for cid in dict.fromkeys(cell_ids)]


_WCTX: dict = {}


def _init_worker(ctx: dict) -> None:
    global _WCTX
    _WCTX = dict(ctx)
    fams = load_families(_WCTX.get("families"), extra_names=_WCTX.get("extra_family_names"))
    _WCTX["family_map"] = {f.name: f for f in fams}


def _run_one_task(task: tuple) -> tuple[list[dict], float]:
    cpu0 = time.process_time()
    seed, cell, units, want_bound = task
    fams: dict[str, Family] = _WCTX["family_map"]
    params: PopulationParams = _WCTX["params"]
    psha: str | None = _WCTX.get("params_sha256")
    site_days: Sequence[T2SiteDayData] = _WCTX["site_days"]
    variant: str = _WCTX["variant"]
    emp_beta_ab: tuple[float, float] | None = _WCTX.get("emp_beta_ab")
    real_limits: Mapping[str, float] | None = _WCTX.get("real_limits")

    sd = pick_site_day(seed, site_days)
    real_lim = real_limits[sd.site] if real_limits is not None else None
    inst = build_acn_instance(
        seed,
        cell,
        sd,
        emp_beta_ab=emp_beta_ab,
        real_limit_units=real_lim,
    )
    feas = instance_feasibility(inst)
    acn_meta = {
        "variant": variant,
        "site": sd.site,
        "date": sd.local_date.isoformat(),
        **feas,
    }

    rows: list[dict] = []
    A0 = inst.availability()
    sha0 = a_sha256(A0)
    clair0 = clair_for(inst, A0)

    if want_bound:
        t0 = time.perf_counter()
        traj = bound_row(inst, A0, clair0)
        row = evaluate(inst, traj, clair=clair0)
        rows.append(
            _finish(
                row,
                family="bound",
                kind="bound",
                config=None,
                config_index=-1,
                tuned_from=None,
                mode="frozen",
                seed=int(seed),
                params_sha256=psha,
                **_timing(traj, (time.perf_counter() - t0) * 1e3),
                **acn_meta,
            )
        )

    for fam_name, sim_name, cfg_fam, cfg_idx in units:
        fam = fams[fam_name]
        src = fams[cfg_fam]
        cfg = src.default if cfg_idx < 0 else src.grid[cfg_idx]
        t0 = time.perf_counter()
        pol = _Named(fam.make(cfg, params), sim_name)
        traj = simulate(inst, cell, pol, seed)
        wall = (time.perf_counter() - t0) * 1e3
        clair = clair0 if a_sha256(traj.A) == sha0 else None
        row = evaluate(inst, traj, clair=clair)
        rows.append(
            _finish(
                row,
                family=fam.name,
                kind=fam.kind,
                config=_cfg_json(cfg),
                config_index=int(cfg_idx),
                tuned_from=fam.tuned_from,
                mode="frozen",
                params_sha256=psha,
                **_timing(traj, wall),
                **acn_meta,
            )
        )

    return rows, time.process_time() - cpu0


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def protocol_sha256(path: Path | str = DEFAULT_PROTOCOL_PATH) -> str | None:
    """Return hex sha256 of ``acn/PROTOCOL_ACN.md`` (or ``None`` if absent)."""
    p = Path(path)
    if not p.exists():
        return None
    return hashlib.sha256(p.read_bytes()).hexdigest()


def run_t2(
    site_days: Sequence[T2SiteDayData],
    seeds: Sequence[int] | tuple[int, int],
    out_rows_path: Path | str,
    *,
    cells: Sequence[Cell] | None = None,
    policies: Sequence[str] = T2_POLICIES,
    variant: str = "t2",
    emp_beta_ab: tuple[float, float] | None = None,
    real_limits: Mapping[str, float] | None = None,
    include_bound: bool = True,
    workers: int = 1,
    families: Sequence[Family] | None = None,
    manifest_path: Path | str | None = None,
    params_path: Path | str = DEFAULT_PARAMS_PATH,
    frozen_path: Path | str = DEFAULT_FROZEN_PATH,
    protocol_path: Path | str = DEFAULT_PROTOCOL_PATH,
    repo_root: Path | str = REPO_ROOT,
) -> dict:
    """Run ACN T2 (or T2-emp / real-limit) on ``seeds`` x ``cells`` and write JSONL + manifest.

    ``seeds`` may be either an explicit sequence of integer seeds or a ``(lo, hi)``
    inclusive 2-tuple when passed via ``run_t2_range``; here any sequence of ints is
    accepted (use ``range(lo, hi + 1)`` for a contiguous block).
    """
    if not site_days:
        raise ValueError("site_days must be non-empty")
    if variant not in ("t2", "t2_emp", "real_limit"):
        raise ValueError(f"unknown variant {variant!r}")
    if variant == "t2_emp" and emp_beta_ab is None:
        raise ValueError("variant='t2_emp' requires emp_beta_ab=(alpha, beta)")
    if variant == "real_limit" and real_limits is None:
        raise ValueError("variant='real_limit' requires real_limits mapping site -> p99 units")

    seed_list = [int(s) for s in seeds]
    if not seed_list:
        raise ValueError("seeds must be non-empty")
    cell_list = list(T2_CELLS) if cells is None else list(cells)
    if not cell_list:
        raise ValueError("cells must be non-empty")

    params_p = Path(params_path)
    frozen_p = Path(frozen_path)
    params = load_params(params_p)
    params_sha = _file_sha(params_p)
    frozen = load_frozen(frozen_p, params_sha)
    extra_names = resolve_extra_family_names(policies) if families is None else []
    fams = load_families(list(families) if families is not None else None,
                         extra_names=extra_names or None)
    fam_map = {f.name: f for f in fams}
    selected = set(policies)
    unknown_pols = sorted(selected - set(fam_map.keys()))
    if unknown_pols:
        raise ValueError(f"unknown policies {unknown_pols}")

    plan_by_cell = {
        c.cell_id: plan_units(fams, "frozen", c, frozen, selected) for c in cell_list
    }
    rows_path = Path(out_rows_path)
    rows_path.parent.mkdir(parents=True, exist_ok=True)
    m_path = Path(manifest_path) if manifest_path is not None else rows_path.with_name(
        f"{rows_path.stem}_manifest.json"
    )

    store = RowStore(rows_path).load()
    bound_hash = cfg_hash(None)
    skipped = 0
    tasks: list[tuple] = []

    def seen(k: tuple, h: str) -> bool:
        if k not in store.keys:
            return False
        if store.keys[k] != h:
            raise ValueError(f"existing row {k} has a different config hash")
        return True

    for s in seed_list:
        for c in cell_list:
            pend = []
            for u in plan_by_cell[c.cell_id]:
                if seen(("F0R", s, c.cell_id, u[1]), cfg_hash(unit_config(fam_map, u))):
                    skipped += 1
                else:
                    pend.append(u)
            want_bound = bool(include_bound) and not seen(
                ("F0R", s, c.cell_id, "bound"), bound_hash
            )
            if include_bound and not want_bound:
                skipped += 1
            if pend or want_bound:
                tasks.append((s, c, pend, want_bound))

    n_workers = max(1, min(int(workers), len(tasks) or 1))
    started = _now_utc()
    t_wall0, t_cpu0 = time.perf_counter(), time.process_time()
    pool_cpu = 0.0
    written = 0

    ctx = {
        "params": params,
        "params_sha256": params_sha,
        "families": list(families) if families is not None else None,
        "extra_family_names": extra_names or None,
        "site_days": list(site_days),
        "variant": variant,
        "emp_beta_ab": tuple(float(x) for x in emp_beta_ab) if emp_beta_ab is not None else None,
        "real_limits": dict(real_limits) if real_limits is not None else None,
    }

    store.open()
    status = "failed"
    try:
        def consume(res: tuple[list[dict], float]) -> None:
            nonlocal written, pool_cpu
            rows, cpu = res
            if n_workers > 1:
                pool_cpu += cpu
            for r in rows:
                store.append(r)
                written += 1

        if n_workers == 1:
            _init_worker(ctx)
            for t in tasks:
                consume(_run_one_task(t))
        else:
            methods = mp.get_all_start_methods()
            use_fork = "fork" in methods and (sys.platform == "linux" or families is not None)
            mpctx = mp.get_context("fork" if use_fork else None)
            with mpctx.Pool(n_workers, initializer=_init_worker, initargs=(ctx,)) as pool:
                for res in pool.imap(_run_one_task, tasks, chunksize=1):
                    consume(res)
        status = "complete"
    finally:
        store.close()
        wall_s = time.perf_counter() - t_wall0
        cpu_s = time.process_time() - t_cpu0 + pool_cpu
        ended = _now_utc()
        manifest = {
            "variant": variant,
            "status": status,
            "started_utc": started,
            "ended_utc": ended,
            "wall_s": wall_s,
            "cpu_s": cpu_s,
            "git": _git(Path(repo_root), [params_p, frozen_p]),
            "protocol_path": str(protocol_path),
            "protocol_sha256": protocol_sha256(protocol_path),
            "population_params_sha256": params_sha,
            "tuning_frozen_sha256": _file_sha(frozen_p),
            "package_versions": _versions(),
            "seeds": {
                "first": min(seed_list),
                "last": max(seed_list),
                "count": len(seed_list),
                "values": seed_list if len(seed_list) <= 250 else None,
            },
            "cells": [c.cell_id for c in cell_list],
            "policies": list(policies),
            "include_bound": bool(include_bound),
            "workers": n_workers,
            "emp_beta_ab": (
                [float(emp_beta_ab[0]), float(emp_beta_ab[1])] if emp_beta_ab is not None else None
            ),
            "real_limits": dict(real_limits) if real_limits is not None else None,
            "n_eligible_site_days": len(site_days),
            "eligible_site_days": [
                {"site": sd.site, "date": sd.local_date.isoformat(), "N": sd.N}
                for sd in site_days
            ],
            "rows_path": str(rows_path),
            "rows_written": written,
            "rows_skipped": skipped,
            "total_rows": len(store),
        }
        _write_json_atomic(m_path, manifest)

    return manifest
