"""Instance generators: F0-R (and SCALE) and the K-copy family (BUILD_SPEC 4, 5).

Seeding: each component draws from its own named child stream of
``SeedSequence(seed)``, so changing a cell never shifts another component's
draws. Within a seed, participants, classes, uniforms and base-load noise are
identical across all cells (common random numbers). The first ``M`` of
``M_MAX = 5`` prior events are used by a cell with ``M`` prior events.
"""
from __future__ import annotations

import hashlib
from dataclasses import replace

import numpy as np

from .instance import (Cell, Instance, chain_availability, iid_availability,
                       kcopy_availability)

M_MAX = 5
H_F0R = 24
Q_INTOLERANT = 0.40
Q_TOLERANT = 0.01
Q_HOMOGENEOUS = 0.14
AR_COEF = 0.7
BASE_RAMP = 0.15
BASE_SD = 0.03

# Stable component ids (never reorder or reuse).
_STREAM_IDS = {
    "P": 1, "E": 2, "a": 3, "slack": 4,
    "class": 5,
    "prior_v": 6, "prior_u": 7,
    "scored_v": 8, "scored_u": 9,
    "base_load": 10,
}
_POLICY_TAG = 0x504F4C49  # "POLI"


def stable_hash(s: str) -> int:
    """64-bit hash of a string that does not depend on PYTHONHASHSEED."""
    return int.from_bytes(hashlib.sha256(s.encode("utf-8")).digest()[:8], "big")


def stream(seed: int, name: str, salt: int = 0) -> np.random.Generator:
    """Named child stream of ``SeedSequence(seed)``; ``salt`` perturbs one stream (tests)."""
    key = (_STREAM_IDS[name],) if salt == 0 else (_STREAM_IDS[name], int(salt))
    return np.random.Generator(np.random.PCG64(np.random.SeedSequence(seed, spawn_key=key)))


def policy_rng(seed: int, cell_id: str, policy_name: str) -> np.random.Generator:
    """Tie-break stream for a policy; entropy layout cannot collide with ``stream``."""
    ss = np.random.SeedSequence(
        entropy=[int(seed), stable_hash(cell_id), stable_hash(policy_name), _POLICY_TAG])
    # re-seed from the generated state so the generator holds no raw seed or cell hash
    return np.random.Generator(np.random.PCG64(ss.generate_state(4)))


def _ro(x: np.ndarray) -> np.ndarray:
    x.flags.writeable = False
    return x


def _base_load(seed: int, N: int, H: int, salt: dict) -> tuple[np.ndarray, np.ndarray]:
    """b_mean[1,H] and realized b[1,H] (AR(1) 0.7, stationary sd 0.03 B0, B0 = N)."""
    B0 = float(N)
    s = np.arange(H) / (H - 1)
    b_mean = B0 * (1.0 + BASE_RAMP * s)
    z = stream(seed, "base_load", salt.get("base_load", 0)).standard_normal(H)
    sd = BASE_SD * B0
    e = np.empty(H)
    e[0] = sd * z[0]
    innov = sd * np.sqrt(1.0 - AR_COEF ** 2)
    for t in range(1, H):
        e[t] = AR_COEF * e[t - 1] + innov * z[t]
    return b_mean[None, :], (b_mean + e)[None, :]


def generate_f0r(seed: int, cell: Cell, N: int = 30, *,
                 stream_salt: dict | None = None) -> Instance:
    """F0-R instance (also SCALE with N=300). ``stream_salt`` is for tests only."""
    if cell.family not in ("F0R", "SCALE"):
        raise ValueError("generate_f0r needs an F0R or SCALE cell")
    salt = stream_salt or {}
    H = H_F0R

    def g(name: str) -> np.random.Generator:
        return stream(seed, name, salt.get(name, 0))

    P = g("P").integers(1, 4, size=N)
    E = g("E").integers(2, 13, size=N)
    a = g("a").integers(0, 3, size=N)
    slack = g("slack").integers(0, 13, size=N)
    d = np.minimum(H, a + -(-E // P) + slack)

    n_int = int(round(N / 3))
    q_int = Q_INTOLERANT
    class_stream = g("class")
    perm = class_stream.permutation(N)
    if cell.intol_share is not None:
        # Post hoc class-split option (default off, so default instances are unchanged). The
        # intolerant count is N * share, dithered by one draw from the class stream (taken
        # after the permutation) when that is not an integer, so the expected share is exact.
        x = N * float(cell.intol_share)
        lo = int(np.floor(x + 1e-9))
        frac = x - lo if x - lo > 1e-9 else 0.0
        n_int = lo + (1 if frac > 0 and class_stream.random() < frac else 0)
        q_int = float(cell.q_intol)
    cls = np.zeros(N, dtype=np.int64)
    cls[perm[:n_int]] = 1
    q = np.where(cls == 1, q_int, Q_TOLERANT)
    if cell.homogeneous_iid:
        q = np.full(N, Q_HOMOGENEOUS)
    if cell.deterministic:
        q = np.zeros(N)

    # scored-event uniforms and prior-event uniforms (all drawn regardless of cell)
    v = g("scored_v").random(N)
    u = g("scored_u").random((N, H))
    pv = g("prior_v").random((N, M_MAX))
    pu = g("prior_u").random((N, M_MAX, H))

    M = cell.M
    if cell.deterministic:
        mode = "det"
        prior_A = np.ones((N, M, H), dtype=np.int64)
        prior_stuck = np.zeros((N, M), dtype=bool)
    elif cell.homogeneous_iid:
        mode = "iid"
        prior_A = iid_availability(pv[:, :M], pu[:, :M], q[:, None])
        prior_stuck = pv[:, :M] < q[:, None]
    else:
        mode = "chain"
        prior_A = chain_availability(pv[:, :M], pu[:, :M], q[:, None], cell.r)
        prior_stuck = pv[:, :M] < q[:, None]

    b_mean, b = _base_load(seed, N, H, salt)
    Lval = (E.sum() / cell.rho + b_mean.sum()) / H
    L = np.full((1, H), Lval)

    announced = ((np.arange(H)[None, :] >= a[:, None])
                 & (np.arange(H)[None, :] < d[:, None])).astype(np.int64)

    return Instance(
        family=cell.family, cell=cell, seed=seed, N=N, H=H,
        P=_ro(P.astype(np.int64)), E=_ro(E.astype(np.int64)),
        a=_ro(a.astype(np.int64)), d=_ro(d.astype(np.int64)),
        group=_ro(np.zeros(N, dtype=np.int64)), L=_ro(L), b_mean=_ro(b_mean),
        announced=_ro(announced), prior_A=_ro(prior_A), prior_stuck=_ro(prior_stuck),
        cls=_ro(cls), q=_ro(q), b=_ro(b), avail_mode=mode, r=float(cell.r),
        v=_ro(v), u=_ro(u))


def generate_kcopy(seed: int, cell: Cell, K: int = 8, *,
                   stream_salt: dict | None = None) -> Instance:
    """K-copy instance I_K: K copies of (A, B, D), H = 2, P = E = 1 (MECHANISM 3.6)."""
    if cell.family != "KCOPY":
        raise ValueError("generate_kcopy needs a KCOPY cell")
    if cell.homogeneous_iid:
        raise ValueError("homogeneous_iid does not apply to the K-copy family")
    if cell.delta_A < 2 or cell.delta_b != 0:
        raise ValueError("the K-copy family is defined for delta_A >= 2 and delta_b == 0")
    salt = stream_salt or {}
    N, H = 3 * K, 2

    def g(name: str) -> np.random.Generator:
        return stream(seed, name, salt.get(name, 0))

    # base role slots: A_k = k, B_k = K + k, D_k = 2K + k; participants are a permutation
    base_cls = np.repeat(np.array([1, 0, 2], dtype=np.int64), K)
    base_copy = np.tile(np.arange(K, dtype=np.int64), 3)
    perm = g("class").permutation(N)
    cls = base_cls[perm]
    copy = base_copy[perm]
    isD = cls == 2

    P = np.ones(N, dtype=np.int64)
    E = np.ones(N, dtype=np.int64)
    a = np.where(isD, 1, 0).astype(np.int64)
    d = np.full(N, 2, dtype=np.int64)
    q = np.where(cls == 1, cell.q, 0.0)
    if cell.deterministic:
        q = np.zeros(N)

    v = g("scored_v").random(N)
    u = np.zeros((N, H))  # unused by the K-copy availability
    pv = g("prior_v").random((N, M_MAX))
    M = cell.M
    if cell.deterministic:
        mode = "det"
        prior_stuck = np.zeros((N, M), dtype=bool)
    else:
        mode = "kcopy"
        prior_stuck = pv[:, :M] < q[:, None]
    prior_A = np.ones((N, M, H), dtype=np.int64)
    prior_A[:, :, 0] = ~prior_stuck

    if cell.cap_mode == "pooled":
        group = np.zeros(N, dtype=np.int64)
        L = np.array([[2.0 * K, K + float(cell.c)]])
    else:
        if abs(cell.c / K - round(cell.c / K)) > 1e-12:
            raise ValueError("per_copy cap needs c/K integer")
        group = copy.copy()
        L = np.tile(np.array([2.0, 1.0 + round(cell.c / K)]), (K, 1))
    G = L.shape[0]
    announced = ((np.arange(H)[None, :] >= a[:, None])
                 & (np.arange(H)[None, :] < d[:, None])).astype(np.int64)

    return Instance(
        family="KCOPY", cell=cell, seed=seed, N=N, H=H,
        P=_ro(P), E=_ro(E), a=_ro(a), d=_ro(d), group=_ro(group), L=_ro(L),
        b_mean=_ro(np.zeros((G, H))), announced=_ro(announced),
        prior_A=_ro(prior_A), prior_stuck=_ro(prior_stuck),
        cls=_ro(cls), q=_ro(q), b=_ro(np.zeros((G, H))), avail_mode=mode,
        r=float(cell.r), v=_ro(v), u=_ro(u))


def _f0r_cells() -> list[Cell]:
    base = dict(family="F0R", delta_b=0, r=0.3)
    cells = [Cell(M=M, delta_A=dA, rho=rho, **base)
             for M in (0, 3) for dA in (0, 1, 2, 4) for rho in (0.95, 1.15)]
    sw = dict(M=3, delta_A=2, rho=0.95)
    cells += [Cell(**{**base, **sw, "M": 1}), Cell(**{**base, **sw, "M": 5}),
              Cell(**{**base, **sw, "r": 0.0}), Cell(**{**base, **sw, "r": 1.0}),
              Cell(**{**base, **sw, "rho": 0.7})]
    cells.append(Cell(family="F0R", M=3, delta_A=0, delta_b=2, rho=0.95, r=0.3))
    return cells


def _kcopy_cells(K: int = 8) -> list[Cell]:
    cells = []
    for q in (0.14, 0.40, 0.50):
        for c in range(0, 2 * K + 1, K // 4):
            for M in (0, 1, 3, 5):
                cells.append(Cell(family="KCOPY", M=M, delta_A=2, delta_b=0, q=q,
                                  c=float(c), cap_mode="pooled"))
    for q in (0.14, 0.40, 0.50):
        for c in (0, K, 2 * K):
            for M in (0, 1, 3, 5):
                cells.append(Cell(family="KCOPY", M=M, delta_A=2, delta_b=0, q=q,
                                  c=float(c), cap_mode="per_copy"))
    return cells


F0R_CELLS: list[Cell] = _f0r_cells()
KCOPY_CELLS: list[Cell] = _kcopy_cells(8)


def scale_cell(cell: Cell) -> Cell:
    """The SCALE (N = 300) version of an F0-R cell."""
    return replace(cell, family="SCALE")
