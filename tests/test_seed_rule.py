"""Seed rule (docs/SEED_LEDGER.md, disclosure of October 20, 2026): every test uses seeds
60000-60049 only.  The development, validation, scaling and confirmation ranges are touched
only by ``run_study.py``.

This file scans the text of every ``tests/*.py`` for an integer literal inside one of the
forbidden ranges and fails if it finds one.  Digit runs inside strings and comments count too
(``"--seeds 61000-61000"`` is a violation).  The single exception is ``test_runner.py``: a
line that carries the comment ``# seed-rule: refusal-test`` may name a ledger range, because
the runner's seed-REFUSAL logic is tested by asserting that those numbers are refused.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

TESTS = Path(__file__).resolve().parent
FORBIDDEN = ((61000, 61099), (61500, 61599), (62000, 62099), (63000, 63019), (500000, 500999))
MARKER = "# seed-rule: refusal-test"
MARKER_FILES = {"test_runner.py", "test_negative_controls.py"}


def forbidden_in(line: str) -> list[int]:
    out = []
    for m in re.finditer(r"(?<![\d_])\d[\d_]*(?![\d_])", line):
        n = int(m.group(0).replace("_", ""))
        if any(lo <= n <= hi for lo, hi in FORBIDDEN):
            out.append(n)
    return out


def violations(path: Path, honour_marker: bool) -> list[tuple[int, int, str]]:
    found = []
    for lineno, line in enumerate(path.read_text().splitlines(), 1):
        if honour_marker and MARKER in line:
            continue
        for n in forbidden_in(line):
            found.append((lineno, n, line.strip()))
    return found


def test_scanner_detects_forbidden_literals():
    # guard against a vacuous scanner: every boundary of every forbidden range is caught
    for lo, hi in FORBIDDEN:
        for n in (lo, lo + 1, hi):
            assert forbidden_in(f"seed = {n}") == [n]
            assert forbidden_in(f"range({n}, {n + 1})") in ([n], [n, n + 1])
        assert forbidden_in(f"seed = {lo - 1}") == [] and forbidden_in(f"seed = {hi + 1}") == []
    assert forbidden_in('"--seeds", "61000-61019"') == [61000, 61019]
    assert forbidden_in("seed = 61_000") == [61000]
    assert forbidden_in("x = 160000 + 1610000") == []      # longer numbers are not matches
    assert forbidden_in("seed = 60049 + 60000") == []      # the tuning range is allowed


def test_scanner_honours_marker_only_where_allowed(tmp_path):
    f = tmp_path / "t.py"
    f.write_text(f"a = 61000  {MARKER}\nb = 61001\n")
    assert [v[0] for v in violations(f, honour_marker=True)] == [2]
    assert [v[0] for v in violations(f, honour_marker=False)] == [1, 2]


def test_test_files_are_found():
    files = sorted(TESTS.glob("test_*.py"))
    assert len(files) >= 10 and TESTS / "test_runner.py" in files


def _files():
    return sorted(p for p in TESTS.glob("*.py") if p.name != Path(__file__).name)


@pytest.mark.parametrize("path", _files(), ids=lambda p: p.name)
def test_no_forbidden_seed_literal(path):
    bad = violations(path, honour_marker=path.name in MARKER_FILES)
    assert not bad, (
        f"{path.name}: seeds outside 60000-60049 (docs/SEED_LEDGER.md seed rule) at "
        + "; ".join(f"line {ln}: {n}" for ln, n, _ in bad))


def test_runtime_guard_raises_outside_the_tuning_seeds():
    """The conftest autouse guard is live: instance and policy-stream generation on a seed
    outside 60000-60049 (an earlier Track E seed, a development seed) raises."""
    from dataclasses import replace

    from conftest import SeedRuleViolation
    from papere.generator import (F0R_CELLS, KCOPY_CELLS, generate_f0r, generate_kcopy,
                                  policy_rng)
    from papere.runner import generate_f0r as runner_generate_f0r   # import-time binding too

    cell = F0R_CELLS[0]
    for bad in (5, 0, 79, 59999, 60050, 61000, 500000):
        for fn in (generate_f0r, runner_generate_f0r):
            with pytest.raises(SeedRuleViolation):
                fn(bad, cell)
        with pytest.raises(SeedRuleViolation):
            policy_rng(bad, "cell", "pol")
        with pytest.raises(SeedRuleViolation):
            generate_kcopy(bad, KCOPY_CELLS[0], 1)
    for good in (60000, 60049):
        assert generate_f0r(good, cell).seed == good
        assert runner_generate_f0r(good, replace(cell)).seed == good
        policy_rng(good, "cell", "pol")


@pytest.mark.seed_rule_exempt
def test_exempt_marker_disables_the_guard():
    # no instance is generated here: just check that the guard is not installed
    from papere.generator import generate_f0r, generate_kcopy, policy_rng
    for fn in (generate_f0r, generate_kcopy, policy_rng):
        assert not hasattr(fn, "__seed_rule_original__")


def test_runner_marked_lines_are_refusal_checks_only():
    """Marked lines in test_runner.py must be refusal/parse plumbing: none may start a run
    that is expected to succeed on a ledger seed, so a marked line never calls ``run(`` or
    ``frozen_run(`` / ``tune(`` outside of a refusal context."""
    src = (TESTS / "test_runner.py").read_text().splitlines()
    for lineno, line in enumerate(src, 1):
        if MARKER in line:
            assert not re.search(r"\b(frozen_run|tune|freeze)\(|\brun\(", line), (lineno, line)
