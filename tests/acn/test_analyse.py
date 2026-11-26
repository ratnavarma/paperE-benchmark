"""Tests for papere.acn.analyse on tiny synthetic row files."""
from __future__ import annotations

import json

import pytest

from papere.acn.analyse import (
    H1_CELL_ID,
    SEC_CELL_D1,
    SEC_CELL_D4,
    analyse_files,
    analyse_variant_rows,
)


def _row(seed: int, cell_id: str, policy: str, r_avoid_per100: float, *,
         r_avoid_kwh: float | None = None, feasible_cap: bool = True) -> dict:
    return {
        "mode": "frozen",
        "study_family": "F0R",
        "seed": seed,
        "cell_id": cell_id,
        "policy": policy,
        "R_avoid_kwh_per100": r_avoid_per100,
        "R_avoid_kwh": r_avoid_per100 * 0.2 if r_avoid_kwh is None else r_avoid_kwh,
        "feasible_strict": feasible_cap,
        "feasible_cap": feasible_cap,
        "feasible_headroom": True,
    }


def test_analyse_h1_share_and_secondary_contrast(tmp_path):
    # Primary cell H1: ce=10, pop=4, targ=2 -> obl=6, tot=8 -> share = 0.75 (exact on every seed)
    # Secondary d1: ce=10, pop=2, targ=0 -> share = 0.80
    # Secondary d4: ce=10, pop=7, targ=0 -> share = 0.30
    # Secondary contrast: 0.80 - 0.30 = 0.50
    rows = []
    for s in range(60000, 60010):
        rows.append(_row(s, H1_CELL_ID, "ce_llf", 10.0))
        rows.append(_row(s, H1_CELL_ID, "pop_mpc", 4.0))
        rows.append(_row(s, H1_CELL_ID, "guarded_mpc_e1", 2.0))

        rows.append(_row(s, SEC_CELL_D1, "ce_llf", 10.0))
        rows.append(_row(s, SEC_CELL_D1, "pop_mpc", 2.0))
        rows.append(_row(s, SEC_CELL_D1, "guarded_mpc_e1", 0.0))

        rows.append(_row(s, SEC_CELL_D4, "ce_llf", 10.0))
        rows.append(_row(s, SEC_CELL_D4, "pop_mpc", 7.0))
        rows.append(_row(s, SEC_CELL_D4, "guarded_mpc_e1", 0.0))

    p_t2 = tmp_path / "t2_rows.jsonl"
    p_t2.write_text("\n".join(json.dumps(r) for r in rows) + "\n")

    res = analyse_files(p_t2, n_boot=500)["t2"]
    assert res["reported"] is True
    assert res["h1"]["share"] == pytest.approx(0.75)
    assert res["h1"]["share_ci"] == pytest.approx([0.75, 0.75])
    assert res["h1"]["h1_supported"] is True
    assert res["secondary_contrast"]["share_d1"] == pytest.approx(0.80)
    assert res["secondary_contrast"]["share_d4"] == pytest.approx(0.30)
    assert res["secondary_contrast"]["contrast_d1_minus_d4"] == pytest.approx(0.50)


def test_analyse_t2_emp_and_real_limit_feasibility_gate():
    rows_few = []
    for s in range(60000, 60010):  # only 10 feasible (< 50)
        rows_few.append(_row(s, H1_CELL_ID, "ce_llf", 10.0, feasible_cap=True))
        rows_few.append(_row(s, H1_CELL_ID, "pop_mpc", 6.0, feasible_cap=True))
        rows_few.append(_row(s, H1_CELL_ID, "guarded_mpc_e1", 2.0, feasible_cap=True))

    res_emp = analyse_variant_rows(rows_few, variant="t2_emp", n_boot=200)
    assert res_emp["reported"] is True
    assert res_emp["meta"]["is_hypothesis_test"] is False
    assert "h1_supported" not in res_emp["h1"]
    assert res_emp["h1"]["share"] == pytest.approx(0.5)

    res_rl_blocked = analyse_variant_rows(rows_few, variant="real_limit", n_boot=200, min_feasible=50)
    assert res_rl_blocked["reported"] is False
    assert res_rl_blocked["feasibility"]["n_feasible_cap"] == 10

    # With 50 feasible + 5 infeasible (excluded), gate passes and share uses feasible seeds only
    rows_many = []
    for i in range(55):
        s = 60000 + i
        ok = i < 50
        rows_many.append(_row(s, H1_CELL_ID, "ce_llf", 10.0, feasible_cap=ok))
        rows_many.append(_row(s, H1_CELL_ID, "pop_mpc", 2.0 if ok else 9.0, feasible_cap=ok))
        rows_many.append(_row(s, H1_CELL_ID, "guarded_mpc_e1", 0.0, feasible_cap=ok))

    res_rl_ok = analyse_variant_rows(rows_many, variant="real_limit", n_boot=200, min_feasible=50)
    assert res_rl_ok["reported"] is True
    assert res_rl_ok["feasibility"]["n_feasible_cap"] == 50
    assert res_rl_ok["h1"]["n_seeds"] == 50
    assert res_rl_ok["h1"]["share"] == pytest.approx(0.8)
