"""Greedy expected-value hedge ranker (post hoc, added 2026-11-02 at the referee's request;
docs/RANKER_POSTHOC.md): caps and rates, never commanding a participant believed complete,
greedy by value, determinism, exact equality with the one-slot MPC, families and frozen file.

Every test uses seeds 60000-60049 only (docs/SEED_LEDGER.md)."""
import json
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from papere import runner
from papere.generator import F0R_CELLS, generate_f0r
from papere.instance import Cell
from papere.policies.base import PopulationParams, PosteriorState
from papere.policies.beliefs import CEBelief, HMMBelief, known_complete
from papere.policies.catalog import FAMILIES
from papere.policies.mpc import MPCPolicy
from papere.policies.posthoc import EXTRA_FAMILIES
from papere.policies.ranker import RANKER_FAMILIES, GreedyEV
from papere.sim import simulate

from test_policy_lint import lint_source
from test_rules import static_of, view_at

ROOT = Path(__file__).resolve().parents[1]
PARAMS = PopulationParams(**json.loads((ROOT / "results" / "population_params.json")
                                       .read_text())["values"])
RANK = {f.name: f for f in RANKER_FAMILIES}
BASE = Cell(family="F0R", M=3, delta_A=2, delta_b=0, rho=1.15, r=0.3)
FROZEN_RANKER = ROOT / "results" / "TUNING_FROZEN_posthoc_ranker.json"


class Stub:
    """Hand belief: fixed ``tail`` [N, K] and ``p_avail`` [N, H]; tail_avail = tail * p_avail."""

    name = "stub"

    def __init__(self, tail, p_avail):
        self.tail = np.asarray(tail, float)
        self.pav = np.asarray(p_avail, float)

    def reset(self, static_view, floored=None, oracle=None):
        pass

    def compute(self, view):
        tav = self.tail[:, :, None] * self.pav[:, None, :]
        return PosteriorState(t=view.t, tail=self.tail, tail_avail=tav, p_avail=self.pav,
                              exp_debt=self.tail.sum(1), p_pos=self.tail[:, 0].copy(),
                              point=False)


class Recorder:
    """Wraps a policy and keeps (view, action) for every act call."""

    def __init__(self, pol):
        self.pol, self.name, self.privileged = pol, pol.name, pol.privileged
        self.calls = []

    def reset(self, sv, rng, oracle=None):
        self.pol.reset(sv, rng, oracle=oracle)

    def floor_mask(self, sv):
        return self.pol.floor_mask(sv)

    def act(self, view):
        x = self.pol.act(view)
        self.calls.append((view, x.copy(), self.pol.last_scores.copy()))
        return x


def makers():
    return [lambda: GreedyEV(HMMBelief(PARAMS, "e1"), 0, 1.0, name="e1"),
            lambda: GreedyEV(HMMBelief(PARAMS, "population"), 1, 0.0, name="pop"),
            lambda: GreedyEV(CEBelief(), 2, 0.0, name="ce"),
            lambda: GreedyEV(HMMBelief(PARAMS, "e1"), 0, 2.0, name="e1g2")]


# ---------------------------------------------------------------------------- hand views
def test_greedy_takes_the_highest_expected_delivery_first():
    """Cap 2, three participants owing 2 units each: the more likely available ones win,
    whatever their deadlines (no planning), and the second unit of the best participant beats
    the first unit of a worse one."""
    sv = static_of(E=[2, 2, 2], P=[2, 2, 2], a=[0] * 3, d=[2, 6, 6], H=6, dA=2,
                   L=np.full((1, 6), 2.0))
    tail = np.array([[1.0, 1.0], [1.0, 0.9], [1.0, 0.2]])
    pav = np.array([[0.5] * 6, [0.9] * 6, [0.95] * 6])
    p = GreedyEV(Stub(tail, pav), 0, 0.0)
    p.reset(sv, np.random.default_rng(0))
    # values: p0 0.5, 0.5; p1 0.9, 0.81; p2 0.95, 0.19 -> top two units: p2#1, p1#1
    assert p.act(view_at(sv, 0)).tolist() == [0, 1, 1]
    sv3 = static_of(E=[2, 2, 2], P=[2, 2, 2], a=[0] * 3, d=[2, 6, 6], H=6, dA=2,
                    L=np.full((1, 6), 3.0))
    p.reset(sv3, np.random.default_rng(0))
    assert p.act(view_at(sv3, 0)).tolist() == [0, 2, 1]                   # then p1#2 (0.81)


def test_proposition3_style_hedge_goes_to_the_identified_participant():
    """One spare unit, two twins already served at slot 0 under lag 2: the hedge goes to the
    twin with the higher probability of still owing (greedy by value, as in Proposition 3)."""
    sv = static_of(E=[1, 1], P=[1, 1], a=[0, 0], d=[2, 2], H=2, dA=2, L=np.full((1, 2), 1.0))
    tail = np.array([[0.1], [0.6]])
    p = GreedyEV(Stub(tail, np.ones((2, 2))), 0, 0.0)
    p.reset(sv, np.random.default_rng(0))
    x = np.array([[1, 0], [1, 0]])
    assert p.act(view_at(sv, 1, x=x)).tolist() == [0, 1]


def test_respects_rates_and_group_caps_on_hand_views():
    rng = np.random.default_rng(60001)
    for _ in range(200):
        N = int(rng.integers(2, 9))
        H = 6
        P = rng.integers(1, 4, size=N)
        group = rng.integers(0, 2, size=N)
        group[0], group[-1] = 0, 1
        L = rng.integers(0, 6, size=(2, H)).astype(float)
        sv = static_of(E=P * 2, P=P, a=[0] * N, d=rng.integers(1, H + 1, size=N), H=H,
                       group=group, L=L)
        tail = np.sort(rng.random((N, 6)), axis=1)[:, ::-1]
        p = GreedyEV(Stub(tail, rng.random((N, H))), int(rng.integers(0, 3)), 1.0)
        p.reset(sv, rng)
        v = view_at(sv, 0)
        x = p.act(v)
        caps = np.maximum(0, v.setpoint_caps(p.m))
        assert x.dtype == np.int64 and (x >= 0).all() and (x <= P).all()
        assert (x[~v.active] == 0).all()
        for g in range(2):
            used = int(x[group == g].sum())
            assert used <= caps[g]
            # greedy uses the whole cap when enough positive units exist
            room = int(np.minimum(P, (tail > 1e-12).sum(1))[(group == g) & v.active].sum())
            assert used == min(caps[g], room)


def test_never_commands_a_participant_believed_complete():
    """p0 delivered all it owed (confirmed debt 0); p1 was commanded at a slot whose A is
    hidden (true debt was already 0). Both are known complete; spare cap goes unused."""
    sv = static_of(E=[2, 3, 2], P=[2, 2, 2], a=[0] * 3, d=[6, 6, 6], H=6, dA=1,
                   L=np.full((1, 6), 10.0))
    x = np.zeros((3, 6), int)
    A = np.full((3, 6), -1, int)
    y = np.zeros((3, 6), int)
    x[0, 0], A[0, 0], y[0, 0] = 2, 1, 2            # p0 done
    x[1, 0], A[1, 0], y[1, 0] = 2, 1, 2
    x[1, 1], A[1, 1], y[1, 1] = 2, 1, 1            # p1 done at slot 1
    v = view_at(sv, 3, x=np.where(np.arange(6)[None, :] < 3, x, 0), A=A, y=y)
    for make in (lambda: GreedyEV(HMMBelief(PARAMS, "e1"), 0, 1.0),
                 lambda: GreedyEV(HMMBelief(PARAMS, "population"), 0, 2.0),
                 lambda: GreedyEV(CEBelief(), 0, 0.0)):
        p = make()
        p.reset(sv, np.random.default_rng(0))
        out = p.act(v)
        assert known_complete(v)[:2].all()
        assert out[0] == 0 and out[1] == 0 and out[2] == 2


@pytest.mark.parametrize("dA", [0, 1, 2, 4])
def test_never_commands_believed_complete_or_revealed_stuck_in_the_simulator(dA):
    """Every action of every call: no unit to a participant the wrapper marks complete, to one
    revealed stuck in column t (delta_A = 0) or to one whose offered units are all worthless."""
    cell = replace(BASE, delta_A=dA)
    n_calls = 0
    for j, make in enumerate(makers()):
        for seed in (60000 + 3 * j, 60031 + j):
            inst = generate_f0r(seed, cell)
            rec = Recorder(make())
            tr = simulate(inst, cell, rec, seed)       # the simulator raises on any breach
            for view, x, sc in rec.calls:
                done = known_complete(view)
                assert (x[done] == 0).all()
                if dA == 0 and view.A_confirmed.shape[1] == view.t + 1:
                    assert (x[view.A_confirmed[:, view.t] == 0] == 0).all()
                assert ((x > 0) <= np.isfinite(sc).any(axis=1)).all()
                n_calls += 1
            assert (tr.x <= inst.P[:, None]).all()
    assert n_calls > 0


@pytest.mark.parametrize("cell", F0R_CELLS, ids=lambda c: c.cell_id)
def test_actions_are_feasible_on_every_f0r_cell(cell):
    for j, make in enumerate(makers()):
        seed = 60000 + (j * 11) % 50
        inst = generate_f0r(seed, cell)
        tr = simulate(inst, cell, make(), seed)       # validates windows, P_i and caps
        assert tr.x.dtype == np.int64


# ----------------------------------------------------------------------------- determinism
def test_deterministic_with_a_fixed_seed():
    cell = replace(BASE, delta_A=1)
    inst = generate_f0r(60005, cell)
    for make in makers():
        a = simulate(inst, cell, make(), 60005)
        b = simulate(inst, cell, make(), 60005)
        assert np.array_equal(a.x, b.x) and np.array_equal(a.y, b.y)
    sv = static_of(E=[3] * 6, P=[1] * 6, a=[0] * 6, d=[6] * 6, H=6, L=np.full((1, 6), 2.0))
    outs = set()
    for s in range(30):                               # equal values: ties by the rng, not index
        p = GreedyEV(CEBelief(), 0, 0.0)
        p.reset(sv, np.random.default_rng(s))
        o = p.act(view_at(sv, 0))
        assert o.sum() == 2
        outs.add(tuple(o.tolist()))
        p2 = GreedyEV(CEBelief(), 0, 0.0)
        p2.reset(sv, np.random.default_rng(s))
        assert np.array_equal(p2.act(view_at(sv, 0)), o)
    assert len(outs) > 5


# ------------------------------------------------------------- equality with one-slot MPC
@pytest.mark.parametrize("dA", [0, 1, 2, 4])
@pytest.mark.parametrize("rho", [0.95, 1.15])
def test_equals_mpc_with_a_one_slot_horizon_decision_for_decision(dA, rho):
    """The greedy fill is the exact optimum of the one-slot problem (laminar matroid), so the
    ranker equals MPCPolicy(W = 1) with the same belief, m and gamma, same tie table."""
    cell = replace(BASE, delta_A=dA, rho=rho)
    for seed in (60002, 60019, 60037):
        inst = generate_f0r(seed, cell)
        for mode in ("e1", "population", "ce"):
            for m, g in ((0, 0.0), (1, 1.0), (0, 2.0)):
                def bel():
                    return CEBelief() if mode == "ce" else HMMBelief(PARAMS, mode)
                a = simulate(inst, cell, GreedyEV(bel(), m, g, name="x"), seed)
                b = simulate(inst, cell, MPCPolicy(bel(), 1, m, k=0, gamma=g, name="x"), seed)
                assert np.array_equal(a.x, b.x), (mode, m, g, seed)


# -------------------------------------------------------------------- families and freeze
def test_ranker_families_are_separate_and_within_budget():
    names = {f.name for f in FAMILIES} | {f.name for f in EXTRA_FAMILIES}
    assert len(FAMILIES) == 17 and set(RANK).isdisjoint(names)
    assert set(RANK) == {"greedy_ev", "greedy_ev_pop", "greedy_ev_ce"}
    assert len(RANK["greedy_ev"].grid) == len(RANK["greedy_ev_pop"].grid) == 12
    assert len(RANK["greedy_ev_ce"].grid) == 3
    assert all(f.tunable and len(f.grid) <= 48 for f in RANKER_FAMILIES)
    assert RANK["greedy_ev"].kind == "per_participant"
    assert RANK["greedy_ev_pop"].kind == RANK["greedy_ev_ce"].kind == "oblivious"
    e1 = RANK["greedy_ev"].make({"m": 1, "gamma": 0.5}, PARAMS)
    pop = RANK["greedy_ev_pop"].make({"m": 1, "gamma": 0.5}, PARAMS)
    ce = RANK["greedy_ev_ce"].make({"m": 2}, PARAMS)
    assert e1.belief.mode == "e1" and pop.belief.mode == "population"
    assert isinstance(ce.belief, CEBelief) and ce.gamma == 0.0 and ce.m == 2.0
    assert (e1.W, e1.k, e1.m, e1.gamma) == (1, 0, 1.0, 0.5)
    runner.load_families(list(FAMILIES) + list(EXTRA_FAMILIES) + list(RANKER_FAMILIES))


def test_ranker_module_passes_the_lint():
    p = ROOT / "src" / "papere" / "policies" / "ranker.py"
    assert lint_source(p.read_text(), "papere.policies.ranker") == []


@pytest.mark.skipif(not FROZEN_RANKER.exists(), reason="ranker tuning not frozen yet")
def test_frozen_ranker_file_rests_on_the_tuning_seeds_and_resolves_per_cell():
    d = runner.load_frozen(FROZEN_RANKER, runner._file_sha(runner.DEFAULT_PARAMS_PATH))
    assert set(d) == {"greedy_ev", "greedy_ev_pop", "greedy_ev_ce", "_meta"}
    assert d["_meta"]["seeds"] == [60000, 60049] and d["_meta"]["n_seeds"] == 50
    assert len(d["_meta"]["cells"]) == 22
    main = json.loads((ROOT / "results" / "TUNING_FROZEN.json").read_text())
    assert set(RANK).isdisjoint(main)                 # the main frozen file is untouched
    for c in (replace(BASE, delta_A=dA, rho=rho) for dA in (0, 1, 2, 4) for rho in (0.95, 1.15)):
        u = runner.plan_units(list(RANKER_FAMILIES), "frozen", c, d, None)
        for fam, sim, src, idx in u:
            assert fam == sim == src and d[fam][c.cell_id]["config_index"] == idx
            assert RANK[fam].grid[idx] == d[fam][c.cell_id]["config"]


# ------------------------------------------------------------------ the numbers file
NUMBERS = ROOT / "results" / "posthoc_ranker.json"


@pytest.mark.skipif(not NUMBERS.exists(), reason="scripts/posthoc_ranker.py not run yet")
def test_ranker_numbers_schema_label_and_checks():
    d = json.loads(NUMBERS.read_text())
    meta, nums = d["meta"], d["numbers"]
    label = "descriptive, post hoc, added 2026-11-02 at the referee's request"
    assert meta["label"] == label
    assert meta["bootstrap"]["n_boot"] == 10000 and meta["bootstrap"]["seed"] == 20261020
    assert meta["bootstrap"]["level"] == 0.95
    assert meta["seeds"] == list(runner.OPEN_RANGES[("F0R", "frozen")])   # the development range
    assert meta["checks"]["rerun_comparators_equal_f0r_extra"] == 8 * 3 * 4 * 100
    assert meta["checks"]["factorial_numbers_equal_posthoc_g3_runs"] == 8 * 4
    need = {"value", "ci_lo", "ci_hi", "n_seeds", "label", "unit", "statistic", "cell_id",
            "source_file"}
    for k, v in nums.items():
        assert k.startswith("posthoc_ranker/") and need <= set(v) and v["label"] == label, k
        assert v["n_seeds"] == 100
    for rho in ("0.95", "1.15"):
        for dA in (0, 1, 2, 4):
            b = f"posthoc_ranker/M3_rho{rho}/dA{dA}"
            for s in ("R_avoid_greedy_ev", "R_avoid_greedy_ev_pop", "greedy_ev_minus_ce_llf",
                      "greedy_ev_minus_targeted_mpc", "greedy_ev_pop_minus_shared_rate_mpc",
                      "belief_pop_to_e1_in_greedy", "belief_pop_to_e1_in_llf",
                      "belief_pop_to_e1_in_mpc", "belief_step_mpc_minus_greedy",
                      "violation_kwslot_greedy_ev"):
                assert f"{b}/{s}" in nums
    paper = json.loads((ROOT / "results" / "paper_numbers.json").read_text())["numbers"]
    others = set(paper)
    for name in ("posthoc_oblivious_share.json", "g2_numbers.json", "posthoc_g3_runs.json",
                 "confirm_paper_numbers.json", "posthoc_applied_energy.json"):
        p = ROOT / "results" / name
        if p.exists():
            others |= set(json.loads(p.read_text())["numbers"])
    assert others.isdisjoint(nums)                    # no key collision in paper/build.py
