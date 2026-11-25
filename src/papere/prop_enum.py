"""Exhaustive exact enumerator for Propositions 1 and 3 and gap(c) on I_K (gate G1).

Everything here is brute force in exact rational arithmetic (``fractions.Fraction``,
or integers over a common denominator that are turned into Fractions). The closed
forms of MECHANISM_E_v2 Sections 3.5, 3.6 and 3.9 live in the ``closed_*`` functions
at the bottom of the module. No enumerated value is computed from a closed form; the
two are only compared afterwards (tests/test_prop_enum.py, scripts/g1_propositions.py).

Model (MECHANISM_E_v2 Section 3.6, BUILD_SPEC Section 5)
--------------------------------------------------------
I_K has K copies of (A, B, D); H = 2; P = E = 1. A and B have window [0, 2), D has
window [1, 2). A is available at slot 0 with probability 1 - q and at slot 1 always;
B and D are always available. Delivery is y_it = min(x_it, r_it) * A_it with r the
true remaining debt. With lag delta >= 2 nothing is observed before the horizon ends,
so every policy is a law over open-loop 0/1 schedules.

Participant order: A_0..A_{K-1}, B_0..B_{K-1}, D_0..D_{K-1}. "Twins" are the 2K
participants A_0..A_{K-1}, B_0..B_{K-1} (twin index j < K is A_j, j >= K is B_{j-K}).

Schedule code. A schedule sigma is encoded as an integer: twin j uses bits 2j (slot 0)
and 2j+1 (slot 1); D_k uses bit 4K + k (slot 1; D has no slot-0 option because its
window starts at slot 1, which prunes every schedule that would set x_{D,0} = 1).
A schedule is also given as a tuple of 3K rows (x_i0, x_i1).

Caps (setpoint semantics, sum of setpoints per slot):
  pooled   -- slot 0 cap 2K, slot 1 cap K + c;
  per_copy -- group k = {A_k, B_k, D_k}, slot 0 cap 2, slot 1 cap 1 + c/K (c/K integer).

Symmetry groups (policy classes)
--------------------------------
  Prop 1 pooled   : all permutations of the 2K twins (D rows fixed).
  Prop 1 per_copy : within-pair swaps A_k <-> B_k combined with permutations of whole
                    copies (k -> pi(k) moving A, B and D of a copy together).
  Prop 3          : the same groups restricted to maps that send every twin to a twin
                    with an equal observed history.
Orbits are computed from canonical forms (the lexicographically smallest image under
the group, obtained by sorting within the classes the group permutes freely), and
cross-checked in the tests against explicit enumeration of every group element.
"""

from __future__ import annotations

import itertools
import math
from dataclasses import dataclass
from fractions import Fraction
from functools import lru_cache
from typing import Iterable, Sequence

import numpy as np

POOLED = "pooled"
PER_COPY = "per_copy"
CAP_MODES = (POOLED, PER_COPY)

Row = tuple[int, int]
Schedule = tuple[Row, ...]


# ---------------------------------------------------------------------------
# Instance, schedules and caps
# ---------------------------------------------------------------------------


def n_participants(K: int) -> int:
    return 3 * K


def role(i: int, K: int) -> str:
    """Role letter of participant i in the order A_0..A_{K-1}, B_0.., D_0.."""
    return "ABD"[i // K]


def copy_of(i: int, K: int) -> int:
    return i % K


def windows(K: int) -> list[tuple[int, int]]:
    """Windows [a_i, d_i) in participant order (A, B: [0, 2); D: [1, 2))."""
    return [(0, 2)] * (2 * K) + [(1, 2)] * K


def caps(K: int, c: int, cap_mode: str) -> dict[int, tuple[int, int]]:
    """Slot caps per cap group. Pooled: {0: (2K, K + c)}. Per-copy: {k: (2, 1 + c/K)}."""
    if cap_mode == POOLED:
        return {0: (2 * K, K + c)}
    if cap_mode == PER_COPY:
        if c % K:
            raise ValueError("per-copy cap needs c/K integer")
        return {k: (2, 1 + c // K) for k in range(K)}
    raise ValueError(cap_mode)


def cap_group(i: int, K: int, cap_mode: str) -> int:
    return 0 if cap_mode == POOLED else copy_of(i, K)


def decode(code: int, K: int) -> Schedule:
    """Integer schedule code -> tuple of 3K rows (x_i0, x_i1)."""
    rows: list[Row] = []
    for j in range(2 * K):
        rows.append(((code >> (2 * j)) & 1, (code >> (2 * j + 1)) & 1))
    for k in range(K):
        rows.append((0, (code >> (4 * K + k)) & 1))
    return tuple(rows)


def encode(sigma: Sequence[Row], K: int) -> int:
    code = 0
    for j in range(2 * K):
        x0, x1 = sigma[j]
        code |= (x0 << (2 * j)) | (x1 << (2 * j + 1))
    for k in range(K):
        x0, x1 = sigma[2 * K + k]
        if x0:
            raise ValueError("D has no slot-0 option (window [1, 2))")
        code |= x1 << (4 * K + k)
    return code


def is_feasible(sigma: Sequence[Row], K: int, c: int, cap_mode: str) -> bool:
    """Window and setpoint-cap check of a schedule, participant by participant."""
    win = windows(K)
    for i, (x0, x1) in enumerate(sigma):
        for t, x in enumerate((x0, x1)):
            if x not in (0, 1):
                return False
            if x and not (win[i][0] <= t < win[i][1]):
                return False
    load: dict[tuple[int, int], int] = {}
    for i, row in enumerate(sigma):
        g = cap_group(i, K, cap_mode)
        for t in (0, 1):
            load[(g, t)] = load.get((g, t), 0) + row[t]
    for g, (c0, c1) in caps(K, c, cap_mode).items():
        if load.get((g, 0), 0) > c0 or load.get((g, 1), 0) > c1:
            return False
    return True


def schedules(K: int, c: int, cap_mode: str) -> list[Schedule]:
    """Every feasible open-loop 0/1 schedule of I_K (explicit list; small K only).

    Enumerated participant by participant with pruning: twins have 4 rows, D only the
    two rows with x_{D,0} = 0, and any partial schedule that already breaks a slot cap
    is dropped.
    """
    cap = caps(K, c, cap_mode)
    opts_twin: list[Row] = [(0, 0), (1, 0), (0, 1), (1, 1)]
    opts_d: list[Row] = [(0, 0), (0, 1)]
    out: list[Schedule] = []

    def rec(i: int, acc: list[Row], load: dict[tuple[int, int], int]) -> None:
        if i == 3 * K:
            out.append(tuple(acc))
            return
        g = cap_group(i, K, cap_mode)
        for row in opts_twin if i < 2 * K else opts_d:
            l0 = load.get((g, 0), 0) + row[0]
            l1 = load.get((g, 1), 0) + row[1]
            if l0 > cap[g][0] or l1 > cap[g][1]:
                continue
            load2 = dict(load)
            load2[(g, 0)], load2[(g, 1)] = l0, l1
            rec(i + 1, acc + [row], load2)

    rec(0, [], {})
    return out


def all_codes(K: int) -> np.ndarray:
    """Every window-feasible schedule code (caps not yet applied): 2^(5K) codes."""
    return np.arange(1 << (5 * K), dtype=np.int64)


def code_matrix(codes: np.ndarray, K: int) -> np.ndarray:
    """codes -> array x[S, 3K, 2] of 0/1 setpoints (same layout as ``decode``)."""
    S = codes.shape[0]
    x = np.zeros((S, 3 * K, 2), dtype=np.int64)
    for j in range(2 * K):
        x[:, j, 0] = (codes >> (2 * j)) & 1
        x[:, j, 1] = (codes >> (2 * j + 1)) & 1
    for k in range(K):
        x[:, 2 * K + k, 1] = (codes >> (4 * K + k)) & 1
    return x


def feasible_mask(x: np.ndarray, K: int, c: int, cap_mode: str) -> np.ndarray:
    """Boolean mask of schedules in x[S, 3K, 2] that respect the caps of (c, cap_mode)."""
    ok = np.ones(x.shape[0], dtype=bool)
    for g, (c0, c1) in caps(K, c, cap_mode).items():
        members = [i for i in range(3 * K) if cap_group(i, K, cap_mode) == g]
        ok &= x[:, members, 0].sum(axis=1) <= c0
        ok &= x[:, members, 1].sum(axis=1) <= c1
    return ok


# ---------------------------------------------------------------------------
# Realizations and delivery
# ---------------------------------------------------------------------------


def availability(stuck: Sequence[int], K: int) -> list[tuple[int, int]]:
    """A_it for a stuck pattern of the K A copies (stuck A: unavailable at slot 0)."""
    av = [(1 - s, 1) for s in stuck]
    av += [(1, 1)] * (2 * K)
    return av


def stuck_patterns(K: int, q: Fraction) -> list[tuple[tuple[int, ...], Fraction]]:
    """All 2^K stuck patterns of the A copies with their exact probabilities."""
    out = []
    for pat in itertools.product((0, 1), repeat=K):
        p = Fraction(1)
        for s in pat:
            p *= q if s else 1 - q
        out.append((pat, p))
    return out


def simulate_residual(sigma: Sequence[Row], stuck: Sequence[int], K: int) -> int:
    """Residual sum_i r_i at the horizon of schedule sigma in one realization.

    Delivery is simulated slot by slot: y_it = min(x_it, r_it) * A_it, r -= y.
    """
    av = availability(stuck, K)
    total = 0
    for i, row in enumerate(sigma):
        r = 1  # E_i
        for t in (0, 1):
            y = min(row[t], r) * av[i][t]
            r -= y
        total += r
    return total


def expected_residual(sigma: Sequence[Row], K: int, q: Fraction) -> Fraction:
    """E[R(sigma)]: exact average of ``simulate_residual`` over the 2^K stuck patterns."""
    return sum(
        (p * simulate_residual(sigma, pat, K) for pat, p in stuck_patterns(K, q)),
        Fraction(0),
    )


def residual_by_pattern(x: np.ndarray, K: int) -> tuple[list[tuple[int, ...]], np.ndarray]:
    """Vectorized ``simulate_residual``: R[p, S] for every stuck pattern p and schedule S."""
    pats = list(itertools.product((0, 1), repeat=K))
    out = np.zeros((len(pats), x.shape[0]), dtype=np.int64)
    for pi, pat in enumerate(pats):
        av = np.array(availability(pat, K), dtype=np.int64)  # [3K, 2]
        r = np.ones((x.shape[0], 3 * K), dtype=np.int64)
        for t in (0, 1):
            y = np.minimum(x[:, :, t], r) * av[None, :, t]
            r = r - y
        out[pi] = r.sum(axis=1)
    return pats, out


@dataclass
class ResidualTable:
    """E[R(sigma)] for every schedule code of I_K at one q, as integers over q_den^K.

    ``num[s] / den`` is the exact expected residual of schedule ``codes[s]``; ``den`` is
    the K-th power of q's denominator, so every pattern probability is an integer
    weight over ``den`` and the sum is exact.
    """

    K: int
    q: Fraction
    codes: np.ndarray
    x: np.ndarray
    num: np.ndarray
    den: int
    worst: np.ndarray  # max over realizations of R (int)
    best: np.ndarray  # min over realizations of R (int)

    def value(self, idx: int) -> Fraction:
        return Fraction(int(self.num[idx]), self.den)


@lru_cache(maxsize=None)
def _patterns_and_x(K: int):
    codes = all_codes(K)
    x = code_matrix(codes, K)
    pats, R = residual_by_pattern(x, K)
    return codes, x, pats, R


@lru_cache(maxsize=None)
def residual_table(K: int, q: Fraction) -> ResidualTable:
    """Exhaustive E[R] over all window-feasible schedules of I_K (see ``ResidualTable``)."""
    q = Fraction(q)
    codes, x, pats, R = _patterns_and_x(K)
    a, b = q.numerator, q.denominator
    num = np.zeros(codes.shape[0], dtype=np.int64)
    for pat, row in zip(pats, R):
        n = sum(pat)
        w = a**n * (b - a) ** (K - n)
        num += w * row
    return ResidualTable(K, q, codes, x, num, b**K, R.max(axis=0), R.min(axis=0))


# ---------------------------------------------------------------------------
# Orbits and optima
# ---------------------------------------------------------------------------


def _twin_codes(x: np.ndarray, K: int) -> np.ndarray:
    """Row code 0..3 (x0 + 2 x1) of every twin: array [S, 2K]."""
    return x[:, : 2 * K, 0] + 2 * x[:, : 2 * K, 1]


def canonical_keys(
    x: np.ndarray, K: int, cap_mode: str, classes: Sequence[int] | None = None
) -> np.ndarray:
    """Canonical orbit key of every schedule in x[S, 3K, 2] under the symmetry group.

    ``classes[j]`` is the observed-history class of twin j (None: all twins equal, the
    Proposition 1 group). The group is every map of twins that preserves the class and,
    for per-copy, the cap groups. The key is the encoded minimal image:
      pooled   -- multiset of (class, row) over twins, D rows in place;
      per_copy -- multiset over copies of (sorted pair of (class, row) of its twins,
                  D row), i.e. within-pair swaps of equal-class twins and permutations
                  of copies whose (class pair, rows) agree.
    """
    if classes is None:
        classes = [0] * (2 * K)
    cl = np.asarray(classes, dtype=np.int64)
    ncls = int(cl.max()) + 1
    base = 4 * ncls
    tw = cl[None, :] * 4 + _twin_codes(x, K)  # [S, 2K]
    dbits = x[:, 2 * K :, 1]  # [S, K]
    if cap_mode == POOLED:
        s = np.sort(tw, axis=1)
        key = np.zeros(x.shape[0], dtype=np.int64)
        for j in range(2 * K):
            key = key * base + s[:, j]
        for k in range(K):
            key = key * 2 + dbits[:, k]
        return key
    if cap_mode == PER_COPY:
        a_t, b_t = tw[:, :K], tw[:, K:]
        lo, hi = np.minimum(a_t, b_t), np.maximum(a_t, b_t)
        ck = (lo * base + hi) * 2 + dbits  # [S, K]
        ck = np.sort(ck, axis=1)
        cb = base * base * 2
        key = np.zeros(x.shape[0], dtype=np.int64)
        for k in range(K):
            key = key * cb + ck[:, k]
        return key
    raise ValueError(cap_mode)


def group_elements(K: int, cap_mode: str, classes: Sequence[int] | None = None):
    """Explicit list of the symmetry group as participant permutations (reference only).

    Each element is a tuple perm with perm[i] = image of participant i. Used by the tests
    to check ``canonical_keys`` against brute-force orbits.
    """
    if classes is None:
        classes = [0] * (2 * K)
    out = []
    if cap_mode == POOLED:
        for p in itertools.permutations(range(2 * K)):
            if all(classes[p[j]] == classes[j] for j in range(2 * K)):
                out.append(tuple(p) + tuple(range(2 * K, 3 * K)))
    else:
        for pi in itertools.permutations(range(K)):
            for sw in itertools.product((0, 1), repeat=K):
                perm = [0] * (3 * K)
                for k in range(K):
                    a_img, b_img = (pi[k], K + pi[k]) if not sw[k] else (K + pi[k], pi[k])
                    perm[k], perm[K + k], perm[2 * K + k] = a_img, b_img, 2 * K + pi[k]
                if all(classes[perm[j]] == classes[j] for j in range(2 * K)):
                    out.append(tuple(perm))
    return out


def apply_perm(sigma: Schedule, perm: Sequence[int]) -> Schedule:
    """Image of a schedule: participant i's row moves to participant perm[i]."""
    out: list[Row] = [(0, 0)] * len(sigma)
    for i, row in enumerate(sigma):
        out[perm[i]] = row
    return tuple(out)


@dataclass
class OrbitResult:
    value: Fraction  # min over orbits of the orbit-mean E[R]
    n_orbits: int
    n_schedules: int
    argmin_codes: list[int]  # the schedules of one minimizing orbit


@lru_cache(maxsize=None)
def _feasible_idx(K: int, c: int, cap_mode: str) -> np.ndarray:
    """Indices (into ``all_codes(K)``) of the schedules feasible under (c, cap_mode)."""
    _, x, _, _ = _patterns_and_x(K)
    return np.flatnonzero(feasible_mask(x, K, c, cap_mode))


@lru_cache(maxsize=24)
def _orbit_structure(K: int, c: int, cap_mode: str, classes: tuple[int, ...] | None):
    """Orbits of the feasible schedules: (indices sorted by canonical key, starts, counts).

    Independent of q, so one structure serves every q.
    """
    _, x, _, _ = _patterns_and_x(K)
    idx = _feasible_idx(K, c, cap_mode)
    keys = canonical_keys(x[idx], K, cap_mode, classes)
    order = np.argsort(keys, kind="stable")
    ks = keys[order]
    starts = np.flatnonzero(np.r_[True, ks[1:] != ks[:-1]])
    counts = np.diff(np.r_[starts, ks.shape[0]])
    return idx[order], starts, counts


def _orbit_min(tab: "ResidualTable", struct) -> OrbitResult:
    """Exact min over orbits of the orbit-mean E[R] (sum / count over orbit elements)."""
    sidx, starts, counts = struct
    sums = np.add.reduceat(tab.num[sidx], starts)
    # float pre-filter, then exact comparison among every orbit near the float minimum
    means = sums.astype(np.float64) / counts
    mn = means.min()
    cand = np.flatnonzero(means <= mn * (1 + 1e-9) + 1e-12)
    best: Fraction | None = None
    best_i = -1
    for i in cand.tolist():
        v = Fraction(int(sums[i]), int(counts[i]) * tab.den)
        if best is None or v < best:
            best, best_i = v, i
    lo = starts[best_i]
    hi = lo + counts[best_i]
    return OrbitResult(best, len(starts), int(sidx.shape[0]), tab.codes[sidx[lo:hi]].tolist())


_OPT_CACHE: dict = {}


def orbit_optimum(
    K: int, q: Fraction, c: int, cap_mode: str, classes: tuple[int, ...] | None = None,
    prefill_qs: Sequence[Fraction] | None = None,
) -> OrbitResult:
    """min over orbits of the (history-)symmetry group of the orbit-mean E[R].

    ``classes`` None is the Proposition 1 group. ``prefill_qs`` computes the same orbit
    structure for several q at once (a cache only; values are identical).
    """
    q = Fraction(q)
    key = (K, q, c, cap_mode, classes)
    if key not in _OPT_CACHE:
        struct = _orbit_structure(K, c, cap_mode, classes)
        for qq in {q, *map(Fraction, prefill_qs or ())}:
            k2 = (K, qq, c, cap_mode, classes)
            if k2 not in _OPT_CACHE:
                _OPT_CACHE[k2] = _orbit_min(residual_table(K, qq), struct)
    return _OPT_CACHE[key]


def _feasible(K: int, q: Fraction, c: int, cap_mode: str):
    tab = residual_table(K, Fraction(q))
    m = np.zeros(tab.codes.shape[0], dtype=bool)
    m[_feasible_idx(K, c, cap_mode)] = True
    return tab, m


def oblivious_optimum(K: int, q: Fraction, c: int, cap_mode: str) -> OrbitResult:
    """Prop 1 class optimum: min over twin-symmetric laws of E[R].

    Enumerates every feasible schedule, computes E[R] exactly by realization
    enumeration, groups schedules into orbits of the symmetry group (pooled: all twin
    permutations; per-copy: within-pair swaps x copy permutations) and returns the
    minimum orbit mean. An invariant law is a mixture of uniform-on-orbit laws, so this
    minimum is the class optimum.
    """
    return orbit_optimum(K, q, c, cap_mode, None)


def posterior_optimum(K: int, q: Fraction, c: int, cap_mode: str) -> Fraction:
    """Roles known: min over every feasible deterministic schedule of E[R]."""
    tab, m = _feasible(K, q, c, cap_mode)
    return Fraction(int(tab.num[m].min()), tab.den)


def hedge_all_A_schedule(K: int) -> Schedule:
    """'All twins at slot 0; all D copies and all A copies at slot 1'."""
    return tuple([(1, 1)] * K + [(1, 0)] * K + [(0, 1)] * K)


def law_value(law: Iterable[tuple[Schedule, Fraction]], K: int, q: Fraction) -> Fraction:
    """E[R] of a law over schedules, each schedule scored by ``expected_residual``."""
    tot_p, tot = Fraction(0), Fraction(0)
    for sigma, p in law:
        tot_p += p
        tot += p * expected_residual(sigma, K, q)
    if tot_p != 1:
        raise ValueError("law does not sum to 1")
    return tot


def law_realization_values(
    law: Iterable[tuple[Schedule, Fraction]], K: int
) -> dict[tuple[int, ...], Fraction]:
    """Per stuck pattern, the law-average realized residual."""
    law = list(law)
    out = {}
    for pat in itertools.product((0, 1), repeat=K):
        out[pat] = sum((p * simulate_residual(s, pat, K) for s, p in law), Fraction(0))
    return out


def deterministic_oblivious_worst(K: int, q: Fraction, c: int, cap_mode: str) -> Fraction:
    """min over deterministic schedules sigma of max over g in the group of E[R(g sigma)].

    A deterministic reliability-oblivious policy plays the same sigma on I_K and on
    every relabelled instance; its worst case over relabellings equals the max over the
    orbit of sigma on the fixed instance. Enumerated orbit by orbit.
    """
    tab, m = _feasible(K, q, c, cap_mode)
    keys = canonical_keys(tab.x[m], K, cap_mode)
    num = tab.num[m]
    order = np.argsort(keys, kind="stable")
    ks = keys[order]
    starts = np.flatnonzero(np.r_[True, ks[1:] != ks[:-1]])
    mx = np.maximum.reduceat(num[order], starts)
    return Fraction(int(mx.min()), tab.den)


def zero_residual_schedules(K: int, c: int, cap_mode: str) -> list[Schedule]:
    """Feasible schedules with R = 0 in every realization (by simulation)."""
    tab, m = _feasible(K, Fraction(1, 2), c, cap_mode)
    idx = np.flatnonzero(m & (tab.worst == 0))
    return [decode(int(tab.codes[i]), K) for i in idx]


def min_residual_any_realization(K: int, c: int, cap_mode: str, cap_override=None) -> int:
    """min over feasible schedules and realizations of R (for the headroom-margin row).

    ``cap_override`` = (slot-0 cap, slot-1 cap) of a pooled cap used instead of caps().
    """
    tab = residual_table(K, Fraction(1, 2))
    if cap_override is None:
        m = feasible_mask(tab.x, K, c, cap_mode)
    else:
        c0, c1 = cap_override
        m = (tab.x[:, :, 0].sum(axis=1) <= c0) & (tab.x[:, :, 1].sum(axis=1) <= c1)
    return int(tab.best[m].min())


def min_expected_with_caps(K: int, q: Fraction, c0: int, c1: int) -> Fraction:
    """min over schedules with pooled caps (c0, c1) of E[R] (any law; for margin rows)."""
    tab = residual_table(K, Fraction(q))
    m = (tab.x[:, :, 0].sum(axis=1) <= c0) & (tab.x[:, :, 1].sum(axis=1) <= c1)
    return Fraction(int(tab.num[m].min()), tab.den)


# ---------------------------------------------------------------------------
# Proposition 3: histories
# ---------------------------------------------------------------------------


def histories(K: int, M: int, q: Fraction, kind: str):
    """Exhaustive prior-event histories with exact probabilities.

    kind = "full": every A copy has a stuck sequence in {0,1}^M (2^(KM) histories);
    kind = "count": every A copy has a stuck count n in 0..M with prob C(M,n) q^n (1-q)^(M-n).
    B copies are never stuck, so their history is all zeros / count 0. Yields
    (twin_histories, probability) with twin_histories a tuple over the 2K twins.
    """
    q = Fraction(q)
    if kind == "full":
        per_copy = []
        for seq in itertools.product((0, 1), repeat=M):
            n = sum(seq)
            per_copy.append((seq, q**n * (1 - q) ** (M - n)))
        zero = tuple([0] * M)
    elif kind == "count":
        per_copy = [(n, math.comb(M, n) * q**n * (1 - q) ** (M - n)) for n in range(M + 1)]
        zero = 0
    else:
        raise ValueError(kind)
    for combo in itertools.product(per_copy, repeat=K):
        p = Fraction(1)
        for _, pk in combo:
            p *= pk
        hist = tuple(h for h, _ in combo) + tuple([zero] * K)
        yield hist, p


def history_classes(hist: Sequence) -> tuple[int, ...]:
    """Twins' equality classes of observed history, labelled by first appearance."""
    lab: dict = {}
    return tuple(lab.setdefault(h, len(lab)) for h in hist)


def identified(hist: Sequence, K: int) -> list[int]:
    """A copies with at least one past stuck outcome (the history differs from B's)."""
    zero = hist[K]  # B_0's history: never stuck
    return [k for k in range(K) if hist[k] != zero]


def history_class_optimum(
    K: int, q: Fraction, c: int, cap_mode: str, classes: tuple[int, ...],
    prefill_qs: Sequence[Fraction] | None = None,
) -> OrbitResult:
    """min over orbits of the history group of the orbit-mean E[R] given the true roles.

    The scored-event E[R(sigma)] is the realization enumeration of ``residual_table``
    (every A fails with probability q whatever its history). The value depends on the
    history only through the group, i.e. through ``classes``.
    """
    return orbit_optimum(K, q, c, cap_mode, tuple(classes), prefill_qs)


@dataclass
class HistoryResult:
    value: Fraction  # E over histories of the per-history class optimum
    by_identified: dict[int, Fraction]  # E[value | I = i]
    prob_identified: dict[int, Fraction]
    per_history_by_I: dict[int, set[Fraction]]  # distinct per-history optima for each I
    n_histories: int


def history_optimum(
    K: int, q: Fraction, M: int, cap_mode: str, kind: str,
    prefill_qs: Sequence[Fraction] | None = None,
) -> HistoryResult:
    """Prop 3 class optimum averaged exhaustively over histories (spare cap c = K).

    For every history (``histories``) with probability p: the per-history optimum is
    ``history_class_optimum`` for the history's equal-history group; the result is the
    p-weighted sum. Also returns E[. | I] by the number I of identified A copies.
    """
    q = Fraction(q)
    tot = Fraction(0)
    byI: dict[int, Fraction] = {}
    pI: dict[int, Fraction] = {}
    distinct: dict[int, set[Fraction]] = {}
    n = 0
    for hist, p in histories(K, M, q, kind):
        n += 1
        v = history_class_optimum(K, q, K, cap_mode, history_classes(hist), prefill_qs).value
        I = len(identified(hist, K))
        tot += p * v
        byI[I] = byI.get(I, Fraction(0)) + p * v
        pI[I] = pI.get(I, Fraction(0)) + p
        distinct.setdefault(I, set()).add(v)
    cond = {i: byI[i] / pI[i] for i in byI}
    return HistoryResult(tot, cond, pI, distinct, n)


def identified_first_law(hist: Sequence, K: int, cap_mode: str) -> list[tuple[Schedule, Fraction]]:
    """The e1 policy as an explicit law, spare cap c = K.

    All twins at slot 0, every D at slot 1, every identified A at slot 1; remaining
    slot-1 units go uniformly at random to unidentified twins: pooled -- a uniformly
    random (K - I)-subset of the 2K - I unidentified twins; per-copy -- in each
    unidentified copy one of its two twins, uniformly and independently.
    """
    ids = set(identified(hist, K))
    base = [[1, 0] for _ in range(2 * K)] + [[0, 1] for _ in range(K)]
    for k in ids:
        base[k][1] = 1
    law = []
    if cap_mode == POOLED:
        unid = [j for j in range(2 * K) if not (j < K and j in ids)]
        subsets = list(itertools.combinations(unid, K - len(ids)))
        for sub in subsets:
            rows = [list(r) for r in base]
            for j in sub:
                rows[j][1] = 1
            law.append((tuple(tuple(r) for r in rows), Fraction(1, len(subsets))))
    else:
        unid_copies = [k for k in range(K) if k not in ids]
        choices = list(itertools.product((0, 1), repeat=len(unid_copies)))
        for ch in choices:
            rows = [list(r) for r in base]
            for k, side in zip(unid_copies, ch):
                rows[k + side * K][1] = 1
            law.append((tuple(tuple(r) for r in rows), Fraction(1, len(choices))))
    return law


def identified_first_value(K: int, q: Fraction, M: int, cap_mode: str, kind: str):
    """E[R] of the e1 law, by enumeration over histories, laws and realizations.

    Returns (overall value, per-history list of (classes, value)) so that the per-history
    comparison with the class optimum can be made.
    """
    q = Fraction(q)
    tot = Fraction(0)
    per: dict[tuple[int, ...], Fraction] = {}
    cache: dict[tuple, Fraction] = {}
    for hist, p in histories(K, M, q, kind):
        key = tuple(identified(hist, K))
        if key not in cache:
            law = identified_first_law(hist, K, cap_mode)
            for sigma, _ in law:
                assert is_feasible(sigma, K, K, cap_mode)
            cache[key] = law_value(law, K, q)
        v = cache[key]
        tot += p * v
        per[history_classes(hist)] = v
    return tot, per


# ---------------------------------------------------------------------------
# Closed forms (MECHANISM_E_v2) -- used only for comparison
# ---------------------------------------------------------------------------


def closed_prop1(K: int, q: Fraction) -> Fraction:
    return Fraction(K) * Fraction(q) / 2


def closed_gap(K: int, q: Fraction, c: int) -> Fraction:
    q = Fraction(q)
    return q * c / 2 if c <= K else q * (K - Fraction(c, 2))


def closed_oblivious(K: int, q: Fraction, c: int) -> Fraction:
    """Symmetric rule: hedges c of 2K twins, covers c/2 A copies: q (K - c/2)."""
    return Fraction(q) * (K - Fraction(c, 2))


def closed_posterior(K: int, q: Fraction, c: int) -> Fraction:
    return Fraction(q) * max(0, K - c)


def f_identified(q: Fraction, M: int) -> Fraction:
    return 1 - (1 - Fraction(q)) ** M


def closed_prop3_per_copy(K: int, q: Fraction, M: int) -> Fraction:
    return K * Fraction(q) / 2 * (1 - f_identified(q, M))


def closed_prop3_pooled(K: int, q: Fraction, M: int) -> Fraction:
    q = Fraction(q)
    f = f_identified(q, M)
    a, d = f.numerator, f.denominator
    s = Fraction(0)
    for i in range(K + 1):
        s += Fraction(math.comb(K, i) * a**i * (d - a) ** (K - i) * (K - i), 2 * K - i)
    return q * K * s / d**K


def closed_prop3_pooled_given_I(K: int, q: Fraction, I: int) -> Fraction:
    return Fraction(q) * K * Fraction(K - I, 2 * K - I)


def closed_prop3_per_copy_given_I(K: int, q: Fraction, I: int) -> Fraction:
    return Fraction(q) * (K - I) / 2


def share(value: Fraction, K: int, q: Fraction) -> Fraction:
    """Share of the oblivious gap K q / 2 recovered: 1 - E[R] / (K q / 2)."""
    return 1 - value / (Fraction(K) * Fraction(q) / 2)
