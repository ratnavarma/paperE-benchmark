# Analysis spec: endpoints E1–E3, gate G2 and the data file

Written October 20, 2026 by the implementation lead from PLAN_PGAI4E_E Sections 6 and 8. Every number is development. Unit: the seed. Pairs: policies within seed and cell. Intervals: paired bootstrap over seeds, 10,000 resamples, 95% percentile, fixed bootstrap seed. Energy in kWh per 100 participants per event (`*_kwh_per100` keys). New readings are logged in OPEN_QUESTIONS.

## 1. Policy sets

- Oblivious set O: ce_llf, ce_edf, pes_llf, sym_margin, persistence, uncorr_pes, probe_first, mpc_ce, mpc_pes, pop_mpc. The floor is reported beside them, never inside O for the primary E1 (its recovery is bought with event shortfall, a different realized instance); a sensitivity E1 includes it.
- Candidate: guarded_mpc_e1. Reference: oracle_mpc. Per-participant rows: user_flag, rwdf_e, rwdf_e_literal, llf_post. Bound: the clairvoyant row.

## 2. E1, the obliviousness gap

For each cell, the best oblivious policy is fixed in advance on the tuning seeds: the member of O with the lowest frozen tuning objective (mean R_avoid on seeds 60000–60049) in `results/TUNING_FROZEN.json`. The untuned points ce_llf, ce_edf and pes_llf lie inside sym_margin's grid, so sym_margin's tuned value bounds them on the tuning seeds. Selecting on the development seeds would bias E1 upward, because the minimum taken at δ_A ∈ {0, 1} shrinks the subtracted low-delay gap. A sensitivity E1 uses, per (M, ρ), the single member of O that minimizes E1 itself on the development seeds, a conservative lower reading. Per seed s and cell:

- `gap(s, δ) = R_avoid(best O) − R_avoid(e1)`;
- `E1(s) = mean_{δ ∈ {2, 4}} gap(s, δ) − mean_{δ ∈ {0, 1}} gap(s, δ)`, by M ∈ {0, 3} and ρ ∈ {0.95, 1.15}.

Report the mean and the bootstrap interval of E1, and of each `gap(·, δ)`. Share of the oracle gap: the same contrast with oracle_mpc in place of e1, and the ratio of the two means (with a bootstrap interval of the ratio). Reading against the practical threshold of 0.5 kWh per 100 (PLAN 6): interval wholly above 0.5, "detected above the practical threshold"; interval excluding 0 and wholly below 0.5, "detected, below the practical threshold"; interval excluding 0 but containing 0.5, "detected, size uncertain against the threshold"; interval including 0, "not detected at this size".

## 3. E2, the correctability split

For every policy and cell: means and intervals of R_uncorr_hi, R_uncorr_lo, R_corr_hi, R_corr_lo. For the candidate against the best O: the paired gain in R_uncorr and in R_corr under both readings. The prediction (the gain sits in R_uncorr) counts as supported only if it holds under both readings.

## 4. E3, theory tracking on the K-copy family

Per K-copy cell (q, c, M, cap mode), per seed, in units on the instance:

- `gap_oracle(s) = R(pop_mpc) − R(oracle_mpc)` against gap(c) (MECHANISM 3.6), at every c;
- `gap_e1(s) = R(pop_mpc) − R(e1)` against the Proposition 3 value `K q/2 − E[R_e1]` (pooled: exact binomial sum; per-copy: `K (q/2) f`), at c = K;
- also `R(pop_mpc)` against `q (K − c/2)`.

Primary pass rule: every predicted value lies inside its simultaneous 95% Monte Carlo interval (Bonferroni over all E3 points), so that "every point within its interval" is a 95% statement about the whole family. Also reported: the pointwise 95% count, the number expected outside by chance, a binomial test of that count, and every point outside its pointwise interval.

## 4b. Completeness

The analysis refuses to compute any endpoint if a required policy, seed or cell is missing, if a row lacks `mode` or `study_family`, if a seed lies outside the range of its run (pilot 61000–61019, F0-R 61000–61099, K-copy 61500–61599, scaling 63000–63019), or if a privileged row appears in a non-reference set. With `--strict`, nothing is written on any warning.

## 5. Secondary

Floor: net recovery gain (best O R_avoid minus floor R_avoid) beside the event shortfall, never summed. Return-probability sweep r ∈ {0, 0.3, 1}. Violations (count, kW·slot, longest run), hedge waste, peak, deadline misses, CPU ms per decision, per policy and cell. Lag-split cell. RWDF-E literal beside RWDF-E.

## 6. Gate G2 (pilot, seeds 61000–61019, cell δ_A = 2, ρ = 0.95, M = 3)

- E1 at that cell as in Section 2, with its δ ∈ {0, 1} comparison cells at M = 3, ρ = 0.95; the pilot therefore runs all 22 cells on its 20 seeds. There is no fallback to the raw gap. If the interval sits wholly below 0.5 kWh per 100, the note becomes the in-progress format, "simple rules suffice in this regime".
- Gain of a policy P: `R_avoid(sym_margin) − R_avoid(P)` at the G2 cell, sym_margin being the tuned symmetric margin. If pop_mpc's or persistence's mean gain reaches 80% of the candidate's mean gain, that is the headline. Report both ratios with intervals.

## 7. The data file

`uv run python -m papere.analysis --all` reads the saved rows and writes `results/paper_numbers.json`: every number the note uses, each with its source file, row filter, statistic and interval. DEV_REPORT_E tables are generated from that file only.
