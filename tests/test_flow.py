"""Tests for papere.flow against networkx and the exhaustive enumerator (gate G1).

Default run: systematic grid (every N <= 2, H <= 2 instance in a bounded box,
~20k instances) plus a seeded random battery of 6,000 instances (N <= 4, H <= 4).
With PAPERE_G1_FULL=1: the full grid (~258k) and a 20000-instance battery.
"""

from __future__ import annotations

import os
import sys
import time
from fractions import Fraction

import numpy as np
import pytest

from papere.enumerator import brute_force, grid_problems, random_battery
from papere.flow import (
    FlowProblem,
    _pair_improves,
    clairvoyant,
    is_feasible,
    is_leximin_local_optimum,
    leximin_flow,
    max_flow,
    min_peak_flow,
    networkx_max_flow,
    peak,
    sorted_fractions,
)

FULL = os.environ.get("PAPERE_G1_FULL") == "1"
RANDOM_N = 20000 if FULL else 6000
RANDOM_SEED = 20261020


def _check(p: FlowProblem) -> list[str]:
    """All flow-vs-brute-force assertions for one instance; returns failures."""
    errs: list[str] = []
    bf = brute_force(p)
    F, y = max_flow(p)
    Fn, yn = networkx_max_flow(p)
    c = clairvoyant(p)
    if not (F == Fn == bf.F_star == c.F_star):
        errs.append(f"F*: dinic {F}, networkx {Fn}, brute {bf.F_star}, clairvoyant {c.F_star}")
    for name, yy, FF in (("max_flow", y, F), ("networkx", yn, Fn), ("leximin", c.leximin_y, F),
                         ("min_peak", c.min_peak_y, F), ("clairvoyant.y", c.y, F)):
        if not is_feasible(p, yy):
            errs.append(f"{name} y infeasible")
        if yy.dtype != np.int64:
            errs.append(f"{name} y dtype {yy.dtype}")
        if int(yy.sum()) != FF:
            errs.append(f"{name} y sum {int(yy.sum())} != {FF}")
    # leximin
    lex = sorted_fractions(p.E, c.leximin_shortfall)
    if lex != bf.leximin_sorted:
        errs.append(f"leximin {lex} != brute {bf.leximin_sorted}")
    if not np.array_equal(c.leximin_shortfall, p.E - c.leximin_y.sum(axis=1)):
        errs.append("leximin_shortfall != E - row sums")
    if tuple(c.leximin_y.sum(axis=1).tolist()) not in bf.max_flow_z:
        errs.append("leximin z not among brute-force max-flow delivery vectors")
    if not is_leximin_local_optimum(p, c.leximin_y):
        errs.append("leximin fails the local-exchange certificate")
    # min peak
    if abs(c.min_peak - bf.min_peak) > 1e-9:
        errs.append(f"min peak {c.min_peak} != brute {bf.min_peak}")
    if abs(peak(p, c.min_peak_y) - c.min_peak) > 1e-12:
        errs.append("min_peak_y does not achieve min_peak")
    # identities
    s_own = np.maximum(0, p.E - p.cap.sum(axis=1))
    if not np.array_equal(c.s_own, s_own) or c.s_own.dtype != np.int64:
        errs.append("s_own")
    if c.R_star != int(p.E.sum()) - c.F_star or c.R_couple != c.R_star - int(s_own.sum()):
        errs.append("R*/R_couple identity")
    if c.R_couple < 0:
        errs.append("R_couple < 0")
    for v in (c.F_star, c.R_star, c.R_couple):
        if type(v) is not int:
            errs.append(f"non-int scalar {type(v)}")
    return errs


def _run_battery(problems) -> int:
    n = 0
    failures = []
    for p in problems:
        n += 1
        e = _check(p)
        if e:
            failures.append((n, p, e))
            if len(failures) >= 5:
                break
    assert not failures, "\n".join(f"#{k}: {e}\n{p}" for k, p, e in failures)
    return n


def test_systematic_grid():
    n = _run_battery(grid_problems(full=FULL))
    assert n == (257712 if FULL else 20448)


def test_random_battery():
    n = _run_battery(random_battery(RANDOM_N, RANDOM_SEED))
    assert n == RANDOM_N


# --------------------------------------------------------------------------- #
# Hand cases
# --------------------------------------------------------------------------- #
def _i1(omega: int) -> FlowProblem:
    """MECHANISM_E_v2 Section 3, instance I1 (K = 1): A, B windows {0, 1}, D window
    {1}; P = E = 1; cap 2 per slot; omega = 1 iff A is available at slot 0."""
    cap = np.array([[omega, 1], [1, 1], [0, 1]])
    return FlowProblem(E=[1, 1, 1], cap=cap, group=[0, 0, 0], slot_cap=[[2, 2]], base=[[0.0, 0.0]])


@pytest.mark.parametrize("omega", [0, 1])
def test_i1_r_star_zero(omega):
    p = _i1(omega)
    c = clairvoyant(p)
    assert c.F_star == 3 and c.R_star == 0 and c.R_couple == 0
    assert c.s_own.tolist() == [0, 0, 0]
    assert c.leximin_shortfall.tolist() == [0, 0, 0]
    assert c.min_peak == 2.0  # 3 units over 2 slots of cap 2
    assert networkx_max_flow(p)[0] == 3 == brute_force(p).F_star
    if omega == 0:  # B at slot 0, A and D at slot 1
        assert c.y[:, 0].tolist() == [0, 1, 0] and c.y[:, 1].tolist() == [1, 0, 1]


def test_own_and_coupling_shortfall():
    # 0: E=5 but only 2 units of own capacity (s_own = 3), uses slot 1.
    # 1, 2: E=1 each, both only at slot 0, slot cap 1 -> one coupling unit lost.
    p = FlowProblem(
        E=[5, 1, 1],
        cap=[[0, 2], [1, 0], [1, 0]],
        group=[0, 0, 0],
        slot_cap=[[1, 3]],
        base=[[0.5, 1.25]],
    )
    c = clairvoyant(p)
    assert c.F_star == 3 and c.R_star == 4
    assert c.s_own.tolist() == [3, 0, 0] and c.R_couple == 1
    assert sorted(c.leximin_shortfall.tolist()) == [0, 1, 3]
    assert c.min_peak == pytest.approx(3.25)
    assert brute_force(p).F_star == 3


def test_leximin_equal_threshold_exchange():
    """The naive rule 'improve iff s_i/E_i > (s_j+1)/E_j' misses this exchange.

    i: E=2, j: E=4, one slot of cap 4. Max flows: z_i in {0,1,2}, z_j = 4 - z_i.
    z_i=1 gives (1/2, 1/4); z_i=2 gives (1/2, 0), the leximin."""
    p = FlowProblem(E=[2, 4], cap=[[2], [4]], group=[0, 0], slot_cap=[[4]])
    assert Fraction(1, 2) == Fraction(1 + 1, 4)  # equality case of the naive rule
    assert _pair_improves(1, 2, 1, 4)
    y = leximin_flow(p)
    assert y[:, 0].tolist() == [2, 2]
    assert sorted_fractions(p.E, p.E - y.sum(axis=1)) == (Fraction(1, 2), Fraction(0))
    assert brute_force(p).leximin_sorted == (Fraction(1, 2), Fraction(0))
    assert not is_leximin_local_optimum(p, np.array([[1], [3]]))
    assert is_leximin_local_optimum(p, y)


def test_min_peak_moves_load_to_low_base_slot():
    # One participant, 2 units, two slots; base 3.0 then 0.5 -> put both in slot 1.
    p = FlowProblem(E=[2], cap=[[2, 2]], group=[0], slot_cap=[[2, 2]], base=[[3.0, 0.5]])
    pk, y = min_peak_flow(p)
    assert pk == 3.0 and y.tolist() == [[0, 2]]
    # Two groups summed per slot.
    p = FlowProblem(E=[2, 2], cap=[[2, 2], [2, 2]], group=[0, 1], slot_cap=[[2, 2], [2, 2]],
                    base=[[1.0, 0.25], [1.0, 0.25]])
    pk, y = min_peak_flow(p)
    # slot base totals (2.0, 0.5); loads (0,4) -> 4.5, (1,3) -> 3.5, (2,2) -> 4.0
    assert pk == pytest.approx(3.5) and y.sum(axis=0).tolist() == [1, 3]
    assert pk == pytest.approx(brute_force(p).min_peak)


def test_empty_and_zero_cases():
    p = FlowProblem(E=[0, 3], cap=[[0, 0], [0, 0]], group=[0, 0], slot_cap=[[0, 0]])
    c = clairvoyant(p)
    assert c.F_star == 0 and c.R_star == 3 and c.s_own.tolist() == [0, 3] and c.R_couple == 0
    assert c.leximin_y.sum() == 0 and c.min_peak == 0.0


def test_problem_validation():
    with pytest.raises(ValueError):
        FlowProblem(E=[2.9], cap=[[1]], group=[0], slot_cap=[[1]])
    with pytest.raises(ValueError):
        FlowProblem(E=[2], cap=[[1.99]], group=[0], slot_cap=[[1]])
    with pytest.raises(ValueError):
        FlowProblem(E=[2], cap=[[1]], group=[0], slot_cap=[[0.5]])
    with pytest.raises(ValueError):
        FlowProblem(E=[float("nan")], cap=[[1]], group=[0], slot_cap=[[1]])
    with pytest.raises(ValueError):
        FlowProblem(E=[-3.0], cap=[[1]], group=[0], slot_cap=[[1]])
    ok = FlowProblem(E=[3.0], cap=[[2.0 + 1e-12]], group=[0.0], slot_cap=[[1.0]])
    assert ok.E.tolist() == [3] and ok.cap.tolist() == [[2]]
    assert ok.E.dtype == ok.cap.dtype == ok.slot_cap.dtype == ok.group.dtype == np.int64
    with pytest.raises(ValueError):
        FlowProblem(E=[1], cap=[[1, 1]], group=[1], slot_cap=[[1, 1]])
    with pytest.raises(ValueError):
        FlowProblem(E=[1], cap=[[1, 1]], group=[0], slot_cap=[[1]])
    with pytest.raises(ValueError):
        FlowProblem(E=[-1], cap=[[1]], group=[0], slot_cap=[[1]])


def test_flow_does_not_use_networkx(monkeypatch):
    monkeypatch.setitem(sys.modules, "networkx", None)  # any import now raises
    p = _i1(0)
    c = clairvoyant(p)
    assert c.F_star == 3
    with pytest.raises(ImportError):
        networkx_max_flow(p)


# --------------------------------------------------------------------------- #
# Performance sanity
# --------------------------------------------------------------------------- #
def _big(seed: int, N: int = 300, H: int = 24, rho: float = 1.2) -> FlowProblem:
    rng = np.random.default_rng(seed)
    P = rng.integers(1, 4, N)
    E = rng.integers(2, 13, N)
    a = rng.integers(0, 3, N)
    d = np.minimum(H, a + np.ceil(E / P).astype(int) + rng.integers(0, 13, N))
    A = (rng.random((N, H)) < 0.9).astype(np.int64)
    cap = np.zeros((N, H), dtype=np.int64)
    for i in range(N):
        cap[i, a[i]:d[i]] = P[i] * A[i, a[i]:d[i]]
    sc = np.full((1, H), int(E.sum() / rho / H))
    base = (N * (1 + 0.15 * np.arange(H) / (H - 1)) + rng.normal(0, 1, H))[None, :]
    return FlowProblem(E=E, cap=cap, group=np.zeros(N, dtype=np.int64), slot_cap=sc, base=base)


def test_performance_n300(capsys):
    p = _big(7)
    t0 = time.perf_counter()
    c = clairvoyant(p)
    dt = time.perf_counter() - t0
    with capsys.disabled():
        print(f"\n[perf] N=300 H=24 clairvoyant (max flow + leximin + min peak): {dt:.3f} s, "
              f"F*={c.F_star}, R*={c.R_star}")
    assert dt < 5.0
    assert c.F_star == networkx_max_flow(p)[0]
    assert is_feasible(p, c.leximin_y) and is_feasible(p, c.min_peak_y)
    assert c.leximin_y.sum() == c.F_star == c.min_peak_y.sum()
    assert is_leximin_local_optimum(p, c.leximin_y)
