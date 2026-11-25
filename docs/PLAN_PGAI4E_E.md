# Track E: plan for a non-archival PGAI4E note

Pre-declared plan, sections 1 to 8. The remaining sections were internal scheduling and are held in the private development record.

Status: approved by the author on October 19, 2026. Written October 19, 2026. Nothing is built. Written by the research lead after the owner's message "Don't retire yet. Plan the non-archival PGAI4E note (due Nov 20) with repeated-event F0 and the missing comparators." It narrows FORMULATION_E_v2 using the private review record.

## 1. Venue facts, checked October 19, 2026

Source: https://pgai4e.github.io/

- AAAI-27 Workshop on Physics-Governed AI for Energy, Montréal, February 22 or 23, 2027.
- Submission November 20, 2026, AoE. Notification December 2.
- Full papers 7 pages, in-progress papers 3–4 pages, AAAI-27 author kit.
- Double-blind on OpenReview. Non-archival. Accepted papers are posted in full on the workshop site unless the authors ask for the abstract only.
- No dual-submission rule is stated.
- Fit: the call names "observability, controllability, latency" as forces that shape which architectures are viable. It also names decisions constrained by operational limits. Both describe this note.

## 2. What the note claims

Three claims, each tied to an endpoint in Section 6:

1. Under a contested setpoint cap, once telemetry delay reaches the remaining window, any reliability-oblivious scheduler loses at least q/2 units per contested pair and the gap is a tent in the spare cap (Proposition 1).
2. Per-participant history learned across events recovers a stated share of that gap after M prior events: f = 1 − (1 − q)^M when each copy has its own cap and about f / (2 − f) when the cap is pooled (Proposition 3, new in this plan).
3. In a synthetic post-event recovery family with failure caused by the curtailment pause, the measured gap and its recovery track Propositions 1 and 3. The note reports whether simple rules close it: persistence, pessimism on uncorrectable setpoints, a population-rate stochastic MPC, a user-history flag and a floor during the event.

What the note does not claim:

- No real-data result. The family is synthetic, with failure rates set from a lab study (Brinkel et al. 2024) and delays labelled by channel from documented API behaviour.
- No per-slot cost of delay for any deployed system.
- No confirmatory test. Every number comes from development seeds and is labelled so. The reserved range 500000–500999 stays closed.
- Proposition 2, correctability, is credited to Kim, Li, Kadota and Modiano (Allerton 2015) for unit packets. The note gives only the divisible-energy form.

Predicted harsh-review score for the note: about 6 out of 10. That is enough for a workshop poster. It is not the owner's 8 bar and the note does not pretend otherwise. Its purpose is a public, citable first step and reviewer feedback before any e-Energy decision.

## 3. Changes from FORMULATION_E_v2, by review finding

| Review finding (row of the private review record) | Change in this plan |
|---|---|
| 1. e1 has no per-participant prior in single-event F0 | F0-R: M prior events per participant with a persistent hidden class |
| 3. Missing comparators; 3-point margin grid | Seven comparators added (Section 5); 48-point grid for every tunable family |
| 4. Slope endpoint attenuates a step effect | Primary endpoint is the gap at δ ∈ {2, 4} against δ ∈ {0, 1}, not a slope |
| 6. Failure exogenous; return probability unsourced; floor crippled | Failure caused by the pause; floor acts during the event, with its event cost reported; return probability swept |
| 7. Propositions reduce to known effects | Kim et al. credited; Proposition 3 added; experiments must track the propositions |
| 8. Mechanism attribution untested | Correctability split R_avoid = R_uncorr + R_corr is a primary endpoint |
| 11. NC1 tolerance, NC3 specification | NC1 on deterministic availability; NC3′ with homogeneous q and memoryless availability; NC4 added |
| 2, 5, 10. Delay grounding, ACN taper, adacharge shim | Out of scope for the note. ACN-Data, adacharge and F1 stay for any later e-Energy version |

## 4. Family F0-R: repeated events with pause-caused failure

Per seed:

- N = 30 participants, H = 24 recovery slots of 15 minutes. P_i, E_i, release and slack as in FORMULATION_E_v2 Section 5.1.
- Each participant has a hidden class: pause-intolerant with share 1/3, tolerant otherwise. Classes are assigned by a seeded random permutation, independent of index, P_i, E_i and window. A generator test checks that independence.
- Events: M prior events and one scored event. M ∈ {0, 1, 3, 5}. Prior events are fully confirmed by the time the scored event starts.
- Each event has a curtailment pause of 2 slots. After the pause a participant is stuck with probability 0.40 if intolerant and 0.01 if tolerant, a population mean of 0.14 (Brinkel et al., 20-minute pause, 42 models).
- A stuck participant returns to available with probability r per slot, r ∈ {0, 0.3, 1}. Available participants stay available with probability 0.98.
- Floor option: a participant kept on a one-unit floor during the event never pauses, so it never gets stuck. The floor costs one unit of curtailment per slot per floored participant. That event shortfall is reported in its own column.
- Delay δ_A ∈ {0, 1, 2, 4}, labelled by channel: 0 for OCPP at 90 s, 1 for Enode and ecobee, 2 to 4 for OEM telematics at 30–60 minutes. Base-load lag δ_b = 0 in primary cells.
- Stress ρ ∈ {0.7, 0.95, 1.15}. Contested cells are ρ ∈ {0.95, 1.15}.

Cells per seed:

- Primary: M ∈ {0, 3} × δ_A ∈ {0, 1, 2, 4} × ρ ∈ {0.95, 1.15}, at r = 0.3. That is 16 cells.
- One-at-a-time sweeps at δ_A = 2 and ρ = 0.95: M ∈ {1, 5}, r ∈ {0, 1}, ρ = 0.7. That is 5 cells.
- Lag-split cell: δ_A = 0 with δ_b = 2, at M = 3 and ρ = 0.95. That is 1 cell.

### K-copy validation family

Instance I_K from MECHANISM_E_v2 Section 3.6, with q ∈ {0.14, 0.40, 0.50}, spare cap c from 0 to 2K in K/4 steps and M ∈ {0, 1, 3, 5}. Its purpose is to check that measured gaps match gap(c) and the Proposition 3 curve within Monte Carlo error.

### Seeds (inside D5)

- Tuning 60000–60049.
- F0-R development 61000–61099.
- K-copy validation 61500–61599.
- Scaling at N = 300, compute only, 63000–63019.
- 62000–62099 stays unused, kept for any F1 on ACN-Data later.
- 500000–500999 stays closed.

## 5. Comparators

Every policy gets its inputs only through the information-set wrapper. Tunable families get the same tuning budget of 48 evaluations on tuning seeds.

| Class | Policy | What it uses |
|---|---|---|
| Oblivious | Certainty-equivalent LLF and EDF | confirmed history |
| Oblivious | Pessimistic LLF | treats every unconfirmed setpoint as failed |
| Oblivious | Best symmetric margin | {EDF, LLF} × {CE, PES} × headroom m ∈ {0, 1, 2} × deadline tightening k ∈ {0, 1, 2, 3} |
| Oblivious | Persistence | each participant's last confirmed state carries forward |
| Oblivious | Uncorrectable-only pessimism | PES for setpoints with s + δ ≥ d_i, CE otherwise (Proposition 2 as a rule) |
| Oblivious | Population-rate scenario MPC | the guarded MPC with one population failure rate for everyone |
| Oblivious | Probe-first | one unit to every participant at release, re-probe on failure |
| Oblivious | Floor during the event | Brinkel's workaround, with its event cost |
| Per-participant | User-history flag | pessimistic treatment for any participant stuck in a prior event |
| Per-participant | RWDF-E | Hou–Kumar and Kim et al. index: confirmed shortfall × p̂_i × q̂_i^m, with m the count of unconfirmed setpoints |
| Per-participant | LLF-POST | laxity order weighted by the e1 posterior |
| Per-participant (candidate) | Guarded MPC with e1 | Beta–Bernoulli per participant across events, population prior from tuning seeds |
| Reference | Oracle-posterior guarded MPC | true class; labelled reference, never the candidate |
| Bound | Clairvoyant max flow, then minimum peak | full realization; labelled bound |

Dropped for the note: GTL, adacharge, sLLF, the learned estimator e2 and the physical-load cell. The note says so.

## 6. Endpoints and analysis

Unit: the seed. Pairs: policies within seed and cell. Intervals: paired bootstrap, 10,000 resamples, 95%. All results are labelled development.

Primary, all reported per 100 participants per event:

- E1, the obliviousness gap. R_avoid of the best oblivious policy minus R_avoid of guarded MPC with e1, at δ_A ∈ {2, 4} against δ_A ∈ {0, 1}, by M and ρ, in kWh. It is also reported as a share of the oracle gap.
- E2, the correctability split. R_avoid = R_uncorr + R_corr for every policy, where R_uncorr counts shortfall traced to setpoints with s + δ_A ≥ d_i. Prediction: the candidate's gain sits in R_uncorr.
- E3, theory tracking. On the K-copy family, the measured gap against gap(c) and against the Proposition 3 values, for both the per-copy and the pooled cap. Pass if every point lies within its 95% Monte Carlo interval.

Practically meaningful effect: 0.5 kWh per 100 participants per event, which is two one-unit deadline misses per 100. For scale, the K-copy ceiling at q = 0.40 is 1.67 kWh per 100. An interval that excludes zero but stays below 0.5 kWh is reported as "detected, below the practical threshold". An interval that includes zero is reported as "not detected at this size".

Secondary, descriptive:

- Floor: net recovery gain against event shortfall, side by side, never summed.
- Return-probability sweep r ∈ {0, 0.3, 1}.
- Violations (count, kW·slot, longest run), hedge waste, peak, deadline misses, CPU ms per decision.
- The lag-split cell.

Negative controls, which must pass before the F0-R runs:

- NC1: deterministic availability, δ_A = 0, ρ = 0.7. Every capacity-aware policy reaches R_avoid = 0 exactly.
- NC2: guarded MPC with a certainty-equivalent posterior equals MPC-CE decision for decision.
- NC3′: homogeneous q with memoryless availability. Guarded MPC with e1 and population-rate MPC agree within 0.5 kWh per 100.
- NC4: at M = 0, guarded MPC with e1 and population-rate MPC agree within 0.5 kWh per 100, as Proposition 3 predicts.

## 7. Theory content

- Proposition 1, the oblivious lower bound and gap(c), proved in MECHANISM_E_v2 Section 3.6.
- Proposition 2, the necessary correctability condition, in divisible-energy form, credited to Kim et al. for unit packets.
- Proposition 3, new: on I_K with persistent classes (q for A, 0 for B) and M fully confirmed prior events, the e1 policy identifies an A copy when that copy was stuck at least once. That happens with probability f = 1 − (1 − q)^M, independently across copies. Unidentified A copies look the same as B copies. The result depends on how the cap is shared:
  - Cap per copy (each copy has its own cap of 2): the identified copy is hedged and the rest fall to the symmetric bound. E[R_e1] = K · (q/2) · (1 − f), so the share of the oblivious gap recovered is f.
  - Cap pooled across copies (cap 2K, spare K): with I copies identified, the e1 policy hedges those I and spreads the other K − I hedges over the 2K − I unidentified twins. E[R_e1 | I] = q · K · (K − I) / (2K − I). The recovered share is at least f / (2 − f) for every K, equals f at K = 1 and tends to f / (2 − f) as K grows (sign-off, October 19).
  - At q = 0.40: f = 0.40, 0.78 and 0.92 after 1, 3 and 5 events. Recovered shares are then 0.40, 0.78 and 0.92 per copy, against about 0.25, 0.64 and 0.86 pooled.
  - The research lead derived this by hand on October 19. A first draft of this plan stated 1 − (1 − q)^M for the pooled case, which is wrong. The hand proof goes into MECHANISM_E_v2 before the build and is signed off once.
- T1, the closed-loop bound, stays open and is listed as future work.

## 8. Kill gates

| Gate | Date | Test | If it fails |
|---|---|---|---|
| G1 | October 24 | Max flow agrees with the exhaustive enumerator on every instance with N ≤ 4 and H ≤ 4. The enumerator reproduces Propositions 1 and 3 exactly on small I_K | Stop and fix. No F0-R run before G1 passes |
| G2 | October 31 | Pilot on 20 F0-R seeds at δ_A = 2, ρ = 0.95, M = 3 | If the E1 interval sits wholly below 0.5 kWh per 100, the note becomes an in-progress paper of 3–4 pages framed as "simple rules suffice in this regime". If a population-rate or persistence rule reaches 80% of the candidate's gain, that is the headline |
| G3 | November 14 | Harsh review of the draft finds no claim that outruns the development evidence. The theory section is signed off | Fix before November 18, or cut to the in-progress format |
| G4 | November 18 | Owner reads the PDF | Owner submits or withholds |
