#!/usr/bin/env python3
"""Render docs/DEV_TABLES.md from results/paper_numbers.json.

Usage: uv run python scripts/make_dev_tables.py

Reads results/paper_numbers.json only. Standard library only: it does not import papere,
generate instances, or run any simulation. Overwrites docs/DEV_TABLES.md.

Number format: ``value [ci_lo, ci_hi]`` with two decimals when the file stores an interval,
``value`` alone otherwise. Counts are integers, flags are yes/no, and a key the file does not
store is shown as an em dash. The E3 z-score is derived here as (measured - predicted) / mc_se
because the file does not store it.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "results" / "paper_numbers.json"
OUT = ROOT / "docs" / "DEV_TABLES.md"

HEADER_LINE = ("All numbers are development; generated from results/paper_numbers.json "
               "by scripts/make_dev_tables.py; do not edit by hand.")
DASH = "—"

STRATA = ["M0_rho0.95", "M0_rho1.15", "M3_rho0.95", "M3_rho1.15"]
DELTAS = [0, 1, 2, 4]
POLICY_ORDER = [
    "bound", "guarded_mpc_e1", "oracle_mpc", "pop_mpc", "mpc_ce", "mpc_pes", "sym_margin",
    "ce_llf", "ce_edf", "pes_llf", "persistence", "uncorr_pes", "probe_first", "floor",
    "user_flag", "rwdf_e", "rwdf_e_literal", "llf_post",
]
POLICY_LABEL = {"guarded_mpc_e1": "guarded_mpc_e1 (candidate)"}
CELL_METRICS = [
    ("R_avoid_kwh_per100", "R_avoid (kWh/100)"),
    ("violation_count_per100", "Violations (count/100)"),
    ("violation_kwslot", "Violation (kW·slot)"),
    ("violation_longest_run_slots", "Longest violation run (slots)"),
    ("hedge_waste_kwslot", "Hedge waste (kW·slot)"),
    ("deadline_miss_count_per100", "Deadline misses (count/100)"),
    ("deadline_miss_kwh_per100", "Deadline-miss energy (kWh/100)"),
    ("peak_kw", "Peak (kW)"),
    ("cpu_ms_mean", "CPU ms per decision (mean)"),
    ("event_shortfall_kwh_per100", "Event shortfall (kWh/100)"),
    ("R_corr_hi_kwh_per100", "R_corr hi (kWh/100)"),
    ("R_corr_lo_kwh_per100", "R_corr lo (kWh/100)"),
    ("R_uncorr_hi_kwh_per100", "R_uncorr hi (kWh/100)"),
    ("R_uncorr_lo_kwh_per100", "R_uncorr lo (kWh/100)"),
]
CELL_RE = re.compile(
    r"^(?P<fam>F0R|SCALE)_M(?P<M>\d+)_dA(?P<dA>\d+)_db(?P<db>\d+)"
    r"_rho(?P<rho>[\d.]+)_r(?P<r>[\d.]+)$"
)


# ---------------------------------------------------------------- formatting helpers

def num(x: float) -> str:
    s = f"{x:.2f}"
    return "0.00" if s == "-0.00" else s


def fmt(e: dict | None, interval: bool = True) -> str:
    if not e or e.get("value") is None:
        return DASH
    s = num(e["value"])
    lo, hi = e.get("ci_lo"), e.get("ci_hi")
    if interval and lo is not None and hi is not None:
        s += f" [{num(lo)}, {num(hi)}]"
    return s


def count(e: dict | None) -> str:
    if not e or e.get("value") is None:
        return DASH
    return str(int(round(e["value"])))


def flag(e: dict | None) -> str:
    if not e:
        return DASH
    if "supported" in e:
        return "yes" if e["supported"] else "no"
    return "yes" if e.get("value") else "no"


def reading(e: dict | None) -> str:
    return (e or {}).get("reading") or DASH


def bo_text(bo) -> str:
    if bo is None:
        return DASH
    if isinstance(bo, dict):
        return "; ".join(f"δ{k}: {bo[k]}" for k in sorted(bo, key=int))
    return str(bo)


def esc(c) -> str:
    return str(c).replace("|", "\\|").replace("\n", " ")


def table(headers: list[str], rows: list[list]) -> str:
    for r in rows:
        assert len(r) == len(headers), (headers, r)
    lines = ["| " + " | ".join(headers) + " |",
             "| " + " | ".join("---" for _ in headers) + " |"]
    lines += ["| " + " | ".join(esc(c) for c in r) + " |" for r in rows]
    return "\n".join(lines)


def cell_sort_key(cell: str):
    m = CELL_RE.match(cell)
    if not m:
        return (9, cell)
    return (int(m["M"]), int(m["dA"]), int(m["db"]), float(m["rho"]), float(m["r"]))


def cell_desc(cell: str) -> str:
    m = CELL_RE.match(cell)
    if not m:
        return cell
    return f"M = {m['M']}, δ_A = {m['dA']}, δ_b = {m['db']}, ρ = {m['rho']}, r = {m['r']}"


def stratum_label(s: str) -> str:
    M, rho = s.split("_")
    return f"M = {M[1:]}, ρ = {rho[3:]}"


def order_policies(present: set[str]) -> list[str]:
    known = [p for p in POLICY_ORDER if p in present]
    extra = sorted(present - set(POLICY_ORDER))
    return known + extra


# ---------------------------------------------------------------- sections

def section_e1(G) -> list[str]:
    rows = []
    for s in STRATA:
        p = G(f"e1/primary/{s}/contrast")
        f = G(f"e1/sensitivity_floor/{s}/contrast")
        m = G(f"e1/sensitivity_min_e1/{s}/contrast")
        o = G(f"e1/primary/{s}/oracle_contrast")
        rows.append([
            stratum_label(s),
            fmt(p), reading(p), bo_text((p or {}).get("best_oblivious")),
            fmt(f), reading(f),
            fmt(m), reading(m), bo_text((m or {}).get("best_oblivious")),
            fmt(o),
        ])
    headers = [
        "Stratum",
        "Primary contrast", "Primary reading", "Primary best oblivious (by δ_A)",
        "Floor-included contrast", "Floor-included reading",
        "Min-E1 contrast", "Min-E1 reading", "Min-E1 best oblivious (by δ_A)",
        "Oracle contrast",
    ]
    return [
        "## 1. E1 by stratum",
        "",
        "Contrast = mean gap over δ_A ∈ {2, 4} minus mean gap over δ_A ∈ {0, 1}, in kWh per 100 "
        "per event. Primary uses the best oblivious policy fixed on the tuning seeds. Floor-included "
        "lets the floor be chosen. Min-E1 uses the oblivious member that minimizes E1 itself. "
        "Oracle replaces the candidate with oracle_mpc.",
        "",
        table(headers, rows),
        "",
    ]


def section_e1_gaps(G) -> list[str]:
    rows = []
    for s in STRATA:
        for d in DELTAS:
            g = G(f"e1/primary/{s}/gap_dA{d}")
            og = G(f"e1/primary/{s}/oracle_gap_dA{d}")
            rows.append([
                stratum_label(s), d,
                fmt(g), (g or {}).get("best_oblivious") or DASH,
                fmt(og),
            ])
    headers = ["Stratum", "δ_A", "Gap: best oblivious − candidate",
               "Best oblivious", "Oracle gap: best oblivious − oracle_mpc"]
    return [
        "## 2. Per-δ gaps and oracle gaps",
        "",
        "kWh per 100 per event, primary selection. Gap = R_avoid(best oblivious) − "
        "R_avoid(guarded_mpc_e1). Oracle gap = R_avoid(best oblivious) − R_avoid(oracle_mpc).",
        "",
        table(headers, rows),
        "",
    ]


def section_e2(G) -> list[str]:
    rows = []
    for s in STRATA:
        for label, tag in [("δ_A = 2", "dA2"), ("δ_A = 4", "dA4"), ("contrast", "contrast")]:
            base = f"e2/{s}/{tag}"
            rows.append([
                stratum_label(s), label,
                fmt(G(f"{base}/readingA/gain_uncorr")),
                fmt(G(f"{base}/readingA/gain_corr")),
                fmt(G(f"{base}/readingA/diff")),
                fmt(G(f"{base}/readingB/gain_uncorr")),
                fmt(G(f"{base}/readingB/gain_corr")),
                fmt(G(f"{base}/readingB/diff")),
                flag(G(f"{base}/supported")),
            ])
    headers = [
        "Stratum", "Row",
        "A: gain uncorr", "A: gain corr", "A: diff",
        "B: gain uncorr", "B: gain corr", "B: diff",
        "Supported (both readings)",
    ]
    return [
        "## 3. E2 by stratum, δ_A ∈ {2, 4} and contrast",
        "",
        "kWh per 100 per event. gain = best oblivious minus candidate. Reading A and reading B "
        "are the two readings of the E2 prediction. A prediction is supported only if it holds "
        "under both readings.",
        "",
        table(headers, rows),
        "",
    ]


def parse_e3_point(key: str):
    _, check, cap, q, c, M = key.split("/")
    return check, cap, float(q[1:]), int(c[1:]), int(M[1:])


def section_e3(N) -> list[str]:
    G = N.get
    S = lambda k: G(f"e3/summary/{k}")  # noqa: E731

    summary_rows = [
        ["Points", count(S("n_points"))],
        ["Simultaneous passes (primary rule: Bonferroni 95% interval)", count(S("n_pass"))],
        ["Simultaneous failures", count(S("n_fail"))],
        ["Pointwise misses (predicted outside the percentile interval)",
         count(S("n_pointwise_misses"))],
        ["Expected failures by chance", fmt(S("expected_failures_by_chance"), interval=False)],
        ["Binomial p (upper)", fmt(S("binomial_p_upper"), interval=False)],
    ]

    check_rows = []
    for check in ["R_pop", "gap_oracle", "gap_e1"]:
        e = S(f"{check}/n_pass")
        if not e:
            check_rows.append([check, DASH, DASH, DASH, DASH])
            continue
        points = int(e.get("points", 0))
        pw = int(e.get("pass_pointwise", 0))
        check_rows.append([check, points, count(e), pw, points - pw])

    points = {k: v for k, v in N.items()
              if k.startswith("e3/") and not k.startswith("e3/summary/")}

    misses = []
    for key, v in points.items():
        if v.get("passed_pointwise"):
            continue
        check, cap, q, c, M = parse_e3_point(key)
        se = v.get("mc_se")
        z = DASH if not se else num((v["value"] - v["predicted"]) / se)
        misses.append((check, cap, q, c, M, key, v, z))
    misses.sort(key=lambda t: (t[0], t[1], t[2], t[3], t[4]))
    miss_rows = [[check, cap, f"{q:g}", c, M, fmt(v), num(v["predicted"]), z,
                  v.get("predicted_by", DASH), "yes" if v.get("passed") else "no"]
                 for check, cap, q, c, M, key, v, z in misses]

    # Stored pointwise flags are used as-is; report any disagreement with the printed interval.
    disagree = [k for k, v in points.items()
                if (v["ci_lo"] <= v["predicted"] <= v["ci_hi"]) != bool(v["passed_pointwise"])]

    lines = [
        "## 4. E3 summary and pointwise misses",
        "",
        "E3 summary fields are stored in `numbers` under `e3/summary/*`, not in `meta`. "
        "Simultaneous passes use the Bonferroni 95% interval, which is the primary rule. "
        "Pointwise misses use the percentile interval for the measured value.",
        "",
        table(["Summary", "Value"], summary_rows),
        "",
        "Per check (points inside the simultaneous interval; pointwise passes; pointwise misses):",
        "",
        table(["Check", "Points", "Simultaneous passes", "Pointwise passes", "Pointwise misses"],
              check_rows),
        "",
        f"Every pointwise miss ({len(miss_rows)}). Units on the instance (1 unit = 0.25 kWh). "
        "z is derived here as (measured − predicted) / mc_se; the file does not store it. A "
        "z of about 1.9 can still be a pointwise miss, because the pointwise rule is the "
        "percentile interval and not z.",
        "",
        table(["Check", "Cap mode", "q", "c", "M", "Measured [CI]", "Predicted", "z (derived)",
               "Predicted by", "Simultaneous pass"], miss_rows),
        "",
    ]
    if disagree:
        lines += [f"Note: {len(disagree)} point(s) where the stored pointwise flag differs from "
                  "the printed-interval test (floating-point edge): " + ", ".join(sorted(disagree))
                  + ". The stored flag is used.", ""]
    return lines


def section_cells(N) -> list[str]:
    G = N.get
    cells = sorted({k.split("/")[1] for k in N if k.startswith("cell/")}, key=cell_sort_key)
    lines = [
        "## 5. Per-cell policy tables (F0-R cells)",
        "",
        "One table per cell. Each row is a policy, in the family order given in the spec. "
        "Values are cell means across seeds, with the stored interval where one exists.",
        "",
    ]
    for cell in cells:
        pols = order_policies({k.split("/")[2] for k in N if k.startswith(f"cell/{cell}/")})
        headers = ["Policy"] + [label for _, label in CELL_METRICS]
        rows = []
        for p in pols:
            rows.append([POLICY_LABEL.get(p, p)]
                        + [fmt(G(f"cell/{cell}/{p}/{metric}")) for metric, _ in CELL_METRICS])
        lines += [f"### {cell}", "", cell_desc(cell), "", table(headers, rows), ""]
    return lines


def section_secondary(N) -> list[str]:
    G = N.get
    lines = ["## 6. Floor trade-off, return-probability sweep, lag split and RWDF-E", ""]

    # 6a floor trade-off
    floor_cells = sorted({k.split("/")[2] for k in N if k.startswith("secondary/floor/")},
                         key=cell_sort_key)
    rows = []
    for cell in floor_cells:
        sf = G(f"secondary/floor/{cell}/event_shortfall")
        ng = G(f"secondary/floor/{cell}/net_recovery_gain")
        rows.append([cell, (ng or {}).get("best_oblivious") or DASH,
                     fmt(sf), fmt(ng)])
    lines += [
        "### 6a. Floor trade-off",
        "",
        "Event shortfall is the floor's mean shortfall (kWh per 100 per event). Net recovery "
        "gain is R_avoid(best oblivious) − R_avoid(floor). The two are reported side by side "
        "and are never summed.",
        "",
        table(["Cell", "Best oblivious", "Floor event shortfall", "Net recovery gain"], rows),
        "",
    ]

    # 6b return-probability sweep
    sweep_rows = []
    for r_key, r_val in [("r0", "0"), ("r0.3", "0.3"), ("r1", "1")]:
        g = G(f"secondary/r_sweep/{r_key}/gap")
        og = G(f"secondary/r_sweep/{r_key}/oracle_gap")
        sweep_rows.append([r_val, f"F0R_M3_dA2_db0_rho0.95_{r_key}", fmt(g),
                           (g or {}).get("best_oblivious") or DASH, fmt(og)])
    lines += [
        "### 6b. Return-probability sweep (M = 3, δ_A = 2, ρ = 0.95)",
        "",
        table(["r", "Cell", "Gap: best oblivious − candidate", "Best oblivious",
               "Oracle gap: best oblivious − oracle_mpc"], sweep_rows),
        "",
    ]

    # 6c lag-split cell
    lag_cell = "F0R_M3_dA0_db2_rho0.95_r0.3"
    lg = G("secondary/lag_split/gap")
    lo = G("secondary/lag_split/oracle_gap")
    bo = (lg or {}).get("best_oblivious") or DASH
    lag_rows = [
        ["Gap: best oblivious − candidate", bo, fmt(lg)],
        ["Oracle gap: best oblivious − oracle_mpc", bo, fmt(lo)],
        ["R_avoid, candidate", "guarded_mpc_e1",
         fmt(G(f"cell/{lag_cell}/guarded_mpc_e1/R_avoid_kwh_per100"))],
        ["R_avoid, best oblivious", bo,
         fmt(G(f"cell/{lag_cell}/{bo}/R_avoid_kwh_per100")) if bo != DASH else DASH],
        ["R_avoid, oracle", "oracle_mpc",
         fmt(G(f"cell/{lag_cell}/oracle_mpc/R_avoid_kwh_per100"))],
    ]
    lines += [
        f"### 6c. Lag-split cell (δ_A = 0, δ_b = 2): `{lag_cell}`",
        "",
        table(["Quantity", "Policy", "Value"], lag_rows),
        "",
    ]

    # 6d RWDF-E vs RWDF-E literal
    rwdf_cells = sorted({k.split("/")[2] for k in N if k.startswith("secondary/rwdf/")},
                        key=cell_sort_key)
    rw_rows = []
    for cell in rwdf_cells:
        rw_rows.append([
            cell,
            fmt(G(f"secondary/rwdf/{cell}/rwdf_e")),
            fmt(G(f"secondary/rwdf/{cell}/rwdf_e_literal")),
            fmt(G(f"secondary/rwdf/{cell}/literal_minus_rwdf_e")),
        ])
    lines += [
        "### 6d. RWDF-E vs RWDF-E literal",
        "",
        "R_avoid in kWh per 100 per event. Literal − RWDF-E is the stored difference.",
        "",
        table(["Cell", "RWDF-E R_avoid", "RWDF-E literal R_avoid", "Literal − RWDF-E"], rw_rows),
        "",
    ]
    return lines


def section_scale(N) -> list[str]:
    G = N.get
    cells = sorted({k.split("/")[1] for k in N if k.startswith("scale/")}, key=cell_sort_key)
    lines = [
        "## 7. Scaling (N = 300)",
        "",
        "Per scale cell and policy. CPU ms per decision: mean and max, as stored (per-seed mean "
        "and per-seed max, averaged over seeds). R_avoid in kWh per 100 per event. Seeds per "
        "cell: 20.",
        "",
    ]
    for cell in cells:
        pols = order_policies({k.split("/")[2] for k in N if k.startswith(f"scale/{cell}/")})
        rows = []
        for p in pols:
            rows.append([
                POLICY_LABEL.get(p, p),
                fmt(G(f"scale/{cell}/{p}/R_avoid_kwh_per100")),
                fmt(G(f"scale/{cell}/{p}/cpu_ms_mean")),
                fmt(G(f"scale/{cell}/{p}/cpu_ms_max")),
            ])
        lines += [f"### {cell}", "", cell_desc(cell), "",
                  table(["Policy", "R_avoid (kWh/100)", "CPU ms per decision (mean)",
                         "CPU ms per decision (max)"], rows), ""]
    return lines


def provenance(meta: dict) -> list[str]:
    b = meta.get("bootstrap", {})
    git = meta.get("git", {})
    inp = meta.get("inputs", {})
    lines = [
        "## Provenance and conventions",
        "",
        f"- Source: `results/paper_numbers.json`, generated {meta.get('generated_utc', DASH)}, "
        f"git {str(git.get('commit', DASH))[:7]} (dirty: {git.get('dirty', DASH)}), "
        f"label {meta.get('label', DASH)}.",
        f"- Bootstrap (per `meta`): {b.get('n_boot', DASH)} resamples, seed {b.get('seed', DASH)}, "
        f"level {b.get('level', DASH)}, unit {b.get('unit', DASH)}, {b.get('interval', DASH)} "
        "interval.",
        f"- Threshold: {meta.get('threshold_kwh_per100', DASH)} kWh per 100.",
    ]
    for name in ["f0r", "kcopy", "scale"]:
        i = inp.get(name)
        if i:
            lines.append(f"- Input `{name}`: `{i.get('path')}`, {i.get('rows_kept')} rows kept "
                         f"of {i.get('rows')}, seeds {i.get('seed_range')}.")
    warns = meta.get("warnings") or []
    lines.append(f"- Warnings in `meta`: {len(warns)}.")
    lines += [
        "- `value [lo, hi]` is the stored value with its stored interval. A bare value means "
        "no interval is stored. Two decimals throughout, except counts (integers) and flags "
        "(yes/no). `—` means the file does not store that key.",
        "- Units: kWh per 100 per event unless stated. CPU in ms. E3 in units on the instance "
        "(1 unit = 0.25 kWh).",
        "",
    ]
    return lines


def main() -> None:
    data = json.loads(SRC.read_text(encoding="utf-8"))
    meta, N = data["meta"], data["numbers"]
    G = N.get

    out: list[str] = [
        "# Development tables",
        "",
        HEADER_LINE,
        "",
    ]
    out += provenance(meta)
    out += section_e1(G)
    out += section_e1_gaps(G)
    out += section_e2(G)
    out += section_e3(N)
    out += section_cells(N)
    out += section_secondary(N)
    out += section_scale(N)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(out).rstrip() + "\n", encoding="utf-8")
    print(f"wrote {OUT} ({OUT.stat().st_size} bytes, {len(N)} numbers read)")


if __name__ == "__main__":
    main()
