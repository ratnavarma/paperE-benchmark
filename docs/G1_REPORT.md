# Gate G1 report, Track E PGAI4E note

Date: October 20, 2026 (target October 24). Written by the implementation lead. All results are development checks on the build itself; no study seed was run. AI-assisted work, reviewed by separate read-only reviewers, not independent human review.

## Verdict

**G1 passes.** Max flow agrees with the exhaustive enumerator on every instance checked with N ≤ 4 and H ≤ 4. The enumerator reproduces Proposition 1, gap(c), the I1 table and Proposition 3 exactly, in rational arithmetic, on I_K for K = 1 to 4. No disagreement was found, so nothing stopped work. F0-R runs may proceed after policies (step 4) and negative controls (step 5).

## What failed or is weaker than it sounds

Nothing failed at the gate. These are the limits of what was checked, and the defects found on the way to it.

- **"Every instance" is a battery, not all instances** (OPEN_QUESTIONS row 9). Checked: every instance with N ≤ 2 and H ≤ 2 in a bounded parameter box (257,712 instances), plus 20,000 seeded random instances with N ≤ 4 and H ≤ 4, P ∈ {1, 2, 3}, E ∈ {1, …, 6}, G ∈ {1, 2, 3}, slot caps 0–4 and non-integer base load. A reviewer added 4,100 instances with N = 5–8 against an independent exact solver, with 0 mismatches.
- **Two symmetry-group mutations leave the proposition values unchanged on I_K.** Letting D copies swap with twins, and giving the per-copy cap all twin permutations, change no value. They are caught only by the test that compares canonical-key orbits against explicitly enumerated group orbits. The groups are therefore pinned by that test, not by the propositions. Proposition 1 and gap(c) also give the same values under the smaller within-pair-swap group, as theory says; only the pooled Proposition 3 checks tell the two groups apart.
- **Some rows are closed form, not enumeration, and are labelled so.** The pooled Proposition 3 share at K = 1000 (12 rows) and the large-K table entries are closed form. Full prior-event sequences are enumerated only when K·M ≤ 8. Above that, stuck-count histories are used; the two agree in all 90 cases where both run.
- **Rounding.** The per-copy share at q = 0.5, M = 3 is exactly 0.875. The table's 0.88 rounds half up.
- **The scored-event independence assumption of Proposition 3 is built into the enumerator**, which reuses one residual table for every history. A reviewer's joint enumeration of M + 1 events (K ≤ 2, M ≤ 2) confirmed it factorises and reproduced the history optimum in all 16 cases.
- **Defects found and fixed before the gate**, each by a read-only review:
  - The wrapper's δ_A = 0 reveal leaked stuck states of uncommanded participants. Replaced by within-slot re-dispatch (OPEN_QUESTIONS row 11; needs owner confirmation).
  - The policy random-number stream exposed the seed and cell, from which a policy could regenerate the instance. A policy could also make wrapper arrays writable, widen its own lag through its static view, and slip actions past validation. All closed; an allow-list lint now guards policy modules.
  - The E2 correctability split counted own-capacity shortfall, already in R*, as uncorrectable. That biased E2 toward the claim (58 of 229 R_uncorr units in a probe). Replaced by a two-reading split (OPEN_QUESTIONS row 7; needs owner confirmation).
- **The K-copy structure check has limited power on stuck rates.** Windows, caps, groups and roles are compared against the enumerator's own definitions and every structural mutant is caught. But the binomial tests on A's stuck rate reliably catch only errors of about 10% relative or more (a 0.92q mutant was caught in 1 of 9 runs, 0.90q in 8 of 9). The E3 Monte Carlo comparison on 61500–61599 is the stronger check on rates. Pooled c is checked at the integer multiples the K = 8 cells rescale to (all of 0…2K for K = 1, 2, 4; {0, 3, 6} at K = 3).
- G1 checks the bound and the theory. It says nothing about any policy. No study result exists yet.

## Part 1: flow code against the enumerator

| Check | Instances | Result |
|---|---:|---|
| F* (own Dinic) = networkx max flow = brute force | 257,712 grid + 20,000 random | equal on all |
| Integer leximin of sorted s_i/E_i = brute-force leximin (exact fractions) | same | equal on all |
| Minimum peak among max flows = brute force | same | equal on all |
| Returned flows feasible, integer, maximal; s_own and R*_couple identities | same | hold on all |
| Fast brute force = naive DFS over every matrix | 2,000 random + grid sample | equal |
| Independent reviewer solver, N = 5–8, G ≤ 3 | 4,100 | 0 mismatches |
| N = 300, H = 24, max flow + leximin + min peak | 1 | 0.87 s |

Mutation testing by the reviewer: every leximin mutant (tie-break removed or reversed, absolute shortfall) and every peak-rounding mutant is caught.

Command: `PAPERE_G1_FULL=1 uv run pytest -q tests/test_flow.py tests/test_enumerator.py` (18 passed, 6 min 6 s; log in `logs/g1_flow_full.txt`).

## Part 2: propositions on I_K

Grid: K ∈ {1, 2, 3, 4}, q ∈ {1/2, 2/5, 7/50}, M ∈ {0, 1, 2, 3, 5}; pooled cap at c = 0 … 2K, per-copy cap at c ∈ {0, K, 2K}; Proposition 3 at c = K. Every feasible schedule is enumerated (2^20 at K = 4), delivery y = min(x, r)·A is simulated in every stuck pattern with exact probabilities, and the optimum over symmetric laws is the minimum orbit mean. Closed forms are used only on the comparison side.

| Check | Rows | Holds |
|---|---:|---:|
| Proposition 1: oblivious optimum = K q/2; posterior optimum = 0; hedge-all-A schedule R = 0 in every realization | 72 | 72 |
| gap(c) = q c/2 (c ≤ K), q (K − c/2) (c ≥ K), and both optima separately | 324 | 324 |
| I1 table (MECHANISM 3.4) and Section 3.5 bounds, K = 1, q = 1/2 | 26 | 26 |
| Proposition 3: class optimum = per-copy K(q/2)(1 − f) and pooled exact binomial sum | 210 | 210 |
| Proposition 3: E[R \| I] = qK(K − I)/(2K − I) pooled, q(K − I)/2 per copy, for every history | 1,188 | 1,188 |
| Proposition 3: identified-first law attains the class optimum | 420 | 420 |
| Proposition 3: recovered share = f per copy; ≥ f/(2 − f) pooled; = f at K = 1 | 240 | 240 |
| Proposition 3 at M = 0 equals Proposition 1 (NC4 shape) | 48 | 48 |
| Full sequences = count histories | 90 | 90 |
| Pooled share at K = 1000 within 1e-3 of f/(2 − f) (closed form only) | 12 | 12 |
| MECHANISM 3.9 and PLAN 7 table values | 19 | 19 |
| K-copy generator builds exactly the enumerator's I_K (K ∈ {1, 2, 3, 4, 8}) | 74 | 74 |
| **Total** | **2,723** | **2,723** |

Recovered shares reproduced: at q = 0.40, f = 0.40, 0.784, 0.922 after M = 1, 3, 5; per-copy shares 0.40, 0.78, 0.92; pooled large-K shares 0.25, 0.64, 0.86. At q = 0.50, M = 3: f = 0.875, per-copy 0.88, pooled 0.78.

Mutation testing by the reviewer (14 deliberate bugs, including A stuck at slot 1, caps off by one, f = 1 − q^M, B stuck, orbit mean replaced by minimum, history ignored, identity-only group): every one is caught by the test suite; 12 of 14 also change script rows.

Commands: `uv run pytest -q tests/test_prop_enum.py tests/test_kcopy_structure.py` (209 passed, about 22 s); `uv run python scripts/g1_propositions.py` (about 2 min; writes `results/g1_propositions.json` and `.md`).

## Environment

Python 3.13.16, numpy 2.5.4, scipy 1.18.1, networkx 3.7, managed by uv. Full test suite: 421 passed (72 s). Git commits: proposition results `e9f4014`, K-copy structure `ad7c7ce`, full battery log `2662f7c`.

## Owner decisions still open

- OPEN_QUESTIONS row 11: δ_A = 0 as within-slot re-dispatch of commanded participants only.
- OPEN_QUESTIONS row 7: the two-reading E2 split.
- OPEN_QUESTIONS row 20: the uncorrectable rule s + max(δ_A, 1) ≥ d_i.

None affects G1. All three affect the F0-R study.
