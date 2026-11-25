# Proofs of the PGAI4E note, draft 7

These are the proofs of the PGAI4E note, draft 7 ("One Failure Rate, and That Is Most of What You Need"). The paper keeps the statements and a short proof sketch for each. The instance, the statements and the proofs below are copied verbatim from draft 6 (paper/note.md at commit 0fd29ee), where they appeared in full.

## The worked instance

Instance I1 has two slots and a cap of 2 units per slot. Every participant accepts at most 1 unit per slot. A and B each owe 1 unit, deliverable in slot 0 or slot 1. D owes 1 unit, deliverable in slot 1 only.

One of A and B is unreliable: it is unavailable in slot 0 with probability q and available in slot 1. The other is always available. The operator cannot tell them apart.

With δ ∈ {0, 1}, EDF, LLF and any capacity-aware MPC deliver everything. With δ = 2 nothing is observed before the horizon ends.

D needs one unit of slot 1, which leaves one unit of spare cap for a hedge. Sent to the unreliable twin it loses nothing. Sent to the other it loses q in expectation.

## Statements

**Proposition 1.** Take K copies of I1 on one feeder with cap 2K per slot and δ ≥ 2. In each pair, the unreliable twin is chosen uniformly at random, independently across pairs and of every observable. Every scheduler whose schedule law is independent of the class draw then has expected residual at least K q/2 units. So does its worst case over class assignments.

A scheduler that knows the classes loses nothing. With spare cap c after the D copies, the gap is q c/2 for c ≤ K. For K ≤ c ≤ 2K it is q (K − c/2).

**Proposition 2.** Under delay δ, consider a failed setpoint to i in slot s. A setpoint can condition on the failure only in slots t with s + δ ≤ t ≤ d_i − 1. So s + δ ≤ d_i − 1 is necessary for correction by re-dispatch.

**Proposition 3.** Suppose classes persist across events. An unreliable copy fails after each pause with probability q, independently across events given its class. A reliable copy never fails. Take M earlier events, each fully confirmed. An unreliable copy has failed at least once in them with probability f = 1 − (1 − q)^M. Such a copy is identified.

Take a scheduler that ranks twins by a failure estimate and hedges in that order. The estimate must be strictly increasing in past failures, equal for equal histories and blind to labels. With a cap per pair, the scheduler recovers exactly the share f of the Proposition 1 gap. No history-only scheduler recovers more.

Under a pooled cap the 2K twins share one cap and one parameter set, so pair membership is not an input. With I copies identified, the scheduler's expected residual is q K (K − I)/(2K − I). Its recovered share is at least f/(2 − f) for every K, with equality in the limit.

At q = 0.40 the per-pair share is 0.40, 0.78 and 0.92 after one, three and five events. The pooled share is at least 0.25, 0.64 and 0.86, the large-K limits. At K = 8 the exact binomial sum runs a little higher. Pooling lowers it because the reliable partners of identified copies stay in the unidentified pool.

## Proofs

*Proposition 1.* Under δ ≥ 2 nothing is observed before the horizon ends. So every scheduler is a law over open-loop schedules σ. Serving every D copy in slot 1 is without loss for the bound, since leaving one out loses a unit for sure while a hedge saves at most q. Then slot 1 holds K spare units.

Slot 0 has cap for all 2K twins. Omitting a twin there only raises its loss. So take every twin commanded in slot 0. Let h_k ∈ {0, 1, 2} be the slot-1 setpoints on pair k, with Σ_k h_k ≤ K. A pair with both twins hedged loses nothing. A pair with one twin hedged loses q/2 in expectation over the class draw. A pair with no hedge loses q.

So the expected residual of σ, averaged over class assignments, is q Σ_k (2 − h_k)/2 ≥ q K/2. A scheduler that does not read the class draws σ independently of the classes. Its expected residual is therefore an average of such terms. The worst case is at least the average.

Hedging every unreliable twin attains zero. With spare cap c in place of K, the same count gives the class-blind bound q (2K − c)/2. A class-blind scheduler attains it. For c ≤ K it hedges one twin in c pairs. For c ≥ K it hedges both twins in c − K pairs and one twin in the rest. The informed residual is q max(0, K − c), which gives the tent.

*Proposition 2.* A setpoint sent in slot t can depend on the outcome of slot s only if that outcome is known at t. That requires s + δ ≤ t. A correcting setpoint must also fall inside the window, so t ≤ d_i − 1.

*Proposition 3.* Per pair, an identified copy hedges its unreliable twin and loses nothing. An unidentified pair is the twin problem of Proposition 1 and loses q/2. Identification has probability f independently across copies, which gives K (q/2)(1 − f). Given clean histories on both twins, the class is still uniform on the pair and independent of everything the scheduler reads. So Proposition 1 bounds any history-only rule on unidentified pairs.

In the pooled case, hedges are unit items, so greedy by value is optimal. An identified twin fails with probability q. An unidentified twin is worth q (K − I)/(2K − I) ≤ q/2.

With I identified, K − I hedges are left for 2K − I exchangeable twins. Each unidentified unreliable twin is unhedged with probability K/(2K − I). The function g(i) = (K − i)/(2K − i) is concave. Jensen's inequality over I ~ Bin(K, f) then gives E[R] ≤ q K (1 − f)/(2 − f), tight as K grows.
