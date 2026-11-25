"""Ledger tests: hand-computed metrics, the I1 mechanism case, split and bound properties."""
from __future__ import annotations

import json
from dataclasses import replace

import numpy as np
import pytest

from papere.flow import clairvoyant
from papere.generator import F0R_CELLS, generate_f0r
from papere.instance import Cell, Instance
import papere.ledger as ledger_mod
from papere.ledger import BoundViolation, bound_row, clair_for, evaluate, flow_problem
from papere.sim import Trajectory, simulate

from test_sim import i1_instance, schedule_policy


# --------------------------------------------------------------------------- helpers
def arr(x, dtype=np.int64):
    return np.array(x, dtype=dtype)


def make_instance(P, E, a, d, L, b, group=None, delta_A=2) -> Instance:
    """Hand-built single- or multi-group instance; hidden fields are dummies."""
    P, E, a, d = arr(P), arr(E), arr(a), arr(d)
    L, b = np.asarray(L, dtype=float), np.asarray(b, dtype=float)
    N, H = len(P), L.shape[1]
    group = np.zeros(N, dtype=np.int64) if group is None else arr(group)
    cell = Cell(family="F0R", M=0, delta_A=delta_A, delta_b=0)
    return Instance(
        family="F0R", cell=cell, seed=0, N=N, H=H, P=P, E=E, a=a, d=d, group=group, L=L,
        b_mean=b.copy(), announced=np.ones((N, H), dtype=np.int64),
        prior_A=np.ones((N, 0, H), dtype=np.int64), prior_stuck=np.zeros((N, 0), dtype=bool),
        cls=np.zeros(N, dtype=np.int64), q=np.zeros(N), b=b, avail_mode="det", r=0.3,
        v=np.zeros(N), u=np.zeros((N, H)))


def make_traj(inst, x, y, A, floored=None, cpu=None, name="hand") -> Trajectory:
    x, y, A = arr(x), arr(y), arr(A)
    r_before = np.zeros_like(x)
    r = inst.E.astype(np.int64).copy()
    for t in range(inst.H):
        r_before[:, t] = r
        r = r - y[:, t]
    return Trajectory(
        policy=name, privileged=False, seed=0, cell_id=inst.cell.cell_id, x=x, y=y, A=A,
        r_before=r_before, r_final=r,
        floored=np.zeros(inst.N, dtype=bool) if floored is None else np.asarray(floored),
        cpu_ms=np.zeros(inst.H) if cpu is None else np.asarray(cpu, dtype=float),
        rounds=np.ones(inst.H, dtype=np.int64))


def split(m):
    """(R_uncorr_hi, R_uncorr_lo, R_corr_hi, R_corr_lo) in units."""
    return (m["R_uncorr_hi_u"], m["R_uncorr_lo_u"], m["R_corr_hi_u"], m["R_corr_lo_u"])


def hand1():
    """3 participants, H=4. See the derivation in the comments of test_hand_instance."""
    inst = make_instance(P=[2, 1, 1], E=[3, 3, 1], a=[0, 0, 1], d=[3, 4, 4],
                         L=[[3, 3, 3, 3]], b=[[0, 2, 2, 0]])
    A = [[1, 0, 1, 1],
         [1, 1, 0, 1],
         [1, 1, 1, 1]]
    x = [[1, 2, 2, 0],
         [1, 1, 1, 0],
         [0, 1, 1, 1]]
    y = [[1, 0, 2, 0],
         [1, 1, 0, 0],
         [0, 1, 0, 0]]
    return inst, make_traj(inst, x, y, A, cpu=[1.0, 3.0, 2.0, 2.0])


# --------------------------------------------------------------------------- flow_problem
def test_flow_problem_cap_group_slotcap_base():
    inst, traj = hand1()
    fp = flow_problem(inst, traj.A)
    # cap = P*A inside [a, d), 0 outside: p0 window 0..2, p1 0..3, p2 1..3
    assert fp.cap.tolist() == [[2, 0, 2, 0], [1, 1, 0, 1], [0, 1, 1, 1]]
    assert fp.slot_cap.tolist() == [[3, 1, 1, 3]]
    assert fp.base.tolist() == [[0, 2, 2, 0]]
    assert fp.E.tolist() == [3, 3, 1] and fp.group.tolist() == [0, 0, 0]


def test_flow_problem_slot_cap_floors_with_tolerance_and_clamps():
    inst = make_instance(P=[1], E=[1], a=[0], d=[4], L=[[3.0, 3.0, 3.0, 1.0]],
                         b=[[0.5, 1.9999999999, 3.7, 0.0]])
    fp = flow_problem(inst, np.ones((1, 4), dtype=np.int64))
    # floor(2.5)=2; floor(1.0000000001+1e-9)=1 (tolerance keeps 1.0 from rounding down);
    # L-b = -0.7 clamps to 0; floor(1.0)=1
    assert fp.slot_cap.tolist() == [[2, 1, 0, 1]]


def test_flow_problem_multi_group():
    inst = make_instance(P=[1, 1], E=[1, 1], a=[0, 0], d=[2, 2], L=[[2, 2], [1, 1]],
                         b=[[0, 0], [0, 0]], group=[0, 1])
    fp = flow_problem(inst, np.ones((2, 2), dtype=np.int64))
    assert fp.group.tolist() == [0, 1] and fp.slot_cap.shape == (2, 2)


# --------------------------------------------------------------------------- hand instance
def test_hand_instance_every_metric():
    """Hand derivation.

    x/y/A are in hand1(). Debt before each slot: p0 3,2,2,0; p1 3,2,1,1; p2 1,1,0,0.
    D = (1+0+2) + (1+1+0) + (0+1+0) = 6 of sum E = 7, so R_abs = 1 unit.
    Final residual [0, 1, 0]: one participant misses its deadline, 1 unit.
    Bound: p0 takes slots 0 (2) and 2 (1), p1 takes 0, 1, 3, p2 takes 3 -> all 7 fit
    (slot caps 3,1,1,3), so R* = 0, s_own = 0, and R_avoid = 1.
    Minimum peak: with Pi < 3 the cap at t=1 is floor(Pi - 2) = 0, so at most 4 units
    flow; Pi = 3 carries 7. Bound min peak = 3.
    Loads ell = b + sum y = [2, 4, 4, 0]; peak 4; L = 3: violations at t=1,2 (1 kW each).
    Hedge waste: p2 sent 1 at t=2 and t=3 with zero debt: 2 kW.slot.
    Failed setpoints: p0 at t=1 (lost min(2,2)=2), p1 at t=2 (lost min(1,1)=1).
    """
    inst, traj = hand1()
    m = evaluate(inst, traj, delta_A=2)
    assert m["D_u"] == 6 and m["D_kwh"] == 1.5
    assert m["R_abs_u"] == 1 and m["R_abs_kwh"] == 0.25
    assert m["R_star_u"] == 0 and m["R_avoid_u"] == 1 and m["R_avoid_kwh"] == 0.25
    assert m["s_own_u"] == 0 and m["R_couple_u"] == 0
    assert m["deadline_miss_count"] == 1 and m["deadline_miss_u"] == 1
    assert m["deadline_miss_kwh"] == 0.25
    assert m["peak_kw"] == 4.0
    assert m["violation_count"] == 2 and m["violation_kwslot"] == 2.0
    assert m["violation_longest_run_slots"] == 2
    assert m["hedge_waste_kwslot"] == 2.0
    assert m["cpu_mean_ms"] == 2.0 and m["cpu_max_ms"] == 3.0
    assert m["bound_min_peak_kw"] == 3.0
    assert m["bound_max_short_frac"] == 0.0 and m["bound_short_count"] == 0
    assert m["event_shortfall_u"] == 0 and m["event_shortfall_kwh"] == 0.0
    # delta_A = 2: p1's failure at s=2 has s+2 = 4 >= d=4 (uncorrectable, residual 1);
    # p0's loss at s=1 has 1+2 = 3 >= d=3 but p0 finished (residual 0) so u_0 = 0.
    assert m["u_raw_u"] == 1
    assert split(m) == (1, 1, 0, 0)               # s_own = R_couple = 0: both readings agree
    # per-100 versions: N = 3
    assert m["R_avoid_kwh_per100"] == pytest.approx(0.25 * 100 / 3)
    assert m["R_avoid_u_per100"] == pytest.approx(100 / 3)
    assert m["deadline_miss_count_per100"] == pytest.approx(100 / 3)


def test_hand_instance_split_depends_on_delta_A():
    inst, traj = hand1()
    m1 = evaluate(inst, traj, delta_A=1)       # p1: 2+1 = 3 < 4 -> correctable
    assert m1["u_raw_u"] == 0 and split(m1) == (0, 0, 1, 1)
    m0 = evaluate(inst, traj, delta_A=0)       # lag max(0,1) = 1: same as delta_A = 1
    assert split(m0) == (0, 0, 1, 1)
    m_default = evaluate(inst, traj)           # instance cell has delta_A = 2
    assert m_default["delta_A"] == 2 and m_default["R_uncorr_hi_u"] == 1


def test_mixed_uncorrectable_and_correctable():
    """R_abs = 2, R* = 0. p0 fails at s=0 (retry would have been possible), p1 fails at s=2.
    delta_A = 2: p0 0+2 < 3 correctable; p1 2+2 >= 3 uncorrectable -> 1 + 1."""
    inst = make_instance(P=[1, 1], E=[1, 1], a=[0, 0], d=[3, 3],
                         L=[[2, 2, 2, 2]], b=np.zeros((1, 4)))
    A = [[0, 1, 1, 1], [1, 1, 0, 1]]
    x = [[1, 0, 0, 0], [0, 0, 1, 0]]
    y = np.zeros((2, 4), dtype=np.int64)
    traj = make_traj(inst, x, y, A)
    m = evaluate(inst, traj, delta_A=2)
    assert m["R_abs_u"] == 2 and m["R_star_u"] == 0 and m["R_avoid_u"] == 2
    assert m["u_raw_u"] == 1
    assert split(m) == (1, 1, 1, 1)
    assert m["R_uncorr_hi_kwh"] == 0.25 and m["R_corr_lo_kwh"] == 0.25
    assert m["deadline_miss_count"] == 2 and m["deadline_miss_u"] == 2
    # delta_A = 0 uses lag 1: p1 at s=2 is still late (2+1 >= 3), p0 at s=0 is not
    assert split(evaluate(inst, traj, delta_A=0)) == (1, 1, 1, 1)


def test_unavoidable_failure_is_capped_by_r_avoid():
    """d=1, A=[0,1]: the failed setpoint at s=0 is late but the shortfall is unavoidable
    (R* = 1, s_own = 1), so u = min(max(0, 1 - 1), 1) = 0 and R_avoid = 0."""
    inst = make_instance(P=[1], E=[1], a=[0], d=[1], L=[[1, 1]], b=np.zeros((1, 2)))
    traj = make_traj(inst, [[1, 0]], [[0, 0]], [[0, 1]])
    m = evaluate(inst, traj, delta_A=1)
    assert m["R_star_u"] == 1 and m["s_own_u"] == 1 and m["R_couple_u"] == 0
    assert m["R_avoid_u"] == 0
    # the residual is all own-capacity shortfall (s_own = 1), so it is not "uncorrectable"
    assert m["u_raw_u"] == 0 and split(m) == (0, 0, 0, 0)


def test_hedged_overshoot_is_not_a_loss():
    """x above the debt is hedge, not a failed delivery: min(x, r) - y counts only the
    deliverable part. Debt 1, x=2 at an unavailable slot: lost min(2,1) - 0 = 1, not 2."""
    inst = make_instance(P=[2], E=[1], a=[0], d=[2], L=[[3, 3]], b=np.zeros((1, 2)))
    traj = make_traj(inst, [[2, 0]], [[0, 0]], [[0, 1]])
    m = evaluate(inst, traj, delta_A=2)
    assert m["u_raw_u"] == 1                      # min(r_final - s_own = 1, lost = 1)
    assert m["hedge_waste_kwslot"] == 0.0         # debt was 1 at that slot
    # delivered 1 at t=0 (x=2, debt 1: not waste by the spec), then debt 0 at t=1 with x=2
    traj2 = make_traj(inst, [[2, 2]], [[1, 0]], [[1, 1]])
    assert evaluate(inst, traj2)["hedge_waste_kwslot"] == 2.0


def test_violation_runs_are_per_group_and_longest_wins():
    # two groups, H=5; group 0 violates at t=0 and t=2,3,4 (run 3), group 1 at t=1 only
    inst = make_instance(P=[3, 3], E=[9, 9], a=[0, 0], d=[5, 5],
                         L=[[1, 5, 1, 1, 1], [5, 1, 5, 5, 5]], b=np.zeros((2, 5)),
                         group=[0, 1])
    y = [[2, 0, 2, 2, 2], [0, 2, 0, 0, 0]]
    traj = make_traj(inst, y, y, np.ones((2, 5), dtype=np.int64))
    m = evaluate(inst, traj, delta_A=0)
    assert m["violation_count"] == 5          # (0,0),(0,2),(0,3),(0,4),(1,1)
    assert m["violation_kwslot"] == 5.0
    assert m["violation_longest_run_slots"] == 3
    assert m["peak_kw"] == 2.0


def test_event_shortfall_is_its_own_key():
    inst, traj = hand1()
    traj = replace(traj, floored=np.array([True, False, True]))
    m = evaluate(inst, traj, delta_A=2)
    assert m["event_shortfall_u"] == 4 and m["event_shortfall_kwh"] == 1.0
    assert m["floored_count"] == 2
    assert m["R_abs_u"] == 1 and m["R_avoid_u"] == 1     # untouched by the floor


def test_passed_clair_must_match_traj_A():
    inst, traj = hand1()
    good = clair_for(inst, traj.A)
    assert evaluate(inst, traj, clair=good, delta_A=2) == evaluate(inst, traj, delta_A=2)
    # untagged (raw clairvoyant) output is re-verified and accepted when right
    raw = clairvoyant(flow_problem(inst, traj.A))
    assert evaluate(inst, traj, clair=raw, delta_A=2) == evaluate(inst, traj, delta_A=2)
    # a bound for a different availability (p1 stuck throughout) is refused, tagged or not
    A2 = traj.A.copy()
    A2[1, :] = 0
    with pytest.raises(ValueError):
        evaluate(inst, traj, clair=clair_for(inst, A2), delta_A=2)
    with pytest.raises(ValueError):
        evaluate(inst, traj, clair=clairvoyant(flow_problem(inst, A2)), delta_A=2)


def test_stale_unfloored_clair_for_a_floored_run_raises():
    cell = replace(F0R_CELLS[0], r=0.0, M=3)
    inst = generate_f0r(60003, cell)
    floor_all = np.ones(inst.N, dtype=bool)

    class Floor(RandomPolicy):
        def floor_mask(self, static_view):
            return floor_all

    traj = simulate(inst, cell, Floor("floor_all", 0.9), seed=60003)
    assert not np.array_equal(inst.availability(), traj.A)       # the floor changed A
    stale = clair_for(inst, inst.availability())
    with pytest.raises(ValueError):
        evaluate(inst, traj, clair=stale)
    fresh = clair_for(inst, traj.A)
    assert evaluate(inst, traj, clair=fresh) == evaluate(inst, traj)


def optimistic_forecast_case():
    """H=2, two participants (P=E=1, d=2), both available only at t=0. Realized base load
    at t=0 is 1 but the forecast b_mean is 0: the setpoint cap is 2, the realized headroom 1.
    The policy sends both and delivers 2; the bound (realized headroom) delivers 1."""
    inst = make_instance(P=[1, 1], E=[1, 1], a=[0, 0], d=[2, 2], L=[[2, 2]],
                         b=[[1, 0]])
    inst = replace(inst, b_mean=np.zeros((1, 2)))
    traj = make_traj(inst, [[1, 0], [1, 0]], [[1, 0], [1, 0]], [[1, 0], [1, 0]])
    return inst, traj


def test_optimistic_forecast_gives_negative_r_avoid_not_an_error():
    inst, traj = optimistic_forecast_case()
    m = evaluate(inst, traj, delta_A=2)
    assert m["R_abs_u"] == 0 and m["R_star_u"] == 1 and m["R_avoid_u"] == -1
    assert m["R_avoid_kwh"] == -0.25
    assert m["exceeds_bound"] is True
    assert m["bound_overshoot_u"] == 1 and m["bound_overshoot_kwh"] == 0.25
    # the secondary bound uses the enforced setpoint cap (2): R*_sp = 0, R_avoid_sp = 0
    assert m["R_star_sp_u"] == 0 and m["R_avoid_sp_u"] == 0 and m["R_avoid_sp_kwh"] == 0.0
    # the overload is reported beside it: ell = 1 + 2 = 3 > 2
    assert m["violation_count"] == 1 and m["violation_kwslot"] == 1.0
    # clipped split readings; the identity holds in the negative case
    assert split(m) == (0, 0, -1, -1)
    assert m["R_uncorr_hi_u"] + m["R_corr_lo_u"] == m["R_avoid_u"]
    assert m["R_uncorr_lo_u"] + m["R_corr_hi_u"] == m["R_avoid_u"]
    assert m["R_avoid_u_per100"] == pytest.approx(-100 / 2)
    json.dumps(m)


def test_not_exceeding_the_bound_flags_false():
    inst, traj = hand1()
    m = evaluate(inst, traj, delta_A=2)
    assert m["exceeds_bound"] is False and m["bound_overshoot_u"] == 0
    assert m["R_avoid_sp_u"] >= 0


def test_beating_the_setpoint_cap_bound_is_fatal():
    """Delivering more than the enforced setpoint cap allows cannot happen under the
    simulator: forecast b_mean = 2 at t=0 gives cap 0 there, yet y > 0 is delivered."""
    inst, traj = optimistic_forecast_case()
    inst = replace(inst, b_mean=np.full((1, 2), 2.0))
    with pytest.raises(BoundViolation):
        evaluate(inst, traj, delta_A=2)


def test_delta_b_selects_the_forecast_lag():
    inst, traj = optimistic_forecast_case()
    # delta_b = 0: t=1 forecast is b[:, 0] = 1 (irrelevant here); t=0 uses b_mean
    assert evaluate(inst, traj, delta_b=0)["delta_b"] == 0
    assert evaluate(inst, traj, delta_b=2)["R_star_sp_u"] == 0   # t<=1 all use b_mean
    assert evaluate(inst, traj)["delta_b"] == inst.cell.delta_b


def test_impossible_delivery_is_fatal():
    inst, traj = hand1()
    y = traj.y.copy()
    y[0, 1] = 1                                    # p0 is not available at t=1
    with pytest.raises(BoundViolation):
        evaluate(inst, make_traj(inst, traj.x, y, traj.A))
    with pytest.raises(BoundViolation):
        evaluate(inst, replace(traj, r_final=traj.r_final + 1))


def test_trajectory_guards():
    inst, traj = hand1()
    with pytest.raises(ValueError):
        evaluate(inst, replace(traj, seed=7))
    with pytest.raises(ValueError):
        evaluate(inst, replace(traj, cell_id="other"))
    y = traj.y.copy()
    y[0, 0] = 0                                    # y != min(x, r_before) * A
    bad = make_traj(inst, traj.x, y, traj.A)
    with pytest.raises(ValueError):
        evaluate(inst, bad)
    with pytest.raises(ValueError):                # delivered where A = 0
        yy = traj.y.copy()
        yy[0, 1] = 1
        evaluate(inst, make_traj(inst, traj.x, yy, traj.A))


def test_a_sha256_in_row():
    inst, traj = hand1()
    m = evaluate(inst, traj)
    assert len(m["A_sha256"]) == 64
    A2 = traj.A.copy()
    A2[0, 3] = 0
    assert ledger_mod.a_sha256(A2) != m["A_sha256"]


def test_inconsistent_trajectory_rejected():
    inst, traj = hand1()
    with pytest.raises(ValueError):
        evaluate(inst, replace(traj, r_final=traj.r_final + 1))


# --------------------------------------------------------------------------- split probes
def test_probe_a_own_shortfall_is_not_uncorrectable():
    """Reviewer's probe A. k: d=1, stuck at slot 0 (s_own = 1), late failed command.
    j: d=3, fails at s=0, correctable at delta_A=2 (0 + 2 < 3). R_abs = 2, R* = 1,
    R_avoid = 1, all of it j's. Both readings: uncorrectable 0, correctable 1."""
    inst = make_instance(P=[1, 1], E=[1, 1], a=[0, 0], d=[1, 3],
                         L=[[5, 5, 5, 5]], b=np.zeros((1, 4)))
    A = [[0, 1, 1, 1], [0, 1, 1, 1]]
    x = [[1, 0, 0, 0], [1, 0, 0, 0]]
    traj = make_traj(inst, x, np.zeros((2, 4)), A)
    for dA in (0, 1, 2):
        m = evaluate(inst, traj, delta_A=dA)
        assert m["R_abs_u"] == 2 and m["R_star_u"] == 1 and m["s_own_u"] == 1
        assert m["R_avoid_u"] == 1
        assert m["u_raw_u"] == 0
        assert m["R_uncorr_hi_u"] == 0
        assert m["R_corr_lo_u"] == m["R_corr_hi_u"] == 1


def test_coupling_case_lo_below_hi():
    """4 participants, d=2, slot caps (1, 0): R* = 3, all coupling (s_own = 0).
    p0 idle, p1..p3 command at s=1 and fail (A=[1,0]); D = 0, R_abs = 4, R_avoid = 1,
    sum u = 3 = R_couple. The failures could all be coupling shortfall: lo = 0, hi = 1."""
    inst = make_instance(P=[1] * 4, E=[1] * 4, a=[0] * 4, d=[2] * 4,
                         L=[[1, 0]], b=np.zeros((1, 2)))
    A = [[1, 0]] * 4
    x = [[0, 0], [0, 1], [0, 1], [0, 1]]
    traj = make_traj(inst, x, np.zeros((4, 2)), A)
    m = evaluate(inst, traj, delta_A=2)
    assert m["R_star_u"] == 3 and m["s_own_u"] == 0 and m["R_couple_u"] == 3
    assert m["R_avoid_u"] == 1 and m["u_raw_u"] == 3
    assert m["R_uncorr_hi_u"] == 1 and m["R_uncorr_lo_u"] == 0
    assert m["R_corr_hi_u"] == 1 and m["R_corr_lo_u"] == 0
    assert m["R_uncorr_lo_kwh"] == 0.0 and m["R_corr_hi_kwh"] == 0.25


def test_delta_A_zero_rule_lag_is_at_least_one():
    """d=2, one participant. Failure at s = d-1 = 1: uncorrectable at delta_A = 0, 1, 2.
    Failure at s = 0 (= d-2): correctable at delta_A = 0 and 1, uncorrectable at 2."""
    inst = make_instance(P=[1], E=[1], a=[0], d=[2], L=[[2, 2]], b=np.zeros((1, 2)))
    late = make_traj(inst, [[0, 1]], [[0, 0]], [[1, 0]])
    for dA in (0, 1, 2):
        assert split(evaluate(inst, late, delta_A=dA)) == (1, 1, 0, 0)
    early = make_traj(inst, [[1, 0]], [[0, 0]], [[0, 1]])
    assert split(evaluate(inst, early, delta_A=0)) == (0, 0, 1, 1)
    assert split(evaluate(inst, early, delta_A=1)) == (0, 0, 1, 1)
    assert split(evaluate(inst, early, delta_A=2)) == (1, 1, 0, 0)


# --------------------------------------------------------------------------- bound row
def test_bound_row_has_zero_r_avoid_and_min_peak():
    inst, traj = hand1()
    row = bound_row(inst, traj.A)
    assert row.policy == "bound" and row.privileged
    assert np.array_equal(row.x, row.y)
    m = evaluate(inst, row, delta_A=2)
    assert m["R_avoid_u"] == 0 and m["R_avoid_kwh"] == 0.0
    assert m["R_abs_u"] == m["R_star_u"] == 0
    assert m["peak_kw"] == 3.0 == m["bound_min_peak_kw"]
    assert m["violation_count"] == 0 and m["hedge_waste_kwslot"] == 0.0
    assert split(m) == (0, 0, 0, 0) and m["deadline_miss_count"] == 0


def test_bound_row_with_irreducible_shortfall():
    inst = make_instance(P=[1], E=[3], a=[0], d=[2], L=[[1, 1, 1]], b=np.zeros((1, 3)))
    A = np.array([[1, 0, 1]])
    m = evaluate(inst, bound_row(inst, A), delta_A=0)
    assert m["R_star_u"] == 2 and m["R_abs_u"] == 2 and m["R_avoid_u"] == 0
    assert m["bound_short_count"] == 1 and m["bound_max_short_frac"] == pytest.approx(2 / 3)


# --------------------------------------------------------------------------- mechanism I1
def run_i1(omega, sched, delta_A=2):
    inst, cell, idx = i1_instance(omega, delta_A=delta_A)
    traj = simulate(inst, cell, schedule_policy(idx, sched), seed=inst.seed)
    return evaluate(inst, traj, delta_A=cell.delta_A)


def test_mechanism_i1_ce_omega0_is_all_uncorrectable():
    m = run_i1(0, {0: ["A", "B"], 1: ["D"]}, delta_A=2)
    assert m["R_abs_u"] == 1 and m["R_star_u"] == 0
    assert m["R_avoid_u"] == 1 and m["R_avoid_kwh"] == 0.25
    assert m["s_own_u"] == 0 and m["R_couple_u"] == 0       # so lo == hi
    assert split(m) == (1, 1, 0, 0) and m["R_uncorr_hi_kwh"] == m["R_uncorr_lo_kwh"] == 0.25
    assert m["R_corr_hi_u"] == m["R_corr_lo_u"] == 0 and m["u_raw_u"] == 1
    assert m["deadline_miss_count"] == 1 and m["hedge_waste_kwslot"] == 0.0
    assert m["violation_count"] == 0 and m["peak_kw"] == 1.0   # B at t=0, D at t=1


def test_mechanism_i1_other_cases():
    assert run_i1(1, {0: ["A", "B"], 1: ["D"]})["R_avoid_u"] == 0       # omega1: A delivers
    hedged0 = run_i1(0, {0: ["A", "B"], 1: ["A", "D"]})
    assert hedged0["R_avoid_u"] == 0 and hedged0["hedge_waste_kwslot"] == 0.0
    hedged1 = run_i1(1, {0: ["A", "B"], 1: ["A", "D"]})
    assert hedged1["R_avoid_u"] == 0 and hedged1["hedge_waste_kwslot"] == 1.0  # spare A setpoint


def test_mechanism_i1_with_correctable_lag():
    """The omega0 failure at s=0 (d=2) is correctable when the lag is 0 or 1 (0 + 1 < 2):
    books as corrected-in-principle, 1 unit, in both readings."""
    inst, cell, idx = i1_instance(0, delta_A=2)
    traj = simulate(inst, cell, schedule_policy(idx, {0: ["A", "B"], 1: ["D"]}),
                    seed=inst.seed)
    for dA in (0, 1):
        m = evaluate(inst, traj, delta_A=dA)
        assert m["R_avoid_u"] == 1 and split(m) == (0, 0, 1, 1)
    assert split(evaluate(inst, traj, delta_A=2)) == (1, 1, 0, 0)


# --------------------------------------------------------------------------- units / JSON
def test_kwh_is_quarter_of_units_everywhere():
    inst, traj = hand1()
    for t in (traj, bound_row(inst, traj.A)):
        m = evaluate(inst, t, delta_A=2)
        pairs = [(k[:-2], k) for k in m if k.endswith("_u")]
        assert pairs
        for base, k in pairs:
            assert m[base + "_kwh"] == pytest.approx(0.25 * m[k]), base


def test_json_round_trip_and_types():
    inst, traj = hand1()
    m = evaluate(inst, traj, delta_A=2)
    assert json.loads(json.dumps(m)) == m
    for k, v in m.items():
        assert isinstance(v, (int, float, str, bool)) and not isinstance(v, np.generic), k
        if k.endswith("_count") or k.endswith("_slots") or k in ("seed", "N", "H", "delta_A"):
            assert isinstance(v, int), k
        if k.endswith(("_u", "_kwh", "_kw", "_kwslot", "_ms")):
            assert isinstance(v, float), k
    mb = evaluate(inst, bound_row(inst, traj.A), delta_A=2)
    assert json.loads(json.dumps(mb)) == mb


def test_suffix_discipline():
    inst, traj = hand1()
    m = evaluate(inst, traj, delta_A=2)
    for k in m:
        if k in ("policy", "privileged", "seed", "cell_id", "family", "N", "H", "delta_A",
                 "delta_b", "A_sha256", "exceeds_bound", "bound_row"):
            continue
        base = k[:-len("_per100")] if k.endswith("_per100") else k
        assert base.endswith(("_u", "_kwh", "_kw", "_kwslot", "_ms", "_slots", "_count",
                              "_frac")), k


# --------------------------------------------------------------------------- properties
class RandomPolicy:
    """Random feasible policy: random setpoints, trimmed to the setpoint cap."""

    privileged = False

    def __init__(self, name, density, floor_share=0.0):
        self.name, self.density, self.floor_share = name, density, floor_share
        self.rng = None

    def reset(self, static_view, rng, oracle=None):
        self.rng = rng

    def floor_mask(self, static_view):
        if self.floor_share == 0.0:
            return None
        return self.rng.random(static_view.N) < self.floor_share

    def act(self, view):
        x = (self.rng.integers(0, view.P + 1) * (self.rng.random(view.N) < self.density))
        x = np.where(view.active, x, 0).astype(np.int64)
        caps = np.maximum(0, view.setpoint_caps())
        for g in range(view.G):
            idx = np.flatnonzero((view.group == g) & (x > 0))
            while x[idx].sum() > caps[g]:
                j = idx[self.rng.integers(0, len(idx))]
                x[j] -= 1
                idx = np.flatnonzero((view.group == g) & (x > 0))
        return x


PROPERTY_CELLS = [F0R_CELLS[i] for i in (0, 3, 5, 7, 8, 13, 17, 21)]


@pytest.mark.parametrize("cell", PROPERTY_CELLS, ids=lambda c: c.cell_id)
def test_split_identity_and_nonnegative_avoid_on_random_policies(cell):
    for seed in (60000, 60001):
        inst = generate_f0r(seed, cell)
        for k, (density, fl) in enumerate([(0.3, 0.0), (0.7, 0.0), (1.0, 0.0), (0.5, 0.3)]):
            pol = RandomPolicy(f"rand{k}", density, fl)
            traj = simulate(inst, cell, pol, seed=seed)
            clair = clair_for(inst, traj.A)
            prev_hi = -1
            for dA in (0, 1, 2, 4, cell.delta_A):
                m = evaluate(inst, traj, clair=clair, delta_A=dA)
                assert m["R_avoid_sp_u"] >= 0          # hard invariant
                assert m["exceeds_bound"] == (m["R_avoid_u"] < 0)
                assert m["bound_overshoot_u"] == max(0, -m["R_avoid_u"])
                pos = max(0, m["R_avoid_u"])
                assert 0 <= m["R_uncorr_lo_u"] <= m["R_uncorr_hi_u"] <= pos
                assert m["R_corr_lo_u"] <= m["R_corr_hi_u"]
                if m["R_avoid_u"] >= 0:
                    assert 0 <= m["R_corr_lo_u"] <= m["R_corr_hi_u"] <= pos
                assert m["R_uncorr_hi_u"] + m["R_corr_lo_u"] == m["R_avoid_u"]
                assert m["R_uncorr_lo_u"] + m["R_corr_hi_u"] == m["R_avoid_u"]
                assert m["R_uncorr_hi_u"] <= m["u_raw_u"]
                assert "R_uncorr_u" not in m and "R_corr_u" not in m
                assert m["R_abs_u"] == m["R_avoid_u"] + m["R_star_u"]
                assert m["R_star_u"] == m["s_own_u"] + m["R_couple_u"]
                assert m["D_u"] + m["R_abs_u"] == m["E_u"]
                assert m["deadline_miss_u"] == m["R_abs_u"]
                assert m["event_shortfall_u"] == 2 * m["floored_count"]
            # the late set grows with the lag; delta_A = 0 and 1 agree
            by_lag = [evaluate(inst, traj, clair=clair, delta_A=d)["u_raw_u"]
                      for d in (0, 1, 2, 4)]
            assert by_lag == sorted(by_lag) and by_lag[0] == by_lag[1]
            assert m["violation_count"] >= 0
            json.dumps(m)


@pytest.mark.parametrize("cell", PROPERTY_CELLS[:4], ids=lambda c: c.cell_id)
def test_bound_row_r_avoid_zero_on_generated_instances(cell):
    inst = generate_f0r(60002, cell)
    A = inst.availability()
    row = bound_row(inst, A)
    m = evaluate(inst, row, delta_A=cell.delta_A)
    assert m["R_avoid_u"] == 0 and split(m) == (0, 0, 0, 0)
    assert m["R_abs_u"] == m["R_star_u"]
    assert m["peak_kw"] == m["bound_min_peak_kw"]
    # no random policy beats the bound or its R_abs
    traj = simulate(inst, cell, RandomPolicy("rand", 0.8), seed=60002)
    assert evaluate(inst, traj)["R_abs_u"] >= m["R_abs_u"]


def test_floored_bound_uses_floored_availability():
    cell = replace(F0R_CELLS[0], r=0.0, M=3)
    inst = generate_f0r(60003, cell)
    floor_all = np.ones(inst.N, dtype=bool)

    class Floor(RandomPolicy):
        def floor_mask(self, static_view):
            return floor_all

    traj = simulate(inst, cell, Floor("floor_all", 0.9), seed=60003)
    assert np.array_equal(traj.A, inst.availability(floor_all))
    m = evaluate(inst, traj)                       # bound computed on the floored A
    plain = clairvoyant(flow_problem(inst, inst.availability())).R_star
    floored = clairvoyant(flow_problem(inst, traj.A)).R_star
    assert m["R_star_u"] == floored <= plain       # r <= 0.98: floored dominates (OPEN 17)
    assert m["event_shortfall_u"] == 2 * inst.N


@pytest.mark.parametrize("delta_b", [0, 2])
def test_bound_row_reports_raw_negative_r_avoid_sp_but_policies_stay_hard(delta_b):
    """Tuning seed 60000, rho = 0.7: realized headroom lets the bound beat R*_sp
    (R* = 11 < R*_sp = 12 at delta_b = 0, 13 at delta_b = 2)."""
    cell = replace(F0R_CELLS[1], rho=0.7, delta_b=delta_b, delta_A=2)
    inst = generate_f0r(60000, cell)
    A = inst.availability()
    row = bound_row(inst, A)
    m = evaluate(inst, row)                        # must not raise
    assert m["bound_row"] is True and m["exceeds_bound"] is False
    assert m["R_avoid_u"] == 0 and m["bound_overshoot_u"] == 0
    assert m["R_avoid_sp_u"] < 0 and m["R_avoid_sp_kwh"] == 0.25 * m["R_avoid_sp_u"]
    assert m["R_star_sp_u"] > m["R_star_u"]
    json.dumps(m)
    # the same deliveries as a policy row beat the setpoint-cap bound: still fatal
    mimic = replace(row, policy="mimic", privileged=False)
    assert not getattr(mimic, "is_bound_row", False)
    with pytest.raises(BoundViolation):
        evaluate(inst, mimic)


def test_policy_rows_report_bound_row_false():
    inst, traj = hand1()
    assert evaluate(inst, traj)["bound_row"] is False
    assert evaluate(inst, bound_row(inst, traj.A))["bound_row"] is True
