"""Post hoc round 3 runner and analyser: M6 (guard ablation) and M3 (failure persistence).

Contract: ``acn/POSTHOC_ROUND3_PROTOCOL.md``.
Writes rows and analysis JSON under ``results/posthoc_round3/`` (or a custom ``--out-dir``;
in ``--smoke`` mode defaults to ``results/posthoc_round3/smoke/``, uses seeds 799990-799994,
at most 3 site-days per real dataset, and prints counts, timings, and projected full-run
time only).

Examples
--------
Smoke run (safe, fast; prints counts and timings only):
  uv run python scripts/posthoc_round3.py --smoke --workers 4

Full protocol run (runs seeds 61000-61099 synthetic; 760000-760199 M6 real;
770000-770199 M3 real):
  uv run python scripts/posthoc_round3.py --workers 6
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import time

from papere import runner
from papere.acn.analyse import load_rows_file
from papere.acn.instances import T2_MIN_PARTICIPANTS, build_t2_site_days
from papere.acn.load import DEFAULT_DATA_DIR, DEFAULT_SITES, load_all_sites
from papere.acn.pa import DEFAULT_PA_CSV, load_pa_sites
from papere.acn.run_t2 import protocol_sha256, run_t2
from papere.posthoc_round3 import (
    DEFAULT_N_BOOT,
    M3_BOOT_SEED,
    M3_POLICIES,
    M3_REAL_SEEDS,
    M3_SYNTH_SEEDS,
    M6_BOOT_SEED,
    M6_POLICIES,
    M6_REAL_SEEDS,
    M6_SYNTH_SEEDS,
    SMOKE_MAX_SITE_DAYS,
    SMOKE_SEEDS,
    analyse_m3_rows,
    analyse_m6_rows,
    m3_cells,
    m6_cells,
)
from papere.runner import (
    DEFAULT_FROZEN_PATH,
    DEFAULT_PARAMS_PATH,
    REPO_ROOT,
    _file_sha,
    _write_json_atomic,
    load_params,
    parse_seeds,
)

DEFAULT_ROUND3_PROTOCOL = REPO_ROOT / "acn" / "POSTHOC_ROUND3_PROTOCOL.md"
DEFAULT_OUT_DIR = REPO_ROOT / "results" / "posthoc_round3"
ALL_DATASETS: tuple[str, ...] = ("synthetic", "acn", "pa")


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description="Run post hoc round 3 studies M6 (guard ablation) and M3 (failure persistence)."
    )
    ap.add_argument(
        "--study",
        choices=("both", "m6", "m3"),
        default="both",
        help="Which study to run (default: both)",
    )
    ap.add_argument(
        "--datasets",
        default="synthetic,acn,pa",
        help="Comma-separated datasets from {synthetic,acn,pa} (default: synthetic,acn,pa)",
    )
    ap.add_argument(
        "--out-dir",
        type=Path,
        default=None,
        help="Output directory (default: results/posthoc_round3, or results/posthoc_round3/smoke with --smoke)",
    )
    ap.add_argument("--workers", type=int, default=1, help="Worker processes (default: 1)")
    ap.add_argument("--n-boot", type=int, default=DEFAULT_N_BOOT, help="Bootstrap resamples (default: 10000)")
    ap.add_argument("--acn-data-dir", type=Path, default=DEFAULT_DATA_DIR, help="ACN JSON.gz directory")
    ap.add_argument("--pa-csv", type=Path, default=DEFAULT_PA_CSV, help="Palo Alto CSV path")
    ap.add_argument(
        "--max-site-days",
        type=int,
        default=None,
        help="Optional cap on eligible T2 site-days per real dataset (capped at 3 in --smoke)",
    )
    ap.add_argument(
        "--m6-synth-seeds",
        default=None,
        help="Override M6 synthetic seed range A-B (default: 61000-61099; 799990-799994 in --smoke)",
    )
    ap.add_argument(
        "--m6-real-seeds",
        default=None,
        help="Override M6 real-data seed range A-B (default: 760000-760199; 799990-799994 in --smoke)",
    )
    ap.add_argument(
        "--m3-synth-seeds",
        default=None,
        help="Override M3 synthetic seed range A-B (default: 61000-61099; 799990-799994 in --smoke)",
    )
    ap.add_argument(
        "--m3-real-seeds",
        default=None,
        help="Override M3 real-data seed range A-B (default: 770000-770199; 799990-799994 in --smoke)",
    )
    ap.add_argument(
        "--smoke",
        action="store_true",
        help="Smoke mode: seeds 799990-799994, at most 3 site-days, print counts and timings only",
    )
    ap.add_argument(
        "--allow-dirty",
        action="store_true",
        help="Allow uncommitted frozen/params files in synthetic runner (enabled automatically in --smoke)",
    )
    return ap.parse_args(argv)


def _resolve_seed_pair(override: str | None, default_pair: tuple[int, int], smoke: bool) -> tuple[int, int]:
    if override is not None:
        return parse_seeds(override)
    return SMOKE_SEEDS if smoke else default_pair


def _count_seeds(pair: tuple[int, int]) -> int:
    return pair[1] - pair[0] + 1


def _load_real_site_days(
    datasets: set[str],
    acn_data_dir: Path,
    pa_csv: Path,
    max_site_days: int | None,
) -> tuple[dict[str, list], dict[str, dict], dict[str, float]]:
    site_days_map: dict[str, list] = {}
    counts: dict[str, dict] = {}
    load_timings: dict[str, float] = {}

    if "acn" in datasets:
        t0 = time.perf_counter()
        sessions_by_site, _ = load_all_sites(sites=DEFAULT_SITES, data_dir=acn_data_dir)
        all_days = build_t2_site_days(sessions_by_site, min_participants=T2_MIN_PARTICIPANTS)
        kept = all_days[:max_site_days] if max_site_days is not None else all_days
        load_timings["acn_load_s"] = time.perf_counter() - t0
        site_days_map["acn"] = kept
        counts["acn"] = {"total_eligible_site_days": len(all_days), "used_site_days": len(kept)}

    if "pa" in datasets:
        t0 = time.perf_counter()
        sessions_by_site, _ = load_pa_sites(csv_path=pa_csv)
        all_days = build_t2_site_days(sessions_by_site, min_participants=T2_MIN_PARTICIPANTS)
        kept = all_days[:max_site_days] if max_site_days is not None else all_days
        load_timings["pa_load_s"] = time.perf_counter() - t0
        site_days_map["pa"] = kept
        counts["pa"] = {"total_eligible_site_days": len(all_days), "used_site_days": len(kept)}

    return site_days_map, counts, load_timings


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    datasets = [d.strip() for d in args.datasets.split(",") if d.strip()]
    bad_ds = [d for d in datasets if d not in ALL_DATASETS]
    if bad_ds:
        raise SystemExit(f"unknown datasets {bad_ds}; choose from {ALL_DATASETS}")
    ds_set = set(datasets)

    out_dir = args.out_dir
    if out_dir is None:
        out_dir = DEFAULT_OUT_DIR / "smoke" if args.smoke else DEFAULT_OUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    max_sd = args.max_site_days
    if args.smoke:
        max_sd = SMOKE_MAX_SITE_DAYS if max_sd is None else min(int(max_sd), SMOKE_MAX_SITE_DAYS)

    m6_synth_pair = _resolve_seed_pair(args.m6_synth_seeds, M6_SYNTH_SEEDS, args.smoke)
    m6_real_pair = _resolve_seed_pair(args.m6_real_seeds, M6_REAL_SEEDS, args.smoke)
    m3_synth_pair = _resolve_seed_pair(args.m3_synth_seeds, M3_SYNTH_SEEDS, args.smoke)
    m3_real_pair = _resolve_seed_pair(args.m3_real_seeds, M3_REAL_SEEDS, args.smoke)

    params = load_params(DEFAULT_PARAMS_PATH)
    beta_ab = (float(params.alpha), float(params.beta))
    allow_dirty = bool(args.allow_dirty or args.smoke)

    want_m6 = args.study in ("both", "m6")
    want_m3 = args.study in ("both", "m3")

    m6_cell_list = [c for _, c in m6_cells()]
    m3_cell_specs = m3_cells(beta_ab)
    m3_cell_list = [c for _, _, c in m3_cell_specs]
    m3_extra_cells = [c for c in m3_cell_list if c.redraw_prob != 0.0 or c.beta_q is not None]

    site_days_map, sd_counts, load_timings = _load_real_site_days(
        ds_set, args.acn_data_dir, args.pa_csv, max_sd
    )

    timings: dict[str, float] = dict(load_timings)
    row_counts: dict[str, dict] = {}
    analysis_out: dict = {
        "meta": {
            "label": "post hoc round 3 (explanatory)",
            "smoke": bool(args.smoke),
            "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "protocol_path": str(DEFAULT_ROUND3_PROTOCOL),
            "protocol_sha256": protocol_sha256(DEFAULT_ROUND3_PROTOCOL),
            "population_params_sha256": _file_sha(DEFAULT_PARAMS_PATH),
            "tuning_frozen_sha256": _file_sha(DEFAULT_FROZEN_PATH),
            "beta_q_params": {"alpha": beta_ab[0], "beta": beta_ab[1],
                              "mean": beta_ab[0] / (beta_ab[0] + beta_ab[1])},
            "datasets": datasets,
            "workers": int(args.workers),
            "n_boot": int(args.n_boot),
            "site_day_counts": sd_counts,
        },
        "m6": {},
        "m3": {},
    }

    # ------------------------------------------------------------------ M6: guard ablation
    if want_m6:
        if "synthetic" in ds_set:
            sub_dir = out_dir / "m6_synthetic"
            open_rng = (
                {("F0R", "frozen"): m6_synth_pair}
                if args.smoke or m6_synth_pair != M6_SYNTH_SEEDS
                else None
            )
            t0 = time.perf_counter()
            res = runner.run(
                "F0R",
                m6_synth_pair,
                sub_dir,
                mode="frozen",
                policies=list(M6_POLICIES),
                cell_ids=[c.cell_id for c in m6_cell_list],
                workers=args.workers,
                open_ranges=open_rng,
                allow_dirty=allow_dirty,
                argv=["scripts/posthoc_round3.py", "m6", "synthetic"],
            )
            timings["m6_synthetic_s"] = time.perf_counter() - t0
            row_counts["m6_synthetic"] = {
                "n_seeds": _count_seeds(m6_synth_pair),
                "n_cells": len(m6_cell_list),
                "rows_written": res["rows_written"],
                "rows_skipped": res["rows_skipped"],
                "total_rows": res["total_rows"],
            }
            rows = load_rows_file(sub_dir / runner.ROWS_NAME)
            t0 = time.perf_counter()
            analysis_out["m6"]["synthetic"] = analyse_m6_rows(
                rows, clustered=False, n_boot=args.n_boot, boot_seed=M6_BOOT_SEED
            )
            timings["m6_synthetic_analyse_s"] = time.perf_counter() - t0

        for ds in ("acn", "pa"):
            if ds not in ds_set:
                continue
            rows_path = out_dir / f"m6_{ds}_rows.jsonl"
            manifest_path = out_dir / f"m6_{ds}_manifest.json"
            seeds_list = list(range(m6_real_pair[0], m6_real_pair[1] + 1))
            t0 = time.perf_counter()
            man = run_t2(
                site_days_map[ds],
                seeds_list,
                rows_path,
                cells=m6_cell_list,
                policies=M6_POLICIES,
                variant="t2",
                workers=args.workers,
                manifest_path=manifest_path,
                protocol_path=DEFAULT_ROUND3_PROTOCOL,
            )
            timings[f"m6_{ds}_s"] = time.perf_counter() - t0
            row_counts[f"m6_{ds}"] = {
                "n_seeds": len(seeds_list),
                "n_cells": len(m6_cell_list),
                "n_site_days": len(site_days_map[ds]),
                "rows_written": man["rows_written"],
                "rows_skipped": man["rows_skipped"],
                "total_rows": man["total_rows"],
            }
            rows = load_rows_file(rows_path)
            t0 = time.perf_counter()
            analysis_out["m6"][ds] = analyse_m6_rows(
                rows, clustered=True, n_boot=args.n_boot, boot_seed=M6_BOOT_SEED
            )
            timings[f"m6_{ds}_analyse_s"] = time.perf_counter() - t0

    # ------------------------------------------------------------------ M3: failure persistence
    if want_m3:
        if "synthetic" in ds_set:
            sub_dir = out_dir / "m3_synthetic"
            open_rng = (
                {("F0R", "frozen"): m3_synth_pair}
                if args.smoke or m3_synth_pair != M3_SYNTH_SEEDS
                else None
            )
            t0 = time.perf_counter()
            res = runner.run(
                "F0R",
                m3_synth_pair,
                sub_dir,
                mode="frozen",
                policies=list(M3_POLICIES),
                cell_ids=[c.cell_id for c in m3_cell_list],
                extra_cells=m3_extra_cells,
                workers=args.workers,
                open_ranges=open_rng,
                allow_dirty=allow_dirty,
                argv=["scripts/posthoc_round3.py", "m3", "synthetic"],
            )
            timings["m3_synthetic_s"] = time.perf_counter() - t0
            row_counts["m3_synthetic"] = {
                "n_seeds": _count_seeds(m3_synth_pair),
                "n_cells": len(m3_cell_list),
                "rows_written": res["rows_written"],
                "rows_skipped": res["rows_skipped"],
                "total_rows": res["total_rows"],
            }
            rows = load_rows_file(sub_dir / runner.ROWS_NAME)
            t0 = time.perf_counter()
            analysis_out["m3"]["synthetic"] = analyse_m3_rows(
                rows, clustered=False, n_boot=args.n_boot, boot_seed=M3_BOOT_SEED
            )
            timings["m3_synthetic_analyse_s"] = time.perf_counter() - t0

        for ds in ("acn", "pa"):
            if ds not in ds_set:
                continue
            rows_path = out_dir / f"m3_{ds}_rows.jsonl"
            manifest_path = out_dir / f"m3_{ds}_manifest.json"
            seeds_list = list(range(m3_real_pair[0], m3_real_pair[1] + 1))
            t0 = time.perf_counter()
            man = run_t2(
                site_days_map[ds],
                seeds_list,
                rows_path,
                cells=m3_cell_list,
                policies=M3_POLICIES,
                variant="t2",
                workers=args.workers,
                manifest_path=manifest_path,
                protocol_path=DEFAULT_ROUND3_PROTOCOL,
            )
            timings[f"m3_{ds}_s"] = time.perf_counter() - t0
            row_counts[f"m3_{ds}"] = {
                "n_seeds": len(seeds_list),
                "n_cells": len(m3_cell_list),
                "n_site_days": len(site_days_map[ds]),
                "rows_written": man["rows_written"],
                "rows_skipped": man["rows_skipped"],
                "total_rows": man["total_rows"],
            }
            rows = load_rows_file(rows_path)
            t0 = time.perf_counter()
            analysis_out["m3"][ds] = analyse_m3_rows(
                rows, clustered=True, n_boot=args.n_boot, boot_seed=M3_BOOT_SEED
            )
            timings[f"m3_{ds}_analyse_s"] = time.perf_counter() - t0

    # Projected full-run time (linear scaling in seed count for simulation + constant load/analyse)
    projected_components: dict[str, float] = {}
    full_seed_targets = {
        "m6_synthetic": _count_seeds(M6_SYNTH_SEEDS),
        "m6_acn": _count_seeds(M6_REAL_SEEDS),
        "m6_pa": _count_seeds(M6_REAL_SEEDS),
        "m3_synthetic": _count_seeds(M3_SYNTH_SEEDS),
        "m3_acn": _count_seeds(M3_REAL_SEEDS),
        "m3_pa": _count_seeds(M3_REAL_SEEDS),
    }
    proj_total = sum(load_timings.values())
    for key, rc in row_counts.items():
        sim_s = timings.get(f"{key}_s", 0.0)
        an_s = timings.get(f"{key}_analyse_s", 0.0)
        n_ran = max(1, int(rc["n_seeds"]))
        n_full = full_seed_targets[key]
        proj_sim = sim_s * (n_full / n_ran)
        projected_components[f"{key}_sim_s"] = round(proj_sim, 2)
        proj_total += proj_sim + an_s

    _write_json_atomic(out_dir / "analysis.json", analysis_out)

    summary = {
        "smoke": bool(args.smoke),
        "study": args.study,
        "datasets": datasets,
        "workers": int(args.workers),
        "out_dir": str(out_dir),
        "site_day_counts": sd_counts,
        "row_counts": row_counts,
        "timings_s": {k: round(v, 3) for k, v in timings.items()},
        "total_wall_s": round(sum(timings.values()), 3),
        "projected_full_run_s": {
            "at_workers": int(args.workers),
            "components": projected_components,
            "total_s": round(proj_total, 2),
            "total_min": round(proj_total / 60.0, 2),
        },
    }
    _write_json_atomic(out_dir / "summary.json", summary)

    # Always print counts and timings only in --smoke mode (and concisely otherwise).
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
