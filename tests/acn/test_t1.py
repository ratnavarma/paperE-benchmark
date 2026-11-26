"""Tests for papere.acn.t1: regime indicator and T1 aggregation/bootstrap."""
from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from papere.acn.load import clean_sessions
from papere.acn.t1 import evaluate_t1, in_uncorrectable_regime

LA = ZoneInfo("America/Los_Angeles")


def _rfc2822_utc(dt_local: datetime) -> str:
    return dt_local.astimezone(ZoneInfo("UTC")).strftime("%a, %d %b %Y %H:%M:%S GMT")


def _raw(conn_local: datetime, disc_local: datetime, kwh_del: float, kwh_req: float, sid: str) -> dict:
    return {
        "sessionID": sid,
        "userID": f"u_{sid}",
        "timezone": "America/Los_Angeles",
        "connectionTime": _rfc2822_utc(conn_local),
        "disconnectTime": _rfc2822_utc(disc_local),
        "kWhDelivered": kwh_del,
        "userInputs": [{"kWhRequested": kwh_req}],
        "pilotSignal": {"timestamps": [_rfc2822_utc(conn_local)], "pilot": [32.0]},
        "chargingCurrent": {"timestamps": [_rfc2822_utc(conn_local)], "current": [16.0]},
    }


def test_regime_indicator_exact_boundaries():
    # w < delta + 15 min
    assert in_uncorrectable_regime(29.9, 15) is True
    assert in_uncorrectable_regime(30.0, 15) is False
    assert in_uncorrectable_regime(44.9, 30) is True
    assert in_uncorrectable_regime(45.0, 30) is False
    assert in_uncorrectable_regime(74.9, 60) is True
    assert in_uncorrectable_regime(75.0, 60) is False


def test_t1_on_handmade_site_days():
    # Build two eligible weekday site-days (Monday & Tuesday) at site "caltech"
    # At e = 17:00, each day has 4 population sessions (plus 6 morning filler sessions -> 10/day):
    # - sA: conn 16:00, disc 17:20 (w = 20 min < 30, 45, 75), delivered=4 (half by 17:00 -> 2.0),
    #       actually linear constant current: 60/(80)*4 = 3.0 delivered by 17:00, req=7.0 -> rem=4.0 kWh
    # - sB: conn 16:00, disc 17:40 (w = 40 min -> in regime for d=30,60; NOT d=15),
    #       del=5.0, frac at 17:00 = 60/100 = 0.6 -> del_at_e=3.0, req=5.0 -> rem=2.0 kWh
    # - sC: conn 16:00, disc 18:30 (w = 90 min -> never in regime),
    #       del=3.0, frac=60/150=0.4 -> del_at_e=1.2, req=5.2 -> rem=4.0 kWh
    # - sD: conn 16:00, disc 17:10, del=2.0, frac=60/70 -> rem < 0.25 (excluded from pop!)
    raws = []
    for day_idx, day_num in enumerate((4, 5)):  # Mon Nov 4, Tue Nov 5 2019
        base = datetime(2019, 11, day_num, 16, 0, tzinfo=LA)
        e = datetime(2019, 11, day_num, 17, 0, tzinfo=LA)
        # 6 morning filler sessions disconnected before 17:00
        for j in range(6):
            m0 = datetime(2019, 11, day_num, 9, 0, tzinfo=LA)
            raws.append(_raw(m0, m0 + timedelta(hours=2), 5.0, 5.0, f"fill_{day_idx}_{j}"))
        # 3 population sessions + 1 below 0.25 kWh remaining
        raws.append(_raw(base, e + timedelta(minutes=20), 4.0, 7.0, f"A_{day_idx}"))  # rem = 4.0
        raws.append(_raw(base, e + timedelta(minutes=40), 5.0, 5.0, f"B_{day_idx}"))  # rem = 2.0
        raws.append(_raw(base, e + timedelta(minutes=90), 3.0, 5.2, f"C_{day_idx}"))  # rem = 4.0
        raws.append(_raw(base, e + timedelta(minutes=10), 2.0, 1.8, f"D_{day_idx}"))  # rem ~ 0.086 < 0.25

    sessions, _ = clean_sessions(raws, site="caltech")
    res = evaluate_t1({"caltech": sessions}, event_hours=(17,), deltas_min=(15, 30, 60), n_boot=500)

    assert res["meta"]["pooled_site_day_count"] == 2
    p17 = res["pooled"]["17:00"]
    # Population = 3 sessions/day * 2 days = 6; total remaining = (4 + 2 + 4)*2 = 20 kWh
    # delta=15 (w < 30): only A -> share = 1/3, energy_at_risk = 4/10 = 0.4
    assert p17["15"]["n_pop_sessions"] == 6
    assert p17["15"]["n_regime_sessions"] == 2
    assert p17["15"]["share"] == pytest.approx(1.0 / 3.0)
    assert p17["15"]["energy_at_risk"] == pytest.approx(0.4)
    # delta=30 (w < 45): A and B -> share = 2/3, energy_at_risk = (4 + 2)/10 = 0.6
    assert p17["30"]["share"] == pytest.approx(2.0 / 3.0)
    assert p17["30"]["energy_at_risk"] == pytest.approx(0.6)
    # delta=60 (w < 75): A and B -> share = 2/3, energy_at_risk = 0.6
    assert p17["60"]["share"] == pytest.approx(2.0 / 3.0)
    assert p17["60"]["energy_at_risk"] == pytest.approx(0.6)
    # Identical days -> zero bootstrap width
    assert p17["30"]["share_ci"] == pytest.approx([2.0 / 3.0, 2.0 / 3.0])
