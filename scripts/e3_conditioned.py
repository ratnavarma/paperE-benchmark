"""E3 diagnostic conditioned on the realized stuck draws (added after DEV_REPORT_E).

Label: "diagnostic, conditioned on realized stuck draws, added after DEV_REPORT_E";
development. It is not a pre-registered endpoint and does not replace E3.

Why. On the K-copy validation seeds 61500-61599 every E3 point passes its simultaneous
interval, but all pointwise misses and all Proposition 3 points sit below prediction
(DEV_REPORT_E Section 8). Common random numbers share the stuck draws across cells, so a
seed set that happens to realize fewer stuck A copies than expected shifts every point the
same way. This script removes that common mode: per seed it computes the expected residual
of each policy *given* the realized stuck pattern of the scored event and the realized
prior-event stuck history, over the policy's own tie-break randomness only, and compares
the measured residual with that conditional expectation.

What is read. For each K-copy cell and seed the instance is regenerated with
``generate_kcopy(seed, cell, K=8)`` -- generation only, deterministic, no policy is run.
From it the script reads the class of each participant (which twins are A copies), the cap
group (copy index under the per-copy cap), the scored-event stuck pattern
(``availability()`` with no floor, slot 0) and ``prior_stuck``. Nothing else hidden is used.
Measured residuals come from ``results/kcopy_dev/rows.jsonl`` (``R_abs_u``).

Decision laws on I_K (MECHANISM_E_v2 3.6, 3.9; tests/test_mpc.py I_K tests). Every policy
serves every twin at slot 0 and every D copy at slot 1, and fills the spare slot-1 cap of
each cap group (pooled: c; per-copy: c/K per copy) with slot-1 hedges on twins, at most one
per twin. Hedges go to the twins of highest priority, ties uniformly at random (the MPC's
i.i.d. arc perturbation), so the hedge set is uniform over the priority-maximizing sets:
  * pop_mpc   -- one population rate for all: priority equal for every twin;
  * oracle_mpc-- knows classes, not the realized stuck state: priority A > B;
  * guarded_mpc_e1 -- Beta-Bernoulli on the own prior stuck count, strictly increasing in
    the count: priority = count (B copies are never stuck, count 0).
The realized residual of a hedge set is the number of stuck A copies left unhedged.
Given the realization the conditional expectation is a sum of hypergeometric means
(closed forms ``cond_pop``, ``cond_oracle``, ``cond_e1`` below); each is checked against
exhaustive enumeration of the uniform hedge subsets on small K (``enumerate_law``, built on
``prop_enum.simulate_residual`` and ``prop_enum.is_feasible``), in tests and in this run.

Usage: uv run python scripts/e3_conditioned.py [--rows results/kcopy_dev/rows.jsonl]
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import itertools
import json
import math
import subprocess
import sys
import time
from datetime import datetime, timezone
from fractions import Fraction
from pathlib import Path
from typing import Iterable, Sequence

import numpy as np

from papere import prop_enum as pe
from papere.generator import KCOPY_CELLS, generate_kcopy
from papere.instance import Cell

ROOT = Path(__file__).resolve().parents[1]
LABEL = "diagnostic, conditioned on realized stuck draws, added after DEV_REPORT_E"
STATUS = "development"
K_STUDY = 8
SEED_LO, SEED_HI = 61500, 61599
POLICIES = ("pop_mpc", "oracle_mpc", "guarded_mpc_e1")
SHORT = {"pop_mpc": "pop", "oracle_mpc": "oracle", "guarded_mpc_e1": "e1"}
CHECKS = ("R_pop", "gap_oracle", "gap_e1")
METRIC = "R_abs_u"


# =========================================================================================
# Realization of one instance (what is conditioned on)
# =========================================================================================
class Realization:
    """Twins of one K-copy instance by cap group, with stuck flag and prior stuck count.

    ``groups`` is a list over cap groups; each group is a list of twins
    ``(role, stuck, count)`` with role "A" or "B". Pooled: one group of 2K twins.
    Per-copy: K groups {A_k, B_k}. ``budget[g]`` is the spare slot-1 cap of group g after
    its D copies, capped at the number of twins in the group.
    """

    def __init__(self, groups: list[list[tuple[str, int, int]]], budget: list[int],
                 K: int, c: int, cap_mode: str):
        self.groups, self.budget, self.K, self.c, self.cap_mode = groups, budget, K, c, cap_mode

    @property
    def A(self) -> list[tuple[int, int]]:
        return [(s, n) for g in self.groups for (r, s, n) in g if r == "A"]

    @property
    def S(self) -> int:
        """Realized number of stuck A copies in the scored event."""
        return sum(s for s, _ in self.A)

    @property
    def I(self) -> int:
        """A copies with at least one prior stuck outcome (identified)."""
        return sum(1 for _, n in self.A if n > 0)

    @property
    def S_unid(self) -> int:
        """Stuck A copies that are not identified."""
        return sum(s for s, n in self.A if n == 0)

    @classmethod
    def abstract(cls, K: int, c: int, cap_mode: str, stuck: Sequence[int],
                 counts: Sequence[int]) -> "Realization":
        """From an A-copy stuck pattern and prior counts in prop_enum order (copy k = A_k, B_k)."""
        if cap_mode == "pooled":
            g = [("A", int(stuck[k]), int(counts[k])) for k in range(K)]
            g += [("B", 0, 0) for _ in range(K)]
            return cls([g], [min(c, 2 * K)], K, c, cap_mode)
        if c % K:
            raise ValueError("per-copy cap needs c/K integer")
        groups = [[("A", int(stuck[k]), int(counts[k])), ("B", 0, 0)] for k in range(K)]
        return cls(groups, [min(c // K, 2)] * K, K, c, cap_mode)

    @classmethod
    def from_instance(cls, inst, K: int) -> "Realization":
        """Read class, cap group, scored stuck pattern (no floor) and prior stuck counts."""
        cell = inst.cell
        c = int(round(cell.c))
        if inst.N != 3 * K:
            raise ValueError("instance size does not match K")
        stuck0 = inst.availability()[:, 0] == 0          # no floor
        counts = inst.prior_stuck.sum(axis=1).astype(int)
        cls_ = np.asarray(inst.cls)
        if cls_[(cls_ != 1)].size and stuck0[cls_ != 1].any():
            raise AssertionError("a B or D copy is stuck in the K-copy family")
        if (counts[cls_ != 1] > 0).any():
            raise AssertionError("a B or D copy has a prior stuck outcome")
        twins = np.flatnonzero(cls_ != 2)
        grp = np.asarray(inst.group)
        gids = sorted(set(grp[twins].tolist()))
        groups, budget = [], []
        for g in gids:
            members = [i for i in twins.tolist() if grp[i] == g]
            groups.append([("A" if cls_[i] == 1 else "B", int(stuck0[i]), int(counts[i]))
                           for i in members])
            nD = int(((cls_ == 2) & (grp == g)).sum())
            spare = int(math.floor(float(inst.L[g, 1]) - nD + 1e-9))
            budget.append(max(0, min(spare, len(members))))
        if cell.cap_mode == "pooled":
            if len(groups) != 1 or budget[0] != min(c, 2 * K):
                raise AssertionError("pooled instance does not have one group with spare c")
        else:
            if len(groups) != K or any(sorted(r for r, _, _ in g) != ["A", "B"] for g in groups):
                raise AssertionError("per-copy instance groups are not {A_k, B_k}")
            if any(b != min(c // K, 2) for b in budget):
                raise AssertionError("per-copy spare is not c/K")
        return cls(groups, budget, K, c, cell.cap_mode)


def priority(policy: str, role: str, count: int) -> int:
    """Hedge priority of a twin under each policy's decision law (higher first)."""
    if policy == "pop_mpc":
        return 0
    if policy == "oracle_mpc":
        return 1 if role == "A" else 0
    if policy == "guarded_mpc_e1":
        return count
    raise ValueError(policy)


# =========================================================================================
# Closed forms (hypergeometric), exact Fractions
# =========================================================================================
def hyper_unhedged(g: int, s: int, r: int) -> tuple[Fraction, Fraction]:
    """Mean and variance of the stuck twins left unhedged when r of g twins (s stuck) are
    hedged uniformly at random: s - X with X ~ Hypergeometric(g, s, r)."""
    if g == 0:
        return Fraction(0), Fraction(0)
    mean = Fraction(s * (g - r), g)
    var = Fraction(0) if g == 1 else Fraction(r * s * (g - s) * (g - r), g * g * (g - 1))
    return mean, var


def greedy_moments(real: Realization, policy: str) -> tuple[Fraction, Fraction]:
    """E and Var of the residual given the realization: per group, hedge the levels of
    highest priority first; the boundary level gets a uniform random subset."""
    mean, var = Fraction(0), Fraction(0)
    for twins, h in zip(real.groups, real.budget):
        levels: dict[int, list[int]] = {}
        for role, s, n in twins:
            levels.setdefault(priority(policy, role, n), []).append(s)
        left = h
        for p in sorted(levels, reverse=True):
            ss = levels[p]
            r = min(left, len(ss))
            m, v = hyper_unhedged(len(ss), sum(ss), r)
            mean, var, left = mean + m, var + v, left - r
    return mean, var


def cond_pop(K: int, c: int, S: int) -> Fraction:
    """pop_mpc: min(c, 2K) hedges spread uniformly over the 2K twins (pooled) or c/K per
    copy over its 2 twins (per-copy): E[R | S] = S (2K - min(c, 2K)) / (2K), both caps."""
    return Fraction(S * (2 * K - min(c, 2 * K)), 2 * K)


def cond_oracle(K: int, c: int, S: int) -> Fraction:
    """oracle_mpc: min(c, K) of the K A copies hedged uniformly (pooled); per-copy c/K >= 1
    hedges every A: E[R | S] = S (K - min(c, K)) / K, both caps."""
    return Fraction(S * (K - min(c, K)), K)


def cond_e1(K: int, c: int, cap_mode: str, A: Sequence[tuple[int, int]]) -> Fraction:
    """guarded_mpc_e1 given the realized (stuck, prior count) of every A copy.

    Pooled: h = min(c, 2K) hedges go to A copies in decreasing prior count; the count level
    n_b where the hedges run out gets a uniform random subset. With h_b hedges left at that
    level (g_b twins, s_b stuck; level 0 holds the K B copies too),
        E[R] = sum_{n < n_b} s_n + s_b (g_b - h_b) / g_b.
    Per-copy (A given as copy-ordered list, the copy's B has count 0): spare c/K = 0 leaves
    the stuck A; 2 covers both; 1 hedges an identified A, else one of the two at random:
        E[R] = [c = 0] S + [c = K] S_unid / 2.
    """
    if cap_mode == "per_copy":
        S = sum(s for s, _ in A)
        S_unid = sum(s for s, n in A if n == 0)
        sp = min(c // K, 2)
        return Fraction(S) if sp == 0 else (Fraction(S_unid, 2) if sp == 1 else Fraction(0))
    h = min(c, 2 * K)
    total = Fraction(0)
    counts = sorted({n for _, n in A if n > 0}, reverse=True)
    for n in counts:
        lev = [s for s, m in A if m == n]
        r = min(h, len(lev))
        total += Fraction(sum(lev) * (len(lev) - r), len(lev))
        h -= r
    g0 = sum(1 for _, n in A if n == 0) + K               # unidentified A plus every B
    s0 = sum(s for s, n in A if n == 0)
    r = min(h, g0)
    return total + Fraction(s0 * (g0 - r), g0)


def cond_e1_at_K(K: int, cap_mode: str, I: int, S_unid: int) -> Fraction:
    """Proposition 3 given the realization, c = K: pooled S_unid K / (2K - I) (every
    identified A hedged, K - I hedges over the 2K - I unidentified twins); per-copy
    S_unid / 2."""
    if cap_mode == "pooled":
        return Fraction(S_unid * K, 2 * K - I)
    return Fraction(S_unid, 2)


def cond_closed(real: Realization, policy: str) -> Fraction:
    if policy == "pop_mpc":
        return cond_pop(real.K, real.c, real.S)
    if policy == "oracle_mpc":
        return cond_oracle(real.K, real.c, real.S)
    if policy == "guarded_mpc_e1":
        if real.cap_mode == "per_copy":
            A = [next((s, n) for r, s, n in g if r == "A") for g in real.groups]
        else:
            A = real.A
        return cond_e1(real.K, real.c, real.cap_mode, A)
    raise ValueError(policy)


# =========================================================================================
# Exhaustive enumeration of the decision law (verification, small K)
# =========================================================================================
def enumerate_law(K: int, c: int, cap_mode: str, policy: str, stuck: Sequence[int],
                  counts: Sequence[int]) -> tuple[Fraction, Fraction, int]:
    """E[R], E[R^2] and support size of the policy's law given the realization, by brute force.

    Participant order is prop_enum's (A_0..A_{K-1}, B_0..B_{K-1}, D_0..D_{K-1}); copy k is
    {A_k, B_k, D_k}. Every hedge set that fills each group's spare slot-1 cap is listed
    explicitly (pooled: every h-subset of the 2K twins; per-copy: every product of per-copy
    subsets); the law is uniform over those of maximal total priority. Each schedule (all
    twins at slot 0, every D at slot 1, the hedged twins also at slot 1) is checked with
    ``prop_enum.is_feasible`` and scored with ``prop_enum.simulate_residual``.
    """
    twins = list(range(2 * K))
    role = ["A"] * K + ["B"] * K
    cnt = list(counts) + [0] * K
    prio = [priority(policy, role[j], cnt[j]) for j in twins]
    if cap_mode == "pooled":
        h = min(c, 2 * K)
        sets = [frozenset(s) for s in itertools.combinations(twins, h)]
    else:
        if c % K:
            raise ValueError("per-copy cap needs c/K integer")
        h = min(c // K, 2)
        per = [list(itertools.combinations((k, K + k), h)) for k in range(K)]
        sets = [frozenset(j for part in combo for j in part) for combo in itertools.product(*per)]
    best = max(sum(prio[j] for j in s) for s in sets)
    law = [s for s in sets if sum(prio[j] for j in s) == best]
    m1 = m2 = Fraction(0)
    w = Fraction(1, len(law))
    for s in law:
        sigma = tuple((1, 1 if j in s else 0) for j in twins) + tuple((0, 1) for _ in range(K))
        if not pe.is_feasible(sigma, K, c, cap_mode):
            raise AssertionError("enumerated schedule breaks a cap")
        R = pe.simulate_residual(sigma, stuck, K)
        m1 += w * R
        m2 += w * R * R
    return m1, m2, len(law)


def c_values(K: int, cap_mode: str) -> list[int]:
    return list(range(0, 2 * K + 1)) if cap_mode == "pooled" else [0, K, 2 * K]


def verify_closed_forms(Ks: Iterable[int], max_count: int = 3) -> dict:
    """Closed forms against exhaustive enumeration for every stuck pattern, every prior
    count vector (counts 0..max_count per A copy), every c and both caps; exact equality.
    pop and oracle are checked on every count vector too (their law ignores history)."""
    out = {"cases": 0, "mismatches": [], "by_form": {}, "K": list(Ks), "max_count": max_count}
    for K in out["K"]:
        for cap_mode in ("pooled", "per_copy"):
            for c in c_values(K, cap_mode):
                for stuck in itertools.product((0, 1), repeat=K):
                    S = sum(stuck)
                    for counts in itertools.product(range(max_count + 1), repeat=K):
                        real = Realization.abstract(K, c, cap_mode, stuck, counts)
                        I = sum(1 for n in counts if n > 0)
                        S_un = sum(s for s, n in zip(stuck, counts) if n == 0)
                        for pol in POLICIES:
                            m1, m2, _ = enumerate_law(K, c, cap_mode, pol, stuck, counts)
                            var = m2 - m1 * m1
                            gm, gv = greedy_moments(real, pol)
                            cf = {"pop_mpc": lambda: cond_pop(K, c, S),
                                  "oracle_mpc": lambda: cond_oracle(K, c, S),
                                  "guarded_mpc_e1": lambda: cond_e1(K, c, cap_mode,
                                                                    list(zip(stuck, counts)))}[pol]()
                            checks = {f"cond_{SHORT[pol]}": cf, f"greedy_mean_{SHORT[pol]}": gm,
                                      f"greedy_var_{SHORT[pol]}": gv}
                            tgt = {f"cond_{SHORT[pol]}": m1, f"greedy_mean_{SHORT[pol]}": m1,
                                   f"greedy_var_{SHORT[pol]}": var}
                            if pol == "guarded_mpc_e1" and c == K:
                                checks["cond_e1_at_K"] = cond_e1_at_K(K, cap_mode, I, S_un)
                                tgt["cond_e1_at_K"] = m1
                            for name, v in checks.items():
                                d = out["by_form"].setdefault(name, {"cases": 0, "equal": 0})
                                d["cases"] += 1
                                out["cases"] += 1
                                if v == tgt[name]:
                                    d["equal"] += 1
                                else:
                                    out["mismatches"].append(dict(
                                        form=name, K=K, cap_mode=cap_mode, c=c,
                                        stuck=list(stuck), counts=list(counts),
                                        closed=str(v), enumerated=str(tgt[name])))
    out["all_equal"] = not out["mismatches"]
    return out


def verify_total_expectation(Ks: Iterable[int], qs: Sequence[Fraction], Ms: Sequence[int]) -> dict:
    """Averaging the conditional closed forms over the stuck and history law recovers the
    unconditional closed forms of prop_enum (closed_oblivious, closed_posterior,
    closed_prop3_*); exact equality."""
    res = {"cases": 0, "equal": 0, "mismatches": []}
    for K in Ks:
        for q in qs:
            pats = pe.stuck_patterns(K, q)
            for cap_mode in ("pooled", "per_copy"):
                for c in c_values(K, cap_mode):
                    pop = sum((p * cond_pop(K, c, sum(s)) for s, p in pats), Fraction(0))
                    orc = sum((p * cond_oracle(K, c, sum(s)) for s, p in pats), Fraction(0))
                    pairs = [("pop", pop, pe.closed_oblivious(K, q, c)),
                             ("oracle", orc, pe.closed_posterior(K, q, c))]
                    if c == K:
                        for M in Ms:
                            e = Fraction(0)
                            for hist, ph in pe.histories(K, M, q, "count"):
                                counts = hist[:K]
                                for s, p in pats:
                                    e += ph * p * cond_e1(K, c, cap_mode, list(zip(s, counts)))
                            tgt = (pe.closed_prop3_pooled if cap_mode == "pooled"
                                   else pe.closed_prop3_per_copy)(K, q, M)
                            pairs.append((f"e1_M{M}", e, tgt))
                    for name, a, b in pairs:
                        res["cases"] += 1
                        if a == b:
                            res["equal"] += 1
                        else:
                            res["mismatches"].append(dict(form=name, K=K, q=str(q), c=c,
                                                          cap_mode=cap_mode, got=str(a), want=str(b)))
    res["all_equal"] = not res["mismatches"]
    return res


# =========================================================================================
# Rows, statistics, provenance
# =========================================================================================
def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def git_info() -> dict:
    def run(*a):
        return subprocess.run(["git", "-C", str(ROOT), *a], capture_output=True, text=True,
                              timeout=60)
    try:
        c = run("rev-parse", "HEAD")
        s = run("status", "--porcelain", "--untracked-files=no")
        return {"commit": c.stdout.strip() or None, "dirty": bool(s.stdout.strip())}
    except (OSError, subprocess.SubprocessError):
        return {"commit": None, "dirty": None}


def load_rows(path: Path, cell_ids: set[str], seeds: Sequence[int]) -> dict:
    """R_abs_u per (cell_id, policy, seed) for the three E3 policies; refuses on gaps."""
    opener = gzip.open if path.suffix == ".gz" else open
    keys = [f'"policy":"{p}"' for p in POLICIES]
    vals: dict[tuple[str, str], dict[int, float]] = {}
    n = 0
    with opener(path, "rt") as f:
        for line in f:
            if not any(k in line for k in keys):
                continue
            r = json.loads(line)
            if r.get("policy") not in POLICIES or r.get("cell_id") not in cell_ids:
                continue
            if r.get("study_family") != "KCOPY" or r.get("mode") != "frozen":
                raise SystemExit(f"unexpected row family/mode: {r.get('study_family')}/{r.get('mode')}")
            s = int(r["seed"])
            if not SEED_LO <= s <= SEED_HI:
                raise SystemExit(f"row seed {s} outside {SEED_LO}-{SEED_HI}")
            d = vals.setdefault((r["cell_id"], r["policy"]), {})
            if s in d:
                raise SystemExit(f"duplicate row {r['cell_id']} {r['policy']} {s}")
            d[s] = float(r[METRIC])
            n += 1
    for cid in cell_ids:
        for p in POLICIES:
            got = vals.get((cid, p), {})
            if sorted(got) != list(seeds):
                raise SystemExit(f"missing rows for {cid} {p}: {len(got)} of {len(seeds)} seeds")
    return {"vals": vals, "n_rows": n}


def t_interval(mean: float, sd: float, n: int, level: float) -> tuple[float, float]:
    from scipy import stats as sps
    if n < 2:
        return math.nan, math.nan
    h = float(sps.t.ppf(0.5 + level / 2.0, n - 1)) * sd / math.sqrt(n)
    return mean - h, mean + h


def series_stats(x: Sequence[Fraction], level_sim: float) -> dict:
    """Exact mean, sd and Student-t intervals (simultaneous level and pointwise 95%)."""
    n = len(x)
    mean = sum(x, Fraction(0)) / n
    arr = np.array([float(v) for v in x])
    sd = float(np.std(arr, ddof=1)) if n > 1 else math.nan
    lo_s, hi_s = t_interval(float(mean), sd, n, level_sim)
    lo_p, hi_p = t_interval(float(mean), sd, n, 0.95)
    return {"mean": float(mean), "mean_exact": str(mean), "sd": sd, "se": sd / math.sqrt(n),
            "sim_lo": lo_s, "sim_hi": hi_s, "pw_lo": lo_p, "pw_hi": hi_p,
            "identically_zero": all(v == 0 for v in x)}


def contains(st: dict, v: float, which: str, tol: float = 1e-9) -> bool:
    if st["identically_zero"]:
        return v == 0 or abs(v - st["mean"]) <= tol
    lo, hi = st[f"{which}_lo"], st[f"{which}_hi"]
    return bool(math.isfinite(lo) and lo - tol <= v <= hi + tol)


def sign(x: Fraction) -> str:
    return "zero" if x == 0 else ("above" if x > 0 else "below")


def binom_two_sided(k: int, n: int, p: float) -> float:
    from scipy import stats as sps
    return float(sps.binomtest(k, n, p).pvalue)


def pred_unconditional(check: str, K: int, q: Fraction, c: int, M: int, cap_mode: str) -> Fraction:
    if check == "R_pop":
        return pe.closed_oblivious(K, q, c)
    if check == "gap_oracle":
        return pe.closed_gap(K, q, c)
    ee = (pe.closed_prop3_pooled if cap_mode == "pooled" else pe.closed_prop3_per_copy)(K, q, M)
    return Fraction(K) * q / 2 - ee


def e3_original_flags() -> dict:
    """Read-only cross-reference to the E3 pass flags in results/paper_numbers.json."""
    p = ROOT / "results" / "paper_numbers.json"
    try:
        nums = json.loads(p.read_text())["numbers"]
    except (OSError, KeyError, ValueError):
        return {}
    return {k: v for k, v in nums.items() if k.startswith("e3/") and "/summary/" not in k}


# =========================================================================================
# Main
# =========================================================================================
def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--rows", default=str(ROOT / "results" / "kcopy_dev" / "rows.jsonl"))
    ap.add_argument("--out-json", default=str(ROOT / "results" / "e3_conditioned.json"))
    ap.add_argument("--out-md", default=str(ROOT / "results" / "e3_conditioned.md"))
    ap.add_argument("--verify-K", type=int, default=4, help="enumerate closed forms for K <= this")
    args = ap.parse_args(argv)
    t0 = time.time()
    K = K_STUDY
    seeds = list(range(SEED_LO, SEED_HI + 1))
    cells: list[Cell] = list(KCOPY_CELLS)
    cell_ids = {c.cell_id for c in cells}

    # 1. closed forms against enumeration (small K) and against the unconditional forms
    ver = verify_closed_forms(range(1, args.verify_K + 1), 3)
    tot = verify_total_expectation(range(1, args.verify_K + 1),
                                   [Fraction(7, 50), Fraction(2, 5), Fraction(1, 2)], [0, 1, 3, 5])
    if not (ver["all_equal"] and tot["all_equal"]):
        print("closed-form verification FAILED", file=sys.stderr)

    # 2. realizations (instance generation only; no policy is run)
    real: dict[tuple[str, int], Realization] = {}
    for cell in cells:
        for s in seeds:
            real[(cell.cell_id, s)] = Realization.from_instance(generate_kcopy(s, cell, K=K), K)
    cond: dict[tuple[str, str, int], tuple[Fraction, Fraction]] = {}
    for (cid, s), rl in real.items():
        for p in POLICIES:
            m, v = greedy_moments(rl, p)
            cf = cond_closed(rl, p)
            if cf != m:
                raise AssertionError(f"closed form and greedy law disagree: {cid} {s} {p}")
            if p == "guarded_mpc_e1" and rl.c == K:
                if cond_e1_at_K(K, rl.cap_mode, rl.I, rl.S_unid) != cf:
                    raise AssertionError(f"Prop 3 conditional form disagrees: {cid} {s}")
            cond[(cid, p, s)] = (cf, v)

    # realized stuck and identification rates
    q_values = sorted({c.q for c in cells})
    stuck_rate = []
    for q in q_values:
        cid = next(c.cell_id for c in cells if c.q == q)
        Ss = [real[(cid, s)].S for s in seeds]
        # S depends only on (seed, q): check across every cell with this q
        for c in cells:
            if c.q == q and [real[(c.cell_id, s)].S for s in seeds] != Ss:
                raise AssertionError("stuck count differs across cells of one q")
        k, n = sum(Ss), K * len(seeds)
        arr = np.array(Ss, float) / K
        stuck_rate.append(dict(
            q=q, n_A_copies=n, stuck=k, rate=k / n, expected=q * n,
            rate_minus_q=k / n - q, se_rate_across_seeds=float(arr.std(ddof=1) / math.sqrt(len(seeds))),
            z_binomial=(k - q * n) / math.sqrt(n * q * (1 - q)),
            binom_two_sided_p=binom_two_sided(k, n, q),
            per_seed_S=Ss))
    ident_rate = []
    for q in q_values:
        for M in (1, 3, 5):
            cid = next(c.cell_id for c in cells if c.q == q and c.M == M)
            Is = [real[(cid, s)].I for s in seeds]
            f = float(pe.f_identified(Fraction(str(q)), M))
            k, n = sum(Is), K * len(seeds)
            ident_rate.append(dict(q=q, M=M, identified=k, n_A_copies=n, rate=k / n, f=f,
                                   z_binomial=(k - f * n) / math.sqrt(n * f * (1 - f)),
                                   binom_two_sided_p=binom_two_sided(k, n, f)))

    # 3. rows: measured minus conditional, per policy and cell
    rows_path = Path(args.rows)
    if not rows_path.exists() and Path(str(rows_path) + ".gz").exists():
        rows_path = Path(str(rows_path) + ".gz")
    loaded = load_rows(rows_path, cell_ids, seeds)
    vals = loaded["vals"]
    m_policy_cells = len(cells) * len(POLICIES)
    lvl_pc = 1.0 - 0.05 / m_policy_cells
    per_policy_cell = []
    for cell in cells:
        cid = cell.cell_id
        for p in POLICIES:
            d = [Fraction(vals[(cid, p)][s]) - cond[(cid, p, s)][0] for s in seeds]
            st = series_stats(d, lvl_pc)
            det = [s for s in seeds if cond[(cid, p, s)][1] == 0]
            det_bad = [s for s in det if Fraction(vals[(cid, p)][s]) != cond[(cid, p, s)][0]]
            meas = sum((Fraction(vals[(cid, p)][s]) for s in seeds), Fraction(0)) / len(seeds)
            per_policy_cell.append(dict(
                cell_id=cid, policy=p, q=cell.q, c=int(round(cell.c)), M=cell.M,
                cap_mode=cell.cap_mode, measured_mean=float(meas),
                conditional_mean=float(sum((cond[(cid, p, s)][0] for s in seeds), Fraction(0)) / len(seeds)),
                diff=st, contains_zero_pointwise=contains(st, 0.0, "pw"),
                contains_zero_simultaneous=contains(st, 0.0, "sim"),
                n_seeds_deterministic=len(det), n_deterministic_mismatch=len(det_bad),
                deterministic_mismatch_seeds=det_bad))
    pc_summary = {}
    for p in POLICIES:
        recs = [r for r in per_policy_cell if r["policy"] == p]
        pc_summary[p] = dict(
            cells=len(recs),
            contains_zero_simultaneous=sum(r["contains_zero_simultaneous"] for r in recs),
            contains_zero_pointwise=sum(r["contains_zero_pointwise"] for r in recs),
            mean_of_cell_mean_diffs=float(np.mean([r["diff"]["mean"] for r in recs])),
            max_abs_z=float(max((abs(r["diff"]["mean"]) / r["diff"]["se"]) if r["diff"]["se"] > 0
                                else 0.0 for r in recs)),
            seed_cells_deterministic=sum(r["n_seeds_deterministic"] for r in recs),
            seed_cells_deterministic_mismatch=sum(r["n_deterministic_mismatch"] for r in recs),
            cells_identically_zero=sum(r["diff"]["identically_zero"] for r in recs))

    # 4. the 312 E3 points
    orig = e3_original_flags()
    raw = []
    for cell in cells:
        cid, c, q = cell.cell_id, int(round(cell.c)), Fraction(str(cell.q))
        pop = {s: Fraction(vals[(cid, "pop_mpc")][s]) for s in seeds}
        cp = {s: cond[(cid, "pop_mpc", s)][0] for s in seeds}
        meas = {"R_pop": {s: pop[s] for s in seeds}}
        cnd = {"R_pop": cp}
        orc = {s: Fraction(vals[(cid, "oracle_mpc")][s]) for s in seeds}
        meas["gap_oracle"] = {s: pop[s] - orc[s] for s in seeds}
        cnd["gap_oracle"] = {s: cp[s] - cond[(cid, "oracle_mpc", s)][0] for s in seeds}
        if c == K:
            e1 = {s: Fraction(vals[(cid, "guarded_mpc_e1")][s]) for s in seeds}
            meas["gap_e1"] = {s: pop[s] - e1[s] for s in seeds}
            cnd["gap_e1"] = {s: cp[s] - cond[(cid, "guarded_mpc_e1", s)][0] for s in seeds}
        for chk in CHECKS:
            if chk not in meas:
                continue
            raw.append((cell, chk, meas[chk], cnd[chk],
                        pred_unconditional(chk, K, q, c, cell.M, cell.cap_mode)))
    m_pts = len(raw)
    level = 1.0 - 0.05 / m_pts
    points = []
    for cell, chk, ms, cs, pu in raw:
        c = int(round(cell.c))
        mser = [ms[s] for s in seeds]
        dser = [ms[s] - cs[s] for s in seeds]
        st_m = series_stats(mser, level)
        st_d = series_stats(dser, level)
        cond_mean = sum((cs[s] for s in seeds), Fraction(0)) / len(seeds)
        meas_mean = sum(mser, Fraction(0)) / len(seeds)
        key = f"e3/{chk}/{cell.cap_mode}/q{cell.q:g}/c{c}/M{cell.M}"
        o = orig.get(key, {})
        points.append(dict(
            check=chk, cell_id=cell.cell_id, q=cell.q, c=c, M=cell.M, cap_mode=cell.cap_mode,
            K=K, n_seeds=len(seeds), measured_mean=float(meas_mean),
            predicted_unconditional=float(pu), predicted_unconditional_exact=str(pu),
            predicted_conditional=float(cond_mean), predicted_conditional_exact=str(cond_mean),
            measured_minus_unconditional=float(meas_mean - pu),
            sign_measured_minus_unconditional=sign(meas_mean - pu),
            unconditional_in_simultaneous_t=contains(st_m, float(pu), "sim"),
            unconditional_in_pointwise_t=contains(st_m, float(pu), "pw"),
            dev_report_pass_simultaneous=o.get("passed"),
            dev_report_pass_pointwise_bootstrap=o.get("passed_pointwise"),
            measured_minus_conditional=st_d,
            sign_measured_minus_conditional=sign(meas_mean - cond_mean),
            conditional_zero_in_simultaneous=contains(st_d, 0.0, "sim"),
            conditional_zero_in_pointwise=contains(st_d, 0.0, "pw"),
            label=LABEL, status=STATUS))

    def combined_z(pts):
        # one point per cell within a check; given the realization the cells' tie-break
        # streams are independent, so the per-cell mean residuals combine as independent
        nz = [p["measured_minus_conditional"] for p in pts
              if not p["measured_minus_conditional"]["identically_zero"]]
        v = sum(d["se"] ** 2 for d in nz)
        return float(sum(d["mean"] for d in nz) / math.sqrt(v)) if v > 0 else 0.0

    def summarize(pts):
        return dict(
            combined_z_measured_minus_conditional=combined_z(pts),
            points=len(pts),
            conditional_zero_in_simultaneous=sum(p["conditional_zero_in_simultaneous"] for p in pts),
            conditional_zero_in_pointwise=sum(p["conditional_zero_in_pointwise"] for p in pts),
            conditional_identically_zero=sum(p["measured_minus_conditional"]["identically_zero"] for p in pts),
            sign_conditional={k: sum(p["sign_measured_minus_conditional"] == k for p in pts)
                              for k in ("above", "below", "zero")},
            unconditional_in_simultaneous_t=sum(p["unconditional_in_simultaneous_t"] for p in pts),
            unconditional_in_pointwise_t=sum(p["unconditional_in_pointwise_t"] for p in pts),
            dev_report_pointwise_bootstrap_pass=sum(bool(p["dev_report_pass_pointwise_bootstrap"]) for p in pts),
            sign_unconditional={k: sum(p["sign_measured_minus_unconditional"] == k for p in pts)
                                for k in ("above", "below", "zero")},
            mean_measured_minus_unconditional=float(np.mean([p["measured_minus_unconditional"] for p in pts])),
            mean_measured_minus_conditional=float(np.mean([p["measured_minus_conditional"]["mean"] for p in pts])),
            mean_conditional_minus_unconditional=float(np.mean(
                [p["predicted_conditional"] - p["predicted_unconditional"] for p in pts])))

    summary = {"all": summarize(points)}
    summary["all"]["combined_z_measured_minus_conditional"] = None   # cells repeat across checks
    for chk in CHECKS:
        summary[chk] = summarize([p for p in points if p["check"] == chk])
    nz = [p for p in points if not p["measured_minus_conditional"]["identically_zero"]]
    summary["not_identically_zero"] = summarize(nz)
    summary["not_identically_zero"]["combined_z_measured_minus_conditional"] = None
    misses = [p for p in points if p["dev_report_pass_pointwise_bootstrap"] is False]
    summary["dev_report_pointwise_misses"] = [dict(
        key=f"{p['check']}/{p['cap_mode']}/q{p['q']:g}/c{p['c']}/M{p['M']}",
        measured=p["measured_mean"], unconditional=p["predicted_unconditional"],
        conditional=p["predicted_conditional"],
        diff=p["measured_minus_conditional"]["mean"],
        pw=[p["measured_minus_conditional"]["pw_lo"], p["measured_minus_conditional"]["pw_hi"]],
        zero_in_pointwise=p["conditional_zero_in_pointwise"]) for p in misses]

    rows_sha = file_sha256(rows_path)
    manifest = rows_path.parent / "manifest.json"
    inputs = {"rows": {"path": str(rows_path.relative_to(ROOT)) if rows_path.is_relative_to(ROOT)
                       else str(rows_path), "sha256": rows_sha, "rows_kept": loaded["n_rows"]}}
    if manifest.exists():
        inputs["manifest"] = {"path": str(manifest.relative_to(ROOT)), "sha256": file_sha256(manifest)}
    inputs["script"] = {"path": str(Path(__file__).resolve().relative_to(ROOT)),
                        "sha256": file_sha256(Path(__file__).resolve())}
    out = {
        "meta": {
            "label": LABEL, "status": STATUS,
            "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "git": git_info(), "inputs": inputs,
            "seeds": [SEED_LO, SEED_HI], "n_seeds": len(seeds), "K": K, "metric": METRIC,
            "policies": list(POLICIES), "n_cells": len(cells),
            "simultaneous_level": level, "simultaneous_m": m_pts, "pointwise_level": 0.95,
            "interval": "Student-t on the per-seed series (both levels)",
            "conditioned_on": "per seed and cell: scored-event stuck pattern of the A copies "
                              "(Instance.availability() with no floor, slot 0) and prior_stuck "
                              "counts, read from generate_kcopy(seed, cell, K=8); generation only, "
                              "no policy simulation",
            "decision_laws": {
                "pop_mpc": "every D at slot 1; spare slot-1 cap hedges twins uniformly at random "
                           "(pooled: min(c,2K) of 2K twins; per-copy: c/K of the copy's 2 twins)",
                "oracle_mpc": "knows classes, not the realized stuck state: hedges A copies first, "
                              "min(c,K) uniformly among the K A copies when c < K",
                "guarded_mpc_e1": "hedges A copies in decreasing prior stuck count (identified "
                                  "first), the level where hedges run out uniformly; remaining "
                                  "hedges uniformly over the unidentified twins"},
            "seed_note": "61500-61599 regenerated for instance generation only, on owner request; "
                         "no policy was run on them by this script",
            "verify_K": args.verify_K,
            "runtime_s": None,
        },
        "closed_form_verification": {"enumeration": ver, "total_expectation": tot},
        "stuck_rate": stuck_rate,
        "identified_rate": ident_rate,
        "per_policy_cell_summary": pc_summary,
        "per_policy_cell_level_simultaneous": lvl_pc,
        "summary": summary,
        "points": points,
        "per_policy_cell": per_policy_cell,
    }
    out["meta"]["runtime_s"] = round(time.time() - t0, 1)
    Path(args.out_json).write_text(json.dumps(out, indent=1) + "\n")
    Path(args.out_md).write_text(render_md(out) + "\n")
    print(json.dumps({"stuck_rate": [{k: r[k] for k in ("q", "rate", "z_binomial")} for r in stuck_rate],
                      "summary": {k: v for k, v in summary.items() if k != "dev_report_pointwise_misses"},
                      "per_policy_cell": pc_summary,
                      "verification": {"enumeration_all_equal": ver["all_equal"],
                                       "cases": ver["cases"],
                                       "total_expectation_all_equal": tot["all_equal"]},
                      "runtime_s": out["meta"]["runtime_s"]}, indent=1))
    return 0


def render_md(o: dict) -> str:
    m, s = o["meta"], o["summary"]
    L = [f"# E3 conditioned on the realized stuck draws", "",
         f"**Label:** {m['label']}. **Status:** {m['status']}. Not a pre-registered endpoint; "
         "E3 itself (DEV_REPORT_E Section 8) is unchanged.", "",
         f"Seeds {m['seeds'][0]}–{m['seeds'][1]} (n = {m['n_seeds']}), K = {m['K']}, metric "
         f"`{m['metric']}`. Git {m['git']['commit']} (dirty {m['git']['dirty']}). Rows "
         f"`{m['inputs']['rows']['path']}` sha256 `{m['inputs']['rows']['sha256']}`.", "",
         "Per seed and cell, each policy's expected residual is computed given the realized "
         "stuck pattern of the scored event and the realized prior stuck counts (instance "
         "generation only, no policy run), over the policy's own tie-break randomness. "
         "Measured minus that conditional expectation removes the stuck draws that common "
         "random numbers share across cells.", "",
         "## Realized stuck rate", "",
         "| q | stuck / A copies | rate | rate − q | z (binomial) | p (two-sided) |",
         "|---:|---:|---:|---:|---:|---:|"]
    for r in o["stuck_rate"]:
        L.append(f"| {r['q']:g} | {r['stuck']} / {r['n_A_copies']} | {r['rate']:.4f} | "
                 f"{r['rate_minus_q']:+.4f} | {r['z_binomial']:+.2f} | {r['binom_two_sided_p']:.3f} |")
    L += ["", "Identified share (A copies with a prior stuck outcome) against f = 1 − (1 − q)^M:", "",
          "| q | M | rate | f | z | two-sided p |", "|---:|---:|---:|---:|---:|---:|"]
    for r in o["identified_rate"]:
        L.append(f"| {r['q']:g} | {r['M']} | {r['rate']:.4f} | {r['f']:.4f} | {r['z_binomial']:+.2f} | "
                 f"{r['binom_two_sided_p']:.4f} |")
    L += ["", "The M values share the prior-event draws, so these tests are correlated; the smallest "
          "p is reported without adjustment."]
    L += ["", "## The 312 E3 points, before and after conditioning", "",
          f"Simultaneous level {m['simultaneous_level']:.6f} (Bonferroni over {m['simultaneous_m']} "
          "points, as E3 primary); pointwise 95%. Student-t intervals on the per-seed series.", "",
          "| check | points | uncond. in simult. | uncond. in pointwise (t) | uncond. below / above | "
          "0 in simult. (cond.) | 0 in pointwise (cond.) | cond. below / above / exactly 0 | "
          "mean meas − uncond | mean meas − cond | combined z (cond.) |",
          "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for k in ("R_pop", "gap_oracle", "gap_e1", "all"):
        d = s[k]
        L.append(f"| {k} | {d['points']} | {d['unconditional_in_simultaneous_t']} | "
                 f"{d['unconditional_in_pointwise_t']} | {d['sign_unconditional']['below']} / "
                 f"{d['sign_unconditional']['above']} | {d['conditional_zero_in_simultaneous']} | "
                 f"{d['conditional_zero_in_pointwise']} | {d['sign_conditional']['below']} / "
                 f"{d['sign_conditional']['above']} / {d['sign_conditional']['zero']} | "
                 f"{d['mean_measured_minus_unconditional']:+.4f} | {d['mean_measured_minus_conditional']:+.4f} | "
                 + ("–" if d["combined_z_measured_minus_conditional"] is None
                    else f"{d['combined_z_measured_minus_conditional']:+.2f}") + " |")
    nz = s["not_identically_zero"]
    L += ["", "Combined z: sum of the per-point mean residuals over the root sum of their "
          "squared standard errors, within one check (one point per cell; given the realization "
          "the cells' tie-break streams are independent). Not defined for `all`, where a cell "
          "contributes to several checks."]
    L += ["", f"Points whose conditional residual is not identically zero across seeds: "
          f"{nz['points']}; 0 inside the pointwise interval for {nz['conditional_zero_in_pointwise']} "
          f"(expected about {0.95 * nz['points']:.1f}); sign below / above "
          f"{nz['sign_conditional']['below']} / {nz['sign_conditional']['above']}.", "",
          "DEV_REPORT_E pointwise misses (bootstrap) after conditioning:", "",
          "| point | measured | unconditional | conditional | meas − cond | pointwise 95% | 0 inside |",
          "|---|---:|---:|---:|---:|---|---|"]
    for p in s["dev_report_pointwise_misses"]:
        L.append(f"| {p['key']} | {p['measured']:.3f} | {p['unconditional']:.3f} | "
                 f"{p['conditional']:.3f} | {p['diff']:+.3f} | [{p['pw'][0]:+.3f}, {p['pw'][1]:+.3f}] | "
                 f"{'yes' if p['zero_in_pointwise'] else 'no'} |")
    L += ["", "## Proposition 3 points (pop − e1, c = K)", "",
          "| cap | q | M | measured | unconditional | conditional | meas − cond | pointwise 95% |",
          "|---|---:|---:|---:|---:|---:|---:|---|"]
    for p in o["points"]:
        if p["check"] != "gap_e1":
            continue
        d = p["measured_minus_conditional"]
        L.append(f"| {p['cap_mode']} | {p['q']:g} | {p['M']} | {p['measured_mean']:.3f} | "
                 f"{p['predicted_unconditional']:.3f} | {p['predicted_conditional']:.3f} | "
                 f"{d['mean']:+.3f} | [{d['pw_lo']:+.3f}, {d['pw_hi']:+.3f}] |")
    L += ["", "## Checks of the conditional laws against the rows", "",
          f"Per policy and cell (144 cells each; simultaneous level "
          f"{o['per_policy_cell_level_simultaneous']:.6f} over 432 policy-cells):", "",
          "| policy | 0 in simult. | 0 in pointwise | max abs z | seed-cells deterministic given "
          "the realization | of which measured ≠ conditional |", "|---|---:|---:|---:|---:|---:|"]
    for p, d in o["per_policy_cell_summary"].items():
        L.append(f"| {p} | {d['contains_zero_simultaneous']} / {d['cells']} | "
                 f"{d['contains_zero_pointwise']} / {d['cells']} | {d['max_abs_z']:.2f} | "
                 f"{d['seed_cells_deterministic']} | {d['seed_cells_deterministic_mismatch']} |")
    v, t = o["closed_form_verification"]["enumeration"], o["closed_form_verification"]["total_expectation"]
    L += ["", "## Closed forms", "",
          f"Conditional closed forms (hypergeometric) against exhaustive enumeration of the "
          f"uniform hedge subsets (K ≤ {m['verify_K']}, "
          f"every stuck pattern, prior counts 0..3 per A copy, every c, both caps): {v['cases']} comparisons, "
          f"all exact: {v['all_equal']}. Averaged over the stuck and history law they recover "
          f"prop_enum's unconditional closed forms: {t['equal']} / {t['cases']} exact.",
          "", "Regenerate: `uv run python scripts/e3_conditioned.py`."]
    return "\n".join(L)


if __name__ == "__main__":
    sys.exit(main())
