# Confirmation protocol, Track E PGAI4E note (FROZEN October 20, 2026; not yet run)

Status: frozen October 20, 2026 after Varma's chat approval ("Yes: freeze the confirmation protocol and run 500000-500199 once. I'll type run when you show me the frozen manifest."). Nothing here has run. Seeds 500000–500999 stay closed. The runner refuses them unless `CONFIRMATION_APPROVED` at the repo root holds exactly the line `run`, and only Varma types that.

## 1. Seeds and scope

- Reserved seeds 500000–500199 (200 seeds), opened once. No resumption with new seeds, no early stopping, no extension.
- Cells: M = 3, δ_A ∈ {0, 1, 2, 4}, ρ ∈ {0.95, 1.15}, r = 0.3, δ_b = 0. That is 8 cells.
- Policies, with frozen configurations from `results/TUNING_FROZEN.json` (sha256 d4b4d4ee…aa10): ce_llf, sym_margin, mpc_ce, pop_mpc, llf_post, guarded_mpc_e1, oracle_mpc, plus the bound row. Population parameters come from `results/population_params.json` (sha256 0cbd0604…da71).
- Code: the commit recorded in the manifest at freeze. The runner checks every hash and refuses to start on a mismatch.

## 2. Declared tests (family C, five tests)

All are paired over seeds. Intervals are paired bootstrap percentile intervals at level 1 − 0.05/5 = 99% (Bonferroni over the family), with 10,000 resamples and seed 20261020. A test is supported when its 99% interval lies wholly on the predicted side of its threshold. Otherwise it is reported as "not supported at this size", never as evidence of no effect.

| Test | Statistic | Prediction from development | Supported if |
|---|---|---|---|
| C1 | E1 at M = 3, ρ = 1.15: mean gap (best oblivious − candidate) over δ ∈ {2, 4} minus over δ ∈ {0, 1}; best oblivious fixed as in development (sym_margin at δ = 0, which is identical to CE-LLF with zero margin; pop_mpc at δ ≥ 1) | +1.05 kWh per 100 | interval > 0 |
| C2 | E1 at M = 3, ρ = 0.95, same definition | +0.31, not detected | interval > 0 (expected to fail; reported either way) |
| C3 | Gate ratio at M = 3, δ = 2, ρ = 0.95: (R_avoid(ce_llf) − R_avoid(pop_mpc)) / (R_avoid(ce_llf) − R_avoid(guarded_mpc_e1)), ratio of means | 0.83 | interval > 0.5 |
| C4 | Belief-by-rule interaction at δ = 2, ρ = 0.95: (ce_llf − mpc_ce) − (llf_post − guarded_mpc_e1) on R_avoid | −4.85 | interval < 0 |
| C5 | Fall of the reliability-blind share under the tight limit: share(δ = 1) − share(δ = 4) at ρ = 1.15, share = (ce_llf − pop_mpc)/(ce_llf − guarded_mpc_e1), ratio of means, jointly resampled | +0.53 | interval > 0 |

C4 and C5 were found post hoc on development seeds. Confirming them here is the point of including them, and the paper will say so.

## 3. What is reported

Every test is reported with its 99% interval and verdict. The paper also gives the per-cell R_avoid means, the violations and the deadline misses for the five policies, each labelled "confirmation". No other test is labelled confirmatory.

## 4. Freeze checklist (before Varma types "run")

1. Write `scripts/confirm_analysis.py`, which computes exactly Section 2 from the confirmation rows and nothing else. Test it on development rows; it must reproduce the development values given in Section 2.
2. Write `docs/MANIFEST_CONFIRMATION.json` with the sha256 of this protocol, the analysis script, TUNING_FROZEN.json, population_params.json, every file under src/papere, the runner and uv.lock, plus the git commit. Commit it.
3. Run the runner's dry run against the reserved range. It must refuse without the approval file and accept the plan with it.
4. Varma types `run`. The approval file is written. The run starts once.
5. Run the frozen analysis unchanged. Save rows, analysis output, environment and wall time. Push.

## 5. Exact commands (frozen)

Run, once, after `CONFIRMATION_APPROVED` holds Varma's typed `run`:

    uv run python run_study.py --family F0R --mode frozen --seeds 500000-500199 \
      --out results/f0r_confirm --workers 8 \
      --policies ce_llf,sym_margin,mpc_ce,pop_mpc,llf_post,guarded_mpc_e1,oracle_mpc \
      --cells F0R_M3_dA0_db0_rho0.95_r0.3,F0R_M3_dA1_db0_rho0.95_r0.3,F0R_M3_dA2_db0_rho0.95_r0.3,F0R_M3_dA4_db0_rho0.95_r0.3,F0R_M3_dA0_db0_rho1.15_r0.3,F0R_M3_dA1_db0_rho1.15_r0.3,F0R_M3_dA2_db0_rho1.15_r0.3,F0R_M3_dA4_db0_rho1.15_r0.3

Analyze, unchanged:

    uv run python scripts/confirm_analysis.py --rows results/f0r_confirm/rows.jsonl \
      --seeds 500000-500199 --out results/confirm_numbers.json

Pre-freeze check: on development rows 61000–61099 the analysis reproduces C1 1.054, C2 0.308, C3 0.825, C4 −4.850 and C5 0.526 (results/confirm_check_dev.json).
