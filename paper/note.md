---
title: "Scheduling Electric Vehicle Charging Recovery after Demand Response When Delivery Is Confirmed Late"
keywords: "Demand response; Electric vehicle charging; Delayed telemetry; Model predictive control; Distribution feeder; Reliability learning; Managed charging"
status: "DRAFT 10, November 2, 2026, Applied Energy Phase 2: journal build, restored sections, utility-pilot section, post hoc ranker and review-check numbers."
---


# Abstract

Under a feeder limit, an operator replenishes deferred energy in electric vehicles prior to owner departure following a demand-response event. For some vehicles charging never resumes without notice and cloud confirmation can arrive 30 to 60 minutes late. We ask how much planning, one shared failure rate and reliability learned per participant help an operator. A two-slot example bounds the cost of a scheduler that ignores who is unreliable. We evaluate schedulers on a synthetic benchmark of 30 participants spanning 24 slots of 15 minutes. Under a frozen protocol, all five pre-declared tests passed on 200 held-out random instances with five-test-adjusted 99% intervals. Given three prior events, a 30-minute delay and a loose limit, a planner with one shared failure rate took {{confirm/C3}} of the advantage that a planner using per-participant reliability holds against least-laxity-first greedy. With a tight limit, that share dropped by {{confirm/C5}} between a 15-minute and a 60-minute delay. Per-participant learning showed a bigger lead at delays of 30 to 60 minutes than at 0 to 15 minutes, with {{confirm/C1}} kWh per 100 participants per event under the tight limit and {{confirm/C2}} under the loose limit. Both lower ends fell short of the 0.5 kWh practical threshold. Per-participant reliability helped inside the planner but not inside two greedy rules post hoc. The synthetic data draw the mean failure rate from a laboratory study, while documented refresh intervals set the delays. A utility pilot must confirm the share.

# Introduction

Imagine the close of a demand-response event. Thirty vehicles must return deferred energy before their owners leave. One feeder limit caps their combined draw. In lab tests, about a seventh of EV models failed to restart charging after a pause [brinkel2024]. On the slowest makes, the vehicle cloud logs what happened with a delay of up to about an hour [smartcar2026].

20 minutes of paused charging across 42 EV models yield the one-in-seven result. Unsuccessful units switch to sleep mode and ignore charging signals. A 6-hour pause on 21 models showed the failure share stood at about twice the level [brinkel2024].

Deployed programs may also often feature silent non-delivery. A review of a utility EV program spotted technical glitches or opt-outs in 29% of plugged-in event statuses [guidehouse2022]. Across the 18 events featuring 10 or more plugged-in vehicles, the share varied between 13% and 41% for each event. The evaluation could not distinguish the two causes.

Verification lags, too. Via manufacturer clouds, the slowest vehicles update their data only every 30 to 60 minutes [smartcar2026]. A vehicle that is idle or asleep transmits no data whatsoever [smartcar2026]. A demand-response provider reported in a 2017 regulatory filing that it received utility meter data about 48 hours later [ohmconnect2017].

Fast confirmation makes a failed setpoint simple to correct. The operator notices it and transmits the energy once more. If confirmation lags behind the time remaining before a deadline, the operator must pre-select who receives additional energy. We name that surplus energy a hedge.

The smallest case displays the problem. Each of the two participants owes one unit, and one of them, though nobody knows which, is silently unreliable. Wasting a spare unit in a hedge to the wrong one costs the operator q, the chance that the unreliable one fails.

Utilities and aggregators operating managed-charging programs care about this. A vehicle lacking energy at its deadline is a customer who departs with less charge than promised. Additional hedges tap the same feeder limit the event shielded.

What does an operator gain from three capabilities, the three steps of our results?

- planning is the use of a planner rather than a greedy priority rule.
- shared-rate hedging is a stochastic model of silent failure that applies one rate to everyone.
- per-participant targeting learns reliability per participant across events

## Related work

Uncoordinated EV charging may burden home distribution networks [clementnyns2010]. Smart charging may reduce how EVs affect transmission and distribution systems [crozier2020]. Demand-side management extends to the real-time regulation of distributed energy resources [palensky2011]. Controlling many small loads together constitutes a distinct control problem [callaway2011]. A demand-response event lets deferred energy come back as a rebound. This paper schedules that rebound for EVs with deadlines if delivery is confirmed late. Published EV charging records capture actual arrival times, departure times, and energy demands [lee2019acndata].

Adaptive charging networks plan using MPC and convex optimization [lee2021acn] to meet unbalanced three-phase limits. A rule called rampdown applies the measured charging current to recover capacity a vehicle does not draw. Rampdown requires that current in real time, but that signal arrives late here.

Smoothed least-laxity-first characterizes deadline feasibility under a shared limit. The result also shows that basic LLF may fail instances that are feasible offline [chen2021sllf]. MPC and a two-stage stochastic program incorporating user behavior address uncertain arrival and departure times at large charging stations [puech2024]. A framework for online optimization operates using user estimates of energy and departure time, or without them [tucker2022]. As we read them, these models all fail to model delivery feedback that arrives late.

The EV2Gym simulator tests smart-charging algorithms [ev2gym2024]. Its code release provides handlers for failed action signals and one-step-lagged observations [ev2gym2025code].

Wireless scheduling pairs deadlines and per-client channel reliability [hou2009]. Kim et al. introduce delayed acknowledgments [kim2015].

We add divisible energy, a shared setpoint cap, reliability learned across events and a bound for reliability-blind schedulers. Index policies [taylor2014] and bandits [kalathil2015] learn which loads react to demand-response signals. Data-driven targeting picks the customers for demand-response [kwac2016]. State augmentation also handles delayed state [katsikopoulos2003]. Kalman filtering infers the energy load state when real-time measurements are absent [mathieu2013]. A third route [chapelle2014] learns from delayed labels. Delayed-feedback online learning examines how lag increases regret [joulani2013].

Each of our three steps carries a standard name. A value of the stochastic solution [birge1982] is the hedging step. The targeting step and the oracle gap are values of information. Shared-rate MPC versus Targeted MPC means complete against partial pooling of the failure rate [gelman2013].

## Contributions

Our contributions:

1. For the two-slot case, a scheduler unable to read the class drops at least q/2 units per pair in expectation (Proposition 1). Proposition 3 quantifies the share of the loss that M earlier events recover. It holds exactly per pair and bounds the share from below under a pooled cap. Neither addresses lags that fit inside the window.
2. This is a development study featuring pre-declared endpoints and explicitly labeled post hoc analyses. For 100 development seeds at the reference cell (three prior events, a 30-minute lag, the loose limit), a planner with one shared failure rate captures {{g2_full/ratio/pop_mpc|v}} of the benefit from a model that identifies who fails, including the planning step. One of two informative strata detected the delay contrast and the correctability split was not supported.
3. A confirmation run on 200 reserved seeds under a frozen protocol. Each of the five declared tests was supported, including two found post hoc in development. For these seeds the planner with one shared failure rate captures {{confirm/C3|v}} of that gain at the reference cell. The tight limit makes the share drop as the delay rises from 15 to 60 minutes (C5).
4. This post hoc factorial crosses three beliefs with three decision rules: least-laxity-first, a greedy expected-value ranker, and the planner. A single shared failure rate aids both the planner and the greedy expected-value ranker. Inside the planner, per-participant reliability helps at a 30-minute delay under both limits, though it does not help inside LLF or the ranker.
5. A statement of what a utility pilot needs to record and gauge to verify or disprove the share in contribution 3 (Section "From a synthetic benchmark to a utility pilot").

# Model

Participants i = 1, ..., N recover over slots t = 0, ..., H − 1 of 15 minutes. One unit is 1 kW for one slot, or 0.25 kWh. Participant i owes E_i units, takes in no more than P_i per slot and spans release a_i to exclusive deadline d_i (Figure 1). The energy is stated in kWh, and δ slots equal 15δ minutes. The mean obligation at the reference cell is {{fla/obligation/M3_rho0.95/dA2/E_kwh_per100}} kWh per 100 participants per event.

[[FIG: fig_setting]]

Notation used in the prose:

- N – participants per seed, a count
- H – horizon, in 15-minute slots
- δ – confirmation delay, in slots
- δ_b – base-load lag, in slots (0 except in one lag-split cell)
- ρ – stress, obligations over expected headroom, a ratio
- M – earlier events with confirmed outcomes, a count
- q – chance that an unreliable participant is stuck after a pause
- r – chance per slot that a stuck participant returns
- R_it – remaining debt of participant i at slot t, in units
- R_avoid – avoidable residual, in kWh per 100 participants per event (kWh per 100 below)

The operator transmits whole-number setpoints x_it. For participant i at slot t, delivered energy is y_it = min(x_it, R_it) · A_it. R_it gives the actual residual debt of i at slot t, while A_it logs if participant i honors a setpoint in slot t. A setpoint sent to a participant that is unavailable or finished delivers nothing.

In slot t, the operator has the parameters, its own setpoints and the energy y_is delivered for s ≤ t − δ. It infers A_is solely at points where a setpoint could deliver, meaning x_is > 0 and R_is > 0. A stuck participant remains hidden until the operator issues a command and observes no delivery. At δ = 0, the slot reveals a failed command and the operator re-dispatches the slot.

Setpoints for a slot stay inside forecast headroom, similar to adaptive charging networks that total charging-rate signals against the limit [lee2021acn]. Only base-load forecast error can then cause a violation.

The clairvoyant reference has full information on the actual availability and headroom, just as the offline optimal of adaptive charging networks does [lee2021acn]. It equals the largest flow they permit. The minimum residual R* equals the obligation less that flow. R_abs equals the obligation minus the delivered energy. R_avoid, the avoidable residual, equals R_abs minus R* and is the primary endpoint.

Schedulers rely on forecast headroom, but the reference relies on realized headroom, which lets R_avoid turn negative. For three prior events, with ρ = 0.95 and δ = 0, the planner that learns who fails averages {{cell/F0R_M3_dA0_db0_rho0.95_r0.3/guarded_mpc_e1/R_avoid_kwh_per100}} kWh per 100. A deadline miss is a participant that has debt at its deadline, even one unit of 0.25 kWh. Violations and deadline misses are reported separately. Power and energy never share a column.

# Theory

## The running example

Instance I1 is the two-slot example from the introduction, having a cap of 2 units per slot. Each participant takes in no more than 1 unit per slot. A and B each owe 1 unit. D owes 1 unit, deliverable in slot 1 only. A or B is unreliable: it fails in slot 0 with probability q and succeeds in slot 1. The other stays available in every slot. The operator cannot distinguish between the two.

For δ ∈ {0, 1}, EDF, LLF and any capacity-aware MPC deliver everything. For δ = 2, no observation occurs before the horizon ends. D requires one unit of slot 1, leaving one unit of spare cap for a hedge. The hedge sent to the unreliable twin loses nothing. It loses q on average if routed to the other.

## Statements

**Proposition 1.** Take K copies of I1 on one feeder with cap 2K per slot and δ ≥ 2. In each pair, the unreliable twin is chosen uniformly at random, independently across pairs and of every observable. Every scheduler whose schedule law is independent of the class draw then has expected residual at least K q/2 units. So does its worst case over class assignments.

With the spare cap set to K, a class-aware scheduler suffers no loss. After the D copies, an informed scheduler with a general spare cap c loses nothing only if c ≥ K. The difference between the two equals q c/2 for c ≤ K. When K ≤ c ≤ 2K, the value reads q (K − c/2).

**Proposition 2.** Under delay δ, consider a failed setpoint to i in slot s. A setpoint can condition on the failure only in slots t with s + δ ≤ t ≤ d_i − 1. So s + δ ≤ d_i − 1 is necessary for correction by re-dispatch. A failure can be corrected only if its confirmation arrives while the window is still open (Figure 2).

[[FIG: fig_window]]

**Proposition 3.** Suppose classes persist across events. An unreliable copy fails after each pause with probability q, independently across events given its class. A reliable copy never fails. Take M earlier events, each fully confirmed. An unreliable copy has failed at least once in them with probability f = 1 − (1 − q)^M. Such a copy is identified.

Picture a scheduler that orders twins according to a failure estimate and places hedges in that sequence. The estimate must be strictly increasing in past failures, equal for equal histories and blind to labels. Applying a cap per pair makes the scheduler recover exactly the share f of the Proposition 1 gap. No history-only scheduler recovers any more.

With a pooled cap, the 2K twins share a single cap and parameter set, so pair membership is not an input. Once I copies are identified, the scheduler's mean residual equals q K (K − I)/(2K − I). A recovered share reaches no less than f/(2 − f) across all K, hitting that bound only as K grows.

When q = 0.40, the per-pair share equals 0.40, 0.78 and 0.92 after one, three and five events. The pooled share is at least 0.25, 0.64 and 0.86, the large-K limits. At K = 8 the exact binomial sum comes out slightly higher. Pooling lowers it because the reliable partners of identified copies stay in the unidentified pool.

## Proof sketches

Proposition 1. With δ ≥ 2 nothing is seen before the horizon ends, so a scheduler fixes its whole schedule in advance. A schedule blind to the class puts each pair's spare unit on the unreliable twin half the time. Each pair then loses q/2 on average, while a scheduler that knows the classes loses nothing.

Proposition 2 is elementary. Kim et al. study the same timing question for unit packets with deadlines and delayed acknowledgments [kim2015].

Proposition 3. A copy that failed in an earlier event is identified, which happens with probability f. Its pair gets the right hedge and loses nothing. An unidentified pair is the blind problem of Proposition 1 and loses q/2. Under a pooled cap identified twins take hedges first. Jensen's inequality over the number identified then gives f/(2 − f). Full proofs are in Appendix B.



# Study design

## Recovery family

Every seed takes N = 30 participants across H = 24 slots. Rates range from 1 to 3 units and obligations range from 2 to 12 units. Release spans slot 0 to 2 and slack spans 0 to 12 slots. One third of participants are pause-intolerant, positioned via a seeded permutation uncorrelated with any observable.

A two-slot pause of 30 minutes leaves an intolerant participant stuck with probability 0.40, while a tolerant one faces probability 0.01. The mean is 0.14, the share of 42 EV models tested that failed the 20-minute paused-charging test [brinkel2024]. That study saw more frequent failures with longer pauses, so our q might sit a bit low.

Each slot has probability r for a stuck participant to come back. Every participant holds M earlier events, all confirmed.

Delay δ ∈ {0, 1, 2, 4} denotes fast charger telemetry, a 15-minute cloud refresh and a 30 to 60 minute vehicle-cloud refresh. Stress ρ ∈ {0.95, 1.15} measures obligations against expected headroom, where ρ = 1.15 marks the tight limit and ρ = 0.95 the loose limit. The primary cells span M ∈ {0, 3}, δ and ρ with r = 0.3. Each sweep changes M, r or ρ in turn. The reference cell takes M = 3, δ = 2 and ρ = 0.95.

## Validation family

Proposition 1's K-copy family uses K = 8 and q ∈ {0.14, 0.40, 0.50}. Spare cap runs from 0 to 2K units per slot, or 0 to 16 kW. Earlier events span M ∈ {0, 1, 3, 5}. We run it under pooled and per-pair caps.

## Schedulers

Every one takes identical information via a wrapper blocking all access to hidden state. Four of them bear the labels applied from this point forward:

- CE-LLF (the greedy rule), certainty-equivalent least-laxity-first, serves the least slack first and trusts every setpoint
- CE-MPC (the planner): certainty-equivalent receding-horizon MPC
- Shared-rate MPC is the planner with one failure rate
- Targeted MPC is the planner that learns who fails.

Certainty-equivalent EDF, pessimistic LLF and the best of 48 margin settings over rule, belief, headroom and deadline tightening make up the other reliability-oblivious rules. Persistence, pessimism on uncorrectable setpoints only, probe-first and an event floor are four more rules, not prior-rule behaviors. The per-participant rules consist of a flag for participants stuck before, a reliability-weighted debt index and LLF with a per-participant posterior (LLF-POST). These references are the oracle (Targeted MPC assuming the true class) and the clairvoyant reference.

The index ranks participants by laxity or deadline first. A tie goes to the larger product of confirmed debt, the chance the participant is available now and the chance all unconfirmed setpoints failed. It modifies the weighted-delivery debt of Hou et al., dividing debt by channel reliability [hou2009]. It also draws on scheduling with delayed acknowledgments [kim2015].

The setting of each tunable family came from 48 evaluations on 50 tuning seeds and was frozen before the development run. It used only R_avoid as the objective, breaking ties by violations. Therefore, a margin greater than zero could not win. Tuning picked a zero margin in every case. Where this paper applies the "best margin rule", δ = 0 and the reference cell, the frozen setting is LLF without deadline tightening, so it equals CE-LLF there. For the remaining cells, the freeze selected EDF or a tightened deadline.

We left out the adaptive charging network scheduler with its rampdown rule [lee2021acn] since that rule needs a measured charging current which is delayed in this setup. We did not run a learned delivery estimator or the Gan–Topcu–Low protocol [gan2013]. Post hoc, we added Smoothed LLF [chen2021sllf] and the greedy expected-value ranker as stronger greedy anchors.

## The planner in equations

CE-MPC, Shared-rate MPC and Targeted MPC share one planner and differ only in its belief. At slot t it plans the slots s = t, ..., H_t − 1, with H_t = t + *W* capped at H, then executes slot t only. The window *W* is tuned per cell from {2, 4, 8, 24} slots.

The belief is a two-state chain per participant: stuck after the pause with probability q_i, returning with probability r per slot and staying available with a fitted probability. Targeted MPC takes q_i as the Beta–Bernoulli posterior mean over the M earlier events of i. Shared-rate MPC takes the same posterior pooled over every participant's events. CE-MPC uses a point belief instead: every setpoint delivers and every participant stays available.

An exact forward pass gives e_k(i, s) = P(R_it ≥ *k* and A_is = 1) and p_i(s) = P(A_is = 1). The *k*-th unit of i in slot s is worth v_k(i, s) = min(v_k(i, s − 1), e_k(i, s)), from e_k at the first slot max(t, a_i). So a unit is never worth more for waiting. The plan cannot drift units to the end of the window when a stuck participant is forecast to return.

The guard of Shared-rate MPC and Targeted MPC pulls uncertain units into slots where a failure can still be seen and retried. Its scale γ is tuned per cell from {0, 0.5, 1, 2}.

Let δ_1 = max(δ, 1) and o_k(i) = P(R_it ≥ *k*). A slot with s + δ_1 < d_i gets u_k(i, s) = v_k(i, s) + min(1, γ p_i(s + δ_1)) · (o_k(i) − v_k(i, s)). Other slots keep u_k = v_k, again under a running minimum.

With 0 ≤ z_k(i, s) ≤ 1 per unit and slot, the planner maximizes Σ u_k(i, s) z_k(i, s). Rate rows Σ_k z_k(i, s) ≤ P_i hold per participant and slot. Cap rows keep each feeder group within its forecast headroom C_g(s) in each slot. Unit rows Σ_s z_k(i, s) ≤ 1 plan each unit once, with equal units sharing one row.

The rate rows nest inside the cap rows and the unit rows partition the variables. These two laminar families make the matrix totally unimodular, so the LP vertex is integral. HiGHS dual simplex solves it, with a MILP fallback for a fractional vertex. Tie preferences of order 0.00001 per unit favor earlier slots and urgent participants among plans of equal value.

The remaining details are in docs/POLICY_SPEC.md of the code release. They cover deadline tightening for CE-MPC, the forecast rule for later slots and tie-breaking. They also give the Beta prior of the posterior and the fitted chance of staying available. The frozen *W* and γ of each cell are in results/TUNING_FROZEN.json.

## Endpoints

The delay contrast (E1 in the code) equals a difference of gaps. The gap subtracts R_avoid of Targeted MPC from R_avoid of the best oblivious scheduler. The delay contrast equals the mean gap for δ ∈ {2, 4} less the mean gap for δ ∈ {0, 1}.

The tuning seeds locked in the best oblivious scheduler per cell. For M = 3, CE-LLF applies at δ = 0, while Shared-rate MPC applies at δ ≥ 1. We calculate the contrast across four strata, M ∈ {0, 3} crossed with ρ. At M = 0, the learned rate matches the shared rate. Only the two M = 3 strata, the informative strata, can show an effect.

E2 correctability split partitions R_avoid into correctable and uncorrectable components. Shortfall traced to setpoints that Proposition 2 rules out of correction is uncorrectable. The split predicts that Targeted MPC gain lies in the uncorrectable part. The plan demanded this under two readings of that part, the first applying the traced shortfall (Appendix A.1).

Theory tracking (E3) matches measured gaps on the validation family against Propositions 1 and 3. The gate functioned as a pre-declared check at the reference cell (M = 3, δ = 2, ρ = 0.95). The scale is the gain of Targeted MPC over CE-LLF. It asked whether Shared-rate MPC or persistence reaches 80% of that gain.

## Analysis

The unit equals the seed. We use paired bootstrap 95% intervals with 10,000 resamples over the 100 seeds of a development cell. We count an effect above 0.5 kWh per 100, two one-unit deadline misses, as practically meaningful. We use the phrase "not detected at this size" if a bootstrap interval contains zero.

## Post hoc analyses

An earlier formulation pre-declared a belief-by-rule factorial as a secondary analysis. The decompositions, the reliability-blind shares, the additional executions, and the conditional verification of theory tracking were selected following the development outcomes. The greedy expected-value ranker, the delay contrast against a single fixed comparator and the scan across the violation exchange rate came in after a pre-submission review. A subsequent revision included the confirmation run's per-cell means, which the frozen protocol promised, by reading its existing rows, and added more descriptive shares on development rows. The later revision also included a diagnostic policy run of CE-LLF and CE-MPC on the tuning seeds. The remaining post hoc analyses rely on development seeds alone. The confirmation table uses existing rows of reserved seeds, with no rerun, while the diagnostic used tuning seeds. We mark each at its location. The post hoc intervals lack multiplicity adjustments.

# Results

## Pre-declared outcomes

In the reference cell (M = 3, δ = 2, ρ = 0.95), the four planning-ladder schedulers produce this avoidable residual in kWh per 100 participants per event: CE-LLF {{cell/F0R_M3_dA2_db0_rho0.95_r0.3/ce_llf/R_avoid_kwh_per100}}, CE-MPC {{cell/F0R_M3_dA2_db0_rho0.95_r0.3/mpc_ce/R_avoid_kwh_per100}}, Shared-rate MPC {{cell/F0R_M3_dA2_db0_rho0.95_r0.3/pop_mpc/R_avoid_kwh_per100}} and Targeted MPC {{cell/F0R_M3_dA2_db0_rho0.95_r0.3/guarded_mpc_e1/R_avoid_kwh_per100}}. CE-LLF, CE-MPC, Shared-rate MPC and Targeted MPC miss {{cell/F0R_M3_dA2_db0_rho0.95_r0.3/ce_llf/deadline_miss_count_per100}}, {{cell/F0R_M3_dA2_db0_rho0.95_r0.3/mpc_ce/deadline_miss_count_per100}}, {{cell/F0R_M3_dA2_db0_rho0.95_r0.3/pop_mpc/deadline_miss_count_per100}} and {{cell/F0R_M3_dA2_db0_rho0.95_r0.3/guarded_mpc_e1/deadline_miss_count_per100}} deadlines per 100 participants per event, respectively. These levels are descriptive. Post hoc, Targeted MPC beats CE-LLF by {{fla/obligation/M3_rho0.95/dA2/total_pct}} percent of the obligation. Targeted MPC leads Shared-rate MPC by {{fla/obligation/M3_rho0.95/dA2/targeting_pct}} percent. Section "Secondary endpoints" holds the limit excess. A trial-run gate preceding the development run appears in Appendix A.4.

The class-blind hedge on the two-slot instance of Proposition 1 already cuts the loss in half, from q to q/2 per pair. Class information recovers the remainder. Shared-rate MPC took most of the gain at the reference cell as here and in C3 (Section "Confirmation"). The instance may sketch that form but fails to forecast the confirmed share of {{confirm/C3|v}}.

The delay contrast is detected above the practical threshold in one of the two informative strata: {{e1/primary/M3_rho1.15/contrast}} at M = 3 and ρ = 1.15. {{e1/primary/M3_rho0.95/contrast}} at ρ = 0.95 is not detected at this size. We applied two conservative comparators to the same seeds. Allowing the floor as comparator, it is {{e1/sensitivity_floor/M3_rho0.95/contrast}} at ρ = 0.95 (reversed) and {{e1/sensitivity_floor/M3_rho1.15/contrast}} at ρ = 1.15 (not detected). With the oblivious rule that minimizes the contrast on these seeds, it is {{e1/sensitivity_min_e1/M3_rho0.95/contrast}} (reversed) and {{e1/sensitivity_min_e1/M3_rho1.15/contrast}} (not detected). So the delay contrast varies with the comparator. The delay contrast subtracts the δ = 1 gap, nonzero here (Table 1).

The correctability split is not supported. The first reading at ρ = 0.95 assigns {{e2/M3_rho0.95/contrast/readingA/gain_uncorr}} of the contrast to the uncorrectable part and {{e2/M3_rho0.95/contrast/readingA/gain_corr}} to the correctable part. However, the rule demanded both readings and our endpoint definition was flawed (Appendix A.1).

[[TABLE: gap]]

Table 1 lists the gap against each comparator at every delay, under the avoidable residual for three schedulers. Targeted MPC beats Shared-rate MPC by {{e1/primary/M3_rho1.15/gap_dA2}} under the tight limit at δ = 2. The oracle takes the lead by {{e1/primary/M3_rho1.15/oracle_gap_dA2}}.

For δ = 2 and ρ = 0.95, the learned reliability recovers {{layers/msweep/M1/share}} of the oracle's lead after one event, {{layers/msweep/M3/share}} after three, and {{layers/msweep/M5/share}} after five. Proposition 3 yields at least 0.25, 0.64 and 0.86 in the limit, but this holds only for the pooled two-slot instance. Since the recovery family is a different instance, these shares do not test the bound.

## Confirmation

We locked five tests, the analysis code, and a record of file hashes prior to revealing any reserved seed. The run applied seeds 500000 to 500199 a single time, with M = 3 and r = 0.3. A test earns supported status only if its 99% interval, corrected by Bonferroni for the five tests, sits entirely on the predicted side. For the development seeds the frozen script reproduced all development values.

The frozen protocol also pledged cell-level means over the reserved seeds. Table 2 reports the avoidable residual for five schedulers and the gap behind C1 and C2. It describes, it does not test. For these seeds the gap at δ = 1, 2 and 4 is {{confirm_cell/M3_rho0.95/dA1/gap|v}}, {{confirm_cell/M3_rho0.95/dA2/gap|v}} and {{confirm_cell/M3_rho0.95/dA4/gap|v}} under the loose limit and {{confirm_cell/M3_rho1.15/dA1/gap|v}}, {{confirm_cell/M3_rho1.15/dA2/gap|v}} and {{confirm_cell/M3_rho1.15/dA4/gap|v}} under the tight limit. No trend test among δ ≥ 1 was declared and we claim none. In the reference cell, CE-LLF, CE-MPC, Shared-rate MPC, Targeted MPC and the oracle miss {{confirm_cell/M3_rho0.95/dA2/ce_llf/deadline_miss_count_per100|v}}, {{confirm_cell/M3_rho0.95/dA2/mpc_ce/deadline_miss_count_per100|v}}, {{confirm_cell/M3_rho0.95/dA2/pop_mpc/deadline_miss_count_per100|v}}, {{confirm_cell/M3_rho0.95/dA2/guarded_mpc_e1/deadline_miss_count_per100|v}} and {{confirm_cell/M3_rho0.95/dA2/oracle_mpc/deadline_miss_count_per100|v}} deadlines per 100 participants per event. The oracle still misses many, since the regime is strained and a miss includes any unit still owed. Targeted MPC exceeds the limit by {{confirm_cell/M3_rho0.95/dA2/guarded_mpc_e1/violation_kwh}} kWh per event against {{confirm_cell/M3_rho0.95/dA2/ce_llf/violation_kwh}} kWh for CE-LLF. All entries for the two measures live in the code release.

[[TABLE: confirm]]

- C1, the delay contrast at ρ = 1.15 above 0: development {{confirm_dev/C1|v}}, confirmation {{confirm/C1}}.
- C2, the delay contrast at ρ = 0.95 above 0: development {{confirm_dev/C2|v}} and not detected, confirmation {{confirm/C2}}.
- C3, the share captured by Shared-rate MPC (as in the gate), above 0.5 at δ = 2 and ρ = 0.95: development {{confirm_dev/C3|v}}, confirmation {{confirm/C3}}.
- C4, belief-by-rule interaction below 0 at δ = 2 and ρ = 0.95: development {{confirm_dev/C4|v}}, confirmation {{confirm/C4}}.
- C5, fall of the reliability-blind share from δ = 1 to δ = 4 above 0 at ρ = 1.15: development {{confirm_dev/C5|v}}, confirmation {{confirm/C5}}.

All five were supported. C2 was expected to fail on development evidence. At both limits, the advantage of per-participant learning is greater at 30 to 60 minutes than at 0 to 15 minutes. This contrasts two delay bands, not a trend. At δ = 0, the difference is near zero as a failure re-dispatches inside the slot. For δ ≥ 1 the development gap lacks any pattern as delay increases (Table 1). Neither bottom end meets the 0.5 kWh practical threshold. In development, C4 and C5 were found post hoc and they hold on fresh seeds. C4 compares the step from LLF to MPC under a point belief with the same step under per-participant reliability. Part of it is LLF worsening with the posterior: at the reference cell LLF-POST leaves {{factorial3/M3_rho0.95/dA2/llf_e1}} against {{factorial3/M3_rho0.95/dA2/llf_ce}} for CE-LLF. C4 shows that this LLF threshold rule cannot apply the belief. The evidence does not establish that greedy rules broadly cannot.

The share in C3 fell under its development value and under the 0.80 gate bar, yet sat well above one half. The declared one half bar was easy to clear, so the pass is weak support.

The share dropped with the larger sample: {{g2/ratio/pop_mpc|v}} on the 20-seed trial run, {{g2_full/ratio/pop_mpc|v}} on 100 development seeds and {{confirm/C3|v}} on 200 confirmation seeds. The share counts the planning and shared-rate steps, which the post hoc split below shows give most of the gain at this cell. Intervals are kWh per 100 for C1, C2 and C4, and they are ratios for C3 and C5.

## Post hoc: where the gain lies

We break down the gain of Targeted MPC over CE-LLF along one path of three steps:

- planning, from CE-LLF to CE-MPC
- shared-rate hedging: from CE-MPC to Shared-rate MPC.
- per-participant targeting, shifting from Shared-rate MPC to Targeted MPC

Figure 3 plots the three steps by delay and stress.

[[FIG: fig_layers]]

The order of the steps determines the split. A factorial of belief and rule shows why. The beliefs are certainty-equivalent, one shared failure rate and per-participant reliability. The rules comprise the greedy LLF rule, the next subsection’s greedy expected-value ranker, and the MPC planner, all run on the same seeds.

[[TABLE: factorial]]

Table 3 lists the avoidable residual for each belief and each rule across all delays under the two limits. Figure 4 displays the steps between them at the reference cell.

[[FIG: fig_ladder]]

The factorial gains below use kWh per 100 at ρ = 0.95, with positive values indicating lower R_avoid. Inside the LLF rule, a shared failure rate helps at δ = 1: {{posthoc_runs/factorial/M3_rho0.95/dA1/belief_ce_to_pop_in_llf}}. It costs energy at long delays: {{posthoc_runs/factorial/M3_rho0.95/dA2/belief_ce_to_pop_in_llf}} at δ = 2 and {{posthoc_runs/factorial/M3_rho0.95/dA4/belief_ce_to_pop_in_llf}} at δ = 4. Then adding per-participant reliability changes almost nothing: {{posthoc_runs/factorial/M3_rho0.95/dA2/belief_pop_to_e1_in_llf}} at δ = 2. The rule's thresholds limit the belief's scope to alter its actions.

Both steps help at δ = 2 inside the planner. Per-participant reliability adds {{posthoc_runs/factorial/M3_rho0.95/dA2/belief_pop_to_e1_in_mpc}} and the shared rate adds {{posthoc_runs/factorial/M3_rho0.95/dA2/belief_ce_to_pop_in_mpc}}. The per-participant second step grows to {{posthoc_runs/factorial/M3_rho1.15/dA2/belief_pop_to_e1_in_mpc}} under the tight limit.

Swapping LLF for MPC yields {{posthoc_runs/factorial/M3_rho0.95/dA2/rule_llf_to_mpc_given_ce}} via a certainty-equivalent belief and {{posthoc_runs/factorial/M3_rho0.95/dA2/rule_llf_to_mpc_given_e1}} via per-participant reliability.

The basic per-participant rules lag behind Targeted MPC in the reference cell. Persistence lags by {{posthoc/rules/gate/persistence_minus_candidate}}, the user flag by {{posthoc/rules/gate/user_flag_minus_candidate}} and the reliability-weighted index by {{posthoc/rules/gate/rwdf_e_minus_candidate}}.

Under the tight limit the reliability-blind share of the gain decreases as delay increases. The reliability-blind share is {{posthoc/oblivious_share/M3_rho1.15/dA1/share}} at δ = 1, {{posthoc/oblivious_share/M3_rho1.15/dA2/share}} at δ = 2 and {{posthoc/oblivious_share/M3_rho1.15/dA4/share}} at δ = 4. The share drops as planning and shared-rate hedging yield smaller gains at long delays. For development seeds the targeting gain does not trend with delay. On development seeds the drop between δ = 1 and δ = 4 equals {{share_fall/M3_rho1.15}} under the tight limit. The value at ρ = 0.95 is {{share_fall/M3_rho0.95}}, not detected at this size.

Three additional post hoc runs answer obvious objections. First, the planning step is not merely LLF's known failure. Smoothed LLF hits zero avoidable residual across all {{sllf_exact/n_seeds|i}} exact-base-load seeds. CE-LLF retains a residual on {{sllf_exact/ce_llf_nonzero|i}} of them. Yet R_avoid against CE-LLF changes by only {{posthoc_runs/sllf/M3_rho0.95/dA2/sllf_minus_cellf}} at δ = 2 and ρ = 0.95. There, planning still beats smoothed LLF by {{posthoc_runs/sllf/M3_rho0.95/dA2/planning_sllf}}.

How failure risk was spread changed the value of knowing who fails. We fixed the mean stuck probability at 0.14 and changed the split at δ = 2 and ρ = 0.95. At q = 0.88, with 15% of participants, targeting adds {{posthoc_runs/het/split0.15_q0.88/M3_rho0.95/dA2/targeting}}. The learned reliability recovers {{posthoc_runs/het/split0.15_q0.88/M3_rho0.95/dA2/recovery_share}} of the oracle's gain. When half the participants have q = 0.27, targeting adds {{posthoc_runs/het/split0.5_q0.27/M3_rho0.95/dA2/targeting}}. The share that reliability recovers is {{posthoc_runs/het/split0.5_q0.27/M3_rho0.95/dA2/recovery_share}}. We fitted the posterior's prior using the one-third split, meaning the remaining splits also evaluate a mis-specified prior. The split also shifts the share of the gain that one shared failure rate captures. The share equals {{fla/split_share/split0.15_q0.88/M3_rho0.95/dA2/share}} when 15% of participants hold q = 0.88, it stands at {{fla/split_share/split0.333_q0.4/M3_rho0.95/dA2/share}} for the one-third allocation, and it reaches {{fla/split_share/split0.5_q0.27/M3_rho0.95/dA2/share}} when half of participants hold q = 0.27. In the tight limit, the values are {{fla/split_share/split0.15_q0.88/M3_rho1.15/dA2/share}}, {{fla/split_share/split0.333_q0.4/M3_rho1.15/dA2/share}} and {{fla/split_share/split0.5_q0.27/M3_rho1.15/dA2/share}}.

Third, a floor on participants stuck in an earlier event outperforms Shared-rate MPC by {{posthoc_runs/floor_flagged/M3_rho0.95/dA4/net_recovery_gain_vs_best_oblivious}} at δ = 4 and ρ = 0.95 yet curtails {{posthoc_runs/floor_flagged/M3_rho0.95/dA4/event_shortfall|v}} kWh per 100. At δ = 2 the two are not distinguishable: {{posthoc_runs/floor_flagged/M3_rho0.95/dA2/net_recovery_gain_vs_best_oblivious}}. A floor on everyone costs {{posthoc_runs/floor_flagged/M3_rho0.95/dA4/floor_all_event_shortfall|v}} kWh per 100. Across the M = 3 primary cells, the floor on everyone yields a maximum net recovery gain of {{secondary/floor/F0R_M3_dA4_db0_rho1.15_r0.3/net_recovery_gain|v}} kWh per 100 against the best oblivious scheduler.

The flagged floor ran in four cells against Targeted MPC, with δ ∈ {2, 4} at both limits.

It outperforms the alternative only at δ = 4 and ρ = 0.95, with a margin of {{posthoc_runs/floor_flagged/M3_rho0.95/dA4/candidate_minus_floor_flagged}}. At δ = 4 and ρ = 1.15, the two are not distinguishable: {{posthoc_runs/floor_flagged/M3_rho1.15/dA4/candidate_minus_floor_flagged}}. For δ = 2, Targeted MPC performs better: subtracting the floor's R_avoid yields {{posthoc_runs/floor_flagged/M3_rho0.95/dA2/candidate_minus_floor_flagged}}. Because floored participants are never stuck, the floor's R* is not the R* of Targeted MPC.

## Post hoc: a greedy expected-value ranker

A pre-submission review asked if the planner beats the strongest simple greedy rule. The greedy expected-value ranker pulls from the identical posterior that the planners use. In every slot, it orders all owed units by their current likelihood of arrival, includes the planner's guard credit, and loads the feeder cap starting with the highest-ranked items. It does not plan ahead. It matches the guarded planner with a one-slot window, using sorting rather than a linear program. A unit test compares the two decision by decision.

It was tuned on the 50 tuning seeds across 27 margin and guard scale settings, frozen, then run once on the 100 development seeds. The reserved seeds stay closed. The rule holds three beliefs, same as the other rules: a point belief, the shared rate and per-participant reliability. We drafted the reading rule prior to the development run. The claim survives if the ranker's per-participant step is nonpositive at δ ≥ 2 but MPC's is positive. It remains post hoc, because the factorial it extends was itself post hoc.

In the ranker, the per-participant belief lifts the avoidable residual. In the reference cell the move from the shared rate to per-participant reliability is {{posthoc_ranker/M3_rho0.95/dA2/belief_pop_to_e1_in_greedy}}. Inside LLF this step is {{posthoc_ranker/M3_rho0.95/dA2/belief_pop_to_e1_in_llf}} and inside MPC it is {{posthoc_ranker/M3_rho0.95/dA2/belief_pop_to_e1_in_mpc}}. Inside the ranker it is {{posthoc_ranker/M3_rho0.95/dA4/belief_pop_to_e1_in_greedy}} at δ = 4 and ρ = 0.95. In the tight limit it is {{posthoc_ranker/M3_rho1.15/dA2/belief_pop_to_e1_in_greedy}} at δ = 2 and {{posthoc_ranker/M3_rho1.15/dA4/belief_pop_to_e1_in_greedy}} at δ = 4, not detected at this size.

In MPC the step is positive at δ = 2 under both limits and at δ = 4 under the tight limit: {{posthoc_runs/factorial/M3_rho1.15/dA4/belief_pop_to_e1_in_mpc}}. Under the loose limit at δ = 4, it is {{posthoc_runs/factorial/M3_rho0.95/dA4/belief_pop_to_e1_in_mpc}}, not detected at this size.

So the reading rule holds in three out of the four cells. Per-participant reliability helped inside the planner at δ = 2 under both limits. Per-participant reliability hurt or did nothing in LLF with threshold insertion and the greedy expected-value ranker at δ ≥ 2. The shared failure rate acts differently: within the ranker, moving from a point belief to the shared rate adds {{posthoc_ranker/M3_rho0.95/dA2/belief_ce_to_pop_in_greedy}} at the reference cell, while inside MPC it adds {{posthoc_ranker/M3_rho0.95/dA2/belief_ce_to_pop_in_mpc}}. By design, the ranker ignores deadlines past a tie-break, making it one greedy rule rather than all of them.

A diagnostic on the tuning seeds reveals the cause of the ranker's loss. It orders by the current delivery probability and overlooks the deadline except for the urgency tie-break. Per-participant reliability drives participants with a stuck record to the tail of their windows, leaving many short at the deadline. The planner defers them as well yet delivers them before their deadlines.

The ranker comes in behind the planners. At the reference cell the ranker with per-participant reliability leaves {{posthoc_ranker/M3_rho0.95/dA2/greedy_ev_minus_targeted_mpc}} more residual than Targeted MPC and {{posthoc_ranker/M3_rho0.95/dA2/greedy_ev_minus_ce_llf}} more than CE-LLF. At the shared rate, it lags Shared-rate MPC by {{posthoc_ranker/M3_rho0.95/dA2/greedy_ev_pop_minus_shared_rate_mpc}}. At the tight limit the two are not distinguishable: {{fla/ranker_vs_mpc/M3_rho1.15/dA2/greedy_ev_pop_minus_pop_mpc}}. The ranker goes over the limit by {{si/posthoc_ranker/M3_rho0.95/dA2/violation_greedy_ev_minus_ce_llf_kwh}} kWh per event more than CE-LLF.

## Post hoc: review checks on development rows

These checks use the development rows. They ran no policy and opened no reserved seed. The diagnostic in Section "Why CE-LLF improves as confirmation slows" is the exception, as it ran CE-LLF and CE-MPC on the tuning seeds.

### The delay contrast with one fixed comparator

The frozen comparator depends on delay: CE-LLF at δ = 0 and Shared-rate MPC at δ ≥ 1. At every delay, using Shared-rate MPC as the comparator, the delay contrast is {{e1_fixed/M3_rho0.95/contrast}} at ρ = 0.95 and {{e1_fixed/M3_rho1.15/contrast}} at ρ = 1.15. Using the frozen comparator, they stood at {{e1/primary/M3_rho0.95/contrast}} and {{e1/primary/M3_rho1.15/contrast}}.

The δ = 0 term is the only one that differs. The gap to Shared-rate MPC is {{e1_fixed/M3_rho0.95/gap0}} at ρ = 0.95, while the gap to CE-LLF is {{e1/primary/M3_rho0.95/gap_dA0}}. For M = 0, the fixed-comparator contrast is {{e1_fixed/M0_rho0.95/contrast|v}} under the loose limit and {{e1_fixed/M0_rho1.15/contrast|v}} under the tight limit, as Targeted MPC matches Shared-rate MPC without prior events. With either comparator, the contrast remains above the practical threshold under the tight limit. At the loose limit, the result remains not detected at this size.

### The violation exchange rate

The discounted gains above treat every kWh over the realized limit as a single kWh undelivered. We changed that rate at the reference cell. Counting 0, 1, 2 or 4 kWh undelivered for each kWh above the limit, the advantage of Targeted MPC versus CE-LLF is {{exchange/M3_rho0.95/dA2/x0/total}}, {{exchange/M3_rho0.95/dA2/x0.25/total}}, {{exchange/M3_rho0.95/dA2/x0.5/total}} and {{exchange/M3_rho0.95/dA2/x1/total}}. Targeted MPC leads Shared-rate MPC by {{exchange/M3_rho0.95/dA2/x0/targeting}}, {{exchange/M3_rho0.95/dA2/x0.25/targeting}}, {{exchange/M3_rho0.95/dA2/x0.5/targeting}} and {{exchange/M3_rho0.95/dA2/x1/targeting}}.

The advantage over the greedy rule remains above zero for all rates. This size shows no detected lead over Shared-rate MPC once each kWh above the limit costs 4 kWh.

### Why CE-LLF improves as confirmation slows

CE-LLF's avoidable residual drops as the delay increases: {{cell/F0R_M3_dA1_db0_rho0.95_r0.3/ce_llf/R_avoid_kwh_per100}} at δ = 1, {{cell/F0R_M3_dA2_db0_rho0.95_r0.3/ce_llf/R_avoid_kwh_per100}} at δ = 2 and {{cell/F0R_M3_dA4_db0_rho0.95_r0.3/ce_llf/R_avoid_kwh_per100}} at δ = 4. Delay alters only the operator's view. For every one of the {{cellf_delay/M3_rho0.95/same_availability|i}} seeds, the realized availability and the minimum residual R* match at δ = 1 and δ = 4.

The drop equals additional energy delivered. From δ = 1 to δ = 4, CE-LLF delivers {{cellf_delay/M3_rho0.95/ce_llf_delivered_rise}} kWh per 100 more under the loose limit and {{cellf_delay/M3_rho1.15/ce_llf_delivered_rise}} under the tight limit, while CE-MPC falls less, by {{cellf_delay/M3_rho0.95/ce_mpc_R_avoid_fall}}. A post hoc diagnostic on the 50 tuning seeds follows the fall. {{diag_cellf/M3_rho0.95/ce_llf/dA1/R_avoid|v}} at δ = 1 and {{diag_cellf/M3_rho0.95/ce_llf/dA4/R_avoid|v}} at δ = 4 reproduce the fall. CE-LLF transmits identical energy at both delays. At δ = 4, the energy sent to participants stuck in that slot shifts by {{diag_cellf/M3_rho0.95/ce_llf/dA4_minus_dA1/to_stuck}} kWh per 100, while delivered energy shifts by {{diag_cellf/M3_rho0.95/ce_llf/dA4_minus_dA1/delivered}}. Retries explain the drop. A participant whose earlier setpoint in the event had already failed sees its setpoints change by {{diag_cellf/M3_rho0.95/ce_llf/dA4_minus_dA1/retry_stuck}}. It exceeds the total change, so initial setpoints to stuck participants climb a bit. Because laxity was not logged, the following is our reading of these counts. Given a one-slot delay, CE-LLF observes the failure, the participant's laxity shrinks, and LLF transmits to it again while it remains stuck. At a four-slot delay the failure has not yet appeared, so the cap goes to participants who can draw it. Retries change by {{diag_cellf/M3_rho1.15/ce_llf/dA4_minus_dA1/retry_stuck}} under the tight limit, matching the pattern. CE-MPC has the same effect, but smaller: its retries change by {{diag_cellf/M3_rho0.95/mpc_ce/dA4_minus_dA1/retry_stuck}}. CE-LLF anchors the headline share, so we also calculate the share using CE-MPC as the base. The share is {{fla/cempc_share/M3_rho0.95/dA2/share}} at the reference cell and {{fla/cempc_share/M3_rho1.15/dA2/share}} under the tight limit.

## Secondary endpoints

Replacing LLF with MPC causes most of the decrease in deadline misses. For δ = 2 and ρ = 0.95, planning eliminates {{layers/M3_rho0.95/dA2/deadline_misses/planning}} deadline misses for every 100 participants in each event. Targeting removes {{layers/M3_rho0.95/dA2/deadline_misses/targeting}}. Shared-rate hedging shifts misses by {{layers/M3_rho0.95/dA2/deadline_misses/hedging}}: it gives more energy but scatters it.

Targeted MPC exceeds the limit by {{si/cell/F0R_M3_dA2_db0_rho0.95_r0.3/guarded_mpc_e1/violation_kwh}} kWh per event in the reference cell, while CE-LLF exceeds it by {{si/cell/F0R_M3_dA2_db0_rho0.95_r0.3/ce_llf/violation_kwh}} kWh, a paired difference of {{si/violation/gate/candidate_minus_ce_llf}} kWh. These feeder totals cover N = 30 participants. The tuning objective disregarded violations, so we tally every kWh exceeding the realized limit as a single kWh undelivered. It scales by 100/N in kWh per 100.

The gain over CE-LLF then drops from {{layers/M3_rho0.95/dA2/total}} to {{posthoc/discounted/dev/M3_rho0.95/dA2/total}} and the lead over Shared-rate MPC from {{layers/M3_rho0.95/dA2/targeting}} to {{posthoc/discounted/dev/M3_rho0.95/dA2/targeting}}. The tight limit gives a discounted lead of {{posthoc/discounted/dev/M3_rho1.15/dA2/targeting}}. For a descriptive check on the confirmation seeds, the discounted gain is {{posthoc/discounted/confirm/M3_rho0.95/dA2/total}} and the lead is {{posthoc/discounted/confirm/M3_rho0.95/dA2/targeting}}.

Shared-rate MPC falls further behind as stuck participants remain stuck. With δ = 2 and ρ = 0.95, the value is {{secondary/r_sweep/r0/gap}} without return, {{secondary/r_sweep/r0.3/gap}} at r = 0.3, and {{secondary/r_sweep/r1/gap}} at r = 1. With just base-load lag (δ = 0, δ_b = 2) the gap to CE-LLF is {{secondary/lag_split/gap}}, so CE-LLF performs better. No positive margin was selected, so the cell shows no margin benefit.

## Theory tracking and controls

For the validation family, {{e3/summary/n_pass|i}} of the {{e3/summary/n_points|i}} measured points fall within their simultaneous 95% intervals around Propositions 1 and 3 (Figure 5). Most points sit below the predicted values. Appendix A.5 contains the interval rule change and a conditioned check that accounts for most of the shift.

Two negative controls pass exactly: with a certainty-equivalent posterior Targeted MPC reproduces CE-MPC action for action and at M = 0 it matches Shared-rate MPC. The two zero-residual controls and the homogeneous-failure control failed, even though the plan required every control to pass first. One cell in the homogeneous control showed Targeted MPC slightly worse (Appendix A.2).

In the reference cell at N = 300, Targeted MPC uses {{scale/SCALE_M3_dA2_db0_rho0.95_r0.3/guarded_mpc_e1/cpu_ms_mean|v}} ms of CPU per decision. CE-LLF uses {{scale/SCALE_M3_dA2_db0_rho0.95_r0.3/ce_llf/cpu_ms_mean|v}} ms. The run manifest lists four worker processes, yet it omits the processor model and thread settings, leaving the timing hardware unspecified. For those 20 seeds the R_avoid ranking stands: Targeted MPC {{scale/SCALE_M3_dA2_db0_rho0.95_r0.3/guarded_mpc_e1/R_avoid_kwh_per100}}, Shared-rate MPC {{scale/SCALE_M3_dA2_db0_rho0.95_r0.3/pop_mpc/R_avoid_kwh_per100}} and CE-LLF {{scale/SCALE_M3_dA2_db0_rho0.95_r0.3/ce_llf/R_avoid_kwh_per100}}. At N = 300, one shared failure rate captures a share of the gain of {{fla/scale_share/M3_rho0.95/dA2/share}}.

# From a synthetic benchmark to a utility pilot

## Why a synthetic benchmark

Three needs drove the synthetic design. First, control. The benchmark determines who is unreliable, the frequency of their failures, and the timing of delivery confirmation. Then each factor can shift in isolation. Every delay uses the same realized availability, so a delay effect stays distinct from a change in failures.

Also, a known reference. The clairvoyant reference requires the realized availability of every participant in every slot. Field data do not show it for a participant who was never commanded while stuck.

Third, a genuine check. We locked the analysis script, file hashes, and five tests prior to opening the reserved seeds. We then opened the 200 reserved seeds once. You cannot redraw a field trial on fresh seeds in this way.

## Where the parameters come from

- Failure after a pause. The mean stuck probability of 0.14 is the share of 42 EV models that failed to restart after a 20-minute pause in a laboratory study [brinkel2024]. A 6-hour pause left the share on 21 models at about double its earlier level.
- Failure within a program. A single utility evaluation spotted technical issues or opt-outs in 29% of plugged-in event statuses, from 13% to 41% per event [guidehouse2022]. It could not distinguish the two causes, so it bounds the field failure rate but does not set it.
- Delay. Clouds for the slowest vehicle types refresh every 30 to 60 minutes, and idle vehicles transmit nothing [smartcar2026]. This assigns δ = 2 and δ = 4. Fast charger telemetry gives δ = 0 and a 15-minute cloud refresh gives δ = 1.
- We did not source these values. We select the risk split, placing one third of participants at 0.40 and the others at 0.01, the return probability r, the obligations, rates, windows, the feeder limit, and the base-load forecast error. A post hoc sweep of the split reveals the extent to which the targeting gain relies on it.

## What a utility pilot must confirm

A utility pilot would swap the synthetic family for logged events. It requires four items:

- Recorded setpoints and timestamped delivery confirmations for each participant and slot, revealing the failures and delay distribution
- A failure history per participant across several events, at least three, tests whether failures persist across events.
- The base load during recovery and the feeder or program limit set the stress.
- A metric of the principal finding, specified beforehand.

The measure is the share in C3 computed on the utility pilot. It divides the gain of Shared-rate MPC over the current dispatch rule by the gain of Targeted MPC over the same rule. A utility pilot would execute the three schedulers in randomized events or run the logs through the simulator.

The share of {{confirm/C3|v}} is confirmed when the utility pilot's interval sits above one half. The share is refuted if the utility pilot's interval lies below one half, which means learning who fails carries most of the gain. Two additional checks account for that outcome. If failure counts per participant vary beyond what a single common rate permits, per-participant reliability has greater value. If a participant's failures do not repeat across events, per-participant reliability is worth less. This paper lacks utility-pilot data.

# Discussion

## Limitations

- The recovery family is synthetic. A lab study gives only the mean failure rate, not data from households after real events. We set the split between the share and the rate of failure-prone participants. It shifts the targeting gain from {{posthoc_runs/het/split0.5_q0.27/M3_rho0.95/dA2/targeting}} to {{posthoc_runs/het/split0.15_q0.88/M3_rho0.95/dA2/targeting}} at the reference cell. The lab study lists failure by vehicle model, meaning an operator can learn a participant's class via make and model at enrollment. That would favor the concentrated split and a class-aware rule.
- CE-LLF, the base of the headline share, leaves less avoidable residual as delay grows ({{cell/F0R_M3_dA1_db0_rho0.95_r0.3/ce_llf/R_avoid_kwh_per100|v}} at δ = 1, {{cell/F0R_M3_dA4_db0_rho0.95_r0.3/ce_llf/R_avoid_kwh_per100|v}} at δ = 4). A post hoc diagnostic on 50 tuning seeds links this to retries sent to participants who are still stuck. Using CE-MPC as the base, the share is {{fla/cempc_share/M3_rho0.95/dA2/share|v}} at the reference cell and {{fla/cempc_share/M3_rho1.15/dA2/share|v}} under the tight limit (Section "Why CE-LLF improves as confirmation slows").
- Delay is a channel label from documented API behavior, not measured latency. Real refreshes produce delays ranging from zero to their period, whereas we set δ.
- Five confirmatory tests, the descriptive violation-discounted check, and the descriptive confirmation means (Table 2 with its deadline misses and limit excess) aside, all numbers derive from development seeds. A post hoc diagnostic on 50 tuning seeds is the one exception. The confirmation drew on the same synthetic family, so it verifies the development results, not their realism. We did not run the conservative-comparator analyses for the delay contrast on reserved seeds.
- Probes ran on development seeds and a guard trial run on unlisted seeds, yet no tuned setting was selected for either (Appendix A.3).
- The tuning objective disregarded violations, so it never picked margins. The violation-discounted benefits, the rate-of-exchange scan, the decompositions and the shares are post hoc.
- Our correctability split was flawed as an endpoint, so we cannot locate the gain within the window.
- With a load-only limit, overbooking setpoints can match the gain of Targeted MPC in the two-slot example. We examine only setpoint-cap semantics. A single aggregate limit applies, lacking phases and power flow.
- The scale run spans 20 seeds with N = 300 across a few cells. No one recorded the timing hardware.

## Threats to validity

### Internal validity

Tuning selected the settings for every family along with the strongest oblivious comparator across 50 tuning seeds. The delay contrast comparator thus changes with delay. The fixed-comparator check reveals how much that matters. Development results prompted the selection of several analyses: the decompositions, the shares, added runs, the ranker and the exchange-rate sweep. No multiplicity correction applied to their intervals. The run manifest records the ranker's frozen settings file was not committed ahead of its development run. The build used development seeds and a unit test saw the validation seeds before the interval rule changed (Appendix A.3). Three control rules did not pass (Appendix A.2).

### External validity

Every result draws from a single synthetic family of 30 participants under one aggregate limit. Actual feeders include multiple phases, voltage constraints, and numerous extra participants. Vehicle-model lab tests yield the failure rate, rather than enrolled households. Each run holds delays steady, but real channels vary them. We assume failure classes persist across events, but no field data here verifies that.

### Construct validity

The main endpoint compares energy with a clairvoyant reference that observes realized headroom, allowing it to be negative. It tallies energy, rather than the energy value for any driver when they leave. Violations fall outside the endpoint and enter solely via the discounted gains. The delay names a channel; it is not an observed latency. The correctability split failed to capture its intended target (Appendix A.1).

## What would change the conclusion

Any one of these would change our conclusion:

- Field data in which one shared failure rate fits poorly would make per-participant reliability worth more
- rates of failure that fail to carry over between events, reducing its value
- telemetry that shows delivery inside one slot on most channels

# Conclusions

If delivery confirms late, an operator restoring charging energy after a demand-response event must hedge failed setpoints ahead of time. A synthetic benchmark with a 30-minute delay and a loose limit shows that planning with one shared failure rate captured {{confirm/C3}} of the gain from a planner that learns per-participant reliability. A tight limit saw that share drop from a 15-minute to a 60-minute delay. Knowing which participants fail mattered more for delays of 30 to 60 minutes than for 0 to 15 minutes. It helped inside the planner and not inside two greedy rules. A utility pilot logging setpoints, confirmations, and failure histories can directly test the share.

# Data and code

All data are synthetic. The released code generates the data from the seeds listed in the release. No customer record or personal record is used. The code and every result file are in the public repository <https://github.com/ratnavarma/paperE-benchmark>, release v1.0 [paperE2026data]. The build that fills every number in this paper is in the same public repository. AI-based assistants helped write the simulation and analysis code. The author reviewed and tested the code.


# Appendix A. Protocol audit trail

This appendix notes three breaks from the pre-declared plan and two items of protocol history. The main text refers to the correctability split, the failed control rules, the seed use in the build, the trial-run gate and theory tracking.

## A.1 The correctability split (E2): the two readings

The correctability split breaks R_avoid into uncorrectable and correctable pieces. The shortfall that traces to setpoints Proposition 2 rules out of correction is uncorrectable. A portion of it may arise from the shared cap regardless, giving the uncorrectable part two estimates. The first reading takes the traced shortfall. The second takes the cap's coupling shortfall away from it. Each reading sums the two parts to R_avoid. The split predicts that the Targeted MPC gain falls within the uncorrectable part in both readings.

In the first reading with ρ = 0.95, the contrast measures {{e2/M3_rho0.95/contrast/readingA/gain_uncorr}} for the uncorrectable part and {{e2/M3_rho0.95/contrast/readingA/gain_corr}} for the correctable part. Yet at δ = 2, both limits place the gain in the correctable part: {{e2/M3_rho0.95/dA2/readingA/gain_corr}} at ρ = 0.95 and {{e2/M3_rho1.15/dA2/readingA/gain_corr}} at ρ = 1.15. The second reading sets every scheduler in contested cells to zero, since its coupling term overwhelms the traced shortfall. The rule demanded both readings, and our endpoint definition was flawed.

## A.2 The three control rules that failed

Both zero-residual controls failed as our plan left base-load noise in. Exact base load lets every planning scheduler reach zero on all 50 seeds of the control. Greedy rules fail to reach zero, consistent with LLF failing feasible cases under a shared limit [chen2021sllf].

The homogeneous-failure control missed the interval-width target at 50 and at 250 seeds. One cell in the band indicated Targeted MPC was slightly worse, and its interval excluded zero. docs/NC_REPORT.md in the code release holds the full control report.

## A.3 Seed use during the build

While building, tests and probes applied policies to development seeds 61000 to 61099 and assessed rough performance there. A unit test matched validation residuals to theory on the validation seeds. A trial run on seeds 60050 to 60059 informed the Targeted MPC guard. No tuned setting came from development seeds. The code release logs the seed ranges and their uses in docs/SEED_LEDGER.md.

## A.4 The trial-run gate

The plan placed a gate on a 20-seed trial run at the reference cell. A shared-rate or persistence rule reaching 0.80 of the gain of Targeted MPC over CE-LLF would make that share the headline finding. The gate passed its criterion. At full size, Shared-rate MPC got {{g2_full/ratio/pop_mpc}} of the gain of Targeted MPC over CE-LLF, exceeding 0.80 in the point estimate, though not in the interval. Persistence hit {{g2_full/ratio/persistence}}. A negative share indicates persistence retained more avoidable residual than CE-LLF. In the 20-seed trial run, the share stood at {{g2/ratio/pop_mpc}}, while the delay contrast measured {{g2/e1_stat}}, with its top edge matching the 0.5 threshold.

## A.5 Theory tracking: interval rule and conditioned check

The plan's literal rule applied pointwise intervals, and {{e3/summary/n_pointwise_misses|i}} points miss under them. We switched to simultaneous intervals ahead of the development run.

That move came after a unit test had compared residuals with theory on these seeds. Most points fall below the predicted value.

{{e3/prop3_shortfall/n_below|i}} of the {{e3/prop3_shortfall/n_points|i}} Proposition 3 points that have a nonzero prediction sit below it. {{e3/prop3_shortfall/n_above_third|i}} miss the prediction by over one third. {{e3/prop3_shortfall/max_rel|v}} is the largest relative shortfall, with a predicted value of {{si/e3/prop3_shortfall/max_rel_predicted_wh|v}} Wh and a measured value of {{si/e3/prop3_shortfall/max_rel_measured_wh|v}} Wh. The biggest absolute drop equals {{si/e3/prop3_shortfall/max_abs_wh|v}} Wh.

A post hoc check accounts for most of the shift. These seeds had fewer unreliable copies stuck than q predicts: {{e3cond/stuck_rate/q0.14|v}} at q = 0.14, {{e3cond/stuck_rate/q0.4|v}} at q = 0.40 and {{e3cond/stuck_rate/q0.5|v}} at q = 0.50. We calculated the expected residual for each policy using the failures seen on each seed and checked the measured residual against it.

Conditioning shifts the mean difference from prediction for the Proposition 1 residuals from {{e3cond/R_pop/mean_uncond_wh|v}} Wh to {{e3cond/R_pop/mean_cond_wh|v}} Wh. For the Proposition 3 gaps, the mean difference shifts from {{e3cond/gap_e1/mean_uncond_wh|v}} Wh to {{e3cond/gap_e1/mean_cond_wh|v}} Wh. Of these {{e3cond/gap_e1/n_points|i}} points, {{e3cond/gap_e1/n_below_cond|i}} still sit below and {{e3cond/gap_e1/n_above_cond|i}} above, leaving a smaller shift.

# Appendix B. Proofs

Instance I1 and the statements of Propositions 1 to 3 are in the Theory section. The proofs follow.

## B.1 Proposition 1

Under δ ≥ 2 nothing is observed before the horizon ends. So every scheduler is a law over open-loop schedules σ. Serving every D copy in slot 1 is without loss for the bound. Leaving one out loses a unit for sure, while a hedge saves at most q. Then slot 1 holds K spare units.

Slot 0 has cap for all 2K twins. Omitting a twin there only raises its loss. So take every twin commanded in slot 0.

Let h_k ∈ {0, 1, 2} be the slot-1 setpoints on pair k, with Σ_k h_k ≤ K. A pair with both twins hedged loses nothing. A pair with one twin hedged loses q/2 in expectation over the class draw. A pair with no hedge loses q.

So the expected residual of σ, averaged over class assignments, is q Σ_k (2 − h_k)/2 ≥ q K/2. A scheduler that does not read the class draws σ independently of the classes. Its expected residual is therefore an average of such terms. The worst case is at least the average.

Hedging every unreliable twin attains zero. With spare cap c in place of K, the same count gives the class-blind bound q (2K − c)/2. A class-blind scheduler attains it.

For c ≤ K it hedges one twin in c pairs. For c ≥ K it hedges both twins in c − K pairs and one twin in the rest. The informed residual is q max(0, K − c), which gives the tent.

## B.2 Proposition 2

A setpoint sent in slot t can depend on the outcome of slot s only if that outcome is known at t. That requires s + δ ≤ t. A correcting setpoint must also fall inside the window, so t ≤ d_i − 1.

## B.3 Proposition 3

Per pair, an identified copy hedges its unreliable twin and loses nothing. An unidentified pair is the twin problem of Proposition 1 and loses q/2. Identification has probability f independently across copies, which gives K (q/2)(1 − f).

Given clean histories on both twins, the class is still uniform on the pair and independent of everything the scheduler reads. So Proposition 1 bounds any history-only rule on unidentified pairs.

In the pooled case, hedges are unit items, so greedy by value is optimal. An identified twin fails with probability q. An unidentified twin is worth q (K − I)/(2K − I) ≤ q/2.

With I identified, K − I hedges are left for 2K − I exchangeable twins. Each unidentified unreliable twin is unhedged with probability K/(2K − I). The function g(i) = (K − i)/(2K − i) is concave.

Jensen's inequality over I, binomial with parameters K and f, then gives E[R] ≤ q K (1 − f)/(2 − f), tight as K grows.


# References

- [brinkel2024] N. Brinkel, T. van Wijk, A. Buijze, N. K. Panda, J. Meersmans, P. Markotić et al. Enhancing smart charging in electric vehicles by addressing paused and delayed charging problems. Nature Communications 15(1), article 5089, 2024. doi:10.1038/s41467-024-48477-w
- [chapelle2014] O. Chapelle. Modeling delayed feedback in display advertising. Proceedings of the 20th ACM SIGKDD International Conference on Knowledge Discovery and Data Mining, pp. 1097-1105, 2014. doi:10.1145/2623330.2623634
- [chen2021sllf] N. Chen, C. Kurniawan, Y. Nakahira, L. Chen, S. H. Low. Smoothed least-laxity-first algorithm for electric vehicle charging: online decision and performance analysis with resource augmentation. IEEE Transactions on Smart Grid 13(3), pp. 2209-2217, 2022. doi:10.1109/TSG.2021.3138615
- [ev2gym2024] S. Orfanoudakis, C. Diaz-Londono, Y. E. Yilmaz, P. Palensky, P. P. Vergara. EV2Gym: a flexible V2G simulator for EV smart charging research and benchmarking. IEEE Transactions on Intelligent Transportation Systems 26(2), pp. 2410-2421, 2025. doi:10.1109/TITS.2024.3510945
- [ev2gym2025code] S. Orfanoudakis et al. EV2Gym, release 2.0.0 (software). GitHub repository, https://github.com/StavrosOrf/EV2Gym, released October 2025.
- [gan2013] L. Gan, U. Topcu, S. H. Low. Optimal decentralized protocol for electric vehicle charging. IEEE Transactions on Power Systems 28(2), pp. 940-951, 2013. doi:10.1109/TPWRS.2012.2210288
- [kalathil2015] D. Kalathil, R. Rajagopal. Online learning for demand response. Proceedings of the 53rd Annual Allerton Conference, pp. 218-222, 2015. doi:10.1109/ALLERTON.2015.7447007
- [katsikopoulos2003] K. V. Katsikopoulos, S. E. Engelbrecht. Markov decision processes with delays and asynchronous cost collection. IEEE Transactions on Automatic Control 48(4), pp. 568-574, 2003. doi:10.1109/TAC.2003.809799
- [taylor2014] J. A. Taylor, J. L. Mathieu. Index policies for demand response. IEEE Transactions on Power Systems 29(3), pp. 1287-1295, 2014. doi:10.1109/TPWRS.2013.2289972
- [guidehouse2022] Guidehouse. National Grid EV and PHEV demand response evaluation, Massachusetts. Study MA21-DR04-E-Res EV, https://ma-eeac.org/wp-content/uploads/MA21-DR04-E-Res-EV-National-Grid-EV-and-PHEV-Demand-Response-Evaluation-Report-2022-07-11-FINAL-wInfographic.pdf, July 2022.
- [hou2009] I.-H. Hou, V. Borkar, P. R. Kumar. A theory of QoS for wireless. IEEE INFOCOM 2009, pp. 486-494, 2009. doi:10.1109/INFCOM.2009.5061954
- [kim2015] K. S. Kim, C.-P. Li, I. Kadota, E. Modiano. Optimal scheduling of real-time traffic in wireless networks with delayed feedback. Proceedings of the 53rd Annual Allerton Conference, pp. 1143-1149, 2015. doi:10.1109/ALLERTON.2015.7447137
- [lee2021acn] Z. J. Lee, G. Lee, T. Lee, C. Jin, R. Lee, Z. Low, D. Chang, C. Ortega, S. H. Low. Adaptive charging networks: a framework for smart electric vehicle charging. IEEE Transactions on Smart Grid 12(5), pp. 4339-4350, 2021. doi:10.1109/TSG.2021.3074437
- [mathieu2013] J. L. Mathieu, S. Koch, D. S. Callaway. State estimation and control of electric loads to manage real-time energy imbalance. IEEE Transactions on Power Systems 28(1), pp. 430-440, 2013. doi:10.1109/TPWRS.2012.2204074
- [ohmconnect2017] OhmConnect. OhmConnect Inc. comments on August 8, 2017 IEPR Commissioner Workshop on Demand Response. California Energy Commission docket 17-IEPR-12, TN 220854, https://efiling.energy.ca.gov/GetDocument.aspx?tn=220854, filed 22 August 2017.
- [puech2024] A. Puech, T. Rigaut, W. Templier, M. Tournoud. Controlling large electric vehicle charging stations via user behavior modeling and stochastic programming. IEEE PES Innovative Smart Grid Technologies Europe (ISGT Europe), pp. 1-6, 2024. doi:10.1109/ISGTEUROPE62998.2024.10863074
- [smartcar2026] Smartcar. Data freshness frequencies. Developer documentation, https://smartcar.com/docs/help/frequencies, accessed 2 November 2026.
- [tucker2022] N. Tucker, M. Alizadeh. A deployable online optimization framework for EV smart charging with real-world test cases. IEEE SmartGridComm, pp. 172-178, 2022. doi:10.1109/SmartGridComm52983.2022.9961029
- [birge1982] J. R. Birge. The value of the stochastic solution in stochastic linear programs with fixed recourse. Mathematical Programming 24, pp. 314-325, 1982. doi:10.1007/BF01585113
- [gelman2013] A. Gelman, J. B. Carlin, H. S. Stern, D. B. Dunson, A. Vehtari, D. B. Rubin. Bayesian Data Analysis, 3rd edition. CRC Press, 2013. doi:10.1201/b16018
- [joulani2013] P. Joulani, A. György, C. Szepesvári. Online learning under delayed feedback. Proceedings of the 30th International Conference on Machine Learning, PMLR 28(3), https://proceedings.mlr.press/v28/joulani13.html, pp. 1453-1461, 2013.
- [callaway2011] D. S. Callaway, I. A. Hiskens. Achieving controllability of electric loads. Proceedings of the IEEE 99(1), pp. 184-199, 2011. doi:10.1109/JPROC.2010.2081652
- [palensky2011] P. Palensky, D. Dietrich. Demand side management: demand response, intelligent energy systems, and smart loads. IEEE Transactions on Industrial Informatics 7(3), pp. 381-388, 2011. doi:10.1109/TII.2011.2158841
- [clementnyns2010] K. Clement-Nyns, E. Haesen, J. Driesen. The impact of charging plug-in hybrid electric vehicles on a residential distribution grid. IEEE Transactions on Power Systems 25(1), pp. 371-380, 2010. doi:10.1109/TPWRS.2009.2036481
- [lee2019acndata] Z. J. Lee, T. Li, S. H. Low. ACN-Data: analysis and applications of an open EV charging dataset. Proceedings of the Tenth ACM International Conference on Future Energy Systems (e-Energy '19), pp. 139-149, 2019. doi:10.1145/3307772.3328313
- [kwac2016] J. Kwac, R. Rajagopal. Data-driven targeting of customers for demand response. IEEE Transactions on Smart Grid 7(5), pp. 2199-2207, 2016. doi:10.1109/TSG.2015.2480841
- [crozier2020] C. Crozier, T. Morstyn, M. McCulloch. The opportunity for smart charging to mitigate the impact of electric vehicles on transmission and distribution systems. Applied Energy 268, article 114973, 2020. doi:10.1016/j.apenergy.2020.114973
- [paperE2026data] {FNU Ratnavarma}. Code, synthetic data and results for scheduling recovery under late delivery confirmation, release v1.0 (dataset). GitHub repository, https://github.com/ratnavarma/paperE-benchmark, 2026.
