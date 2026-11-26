"""End-to-end ACN-Data / PK / PA experiment runner: T1, T3, T2 (and variants), and analysis.

Writes all outputs under ``results/acn/<run_name>/``:
- ``cleaning.json``
- ``t1.json``
- ``t3.json`` (ACN only)
- ``t2_rows.jsonl`` and ``t2_manifest.json`` (ACN, and PA when >= 20 eligible T2 site-days)
- ``t2_emp_rows.jsonl`` and ``t2_emp_manifest.json`` (ACN only, unless skipped)
- ``real_limit_rows.jsonl`` and ``real_limit_manifest.json`` (ACN only, unless skipped)
- ``t2_analysis.json`` (when T2 runs)
- ``summary.json``
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import time

from papere.acn.analyse import T2_BOOT_SEED, analyse_files
from papere.acn.instances import (
    T2_MIN_PARTICIPANTS,
    build_t2_site_days,
    compute_site_real_limits,
)
from papere.acn.load import DEFAULT_DATA_DIR, DEFAULT_SITES, eligible_site_days, load_all_sites
from papere.acn.pa import (
    DEFAULT_AMENDMENT_4_PATH,
    DEFAULT_PA_CSV,
    PA_DEFAULT_SEEDS,
    PA_MIN_T2_SITE_DAYS,
    PA_T1_BOOT_SEED,
    PA_T2_BOOT_SEED,
    load_pa_sites,
    summarize_pa_cleaning,
)
from papere.acn.pk import (
    DEFAULT_AMENDMENT_1_PATH,
    DEFAULT_AMENDMENT_2_PATH,
    DEFAULT_AMENDMENT_3_PATH,
    DEFAULT_PK_CSV,
    PK_T1_BOOT_SEED,
    PK_T2_BOOT_SEED,
    load_pk_sites,
    summarize_pk_cleaning,
)
from papere.acn.run_t2 import protocol_sha256, resolve_t2_cells, run_t2
from papere.acn.t1 import T1_BOOT_SEED, evaluate_t1
from papere.acn.t3 import evaluate_t3
from papere.runner import REPO_ROOT, _write_json_atomic, parse_seeds


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Run Paper E ACN-Data experiments (T1, T3, T2).")
    ap.add_argument(
        "--dataset",
        choices=("acn", "pk", "pa"),
        default="acn",
        help=(
            "Dataset to run: 'acn' (default, base protocol), "
            "'pk' (Perth & Kinross, T1 only per amendment 3), or "
            "'pa' (City of Palo Alto, T1 + T2 per amendment 4)"
        ),
    )
    ap.add_argument("--run-name", required=True, help="Output subfolder under results/acn/")
    ap.add_argument(
        "--seeds",
        default=None,
        help=(
            "Seed range A-B (inclusive) or single seed A "
            "(required for acn; defaults to 730000-730199 for pa; unused for pk T1-only)"
        ),
    )
    ap.add_argument(
        "--sites",
        default=None,
        help=(
            "Site filter: comma-separated for acn (default: caltech,jpl,office001); "
            "semicolon-separated for pk and pa (default: all sites)"
        ),
    )
    ap.add_argument(
        "--data-dir",
        type=Path,
        default=DEFAULT_DATA_DIR,
        help="Directory holding acn_<site>.json.gz files (acn dataset)",
    )
    ap.add_argument(
        "--pk-csv",
        type=Path,
        default=DEFAULT_PK_CSV,
        help="Path to Perth & Kinross CSV file (pk dataset)",
    )
    ap.add_argument(
        "--pa-csv",
        type=Path,
        default=DEFAULT_PA_CSV,
        help="Path to Palo Alto CSV file (pa dataset)",
    )
    ap.add_argument(
        "--out-root",
        type=Path,
        default=REPO_ROOT / "results" / "acn",
        help="Base output directory (default: results/acn)",
    )
    ap.add_argument(
        "--cells",
        default=None,
        help="Comma-separated T2 cell IDs (default: all 16 protocol cells)",
    )
    ap.add_argument("--workers", type=int, default=1, help="Worker processes for T2")
    ap.add_argument(
        "--max-sessions-per-site",
        type=int,
        default=None,
        help="Optional cap on cleaned sessions kept per site (smoke tests)",
    )
    ap.add_argument(
        "--max-site-days",
        type=int,
        default=None,
        help="Optional cap on eligible site-days used (smoke tests)",
    )
    ap.add_argument(
        "--min-participants",
        type=int,
        default=T2_MIN_PARTICIPANTS,
        help="Minimum T2 participants per site-day (default: 5, per protocol)",
    )
    ap.add_argument(
        "--min-t2-site-days",
        type=int,
        default=None,
        help=(
            "Minimum eligible T2 site-days required to run T2 "
            "(default: 20 for pa per amendment 4; 1 for acn)"
        ),
    )
    ap.add_argument("--n-boot-t1", type=int, default=10_000, help="T1 bootstrap resamples")
    ap.add_argument("--n-boot-t2", type=int, default=10_000, help="T2 bootstrap resamples")
    ap.add_argument("--skip-t1", action="store_true", help="Skip T1")
    ap.add_argument("--skip-t3", action="store_true", help="Skip T3")
    ap.add_argument("--skip-t2-emp", action="store_true", help="Skip T2-emp variant")
    ap.add_argument("--skip-real-limit", action="store_true", help="Skip real-limit variant")
    ap.add_argument(
        "--t2-emp-source",
        choices=("h3_users", "all_users"),
        default="h3_users",
        help="Which T3 beta-binomial fit supplies (alpha, beta) for T2-emp",
    )
    ap.add_argument(
        "--smoke-quiet",
        action="store_true",
        help="Print only counts and timings (never print shares or rates)",
    )
    args = ap.parse_args(argv)
    if args.seeds is None:
        if args.dataset == "pa":
            args.seeds = PA_DEFAULT_SEEDS
        elif args.dataset == "acn":
            ap.error("--seeds is required for --dataset acn")
    return args


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    is_pk = args.dataset == "pk"
    is_pa = args.dataset == "pa"

    t1_boot_seed = (
        PK_T1_BOOT_SEED if is_pk else (PA_T1_BOOT_SEED if is_pa else T1_BOOT_SEED)
    )
    t2_boot_seed = (
        PA_T2_BOOT_SEED if is_pa else (PK_T2_BOOT_SEED if is_pk else T2_BOOT_SEED)
    )
    skip_t3 = True if (is_pk or is_pa) else args.skip_t3
    skip_t2_emp = True if (is_pk or is_pa) else args.skip_t2_emp
    skip_real_limit = True if (is_pk or is_pa) else args.skip_real_limit

    out_dir = Path(args.out_root) / args.run_name
    out_dir.mkdir(parents=True, exist_ok=True)
    timings: dict[str, float] = {}

    # 1. Load & clean
    t0 = time.perf_counter()
    if is_pk:
        site_filter = (
            [s.strip() for s in args.sites.split(";") if s.strip()] if args.sites else None
        )
        sessions_by_site, reports = load_pk_sites(
            csv_path=args.pk_csv,
            sites=site_filter,
            max_sessions_per_site=args.max_sessions_per_site,
        )
        sites = sorted(sessions_by_site.keys())
        timings["load_s"] = time.perf_counter() - t0
        pooled_clean = summarize_pk_cleaning(reports)
        cleaning_blob = {
            "pooled": pooled_clean.as_dict(),
            "sites": {site: rep.as_dict() for site, rep in reports.items()},
        }
    elif is_pa:
        site_filter = (
            [s.strip() for s in args.sites.split(";") if s.strip()] if args.sites else None
        )
        sessions_by_site, reports = load_pa_sites(
            csv_path=args.pa_csv,
            sites=site_filter,
            max_sessions_per_site=args.max_sessions_per_site,
        )
        sites = sorted(sessions_by_site.keys())
        timings["load_s"] = time.perf_counter() - t0
        pooled_clean = summarize_pa_cleaning(reports)
        cleaning_blob = {
            "pooled": pooled_clean.as_dict(),
            "sites": {site: rep.as_dict() for site, rep in reports.items()},
        }
    else:
        sites_str = args.sites if args.sites is not None else ",".join(DEFAULT_SITES)
        sites = [s.strip() for s in sites_str.split(",") if s.strip()]
        sessions_by_site, reports = load_all_sites(
            sites=sites,
            data_dir=args.data_dir,
            max_sessions_per_site=args.max_sessions_per_site,
        )
        timings["load_s"] = time.perf_counter() - t0
        cleaning_blob = {site: rep.as_dict() for site, rep in reports.items()}
    _write_json_atomic(out_dir / "cleaning.json", cleaning_blob)

    # Full eligible weekday site-day counts per site (counts only, prior to any smoke cap).
    all_t1_site_days_by_site = {
        site: eligible_site_days(sessions_by_site[site]) for site in sites
    }

    # 2. T1
    t1_res = None
    if not args.skip_t1:
        t0 = time.perf_counter()
        if (is_pk or is_pa) and args.max_site_days is not None:
            # Cap T1 to at most max_site_days eligible site-days for smoke runs.
            all_days = [sd for site in sites for sd in all_t1_site_days_by_site[site]]
            capped_keys = {(sd.site, sd.local_date) for sd in all_days[: int(args.max_site_days)]}
            t1_sessions = {
                site: [s for s in sessions_by_site[site] if (site, s.local_date) in capped_keys]
                for site in sites
            }
        else:
            t1_sessions = sessions_by_site
        t1_res = evaluate_t1(t1_sessions, n_boot=args.n_boot_t1, boot_seed=t1_boot_seed)
        timings["t1_s"] = time.perf_counter() - t0
        _write_json_atomic(out_dir / "t1.json", t1_res)

    # Amendment 3: Perth & Kinross runs T1 only (no T2, no T3).
    if is_pk:
        pk_summary = {
            "dataset": args.dataset,
            "run_name": args.run_name,
            "out_dir": str(out_dir),
            "status": "t1_only",
            "t2_runnable": False,
            "t2_skip_reason": "amendment_3_pk_t1_only",
            "protocol_sha256": protocol_sha256(),
            "amendment_1_sha256": protocol_sha256(DEFAULT_AMENDMENT_1_PATH),
            "amendment_2_sha256": protocol_sha256(DEFAULT_AMENDMENT_2_PATH),
            "amendment_3_sha256": protocol_sha256(DEFAULT_AMENDMENT_3_PATH),
            "sites": sites,
            "t1_boot_seed": t1_boot_seed,
            "eligible_site_days_per_site": {
                site: len(all_t1_site_days_by_site[site]) for site in sites
            },
            "cleaning_pooled": cleaning_blob["pooled"],
            "cleaning_kept_counts": {s: reports[s].kept_count for s in sites},
            "t1_pooled_site_days": t1_res["meta"]["pooled_site_day_count"] if t1_res else None,
            "t3_pooled_events": None,
            "t2_rows_written": 0,
            "t2_emp_rows_written": 0,
            "real_limit_rows_written": 0,
            "timings_s": timings,
        }
        _write_json_atomic(out_dir / "summary.json", pk_summary)
        if args.smoke_quiet:
            print(json.dumps(pk_summary, indent=2))
        else:
            print(f"Run {args.run_name} (pk, T1 only per amendment 3) complete -> {out_dir}")
            print(f"  sites: {len(sites)}, T1 pooled site-days: {pk_summary['t1_pooled_site_days']}")
            print(f"  timings (s): { {k: round(v, 3) for k, v in timings.items()} }")
        return 0

    lo, hi = parse_seeds(args.seeds)
    seeds = list(range(lo, hi + 1))
    cell_ids = [c.strip() for c in args.cells.split(",") if c.strip()] if args.cells else None
    cells = resolve_t2_cells(cell_ids)

    # 3. T3 (ACN only; not applicable to PA per amendment 4)
    t3_res = None
    if not skip_t3:
        t0 = time.perf_counter()
        t3_res = evaluate_t3(sessions_by_site)
        timings["t3_s"] = time.perf_counter() - t0
        _write_json_atomic(out_dir / "t3.json", t3_res)

    # 4. T2 eligible site-days & amendment 4 gate
    t0 = time.perf_counter()
    all_t2_site_days = build_t2_site_days(
        sessions_by_site, min_participants=args.min_participants
    )
    t2_site_days_per_site = {site: 0 for site in sites}
    for sd in all_t2_site_days:
        t2_site_days_per_site[sd.site] = t2_site_days_per_site.get(sd.site, 0) + 1
    timings["site_days_s"] = time.perf_counter() - t0

    min_t2_site_days = (
        int(args.min_t2_site_days)
        if args.min_t2_site_days is not None
        else (PA_MIN_T2_SITE_DAYS if is_pa else 1)
    )

    if is_pa and len(all_t2_site_days) < min_t2_site_days:
        pa_skip_summary = {
            "dataset": args.dataset,
            "run_name": args.run_name,
            "out_dir": str(out_dir),
            "status": "t2_not_runnable",
            "t2_runnable": False,
            "t2_skip_reason": (
                f"fewer than {min_t2_site_days} eligible T2 site-days "
                f"({len(all_t2_site_days)} < {min_t2_site_days})"
            ),
            "protocol_sha256": protocol_sha256(),
            "amendment_3_sha256": protocol_sha256(DEFAULT_AMENDMENT_3_PATH),
            "amendment_4_sha256": protocol_sha256(DEFAULT_AMENDMENT_4_PATH),
            "sites": sites,
            "seeds": [lo, hi],
            "n_seeds": len(seeds),
            "t1_boot_seed": t1_boot_seed,
            "t2_boot_seed": t2_boot_seed,
            "cells": [c.cell_id for c in cells],
            "min_participants": int(args.min_participants),
            "min_t2_site_days": min_t2_site_days,
            "n_t2_site_days": 0,
            "n_t2_site_days_total": len(all_t2_site_days),
            "eligible_site_days_per_site": {
                site: len(all_t1_site_days_by_site[site]) for site in sites
            },
            "t2_eligible_site_days_per_site": t2_site_days_per_site,
            "cleaning_pooled": cleaning_blob["pooled"],
            "cleaning_kept_counts": {s: reports[s].kept_count for s in sites},
            "t1_pooled_site_days": t1_res["meta"]["pooled_site_day_count"] if t1_res else None,
            "t3_pooled_events": None,
            "t2_rows_written": 0,
            "t2_emp_rows_written": 0,
            "real_limit_rows_written": 0,
            "timings_s": timings,
        }
        _write_json_atomic(out_dir / "summary.json", pa_skip_summary)
        if args.smoke_quiet:
            print(json.dumps(pa_skip_summary, indent=2))
        else:
            print(
                f"Run {args.run_name} (pa): T2 skipped ({len(all_t2_site_days)} eligible T2 "
                f"site-days < {min_t2_site_days}) -> {out_dir}"
            )
        return 0

    site_days = (
        all_t2_site_days[: int(args.max_site_days)]
        if args.max_site_days is not None
        else all_t2_site_days
    )
    if not site_days:
        raise SystemExit("No eligible T2 site-days found for the selected sites/caps.")

    # 5. T2 primary
    t2_rows_path = out_dir / "t2_rows.jsonl"
    t0 = time.perf_counter()
    t2_manifest = run_t2(
        site_days,
        seeds,
        t2_rows_path,
        cells=cells,
        variant="t2",
        workers=args.workers,
        manifest_path=out_dir / "t2_manifest.json",
    )
    timings["t2_s"] = time.perf_counter() - t0

    # 6. T2-emp (uses T3 beta-binomial fit if available and finite; skipped for PA)
    t2_emp_rows_path: Path | None = None
    t2_emp_manifest = None
    if not skip_t2_emp and t3_res is not None:
        bb_key = (
            "beta_binomial_h3_users"
            if args.t2_emp_source == "h3_users"
            else "beta_binomial_all_users"
        )
        bb = t3_res["persistence_h3"][bb_key]
        alpha, beta = bb.get("alpha", math.nan), bb.get("beta", math.nan)
        if not (math.isfinite(alpha) and math.isfinite(beta) and alpha > 0 and beta > 0):
            bb_alt = t3_res["persistence_h3"]["beta_binomial_all_users"]
            alpha, beta = bb_alt.get("alpha", math.nan), bb_alt.get("beta", math.nan)
        if math.isfinite(alpha) and math.isfinite(beta) and alpha > 0 and beta > 0:
            t2_emp_rows_path = out_dir / "t2_emp_rows.jsonl"
            t0 = time.perf_counter()
            t2_emp_manifest = run_t2(
                site_days,
                seeds,
                t2_emp_rows_path,
                cells=cells,
                variant="t2_emp",
                emp_beta_ab=(alpha, beta),
                workers=args.workers,
                manifest_path=out_dir / "t2_emp_manifest.json",
            )
            timings["t2_emp_s"] = time.perf_counter() - t0

    # 7. Real-limit variant (skipped for PA per amendment 4)
    real_limit_rows_path: Path | None = None
    real_limit_manifest = None
    if not skip_real_limit:
        t0 = time.perf_counter()
        real_limits = compute_site_real_limits(sessions_by_site)
        timings["real_limits_compute_s"] = time.perf_counter() - t0
        if all(math.isfinite(real_limits.get(sd.site, math.nan)) for sd in site_days):
            real_limit_rows_path = out_dir / "real_limit_rows.jsonl"
            t0 = time.perf_counter()
            real_limit_manifest = run_t2(
                site_days,
                seeds,
                real_limit_rows_path,
                cells=cells,
                variant="real_limit",
                real_limits=real_limits,
                workers=args.workers,
                manifest_path=out_dir / "real_limit_manifest.json",
            )
            timings["real_limit_s"] = time.perf_counter() - t0

    # 8. Analyse T2 (and variants)
    t0 = time.perf_counter()
    analysis = analyse_files(
        t2_rows_path,
        t2_emp_rows_path=t2_emp_rows_path,
        real_limit_rows_path=real_limit_rows_path,
        n_boot=args.n_boot_t2,
        boot_seed=t2_boot_seed,
    )
    timings["analyse_s"] = time.perf_counter() - t0
    _write_json_atomic(out_dir / "t2_analysis.json", analysis)

    summary = {
        "dataset": args.dataset,
        "run_name": args.run_name,
        "out_dir": str(out_dir),
        "status": "complete",
        "t2_runnable": True,
        "protocol_sha256": protocol_sha256(),
        "sites": sites,
        "seeds": [lo, hi],
        "n_seeds": len(seeds),
        "t1_boot_seed": t1_boot_seed,
        "t2_boot_seed": t2_boot_seed,
        "cells": [c.cell_id for c in cells],
        "n_t2_site_days": len(site_days),
        "n_t2_site_days_total": len(all_t2_site_days),
        "eligible_site_days_per_site": {
            site: len(all_t1_site_days_by_site[site]) for site in sites
        },
        "t2_eligible_site_days_per_site": t2_site_days_per_site,
        "cleaning_kept_counts": {s: reports[s].kept_count for s in sites},
        "t1_pooled_site_days": t1_res["meta"]["pooled_site_day_count"] if t1_res else None,
        "t3_pooled_events": t3_res["pooled"]["n_events"] if t3_res else None,
        "t2_rows_written": t2_manifest["rows_written"],
        "t2_emp_rows_written": t2_emp_manifest["rows_written"] if t2_emp_manifest else 0,
        "real_limit_rows_written": (
            real_limit_manifest["rows_written"] if real_limit_manifest else 0
        ),
        "timings_s": timings,
    }
    if is_pa:
        summary["min_t2_site_days"] = min_t2_site_days
        summary["amendment_3_sha256"] = protocol_sha256(DEFAULT_AMENDMENT_3_PATH)
        summary["amendment_4_sha256"] = protocol_sha256(DEFAULT_AMENDMENT_4_PATH)
        summary["cleaning_pooled"] = cleaning_blob["pooled"]
    _write_json_atomic(out_dir / "summary.json", summary)

    if args.smoke_quiet:
        print(json.dumps(summary, indent=2))
    else:
        print(f"Run {args.run_name} complete -> {out_dir}")
        print(
            f"  site-days (T2): {len(site_days)}, seeds: {lo}-{hi} ({len(seeds)}), "
            f"cells: {len(cells)}"
        )
        print(f"  timings (s): { {k: round(v, 3) for k, v in timings.items()} }")
        h1 = analysis["t2"].get("h1")
        if h1 is not None:
            print(
                f"  T2 H1 share: {h1['share']:.3f} [{h1['share_ci'][0]:.3f}, "
                f"{h1['share_ci'][1]:.3f}] supported={h1.get('h1_supported')}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
