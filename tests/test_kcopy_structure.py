"""generate_kcopy builds exactly the enumerator's I_K (gate G1 structure item).

For K in {1, 2, 3, 4, 8}, several seeds, both cap modes and the c values of KCOPY_CELLS
(rescaled from K = 8 to K: pooled c -> c K / 8 when integer; per-copy c in {0, 8, 16}
-> {0, K, 2K}), the generated instance must match prop_enum's model: roles, windows,
P = E = 1, H = 2, cap groups and caps, zero base load, availability pattern, lags, and
stuck frequencies (scored and prior events) consistent with q.
"""

from __future__ import annotations

from dataclasses import replace
from fractions import Fraction as F

import numpy as np
import pytest
from scipy.stats import binomtest

from papere import prop_enum as pe
from papere.generator import KCOPY_CELLS, generate_kcopy

KS = [1, 2, 3, 4, 8]
SEEDS = [60000, 60001, 60002, 60037, 60049]
ROLE_CLS = {"A": 1, "B": 0, "D": 2}


def cells_for_K(K: int):
    out, seen = [], set()
    for cell in KCOPY_CELLS:
        cK = F(int(cell.c)) * K / 8
        if cell.cap_mode == pe.PER_COPY:
            cK = F(int(cell.c), 8) * K
        if cK.denominator != 1:
            continue
        new = replace(cell, c=float(cK))
        if new not in seen:
            seen.add(new)
            out.append(new)
    return out


def check_structure(inst, K: int, c: int, mode: str) -> None:
    assert inst.N == pe.n_participants(K) and inst.H == 2
    cls = np.asarray(inst.cls)
    for r, v in ROLE_CLS.items():
        assert int((cls == v).sum()) == K, r
    assert np.all(np.asarray(inst.P) == 1) and np.all(np.asarray(inst.E) == 1)
    win = {r: pe.windows(K)[i * K] for i, r in enumerate("ABD")}
    assert win == {"A": (0, 2), "B": (0, 2), "D": (1, 2)}
    for i in range(inst.N):
        r = "BAD"[int(cls[i])]
        assert (int(inst.a[i]), int(inst.d[i])) == win[r]
        for t in range(2):
            assert int(inst.announced[i, t]) == int(win[r][0] <= t < win[r][1])
    caps = pe.caps(K, c, mode)
    L = np.asarray(inst.L)
    assert L.shape == (len(caps), 2)
    for g, (c0, c1) in caps.items():
        assert L[g, 0] == c0 and L[g, 1] == c1
    group = np.asarray(inst.group)
    if mode == pe.POOLED:
        assert np.all(group == 0)
    else:
        assert sorted(set(group.tolist())) == list(range(K))
        for g in range(K):
            assert sorted(cls[group == g].tolist()) == [0, 1, 2]  # {A_k, B_k, D_k}
    assert np.all(np.asarray(inst.b) == 0) and np.all(np.asarray(inst.b_mean) == 0)
    assert inst.cell.delta_A >= 2 and inst.cell.delta_b == 0
    A = np.asarray(inst.availability())
    assert np.all(A[cls != 1] == 1)  # B and D always available
    assert np.all(A[cls == 1, 1] == 1)  # A available at slot 1
    # the realized availability equals the enumerator's for the realized stuck pattern
    stuck = [int(s) for s in (A[cls == 1, 0] == 0)]
    av = pe.availability(stuck, K)
    for i_rank, i in enumerate(np.flatnonzero(cls == 1)):
        assert tuple(A[i]) == av[i_rank]
    ps = np.asarray(inst.prior_stuck)
    assert ps.shape == (inst.N, inst.cell.M)
    assert not ps[cls != 1].any()  # B and D never stuck in prior events
    assert np.all(np.asarray(inst.prior_A)[:, :, 0] == ~ps)
    assert np.all(np.asarray(inst.prior_A)[:, :, 1] == 1)
    assert np.allclose(np.asarray(inst.q)[cls == 1], inst.cell.q)
    assert np.all(np.asarray(inst.q)[cls != 1] == 0)


@pytest.mark.parametrize("K", KS)
def test_kcopy_structure_matches_enumerator(K):
    cells = cells_for_K(K)
    modes = {cl.cap_mode for cl in cells}
    assert modes == set(pe.CAP_MODES)
    per_copy_c = {int(cl.c) for cl in cells if cl.cap_mode == pe.PER_COPY}
    assert per_copy_c == {0, K, 2 * K}
    for cell in cells:
        for seed in SEEDS:
            check_structure(generate_kcopy(seed, cell, K), K, int(cell.c), cell.cap_mode)


@pytest.mark.parametrize("K", [1, 4, 8])
@pytest.mark.parametrize("q", [0.14, 0.40, 0.50])
def test_kcopy_stuck_frequencies(K, q):
    cell = next(cl for cl in cells_for_K(K) if cl.q == q and cl.M == 5 and cl.cap_mode == "pooled")
    n_seeds = 2000 // K
    s0 = n0 = sp = npr = 0
    # Seed rule: only seeds 60000-60049 may be used.  The ~2000 independent draws come from
    # 50 seeds x salted "scored_v"/"prior_v" child streams (the generator's test-only
    # stream_salt), i.e. additional parameter combinations, not additional seeds.
    for j in range(n_seeds):
        seed, salt = 60000 + j % 50, j // 50
        inst = generate_kcopy(seed, cell, K,
                              stream_salt={"scored_v": salt, "prior_v": salt} if salt else None)
        isA = np.asarray(inst.cls) == 1
        A = np.asarray(inst.availability())
        s0 += int((A[isA, 0] == 0).sum())
        n0 += int(isA.sum())
        ps = np.asarray(inst.prior_stuck)
        sp += int(ps[isA].sum())
        npr += ps[isA].size
    assert binomtest(s0, n0, q).pvalue > 1e-4
    assert binomtest(sp, npr, q).pvalue > 1e-4
