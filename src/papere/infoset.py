"""The information-set wrapper (BUILD_SPEC Section 6, FORMULATION Section 3.3).

``InformationSet`` holds copies of permitted data only, as read-only arrays. It
has no reference to the ``Instance`` or to any hidden array, and the revealed
availability it holds is already masked by the simulator: ``A_is`` is known
only where a setpoint could have delivered (``x_is > 0`` and ``r_is > 0``),
encoded as ``-1`` elsewhere. Any read beyond the information set raises
``InformationSetViolation``.
"""
from __future__ import annotations

import operator

import numpy as np

from .instance import Cell, Instance

UNKNOWN = -1  # masked availability


class InformationSetViolation(Exception):
    """Raised on any read beyond the information set."""


def _ro_copy(x, dtype=None) -> np.ndarray:
    """Immutable copy: an array over an immutable ``bytes`` buffer.

    ``flags.writeable = True`` raises on it (and on any view of it), so a policy
    cannot re-enable writes. The buffer holds exactly this array's data.
    """
    src = np.ascontiguousarray(x, dtype=dtype)
    return np.frombuffer(src.tobytes(), dtype=src.dtype).reshape(src.shape)


class _Guarded:
    """Base: immutable; reads of unknown attributes raise a violation."""

    __slots__ = ()

    def __getattr__(self, name: str):
        # only called when normal lookup fails
        if name.startswith("__"):
            raise AttributeError(name)
        raise InformationSetViolation(
            f"{type(self).__name__} exposes no attribute {name!r}")

    def __setattr__(self, name: str, value) -> None:
        raise InformationSetViolation("information set is read-only")


class StaticView(_Guarded):
    """Public parameters only: no time-varying data (for ``reset`` / ``floor_mask``)."""

    __slots__ = ("N", "H", "G", "P", "E", "a", "d", "group", "L", "b_mean",
                 "announced", "prior_A", "prior_stuck", "M", "family",
                 "delta_A", "delta_b")

    def __init__(self, *, N, H, P, E, a, d, group, L, b_mean, announced,
                 prior_A, prior_stuck, family, delta_A, delta_b):
        s = object.__setattr__
        s(self, "N", int(N))
        s(self, "H", int(H))
        s(self, "P", _ro_copy(P, np.int64))
        s(self, "E", _ro_copy(E, np.int64))
        s(self, "a", _ro_copy(a, np.int64))
        s(self, "d", _ro_copy(d, np.int64))
        s(self, "group", _ro_copy(group, np.int64))
        s(self, "L", _ro_copy(L, np.float64))
        s(self, "b_mean", _ro_copy(b_mean, np.float64))
        s(self, "announced", _ro_copy(announced, np.int64))
        s(self, "prior_A", _ro_copy(prior_A, np.int64))
        s(self, "prior_stuck", _ro_copy(prior_stuck, bool))
        s(self, "G", int(self.L.shape[0]))
        s(self, "M", int(self.prior_A.shape[1]))
        s(self, "family", str(family))
        s(self, "delta_A", int(delta_A))
        s(self, "delta_b", int(delta_b))

    @classmethod
    def from_instance(cls, inst: Instance, cell: Cell | None = None) -> "StaticView":
        cell = inst.cell if cell is None else cell
        return cls(N=inst.N, H=inst.H, P=inst.P, E=inst.E, a=inst.a, d=inst.d,
                   group=inst.group, L=inst.L, b_mean=inst.b_mean,
                   announced=inst.announced, prior_A=inst.prior_A,
                   prior_stuck=inst.prior_stuck, family=inst.family,
                   delta_A=cell.delta_A, delta_b=cell.delta_b)


class InformationSet(StaticView):
    """What a policy may see at decision slot ``t``.

    Built from a ``StaticView`` plus already-cut data: ``x_past [N, t]``,
    masked ``A_obs [N, max(0, t-δ_A+1)]`` (int8 in {1, 0, -1}), ``y_conf`` of
    the same shape, ``b_obs [G, max(0, t-δ_b)]``.

    At ``δ_A = 0`` the last column of ``A_confirmed`` is slot ``t`` itself: it is
    all -1 on the first call of ``act`` (``redispatch_round == 0``) and shows
    availability only for participants commanded and found unavailable/available
    in earlier rounds of the same slot; ``y_confirmed`` there is 0 (unknown).
    ``act`` may be called again at the same ``t`` with ``redispatch_round >= 1``.
    """

    __slots__ = ("t", "redispatch_round", "_x_past", "_A_conf", "_y_conf", "_b_obs",
                 "_debt", "_b_hat")

    def __init__(self, static: StaticView, t: int, x_past, A_obs, y_conf, b_obs,
                 redispatch_round: int = 0):
        s = object.__setattr__
        for name in StaticView.__slots__:
            s(self, name, getattr(static, name))  # shares read-only arrays
        t = int(t)
        if not 0 <= t < self.H:
            raise InformationSetViolation(f"decision slot {t} outside 0..{self.H - 1}")
        n_conf = max(0, t - self.delta_A + 1)
        n_b = max(0, t - self.delta_b)
        x_past = np.asarray(x_past)
        A_obs = np.asarray(A_obs)
        y_conf = np.asarray(y_conf)
        b_obs = np.asarray(b_obs)
        if x_past.shape != (self.N, t):
            raise ValueError("x_past must have shape [N, t]")
        if A_obs.shape != (self.N, n_conf) or y_conf.shape != (self.N, n_conf):
            raise ValueError("A_obs and y_conf must have shape [N, max(0, t-delta_A+1)]")
        if b_obs.shape != (self.G, n_b):
            raise ValueError("b_obs must have shape [G, max(0, t-delta_b)]")
        if A_obs.size and not np.isin(A_obs, (-1, 0, 1)).all():
            raise ValueError("A_obs entries must be in {1, 0, -1}")
        s(self, "t", t)
        s(self, "redispatch_round", int(redispatch_round))
        s(self, "_x_past", _ro_copy(x_past, np.int64))
        s(self, "_A_conf", _ro_copy(A_obs, np.int8))
        s(self, "_y_conf", _ro_copy(y_conf, np.int64))
        s(self, "_b_obs", _ro_copy(b_obs, np.float64))
        debt = _ro_copy(self.E - self._y_conf.sum(axis=1), np.int64)
        s(self, "_debt", debt)
        if n_b > 0:
            bh = _ro_copy(self._b_obs[:, -1], np.float64)
        else:
            bh = _ro_copy(self.b_mean[:, t], np.float64)
        s(self, "_b_hat", bh)

    # ---- construction from simulator state ---------------------------------
    @classmethod
    def build(cls, static: StaticView, t: int, x: np.ndarray, A_masked: np.ndarray,
              y: np.ndarray, b: np.ndarray, redispatch_round: int = 0, *,
              delta_A: int | None = None, delta_b: int | None = None) -> "InformationSet":
        """Cut the permitted prefixes out of full-size arrays and wrap them.

        ``A_masked`` must already be masked (``-1`` where not revealed). Columns
        of ``x`` at or after ``t``, ``A_masked``/``y`` after ``t-δ_A`` and ``b``
        after ``t-1-δ_b`` are never read. The simulator passes the lags from its own
        ``Cell`` and a ``static`` that no policy can reach; the lags default to the
        ones stored on ``static`` (tests only).
        """
        dA = static.delta_A if delta_A is None else int(delta_A)
        db = static.delta_b if delta_b is None else int(delta_b)
        n_conf = max(0, t - dA + 1)
        n_b = max(0, t - db)
        return cls(static, t, x[:, :t], A_masked[:, :n_conf], y[:, :n_conf], b[:, :n_b],
                   redispatch_round)

    # ---- window of what is known -------------------------------------------
    @property
    def last_confirmed_slot(self) -> int:
        """``t - δ_A``: latest slot whose A and y are known (negative: none)."""
        return self.t - self.delta_A

    @property
    def last_base_slot(self) -> int:
        """``t - 1 - δ_b``: latest slot whose base load is known (negative: none)."""
        return self.t - 1 - self.delta_b

    # ---- whole-array accessors (permitted prefix only) ----------------------
    @property
    def x_past(self) -> np.ndarray:
        """Own past setpoints, shape [N, t]."""
        return self._x_past

    @property
    def A_confirmed(self) -> np.ndarray:
        """Revealed availability, int8 [N, max(0, t-δ_A+1)] in {1, 0, -1 = unknown}."""
        return self._A_conf

    @property
    def y_confirmed(self) -> np.ndarray:
        """Delivered units, int64 [N, max(0, t-δ_A+1)], same cutoff as ``A_confirmed``."""
        return self._y_conf

    @property
    def b_observed(self) -> np.ndarray:
        """Observed base load, float64 [G, max(0, t-δ_b)] (slots 0..t-1-δ_b)."""
        return self._b_obs

    # ---- per-slot accessors -------------------------------------------------
    def _check(self, s, upper: int, what: str) -> int:
        try:
            s = operator.index(s)
        except TypeError:
            raise InformationSetViolation(f"{what}: slot must be an integer") from None
        if s < 0 or s > upper:
            raise InformationSetViolation(
                f"{what}({s}) is outside the information set at t={self.t} "
                f"(allowed 0..{upper})")
        return s

    def availability(self, s: int) -> np.ndarray:
        """Revealed ``A_is`` for all i (1/0/-1) at slot ``s <= t - δ_A``."""
        s = self._check(s, self.t - self.delta_A, "availability")
        return self._A_conf[:, s]

    def delivered(self, s: int) -> np.ndarray:
        """``y_is`` for all i at slot ``s <= t - δ_A``."""
        s = self._check(s, self.t - self.delta_A, "delivered")
        return self._y_conf[:, s]

    def base_load(self, s: int) -> np.ndarray:
        """``b_s`` for all groups at slot ``s <= t - 1 - δ_b``."""
        s = self._check(s, self.t - 1 - self.delta_b, "base_load")
        return self._b_obs[:, s]

    def setpoint(self, s: int) -> np.ndarray:
        """Own setpoint ``x_is`` for all i at slot ``s < t``."""
        s = self._check(s, self.t - 1, "setpoint")
        return self._x_past[:, s]

    # ---- derived helpers ----------------------------------------------------
    @property
    def confirmed_debt(self) -> np.ndarray:
        """``E_i - sum_{s <= t-δ_A} y_is`` (int64 [N])."""
        return self._debt

    @property
    def base_forecast(self) -> np.ndarray:
        """Default forecast ``b̂[g, t]``: last observed base load, else ``b_mean[g, t]``."""
        return self._b_hat

    @property
    def active(self) -> np.ndarray:
        """Boolean [N]: slot ``t`` lies in participant i's window."""
        return (self.a <= self.t) & (self.t < self.d)

    def setpoint_cap(self, g: int, margin: float = 0) -> int:
        """``floor(L[g,t] - b̂[g,t] - margin + 1e-9)``; may be negative (not clamped)."""
        if not 0 <= int(g) < self.G:
            raise InformationSetViolation(f"no cap group {g}")
        return int(np.floor(self.L[int(g), self.t] - self._b_hat[int(g)] - margin + 1e-9))

    def setpoint_caps(self, margin: float = 0) -> np.ndarray:
        """``setpoint_cap`` for every group, int64 [G]."""
        return np.floor(self.L[:, self.t] - self._b_hat - margin + 1e-9).astype(np.int64)


class OracleView:
    """True class and stuck probabilities, for privileged reference policies only."""

    __slots__ = ("cls", "q")

    def __init__(self, cls_, q):
        object.__setattr__(self, "cls", _ro_copy(cls_, np.int64))
        object.__setattr__(self, "q", _ro_copy(q, np.float64))

    def __setattr__(self, name, value):
        raise AttributeError("OracleView is read-only")

    @classmethod
    def from_instance(cls, inst: Instance) -> "OracleView":
        return cls(inst.cls, inst.q)
