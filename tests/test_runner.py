"""Runner tests: resumability, partial-line recovery, idempotence, worker invariance, freeze
logic, seed refusal, manifest, bound rows. Tiny injected families; no real catalog."""
import json
import math
import os
from pathlib import Path

import numpy as np
import pytest

from papere import runner
from papere.generator import F0R_CELLS, KCOPY_CELLS
from papere.policies.base import Family, PopulationParams
from papere.runner import (RowStore, RunnerError, SeedRefused, TIMING_KEYS, check_seeds,
                           freeze, iter_rows, main, row_key, run, tune_name)

PARAMS = PopulationParams(alpha=1.0, beta=2.0, q_bar_stuck=10.0, q_bar_total=50.0,
                          n_aa=90.0, n_as=2.0, n_ss=6.0, n_sa=2.0)
N_SMALL = 8
TUNE = (60000, 60001)
# Test-only open ranges (injected via ``open_ranges``).  Seed rule (docs/SEED_LEDGER.md): every
# test uses seeds 60000-60049 only, so the plumbing tests map each mode onto disjoint tuning
# seeds: the tuning range is shrunk to two seeds so the freeze tests stay fast, and the frozen
# modes of F0R / KCOPY / SCALE are re-pointed at other tuning seeds.  The real ledger numbers
# appear only in the marked refusal tests further down.
F0R_FROZEN = (60040, 60049)
KCOPY_FROZEN = (60030, 60039)
SCALE_FROZEN = (60020, 60029)
OPEN = {("F0R", "tune"): TUNE, ("F0R", "frozen"): F0R_FROZEN,
        ("KCOPY", "frozen"): KCOPY_FROZEN, ("SCALE", "frozen"): SCALE_FROZEN}
FROZEN_SEEDS = (60040, 60041)


def find_cell(M, dA, rho):
    return next(c for c in F0R_CELLS if c.M == M and c.delta_A == dA and c.rho == rho
                and c.r == 0.3 and c.delta_b == 0)


CELL_A = find_cell(0, 2, 0.95)
CELL_B = find_cell(3, 0, 1.15)
CELL_IDS = [CELL_A.cell_id, CELL_B.cell_id]


class Greedy:
    """Laxity-first greedy on confirmed debt with a cap margin; reads only the view."""

    def __init__(self, name="x", m=0, floor=False, privileged=False, record=None):
        self.name, self.m, self.floor, self.privileged = name, m, floor, privileged
        self.record = record

    def reset(self, static_view, rng, oracle=None):
        if self.record is not None:
            self.record.append(float(rng.random()))

    def floor_mask(self, static_view):
        return np.ones(static_view.N, dtype=bool) if self.floor else None

    def act(self, view):
        x = np.zeros(view.N, dtype=np.int64)
        debt = view.confirmed_debt
        # +1 kW of slack: an optimistic last-value cap can overdeliver past the realized-cap
        # bound, and the ledger then raises BoundViolation (reported to the lead)
        cap = [max(0, view.setpoint_cap(g, self.m + 1)) for g in range(view.G)]
        idx = [i for i in range(view.N) if view.active[i] and debt[i] > 0]
        idx.sort(key=lambda i: ((view.d[i] - view.t) - math.ceil(debt[i] / view.P[i]), i))
        for i in idx:
            g = int(view.group[i])
            u = int(min(view.P[i], debt[i], cap[g]))
            x[i] = u
            cap[g] -= u
        return x


def families(record=None):
    return [
        Family("CE-LLF", "oblivious", ({"m": 0},), {"m": 0},
               lambda cfg, p: Greedy(m=cfg["m"])),
        Family("Margin-LLF", "oblivious", ({"m": 0}, {"m": 1}), {"m": 0},
               lambda cfg, p: Greedy(m=cfg["m"], record=record)),
        Family("Floor-LLF", "oblivious", ({"m": 0},), {"m": 0},
               lambda cfg, p: Greedy(m=cfg["m"], floor=True)),
        Family("Oracle-ref", "reference", ({"m": 0},), {"m": 0},
               lambda cfg, p: Greedy(m=cfg["m"], privileged=True), tuned_from="Margin-LLF"),
    ]


def strip(rows):
    return sorted(({k: v for k, v in r.items() if k not in TIMING_KEYS} for r in rows),
                  key=lambda r: json.dumps(row_key(r)))


def read_rows(out):
    return list(iter_rows(Path(out) / "rows.jsonl"))


def tune(tmp, name="tune", workers=1, fams=None, **kw):
    out = tmp / name
    run("F0R", TUNE, out, mode="tune", cell_ids=CELL_IDS, workers=workers,
        families=fams or families(), params=PARAMS, params_path=tmp / "none.json",
        f0r_N=N_SMALL, open_ranges=OPEN, **kw)
    return out


def do_freeze(tmp, tune_out, name="TUNING_FROZEN.json"):
    fp = tmp / name
    freeze(tune_out, seeds=TUNE, cell_ids=CELL_IDS, families=families(), frozen_path=fp,
           params_path=tmp / "none.json", open_ranges=OPEN)
    return fp


def frozen_run(tmp, name, fp, workers=1, seeds=FROZEN_SEEDS, **kw):
    out = tmp / name
    s = run("F0R", seeds, out, mode="frozen", cell_ids=CELL_IDS, workers=workers,
            families=families(), params=PARAMS, params_path=tmp / "none.json",
            frozen_path=fp, f0r_N=N_SMALL, open_ranges=OPEN,
            **{"allow_dirty": True, **kw})
    return out, s


@pytest.fixture(scope="module")
def tuned(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("tuned")
    out = tune(tmp)
    fp = do_freeze(tmp, out)
    return tmp, out, fp


# ------------------------------------------------------------------ tune mode ---
def test_tune_runs_only_tunable_grid(tuned):
    _, out, _ = tuned
    rows = read_rows(out)
    assert len(rows) == 2 * 2 * 2          # cells x seeds x configs of the one tunable family
    assert {r["family"] for r in rows} == {"Margin-LLF"}
    assert {r["policy"] for r in rows} == {tune_name("Margin-LLF", 0), tune_name("Margin-LLF", 1)}
    assert all(r["mode"] == "tune" and r["kind"] == "oblivious" for r in rows)
    assert {r["config_index"] for r in rows} == {0, 1}
    assert all(r["config"] == {"m": r["config_index"]} for r in rows)
    assert not any(r["family"] == "bound" for r in rows)


def test_tune_configs_share_the_tiebreak_stream(tmp_path):
    # common random numbers: the stream depends on (seed, cell) only, not on the @cNN name
    rec = []
    out = tmp_path / "t"
    run("F0R", (60000, 60000), out, mode="tune", cell_ids=CELL_IDS[:1], workers=1,
        families=families(record=rec), params=PARAMS, params_path=tmp_path / "n.json",
        f0r_N=N_SMALL)
    assert len(rec) == 2 and rec[0] == rec[1]


def test_tune_refuses_other_seeds_and_families(tmp_path):
    kw = dict(families=families(), params=PARAMS, params_path=tmp_path / "n.json")
    # injected ranges: tune is open for F0R on TUNE only; frozen-mode seeds are not tuning seeds
    kw["open_ranges"] = OPEN
    with pytest.raises(SeedRefused):
        run("F0R", FROZEN_SEEDS, tmp_path / "a", mode="tune", **kw)
    with pytest.raises(SeedRefused):
        run("KCOPY", KCOPY_FROZEN, tmp_path / "b", mode="tune", **kw)
    with pytest.raises(SeedRefused):
        run("SCALE", SCALE_FROZEN, tmp_path / "c", mode="tune", **kw)
    assert not (tmp_path / "a").exists()


# ------------------------------------------------------------------ freeze ------
def fake_family(n_cfg=3):
    return Family("T", "oblivious", tuple({"m": i} for i in range(n_cfg)), {"m": 0},
                  lambda cfg, p: Greedy(m=cfg["m"]))


def write_fake(out, vals, seeds=TUNE, fam="T", n_cfg=3):
    """vals[(cell_id, idx)] = (objective, violation), same for each seed."""
    store = RowStore(out / "rows.jsonl")
    store.open()
    for (cid, idx), (obj, viol) in vals.items():
        for s in range(seeds[0], seeds[1] + 1):
            store.append({"mode": "tune", "seed": s, "cell_id": cid, "study_family": "F0R",
                          "policy": tune_name(fam, idx), "config_index": idx,
                          "config": {"m": idx}, "family": fam, "params_sha256": None,
                          "R_avoid_kwh_per100": obj, "violation_kwslot": viol})
    store.close()


def test_freeze_selection_and_tiebreaks(tmp_path):
    out = tmp_path / "f"
    out.mkdir()
    a, b, c = CELL_IDS[0], CELL_IDS[1], F0R_CELLS[0].cell_id
    vals = {
        # cell a: config 2 has the lowest objective
        (a, 0): (5.0, 0.0), (a, 1): (4.0, 9.0), (a, 2): (3.0, 9.0),
        # cell b: configs 1 and 2 tie on objective, 2 has lower violation
        (b, 0): (5.0, 0.0), (b, 1): (3.0, 2.0), (b, 2): (3.0, 1.0),
        # cell c: full tie -> lowest index
        (c, 0): (3.0, 1.0), (c, 1): (3.0, 1.0), (c, 2): (3.0, 1.0),
    }
    write_fake(out, vals)
    fp = tmp_path / "TUNING_FROZEN.json"
    res = freeze(out, seeds=TUNE, cell_ids=[a, b, c], families=[fake_family()],
                 frozen_path=fp, params_path=tmp_path / "none.json", open_ranges=OPEN)
    assert [res["T"][x]["config_index"] for x in (a, b, c)] == [2, 2, 0]
    got = json.loads(fp.read_text())
    assert got["T"][a] == {"config_index": 2, "config": {"m": 2},
                           "mean_R_avoid_kwh_per100": 3.0, "mean_violation_kwslot": 9.0,
                           "n_seeds": 2, "seeds": [60000, 60001]}
    assert got["_meta"]["seeds"] == [60000, 60001]
    # idempotent rewrite is allowed; a different selection is not overwritten silently
    freeze(out, seeds=TUNE, cell_ids=[a, b, c], families=[fake_family()], frozen_path=fp,
           params_path=tmp_path / "none.json", open_ranges=OPEN)
    vals[(a, 1)] = (1.0, 0.0)
    out2 = tmp_path / "f2"
    out2.mkdir()
    write_fake(out2, vals)
    with pytest.raises(RunnerError, match="exists and differs"):
        freeze(out2, seeds=TUNE, cell_ids=[a, b, c], families=[fake_family()],
               frozen_path=fp, params_path=tmp_path / "none.json", open_ranges=OPEN)


def test_freeze_refuses_missing_row(tmp_path):
    out = tmp_path / "f"
    out.mkdir()
    a = CELL_IDS[0]
    write_fake(out, {(a, 0): (1.0, 0.0), (a, 1): (1.0, 0.0), (a, 2): (1.0, 0.0)})
    fp = tmp_path / "TUNING_FROZEN.json"
    # one seed missing for one config
    rows = list(iter_rows(out / "rows.jsonl"))
    (out / "rows.jsonl").write_text("".join(
        json.dumps(r) + "\n" for r in rows
        if not (r["seed"] == 60001 and r["config_index"] == 2)))
    with pytest.raises(RunnerError, match="1 tuning rows missing"):
        freeze(out, seeds=TUNE, cell_ids=[a], families=[fake_family()], frozen_path=fp,
               params_path=tmp_path / "none.json", open_ranges=OPEN)
    assert not fp.exists()
    # a missing cell also counts
    with pytest.raises(RunnerError, match="missing"):
        freeze(out, seeds=TUNE, cell_ids=[a, CELL_IDS[1]], families=[fake_family()],
               frozen_path=fp, params_path=tmp_path / "none.json", open_ranges=OPEN)
    # and a seed set other than the full tuning set is refused outright
    with pytest.raises(RunnerError):
        freeze(out, seeds=(60000, 60002), cell_ids=[a], families=[fake_family()],
               frozen_path=fp, params_path=tmp_path / "none.json", open_ranges=OPEN)


def test_freeze_cli_and_real_tuning(tuned):
    _, _, fp = tuned
    d = json.loads(fp.read_text())
    assert set(d) == {"Margin-LLF", "_meta"}
    assert set(d["Margin-LLF"]) == set(CELL_IDS)
    for ent in d["Margin-LLF"].values():
        assert ent["config"] == {"m": ent["config_index"]} and ent["n_seeds"] == 2


def test_freeze_via_main(tmp_path):
    out = tmp_path / "f"
    out.mkdir()
    write_fake(out, {(CELL_IDS[0], i): (3.0 - i, 0.0) for i in range(3)})
    fp = tmp_path / "TF.json"
    rc = main(["--family", "F0R", "--freeze", "--out", str(out), "--frozen-path", str(fp),
               "--population-params", str(tmp_path / "none.json"), "--seeds", "60000-60001", "--cells", CELL_IDS[0]], families=[fake_family()],
              open_ranges=OPEN)
    assert rc == 0 and json.loads(fp.read_text())["T"][CELL_IDS[0]]["config_index"] == 2
    rc = main(["--family", "F0R", "--freeze", "--out", str(out), "--frozen-path",
               str(tmp_path / "other.json"), "--population-params",
               str(tmp_path / "none.json"), "--seeds", "60000-60001",
               "--cells", CELL_IDS[1]], families=[fake_family()], open_ranges=OPEN)
    assert rc == 2


# ------------------------------------------------------------------ frozen mode --
def test_frozen_requires_frozen_file(tmp_path):
    with pytest.raises(RunnerError, match="TUNING_FROZEN"):
        frozen_run(tmp_path, "r", tmp_path / "missing.json")
    # and the same through the CLI exit code
    rc = main(["--family", "F0R", "--seeds", "60040-60040", "--out", str(tmp_path / "o"),
               "--frozen-path", str(tmp_path / "missing.json"), "--workers", "1"],
              families=families(), params=PARAMS, f0r_N=N_SMALL, open_ranges=OPEN)
    assert rc == 2


def test_frozen_rows_bound_and_configs(tuned):
    tmp, _, fp = tuned
    out, s = frozen_run(tmp, "fr", fp)
    rows = read_rows(out)
    frozen = json.loads(fp.read_text())
    n_pairs = 2 * 2
    assert len(rows) == n_pairs * (1 + 4)       # bound + 4 families
    for seed in range(FROZEN_SEEDS[0], FROZEN_SEEDS[1] + 1):
        for cid in CELL_IDS:
            sub = {r["family"]: r for r in rows if r["seed"] == seed and r["cell_id"] == cid}
            assert set(sub) == {"bound", "CE-LLF", "Margin-LLF", "Floor-LLF", "Oracle-ref"}
            b = sub["bound"]
            assert b["kind"] == "bound" and b["policy"] == "bound" and b["mode"] == "frozen"
            assert b["R_avoid_u"] == 0 and b["privileged"] is True
            fz = frozen["Margin-LLF"][cid]
            assert sub["Margin-LLF"]["config_index"] == fz["config_index"]
            assert sub["Margin-LLF"]["config"] == fz["config"]
            assert sub["Oracle-ref"]["config_index"] == fz["config_index"]   # tuned_from
            assert sub["Oracle-ref"]["config"] == fz["config"]
            assert sub["Oracle-ref"]["privileged"] is True
            assert sub["Margin-LLF"]["privileged"] is False
            assert sub["CE-LLF"]["config_index"] == 0 and sub["CE-LLF"]["config"] == {"m": 0}
            assert sub["Floor-LLF"]["floored_count"] == N_SMALL
            for r in sub.values():
                assert r["study_family"] == "F0R" and r["R_avoid_u"] >= 0
                assert r["wall_ms"] >= 0 and "cpu_ms_total" in r and "cpu_ms_p95" in r
            # the bound is the unfloored one: same availability hash as a non-floored policy
            assert b["A_sha256"] == sub["CE-LLF"]["A_sha256"]


def test_frozen_policy_and_cell_filters(tuned):
    tmp, _, fp = tuned
    out, _ = frozen_run(tmp, "flt", fp, policies=["Oracle-ref"], seeds=(60040, 60040))
    rows = read_rows(out)
    assert {r["family"] for r in rows} == {"bound", "Oracle-ref"}
    with pytest.raises(RunnerError, match="unknown policies"):
        frozen_run(tmp, "flt2", fp, policies=["nope"])
    with pytest.raises(RunnerError, match="unknown F0R cell"):
        run("F0R", (60040, 60040), tmp / "flt3", cell_ids=["zzz"], families=families(),
            params=PARAMS, frozen_path=fp, params_path=tmp / "none.json",
            open_ranges=OPEN, allow_dirty=True)


def test_frozen_file_must_cover_cell(tuned):
    tmp, _, fp = tuned
    d = json.loads(fp.read_text())
    del d["Margin-LLF"][CELL_IDS[1]]
    bad = tmp / "partial.json"
    bad.write_text(json.dumps(d))
    with pytest.raises(RunnerError, match="no entry"):
        frozen_run(tmp, "cov", bad)
    assert not any((tmp / "cov").glob("rows.jsonl")) or not read_rows(tmp / "cov")


def test_frozen_grid_mismatch_refused(tuned):
    tmp, _, fp = tuned
    d = json.loads(fp.read_text())
    d["Margin-LLF"][CELL_IDS[0]]["config"] = {"m": 99}
    bad = tmp / "mismatch.json"
    bad.write_text(json.dumps(d))
    with pytest.raises(RunnerError, match="does not match"):
        frozen_run(tmp, "mm", bad)


def test_population_params_hash_checked(tmp_path):
    pp = tmp_path / "pp.json"
    pp.write_text(json.dumps(PARAMS.__dict__))
    out = tmp_path / "t"
    run("F0R", TUNE, out, mode="tune", cell_ids=CELL_IDS[:1], families=families(),
        params_path=pp, f0r_N=N_SMALL, open_ranges=OPEN)
    fp = tmp_path / "TF.json"
    freeze(out, seeds=TUNE, cell_ids=CELL_IDS[:1], families=families(), frozen_path=fp,
           params_path=pp, open_ranges=OPEN)
    assert json.loads(fp.read_text())["_meta"]["population_params_sha256"]
    run("F0R", (60040, 60040), tmp_path / "ok", cell_ids=CELL_IDS[:1], families=families(),
        params_path=pp, frozen_path=fp, f0r_N=N_SMALL, open_ranges=OPEN, allow_dirty=True)
    pp.write_text(json.dumps({**PARAMS.__dict__, "alpha": 7.0}))
    with pytest.raises(RunnerError, match="population parameters changed"):
        run("F0R", (60040, 60040), tmp_path / "bad", cell_ids=CELL_IDS[:1],
            families=families(), params_path=pp, frozen_path=fp, f0r_N=N_SMALL,
            open_ranges=OPEN, allow_dirty=True)


def test_params_loaded_from_file(tmp_path):
    pp = tmp_path / "pp.json"
    pp.write_text(json.dumps({"params": {**PARAMS.__dict__, "extra": 1}}))
    assert runner.load_params(pp) == PARAMS
    pp.write_text(json.dumps({"seeds": {}, "values": PARAMS.__dict__, "diagnostics": {}}))
    assert runner.load_params(pp) == PARAMS
    if runner.DEFAULT_PARAMS_PATH.exists():                             # fit.py's file
        assert runner.load_params(runner.DEFAULT_PARAMS_PATH).alpha > 0
    pp.write_text(json.dumps({"alpha": 1}))
    with pytest.raises(RunnerError, match="missing"):
        runner.load_params(pp)


def test_kcopy_uses_defaults_without_frozen_file(tmp_path):
    cid = next(c.cell_id for c in KCOPY_CELLS if c.cap_mode == "pooled" and c.M == 0
               and c.c == 8.0 and c.q == 0.4)
    out = tmp_path / "k"
    run("KCOPY", (60030, 60031), out, cell_ids=[cid], families=families(), params=PARAMS,
        frozen_path=tmp_path / "does_not_exist.json", params_path=tmp_path / "n.json",
        open_ranges=OPEN, allow_dirty=True)
    rows = read_rows(out)
    assert len(rows) == 2 * 5
    for r in rows:
        if r["family"] in ("bound",):
            continue
        assert r["config"] == {"m": 0} and r["study_family"] == "KCOPY"
    with pytest.raises(SeedRefused):
        run("KCOPY", (60040, 60040), tmp_path / "k2", cell_ids=[cid], families=families(),
            params=PARAMS, open_ranges=OPEN)         # an F0R frozen seed is not a KCOPY seed


def test_scale_uses_matching_f0r_frozen_config(tuned):
    tmp, _, fp = tuned
    out = tmp / "scale"
    cids = [runner.scale_cell(CELL_A).cell_id, runner.scale_cell(CELL_B).cell_id]
    run("SCALE", (60020, 60020), out, cell_ids=cids, families=families(), params=PARAMS,
        frozen_path=fp, params_path=tmp / "none.json", scale_N=12, open_ranges=OPEN,
        allow_dirty=True)
    frozen = json.loads(fp.read_text())
    rows = read_rows(out)
    assert {r["cell_id"] for r in rows} == set(cids)
    for r in rows:
        assert r["N"] == 12 and r["study_family"] == "SCALE"
        if r["family"] == "Margin-LLF":
            f0r_id = r["cell_id"].replace("SCALE", "F0R", 1)
            assert r["config_index"] == frozen["Margin-LLF"][f0r_id]["config_index"]
    assert {c.delta_A for c in runner.study_cells("SCALE")} == {0, 2}
    with pytest.raises(RunnerError, match="TUNING_FROZEN"):
        run("SCALE", (60020, 60020), tmp / "scale2", cell_ids=cids, families=families(),
            params=PARAMS, frozen_path=tmp / "nope.json", params_path=tmp / "none.json",
            open_ranges=OPEN, allow_dirty=True)


# ------------------------------------------------------------------ resume etc. --
class Boom(Exception):
    pass


def killer(k):
    n = {"rows": 0}

    def hook(row):
        n["rows"] += 1
        if n["rows"] == k:
            raise Boom

    return hook


def test_resume_after_exception_matches_clean_run(tuned):
    tmp, _, fp = tuned
    clean, _ = frozen_run(tmp, "clean", fp)
    for k in (1, 3, 7):
        out = tmp / f"killed{k}"
        with pytest.raises(Boom):
            frozen_run(tmp, f"killed{k}", fp, after_row=killer(k))
        assert len(read_rows(out)) == k
        m = json.loads((out / "manifest.json").read_text())
        assert m["invocations"][-1]["status"] == "failed"
        _, s = frozen_run(tmp, f"killed{k}", fp)
        rows = read_rows(out)
        keys = [row_key(r) for r in rows]
        assert len(keys) == len(set(keys)) == len(read_rows(clean))
        assert strip(rows) == strip(read_rows(clean))
        assert s["rows_written"] == len(rows) - k and s["rows_skipped"] == k
        assert [i["status"] for i in json.loads((out / "manifest.json").read_text())
                ["invocations"]] == ["failed", "complete"]


def test_truncated_trailing_line_recovered(tuned, capsys):
    tmp, _, fp = tuned
    clean, _ = frozen_run(tmp, "clean2", fp)
    out = tmp / "trunc"
    frozen_run(tmp, "trunc", fp, after_row=None, seeds=(60040, 60040))
    path = out / "rows.jsonl"
    lines = path.read_bytes().split(b"\n")
    # cut the last complete row in half and drop its newline
    assert lines[-1] == b""
    n_before = len(lines) - 1
    path.write_bytes(b"\n".join(lines[:-2]) + b"\n" + lines[-2][: len(lines[-2]) // 2])
    with pytest.raises(RunnerError, match="partial line"):
        RowStore(path).load(truncate=False)
    _, s = frozen_run(tmp, "trunc", fp)             # recover + extend to both seeds
    assert "partial line" in capsys.readouterr().err
    rows = read_rows(out)
    assert len({row_key(r) for r in rows}) == len(rows)
    assert strip(rows) == strip(read_rows(clean))
    m = json.loads((out / "manifest.json").read_text())
    assert any(i["partial_bytes_recovered"] > 0 for i in m["invocations"])
    assert n_before == 5 * 2


def test_corrupt_middle_line_is_an_error(tuned):
    tmp, _, fp = tuned
    out, _ = frozen_run(tmp, "corrupt", fp, seeds=(60040, 60040))
    path = out / "rows.jsonl"
    lines = path.read_bytes().split(b"\n")
    lines[1] = b"{not json"
    path.write_bytes(b"\n".join(lines))
    with pytest.raises(RunnerError, match="corrupt"):
        frozen_run(tmp, "corrupt", fp)


def test_idempotent_rerun(tuned):
    tmp, _, fp = tuned
    out, s1 = frozen_run(tmp, "idem", fp)
    before = (out / "rows.jsonl").read_bytes()
    _, s2 = frozen_run(tmp, "idem", fp)
    assert s2["rows_written"] == 0 and s2["tasks"] == 0 and s1["rows_written"] > 0
    assert (out / "rows.jsonl").read_bytes() == before
    # extending the seed range only adds the new seed
    _, s3 = frozen_run(tmp, "idem", fp, seeds=(60040, 60042))
    assert s3["rows_written"] == 2 * 5
    rows = read_rows(out)
    assert len({row_key(r) for r in rows}) == len(rows) == 3 * 2 * 5


def test_idempotent_tune(tmp_path):
    out = tune(tmp_path)
    before = (out / "rows.jsonl").read_bytes()
    tune(tmp_path)
    assert (out / "rows.jsonl").read_bytes() == before


def test_worker_count_invariance(tuned):
    tmp, _, fp = tuned
    o1, _ = frozen_run(tmp, "w1", fp, workers=1, seeds=(60040, 60042))
    o2, _ = frozen_run(tmp, "w2", fp, workers=2, seeds=(60040, 60042))
    r1, r2 = read_rows(o1), read_rows(o2)
    assert strip(r1) == strip(r2)
    assert [row_key(r) for r in r1] == [row_key(r) for r in r2]   # file order too
    t1 = read_rows(tune(tmp, "tw1", workers=1))
    t2 = read_rows(tune(tmp, "tw2", workers=2))
    assert strip(t1) == strip(t2)


def test_manifest_contents(tuned):
    tmp, _, fp = tuned
    out, _ = frozen_run(tmp, "man", fp)
    frozen_run(tmp, "man", fp)
    m = json.loads((out / "manifest.json").read_text())
    pv = m["package_versions"]
    assert set(pv) == {"python", "numpy", "scipy", "networkx"} and all(pv.values())
    assert "commit" in m["git"] and "dirty" in m["git"]
    assert m["git"]["commit"] is None or len(m["git"]["commit"]) == 40
    assert m["args"]["family"] == "F0R" and m["args"]["seeds"] == list(FROZEN_SEEDS)
    assert m["status"] == "complete" and m["start_utc"] and m["end_utc"]
    assert m["cpu_s_total"] >= 0 and m["wall_s"] >= 0
    assert m["row_counts"]["total"] == 20
    assert m["row_counts"]["by_family"]["bound"] == 4
    assert m["row_counts"]["by_mode"] == {"frozen": 20}
    assert len(m["invocations"]) == 2 and m["invocations"][1]["rows_written"] == 0
    assert m["invocations"][0]["rows_written"] == 20


def test_main_cli_end_to_end(tuned, capsys):
    tmp, _, fp = tuned
    rc = main(["--family", "F0R", "--seeds", "60040-60040", "--out", str(tmp / "cli"),
               "--frozen-path", str(fp), "--workers", "1", "--cells", ",".join(CELL_IDS),
               "--policies", "CE-LLF,Margin-LLF", "--allow-dirty"],
              families=families(), params=PARAMS, f0r_N=N_SMALL, open_ranges=OPEN)
    assert rc == 0
    assert len(read_rows(tmp / "cli")) == 2 * 3
    assert "wrote 6 rows" in capsys.readouterr().out


def test_policy_failure_aborts_without_swallowing(tmp_path):
    bad = Family("Bad", "oblivious", ({"m": 0},), {"m": 0},
                 lambda cfg, p: Greedy(m=cfg["m"]) if False else _Raises())
    with pytest.raises(RuntimeError, match="policy bug"):
        run("KCOPY", (60030, 60030), tmp_path / "bad", cell_ids=[KCOPY_CELLS[0].cell_id],
            families=[bad], params=PARAMS, open_ranges=OPEN, allow_dirty=True)


class _Raises:
    name, privileged = "x", False

    def reset(self, *a, **k):
        pass

    def floor_mask(self, sv):
        return None

    def act(self, view):
        raise RuntimeError("policy bug")


# ------------------------------------------------------------------ seed refusal --
REFUSED = [
    ("F0R", "frozen", 500000, 500000), ("F0R", "frozen", 500999, 500999),  # seed-rule: refusal-test
    ("KCOPY", "frozen", 500100, 500200), ("SCALE", "frozen", 499999, 500001),  # seed-rule: refusal-test
    ("F0R", "tune", 500000, 500000),  # seed-rule: refusal-test
    ("F0R", "frozen", 0, 79), ("F0R", "frozen", 5, 5), ("F0R", "frozen", 62000, 62099),  # seed-rule: refusal-test
    ("F0R", "frozen", 100000, 100999), ("F0R", "frozen", 200000, 200000),
    ("F0R", "frozen", 300000, 300000), ("F0R", "frozen", 60000, 60049),   # tuning seeds
    ("F0R", "frozen", 60999, 61000), ("F0R", "frozen", 61050, 61100),  # seed-rule: refusal-test
    ("F0R", "frozen", 61000, 62000),  # seed-rule: refusal-test
    ("F0R", "tune", 61000, 61000), ("F0R", "tune", 59999, 60000), ("F0R", "tune", 60000, 60050),  # seed-rule: refusal-test
    ("KCOPY", "frozen", 61000, 61000), ("KCOPY", "frozen", 61600, 61600),  # seed-rule: refusal-test
    ("KCOPY", "tune", 61500, 61500),  # seed-rule: refusal-test
    ("SCALE", "frozen", 63020, 63020), ("SCALE", "frozen", 61000, 61000),  # seed-rule: refusal-test
    ("SCALE", "tune", 63000, 63000),  # seed-rule: refusal-test
]
ACCEPTED = [("F0R", "tune", 60000, 60049), ("F0R", "tune", 60010, 60010),
            ("F0R", "frozen", 61000, 61099), ("F0R", "frozen", 61000, 61019),  # seed-rule: refusal-test
            ("KCOPY", "frozen", 61500, 61599), ("SCALE", "frozen", 63000, 63019)]  # seed-rule: refusal-test


@pytest.mark.parametrize("fam,mode,lo,hi", REFUSED)
def test_seed_refusals(tmp_path, fam, mode, lo, hi):
    with pytest.raises(SeedRefused):
        check_seeds(fam, mode, lo, hi, repo_root=tmp_path)
    out = tmp_path / "never"
    with pytest.raises(SeedRefused):
        run(fam, (lo, hi), out, mode=mode, families=families(), params=PARAMS,
            repo_root=tmp_path)
    assert not out.exists()
    rc = main(["--family", fam, "--mode", mode, "--seeds", f"{lo}-{hi}", "--out", str(out)],
              families=families(), params=PARAMS, repo_root=tmp_path)
    assert rc == 2 and not out.exists()


@pytest.mark.parametrize("fam,mode,lo,hi", ACCEPTED)
def test_seed_accepts_ledger_ranges(tmp_path, fam, mode, lo, hi):
    check_seeds(fam, mode, lo, hi, repo_root=tmp_path)


def test_real_confirmation_file_absent():
    assert not (runner.REPO_ROOT / "CONFIRMATION_APPROVED").exists()
    with pytest.raises(SeedRefused):
        check_seeds("F0R", "frozen", 500000, 500000)        # real repo root  # seed-rule: refusal-test


@pytest.mark.parametrize("text", ["", "RUN\n", "approved\n", "please run\n", "run now\n",
                                  "yes\n", "Run\n", "run\n\n", "x\nrun\n", "run\nx\n",
                                  "run\r\n", " run\n", "run \n"])
def test_wrong_confirmation_text_refused(tmp_path, text):
    (tmp_path / "CONFIRMATION_APPROVED").write_text(text)
    with pytest.raises(SeedRefused):
        check_seeds("F0R", "frozen", 500000, 500010, repo_root=tmp_path)  # seed-rule: refusal-test


def test_right_confirmation_text_opens_only_confirmation_range(tmp_path):
    (tmp_path / "CONFIRMATION_APPROVED").write_text("run\n")
    check_seeds("F0R", "frozen", 500000, 500010, repo_root=tmp_path)  # seed-rule: refusal-test
    (tmp_path / "CONFIRMATION_APPROVED").write_text("run")      # no newline is fine too
    check_seeds("F0R", "frozen", 500000, 500010, repo_root=tmp_path)  # seed-rule: refusal-test
    for lo, hi in ((499999, 500001), (500990, 501000)):  # seed-rule: refusal-test
        with pytest.raises(SeedRefused):
            check_seeds("F0R", "frozen", lo, hi, repo_root=tmp_path)
    with pytest.raises(SeedRefused):
        check_seeds("F0R", "tune", 500000, 500001, repo_root=tmp_path)  # seed-rule: refusal-test
    # approval does not widen the ordinary ranges
    with pytest.raises(SeedRefused):
        check_seeds("F0R", "frozen", 62000, 62001, repo_root=tmp_path)  # seed-rule: refusal-test


def test_test_only_range_override_cannot_open_confirmation(tmp_path):
    ov = {("F0R", "frozen"): (0, 10), ("F0R", "tune"): (0, 10)}
    check_seeds("F0R", "frozen", 5, 6, repo_root=tmp_path, open_ranges=ov)
    with pytest.raises(SeedRefused):
        check_seeds("F0R", "frozen", 400000, 500500, repo_root=tmp_path, open_ranges=ov)  # seed-rule: refusal-test
    with pytest.raises(SeedRefused):
        check_seeds("F0R", "frozen", 11, 11, repo_root=tmp_path, open_ranges=ov)
    # the defaults carry no override
    assert runner.OPEN_RANGES == {
        ("F0R", "tune"): (60000, 60049), ("F0R", "frozen"): (61000, 61099),  # seed-rule: refusal-test
        ("KCOPY", "frozen"): (61500, 61599), ("SCALE", "frozen"): (63000, 63019)}  # seed-rule: refusal-test


def test_parse_seeds():
    assert runner.parse_seeds("60010-60019") == (60010, 60019)
    assert runner.parse_seeds("60010") == (60010, 60010)
    for bad in ("", "a-b", "5-3", "1-2-3"):
        with pytest.raises(RunnerError):
            runner.parse_seeds(bad)


def test_lock_blocks_second_runner(tuned):
    tmp, _, fp = tuned
    import fcntl
    out = tmp / "locked"
    out.mkdir()
    fd = os.open(out / ".lock", os.O_RDWR | os.O_CREAT)
    fcntl.flock(fd, fcntl.LOCK_EX)
    try:
        with pytest.raises(RunnerError, match="in use"):
            frozen_run(tmp, "locked", fp)
    finally:
        os.close(fd)


# ------------------------------------------------------------------ review fixes --
import hashlib
import subprocess


def git(cwd, *a):
    subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", "-C", str(cwd), *a],
                   check=True, capture_output=True)


def test_freeze_requires_full_tuning_set(tmp_path):
    out = tmp_path / "f"
    out.mkdir()
    write_fake(out, {(CELL_IDS[0], i): (3.0 - i, 0.0) for i in range(3)})
    kw = dict(families=[fake_family()], params_path=tmp_path / "none.json")
    with pytest.raises(RunnerError, match="full tuning set"):
        freeze(out, seeds=TUNE, frozen_path=tmp_path / "a.json", **kw)       # 2 of 50 seeds
    with pytest.raises(RunnerError, match="every F0-R cell"):
        freeze(out, cell_ids=CELL_IDS[:1], frozen_path=tmp_path / "a.json", **kw)
    with pytest.raises(RunnerError, match="missing"):                       # default = 50 seeds
        freeze(out, frozen_path=tmp_path / "a.json", **kw)
    assert not (tmp_path / "a.json").exists()


def test_freeze_full_set_positive(tmp_path):
    out = tmp_path / "f"
    out.mkdir()
    store = RowStore(out / "rows.jsonl")
    store.open()
    for c in F0R_CELLS:
        for idx in range(2):
            for s in range(60000, 60050):
                store.append({"mode": "tune", "seed": s, "cell_id": c.cell_id,
                              "study_family": "F0R", "policy": tune_name("T", idx),
                              "config_index": idx, "config": {"m": idx}, "family": "T",
                              "params_sha256": None, "R_avoid_kwh_per100": 2.0 - idx,
                              "violation_kwslot": 0.0})
    store.close()
    fp = tmp_path / "TF.json"
    freeze(out, families=[fake_family(2)], frozen_path=fp, params_path=tmp_path / "none.json")
    d = json.loads(fp.read_text())
    assert len(d["T"]) == 22 and d["_meta"]["n_seeds"] == 50 and "git_commit" in d["_meta"]
    assert all(e["n_seeds"] == 50 and e["seeds"] == [60000, 60049] and e["config_index"] == 1
               for e in d["T"].values())
    runner.load_frozen(fp, None)                                         # the real check


def test_load_frozen_checks_seed_set(tuned):
    tmp, _, fp = tuned
    good = json.loads(fp.read_text())
    for name, edit in {
        "n49": lambda d: d["Margin-LLF"][CELL_IDS[0]].update(n_seeds=49),
        "range": lambda d: d["Margin-LLF"][CELL_IDS[0]].update(seeds=[60000, 60000]),
        "meta": lambda d: d["_meta"].update(seeds=[60000, 60000]),
        "metan": lambda d: d["_meta"].update(n_seeds=1),
    }.items():
        d = json.loads(json.dumps(good))
        edit(d)
        bad = tmp / f"bad_{name}.json"
        bad.write_text(json.dumps(d))
        with pytest.raises(RunnerError, match="tuning set|rests on"):
            frozen_run(tmp, f"bad_{name}", bad)
    assert runner.load_frozen(fp, None, TUNE)
    with pytest.raises(RunnerError, match="tuning set"):                 # 2 seeds != 50
        runner.load_frozen(fp, None)


def test_dedupe_key_has_no_config_index_and_config_change_refused(tuned):
    tmp, _, fp = tuned
    out, _ = frozen_run(tmp, "dd", fp)
    rows = read_rows(out)
    assert all(len(row_key(r)) == 4 for r in rows)
    assert row_key(rows[0]) == (rows[0]["study_family"], rows[0]["seed"], rows[0]["cell_id"],
                                rows[0]["policy"])
    d = json.loads(fp.read_text())
    for ent in d["Margin-LLF"].values():
        ent["config_index"] = 1 - ent["config_index"]
        ent["config"] = {"m": ent["config_index"]}
    other = tmp / "other_selection.json"
    other.write_text(json.dumps(d))
    before = (out / "rows.jsonl").read_bytes()
    with pytest.raises(RunnerError, match="different config"):
        frozen_run(tmp, "dd", other)
    assert (out / "rows.jsonl").read_bytes() == before                    # nothing appended
    frozen_run(tmp, "dd", fp)                                             # same selection: fine


def test_provenance_params_sha_everywhere(tmp_path):
    pp = tmp_path / "pp.json"
    pp.write_text(json.dumps(PARAMS.__dict__))
    sha = hashlib.sha256(pp.read_bytes()).hexdigest()
    out = tmp_path / "t"
    run("F0R", TUNE, out, mode="tune", cell_ids=CELL_IDS[:1], families=families(),
        params_path=pp, f0r_N=N_SMALL, open_ranges=OPEN)
    assert {r["params_sha256"] for r in read_rows(out)} == {sha}
    fp = tmp_path / "TF.json"
    kw = dict(seeds=TUNE, cell_ids=CELL_IDS[:1], families=families(), frozen_path=fp,
              params_path=pp, open_ranges=OPEN)
    freeze(out, **kw)
    meta = json.loads(fp.read_text())["_meta"]
    assert meta["population_params_sha256"] == sha and "git_commit" in meta
    # frozen manifest records both hashes
    o2 = tmp_path / "fr"
    run("F0R", (60040, 60040), o2, cell_ids=CELL_IDS[:1], families=families(), params_path=pp,
        frozen_path=fp, f0r_N=N_SMALL, open_ranges=OPEN, allow_dirty=True)
    m = json.loads((o2 / "manifest.json").read_text())
    assert m["provenance"]["population_params_sha256"] == sha
    assert m["provenance"]["tuning_frozen_sha256"] == hashlib.sha256(fp.read_bytes()).hexdigest()
    assert m["invocations"][0]["population_params_sha256"] == sha
    assert m["provenance"]["allow_dirty"] is True and m["args"]["allow_dirty"] is True
    assert {r["params_sha256"] for r in read_rows(o2)} == {sha}
    # rows that disagree with each other
    rows = read_rows(out)
    rows[0]["params_sha256"] = "0" * 64
    bad = tmp_path / "bad"
    bad.mkdir()
    (bad / "rows.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    with pytest.raises(RunnerError, match="disagree"):
        freeze(bad, **{**kw, "frozen_path": tmp_path / "x.json", "overwrite": True})
    # rows that disagree with the current file
    pp.write_text(json.dumps({**PARAMS.__dict__, "alpha": 9.0}))
    with pytest.raises(RunnerError, match="differ from the current"):
        freeze(out, **{**kw, "frozen_path": tmp_path / "y.json"})


def test_frozen_requires_committed_files(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-q")
    pp, fp = repo / "pp.json", repo / "TF.json"
    pp.write_text(json.dumps(PARAMS.__dict__))
    out = tmp_path / "t"
    run("F0R", TUNE, out, mode="tune", cell_ids=CELL_IDS[:1], families=families(),
        params_path=pp, f0r_N=N_SMALL, open_ranges=OPEN)
    freeze(out, seeds=TUNE, cell_ids=CELL_IDS[:1], families=families(), frozen_path=fp,
           params_path=pp, open_ranges=OPEN)
    kw = dict(cell_ids=CELL_IDS[:1], families=families(), params_path=pp, frozen_path=fp,
              f0r_N=N_SMALL, open_ranges=OPEN, repo_root=repo)

    def attempt(name):
        return run("F0R", (60040, 60040), tmp_path / name, **kw)

    with pytest.raises(RunnerError, match="committed"):                  # untracked
        attempt("r1")
    assert not runner.is_committed(pp) and not runner.is_committed(fp)
    git(repo, "add", "pp.json", "TF.json")
    with pytest.raises(RunnerError, match="committed"):                  # staged only
        attempt("r2")
    git(repo, "commit", "-q", "-m", "x")
    attempt("r3")
    m = json.loads((tmp_path / "r3" / "manifest.json").read_text())
    assert m["provenance"]["allow_dirty"] is False
    assert set(m["provenance"]["committed"].values()) == {True}
    assert m["git"]["commit"] and len(m["git"]["commit"]) == 40
    fp.write_text(fp.read_text() + "\n")                                  # modified vs HEAD
    with pytest.raises(RunnerError, match="committed"):
        attempt("r4")
    run("F0R", (60040, 60040), tmp_path / "r5", allow_dirty=True, **kw)   # flag overrides
    assert json.loads((tmp_path / "r5" / "manifest.json").read_text())["args"]["allow_dirty"]
    # KCOPY needs the params file committed too
    git(repo, "checkout", "--", "TF.json")
    pp.write_text(pp.read_text() + " ")
    with pytest.raises(RunnerError, match="committed"):
        run("KCOPY", (60030, 60030), tmp_path / "r6", cell_ids=[KCOPY_CELLS[0].cell_id],
            families=families(), params_path=pp, repo_root=repo, open_ranges=OPEN)
    # the CLI flag exists and defaults to off
    assert runner.build_parser().parse_args(
        ["--family", "F0R", "--out", "x"]).allow_dirty is False
    # tune mode does not need committed files
    run("F0R", TUNE, tmp_path / "t2", mode="tune", cell_ids=CELL_IDS[:1], families=families(),
        params_path=pp, f0r_N=N_SMALL, open_ranges=OPEN, repo_root=repo)


def test_dirty_flag_counts_untracked_and_modified(tmp_path):
    repo = tmp_path / "repo"
    (repo / "src").mkdir(parents=True)
    (repo / "tests").mkdir()
    git(repo, "init", "-q")
    (repo / "src" / "a.py").write_text("x = 1\n")
    (repo / "run_study.py").write_text("pass\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "x")
    assert runner._git(repo)["dirty"] is False
    (repo / "elsewhere.txt").write_text("not watched")
    assert runner._git(repo)["dirty"] is False
    (repo / "src" / "new.py").write_text("untracked")
    assert runner._git(repo)["dirty"] is True
    (repo / "src" / "new.py").unlink()
    (repo / "tests" / "t.py").write_text("untracked")
    assert runner._git(repo)["dirty"] is True
    (repo / "tests" / "t.py").unlink()
    (repo / "run_study.py").write_text("changed\n")
    assert runner._git(repo)["dirty"] is True
    (repo / "run_study.py").write_text("pass\n")
    (repo / "results").mkdir()
    (repo / "results" / "TUNING_FROZEN.json").write_text("{}")             # untracked
    assert runner._git(repo)["dirty"] is True


def test_rowstore_keeps_only_keys(tuned):
    tmp, out, _ = tuned
    import shutil
    cp = tmp / "rowstore_copy"
    cp.mkdir(exist_ok=True)
    shutil.copy(out / "rows.jsonl", cp / "rows.jsonl")
    st = RowStore(cp / "rows.jsonl").load()
    assert not hasattr(st, "rows") and len(st) == 8
    assert all(isinstance(k, tuple) and isinstance(v, str) for k, v in st.keys.items())
    assert st.by_mode == {"tune": 8} and st.by_family == {"Margin-LLF": 8}
    st.open()
    st.append({"mode": "tune", "seed": 1, "cell_id": "c", "study_family": "F0R",
               "policy": "p", "family": "p", "config": None})
    st.close()
    assert not hasattr(st, "rows") and len(st) == 9


def test_freeze_rejects_nonfinite(tmp_path):
    for bad in (float("nan"), float("inf")):
        out = tmp_path / f"f{bad}"
        out.mkdir()
        write_fake(out, {(CELL_IDS[0], i): (3.0 - i, 0.0) for i in range(3)})
        rows = list(iter_rows(out / "rows.jsonl"))
        rows[4]["R_avoid_kwh_per100"] = bad
        (out / "rows.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
        with pytest.raises(RunnerError, match="non-finite objective in row") as e:
            freeze(out, seeds=TUNE, cell_ids=CELL_IDS[:1], families=[fake_family()],
                   frozen_path=tmp_path / "x.json", params_path=tmp_path / "none.json",
                   open_ranges=OPEN)
        assert rows[4]["policy"] in str(e.value) and str(rows[4]["seed"]) in str(e.value)
        assert not (tmp_path / "x.json").exists()


def test_partial_line_truncation_is_fsynced(tmp_path, monkeypatch):
    p = tmp_path / "rows.jsonl"
    row = {"mode": "tune", "seed": 1, "cell_id": "c", "study_family": "F0R", "policy": "p",
           "family": "p", "config": None}
    p.write_bytes((json.dumps(row) + "\n").encode() + b'{"mode": "tu')
    calls = []
    real = os.fsync
    monkeypatch.setattr(runner.os, "fsync", lambda fd: (calls.append(fd), real(fd))[1])
    st = RowStore(p).load(quiet=True)
    assert calls and st.recovered_bytes == len(b'{"mode": "tu') and len(st) == 1
    assert p.read_bytes() == (json.dumps(row) + "\n").encode()


def test_single_worker_cpu_not_double_counted_on_failure(tuned, monkeypatch):
    tmp, _, fp = tuned
    orig = runner.run_task
    monkeypatch.setattr(runner, "run_task", lambda t: (orig(t)[0], 1000.0))
    with pytest.raises(Boom):
        frozen_run(tmp, "cpu", fp, after_row=killer(2))
    m = json.loads((tmp / "cpu" / "manifest.json").read_text())
    assert m["invocations"][-1]["status"] == "failed" and m["cpu_s_total"] < 100
