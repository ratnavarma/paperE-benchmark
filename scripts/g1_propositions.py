"""Gate G1: run the full proposition grid on the exhaustive enumerator and write results.

Writes results/g1_propositions.json and results/g1_propositions.md. Every row has the
enumerated value (brute force over schedules, realizations and histories, exact), the
closed form or bound from MECHANISM_E_v2, the relation checked and whether it holds
exactly. Rows labelled "closed form only" are not enumerated.

Usage: uv run python scripts/g1_propositions.py [--K 1 2 3 4]
"""

from __future__ import annotations

import argparse
import itertools
import json
import time
from decimal import ROUND_HALF_UP, Decimal
from fractions import Fraction as F
from pathlib import Path

from papere import prop_enum as pe

QS = [F(1, 2), F(2, 5), F(7, 50)]
MS = [0, 1, 2, 3, 5]
ROOT = Path(__file__).resolve().parents[1]


def rnd(x: F, digits: int) -> str:
    d = Decimal(x.numerator) / Decimal(x.denominator)
    return str(d.quantize(Decimal(1).scaleb(-digits), rounding=ROUND_HALF_UP))


def fstr(x) -> str:
    """Exact string for a Fraction; 15-digit decimal for huge closed-form-only fractions."""
    if isinstance(x, F) and max(x.numerator.bit_length(), x.denominator.bit_length()) > 256:
        return "~" + rnd(x, 15)
    return str(x)


class Rows:
    def __init__(self):
        self.rows = []

    def add(self, check, enumerated, closed, rel="==", K=None, q=None, M=None, c=None,
            cap_mode=None, note="", ok=None):
        if ok is not None:
            pass
        elif rel == "==":
            ok = enumerated == closed
        elif rel == ">=":
            ok = enumerated >= closed
        elif rel.startswith("within"):
            ok = abs(enumerated - closed) < F(1, 1000)
        elif rel == "rounds to":
            ok = enumerated == closed
        else:
            raise ValueError(rel)
        ok = bool(ok)
        self.rows.append(dict(
            check=check, K=K, q=None if q is None else str(q), M=M, c=c, cap_mode=cap_mode,
            enumerated=fstr(enumerated), closed_form=fstr(closed), relation=rel, holds=bool(ok),
            enumerated_float=float(enumerated) if isinstance(enumerated, (F, int)) else None,
            note=note,
        ))
        if not ok:
            print("FAIL", self.rows[-1])


def run(Ks):
    R = Rows()
    t0 = time.time()
    timing = {}
    for K in Ks:
        tk = time.time()
        for q in QS:
            # Proposition 1
            for mode in pe.CAP_MODES:
                ob = pe.oblivious_optimum(K, q, K, mode)
                R.add("prop1_oblivious_optimum", ob.value, pe.closed_prop1(K, q), K=K, q=q, c=K,
                      cap_mode=mode, note=f"{ob.n_orbits} orbits / {ob.n_schedules} schedules")
                R.add("prop1_posterior_optimum", pe.posterior_optimum(K, q, K, mode), F(0),
                      K=K, q=q, c=K, cap_mode=mode)
                sig = pe.hedge_all_A_schedule(K)
                worst = max(pe.simulate_residual(sig, p, K)
                            for p in itertools.product((0, 1), repeat=K))
                assert pe.is_feasible(sig, K, K, mode)
                R.add("prop1_hedge_all_A_max_R_over_realizations", F(worst), F(0), K=K, q=q,
                      c=K, cap_mode=mode)
            # gap(c)
            for mode in pe.CAP_MODES:
                cs = range(2 * K + 1) if mode == pe.POOLED else [0, K, 2 * K]
                for c in cs:
                    ob = pe.oblivious_optimum(K, q, c, mode).value
                    po = pe.posterior_optimum(K, q, c, mode)
                    R.add("gap_c", ob - po, pe.closed_gap(K, q, c), K=K, q=q, c=c, cap_mode=mode)
                    R.add("gap_c_oblivious_optimum", ob, pe.closed_oblivious(K, q, c), K=K, q=q,
                          c=c, cap_mode=mode)
                    R.add("gap_c_posterior_optimum", po, pe.closed_posterior(K, q, c), K=K, q=q,
                          c=c, cap_mode=mode)
            # Proposition 3
            for M in MS:
                f = pe.f_identified(q, M)
                for mode in pe.CAP_MODES:
                    kinds = ["count"] + (["full"] if K * M <= 8 else [])
                    vals = {}
                    ob = pe.oblivious_optimum(K, q, K, mode).value
                    for kind in kinds:
                        r = pe.history_optimum(K, q, M, mode, kind, prefill_qs=QS)
                        vals[kind] = r.value
                        cf = (pe.closed_prop3_pooled(K, q, M) if mode == pe.POOLED
                              else pe.closed_prop3_per_copy(K, q, M))
                        tag = f"histories={kind} ({r.n_histories})"
                        R.add("prop3_history_optimum", r.value, cf, K=K, q=q, M=M, c=K,
                              cap_mode=mode, note=tag)
                        for I in sorted(r.by_identified):
                            cI = (pe.closed_prop3_pooled_given_I(K, q, I) if mode == pe.POOLED
                                  else pe.closed_prop3_per_copy_given_I(K, q, I))
                            R.add(f"prop3_E[R|I={I}]", r.by_identified[I], cI, K=K, q=q, M=M,
                                  c=K, cap_mode=mode, note=tag)
                            R.add(f"prop3_every_history_with_I={I}", F(len(r.per_history_by_I[I])),
                                  F(1), K=K, q=q, M=M, c=K, cap_mode=mode,
                                  note=tag + "; count of distinct per-history optima")
                        e1, per = pe.identified_first_value(K, q, M, mode, kind)
                        R.add("prop3_identified_first_law_vs_class_optimum", e1, r.value, K=K,
                              q=q, M=M, c=K, cap_mode=mode,
                              note=tag + "; closed_form column = enumerated class optimum")
                        nbad = sum(v != pe.history_class_optimum(K, q, K, mode, cls).value
                                   for cls, v in per.items())
                        R.add("prop3_identified_first_per_history_mismatches", F(nbad), F(0),
                              K=K, q=q, M=M, c=K, cap_mode=mode, note=tag)
                        s = 1 - r.value / ob
                        if mode == pe.PER_COPY:
                            R.add("prop3_share_recovered", s, f, K=K, q=q, M=M, c=K,
                                  cap_mode=mode, note=tag)
                        else:
                            R.add("prop3_share_recovered_vs_f/(2-f)", s, f / (2 - f), ">=", K=K,
                                  q=q, M=M, c=K, cap_mode=mode, note=tag)
                            if K == 1:
                                R.add("prop3_share_recovered_K1", s, f, K=K, q=q, M=M, c=K,
                                      cap_mode=mode, note=tag)
                        if M == 0:
                            R.add("prop3_M0_equals_prop1", r.value, ob, K=K, q=q, M=M, c=K,
                                  cap_mode=mode, note=tag + "; closed_form column = enumerated Prop 1")
                    if len(vals) == 2:
                        R.add("prop3_full_vs_count_histories", vals["full"], vals["count"], K=K,
                              q=q, M=M, c=K, cap_mode=mode)
        timing[K] = round(time.time() - tk, 1)
        print(f"K={K} done in {timing[K]} s")

    # I1 table (MECHANISM 3.4), K = 1, q = 1/2
    H = F(1, 2)
    laws = {
        "posterior": [(((1, 1), (1, 0), (0, 1)), F(1))],
        "certainty_equivalent": [(((1, 0), (1, 0), (0, 1)), F(1))],
        "pessimistic_D_first_random_twin": [(((1, 1), (1, 0), (0, 1)), H),
                                            (((1, 0), (1, 1), (0, 1)), H)],
        "pessimistic_A_and_B_first": [(((1, 1), (1, 1), (0, 0)), F(1))],
        "one_twin_slot0_at_random": [(((1, 0), (0, 1), (0, 1)), H), (((0, 1), (1, 0), (0, 1)), H)],
    }
    table = {"posterior": (0, 0, 0), "certainty_equivalent": (0, 1, F(1, 2)),
             "pessimistic_D_first_random_twin": (0, F(1, 2), F(1, 4)),
             "pessimistic_A_and_B_first": (1, 1, 1),
             "one_twin_slot0_at_random": (0, F(1, 2), F(1, 4))}
    for name, law in laws.items():
        r1, r0, er = table[name]
        real = pe.law_realization_values(law, 1)
        R.add(f"I1_{name}_E[R]_units", pe.law_value(law, 1, H), F(er), K=1, q=H, c=1, cap_mode="pooled")
        R.add(f"I1_{name}_E[R]_kWh", pe.law_value(law, 1, H) / 4, F(er) / 4, K=1, q=H, c=1,
              cap_mode="pooled")
        R.add(f"I1_{name}_R_omega1", real[(0,)], F(r1), K=1, q=H, c=1, cap_mode="pooled")
        R.add(f"I1_{name}_R_omega0", real[(1,)], F(r0), K=1, q=H, c=1, cap_mode="pooled")
    R.add("I1_headroom_margin_m1_min_R_any_realization",
          F(pe.min_residual_any_realization(1, 0, pe.POOLED, cap_override=(1, 1))), F(1), ">=",
          K=1, q=H, cap_mode="pooled", note="cap C' = 1 per slot")
    R.add("I1_headroom_margin_m1_min_E[R]", pe.min_expected_with_caps(1, H, 1, 1), F(1), ">=",
          K=1, q=H, cap_mode="pooled", note="cap C' = 1 per slot")
    zs = set(pe.zero_residual_schedules(1, 1, pe.POOLED))
    R.add("I1_zero_residual_schedules_are_the_two_listed",
          F(int(zs == {((0, 1), (1, 0), (0, 1)), ((1, 1), (1, 0), (0, 1))})), F(1), K=1, c=1,
          cap_mode="pooled", note=f"{len(zs)} schedules")
    R.add("I1_sec35_swap_invariant_bound", pe.oblivious_optimum(1, H, 1, pe.POOLED).value,
          F(1, 4), K=1, q=H, c=1, cap_mode="pooled")
    R.add("I1_sec35_deterministic_oblivious_worst_case",
          pe.deterministic_oblivious_worst(1, H, 1, pe.POOLED), H, K=1, q=H, c=1, cap_mode="pooled")
    R.add("I1_sec35_deadline_tightening_lower_bound", pe.oblivious_optimum(1, H, 1, pe.POOLED).value,
          F(1, 4), ">=", K=1, q=H, c=1, cap_mode="pooled",
          note="any oblivious rule incl. tightening: enumerated class optimum >= 0.25")

    # closed form only: K = 1000 pooled shares
    for q in QS:
        for M in (1, 2, 3, 5):
            f = pe.f_identified(q, M)
            s = pe.share(pe.closed_prop3_pooled(1000, q, M), 1000, q)
            R.add("prop3_pooled_share_K1000_closed_form_only", s, f / (2 - f), "within 1e-3",
                  K=1000, q=q, M=M, c=1000, cap_mode="pooled", note="closed form only, not enumerated")

    # MECHANISM 3.9 table and PLAN Section 7
    Kbig = max(Ks)
    for q, M, f_s, pc_s, po_s in [(F(2, 5), 1, "0.40", "0.40", "0.25"),
                                  (F(2, 5), 3, "0.784", "0.78", "0.64"),
                                  (F(2, 5), 5, "0.922", "0.92", "0.86"),
                                  (F(1, 2), 3, "0.875", "0.88", "0.78")]:
        f = pe.f_identified(q, M)
        R.add("table39_f", rnd(f, len(f_s) - 2), f_s, "rounds to", q=q, M=M)
        r = pe.history_optimum(Kbig, q, M, pe.PER_COPY, "count")
        pc = 1 - r.value / pe.oblivious_optimum(Kbig, q, Kbig, pe.PER_COPY).value
        R.add("table39_share_per_copy_enumerated", rnd(pc, 2), pc_s, "rounds to", K=Kbig, q=q, M=M,
              cap_mode="per_copy", note=f"exact {pc}")
        po = pe.share(pe.closed_prop3_pooled(1000, q, M), 1000, q)
        R.add("table39_share_pooled_large_K", rnd(po, 2), po_s, "rounds to", K=1000, q=q, M=M,
              cap_mode="pooled", note="closed form only at K = 1000")
        R.add("table39_share_pooled_limit_f/(2-f)", rnd(f / (2 - f), 2), po_s, "rounds to", q=q,
              M=M, cap_mode="pooled", note="limit, closed form only")
        if q == F(2, 5):
            R.add("plan7_f_two_decimals", rnd(f, 2), {1: "0.40", 3: "0.78", 5: "0.92"}[M],
                  "rounds to", q=q, M=M)
    kcopy_structure(R, sorted(set(Ks) | {8}))
    return R.rows, timing, round(time.time() - t0, 1)


def kcopy_structure(R, Ks, seeds=(61500, 61501, 61502, 61537, 61599)):
    """generate_kcopy vs the enumerator's I_K; reuses tests/test_kcopy_structure.py checks."""
    import importlib.util

    import numpy as np
    from scipy.stats import binomtest

    from papere.generator import generate_kcopy

    spec = importlib.util.spec_from_file_location(
        "kcopy_checks", ROOT / "tests" / "test_kcopy_structure.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    for K in Ks:
        groups = {}
        for cell in mod.cells_for_K(K):
            for seed in seeds:
                key = (cell.cap_mode, int(cell.c))
                n, bad = groups.get(key, (0, 0))
                try:
                    mod.check_structure(generate_kcopy(seed, cell, K), K, int(cell.c), cell.cap_mode)
                except AssertionError:
                    bad += 1
                groups[key] = (n + 1, bad)
        for (mode, c), (n, bad) in sorted(groups.items()):
            R.add("kcopy_structure_failed_instances", F(bad), F(0), K=K, c=c, cap_mode=mode,
                  note=f"{n} instances (cells of KCOPY_CELLS rescaled to K x {len(seeds)} seeds)")
        for q in (0.14, 0.40, 0.50):
            cell = next(cl for cl in mod.cells_for_K(K)
                        if cl.q == q and cl.M == 5 and cl.cap_mode == "pooled")
            s0 = n0 = sp = npr = 0
            for seed in range(61500, 61500 + 2000 // K):
                inst = generate_kcopy(seed, cell, K)
                isA = np.asarray(inst.cls) == 1
                A = np.asarray(inst.availability())
                s0 += int((A[isA, 0] == 0).sum())
                n0 += int(isA.sum())
                ps = np.asarray(inst.prior_stuck)
                sp += int(ps[isA].sum())
                npr += ps[isA].size
            for name, k, n in (("kcopy_structure_A_slot0_stuck_freq", s0, n0),
                               ("kcopy_structure_A_prior_stuck_freq", sp, npr)):
                pv = binomtest(k, n, q).pvalue
                R.add(name, F(k, n), F(q).limit_denominator(100), "binomial p > 1e-4", K=K,
                      q=F(q).limit_denominator(100), M=5, cap_mode="pooled", ok=pv > 1e-4,
                      note=f"n = {n}, p = {pv:.3g}")


def write(rows, timing, total, Ks):
    out = ROOT / "results"
    out.mkdir(exist_ok=True)
    n_ok = sum(r["holds"] for r in rows)
    meta = dict(Ks=Ks, qs=[str(q) for q in QS], Ms=MS, n_rows=len(rows), n_hold=n_ok,
                all_hold=n_ok == len(rows), seconds_per_K=timing, seconds_total=total,
                full_histories_when="K*M <= 8; stuck-count histories always")
    (out / "g1_propositions.json").write_text(json.dumps(dict(meta=meta, rows=rows), indent=1))
    cols = ["check", "K", "q", "M", "c", "cap_mode", "enumerated", "closed_form", "relation",
            "holds", "note"]
    lines = ["# G1: exhaustive enumerator vs Propositions 1 and 3, gap(c) and the I1 table", "",
             f"Grid K = {Ks}, q = {meta['qs']}, M = {MS}. Rows: {len(rows)}, holding: {n_ok}. "
             f"Runtime {total} s (per K: {timing}).", "",
             "Enumerated values are exact brute force over schedules, realizations and "
             "histories; closed forms are from MECHANISM_E_v2 Sections 3.4-3.9. Rows marked "
             "'closed form only' are not enumerated.", "",
             "| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for r in rows:
        lines.append("| " + " | ".join("" if r[c] is None else str(r[c]) for c in cols) + " |")
    (out / "g1_propositions.md").write_text("\n".join(lines) + "\n")
    print(f"{n_ok}/{len(rows)} rows hold; wrote {out}/g1_propositions.{{json,md}} in {total} s")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--K", type=int, nargs="+", default=[1, 2, 3, 4])
    a = ap.parse_args()
    rows, timing, total = run(a.K)
    write(rows, timing, total, a.K)
