"""Tests for papere.acn.t3: pause/resume detection, Wilson CI, Tarone test, beta-binomial MLE."""
from __future__ import annotations

from datetime import datetime, timedelta
import math
from zoneinfo import ZoneInfo

import numpy as np
import pytest
from scipy.stats import norm

from papere.acn.load import clean_session
from papere.acn.t3 import (
    beta_binomial_mle,
    detect_resume_events,
    evaluate_t3,
    tarone_overdispersion_test,
    wilson_interval,
)
from papere.fit import beta_binomial_mle as fit_beta_binomial_mle

LA = ZoneInfo("America/Los_Angeles")


def _rfc2822_utc(dt_local: datetime) -> str:
    return dt_local.astimezone(ZoneInfo("UTC")).strftime("%a, %d %b %Y %H:%M:%S GMT")


def _trace_session(
    pilot_by_min: list[float],
    current_by_min: list[float],
    *,
    kwh_delivered: float = 5.0,
    kwh_requested: float | None = 15.0,
    user_id: str | None = "u1",
    sid: str = "s1",
):
    base = datetime(2019, 11, 4, 12, 0, tzinfo=LA)
    n = len(pilot_by_min)
    disc = base + timedelta(minutes=n)
    raw = {
        "sessionID": sid,
        "userID": user_id,
        "timezone": "America/Los_Angeles",
        "connectionTime": _rfc2822_utc(base),
        "disconnectTime": _rfc2822_utc(disc),
        "kWhDelivered": kwh_delivered,
        "userInputs": [{"kWhRequested": kwh_requested}] if kwh_requested is not None else None,
        "pilotSignal": {
            "timestamps": [_rfc2822_utc(base + timedelta(minutes=m)) for m in range(n)],
            "pilot": pilot_by_min,
        },
        "chargingCurrent": {
            "timestamps": [_rfc2822_utc(base + timedelta(minutes=m)) for m in range(n)],
            "current": current_by_min,
        },
    }
    sess = clean_session(raw, site="caltech")
    assert sess is not None
    return sess


def test_resume_success_failure_and_exclusions():
    # 1. Success: 15 min pause (pilot=0), 15 min resume (pilot=16, current rises to 12 A)
    s_ok = _trace_session(
        pilot_by_min=[0.0] * 15 + [16.0] * 15,
        current_by_min=[0.0] * 15 + [0.0, 0.5, 12.0] + [12.0] * 12,
        kwh_delivered=3.0,
        kwh_requested=10.0,
        sid="ok",
    )
    ev, ex = detect_resume_events(s_ok)
    assert len(ev) == 1 and ev[0].failed is False and ev[0].minute_index == 15
    assert ex["candidates"] == 1

    # 2. Failure: 15 min pause (pilot=6 A), 1 min intermediate 7 A, then 15 min pilot=8 A, current<=1 A
    s_fail = _trace_session(
        pilot_by_min=[16.0] * 10 + [6.0] * 15 + [7.0] + [8.0] * 15,
        current_by_min=[16.0] * 10 + [0.0] * 15 + [0.0] + [0.5] * 15,
        kwh_delivered=2.0,
        kwh_requested=10.0,
        sid="fail",
    )
    ev, ex = detect_resume_events(s_fail)
    assert len(ev) == 1 and ev[0].failed is True and ev[0].minute_index == 26

    # 3. Pause too short (14 min) -> no candidate
    s_short_pause = _trace_session(
        pilot_by_min=[0.0] * 14 + [16.0] * 20,
        current_by_min=[0.0] * 14 + [0.0] * 20,
        sid="short_pause",
    )
    ev, ex = detect_resume_events(s_short_pause)
    assert len(ev) == 0 and ex["candidates"] == 0

    # 4. Excluded by (a): need_source != "requested"
    s_no_req = _trace_session(
        pilot_by_min=[0.0] * 15 + [16.0] * 15,
        current_by_min=[0.0] * 30,
        kwh_requested=None,
        sid="no_req",
    )
    ev, ex = detect_resume_events(s_no_req)
    assert len(ev) == 0 and ex["excluded_need_source"] == 1

    # 5. Excluded by (b): remaining need < 1.0 kWh at resume minute
    # 10 min at 20 A before pause delivers all 5.0 kWh -> remaining = 5.5 - 5.0 = 0.5 < 1.0
    s_low_rem = _trace_session(
        pilot_by_min=[20.0] * 10 + [0.0] * 15 + [16.0] * 15,
        current_by_min=[20.0] * 10 + [0.0] * 30,
        kwh_delivered=5.0,
        kwh_requested=5.5,
        sid="low_rem",
    )
    ev, ex = detect_resume_events(s_low_rem)
    assert len(ev) == 0 and ex["excluded_remaining_need"] == 1

    # 6. Excluded by (c1): disconnects after only 14 minutes of resume
    s_short_win = _trace_session(
        pilot_by_min=[0.0] * 15 + [16.0] * 14,
        current_by_min=[0.0] * 29,
        sid="short_win",
    )
    ev, ex = detect_resume_events(s_short_win)
    assert len(ev) == 0 and ex["excluded_window_or_pilot"] == 1

    # 7. Excluded by (c2): pilot drops below 8 A at minute 10 of resume window
    s_drop = _trace_session(
        pilot_by_min=[0.0] * 15 + [16.0] * 9 + [6.0] + [16.0] * 10,
        current_by_min=[0.0] * 35,
        sid="drop",
    )
    ev, ex = detect_resume_events(s_drop)
    assert len(ev) == 0 and ex["excluded_window_or_pilot"] == 1


def test_tarone_overdispersion_known_example():
    # Exact hand-calculated example:
    # 4 users each with n_i = 10 trials; failures x = [0, 0, 10, 10]
    # p_hat = 20 / 40 = 0.5 -> p*(1-p) = 0.25
    # S = sum((x_i - 5)^2) / 0.25 = (25 + 25 + 25 + 25) / 0.25 = 400.0
    # sum(n_i) = 40, sum(n_i * (n_i - 1)) = 4 * 90 = 360
    # Z = (400 - 40) / sqrt(2 * 360) = 360 / sqrt(720) = 13.416407864998739
    res = tarone_overdispersion_test([0, 0, 10, 10], [10, 10, 10, 10])
    expected_z = (400.0 - 40.0) / math.sqrt(2.0 * 360.0)
    assert res["s_stat"] == pytest.approx(400.0)
    assert res["z_stat"] == pytest.approx(expected_z)
    assert res["p_value"] == pytest.approx(float(norm.sf(expected_z)))
    assert res["h3_supported"] is True

    # Underdispersed / exact equal rate: x = [5, 5, 5, 5], n = [10, 10, 10, 10] -> S = 0, Z < 0
    res_eq = tarone_overdispersion_test([5, 5, 5, 5], [10, 10, 10, 10])
    assert res_eq["s_stat"] == pytest.approx(0.0)
    assert res_eq["z_stat"] == pytest.approx(-40.0 / math.sqrt(720.0))
    assert res_eq["h3_supported"] is False


def test_wilson_interval_and_beta_binomial_matches_fit_py():
    lo, hi = wilson_interval(0, 10, level=0.95)
    assert lo == pytest.approx(0.0)
    assert 0.25 < hi < 0.35

    lo50, hi50 = wilson_interval(50, 100, level=0.95)
    assert lo50 == pytest.approx(1.0 - hi50)
    assert 0.39 < lo50 < 0.41

    # Compare variable-n beta_binomial_mle against papere.fit.beta_binomial_mle when all n_i == 5
    counts = np.array([0, 0, 0, 1, 0, 3, 4, 2, 0, 5, 1, 0, 4, 0, 0], dtype=np.int64)
    a_ref, b_ref, ll_ref = fit_beta_binomial_mle(counts, 5)
    got = beta_binomial_mle(counts, np.full_like(counts, 5))
    assert got["alpha"] == pytest.approx(a_ref, rel=1e-5)
    assert got["beta"] == pytest.approx(b_ref, rel=1e-5)
    assert got["loglik_beta_binomial"] == pytest.approx(ll_ref, rel=1e-6)
    assert got["intra_class_correlation"] == pytest.approx(1.0 / (a_ref + b_ref + 1.0), rel=1e-5)


def test_evaluate_t3_end_to_end():
    # Two users with 5 events each: u_bad fails all 5, u_good succeeds all 5
    sessions = []
    for i in range(5):
        sessions.append(
            _trace_session(
                pilot_by_min=[0.0] * 15 + [16.0] * 15,
                current_by_min=[0.0] * 30,
                user_id="u_bad",
                sid=f"bad_{i}",
            )
        )
        sessions.append(
            _trace_session(
                pilot_by_min=[0.0] * 15 + [16.0] * 15,
                current_by_min=[0.0] * 15 + [15.0] * 15,
                user_id="u_good",
                sid=f"good_{i}",
            )
        )
    out = evaluate_t3({"caltech": sessions})
    assert out["pooled"]["n_events"] == 10
    assert out["pooled"]["n_failures"] == 5
    assert out["pooled"]["failure_rate"] == pytest.approx(0.5)
    assert out["persistence_h3"]["tarone"]["n_users"] == 2
    assert out["persistence_h3"]["tarone"]["h3_supported"] is True
    assert out["persistence_h3"]["beta_binomial_h3_users"]["intra_class_correlation"] > 0.5
