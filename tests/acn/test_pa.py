"""Tests for papere.acn.pa: window, timezones/DST, cleaning, duplicates, T1/T2, and <20 gate."""
from __future__ import annotations

import csv
from datetime import date, datetime, timedelta
import importlib.util
import json
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pytest

from papere.acn.instances import T2_P_UNITS, build_acn_instance, build_t2_site_days
from papere.acn.pa import (
    PA_DEFAULT_SEEDS,
    PA_MIN_T2_SITE_DAYS,
    PA_T1_BOOT_SEED,
    PA_T2_BOOT_SEED,
    PA_TIMEZONE,
    clean_pa_rows,
    load_pa_sites,
    parse_pa_start_end,
    parse_pa_timestamp,
    summarize_pa_cleaning,
)
from papere.acn.run_t2 import resolve_t2_cells, run_t2
from papere.acn.t1 import evaluate_t1
from papere.instance import Cell

LA = ZoneInfo(PA_TIMEZONE)
UTC = ZoneInfo("UTC")


def _pa_row(
    *,
    station: str = "PALO ALTO CA / HAMILTON #1",
    mac: str = "000D:6F00:015A:9D76",
    org: str = "City of Palo Alto",
    start_date: str = "11/4/2019 16:00",
    start_tz: str = "PST",
    end_date: str = "11/4/2019 18:00",
    end_tz: str = "PST",
    energy_kwh: str = "10.0",
    port_type: str = "Level 2",
    port_number: str = "1",
    address: str = "250 Hamilton Ave",
    event_id: str = "1001",
    user_id: str = "5001",
) -> dict[str, str]:
    return {
        "Station Name": station,
        "MAC Address": mac,
        "Org Name": org,
        "Start Date": start_date,
        "Start Time Zone": start_tz,
        "End Date": end_date,
        "End Time Zone": end_tz,
        "Transaction Date (Pacific Time)": end_date,
        "Total Duration (hh:mm:ss)": "2:00:00",
        "Charging Time (hh:mm:ss)": "2:00:00",
        "Energy (kWh)": energy_kwh,
        "Port Type": port_type,
        "Port Number": port_number,
        "Address 1": address,
        "Plug In Event Id": event_id,
        "User ID": user_id,
    }


def test_pa_timestamps_timezones_dst_and_window_boundaries():
    # 1. Explicit PDT -> PST across DST fall-back (2019-11-02 22:22 PDT -> 2019-11-03 10:58 PST)
    #    22:22 PDT = 2019-11-03 05:22 UTC; 10:58 PST = 2019-11-03 18:58 UTC -> 13h 36m
    r_dst = _pa_row(
        event_id="dst",
        start_date="11/2/2019 22:22",
        start_tz="PDT",
        end_date="11/3/2019 10:58",
        end_tz="PST",
        energy_kwh="27.2",
    )
    # 2. Missing timezone tags -> treated as local wall time in America/Los_Angeles (with fold=1 retry)
    #    2019-11-03 01:40 PDT (08:40 UTC) -> 2019-11-03 01:20 PST (09:20 UTC) = 40 min
    r_local_fallback = _pa_row(
        event_id="fallback",
        start_date="11/3/2019 1:40",
        start_tz="",
        end_date="11/3/2019 1:20",
        end_tz="",
        energy_kwh="4.0",
    )
    # 3. UTC tag landing on 2020-02-29 23:30 PST (inside window!)
    r_utc_in = _pa_row(
        event_id="utc_in",
        start_date="3/1/2020 7:30",
        start_tz="UTC",
        end_date="3/1/2020 9:30",
        end_tz="UTC",
        energy_kwh="6.0",
    )
    # 4. UTC tag landing on 2019-10-31 17:30 PDT (outside window -> dropped)
    r_utc_out = _pa_row(
        event_id="utc_out",
        start_date="11/1/2019 0:30",
        start_tz="UTC",
        end_date="11/1/2019 2:30",
        end_tz="UTC",
        energy_kwh="6.0",
    )
    # 5. Outside window: before 2019-11-01 and after 2020-02-29
    r_before = _pa_row(
        event_id="before",
        start_date="10/31/2019 23:59",
        start_tz="PDT",
        end_date="11/1/2019 1:00",
        end_tz="PDT",
    )
    r_after = _pa_row(
        event_id="after",
        start_date="3/1/2020 0:00",
        start_tz="PST",
        end_date="3/1/2020 2:00",
        end_tz="PST",
    )

    by_site, reports = clean_pa_rows(
        [r_dst, r_local_fallback, r_utc_in, r_utc_out, r_before, r_after]
    )
    rep = reports["250 Hamilton Ave"]
    assert rep.raw_count == 6
    assert rep.dropped_outside_window == 3
    assert rep.in_window_count == 3
    assert rep.kept_count == 3

    by_id = {s.session_id.split(":")[-1]: s for s in by_site["250 Hamilton Ave"]}
    s_dst = by_id["dst"]
    assert s_dst.local_date == date(2019, 11, 2)
    assert s_dst.duration_s == pytest.approx((13 * 60 + 36) * 60.0)
    assert s_dst.connection_ts == datetime(2019, 11, 3, 5, 22, tzinfo=UTC).timestamp()
    assert s_dst.disconnect_ts == datetime(2019, 11, 3, 18, 58, tzinfo=UTC).timestamp()

    s_fb = by_id["fallback"]
    assert s_fb.local_date == date(2019, 11, 3)
    assert s_fb.duration_s == pytest.approx(40.0 * 60.0)

    s_utc = by_id["utc_in"]
    assert s_utc.local_date == date(2020, 2, 29)
    assert s_utc.duration_s == pytest.approx(2.0 * 3600.0)

    assert parse_pa_timestamp("11/4/2019 17:00", "PST") == datetime(
        2019, 11, 5, 1, 0, tzinfo=UTC
    ).timestamp()
    assert parse_pa_start_end("11/4/2019 17:00", "PST", "", "PST")[1] is None


def test_pa_cleaning_rules_all_field_dedup_and_site_grouping():
    rows = [
        # 1. Missing start -> dropped_missing_or_invalid_start
        _pa_row(event_id="1", start_date=""),
        # 2. Outside window (at a different historical address) -> dropped_outside_window
        _pa_row(
            event_id="2",
            address="Old Historical St",
            start_date="7/29/2011 20:17",
            start_tz="PDT",
            end_date="7/29/2011 23:20",
            end_tz="PDT",
        ),
        # 3. Missing / unparseable end -> dropped_missing_or_invalid_end
        _pa_row(event_id="3", end_date="42845.81041"),
        # 4. Missing energy -> dropped_missing_or_invalid_energy
        _pa_row(event_id="4", energy_kwh=""),
        # 5. Missing address -> dropped_missing_site
        _pa_row(event_id="5", address=""),
        # 6. end <= start -> dropped_end_le_start
        _pa_row(event_id="6", start_date="11/4/2019 18:00", end_date="11/4/2019 18:00"),
        _pa_row(event_id="7", start_date="11/4/2019 19:00", end_date="11/4/2019 18:00"),
        # 7. duration > 24 h -> dropped_duration_gt_24h
        _pa_row(
            event_id="8",
            start_date="11/4/2019 10:00",
            end_date="11/5/2019 10:01",
            energy_kwh="12.0",
        ),
        # 8. energy < 0.1 -> dropped_kwh_lt_0_1
        _pa_row(event_id="9", energy_kwh="0.09"),
        # 9. Valid boundary (24 h, 0.1 kWh) -> kept
        _pa_row(
            event_id="10",
            station="PALO ALTO CA / HAMILTON #1",
            start_date="11/4/2019 10:00",
            end_date="11/5/2019 10:00",
            energy_kwh="0.1",
        ),
        # 10. Exact duplicate of row 9 (all fields equal) -> dropped_exact_duplicate
        _pa_row(
            event_id="10",
            station="PALO ALTO CA / HAMILTON #1",
            start_date="11/4/2019 10:00",
            end_date="11/5/2019 10:00",
            energy_kwh="0.1",
        ),
        # 11. Different Station Name at SAME Address 1 -> NOT a duplicate, grouped into same site!
        _pa_row(
            event_id="10",
            station="PALO ALTO CA / HAMILTON #2",
            start_date="11/4/2019 10:00",
            end_date="11/5/2019 10:00",
            energy_kwh="0.1",
        ),
    ]

    by_site, reports = clean_pa_rows(rows)
    # Historical out-of-window site and blank site do not appear in active sessions_by_site
    assert list(by_site.keys()) == ["250 Hamilton Ave"]
    assert len(by_site["250 Hamilton Ave"]) == 2

    pooled = summarize_pa_cleaning(reports)
    assert pooled.raw_count == 12
    assert pooled.dropped_missing_or_invalid_start == 1
    assert pooled.dropped_outside_window == 1
    assert pooled.in_window_count == 10
    assert pooled.dropped_missing_or_invalid_end == 1
    assert pooled.dropped_missing_or_invalid_energy == 1
    assert pooled.dropped_missing_start_end_or_energy == 3
    assert pooled.dropped_missing_site == 1
    assert pooled.dropped_end_le_start == 2
    assert pooled.dropped_duration_gt_24h == 1
    assert pooled.dropped_kwh_lt_0_1 == 1
    assert pooled.dropped_exact_duplicate == 1
    assert pooled.kept_count == 2
    # Accounting identity: raw_count == all drops + kept
    total_dropped = (
        pooled.dropped_missing_or_invalid_start
        + pooled.dropped_outside_window
        + pooled.dropped_missing_or_invalid_end
        + pooled.dropped_missing_or_invalid_energy
        + pooled.dropped_missing_site
        + pooled.dropped_end_le_start
        + pooled.dropped_duration_gt_24h
        + pooled.dropped_kwh_lt_0_1
        + pooled.dropped_exact_duplicate
    )
    assert pooled.raw_count == total_dropped + pooled.kept_count


def test_pa_linear_delivered_energy_and_session_fields():
    row = _pa_row(
        event_id="lin",
        start_date="11/4/2019 15:00",
        start_tz="PST",
        end_date="11/4/2019 19:00",
        end_tz="PST",
        energy_kwh="16.0",
        user_id="98765",
    )
    by_site, _ = clean_pa_rows([row])
    s = by_site["250 Hamilton Ave"][0]
    assert s.site == "250 Hamilton Ave"
    assert s.timezone == PA_TIMEZONE
    assert s.user_id == "98765"
    assert s.kwh_delivered == pytest.approx(16.0)
    assert s.need_kwh == pytest.approx(16.0)
    assert s.need_source == "delivered"
    assert s.pilot_1m.size == 0
    assert s.current_1m.size == 0

    t0 = s.connection_ts
    assert s.delivered_energy_at(t0) == pytest.approx(0.0)
    assert s.delivered_energy_at(t0 + 3600.0) == pytest.approx(4.0)
    assert s.delivered_energy_at(t0 + 2 * 3600.0) == pytest.approx(8.0)
    assert s.remaining_need_at(t0 + 2 * 3600.0) == pytest.approx(8.0)
    assert s.delivered_energy_at(t0 + 4 * 3600.0) == pytest.approx(16.0)


def _make_synthetic_pa_rows(n_weekdays: int = 2, address: str = "250 Hamilton Ave") -> list[dict[str, str]]:
    """Build ``n_weekdays`` eligible T1 & T2 weekday site-days starting Mon 2019-11-04."""
    rows: list[dict[str, str]] = []
    ev_id = 1
    d = date(2019, 11, 4)  # Monday (PST)
    made = 0
    while made < n_weekdays:
        if d.weekday() < 5:
            d_str = f"{d.month}/{d.day}/{d.year}"
            # 5 morning filler sessions so total cleaned >= 10
            for j in range(5):
                rows.append(
                    _pa_row(
                        station=f"PALO ALTO CA / TEST #{j + 1}",
                        start_date=f"{d_str} 9:00",
                        start_tz="PST",
                        end_date=f"{d_str} 11:00",
                        end_tz="PST",
                        energy_kwh="6.0",
                        address=address,
                        event_id=str(ev_id),
                    )
                )
                ev_id += 1
            # 6 evening sessions connected at 17:00 (all d_i >= 1 -> T2 eligible, N=6 >= 5)
            evening_specs = [
                ("17:20", "8.0"),   # rem = 2.0 kWh; w = 20, d = 1
                ("17:40", "10.0"),  # rem = 4.0 kWh; w = 40, d = 2
                ("18:00", "8.0"),   # rem = 4.0 kWh; w = 60, d = 4
                ("18:30", "10.0"),  # rem = 6.0 kWh; w = 90, d = 6
                ("19:00", "12.0"),  # rem = 8.0 kWh; w = 120, d = 8
                ("19:30", "14.0"),  # rem = 10.0 kWh; w = 150, d = 10
            ]
            for j, (end_t, kwh_s) in enumerate(evening_specs):
                rows.append(
                    _pa_row(
                        station=f"PALO ALTO CA / EV #{j + 1}",
                        start_date=f"{d_str} 16:00",
                        start_tz="PST",
                        end_date=f"{d_str} {end_t}",
                        end_tz="PST",
                        energy_kwh=kwh_s,
                        address=address,
                        event_id=str(ev_id),
                    )
                )
                ev_id += 1
            # 1 short session ending at 17:10 (in T1 pop, dropped from T2 because d_i == 0)
            rows.append(
                _pa_row(
                    station="PALO ALTO CA / SHORT #1",
                    start_date=f"{d_str} 16:00",
                    start_tz="PST",
                    end_date=f"{d_str} 17:10",
                    end_tz="PST",
                    energy_kwh="7.0",
                    address=address,
                    event_id=str(ev_id),
                )
            )
            ev_id += 1
            made += 1
        d += timedelta(days=1)
    return rows


def test_t1_and_t2_accept_pa_records(tmp_path: Path):
    rows = _make_synthetic_pa_rows(n_weekdays=2)
    by_site, _ = clean_pa_rows(rows)

    t1 = evaluate_t1(
        by_site,
        event_hours=(17,),
        deltas_min=(15, 30, 60),
        n_boot=200,
        boot_seed=PA_T1_BOOT_SEED,
    )
    assert t1["meta"]["pooled_site_day_count"] == 2
    assert t1["meta"]["boot_seed"] == PA_T1_BOOT_SEED
    p17 = t1["pooled"]["17:00"]
    assert p17["15"]["n_pop_sessions"] == 14
    assert p17["15"]["share"] == pytest.approx(2.0 / 7.0)
    assert p17["30"]["share"] == pytest.approx(3.0 / 7.0)
    assert p17["60"]["share"] == pytest.approx(4.0 / 7.0)

    sds = build_t2_site_days(by_site)
    assert len(sds) == 2
    sd = sds[0]
    assert sd.N == 6
    assert np.all(sd.P == T2_P_UNITS)
    assert np.all(sd.a == 0)
    assert sorted(sd.d.tolist()) == [1, 2, 4, 6, 8, 10]
    assert sorted(sd.E.tolist()) == [8, 16, 16, 24, 32, 40]

    cell = Cell(family="F0R", M=3, delta_A=2, delta_b=0, rho=0.95, r=0.3)
    inst = build_acn_instance(60000, cell, sd)
    assert inst.N == 6
    assert inst.H == 24

    rows_path = tmp_path / "t2_rows.jsonl"
    manifest = run_t2(
        sds,
        [60000],
        rows_path,
        cells=resolve_t2_cells(["F0R_M3_dA2_db0_rho0.95_r0.3"]),
        workers=1,
    )
    assert manifest["status"] == "complete"
    assert manifest["rows_written"] == 4


def _load_acn_all_module():
    script_path = Path(__file__).resolve().parents[2] / "scripts" / "acn_all.py"
    spec = importlib.util.spec_from_file_location("acn_all_script_pa", script_path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    fieldnames = list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)


def test_acn_all_cli_dataset_pa_gate_and_run(tmp_path: Path):
    mod = _load_acn_all_module()

    # Default seeds for --dataset pa match amendment 4 (without running them)
    parsed_pa = mod._parse_args(["--dataset", "pa", "--run-name", "check_pa_defaults"])
    assert parsed_pa.seeds == PA_DEFAULT_SEEDS
    assert PA_DEFAULT_SEEDS == "730000-730199"
    assert PA_T1_BOOT_SEED == 730_500
    assert PA_T2_BOOT_SEED == 731_000
    assert PA_MIN_T2_SITE_DAYS == 20

    # Case A: 19 eligible T2 site-days (< 20 gate) -> T1 runs, T2 skipped, counts written to summary.json
    csv_19 = tmp_path / "pa_19.csv"
    _write_csv(csv_19, _make_synthetic_pa_rows(n_weekdays=19))
    out_root = tmp_path / "out"
    rc = mod.main(
        [
            "--dataset",
            "pa",
            "--pa-csv",
            str(csv_19),
            "--out-root",
            str(out_root),
            "--run-name",
            "pa_19_gate",
            "--seeds",
            "60000-60001",
            "--cells",
            "F0R_M3_dA2_db0_rho0.95_r0.3",
            "--n-boot-t1",
            "50",
            "--smoke-quiet",
        ]
    )
    assert rc == 0
    dir_19 = out_root / "pa_19_gate"
    assert (dir_19 / "cleaning.json").exists()
    assert (dir_19 / "t1.json").exists()
    assert (dir_19 / "summary.json").exists()
    assert not (dir_19 / "t2_rows.jsonl").exists()
    assert not (dir_19 / "t2_manifest.json").exists()
    assert not (dir_19 / "t2_analysis.json").exists()
    assert not (dir_19 / "t3.json").exists()

    s19 = json.loads((dir_19 / "summary.json").read_text())
    assert s19["dataset"] == "pa"
    assert s19["status"] == "t2_not_runnable"
    assert s19["t2_runnable"] is False
    assert s19["min_t2_site_days"] == 20
    assert s19["n_t2_site_days_total"] == 19
    assert s19["n_t2_site_days"] == 0
    assert s19["t2_eligible_site_days_per_site"] == {"250 Hamilton Ave": 19}
    assert s19["t2_rows_written"] == 0
    assert s19["amendment_4_sha256"] is not None

    # Case B: 20 eligible T2 site-days (meets gate) -> T1 + T2 run with amendment 4 boot seeds
    csv_20 = tmp_path / "pa_20.csv"
    _write_csv(csv_20, _make_synthetic_pa_rows(n_weekdays=20))
    loaded, _ = load_pa_sites(csv_20)
    assert len(loaded["250 Hamilton Ave"]) == 20 * 12

    rc = mod.main(
        [
            "--dataset",
            "pa",
            "--pa-csv",
            str(csv_20),
            "--out-root",
            str(out_root),
            "--run-name",
            "pa_20_ok",
            "--seeds",
            "60000-60001",
            "--cells",
            "F0R_M3_dA2_db0_rho0.95_r0.3",
            "--max-site-days",
            "5",
            "--n-boot-t1",
            "50",
            "--n-boot-t2",
            "50",
            "--smoke-quiet",
        ]
    )
    assert rc == 0
    dir_20 = out_root / "pa_20_ok"
    assert (dir_20 / "cleaning.json").exists()
    assert (dir_20 / "t1.json").exists()
    assert (dir_20 / "t2_rows.jsonl").exists()
    assert (dir_20 / "t2_manifest.json").exists()
    assert (dir_20 / "t2_analysis.json").exists()
    assert (dir_20 / "summary.json").exists()
    assert not (dir_20 / "t3.json").exists()
    assert not (dir_20 / "t2_emp_rows.jsonl").exists()
    assert not (dir_20 / "real_limit_rows.jsonl").exists()

    t1 = json.loads((dir_20 / "t1.json").read_text())
    assert t1["meta"]["boot_seed"] == PA_T1_BOOT_SEED
    assert t1["meta"]["pooled_site_day_count"] == 5  # capped by --max-site-days 5
    analysis = json.loads((dir_20 / "t2_analysis.json").read_text())
    assert set(analysis.keys()) == {"t2"}
    assert analysis["t2"]["meta"]["boot_seed"] == PA_T2_BOOT_SEED
    s20 = json.loads((dir_20 / "summary.json").read_text())
    assert s20["status"] == "complete"
    assert s20["t2_runnable"] is True
    assert s20["n_t2_site_days_total"] == 20
    assert s20["n_t2_site_days"] == 5
    assert s20["eligible_site_days_per_site"] == {"250 Hamilton Ave": 20}
    assert s20["t2_eligible_site_days_per_site"] == {"250 Hamilton Ave": 20}
    assert s20["t2_rows_written"] == 8
