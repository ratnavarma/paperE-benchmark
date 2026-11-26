"""Tests for papere.acn.load: cleaning rules, resampling, delivered energy, site-days."""
from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import numpy as np
import pytest

from papere.acn.load import (
    CleaningReport,
    clean_session,
    clean_sessions,
    eligible_site_days,
    extract_need,
    parse_timestamp,
    resample_locf,
    sessions_connected_at,
)

LA = ZoneInfo("America/Los_Angeles")


def _rfc2822_utc(dt_local: datetime) -> str:
    dt_utc = dt_local.astimezone(ZoneInfo("UTC"))
    return dt_utc.strftime("%a, %d %b %Y %H:%M:%S GMT")


def make_raw_session(
    *,
    conn_local: datetime,
    duration_min: float = 120.0,
    kwh_delivered: float = 10.0,
    pilot_pts: list[tuple[float, float]] | None = None,
    current_pts: list[tuple[float, float]] | None = None,
    user_inputs: list[dict] | None = None,
    user_id: str | None = "u1",
    session_id: str = "s1",
    tz: str = "America/Los_Angeles",
) -> dict:
    disc_local = conn_local + timedelta(minutes=duration_min)
    if pilot_pts is None:
        pilot_pts = [(0.0, 32.0)]
    if current_pts is None:
        current_pts = [(0.0, 20.0)]
    return {
        "sessionID": session_id,
        "userID": user_id,
        "timezone": tz,
        "connectionTime": _rfc2822_utc(conn_local),
        "disconnectTime": _rfc2822_utc(disc_local),
        "kWhDelivered": kwh_delivered,
        "userInputs": user_inputs,
        "pilotSignal": {
            "timestamps": [_rfc2822_utc(conn_local + timedelta(minutes=m)) for m, _ in pilot_pts],
            "pilot": [v for _, v in pilot_pts],
        },
        "chargingCurrent": {
            "timestamps": [_rfc2822_utc(conn_local + timedelta(minutes=m)) for m, _ in current_pts],
            "current": [v for _, v in current_pts],
        },
    }


def test_cleaning_rules_in_protocol_order():
    base = datetime(2019, 11, 4, 10, 0, tzinfo=LA)  # Monday
    # 1. disconnect <= connection (also violates kwh < 0.1 and missing series -> counted under rule 1)
    bad1 = make_raw_session(conn_local=base, duration_min=0.0, kwh_delivered=0.01)
    bad1["pilotSignal"] = None
    # 2. duration > 24 h (also violates kwh < 0.1 -> counted under rule 2)
    bad2 = make_raw_session(conn_local=base, duration_min=24 * 60 + 1, kwh_delivered=0.01)
    # 3. kWh delivered < 0.1 (also missing series -> counted under rule 3)
    bad3 = make_raw_session(conn_local=base, duration_min=60.0, kwh_delivered=0.09)
    bad3["chargingCurrent"] = None
    # 4. missing pilot or current series
    bad4 = make_raw_session(conn_local=base, duration_min=60.0, kwh_delivered=5.0)
    bad4["pilotSignal"] = {"timestamps": [], "pilot": []}
    bad5 = make_raw_session(conn_local=base, duration_min=60.0, kwh_delivered=5.0)
    bad5["chargingCurrent"] = None
    # 5. valid session at exact boundaries (24h and 0.1 kWh)
    good = make_raw_session(conn_local=base, duration_min=24 * 60, kwh_delivered=0.1)

    kept, rep = clean_sessions([bad1, bad2, bad3, bad4, bad5, good], site="caltech")
    assert rep.raw_count == 6
    assert rep.dropped_disconnect_le_connection == 1
    assert rep.dropped_duration_gt_24h == 1
    assert rep.dropped_kwh_lt_0_1 == 1
    assert rep.dropped_missing_series == 2
    assert rep.kept_count == 1
    assert len(kept) == 1


def test_need_and_need_source():
    raw_req = {
        "userInputs": [
            {"kWhRequested": 5.0},
            {"kWhRequested": None},
            {"kWhRequested": 12.5},
        ]
    }
    assert extract_need(raw_req, 8.0) == (12.5, "requested")
    assert extract_need({"userInputs": None}, 8.0) == (8.0, "delivered")
    assert extract_need({"userInputs": [{"kWhRequested": None}]}, 8.0) == (8.0, "delivered")


def test_resample_locf_and_delivered_energy_by_time():
    # Raw samples at t = 10, 100, 220; grid at 0, 60, 120, 180, 240
    raw_ts = np.array([10.0, 100.0, 220.0])
    raw_vals = np.array([8.0, 16.0, 0.0])
    grid = np.array([0.0, 60.0, 120.0, 180.0, 240.0])
    out = resample_locf(raw_ts, raw_vals, grid)
    assert np.isnan(out[0])
    assert np.allclose(out[1:], [8.0, 16.0, 16.0, 0.0])

    # Hand-made 60-minute session: 20 A for first 30 min, 10 A for next 30 min -> ratio 2:1
    # Total kWhDelivered = 9.0 -> 6.0 kWh in first 30 min, 3.0 kWh in second 30 min.
    base = datetime(2019, 11, 4, 16, 0, tzinfo=LA)
    raw = make_raw_session(
        conn_local=base,
        duration_min=60.0,
        kwh_delivered=9.0,
        current_pts=[(0.0, 20.0), (30.0, 10.0)],
        user_inputs=[{"kWhRequested": 15.0}],
    )
    sess = clean_session(raw, site="caltech", report=CleaningReport("caltech"))
    assert sess is not None
    assert sess.grid_ts.size == 60
    assert sess.need_kwh == 15.0 and sess.need_source == "requested"

    t0 = sess.connection_ts
    assert sess.delivered_energy_at(t0) == pytest.approx(0.0)
    assert sess.delivered_energy_at(t0 + 15 * 60) == pytest.approx(3.0)
    assert sess.delivered_energy_at(t0 + 30 * 60) == pytest.approx(6.0)
    assert sess.delivered_energy_at(t0 + 45 * 60) == pytest.approx(7.5)
    assert sess.delivered_energy_at(t0 + 60 * 60) == pytest.approx(9.0)
    assert sess.remaining_need_at(t0 + 30 * 60) == pytest.approx(9.0)


def test_site_day_eligibility_weekdays_and_min_sessions():
    mon = datetime(2019, 11, 4, 10, 0, tzinfo=LA)  # Monday
    tue = datetime(2019, 11, 5, 10, 0, tzinfo=LA)  # Tuesday
    sat = datetime(2019, 11, 9, 10, 0, tzinfo=LA)  # Saturday

    raws = (
        [make_raw_session(conn_local=mon, session_id=f"m{i}") for i in range(10)]
        + [make_raw_session(conn_local=tue, session_id=f"t{i}") for i in range(9)]
        + [make_raw_session(conn_local=sat, session_id=f"s{i}") for i in range(15)]
    )
    sess, _ = clean_sessions(raws, site="jpl")
    days = eligible_site_days(sess)
    assert len(days) == 1
    assert days[0].local_date == mon.date()
    assert days[0].n_cleaned_sessions == 10
    assert len(sessions_connected_at(sess, days[0].event_timestamp(11, 0))) == 10


def test_parse_timestamp_fast_and_fallback():
    s = "Fri, 01 Nov 2019 14:13:26 GMT"
    ts = parse_timestamp(s)
    assert ts == datetime(2019, 11, 1, 14, 13, 26, tzinfo=ZoneInfo("UTC")).timestamp()
    assert parse_timestamp("2019-11-01T14:13:26Z") == ts
