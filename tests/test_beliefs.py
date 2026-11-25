"""Beliefs (POLICY_SPEC Sections 2 and 3.2): point masses, HMM exactness by brute force,
the three q modes, calibration on a generated cell, speed and the policy lint."""
import itertools
import time
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from papere.generator import generate_f0r
from papere.infoset import InformationSet, OracleView, StaticView
from papere.instance import Cell
from papere.policies.base import PopulationParams
from papere.policies.beliefs import (CEBelief, HMMBelief, PersistBelief, PESBelief,
                                     PRIOR_ESS, known_complete)
from papere.sim import simulate

from test_policy_lint import lint_source

# modest pseudo-counts so that the instance's own prior counts visibly move p_stay and r
SMALL = PopulationParams(alpha=0.4, beta=2.4, q_bar_stuck=30.0, q_bar_total=210.0,
                         n_aa=90.0, n_as=10.0, n_ss=12.0, n_sa=8.0)
# the fitted-scale numbers (tuning seeds 60000-60049, rounded)
FITTED = PopulationParams(alpha=0.289, beta=1.811, q_bar_stuck=1064.0, q_bar_total=7500.0,
                          n_aa=156574.0, n_as=3204.0, n_ss=8945.0, n_sa=3777.0)


# ------------------------------------------------------------------ view building
def make_static(E, P, a, d, prior_A, dA, H):
    N = len(E)
    prior_A = np.asarray(prior_A, dtype=np.int64).reshape(N, -1, H)
    return StaticView(
        N=N, H=H, P=P, E=E, a=a, d=d, group=np.zeros(N, dtype=np.int64),
        L=np.full((1, H), 1000.0), b_mean=np.zeros((1, H)),
        announced=np.ones((N, H), dtype=np.int64), prior_A=prior_A,
        prior_stuck=prior_A[:, :, 0] == 0, family="F0R", delta_A=dA, delta_b=0)


def observe(E, A, x, xr, t):
    """Mimic the simulator's masking. ``xr`` are the commands that reveal A (final setpoints
    plus earlier re-dispatch rounds). Returns the masked A and delivered y, [N, H]."""
    N, H = A.shape
    r = np.array(E, dtype=np.int64)
    y = np.zeros((N, H), dtype=np.int64)
    rev = np.zeros((N, H), dtype=bool)
    for s in range(H):
        rev[:, s] = (xr[:, s] > 0) & (r > 0)
        if s < t:
            y[:, s] = np.minimum(x[:, s], r) * A[:, s]
            r = r - y[:, s]
        else:                      # slots >= t do not matter beyond their reveals
            y[:, s] = np.minimum(x[:, s], r) * A[:, s]
    return np.where(rev, A, -1).astype(np.int8), y


def make_view(static, A, x, xr, t):
    Am, y = observe(static.E, A, x, xr, t)
    y_view = y.copy()
    if static.delta_A == 0:
        y_view[:, t] = 0           # column t: delivery unknown, shown as 0
    view = InformationSet.build(static, t, x, Am, y_view, np.zeros((1, static.H)))
    return view, Am, y_view


# -------------------------------------------------------------------- point beliefs
@pytest.fixture
def hand_view():
    """N=4, H=6, delta_A=3, t=5: slots 0..2 confirmed, 3 and 4 unconfirmed."""
    H, dA, t = 6, 3, 5
    E = np.array([6, 6, 6, 2])
    P = np.array([3, 3, 3, 3])
    a = np.array([0, 0, 1, 0])
    d = np.array([6, 5, 6, 6])
    static = make_static(E, P, a, d, np.ones((4, 0, H)), dA, H)
    A = np.ones((4, H), dtype=np.int64)
    A[1, 1:3] = 0                   # participant 1 stuck at slots 1, 2
    x = np.zeros((4, H), dtype=np.int64)
    x[0, :5] = [1, 1, 0, 2, 1]
    x[1, :5] = [1, 0, 1, 2, 2]
    x[2, :5] = [0, 0, 0, 3, 3]
    x[3, :5] = [2, 1, 0, 0, 0]
    view, Am, _ = make_view(static, A, x, x.copy(), t)
    return static, view, Am


def test_hand_view_is_what_the_cases_assume(hand_view):
    _, view, Am = hand_view
    assert view.confirmed_debt.tolist() == [4, 5, 6, 0]
    assert Am[0, :3].tolist() == [1, 1, -1]        # revealed avail, then unknown (x = 0)
    assert Am[1, :3].tolist() == [1, -1, 0]        # revealed avail, unknown, revealed stuck
    assert Am[2, :3].tolist() == [-1, -1, -1]      # nothing revealed
    assert Am[3, :3].tolist() == [1, -1, -1]       # x > 0 with A hidden: already complete
    assert known_complete(view).tolist() == [False, False, False, True]


@pytest.mark.parametrize("cls,debt", [(CEBelief, [1, 1, 0, 0]), (PESBelief, [4, 5, 6, 0])])
def test_ce_pes_point_masses(hand_view, cls, debt):
    static, view, _ = hand_view
    b = cls()
    b.reset(static, None)
    post = b.compute(view)
    assert post.point and post.t == 5
    assert post.exp_debt.tolist() == debt
    assert post.tail.shape == (4, 6) and post.tail_avail.shape == (4, 6, 6)
    for i, dv in enumerate(debt):
        assert post.tail[i].tolist() == [1.0] * dv + [0.0] * (6 - dv)
    assert post.p_pos.tolist() == [float(v > 0) for v in debt]
    # availability is 1 inside the window and tau >= t only: tau = 5 here
    assert post.p_avail[:, :5].sum() == 0
    assert post.p_avail[:, 5].tolist() == [1.0, 0.0, 1.0, 1.0]    # participant 1: d = 5
    assert np.allclose(post.tail_avail, post.tail[:, :, None] * post.p_avail[:, None, :])
    for arr in (post.tail, post.tail_avail, post.p_avail, post.exp_debt, post.p_pos):
        assert arr.dtype == np.float64


def test_persist_point_masses(hand_view):
    static, view, _ = hand_view
    for base, nothing_revealed_debt in (("CE", 0), ("PES", 6)):
        b = PersistBelief(base)
        b.reset(static, None)
        post = b.compute(view)
        assert post.point
        # 0: last revealed avail -> CE; 1: last revealed stuck -> confirmed debt, availability 0
        # 2: nothing revealed -> base belief; 3: known complete
        assert post.exp_debt.tolist() == [1.0, 5.0, float(nothing_revealed_debt), 0.0]
        assert post.p_avail[:, 5].tolist() == [1.0, 0.0, 1.0, 1.0]
    assert PersistBelief("CE").name != PersistBelief("PES").name
    with pytest.raises(ValueError):
        PersistBelief("HMM")


def test_known_complete_is_zero_for_every_belief(hand_view):
    static, view, _ = hand_view
    beliefs = [CEBelief(), PESBelief(), PersistBelief("CE"), PersistBelief("PES"),
               HMMBelief(SMALL, "e1"), HMMBelief(SMALL, "population")]
    for b in beliefs:
        b.reset(static, None)
        post = b.compute(view)
        assert post.tail[3].sum() == 0 and post.tail_avail[3].sum() == 0
        assert post.exp_debt[3] == 0 and post.p_pos[3] == 0, b.name


def test_ce_point_mass_floors_at_zero_and_uses_only_unconfirmed_slots(hand_view):
    static, view, _ = hand_view
    b = CEBelief()
    b.reset(static, None)
    post = b.compute(view)
    # participant 2: 6 - (3 + 3) = 0; participant 0: confirmed slots 0..2 are not subtracted
    assert post.exp_debt[2] == 0 and post.exp_debt[0] == 1


def test_delta_a_zero_has_no_unconfirmed_and_uses_revealed_current_column():
    H, t = 5, 2
    E = np.array([4, 4])
    static = make_static(E, np.array([2, 2]), np.zeros(2, int), np.full(2, H),
                         np.ones((2, 0, H)), 0, H)
    A = np.array([[1, 1, 0, 1, 1], [1, 1, 1, 1, 1]])
    x = np.array([[1, 1, 0, 0, 0], [1, 0, 0, 0, 0]])
    xr = x.copy()
    xr[:, 2] = [2, 0]                  # participant 0 commanded in an earlier round and found stuck
    view, Am, _ = make_view(static, A, x, xr, t)
    assert Am[:, 2].tolist() == [0, -1]
    assert view.confirmed_debt.tolist() == [2, 3]
    pers = PersistBelief("CE")
    pers.reset(static, None)
    post = pers.compute(view)
    assert post.exp_debt.tolist() == [2.0, 3.0]
    assert post.p_avail[:, 2].tolist() == [0.0, 1.0]       # last revealed state of 0 is stuck
    hmm = HMMBelief(SMALL, "population")
    hmm.reset(static, None)
    ph = hmm.compute(view)
    assert ph.p_avail[0, 2] == 0.0                         # the revealed entry is exact
    assert np.isclose(ph.p_avail[0, 3], hmm.r)             # stuck at t, then returns with r
    assert np.allclose(ph.tail[0], [1, 1, 0, 0])            # debt 2 for sure


def test_point_beliefs_respect_a_revealed_current_column_at_delta_zero():
    H, t = 5, 2
    E = np.array([4, 4, 4])
    static = make_static(E, np.array([2, 2, 2]), np.zeros(3, int), np.full(3, H),
                         np.ones((3, 0, H)), 0, H)
    A = np.ones((3, H), dtype=np.int64)
    A[0, 2] = 0
    x = np.zeros((3, H), dtype=np.int64)
    xr = x.copy()
    xr[:, 2] = [2, 1, 0]               # 0 revealed stuck, 1 revealed available, 2 not commanded
    view, Am, _ = make_view(static, A, x, xr, t)
    assert Am[:, 2].tolist() == [0, 1, -1]
    for b in (CEBelief(), PESBelief(), PersistBelief("CE"), PersistBelief("PES")):
        b.reset(static, None)
        post = b.compute(view)
        assert post.p_avail[:, 2].tolist() == [0.0, 1.0, 1.0], b.name
        assert post.tail_avail[0, :, 2].sum() == 0.0, b.name     # zero value at t for 0
        assert post.tail_avail[1, :, 2].sum() > 0.0 and post.tail_avail[2, :, 2].sum() > 0.0
        assert post.p_avail[0, 3] == (0.0 if b.name.startswith("PERSIST") else 1.0)


# --------------------------------------------------------------- HMM: exactness
def chain_path(rng, q, ps, r, H):
    Z = np.empty(H, dtype=np.int64)
    Z[0] = rng.random() >= q
    for s in range(1, H):
        Z[s] = rng.random() < (ps if Z[s - 1] else r)
    return Z


def population_numbers(prior_A, params, mode, prior_stuck, q_true, floored):
    """Independent re-derivation of p_stay, r and q_i (loops, no vectorization)."""
    n = dict(aa=0, as_=0, ss=0, sa=0)
    N, M, H = prior_A.shape
    for i in range(N):
        for m in range(M):
            for s in range(1, H):
                u, v = prior_A[i, m, s - 1], prior_A[i, m, s]
                key = {(1, 1): "aa", (1, 0): "as_", (0, 0): "ss", (0, 1): "sa"}[(u, v)]
                n[key] += 1
    E = PRIOR_ESS
    ps = (E * params.n_aa / (params.n_aa + params.n_as) + n["aa"]) / (E + n["aa"] + n["as_"])
    r = (E * params.n_sa / (params.n_sa + params.n_ss) + n["sa"]) / (E + n["sa"] + n["ss"])
    k = prior_stuck.sum(axis=1)
    if mode == "e1":
        q = (params.alpha + k) / (params.alpha + params.beta + M)
    elif mode == "population":
        q = np.full(N, (params.alpha + k.sum()) / (params.alpha + params.beta + N * M))
    else:
        q = np.array(q_true, dtype=float)
    q = np.where(floored, 0.0, q)
    return q, ps, r


def brute_posterior(E_i, x_i, xr_i, Am_i, y_i, t, dA, q, ps, r, H, kmax):
    """Enumerate every availability path of the chain, keep those consistent with the
    view, return (tail [kmax], tail_avail [kmax, H], p_avail [H])."""
    n_conf = max(0, t - dA + 1)
    w_tot = 0.0
    w = np.zeros((E_i + 1, H, 2))             # [debt at t, tau, Z_tau]
    for path in itertools.product((0, 1), repeat=H):
        pr = (1 - q) if path[0] else q
        for s in range(1, H):
            p_av = ps if path[s - 1] else r
            pr *= p_av if path[s] else (1 - p_av)
        if pr == 0.0:
            continue
        Ap = np.array(path, dtype=np.int64)[None, :]
        Am_c, y_c = observe(np.array([E_i]), Ap, x_i[None], xr_i[None], t)
        yc = y_c[0].copy()
        ycv = yc[:n_conf]
        yv = y_i[:n_conf]
        if dA == 0:
            ycv, yv = ycv[:-1], yv[:-1]       # column t: delivery unknown
        if not (Am_c[0, :n_conf] == Am_i[:n_conf]).all() or not (ycv == yv).all():
            continue
        debt_t = E_i - yc[:t].sum()
        w_tot += pr
        for tau in range(H):
            w[debt_t, tau, path[tau]] += pr
    assert w_tot > 0, "the true path must be consistent"
    w /= w_tot
    tail = np.zeros(kmax)
    tail_avail = np.zeros((kmax, H))
    p_avail = np.zeros(H)
    for k in range(1, kmax + 1):
        if k <= E_i:
            tail[k - 1] = w[k:, 0, :].sum()
            for tau in range(t, H):
                tail_avail[k - 1, tau] = w[k:, tau, 1].sum()
    for tau in range(t, H):
        p_avail[tau] = w[:, tau, 1].sum()
    return tail, tail_avail, p_avail


COVER = dict(stuck=0, avail=0, unknown_no_x=0, unconfirmed=0, floored=0, current_col=0,
             hidden_with_x=0)


def scenario(rng, dA, H, N=3, M=2):
    E = rng.integers(1, 4, N)
    P = rng.integers(1, 3, N)
    q_true = rng.uniform(0.15, 0.7, N)
    ps_true, r_true = 0.75, 0.4
    floored = rng.random(N) < 0.3
    prior_A = np.stack([[chain_path(rng, q_true[i], ps_true, r_true, H) for _ in range(M)]
                        for i in range(N)])
    A = np.stack([chain_path(rng, 0.0 if floored[i] else q_true[i], ps_true, r_true, H)
                  for i in range(N)])
    x = (rng.integers(0, 3, (N, H)) * (rng.random((N, H)) < 0.65))
    x = np.minimum(x, P[:, None])
    t = int(rng.integers(0, H))
    xr = x.copy()
    if dA == 0:
        extra = (rng.integers(1, 3, (N, H)) * (rng.random((N, H)) < 0.3))
        xr = np.maximum(x, np.minimum(extra, P[:, None]))
        xr[:, t] = np.minimum(extra[:, t], P)        # column t: only earlier-round commands
    static = make_static(E, P, np.zeros(N, int), np.full(N, H), prior_A, dA, H)
    return static, A, x, xr, t, q_true, floored


@pytest.mark.parametrize("mode", ["e1", "population", "oracle"])
@pytest.mark.parametrize("dA,H", [(0, 4), (1, 4), (2, 4), (3, 5)])
def test_hmm_matches_brute_force(mode, dA, H):
    rng = np.random.default_rng(1000 * dA + len(mode))
    cover = dict.fromkeys(COVER, 0)
    for _ in range(120):
        static, A, x, xr, t, q_true, floored = scenario(rng, dA, H)
        view, Am, y_view = make_view(static, A, x, xr, t)
        belief = HMMBelief(SMALL, mode)
        belief.reset(static, floored, oracle=OracleView(np.zeros(static.N, int), q_true))
        q, ps, r = population_numbers(static.prior_A, SMALL, mode, static.prior_stuck,
                                      q_true, floored)
        assert np.allclose(belief.q, q, atol=1e-15, rtol=0)
        assert np.isclose(belief.p_stay, ps, atol=1e-15) and np.isclose(belief.r, r, atol=1e-15)
        post = belief.compute(view)
        kmax = int(static.E.max())
        assert post.tail.shape == (static.N, kmax)
        assert post.tail_avail.shape == (static.N, kmax, H) and not post.point
        n_conf = max(0, t - dA + 1)
        for i in range(static.N):
            tail, tail_avail, p_avail = brute_posterior(
                int(static.E[i]), x[i], xr[i], Am[i], y_view[i], t, dA, q[i], ps, r, H, kmax)
            assert np.allclose(post.tail[i], tail, atol=1e-12, rtol=0), (mode, dA, t, i)
            assert np.allclose(post.tail_avail[i], tail_avail, atol=1e-12, rtol=0), (mode, dA, t, i)
            assert np.allclose(post.p_avail[i], p_avail, atol=1e-12, rtol=0), (mode, dA, t, i)
            assert np.isclose(post.exp_debt[i], tail.sum(), atol=1e-12)
            assert np.isclose(post.p_pos[i], tail[0], atol=1e-12)
        # structural properties
        assert (post.tail_avail[:, :, :t] == 0).all() and (post.p_avail[:, :t] == 0).all()
        assert (np.diff(post.tail, axis=1) <= 1e-15).all()
        assert (post.tail_avail <= post.tail[:, :, None] + 1e-12).all()
        assert (post.tail_avail <= post.p_avail[:, None, :] + 1e-12).all()
        # coverage bookkeeping
        conf = Am[:, :n_conf]
        cover["stuck"] += int((conf == 0).any())
        cover["avail"] += int((conf == 1).any())
        cover["unknown_no_x"] += int(((conf == -1) & (x[:, :n_conf] == 0)).any())
        cover["hidden_with_x"] += int(((conf[:, :max(0, min(n_conf, t))] == -1)
                                       & (x[:, :max(0, min(n_conf, t))] > 0)).any())
        lo = max(t - dA + 1, 0)
        cover["unconfirmed"] += int(x[:, lo:t].sum() > 0)
        cover["floored"] += int(floored.any())
        cover["current_col"] += int(dA == 0 and (Am[:, t] >= 0).any())
    needed = ["stuck", "avail", "unknown_no_x", "hidden_with_x", "floored"]
    needed += ["unconfirmed"] if dA >= 2 else []
    needed += ["current_col"] if dA == 0 else []
    for key in needed:
        assert cover[key] > 0, f"scenario sweep never produced: {key}"


def test_hmm_analytic_unconfirmed_setpoint():
    """One participant, E = 2, x_0 = 2 unconfirmed at t = 1 (delta_A = 2): closed form."""
    H = 4
    static = make_static(np.array([2]), np.array([2]), np.array([0]), np.array([H]),
                         np.zeros((1, 0, H)), 2, H)
    x = np.zeros((1, H), dtype=np.int64)
    x[0, 0] = 2
    view, _, _ = make_view(static, np.ones((1, H), dtype=np.int64), x, x.copy(), 1)
    b = HMMBelief(SMALL, "e1")
    b.reset(static, None)
    q, ps, r = b.q[0], b.p_stay, b.r
    assert np.isclose(q, SMALL.alpha / (SMALL.alpha + SMALL.beta))     # M = 0
    post = b.compute(view)
    assert np.allclose(post.tail[0], [q, q])                           # debt 2 iff stuck at 0
    assert np.isclose(post.p_avail[0, 1], (1 - q) * ps + q * r)
    assert np.isclose(post.tail_avail[0, 0, 1], q * r)                 # stuck at 0, avail at 1
    assert np.isclose(post.tail_avail[0, 1, 1], q * r)
    p2 = (1 - q) * ps * ps + (1 - q) * (1 - ps) * r + q * r * ps + q * (1 - r) * r
    assert np.isclose(post.p_avail[0, 2], p2)


def test_hmm_no_information_at_t0_is_the_prior():
    H = 5
    static = make_static(np.array([3, 3]), np.array([1, 1]), np.zeros(2, int),
                         np.full(2, H), np.zeros((2, 0, H)), 2, H)
    view = InformationSet.build(static, 0, np.zeros((2, H), int), np.full((2, H), -1, np.int8),
                                np.zeros((2, H), int), np.zeros((1, H)))
    b = HMMBelief(SMALL, "population")
    b.reset(static, np.array([False, True]))
    post = b.compute(view)
    q = SMALL.alpha / (SMALL.alpha + SMALL.beta)
    assert np.isclose(post.p_avail[0, 0], 1 - q) and post.p_avail[1, 0] == 1.0   # floored
    assert np.allclose(post.tail[:, :3], 1.0)


# -------------------------------------------------------- the three q modes
def test_modes_differ_only_in_q():
    cell = Cell(family="F0R", M=3, delta_A=2, delta_b=0, rho=0.95, r=0.3)
    inst = generate_f0r(60020, cell)
    static = StaticView.from_instance(inst)
    oracle = OracleView.from_instance(inst)
    e1, pop, orc = (HMMBelief(FITTED, m) for m in ("e1", "population", "oracle"))
    for b in (e1, pop, orc):
        b.reset(static, None, oracle=oracle)
    assert e1.p_stay == pop.p_stay == orc.p_stay and e1.r == pop.r == orc.r
    k = static.prior_stuck.sum(axis=1)
    assert np.allclose(e1.q, (FITTED.alpha + k) / (FITTED.alpha + FITTED.beta + 3))
    assert len(np.unique(pop.q)) == 1
    assert np.isclose(pop.q[0], (FITTED.alpha + k.sum()) / (FITTED.alpha + FITTED.beta + 30 * 3))
    assert np.array_equal(orc.q, inst.q)
    assert len(np.unique(e1.q)) > 1 and not np.allclose(e1.q, pop.q)

    rng = np.random.default_rng(5)
    x = (rng.integers(0, 3, (30, 24)) * (rng.random((30, 24)) < 0.4)).astype(np.int64)
    x = np.minimum(x, inst.P[:, None])
    A = inst.availability()
    Am, y = observe(inst.E, A, x, x, 9)
    view = InformationSet.build(static, 9, x, Am, y, inst.b)
    ref = pop.compute(view)
    swapped = HMMBelief(FITTED, "e1")
    swapped.reset(static, None)
    swapped.q = pop.q.copy()                     # same q => same posterior, nothing else differs
    got = swapped.compute(view)
    for f in ("tail", "tail_avail", "p_avail", "exp_debt", "p_pos"):
        assert np.array_equal(getattr(ref, f), getattr(got, f)), f
    assert not np.allclose(e1.compute(view).p_avail, ref.p_avail)


def test_e1_and_population_are_identical_at_m0():
    cell = Cell(family="F0R", M=0, delta_A=2, delta_b=0, rho=0.95, r=0.3)
    inst = generate_f0r(60021, cell)
    static = StaticView.from_instance(inst)
    e1, pop = HMMBelief(FITTED, "e1"), HMMBelief(FITTED, "population")
    e1.reset(static, None)
    pop.reset(static, None)
    assert np.array_equal(e1.q, pop.q)
    assert np.allclose(e1.q, FITTED.alpha / (FITTED.alpha + FITTED.beta))
    # with M = 0 the transition numbers are the tuning means alone
    assert np.isclose(e1.p_stay, FITTED.n_aa / (FITTED.n_aa + FITTED.n_as))
    assert np.isclose(e1.r, FITTED.n_sa / (FITTED.n_sa + FITTED.n_ss))
    rng = np.random.default_rng(11)
    A = inst.availability()
    for t in (0, 3, 9, 17):
        x = (rng.integers(0, 3, (30, 24)) * (rng.random((30, 24)) < 0.4)).astype(np.int64)
        x = np.minimum(x, inst.P[:, None])
        Am, y = observe(inst.E, A, x, x, t)
        view = InformationSet.build(static, t, x, Am, y, inst.b)
        u, v = e1.compute(view), pop.compute(view)
        for f in ("tail", "tail_avail", "p_avail", "exp_debt", "p_pos"):
            assert np.array_equal(getattr(u, f), getattr(v, f)), (t, f)


def test_oracle_mode_needs_the_oracle_view():
    cell = Cell(family="F0R", M=1, delta_A=2, delta_b=0, rho=0.95, r=0.3)
    static = StaticView.from_instance(generate_f0r(60022, cell))
    with pytest.raises(ValueError):
        HMMBelief(FITTED, "oracle").reset(static, None)
    with pytest.raises(ValueError):
        HMMBelief(FITTED, "bogus")


def test_floored_participants_start_available_and_others_keep_their_q():
    cell = Cell(family="F0R", M=3, delta_A=2, delta_b=0, rho=0.95, r=0.3)
    static = StaticView.from_instance(generate_f0r(60023, cell))
    fl = np.zeros(30, dtype=bool)
    fl[[2, 7]] = True
    plain, floored = HMMBelief(FITTED, "e1"), HMMBelief(FITTED, "e1")
    plain.reset(static, None)
    floored.reset(static, fl)
    assert (floored.q[fl] == 0).all() and np.array_equal(floored.q[~fl], plain.q[~fl])


def test_population_update_uses_instance_transition_counts():
    cell = Cell(family="F0R", M=5, delta_A=2, delta_b=0, rho=0.95, r=0.3)
    static = StaticView.from_instance(generate_f0r(60024, cell))
    a0, a1 = static.prior_A[:, :, :-1], static.prior_A[:, :, 1:]
    n_aa, n_as = ((a0 == 1) & (a1 == 1)).sum(), ((a0 == 1) & (a1 == 0)).sum()
    n_sa, n_ss = ((a0 == 0) & (a1 == 1)).sum(), ((a0 == 0) & (a1 == 0)).sum()
    b = HMMBelief(SMALL, "e1")
    b.reset(static, None)
    ra, rs = SMALL.n_aa / (SMALL.n_aa + SMALL.n_as), SMALL.n_sa / (SMALL.n_sa + SMALL.n_ss)
    assert np.isclose(b.p_stay, (PRIOR_ESS * ra + n_aa) / (PRIOR_ESS + n_aa + n_as))
    assert np.isclose(b.r, (PRIOR_ESS * rs + n_sa) / (PRIOR_ESS + n_sa + n_ss))
    assert not np.isclose(b.p_stay, SMALL.n_aa / (SMALL.n_aa + SMALL.n_as))


@pytest.mark.parametrize("r_true", [0.0, 1.0])
def test_r_hat_follows_the_instance_in_the_r_sweep_cells(r_true):
    cell = Cell(family="F0R", M=3, delta_A=2, delta_b=0, rho=0.95, r=r_true)
    hats = []
    for seed in range(60000, 60020):
        b = HMMBelief(FITTED, "e1")
        b.reset(StaticView.from_instance(generate_f0r(seed, cell)), None)
        hats.append(b.r)
    assert abs(np.mean(hats) - r_true) < 0.15, np.mean(hats)


def test_r_hat_equals_the_tuning_mean_at_m0():
    cell = Cell(family="F0R", M=0, delta_A=2, delta_b=0, rho=0.95, r=1.0)
    b = HMMBelief(FITTED, "population")
    b.reset(StaticView.from_instance(generate_f0r(60025, cell)), None)
    assert np.isclose(b.r, FITTED.n_sa / (FITTED.n_sa + FITTED.n_ss), atol=1e-15, rtol=0)
    assert np.isclose(b.p_stay, FITTED.n_aa / (FITTED.n_aa + FITTED.n_as), atol=1e-15, rtol=0)


def test_compute_before_reset_raises():
    for b in (CEBelief(), PESBelief(), PersistBelief(), HMMBelief(FITTED)):
        with pytest.raises(RuntimeError):
            b.compute(None)


# --------------------------------------------------------- Monte Carlo calibration
class Recorder:
    """Commands one unit to as many active participants as the cap allows (rotating the
    order) and records the HMM(oracle) availability forecast made before each decision."""

    privileged = True
    name = "belief-recorder"

    def __init__(self, params, mode="oracle"):
        self.belief = HMMBelief(params, mode)
        self.rec = None

    def reset(self, static_view, rng, oracle=None):
        self.belief.reset(static_view, None, oracle=oracle)
        self.rec = np.zeros((static_view.N, static_view.H))

    def floor_mask(self, static_view):
        return None

    def act(self, view):
        if view.redispatch_round == 0:
            self.rec[:, view.t] = self.belief.compute(view).p_avail[:, view.t]
        N = view.N
        x = np.zeros(N, dtype=np.int64)
        cap = max(0, view.setpoint_cap(0, 0))
        order = np.roll(np.arange(N), -(view.t * 7 % N))
        for i in order:
            if cap <= 0:
                break
            if view.active[i] and view.confirmed_debt[i] > 0:
                x[i] = 1
                cap -= 1
        return x


@pytest.mark.parametrize("dA", [2, 0])
def test_oracle_p_avail_is_calibrated(dA):
    cell = Cell(family="F0R", M=3, delta_A=dA, delta_b=0, rho=0.95, r=0.3)
    preds, outs = [], []
    for seed in range(60000, 60050):
        inst = generate_f0r(seed, cell)
        pol = Recorder(FITTED)
        traj = simulate(inst, cell, pol, seed)
        preds.append(pol.rec.ravel())
        outs.append(traj.A.ravel())
    p, a = np.concatenate(preds), np.concatenate(outs)
    edges = [0.0, 0.2, 0.4, 0.6, 0.8, 0.9, 0.95, 0.98, 1.0 + 1e-9]
    checked = 0
    for lo, hi in zip(edges[:-1], edges[1:]):
        sel = (p >= lo) & (p < hi)
        n = int(sel.sum())
        if n < 300:
            continue
        gap = abs(p[sel].mean() - a[sel].mean())
        se = np.sqrt(max(a[sel].mean() * (1 - a[sel].mean()), 1e-4) / n)
        assert gap < max(0.03, 6 * se), (dA, lo, hi, n, gap)
        checked += 1
    assert checked >= 3
    assert abs(p.mean() - a.mean()) < 0.01


# ------------------------------------------------------------------------- speed
def test_compute_is_fast_at_n30_h24_delta4():
    cell = Cell(family="F0R", M=3, delta_A=4, delta_b=0, rho=0.95, r=0.3)
    inst = generate_f0r(60026, cell)
    static = StaticView.from_instance(inst)
    rng = np.random.default_rng(3)
    x = (rng.integers(0, 4, (30, 24)) * (rng.random((30, 24)) < 0.5)).astype(np.int64)
    x = np.minimum(x, inst.P[:, None])
    Am, y = observe(inst.E, inst.availability(), x, x, 14)
    view = InformationSet.build(static, 14, x, Am, y, inst.b)
    beliefs = [HMMBelief(FITTED, "e1"), CEBelief(), PESBelief(), PersistBelief("PES")]
    for b in beliefs:
        b.reset(static, None)
        b.compute(view)
        best = np.inf
        for _ in range(5):
            t0 = time.perf_counter()
            for _ in range(40):
                b.compute(view)
            best = min(best, (time.perf_counter() - t0) / 40 * 1e3)
        print(f"{b.name}: {best:.3f} ms per compute")
        assert best < 5.0, (b.name, best)


# ------------------------------------------------------------------------- lint
def test_beliefs_module_passes_the_policy_lint():
    path = Path(__file__).resolve().parents[1] / "src" / "papere" / "policies" / "beliefs.py"
    assert lint_source(path.read_text(), "papere.policies.beliefs") == []
