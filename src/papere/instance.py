"""Cell and Instance dataclasses (BUILD_SPEC Section 3).

An ``Instance`` is one realized draw for one (seed, cell). Public fields may be
shown to policies through the information-set wrapper; hidden fields (class,
stuck probabilities, realized base load, availability uniforms) never may.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

FAMILIES = ("F0R", "KCOPY", "SCALE")
CAP_MODES = ("pooled", "per_copy")

STAY_AVAILABLE = 0.98  # P(available stays available) in the two-state chain


@dataclass(frozen=True)
class Cell:
    """One experimental cell. Unused fields keep their defaults."""

    family: str = "F0R"
    M: int = 0
    delta_A: int = 0
    delta_b: int = 0
    rho: float = 1.0
    r: float = 0.3
    # K-copy only
    q: float = 0.14
    c: float = 0.0
    cap_mode: str = "pooled"
    # option flags (negative controls)
    deterministic: bool = False
    homogeneous_iid: bool = False
    # F0-R / SCALE only: class split (share of pause-intolerant participants and their stuck
    # probability). ``None`` keeps the generator's default (1/3 at q = 0.40). Added for the
    # post hoc heterogeneity sweep (OPEN_QUESTIONS row 60); both are set together.
    intol_share: float | None = None
    q_intol: float | None = None

    def __post_init__(self) -> None:
        if self.family not in FAMILIES:
            raise ValueError(f"unknown family {self.family!r}")
        if self.cap_mode not in CAP_MODES:
            raise ValueError(f"unknown cap_mode {self.cap_mode!r}")
        if not 0 <= self.M <= 5:
            raise ValueError("M must be in 0..5")
        if self.delta_A < 0 or self.delta_b < 0:
            raise ValueError("lags must be non-negative")
        if (self.intol_share is None) != (self.q_intol is None):
            raise ValueError("intol_share and q_intol are set together or not at all")
        if self.intol_share is not None:
            if self.family == "KCOPY":
                raise ValueError("the class split does not apply to the K-copy family")
            if not 0.0 < self.intol_share < 1.0 or not 0.0 <= self.q_intol <= 1.0:
                raise ValueError("intol_share must be in (0, 1) and q_intol in [0, 1]")

    @property
    def cell_id(self) -> str:
        """Stable, human-readable identifier (used for seeding policy streams)."""
        if self.family == "KCOPY":
            s = (f"KCOPY_{self.cap_mode}_q{self.q:g}_c{self.c:g}_M{self.M}"
                 f"_dA{self.delta_A}_db{self.delta_b}")
        else:
            s = (f"{self.family}_M{self.M}_dA{self.delta_A}_db{self.delta_b}"
                 f"_rho{self.rho:g}_r{self.r:g}")
        if self.deterministic:
            s += "_det"
        if self.homogeneous_iid:
            s += "_iid"
        if self.intol_share is not None:
            s += f"_split{self.intol_share:g}_q{self.q_intol:g}"
        return s


def chain_availability(v: np.ndarray, u: np.ndarray, q: np.ndarray, r: float,
                       floored: np.ndarray | None = None) -> np.ndarray:
    """Two-state chain availability, shape ``u.shape`` (``[..., H]``).

    Slot 0: stuck iff ``v < q`` (never if floored). For t >= 1 an available
    participant stays available iff ``u_t < 0.98``; a stuck one returns iff
    ``u_t < r``. The same ``v`` and ``u`` serve every ``r``.
    """
    H = u.shape[-1]
    stuck0 = v < q
    if floored is not None:
        stuck0 = stuck0 & ~floored
    A = np.empty(u.shape, dtype=np.int64)
    cur = (~stuck0).astype(bool)
    A[..., 0] = cur
    for t in range(1, H):
        cur = np.where(cur, u[..., t] < STAY_AVAILABLE, u[..., t] < r)
        A[..., t] = cur
    return A


def iid_availability(v: np.ndarray, u: np.ndarray, q: np.ndarray,
                     floored: np.ndarray | None = None) -> np.ndarray:
    """I.i.d. Bernoulli(1 - q) availability (NC3'); slot 0 uses ``v``."""
    stuck0 = v < q
    if floored is not None:
        stuck0 = stuck0 & ~floored
    A = (u < (1.0 - q)[..., None]).astype(np.int64)
    A[..., 0] = ~stuck0
    return A


def kcopy_availability(v: np.ndarray, q: np.ndarray, H: int,
                       floored: np.ndarray | None = None) -> np.ndarray:
    """K-copy availability: stuck at slot 0 iff ``v < q``; available afterwards."""
    stuck0 = v < q
    if floored is not None:
        stuck0 = stuck0 & ~floored
    A = np.ones(v.shape + (H,), dtype=np.int64)
    A[..., 0] = ~stuck0
    return A


@dataclass(eq=False)
class Instance:
    """A realized instance. See BUILD_SPEC Section 3 for the public/hidden split."""

    family: str
    cell: Cell
    seed: int
    # ---- public ----
    N: int
    H: int
    P: np.ndarray            # [N] int64
    E: np.ndarray            # [N] int64
    a: np.ndarray            # [N] int64 release slot
    d: np.ndarray            # [N] int64 exclusive deadline
    group: np.ndarray        # [N] int64 cap group
    L: np.ndarray            # [G, H] float64
    b_mean: np.ndarray       # [G, H] float64
    announced: np.ndarray    # [N, H] int64 in {1, 0, -1}
    prior_A: np.ndarray      # [N, M, H] int64
    prior_stuck: np.ndarray  # [N, M] bool
    # ---- hidden ----
    cls: np.ndarray          # [N] int64: 1 = intolerant (A), 0 = tolerant (B), 2 = D
    q: np.ndarray            # [N] float64 stuck probability after a pause
    b: np.ndarray            # [G, H] float64 realized base load
    avail_mode: str          # 'chain' | 'iid' | 'det' | 'kcopy'
    r: float
    v: np.ndarray            # [N] initial stuck uniforms
    u: np.ndarray            # [N, H] chain uniforms

    @property
    def n_groups(self) -> int:
        return int(self.L.shape[0])

    def slot_cap(self) -> np.ndarray:
        """Realized slot headroom ``max(0, floor(L - b + 1e-9))`` [G, H] (int64)."""
        return np.maximum(0, np.floor(self.L - self.b + 1e-9)).astype(np.int64)

    def availability(self, floored: np.ndarray | None = None) -> np.ndarray:
        """Scored-event availability ``A[N, H]``; floored participants are never stuck.

        The uniforms are stored, so floored and unfloored versions share draws.
        """
        if floored is None:
            fl = np.zeros(self.N, dtype=bool)
        else:
            fl = np.asarray(floored, dtype=bool)
            if fl.shape != (self.N,):
                raise ValueError("floored must have shape [N]")
        if self.avail_mode == "det":
            return np.ones((self.N, self.H), dtype=np.int64)
        if self.avail_mode == "chain":
            return chain_availability(self.v, self.u, self.q, self.r, fl)
        if self.avail_mode == "iid":
            return iid_availability(self.v, self.u, self.q, fl)
        if self.avail_mode == "kcopy":
            return kcopy_availability(self.v, self.q, self.H, fl)
        raise ValueError(f"unknown avail_mode {self.avail_mode!r}")
