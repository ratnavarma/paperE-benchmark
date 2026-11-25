"""Tests for papere.enumerator part 1 (brute-force clairvoyant)."""

from __future__ import annotations

import itertools
import os
from fractions import Fraction

import numpy as np
import pytest

from papere.enumerator import (
    _rows,
    brute_force,
    brute_force_naive,
    grid_problems,
    random_battery,
    random_problem,
)
from papere.flow import FlowProblem

FULL = os.environ.get("PAPERE_G1_FULL") == "1"


def test_rows_exhaustive():
    rows = _rows([2, 0, 3], 3)
    expect = [r for r in itertools.product(range(3), range(1), range(4)) if sum(r) <= 3]
    assert rows == expect and len(set(rows)) == len(rows)


def test_merged_dp_equals_naive_dfs():
    """The merged DP must reach exactly what the plain DFS over every matrix reaches."""
    n = 2000 if FULL else 600
    for k, p in enumerate(random_battery(n, 777)):
        a, b = brute_force(p), brute_force_naive(p)
        assert a.F_star == b.F_star, k
        assert a.leximin_sorted == b.leximin_sorted, k
        assert a.min_peak == b.min_peak, k
        assert a.max_flow_z == b.max_flow_z, k


def test_merged_dp_equals_naive_on_grid_sample():
    for k, p in enumerate(grid_problems()):
        if k % 7:
            continue
        a, b = brute_force(p), brute_force_naive(p)
        assert (a.F_star, a.leximin_sorted, a.min_peak, a.max_flow_z) == (
            b.F_star, b.leximin_sorted, b.min_peak, b.max_flow_z), k


def test_hand_i1():
    cap = np.array([[0, 1], [1, 1], [0, 1]])  # omega0: A unavailable at slot 0
    p = FlowProblem(E=[1, 1, 1], cap=cap, group=[0, 0, 0], slot_cap=[[2, 2]])
    r = brute_force(p)
    assert r.F_star == 3 and r.leximin_sorted == (0, 0, 0) and r.min_peak == 2.0
    assert r.max_flow_z == frozenset({(1, 1, 1)})
    p1 = FlowProblem(E=[1, 1, 1], cap=cap, group=[0, 0, 0], slot_cap=[[2, 1]])
    r1 = brute_force(p1)  # slot 1 can take only one of A, D
    assert r1.F_star == 2 and r1.leximin_sorted == (1, 0, 0)
    assert r1.max_flow_z == frozenset({(1, 1, 0), (0, 1, 1)})


def test_hand_leximin_and_peak():
    p = FlowProblem(E=[2, 4], cap=[[2], [4]], group=[0, 0], slot_cap=[[4]], base=[[0.75]])
    r = brute_force(p)
    assert r.F_star == 4
    assert r.max_flow_z == frozenset({(0, 4), (1, 3), (2, 2)})
    assert r.leximin_sorted == (Fraction(1, 2), Fraction(0))
    assert r.min_peak == 4.75


def test_size_guard():
    p = FlowProblem(E=[1] * 5, cap=np.ones((5, 2), int), group=[0] * 5, slot_cap=[[5, 5]])
    with pytest.raises(ValueError):
        brute_force(p)


def test_generators_stay_in_box():
    rng = np.random.default_rng(1)
    for _ in range(2000):
        p = random_problem(rng)
        assert 1 <= p.N <= 4 and 1 <= p.H <= 4 and p.G in (1, 2, 3)
        assert ((p.E >= 1) & (p.E <= 6)).all()
        assert (p.cap <= 3).all() and ((p.slot_cap >= 0) & (p.slot_cap <= 4)).all()
        for i in range(p.N):  # cap row is P_i * mask
            nz = set(p.cap[i][p.cap[i] > 0].tolist())
            assert len(nz) <= 1
    a = random_battery(50, 3)
    b = random_battery(50, 3)
    assert all(np.array_equal(x.cap, y.cap) and np.array_equal(x.base, y.base) for x, y in zip(a, b))
    probs = list(grid_problems())
    assert len(probs) == 20448
    assert max(p.N for p in probs) == 2 and max(p.H for p in probs) == 2
