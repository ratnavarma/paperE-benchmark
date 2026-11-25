"""Greedy expected-value hedge ranker: tuning, freeze and development runs (post hoc).

Label: "descriptive, post hoc, added 2026-11-02 at the referee's request". Design in
docs/RANKER_POSTHOC.md; the policy is src/papere/policies/ranker.py (RANKER_FAMILIES).

  uv run python scripts/run_posthoc_ranker.py tune   [--workers 16]
      every configuration of greedy_ev, greedy_ev_pop (m x gamma, 12 each) and greedy_ev_ce (m, 3)
      on tuning seeds 60000-60049, all 22 F0-R cells -> results/tuning_posthoc_ranker/rows.jsonl
  uv run python scripts/run_posthoc_ranker.py freeze
      the runner's selection rule (lowest mean R_avoid, then violations, then index)
      -> results/TUNING_FROZEN_posthoc_ranker.json (results/TUNING_FROZEN.json is never touched)
  uv run python scripts/run_posthoc_ranker.py run    [--workers 16]
      development seeds 61000-61099, M = 3, delta_A in {0,1,2,4}, rho in {0.95,1.15}, r = 0.3:
      the three ranker families at their frozen configuration, then ce_llf, pop_mpc and
      guarded_mpc_e1 at theirs (results/TUNING_FROZEN.json) as a reproduction check against
      results/f0r_extra -> results/f0r_posthoc_ranker/rows.jsonl (+ .gz copy)

The new frozen file cannot be committed before the run (commits wait for the author), so the ranker
invocation passes allow_dirty=True; the runner records it in the manifest. The comparator
invocation needs no such flag. Reserved seeds are refused by the runner; no approval file is
created here.
"""
from __future__ import annotations

import argparse
import gzip
import shutil
from pathlib import Path

from papere import runner
from papere.instance import Cell
from papere.policies.catalog import FAMILIES
from papere.policies.ranker import RANKER_FAMILIES

ROOT = Path(__file__).resolve().parents[1]
TUNE_OUT = ROOT / "results" / "tuning_posthoc_ranker"
FROZEN = ROOT / "results" / "TUNING_FROZEN_posthoc_ranker.json"
OUT = ROOT / "results" / "f0r_posthoc_ranker"
TUNE_SEEDS = (60000, 60049)
DEV_SEEDS = (61000, 61099)
LABEL = "descriptive, post hoc, added 2026-11-02 at the referee's request"
RANKERS = [f.name for f in RANKER_FAMILIES]
COMPARATORS = ["ce_llf", "pop_mpc", "guarded_mpc_e1"]


def cells() -> list[Cell]:
    return [Cell(family="F0R", M=3, delta_A=d, delta_b=0, rho=rho, r=0.3)
            for d in (0, 1, 2, 4) for rho in (0.95, 1.15)]


def gz_copy(d: Path) -> None:
    src = d / runner.ROWS_NAME
    with open(src, "rb") as fi, gzip.GzipFile(d / (runner.ROWS_NAME + ".gz"), "wb",
                                               mtime=0) as fo:
        shutil.copyfileobj(fi, fo)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("step", choices=["tune", "freeze", "run"])
    ap.add_argument("--workers", type=int, default=16)
    a = ap.parse_args()
    argv = ["scripts/run_posthoc_ranker.py", a.step, f"label={LABEL}"]
    if a.step == "tune":
        res = runner.run("F0R", TUNE_SEEDS, TUNE_OUT, mode="tune", workers=a.workers,
                         families=list(RANKER_FAMILIES), argv=argv)
        print(f"[ranker tune] {res}")
        gz_copy(TUNE_OUT)
    elif a.step == "freeze":
        res = runner.freeze(TUNE_OUT, families=list(RANKER_FAMILIES), frozen_path=FROZEN)
        for fam in RANKERS:
            print(fam, {c: v["config"] for c, v in res[fam].items() if "_M3_" in c and c.endswith("r0.3")
                        and "_db0_" in c})
        print(f"[ranker freeze] -> {FROZEN}")
    else:
        ids = [c.cell_id for c in cells()]
        res = runner.run("F0R", DEV_SEEDS, OUT, mode="frozen", policies=RANKERS, cell_ids=ids,
                         workers=a.workers, families=list(RANKER_FAMILIES), frozen_path=FROZEN,
                         allow_dirty=True, argv=argv)
        print(f"[ranker run] rankers: {res}")
        res = runner.run("F0R", DEV_SEEDS, OUT, mode="frozen", policies=COMPARATORS,
                         cell_ids=ids, workers=a.workers, families=list(FAMILIES), argv=argv)
        print(f"[ranker run] comparators: {res}")
        gz_copy(OUT)


if __name__ == "__main__":
    main()
