"""Tests for post hoc round 3 (M6 guard ablation and M3 failure persistence).

Every instance/simulation test uses tuning seeds 60000-60049 only (with ``conftest.draw``
salts for large draws), complying with ``tests/test_seed_rule.py``.
"""
from __future__ import annotations

from dataclasses import replace
from datetime import date
import json
from pathlib import Path

import numpy as np
import pytest

from conftest import draw
from papere import runner
from papere.acn.analyse import load_rows_file
from papere.acn.instances import (
    _ACN_STREAM_IDS,
    T2SiteDayData,
    build_acn_instance,
)
from papere.acn.run_t2 import run_t2
from papere.analysis import Bootstrap
from papere.generator import (
    _STREAM_IDS,
    M_MAX,
    _evolve_classes,
    generate_f0r,
    stream,
)
from papere.instance import Cell
from papere.ledger import evaluate
from papere.policies.base import PopulationParams
from papere.policies.catalog import ABLATION_BY_NAME, FAMILIES
from papere.posthoc_round3 import (
    ClusteredBootstrap,
    M3_BOOT_SEED,
    M6_BOOT_SEED,
    analyse_m3_rows,
    analyse_m6_rows,
    m3_cells,
    m6_cells,
)
from papere.sim import simulate

ROOT = Path(__file__).resolve().parents[1]
PARAMS_DATA = json.loads((ROOT / "results" / "population_params.json").read_text())
PARAMS = PopulationParams(**PARAMS_DATA["values"])
FROZEN = json.loads((ROOT / "results" / "TUNING_FROZEN.json").read_text())
FAM = {f.name: f for f in FAMILIES}

BASE_REF = Cell(family="F0R", M=3, delta_A=2, delta_b=0, rho=0.95, r=0.3)
BASE_TIGHT_M6 = Cell(family="F0R", M=3, delta_A=2, delta_b=0, rho=1.15, r=0.3)
BASE_TIGHT_M3 = Cell(family="F0R", M=3, delta_A=4, delta_b=0, rho=1.15, r=0.3)

INSTANCE_FIELDS = (
    "P", "E", "a", "d", "group", "L", "b_mean", "announced",
    "prior_A", "prior_stuck", "cls", "q", "b", "v", "u",
)


def _dummy_site_day(n: int = 12, site: str = "caltech", day: int = 4) -> T2SiteDayData:
    return T2SiteDayData(
        site=site,
        local_date=date(2019, 11, day),
        timezone="America/Los_Angeles",
        n_cleaned_sessions=20,
        session_ids=tuple(f"s{i}" for i in range(n)),
        E=np.array([4 + (i % 7) for i in range(n)], dtype=np.int64),
        P=np.full(n, 6, dtype=np.int64),
        a=np.zeros(n, dtype=np.int64),
        d=np.array([2 + (i % 10) for i in range(n)], dtype=np.int64),
    )


def _assert_instances_identical(a, b) -> None:
    for field in INSTANCE_FIELDS:
        assert np.array_equal(getattr(a, field), getattr(b, field)), field
    assert a.avail_mode == b.avail_mode
    assert a.r == b.r
    assert np.array_equal(a.availability(), b.availability())


# ------------------------------------------------------------------ s = 0 identity & streams
def test_s0_reproduces_current_instances_exactly():
    sd = _dummy_site_day(n=12)
    for seed in range(60000, 60020):
        ref = generate_f0r(seed, BASE_REF)
        with_cell_s0 = generate_f0r(seed, replace(BASE_REF, redraw_prob=0.0))
        with_kw_s0 = generate_f0r(seed, BASE_REF, redraw_prob=0.0)
        _assert_instances_identical(ref, with_cell_s0)
        _assert_instances_identical(ref, with_kw_s0)
        assert replace(BASE_REF, redraw_prob=0.0).cell_id == BASE_REF.cell_id

        acn_ref = build_acn_instance(seed, BASE_REF, sd)
        acn_cell_s0 = build_acn_instance(seed, replace(BASE_REF, redraw_prob=0.0), sd)
        acn_kw_s0 = build_acn_instance(seed, BASE_REF, sd, redraw_prob=0.0)
        _assert_instances_identical(acn_ref, acn_cell_s0)
        _assert_instances_identical(acn_ref, acn_kw_s0)


def test_new_streams_are_disjoint_and_preserve_crn():
    gen_ids = set(_STREAM_IDS.values())
    acn_ids = set(_ACN_STREAM_IDS.values())
    assert len(gen_ids) == len(_STREAM_IDS)
    assert gen_ids.isdisjoint(acn_ids)
    assert {"redraw_u", "redraw_cls", "beta_q"} <= set(_STREAM_IDS)

    sd = _dummy_site_day(n=15)
    seed = 60011
    ref = generate_f0r(seed, BASE_REF)
    for cell in (
        replace(BASE_REF, redraw_prob=0.2),
        replace(BASE_REF, redraw_prob=0.5),
        replace(BASE_REF, beta_q=(PARAMS.alpha, PARAMS.beta)),
    ):
        alt = generate_f0r(seed, cell)
        for field in ("P", "E", "a", "d", "L", "b_mean", "b", "v", "u", "announced"):
            assert np.array_equal(getattr(ref, field), getattr(alt, field)), (cell.cell_id, field)

        acn_ref = build_acn_instance(seed, BASE_REF, sd)
        acn_alt = build_acn_instance(seed, cell, sd)
        for field in ("P", "E", "a", "d", "L", "b_mean", "b", "v", "u", "announced"):
            assert np.array_equal(getattr(acn_ref, field), getattr(acn_alt, field))

    # Salting the new streams does not disturb any default (s=0) instance
    salted = generate_f0r(seed, BASE_REF, stream_salt={"redraw_u": 7, "redraw_cls": 7, "beta_q": 7})
    _assert_instances_identical(ref, salted)


# ------------------------------------------------------------------ redraw frequency
@pytest.mark.parametrize("s", [0.2, 0.5])
def test_redraw_frequency_close_to_s_on_large_draw(s):
    n_draws = 500
    cell_m0 = replace(BASE_REF, M=0, redraw_prob=s)
    cell_m3 = replace(BASE_REF, M=3, redraw_prob=s)
    base_m0 = replace(BASE_REF, M=0)

    # 1. Direct redraw mask fraction in _evolve_classes over 500 x 30 x 4 = 60,000 events
    redrawn_counts = []
    # 2. End-to-end generator class-change rates at M=0 (1 step) and M=3 (4 steps)
    changed_m0 = []
    changed_m3 = []
    intol_shares = []
    for j in range(n_draws):
        seed, salt = draw(j)
        inst0 = generate_f0r(seed, base_m0, stream_salt=salt)
        inst_m0 = generate_f0r(seed, cell_m0, stream_salt=salt)
        inst_m3 = generate_f0r(seed, cell_m3, stream_salt=salt)

        sl = salt or {}
        ru = stream(seed, "redraw_u", sl.get("redraw_u", 0)).random((30, M_MAX + 1))
        rc = stream(seed, "redraw_cls", sl.get("redraw_cls", 0)).random((30, M_MAX + 1))
        _, sc_cls, redrawn = _evolve_classes(inst0.cls, 3, s, 1.0 / 3.0, ru, rc)
        assert np.array_equal(sc_cls, inst_m3.cls)
        redrawn_counts.append(redrawn.mean())

        changed_m0.append((inst_m0.cls != inst0.cls).mean())
        changed_m3.append((inst_m3.cls != inst0.cls).mean())
        intol_shares.append((inst_m3.cls == 1).mean())

    assert float(np.mean(redrawn_counts)) == pytest.approx(s, abs=0.01)
    # One-step redraw from Bernoulli(1/3) changes class with prob (4/9)*s
    inferred_s_m0 = float(np.mean(changed_m0)) / (4.0 / 9.0)
    assert inferred_s_m0 == pytest.approx(s, abs=0.025)
    # Four-step Markov chain (M=3 prior + 1 scored) changes class with prob (4/9)*(1 - (1-s)^4)
    expected_m3_change = (4.0 / 9.0) * (1.0 - (1.0 - s) ** 4)
    assert float(np.mean(changed_m3)) == pytest.approx(expected_m3_change, abs=0.015)
    # Stationary intolerant share remains 1/3
    assert float(np.mean(intol_shares)) == pytest.approx(1.0 / 3.0, abs=0.015)

    # Also verify ACN builder forwards redraw_prob and updates classes/priors
    sd = _dummy_site_day(n=24)
    acn_changes = []
    for j in range(200):
        seed, salt = draw(j)
        a0 = build_acn_instance(seed, base_m0, sd, stream_salt=salt)
        as_ = build_acn_instance(seed, cell_m0, sd, stream_salt=salt)
        acn_changes.append((as_.cls != a0.cls).mean())
    assert float(np.mean(acn_changes)) / (4.0 / 9.0) == pytest.approx(s, abs=0.04)


# ------------------------------------------------------------------ Beta-q mean & persistence
def test_beta_q_mean_variance_and_persistence():
    alpha, beta = float(PARAMS.alpha), float(PARAMS.beta)
    expected_mean = alpha / (alpha + beta)
    expected_var = (alpha * beta) / (((alpha + beta) ** 2) * (alpha + beta + 1.0))

    cell_bq = replace(BASE_REF, beta_q=(alpha, beta))
    qs = []
    for j in range(500):
        seed, salt = draw(j)
        inst = generate_f0r(seed, cell_bq, stream_salt=salt)
        qs.append(inst.q)
        # Persistent across all M prior events: same q determines prior_stuck
        sl = salt or {}
        pv = stream(seed, "prior_v", sl.get("prior_v", 0)).random((inst.N, M_MAX))
        assert np.array_equal(inst.prior_stuck, pv[:, :cell_bq.M] < inst.q[:, None])
        assert np.all((inst.q >= 0.0) & (inst.q <= 1.0))

    all_q = np.concatenate(qs)
    assert float(all_q.mean()) == pytest.approx(expected_mean, abs=0.008)
    assert float(all_q.var()) == pytest.approx(expected_var, abs=0.005)

    # ACN builder matches the same Beta-q distribution
    sd = _dummy_site_day(n=20)
    acn_qs = [
        build_acn_instance(seed, cell_bq, sd, stream_salt=salt).q
        for seed, salt in (draw(j) for j in range(300))
    ]
    assert float(np.concatenate(acn_qs).mean()) == pytest.approx(expected_mean, abs=0.01)


def test_persistence_validation_errors():
    with pytest.raises(ValueError):
        Cell(family="F0R", redraw_prob=-0.1)
    with pytest.raises(ValueError):
        Cell(family="F0R", redraw_prob=1.2)
    with pytest.raises(ValueError):
        Cell(family="KCOPY", delta_A=2, redraw_prob=0.2)
    with pytest.raises(ValueError):
        Cell(family="F0R", beta_q=(-0.1, 1.0))
    with pytest.raises(ValueError):
        Cell(family="F0R", redraw_prob=0.2, beta_q=(0.3, 1.8))
    sd = _dummy_site_day(n=8)
    with pytest.raises(ValueError):
        build_acn_instance(60000, replace(BASE_REF, redraw_prob=0.2), sd, emp_beta_ab=(0.3, 1.8))


# ------------------------------------------------------------------ gamma = 0 ablation
@pytest.mark.parametrize("cell", [BASE_REF, BASE_TIGHT_M6], ids=lambda c: c.cell_id)
def test_gamma0_variant_equals_existing_gamma0_code_path(cell):
    assert len(FAMILIES) == 17  # base catalog untouched
    assert "guarded_mpc_e1_g0" in ABLATION_BY_NAME
    g0_fam = ABLATION_BY_NAME["guarded_mpc_e1_g0"]
    assert g0_fam.tuned_from == "guarded_mpc_e1"
    assert not g0_fam.tunable

    frozen_cfg = dict(FROZEN["guarded_mpc_e1"][cell.cell_id]["config"])
    assert frozen_cfg["gamma"] > 0.0  # ablation is active on both M6 cells
    direct_g0_cfg = {**frozen_cfg, "gamma": 0.0}

    for seed in range(60000, 60008):
        inst = generate_f0r(seed, cell)
        pol_ablation = g0_fam.make(frozen_cfg, PARAMS)
        pol_direct = FAM["guarded_mpc_e1"].make(direct_g0_cfg, PARAMS)
        assert pol_ablation.gamma == 0.0
        assert (pol_ablation.W, pol_ablation.m, pol_ablation.k) == (
            frozen_cfg["W"], float(frozen_cfg["m"]), 0
        )

        tr_abl = simulate(inst, cell, pol_ablation, seed)
        tr_dir = simulate(inst, cell, pol_direct, seed)
        assert np.array_equal(tr_abl.x, tr_dir.x)
        assert np.array_equal(tr_abl.y, tr_dir.y)
        assert np.array_equal(tr_abl.r_final, tr_dir.r_final)
        assert np.array_equal(tr_abl.A, tr_dir.A)
        assert np.array_equal(tr_abl.rounds, tr_dir.rounds)

        ev_abl = evaluate(inst, tr_abl)
        ev_dir = evaluate(inst, tr_dir)
        assert ev_abl["R_avoid_kwh_per100"] == pytest.approx(ev_dir["R_avoid_kwh_per100"])
        assert ev_abl["deadline_miss_count_per100"] == pytest.approx(ev_dir["deadline_miss_count_per100"])


def test_gamma0_and_persistence_work_in_both_runners(tmp_path):
    # Verify f0r_cell_id strips persistence options for frozen config lookup
    c_red = replace(BASE_REF, redraw_prob=0.2)
    c_bq = replace(BASE_TIGHT_M3, beta_q=(PARAMS.alpha, PARAMS.beta))
    assert runner.f0r_cell_id(c_red) == BASE_REF.cell_id
    assert runner.f0r_cell_id(c_bq) == BASE_TIGHT_M3.cell_id

    # Synthetic runner with guarded_mpc_e1_g0 (auto-resolved without passing families)
    synth_out = tmp_path / "synth_m6"
    res = runner.run(
        "F0R",
        (60000, 60001),
        synth_out,
        mode="frozen",
        policies=["guarded_mpc_e1", "guarded_mpc_e1_g0"],
        cell_ids=[BASE_REF.cell_id],
        workers=1,
        open_ranges={("F0R", "frozen"): (60000, 60001)},
        allow_dirty=True,
    )
    assert res["rows_written"] == 2 * 3  # 2 seeds x (bound + 2 policies)
    rows = load_rows_file(synth_out / "rows.jsonl")
    assert {r["policy"] for r in rows} == {"bound", "guarded_mpc_e1", "guarded_mpc_e1_g0"}

    # ACN runner with guarded_mpc_e1_g0 and persistence cells
    sds = [_dummy_site_day(n=8, site="caltech", day=4), _dummy_site_day(n=9, site="jpl", day=5)]
    acn_m6_path = tmp_path / "acn_m6.jsonl"
    man_m6 = run_t2(
        sds,
        [60000, 60001],
        acn_m6_path,
        cells=[BASE_REF],
        policies=("guarded_mpc_e1", "guarded_mpc_e1_g0"),
        workers=1,
    )
    assert man_m6["rows_written"] == 2 * 3

    acn_m3_path = tmp_path / "acn_m3.jsonl"
    man_m3 = run_t2(
        sds,
        [60000, 60001],
        acn_m3_path,
        cells=[c_red, c_bq],
        policies=("ce_llf", "pop_mpc", "guarded_mpc_e1"),
        workers=1,
    )
    assert man_m3["rows_written"] == 2 * 2 * 4  # 2 seeds x 2 cells x (bound + 3 policies)


# ------------------------------------------------------------------ analysis & clustered bootstrap
def test_clustered_bootstrap_singleton_matches_plain_and_handles_clusters():
    rng = np.random.default_rng(123)
    x = rng.normal(5.0, 2.0, size=20)
    y = rng.normal(3.0, 1.5, size=20)

    plain = Bootstrap(n_boot=2000, seed=M6_BOOT_SEED, level=0.95)
    clust = ClusteredBootstrap(n_boot=2000, seed=M6_BOOT_SEED, level=0.95)

    r_plain = plain.run({"d": x - y}, {"m": lambda m: m["d"]})["m"]
    r_none = clust.run({"d": x - y}, {"m": lambda m: m["d"]}, clusters=None)["m"]
    assert r_none == r_plain

    # Distinct clusters in sorted order: exact match with plain Bootstrap
    singleton_clusters = [(f"site_{i:02d}", "2019-11-04") for i in range(20)]
    r_sing = clust.run({"d": x - y}, {"m": lambda m: m["d"]}, clusters=singleton_clusters)["m"]
    assert r_sing.value == pytest.approx(r_plain.value)
    assert r_sing.lo == pytest.approx(r_plain.lo)
    assert r_sing.hi == pytest.approx(r_plain.hi)

    # Identical repeated observations inside 4 clusters -> clustered CI is wider than naive
    base_vals = np.array([0.0, 2.0, 8.0, 10.0])
    rep_vals = np.repeat(base_vals, 5)
    rep_clusters = [(f"s{i}", "2019-11-04") for i in range(4) for _ in range(5)]
    st_naive = plain.run({"v": rep_vals}, {"m": lambda m: m["v"]})["m"]
    st_clust = clust.run({"v": rep_vals}, {"m": lambda m: m["v"]}, clusters=rep_clusters)["m"]
    assert st_clust.value == pytest.approx(5.0)
    assert (st_clust.hi - st_clust.lo) > (st_naive.hi - st_naive.lo)

    # Single cluster returns point estimate with NaN interval
    st_one = clust.run(
        {"v": rep_vals},
        {"m": lambda m: m["v"]},
        clusters=[("only", "2019-11-04")] * len(rep_vals),
    )["m"]
    assert st_one.value == pytest.approx(5.0)
    assert np.isnan(st_one.lo) and np.isnan(st_one.hi)


def test_analyse_m6_and_m3_on_tiny_rows_files(tmp_path):
    # Tiny M6 rows file (real-data style with repeated site-days)
    m6_rows = []
    clusters = [("caltech", "2019-11-04"), ("caltech", "2019-11-05"), ("jpl", "2019-11-04")]
    for idx, seed in enumerate(range(60000, 60012)):
        site, dt = clusters[idx % len(clusters)]
        for _, cell in m6_cells():
            cid = cell.cell_id
            base_miss = 10.0
            m6_rows.append({
                "mode": "frozen", "study_family": "F0R", "seed": seed, "cell_id": cid,
                "policy": "bound", "site": site, "date": dt, "N": 20,
                "R_avoid_kwh_per100": 0.0, "deadline_miss_count_per100": base_miss,
                "bound_short_count": 2,
            })
            # Guard on has R_avoid = 4.0, misses = 30.0; guard off has R_avoid = 5.5, misses = 35.0
            # Guard on minus guard off = -1.5 kWh/100 and -5.0 misses/100 (exact across seeds)
            jitter = float(idx % 3) * 0.1
            m6_rows.append({
                "mode": "frozen", "study_family": "F0R", "seed": seed, "cell_id": cid,
                "policy": "guarded_mpc_e1", "site": site, "date": dt, "N": 20,
                "R_avoid_kwh_per100": 4.0 + jitter, "deadline_miss_count_per100": 30.0 + jitter,
                "bound_short_count": 2,
            })
            m6_rows.append({
                "mode": "frozen", "study_family": "F0R", "seed": seed, "cell_id": cid,
                "policy": "guarded_mpc_e1_g0", "site": site, "date": dt, "N": 20,
                "R_avoid_kwh_per100": 5.5 + jitter, "deadline_miss_count_per100": 35.0 + jitter,
                "bound_short_count": 2,
            })

    p_m6 = tmp_path / "m6_tiny.jsonl"
    p_m6.write_text("\n".join(json.dumps(r) for r in m6_rows) + "\n")
    res_m6 = analyse_m6_rows(load_rows_file(p_m6), clustered=True, n_boot=500, boot_seed=M6_BOOT_SEED)
    assert set(res_m6["by_label"]) == {"reference", "tight"}
    ref_m6 = res_m6["by_label"]["reference"]
    assert ref_m6["n_seeds"] == 12
    assert ref_m6["n_clusters"] == 3
    assert ref_m6["R_avoid_kwh_per100"]["guard_on_minus_guard_off"]["value"] == pytest.approx(-1.5)
    assert ref_m6["R_avoid_kwh_per100"]["guard_on_minus_guard_off"]["ci_lo"] == pytest.approx(-1.5)
    assert ref_m6["avoidable_deadline_misses_per100"]["guard_on"]["value"] == pytest.approx(20.1)
    assert ref_m6["avoidable_deadline_misses_per100"]["guard_off"]["value"] == pytest.approx(25.1)
    assert ref_m6["avoidable_deadline_misses_per100"]["guard_on_minus_guard_off"]["value"] == pytest.approx(-5.0)
    assert ref_m6["deadline_miss_count_per100"]["guard_on_minus_guard_off"]["value"] == pytest.approx(-5.0)

    # Tiny M3 rows file across all 4 settings x 2 cells (unclustered synthetic)
    m3_rows = []
    gain_by_setting = {"s0": (4.0, 1.2), "s0.2": (3.5, 0.7), "s0.5": (3.0, 0.1), "beta_q": (4.2, 1.4)}
    for seed in range(60000, 60010):
        for _, setting, cell in m3_cells((PARAMS.alpha, PARAMS.beta)):
            g_ce, g_pop = gain_by_setting[setting]
            targ = 3.0
            for pol, val in (
                ("guarded_mpc_e1", targ),
                ("pop_mpc", targ + g_pop),
                ("ce_llf", targ + g_ce),
            ):
                m3_rows.append({
                    "mode": "frozen", "study_family": "F0R", "seed": seed,
                    "cell_id": cell.cell_id, "policy": pol, "R_avoid_kwh_per100": val,
                })

    p_m3 = tmp_path / "m3_tiny.jsonl"
    p_m3.write_text("\n".join(json.dumps(r) for r in m3_rows) + "\n")
    res_m3 = analyse_m3_rows(load_rows_file(p_m3), clustered=False, n_boot=500, boot_seed=M3_BOOT_SEED)
    assert set(res_m3["by_setting"]) == {"s0", "s0.2", "s0.5", "beta_q"}
    for setting, (g_ce, g_pop) in gain_by_setting.items():
        for lbl in ("reference", "tight"):
            ent = res_m3["by_setting"][setting][lbl]
            assert ent["n_seeds"] == 10
            assert ent["n_clusters"] is None
            assert ent["targeted_gain_over_ce_llf"]["value"] == pytest.approx(g_ce)
            assert ent["targeted_gain_over_pop_mpc"]["value"] == pytest.approx(g_pop)
            assert ent["targeted_gain_over_ce_llf"]["ci_lo"] == pytest.approx(g_ce)
            assert ent["targeted_gain_over_pop_mpc"]["ci_hi"] == pytest.approx(g_pop)
