"""Beliefs over remaining debt and availability (POLICY_SPEC Sections 2 and 3.2).

Every belief maps an ``InformationSet`` to a ``PosteriorState`` and reads nothing else.
At decision slot ``t`` with lag ``delta_A``:

* confirmed slots are ``s <= c`` with ``c = t - delta_A``; the confirmed debt ``c_i`` is
  the debt after slot ``c``;
* unconfirmed slots of participant i are ``U_i = {s : c < s < t, x_is > 0}``; their
  outcome is not observed, so the availability state at ``c`` (the last thing observed)
  conditions everything after it;
* at ``delta_A = 0`` the last confirmed column is slot ``t`` itself: ``A_confirmed[:, t]``
  holds revealed entries (1/0) for participants commanded in an earlier re-dispatch
  round and -1 elsewhere. A revealed entry is an exact observation of ``Z_t``;
* a participant is *known complete* if ``c_i = 0`` or some confirmed slot ``s < t`` has
  ``x_is > 0`` and ``A_is = -1`` (the mask hides A only when the true debt was already
  0). Every belief then returns the point mass at debt 0.

Point beliefs (CE, PES, PERSIST) put all mass on one debt value and take availability
as 1 (PERSIST: the last revealed state) inside the window ``a_i <= tau < d_i`` and 0
outside it. At ``delta_A = 0`` a state revealed in column t overrides slot t for every
point belief: 0 if stuck (so no unit at t has value), 1 if available.

``HMMBelief`` is the exact Bayes posterior of the two-state chain (Z_0 stuck with
probability q_i, avail -> avail with ``p_stay``, stuck -> avail with ``r``) given the
revealed entries. Observations of the state are exact, so the filtered law of
``Z_c`` is a point mass at the last revealed state propagated forward (or the
prior propagated if nothing is revealed). The joint law of true debt and state over the
unconfirmed slots is the exact distribution a 2^|U_i| path enumeration would give; it
is computed here by a debt-by-state recursion over the same chain, with delivery
``y = min(x, remaining) * A`` in time order, so no path is enumerated twice. The tail
for ``tau >= t`` uses the two-state transition powers.

``p_stay`` and ``r`` are the tuning-seed means in ``PopulationParams``, worth ``PRIOR_ESS``
observations, plus this instance's pooled prior-chain counts, computed once in ``reset``
(POLICY_SPEC 3.2). The population mode's ``q_bar`` is the same Beta(alpha, beta) prior as
e1 updated with the pooled stuck count, so at M = 0 e1 and population coincide.
"""
from __future__ import annotations

import numpy as np

from papere.infoset import InformationSet, OracleView, StaticView, UNKNOWN

from .base import PopulationParams, PosteriorState

_MODES = ("e1", "population", "oracle")

PRIOR_ESS = 10.0
"""Effective sample size of the tuning-seed prior for the population level numbers.

``p_stay`` and ``r`` take their prior mean from the tuning-seed transition counts, each row
(avail, stuck) rescaled to ``PRIOR_ESS`` observations with its ratio kept; ``q_bar`` takes its
``q_bar`` does not use it (it is the Beta(alpha, beta) posterior mean). The
instance's own pooled prior-chain counts are then added, so the estimates equal the tuning
means exactly at M = 0 and are data-dominated once the instance has history (the r sweep
cells move r_hat toward their own r). The rule is identical for every HMM policy, so it
cannot favour the candidate. e1's alpha, beta are untouched.
"""


# --------------------------------------------------------------------------- helpers
def known_complete(view: InformationSet) -> np.ndarray:
    """Boolean [N]: the true debt is certainly 0 (``c_i = 0`` or a hidden-A command)."""
    done = view.confirmed_debt == 0
    ncols = min(view.t - view.delta_A + 1, view.t)
    if ncols > 0:
        hidden = (view.A_confirmed[:, :ncols] == UNKNOWN) & (view.x_past[:, :ncols] > 0)
        done = done | hidden.any(axis=1)
    return done


def unconfirmed_setpoint_sum(view: InformationSet) -> np.ndarray:
    """Sum over the unconfirmed slots ``t - delta_A < s < t`` of ``x_is`` (int64 [N])."""
    lo = max(view.t - view.delta_A + 1, 0)
    if lo >= view.t:
        return np.zeros(view.N, dtype=np.int64)
    return view.x_past[:, lo:view.t].sum(axis=1)


def last_revealed_state(view: InformationSet) -> tuple[np.ndarray, np.ndarray]:
    """(has [N] bool, state [N] int8) of the latest revealed entry of this event."""
    A = view.A_confirmed
    n = A.shape[0]
    if A.shape[1] == 0:
        return np.zeros(n, dtype=bool), np.zeros(n, dtype=np.int8)
    revealed = A >= 0
    has = revealed.any(axis=1)
    last = A.shape[1] - 1 - np.argmax(revealed[:, ::-1], axis=1)
    return has, A[np.arange(n), last]


def _point_state(view: InformationSet, debt: np.ndarray, p_av: np.ndarray, kmax: int,
                 horizon: int) -> PosteriorState:
    """PosteriorState of a point mass at ``debt`` with availability ``p_av`` [N, H]."""
    t = view.t
    ks = np.arange(1, kmax + 1)
    tail = (debt[:, None] >= ks[None, :]).astype(np.float64)
    pav = np.zeros((view.N, horizon), dtype=np.float64)
    pav[:, t:] = p_av[:, t:]
    tail_avail = tail[:, :, None] * pav[:, None, :]
    exp_debt = debt.astype(np.float64)
    return PosteriorState(t=t, tail=tail, tail_avail=tail_avail, p_avail=pav,
                          exp_debt=exp_debt, p_pos=tail[:, 0].copy(), point=True)


class _PointBelief:
    """Shared reset for the point beliefs."""

    name = "point"

    def __init__(self) -> None:
        self._ready = False

    def reset(self, static_view: StaticView, floored: np.ndarray | None = None,
              oracle: OracleView | None = None) -> None:
        self._N = static_view.N
        self._H = static_view.H
        self._kmax = int(static_view.E.max())
        tau = np.arange(static_view.H)[None, :]
        self._window = ((tau >= static_view.a[:, None])
                        & (tau < static_view.d[:, None])).astype(np.float64)
        self._ready = True

    def _check(self, view: InformationSet) -> None:
        if not self._ready:
            raise RuntimeError(f"{self.name}: reset() has not been called")
        if view.N != self._N or view.H != self._H:
            raise ValueError(f"{self.name}: view does not match the reset static view")

    def _debt(self, view: InformationSet) -> np.ndarray:
        raise NotImplementedError

    def _avail(self, view: InformationSet) -> np.ndarray:
        return self._window

    def compute(self, view: InformationSet) -> PosteriorState:
        self._check(view)
        debt = np.where(known_complete(view), 0, self._debt(view)).astype(np.int64)
        avail = self._avail(view)
        if view.delta_A == 0:
            # column t holds exact reveals from earlier re-dispatch rounds
            cur = view.A_confirmed[:, view.t]
            if (cur >= 0).any():
                avail = avail.copy()
                avail[:, view.t] = np.where(cur == 0, 0.0,
                                            np.where(cur == 1, 1.0, avail[:, view.t]))
        return _point_state(view, debt, avail, self._kmax, self._H)


class CEBelief(_PointBelief):
    """Certainty equivalence: unconfirmed setpoints delivered in full (floored at 0)."""

    name = "CE"

    def _debt(self, view: InformationSet) -> np.ndarray:
        return np.maximum(view.confirmed_debt - unconfirmed_setpoint_sum(view), 0)


class PESBelief(_PointBelief):
    """Pessimism: unconfirmed setpoints assumed failed; debt is the confirmed debt."""

    name = "PES"

    def _debt(self, view: InformationSet) -> np.ndarray:
        return view.confirmed_debt.astype(np.int64)


class PersistBelief(_PointBelief):
    """Persistence: unconfirmed setpoints delivered iff the last revealed state is available.

    With nothing revealed yet in this event the base belief (CE or PES) decides the debt
    and availability is 1 inside the window.
    """

    def __init__(self, base: str = "CE") -> None:
        super().__init__()
        if base not in ("CE", "PES"):
            raise ValueError("base must be 'CE' or 'PES'")
        self.base = base
        self.name = f"PERSIST-{base}"

    def _debt(self, view: InformationSet) -> np.ndarray:
        has, state = last_revealed_state(view)
        c = view.confirmed_debt.astype(np.int64)
        ce = np.maximum(c - unconfirmed_setpoint_sum(view), 0)
        base = ce if self.base == "CE" else c
        return np.where(has, np.where(state == 1, ce, c), base)

    def _avail(self, view: InformationSet) -> np.ndarray:
        has, state = last_revealed_state(view)
        up = np.where(has, (state == 1).astype(np.float64), 1.0)
        return self._window * up[:, None]


# ------------------------------------------------------------------------------ HMM
class HMMBelief:
    """Exact posterior of the two-state availability chain (POLICY_SPEC 2, 3.2).

    ``mode`` sets only the initial stuck probability ``q_i``: ``e1`` (Beta-Bernoulli on
    the participant's own prior-event stuck count), ``population`` (one pooled rate) or
    ``oracle`` (true ``q_i`` from ``OracleView``, given to ``reset`` as ``oracle=``).
    ``p_stay`` and ``r`` are the same population estimates in all modes. After ``reset``
    the numbers used are readable as ``q`` ([N], 0 for floored participants),
    ``p_stay`` and ``r``.
    """

    def __init__(self, params: PopulationParams, mode: str = "e1") -> None:
        if mode not in _MODES:
            raise ValueError(f"mode must be one of {_MODES}")
        self.params = params
        self.mode = mode
        self.name = f"HMM-{mode}"
        self._ready = False

    # ---- setup -------------------------------------------------------------
    def reset(self, static_view: StaticView, floored: np.ndarray | None = None,
              oracle: OracleView | None = None) -> None:
        p = self.params
        N, H, M = static_view.N, static_view.H, static_view.M
        pa = static_view.prior_A
        if M > 0 and H > 1:
            a0, a1 = pa[:, :, :-1] == 1, pa[:, :, 1:] == 1
            n_aa = float(np.sum(a0 & a1))
            n_as = float(np.sum(a0 & ~a1))
            n_sa = float(np.sum(~a0 & a1))
            n_ss = float(np.sum(~a0 & ~a1))
        else:
            n_aa = n_as = n_sa = n_ss = 0.0
        row_a, row_s = p.n_aa + p.n_as, p.n_sa + p.n_ss
        if row_a <= 0 or row_s <= 0 or p.q_bar_total <= 0:
            raise ValueError("no transition counts: PopulationParams has empty pseudo-counts")
        self.p_stay = (PRIOR_ESS * p.n_aa / row_a + n_aa) / (PRIOR_ESS + n_aa + n_as)
        self.r = (PRIOR_ESS * p.n_sa / row_s + n_sa) / (PRIOR_ESS + n_sa + n_ss)

        stuck_i = static_view.prior_stuck.sum(axis=1).astype(np.float64)
        if self.mode == "e1":
            q = (p.alpha + stuck_i) / (p.alpha + p.beta + M)
        elif self.mode == "population":
            q_bar = (p.alpha + stuck_i.sum()) / (p.alpha + p.beta + N * M)
            q = np.full(N, q_bar)
        else:
            if oracle is None:
                raise ValueError("HMMBelief(mode='oracle') needs reset(..., oracle=OracleView)")
            q = np.array(oracle.q, dtype=np.float64)
            if q.shape != (N,):
                raise ValueError("oracle q must have shape [N]")
        q = np.clip(q, 0.0, 1.0)
        if floored is not None:
            fl = np.asarray(floored, dtype=bool)
            if fl.shape != (N,):
                raise ValueError("floored must have shape [N]")
            q = np.where(fl, 0.0, q)
        self.q = q

        # P(Z_{tau+h} = avail | Z_tau = avail / stuck), h = 0..H
        pa_a = np.empty(H + 1)
        pa_s = np.empty(H + 1)
        pa_a[0], pa_s[0] = 1.0, 0.0
        for h in range(H):
            pa_a[h + 1] = pa_a[h] * self.p_stay + (1.0 - pa_a[h]) * self.r
            pa_s[h + 1] = pa_s[h] * self.p_stay + (1.0 - pa_s[h]) * self.r
        self._pa_a, self._pa_s = pa_a, pa_s
        self._N, self._H = N, H
        self._kmax = int(static_view.E.max())
        self._dgrid = np.arange(self._kmax + 1)
        self._rowoff = np.arange(N)[:, None] * (self._kmax + 1)
        self._rows = np.arange(N)
        self._ready = True

    # ---- exact filter + debt recursion ---------------------------------------
    def compute(self, view: InformationSet) -> PosteriorState:
        if not self._ready:
            raise RuntimeError(f"{self.name}: reset() has not been called")
        N, H, K = self._N, self._H, self._kmax
        if view.N != N or view.H != H:
            raise ValueError(f"{self.name}: view does not match the reset static view")
        t = view.t
        c = t - view.delta_A
        q, ps, r = self.q, self.p_stay, self.r
        cdebt = np.asarray(view.confirmed_debt, dtype=np.int64)
        rows = self._rows

        Ja = np.zeros((N, K + 1))
        Js = np.zeros((N, K + 1))
        if c >= 0:
            # filtered law of Z_c: exact observation propagated, or the prior propagated
            has, state = last_revealed_state(view)
            nc = view.A_confirmed.shape[1]
            if nc:
                rev = view.A_confirmed >= 0
                last_idx = nc - 1 - np.argmax(rev[:, ::-1], axis=1)
            else:
                last_idx = np.zeros(N, dtype=np.int64)
            lag = np.where(has, c - last_idx, 0)
            from_obs = np.where(state == 1, self._pa_a[lag], self._pa_s[lag])
            prior_c = (1.0 - q) * self._pa_a[c] + q * self._pa_s[c]
            pa_c = np.where(has, from_obs, prior_c)
            Ja[rows, cdebt] = pa_c
            Js[rows, cdebt] = 1.0 - pa_c
            s_first = c + 1
        else:
            Ja[rows, cdebt] = 1.0       # no state yet; slot 0 draws from the initial law
            s_first = 0

        x_past = view.x_past
        for s in range(s_first, t + 1):
            if s == 0:
                marg = Ja + Js
                Ja = marg * (1.0 - q)[:, None]
                Js = marg * q[:, None]
            else:
                Ja, Js = Ja * ps + Js * r, Ja * (1.0 - ps) + Js * (1.0 - r)
            if s < t:
                xs = x_past[:, s]
                if xs.any():
                    tgt = np.maximum(self._dgrid[None, :] - xs[:, None], 0)
                    idx = (self._rowoff + tgt).ravel()
                    Ja = np.bincount(idx, weights=Ja.ravel(),
                                     minlength=N * (K + 1)).reshape(N, K + 1)

        kc = known_complete(view)
        if kc.any():
            for J in (Ja, Js):
                tot = J[kc].sum(axis=1)
                J[kc] = 0.0
                J[kc, 0] = tot

        # tails at slot t, split by the state at t
        TA = np.cumsum(Ja[:, ::-1], axis=1)[:, ::-1][:, 1:]
        TS = np.cumsum(Js[:, ::-1], axis=1)[:, ::-1][:, 1:]
        h = np.arange(H - t)
        pa_h, ps_h = self._pa_a[h], self._pa_s[h]
        tail_avail = np.zeros((N, K, H))
        tail_avail[:, :, t:] = TA[:, :, None] * pa_h + TS[:, :, None] * ps_h
        p_avail = np.zeros((N, H))
        p_t = Ja.sum(axis=1)
        p_avail[:, t:] = p_t[:, None] * pa_h + (1.0 - p_t)[:, None] * ps_h
        tail = TA + TS
        return PosteriorState(t=t, tail=tail, tail_avail=tail_avail, p_avail=p_avail,
                              exp_debt=tail.sum(axis=1), p_pos=tail[:, 0].copy(), point=False)
