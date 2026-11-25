# Build spec: shared interfaces for the Track E note

Written October 20, 2026 by the implementation lead from PLAN_PGAI4E_E (Sections 4–6), MECHANISM_E_v2 (Sections 3, 3.9) and FORMULATION_E_v2 (Sections 3.1–3.7). It fixes module boundaries and conventions so separate builders produce code that fits. It adds no claim, endpoint, comparator, cell, seed or gate. Where it settles an ambiguity, the reading is logged in OPEN_QUESTIONS.md.

## 1. Conventions

- Integer units throughout. One unit = 1 kW for one 15-minute slot = 0.25 kWh. Arrays are numpy `int64` for units, `float64` for base load and limits.
- Slots `t = 0 … H−1`. Participant `i` may receive setpoints only for `a_i ≤ t < d_i` (`d_i` exclusive).
- Cap groups. Every participant belongs to one group `group[i] ∈ {0 … G−1}`. Group `g` has limit `L[g, t]` and base load `b[g, t]`. F0-R has `G = 1`. The K-copy family has `G = 1` (pooled cap) or `G = K` (per-copy cap) and zero base load.
- Realized slot headroom for the flow bound: `slot_cap[g, t] = max(0, floor(L[g, t] − b[g, t] + 1e-9))`.
- Setpoint cap (primary semantics): `Σ_{i∈g} x_it ≤ floor(L[g, t] − b̂[g, t] − m)` with `b̂` the default forecast (last observed value, fallback `b_mean[g, t]` when nothing is observed yet) and margin `m ≥ 0`. The simulator enforces it with `m = 0` and raises on any breach. A violation (`ℓ > L`) can then arise only from base-load forecast error.
- Physical load `ℓ[g, t] = b[g, t] + Σ_{i∈g} y_it`. Peak = `max_t Σ_g ℓ[g, t]`.
- Randomness: `numpy.random.SeedSequence`. Each generator component draws from its own named child stream so that changing a cell never shifts another component's draws (common random numbers across cells within a seed). Policy tie-break streams come from `policy_rng(seed, cell_id, policy_name)` and never share a stream with the generator.

## 2. Modules

| Module | Content |
|---|---|
| `papere/instance.py` | `Instance`, `Cell` dataclasses; availability realization with and without floor |
| `papere/generator.py` | `generate_f0r(seed, cell, N=30)`, `generate_kcopy(seed, cell)` |
| `papere/infoset.py` | `InformationSet` (the wrapper), `InformationSetViolation`, `OracleView` |
| `papere/sim.py` | `Policy` protocol, `simulate(...) → Trajectory`, action validation |
| `papere/flow.py` | `FlowProblem`, max flow, own/coupling shortfall, integer leximin, minimum peak |
| `papere/enumerator.py` | brute-force clairvoyant for N ≤ 4, H ≤ 4; proposition enumerator (G1) |
| `papere/ledger.py` | metrics from a `Trajectory` and the clairvoyant result |

`flow.py` and `enumerator.py` take plain arrays (`FlowProblem`) and do not import `instance.py`. `ledger.py` holds the adapter `flow_problem(instance, A)`.

## 3. `Instance` (realized; hidden and public parts)

Public (the policy may see these through the wrapper):

- `N, H, P[N], E[N], a[N], d[N], group[N], L[G, H]`
- `b_mean[G, H]`: expected base load (a parameter of the base-load model)
- `announced[N, H]` in {1, 0, −1 for unknown}
- `prior_A[N, M, H]`: availability in each of the M prior events, fully confirmed; `prior_stuck[N, M]` = stuck after the pause in that event
- `family`, `cell` metadata

Hidden (never reachable through the wrapper):

- `cls[N]`: 1 = pause-intolerant (A in I_K), 0 = tolerant (B in I_K), 2 = D in I_K
- `q[N]`: stuck probability after a pause
- `b[G, H]`: realized base load
- the scored-event availability, produced by `instance.availability(floored: bool[N]) → A[N, H]` from stored uniforms (common random numbers between floored and unfloored versions)

## 4. F0-R generator (PLAN Section 4, FORMULATION Section 5.1)

- `N = 30` (scaling: 300), `H = 24`. `P_i ~ U{1,2,3}`, `E_i ~ U{2…12}`, `a_i ~ U{0,1,2}`, `slack_i ~ U{0…12}`, `d_i = min(H, a_i + ceil(E_i/P_i) + slack_i)`.
- Class: exactly `round(N/3)` intolerant participants placed by a seeded uniform random permutation drawn from its own stream. `q = 0.40` intolerant, `0.01` tolerant.
- Scored-event availability, a two-state chain per participant: state at slot 0 is the post-pause state, stuck with probability `q_i` (never stuck if floored). For `t ≥ 1`: available stays available iff `u_it < 0.98`; stuck returns iff `u_it < r`. `A_it = 1` iff available. The same uniforms `u` serve every `r` and the floored version.
- Prior events: `M_max = 5` events drawn once per seed with the same chain at the cell's `r`, never floored. A cell with `M` uses the first `M`.
- Announcements: `announced = 1` inside the window, `0` outside. Silent failure is not announced.
- Base load: `b_t = B0 (1 + 0.15 s_t) + e_t`, `s_t = t/(H−1)`, `e_t` AR(1) with coefficient 0.7 and stationary standard deviation `0.03 B0`, `B0 = N` units. `b_mean_t = B0 (1 + 0.15 s_t)`.
- Limit: constant `L = (Σ E_i / ρ + Σ_t b_mean_t) / H`.
- Options: `deterministic=True` (NC1: every participant available every slot, no stuck, no drops); `homogeneous_iid=True` (NC3′: every `q_i = 0.14`, availability i.i.d. Bernoulli(0.86) per slot in the scored and prior events).
- `Cell` fields: `M, delta_A, delta_b, rho, r, family`, plus the option flags. Primary, sweep and lag-split cells are listed in `generator.F0R_CELLS` exactly as PLAN Section 4 (22 cells).

## 5. K-copy generator (MECHANISM Section 3.6, PLAN Section 4)

- `K` copies of (A, B, D), `N = 3K`, `H = 2`, `P = E = 1`. A and B windows `[0, 2)`, D window `[1, 2)`. Participant indices are a seeded random permutation of the 3K roles.
- A: stuck at slot 0 with probability `q`, available at slot 1. B and D: always available.
- Prior events: A stuck with probability `q` per event, independently; B and D never.
- Caps: pooled `G = 1`, `L[0] = (2K, K + c)`; per-copy `G = K`, group k = {A_k, B_k, D_k}, `L[k] = (2, 1 + c/K)` with `c/K` an integer. Base load zero.
- `delta_A = 2`, `delta_b = 0`.

## 6. Information set (FORMULATION Section 3.3)

At decision slot `t` the wrapper exposes only:

- the public parameters of Section 3, plus `t, delta_A, delta_b`;
- the policy's own past setpoints `x_is`, `s < t`;
- `y_is` for every participant and every `s ≤ t − delta_A`; `A_is` at the same cutoff but only where a setpoint could have delivered (`x_is > 0` and `r_is > 0`), and −1 (unknown) elsewhere. The simulator applies the mask; the wrapper never holds unmasked `A`. Prior events stay fully confirmed (`prior_A`, `prior_stuck`). (Corrected by the owner side on 2026-10-20; OPEN_QUESTIONS #3.)
- `b_s` for `s ≤ t − 1 − delta_b`;
- helpers derived only from those: confirmed debt `E_i − Σ_{s ≤ t−δ_A} y_is`, `setpoint_cap(g, margin)`.

No generative parameter (class share, `q` values, `r`, 0.98) is exposed. Policies estimate them on tuning seeds. The wrapper object holds copies of permitted data only, as read-only arrays, and has no reference to the `Instance`. Any read past the information set raises `InformationSetViolation`. The oracle-posterior reference receives the true class through a separate `OracleView`, and its output rows are flagged `privileged`.

## 7. Simulator

`simulate(instance, cell, policy, seed) → Trajectory`:

1. `policy.reset(static_view, rng)`; `floored = policy.floor_mask(static_view)` (default none); `A = instance.availability(floored)`.
2. For `t = 0 … H−1`: build `InformationSet` at `t`; `x = policy.act(view)`; validate (integer, `0 ≤ x ≤ P`, zero outside window, setpoint cap with `m = 0`); `y = min(x, r) · A[:, t]`; `r −= y`; record CPU time of `act`.
3. `Trajectory` holds `x, y, A, r` before each slot, `floored`, CPU ms per decision.

## 8. Evaluator (FORMULATION Sections 3.6–3.7, PLAN Section 6)

- Flow network on the realized instance: source → i (`E_i`); i → (g(i), t) (`P_i · A_it` inside the window); (g, t) → T_t (`slot_cap[g, t]`); T_t → sink (unbounded, or the peak cap). `F*`, `R* = Σ E − F*`, `s_own_i = max(0, E_i − Σ_t cap_it)`, `R*_couple = R* − Σ s_own`.
- Leximin: exact lexicographic minimization of the descending-sorted vector `s_i / E_i` over integer maximum flows.
- Minimum peak `P*` among maximum flows: the smallest `Π` such that the network with T_t → sink capacity `floor(Π − Σ_g b[g, t] + 1e-9)` still carries `F*`. The clairvoyant bound row uses that flow.
- Ledger metrics per run: `D`, `R_abs`, `R_avoid = R_abs − R*`, deadline misses (count, kWh), peak (kW), violations (count, kW·slot, longest run), hedge waste `Σ x_it · [r_it = 0]` (kW·slot), CPU ms per decision, event shortfall `2 · Σ floored` units.
- Correctability split (revised 2026-10-20 after the ledger review; OPEN_QUESTIONS rows 7 and 20): `lost_uncorr_i = Σ_{s : s + max(δ_A, 1) ≥ d_i} (min(x_is, r_is) − y_is)` (availability is fixed within a slot, so a participant's own failure is never retried in the same slot, even at δ_A = 0); `u_i = min(max(0, r_i(d_i) − s_own_i), lost_uncorr_i)`. Upper reading `R_uncorr_hi = min(R_avoid, Σ u_i)`; lower reading `R_uncorr_lo = min(R_avoid, max(0, Σ u_i − R*_couple))`, since coupling shortfall cannot be attributed per participant. `R_corr_hi = R_avoid − R_uncorr_lo`, `R_corr_lo = R_avoid − R_uncorr_hi`. E2 reports both readings; the prediction counts as supported only if it holds under both. The raw `Σ u_i` is also kept.
- kWh = units × 0.25. Rates per 100 participants per event = value × 100 / N.
