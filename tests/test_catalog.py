"""Catalog (POLICY_SPEC 5 and 7): names, kinds, 48-point grids, defaults, every config builds
a working policy, MPC entries are lazy."""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from papere.generator import F0R_CELLS, generate_f0r
from papere.infoset import InformationSet, OracleView, StaticView
from papere.instance import Cell
from papere.policies.base import Family, PopulationParams
from papere.policies.catalog import FAMILIES
from papere.sim import Policy

from test_policy_lint import lint_source

ROOT = Path(__file__).resolve().parents[1]
PARAMS = PopulationParams(**json.loads((ROOT / "results" / "population_params.json")
                                       .read_text())["values"])
FAM = {f.name: f for f in FAMILIES}

NAMES = ["ce_llf", "ce_edf", "pes_llf", "sym_margin", "persistence", "uncorr_pes",
         "probe_first", "floor", "mpc_ce", "mpc_pes", "pop_mpc", "user_flag", "rwdf_e",
         "rwdf_e_literal", "llf_post", "guarded_mpc_e1", "oracle_mpc"]
KINDS = {"ce_llf": "oblivious", "ce_edf": "oblivious", "pes_llf": "oblivious",
         "sym_margin": "oblivious", "persistence": "oblivious", "uncorr_pes": "oblivious",
         "probe_first": "oblivious", "floor": "oblivious", "mpc_ce": "oblivious",
         "mpc_pes": "oblivious", "pop_mpc": "oblivious", "user_flag": "per_participant",
         "rwdf_e": "per_participant", "rwdf_e_literal": "per_participant",
         "llf_post": "per_participant",
         "guarded_mpc_e1": "candidate", "oracle_mpc": "reference"}
SINGLE = {"ce_llf", "ce_edf", "pes_llf"}
TUNABLE = [n for n in NAMES if n not in SINGLE | {"oracle_mpc"}]
AXES = {"sym_margin": {"O", "B", "m", "k"}, "persistence": {"O", "B", "m", "k"},
        "uncorr_pes": {"O", "B", "m", "k"}, "probe_first": {"O", "B", "m", "k"},
        "floor": {"O", "B", "m", "k"}, "user_flag": {"O", "B", "m", "k"},
        "rwdf_e": {"O", "B", "m", "k"}, "rwdf_e_literal": {"O", "B", "m", "k"},
        "mpc_ce": {"W", "m", "k"}, "mpc_pes": {"W", "m", "k"},
        "pop_mpc": {"W", "m", "gamma"}, "guarded_mpc_e1": {"W", "m", "gamma"},
        "llf_post": {"O", "theta", "m", "k"}}


def js(cfg) -> str:
    return json.dumps(cfg, sort_keys=True)


def test_seventeen_families():
    assert len(FAMILIES) == 17 and "rwdf_e_literal" in FAM


def test_names_order_and_kinds():
    assert [f.name for f in FAMILIES] == NAMES
    assert all(isinstance(f, Family) for f in FAMILIES)
    for f in FAMILIES:
        assert f.kind == KINDS[f.name], f.name


def test_tuned_from_and_tunable():
    for f in FAMILIES:
        assert f.tuned_from == ("guarded_mpc_e1" if f.name == "oracle_mpc" else None)
    assert {f.name for f in FAMILIES if f.tunable} == set(TUNABLE)
    assert not FAM["oracle_mpc"].tunable
    assert len(FAM["oracle_mpc"].grid) == 1 and FAM["oracle_mpc"].default == \
        FAM["guarded_mpc_e1"].default


@pytest.mark.parametrize("name", TUNABLE)
def test_grid_has_48_distinct_configs_with_the_right_axes(name):
    g = FAM[name].grid
    assert len(g) == 48
    assert len({js(c) for c in g}) == 48
    assert all(set(c) == AXES[name] for c in g)


def test_grid_values_match_the_spec():
    for name in ("sym_margin", "persistence", "uncorr_pes", "probe_first", "floor",
                 "user_flag", "rwdf_e", "rwdf_e_literal"):
        g = FAM[name].grid
        assert {c["O"] for c in g} == {"EDF", "LLF"} and {c["B"] for c in g} == {"CE", "PES"}
        assert {c["m"] for c in g} == {0, 1, 2} and {c["k"] for c in g} == {0, 1, 2, 3}
    for name in ("mpc_ce", "mpc_pes"):
        g = FAM[name].grid
        assert {c["W"] for c in g} == {2, 4, 8, 24}
        assert {c["m"] for c in g} == {0, 1, 2} and {c["k"] for c in g} == {0, 1, 2, 3}
    for name in ("pop_mpc", "guarded_mpc_e1"):
        g = FAM[name].grid
        assert {c["W"] for c in g} == {2, 4, 8, 24} and {c["m"] for c in g} == {0, 1, 2}
        assert {c["gamma"] for c in g} == {0, 0.5, 1, 2}
    g = FAM["llf_post"].grid
    assert {c["O"] for c in g} == {"EDF", "LLF"} and {c["theta"] for c in g} == {0, 0.05}
    assert {c["m"] for c in g} == {0, 1, 2} and {c["k"] for c in g} == {0, 1, 2, 3}


def test_single_points():
    assert FAM["ce_llf"].default == {"O": "LLF", "B": "CE", "m": 0, "k": 0}
    assert FAM["ce_edf"].default == {"O": "EDF", "B": "CE", "m": 0, "k": 0}
    assert FAM["pes_llf"].default == {"O": "LLF", "B": "PES", "m": 0, "k": 0}
    for n in SINGLE:
        assert FAM[n].grid == (FAM[n].default,)


def test_defaults_follow_section_7_and_lie_in_the_grid():
    for name in TUNABLE:
        f = FAM[name]
        d = f.default
        assert js(d) in {js(c) for c in f.grid}, name
        assert d["m"] == 0
        if "k" in d:
            assert d["k"] == 0
        if "gamma" in d:
            assert d["gamma"] == 1
        if "W" in d:
            assert d["W"] == 24
        if "O" in d:
            assert d["O"] == "LLF"
        if "B" in d:
            assert d["B"] == ("CE" if name == "user_flag" else "PES")
        if "theta" in d:
            assert d["theta"] == 0
    # exactly the runner's matching rule: same JSON text as the grid entry
    for f in FAMILIES:
        assert sum(js(c) == js(f.default) for c in f.grid) == 1


def _first_view(inst, cell):
    sv = StaticView.from_instance(inst, cell)
    N, H = inst.N, inst.H
    view = InformationSet.build(sv, 0, np.zeros((N, H), np.int64),
                                np.full((N, H), -1, np.int8), np.zeros((N, H), np.int64),
                                inst.b, 0, delta_A=cell.delta_A, delta_b=cell.delta_b)
    return sv, view


@pytest.mark.parametrize("name", NAMES)
def test_every_config_builds_a_working_policy(name):
    fam = FAM[name]
    cell = Cell(family="F0R", M=3, delta_A=2, delta_b=0, rho=0.95, r=0.3)
    inst = generate_f0r(60000, cell)
    sv, view = _first_view(inst, cell)
    oracle = OracleView.from_instance(inst)
    for ci, cfg in enumerate(fam.grid):
        pol = fam.make(cfg, PARAMS)
        assert isinstance(pol, Policy)
        assert pol.name == name
        assert bool(pol.privileged) == (name == "oracle_mpc")
        pol.reset(sv, np.random.default_rng(ci), oracle=oracle if pol.privileged else None)
        fm = pol.floor_mask(sv)
        assert (fm is not None) == (name == "floor")
        if fm is not None:
            assert fm.dtype == bool and fm.shape == (inst.N,) and fm.all()
        x = pol.act(view)
        assert x.shape == (inst.N,) and np.issubdtype(x.dtype, np.integer)
        assert (x >= 0).all() and (x <= inst.P).all()
        assert x.sum() <= max(0, view.setpoint_cap(0))
        assert (x[~view.active] == 0).all()


def test_each_make_returns_a_fresh_policy():
    for f in FAMILIES:
        a, b = f.make(f.default, PARAMS), f.make(f.default, PARAMS)
        assert a is not b


def test_catalog_imports_without_the_mpc_module():
    code = ("import sys\n"
            "sys.modules['papere.policies.mpc'] = None\n"
            "from papere.policies import catalog\n"
            "fams = {f.name: f for f in catalog.FAMILIES}\n"
            "assert len(fams) == 17\n"
            "fams['ce_llf'].make(fams['ce_llf'].default, None)\n"
            "try:\n"
            "    fams['mpc_ce'].make(fams['mpc_ce'].default, None)\n"
            "except ImportError:\n"
            "    print('lazy-ok')\n")
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                         cwd=ROOT)
    assert out.returncode == 0, out.stderr
    assert "lazy-ok" in out.stdout


def test_family_names_are_distinct_from_the_tune_suffix():
    assert all("@" not in f.name for f in FAMILIES)


def test_lint_clean():
    path = ROOT / "src" / "papere" / "policies" / "catalog.py"
    assert lint_source(path.read_text(), "papere.policies.catalog") == []
