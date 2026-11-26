"""T3: inferred failures to resume and per-user persistence (protocol section 2, H3).

Rules (``acn/PROTOCOL_ACN.md`` section 2):
- 1-minute LOCF grid of pilot and current while connected.
- Pause: ``pilot <= 6 A`` for at least 15 consecutive minutes.
- Resume event: the first minute after a pause where ``pilot >= 8 A``, provided:
  (a) ``need_source == "requested"``,
  (b) remaining need at that minute ``>= 1 kWh``,
  (c) the vehicle stays connected and ``pilot >= 8 A`` for the next 15 minutes.
  Events failing (a), (b), or (c) are not counted.
- Failure to resume: ``current <= 1 A`` in every minute of those 15 minutes.
  Otherwise success.
- Outputs: pooled and per-site failure rates with Wilson 95% intervals; event, session
  and user counts; Tarone's score test for binomial overdispersion on users with
  ``userID`` and at least 5 resume events; beta-binomial MLE ``(alpha, beta)`` and
  intraclass correlation using the same optimization method as ``population_params.json``.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
import math
from typing import Mapping, Sequence

import numpy as np
from scipy.optimize import minimize
from scipy.special import betaln, gammaln
from scipy.stats import norm

from .load import Session

PAUSE_PILOT_MAX_A = 6.0
PAUSE_MIN_MINUTES = 15
RESUME_PILOT_MIN_A = 8.0
RESUME_WINDOW_MINUTES = 15
RESUME_MIN_REMAINING_KWH = 1.0
FAILURE_CURRENT_MAX_A = 1.0
H3_MIN_EVENTS_PER_USER = 5


@dataclass(frozen=True)
class ResumeEvent:
    """One valid (counted) resume event on a session."""

    site: str
    session_id: str
    user_id: str | None
    minute_index: int
    event_ts: float
    remaining_kwh: float
    failed: bool


def detect_resume_events(session: Session) -> tuple[list[ResumeEvent], dict[str, int]]:
    """Detect all valid resume events and exclusion counts on a single cleaned session."""
    pilot = session.pilot_1m
    current = session.current_1m
    grid_ts = session.grid_ts
    n = pilot.size
    counts = {
        "candidates": 0,
        "excluded_need_source": 0,
        "excluded_remaining_need": 0,
        "excluded_window_or_pilot": 0,
    }
    events: list[ResumeEvent] = []

    pause_run = 0
    in_pause = False

    for m in range(n):
        p = float(pilot[m])
        if not math.isfinite(p):
            pause_run = 0
            continue
        if p <= PAUSE_PILOT_MAX_A:
            pause_run += 1
            if pause_run >= PAUSE_MIN_MINUTES:
                in_pause = True
            continue

        # pilot > 6 A breaks a pause run, but if already in_pause we wait for first pilot >= 8 A
        pause_run = 0
        if not in_pause:
            continue

        if p >= RESUME_PILOT_MIN_A:
            in_pause = False
            counts["candidates"] += 1
            # (a) need_source == "requested"
            if session.need_source != "requested":
                counts["excluded_need_source"] += 1
                continue
            t_r = float(grid_ts[m])
            # (b) remaining need at that minute >= 1 kWh
            rem = session.remaining_need_at(t_r)
            if rem < RESUME_MIN_REMAINING_KWH:
                counts["excluded_remaining_need"] += 1
                continue
            # (c) stays connected and pilot >= 8 A for the next 15 minutes
            end_m = m + RESUME_WINDOW_MINUTES
            if (
                end_m > n
                or (t_r + RESUME_WINDOW_MINUTES * 60.0) > session.disconnect_ts + 1e-9
            ):
                counts["excluded_window_or_pilot"] += 1
                continue
            p_win = pilot[m:end_m]
            if not bool(np.all(np.isfinite(p_win) & (p_win >= RESUME_PILOT_MIN_A))):
                counts["excluded_window_or_pilot"] += 1
                continue

            c_win = current[m:end_m]
            failed = bool(np.all(np.isfinite(c_win) & (c_win <= FAILURE_CURRENT_MAX_A)))
            events.append(
                ResumeEvent(
                    site=session.site,
                    session_id=session.session_id,
                    user_id=session.user_id,
                    minute_index=m,
                    event_ts=t_r,
                    remaining_kwh=rem,
                    failed=failed,
                )
            )

    return events, counts


def wilson_interval(k: int, n: int, level: float = 0.95) -> tuple[float, float]:
    """Wilson score confidence interval for ``k`` events out of ``n`` trials."""
    if n <= 0:
        return math.nan, math.nan
    z = float(norm.ppf(0.5 + level / 2.0))
    z2 = z * z
    p = k / n
    denom = 1.0 + z2 / n
    center = (p + z2 / (2.0 * n)) / denom
    half = (z / denom) * math.sqrt(p * (1.0 - p) / n + z2 / (4.0 * n * n))
    return max(0.0, center - half), min(1.0, center + half)


def tarone_overdispersion_test(
    failures: Sequence[int],
    trials: Sequence[int],
) -> dict:
    """Tarone's score test for binomial overdispersion against a common rate.

    Formula (Tarone, R. E., 1979, 'Testing the goodness of fit of the binomial
    distribution', Biometrika 66(3), 585-590, eq. (6)):

    Given K groups with counts ``x_i`` out of ``n_i`` trials (i = 1..K) and
    pooled rate ``p_hat = sum(x_i) / sum(n_i)``:

        S = sum_i (x_i - n_i * p_hat)^2 / (p_hat * (1 - p_hat))
        Z = (S - sum_i n_i) / sqrt(2 * sum_i n_i * (n_i - 1))

    Under the null of a common binomial rate, ``Z`` is asymptotically standard
    normal. Overdispersion corresponds to ``Z > 0``, so the one-sided p-value is
    ``1 - Phi(Z) = norm.sf(Z)``.
    """
    x = np.asarray(failures, dtype=np.float64)
    n = np.asarray(trials, dtype=np.float64)
    if x.shape != n.shape:
        raise ValueError("failures and trials must have identical shape")
    k_groups = int(x.size)
    tot_n = float(n.sum()) if k_groups else 0.0
    tot_x = float(x.sum()) if k_groups else 0.0
    denom_var = float(np.sum(n * (n - 1.0))) if k_groups else 0.0

    if k_groups < 2 or tot_n <= 0.0 or denom_var <= 0.0:
        return {
            "n_users": k_groups,
            "total_events": int(tot_n),
            "total_failures": int(tot_x),
            "p_hat": tot_x / tot_n if tot_n > 0.0 else math.nan,
            "s_stat": math.nan,
            "z_stat": math.nan,
            "p_value": math.nan,
            "p_value_two_sided": math.nan,
            "h3_supported": False,
        }

    p_hat = tot_x / tot_n
    if p_hat <= 0.0 or p_hat >= 1.0:
        return {
            "n_users": k_groups,
            "total_events": int(tot_n),
            "total_failures": int(tot_x),
            "p_hat": float(p_hat),
            "s_stat": math.nan,
            "z_stat": math.nan,
            "p_value": math.nan,
            "p_value_two_sided": math.nan,
            "h3_supported": False,
        }

    s_stat = float(np.sum((x - n * p_hat) ** 2) / (p_hat * (1.0 - p_hat)))
    z_stat = (s_stat - tot_n) / math.sqrt(2.0 * denom_var)
    p_one = float(norm.sf(z_stat))
    p_two = float(2.0 * norm.sf(abs(z_stat)))
    return {
        "n_users": k_groups,
        "total_events": int(tot_n),
        "total_failures": int(tot_x),
        "p_hat": float(p_hat),
        "s_stat": s_stat,
        "z_stat": float(z_stat),
        "p_value": p_one,
        "p_value_two_sided": p_two,
        "h3_supported": bool(p_one < 0.05),
    }


def beta_binomial_mle(
    failures: Sequence[int],
    trials: Sequence[int],
) -> dict:
    """Beta-binomial MLE ``(alpha, beta)`` for variable ``n_i`` using the ``fit.py`` method.

    Uses ``scipy.optimize.minimize(..., method="L-BFGS-B", bounds=[(-8, 8), (-8, 8)])``
    on log-parameters from three concentration starts ``(0.5, 2.0, 10.0)``, matching
    ``src/papere/fit.py`` and ``results/population_params.json``.
    """
    k = np.asarray(failures, dtype=np.float64)
    n = np.asarray(trials, dtype=np.float64)
    if k.shape != n.shape:
        raise ValueError("failures and trials must have identical shape")
    if k.size == 0 or float(n.sum()) <= 0.0:
        return {
            "n_users": int(k.size),
            "alpha": math.nan,
            "beta": math.nan,
            "beta_binomial_mean": math.nan,
            "intra_class_correlation": math.nan,
            "pooled_rate": math.nan,
            "loglik_beta_binomial": math.nan,
            "loglik_binomial": math.nan,
            "lrt_statistic": math.nan,
        }

    logc = gammaln(n + 1.0) - gammaln(k + 1.0) - gammaln(n - k + 1.0)

    def nll(theta: np.ndarray) -> float:
        a, b = np.exp(theta)
        return -float(np.sum(logc + betaln(k + a, n - k + b) - betaln(a, b)))

    pooled = float(k.sum() / n.sum())
    p0 = float(np.clip(pooled, 1e-3, 1.0 - 1e-3))
    best = None
    for conc in (0.5, 2.0, 10.0):
        x0 = np.log([p0 * conc, (1.0 - p0) * conc])
        res = minimize(nll, x0, method="L-BFGS-B", bounds=[(-8.0, 8.0), (-8.0, 8.0)])
        if best is None or res.fun < best.fun:
            best = res

    alpha, beta = (float(v) for v in np.exp(best.x))
    ll_bb = -float(best.fun)

    if 0.0 < pooled < 1.0:
        ll_bin = float(np.sum(logc + k * np.log(pooled) + (n - k) * np.log1p(-pooled)))
    else:
        ll_bin = 0.0

    return {
        "n_users": int(k.size),
        "alpha": alpha,
        "beta": beta,
        "beta_binomial_mean": alpha / (alpha + beta),
        "intra_class_correlation": 1.0 / (alpha + beta + 1.0),
        "pooled_rate": pooled,
        "loglik_beta_binomial": ll_bb,
        "loglik_binomial": ll_bin,
        "lrt_statistic": 2.0 * (ll_bb - ll_bin),
    }


def _summarize_events(
    events: Sequence[ResumeEvent],
    n_cleaned_sessions: int,
    exclusions: dict[str, int],
) -> dict:
    n_ev = len(events)
    n_fail = sum(1 for e in events if e.failed)
    rate = (n_fail / n_ev) if n_ev > 0 else math.nan
    lo, hi = wilson_interval(n_fail, n_ev, level=0.95)
    sess_ids = {e.session_id for e in events}
    user_ids = {e.user_id for e in events if e.user_id is not None}
    return {
        "n_cleaned_sessions": int(n_cleaned_sessions),
        "n_events": int(n_ev),
        "n_failures": int(n_fail),
        "n_sessions_with_events": len(sess_ids),
        "n_users_with_events": len(user_ids),
        "failure_rate": rate,
        "wilson_95_ci": [lo, hi],
        "exclusions": dict(exclusions),
    }


def evaluate_t3(
    sessions_by_site: Mapping[str, Sequence[Session]],
    *,
    min_user_events: int = H3_MIN_EVENTS_PER_USER,
) -> dict:
    """Compute T3 inferred failure rates, Wilson CIs, Tarone's test and beta-binomial fit."""
    site_names = sorted(sessions_by_site.keys())
    sites_out: dict[str, dict] = {}
    all_events: list[ResumeEvent] = []
    pooled_excl = {
        "candidates": 0,
        "excluded_need_source": 0,
        "excluded_remaining_need": 0,
        "excluded_window_or_pilot": 0,
    }
    total_cleaned = 0

    for site in site_names:
        sess_list = sessions_by_site[site]
        total_cleaned += len(sess_list)
        site_events: list[ResumeEvent] = []
        site_excl = {k: 0 for k in pooled_excl}
        for s in sess_list:
            ev, ex = detect_resume_events(s)
            site_events.extend(ev)
            for k, v in ex.items():
                site_excl[k] += v
                pooled_excl[k] += v
        all_events.extend(site_events)
        sites_out[site] = _summarize_events(site_events, len(sess_list), site_excl)

    pooled_summary = _summarize_events(all_events, total_cleaned, pooled_excl)

    # Per-user aggregation across all sites (users with non-empty userID)
    user_trials: dict[str, int] = defaultdict(int)
    user_fails: dict[str, int] = defaultdict(int)
    for ev in all_events:
        if ev.user_id is None:
            continue
        user_trials[ev.user_id] += 1
        if ev.failed:
            user_fails[ev.user_id] += 1

    all_uids = sorted(user_trials.keys())
    h3_uids = [u for u in all_uids if user_trials[u] >= int(min_user_events)]

    h3_fails = [user_fails[u] for u in h3_uids]
    h3_trials = [user_trials[u] for u in h3_uids]
    all_fails = [user_fails[u] for u in all_uids]
    all_trials = [user_trials[u] for u in all_uids]

    tarone = tarone_overdispersion_test(h3_fails, h3_trials)
    bb_h3 = beta_binomial_mle(h3_fails, h3_trials)
    bb_all = beta_binomial_mle(all_fails, all_trials)

    per_user_counts = {
        u: {"n_events": user_trials[u], "n_failures": user_fails[u]}
        for u in all_uids
    }

    return {
        "meta": {
            "note": "Inferred failures to resume under protocol section 2 pilot/current rules.",
            "pause_pilot_max_a": PAUSE_PILOT_MAX_A,
            "pause_min_minutes": PAUSE_MIN_MINUTES,
            "resume_pilot_min_a": RESUME_PILOT_MIN_A,
            "resume_window_minutes": RESUME_WINDOW_MINUTES,
            "resume_min_remaining_kwh": RESUME_MIN_REMAINING_KWH,
            "failure_current_max_a": FAILURE_CURRENT_MAX_A,
            "h3_min_events_per_user": int(min_user_events),
        },
        "sites": sites_out,
        "pooled": pooled_summary,
        "persistence_h3": {
            "min_events_per_user": int(min_user_events),
            "tarone": tarone,
            "beta_binomial_h3_users": bb_h3,
            "beta_binomial_all_users": bb_all,
        },
        "per_user_counts": per_user_counts,
    }
