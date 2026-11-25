# Evidence ledger, Track E PGAI4E note

Each claim in `docs/DEV_REPORT_E.md`, the file that supports it, and the command that regenerates it. Every value is development. Keys refer to `results/paper_numbers.json` → `numbers`.

## Regeneration chain

| Step | Command | Output |
|---|---|---|
| Population fit | `uv run python -m papere.fit` | results/population_params.json |
| Tuning | `uv run python run_study.py --family F0R --mode tune --seeds 60000-60049 --out results/tuning --workers 4` | results/tuning/rows.jsonl (git-ignored); `uv run python scripts/aggregate_tuning.py` → results/tuning/aggregates.csv |
| Freeze | `uv run python run_study.py --family F0R --freeze --out results/tuning` | results/TUNING_FROZEN.json |
| K-copy | `uv run python run_study.py --family KCOPY --seeds 61500-61599 --out results/kcopy_dev --workers 4` | results/kcopy_dev/rows.jsonl.gz |
| F0-R | `uv run python run_study.py --family F0R --seeds 61000-61099 --out results/f0r_dev --workers 4` | results/f0r_dev/rows.jsonl.gz |
| Scaling | `uv run python run_study.py --family SCALE --seeds 63000-63019 --out results/scale_dev --workers 4` | results/scale_dev/rows.jsonl.gz |
| Data file | `gunzip -k results/*/rows.jsonl.gz` then `uv run python -m papere.analysis --all --frozen results/TUNING_FROZEN.json` | results/paper_numbers.json |
| G2 gate | `uv run python -m papere.analysis --g2 results/f0r_dev --frozen results/TUNING_FROZEN.json` (pilot seeds 61000–61019 only) | results/g2_numbers.json |
| Tables | `uv run python scripts/make_dev_tables.py` | docs/DEV_TABLES.md |
| Negative controls | `uv run python scripts/negative_controls.py --workers 4`; `--nc3-extended --workers 4` | results/negative_controls/*.json, docs/NC_REPORT.md |
| G1 | `PAPERE_G1_FULL=1 uv run pytest -q tests/test_flow.py tests/test_enumerator.py`; `uv run python scripts/g1_propositions.py` | logs/g1_flow_full.txt, results/g1_propositions.{json,md} |

## Claims

| # | Claim (DEV_REPORT_E section) | Value | Source |
|---|---|---|---|
| C1 | E1 detected above the threshold at M = 3, ρ = 1.15 (3.1) | +1.05 [+0.59, +1.53] | `e1/primary/M3_rho1.15/contrast` |
| C2 | E1 not detected at M = 3, ρ = 0.95 (3.1) | +0.31 [−0.25, +0.85] | `e1/primary/M3_rho0.95/contrast` |
| C3 | M = 0 E1 is a comparator artefact; gaps at δ_A ≥ 1 are 0 (1, item 5) | +0.11, +0.04; gaps 0 | `e1/primary/M0_rho*/contrast`, `.../gap_dA{1,2,4}`, `.../gap_dA0`; `best_oblivious` field |
| C4 | Per-delay gaps at M = 3, incl. δ_A = 1 (3.1) | table in 3.1 | `e1/primary/M3_rho*/gap_dA{0,1,2,4}` |
| C5 | Oracle contrasts (3.1) | table in 3.1 | `e1/primary/M*_rho*/oracle_contrast` |
| C6 | e1 recovers 0.69 of the oracle's E1 contrast at M = 3, ρ = 1.15 (2) | 0.69 [0.49, 0.87] | `e1/primary/M3_rho1.15/oracle_share` |
| C7 | Floor-allowed and minimum-E1 sensitivities reverse or remove E1 (3.2) | table in 3.2 | `e1/sensitivity_floor/*/contrast`, `e1/sensitivity_min_e1/*/contrast` (comparator in `best_oblivious`) |
| C8 | Mean R_avoid at M = 3, ρ = 1.15, δ_A = 2 by policy (3.1) | 2.42, 4.12, 1.78, 5.97, 6.48 | `cell/F0R_M3_dA2_db0_rho1.15_r0.3/<policy>/R_avoid_kwh_per100` |
| C9 | G2 on the pilot: E1, ratio 0.95, headline fired, tie at 0.5 (4) | see G2_REPORT | results/g2_numbers.json; docs/G2_REPORT.md |
| C10 | G2 quantities at full size: gains and ratio 0.83 (4) | 0.83 [0.70, 0.95] | `g2_full/e1_stat`, `g2_full/gain/{candidate,pop_mpc,persistence}`, `g2_full/ratio/{pop_mpc,persistence}`, `g2_full/flag/*` |
| C11 | E2 not supported; reading A values; reading B degenerate (5) | table in 5 | `e2/M*_rho*/{dA2,dA4,contrast}/reading{A,B}/*`, `e2/*/contrast/supported`; ledger formula src/papere/ledger.py (R_uncorr_lo) |
| C12 | Floor event shortfall 50; net recovery gain range (6) | 50.0; −4.24 to +2.02 | `secondary/floor/*/event_shortfall`, `.../net_recovery_gain` |
| C13 | Return-probability sweep (6) | table in 6 | `secondary/r_sweep/r{0,0.3,1}/{gap,oracle_gap}` |
| C14 | Lag-split cell gap (6) | −0.42 [−0.62, −0.25] | `secondary/lag_split/gap` |
| C15 | Violations, hedge waste, misses, peak, CPU at the G2 cell (6) | table in 6 | `cell/F0R_M3_dA2_db0_rho0.95_r0.3/<policy>/<metric>` |
| C16 | Scaling CPU and sign at N = 300 (6) | 12–25 ms; 4.80 vs 5.93 | `scale/SCALE_*/<policy>/cpu_ms_mean`, `.../R_avoid_kwh_per100` |
| C17 | E3: 312/312 simultaneous; 11 pointwise misses vs 15.6; all Prop 3 points below prediction (8) | see 8 | `e3/summary/*`, `e3/gap_e1/*`, `e3/R_pop/*`, `e3/gap_oracle/*` |
| C18 | Negative-control verdicts (7) | table in 7 | docs/NC_REPORT.md; results/negative_controls/nc_results.json, nc3_extended.json |
| C19 | G1 passed (2) | 2,723/2,723; 277,712 instances | docs/G1_REPORT.md; results/g1_propositions.json; logs/g1_flow_full.txt |
| C20 | Tuning selections and margin m = 0 almost everywhere (6) | per family per cell | results/TUNING_FROZEN.json; results/tuning/aggregates.csv |
| C21 | Seed-hygiene disclosures (1, item 8) | — | docs/SEED_LEDGER.md (Disclosure) |
| C22 | Defects caught by review (1, item 12) | — | git log of this branch (commit messages naming each review fix); docs/OPEN_QUESTIONS.md rows 7, 11, 31, 36, 47–49; the RNG and missing-seed fixes are documented in the commits "Step 1: review and owner-QA fixes" and "Analysis: review fixes" |
| C23 | Tuned sym_margin = CE-LLF: m = 0 in every frozen entry (1, item 3) | 286 entries | results/TUNING_FROZEN.json; `cell/F0R_M3_dA2_db0_rho0.95_r0.3/{sym_margin,ce_llf}/*` |
| C24 | Comparators per δ_A (3.1, 3.2) | names | `e1/primary/*/contrast` and `e1/sensitivity_min_e1/*/contrast` field `best_oblivious`; `e1/sensitivity_min_e1/*/gap_dA{0,1,2,4}` |
| C25 | Reading B gain 0 everywhere; R_uncorr_lo 0 at the G2 cell (5) | 0 [0, 0] | `e2/M3_rho*/{dA2,dA4,contrast}/readingB/gain_uncorr`; `cell/F0R_M3_dA2_db0_rho0.95_r0.3/<policy>/R_uncorr_lo_kwh_per100` |
| C26 | History and stress sweeps against Proposition 3 shares (6.1) | table in 6.1 | `cell/F0R_M{1,3,5}_dA2_db0_rho0.95_r0.3/<policy>/R_avoid_kwh_per100`, `cell/F0R_M3_dA2_db0_rho0.7_r0.3/<policy>/R_avoid_kwh_per100`; Proposition 3 values: results/g1_propositions.json |
| C27 | RWDF-E literal minus RWDF-E (6.3) | 1.25 [−0.58, +3.14] at r = 0 | `secondary/rwdf/*/literal_minus_rwdf_e` |
| C28 | E3 direction counts (8) | 107/8/29; 18 of 24 | `e3/R_pop/*` and `e3/gap_e1/*` fields value and predicted |
| C29 | Negative R_avoid (1, item 10) | about −2.5 | `cell/F0R_M3_dA0_db0_rho1.15_r0.3/sym_margin/R_avoid_kwh_per100` |

| C30 | Three-layer factorial: planning, hedging, targeting, oracle targeting, total, for R_avoid and deadline misses (descriptive, post hoc, added after DEV_REPORT_E; factorial pre-declared as secondary in FORMULATION_E_v2 8.2) | 16 cells | `layers/M*_rho*/dA*/{planning,hedging,targeting,oracle_targeting,total}`, `layers/M*_rho*/dA*/deadline_misses/*` |
| C31 | M-sweep recovery share of the oracle gap (δ_A = 2, ρ = 0.95) | 0.13 [−0.17, 0.36], 0.39 [0.12, 0.60], 0.40 [0.04, 0.65] | `layers/msweep/M{1,3,5}/{numerator,denominator,share}` |
| C32 | E3 conditioned on realized stuck draws (diagnostic, added after DEV_REPORT_E) | 312/312 simultaneous, 307/312 pointwise | results/e3_conditioned.json; `uv run python scripts/e3_conditioned.py` |

Provenance: the data file was regenerated from clean commit `8f1c7e7` (`meta.git.dirty` false; sha256 `a8fade973b4bb0e2…`), and every key cited above is checked to exist by `uv run python scripts/check_ledger.py` (39 cited keys, all present). `results/paper_numbers.json` → `meta` also records the git commit, the bootstrap settings and the sha256 of every input rows file. Inputs: tuning, frozen and population files are committed; development rows are committed gzipped.
