"""Simulator tests: I1 hand check, validation, oracle routing, masking, CPU timing."""
from dataclasses import replace

import numpy as np
import pytest

from papere.generator import F0R_CELLS, generate_f0r, generate_kcopy, policy_rng, stable_hash
from papere.infoset import InformationSet, OracleView, StaticView, UNKNOWN
from papere.instance import Cell
from papere.sim import InvalidAction, Policy, Trajectory, simulate

from test_infoset import reachable


class Scripted:
    """Tiny policy: ``plan(view) -> int[N]``; reads only the view."""

    def __init__(self, plan, name="scripted", privileged=False, floor=None):
        self.plan, self.name, self.privileged, self._floor = plan, name, privileged, floor
        self.reset_args = None
        self.views = []

    def reset(self, static_view, rng, oracle=None):
        self.reset_args = (static_view, rng, oracle)

    def floor_mask(self, static_view):
        return self._floor

    def act(self, view):
        self.views.append(view)
        return self.plan(view)


def i1_instance(omega: int, delta_A: int = 2):
    """K=1 pooled c=K=1 (cap 2, 2): returns instance, cell, role indices. omega 0 = A stuck.

    ``delta_A != 2`` relabels the cell after generation (the generator needs delta_A >= 2).
    """
    cell = Cell(family="KCOPY", M=0, delta_A=2, delta_b=0, q=0.5, c=1.0, cap_mode="pooled")
    for seed in range(60000, 60050):
        inst = generate_kcopy(seed, cell, K=1)
        stuck = inst.availability()[inst.cls == 1, 0][0] == 0
        if stuck == (omega == 0):
            if delta_A != 2:
                cell = replace(cell, delta_A=delta_A)
                inst = replace(inst, cell=cell)
            return inst, cell, {k: int(np.flatnonzero(inst.cls == v)[0])
                                for k, v in (("A", 1), ("B", 0), ("D", 2))}
    raise AssertionError("no seed found")


def schedule_policy(idx, sched):
    def plan(view):
        x = np.zeros(view.N, dtype=np.int64)
        for role in sched.get(view.t, []):
            x[idx[role]] = 1
        return x
    return Scripted(plan, name="sched")


def residual(omega, sched):
    inst, cell, idx = i1_instance(omega)
    traj = simulate(inst, cell, schedule_policy(idx, sched), seed=inst.seed)
    return int(traj.r_final.sum()), traj, idx


def test_i1_certainty_equivalent_and_hedged_schedules():
    ce = {0: ["A", "B"], 1: ["D"]}
    hedge = {0: ["A", "B"], 1: ["A", "D"]}
    assert residual(1, ce)[0] == 0      # omega1: A delivers at slot 0
    assert residual(0, ce)[0] == 1      # omega0: A stuck, never served again
    assert residual(1, hedge)[0] == 0
    assert residual(0, hedge)[0] == 0
    # hand-check of the hedged omega0 trajectory
    _, traj, idx = residual(0, hedge)
    assert traj.y[idx["A"]].tolist() == [0, 1] and traj.y[idx["B"]].tolist() == [1, 0]
    assert traj.y[idx["D"]].tolist() == [0, 1]
    assert traj.r_before[idx["A"]].tolist() == [1, 1]
    # omega1 hedge: the second A setpoint delivers nothing (debt already zero)
    _, traj, idx = residual(1, hedge)
    assert traj.y[idx["A"]].tolist() == [1, 0] and traj.r_before[idx["A"]].tolist() == [1, 0]


def test_i1_policy_cannot_see_the_outcome_at_delta_2():
    inst, cell, idx = i1_instance(0)
    pol = schedule_policy(idx, {0: ["A", "B"], 1: ["A", "D"]})
    simulate(inst, cell, pol, seed=inst.seed)
    v1 = pol.views[1]
    assert v1.A_confirmed.shape == (3, 0) and v1.y_confirmed.shape == (3, 0)
    assert (v1.confirmed_debt == 1).all()


# -------------------------------------------------------------- validation
def f0r_instance(delta_A=2, seed=60000, **kw):
    cell = replace(F0R_CELLS[0], delta_A=delta_A, **kw)
    return generate_f0r(seed, cell), cell


def first_active(inst, t=0):
    return int(np.flatnonzero((inst.a <= t) & (t < inst.d))[0])


@pytest.mark.parametrize("kind", ["float", "negative", "above_P", "outside_window", "cap",
                                  "shape", "bool"])
def test_invalid_actions_raise(kind):
    inst, cell = f0r_instance()
    i = first_active(inst)
    out = int(np.flatnonzero(inst.a > 0)[0]) if (inst.a > 0).any() else None

    def plan(view):
        x = np.zeros(view.N, dtype=np.int64)
        if kind == "float":
            return x.astype(float)
        if kind == "bool":
            return x.astype(bool)
        if kind == "shape":
            return x[:-1]
        if kind == "negative":
            x[i] = -1
        elif kind == "above_P":
            x[i] = view.P[i] + 1
        elif kind == "outside_window":
            assert out is not None
            x[out] = 1
        elif kind == "cap":
            # fill every active participant to P: exceeds the single group's cap
            x[view.active] = view.P[view.active]
            assert x.sum() > view.setpoint_cap(0)
        return x

    with pytest.raises(InvalidAction):
        simulate(inst, cell, Scripted(plan), seed=inst.seed)


def test_cap_boundary_is_allowed_and_zero_is_valid():
    inst, cell = f0r_instance()

    def plan(view):
        x = np.zeros(view.N, dtype=np.int64)
        cap = max(0, view.setpoint_cap(0))
        for j in np.flatnonzero(view.active):
            give = min(int(view.P[j]), cap - int(x.sum()))
            x[j] = give
        assert x.sum() <= cap
        return x

    traj = simulate(inst, cell, Scripted(plan), seed=inst.seed)
    assert isinstance(traj, Trajectory)
    assert traj.x.sum() > 0
    simulate(inst, cell, Scripted(lambda v: np.zeros(v.N, dtype=np.int64)), seed=inst.seed)


def test_per_group_cap_enforced():
    """Group 0 exceeds its own cap while the pooled total stays within the sum of caps."""
    cell = Cell(family="KCOPY", M=0, delta_A=2, q=0.5, c=0.0, cap_mode="per_copy")
    inst = generate_kcopy(60003, cell, K=2)         # slot-1 cap is 1 per copy, sum of caps 2
    assert inst.L[:, 1].tolist() == [1.0, 1.0]

    def members(g):
        return np.flatnonzero((inst.group == g) & (inst.cls != 1))   # B and D of copy g

    def plan_for(counts):
        def plan(view):
            x = np.zeros(view.N, dtype=np.int64)
            if view.t == 1:
                for g, n in counts.items():
                    x[members(g)[:n]] = 1
            return x
        return plan

    # 2 units in group 0, 0 in group 1: pooled total 2 <= 1 + 1, but group 0 breaches
    with pytest.raises(InvalidAction):
        simulate(inst, cell, Scripted(plan_for({0: 2})), seed=inst.seed)
    with pytest.raises(InvalidAction):
        simulate(inst, cell, Scripted(plan_for({1: 2})), seed=inst.seed)
    # one unit per group is fine
    traj = simulate(inst, cell, Scripted(plan_for({0: 1, 1: 1})), seed=inst.seed)
    assert traj.x[:, 1].sum() == 2


# ---------------------------------------------------------------- plumbing
def test_oracle_only_reaches_privileged_policies():
    inst, cell = f0r_instance()
    zero = lambda v: np.zeros(v.N, dtype=np.int64)  # noqa: E731
    normal, priv = Scripted(zero, "n"), Scripted(zero, "p", privileged=True)
    t_n = simulate(inst, cell, normal, seed=inst.seed)
    t_p = simulate(inst, cell, priv, seed=inst.seed)
    assert normal.reset_args[2] is None and not t_n.privileged
    oracle = priv.reset_args[2]
    assert isinstance(oracle, OracleView) and t_p.privileged
    assert np.array_equal(oracle.cls, inst.cls) and np.array_equal(oracle.q, inst.q)
    assert isinstance(normal.reset_args[0], StaticView)
    assert isinstance(normal, Policy)
    # no policy receives the Instance through the views
    assert not any(type(o).__name__ in ("Instance", "Cell")
                   for v in normal.views for o in reachable(v))


def test_tiebreak_stream_shared_across_policy_names():
    inst, cell = f0r_instance()
    zero = lambda v: np.zeros(v.N, dtype=np.int64)  # noqa: E731
    p1, p2 = Scripted(zero, "pol"), Scripted(zero, "other_name")
    simulate(inst, cell, p1, seed=inst.seed)
    simulate(inst, cell, p2, seed=inst.seed)
    expect = policy_rng(inst.seed, cell.cell_id, "tiebreak").random(3)
    assert np.array_equal(p1.reset_args[1].random(3), expect)
    assert np.array_equal(p2.reset_args[1].random(3), expect)
    # still distinct across seeds and cells
    other_cell = replace(cell, rho=0.7)
    inst2 = generate_f0r(inst.seed, other_cell)
    p3 = Scripted(zero, "pol")
    simulate(inst2, other_cell, p3, seed=inst.seed)
    assert not np.array_equal(p3.reset_args[1].random(3), expect)
    inst3 = generate_f0r(inst.seed + 1, cell)
    p4 = Scripted(zero, "pol")
    simulate(inst3, cell, p4, seed=inst3.seed)
    assert not np.array_equal(p4.reset_args[1].random(3), expect)
    # no raw seed or cell hash inside the stream handed to the policy
    ent = np.atleast_1d(np.asarray(p1.reset_args[1].bit_generator.seed_seq.entropy)).tolist()
    assert inst.seed not in ent and stable_hash(cell.cell_id) not in ent


def test_identical_policies_with_different_names_give_identical_trajectories():
    inst, cell = f0r_instance(delta_A=2, seed=60003)

    def tie_break_policy(view, rng_holder):
        x = np.zeros(view.N, dtype=np.int64)
        cand = np.flatnonzero(view.active & (view.confirmed_debt > 0))
        cand = cand[np.argsort(rng_holder[0].random(len(cand)))]   # tie-break noise
        left = max(0, view.setpoint_cap(0))
        for j in cand:
            give = min(int(view.P[j]), left)
            x[j], left = give, left - give
        return x

    def make(name):
        holder = []
        pol = Scripted(lambda v: tie_break_policy(v, holder), name=name)
        orig = pol.reset
        pol.reset = lambda sv, rng, oracle=None: (holder.append(rng), orig(sv, rng, oracle))[1]
        return pol

    t1 = simulate(inst, cell, make("alpha"), seed=inst.seed)
    t2 = simulate(inst, cell, make("beta@c07"), seed=inst.seed)
    assert t1.policy != t2.policy
    for f in ("x", "y", "A", "r_before", "r_final"):
        assert np.array_equal(getattr(t1, f), getattr(t2, f)), f
    assert t1.x.sum() > 0


def test_cpu_ms_recorded():
    inst, cell = f0r_instance()

    def slow(view):
        s = 0.0
        for k in range(20000):
            s += k * 0.5
        return np.zeros(view.N, dtype=np.int64)

    traj = simulate(inst, cell, Scripted(slow), seed=inst.seed)
    assert traj.cpu_ms.shape == (inst.H,) and (traj.cpu_ms > 0).all()


def test_delivery_semantics_and_shapes():
    inst, cell = f0r_instance()

    def plan(view):  # greedy under the cap, ignores debt
        x = np.zeros(view.N, dtype=np.int64)
        left = max(0, view.setpoint_cap(0))
        for j in np.flatnonzero(view.active):
            give = min(int(view.P[j]), left)
            x[j], left = give, left - give
        return x

    traj = simulate(inst, cell, Scripted(plan), seed=inst.seed)
    N, H = inst.N, inst.H
    for arr in (traj.x, traj.y, traj.A, traj.r_before):
        assert arr.shape == (N, H)
    assert traj.r_final.shape == (N,) and traj.floored.shape == (N,)
    assert np.array_equal(traj.A, inst.availability())
    assert np.array_equal(traj.y, np.minimum(traj.x, traj.r_before) * traj.A)
    assert np.array_equal(traj.r_before[:, 0], inst.E)
    assert np.array_equal(traj.r_before[:, 1:], inst.E[:, None] - np.cumsum(traj.y, axis=1)[:, :-1])
    assert np.array_equal(traj.r_final, inst.E - traj.y.sum(axis=1))
    assert (traj.r_final >= 0).all() and traj.y.sum() > 0
    assert traj.policy == "scripted" and traj.cell_id == cell.cell_id


def test_floor_mask_applied():
    inst, cell = f0r_instance()
    fl = np.ones(inst.N, dtype=bool)
    zero = lambda v: np.zeros(v.N, dtype=np.int64)  # noqa: E731
    traj = simulate(inst, cell, Scripted(zero, floor=fl), seed=inst.seed)
    assert traj.floored.all() and (traj.A[:, 0] == 1).all()
    assert np.array_equal(traj.A, inst.availability(fl))
    with pytest.raises(InvalidAction):
        simulate(inst, cell, Scripted(zero, floor=np.ones(3, dtype=bool)), seed=inst.seed)
    with pytest.raises(ValueError):
        simulate(inst, replace(cell, M=1), Scripted(zero), seed=inst.seed)


# ----------------------------------------------- observation mask (correction)
def greedy_blind(view):
    """Send to active participants in index order up to the cap, ignoring debt."""
    x = np.zeros(view.N, dtype=np.int64)
    left = max(0, view.setpoint_cap(0))
    for j in np.flatnonzero(view.active):
        give = min(int(view.P[j]), left)
        x[j], left = give, left - give
    return x


@pytest.mark.parametrize("delta_A", [1, 2, 4])
def test_revealed_availability_masked_by_setpoint_and_debt(delta_A):
    inst, cell = f0r_instance(delta_A=delta_A, seed=60001, rho=1.15)
    pol = Scripted(greedy_blind)
    traj = simulate(inst, cell, pol, seed=inst.seed)
    revealed = (traj.x > 0) & (traj.r_before > 0)
    truth_masked = np.where(revealed, traj.A, UNKNOWN)
    t_ = np.arange(inst.H)[None, :]
    window = (t_ >= inst.a[:, None]) & (t_ < inst.d[:, None])
    unsent = window & (traj.x == 0) & (traj.r_before > 0)
    completed = (traj.x > 0) & (traj.r_before == 0)
    stuck = (traj.x > 0) & (traj.r_before > 0) & (traj.A == 0)
    assert unsent.any() and completed.any() and stuck.any()
    for view in pol.views:
        n = max(0, view.t - delta_A + 1)
        assert view.A_confirmed.shape == (inst.N, n) == view.y_confirmed.shape
        assert np.array_equal(view.A_confirmed, truth_masked[:, :n])
        assert np.array_equal(view.y_confirmed, traj.y[:, :n])
        assert np.array_equal(view.x_past, traj.x[:, :view.t])
    last = pol.views[-1]
    n = last.A_confirmed.shape[1]
    assert (last.A_confirmed[unsent[:, :n]] == UNKNOWN).all()
    assert (last.A_confirmed[completed[:, :n]] == UNKNOWN).all()
    assert (last.A_confirmed[stuck[:, :n]] == 0).all()
    sent = (traj.x > 0) & (traj.r_before > 0)
    assert (last.A_confirmed[sent[:, :n]] == traj.A[:, :n][sent[:, :n]]).all()
    # the wrapper holds no array equal to the unmasked A prefix
    A_prefix = traj.A[:, :n]
    assert (A_prefix != last.A_confirmed).any()
    for o in reachable(last):
        if isinstance(o, np.ndarray) and o.shape == A_prefix.shape and o.size:
            assert not np.array_equal(o, A_prefix)


def redispatch_greedy(view):
    """Greedy over active participants with debt, skipping those found failed this slot."""
    x = np.zeros(view.N, dtype=np.int64)
    left = max(0, view.setpoint_cap(0))
    bad = (view.A_confirmed[:, view.t] == 0) if view.delta_A == 0 else np.zeros(view.N, bool)
    for j in np.flatnonzero(view.active & (view.confirmed_debt > 0) & ~bad):
        give = min(int(view.P[j]), left)
        x[j], left = give, left - give
    return x


class Recording(Scripted):
    """Stores every view and every returned action (the reviewer's caching probe)."""

    def __init__(self, plan, **kw):
        super().__init__(plan, **kw)
        self.calls = []

    def act(self, view):
        x = super().act(view)
        self.calls.append((view.t, view.redispatch_round, np.array(x)))
        return x


def test_delta_A_zero_never_reveals_uncommanded_participants():
    inst, cell = f0r_instance(delta_A=0, seed=60001)
    pol = Recording(redispatch_greedy)
    traj = simulate(inst, cell, pol, seed=inst.seed)
    assert traj.rounds.max() > 1                         # re-dispatch actually happened
    assert (traj.rounds >= 1).all() and np.array_equal(traj.rounds, np.bincount(
        [c[0] for c in pol.calls], minlength=inst.H))
    # (i, s) pairs commanded with debt in some call of slot s
    commanded = np.zeros((inst.N, inst.H), dtype=bool)
    for t, rnd, x in pol.calls:
        commanded[:, t] |= (x > 0) & (traj.r_before[:, t] > 0)
    ever = np.zeros((inst.N, inst.H), dtype=bool)
    for v in pol.views:
        ever[:, :v.A_confirmed.shape[1]] |= v.A_confirmed != UNKNOWN
    assert (ever <= commanded).all()                     # revealed set within commanded set
    t_ = np.arange(inst.H)[None, :]
    window = (t_ >= inst.a[:, None]) & (t_ < inst.d[:, None])
    never = window & (traj.r_before > 0) & ~commanded
    assert never.any() and not ever[never].any()         # uncommanded stay unknown forever
    # per call: column t shows only entries commanded in EARLIER rounds of the same slot
    by_slot = {}
    for (t, rnd, x), v in zip(pol.calls, pol.views):
        assert v.redispatch_round == rnd and v.A_confirmed.shape[1] == t + 1
        col = v.A_confirmed[:, t]
        if rnd == 0:
            assert (col == UNKNOWN).all() and (v.y_confirmed[:, t] == 0).all()
        else:
            earlier = np.zeros(inst.N, dtype=bool)
            for x0 in by_slot[t]:
                earlier |= (x0 > 0) & (traj.r_before[:, t] > 0)
            assert ((col != UNKNOWN) <= earlier).all()
            assert (col[col != UNKNOWN] == traj.A[:, t][col != UNKNOWN]).all()
            assert (col == 0).any()                      # a re-dispatch needs a failure
        by_slot.setdefault(t, []).append(x)
        assert np.array_equal(v.confirmed_debt, traj.r_before[:, t])
        # past columns: exact mask with final x, OR reveals made during re-dispatch
        assert np.array_equal(v.x_past, traj.x[:, :t])
    # last call's action is the slot's action
    last = {}
    for t, rnd, x in pol.calls:
        last[t] = x
    assert all(np.array_equal(last[t], traj.x[:, t]) for t in range(inst.H))
    # revealed entries persist into later slots (policy legitimately learned them)
    for v in pol.views:
        for s in range(v.t):
            seen = v.A_confirmed[:, s] != UNKNOWN
            assert (seen >= ((traj.x[:, s] > 0) & (traj.r_before[:, s] > 0))).all()


def i1_ce_redispatch(view):
    """Certainty-equivalent: serve active participants with debt, skipping known failures."""
    return redispatch_greedy(view)


def test_i1_delta_A_zero_failed_command_is_corrected_within_the_slot():
    inst, cell, idx = i1_instance(0, delta_A=0)          # omega0: A stuck at slot 0
    pol = Recording(i1_ce_redispatch)
    traj = simulate(inst, cell, pol, seed=inst.seed)
    assert int(traj.r_final.sum()) == 0
    assert traj.rounds.tolist() == [2, 1]
    v1 = pol.views[1]                                    # slot 0, round 1
    assert (v1.t, v1.redispatch_round) == (0, 1)
    assert v1.A_confirmed[idx["A"], 0] == 0
    assert v1.A_confirmed[idx["D"], 0] == UNKNOWN        # D never commanded
    assert traj.x[:, 0].tolist() == [1 if k == idx["B"] else 0 for k in range(3)]
    inst1, cell1, idx1 = i1_instance(1, delta_A=0)
    t1 = simulate(inst1, cell1, Recording(i1_ce_redispatch), seed=inst1.seed)
    assert int(t1.r_final.sum()) == 0 and t1.rounds.tolist() == [1, 1]
    # contrast: the same certainty-equivalent rule at delta_A = 2 loses a unit in omega0
    assert residual(0, {0: ["A", "B"], 1: ["D"]})[0] == 1


def test_redispatch_terminates_when_everyone_is_stuck():
    inst, cell = f0r_instance(delta_A=0, seed=60003, r=0.0)
    inst = replace(inst, v=np.zeros(inst.N), q=np.ones(inst.N))   # all stuck, r = 0

    def probe_one(view):
        x = np.zeros(view.N, dtype=np.int64)
        cand = np.flatnonzero(view.active & (view.confirmed_debt > 0)
                              & (view.A_confirmed[:, view.t] != 0))
        if len(cand) and view.setpoint_cap(0) >= 1:
            x[cand[0]] = 1
        return x

    traj = simulate(inst, cell, Scripted(probe_one), seed=inst.seed)
    n_active = ((inst.a[:, None] <= np.arange(inst.H)) & (np.arange(inst.H) < inst.d[:, None])).sum(0)
    assert (traj.rounds == n_active + 1).all()
    assert traj.rounds.max() <= inst.N + 1 and traj.y.sum() == 0


def test_cpu_ms_sums_over_rounds():
    inst, cell = f0r_instance(delta_A=0, seed=60001)
    traj = simulate(inst, cell, Recording(redispatch_greedy), seed=inst.seed)
    assert (traj.cpu_ms > 0).all() and traj.rounds.max() > 1


def test_validation_independent_of_anything_the_policy_can_reach():
    inst, cell = f0r_instance()
    for attack in ("window", "cap"):
        errors = []

        def plan(view, attack=attack):
            for arr in (view.L, view.a, view.d, view.P, view.b_mean):
                for fn in (lambda: setattr(arr.flags, "writeable", True),
                           lambda: arr.setflags(write=True),
                           lambda: arr.__setitem__(Ellipsis, 10 ** 6)):
                    try:
                        fn()
                    except ValueError:
                        errors.append(1)
            x = np.zeros(view.N, dtype=np.int64)
            if attack == "window":
                x[~view.active] = 1
                assert x.sum() > 0
            else:
                x[view.active] = view.P[view.active]
            return x

        with pytest.raises(InvalidAction):
            simulate(inst, cell, Scripted(plan), seed=inst.seed)
        assert len(errors) == 15                          # every tampering attempt refused


def test_simulator_cap_matches_view_forecast_rule():
    from papere.sim import _slot_caps
    for dA, db in ((2, 0), (0, 2), (1, 3)):
        inst, cell = f0r_instance(delta_A=dA, delta_b=db, seed=60004)
        pol = Recording(lambda v: np.zeros(v.N, dtype=np.int64))
        simulate(inst, cell, pol, seed=inst.seed)
        for v in pol.views:
            assert np.array_equal(_slot_caps(inst, v.t, db), np.maximum(0, v.setpoint_caps(0)))


def test_seed_must_match_instance():
    inst, cell = f0r_instance()
    with pytest.raises(ValueError):
        simulate(inst, cell, Scripted(lambda v: np.zeros(v.N, dtype=np.int64)),
                 seed=inst.seed + 1)


def test_delta_b_lag_through_simulator():
    inst, cell = f0r_instance(delta_A=0, delta_b=2, seed=60002)
    pol = Scripted(lambda v: np.zeros(v.N, dtype=np.int64))
    simulate(inst, cell, pol, seed=inst.seed)
    for view in pol.views:
        assert view.b_observed.shape == (1, max(0, view.t - 2))
        assert np.array_equal(view.b_observed, inst.b[:, :max(0, view.t - 2)])
        assert view.A_confirmed.shape[1] == view.t + 1


@pytest.mark.parametrize("dA,db", [(2, 1), (0, 2), (1, 0)])
def test_rewriting_static_view_lags_via_descriptor_widens_nothing(dA, db):
    """A policy that forces its own StaticView's lags to -1 sees the same data as one that doesn't."""
    inst, cell = f0r_instance(delta_A=dA, delta_b=db, seed=60005)

    class Tamper(Recording):
        def reset(self, static_view, rng, oracle=None):
            super().reset(static_view, rng, oracle)
            for name in ("delta_A", "delta_b"):
                StaticView.__dict__[name].__set__(static_view, -1)   # bypasses __setattr__
            assert static_view.delta_A == -1

    honest = Recording(redispatch_greedy)
    tamper = Tamper(redispatch_greedy)
    t1 = simulate(inst, cell, honest, seed=inst.seed)
    t2 = simulate(inst, cell, tamper, seed=inst.seed)
    assert np.array_equal(t1.x, t2.x) and np.array_equal(t1.y, t2.y)
    for v1, v2 in zip(honest.views, tamper.views):
        assert (v2.delta_A, v2.delta_b) == (dA, db)
        assert v2.A_confirmed.shape == v1.A_confirmed.shape == (inst.N, max(0, v2.t - dA + 1))
        assert v2.b_observed.shape == v1.b_observed.shape == (1, max(0, v2.t - db))
        assert np.array_equal(v2.A_confirmed, v1.A_confirmed)
        assert np.array_equal(v2.b_observed, v1.b_observed)


def test_policy_static_view_is_a_separate_object():
    inst, cell = f0r_instance()
    pol = Recording(lambda v: np.zeros(v.N, dtype=np.int64))
    simulate(inst, cell, pol, seed=inst.seed)
    sv = pol.reset_args[0]
    assert all(v is not sv for v in pol.views)
    assert not np.may_share_memory(sv.P, pol.views[0].P)


def test_redispatch_log_records_every_round():
    inst, cell = f0r_instance(delta_A=0, seed=60001)
    pol = Recording(redispatch_greedy)
    traj = simulate(inst, cell, pol, seed=inst.seed)
    multi = {t for t in range(inst.H) if traj.rounds[t] > 1}
    assert multi and {e[0] for e in traj.redispatch_log} == multi
    assert len(traj.redispatch_log) == int(traj.rounds[list(multi)].sum())
    by_call = {(t, rnd): x for t, rnd, x in pol.calls}
    for t, rnd, x, revealed in traj.redispatch_log:
        assert np.array_equal(x, by_call[(t, rnd)])
        if rnd == 0:
            assert not revealed.any()
        else:  # reveals only come from earlier, possibly withdrawn, commands
            assert (revealed <= (np.stack([e[2] for e in traj.redispatch_log
                                           if e[0] == t and e[1] < rnd]).max(0) > 0)).all()
    # a withdrawn command exists: someone commanded in an early round is not in the final x
    assert any(((e[2] > 0) & (traj.x[:, e[0]] == 0)).any() for e in traj.redispatch_log)
    # slots with a single round are not logged
    assert not any(traj.rounds[e[0]] == 1 for e in traj.redispatch_log)
