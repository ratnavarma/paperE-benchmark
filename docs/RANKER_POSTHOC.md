# Greedy expected-value hedge ranker (post hoc baseline)

Decided by the author on 2026-11-02 at the request of the journal-style referee (the private review record, Section 3.3 "Missing baselines", Section 3.5 and major comment 6). The referee asked for "a greedy expected-value hedge ranker (per-participant posterior, no planning)". The referee notes that greedy by value is optimal in Proposition 3's instance. The claim "models of silent failure pay off only inside a planner" must survive this ranker or be scoped to LLF.

Label of every number: "descriptive, post hoc, added 2026-11-02 at the referee's request". Development seeds 61000 to 61099 only. The reserved range 500000 to 500999 stays closed. No approval file is created.

## 1. Policy

Module `src/papere/policies/ranker.py`, class `GreedyEV`. At decision slot t, for each active participant i (`a_i <= t < d_i`) and unit k = 1 .. P_i:

- **Value.** The value is what the planner gives the k-th unit to i at slot t, `v(i, k) = tail_avail[i, k, t] = P(debt_i >= k and Z_it = avail)`. This comes from the same `PosteriorState` the MPC family reads. A participant revealed stuck in column t (delta_A = 0 re-dispatch) has `v = 0`. A unit worth less than `VAL_EPS = 1e-12` is not offered, so a participant believed complete is never commanded.
- **Correctability credit (knob gamma).** This is the guard of `mpc.py` evaluated at tau = t. If `t + max(delta_A, 1) < d_i` and `v > 0`, then `u = v + min(1, gamma * p_avail[i, t + dl]) * (tail[i, k] - v)`. gamma = 0 removes it.
- **Score.** `s(i, k) = u(i, k) - URGENT * (d_i - t) + TIE noise + REVEAL * [i revealed available in column t]`. The constants and the tie table are those of `mpc.py` (URGENT = 1e-5, TIE = 1e-6, REVEAL = 1e-3). The tie table is drawn from the policy's rng once per slot and has shape [N, 1, Kmax]. Consecutive units with identical values share one draw, as in the MPC's unit classes. EARLY is 0 at tau = t.
- **Fill.** Units are sorted by score, highest first. A unit is taken if its score is positive, i has room under `P_i`, and its group has room under `max(0, setpoint_cap(g, m))` (margin m is the second knob). Then the next unit is considered. There is no look-ahead, no later slot and no LP.

Per participant the constraints are `P_i` per participant inside a group cap per group. This is a laminar matroid, so the greedy fill is the exact optimum of the one-slot problem. The policy is therefore the guarded MPC with horizon W = 1, solved by sorting instead of HiGHS. A unit test checks the two decision for decision. The MPC's tuning grid has W in {2, 4, 8, 24}, so W = 1 was never a configuration of any family.

The policy sees exactly the information wrapper every policy sees: `StaticView`, `InformationSet` and the frozen `PopulationParams`. It has its own tie-break stream from the simulator (the common per (seed, cell) stream).

Variants (three families, `RANKER_FAMILIES` in `ranker.py`; the 17-family catalog and `posthoc.py` are untouched):

| Family | Belief | Kind | Grid |
|---|---|---|---|
| `greedy_ev` | HMM e1, the same per-participant posterior as Targeted MPC (`guarded_mpc_e1`) | per_participant | m in {0, 1, 2} x gamma in {0, 0.5, 1, 2} = 12 |
| `greedy_ev_pop` | HMM population, the same pooled posterior as Shared-rate MPC (`pop_mpc`) | oblivious | m x gamma = 12 |
| `greedy_ev_ce` | CE point belief (certainty equivalent), as CE-LLF and CE-MPC | oblivious | m in {0, 1, 2} = 3 (gamma has no effect on a point belief with availability 1) |

Under CE every owed unit is worth 1, so `greedy_ev_ce` serves units in earliest-deadline order (URGENT breaks the ties). It is close to CE-EDF and is included as the CE level of the rule factor.

## 2. Tuning

- Seeds 60000 to 60049 (the tuning seeds), all 22 F0-R cells, every configuration of the three grids. That is 27 configurations in total, under the 48 per family that every other family had.
- Selection per cell is the runner's rule: lowest mean R_avoid_kwh_per100, ties by lower mean violation_kwslot, then lower configuration index.
- Rows: `results/tuning_posthoc_ranker/rows.jsonl`. Frozen selection: `results/TUNING_FROZEN_posthoc_ranker.json`, written by `papere.runner.freeze` with `frozen_path` set and only the three ranker families injected. `results/TUNING_FROZEN.json` is not touched.
- Command: `uv run python scripts/run_posthoc_ranker.py tune`, then `... freeze`.

## 3. Runs

- Seeds 61000 to 61099. Cells: M = 3, delta_A in {0, 1, 2, 4}, rho in {0.95, 1.15}, r = 0.3, delta_b = 0. These are the cells of Table 1 and of the belief-by-rule factorial in `results/posthoc_g3_runs.json`.
- Policies: `greedy_ev`, `greedy_ev_pop` and `greedy_ev_ce` at their frozen configuration per cell (from the new frozen file). As a reproduction check, `ce_llf`, `pop_mpc` and `guarded_mpc_e1` are rerun at their frozen configuration from `results/TUNING_FROZEN.json` into the same directory. The analysis checks they equal the rows in `results/f0r_extra/`.
- Rows: `results/f0r_posthoc_ranker/rows.jsonl` (and a `.gz` copy, as in `f0r_extra`). The runner refuses reserved seeds without the approval file. That file is never created.
- The new frozen file is not committed (commits wait for the author). The ranker invocation therefore runs with `allow_dirty`, which the manifest records. Command: `uv run python scripts/run_posthoc_ranker.py run`.

## 4. Analysis

`scripts/posthoc_ranker.py` writes `results/posthoc_ranker.json` in the paper_numbers schema (value, ci_lo, ci_hi, n_seeds, label, unit, statistic, cell_id, source_file). Every interval is a paired percentile bootstrap over the 100 seeds with `papere.analysis.Bootstrap` (n_boot 10000, seed 20261020, 95%). Keys start with `posthoc_ranker/`; the ones below are per cell `M3_rho{rho}/dA{d}`:

- `R_avoid_{greedy_ev, greedy_ev_pop, greedy_ev_ce}`;
- `greedy_ev_minus_ce_llf`, `greedy_ev_minus_targeted_mpc` (guarded_mpc_e1), `greedy_ev_pop_minus_shared_rate_mpc` (pop_mpc): R_avoid differences, first minus second, so negative means the ranker is better;
- `belief_pop_to_e1_in_greedy`, `belief_ce_to_pop_in_greedy` (gain convention as the factorial: positive means the second belief has the lower R_avoid), next to `belief_*_in_llf` and `belief_*_in_mpc` recomputed from `results/f0r_extra/` (checked equal to `results/posthoc_g3_runs.json`);
- `belief_step_greedy_minus_llf`, `belief_step_mpc_minus_greedy`: differences of the pop-to-e1 belief step between rules, jointly resampled;
- rule steps `rule_llf_to_greedy_given_{ce,pop,e1}` and `rule_greedy_to_mpc_given_{ce,pop,e1}`;
- `violation_kwslot_greedy_ev` and `violation_greedy_ev_minus_ce_llf`, and the deadline misses of greedy_ev.

## 5. Reading rule for the claim

The claim is "models of silent failure pay off only inside a planner". It survives the ranker if the belief step pop to e1 inside the greedy ranker is not positive at delta >= 2 (its interval includes 0 or lies below it) while the same step inside MPC is positive. If the step inside the greedy ranker is positive with an interval above 0 at delta >= 2, the claim must be scoped to LLF. This rule is written before the development runs. It is still post hoc, because the factorial it extends was itself post hoc.

## 6. Outcome (2026-11-02, development seeds, post hoc)

- **Frozen setting.** On every Table 1 cell, greedy_ev and greedy_ev_pop chose m = 0. greedy_ev chose gamma = 2 at delta 0 (both rho) and at delta 1, rho 0.95; gamma = 0.5 at delta 1, rho 1.15; and gamma = 0 at delta 2 and 4. greedy_ev_pop chose gamma = 0 everywhere except gamma = 2 at delta 0, rho 0.95. greedy_ev_ce chose m = 0. The full table is in `results/TUNING_FROZEN_posthoc_ranker.json`.
- **Checks.** The rerun comparators equal the `f0r_extra` rows on all 9,600 seed values. The 32 recomputed LLF and MPC factorial steps equal `posthoc_g3_runs.json`. The ranker equals the one-slot MPC decision for decision (tests).
- **Belief step inside the ranker (pop to e1, gain convention).** Reference cell (M = 3, delta = 2, rho = 0.95): -4.69 [-5.87, -3.52]. The same step is 0.06 [0.00, 0.14] inside LLF and 0.71 [0.17, 1.24] inside MPC. At delta = 4, rho = 0.95 it is -3.77 [-4.99, -2.57]. At rho = 1.15 it is -0.13 [-0.97, 0.69] at delta 2 and 0.14 [-0.78, 1.07] at delta 4. The per-participant belief never helps inside the ranker at delta >= 2: it hurts or does nothing.
- **Mechanism (diagnostic on tuning seeds 60000 to 60049, not in the numbers file).** The ranker ranks by expected delivery without deadlines, so the e1 belief starves participants with a stuck history. At the reference cell their first command comes at 85% of their window, against 26% for the others. Each ends with about 5.0 residual units, against 2.2 under the pooled ranker. The planner also defers them (66%), but it still serves them before their deadline.
- **Reading under Section 5.** The claim survives this ranker. Per-participant models of silent failure pay off inside the planner. Inside both greedy rules tested, LLF with threshold insertion and the greedy expected-value ranker, they hurt or do nothing.
