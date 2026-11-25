"""Study runner (CLOUD_BUILD_PROMPT RUNNER and RUN ORDER; POLICY_SPEC Sections 5 and 7).

What it does
------------
* ``run``: simulate every selected (seed, cell) with every selected policy and append one
  JSONL row per (seed, cell, policy[, config]) to ``<out>/rows.jsonl``.
* ``freeze``: select the per-cell configuration of every tunable family from complete
  tuning rows and write ``results/TUNING_FROZEN.json``.

Modes
-----
``tune``    F0R only, seeds 60000-60049 only. Every grid configuration of every tunable
            family (nothing else) on every F0-R cell. The policy name given to
            ``simulate`` is ``<family>@c<index>`` so tie-break streams differ per config.
``frozen``  Each selected family runs its frozen configuration (F0R, SCALE: from
            TUNING_FROZEN.json, required; KCOPY: the family default), families with
            ``tuned_from`` use the referenced family's configuration, plus the clairvoyant
            bound row on the unfloored availability (family and kind ``bound``).

Row file
--------
The parent process is the only writer. Each row is one complete line written with
``os.write`` on an ``O_APPEND`` descriptor followed by ``fsync``. On load a trailing partial
line (no newline) is reported and truncated. Rows already present, by key
``(study family, seed, cell_id, policy)``, are skipped, so a run is resumable and
idempotent; an existing row whose config differs from the current selection is a refusal.
Only the key set is held in memory. Every row carries the sha256 of the population
parameters; frozen runs need those and TUNING_FROZEN.json committed (``allow_dirty`` aside). Rows keep the ledger's keys except that the ledger's ``family`` (F0R, KCOPY,
SCALE) is renamed ``study_family`` and ``family`` is the policy family.

Determinism
-----------
A task is one (seed, cell). A task's result depends on (seed, cell, policy name, config)
only, and the file order follows task order (ordered ``imap``), so the worker count changes
nothing but the timing fields (``TIMING_KEYS``).

Seed refusal
------------
See ``check_seeds``. The ledger's open ranges are constants in ``OPEN_RANGES``; the
``open_ranges`` parameter of ``run`` and ``freeze`` exists for tests only and the CLI
never sets it. Seeds 500000-500999 are refused unless ``<repo root>/CONFIRMATION_APPROVED``
holds a line that is exactly ``run``.
"""
from __future__ import annotations

import argparse
import dataclasses
import fcntl
import hashlib
import json
import math
import multiprocessing as mp
import os
import platform
import re
import subprocess
import sys
import time
from dataclasses import dataclass, replace
from fractions import Fraction
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from .generator import F0R_CELLS, KCOPY_CELLS, generate_f0r, generate_kcopy, scale_cell
from .instance import Cell
from .ledger import a_sha256, bound_row, clair_for, evaluate
from .policies.base import Family, PopulationParams
from .sim import simulate

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PARAMS_PATH = REPO_ROOT / "results" / "population_params.json"
DEFAULT_FROZEN_PATH = REPO_ROOT / "results" / "TUNING_FROZEN.json"
ROWS_NAME = "rows.jsonl"
CONFIRMATION_FILE = "CONFIRMATION_APPROVED"
CONFIRMATION_WORD = "run"
CONFIRMATION_RANGE = (500000, 500999)

# SEED_LEDGER open ranges, by (study family, mode). Everything else is refused.
OPEN_RANGES: dict[tuple[str, str], tuple[int, int]] = {
    ("F0R", "tune"): (60000, 60049),
    ("F0R", "frozen"): (61000, 61099),
    ("KCOPY", "frozen"): (61500, 61599),
    ("SCALE", "frozen"): (63000, 63019),
}
TUNE_RANGE = OPEN_RANGES[("F0R", "tune")]

SCALE_DELTA_A = (0, 2)          # FORMULATION_E_v2 Section 5.3
TIMING_KEYS = ("wall_ms", "cpu_ms_total", "cpu_ms_mean", "cpu_ms_p95", "cpu_ms_max",
               "cpu_mean_ms", "cpu_max_ms")
OBJECTIVE_KEY = "R_avoid_kwh_per100"
TIEBREAK_KEY = "violation_kwslot"


class RunnerError(Exception):
    """Any refusal or inconsistency; the CLI prints it and exits with status 2."""


class SeedRefused(RunnerError):
    """A seed outside the ledger's open ranges, or a closed confirmation range."""


# ---------------------------------------------------------------------------------------
# seeds
# ---------------------------------------------------------------------------------------
def parse_seeds(spec: str) -> tuple[int, int]:
    m = re.fullmatch(r"\s*(\d+)\s*(?:-\s*(\d+)\s*)?", str(spec))
    if not m:
        raise RunnerError(f"bad --seeds {spec!r}; expected A-B or A")
    lo = int(m.group(1))
    hi = int(m.group(2)) if m.group(2) is not None else lo
    if hi < lo:
        raise RunnerError(f"bad --seeds {spec!r}: B < A")
    return lo, hi


def confirmation_approved(repo_root: Path | str) -> bool:
    """True iff ``CONFIRMATION_APPROVED`` exists at ``repo_root`` and holds exactly the line
    ``run`` (Varma's typed approval); only a trailing newline is stripped."""
    p = Path(repo_root) / CONFIRMATION_FILE
    try:
        text = p.read_bytes().decode("utf-8")      # bytes: no newline translation
    except (OSError, UnicodeDecodeError):
        return False
    if text.endswith("\n"):
        text = text[:-1]
    return text == CONFIRMATION_WORD


def check_seeds(family: str, mode: str, lo: int, hi: int, *,
                repo_root: Path | str = REPO_ROOT, open_ranges: dict | None = None) -> None:
    """Raise ``SeedRefused`` unless seeds ``lo..hi`` may be run for (family, mode)."""
    clo, chi = CONFIRMATION_RANGE
    if lo <= chi and hi >= clo:                     # any overlap with the closed range
        if not confirmation_approved(repo_root):
            raise SeedRefused(
                f"seeds {lo}-{hi} overlap the reserved confirmation range {clo}-{chi}, "
                f"CLOSED until Varma types '{CONFIRMATION_WORD}' "
                f"(no approved {CONFIRMATION_FILE} at {Path(repo_root)})")
        if not (clo <= lo and hi <= chi):
            raise SeedRefused("a confirmation run must lie entirely inside "
                              f"{clo}-{chi}; got {lo}-{hi}")
        if mode != "frozen":
            raise SeedRefused("confirmation seeds are for frozen mode only")
        return
    ranges = OPEN_RANGES if open_ranges is None else open_ranges
    rng = ranges.get((family, mode))
    if rng is None:
        raise SeedRefused(f"no open seed range for family {family} in mode {mode}")
    if not (rng[0] <= lo and hi <= rng[1]):
        raise SeedRefused(f"seeds {lo}-{hi} are outside the open range {rng[0]}-{rng[1]} "
                          f"for {family} {mode}")


# ---------------------------------------------------------------------------------------
# row store
# ---------------------------------------------------------------------------------------
def row_key(row: dict) -> tuple:
    """Dedupe key: (study family, seed, cell, policy name). Tune policy names carry the
    config index, so tune rows are distinct per config; frozen rows are one per policy."""
    return (row["study_family"], int(row["seed"]), row["cell_id"], row["policy"])


def cfg_hash(cfg) -> str:
    return hashlib.sha256(json.dumps(cfg, sort_keys=True, default=_jsonable)
                          .encode()).hexdigest()[:16]


def _jsonable(o):
    if isinstance(o, np.generic):
        return o.item()
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, (set, frozenset)):
        return sorted(o)
    raise TypeError(f"not JSON serialisable: {type(o).__name__}")


def _dumps(obj) -> str:
    return json.dumps(obj, default=_jsonable, separators=(",", ":"), allow_nan=True)


def iter_rows(path: Path | str):
    """Stream the complete rows of a JSONL file (a trailing partial line is ignored)."""
    p = Path(path)
    if not p.exists():
        return
    with open(p, "rb") as f:
        for line in f:
            if not line.endswith(b"\n"):
                return
            yield json.loads(line)


class RowStore:
    """Append-only JSONL file with durable single-write appends and partial-line recovery.

    Only the key set (key -> short hash of the row's config) and row counters are kept in
    memory, never the rows themselves.
    """

    def __init__(self, path: Path):
        self.path = Path(path)
        self.keys: dict[tuple, str] = {}
        self.by_mode: dict[str, int] = {}
        self.by_family: dict[str, int] = {}
        self.recovered_bytes = 0
        self._fd: int | None = None

    def __len__(self) -> int:
        return len(self.keys)

    def _note(self, row: dict, k: tuple) -> None:
        self.keys[k] = cfg_hash(row.get("config"))
        self.by_mode[row["mode"]] = self.by_mode.get(row["mode"], 0) + 1
        self.by_family[row["family"]] = self.by_family.get(row["family"], 0) + 1

    def load(self, *, truncate: bool = True, quiet: bool = False) -> "RowStore":
        self.keys, self.by_mode, self.by_family, self.recovered_bytes = {}, {}, {}, 0
        if not self.path.exists():
            return self
        offset = 0
        with open(self.path, "rb") as f:
            for n, line in enumerate(f, 1):
                if not line.endswith(b"\n"):
                    self.recovered_bytes = len(line)
                    break
                try:
                    row = json.loads(line)
                    k = row_key(row)
                except (ValueError, KeyError, TypeError) as e:
                    raise RunnerError(f"{self.path}: corrupt row at line {n}: {e}") from None
                if k in self.keys:
                    raise RunnerError(f"{self.path}: duplicate row key {k} at line {n}")
                self._note(row, k)
                offset += len(line)
        if self.recovered_bytes:
            if not truncate:
                raise RunnerError(f"{self.path}: trailing partial line "
                                  f"({self.recovered_bytes} bytes); rerun the study "
                                  "command once to recover it")
            if not quiet:
                print(f"[runner] {self.path}: trailing partial line of "
                      f"{self.recovered_bytes} bytes detected, truncating", file=sys.stderr)
            fd = os.open(self.path, os.O_WRONLY)
            try:
                os.ftruncate(fd, offset)
                os.fsync(fd)
            finally:
                os.close(fd)
        return self

    def open(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._fd = os.open(self.path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o644)

    def append(self, row: dict) -> None:
        k = row_key(row)
        if k in self.keys:
            raise RunnerError(f"refusing to write duplicate row {k}")
        buf = memoryview((_dumps(row) + "\n").encode("utf-8"))
        while len(buf):
            n = os.write(self._fd, buf)
            buf = buf[n:]
        os.fsync(self._fd)
        self._note(row, k)

    def close(self) -> None:
        if self._fd is not None:
            os.close(self._fd)
            self._fd = None



# ---------------------------------------------------------------------------------------
# families, params, frozen file
# ---------------------------------------------------------------------------------------
def load_families(injected: list[Family] | None = None) -> list[Family]:
    """``papere.policies.catalog.FAMILIES`` (imported lazily) or the injected list."""
    if injected is None:
        try:
            from papere.policies import catalog
        except ImportError as e:
            raise RunnerError(f"cannot import papere.policies.catalog ({e})") from None
        fams = list(catalog.FAMILIES)
    else:
        fams = list(injected)
    names = [f.name for f in fams]
    if len(set(names)) != len(names):
        raise RunnerError("family names must be unique")
    for f in fams:
        if f.name == "bound" or "@" in f.name:
            raise RunnerError(f"reserved family name {f.name!r}")
        if f.tuned_from is not None and f.tuned_from not in names:
            raise RunnerError(f"{f.name}: tuned_from {f.tuned_from!r} is not a family")
    return fams


def load_params(path: Path | str) -> PopulationParams:
    p = Path(path)
    try:
        d = json.loads(p.read_text())
    except OSError as e:
        raise RunnerError(f"cannot read population parameters {p}: {e}") from None
    for key in ("values", "params"):        # fit.py writes {"values": {...}, ...}
        if isinstance(d.get(key), dict):
            d = d[key]
            break
    names = [f.name for f in dataclasses.fields(PopulationParams)]
    missing = [n for n in names if n not in d]
    if missing:
        raise RunnerError(f"{p}: missing population parameters {missing}")
    return PopulationParams(**{n: float(d[n]) for n in names})


def _file_sha(path: Path) -> str | None:
    try:
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()
    except OSError:
        return None


def _cfg_json(cfg) -> object:
    return json.loads(_dumps(cfg))


def load_frozen(path: Path | str, params_sha: str | None = None,
                tune_range: tuple[int, int] = TUNE_RANGE) -> dict:
    """Load TUNING_FROZEN.json; refuse unless every entry rests on the full tuning seed set
    (``tune_range``, 50 seeds) and on the population parameters currently in use."""
    p = Path(path)
    if not p.exists():
        raise RunnerError(f"TUNING_FROZEN.json missing ({p}): run the tuning and --freeze "
                          "first (frozen F0R and SCALE runs refuse to start without it)")
    d = json.loads(p.read_text())
    meta = d.get("_meta", {})
    n_exp = tune_range[1] - tune_range[0] + 1
    if meta.get("seeds") != list(tune_range) or meta.get("n_seeds") != n_exp:
        raise RunnerError(f"{p}: frozen on seeds {meta.get('seeds')}, expected the full "
                          f"tuning set {list(tune_range)}")
    for fam, cells in d.items():
        if fam == "_meta":
            continue
        for cid, ent in cells.items():
            if ent.get("n_seeds") != n_exp or ent.get("seeds") != list(tune_range):
                raise RunnerError(f"{p}: entry {fam}/{cid} rests on n_seeds="
                                  f"{ent.get('n_seeds')} seeds={ent.get('seeds')}, "
                                  f"expected {n_exp} seeds {list(tune_range)}")
    if meta.get("population_params_sha256") != params_sha:
        raise RunnerError("population parameters changed since the freeze (sha256 of the "
                          "parameters in use differs from TUNING_FROZEN.json)")
    return d


def default_index(fam: Family) -> int:
    for i, g in enumerate(fam.grid):
        if _cfg_json(g) == _cfg_json(fam.default):
            return i
    return -1


def tune_name(family: str, idx: int) -> str:
    return f"{family}@c{idx:02d}"


# ---------------------------------------------------------------------------------------
# cells and planning
# ---------------------------------------------------------------------------------------
def study_cells(family: str) -> list[Cell]:
    if family == "F0R":
        return list(F0R_CELLS)
    if family == "KCOPY":
        return list(KCOPY_CELLS)
    if family == "SCALE":
        return [scale_cell(c) for c in F0R_CELLS if c.delta_A in SCALE_DELTA_A]
    raise RunnerError(f"unknown family {family!r}")


def f0r_cell_id(cell: Cell) -> str:
    """Id of the F0-R cell whose frozen configuration this cell uses.

    A cell with a class split (post hoc heterogeneity sweep) uses the frozen configuration of
    the baseline-split cell: the configurations were tuned on the baseline split only."""
    if cell.family == "SCALE" or cell.intol_share is not None:
        return replace(cell, family="F0R", intol_share=None, q_intol=None).cell_id
    return cell.cell_id


# A unit of work inside a task: (family name, sim policy name, config family, config index)
# where config index -1 means the config family's default.
Unit = tuple


def plan_units(families: list[Family], mode: str, cell: Cell, frozen: dict | None,
               selected: set[str] | None) -> list[Unit]:
    by_name = {f.name: f for f in families}
    units: list[Unit] = []
    for fam in families:
        if selected is not None and fam.name not in selected:
            continue
        if mode == "tune":
            if not fam.tunable:
                continue
            for idx in range(len(fam.grid)):
                units.append((fam.name, tune_name(fam.name, idx), fam.name, idx))
            continue
        src = by_name[fam.tuned_from] if fam.tuned_from else fam
        if frozen is not None and src.tunable:
            try:
                ent = frozen[src.name][f0r_cell_id(cell)]
            except KeyError:
                raise RunnerError(f"TUNING_FROZEN.json has no entry for family "
                                  f"{src.name!r} on cell {f0r_cell_id(cell)!r}") from None
            idx = int(ent["config_index"])
            if not 0 <= idx < len(src.grid) or _cfg_json(src.grid[idx]) != ent["config"]:
                raise RunnerError(f"frozen config of {src.name!r} on {cell.cell_id} does not "
                                  "match the family's current grid")
        else:
            idx = default_index(src)
        units.append((fam.name, fam.name, src.name, idx))
    return units


# ---------------------------------------------------------------------------------------
# worker side
# ---------------------------------------------------------------------------------------
class _Named:
    """Policy proxy that only changes ``name`` (the stream key in ``simulate``)."""

    def __init__(self, inner, name: str):
        self._inner = inner
        self.name = name

    @property
    def privileged(self) -> bool:
        return bool(getattr(self._inner, "privileged", False))

    def reset(self, static_view, rng, oracle=None):
        return self._inner.reset(static_view, rng, oracle=oracle)

    def floor_mask(self, static_view):
        return self._inner.floor_mask(static_view)

    def act(self, view):
        return self._inner.act(view)


_CTX: dict = {}


def _init_worker(ctx: dict) -> None:
    global _CTX
    _CTX = dict(ctx)


def _ctx_families() -> dict[str, Family]:
    if "family_map" not in _CTX:
        fams = load_families(_CTX.get("families"))
        _CTX["family_map"] = {f.name: f for f in fams}
    return _CTX["family_map"]


def _make_instance(study: str, seed: int, cell: Cell):
    if study == "KCOPY":
        return generate_kcopy(seed, cell, K=_CTX["kcopy_K"])
    return generate_f0r(seed, cell, N=_CTX["scale_N"] if study == "SCALE" else _CTX["f0r_N"])


def _timing(traj, wall_ms: float) -> dict:
    c = np.asarray(traj.cpu_ms, dtype=np.float64)
    return {"wall_ms": float(wall_ms),
            "cpu_ms_total": float(c.sum()) if c.size else 0.0,
            "cpu_ms_mean": float(c.mean()) if c.size else 0.0,
            "cpu_ms_p95": float(np.percentile(c, 95)) if c.size else 0.0,
            "cpu_ms_max": float(c.max()) if c.size else 0.0}


def _finish(row: dict, **extra) -> dict:
    row["study_family"] = row.pop("family")
    row.update(extra)
    return row


def run_task(task: tuple) -> tuple[list[dict], float]:
    """All pending work of one (seed, cell): returns (rows, cpu seconds of this task)."""
    cpu0 = time.process_time()
    study, mode, seed, cell, units, want_bound = task
    fams = _ctx_families()
    params: PopulationParams = _CTX["params"]
    psha = _CTX.get("params_sha256")
    inst = _make_instance(study, seed, cell)
    rows: list[dict] = []
    A0 = inst.availability()
    sha0 = a_sha256(A0)
    clair0 = clair_for(inst, A0)

    if want_bound:
        t0 = time.perf_counter()
        traj = bound_row(inst, A0, clair0)
        row = evaluate(inst, traj, clair=clair0)
        rows.append(_finish(row, family="bound", kind="bound", config=None, config_index=-1,
                            tuned_from=None, mode=mode, seed=int(seed),
                            params_sha256=psha,
                            **_timing(traj, (time.perf_counter() - t0) * 1e3)))
    for fam_name, sim_name, cfg_fam, cfg_idx in units:
        fam = fams[fam_name]
        src = fams[cfg_fam]
        cfg = src.default if cfg_idx < 0 else src.grid[cfg_idx]
        t0 = time.perf_counter()
        pol = _Named(fam.make(cfg, params), sim_name)
        traj = simulate(inst, cell, pol, seed)
        wall = (time.perf_counter() - t0) * 1e3
        # the bound on the policy's own realized A; reuse the unfloored one when equal
        clair = clair0 if a_sha256(traj.A) == sha0 else None
        row = evaluate(inst, traj, clair=clair)
        rows.append(_finish(row, family=fam.name, kind=fam.kind, config=_cfg_json(cfg),
                            config_index=int(cfg_idx), tuned_from=fam.tuned_from,
                            mode=mode, params_sha256=psha, **_timing(traj, wall)))
    return rows, time.process_time() - cpu0


# ---------------------------------------------------------------------------------------
# manifest
# ---------------------------------------------------------------------------------------
def _git_run(cwd: Path, *a):
    return subprocess.run(["git", "-C", str(cwd), *a], capture_output=True, text=True,
                          timeout=60)


def _git(repo_root: Path, extra_paths: list[Path] = ()) -> dict:
    """Commit and dirty flag. Dirty counts modified AND untracked files under src/,
    run_study.py, tests/ and the frozen/params files."""
    root = Path(repo_root)
    specs = ["src", "run_study.py", "tests", "results/TUNING_FROZEN.json",
             "results/population_params.json"]
    for q in extra_paths:
        try:
            specs.append(str(Path(q).resolve().relative_to(root.resolve())))
        except ValueError:
            pass
    try:
        c = _git_run(root, "rev-parse", "HEAD")
        if c.returncode != 0:
            return {"commit": None, "dirty": None}
        s = _git_run(root, "status", "--porcelain", "--untracked-files=all", "--", *specs)
        return {"commit": c.stdout.strip(), "dirty": bool(s.stdout.strip())}
    except (OSError, subprocess.SubprocessError):
        return {"commit": None, "dirty": None}


def is_committed(path: Path | str) -> bool:
    """File is tracked and identical to HEAD (``git ls-files`` and ``git diff HEAD``)."""
    p = Path(path)
    try:
        if not p.exists():
            return False
        if _git_run(p.parent, "ls-files", "--error-unmatch", "--", p.name).returncode != 0:
            return False
        return _git_run(p.parent, "diff", "--quiet", "HEAD", "--", p.name).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def _versions() -> dict:
    import networkx
    import scipy
    return {"python": platform.python_version(), "numpy": np.__version__,
            "scipy": scipy.__version__, "networkx": networkx.__version__}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _write_json_atomic(path: Path, obj) -> None:
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "w") as f:
        json.dump(obj, f, indent=2, sort_keys=False, default=_jsonable)
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def _row_counts(store: "RowStore") -> dict:
    return {"total": len(store), "by_mode": dict(store.by_mode),
            "by_family": dict(store.by_family)}


# ---------------------------------------------------------------------------------------
# run
# ---------------------------------------------------------------------------------------
def _resolve_cells(study: str, cell_ids: list[str] | None, study_cells_: list[Cell]) -> list[Cell]:
    if not cell_ids:
        return study_cells_
    by_id = {c.cell_id: c for c in study_cells_}
    unknown = [c for c in cell_ids if c not in by_id]
    if unknown:
        raise RunnerError(f"unknown {study} cell ids: {unknown[:5]}")
    return [by_id[c] for c in dict.fromkeys(cell_ids)]


def unit_config(fams: dict[str, Family], unit: Unit):
    src = fams[unit[2]]
    return _cfg_json(src.default if unit[3] < 0 else src.grid[unit[3]])


def run(study: str, seeds: tuple[int, int], out: Path | str, *, mode: str = "frozen",
        policies: list[str] | None = None, cell_ids: list[str] | None = None,
        workers: int = 4, families: list[Family] | None = None,
        params: PopulationParams | None = None, params_path: Path | str | None = None,
        frozen_path: Path | str | None = None, repo_root: Path | str = REPO_ROOT,
        open_ranges: dict | None = None, f0r_N: int = 30, scale_N: int = 300,
        kcopy_K: int = 8, after_row=None, allow_dirty: bool = False,
        argv: list[str] | None = None, extra_cells: list[Cell] | None = None) -> dict:
    """Run a study. ``open_ranges``, ``f0r_N``, ``scale_N``, ``kcopy_K`` and ``after_row``
    (called in the parent after each durable row) are for tests; the CLI never sets them.
    ``allow_dirty`` skips the committed-files check (recorded in the manifest)."""
    if mode not in ("tune", "frozen"):
        raise RunnerError(f"unknown mode {mode!r}")
    if study not in ("F0R", "KCOPY", "SCALE"):
        raise RunnerError(f"unknown family {study!r}")
    lo, hi = seeds
    check_seeds(study, mode, lo, hi, repo_root=repo_root, open_ranges=open_ranges)
    if mode == "tune" and study != "F0R":
        raise SeedRefused("tune mode is for family F0R only")
    tune_range = (OPEN_RANGES if open_ranges is None else open_ranges).get(
        ("F0R", "tune"), TUNE_RANGE)
    params_given = params_path is not None
    params_path = Path(params_path) if params_given else DEFAULT_PARAMS_PATH
    frozen_path = Path(frozen_path) if frozen_path else DEFAULT_FROZEN_PATH
    params_from_file = params is None
    if params is None:
        params = load_params(params_path)
    params_sha = _file_sha(params_path) if (params_given or params_from_file) else None
    fams = load_families(families)
    selected = None
    if policies:
        known = {f.name for f in fams}
        bad = [p for p in policies if p not in known]
        if bad:
            raise RunnerError(f"unknown policies {bad}; known: {sorted(known)}")
        selected = set(policies)
    needs_frozen = mode == "frozen" and study in ("F0R", "SCALE")
    frozen = load_frozen(frozen_path, params_sha, tune_range) if needs_frozen else None
    committed = {}
    if mode == "frozen":
        committed[str(params_path)] = is_committed(params_path)
        if needs_frozen:
            committed[str(frozen_path)] = is_committed(frozen_path)
        bad = [f for f, ok in committed.items() if not ok]
        if bad and not allow_dirty:
            raise RunnerError("frozen-mode runs need these files committed and unchanged "
                              f"vs HEAD: {bad} (commit them first)")
    # ``extra_cells`` (post hoc runs, scripts/run_posthoc_g3.py): cells outside the study's
    # list, selectable by id only; the CLI never passes them.
    cells = _resolve_cells(study, cell_ids, study_cells(study) + list(extra_cells or []))
    fam_map = {f.name: f for f in fams}

    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    lock_fd = os.open(out / ".lock", os.O_RDWR | os.O_CREAT, 0o644)
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        os.close(lock_fd)
        raise RunnerError(f"{out} is in use by another runner") from None

    try:
        store = RowStore(out / ROWS_NAME).load()
        skipped = 0
        tasks = []
        plan_by_cell = {c.cell_id: plan_units(fams, mode, c, frozen, selected) for c in cells}
        bound_hash = cfg_hash(None)

        def seen(k, h):
            """True if row k exists; a row with a different config is a refusal."""
            if k not in store.keys:
                return False
            if store.keys[k] != h:
                raise RunnerError(f"existing row {k} was produced with a different config "
                                  "than the current selection; use a fresh --out directory")
            return True

        for seed in range(lo, hi + 1):
            for c in cells:
                pend = []
                for u in plan_by_cell[c.cell_id]:
                    if seen((study, seed, c.cell_id, u[1]), cfg_hash(unit_config(fam_map, u))):
                        skipped += 1
                    else:
                        pend.append(u)
                want_bound = mode == "frozen" and not seen(
                    (study, seed, c.cell_id, "bound"), bound_hash)
                if mode == "frozen" and not want_bound:
                    skipped += 1
                if pend or want_bound:
                    tasks.append((study, mode, seed, c, pend, want_bound))

        workers = max(1, min(int(workers), len(tasks) or 1))
        git = _git(Path(repo_root), [params_path, frozen_path])
        prov = {"population_params_sha256": params_sha,
                "tuning_frozen_sha256": _file_sha(frozen_path) if needs_frozen else None,
                "allow_dirty": bool(allow_dirty), "committed": committed}
        inv = {"argv": argv, "family": study, "mode": mode, "seeds": [lo, hi],
               "policies": sorted(selected) if selected else None,
               "cells": [c.cell_id for c in cells], "workers": workers,
               "started_utc": _now(), "ended_utc": None, "status": "running",
               "git_commit": git["commit"], "git_dirty": git["dirty"], **prov,
               "tasks": len(tasks), "rows_skipped": skipped, "rows_written": 0,
               "partial_bytes_recovered": store.recovered_bytes, "cpu_s": None,
               "wall_s": None}
        manifest_path = out / "manifest.json"
        manifest = {}
        if manifest_path.exists():
            try:
                manifest = json.loads(manifest_path.read_text())
            except ValueError:
                manifest = {}
        invocations = list(manifest.get("invocations", []))
        invocations.append(inv)

        def write_manifest():
            manifest.update({
                "package_versions": _versions(), "git": git, "family": study, "mode": mode,
                "provenance": prov,
                "args": {"family": study, "mode": mode, "seeds": [lo, hi], "out": str(out),
                         "policies": inv["policies"], "cells": inv["cells"],
                         "workers": workers, "allow_dirty": bool(allow_dirty), "argv": argv},
                "start_utc": inv["started_utc"], "end_utc": inv["ended_utc"],
                "status": inv["status"], "cpu_s_total": inv["cpu_s"], "wall_s": inv["wall_s"],
                "row_counts": _row_counts(store), "invocations": invocations})
            _write_json_atomic(manifest_path, manifest)

        ctx = {"params": params, "params_sha256": params_sha, "families": families,
               "f0r_N": f0r_N, "scale_N": scale_N, "kcopy_K": kcopy_K}
        t_wall, t_cpu = time.perf_counter(), time.process_time()
        pool_cpu = 0.0
        written = 0
        try:
            write_manifest()
            store.open()

            def consume(result):
                nonlocal written, pool_cpu
                rows, cpu = result
                if workers > 1:             # inline tasks are already in the parent's CPU
                    pool_cpu += cpu
                for row in rows:
                    store.append(row)
                    written += 1
                    if after_row is not None:
                        after_row(row)

            if workers == 1:
                _init_worker(ctx)
                for task in tasks:
                    consume(run_task(task))
            else:
                methods = mp.get_all_start_methods()
                if families is not None and "fork" not in methods:
                    raise RunnerError("injected families need the fork start method")
                mpctx = mp.get_context("fork" if "fork" in methods and (sys.platform == "linux"
                                                                or families is not None)
                                       else None)
                with mpctx.Pool(workers, initializer=_init_worker, initargs=(ctx,)) as pool:
                    for res in pool.imap(run_task, tasks, chunksize=1):
                        consume(res)
            inv["status"] = "complete"
        except BaseException:
            inv["status"] = "failed"
            raise
        finally:
            store.close()
            inv["ended_utc"] = _now()
            inv["rows_written"] = written
            inv["wall_s"] = time.perf_counter() - t_wall
            inv["cpu_s"] = time.process_time() - t_cpu + pool_cpu
            write_manifest()
    finally:
        os.close(lock_fd)
    return {"rows_written": written, "rows_skipped": skipped, "tasks": len(tasks),
            "total_rows": len(store), "out": str(out), "status": inv["status"]}


# ---------------------------------------------------------------------------------------
# freeze
# ---------------------------------------------------------------------------------------
def freeze(out: Path | str, *, seeds: tuple[int, int] | None = None,
           cell_ids: list[str] | None = None, families: list[Family] | None = None,
           frozen_path: Path | str | None = None, params_path: Path | str | None = None,
           repo_root: Path | str = REPO_ROOT, open_ranges: dict | None = None,
           overwrite: bool = False) -> dict:
    """Per-cell selection from complete tuning rows -> TUNING_FROZEN.json (POLICY_SPEC 7).

    Requires the FULL tuning set: every seed of the tuning range (60000-60049) x every F0-R
    cell x every config of every tunable family. Lowest mean ``R_avoid_kwh_per100``, ties by
    lower mean ``violation_kwslot``, then lower configuration index. Streaming: the rows are
    read once, only exact running sums, counts and seed sets are kept. ``seeds`` and
    ``cell_ids`` may differ from the full set only together with a test ``open_ranges``.
    """
    ranges = OPEN_RANGES if open_ranges is None else open_ranges
    tune_range = ranges[("F0R", "tune")]
    seeds = tune_range if seeds is None else tuple(seeds)
    lo, hi = seeds
    check_seeds("F0R", "tune", lo, hi, repo_root=repo_root, open_ranges=open_ranges)
    if seeds != tune_range:
        raise RunnerError(f"freeze needs the full tuning set {tune_range}, got {seeds}")
    if cell_ids and open_ranges is None:
        raise RunnerError("freeze needs every F0-R cell; --cells is not allowed")
    frozen_path = Path(frozen_path) if frozen_path else DEFAULT_FROZEN_PATH
    params_path = Path(params_path) if params_path else DEFAULT_PARAMS_PATH
    fams = [f for f in load_families(families) if f.tunable]
    cells = _resolve_cells("F0R", cell_ids, study_cells("F0R"))
    path = Path(out) / ROWS_NAME
    RowStore(path).load(truncate=False)            # partial line / duplicates / corruption

    n_seeds = hi - lo + 1
    grids = {f.name: [_cfg_json(g) for g in f.grid] for f in fams}
    cell_set = {c.cell_id for c in cells}
    acc: dict[tuple, dict] = {
        (f.name, c.cell_id, i): {"n": 0, "obj": Fraction(0), "viol": Fraction(0),
                                 "seeds": set()}
        for f in fams for c in cells for i in range(len(f.grid))}
    shas: set = set()
    for r in iter_rows(path):
        if r.get("mode") != "tune" or r.get("study_family") != "F0R":
            continue
        key = (r["family"], r["cell_id"], int(r["config_index"]))
        a = acc.get(key)
        seed = int(r["seed"])
        if a is None or not lo <= seed <= hi:
            continue
        if r["policy"] != tune_name(key[0], key[2]) or r["config"] != grids[key[0]][key[2]]:
            raise RunnerError(f"row {row_key(r)} was run with a different config than the "
                              "family's current grid")
        obj, viol = r[OBJECTIVE_KEY], r[TIEBREAK_KEY]
        if not (isinstance(obj, (int, float)) and isinstance(viol, (int, float))
                and math.isfinite(obj) and math.isfinite(viol)):
            raise RunnerError(f"non-finite objective in row {row_key(r)}: "
                              f"{OBJECTIVE_KEY}={obj}, {TIEBREAK_KEY}={viol}")
        shas.add(r.get("params_sha256"))
        a["n"] += 1
        a["obj"] += Fraction(obj)
        a["viol"] += Fraction(viol)
        a["seeds"].add(seed)

    full = set(range(lo, hi + 1))
    n_missing, first = 0, []
    for key, a in acc.items():
        miss = full - a["seeds"]
        if miss:
            n_missing += len(miss)
            if len(first) < 3:
                first.append((*key, min(miss)))
        if a["n"] != len(a["seeds"]):
            raise RunnerError(f"duplicate tuning rows for {key}")
    if n_missing:
        raise RunnerError(f"refusing to freeze: {n_missing} tuning rows missing "
                          f"(family, cell, config, seed), first {first}")
    if len(shas) != 1:
        raise RunnerError(f"tuning rows disagree on population_params sha256: {sorted(map(str, shas))}")
    sha = next(iter(shas))
    if sha != _file_sha(params_path):
        raise RunnerError("tuning rows were produced with population parameters that differ "
                          f"from the current {params_path}")

    result: dict = {}
    digest = hashlib.sha256()
    for fam in fams:
        result[fam.name] = {}
        for c in cells:
            best = None
            for idx in range(len(fam.grid)):
                a = acc[(fam.name, c.cell_id, idx)]
                obj, viol = float(a["obj"] / a["n"]), float(a["viol"] / a["n"])
                digest.update(repr((fam.name, c.cell_id, idx, a["n"], str(a["obj"]),
                                    str(a["viol"]))).encode())
                cand = (round(obj, 9), round(viol, 9), idx)
                if best is None or cand < best[0]:
                    best = (cand, obj, viol)
            idx = best[0][2]
            result[fam.name][c.cell_id] = {
                "config_index": idx, "config": grids[fam.name][idx],
                f"mean_{OBJECTIVE_KEY}": best[1], f"mean_{TIEBREAK_KEY}": best[2],
                "n_seeds": n_seeds, "seeds": [lo, hi]}
    git = _git(Path(repo_root))
    result["_meta"] = {
        "selection": f"lowest mean {OBJECTIVE_KEY}, ties by mean {TIEBREAK_KEY}, then "
                     "config index",
        "seeds": [lo, hi], "n_seeds": n_seeds, "tuning_rows_sha256": digest.hexdigest(),
        "population_params_sha256": sha, "git_commit": git["commit"],
        "git_dirty": git["dirty"],
        "families": [f.name for f in fams], "cells": [c.cell_id for c in cells]}
    text = json.dumps(result, indent=2, default=_jsonable) + "\n"
    if frozen_path.exists() and not overwrite:
        old = json.loads(frozen_path.read_text())
        new = json.loads(text)
        for d in (old, new):                       # the commit may move; the selection may not
            d.get("_meta", {}).pop("git_commit", None)
            d.get("_meta", {}).pop("git_dirty", None)
        if old != new:
            raise RunnerError(f"{frozen_path} exists and differs; a frozen file is not "
                              "overwritten without overwrite=True (--overwrite-frozen)")
    frozen_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = frozen_path.with_name(frozen_path.name + ".tmp")
    with open(tmp, "w") as f:
        f.write(text)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, frozen_path)
    return result


# ---------------------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="run_study.py", description=__doc__.split("\n")[0])
    p.add_argument("--family", required=True, choices=["F0R", "KCOPY", "SCALE"])
    p.add_argument("--seeds", help="A-B (inclusive) or A; default for --freeze: 60000-60049")
    p.add_argument("--out", required=True, help="results directory, e.g. results/f0r_pilot")
    p.add_argument("--mode", choices=["tune", "frozen"], default="frozen")
    p.add_argument("--policies", help="comma-separated family names")
    p.add_argument("--cells", help="comma-separated cell ids")
    p.add_argument("--workers", type=int, default=4)
    p.add_argument("--freeze", action="store_true",
                   help="select per-cell configs from complete tuning rows in --out")
    p.add_argument("--overwrite-frozen", action="store_true")
    p.add_argument("--frozen-path", default=None)
    p.add_argument("--population-params", default=None)
    p.add_argument("--allow-dirty", action="store_true",
                   help="skip the committed-files check (recorded in the manifest)")
    return p


def _csv(s: str | None) -> list[str] | None:
    return [x.strip() for x in s.split(",") if x.strip()] if s else None


def main(argv: list[str] | None = None, **inject) -> int:
    """CLI entry. ``inject`` (tests only): families, params, repo_root, open_ranges, f0r_N,
    scale_N, kcopy_K, after_row."""
    argv = list(sys.argv[1:] if argv is None else argv)
    args = build_parser().parse_args(argv)
    try:
        if args.freeze:
            if args.family != "F0R":
                raise RunnerError("--freeze applies to family F0R tuning rows")
            seeds = parse_seeds(args.seeds) if args.seeds else None
            res = freeze(args.out, seeds=seeds, cell_ids=_csv(args.cells),
                         families=inject.get("families"), frozen_path=args.frozen_path,
                         params_path=args.population_params,
                         repo_root=inject.get("repo_root", REPO_ROOT),
                         open_ranges=inject.get("open_ranges"),
                         overwrite=args.overwrite_frozen)
            print(f"[runner] froze {len(res) - 1} families -> "
                  f"{args.frozen_path or DEFAULT_FROZEN_PATH}")
            return 0
        if not args.seeds:
            raise RunnerError("--seeds is required")
        summary = run(args.family, parse_seeds(args.seeds), args.out, mode=args.mode,
                      policies=_csv(args.policies), cell_ids=_csv(args.cells),
                      workers=args.workers, params_path=args.population_params,
                      frozen_path=args.frozen_path, allow_dirty=args.allow_dirty,
                      argv=argv, **inject)
        print(f"[runner] {summary['status']}: wrote {summary['rows_written']} rows, skipped "
              f"{summary['rows_skipped']}, total {summary['total_rows']} in {summary['out']}")
        return 0
    except RunnerError as e:
        print(f"[runner] error: {e}", file=sys.stderr)
        return 2
