"""Post hoc policies, added after the G3 review (development, post hoc).

Three additions that sit outside the 17-family catalog of POLICY_SPEC 5 (the catalog and its
tests are untouched; ``EXTRA_FAMILIES`` is passed to the runner by ``scripts/run_posthoc_g3.py``):

``sllf``  smoothed least-laxity-first
    N. Chen, C. Kurniawan, Y. Nakahira, L. Chen, S. H. Low, "Smoothed Least-Laxity-First
    Algorithm for EV Charging", IEEE Trans. Smart Grid, arXiv 2102.08610, Section II-C,
    Eqs. (5), (6), (16), (17) and Algorithm 1. Nothing is tuned: paper defaults only
    (``f = log``, which Eq. (16) shows does not matter for any strictly concave increasing f).

    What is implemented, exactly. At decision slot t, over the participants that are active
    (``a_i <= t < d_i``), not revealed stuck in column t (delta_A = 0 re-dispatch; the same
    reading as the rule chassis, OPEN_QUESTIONS row 38) and believed to owe something, with
    the certainty-equivalent belief (confirmed debt minus unconfirmed setpoints, as ce_llf):

    * paper EV i  -> participant i;  maximum rate ``r_i`` -> ``P_i``;  remaining energy
      ``e_i(t)`` -> believed debt ``b_i``;  power limit ``P(t)`` -> the group setpoint cap
      ``max(0, setpoint_cap(g, 0))`` (the forecast cap, margin 0; groups are independent);
    * laxity (Definition 4): ``l_i = (d_i - t) - b_i / P_i`` (real valued, not ceiled);
    * the slot's total is ``T = min(cap, sum_i min(P_i, b_i))`` (Eq. 17);
    * rates are the water-filling solution of Eq. (16): for a threshold ``L`` on the laxity
      after the slot, ``r_i(L) = clip(P_i (L - l_i + 1), 0, min(P_i, b_i))``, since
      ``l_i(t+1) = l_i(t) - 1 + r_i / P_i``. ``L`` solves ``sum_i r_i(L) = T`` by bisection
      (Algorithm 1; 200 halvings of the bracket ``[min l - 1, max(l - 1 + min(P, b)/P)]``);
      that maximizes the minimum post-slot laxity, with the ordering of Eq. (5);
    * integer rounding (the paper's rates are real): ``x_i = floor(r_i)``, then the
      ``T - sum floor(r_i)`` remaining units go one each to the participants with the
      largest fractional part among those with room (``floor < min(P_i, b_i)``). Ties go
      first to participants revealed available in column t (delta_A = 0 only), then to a
      fresh permutation drawn from the policy rng every ``act`` call, never by index.

    The result never exceeds ``P_i``, the believed debt or the group cap, and uses the whole
    of ``T``. Not implemented: the paper's online arrivals (all participants of an event are
    known in advance here) and its power limit P(t) varying with a forecast other than the
    last-value setpoint cap.

``floor_flagged``  flagged-only floor
    The floor rule of POLICY_SPEC 5 restricted to participants stuck in at least one prior
    event (``prior_stuck.any(axis=1)``, M = 3 in the post hoc cells): only they keep the
    one-unit floor during the event (they are never stuck at slot 0, which costs 2 units of
    event shortfall each). Everything after the event is exactly the floor family's chassis
    (``PriorityRule``) at the frozen configuration of ``floor`` for the cell. It reads one
    per-participant input, the prior stuck history, so it is a per-participant rule like
    user_flag; the plan's floor (everyone) is the oblivious form (OPEN_QUESTIONS row 29).
"""
from __future__ import annotations

import numpy as np

from papere.infoset import InformationSet, OracleView, StaticView

from .base import Family, PopulationParams
from .beliefs import CEBelief, HMMBelief
from .catalog import DEFAULT_POST, DEFAULT_RULE
from .rules import (LLFPost, PriorityRule, base_belief, believed_debt, blocked_now,
                    known_available_now)

BISECTION_STEPS = 200
FRAC_EPS = 1e-9


def smoothed_rates(lax: np.ndarray, P: np.ndarray, b: np.ndarray, cap: int) -> np.ndarray:
    """Real-valued sLLF rates (Eq. 16-17) for one cap group.

    ``lax`` laxities, ``P`` rate limits, ``b`` believed debts (> 0), ``cap`` the integer
    group cap. Returns ``r`` with ``0 <= r_i <= min(P_i, b_i)`` and
    ``sum r = min(cap, sum min(P_i, b_i))`` (to bisection tolerance).
    """
    lax = np.asarray(lax, dtype=np.float64)
    P = np.asarray(P, dtype=np.float64)
    room = np.minimum(P, np.asarray(b, dtype=np.float64))
    total = float(min(max(cap, 0), room.sum()))
    if lax.size == 0 or total <= 0.0:
        return np.zeros(lax.shape)
    if total >= room.sum() - 1e-12:
        return room.copy()
    lo = float(lax.min()) - 1.0                       # every rate is 0 here
    hi = float((lax - 1.0 + room / P).max())          # every rate is at its limit here
    for _ in range(BISECTION_STEPS):
        mid = 0.5 * (lo + hi)
        s = np.clip(P * (mid - lax + 1.0), 0.0, room).sum()
        if s >= total:
            hi = mid
        else:
            lo = mid
    r = np.clip(P * (hi - lax + 1.0), 0.0, room)
    return np.round(r, 9)


def round_largest_remainder(r: np.ndarray, room: np.ndarray, total: int,
                            tie: np.ndarray) -> np.ndarray:
    """Integer rates from real rates: floors, then the remaining units to the largest
    fractional parts among participants with room; ``tie`` is a lexsort key (ascending) that
    breaks equal fractions (smaller first)."""
    base = np.floor(r + FRAC_EPS).astype(np.int64)
    base = np.minimum(base, room)
    k = int(total - base.sum())
    if k <= 0:
        return base
    frac = r - base
    cand = np.flatnonzero(base < room)
    order = cand[np.lexsort((tie[cand], -np.round(frac[cand], 9)))]
    out = base.copy()
    out[order[:k]] += 1
    return out


class SmoothedLLF:
    """sLLF with the certainty-equivalent belief (module docstring)."""

    privileged = False

    def __init__(self, name: str = "sllf") -> None:
        self.name = name
        self.belief = CEBelief()
        self._ready = False

    def reset(self, static_view: StaticView, rng: np.random.Generator,
              oracle: OracleView | None = None) -> None:
        self.rng = rng
        self.belief.reset(static_view, None, oracle=oracle)
        self._ready = True

    def floor_mask(self, static_view: StaticView) -> np.ndarray | None:
        return None

    def act(self, view: InformationSet) -> np.ndarray:
        if not self._ready:
            raise RuntimeError(f"{self.name}: reset() has not been called")
        N, t = view.N, view.t
        perm = self.rng.permutation(N)
        b = believed_debt(self.belief.compute(view))
        elig = view.active & (b > 0) & ~blocked_now(view)
        x = np.zeros(N, dtype=np.int64)
        caps = np.maximum(0, view.setpoint_caps(0)).astype(np.int64)
        known = (~known_available_now(view)).astype(np.int64)
        lax = (view.d - t) - b / view.P
        for g in range(view.G):
            idx = np.flatnonzero(elig & (view.group == g))
            if idx.size == 0:
                continue
            P, bb = view.P[idx], b[idx]
            room = np.minimum(P, bb).astype(np.int64)
            total = int(min(caps[g], room.sum()))
            r = smoothed_rates(lax[idx], P, bb, int(caps[g]))
            tie = np.lexsort((perm[idx], known[idx]))   # rank of (known-available, permutation)
            rank = np.empty(idx.size, dtype=np.int64)
            rank[tie] = np.arange(idx.size)
            x[idx] = round_largest_remainder(r, room, total, rank)
        return x


class FloorFlagged(PriorityRule):
    """Floor only the participants stuck in at least one prior event; chassis as ``floor``."""

    def _setup(self, static_view: StaticView, oracle: OracleView | None) -> None:
        ps = np.asarray(static_view.prior_stuck, dtype=bool)
        flag = ps.any(axis=1) if ps.ndim == 2 and ps.shape[1] else np.zeros(
            static_view.N, dtype=bool)
        self.flagged = flag
        self._floored = flag.copy()          # the belief's reset receives the same mask


class LLFPop(LLFPost):
    """LLF-POST with the population-rate posterior in place of e1 (module docstring)."""

    def __init__(self, params: PopulationParams, order: str = "LLF", theta: float = 0.0,
                 m: float = 0, k: int = 0, name: str = "llf_pop") -> None:
        super().__init__(params, order, theta, m, k, name)
        self.hmm = HMMBelief(params, "population")


# --------------------------------------------------------------------------- families
def _make_sllf(cfg: dict, params: PopulationParams):
    return SmoothedLLF(name="sllf")


def _make_floor_flagged(cfg: dict, params: PopulationParams):
    return FloorFlagged(base_belief(cfg["B"]), cfg["O"], cfg["m"], cfg["k"],
                        name="floor_flagged")


def _make_llf_pop(cfg: dict, params: PopulationParams):
    return LLFPop(params, cfg["O"], cfg["theta"], cfg["m"], cfg["k"], name="llf_pop")


EXTRA_FAMILIES: list[Family] = [
    Family(name="sllf", kind="oblivious", grid=({},), default={}, make=_make_sllf),
    Family(name="floor_flagged", kind="per_participant", grid=(dict(DEFAULT_RULE),),
           default=dict(DEFAULT_RULE), make=_make_floor_flagged, tuned_from="floor"),
    Family(name="llf_pop", kind="oblivious", grid=(dict(DEFAULT_POST),),
           default=dict(DEFAULT_POST), make=_make_llf_pop, tuned_from="llf_post"),
]
