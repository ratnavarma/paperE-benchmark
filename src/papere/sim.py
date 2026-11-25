"""Simulator (BUILD_SPEC Section 7): ``Policy`` protocol, ``simulate``, ``Trajectory``."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

import numpy as np

from .generator import policy_rng
from .infoset import InformationSet, OracleView, StaticView, UNKNOWN
from .instance import Cell, Instance


TIEBREAK_STREAM = "tiebreak"


class InvalidAction(Exception):
    """A policy returned a setpoint vector that breaks the rules."""


@runtime_checkable
class Policy(Protocol):
    """Interface every policy implements. Inputs arrive only through the views."""

    name: str
    privileged: bool

    def reset(self, static_view: StaticView, rng: np.random.Generator,
              oracle: OracleView | None = None) -> None: ...

    def floor_mask(self, static_view: StaticView) -> np.ndarray | None: ...

    def act(self, view: InformationSet) -> np.ndarray: ...


@dataclass
class Trajectory:
    """Everything the ledger needs from one run."""

    policy: str
    privileged: bool
    seed: int
    cell_id: str
    x: np.ndarray         # [N, H] setpoints
    y: np.ndarray         # [N, H] delivered units
    A: np.ndarray         # [N, H] realized availability (true, with the floor applied)
    r_before: np.ndarray  # [N, H] true remaining debt at the start of each slot
    r_final: np.ndarray   # [N] residual after the last slot
    floored: np.ndarray   # [N] bool
    cpu_ms: np.ndarray    # [H] CPU time of ``act`` per decision (summed over rounds)
    rounds: np.ndarray    # [H] number of ``act`` calls per slot (>1 only at delta_A = 0)
    # audit log, slots with more than one round only: (t, round, x returned, column-t entries
    # revealed in the view that call saw); lets withdrawn commands and reveals be checked
    redispatch_log: list = field(default_factory=list)


def _slot_caps(inst: Instance, t: int, delta_b: int) -> np.ndarray:
    """Setpoint cap per group with m = 0, from the simulator's own data (not the view)."""
    last = t - 1 - delta_b
    b_hat = inst.b[:, last] if last >= 0 else inst.b_mean[:, t]
    return np.maximum(0, np.floor(inst.L[:, t] - b_hat + 1e-9)).astype(np.int64)


def _validate(x, inst: Instance, t: int, caps: np.ndarray) -> np.ndarray:
    """Check an action against the instance itself, never against anything a policy can reach."""
    x = np.asarray(x)
    if x.shape != (inst.N,):
        raise InvalidAction(f"t={t}: action must have shape ({inst.N},), got {x.shape}")
    if not np.issubdtype(x.dtype, np.integer):
        raise InvalidAction(f"t={t}: action must be integer-typed, got {x.dtype}")
    x = x.astype(np.int64)
    if (x < 0).any():
        raise InvalidAction(f"t={t}: negative setpoint")
    if (x > inst.P).any():
        raise InvalidAction(f"t={t}: setpoint above P_i")
    outside = ~((inst.a <= t) & (t < inst.d))
    if (x[outside] != 0).any():
        raise InvalidAction(f"t={t}: nonzero setpoint outside the window")
    for g in range(inst.n_groups):
        total = int(x[inst.group == g].sum())
        if total > caps[g]:
            raise InvalidAction(f"t={t}: group {g} setpoints {total} exceed cap {caps[g]}")
    return x


def simulate(instance: Instance, cell: Cell, policy: Policy, seed: int) -> Trajectory:
    """Run ``policy`` on ``instance`` and return the trajectory.

    ``delta_A >= 1``: one ``act`` call per slot. ``delta_A = 0``: within-slot
    re-dispatch. The view starts with column ``t`` unknown; after each call, A_it is
    revealed for commanded participants with true debt > 0, and if any of them is
    unavailable ``act`` is called again (``redispatch_round`` += 1). The last call's
    action is the slot's action. Every call's action is validated in full.
    """
    if cell.cell_id != instance.cell.cell_id:
        raise ValueError("cell does not match the instance")
    if int(seed) != instance.seed:
        raise ValueError("seed does not match the instance seed")
    N, H = instance.N, instance.H
    privileged = bool(getattr(policy, "privileged", False))
    # The simulator slices with its own StaticView, which no policy can reach; the policy
    # gets a separate instance, so rewriting its fields cannot change what a view contains.
    sim_static = StaticView.from_instance(instance, cell)
    policy_static = StaticView.from_instance(instance, cell)
    # common random numbers: one tie-break stream per (seed, cell), the same for every policy
    rng = policy_rng(seed, cell.cell_id, TIEBREAK_STREAM)
    oracle = OracleView.from_instance(instance) if privileged else None
    policy.reset(policy_static, rng, oracle=oracle)

    fm = policy.floor_mask(policy_static)
    if fm is None:
        floored = np.zeros(N, dtype=bool)
    else:
        floored = np.asarray(fm)
        if floored.shape != (N,) or floored.dtype != bool:
            raise InvalidAction("floor_mask must be None or a bool array of shape [N]")
        floored = floored.copy()
    A = instance.availability(floored)

    x = np.zeros((N, H), dtype=np.int64)
    y = np.zeros((N, H), dtype=np.int64)
    r_before = np.zeros((N, H), dtype=np.int64)
    A_obs = np.full((N, H), UNKNOWN, dtype=np.int8)  # masked: the wrapper's only source of A
    cpu_ms = np.zeros(H)
    rounds = np.zeros(H, dtype=np.int64)
    log: list = []
    r = instance.E.astype(np.int64).copy()

    for t in range(H):
        caps = _slot_caps(instance, t, cell.delta_b)
        revealed = np.zeros(N, dtype=bool)   # column-t reveals made during re-dispatch
        rnd = 0
        slot_log = []
        while True:
            if cell.delta_A == 0:
                A_obs[:, t] = np.where(revealed, A[:, t], UNKNOWN)
            view = InformationSet.build(sim_static, t, x, A_obs, y, instance.b, rnd,
                                        delta_A=cell.delta_A, delta_b=cell.delta_b)
            t0 = time.process_time_ns()
            action = policy.act(view)
            cpu_ms[t] += (time.process_time_ns() - t0) / 1e6
            xt = _validate(action, instance, t, caps)
            rounds[t] += 1
            slot_log.append((t, rnd, xt.copy(), revealed.copy()))
            if cell.delta_A != 0:
                break
            new = (xt > 0) & (r > 0) & ~revealed
            if not (new & (A[:, t] == 0)).any():
                break                          # fixpoint: nothing to correct
            revealed |= new
            rnd += 1
            if rnd > N:
                raise RuntimeError("re-dispatch did not terminate")
        if len(slot_log) > 1:
            log.extend(slot_log)
        x[:, t] = xt
        r_before[:, t] = r
        yt = np.minimum(xt, r) * A[:, t]
        y[:, t] = yt
        final_mask = ((xt > 0) & (r > 0)) | revealed
        A_obs[:, t] = np.where(final_mask, A[:, t], UNKNOWN)
        r = r - yt

    return Trajectory(policy=policy.name, privileged=privileged, seed=int(seed),
                      cell_id=cell.cell_id, x=x, y=y, A=A, r_before=r_before,
                      r_final=r, floored=floored, cpu_ms=cpu_ms, rounds=rounds,
                      redispatch_log=log)
