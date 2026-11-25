"""Priority-rule chassis and rule families (POLICY_SPEC 4 and 5): hand views, I1 (MECHANISM 3.4),
validity through simulate() on F0-R cells, floor, re-dispatch and the lint."""
import json
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from indep_streams import independent_tiebreaks

from papere.generator import F0R_CELLS, generate_f0r, generate_kcopy
from papere.infoset import InformationSet, StaticView
from papere.instance import Cell
from papere.policies.base import PopulationParams
from papere.policies.beliefs import CEBelief, PersistBelief, PESBelief
from papere.policies.catalog import FAMILIES
from papere.policies.rules import (LLFPost, PriorityRule, ProbeFirst, RWDFE,
                                   UncorrectableBelief, blocked_now, effective_deadline,
                                   laxity, user_flag_rule)
from papere.sim import simulate

from test_policy_lint import lint_source

ROOT = Path(__file__).resolve().parents[1]
FITTED = PopulationParams(**json.loads((ROOT / "results" / "population_params.json")
                                       .read_text())["values"])
FAM = {f.name: f for f in FAMILIES}


# ------------------------------------------------------------------------- view helpers
def static_of(E, P, a, d, H, dA=1, group=None, L=None, b_mean=None, prior_stuck=None, M=0):
    N = len(E)
    group = np.zeros(N, dtype=np.int64) if group is None else np.asarray(group)
    G = int(group.max()) + 1
    L = np.full((G, H), 1000.0) if L is None else np.asarray(L, dtype=float)
    b_mean = np.zeros((G, H)) if b_mean is None else np.asarray(b_mean, dtype=float)
    ps = np.zeros((N, M), dtype=bool) if prior_stuck is None else np.asarray(prior_stuck, bool)
    pa = np.ones((N, M, H), dtype=np.int64)
    return StaticView(N=N, H=H, P=P, E=E, a=a, d=d, group=group, L=L, b_mean=b_mean,
                      announced=np.ones((N, H), dtype=np.int64), prior_A=pa,
                      prior_stuck=ps, family="F0R", delta_A=dA, delta_b=0)


def view_at(sv, t, x=None, A=None, y=None, rnd=0):
    N, H = sv.N, sv.H
    x = np.zeros((N, H), dtype=np.int64) if x is None else np.asarray(x, dtype=np.int64)
    A = np.full((N, H), -1, dtype=np.int8) if A is None else np.asarray(A, dtype=np.int8)
    y = np.zeros((N, H), dtype=np.int64) if y is None else np.asarray(y, dtype=np.int64)
    return InformationSet.build(sv, t, x, A, y, np.zeros((sv.G, H)), rnd)


def run(policy, sv, view, seed=0):
    policy.reset(sv, np.random.default_rng(seed))
    return policy.act(view)


def rule(base="CE", order="LLF", m=0, k=0, **kw):
    b = {"CE": CEBelief, "PES": PESBelief}[base]()
    return PriorityRule(b, order, m, k, name="t", **kw)


# ------------------------------------------------------------------------ chassis: order
def test_laxity_and_effective_deadline_by_hand():
    sv = static_of(E=[6, 2, 4, 3], P=[2, 2, 2, 1], a=[0] * 4, d=[10, 3, 6, 3], H=10)
    v = view_at(sv, 0)
    b = np.array([6, 2, 4, 3])
    assert laxity(v, b, 0).tolist() == [10 - 3, 3 - 1, 6 - 2, 3 - 3]
    assert laxity(v, b, 2).tolist() == [8 - 3, 1 - 1, 4 - 2, 1 - 3]      # d' = max(t+1, d-k)
    assert effective_deadline(v, 5).tolist() == [5, 1, 1, 1]


def test_llf_order_and_greedy_allocation():
    sv = static_of(E=[6, 2, 4, 3], P=[2, 2, 2, 1], a=[0] * 4, d=[10, 3, 6, 3], H=10,
                   L=np.full((1, 10), 4.0))
    v = view_at(sv, 0)
    # laxities 7, 2, 4, 0 -> order p3, p1, p2, p0 ; x = min(P, b, remaining cap)
    assert run(rule(), sv, v).tolist() == [0, 2, 1, 1]
    sv3 = static_of(E=[6, 2, 4, 3], P=[2, 2, 2, 1], a=[0] * 4, d=[10, 3, 6, 3], H=10,
                    L=np.full((1, 10), 3.0))
    assert run(rule(), sv3, view_at(sv3, 0)).tolist() == [0, 2, 0, 1]


def test_edf_differs_from_llf():
    # A: laxity 2, deadline 6 ; B: laxity 3, deadline 4. cap 1.
    sv = static_of(E=[4, 1], P=[1, 1], a=[0, 0], d=[6, 4], H=8, L=np.full((1, 8), 1.0))
    v = view_at(sv, 0)
    assert run(rule(order="LLF"), sv, v).tolist() == [1, 0]
    assert run(rule(order="EDF"), sv, v).tolist() == [0, 1]


def test_units_capped_by_belief_and_rate():
    sv = static_of(E=[1, 5], P=[3, 2], a=[0, 0], d=[9, 9], H=9)
    assert run(rule(), sv, view_at(sv, 0)).tolist() == [1, 2]


def test_tie_break_is_random_not_by_index_and_fresh_per_act():
    sv = static_of(E=[3] * 6, P=[1] * 6, a=[0] * 6, d=[6] * 6, H=6, L=np.full((1, 6), 2.0))
    v = view_at(sv, 0)
    pol = rule()
    pol.reset(sv, np.random.default_rng(5))
    xs = np.array([pol.act(v) for _ in range(600)])
    assert (xs.sum(axis=1) == 2).all()
    freq = xs.mean(axis=0)
    assert ((freq > 0.2) & (freq < 0.47)).all(), freq        # each is picked ~ 2/6
    assert len({tuple(r) for r in xs}) > 5                    # fresh draw each call
    firsts = {int(np.flatnonzero(run(rule(), sv, v, seed=s))[0]) for s in range(40)}
    assert len(firsts) > 3                                    # differs across policy seeds


def test_tie_break_only_among_ties():
    sv = static_of(E=[3, 3, 1], P=[1, 1, 1], a=[0, 0, 0], d=[6, 6, 9], H=9,
                   L=np.full((1, 9), 1.0))
    v = view_at(sv, 0)
    for s in range(30):                    # laxities 3, 3, 8: the third is never chosen first
        assert run(rule(), sv, v, seed=s)[2] == 0


# ------------------------------------------------------------------- chassis: caps, windows
def test_group_caps_and_margin():
    sv = static_of(E=[5] * 4, P=[3] * 4, a=[0] * 4, d=[6] * 4, H=6, group=[0, 0, 1, 1],
                   L=np.array([[2.0] * 6, [1.0] * 6]))
    v = view_at(sv, 0)
    for s in range(10):
        x = run(rule(), sv, v, seed=s)
        assert x[:2].sum() == 2 and x[2:].sum() == 1
        x1 = run(rule(m=1), sv, v, seed=s)           # caps 1 and 0
        assert x1[:2].sum() == 1 and x1[2:].sum() == 0


def test_negative_cap_is_clipped_to_zero():
    sv = static_of(E=[5, 5], P=[3, 3], a=[0, 0], d=[6, 6], H=6, group=[0, 1],
                   L=np.array([[4.0] * 6, [0.5] * 6]), b_mean=np.array([[0.0] * 6, [1.0] * 6]))
    v = view_at(sv, 0)
    assert v.setpoint_cap(1) == -1
    x = run(rule(), sv, v)
    assert x.tolist() == [3, 0]


def test_windows_are_respected():
    # t = 3: p0 expired (d = 3), p1 active, p2 not yet released (a = 4)
    sv = static_of(E=[4, 4, 4], P=[2, 2, 2], a=[0, 3, 4], d=[3, 8, 9], H=9)
    v = view_at(sv, 3)
    for s in range(5):
        assert run(rule(), sv, v, seed=s).tolist() == [0, 2, 0]


def test_known_complete_is_skipped():
    # dA = 1, t = 3. p0: setpoint at slot 1 with A hidden (-1) -> true debt was 0.
    # p1: confirmed debt 0 through y. p2 owes 2.
    sv = static_of(E=[4, 2, 2], P=[2, 2, 2], a=[0] * 3, d=[9] * 3, H=9)
    x = np.zeros((3, 9), dtype=np.int64)
    x[0, 1] = 1
    x[1, 0] = 2
    y = np.zeros((3, 9), dtype=np.int64)
    y[1, 0] = 2
    A = np.full((3, 9), -1, dtype=np.int8)
    A[1, 0] = 1
    v = view_at(sv, 3, x=x, A=A, y=y)
    for base in ("CE", "PES"):
        assert run(rule(base), sv, v).tolist() == [0, 0, 2]


def test_redispatch_blocks_stuck_and_prefers_revealed_available():
    sv = static_of(E=[3] * 4, P=[1] * 4, a=[0] * 4, d=[9] * 4, H=9, dA=0,
                   L=np.full((1, 9), 1.0))
    A = np.full((4, 9), -1, dtype=np.int8)
    A[0, 2], A[1, 2] = 0, 1                          # column t = 2 : p0 stuck, p1 available
    v = view_at(sv, 2, A=A, rnd=1)
    assert blocked_now(v).tolist() == [True, False, False, False]
    for s in range(40):
        assert run(rule(), sv, v, seed=s).tolist() == [0, 1, 0, 0]
    # without any reveal (first call) p1 has no priority
    v0 = view_at(sv, 2)
    assert len({int(np.flatnonzero(run(rule(), sv, v0, seed=s))[0]) for s in range(40)}) == 4


# -------------------------------------------------------------------------------- floor
class SpyBelief(PESBelief):
    def reset(self, static_view, floored=None, oracle=None):
        self.seen = None if floored is None else np.asarray(floored).copy()
        super().reset(static_view, floored, oracle=oracle)


def test_floor_mask_and_belief_reset():
    sv = static_of(E=[2, 2, 2], P=[1, 1, 1], a=[0] * 3, d=[5] * 3, H=5)
    spy = SpyBelief()
    pol = PriorityRule(spy, "LLF", 0, 0, name="floor", floor=True)
    pol.reset(sv, np.random.default_rng(0))
    fm = pol.floor_mask(sv)
    assert fm.dtype == bool and fm.shape == (3,) and fm.all()
    assert spy.seen is not None and spy.seen.all()
    spy2 = SpyBelief()
    pol2 = PriorityRule(spy2, "LLF", 0, 0, name="nofloor")
    pol2.reset(sv, np.random.default_rng(0))
    assert pol2.floor_mask(sv) is None and spy2.seen is None


# ---------------------------------------------------------------- hand cases per family
def test_persistence_hand_case():
    # dA = 2, t = 5: slots <= 3 confirmed, slot 4 unconfirmed (x = 2 for both).
    # p0 last revealed available (slot 2, delivered 1): debt 3, unconfirmed counted -> 1.
    # p1 last revealed stuck (slot 2): unconfirmed setpoint failed -> debt 4.
    H = 8
    sv = static_of(E=[4, 4], P=[2, 2], a=[0, 0], d=[8, 8], H=H, dA=2,
                   L=np.full((1, H), 3.0))
    x = np.zeros((2, H), dtype=np.int64)
    x[:, 2] = 1
    x[:, 4] = 2
    A = np.full((2, H), -1, dtype=np.int8)
    A[0, 2], A[1, 2] = 1, 0
    y = np.zeros((2, H), dtype=np.int64)
    y[0, 2] = 1
    v = view_at(sv, 5, x=x, A=A, y=y)
    assert v.confirmed_debt.tolist() == [3, 4]
    pol = PriorityRule(PersistBelief("CE"), "LLF", 0, 0, name="persistence")
    # laxity: p0 (8-5) - ceil(1/2) = 2, p1 3 - 2 = 1  -> p1 first: min(2, 4, 3) = 2, p0 gets 1
    for s in range(20):
        assert run(pol, sv, v, seed=s).tolist() == [1, 2]
    # plain CE believes both delivered: debts 1 and 2
    assert run(rule("CE"), sv, v).tolist() == [1, 2]
    # PES: debts 3 and 4, laxity 1 and 1 (tie): either order, never persistence's choice
    # forced; both outcomes occur
    outs = {tuple(run(rule("PES"), sv, v, seed=s)) for s in range(30)}
    assert outs == {(1, 2), (2, 1)}


def test_persistence_uses_base_belief_when_nothing_revealed():
    H = 8
    sv = static_of(E=[4], P=[2], a=[0], d=[8], H=H, dA=2)
    x = np.zeros((1, H), dtype=np.int64)
    x[0, 4] = 2
    v = view_at(sv, 5, x=x)
    assert run(PriorityRule(PersistBelief("CE"), "LLF", name="p"), sv, v).tolist() == [2]   # 4-2
    sv2 = static_of(E=[4], P=[2], a=[0], d=[8], H=H, dA=2, L=np.full((1, H), 1.0))
    v2 = view_at(sv2, 5, x=x)
    assert run(PriorityRule(PersistBelief("PES"), "LLF", name="p"), sv2, v2).tolist() == [1]


def test_uncorrectable_only_pessimism_hand_case():
    # dA = 2, t = 6, unconfirmed slot 5 (x = 2 each). p0: d = 7, 5 + 2 >= 7 uncorrectable ->
    # assumed failed, debt 4. p1: d = 10, correctable -> CE delivered, debt 2. c = 4 both.
    H = 10
    sv = static_of(E=[4, 4], P=[4, 4], a=[0, 0], d=[7, 10], H=H, dA=2)
    x = np.zeros((2, H), dtype=np.int64)
    x[:, 5] = 2
    v = view_at(sv, 6, x=x)
    bel = UncorrectableBelief("CE")
    bel.reset(sv)
    st = bel.compute(v)
    assert st.exp_debt.tolist() == [4.0, 2.0] and st.point
    assert st.tail[:, :4].tolist() == [[1, 1, 1, 1], [1, 1, 0, 0]]
    assert run(PriorityRule(UncorrectableBelief("CE"), "LLF", name="u"), sv, v).tolist() == [4, 2]
    # B = PES: both treated as failed
    assert run(PriorityRule(UncorrectableBelief("PES"), "LLF", name="u"), sv, v).tolist() == [4, 4]
    # plain CE would give 2 and 2
    assert run(rule("CE"), sv, v).tolist() == [2, 2]


def test_uncorrectable_known_complete_stays_zero():
    H = 10
    sv = static_of(E=[4], P=[4], a=[0], d=[7], H=H, dA=2)
    x = np.zeros((1, H), dtype=np.int64)
    x[0, 2] = 1                           # confirmed slot 2 (t - dA = 4), A hidden: complete
    v = view_at(sv, 6, x=x)
    bel = UncorrectableBelief("CE")
    bel.reset(sv)
    assert bel.compute(v).exp_debt.tolist() == [0.0]


def test_probe_first_hand_case():
    # dA = 1, t = 4. p0 released now (a = 4). p1 last revealed stuck. p2 last revealed available.
    # p3 never revealed, not released now. cap 2.
    H = 10
    sv = static_of(E=[3, 3, 3, 3], P=[2, 2, 2, 2], a=[4, 0, 0, 0], d=[10] * 4, H=H, dA=1,
                   L=np.full((1, H), 2.0))
    x = np.zeros((4, H), dtype=np.int64)
    x[1, 1] = x[2, 1] = 1
    A = np.full((4, H), -1, dtype=np.int8)
    A[1, 1], A[2, 1] = 0, 1
    y = np.zeros((4, H), dtype=np.int64)
    y[2, 1] = 1
    v = view_at(sv, 4, x=x, A=A, y=y)
    for s in range(20):
        # probes go to p0 and p1 (cap 2 used), nothing left for the chassis
        assert run(ProbeFirst(PESBelief(), "LLF", 0, 0, name="pf"), sv, v, seed=s).tolist() \
            == [1, 1, 0, 0]
    # cap 6: probes first, then the chassis on the remaining cap (probe is unit one)
    sv6 = static_of(E=[3, 3, 3, 3], P=[2, 2, 2, 2], a=[4, 0, 0, 0], d=[10] * 4, H=H, dA=1,
                    L=np.full((1, H), 6.0))
    v6 = view_at(sv6, 4, x=x, A=A, y=y)
    # probes p0, p1; then laxities 4, 4, 5, 4 for p0, p1, p2, p3: the three tied ones need
    # 1 + 1 + 2 = 4 more units = the remaining cap, p2 gets nothing
    for s in range(10):
        assert run(ProbeFirst(PESBelief(), "LLF", 0, 0, name="pf"), sv6, v6,
                   seed=s).tolist() == [2, 2, 0, 2]


def test_probe_first_probes_count_against_the_cap_and_go_in_priority_order():
    H = 10
    # three released now; cap 2: only two probes, the two with least laxity
    sv = static_of(E=[2, 5, 9], P=[1, 1, 1], a=[4, 4, 4], d=[12, 12, 12], H=H + 2, dA=1,
                   L=np.full((1, H + 2), 2.0))
    v = view_at(sv, 4)
    for s in range(10):
        # laxity 12-4-b: 6, 3, -1 -> p2 then p1
        assert run(ProbeFirst(PESBelief(), "LLF", 0, 0, name="pf"), sv, v, seed=s).tolist() \
            == [0, 1, 1]


def test_probe_first_never_probes_known_complete():
    # dA = 2, t = 5, confirmed <= 3. p0 revealed stuck at slot 1, then a setpoint at slot 2
    # with A hidden (-1) -> known complete. p1 revealed stuck at slot 1, owes. cap 5.
    H = 10
    sv = static_of(E=[3, 3], P=[2, 2], a=[0, 0], d=[10, 10], H=H, dA=2,
                   L=np.full((1, H), 5.0))
    x = np.zeros((2, H), dtype=np.int64)
    x[:, 1] = 1
    x[0, 2] = 1
    A = np.full((2, H), -1, dtype=np.int8)
    A[:, 1] = 0
    v = view_at(sv, 5, x=x, A=A)
    assert run(ProbeFirst(CEBelief(), "LLF", 0, 0, name="pf"), sv, v).tolist() == [0, 2]


def test_probe_first_not_when_stuck_revealed_this_slot():
    H = 6
    sv = static_of(E=[3, 3], P=[2, 2], a=[0, 0], d=[6, 6], H=H, dA=0, L=np.full((1, H), 4.0))
    A = np.full((2, H), -1, dtype=np.int8)
    A[0, 2] = 0                              # revealed stuck at t = 2
    x = np.zeros((2, H), dtype=np.int64)
    v = view_at(sv, 2, x=x, A=A, rnd=1)
    assert run(ProbeFirst(PESBelief(), "LLF", 0, 0, name="pf"), sv, v).tolist() == [0, 2]


def test_user_flag_treats_flagged_participants_as_pes():
    # dA = 2, t = 5, unconfirmed slot 4 with x = 2 for both. c = 3 both (y at slot 2).
    # flagged p0 -> PES debt 3 ; unflagged p1 with B = CE -> debt 1.
    H = 8
    ps = np.array([[True, False], [False, False]])
    sv = static_of(E=[4, 4], P=[3, 3], a=[0, 0], d=[8, 8], H=H, dA=2, prior_stuck=ps, M=2)
    x = np.zeros((2, H), dtype=np.int64)
    x[:, 2] = 1
    x[:, 4] = 2
    A = np.full((2, H), -1, dtype=np.int8)
    A[:, 2] = 1
    y = np.zeros((2, H), dtype=np.int64)
    y[:, 2] = 1
    v = view_at(sv, 5, x=x, A=A, y=y)
    pol = user_flag_rule("CE", "LLF", 0, 0)
    x_ce = run(pol, sv, v)
    assert pol.flagged.tolist() == [True, False]
    assert x_ce.tolist() == [3, 1]
    pol_pes = user_flag_rule("PES", "LLF", 0, 0)
    assert run(pol_pes, sv, v).tolist() == [3, 3]
    # nobody flagged: pure B
    sv0 = static_of(E=[4, 4], P=[3, 3], a=[0, 0], d=[8, 8], H=H, dA=2,
                    prior_stuck=np.zeros((2, 2), bool), M=2)
    pol0 = user_flag_rule("CE", "LLF", 0, 0)
    assert run(pol0, sv0, view_at(sv0, 5, x=x, A=A, y=y)).tolist() == [1, 1]
    # M = 0: no history at all
    sv_m0 = static_of(E=[4, 4], P=[3, 3], a=[0, 0], d=[8, 8], H=H, dA=2)
    assert run(user_flag_rule("CE", "LLF", 0, 0), sv_m0, view_at(sv_m0, 5, x=x, A=A, y=y)
               ).tolist() == [1, 1]


# ------------------------------------------------------------------------------ RWDF-E
HAND_PARAMS = PopulationParams(alpha=1.0, beta=3.0, q_bar_stuck=1.0, q_bar_total=4.0,
                               n_aa=90.0, n_as=10.0, n_ss=5.0, n_sa=5.0)


def test_rwdf_index_by_hand():
    # M = 0 : q_i = alpha/(alpha+beta) = 0.25, p_stay = 0.9, r = 0.5.
    # t = 3, dA = 2: confirmed slots <= 1, unconfirmed slot 2 (p0 only), nothing revealed.
    # P(avail_h | avail now): 1, .9, .86, .844 ; P(avail_h | stuck now): 0, .5, .7, .78
    # P(Z_2 avail) = .75 * .86 + .25 * .7 = .82  -> qhat_0 = .18
    # P(Z_3 avail) = .75 * .844 + .25 * .78 = .828 = phat for both
    H = 8
    sv = static_of(E=[4, 3], P=[1, 1], a=[0, 0], d=[8, 8], H=H, dA=2, L=np.full((1, H), 1.0))
    x = np.zeros((2, H), dtype=np.int64)
    x[0, 2] = 1
    v = view_at(sv, 3, x=x)
    pol = RWDFE(HAND_PARAMS, "PES", "LLF", 0, 0, literal=True)
    pol.reset(sv, np.random.default_rng(0))
    assert abs(pol.hmm.q[0] - 0.25) < 1e-12 and abs(pol.hmm.p_stay - 0.9) < 1e-12
    assert abs(pol.hmm.r - 0.5) < 1e-12
    n, qhat = pol._fail_prob(v)
    assert n.tolist() == [1, 0] and abs(qhat[0] - 0.18) < 1e-12 and qhat[1] == 0.0
    x_out = pol.act(v)
    phat = 0.828
    assert abs(pol.last_index[0] - 4 * phat * 0.18) < 1e-12
    assert abs(pol.last_index[1] - 3 * phat) < 1e-12
    assert x_out.tolist() == [0, 1]                  # 0.596 < 2.484 -> p1 first, cap 1
    # a bigger confirmed shortfall for p0 flips the order: 20 * .828 * .18 = 2.98 > 2.484
    sv2 = static_of(E=[20, 3], P=[1, 1], a=[0, 0], d=[80, 8], H=H + 72, dA=2,
                    L=np.full((1, H + 72), 1.0))
    x2 = np.zeros((2, H + 72), dtype=np.int64)
    x2[0, 2] = 1
    pol2 = RWDFE(HAND_PARAMS, "PES", "LLF", 0, 0, literal=True)
    pol2.reset(sv2, np.random.default_rng(0))
    x_out2 = pol2.act(view_at(sv2, 3, x=x2))
    assert x_out2.tolist() == [1, 0]


def test_rwdf_failure_probability_uses_last_revealed_state():
    # p0 revealed stuck at slot 1 (dA = 2, t = 4, unconfirmed slots 3 -> x there)
    # Z_3 from a stuck state at slot 1 : two steps -> P(avail) = .7 -> qhat = .3 ; phat at t=4:
    # three steps from stuck -> .78
    H = 8
    sv = static_of(E=[4], P=[1], a=[0], d=[8], H=H, dA=2)
    x = np.zeros((1, H), dtype=np.int64)
    x[0, 1] = x[0, 3] = 1
    A = np.full((1, H), -1, dtype=np.int8)
    A[0, 1] = 0
    v = view_at(sv, 4, x=x, A=A)
    pol = RWDFE(HAND_PARAMS, "PES", "LLF", 0, 0)
    pol.reset(sv, np.random.default_rng(0))
    n, qhat = pol._fail_prob(v)
    assert n.tolist() == [1] and abs(qhat[0] - 0.3) < 1e-12
    pol.act(v)
    assert abs(pol.last_index[0] - 4 * 0.78 * 0.3) < 1e-12


def test_rwdf_literal_ties_by_order_on_deadline_then_random():
    H = 8
    sv = static_of(E=[3, 3], P=[1, 1], a=[0, 0], d=[8, 5], H=H, dA=2, L=np.full((1, H), 1.0))
    v = view_at(sv, 3)
    for s in range(15):
        pol = RWDFE(HAND_PARAMS, "PES", "EDF", 0, 0, literal=True)
        pol.reset(sv, np.random.default_rng(s))
        assert pol.act(v).tolist() == [0, 1]         # equal index, earlier deadline first


def test_rwdf_e_order_is_o_first_then_index():
    # Same state as the index-by-hand case: indexes 0.596 (p0) and 2.484 (p1); laxity (t=3,
    # d=8): p0 5-4 = 1, p1 5-3 = 2.  Literal: index first -> p1.  rwdf_e: LLF first -> p0.
    H = 8
    sv = static_of(E=[4, 3], P=[1, 1], a=[0, 0], d=[8, 8], H=H, dA=2, L=np.full((1, H), 1.0))
    x = np.zeros((2, H), dtype=np.int64)
    x[0, 2] = 1
    v = view_at(sv, 3, x=x)
    lit = RWDFE(HAND_PARAMS, "PES", "LLF", 0, 0, literal=True)
    assert run(lit, sv, v).tolist() == [0, 1]
    new = RWDFE(HAND_PARAMS, "PES", "LLF", 0, 0)
    assert run(new, sv, v).tolist() == [1, 0]
    assert abs(new.last_index[1] - 3 * 0.828) < 1e-12
    # equal laxity: the index decides (p0: 4 units P=2 -> lax 5-2=3 ; p1: 5 units P=2 -> 5-3=2
    # is different) -> build equal laxity with E=[3,3]: p1 has the larger index (no setpoint)
    sv2 = static_of(E=[3, 3], P=[1, 1], a=[0, 0], d=[8, 8], H=H, dA=2, L=np.full((1, H), 1.0))
    for s in range(10):
        pol = RWDFE(HAND_PARAMS, "PES", "LLF", 0, 0)
        pol.reset(sv2, np.random.default_rng(s))
        assert pol.act(view_at(sv2, 3, x=x)).tolist() == [0, 1]


def test_rwdf_e_at_delta_A_zero_is_not_catastrophically_worse_than_llf():
    cell = f0r_cell(0, 0, 0.95)
    res = {"rwdf_e": 0, "rwdf_e_literal": 0, "pes_llf": 0}
    for seed in (60000, 60001, 60002, 60003):
        inst = generate_f0r(seed, cell)
        for n in res:
            pol = FAM[n].make(FAM[n].default, FITTED)
            res[n] += int(simulate(inst, cell, pol, seed).r_final.sum())
    assert res["rwdf_e"] <= 1.15 * res["pes_llf"] + 5, res


def test_user_flag_default_differs_from_sym_margin_pes_with_a_flagged_participant():
    assert FAM["user_flag"].default["B"] == "CE"
    H = 8
    ps = np.array([[True], [False]])
    sv = static_of(E=[4, 4], P=[3, 3], a=[0, 0], d=[8, 8], H=H, dA=2, prior_stuck=ps, M=1)
    x = np.zeros((2, H), dtype=np.int64)
    x[:, 2] = 1
    x[:, 4] = 2
    A = np.full((2, H), -1, dtype=np.int8)
    A[:, 2] = 1
    y = np.zeros((2, H), dtype=np.int64)
    y[:, 2] = 1
    v = view_at(sv, 5, x=x, A=A, y=y)
    uf = FAM["user_flag"].make(FAM["user_flag"].default, FITTED)
    sym = FAM["sym_margin"].make(FAM["sym_margin"].default, FITTED)
    assert FAM["sym_margin"].default["B"] == "PES"
    assert run(uf, sv, v).tolist() == [3, 1]          # flagged PES (3), unflagged CE (1)
    assert run(sym, sv, v).tolist() == [3, 3]         # sym_margin PES: both 3


# ----------------------------------------------------------------------------- LLF-POST
def _kcopy_identified(seed_range=range(60000, 60050)):
    """K = 1 pooled c = 1, q = 0.5, M = 3, with A having a prior stuck event and B none."""
    cell = Cell(family="KCOPY", M=3, delta_A=2, delta_b=0, q=0.5, c=1.0, cap_mode="pooled")
    for sd in seed_range:
        inst = generate_kcopy(sd, cell, K=1)
        if inst.prior_stuck[inst.cls == 1].any():
            return inst, cell
    raise AssertionError("no seed with an identified A copy")


def test_llf_post_hedges_identified_copy_first():
    inst, cell = _kcopy_identified()
    iA = int(np.flatnonzero(inst.cls == 1)[0])
    iB = int(np.flatnonzero(inst.cls == 0)[0])
    iD = int(np.flatnonzero(inst.cls == 2)[0])
    with independent_tiebreaks():
        for sd in range(5):
            pol = LLFPost(FITTED, "LLF", 0.0, 0, 0, name=f"llf_post_{sd}")
            traj = simulate(inst, cell, pol, inst.seed)
            assert traj.x[:, 0].tolist().count(1) == 2 and traj.x[iD, 0] == 0
            assert traj.x[iD, 1] == 1 and traj.x[iA, 1] == 1 and traj.x[iB, 1] == 0
        # the oblivious PES-LLF has no such preference (A and B are twins to it)
        seen = set()
        for sd in range(40):
            p = PriorityRule(PESBelief(), "LLF", 0, 0, name=f"pes_{sd}")
            seen.add(int(simulate(inst, cell, p, inst.seed).x[iA, 1]))
    assert seen == {0, 1}


def test_llf_post_theta_skips_and_unit_counts():
    H = 8
    sv = static_of(E=[3, 2], P=[3, 3], a=[0, 0], d=[8, 8], H=H, dA=3)
    # no setpoints yet: tail is 1 for k <= c_i, so units = min(P, c_i)
    assert run(LLFPost(FITTED, "LLF", 0.0, 0, 0), sv, view_at(sv, 0)).tolist() == [3, 2]
    # two 1-unit setpoints in flight for p0 (slots 2, 3; t = 4): the e1 tail is
    # [1, .116, .069] (debt >= 1 surely, >= 2 w.p. .116, >= 3 w.p. .069)
    x = np.zeros((2, H), dtype=np.int64)
    x[0, 2] = x[0, 3] = 1
    v = view_at(sv, 4, x=x)
    pol = LLFPost(FITTED, "LLF", 0.0, 0, 0)
    pol.reset(sv, np.random.default_rng(0))
    tail = pol.hmm.compute(v).tail[0]
    assert tail[0] == pytest.approx(1.0) and 0.05 < tail[2] < tail[1] < 0.2
    assert pol.act(v).tolist() == [3, 2]                                  # theta 0 : all 3
    assert run(LLFPost(FITTED, "LLF", 0.05, 0, 0), sv, v).tolist() == [3, 2]
    assert run(LLFPost(FITTED, "LLF", 0.2, 0, 0), sv, v).tolist() == [1, 2]   # only tail > .2
    # a participant whose debt is unlikely is skipped altogether: one 2-unit setpoint at slot 3
    # on E = 2 leaves debt >= 1 only if it failed (p_pos ~ .14 < .5)
    sv2 = static_of(E=[2, 2], P=[3, 3], a=[0, 0], d=[8, 8], H=H, dA=3)
    x2 = np.zeros((2, H), dtype=np.int64)
    x2[0, 3] = 2
    v2 = view_at(sv2, 4, x=x2)
    assert run(LLFPost(FITTED, "LLF", 0.5, 0, 0), sv2, v2).tolist() == [0, 2]
    assert run(LLFPost(FITTED, "LLF", 0.0, 0, 0), sv2, v2)[0] == 2


# -------------------------------------------------------------------- I1 (MECHANISM 3.4)
def i1_instance(omega):
    cell = Cell(family="KCOPY", M=0, delta_A=2, delta_b=0, q=0.5, c=1.0, cap_mode="pooled")
    for seed in range(60000, 60050):
        inst = generate_kcopy(seed, cell, K=1)
        stuck = inst.availability()[inst.cls == 1, 0][0] == 0
        if stuck == (omega == 0):
            return inst, cell
    raise AssertionError("no seed")


def i1_residual(policy, omega):
    inst, cell = i1_instance(omega)
    return int(simulate(inst, cell, policy, inst.seed).r_final.sum())


def test_i1_ce_llf_and_ce_edf_reproduce_the_ce_row():
    for order in ("LLF", "EDF"):
        for sd in range(8):
            assert i1_residual(PriorityRule(CEBelief(), order, name=f"ce{sd}"), 1) == 0
            assert i1_residual(PriorityRule(CEBelief(), order, name=f"ce{sd}"), 0) == 1


def test_i1_pes_llf_three_way_tie_matches_a_mixture_of_two_rows():
    """PES-LLF at t = 1 sees A, B and D with debt 1, laxity 0 and cap 2: a 3-way tie.

    D left out (prob 1/3) is the row 'pessimistic debt, A and B first' (R = 1 in both omegas);
    D served (prob 2/3) is the row 'D first, then A or B by symmetry' (R = 0 in omega1,
    1/2 in omega0). So E[R | omega1] = 1/3, E[R | omega0] = 1/3 + 2/3 * 1/2 = 2/3, mean 1/2.
    """
    n = 600
    with independent_tiebreaks():
        r1 = np.mean([i1_residual(PriorityRule(PESBelief(), "LLF", name=f"p{s}"), 1)
                      for s in range(n)])
        r0 = np.mean([i1_residual(PriorityRule(PESBelief(), "LLF", name=f"p{s}"), 0)
                      for s in range(n)])
    assert abs(r1 - 1 / 3) < 0.06 and abs(r0 - 2 / 3) < 0.06
    assert abs((r1 + r0) / 2 - 0.5) < 0.05


def test_i1_floor_and_probe_run():
    for omega in (0, 1):
        for pol in (PriorityRule(PESBelief(), "LLF", name="fl", floor=True),
                    ProbeFirst(CEBelief(), "LLF", name="pf")):
            assert i1_residual(pol, omega) in (0, 1, 2, 3)


# ------------------------------------------------------- validity through simulate()
def f0r_cell(dA, db, rho, M=3):
    return Cell(family="F0R", M=M, delta_A=dA, delta_b=db, rho=rho, r=0.3)


RULE_FAMILIES = ["ce_llf", "ce_edf", "pes_llf", "sym_margin", "persistence", "uncorr_pes",
                 "probe_first", "floor", "user_flag", "rwdf_e", "rwdf_e_literal", "llf_post"]
MPC_FAMILIES = ["mpc_ce", "mpc_pes", "pop_mpc", "guarded_mpc_e1", "oracle_mpc"]
CELLS = [f0r_cell(dA, db, rho) for dA in (0, 1, 2, 4) for db in (0, 2)
         for rho in (0.95, 1.15, 0.7)]


def _configs(fam, rng):
    cfgs = [fam.default]
    if len(fam.grid) > 1:
        pick = rng.choice(len(fam.grid), size=2, replace=False)
        cfgs += [fam.grid[int(i)] for i in pick]
    return cfgs


@pytest.mark.parametrize("name", RULE_FAMILIES)
def test_rule_family_valid_on_f0r_cells(name):
    fam = FAM[name]
    rng = np.random.default_rng(abs(hash(name)) % 1000)
    rounds_seen = 0
    for ci, cell in enumerate(CELLS):
        seed = 60000 + ci
        inst = generate_f0r(seed, cell)
        for cfg in _configs(fam, rng):
            pol = fam.make(cfg, FITTED)
            traj = simulate(inst, cell, pol, seed)          # raises InvalidAction on a breach
            assert traj.x.shape == (inst.N, inst.H) and traj.cpu_ms.shape == (inst.H,)
            if cell.delta_A == 0:
                rounds_seen += int(traj.rounds.max() > 1)
            if name == "floor":
                assert traj.floored.all()
            else:
                assert not traj.floored.any()
    if name != "floor":
        assert rounds_seen > 0           # the re-dispatch loop was exercised at dA = 0


@pytest.mark.parametrize("name", MPC_FAMILIES)
def test_mpc_family_valid_on_f0r_cells(name):
    fam = FAM[name]
    for dA, db, rho in [(0, 0, 0.95), (1, 2, 1.15), (2, 0, 0.7), (4, 2, 0.95)]:
        cell = f0r_cell(dA, db, rho)
        inst = generate_f0r(60010 + dA, cell)
        traj = simulate(inst, cell, fam.make(fam.default, FITTED), inst.seed)
        assert traj.x.sum() > 0


def test_probe_first_sends_a_probe_at_release_in_simulation():
    cell = f0r_cell(2, 0, 0.95)
    inst = generate_f0r(60005, cell)
    traj = simulate(inst, cell, FAM["probe_first"].make(FAM["probe_first"].default, FITTED),
                    inst.seed)
    # cap rho = .95 is tight but every participant released at t with a positive cap has x >= 1
    # in the probe pass unless the cap ran out; check that no released participant is skipped
    # while a later-priority unit went to a non-probe in the same slot
    for t in range(inst.H):
        rel = np.flatnonzero((inst.a == t))
        if rel.size and traj.x[:, t].sum() > 0:
            assert traj.x[rel, t].sum() >= 1


def test_rules_never_command_a_participant_whose_stuck_state_is_revealed_now():
    # dA = 0: a participant found stuck in a round is not commanded again in the same slot
    cell = f0r_cell(0, 0, 0.95)
    n_stuck_revealed = 0
    for seed in (60010, 60011, 60012):
        inst = generate_f0r(seed, cell)
        pol = FAM["ce_llf"].make(FAM["ce_llf"].default, FITTED)
        traj = simulate(inst, cell, pol, seed)
        for (t, rnd, xt, revealed) in traj.redispatch_log:
            if rnd > 0:
                stuck = revealed & (inst.availability()[:, t] == 0)
                n_stuck_revealed += int(stuck.sum())
                assert (xt[stuck] == 0).all()
    # not vacuous: tuning seeds 60010-60012 do reveal stuck participants in re-dispatch rounds
    assert n_stuck_revealed > 0


# ------------------------------------------------------------------------------------ lint
@pytest.mark.parametrize("fname", ["rules.py", "catalog.py"])
def test_lint_clean(fname):
    path = ROOT / "src" / "papere" / "policies" / fname
    assert lint_source(path.read_text(), "papere.policies." + path.stem) == []
