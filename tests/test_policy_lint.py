"""Allow-list lint for policy modules: policies may reach data only through the wrappers.

Everything under ``src/papere/policies/`` is parsed with ``ast``. Imports are checked
against an allow-list; reflection and introspection identifiers are forbidden by name.
This is a guard against accidents and obvious shortcuts, not a sandbox.
"""
import ast
from pathlib import Path

import pytest

POLICY_DIR = Path(__file__).resolve().parents[1] / "src" / "papere" / "policies"

ALLOWED_TOP = {"math", "dataclasses", "typing", "functools", "itertools", "collections",
               "heapq", "abc", "enum", "__future__", "numpy", "scipy", "networkx"}
ALLOWED_PAPERE = {  # module -> permitted imported names
    "papere.infoset": {"InformationSet", "InformationSetViolation", "OracleView",
                       "StaticView", "UNKNOWN"},
    "papere.sim": {"Policy"},
}
POLICIES_PKG = "papere.policies"
FORBIDDEN_SUBMODULES = ("numpy.ctypeslib", "numpy.f2py", "numpy.distutils", "scipy.weave")

FORBIDDEN_ATTRS = {
    "tb_frame", "f_back", "f_locals", "f_globals", "f_builtins", "gi_frame", "cr_frame",
    "__traceback__", "_getframe", "_current_frames", "modules", "bit_generator", "seed_seq",
    "__set__", "__dict__", "__import__", "__globals__", "__builtins__", "__subclasses__",
    "__mro__", "__bases__", "__code__", "__closure__", "__getattribute__", "__reduce__",
    "__reduce_ex__", "ctypeslib",
}
FORBIDDEN_NAMES = FORBIDDEN_ATTRS | {"globals", "locals", "vars", "eval", "exec", "compile",
                                     "open", "breakpoint", "input", "importlib", "sys",
                                     "gc", "inspect", "builtins", "ctypes", "types"}
REFLECTION = {"getattr", "setattr", "delattr", "hasattr"}
# text check (catches names hidden in strings or comments); "modules" is too generic for it
TEXT_PATTERNS = sorted((FORBIDDEN_ATTRS - {"modules", "ctypeslib"})
                       | {"object.__setattr__", "super().__setattr__"})


def _resolve(node: ast.ImportFrom, module_name: str) -> str:
    """Absolute module name of a from-import (handles relative imports)."""
    if node.level == 0:
        return node.module or ""
    parts = module_name.split(".")
    base = parts[:len(parts) - node.level] if node.level <= len(parts) else []
    return ".".join(base + ([node.module] if node.module else []))


def _check_import(mod: str, names: list[str], problems: list[str]) -> None:
    top = mod.split(".")[0]
    if mod == POLICIES_PKG or mod.startswith(POLICIES_PKG + "."):
        return
    if top == "papere":
        allowed = ALLOWED_PAPERE.get(mod)
        if allowed is None or not names or any(n not in allowed for n in names):
            problems.append(f"papere import not allowed: {mod} {names}")
        return
    if top not in ALLOWED_TOP or any(mod == m or mod.startswith(m + ".")
                                     for m in FORBIDDEN_SUBMODULES):
        problems.append(f"import not allowed: {mod}")


def lint_source(src: str, module_name: str = "papere.policies.x") -> list[str]:
    problems: list[str] = []
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                if a.name.split(".")[0] == "papere" and not a.name.startswith(POLICIES_PKG):
                    problems.append(f"plain import of papere module: {a.name}")
                else:
                    _check_import(a.name, [], problems)
        elif isinstance(node, ast.ImportFrom):
            mod = _resolve(node, module_name)
            names = [a.name for a in node.names]
            if "*" in names:
                problems.append(f"star import from {mod}")
            _check_import(mod, names, problems)
            if mod == "papere" or mod == "":
                problems.append("from papere import ...")
        elif isinstance(node, ast.Attribute):
            if node.attr in FORBIDDEN_ATTRS:
                problems.append(f"attribute .{node.attr}")
            if node.attr == "__setattr__":
                v = node.value
                if (isinstance(v, ast.Name) and v.id == "object") or \
                        (isinstance(v, ast.Call) and isinstance(v.func, ast.Name)
                         and v.func.id == "super"):
                    problems.append("__setattr__ on object/super")
        elif isinstance(node, ast.Name):
            if node.id in FORBIDDEN_NAMES:
                problems.append(f"name {node.id}")
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name) \
                and node.func.id in REFLECTION:
            arg = node.args[1] if len(node.args) > 1 else None
            if not (isinstance(arg, ast.Constant) and isinstance(arg.value, str)):
                problems.append(f"{node.func.id}() with a non-literal name")
            elif arg.value in FORBIDDEN_ATTRS or arg.value in FORBIDDEN_NAMES:
                problems.append(f"{node.func.id}() of forbidden name {arg.value!r}")
    for pat in TEXT_PATTERNS:
        if pat in src:
            problems.append(f"text:{pat}")
    return sorted(set(problems))


def policy_files():
    return sorted(POLICY_DIR.rglob("*.py"))


def test_policy_package_exists():
    assert (POLICY_DIR / "__init__.py").exists()


@pytest.mark.parametrize("path", policy_files(), ids=lambda p: p.name)
def test_policy_modules_are_clean(path):
    assert lint_source(path.read_text(), "papere.policies." + path.stem) == []


PLANTED = {
    # reviewer's variants
    "frame_walk": "def f(e):\n    return e.__traceback__.tb_frame.f_back.f_locals",
    "importlib": "import importlib\nm = importlib.import_module('papere.generator')",
    "from_importlib": "from importlib import import_module",
    "sys_modules": "import sys\nx = sys.modules['papere.generator']",
    "builtins_import": "import builtins\nbuiltins.__import__('papere.generator')",
    "import_papere_sim": "import papere.sim\nx = papere.sim.policy_rng",
    "import_papere_infoset": "import papere.infoset",
    "from_papere_sim_other": "from papere.sim import policy_rng",
    "from_papere_sim_simulate": "from papere.sim import Policy, simulate",
    "getattr_concat": "def f(rng):\n    return getattr(rng, 'bit_' + 'generator')",
    "getattr_literal_forbidden": "def f(rng):\n    return getattr(rng, 'bit_generator')",
    "getattr_var": "def f(rng, n):\n    return getattr(rng, n)",
    "setattr_var": "def f(o, n):\n    setattr(o, n, 1)",
    "delattr_var": "def f(o, n):\n    delattr(o, n)",
    "super_setattr": "class A:\n    def f(self):\n        super().__setattr__('x', 1)",
    "object_setattr": "object.__setattr__(view, 'x', 1)",
    "slot_set": "def f(sv):\n    type(sv).__dict__['delta_b'].__set__(sv, -1)",
    "slot_set_only": "def f(d, sv):\n    d.__set__(sv, -1)",
    "current_frames": "import sys\nsys._current_frames()",
    "getframe": "import sys\nsys._getframe(1)",
    "gc": "import gc\ngc.get_objects()",
    "from_gc": "from gc import get_objects",
    "inspect": "import inspect",
    "from_inspect": "from inspect import currentframe",
    "ctypes": "import ctypes",
    "types": "import types",
    "os": "import os",
    "pickle": "import pickle",
    "numpy_ctypeslib": "import numpy.ctypeslib",
    "np_ctypeslib_attr": "import numpy as np\nx = np.ctypeslib",
    # earlier variants
    "generator": "import papere.generator",
    "instance_alias": "import papere.instance as inst",
    "from_generator": "from papere.generator import policy_rng",
    "from_papere": "from papere import generator",
    "from_instance": "from papere.instance import Instance",
    "relative_instance": "from ..instance import Instance",
    "relative_generator": "from ..generator import stream",
    "relative_pkg": "from .. import instance",
    "bit_generator": "def f(rng):\n    return rng.bit_generator.state",
    "seed_seq": "def f(rng):\n    return rng.bit_generator.seed_seq",
    "eval": "eval('1')",
    "dunder_import": "__import__('os')",
    "globals_of_function": "def f():\n    pass\nx = f.__globals__",
    "star": "from numpy import *",
    "infoset_unlisted_name": "from papere.infoset import Instance",
    "open": "open('/etc/passwd')",
}


@pytest.mark.parametrize("name", sorted(PLANTED))
def test_linter_flags_planted_pattern(name, tmp_path):
    f = tmp_path / "bad.py"
    f.write_text(PLANTED[name] + "\n")
    assert lint_source(f.read_text(), "papere.policies.bad"), name


def test_linter_accepts_clean_policies(tmp_path):
    ok = ("from __future__ import annotations\nimport math\nimport numpy as np\n"
          "from collections import defaultdict\nfrom dataclasses import dataclass\n"
          "from scipy.optimize import linprog\n"
          "from papere.infoset import InformationSet, StaticView, OracleView, UNKNOWN\n"
          "from papere.sim import Policy\nfrom .base import Helper\nfrom . import util\n"
          "from papere.policies.other import X\n\n\nclass P:\n    name = 'p'\n"
          "    privileged = False\n"
          "    def reset(self, static_view, rng, oracle=None):\n        self.rng = rng\n"
          "    def act(self, view):\n        n = getattr(view, 'N')\n"
          "        return np.zeros(n, dtype=np.int64)\n")
    f = tmp_path / "good.py"
    f.write_text(ok)
    assert lint_source(f.read_text(), "papere.policies.p") == []
