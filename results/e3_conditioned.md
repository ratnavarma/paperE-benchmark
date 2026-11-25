# E3 conditioned on the realized stuck draws

**Label:** diagnostic, conditioned on realized stuck draws, added after DEV_REPORT_E. **Status:** development. Not a pre-registered endpoint; E3 itself (DEV_REPORT_E Section 8) is unchanged.

Seeds 61500–61599 (n = 100), K = 8, metric `R_abs_u`. Git 12ad346eadf21e502fff877e80e263b1e47793ad (dirty False). Rows `results/kcopy_dev/rows.jsonl` sha256 `fca8d00cea252fd9f1a7e4c47fac080cbc022f5ad7dc08b7977e9c74b9c157fb`.

Per seed and cell, each policy's expected residual is computed given the realized stuck pattern of the scored event and the realized prior stuck counts (instance generation only, no policy run), over the policy's own tie-break randomness. Measured minus that conditional expectation removes the stuck draws that common random numbers share across cells.

## Realized stuck rate

| q | stuck / A copies | rate | rate − q | z (binomial) | p (two-sided) |
|---:|---:|---:|---:|---:|---:|
| 0.14 | 101 / 800 | 0.1263 | -0.0138 | -1.12 | 0.285 |
| 0.4 | 305 / 800 | 0.3812 | -0.0188 | -1.08 | 0.295 |
| 0.5 | 377 / 800 | 0.4713 | -0.0287 | -1.63 | 0.112 |

Identified share (A copies with a prior stuck outcome) against f = 1 − (1 − q)^M:

| q | M | rate | f | z | two-sided p |
|---:|---:|---:|---:|---:|---:|
| 0.14 | 1 | 0.1338 | 0.1400 | -0.51 | 0.6466 |
| 0.14 | 3 | 0.3625 | 0.3639 | -0.08 | 0.9415 |
| 0.14 | 5 | 0.5250 | 0.5296 | -0.26 | 0.8043 |
| 0.4 | 1 | 0.4012 | 0.4000 | +0.07 | 0.9425 |
| 0.4 | 3 | 0.7900 | 0.7840 | +0.41 | 0.6992 |
| 0.4 | 5 | 0.9113 | 0.9222 | -1.16 | 0.2351 |
| 0.5 | 1 | 0.4875 | 0.5000 | -0.71 | 0.5018 |
| 0.5 | 3 | 0.8750 | 0.8750 | +0.00 | 1.0000 |
| 0.5 | 5 | 0.9513 | 0.9688 | -2.84 | 0.0078 |

The M values share the prior-event draws, so these tests are correlated; the smallest p is reported without adjustment.

## The 312 E3 points, before and after conditioning

Simultaneous level 0.999840 (Bonferroni over 312 points, as E3 primary); pointwise 95%. Student-t intervals on the per-seed series.

| check | points | uncond. in simult. | uncond. in pointwise (t) | uncond. below / above | 0 in simult. (cond.) | 0 in pointwise (cond.) | cond. below / above / exactly 0 | mean meas − uncond | mean meas − cond | combined z (cond.) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| R_pop | 144 | 144 | 140 | 107 / 8 | 144 | 141 | 46 / 50 / 48 | -0.0815 | +0.0002 | +0.05 |
| gap_oracle | 144 | 144 | 140 | 74 / 13 | 144 | 142 | 53 / 43 / 48 | -0.0364 | -0.0024 | -0.53 |
| gap_e1 | 24 | 24 | 21 | 18 / 0 | 24 | 24 | 14 / 4 / 6 | -0.0770 | -0.0224 | -1.88 |
| all | 312 | 312 | 301 | 199 / 21 | 312 | 307 | 113 / 97 / 102 | -0.0603 | -0.0027 | – |

Combined z: sum of the per-point mean residuals over the root sum of their squared standard errors, within one check (one point per cell; given the realization the cells' tie-break streams are independent). Not defined for `all`, where a cell contributes to several checks.

Points whose conditional residual is not identically zero across seeds: 210; 0 inside the pointwise interval for 205 (expected about 199.5); sign below / above 113 / 97.

DEV_REPORT_E pointwise misses (bootstrap) after conditioning:

| point | measured | unconditional | conditional | meas − cond | pointwise 95% | 0 inside |
|---|---:|---:|---:|---:|---|---|
| gap_oracle/pooled/q0.4/c2/M0 | 0.280 | 0.400 | 0.381 | -0.101 | [-0.192, -0.010] | no |
| R_pop/pooled/q0.5/c2/M0 | 3.250 | 3.500 | 3.299 | -0.049 | [-0.163, +0.066] | yes |
| R_pop/pooled/q0.5/c4/M1 | 2.720 | 3.000 | 2.828 | -0.107 | [-0.259, +0.044] | yes |
| R_pop/pooled/q0.5/c4/M3 | 2.740 | 3.000 | 2.828 | -0.087 | [-0.239, +0.064] | yes |
| gap_e1/pooled/q0.5/c8/M1 | 0.480 | 0.705 | 0.612 | -0.132 | [-0.281, +0.016] | yes |
| R_pop/pooled/q0.5/c10/M1 | 1.180 | 1.500 | 1.414 | -0.234 | [-0.380, -0.088] | no |
| gap_oracle/pooled/q0.5/c10/M1 | 1.180 | 1.500 | 1.414 | -0.234 | [-0.380, -0.088] | no |
| R_pop/per_copy/q0.14/c8/M5 | 0.430 | 0.560 | 0.505 | -0.075 | [-0.163, +0.013] | yes |
| gap_oracle/per_copy/q0.14/c8/M5 | 0.430 | 0.560 | 0.505 | -0.075 | [-0.163, +0.013] | yes |
| gap_e1/per_copy/q0.5/c8/M1 | 0.770 | 1.000 | 0.900 | -0.130 | [-0.271, +0.011] | yes |
| gap_e1/per_copy/q0.5/c8/M5 | 1.710 | 1.938 | 1.790 | -0.080 | [-0.248, +0.088] | yes |

## Proposition 3 points (pop − e1, c = K)

| cap | q | M | measured | unconditional | conditional | meas − cond | pointwise 95% |
|---|---:|---:|---:|---:|---:|---:|---|
| pooled | 0.14 | 0 | 0.000 | 0.000 | 0.000 | +0.000 | [+0.000, +0.000] |
| pooled | 0.14 | 1 | 0.010 | 0.045 | 0.010 | -0.000 | [-0.047, +0.046] |
| pooled | 0.14 | 3 | 0.070 | 0.132 | 0.086 | -0.016 | [-0.102, +0.069] |
| pooled | 0.14 | 5 | 0.120 | 0.213 | 0.156 | -0.036 | [-0.109, +0.037] |
| pooled | 0.4 | 0 | 0.000 | 0.000 | 0.000 | +0.000 | [+0.000, +0.000] |
| pooled | 0.4 | 1 | 0.400 | 0.425 | 0.410 | -0.010 | [-0.140, +0.120] |
| pooled | 0.4 | 3 | 0.950 | 1.068 | 1.033 | -0.083 | [-0.246, +0.079] |
| pooled | 0.4 | 5 | 1.310 | 1.390 | 1.302 | +0.008 | [-0.138, +0.154] |
| pooled | 0.5 | 0 | 0.000 | 0.000 | 0.000 | +0.000 | [+0.000, +0.000] |
| pooled | 0.5 | 1 | 0.480 | 0.705 | 0.612 | -0.132 | [-0.281, +0.016] |
| pooled | 0.5 | 3 | 1.520 | 1.592 | 1.474 | +0.046 | [-0.125, +0.216] |
| pooled | 0.5 | 5 | 1.750 | 1.891 | 1.722 | +0.028 | [-0.154, +0.209] |
| per_copy | 0.14 | 0 | 0.000 | 0.000 | 0.000 | +0.000 | [+0.000, +0.000] |
| per_copy | 0.14 | 1 | 0.050 | 0.078 | 0.045 | +0.005 | [-0.025, +0.035] |
| per_copy | 0.14 | 3 | 0.140 | 0.204 | 0.155 | -0.015 | [-0.069, +0.039] |
| per_copy | 0.14 | 5 | 0.210 | 0.297 | 0.235 | -0.025 | [-0.097, +0.047] |
| per_copy | 0.4 | 0 | 0.000 | 0.000 | 0.000 | +0.000 | [+0.000, +0.000] |
| per_copy | 0.4 | 1 | 0.580 | 0.640 | 0.620 | -0.040 | [-0.150, +0.070] |
| per_copy | 0.4 | 3 | 1.170 | 1.254 | 1.205 | -0.035 | [-0.197, +0.127] |
| per_copy | 0.4 | 5 | 1.380 | 1.476 | 1.390 | -0.010 | [-0.182, +0.162] |
| per_copy | 0.5 | 0 | 0.000 | 0.000 | 0.000 | +0.000 | [+0.000, +0.000] |
| per_copy | 0.5 | 1 | 0.770 | 1.000 | 0.900 | -0.130 | [-0.271, +0.011] |
| per_copy | 0.5 | 3 | 1.630 | 1.750 | 1.640 | -0.010 | [-0.188, +0.168] |
| per_copy | 0.5 | 5 | 1.710 | 1.938 | 1.790 | -0.080 | [-0.248, +0.088] |

## Checks of the conditional laws against the rows

Per policy and cell (144 cells each; simultaneous level 0.999884 over 432 policy-cells):

| policy | 0 in simult. | 0 in pointwise | max abs z | seed-cells deterministic given the realization | of which measured ≠ conditional |
|---|---:|---:|---:|---:|---:|
| pop_mpc | 144 / 144 | 141 / 144 | 3.17 | 6144 | 0 |
| oracle_mpc | 144 / 144 | 142 / 144 | 3.31 | 11304 | 0 |
| guarded_mpc_e1 | 144 / 144 | 140 / 144 | 3.12 | 8626 | 0 |

## Closed forms

Conditional closed forms (hypergeometric) against exhaustive enumeration of the uniform hedge subsets (K ≤ 4, every stuck pattern, prior counts 0..3 per A copy, every c, both caps): 502848 comparisons, all exact: True. Averaged over the stuck and history law they recover prop_enum's unconditional closed forms: 312 / 312 exact.

Regenerate: `uv run python scripts/e3_conditioned.py`.
