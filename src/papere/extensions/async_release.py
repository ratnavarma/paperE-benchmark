"""Asynchronous intra-slot late-acknowledgement hedge release & shared-cap ledger.

Implements the multi-event shared-capacity hedge pool for C37 (HedgeCap):

1. ``SharedHedgeCapLedger`` spans concurrent open dispatch events ``e in E_t``
   sharing a physical capacity group ``g`` (feeder, transformer, or AI
   data-center PDU breaker envelope ``C_{g,t}``), partitioning headroom into
   primary allocations ``x^(1)_{i,t}`` and secondary hedges ``x^(2)_{j,t}``.
2. ``hedge_dependency_edges(primary_id, secondary_id, event_id, hedged_kw,
   min_dwell_tau)`` constructs directed dependency edges linking primary
   setpoints to their hedging secondaries with hardware minimum dwell/slew
   constraints ``tau_min``.
3. ``process_async_ack`` handles mid-slot asynchronous webhook/telemetry
   confirmations certifying delivered energy ``y_{i,s}`` or censored
   ``known_complete`` (``A_{i,s} == UNKNOWN (-1)`` with ``x_{i,s} > 0``),
   emits idempotent ``CANCEL_OR_RAMPDOWN_SETPOINT`` commands respecting
   ``min_dwell_tau`` (and optional hardware floor / thermal slew rate), and
   atomically returns freed headroom ``Delta C_{g,t}`` to starved concurrent
   events ``e' in E_t`` once dwell/slew completes.
4. ``benchmark_async_release`` compares ``HedgeCap + AsyncRelease`` against
   equal-cap static pooled overbooking buffer, wait-for-confirmation, and
   physical-cap blind overbooking across concurrent dispatch events.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Iterable, Literal

import numpy as np

from papere.infoset import UNKNOWN


@dataclass
class HedgeDependencyEdge:
    """Directed edge linking a primary allocation to a secondary hedge actuator."""

    primary_id: int
    secondary_id: int
    event_id: str
    hedged_kw: int
    min_dwell_tau: float
    group_id: int = 0
    created_tau: float = 0.0
    min_floor_kw: int = 0
    slew_rate_kw_per_s: float | None = None
    edge_id: str = ""
    released_kw: int = 0
    pending_release_kw: int = 0
    release_effective_tau: float | None = None
    status: Literal["ACTIVE", "RAMPING_DOWN", "RELEASED"] = "ACTIVE"

    def __post_init__(self) -> None:
        self.primary_id = int(self.primary_id)
        self.secondary_id = int(self.secondary_id)
        self.event_id = str(self.event_id)
        self.hedged_kw = int(self.hedged_kw)
        self.min_dwell_tau = float(self.min_dwell_tau)
        self.group_id = int(self.group_id)
        self.created_tau = float(self.created_tau)
        self.min_floor_kw = int(self.min_floor_kw)
        if self.hedged_kw < 0:
            raise ValueError("hedged_kw must be non-negative")
        if self.min_dwell_tau < 0.0:
            raise ValueError("min_dwell_tau must be non-negative")
        if self.min_floor_kw < 0 or self.min_floor_kw > self.hedged_kw:
            raise ValueError("min_floor_kw must satisfy 0 <= min_floor_kw <= hedged_kw")
        if self.slew_rate_kw_per_s is not None and self.slew_rate_kw_per_s <= 0.0:
            raise ValueError("slew_rate_kw_per_s must be positive when provided")
        if not self.edge_id:
            self.edge_id = f"{self.event_id}:p{self.primary_id}->s{self.secondary_id}"

    @property
    def active_kw(self) -> int:
        """Capacity currently held on the ledger (excluding finalized releases)."""
        return self.hedged_kw - self.released_kw

    @property
    def cancellable_kw(self) -> int:
        """Additional capacity still eligible for cancellation above ``min_floor_kw``."""
        return max(0, self.hedged_kw - self.released_kw - self.pending_release_kw - self.min_floor_kw)


def hedge_dependency_edges(
    primary_id: int,
    secondary_id: int,
    event_id: str,
    hedged_kw: int,
    min_dwell_tau: float,
    *,
    group_id: int = 0,
    created_tau: float = 0.0,
    min_floor_kw: int = 0,
    slew_rate_kw_per_s: float | None = None,
    edge_id: str = "",
) -> HedgeDependencyEdge:
    """Create a ``HedgeDependencyEdge(primary_id, secondary_id, event_id, hedged_kw, min_dwell_tau)``."""
    return HedgeDependencyEdge(
        primary_id=primary_id,
        secondary_id=secondary_id,
        event_id=event_id,
        hedged_kw=hedged_kw,
        min_dwell_tau=min_dwell_tau,
        group_id=group_id,
        created_tau=created_tau,
        min_floor_kw=min_floor_kw,
        slew_rate_kw_per_s=slew_rate_kw_per_s,
        edge_id=edge_id,
    )


@dataclass
class DispatchEvent:
    """An open dispatch event sharing a cap-group envelope ``C_{g,t}``."""

    event_id: str
    group_id: int
    priority: int = 0
    deadline_slot: int = 1
    slot_t: int = 0
    slot_duration_s: float = 900.0
    primary_allocs: dict[int, int] = field(default_factory=dict)
    secondary_allocs: dict[int, int] = field(default_factory=dict)
    device_debt: dict[int, int] = field(default_factory=dict)
    device_rate_cap: dict[int, int] = field(default_factory=dict)
    starved_requests: dict[int, int] = field(default_factory=dict)

    @property
    def primary_total_kw(self) -> int:
        return int(sum(self.primary_allocs.values()))

    @property
    def secondary_total_kw(self) -> int:
        return int(sum(self.secondary_allocs.values()))

    @property
    def total_allocated_kw(self) -> int:
        return self.primary_total_kw + self.secondary_total_kw

    @property
    def starved_demand_kw(self) -> int:
        return int(sum(max(0, kw) for kw in self.starved_requests.values()))


@dataclass(frozen=True)
class AsyncAckEvent:
    """Mid-slot asynchronous confirmation or censored telemetry event at ``tau``."""

    event_id: str
    primary_id: int
    slot_s: int
    arrival_tau: float
    delivered_kw: int
    availability_obs: int   # 1 = available, 0 = stuck/failed, -1 (UNKNOWN) = masked
    commanded_kw: int
    ack_id: str = ""

    def __post_init__(self) -> None:
        if self.availability_obs not in (UNKNOWN, 0, 1):
            raise ValueError("availability_obs must be in {-1, 0, 1}")
        if self.delivered_kw < 0 or self.commanded_kw < 0:
            raise ValueError("delivered_kw and commanded_kw must be non-negative")
        if self.arrival_tau < 0.0:
            raise ValueError("arrival_tau must be non-negative")

    @property
    def effective_ack_id(self) -> str:
        if self.ack_id:
            return self.ack_id
        return (f"ack:{self.event_id}:p{self.primary_id}:s{self.slot_s}"
                f":tau{self.arrival_tau:.6f}:y{self.delivered_kw}:A{self.availability_obs}")


@dataclass(frozen=True)
class CancelOrRampdownCommand:
    """Actuator command cancelling or ramping down a redundant secondary hedge."""

    secondary_id: int
    event_id: str
    group_id: int
    edge_id: str
    previous_kw: int
    revised_kw: int
    freed_kw: int
    issued_tau: float
    effective_tau: float
    idempotency_key: str
    reason: Literal["PRIMARY_CONFIRMED_DELIVERY", "PRIMARY_CENSORED_KNOWN_COMPLETE"]
    command_type: Literal["CANCEL_OR_RAMPDOWN_SETPOINT"] = "CANCEL_OR_RAMPDOWN_SETPOINT"


@dataclass(frozen=True)
class ReallocationCommand:
    """Atomic headroom return command assigning freed ``Delta C_{g,t}`` to a starved event."""

    target_event_id: str
    device_id: int
    group_id: int
    allocated_kw: int
    effective_tau: float
    source_edge_id: str
    idempotency_key: str
    command_type: Literal["REALLOCATE_STARVED_EVENT"] = "REALLOCATE_STARVED_EVENT"


@dataclass
class PendingCapacityRelease:
    """Freed capacity waiting on hardware ``min_dwell_tau`` or slew completion."""

    group_id: int
    event_id: str
    edge_id: str
    secondary_id: int
    freed_kw: int
    effective_tau: float
    idempotency_key: str
    settled: bool = False


@dataclass(frozen=True)
class AckProcessResult:
    """Structured outcome returned by ``SharedHedgeCapLedger.process_async_ack``."""

    event_id: str
    primary_id: int
    known_complete_triggered: bool
    satisfied_delta_kw: int
    freed_capacity_now_kw: int
    deferred_release_kw: int
    cancel_commands: tuple[CancelOrRampdownCommand, ...]
    reallocations: tuple[ReallocationCommand, ...]
    idempotent_duplicate: bool = False


def _make_idempotency_key(*parts: object) -> str:
    raw = "|".join(str(p) for p in parts).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:20]


class SharedHedgeCapLedger:
    """Atomic multi-event shared-capacity ledger for hedged setpoint dispatch.

    Enforces ``sum_{e in E_t} (primary_e + secondary_e) <= C_{g,t}`` across all
    concurrent open dispatch events in every cap-group ``g``, at every instant
    ``tau`` within a slot (including dwell/slew ramp-down intervals).
    """

    def __init__(self, group_caps: dict[int, int] | Iterable[int], *, slot_duration_s: float = 900.0) -> None:
        if isinstance(group_caps, dict):
            self._caps: dict[int, int] = {int(g): int(c) for g, c in group_caps.items()}
        else:
            self._caps = {int(g): int(c) for g, c in enumerate(group_caps)}
        for g, c in self._caps.items():
            if c < 0:
                raise ValueError(f"group {g} cap must be non-negative, got {c}")
        self.slot_duration_s = float(slot_duration_s)
        self.current_tau: float = 0.0
        self._events: dict[str, DispatchEvent] = {}
        self._edges: dict[str, HedgeDependencyEdge] = {}
        self._edges_by_primary: dict[tuple[str, int], list[str]] = {}
        self._pending_releases: list[PendingCapacityRelease] = []
        self._processed_acks: set[str] = set()
        self.cancel_log: list[CancelOrRampdownCommand] = []
        self.reallocation_log: list[ReallocationCommand] = []

    # ---- inspection ---------------------------------------------------------
    def group_cap(self, group_id: int) -> int:
        g = int(group_id)
        if g not in self._caps:
            raise KeyError(f"unknown cap group {g}")
        return self._caps[g]

    def total_allocated(self, group_id: int) -> int:
        g = int(group_id)
        return sum(ev.total_allocated_kw for ev in self._events.values() if ev.group_id == g)

    def primary_allocated(self, group_id: int) -> int:
        g = int(group_id)
        return sum(ev.primary_total_kw for ev in self._events.values() if ev.group_id == g)

    def secondary_allocated(self, group_id: int) -> int:
        g = int(group_id)
        return sum(ev.secondary_total_kw for ev in self._events.values() if ev.group_id == g)

    def available_headroom(self, group_id: int) -> int:
        return self.group_cap(group_id) - self.total_allocated(group_id)

    def event(self, event_id: str) -> DispatchEvent:
        return self._events[str(event_id)]

    def pending_release_kw(self, group_id: int) -> int:
        g = int(group_id)
        return sum(p.freed_kw for p in self._pending_releases if not p.settled and p.group_id == g)

    def assert_invariants(self) -> None:
        """Verify hard capacity and ledger-accounting invariants across all groups."""
        for g, cap in self._caps.items():
            alloc = self.total_allocated(g)
            if alloc < 0 or alloc > cap:
                raise AssertionError(f"group {g}: allocated {alloc} outside [0, {cap}]")
        for edge in self._edges.values():
            ev = self._events[edge.event_id]
            sec_alloc = ev.secondary_allocs.get(edge.secondary_id, 0)
            if edge.active_kw < 0:
                raise AssertionError(f"edge {edge.edge_id}: negative active_kw {edge.active_kw}")
            if edge.active_kw > sec_alloc:
                raise AssertionError(
                    f"edge {edge.edge_id}: active_kw {edge.active_kw} > event secondary_alloc {sec_alloc}"
                )

    # ---- registration & reservation ----------------------------------------
    def open_event(
        self,
        event_id: str,
        group_id: int,
        *,
        priority: int = 0,
        deadline_slot: int = 1,
        slot_t: int = 0,
        device_debt: dict[int, int] | None = None,
        device_rate_cap: dict[int, int] | None = None,
    ) -> DispatchEvent:
        eid = str(event_id)
        g = int(group_id)
        if g not in self._caps:
            raise KeyError(f"unknown cap group {g}")
        if eid in self._events:
            raise ValueError(f"event {eid!r} is already open")
        ev = DispatchEvent(
            event_id=eid,
            group_id=g,
            priority=int(priority),
            deadline_slot=int(deadline_slot),
            slot_t=int(slot_t),
            slot_duration_s=self.slot_duration_s,
            device_debt={int(k): int(v) for k, v in (device_debt or {}).items()},
            device_rate_cap={int(k): int(v) for k, v in (device_rate_cap or {}).items()},
        )
        self._events[eid] = ev
        return ev

    def allocate_primary(self, event_id: str, device_id: int, kw: int, *, allow_partial: bool = False) -> int:
        """Reserve primary capacity ``x^(1)_{i,t}``; queues unmet demand as starved if partial."""
        ev = self._events[str(event_id)]
        dev = int(device_id)
        want = int(kw)
        if want < 0:
            raise ValueError("kw must be non-negative")
        headroom = self.available_headroom(ev.group_id)
        rate_cap = ev.device_rate_cap.get(dev)
        cur_dev = ev.primary_allocs.get(dev, 0) + ev.secondary_allocs.get(dev, 0)
        if rate_cap is not None and cur_dev + want > rate_cap:
            want = max(0, rate_cap - cur_dev)
        if want > headroom:
            if not allow_partial:
                raise ValueError(
                    f"group {ev.group_id}: requested {want} kW exceeds available headroom {headroom} kW"
                )
            grant = headroom
            shortfall = want - grant
            ev.starved_requests[dev] = ev.starved_requests.get(dev, 0) + shortfall
        else:
            grant = want
        if grant > 0:
            ev.primary_allocs[dev] = ev.primary_allocs.get(dev, 0) + grant
        return grant

    def register_starved_demand(self, event_id: str, device_id: int, kw: int) -> None:
        """Explicitly enqueue starved demand on an open concurrent event."""
        ev = self._events[str(event_id)]
        dev = int(device_id)
        amt = int(kw)
        if amt <= 0:
            return
        ev.starved_requests[dev] = ev.starved_requests.get(dev, 0) + amt

    def hedge_dependency_edges(
        self,
        primary_id: int,
        secondary_id: int,
        event_id: str,
        hedged_kw: int,
        min_dwell_tau: float,
        *,
        created_tau: float | None = None,
        min_floor_kw: int = 0,
        slew_rate_kw_per_s: float | None = None,
        edge_id: str = "",
    ) -> HedgeDependencyEdge:
        """Atomically reserve secondary hedge capacity ``x^(2)_{j,t}`` and record its edge."""
        ev = self._events[str(event_id)]
        sec = int(secondary_id)
        kw = int(hedged_kw)
        if kw <= 0:
            raise ValueError("hedged_kw must be positive")
        headroom = self.available_headroom(ev.group_id)
        if kw > headroom:
            raise ValueError(
                f"group {ev.group_id}: hedge {kw} kW exceeds available headroom {headroom} kW"
            )
        rate_cap = ev.device_rate_cap.get(sec)
        cur_sec = ev.primary_allocs.get(sec, 0) + ev.secondary_allocs.get(sec, 0)
        if rate_cap is not None and cur_sec + kw > rate_cap:
            raise ValueError(
                f"device {sec}: hedge {kw} kW exceeds device rate cap {rate_cap} kW (current {cur_sec})"
            )
        tau0 = self.current_tau if created_tau is None else float(created_tau)
        edge = hedge_dependency_edges(
            primary_id=primary_id,
            secondary_id=sec,
            event_id=ev.event_id,
            hedged_kw=kw,
            min_dwell_tau=min_dwell_tau,
            group_id=ev.group_id,
            created_tau=tau0,
            min_floor_kw=min_floor_kw,
            slew_rate_kw_per_s=slew_rate_kw_per_s,
            edge_id=edge_id or f"{ev.event_id}:p{int(primary_id)}->s{sec}#{len(self._edges)}",
        )
        if edge.edge_id in self._edges:
            raise ValueError(f"duplicate edge_id {edge.edge_id!r}")
        ev.secondary_allocs[sec] = ev.secondary_allocs.get(sec, 0) + kw
        self._edges[edge.edge_id] = edge
        self._edges_by_primary.setdefault((ev.event_id, int(primary_id)), []).append(edge.edge_id)
        return edge

    def edges_for_primary(self, event_id: str, primary_id: int) -> list[HedgeDependencyEdge]:
        ids = self._edges_by_primary.get((str(event_id), int(primary_id)), [])
        return [self._edges[eid] for eid in ids]

    # ---- mid-slot asynchronous acknowledgement handler ----------------------
    def process_async_ack(self, ack: AsyncAckEvent) -> AckProcessResult:
        """Process a mid-slot async confirmation or censored ``known_complete`` signal.

        1. Rejects duplicate ``ack_id`` idempotently without double-freeing cap.
        2. Detects censored ``known_complete`` when ``availability_obs == UNKNOWN (-1)``
           and ``commanded_kw > 0`` (matching ``papere.policies.beliefs.known_complete``),
           certifying remaining debt = 0.
        3. Preserves hedges intact when ``availability_obs == 0`` (confirmed stuck).
        4. Emits ``CANCEL_OR_RAMPDOWN_SETPOINT`` commands respecting ``min_dwell_tau``,
           ``min_floor_kw``, and ``slew_rate_kw_per_s``.
        5. Atomically returns freed ``Delta C_{g,t}`` to starved concurrent events
           immediately if dwell/slew is already satisfied, or queues settlement for
           ``advance_time(effective_tau)`` to guarantee zero physical overload.
        """
        ack_key = ack.effective_ack_id
        if ack_key in self._processed_acks:
            return AckProcessResult(
                event_id=ack.event_id,
                primary_id=ack.primary_id,
                known_complete_triggered=False,
                satisfied_delta_kw=0,
                freed_capacity_now_kw=0,
                deferred_release_kw=0,
                cancel_commands=(),
                reallocations=(),
                idempotent_duplicate=True,
            )
        self._processed_acks.add(ack_key)

        if ack.arrival_tau > self.current_tau:
            self.advance_time(ack.arrival_tau)

        ev = self._events[str(ack.event_id)]
        pid = int(ack.primary_id)
        debt_before = ev.device_debt.get(pid, ev.primary_allocs.get(pid, ack.commanded_kw))

        # Censored known_complete rule (beliefs.py:L62-69): A_is == -1 with x_is > 0
        censored_complete = (ack.availability_obs == UNKNOWN) and (ack.commanded_kw > 0)
        if censored_complete:
            satisfied_delta = max(debt_before, ack.commanded_kw)
            ev.device_debt[pid] = 0
            reason: Literal["PRIMARY_CONFIRMED_DELIVERY", "PRIMARY_CENSORED_KNOWN_COMPLETE"] = (
                "PRIMARY_CENSORED_KNOWN_COMPLETE"
            )
        elif ack.availability_obs == 1 and ack.delivered_kw > 0:
            satisfied_delta = min(debt_before, ack.delivered_kw) if pid in ev.device_debt else ack.delivered_kw
            if pid in ev.device_debt:
                ev.device_debt[pid] = max(0, debt_before - ack.delivered_kw)
            reason = "PRIMARY_CONFIRMED_DELIVERY"
        else:
            # Confirmed stuck (A=0) or zero delivery -> keep secondary hedge armed!
            return AckProcessResult(
                event_id=ev.event_id,
                primary_id=pid,
                known_complete_triggered=False,
                satisfied_delta_kw=0,
                freed_capacity_now_kw=0,
                deferred_release_kw=0,
                cancel_commands=(),
                reallocations=(),
            )

        remaining_to_release = int(satisfied_delta)
        cancel_cmds: list[CancelOrRampdownCommand] = []
        realloc_cmds: list[ReallocationCommand] = []
        freed_now_total = 0
        deferred_total = 0

        for edge in self.edges_for_primary(ev.event_id, pid):
            if remaining_to_release <= 0:
                break
            can_cancel = edge.cancellable_kw
            if can_cancel <= 0:
                continue
            reduce_kw = min(remaining_to_release, can_cancel)
            prev_kw = ev.secondary_allocs.get(edge.secondary_id, 0)
            # Revised setpoint reflects all pending + newly scheduled reductions on this secondary
            pending_on_edge = edge.pending_release_kw
            revised_kw = max(0, prev_kw - pending_on_edge - reduce_kw)

            earliest_dwell = edge.created_tau + edge.min_dwell_tau
            slew_s = (reduce_kw / edge.slew_rate_kw_per_s) if edge.slew_rate_kw_per_s is not None else 0.0
            effective_tau = max(ack.arrival_tau, earliest_dwell) + slew_s

            idem_key = _make_idempotency_key(
                "CANCEL", ev.event_id, edge.edge_id, edge.secondary_id, ack_key, revised_kw
            )
            cmd = CancelOrRampdownCommand(
                secondary_id=edge.secondary_id,
                event_id=ev.event_id,
                group_id=ev.group_id,
                edge_id=edge.edge_id,
                previous_kw=prev_kw - pending_on_edge,
                revised_kw=revised_kw,
                freed_kw=reduce_kw,
                issued_tau=ack.arrival_tau,
                effective_tau=effective_tau,
                idempotency_key=idem_key,
                reason=reason,
            )
            cancel_cmds.append(cmd)
            self.cancel_log.append(cmd)
            remaining_to_release -= reduce_kw

            if effective_tau <= ack.arrival_tau + 1e-12:
                # Dwell and slew already satisfied -> atomic release & immediate reallocation
                self._commit_release(ev, edge, reduce_kw)
                freed_now_total += reduce_kw
                realloc_cmds.extend(
                    self._reallocate_starved(ev.group_id, ack.arrival_tau, source_edge_id=edge.edge_id)
                )
            else:
                # Respect minimum dwell / slew: hold cap reserved until effective_tau
                edge.pending_release_kw += reduce_kw
                edge.release_effective_tau = max(edge.release_effective_tau or 0.0, effective_tau)
                edge.status = "RAMPING_DOWN"
                deferred_total += reduce_kw
                self._pending_releases.append(
                    PendingCapacityRelease(
                        group_id=ev.group_id,
                        event_id=ev.event_id,
                        edge_id=edge.edge_id,
                        secondary_id=edge.secondary_id,
                        freed_kw=reduce_kw,
                        effective_tau=effective_tau,
                        idempotency_key=idem_key,
                    )
                )

        self.assert_invariants()
        return AckProcessResult(
            event_id=ev.event_id,
            primary_id=pid,
            known_complete_triggered=censored_complete,
            satisfied_delta_kw=int(satisfied_delta),
            freed_capacity_now_kw=freed_now_total,
            deferred_release_kw=deferred_total,
            cancel_commands=tuple(cancel_cmds),
            reallocations=tuple(realloc_cmds),
        )

    def advance_time(self, tau: float) -> list[ReallocationCommand]:
        """Advance intra-slot clock to ``tau``, atomically settling matured dwell/slew releases."""
        tau = float(tau)
        if tau < self.current_tau - 1e-12:
            raise ValueError(f"cannot move clock backwards from {self.current_tau} to {tau}")
        self.current_tau = tau
        reallocs: list[ReallocationCommand] = []
        matured = [p for p in self._pending_releases if not p.settled and p.effective_tau <= tau + 1e-12]
        matured.sort(key=lambda p: (p.effective_tau, p.edge_id))
        for item in matured:
            item.settled = True
            ev = self._events[item.event_id]
            edge = self._edges[item.edge_id]
            edge.pending_release_kw = max(0, edge.pending_release_kw - item.freed_kw)
            self._commit_release(ev, edge, item.freed_kw)
            reallocs.extend(
                self._reallocate_starved(item.group_id, item.effective_tau, source_edge_id=item.edge_id)
            )
        if matured:
            self.assert_invariants()
        return reallocs

    def _commit_release(self, ev: DispatchEvent, edge: HedgeDependencyEdge, freed_kw: int) -> None:
        sec = edge.secondary_id
        prev = ev.secondary_allocs.get(sec, 0)
        if freed_kw > prev:
            raise AssertionError(f"cannot release {freed_kw} kW from secondary {sec} holding {prev} kW")
        new_val = prev - freed_kw
        if new_val == 0:
            ev.secondary_allocs.pop(sec, None)
        else:
            ev.secondary_allocs[sec] = new_val
        edge.released_kw += freed_kw
        if edge.cancellable_kw == 0 and edge.pending_release_kw == 0:
            edge.status = "RELEASED"

    def _reallocate_starved(
        self, group_id: int, effective_tau: float, *, source_edge_id: str
    ) -> list[ReallocationCommand]:
        """Atomically assign freed group headroom ``Delta C_{g,t}`` to starved concurrent events."""
        g = int(group_id)
        avail = self.available_headroom(g)
        if avail <= 0:
            return []
        candidates = [
            ev for ev in self._events.values()
            if ev.group_id == g and ev.starved_demand_kw > 0
        ]
        # Higher priority first, then earliest deadline, then deterministic event_id
        candidates.sort(key=lambda e: (-e.priority, e.deadline_slot, e.event_id))
        issued: list[ReallocationCommand] = []
        for ev in candidates:
            if avail <= 0:
                break
            for dev in sorted(list(ev.starved_requests)):
                if avail <= 0:
                    break
                want = ev.starved_requests.get(dev, 0)
                if want <= 0:
                    continue
                rate_cap = ev.device_rate_cap.get(dev)
                cur_dev = ev.primary_allocs.get(dev, 0) + ev.secondary_allocs.get(dev, 0)
                dev_room = want if rate_cap is None else max(0, min(want, rate_cap - cur_dev))
                grant = min(avail, dev_room)
                if grant <= 0:
                    continue
                ev.primary_allocs[dev] = ev.primary_allocs.get(dev, 0) + grant
                rem = want - grant
                if rem == 0:
                    ev.starved_requests.pop(dev, None)
                else:
                    ev.starved_requests[dev] = rem
                avail -= grant
                cmd = ReallocationCommand(
                    target_event_id=ev.event_id,
                    device_id=dev,
                    group_id=g,
                    allocated_kw=grant,
                    effective_tau=effective_tau,
                    source_edge_id=source_edge_id,
                    idempotency_key=_make_idempotency_key(
                        "REALLOC", ev.event_id, dev, source_edge_id, grant, f"{effective_tau:.6f}"
                    ),
                )
                issued.append(cmd)
                self.reallocation_log.append(cmd)
        return issued


# --------------------------------------------------------------------------- benchmark helper
def _simulate_concurrent_slot_seed(
    seed: int,
    *,
    n_primaries: int = 12,
    n_starved_devices: int = 12,
    shared_cap_kw: int = 18,
    unit_kw: int = 1,
    slot_duration_s: float = 900.0,
    min_dwell_tau: float = 90.0,
    q_intolerant: float = 0.40,
    q_tolerant: float = 0.01,
    prior_events_m: int = 3,
    censored_complete_prob: float = 0.12,
) -> dict[str, dict[str, float]]:
    """Run one paired-CRN concurrent two-event slot comparing dispatch strategies at equal cap.

    Event E1 (urgent, final slot before deadline) has ``n_primaries`` participants
    (1/3 pause-intolerant at ``q=0.40``, 2/3 tolerant at ``q=0.01``), each needing
    ``unit_kw`` with spare backup devices available on the same feeder cap ``shared_cap_kw``.
    Event E2 (concurrent open dispatch event sharing cap-group 0) has ``n_starved_devices``
    reliable participants competing for the same feeder cap ``shared_cap_kw``.

    All strategies share identical draws (CRN) for latent classes, prior history ``M``,
    availability ``A``, censored ``known_complete`` flags, and mid-slot async ack times.
    """
    rng = np.random.Generator(np.random.PCG64(np.random.SeedSequence(int(seed), spawn_key=(37, 1))))
    n_intol = n_primaries // 3
    cls = np.zeros(n_primaries, dtype=np.int64)
    cls[rng.permutation(n_primaries)[:n_intol]] = 1
    q_true = np.where(cls == 1, q_intolerant, q_tolerant)

    # Prior M events -> Beta-Bernoulli e1 posterior (same alpha/beta as paperE)
    alpha, beta = 0.2893769407284573, 1.8112608394382754
    prior_stuck = (rng.random((n_primaries, prior_events_m)) < q_true[:, None]).sum(axis=1)
    q_hat = (alpha + prior_stuck) / (alpha + beta + prior_events_m)

    # Realized event: either already-complete (censored A=-1), available (A=1), or stuck (A=0)
    already_complete = rng.random(n_primaries) < censored_complete_prob
    avail = np.where(already_complete, 1, (rng.random(n_primaries) >= q_true).astype(np.int64))
    # Async confirmation arrives mid-slot for responsive / already-complete devices;
    # stuck devices either confirm late (50%) or stay silent until timeout (50%)
    ack_tau = rng.uniform(0.15 * slot_duration_s, 0.45 * slot_duration_s, size=n_primaries)
    stuck_silent = rng.random(n_primaries) < 0.5
    timeout_tau = 0.65 * slot_duration_s

    kwh_per_kw_full_slot = slot_duration_s / 3600.0  # 0.25 kWh per kW for 15-min slot
    e1_true_demand = int((~already_complete).sum()) * unit_kw
    hedge_budget = max(0, shared_cap_kw - n_primaries * unit_kw)

    # ---------------- Strategy 1: HedgeCap + AsyncRelease --------------------
    ledger = SharedHedgeCapLedger({0: shared_cap_kw}, slot_duration_s=slot_duration_s)
    ledger.open_event(
        "E1_urgent", 0, priority=10, deadline_slot=1,
        device_debt={i: unit_kw for i in range(n_primaries)},
    )
    ledger.open_event(
        "E2_concurrent", 0, priority=5, deadline_slot=2,
        device_debt={100 + j: unit_kw for j in range(n_starved_devices)},
    )
    for i in range(n_primaries):
        ledger.allocate_primary("E1_urgent", i, unit_kw)

    # Target hedges to highest posterior failure probability primaries up to hedge_budget
    ranked = np.argsort(-q_hat, kind="mergesort")
    hedged_primaries: list[int] = []
    for idx in ranked[:hedge_budget]:
        i = int(idx)
        sec_id = 50 + i
        ledger.hedge_dependency_edges(
            primary_id=i, secondary_id=sec_id, event_id="E1_urgent",
            hedged_kw=unit_kw, min_dwell_tau=min_dwell_tau, created_tau=0.0,
        )
        hedged_primaries.append(i)

    # Remaining cap (if any) goes to E2; rest of E2 is registered starved
    for j in range(n_starved_devices):
        ledger.allocate_primary("E2_concurrent", 100 + j, unit_kw, allow_partial=True)

    # Process mid-slot async acks in chronological order
    order = np.argsort(ack_tau)
    e2_reallocated_kwh = 0.0
    hedge_waste_kwslot = 0.0
    censored_releases = 0
    for idx in order:
        i = int(idx)
        tau = float(ack_tau[i])
        if already_complete[i]:
            ack = AsyncAckEvent(
                event_id="E1_urgent", primary_id=i, slot_s=0, arrival_tau=tau,
                delivered_kw=0, availability_obs=UNKNOWN, commanded_kw=unit_kw,
            )
        elif avail[i] == 1:
            ack = AsyncAckEvent(
                event_id="E1_urgent", primary_id=i, slot_s=0, arrival_tau=tau,
                delivered_kw=unit_kw, availability_obs=1, commanded_kw=unit_kw,
            )
        else:
            if stuck_silent[i]:
                continue
            ack = AsyncAckEvent(
                event_id="E1_urgent", primary_id=i, slot_s=0, arrival_tau=tau,
                delivered_kw=0, availability_obs=0, commanded_kw=unit_kw,
            )
        res = ledger.process_async_ack(ack)
        if res.known_complete_triggered and res.cancel_commands:
            censored_releases += 1
        for cmd in res.cancel_commands:
            # Secondary only held redundant load until effective_tau
            frac_held = min(1.0, cmd.effective_tau / slot_duration_s)
            hedge_waste_kwslot += cmd.freed_kw * frac_held
        for rcmd in res.reallocations:
            frac_rem = max(0.0, (slot_duration_s - rcmd.effective_tau) / slot_duration_s)
            e2_reallocated_kwh += rcmd.allocated_kw * frac_rem * kwh_per_kw_full_slot

    # Flush any pending dwell releases before slot end
    for rcmd in ledger.advance_time(slot_duration_s):
        frac_rem = max(0.0, (slot_duration_s - rcmd.effective_tau) / slot_duration_s)
        e2_reallocated_kwh += rcmd.allocated_kw * frac_rem * kwh_per_kw_full_slot

    # E1 delivery: responsive non-complete primaries + hedged stuck primaries
    e1_deliv_kw = 0
    for i in range(n_primaries):
        if already_complete[i]:
            continue
        if avail[i] == 1 or i in hedged_primaries:
            e1_deliv_kw += unit_kw
    e1_deliv_kwh = e1_deliv_kw * kwh_per_kw_full_slot
    e1_shortfall_kwh = (e1_true_demand - e1_deliv_kw) * kwh_per_kw_full_slot
    # Initial E2 allocations (beyond hedge_budget, here 0 when cap=18, n_prim=12, hedge_budget=6)
    e2_init_kw = max(0, shared_cap_kw - n_primaries * unit_kw - len(hedged_primaries) * unit_kw)
    e2_deliv_kwh = e2_init_kw * kwh_per_kw_full_slot + e2_reallocated_kwh

    res_hedgecap = {
        "total_delivered_kwh": e1_deliv_kwh + e2_deliv_kwh,
        "urgent_delivered_kwh": e1_deliv_kwh,
        "urgent_shortfall_kwh": e1_shortfall_kwh,
        "starved_event_delivered_kwh": e2_deliv_kwh,
        "hedge_waste_kwslot": hedge_waste_kwslot,
        "overload_kwslot": 0.0,
        "cancel_commands": float(len(ledger.cancel_log)),
        "reallocated_kw": float(sum(r.allocated_kw for r in ledger.reallocation_log)),
        "censored_releases": float(censored_releases),
    }

    # ---------------- Strategy 2: Static Pooled Overbooking Buffer (Equal Cap) --
    # Allocates same hedge_budget uniformly/blindly without per-asset targeting or
    # mid-slot async cancellation -> holds wasted hedges for full slot, starves E2.
    static_hedged = set(int(x) for x in rng.permutation(n_primaries)[:hedge_budget])
    s2_e1_kw = 0
    s2_waste = 0.0
    for i in range(n_primaries):
        if already_complete[i]:
            if i in static_hedged:
                s2_waste += unit_kw
            continue
        if avail[i] == 1:
            s2_e1_kw += unit_kw
            if i in static_hedged:
                s2_waste += unit_kw
        elif i in static_hedged:
            s2_e1_kw += unit_kw
    s2_e1_kwh = s2_e1_kw * kwh_per_kw_full_slot
    s2_e2_kwh = max(0, shared_cap_kw - n_primaries * unit_kw - len(static_hedged) * unit_kw) * kwh_per_kw_full_slot
    res_static = {
        "total_delivered_kwh": s2_e1_kwh + s2_e2_kwh,
        "urgent_delivered_kwh": s2_e1_kwh,
        "urgent_shortfall_kwh": (e1_true_demand - s2_e1_kw) * kwh_per_kw_full_slot,
        "starved_event_delivered_kwh": s2_e2_kwh,
        "hedge_waste_kwslot": s2_waste,
        "overload_kwslot": 0.0,
        "cancel_commands": 0.0,
        "reallocated_kw": 0.0,
        "censored_releases": 0.0,
    }

    # ---------------- Strategy 3: Wait-for-Confirmation (Equal Cap) ----------
    # Holds backup reserve idle until explicit failure ack (at ack_tau) or timeout
    # (at timeout_tau); then dispatches backup only for the remaining fraction of slot.
    # Unneeded reserve can only be released to E2 after all primaries confirm/timeout.
    s3_e1_kwh = 0.0
    failed_times: list[float] = []
    for i in range(n_primaries):
        if already_complete[i]:
            continue
        if avail[i] == 1:
            s3_e1_kwh += unit_kw * kwh_per_kw_full_slot
        else:
            detect_tau = timeout_tau if stuck_silent[i] else float(ack_tau[i])
            failed_times.append(detect_tau)
    failed_times.sort()
    backups_used = min(hedge_budget, len(failed_times))
    for k_idx in range(backups_used):
        rem_frac = max(0.0, (slot_duration_s - failed_times[k_idx]) / slot_duration_s)
        s3_e1_kwh += unit_kw * rem_frac * kwh_per_kw_full_slot
    # Unused reserve is only freed to E2 after confirmation timeout
    unused_reserve = hedge_budget - backups_used
    s3_e2_kwh = unused_reserve * max(0.0, (slot_duration_s - timeout_tau) / slot_duration_s) * kwh_per_kw_full_slot
    res_wait = {
        "total_delivered_kwh": s3_e1_kwh + s3_e2_kwh,
        "urgent_delivered_kwh": s3_e1_kwh,
        "urgent_shortfall_kwh": e1_true_demand * kwh_per_kw_full_slot - s3_e1_kwh,
        "starved_event_delivered_kwh": s3_e2_kwh,
        "hedge_waste_kwslot": 0.0,
        "overload_kwslot": 0.0,
        "cancel_commands": 0.0,
        "reallocated_kw": float(unused_reserve),
        "censored_releases": 0.0,
    }

    # ---------------- Strategy 4: Blind Physical Overbooking (Violates Cap) --
    # Dispatches E1 primaries + static hedges + E2 without enforcing shared cap ->
    # triggers physical feeder overload whenever primaries succeed.
    s4_e1_kw = s2_e1_kw
    s4_e2_kw = min(n_starved_devices, shared_cap_kw - n_primaries) * unit_kw
    # Realized physical load: responsive non-complete primaries + all static hedges + E2
    phys_load_kw = int(((avail == 1) & (~already_complete)).sum()) * unit_kw + len(static_hedged) * unit_kw + s4_e2_kw
    overload_kw = max(0.0, float(phys_load_kw - shared_cap_kw))
    res_overbook = {
        "total_delivered_kwh": (s4_e1_kw + s4_e2_kw) * kwh_per_kw_full_slot,
        "urgent_delivered_kwh": s4_e1_kw * kwh_per_kw_full_slot,
        "urgent_shortfall_kwh": (e1_true_demand - s4_e1_kw) * kwh_per_kw_full_slot,
        "starved_event_delivered_kwh": s4_e2_kw * kwh_per_kw_full_slot,
        "hedge_waste_kwslot": s2_waste,
        "overload_kwslot": overload_kw,
        "cancel_commands": 0.0,
        "reallocated_kw": 0.0,
        "censored_releases": 0.0,
    }

    return {
        "hedgecap_async_release": res_hedgecap,
        "static_pooled_overbooking": res_static,
        "wait_for_confirmation": res_wait,
        "blind_physical_overbooking": res_overbook,
    }


def benchmark_async_release(
    seeds: Iterable[int] = range(60000, 60050),
    *,
    n_primaries: int = 12,
    n_starved_devices: int = 12,
    shared_cap_kw: int = 18,
    min_dwell_tau: float = 90.0,
    slot_duration_s: float = 900.0,
) -> dict[str, dict[str, float]]:
    """Compare ``HedgeCap + AsyncRelease`` against static pooled buffer & wait-for-confirm.

    Runs on tuning seeds ``60000..60049`` by default (zero overlap with frozen
    development or confirmation seeds) at strictly equal shared cap ``shared_cap_kw``.
    Returns mean metrics per strategy.
    """
    seed_list = [int(s) for s in seeds]
    if not seed_list:
        raise ValueError("seeds must be non-empty")
    per_strategy: dict[str, dict[str, list[float]]] = {}
    for seed in seed_list:
        out = _simulate_concurrent_slot_seed(
            seed,
            n_primaries=n_primaries,
            n_starved_devices=n_starved_devices,
            shared_cap_kw=shared_cap_kw,
            min_dwell_tau=min_dwell_tau,
            slot_duration_s=slot_duration_s,
        )
        for strat, metrics in out.items():
            bucket = per_strategy.setdefault(strat, {k: [] for k in metrics})
            for k, v in metrics.items():
                bucket[k].append(float(v))

    summary: dict[str, dict[str, float]] = {}
    for strat, bucket in per_strategy.items():
        summary[strat] = {
            k: float(np.mean(vals)) for k, vals in bucket.items()
        }
        summary[strat]["n_seeds"] = float(len(seed_list))
    return summary
