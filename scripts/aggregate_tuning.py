"""Aggregate the tuning rows into one row per (family, cell_id, config_index).

Usage: nice uv run python scripts/aggregate_tuning.py [--rows results/tuning/rows.jsonl]
                                                       [--out results/tuning/aggregates.csv]

Reads ``rows.jsonl`` read-only and as a stream (no lock, no write, no truncation), so it is
safe while the tuning job is still appending. A line that does not parse (the partial trailing
line of a file being written) is skipped and counted. Memory is O(groups): running sums keyed by
``(family, cell_id, config_index)`` plus the set of seeds seen in the group.

Output columns: family, kind, cell_id, config_index, config (JSON), n_seeds, seed_min,
seed_max, R_avoid_kwh_per100 mean and sd (sample, ddof = 1), and the means of
R_avoid_sp_kwh_per100, violation_kwslot (kW.slot, the ledger key), violation_count,
hedge_waste_kwslot, deadline_miss_count, event_shortfall_kwh, cpu_ms_mean, plus params_sha256
(asserted single-valued within the group).

Coverage printed: rows seen against the expected total, derived from
``papere.policies.catalog.FAMILIES`` (tunable families x grid size x F0R_CELLS x seeds), and per
family the number of expected (cell, config) groups with fewer than 50 seeds (absent groups
count as 0 seeds). No instance is generated and nothing is simulated.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:          # allow running without an editable install
    sys.path.insert(0, str(ROOT / "src"))

from papere.generator import F0R_CELLS  # noqa: E402
from papere.policies.catalog import FAMILIES  # noqa: E402

N_SEEDS = 50                                    # tuning block 60000-60049
OBJECTIVE = "R_avoid_kwh_per100"
MEAN_KEYS = ("R_avoid_sp_kwh_per100", "violation_kwslot", "violation_count",
             "hedge_waste_kwslot", "deadline_miss_count", "event_shortfall_kwh",
             "cpu_ms_mean")
DEFAULT_ROWS = ROOT / "results" / "tuning" / "rows.jsonl"
DEFAULT_OUT = ROOT / "results" / "tuning" / "aggregates.csv"

COLUMNS = (["family", "kind", "cell_id", "config_index", "config", "n_seeds", "seed_min",
            "seed_max", OBJECTIVE + "_mean", OBJECTIVE + "_sd"]
           + [k + "_mean" for k in MEAN_KEYS] + ["params_sha256"])


@dataclass
class Group:
    kind: str
    config: dict
    params_sha256: str
    seeds: set = field(default_factory=set)
    n: int = 0
    mean: float = 0.0                           # Welford running mean / sum of squares
    m2: float = 0.0
    sums: list = field(default_factory=lambda: [0.0] * len(MEAN_KEYS))


@dataclass
class Stats:
    lines: int = 0
    parsed: int = 0
    skipped_unparsable: int = 0
    skipped_not_tune: int = 0
    skipped_untunable_family: int = 0
    duplicates: int = 0
    used: int = 0
    param_hashes: set = field(default_factory=set)


def tunable_families() -> list:
    return [f for f in FAMILIES if f.tunable]


def expected_groups() -> dict:
    """{family: set of (cell_id, config_index)} the full tuning run must cover."""
    cells = [c.cell_id for c in F0R_CELLS]
    return {f.name: {(c, i) for c in cells for i in range(len(f.grid))}
            for f in tunable_families()}


def expected_rows(n_seeds: int = N_SEEDS) -> int:
    return sum(len(g) for g in expected_groups().values()) * n_seeds


def aggregate(path) -> tuple[dict, Stats]:
    """Stream ``path`` and return ({(family, cell_id, config_index): Group}, Stats)."""
    tunable = {f.name for f in tunable_families()}
    groups: dict = {}
    st = Stats()
    with open(path, "rb") as fh:
        for raw in fh:
            st.lines += 1
            try:
                row = json.loads(raw)
            except ValueError:                  # partial (or corrupt) line: skip
                st.skipped_unparsable += 1
                continue
            if not isinstance(row, dict):
                st.skipped_unparsable += 1
                continue
            st.parsed += 1
            if row.get("mode") != "tune":
                st.skipped_not_tune += 1
                continue
            fam = row["family"]
            if fam not in tunable:
                st.skipped_untunable_family += 1
                continue
            key = (fam, row["cell_id"], int(row["config_index"]))
            seed = int(row["seed"])
            sha = row["params_sha256"]
            st.param_hashes.add(sha)
            g = groups.get(key)
            if g is None:
                g = groups[key] = Group(kind=row["kind"], config=row["config"],
                                        params_sha256=sha)
            else:
                assert g.params_sha256 == sha, f"params_sha256 differs within group {key}"
            if seed in g.seeds:
                st.duplicates += 1
                continue
            g.seeds.add(seed)
            x = float(row[OBJECTIVE])
            g.n += 1
            d = x - g.mean
            g.mean += d / g.n
            g.m2 += d * (x - g.mean)
            for j, k in enumerate(MEAN_KEYS):
                g.sums[j] += float(row[k])
            st.used += 1
    return groups, st


def _fmt(x: float) -> str:
    return repr(float(x))


def write_csv(groups: dict, out) -> int:
    out = Path(out)
    tmp = out.with_name(out.name + ".tmp")
    with open(tmp, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(COLUMNS)
        for (fam, cell, idx) in sorted(groups):
            g = groups[(fam, cell, idx)]
            sd = _fmt(math.sqrt(g.m2 / (g.n - 1))) if g.n > 1 else ""
            w.writerow([fam, g.kind, cell, idx, json.dumps(g.config),
                        g.n, min(g.seeds), max(g.seeds), _fmt(g.mean), sd]
                       + [_fmt(s / g.n) for s in g.sums] + [g.params_sha256])
    os.replace(tmp, out)
    return len(groups)


def coverage(groups: dict, st: Stats, n_seeds: int = N_SEEDS) -> dict:
    exp = expected_groups()
    exp_rows = sum(len(v) for v in exp.values()) * n_seeds
    short = {}
    zero = {}
    for fam, keys in exp.items():
        short[fam] = sum(1 for (c, i) in keys
                         if (fam, c, i) not in groups or groups[(fam, c, i)].n < n_seeds)
        zero[fam] = sum(1 for (c, i) in keys if (fam, c, i) not in groups)
    unexpected = sum(1 for (fam, c, i) in groups if (c, i) not in exp.get(fam, ()))
    return {"expected_rows": exp_rows, "rows_used": st.used, "short": short, "zero": zero,
            "expected_groups": {f: len(v) for f, v in exp.items()}, "unexpected": unexpected}


def print_coverage(groups: dict, st: Stats, n_seeds: int = N_SEEDS, file=None) -> dict:
    file = file or sys.stdout
    cov = coverage(groups, st, n_seeds)
    exp_rows = cov["expected_rows"]
    n_fam = len(cov["expected_groups"])
    print(f"lines read {st.lines}; parsed {st.parsed}; unparsable/partial skipped "
          f"{st.skipped_unparsable}; non-tune {st.skipped_not_tune}; untunable family "
          f"{st.skipped_untunable_family}; duplicate (group, seed) {st.duplicates}", file=file)
    print(f"coverage: {st.used} rows used / {exp_rows} expected "
          f"({100.0 * st.used / exp_rows:.2f}%) = {n_fam} tunable families x "
          f"{len(F0R_CELLS)} cells x grid x {n_seeds} seeds; groups present {len(groups)} / "
          f"{sum(cov['expected_groups'].values())}; unexpected groups {cov['unexpected']}",
          file=file)
    print(f"distinct params_sha256 overall: {len(st.param_hashes)}", file=file)
    print("groups with < %d seeds per family (of which absent):" % n_seeds, file=file)
    for fam, n in cov["short"].items():
        print(f"  {fam:16s} {n:4d} / {cov['expected_groups'][fam]:4d}  (absent {cov['zero'][fam]})",
              file=file)
    return cov


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--rows", default=str(DEFAULT_ROWS))
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    args = ap.parse_args(argv)
    t0 = time.perf_counter()
    groups, st = aggregate(args.rows)
    n = write_csv(groups, args.out)
    print_coverage(groups, st)
    print(f"wrote {n} group rows to {args.out} in {time.perf_counter() - t0:.1f} s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
