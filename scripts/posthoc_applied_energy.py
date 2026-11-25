"""Post hoc, descriptive numbers added for the Applied Energy revision (Phase 1, 2026-11-02).

Nothing here runs a policy or opens a reserved seed. Every number is derived from files that already exist:

1. e3/prop3_shortfall/*: how far the Proposition 3 points of theory tracking (E3) lie below prediction.
   Read from results/paper_numbers.json, keys e3/gap_e1/{pooled,per_copy}/q*/c8/M* (measured value and the
   "predicted" field). Points with a zero prediction (M = 0) are left out. Replaces the draft's wrong
   "by up to a third".
2. confirm_dev/C1..C5: the development values of the five confirmation tests, copied without change from
   results/confirm_check_dev.json (the frozen confirmation script run on development seeds 61000-61099, 99%
   intervals). Replaces five values the draft typed by hand.
3. share_fall/M3_rho{0.95,1.15}: share(delta 1) - share(delta 4) of the reliability-blind share on the 100
   development seeds, share = (ce_llf - pop_mpc) / (ce_llf - guarded_mpc_e1) as a ratio of means, all four
   vectors resampled jointly, paired bootstrap 95% (the analysis module's Bootstrap, default settings, as in
   posthoc_oblivious_share.py). The rho = 1.15 value is C5's statistic on development seeds at 95%.
4. sllf_exact/*: seed counts of the post hoc smoothed-LLF check on exact base load, copied from
   results/posthoc_sllf_nc1_exact.json.

Phase 2 additions (2026-11-02, Applied Energy journal build; same rules: read-only on existing rows,
development seeds 61000-61099 only, no reserved seed, no policy run):

5. factorial3/M3_rho{rho}/dA{d}/{rule}_{belief}: mean R_avoid of the 3 x 3 belief-by-rule factorial (rules
   LLF, greedy expected-value ranker, MPC; beliefs certainty-equivalent, shared rate, per participant) with
   paired bootstrap 95% intervals. LLF and MPC rows from results/f0r_extra, ranker rows from
   results/f0r_posthoc_ranker. The ranker levels are checked equal to results/posthoc_ranker.json.
6. e1_fixed/M{M}_rho{rho}/*: the delay contrast with one fixed comparator, Shared-rate MPC (pop_mpc) at
   every delay, per stratum (M in {0, 3} x rho). Same statistic as E1: mean gap over delta {2, 4} minus mean
   gap over delta {0, 1}, gap = R_avoid(pop_mpc) - R_avoid(guarded_mpc_e1). The same code with the frozen
   comparator (CE-LLF at delta 0, pop_mpc at delta >= 1) must reproduce e1/primary/M3_rho*/contrast exactly.
7. exchange/M3_rho0.95/dA2/x{rate}/{total,targeting}: the violation-discounted gain at the reference cell
   for exchange rates 0, 0.25, 0.5 and 1 kWh counted undelivered per kW·slot above the realized limit
   (0, 1, 2 and 4 kWh per kWh above the limit). R_disc = R_avoid + rate * violation_kwslot * 100 / N. Rate 0
   must equal layers/.../total and rate 0.25 must equal posthoc/discounted/dev/... (checked).
8. cellf_delay/M3_rho{rho}/*: why CE-LLF's avoidable residual falls from delta 1 to delta 4. Paired falls of
   R_avoid and of delivered energy, the count of seeds with the same realized availability (A_sha256) and the
   same minimum residual R* at delta 1 and 4, and the same fall for CE-MPC. Rows hold no count of failed
   setpoints, so no mechanism is computed here.
9. si/*: SI versions of numbers the note printed in kW·slot or instance units (1 kW·slot = 0.25 kWh; one
   instance unit = 0.25 kWh = 250 Wh). Linear rescaling of value and interval, never typed.
10. e3cond/*: the post hoc E3 check conditioned on realized stuck draws, copied from
   results/e3_conditioned.json (mean residuals rescaled from units to Wh).

Run: uv run python scripts/posthoc_applied_energy.py
Writes results/posthoc_applied_energy.json in the paper_numbers schema.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import re
import subprocess
from collections import defaultdict
from pathlib import Path

import numpy as np

from papere.analysis import Bootstrap, safe_ratio

PAPER_NUMBERS = Path("results/paper_numbers.json")
CONFIRM_DEV = Path("results/confirm_check_dev.json")
SLLF_EXACT = Path("results/posthoc_sllf_nc1_exact.json")
ROWS = Path("results/f0r_dev/rows.jsonl.gz")
OUT = Path("results/posthoc_applied_energy.json")
EXTRA_ROWS = Path("results/f0r_extra/rows.jsonl.gz")
RANKER_ROWS = Path("results/f0r_posthoc_ranker/rows.jsonl.gz")
RANKER_NUMBERS = Path("results/posthoc_ranker.json")
POSTHOC_SHARE = Path("results/posthoc_oblivious_share.json")
E3_COND = Path("results/e3_conditioned.json")
DEV_SEEDS = list(range(61000, 61100))
KWH_PER_KWSLOT = 0.25
WH_PER_UNIT = 250.0
RULES = {"llf": "LLF", "greedy": "greedy expected-value ranker", "mpc": "MPC"}
BELIEFS = {"ce": "certainty-equivalent", "pop": "shared rate", "e1": "per participant"}
SCHED = {("llf", "ce"): "ce_llf", ("llf", "pop"): "llf_pop", ("llf", "e1"): "llf_post",
         ("greedy", "ce"): "greedy_ev_ce", ("greedy", "pop"): "greedy_ev_pop", ("greedy", "e1"): "greedy_ev",
         ("mpc", "ce"): "mpc_ce", ("mpc", "pop"): "pop_mpc", ("mpc", "e1"): "guarded_mpc_e1"}
LABEL = "descriptive, post hoc, added for the Applied Energy revision 2026-11-02"
POLICIES = ("ce_llf", "pop_mpc", "guarded_mpc_e1")


def scalar(value, unit, statistic, source, **extra):
    return {"value": value, "ci_lo": None, "ci_hi": None, "label": LABEL, "unit": unit,
            "statistic": statistic, "source_file": source, **extra}


def prop3_shortfall(numbers: dict) -> dict:
    pat = re.compile(r"^e3/gap_e1/(pooled|per_copy)/q([\d.]+)/c(\d+)/M(\d+)$")
    pts = []
    for k, e in numbers.items():
        m = pat.match(k)
        if not m or not e.get("predicted"):
            continue
        meas, pred = float(e["value"]), float(e["predicted"])
        pts.append({"key": k, "measured": meas, "predicted": pred,
                    "rel_shortfall": (pred - meas) / pred, "abs_shortfall": pred - meas})
    if not pts:
        raise SystemExit("no Proposition 3 points found in paper_numbers.json")
    src = str(PAPER_NUMBERS)
    worst_rel = max(pts, key=lambda p: p["rel_shortfall"])
    worst_abs = max(pts, key=lambda p: p["abs_shortfall"])
    pre = "e3/prop3_shortfall"
    unit = "units on the instance (1 unit = 0.25 kWh)"
    return {
        f"{pre}/n_points": scalar(len(pts), "count", "Proposition 3 points with a nonzero prediction "
                                  "(gap_e1, c = K = 8, M in {1, 3, 5}, both caps, q in {0.14, 0.40, 0.50})", src),
        f"{pre}/n_below": scalar(sum(p["measured"] < p["predicted"] for p in pts), "count",
                                 "points whose measured gap lies below the prediction", src),
        f"{pre}/n_above_third": scalar(sum(p["rel_shortfall"] > 1 / 3 for p in pts), "count",
                                       "points whose shortfall exceeds one third of the prediction", src),
        f"{pre}/max_rel": scalar(worst_rel["rel_shortfall"], "ratio",
                                 "largest (predicted - measured) / predicted", src, point=worst_rel["key"]),
        f"{pre}/max_rel_predicted": scalar(worst_rel["predicted"], unit,
                                           "prediction at the point with the largest relative shortfall", src,
                                           point=worst_rel["key"]),
        f"{pre}/max_rel_measured": scalar(worst_rel["measured"], unit,
                                          "measured gap at the point with the largest relative shortfall", src,
                                          point=worst_rel["key"]),
        f"{pre}/max_abs": scalar(worst_abs["abs_shortfall"], unit,
                                 "largest predicted - measured", src, point=worst_abs["key"]),
    }


def confirm_dev() -> dict:
    tests = json.loads(CONFIRM_DEV.read_text(encoding="utf-8"))["tests"]
    out = {}
    for name, t in tests.items():
        out[f"confirm_dev/{name}"] = {
            "value": t["value"], "ci_lo": t["ci_lo"], "ci_hi": t["ci_hi"], "level": t["level"],
            "n_seeds": t["n_seeds"], "statistic": t["statistic"], "verdict": t["verdict"],
            "label": "development, frozen confirmation script on development seeds 61000-61099, copied without change",
            "source_file": str(CONFIRM_DEV)}
    return out


def share_fall() -> dict:
    vals: dict[tuple[str, str], dict[int, float]] = defaultdict(dict)
    with gzip.open(ROWS, "rt") as fh:
        for line in fh:
            r = json.loads(line)
            if r.get("mode") != "frozen" or r["policy"] not in POLICIES:
                continue
            vals[(r["cell_id"], r["policy"])][r["seed"]] = r["R_avoid_kwh_per100"]
    boot = Bootstrap()
    out = {}
    for rho in ("0.95", "1.15"):
        c1, c4 = f"F0R_M3_dA1_db0_rho{rho}_r0.3", f"F0R_M3_dA4_db0_rho{rho}_r0.3"
        seeds = sorted(set.intersection(*(set(vals[(c, p)]) for c in (c1, c4) for p in POLICIES)))
        v = {(c, p): np.array([vals[(c, p)][s] for s in seeds]) for c in (c1, c4) for p in POLICIES}
        st = boot.run({"o1": v[(c1, "ce_llf")] - v[(c1, "pop_mpc")], "t1": v[(c1, "ce_llf")] - v[(c1, "guarded_mpc_e1")],
                       "o4": v[(c4, "ce_llf")] - v[(c4, "pop_mpc")], "t4": v[(c4, "ce_llf")] - v[(c4, "guarded_mpc_e1")]},
                      {"d": lambda m: safe_ratio(m["o1"], m["t1"]) - safe_ratio(m["o4"], m["t4"])})["d"]
        out[f"share_fall/M3_rho{rho}"] = {
            "value": st.value, "ci_lo": st.lo, "ci_hi": st.hi, "n_seeds": len(seeds), "label": LABEL,
            "unit": "ratio", "source_file": str(ROWS), "cells": [c1, c4],
            "statistic": "share(delta 1) - share(delta 4), share = (ce_llf - pop_mpc)/(ce_llf - candidate), "
                         "ratios of means, jointly resampled, paired bootstrap 95%",
            "bootstrap": {"n_boot": boot.n_boot, "seed": boot.seed, "level": boot.level}}
    return out


def sllf_exact() -> dict:
    d = json.loads(SLLF_EXACT.read_text(encoding="utf-8"))
    src = str(SLLF_EXACT)
    p = d["policies"]
    return {
        "sllf_exact/n_seeds": scalar(p["sllf"]["n_seeds"], "count", "seeds of the exact-base-load check", src),
        "sllf_exact/sllf_zero": scalar(p["sllf"]["n_R_avoid_zero"], "count",
                                       "seeds where smoothed LLF reaches zero avoidable residual", src),
        "sllf_exact/ce_llf_nonzero": scalar(p["ce_llf"]["n_R_avoid_nonzero"], "count",
                                            "seeds where CE-LLF leaves a nonzero avoidable residual", src),
    }


def load_rows(path: Path, policies, metrics=("R_avoid_kwh_per100",)) -> dict:
    """(cell_id, policy) -> metric -> seed -> value, frozen rows on development seeds only."""
    vals: dict = defaultdict(lambda: defaultdict(dict))
    with gzip.open(path, "rt") as fh:
        for line in fh:
            r = json.loads(line)
            if r.get("mode") != "frozen" or r["policy"] not in policies:
                continue
            if not 61000 <= r["seed"] <= 61099:
                raise SystemExit(f"row outside the development seeds in {path}: {r['seed']}")
            for m in metrics:
                vals[(r["cell_id"], r["policy"])][m][r["seed"]] = r[m]
            vals[(r["cell_id"], r["policy"])]["N"][r["seed"]] = r["N"]
    return vals


def vec(vals: dict, cell: str, pol: str, metric: str = "R_avoid_kwh_per100") -> np.ndarray:
    d = vals.get((cell, pol), {}).get(metric)
    if not d or any(s not in d for s in DEV_SEEDS):
        raise SystemExit(f"missing development rows: {cell} {pol} {metric}")
    return np.array([d[s] for s in DEV_SEEDS], dtype=float)


def stat_entry(st, unit: str, statistic: str, source, cell=None, **extra) -> dict:
    e = {"value": st.value, "ci_lo": st.lo, "ci_hi": st.hi, "n_seeds": len(DEV_SEEDS), "label": LABEL_P2,
         "unit": unit, "statistic": statistic, "source_file": source}
    if cell:
        e["cell_id"] = cell
    e.update(extra)
    return e


LABEL_P2 = "descriptive, post hoc, development seeds 61000-61099, added for the Applied Energy journal build 2026-11-02"
KWH100 = "kWh per 100 participants per event"


def fcell(M: int, d: int, rho: str) -> str:
    return f"F0R_M{M}_dA{d}_db0_rho{rho}_r0.3"


def factorial3(boot: Bootstrap) -> dict:
    extra = load_rows(EXTRA_ROWS, {v for (r, b), v in SCHED.items() if r != "greedy"})
    rank = load_rows(RANKER_ROWS, {v for (r, b), v in SCHED.items() if r == "greedy"})
    ranker_nums = json.loads(RANKER_NUMBERS.read_text(encoding="utf-8"))["numbers"]
    out, n_checked = {}, 0
    for rho in ("0.95", "1.15"):
        for d in (0, 1, 2, 4):
            cell = fcell(3, d, rho)
            for (rule, belief), pol in SCHED.items():
                src = rank if rule == "greedy" else extra
                st = boot.mean_ci(vec(src, cell, pol))
                key = f"factorial3/M3_rho{rho}/dA{d}/{rule}_{belief}"
                out[key] = stat_entry(st, KWH100, f"mean R_avoid of {pol} ({RULES[rule]}, {BELIEFS[belief]} belief)",
                                      str(RANKER_ROWS if rule == "greedy" else EXTRA_ROWS), cell, policy=pol)
                if rule == "greedy":
                    ref = ranker_nums[f"posthoc_ranker/M3_rho{rho}/dA{d}/R_avoid_{pol}"]
                    if any(abs(out[key][f] - ref[f]) > 1e-9 for f in ("value", "ci_lo", "ci_hi")):
                        raise SystemExit(f"{key} differs from posthoc_ranker.json")
                    n_checked += 1
    print(f"factorial3: {len(out)} levels; {n_checked} ranker levels equal posthoc_ranker.json")
    return out


def e1_fixed(boot: Bootstrap, numbers: dict) -> dict:
    dev = load_rows(ROWS, ("ce_llf", "pop_mpc", "guarded_mpc_e1"))
    out = {}

    def contrast(comp: dict, M: int, rho: str):
        vectors = {f"g{d}": vec(dev, fcell(M, d, rho), comp[d]) - vec(dev, fcell(M, d, rho), "guarded_mpc_e1")
                   for d in (0, 1, 2, 4)}
        stats = {f"gap{d}": (lambda m, d=d: m[f"g{d}"]) for d in (0, 1, 2, 4)}
        stats["contrast"] = lambda m: (m["g2"] + m["g4"]) / 2 - (m["g0"] + m["g1"]) / 2
        return boot.run(vectors, stats)

    for rho in ("0.95", "1.15"):
        frozen = contrast({0: "ce_llf", 1: "pop_mpc", 2: "pop_mpc", 4: "pop_mpc"}, 3, rho)["contrast"]
        ref = numbers[f"e1/primary/M3_rho{rho}/contrast"]
        if any(abs(a - ref[f]) > 1e-9 for a, f in ((frozen.value, "value"), (frozen.lo, "ci_lo"), (frozen.hi, "ci_hi"))):
            raise SystemExit(f"frozen-comparator contrast does not reproduce e1/primary/M3_rho{rho}/contrast")
    print("e1_fixed: frozen-comparator code reproduces e1/primary/M3_rho{0.95,1.15}/contrast exactly")
    for M in (0, 3):
        for rho in ("0.95", "1.15"):
            res = contrast({d: "pop_mpc" for d in (0, 1, 2, 4)}, M, rho)
            for name, st in res.items():
                out[f"e1_fixed/M{M}_rho{rho}/{name}"] = stat_entry(
                    st, KWH100, "delay contrast with Shared-rate MPC as the comparator at every delay: "
                    "mean gap over delta {2,4} minus mean gap over delta {0,1}, gap = R_avoid(pop_mpc) - "
                    "R_avoid(guarded_mpc_e1)" if name == "contrast" else
                    f"gap R_avoid(pop_mpc) - R_avoid(guarded_mpc_e1) at delta {name[3:]}", str(ROWS),
                    stratum=f"M{M}_rho{rho}")
    return out


def exchange(boot: Bootstrap, numbers: dict, share_numbers: dict) -> dict:
    dev = load_rows(ROWS, ("ce_llf", "pop_mpc", "guarded_mpc_e1"), ("R_avoid_kwh_per100", "violation_kwslot"))
    cell = fcell(3, 2, "0.95")
    out = {}
    R = {p: vec(dev, cell, p) for p in ("ce_llf", "pop_mpc", "guarded_mpc_e1")}
    V = {p: vec(dev, cell, p, "violation_kwslot") for p in R}
    N = vec(dev, cell, "ce_llf", "N")
    for rate in (0.0, 0.25, 0.5, 1.0):
        disc = {p: R[p] + rate * V[p] * 100.0 / N for p in R}
        res = boot.run({"t": disc["ce_llf"] - disc["guarded_mpc_e1"], "g": disc["pop_mpc"] - disc["guarded_mpc_e1"]},
                       {"total": lambda m: m["t"], "targeting": lambda m: m["g"]})
        tag = f"x{rate:g}"
        for name, st in res.items():
            out[f"exchange/M3_rho0.95/dA2/{tag}/{name}"] = stat_entry(
                st, KWH100, f"violation-discounted gain at exchange rate {rate:g} kWh per kW·slot "
                f"({rate / KWH_PER_KWSLOT:g} kWh per kWh above the limit): R_avoid + rate * violation_kwslot * 100/N, "
                + ("ce_llf - candidate" if name == "total" else "pop_mpc - candidate"), str(ROWS), cell,
                rate_kwh_per_kwslot=rate)
    checks = [("x0/total", numbers["layers/M3_rho0.95/dA2/total"]),
              ("x0/targeting", numbers["layers/M3_rho0.95/dA2/targeting"]),
              ("x0.25/total", share_numbers["posthoc/discounted/dev/M3_rho0.95/dA2/total"]),
              ("x0.25/targeting", share_numbers["posthoc/discounted/dev/M3_rho0.95/dA2/targeting"])]
    for k, ref in checks:
        e = out[f"exchange/M3_rho0.95/dA2/{k}"]
        if abs(e["value"] - ref["value"]) > 1e-9:
            raise SystemExit(f"exchange {k} does not reproduce its published value")
    print("exchange: rate 0 equals the layers totals, rate 0.25 equals the published discounted gains")
    return out


def cellf_delay(boot: Bootstrap) -> dict:
    mets = ("R_avoid_kwh_per100", "D_kwh_per100", "R_star_kwh_per100", "A_sha256")
    dev = load_rows(ROWS, ("ce_llf", "mpc_ce"), mets)
    out = {}
    for rho in ("0.95", "1.15"):
        c1, c4 = fcell(3, 1, rho), fcell(3, 4, rho)
        pre = f"cellf_delay/M3_rho{rho}"
        for pol, tag in (("ce_llf", "ce_llf"), ("mpc_ce", "ce_mpc")):
            st = boot.mean_ci(vec(dev, c1, pol) - vec(dev, c4, pol))
            out[f"{pre}/{tag}_R_avoid_fall"] = stat_entry(st, KWH100, f"paired R_avoid({pol}, delta 1) - R_avoid({pol}, delta 4)",
                                                          str(ROWS), cells=[c1, c4])
        st = boot.mean_ci(vec(dev, c4, "ce_llf", "D_kwh_per100") - vec(dev, c1, "ce_llf", "D_kwh_per100"))
        out[f"{pre}/ce_llf_delivered_rise"] = stat_entry(st, KWH100, "paired delivered energy D(ce_llf, delta 4) - D(ce_llf, delta 1)",
                                                         str(ROWS), cells=[c1, c4])
        a1, a4 = dev[(c1, "ce_llf")]["A_sha256"], dev[(c4, "ce_llf")]["A_sha256"]
        s1, s4 = dev[(c1, "ce_llf")]["R_star_kwh_per100"], dev[(c4, "ce_llf")]["R_star_kwh_per100"]
        out[f"{pre}/same_availability"] = {"value": sum(a1[s] == a4[s] for s in DEV_SEEDS), "ci_lo": None, "ci_hi": None,
                                           "label": LABEL_P2, "unit": "count", "source_file": str(ROWS),
                                           "statistic": "seeds whose realized availability hash is equal at delta 1 and delta 4"}
        out[f"{pre}/same_r_star"] = {"value": sum(abs(s1[s] - s4[s]) < 1e-12 for s in DEV_SEEDS), "ci_lo": None, "ci_hi": None,
                                     "label": LABEL_P2, "unit": "count", "source_file": str(ROWS),
                                     "statistic": "seeds whose minimum residual R* is equal at delta 1 and delta 4"}
    return out


def scaled(e: dict, factor: float, unit: str, why: str) -> dict:
    out = {k: v for k, v in e.items()}
    for f in ("value", "ci_lo", "ci_hi"):
        if out.get(f) is not None:
            out[f] = out[f] * factor
    out["unit"] = unit
    out["label"] = (e.get("label") or "") + "; " + why
    return out


def si_numbers(numbers: dict, share_numbers: dict, own: dict) -> dict:
    """SI rescalings (never typed): kW·slot -> kWh (x 0.25); instance units -> Wh (x 250)."""
    out = {}
    kwh = "kWh per event (feeder total, N = 30)"
    why = "rescaled to kWh, 1 kW·slot = 0.25 kWh"
    out["si/violation/gate/candidate_minus_ce_llf"] = scaled(share_numbers["posthoc/violation/gate/candidate_minus_ce_llf"],
                                                             KWH_PER_KWSLOT, kwh, why)
    for pol in ("guarded_mpc_e1", "ce_llf", "sym_margin"):
        k = f"cell/F0R_M3_dA2_db0_rho0.95_r0.3/{pol}/violation_kwslot"
        out[f"si/{k[:-len('violation_kwslot')]}violation_kwh"] = scaled(numbers[k], KWH_PER_KWSLOT, kwh, why)
    rk = json.loads(RANKER_NUMBERS.read_text(encoding="utf-8"))["numbers"]
    for d in (2, 4):
        k = f"posthoc_ranker/M3_rho0.95/dA{d}/violation_greedy_ev_minus_ce_llf"
        out[f"si/{k}_kwh"] = scaled(rk[k], KWH_PER_KWSLOT, kwh, why)
    for name in ("max_rel_predicted", "max_rel_measured", "max_abs"):
        out[f"si/e3/prop3_shortfall/{name}_wh"] = scaled(own[f"e3/prop3_shortfall/{name}"], WH_PER_UNIT,
                                                          "Wh on the instance", "rescaled to Wh, 1 unit = 250 Wh")
    return out


def e3cond() -> dict:
    d = json.loads(E3_COND.read_text(encoding="utf-8"))
    src = str(E3_COND)
    lab = "post hoc diagnostic conditioned on realized stuck draws (results/e3_conditioned.json), copied"
    out = {}
    for s in d["stuck_rate"]:
        out[f"e3cond/stuck_rate/q{s['q']:g}"] = {"value": s["rate"], "ci_lo": None, "ci_hi": None, "label": lab,
                                                "unit": "ratio", "source_file": src, "n_copies": s["n_A_copies"],
                                                "statistic": f"realized stuck share of unreliable copies at q = {s['q']:g}"}
    for check in ("R_pop", "gap_oracle", "gap_e1"):
        sm = d["summary"][check]
        base = {"ci_lo": None, "ci_hi": None, "label": lab, "source_file": src}
        out[f"e3cond/{check}/n_points"] = {**base, "value": sm["points"], "unit": "count", "statistic": "points"}
        out[f"e3cond/{check}/n_below_uncond"] = {**base, "value": sm["sign_unconditional"]["below"], "unit": "count",
                                                 "statistic": "points below the unconditional prediction"}
        out[f"e3cond/{check}/n_below_cond"] = {**base, "value": sm["sign_conditional"]["below"], "unit": "count",
                                               "statistic": "points below the conditional expectation"}
        out[f"e3cond/{check}/n_above_cond"] = {**base, "value": sm["sign_conditional"]["above"], "unit": "count",
                                               "statistic": "points above the conditional expectation"}
        out[f"e3cond/{check}/mean_uncond_wh"] = {**base, "value": sm["mean_measured_minus_unconditional"] * WH_PER_UNIT,
                                                 "unit": "Wh on the instance", "statistic": "mean measured minus unconditional prediction"}
        out[f"e3cond/{check}/mean_cond_wh"] = {**base, "value": sm["mean_measured_minus_conditional"] * WH_PER_UNIT,
                                               "unit": "Wh on the instance", "statistic": "mean measured minus conditional expectation"}
        if sm.get("combined_z_measured_minus_conditional") is not None:
            out[f"e3cond/{check}/combined_z"] = {**base, "value": sm["combined_z_measured_minus_conditional"], "unit": "z",
                                                 "statistic": "combined z of measured minus conditional"}
    return out


def main() -> None:
    numbers = json.loads(PAPER_NUMBERS.read_text(encoding="utf-8"))["numbers"]
    share_numbers = json.loads(POSTHOC_SHARE.read_text(encoding="utf-8"))["numbers"]
    out = {}
    out.update(prop3_shortfall(numbers))
    out.update(confirm_dev())
    out.update(share_fall())
    out.update(sllf_exact())
    boot = Bootstrap()
    out.update(factorial3(boot))
    out.update(e1_fixed(boot, numbers))
    out.update(exchange(boot, numbers, share_numbers))
    out.update(cellf_delay(boot))
    out.update(si_numbers(numbers, share_numbers, out))
    out.update(e3cond())
    commit = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    meta = {"label": LABEL, "label_phase2": LABEL_P2, "git": {"commit": commit},
            "bootstrap": {"n_boot": boot.n_boot, "seed": boot.seed, "level": boot.level},
            "inputs_sha256": {str(p): hashlib.sha256(p.read_bytes()).hexdigest()
                              for p in (PAPER_NUMBERS, CONFIRM_DEV, SLLF_EXACT, ROWS, EXTRA_ROWS, RANKER_ROWS,
                                        RANKER_NUMBERS, POSTHOC_SHARE, E3_COND)}}
    OUT.write_text(json.dumps({"meta": meta, "numbers": out}, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    for k, e in out.items():
        lo, hi = e.get("ci_lo"), e.get("ci_hi")
        print(k, round(float(e["value"]), 4), "" if lo is None else f"[{lo:.3f}, {hi:.3f}]", e.get("point", ""))


if __name__ == "__main__":
    main()
