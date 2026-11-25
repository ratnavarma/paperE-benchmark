"""Exhaustive enumerators for gate G1 (PLAN Section 8, OPEN_QUESTIONS rows 9-10).

Part 1 (this file, now): ``brute_force`` — clairvoyant quantities for small
instances (N <= 4, H <= 4) by exhaustive enumeration of integer delivery
matrices, with no flow theory. ``brute_force_naive`` is a plain DFS over every
matrix (no merging) used to cross-check ``brute_force`` on the smallest cases.

Part 2 (later task): the proposition enumerator for Propositions 1 and 3 on
small I_K. See the placeholder section at the end of the file.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass
from fractions import Fraction

import numpy as np

from papere.flow import FlowProblem

__all__ = [
    "BruteForceResult",
    "brute_force",
    "brute_force_naive",
    "random_problem",
    "random_battery",
    "grid_problems",
]

BF_MAX_N = 4
BF_MAX_H = 4


@dataclass
class BruteForceResult:
    F_star: int
    leximin_sorted: tuple[Fraction, ...]  # descending s_i/E_i, lexicographic minimum over max flows
    min_peak: float  # minimum over max-flow matrices of max_t sum_g (base + load)
    max_flow_z: frozenset[tuple[int, ...]]  # every delivery vector z of a max-flow matrix
    n_states: int  # distinct final (z, load) states reached


def _rows(cap_row: list[int], E: int) -> list[tuple[int, ...]]:
    """Every integer row 0 <= r_t <= cap_t with sum r <= E."""
    out = []
    for r in itertools.product(*(range(c + 1) for c in cap_row)):
        if sum(r) <= E:
            out.append(r)
    return out


def _sorted_fracs(E: list[int], z: tuple[int, ...]) -> tuple[Fraction, ...]:
    return tuple(
        sorted(((Fraction(e - zi, e) if e > 0 else Fraction(0)) for e, zi in zip(E, z)), reverse=True)
    )


def _peak(base_tot: list[float], load_by_t: list[int]) -> float:
    if not base_tot:
        return 0.0
    return float(max(np.asarray(base_tot) + np.asarray(load_by_t, dtype=np.int64)))


def _check_small(p: FlowProblem) -> None:
    if p.N > BF_MAX_N or p.H > BF_MAX_H:
        raise ValueError(f"brute force is for N <= {BF_MAX_N}, H <= {BF_MAX_H}")


def brute_force(problem: FlowProblem) -> BruteForceResult:
    """Exhaustive clairvoyant quantities for N <= 4, H <= 4.

    Every integer delivery matrix y with 0 <= y_it <= cap_it, sum_t y_it <= E_i
    and group slot caps sum_{i in g} y_it <= slot_cap[g, t] is generated, row by
    row (participant by participant; every row vector of participant i is
    tried against every partial matrix). Partial matrices are merged when they
    agree on (z_1..z_k, group-slot load matrix): every later feasibility test
    and every objective (F = sum z, the shortfall vector, the peak) depends on
    the partial matrix only through that pair, so merging loses no reachable
    final (z, load) pair. A branch is cut only when even its trivial upper
    bound (current total + sum over remaining participants of
    min(E_i, sum_t cap_it)) is below F*, which itself comes from a first
    exhaustive pass over load matrices. Nothing uses flow theory."""
    p = problem
    _check_small(p)
    N, H, G = p.N, p.H, p.G
    E = p.E.tolist()
    cap = p.cap.tolist()
    grp = p.group.tolist()
    sc = [v for row in p.slot_cap.tolist() for v in row]  # flat (g, t)
    rows = [_rows(cap[i], E[i]) for i in range(N)]

    def add(load: tuple[int, ...], g: int, r: tuple[int, ...]) -> tuple[int, ...] | None:
        new = list(load)
        off = g * H
        for t in range(H):
            v = new[off + t] + r[t]
            if v > sc[off + t]:
                return None
            new[off + t] = v
        return tuple(new)

    # Pass 1: reachable group-slot load matrices -> F* = max total load.
    loads = {tuple([0] * (G * H))}
    for i in range(N):
        nxt = set()
        for L in loads:
            for r in rows[i]:
                L2 = add(L, grp[i], r)
                if L2 is not None:
                    nxt.add(L2)
        loads = nxt
    F_star = max(sum(L) for L in loads)

    # Pass 2: (z prefix, load) states, cut by the trivial bound.
    rem = [0] * (N + 1)
    for i in range(N - 1, -1, -1):
        rem[i] = rem[i + 1] + min(E[i], sum(cap[i]))
    states = {((), tuple([0] * (G * H)))}
    for i in range(N):
        nxt = set()
        for z, L in states:
            base_total = sum(L)
            for r in rows[i]:
                if base_total + sum(r) + rem[i + 1] < F_star:
                    continue
                L2 = add(L, grp[i], r)
                if L2 is not None:
                    nxt.add((z + (sum(r),), L2))
        states = nxt
    finals = [(z, L) for z, L in states if sum(z) == F_star]
    zs = frozenset(z for z, _ in finals)
    lex = min(_sorted_fracs(E, z) for z in zs)
    base_tot = p.base.sum(axis=0).tolist()
    best_peak = min(
        _peak(base_tot, [sum(L[g * H + t] for g in range(G)) for t in range(H)]) for _, L in finals
    )
    return BruteForceResult(
        F_star=int(F_star), leximin_sorted=lex, min_peak=best_peak, max_flow_z=zs, n_states=len(states)
    )


def brute_force_naive(problem: FlowProblem, limit: int = 2_000_000) -> BruteForceResult:
    """Plain DFS over every feasible delivery matrix, no merging (cross-check).

    Raises if more than ``limit`` complete matrices would be visited."""
    p = problem
    _check_small(p)
    N, H, G = p.N, p.H, p.G
    E = p.E.tolist()
    cap = p.cap.tolist()
    grp = p.group.tolist()
    rows = [_rows(cap[i], E[i]) for i in range(N)]
    base_tot = p.base.sum(axis=0).tolist()
    load = [[0] * H for _ in range(G)]
    sc = p.slot_cap.tolist()
    z = [0] * N
    best = {"F": -1, "lex": None, "peak": None, "zs": set(), "count": 0}

    def rec(i: int) -> None:
        if i == N:
            best["count"] += 1
            if best["count"] > limit:
                raise RuntimeError("naive enumeration limit exceeded")
            F = sum(z)
            lt = [sum(load[g][t] for g in range(G)) for t in range(H)]
            pk = _peak(base_tot, lt)
            lx = _sorted_fracs(E, tuple(z))
            if F > best["F"]:
                best.update(F=F, lex=lx, peak=pk, zs={tuple(z)})
            elif F == best["F"]:
                best["lex"] = min(best["lex"], lx)
                best["peak"] = min(best["peak"], pk)
                best["zs"].add(tuple(z))
            return
        g = grp[i]
        for r in rows[i]:
            if all(load[g][t] + r[t] <= sc[g][t] for t in range(H)):
                for t in range(H):
                    load[g][t] += r[t]
                z[i] = sum(r)
                rec(i + 1)
                for t in range(H):
                    load[g][t] -= r[t]
        z[i] = 0

    rec(0)
    return BruteForceResult(
        F_star=int(best["F"]),
        leximin_sorted=best["lex"],
        min_peak=float(best["peak"]),
        max_flow_z=frozenset(best["zs"]),
        n_states=best["count"],
    )


# --------------------------------------------------------------------------- #
# Instance batteries for G1 (OPEN_QUESTIONS row 9): a systematic grid and a
# seeded random battery, all N <= 4, H <= 4.
# --------------------------------------------------------------------------- #
def _cap_from(P: list[int], A: np.ndarray, a: list[int], d: list[int], H: int) -> np.ndarray:
    cap = np.zeros((len(P), H), dtype=np.int64)
    for i in range(len(P)):
        for t in range(a[i], d[i]):
            cap[i, t] = P[i] * int(A[i, t])
    return cap


def random_problem(rng: np.random.Generator, max_N: int = BF_MAX_N, max_H: int = BF_MAX_H) -> FlowProblem:
    """One random small instance: windows, availability, P in {1,2,3},
    E in {1..6}, G in {1,2,3}, slot caps 0..4, non-integer base loads.

    Half the draws use a loose sub-profile (E in {1..3}, slot caps 2..4) so the
    peak search has room to move; the other half the full box."""
    N = int(rng.integers(1, max_N + 1))
    H = int(rng.integers(1, max_H + 1))
    G = int(rng.integers(1, 4))
    loose = bool(rng.random() < 0.5)
    P = rng.integers(1, 4, size=N).tolist()
    E = rng.integers(1, 4 if loose else 7, size=N)
    a = rng.integers(0, H, size=N).tolist()
    d = [int(rng.integers(a[i] + 1, H + 1)) for i in range(N)]
    p_av = float(rng.choice([0.5, 0.8, 1.0]))
    A = (rng.random((N, H)) < p_av).astype(np.int64)
    cap = _cap_from(P, A, a, d, H)
    group = rng.integers(0, G, size=N)
    slot_cap = rng.integers(2 if loose else 0, 5, size=(G, H))
    base = np.round(rng.uniform(0.0, 4.0, size=(G, H)), 3) + 0.125
    return FlowProblem(E=E, cap=cap, group=group, slot_cap=slot_cap, base=base)


def random_battery(n: int, seed: int) -> list[FlowProblem]:
    rng = np.random.default_rng(np.random.SeedSequence(seed))
    return [random_problem(rng) for _ in range(n)]


def _slot_pattern(totals: tuple[float, float]):
    """Base matrix [G, H] whose slot totals sum_g base[g, t] are totals[t],
    split unevenly (0.625 / 0.375) when G = 2."""

    def f(G: int, H: int) -> np.ndarray:
        w = np.array([1.0]) if G == 1 else np.array([0.625, 0.375])
        return np.outer(w, np.array(totals[:H], dtype=np.float64))

    return f


_GRID_BASES = (
    _slot_pattern((0.25, 0.75)),  # differ by 0.5
    _slot_pattern((2.25, 0.5)),  # differ by integer + fraction (1.75), high first
    _slot_pattern((0.5, 1.75)),  # differ by 1.25, low first
    _slot_pattern((1.5, 3.5)),  # differ by an exact integer
    _slot_pattern((0.125, 1.0625)),  # differ by 0.9375
)


def grid_problems(full: bool = False):
    """Systematic grid over every N <= 2, H <= 2 instance in a bounded box.

    Per participant: P in Ps, availability/window mask in {0,1}^H (cap = P*mask),
    E in Es. G = 1 with slot caps in SC1^H; G = 2 (participants in distinct
    groups when N = 2) with slot caps in SC2^(2H). Base load cycles through
    ``_GRID_BASES``, whose slot base totals differ by integer + fraction (in
    either direction), by an exact integer, by a fraction and by a fraction near
    1, so peak-rounding errors show up on the grid alone."""
    Ps = (1, 2, 3) if full else (1, 3)
    Es = (1, 2, 3, 4) if full else (1, 2, 4)
    SC1 = (0, 1, 2, 3, 4) if full else (0, 1, 2, 3)
    SC2 = (0, 1, 2) if full else (0, 2)
    counter = itertools.count()
    for N in (1, 2):
        for H in (1, 2):
            masks = list(itertools.product((0, 1), repeat=H))
            per = list(itertools.product(Ps, masks, Es))
            for parts in itertools.product(per, repeat=N):
                E = np.array([e for _, _, e in parts])
                cap = np.array([[P * m for m in mask] for P, mask, _ in parts], dtype=np.int64)
                for G, SC in ((1, SC1), (2, SC2)):
                    group = np.array([0] * N) if G == 1 else np.arange(N) % 2
                    for scs in itertools.product(SC, repeat=G * H):
                        slot_cap = np.array(scs, dtype=np.int64).reshape(G, H)
                        base = _GRID_BASES[next(counter) % len(_GRID_BASES)](G, H)
                        yield FlowProblem(E=E, cap=cap, group=group, slot_cap=slot_cap, base=base)


# --------------------------------------------------------------------------- #
# Part 2 (later task): proposition enumerator for gate G1.
# Reproduce Propositions 1 and 3 of MECHANISM_E_v2 exactly on small I_K.
# --------------------------------------------------------------------------- #
