# Policy spec: step 4 of the Track E build

Written October 20, 2026 by the implementation lead from PLAN_PGAI4E_E Section 5, FORMULATION_E_v2 Sections 6.1–6.3 and MECHANISM_E_v2 Sections 3.5–3.9. It fixes the policy interfaces, the belief layer, every comparator's rule and its 48-point tuning grid. It adds no comparator and drops none. New readings are logged in OPEN_QUESTIONS rows 23 onward.

## 1. Ground rules

- Every policy lives in `src/papere/policies/`, implements `papere.sim.Policy` and reads only `StaticView` and `InformationSet` (the allow-list lint enforces imports). Policies are called once per slot, or several times at δ_A = 0 during re-dispatch (`view.redispatch_round`); `act` must be a pure function of the view plus state set in `reset`.
- Population parameters fitted on tuning seeds 60000–60049 reach policies as plain numbers through the constructor (`PopulationParams`, Section 3.2). Policies never import the generator.
- **Equal inputs.** Every policy gets the same view, the same `PopulationParams` and its own tie-break stream. The per-participant policies differ from the oblivious ones only in using the per-participant posterior (e1: each participant's own prior-event stuck count). The oracle-posterior reference differs from the candidate only in replacing e1's per-participant stuck probability with the true one from `OracleView`; it is flagged `privileged` and labelled reference. Nothing else differs.
- Ties are broken with the policy's `rng` (random permutation or a perturbation of at most 1e-6 per unit of objective), never by index.
- Every action respects windows, `P_i` and each group's setpoint cap `view.setpoint_cap(g, margin=m)` clipped at 0.

## 2. Beliefs over remaining debt (module `policies/beliefs.py`)

At decision slot t, for participant i:

- Confirmed debt `c_i = view.confirmed_debt[i]`.
- Unconfirmed setpoints: slots `U_i = {s : t − δ_A < s < t, x_is > 0}` (empty at δ_A = 0).
- Known complete: some revealed entry `A_conf[i, s] = −1` with `x_is > 0`, or `c_i = 0`. Then the true debt is 0.
- Hidden state `Z_s ∈ {avail, stuck}`, `A_is = 1` iff avail.

A belief returns a `PosteriorState` (`policies/base.py`):

- `tail[i, k] = P(true debt_i ≥ k)` for `k = 1 … Kmax` (`Kmax = max E`);
- `tail_avail[i, k, τ] = P(true debt_i ≥ k and Z_iτ = avail)` for `τ ≥ t`;
- `p_avail[i, τ] = P(Z_iτ = avail)` for `τ ≥ t`;
- `exp_debt[i]`, `p_pos[i] = tail[i, 1]`, `point: bool`.

Beliefs:

| Belief | Debt | Availability |
|---|---|---|
| CE | point mass at `c_i` minus unconfirmed setpoints applied in time order, floored at 0 | 1 inside the window |
| PES | point mass at `c_i` | 1 inside the window |
| PERSIST | unconfirmed setpoints delivered iff the last revealed state of i is available (a base belief, CE or PES, if nothing is revealed yet) | 1 if the last revealed state is available, else 0 |
| HMM(q_i) | exact posterior of the two-state chain (below) | from the same chain |

HMM(q_i): initial `P(Z_i0 = stuck) = q_i` (0 if the policy floored i); transitions `avail → avail` with `p_stay`, `stuck → avail` with `r`. Forward-filter over `s ≤ t − δ_A` (and revealed entries of column t at δ_A = 0) using revealed `A` as exact observations and `−1` as no observation. Then enumerate the `2^|U_i|` state paths over the unconfirmed slots (|U_i| ≤ 4) to get the exact joint law of true debt and `Z_{t−1}`, and propagate the chain forward for `τ ≥ t`. Delivery inside a path follows `y = min(x, r)·A`.

The three HMM instances differ only in `q_i`:

- **e1 (candidate's posterior):** Beta–Bernoulli per participant on its prior-event stuck count: `q_i = (α + k_i)/(α + β + M)`.
- **population:** one rate `q̄` for everyone.
- **oracle:** the true `q_i` from `OracleView`.

`p_stay` and `r` are the same population estimates for all three (Section 3.2). Class enters only through `Z_0`, so HMM(q_i) is the exact Bayes posterior given the estimated parameters.

## 3. Parameters

### 3.1 Tuning-seed fit (`src/papere/fit.py`, outside `policies/`)

From F0-R instances on seeds 60000–60049 (primary cell, M = 5, r = 0.3), using only prior-event data:

- `α, β`: beta-binomial maximum likelihood over per-participant stuck counts out of 5.
- `q̄_tune`: pooled stuck rate.
- transition counts `(n_aa, n_as)` and `(n_ss, n_sa)` over prior chains, as Beta pseudo-counts.

Written to `results/population_params.json` and frozen with the tuning freeze.

### 3.2 Per-instance population update (inside policies, population level only)

`p_stay` and `r` are Beta posterior means: each row of tuning transition counts is rescaled to an effective sample size of 10 (keeping its ratio), then the instance's own pooled prior-chain transition counts (all participants together) are added. The population rate is `q̄ = (α + Σ_i k_i)/(α + β + N·M)`: the same tuning-seed beta prior as e1, updated with the instance's pooled stuck counts. At M = 0 e1 and the population mode therefore use the same `q` for everyone. e1 keeps the tuning-seed `α, β` and adds only participant i's own count. All of this is population-level information, identical for every policy that uses it (OPEN_QUESTIONS rows 26, 36).

## 4. Priority-rule chassis (`policies/rules.py`)

At slot t, over active participants (`a_i ≤ t < d_i`) not known complete:

- believed debt `b_i` from the family's belief;
- effective deadline `d′_i = max(t + 1, d_i − k)`;
- laxity `ℓ_i = (d′_i − t) − ⌈b_i / P_i⌉`;
- order: LLF by `ℓ` ascending, or EDF by `d′` ascending; ties by a fresh random permutation;
- allocation: in order, `x_i = min(P_i, b_i, remaining cap of group(i))` with cap `setpoint_cap(g, m)`.

## 5. Comparators and tuning grids

Every tunable family has exactly 48 configurations. Grid symbols: `O ∈ {EDF, LLF}`, `m ∈ {0, 1, 2}`, `k ∈ {0, 1, 2, 3}`, `W ∈ {2, 4, 8, 24}`, `γ ∈ {0, 0.5, 1, 2}`.

| Class | Family | Rule | Grid (48) |
|---|---|---|---|
| Oblivious | CE-LLF, CE-EDF, PES-LLF | chassis with CE or PES, m = k = 0 | named points of the margin grid, reported as their own rows |
| Oblivious | Best symmetric margin | chassis with belief B | O × B ∈ {CE, PES} × m × k |
| Oblivious | Persistence | chassis with PERSIST; base belief B when nothing is revealed | O × B × m × k |
| Oblivious | Uncorrectable-only pessimism | unconfirmed setpoint at s assumed failed if `s + δ_A ≥ d_i`, else treated by B | O × B × m × k |
| Oblivious | Probe-first | before the chassis, a 1-unit probe to every participant at its release slot and to every participant whose last revealed state is stuck; then the chassis with B on the remaining cap | O × B × m × k |
| Oblivious | Floor during the event | `floor_mask` = everyone; then the chassis with B. Event shortfall reported separately | O × B × m × k |
| Oblivious | MPC-CE, MPC-PES | MPC (Section 6) with the CE or PES belief | W × m × k |
| Oblivious | Population-rate scenario MPC | guarded MPC with HMM(q̄) | W × m × γ |
| Per-participant | User-history flag | chassis; participants stuck in any prior event get PES, the rest B | O × B × m × k |
| Per-participant | RWDF-E | primary key O (laxity or deadline on d′), then the Hou–Kumar / Kim et al. index `c_i · p̂_i · q̂_i^{n_i}` under e1 descending, then random; `p̂_i = p_avail[i, t]`, `q̂_i` = e1 per-setpoint failure probability averaged over `U_i`, `n_i = |U_i|`; units by belief B. Reading of 2026-10-20 (OPEN_QUESTIONS): the index ranks packets that share one deadline in Hou–Kumar, so deadlines order first here | O × B × m × k |
| Per-participant | RWDF-E literal (sensitivity row) | the index as the primary key, O only breaking ties: the plan's literal transplant, reported beside RWDF-E | O × B × m × k |
| Per-participant | LLF-POST | laxity on PES debt with `d′`; ties by `p_pos` descending under e1; skip if `p_pos ≤ θ`; units `#{k : tail[i, k] > θ}` | O × θ ∈ {0, 0.05} × m × k |
| Candidate | Guarded MPC with e1 | guarded MPC with HMM(e1) | W × m × γ |
| Reference | Oracle-posterior guarded MPC | guarded MPC with HMM(true q) | not tuned: uses the candidate's frozen configuration per cell |
| Bound | Clairvoyant | `ledger.bound_row` (max flow, then minimum peak) | none |

## 6. MPC (`policies/mpc.py`)

Receding horizon over slots `t … t + W − 1` (clipped at H), integer plan, first slot executed. Inputs: a `PosteriorState`, per-slot setpoint caps (current slot from `setpoint_cap(g, m)`; later slots from the same last-value forecast), windows with `d′ = d − k` (MPC-CE/PES) or `d` (guarded). Objective: maximize planned expected useful delivery, the k-th unit to i at slot τ worth `tail_avail[i, k, τ]`, plus a small earliness preference and the guard. The guard with width scale γ is the builder's design and must be documented in the module docstring; γ = 0 must remove it. Required properties:

- NC2: guarded MPC with the CE belief and γ = 0 equals MPC-CE (k = 0, same W and m) decision for decision.
- On I_K at δ_A = 2: the population-rate MPC reaches the symmetric optimum `q(K − c/2)` in expectation (all D first, hedges spread at random over twins); the e1 MPC hedges identified A copies first; the oracle reaches `q · max(0, K − c)`.
- Integer, feasible, at most ~20 ms per decision at N = 30 (HiGHS through `scipy.optimize.linprog` or milp is allowed, as is a hand-written min-cost flow).

## 7. Tuning (run after step 5)

For each family and each of the 22 F0-R cells, evaluate all 48 configurations on seeds 60000–60049 and select per cell the configuration with the lowest mean `R_avoid_kwh_per100`, ties by lower mean violation kW·slot, then lower configuration index. The selection is frozen in `results/TUNING_FROZEN.json` and committed before any development seed is run. K-copy runs use each family's default configuration (m = 0, k = 0, γ = 1, W = H, O = LLF, B = PES; θ = 0); scaling runs use the frozen F0-R configuration of the matching cell.
