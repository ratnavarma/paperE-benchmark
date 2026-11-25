"""Tests for scripts/aggregate_tuning.py on a synthetic rows file (no generation, no simulation)."""
from __future__ import annotations

import csv
import importlib.util
import io
import json
import statistics
import sys
from pathlib import Path

import pytest

from papere.generator import F0R_CELLS
from papere.policies.catalog import FAMILIES

_SPEC = importlib.util.spec_from_file_location(
    "aggregate_tuning", Path(__file__).resolve().parents[1] / "scripts" / "aggregate_tuning.py")
agg = importlib.util.module_from_spec(_SPEC)
sys.modules["aggregate_tuning"] = agg          # dataclasses needs the module registered
_SPEC.loader.exec_module(agg)

SHA = "ab" * 32
CELL0, CELL1 = F0R_CELLS[0].cell_id, F0R_CELLS[1].cell_id
SYM = next(f for f in FAMILIES if f.name == "sym_margin")


def make_row(family, cell, idx, seed, r, **over):
    fam = next(f for f in FAMILIES if f.name == family)
    row = {"policy": f"{family}@c{idx:02d}", "seed": seed, "cell_id": cell, "family": family,
           "kind": fam.kind, "config": dict(fam.grid[idx]), "config_index": idx,
           "mode": "tune", "params_sha256": SHA,
           "R_avoid_kwh_per100": r, "R_avoid_sp_kwh_per100": r + 1.0,
           "violation_kwslot": 2.0 * r, "violation_count": 3, "hedge_waste_kwslot": 0.5,
           "deadline_miss_count": 4, "event_shortfall_kwh": 0.25, "cpu_ms_mean": 0.1 * seed % 1}
    row.update(over)
    return row


@pytest.fixture
def rows_file(tmp_path):
    p = tmp_path / "rows.jsonl"
    vals = [1.0, 2.0, 4.0, 7.0]
    lines = [json.dumps(make_row("sym_margin", CELL0, 0, 60000 + i, v))
             for i, v in enumerate(vals)]
    lines.append(json.dumps(make_row("sym_margin", CELL0, 0, 60001, 99.0)))      # duplicate seed
    lines.append(json.dumps(make_row("sym_margin", CELL1, 5, 60049, -3.0)))
    lines.append(json.dumps(make_row("ce_llf", CELL0, 0, 60000, 1.0)))           # not tunable
    lines.append(json.dumps(make_row("sym_margin", CELL0, 1, 60000, 1.0, mode="final")))
    text = "\n".join(lines) + "\n" + '{"policy": "sym_margin@c00", "seed": 600'   # partial tail
    p.write_text(text)
    return p, vals


def test_expected_rows_derived_from_catalog():
    assert len(agg.tunable_families()) == 13
    assert len(F0R_CELLS) == 22
    assert agg.expected_rows() == 686_400


def test_aggregate_values_and_partial_line(rows_file):
    p, vals = rows_file
    before = p.read_bytes()
    groups, st = agg.aggregate(p)
    assert p.read_bytes() == before                      # input untouched
    assert st.skipped_unparsable == 1
    assert st.duplicates == 1
    assert st.skipped_untunable_family == 1 and st.skipped_not_tune == 1
    assert st.used == 5
    g = groups[("sym_margin", CELL0, 0)]
    assert g.n == 4 and g.seeds == {60000, 60001, 60002, 60003}
    assert g.mean == pytest.approx(statistics.mean(vals))
    assert (g.m2 / (g.n - 1)) ** 0.5 == pytest.approx(statistics.stdev(vals))
    assert g.config == SYM.grid[0]
    assert ("sym_margin", CELL1, 5) in groups


def test_csv_output_and_coverage(rows_file, tmp_path):
    p, vals = rows_file
    out = tmp_path / "aggregates.csv"
    buf = io.StringIO()
    groups, st = agg.aggregate(p)
    assert agg.write_csv(groups, out) == 2
    cov = agg.print_coverage(groups, st, file=buf)
    with open(out, newline="") as fh:
        rows = list(csv.DictReader(fh))
    assert list(rows[0]) == agg.COLUMNS
    r0 = next(r for r in rows if r["cell_id"] == CELL0)
    assert (r0["family"], r0["kind"], r0["config_index"], r0["n_seeds"]) == (
        "sym_margin", "oblivious", "0", "4")
    assert (r0["seed_min"], r0["seed_max"]) == ("60000", "60003")
    assert json.loads(r0["config"]) == SYM.grid[0]
    assert float(r0["R_avoid_kwh_per100_mean"]) == pytest.approx(3.5)
    assert float(r0["R_avoid_kwh_per100_sd"]) == pytest.approx(statistics.stdev(vals))
    assert float(r0["R_avoid_sp_kwh_per100_mean"]) == pytest.approx(4.5)
    assert float(r0["violation_kwslot_mean"]) == pytest.approx(7.0)
    assert float(r0["violation_count_mean"]) == 3.0
    assert float(r0["hedge_waste_kwslot_mean"]) == 0.5
    assert r0["params_sha256"] == SHA
    r1 = next(r for r in rows if r["cell_id"] == CELL1)
    assert r1["n_seeds"] == "1" and r1["R_avoid_kwh_per100_sd"] == ""
    # coverage
    assert cov["expected_rows"] == 686_400 and cov["rows_used"] == 5
    assert cov["short"]["sym_margin"] == 48 * 22         # nothing reaches 50 seeds
    assert cov["zero"]["sym_margin"] == 48 * 22 - 2
    assert cov["short"]["mpc_ce"] == 48 * 22 and "ce_llf" not in cov["short"]
    assert "5 rows used / 686400 expected" in buf.getvalue()


def test_full_group_is_not_short(tmp_path):
    p = tmp_path / "rows.jsonl"
    p.write_text("\n".join(json.dumps(make_row("sym_margin", CELL0, 0, 60000 + i, float(i)))
                           for i in range(50)) + "\n")
    groups, st = agg.aggregate(p)
    cov = agg.coverage(groups, st)
    assert cov["short"]["sym_margin"] == 48 * 22 - 1


def test_params_sha_must_be_single_valued(tmp_path):
    p = tmp_path / "rows.jsonl"
    p.write_text(json.dumps(make_row("sym_margin", CELL0, 0, 60000, 1.0)) + "\n"
                 + json.dumps(make_row("sym_margin", CELL0, 0, 60001, 1.0,
                                       params_sha256="cd" * 32)) + "\n")
    with pytest.raises(AssertionError):
        agg.aggregate(p)
