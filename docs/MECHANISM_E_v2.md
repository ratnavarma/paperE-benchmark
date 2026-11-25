# Track E condition 1: the mechanism, worked by hand

Status: hand derivation, October 19, 2026. No code, simulation or seed was used. Written by the research lead for the owner's decision. AI-assisted work, not independent review.

## 1. The condition-1 sentence

Under delayed telemetry a silent setpoint failure can only be corrected by hedging once the delay reaches the participant's remaining window. Under a contested setpoint cap the hedge capacity must go to the participants whose delivery probably failed. Any reliability-oblivious rule, margins included, spreads that capacity blindly and loses at least q/2 units per contested pair of twins. A policy that plans over each participant's posterior of remaining debt loses nothing on the same instance.

The claim holds under three qualifiers, each checkable:

- setpoint-sum cap semantics (Section 5 covers the physical-load case, where overbooking closes the gap);
- no per-participant reliability input to the comparator. A rule that reads a per-participant confirmed failure rate is already in the posterior class and the study runs it as LLF-POST;
- a contested cap: spare cap at least one unit and below the number of uncertain participants (Section 3.6).

The reviewer's candidate was re-dispatch after a silent failure. The derivation below keeps it and sharpens it in two ways:

- The gap is zero while the failure is observed before the participant's last slot. Delay matters only when it pushes discovery past the deadline. Correction then turns into hedging.
- What beats the margin is information about who is likely to fail, not planning as such. A posterior-priority rule matches guarded MPC on this instance. The study must therefore separate information from planning (Section 6).

## 2. Model used in the instance

The model is the v1 model with two clarifications. Both go into FORMULATION_E_v2.

1. **Delivery.** Delivered energy is y_it = min(x_it, r_it) · A_it, where r_it is the true remaining debt. A setpoint sent to an unavailable participant delivers nothing. A setpoint sent to a participant whose debt is already zero also delivers nothing.
2. **Information.** At decision slot t the operator knows A_is for s ≤ t − δ. With δ = 0 it sees current availability and never sends a failing setpoint. With δ = 1 it learns the outcome of slot t at slot t + 1. With δ = 2 it learns it at slot t + 2. Base load gets its own lag δ_b. In this instance the base load is known (δ_b = 0), so the debt channel is isolated.
3. **Setpoint cap (primary semantics).** The operator requires Σ_i x_it ≤ C_t, where C_t is forecast headroom less any margin. This follows ACN practice: pilot signals are summed against the limit because a device may draw its full pilot. Section 5 treats the physical-load semantics, in which only delivered load counts.

One unit is 1 kW held for one 15-minute slot, or 0.25 kWh.

## 3. Instance I1

H = 2 slots, setpoint cap C = 2 units per slot, every rate limit P_i = 1 unit.

| Participant | E_i | Window | Realized availability | Announced |
|---|---:|---|---|---|
| A | 1 | slots 0–1 | slot 0 available with probability 1/2, slot 1 available | available both slots |
| B | 1 | slots 0–1 | available both slots | available both slots |
| D | 1 | slot 1 only | available | available |

A and B look the same to the operator. Same obligation, rate, window and announcement. The only difference is A's failure probability at slot 0, q_A = 1/2, against q_B = 0. A policy with a reliability estimate knows this. A reliability-oblivious policy does not.

### 3.1 Clairvoyant bound

Two realizations, each with probability 1/2.

- ω1, A available at slot 0. Serve A and B at slot 0 and D at slot 1. Flow is 3 = Σ E_i. R* = 0.
- ω0, A unavailable at slot 0. Serve B at slot 0, then A and D at slot 1. Slot 1 carries 2 units, within the cap. Flow is 3. R* = 0.

R* = 0 in both realizations, so every residual below is avoidable residual.

### 3.2 δ = 0

The operator sees A's slot-0 availability before acting.

- ω1: laxities at slot 0 are A 1 and B 1. LLF serves both. Slot 1 serves D. R = 0.
- ω0: A is seen as unavailable. Slot 0 serves B. At slot 1 the laxities are A 0 and D 0. LLF serves both. R = 0.

EDF, LLF and any capacity-aware MPC reach R = 0. Reliability information is worth nothing at δ = 0.

### 3.3 δ = 1

Slot 0: every sensible policy serves A and B, since both are announced available. At slot 1 the operator knows slot 0.

- ω0: it learns that A's setpoint delivered nothing. Believed debt of A is 1, laxity 0. D has laxity 0. Serve A and D, 2 units. R = 0.
- ω1: serve D. R = 0.

The gap is still zero. The failure is observed while A can still be served.

### 3.4 δ = 2

The horizon ends at slot 2, so under δ = 2 the operator learns no availability before the end. Every policy is open loop on I1: a fixed or randomized schedule over A, B and D in slots 0 and 1, with at most 2 units per slot.

Feasible outcomes of a schedule:

- D is served only by a slot-1 setpoint.
- B is served by any setpoint.
- A is served by a slot-1 setpoint, or by a slot-0 setpoint in ω1 only.

Zero residual in both realizations needs D and A at slot 1. Slot 1 is then full, so B must be at slot 0. Two schedules do this: {slot 0: B; slot 1: A, D} and {slot 0: A, B; slot 1: A, D}. Both put the extra slot-1 unit on A, the participant that may have failed.

| Policy | Schedule | R in ω1 | R in ω0 | E[R] in units | E[R] in kWh |
|---|---|---:|---:|---:|---:|
| Posterior-guarded (q_A = 1/2, q_B = 0) | slot 0: A, B; slot 1: D, A | 0 | 0 | 0 | 0 |
| Certainty-equivalent EDF or LLF | slot 0: A, B; slot 1: D | 0 | 1 | 0.5 | 0.125 |
| Pessimistic debt, D first, then A or B by symmetry | slot 0: A, B; slot 1: D and one of A, B | 0 | 1/2 on average | 0.25 | 0.0625 |
| Pessimistic debt, A and B first | slot 0: A, B; slot 1: A, B | 1 (D short) | 1 (D short) | 1 | 0.25 |
| Serve one of A, B at slot 0 by symmetry, the other and D at slot 1 | slot 0: X; slot 1: Y, D | 0 | 1/2 on average | 0.25 | 0.0625 |
| Headroom margin m = 1, so C' = 1 | one unit per slot | ≥ 1 | ≥ 1 | ≥ 1 | ≥ 0.25 |
| Deadline tightening by k slots, any k | as the base rule; 0.5 with a certainty-equivalent base | | | ≥ 0.25 (from Section 3.5) | ≥ 0.0625 |

Posterior-guarded in ω1: A is already complete. Its slot-1 setpoint delivers min(1, 0) · 1 = 0, so no energy is lost and the cap holds. In ω0, A delivers 1 unit at slot 1.

Certainty-equivalent rules assume an unconfirmed setpoint was delivered. They believe A and B are done and serve D alone. In ω0, A misses 1 unit.

With m = 1 only 2 units fit in the two slots against 3 units of obligation. At least 1 unit is short in both realizations.

### 3.5 Why no reliability-oblivious margin can close the gap

Definitions, as corrected in the sign-off (Section 7):

- Let swap(I1) be the instance with the labels of A and B exchanged, so B is the unreliable twin.
- A policy π is reliability-oblivious if its law over schedules on I1 equals its law on swap(I1). It may use announcements, windows, rates, obligations, confirmed outcomes and its own past setpoints. It may not use any input that differs between the two instances.
- EDF, LLF, sLLF, the certainty-equivalent and pessimistic MPCs, every headroom margin m, every deadline tightening k, probe-first, the floor rule and adacharge without a reliability input are reliability-oblivious. That holds with deterministic index tie-breaking too, because the tie-break does not change when only reliability changes.
- A swap-invariant policy, one with P(σ) = P(swap σ) on the fixed instance, is the special case that randomizes ties.

Under δ = 2 no availability is observed before the horizon ends, so every policy is a law over open-loop schedules σ. Write R(σ) for the expected residual of σ on I1.

- If σ serves D at slot 1, slot 1 holds one more unit, so at most one twin is at slot 1. Then R(σ) + R(swap σ) ≥ q_A: of σ and swap σ, the one that leaves the unreliable twin off slot 1 has residual at least q_A.
- If σ does not serve D at slot 1, R(σ) ≥ 1.

For a swap-invariant law P, the reindexing identity gives

E[R] = Σ_σ P(σ) R(σ) = ½ Σ_σ P(σ) [R(σ) + R(swap σ)] ≥ q_A / 2 = 0.25 units.

For a reliability-oblivious policy, the same identity holds across the two instances: R_{I1}(π) + R_{swap I1}(π) ≥ q_A. The average over I1 and swap(I1) is at least 0.25 units. A deterministic oblivious policy has worst case at least q_A = 0.5 units.

The bound is tight. Random tie-breaking between the twins reaches 0.25, either with pessimistic debt and D first or by serving one twin at random at slot 0. The posterior-guarded policy loses 0 on both instances.

### 3.6 Proposition 1 and the operational unit

Instance I_K: H = 2, setpoint cap 2K per slot, K copies each of A, B and D as in I1. A is available at slot 0 with probability 1 − q and at slot 1. Lag δ ≥ 2, base load known, delivery y = min(x, r) · A.

**Proposition 1.** Let π have a law over schedules invariant under every permutation of the 2K twins. Then E[R_π] ≥ K · q / 2 units. The schedule "all twins at slot 0; all D copies and all A copies at slot 1" has R = 0 in every realization, so the gap is exactly K · q / 2.

Proof sketch. Let m be the number of D copies served at slot 1, leaving |S| ≤ 2K − m slot-1 units for twins. Exchangeability gives E|S ∩ A| = |S| / 2. Each A copy outside S has expected residual at least q. So E[R] ≥ (K − m) + q (K − (2K − m) / 2) ≥ K q / 2. Linearity of expectation means failures need not be independent across copies. Pooling the cap across copies changes nothing.

Contested-cap condition. Let c be the spare slot-1 cap after the D copies, so c = K in I_K. A symmetric rule hedges c of 2K twins and covers c/2 A copies in expectation. The posterior rule covers min(c, K). The gap is

gap(c) = q · c / 2 for 0 ≤ c ≤ K and gap(c) = q · (K − c / 2) for K ≤ c ≤ 2K.

The gap is zero with no spare cap and zero with enough cap to hedge every twin. It peaks at c = K. It is not monotone in the cap, so the stress factor ρ must be read as a dose with an interior peak.

Noisy posterior. Let ρ_r be the expected share of A copies among the hedged twins when c = K. Then E[R] = K q (1 − ρ_r). The symmetric rule has ρ_r = 1/2 and the oracle posterior ρ_r = 1. An estimator recovers the share 2ρ_r − 1 of the gap. This is how the e1 and e2 estimators are scored against the oracle row.

Uncertain hedge. If A's slot-1 availability is 1 − q′ rather than 1, the gap becomes K q (1 − q′) / 2. F0 varies q′ through the Markov return probability.

Operational unit. The gap is K q / 2 units on an obligation of 3K units, a share of q / 6, about 8% at q = 1/2. With q = 1/2 and 99 participants (K = 33) it is 8.25 units, or 2.06 kWh per event. Each such kWh is a deadline miss for one named participant, not a pooled shortfall.

### 3.7 Proposition 2: when correction is possible

**Proposition 2 (necessary condition).** Under lag δ, a setpoint to i at slot s whose outcome is a failure can be followed by a setpoint that conditions on that failure only at slots t with s + δ ≤ t ≤ d_i − 1. So s + δ ≤ d_i − 1 is necessary for correction by re-dispatch.

It is not sufficient. Sufficiency also needs i available at some such t, spare cap there at least equal to the lost amount and P_i times the remaining available slots at least the remaining debt. Keeping that spare cap is itself a reserved hedge. The paper states Proposition 2 as necessity only. In I1 the slot-0 setpoint meets the condition for δ ≤ 1 and fails it for δ ≥ 2.

Prediction for the study: the share of setpoints with s + δ ≥ d_i grows with δ and with the share of short-window participants. The gap should grow with δ, saturate once most windows are shorter than δ and vanish when failure probabilities are homogeneous across participants. Homogeneous failure probability is therefore a built-in negative control (NC3).

### 3.8 What the propositions do not yet cover

- The lower bound is proved for the open-loop endpoint, where no outcome arrives before the horizon ends. For 1 ≤ δ < H, histories diverge after the first observed failure and no closed-loop lower bound is proved yet. Until one is, the growth of the gap with δ is an empirical prediction, not a theorem.
- There is no general upper bound for the posterior policy yet. The target statement is E[R_post] ≤ R* + (expected uncertain units that no hedge can cover under the cap).
- Both are theory deliverables T1 and T2 in FORMULATION_E_v2. If T1 cannot be proved, the paper states the open-loop result only and labels the δ slope as measured.

### 3.9 Proposition 3: what history across events recovers

Added October 19, 2026, for PLAN_PGAI4E_E. Hand derivation by the research lead.

Setting. Instance I_K with δ ≥ 2, as in Section 3.6. Two assumptions carry the result. Given class, each event's stuck draw is independent of past events, so every A copy fails with probability q whatever its history. And q_B = 0, so no B copy is ever identified by mistake. Before the scored event, every participant took part in M earlier events with the same pause. Classes persist: an A copy is stuck after each pause with probability q, independently across events and copies. A B copy is never stuck. Earlier events are fully confirmed before the scored event starts.

Estimator. Any estimator whose failure estimate is strictly increasing in the count of past stuck outcomes, is equal for equal histories and uses no index or label input, with ties broken at random. The Beta–Bernoulli estimator e1 qualifies. An A copy with at least one past stuck outcome is identified. That happens with probability f = 1 − (1 − q)^M, independently across copies. A participant never stuck in M events has the same posterior as every other such participant, whatever its class.

Policy. Serve every D copy at slot 1. Hedge identified A copies first. Spread any remaining hedges evenly over the unidentified twins.

Per-copy cap (each copy has its own cap of 2 per slot). An identified copy hedges its A and loses nothing. An unidentified copy is the twin problem of Section 3.5 and loses q/2 in expectation. So

E[R] = K · (q/2) · (1 − f),

and the share of the oblivious gap K · q/2 that history recovers is exactly f. No history-only estimator can recover more under a per-copy cap, since Section 3.5's bound applies to every unidentified pair.

Pooled cap (2K per slot, K spare at slot 1). Let I be the number of identified A copies. The policy hedges those I and spreads the other K − I hedges over the 2K − I unidentified twins: K − I A copies and all K B copies. Each unidentified A copy is hedged with probability (K − I)/(2K − I), so its expected residual is q · K/(2K − I). Then

E[R | I] = q · K · (K − I)/(2K − I).

Hedging identified copies first is optimal within the class of policies whose law is invariant under permutations of twins with equal histories. Each hedge is one unit and each twin needs at most one, so choosing hedges is a unit-weight knapsack and greedy by value is optimal. Hedging an identified A is worth q. Hedging an unidentified twin is worth q · (K − I)/(2K − I) ≤ q/2. Spreading evenly is not required: any K − I distinct unidentified twins give the same expectation by exchangeability. Exactly, with I ~ Bin(K, f),

E[R] = q K Σ_i C(K, i) f^i (1 − f)^(K − i) (K − i)/(2K − i).

The map i ↦ (K − i)/(2K − i) is concave on [0, K], so Jensen's inequality gives E[R] ≤ q K (1 − f)/(2 − f) for every K. The recovered share is therefore at least f/(2 − f) at every K. It equals f at K = 1 and tends to f/(2 − f) as K grows.

The pooled share is lower because the B copies of identified pairs stay in the unidentified pool. Under a per-copy cap, K − I hedges contest 2(K − I) twins. Under a pooled cap, the same K − I hedges contest 2K − I twins. The difference is exactly the I B copies whose pairs were resolved. The pairing is part of the per-copy instance.

| q | M | f | Share recovered, per-copy cap | Share recovered, pooled cap (large K) |
|---:|---:|---:|---:|---:|
| 0.40 | 1 | 0.40 | 0.40 | 0.25 |
| 0.40 | 3 | 0.784 | 0.78 | 0.64 |
| 0.40 | 5 | 0.922 | 0.92 | 0.86 |
| 0.50 | 3 | 0.875 | 0.88 | 0.78 |

At M = 0, f = 0 and the e1 policy is reliability-oblivious, as the private review record found. That is negative control NC4 in PLAN_PGAI4E_E.

## 4. The falsifiers

1. **Margin is enough.** On the development families, the best tuned symmetric rule comes within the minimum effect of interest of the posterior-guarded policy on avoidable residual at every δ, with violations no worse. Its search space is headroom m, deadline tightening k and certainty-equivalent or pessimistic debt, on the same tuning seeds and the same grid size. Then the mechanism does not operate at realistic scale and the paper reduces to "use a margin". The track retires or becomes a short note.
2. **Nothing to target.** If public sessions show near-homogeneous non-delivery across participants, the posterior carries no targeting information and the gap vanishes by Section 3.5. A noisy posterior recovers only the share 2ρ_r − 1 of the gap (Section 3.6), so the AUC threshold is a floor, not a guarantee. The test is a held-out AUC below 0.60 for predicting a shortfall from delayed features, or a between-participant variance not distinguishable from zero. This check runs on ACN-Data before any policy is built and it can kill the track in its first day.
3. **Delay never reaches the window.** If, at realistic telemetry lags, almost no setpoints fall in the s + δ ≥ d_i regime, the mechanism exists but is irrelevant. The descriptive report gives that share per family and per δ.

## 5. Where a margin does work: physical-load semantics

Suppose the limit binds only on delivered load and the operator may overbook setpoints. Overbooking by one unit in I1 sends D, A and B at slot 1. Physical load is 1 from D, plus 1 from A in ω0, plus 0 from B, which is already complete. Load stays within 2 and R = 0. Overbooking copies the posterior-guarded result on I1.

Overbooking fails when hedged participants are not actually complete. Then the extra setpoints draw, load exceeds the limit and violations appear. The posterior-guarded policy can choose that risk. A blind overbooking margin cannot. That is a trade between energy and violations, not a dominance result. FORMULATION_E_v2 therefore makes the setpoint cap the primary semantics. Physical-load semantics with an overbooking margin among the comparators is a declared secondary cell and falsifier 1 is applied to it separately. If overbooking matches the posterior policy there, the paper says so.

## 6. What this means for the design

- The candidate's gain comes from the debt posterior. Planning is one way to use it. The study crosses belief (certainty-equivalent, pessimistic, posterior) with the decision rule (priority rule, MPC), so information and planning are separated.
- The learned component has a natural place. It estimates P(setpoint delivered | delayed history) and so supplies the posterior. It must be trained on delayed labels. It is kept only if it beats the empirical per-participant Markov estimate under the same scheduler.
- The base-load channel stays. A headroom margin is the right tool for base-load lag. The study adds a cell where availability lag and base-load lag differ, so the two channels can be told apart.

## 7. Sign-off record (October 19, 2026)

The owner approved one short pass on the mathematics. Its findings and what changed:

| Finding | Change |
|---|---|
| I1 arithmetic and every table cell correct; the 0.25 bound true and tight | none |
| "Participant-symmetric" mixed swap-invariance with reliability-obliviousness | Section 3.5 now defines reliability-oblivious against swap(I1) and treats swap-invariance as the special case |
| Write the proof as a reindexing identity | done, Section 3.5 |
| Proposition 1 stated with exact assumptions; the shared cap changes nothing; numbers are 8.25 units and 2.06 kWh for 99 participants | Section 3.6 |
| The gap needs a contested cap and is not monotone in the cap | the gap(c) formula and the third qualifier in Section 1 |
| Proposition 2 is necessary only; sufficiency needs a reserved hedge | Section 3.7 |
| Rules with a per-participant delivery-rate input are already the posterior class | qualifier 2 in Section 1 |
| Publishability needs a closed-loop lower bound for 1 ≤ δ < H, a matching upper bound and the gap normalized to obligation | normalized gap q/6 added; T1 and T2 listed in Section 3.8 and FORMULATION_E_v2 |
| Vary the hedge's own availability q′; give the noisy-posterior interpolation | Section 3.6 |
| Confirm delivered-energy telemetry carries the same lag as availability | FORMULATION_E_v2 Section 3.3 states it: y_is and A_is arrive together |

The judgment, paraphrased: correct as stated, but on its own a value-of-information example. With T1, T2 and the normalized gap on realistic q it becomes a clean separation whose assumptions are each checkable.
