"""Tests for papere.acn.pk: timestamps (DST & midnight), AC filter, duplicates, T1/T2 integration."""
from __future__ import annotations

import csv
from datetime import date, datetime
import importlib.util
import json
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pytest

from papere.acn.instances import T2_P_UNITS, build_acn_instance, build_t2_site_days
from papere.acn.pk import (
    PK_AC_MODELS,
    PK_DEFAULT_SEEDS,
    PK_T1_BOOT_SEED,
    PK_T2_BOOT_SEED,
    PK_TIMEZONE,
    PK_WINDOW_END,
    PK_WINDOW_START,
    clean_pk_rows,
    load_pk_sites,
    parse_pk_local_timestamp,
    parse_pk_start_end,
    repair_pk_date,
    summarize_pk_cleaning,
)
from papere.acn.run_t2 import resolve_t2_cells, run_t2
from papere.acn.t1 import evaluate_t1
from papere.instance import Cell

LONDON = ZoneInfo(PK_TIMEZONE)
UTC = ZoneInfo("UTC")


def _pk_row(
    *,
    row_id: str = "1",
    cp_id: str = "50839",
    connector: str = "1",
    start_date: str = "2019-06-10T00:00:00",
    start_time: str = "16:00",
    end_date: str = "2019-06-10T00:00:00",
    end_time: str = "18:00",
    total_kwh: str = "10.0",
    site: str = "Mill Street, Perth",
    model: str = "APT 22kW Raption",
) -> dict[str, str]:
    return {
        "_id": row_id,
        "CP ID": cp_id,
        "Connector": connector,
        "Start Date": start_date,
        "Start Time": start_time,
        "End Date": end_date,
        "End Time": end_time,
        "Total kWh": total_kwh,
        "Site": site,
        "Model": model,
    }


def test_timestamps_across_midnight_and_dst_changes():
    # 1. Normal overnight session across midnight in BST (2019-06-10 22:30 -> 2019-06-11 01:30 = 3 h)
    r_mid = _pk_row(
        row_id="mid",
        start_date="2019-06-10T00:00:00",
        start_time="22:30",
        end_date="2019-06-11T00:00:00",
        end_time="01:30",
        total_kwh="12.0",
    )
    # 2. Fall-back DST change (2018-10-28 02:00 BST -> 01:00 GMT):
    #    2018-10-27 22:00 BST (21:00 UTC) -> 2018-10-28 08:00 GMT (08:00 UTC) = 11 hours
    r_fall = _pk_row(
        row_id="fall",
        start_date="2018-10-27T00:00:00",
        start_time="22:00",
        end_date="2018-10-28T00:00:00",
        end_time="08:00",
        total_kwh="22.0",
    )
    # 3. Spring-forward DST change (2019-03-31 01:00 GMT -> 02:00 BST):
    #    2019-03-30 22:00 GMT (22:00 UTC) -> 2019-03-31 08:00 BST (07:00 UTC) = 9 hours
    r_spring = _pk_row(
        row_id="spring",
        start_date="2019-03-30T00:00:00",
        start_time="22:00",
        end_date="2019-03-31T00:00:00",
        end_time="08:00",
        total_kwh="18.0",
    )
    # 4. Session spanning the repeated fall-back hour (01:40 BST -> 01:20 GMT = 40 min)
    r_ambig = _pk_row(
        row_id="ambig",
        start_date="2018-10-28T00:00:00",
        start_time="01:40",
        end_date="2018-10-28T00:00:00",
        end_time="01:20",
        total_kwh="4.0",
    )

    by_site, reports = clean_pk_rows([r_mid, r_fall, r_spring, r_ambig])
    sess_by_id = {s.session_id: s for s in by_site["Mill Street, Perth"]}
    assert reports["Mill Street, Perth"].kept_count == 4

    s_mid = sess_by_id["mid"]
    assert s_mid.local_date == date(2019, 6, 10)
    assert s_mid.duration_s == pytest.approx(3.0 * 3600.0)
    assert s_mid.connection_ts == datetime(2019, 6, 10, 21, 30, tzinfo=UTC).timestamp()
    assert s_mid.disconnect_ts == datetime(2019, 6, 11, 0, 30, tzinfo=UTC).timestamp()

    s_fall = sess_by_id["fall"]
    assert s_fall.local_date == date(2018, 10, 27)
    assert s_fall.duration_s == pytest.approx(11.0 * 3600.0)
    # Linear delivered energy at 2018-10-28 00:00 UTC (3 h elapsed out of 11 h) -> 6.0 kWh
    t_check = datetime(2018, 10, 28, 0, 0, tzinfo=UTC).timestamp()
    assert s_fall.delivered_energy_at(t_check) == pytest.approx(22.0 * 3.0 / 11.0)

    s_spring = sess_by_id["spring"]
    assert s_spring.local_date == date(2019, 3, 30)
    assert s_spring.duration_s == pytest.approx(9.0 * 3600.0)

    s_ambig = sess_by_id["ambig"]
    assert s_ambig.duration_s == pytest.approx(40.0 * 60.0)
    assert parse_pk_local_timestamp("2019-06-10", "17:00") == datetime(
        2019, 6, 10, 16, 0, tzinfo=UTC
    ).timestamp()
    assert parse_pk_start_end("2019-06-10", "17:00", "", "") is None


def test_ac_model_filter_per_amendment_2():
    kept_models = sorted(PK_AC_MODELS)
    excluded_models = [
        "APT Triple Rapid Charger",
        "Siemens Triple Rapid Charger",
        "Siemens Semi-Rapid",
        "Unknown Rapid Charger",
    ]
    rows = []
    for i, m in enumerate(kept_models + excluded_models, start=1):
        rows.append(_pk_row(row_id=str(i), cp_id=str(50000 + i), model=m))

    by_site, reports = clean_pk_rows(rows)
    rep = reports["Mill Street, Perth"]
    assert rep.raw_count == len(kept_models) + len(excluded_models)
    assert rep.dropped_non_ac_model == len(excluded_models)
    assert rep.after_ac_filter == len(kept_models)
    assert rep.kept_count == len(kept_models)
    assert len(by_site["Mill Street, Perth"]) == len(kept_models)


def test_cleaning_rules_and_exact_duplicate_removal():
    rows = [
        # 1. Missing end timestamp -> dropped_missing_or_invalid_ts
        _pk_row(row_id="1", end_date="", end_time="", total_kwh=""),
        # 2. end <= start -> dropped_end_le_start
        _pk_row(row_id="2", start_time="18:00", end_time="18:00"),
        _pk_row(row_id="3", start_time="19:00", end_time="18:00"),
        # 3. duration > 24 h -> dropped_duration_gt_24h
        _pk_row(
            row_id="4",
            start_date="2019-06-10T00:00:00",
            start_time="10:00",
            end_date="2019-06-11T00:00:00",
            end_time="10:01",
        ),
        # 4. Total kWh < 0.1 -> dropped_kwh_lt_0_1
        _pk_row(row_id="5", total_kwh="0.09"),
        # 5. Valid boundary (exact 24 h, exact 0.1 kWh) -> kept
        _pk_row(
            row_id="6",
            cp_id="50100",
            start_date="2019-06-10T00:00:00",
            start_time="10:00",
            end_date="2019-06-11T00:00:00",
            end_time="10:00",
            total_kwh="0.1",
        ),
        # 6. Exact duplicate of row 6 (all 9 data fields identical, different _id) -> dropped
        _pk_row(
            row_id="7",
            cp_id="50100",
            start_date="2019-06-10T00:00:00",
            start_time="10:00",
            end_date="2019-06-11T00:00:00",
            end_time="10:00",
            total_kwh="0.1",
        ),
        # 7. Exact duplicate of row 6 (including same _id) -> dropped
        _pk_row(
            row_id="6",
            cp_id="50100",
            start_date="2019-06-10T00:00:00",
            start_time="10:00",
            end_date="2019-06-11T00:00:00",
            end_time="10:00",
            total_kwh="0.1",
        ),
        # 8. Differs only in Connector -> NOT a duplicate -> kept
        _pk_row(
            row_id="8",
            cp_id="50100",
            connector="2",
            start_date="2019-06-10T00:00:00",
            start_time="10:00",
            end_date="2019-06-11T00:00:00",
            end_time="10:00",
            total_kwh="0.1",
        ),
    ]

    by_site, reports = clean_pk_rows(rows)
    rep = reports["Mill Street, Perth"]
    assert rep.raw_count == 9
    assert rep.dropped_non_ac_model == 0
    assert rep.dropped_missing_or_invalid_ts == 1
    assert rep.dropped_end_le_start == 2
    assert rep.dropped_duration_gt_24h == 1
    assert rep.dropped_kwh_lt_0_1 == 1
    assert rep.dropped_exact_duplicate == 2
    assert rep.kept_count == 2
    assert len(by_site["Mill Street, Perth"]) == 2
    pooled = summarize_pk_cleaning(reports)
    assert pooled.kept_count == 2
    assert pooled.as_dict()["after_kwh_ge_0_1"] == 4


def test_need_linear_delivered_energy_and_no_series():
    row = _pk_row(
        row_id="lin1",
        start_date="2019-06-10T00:00:00",
        start_time="15:00",
        end_date="2019-06-10T00:00:00",
        end_time="19:00",
        total_kwh="16.0",
    )
    by_site, _ = clean_pk_rows([row])
    s = by_site["Mill Street, Perth"][0]

    assert s.site == "Mill Street, Perth"
    assert s.timezone == PK_TIMEZONE
    assert s.user_id is None
    assert s.kwh_delivered == pytest.approx(16.0)
    assert s.need_kwh == pytest.approx(16.0)
    assert s.need_source == "delivered"
    assert s.pilot_1m.size == 0
    assert s.current_1m.size == 0
    assert s.grid_ts.size == 0

    t0 = s.connection_ts
    assert s.delivered_energy_at(t0 - 60.0) == pytest.approx(0.0)
    assert s.delivered_energy_at(t0) == pytest.approx(0.0)
    assert s.delivered_energy_at(t0 + 3600.0) == pytest.approx(4.0)
    assert s.delivered_energy_at(t0 + 2 * 3600.0) == pytest.approx(8.0)
    assert s.delivered_energy_at(t0 + 3 * 3600.0) == pytest.approx(12.0)
    assert s.delivered_energy_at(t0 + 4 * 3600.0) == pytest.approx(16.0)
    assert s.delivered_energy_at(t0 + 5 * 3600.0) == pytest.approx(16.0)

    assert s.remaining_need_at(t0 + 2 * 3600.0) == pytest.approx(8.0)
    assert s.remaining_need_at(t0 + 3 * 3600.0) == pytest.approx(4.0)


def _make_synthetic_pk_rows() -> list[dict[str, str]]:
    """Build two eligible weekday site-days (Mon 2019-06-10, Tue 2019-06-11) at one site."""
    rows: list[dict[str, str]] = []
    rid = 1
    for day_str in ("2019-06-10T00:00:00", "2019-06-11T00:00:00"):
        # 5 morning filler sessions (09:00-11:00) so total cleaned >= 10
        for j in range(5):
            rows.append(
                _pk_row(
                    row_id=str(rid),
                    cp_id=f"5100{j}",
                    start_date=day_str,
                    start_time="09:00",
                    end_date=day_str,
                    end_time="11:00",
                    total_kwh="6.0",
                )
            )
            rid += 1
        # 6 evening sessions connected at 17:00, all starting at 16:00:
        # ends at 17:20 (d=1, w=20), 17:40 (d=2, w=40), 18:00 (d=4, w=60),
        #         18:30 (d=6, w=90), 19:00 (d=8, w=120), 19:30 (d=10, w=150)
        evening_specs = [
            ("17:20", "8.0"),   # 60/80 delivered -> rem = 2.0 kWh; w=20 (< 30, 45, 75), d=1
            ("17:40", "10.0"),  # 60/100 delivered -> rem = 4.0 kWh; w=40 (< 45, 75), d=2
            ("18:00", "8.0"),   # 60/120 delivered -> rem = 4.0 kWh; w=60 (< 75), d=4
            ("18:30", "10.0"),  # 60/150 delivered -> rem = 6.0 kWh; w=90 (not in regime), d=6
            ("19:00", "12.0"),  # 60/180 delivered -> rem = 8.0 kWh; w=120, d=8
            ("19:30", "14.0"),  # 60/210 delivered -> rem = 10.0 kWh; w=150, d=10
        ]
        for j, (end_t, kwh_s) in enumerate(evening_specs):
            rows.append(
                _pk_row(
                    row_id=str(rid),
                    cp_id=f"5200{j}",
                    start_date=day_str,
                    start_time="16:00",
                    end_date=day_str,
                    end_time=end_t,
                    total_kwh=kwh_s,
                )
            )
            rid += 1
        # 1 short session ending at 17:10 (w=10 -> in T1 regime, d=0 -> dropped from T2)
        rows.append(
            _pk_row(
                row_id=str(rid),
                cp_id="53000",
                start_date=day_str,
                start_time="16:00",
                end_date=day_str,
                end_time="17:10",
                total_kwh="7.0",  # 60/70 delivered -> rem = 1.0 kWh >= 0.25
            )
        )
        rid += 1
    return rows


def test_t1_and_instance_builder_accept_pk_records(tmp_path: Path):
    rows = _make_synthetic_pk_rows()
    by_site, _ = clean_pk_rows(rows)

    # T1 accepts PK sessions directly
    t1 = evaluate_t1(
        by_site,
        event_hours=(17,),
        deltas_min=(15, 30, 60),
        n_boot=200,
        boot_seed=PK_T1_BOOT_SEED,
    )
    assert t1["meta"]["pooled_site_day_count"] == 2
    assert t1["meta"]["boot_seed"] == PK_T1_BOOT_SEED
    p17 = t1["pooled"]["17:00"]
    # 7 pop sessions/day: w in {10, 20, 40, 60, 90, 120, 150}; rem = {1, 2, 4, 4, 6, 8, 10} (sum=35)
    assert p17["15"]["n_pop_sessions"] == 14
    assert p17["15"]["share"] == pytest.approx(2.0 / 7.0)  # w in {10, 20}
    assert p17["15"]["energy_at_risk"] == pytest.approx((1.0 + 2.0) / 35.0)
    assert p17["30"]["share"] == pytest.approx(3.0 / 7.0)  # w in {10, 20, 40}
    assert p17["60"]["share"] == pytest.approx(4.0 / 7.0)  # w in {10, 20, 40, 60}

    # T2 instance builder accepts PK sessions directly
    sds = build_t2_site_days(by_site)
    assert len(sds) == 2
    sd = sds[0]
    assert sd.N == 6  # short w=10 session dropped because d_i == 0
    assert np.all(sd.P == T2_P_UNITS)
    assert np.all(sd.a == 0)
    assert sorted(sd.d.tolist()) == [1, 2, 4, 6, 8, 10]
    # Remaining kWh = [2, 4, 4, 6, 8, 10] -> E_i = ceil(rem / 0.25) = [8, 16, 16, 24, 32, 40]
    assert sorted(sd.E.tolist()) == [8, 16, 16, 24, 32, 40]

    cell = Cell(family="F0R", M=3, delta_A=2, delta_b=0, rho=0.95, r=0.3)
    inst = build_acn_instance(60000, cell, sd)
    assert inst.N == 6
    assert inst.H == 24
    assert np.array_equal(inst.E, sd.E)
    assert np.array_equal(inst.P, sd.P)

    # Mini run_t2 smoke on synthetic PK site-days
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
    spec = importlib.util.spec_from_file_location("acn_all_script", script_path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_acn_all_cli_dataset_pk(tmp_path: Path):
    mod = _load_acn_all_module()

    # Amendment 3: --dataset pk runs T1 only (no --seeds required); acn still requires --seeds
    parsed_pk = mod._parse_args(["--dataset", "pk", "--run-name", "check_defaults"])
    assert parsed_pk.seeds is None
    with pytest.raises(SystemExit):
        mod._parse_args(["--dataset", "acn", "--run-name", "missing_seeds"])

    # Write synthetic CSV and run end-to-end with --dataset pk (T1 only per amendment 3)
    csv_path = tmp_path / "synthetic_pk.csv"
    rows = _make_synthetic_pk_rows()
    fieldnames = list(rows[0].keys())
    with csv_path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)

    loaded, _ = load_pk_sites(csv_path)
    assert len(loaded["Mill Street, Perth"]) == 24

    out_root = tmp_path / "out"
    rc = mod.main(
        [
            "--dataset",
            "pk",
            "--pk-csv",
            str(csv_path),
            "--out-root",
            str(out_root),
            "--run-name",
            "pk_unit",
            "--n-boot-t1",
            "50",
            "--smoke-quiet",
        ]
    )
    assert rc == 0

    run_dir = out_root / "pk_unit"
    assert (run_dir / "cleaning.json").exists()
    assert (run_dir / "t1.json").exists()
    assert (run_dir / "summary.json").exists()
    # Amendment 3: PK runs T1 only (no T2, no T3, no T2-emp, no real-limit)
    assert not (run_dir / "t2_rows.jsonl").exists()
    assert not (run_dir / "t2_manifest.json").exists()
    assert not (run_dir / "t2_analysis.json").exists()
    assert not (run_dir / "t3.json").exists()
    assert not (run_dir / "t2_emp_rows.jsonl").exists()
    assert not (run_dir / "real_limit_rows.jsonl").exists()

    t1 = json.loads((run_dir / "t1.json").read_text())
    assert t1["meta"]["boot_seed"] == PK_T1_BOOT_SEED
    summary = json.loads((run_dir / "summary.json").read_text())
    assert summary["dataset"] == "pk"
    assert summary["status"] == "t1_only"
    assert summary["t2_runnable"] is False
    assert summary["t1_boot_seed"] == PK_T1_BOOT_SEED
    assert summary["t1_pooled_site_days"] == 2
    assert summary["t3_pooled_events"] is None
    assert summary["t2_rows_written"] == 0
    assert summary["t2_emp_rows_written"] == 0
    assert summary["real_limit_rows_written"] == 0
    assert summary["amendment_3_sha256"] is not None


def test_date_repair_unit_cases():
    # In-range date -> untouched
    assert repair_pk_date(date(2018, 9, 1)) == (date(2018, 9, 1), False)
    assert repair_pk_date(date(2019, 8, 31)) == (date(2019, 8, 31), False)
    assert PK_WINDOW_START == date(2018, 9, 1)
    assert PK_WINDOW_END == date(2019, 8, 31)

    # Outside range with day <= 12 -> swap day and month into range
    assert repair_pk_date(date(2019, 12, 8)) == (date(2019, 8, 12), True)
    assert repair_pk_date(date(2018, 1, 12)) == (date(2018, 12, 1), True)
    assert repair_pk_date(date(2018, 3, 10)) == (date(2018, 10, 3), True)

    # Outside range with day <= 12, but still outside range after swap -> (None, True)
    assert repair_pk_date(date(1970, 1, 1)) == (None, True)
    assert repair_pk_date(date(2020, 1, 5)) == (None, True)
    assert repair_pk_date(date(2018, 5, 4)) == (None, True)  # 2018-04-05 still < 2018-09-01

    # Outside range with day > 12 -> cannot swap -> (None, False)
    assert repair_pk_date(date(2019, 9, 15)) == (None, False)
    assert repair_pk_date(date(2018, 8, 25)) == (None, False)


def test_clean_pk_rows_amendment_3_date_repair_and_counts():
    rows = [
        # 1. Both start and end swapped into range: 2019-12-08 -> 2019-08-12 (kept)
        _pk_row(
            row_id="swap_both",
            cp_id="50001",
            start_date="2019-12-08T00:00:00",
            start_time="16:00",
            end_date="2019-12-08T00:00:00",
            end_time="18:00",
            total_kwh="8.0",
        ),
        # 2. Only start swapped (overnight across day 12->13): 2019-12-06 -> 2019-06-12 to 2019-06-13 (kept)
        _pk_row(
            row_id="swap_start_only",
            cp_id="50002",
            start_date="2019-12-06T00:00:00",
            start_time="20:00",
            end_date="2019-06-13T00:00:00",
            end_time="08:00",
            total_kwh="12.0",
        ),
        # 3. Only end swapped (overnight Nov 30 -> Dec 1): 2018-11-30 to 2018-01-12 -> 2018-12-01 (kept)
        _pk_row(
            row_id="swap_end_only",
            cp_id="50003",
            start_date="2018-11-30T00:00:00",
            start_time="20:00",
            end_date="2018-01-12T00:00:00",
            end_time="09:00",
            total_kwh="14.0",
        ),
        # 4. Still outside range after swap (1970-01-01) -> dropped_date_outside_range
        _pk_row(
            row_id="still_out_swap",
            cp_id="50004",
            start_date="2019-06-10T00:00:00",
            start_time="16:00",
            end_date="1970-01-01T00:00:00",
            end_time="18:00",
            total_kwh="5.0",
        ),
        # 5. Outside range with day > 12 (cannot swap) -> dropped_date_outside_range
        _pk_row(
            row_id="out_day_gt_12",
            cp_id="50005",
            start_date="2019-09-20T00:00:00",
            start_time="16:00",
            end_date="2019-09-20T00:00:00",
            end_time="18:00",
            total_kwh="5.0",
        ),
        # 6. Swap makes end precede start: 2019-08-07 22:35 -> 2019-09-07 08:40 (swaps end to 2019-07-09 < 2019-08-07)
        _pk_row(
            row_id="swap_end_lt_start",
            cp_id="50006",
            start_date="2019-08-07T00:00:00",
            start_time="22:35",
            end_date="2019-09-07T00:00:00",
            end_time="08:40",
            total_kwh="10.0",
        ),
        # 7. Unswapped normal in-range row (kept)
        _pk_row(
            row_id="normal",
            cp_id="50007",
            start_date="2019-06-10T00:00:00",
            start_time="10:00",
            end_date="2019-06-10T00:00:00",
            end_time="12:00",
            total_kwh="6.0",
        ),
    ]

    by_site, reports = clean_pk_rows(rows)
    rep = reports["Mill Street, Perth"]
    assert rep.raw_count == 7
    assert rep.dropped_date_outside_range == 2
    assert rep.repaired_date_rows == 4  # rows 1, 2, 3, and 6 (before end < start drop)
    assert rep.repaired_start_date == 2  # rows 1, 2
    assert rep.repaired_end_date == 3    # rows 1, 3, 6
    assert rep.dropped_swap_end_lt_start == 1
    assert rep.dropped_end_le_start == 0
    assert rep.kept_count == 4
    assert rep.after_end_gt_start == 4

    by_id = {s.session_id: s for s in by_site["Mill Street, Perth"]}
    assert set(by_id.keys()) == {"swap_both", "swap_start_only", "swap_end_only", "normal"}
    assert by_id["swap_both"].local_date == date(2019, 8, 12)
    assert by_id["swap_both"].duration_s == pytest.approx(2.0 * 3600.0)
    assert by_id["swap_start_only"].local_date == date(2019, 6, 12)
    assert by_id["swap_start_only"].duration_s == pytest.approx(12.0 * 3600.0)
    assert by_id["swap_end_only"].local_date == date(2018, 11, 30)
    assert by_id["swap_end_only"].duration_s == pytest.approx(13.0 * 3600.0)

