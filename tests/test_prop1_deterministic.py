"""Proposition 1 for randomly assigned classes: deterministic schedulers on I_K.

I_K, delta = 2, pooled cap at c = K, q in {1/2, 2/5}. Slot 1 holds K spare units for the 2K twins.
A deterministic reliability-oblivious scheduler plays one open-loop schedule whatever the classes
are. The instance generator places classes uniformly at random, so which twin of each pair is
unreliable is a fair coin per pair. Claims, in exact fractions:

  (a) every feasible deterministic schedule (all of them, enumerated, including those with more
      than K twins in slot 1) has expected residual at least K q/2 averaged uniformly over the
      2^K assignments, and K q/2 is attained;
  (b) the worst case over assignments is at least the average, for every schedule;
  (c) the lowest-index tie-break scheduler (CE-LLF with equal estimates) meets K q/2 with equality
      on average.

No worst-case value is asserted: a schedule that hedges both twins of K/2 pairs loses exactly
K q/2 under every assignment, so the worst case of a deterministic scheduler can be as low as the
average.

Twin indexing used by (c): index j < K is A_j and j >= K is B_{j-K} (papere.prop_enum order), so
the lowest-index tie-break hedges A_0..A_{K-1}. The interleaved order A_0, B_0, A_1, ... is also
checked; the average is K q/2 for every choice of K hedged twins. Values come from the exhaustive
enumerator (``papere.prop_enum``) or its single-schedule simulator.
"""

from __future__ import annotations

import itertools
from fractions import Fraction as F

import numpy as np
import pytest

from papere import prop_enum as pe

KS = [1, 2, 3]
QS = [F(1, 2), F(2, 5)]


def hedge_lowest_index(K: int, hedged: tuple[int, ...]) -> pe.Schedule:
    """Twins (index j < K is A_j, j >= K is B_{j-K}) in slot 0; twins in `hedged` also in slot 1;
    every D in slot 1."""
    rows = [(1, 1) if j in hedged else (1, 0) for j in range(2 * K)]
    rows += [(0, 1)] * K
    return tuple(rows)


def relabel(sigma: pe.Schedule, K: int, unreliable: tuple[int, ...]) -> pe.Schedule:
    """The same schedule when the twins in `unreliable` (K of the 2K indices) are the unreliable
    ones. pe fixes the A copies as unreliable, so move those rows into the A slots."""
    rest = [j for j in range(2 * K) if j not in unreliable]
    order = list(unreliable) + rest
    return tuple(sigma[j] for j in order) + tuple(sigma[2 * K:])


def pair_masks(K: int):
    """For each assignment bit per pair, the K unreliable twin indices (pair k = A_k, B_k)."""
    for bits in itertools.product((0, 1), repeat=K):
        yield tuple(k + K * b for k, b in enumerate(bits))


def _mean_worst(sigma: pe.Schedule, K: int, q: F, assignments) -> tuple[F, F]:
    vals = [pe.expected_residual(relabel(sigma, K, u), K, q) for u in assignments]
    return sum(vals, F(0)) / len(vals), max(vals)


@pytest.mark.parametrize("K", KS)
@pytest.mark.parametrize("q", QS)
def test_lowest_index_tiebreak_meets_bound_on_average(K, q):
    """(c) with the A_0..A_{K-1}, B_0..B_{K-1} index order, and with the interleaved order."""
    order = {"A_then_B": tuple(range(K)),
             "interleaved": tuple([x for k in range(K) for x in (k, K + k)][:K])}
    for name, hedged in order.items():
        sigma = hedge_lowest_index(K, hedged)
        assert pe.is_feasible(sigma, K, K, pe.POOLED), name
        mean, worst = _mean_worst(sigma, K, q, pair_masks(K))
        assert mean == K * q / 2, name
        assert worst >= mean, name
    # uniform over every set of K unreliable positions (the generator permutes all participants)
    sigma = hedge_lowest_index(K, tuple(range(K)))
    mean, worst = _mean_worst(sigma, K, q, itertools.combinations(range(2 * K), K))
    assert mean == K * q / 2 and worst >= mean


@pytest.mark.parametrize("K", KS)
@pytest.mark.parametrize("q", QS)
def test_mean_over_pair_assignments_is_kq_over_2_for_any_k_hedges(K, q):
    """The average does not depend on which K twins are hedged."""
    for hedged in itertools.combinations(range(2 * K), K):
        sigma = hedge_lowest_index(K, hedged)
        mean, worst = _mean_worst(sigma, K, q, pair_masks(K))
        assert mean == K * q / 2
        assert worst >= mean


@pytest.mark.parametrize("q", QS)
def test_hedging_both_twins_of_half_the_pairs_is_flat_over_assignments(q):
    """K = 2: hedge A_0 and B_0. Every assignment gives exactly K q/2, so no worst-case claim."""
    K = 2
    sigma = hedge_lowest_index(K, (0, K))
    vals = {pe.expected_residual(relabel(sigma, K, u), K, q) for u in pair_masks(K)}
    assert vals == {K * q / 2}


def _codes(x: np.ndarray, K: int) -> np.ndarray:
    """Schedule array x[S, 3K, 2] -> integer codes (inverse of ``pe.code_matrix``)."""
    code = np.zeros(x.shape[0], dtype=np.int64)
    for j in range(2 * K):
        code |= (x[:, j, 0] << (2 * j)) | (x[:, j, 1] << (2 * j + 1))
    for k in range(K):
        code |= x[:, 2 * K + k, 1] << (4 * K + k)
    return code


@pytest.mark.parametrize("K", KS)
@pytest.mark.parametrize("q", QS)
def test_every_deterministic_schedule_averages_at_least_kq_over_2(K, q):
    """(a) and (b) over every feasible schedule of I_K at the pooled cap c = K."""
    tab = pe.residual_table(K, q)
    feas = pe.feasible_mask(tab.x, K, K, pe.POOLED)
    x = tab.x[feas]
    hedges = x[:, : 2 * K, 1].sum(axis=1)  # twins with a slot-1 setpoint (a "hedge" or a delay)
    per_mask = []
    for bits in itertools.product((0, 1), repeat=K):
        perm = list(range(3 * K))
        for k, b in enumerate(bits):
            if b:
                perm[k], perm[K + k] = K + k, k
        per_mask.append(tab.num[_codes(x[:, perm, :], K)])
    per_mask = np.stack(per_mask)  # [2^K, S], integers over tab.den
    total = per_mask.sum(axis=0)  # integers over tab.den * 2^K
    bound = K * q / 2 * tab.den * 2**K
    assert bound.denominator == 1
    bound = int(bound)
    assert total.min() == bound  # (a) attained
    assert total[hedges <= K].min() == bound  # also by schedules with at most K hedges
    assert (hedges > K).any()  # the enumeration includes schedules that drop a D copy for a hedge
    assert (total >= bound).all()  # (a)
    assert (per_mask.max(axis=0) * 2**K >= total).all()  # (b) worst case >= average
