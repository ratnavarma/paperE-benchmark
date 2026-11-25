"""Priority-rule chassis and the rule families built on it (POLICY_SPEC Sections 4 and 5).

Chassis (``PriorityRule``). At slot t, over the participants that are active
(``a_i <= t < d_i``), not blocked this slot (below) and believed to owe something
(``b_i > 0``, which also drops every known-complete participant because every belief puts
debt 0 on them):

* believed debt ``b_i`` from the family's belief (point beliefs: the point mass; a
  non-point belief would give ``ceil(E[debt])``);
* effective deadline ``d'_i = max(t + 1, d_i - k)``;
* laxity ``l_i = (d'_i - t) - ceil(b_i / P_i)``;
* order: LLF by ``l`` ascending or EDF by ``d'`` ascending; ties by a permutation of the
  participants drawn fresh from the policy rng in every ``act`` call, never by index;
* allocation in that order: ``x_i = min(P_i, b_i, remaining cap of group(i))`` with the
  group cap ``max(0, view.setpoint_cap(g, m))``.

Two readings the spec leaves open, applied to every rule family at ``delta_A = 0`` where
availability of the current slot may already be revealed (re-dispatch rounds):

* a participant whose column-t entry is revealed *stuck* is blocked for this slot: a
  command to it cannot deliver and would only occupy cap, so it would also stop the
  re-dispatch from ever reaching the next participant;
* ties go first to participants revealed *available* in column t (they are certain to
  deliver), then to the random permutation. Without this a re-dispatch round could swap a
  revealed-available participant out for an unrevealed twin of equal priority.

Neither changes the first call of a slot (nothing is revealed then) or any ``delta_A >= 1``
decision.

Families (``Family`` objects are in ``catalog.py``):

* ``PriorityRule`` with ``CEBelief`` / ``PESBelief``: CE-LLF, CE-EDF, PES-LLF and the best
  symmetric margin (O x B x m x k).
* persistence: ``PriorityRule`` with ``PersistBelief(base=B)``.
* uncorrectable-only pessimism: ``UncorrectableBelief(B)``. An unconfirmed setpoint at
  slot s is assumed failed iff ``s + delta_A >= d_i`` (it can no longer be corrected after
  its outcome arrives); every other unconfirmed setpoint is treated by B (CE: delivered,
  PES: failed). B = PES therefore equals the symmetric-margin PES rule; the two grids
  coincide on those 24 points but are reported as separate families (OPEN_QUESTIONS).
* probe-first (``ProbeFirst``), floor (``PriorityRule(floor=True)``), user-history flag
  (``MixBelief`` of PES for flagged participants and B for the rest).
* ``RWDFE`` and ``LLFPost``: per-participant rules reading the e1 ``HMMBelief``.

RWDF-E index. ``index_i = c_i * phat_i * qhat_i ** n_i`` with ``c_i`` the confirmed debt,
``phat_i = p_avail[i, t]`` from the e1 posterior, ``n_i = |U_i|`` the number of unconfirmed
setpoints and ``qhat_i`` the mean over ``U_i`` of the e1 per-setpoint failure probability
``1 - P(Z_is = avail)``. ``P(Z_is = avail)`` is the filtered chain law at the slot: the
last revealed state of i (a point mass) propagated ``s - s_last`` steps with the
population ``p_stay`` and ``r`` of the belief, or, if nothing is revealed in this event,
the initial law ``P(Z_i0 = avail) = 1 - q_i`` propagated ``s`` steps. It is computed in
``_fail_prob`` from the public ``q``, ``p_stay`` and ``r`` of the reset belief; it does not
condition on the unconfirmed setpoints' own outcomes (unobserved). ``qhat ** 0 = 1``.
Order (family ``rwdf_e``): primary key O (LLF laxity on ``d'`` and the belief-B debt, or EDF
on ``d'``), then the index descending (to 12 digits), then the random permutation. The family
``rwdf_e_literal`` serves in descending index first and uses O only for ties (it ignores
deadlines; reported as a sensitivity row). Units by the belief B in both.

LLF-POST. Laxity (or ``d'`` for EDF) on the PES debt ``c_i``; ties by ``p_pos`` descending
under e1; skipped if ``p_pos <= theta``; units ``#{k : tail[i, k] > theta}`` capped by
``P_i`` and the group cap.
"""
from __future__ import annotations

import numpy as np

from papere.infoset import InformationSet, OracleView, StaticView

from .base import PopulationParams, PosteriorState
from .beliefs import (CEBelief, HMMBelief, PersistBelief, PESBelief, known_complete,
                      last_revealed_state)

ORDERS = ("EDF", "LLF")
BASES = ("CE", "PES")
TIE_DIGITS = 12


# ----------------------------------------------------------------------------- helpers
def base_belief(name: str):
    """The point belief called ``'CE'`` or ``'PES'``."""
    if name == "CE":
        return CEBelief()
    if name == "PES":
        return PESBelief()
    raise ValueError(f"base belief must be one of {BASES}, got {name!r}")


def believed_debt(post: PosteriorState) -> np.ndarray:
    """Integer believed debt [N]: the point mass, or ``ceil(E[debt])`` for a distribution."""
    if post.point:
        return np.rint(post.exp_debt).astype(np.int64)
    return np.ceil(np.asarray(post.exp_debt) - 1e-9).astype(np.int64)


def ceil_div(b: np.ndarray, P: np.ndarray) -> np.ndarray:
    return -((-b) // P)


def effective_deadline(view: InformationSet, k: int) -> np.ndarray:
    """``d'_i = max(t + 1, d_i - k)`` (int64 [N])."""
    return np.maximum(view.t + 1, view.d - int(k))


def laxity(view: InformationSet, b: np.ndarray, k: int) -> np.ndarray:
    return (effective_deadline(view, k) - view.t) - ceil_div(b, view.P)


def current_column(view: InformationSet) -> np.ndarray | None:
    """Revealed availability of slot t (1/0/-1) at delta_A = 0, else None."""
    if view.delta_A == 0 and view.A_confirmed.shape[1] == view.t + 1:
        return view.A_confirmed[:, view.t]
    return None


def blocked_now(view: InformationSet) -> np.ndarray:
    """Participants revealed stuck at slot t (delta_A = 0 re-dispatch): cannot deliver now."""
    col = current_column(view)
    if col is None:
        return np.zeros(view.N, dtype=bool)
    return col == 0


def known_available_now(view: InformationSet) -> np.ndarray:
    col = current_column(view)
    if col is None:
        return np.zeros(view.N, dtype=bool)
    return col == 1


def _state_like(st: PosteriorState, debt: np.ndarray) -> PosteriorState:
    """Point-mass PosteriorState at integer ``debt`` with the availability of ``st``."""
    kmax = st.tail.shape[1]
    tail = (debt[:, None] >= np.arange(1, kmax + 1)[None, :]).astype(np.float64)
    return PosteriorState(t=st.t, tail=tail, tail_avail=tail[:, :, None] * st.p_avail[:, None, :],
                          p_avail=st.p_avail, exp_debt=debt.astype(np.float64),
                          p_pos=tail[:, 0].copy(), point=True)


# ------------------------------------------------------------------------ belief wrappers
class UncorrectableBelief:
    """Uncorrectable-only pessimism (POLICY_SPEC 5).

    Unconfirmed setpoint at slot s is assumed failed iff ``s + delta_A >= d_i``; the others
    are treated by the base belief ``B``. Debt is ``max(c_i - delivered, 0)`` where
    ``delivered`` is the sum of the setpoints assumed delivered; known-complete
    participants have debt 0. Availability is 1 inside the window.
    """

    def __init__(self, base: str = "PES") -> None:
        if base not in BASES:
            raise ValueError(f"base must be one of {BASES}")
        self.base = base
        self.name = f"UNCORR-{base}"
        self._pes = PESBelief()

    def reset(self, static_view: StaticView, floored: np.ndarray | None = None,
              oracle: OracleView | None = None) -> None:
        self._pes.reset(static_view, floored, oracle=oracle)

    def compute(self, view: InformationSet) -> PosteriorState:
        st = self._pes.compute(view)          # PES debt, 0 for known complete
        c = np.rint(st.exp_debt).astype(np.int64)
        t, dA = view.t, view.delta_A
        lo = max(t - dA + 1, 0)
        if self.base == "PES" or lo >= t:
            return st
        slots = np.arange(lo, t)
        correctable = (slots[None, :] + dA) < view.d[:, None]
        delivered = (view.x_past[:, lo:t] * correctable).sum(axis=1)
        debt = np.where(c > 0, np.maximum(c - delivered, 0), 0)
        return _state_like(st, debt)


class MixBelief:
    """Row-wise mixture: ``if_true`` for the participants in ``mask``, ``if_false`` for the rest."""

    def __init__(self, if_true, if_false, name: str = "MIX") -> None:
        self.a, self.b, self.name = if_true, if_false, name
        self.mask = None

    def set_mask(self, mask: np.ndarray) -> None:
        self.mask = np.asarray(mask, dtype=bool)

    def reset(self, static_view: StaticView, floored: np.ndarray | None = None,
              oracle: OracleView | None = None) -> None:
        self.a.reset(static_view, floored, oracle=oracle)
        self.b.reset(static_view, floored, oracle=oracle)

    def compute(self, view: InformationSet) -> PosteriorState:
        if self.mask is None:
            raise RuntimeError("MixBelief: mask not set")
        sa, sb = self.a.compute(view), self.b.compute(view)
        m = self.mask
        return PosteriorState(
            t=sa.t, tail=np.where(m[:, None], sa.tail, sb.tail),
            tail_avail=np.where(m[:, None, None], sa.tail_avail, sb.tail_avail),
            p_avail=np.where(m[:, None], sa.p_avail, sb.p_avail),
            exp_debt=np.where(m, sa.exp_debt, sb.exp_debt),
            p_pos=np.where(m, sa.p_pos, sb.p_pos), point=bool(sa.point and sb.point))


# ------------------------------------------------------------------------------- chassis
class PriorityRule:
    """The chassis of POLICY_SPEC 4 for one point belief.

    ``order`` is ``'LLF'`` or ``'EDF'``, ``m`` the cap margin, ``k`` the deadline tightening.
    ``floor=True`` floors every participant (``floor_mask`` all True; the belief's ``reset``
    receives that mask).
    """

    privileged = False

    def __init__(self, belief, order: str = "LLF", m: float = 0, k: int = 0,
                 name: str = "rule", floor: bool = False) -> None:
        if order not in ORDERS:
            raise ValueError(f"order must be one of {ORDERS}")
        if float(m) < 0 or int(k) < 0:
            raise ValueError("m and k must be non-negative")
        self.belief = belief
        self.order = order
        self.m = float(m)
        self.k = int(k)
        self.name = name
        self.floor = bool(floor)
        self._ready = False

    # ---- Policy protocol -------------------------------------------------------
    def reset(self, static_view: StaticView, rng: np.random.Generator,
              oracle: OracleView | None = None) -> None:
        self.rng = rng
        self._N = static_view.N
        self._floored = np.ones(self._N, dtype=bool) if self.floor else None
        self._setup(static_view, oracle)
        self.belief.reset(static_view, self._floored, oracle=oracle)
        self._ready = True

    def _setup(self, static_view: StaticView, oracle: OracleView | None) -> None:
        """Hook for subclasses (called before the belief reset)."""

    def floor_mask(self, static_view: StaticView) -> np.ndarray | None:
        return None if self._floored is None else self._floored.copy()

    def act(self, view: InformationSet) -> np.ndarray:
        if not self._ready:
            raise RuntimeError(f"{self.name}: reset() has not been called")
        elig, want, keys, probe = self._plan(view)
        order = self._order(view, elig, keys)
        return self._allocate(view, order, want, probe)

    # ---- the rule ---------------------------------------------------------------
    def _o_key(self, view: InformationSet, b: np.ndarray) -> np.ndarray:
        if self.order == "LLF":
            return laxity(view, b, self.k)
        return effective_deadline(view, self.k)

    def _plan(self, view: InformationSet):
        """(eligible mask, wanted units [N], priority keys, probe mask or None)."""
        post = self.belief.compute(view)
        b = believed_debt(post)
        elig = view.active & (b > 0) & ~blocked_now(view)
        return elig, b, [self._o_key(view, b)], None

    def _order(self, view: InformationSet, elig: np.ndarray, keys: list) -> np.ndarray:
        """Eligible indices sorted by ``keys`` (first is primary), known-available-now, then a
        permutation drawn fresh from the policy rng."""
        perm = self.rng.permutation(view.N)
        idx = np.flatnonzero(elig)
        if idx.size == 0:
            return idx
        cols = [np.asarray(k)[idx] for k in keys]
        cols.append((~known_available_now(view))[idx].astype(np.int64))
        cols.append(perm[idx])
        return idx[np.lexsort(cols[::-1])]

    def _caps(self, view: InformationSet) -> np.ndarray:
        return np.maximum(0, view.setpoint_caps(self.m)).astype(np.int64)

    def _allocate(self, view: InformationSet, order: np.ndarray, want: np.ndarray,
                  probe: np.ndarray | None) -> np.ndarray:
        x = np.zeros(view.N, dtype=np.int64)
        rem = self._caps(view)
        P, grp = view.P, view.group
        if probe is not None:                       # 1-unit probes first, in priority order
            for i in order:
                if probe[i] and rem[grp[i]] > 0:
                    x[i] = 1
                    rem[grp[i]] -= 1
        for i in order:
            g = grp[i]
            u = min(int(P[i]) - int(x[i]), int(want[i]) - int(x[i]), int(rem[g]))
            if u > 0:
                x[i] += u
                rem[g] -= u
        return x


# ---------------------------------------------------------------------------- probe-first
class ProbeFirst(PriorityRule):
    """Probe-first (POLICY_SPEC 5): 1-unit probes, then the chassis with belief B.

    Probed: every non-complete active participant at its release slot (``a_i = t``) and every
    one whose last revealed state in this event is stuck, except those revealed stuck in
    column t at delta_A = 0 (already known stuck now). Probes are served in the chassis
    order and count against the group caps; a probed participant keeps its probe as the
    first unit of the chassis allocation (``x_i = max(1, min(P_i, b_i, ...))``). A
    known-complete participant is never probed.
    """

    def _plan(self, view: InformationSet):
        post = self.belief.compute(view)
        b = believed_debt(post)
        has, state = last_revealed_state(view)
        probe = (view.active & ~known_complete(view) & ~blocked_now(view)
                 & ((view.a == view.t) | (has & (state == 0))))
        elig = (view.active & ~blocked_now(view)) & ((b > 0) | probe)
        want = np.where(probe, np.maximum(b, 1), b)
        return elig, want, [self._o_key(view, b)], probe


# ------------------------------------------------------------------------------ per-participant
class RWDFE(PriorityRule):
    """RWDF-E (``literal=False``, family ``rwdf_e``) and the literal transplant (``literal=True``).

    Hou-Kumar's index ranks packets that share one deadline. For heterogeneous windows the
    faithful extension is: primary key O (LLF laxity on d', or EDF on d', belief-B debt),
    secondary key the index ``c_i * phat_i * qhat_i ** n_i`` descending, then the random
    permutation. ``literal=True`` (family ``rwdf_e_literal``, a sensitivity row) puts the
    index first and uses O only to break index ties, which ignores deadlines.

    ``qhat ** n`` treats the n unconfirmed setpoints as failing independently with the same
    per-setpoint probability; the chain makes consecutive outcomes positively correlated, so
    this is an approximation that is kept as specified.

    ``belief`` supplies the units (B = CE or PES); the e1 ``HMMBelief`` supplies the index.
    ``last_index`` holds the index of the latest ``act`` call (for tests).
    """

    def __init__(self, params: PopulationParams, base: str = "PES", order: str = "LLF",
                 m: float = 0, k: int = 0, name: str = "rwdf_e", literal: bool = False) -> None:
        super().__init__(base_belief(base), order, m, k, name)
        self.literal = bool(literal)
        self.hmm = HMMBelief(params, "e1")
        self.last_index: np.ndarray | None = None

    def _setup(self, static_view: StaticView, oracle: OracleView | None) -> None:
        self.hmm.reset(static_view, None, oracle=oracle)
        H = static_view.H
        ps, r = self.hmm.p_stay, self.hmm.r
        pa_a, pa_s = np.empty(H + 1), np.empty(H + 1)
        pa_a[0], pa_s[0] = 1.0, 0.0
        for h in range(H):
            pa_a[h + 1] = pa_a[h] * ps + (1.0 - pa_a[h]) * r
            pa_s[h + 1] = pa_s[h] * ps + (1.0 - pa_s[h]) * r
        self._pa_a, self._pa_s = pa_a, pa_s

    def _fail_prob(self, view: InformationSet) -> tuple[np.ndarray, np.ndarray]:
        """(n_i, qhat_i): number of unconfirmed setpoints and their mean e1 failure probability."""
        t, dA, N = view.t, view.delta_A, view.N
        lo = max(t - dA + 1, 0)
        if lo >= t:
            return np.zeros(N, dtype=np.int64), np.zeros(N)
        has, state = last_revealed_state(view)
        A = view.A_confirmed
        if A.shape[1]:
            rev = A >= 0
            last_idx = A.shape[1] - 1 - np.argmax(rev[:, ::-1], axis=1)
        else:
            last_idx = np.zeros(N, dtype=np.int64)
        anchor = np.where(has, last_idx, 0)
        p_anchor = np.where(has, (state == 1).astype(np.float64), 1.0 - self.hmm.q)
        slots = np.arange(lo, t)
        lag = slots[None, :] - anchor[:, None]
        pav = p_anchor[:, None] * self._pa_a[lag] + (1.0 - p_anchor)[:, None] * self._pa_s[lag]
        sent = view.x_past[:, lo:t] > 0
        n = sent.sum(axis=1)
        qhat = np.where(n > 0, ((1.0 - pav) * sent).sum(axis=1) / np.maximum(n, 1), 0.0)
        return n.astype(np.int64), qhat

    def _plan(self, view: InformationSet):
        post_h = self.hmm.compute(view)
        b = believed_debt(self.belief.compute(view))
        n, qhat = self._fail_prob(view)
        c = view.confirmed_debt.astype(np.float64)
        idx = c * post_h.p_avail[:, view.t] * np.power(qhat, n)
        idx = np.where(known_complete(view), 0.0, idx)
        self.last_index = idx
        elig = view.active & (b > 0) & ~blocked_now(view)
        neg = -np.round(idx, TIE_DIGITS)
        o = self._o_key(view, b)
        return elig, b, ([neg, o] if self.literal else [o, neg]), None


class LLFPost(PriorityRule):
    """LLF-POST: order on PES debt, ties by e1 ``p_pos`` descending, skip ``p_pos <= theta``."""

    def __init__(self, params: PopulationParams, order: str = "LLF", theta: float = 0.0,
                 m: float = 0, k: int = 0, name: str = "llf_post") -> None:
        super().__init__(PESBelief(), order, m, k, name)
        if float(theta) < 0:
            raise ValueError("theta must be non-negative")
        self.theta = float(theta)
        self.hmm = HMMBelief(params, "e1")

    def _setup(self, static_view: StaticView, oracle: OracleView | None) -> None:
        self.hmm.reset(static_view, None, oracle=oracle)

    def _plan(self, view: InformationSet):
        post = self.hmm.compute(view)
        b_pes = believed_debt(self.belief.compute(view))
        th = self.theta
        want = (post.tail > th).sum(axis=1).astype(np.int64)
        elig = view.active & (post.p_pos > th) & (want > 0) & ~blocked_now(view)
        keys = [self._o_key(view, b_pes), -np.round(post.p_pos, TIE_DIGITS)]
        return elig, want, keys, None


# -------------------------------------------------------------------------------- builders
def user_flag_rule(base: str, order: str, m: float, k: int, name: str = "user_flag"):
    """User-history flag: participants stuck in any prior event get PES, the rest B."""
    mix = MixBelief(PESBelief(), base_belief(base), name=f"FLAG-{base}")
    pol = _FlagRule(mix, order, m, k, name)
    return pol


class _FlagRule(PriorityRule):
    def _setup(self, static_view: StaticView, oracle: OracleView | None) -> None:
        flag = np.asarray(static_view.prior_stuck, dtype=bool)
        flag = flag.any(axis=1) if flag.ndim == 2 and flag.shape[1] else np.zeros(
            static_view.N, dtype=bool)
        self.belief.set_mask(flag)
        self.flagged = flag
