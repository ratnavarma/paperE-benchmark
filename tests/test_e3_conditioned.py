"""Tests for scripts/e3_conditioned.py: conditional closed forms against exhaustive
enumeration of the hedge laws on small K, in exact Fractions.

Instances are generated only on tuning seeds 60000-60049 (tests/conftest.py); no policy is
simulated here.
"""
from __future__ import annotations

import importlib.util
import itertools
import json
import math
from fractions import Fraction as F
from pathlib import Path

import pytest

from papere import prop_enum as pe
from papere.generator import generate_kcopy
from papere.instance import Cell

_SPEC = importlib.util.spec_from_file_location(
    "e3_conditioned", Path(__file__).resolve().parents[1] / "scripts" / "e3_conditioned.py")
ec = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(ec)

QS = [F(7, 50), F(2, 5), F(1, 2)]


# ------------------------------------------------------------------ enumeration vs closed form
@pytest.mark.parametrize("K", (1, 2, 3))
def test_closed_forms_equal_enumeration_every_realization(K):
    """Every stuck pattern, prior counts 0..2, every c, both caps, all three policies."""
    v = ec.verify_closed_forms([K], max_count=2)
    assert v["all_equal"], v["mismatches"][:3]
    assert v["cases"] > 0
    for form in ("cond_pop", "cond_oracle", "cond_e1", "cond_e1_at_K",
                 "greedy_mean_e1", "greedy_var_e1", "greedy_var_pop", "greedy_var_oracle"):
        assert v["by_form"][form]["equal"] == v["by_form"][form]["cases"] > 0


def test_closed_forms_equal_enumeration_K4():
    v = ec.verify_closed_forms([4], max_count=1)
    assert v["all_equal"], v["mismatches"][:3]


def test_closed_forms_equal_enumeration_K4_distinct_counts_pooled():
    """K = 4 pooled with every count level distinct (the boundary level is a single copy)."""
    K = 4
    for c in range(0, 2 * K + 1):
        for stuck in itertools.product((0, 1), repeat=K):
            for counts in itertools.permutations((0, 1, 2, 3)):
                m1, m2, _ = ec.enumerate_law(K, c, "pooled", "guarded_mpc_e1", stuck, counts)
                assert ec.cond_e1(K, c, "pooled", list(zip(stuck, counts))) == m1
                real = ec.Realization.abstract(K, c, "pooled", stuck, counts)
                assert ec.greedy_moments(real, "guarded_mpc_e1") == (m1, m2 - m1 * m1)


def test_hand_values():
    # pooled K = 2, c = 1: one hedge over 4 twins; a stuck A is missed w.p. 3/4
    assert ec.cond_pop(2, 1, 1) == F(3, 4)
    assert ec.enumerate_law(2, 1, "pooled", "pop_mpc", (1, 0), (0, 0))[0] == F(3, 4)
    # oracle, K = 3, c = 1, two stuck: one of three A copies hedged -> 2 * 2/3
    assert ec.cond_oracle(3, 1, 2) == F(4, 3)
    assert ec.enumerate_law(3, 1, "pooled", "oracle_mpc", (1, 1, 0), (0, 0, 0))[0] == F(4, 3)
    # e1 pooled K = 3, c = 3, A_0 identified (stuck), A_1 unidentified stuck: A_0 hedged,
    # two hedges over 5 unidentified twins -> A_1 missed w.p. 3/5
    assert ec.cond_e1(3, 3, "pooled", [(1, 2), (1, 0), (0, 0)]) == F(3, 5)
    assert ec.cond_e1_at_K(3, "pooled", 1, 1) == F(3, 5)
    # e1 pooled K = 3, c = 1, two identified with counts 2 and 1, both stuck: the count-2
    # copy takes the only hedge, the count-1 copy is missed
    assert ec.cond_e1(3, 1, "pooled", [(1, 2), (1, 1), (0, 0)]) == 1
    # e1 pooled, c = 1, two identified with equal counts, both stuck: one of them missed
    assert ec.cond_e1(3, 1, "pooled", [(1, 1), (1, 1), (0, 0)]) == 1
    assert ec.enumerate_law(3, 1, "pooled", "guarded_mpc_e1", (1, 1, 0), (1, 1, 0))[0] == 1
    # per-copy, c = K: an unidentified stuck A is missed w.p. 1/2, an identified one never
    assert ec.cond_e1(2, 2, "per_copy", [(1, 0), (1, 3)]) == F(1, 2)


@pytest.mark.parametrize("K", (2, 3, 4))
def test_law_support_sizes(K):
    """The enumerated laws are the uniform hedge subsets of the decision laws."""
    zero = (0,) * K
    for c in range(0, 2 * K + 1):
        assert ec.enumerate_law(K, c, "pooled", "pop_mpc", zero, zero)[2] == math.comb(2 * K, c)
        n_or = math.comb(K, c) if c <= K else math.comb(K, c - K)
        assert ec.enumerate_law(K, c, "pooled", "oracle_mpc", zero, zero)[2] == n_or
    assert ec.enumerate_law(K, K, "per_copy", "pop_mpc", zero, zero)[2] == 2 ** K
    counts = (1,) + (0,) * (K - 1)       # one identified copy
    assert ec.enumerate_law(K, K, "pooled", "guarded_mpc_e1", zero, counts)[2] == \
        math.comb(2 * K - 1, K - 1)
    assert ec.enumerate_law(K, K, "per_copy", "guarded_mpc_e1", zero, counts)[2] == 2 ** (K - 1)


def test_deterministic_cases_have_zero_variance():
    K = 3
    for stuck in itertools.product((0, 1), repeat=K):
        for c in (0, 2 * K):
            for pol in ec.POLICIES:
                real = ec.Realization.abstract(K, c, "pooled", stuck, (0,) * K)
                assert ec.greedy_moments(real, pol)[1] == 0
        real = ec.Realization.abstract(K, K, "pooled", stuck, (0,) * K)
        assert ec.greedy_moments(real, "oracle_mpc") == (0, 0)


# ------------------------------------------------------------------ conditional -> unconditional
@pytest.mark.parametrize("K", (1, 2, 3))
def test_conditional_forms_average_to_prop_enum_closed_forms(K):
    t = ec.verify_total_expectation([K], QS, [0, 1, 3, 5])
    assert t["all_equal"], t["mismatches"][:3]
    assert t["cases"] == len(QS) * (2 * (2 * K + 1) + 2 * 3 + 2 * 4)


@pytest.mark.parametrize("cap_mode", ("pooled", "per_copy"))
def test_prop3_conditional_given_I_matches_prop_enum(cap_mode):
    """Averaging cond_e1_at_K over the scored stuck draws given I gives prop_enum's
    closed_prop3_*_given_I, for every I."""
    K = 4
    for q in QS:
        for I in range(K + 1):
            e = F(0)
            for pat, p in pe.stuck_patterns(K, q):
                counts = [1] * I + [0] * (K - I)
                S_un = sum(s for s, n in zip(pat, counts) if n == 0)
                e += p * ec.cond_e1_at_K(K, cap_mode, I, S_un)
            want = (pe.closed_prop3_pooled_given_I if cap_mode == "pooled"
                    else pe.closed_prop3_per_copy_given_I)(K, q, I)
            assert e == want


# ------------------------------------------------------------------ reading an instance
def _cells(K):
    out = []
    for q in (0.14, 0.4):
        for M in (0, 3):
            for c in (0, K // 2, K, 2 * K):
                out.append(Cell(family="KCOPY", M=M, delta_A=2, delta_b=0, q=q, c=float(c),
                                cap_mode="pooled"))
            for c in (0, K, 2 * K):
                out.append(Cell(family="KCOPY", M=M, delta_A=2, delta_b=0, q=q, c=float(c),
                                cap_mode="per_copy"))
    return out


@pytest.mark.parametrize("K", (4, 8))
def test_realization_from_instance(K):
    for seed in (60000, 60001, 60049):
        S_by_q = {}
        for cell in _cells(K):
            inst = generate_kcopy(seed, cell, K=K)
            real = ec.Realization.from_instance(inst, K)
            A = inst.cls == 1
            stuck = (inst.availability()[:, 0] == 0) & A
            assert real.S == int(stuck.sum())
            assert real.I == int((inst.prior_stuck.any(axis=1) & A).sum())
            assert sum(len(g) for g in real.groups) == 2 * K
            # S depends on (seed, q) only: common random numbers across c, M and cap mode
            assert S_by_q.setdefault(cell.q, real.S) == real.S
            for pol in ec.POLICIES:
                m, _ = ec.greedy_moments(real, pol)
                assert ec.cond_closed(real, pol) == m
            if int(cell.c) == K:
                assert ec.cond_e1_at_K(K, cell.cap_mode, real.I, real.S_unid) == \
                    ec.cond_closed(real, "guarded_mpc_e1")


def test_realization_matches_abstract_order_per_copy():
    """Per-copy groups are the copies {A_k, B_k}; the closed forms agree with the
    abstract (prop_enum-ordered) realization built from the same stuck and counts."""
    K = 4
    cell = Cell(family="KCOPY", M=3, delta_A=2, delta_b=0, q=0.4, c=float(K), cap_mode="per_copy")
    inst = generate_kcopy(60002, cell, K=K)
    real = ec.Realization.from_instance(inst, K)
    A = [next((s, n) for r, s, n in g if r == "A") for g in real.groups]
    ab = ec.Realization.abstract(K, K, "per_copy", [s for s, _ in A], [n for _, n in A])
    for pol in ec.POLICIES:
        assert ec.greedy_moments(real, pol) == ec.greedy_moments(ab, pol)


# ------------------------------------------------------------------ rows and statistics
def test_load_rows_refuses_missing_policy(tmp_path):
    cid = "KCOPY_pooled_q0.4_c8_M0_dA2_db0"
    seeds = [ec.SEED_LO, ec.SEED_LO + 1]
    p = tmp_path / "rows.jsonl"
    with open(p, "w") as f:
        for s in seeds:
            for pol in ("pop_mpc", "oracle_mpc"):
                f.write(json.dumps({"policy": pol, "cell_id": cid, "seed": s, "R_abs_u": 1.0,
                                    "study_family": "KCOPY", "mode": "frozen"},
                                   separators=(",", ":")) + "\n")
    with pytest.raises(SystemExit):
        ec.load_rows(p, {cid}, seeds)


def test_series_stats_exact_zero_and_interval():
    st = ec.series_stats([F(0)] * 10, 0.999)
    assert st["identically_zero"] and ec.contains(st, 0.0, "sim") and ec.contains(st, 0.0, "pw")
    st = ec.series_stats([F(1), F(-1)] * 20, 0.999)
    assert st["mean"] == 0 and st["sim_lo"] < st["pw_lo"] < 0 < st["pw_hi"] < st["sim_hi"]
    assert ec.sign(F(-1, 3)) == "below" and ec.sign(F(0)) == "zero"
