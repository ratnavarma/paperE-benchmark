"""Seed-rule guard (docs/SEED_LEDGER.md): every test uses seeds 60000-60049 only.

An autouse fixture wraps ``generate_f0r``, ``generate_kcopy`` and ``policy_rng`` so that a call
with a seed outside 60000-60049 raises ``SeedRuleViolation``.  The wrappers are installed in
``papere.generator`` and in every already-imported module (src, scripts, tests) that bound one
of these functions by name at import time.  A test that must exercise refusal or plumbing with
other seed numbers opts out with ``@pytest.mark.seed_rule_exempt``; an exempt test must not
generate instances on those seeds (runner refusal tests refuse before generating).
"""
from __future__ import annotations

import functools
import sys

import pytest

SEED_LO, SEED_HI = 60000, 60049
GUARDED = ("generate_f0r", "generate_kcopy", "policy_rng")


class SeedRuleViolation(AssertionError):
    """A test generated an instance or policy stream on a seed outside 60000-60049."""


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "seed_rule_exempt: the test may pass seeds outside 60000-60049 (refusal or "
                   "plumbing tests); it must not generate instances on them")


def _guard(fn):
    @functools.wraps(fn)
    def wrapper(seed, *args, **kwargs):
        s = int(seed)
        if not SEED_LO <= s <= SEED_HI:
            raise SeedRuleViolation(
                f"{fn.__name__}(seed={s}): tests may use seeds {SEED_LO}-{SEED_HI} only "
                "(docs/SEED_LEDGER.md)")
        return fn(seed, *args, **kwargs)
    wrapper.__seed_rule_original__ = fn
    return wrapper


@pytest.fixture(autouse=True)
def seed_rule_guard(request, monkeypatch):
    if request.node.get_closest_marker("seed_rule_exempt"):
        yield
        return
    from papere import generator
    wrappers = {}
    for name in GUARDED:
        orig = getattr(generator, name)
        orig = getattr(orig, "__seed_rule_original__", orig)
        wrappers[orig] = _guard(orig)
    for mod in list(sys.modules.values()):
        if mod is None or not hasattr(mod, "__dict__"):
            continue
        try:
            items = list(vars(mod).items())
        except Exception:
            continue
        for attr, val in items:
            try:
                key = getattr(val, "__seed_rule_original__", val)
                w = wrappers.get(key)
            except TypeError:                       # unhashable module attribute
                continue
            if w is not None and val is not w:
                monkeypatch.setattr(mod, attr, w)
    yield


# ------------------------------------------------------------------ many-draw helpers
def draw(j: int) -> tuple[int, dict | None]:
    """The j-th independent draw, from tuning seeds 60000-60049 only.

    A test that needs more than 50 independent instances uses the 50 tuning seeds times the
    generator's test-only ``stream_salt`` (every named child stream re-keyed by ``j // 50``), so
    draw j is ``(60000 + j % 50, salt j // 50)``.  Salt 0 is the unsalted generator, so the
    first 50 draws are the plain tuning instances.  Distinct (seed, salt) pairs give
    independent child streams.
    """
    from papere.generator import _STREAM_IDS
    salt = j // 50
    return 60000 + j % 50, ({name: salt for name in _STREAM_IDS} if salt else None)
