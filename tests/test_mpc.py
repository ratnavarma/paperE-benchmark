"""MPC tests (POLICY_SPEC Section 6): NC2, I1 and I_K hedging, feasibility, speed.

Hand beliefs (point CE/PES and an exact two-slot K-copy posterior) live here so the MPC can
be checked on its own; the integration tests use ``papere.policies.beliefs`` when present.
"""
from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from indep_streams import independent_tiebreaks
from scipy.stats import chisquare

from papere.generator import F0R_CELLS, generate_f0r, generate_kcopy
from papere.infoset import InformationSet, StaticView
from papere.instance import Cell
from papere.policies.base import PopulationParams, PosteriorState
from papere.policies import mpc as mpc_mod
from papere.policies.mpc import MPCPolicy, guarded_mpc, mpc_ce, mpc_pes
from papere.prop_enum import (closed_oblivious, closed_posterior, closed_prop3_per_copy,
                              closed_prop3_pooled)
from papere.sim import simulate


try:
    from papere.policies import beliefs as B
except ImportError:          # beliefs.py not built yet
    B = None
needs_beliefs = pytest.mark.skipif(B is None, reason="papere.policies.beliefs not available")

# Binding seed rule: tests use only the tuning seeds 60000-60049 (SEED_LEDGER).
TUNING_SEEDS = range(60000, 60050)
F0R_SEEDS = TUNING_SEEDS
KCOPY_SEEDS = TUNING_SEEDS
PARAMS_PATH = Path(__file__).resolve().parents[1] / "results" / "population_params.json"


def population_params() -> PopulationParams:
    if PARAMS_PATH.exists():
        return PopulationParams(**json.loads(PARAMS_PATH.read_text())["values"])
    return PopulationParams(alpha=0.29, beta=1.81, q_bar_stuck=1064.0, q_bar_total=7500.0,
                            n_aa=156574.0, n_as=3204.0, n_ss=8945.0, n_sa=3777.0)


def i1_instance(omega: int):
    """I1 = K-copy K = 1, pooled, c = 1, q = 1/2, delta_A = 2, from a tuning seed.

    omega 0 = A stuck at slot 0. Returns instance, cell and role indices.
    """
    cell = Cell(family="KCOPY", M=0, delta_A=2, delta_b=0, q=0.5, c=1.0, cap_mode="pooled")
    for seed in TUNING_SEEDS:
        inst = generate_kcopy(seed, cell, K=1)
        stuck = inst.availability()[inst.cls == 1, 0][0] == 0
        if stuck == (omega == 0):
            return inst, cell, {k: int(np.flatnonzero(inst.cls == v)[0])
                                for k, v in (("A", 1), ("B", 0), ("D", 2))}
    raise AssertionError("no tuning seed gives this realization")


# --------------------------------------------------------------------------- beliefs
class HandPoint:
    """CE or PES point belief, availability 1 inside the window (POLICY_SPEC 2)."""

    def __init__(self, kind: str) -> None:
        self.kind = kind
        self.name = f"hand-{kind}"
        self.calls = 0
        self.reset_args = None

    def reset(self, static_view, floored=None, oracle=None):
        self.reset_args = (floored, oracle)
        self.sv = static_view
        self.kmax = int(static_view.E.max())

    def compute(self, view: InformationSet) -> PosteriorState:
        self.calls += 1
        t, N, H = view.t, view.N, view.H
        c = np.asarray(view.confirmed_debt, dtype=np.int64)
        lo = max(t - view.delta_A + 1, 0)
        unconf = view.x_past[:, lo:t].sum(axis=1) if lo < t else np.zeros(N, np.int64)
        debt = np.maximum(c - unconf, 0) if self.kind == "CE" else c
        tail = (debt[:, None] >= np.arange(1, self.kmax + 1)[None, :]).astype(float)
        tau = np.arange(H)[None, :]
        pav = ((tau >= np.maximum(view.a, t)[:, None]) & (tau < view.d[:, None])).astype(float)
        return PosteriorState(t=t, tail=tail, tail_avail=tail[:, :, None] * pav[:, None, :],
                              p_avail=pav, exp_debt=debt.astype(float), p_pos=tail[:, 0],
                              point=True)


class KCopyPosterior:
    """Exact posterior on I_K-like instances (H = 2, P = E = 1, lag >= 2) given q_i.

    Stuck at slot 0 with probability q_i, available at slot 1 always. At t = 1 a twin that
    got a slot-0 setpoint still owes 1 with probability q_i.
    """

    def __init__(self, q) -> None:
        self.q = np.asarray(q, dtype=float)
        self.name = "kcopy-post"

    def reset(self, static_view, floored=None, oracle=None):
        assert static_view.H == 2 and static_view.delta_A >= 2

    def compute(self, view):
        t, N = view.t, view.N
        q = self.q
        tail = np.ones((N, 1))
        pav = np.zeros((N, 2))
        tav = np.zeros((N, 1, 2))
        if t == 0:
            pav[:, 0], pav[:, 1] = 1 - q, 1.0
            tav[:, 0, 0], tav[:, 0, 1] = 1 - q, 1.0
        else:
            served = view.x_past[:, 0] > 0
            tail[served, 0] = q[served]
            pav[:, 1] = 1.0
            tav[:, 0, 1] = tail[:, 0]
        return PosteriorState(t=t, tail=tail, tail_avail=tav, p_avail=pav,
                              exp_debt=tail[:, 0].copy(), p_pos=tail[:, 0].copy(), point=False)


class Recorder:
    """Wraps a policy; checks every action against the policy's own caps and windows."""

    def __init__(self, pol: MPCPolicy) -> None:
        self.pol, self.name, self.privileged = pol, pol.name, pol.privileged
        self.calls, self.rounds_seen = 0, set()

    def reset(self, static_view, rng, oracle=None):
        self.pol.reset(static_view, rng, oracle)

    def floor_mask(self, static_view):
        return self.pol.floor_mask(static_view)

    def act(self, view):
        x = self.pol.act(view)
        self.calls += 1
        self.rounds_seen.add(view.redispatch_round)
        assert x.dtype == np.int64 and x.shape == (view.N,)
        assert (x >= 0).all() and (x <= view.P).all()
        assert (x[~view.active] == 0).all()
        for g in range(view.G):
            assert x[view.group == g].sum() <= max(0, view.setpoint_cap(g, self.pol.m))
        col = mpc_mod.current_column(view)
        if col is not None:                    # never command a participant revealed stuck
            assert (x[col == 0] == 0).all()
        return x


def roles(inst):
    return {r: np.flatnonzero(inst.cls == v) for r, v in (("A", 1), ("B", 0), ("D", 2))}


def kcopy_cells(K):
    out = []
    for c in sorted({0, K // 2, K, 3 * K // 2, 2 * K}):     # K even: all integral
        out.append(Cell(family="KCOPY", M=0, delta_A=2, delta_b=0, q=0.4, c=float(c),
                            cap_mode="pooled"))
    for c in (0, K, 2 * K):
        out.append(Cell(family="KCOPY", M=0, delta_A=2, delta_b=0, q=0.4, c=float(c),
                        cap_mode="per_copy"))
    return out


# --------------------------------------------------------------------------- NC2
NC2_CELLS = [c for c in F0R_CELLS if c.M == 3 and c.rho == 0.95 and c.r == 0.3]


@needs_beliefs
@pytest.mark.parametrize("cell", NC2_CELLS, ids=lambda c: c.cell_id)
def test_nc2_guarded_ce_equals_mpc_ce_decision_for_decision(cell):
    """NC2: guarded MPC with the CE belief and gamma = 0 is MPC-CE (k = 0), same W and m.

    Both get the same tie-break stream (same name); the CE credit is 0 for every gamma,
    so gamma = 1 is checked too.
    """
    n_cmp = 0
    for seed in list(F0R_SEEDS)[:2]:
        inst = generate_f0r(seed, cell)
        for W in (2, 8, 24):
            for m in (0, 2):
                ref = simulate(inst, cell, mpc_ce(W, m, 0, name="nc2"), seed)
                for gamma in (0.0, 1.0):
                    got = simulate(inst, cell,
                                   guarded_mpc(B.CEBelief(), W, m, gamma, name="nc2"), seed)
                    assert np.array_equal(got.x, ref.x), (cell.cell_id, seed, W, m, gamma)
                    assert np.array_equal(got.rounds, ref.rounds)
                    assert [e[2].tolist() for e in got.redispatch_log] == \
                        [e[2].tolist() for e in ref.redispatch_log]
                    n_cmp += 1
    assert n_cmp == 24


# --------------------------------------------------------------------------- I1
def run(inst, cell, pol):
    return simulate(inst, cell, pol, inst.seed)


def test_i1_ce_mpc_gives_the_ce_schedule():
    for omega, want_R in ((1, 0), (0, 1)):
        inst, cell, idx = i1_instance(omega)
        tr = run(inst, cell, MPCPolicy(HandPoint("CE"), 2, 0, name="ce"))
        assert tr.x[[idx["A"], idx["B"], idx["D"]]].tolist() == [[1, 0], [1, 0], [0, 1]]
        assert int(tr.r_final.sum()) == want_R


def test_i1_posterior_mpc_hedges_A_at_slot_1():
    """q_A = 1/2, q_B = q_D = 0: A is covered at slot 1 with D; R = 0 in both realizations."""
    for omega in (0, 1):
        inst, cell, idx = i1_instance(omega)
        q = np.where(inst.cls == 1, 0.5, 0.0)
        tr = run(inst, cell, MPCPolicy(KCopyPosterior(q), 2, 0, gamma=1.0, name="post"))
        assert tr.x[idx["A"], 1] == 1 and tr.x[idx["D"], 1] == 1 and tr.x[idx["B"], 0] == 1
        assert int(tr.r_final.sum()) == 0


@needs_beliefs
def test_i1_oracle_hmm_mpc_hedges_A_at_slot_1():
    for omega in (0, 1):
        inst, cell, idx = i1_instance(omega)
        pol = guarded_mpc(B.HMMBelief(population_params(), "oracle"), 2, 0, 1.0,
                          name="oracle", privileged=True)
        tr = run(inst, cell, pol)
        assert tr.x[idx["A"], 1] == 1 and tr.x[idx["D"], 1] == 1
        assert int(tr.r_final.sum()) == 0


def test_i1_pes_mpc_is_oblivious():
    """PES MPC cannot tell A from B (MECHANISM 3.5: E[R] >= 1/4 for any oblivious policy).

    It serves A and B at slot 0 and, at slot 1, two of the three equal-value units
    {A, B, D} chosen uniformly by the tie-break: E[R] = 1/3 + (2/3)(1/2)(1/2) = 1/2.
    """
    inst, cell, idx = i1_instance(0)
    hits = {"A": 0, "B": 0, "D": 0}
    n = 600
    with independent_tiebreaks():
        for s in range(n):
            tr = run(inst, cell, MPCPolicy(HandPoint("PES"), 2, 0, name=f"pes{s}"))
            assert tr.x[idx["A"], 0] == 1 and tr.x[idx["B"], 0] == 1 and tr.x[:, 1].sum() == 2
            for r in hits:
                hits[r] += int(tr.x[idx[r], 1])
    assert chisquare(list(hits.values())).pvalue > 1e-3
    for r in hits:
        assert abs(hits[r] / n - 2 / 3) < 4 * np.sqrt((2 / 9) / n)


# --------------------------------------------------------------------------- I_K by hand
def slot1_cover(tr, inst):
    """Indices of twins with a slot-1 setpoint."""
    tw = np.flatnonzero(inst.cls != 2)
    return set(tw[tr.x[tw, 1] > 0].tolist())


def spare_per_group(inst, cell, K):
    return int(cell.c) if cell.cap_mode == "pooled" else int(cell.c) // K


@pytest.mark.parametrize("K", (2, 4, 8))
def test_ik_point_posterior_serves_every_D_and_fills_spare_with_twins(K):
    for cell in kcopy_cells(K):
        for seed in list(KCOPY_SEEDS)[:3]:
            inst = generate_kcopy(seed, cell, K=K)
            q = np.full(inst.N, 0.3)
            tr = run(inst, cell, MPCPolicy(KCopyPosterior(q), 2, 0, gamma=1.0, name="sym"))
            R = roles(inst)
            assert (tr.x[R["D"], 1] == 1).all()
            assert ((tr.x[:, 0] + tr.x[:, 1])[np.concatenate([R["A"], R["B"]])] >= 1).all()
            sp = spare_per_group(inst, cell, K)
            cov = slot1_cover(tr, inst)
            if cell.cap_mode == "pooled":
                assert len(cov) == min(sp, 2 * K)
            else:
                for g in range(K):
                    tw = [i for i in cov if inst.group[i] == g]
                    assert len(tw) == min(sp, 2)


@pytest.mark.parametrize("cap_mode,K,c", [("pooled", 4, 2), ("pooled", 4, 4),
                                          ("pooled", 2, 1), ("per_copy", 4, 4)])
def test_ik_symmetric_posterior_spreads_hedges_uniformly(cap_mode, K, c):
    cell = Cell(family="KCOPY", M=0, delta_A=2, delta_b=0, q=0.4, c=float(c), cap_mode=cap_mode)
    inst = generate_kcopy(KCOPY_SEEDS[0], cell, K=K)
    twins = np.flatnonzero(inst.cls != 2)
    q = np.full(inst.N, 0.3)
    n = 400
    counts = np.zeros(inst.N)
    with independent_tiebreaks():       # replicates need independent tie-break streams
        for s in range(n):
            tr = run(inst, cell, MPCPolicy(KCopyPosterior(q), 2, 0, name=f"sym{s}"))
            assert (tr.x[inst.cls == 2, 1] == 1).all()
            counts += tr.x[:, 1] > 0
    obs = counts[twins]
    assert obs.sum() == n * c                       # c hedges per run (per-copy: c/K per copy)
    assert chisquare(obs).pvalue > 1e-3


@pytest.mark.parametrize("K", (2, 4, 8))
def test_ik_identified_copies_are_hedged_first(K):
    rng = np.random.default_rng(7)
    for cell in kcopy_cells(K):
        for seed in list(KCOPY_SEEDS)[:3]:
            inst = generate_kcopy(seed, cell, K=K)
            R = roles(inst)
            ident = rng.choice(R["A"], size=max(1, K // 2), replace=False)
            q = np.full(inst.N, 0.1)
            q[ident] = 0.6
            tr = run(inst, cell, MPCPolicy(KCopyPosterior(q), 2, 0, gamma=1.0, name="id"))
            cov = slot1_cover(tr, inst)
            assert (tr.x[R["D"], 1] == 1).all()
            sp = spare_per_group(inst, cell, K)
            if cell.cap_mode == "pooled":
                if sp >= ident.size:
                    assert set(ident.tolist()) <= cov
                else:
                    assert cov <= set(ident.tolist())
            else:
                for i in ident:                     # its copy's spare goes to it first
                    if sp >= 1:
                        assert i in cov


# --------------------------------------------------------------------------- I_K, HMM, MC
def mc_residual(cell, K, make, cond, n_rng=3):
    """Mean residual over KCOPY_SEEDS x n_rng policy streams, SE from per-seed means.

    Also the mean of R minus ``cond(inst)``, its expectation given the seed's realized
    stuck pattern and prior history (removes the common-mode seed noise).
    """
    per_seed, diff = [], []
    with independent_tiebreaks(1):      # replicates need independent tie-break streams
        for seed in KCOPY_SEEDS:
            inst = generate_kcopy(seed, cell, K=K)
            r = np.mean([run(inst, cell, make(f"mc{j}")).r_final.sum()
                         for j in range(n_rng)])
            per_seed.append(r)
            diff.append(r - cond(inst))
    a, b = np.asarray(per_seed), np.asarray(diff)
    n = np.sqrt(a.size)
    return a.mean(), a.std(ddof=1) / n, b.mean(), b.std(ddof=1) / n


def stuck_A(inst):
    return (inst.availability()[:, 0] == 0) & (inst.cls == 1)


def cond_symmetric(c, K):
    return lambda inst: stuck_A(inst).sum() * (1 - min(c, 2 * K) / (2 * K))


def cond_oracle(c, K):
    return lambda inst: stuck_A(inst).sum() * (1 - min(c, K) / K)


def cond_e1(cap_mode, K):
    """c = K: identified A copies covered; the rest spread over the unidentified twins."""
    def f(inst):
        ident = (inst.cls == 1) & inst.prior_stuck.any(axis=1)
        n_u = (stuck_A(inst) & ~ident).sum()
        if cap_mode == "pooled":
            return n_u * K / (2 * K - ident.sum())
        return n_u / 2
    return f


def assert_close(mean, se, target, label):
    tol = 4 * max(se, 1e-9) + 1e-9
    assert abs(mean - float(target)) <= tol, \
        f"{label}: {mean:.3f} +- {se:.3f} vs {float(target):.3f}"


@needs_beliefs
@pytest.mark.parametrize("cap_mode,c", [("pooled", 0), ("pooled", 2), ("pooled", 4),
                                        ("pooled", 6), ("pooled", 8), ("per_copy", 4),
                                        ("per_copy", 8)])
def test_ik_population_and_oracle_mpc_reach_enumerated_optima(cap_mode, c):
    K, q = 4, 0.4
    cell = Cell(family="KCOPY", M=3, delta_A=2, delta_b=0, q=q, c=float(c), cap_mode=cap_mode)
    pp = population_params()
    m, se, dm, dse = mc_residual(cell, K, lambda nm: guarded_mpc(
        B.HMMBelief(pp, "population"), 2, 0, 1.0, name=nm), cond_symmetric(c, K))
    assert_close(m, se, closed_oblivious(K, q, c), f"population {cap_mode} c={c}")
    assert_close(dm, dse, 0.0, f"population {cap_mode} c={c}, conditional")
    m, se, dm, dse = mc_residual(cell, K, lambda nm: guarded_mpc(
        B.HMMBelief(pp, "oracle"), 2, 0, 1.0, name=nm, privileged=True),
        cond_oracle(c, K), n_rng=1)
    assert_close(m, se, closed_posterior(K, q, c), f"oracle {cap_mode} c={c}")
    assert_close(dm, dse, 0.0, f"oracle {cap_mode} c={c}, conditional")


@needs_beliefs
@pytest.mark.parametrize("cap_mode,M", [("pooled", 1), ("pooled", 3), ("per_copy", 1),
                                        ("per_copy", 3), ("pooled", 0)])
def test_ik_e1_mpc_reaches_proposition_3(cap_mode, M):
    K, q = 4, 0.4
    cell = Cell(family="KCOPY", M=M, delta_A=2, delta_b=0, q=q, c=float(K), cap_mode=cap_mode)
    target = (closed_prop3_pooled if cap_mode == "pooled" else closed_prop3_per_copy)(K, q, M)
    m, se, dm, dse = mc_residual(cell, K, lambda nm: guarded_mpc(
        B.HMMBelief(population_params(), "e1"), 2, 0, 1.0, name=nm), cond_e1(cap_mode, K))
    assert_close(m, se, target, f"e1 {cap_mode} M={M}")
    assert_close(dm, dse, 0.0, f"e1 {cap_mode} M={M}, conditional")


# --------------------------------------------------------------------------- guard
def tiny_view(dA=1, H=6, d=6):
    sv = StaticView(N=1, H=H, P=[1], E=[1], a=[0], d=[d], group=[0], L=np.full((1, H), 5.0),
                    b_mean=np.zeros((1, H)), announced=np.ones((1, H)),
                    prior_A=np.zeros((1, 0, H)), prior_stuck=np.zeros((1, 0), bool),
                    family="F0R", delta_A=dA, delta_b=0)
    view = InformationSet(sv, 0, np.zeros((1, 0)), np.zeros((1, max(0, 1 - dA)), np.int8),
                          np.zeros((1, max(0, 1 - dA))), np.zeros((1, 0)))
    return sv, view


def rising_post(H=6):
    """Debt 1; availability forecast rising from 0.5 to 0.9 (a possibly stuck participant)."""
    p = np.linspace(0.5, 0.9, H)[None, :]
    return PosteriorState(t=0, tail=np.ones((1, 1)), tail_avail=p[:, None, :].copy(),
                          p_avail=p.copy(), exp_debt=np.ones(1), p_pos=np.ones(1), point=False)


def test_rising_forecast_does_not_make_the_plan_wait():
    """S2: with a rising availability forecast the unit is sent now, not at the last slot.

    The running minimum makes the value constant (0.5) over the window, so the earliness
    preference places it at the current slot, with or without the guard.
    """
    sv, view = tiny_view()
    post = rising_post()
    for gamma in (0.0, 0.5, 1.0, 2.0):
        pol = MPCPolicy(HandPoint("CE"), 6, 0, gamma=gamma)
        pol.reset(sv, np.random.default_rng(0))
        assert pol.decide(view, post).tolist() == [1], gamma
        assert pol.last_plan[0].tolist() == [1, 0, 0, 0, 0, 0]
    vb = pol.base_values(post, 0, 6, np.zeros(1, np.int64), np.zeros(1, bool))
    assert np.allclose(vb[0, 0], 0.5)
    falling = replace(post, tail_avail=post.tail_avail[:, :, ::-1].copy())
    vb = pol.base_values(falling, 0, 6, np.zeros(1, np.int64), np.zeros(1, bool))
    assert np.allclose(vb, falling.tail_avail)        # already non-increasing: unchanged


def test_running_min_starts_at_release_and_after_a_revealed_stuck_slot():
    sv, view = tiny_view()
    pol = MPCPolicy(HandPoint("CE"), 6, 0)
    pol.reset(sv, np.random.default_rng(0))
    raw = np.array([[[0.0, 0.9, 0.7, 0.8, 0.6, 0.9]]])
    post = replace(rising_post(), tail_avail=raw)
    vb = pol.base_values(post, 0, 6, np.zeros(1, np.int64), np.ones(1, bool))
    assert np.allclose(vb[0, 0], [0.0, 0.9, 0.7, 0.7, 0.6, 0.6])
    vb = pol.base_values(post, 0, 6, np.array([2]), np.zeros(1, bool))
    assert np.allclose(vb[0, 0], [0.0, 0.9, 0.7, 0.7, 0.6, 0.6])


def grid(pol, post, t=0, H=6, lo=None, blocked=None):
    lo = np.zeros(post.tail.shape[0], np.int64) + t if lo is None else lo
    blocked = np.zeros(post.tail.shape[0], bool) if blocked is None else blocked
    return pol.value_grid(post, t, H, lo, blocked)


def test_guard_value_never_exceeds_tail_and_skips_uncorrectable_slots():
    sv, view = tiny_view(dA=2)
    post = rising_post()
    for gamma in (0.5, 1.0, 2.0):
        pol = MPCPolicy(HandPoint("CE"), 6, 0, gamma=gamma)
        pol.reset(sv, np.random.default_rng(0))
        v = grid(pol, post)[0, 0]
        assert (v <= 1.0 + 1e-12).all() and (np.diff(v) <= 1e-15).all()
        assert np.allclose(v[4:], 0.5)                  # tau + 2 >= d: no credit
        assert (v[:4] > 0.5).all()
    pol0 = MPCPolicy(HandPoint("CE"), 6, 0, gamma=0.0)
    pol0.reset(sv, np.random.default_rng(0))
    assert np.allclose(grid(pol0, post)[0, 0], 0.5)


def test_no_credit_where_the_base_value_is_zero():
    sv, view = tiny_view(dA=1, H=3, d=3)
    p = np.array([[0.9, 0.0, 0.9]])
    post = PosteriorState(t=0, tail=np.ones((1, 1)), tail_avail=p[:, None, :].copy(),
                          p_avail=p.copy(), exp_debt=np.ones(1), p_pos=np.ones(1), point=False)
    for gamma in (1.0, 2.0):
        pol = MPCPolicy(HandPoint("CE"), 3, 0, gamma=gamma)
        pol.reset(sv, np.random.default_rng(0))
        v = grid(pol, post, H=3)[0, 0]
        assert v[0] >= 0.9 and v[1] == 0.0 and v[2] == 0.0, v


@needs_beliefs
def test_value_grid_is_monotone_and_bounded_on_hmm_posteriors():
    """value_grid: non-increasing in tau (from lo_i) and in k, 0 <= v <= tail."""
    pp = population_params()
    for cell in [c for c in F0R_CELLS if c.M == 3 and c.rho == 0.95 and c.r == 0.3][:4]:
        inst = generate_f0r(F0R_SEEDS[2], cell)
        for gamma in (0.0, 0.5, 2.0):
            pol = guarded_mpc(B.HMMBelief(pp, "e1"), 24, 0, gamma)
            seen = []

            class Probe(Recorder):
                def act(self, view):
                    post = self.pol.belief.compute(view)
                    t = view.t
                    lo = np.maximum(t, view.a)
                    blk = np.zeros(view.N, bool)
                    v = self.pol.value_grid(post, t, view.H, lo, blk)
                    seen.append((v, post.tail, lo - t))
                    return super().act(view)

            simulate(inst, cell, Probe(pol), inst.seed)
            for v, tail, start in seen:
                assert (v >= -1e-15).all() and (v <= tail[:, :, None] + 1e-12).all()
                assert (np.diff(v, axis=1) <= 1e-12).all()                  # in k
                for i in range(v.shape[0]):
                    s0 = max(int(start[i]), 0)
                    assert (np.diff(v[i, :, s0:], axis=1) <= 1e-12).all()   # in tau


def test_milp_fallback_on_a_fractional_vertex(monkeypatch):
    """N2: a fractional LP vertex is re-solved as a MILP and counted."""
    cell = NC2_CELLS[0]
    inst = generate_f0r(F0R_SEEDS[0], cell)
    sv = StaticView.from_instance(inst, cell)
    z = np.zeros((inst.N, inst.H), np.int64)
    view = InformationSet.build(sv, 0, z, np.full((inst.N, inst.H), -1, np.int8), z, inst.b)
    ref = MPCPolicy(HandPoint("CE"), 24, 0)
    ref.reset(sv, np.random.default_rng(3))
    x_ref = ref.act(view)

    real = mpc_mod.linprog

    def fractional(*a, **kw):
        r = real(*a, **kw)
        r.x = r.x * 0.5                        # pretend the vertex came back fractional
        return r

    monkeypatch.setattr(mpc_mod, "linprog", fractional)
    before = mpc_mod.FALLBACKS["milp"]
    pol = MPCPolicy(HandPoint("CE"), 24, 0)
    pol.reset(sv, np.random.default_rng(3))
    x = pol.act(view)
    assert mpc_mod.FALLBACKS["milp"] == before + 1
    assert x.dtype == np.int64 and x.sum() == x_ref.sum()
    assert x.sum() <= max(0, view.setpoint_cap(0, 0)) and (x <= inst.P).all()
    assert np.array_equal(pol.last_plan.sum(axis=0), ref.last_plan.sum(axis=0))


# --------------------------------------------------------------------------- protocol
def test_belief_called_once_per_act_and_reset_passes_none_and_oracle():
    cell = replace(NC2_CELLS[0], delta_A=0)
    inst = generate_f0r(F0R_SEEDS[0], cell)
    hb = HandPoint("PES")
    rec = Recorder(MPCPolicy(hb, 8, 1, name="pes"))
    tr = simulate(inst, cell, rec, inst.seed)
    assert hb.calls == rec.calls == int(tr.rounds.sum())
    assert hb.reset_args == (None, None)
    assert rec.pol.floor_mask(None) is None
    hb2 = HandPoint("CE")
    pol = MPCPolicy(hb2, 4, 0, privileged=True, name="priv")
    simulate(inst, cell, pol, inst.seed)
    assert hb2.reset_args[0] is None and hb2.reset_args[1] is not None


def test_repeated_act_at_same_slot_is_consistent():
    """Two calls on the same view (as at delta_A = 0 re-dispatch) both return valid plans."""
    cell = replace(NC2_CELLS[0], delta_A=0)
    inst = generate_f0r(F0R_SEEDS[1], cell)
    sv = StaticView.from_instance(inst, cell)
    pol = MPCPolicy(HandPoint("CE"), 24, 0)
    pol.reset(sv, np.random.default_rng(1))
    x = np.zeros((inst.N, inst.H), np.int64)
    A = np.full((inst.N, inst.H), -1, np.int8)
    view = InformationSet.build(sv, 0, x, A, x, inst.b)
    a1, a2 = pol.act(view), pol.act(view)
    assert a1.sum() == a2.sum()          # same objective value; ties may differ


# --------------------------------------------------------------------------- feasibility
def feasibility_policies():
    pols = [lambda: MPCPolicy(HandPoint("CE"), 4, 1, k=2, name="ce"),
            lambda: MPCPolicy(HandPoint("PES"), 24, 2, k=1, name="pes")]
    if B is not None:
        pp = population_params()
        pols += [lambda: guarded_mpc(B.HMMBelief(pp, "e1"), 8, 0, 1.0, name="e1"),
                 lambda: guarded_mpc(B.HMMBelief(pp, "population"), 24, 1, 2.0, name="pop"),
                 lambda: mpc_pes(2, 0, 3), lambda: mpc_ce(24, 0, 0)]
    return pols


@pytest.mark.parametrize("cell", F0R_CELLS, ids=lambda c: c.cell_id)
def test_actions_are_feasible_on_every_f0r_cell(cell):
    """simulate() validates every call; Recorder checks the m-margin caps and integrality."""
    for j, make in enumerate(feasibility_policies()):
        seed = F0R_SEEDS[(j * 7) % len(F0R_SEEDS)]
        inst = generate_f0r(seed, cell)
        rec = Recorder(make())
        tr = simulate(inst, cell, rec, seed)
        assert tr.x.dtype == np.int64 and rec.calls == int(tr.rounds.sum())


@pytest.mark.parametrize("kind", ("CE", "PES"))
def test_redispatch_keeps_revealed_available_commands(kind):
    """S4: across re-dispatch rounds of one slot, a commanded participant revealed
    available is never dropped (same tie-break table, REVEAL preference)."""
    cells = [c for c in F0R_CELLS if c.delta_A == 0]
    n_checked = 0
    for cell in cells:
        for seed in list(F0R_SEEDS)[:8]:
            inst = generate_f0r(seed, cell)
            tr = simulate(inst, cell, MPCPolicy(HandPoint(kind), 24, 0, name=kind), seed)
            log = tr.redispatch_log
            for (t0, r0, x0, _), (t1, r1, x1, rev1) in zip(log, log[1:]):
                if t1 != t0 or r1 != r0 + 1:
                    continue
                keep = rev1 & (tr.A[:, t1] == 1) & (x0 > 0)
                assert (x1[keep] >= x0[keep]).all(), (cell.cell_id, seed, t1, r1)
                n_checked += int(keep.sum())
    assert n_checked > 0


@needs_beliefs
def test_redispatch_hmm_reallocates_only_past_reveal(monkeypatch):
    """S4, HMM: a revealed-available command is dropped only when the plan value gained
    exceeds REVEAL per unit kept (re-solve with the unit forced and compare)."""
    pp = population_params()
    stats = {"rounds": 0, "drops": 0, "count_drops": 0}

    class Check(Recorder):
        def reset(self, static_view, rng, oracle=None):
            super().reset(static_view, rng, oracle)
            self.prev = (-1, None)

        def act(self, view):
            x = super().act(view)
            col = mpc_mod.current_column(view)
            t_prev, x_prev = self.prev
            if col is not None and view.redispatch_round > 0 and t_prev == view.t:
                stats["rounds"] += 1
                keep = (col == 1) & (x_prev > 0)
                if (x[keep] < x_prev[keep]).any():
                    stats["drops"] += 1
                    post = self.pol.belief.compute(view)
                    obj_free = self.pol.last_objective
                    n_free = int(self.pol.last_plan[col == 1, 0].sum())
                    monkeypatch.setattr(mpc_mod, "REVEAL", 10.0)
                    self.pol.decide(view, post)
                    monkeypatch.setattr(mpc_mod, "REVEAL", 1e-3)
                    obj_forced = self.pol.last_objective
                    n_forced = int(self.pol.last_plan[col == 1, 0].sum())
                    # n_forced == n_free: units moved between revealed-available
                    # participants, which REVEAL does not rank (value-driven or tie)
                    assert n_forced >= n_free
                    stats["count_drops"] += int(n_forced > n_free)
                    assert obj_free - obj_forced >= 1e-3 * (n_forced - n_free) - 1e-9
            self.prev = (view.t, x)
            return x

    for cell in [c for c in F0R_CELLS if c.delta_A == 0]:
        for seed in list(F0R_SEEDS)[:6]:
            inst = generate_f0r(seed, cell)
            for mode in ("e1", "population"):
                pol = guarded_mpc(B.HMMBelief(pp, mode), 24, 0, 0.0, name=mode)
                simulate(inst, cell, Check(pol), seed)
    assert stats["rounds"] > 0


def test_redispatch_rounds_occur_and_validate():
    cell = [c for c in F0R_CELLS if c.delta_A == 0 and c.M == 3][0]
    n_multi = 0
    for seed in list(F0R_SEEDS)[:6]:
        inst = generate_f0r(seed, cell)
        rec = Recorder(MPCPolicy(HandPoint("CE"), 24, 0, name="ce"))
        tr = simulate(inst, cell, rec, seed)
        n_multi += int((tr.rounds > 1).sum())
    assert n_multi > 0


# --------------------------------------------------------------------------- speed
@needs_beliefs
def test_speed_per_decision_n30_h24_w24():
    cell = [c for c in F0R_CELLS if c.delta_A == 2 and c.M == 3 and c.rho == 0.95
            and c.r == 0.3][0]
    pp = population_params()
    ms = []
    for seed in list(F0R_SEEDS)[:5]:
        inst = generate_f0r(seed, cell)
        assert inst.N == 30 and inst.H == 24
        for pol in (guarded_mpc(B.HMMBelief(pp, "e1"), 24, 0, 1.0), mpc_ce(24, 0, 0)):
            tr = simulate(inst, cell, pol, seed)
            ms.append(tr.cpu_ms / tr.rounds)
    ms = np.concatenate(ms)
    assert ms.mean() <= 20.0, ms.mean()
