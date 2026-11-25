"""Greedy expected-value hedge ranker (post hoc baseline, added 2026-11-02 at the referee's
request; docs/RANKER_POSTHOC.md). Outside the 17-family catalog of POLICY_SPEC 5: the catalog,
``posthoc.py`` and their tests are untouched, and ``RANKER_FAMILIES`` is passed to the runner
by ``scripts/run_posthoc_ranker.py``.

What the referee asked for: "a greedy expected-value hedge ranker (per-participant posterior,
no planning)". Greedy by value is optimal in Proposition 3's instance (hedges are unit items).

Policy (``GreedyEV``), at decision slot t
-----------------------------------------
* Belief. One ``PosteriorState`` per ``act`` call from the family's belief: HMM e1 (the same
  per-participant posterior as Targeted MPC, ``guarded_mpc_e1``), HMM population (the same
  pooled posterior as Shared-rate MPC, ``pop_mpc``) or CE (certainty equivalent).
* Candidates. Units (i, k), k = 1 .. P_i, of participants active now (``a_i <= t < d_i``)
  with ``tail[i, k] > VAL_EPS``. A participant believed complete has tail 0 and is never
  commanded. A participant revealed stuck in column t (delta_A = 0 re-dispatch) is worth 0 now
  and is not commanded.
* Value. Exactly what the planner gives that unit at tau = t:
  ``v = tail_avail[i, k, t] = P(debt_i >= k and Z_it = avail)``, plus, with knob gamma, the
  planner's correctability credit at tau = t: if ``t + max(delta_A, 1) < d_i`` and ``v > 0``,
  ``u = v + min(1, gamma * p_avail[i, t + dl]) * (tail[i, k] - v)`` (gamma = 0 removes it).
  Both come from ``MPCPolicy.value_grid`` with a one-slot horizon, so the code path is shared.
* Score. ``u - URGENT * (d_i - t) + noise + REVEAL * [revealed available in column t]`` with the
  constants of ``mpc.py``. The noise table ``U[0, TIE)`` of shape [N, 1, Kmax] is drawn from the
  policy rng once per slot (reused across that slot's re-dispatch rounds); consecutive units of
  i with identical values form one class and share the draw of the class's first unit, as the
  MPC's unit classes do.
* Fill. Units sorted by score, highest first; a unit is taken iff its score is positive, i has
  room under ``P_i`` and its group has room under ``max(0, view.setpoint_cap(g, m))`` (knob m).
  No look-ahead, no later slot, no LP.

Exactness. The per-participant rate rows nest inside the group cap rows (a laminar family), so
the feasible unit sets form a laminar matroid and the greedy fill is the exact optimum of the
one-slot problem. The policy therefore equals ``MPCPolicy(belief, W=1, m, k=0, gamma)`` decision
for decision, same tie table and all (tested in ``tests/test_ranker.py``); it is the guarded
MPC with its planning horizon cut to the current slot. The MPC tuning grids use W in
{2, 4, 8, 24}, so W = 1 was never a configuration of any catalog family.

Families (``RANKER_FAMILIES``)
------------------------------
* ``greedy_ev``      HMM e1;          grid m in {0, 1, 2} x gamma in {0, 0.5, 1, 2} (12).
* ``greedy_ev_pop``  HMM population;  same grid (12).
* ``greedy_ev_ce``   CE point belief; grid m in {0, 1, 2} (3): for a point belief with
  availability 1 in the window ``v = tail``, so the credit is 0 at every gamma.
Tuned on seeds 60000-60049 over all 22 F0-R cells with the runner's selection rule (well under
the 48-evaluation budget), frozen in ``results/TUNING_FROZEN_posthoc_ranker.json``.
"""
from __future__ import annotations

import numpy as np

from papere.infoset import InformationSet

from .base import Belief, Family, PopulationParams, PosteriorState
from .beliefs import CEBelief, HMMBelief
from .catalog import GAMMA_VALUES, M_VALUES, _grid
from .mpc import REVEAL, URGENT, VAL_EPS, MPCPolicy, current_column


class GreedyEV(MPCPolicy):
    """Greedy expected-value ranker over a ``Belief``: the one-slot planning value, filled
    greedily under ``P_i`` and the group caps. See the module docstring."""

    def __init__(self, belief: Belief, m: float = 0.0, gamma: float = 0.0,
                 name: str | None = None, privileged: bool = False) -> None:
        bname = getattr(belief, "name", "belief")
        super().__init__(belief, W=1, m=m, k=0, gamma=gamma, privileged=privileged,
                         name=name if name is not None
                         else f"GREEDY[{bname}]_m{float(m):g}_g{float(gamma):g}")
        self.last_scores: np.ndarray | None = None   # [N, Kmax] scores of the last act (-inf: not offered)

    def decide(self, view: InformationSet, post: PosteriorState) -> np.ndarray:
        N, t = self._N, view.t
        t_end = t + 1
        x = np.zeros(N, dtype=np.int64)
        self.last_plan = np.zeros((N, 1), dtype=np.int64)
        tail = np.asarray(post.tail, dtype=np.float64)
        Kmax = tail.shape[1]
        noise = self._tie_table(view, 1, Kmax)[:, 0, :]                 # [N, Kmax]
        col = current_column(view)
        blocked = np.zeros(N, bool) if col is None else (col == 0)
        avail_now = np.zeros(N, bool) if col is None else (col == 1)

        lo = np.maximum(t, self._a)
        active = (self._a <= t) & (t < self._d)
        n_units = (tail > VAL_EPS).sum(axis=1)
        Ki = np.where(active, np.minimum(n_units, self._P), 0)
        self.last_scores = np.full((N, Kmax), -np.inf)
        if not (Ki > 0).any():
            return x
        vg = self.value_grid(post, t, t_end, lo, blocked)[:, :, 0]      # [N, Kmax]
        vg[blocked, :] = 0.0

        # classes of consecutive units with identical value and tail (as in MPCPolicy.decide);
        # every unit uses the value and the noise of its class's first unit
        if Kmax > 1:
            brk = (np.abs(np.diff(vg, axis=1)) > VAL_EPS) | (np.abs(np.diff(tail, axis=1)) > VAL_EPS)
            starts = np.concatenate([np.ones((N, 1), bool), brk], axis=1)
        else:
            starts = np.ones((N, 1), bool)
        first_k = np.maximum.accumulate(np.where(starts, np.arange(Kmax)[None, :], 0), axis=1)
        rows = np.arange(N)[:, None]
        val = vg[rows, first_k]
        score = (val - URGENT * (self._d - t)[:, None] + noise[rows, first_k]
                 + REVEAL * avail_now[:, None])
        offered = (np.arange(Kmax)[None, :] < Ki[:, None]) & (val > VAL_EPS) & (score > 0.0)
        self.last_scores = np.where(offered, score, -np.inf)

        ii, kk = np.nonzero(offered)
        order = np.argsort(-score[ii, kk], kind="stable")
        caps = self.caps(view, t_end)[:, 0]
        rem = caps.copy()
        for j in order:
            i = ii[j]
            g = self._group[i]
            if x[i] < self._P[i] and rem[g] > 0:
                x[i] += 1
                rem[g] -= 1
        self.last_plan = x[:, None].copy()
        return self._clip(x, caps, view)


# --------------------------------------------------------------------------- families
GRID_M_GAMMA = _grid(m=M_VALUES, gamma=GAMMA_VALUES)
GRID_M = _grid(m=M_VALUES)
DEFAULT_GREEDY = {"m": 0, "gamma": 1.0}
DEFAULT_GREEDY_CE = {"m": 0}


def _make_greedy(mode: str, name: str):
    def make(cfg: dict, params: PopulationParams):
        return GreedyEV(HMMBelief(params, mode), cfg["m"], cfg["gamma"], name=name)
    return make


def _make_greedy_ce(cfg: dict, params: PopulationParams):
    return GreedyEV(CEBelief(), cfg["m"], 0.0, name="greedy_ev_ce")


RANKER_FAMILIES: list[Family] = [
    Family(name="greedy_ev", kind="per_participant", grid=GRID_M_GAMMA,
           default=dict(DEFAULT_GREEDY), make=_make_greedy("e1", "greedy_ev")),
    Family(name="greedy_ev_pop", kind="oblivious", grid=GRID_M_GAMMA,
           default=dict(DEFAULT_GREEDY), make=_make_greedy("population", "greedy_ev_pop")),
    Family(name="greedy_ev_ce", kind="oblivious", grid=GRID_M,
           default=dict(DEFAULT_GREEDY_CE), make=_make_greedy_ce),
]
