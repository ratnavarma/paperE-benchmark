"""Shared policy interfaces (POLICY_SPEC Sections 1-3). Types only; no policy logic here."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Protocol

import numpy as np

from papere.infoset import InformationSet, StaticView
from papere.sim import Policy


@dataclass(frozen=True)
class PopulationParams:
    """Population-level parameters fitted on tuning seeds 60000-60049 (POLICY_SPEC 3.1).

    Transition counts are rescaled to an effective sample size (beliefs.PRIOR_ESS) and then
    combined with the instance's own pooled prior-chain counts (POLICY_SPEC 3.2).
    """

    alpha: float          # beta-binomial prior on the per-participant stuck probability
    beta: float
    q_bar_stuck: float    # pooled stuck count on tuning seeds
    q_bar_total: float    # pooled number of (participant, event) pairs on tuning seeds
    n_aa: float           # avail -> avail transitions
    n_as: float           # avail -> stuck
    n_ss: float           # stuck -> stuck
    n_sa: float           # stuck -> avail


@dataclass(frozen=True)
class PosteriorState:
    """Belief over remaining debt and availability at one decision (POLICY_SPEC 2).

    Arrays are indexed [i, k-1] for k = 1..Kmax and [.., tau] for absolute slots tau;
    entries for tau < t are 0.
    """

    t: int
    tail: np.ndarray        # [N, Kmax]      P(debt_i >= k)
    tail_avail: np.ndarray  # [N, Kmax, H]   P(debt_i >= k and Z_i,tau = avail)
    p_avail: np.ndarray     # [N, H]         P(Z_i,tau = avail)
    exp_debt: np.ndarray    # [N]
    p_pos: np.ndarray       # [N]            P(debt_i >= 1)
    point: bool             # True for the CE, PES and PERSIST point beliefs


class Belief(Protocol):
    """Maps a view to a PosteriorState. Set up once per run with ``reset``."""

    name: str

    def reset(self, static_view: StaticView, floored: np.ndarray | None = None,
              oracle=None) -> None: ...

    def compute(self, view: InformationSet) -> PosteriorState: ...


@dataclass(frozen=True)
class Family:
    """One comparator family and its tuning grid (POLICY_SPEC 5 and 7).

    ``kind`` is 'oblivious', 'per_participant', 'candidate' or 'reference'. ``grid`` holds
    the 48 configurations of a tunable family, or just ``(default,)``. A family with
    ``tuned_from`` set is not tuned and uses that family's frozen configuration per cell.
    """

    name: str
    kind: str
    grid: tuple
    default: dict
    make: Callable[[dict, PopulationParams], Policy]
    tuned_from: str | None = None

    @property
    def tunable(self) -> bool:
        return self.tuned_from is None and len(self.grid) > 1
