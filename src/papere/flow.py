"""Clairvoyant flow bound for the Track E evaluator (BUILD_SPEC Sections 1, 2, 8).

Network on the realized instance (all capacities integer units):

    source -> i          capacity E_i
    i      -> (g(i), t)  capacity cap[i, t]   (= P_i * A_it inside the window, 0 outside)
    (g, t) -> T_t        capacity slot_cap[g, t]
    T_t    -> sink       unbounded, or a peak cap floor(Pi - sum_g base[g, t] + 1e-9)

Everything takes plain arrays (``FlowProblem``); this module does not import
``instance.py``.  The max-flow solver is a pure-Python Dinic on integer
capacities; ``networkx_max_flow`` is an independent cross-check.

Contents
--------
* ``max_flow``          F* and an integer delivery matrix y[N, H].
* ``leximin_flow``      exact integer leximin of the descending-sorted vector
                        s_i / E_i over integer maximum flows (see its docstring
                        for the algorithm and the proof sketch).
* ``min_peak_flow``     minimum peak among maximum flows, exact search over the
                        candidate values sum_g base[g, t] + k.
* ``clairvoyant``       everything above bundled as ``ClairvoyantResult``.
* ``is_feasible``, ``peak``, ``sorted_fractions``, ``is_leximin_local_optimum``:
                        checking helpers used by the tests and by ledger.py.
"""

from __future__ import annotations

import heapq
from collections import deque
from dataclasses import dataclass
from fractions import Fraction

import numpy as np

__all__ = [
    "FlowProblem",
    "ClairvoyantResult",
    "max_flow",
    "networkx_max_flow",
    "leximin_flow",
    "min_peak_flow",
    "clairvoyant",
    "is_feasible",
    "peak",
    "sorted_fractions",
    "is_leximin_local_optimum",
]

PEAK_EPS = 1e-9


# --------------------------------------------------------------------------- #
# Problem data
# --------------------------------------------------------------------------- #
def _whole(x, name: str) -> np.ndarray:
    """Cast to int64, refusing anything that is not a whole number within 1e-9.

    Silent truncation (2.9 -> 2) would change the instance, so it raises."""
    a = np.asarray(x)
    if a.dtype == np.bool_:
        a = a.astype(np.int64)
    if np.issubdtype(a.dtype, np.integer):
        return a.astype(np.int64)
    if not np.issubdtype(a.dtype, np.floating):
        raise ValueError(f"{name} must be numeric, got dtype {a.dtype}")
    if not np.isfinite(a).all():
        raise ValueError(f"{name} must be finite")
    r = np.round(a)
    if not np.allclose(a, r, rtol=0.0, atol=1e-9):
        raise ValueError(f"{name} must hold whole numbers")
    return r.astype(np.int64)


@dataclass
class FlowProblem:
    """Plain-array flow problem.

    E[N] int, cap[N, H] int (P_i * A_it inside the window, 0 outside; computed by
    the caller), group[N] int in 0..G-1, slot_cap[G, H] int, base[G, H] float
    (realized base load; used only for the peak).
    """

    E: np.ndarray
    cap: np.ndarray
    group: np.ndarray
    slot_cap: np.ndarray
    base: np.ndarray | None = None

    def __post_init__(self) -> None:
        self.E = _whole(self.E, "E").reshape(-1)
        self.cap = _whole(self.cap, "cap")
        self.group = _whole(self.group, "group").reshape(-1)
        self.slot_cap = _whole(self.slot_cap, "slot_cap")
        N = self.E.shape[0]
        if self.cap.ndim != 2 or self.cap.shape[0] != N:
            raise ValueError(f"cap must be [N, H] with N={N}, got {self.cap.shape}")
        H = self.cap.shape[1]
        if self.slot_cap.ndim != 2 or self.slot_cap.shape[1] != H:
            raise ValueError(f"slot_cap must be [G, H] with H={H}, got {self.slot_cap.shape}")
        G = self.slot_cap.shape[0]
        if self.base is None:
            self.base = np.zeros((G, H), dtype=np.float64)
        self.base = np.asarray(self.base, dtype=np.float64)
        if self.base.shape != (G, H):
            raise ValueError(f"base must be [G, H]={(G, H)}, got {self.base.shape}")
        if self.group.shape[0] != N:
            raise ValueError("group must have length N")
        if N and (self.group.min() < 0 or self.group.max() >= G):
            raise ValueError("group index out of range")
        if (self.E < 0).any() or (self.cap < 0).any() or (self.slot_cap < 0).any():
            raise ValueError("E, cap and slot_cap must be non-negative")

    @property
    def N(self) -> int:
        return int(self.E.shape[0])

    @property
    def H(self) -> int:
        return int(self.cap.shape[1])

    @property
    def G(self) -> int:
        return int(self.slot_cap.shape[0])


@dataclass
class ClairvoyantResult:
    F_star: int
    R_star: int
    s_own: np.ndarray  # [N] int
    R_couple: int
    y: np.ndarray  # [N, H] int, some maximum flow
    leximin_shortfall: np.ndarray  # [N] int, s_i = E_i - sum_t leximin_y[i, t]
    leximin_y: np.ndarray  # [N, H] int
    min_peak: float
    min_peak_y: np.ndarray  # [N, H] int; the "clairvoyant bound" policy row


# --------------------------------------------------------------------------- #
# Residual network and Dinic
# --------------------------------------------------------------------------- #
class _Net:
    """Adjacency-list residual network. Edge e and e ^ 1 are a forward/reverse pair."""

    __slots__ = ("n", "adj", "to", "cap")

    def __init__(self, n: int) -> None:
        self.n = n
        self.adj: list[list[int]] = [[] for _ in range(n)]
        self.to: list[int] = []
        self.cap: list[int] = []

    def add(self, u: int, v: int, c: int) -> int:
        e = len(self.to)
        self.to.append(v)
        self.cap.append(int(c))
        self.to.append(u)
        self.cap.append(0)
        self.adj[u].append(e)
        self.adj[v].append(e + 1)
        return e

    def flow(self, e: int) -> int:
        """Flow on forward edge e (reverse residual starts at 0)."""
        return self.cap[e ^ 1]

    def dinic(self, s: int, t: int) -> int:
        to, cap, adj, n = self.to, self.cap, self.adj, self.n
        total = 0
        while True:
            level = [-1] * n
            level[s] = 0
            q = deque([s])
            while q:
                u = q.popleft()
                lu = level[u] + 1
                for e in adj[u]:
                    v = to[e]
                    if cap[e] > 0 and level[v] < 0:
                        level[v] = lu
                        q.append(v)
            if level[t] < 0:
                return total
            it = [0] * n
            while True:  # augment along level-graph paths until blocked
                path: list[int] = []
                u = s
                while u != t:
                    au = adj[u]
                    i = it[u]
                    lu = level[u] + 1
                    while i < len(au):
                        e = au[i]
                        if cap[e] > 0 and level[to[e]] == lu:
                            break
                        i += 1
                    it[u] = i
                    if i < len(au):
                        e = au[i]
                        path.append(e)
                        u = to[e]
                    else:  # dead end: prune u, retreat
                        if u == s:
                            break
                        level[u] = -2
                        e = path.pop()
                        u = to[e ^ 1]
                        it[u] += 1
                if u != t:
                    break
                f = min(cap[e] for e in path)
                for e in path:
                    cap[e] -= f
                    cap[e ^ 1] += f
                total += f


class _Built:
    """Network for a FlowProblem with node and edge bookkeeping."""

    def __init__(self, p: FlowProblem, sink_cap: list[int] | None = None) -> None:
        N, H, G = p.N, p.H, p.G
        self.N, self.H, self.G = N, H, G
        self.src = 0
        self.part0 = 1
        self.gt0 = 1 + N
        self.T0 = 1 + N + G * H
        self.sink = 1 + N + G * H + H
        net = _Net(self.sink + 1)
        big = int(p.E.sum()) + 1
        self.src_edge = [net.add(self.src, self.part0 + i, int(p.E[i])) for i in range(N)]
        self.eid = [[-1] * H for _ in range(N)]
        cap = p.cap.tolist()
        grp = p.group.tolist()
        for i in range(N):
            g = grp[i]
            row = cap[i]
            for t in range(H):
                if row[t] > 0:
                    self.eid[i][t] = net.add(self.part0 + i, self.gt0 + g * H + t, row[t])
        sc = p.slot_cap.tolist()
        self.gt_edge = [[-1] * H for _ in range(G)]
        for g in range(G):
            for t in range(H):
                if sc[g][t] > 0:
                    self.gt_edge[g][t] = net.add(self.gt0 + g * H + t, self.T0 + t, sc[g][t])
        self.T_edge = [-1] * H
        for t in range(H):
            c = big if sink_cap is None else max(0, int(sink_cap[t]))
            if c > 0:
                self.T_edge[t] = net.add(self.T0 + t, self.sink, c)
        self.net = net
        self.group = grp

    def load(self, y: np.ndarray) -> None:
        """Push a feasible integer flow y (from zero) into the residual network."""
        cap = self.net.cap

        def push(e: int, f: int) -> None:
            if e < 0 or cap[e] < f:
                raise ValueError("flow does not fit the network")
            cap[e] -= f
            cap[e ^ 1] += f

        for i in range(self.N):
            g = self.group[i]
            row = [int(v) for v in y[i]]
            for t in range(self.H):
                f = row[t]
                if f > 0:
                    push(self.eid[i][t], f)
                    push(self.gt_edge[g][t], f)
                    push(self.T_edge[t], f)
            if sum(row) > 0:
                push(self.src_edge[i], sum(row))

    def y(self) -> np.ndarray:
        y = np.zeros((self.N, self.H), dtype=np.int64)
        for i in range(self.N):
            for t in range(self.H):
                e = self.eid[i][t]
                if e >= 0:
                    y[i, t] = self.net.flow(e)
        return y


# --------------------------------------------------------------------------- #
# Max flow
# --------------------------------------------------------------------------- #
def max_flow(problem: FlowProblem, sink_cap: list[int] | None = None) -> tuple[int, np.ndarray]:
    """Integer maximum flow (Dinic). Returns (F*, y[N, H] int64).

    ``sink_cap`` optionally caps T_t -> sink (used by the peak search)."""
    b = _Built(problem, sink_cap)
    F = b.net.dinic(b.src, b.sink)
    return int(F), b.y()


def networkx_max_flow(problem: FlowProblem) -> tuple[int, np.ndarray]:
    """Cross-check: same network solved by networkx.maximum_flow."""
    import networkx as nx

    p = problem
    N, H, G = p.N, p.H, p.G
    D = nx.DiGraph()
    D.add_node("s")
    D.add_node("z")
    for i in range(N):
        D.add_edge("s", ("i", i), capacity=int(p.E[i]))
        g = int(p.group[i])
        for t in range(H):
            if p.cap[i, t] > 0:
                D.add_edge(("i", i), ("gt", g, t), capacity=int(p.cap[i, t]))
    for g in range(G):
        for t in range(H):
            if p.slot_cap[g, t] > 0:
                D.add_edge(("gt", g, t), ("T", t), capacity=int(p.slot_cap[g, t]))
    for t in range(H):
        D.add_edge(("T", t), "z")  # no capacity attribute = unbounded
    F, fd = nx.maximum_flow(D, "s", "z")
    y = np.zeros((N, H), dtype=np.int64)
    for i in range(N):
        for (kind, *rest), f in fd.get(("i", i), {}).items():
            if kind == "gt":
                y[i, rest[1]] = int(round(f))
    return int(round(F)), y


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def is_feasible(problem: FlowProblem, y: np.ndarray) -> bool:
    """Integer, 0 <= y <= cap, row sums <= E, group-slot sums <= slot_cap."""
    p = problem
    y = np.asarray(y)
    if y.shape != (p.N, p.H) or not np.issubdtype(y.dtype, np.integer):
        return False
    if (y < 0).any() or (y > p.cap).any() or (y.sum(axis=1) > p.E).any():
        return False
    load = np.zeros((p.G, p.H), dtype=np.int64)
    np.add.at(load, p.group, y)
    return bool((load <= p.slot_cap).all())


def peak(problem: FlowProblem, y: np.ndarray) -> float:
    """max_t sum_g (base[g, t] + sum_{i in g} y_it)."""
    p = problem
    if p.H == 0:
        return 0.0
    tot = p.base.sum(axis=0) + np.asarray(y).sum(axis=0)
    return float(tot.max())


def _frac(s: int, E: int) -> Fraction:
    return Fraction(int(s), int(E)) if E > 0 else Fraction(0)


def sorted_fractions(E: np.ndarray, shortfall: np.ndarray) -> tuple[Fraction, ...]:
    """Descending-sorted vector of s_i / E_i as exact Fractions (E_i = 0 gives 0)."""
    return tuple(sorted((_frac(s, e) for s, e in zip(shortfall.tolist(), E.tolist())), reverse=True))


# --------------------------------------------------------------------------- #
# Leximin
# --------------------------------------------------------------------------- #
def _key(s: int, E: int) -> tuple[Fraction, Fraction]:
    """Greedy priority of giving participant one more unit (larger = first).

    (s/E, -(s-1)/E) compared lexicographically; see ``leximin_flow``."""
    return (Fraction(s, E), -Fraction(s - 1, E))


def _bfs_path(b: _Built, start: int) -> list[int] | None:
    """Shortest residual path start -> sink avoiding the source; list of edges."""
    net = b.net
    to, cap, adj = net.to, net.cap, net.adj
    sink, src = b.sink, b.src
    par = [-1] * net.n
    seen = [False] * net.n
    seen[start] = True
    seen[src] = True
    q = deque([start])
    while q:
        u = q.popleft()
        for e in adj[u]:
            if cap[e] > 0:
                v = to[e]
                if not seen[v]:
                    seen[v] = True
                    par[v] = e
                    if v == sink:
                        path = []
                        while v != start:
                            e2 = par[v]
                            path.append(e2)
                            v = to[e2 ^ 1]
                        return path
                    q.append(v)
    return None


def leximin_flow(problem: FlowProblem) -> np.ndarray:
    """Exact integer leximin over integer maximum flows. Returns y[N, H] int64.

    Objective: lexicographically minimize the descending-sorted vector of
    shortfall fractions s_i / E_i, s_i = E_i - z_i, z_i = sum_t y_it, over all
    INTEGER maximum flows y.

    Algorithm (greedy unit augmentation, Federgruen-Groenevelt):
      start from the zero flow; repeatedly take the participant i with the
      largest key (s_i/E_i, -(s_i-1)/E_i) (lexicographic, exact Fractions) and
      push one more unit source -> i -> ... -> sink along a residual path that
      avoids the source; if no such path exists, i is saturated for good and is
      dropped. Stop when every participant is satisfied or dropped. Units are
      pushed in batches only while i stays the top key, so the order is that of
      the unit greedy with some tie-breaking.

    Proof sketch.
      (1) Delivery vectors. Z = {z in Z^N : z is the source-edge flow of some
      integer flow} is the integer point set of the integral polymatroid with
      rank r(S) = max flow out of S (network-flow polymatroid; integrality of
      flows with integer capacities). Integer maximum flows are exactly its
      integer bases.
      (2) Encoding. Let v_1 < ... < v_m be the distinct values of
      (E_i - z)/E_i over all i and all z in 0..E_i (every attainable shortfall
      fraction), fixed before the algorithm runs, and Phi(v_k) = B^k with
      B = N + 2. The ranks never depend on the current flow. Comparing descending-sorted vectors
      lexicographically = comparing count vectors from the top = comparing
      sum_i Phi(s_i/E_i) (base-B digits, counts <= N < B). For each i the map
      z_i -> Phi((E_i - z_i)/E_i) is discretely convex: consecutive values sit
      at strictly increasing ranks, and B^{r+1} - B^r >= (B-1) B^r > B^r - B^{r'}
      for r' < r. So leximin = minimizing a separable convex function over the
      integer bases of an integral polymatroid.
      (3) Greedy. For separable concave maximization over an integral
      polymatroid the unit greedy (always add a unit to a feasible coordinate
      of largest marginal gain; a coordinate that becomes infeasible stays
      infeasible) is optimal (Federgruen & Groenevelt, Oper. Res. 1986). Here
      every gain is positive, so greedy ends at a base (a max flow). The gain of
      i is B^{r(s_i/E_i)} - B^{r((s_i-1)/E_i)}; with B >= 3 it orders exactly as
      the key above (larger current fraction first; at equal current fraction
      the smaller next fraction first; equal keys mean equal E and s, equal gain).
      (4) Augmentation. z + e_i is feasible iff the residual graph has a path
      i -> sink avoiding the source (decompose the difference of two flows).
    The result is certified independently by ``is_leximin_local_optimum``
    (Murota: an M-convex function is minimized iff no improving unit exchange
    z + e_i - e_j exists) and checked against brute force in the tests.
    """
    p = problem
    b = _Built(p)
    net = b.net
    E = p.E.tolist()
    s = list(E)
    heap: list[tuple[Fraction, Fraction, int]] = []
    for i in range(p.N):
        if E[i] > 0:
            k = _key(E[i], E[i])
            heap.append((-k[0], -k[1], i))
    heapq.heapify(heap)
    while heap:
        _, _, i = heapq.heappop(heap)
        path = _bfs_path(b, b.part0 + i)
        if path is None:
            continue  # saturated forever (polymatroid monotonicity)
        # units i may take while it remains a top key
        if heap:
            nxt = (-heap[0][0], -heap[0][1])
            m = 0
            while s[i] - m > 0 and _key(s[i] - m, E[i]) >= nxt:
                m += 1
        else:
            m = s[i]
        f = min([m, s[i]] + [net.cap[e] for e in path])
        se = b.src_edge[i]
        net.cap[se] -= f
        net.cap[se ^ 1] += f
        for e in path:
            net.cap[e] -= f
            net.cap[e ^ 1] += f
        s[i] -= f
        if s[i] > 0:
            k = _key(s[i], E[i])
            heapq.heappush(heap, (-k[0], -k[1], i))
    return b.y()


def _pair_improves(si: int, Ei: int, sj: int, Ej: int) -> bool:
    """Is {(s_i-1)/E_i, (s_j+1)/E_j} lexicographically smaller (descending) than
    {s_i/E_i, s_j/E_j}? Moving one unit of delivery from j to i."""
    old = sorted((Fraction(si, Ei), Fraction(sj, Ej)), reverse=True)
    new = sorted((Fraction(si - 1, Ei), Fraction(sj + 1, Ej)), reverse=True)
    return new < old


def is_leximin_local_optimum(problem: FlowProblem, y: np.ndarray) -> bool:
    """Certificate: y is a max flow and no improving unit exchange exists.

    For participants i (s_i > 0) and j (z_j > 0, E_j > 0), the exchange
    z + e_i - e_j is feasible iff the residual graph of y has a path i ~> j
    avoiding the source. It improves iff the two changed entries improve as a
    pair (``_pair_improves``). Note the naive test s_i/E_i > (s_j+1)/E_j is
    NOT sufficient: with s_i/E_i == (s_j+1)/E_j the exchange still improves when
    (s_i-1)/E_i < s_j/E_j (e.g. 1/2,1/4 -> 0,1/2)."""
    p = problem
    F, _ = max_flow(p)
    if int(np.asarray(y).sum()) != F or not is_feasible(p, y):
        return False
    b = _Built(p)
    b.load(np.asarray(y))
    net = b.net
    z = np.asarray(y).sum(axis=1)
    s = p.E - z
    for i in range(p.N):
        if s[i] <= 0:
            continue
        # reachability from i avoiding the source
        seen = [False] * net.n
        seen[b.src] = True
        seen[b.part0 + i] = True
        q = deque([b.part0 + i])
        while q:
            u = q.popleft()
            for e in net.adj[u]:
                if net.cap[e] > 0 and not seen[net.to[e]]:
                    seen[net.to[e]] = True
                    q.append(net.to[e])
        for j in range(p.N):
            if j != i and seen[b.part0 + j] and z[j] > 0 and p.E[j] > 0:
                if _pair_improves(int(s[i]), int(p.E[i]), int(s[j]), int(p.E[j])):
                    return False
    return True


# --------------------------------------------------------------------------- #
# Minimum peak among maximum flows
# --------------------------------------------------------------------------- #
def _sink_caps(base_tot: np.ndarray, Pi: float) -> list[int]:
    return [max(0, int(np.floor(Pi - bt + PEAK_EPS))) for bt in base_tot.tolist()]


def min_peak_flow(problem: FlowProblem, F_star: int | None = None) -> tuple[float, np.ndarray]:
    """Smallest Pi such that T_t -> sink capped at floor(Pi - sum_g base[g,t] + 1e-9)
    (clipped at 0) still carries F*. Returns (peak of the returned flow, y).

    The optimal peak equals sum_g base[g, t*] + k for some slot t* and integer
    k >= 0, and feasibility is monotone in Pi, so a binary search over the
    sorted candidate set {sum_g base[g, s] + k : s, 0 <= k <= K} (K = max slot
    throughput) restricted to Pi >= max_t sum_g base[g, t] is exact.

    Tolerance. Caps use floor(Pi - b_t + 1e-9) with b_t = sum_g base[g, t], so a
    returned flow has load_t <= Pi - b_t + 1e-9, i.e. peak <= Pi + 1e-9, and the
    candidate equal to the true optimum is always feasible. The search is
    exact unless two slot base totals have fractional parts that differ by a
    nonzero amount of at most 1e-9 (impossible for base loads stated to fewer
    than nine decimal places); in that case it can return a peak above the
    optimum by at most 1e-9. The returned value is the peak of the returned
    flow, computed directly, not the candidate Pi."""
    p = problem
    if F_star is None:
        F_star, _ = max_flow(p)
    if p.H == 0:
        return 0.0, np.zeros((p.N, 0), dtype=np.int64)
    bt = p.base.sum(axis=0)
    K = int(min(int(p.E.sum()), int(p.slot_cap.sum(axis=0).max())))
    lo_bound = float(bt.max())
    cands = sorted({float(bt[s]) + k for s in range(p.H) for k in range(K + 1)})
    cands = [c for c in cands if c >= lo_bound - PEAK_EPS]
    lo, hi = 0, len(cands) - 1
    best: tuple[int, np.ndarray] | None = None
    # cands[-1] is always feasible: every T_t cap >= that slot's throughput
    while lo < hi:
        mid = (lo + hi) // 2
        F, y = max_flow(p, _sink_caps(bt, cands[mid]))
        if F == F_star:
            hi = mid
            best = (mid, y)
        else:
            lo = mid + 1
    if best is None or best[0] != lo:
        F, y = max_flow(p, _sink_caps(bt, cands[lo]))
        if F != F_star:
            raise AssertionError("peak search: largest candidate infeasible")
        best = (lo, y)
    return peak(p, best[1]), best[1]


# --------------------------------------------------------------------------- #
# Bundle
# --------------------------------------------------------------------------- #
def clairvoyant(problem: FlowProblem) -> ClairvoyantResult:
    p = problem
    F, y = max_flow(p)
    E_tot = int(p.E.sum())
    s_own = np.maximum(0, p.E - p.cap.sum(axis=1)).astype(np.int64)
    R = E_tot - F
    ly = leximin_flow(p)
    assert int(ly.sum()) == F, "leximin flow is not maximum"
    mp, my = min_peak_flow(p, F)
    return ClairvoyantResult(
        F_star=int(F),
        R_star=int(R),
        s_own=s_own,
        R_couple=int(R - int(s_own.sum())),
        y=y,
        leximin_shortfall=(p.E - ly.sum(axis=1)).astype(np.int64),
        leximin_y=ly,
        min_peak=float(mp),
        min_peak_y=my,
    )
