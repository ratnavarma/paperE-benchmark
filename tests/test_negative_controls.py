"""Tests for scripts/negative_controls.py (tiny seed counts inside the tuning block 60000-60049)."""
from __future__ import annotations

import copy
import importlib.util
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from papere.generator import F0R_CELLS, generate_f0r
from papere.policies.beliefs import CEBelief
from papere.policies.mpc import guarded_mpc, mpc_ce
from papere.sim import simulate

_SPEC = importlib.util.spec_from_file_location(
    "negative_controls", Path(__file__).resolve().parents[1] / "scripts" / "negative_controls.py")
nc = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(nc)

SEED = 60000


# ------------------------------------------------------------------ seeds
@pytest.mark.seed_rule_exempt      # refusal test: the script refuses these seeds before generating
def test_seed_guard():
    assert nc.parse_seeds("60000-60002") == [60000, 60001, 60002]
    for bad in ("61000-61001", "59999-60000", "60049-60050", "500000-500001"):  # seed-rule: refusal-test
        with pytest.raises(SystemExit):
            nc.parse_seeds(bad)
    with pytest.raises(SystemExit):
        nc.check_seeds([60000, 62000])  # seed-rule: refusal-test


# ------------------------------------------------------------------ bootstrap
def test_bootstrap_constant_and_symmetric():
    b = nc.paired_bootstrap(np.full(20, 0.3), n_boot=2000)
    assert b["mean"] == pytest.approx(0.3) and b["lo"] == pytest.approx(0.3)
    assert b["hi"] == pytest.approx(0.3)
    z = nc.paired_bootstrap(np.array([1.0, -1.0] * 10), n_boot=4000)
    assert z["mean"] == 0.0 and z["lo"] < 0.0 < z["hi"]
    assert z["lo"] == pytest.approx(-z["hi"], abs=0.15)


def test_bootstrap_matches_normal_theory_and_is_reproducible():
    rng = np.random.default_rng(1)
    d = rng.normal(0.2, 1.0, size=400)
    b = nc.paired_bootstrap(d, n_boot=10_000, rng_seed=5)
    half = 1.96 * d.std(ddof=1) / np.sqrt(d.size)
    assert b["lo"] == pytest.approx(d.mean() - half, abs=0.02)
    assert b["hi"] == pytest.approx(d.mean() + half, abs=0.02)
    assert nc.paired_bootstrap(d, n_boot=500, rng_seed=5) == nc.paired_bootstrap(
        d, n_boot=500, rng_seed=5)
    assert nc.paired_bootstrap(d, n_boot=500, rng_seed=6) != nc.paired_bootstrap(
        d, n_boot=500, rng_seed=5)


def test_bootstrap_known_small_case_by_enumeration():
    # n = 2: the mean takes values d0, (d0+d1)/2, d1 with probabilities 1/4, 1/2, 1/4
    b = nc.paired_bootstrap(np.array([0.0, 4.0]), n_boot=20_000, rng_seed=3)
    assert b["lo"] == pytest.approx(0.0, abs=1e-9) and b["hi"] == pytest.approx(4.0, abs=1e-9)
    assert b["mean"] == 2.0


# ------------------------------------------------------------------ NC2 comparator
def _pair(cell, W=24, m=0, gamma=0.0):
    inst = generate_f0r(SEED, cell)
    tg = simulate(inst, cell, guarded_mpc(CEBelief(), W, m, gamma, name=nc.NC2_NAME), SEED)
    tc = simulate(inst, cell, mpc_ce(W, m, 0, name=nc.NC2_NAME), SEED)
    return tg, tc


def _cell(dA, rho=1.15, M=3):
    return next(c for c in F0R_CELLS if c.delta_A == dA and c.rho == rho and c.M == M
                and c.r == 0.3 and c.delta_b == 0)


def test_nc2_identical_trajectories_have_zero_mismatches():
    for dA in (0, 2):
        tg, tc = _pair(_cell(dA), 8, 1, 0.5)
        out = nc.compare_trajectories(tg, tc)
        assert out["mismatches"] == 0 and out["actions_compared"] >= tg.x.shape[1]


def test_nc2_comparator_detects_injected_mismatch():
    tg, tc = _pair(_cell(2))
    bad = copy.deepcopy(tc)
    bad.x[3, 5] += 1
    out = nc.compare_trajectories(tg, bad)
    assert out["slot_mismatch"] == 1 and out["entry_mismatch"] == 1
    assert out["mismatches"] >= 1 and out["first_bad_slot"] == 5
    # a different number of rounds in a slot is also a mismatch
    bad2 = copy.deepcopy(tc)
    bad2.rounds[2] += 1
    assert nc.compare_trajectories(tg, bad2)["round_mismatch"] == 1


def test_nc2_comparator_detects_redispatch_log_difference():
    tg, tc = _pair(_cell(0))
    assert len(tg.redispatch_log) > 0, "pick a cell/seed with re-dispatch"
    bad = copy.deepcopy(tc)
    t, rnd, x, rev = bad.redispatch_log[0]
    x2 = x.copy()
    x2[0] += 1
    bad.redispatch_log[0] = (t, rnd, x2, rev)
    assert nc.compare_trajectories(tg, bad)["log_mismatch"] == 1
    bad.redispatch_log.pop()
    assert nc.compare_trajectories(tg, bad)["log_mismatch"] >= 1


def test_run_nc2_zero_mismatch_and_detects_broken_baseline(monkeypatch):
    monkeypatch.setattr(nc, "NC2_CELLS", [_cell(0), _cell(2)])
    monkeypatch.setattr(nc, "NC2_CONFIGS", ((24, 0, 0.0), (2, 2, 2.0)))
    rows = nc.run_nc2(SEED)
    assert len(rows) == 4 and all(r["mismatches"] == 0 for r in rows)
    s = nc.summarize_nc2(rows)
    assert s["verdict"] == "PASS" and s["total_mismatches"] == 0 and s["n_failing_sims"] == 0

    import papere.policies.mpc as mpc_mod
    orig = mpc_mod.mpc_ce
    monkeypatch.setattr(mpc_mod, "mpc_ce", lambda W, m, k, name=None: orig(W, m + 3, k, name=name))
    bad = nc.run_nc2(SEED)
    sb = nc.summarize_nc2(bad)
    assert sb["verdict"] == "FAIL" and sb["total_mismatches"] > 0
    assert sb["failing"] and {"cell_id", "seed", "W"} <= set(sb["failing"][0])


# ------------------------------------------------------------------ NC1 summary logic
def _r1(fam, seed, ra, rsp, ex=False, err=None):
    return {"control": "NC1", "family": fam, "kind": "oblivious", "seed": seed, "cell_id": "x",
            "R_avoid_u": ra, "R_avoid_sp_u": rsp, "exceeds_bound": ex, "violation_count": 0,
            "deadline_miss_count": 0, "error": err}


def test_nc1_summary_counts_and_two_verdicts():
    rows = ([_r1("a", s, 0.0, 0.0) for s in (1, 2, 3)]                      # clean
            + [_r1("b", 1, 0.0, 1.0), _r1("b", 2, 0.0, 1.0), _r1("b", 3, 0.0, 0.0)]  # sp only
            + [_r1("c", 1, -1.0, 0.0, True), _r1("c", 2, 0.0, 0.0), _r1("c", 3, 4.0, 5.0)])
    s = nc.summarize_nc1(rows)
    fa, fb, fc = (s["families"][k] for k in "abc")
    assert fa["n_nonzero_R_avoid"] == 0 and fa["n_nonzero_R_avoid_sp"] == 0
    assert fb["n_nonzero_R_avoid"] == 0 and fb["n_nonzero_R_avoid_sp"] == 2
    assert fb["max_R_avoid_sp_u"] == 1.0 and fb["mean_R_avoid_sp_u"] == pytest.approx(2 / 3)
    assert fc["n_nonzero_R_avoid"] == 2 and fc["n_exceeds_bound"] == 1
    assert fc["max_R_avoid_u"] == 4.0 and fc["min_R_avoid_u"] == -1.0
    assert fc["failing_seeds_R_avoid"] == [1, 3]
    assert s["failing_families_literal"] == ["c"] and s["failing_families_sp"] == ["b", "c"]
    assert s["verdict_literal_R_avoid"] == "FAIL" and s["verdict_R_avoid_sp"] == "FAIL"


def test_nc1_summary_pass_and_error_rows():
    clean = [_r1("a", s, 0.0, 0.0) for s in (1, 2)]
    s = nc.summarize_nc1(clean)
    assert s["verdict_literal_R_avoid"] == "PASS" and s["verdict_R_avoid_sp"] == "PASS"
    s = nc.summarize_nc1(clean + [_r1("e", 1, None, None, None, err="boom")])
    assert s["families"]["e"]["n_errors"] == 1
    assert s["verdict_literal_R_avoid"] == "FAIL" and s["failing_families_literal"] == ["e"]


# ------------------------------------------------------------------ NC3'/NC4 summary logic
def _rp(cell, seed, diff, ident=True, matched=None):
    r = {"control": "NC4", "cell_id": cell, "seed": seed, "diff_kwh_per100": diff,
         "e1_R_avoid_kwh_per100": 1.0 + diff, "pop_R_avoid_kwh_per100": 1.0,
         "identical_catalog_names": ident}
    if matched is not None:
        r["identical_matched_names"] = matched
    return r


def test_pair_summary_pass_fail_and_identical_counts():
    rows = ([_rp("zero", s, 0.0, True, True) for s in range(10)]
            + [_rp("wide", s, 3.0 * (-1) ** s, False, True) for s in range(10)]
            + [_rp("shift", s, 0.8, False, False) for s in range(10)]
            + [_rp("small", s, 0.01 * (-1) ** s) for s in range(10)])
    s = nc.summarize_pairs(rows, ["zero", "wide", "shift", "small"], n_boot=2000)
    c = s["cells"]
    assert c["zero"]["pass"] and c["zero"]["ci_lo"] == c["zero"]["ci_hi"] == 0.0
    assert c["zero"]["n_identical_catalog_names"] == 10 and c["zero"]["n_identical_matched_names"] == 10
    assert not c["wide"]["pass"]                       # CI half-width far above 0.5
    assert c["wide"]["n_identical_catalog_names"] == 0 and c["wide"]["n_identical_matched_names"] == 10
    assert not c["shift"]["pass"] and c["shift"]["mean_diff"] == pytest.approx(0.8)
    assert c["small"]["pass"] and c["small"]["n_identical_matched_names"] is None
    assert s["verdict"] == "FAIL" and s["failing_cells"] == ["wide", "shift"]
    ok = nc.summarize_pairs([r for r in rows if r["cell_id"] in ("zero", "small")], n_boot=500)
    assert ok["verdict"] == "PASS"


def test_pair_summary_matched_name_supplement_and_report_renders():
    rows = []
    for s in range(10):
        r = _rp("m0", s, 3.0 * (-1) ** s, False, True)
        r["diff_matched_kwh_per100"] = 0.0
        rows.append(r)
    sm = nc.summarize_pairs(rows, ["m0"], n_boot=500)
    c = sm["cells"]["m0"]
    assert not c["pass"] and c["matched_pass"] and c["matched_ci_lo"] == c["matched_ci_hi"] == 0.0


def test_pair_summary_boundary_is_inclusive():
    rows = [_rp("edge", s, 0.5) for s in range(5)]     # CI = [0.5, 0.5] exactly
    assert nc.summarize_pairs(rows, n_boot=200)["cells"]["edge"]["pass"]
    rows = [_rp("over", s, 0.5001) for s in range(5)]
    assert not nc.summarize_pairs(rows, n_boot=200)["cells"]["over"]["pass"]


# ------------------------------------------------------------------ end-to-end on a tiny spec
def test_run_seed_tiny(monkeypatch):
    c0 = _cell(2, 0.95, 0)
    monkeypatch.setattr(nc, "NC1_FAMILY_NAMES", ["ce_llf", "guarded_mpc_e1"])
    monkeypatch.setattr(nc, "NC2_CELLS", [c0])
    monkeypatch.setattr(nc, "NC2_CONFIGS", ((24, 0, 0.0),))
    monkeypatch.setattr(nc, "NC3_CELLS", [replace(c0, homogeneous_iid=True)])
    monkeypatch.setattr(nc, "NC4_CELLS", [c0])
    out = nc.run_seed(SEED)
    assert {r["family"] for r in out["NC1"]} == {"ce_llf", "guarded_mpc_e1"}
    assert len(out["NC2"]) == 1 and out["NC2"][0]["mismatches"] == 0
    assert out["NC3p"][0]["cell_id"].endswith("_iid")
    r4 = out["NC4"][0]
    assert r4["identical_matched_names"] is True       # M = 0: e1 and population coincide
    assert r4["diff_matched_kwh_per100"] == 0.0
    assert "identical_matched_names" in out["NC3p"][0] or out["NC3p"][0]["cell_id"].find("_M0_") < 0
    rows = nc.collect([out])
    summ = nc.build_summaries(rows)
    assert set(summ["verdicts"]) == {"NC1_literal_R_avoid", "NC1_R_avoid_sp",
                                     "NC1_exact_R_avoid_diagnostic", "NC2", "NC3p", "NC4"}
    res = {"label": "development", "seeds": {"first": SEED, "last": SEED, "count": 1},
           "git": {"commit": "x", "dirty_paths": []}, "package_versions": {},
           "population_params_sha256": "s", "population_params_path": "p", "workers": 1,
           "runtime_seconds": 1.0, "finished_utc": "t", "rows": rows, "summaries": summ,
           "spec": {"boot_seed": nc.BOOT_SEED, "nc1_cell": nc.NC1_CELL.cell_id,
                    "nc3_cells": [c.cell_id for c in nc.NC3_CELLS],
                    "nc4_cells": [c.cell_id for c in nc.NC4_CELLS]}}
    md = nc.render_report(res)
    assert "## NC1" in md and "## NC4" in md and "development" in md.lower()
    assert "Owner-side rulings" in md and md.index("Owner-side rulings") < md.index("## NC1")


def test_exact_base_instance_and_nc1_decomposition():
    inst = generate_f0r(SEED, nc.NC1_CELL)
    ix = nc.exact_base_instance(inst)
    assert np.all(ix.b == inst.N) and np.all(ix.b_mean == inst.N)
    assert np.array_equal(ix.E, inst.E) and np.array_equal(ix.availability(), inst.availability())
    assert not np.allclose(inst.b, ix.b)                      # the original has ramp and noise
    assert ix.L[0, 0] == pytest.approx((inst.E.sum() / 0.7 + inst.N * inst.H) / inst.H)
    rows = nc.run_nc1(SEED)
    for r in rows:
        if r["error"] is None:
            assert r["overshoot_u"] == max(0.0, -r["R_avoid_u"])
            assert r["cap_gap_u"] == r["R_avoid_sp_u"] - r["R_avoid_u"]
        # exact forecast: caps agree, so the two bounds coincide
        assert r["exact_R_avoid_u"] == r["exact_R_avoid_sp_u"]
    s = nc.summarize_nc1(rows)
    assert s["verdict_exact_R_avoid_diagnostic"] in ("PASS", "FAIL")
    assert "mean_overshoot_u" in next(iter(s["families"].values()))


# ------------------------------------------------------------------ rulings, labels, extended mode
def test_cell_label_never_calls_a_wide_cell_a_pass():
    assert nc.cell_label(-0.3, 0.2) == "pass"
    assert nc.cell_label(0.1, 0.3).startswith("pass (difference detected")
    wide = nc.cell_label(-0.8, 0.6)
    assert wide.startswith("no difference detected at this size") and "-0.800" in wide
    assert nc.cell_label(0.2, 0.9).startswith("difference detected")
    assert nc.cell_label(-1.5, -0.7).startswith("difference detected")
    assert not nc.cell_label(-0.8, 0.6).startswith("pass")


def _r1x(fam, seed, ra, rsp, xa, xsp):
    r = _r1(fam, seed, ra, rsp)
    r.update(exact_R_avoid_u=xa, exact_R_avoid_sp_u=xsp, exact_error=None,
             overshoot_u=max(0.0, -ra), cap_gap_u=rsp - ra)
    return r


def _fake_res(n1rows, pair_rows):
    n1 = nc.summarize_nc1(n1rows)
    n3 = nc.summarize_pairs(pair_rows, n_boot=300)
    V = {"NC1_literal_R_avoid": n1["verdict_literal_R_avoid"], "NC1_R_avoid_sp": n1["verdict_R_avoid_sp"],
         "NC1_exact_R_avoid_diagnostic": n1["verdict_exact_R_avoid_diagnostic"],
         "NC2": "PASS", "NC3p": n3["verdict"], "NC4": "PASS"}
    return {"seeds": {"first": 60000, "last": 60002, "count": 3},
            "summaries": {"NC1": n1, "NC3p": n3, "verdicts": V}}


def test_rulings_section_content_from_data():
    rows = []
    for s in (1, 2, 3):
        for f in nc.PLANNING:
            rows.append(_r1x(f, s, -1.0, 0.0, 0.0, 0.0))
        rows.append(_r1x("ce_llf", s, 0.0, 1.0, 2.0 if s == 1 else 0.0, 2.0 if s == 1 else 0.0))
    pairs = [_rp("c", s, 0.1 * (-1) ** s) for s in range(10)]
    txt = "\n".join(nc._rulings_section(_fake_res(rows, pairs)))
    assert "Owner-side rulings (ruled by the owner side on 2026-10-20)" in txt
    assert "NC1 and NC1_sp stay FAIL" in txt and "Verdict: **PASS**" in txt
    assert "ce_llf (R_avoid != 0 on 1 seeds" in txt and "Chen et al., sLLF" in txt
    assert "No cell shows a candidate gain whose interval excludes zero." in txt
    # a planning policy with an exact shortfall flips the check to FAIL
    rows.append(_r1x("mpc_ce", 4, 0.0, 0.0, 3.0, 3.0))
    assert "Verdict: **FAIL**" in "\n".join(nc._rulings_section(_fake_res(rows, pairs)))
    # a real candidate gain must be stated, not hidden
    gain = [_rp("c", s, -2.0 - 0.01 * s) for s in range(10)]
    t2 = "\n".join(nc._rulings_section(_fake_res(rows, gain)))
    assert "CORRECTION" in t2 and "No cell shows a candidate gain" not in t2


def test_rulings_section_handles_results_without_exact_fields():
    res = _fake_res([_r1("a", s, 0.0, 0.0) for s in (1, 2)], [_rp("c", s, 0.0) for s in range(5)])
    for f in res["summaries"]["NC1"]["families"].values():
        for k in [k for k in f if k.startswith("exact_")]:
            del f[k]
    assert "not present in this results file" in "\n".join(nc._rulings_section(res))


@pytest.mark.seed_rule_exempt
def test_extended_seed_whitelist_is_its_own_and_original_modes_unchanged():
    ok = nc.parse_seeds("64000-64249", nc.EXT_LO, nc.EXT_HI)
    assert len(ok) == 250 and ok[0] == 64000 and ok[-1] == 64249
    for bad in ("63999-64000", "64249-64250", "60000-60049", "61000-61001", "500000-500001"):  # seed-rule: refusal-test
        with pytest.raises(SystemExit):
            nc.parse_seeds(bad, nc.EXT_LO, nc.EXT_HI)
    with pytest.raises(SystemExit):                      # original modes still refuse 64000
        nc.parse_seeds("64000-64001")
    with pytest.raises(SystemExit):
        nc.run_extended([60000], 1)                      # refuses before generating anything
    with pytest.raises(SystemExit):
        nc.main(["--nc3-extended", "--seeds", "60000-60001"])
    with pytest.raises(SystemExit):
        nc.main(["--seeds", "64000-64001"])


def test_run_extended_tiny_with_patched_whitelist(monkeypatch):
    c0 = _cell(2, 0.95, 0)
    cells = [replace(c0, homogeneous_iid=True), replace(_cell(2, 0.95, 3), homogeneous_iid=True)]
    monkeypatch.setattr(nc, "NC3_CELLS", cells)
    ext = nc.run_extended([60000, 60001, 60002], 1, lo=60000, hi=60049)
    assert ext["mode"] == "nc3_extended" and ext["seeds"]["count"] == 3
    assert ext["git"]["commit"] and "working_tree_dirty" in ext["git"]
    assert len(ext["population_params_sha256"]) == 64 and len(ext["rows"]) == 6
    sm = ext["summary"]
    assert set(sm["cells"]) == {c.cell_id for c in cells}
    for c in sm["cells"].values():
        assert c["label"].startswith("pass") == c["pass"]
    m0 = sm["cells"][cells[0].cell_id]
    assert m0["n_identical_matched_names"] == 3 and m0["matched_ci_lo"] == 0.0
    assert sm["cells"][cells[1].cell_id]["n_identical_matched_names"] is None
    md = "\n".join(nc._ext_section(ext))
    assert "Pre-declared rule" in md and md.index("Pre-declared rule") < md.index("| cell |")
    assert "NC3' extended" in md and "64000-64249" in md
