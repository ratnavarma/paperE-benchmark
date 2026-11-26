"""Pre-filing §112(a) enablement extensions for C37 (HedgeCap).

These modules live strictly outside the frozen ``papere`` benchmark core so that
frozen confirmation seeds, policies, and results remain untouched:

- ``async_release``: ``SharedHedgeCapLedger``, ``hedge_dependency_edges``,
  mid-slot asynchronous acknowledgement & censored ``known_complete`` handler,
  ``CANCEL_OR_RAMPDOWN_SETPOINT`` emitter respecting minimum dwell/slew
  ``tau_min``, atomic headroom return to starved concurrent events, and an
  equal-cap comparative benchmark.
- ``conformal_margin``: ``AdaptiveConformalHeadroom`` maintaining a zero-leakage
  rolling window of matured lag-``delta_b`` base-load residuals with Adaptive
  Conformal Inference (ACI) updates, drop-in ``ConformalGuardedMPC`` policy
  compatible with ``papere.sim.simulate``, and a comparative benchmark.
"""
from __future__ import annotations

from .async_release import (
    AckProcessResult,
    AsyncAckEvent,
    CancelOrRampdownCommand,
    DispatchEvent,
    HedgeDependencyEdge,
    PendingCapacityRelease,
    ReallocationCommand,
    SharedHedgeCapLedger,
    benchmark_async_release,
    hedge_dependency_edges,
)
from .conformal_margin import (
    AdaptiveConformalHeadroom,
    ConformalGuardedMPC,
    ConformalStepRecord,
    benchmark_conformal_headroom,
    conformal_guarded_mpc,
)

__all__ = [
    "AckProcessResult",
    "AsyncAckEvent",
    "CancelOrRampdownCommand",
    "DispatchEvent",
    "HedgeDependencyEdge",
    "PendingCapacityRelease",
    "ReallocationCommand",
    "SharedHedgeCapLedger",
    "benchmark_async_release",
    "hedge_dependency_edges",
    "AdaptiveConformalHeadroom",
    "ConformalGuardedMPC",
    "ConformalStepRecord",
    "benchmark_conformal_headroom",
    "conformal_guarded_mpc",
]
