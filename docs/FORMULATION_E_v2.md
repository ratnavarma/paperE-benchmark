# Track E formulation v2: delayed telemetry turns correction into hedging

Status: formulation for owner approval, October 19, 2026. No experiment, simulation, seed or compute lease was used. Written by the research lead from FORMULATION_E_v1, the private review record, the September 22 redesign brief, the v10 components and a new full-text novelty search. AI-assisted work, not independent review.

Owner decisions applied (D1–D8, October 19): E1 narrowed; leximin on shortfall fractions; ACN-Data and NREL profiles approved; numpy, scipy, networkx and cvxpy with open solvers, acnportal and adacharge pinned; development seeds 60000–63019, reserved 500000–500999 closed; ACM e-Energy 2027 primary; 30 cloud agent hours; adacharge MPC as comparator of record.

## 1. What changed from v1

| v1 | v2 | Why |
|---|---|---|
| Gain from MPC plus a headroom margin under one slot of delay | Gain from a per-participant debt posterior once delay reaches the remaining window | Condition 1 of the private review record. Worked in MECHANISM_E_v2.md |
| δ = 1 only | δ ∈ {0, 1, 2, 4}; primary endpoint is the slope against δ | Review fix |
| Availability and base load on one lag | Separate lags δ_A and δ_b, with a cell where they differ | Review fix. Base-load lag is the margin's job; availability lag is the posterior's |
| Setpoints assumed capped at believed debt | Delivery y = min(x, r) · A; setpoints to a complete participant deliver nothing | Needed for hedging to be well defined |
| One semantics for the limit | Setpoint cap primary; physical-load cap with overbooking secondary | Overbooking copies the gain under physical semantics on I1. Declared, not hidden |
| GTL as the published optimizer | adacharge MPC as comparator of record; GTL secondary | Condition 2 |
| Candidate tuned, others not | Equal tuning grid for every tunable comparator | Condition 2 |
| Optional logistic forecast | Learned delivery estimator with a dated gate and kill rule | Learning component for e-Energy and the L4DC option |
| IEEE TAI framing | ACM e-Energy 2027 framing | Condition 3 and GOAL.md |
| No data check before policies | Stop rule S0 on ACN-Data before any policy is built | Falsifier 2 can end the track in a day |

## 2. Claim under test

Under a shared setpoint cap, delayed availability telemetry costs avoidable residual that grows with the delay. The cost comes from setpoints whose outcome is learned after the participant's last usable slot. A policy that plans over a per-participant posterior of delivery recovers that cost. The best participant-symmetric margin rule, tuned on the same seeds, does not.

Who acts on the answer: an aggregator or charging-site operator choosing between faster telemetry, a margin, or a delivery estimator. What they do differently: they learn how many kWh per 100 participants each slot of delay costs. They also learn whether a margin buys it back and whether a learned estimator is worth deploying.

## 3. Formal problem

### 3.1 Sets and units

- Participants i ∈ I = {1, …, N}, N ∈ {30, 300}.
- Slots t ∈ {0, …, H − 1}, H = 24 slots of 15 minutes for F0 and F2. F1 uses the ACN session span, cut to 15-minute slots.
- One unit is 1 kW held for one slot, 0.25 kWh. All quantities are integer units unless stated.

### 3.2 Parameters

- E_i: obligation. In F0 and F2 this is energy deferred during a demand-response event. In F1 it is the session's requested energy, capped at the delivered energy observed in the data.
- P_i: per-slot rate limit. a_i: release slot. d_i: exclusive deadline.
- A_it ∈ {0, 1}: realized availability, meaning the participant would follow a setpoint in slot t. F1 also uses a fractional acceptance version, Section 3.4.
- Â_it ∈ {1, 0, ?}: announced availability, with "?" outside participant i's announcement horizon.
- b_t: uncontrolled base load. L_t: feeder limit.
- δ_A, δ_b: telemetry lags for availability and base load.

### 3.3 Information set

At decision slot t the operator knows:

- every parameter except A and b;
- the announcements Â;
- its own past setpoints x_is for s < t;
- delivered energy y_is for every participant, for s ≤ t − δ_A. Availability A_is is revealed only where a setpoint could have delivered (x_is > 0 and r_is > 0). Elsewhere it stays unknown. That is what makes a failure silent;
- base load b_s for s ≤ t − 1 − δ_b.

With δ_A = 0 the operator sees current availability, as in ACN-Sim. With δ_A = k ≥ 1 the outcome of slot s is known at slot s + k. Every online comparator receives exactly this set through one wrapper. No policy can read the true state.

### 3.4 Dynamics

- Setpoints: integer 0 ≤ x_it ≤ P_i for a_i ≤ t < d_i, else 0.
- Delivery: y_it = min(x_it, r_it) · A_it, with r_i(a_i) = E_i and r_i(t + 1) = r_it − y_it.
- F1 acceptance variant: y_it = min(x_it, r_it, ⌊P_i · α_it⌋), where α_it ∈ [0, 1] is the session's acceptance fraction taken from the observed current against pilot. A silent shortfall is any slot with α_it < 1 while a setpoint is active. This variant is used only if the ACN-Data check in Section 7 finds those time series.
- Feeder load: ℓ_t = b_t + Σ_i y_it.

### 3.5 The limit, two semantics

- **Setpoint cap (primary).** Policies must satisfy Σ_i x_it ≤ L_t − b̂_t − m_t, where b̂_t is the policy's base-load forecast and m_t its margin. This mirrors ACN practice. A violation can occur only through base-load forecast error.
- **Physical-load cap (secondary cell).** Policies may send Σ_i x_it above forecast headroom. Only ℓ_t > L_t counts as a violation.
- Under both semantics a violation has magnitude v_t = ℓ_t − L_t when positive. The count, the total in kW·slot and the longest run of consecutive violating slots are reported separately. A short overload is not automatically harm. Transformer thermal tolerance is outside the model, so duration is reported beside magnitude and no thermal claim is made.

### 3.6 Endpoints, each reported separately

- Delivered energy D, in kWh.
- Absolute residual R_abs = Σ E_i − D, in kWh.
- Avoidable residual R_avoid = R_abs − R*, in kWh, with R* from Section 3.7.
- Deadline misses: count of participants with r_i(d_i) > 0 and their kWh.
- Peak = max_t ℓ_t, in kW.
- Violations: count, kW·slot and longest run in slots.
- Hedge waste: setpoint units sent to participants whose true debt was already zero, in kW·slot. Under the setpoint cap this is capacity no one else could use.
- Compute per decision: single-thread CPU milliseconds.

kW and kWh never share a column. Energy is always read beside violations. Rates are expressed per 100 participants per event.

### 3.7 Infeasibility rule, fixed before any algorithm runs

Unchanged from v1 Section 5.8, with the owner's choice D2.

1. Flow network on the realized instance: source to i with capacity E_i; i to t with capacity P_i · A_it in i's window (⌊P_i · α_it⌋ in the F1 variant); t to sink with capacity max(0, L_t − b_t).
2. Maximum flow F*. Integer capacities give an integer optimal flow.
3. R* = Σ E_i − F*.
4. Own-capacity shortfall s_i^own = max(0, E_i − Σ_t cap_it). Coupling shortfall R*_couple = R* − Σ s_i^own.
5. Who is shorted: leximin on shortfall fractions s_i / E_i among maximum flows (D2).
6. Minimum peak P* among maximum flows by binary search on a peak cap.

R_avoid uses only R*. It does not depend on the shorting rule.

## 4. Mechanism and hand instance

MECHANISM_E_v2.md works instance I1 (N = 3, H = 2) by hand. Summary:

- δ_A ∈ {0, 1}: every capacity-aware policy reaches R = 0. Reliability information is worth nothing.
- δ_A = 2: the posterior-guarded policy reaches E[R] = 0. Every participant-symmetric rule has E[R] ≥ 0.25 units. That covers EDF, LLF, pessimistic or certainty-equivalent debt, any headroom margin and any deadline tightening.
- K copies: the gap is at least K · q / 2 units, linear in N. With q = 1/2 that is about 2.1 kWh per 100 participants per event.
- Physical-load semantics: an overbooking margin copies the result on I1. That is why overbooking is a comparator in the secondary cell.

Proposition 1 in the paper states the lower bound K · q / 2 for reliability-oblivious policies on the K-copy family, with the contested-cap formula gap(c). Proposition 2 states the necessary correctability condition s + δ_A ≤ d_i − 1. Both are proved by hand in the mechanism file, signed off on October 19, and checked by the exhaustive enumerator (build step 2) before any study run.

Theory deliverables, owned by the research lead:

- T1, closed-loop lower bound for 1 ≤ δ_A < H on a staircase family whose windows are longer than δ_A. Target: the oblivious gap grows at least linearly in the number of setpoints with s + δ_A ≥ d_i under a contested cap.
- T2, an upper bound for the posterior policy: E[R_post] ≤ R* + the expected uncertain units that no hedge can cover under the cap.
- Deadline for both: November 20, 2026. If T1 is not proved by then, the paper states the open-loop result only and labels the δ slope as measured. T2 is optional. The paper does not depend on it.

## 5. Families and cells

### 5.1 F0, synthetic post-event recovery (pilot)

- N = 30, H = 24. P_i uniform on {1, 2, 3}. E_i uniform on {2, …, 12}. a_i uniform on {0, 1, 2}. d_i = min(H, a_i + ⌈E_i / P_i⌉ + slack_i), slack_i uniform on {0, …, 12}.
- Availability after the event: each participant starts in a "stuck" state with probability q_i, meaning it silently fails to resume after the curtailment pause. Stuck and available form a two-state Markov chain with return probability 0.3 and stay-available probability 0.98. This is grounded in Brinkel et al. (N3): about one-third of tested EV models fail some pause tests and 86% of 42 models resumed after a 20-minute pause.
- Heterogeneity κ ∈ {homogeneous, heterogeneous}, both with mean q̄ = 0.14:
  - heterogeneous: a pause-intolerant class with share 1/3 and q_i = 0.40 and a tolerant class with q_i = 0.01;
  - homogeneous: q_i = 0.14 for every participant.
  Class membership is hidden. It enters the estimators only through confirmed outcomes and, in F1, through user history.
- Announcements: horizon h_i uniform on {8, …, 24}. Optimistic error probability 0.5 inside the horizon.
- Base load: B0 · (1 + 0.15 · s_t) + e_t, s_t a fixed evening ramp, e_t AR(1) with coefficient 0.7 and standard deviation 3% of B0.
- Constant limit L set by stress ρ = Σ E_i / Σ_t (L − E[b_t]).

Crossed cells within each seed:

- δ_A ∈ {0, 1, 2, 4} with δ_b = δ_A;
- ρ ∈ {0.7, 0.95, 1.15};
- κ ∈ {homogeneous, heterogeneous}.

That is 24 primary cells per seed. Added cells, at ρ = 0.95 and κ heterogeneous only:

- lag-split cells: δ_A = 2 with δ_b = 0 and δ_A = 0 with δ_b = 2;
- physical-load semantics at δ_A ∈ {0, 1, 2, 4}.

Within a seed, participants, availability and base-load noise are shared across cells. Cells are within-seed factors, not replicates.

### 5.2 F1, ACN-Data sessions (unseen)

- Sessions from ACN-Data. Arrival is the connection time and the deadline is the disconnection time. The announced departure is the user's requested departure, so announcement error is real. Obligation is the requested energy capped at the energy actually delivered in the data.
- Availability and acceptance come from the session's own current and pilot trace when the API exposes it (Section 7). Otherwise they come from a semi-Markov process fitted to session-level shortfall, stated as a fallback.
- Base load comes from one NREL End-Use Load Profile with a different ramp from F0.
- Cells: δ_A ∈ {0, 1, 2, 4} at the site's own stress level, κ as observed in the data.
- Train, tuning and test splits by calendar date. The learned estimator and every tuned knob see only the earlier dates. F1 test days are generated once, after the freeze.

### 5.3 F2, scaling

F0 at N = 300 on seeds 63000–63019, δ_A ∈ {0, 2}. Compute per decision only, plus a check that the F0 sign holds.

### 5.4 Seeds

- Tuning 60000–60049. Pilot F0 61000–61099. F1 sample draws 62000–62099. F2 63000–63019.
- Reserved 500000–500999 stays closed until the owner types "run".
- None overlaps 100000–100999, 200000–200999, 300000–300999, earlier Track E seeds 0–79 or Paper C seeds.

## 6. Comparators

Every online comparator gets the Section 3.3 information set through the same wrapper. The default base-load forecast is last value plus the tuned margin. The tuning grid has the same size, 12 points, for every tunable policy.

### 6.1 The factorial core

Belief about debt crossed with decision rule:

| Belief \ Rule | Priority rule (laxity order, fill headroom) | MPC over W slots (integer flow, min-cost) |
|---|---|---|
| Certainty-equivalent: unconfirmed setpoints assumed delivered | LLF-CE | MPC-CE (MPC-LA in v1) |
| Pessimistic: unconfirmed setpoints assumed failed | LLF-PES | MPC-PES |
| Posterior: expected debt and failure probability per participant | LLF-POST: hedge by posterior failure probability times urgency. A rule that reads a per-participant confirmed failure rate belongs here, not among the margins | Guarded MPC (candidate): expected-debt flow plus the v10 suffix-capacity guard at width w_i from the posterior |

The posterior comes from an estimator, Section 6.3. The posterior of record is the empirical per-participant estimate. The learned estimator replaces it only in a declared secondary contrast.

### 6.2 External, margin and reference rows

| Comparator | Objective | Information | Feasible actions | Tuning |
|---|---|---|---|---|
| Immediate release | full rate to every believed-available participant with believed debt | 3.3 | setpoint cap | none |
| EDF-CE | earliest deadline first | 3.3 | setpoint cap | none |
| Best symmetric margin | best of {EDF, LLF} × {CE, PES} × headroom m × deadline tightening k | 3.3 | setpoint cap | 12-point grid over (rule, belief, m, k) on tuning seeds |
| Probe-first (Brinkel's probing workaround) | send one unit to every participant at release, then LLF-CE; re-probe a participant whose probe failed | 3.3 | setpoint cap | none |
| Floor rule (Brinkel's 6 A floor analog) | keep a one-unit setpoint on every participant with believed debt until confirmed complete, then LLF-CE | 3.3 | setpoint cap | none |
| Overbooking margin (physical cell only) | LLF-PES with setpoints allowed up to (1 + o) × forecast headroom | 3.3 | physical cap | o on the same 12-point grid |
| sLLF (Chen et al.) | maximize minimum next-slot laxity | 3.3 | setpoint cap, continuous then rounded | paper defaults |
| **adacharge MPC (comparator of record)** | ACN's adaptive scheduling algorithm, pinned commit, its own objective as shipped | 3.3, fed as delayed session state and confirmed energy | its own constraints with the setpoint cap | its documented defaults, plus the same headroom margin grid |
| GTL-capped (secondary) | Gan–Topcu–Low ODC, then scaled to forecast headroom | 3.3 | rounded | none, as v1 Section 6.3 |
| Oracle-posterior guarded MPC | guarded MPC fed the true q_i | true q_i, otherwise 3.3 | setpoint cap | as candidate | 
| Clairvoyant bound | max flow, then min peak | full A, b, L | integer flow | labelled bound, not a policy |

adacharge runs unmodified. Only its inputs pass through the wrapper. If its interface cannot accept delayed state without code changes, the shim is published beside it and named in the paper. adacharge carries a custom Caltech non-commercial licence and was last committed on February 20, 2021. It runs in its own pinned environment (Python 3.9 to 3.11, cvxpy with ECOS), with rampdown on (`estimate_max_rate=True`, `SimpleRampdown`), fed delayed measurements. Its code is not redistributed. The artifact fetches it at the pinned commit.

Prior tooling: EV2Gym ships `FailedActionCommunication` and `DelayedObservation` wrappers (N8). The v2 wrapper differs in three ways. Failures are hidden for exactly δ_A slots. The debt ledger stays exact. The clairvoyant bound is computed on the same realized instance. The paper cites EV2Gym and states these differences.

The acnportal EDF and LLF run unmodified in the δ_A = 0 truthful cell as an agreement check on ours.

### 6.3 Delivery estimators and the learned component

- **e0, none.** CE and PES rows.
- **e1, empirical (posterior of record).** Beta–Bernoulli per participant on confirmed outcomes only, with a population prior fitted on tuning seeds, plus the Markov return term. In F1 the prior is per user ID where the data carry one.
- **e2, learned.** Gradient-boosted classifier, or logistic regression if it ties, predicting P(A_it = 1 or α_it ≥ 0.9 | delayed history). Features: time since release, fraction of E_i confirmed, last confirmed outcomes, announcement, time of day, the participant's confirmed failure rate so far. It trains only on labels the operator would have received by then, which makes it a delayed-feedback learning problem.

Gate for e2, dated November 7, 2026: under guarded MPC on tuning seeds and F1 tuning dates, e2 must lower R_avoid against e1 by at least the minimum effect of interest at δ_A = 2, with violations no worse. Kill rule: if it does not, e2 is reported as a failed prediction and dropped. L4DC 2027 is then dropped too. The gate result is recorded in GOAL.md on the day.

## 7. Data check before any policy (stop rule S0)

On ACN-Data, before any scheduler is built:

1. Confirm that per-session `chargingCurrent` and `pilotSignal` time series come through the `/ts` endpoint (the papers say about 4 s resolution). Confirm which pilot `pilotSignal` holds: the controller's command or the EVSE's applied pilot. Record the share of sessions that carry both. Cache the pull once. The JPL `/ts` pages return 502 errors on some ranges (acnportal issue 122).
2. Define a silent shortfall slot as one with active pilot and delivered current below 90% of pilot.
3. Measure between-session and between-user heterogeneity of the shortfall rate, with a bootstrap interval.
4. Fit e1 and e2 on early dates and score held-out AUC on late dates, using only delayed features.
5. Count the share of active setpoints with s + δ_A ≥ d_i at each δ_A in {1, 2, 4}.

S0 fires if the held-out AUC of the better estimator is below 0.60, or if between-user heterogeneity is indistinguishable from zero, or if the share in step 5 is below 2% at δ_A = 4. When S0 fires the track stops and the result is written up as a short negative note.

## 8. Pre-declared analysis

### 8.1 Primary family P (Holm, α = 0.05, two-sided, unit = seed, paired within seed)

For each seed and policy, fit the least-squares slope of R_avoid against δ_A over {0, 1, 2, 4}. Pool primary cells at κ heterogeneous across ρ, weighting cells equally.

- P1: slope of guarded MPC minus slope of the best symmetric margin, on R_avoid. Minimum effect of interest: 0.5% of obligated energy per slot of delay.
- P2: slope of guarded MPC minus slope of adacharge MPC, on R_avoid. Same minimum effect.
- P3: guarded MPC minus adacharge MPC on total violation at δ_A = 2, kW·slot per 100 participants per event. Noninferiority margin 1 kW·slot.

Operational reading of the minimum effect: in F0, 0.5% of obligated energy is about 0.9 kWh per 100 participants per event per slot of delay. In F1 it is about 5 kWh, roughly one participant's typical shortfall. Each P1 or P2 result is also reported as deadline misses per 100 participants.

### 8.2 Secondary, descriptive

- Factorial decomposition at δ_A ∈ {2, 4}: the belief effect within each rule, the rule effect within each belief and the interaction.
- Heterogeneity dose-response: the guarded-MPC gain at κ homogeneous against κ heterogeneous.
- Lag-split cells: whether the margin closes the base-load channel and the posterior the availability channel.
- Physical-load cell: guarded MPC against the overbooking margin, energy and violations side by side.
- e2 against e1 under guarded MPC (gate result).
- Oracle-posterior gap: how much of the oracle's gain e1 and e2 recover.
- Hedge waste per policy.
- Compute per decision at N = 30 and N = 300.
- Per-cell paired differences with their own intervals, for every δ_A, ρ and κ.

### 8.3 Negative controls (must pass before any study run)

- NC1: δ_A = 0, truthful announcements, ρ = 0.7. Every capacity-aware policy reaches R_avoid = 0.
- NC2: guarded MPC with the posterior set to certainty-equivalent and w = 0 equals MPC-CE decision for decision.
- NC3: κ homogeneous. Predicted: guarded MPC and the best symmetric margin are equivalent within the minimum effect at every δ_A. A large gain here would point to a defect, not the mechanism.

### 8.4 Seed count

Paired test at Holm level 0.05/3, two-sided, power 0.8: n = ((2.39 + 0.84) · σ_d / Δ)². σ_d is estimated on the first 20 pilot seeds. The count is at most 100 when σ_d / Δ ≤ 3.1 and rises to at most 300 otherwise. A test still underpowered is reported as "not detected at this size".

## 9. Stop rules

Applied after S0, after the pilot and again after F1.

- S0, nothing to target. Section 7.
- S1, no scheduling gap. If the best symmetric margin is within 2% of obligated energy of the clairvoyant bound on R_avoid in every cell, with mean violation at most 0.5 kW·slot per event, there is no paper.
- S2, the margin is the story. If the best symmetric margin captures at least 80% of the guarded-MPC gain on P1 at δ_A ≥ 2, the paper reduces to a margin rule. Recommend retirement or a short note.
- S3, delay is not a mechanism. If the slope of the best online policy is below the minimum effect on both R_avoid and violations, the question is answered negatively, kept and written up.
- S4, reference disagreement. Any disagreement between the max-flow bound and the exhaustive enumerator for N ≤ 4 and H ≤ 4 stops work until found.
- S5, unseen reversal. If the P1 or P2 sign reverses on F1, no general claim is made.

## 10. Claim boundary

If the study passes, the claim reads: under a shared setpoint cap with δ_A-slot availability telemetry, the avoidable residual of named online schedulers grows by stated kWh per 100 participants per slot of delay and a posterior-guarded scheduler changes that slope by a stated amount relative to adacharge and the best tuned margin. The boundary:

- F0 is synthetic, with failure rates set from Brinkel et al. F1 is semi-synthetic: real sessions, real announcement error and real acceptance traces, with a synthetic delay layer and a modelled base load.
- ACN's own telemetry is near real time, about 4 s. ACN grounds the failure process, not the delay. The delay regime is residential: devices reached through vendor clouds or AMI, which is mostly read hourly (DOE SGIG, A7). The paper says so in the introduction.
- One aggregate limit, no phases, no power flow, no thermal model.
- Integer 0.25 kWh units, 15-minute slots, δ_A up to 4 slots.
- N from 30 to 300.
- No calibrated household behavior after real demand-response events. No dataset covers it.

Results that would change the conclusion: measured field telemetry lags far below one slot; a multi-phase limit where hedges interact across phases; real event data in which failures are homogeneous across participants.

## 11. Threats to validity, stated now

- Internal: the posterior could leak true state through the wrapper. The wrapper is tested to refuse any read beyond Section 3.3. NC2 and NC3 also guard against this.
- Construct: avoidable residual measures energy shortfall, not customer harm. Deadline misses per 100 participants are reported beside it.
- External: ACN is workplace and campus charging, not households recovering after an event. F0 carries the event framing and F1 the real-data grounding. The paper says which result comes from which family.
- Comparator: adacharge is run through a shim. The shim is published and its effect is checked at δ_A = 0, where it must reproduce adacharge's own results.

## 12. Venue

- **ACM e-Energy 2027, Winter cycle, primary.** Abstract January 8, 2027 and paper January 15, 2027, AoE. Ten pages ACM sigconf, double-blind. Track: Control and energy systems, with Learning as second choice.
- **L4DC 2027, upside only.** Deadline November 13, 2026, not November 14. Its decision on January 25 falls after the e-Energy deadline, so one paper cannot be in both queues. If the e2 gate passes on November 7 and the owner wants L4DC, e-Energy waits for the L4DC decision. My recommendation is not to split. Keep e-Energy.
- **PGAI4E at AAAI-27, optional.** Due November 20, 2026, non-archival. e-Energy allows a substantial extension of a prior workshop paper, cited anonymously, with the differences explained. The two review windows do not overlap. Confirm with the e-Energy chairs before relying on this.
- IEEE TAI framing is removed.

## 13. Venue facts and novelty

See NOVELTY_TABLE_E_v2.md and the self-derived e-Energy rubric in RUBRIC_EENERGY_2027_selfderived.md.

## 14. Terminology

"Belief" is on the ICLR list of overclaimed terms. The paper uses "posterior over remaining debt" and defines it in Section 3. This file keeps "belief" only as the factorial's row label.

## 15. Cost estimate

| Item | Cloud agent hours |
|---|---:|
| Generator for F0 and F2, information-set wrapper, delivery and ledgers | 3–4 |
| Max flow, shorting rule, minimum peak, exhaustive enumerator check, propositions checked on I1 and K copies | 3–4 |
| ACN-Data pull and cache, S0 data check, F1 builder | 3–4 |
| Rules: IR, EDF, LLF in CE, PES and POST forms, margins, probe-first, floor, sLLF | 3–4 |
| MPC-CE, MPC-PES and guarded MPC on min-cost flow | 3–4 |
| adacharge pinned environment, shim and δ = 0 reproduction check; acnportal agreement check | 2–3 |
| Estimators e1 and e2, with the November 7 gate | 2–3 |
| Negative controls, tuning freeze, pilot, F1, F2 runs (CPU minutes) | 1–2 |
| Analysis, tables, DEV_REPORT_E, evidence ledger, frozen confirmation protocol | 3–4 |
| **Total** | **23–32** |

The upper end exceeds the D7 cap of 30 hours. To stay inside it, GTL-capped is dropped from the build (it was a secondary row) and the physical-load cell is run only for LLF-PES, overbooking and guarded MPC. That brings the estimate to 22–29 hours.
