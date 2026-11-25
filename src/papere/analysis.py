"""Analysis of the saved rows: E1-E3, the secondary endpoints, gate G2 and the data file.

Contract: docs/ANALYSIS_SPEC.md (every section). Every number is development. The unit is
the seed; policies are paired within seed and cell; intervals are paired bootstrap over
seeds (10,000 resamples, 95% percentile, fixed bootstrap seed).

Bootstrap
---------
``Bootstrap`` draws one resample-count matrix per sample size ``n`` from a generator seeded
with ``BOOT_SEED``, so a call is reproducible and any two calls with the same seed list
resample the seeds identically. Within one call every quantity (gaps at each delay, the
contrast, the oracle contrast, the ratio) is computed from the same resamples, so the
quantities of a contrast are resampled jointly.

Rows and refusals (ANALYSIS_SPEC 4b)
------------------------------------
``load_rows`` reads ``<dir>/rows.jsonl`` (or a file path) and keeps only ``mode == "frozen"``
rows of the requested ``study_family`` (tuning rows are skipped). It refuses a corrupt row, a
row lacking ``mode`` or ``study_family``, a kept row of another study family and a kept row
whose seed lies outside the run's range. ``RowSet.require`` refuses unless every required
(cell, policy) holds every seed of the range; ``check_kinds`` refuses a wrong row kind or a
privileged row outside the reference and bound sets. Every ``AnalysisError`` makes the CLI exit
2 with nothing written; there is no partial computation and no silent subset.

Readings and conventions (docs/OPEN_QUESTIONS.md rows 49 and 52-56)
-------------------------------------------------------------------
* E1 best oblivious policy (primary): per cell, the O member with the lowest frozen tuning
  objective in results/TUNING_FROZEN.json (ce_llf, ce_edf and pes_llf are points of
  sym_margin's grid and are not in the frozen file). Sensitivities: the floor allowed in the
  choice; and, per (M, rho), the single O member minimizing E1 itself on the development seeds
  (a conservative lower reading).
* E2 splits come in the ledger's two consistent readings. Reading A pairs ``R_uncorr_hi``
  with ``R_corr_lo``; reading B pairs ``R_uncorr_lo`` with ``R_corr_hi``. The prediction "the
  gain sits in R_uncorr" holds under a reading when the paired gain in R_uncorr has an
  interval wholly above 0 and exceeds the paired gain in R_corr. It is "supported" only if it
  holds under both readings.
* E3 uses ``R_abs_u`` (units on the instance). The primary pass rule is the simultaneous
  (Bonferroni) 95% interval; pointwise misses, the chance count and a binomial p-value are
  reported beside it.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from fractions import Fraction
from pathlib import Path
from typing import Callable, Iterable, Sequence

import numpy as np

from . import prop_enum
from .generator import F0R_CELLS, KCOPY_CELLS, scale_cell
from .instance import Cell

REPO_ROOT = Path(__file__).resolve().parents[2]
ROWS_NAME = "rows.jsonl"
LABEL = "development"

BOOT_SEED = 20261020
N_BOOT = 10_000
THRESHOLD = 0.5            # kWh per 100 participants per event (PLAN 6)
HEADLINE_SHARE = 0.8       # PLAN 8, G2
TOL = 1e-9                 # float slack on equality boundaries (80% share, E3 containment)

OBLIVIOUS = ("ce_llf", "ce_edf", "pes_llf", "sym_margin", "persistence", "uncorr_pes",
             "probe_first", "mpc_ce", "mpc_pes", "pop_mpc")
FLOOR = "floor"
CANDIDATE = "guarded_mpc_e1"
REFERENCE = "oracle_mpc"
PER_PARTICIPANT = ("user_flag", "rwdf_e", "rwdf_e_literal", "llf_post")
BOUND = "bound"

R_KEY = "R_avoid_kwh_per100"
READINGS = {"A": ("R_uncorr_hi_kwh_per100", "R_corr_lo_kwh_per100"),
            "B": ("R_uncorr_lo_kwh_per100", "R_corr_hi_kwh_per100")}
SPLIT_KEYS = ("R_uncorr_hi_kwh_per100", "R_uncorr_lo_kwh_per100",
              "R_corr_hi_kwh_per100", "R_corr_lo_kwh_per100")
DESCRIPTIVE_KEYS = (R_KEY, *SPLIT_KEYS, "event_shortfall_kwh_per100",
                    "violation_count_per100", "violation_kwslot",
                    "violation_longest_run_slots", "hedge_waste_kwslot", "peak_kw",
                    "deadline_miss_count_per100", "deadline_miss_kwh_per100", "cpu_ms_mean")
TIMING_KEYS = ("cpu_ms_mean", "cpu_ms_p95", "cpu_ms_max", "wall_ms")
E1_KEEP = tuple(dict.fromkeys((*DESCRIPTIVE_KEYS, "N")))
E3_KEEP = ("R_abs_u", "R_avoid_u", "N")
SCALE_KEEP = tuple(dict.fromkeys((R_KEY, *TIMING_KEYS, "N")))
E3_POLICIES = ("pop_mpc", REFERENCE, CANDIDATE)

KIND_OF = {**{p: "oblivious" for p in OBLIVIOUS}, FLOOR: "oblivious", CANDIDATE: "candidate",
           REFERENCE: "reference", **{p: "per_participant" for p in PER_PARTICIPANT},
           BOUND: "bound"}
PRIVILEGED_OK = (REFERENCE, BOUND)
FROZEN_KEY = "mean_R_avoid_kwh_per100"
TUNE_RANGE = (60000, 60049)
SCALE_DELTA_A = (0, 2)
RUN_RANGES = {"f0r": (61000, 61099), "kcopy": (61500, 61599), "scale": (63000, 63019),
              "pilot": (61000, 61019)}
DEFAULT_FROZEN = "results/TUNING_FROZEN.json"
DEFAULT_DIRS = {"f0r": "results/f0r_dev", "kcopy": "results/kcopy_dev",
                "scale": "results/scale_dev"}
DEFAULT_PAPER_NUMBERS = "results/paper_numbers.json"
DEFAULT_G2_NUMBERS = "results/g2_numbers.json"
G2_CELL = dict(M=3, delta_A=2, rho=0.95)


class AnalysisError(Exception):
    """A malformed input (corrupt row) or an impossible request."""


# ---------------------------------------------------------------------------------------
# statistics
# ---------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Stat:
    """A statistic with its 95% percentile interval (NaN when undefined)."""

    value: float
    lo: float
    hi: float

    def wholly_above(self, x: float) -> bool:
        return self.lo > x

    def wholly_below(self, x: float) -> bool:
        return self.hi < x

    def contains(self, x: float, tol: float = 0.0) -> bool:
        return self.lo - tol <= x <= self.hi + tol


NAN_STAT = Stat(math.nan, math.nan, math.nan)


def safe_ratio(a, b):
    """a / b elementwise, NaN where |b| is below 1e-12."""
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    with np.errstate(divide="ignore", invalid="ignore"):
        out = np.where(np.abs(b) > 1e-12, a / np.where(np.abs(b) > 1e-12, b, 1.0), np.nan)
    return float(out) if out.ndim == 0 else out


class Bootstrap:
    """Paired bootstrap over seeds with a fixed generator."""

    def __init__(self, n_boot: int = N_BOOT, seed: int = BOOT_SEED, level: float = 0.95):
        self.n_boot, self.seed, self.level = int(n_boot), int(seed), float(level)
        self._counts: dict[int, np.ndarray] = {}

    def counts(self, n: int) -> np.ndarray:
        """``[n_boot, n]`` multiplicities of each seed in each resample."""
        if n not in self._counts:
            rng = np.random.default_rng(self.seed)
            idx = rng.integers(0, n, size=(self.n_boot, n))
            flat = (idx + n * np.arange(self.n_boot)[:, None]).ravel()
            self._counts[n] = np.bincount(flat, minlength=self.n_boot * n).reshape(
                self.n_boot, n).astype(np.float64)
        return self._counts[n]

    def _interval(self, boots: np.ndarray) -> tuple[float, float]:
        b = np.asarray(boots, dtype=float)
        b = b[np.isfinite(b)]
        if b.size == 0:
            return math.nan, math.nan
        a = (1.0 - self.level) / 2.0 * 100.0
        lo, hi = np.percentile(b, [a, 100.0 - a])
        return float(lo), float(hi)

    def run(self, vectors: dict[str, np.ndarray],
            stats: dict[str, Callable[[dict], object]]) -> dict[str, Stat]:
        """Statistics of the means of aligned per-seed vectors, resampled jointly.

        Each ``stats`` function receives ``{name: mean}`` (floats for the point value,
        arrays of length ``n_boot`` for the resamples) and returns a number or array.
        """
        names = list(vectors)
        if not names:
            return {k: NAN_STAT for k in stats}
        n = len(vectors[names[0]])
        for k in names:
            if len(vectors[k]) != n:
                raise AnalysisError(f"vector {k!r} has length {len(vectors[k])}, expected {n}")
        if n < 2:
            point = {k: float(vectors[k].mean()) if n else math.nan for k in names}
            return {k: Stat(float(np.asarray(f(point))), math.nan, math.nan)
                    for k, f in stats.items()}
        V = np.column_stack([np.asarray(vectors[k], dtype=float) for k in names])
        point = dict(zip(names, V.mean(axis=0)))
        boots = self.counts(n) @ V / n
        bmeans = {k: boots[:, j] for j, k in enumerate(names)}
        out = {}
        for k, f in stats.items():
            val = float(np.asarray(f(point)))
            lo, hi = self._interval(np.asarray(f(bmeans), dtype=float))
            out[k] = Stat(val, lo, hi)
        return out

    def mean_ci(self, v: np.ndarray) -> Stat:
        return self.run({"v": np.asarray(v, dtype=float)}, {"m": lambda m: m["v"]})["m"]

    def mean_ci_matrix(self, V: np.ndarray) -> list[Stat]:
        """Mean and interval of every column of ``V`` ([n, k]) in one pass."""
        V = np.asarray(V, dtype=float)
        n, k = V.shape
        if n < 2:
            return [Stat(float(V[:, j].mean()) if n else math.nan, math.nan, math.nan)
                    for j in range(k)]
        boots = self.counts(n) @ V / n
        pt = V.mean(axis=0)
        return [Stat(float(pt[j]), *self._interval(boots[:, j])) for j in range(k)]


def reading_label(lo: float, hi: float, threshold: float = THRESHOLD) -> str:
    """The four-way reading of an interval against the practical threshold (ANALYSIS_SPEC 2).

    Strict inequalities: an interval touching 0 includes 0; one touching the threshold
    contains it. A wholly negative interval (outside the four readings) is labelled
    separately so it is never read as "not detected".
    """
    if not (math.isfinite(lo) and math.isfinite(hi)):
        return "interval undefined"
    if hi < 0:
        return "reversed: interval wholly below 0"
    if lo > threshold:
        return "detected above the practical threshold"
    if lo > 0 and hi < threshold:
        return "detected, below the practical threshold"
    if lo > 0:
        return "detected, size uncertain against the threshold"
    return "not detected at this size"


# ---------------------------------------------------------------------------------------
# row loading
# ---------------------------------------------------------------------------------------
class RowSet:
    """Frozen-mode rows of one study family, reduced to the metrics asked for."""

    def __init__(self, path: Path | None, study: str | None, seed_range: tuple[int, int]):
        self.path = path
        self.study = study
        self.seed_range = (int(seed_range[0]), int(seed_range[1]))
        self.expected_seeds = list(range(self.seed_range[0], self.seed_range[1] + 1))
        self.sha256: str | None = None
        self.n_rows = 0
        self.n_kept = 0
        self.skipped: dict[str, int] = {}
        self.partial_tail = False
        self.duplicates = 0
        self.missing: str | None = None
        self._vals: dict[tuple[str, str], dict[str, dict[int, float]]] = {}
        self._seeds: dict[tuple[str, str], set[int]] = {}
        self._kind: dict[tuple[str, str], set] = {}
        self._priv: dict[tuple[str, str], set] = {}

    # -- queries
    def cells(self) -> list[str]:
        return sorted({c for c, _ in self._vals})

    def policies(self, cell_id: str | None = None) -> list[str]:
        return sorted({p for c, p in self._vals if cell_id is None or c == cell_id})

    def has(self, cell_id: str, policy: str) -> bool:
        return (cell_id, policy) in self._vals

    def seeds(self, cell_id: str, policy: str) -> list[int]:
        return sorted(self._seeds.get((cell_id, policy), ()))

    def seedset(self, cell_id: str, policy: str) -> set[int]:
        return self._seeds.get((cell_id, policy), set())

    def metrics(self, cell_id: str, policy: str) -> list[str]:
        return sorted(self._vals.get((cell_id, policy), {}))

    def vec(self, cell_id: str, policy: str, metric: str, seeds: Sequence[int]) -> np.ndarray:
        try:
            d = self._vals[(cell_id, policy)][metric]
            v = np.array([d[s] for s in seeds], dtype=float)
        except KeyError:
            raise AnalysisError(f"no values of {metric!r} for policy {policy!r} on cell "
                                f"{cell_id!r} at the requested seeds") from None
        if not np.isfinite(v).all():
            raise AnalysisError(f"non-finite {metric!r} for policy {policy!r} on {cell_id!r}")
        return v

    def n_of(self, cell_id: str, policy: str) -> int | None:
        d = self._vals.get((cell_id, policy), {}).get("N")
        return int(next(iter(d.values()))) if d else None

    @property
    def source(self) -> str:
        return str(self.path) if self.path else "(none)"

    # -- completeness (ANALYSIS_SPEC 4b)
    def require(self, cells: Iterable[str], policies: Iterable[str]) -> None:
        """Refuse unless every (cell, policy) has a row for every seed of the run's range."""
        if self.missing:
            raise AnalysisError(f"{self.study} input missing: {self.missing}")
        want = set(self.expected_seeds)
        bad = []
        for c in dict.fromkeys(cells):
            for p in dict.fromkeys(policies):
                gone = want - self._seeds.get((c, p), set())
                if gone:
                    bad.append((c, p, len(gone)))
        if bad:
            raise AnalysisError(
                f"{self.study}: {len(bad)} (cell, policy) pairs lack rows for "
                f"{self.seed_range[0]}..{self.seed_range[1]}; first: "
                + "; ".join(f"{c} / {p} ({n} seeds missing)" for c, p, n in bad[:4]))

    def check_kinds(self, cells: Iterable[str], policies: Iterable[str]) -> None:
        """Rows carry the kind the analysis assumes; privileged rows only in reference/bound."""
        for c in dict.fromkeys(cells):
            for p in dict.fromkeys(policies):
                key = (c, p)
                if key not in self._vals:
                    continue
                kinds, priv = self._kind.get(key, set()), self._priv.get(key, set())
                if kinds != {KIND_OF[p]}:
                    raise AnalysisError(f"{c} / {p}: row kind {sorted(map(str, kinds))}, "
                                        f"expected {KIND_OF[p]!r}")
                if p not in PRIVILEGED_OK and priv != {False}:
                    raise AnalysisError(f"{c} / {p}: privileged row in a non-reference set "
                                        f"(privileged={sorted(map(str, priv))})")


def load_rows(source: Path | str | None, study: str, *, seed_range: tuple[int, int],
              keep: Iterable[str] = E1_KEEP, policies: Iterable[str] | None = None,
              modes: Iterable[str] = ("frozen",)) -> RowSet:
    """Read a rows.jsonl (or a directory holding one).

    A missing input gives an empty ``RowSet`` with ``missing`` set (``require`` then refuses).
    Refuses (``AnalysisError``) a corrupt row, a row without ``mode``, ``study_family``,
    ``cell_id`` or ``seed``, a kept row of another study family, and a kept row whose seed
    lies outside ``seed_range``. Tuning rows (``mode`` not in ``modes``) are skipped.
    """
    keep = tuple(keep)
    pol = None if policies is None else set(policies)
    modes = set(modes)
    p = Path(source) if source is not None else None
    if p is not None and p.is_dir():
        p = p / ROWS_NAME
    rs = RowSet(p, study, seed_range)
    if p is None:
        rs.missing = "no input given"
        return rs
    if not p.exists():
        rs.missing = f"{p} does not exist"
        return rs
    lo, hi = rs.seed_range
    with open(p, "rb") as f:
        for n, line in enumerate(f, 1):
            if not line.endswith(b"\n"):
                rs.partial_tail = True
                break
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except ValueError as e:
                raise AnalysisError(f"{p}: corrupt row at line {n}: {e}") from None
            rs.n_rows += 1
            for need in ("mode", "study_family", "cell_id", "seed", "policy"):
                if need not in row:
                    raise AnalysisError(f"{p}: row at line {n} lacks {need!r}")
            if str(row["mode"]) not in modes:
                rs.skipped["mode"] = rs.skipped.get("mode", 0) + 1
                continue
            if row["study_family"] != study:
                raise AnalysisError(f"{p}: row at line {n} has study_family "
                                    f"{row['study_family']!r}, expected {study!r}")
            policy = str(row["policy"])
            if pol is not None and policy not in pol:
                rs.skipped["policy"] = rs.skipped.get("policy", 0) + 1
                continue
            try:
                cell, seed = str(row["cell_id"]), int(row["seed"])
            except (TypeError, ValueError):
                raise AnalysisError(f"{p}: row at line {n} has a bad cell_id or seed") from None
            if not lo <= seed <= hi:
                raise AnalysisError(f"{p}: row at line {n} has seed {seed} outside the "
                                    f"{study} range {lo}..{hi}")
            key = (cell, policy)
            seen = rs._seeds.setdefault(key, set())
            if seed in seen:
                rs.duplicates += 1
                continue
            seen.add(seed)
            rs._kind.setdefault(key, set()).add(row.get("kind"))
            rs._priv.setdefault(key, set()).add(row.get("privileged"))
            slot = rs._vals.setdefault(key, {})
            for m in keep:
                v = row.get(m)
                if v is None:
                    continue
                slot.setdefault(m, {})[seed] = float(v)
            rs.n_kept += 1
    rs.sha256 = file_sha256(p)
    return rs


def file_sha256(path: Path | str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def f0r_cell_id(M: int, delta_A: int, rho: float, r: float = 0.3, delta_b: int = 0,
                family: str = "F0R") -> str:
    return Cell(family=family, M=M, delta_A=delta_A, delta_b=delta_b, rho=rho, r=r).cell_id


def row_filter(rs: RowSet, cells: Sequence[str] | str, policies: Sequence[str] | str,
               seeds: Sequence[int]) -> str:
    cells = [cells] if isinstance(cells, str) else list(cells)
    policies = [policies] if isinstance(policies, str) else list(policies)
    s = f"{min(seeds)}..{max(seeds)}" if len(seeds) else "none"
    return (f"study_family={rs.study}; mode=frozen; cell_id in [{', '.join(cells)}]; "
            f"policy in [{', '.join(policies)}]; seeds {s} (n={len(seeds)})")


# ---------------------------------------------------------------------------------------
# best oblivious policy: fixed in advance on the tuning seeds (ANALYSIS_SPEC 2)
# ---------------------------------------------------------------------------------------
def load_frozen_file(path: Path | str | None) -> dict:
    """Read results/TUNING_FROZEN.json; refuse if absent or not frozen on the tuning set."""
    if path is None or not Path(path).exists():
        raise AnalysisError(f"the frozen tuning file is required and was not found: {path} "
                            "(the best oblivious policy is fixed on the tuning seeds)")
    try:
        d = json.loads(Path(path).read_text())
    except ValueError as e:
        raise AnalysisError(f"{path}: not valid JSON: {e}") from None
    meta = d.get("_meta") if isinstance(d, dict) else None
    if not meta or meta.get("seeds") != list(TUNE_RANGE):
        raise AnalysisError(f"{path}: not frozen on the tuning seeds {list(TUNE_RANGE)}")
    return d


def frozen_best(frozen: dict, cell_id: str, *, include_floor: bool = False) -> dict:
    """The O member with the lowest frozen tuning objective on one F0-R cell.

    Only tunable families appear in the frozen file; ce_llf, ce_edf and pes_llf are single
    points of sym_margin's grid, so sym_margin's tuned value bounds them on the tuning
    seeds and they are not candidates. Ties (to 9 digits) go to the earlier member of O.
    """
    names = [p for p in OBLIVIOUS if p in frozen]
    if include_floor:
        if FLOOR not in frozen:
            raise AnalysisError("the frozen file has no floor family")
        names.append(FLOOR)
    if not names:
        raise AnalysisError("the frozen file holds no oblivious family")
    obj = {}
    for p in names:
        ent = frozen[p].get(cell_id) if isinstance(frozen.get(p), dict) else None
        if ent is None or FROZEN_KEY not in ent:
            raise AnalysisError(f"the frozen file has no {FROZEN_KEY} for {p} on {cell_id}")
        obj[p] = float(ent[FROZEN_KEY])
    order = OBLIVIOUS + (FLOOR,)
    best = min(names, key=lambda p: (round(obj[p], 9), order.index(p)))
    return {"best": best, "objectives": obj}


# ---------------------------------------------------------------------------------------
# E1
# ---------------------------------------------------------------------------------------
def e1_analysis(rs: RowSet, boot: Bootstrap, M: int, rho: float, *, selection: str = "frozen",
                frozen: dict | None = None, r: float = 0.3, delta_b: int = 0,
                high: Sequence[int] = (2, 4), low: Sequence[int] = (0, 1),
                include_floor: bool = False, candidate: str = CANDIDATE,
                reference: str = REFERENCE) -> dict:
    """E1 at one (M, rho): per-delta gaps, the contrast, the oracle share and the label.

    ``gap(s, d) = R_avoid(best O at that cell) - R_avoid(candidate)``;
    ``E1(s) = mean_{d in high} gap - mean_{d in low} gap``.

    ``selection="frozen"`` (primary): the best O of each cell is the O member with the lowest
    frozen tuning objective (``frozen`` is the parsed TUNING_FROZEN.json).
    ``selection="min_e1"`` (sensitivity, a conservative lower reading): the single O member,
    the same at every delay cell, that minimizes E1 itself on these seeds.
    Refuses (``AnalysisError``) if any delay cell, policy or seed is missing.
    """
    deltas = list(high) + [d for d in low if d not in high]
    cells = {d: f0r_cell_id(M, d, rho, r, delta_b) for d in deltas}
    pols = list(OBLIVIOUS) + [candidate, reference] + ([FLOOR] if include_floor else [])
    rs.require(cells.values(), pols)
    seeds = rs.expected_seeds
    rs.check_kinds(cells.values(), pols)
    res: dict = {"M": M, "rho": rho, "r": r, "delta_b": delta_b, "include_floor": include_floor,
                 "selection": selection, "high": list(high), "low": list(low), "cells": cells,
                 "best": {}, "contrast": None, "gaps": {}, "oracle_gaps": {},
                 "oracle_contrast": None, "share": None, "share_defined": False,
                 "label": None, "seeds": seeds, "used": deltas, "hi_used": list(high),
                 "lo_used": list(low)}
    vec_cand = {d: rs.vec(cells[d], candidate, R_KEY, seeds) for d in deltas}
    vec_orc = {d: rs.vec(cells[d], reference, R_KEY, seeds) for d in deltas}
    names = list(OBLIVIOUS)

    def contrast_of(per_delta: dict[int, np.ndarray]) -> float:
        return float(np.mean([per_delta[d].mean() for d in high])
                     - np.mean([per_delta[d].mean() for d in low]))

    if selection == "frozen":
        if frozen is None:
            raise AnalysisError("selection='frozen' needs the frozen tuning file")
        chosen = {}
        for d in deltas:
            fb = frozen_best(frozen, cells[d], include_floor=include_floor)
            chosen[d] = fb["best"]
            res["best"][d] = {"frozen_objectives": fb["objectives"]}
    elif selection == "min_e1":
        if include_floor:
            raise AnalysisError("the minimum-E1 sensitivity is over O and excludes the floor")
        scores = {}
        for p in names:
            gaps_p = {d: rs.vec(cells[d], p, R_KEY, seeds) - vec_cand[d] for d in deltas}
            scores[p] = contrast_of(gaps_p)
        pick = min(names, key=lambda p: (scores[p], names.index(p)))
        chosen = {d: pick for d in deltas}
        for d in deltas:
            res["best"][d] = {"min_e1_scores": scores}
    else:
        raise AnalysisError(f"unknown selection {selection!r}")

    vec_best = {}
    for d in deltas:
        pol = chosen[d]
        vec_best[d] = rs.vec(cells[d], pol, R_KEY, seeds)
        dev = {p: float(rs.vec(cells[d], p, R_KEY, seeds).mean())
               for p in (names + ([FLOOR] if include_floor else []))}
        res["best"][d].update({"policy": pol, "mean_R_avoid_kwh_per100": float(vec_best[d].mean()),
                               "means": dev})
    vectors, stats = {}, {}
    for d in deltas:
        vectors[f"g{d}"] = vec_best[d] - vec_cand[d]
        vectors[f"o{d}"] = vec_best[d] - vec_orc[d]
        stats[f"gap{d}"] = (lambda m, d=d: m[f"g{d}"])
        stats[f"ogap{d}"] = (lambda m, d=d: m[f"o{d}"])

    def side(m, key, ds):
        return sum(m[f"{key}{d}"] for d in ds) / len(ds)

    stats["e1"] = lambda m: side(m, "g", high) - side(m, "g", low)
    stats["e1o"] = lambda m: side(m, "o", high) - side(m, "o", low)
    stats["share"] = lambda m: safe_ratio(side(m, "g", high) - side(m, "g", low),
                                          side(m, "o", high) - side(m, "o", low))
    out = boot.run(vectors, stats)
    for d in deltas:
        res["gaps"][d] = out[f"gap{d}"]
        res["oracle_gaps"][d] = out[f"ogap{d}"]
    res["contrast"] = out["e1"]
    res["label"] = reading_label(out["e1"].lo, out["e1"].hi)
    res["oracle_contrast"] = out["e1o"]
    den = out["e1o"]
    # a ratio of means has no usable interval when the denominator's interval includes 0
    res["share_defined"] = bool(math.isfinite(den.lo) and (den.lo > 0 or den.hi < 0))
    sh = out["share"]
    res["share"] = sh if res["share_defined"] else Stat(sh.value, math.nan, math.nan)
    return res


# ---------------------------------------------------------------------------------------
# E2
# ---------------------------------------------------------------------------------------
def _holds(gu: Stat, diff: Stat) -> bool:
    """The gain sits in R_uncorr under one reading (see module docstring)."""
    return bool(math.isfinite(gu.lo) and math.isfinite(diff.lo) and gu.lo > 0 and diff.lo > 0)


def e2_analysis(rs: RowSet, boot: Bootstrap, e1: dict, *, candidate: str = CANDIDATE) -> dict:
    """E2 for one (M, rho): paired gains in R_uncorr and R_corr under both readings.

    Best O per cell is the one E1 chose. Reported per delay cell and for the E1-style
    contrast (high minus low delays). ``supported`` needs both readings to hold.
    """
    res: dict = {"M": e1["M"], "rho": e1["rho"], "cells": {}, "contrast": None, "missing": []}
    used = e1["used"]
    seeds = e1["seeds"]
    if not used:
        res["missing"].append("no E1 cells")
        return res
    vectors, stats = {}, {}
    for d in used:
        cell = e1["cells"][d]
        b = e1["best"][d]["policy"]
        for tag, (ku, kc) in READINGS.items():
            try:
                gu = rs.vec(cell, b, ku, seeds) - rs.vec(cell, candidate, ku, seeds)
                gc = rs.vec(cell, b, kc, seeds) - rs.vec(cell, candidate, kc, seeds)
            except AnalysisError as ex:
                res["missing"].append(str(ex))
                continue
            vectors[f"u{tag}{d}"], vectors[f"c{tag}{d}"] = gu, gc
            stats[f"U{tag}{d}"] = (lambda m, t=tag, d=d: m[f"u{t}{d}"])
            stats[f"C{tag}{d}"] = (lambda m, t=tag, d=d: m[f"c{t}{d}"])
            stats[f"D{tag}{d}"] = (lambda m, t=tag, d=d: m[f"u{t}{d}"] - m[f"c{t}{d}"])
    hi = [d for d in e1.get("hi_used", []) if all(f"u{t}{d}" in vectors for t in READINGS)]
    lo = [d for d in e1.get("lo_used", []) if all(f"u{t}{d}" in vectors for t in READINGS)]
    if hi and lo:
        for tag in READINGS:
            for kind in ("u", "c"):
                stats[f"{kind.upper()}{tag}x"] = (
                    lambda m, t=tag, k=kind: sum(m[f"{k}{t}{d}"] for d in hi) / len(hi)
                    - sum(m[f"{k}{t}{d}"] for d in lo) / len(lo))
            stats[f"D{tag}x"] = (lambda m, t=tag: (
                sum(m[f"u{t}{d}"] - m[f"c{t}{d}"] for d in hi) / len(hi)
                - sum(m[f"u{t}{d}"] - m[f"c{t}{d}"] for d in lo) / len(lo)))
    if not vectors:
        return res
    out = boot.run(vectors, stats)

    def pack(suffix: str) -> dict:
        readings = {}
        for tag in READINGS:
            if f"U{tag}{suffix}" not in out:
                continue
            gu, gc, df = out[f"U{tag}{suffix}"], out[f"C{tag}{suffix}"], out[f"D{tag}{suffix}"]
            readings[tag] = {"gain_uncorr": gu, "gain_corr": gc, "diff": df,
                             "holds": _holds(gu, df)}
        return {"readings": readings,
                "supported": bool(len(readings) == len(READINGS)
                                  and all(v["holds"] for v in readings.values()))}

    for d in used:
        res["cells"][d] = pack(str(d))
    if hi and lo:
        res["contrast"] = pack("x")
    return res


# ---------------------------------------------------------------------------------------
# E3
# ---------------------------------------------------------------------------------------
def _frac(q: float) -> Fraction:
    return Fraction(str(q))


def t_interval(v: np.ndarray, level: float) -> tuple[float, float]:
    """Student-t Monte Carlo interval of the mean of ``v`` at confidence ``level``."""
    from scipy import stats as sps
    n = len(v)
    m = float(np.mean(v))
    if n < 2:
        return math.nan, math.nan
    se = float(np.std(v, ddof=1)) / math.sqrt(n)
    h = float(sps.t.ppf(0.5 + level / 2.0, n - 1)) * se
    return m - h, m + h


def e3_analysis(rs: RowSet, boot: Bootstrap, K: int = 8, *,
                cells: Sequence[Cell] | None = None) -> dict:
    """E3: measured against the closed forms of MECHANISM_E_v2 Sections 3.6 and 3.9.

    Predicted values (units on the instance, K = 8):
      * ``R(pop_mpc)``  against ``prop_enum.closed_oblivious(K, q, c) = q (K - c/2)``;
      * ``R(pop_mpc) - R(oracle_mpc)`` against ``prop_enum.closed_gap(K, q, c)``;
      * at c = K, ``R(pop_mpc) - R(e1)`` against ``K q / 2 - E[R_e1]`` with
        ``E[R_e1] = prop_enum.closed_prop3_pooled(K, q, M)`` (exact binomial sum) for the
        pooled cap and ``prop_enum.closed_prop3_per_copy(K, q, M)`` (= K (q/2)(1 - f)) for
        the per-copy cap.

    Primary pass rule (ANALYSIS_SPEC 4): every predicted value lies inside its simultaneous
    95% interval, Bonferroni over all points (Student-t Monte Carlo intervals at level
    ``1 - 0.05 / m``; the bootstrap cannot resolve tails that far out). Also reported: the
    pointwise 95% bootstrap interval of every point, the pointwise misses, the count expected
    outside by chance and the upper-tail binomial p-value of the observed miss count.
    Refuses if any K-copy cell or required policy row is missing.
    """
    from scipy import stats as sps
    cells = list(KCOPY_CELLS if cells is None else cells)
    ids = [c.cell_id for c in cells]
    rs.require(ids, ("pop_mpc", REFERENCE))
    rs.require([c.cell_id for c in cells if int(round(c.c)) == K], (CANDIDATE,))
    rs.check_kinds(ids, ("pop_mpc", REFERENCE, CANDIDATE))
    seeds = rs.expected_seeds
    n = len(seeds)
    points = []
    for cell in cells:
        cid = cell.cell_id
        q = _frac(cell.q)
        c = int(round(cell.c))
        vectors = {"pop": rs.vec(cid, "pop_mpc", "R_abs_u", seeds),
                   "orc": rs.vec(cid, REFERENCE, "R_abs_u", seeds)}
        stats = {"R_pop": lambda m: m["pop"], "gap_oracle": lambda m: m["pop"] - m["orc"]}
        used_pols = ["pop_mpc", REFERENCE]
        series = {"R_pop": vectors["pop"], "gap_oracle": vectors["pop"] - vectors["orc"]}
        if c == K:
            vectors["e1"] = rs.vec(cid, CANDIDATE, "R_abs_u", seeds)
            stats["gap_e1"] = lambda m: m["pop"] - m["e1"]
            series["gap_e1"] = vectors["pop"] - vectors["e1"]
            used_pols.append(CANDIDATE)
        out = boot.run(vectors, stats)
        preds = {
            "R_pop": (float(prop_enum.closed_oblivious(K, q, c)), "prop_enum.closed_oblivious"),
            "gap_oracle": (float(prop_enum.closed_gap(K, q, c)), "prop_enum.closed_gap"),
        }
        if c == K:
            if cell.cap_mode == "pooled":
                ee = prop_enum.closed_prop3_pooled(K, q, cell.M)
                fn = "prop_enum.closed_prop3_pooled"
            else:
                ee = prop_enum.closed_prop3_per_copy(K, q, cell.M)
                fn = "prop_enum.closed_prop3_per_copy"
            preds["gap_e1"] = (float(Fraction(K) * q / 2 - ee), f"K q/2 - {fn}")
        for check, (pred, fn) in preds.items():
            st = out[check]
            se = float(np.std(series[check], ddof=1)) / math.sqrt(n) if n > 1 else math.nan
            points.append({
                "check": check, "cell_id": cid, "q": cell.q, "c": c, "M": cell.M,
                "cap_mode": cell.cap_mode, "K": K, "n_seeds": n, "measured": st,
                "predicted": pred, "function": fn,
                "pass_pointwise": bool(st.contains(pred, tol=TOL)),
                "mc_se": se, "series": series[check],
                "z": ((st.value - pred) / se) if se and se > 0 else
                (0.0 if abs(st.value - pred) < 1e-9 else math.inf),
                "seeds": seeds, "policies": used_pols})
    m = len(points)
    level = 1.0 - 0.05 / m if m else 0.95
    for p in points:
        lo, hi = t_interval(p.pop("series"), level)
        p["simultaneous_lo"], p["simultaneous_hi"] = lo, hi
        p["pass"] = bool(math.isfinite(lo) and lo - TOL <= p["predicted"] <= hi + TOL)
    fails = [p for p in points if not p["pass"]]
    misses = [p for p in points if not p["pass_pointwise"]]
    by_check = {}
    for p in points:
        d = by_check.setdefault(p["check"], {"points": 0, "pass": 0, "pass_pointwise": 0})
        d["points"] += 1
        d["pass"] += int(p["pass"])
        d["pass_pointwise"] += int(p["pass_pointwise"])
    p_binom = float(sps.binom.sf(len(misses) - 1, m, 0.05)) if m else math.nan
    return {"K": K, "points": points, "n_points": m, "n_pass": m - len(fails),
            "n_fail": len(fails), "failures": fails, "by_check": by_check,
            "all_pass": bool(m > 0 and not fails),
            "simultaneous_level": level,
            "n_pointwise_misses": len(misses), "pointwise_misses": misses,
            "expected_failures_by_chance": 0.05 * m, "binomial_p_upper": p_binom}


# ---------------------------------------------------------------------------------------
# descriptive tables and secondary endpoints
# ---------------------------------------------------------------------------------------
def cell_policy_table(rs: RowSet, boot: Bootstrap, cell_ids: Iterable[str],
                      metrics: Sequence[str] = DESCRIPTIVE_KEYS,
                      policies: Sequence[str] | None = None) -> dict:
    """Mean and interval of each metric for each (cell, policy) over the run's seeds."""
    table = {}
    seeds = rs.expected_seeds
    for cid in cell_ids:
        for p in rs.policies(cid):
            if policies is not None and p not in policies:
                continue
            have = [m for m in metrics if m in rs.metrics(cid, p)
                    and len(rs._vals[(cid, p)][m]) == len(seeds)]
            if not have:
                continue
            V = np.column_stack([rs.vec(cid, p, m, seeds) for m in have])
            table[(cid, p)] = {"seeds": seeds,
                               "stats": dict(zip(have, boot.mean_ci_matrix(V)))}
    return table


def floor_analysis(rs: RowSet, boot: Bootstrap, cell_ids: Iterable[str], frozen: dict) -> dict:
    """Net recovery gain of the floor beside its event shortfall; never summed.

    The best O is the frozen choice (floor excluded)."""
    out = {}
    seeds = rs.expected_seeds
    for cid in cell_ids:
        rs.require([cid], (FLOOR,))
        best = frozen_best(frozen, cid)["best"]
        rs.require([cid], (best,))
        res = boot.run(
            {"best": rs.vec(cid, best, R_KEY, seeds),
             "floor": rs.vec(cid, FLOOR, R_KEY, seeds),
             "short": rs.vec(cid, FLOOR, "event_shortfall_kwh_per100", seeds)},
            {"net_gain": lambda m: m["best"] - m["floor"], "event_shortfall": lambda m: m["short"]})
        out[cid] = {"best_oblivious": best, "seeds": seeds, **res}
    return out


def rwdf_analysis(rs: RowSet, boot: Bootstrap, cell_ids: Iterable[str]) -> dict:
    out = {}
    seeds = rs.expected_seeds
    for cid in cell_ids:
        rs.require([cid], ("rwdf_e", "rwdf_e_literal"))
        res = boot.run({"a": rs.vec(cid, "rwdf_e", R_KEY, seeds),
                        "b": rs.vec(cid, "rwdf_e_literal", R_KEY, seeds)},
                       {"rwdf_e": lambda m: m["a"], "rwdf_e_literal": lambda m: m["b"],
                        "literal_minus_rwdf_e": lambda m: m["b"] - m["a"]})
        out[cid] = {"seeds": seeds, **res}
    return out


def gap_vs_best(rs: RowSet, boot: Bootstrap, cell_id: str, frozen: dict, *,
                candidate: str = CANDIDATE, reference: str = REFERENCE) -> dict:
    """Gap of the frozen best O over the candidate (and the reference) at one cell."""
    best = frozen_best(frozen, cell_id)["best"]
    rs.require([cell_id], (best, candidate, reference))
    seeds = rs.expected_seeds
    vec = {"best": rs.vec(cell_id, best, R_KEY, seeds),
           "cand": rs.vec(cell_id, candidate, R_KEY, seeds),
           "orc": rs.vec(cell_id, reference, R_KEY, seeds)}
    stats = {"gap": lambda m: m["best"] - m["cand"], "R_best": lambda m: m["best"],
             "R_candidate": lambda m: m["cand"], "oracle_gap": lambda m: m["best"] - m["orc"]}
    return {"best_oblivious": best, "seeds": seeds, **boot.run(vec, stats)}


# ---------------------------------------------------------------------------------------
# G2
# ---------------------------------------------------------------------------------------
def g2_analysis(rs: RowSet, boot: Bootstrap, frozen: dict, *,
                candidate: str = CANDIDATE) -> dict:
    """Gate G2 at the pilot cell (delta_A = 2, rho = 0.95, M = 3).

    E1 is the Section 2 contrast at M = 3, rho = 0.95 (delta 2, 4 against delta 0, 1) with
    the frozen best O. There is no fallback: the pilot must hold all four delay cells, or
    this refuses. Gains are measured from ``sym_margin`` (OPEN_QUESTIONS row 51).
    """
    e1 = e1_analysis(rs, boot, 3, 0.95, selection="frozen", frozen=frozen)
    g2cell = f0r_cell_id(3, 2, 0.95)
    seeds = rs.expected_seeds
    stat = e1["contrast"]
    res: dict = {"cell_id": g2cell, "e1": e1, "seeds": seeds,
                 "decision_basis": "E1 contrast (delta 2, 4 against delta 0, 1) at M=3, rho=0.95",
                 "e1_stat": stat, "e1_label": reading_label(stat.lo, stat.hi),
                 "simple_rules_suffice": bool(math.isfinite(stat.hi) and stat.hi < THRESHOLD),
                 "gains": {}, "ratios": {}, "headline": {}}
    base = rs.vec(g2cell, "sym_margin", R_KEY, seeds)
    vec = {"cand": base - rs.vec(g2cell, candidate, R_KEY, seeds),
           "pop": base - rs.vec(g2cell, "pop_mpc", R_KEY, seeds),
           "pers": base - rs.vec(g2cell, "persistence", R_KEY, seeds)}
    stats = {"gain_candidate": lambda m: m["cand"], "gain_pop_mpc": lambda m: m["pop"],
             "gain_persistence": lambda m: m["pers"],
             "ratio_pop_mpc": lambda m: safe_ratio(m["pop"], m["cand"]),
             "ratio_persistence": lambda m: safe_ratio(m["pers"], m["cand"]),
             "diff_pop_mpc": lambda m: m["pop"] - HEADLINE_SHARE * m["cand"],
             "diff_persistence": lambda m: m["pers"] - HEADLINE_SHARE * m["cand"]}
    out = boot.run(vec, stats)
    res["gains"] = {"candidate": out["gain_candidate"], "pop_mpc": out["gain_pop_mpc"],
                    "persistence": out["gain_persistence"]}
    cand_pos = out["gain_candidate"].value > 0
    den_ok = bool(math.isfinite(out["gain_candidate"].lo) and out["gain_candidate"].lo > 0)
    for key in ("pop_mpc", "persistence"):
        r = out[f"ratio_{key}"]
        res["ratios"][key] = r if den_ok else Stat(r.value, math.nan, math.nan)
        d = out[f"diff_{key}"]
        res["headline"][key] = {
            "reaches_80pct_of_candidate_gain": bool(cand_pos and d.value >= -TOL),
            "ci_wholly_at_or_above_80pct": bool(cand_pos and math.isfinite(d.lo) and d.lo >= -TOL),
            "ratio_interval_defined": den_ok}
    res["candidate_gain_positive"] = bool(cand_pos)
    res["any_headline"] = any(v["reaches_80pct_of_candidate_gain"]
                              for v in res["headline"].values())
    return res


# ---------------------------------------------------------------------------------------
# the data file
# ---------------------------------------------------------------------------------------
class Numbers:
    """Collector of the data file's numbers (id -> record)."""

    def __init__(self) -> None:
        self.items: dict[str, dict] = {}

    def add(self, nid: str, stat: Stat | float | int, *, n_seeds: int | None, statistic: str,
            source: str, row_filter_: str, unit: str | None = None, **extra) -> None:
        if nid in self.items:
            raise AnalysisError(f"duplicate number id {nid!r}")
        if isinstance(stat, Stat):
            value, lo, hi = stat.value, stat.lo, stat.hi
        else:
            value, lo, hi = stat, None, None
        rec = {"value": value, "ci_lo": lo, "ci_hi": hi, "n_seeds": n_seeds,
               "statistic": statistic, "source_file": source, "row_filter": row_filter_,
               "label": LABEL}
        if unit:
            rec["unit"] = unit
        rec.update(extra)
        self.items[nid] = rec


def _jsonable(o):
    if isinstance(o, dict):
        return {str(k): _jsonable(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_jsonable(v) for v in o]
    if isinstance(o, Stat):
        return _jsonable({"value": o.value, "ci_lo": o.lo, "ci_hi": o.hi})
    if isinstance(o, (np.floating, float)):
        f = float(o)
        return f if math.isfinite(f) else None
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, np.bool_):
        return bool(o)
    return o


def git_info(root: Path = REPO_ROOT) -> dict:
    def run(*a):
        return subprocess.run(["git", "-C", str(root), *a], capture_output=True, text=True,
                              timeout=60)
    try:
        c = run("rev-parse", "HEAD")
        if c.returncode != 0:
            return {"commit": None, "dirty": None}
        s = run("status", "--porcelain", "--untracked-files=no")
        return {"commit": c.stdout.strip(), "dirty": bool(s.stdout.strip())}
    except (OSError, subprocess.SubprocessError):
        return {"commit": None, "dirty": None}


def input_record(rs: RowSet) -> dict:
    return {"path": rs.source, "sha256": rs.sha256, "rows": rs.n_rows, "rows_kept": rs.n_kept,
            "skipped": dict(rs.skipped), "duplicates": rs.duplicates,
            "partial_tail": rs.partial_tail, "missing": rs.missing,
            "study_family": rs.study, "seed_range": list(rs.seed_range)}


def _meta(inputs: dict[str, RowSet], boot: Bootstrap, warnings: list[str],
          files: dict | None = None) -> dict:
    return {"label": LABEL, "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "git": git_info(), "bootstrap": {"n_boot": boot.n_boot, "seed": boot.seed,
                                             "level": boot.level, "unit": "seed",
                                             "interval": "percentile"},
            "threshold_kwh_per100": THRESHOLD,
            "inputs": {k: input_record(v) for k, v in inputs.items()},
            "files": files or {},
            "warnings": warnings}


def _fmt_rho(rho: float) -> str:
    return f"{rho:g}"


def add_e1(nums: Numbers, rs: RowSet, e1: dict, tag: str) -> None:
    key = f"e1/{tag}/M{e1['M']}_rho{_fmt_rho(e1['rho'])}"
    seeds = e1["seeds"]
    cells = [e1["cells"][d] for d in e1["used"]]
    src = rs.source
    best = {str(d): e1["best"][d]["policy"] for d in e1["used"]}
    sel = SELECTION_NOTE[(e1["selection"], e1["include_floor"])]
    common = dict(n_seeds=len(seeds), source=src, selection=sel)
    pols = sorted({e1["best"][d]["policy"] for d in e1["used"]} | {CANDIDATE, REFERENCE})
    flt = row_filter(rs, cells, pols, seeds) if seeds else "no rows"
    for d, st in e1["gaps"].items():
        nums.add(f"{key}/gap_dA{d}", st, statistic="mean over seeds of R_avoid(best oblivious) "
                 "- R_avoid(guarded_mpc_e1)", row_filter_=flt, unit="kWh per 100 per event",
                 best_oblivious=best[str(d)], **common)
    for d, st in e1["oracle_gaps"].items():
        nums.add(f"{key}/oracle_gap_dA{d}", st, statistic="mean over seeds of R_avoid(best "
                 "oblivious) - R_avoid(oracle_mpc)", row_filter_=flt,
                 unit="kWh per 100 per event", best_oblivious=best[str(d)], **common)
    if e1["contrast"] is not None:
        nums.add(f"{key}/contrast", e1["contrast"],
                 statistic=f"E1: mean gap over delta {e1['hi_used']} minus mean gap over delta "
                           f"{e1['lo_used']}", row_filter_=flt, unit="kWh per 100 per event",
                 reading=e1["label"], best_oblivious=best, include_floor=e1["include_floor"],
                 **common)
    if e1["oracle_contrast"] is not None:
        nums.add(f"{key}/oracle_contrast", e1["oracle_contrast"],
                 statistic="E1 contrast with oracle_mpc in place of the candidate",
                 row_filter_=flt, unit="kWh per 100 per event", best_oblivious=best, **common)
        nums.add(f"{key}/oracle_share", e1["share"],
                 statistic="ratio of means: E1 contrast over the oracle contrast",
                 row_filter_=flt, unit="ratio", interval_defined=e1["share_defined"], **common)


def add_e2(nums: Numbers, rs: RowSet, e2: dict, e1: dict) -> None:
    key = f"e2/M{e2['M']}_rho{_fmt_rho(e2['rho'])}"
    seeds = e1["seeds"]
    src = rs.source

    def add_pack(pack: dict, suffix: str, cells: list[str], statistic_prefix: str) -> None:
        flt = row_filter(rs, cells, sorted({e1["best"][d]["policy"] for d in e1["used"]}
                                           | {CANDIDATE}), seeds)
        for tag, r in pack["readings"].items():
            for nm in ("gain_uncorr", "gain_corr", "diff"):
                nums.add(f"{key}/{suffix}/reading{tag}/{nm}", r[nm], n_seeds=len(seeds),
                         source=src, row_filter_=flt, unit="kWh per 100 per event",
                         statistic=f"{statistic_prefix}: paired {nm.replace('_', ' ')} "
                                   f"(best oblivious minus candidate), reading {tag}",
                         holds=r["holds"])
        nums.add(f"{key}/{suffix}/supported", 1.0 if pack["supported"] else 0.0,
                 n_seeds=len(seeds), source=src, row_filter_=flt, unit="flag",
                 statistic="prediction supported only if it holds under both readings",
                 supported=pack["supported"])

    for d, pack in e2["cells"].items():
        add_pack(pack, f"dA{d}", [e1["cells"][d]], "cell")
    if e2["contrast"] is not None:
        add_pack(e2["contrast"], "contrast", [e1["cells"][d] for d in e1["used"]], "contrast")


def add_e3(nums: Numbers, rs: RowSet, e3: dict) -> None:
    src = rs.source
    for p in e3["points"]:
        nid = (f"e3/{p['check']}/{p['cap_mode']}/q{p['q']:g}/c{p['c']}/M{p['M']}")
        nums.add(nid, p["measured"], n_seeds=p["n_seeds"], source=src,
                 statistic={"R_pop": "mean R_abs_u of pop_mpc against q (K - c/2)",
                            "gap_oracle": "mean R_abs_u(pop_mpc) - R_abs_u(oracle_mpc) against gap(c)",
                            "gap_e1": "mean R_abs_u(pop_mpc) - R_abs_u(guarded_mpc_e1) against "
                                      "K q/2 - E[R_e1] (Proposition 3)"}[p["check"]],
                 row_filter_=row_filter(rs, p["cell_id"], p["policies"], p["seeds"]),
                 unit="units on the instance (1 unit = 0.25 kWh)", predicted=p["predicted"],
                 predicted_by=p["function"], passed=p["pass"],
                 passed_pointwise=p["pass_pointwise"], mc_se=p["mc_se"], K=p["K"],
                 simultaneous_lo=p["simultaneous_lo"], simultaneous_hi=p["simultaneous_hi"],
                 simultaneous_level=e3["simultaneous_level"])
    n_seeds = max((p["n_seeds"] for p in e3["points"]), default=0)
    for nm, v in (("n_points", e3["n_points"]), ("n_pass", e3["n_pass"]),
                  ("n_fail", e3["n_fail"]), ("n_pointwise_misses", e3["n_pointwise_misses"]),
                  ("expected_failures_by_chance", e3["expected_failures_by_chance"]),
                  ("binomial_p_upper", e3["binomial_p_upper"])):
        nums.add(f"e3/summary/{nm}", v, n_seeds=n_seeds, source=src,
                 statistic=("E3 " + nm.replace("_", " ") + ("; primary rule is the simultaneous (Bonferroni) "
                                                    "95% interval" if nm in ("n_pass", "n_fail") else "")), row_filter_="all K-copy points",
                 unit="count")
    for chk, d in e3["by_check"].items():
        nums.add(f"e3/summary/{chk}/n_pass", d["pass"], n_seeds=n_seeds, source=src,
                 statistic=f"E3 points inside the simultaneous interval for {chk} of {d['points']}",
                 row_filter_="all K-copy points", unit="count", points=d["points"],
                 pass_pointwise=d["pass_pointwise"])


SELECTION_NOTE = {
    ("frozen", False): "primary: best O fixed on the tuning seeds (lowest frozen tuning "
                       "objective in TUNING_FROZEN.json, floor excluded)",
    ("frozen", True): "sensitivity: as the primary but the floor may be chosen",
    ("min_e1", False): "sensitivity: the single O member that minimizes E1 itself on the "
                       "development seeds (conservative lower reading)",
}
E1_VARIANTS = (("primary", dict(selection="frozen", include_floor=False)),
               ("sensitivity_floor", dict(selection="frozen", include_floor=True)),
               ("sensitivity_min_e1", dict(selection="min_e1", include_floor=False)))
F0R_POLICIES = (*OBLIVIOUS, FLOOR, CANDIDATE, REFERENCE, *PER_PARTICIPANT, BOUND)
G2_POLICIES = (*OBLIVIOUS, CANDIDATE, REFERENCE)


def _frozen_record(path: Path | str) -> dict:
    return {"path": str(path), "sha256": file_sha256(path)}


def _check_f0r(rs: RowSet, cell_ids: Sequence[str], policies: Sequence[str]) -> None:
    rs.require(cell_ids, policies)
    rs.check_kinds(cell_ids, policies)


LAYERS_LABEL = ("descriptive, post hoc, added after DEV_REPORT_E; factorial pre-declared as "
                "secondary in FORMULATION_E_v2 8.2")
LAYER_POLICIES = ("ce_llf", "mpc_ce", "pop_mpc", CANDIDATE, REFERENCE)
LAYER_TERMS = ("planning", "hedging", "targeting", "oracle_targeting", "total")
LAYER_METRICS = {"": R_KEY, "deadline_misses/": "deadline_miss_count_per100"}
MSWEEP_MS = (1, 3, 5)
IDENTITY_TOL = 1e-9


def check_layer_identity(terms: dict[str, np.ndarray], where: str) -> None:
    """planning + hedging + targeting == total, per seed, up to 1e-9; else refuse."""
    err = np.abs(terms["planning"] + terms["hedging"] + terms["targeting"] - terms["total"])
    if not (err <= IDENTITY_TOL).all():
        raise AnalysisError(f"layers: planning + hedging + targeting != total on {where} "
                            f"(max per-seed error {float(err.max()):.3g})")


def layers_analysis(rs: RowSet, boot: Bootstrap) -> dict:
    """Descriptive post hoc belief-by-rule factorial over the 16 primary cells.

    planning = ce_llf - mpc_ce; hedging = mpc_ce - pop_mpc; targeting = pop_mpc - e1;
    oracle_targeting = pop_mpc - oracle_mpc; total = ce_llf - e1, all on the same seeds, for
    R_avoid and for deadline misses per 100. Refuses on missing rows or if the per-seed sum
    identity fails. Also the M-sweep recovery share at delta 2, rho 0.95, r 0.3.
    """
    seeds = rs.expected_seeds
    out: dict = {"cells": {}, "msweep": {}}
    for M in (0, 3):
        for rho in (0.95, 1.15):
            for d in (0, 1, 2, 4):
                cid = f0r_cell_id(M, d, rho)
                rs.require([cid], LAYER_POLICIES)
                rec = {"cell_id": cid, "seeds": seeds}
                for prefix, metric in LAYER_METRICS.items():
                    v = {p: rs.vec(cid, p, metric, seeds) for p in LAYER_POLICIES}
                    terms = {"planning": v["ce_llf"] - v["mpc_ce"],
                             "hedging": v["mpc_ce"] - v["pop_mpc"],
                             "targeting": v["pop_mpc"] - v[CANDIDATE],
                             "oracle_targeting": v["pop_mpc"] - v[REFERENCE],
                             "total": v["ce_llf"] - v[CANDIDATE]}
                    check_layer_identity(terms, f"{cid} ({metric})")
                    res = boot.run(terms, {k: (lambda m, k=k: m[k]) for k in LAYER_TERMS})
                    rec.update({f"{prefix}{k}": res[k] for k in LAYER_TERMS})
                out["cells"][(M, rho, d)] = rec
    for m in MSWEEP_MS:
        cid = f0r_cell_id(m, 2, 0.95)
        rs.require([cid], ("pop_mpc", CANDIDATE, REFERENCE))
        pop, e1, orc = (rs.vec(cid, p, R_KEY, seeds) for p in ("pop_mpc", CANDIDATE, REFERENCE))
        res = boot.run({"num": pop - e1, "den": pop - orc},
                       {"numerator": lambda x: x["num"], "denominator": lambda x: x["den"],
                        "share": lambda x: safe_ratio(x["num"], x["den"])})
        den = res["denominator"]
        defined = bool(math.isfinite(den.lo) and (den.lo > 0 or den.hi < 0))
        share = res["share"]
        out["msweep"][m] = {"cell_id": cid, "seeds": seeds, "numerator": res["numerator"],
                            "denominator": den, "interval_defined": defined,
                            "share": share if defined else Stat(share.value, math.nan, math.nan)}
    return out


def add_layers(nums: Numbers, rs: RowSet, layers: dict) -> None:
    stat_text = {
        "planning": "mean {k}(ce_llf) - {k}(mpc_ce)", "hedging": "mean {k}(mpc_ce) - {k}(pop_mpc)",
        "targeting": "mean {k}(pop_mpc) - {k}(guarded_mpc_e1)",
        "oracle_targeting": "mean {k}(pop_mpc) - {k}(oracle_mpc)",
        "total": "mean {k}(ce_llf) - {k}(guarded_mpc_e1)"}
    pairs = {"planning": ("ce_llf", "mpc_ce"), "hedging": ("mpc_ce", "pop_mpc"),
             "targeting": ("pop_mpc", CANDIDATE), "oracle_targeting": ("pop_mpc", REFERENCE),
             "total": ("ce_llf", CANDIDATE)}
    for (M, rho, d), r in layers["cells"].items():
        key = f"layers/M{M}_rho{_fmt_rho(rho)}/dA{d}"
        common = dict(n_seeds=len(r["seeds"]), source=rs.source, layer_label=LAYERS_LABEL)
        for prefix, metric in LAYER_METRICS.items():
            for k in LAYER_TERMS:
                nums.add(f"{key}/{prefix}{k}", r[f"{prefix}{k}"],
                         statistic=stat_text[k].format(k=metric),
                         row_filter_=row_filter(rs, r["cell_id"], pairs[k], r["seeds"]),
                         unit=("kWh per 100 per event" if not prefix
                               else "misses per 100 per event"), **common)
    for m, r in layers["msweep"].items():
        key = f"layers/msweep/M{m}"
        common = dict(n_seeds=len(r["seeds"]), source=rs.source, layer_label=LAYERS_LABEL)
        flt = row_filter(rs, r["cell_id"], ("pop_mpc", CANDIDATE, REFERENCE), r["seeds"])
        nums.add(f"{key}/numerator", r["numerator"], row_filter_=flt,
                 statistic="mean R_avoid(pop_mpc) - R_avoid(guarded_mpc_e1)",
                 unit="kWh per 100 per event", **common)
        nums.add(f"{key}/denominator", r["denominator"], row_filter_=flt,
                 statistic="mean R_avoid(pop_mpc) - R_avoid(oracle_mpc)",
                 unit="kWh per 100 per event", **common)
        extra = {} if r["interval_defined"] else {
            "note": "interval withheld: the denominator's interval includes 0"}
        nums.add(f"{key}/share", r["share"], row_filter_=flt, unit="ratio",
                 statistic="ratio of means numerator / denominator, jointly resampled",
                 interval_defined=r["interval_defined"], **extra, **common)


def build_paper_numbers(f0r: Path | str | None, kcopy: Path | str | None,
                        scale: Path | str | None, frozen_path: Path | str | None, *,
                        boot: Bootstrap | None = None, ranges: dict | None = None,
                        f0r_cells: Sequence[Cell] | None = None,
                        kcopy_cells: Sequence[Cell] | None = None,
                        scale_cells: Sequence[Cell] | None = None) -> dict:
    """Compute everything and return the data-file dict (not yet written).

    Refuses (``AnalysisError``) on any missing input, cell, policy or seed (ANALYSIS_SPEC 4b).
    The ``ranges`` and ``*_cells`` arguments exist for tests; the defaults are the run plan.
    """
    boot = boot or Bootstrap()
    rng = {**RUN_RANGES, **(ranges or {})}
    f0r_cells = list(F0R_CELLS if f0r_cells is None else f0r_cells)
    kcopy_cells = list(KCOPY_CELLS if kcopy_cells is None else kcopy_cells)
    scale_cells = list(scale_cell(c) for c in F0R_CELLS if c.delta_A in SCALE_DELTA_A) \
        if scale_cells is None else list(scale_cells)
    frozen = load_frozen_file(frozen_path)
    rs_f = load_rows(f0r, "F0R", seed_range=rng["f0r"], keep=E1_KEEP)
    rs_k = load_rows(kcopy, "KCOPY", seed_range=rng["kcopy"], keep=E3_KEEP,
                     policies=E3_POLICIES)
    rs_s = load_rows(scale, "SCALE", seed_range=rng["scale"], keep=SCALE_KEEP)
    inputs = {"f0r": rs_f, "kcopy": rs_k, "scale": rs_s}
    # completeness and kinds first: nothing is computed on a partial input
    f_ids = [c.cell_id for c in f0r_cells]
    _check_f0r(rs_f, f_ids, F0R_POLICIES)
    _check_f0r(rs_s, [c.cell_id for c in scale_cells], F0R_POLICIES)
    rs_k.require([c.cell_id for c in kcopy_cells], ("pop_mpc", REFERENCE))
    rs_k.require([c.cell_id for c in kcopy_cells if int(round(c.c)) == 8], (CANDIDATE,))
    warnings: list[str] = []
    for k, rs in inputs.items():
        if rs.partial_tail:
            warnings.append(f"input {k}: trailing partial line ignored")
        if rs.duplicates:
            warnings.append(f"input {k}: {rs.duplicates} duplicate rows ignored")
    nums = Numbers()
    sections: dict = {"e1": {}, "e2": {}, "e3": None, "secondary": {}}

    for tag, kw in E1_VARIANTS:
        for M in (0, 3):
            for rho in (0.95, 1.15):
                e1 = e1_analysis(rs_f, boot, M, rho, frozen=frozen, **kw)
                add_e1(nums, rs_f, e1, tag)
                sections["e1"][f"{tag}/M{M}_rho{_fmt_rho(rho)}"] = e1
                if tag == "primary":
                    e2 = e2_analysis(rs_f, boot, e1)
                    add_e2(nums, rs_f, e2, e1)
                    sections["e2"][f"M{M}_rho{_fmt_rho(rho)}"] = e2
    g2f = g2_analysis(rs_f, boot, frozen)        # full development set, not the pilot
    add_g2(nums, rs_f, g2f, "g2_full", None, G2_FULL_NOTE)
    sections["g2_full"] = g2f
    layers = layers_analysis(rs_f, boot)
    add_layers(nums, rs_f, layers)
    sections["layers"] = layers
    table = cell_policy_table(rs_f, boot, rs_f.cells())
    for (cid, pol), t in table.items():
        for m, st in t["stats"].items():
            nums.add(f"cell/{cid}/{pol}/{m}", st, n_seeds=len(t["seeds"]), source=rs_f.source,
                     statistic=f"mean of {m}",
                     row_filter_=row_filter(rs_f, cid, pol, t["seeds"]),
                     unit=("kWh per 100 per event" if m.endswith("kwh_per100") else None))
    fl = floor_analysis(rs_f, boot, f_ids, frozen)
    for cid, d in fl.items():
        flt = row_filter(rs_f, cid, [d["best_oblivious"], FLOOR], d["seeds"])
        nums.add(f"secondary/floor/{cid}/net_recovery_gain", d["net_gain"],
                 n_seeds=len(d["seeds"]), source=rs_f.source, row_filter_=flt,
                 statistic="mean R_avoid(best oblivious) - R_avoid(floor); beside, never "
                           "summed with, the event shortfall", unit="kWh per 100 per event",
                 best_oblivious=d["best_oblivious"])
        nums.add(f"secondary/floor/{cid}/event_shortfall", d["event_shortfall"],
                 n_seeds=len(d["seeds"]), source=rs_f.source, row_filter_=flt,
                 statistic="mean event_shortfall_kwh_per100 of the floor",
                 unit="kWh per 100 per event")
    sections["secondary"]["floor"] = fl

    def add_gap(prefix: str, cid: str, g: dict, what: str) -> None:
        flt = row_filter(rs_f, cid, [g["best_oblivious"], CANDIDATE, REFERENCE], g["seeds"])
        for nm, who in (("gap", "candidate"), ("oracle_gap", "oracle")):
            nums.add(f"{prefix}/{nm}", g[nm], n_seeds=len(g["seeds"]), source=rs_f.source,
                     row_filter_=flt, unit="kWh per 100 per event",
                     statistic=f"{what}: mean R_avoid(best oblivious) - R_avoid({who})",
                     best_oblivious=g["best_oblivious"])

    sweep = {}
    for r in (0.0, 0.3, 1.0):
        cid = f0r_cell_id(3, 2, 0.95, r=r)
        if cid in f_ids:
            sweep[r] = gap_vs_best(rs_f, boot, cid, frozen)
            add_gap(f"secondary/r_sweep/r{r:g}", cid, sweep[r], f"return probability r={r:g}")
    sections["secondary"]["r_sweep"] = sweep
    lag_id = Cell(family="F0R", M=3, delta_A=0, delta_b=2, rho=0.95, r=0.3).cell_id
    if lag_id in f_ids:
        lg = gap_vs_best(rs_f, boot, lag_id, frozen)
        add_gap("secondary/lag_split", lag_id, lg, "lag-split cell (delta_A=0, delta_b=2)")
        sections["secondary"]["lag_split"] = lg
    rw = rwdf_analysis(rs_f, boot, f_ids)
    for cid, d in rw.items():
        flt = row_filter(rs_f, cid, ["rwdf_e", "rwdf_e_literal"], d["seeds"])
        for nm in ("rwdf_e", "rwdf_e_literal", "literal_minus_rwdf_e"):
            nums.add(f"secondary/rwdf/{cid}/{nm}", d[nm], n_seeds=len(d["seeds"]),
                     source=rs_f.source, row_filter_=flt, unit="kWh per 100 per event",
                     statistic=f"mean R_avoid: {nm}")
    sections["secondary"]["rwdf"] = rw

    e3 = e3_analysis(rs_k, boot, 8, cells=kcopy_cells)
    add_e3(nums, rs_k, e3)
    sections["e3"] = e3
    ns = {rs_k.n_of(c, p) for (c, p) in rs_k._vals if p == "pop_mpc"}
    if ns - {None, 24}:
        warnings.append(f"E3 assumes K = 8 (N = 24); rows have N in {sorted(ns - {None})}")

    tbl = cell_policy_table(rs_s, boot, rs_s.cells(), metrics=SCALE_KEEP[:-1])
    for (cid, pol), t in tbl.items():
        for m, st in t["stats"].items():
            nums.add(f"scale/{cid}/{pol}/{m}", st, n_seeds=len(t["seeds"]),
                     source=rs_s.source, statistic=f"mean of {m} at N = 300",
                     row_filter_=row_filter(rs_s, cid, pol, t["seeds"]),
                     unit="ms" if m.startswith(("cpu", "wall")) else "kWh per 100 per event")
    return {"meta": _meta(inputs, boot, warnings, {"tuning_frozen": _frozen_record(frozen_path)}),
            "numbers": nums.items, "_sections": sections}


G2_FULL_NOTE = ("G2 quantities at full development size (not the gate itself, which used "
                "the pilot)")


def add_g2(nums: Numbers, rs: RowSet, g: dict, prefix: str, e1_tag: str | None,
           note: str) -> None:
    """The G2 numbers: E1 at the stratum, gains over sym_margin, ratios and the 80% flags."""
    if e1_tag:
        add_e1(nums, rs, g["e1"], e1_tag)
    seeds = g["seeds"]
    extra = {"g2_note": note} if note else {}
    flt = row_filter(rs, g["cell_id"], ["sym_margin", CANDIDATE, "pop_mpc", "persistence"], seeds)
    for nm, st in g["gains"].items():
        nums.add(f"{prefix}/gain/{nm}", st, n_seeds=len(seeds), source=rs.source, row_filter_=flt,
                 statistic=f"mean R_avoid(sym_margin) - R_avoid({nm}) at the G2 cell",
                 unit="kWh per 100 per event", **extra)
    for nm, st in g["ratios"].items():
        h = g["headline"][nm]
        nums.add(f"{prefix}/ratio/{nm}", st, n_seeds=len(seeds), source=rs.source,
                 row_filter_=flt, statistic=f"ratio of mean gains: {nm} over candidate",
                 unit="ratio", interval_defined=h["ratio_interval_defined"],
                 reaches_80pct=h["reaches_80pct_of_candidate_gain"],
                 ci_wholly_at_or_above_80pct=h["ci_wholly_at_or_above_80pct"], **extra)
    for nm, h in g["headline"].items():
        for fl in ("reaches_80pct_of_candidate_gain", "ci_wholly_at_or_above_80pct"):
            nums.add(f"{prefix}/flag/{nm}/{fl}", 1.0 if h[fl] else 0.0, n_seeds=len(seeds),
                     source=rs.source, row_filter_=flt, unit="flag", flag=bool(h[fl]),
                     statistic=f"{fl} for {nm}", **extra)
    stat = g["e1_stat"]
    nums.add(f"{prefix}/e1_stat", stat, n_seeds=len(seeds), source=rs.source, row_filter_=flt,
             statistic="E1 contrast at the G2 stratum (M=3, rho=0.95)", unit="kWh per 100 per event",
             reading=g["e1_label"], simple_rules_suffice=g["simple_rules_suffice"], **extra)


def build_g2_numbers(pilot: Path | str | None, frozen_path: Path | str | None, *,
                     boot: Bootstrap | None = None, ranges: dict | None = None) -> dict:
    """G2 numbers and flags. Refuses unless the pilot holds the M = 3, rho = 0.95 cells."""
    boot = boot or Bootstrap()
    rng = {**RUN_RANGES, **(ranges or {})}
    frozen = load_frozen_file(frozen_path)
    rs = load_rows(pilot, "F0R", seed_range=rng["pilot"], keep=E1_KEEP)
    cells = [f0r_cell_id(3, d, 0.95) for d in (0, 1, 2, 4)]
    _check_f0r(rs, cells, G2_POLICIES)
    nums = Numbers()
    warnings: list[str] = []
    if rs.partial_tail:
        warnings.append("pilot: trailing partial line ignored")
    if rs.duplicates:
        warnings.append(f"pilot: {rs.duplicates} duplicate rows ignored")
    g = g2_analysis(rs, boot, frozen)
    add_g2(nums, rs, g, "g2", "g2", "")
    stat = g["e1_stat"]
    flags = {"simple_rules_suffice": g["simple_rules_suffice"],
             "any_headline_80pct": g["any_headline"],
             "headline_pop_mpc": g["headline"]["pop_mpc"]["reaches_80pct_of_candidate_gain"],
             "headline_persistence": g["headline"]["persistence"]["reaches_80pct_of_candidate_gain"],
             "e1_reading": g["e1_label"], "decision_basis": g["decision_basis"],
             "e1": {"value": stat.value, "ci_lo": stat.lo, "ci_hi": stat.hi},
             "candidate_gain_positive": g["candidate_gain_positive"]}
    return {"meta": _meta({"pilot": rs}, boot, warnings, {"tuning_frozen": _frozen_record(frozen_path)}),
            "numbers": nums.items, "flags": flags, "_sections": {"g2": g}}


def write_json(obj: dict, path: Path | str) -> None:
    obj = {k: v for k, v in obj.items() if not k.startswith("_")}
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(p.name + ".tmp")
    with open(tmp, "w") as f:
        json.dump(_jsonable(obj), f, indent=1, allow_nan=False)
        f.write("\n")
    tmp.replace(p)


# ---------------------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="python -m papere.analysis", description=__doc__.split("\n")[0])
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--all", action="store_true",
                   help="write results/paper_numbers.json from the F0R, K-copy and SCALE rows")
    g.add_argument("--g2", metavar="PILOT_DIR",
                   help="write results/g2_numbers.json from the pilot rows")
    p.add_argument("--f0r", default=DEFAULT_DIRS["f0r"], help="F0R development rows dir")
    p.add_argument("--kcopy", default=DEFAULT_DIRS["kcopy"], help="K-copy rows dir")
    p.add_argument("--scale", default=DEFAULT_DIRS["scale"], help="SCALE rows dir")
    p.add_argument("--frozen", default=DEFAULT_FROZEN, help="TUNING_FROZEN.json (required)")
    p.add_argument("--out", default=None, help="output path (default by mode, under the repo)")
    p.add_argument("--n-boot", type=int, default=N_BOOT)
    p.add_argument("--boot-seed", type=int, default=BOOT_SEED)
    p.add_argument("--strict", action="store_true",
                   help="exit 2 and write nothing if any warning was raised")
    return p


def _resolve(p: str) -> Path:
    q = Path(p)
    return q if q.is_absolute() or q.exists() else REPO_ROOT / q


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    boot = Bootstrap(args.n_boot, args.boot_seed)
    try:
        frozen = _resolve(args.frozen)
        if args.all:
            data = build_paper_numbers(_resolve(args.f0r), _resolve(args.kcopy),
                                       _resolve(args.scale), frozen, boot=boot)
            out = Path(args.out) if args.out else REPO_ROOT / DEFAULT_PAPER_NUMBERS
        else:
            data = build_g2_numbers(_resolve(args.g2), frozen, boot=boot)
            out = Path(args.out) if args.out else REPO_ROOT / DEFAULT_G2_NUMBERS
    except AnalysisError as e:
        print(f"[analysis] refused: {e}", file=sys.stderr)
        return 2
    warns = data["meta"]["warnings"]
    for w in warns:
        print(f"[analysis] warning: {w}", file=sys.stderr)
    if args.strict and warns:
        print("[analysis] --strict: warnings raised, nothing written", file=sys.stderr)
        return 2
    write_json(data, out)
    print(f"[analysis] wrote {len(data['numbers'])} numbers to {out}")
    if args.g2:
        print(f"[analysis] G2 flags: {json.dumps(_jsonable(data['flags']))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
