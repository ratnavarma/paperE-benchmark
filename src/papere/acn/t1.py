"""T1: empirical frequency of the uncorrectable regime (protocol section 1, claim C1).

Event end time ``e``: 17:00 local (primary); 15:00 and 19:00 (sensitivity).
Population: sessions connected at ``e`` on an eligible weekday site-day, with
remaining need ``need - delivered(e) >= 0.25`` kWh.
Recovery window: ``w = disconnect - e`` (in minutes).
Regime indicator for delay ``delta`` in ``{15, 30, 60}`` minutes: ``w < delta + 15``.
Outputs per site and pooled: share in regime, energy-at-risk ratio, and 95%
bootstrap intervals over site-days (10,000 resamples, generator seed 710000).
"""
from __future__ import annotations

from typing import Mapping, Sequence

import numpy as np

from papere.analysis import Bootstrap, safe_ratio

from .load import MIN_SESSIONS_PER_DAY, Session, SiteDay, eligible_site_days, sessions_connected_at

T1_EVENT_HOURS: tuple[int, ...] = (17, 15, 19)
T1_DELTAS_MIN: tuple[int, ...] = (15, 30, 60)
T1_MIN_REMAINING_KWH = 0.25
T1_SLOT_MIN = 15.0
T1_N_BOOT = 10_000
T1_BOOT_SEED = 710_000


def in_uncorrectable_regime(recovery_window_min: float, delta_min: float) -> bool:
    """Protocol section 1 regime indicator: ``w < delta + 15`` minutes."""
    return float(recovery_window_min) < float(delta_min) + T1_SLOT_MIN


def _site_day_population(
    sessions: Sequence[Session],
    site_day: SiteDay,
    event_hour: int,
    *,
    min_remaining_kwh: float = T1_MIN_REMAINING_KWH,
) -> list[tuple[float, float]]:
    """Return ``[(recovery_window_min, remaining_kwh), ...]`` for population sessions at ``e``."""
    e_ts = site_day.event_timestamp(event_hour, 0)
    out: list[tuple[float, float]] = []
    for s in sessions_connected_at(sessions, e_ts):
        rem = s.remaining_need_at(e_ts)
        if rem >= min_remaining_kwh:
            w_min = (s.disconnect_ts - e_ts) / 60.0
            out.append((w_min, rem))
    return out


def _aggregate_group(
    day_pops: Sequence[list[tuple[float, float]]],
    deltas_min: Sequence[int],
    boot: Bootstrap,
) -> dict[str, dict]:
    """Compute share, energy-at-risk and bootstrap CIs across ``day_pops`` for each delta."""
    n_days = len(day_pops)
    n_pop_vec = np.array([len(p) for p in day_pops], dtype=np.float64)
    rem_pop_vec = np.array([sum(rem for _, rem in p) for p in day_pops], dtype=np.float64)
    n_days_with_pop = int(np.sum(n_pop_vec > 0))

    by_delta: dict[str, dict] = {}
    for d_min in deltas_min:
        n_reg_vec = np.array(
            [sum(1 for w, _ in p if in_uncorrectable_regime(w, d_min)) for p in day_pops],
            dtype=np.float64,
        )
        rem_reg_vec = np.array(
            [sum(rem for w, rem in p if in_uncorrectable_regime(w, d_min)) for p in day_pops],
            dtype=np.float64,
        )
        res = boot.run(
            {
                "n_reg": n_reg_vec,
                "n_pop": n_pop_vec,
                "rem_reg": rem_reg_vec,
                "rem_pop": rem_pop_vec,
            },
            {
                "share": lambda m: safe_ratio(m["n_reg"], m["n_pop"]),
                "energy_at_risk": lambda m: safe_ratio(m["rem_reg"], m["rem_pop"]),
            },
        )
        st_share = res["share"]
        st_ear = res["energy_at_risk"]
        by_delta[str(int(d_min))] = {
            "delta_min": int(d_min),
            "n_site_days": int(n_days),
            "n_site_days_with_pop": n_days_with_pop,
            "n_pop_sessions": int(n_pop_vec.sum()),
            "n_regime_sessions": int(n_reg_vec.sum()),
            "total_remaining_kwh": float(rem_pop_vec.sum()),
            "regime_remaining_kwh": float(rem_reg_vec.sum()),
            "share": st_share.value,
            "share_ci": [st_share.lo, st_share.hi],
            "energy_at_risk": st_ear.value,
            "energy_at_risk_ci": [st_ear.lo, st_ear.hi],
        }
    return by_delta


def evaluate_t1(
    sessions_by_site: Mapping[str, Sequence[Session]],
    *,
    event_hours: Sequence[int] = T1_EVENT_HOURS,
    deltas_min: Sequence[int] = T1_DELTAS_MIN,
    min_sessions_per_day: int = MIN_SESSIONS_PER_DAY,
    n_boot: int = T1_N_BOOT,
    boot_seed: int = T1_BOOT_SEED,
) -> dict:
    """Compute T1 shares, energy-at-risk ratios and 95% bootstrap intervals per site and pooled.

    Returns a JSON-serializable dict keyed by ``"meta"``, ``"sites"`` and ``"pooled"``,
    each mapping ``"<hour>:00"`` -> ``"<delta_min>"`` -> statistics dict.
    """
    boot = Bootstrap(n_boot=n_boot, seed=boot_seed, level=0.95)
    site_names = sorted(sessions_by_site.keys())
    site_days_map: dict[str, list[SiteDay]] = {
        site: eligible_site_days(sessions_by_site[site], min_sessions=min_sessions_per_day)
        for site in site_names
    }

    sites_out: dict[str, dict] = {site: {} for site in site_names}
    pooled_out: dict[str, dict] = {}

    for hour in event_hours:
        e_key = f"{int(hour):02d}:00"
        pooled_day_pops: list[list[tuple[float, float]]] = []
        for site in site_names:
            sess = sessions_by_site[site]
            days = site_days_map[site]
            day_pops = [_site_day_population(sess, sd, int(hour)) for sd in days]
            sites_out[site][e_key] = _aggregate_group(day_pops, deltas_min, boot)
            pooled_day_pops.extend(day_pops)
        pooled_out[e_key] = _aggregate_group(pooled_day_pops, deltas_min, boot)

    return {
        "meta": {
            "event_hours": [int(h) for h in event_hours],
            "deltas_min": [int(d) for d in deltas_min],
            "min_remaining_kwh": T1_MIN_REMAINING_KWH,
            "min_sessions_per_day": int(min_sessions_per_day),
            "n_boot": int(n_boot),
            "boot_seed": int(boot_seed),
            "site_day_counts": {site: len(site_days_map[site]) for site in site_names},
            "pooled_site_day_count": sum(len(v) for v in site_days_map.values()),
        },
        "sites": sites_out,
        "pooled": pooled_out,
    }
