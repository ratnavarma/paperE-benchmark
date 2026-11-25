# Seed ledger, Track E

| Range | Use | Status |
|---|---|---|
| 60000–60049 | Tuning (margin grid, MPC window, e1 population prior) | open, development |
| 61000–61099 | F0-R development runs | open, development |
| 61500–61599 | K-copy validation family | open, development |
| 62000–62099 | Kept for a possible F1 on ACN-Data | unused |
| 63000–63019 | Scaling at N = 300, compute only | open, development |
| 64000–64249 | NC3′ extended negative control only (homogeneous q, memoryless availability; the 16 NC3′ cells) | open, development; added by the owner side on 2026-10-20 before any run |
| 500000–500999 | Reserved confirmation | CLOSED until the author types "run" |

Earlier Track E seeds 0–79 and every other paper's ranges (100000–100999, 200000–200999, 300000–300999) are never used here.

## Disclosure, October 20, 2026 (build phase)

During steps 1–4 the unit tests generated instances and ran policies on development seeds, not only on tuning seeds:

- 61000–61099 (F0-R development): generator, wrapper, simulator, ledger and rule tests, mostly mechanical; some rule and MPC tests ran policies and checked validity or rough performance.
- 61500–61599 (K-copy validation): structure checks, an oracle-calibration check, and an MPC Monte Carlo check that population, e1 and oracle MPC residuals match Propositions 1 and 3 within 4 standard errors. That check passed. It is an early look at the E3 seeds and is reported as such in DEV_REPORT_E.
- 63000 (scaling): one generator shape check.
- Generator-only statistical tests (class independence, base-load spread and autocorrelation) drew seeds from `range(2000)` and `range(300)`, which include the earlier Track E seeds 0–79. These tests generated instances only; no policy was run on them. They are being moved to the tuning seeds with salted streams, and a runtime guard in `tests/conftest.py` now refuses any seed outside 60000–60049 during tests.

The MPC builder's own probes also ran on 61000–61099 and 61500–61599, and one guard-design pilot used 60050–60059, a range outside every listed use; that pilot informed the choice of guard form. No tuned configuration was chosen on any of these seeds; the guard design evidence otherwise used tuning seeds. From this date every test uses seeds 60000–60049 only, and the development ranges are touched only by `run_study.py`.

## Note, October 20, 2026 (after DEV_REPORT_E)

The diagnostic `scripts/e3_conditioned.py` regenerates the K-copy instances on 61500–61599 (instance generation only, no policy is run) to read each seed's realized stuck pattern and prior history, and compares them with the saved rows of the E3 run. It is labelled "diagnostic, conditioned on realized stuck draws, added after DEV_REPORT_E".

## Note, October 20, 2026 (post hoc runs added after the G3 review)

Three runs on new cells over the existing development range 61000–61099 (F0-R, N = 30). No new seed range is opened, the confirmation range 500000–500999 stays closed and untouched, and no existing results file changes. Label: "development, post hoc, added after the G3 review". Rows are in `results/f0r_extra/` (8,800 rows, frozen configurations from `results/TUNING_FROZEN.json`); numbers are in `results/posthoc_g3_runs.json`.

| Run | Cells (all M = 3, r = 0.3, δ_b = 0) | Policies |
|---|---|---|
| sLLF anchor | δ_A in {0, 1, 2, 4}, ρ in {0.95, 1.15} | sllf, ce_llf, mpc_ce, pop_mpc, guarded_mpc_e1, oracle_mpc |
| Heterogeneity sweep | δ_A = 2, ρ in {0.95, 1.15}, class splits (0.15, 0.88) and (0.5, 0.27) (the baseline (1/3, 0.40) is the sLLF run's δ_A = 2 cells) | ce_llf, mpc_ce, pop_mpc, guarded_mpc_e1, oracle_mpc |
| Flagged-only floor | δ_A in {2, 4}, ρ in {0.95, 1.15} | floor, floor_flagged, the frozen best oblivious policy (pop_mpc) |

The sLLF NC1-exact check and the unit tests use tuning seeds 60000–60049 only (`results/posthoc_sllf_nc1_exact.json`). The heterogeneity analysis regenerates the instances on 61000–61099 to read each split's realized mean stuck probability (instance generation only, no policy is run).

## Note, October 20, 2026 (post hoc runs, second addition after the G3 review)

Two more analyses on the existing development range 61000–61099 (F0-R, N = 30). No new seed range is opened, the confirmation range 500000–500999 stays closed and untouched, and no existing row changes. Label: "development, post hoc, added after the G3 review".

- `llf_pop` (LLF-POST with the population belief, frozen `llf_post` configuration per cell) and its paired comparator `llf_post` were run on the eight sLLF cells (M = 3, δ_A in {0, 1, 2, 4}, ρ in {0.95, 1.15}, r = 0.3, δ_b = 0) by `scripts/run_posthoc_g3.py`. 1,600 rows were appended to `results/f0r_extra/` (10,400 rows now; the first 8,800 are byte-identical to before). The `llf_post` rows equal the ones in `results/f0r_dev/` on every shared key. The unit test that `llf_pop` equals `llf_post` at M = 0 uses tuning seeds 60000–60048 only.
- `scripts/posthoc_g3_runs.py` adds 60 numbers to `results/posthoc_g3_runs.json` (234 now): the paired 2 × 3 factorial (`posthoc_runs/factorial/`, 56 keys) and the flagged floor against the candidate (`posthoc_runs/floor_flagged/.../candidate_minus_floor_flagged`, 4 keys). Same rows, bootstrap settings and clean-commit rule as before.

## Confirmation, October 20, 2026

Reserved seeds 500000–500199 were opened once, after the author typed "run", under the frozen protocol docs/PROTOCOL_CONFIRMATION_E.md and manifest docs/MANIFEST_CONFIRMATION.json (commit 242c96e). 12,800 rows in results/f0r_confirm. The approval file was moved to results/f0r_confirm/CONFIRMATION_APPROVED.used after the run, so the range is closed again. Seeds 500200–500999 have never been opened.

## Note, November 2, 2026 (greedy expected-value ranker, post hoc, at the referee's request)

The ranker families greedy_ev, greedy_ev_pop and greedy_ev_ce (docs/RANKER_POSTHOC.md) were tuned on 60000–60049, all 22 F0-R cells, giving 29,700 rows in `results/tuning_posthoc_ranker/`. The selection is frozen in `results/TUNING_FROZEN_posthoc_ranker.json`; `results/TUNING_FROZEN.json` is unchanged. The ranker was then run on the existing development range 61000–61099, on the eight Table 1 cells (M = 3, δ_A in {0, 1, 2, 4}, ρ in {0.95, 1.15}, r = 0.3, δ_b = 0). ce_llf, pop_mpc and guarded_mpc_e1 were rerun there as a reproduction check, giving 5,600 rows in `results/f0r_posthoc_ranker/`. No new seed range is opened, and the confirmation range 500000–500999 stays closed and untouched. The new frozen file was not committed before the run, so that invocation used `allow_dirty`, which its manifest records. Label: "descriptive, post hoc, added 2026-11-02 at the referee's request". Numbers are in `results/posthoc_ranker.json`. The unit tests use tuning seeds 60000–60049 only.

## Note, November 18, 2026 (Applied Energy revision, author decisions D1 to D3)

- D3, policy run: `scripts/diag_cellf_delay.py` ran ce_llf and mpc_ce with their frozen configurations on tuning seeds 60000–60049 at M = 3, δ_A in {1, 4}, ρ in {0.95, 1.15}, r = 0.3, δ_b = 0. No rows file is written; 60 numbers go to `results/diag_cellf_delay.json`. Label: "tuning seeds, post hoc diagnostic, not a test".
- D1 and D2, no policy run: `scripts/posthoc_fla_2026_11.py` reads existing rows only (`results/f0r_confirm`, `f0r_dev`, `f0r_extra`, `f0r_posthoc_ranker`, `scale_dev`) and writes `results/posthoc_fla.json`. The confirmation rows were read, not rerun; the per-cell means are the ones the frozen protocol (section 3) promised. Seeds 500200–500999 have never been opened.
- Wording note (no change to history): the November 2 note above says "at the referee's request". That review was a pre-submission review of a manuscript not yet submitted to any journal; the manuscript now says "pre-submission review".
