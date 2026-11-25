"""Post hoc development runs, added after the G3 review: sLLF anchor, heterogeneity sweep,
flagged-only floor. Development seeds 61000-61099 only; rows go to results/f0r_extra/.

Label: "development, post hoc, added after the G3 review". Existing results files are not
touched. Frozen configurations come from results/TUNING_FROZEN.json (the heterogeneity cells use
the baseline-split entries: the configurations and the e1 population prior were fitted on the
baseline split, so off-baseline splits test a mis-specified prior).

Run (from a clean, committed tree):  uv run python scripts/run_posthoc_g3.py [--workers 6]

Runs, all F0-R, M = 3, r = 0.3, delta_b = 0:
  1. sLLF anchor:  delta_A in {0,1,2,4}, rho in {0.95,1.15};
                   sllf, ce_llf, mpc_ce, pop_mpc, guarded_mpc_e1, oracle_mpc.
  2. heterogeneity: delta_A = 2, rho in {0.95,1.15}, splits (0.15, 0.88) and (0.5, 0.27)
                   (the baseline split (1/3, 0.40) is run 1's delta_A = 2 cells);
                   ce_llf, mpc_ce, pop_mpc, guarded_mpc_e1, oracle_mpc.
  3. flagged-only floor: delta_A in {2,4}, rho in {0.95,1.15};
                   floor, floor_flagged and the frozen best oblivious policy of the cell.
  4. llf_pop (LLF-POST with the population belief, frozen llf_post configuration per cell) and
                   llf_post itself (its paired comparator) on the sLLF cells: delta_A in {0,1,2,4}, rho in {0.95,1.15}. Appended to the
                   same rows file with a new manifest invocation; rerunning writes nothing new.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import replace
from pathlib import Path

from papere import runner
from papere.analysis import frozen_best
from papere.instance import Cell
from papere.policies.catalog import FAMILIES
from papere.policies.posthoc import EXTRA_FAMILIES

OUT = Path("results/f0r_extra")
SEEDS = (61000, 61099)
LABEL = "development, post hoc, added after the G3 review"
RHOS = (0.95, 1.15)
SPLITS = ((0.15, 0.88), (0.5, 0.27))        # (share intolerant, q intolerant); tolerant q = 0.01
SLLF_POLICIES = ("sllf", "ce_llf", "mpc_ce", "pop_mpc", "guarded_mpc_e1", "oracle_mpc")
HET_POLICIES = ("ce_llf", "mpc_ce", "pop_mpc", "guarded_mpc_e1", "oracle_mpc")
POP_POLICIES = ("llf_pop", "llf_post")   # llf_post: the paired e1 comparator of llf_pop
FLOOR_DELTAS = (2, 4)


def base_cell(dA: int, rho: float, **kw) -> Cell:
    return Cell(family="F0R", M=3, delta_A=dA, delta_b=0, rho=rho, r=0.3, **kw)


def sllf_cells() -> list[Cell]:
    return [base_cell(d, rho) for d in (0, 1, 2, 4) for rho in RHOS]


def het_cells() -> list[Cell]:
    return [base_cell(2, rho, intol_share=s, q_intol=q) for s, q in SPLITS for rho in RHOS]


def floor_cells() -> list[Cell]:
    return [base_cell(d, rho) for d in FLOOR_DELTAS for rho in RHOS]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--workers", type=int, default=6)
    args = ap.parse_args()
    frozen = json.loads(Path("results/TUNING_FROZEN.json").read_text())
    fams = list(FAMILIES) + list(EXTRA_FAMILIES)
    extra = het_cells()

    def go(cells: list[Cell], policies: list[str]) -> None:
        res = runner.run("F0R", SEEDS, OUT, mode="frozen", policies=policies,
                         cell_ids=[c.cell_id for c in cells], workers=args.workers,
                         families=fams, extra_cells=extra,
                         argv=["scripts/run_posthoc_g3.py", f"label={LABEL}"])
        print(f"[posthoc_g3] {[c.cell_id for c in cells][:2]}...{policies}: {res}")

    go(sllf_cells(), list(SLLF_POLICIES))
    go(het_cells(), list(HET_POLICIES))
    for c in floor_cells():
        best = frozen_best(frozen, c.cell_id)["best"]
        go([c], sorted({"floor", "floor_flagged", best}))
    go(sllf_cells(), list(POP_POLICIES))


if __name__ == "__main__":
    main()
