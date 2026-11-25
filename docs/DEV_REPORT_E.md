# Development report, Track E PGAI4E note

Date: October 20, 2026. Written by the implementation lead; revised the same day after the read-only review in the private review record (every required fix applied; Section 11 lists them). **Every number in this report is development**: tuning seeds 60000–60049, F0-R development seeds 61000–61099, K-copy validation seeds 61500–61599, scaling seeds 63000–63019 and the NC3′ extension 64000–64249. No confirmatory seed was run; 500000–500999 stays closed. Units: kWh per 100 participants per event unless stated. Intervals: paired bootstrap over seeds, 10,000 resamples, 95% percentile; E3 uses Student-t Monte Carlo intervals. Numbers come from `results/paper_numbers.json` (regenerated from a clean commit by `uv run python -m papere.analysis --all --frozen results/TUNING_FROZEN.json`); full tables are in `docs/DEV_TABLES.md`; claims and sources are in `docs/EVIDENCE_LEDGER.md`. AI-assisted work; the review is by a separate read-only model, not an independent human.

## 1. What failed

1. **E1, the obliviousness gap, is detected above the practical threshold in only one of four strata, and both conservative readings remove it.** Primary E1 is +1.05 [+0.59, +1.53] at M = 3, ρ = 1.15 and +0.31 [−0.25, +0.85] at M = 3, ρ = 0.95 ("not detected at this size"). The two M = 0 strata read "detected, below the practical threshold", but that is an artefact (item 6). With the floor allowed as the comparator, or with the single oblivious policy that minimizes E1 on these seeds, E1 is reversed or not detected in every stratum (Section 3.2).
2. **The pre-declared G2 headline fired.** A population-rate stochastic MPC reaches 0.95 of the candidate's gain over the tuned symmetric margin in the pilot (20 seeds) and 0.83 [0.70, 0.95] at full size (100 seeds). At the G2 cell most of the gain over the margin baseline comes from planning with a population-rate stochastic model of unconfirmed delivery, not from per-participant history (Section 4).
3. **The tuned "symmetric margin" baseline is CE-LLF.** Tuning chose margin m = 0 in every one of the 286 frozen entries, and at the G2 cell the tuned sym_margin rows are identical to CE-LLF's. Every "gain over the margin baseline" in this report, including the G2 ratio, is a gain over certainty-equivalent LLF.
4. **E2, the correctability split, is formally not supported.** The pre-declared rule requires the prediction (the candidate's gain sits in R_uncorr) to hold under both readings. Under reading A it holds at M = 3, ρ = 0.95 (δ_A = 4 and the delay contrast) and fails at M = 3, ρ = 1.15. Reading B cannot detect anything: the candidate's reading-B gain in R_uncorr is 0 [0, 0] in every cell and contrast, and R_uncorr_lo is 0 for every policy at the G2 cell. Section 5.
5. **The E1 contrast understates the per-participant gain by design.** E1 subtracts the gap at δ_A ∈ {0, 1}, on the premise from instance I1 that δ_A = 1 carries no gap. In F0-R it does: the candidate beats the best oblivious policy at δ_A = 1 by +0.72 [+0.28, +1.16] (ρ = 0.95) and +1.18 [+0.72, +1.64] (ρ = 1.15). Per-delay gaps are reported beside E1 (Section 3.1).
6. **The small "detected" E1 at M = 0 is a comparator artefact.** At M = 0 the candidate and the population-rate MPC are identical by construction (NC4), so every gap at δ_A ≥ 1 is exactly 0. The contrast equals minus half the δ_A = 0 gap, where the comparator fixed on tuning seeds is MPC-CE (ρ = 0.95) or sym_margin (ρ = 1.15), each slightly ahead of the candidate. It is not evidence of a per-participant effect.
7. **In the M sweep, e1 recovers well under Proposition 3's share of the oracle's gap** (Section 6.1): about 0.13, 0.39 and 0.40 at M = 1, 3 and 5, against 0.40, 0.78 and 0.92 (per copy) or 0.25, 0.64 and 0.86 (pooled, large K) on the K-copy instance at q = 0.40. F0-R is not the K-copy instance, so this is not a test of Proposition 3, but the recovery curve that claim 2 describes does not appear at this size.
8. **Negative controls NC1, NC1_sp and NC3′ fail their pre-declared rules, and the F0-R runs went ahead anyway** under owner-side rulings (PLAN 6 says the controls "must pass before the F0-R runs"). NC1 failed because the plan left base-load noise in; NC1-exact passes for the planning policies. NC3′ fails on interval width at 50 and at 250 seeds; at 250 seeds 15 of 16 cells pass, one is "no difference detected at this size", and one cell inside the band shows a small detected difference against e1. Section 7.
9. **E3's literal pre-declared rule fails; the approved simultaneous rule passes.** PLAN 6 says "every point within its 95% interval": 11 of 312 points miss pointwise. The owner approved simultaneous intervals instead (OPEN_QUESTIONS), under which all 312 pass. Section 8.
10. **The candidate violates the limit slightly more than the margin baseline.** At the G2 cell 1.97 kW·slot against 1.58 for sym_margin (Section 6.3). R_avoid can be negative for every policy (down to about −2.5 at δ_A = 0) because policies are capped by the base-load forecast while the bound uses realized headroom (OPEN_QUESTIONS row 31).
11. **Build-phase seed hygiene** (`docs/SEED_LEDGER.md`): unit tests and builder probes ran policies on the F0-R development seeds 61000–61099, the seeds every F0-R number here comes from, and checked validity and rough performance there; an MPC unit test compared K-copy residuals with theory on the E3 seeds 61500–61599; one guard-design pilot on 60050–60059, a range outside every listed use, informed the choice of the candidate's guard form; generator-only statistical tests drew seeds 0–2000, which include the earlier Track E seeds 0–79. No tuned configuration was chosen on development seeds; a runtime guard now restricts tests to 60000–60049.
12. **Defects caught by review before any development run**, each fixed and re-reviewed: the wrapper leaked uncommanded participants' states at δ_A = 0; the policy random stream exposed the seed and cell; the first E2 split counted unavoidable shortfall as uncorrectable (biased toward the claim); HMM planners deferred units (biased toward the candidate over the population-rate MPC); an analysis path inflated E1 when a seed was missing; dev-seed selection of the best oblivious policy inflated E1; the bound row tripped a policy-only invariant in the pilot.
13. **Duplicated grid points.** uncorr_pes and user_flag share 24 of their 48 grid points with sym_margin (OPEN_QUESTIONS rows 39 and 45).

## 2. What held

- **Gate G1** (`docs/G1_REPORT.md`): max flow, leximin and minimum peak agree with an exhaustive enumerator on every instance with N ≤ 2 and H ≤ 2 in a bounded box (257,712) and on 20,000 random instances with N ≤ 4 and H ≤ 4; Propositions 1 and 3, gap(c) and the I1 table reproduce exactly, 2,723 of 2,723 rows.
- **E3, theory tracking** (Section 8): all 312 K-copy points lie inside their simultaneous 95% intervals.
- **NC2 and NC4 pass exactly**, and NC1-exact passes for every planning policy.
- **At M = 3, ρ = 1.15, e1 recovers a large share of the oracle's E1 contrast**: 0.69 [0.49, 0.87]. At M = 3, ρ = 0.95 the oracle's contrast is detected (+1.07 [+0.49, +1.65]) but the candidate's is not; its share there is 0.29 with no defined interval.

## 3. E1, the obliviousness gap

### 3.1 Primary (comparator fixed on tuning seeds)

| Stratum | E1 contrast | Reading | Oracle contrast |
|---|---|---|---|
| M = 0, ρ = 0.95 | +0.11 [+0.05, +0.19] | detected, below the practical threshold (artefact, item 6) | +0.35 [−0.22, +0.92] |
| M = 0, ρ = 1.15 | +0.04 [+0.00, +0.09] | detected, below the practical threshold (artefact, item 6) | +1.79 [+1.18, +2.41] |
| M = 3, ρ = 0.95 | +0.31 [−0.25, +0.85] | not detected at this size | +1.07 [+0.49, +1.65] |
| M = 3, ρ = 1.15 | **+1.05 [+0.59, +1.53]** | detected above the practical threshold | +1.53 [+1.04, +2.04] |

Gaps, best oblivious minus candidate, by delay (M = 3):

| ρ | δ_A = 0 | δ_A = 1 | δ_A = 2 | δ_A = 4 |
|---|---|---|---|---|
| 0.95 | −0.32 [−0.48, −0.17] | +0.72 [+0.28, +1.16] | +0.71 [+0.17, +1.24] | +0.31 [−0.50, +1.11] |
| 1.15 | −0.07 [−0.13, −0.03] | +1.18 [+0.72, +1.64] | +1.70 [+1.10, +2.31] | +1.52 [+0.84, +2.19] |

The comparator fixed on the tuning seeds is the population-rate MPC at δ_A ∈ {1, 2, 4} in every stratum, and at δ_A = 0 sym_margin (MPC-CE at M = 0, ρ = 0.95). At M = 0 every gap at δ_A ≥ 1 is exactly 0.

Mean R_avoid at M = 3, ρ = 1.15, δ_A = 2: candidate 2.42, population-rate MPC 4.12, oracle 1.78, MPC-CE 5.97, sym_margin 6.48 (bound 0 by definition).

### 3.2 Sensitivities

| Stratum | Floor allowed | Minimum-E1 comparator | Comparator |
|---|---|---|---|
| M = 0, ρ = 0.95 | −0.85 [−1.26, −0.46], reversed | −1.02 [−1.49, −0.55], reversed | ce_edf |
| M = 0, ρ = 1.15 | −0.89 [−1.26, −0.52], reversed | −0.87 [−1.38, −0.38], reversed | ce_llf |
| M = 3, ρ = 0.95 | −0.62 [−1.13, −0.13], reversed | −0.92 [−1.49, −0.37], reversed | ce_llf |
| M = 3, ρ = 1.15 | −0.26 [−1.00, +0.51], not detected | −0.32 [−0.83, +0.18], not detected | ce_llf |

The floor never gets stuck, so its recovery R_avoid is low; it pays 50 kWh per 100 of event shortfall for that (Section 6.2).

The minimum-E1 comparator is a certainty-equivalent priority rule (CE-EDF in one stratum, CE-LLF in three). Its gaps to the candidate are small or negative at δ_A = 0 (CE-LLF is ahead of the candidate there in three strata, e.g. −0.32 at M = 3, ρ = 0.95), largest at δ_A = 1 (+5.9 to +7.8) and smaller at δ_A = 2 and 4 (+0.7 to +4.1). So the candidate's lead over CE-LLF is large but does not grow with delay, and the delay contrast against it is negative or not detected. CE-LLF is also the tuned margin baseline (item 3).

## 4. Gate G2 and the population-rate rule

`docs/G2_REPORT.md` holds the gate on the pilot (61000–61019; numbers in `results/g2_numbers.json`, regenerated from a clean commit from `results/f0r_pilot/`): E1 −0.375 [−1.25, +0.50], not detected; the in-progress format was not forced only because the interval's upper end equals 0.5; the population-rate MPC reached 0.95 [0.63, 1.38] of the candidate's gain, the pre-declared headline. The owner chose the full 7-page format on October 20.

At full development size (100 seeds; the gate itself used the pilot):

| Quantity at M = 3, δ_A = 2, ρ = 0.95 | Value |
|---|---|
| E1 at the G2 stratum | +0.31 [−0.25, +0.85] |
| Candidate gain over sym_margin (= CE-LLF) | 4.05 [3.15, 5.00] |
| Population-rate MPC gain over sym_margin | 3.34 [2.48, 4.24] |
| Persistence gain over sym_margin | −0.29 [−0.47, −0.13] |
| Ratio, population-rate over candidate | 0.83 [0.70, 0.95] (point above 80%, interval not wholly above) |
| Ratio, persistence over candidate | −0.07 [−0.12, −0.03] |

## 5. E2, the correctability split

Candidate gain over the best oblivious policy, reading A (`R_uncorr_hi`); "holds" is the analysis's per-row test: the lower ends of the intervals of both the R_uncorr gain and the difference (R_uncorr gain − R_corr gain) lie above zero:

| Stratum | δ_A | Gain in R_uncorr | Gain in R_corr | Holds (reading A) |
|---|---|---|---|---|
| M = 3, ρ = 0.95 | 2 | −0.01 [−0.22, +0.18] | +0.72 [+0.23, +1.21] | no |
| M = 3, ρ = 0.95 | 4 | +1.85 [+1.40, +2.32] | −1.54 [−2.18, −0.92] | yes |
| M = 3, ρ = 0.95 | contrast | +0.78 [+0.53, +1.03] | −0.47 [−0.94, −0.01] | yes |
| M = 3, ρ = 1.15 | 2 | +0.14 [−0.04, +0.33] | +1.56 [+0.99, +2.13] | no |
| M = 3, ρ = 1.15 | 4 | +0.88 [+0.43, +1.33] | +0.63 [+0.18, +1.09] | no |
| M = 3, ρ = 1.15 | contrast | +0.30 [+0.05, +0.54] | +0.76 [+0.40, +1.12] | no |

Reading A supports the prediction at M = 3, ρ = 0.95: as delay grows from 2 to 4 the candidate's gain moves into uncorrectable shortfall, as the mechanism predicts. It does not at ρ = 1.15. Under reading B (`R_uncorr_lo = max(0, Σu − R*_couple)`) the candidate's gain in R_uncorr is 0 [0, 0] in every M = 3 cell and contrast, because in contested cells the coupling shortfall exceeds the traced uncorrectable shortfall, leaving R_uncorr_lo at 0 for the policies compared (0 for every policy at the G2 cell). Reading B therefore cannot support or refute the prediction; this is a limitation of the E2 definition used in this build. With the both-readings rule, E2's "supported" flag is false in every stratum. At M = 0 all E2 gains at δ_A ≥ 1 are exactly 0, as the M = 0 identity requires.

## 6. Secondary endpoints

### 6.1 History and stress sweeps (δ_A = 2, ρ = 0.95 unless stated; mean R_avoid)

| Cell | Population-rate MPC | Candidate | Oracle | sym_margin |
|---|---|---|---|---|
| M = 1 | 4.75 [3.95, 5.54] | 4.54 [3.77, 5.33] | 3.18 [2.49, 3.89] | 8.50 [7.06, 10.04] |
| M = 3 | 4.87 [4.05, 5.69] | 4.16 [3.33, 4.98] | 3.07 [2.39, 3.75] | 8.21 [6.99, 9.43] |
| M = 5 | 4.69 [3.87, 5.53] | 4.00 [3.21, 4.81] | 2.97 [2.26, 3.68] | 8.33 [6.83, 9.93] |
| M = 3, ρ = 0.7 | 6.53 [5.67, 7.43] | 6.37 [5.52, 7.23] | 6.09 [5.26, 6.93] | 7.72 [6.63, 8.81] |

Descriptive shares from these cell means (unpaired point estimates, no intervals): the candidate's gap to the population-rate MPC over the oracle's gap is 0.21/1.57 = 0.13 at M = 1, 0.71/1.80 = 0.39 at M = 3 and 0.69/1.73 = 0.40 at M = 5; 0.17/0.44 = 0.38 at ρ = 0.7. On the K-copy instance at q = 0.40, Proposition 3 predicts 0.40, 0.78 and 0.92 (per copy) or 0.25, 0.64 and 0.86 (pooled, large K). F0-R differs from the K-copy instance (heterogeneous windows, rates, obligations and a Markov return), so the comparison is indicative only; the shares rise with M but stay well below the K-copy values.

### 6.2 Floor during the event

Net recovery gain over the best oblivious policy, beside its event shortfall, never summed. Event shortfall is 50.0 kWh per 100 in every cell (2 units per floored participant). Net recovery gain ranges from −4.24 [−6.00, −2.59] (r = 0 cell) to +2.02 [+1.27, +2.73] (M = 3, δ_A = 4, ρ = 1.15). The floor buys at most about 2 kWh of recovery for 50 kWh of curtailment lost during the event.

### 6.3 Return probability, lag split, violations and compute

**Return-probability sweep** (M = 3, δ_A = 2, ρ = 0.95; gap best oblivious − candidate, and oracle gap):

| r | Gap | Oracle gap |
|---|---|---|
| 0 | +2.16 [+1.26, +3.05] | +2.30 [+1.36, +3.25] |
| 0.3 | +0.71 [+0.17, +1.24] | +1.80 [+1.21, +2.40] |
| 1 | +0.44 [+0.02, +0.85] | +0.67 [+0.25, +1.08] |

The gap is largest when stuck participants never return within the window; there the candidate's gap is close to the oracle's.

**Lag-split cell** (δ_A = 0, δ_b = 2): gap −0.42 [−0.62, −0.25]. With only base-load lag, the margin baseline beats the candidate.

**Violations, hedge waste, peak, misses, compute** at the G2 cell (M = 3, δ_A = 2, ρ = 0.95; means per event):

| Policy | Violation kW·slot | Violations per 100 | Longest run (slots) | Hedge waste kW·slot | Deadline misses per 100 | Peak kW | CPU ms per decision |
|---|---|---|---|---|---|---|---|
| bound | 0.00 | 0.0 | 0.00 | 0.00 | 33.0 | 41.44 | — |
| guarded_mpc_e1 | 1.97 | 12.6 | 1.53 | 0.03 | 42.4 | 42.44 | 3.7 |
| oracle_mpc | 1.99 | 13.1 | 1.56 | 0.02 | 42.0 | 42.44 | 3.7 |
| pop_mpc | 1.89 | 12.6 | 1.53 | 0.01 | 47.1 | 42.44 | 3.6 |
| mpc_ce | 1.73 | 11.7 | 1.50 | 0.00 | 44.9 | 42.36 | 3.4 |
| sym_margin | 1.58 | 10.7 | 1.49 | 0.00 | 70.4 | 42.29 | 0.1 |
| floor | 1.92 | 12.8 | 1.60 | 0.00 | 67.2 | 42.38 | 0.1 |

Tuning selected m = 0 in every frozen entry, so violations come from base-load forecast error and are similar across policies; the candidate's energy gain comes with slightly more violation.

**Scaling (N = 300, compute only):** mean CPU per decision 6.5 to 30.8 ms across the MPC families and cells (the candidate 11.4 to 28.6 ms; the larger values at δ_A = 0 include re-dispatch rounds), and at most 2.3 ms for the priority rules. At M = 3, δ_A = 2, ρ = 0.95 the ordering holds at N = 300: R_avoid candidate 4.80, population-rate MPC 5.93, oracle 3.97, sym_margin 9.15.

**RWDF-E against its literal form:** the literal index-first rule has higher R_avoid than the deadline-first form in every cell; the difference's interval includes zero in the r = 0 cell (1.25 [−0.58, +3.14]). Every other per-cell value: `docs/DEV_TABLES.md`.

## 7. Negative controls (`docs/NC_REPORT.md`)

| Control | Seeds | Verdict |
|---|---|---|
| NC1 (literal R_avoid = 0) | 60000–60049 | FAIL, not relabelled (owner ruling: base-load noise left in by the plan) |
| NC1_sp | 60000–60049 | FAIL, not relabelled |
| NC1-exact, planning policies (mpc_ce, mpc_pes, pop_mpc, guarded_mpc_e1, oracle_mpc) | 60000–60049 | PASS: R_avoid = 0 on all 50 seeds |
| NC1-exact, greedy rules | 60000–60049 | shortfall up to 3 units (LLF family), 18–20 (probe-first, EDF), 62 (literal RWDF-E): a finding consistent with LLF failing feasible instances under a shared limit, not a defect |
| NC2 | 60000–60049 | PASS: 0 mismatches in 118,646 actions |
| NC3′ | 60000–60049 | FAIL on interval width (6 of 16 cells); no interval excludes zero |
| NC3′ extended | 64000–64249 | FAIL overall: 15 of 16 cells inside ±0.5; M = 3, δ_A = 1, ρ = 0.95 "no difference detected at this size" [−0.21, +0.56]; M = 3, δ_A = 0, ρ = 0.95 a small detected difference against e1, +0.07 [+0.02, +0.14] |
| NC4 | 60000–60049 | PASS: identical trajectories, 50 of 50 seeds, all 8 cells |

The F0-R development runs went ahead after the NC1, NC1_sp and NC3′ failures, under the owner-side rulings of October 20 (OPEN_QUESTIONS).

## 8. E3, theory tracking on the K-copy family (K = 8, seeds 61500–61599)

- 312 points: R(pop) against q(K − c/2) (144), pop − oracle against gap(c) (144), pop − e1 against Proposition 3 (24).
- **Primary (approved simultaneous rule): all 312 lie inside their simultaneous 95% intervals** (Bonferroni over the family).
- **The plan's literal pointwise rule fails:** 11 points miss their pointwise 95% interval, against 15.6 expected by chance (binomial p = 0.91).
- **Direction.** Of the 144 R(pop) points, 107 lie below prediction, 8 above and 29 equal (24 of them at c = 2K, where the prediction is exactly 0). Of the 24 Proposition 3 points, the 6 at M = 0 equal their prediction of 0 and the other 18 all lie below (for example pooled q = 0.5, M = 1: 0.48 against 0.71; per-copy q = 0.4, M = 3: 1.17 against 1.25). All 11 pointwise misses are below. A downward shift shared by the oblivious R(pop) points is what fewer realized stuck copies on these seeds would produce, because the stuck draws are shared across cells; the points are therefore not independent and the binomial count is only indicative. A check conditioned on the realized stuck count is reported separately (`results/e3_conditioned.json`, diagnostic, added after this report).
- These seeds were looked at once during the build by an MPC unit test (item 11).

## 9. Gate history

| Gate | Date | Result |
|---|---|---|
| G1 | October 20 | Passed (`docs/G1_REPORT.md`) |
| G2 | October 20 | E1 not detected on the pilot; the population-rate headline fired; the in-progress format was not forced, by a tie at 0.5 (`docs/G2_REPORT.md`); the owner chose the 7-page format |
| G3, G4 | November 14, 18 | Not reached; outside this build |

## 10. Reading for the note

The evidence supports a narrower note than the plan's claim 2. Against the certainty-equivalent baseline, most of the gain comes from planning with a population-rate stochastic model; per-participant history adds a further, smaller gain that is clearest where the cap is most contested (M = 3, ρ = 1.15: E1 +1.05, about 0.69 of the oracle's contrast) and is not robust to the conservative comparators. The correctability split locates the gain in uncorrectable shortfall only at M = 3, ρ = 0.95 under one reading. The K-copy family tracks Propositions 1 and 3 under the approved simultaneous rule. Every number above is development; no confirmatory claim is possible from this build.

## 11. Changes after the review

All eleven required fixes were applied: E2 restated (blocking); the minimum-E1 comparators corrected (ce_edf in one stratum) with their δ_A = 0 behaviour and the sym_margin = CE-LLF identity disclosed; the M = 0, ρ = 0.95 δ_A = 0 comparator corrected to MPC-CE; "detected above the practical threshold in one of four"; the M and ρ sweep cells added against Proposition 3; the NC gate, the guard-form pilot and the development-seed performance looks disclosed; 18 of 24 Proposition 3 points below (6 exact); the "large share" sentence restricted; unsourced unit counts removed; the RWDF-E literal claim qualified; and the nits (−0.47, the scaling range, m = 0 in every entry, the G1 grid size, the g2_numbers provenance, negative R_avoid, "a population-rate stochastic model").
