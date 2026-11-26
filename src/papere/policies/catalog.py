"""Every comparator family of POLICY_SPEC Section 5 with its 48-point grid.

``FAMILIES`` lists the seventeen families in the order of the spec. A grid is a tuple of
dicts with explicit keys; grid order is ``itertools.product`` over the keys in the order
shown below, so the configuration index is stable. Defaults (POLICY_SPEC 7): ``m = 0``,
``k = 0``, ``gamma = 1``, ``W = 24`` (the horizon of F0-R; clipped at H elsewhere),
``O = LLF``, ``B = PES`` (user_flag: ``B = CE``, since with PES it equals sym_margin PES),
``theta = 0``.

* rule families (sym_margin, persistence, uncorr_pes, probe_first, floor, user_flag,
  rwdf_e, rwdf_e_literal): ``O in {EDF, LLF} x B in {CE, PES} x m in {0, 1, 2} x k in {0, 1, 2, 3}``;
* llf_post: ``O x theta in {0, 0.05} x m x k``;
* mpc_ce, mpc_pes: ``W in {2, 4, 8, 24} x m x k``;
* pop_mpc, guarded_mpc_e1: ``W x m x gamma in {0, 0.5, 1, 2}``;
* ce_llf, ce_edf, pes_llf: single points (m = k = 0), not tunable;
* oracle_mpc: not tuned, ``tuned_from = 'guarded_mpc_e1'``; its grid holds only the
  default so the runner can resolve the candidate's frozen configuration.

The MPC constructors are imported inside the ``make`` functions, so this module imports
without ``papere.policies.mpc``.
"""
from __future__ import annotations

import itertools

from .base import Family, PopulationParams
from .beliefs import HMMBelief, PersistBelief
from .rules import (LLFPost, PriorityRule, ProbeFirst, RWDFE, UncorrectableBelief,
                    base_belief, user_flag_rule)

O_VALUES = ("EDF", "LLF")
B_VALUES = ("CE", "PES")
M_VALUES = (0, 1, 2)
K_VALUES = (0, 1, 2, 3)
W_VALUES = (2, 4, 8, 24)
GAMMA_VALUES = (0.0, 0.5, 1.0, 2.0)
THETA_VALUES = (0.0, 0.05)


def _grid(**axes) -> tuple:
    keys = list(axes)
    return tuple(dict(zip(keys, vals)) for vals in itertools.product(*axes.values()))


GRID_OBK = _grid(O=O_VALUES, B=B_VALUES, m=M_VALUES, k=K_VALUES)
GRID_W_M_K = _grid(W=W_VALUES, m=M_VALUES, k=K_VALUES)
GRID_W_M_GAMMA = _grid(W=W_VALUES, m=M_VALUES, gamma=GAMMA_VALUES)
GRID_POST = _grid(O=O_VALUES, theta=THETA_VALUES, m=M_VALUES, k=K_VALUES)

DEFAULT_RULE = {"O": "LLF", "B": "PES", "m": 0, "k": 0}
DEFAULT_USER_FLAG = {"O": "LLF", "B": "CE", "m": 0, "k": 0}
DEFAULT_MPC_K = {"W": 24, "m": 0, "k": 0}
DEFAULT_MPC_GAMMA = {"W": 24, "m": 0, "gamma": 1.0}
DEFAULT_POST = {"O": "LLF", "theta": 0.0, "m": 0, "k": 0}


# ------------------------------------------------------------------------------ makers
def _single(belief_name: str, order: str, name: str):
    def make(cfg: dict, params: PopulationParams):
        return PriorityRule(base_belief(belief_name), order, 0, 0, name=name)
    return make


def _make_sym(cfg, params):
    return PriorityRule(base_belief(cfg["B"]), cfg["O"], cfg["m"], cfg["k"], name="sym_margin")


def _make_persistence(cfg, params):
    return PriorityRule(PersistBelief(cfg["B"]), cfg["O"], cfg["m"], cfg["k"],
                        name="persistence")


def _make_uncorr(cfg, params):
    return PriorityRule(UncorrectableBelief(cfg["B"]), cfg["O"], cfg["m"], cfg["k"],
                        name="uncorr_pes")


def _make_probe(cfg, params):
    return ProbeFirst(base_belief(cfg["B"]), cfg["O"], cfg["m"], cfg["k"], name="probe_first")


def _make_floor(cfg, params):
    return PriorityRule(base_belief(cfg["B"]), cfg["O"], cfg["m"], cfg["k"], name="floor",
                        floor=True)


def _make_mpc_ce(cfg, params):
    from .mpc import mpc_ce
    return mpc_ce(cfg["W"], cfg["m"], cfg["k"], name="mpc_ce")


def _make_mpc_pes(cfg, params):
    from .mpc import mpc_pes
    return mpc_pes(cfg["W"], cfg["m"], cfg["k"], name="mpc_pes")


def _guarded(mode: str, name: str, privileged: bool = False):
    def make(cfg: dict, params: PopulationParams):
        from .mpc import guarded_mpc
        return guarded_mpc(HMMBelief(params, mode), cfg["W"], cfg["m"], cfg["gamma"],
                           name=name, privileged=privileged)
    return make


def _guarded_g0(mode: str, name: str, privileged: bool = False):
    """Guard-ablated variant: forces gamma = 0 while keeping every other frozen setting."""
    def make(cfg: dict, params: PopulationParams):
        from .mpc import guarded_mpc
        return guarded_mpc(HMMBelief(params, mode), cfg["W"], cfg["m"], 0.0,
                           name=name, privileged=privileged)
    return make


def _make_user_flag(cfg, params):
    return user_flag_rule(cfg["B"], cfg["O"], cfg["m"], cfg["k"], name="user_flag")


def _make_rwdf(cfg, params):
    return RWDFE(params, cfg["B"], cfg["O"], cfg["m"], cfg["k"], name="rwdf_e")


def _make_rwdf_literal(cfg, params):
    return RWDFE(params, cfg["B"], cfg["O"], cfg["m"], cfg["k"], name="rwdf_e_literal",
                 literal=True)


def _make_llf_post(cfg, params):
    return LLFPost(params, cfg["O"], cfg["theta"], cfg["m"], cfg["k"], name="llf_post")


def _fam(name, kind, grid, default, make, tuned_from=None) -> Family:
    return Family(name=name, kind=kind, grid=grid, default=dict(default), make=make,
                  tuned_from=tuned_from)


_CE_POINT = {"O": "LLF", "B": "CE", "m": 0, "k": 0}
_CE_EDF_POINT = {"O": "EDF", "B": "CE", "m": 0, "k": 0}
_PES_POINT = {"O": "LLF", "B": "PES", "m": 0, "k": 0}

FAMILIES: list[Family] = [
    _fam("ce_llf", "oblivious", (_CE_POINT,), _CE_POINT, _single("CE", "LLF", "ce_llf")),
    _fam("ce_edf", "oblivious", (_CE_EDF_POINT,), _CE_EDF_POINT, _single("CE", "EDF", "ce_edf")),
    _fam("pes_llf", "oblivious", (_PES_POINT,), _PES_POINT, _single("PES", "LLF", "pes_llf")),
    _fam("sym_margin", "oblivious", GRID_OBK, DEFAULT_RULE, _make_sym),
    _fam("persistence", "oblivious", GRID_OBK, DEFAULT_RULE, _make_persistence),
    _fam("uncorr_pes", "oblivious", GRID_OBK, DEFAULT_RULE, _make_uncorr),
    _fam("probe_first", "oblivious", GRID_OBK, DEFAULT_RULE, _make_probe),
    _fam("floor", "oblivious", GRID_OBK, DEFAULT_RULE, _make_floor),
    _fam("mpc_ce", "oblivious", GRID_W_M_K, DEFAULT_MPC_K, _make_mpc_ce),
    _fam("mpc_pes", "oblivious", GRID_W_M_K, DEFAULT_MPC_K, _make_mpc_pes),
    _fam("pop_mpc", "oblivious", GRID_W_M_GAMMA, DEFAULT_MPC_GAMMA,
         _guarded("population", "pop_mpc")),
    _fam("user_flag", "per_participant", GRID_OBK, DEFAULT_USER_FLAG, _make_user_flag),
    _fam("rwdf_e", "per_participant", GRID_OBK, DEFAULT_RULE, _make_rwdf),
    _fam("rwdf_e_literal", "per_participant", GRID_OBK, DEFAULT_RULE, _make_rwdf_literal),
    _fam("llf_post", "per_participant", GRID_POST, DEFAULT_POST, _make_llf_post),
    _fam("guarded_mpc_e1", "candidate", GRID_W_M_GAMMA, DEFAULT_MPC_GAMMA,
         _guarded("e1", "guarded_mpc_e1")),
    _fam("oracle_mpc", "reference", (DEFAULT_MPC_GAMMA,), DEFAULT_MPC_GAMMA,
         _guarded("oracle", "oracle_mpc", privileged=True), tuned_from="guarded_mpc_e1"),
]

# Post hoc round 3 ablation variants (kept separate from the 17-family spec catalog).
ABLATION_FAMILIES: list[Family] = [
    _fam("guarded_mpc_e1_g0", "candidate", (DEFAULT_MPC_GAMMA,), DEFAULT_MPC_GAMMA,
         _guarded_g0("e1", "guarded_mpc_e1_g0"), tuned_from="guarded_mpc_e1"),
]
ABLATION_BY_NAME: dict[str, Family] = {f.name: f for f in ABLATION_FAMILIES}
