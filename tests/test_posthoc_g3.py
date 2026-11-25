"""Post hoc G3 additions (development, post hoc): the class-split generator option and its
regression pin, sLLF, the flagged-only floor, the runner's extra-cell plumbing.

Every test uses seeds 60000-60049 only (docs/SEED_LEDGER.md)."""
import hashlib
import json
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from papere import runner
from papere.generator import F0R_CELLS, generate_f0r
from papere.instance import Cell
from papere.ledger import evaluate
from papere.policies.base import PopulationParams
from papere.policies.catalog import FAMILIES
from papere.policies.posthoc import (EXTRA_FAMILIES, FloorFlagged, LLFPop, SmoothedLLF,
                                     round_largest_remainder, smoothed_rates)
from papere.policies.rules import PriorityRule, base_belief
from papere.sim import simulate

from test_policy_lint import lint_source
from test_rules import static_of, view_at

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
PARAMS = PopulationParams(**json.loads((ROOT / "results" / "population_params.json")
                                       .read_text())["values"])
FAM = {f.name: f for f in FAMILIES}
EXTRA = {f.name: f for f in EXTRA_FAMILIES}
BASE = Cell(family="F0R", M=3, delta_A=2, delta_b=0, rho=0.95, r=0.3)
SPLITS = [(0.15, 0.88), (0.5, 0.27)]

FIELDS = ["P", "E", "a", "d", "group", "L", "b_mean", "announced", "prior_A", "prior_stuck",
          "cls", "q", "b", "v", "u"]


def instance_hash(inst) -> str:
    m = hashlib.sha256()
    for f in FIELDS:
        a = np.ascontiguousarray(getattr(inst, f))
        m.update(f.encode())
        m.update(str(a.dtype).encode())
        m.update(str(a.shape).encode())
        m.update(a.tobytes())
    m.update(inst.avail_mode.encode())
    m.update(repr(inst.r).encode())
    return m.hexdigest()


# ------------------------------------------------------------- generator: regression pin
def test_default_instances_are_byte_identical_to_before_the_split_option():
    """Hashes taken from the generator before the class-split option was added (all 22 F0-R
    cells, the deterministic, i.i.d. and SCALE variants, seeds 60000, 60017, 60049)."""
    golden = json.loads((ROOT / "tests" / "golden_instance_hashes.json").read_text())
    cells = list(F0R_CELLS)
    cells += [replace(F0R_CELLS[12], deterministic=True),
              replace(F0R_CELLS[12], homogeneous_iid=True),
              replace(F0R_CELLS[12], family="SCALE")]
    n = 0
    for c in cells:
        for s in (60000, 60017, 60049):
            N = 300 if c.family == "SCALE" else 30
            key = f"{c.cell_id}|{c.family}|{s}"
            assert instance_hash(generate_f0r(s, c, N=N)) == golden[key], key
            n += 1
    assert n == len(golden) == 75


def test_cell_ids_unchanged_without_a_split():
    assert BASE.cell_id == "F0R_M3_dA2_db0_rho0.95_r0.3"
    assert replace(BASE, intol_share=0.15, q_intol=0.88).cell_id == \
        "F0R_M3_dA2_db0_rho0.95_r0.3_split0.15_q0.88"


def test_split_must_be_set_together_and_not_on_kcopy():
    with pytest.raises(ValueError):
        Cell(family="F0R", intol_share=0.5)
    with pytest.raises(ValueError):
        Cell(family="F0R", q_intol=0.5)
    with pytest.raises(ValueError):
        Cell(family="KCOPY", intol_share=0.5, q_intol=0.3)
    with pytest.raises(ValueError):
        Cell(family="F0R", intol_share=1.0, q_intol=0.3)


# ------------------------------------------------------------------ generator: the split
def test_baseline_split_given_explicitly_equals_the_default_instance():
    c = replace(BASE, intol_share=1 / 3, q_intol=0.40)
    for s in (60000, 60011, 60049):
        assert instance_hash(generate_f0r(s, c)) == instance_hash(generate_f0r(s, BASE))


@pytest.mark.parametrize("share,q", SPLITS)
def test_split_classes_and_q_values(share, q):
    cell = replace(BASE, intol_share=share, q_intol=q)
    counts = []
    for s in range(60000, 60050):
        inst = generate_f0r(s, cell)
        n_int = int((inst.cls == 1).sum())
        counts.append(n_int)
        assert set(np.unique(inst.q)) <= {q, 0.01}
        assert (inst.q[inst.cls == 1] == q).all() and (inst.q[inst.cls == 0] == 0.01).all()
        assert abs(n_int - 30 * share) < 1.0
        # everything but the classes and what depends on them is the default draw
        ref = generate_f0r(s, BASE)
        for f in ("P", "E", "a", "d", "L", "b", "v", "u"):
            assert np.array_equal(getattr(inst, f), getattr(ref, f))
    if share == 0.5:
        assert set(counts) == {15}
    else:                                   # 4.5 intolerant of 30: dithered between 4 and 5
        assert set(counts) == {4, 5}
        assert abs(np.mean(counts) - 4.5) < 0.6


@pytest.mark.parametrize("share,q", SPLITS)
def test_split_keeps_the_mean_stuck_probability_near_0_14(share, q):
    cell = replace(BASE, intol_share=share, q_intol=q)
    means = [generate_f0r(s, cell).q.mean() for s in range(60000, 60050)]
    assert abs(np.mean(means) - 0.14) < 0.005, np.mean(means)
    assert abs(share * q + (1 - share) * 0.01 - 0.14) < 0.001           # the nominal mean


def test_class_sets_are_nested_across_splits():
    """The class permutation is shared, so a smaller share is a subset of a larger one."""
    for s in (60003, 60021, 60040):
        a = generate_f0r(s, replace(BASE, intol_share=0.15, q_intol=0.88)).cls == 1
        b = generate_f0r(s, BASE).cls == 1
        c = generate_f0r(s, replace(BASE, intol_share=0.5, q_intol=0.27)).cls == 1
        assert (a <= b).all() and (b <= c).all()


# ---------------------------------------------------------------------------------- sLLF
def test_sllf_serves_the_zero_laxity_participant_first():
    # laxities at t = 0: p0 (d=2, b=2, P=1) 0; p1 (d=6, b=6, P=2) 3; p2 (d=6, b=2, P=2) 5
    sv = static_of(E=[2, 6, 2], P=[1, 2, 2], a=[0] * 3, d=[2, 6, 6], H=6,
                   L=np.full((1, 6), 1.0))
    p = SmoothedLLF()
    p.reset(sv, np.random.default_rng(0))
    assert p.act(view_at(sv, 0)).tolist() == [1, 0, 0]               # cap 1: the zero-laxity one
    sv2 = static_of(E=[2, 6, 2], P=[1, 2, 2], a=[0] * 3, d=[2, 6, 6], H=6,
                    L=np.full((1, 6), 2.0))
    p.reset(sv2, np.random.default_rng(0))
    assert p.act(view_at(sv2, 0)).tolist() == [1, 1, 0]              # next, laxity 3 before 5


def test_sllf_smooths_instead_of_serving_in_index_order():
    # two identical participants, cap 3, P = 2: LLF would give (2, 1) by tie break; the real
    # solution is 1.5 each and the extra unit goes to either, by the rng and never by index
    sv = static_of(E=[8, 8], P=[2, 2], a=[0, 0], d=[10, 10], H=10, L=np.full((1, 10), 3.0))
    seen = set()
    for seed in range(40):
        p = SmoothedLLF()
        p.reset(sv, np.random.default_rng(seed))
        seen.add(tuple(p.act(view_at(sv, 0)).tolist()))
    assert seen == {(2, 1), (1, 2)}
    # unequal laxity: p0 is tighter, so it is served more than p1 even though both are fractional
    sv = static_of(E=[8, 6], P=[2, 2], a=[0, 0], d=[5, 10], H=10, L=np.full((1, 10), 3.0))
    p = SmoothedLLF()
    p.reset(sv, np.random.default_rng(0))
    assert p.act(view_at(sv, 0)).tolist() == [2, 1]


def test_smoothed_rates_equalize_post_slot_laxity_by_hand():
    # l = (0, 0), P = (1, 1), b large, cap 1: rates 0.5 each, post-slot laxity l - 1 + r/P = -0.5
    r = smoothed_rates(np.array([0.0, 0.0]), np.array([1, 1]), np.array([5, 5]), 1)
    assert np.allclose(r, [0.5, 0.5])
    # l = (0, 1.5): the looser one waits until the post-slot laxities meet
    r = smoothed_rates(np.array([0.0, 1.5]), np.array([1, 1]), np.array([5, 5]), 1)
    assert np.allclose(r, [1.0, 0.0])
    r = smoothed_rates(np.array([0.0, 0.5]), np.array([1, 1]), np.array([5, 5]), 1)
    assert np.allclose(r, [0.75, 0.25])


def test_sllf_rates_feasible_and_maxmin_on_random_inputs():
    rng = np.random.default_rng(60007)
    for _ in range(300):
        n = int(rng.integers(1, 12))
        P = rng.integers(1, 4, size=n)
        b = rng.integers(1, 13, size=n)
        d = rng.integers(1, 20, size=n)
        lax = d - b / P
        cap = int(rng.integers(0, 3 * n + 1))
        room = np.minimum(P, b)
        r = smoothed_rates(lax, P, b, cap)
        T = min(cap, int(room.sum()))
        assert (r >= -1e-12).all() and (r <= room + 1e-9).all()
        assert abs(r.sum() - T) < 1e-6
        x = round_largest_remainder(r, room, T, rng.permutation(n))
        assert x.dtype == np.int64 and (x >= 0).all() and (x <= room).all()
        assert x.sum() == T
        assert (np.abs(x - r) < 1.0 + 1e-9).all()              # each unit within one of its rate
        # max-min: no other feasible allocation has a higher minimum post-slot laxity
        post = lax - 1 + r / P
        for _ in range(5):
            alt = rng.random(n) * room
            if alt.sum() > T:
                alt *= T / alt.sum()
            assert (lax - 1 + alt / P).min() <= post.min() + 1e-6


@pytest.mark.parametrize("dA", [0, 1, 2, 4])
def test_sllf_never_exceeds_caps_or_rates_in_the_simulator(dA):
    cell = Cell(family="F0R", M=3, delta_A=dA, delta_b=0, rho=1.15, r=0.3)
    for seed in range(60000, 60006):
        inst = generate_f0r(seed, cell)
        traj = simulate(inst, cell, SmoothedLLF(), seed)   # the simulator raises on a breach
        assert (traj.x <= inst.P[:, None]).all() and (traj.x >= 0).all()
        t = np.arange(inst.H)
        outside = ~((inst.a[:, None] <= t[None, :]) & (t[None, :] < inst.d[:, None]))
        assert (traj.x[outside] == 0).all()
        ev = evaluate(inst, traj)
        assert ev["R_avoid_sp_u"] >= 0


def test_sllf_is_deterministic_given_its_stream():
    cell = replace(BASE, delta_A=1)
    inst = generate_f0r(60005, cell)
    a = simulate(inst, cell, SmoothedLLF(), 60005)
    b = simulate(inst, cell, SmoothedLLF(), 60005)
    assert np.array_equal(a.x, b.x)


def _nc1_exact(seed):
    from negative_controls import NC1_CELL, exact_base_instance
    return NC1_CELL, exact_base_instance(generate_f0r(seed, NC1_CELL))


def test_sllf_reaches_zero_on_nc1_exact_where_ce_llf_does_not():
    """NC1-exact: deterministic availability, constant noise-free base load (the forecast is
    exact), rho = 0.7. A feasible schedule exists; LLF can miss it under the shared cap, sLLF
    (which maximizes the minimum laxity) reaches R_avoid = 0 on all 50 tuning seeds."""
    from papere.runner import load_params
    params = load_params(ROOT / "results" / "population_params.json")
    ce = FAM["ce_llf"]
    n_sllf = n_ce = 0
    for seed in range(60000, 60050):
        cell, inst = _nc1_exact(seed)
        for pol, tag in ((SmoothedLLF(), "sllf"), (ce.make(dict(ce.default), params), "ce")):
            ev = evaluate(inst, simulate(inst, cell, pol, seed))
            if ev["R_avoid_u"] != 0:
                if tag == "sllf":
                    n_sllf += 1
                else:
                    n_ce += 1
    assert n_sllf == 0
    assert n_ce == 22                                      # NC_REPORT: ce_llf misses on 22 of 50


def test_sllf_reaches_zero_when_the_cap_does_not_bind():
    cell = Cell(family="F0R", M=3, delta_A=0, delta_b=0, rho=0.2, r=0.3, deterministic=True)
    for seed in range(60000, 60010):
        inst = generate_f0r(seed, cell)
        ev = evaluate(inst, simulate(inst, cell, SmoothedLLF(), seed))
        assert ev["R_avoid_u"] <= 0 and ev["deadline_miss_count"] == 0


# ------------------------------------------------------------------------ flagged floor
def test_floor_flagged_floors_exactly_the_flagged_participants():
    cell = replace(BASE, M=3)
    for seed in (60001, 60013, 60044):
        inst = generate_f0r(seed, cell)
        pol = FloorFlagged(base_belief("CE"), "LLF", 0, 0, name="floor_flagged")
        traj = simulate(inst, cell, pol, seed)
        flagged = inst.prior_stuck.any(axis=1)
        assert np.array_equal(traj.floored, flagged)
        ev = evaluate(inst, traj)
        assert ev["event_shortfall_u"] == 2 * int(flagged.sum())
        assert ev["floored_count"] == int(flagged.sum())
    m0 = replace(BASE, M=0)
    inst = generate_f0r(60001, m0)
    pol = FloorFlagged(base_belief("CE"), "LLF", 0, 0, name="floor_flagged")
    assert not simulate(inst, m0, pol, 60001).floored.any()


def test_floor_flagged_equals_floor_when_everyone_is_flagged():
    sv = static_of(E=[4, 3, 5], P=[2, 1, 2], a=[0] * 3, d=[6, 5, 8], H=8,
                   L=np.full((1, 8), 3.0), prior_stuck=np.ones((3, 2), bool), M=2)
    v = view_at(sv, 2, x=np.array([[1, 1, 0, 0, 0, 0, 0, 0]] * 3))
    a = PriorityRule(base_belief("CE"), "LLF", 0, 0, name="f", floor=True)
    b = FloorFlagged(base_belief("CE"), "LLF", 0, 0, name="f")
    for pol in (a, b):
        pol.reset(sv, np.random.default_rng(3))
    assert np.array_equal(a.floor_mask(sv), b.floor_mask(sv))
    assert np.array_equal(a.act(v), b.act(v))


# ------------------------------------------------------------------------------ llf_pop
def test_llf_pop_uses_the_llf_post_frozen_configuration_per_cell():
    frozen = json.loads((ROOT / "results" / "TUNING_FROZEN.json").read_text())
    fams = runner.load_families(list(FAMILIES) + list(EXTRA_FAMILIES))
    for dA in (0, 1, 2, 4):
        for rho in (0.95, 1.15):
            cell = replace(BASE, delta_A=dA, rho=rho)
            u = {x[0]: x for x in runner.plan_units(fams, "frozen", cell, frozen,
                                                    {"llf_pop", "llf_post"})}
            assert u["llf_pop"][2:] == u["llf_post"][2:] == (
                "llf_post", frozen["llf_post"][cell.cell_id]["config_index"])


def test_llf_pop_belief_is_the_population_rate_and_otherwise_llf_post():
    inst = generate_f0r(60003, BASE)
    sv = static_of(E=[4, 3, 5], P=[2, 1, 2], a=[0] * 3, d=[6, 5, 8], H=8,
                   prior_stuck=np.array([[1, 1], [0, 0], [0, 1]], bool), M=2)
    cfg = dict(EXTRA["llf_pop"].default)
    pop = EXTRA["llf_pop"].make(cfg, PARAMS)
    post = FAM["llf_post"].make(cfg, PARAMS)
    assert isinstance(pop, LLFPop) and pop.hmm.mode == "population" and post.hmm.mode == "e1"
    for pol in (pop, post):
        pol.reset(sv, np.random.default_rng(0))
    assert np.ptp(pop.hmm.q) == 0.0 and np.ptp(post.hmm.q) > 0.0
    assert (pop.theta, pop.order, pop.m, pop.k) == (post.theta, post.order, post.m, post.k)
    assert inst is not None


@pytest.mark.parametrize("dA,rho", [(0, 0.95), (2, 0.95), (4, 1.15), (1, 1.15)])
def test_llf_pop_equals_llf_post_at_m0_decision_for_decision(dA, rho):
    """At M = 0 the e1 and population rates coincide (POLICY_SPEC 3.2): same actions, same
    random streams, so identical trajectories under any configuration (here the cell's
    frozen llf_post configuration, taken from a cell that has M = 3, and a theta > 0 one)."""
    frozen = json.loads((ROOT / "results" / "TUNING_FROZEN.json").read_text())
    cell = replace(BASE, M=0, delta_A=dA, rho=rho)
    cfg = dict(frozen["llf_post"][replace(BASE, delta_A=dA, rho=rho).cell_id]["config"])
    for c in (cfg, {"O": "LLF", "theta": 0.05, "m": 1, "k": 2}):
        for seed in (60000, 60007, 60021, 60048):
            inst = generate_f0r(seed, cell)
            a = simulate(inst, cell, EXTRA["llf_pop"].make(c, PARAMS), seed)
            b = simulate(inst, cell, FAM["llf_post"].make(c, PARAMS), seed)
            assert np.array_equal(a.x, b.x), (c, seed)


# ---------------------------------------------------------------- catalog and runner glue
def test_catalog_is_untouched_and_extra_families_are_separate():
    assert len(FAMILIES) == 17 and {"sllf", "floor_flagged", "llf_pop"}.isdisjoint(FAM)
    assert set(EXTRA) == {"sllf", "floor_flagged", "llf_pop"}
    assert EXTRA["llf_pop"].tuned_from == "llf_post" and not EXTRA["llf_pop"].tunable
    assert EXTRA["llf_pop"].kind == "oblivious"
    assert EXTRA["floor_flagged"].tuned_from == "floor" and not EXTRA["sllf"].tunable
    assert not EXTRA["floor_flagged"].tunable


def test_posthoc_module_passes_the_lint():
    p = ROOT / "src" / "papere" / "policies" / "posthoc.py"
    assert lint_source(p.read_text(), "papere.policies.posthoc") == []


def test_split_cells_use_the_baseline_frozen_configuration():
    split = replace(BASE, intol_share=0.5, q_intol=0.27)
    assert runner.f0r_cell_id(split) == BASE.cell_id
    assert runner.f0r_cell_id(replace(split, family="SCALE")) == BASE.cell_id
    frozen = json.loads((ROOT / "results" / "TUNING_FROZEN.json").read_text())
    fams = runner.load_families(list(FAMILIES) + list(EXTRA_FAMILIES))
    u = runner.plan_units(fams, "frozen", split, frozen, {"floor_flagged", "sllf", "mpc_ce"})
    by = {x[0]: x for x in u}
    idx = frozen["floor"][BASE.cell_id]["config_index"]
    assert by["floor_flagged"] == ("floor_flagged", "floor_flagged", "floor", idx)
    assert by["mpc_ce"][3] == frozen["mpc_ce"][BASE.cell_id]["config_index"]
    assert by["sllf"][2] == "sllf"


def test_extra_cells_are_selectable_by_id_only():
    split = replace(BASE, intol_share=0.5, q_intol=0.27)
    with pytest.raises(runner.RunnerError):
        runner._resolve_cells("F0R", [split.cell_id], runner.study_cells("F0R"))
    got = runner._resolve_cells("F0R", [split.cell_id], runner.study_cells("F0R") + [split])
    assert got == [split]


# ------------------------------------------------------------- the committed numbers file
def _numbers():
    d = json.loads((ROOT / "results" / "posthoc_g3_runs.json").read_text())
    return d["meta"], d["numbers"]


def test_posthoc_numbers_schema_label_and_provenance():
    meta, nums = _numbers()
    label = "development, post hoc, added after the G3 review"
    assert meta["label"] == label and meta["git"]["dirty"] is False
    assert meta["bootstrap"]["n_boot"] == 10000 and meta["bootstrap"]["seed"] == 20261020
    assert len(nums) == 234
    need = {"value", "ci_lo", "ci_hi", "n_seeds", "label", "unit", "statistic", "cell_id"}
    for k, v in nums.items():
        assert k.startswith("posthoc_runs/") and need <= set(v) and v["label"] == label, k
        assert v["n_seeds"] == 100
    for rho in ("0.95", "1.15"):
        for d in (0, 1, 2, 4):
            b = f"posthoc_runs/sllf/M3_rho{rho}/dA{d}"
            for suffix in ("R_avoid_sllf", "R_avoid_ce_llf", "planning_sllf",
                           "sllf_minus_cellf", "deadline_miss_count_per100_sllf"):
                assert f"{b}/{suffix}" in nums
        for split in ("split0.15_q0.88", "split0.333_q0.4", "split0.5_q0.27"):
            for t in ("hedging", "targeting", "oracle_targeting", "total_mpcce",
                      "recovery_share"):
                assert f"posthoc_runs/het/{split}/M3_rho{rho}/dA2/{t}" in nums
        for d in (2, 4):
            for t in ("event_shortfall", "net_recovery_gain_vs_best_oblivious",
                      "floor_all_event_shortfall", "floor_all_net_recovery_gain"):
                assert f"posthoc_runs/floor_flagged/M3_rho{rho}/dA{d}/{t}" in nums
            assert (f"posthoc_runs/floor_flagged/M3_rho{rho}/dA{d}/candidate_minus_floor_flagged"
                    in nums)
            note = nums[f"posthoc_runs/floor_flagged/M3_rho{rho}/dA{d}/"
                        "candidate_minus_floor_flagged"]["note"]
            assert "never stuck" in note and "R*" in note
        for d in (0, 1, 2, 4):
            for t in ("belief_ce_to_pop_in_llf", "belief_pop_to_e1_in_llf",
                      "belief_ce_to_pop_in_mpc", "belief_pop_to_e1_in_mpc",
                      "rule_llf_to_mpc_given_ce", "rule_llf_to_mpc_given_pop",
                      "rule_llf_to_mpc_given_e1"):
                assert f"posthoc_runs/factorial/M3_rho{rho}/dA{d}/{t}" in nums


def test_factorial_gains_are_consistent_with_the_cell_means():
    """Gain convention: each factorial key is the difference of two means of the cell; the
    point values are linear, so they must equal the difference of the stored R_avoid means or,
    for llf_pop and llf_post (no stored mean), satisfy the 2 x 3 additivity identity."""
    _, nums = _numbers()
    for rho in ("0.95", "1.15"):
        for d in (0, 1, 2, 4):
            f = lambda t: nums[f"posthoc_runs/factorial/M3_rho{rho}/dA{d}/{t}"]["value"]
            b = f"posthoc_runs/sllf/M3_rho{rho}/dA{d}"
            m = lambda p: nums[f"{b}/R_avoid_{p}"]["value"]
            assert f("belief_ce_to_pop_in_mpc") == pytest.approx(m("mpc_ce") - m("pop_mpc"))
            assert f("belief_pop_to_e1_in_mpc") == pytest.approx(
                m("pop_mpc") - m("guarded_mpc_e1"))
            assert f("rule_llf_to_mpc_given_ce") == pytest.approx(m("ce_llf") - m("mpc_ce"))
            # the two ways around the square agree (CE-LLF -> E1-MPC)
            via_llf = (f("belief_ce_to_pop_in_llf") + f("belief_pop_to_e1_in_llf")
                       + f("rule_llf_to_mpc_given_e1"))
            via_mpc = f("rule_llf_to_mpc_given_ce") + f("belief_ce_to_pop_in_mpc") + f(
                "belief_pop_to_e1_in_mpc")
            assert via_llf == pytest.approx(via_mpc)
            assert f("rule_llf_to_mpc_given_pop") == pytest.approx(
                f("rule_llf_to_mpc_given_ce") - f("belief_ce_to_pop_in_llf")
                + f("belief_ce_to_pop_in_mpc"))


def test_posthoc_numbers_agree_with_paper_numbers_where_they_overlap():
    """Floor (everyone) and the baseline split are the same rows' statistics as before."""
    _, nums = _numbers()
    pn = json.loads((ROOT / "results" / "paper_numbers.json").read_text())["numbers"]
    for rho in ("0.95", "1.15"):
        for d in (2, 4):
            c = f"F0R_M3_dA{d}_db0_rho{rho}_r0.3"
            a = pn[f"secondary/floor/{c}/net_recovery_gain"]
            b = nums[f"posthoc_runs/floor_flagged/M3_rho{rho}/dA{d}/floor_all_net_recovery_gain"]
            assert (a["value"], a["ci_lo"], a["ci_hi"]) == (b["value"], b["ci_lo"], b["ci_hi"])
        for t, lay in (("hedging", "hedging"), ("targeting", "targeting"),
                       ("oracle_targeting", "oracle_targeting")):
            a = pn[f"layers/M3_rho{rho}/dA2/{lay}"]
            b = nums[f"posthoc_runs/het/split0.333_q0.4/M3_rho{rho}/dA2/{t}"]
            assert abs(a["value"] - b["value"]) < 1e-9
            assert abs(a["ci_lo"] - b["ci_lo"]) < 1e-9 and abs(a["ci_hi"] - b["ci_hi"]) < 1e-9
