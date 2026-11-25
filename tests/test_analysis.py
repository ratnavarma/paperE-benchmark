"""Analysis tests (docs/ANALYSIS_SPEC.md): synthetic rows.jsonl files with known effects.

No simulation. Seed numbers 60000-60049 only (seed rule); the tests point the run ranges at
that block. The noise is built from zero-sum cosine patterns, so every planted mean is exact
and every interval must cover it.
"""
import hashlib
import json
import math
from fractions import Fraction
from pathlib import Path

import numpy as np
import pytest

from papere import analysis as an
from papere.analysis import (AnalysisError, Bootstrap, e1_analysis, e2_analysis, e3_analysis,
                             f0r_cell_id, frozen_best, g2_analysis, load_rows, reading_label)
from papere.generator import F0R_CELLS, scale_cell
from papere.instance import Cell

LO, HI = 60000, 60049
SEEDS = list(range(LO, HI + 1))
RANGE = (LO, HI)
NS = len(SEEDS)
IDX = np.arange(NS)
HIGH, LOW = (2, 4), (0, 1)

OBL_OFFSET = {"sym_margin": 0.0, "ce_llf": 0.5, "ce_edf": 0.8, "pes_llf": 0.6,
              "persistence": 0.4, "uncorr_pes": 0.7, "probe_first": 0.9, "mpc_ce": 0.3,
              "mpc_pes": 0.35, "pop_mpc": 0.2}
ALL_POLICIES = [*OBL_OFFSET, "floor", "guarded_mpc_e1", "oracle_mpc", *an.PER_PARTICIPANT,
                "bound"]
POLICY_K = {p: k for k, p in enumerate(ALL_POLICIES, start=2)}
TUNABLE = ("sym_margin", "persistence", "uncorr_pes", "probe_first", "mpc_ce", "mpc_pes",
           "pop_mpc", "floor")


def wave(k: int, amp: float) -> np.ndarray:
    """Zero-sum pattern over the 50 seeds (a full cosine period, k not a multiple of 50)."""
    return amp * np.cos(2 * np.pi * k * IDX / NS + 0.3 * k)


def write_rows(path: Path, rows: list[dict]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    return path


def metrics(R, u_hi, u_lo, **extra) -> dict:
    """Per-seed metric arrays with a consistent split (R = U_hi + C_lo = U_lo + C_hi)."""
    R, u_hi, u_lo = (np.broadcast_to(np.asarray(x, float), (NS,)) for x in (R, u_hi, u_lo))
    d = {k: np.zeros(NS) for k in (*an.DESCRIPTIVE_KEYS, "cpu_ms_p95", "cpu_ms_max", "wall_ms")}
    d.update({"R_avoid_kwh_per100": R, "R_uncorr_hi_kwh_per100": u_hi,
              "R_uncorr_lo_kwh_per100": u_lo, "R_corr_lo_kwh_per100": R - u_hi,
              "R_corr_hi_kwh_per100": R - u_lo})
    d.update({k: np.broadcast_to(np.asarray(v, float), (NS,)) for k, v in extra.items()})
    return d


def emit(study, policy, cell_id, m: dict, *, N=30, kind=None, privileged=None, drop_seeds=(),
         mode="frozen"):
    kind = kind or an.KIND_OF[policy]
    if privileged is None:
        privileged = policy in an.PRIVILEGED_OK
    out = []
    for i, s in enumerate(SEEDS):
        if s in drop_seeds:
            continue
        row = {"study_family": study, "family": policy, "policy": policy, "kind": kind,
               "privileged": privileged, "mode": mode, "seed": s, "cell_id": cell_id,
               "config": None, "N": N}
        row.update({k: float(v[i]) for k, v in m.items()})
        out.append(row)
    return out


def prim_cells(Ms=(0, 3), deltas=(0, 1, 2, 4), rhos=(0.95, 1.15), extra=False, family="F0R"):
    cs = [Cell(family=family, M=M, delta_A=d, delta_b=0, rho=rho, r=0.3)
          for M in Ms for d in deltas for rho in rhos]
    if extra:                                         # the six sweep / lag-split cells
        ids = {c.cell_id for c in cs}
        for c in F0R_CELLS:
            c2 = Cell(family=family, M=c.M, delta_A=c.delta_A, delta_b=c.delta_b, rho=c.rho,
                      r=c.r)
            if c2.cell_id not in ids:
                cs.append(c2)
    return cs


def base_R(cell: Cell) -> float:
    return (5.0 + 0.1 * cell.delta_A + (0.2 if cell.rho == 1.15 else 0.0) + 0.05 * cell.M
            + 0.07 * cell.r + 0.11 * cell.delta_b - (0.3 if cell.rho == 0.7 else 0.0))


def f0r_rows(*, cells=None, study="F0R", N=30, gain_high=1.0, oracle_gain_high=2.0,
             gu=(0.9, 0.7), floor_off=(0.2, 0.5), best_override=None, drop=None,
             **cell_kw) -> list[dict]:
    """Rows for ten oblivious policies, floor, candidate, oracle, per-participant and bound."""
    cells = prim_cells(**cell_kw) if cells is None else cells
    rows = []
    shared = wave(1, 0.3)
    for cell in cells:
        cid, d = cell.cell_id, cell.delta_A
        base = base_R(cell)
        hi = d in HIGH
        clean = {p: base + o for p, o in OBL_OFFSET.items()}
        if best_override and (cell.M, d, cell.rho) in best_override:
            p, v = best_override[(cell.M, d, cell.rho)]
            clean[p] = base + v
        best_clean = min(clean.values())
        U = (1.0, 0.8)
        for p, v in clean.items():
            rows += emit(study, p, cid, metrics(v + shared + wave(POLICY_K[p], 0.1), *U), N=N)
        fl = base - (floor_off[1] if hi else floor_off[0])
        rows += emit(study, "floor", cid,
                     metrics(fl + shared + wave(POLICY_K["floor"], 0.1), *U,
                             event_shortfall_kwh_per100=1.5), N=N)
        g = gain_high if hi else 0.0
        guh, gul = gu if hi else (0.0, 0.0)
        rows += emit(study, "guarded_mpc_e1", cid,
                     metrics(best_clean - g + shared + wave(POLICY_K["guarded_mpc_e1"], 0.1),
                             U[0] - guh, U[1] - gul), N=N)
        og = oracle_gain_high if hi else 0.0
        rows += emit(study, "oracle_mpc", cid,
                     metrics(best_clean - og + shared + wave(POLICY_K["oracle_mpc"], 0.1),
                             U[0] - guh, U[1] - gul), N=N)
        for p in an.PER_PARTICIPANT:
            off = 0.3 if p == "rwdf_e_literal" else 0.0
            rows += emit(study, p, cid,
                         metrics(base + 0.1 + off + shared + wave(POLICY_K[p], 0.1), *U), N=N)
        rows += emit(study, "bound", cid, metrics(0.0, 0.0, 0.0), N=N)
    if drop:
        rows = [r for r in rows if not drop(r)]
    return rows


def write_frozen(path: Path, rows: list[dict], override=None) -> Path:
    """A TUNING_FROZEN.json whose objective is each tunable family's mean R in ``rows``."""
    acc: dict = {}
    for r in rows:
        if r["study_family"] == "F0R" and r["policy"] in TUNABLE:
            acc.setdefault((r["policy"], r["cell_id"]), []).append(r["R_avoid_kwh_per100"])
    d: dict = {}
    for (p, c), v in acc.items():
        d.setdefault(p, {})[c] = {"config_index": 0, "config": {},
                                  "mean_R_avoid_kwh_per100": float(np.mean(v)),
                                  "mean_violation_kwslot": 0.0, "n_seeds": 50, "seeds": [LO, HI]}
    for (p, c), v in (override or {}).items():
        d[p][c]["mean_R_avoid_kwh_per100"] = v
    d["_meta"] = {"seeds": [LO, HI], "n_seeds": 50}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(d))
    return path


@pytest.fixture(scope="module")
def boot():
    return Bootstrap()


@pytest.fixture(scope="module")
def data(tmp_path_factory):
    d = tmp_path_factory.mktemp("f0r")
    rows = f0r_rows(extra=True)
    write_rows(d / "rows.jsonl", rows)
    fz = write_frozen(d / "frozen.json", rows)
    return {"dir": d, "rows": rows, "frozen_path": fz, "frozen": an.load_frozen_file(fz)}


@pytest.fixture(scope="module")
def rs(data):
    return load_rows(data["dir"], "F0R", seed_range=RANGE)


@pytest.fixture(scope="module")
def frozen(data):
    return data["frozen"]


def load_dir(tmp_path, rows, name="d", study="F0R"):
    write_rows(tmp_path / name / "rows.jsonl", rows)
    return load_rows(tmp_path / name, study, seed_range=RANGE)


# ---------------------------------------------------------------------------------------
# loaders, completeness and the refusals of ANALYSIS_SPEC 4b
# ---------------------------------------------------------------------------------------
def test_loader_basics(tmp_path):
    rows = f0r_rows(cells=prim_cells(Ms=(3,), deltas=(2,), rhos=(0.95,)))
    cid = f0r_cell_id(3, 2, 0.95)
    tune = dict(rows[0], mode="tune", policy="sym_margin@c00")
    tune_other = dict(rows[0], mode="tune", study_family="KCOPY", seed=1)   # tune rows skipped
    dup = dict(rows[0])
    p = tmp_path / "rows.jsonl"
    with open(p, "w") as f:
        for r in [*rows, tune, tune_other, dup]:
            f.write(json.dumps(r) + "\n")
        f.write('{"partial": ')                       # trailing partial line, no newline
    rs = load_rows(tmp_path, "F0R", seed_range=RANGE)
    assert rs.missing is None and rs.partial_tail
    assert rs.skipped == {"mode": 2}
    assert rs.duplicates == 1
    assert "sym_margin@c00" not in rs.policies()
    assert "bound" in rs.policies(cid)                # bound rows are kept like any policy
    assert rs.seeds(cid, "bound") == SEEDS
    assert rs.sha256 == hashlib.sha256(p.read_bytes()).hexdigest()


def test_loader_refusals(tmp_path):
    good = f0r_rows(cells=prim_cells(Ms=(3,), deltas=(2,), rhos=(0.95,)))[0]

    def refuse(rows, match, **kw):
        p = write_rows(tmp_path / "x" / "rows.jsonl", rows)
        with pytest.raises(AnalysisError, match=match):
            load_rows(p, "F0R", seed_range=kw.get("seed_range", RANGE))

    refuse([{k: v for k, v in good.items() if k != "mode"}], "lacks 'mode'")
    refuse([{k: v for k, v in good.items() if k != "study_family"}], "lacks 'study_family'")
    refuse([{k: v for k, v in good.items() if k != "seed"}], "lacks 'seed'")
    refuse([dict(good, study_family="SCALE")], "study_family 'SCALE', expected 'F0R'")
    refuse([dict(good, seed=HI + 1)], "outside the F0R range 60000..60049")
    refuse([good], "outside the F0R range", seed_range=(HI + 1, HI + 50))
    p = tmp_path / "c" / "rows.jsonl"
    p.parent.mkdir()
    p.write_text(json.dumps(good) + "\nnot json\n")
    with pytest.raises(AnalysisError, match="corrupt row at line 2"):
        load_rows(p, "F0R", seed_range=RANGE)


def test_missing_input_refused_by_require(tmp_path):
    rs = load_rows(tmp_path / "nope", "SCALE", seed_range=RANGE)
    assert rs.missing and rs.cells() == [] and rs.sha256 is None
    with pytest.raises(AnalysisError, match="SCALE input missing"):
        rs.require(["c"], ["p"])
    assert load_rows(None, "F0R", seed_range=RANGE).missing


def test_require_reports_missing_seeds_policies_and_cells(rs):
    cid = f0r_cell_id(3, 2, 0.95)
    rs.require([cid], an.OBLIVIOUS)                   # complete: no error
    with pytest.raises(AnalysisError, match="no_such_policy"):
        rs.require([cid], ["no_such_policy"])
    with pytest.raises(AnalysisError, match="KCOPY"):
        rs.require(["KCOPY_pooled_q0.4_c8_M3_dA2_db0"], ["pop_mpc"])


def test_kind_and_privilege_checks(tmp_path):
    cells = prim_cells(Ms=(3,), deltas=(2,), rhos=(0.95,))
    cid = cells[0].cell_id
    rows = f0r_rows(cells=cells)
    load_dir(tmp_path, rows).check_kinds([cid], an.F0R_POLICIES)       # passes
    bad_kind = [dict(r, kind="per_participant") if r["policy"] == "ce_llf" else r for r in rows]
    with pytest.raises(AnalysisError, match="ce_llf: row kind .*expected 'oblivious'"):
        load_dir(tmp_path, bad_kind, "k").check_kinds([cid], an.F0R_POLICIES)
    priv = [dict(r, privileged=True) if r["policy"] == "pop_mpc" else r for r in rows]
    with pytest.raises(AnalysisError, match="privileged row in a non-reference set"):
        load_dir(tmp_path, priv, "p").check_kinds([cid], an.F0R_POLICIES)
    nopriv = [{k: v for k, v in r.items() if k != "privileged"} if r["policy"] == "persistence"
              else r for r in rows]
    with pytest.raises(AnalysisError, match="persistence"):
        load_dir(tmp_path, nopriv, "n").check_kinds([cid], an.F0R_POLICIES)
    # E1 itself refuses a privileged O member
    full = f0r_rows()
    full = [dict(r, privileged=True) if r["policy"] == "pop_mpc" else r for r in full]
    fz = an.load_frozen_file(write_frozen(tmp_path / "f.json", full))
    with pytest.raises(AnalysisError, match="privileged row in a non-reference set"):
        e1_analysis(load_dir(tmp_path, full, "e"), Bootstrap(2000), 3, 0.95, frozen=fz)


# ---------------------------------------------------------------------------------------
# bootstrap
# ---------------------------------------------------------------------------------------
def test_bootstrap_reproducible_and_joint():
    rng = np.random.default_rng(5)
    a, b = rng.normal(1.0, 1.0, NS), rng.normal(0.4, 1.0, NS)
    s1 = Bootstrap().run({"a": a, "b": b}, {"d": lambda m: m["a"] - m["b"]})["d"]
    s2 = Bootstrap().run({"a": a, "b": b}, {"d": lambda m: m["a"] - m["b"]})["d"]
    assert s1 == s2                                   # fixed rng: identical numbers
    s3 = Bootstrap(seed=1).run({"a": a, "b": b}, {"d": lambda m: m["a"] - m["b"]})["d"]
    assert s3 != s1
    # joint resampling: the interval of a - b equals the interval of the paired differences
    alone = Bootstrap().mean_ci(a - b)
    assert math.isclose(s1.lo, alone.lo, abs_tol=1e-12)
    assert math.isclose(s1.hi, alone.hi, abs_tol=1e-12)
    assert math.isclose(s1.value, float((a - b).mean()), abs_tol=1e-12)
    bt = Bootstrap()
    assert bt.n_boot == 10_000 and bt.counts(NS).shape == (10_000, NS)
    assert (bt.counts(NS).sum(axis=1) == NS).all()
    assert s1.lo < s1.value < s1.hi


def test_bootstrap_small_samples():
    st = Bootstrap().mean_ci(np.array([1.0]))
    assert st.value == 1.0 and math.isnan(st.lo) and math.isnan(st.hi)
    c = Bootstrap().mean_ci(np.full(10, 2.0))
    assert (c.value, c.lo, c.hi) == (2.0, 2.0, 2.0)


# ---------------------------------------------------------------------------------------
# reading labels
# ---------------------------------------------------------------------------------------
@pytest.mark.parametrize("lo,hi,label", [
    (0.5000001, 2.0, "detected above the practical threshold"),
    (0.51, 0.52, "detected above the practical threshold"),
    (0.5, 2.0, "detected, size uncertain against the threshold"),      # lo == 0.5: contains 0.5
    (0.2, 0.9, "detected, size uncertain against the threshold"),
    (0.2, 0.5, "detected, size uncertain against the threshold"),      # hi == 0.5: contains 0.5
    (0.0001, 0.4999, "detected, below the practical threshold"),
    (0.2, 0.4, "detected, below the practical threshold"),
    (0.0, 0.3, "not detected at this size"),                           # lo == 0 includes 0
    (-0.1, 0.3, "not detected at this size"),
    (-0.1, 2.0, "not detected at this size"),
    (-0.5, 0.0, "not detected at this size"),                          # hi == 0 includes 0
    (-0.5, -0.1, "reversed: interval wholly below 0"),
    (math.nan, 0.3, "interval undefined"),
])
def test_reading_labels_at_boundaries(lo, hi, label):
    assert reading_label(lo, hi) == label


# ---------------------------------------------------------------------------------------
# E1
# ---------------------------------------------------------------------------------------
def test_e1_recovers_planted_effect(rs, frozen, boot):
    e1 = e1_analysis(rs, boot, 3, 0.95, frozen=frozen)
    assert e1["used"] == [2, 4, 0, 1] and len(e1["seeds"]) == NS
    c = e1["contrast"]
    assert math.isclose(c.value, 1.0, abs_tol=1e-9)
    assert c.lo <= 1.0 <= c.hi and c.hi > c.lo        # noise gives a non-degenerate interval
    assert e1["label"] == "detected above the practical threshold"
    for d in (2, 4):
        g = e1["gaps"][d]
        assert math.isclose(g.value, 1.0, abs_tol=1e-9) and g.lo <= 1.0 <= g.hi and g.lo > 0
    for d in (0, 1):
        g = e1["gaps"][d]
        assert math.isclose(g.value, 0.0, abs_tol=1e-9) and g.lo <= 0.0 <= g.hi
    for M, rho in ((0, 0.95), (0, 1.15), (3, 1.15)):
        e = e1_analysis(rs, boot, M, rho, frozen=frozen)
        assert math.isclose(e["contrast"].value, 1.0, abs_tol=1e-9)
        assert e["contrast"].lo <= 1.0 <= e["contrast"].hi


def test_e1_best_oblivious_is_the_frozen_choice_not_the_development_minimum(rs, data, boot,
                                                                            tmp_path):
    cid = {d: f0r_cell_id(3, d, 0.95) for d in (0, 1, 2, 4)}
    # frozen file: persistence is best on the tuning seeds at delta 4 only; the development
    # rows still make sym_margin the cheapest at delta 4, and E1 follows the frozen choice
    fz = write_frozen(tmp_path / "fz.json", data["rows"],
                      override={("persistence", cid[4]): 0.0})
    e1 = e1_analysis(rs, boot, 3, 0.95, frozen=an.load_frozen_file(fz))
    assert {d: e1["best"][d]["policy"] for d in e1["used"]} == {
        2: "sym_margin", 4: "persistence", 0: "sym_margin", 1: "sym_margin"}
    # persistence is 0.4 above sym_margin in the development rows, so the delta-4 gap is 1.4
    assert math.isclose(e1["gaps"][4].value, 1.4, abs_tol=1e-9)
    assert e1["best"][4]["means"]["sym_margin"] < e1["best"][4]["means"]["persistence"]


def test_frozen_best_rules():
    ce = "c"
    fz = {"sym_margin": {ce: {"mean_R_avoid_kwh_per100": 5.0}},
          "persistence": {ce: {"mean_R_avoid_kwh_per100": 5.0}},        # tie: earlier in O wins
          "pop_mpc": {ce: {"mean_R_avoid_kwh_per100": 5.0 + 1e-12}},   # tie to 9 digits
          "floor": {ce: {"mean_R_avoid_kwh_per100": 1.0}},
          "oracle_mpc": {ce: {"mean_R_avoid_kwh_per100": 0.0}}, "_meta": {}}
    assert frozen_best(fz, ce)["best"] == "sym_margin"
    assert frozen_best(fz, ce, include_floor=True)["best"] == "floor"
    # ce_llf, ce_edf, pes_llf are not frozen families; reference/candidate are never candidates
    assert set(frozen_best(fz, ce)["objectives"]) == {"sym_margin", "persistence", "pop_mpc"}
    with pytest.raises(AnalysisError, match="no mean_R_avoid_kwh_per100 for sym_margin on zz"):
        frozen_best(fz, "zz")
    with pytest.raises(AnalysisError, match="no oblivious family"):
        frozen_best({"_meta": {}}, ce)


def test_frozen_file_required(tmp_path, rs, boot):
    with pytest.raises(AnalysisError, match="frozen tuning file is required"):
        an.load_frozen_file(tmp_path / "absent.json")
    with pytest.raises(AnalysisError, match="frozen tuning file is required"):
        an.load_frozen_file(None)
    p = tmp_path / "f.json"
    p.write_text(json.dumps({"_meta": {"seeds": [1, 2]}}))
    with pytest.raises(AnalysisError, match="not frozen on the tuning seeds"):
        an.load_frozen_file(p)
    with pytest.raises(AnalysisError, match="needs the frozen tuning file"):
        e1_analysis(rs, boot, 3, 0.95)
    # and the CLI writes nothing
    out = tmp_path / "pn.json"
    assert an.main(["--all", "--frozen", str(tmp_path / "absent.json"), "--out", str(out)]) == 2
    assert not out.exists()


def test_e1_refuses_when_an_oblivious_member_misses_a_seed(tmp_path, boot):
    """The review's probe: probe_first lacks seeds at low delay; dropping it inflated E1."""
    low_cells = {f0r_cell_id(3, d, 0.95) for d in LOW}
    rows = f0r_rows(gain_high=0.0, drop=lambda r: (r["policy"] == "probe_first"
                                                   and r["cell_id"] in low_cells
                                                   and r["seed"] >= 60040))
    rs = load_dir(tmp_path, rows)
    fz = an.load_frozen_file(write_frozen(tmp_path / "fz.json", rows))
    with pytest.raises(AnalysisError, match="probe_first .*10 seeds missing"):
        e1_analysis(rs, boot, 3, 0.95, frozen=fz)
    with pytest.raises(AnalysisError, match="probe_first"):
        e1_analysis(rs, boot, 3, 0.95, selection="min_e1")


def test_e1_refuses_missing_delay_cell_or_candidate_seed(tmp_path, boot):
    rows = f0r_rows(deltas=(0, 1, 2))                 # no delta = 4 cells
    rs = load_dir(tmp_path, rows)
    fz = an.load_frozen_file(write_frozen(tmp_path / "fz.json", rows))
    with pytest.raises(AnalysisError, match="dA4"):
        e1_analysis(rs, boot, 3, 0.95, frozen=fz)
    rows = f0r_rows(drop=lambda r: r["policy"] == "guarded_mpc_e1" and r["seed"] == 60049)
    rs = load_dir(tmp_path, rows, "c")
    with pytest.raises(AnalysisError, match="guarded_mpc_e1 .*1 seeds missing"):
        e1_analysis(rs, boot, 3, 0.95, frozen=an.load_frozen_file(
            write_frozen(tmp_path / "fz2.json", rows)))


def test_e1_floor_excluded_primary_included_sensitivity(rs, frozen, boot):
    prim = e1_analysis(rs, boot, 3, 0.95, frozen=frozen)
    sens = e1_analysis(rs, boot, 3, 0.95, frozen=frozen, include_floor=True)
    assert all(prim["best"][d]["policy"] != "floor" for d in prim["used"])
    assert all(sens["best"][d]["policy"] == "floor" for d in sens["used"])
    # floor sits 0.2 below sym_margin at low delay and 0.5 below at high delay
    for d in (0, 1):
        assert math.isclose(sens["gaps"][d].value, -0.2, abs_tol=1e-9)
    for d in (2, 4):
        assert math.isclose(sens["gaps"][d].value, 0.5, abs_tol=1e-9)
    assert math.isclose(sens["contrast"].value, 0.7, abs_tol=1e-9)    # 0.7 not 1.0
    assert math.isclose(prim["contrast"].value, 1.0, abs_tol=1e-9)
    assert sens["include_floor"] and not prim["include_floor"]


def test_e1_oracle_share(rs, frozen, boot):
    e1 = e1_analysis(rs, boot, 3, 0.95, frozen=frozen)
    assert math.isclose(e1["oracle_contrast"].value, 2.0, abs_tol=1e-9)
    assert e1["share_defined"]
    assert math.isclose(e1["share"].value, 0.5, abs_tol=1e-9)
    assert e1["share"].lo <= 0.5 <= e1["share"].hi and e1["share"].hi > e1["share"].lo
    for d in (2, 4):
        assert math.isclose(e1["oracle_gaps"][d].value, 2.0, abs_tol=1e-9)


def test_e1_oracle_share_undefined_when_denominator_includes_zero(tmp_path, boot):
    rows = f0r_rows(oracle_gain_high=0.0)
    e1 = e1_analysis(load_dir(tmp_path, rows), boot, 3, 0.95,
                     frozen=an.load_frozen_file(write_frozen(tmp_path / "f.json", rows)))
    assert not e1["share_defined"]
    assert math.isnan(e1["share"].lo) and math.isnan(e1["share"].hi)


def test_e1_not_detected_when_no_effect(tmp_path, boot):
    rows = f0r_rows(gain_high=0.0)
    e1 = e1_analysis(load_dir(tmp_path, rows), boot, 3, 0.95,
                     frozen=an.load_frozen_file(write_frozen(tmp_path / "f.json", rows)))
    assert e1["label"] == "not detected at this size"
    assert e1["contrast"].lo <= 0.0 <= e1["contrast"].hi


def test_e1_labels_follow_the_effect_size(tmp_path, boot):
    for gain, label in ((0.3, "detected, below the practical threshold"),
                        (1.5, "detected above the practical threshold")):
        rows = f0r_rows(gain_high=gain)
        e1 = e1_analysis(load_dir(tmp_path, rows, f"g{gain}"), boot, 3, 0.95,
                         frozen=an.load_frozen_file(write_frozen(tmp_path / f"f{gain}.json", rows)))
        assert e1["label"] == label, (gain, e1["contrast"])


def probe_rows(rng_seed=11, sd=1.5, bias_high=1.5):
    """Review probe: the candidate is no better than the best O (true E1 = 0). At low delay
    the ten O members are tied; at high delay sym_margin alone is the best."""
    rng = np.random.default_rng(rng_seed)
    rows = []
    for d in (0, 1, 2, 4):
        cell = Cell(family="F0R", M=3, delta_A=d, delta_b=0, rho=0.95, r=0.3)
        cid, b = cell.cell_id, 5.0
        for p in an.OBLIVIOUS:
            true = b + (0.0 if (d in LOW or p == "sym_margin") else bias_high)
            rows += emit("F0R", p, cid, metrics(true + rng.normal(0, sd, NS), 1.0, 0.8))
        for p in ("guarded_mpc_e1", "oracle_mpc"):
            rows += emit("F0R", p, cid, metrics(b + rng.normal(0, sd, NS), 1.0, 0.8))
    return rows


def test_selection_bias_probe_primary_rule_gives_zero(tmp_path, boot):
    rows = probe_rows()
    rs = load_dir(tmp_path, rows)
    cells = {r["cell_id"] for r in rows}      # tuning seeds are independent of these rows:
    fz = an.load_frozen_file(write_frozen(      # sym_margin is the best on them everywhere
        tmp_path / "fz.json", rows,
        override={(p, c): (4.99 if p == "sym_margin" else 5.5)
                  for p in an.OBLIVIOUS if p in TUNABLE for c in cells}))
    e1 = e1_analysis(rs, boot, 3, 0.95, frozen=fz)
    assert all(e1["best"][d]["policy"] == "sym_margin" for d in e1["used"])
    assert e1["contrast"].lo <= 0.0 <= e1["contrast"].hi, e1["contrast"]
    assert abs(e1["contrast"].value) < 0.5
    assert e1["label"] == "not detected at this size"
    # the minimum-E1 sensitivity is a lower reading than the primary
    sens = e1_analysis(rs, boot, 3, 0.95, selection="min_e1")
    assert sens["contrast"].value <= e1["contrast"].value + 1e-12
    assert len({sens["best"][d]["policy"] for d in sens["used"]}) == 1
    assert sens["selection"] == "min_e1"


def test_selection_on_development_seeds_is_biased_and_the_frozen_rule_is_not(tmp_path):
    """Over 40 replicates of the probe the frozen rule averages 0, selecting each cell's best
    O on the development seeds averages about +0.3 (the minimum over ten tied members)."""
    small = Bootstrap(n_boot=200)
    prim, dev = [], []
    for rep in range(40):
        rows = probe_rows(rng_seed=100 + rep)
        rs = load_dir(tmp_path, rows, f"r{rep}")
        cells = {r["cell_id"] for r in rows}
        fz = an.load_frozen_file(write_frozen(
            tmp_path / f"fz{rep}.json", rows,
            override={(p, c): (4.99 if p == "sym_margin" else 5.5)
                      for p in an.OBLIVIOUS if p in TUNABLE for c in cells}))
        prim.append(e1_analysis(rs, small, 3, 0.95, frozen=fz)["contrast"].value)
        gaps = {}
        for d in (0, 1, 2, 4):
            cid = f0r_cell_id(3, d, 0.95)
            means = {p: rs.vec(cid, p, an.R_KEY, SEEDS).mean() for p in an.OBLIVIOUS}
            best = min(means, key=means.get)
            gaps[d] = (rs.vec(cid, best, an.R_KEY, SEEDS)
                       - rs.vec(cid, "guarded_mpc_e1", an.R_KEY, SEEDS))
        dev.append(float(((gaps[2] + gaps[4]) / 2 - (gaps[0] + gaps[1]) / 2).mean()))
    assert abs(np.mean(prim)) < 0.15, np.mean(prim)
    assert np.mean(dev) > 0.2, np.mean(dev)
    assert np.mean(dev) - np.mean(prim) > 0.15


def test_min_e1_sensitivity_picks_the_single_minimizing_member(rs, boot):
    sens = e1_analysis(rs, boot, 3, 0.95, selection="min_e1")
    scores = sens["best"][2]["min_e1_scores"]
    pick = sens["best"][2]["policy"]
    assert pick == min(an.OBLIVIOUS, key=lambda p: (scores[p], an.OBLIVIOUS.index(p)))
    # the planted data make every member's E1 equal 1.0 minus offset differences cancel
    assert math.isclose(sens["contrast"].value, scores[pick], abs_tol=1e-9)
    with pytest.raises(AnalysisError, match="excludes the floor"):
        e1_analysis(rs, boot, 3, 0.95, selection="min_e1", include_floor=True)
    with pytest.raises(AnalysisError, match="unknown selection"):
        e1_analysis(rs, boot, 3, 0.95, selection="nope")


# ---------------------------------------------------------------------------------------
# E2
# ---------------------------------------------------------------------------------------
def test_e2_supported_when_both_readings_agree(rs, frozen, boot):
    e1 = e1_analysis(rs, boot, 3, 0.95, frozen=frozen)
    e2 = e2_analysis(rs, boot, e1)
    for d in (2, 4):
        pack = e2["cells"][d]
        a, b = pack["readings"]["A"], pack["readings"]["B"]
        assert math.isclose(a["gain_uncorr"].value, 0.9, abs_tol=1e-9)
        assert math.isclose(a["gain_corr"].value, 0.1, abs_tol=1e-9)
        assert math.isclose(b["gain_uncorr"].value, 0.7, abs_tol=1e-9)
        assert math.isclose(b["gain_corr"].value, 0.3, abs_tol=1e-9)
        for r in (a, b):                              # the two parts sum to the E1 gap
            assert math.isclose(r["gain_uncorr"].value + r["gain_corr"].value,
                                e1["gaps"][d].value, abs_tol=1e-9)
        assert a["holds"] and b["holds"] and pack["supported"]
    for d in (0, 1):                                  # no gain at low delay: nothing to attribute
        assert not e2["cells"][d]["supported"]
    c = e2["contrast"]
    assert c["supported"]
    assert math.isclose(c["readings"]["A"]["gain_uncorr"].value, 0.9, abs_tol=1e-9)
    assert math.isclose(c["readings"]["B"]["gain_corr"].value, 0.3, abs_tol=1e-9)


@pytest.mark.parametrize("gu,holds_a,holds_b,supported", [
    ((0.9, 0.7), True, True, True),
    ((0.9, 0.4), True, False, False),     # reading B puts 0.6 of the gain in R_corr
    ((0.4, 0.9), False, True, False),     # reading A puts 0.6 of the gain in R_corr
    ((0.5, 0.5), False, False, False),    # gains equal: diff is 0, not wholly above 0
    ((0.0, 0.0), False, False, False),    # nothing in R_uncorr
    ((0.6, 0.6), True, True, True),       # clearly more than half under both readings
    ((0.51, 0.51), False, False, False),  # 0.02 ahead of R_corr: inside the noise
])
def test_e2_supported_flag_logic(tmp_path, boot, gu, holds_a, holds_b, supported):
    rows = f0r_rows(gu=gu)
    rs = load_dir(tmp_path, rows)
    e1 = e1_analysis(rs, boot, 3, 0.95, frozen=an.load_frozen_file(
        write_frozen(tmp_path / "f.json", rows)))
    e2 = e2_analysis(rs, boot, e1)
    pack = e2["cells"][2]
    assert pack["readings"]["A"]["holds"] is holds_a
    assert pack["readings"]["B"]["holds"] is holds_b
    assert pack["supported"] is supported


# ---------------------------------------------------------------------------------------
# E3
# ---------------------------------------------------------------------------------------
K = 8


def kcopy_cells():
    cells = []
    for c in (0, 4, 8, 12, 16):
        for M in (0, 3):
            cells.append(Cell(family="KCOPY", M=M, delta_A=2, delta_b=0, q=0.4, c=float(c),
                              cap_mode="pooled"))
    cells.append(Cell(family="KCOPY", M=3, delta_A=2, delta_b=0, q=0.4, c=8.0, cap_mode="per_copy"))
    cells.append(Cell(family="KCOPY", M=1, delta_A=2, delta_b=0, q=0.14, c=8.0, cap_mode="pooled"))
    return cells


def kcopy_rows(cells, e1_shift=None, oracle_shift=None, pop_shift=None, skip=()):
    from papere import prop_enum as pe
    rows = []
    for cell in cells:
        if cell.cell_id in skip:
            continue
        q = Fraction(str(cell.q))
        c = int(cell.c)
        pop = float(pe.closed_oblivious(K, q, c))
        gap = float(pe.closed_gap(K, q, c))
        shift = (pop_shift or {}).get(cell.cell_id, 0.0)
        pop_v = pop + shift + wave(2, 0.5)
        orc_v = pop_v - gap + wave(3, 0.4)
        base = lambda v: {"R_abs_u": v, "R_avoid_u": v, "N": np.full(NS, 24.0)}
        rows += emit("KCOPY", "pop_mpc", cell.cell_id, base(pop_v), N=24)
        rows += emit("KCOPY", "oracle_mpc", cell.cell_id,
                     base(orc_v + (oracle_shift or {}).get(cell.cell_id, 0.0)), N=24)
        if c == K:
            ee = (pe.closed_prop3_pooled(K, q, cell.M) if cell.cap_mode == "pooled"
                  else pe.closed_prop3_per_copy(K, q, cell.M))
            e1_v = pop_v - float(Fraction(K) * q / 2 - ee) + wave(5, 0.4)
            rows += emit("KCOPY", "guarded_mpc_e1", cell.cell_id,
                         base(e1_v + (e1_shift or {}).get(cell.cell_id, 0.0)), N=24)
    return rows


def load_kc(tmp_path, rows, name="kc"):
    write_rows(tmp_path / name / "rows.jsonl", rows)
    return load_rows(tmp_path / name, "KCOPY", seed_range=RANGE, keep=an.E3_KEEP,
                     policies=an.E3_POLICIES)


def test_e3_all_points_pass(tmp_path, boot):
    cells = kcopy_cells()
    rs = load_kc(tmp_path, kcopy_rows(cells))
    e3 = e3_analysis(rs, boot, K, cells=cells)
    assert e3["by_check"] == {"R_pop": {"points": 12, "pass": 12, "pass_pointwise": 12},
                              "gap_oracle": {"points": 12, "pass": 12, "pass_pointwise": 12},
                              "gap_e1": {"points": 4, "pass": 4, "pass_pointwise": 4}}
    assert e3["n_points"] == 28 and e3["n_pass"] == 28 and e3["failures"] == []
    assert e3["all_pass"] and e3["n_pointwise_misses"] == 0
    assert e3["simultaneous_level"] == pytest.approx(1 - 0.05 / 28)
    assert e3["binomial_p_upper"] == pytest.approx(1.0)
    assert e3["expected_failures_by_chance"] == pytest.approx(1.4)
    fn = {p["function"] for p in e3["points"] if p["check"] == "gap_e1"}
    assert fn == {"K q/2 - prop_enum.closed_prop3_pooled", "K q/2 - prop_enum.closed_prop3_per_copy"}
    from papere import prop_enum as pe
    pt = next(p for p in e3["points"] if p["check"] == "gap_e1" and p["cap_mode"] == "pooled"
              and p["M"] == 3 and p["q"] == 0.4)
    assert math.isclose(pt["predicted"], float(Fraction(8) * Fraction(2, 5) / 2
                                               - pe.closed_prop3_pooled(8, Fraction(2, 5), 3)))
    pc = next(p for p in e3["points"] if p["cap_mode"] == "per_copy" and p["check"] == "gap_e1")
    assert math.isclose(pc["predicted"], 8 * 0.2 * (1 - 0.6 ** 3))
    assert math.isclose(pc["predicted"], 1.2544)
    z = [p for p in e3["points"] if p["check"] == "gap_oracle" and p["c"] in (0, 16)]
    assert z and all(p["predicted"] == 0 and p["pass"] for p in z)
    m0 = next(p for p in e3["points"] if p["check"] == "gap_e1" and p["M"] == 0)
    assert abs(m0["predicted"]) < 1e-12               # M = 0: Proposition 3 predicts no gain
    # simultaneous intervals are wider than the pointwise ones
    assert all(p["simultaneous_hi"] - p["simultaneous_lo"] >= p["measured"].hi - p["measured"].lo
               for p in e3["points"])


def test_e3_planted_mismatch_fails_only_that_point(tmp_path, boot):
    cells = kcopy_cells()
    target = next(c for c in cells if c.cap_mode == "pooled" and c.M == 3 and c.c == 8.0
                  and c.q == 0.4).cell_id
    other = next(c for c in cells if c.cap_mode == "pooled" and c.M == 0 and c.c == 12.0).cell_id
    rs = load_kc(tmp_path, kcopy_rows(cells, e1_shift={target: 1.5}, oracle_shift={other: -2.0}))
    e3 = e3_analysis(rs, boot, K, cells=cells)
    assert not e3["all_pass"] and e3["n_fail"] == 2 and e3["n_pass"] == e3["n_points"] - 2
    assert {(f["check"], f["cell_id"]) for f in e3["failures"]} == {
        ("gap_e1", target), ("gap_oracle", other)}
    f = next(f for f in e3["failures"] if f["check"] == "gap_e1")
    assert not f["measured"].contains(f["predicted"])
    assert math.isclose(f["measured"].value, f["predicted"] - 1.5, abs_tol=1e-9)
    # a miss that large is also a pointwise miss, and the binomial test sees 2 of 28
    assert {(f["check"], f["cell_id"]) for f in e3["pointwise_misses"]} >= {
        ("gap_e1", target), ("gap_oracle", other)}
    assert 0 < e3["binomial_p_upper"] < 0.5


def test_e3_simultaneous_rule_tolerates_a_pointwise_miss_only(tmp_path, boot):
    """A deviation of 2.3 standard errors: outside its pointwise 95% interval, inside the
    Bonferroni interval, so the primary rule passes and the miss is reported."""
    cells = kcopy_cells()
    target = next(c for c in cells if c.cap_mode == "pooled" and c.M == 0 and c.c == 12.0).cell_id
    se = float(np.std(wave(3, 0.4), ddof=1)) / math.sqrt(NS)         # se of the oracle gap
    rs = load_kc(tmp_path, kcopy_rows(cells, oracle_shift={target: -2.3 * se}))
    e3 = e3_analysis(rs, boot, K, cells=cells)
    assert e3["all_pass"] and e3["n_fail"] == 0
    assert [(p["check"], p["cell_id"]) for p in e3["pointwise_misses"]] == [
        ("gap_oracle", target)]
    assert e3["n_pointwise_misses"] == 1
    assert e3["binomial_p_upper"] == pytest.approx(1 - 0.95 ** 28)   # P(X >= 1)


def test_e3_pop_level_mismatch(tmp_path, boot):
    cells = kcopy_cells()
    target = cells[3].cell_id
    rs = load_kc(tmp_path, kcopy_rows(cells, pop_shift={target: 0.7}))
    e3 = e3_analysis(rs, boot, K, cells=cells)
    assert ("R_pop", target) in {(f["check"], f["cell_id"]) for f in e3["failures"]}


def test_e3_refuses_missing_cells_or_policies(tmp_path, boot):
    cells = kcopy_cells()
    rs = load_kc(tmp_path, kcopy_rows(cells, skip=(cells[0].cell_id,)))
    with pytest.raises(AnalysisError, match=cells[0].cell_id):
        e3_analysis(rs, boot, K, cells=cells)
    rows = [r for r in kcopy_rows(cells) if r["policy"] != "guarded_mpc_e1"]
    with pytest.raises(AnalysisError, match="guarded_mpc_e1"):
        e3_analysis(load_kc(tmp_path, rows, "kc2"), boot, K, cells=cells)


# ---------------------------------------------------------------------------------------
# G2
# ---------------------------------------------------------------------------------------
def g2_rows(cand_gain, pop_gain, pers_gain, sym=5.0, deltas=(0, 1, 2, 4)):
    """Pilot rows at M = 3, rho = 0.95; delay 2 and 4 are the high-delay cells."""
    rows = []
    for d in deltas:
        cid = f0r_cell_id(3, d, 0.95)
        hi = d in HIGH
        g = (lambda x: x) if hi else (lambda x: 0.0)
        shared = wave(1, 0.3)
        vals = {"sym_margin": sym, "pop_mpc": sym - g(pop_gain), "persistence": sym - g(pers_gain),
                "ce_llf": sym + 0.5, "ce_edf": sym + 0.5, "pes_llf": sym + 0.5,
                "uncorr_pes": sym + 0.5, "probe_first": sym + 0.5, "mpc_ce": sym + 0.5,
                "mpc_pes": sym + 0.5, "guarded_mpc_e1": sym - g(cand_gain),
                "oracle_mpc": sym - g(cand_gain) - 0.1}
        for p, v in vals.items():
            if not hi and p in ("pop_mpc", "persistence"):
                v = sym + 0.2                           # low delay: both worse than sym_margin
            if not hi and p == "guarded_mpc_e1":
                v = sym                                 # candidate equals best O at low delay
            rows += emit("F0R", p, cid, metrics(v + shared + wave(POLICY_K.get(p, 20), 0.1),
                                                1.0, 0.8))
    return rows


def run_g2(tmp_path, boot, name, *a, **kw):
    rows = g2_rows(*a, **kw)
    rs = load_dir(tmp_path, rows, name)
    return g2_analysis(rs, boot, an.load_frozen_file(write_frozen(tmp_path / f"{name}.json", rows)))


def test_g2_simple_rules_suffice(tmp_path, boot):
    g = run_g2(tmp_path, boot, "a", 1.0, 0.9, 0.5)
    assert g["decision_basis"].startswith("E1 contrast")
    assert g["e1_stat"].hi < 0.5 and g["simple_rules_suffice"]
    assert g["e1_label"] in ("detected, below the practical threshold", "not detected at this size")
    assert math.isclose(g["ratios"]["pop_mpc"].value, 0.9, abs_tol=1e-9)
    assert math.isclose(g["ratios"]["persistence"].value, 0.5, abs_tol=1e-9)
    assert g["ratios"]["pop_mpc"].lo <= 0.9 <= g["ratios"]["pop_mpc"].hi
    assert g["headline"]["pop_mpc"]["reaches_80pct_of_candidate_gain"]
    assert not g["headline"]["persistence"]["reaches_80pct_of_candidate_gain"]
    assert g["any_headline"]


def test_g2_candidate_clearly_ahead(tmp_path, boot):
    g = run_g2(tmp_path, boot, "b", 2.0, 0.3, 0.5)
    assert math.isclose(g["e1_stat"].value, 1.5, abs_tol=1e-9)   # best O persistence, gain 0.5
    assert not g["simple_rules_suffice"]
    assert g["e1_label"] == "detected above the practical threshold"
    assert not g["any_headline"]
    assert math.isclose(g["gains"]["candidate"].value, 2.0, abs_tol=1e-9)
    assert math.isclose(g["ratios"]["pop_mpc"].value, 0.15, abs_tol=1e-9)
    assert math.isclose(g["ratios"]["persistence"].value, 0.25, abs_tol=1e-9)


@pytest.mark.parametrize("pop_gain,flag", [(4.0, True), (3.9, False), (4.1, True), (5.0, True)])
def test_g2_80_percent_boundary(tmp_path, boot, pop_gain, flag):
    g = run_g2(tmp_path, boot, f"c{pop_gain}", 5.0, pop_gain, 0.0, sym=7.0)
    assert g["headline"]["pop_mpc"]["reaches_80pct_of_candidate_gain"] is flag
    assert g["any_headline"] is flag


def test_g2_candidate_without_gain_is_not_a_headline(tmp_path, boot):
    g = run_g2(tmp_path, boot, "d", -0.5, 0.2, 0.2)
    assert not g["candidate_gain_positive"]
    assert not g["any_headline"]
    assert math.isnan(g["ratios"]["pop_mpc"].lo)      # no interval for a ratio on a non-positive base


@pytest.mark.parametrize("deltas", [(2,), (2, 4), (0, 1, 2), (0, 1, 4)])
def test_g2_refuses_without_all_four_delay_cells(tmp_path, boot, deltas):
    with pytest.raises(AnalysisError, match="lack rows"):
        run_g2(tmp_path, boot, "e", 1.0, 0.9, 0.5, deltas=deltas)


def test_g2_json_and_flags(tmp_path, monkeypatch):
    monkeypatch.setitem(an.RUN_RANGES, "pilot", RANGE)
    rows = g2_rows(1.0, 0.9, 0.5)
    d = tmp_path / "pilot"
    write_rows(d / "rows.jsonl", rows)
    fz = write_frozen(tmp_path / "fz.json", rows)
    out = tmp_path / "g2.json"
    assert an.main(["--g2", str(d), "--frozen", str(fz), "--out", str(out)]) == 0
    data = json.loads(out.read_text())
    assert data["flags"]["simple_rules_suffice"] is True
    assert data["flags"]["headline_pop_mpc"] is True
    assert data["flags"]["headline_persistence"] is False
    assert data["flags"]["any_headline_80pct"] is True
    r = data["numbers"]["g2/ratio/pop_mpc"]
    assert math.isclose(r["value"], 0.9, abs_tol=1e-9) and r["ci_lo"] <= 0.9 <= r["ci_hi"]
    assert data["meta"]["inputs"]["pilot"]["sha256"] == hashlib.sha256(
        (d / "rows.jsonl").read_bytes()).hexdigest()
    assert data["meta"]["files"]["tuning_frozen"]["sha256"] == hashlib.sha256(
        fz.read_bytes()).hexdigest()
    # the pilot refuses (exit 2, nothing written) when a delay cell is absent
    short = tmp_path / "short"
    write_rows(short / "rows.jsonl", g2_rows(1.0, 0.9, 0.5, deltas=(0, 1, 2)))
    out2 = tmp_path / "g2b.json"
    assert an.main(["--g2", str(short), "--frozen", str(fz), "--out", str(out2)]) == 2
    assert not out2.exists()
    # and pilot rows outside the pilot range are refused
    monkeypatch.setitem(an.RUN_RANGES, "pilot", (HI + 1, HI + 20))
    assert an.main(["--g2", str(d), "--frozen", str(fz), "--out", str(out2)]) == 2


# ---------------------------------------------------------------------------------------
# secondary
# ---------------------------------------------------------------------------------------
def test_secondary_floor_rwdf_and_table(rs, frozen, boot):
    cid = f0r_cell_id(3, 2, 0.95)
    fl = an.floor_analysis(rs, boot, [cid], frozen)[cid]
    assert fl["best_oblivious"] == "sym_margin"
    assert math.isclose(fl["net_gain"].value, 0.5, abs_tol=1e-9)         # best O minus floor
    assert math.isclose(fl["event_shortfall"].value, 1.5, abs_tol=1e-9)  # reported beside
    rw = an.rwdf_analysis(rs, boot, [cid])[cid]
    assert math.isclose(rw["literal_minus_rwdf_e"].value, 0.3, abs_tol=1e-9)
    tbl = an.cell_policy_table(rs, boot, [cid])
    t = tbl[(cid, "guarded_mpc_e1")]["stats"]
    assert set(t) >= {"R_avoid_kwh_per100", "R_uncorr_hi_kwh_per100", "R_corr_lo_kwh_per100",
                      "violation_count_per100", "cpu_ms_mean"}
    assert (cid, "bound") in tbl
    assert math.isclose(tbl[(cid, "bound")]["stats"]["R_avoid_kwh_per100"].value, 0.0)
    assert math.isclose(t["R_uncorr_hi_kwh_per100"].value + t["R_corr_lo_kwh_per100"].value,
                        t["R_avoid_kwh_per100"].value, abs_tol=1e-9)
    g = an.gap_vs_best(rs, boot, f0r_cell_id(3, 2, 0.95, r=0.0), frozen)
    assert g["best_oblivious"] == "sym_margin" and math.isclose(g["gap"].value, 1.0, abs_tol=1e-9)


# ---------------------------------------------------------------------------------------
# the data file
# ---------------------------------------------------------------------------------------
def _no_nan(s):
    raise ValueError(f"non-finite constant {s} in JSON")


def scale_rows():
    cells = [scale_cell(c) for c in F0R_CELLS if c.delta_A in an.SCALE_DELTA_A]
    rows = f0r_rows(cells=cells, study="SCALE", N=300)
    for r in rows:
        r.update(cpu_ms_mean=12.0, cpu_ms_p95=20.0, cpu_ms_max=30.0, wall_ms=900.0)
    return rows


@pytest.fixture
def plan(monkeypatch, tmp_path, data):
    """Point the run plan at the test block and write a complete set of inputs."""
    for k in ("f0r", "kcopy", "scale", "pilot"):
        monkeypatch.setitem(an.RUN_RANGES, k, RANGE)
    kc = kcopy_cells()
    monkeypatch.setattr(an, "KCOPY_CELLS", kc)
    write_rows(tmp_path / "kc" / "rows.jsonl", kcopy_rows(kc))
    write_rows(tmp_path / "sc" / "rows.jsonl", scale_rows())
    return {"f0r": data["dir"], "kc": tmp_path / "kc", "sc": tmp_path / "sc",
            "frozen": data["frozen_path"], "tmp": tmp_path}


def run_all(plan, out, extra=()):
    return an.main(["--all", "--f0r", str(plan["f0r"]), "--kcopy", str(plan["kc"]),
                    "--scale", str(plan["sc"]), "--frozen", str(plan["frozen"]),
                    "--out", str(out), *extra])


def test_paper_numbers_json_contents(plan):
    out = plan["tmp"] / "paper_numbers.json"
    assert run_all(plan, out) == 0
    data = json.loads(out.read_text(), parse_constant=_no_nan)
    meta, nums = data["meta"], data["numbers"]
    assert meta["label"] == "development"
    assert meta["bootstrap"]["n_boot"] == 10_000 and meta["bootstrap"]["unit"] == "seed"
    assert meta["git"]["commit"] is None or len(meta["git"]["commit"]) == 40
    for key, path in (("f0r", plan["f0r"]), ("kcopy", plan["kc"]), ("scale", plan["sc"])):
        rec = meta["inputs"][key]
        assert rec["sha256"] == hashlib.sha256((path / "rows.jsonl").read_bytes()).hexdigest()
        assert rec["path"].endswith("rows.jsonl") and rec["seed_range"] == [LO, HI]
    assert meta["files"]["tuning_frozen"]["sha256"] == hashlib.sha256(
        plan["frozen"].read_bytes()).hexdigest()
    required = {"value", "ci_lo", "ci_hi", "n_seeds", "statistic", "source_file", "row_filter",
                "label"}
    for nid, rec in nums.items():
        assert required <= set(rec), nid
        assert rec["label"] == "development" and rec["source_file"].endswith("rows.jsonl")
    c = nums["e1/primary/M3_rho0.95/contrast"]
    assert math.isclose(c["value"], 1.0, abs_tol=1e-9) and c["ci_lo"] <= 1.0 <= c["ci_hi"]
    assert c["n_seeds"] == NS and c["reading"] == "detected above the practical threshold"
    assert c["best_oblivious"] == {"2": "sym_margin", "4": "sym_margin", "0": "sym_margin",
                                   "1": "sym_margin"}
    assert c["selection"].startswith("primary: best O fixed on the tuning seeds")
    assert "seeds 60000..60049 (n=50)" in c["row_filter"]
    assert math.isclose(nums["e1/primary/M3_rho0.95/oracle_share"]["value"], 0.5, abs_tol=1e-9)
    assert math.isclose(nums["e1/sensitivity_floor/M3_rho0.95/contrast"]["value"], 0.7,
                        abs_tol=1e-9)
    s = nums["e1/sensitivity_min_e1/M3_rho0.95/contrast"]
    assert s["selection"].startswith("sensitivity: the single O member that minimizes E1")
    assert s["value"] <= c["value"] + 1e-12
    assert nums["e2/M3_rho0.95/contrast/supported"]["supported"] is True
    # G2 quantities at full development size, labelled as such
    e1s = nums["g2_full/e1_stat"]
    assert math.isclose(e1s["value"], c["value"], abs_tol=1e-12) and e1s["n_seeds"] == NS
    assert e1s["g2_note"].startswith("G2 quantities at full development size (not the gate itself")
    gain_c = nums["g2_full/gain/candidate"]
    assert math.isclose(gain_c["value"], 1.0, abs_tol=1e-9)       # sym_margin - candidate at dA 2
    assert math.isclose(nums["g2_full/gain/pop_mpc"]["value"], -0.2, abs_tol=1e-9)
    assert math.isclose(nums["g2_full/gain/persistence"]["value"], -0.4, abs_tol=1e-9)
    r = nums["g2_full/ratio/pop_mpc"]
    assert math.isclose(r["value"], -0.2 / 1.0, abs_tol=1e-9) and r["ci_lo"] <= r["value"] <= r["ci_hi"]
    assert r["interval_defined"] is True
    for pol in ("pop_mpc", "persistence"):
        assert nums[f"g2_full/flag/{pol}/reaches_80pct_of_candidate_gain"]["flag"] is False
        assert nums[f"g2_full/flag/{pol}/ci_wholly_at_or_above_80pct"]["flag"] is False
    assert nums["g2_full/e1_stat"]["simple_rules_suffice"] is False
    assert nums["e3/summary/n_points"]["value"] == 28
    assert nums["e3/summary/n_fail"]["value"] == 0
    assert nums["e3/summary/n_pointwise_misses"]["value"] == 0
    pt = nums["e3/gap_e1/pooled/q0.4/c8/M3"]
    assert pt["passed"] is True and pt["predicted_by"] == "K q/2 - prop_enum.closed_prop3_pooled"
    assert pt["ci_lo"] <= pt["predicted"] <= pt["ci_hi"]
    assert pt["simultaneous_lo"] <= pt["predicted"] <= pt["simultaneous_hi"]
    assert "cell/%s/guarded_mpc_e1/R_avoid_kwh_per100" % f0r_cell_id(3, 2, 0.95) in nums
    assert f"secondary/floor/{f0r_cell_id(3, 2, 0.95)}/event_shortfall" in nums
    assert "secondary/r_sweep/r0/gap" in nums and "secondary/lag_split/gap" in nums
    assert any(k.startswith("scale/") and k.endswith("cpu_ms_mean") for k in nums)
    assert meta["warnings"] == []


def test_paper_numbers_reproducible(plan):
    outs = []
    for i in range(2):
        out = plan["tmp"] / f"o{i}.json"
        assert run_all(plan, out) == 0
        d = json.loads(out.read_text())
        d["meta"].pop("generated_utc")
        outs.append(d)
    assert outs[0] == outs[1]


def test_paper_numbers_refuse_missing_family_and_write_nothing(plan, capsys):
    out = plan["tmp"] / "pn.json"
    import shutil
    shutil.rmtree(plan["sc"])
    assert run_all(plan, out) == 2
    assert not out.exists()
    assert "SCALE input missing" in capsys.readouterr().err
    assert an.main(["--all", "--f0r", str(plan["f0r"]), "--kcopy", str(plan["kc"]),
                    "--scale", str(plan["sc"]), "--frozen", str(plan["tmp"] / "none.json"),
                    "--out", str(out)]) == 2


def test_paper_numbers_refuse_incomplete_f0r_and_wrong_seeds(plan, monkeypatch, capsys):
    out = plan["tmp"] / "pn.json"
    rows = [json.loads(l) for l in (plan["f0r"] / "rows.jsonl").read_text().splitlines()]
    cid = f0r_cell_id(1, 2, 0.95)
    short = [r for r in rows if not (r["cell_id"] == cid and r["policy"] == "pop_mpc"
                                     and r["seed"] == 60049)]
    d = plan["tmp"] / "short"
    write_rows(d / "rows.jsonl", short)
    assert an.main(["--all", "--f0r", str(d), "--kcopy", str(plan["kc"]), "--scale",
                    str(plan["sc"]), "--frozen", str(plan["frozen"]), "--out", str(out)]) == 2
    assert not out.exists() and "pop_mpc" in capsys.readouterr().err
    monkeypatch.setitem(an.RUN_RANGES, "f0r", (HI + 1, HI + 100))   # rows outside the F0R range
    assert run_all(plan, out) == 2
    assert not out.exists()


def test_strict_writes_nothing_on_warnings(plan, tmp_path_factory, capsys):
    out = plan["tmp"] / "pn.json"
    rows = (plan["f0r"] / "rows.jsonl").read_text().splitlines()
    d = plan["tmp"] / "dup"
    write_rows(d / "rows.jsonl", [json.loads(l) for l in rows] + [json.loads(rows[0])])
    args = ["--all", "--f0r", str(d), "--kcopy", str(plan["kc"]), "--scale", str(plan["sc"]),
            "--frozen", str(plan["frozen"]), "--out", str(out)]
    assert an.main(args + ["--strict"]) == 2
    assert not out.exists()
    assert "1 duplicate rows ignored" in capsys.readouterr().err
    assert an.main(args) == 0 and out.exists()                  # without --strict: a warning only


def test_no_non_finite_in_json(plan):
    d = plan["tmp"] / "zero"
    rows = f0r_rows(oracle_gain_high=0.0, extra=True)
    write_rows(d / "rows.jsonl", rows)
    fz = write_frozen(plan["tmp"] / "fz0.json", rows)
    out = plan["tmp"] / "pn.json"
    assert an.main(["--all", "--f0r", str(d), "--kcopy", str(plan["kc"]), "--scale",
                    str(plan["sc"]), "--frozen", str(fz), "--out", str(out)]) == 0
    data = json.loads(out.read_text(), parse_constant=_no_nan)
    share = data["numbers"]["e1/primary/M3_rho0.95/oracle_share"]
    assert share["ci_lo"] is None and share["ci_hi"] is None and share["interval_defined"] is False


LAYER_LABEL = ("descriptive, post hoc, added after DEV_REPORT_E; factorial pre-declared as "
               "secondary in FORMULATION_E_v2 8.2")


def test_layers_factorial(plan):
    out = plan["tmp"] / "pn.json"
    assert run_all(plan, out) == 0
    nums = json.loads(out.read_text())["numbers"]
    cell_layers = {k: v for k, v in nums.items() if k.startswith("layers/M")}
    assert len(cell_layers) == 16 * 10                # 5 terms x (R_avoid, deadline misses)
    assert all(v["layer_label"] == LAYER_LABEL and v["label"] == "development"
               for k, v in nums.items() if k.startswith("layers/"))
    assert not any("sym_margin" in v["statistic"] for k, v in nums.items()
                   if k.startswith("layers/"))
    # planted R_avoid offsets: ce_llf +0.5, mpc_ce +0.3, pop_mpc +0.2 over sym_margin;
    # candidate = best O (sym_margin, offset 0) - gain; oracle = same - oracle gain
    for d, hi in ((0, False), (1, False), (2, True), (4, True)):
        key = f"layers/M3_rho1.15/dA{d}"
        want = {"planning": 0.2, "hedging": 0.1, "targeting": 0.2 + (1.0 if hi else 0.0),
                "oracle_targeting": 0.2 + (2.0 if hi else 0.0), "total": 0.5 + (1.0 if hi else 0.0)}
        for k, v in want.items():
            r = nums[f"{key}/{k}"]
            assert math.isclose(r["value"], v, abs_tol=1e-9), (key, k)
            assert r["ci_lo"] <= r["value"] <= r["ci_hi"] and r["n_seeds"] == NS
        assert math.isclose(nums[f"{key}/planning"]["value"] + nums[f"{key}/hedging"]["value"]
                            + nums[f"{key}/targeting"]["value"], nums[f"{key}/total"]["value"],
                            abs_tol=1e-9)
        for k in want:                                # deadline misses are zero in the test rows
            assert nums[f"{key}/deadline_misses/{k}"]["value"] == 0.0
    # M sweep: share = (pop - e1) / (pop - oracle) = 1.2 / 2.2 at delta 2 (pop +0.2, gains 1, 2)
    for m in (1, 3, 5):
        key = f"layers/msweep/M{m}"
        assert math.isclose(nums[f"{key}/numerator"]["value"], 1.2, abs_tol=1e-9)
        assert math.isclose(nums[f"{key}/denominator"]["value"], 2.2, abs_tol=1e-9)
        sh = nums[f"{key}/share"]
        assert math.isclose(sh["value"], 1.2 / 2.2, abs_tol=1e-9) and sh["interval_defined"]
        assert sh["ci_lo"] <= sh["value"] <= sh["ci_hi"] and "note" not in sh
    # nothing outside layers/ changed or was added by the layers
    assert math.isclose(nums["e1/primary/M3_rho0.95/contrast"]["value"], 1.0, abs_tol=1e-9)
    assert "layer_label" not in nums["e1/primary/M3_rho0.95/contrast"]
    assert "g2_full/e1_stat" in nums and "e3/summary/n_points" in nums


def test_layers_do_not_change_other_keys(plan, monkeypatch):
    out = plan["tmp"] / "pn.json"
    assert run_all(plan, out) == 0
    full = json.loads(out.read_text())["numbers"]
    monkeypatch.setattr(an, "add_layers", lambda nums, rs, layers: None)
    out2 = plan["tmp"] / "pn2.json"
    assert run_all(plan, out2) == 0
    without = json.loads(out2.read_text())["numbers"]
    assert {k: v for k, v in full.items() if not k.startswith("layers/")} == without


def test_layer_identity_and_refusals(tmp_path, boot):
    good = {"planning": np.array([0.1, 0.2]), "hedging": np.array([0.3, 0.1]),
            "targeting": np.array([0.2, 0.2]), "total": np.array([0.6, 0.5])}
    an.check_layer_identity(good, "x")
    bad = dict(good, total=np.array([0.6, 0.5 + 1e-6]))
    with pytest.raises(AnalysisError, match="planning \\+ hedging \\+ targeting != total"):
        an.check_layer_identity(bad, "x")
    an.check_layer_identity(dict(good, total=np.array([0.6, 0.5 + 1e-10])), "x")
    rows = f0r_rows(extra=True, drop=lambda r: r["policy"] == "mpc_ce" and r["seed"] == 60049)
    with pytest.raises(AnalysisError, match="mpc_ce"):
        an.layers_analysis(load_dir(tmp_path, rows), boot)
    # the identity holds on real-shaped rows with deadline misses that differ by policy
    rows = f0r_rows(extra=True)
    for r in rows:
        if r["policy"] in ("ce_llf", "mpc_ce", "pop_mpc", "guarded_mpc_e1", "oracle_mpc"):
            r["deadline_miss_count_per100"] = {"ce_llf": 5.0, "mpc_ce": 4.0, "pop_mpc": 3.5,
                                               "guarded_mpc_e1": 2.0, "oracle_mpc": 1.0}[r["policy"]]
    lay = an.layers_analysis(load_dir(tmp_path, rows, "dm"), boot)["cells"][(3, 0.95, 2)]
    assert math.isclose(lay["deadline_misses/planning"].value, 1.0)
    assert math.isclose(lay["deadline_misses/hedging"].value, 0.5)
    assert math.isclose(lay["deadline_misses/targeting"].value, 1.5)
    assert math.isclose(lay["deadline_misses/total"].value, 3.0)
    assert math.isclose(lay["deadline_misses/oracle_targeting"].value, 2.5)


def test_msweep_share_interval_defined_and_undefined(tmp_path, boot):
    # defined: pop_mpc - oracle = 0.2 + 2.0 on average, far from 0
    rows = f0r_rows(extra=True)
    ok = an.layers_analysis(load_dir(tmp_path, rows, "u"), boot)["msweep"]
    assert all(ok[m]["interval_defined"] and math.isfinite(ok[m]["share"].lo) for m in (1, 3, 5))
    # undefined: the oracle equals pop_mpc on average (best O + 0.2 offset, gain -0.2)
    rows = f0r_rows(extra=True, oracle_gain_high=-0.2)
    lay = an.layers_analysis(load_dir(tmp_path, rows, "u2"), boot)["msweep"]
    for m in (1, 3, 5):
        r = lay[m]
        assert math.isclose(r["denominator"].value, 0.0, abs_tol=1e-9)
        assert not r["interval_defined"]
        assert math.isnan(r["share"].lo) and math.isnan(r["share"].hi)
    nums = an.Numbers()
    d = tmp_path / "f0"
    write_rows(d / "rows.jsonl", rows)
    an.add_layers(nums, load_rows(d, "F0R", seed_range=RANGE), {"cells": {}, "msweep": lay})
    sh = nums.items["layers/msweep/M3/share"]
    assert sh["interval_defined"] is False and "note" in sh and sh["layer_label"] == LAYER_LABEL
    assert math.isnan(sh["ci_lo"])
