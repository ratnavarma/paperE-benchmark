"""Post hoc round 3 (M6 guard ablation and M3 failure persistence): cells and analysis.

Contract: ``acn/POSTHOC_ROUND3_PROTOCOL.md``.
- M6 (guard ablation): ``guarded_mpc_e1`` vs ``guarded_mpc_e1_g0`` (gamma = 0, running
  minimum intact) on reference (M=3, dA=2, rho=0.95) and tight (M=3, dA=2, rho=1.15)
  cells. Paired bootstrap 95% intervals (10,000 resamples, seed 760500; site-day clustered
  for real data).
- M3 (failure persistence): redraw probability s in {0, 0.2, 0.5} plus Beta-q drawn from
  the frozen beta-binomial fit (persistent across events) on reference (rho=0.95, dA=2)
  and tight (rho=1.15, dA=4) cells. Schedulers: ``ce_llf``, ``pop_mpc``, ``guarded_mpc_e1``.
  Paired bootstrap 95% intervals (10,000 resamples, seed 770500; site-day clustered for
  real data).
"""
from __future__ import annotations

from collections import defaultdict
import math
import re
from typing import Callable, Mapping, Sequence

import numpy as np

from papere.analysis import AnalysisError, Bootstrap, NAN_STAT, Stat
from papere.instance import Cell

M6_POLICIES: tuple[str, ...] = ("guarded_mpc_e1", "guarded_mpc_e1_g0")
M6_BOOT_SEED = 760_500
M6_SYNTH_SEEDS: tuple[int, int] = (61_000, 61_099)
M6_REAL_SEEDS: tuple[int, int] = (760_000, 760_199)

M3_POLICIES: tuple[str, ...] = ("ce_llf", "pop_mpc", "guarded_mpc_e1")
M3_BOOT_SEED = 770_500
M3_SYNTH_SEEDS: tuple[int, int] = (61_000, 61_099)
M3_REAL_SEEDS: tuple[int, int] = (770_000, 770_199)
M3_REDRAW_PROBS: tuple[float, ...] = (0.0, 0.2, 0.5)

SMOKE_SEEDS: tuple[int, int] = (799_990, 799_994)
SMOKE_MAX_SITE_DAYS = 3

DEFAULT_N_BOOT = 10_000
DEFAULT_LEVEL = 0.95

R_AVOID_KEY = "R_avoid_kwh_per100"
MISS_KEY = "deadline_miss_count_per100"


def m6_cells() -> list[tuple[str, Cell]]:
    """Protocol M6 cells: reference (rho=0.95, dA=2) and tight (rho=1.15, dA=2)."""
    return [
        ("reference", Cell(family="F0R", M=3, delta_A=2, delta_b=0, rho=0.95, r=0.3)),
        ("tight", Cell(family="F0R", M=3, delta_A=2, delta_b=0, rho=1.15, r=0.3)),
    ]


def m3_cells(beta_ab: tuple[float, float]) -> list[tuple[str, str, Cell]]:
    """Protocol M3 cells: 2 base cells (reference dA=2 rho=0.95; tight dA=4 rho=1.15) x 4 settings."""
    a, b = float(beta_ab[0]), float(beta_ab[1])
    bases = [
        ("reference", dict(family="F0R", M=3, delta_A=2, delta_b=0, rho=0.95, r=0.3)),
        ("tight", dict(family="F0R", M=3, delta_A=4, delta_b=0, rho=1.15, r=0.3)),
    ]
    out: list[tuple[str, str, Cell]] = []
    for cell_label, kw in bases:
        for s in M3_REDRAW_PROBS:
            setting = f"s{s:g}"
            out.append((cell_label, setting, Cell(**kw, redraw_prob=s)))
        out.append((cell_label, "beta_q", Cell(**kw, beta_q=(a, b))))
    return out


class ClusteredBootstrap:
    """Paired percentile bootstrap, optionally clustered by a discrete cluster key.

    When ``clusters`` is ``None``, delegates directly to ``papere.analysis.Bootstrap`` over
    seeds. When ``clusters`` is supplied (e.g. ``(site, date)`` pairs for real T2 data),
    resamples the ``K`` observed clusters with replacement and evaluates each resampled mean
    as ``sum_k w_{b,k} S_k(v) / sum_k w_{b,k} n_k``, which is the exact ratio estimator for
    the observation-weighted mean under unequal cluster sizes and reduces identically to
    ``Bootstrap`` when every cluster has size 1.
    """

    def __init__(self, n_boot: int = DEFAULT_N_BOOT, seed: int = M6_BOOT_SEED,
                 level: float = DEFAULT_LEVEL) -> None:
        self.n_boot = int(n_boot)
        self.seed = int(seed)
        self.level = float(level)
        self._plain = Bootstrap(n_boot=self.n_boot, seed=self.seed, level=self.level)
        self._counts: dict[int, np.ndarray] = {}

    def _cluster_counts(self, k: int) -> np.ndarray:
        if k not in self._counts:
            rng = np.random.default_rng(self.seed)
            idx = rng.integers(0, k, size=(self.n_boot, k))
            flat = (idx + k * np.arange(self.n_boot)[:, None]).ravel()
            self._counts[k] = np.bincount(flat, minlength=self.n_boot * k).reshape(
                self.n_boot, k).astype(np.float64)
        return self._counts[k]

    def _interval(self, boots: np.ndarray) -> tuple[float, float]:
        b = np.asarray(boots, dtype=np.float64)
        b = b[np.isfinite(b)]
        if b.size == 0:
            return math.nan, math.nan
        alpha = (1.0 - self.level) / 2.0 * 100.0
        lo, hi = np.percentile(b, [alpha, 100.0 - alpha])
        return float(lo), float(hi)

    def run(
        self,
        vectors: Mapping[str, np.ndarray],
        stats: Mapping[str, Callable[[dict], object]],
        *,
        clusters: Sequence | None = None,
    ) -> dict[str, Stat]:
        if clusters is None:
            return self._plain.run(dict(vectors), dict(stats))
        names = list(vectors)
        if not names:
            return {k: NAN_STAT for k in stats}
        n = len(vectors[names[0]])
        for k in names:
            if len(vectors[k]) != n:
                raise AnalysisError(f"vector {k!r} has length {len(vectors[k])}, expected {n}")
        if len(clusters) != n:
            raise AnalysisError(f"clusters has length {len(clusters)}, expected {n}")
        if n == 0:
            return {k: NAN_STAT for k in stats}

        V = np.column_stack([np.asarray(vectors[k], dtype=np.float64) for k in names])
        point = dict(zip(names, V.mean(axis=0)))

        unique_clusters = sorted(set(clusters))
        k_clusters = len(unique_clusters)
        if k_clusters < 2:
            return {
                k: Stat(float(np.asarray(f(point))), math.nan, math.nan)
                for k, f in stats.items()
            }

        c_idx = {c: i for i, c in enumerate(unique_clusters)}
        cid_arr = np.array([c_idx[c] for c in clusters], dtype=np.int64)
        S = np.zeros((k_clusters, len(names)), dtype=np.float64)
        np.add.at(S, cid_arr, V)
        nk = np.bincount(cid_arr, minlength=k_clusters).astype(np.float64)

        W = self._cluster_counts(k_clusters)
        denom = W @ nk
        boots = (W @ S) / denom[:, None]
        bmeans = {k: boots[:, j] for j, k in enumerate(names)}
        out: dict[str, Stat] = {}
        for k, f in stats.items():
            val = float(np.asarray(f(point)))
            lo, hi = self._interval(np.asarray(f(bmeans), dtype=np.float64))
            out[k] = Stat(val, lo, hi)
        return out


def _stat_dict(st: Stat) -> dict[str, float | None]:
    def _clean(x: float) -> float | None:
        return float(x) if math.isfinite(x) else None

    return {
        "value": _clean(st.value),
        "ci_lo": _clean(st.lo),
        "ci_hi": _clean(st.hi),
    }


def _index_policy_rows(
    rows: Sequence[dict],
    allowed_policies: Sequence[str],
) -> tuple[dict[tuple[str, str], dict[int, dict]], list[str]]:
    by_cp: dict[tuple[str, str], dict[int, dict]] = defaultdict(dict)
    cells: set[str] = set()
    pol_set = set(allowed_policies)
    for r in rows:
        if r.get("mode", "frozen") != "frozen":
            continue
        pol = r.get("policy")
        if pol not in pol_set:
            continue
        cid = str(r["cell_id"])
        seed = int(r["seed"])
        by_cp[(cid, pol)][seed] = r
        cells.add(cid)
    return by_cp, sorted(cells)


def _extract_clusters(
    by_cp: Mapping[tuple[str, str], Mapping[int, dict]],
    cell_id: str,
    policies: Sequence[str],
    seeds: Sequence[int],
) -> list[tuple[str, str]]:
    clusters: list[tuple[str, str]] = []
    for s in seeds:
        ref = by_cp[(cell_id, policies[0])][s]
        if "site" not in ref or "date" not in ref:
            raise AnalysisError(
                f"clustered bootstrap requires 'site' and 'date' on row "
                f"({cell_id}, {policies[0]}, {s})"
            )
        ck = (str(ref["site"]), str(ref["date"]))
        for p in policies[1:]:
            other = by_cp[(cell_id, p)][s]
            ock = (str(other.get("site")), str(other.get("date")))
            if ock != ck:
                raise AnalysisError(
                    f"cluster mismatch on ({cell_id}, seed={s}): {policies[0]} has {ck}, "
                    f"{p} has {ock}"
                )
        clusters.append(ck)
    return clusters


def _parse_cell_meta(cell_id: str) -> tuple[str, str]:
    """Return ``(cell_label, setting_label)`` from a round-3 ``cell_id``."""
    if "_rho0.95_" in cell_id and "_dA2_" in cell_id:
        cell_label = "reference"
    elif "_rho1.15_" in cell_id and ("_dA2_" in cell_id or "_dA4_" in cell_id):
        cell_label = "tight"
    else:
        cell_label = cell_id

    m_red = re.search(r"_redraw([0-9.eE+-]+)$", cell_id)
    if m_red:
        setting = f"s{float(m_red.group(1)):g}"
    elif "_betaq" in cell_id:
        setting = "beta_q"
    else:
        setting = "s0"
    return cell_label, setting


def analyse_m6_rows(
    rows: Sequence[dict],
    *,
    clustered: bool = False,
    n_boot: int = DEFAULT_N_BOOT,
    boot_seed: int = M6_BOOT_SEED,
    level: float = DEFAULT_LEVEL,
) -> dict:
    """Analyse M6 (guard ablation) rows: guard on (``guarded_mpc_e1``) vs guard off
    (``guarded_mpc_e1_g0``).

    Reports mean ``R_avoid_kwh_per100``, ``deadline_miss_count_per100``, and avoidable
    deadline misses per 100 (subtracting the clairvoyant bound misses per seed when bound
    data are present; note that guard-on minus guard-off is invariant to subtracting the
    shared per-seed bound because both policies face identical realized availability).
    """
    by_cp, cell_ids = _index_policy_rows(rows, (*M6_POLICIES, "bound"))
    boot = ClusteredBootstrap(n_boot=n_boot, seed=boot_seed, level=level)

    per_cell: dict[str, dict] = {}
    by_label: dict[str, dict] = {}

    for cid in cell_ids:
        seed_sets = [set(by_cp.get((cid, p), {}).keys()) for p in M6_POLICIES]
        seeds = sorted(set.intersection(*seed_sets)) if seed_sets else []
        if not seeds:
            continue

        clusters = _extract_clusters(by_cp, cid, M6_POLICIES, seeds) if clustered else None

        r_on = np.array(
            [float(by_cp[(cid, "guarded_mpc_e1")][s][R_AVOID_KEY]) for s in seeds],
            dtype=np.float64,
        )
        r_off = np.array(
            [float(by_cp[(cid, "guarded_mpc_e1_g0")][s][R_AVOID_KEY]) for s in seeds],
            dtype=np.float64,
        )
        m_on = np.array(
            [float(by_cp[(cid, "guarded_mpc_e1")][s][MISS_KEY]) for s in seeds],
            dtype=np.float64,
        )
        m_off = np.array(
            [float(by_cp[(cid, "guarded_mpc_e1_g0")][s][MISS_KEY]) for s in seeds],
            dtype=np.float64,
        )

        # Avoidable deadline misses per 100: subtract the shared clairvoyant bound misses
        # when available (bound row's deadline_miss_count_per100, or bound_short_count * 100 / N).
        bound_rows = by_cp.get((cid, "bound"), {})
        if all(s in bound_rows and MISS_KEY in bound_rows[s] for s in seeds):
            b_miss = np.array([float(bound_rows[s][MISS_KEY]) for s in seeds], dtype=np.float64)
            bound_source = "bound_row_deadline_miss_count_per100"
        elif all(
            "bound_short_count" in by_cp[(cid, "guarded_mpc_e1")][s]
            and "N" in by_cp[(cid, "guarded_mpc_e1")][s]
            for s in seeds
        ):
            b_miss = np.array(
                [
                    float(by_cp[(cid, "guarded_mpc_e1")][s]["bound_short_count"])
                    * 100.0
                    / float(by_cp[(cid, "guarded_mpc_e1")][s]["N"])
                    for s in seeds
                ],
                dtype=np.float64,
            )
            bound_source = "bound_short_count_per100"
        else:
            b_miss = np.zeros(len(seeds), dtype=np.float64)
            bound_source = "none_raw_deadline_miss_count_per100"

        am_on = m_on - b_miss
        am_off = m_off - b_miss

        res = boot.run(
            {
                "r_on": r_on,
                "r_off": r_off,
                "r_diff": r_on - r_off,
                "m_on": m_on,
                "m_off": m_off,
                "m_diff": m_on - m_off,
                "am_on": am_on,
                "am_off": am_off,
                "am_diff": am_on - am_off,
            },
            {
                "r_on": lambda m: m["r_on"],
                "r_off": lambda m: m["r_off"],
                "r_diff": lambda m: m["r_diff"],
                "m_on": lambda m: m["m_on"],
                "m_off": lambda m: m["m_off"],
                "m_diff": lambda m: m["m_diff"],
                "am_on": lambda m: m["am_on"],
                "am_off": lambda m: m["am_off"],
                "am_diff": lambda m: m["am_diff"],
            },
            clusters=clusters,
        )

        cell_label, _ = _parse_cell_meta(cid)
        entry = {
            "cell_id": cid,
            "cell_label": cell_label,
            "n_seeds": len(seeds),
            "n_clusters": len(set(clusters)) if clusters is not None else None,
            "clustered": bool(clustered),
            "bound_miss_source": bound_source,
            "R_avoid_kwh_per100": {
                "guard_on": _stat_dict(res["r_on"]),
                "guard_off": _stat_dict(res["r_off"]),
                "guard_on_minus_guard_off": _stat_dict(res["r_diff"]),
            },
            "avoidable_deadline_misses_per100": {
                "guard_on": _stat_dict(res["am_on"]),
                "guard_off": _stat_dict(res["am_off"]),
                "guard_on_minus_guard_off": _stat_dict(res["am_diff"]),
            },
            "deadline_miss_count_per100": {
                "guard_on": _stat_dict(res["m_on"]),
                "guard_off": _stat_dict(res["m_off"]),
                "guard_on_minus_guard_off": _stat_dict(res["m_diff"]),
            },
        }
        per_cell[cid] = entry
        if cell_label in ("reference", "tight") and cell_label not in by_label:
            by_label[cell_label] = entry

    return {
        "study": "M6_guard_ablation",
        "meta": {
            "policies": list(M6_POLICIES),
            "metric_residual": R_AVOID_KEY,
            "metric_misses": MISS_KEY,
            "contrast": "guard_on_minus_guard_off (guarded_mpc_e1 - guarded_mpc_e1_g0)",
            "clustered": bool(clustered),
            "cluster_unit": "site_day" if clustered else "seed",
            "n_boot": int(n_boot),
            "boot_seed": int(boot_seed),
            "level": float(level),
        },
        "cells": per_cell,
        "by_label": by_label,
    }


def analyse_m3_rows(
    rows: Sequence[dict],
    *,
    clustered: bool = False,
    n_boot: int = DEFAULT_N_BOOT,
    boot_seed: int = M3_BOOT_SEED,
    level: float = DEFAULT_LEVEL,
) -> dict:
    """Analyse M3 (failure persistence) rows across persistence settings and cells.

    Reports per setting: targeted gain over ``ce_llf`` (``R_avoid(ce_llf) - R_avoid(guarded_mpc_e1)``)
    and over ``pop_mpc`` (``R_avoid(pop_mpc) - R_avoid(guarded_mpc_e1)``) in kWh per 100,
    with paired 95% bootstrap intervals (site-day clustered for real data).
    """
    by_cp, cell_ids = _index_policy_rows(rows, M3_POLICIES)
    boot = ClusteredBootstrap(n_boot=n_boot, seed=boot_seed, level=level)

    per_cell: dict[str, dict] = {}
    by_setting: dict[str, dict[str, dict]] = {}

    for cid in cell_ids:
        seed_sets = [set(by_cp.get((cid, p), {}).keys()) for p in M3_POLICIES]
        seeds = sorted(set.intersection(*seed_sets)) if seed_sets else []
        if not seeds:
            continue

        clusters = _extract_clusters(by_cp, cid, M3_POLICIES, seeds) if clustered else None

        v_ce = np.array(
            [float(by_cp[(cid, "ce_llf")][s][R_AVOID_KEY]) for s in seeds],
            dtype=np.float64,
        )
        v_pop = np.array(
            [float(by_cp[(cid, "pop_mpc")][s][R_AVOID_KEY]) for s in seeds],
            dtype=np.float64,
        )
        v_targ = np.array(
            [float(by_cp[(cid, "guarded_mpc_e1")][s][R_AVOID_KEY]) for s in seeds],
            dtype=np.float64,
        )

        res = boot.run(
            {
                "ce": v_ce,
                "pop": v_pop,
                "targ": v_targ,
                "gain_ce": v_ce - v_targ,
                "gain_pop": v_pop - v_targ,
            },
            {
                "mean_ce_llf": lambda m: m["ce"],
                "mean_pop_mpc": lambda m: m["pop"],
                "mean_guarded_mpc_e1": lambda m: m["targ"],
                "targeted_gain_over_ce_llf": lambda m: m["gain_ce"],
                "targeted_gain_over_pop_mpc": lambda m: m["gain_pop"],
            },
            clusters=clusters,
        )

        cell_label, setting = _parse_cell_meta(cid)
        entry = {
            "cell_id": cid,
            "cell_label": cell_label,
            "setting": setting,
            "n_seeds": len(seeds),
            "n_clusters": len(set(clusters)) if clusters is not None else None,
            "clustered": bool(clustered),
            "targeted_gain_over_ce_llf": _stat_dict(res["targeted_gain_over_ce_llf"]),
            "targeted_gain_over_pop_mpc": _stat_dict(res["targeted_gain_over_pop_mpc"]),
            "mean_ce_llf": _stat_dict(res["mean_ce_llf"]),
            "mean_pop_mpc": _stat_dict(res["mean_pop_mpc"]),
            "mean_guarded_mpc_e1": _stat_dict(res["mean_guarded_mpc_e1"]),
        }
        per_cell[cid] = entry
        by_setting.setdefault(setting, {})[cell_label] = entry

    return {
        "study": "M3_failure_persistence",
        "meta": {
            "policies": list(M3_POLICIES),
            "metric": R_AVOID_KEY,
            "gain_convention": "comparator_minus_targeted (positive = targeted lower R_avoid)",
            "clustered": bool(clustered),
            "cluster_unit": "site_day" if clustered else "seed",
            "n_boot": int(n_boot),
            "boot_seed": int(boot_seed),
            "level": float(level),
        },
        "cells": per_cell,
        "by_setting": by_setting,
    }
