"""Receding-horizon MPC over a debt posterior (POLICY_SPEC Section 6).

At decision slot ``t`` the policy asks its belief for a ``PosteriorState`` (once per
``act`` call, so once per re-dispatch round at delta_A = 0), solves one integer plan over
the slots ``T = t .. min(H, t + W) - 1`` and executes the plan's first slot.

Planning model
--------------
* Windows. Participant i may be planned at ``lo_i = max(t, a_i) <= tau < d'_i`` with
  ``d'_i = min(d_i, max(lo_i + 1, d_i - k))``: deadline tightening by ``k`` slots
  (MPC-CE / MPC-PES; the guarded MPC uses ``k = 0``), clipped so that a participant
  active now keeps at least the current slot and a future participant at least its
  release slot (what it gets once it is active).
* Caps. Group g at the current slot: ``max(0, view.setpoint_cap(g, m))``. Later slots:
  the same last-value forecast ``view.base_forecast`` (the last observed base load under
  the delta_b lag, ``b_mean[g, t]`` before any is observed), i.e.
  ``max(0, floor(L[g, tau] - b_hat[g] - m + 1e-9))``. Rate limit ``P_i`` per slot.
* Value. The k-th unit to i at slot tau is worth the running minimum

      v(i, k, tau) = min over lo_i <= tau' <= tau of tail_avail[i, k, tau'],

  with ``tail_avail[i, k, tau] = P(debt_i >= k and Z_i,tau = avail)``. The running
  minimum makes every unit's value non-increasing in tau, so a unit is never worth more
  for waiting. Without it, a posterior whose forecast availability rises over the horizon
  (an HMM participant that may be stuck and is forecast to return) makes later slots look
  better and the plan drifts units to the last, uncorrectable slots, even with spare cap
  now (tuning seed 60001, rho = 0.7, delta_A = 2, t = 0: the population MPC commanded 0
  units with cap 14 and 10 participants active). The rule is the same for every belief;
  for point beliefs (CE, PES) the value is constant inside the window, so they are
  unchanged. A participant revealed stuck in column t at delta_A = 0 cannot deliver now:
  its running minimum starts at t + 1 and its slot-t units are not offered,
  whatever the belief reports for slot t. For a fixed
  slot the value is non-increasing in k (concave per participant), so the unit-level
  arcs are exact for this planning model; for a point belief the plan value is
  ``min(debt, planned units)``. Units worth less than ``VAL_EPS = 1e-12`` are not
  offered, so a participant believed complete is never commanded.
* Secondary preferences (constants below; log them in OPEN_QUESTIONS):
  ``EARLY = 1e-5`` per slot of delay per unit (a unit at tau loses ``EARLY (tau - t)``:
  among equal-value plans the earlier delivery wins) and ``URGENT = 1e-5`` per slot of
  deadline per unit (a unit of i loses ``URGENT (d_i - t)``: among equal values the more
  urgent participant wins; it matters for short W, where an urgent participant and one
  whose window runs past the horizon otherwise look identical). Together at most
  ``2e-5 H`` (4.8e-4 at H = 24). ``REVEAL = 1e-3`` per unit for a slot-t unit of a
  participant revealed *available* in column t during re-dispatch (delta_A = 0). It is a
  tie preference, equal for every belief: it exceeds every tie-break and secondary
  preference, so among equal-value plans a revealed-available command is kept (as in
  the rule families, OPEN_QUESTIONS 46). It is not a commitment: under HMM beliefs the
  revealed information changes the posterior, and the planner may reallocate a
  revealed-available participant's unit when the plan value gained exceeds REVEAL per
  unit kept. Point beliefs (CE, PES) never do (tested).
* Ties. Each (i, tau, unit) arc gets an independent ``U[0, TIE)`` perturbation,
  ``TIE = 1e-6``, from the policy rng, never an index order. The table is drawn once per
  slot and reused across the re-dispatch rounds of that slot, so a later round re-solves
  the same tie-broken problem with only the revealed information changed. HiGHS dual
  simplex runs at feasibility tolerances of 1e-10 so the perturbation, not pivoting
  order, decides ties.

Guard: correctability credit (a tuned heuristic; scale gamma, gamma = 0 removes it)
---------------------------------------------------------------------------------
A unit planned at slot tau whose failure would be seen at ``tau + dl``, ``dl =
max(delta_A, 1)``, while i's window is still open (``tau + dl < d_i``, the lag rule of
OPEN_QUESTIONS 20 and MECHANISM Proposition 2) gets a credit on top of its base value v:

    u(i, k, tau) = v + min(1, gamma * p_avail[i, tau + dl]) * (tail[i, k] - v);
    no credit when tau + dl >= d_i or when v = 0 (a unit that cannot deliver there);
    planning value = running minimum of u over lo_i <= tau' <= tau.

The final running minimum keeps the total value non-increasing in tau too: the credit
uses ``p_avail`` at the retry slot, which rises with tau for a possibly stuck participant,
so without it the credit alone would reintroduce waiting.

``tail - v`` bounds the probability that the unit is owed but fails. The credit pulls
uncertain participants' units into slots where a failure can still be seen and retried and
leaves the uncorrectable end of the window as the hedge of last resort. It is a heuristic,
not a recourse model: it uses the marginal ``p_avail[i, tau + dl]`` rather than
P(avail at tau + dl | stuck at tau), it reserves no capacity for the retry, and the
implied retry can overlap a unit the plan already places at ``tau + dl``. Its scale gamma
is tuned per cell over {0, 0.5, 1, 2} (POLICY_SPEC 5). Reviewer's observation: at
delta_A = 0 with gamma = 0 the informed beliefs do slightly worse than CE (population
minus e1 = -0.34 +- 0.15 kWh per 100 on the tuning seeds), and the difference vanishes at
gamma = 1; per-cell tuning over gamma decides. Properties that hold exactly: the
value never exceeds ``tail[i, k]``; gamma = 0 removes the credit (the code path is
skipped); for point beliefs with availability 1 inside the window (CE, PES) ``v =
tail`` there, so the credit is 0 at every gamma and NC2 holds for every gamma; on I_K
(H = 2, delta_A >= 2) no slot is correctable, so Propositions 1 and 3 are untouched. It
reads only the ``PosteriorState`` (``tail``, ``tail_avail``, ``p_avail``) and the view
(``delta_A``, deadlines). A reservation guard (hold ``round(gamma * sd(debt_i))`` units
of cap in i's correctable suffix) was tried first and dropped: it raised R_avoid in
pilot runs because reserved future capacity pushed other units into the current slot and
displaced the hedges it was meant to protect.

Integrality
-----------
Rows: per (i, tau) ``sum y <= P_i``; per (g, tau) ``sum y <= C``; per (i, unit class)
``sum_tau y <= multiplicity``. Consecutive units whose value rows over the plan horizon
(and tails) are identical, e.g. every surely-owed unit, form one class: merging them
leaves the optimum unchanged and keeps the LP small (about 300 arcs at t = 0 for N = 30).
Every arc lies in one row of the laminar family {(i, tau)} within {(g, tau)} and in one
row of the partition into classes; the union of two laminar families is totally
unimodular, so every basic optimum is integral with integer caps. The simplex vertex is
rounded and checked; should a vertex ever come back fractional, the same problem is
re-solved by ``scipy.optimize.milp`` with integrality (counted in ``FALLBACKS``). A
final clip enforces windows, P_i and the group caps regardless.
"""
from __future__ import annotations

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, linprog, milp
from scipy.sparse import csr_matrix

from papere.infoset import InformationSet, OracleView, StaticView

from .base import Belief, PosteriorState

EARLY = 1e-5          # earliness preference per slot of delay, per unit
URGENT = 1e-5         # earliest-deadline preference per slot of deadline, per unit
REVEAL = 1e-3         # slot-t preference for participants revealed available (delta_A = 0)
TIE = 1e-6            # tie-break perturbation scale per unit (U[0, TIE))
VAL_EPS = 1e-12       # units worth less than this are not offered
_HIGHS_OPTS = {"dual_feasibility_tolerance": 1e-10, "primal_feasibility_tolerance": 1e-10,
               "presolve": True}
FALLBACKS = {"milp": 0}   # fractional LP vertices re-solved as a MILP (read by tests)


def current_column(view: InformationSet) -> np.ndarray | None:
    """Revealed availability of slot t (1/0/-1) during re-dispatch at delta_A = 0."""
    if view.delta_A == 0 and view.A_confirmed.shape[1] == view.t + 1:
        return np.asarray(view.A_confirmed[:, view.t])
    return None


class MPCPolicy:
    """Receding-horizon integer MPC over a ``Belief`` (POLICY_SPEC 6). See module doc."""

    def __init__(self, belief: Belief, W: int, m: float, k: int = 0, gamma: float = 0.0,
                 name: str | None = None, privileged: bool = False) -> None:
        if int(W) < 1:
            raise ValueError("W must be >= 1")
        if int(k) < 0 or float(m) < 0 or float(gamma) < 0:
            raise ValueError("m, k and gamma must be non-negative")
        self.belief = belief
        self.W = int(W)
        self.m = float(m)
        self.k = int(k)
        self.gamma = float(gamma)
        self.privileged = bool(privileged)
        bname = getattr(belief, "name", "belief")
        self.name = name if name is not None else (
            f"MPC[{bname}]_W{self.W}_m{self.m:g}_k{self.k}_g{self.gamma:g}")
        self._ready = False
        self._noise_t = -1
        self._noise = None
        self.last_plan: np.ndarray | None = None    # [N, len(T)] integer plan of last act

    # ---- Policy protocol ------------------------------------------------------
    def reset(self, static_view: StaticView, rng: np.random.Generator,
              oracle: OracleView | None = None) -> None:
        self.rng = rng
        sv = static_view
        self._N, self._H, self._G = sv.N, sv.H, sv.G
        self._a = np.asarray(sv.a, dtype=np.int64)
        self._d = np.asarray(sv.d, dtype=np.int64)
        self._P = np.asarray(sv.P, dtype=np.int64)
        self._group = np.asarray(sv.group, dtype=np.int64)
        self._L = np.asarray(sv.L, dtype=np.float64)
        self._dA = sv.delta_A
        self._noise_t = -1
        self._noise = None
        self.belief.reset(sv, self.floor_mask(sv), oracle=oracle)
        self._ready = True

    def floor_mask(self, static_view: StaticView) -> np.ndarray | None:
        return None

    def act(self, view: InformationSet) -> np.ndarray:
        if not self._ready:
            raise RuntimeError(f"{self.name}: reset() has not been called")
        post = self.belief.compute(view)
        return self.decide(view, post)

    # ---- planning -------------------------------------------------------------
    def caps(self, view: InformationSet, t_end: int) -> np.ndarray:
        """Integer caps [G, t_end - t]: current slot from ``setpoint_caps(m)``, later slots
        from the same last-value forecast; clipped at 0."""
        t = view.t
        cap = np.floor(self._L[:, t:t_end] - np.asarray(view.base_forecast)[:, None]
                       - self.m + 1e-9).astype(np.int64)
        cap[:, 0] = view.setpoint_caps(self.m)
        return np.maximum(cap, 0)

    @staticmethod
    def _running_min(raw: np.ndarray, before: np.ndarray) -> np.ndarray:
        """Running minimum over tau of raw [N, K, T], starting after the ``before`` slots
        (which keep their raw values)."""
        tmp = np.where(before[:, None, :], np.inf, raw)
        return np.where(before[:, None, :], raw, np.minimum.accumulate(tmp, axis=2))

    def _before(self, t: int, T: int, lo: np.ndarray, blocked: np.ndarray) -> np.ndarray:
        start = np.maximum(lo - t, 0) + blocked.astype(np.int64)        # first slot in the min
        return np.arange(T)[None, :] < start[:, None]                   # [N, T]

    def base_values(self, post: PosteriorState, t: int, t_end: int, lo: np.ndarray,
                    blocked: np.ndarray) -> np.ndarray:
        """Running-minimum base values v [N, Kmax, t_end - t] (module doc, 'Value')."""
        raw = np.asarray(post.tail_avail, dtype=np.float64)[:, :, t:t_end]
        return self._running_min(raw, self._before(t, t_end - t, lo, blocked))

    def value_grid(self, post: PosteriorState, t: int, t_end: int, lo: np.ndarray,
                   blocked: np.ndarray) -> np.ndarray:
        """Planning values [N, Kmax, t_end - t]: base value plus guard credit, then the
        running minimum again so the total is non-increasing in tau as well."""
        before = self._before(t, t_end - t, lo, blocked)
        raw = np.asarray(post.tail_avail, dtype=np.float64)[:, :, t:t_end]
        vb = self._running_min(raw, before)
        if self.gamma <= 0.0:
            return vb
        tau = np.arange(t, t_end)
        dl = max(self._dA, 1)
        corr = ((tau[None, :] + dl) < self._d[:, None]) & ~before       # [N, T]
        pr = np.asarray(post.p_avail)[:, np.minimum(tau + dl, self._H - 1)]
        tail = np.asarray(post.tail, dtype=np.float64)
        owed_fail = np.where(vb > VAL_EPS, np.maximum(tail[:, :, None] - vb, 0.0), 0.0)
        credit = (np.minimum(self.gamma * pr, 1.0) * corr)[:, None, :] * owed_fail
        return self._running_min(vb + credit, before)

    def _tie_table(self, view: InformationSet, T: int, Kmax: int) -> np.ndarray:
        """Tie-break table [N, W, Kmax]: drawn once per slot, reused across its rounds."""
        if self._noise is None or self._noise_t != view.t or view.redispatch_round == 0:
            self._noise = self.rng.random((self._N, self.W, Kmax)) * TIE
            self._noise_t = view.t
        return self._noise

    def decide(self, view: InformationSet, post: PosteriorState) -> np.ndarray:
        """Solve the plan for ``post`` at ``view.t`` and return the first slot's setpoints."""
        N, t = self._N, view.t
        t_end = min(self._H, t + self.W)
        T = t_end - t
        x_out = np.zeros(N, dtype=np.int64)
        self.last_plan = np.zeros((N, T), dtype=np.int64)
        tail = np.asarray(post.tail, dtype=np.float64)
        Kmax = tail.shape[1]
        noise_tab = self._tie_table(view, T, Kmax)
        col = current_column(view)
        blocked = np.zeros(N, bool) if col is None else (col == 0)
        avail_now = np.zeros(N, bool) if col is None else (col == 1)

        start = np.maximum(t, self._a)
        dprime = np.minimum(self._d, np.maximum(start + 1, self._d - self.k))
        lo = start
        hi = np.minimum(dprime, t_end)
        ns = np.maximum(hi - lo, 0)
        n_units = (tail > VAL_EPS).sum(axis=1)
        Ki = np.where(ns > 0, np.minimum(n_units, self._P * ns), 0)
        elig = np.flatnonzero(Ki > 0)
        if elig.size == 0:
            return x_out
        ne = elig.size
        vg = self.value_grid(post, t, t_end, lo, blocked)              # [N, Kmax, T]
        vg[blocked, :, 0] = 0.0          # revealed stuck in column t: cannot deliver now

        # ---- unit classes: consecutive units with identical value rows are merged ----
        if Kmax > 1:
            sub = vg[elig]
            brk = (np.abs(np.diff(sub, axis=1)).max(axis=2) > VAL_EPS) \
                | (np.abs(np.diff(tail[elig], axis=1)) > VAL_EPS)        # [E, Kmax-1]
            cls_of_k = np.concatenate([np.zeros((ne, 1), dtype=np.int64),
                                       np.cumsum(brk, axis=1)], axis=1)  # [E, Kmax]
        else:
            cls_of_k = np.zeros((ne, 1), dtype=np.int64)
        K_e = Ki[elig]
        G_e = cls_of_k[np.arange(ne), K_e - 1] + 1                        # classes per i
        Gmax = int(G_e.max())
        inside = np.arange(Kmax)[None, :] < K_e[:, None]
        er = np.broadcast_to(np.arange(ne)[:, None], (ne, Kmax))[inside]
        ck = cls_of_k[inside]
        mult = np.zeros((ne, Gmax), dtype=np.int64)
        np.add.at(mult, (er, ck), 1)
        first_k = np.full((ne, Gmax), Kmax, dtype=np.int64)
        np.minimum.at(first_k, (er, ck), np.broadcast_to(np.arange(Kmax), (ne, Kmax))[inside])

        # ---- unit arcs y[i, tau, class] ----------------------------------------------
        ns_e, lo_e = ns[elig], lo[elig]
        cnt = ns_e * G_e
        tot = int(cnt.sum())
        ei = np.repeat(np.arange(ne), cnt)
        off = np.arange(tot) - np.repeat(np.cumsum(cnt) - cnt, cnt)
        Gr = np.repeat(G_e, cnt)
        tau = np.repeat(lo_e, cnt) + off // Gr
        kk = off % Gr                                     # class index within participant
        ii = elig[ei]
        kf = first_k[ei, kk]
        base_val = vg[ii, kf, tau - t]
        keep = base_val > VAL_EPS
        ei, ii, tau, kk, kf, base_val = (a[keep] for a in (ei, ii, tau, kk, kf, base_val))
        ny = ii.size
        if ny == 0:
            return x_out
        cy = (base_val - EARLY * (tau - t)
              - URGENT * (self._d[ii] - t) + noise_tab[ii, tau - t, kf]
              + REVEAL * ((tau == t) & avail_now[ii]))

        # ---- rows: (i, tau) | (g, tau) | (i, class) ----------------------------------
        it_base = np.zeros(N, dtype=np.int64)
        it_base[elig] = np.cumsum(ns_e) - ns_e
        n_it = int(ns_e.sum())
        n_gt = self._G * T
        ik_base = np.cumsum(G_e) - G_e
        n_ik = int(G_e.sum())
        rr = np.concatenate([it_base[ii] + (tau - lo[ii]),
                             n_it + self._group[ii] * T + (tau - t),
                             n_it + n_gt + ik_base[ei] + kk])
        cc = np.tile(np.arange(ny), 3)
        n_rows = n_it + n_gt + n_ik
        A = csr_matrix((np.ones(rr.size), (rr, cc)), shape=(n_rows, ny))
        caps = self.caps(view, t_end)
        b = np.concatenate([self._P[np.repeat(elig, ns_e)].astype(np.float64),
                            caps.ravel().astype(np.float64),
                            mult[np.arange(Gmax)[None, :] < G_e[:, None]].astype(np.float64)])
        ub = np.minimum(mult[ei, kk], self._P[ii]).astype(np.float64)
        yr = self._solve(-cy, A, b, ub, t)
        reveal_term = REVEAL * ((tau == t) & avail_now[ii])
        self.last_objective = float(((cy - reveal_term) * yr).sum())  # without REVEAL
        plan = np.zeros((N, T), dtype=np.int64)
        np.add.at(plan, (ii, tau - t), yr.astype(np.int64))
        self.last_plan = plan
        return self._clip(plan[:, 0], caps[:, 0], view)

    # ---- helpers ----------------------------------------------------------------
    def _solve(self, c: np.ndarray, A, b: np.ndarray, ub: np.ndarray, t: int) -> np.ndarray:
        """LP vertex (integral by total unimodularity); MILP fallback if it is not."""
        res = linprog(c, A_ub=A, b_ub=b, bounds=np.column_stack([np.zeros(c.size), ub]),
                      method="highs-ds", options=_HIGHS_OPTS)
        if res.status != 0 or res.x is None:
            raise RuntimeError(f"{self.name}: plan LP failed at t={t}: {res.message}")
        y = np.asarray(res.x)
        yr = np.rint(y)
        if np.abs(y - yr).max(initial=0.0) <= 1e-6:
            return yr
        FALLBACKS["milp"] += 1
        res = milp(c, constraints=LinearConstraint(A, -np.inf, b),
                   bounds=Bounds(np.zeros(c.size), ub), integrality=np.ones(c.size))
        if res.status != 0 or res.x is None:
            raise RuntimeError(f"{self.name}: plan MILP failed at t={t}: {res.message}")
        return np.rint(res.x)

    def _clip(self, x: np.ndarray, cap0: np.ndarray, view: InformationSet) -> np.ndarray:
        """Safety net: windows, P_i and group caps (never binds for a correct vertex)."""
        x = np.minimum(np.maximum(x, 0), self._P)
        x = np.where(view.active, x, 0).astype(np.int64)
        for g in range(self._G):
            idx = np.flatnonzero((self._group == g) & (x > 0))
            excess = int(x[idx].sum()) - int(cap0[g])
            while excess > 0 and idx.size:
                j = idx[self.rng.integers(idx.size)]
                x[j] -= 1
                excess -= 1
                idx = np.flatnonzero((self._group == g) & (x > 0))
        return x


# ---- convenience constructors --------------------------------------------------------
def _beliefs():
    from . import beliefs as _b       # deferred import: keeps mpc importable on its own
    return _b


def mpc_ce(W: int, m: float, k: int, name: str | None = None) -> MPCPolicy:
    """MPC-CE: certainty-equivalent belief, deadline tightening k, no guard."""
    return MPCPolicy(_beliefs().CEBelief(), W, m, k=k, gamma=0.0,
                     name=name if name is not None else f"MPC-CE_W{W}_m{m:g}_k{k}")


def mpc_pes(W: int, m: float, k: int, name: str | None = None) -> MPCPolicy:
    """MPC-PES: pessimistic belief, deadline tightening k, no guard."""
    return MPCPolicy(_beliefs().PESBelief(), W, m, k=k, gamma=0.0,
                     name=name if name is not None else f"MPC-PES_W{W}_m{m:g}_k{k}")


def guarded_mpc(belief: Belief, W: int, m: float, gamma: float, name: str | None = None,
                privileged: bool = False) -> MPCPolicy:
    """Guarded MPC (k = 0) with the correctability guard of scale gamma."""
    bname = getattr(belief, "name", "belief")
    return MPCPolicy(belief, W, m, k=0, gamma=gamma, privileged=privileged,
                     name=name if name is not None
                     else f"GMPC[{bname}]_W{W}_m{m:g}_g{gamma:g}")
