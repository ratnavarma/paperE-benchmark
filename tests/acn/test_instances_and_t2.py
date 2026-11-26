"""Tests for papere.acn.instances and papere.acn.run_t2."""
from __future__ import annotations

from datetime import datetime, timedelta
import json
from zoneinfo import ZoneInfo

import numpy as np
import pytest

from papere.acn.instances import (
    T2_P_UNITS,
    build_acn_instance,
    build_t2_site_days,
    compute_site_real_limits,
    instance_feasibility,
    pick_site_day,
)
from papere.acn.load import clean_sessions
from papere.acn.run_t2 import T2_CELLS, resolve_t2_cells, run_t2
from papere.generator import generate_f0r
from papere.instance import Cell

LA = ZoneInfo("America/Los_Angeles")


def _rfc2822_utc(dt_local: datetime) -> str:
    return dt_local.astimezone(ZoneInfo("UTC")).strftime("%a, %d %b %Y %H:%M:%S GMT")


def _make_site_sessions(day_num: int, n_evening: int = 6, site: str = "caltech"):
    raws = []
    # 5 morning filler sessions so total cleaned >= 10
    m0 = datetime(2019, 11, day_num, 8, 0, tzinfo=LA)
    for j in range(5):
        raws.append({
            "sessionID": f"m_{day_num}_{j}",
            "userID": f"um_{j}",
            "timezone": "America/Los_Angeles",
            "connectionTime": _rfc2822_utc(m0),
            "disconnectTime": _rfc2822_utc(m0 + timedelta(hours=2)),
            "kWhDelivered": 4.0,
            "userInputs": [{"kWhRequested": 4.0}],
            "pilotSignal": {"timestamps": [_rfc2822_utc(m0)], "pilot": [32.0]},
            "chargingCurrent": {"timestamps": [_rfc2822_utc(m0)], "current": [16.0]},
        })
    # Evening sessions connected at 17:00
    c0 = datetime(2019, 11, day_num, 16, 0, tzinfo=LA)
    e = datetime(2019, 11, day_num, 17, 0, tzinfo=LA)
    for j in range(n_evening):
        # Disconnect at 17:30 + 15*j min -> d_i = 2 + j
        disc = e + timedelta(minutes=30 + 15 * j)
        # Constant current 10 A, kWhDelivered = 2.0 -> delivered by 17:00 is < 2.0, req = 4.0 + j
        raws.append({
            "sessionID": f"e_{day_num}_{j}",
            "userID": f"ue_{j}",
            "timezone": "America/Los_Angeles",
            "connectionTime": _rfc2822_utc(c0),
            "disconnectTime": _rfc2822_utc(disc),
            "kWhDelivered": 2.0,
            "userInputs": [{"kWhRequested": 4.0 + j}],
            "pilotSignal": {"timestamps": [_rfc2822_utc(c0)], "pilot": [32.0]},
            "chargingCurrent": {"timestamps": [_rfc2822_utc(c0)], "current": [10.0]},
        })
    # Also one session disconnecting at 17:10 (d_i = 0 -> must be dropped)
    raws.append({
        "sessionID": f"short_{day_num}",
        "userID": "ushort",
        "timezone": "America/Los_Angeles",
        "connectionTime": _rfc2822_utc(c0),
        "disconnectTime": _rfc2822_utc(e + timedelta(minutes=10)),
        "kWhDelivered": 1.0,
        "userInputs": [{"kWhRequested": 5.0}],
        "pilotSignal": {"timestamps": [_rfc2822_utc(c0)], "pilot": [32.0]},
        "chargingCurrent": {"timestamps": [_rfc2822_utc(c0)], "current": [10.0]},
    })
    sess, _ = clean_sessions(raws, site=site)
    return sess


def test_instance_keeps_data_and_frozen_generator_streams():
    sess = _make_site_sessions(4, n_evening=6)  # Monday Nov 4 2019
    sds = build_t2_site_days({"caltech": sess})
    assert len(sds) == 1
    sd = sds[0]
    assert sd.N == 6
    assert np.all(sd.P == T2_P_UNITS)
    assert np.all(sd.a == 0)
    assert list(sd.d) == [2, 3, 4, 5, 6, 7]

    cell = Cell(family="F0R", M=3, delta_A=2, delta_b=0, rho=0.95, r=0.3)
    seed = 60000
    inst = build_acn_instance(seed, cell, sd)
    ref = generate_f0r(seed, cell, N=sd.N)

    # Real E, P, a, d preserved
    assert np.array_equal(inst.E, sd.E)
    assert np.array_equal(inst.P, sd.P)
    assert np.array_equal(inst.a, sd.a)
    assert np.array_equal(inst.d, sd.d)

    # Frozen generator streams reused identically
    assert np.array_equal(inst.b_mean, ref.b_mean)
    assert np.array_equal(inst.b, ref.b)
    assert np.array_equal(inst.cls, ref.cls)
    assert np.array_equal(inst.q, ref.q)
    assert np.array_equal(inst.v, ref.v)
    assert np.array_equal(inst.u, ref.u)
    assert np.array_equal(inst.prior_A, ref.prior_A)
    assert np.array_equal(inst.prior_stuck, ref.prior_stuck)

    # Frozen L formula: L = (sum(E) / rho + sum(b_mean)) / H
    expected_L = (float(sd.E.sum()) / cell.rho + float(ref.b_mean.sum())) / 24.0
    assert np.allclose(inst.L, expected_L)


def test_t2_emp_and_real_limit_variants():
    sess = _make_site_sessions(4, n_evening=6)
    sds = build_t2_site_days({"caltech": sess})
    sd = sds[0]
    cell = Cell(family="F0R", M=3, delta_A=2, delta_b=0, rho=0.95, r=0.3)
    seed = 60001

    inst_base = build_acn_instance(seed, cell, sd)
    inst_emp = build_acn_instance(seed, cell, sd, emp_beta_ab=(0.5, 2.5))
    assert not np.array_equal(inst_emp.q, inst_base.q)
    assert np.all((inst_emp.q >= 0.0) & (inst_emp.q <= 1.0))
    assert np.array_equal(inst_emp.b, inst_base.b)
    assert np.array_equal(inst_emp.v, inst_base.v)

    # Real limit variant
    limits = compute_site_real_limits({"caltech": sess})
    assert limits["caltech"] > 0.0
    inst_rl = build_acn_instance(seed, cell, sd, real_limit_units=limits["caltech"])
    expected_L_rl = limits["caltech"] + float(inst_base.b_mean.sum()) / 24.0
    assert np.allclose(inst_rl.L, expected_L_rl)
    feas = instance_feasibility(inst_rl)
    assert set(feas.keys()) == {"feasible_strict", "feasible_cap", "feasible_headroom"}


def test_pick_site_day_and_mini_run_t2(tmp_path):
    sess1 = _make_site_sessions(4, n_evening=6)
    sess2 = _make_site_sessions(5, n_evening=7)
    sds = build_t2_site_days({"caltech": sess1 + sess2})
    assert len(sds) == 2
    assert pick_site_day(60000, sds) == pick_site_day(60000, sds)
    assert len(T2_CELLS) == 16

    cells = resolve_t2_cells(["F0R_M3_dA2_db0_rho0.95_r0.3"])
    rows_path = tmp_path / "t2_rows.jsonl"
    manifest_path = tmp_path / "t2_manifest.json"
    manifest = run_t2(
        sds,
        [60000, 60001],
        rows_path,
        cells=cells,
        workers=1,
        manifest_path=manifest_path,
    )
    assert manifest["status"] == "complete"
    assert manifest["protocol_sha256"] is not None
    assert manifest["rows_written"] == 2 * 4  # 2 seeds x (bound + 3 policies)
    lines = [json.loads(ln) for ln in rows_path.read_text().splitlines()]
    assert len(lines) == 8
    assert {r["policy"] for r in lines} == {"bound", "ce_llf", "pop_mpc", "guarded_mpc_e1"}
    # Resumability: re-running skips all existing rows
    manifest2 = run_t2(
        sds,
        [60000, 60001],
        rows_path,
        cells=cells,
        workers=1,
        manifest_path=manifest_path,
    )
    assert manifest2["rows_written"] == 0
    assert manifest2["rows_skipped"] == 8
