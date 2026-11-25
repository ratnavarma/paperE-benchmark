"""Ledger (BUILD_SPEC Sections 1, 8): metrics from a ``Trajectory`` and the clairvoyant bound.

Conventions
-----------
* One unit = 1 kW for one 15-minute slot = 0.25 kWh (``KWH_PER_UNIT``).
* Key suffixes are explicit: ``_u`` integer-or-float energy units, ``_kwh`` kWh,
  ``_kw`` power, ``_kwslot`` kW.slot (violation magnitude, hedge waste), ``_ms`` CPU
  milliseconds, ``_slots`` a count of slots, ``_count`` a participant or event count,
  ``_per100`` a value per 100 participants (energy keys only, plus the two counts).
* kW and kWh never share a key. The event shortfall is its own key and is never added
  to anything.
* The clairvoyant bound is computed on the SAME realized availability the policy faced
  (``traj.A``, floored version included).
* The correctability split is reported as TWO readings (``_hi`` / ``_lo``) and there is
  no single ``R_uncorr`` / ``R_corr`` key, so nothing downstream can silently use one
  reading (OPEN_QUESTIONS rows 7 and 20).
* ``R_avoid`` is raw and may be negative; ``exceeds_bound`` and ``bound_overshoot_*`` say so.
  ``R_avoid_sp`` (bound with the simulator's setpoint caps) is never negative for a policy row (a bound row reports it raw).
* ``violation_longest_run_slots`` is per cap group (the maximum over groups of the longest
  run of consecutive violating slots of that group), not a run of the summed load.
* The returned dict holds only Python ``int``, ``float`` and ``str`` and round-trips
  through ``json``.
"""
from __future__ import annotations

import hashlib

import numpy as np

from .flow import ClairvoyantResult, FlowProblem, clairvoyant, is_feasible, max_flow, peak
from .instance import Instance
from .sim import Trajectory, _slot_caps

__all__ = ["KWH_PER_UNIT", "BoundViolation", "flow_problem", "clair_for", "evaluate",
           "bound_row"]

KWH_PER_UNIT = 0.25
VIOLATION_EPS = 1e-9


class BoundViolation(AssertionError, ValueError):
    """An impossible state: delivery above P*A, debt accounting errors, or a policy beating
    the setpoint-cap bound ``R*_sp`` (every policy obeys those caps).

    Beating the primary bound ``R*`` is NOT impossible (the forecast cap can exceed the
    realized headroom, OPEN_QUESTIONS 31): that is reported as ``exceeds_bound``.
    """


def flow_problem(instance: Instance, A: np.ndarray) -> FlowProblem:
    """Flow problem on the realized instance and availability ``A`` (BUILD_SPEC Section 8).

    ``cap[i, t] = P_i * A_it`` inside ``[a_i, d_i)``, 0 outside;
    ``slot_cap[g, t] = max(0, floor(L - b + 1e-9))``; ``base = b``.
    """
    A = np.asarray(A)
    if A.shape != (instance.N, instance.H):
        raise ValueError(f"A must have shape {(instance.N, instance.H)}, got {A.shape}")
    t = np.arange(instance.H)[None, :]
    window = (t >= instance.a[:, None]) & (t < instance.d[:, None])
    cap = np.where(window, instance.P[:, None].astype(np.int64) * A.astype(np.int64), 0)
    slot_cap = np.maximum(0, np.floor(instance.L - instance.b + 1e-9)).astype(np.int64)
    return FlowProblem(E=instance.E.astype(np.int64), cap=cap.astype(np.int64),
                       group=instance.group.astype(np.int64), slot_cap=slot_cap,
                       base=np.asarray(instance.b, dtype=np.float64))


def a_sha256(A: np.ndarray) -> str:
    """sha256 of the availability array (shape and int64 contents)."""
    A = np.ascontiguousarray(np.asarray(A, dtype=np.int64))
    h = hashlib.sha256()
    h.update(repr(A.shape).encode())
    h.update(A.tobytes())
    return h.hexdigest()


def clair_for(instance: Instance, A: np.ndarray) -> ClairvoyantResult:
    """Clairvoyant bound on ``A``, tagged with the sha256 of ``A`` (``A_sha256``).

    ``evaluate`` rejects a tagged ``clair`` whose tag differs from ``sha256(traj.A)``, so a
    bound cached for the unfloored availability cannot be applied to a floored run.
    """
    c = clairvoyant(flow_problem(instance, A))
    c.A_sha256 = a_sha256(A)
    return c


def _validate_clair(instance: Instance, traj: Trajectory, clair: ClairvoyantResult) -> None:
    """A passed-in bound must have been computed on ``traj.A``."""
    tag = getattr(clair, "A_sha256", None)
    if tag is not None:
        if tag != a_sha256(traj.A):
            raise ValueError("clair was computed on a different availability than traj.A "
                             "(e.g. an unfloored bound for a floored run)")
        return
    # untagged (raw ``clairvoyant`` output): re-derive F* and check the stored flows
    fp = flow_problem(instance, traj.A)
    F, _ = max_flow(fp)
    ok = (int(clair.F_star) == F and int(clair.R_star) == int(fp.E.sum()) - F
          and is_feasible(fp, clair.y) and int(np.asarray(clair.y).sum()) == F
          and is_feasible(fp, clair.min_peak_y) and int(np.asarray(clair.min_peak_y).sum()) == F
          and abs(peak(fp, clair.min_peak_y) - float(clair.min_peak)) < 1e-9
          and np.array_equal(np.asarray(clair.s_own),
                             np.maximum(0, fp.E - fp.cap.sum(axis=1))))
    if not ok:
        raise ValueError("clair does not match flow_problem(instance, traj.A); "
                         "use clair_for(instance, traj.A)")


def bound_row(instance: Instance, A: np.ndarray, clair: ClairvoyantResult | None = None,
              floored: np.ndarray | None = None) -> Trajectory:
    """The clairvoyant bound as a pseudo-trajectory (label ``'bound'``, ``y = x = min_peak_y``).

    ``evaluate`` on it gives R_avoid = 0 and the bound's own peak, violations and misses.
    """
    if clair is None:
        clair = clair_for(instance, A)
    y = np.asarray(clair.min_peak_y, dtype=np.int64).copy()
    N, H = instance.N, instance.H
    before = np.zeros((N, H), dtype=np.int64)
    r = instance.E.astype(np.int64).copy()
    for t in range(H):
        before[:, t] = r
        r = r - y[:, t]
    fl = np.zeros(N, dtype=bool) if floored is None else np.asarray(floored, dtype=bool).copy()
    row = Trajectory(policy="bound", privileged=True, seed=int(instance.seed),
                     cell_id=instance.cell.cell_id, x=y.copy(), y=y,
                     A=np.asarray(A, dtype=np.int64).copy(), r_before=before, r_final=r,
                     floored=fl, cpu_ms=np.zeros(H), rounds=np.ones(H, dtype=np.int64))
    row.is_bound_row = True        # explicit flag read by ``evaluate`` (see ``is_bound``)
    return row


def is_bound(traj: Trajectory) -> bool:
    """True for a row made by ``bound_row`` (it uses realized headroom, not setpoint caps)."""
    return bool(getattr(traj, "is_bound_row", False))


def _longest_run(flags: np.ndarray) -> int:
    best = cur = 0
    for f in flags.tolist():
        cur = cur + 1 if f else 0
        best = max(best, cur)
    return best


def _check_trajectory(instance: Instance, traj: Trajectory) -> None:
    N, H = instance.N, instance.H
    if int(traj.seed) != int(instance.seed):
        raise ValueError(f"trajectory seed {traj.seed} != instance seed {instance.seed}")
    if str(traj.cell_id) != instance.cell.cell_id:
        raise ValueError(f"trajectory cell {traj.cell_id!r} != instance cell "
                         f"{instance.cell.cell_id!r}")
    for name in ("x", "y", "A", "r_before"):
        if getattr(traj, name).shape != (N, H):
            raise ValueError(f"trajectory.{name} must have shape {(N, H)}")
    if traj.r_final.shape != (N,) or traj.floored.shape != (N,):
        raise ValueError("trajectory.r_final and floored must have shape [N]")
    E = instance.E.astype(np.int64)
    y = traj.y.astype(np.int64)
    resid = E - y.sum(axis=1)
    if not np.array_equal(resid, traj.r_final.astype(np.int64)):
        raise BoundViolation("trajectory is inconsistent: r_final != E - sum_t y")
    before = E[:, None] - (np.cumsum(y, axis=1) - y)
    if not np.array_equal(before, traj.r_before.astype(np.int64)):
        raise BoundViolation("trajectory is inconsistent: r_before != E - sum_{s<t} y")
    t_ = np.arange(instance.H)[None, :]
    window = (t_ >= instance.a[:, None]) & (t_ < instance.d[:, None])
    if (y > instance.P[:, None].astype(np.int64) * traj.A.astype(np.int64) * window).any():
        raise BoundViolation("delivery exceeds P_i * A_it inside the window")
    expect = np.minimum(traj.x.astype(np.int64), before) * traj.A.astype(np.int64)
    if not np.array_equal(expect, y):
        raise BoundViolation("trajectory is inconsistent: y != min(x, r_before) * A")


def evaluate(instance: Instance, traj: Trajectory, clair: ClairvoyantResult | None = None,
             delta_A: int | None = None, delta_b: int | None = None) -> dict:
    """All ledger metrics for one run (see module docstring for the key suffixes).

    ``clair`` may be passed to avoid recomputing the bound; it MUST have been computed
    from ``flow_problem(instance, traj.A)`` (the availability this run faced, floored
    version included). ``delta_A`` and ``delta_b`` default to the instance's cell values.

    ``R_avoid`` is reported raw and may be negative (``exceeds_bound``; OPEN_QUESTIONS 31):
    the policy's setpoint cap uses the forecast, the bound uses realized headroom. The
    secondary bound ``R_star_sp`` uses the simulator's enforced setpoint cap, so
    ``R_avoid_sp >= 0`` is a hard invariant for every policy row (``BoundViolation``
    otherwise); a ``bound_row`` row reports it raw (it may be negative) and has
    ``bound_row: true``, ``exceeds_bound: false``.
    """
    _check_trajectory(instance, traj)
    if delta_A is None:
        delta_A = instance.cell.delta_A
    delta_A = int(delta_A)
    delta_b = int(instance.cell.delta_b if delta_b is None else delta_b)
    if clair is None:
        clair = clair_for(instance, traj.A)
    else:
        _validate_clair(instance, traj, clair)
    N, H = instance.N, instance.H
    E = instance.E.astype(np.int64)
    x = traj.x.astype(np.int64)
    y = traj.y.astype(np.int64)
    rb = traj.r_before.astype(np.int64)
    rf = traj.r_final.astype(np.int64)

    # ---- energy ----
    E_tot = int(E.sum())
    D = int(y.sum())
    R_abs = E_tot - D
    R_star = int(clair.R_star)
    R_avoid = R_abs - R_star                      # may be negative (OPEN_QUESTIONS 31)
    exceeds = R_avoid < 0
    overshoot = max(0, -R_avoid)
    fp = flow_problem(instance, traj.A)
    sp_caps = np.stack([_slot_caps(instance, t, delta_b) for t in range(H)], axis=1)
    fp_sp = FlowProblem(E=fp.E, cap=fp.cap, group=fp.group, slot_cap=sp_caps, base=fp.base)
    R_star_sp = E_tot - int(max_flow(fp_sp)[0])
    R_avoid_sp = R_abs - R_star_sp
    bound = is_bound(traj)
    if bound:
        # the bound uses realized headroom and can exceed R*_sp; R_avoid = 0 by construction
        exceeds = False
        overshoot = 0
    elif R_avoid_sp < 0:
        raise BoundViolation(f"R_avoid_sp = {R_avoid_sp} < 0: run {traj.policy!r} beats the "
                             f"setpoint-cap bound (R_abs={R_abs}, R*_sp={R_star_sp})")
    s_own = int(np.asarray(clair.s_own).sum())
    R_couple = int(clair.R_couple)

    # ---- deadline misses ----
    missed = rf > 0
    miss_count = int(missed.sum())
    miss_u = int(rf[missed].sum())

    # ---- peak and violations ----
    load = np.zeros((instance.n_groups, H))
    np.add.at(load, instance.group, y)
    load = load + instance.b                      # physical load ell[g, t]
    peak_kw = float(load.sum(axis=0).max()) if H else 0.0
    v = load - instance.L
    viol = v > VIOLATION_EPS
    viol_count = int(viol.sum())
    viol_kwslot = float(v[viol].sum())
    longest = max((_longest_run(viol[g]) for g in range(instance.n_groups)), default=0)

    # ---- hedge waste ----
    hedge = int((x * (rb == 0)).sum())

    # ---- correctability split (OPEN_QUESTIONS rows 7 and 20; two readings) ----
    # Availability is fixed within a slot, so a failure is never retried in the same slot,
    # even at delta_A = 0: the lag is max(delta_A, 1).
    s_idx = np.arange(H)[None, :]
    late = (s_idx + max(delta_A, 1)) >= instance.d[:, None]
    failed = np.minimum(x, rb) - y                # units lost on failed setpoints
    lost_uncorr = (failed * late).sum(axis=1)
    s_own_i = np.asarray(clair.s_own, dtype=np.int64)
    u = np.minimum(np.maximum(0, rf - s_own_i), lost_uncorr)
    u_sum = int(u.sum())
    cap_u = max(R_avoid, 0)                       # readings clipped to [0, max(R_avoid, 0)]
    R_uncorr_hi = min(cap_u, u_sum)
    R_uncorr_lo = min(cap_u, max(0, u_sum - R_couple))
    R_corr_hi = R_avoid - R_uncorr_lo             # equals R_avoid (<= 0) when R_avoid <= 0
    R_corr_lo = R_avoid - R_uncorr_hi

    # ---- event shortfall (floor), never summed with anything ----
    n_floored = int(np.asarray(traj.floored, dtype=bool).sum())
    event_u = 2 * n_floored

    # ---- bound summary ----
    lex = np.asarray(clair.leximin_shortfall, dtype=np.int64)
    frac = np.where(E > 0, lex / np.maximum(E, 1), 0.0)

    cpu = np.asarray(traj.cpu_ms, dtype=np.float64)

    out: dict = {
        "policy": str(traj.policy), "privileged": bool(traj.privileged),
        "seed": int(traj.seed), "cell_id": str(traj.cell_id),
        "family": str(instance.family), "N": int(N), "H": int(H), "delta_A": delta_A, "delta_b": delta_b,
        "A_sha256": a_sha256(traj.A),
    }

    def energy(name: str, units) -> None:
        out[f"{name}_u"] = float(units)
        out[f"{name}_kwh"] = float(units) * KWH_PER_UNIT

    energy("E", E_tot)
    energy("D", D)
    energy("R_abs", R_abs)
    energy("R_star", R_star)
    energy("R_avoid", R_avoid)
    energy("R_star_sp", R_star_sp)
    energy("R_avoid_sp", R_avoid_sp)
    out["exceeds_bound"] = bool(exceeds)
    out["bound_row"] = bound
    energy("bound_overshoot", overshoot)
    energy("s_own", s_own)
    energy("R_couple", R_couple)
    out["deadline_miss_count"] = miss_count
    energy("deadline_miss", miss_u)
    out["peak_kw"] = peak_kw
    out["violation_count"] = viol_count
    out["violation_kwslot"] = viol_kwslot
    out["violation_longest_run_slots"] = int(longest)
    out["hedge_waste_kwslot"] = float(hedge)
    energy("u_raw", u_sum)
    energy("R_uncorr_hi", R_uncorr_hi)
    energy("R_uncorr_lo", R_uncorr_lo)
    energy("R_corr_hi", R_corr_hi)
    energy("R_corr_lo", R_corr_lo)
    energy("event_shortfall", event_u)
    out["floored_count"] = n_floored
    out["cpu_mean_ms"] = float(cpu.mean()) if cpu.size else 0.0
    out["cpu_max_ms"] = float(cpu.max()) if cpu.size else 0.0
    out["bound_max_short_frac"] = float(frac.max()) if frac.size else 0.0
    out["bound_short_count"] = int((lex > 0).sum())
    out["bound_min_peak_kw"] = float(clair.min_peak)

    per100 = {}
    for k, val in out.items():
        if (k.endswith("_u") or k.endswith("_kwh") or k in
                ("deadline_miss_count", "violation_count")) and not isinstance(val, bool):
            per100[f"{k}_per100"] = float(val) * 100.0 / N
    out.update(per100)
    return out
