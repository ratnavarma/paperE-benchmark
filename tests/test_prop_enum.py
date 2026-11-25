"""Gate G1: the exhaustive enumerator reproduces Propositions 1 and 3 and gap(c) on I_K.

Every enumerated value is brute force (schedules x realizations x histories) in exact
rationals; closed forms are used only on the right-hand side of the assertions.
Default grid K in {1, 2, 3}; PAPERE_G1_FULL=1 adds K = 4 and the slow orbit checks.
"""

from __future__ import annotations

import itertools
import os
import random
from decimal import ROUND_HALF_UP, Decimal
from fractions import Fraction as F

import numpy as np
import pytest

from papere import prop_enum as pe

FULL = os.environ.get("PAPERE_G1_FULL") == "1"
KS = [1, 2, 3] + ([4] if FULL else [])
QS = [F(1, 2), F(2, 5), F(7, 50)]
MS = [0, 1, 2, 3, 5]
MODES = list(pe.CAP_MODES)


def rnd(x: F, digits: int) -> str:
    d = Decimal(x.numerator) / Decimal(x.denominator)
    return str(d.quantize(Decimal(1).scaleb(-digits), rounding=ROUND_HALF_UP))


# ---------------------------------------------------------------------------
# Enumerator internals
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("K", [1, 2] + ([3] if FULL else []))
@pytest.mark.parametrize("q", QS)
def test_vectorized_residual_equals_scalar_simulation(K, q):
    tab = pe.residual_table(K, q)
    idx = range(len(tab.codes))
    if K >= 3:
        idx = random.Random(0).sample(list(idx), 2000)
    for s in idx:
        sigma = pe.decode(int(tab.codes[s]), K)
        assert pe.encode(sigma, K) == int(tab.codes[s])
        assert tab.value(s) == pe.expected_residual(sigma, K, q)


def test_vectorized_residual_sample_K3():
    q = F(2, 5)
    tab = pe.residual_table(3, q)
    for s in random.Random(1).sample(range(len(tab.codes)), 300):
        sigma = pe.decode(int(tab.codes[s]), 3)
        assert tab.value(s) == pe.expected_residual(sigma, 3, q)


@pytest.mark.parametrize("K", [1, 2, 3])
@pytest.mark.parametrize("mode", MODES)
def test_pruned_schedule_list_equals_feasible_mask(K, mode):
    cs = range(2 * K + 1) if mode == pe.POOLED else [0, K, 2 * K]
    tab = pe.residual_table(K, F(1, 2))
    for c in cs:
        listed = {pe.encode(s, K) for s in pe.schedules(K, c, mode)}
        masked = set(tab.codes[pe.feasible_mask(tab.x, K, c, mode)].tolist())
        assert listed == masked
        assert all(pe.is_feasible(pe.decode(code, K), K, c, mode) for code in listed)


def _brute_orbits(K, c, mode, classes):
    sched = pe.schedules(K, c, mode)
    group = pe.group_elements(K, mode, classes)
    canon = {}
    for s in sched:
        canon[pe.encode(s, K)] = min(pe.encode(pe.apply_perm(s, g), K) for g in group)
    return canon


ORBIT_CASES = [
    (1, pe.POOLED, None),
    (2, pe.POOLED, None),
    (2, pe.PER_COPY, None),
    (2, pe.POOLED, (0, 1, 1, 1)),
    (2, pe.PER_COPY, (0, 1, 1, 1)),
    (2, pe.POOLED, (0, 1, 2, 2)),
    (2, pe.PER_COPY, (0, 1, 2, 2)),
    (2, pe.PER_COPY, (0, 0, 1, 1)),
    (3, pe.PER_COPY, None),
    (3, pe.PER_COPY, (0, 1, 1, 1, 1, 1)),
] + ([(3, pe.POOLED, None), (3, pe.POOLED, (0, 1, 1, 1, 1, 1))] if FULL else [])


@pytest.mark.parametrize("K,mode,classes", ORBIT_CASES)
def test_canonical_keys_match_explicit_group_orbits(K, mode, classes):
    c = K
    brute = _brute_orbits(K, c, mode, classes)
    tab = pe.residual_table(K, F(1, 2))
    m = pe.feasible_mask(tab.x, K, c, mode)
    keys = pe.canonical_keys(tab.x[m], K, mode, classes)
    codes = tab.codes[m].tolist()
    # same partition: key equal <=> brute canonical equal
    k2b, b2k = {}, {}
    for code, key in zip(codes, keys.tolist()):
        b = brute[code]
        assert k2b.setdefault(key, b) == b
        assert b2k.setdefault(b, key) == key


def test_group_preserves_feasibility():
    for K in (1, 2, 3):
        for mode in MODES:
            sample = pe.schedules(K, K, mode)[::37]
            for g in pe.group_elements(K, mode):
                for s in sample:
                    assert pe.is_feasible(pe.apply_perm(s, g), K, K, mode)


# ---------------------------------------------------------------------------
# Proposition 1
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("K", KS)
@pytest.mark.parametrize("q", QS)
@pytest.mark.parametrize("mode", MODES)
def test_prop1_oblivious_optimum(K, q, mode):
    assert pe.oblivious_optimum(K, q, K, mode).value == pe.closed_prop1(K, q)
    assert pe.posterior_optimum(K, q, K, mode) == 0


@pytest.mark.parametrize("K", KS)
@pytest.mark.parametrize("mode", MODES)
def test_prop1_hedge_all_A_schedule_zero_everywhere(K, mode):
    sigma = pe.hedge_all_A_schedule(K)
    assert pe.is_feasible(sigma, K, K, mode)
    for pat in itertools.product((0, 1), repeat=K):
        assert pe.simulate_residual(sigma, pat, K) == 0


# ---------------------------------------------------------------------------
# gap(c)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("K", KS)
@pytest.mark.parametrize("q", QS)
def test_gap_pooled(K, q):
    for c in range(2 * K + 1):
        ob = pe.oblivious_optimum(K, q, c, pe.POOLED).value
        po = pe.posterior_optimum(K, q, c, pe.POOLED)
        assert ob - po == pe.closed_gap(K, q, c), c
        assert ob == pe.closed_oblivious(K, q, c)
        assert po == pe.closed_posterior(K, q, c)


@pytest.mark.parametrize("K", KS)
@pytest.mark.parametrize("q", QS)
def test_gap_per_copy(K, q):
    for c in (0, K, 2 * K):
        ob = pe.oblivious_optimum(K, q, c, pe.PER_COPY).value
        po = pe.posterior_optimum(K, q, c, pe.PER_COPY)
        assert ob - po == pe.closed_gap(K, q, c), c
        assert ob == pe.closed_oblivious(K, q, c)
        assert po == pe.closed_posterior(K, q, c)


# ---------------------------------------------------------------------------
# I1 table (MECHANISM 3.4) and Section 3.5
# ---------------------------------------------------------------------------

A0, B0, D0 = 0, 1, 2
H = F(1, 2)
I1_LAWS = {
    # name: (law, E[R], R in omega1 (A available), R in omega0 (A stuck))
    "posterior": ([(((1, 1), (1, 0), (0, 1)), F(1))], F(0), F(0), F(0)),
    "certainty_equivalent": ([(((1, 0), (1, 0), (0, 1)), F(1))], F(1, 2), F(0), F(1)),
    "pessimistic_D_first_random_twin": (
        [(((1, 1), (1, 0), (0, 1)), H), (((1, 0), (1, 1), (0, 1)), H)],
        F(1, 4), F(0), F(1, 2),
    ),
    "pessimistic_A_and_B_first": ([(((1, 1), (1, 1), (0, 0)), F(1))], F(1), F(1), F(1)),
    "one_twin_slot0_at_random": (
        [(((1, 0), (0, 1), (0, 1)), H), (((0, 1), (1, 0), (0, 1)), H)],
        F(1, 4), F(0), F(1, 2),
    ),
}


@pytest.mark.parametrize("name", list(I1_LAWS))
def test_I1_table_rows(name):
    law, er, r1, r0 = I1_LAWS[name]
    for sigma, _ in law:
        assert pe.is_feasible(sigma, 1, 1, pe.POOLED)  # cap 2 per slot
    assert pe.law_value(law, 1, H) == er
    real = pe.law_realization_values(law, 1)
    assert real[(0,)] == r1 and real[(1,)] == r0
    kwh = {"posterior": "0", "certainty_equivalent": "0.125", "pessimistic_A_and_B_first": "0.25",
           "pessimistic_D_first_random_twin": "0.0625", "one_twin_slot0_at_random": "0.0625"}[name]
    assert pe.law_value(law, 1, H) / 4 == F(kwh)  # kWh column, 1 unit = 0.25 kWh


def test_I1_headroom_margin():
    # m = 1: C' = 1 per slot; at least 1 unit short in every realization
    assert pe.min_residual_any_realization(1, 0, pe.POOLED, cap_override=(1, 1)) == 1
    assert pe.min_expected_with_caps(1, H, 1, 1) == 1


def test_I1_zero_residual_schedules():
    zs = set(pe.zero_residual_schedules(1, 1, pe.POOLED))
    assert zs == {((0, 1), (1, 0), (0, 1)), ((1, 1), (1, 0), (0, 1))}


def test_I1_section35_bound():
    assert pe.oblivious_optimum(1, H, 1, pe.POOLED).value == F(1, 4)
    assert pe.deterministic_oblivious_worst(1, H, 1, pe.POOLED) == F(1, 2)
    # average over I1 and swap(I1) of a deterministic schedule, minimized: 0.25
    tab = pe.residual_table(1, H)
    m = pe.feasible_mask(tab.x, 1, 1, pe.POOLED)
    best = min(
        (pe.expected_residual(s, 1, H) + pe.expected_residual(pe.apply_perm(s, (1, 0, 2)), 1, H)) / 2
        for s in (pe.decode(int(c), 1) for c in tab.codes[m])
    )
    assert best == F(1, 4)


# ---------------------------------------------------------------------------
# Proposition 3
# ---------------------------------------------------------------------------

P3_CASES = [(K, q, M) for K in KS for q in QS for M in MS]


def _kinds(K, M):
    return ["count"] + (["full"] if K * M <= 8 else [])


@pytest.mark.parametrize("K,q,M", P3_CASES)
def test_prop3_per_copy(K, q, M):
    vals = []
    for kind in _kinds(K, M):
        r = pe.history_optimum(K, q, M, pe.PER_COPY, kind, prefill_qs=QS)
        vals.append(r.value)
        assert r.value == pe.closed_prop3_per_copy(K, q, M)
        for I, vs in r.per_history_by_I.items():
            assert vs == {pe.closed_prop3_per_copy_given_I(K, q, I)}
        e1, per = pe.identified_first_value(K, q, M, pe.PER_COPY, kind)
        assert e1 == r.value
        for cls, v in per.items():
            assert v == pe.history_class_optimum(K, q, K, pe.PER_COPY, cls).value
        ob = pe.oblivious_optimum(K, q, K, pe.PER_COPY).value
        assert pe.share(r.value, K, q) == 1 - r.value / ob == pe.f_identified(q, M)
    assert len(set(vals)) == 1  # full sequences == stuck counts


@pytest.mark.parametrize("K,q,M", P3_CASES)
def test_prop3_pooled(K, q, M):
    vals = []
    for kind in _kinds(K, M):
        r = pe.history_optimum(K, q, M, pe.POOLED, kind, prefill_qs=QS)
        vals.append(r.value)
        assert r.value == pe.closed_prop3_pooled(K, q, M)
        for I, vs in r.per_history_by_I.items():
            assert vs == {pe.closed_prop3_pooled_given_I(K, q, I)}
            assert r.by_identified[I] == pe.closed_prop3_pooled_given_I(K, q, I)
        e1, per = pe.identified_first_value(K, q, M, pe.POOLED, kind)
        assert e1 == r.value
        for cls, v in per.items():
            assert v == pe.history_class_optimum(K, q, K, pe.POOLED, cls).value
        ob = pe.oblivious_optimum(K, q, K, pe.POOLED).value
        s = 1 - r.value / ob
        f = pe.f_identified(q, M)
        assert s >= f / (2 - f)
        if K == 1:
            assert s == f
    assert len(set(vals)) == 1


@pytest.mark.parametrize("K", KS)
@pytest.mark.parametrize("q", QS)
@pytest.mark.parametrize("mode", MODES)
def test_prop3_M0_equals_prop1(K, q, mode):
    r = pe.history_optimum(K, q, 0, mode, "count")
    assert r.value == pe.oblivious_optimum(K, q, K, mode).value
    assert r.n_histories == 1


@pytest.mark.parametrize("q", QS)
@pytest.mark.parametrize("M", [1, 3, 5])
def test_prop3_pooled_large_K_closed_form(q, M):
    """Closed form only (no enumeration): K = 1000 share within 1e-3 of f/(2-f)."""
    K = 1000
    f = pe.f_identified(q, M)
    s = pe.share(pe.closed_prop3_pooled(K, q, M), K, q)
    assert abs(s - f / (2 - f)) < F(1, 1000)
    assert s >= f / (2 - f)


# MECHANISM 3.9 table and PLAN Section 7: (q, M, f, per-copy share, pooled large-K share)
TABLE_39 = [
    (F(2, 5), 1, "0.40", "0.40", "0.25"),
    (F(2, 5), 3, "0.784", "0.78", "0.64"),
    (F(2, 5), 5, "0.922", "0.92", "0.86"),
    (F(1, 2), 3, "0.875", "0.88", "0.78"),
]


@pytest.mark.parametrize("q,M,f_s,pc_s,po_s", TABLE_39)
def test_table_39_and_plan7(q, M, f_s, pc_s, po_s):
    f = pe.f_identified(q, M)
    assert rnd(f, len(f_s) - 2) == f_s
    # per-copy share from the enumeration (K = 3)
    r = pe.history_optimum(3, q, M, pe.PER_COPY, "count")
    assert rnd(1 - r.value / pe.oblivious_optimum(3, q, 3, pe.PER_COPY).value, 2) == pc_s
    # pooled large K: closed form at K = 1000 and the limit f/(2-f)
    assert rnd(pe.share(pe.closed_prop3_pooled(1000, q, M), 1000, q), 2) == po_s
    assert rnd(f / (2 - f), 2) == po_s
    if q == F(2, 5):  # PLAN Section 7 states f to two decimals
        assert rnd(f, 2) == {1: "0.40", 3: "0.78", 5: "0.92"}[M]
