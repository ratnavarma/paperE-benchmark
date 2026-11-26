"""Adaptive Conformal Quantile Base-Load Headroom Guard for C37 (HedgeCap).

Maintains a strictly causal rolling window ``W_t`` of matured lag-``delta_b``
base-load residuals ``r_s = b_{g,s} - b_hat_{g, s | s - 1 - delta_b}`` for
``s <= t - 1 - delta_b`` (zero information leakage — reads ONLY public
``InformationSet`` attributes), updates the miscoverage target ``alpha_t`` via
Adaptive Conformal Inference (ACI), and computes the quantile safety margin:

    alpha_t <- clip(alpha_{t-1} + eta * (alpha_viol - I{ell_{g,s} > L_{g,s}}),
                    alpha_min, alpha_max)
    m_t(delta_b, alpha_t) = max(0, Q_{1 - alpha_t}({r_s}_{s in W_t}))
    C_{g,t} = max(0, floor(L_{g,t} - b_hat_{g,t} - m_t(delta_b, alpha_t)))

Decouples physical base-load overload risk (``delta_b``) from silent-actuation
hedging (``delta_A``) without modifying ``InformationSet``, ``sim.py``, or
``policies/mpc.py``.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Iterable, Literal

import numpy as np

from papere.fit import load_population_params
from papere.generator import generate_f0r
from papere.infoset import InformationSet, OracleView, StaticView
from papere.instance import Cell
from papere.ledger import evaluate
from papere.policies.base import Belief, PopulationParams
from papere.policies.beliefs import HMMBelief
from papere.policies.mpc import MPCPolicy
from papere.policies.rules import PriorityRule, base_belief
from papere.sim import simulate


@dataclass(frozen=True)
class ConformalStepRecord:
    """Audit record for one slot update of ``AdaptiveConformalHeadroom``."""

    t: int
    matured_slot: int
    group_id: int
    residual: float | None
    violation_indicator: int | None
    alpha_after: float
    margin_kw: float
    window_len: int
    effective_cap: int


def finite_sample_conformal_quantile(residuals: Iterable[float], alpha: float) -> float:
    """Finite-sample upper conformal quantile ``Q_{1 - alpha}`` of ``residuals``.

    Uses the standard Romano / Gibbs-Candes order-statistic level
    ``ceil((1 - alpha) * (n + 1)) / n`` clipped to ``[0, 1]``. Returns ``0.0``
    for an empty window (cold start handled by caller's ``init_margin``).
    """
    arr = np.asarray(list(residuals), dtype=np.float64)
    n = arr.size
    if n == 0:
        return 0.0
    level = float(np.clip(np.ceil((1.0 - float(alpha)) * (n + 1)) / n, 0.0, 1.0))
    return float(np.quantile(arr, level, method="higher"))


class AdaptiveConformalHeadroom:
    """Rolling lag-``delta_b`` Adaptive Conformal Inference (ACI) headroom controller.

    Reads strictly from ``InformationSet``:
    - ``view.b_observed`` (slots ``0 .. t - 1 - delta_b``)
    - ``view.b_mean`` and ``view.L`` (public static parameters)
    - ``view.y_confirmed`` (when ``s <= t - delta_A``) or ``view.x_past`` (causal
      setpoint upper bound when ``t - delta_A < s <= t - 1 - delta_b``).

    Never accesses hidden instance arrays and is idempotent across multiple
    within-slot re-dispatch calls (``redispatch_round >= 1`` at ``delta_A == 0``).
    """

    def __init__(
        self,
        *,
        alpha_viol: float = 0.05,
        eta: float = 0.05,
        alpha_min: float = 0.005,
        alpha_max: float = 0.50,
        window_size: int = 24,
        init_margin: float = 0.0,
        min_samples: int = 1,
        feedback_mode: Literal["causal_load", "residual"] = "causal_load",
        warm_start_residuals: dict[int, Iterable[float]] | None = None,
    ) -> None:
        if not 0.0 < alpha_min <= alpha_viol <= alpha_max < 1.0:
            raise ValueError("must satisfy 0 < alpha_min <= alpha_viol <= alpha_max < 1")
        if eta < 0.0:
            raise ValueError("eta must be non-negative")
        if int(window_size) < 1 or int(min_samples) < 1:
            raise ValueError("window_size and min_samples must be >= 1")
        if float(init_margin) < 0.0:
            raise ValueError("init_margin must be non-negative")
        if feedback_mode not in ("causal_load", "residual"):
            raise ValueError("feedback_mode must be 'causal_load' or 'residual'")

        self.alpha_viol = float(alpha_viol)
        self.eta = float(eta)
        self.alpha_min = float(alpha_min)
        self.alpha_max = float(alpha_max)
        self.window_size = int(window_size)
        self.init_margin = float(init_margin)
        self.min_samples = int(min_samples)
        self.feedback_mode = feedback_mode
        self._warm_start = warm_start_residuals

        self._G: int = 0
        self._delta_b: int = 0
        self._alpha: np.ndarray = np.empty(0, dtype=np.float64)
        self._windows: list[deque[float]] = []
        self._last_processed_slot: int = -1
        self._last_margin_by_slot: dict[int, np.ndarray] = {}
        self._cached_t: int = -1
        self._cached_margin: np.ndarray = np.empty(0, dtype=np.float64)
        self.history: list[ConformalStepRecord] = []

    @property
    def alpha(self) -> np.ndarray:
        """Current per-group miscoverage level ``alpha_t`` [G]."""
        return self._alpha.copy()

    def window(self, g: int) -> tuple[float, ...]:
        """Current matured residual window ``W_{g,t}`` for group ``g``."""
        return tuple(self._windows[int(g)])

    def reset(self, static_view: StaticView) -> None:
        """Initialize per-group rolling windows and ``alpha_0 = alpha_viol``."""
        self._G = int(static_view.G)
        self._delta_b = int(static_view.delta_b)
        self._alpha = np.full(self._G, self.alpha_viol, dtype=np.float64)
        self._windows = [deque(maxlen=self.window_size) for _ in range(self._G)]
        if self._warm_start is not None:
            for g in range(self._G):
                for r in self._warm_start.get(g, ()):
                    self._windows[g].append(float(r))
        self._last_processed_slot = -1
        self._last_margin_by_slot = {}
        self._cached_t = -1
        self._cached_margin = np.full(self._G, self.init_margin, dtype=np.float64)
        self.history = []

    def _causal_forecast_at_slot(self, view: InformationSet, s: int) -> np.ndarray:
        """Exact causal forecast ``b_hat_{g, s | s - 1 - delta_b}`` using only ``view``."""
        ref = s - 1 - view.delta_b
        if ref >= 0:
            # Since s <= t - 1 - delta_b and delta_b >= 0, ref < s <= last_base_slot
            return np.asarray(view.base_load(ref), dtype=np.float64)
        return np.asarray(view.b_mean[:, s], dtype=np.float64)

    def _causal_group_load_at_slot(self, view: InformationSet, s: int) -> np.ndarray:
        """Strictly causal group load ``ell_{g,s}`` at matured slot ``s <= t - 1 - delta_b``.

        Uses exact confirmed delivery ``view.delivered(s)`` whenever ``s <= t - delta_A``;
        otherwise uses the conservative causal setpoint upper bound ``view.setpoint(s)``
        (guaranteed ``>=`` realized delivery and strictly inside ``InformationSet``).
        """
        b_s = np.asarray(view.base_load(s), dtype=np.float64)
        if s <= view.last_confirmed_slot:
            ctrl = np.asarray(view.delivered(s), dtype=np.float64)
        else:
            ctrl = np.asarray(view.setpoint(s), dtype=np.float64)
        load = b_s.copy()
        np.add.at(load, np.asarray(view.group, dtype=np.int64), ctrl)
        return load

    def update(self, view: InformationSet) -> np.ndarray:
        """Ingest newly matured slots ``s <= t - 1 - delta_b``, update ACI ``alpha_t``,
        and return per-group margins ``m_t(delta_b, alpha_t)`` [G].

        Idempotent if invoked multiple times at the same slot ``view.t``
        (e.g., during ``delta_A = 0`` within-slot re-dispatch).
        """
        if self._G != view.G:
            raise RuntimeError("AdaptiveConformalHeadroom.reset() must be called for this StaticView")
        if view.t == self._cached_t:
            return self._cached_margin.copy()

        matured_hi = view.last_base_slot  # t - 1 - delta_b
        newly_matured_start = self._last_processed_slot + 1
        last_res = [None] * self._G
        last_viol = [None] * self._G

        for s in range(newly_matured_start, matured_hi + 1):
            b_s = np.asarray(view.base_load(s), dtype=np.float64)
            b_hat_s = self._causal_forecast_at_slot(view, s)
            r_s = b_s - b_hat_s

            if self.feedback_mode == "causal_load":
                ell_s = self._causal_group_load_at_slot(view, s)
                viol_s = (ell_s > (np.asarray(view.L[:, s], dtype=np.float64) + 1e-9)).astype(np.int64)
            else:
                prev_m = self._last_margin_by_slot.get(s, np.full(self._G, self.init_margin))
                viol_s = (r_s > prev_m + 1e-9).astype(np.int64)

            for g in range(self._G):
                self._windows[g].append(float(r_s[g]))
                new_alpha = self._alpha[g] + self.eta * (self.alpha_viol - float(viol_s[g]))
                self._alpha[g] = float(np.clip(new_alpha, self.alpha_min, self.alpha_max))
                last_res[g] = float(r_s[g])
                last_viol[g] = int(viol_s[g])
            self._last_processed_slot = s

        margins = np.empty(self._G, dtype=np.float64)
        for g in range(self._G):
            win = self._windows[g]
            if len(win) < self.min_samples:
                # Cold-start: use init_margin (or blended max with observed residuals)
                q_val = finite_sample_conformal_quantile(win, self._alpha[g]) if win else 0.0
                margins[g] = max(0.0, self.init_margin, q_val)
            else:
                q_val = finite_sample_conformal_quantile(win, self._alpha[g])
                margins[g] = max(0.0, q_val)

        self._last_margin_by_slot[view.t] = margins.copy()
        self._cached_t = view.t
        self._cached_margin = margins.copy()

        caps = self.effective_caps(view, margins)
        for g in range(self._G):
            self.history.append(
                ConformalStepRecord(
                    t=view.t,
                    matured_slot=matured_hi,
                    group_id=g,
                    residual=last_res[g],
                    violation_indicator=last_viol[g],
                    alpha_after=float(self._alpha[g]),
                    margin_kw=float(margins[g]),
                    window_len=len(self._windows[g]),
                    effective_cap=int(caps[g]),
                )
            )
        return margins

    def effective_caps(self, view: InformationSet, margins: np.ndarray | None = None) -> np.ndarray:
        """Compute ``C_{g,t} = max(0, floor(L_{g,t} - b_hat_{g,t} - m_{g,t} + 1e-9))`` [G]."""
        m = self._cached_margin if margins is None else np.asarray(margins, dtype=np.float64)
        cap = np.floor(
            np.asarray(view.L[:, view.t], dtype=np.float64)
            - np.asarray(view.base_forecast, dtype=np.float64)
            - m
            + 1e-9
        ).astype(np.int64)
        return np.maximum(cap, 0)


class ConformalGuardedMPC(MPCPolicy):
    """Drop-in ``MPCPolicy`` coupled with ``AdaptiveConformalHeadroom``.

    Preserves the exact ``Policy`` protocol and ``InformationSet`` firewall so
    ``papere.sim.simulate`` and ``papere.ledger.evaluate`` run unmodified.
    """

    def __init__(
        self,
        belief: Belief,
        W: int = 24,
        gamma: float = 1.0,
        *,
        headroom: AdaptiveConformalHeadroom | None = None,
        alpha_viol: float = 0.05,
        eta: float = 0.05,
        alpha_min: float = 0.005,
        alpha_max: float = 0.50,
        window_size: int = 24,
        init_margin: float = 1.0,
        min_samples: int = 3,
        feedback_mode: Literal["causal_load", "residual"] = "causal_load",
        name: str | None = None,
        privileged: bool = False,
    ) -> None:
        super().__init__(
            belief=belief,
            W=W,
            m=0.0,
            k=0,
            gamma=gamma,
            name=name or f"ConformalGMPC[{getattr(belief, 'name', 'belief')}]_a{alpha_viol:g}",
            privileged=privileged,
        )
        self.headroom = headroom if headroom is not None else AdaptiveConformalHeadroom(
            alpha_viol=alpha_viol,
            eta=eta,
            alpha_min=alpha_min,
            alpha_max=alpha_max,
            window_size=window_size,
            init_margin=init_margin,
            min_samples=min_samples,
            feedback_mode=feedback_mode,
        )
        self._current_margins: np.ndarray = np.empty(0, dtype=np.float64)

    def reset(
        self,
        static_view: StaticView,
        rng: np.random.Generator,
        oracle: OracleView | None = None,
    ) -> None:
        super().reset(static_view, rng, oracle=oracle)
        self.headroom.reset(static_view)
        self._current_margins = np.full(static_view.G, self.headroom.init_margin, dtype=np.float64)

    def act(self, view: InformationSet) -> np.ndarray:
        if not self._ready:
            raise RuntimeError(f"{self.name}: reset() has not been called")
        self._current_margins = self.headroom.update(view)
        post = self.belief.compute(view)
        return self.decide(view, post)

    def caps(self, view: InformationSet, t_end: int) -> np.ndarray:
        """Apply dynamic conformal margin ``m_{g,t}(delta_b, alpha_t)`` across planning horizon."""
        t = view.t
        m_col = self._current_margins[:, None]
        cap = np.floor(
            self._L[:, t:t_end]
            - np.asarray(view.base_forecast, dtype=np.float64)[:, None]
            - m_col
            + 1e-9
        ).astype(np.int64)
        cap[:, 0] = self.headroom.effective_caps(view, self._current_margins)
        return np.maximum(cap, 0)


def conformal_guarded_mpc(
    params: PopulationParams,
    *,
    mode: str = "e1",
    W: int = 24,
    gamma: float = 1.0,
    alpha_viol: float = 0.05,
    eta: float = 0.05,
    window_size: int = 24,
    init_margin: float = 1.0,
    min_samples: int = 3,
    feedback_mode: Literal["causal_load", "residual"] = "causal_load",
    name: str | None = None,
) -> ConformalGuardedMPC:
    """Convenience constructor pairing ``HMMBelief(params, mode)`` with ACI headroom."""
    return ConformalGuardedMPC(
        belief=HMMBelief(params, mode=mode),
        W=W,
        gamma=gamma,
        alpha_viol=alpha_viol,
        eta=eta,
        window_size=window_size,
        init_margin=init_margin,
        min_samples=min_samples,
        feedback_mode=feedback_mode,
        name=name,
    )


# --------------------------------------------------------------------------- comparative simulation
def benchmark_conformal_headroom(
    seeds: Iterable[int] = range(60000, 60050),
    *,
    cell: Cell | None = None,
    params: PopulationParams | None = None,
    alpha_viol: float = 0.05,
    eta: float = 0.05,
    init_margin: float = 1.5,
    min_samples: int = 3,
) -> dict[str, dict[str, float]]:
    """Run comparative simulation on ``papere`` instances using unmodified ``simulate`` & ``evaluate``.

    Compares:
    - ``guarded_mpc_e1_m0`` (frozen ``paperE`` zero-margin baseline)
    - ``guarded_mpc_e1_m1`` (fixed margin ``m = 1``)
    - ``sym_margin_ce_llf`` (``CE-LLF`` at ``m = 0``)
    - ``conformal_guarded_mpc_e1`` (``AdaptiveConformalHeadroom`` + ``HMMBelief(e1)``)

    Default cell is the lag-split base-load stress cell (``M=3, delta_A=0, delta_b=2, rho=0.95``)
    on tuning seeds ``60000..60049`` (zero overlap with frozen development or confirmation seeds).
    """
    if cell is None:
        cell = Cell(family="F0R", M=3, delta_A=0, delta_b=2, rho=0.95, r=0.3)
    if params is None:
        params = load_population_params()
    seed_list = [int(s) for s in seeds]
    if not seed_list:
        raise ValueError("seeds must be non-empty")

    def make_policies():
        return {
            "guarded_mpc_e1_m0": MPCPolicy(HMMBelief(params, "e1"), W=24, m=0.0, k=0, gamma=1.0,
                                           name="guarded_mpc_e1_m0"),
            "guarded_mpc_e1_m1": MPCPolicy(HMMBelief(params, "e1"), W=24, m=1.0, k=0, gamma=1.0,
                                           name="guarded_mpc_e1_m1"),
            "sym_margin_ce_llf": PriorityRule(base_belief("CE"), "LLF", 0, 0, name="sym_margin_ce_llf"),
            "conformal_guarded_mpc_e1": conformal_guarded_mpc(
                params, mode="e1", W=24, gamma=1.0,
                alpha_viol=alpha_viol, eta=eta,
                init_margin=init_margin, min_samples=min_samples,
                name="conformal_guarded_mpc_e1",
            ),
        }

    metrics_keys = (
        "violation_kwslot",
        "violation_count",
        "violation_longest_run_slots",
        "R_avoid_kwh_per100",
        "deadline_miss_count_per100",
        "peak_kw",
        "cpu_mean_ms",
    )
    acc: dict[str, dict[str, list[float]]] = {}
    mean_margin_list: list[float] = []

    for seed in seed_list:
        inst = generate_f0r(seed, cell)
        for pname, pol in make_policies().items():
            traj = simulate(inst, cell, pol, seed)
            row = evaluate(inst, traj)
            bucket = acc.setdefault(pname, {k: [] for k in metrics_keys})
            for k in metrics_keys:
                bucket[k].append(float(row[k]))
            if isinstance(pol, ConformalGuardedMPC) and pol.headroom.history:
                mean_margin_list.append(float(np.mean([h.margin_kw for h in pol.headroom.history])))

    summary: dict[str, dict[str, float]] = {}
    for pname, bucket in acc.items():
        summary[pname] = {k: float(np.mean(v)) for k, v in bucket.items()}
        summary[pname]["n_seeds"] = float(len(seed_list))
    if mean_margin_list:
        summary["conformal_guarded_mpc_e1"]["mean_conformal_margin_kw"] = float(np.mean(mean_margin_list))
    return summary
