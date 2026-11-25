"""Generator tests: shapes, formulas, common random numbers, coupling, independence."""
from dataclasses import replace

import numpy as np
import pytest
from scipy.stats import chi2_contingency

from papere.generator import (F0R_CELLS, KCOPY_CELLS, generate_f0r, generate_kcopy,
                              policy_rng, stable_hash, stream)
from papere.instance import Cell

from conftest import draw

BASE = Cell(family="F0R", M=3, delta_A=2, delta_b=0, rho=0.95, r=0.3)


def test_cell_lists():
    assert len(F0R_CELLS) == 22
    assert len({c.cell_id for c in F0R_CELLS}) == 22
    prim = [c for c in F0R_CELLS if c.delta_b == 0 and c.r == 0.3 and c.rho in (0.95, 1.15)
            and c.M in (0, 3)]
    assert len(prim) == 16
    others = {(c.M, c.delta_A, c.delta_b, c.rho, c.r) for c in F0R_CELLS} - \
        {(c.M, c.delta_A, c.delta_b, c.rho, c.r) for c in prim}
    assert others == {(1, 2, 0, 0.95, 0.3), (5, 2, 0, 0.95, 0.3), (3, 2, 0, 0.95, 0.0),
                      (3, 2, 0, 0.95, 1.0), (3, 2, 0, 0.7, 0.3), (3, 0, 2, 0.95, 0.3)}
    pooled = [c for c in KCOPY_CELLS if c.cap_mode == "pooled"]
    per = [c for c in KCOPY_CELLS if c.cap_mode == "per_copy"]
    assert len(pooled) == 3 * 9 * 4 and len(per) == 3 * 3 * 4
    assert sorted({c.c for c in pooled}) == [0, 2, 4, 6, 8, 10, 12, 14, 16]
    assert sorted({c.c for c in per}) == [0, 8, 16]
    assert len({c.cell_id for c in KCOPY_CELLS}) == len(KCOPY_CELLS)
    assert all(c.delta_A == 2 and c.delta_b == 0 for c in KCOPY_CELLS)


def test_f0r_shapes_and_ranges():
    for seed in range(60000, 60020):
        inst = generate_f0r(seed, BASE)
        N, H = 30, 24
        assert (inst.N, inst.H) == (N, H)
        assert inst.P.shape == inst.E.shape == inst.a.shape == inst.d.shape == (N,)
        assert set(np.unique(inst.P)) <= {1, 2, 3}
        assert inst.E.min() >= 2 and inst.E.max() <= 12
        assert inst.a.min() >= 0 and inst.a.max() <= 2
        assert (inst.d <= H).all() and (inst.d > inst.a).all()
        assert inst.L.shape == inst.b_mean.shape == inst.b.shape == (1, H)
        assert inst.prior_A.shape == (N, 3, H) and inst.prior_stuck.shape == (N, 3)
        assert inst.announced.shape == (N, H)
        t = np.arange(H)[None, :]
        assert ((inst.announced == 1) == ((t >= inst.a[:, None]) & (t < inst.d[:, None]))).all()
        assert set(np.unique(inst.announced)) <= {0, 1}
        A = inst.availability()
        assert A.shape == (N, H) and set(np.unique(A)) <= {0, 1}


def test_d_formula_recovered_from_streams():
    seed = 60007
    inst = generate_f0r(seed, BASE)
    slack = stream(seed, "slack").integers(0, 13, size=30)
    expect = np.minimum(24, inst.a + -(-inst.E // inst.P) + slack)
    assert (inst.d == expect).all()
    assert ((slack >= 0) & (slack <= 12)).all()


def test_classes_and_q():
    for seed in range(60000, 60030):
        inst = generate_f0r(seed, BASE)
        assert int(inst.cls.sum()) == 10 and set(np.unique(inst.cls)) == {0, 1}
        assert set(np.unique(inst.q[inst.cls == 1])) == {0.40}
        assert set(np.unique(inst.q[inst.cls == 0])) == {0.01}
        assert inst.q.mean() == pytest.approx(0.14)
    assert int(generate_f0r(60001, replace(BASE, family="SCALE"), N=300).cls.sum()) == 100


def test_limit_reproduces_rho():
    for rho in (0.7, 0.95, 1.15):
        inst = generate_f0r(60005, replace(BASE, rho=rho))
        got = inst.E.sum() / (inst.L - inst.b_mean).sum()
        assert got == pytest.approx(rho)
        assert np.allclose(inst.b_mean[0], 30 * (1 + 0.15 * np.arange(24) / 23))


def test_base_load_noise_scale_and_autocorrelation():
    cell = replace(BASE, M=0)
    # 2000 independent draws = 50 tuning seeds x 40 salts of the generator's streams (seed rule)
    e = np.array([(i.b - i.b_mean)[0] for i in
                  (generate_f0r(s, cell, stream_salt=z) for s, z in map(draw, range(2000)))])
    B0 = 30.0
    assert e[:, 0].std() == pytest.approx(0.03 * B0, rel=0.05)      # stationary from slot 0
    assert e[:, -1].std() == pytest.approx(0.03 * B0, rel=0.05)
    ac = np.mean([np.corrcoef(e[:, t], e[:, t + 1])[0, 1] for t in range(23)])
    assert ac == pytest.approx(0.7, abs=0.03)


def test_crn_across_cells():
    ref = generate_f0r(60003, F0R_CELLS[0])
    for cell in F0R_CELLS:
        inst = generate_f0r(60003, cell)
        for f in ("P", "E", "a", "d", "cls", "q", "v", "u", "b", "b_mean", "announced"):
            assert np.array_equal(getattr(inst, f), getattr(ref, f)), (cell.cell_id, f)
    # M nests
    big = generate_f0r(60003, replace(BASE, M=5))
    for M in (0, 1, 3):
        small = generate_f0r(60003, replace(BASE, M=M))
        assert np.array_equal(small.prior_A, big.prior_A[:, :M])
        assert np.array_equal(small.prior_stuck, big.prior_stuck[:, :M])
    # different seeds differ
    assert not np.array_equal(generate_f0r(60004, BASE).E, ref.E)


def test_prior_stuck_matches_prior_availability_and_rate():
    insts = [generate_f0r(s, replace(BASE, M=5), stream_salt=z)     # 50 seeds x 6 salts
             for s, z in map(draw, range(300))]
    for inst in insts[:5]:
        assert np.array_equal(inst.prior_stuck, inst.prior_A[:, :, 0] == 0)
    rate = np.mean([i.prior_stuck.mean() for i in insts])
    assert rate == pytest.approx(0.14, abs=0.01)


def test_r_monotone_coupling():
    for seed in range(60000, 60040):
        As = {r: generate_f0r(seed, replace(BASE, r=r)) for r in (0.0, 0.3, 1.0)}
        a0, a3, a1 = (As[r].availability() for r in (0.0, 0.3, 1.0))
        assert (a3 >= a0).all() and (a1 >= a3).all()
        assert (As[0.3].prior_A >= As[0.0].prior_A).all()
        assert (As[1.0].prior_A >= As[0.3].prior_A).all()
        # r = 0: a stuck participant never returns
        stuck = a0[:, 0] == 0
        assert (a0[stuck] == 0).all()


def test_floor_coupling():
    # Valid at r = 0.3 (any r <= 0.98); NOT monotone at r = 1, see the test below.
    for seed in range(60000, 60020):
        inst = generate_f0r(seed, BASE)
        fl = np.zeros(30, dtype=bool)
        fl[::2] = True
        A0, A1 = inst.availability(None), inst.availability(fl)
        assert (A1[fl, 0] == 1).all()
        assert np.array_equal(A0[~fl], A1[~fl])
        was_ok = fl & (A0[:, 0] == 1)
        assert np.array_equal(A0[was_ok], A1[was_ok])  # same uniforms afterwards
        assert (A1 >= A0).all()
        allfl = inst.availability(np.ones(30, dtype=bool))
        assert (allfl[:, 0] == 1).all()
    # slot-0 stuck rate matches q
    rate = np.mean([generate_f0r(s, BASE, stream_salt=z).availability()[:, 0] == 0
                    for s, z in map(draw, range(400))])        # 50 seeds x 8 salts
    assert rate == pytest.approx(0.14, abs=0.015)


def test_floor_coupling_not_monotone_at_r1():
    """At r = 1 a floored participant can drop (u >= 0.98) where an unfloored stuck one returns.

    Distributions stay correct, but nothing downstream may assume floored >= unfloored
    pointwise; that holds only for r <= 0.98.
    """
    fl = np.ones(30, dtype=bool)
    found = False
    for s, z in map(draw, range(300)):          # 50 seeds x 6 salts
        inst = generate_f0r(s, replace(BASE, r=1.0), stream_salt=z)
        if (inst.availability(fl) < inst.availability()).any():
            found = True
            break
    assert found
    for r in (0.0, 0.3, 0.9):
        for seed in range(60000, 60050):
            inst = generate_f0r(seed, replace(BASE, r=r))
            assert (inst.availability(fl) >= inst.availability()).all()


def test_deterministic_and_iid_options():
    det = generate_f0r(60003, replace(BASE, deterministic=True))
    assert (det.availability() == 1).all() and (det.availability(np.ones(30, bool)) == 1).all()
    assert (det.prior_A == 1).all() and not det.prior_stuck.any() and (det.q == 0).all()
    iid = [generate_f0r(s, replace(BASE, homogeneous_iid=True, M=5), stream_salt=z)
           for s, z in map(draw, range(300))]            # 50 seeds x 6 salts
    assert all((i.q == 0.14).all() for i in iid)
    Aall = np.stack([i.availability() for i in iid])
    assert Aall.mean() == pytest.approx(0.86, abs=0.01)
    assert np.mean([i.prior_A.mean() for i in iid]) == pytest.approx(0.86, abs=0.01)
    # no persistence: P(stuck at t | stuck at t-1) = 0.14
    prev0 = Aall[:, :, :-1] == 0
    assert (Aall[:, :, 1:][prev0] == 0).mean() == pytest.approx(0.14, abs=0.02)
    # same participants/uniforms as the heterogeneous cell
    het = generate_f0r(60000, replace(BASE, M=5))   # draw 0 = seed 60000, unsalted
    assert np.array_equal(het.E, iid[0].E) and np.array_equal(het.u, iid[0].u)


def test_chain_two_state_rates():
    A = np.stack([generate_f0r(s, BASE, stream_salt=z).availability()
                  for s, z in map(draw, range(300))])      # 50 seeds x 6 salts
    avail_prev = A[:, :, :-1] == 1
    assert (A[:, :, 1:][avail_prev] == 1).mean() == pytest.approx(0.98, abs=0.005)
    stuck_prev = A[:, :, :-1] == 0
    assert (A[:, :, 1:][stuck_prev] == 1).mean() == pytest.approx(0.3, abs=0.03)


def test_scale_family():
    inst = generate_f0r(60030, replace(BASE, family="SCALE"), N=300)
    assert inst.N == 300 and inst.family == "SCALE"
    assert inst.b_mean[0, 0] == pytest.approx(300)


def test_policy_rng_holds_no_seed_or_cell_hash():
    seed, cid, pol = 60007, "F0R_M3_dA2_db0_rho0.95_r0.3", "pol"
    rng = policy_rng(seed, cid, pol)
    ss = rng.bit_generator.seed_seq
    ent = np.atleast_1d(np.asarray(ss.entropy)).astype(object).tolist()
    for secret in (seed, stable_hash(cid), stable_hash(pol)):
        assert secret not in ent
    assert tuple(ss.spawn_key) == ()
    assert seed not in [int(v) for v in np.atleast_1d(ss.pool)]
    assert not np.array_equal(policy_rng(seed, cid, pol).random(4),
                              policy_rng(seed + 1, cid, pol).random(4))


def test_policy_rng_stable_and_separate():
    a = policy_rng(60001, "cellA", "pol").random(5)
    assert np.array_equal(a, policy_rng(60001, "cellA", "pol").random(5))
    assert not np.array_equal(a, policy_rng(60002, "cellA", "pol").random(5))
    assert not np.array_equal(a, policy_rng(60001, "cellB", "pol").random(5))
    assert not np.array_equal(a, policy_rng(60001, "cellA", "pol2").random(5))
    assert stable_hash("abc") == stable_hash("abc") != stable_hash("abd")
    assert stable_hash("abc") == 0xBA7816BF8F01CFEA  # sha256('abc') prefix
    for name in ("P", "class", "scored_u", "base_load"):
        assert not np.array_equal(stream(60001, name).random(5), a)


# ---------------------------------------------------------------- K-copy
def test_kcopy_pooled_structure():
    K = 8
    cell = Cell(family="KCOPY", M=3, delta_A=2, q=0.4, c=4.0, cap_mode="pooled")
    inst = generate_kcopy(60007, cell, K)
    assert (inst.N, inst.H) == (24, 2)
    assert [int((inst.cls == k).sum()) for k in (1, 0, 2)] == [K, K, K]
    assert (inst.P == 1).all() and (inst.E == 1).all() and (inst.d == 2).all()
    assert (inst.a[inst.cls == 2] == 1).all() and (inst.a[inst.cls != 2] == 0).all()
    assert inst.L.shape == (1, 2) and tuple(inst.L[0]) == (16.0, 12.0)
    assert (inst.group == 0).all() and (inst.b == 0).all() and (inst.b_mean == 0).all()
    assert np.array_equal(inst.q[inst.cls == 1], np.full(K, 0.4))
    assert (inst.q[inst.cls != 1] == 0).all()
    assert (inst.announced[inst.cls == 2] == np.array([0, 1])).all()


def test_kcopy_per_copy_structure():
    K = 8
    for c in (0.0, 8.0, 16.0):
        cell = Cell(family="KCOPY", M=1, delta_A=2, q=0.5, c=c, cap_mode="per_copy")
        inst = generate_kcopy(60009, cell, K)
        assert inst.L.shape == (K, 2)
        assert (inst.L[:, 0] == 2).all() and (inst.L[:, 1] == 1 + c / K).all()
        for k in range(K):
            m = inst.group == k
            assert sorted(inst.cls[m]) == [0, 1, 2]
    with pytest.raises(ValueError):
        generate_kcopy(60009, Cell(family="KCOPY", delta_A=2, q=0.5, c=3.0, cap_mode="per_copy"), K)
    for dA, db in ((0, 0), (1, 0), (2, 1), (4, 2)):
        with pytest.raises(ValueError):
            generate_kcopy(60009, Cell(family="KCOPY", delta_A=dA, delta_b=db, q=0.5, c=8.0), K)


def test_kcopy_availability_and_priors():
    K = 8
    cell = Cell(family="KCOPY", M=5, delta_A=2, q=0.4, c=8.0)
    stuck, pst = [], []
    for s, z in map(draw, range(400)):          # 50 seeds x 8 salts
        inst = generate_kcopy(s, cell, K, stream_salt=z)
        A = inst.availability()
        assert (A[:, 1] == 1).all() and (A[inst.cls != 1, 0] == 1).all()
        stuck.append(A[inst.cls == 1, 0] == 0)
        assert not inst.prior_stuck[inst.cls != 1].any()
        assert (inst.prior_A[:, :, 1] == 1).all()
        pst.append(inst.prior_stuck[inst.cls == 1])
        fl = np.zeros(inst.N, bool)
        fl[inst.cls == 1] = True
        assert (inst.availability(fl) == 1).all()
    assert np.mean(stuck) == pytest.approx(0.4, abs=0.02)
    assert np.mean(pst) == pytest.approx(0.4, abs=0.02)
    a, b = generate_kcopy(60003, replace(cell, M=1), K), generate_kcopy(60003, replace(cell, q=0.14, M=5), K)
    assert np.array_equal(a.cls, b.cls) and np.array_equal(a.v, b.v)


# ------------------------------------------- class independence (REQUIRED)
def test_class_stream_structural_independence():
    seed = 60011
    ref = generate_f0r(seed, BASE)
    alt_cls = generate_f0r(seed, BASE, stream_salt={"class": 1})
    assert not np.array_equal(ref.cls, alt_cls.cls)
    for f in ("P", "E", "a", "d", "u", "v", "b"):
        assert np.array_equal(getattr(ref, f), getattr(alt_cls, f)), f
    for name in ("P", "E", "a", "slack"):
        alt = generate_f0r(seed, BASE, stream_salt={name: 1})
        assert np.array_equal(ref.cls, alt.cls), name
        assert np.array_equal(ref.u, alt.u) and np.array_equal(ref.b, alt.b)
    alt = generate_f0r(seed, BASE, stream_salt={"slack": 1})
    assert not np.array_equal(ref.d, alt.d) and np.array_equal(ref.P, alt.P)
    # K-copy: roles come from their own stream
    kc = Cell(family="KCOPY", M=1, delta_A=2, q=0.4, c=8.0)
    k0, k1 = generate_kcopy(60005, kc), generate_kcopy(60005, kc, stream_salt={"class": 1})
    assert not np.array_equal(k0.cls, k1.cls) and np.array_equal(k0.v, k1.v)
    k2 = generate_kcopy(60005, kc, stream_salt={"scored_v": 1})
    assert np.array_equal(k0.cls, k2.cls) and not np.array_equal(k0.v, k2.v)


def _pvalue(table):
    table = np.asarray(table)
    table = table[:, table.sum(axis=0) > 0]
    return chi2_contingency(table)[1]


def test_class_statistical_independence_f0r():
    # 2200 independent draws = 50 tuning seeds x 44 salts of the generator's streams (seed rule)
    cls, P, E, win = [], [], [], []
    for s, z in map(draw, range(2200)):
        inst = generate_f0r(s, replace(BASE, M=0), stream_salt=z)
        cls.append(inst.cls), P.append(inst.P), E.append(inst.E), win.append(inst.d - inst.a)
    cls, P, E, win = map(np.array, (cls, P, E, win))
    assert cls.shape == (2200, 30)

    def table(feature, edges=None):
        f = feature if edges is None else np.digitize(feature, edges)
        levels = np.unique(f)
        return [[int(((cls == c) & (f == lv)).sum()) for lv in levels] for c in (0, 1)]

    idx = np.broadcast_to(np.arange(30), cls.shape)
    assert _pvalue(table(idx)) > 1e-3
    assert _pvalue(table(P)) > 1e-3
    assert _pvalue(table(E)) > 1e-3
    assert _pvalue(table(win, edges=[4, 7, 10, 14, 19])) > 1e-3
    # sanity: the test has power (a class-correlated feature is detected)
    assert _pvalue(table(cls * 2 + (np.random.default_rng(0).random(cls.shape) < 0.2))) < 1e-3


def test_role_statistical_independence_kcopy():
    cell = Cell(family="KCOPY", M=0, delta_A=2, q=0.4, c=8.0)
    # 2200 independent draws = 50 tuning seeds x 44 salts (seed rule)
    roles = np.array([generate_kcopy(s, cell, stream_salt=z).cls for s, z in map(draw, range(2200))])
    tab = [[int((roles[:, i] == r).sum()) for i in range(24)] for r in (0, 1, 2)]
    assert _pvalue(tab) > 1e-3
    # also in blocks of indices
    tab = [[int((roles[:, 8 * j:8 * j + 8] == r).sum()) for j in range(3)] for r in (0, 1, 2)]
    assert _pvalue(tab) > 1e-3
