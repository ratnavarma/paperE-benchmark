# G1: exhaustive enumerator vs Propositions 1 and 3, gap(c) and the I1 table

Grid K = [1, 2, 3, 4], q = ['1/2', '2/5', '7/50'], M = [0, 1, 2, 3, 5]. Rows: 2723, holding: 2723. Runtime 130.8 s (per K: {1: 0.0, 2: 0.1, 3: 1.2, 4: 121.9}).

Enumerated values are exact brute force over schedules, realizations and histories; closed forms are from MECHANISM_E_v2 Sections 3.4-3.9. Rows marked 'closed form only' are not enumerated.

| check | K | q | M | c | cap_mode | enumerated | closed_form | relation | holds | note |
|---|---|---|---|---|---|---|---|---|---|---|
| prop1_oblivious_optimum | 1 | 1/2 |  | 1 | pooled | 1/4 | 1/4 | == | True | 17 orbits / 28 schedules |
| prop1_posterior_optimum | 1 | 1/2 |  | 1 | pooled | 0 | 0 | == | True |  |
| prop1_hedge_all_A_max_R_over_realizations | 1 | 1/2 |  | 1 | pooled | 0 | 0 | == | True |  |
| prop1_oblivious_optimum | 1 | 1/2 |  | 1 | per_copy | 1/4 | 1/4 | == | True | 17 orbits / 28 schedules |
| prop1_posterior_optimum | 1 | 1/2 |  | 1 | per_copy | 0 | 0 | == | True |  |
| prop1_hedge_all_A_max_R_over_realizations | 1 | 1/2 |  | 1 | per_copy | 0 | 0 | == | True |  |
| gap_c | 1 | 1/2 |  | 0 | pooled | 0 | 0 | == | True |  |
| gap_c_oblivious_optimum | 1 | 1/2 |  | 0 | pooled | 1/2 | 1/2 | == | True |  |
| gap_c_posterior_optimum | 1 | 1/2 |  | 0 | pooled | 1/2 | 1/2 | == | True |  |
| gap_c | 1 | 1/2 |  | 1 | pooled | 1/4 | 1/4 | == | True |  |
| gap_c_oblivious_optimum | 1 | 1/2 |  | 1 | pooled | 1/4 | 1/4 | == | True |  |
| gap_c_posterior_optimum | 1 | 1/2 |  | 1 | pooled | 0 | 0 | == | True |  |
| gap_c | 1 | 1/2 |  | 2 | pooled | 0 | 0 | == | True |  |
| gap_c_oblivious_optimum | 1 | 1/2 |  | 2 | pooled | 0 | 0 | == | True |  |
| gap_c_posterior_optimum | 1 | 1/2 |  | 2 | pooled | 0 | 0 | == | True |  |
| gap_c | 1 | 1/2 |  | 0 | per_copy | 0 | 0 | == | True |  |
| gap_c_oblivious_optimum | 1 | 1/2 |  | 0 | per_copy | 1/2 | 1/2 | == | True |  |
| gap_c_posterior_optimum | 1 | 1/2 |  | 0 | per_copy | 1/2 | 1/2 | == | True |  |
| gap_c | 1 | 1/2 |  | 1 | per_copy | 1/4 | 1/4 | == | True |  |
| gap_c_oblivious_optimum | 1 | 1/2 |  | 1 | per_copy | 1/4 | 1/4 | == | True |  |
| gap_c_posterior_optimum | 1 | 1/2 |  | 1 | per_copy | 0 | 0 | == | True |  |
| gap_c | 1 | 1/2 |  | 2 | per_copy | 0 | 0 | == | True |  |
| gap_c_oblivious_optimum | 1 | 1/2 |  | 2 | per_copy | 0 | 0 | == | True |  |
| gap_c_posterior_optimum | 1 | 1/2 |  | 2 | per_copy | 0 | 0 | == | True |  |
| prop3_history_optimum | 1 | 1/2 | 0 | 1 | pooled | 1/4 | 1/4 | == | True | histories=count (1) |
| prop3_E[R|I=0] | 1 | 1/2 | 0 | 1 | pooled | 1/4 | 1/4 | == | True | histories=count (1) |
| prop3_every_history_with_I=0 | 1 | 1/2 | 0 | 1 | pooled | 1 | 1 | == | True | histories=count (1); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 1 | 1/2 | 0 | 1 | pooled | 1/4 | 1/4 | == | True | histories=count (1); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 1 | 1/2 | 0 | 1 | pooled | 0 | 0 | == | True | histories=count (1) |
| prop3_share_recovered_vs_f/(2-f) | 1 | 1/2 | 0 | 1 | pooled | 0 | 0 | >= | True | histories=count (1) |
| prop3_share_recovered_K1 | 1 | 1/2 | 0 | 1 | pooled | 0 | 0 | == | True | histories=count (1) |
| prop3_M0_equals_prop1 | 1 | 1/2 | 0 | 1 | pooled | 1/4 | 1/4 | == | True | histories=count (1); closed_form column = enumerated Prop 1 |
| prop3_history_optimum | 1 | 1/2 | 0 | 1 | pooled | 1/4 | 1/4 | == | True | histories=full (1) |
| prop3_E[R|I=0] | 1 | 1/2 | 0 | 1 | pooled | 1/4 | 1/4 | == | True | histories=full (1) |
| prop3_every_history_with_I=0 | 1 | 1/2 | 0 | 1 | pooled | 1 | 1 | == | True | histories=full (1); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 1 | 1/2 | 0 | 1 | pooled | 1/4 | 1/4 | == | True | histories=full (1); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 1 | 1/2 | 0 | 1 | pooled | 0 | 0 | == | True | histories=full (1) |
| prop3_share_recovered_vs_f/(2-f) | 1 | 1/2 | 0 | 1 | pooled | 0 | 0 | >= | True | histories=full (1) |
| prop3_share_recovered_K1 | 1 | 1/2 | 0 | 1 | pooled | 0 | 0 | == | True | histories=full (1) |
| prop3_M0_equals_prop1 | 1 | 1/2 | 0 | 1 | pooled | 1/4 | 1/4 | == | True | histories=full (1); closed_form column = enumerated Prop 1 |
| prop3_full_vs_count_histories | 1 | 1/2 | 0 | 1 | pooled | 1/4 | 1/4 | == | True |  |
| prop3_history_optimum | 1 | 1/2 | 0 | 1 | per_copy | 1/4 | 1/4 | == | True | histories=count (1) |
| prop3_E[R|I=0] | 1 | 1/2 | 0 | 1 | per_copy | 1/4 | 1/4 | == | True | histories=count (1) |
| prop3_every_history_with_I=0 | 1 | 1/2 | 0 | 1 | per_copy | 1 | 1 | == | True | histories=count (1); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 1 | 1/2 | 0 | 1 | per_copy | 1/4 | 1/4 | == | True | histories=count (1); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 1 | 1/2 | 0 | 1 | per_copy | 0 | 0 | == | True | histories=count (1) |
| prop3_share_recovered | 1 | 1/2 | 0 | 1 | per_copy | 0 | 0 | == | True | histories=count (1) |
| prop3_M0_equals_prop1 | 1 | 1/2 | 0 | 1 | per_copy | 1/4 | 1/4 | == | True | histories=count (1); closed_form column = enumerated Prop 1 |
| prop3_history_optimum | 1 | 1/2 | 0 | 1 | per_copy | 1/4 | 1/4 | == | True | histories=full (1) |
| prop3_E[R|I=0] | 1 | 1/2 | 0 | 1 | per_copy | 1/4 | 1/4 | == | True | histories=full (1) |
| prop3_every_history_with_I=0 | 1 | 1/2 | 0 | 1 | per_copy | 1 | 1 | == | True | histories=full (1); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 1 | 1/2 | 0 | 1 | per_copy | 1/4 | 1/4 | == | True | histories=full (1); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 1 | 1/2 | 0 | 1 | per_copy | 0 | 0 | == | True | histories=full (1) |
| prop3_share_recovered | 1 | 1/2 | 0 | 1 | per_copy | 0 | 0 | == | True | histories=full (1) |
| prop3_M0_equals_prop1 | 1 | 1/2 | 0 | 1 | per_copy | 1/4 | 1/4 | == | True | histories=full (1); closed_form column = enumerated Prop 1 |
| prop3_full_vs_count_histories | 1 | 1/2 | 0 | 1 | per_copy | 1/4 | 1/4 | == | True |  |
| prop3_history_optimum | 1 | 1/2 | 1 | 1 | pooled | 1/8 | 1/8 | == | True | histories=count (2) |
| prop3_E[R|I=0] | 1 | 1/2 | 1 | 1 | pooled | 1/4 | 1/4 | == | True | histories=count (2) |
| prop3_every_history_with_I=0 | 1 | 1/2 | 1 | 1 | pooled | 1 | 1 | == | True | histories=count (2); count of distinct per-history optima |
| prop3_E[R|I=1] | 1 | 1/2 | 1 | 1 | pooled | 0 | 0 | == | True | histories=count (2) |
| prop3_every_history_with_I=1 | 1 | 1/2 | 1 | 1 | pooled | 1 | 1 | == | True | histories=count (2); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 1 | 1/2 | 1 | 1 | pooled | 1/8 | 1/8 | == | True | histories=count (2); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 1 | 1/2 | 1 | 1 | pooled | 0 | 0 | == | True | histories=count (2) |
| prop3_share_recovered_vs_f/(2-f) | 1 | 1/2 | 1 | 1 | pooled | 1/2 | 1/3 | >= | True | histories=count (2) |
| prop3_share_recovered_K1 | 1 | 1/2 | 1 | 1 | pooled | 1/2 | 1/2 | == | True | histories=count (2) |
| prop3_history_optimum | 1 | 1/2 | 1 | 1 | pooled | 1/8 | 1/8 | == | True | histories=full (2) |
| prop3_E[R|I=0] | 1 | 1/2 | 1 | 1 | pooled | 1/4 | 1/4 | == | True | histories=full (2) |
| prop3_every_history_with_I=0 | 1 | 1/2 | 1 | 1 | pooled | 1 | 1 | == | True | histories=full (2); count of distinct per-history optima |
| prop3_E[R|I=1] | 1 | 1/2 | 1 | 1 | pooled | 0 | 0 | == | True | histories=full (2) |
| prop3_every_history_with_I=1 | 1 | 1/2 | 1 | 1 | pooled | 1 | 1 | == | True | histories=full (2); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 1 | 1/2 | 1 | 1 | pooled | 1/8 | 1/8 | == | True | histories=full (2); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 1 | 1/2 | 1 | 1 | pooled | 0 | 0 | == | True | histories=full (2) |
| prop3_share_recovered_vs_f/(2-f) | 1 | 1/2 | 1 | 1 | pooled | 1/2 | 1/3 | >= | True | histories=full (2) |
| prop3_share_recovered_K1 | 1 | 1/2 | 1 | 1 | pooled | 1/2 | 1/2 | == | True | histories=full (2) |
| prop3_full_vs_count_histories | 1 | 1/2 | 1 | 1 | pooled | 1/8 | 1/8 | == | True |  |
| prop3_history_optimum | 1 | 1/2 | 1 | 1 | per_copy | 1/8 | 1/8 | == | True | histories=count (2) |
| prop3_E[R|I=0] | 1 | 1/2 | 1 | 1 | per_copy | 1/4 | 1/4 | == | True | histories=count (2) |
| prop3_every_history_with_I=0 | 1 | 1/2 | 1 | 1 | per_copy | 1 | 1 | == | True | histories=count (2); count of distinct per-history optima |
| prop3_E[R|I=1] | 1 | 1/2 | 1 | 1 | per_copy | 0 | 0 | == | True | histories=count (2) |
| prop3_every_history_with_I=1 | 1 | 1/2 | 1 | 1 | per_copy | 1 | 1 | == | True | histories=count (2); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 1 | 1/2 | 1 | 1 | per_copy | 1/8 | 1/8 | == | True | histories=count (2); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 1 | 1/2 | 1 | 1 | per_copy | 0 | 0 | == | True | histories=count (2) |
| prop3_share_recovered | 1 | 1/2 | 1 | 1 | per_copy | 1/2 | 1/2 | == | True | histories=count (2) |
| prop3_history_optimum | 1 | 1/2 | 1 | 1 | per_copy | 1/8 | 1/8 | == | True | histories=full (2) |
| prop3_E[R|I=0] | 1 | 1/2 | 1 | 1 | per_copy | 1/4 | 1/4 | == | True | histories=full (2) |
| prop3_every_history_with_I=0 | 1 | 1/2 | 1 | 1 | per_copy | 1 | 1 | == | True | histories=full (2); count of distinct per-history optima |
| prop3_E[R|I=1] | 1 | 1/2 | 1 | 1 | per_copy | 0 | 0 | == | True | histories=full (2) |
| prop3_every_history_with_I=1 | 1 | 1/2 | 1 | 1 | per_copy | 1 | 1 | == | True | histories=full (2); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 1 | 1/2 | 1 | 1 | per_copy | 1/8 | 1/8 | == | True | histories=full (2); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 1 | 1/2 | 1 | 1 | per_copy | 0 | 0 | == | True | histories=full (2) |
| prop3_share_recovered | 1 | 1/2 | 1 | 1 | per_copy | 1/2 | 1/2 | == | True | histories=full (2) |
| prop3_full_vs_count_histories | 1 | 1/2 | 1 | 1 | per_copy | 1/8 | 1/8 | == | True |  |
| prop3_history_optimum | 1 | 1/2 | 2 | 1 | pooled | 1/16 | 1/16 | == | True | histories=count (3) |
| prop3_E[R|I=0] | 1 | 1/2 | 2 | 1 | pooled | 1/4 | 1/4 | == | True | histories=count (3) |
| prop3_every_history_with_I=0 | 1 | 1/2 | 2 | 1 | pooled | 1 | 1 | == | True | histories=count (3); count of distinct per-history optima |
| prop3_E[R|I=1] | 1 | 1/2 | 2 | 1 | pooled | 0 | 0 | == | True | histories=count (3) |
| prop3_every_history_with_I=1 | 1 | 1/2 | 2 | 1 | pooled | 1 | 1 | == | True | histories=count (3); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 1 | 1/2 | 2 | 1 | pooled | 1/16 | 1/16 | == | True | histories=count (3); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 1 | 1/2 | 2 | 1 | pooled | 0 | 0 | == | True | histories=count (3) |
| prop3_share_recovered_vs_f/(2-f) | 1 | 1/2 | 2 | 1 | pooled | 3/4 | 3/5 | >= | True | histories=count (3) |
| prop3_share_recovered_K1 | 1 | 1/2 | 2 | 1 | pooled | 3/4 | 3/4 | == | True | histories=count (3) |
| prop3_history_optimum | 1 | 1/2 | 2 | 1 | pooled | 1/16 | 1/16 | == | True | histories=full (4) |
| prop3_E[R|I=0] | 1 | 1/2 | 2 | 1 | pooled | 1/4 | 1/4 | == | True | histories=full (4) |
| prop3_every_history_with_I=0 | 1 | 1/2 | 2 | 1 | pooled | 1 | 1 | == | True | histories=full (4); count of distinct per-history optima |
| prop3_E[R|I=1] | 1 | 1/2 | 2 | 1 | pooled | 0 | 0 | == | True | histories=full (4) |
| prop3_every_history_with_I=1 | 1 | 1/2 | 2 | 1 | pooled | 1 | 1 | == | True | histories=full (4); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 1 | 1/2 | 2 | 1 | pooled | 1/16 | 1/16 | == | True | histories=full (4); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 1 | 1/2 | 2 | 1 | pooled | 0 | 0 | == | True | histories=full (4) |
| prop3_share_recovered_vs_f/(2-f) | 1 | 1/2 | 2 | 1 | pooled | 3/4 | 3/5 | >= | True | histories=full (4) |
| prop3_share_recovered_K1 | 1 | 1/2 | 2 | 1 | pooled | 3/4 | 3/4 | == | True | histories=full (4) |
| prop3_full_vs_count_histories | 1 | 1/2 | 2 | 1 | pooled | 1/16 | 1/16 | == | True |  |
| prop3_history_optimum | 1 | 1/2 | 2 | 1 | per_copy | 1/16 | 1/16 | == | True | histories=count (3) |
| prop3_E[R|I=0] | 1 | 1/2 | 2 | 1 | per_copy | 1/4 | 1/4 | == | True | histories=count (3) |
| prop3_every_history_with_I=0 | 1 | 1/2 | 2 | 1 | per_copy | 1 | 1 | == | True | histories=count (3); count of distinct per-history optima |
| prop3_E[R|I=1] | 1 | 1/2 | 2 | 1 | per_copy | 0 | 0 | == | True | histories=count (3) |
| prop3_every_history_with_I=1 | 1 | 1/2 | 2 | 1 | per_copy | 1 | 1 | == | True | histories=count (3); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 1 | 1/2 | 2 | 1 | per_copy | 1/16 | 1/16 | == | True | histories=count (3); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 1 | 1/2 | 2 | 1 | per_copy | 0 | 0 | == | True | histories=count (3) |
| prop3_share_recovered | 1 | 1/2 | 2 | 1 | per_copy | 3/4 | 3/4 | == | True | histories=count (3) |
| prop3_history_optimum | 1 | 1/2 | 2 | 1 | per_copy | 1/16 | 1/16 | == | True | histories=full (4) |
| prop3_E[R|I=0] | 1 | 1/2 | 2 | 1 | per_copy | 1/4 | 1/4 | == | True | histories=full (4) |
| prop3_every_history_with_I=0 | 1 | 1/2 | 2 | 1 | per_copy | 1 | 1 | == | True | histories=full (4); count of distinct per-history optima |
| prop3_E[R|I=1] | 1 | 1/2 | 2 | 1 | per_copy | 0 | 0 | == | True | histories=full (4) |
| prop3_every_history_with_I=1 | 1 | 1/2 | 2 | 1 | per_copy | 1 | 1 | == | True | histories=full (4); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 1 | 1/2 | 2 | 1 | per_copy | 1/16 | 1/16 | == | True | histories=full (4); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 1 | 1/2 | 2 | 1 | per_copy | 0 | 0 | == | True | histories=full (4) |
| prop3_share_recovered | 1 | 1/2 | 2 | 1 | per_copy | 3/4 | 3/4 | == | True | histories=full (4) |
| prop3_full_vs_count_histories | 1 | 1/2 | 2 | 1 | per_copy | 1/16 | 1/16 | == | True |  |
| prop3_history_optimum | 1 | 1/2 | 3 | 1 | pooled | 1/32 | 1/32 | == | True | histories=count (4) |
| prop3_E[R|I=0] | 1 | 1/2 | 3 | 1 | pooled | 1/4 | 1/4 | == | True | histories=count (4) |
| prop3_every_history_with_I=0 | 1 | 1/2 | 3 | 1 | pooled | 1 | 1 | == | True | histories=count (4); count of distinct per-history optima |
| prop3_E[R|I=1] | 1 | 1/2 | 3 | 1 | pooled | 0 | 0 | == | True | histories=count (4) |
| prop3_every_history_with_I=1 | 1 | 1/2 | 3 | 1 | pooled | 1 | 1 | == | True | histories=count (4); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 1 | 1/2 | 3 | 1 | pooled | 1/32 | 1/32 | == | True | histories=count (4); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 1 | 1/2 | 3 | 1 | pooled | 0 | 0 | == | True | histories=count (4) |
| prop3_share_recovered_vs_f/(2-f) | 1 | 1/2 | 3 | 1 | pooled | 7/8 | 7/9 | >= | True | histories=count (4) |
| prop3_share_recovered_K1 | 1 | 1/2 | 3 | 1 | pooled | 7/8 | 7/8 | == | True | histories=count (4) |
| prop3_history_optimum | 1 | 1/2 | 3 | 1 | pooled | 1/32 | 1/32 | == | True | histories=full (8) |
| prop3_E[R|I=0] | 1 | 1/2 | 3 | 1 | pooled | 1/4 | 1/4 | == | True | histories=full (8) |
| prop3_every_history_with_I=0 | 1 | 1/2 | 3 | 1 | pooled | 1 | 1 | == | True | histories=full (8); count of distinct per-history optima |
| prop3_E[R|I=1] | 1 | 1/2 | 3 | 1 | pooled | 0 | 0 | == | True | histories=full (8) |
| prop3_every_history_with_I=1 | 1 | 1/2 | 3 | 1 | pooled | 1 | 1 | == | True | histories=full (8); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 1 | 1/2 | 3 | 1 | pooled | 1/32 | 1/32 | == | True | histories=full (8); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 1 | 1/2 | 3 | 1 | pooled | 0 | 0 | == | True | histories=full (8) |
| prop3_share_recovered_vs_f/(2-f) | 1 | 1/2 | 3 | 1 | pooled | 7/8 | 7/9 | >= | True | histories=full (8) |
| prop3_share_recovered_K1 | 1 | 1/2 | 3 | 1 | pooled | 7/8 | 7/8 | == | True | histories=full (8) |
| prop3_full_vs_count_histories | 1 | 1/2 | 3 | 1 | pooled | 1/32 | 1/32 | == | True |  |
| prop3_history_optimum | 1 | 1/2 | 3 | 1 | per_copy | 1/32 | 1/32 | == | True | histories=count (4) |
| prop3_E[R|I=0] | 1 | 1/2 | 3 | 1 | per_copy | 1/4 | 1/4 | == | True | histories=count (4) |
| prop3_every_history_with_I=0 | 1 | 1/2 | 3 | 1 | per_copy | 1 | 1 | == | True | histories=count (4); count of distinct per-history optima |
| prop3_E[R|I=1] | 1 | 1/2 | 3 | 1 | per_copy | 0 | 0 | == | True | histories=count (4) |
| prop3_every_history_with_I=1 | 1 | 1/2 | 3 | 1 | per_copy | 1 | 1 | == | True | histories=count (4); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 1 | 1/2 | 3 | 1 | per_copy | 1/32 | 1/32 | == | True | histories=count (4); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 1 | 1/2 | 3 | 1 | per_copy | 0 | 0 | == | True | histories=count (4) |
| prop3_share_recovered | 1 | 1/2 | 3 | 1 | per_copy | 7/8 | 7/8 | == | True | histories=count (4) |
| prop3_history_optimum | 1 | 1/2 | 3 | 1 | per_copy | 1/32 | 1/32 | == | True | histories=full (8) |
| prop3_E[R|I=0] | 1 | 1/2 | 3 | 1 | per_copy | 1/4 | 1/4 | == | True | histories=full (8) |
| prop3_every_history_with_I=0 | 1 | 1/2 | 3 | 1 | per_copy | 1 | 1 | == | True | histories=full (8); count of distinct per-history optima |
| prop3_E[R|I=1] | 1 | 1/2 | 3 | 1 | per_copy | 0 | 0 | == | True | histories=full (8) |
| prop3_every_history_with_I=1 | 1 | 1/2 | 3 | 1 | per_copy | 1 | 1 | == | True | histories=full (8); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 1 | 1/2 | 3 | 1 | per_copy | 1/32 | 1/32 | == | True | histories=full (8); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 1 | 1/2 | 3 | 1 | per_copy | 0 | 0 | == | True | histories=full (8) |
| prop3_share_recovered | 1 | 1/2 | 3 | 1 | per_copy | 7/8 | 7/8 | == | True | histories=full (8) |
| prop3_full_vs_count_histories | 1 | 1/2 | 3 | 1 | per_copy | 1/32 | 1/32 | == | True |  |
| prop3_history_optimum | 1 | 1/2 | 5 | 1 | pooled | 1/128 | 1/128 | == | True | histories=count (6) |
| prop3_E[R|I=0] | 1 | 1/2 | 5 | 1 | pooled | 1/4 | 1/4 | == | True | histories=count (6) |
| prop3_every_history_with_I=0 | 1 | 1/2 | 5 | 1 | pooled | 1 | 1 | == | True | histories=count (6); count of distinct per-history optima |
| prop3_E[R|I=1] | 1 | 1/2 | 5 | 1 | pooled | 0 | 0 | == | True | histories=count (6) |
| prop3_every_history_with_I=1 | 1 | 1/2 | 5 | 1 | pooled | 1 | 1 | == | True | histories=count (6); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 1 | 1/2 | 5 | 1 | pooled | 1/128 | 1/128 | == | True | histories=count (6); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 1 | 1/2 | 5 | 1 | pooled | 0 | 0 | == | True | histories=count (6) |
| prop3_share_recovered_vs_f/(2-f) | 1 | 1/2 | 5 | 1 | pooled | 31/32 | 31/33 | >= | True | histories=count (6) |
| prop3_share_recovered_K1 | 1 | 1/2 | 5 | 1 | pooled | 31/32 | 31/32 | == | True | histories=count (6) |
| prop3_history_optimum | 1 | 1/2 | 5 | 1 | pooled | 1/128 | 1/128 | == | True | histories=full (32) |
| prop3_E[R|I=0] | 1 | 1/2 | 5 | 1 | pooled | 1/4 | 1/4 | == | True | histories=full (32) |
| prop3_every_history_with_I=0 | 1 | 1/2 | 5 | 1 | pooled | 1 | 1 | == | True | histories=full (32); count of distinct per-history optima |
| prop3_E[R|I=1] | 1 | 1/2 | 5 | 1 | pooled | 0 | 0 | == | True | histories=full (32) |
| prop3_every_history_with_I=1 | 1 | 1/2 | 5 | 1 | pooled | 1 | 1 | == | True | histories=full (32); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 1 | 1/2 | 5 | 1 | pooled | 1/128 | 1/128 | == | True | histories=full (32); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 1 | 1/2 | 5 | 1 | pooled | 0 | 0 | == | True | histories=full (32) |
| prop3_share_recovered_vs_f/(2-f) | 1 | 1/2 | 5 | 1 | pooled | 31/32 | 31/33 | >= | True | histories=full (32) |
| prop3_share_recovered_K1 | 1 | 1/2 | 5 | 1 | pooled | 31/32 | 31/32 | == | True | histories=full (32) |
| prop3_full_vs_count_histories | 1 | 1/2 | 5 | 1 | pooled | 1/128 | 1/128 | == | True |  |
| prop3_history_optimum | 1 | 1/2 | 5 | 1 | per_copy | 1/128 | 1/128 | == | True | histories=count (6) |
| prop3_E[R|I=0] | 1 | 1/2 | 5 | 1 | per_copy | 1/4 | 1/4 | == | True | histories=count (6) |
| prop3_every_history_with_I=0 | 1 | 1/2 | 5 | 1 | per_copy | 1 | 1 | == | True | histories=count (6); count of distinct per-history optima |
| prop3_E[R|I=1] | 1 | 1/2 | 5 | 1 | per_copy | 0 | 0 | == | True | histories=count (6) |
| prop3_every_history_with_I=1 | 1 | 1/2 | 5 | 1 | per_copy | 1 | 1 | == | True | histories=count (6); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 1 | 1/2 | 5 | 1 | per_copy | 1/128 | 1/128 | == | True | histories=count (6); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 1 | 1/2 | 5 | 1 | per_copy | 0 | 0 | == | True | histories=count (6) |
| prop3_share_recovered | 1 | 1/2 | 5 | 1 | per_copy | 31/32 | 31/32 | == | True | histories=count (6) |
| prop3_history_optimum | 1 | 1/2 | 5 | 1 | per_copy | 1/128 | 1/128 | == | True | histories=full (32) |
| prop3_E[R|I=0] | 1 | 1/2 | 5 | 1 | per_copy | 1/4 | 1/4 | == | True | histories=full (32) |
| prop3_every_history_with_I=0 | 1 | 1/2 | 5 | 1 | per_copy | 1 | 1 | == | True | histories=full (32); count of distinct per-history optima |
| prop3_E[R|I=1] | 1 | 1/2 | 5 | 1 | per_copy | 0 | 0 | == | True | histories=full (32) |
| prop3_every_history_with_I=1 | 1 | 1/2 | 5 | 1 | per_copy | 1 | 1 | == | True | histories=full (32); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 1 | 1/2 | 5 | 1 | per_copy | 1/128 | 1/128 | == | True | histories=full (32); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 1 | 1/2 | 5 | 1 | per_copy | 0 | 0 | == | True | histories=full (32) |
| prop3_share_recovered | 1 | 1/2 | 5 | 1 | per_copy | 31/32 | 31/32 | == | True | histories=full (32) |
| prop3_full_vs_count_histories | 1 | 1/2 | 5 | 1 | per_copy | 1/128 | 1/128 | == | True |  |
| prop1_oblivious_optimum | 1 | 2/5 |  | 1 | pooled | 1/5 | 1/5 | == | True | 17 orbits / 28 schedules |
| prop1_posterior_optimum | 1 | 2/5 |  | 1 | pooled | 0 | 0 | == | True |  |
| prop1_hedge_all_A_max_R_over_realizations | 1 | 2/5 |  | 1 | pooled | 0 | 0 | == | True |  |
| prop1_oblivious_optimum | 1 | 2/5 |  | 1 | per_copy | 1/5 | 1/5 | == | True | 17 orbits / 28 schedules |
| prop1_posterior_optimum | 1 | 2/5 |  | 1 | per_copy | 0 | 0 | == | True |  |
| prop1_hedge_all_A_max_R_over_realizations | 1 | 2/5 |  | 1 | per_copy | 0 | 0 | == | True |  |
| gap_c | 1 | 2/5 |  | 0 | pooled | 0 | 0 | == | True |  |
| gap_c_oblivious_optimum | 1 | 2/5 |  | 0 | pooled | 2/5 | 2/5 | == | True |  |
| gap_c_posterior_optimum | 1 | 2/5 |  | 0 | pooled | 2/5 | 2/5 | == | True |  |
| gap_c | 1 | 2/5 |  | 1 | pooled | 1/5 | 1/5 | == | True |  |
| gap_c_oblivious_optimum | 1 | 2/5 |  | 1 | pooled | 1/5 | 1/5 | == | True |  |
| gap_c_posterior_optimum | 1 | 2/5 |  | 1 | pooled | 0 | 0 | == | True |  |
| gap_c | 1 | 2/5 |  | 2 | pooled | 0 | 0 | == | True |  |
| gap_c_oblivious_optimum | 1 | 2/5 |  | 2 | pooled | 0 | 0 | == | True |  |
| gap_c_posterior_optimum | 1 | 2/5 |  | 2 | pooled | 0 | 0 | == | True |  |
| gap_c | 1 | 2/5 |  | 0 | per_copy | 0 | 0 | == | True |  |
| gap_c_oblivious_optimum | 1 | 2/5 |  | 0 | per_copy | 2/5 | 2/5 | == | True |  |
| gap_c_posterior_optimum | 1 | 2/5 |  | 0 | per_copy | 2/5 | 2/5 | == | True |  |
| gap_c | 1 | 2/5 |  | 1 | per_copy | 1/5 | 1/5 | == | True |  |
| gap_c_oblivious_optimum | 1 | 2/5 |  | 1 | per_copy | 1/5 | 1/5 | == | True |  |
| gap_c_posterior_optimum | 1 | 2/5 |  | 1 | per_copy | 0 | 0 | == | True |  |
| gap_c | 1 | 2/5 |  | 2 | per_copy | 0 | 0 | == | True |  |
| gap_c_oblivious_optimum | 1 | 2/5 |  | 2 | per_copy | 0 | 0 | == | True |  |
| gap_c_posterior_optimum | 1 | 2/5 |  | 2 | per_copy | 0 | 0 | == | True |  |
| prop3_history_optimum | 1 | 2/5 | 0 | 1 | pooled | 1/5 | 1/5 | == | True | histories=count (1) |
| prop3_E[R|I=0] | 1 | 2/5 | 0 | 1 | pooled | 1/5 | 1/5 | == | True | histories=count (1) |
| prop3_every_history_with_I=0 | 1 | 2/5 | 0 | 1 | pooled | 1 | 1 | == | True | histories=count (1); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 1 | 2/5 | 0 | 1 | pooled | 1/5 | 1/5 | == | True | histories=count (1); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 1 | 2/5 | 0 | 1 | pooled | 0 | 0 | == | True | histories=count (1) |
| prop3_share_recovered_vs_f/(2-f) | 1 | 2/5 | 0 | 1 | pooled | 0 | 0 | >= | True | histories=count (1) |
| prop3_share_recovered_K1 | 1 | 2/5 | 0 | 1 | pooled | 0 | 0 | == | True | histories=count (1) |
| prop3_M0_equals_prop1 | 1 | 2/5 | 0 | 1 | pooled | 1/5 | 1/5 | == | True | histories=count (1); closed_form column = enumerated Prop 1 |
| prop3_history_optimum | 1 | 2/5 | 0 | 1 | pooled | 1/5 | 1/5 | == | True | histories=full (1) |
| prop3_E[R|I=0] | 1 | 2/5 | 0 | 1 | pooled | 1/5 | 1/5 | == | True | histories=full (1) |
| prop3_every_history_with_I=0 | 1 | 2/5 | 0 | 1 | pooled | 1 | 1 | == | True | histories=full (1); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 1 | 2/5 | 0 | 1 | pooled | 1/5 | 1/5 | == | True | histories=full (1); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 1 | 2/5 | 0 | 1 | pooled | 0 | 0 | == | True | histories=full (1) |
| prop3_share_recovered_vs_f/(2-f) | 1 | 2/5 | 0 | 1 | pooled | 0 | 0 | >= | True | histories=full (1) |
| prop3_share_recovered_K1 | 1 | 2/5 | 0 | 1 | pooled | 0 | 0 | == | True | histories=full (1) |
| prop3_M0_equals_prop1 | 1 | 2/5 | 0 | 1 | pooled | 1/5 | 1/5 | == | True | histories=full (1); closed_form column = enumerated Prop 1 |
| prop3_full_vs_count_histories | 1 | 2/5 | 0 | 1 | pooled | 1/5 | 1/5 | == | True |  |
| prop3_history_optimum | 1 | 2/5 | 0 | 1 | per_copy | 1/5 | 1/5 | == | True | histories=count (1) |
| prop3_E[R|I=0] | 1 | 2/5 | 0 | 1 | per_copy | 1/5 | 1/5 | == | True | histories=count (1) |
| prop3_every_history_with_I=0 | 1 | 2/5 | 0 | 1 | per_copy | 1 | 1 | == | True | histories=count (1); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 1 | 2/5 | 0 | 1 | per_copy | 1/5 | 1/5 | == | True | histories=count (1); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 1 | 2/5 | 0 | 1 | per_copy | 0 | 0 | == | True | histories=count (1) |
| prop3_share_recovered | 1 | 2/5 | 0 | 1 | per_copy | 0 | 0 | == | True | histories=count (1) |
| prop3_M0_equals_prop1 | 1 | 2/5 | 0 | 1 | per_copy | 1/5 | 1/5 | == | True | histories=count (1); closed_form column = enumerated Prop 1 |
| prop3_history_optimum | 1 | 2/5 | 0 | 1 | per_copy | 1/5 | 1/5 | == | True | histories=full (1) |
| prop3_E[R|I=0] | 1 | 2/5 | 0 | 1 | per_copy | 1/5 | 1/5 | == | True | histories=full (1) |
| prop3_every_history_with_I=0 | 1 | 2/5 | 0 | 1 | per_copy | 1 | 1 | == | True | histories=full (1); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 1 | 2/5 | 0 | 1 | per_copy | 1/5 | 1/5 | == | True | histories=full (1); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 1 | 2/5 | 0 | 1 | per_copy | 0 | 0 | == | True | histories=full (1) |
| prop3_share_recovered | 1 | 2/5 | 0 | 1 | per_copy | 0 | 0 | == | True | histories=full (1) |
| prop3_M0_equals_prop1 | 1 | 2/5 | 0 | 1 | per_copy | 1/5 | 1/5 | == | True | histories=full (1); closed_form column = enumerated Prop 1 |
| prop3_full_vs_count_histories | 1 | 2/5 | 0 | 1 | per_copy | 1/5 | 1/5 | == | True |  |
| prop3_history_optimum | 1 | 2/5 | 1 | 1 | pooled | 3/25 | 3/25 | == | True | histories=count (2) |
| prop3_E[R|I=0] | 1 | 2/5 | 1 | 1 | pooled | 1/5 | 1/5 | == | True | histories=count (2) |
| prop3_every_history_with_I=0 | 1 | 2/5 | 1 | 1 | pooled | 1 | 1 | == | True | histories=count (2); count of distinct per-history optima |
| prop3_E[R|I=1] | 1 | 2/5 | 1 | 1 | pooled | 0 | 0 | == | True | histories=count (2) |
| prop3_every_history_with_I=1 | 1 | 2/5 | 1 | 1 | pooled | 1 | 1 | == | True | histories=count (2); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 1 | 2/5 | 1 | 1 | pooled | 3/25 | 3/25 | == | True | histories=count (2); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 1 | 2/5 | 1 | 1 | pooled | 0 | 0 | == | True | histories=count (2) |
| prop3_share_recovered_vs_f/(2-f) | 1 | 2/5 | 1 | 1 | pooled | 2/5 | 1/4 | >= | True | histories=count (2) |
| prop3_share_recovered_K1 | 1 | 2/5 | 1 | 1 | pooled | 2/5 | 2/5 | == | True | histories=count (2) |
| prop3_history_optimum | 1 | 2/5 | 1 | 1 | pooled | 3/25 | 3/25 | == | True | histories=full (2) |
| prop3_E[R|I=0] | 1 | 2/5 | 1 | 1 | pooled | 1/5 | 1/5 | == | True | histories=full (2) |
| prop3_every_history_with_I=0 | 1 | 2/5 | 1 | 1 | pooled | 1 | 1 | == | True | histories=full (2); count of distinct per-history optima |
| prop3_E[R|I=1] | 1 | 2/5 | 1 | 1 | pooled | 0 | 0 | == | True | histories=full (2) |
| prop3_every_history_with_I=1 | 1 | 2/5 | 1 | 1 | pooled | 1 | 1 | == | True | histories=full (2); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 1 | 2/5 | 1 | 1 | pooled | 3/25 | 3/25 | == | True | histories=full (2); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 1 | 2/5 | 1 | 1 | pooled | 0 | 0 | == | True | histories=full (2) |
| prop3_share_recovered_vs_f/(2-f) | 1 | 2/5 | 1 | 1 | pooled | 2/5 | 1/4 | >= | True | histories=full (2) |
| prop3_share_recovered_K1 | 1 | 2/5 | 1 | 1 | pooled | 2/5 | 2/5 | == | True | histories=full (2) |
| prop3_full_vs_count_histories | 1 | 2/5 | 1 | 1 | pooled | 3/25 | 3/25 | == | True |  |
| prop3_history_optimum | 1 | 2/5 | 1 | 1 | per_copy | 3/25 | 3/25 | == | True | histories=count (2) |
| prop3_E[R|I=0] | 1 | 2/5 | 1 | 1 | per_copy | 1/5 | 1/5 | == | True | histories=count (2) |
| prop3_every_history_with_I=0 | 1 | 2/5 | 1 | 1 | per_copy | 1 | 1 | == | True | histories=count (2); count of distinct per-history optima |
| prop3_E[R|I=1] | 1 | 2/5 | 1 | 1 | per_copy | 0 | 0 | == | True | histories=count (2) |
| prop3_every_history_with_I=1 | 1 | 2/5 | 1 | 1 | per_copy | 1 | 1 | == | True | histories=count (2); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 1 | 2/5 | 1 | 1 | per_copy | 3/25 | 3/25 | == | True | histories=count (2); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 1 | 2/5 | 1 | 1 | per_copy | 0 | 0 | == | True | histories=count (2) |
| prop3_share_recovered | 1 | 2/5 | 1 | 1 | per_copy | 2/5 | 2/5 | == | True | histories=count (2) |
| prop3_history_optimum | 1 | 2/5 | 1 | 1 | per_copy | 3/25 | 3/25 | == | True | histories=full (2) |
| prop3_E[R|I=0] | 1 | 2/5 | 1 | 1 | per_copy | 1/5 | 1/5 | == | True | histories=full (2) |
| prop3_every_history_with_I=0 | 1 | 2/5 | 1 | 1 | per_copy | 1 | 1 | == | True | histories=full (2); count of distinct per-history optima |
| prop3_E[R|I=1] | 1 | 2/5 | 1 | 1 | per_copy | 0 | 0 | == | True | histories=full (2) |
| prop3_every_history_with_I=1 | 1 | 2/5 | 1 | 1 | per_copy | 1 | 1 | == | True | histories=full (2); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 1 | 2/5 | 1 | 1 | per_copy | 3/25 | 3/25 | == | True | histories=full (2); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 1 | 2/5 | 1 | 1 | per_copy | 0 | 0 | == | True | histories=full (2) |
| prop3_share_recovered | 1 | 2/5 | 1 | 1 | per_copy | 2/5 | 2/5 | == | True | histories=full (2) |
| prop3_full_vs_count_histories | 1 | 2/5 | 1 | 1 | per_copy | 3/25 | 3/25 | == | True |  |
| prop3_history_optimum | 1 | 2/5 | 2 | 1 | pooled | 9/125 | 9/125 | == | True | histories=count (3) |
| prop3_E[R|I=0] | 1 | 2/5 | 2 | 1 | pooled | 1/5 | 1/5 | == | True | histories=count (3) |
| prop3_every_history_with_I=0 | 1 | 2/5 | 2 | 1 | pooled | 1 | 1 | == | True | histories=count (3); count of distinct per-history optima |
| prop3_E[R|I=1] | 1 | 2/5 | 2 | 1 | pooled | 0 | 0 | == | True | histories=count (3) |
| prop3_every_history_with_I=1 | 1 | 2/5 | 2 | 1 | pooled | 1 | 1 | == | True | histories=count (3); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 1 | 2/5 | 2 | 1 | pooled | 9/125 | 9/125 | == | True | histories=count (3); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 1 | 2/5 | 2 | 1 | pooled | 0 | 0 | == | True | histories=count (3) |
| prop3_share_recovered_vs_f/(2-f) | 1 | 2/5 | 2 | 1 | pooled | 16/25 | 8/17 | >= | True | histories=count (3) |
| prop3_share_recovered_K1 | 1 | 2/5 | 2 | 1 | pooled | 16/25 | 16/25 | == | True | histories=count (3) |
| prop3_history_optimum | 1 | 2/5 | 2 | 1 | pooled | 9/125 | 9/125 | == | True | histories=full (4) |
| prop3_E[R|I=0] | 1 | 2/5 | 2 | 1 | pooled | 1/5 | 1/5 | == | True | histories=full (4) |
| prop3_every_history_with_I=0 | 1 | 2/5 | 2 | 1 | pooled | 1 | 1 | == | True | histories=full (4); count of distinct per-history optima |
| prop3_E[R|I=1] | 1 | 2/5 | 2 | 1 | pooled | 0 | 0 | == | True | histories=full (4) |
| prop3_every_history_with_I=1 | 1 | 2/5 | 2 | 1 | pooled | 1 | 1 | == | True | histories=full (4); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 1 | 2/5 | 2 | 1 | pooled | 9/125 | 9/125 | == | True | histories=full (4); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 1 | 2/5 | 2 | 1 | pooled | 0 | 0 | == | True | histories=full (4) |
| prop3_share_recovered_vs_f/(2-f) | 1 | 2/5 | 2 | 1 | pooled | 16/25 | 8/17 | >= | True | histories=full (4) |
| prop3_share_recovered_K1 | 1 | 2/5 | 2 | 1 | pooled | 16/25 | 16/25 | == | True | histories=full (4) |
| prop3_full_vs_count_histories | 1 | 2/5 | 2 | 1 | pooled | 9/125 | 9/125 | == | True |  |
| prop3_history_optimum | 1 | 2/5 | 2 | 1 | per_copy | 9/125 | 9/125 | == | True | histories=count (3) |
| prop3_E[R|I=0] | 1 | 2/5 | 2 | 1 | per_copy | 1/5 | 1/5 | == | True | histories=count (3) |
| prop3_every_history_with_I=0 | 1 | 2/5 | 2 | 1 | per_copy | 1 | 1 | == | True | histories=count (3); count of distinct per-history optima |
| prop3_E[R|I=1] | 1 | 2/5 | 2 | 1 | per_copy | 0 | 0 | == | True | histories=count (3) |
| prop3_every_history_with_I=1 | 1 | 2/5 | 2 | 1 | per_copy | 1 | 1 | == | True | histories=count (3); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 1 | 2/5 | 2 | 1 | per_copy | 9/125 | 9/125 | == | True | histories=count (3); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 1 | 2/5 | 2 | 1 | per_copy | 0 | 0 | == | True | histories=count (3) |
| prop3_share_recovered | 1 | 2/5 | 2 | 1 | per_copy | 16/25 | 16/25 | == | True | histories=count (3) |
| prop3_history_optimum | 1 | 2/5 | 2 | 1 | per_copy | 9/125 | 9/125 | == | True | histories=full (4) |
| prop3_E[R|I=0] | 1 | 2/5 | 2 | 1 | per_copy | 1/5 | 1/5 | == | True | histories=full (4) |
| prop3_every_history_with_I=0 | 1 | 2/5 | 2 | 1 | per_copy | 1 | 1 | == | True | histories=full (4); count of distinct per-history optima |
| prop3_E[R|I=1] | 1 | 2/5 | 2 | 1 | per_copy | 0 | 0 | == | True | histories=full (4) |
| prop3_every_history_with_I=1 | 1 | 2/5 | 2 | 1 | per_copy | 1 | 1 | == | True | histories=full (4); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 1 | 2/5 | 2 | 1 | per_copy | 9/125 | 9/125 | == | True | histories=full (4); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 1 | 2/5 | 2 | 1 | per_copy | 0 | 0 | == | True | histories=full (4) |
| prop3_share_recovered | 1 | 2/5 | 2 | 1 | per_copy | 16/25 | 16/25 | == | True | histories=full (4) |
| prop3_full_vs_count_histories | 1 | 2/5 | 2 | 1 | per_copy | 9/125 | 9/125 | == | True |  |
| prop3_history_optimum | 1 | 2/5 | 3 | 1 | pooled | 27/625 | 27/625 | == | True | histories=count (4) |
| prop3_E[R|I=0] | 1 | 2/5 | 3 | 1 | pooled | 1/5 | 1/5 | == | True | histories=count (4) |
| prop3_every_history_with_I=0 | 1 | 2/5 | 3 | 1 | pooled | 1 | 1 | == | True | histories=count (4); count of distinct per-history optima |
| prop3_E[R|I=1] | 1 | 2/5 | 3 | 1 | pooled | 0 | 0 | == | True | histories=count (4) |
| prop3_every_history_with_I=1 | 1 | 2/5 | 3 | 1 | pooled | 1 | 1 | == | True | histories=count (4); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 1 | 2/5 | 3 | 1 | pooled | 27/625 | 27/625 | == | True | histories=count (4); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 1 | 2/5 | 3 | 1 | pooled | 0 | 0 | == | True | histories=count (4) |
| prop3_share_recovered_vs_f/(2-f) | 1 | 2/5 | 3 | 1 | pooled | 98/125 | 49/76 | >= | True | histories=count (4) |
| prop3_share_recovered_K1 | 1 | 2/5 | 3 | 1 | pooled | 98/125 | 98/125 | == | True | histories=count (4) |
| prop3_history_optimum | 1 | 2/5 | 3 | 1 | pooled | 27/625 | 27/625 | == | True | histories=full (8) |
| prop3_E[R|I=0] | 1 | 2/5 | 3 | 1 | pooled | 1/5 | 1/5 | == | True | histories=full (8) |
| prop3_every_history_with_I=0 | 1 | 2/5 | 3 | 1 | pooled | 1 | 1 | == | True | histories=full (8); count of distinct per-history optima |
| prop3_E[R|I=1] | 1 | 2/5 | 3 | 1 | pooled | 0 | 0 | == | True | histories=full (8) |
| prop3_every_history_with_I=1 | 1 | 2/5 | 3 | 1 | pooled | 1 | 1 | == | True | histories=full (8); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 1 | 2/5 | 3 | 1 | pooled | 27/625 | 27/625 | == | True | histories=full (8); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 1 | 2/5 | 3 | 1 | pooled | 0 | 0 | == | True | histories=full (8) |
| prop3_share_recovered_vs_f/(2-f) | 1 | 2/5 | 3 | 1 | pooled | 98/125 | 49/76 | >= | True | histories=full (8) |
| prop3_share_recovered_K1 | 1 | 2/5 | 3 | 1 | pooled | 98/125 | 98/125 | == | True | histories=full (8) |
| prop3_full_vs_count_histories | 1 | 2/5 | 3 | 1 | pooled | 27/625 | 27/625 | == | True |  |
| prop3_history_optimum | 1 | 2/5 | 3 | 1 | per_copy | 27/625 | 27/625 | == | True | histories=count (4) |
| prop3_E[R|I=0] | 1 | 2/5 | 3 | 1 | per_copy | 1/5 | 1/5 | == | True | histories=count (4) |
| prop3_every_history_with_I=0 | 1 | 2/5 | 3 | 1 | per_copy | 1 | 1 | == | True | histories=count (4); count of distinct per-history optima |
| prop3_E[R|I=1] | 1 | 2/5 | 3 | 1 | per_copy | 0 | 0 | == | True | histories=count (4) |
| prop3_every_history_with_I=1 | 1 | 2/5 | 3 | 1 | per_copy | 1 | 1 | == | True | histories=count (4); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 1 | 2/5 | 3 | 1 | per_copy | 27/625 | 27/625 | == | True | histories=count (4); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 1 | 2/5 | 3 | 1 | per_copy | 0 | 0 | == | True | histories=count (4) |
| prop3_share_recovered | 1 | 2/5 | 3 | 1 | per_copy | 98/125 | 98/125 | == | True | histories=count (4) |
| prop3_history_optimum | 1 | 2/5 | 3 | 1 | per_copy | 27/625 | 27/625 | == | True | histories=full (8) |
| prop3_E[R|I=0] | 1 | 2/5 | 3 | 1 | per_copy | 1/5 | 1/5 | == | True | histories=full (8) |
| prop3_every_history_with_I=0 | 1 | 2/5 | 3 | 1 | per_copy | 1 | 1 | == | True | histories=full (8); count of distinct per-history optima |
| prop3_E[R|I=1] | 1 | 2/5 | 3 | 1 | per_copy | 0 | 0 | == | True | histories=full (8) |
| prop3_every_history_with_I=1 | 1 | 2/5 | 3 | 1 | per_copy | 1 | 1 | == | True | histories=full (8); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 1 | 2/5 | 3 | 1 | per_copy | 27/625 | 27/625 | == | True | histories=full (8); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 1 | 2/5 | 3 | 1 | per_copy | 0 | 0 | == | True | histories=full (8) |
| prop3_share_recovered | 1 | 2/5 | 3 | 1 | per_copy | 98/125 | 98/125 | == | True | histories=full (8) |
| prop3_full_vs_count_histories | 1 | 2/5 | 3 | 1 | per_copy | 27/625 | 27/625 | == | True |  |
| prop3_history_optimum | 1 | 2/5 | 5 | 1 | pooled | 243/15625 | 243/15625 | == | True | histories=count (6) |
| prop3_E[R|I=0] | 1 | 2/5 | 5 | 1 | pooled | 1/5 | 1/5 | == | True | histories=count (6) |
| prop3_every_history_with_I=0 | 1 | 2/5 | 5 | 1 | pooled | 1 | 1 | == | True | histories=count (6); count of distinct per-history optima |
| prop3_E[R|I=1] | 1 | 2/5 | 5 | 1 | pooled | 0 | 0 | == | True | histories=count (6) |
| prop3_every_history_with_I=1 | 1 | 2/5 | 5 | 1 | pooled | 1 | 1 | == | True | histories=count (6); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 1 | 2/5 | 5 | 1 | pooled | 243/15625 | 243/15625 | == | True | histories=count (6); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 1 | 2/5 | 5 | 1 | pooled | 0 | 0 | == | True | histories=count (6) |
| prop3_share_recovered_vs_f/(2-f) | 1 | 2/5 | 5 | 1 | pooled | 2882/3125 | 1441/1684 | >= | True | histories=count (6) |
| prop3_share_recovered_K1 | 1 | 2/5 | 5 | 1 | pooled | 2882/3125 | 2882/3125 | == | True | histories=count (6) |
| prop3_history_optimum | 1 | 2/5 | 5 | 1 | pooled | 243/15625 | 243/15625 | == | True | histories=full (32) |
| prop3_E[R|I=0] | 1 | 2/5 | 5 | 1 | pooled | 1/5 | 1/5 | == | True | histories=full (32) |
| prop3_every_history_with_I=0 | 1 | 2/5 | 5 | 1 | pooled | 1 | 1 | == | True | histories=full (32); count of distinct per-history optima |
| prop3_E[R|I=1] | 1 | 2/5 | 5 | 1 | pooled | 0 | 0 | == | True | histories=full (32) |
| prop3_every_history_with_I=1 | 1 | 2/5 | 5 | 1 | pooled | 1 | 1 | == | True | histories=full (32); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 1 | 2/5 | 5 | 1 | pooled | 243/15625 | 243/15625 | == | True | histories=full (32); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 1 | 2/5 | 5 | 1 | pooled | 0 | 0 | == | True | histories=full (32) |
| prop3_share_recovered_vs_f/(2-f) | 1 | 2/5 | 5 | 1 | pooled | 2882/3125 | 1441/1684 | >= | True | histories=full (32) |
| prop3_share_recovered_K1 | 1 | 2/5 | 5 | 1 | pooled | 2882/3125 | 2882/3125 | == | True | histories=full (32) |
| prop3_full_vs_count_histories | 1 | 2/5 | 5 | 1 | pooled | 243/15625 | 243/15625 | == | True |  |
| prop3_history_optimum | 1 | 2/5 | 5 | 1 | per_copy | 243/15625 | 243/15625 | == | True | histories=count (6) |
| prop3_E[R|I=0] | 1 | 2/5 | 5 | 1 | per_copy | 1/5 | 1/5 | == | True | histories=count (6) |
| prop3_every_history_with_I=0 | 1 | 2/5 | 5 | 1 | per_copy | 1 | 1 | == | True | histories=count (6); count of distinct per-history optima |
| prop3_E[R|I=1] | 1 | 2/5 | 5 | 1 | per_copy | 0 | 0 | == | True | histories=count (6) |
| prop3_every_history_with_I=1 | 1 | 2/5 | 5 | 1 | per_copy | 1 | 1 | == | True | histories=count (6); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 1 | 2/5 | 5 | 1 | per_copy | 243/15625 | 243/15625 | == | True | histories=count (6); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 1 | 2/5 | 5 | 1 | per_copy | 0 | 0 | == | True | histories=count (6) |
| prop3_share_recovered | 1 | 2/5 | 5 | 1 | per_copy | 2882/3125 | 2882/3125 | == | True | histories=count (6) |
| prop3_history_optimum | 1 | 2/5 | 5 | 1 | per_copy | 243/15625 | 243/15625 | == | True | histories=full (32) |
| prop3_E[R|I=0] | 1 | 2/5 | 5 | 1 | per_copy | 1/5 | 1/5 | == | True | histories=full (32) |
| prop3_every_history_with_I=0 | 1 | 2/5 | 5 | 1 | per_copy | 1 | 1 | == | True | histories=full (32); count of distinct per-history optima |
| prop3_E[R|I=1] | 1 | 2/5 | 5 | 1 | per_copy | 0 | 0 | == | True | histories=full (32) |
| prop3_every_history_with_I=1 | 1 | 2/5 | 5 | 1 | per_copy | 1 | 1 | == | True | histories=full (32); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 1 | 2/5 | 5 | 1 | per_copy | 243/15625 | 243/15625 | == | True | histories=full (32); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 1 | 2/5 | 5 | 1 | per_copy | 0 | 0 | == | True | histories=full (32) |
| prop3_share_recovered | 1 | 2/5 | 5 | 1 | per_copy | 2882/3125 | 2882/3125 | == | True | histories=full (32) |
| prop3_full_vs_count_histories | 1 | 2/5 | 5 | 1 | per_copy | 243/15625 | 243/15625 | == | True |  |
| prop1_oblivious_optimum | 1 | 7/50 |  | 1 | pooled | 7/100 | 7/100 | == | True | 17 orbits / 28 schedules |
| prop1_posterior_optimum | 1 | 7/50 |  | 1 | pooled | 0 | 0 | == | True |  |
| prop1_hedge_all_A_max_R_over_realizations | 1 | 7/50 |  | 1 | pooled | 0 | 0 | == | True |  |
| prop1_oblivious_optimum | 1 | 7/50 |  | 1 | per_copy | 7/100 | 7/100 | == | True | 17 orbits / 28 schedules |
| prop1_posterior_optimum | 1 | 7/50 |  | 1 | per_copy | 0 | 0 | == | True |  |
| prop1_hedge_all_A_max_R_over_realizations | 1 | 7/50 |  | 1 | per_copy | 0 | 0 | == | True |  |
| gap_c | 1 | 7/50 |  | 0 | pooled | 0 | 0 | == | True |  |
| gap_c_oblivious_optimum | 1 | 7/50 |  | 0 | pooled | 7/50 | 7/50 | == | True |  |
| gap_c_posterior_optimum | 1 | 7/50 |  | 0 | pooled | 7/50 | 7/50 | == | True |  |
| gap_c | 1 | 7/50 |  | 1 | pooled | 7/100 | 7/100 | == | True |  |
| gap_c_oblivious_optimum | 1 | 7/50 |  | 1 | pooled | 7/100 | 7/100 | == | True |  |
| gap_c_posterior_optimum | 1 | 7/50 |  | 1 | pooled | 0 | 0 | == | True |  |
| gap_c | 1 | 7/50 |  | 2 | pooled | 0 | 0 | == | True |  |
| gap_c_oblivious_optimum | 1 | 7/50 |  | 2 | pooled | 0 | 0 | == | True |  |
| gap_c_posterior_optimum | 1 | 7/50 |  | 2 | pooled | 0 | 0 | == | True |  |
| gap_c | 1 | 7/50 |  | 0 | per_copy | 0 | 0 | == | True |  |
| gap_c_oblivious_optimum | 1 | 7/50 |  | 0 | per_copy | 7/50 | 7/50 | == | True |  |
| gap_c_posterior_optimum | 1 | 7/50 |  | 0 | per_copy | 7/50 | 7/50 | == | True |  |
| gap_c | 1 | 7/50 |  | 1 | per_copy | 7/100 | 7/100 | == | True |  |
| gap_c_oblivious_optimum | 1 | 7/50 |  | 1 | per_copy | 7/100 | 7/100 | == | True |  |
| gap_c_posterior_optimum | 1 | 7/50 |  | 1 | per_copy | 0 | 0 | == | True |  |
| gap_c | 1 | 7/50 |  | 2 | per_copy | 0 | 0 | == | True |  |
| gap_c_oblivious_optimum | 1 | 7/50 |  | 2 | per_copy | 0 | 0 | == | True |  |
| gap_c_posterior_optimum | 1 | 7/50 |  | 2 | per_copy | 0 | 0 | == | True |  |
| prop3_history_optimum | 1 | 7/50 | 0 | 1 | pooled | 7/100 | 7/100 | == | True | histories=count (1) |
| prop3_E[R|I=0] | 1 | 7/50 | 0 | 1 | pooled | 7/100 | 7/100 | == | True | histories=count (1) |
| prop3_every_history_with_I=0 | 1 | 7/50 | 0 | 1 | pooled | 1 | 1 | == | True | histories=count (1); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 1 | 7/50 | 0 | 1 | pooled | 7/100 | 7/100 | == | True | histories=count (1); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 1 | 7/50 | 0 | 1 | pooled | 0 | 0 | == | True | histories=count (1) |
| prop3_share_recovered_vs_f/(2-f) | 1 | 7/50 | 0 | 1 | pooled | 0 | 0 | >= | True | histories=count (1) |
| prop3_share_recovered_K1 | 1 | 7/50 | 0 | 1 | pooled | 0 | 0 | == | True | histories=count (1) |
| prop3_M0_equals_prop1 | 1 | 7/50 | 0 | 1 | pooled | 7/100 | 7/100 | == | True | histories=count (1); closed_form column = enumerated Prop 1 |
| prop3_history_optimum | 1 | 7/50 | 0 | 1 | pooled | 7/100 | 7/100 | == | True | histories=full (1) |
| prop3_E[R|I=0] | 1 | 7/50 | 0 | 1 | pooled | 7/100 | 7/100 | == | True | histories=full (1) |
| prop3_every_history_with_I=0 | 1 | 7/50 | 0 | 1 | pooled | 1 | 1 | == | True | histories=full (1); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 1 | 7/50 | 0 | 1 | pooled | 7/100 | 7/100 | == | True | histories=full (1); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 1 | 7/50 | 0 | 1 | pooled | 0 | 0 | == | True | histories=full (1) |
| prop3_share_recovered_vs_f/(2-f) | 1 | 7/50 | 0 | 1 | pooled | 0 | 0 | >= | True | histories=full (1) |
| prop3_share_recovered_K1 | 1 | 7/50 | 0 | 1 | pooled | 0 | 0 | == | True | histories=full (1) |
| prop3_M0_equals_prop1 | 1 | 7/50 | 0 | 1 | pooled | 7/100 | 7/100 | == | True | histories=full (1); closed_form column = enumerated Prop 1 |
| prop3_full_vs_count_histories | 1 | 7/50 | 0 | 1 | pooled | 7/100 | 7/100 | == | True |  |
| prop3_history_optimum | 1 | 7/50 | 0 | 1 | per_copy | 7/100 | 7/100 | == | True | histories=count (1) |
| prop3_E[R|I=0] | 1 | 7/50 | 0 | 1 | per_copy | 7/100 | 7/100 | == | True | histories=count (1) |
| prop3_every_history_with_I=0 | 1 | 7/50 | 0 | 1 | per_copy | 1 | 1 | == | True | histories=count (1); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 1 | 7/50 | 0 | 1 | per_copy | 7/100 | 7/100 | == | True | histories=count (1); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 1 | 7/50 | 0 | 1 | per_copy | 0 | 0 | == | True | histories=count (1) |
| prop3_share_recovered | 1 | 7/50 | 0 | 1 | per_copy | 0 | 0 | == | True | histories=count (1) |
| prop3_M0_equals_prop1 | 1 | 7/50 | 0 | 1 | per_copy | 7/100 | 7/100 | == | True | histories=count (1); closed_form column = enumerated Prop 1 |
| prop3_history_optimum | 1 | 7/50 | 0 | 1 | per_copy | 7/100 | 7/100 | == | True | histories=full (1) |
| prop3_E[R|I=0] | 1 | 7/50 | 0 | 1 | per_copy | 7/100 | 7/100 | == | True | histories=full (1) |
| prop3_every_history_with_I=0 | 1 | 7/50 | 0 | 1 | per_copy | 1 | 1 | == | True | histories=full (1); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 1 | 7/50 | 0 | 1 | per_copy | 7/100 | 7/100 | == | True | histories=full (1); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 1 | 7/50 | 0 | 1 | per_copy | 0 | 0 | == | True | histories=full (1) |
| prop3_share_recovered | 1 | 7/50 | 0 | 1 | per_copy | 0 | 0 | == | True | histories=full (1) |
| prop3_M0_equals_prop1 | 1 | 7/50 | 0 | 1 | per_copy | 7/100 | 7/100 | == | True | histories=full (1); closed_form column = enumerated Prop 1 |
| prop3_full_vs_count_histories | 1 | 7/50 | 0 | 1 | per_copy | 7/100 | 7/100 | == | True |  |
| prop3_history_optimum | 1 | 7/50 | 1 | 1 | pooled | 301/5000 | 301/5000 | == | True | histories=count (2) |
| prop3_E[R|I=0] | 1 | 7/50 | 1 | 1 | pooled | 7/100 | 7/100 | == | True | histories=count (2) |
| prop3_every_history_with_I=0 | 1 | 7/50 | 1 | 1 | pooled | 1 | 1 | == | True | histories=count (2); count of distinct per-history optima |
| prop3_E[R|I=1] | 1 | 7/50 | 1 | 1 | pooled | 0 | 0 | == | True | histories=count (2) |
| prop3_every_history_with_I=1 | 1 | 7/50 | 1 | 1 | pooled | 1 | 1 | == | True | histories=count (2); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 1 | 7/50 | 1 | 1 | pooled | 301/5000 | 301/5000 | == | True | histories=count (2); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 1 | 7/50 | 1 | 1 | pooled | 0 | 0 | == | True | histories=count (2) |
| prop3_share_recovered_vs_f/(2-f) | 1 | 7/50 | 1 | 1 | pooled | 7/50 | 7/93 | >= | True | histories=count (2) |
| prop3_share_recovered_K1 | 1 | 7/50 | 1 | 1 | pooled | 7/50 | 7/50 | == | True | histories=count (2) |
| prop3_history_optimum | 1 | 7/50 | 1 | 1 | pooled | 301/5000 | 301/5000 | == | True | histories=full (2) |
| prop3_E[R|I=0] | 1 | 7/50 | 1 | 1 | pooled | 7/100 | 7/100 | == | True | histories=full (2) |
| prop3_every_history_with_I=0 | 1 | 7/50 | 1 | 1 | pooled | 1 | 1 | == | True | histories=full (2); count of distinct per-history optima |
| prop3_E[R|I=1] | 1 | 7/50 | 1 | 1 | pooled | 0 | 0 | == | True | histories=full (2) |
| prop3_every_history_with_I=1 | 1 | 7/50 | 1 | 1 | pooled | 1 | 1 | == | True | histories=full (2); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 1 | 7/50 | 1 | 1 | pooled | 301/5000 | 301/5000 | == | True | histories=full (2); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 1 | 7/50 | 1 | 1 | pooled | 0 | 0 | == | True | histories=full (2) |
| prop3_share_recovered_vs_f/(2-f) | 1 | 7/50 | 1 | 1 | pooled | 7/50 | 7/93 | >= | True | histories=full (2) |
| prop3_share_recovered_K1 | 1 | 7/50 | 1 | 1 | pooled | 7/50 | 7/50 | == | True | histories=full (2) |
| prop3_full_vs_count_histories | 1 | 7/50 | 1 | 1 | pooled | 301/5000 | 301/5000 | == | True |  |
| prop3_history_optimum | 1 | 7/50 | 1 | 1 | per_copy | 301/5000 | 301/5000 | == | True | histories=count (2) |
| prop3_E[R|I=0] | 1 | 7/50 | 1 | 1 | per_copy | 7/100 | 7/100 | == | True | histories=count (2) |
| prop3_every_history_with_I=0 | 1 | 7/50 | 1 | 1 | per_copy | 1 | 1 | == | True | histories=count (2); count of distinct per-history optima |
| prop3_E[R|I=1] | 1 | 7/50 | 1 | 1 | per_copy | 0 | 0 | == | True | histories=count (2) |
| prop3_every_history_with_I=1 | 1 | 7/50 | 1 | 1 | per_copy | 1 | 1 | == | True | histories=count (2); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 1 | 7/50 | 1 | 1 | per_copy | 301/5000 | 301/5000 | == | True | histories=count (2); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 1 | 7/50 | 1 | 1 | per_copy | 0 | 0 | == | True | histories=count (2) |
| prop3_share_recovered | 1 | 7/50 | 1 | 1 | per_copy | 7/50 | 7/50 | == | True | histories=count (2) |
| prop3_history_optimum | 1 | 7/50 | 1 | 1 | per_copy | 301/5000 | 301/5000 | == | True | histories=full (2) |
| prop3_E[R|I=0] | 1 | 7/50 | 1 | 1 | per_copy | 7/100 | 7/100 | == | True | histories=full (2) |
| prop3_every_history_with_I=0 | 1 | 7/50 | 1 | 1 | per_copy | 1 | 1 | == | True | histories=full (2); count of distinct per-history optima |
| prop3_E[R|I=1] | 1 | 7/50 | 1 | 1 | per_copy | 0 | 0 | == | True | histories=full (2) |
| prop3_every_history_with_I=1 | 1 | 7/50 | 1 | 1 | per_copy | 1 | 1 | == | True | histories=full (2); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 1 | 7/50 | 1 | 1 | per_copy | 301/5000 | 301/5000 | == | True | histories=full (2); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 1 | 7/50 | 1 | 1 | per_copy | 0 | 0 | == | True | histories=full (2) |
| prop3_share_recovered | 1 | 7/50 | 1 | 1 | per_copy | 7/50 | 7/50 | == | True | histories=full (2) |
| prop3_full_vs_count_histories | 1 | 7/50 | 1 | 1 | per_copy | 301/5000 | 301/5000 | == | True |  |
| prop3_history_optimum | 1 | 7/50 | 2 | 1 | pooled | 12943/250000 | 12943/250000 | == | True | histories=count (3) |
| prop3_E[R|I=0] | 1 | 7/50 | 2 | 1 | pooled | 7/100 | 7/100 | == | True | histories=count (3) |
| prop3_every_history_with_I=0 | 1 | 7/50 | 2 | 1 | pooled | 1 | 1 | == | True | histories=count (3); count of distinct per-history optima |
| prop3_E[R|I=1] | 1 | 7/50 | 2 | 1 | pooled | 0 | 0 | == | True | histories=count (3) |
| prop3_every_history_with_I=1 | 1 | 7/50 | 2 | 1 | pooled | 1 | 1 | == | True | histories=count (3); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 1 | 7/50 | 2 | 1 | pooled | 12943/250000 | 12943/250000 | == | True | histories=count (3); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 1 | 7/50 | 2 | 1 | pooled | 0 | 0 | == | True | histories=count (3) |
| prop3_share_recovered_vs_f/(2-f) | 1 | 7/50 | 2 | 1 | pooled | 651/2500 | 651/4349 | >= | True | histories=count (3) |
| prop3_share_recovered_K1 | 1 | 7/50 | 2 | 1 | pooled | 651/2500 | 651/2500 | == | True | histories=count (3) |
| prop3_history_optimum | 1 | 7/50 | 2 | 1 | pooled | 12943/250000 | 12943/250000 | == | True | histories=full (4) |
| prop3_E[R|I=0] | 1 | 7/50 | 2 | 1 | pooled | 7/100 | 7/100 | == | True | histories=full (4) |
| prop3_every_history_with_I=0 | 1 | 7/50 | 2 | 1 | pooled | 1 | 1 | == | True | histories=full (4); count of distinct per-history optima |
| prop3_E[R|I=1] | 1 | 7/50 | 2 | 1 | pooled | 0 | 0 | == | True | histories=full (4) |
| prop3_every_history_with_I=1 | 1 | 7/50 | 2 | 1 | pooled | 1 | 1 | == | True | histories=full (4); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 1 | 7/50 | 2 | 1 | pooled | 12943/250000 | 12943/250000 | == | True | histories=full (4); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 1 | 7/50 | 2 | 1 | pooled | 0 | 0 | == | True | histories=full (4) |
| prop3_share_recovered_vs_f/(2-f) | 1 | 7/50 | 2 | 1 | pooled | 651/2500 | 651/4349 | >= | True | histories=full (4) |
| prop3_share_recovered_K1 | 1 | 7/50 | 2 | 1 | pooled | 651/2500 | 651/2500 | == | True | histories=full (4) |
| prop3_full_vs_count_histories | 1 | 7/50 | 2 | 1 | pooled | 12943/250000 | 12943/250000 | == | True |  |
| prop3_history_optimum | 1 | 7/50 | 2 | 1 | per_copy | 12943/250000 | 12943/250000 | == | True | histories=count (3) |
| prop3_E[R|I=0] | 1 | 7/50 | 2 | 1 | per_copy | 7/100 | 7/100 | == | True | histories=count (3) |
| prop3_every_history_with_I=0 | 1 | 7/50 | 2 | 1 | per_copy | 1 | 1 | == | True | histories=count (3); count of distinct per-history optima |
| prop3_E[R|I=1] | 1 | 7/50 | 2 | 1 | per_copy | 0 | 0 | == | True | histories=count (3) |
| prop3_every_history_with_I=1 | 1 | 7/50 | 2 | 1 | per_copy | 1 | 1 | == | True | histories=count (3); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 1 | 7/50 | 2 | 1 | per_copy | 12943/250000 | 12943/250000 | == | True | histories=count (3); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 1 | 7/50 | 2 | 1 | per_copy | 0 | 0 | == | True | histories=count (3) |
| prop3_share_recovered | 1 | 7/50 | 2 | 1 | per_copy | 651/2500 | 651/2500 | == | True | histories=count (3) |
| prop3_history_optimum | 1 | 7/50 | 2 | 1 | per_copy | 12943/250000 | 12943/250000 | == | True | histories=full (4) |
| prop3_E[R|I=0] | 1 | 7/50 | 2 | 1 | per_copy | 7/100 | 7/100 | == | True | histories=full (4) |
| prop3_every_history_with_I=0 | 1 | 7/50 | 2 | 1 | per_copy | 1 | 1 | == | True | histories=full (4); count of distinct per-history optima |
| prop3_E[R|I=1] | 1 | 7/50 | 2 | 1 | per_copy | 0 | 0 | == | True | histories=full (4) |
| prop3_every_history_with_I=1 | 1 | 7/50 | 2 | 1 | per_copy | 1 | 1 | == | True | histories=full (4); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 1 | 7/50 | 2 | 1 | per_copy | 12943/250000 | 12943/250000 | == | True | histories=full (4); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 1 | 7/50 | 2 | 1 | per_copy | 0 | 0 | == | True | histories=full (4) |
| prop3_share_recovered | 1 | 7/50 | 2 | 1 | per_copy | 651/2500 | 651/2500 | == | True | histories=full (4) |
| prop3_full_vs_count_histories | 1 | 7/50 | 2 | 1 | per_copy | 12943/250000 | 12943/250000 | == | True |  |
| prop3_history_optimum | 1 | 7/50 | 3 | 1 | pooled | 556549/12500000 | 556549/12500000 | == | True | histories=count (4) |
| prop3_E[R|I=0] | 1 | 7/50 | 3 | 1 | pooled | 7/100 | 7/100 | == | True | histories=count (4) |
| prop3_every_history_with_I=0 | 1 | 7/50 | 3 | 1 | pooled | 1 | 1 | == | True | histories=count (4); count of distinct per-history optima |
| prop3_E[R|I=1] | 1 | 7/50 | 3 | 1 | pooled | 0 | 0 | == | True | histories=count (4) |
| prop3_every_history_with_I=1 | 1 | 7/50 | 3 | 1 | pooled | 1 | 1 | == | True | histories=count (4); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 1 | 7/50 | 3 | 1 | pooled | 556549/12500000 | 556549/12500000 | == | True | histories=count (4); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 1 | 7/50 | 3 | 1 | pooled | 0 | 0 | == | True | histories=count (4) |
| prop3_share_recovered_vs_f/(2-f) | 1 | 7/50 | 3 | 1 | pooled | 45493/125000 | 45493/204507 | >= | True | histories=count (4) |
| prop3_share_recovered_K1 | 1 | 7/50 | 3 | 1 | pooled | 45493/125000 | 45493/125000 | == | True | histories=count (4) |
| prop3_history_optimum | 1 | 7/50 | 3 | 1 | pooled | 556549/12500000 | 556549/12500000 | == | True | histories=full (8) |
| prop3_E[R|I=0] | 1 | 7/50 | 3 | 1 | pooled | 7/100 | 7/100 | == | True | histories=full (8) |
| prop3_every_history_with_I=0 | 1 | 7/50 | 3 | 1 | pooled | 1 | 1 | == | True | histories=full (8); count of distinct per-history optima |
| prop3_E[R|I=1] | 1 | 7/50 | 3 | 1 | pooled | 0 | 0 | == | True | histories=full (8) |
| prop3_every_history_with_I=1 | 1 | 7/50 | 3 | 1 | pooled | 1 | 1 | == | True | histories=full (8); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 1 | 7/50 | 3 | 1 | pooled | 556549/12500000 | 556549/12500000 | == | True | histories=full (8); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 1 | 7/50 | 3 | 1 | pooled | 0 | 0 | == | True | histories=full (8) |
| prop3_share_recovered_vs_f/(2-f) | 1 | 7/50 | 3 | 1 | pooled | 45493/125000 | 45493/204507 | >= | True | histories=full (8) |
| prop3_share_recovered_K1 | 1 | 7/50 | 3 | 1 | pooled | 45493/125000 | 45493/125000 | == | True | histories=full (8) |
| prop3_full_vs_count_histories | 1 | 7/50 | 3 | 1 | pooled | 556549/12500000 | 556549/12500000 | == | True |  |
| prop3_history_optimum | 1 | 7/50 | 3 | 1 | per_copy | 556549/12500000 | 556549/12500000 | == | True | histories=count (4) |
| prop3_E[R|I=0] | 1 | 7/50 | 3 | 1 | per_copy | 7/100 | 7/100 | == | True | histories=count (4) |
| prop3_every_history_with_I=0 | 1 | 7/50 | 3 | 1 | per_copy | 1 | 1 | == | True | histories=count (4); count of distinct per-history optima |
| prop3_E[R|I=1] | 1 | 7/50 | 3 | 1 | per_copy | 0 | 0 | == | True | histories=count (4) |
| prop3_every_history_with_I=1 | 1 | 7/50 | 3 | 1 | per_copy | 1 | 1 | == | True | histories=count (4); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 1 | 7/50 | 3 | 1 | per_copy | 556549/12500000 | 556549/12500000 | == | True | histories=count (4); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 1 | 7/50 | 3 | 1 | per_copy | 0 | 0 | == | True | histories=count (4) |
| prop3_share_recovered | 1 | 7/50 | 3 | 1 | per_copy | 45493/125000 | 45493/125000 | == | True | histories=count (4) |
| prop3_history_optimum | 1 | 7/50 | 3 | 1 | per_copy | 556549/12500000 | 556549/12500000 | == | True | histories=full (8) |
| prop3_E[R|I=0] | 1 | 7/50 | 3 | 1 | per_copy | 7/100 | 7/100 | == | True | histories=full (8) |
| prop3_every_history_with_I=0 | 1 | 7/50 | 3 | 1 | per_copy | 1 | 1 | == | True | histories=full (8); count of distinct per-history optima |
| prop3_E[R|I=1] | 1 | 7/50 | 3 | 1 | per_copy | 0 | 0 | == | True | histories=full (8) |
| prop3_every_history_with_I=1 | 1 | 7/50 | 3 | 1 | per_copy | 1 | 1 | == | True | histories=full (8); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 1 | 7/50 | 3 | 1 | per_copy | 556549/12500000 | 556549/12500000 | == | True | histories=full (8); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 1 | 7/50 | 3 | 1 | per_copy | 0 | 0 | == | True | histories=full (8) |
| prop3_share_recovered | 1 | 7/50 | 3 | 1 | per_copy | 45493/125000 | 45493/125000 | == | True | histories=full (8) |
| prop3_full_vs_count_histories | 1 | 7/50 | 3 | 1 | per_copy | 556549/12500000 | 556549/12500000 | == | True |  |
| prop3_history_optimum | 1 | 7/50 | 5 | 1 | pooled | 1029059101/31250000000 | 1029059101/31250000000 | == | True | histories=count (6) |
| prop3_E[R|I=0] | 1 | 7/50 | 5 | 1 | pooled | 7/100 | 7/100 | == | True | histories=count (6) |
| prop3_every_history_with_I=0 | 1 | 7/50 | 5 | 1 | pooled | 1 | 1 | == | True | histories=count (6); count of distinct per-history optima |
| prop3_E[R|I=1] | 1 | 7/50 | 5 | 1 | pooled | 0 | 0 | == | True | histories=count (6) |
| prop3_every_history_with_I=1 | 1 | 7/50 | 5 | 1 | pooled | 1 | 1 | == | True | histories=count (6); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 1 | 7/50 | 5 | 1 | pooled | 1029059101/31250000000 | 1029059101/31250000000 | == | True | histories=count (6); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 1 | 7/50 | 5 | 1 | pooled | 0 | 0 | == | True | histories=count (6) |
| prop3_share_recovered_vs_f/(2-f) | 1 | 7/50 | 5 | 1 | pooled | 165491557/312500000 | 165491557/459508443 | >= | True | histories=count (6) |
| prop3_share_recovered_K1 | 1 | 7/50 | 5 | 1 | pooled | 165491557/312500000 | 165491557/312500000 | == | True | histories=count (6) |
| prop3_history_optimum | 1 | 7/50 | 5 | 1 | pooled | 1029059101/31250000000 | 1029059101/31250000000 | == | True | histories=full (32) |
| prop3_E[R|I=0] | 1 | 7/50 | 5 | 1 | pooled | 7/100 | 7/100 | == | True | histories=full (32) |
| prop3_every_history_with_I=0 | 1 | 7/50 | 5 | 1 | pooled | 1 | 1 | == | True | histories=full (32); count of distinct per-history optima |
| prop3_E[R|I=1] | 1 | 7/50 | 5 | 1 | pooled | 0 | 0 | == | True | histories=full (32) |
| prop3_every_history_with_I=1 | 1 | 7/50 | 5 | 1 | pooled | 1 | 1 | == | True | histories=full (32); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 1 | 7/50 | 5 | 1 | pooled | 1029059101/31250000000 | 1029059101/31250000000 | == | True | histories=full (32); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 1 | 7/50 | 5 | 1 | pooled | 0 | 0 | == | True | histories=full (32) |
| prop3_share_recovered_vs_f/(2-f) | 1 | 7/50 | 5 | 1 | pooled | 165491557/312500000 | 165491557/459508443 | >= | True | histories=full (32) |
| prop3_share_recovered_K1 | 1 | 7/50 | 5 | 1 | pooled | 165491557/312500000 | 165491557/312500000 | == | True | histories=full (32) |
| prop3_full_vs_count_histories | 1 | 7/50 | 5 | 1 | pooled | 1029059101/31250000000 | 1029059101/31250000000 | == | True |  |
| prop3_history_optimum | 1 | 7/50 | 5 | 1 | per_copy | 1029059101/31250000000 | 1029059101/31250000000 | == | True | histories=count (6) |
| prop3_E[R|I=0] | 1 | 7/50 | 5 | 1 | per_copy | 7/100 | 7/100 | == | True | histories=count (6) |
| prop3_every_history_with_I=0 | 1 | 7/50 | 5 | 1 | per_copy | 1 | 1 | == | True | histories=count (6); count of distinct per-history optima |
| prop3_E[R|I=1] | 1 | 7/50 | 5 | 1 | per_copy | 0 | 0 | == | True | histories=count (6) |
| prop3_every_history_with_I=1 | 1 | 7/50 | 5 | 1 | per_copy | 1 | 1 | == | True | histories=count (6); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 1 | 7/50 | 5 | 1 | per_copy | 1029059101/31250000000 | 1029059101/31250000000 | == | True | histories=count (6); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 1 | 7/50 | 5 | 1 | per_copy | 0 | 0 | == | True | histories=count (6) |
| prop3_share_recovered | 1 | 7/50 | 5 | 1 | per_copy | 165491557/312500000 | 165491557/312500000 | == | True | histories=count (6) |
| prop3_history_optimum | 1 | 7/50 | 5 | 1 | per_copy | 1029059101/31250000000 | 1029059101/31250000000 | == | True | histories=full (32) |
| prop3_E[R|I=0] | 1 | 7/50 | 5 | 1 | per_copy | 7/100 | 7/100 | == | True | histories=full (32) |
| prop3_every_history_with_I=0 | 1 | 7/50 | 5 | 1 | per_copy | 1 | 1 | == | True | histories=full (32); count of distinct per-history optima |
| prop3_E[R|I=1] | 1 | 7/50 | 5 | 1 | per_copy | 0 | 0 | == | True | histories=full (32) |
| prop3_every_history_with_I=1 | 1 | 7/50 | 5 | 1 | per_copy | 1 | 1 | == | True | histories=full (32); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 1 | 7/50 | 5 | 1 | per_copy | 1029059101/31250000000 | 1029059101/31250000000 | == | True | histories=full (32); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 1 | 7/50 | 5 | 1 | per_copy | 0 | 0 | == | True | histories=full (32) |
| prop3_share_recovered | 1 | 7/50 | 5 | 1 | per_copy | 165491557/312500000 | 165491557/312500000 | == | True | histories=full (32) |
| prop3_full_vs_count_histories | 1 | 7/50 | 5 | 1 | per_copy | 1029059101/31250000000 | 1029059101/31250000000 | == | True |  |
| prop1_oblivious_optimum | 2 | 1/2 |  | 2 | pooled | 1/2 | 1/2 | == | True | 117 orbits / 912 schedules |
| prop1_posterior_optimum | 2 | 1/2 |  | 2 | pooled | 0 | 0 | == | True |  |
| prop1_hedge_all_A_max_R_over_realizations | 2 | 1/2 |  | 2 | pooled | 0 | 0 | == | True |  |
| prop1_oblivious_optimum | 2 | 1/2 |  | 2 | per_copy | 1/2 | 1/2 | == | True | 153 orbits / 784 schedules |
| prop1_posterior_optimum | 2 | 1/2 |  | 2 | per_copy | 0 | 0 | == | True |  |
| prop1_hedge_all_A_max_R_over_realizations | 2 | 1/2 |  | 2 | per_copy | 0 | 0 | == | True |  |
| gap_c | 2 | 1/2 |  | 0 | pooled | 0 | 0 | == | True |  |
| gap_c_oblivious_optimum | 2 | 1/2 |  | 0 | pooled | 1 | 1 | == | True |  |
| gap_c_posterior_optimum | 2 | 1/2 |  | 0 | pooled | 1 | 1 | == | True |  |
| gap_c | 2 | 1/2 |  | 1 | pooled | 1/4 | 1/4 | == | True |  |
| gap_c_oblivious_optimum | 2 | 1/2 |  | 1 | pooled | 3/4 | 3/4 | == | True |  |
| gap_c_posterior_optimum | 2 | 1/2 |  | 1 | pooled | 1/2 | 1/2 | == | True |  |
| gap_c | 2 | 1/2 |  | 2 | pooled | 1/2 | 1/2 | == | True |  |
| gap_c_oblivious_optimum | 2 | 1/2 |  | 2 | pooled | 1/2 | 1/2 | == | True |  |
| gap_c_posterior_optimum | 2 | 1/2 |  | 2 | pooled | 0 | 0 | == | True |  |
| gap_c | 2 | 1/2 |  | 3 | pooled | 1/4 | 1/4 | == | True |  |
| gap_c_oblivious_optimum | 2 | 1/2 |  | 3 | pooled | 1/4 | 1/4 | == | True |  |
| gap_c_posterior_optimum | 2 | 1/2 |  | 3 | pooled | 0 | 0 | == | True |  |
| gap_c | 2 | 1/2 |  | 4 | pooled | 0 | 0 | == | True |  |
| gap_c_oblivious_optimum | 2 | 1/2 |  | 4 | pooled | 0 | 0 | == | True |  |
| gap_c_posterior_optimum | 2 | 1/2 |  | 4 | pooled | 0 | 0 | == | True |  |
| gap_c | 2 | 1/2 |  | 0 | per_copy | 0 | 0 | == | True |  |
| gap_c_oblivious_optimum | 2 | 1/2 |  | 0 | per_copy | 1 | 1 | == | True |  |
| gap_c_posterior_optimum | 2 | 1/2 |  | 0 | per_copy | 1 | 1 | == | True |  |
| gap_c | 2 | 1/2 |  | 2 | per_copy | 1/2 | 1/2 | == | True |  |
| gap_c_oblivious_optimum | 2 | 1/2 |  | 2 | per_copy | 1/2 | 1/2 | == | True |  |
| gap_c_posterior_optimum | 2 | 1/2 |  | 2 | per_copy | 0 | 0 | == | True |  |
| gap_c | 2 | 1/2 |  | 4 | per_copy | 0 | 0 | == | True |  |
| gap_c_oblivious_optimum | 2 | 1/2 |  | 4 | per_copy | 0 | 0 | == | True |  |
| gap_c_posterior_optimum | 2 | 1/2 |  | 4 | per_copy | 0 | 0 | == | True |  |
| prop3_history_optimum | 2 | 1/2 | 0 | 2 | pooled | 1/2 | 1/2 | == | True | histories=count (1) |
| prop3_E[R|I=0] | 2 | 1/2 | 0 | 2 | pooled | 1/2 | 1/2 | == | True | histories=count (1) |
| prop3_every_history_with_I=0 | 2 | 1/2 | 0 | 2 | pooled | 1 | 1 | == | True | histories=count (1); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 2 | 1/2 | 0 | 2 | pooled | 1/2 | 1/2 | == | True | histories=count (1); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 2 | 1/2 | 0 | 2 | pooled | 0 | 0 | == | True | histories=count (1) |
| prop3_share_recovered_vs_f/(2-f) | 2 | 1/2 | 0 | 2 | pooled | 0 | 0 | >= | True | histories=count (1) |
| prop3_M0_equals_prop1 | 2 | 1/2 | 0 | 2 | pooled | 1/2 | 1/2 | == | True | histories=count (1); closed_form column = enumerated Prop 1 |
| prop3_history_optimum | 2 | 1/2 | 0 | 2 | pooled | 1/2 | 1/2 | == | True | histories=full (1) |
| prop3_E[R|I=0] | 2 | 1/2 | 0 | 2 | pooled | 1/2 | 1/2 | == | True | histories=full (1) |
| prop3_every_history_with_I=0 | 2 | 1/2 | 0 | 2 | pooled | 1 | 1 | == | True | histories=full (1); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 2 | 1/2 | 0 | 2 | pooled | 1/2 | 1/2 | == | True | histories=full (1); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 2 | 1/2 | 0 | 2 | pooled | 0 | 0 | == | True | histories=full (1) |
| prop3_share_recovered_vs_f/(2-f) | 2 | 1/2 | 0 | 2 | pooled | 0 | 0 | >= | True | histories=full (1) |
| prop3_M0_equals_prop1 | 2 | 1/2 | 0 | 2 | pooled | 1/2 | 1/2 | == | True | histories=full (1); closed_form column = enumerated Prop 1 |
| prop3_full_vs_count_histories | 2 | 1/2 | 0 | 2 | pooled | 1/2 | 1/2 | == | True |  |
| prop3_history_optimum | 2 | 1/2 | 0 | 2 | per_copy | 1/2 | 1/2 | == | True | histories=count (1) |
| prop3_E[R|I=0] | 2 | 1/2 | 0 | 2 | per_copy | 1/2 | 1/2 | == | True | histories=count (1) |
| prop3_every_history_with_I=0 | 2 | 1/2 | 0 | 2 | per_copy | 1 | 1 | == | True | histories=count (1); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 2 | 1/2 | 0 | 2 | per_copy | 1/2 | 1/2 | == | True | histories=count (1); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 2 | 1/2 | 0 | 2 | per_copy | 0 | 0 | == | True | histories=count (1) |
| prop3_share_recovered | 2 | 1/2 | 0 | 2 | per_copy | 0 | 0 | == | True | histories=count (1) |
| prop3_M0_equals_prop1 | 2 | 1/2 | 0 | 2 | per_copy | 1/2 | 1/2 | == | True | histories=count (1); closed_form column = enumerated Prop 1 |
| prop3_history_optimum | 2 | 1/2 | 0 | 2 | per_copy | 1/2 | 1/2 | == | True | histories=full (1) |
| prop3_E[R|I=0] | 2 | 1/2 | 0 | 2 | per_copy | 1/2 | 1/2 | == | True | histories=full (1) |
| prop3_every_history_with_I=0 | 2 | 1/2 | 0 | 2 | per_copy | 1 | 1 | == | True | histories=full (1); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 2 | 1/2 | 0 | 2 | per_copy | 1/2 | 1/2 | == | True | histories=full (1); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 2 | 1/2 | 0 | 2 | per_copy | 0 | 0 | == | True | histories=full (1) |
| prop3_share_recovered | 2 | 1/2 | 0 | 2 | per_copy | 0 | 0 | == | True | histories=full (1) |
| prop3_M0_equals_prop1 | 2 | 1/2 | 0 | 2 | per_copy | 1/2 | 1/2 | == | True | histories=full (1); closed_form column = enumerated Prop 1 |
| prop3_full_vs_count_histories | 2 | 1/2 | 0 | 2 | per_copy | 1/2 | 1/2 | == | True |  |
| prop3_history_optimum | 2 | 1/2 | 1 | 2 | pooled | 7/24 | 7/24 | == | True | histories=count (4) |
| prop3_E[R|I=0] | 2 | 1/2 | 1 | 2 | pooled | 1/2 | 1/2 | == | True | histories=count (4) |
| prop3_every_history_with_I=0 | 2 | 1/2 | 1 | 2 | pooled | 1 | 1 | == | True | histories=count (4); count of distinct per-history optima |
| prop3_E[R|I=1] | 2 | 1/2 | 1 | 2 | pooled | 1/3 | 1/3 | == | True | histories=count (4) |
| prop3_every_history_with_I=1 | 2 | 1/2 | 1 | 2 | pooled | 1 | 1 | == | True | histories=count (4); count of distinct per-history optima |
| prop3_E[R|I=2] | 2 | 1/2 | 1 | 2 | pooled | 0 | 0 | == | True | histories=count (4) |
| prop3_every_history_with_I=2 | 2 | 1/2 | 1 | 2 | pooled | 1 | 1 | == | True | histories=count (4); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 2 | 1/2 | 1 | 2 | pooled | 7/24 | 7/24 | == | True | histories=count (4); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 2 | 1/2 | 1 | 2 | pooled | 0 | 0 | == | True | histories=count (4) |
| prop3_share_recovered_vs_f/(2-f) | 2 | 1/2 | 1 | 2 | pooled | 5/12 | 1/3 | >= | True | histories=count (4) |
| prop3_history_optimum | 2 | 1/2 | 1 | 2 | pooled | 7/24 | 7/24 | == | True | histories=full (4) |
| prop3_E[R|I=0] | 2 | 1/2 | 1 | 2 | pooled | 1/2 | 1/2 | == | True | histories=full (4) |
| prop3_every_history_with_I=0 | 2 | 1/2 | 1 | 2 | pooled | 1 | 1 | == | True | histories=full (4); count of distinct per-history optima |
| prop3_E[R|I=1] | 2 | 1/2 | 1 | 2 | pooled | 1/3 | 1/3 | == | True | histories=full (4) |
| prop3_every_history_with_I=1 | 2 | 1/2 | 1 | 2 | pooled | 1 | 1 | == | True | histories=full (4); count of distinct per-history optima |
| prop3_E[R|I=2] | 2 | 1/2 | 1 | 2 | pooled | 0 | 0 | == | True | histories=full (4) |
| prop3_every_history_with_I=2 | 2 | 1/2 | 1 | 2 | pooled | 1 | 1 | == | True | histories=full (4); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 2 | 1/2 | 1 | 2 | pooled | 7/24 | 7/24 | == | True | histories=full (4); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 2 | 1/2 | 1 | 2 | pooled | 0 | 0 | == | True | histories=full (4) |
| prop3_share_recovered_vs_f/(2-f) | 2 | 1/2 | 1 | 2 | pooled | 5/12 | 1/3 | >= | True | histories=full (4) |
| prop3_full_vs_count_histories | 2 | 1/2 | 1 | 2 | pooled | 7/24 | 7/24 | == | True |  |
| prop3_history_optimum | 2 | 1/2 | 1 | 2 | per_copy | 1/4 | 1/4 | == | True | histories=count (4) |
| prop3_E[R|I=0] | 2 | 1/2 | 1 | 2 | per_copy | 1/2 | 1/2 | == | True | histories=count (4) |
| prop3_every_history_with_I=0 | 2 | 1/2 | 1 | 2 | per_copy | 1 | 1 | == | True | histories=count (4); count of distinct per-history optima |
| prop3_E[R|I=1] | 2 | 1/2 | 1 | 2 | per_copy | 1/4 | 1/4 | == | True | histories=count (4) |
| prop3_every_history_with_I=1 | 2 | 1/2 | 1 | 2 | per_copy | 1 | 1 | == | True | histories=count (4); count of distinct per-history optima |
| prop3_E[R|I=2] | 2 | 1/2 | 1 | 2 | per_copy | 0 | 0 | == | True | histories=count (4) |
| prop3_every_history_with_I=2 | 2 | 1/2 | 1 | 2 | per_copy | 1 | 1 | == | True | histories=count (4); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 2 | 1/2 | 1 | 2 | per_copy | 1/4 | 1/4 | == | True | histories=count (4); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 2 | 1/2 | 1 | 2 | per_copy | 0 | 0 | == | True | histories=count (4) |
| prop3_share_recovered | 2 | 1/2 | 1 | 2 | per_copy | 1/2 | 1/2 | == | True | histories=count (4) |
| prop3_history_optimum | 2 | 1/2 | 1 | 2 | per_copy | 1/4 | 1/4 | == | True | histories=full (4) |
| prop3_E[R|I=0] | 2 | 1/2 | 1 | 2 | per_copy | 1/2 | 1/2 | == | True | histories=full (4) |
| prop3_every_history_with_I=0 | 2 | 1/2 | 1 | 2 | per_copy | 1 | 1 | == | True | histories=full (4); count of distinct per-history optima |
| prop3_E[R|I=1] | 2 | 1/2 | 1 | 2 | per_copy | 1/4 | 1/4 | == | True | histories=full (4) |
| prop3_every_history_with_I=1 | 2 | 1/2 | 1 | 2 | per_copy | 1 | 1 | == | True | histories=full (4); count of distinct per-history optima |
| prop3_E[R|I=2] | 2 | 1/2 | 1 | 2 | per_copy | 0 | 0 | == | True | histories=full (4) |
| prop3_every_history_with_I=2 | 2 | 1/2 | 1 | 2 | per_copy | 1 | 1 | == | True | histories=full (4); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 2 | 1/2 | 1 | 2 | per_copy | 1/4 | 1/4 | == | True | histories=full (4); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 2 | 1/2 | 1 | 2 | per_copy | 0 | 0 | == | True | histories=full (4) |
| prop3_share_recovered | 2 | 1/2 | 1 | 2 | per_copy | 1/2 | 1/2 | == | True | histories=full (4) |
| prop3_full_vs_count_histories | 2 | 1/2 | 1 | 2 | per_copy | 1/4 | 1/4 | == | True |  |
| prop3_history_optimum | 2 | 1/2 | 2 | 2 | pooled | 5/32 | 5/32 | == | True | histories=count (9) |
| prop3_E[R|I=0] | 2 | 1/2 | 2 | 2 | pooled | 1/2 | 1/2 | == | True | histories=count (9) |
| prop3_every_history_with_I=0 | 2 | 1/2 | 2 | 2 | pooled | 1 | 1 | == | True | histories=count (9); count of distinct per-history optima |
| prop3_E[R|I=1] | 2 | 1/2 | 2 | 2 | pooled | 1/3 | 1/3 | == | True | histories=count (9) |
| prop3_every_history_with_I=1 | 2 | 1/2 | 2 | 2 | pooled | 1 | 1 | == | True | histories=count (9); count of distinct per-history optima |
| prop3_E[R|I=2] | 2 | 1/2 | 2 | 2 | pooled | 0 | 0 | == | True | histories=count (9) |
| prop3_every_history_with_I=2 | 2 | 1/2 | 2 | 2 | pooled | 1 | 1 | == | True | histories=count (9); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 2 | 1/2 | 2 | 2 | pooled | 5/32 | 5/32 | == | True | histories=count (9); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 2 | 1/2 | 2 | 2 | pooled | 0 | 0 | == | True | histories=count (9) |
| prop3_share_recovered_vs_f/(2-f) | 2 | 1/2 | 2 | 2 | pooled | 11/16 | 3/5 | >= | True | histories=count (9) |
| prop3_history_optimum | 2 | 1/2 | 2 | 2 | pooled | 5/32 | 5/32 | == | True | histories=full (16) |
| prop3_E[R|I=0] | 2 | 1/2 | 2 | 2 | pooled | 1/2 | 1/2 | == | True | histories=full (16) |
| prop3_every_history_with_I=0 | 2 | 1/2 | 2 | 2 | pooled | 1 | 1 | == | True | histories=full (16); count of distinct per-history optima |
| prop3_E[R|I=1] | 2 | 1/2 | 2 | 2 | pooled | 1/3 | 1/3 | == | True | histories=full (16) |
| prop3_every_history_with_I=1 | 2 | 1/2 | 2 | 2 | pooled | 1 | 1 | == | True | histories=full (16); count of distinct per-history optima |
| prop3_E[R|I=2] | 2 | 1/2 | 2 | 2 | pooled | 0 | 0 | == | True | histories=full (16) |
| prop3_every_history_with_I=2 | 2 | 1/2 | 2 | 2 | pooled | 1 | 1 | == | True | histories=full (16); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 2 | 1/2 | 2 | 2 | pooled | 5/32 | 5/32 | == | True | histories=full (16); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 2 | 1/2 | 2 | 2 | pooled | 0 | 0 | == | True | histories=full (16) |
| prop3_share_recovered_vs_f/(2-f) | 2 | 1/2 | 2 | 2 | pooled | 11/16 | 3/5 | >= | True | histories=full (16) |
| prop3_full_vs_count_histories | 2 | 1/2 | 2 | 2 | pooled | 5/32 | 5/32 | == | True |  |
| prop3_history_optimum | 2 | 1/2 | 2 | 2 | per_copy | 1/8 | 1/8 | == | True | histories=count (9) |
| prop3_E[R|I=0] | 2 | 1/2 | 2 | 2 | per_copy | 1/2 | 1/2 | == | True | histories=count (9) |
| prop3_every_history_with_I=0 | 2 | 1/2 | 2 | 2 | per_copy | 1 | 1 | == | True | histories=count (9); count of distinct per-history optima |
| prop3_E[R|I=1] | 2 | 1/2 | 2 | 2 | per_copy | 1/4 | 1/4 | == | True | histories=count (9) |
| prop3_every_history_with_I=1 | 2 | 1/2 | 2 | 2 | per_copy | 1 | 1 | == | True | histories=count (9); count of distinct per-history optima |
| prop3_E[R|I=2] | 2 | 1/2 | 2 | 2 | per_copy | 0 | 0 | == | True | histories=count (9) |
| prop3_every_history_with_I=2 | 2 | 1/2 | 2 | 2 | per_copy | 1 | 1 | == | True | histories=count (9); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 2 | 1/2 | 2 | 2 | per_copy | 1/8 | 1/8 | == | True | histories=count (9); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 2 | 1/2 | 2 | 2 | per_copy | 0 | 0 | == | True | histories=count (9) |
| prop3_share_recovered | 2 | 1/2 | 2 | 2 | per_copy | 3/4 | 3/4 | == | True | histories=count (9) |
| prop3_history_optimum | 2 | 1/2 | 2 | 2 | per_copy | 1/8 | 1/8 | == | True | histories=full (16) |
| prop3_E[R|I=0] | 2 | 1/2 | 2 | 2 | per_copy | 1/2 | 1/2 | == | True | histories=full (16) |
| prop3_every_history_with_I=0 | 2 | 1/2 | 2 | 2 | per_copy | 1 | 1 | == | True | histories=full (16); count of distinct per-history optima |
| prop3_E[R|I=1] | 2 | 1/2 | 2 | 2 | per_copy | 1/4 | 1/4 | == | True | histories=full (16) |
| prop3_every_history_with_I=1 | 2 | 1/2 | 2 | 2 | per_copy | 1 | 1 | == | True | histories=full (16); count of distinct per-history optima |
| prop3_E[R|I=2] | 2 | 1/2 | 2 | 2 | per_copy | 0 | 0 | == | True | histories=full (16) |
| prop3_every_history_with_I=2 | 2 | 1/2 | 2 | 2 | per_copy | 1 | 1 | == | True | histories=full (16); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 2 | 1/2 | 2 | 2 | per_copy | 1/8 | 1/8 | == | True | histories=full (16); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 2 | 1/2 | 2 | 2 | per_copy | 0 | 0 | == | True | histories=full (16) |
| prop3_share_recovered | 2 | 1/2 | 2 | 2 | per_copy | 3/4 | 3/4 | == | True | histories=full (16) |
| prop3_full_vs_count_histories | 2 | 1/2 | 2 | 2 | per_copy | 1/8 | 1/8 | == | True |  |
| prop3_history_optimum | 2 | 1/2 | 3 | 2 | pooled | 31/384 | 31/384 | == | True | histories=count (16) |
| prop3_E[R|I=0] | 2 | 1/2 | 3 | 2 | pooled | 1/2 | 1/2 | == | True | histories=count (16) |
| prop3_every_history_with_I=0 | 2 | 1/2 | 3 | 2 | pooled | 1 | 1 | == | True | histories=count (16); count of distinct per-history optima |
| prop3_E[R|I=1] | 2 | 1/2 | 3 | 2 | pooled | 1/3 | 1/3 | == | True | histories=count (16) |
| prop3_every_history_with_I=1 | 2 | 1/2 | 3 | 2 | pooled | 1 | 1 | == | True | histories=count (16); count of distinct per-history optima |
| prop3_E[R|I=2] | 2 | 1/2 | 3 | 2 | pooled | 0 | 0 | == | True | histories=count (16) |
| prop3_every_history_with_I=2 | 2 | 1/2 | 3 | 2 | pooled | 1 | 1 | == | True | histories=count (16); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 2 | 1/2 | 3 | 2 | pooled | 31/384 | 31/384 | == | True | histories=count (16); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 2 | 1/2 | 3 | 2 | pooled | 0 | 0 | == | True | histories=count (16) |
| prop3_share_recovered_vs_f/(2-f) | 2 | 1/2 | 3 | 2 | pooled | 161/192 | 7/9 | >= | True | histories=count (16) |
| prop3_history_optimum | 2 | 1/2 | 3 | 2 | pooled | 31/384 | 31/384 | == | True | histories=full (64) |
| prop3_E[R|I=0] | 2 | 1/2 | 3 | 2 | pooled | 1/2 | 1/2 | == | True | histories=full (64) |
| prop3_every_history_with_I=0 | 2 | 1/2 | 3 | 2 | pooled | 1 | 1 | == | True | histories=full (64); count of distinct per-history optima |
| prop3_E[R|I=1] | 2 | 1/2 | 3 | 2 | pooled | 1/3 | 1/3 | == | True | histories=full (64) |
| prop3_every_history_with_I=1 | 2 | 1/2 | 3 | 2 | pooled | 1 | 1 | == | True | histories=full (64); count of distinct per-history optima |
| prop3_E[R|I=2] | 2 | 1/2 | 3 | 2 | pooled | 0 | 0 | == | True | histories=full (64) |
| prop3_every_history_with_I=2 | 2 | 1/2 | 3 | 2 | pooled | 1 | 1 | == | True | histories=full (64); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 2 | 1/2 | 3 | 2 | pooled | 31/384 | 31/384 | == | True | histories=full (64); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 2 | 1/2 | 3 | 2 | pooled | 0 | 0 | == | True | histories=full (64) |
| prop3_share_recovered_vs_f/(2-f) | 2 | 1/2 | 3 | 2 | pooled | 161/192 | 7/9 | >= | True | histories=full (64) |
| prop3_full_vs_count_histories | 2 | 1/2 | 3 | 2 | pooled | 31/384 | 31/384 | == | True |  |
| prop3_history_optimum | 2 | 1/2 | 3 | 2 | per_copy | 1/16 | 1/16 | == | True | histories=count (16) |
| prop3_E[R|I=0] | 2 | 1/2 | 3 | 2 | per_copy | 1/2 | 1/2 | == | True | histories=count (16) |
| prop3_every_history_with_I=0 | 2 | 1/2 | 3 | 2 | per_copy | 1 | 1 | == | True | histories=count (16); count of distinct per-history optima |
| prop3_E[R|I=1] | 2 | 1/2 | 3 | 2 | per_copy | 1/4 | 1/4 | == | True | histories=count (16) |
| prop3_every_history_with_I=1 | 2 | 1/2 | 3 | 2 | per_copy | 1 | 1 | == | True | histories=count (16); count of distinct per-history optima |
| prop3_E[R|I=2] | 2 | 1/2 | 3 | 2 | per_copy | 0 | 0 | == | True | histories=count (16) |
| prop3_every_history_with_I=2 | 2 | 1/2 | 3 | 2 | per_copy | 1 | 1 | == | True | histories=count (16); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 2 | 1/2 | 3 | 2 | per_copy | 1/16 | 1/16 | == | True | histories=count (16); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 2 | 1/2 | 3 | 2 | per_copy | 0 | 0 | == | True | histories=count (16) |
| prop3_share_recovered | 2 | 1/2 | 3 | 2 | per_copy | 7/8 | 7/8 | == | True | histories=count (16) |
| prop3_history_optimum | 2 | 1/2 | 3 | 2 | per_copy | 1/16 | 1/16 | == | True | histories=full (64) |
| prop3_E[R|I=0] | 2 | 1/2 | 3 | 2 | per_copy | 1/2 | 1/2 | == | True | histories=full (64) |
| prop3_every_history_with_I=0 | 2 | 1/2 | 3 | 2 | per_copy | 1 | 1 | == | True | histories=full (64); count of distinct per-history optima |
| prop3_E[R|I=1] | 2 | 1/2 | 3 | 2 | per_copy | 1/4 | 1/4 | == | True | histories=full (64) |
| prop3_every_history_with_I=1 | 2 | 1/2 | 3 | 2 | per_copy | 1 | 1 | == | True | histories=full (64); count of distinct per-history optima |
| prop3_E[R|I=2] | 2 | 1/2 | 3 | 2 | per_copy | 0 | 0 | == | True | histories=full (64) |
| prop3_every_history_with_I=2 | 2 | 1/2 | 3 | 2 | per_copy | 1 | 1 | == | True | histories=full (64); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 2 | 1/2 | 3 | 2 | per_copy | 1/16 | 1/16 | == | True | histories=full (64); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 2 | 1/2 | 3 | 2 | per_copy | 0 | 0 | == | True | histories=full (64) |
| prop3_share_recovered | 2 | 1/2 | 3 | 2 | per_copy | 7/8 | 7/8 | == | True | histories=full (64) |
| prop3_full_vs_count_histories | 2 | 1/2 | 3 | 2 | per_copy | 1/16 | 1/16 | == | True |  |
| prop3_history_optimum | 2 | 1/2 | 5 | 2 | pooled | 127/6144 | 127/6144 | == | True | histories=count (36) |
| prop3_E[R|I=0] | 2 | 1/2 | 5 | 2 | pooled | 1/2 | 1/2 | == | True | histories=count (36) |
| prop3_every_history_with_I=0 | 2 | 1/2 | 5 | 2 | pooled | 1 | 1 | == | True | histories=count (36); count of distinct per-history optima |
| prop3_E[R|I=1] | 2 | 1/2 | 5 | 2 | pooled | 1/3 | 1/3 | == | True | histories=count (36) |
| prop3_every_history_with_I=1 | 2 | 1/2 | 5 | 2 | pooled | 1 | 1 | == | True | histories=count (36); count of distinct per-history optima |
| prop3_E[R|I=2] | 2 | 1/2 | 5 | 2 | pooled | 0 | 0 | == | True | histories=count (36) |
| prop3_every_history_with_I=2 | 2 | 1/2 | 5 | 2 | pooled | 1 | 1 | == | True | histories=count (36); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 2 | 1/2 | 5 | 2 | pooled | 127/6144 | 127/6144 | == | True | histories=count (36); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 2 | 1/2 | 5 | 2 | pooled | 0 | 0 | == | True | histories=count (36) |
| prop3_share_recovered_vs_f/(2-f) | 2 | 1/2 | 5 | 2 | pooled | 2945/3072 | 31/33 | >= | True | histories=count (36) |
| prop3_history_optimum | 2 | 1/2 | 5 | 2 | per_copy | 1/64 | 1/64 | == | True | histories=count (36) |
| prop3_E[R|I=0] | 2 | 1/2 | 5 | 2 | per_copy | 1/2 | 1/2 | == | True | histories=count (36) |
| prop3_every_history_with_I=0 | 2 | 1/2 | 5 | 2 | per_copy | 1 | 1 | == | True | histories=count (36); count of distinct per-history optima |
| prop3_E[R|I=1] | 2 | 1/2 | 5 | 2 | per_copy | 1/4 | 1/4 | == | True | histories=count (36) |
| prop3_every_history_with_I=1 | 2 | 1/2 | 5 | 2 | per_copy | 1 | 1 | == | True | histories=count (36); count of distinct per-history optima |
| prop3_E[R|I=2] | 2 | 1/2 | 5 | 2 | per_copy | 0 | 0 | == | True | histories=count (36) |
| prop3_every_history_with_I=2 | 2 | 1/2 | 5 | 2 | per_copy | 1 | 1 | == | True | histories=count (36); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 2 | 1/2 | 5 | 2 | per_copy | 1/64 | 1/64 | == | True | histories=count (36); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 2 | 1/2 | 5 | 2 | per_copy | 0 | 0 | == | True | histories=count (36) |
| prop3_share_recovered | 2 | 1/2 | 5 | 2 | per_copy | 31/32 | 31/32 | == | True | histories=count (36) |
| prop1_oblivious_optimum | 2 | 2/5 |  | 2 | pooled | 2/5 | 2/5 | == | True | 117 orbits / 912 schedules |
| prop1_posterior_optimum | 2 | 2/5 |  | 2 | pooled | 0 | 0 | == | True |  |
| prop1_hedge_all_A_max_R_over_realizations | 2 | 2/5 |  | 2 | pooled | 0 | 0 | == | True |  |
| prop1_oblivious_optimum | 2 | 2/5 |  | 2 | per_copy | 2/5 | 2/5 | == | True | 153 orbits / 784 schedules |
| prop1_posterior_optimum | 2 | 2/5 |  | 2 | per_copy | 0 | 0 | == | True |  |
| prop1_hedge_all_A_max_R_over_realizations | 2 | 2/5 |  | 2 | per_copy | 0 | 0 | == | True |  |
| gap_c | 2 | 2/5 |  | 0 | pooled | 0 | 0 | == | True |  |
| gap_c_oblivious_optimum | 2 | 2/5 |  | 0 | pooled | 4/5 | 4/5 | == | True |  |
| gap_c_posterior_optimum | 2 | 2/5 |  | 0 | pooled | 4/5 | 4/5 | == | True |  |
| gap_c | 2 | 2/5 |  | 1 | pooled | 1/5 | 1/5 | == | True |  |
| gap_c_oblivious_optimum | 2 | 2/5 |  | 1 | pooled | 3/5 | 3/5 | == | True |  |
| gap_c_posterior_optimum | 2 | 2/5 |  | 1 | pooled | 2/5 | 2/5 | == | True |  |
| gap_c | 2 | 2/5 |  | 2 | pooled | 2/5 | 2/5 | == | True |  |
| gap_c_oblivious_optimum | 2 | 2/5 |  | 2 | pooled | 2/5 | 2/5 | == | True |  |
| gap_c_posterior_optimum | 2 | 2/5 |  | 2 | pooled | 0 | 0 | == | True |  |
| gap_c | 2 | 2/5 |  | 3 | pooled | 1/5 | 1/5 | == | True |  |
| gap_c_oblivious_optimum | 2 | 2/5 |  | 3 | pooled | 1/5 | 1/5 | == | True |  |
| gap_c_posterior_optimum | 2 | 2/5 |  | 3 | pooled | 0 | 0 | == | True |  |
| gap_c | 2 | 2/5 |  | 4 | pooled | 0 | 0 | == | True |  |
| gap_c_oblivious_optimum | 2 | 2/5 |  | 4 | pooled | 0 | 0 | == | True |  |
| gap_c_posterior_optimum | 2 | 2/5 |  | 4 | pooled | 0 | 0 | == | True |  |
| gap_c | 2 | 2/5 |  | 0 | per_copy | 0 | 0 | == | True |  |
| gap_c_oblivious_optimum | 2 | 2/5 |  | 0 | per_copy | 4/5 | 4/5 | == | True |  |
| gap_c_posterior_optimum | 2 | 2/5 |  | 0 | per_copy | 4/5 | 4/5 | == | True |  |
| gap_c | 2 | 2/5 |  | 2 | per_copy | 2/5 | 2/5 | == | True |  |
| gap_c_oblivious_optimum | 2 | 2/5 |  | 2 | per_copy | 2/5 | 2/5 | == | True |  |
| gap_c_posterior_optimum | 2 | 2/5 |  | 2 | per_copy | 0 | 0 | == | True |  |
| gap_c | 2 | 2/5 |  | 4 | per_copy | 0 | 0 | == | True |  |
| gap_c_oblivious_optimum | 2 | 2/5 |  | 4 | per_copy | 0 | 0 | == | True |  |
| gap_c_posterior_optimum | 2 | 2/5 |  | 4 | per_copy | 0 | 0 | == | True |  |
| prop3_history_optimum | 2 | 2/5 | 0 | 2 | pooled | 2/5 | 2/5 | == | True | histories=count (1) |
| prop3_E[R|I=0] | 2 | 2/5 | 0 | 2 | pooled | 2/5 | 2/5 | == | True | histories=count (1) |
| prop3_every_history_with_I=0 | 2 | 2/5 | 0 | 2 | pooled | 1 | 1 | == | True | histories=count (1); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 2 | 2/5 | 0 | 2 | pooled | 2/5 | 2/5 | == | True | histories=count (1); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 2 | 2/5 | 0 | 2 | pooled | 0 | 0 | == | True | histories=count (1) |
| prop3_share_recovered_vs_f/(2-f) | 2 | 2/5 | 0 | 2 | pooled | 0 | 0 | >= | True | histories=count (1) |
| prop3_M0_equals_prop1 | 2 | 2/5 | 0 | 2 | pooled | 2/5 | 2/5 | == | True | histories=count (1); closed_form column = enumerated Prop 1 |
| prop3_history_optimum | 2 | 2/5 | 0 | 2 | pooled | 2/5 | 2/5 | == | True | histories=full (1) |
| prop3_E[R|I=0] | 2 | 2/5 | 0 | 2 | pooled | 2/5 | 2/5 | == | True | histories=full (1) |
| prop3_every_history_with_I=0 | 2 | 2/5 | 0 | 2 | pooled | 1 | 1 | == | True | histories=full (1); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 2 | 2/5 | 0 | 2 | pooled | 2/5 | 2/5 | == | True | histories=full (1); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 2 | 2/5 | 0 | 2 | pooled | 0 | 0 | == | True | histories=full (1) |
| prop3_share_recovered_vs_f/(2-f) | 2 | 2/5 | 0 | 2 | pooled | 0 | 0 | >= | True | histories=full (1) |
| prop3_M0_equals_prop1 | 2 | 2/5 | 0 | 2 | pooled | 2/5 | 2/5 | == | True | histories=full (1); closed_form column = enumerated Prop 1 |
| prop3_full_vs_count_histories | 2 | 2/5 | 0 | 2 | pooled | 2/5 | 2/5 | == | True |  |
| prop3_history_optimum | 2 | 2/5 | 0 | 2 | per_copy | 2/5 | 2/5 | == | True | histories=count (1) |
| prop3_E[R|I=0] | 2 | 2/5 | 0 | 2 | per_copy | 2/5 | 2/5 | == | True | histories=count (1) |
| prop3_every_history_with_I=0 | 2 | 2/5 | 0 | 2 | per_copy | 1 | 1 | == | True | histories=count (1); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 2 | 2/5 | 0 | 2 | per_copy | 2/5 | 2/5 | == | True | histories=count (1); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 2 | 2/5 | 0 | 2 | per_copy | 0 | 0 | == | True | histories=count (1) |
| prop3_share_recovered | 2 | 2/5 | 0 | 2 | per_copy | 0 | 0 | == | True | histories=count (1) |
| prop3_M0_equals_prop1 | 2 | 2/5 | 0 | 2 | per_copy | 2/5 | 2/5 | == | True | histories=count (1); closed_form column = enumerated Prop 1 |
| prop3_history_optimum | 2 | 2/5 | 0 | 2 | per_copy | 2/5 | 2/5 | == | True | histories=full (1) |
| prop3_E[R|I=0] | 2 | 2/5 | 0 | 2 | per_copy | 2/5 | 2/5 | == | True | histories=full (1) |
| prop3_every_history_with_I=0 | 2 | 2/5 | 0 | 2 | per_copy | 1 | 1 | == | True | histories=full (1); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 2 | 2/5 | 0 | 2 | per_copy | 2/5 | 2/5 | == | True | histories=full (1); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 2 | 2/5 | 0 | 2 | per_copy | 0 | 0 | == | True | histories=full (1) |
| prop3_share_recovered | 2 | 2/5 | 0 | 2 | per_copy | 0 | 0 | == | True | histories=full (1) |
| prop3_M0_equals_prop1 | 2 | 2/5 | 0 | 2 | per_copy | 2/5 | 2/5 | == | True | histories=full (1); closed_form column = enumerated Prop 1 |
| prop3_full_vs_count_histories | 2 | 2/5 | 0 | 2 | per_copy | 2/5 | 2/5 | == | True |  |
| prop3_history_optimum | 2 | 2/5 | 1 | 2 | pooled | 34/125 | 34/125 | == | True | histories=count (4) |
| prop3_E[R|I=0] | 2 | 2/5 | 1 | 2 | pooled | 2/5 | 2/5 | == | True | histories=count (4) |
| prop3_every_history_with_I=0 | 2 | 2/5 | 1 | 2 | pooled | 1 | 1 | == | True | histories=count (4); count of distinct per-history optima |
| prop3_E[R|I=1] | 2 | 2/5 | 1 | 2 | pooled | 4/15 | 4/15 | == | True | histories=count (4) |
| prop3_every_history_with_I=1 | 2 | 2/5 | 1 | 2 | pooled | 1 | 1 | == | True | histories=count (4); count of distinct per-history optima |
| prop3_E[R|I=2] | 2 | 2/5 | 1 | 2 | pooled | 0 | 0 | == | True | histories=count (4) |
| prop3_every_history_with_I=2 | 2 | 2/5 | 1 | 2 | pooled | 1 | 1 | == | True | histories=count (4); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 2 | 2/5 | 1 | 2 | pooled | 34/125 | 34/125 | == | True | histories=count (4); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 2 | 2/5 | 1 | 2 | pooled | 0 | 0 | == | True | histories=count (4) |
| prop3_share_recovered_vs_f/(2-f) | 2 | 2/5 | 1 | 2 | pooled | 8/25 | 1/4 | >= | True | histories=count (4) |
| prop3_history_optimum | 2 | 2/5 | 1 | 2 | pooled | 34/125 | 34/125 | == | True | histories=full (4) |
| prop3_E[R|I=0] | 2 | 2/5 | 1 | 2 | pooled | 2/5 | 2/5 | == | True | histories=full (4) |
| prop3_every_history_with_I=0 | 2 | 2/5 | 1 | 2 | pooled | 1 | 1 | == | True | histories=full (4); count of distinct per-history optima |
| prop3_E[R|I=1] | 2 | 2/5 | 1 | 2 | pooled | 4/15 | 4/15 | == | True | histories=full (4) |
| prop3_every_history_with_I=1 | 2 | 2/5 | 1 | 2 | pooled | 1 | 1 | == | True | histories=full (4); count of distinct per-history optima |
| prop3_E[R|I=2] | 2 | 2/5 | 1 | 2 | pooled | 0 | 0 | == | True | histories=full (4) |
| prop3_every_history_with_I=2 | 2 | 2/5 | 1 | 2 | pooled | 1 | 1 | == | True | histories=full (4); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 2 | 2/5 | 1 | 2 | pooled | 34/125 | 34/125 | == | True | histories=full (4); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 2 | 2/5 | 1 | 2 | pooled | 0 | 0 | == | True | histories=full (4) |
| prop3_share_recovered_vs_f/(2-f) | 2 | 2/5 | 1 | 2 | pooled | 8/25 | 1/4 | >= | True | histories=full (4) |
| prop3_full_vs_count_histories | 2 | 2/5 | 1 | 2 | pooled | 34/125 | 34/125 | == | True |  |
| prop3_history_optimum | 2 | 2/5 | 1 | 2 | per_copy | 6/25 | 6/25 | == | True | histories=count (4) |
| prop3_E[R|I=0] | 2 | 2/5 | 1 | 2 | per_copy | 2/5 | 2/5 | == | True | histories=count (4) |
| prop3_every_history_with_I=0 | 2 | 2/5 | 1 | 2 | per_copy | 1 | 1 | == | True | histories=count (4); count of distinct per-history optima |
| prop3_E[R|I=1] | 2 | 2/5 | 1 | 2 | per_copy | 1/5 | 1/5 | == | True | histories=count (4) |
| prop3_every_history_with_I=1 | 2 | 2/5 | 1 | 2 | per_copy | 1 | 1 | == | True | histories=count (4); count of distinct per-history optima |
| prop3_E[R|I=2] | 2 | 2/5 | 1 | 2 | per_copy | 0 | 0 | == | True | histories=count (4) |
| prop3_every_history_with_I=2 | 2 | 2/5 | 1 | 2 | per_copy | 1 | 1 | == | True | histories=count (4); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 2 | 2/5 | 1 | 2 | per_copy | 6/25 | 6/25 | == | True | histories=count (4); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 2 | 2/5 | 1 | 2 | per_copy | 0 | 0 | == | True | histories=count (4) |
| prop3_share_recovered | 2 | 2/5 | 1 | 2 | per_copy | 2/5 | 2/5 | == | True | histories=count (4) |
| prop3_history_optimum | 2 | 2/5 | 1 | 2 | per_copy | 6/25 | 6/25 | == | True | histories=full (4) |
| prop3_E[R|I=0] | 2 | 2/5 | 1 | 2 | per_copy | 2/5 | 2/5 | == | True | histories=full (4) |
| prop3_every_history_with_I=0 | 2 | 2/5 | 1 | 2 | per_copy | 1 | 1 | == | True | histories=full (4); count of distinct per-history optima |
| prop3_E[R|I=1] | 2 | 2/5 | 1 | 2 | per_copy | 1/5 | 1/5 | == | True | histories=full (4) |
| prop3_every_history_with_I=1 | 2 | 2/5 | 1 | 2 | per_copy | 1 | 1 | == | True | histories=full (4); count of distinct per-history optima |
| prop3_E[R|I=2] | 2 | 2/5 | 1 | 2 | per_copy | 0 | 0 | == | True | histories=full (4) |
| prop3_every_history_with_I=2 | 2 | 2/5 | 1 | 2 | per_copy | 1 | 1 | == | True | histories=full (4); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 2 | 2/5 | 1 | 2 | per_copy | 6/25 | 6/25 | == | True | histories=full (4); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 2 | 2/5 | 1 | 2 | per_copy | 0 | 0 | == | True | histories=full (4) |
| prop3_share_recovered | 2 | 2/5 | 1 | 2 | per_copy | 2/5 | 2/5 | == | True | histories=full (4) |
| prop3_full_vs_count_histories | 2 | 2/5 | 1 | 2 | per_copy | 6/25 | 6/25 | == | True |  |
| prop3_history_optimum | 2 | 2/5 | 2 | 2 | pooled | 546/3125 | 546/3125 | == | True | histories=count (9) |
| prop3_E[R|I=0] | 2 | 2/5 | 2 | 2 | pooled | 2/5 | 2/5 | == | True | histories=count (9) |
| prop3_every_history_with_I=0 | 2 | 2/5 | 2 | 2 | pooled | 1 | 1 | == | True | histories=count (9); count of distinct per-history optima |
| prop3_E[R|I=1] | 2 | 2/5 | 2 | 2 | pooled | 4/15 | 4/15 | == | True | histories=count (9) |
| prop3_every_history_with_I=1 | 2 | 2/5 | 2 | 2 | pooled | 1 | 1 | == | True | histories=count (9); count of distinct per-history optima |
| prop3_E[R|I=2] | 2 | 2/5 | 2 | 2 | pooled | 0 | 0 | == | True | histories=count (9) |
| prop3_every_history_with_I=2 | 2 | 2/5 | 2 | 2 | pooled | 1 | 1 | == | True | histories=count (9); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 2 | 2/5 | 2 | 2 | pooled | 546/3125 | 546/3125 | == | True | histories=count (9); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 2 | 2/5 | 2 | 2 | pooled | 0 | 0 | == | True | histories=count (9) |
| prop3_share_recovered_vs_f/(2-f) | 2 | 2/5 | 2 | 2 | pooled | 352/625 | 8/17 | >= | True | histories=count (9) |
| prop3_history_optimum | 2 | 2/5 | 2 | 2 | pooled | 546/3125 | 546/3125 | == | True | histories=full (16) |
| prop3_E[R|I=0] | 2 | 2/5 | 2 | 2 | pooled | 2/5 | 2/5 | == | True | histories=full (16) |
| prop3_every_history_with_I=0 | 2 | 2/5 | 2 | 2 | pooled | 1 | 1 | == | True | histories=full (16); count of distinct per-history optima |
| prop3_E[R|I=1] | 2 | 2/5 | 2 | 2 | pooled | 4/15 | 4/15 | == | True | histories=full (16) |
| prop3_every_history_with_I=1 | 2 | 2/5 | 2 | 2 | pooled | 1 | 1 | == | True | histories=full (16); count of distinct per-history optima |
| prop3_E[R|I=2] | 2 | 2/5 | 2 | 2 | pooled | 0 | 0 | == | True | histories=full (16) |
| prop3_every_history_with_I=2 | 2 | 2/5 | 2 | 2 | pooled | 1 | 1 | == | True | histories=full (16); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 2 | 2/5 | 2 | 2 | pooled | 546/3125 | 546/3125 | == | True | histories=full (16); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 2 | 2/5 | 2 | 2 | pooled | 0 | 0 | == | True | histories=full (16) |
| prop3_share_recovered_vs_f/(2-f) | 2 | 2/5 | 2 | 2 | pooled | 352/625 | 8/17 | >= | True | histories=full (16) |
| prop3_full_vs_count_histories | 2 | 2/5 | 2 | 2 | pooled | 546/3125 | 546/3125 | == | True |  |
| prop3_history_optimum | 2 | 2/5 | 2 | 2 | per_copy | 18/125 | 18/125 | == | True | histories=count (9) |
| prop3_E[R|I=0] | 2 | 2/5 | 2 | 2 | per_copy | 2/5 | 2/5 | == | True | histories=count (9) |
| prop3_every_history_with_I=0 | 2 | 2/5 | 2 | 2 | per_copy | 1 | 1 | == | True | histories=count (9); count of distinct per-history optima |
| prop3_E[R|I=1] | 2 | 2/5 | 2 | 2 | per_copy | 1/5 | 1/5 | == | True | histories=count (9) |
| prop3_every_history_with_I=1 | 2 | 2/5 | 2 | 2 | per_copy | 1 | 1 | == | True | histories=count (9); count of distinct per-history optima |
| prop3_E[R|I=2] | 2 | 2/5 | 2 | 2 | per_copy | 0 | 0 | == | True | histories=count (9) |
| prop3_every_history_with_I=2 | 2 | 2/5 | 2 | 2 | per_copy | 1 | 1 | == | True | histories=count (9); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 2 | 2/5 | 2 | 2 | per_copy | 18/125 | 18/125 | == | True | histories=count (9); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 2 | 2/5 | 2 | 2 | per_copy | 0 | 0 | == | True | histories=count (9) |
| prop3_share_recovered | 2 | 2/5 | 2 | 2 | per_copy | 16/25 | 16/25 | == | True | histories=count (9) |
| prop3_history_optimum | 2 | 2/5 | 2 | 2 | per_copy | 18/125 | 18/125 | == | True | histories=full (16) |
| prop3_E[R|I=0] | 2 | 2/5 | 2 | 2 | per_copy | 2/5 | 2/5 | == | True | histories=full (16) |
| prop3_every_history_with_I=0 | 2 | 2/5 | 2 | 2 | per_copy | 1 | 1 | == | True | histories=full (16); count of distinct per-history optima |
| prop3_E[R|I=1] | 2 | 2/5 | 2 | 2 | per_copy | 1/5 | 1/5 | == | True | histories=full (16) |
| prop3_every_history_with_I=1 | 2 | 2/5 | 2 | 2 | per_copy | 1 | 1 | == | True | histories=full (16); count of distinct per-history optima |
| prop3_E[R|I=2] | 2 | 2/5 | 2 | 2 | per_copy | 0 | 0 | == | True | histories=full (16) |
| prop3_every_history_with_I=2 | 2 | 2/5 | 2 | 2 | per_copy | 1 | 1 | == | True | histories=full (16); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 2 | 2/5 | 2 | 2 | per_copy | 18/125 | 18/125 | == | True | histories=full (16); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 2 | 2/5 | 2 | 2 | per_copy | 0 | 0 | == | True | histories=full (16) |
| prop3_share_recovered | 2 | 2/5 | 2 | 2 | per_copy | 16/25 | 16/25 | == | True | histories=full (16) |
| prop3_full_vs_count_histories | 2 | 2/5 | 2 | 2 | per_copy | 18/125 | 18/125 | == | True |  |
| prop3_history_optimum | 2 | 2/5 | 3 | 2 | pooled | 8514/78125 | 8514/78125 | == | True | histories=count (16) |
| prop3_E[R|I=0] | 2 | 2/5 | 3 | 2 | pooled | 2/5 | 2/5 | == | True | histories=count (16) |
| prop3_every_history_with_I=0 | 2 | 2/5 | 3 | 2 | pooled | 1 | 1 | == | True | histories=count (16); count of distinct per-history optima |
| prop3_E[R|I=1] | 2 | 2/5 | 3 | 2 | pooled | 4/15 | 4/15 | == | True | histories=count (16) |
| prop3_every_history_with_I=1 | 2 | 2/5 | 3 | 2 | pooled | 1 | 1 | == | True | histories=count (16); count of distinct per-history optima |
| prop3_E[R|I=2] | 2 | 2/5 | 3 | 2 | pooled | 0 | 0 | == | True | histories=count (16) |
| prop3_every_history_with_I=2 | 2 | 2/5 | 3 | 2 | pooled | 1 | 1 | == | True | histories=count (16); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 2 | 2/5 | 3 | 2 | pooled | 8514/78125 | 8514/78125 | == | True | histories=count (16); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 2 | 2/5 | 3 | 2 | pooled | 0 | 0 | == | True | histories=count (16) |
| prop3_share_recovered_vs_f/(2-f) | 2 | 2/5 | 3 | 2 | pooled | 11368/15625 | 49/76 | >= | True | histories=count (16) |
| prop3_history_optimum | 2 | 2/5 | 3 | 2 | pooled | 8514/78125 | 8514/78125 | == | True | histories=full (64) |
| prop3_E[R|I=0] | 2 | 2/5 | 3 | 2 | pooled | 2/5 | 2/5 | == | True | histories=full (64) |
| prop3_every_history_with_I=0 | 2 | 2/5 | 3 | 2 | pooled | 1 | 1 | == | True | histories=full (64); count of distinct per-history optima |
| prop3_E[R|I=1] | 2 | 2/5 | 3 | 2 | pooled | 4/15 | 4/15 | == | True | histories=full (64) |
| prop3_every_history_with_I=1 | 2 | 2/5 | 3 | 2 | pooled | 1 | 1 | == | True | histories=full (64); count of distinct per-history optima |
| prop3_E[R|I=2] | 2 | 2/5 | 3 | 2 | pooled | 0 | 0 | == | True | histories=full (64) |
| prop3_every_history_with_I=2 | 2 | 2/5 | 3 | 2 | pooled | 1 | 1 | == | True | histories=full (64); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 2 | 2/5 | 3 | 2 | pooled | 8514/78125 | 8514/78125 | == | True | histories=full (64); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 2 | 2/5 | 3 | 2 | pooled | 0 | 0 | == | True | histories=full (64) |
| prop3_share_recovered_vs_f/(2-f) | 2 | 2/5 | 3 | 2 | pooled | 11368/15625 | 49/76 | >= | True | histories=full (64) |
| prop3_full_vs_count_histories | 2 | 2/5 | 3 | 2 | pooled | 8514/78125 | 8514/78125 | == | True |  |
| prop3_history_optimum | 2 | 2/5 | 3 | 2 | per_copy | 54/625 | 54/625 | == | True | histories=count (16) |
| prop3_E[R|I=0] | 2 | 2/5 | 3 | 2 | per_copy | 2/5 | 2/5 | == | True | histories=count (16) |
| prop3_every_history_with_I=0 | 2 | 2/5 | 3 | 2 | per_copy | 1 | 1 | == | True | histories=count (16); count of distinct per-history optima |
| prop3_E[R|I=1] | 2 | 2/5 | 3 | 2 | per_copy | 1/5 | 1/5 | == | True | histories=count (16) |
| prop3_every_history_with_I=1 | 2 | 2/5 | 3 | 2 | per_copy | 1 | 1 | == | True | histories=count (16); count of distinct per-history optima |
| prop3_E[R|I=2] | 2 | 2/5 | 3 | 2 | per_copy | 0 | 0 | == | True | histories=count (16) |
| prop3_every_history_with_I=2 | 2 | 2/5 | 3 | 2 | per_copy | 1 | 1 | == | True | histories=count (16); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 2 | 2/5 | 3 | 2 | per_copy | 54/625 | 54/625 | == | True | histories=count (16); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 2 | 2/5 | 3 | 2 | per_copy | 0 | 0 | == | True | histories=count (16) |
| prop3_share_recovered | 2 | 2/5 | 3 | 2 | per_copy | 98/125 | 98/125 | == | True | histories=count (16) |
| prop3_history_optimum | 2 | 2/5 | 3 | 2 | per_copy | 54/625 | 54/625 | == | True | histories=full (64) |
| prop3_E[R|I=0] | 2 | 2/5 | 3 | 2 | per_copy | 2/5 | 2/5 | == | True | histories=full (64) |
| prop3_every_history_with_I=0 | 2 | 2/5 | 3 | 2 | per_copy | 1 | 1 | == | True | histories=full (64); count of distinct per-history optima |
| prop3_E[R|I=1] | 2 | 2/5 | 3 | 2 | per_copy | 1/5 | 1/5 | == | True | histories=full (64) |
| prop3_every_history_with_I=1 | 2 | 2/5 | 3 | 2 | per_copy | 1 | 1 | == | True | histories=full (64); count of distinct per-history optima |
| prop3_E[R|I=2] | 2 | 2/5 | 3 | 2 | per_copy | 0 | 0 | == | True | histories=full (64) |
| prop3_every_history_with_I=2 | 2 | 2/5 | 3 | 2 | per_copy | 1 | 1 | == | True | histories=full (64); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 2 | 2/5 | 3 | 2 | per_copy | 54/625 | 54/625 | == | True | histories=full (64); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 2 | 2/5 | 3 | 2 | per_copy | 0 | 0 | == | True | histories=full (64) |
| prop3_share_recovered | 2 | 2/5 | 3 | 2 | per_copy | 98/125 | 98/125 | == | True | histories=full (64) |
| prop3_full_vs_count_histories | 2 | 2/5 | 3 | 2 | per_copy | 54/625 | 54/625 | == | True |  |
| prop3_history_optimum | 2 | 2/5 | 5 | 2 | pooled | 1985634/48828125 | 1985634/48828125 | == | True | histories=count (36) |
| prop3_E[R|I=0] | 2 | 2/5 | 5 | 2 | pooled | 2/5 | 2/5 | == | True | histories=count (36) |
| prop3_every_history_with_I=0 | 2 | 2/5 | 5 | 2 | pooled | 1 | 1 | == | True | histories=count (36); count of distinct per-history optima |
| prop3_E[R|I=1] | 2 | 2/5 | 5 | 2 | pooled | 4/15 | 4/15 | == | True | histories=count (36) |
| prop3_every_history_with_I=1 | 2 | 2/5 | 5 | 2 | pooled | 1 | 1 | == | True | histories=count (36); count of distinct per-history optima |
| prop3_E[R|I=2] | 2 | 2/5 | 5 | 2 | pooled | 0 | 0 | == | True | histories=count (36) |
| prop3_every_history_with_I=2 | 2 | 2/5 | 5 | 2 | pooled | 1 | 1 | == | True | histories=count (36); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 2 | 2/5 | 5 | 2 | pooled | 1985634/48828125 | 1985634/48828125 | == | True | histories=count (36); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 2 | 2/5 | 5 | 2 | pooled | 0 | 0 | == | True | histories=count (36) |
| prop3_share_recovered_vs_f/(2-f) | 2 | 2/5 | 5 | 2 | pooled | 8772808/9765625 | 1441/1684 | >= | True | histories=count (36) |
| prop3_history_optimum | 2 | 2/5 | 5 | 2 | per_copy | 486/15625 | 486/15625 | == | True | histories=count (36) |
| prop3_E[R|I=0] | 2 | 2/5 | 5 | 2 | per_copy | 2/5 | 2/5 | == | True | histories=count (36) |
| prop3_every_history_with_I=0 | 2 | 2/5 | 5 | 2 | per_copy | 1 | 1 | == | True | histories=count (36); count of distinct per-history optima |
| prop3_E[R|I=1] | 2 | 2/5 | 5 | 2 | per_copy | 1/5 | 1/5 | == | True | histories=count (36) |
| prop3_every_history_with_I=1 | 2 | 2/5 | 5 | 2 | per_copy | 1 | 1 | == | True | histories=count (36); count of distinct per-history optima |
| prop3_E[R|I=2] | 2 | 2/5 | 5 | 2 | per_copy | 0 | 0 | == | True | histories=count (36) |
| prop3_every_history_with_I=2 | 2 | 2/5 | 5 | 2 | per_copy | 1 | 1 | == | True | histories=count (36); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 2 | 2/5 | 5 | 2 | per_copy | 486/15625 | 486/15625 | == | True | histories=count (36); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 2 | 2/5 | 5 | 2 | per_copy | 0 | 0 | == | True | histories=count (36) |
| prop3_share_recovered | 2 | 2/5 | 5 | 2 | per_copy | 2882/3125 | 2882/3125 | == | True | histories=count (36) |
| prop1_oblivious_optimum | 2 | 7/50 |  | 2 | pooled | 7/50 | 7/50 | == | True | 117 orbits / 912 schedules |
| prop1_posterior_optimum | 2 | 7/50 |  | 2 | pooled | 0 | 0 | == | True |  |
| prop1_hedge_all_A_max_R_over_realizations | 2 | 7/50 |  | 2 | pooled | 0 | 0 | == | True |  |
| prop1_oblivious_optimum | 2 | 7/50 |  | 2 | per_copy | 7/50 | 7/50 | == | True | 153 orbits / 784 schedules |
| prop1_posterior_optimum | 2 | 7/50 |  | 2 | per_copy | 0 | 0 | == | True |  |
| prop1_hedge_all_A_max_R_over_realizations | 2 | 7/50 |  | 2 | per_copy | 0 | 0 | == | True |  |
| gap_c | 2 | 7/50 |  | 0 | pooled | 0 | 0 | == | True |  |
| gap_c_oblivious_optimum | 2 | 7/50 |  | 0 | pooled | 7/25 | 7/25 | == | True |  |
| gap_c_posterior_optimum | 2 | 7/50 |  | 0 | pooled | 7/25 | 7/25 | == | True |  |
| gap_c | 2 | 7/50 |  | 1 | pooled | 7/100 | 7/100 | == | True |  |
| gap_c_oblivious_optimum | 2 | 7/50 |  | 1 | pooled | 21/100 | 21/100 | == | True |  |
| gap_c_posterior_optimum | 2 | 7/50 |  | 1 | pooled | 7/50 | 7/50 | == | True |  |
| gap_c | 2 | 7/50 |  | 2 | pooled | 7/50 | 7/50 | == | True |  |
| gap_c_oblivious_optimum | 2 | 7/50 |  | 2 | pooled | 7/50 | 7/50 | == | True |  |
| gap_c_posterior_optimum | 2 | 7/50 |  | 2 | pooled | 0 | 0 | == | True |  |
| gap_c | 2 | 7/50 |  | 3 | pooled | 7/100 | 7/100 | == | True |  |
| gap_c_oblivious_optimum | 2 | 7/50 |  | 3 | pooled | 7/100 | 7/100 | == | True |  |
| gap_c_posterior_optimum | 2 | 7/50 |  | 3 | pooled | 0 | 0 | == | True |  |
| gap_c | 2 | 7/50 |  | 4 | pooled | 0 | 0 | == | True |  |
| gap_c_oblivious_optimum | 2 | 7/50 |  | 4 | pooled | 0 | 0 | == | True |  |
| gap_c_posterior_optimum | 2 | 7/50 |  | 4 | pooled | 0 | 0 | == | True |  |
| gap_c | 2 | 7/50 |  | 0 | per_copy | 0 | 0 | == | True |  |
| gap_c_oblivious_optimum | 2 | 7/50 |  | 0 | per_copy | 7/25 | 7/25 | == | True |  |
| gap_c_posterior_optimum | 2 | 7/50 |  | 0 | per_copy | 7/25 | 7/25 | == | True |  |
| gap_c | 2 | 7/50 |  | 2 | per_copy | 7/50 | 7/50 | == | True |  |
| gap_c_oblivious_optimum | 2 | 7/50 |  | 2 | per_copy | 7/50 | 7/50 | == | True |  |
| gap_c_posterior_optimum | 2 | 7/50 |  | 2 | per_copy | 0 | 0 | == | True |  |
| gap_c | 2 | 7/50 |  | 4 | per_copy | 0 | 0 | == | True |  |
| gap_c_oblivious_optimum | 2 | 7/50 |  | 4 | per_copy | 0 | 0 | == | True |  |
| gap_c_posterior_optimum | 2 | 7/50 |  | 4 | per_copy | 0 | 0 | == | True |  |
| prop3_history_optimum | 2 | 7/50 | 0 | 2 | pooled | 7/50 | 7/50 | == | True | histories=count (1) |
| prop3_E[R|I=0] | 2 | 7/50 | 0 | 2 | pooled | 7/50 | 7/50 | == | True | histories=count (1) |
| prop3_every_history_with_I=0 | 2 | 7/50 | 0 | 2 | pooled | 1 | 1 | == | True | histories=count (1); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 2 | 7/50 | 0 | 2 | pooled | 7/50 | 7/50 | == | True | histories=count (1); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 2 | 7/50 | 0 | 2 | pooled | 0 | 0 | == | True | histories=count (1) |
| prop3_share_recovered_vs_f/(2-f) | 2 | 7/50 | 0 | 2 | pooled | 0 | 0 | >= | True | histories=count (1) |
| prop3_M0_equals_prop1 | 2 | 7/50 | 0 | 2 | pooled | 7/50 | 7/50 | == | True | histories=count (1); closed_form column = enumerated Prop 1 |
| prop3_history_optimum | 2 | 7/50 | 0 | 2 | pooled | 7/50 | 7/50 | == | True | histories=full (1) |
| prop3_E[R|I=0] | 2 | 7/50 | 0 | 2 | pooled | 7/50 | 7/50 | == | True | histories=full (1) |
| prop3_every_history_with_I=0 | 2 | 7/50 | 0 | 2 | pooled | 1 | 1 | == | True | histories=full (1); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 2 | 7/50 | 0 | 2 | pooled | 7/50 | 7/50 | == | True | histories=full (1); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 2 | 7/50 | 0 | 2 | pooled | 0 | 0 | == | True | histories=full (1) |
| prop3_share_recovered_vs_f/(2-f) | 2 | 7/50 | 0 | 2 | pooled | 0 | 0 | >= | True | histories=full (1) |
| prop3_M0_equals_prop1 | 2 | 7/50 | 0 | 2 | pooled | 7/50 | 7/50 | == | True | histories=full (1); closed_form column = enumerated Prop 1 |
| prop3_full_vs_count_histories | 2 | 7/50 | 0 | 2 | pooled | 7/50 | 7/50 | == | True |  |
| prop3_history_optimum | 2 | 7/50 | 0 | 2 | per_copy | 7/50 | 7/50 | == | True | histories=count (1) |
| prop3_E[R|I=0] | 2 | 7/50 | 0 | 2 | per_copy | 7/50 | 7/50 | == | True | histories=count (1) |
| prop3_every_history_with_I=0 | 2 | 7/50 | 0 | 2 | per_copy | 1 | 1 | == | True | histories=count (1); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 2 | 7/50 | 0 | 2 | per_copy | 7/50 | 7/50 | == | True | histories=count (1); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 2 | 7/50 | 0 | 2 | per_copy | 0 | 0 | == | True | histories=count (1) |
| prop3_share_recovered | 2 | 7/50 | 0 | 2 | per_copy | 0 | 0 | == | True | histories=count (1) |
| prop3_M0_equals_prop1 | 2 | 7/50 | 0 | 2 | per_copy | 7/50 | 7/50 | == | True | histories=count (1); closed_form column = enumerated Prop 1 |
| prop3_history_optimum | 2 | 7/50 | 0 | 2 | per_copy | 7/50 | 7/50 | == | True | histories=full (1) |
| prop3_E[R|I=0] | 2 | 7/50 | 0 | 2 | per_copy | 7/50 | 7/50 | == | True | histories=full (1) |
| prop3_every_history_with_I=0 | 2 | 7/50 | 0 | 2 | per_copy | 1 | 1 | == | True | histories=full (1); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 2 | 7/50 | 0 | 2 | per_copy | 7/50 | 7/50 | == | True | histories=full (1); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 2 | 7/50 | 0 | 2 | per_copy | 0 | 0 | == | True | histories=full (1) |
| prop3_share_recovered | 2 | 7/50 | 0 | 2 | per_copy | 0 | 0 | == | True | histories=full (1) |
| prop3_M0_equals_prop1 | 2 | 7/50 | 0 | 2 | per_copy | 7/50 | 7/50 | == | True | histories=full (1); closed_form column = enumerated Prop 1 |
| prop3_full_vs_count_histories | 2 | 7/50 | 0 | 2 | per_copy | 7/50 | 7/50 | == | True |  |
| prop3_history_optimum | 2 | 7/50 | 1 | 2 | pooled | 47257/375000 | 47257/375000 | == | True | histories=count (4) |
| prop3_E[R|I=0] | 2 | 7/50 | 1 | 2 | pooled | 7/50 | 7/50 | == | True | histories=count (4) |
| prop3_every_history_with_I=0 | 2 | 7/50 | 1 | 2 | pooled | 1 | 1 | == | True | histories=count (4); count of distinct per-history optima |
| prop3_E[R|I=1] | 2 | 7/50 | 1 | 2 | pooled | 7/75 | 7/75 | == | True | histories=count (4) |
| prop3_every_history_with_I=1 | 2 | 7/50 | 1 | 2 | pooled | 1 | 1 | == | True | histories=count (4); count of distinct per-history optima |
| prop3_E[R|I=2] | 2 | 7/50 | 1 | 2 | pooled | 0 | 0 | == | True | histories=count (4) |
| prop3_every_history_with_I=2 | 2 | 7/50 | 1 | 2 | pooled | 1 | 1 | == | True | histories=count (4); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 2 | 7/50 | 1 | 2 | pooled | 47257/375000 | 47257/375000 | == | True | histories=count (4); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 2 | 7/50 | 1 | 2 | pooled | 0 | 0 | == | True | histories=count (4) |
| prop3_share_recovered_vs_f/(2-f) | 2 | 7/50 | 1 | 2 | pooled | 749/7500 | 7/93 | >= | True | histories=count (4) |
| prop3_history_optimum | 2 | 7/50 | 1 | 2 | pooled | 47257/375000 | 47257/375000 | == | True | histories=full (4) |
| prop3_E[R|I=0] | 2 | 7/50 | 1 | 2 | pooled | 7/50 | 7/50 | == | True | histories=full (4) |
| prop3_every_history_with_I=0 | 2 | 7/50 | 1 | 2 | pooled | 1 | 1 | == | True | histories=full (4); count of distinct per-history optima |
| prop3_E[R|I=1] | 2 | 7/50 | 1 | 2 | pooled | 7/75 | 7/75 | == | True | histories=full (4) |
| prop3_every_history_with_I=1 | 2 | 7/50 | 1 | 2 | pooled | 1 | 1 | == | True | histories=full (4); count of distinct per-history optima |
| prop3_E[R|I=2] | 2 | 7/50 | 1 | 2 | pooled | 0 | 0 | == | True | histories=full (4) |
| prop3_every_history_with_I=2 | 2 | 7/50 | 1 | 2 | pooled | 1 | 1 | == | True | histories=full (4); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 2 | 7/50 | 1 | 2 | pooled | 47257/375000 | 47257/375000 | == | True | histories=full (4); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 2 | 7/50 | 1 | 2 | pooled | 0 | 0 | == | True | histories=full (4) |
| prop3_share_recovered_vs_f/(2-f) | 2 | 7/50 | 1 | 2 | pooled | 749/7500 | 7/93 | >= | True | histories=full (4) |
| prop3_full_vs_count_histories | 2 | 7/50 | 1 | 2 | pooled | 47257/375000 | 47257/375000 | == | True |  |
| prop3_history_optimum | 2 | 7/50 | 1 | 2 | per_copy | 301/2500 | 301/2500 | == | True | histories=count (4) |
| prop3_E[R|I=0] | 2 | 7/50 | 1 | 2 | per_copy | 7/50 | 7/50 | == | True | histories=count (4) |
| prop3_every_history_with_I=0 | 2 | 7/50 | 1 | 2 | per_copy | 1 | 1 | == | True | histories=count (4); count of distinct per-history optima |
| prop3_E[R|I=1] | 2 | 7/50 | 1 | 2 | per_copy | 7/100 | 7/100 | == | True | histories=count (4) |
| prop3_every_history_with_I=1 | 2 | 7/50 | 1 | 2 | per_copy | 1 | 1 | == | True | histories=count (4); count of distinct per-history optima |
| prop3_E[R|I=2] | 2 | 7/50 | 1 | 2 | per_copy | 0 | 0 | == | True | histories=count (4) |
| prop3_every_history_with_I=2 | 2 | 7/50 | 1 | 2 | per_copy | 1 | 1 | == | True | histories=count (4); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 2 | 7/50 | 1 | 2 | per_copy | 301/2500 | 301/2500 | == | True | histories=count (4); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 2 | 7/50 | 1 | 2 | per_copy | 0 | 0 | == | True | histories=count (4) |
| prop3_share_recovered | 2 | 7/50 | 1 | 2 | per_copy | 7/50 | 7/50 | == | True | histories=count (4) |
| prop3_history_optimum | 2 | 7/50 | 1 | 2 | per_copy | 301/2500 | 301/2500 | == | True | histories=full (4) |
| prop3_E[R|I=0] | 2 | 7/50 | 1 | 2 | per_copy | 7/50 | 7/50 | == | True | histories=full (4) |
| prop3_every_history_with_I=0 | 2 | 7/50 | 1 | 2 | per_copy | 1 | 1 | == | True | histories=full (4); count of distinct per-history optima |
| prop3_E[R|I=1] | 2 | 7/50 | 1 | 2 | per_copy | 7/100 | 7/100 | == | True | histories=full (4) |
| prop3_every_history_with_I=1 | 2 | 7/50 | 1 | 2 | per_copy | 1 | 1 | == | True | histories=full (4); count of distinct per-history optima |
| prop3_E[R|I=2] | 2 | 7/50 | 1 | 2 | per_copy | 0 | 0 | == | True | histories=full (4) |
| prop3_every_history_with_I=2 | 2 | 7/50 | 1 | 2 | per_copy | 1 | 1 | == | True | histories=full (4); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 2 | 7/50 | 1 | 2 | per_copy | 301/2500 | 301/2500 | == | True | histories=full (4); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 2 | 7/50 | 1 | 2 | per_copy | 0 | 0 | == | True | histories=full (4) |
| prop3_share_recovered | 2 | 7/50 | 1 | 2 | per_copy | 7/50 | 7/50 | == | True | histories=full (4) |
| prop3_full_vs_count_histories | 2 | 7/50 | 1 | 2 | per_copy | 301/2500 | 301/2500 | == | True |  |
| prop3_history_optimum | 2 | 7/50 | 2 | 2 | pooled | 35166131/312500000 | 35166131/312500000 | == | True | histories=count (9) |
| prop3_E[R|I=0] | 2 | 7/50 | 2 | 2 | pooled | 7/50 | 7/50 | == | True | histories=count (9) |
| prop3_every_history_with_I=0 | 2 | 7/50 | 2 | 2 | pooled | 1 | 1 | == | True | histories=count (9); count of distinct per-history optima |
| prop3_E[R|I=1] | 2 | 7/50 | 2 | 2 | pooled | 7/75 | 7/75 | == | True | histories=count (9) |
| prop3_every_history_with_I=1 | 2 | 7/50 | 2 | 2 | pooled | 1 | 1 | == | True | histories=count (9); count of distinct per-history optima |
| prop3_E[R|I=2] | 2 | 7/50 | 2 | 2 | pooled | 0 | 0 | == | True | histories=count (9) |
| prop3_every_history_with_I=2 | 2 | 7/50 | 2 | 2 | pooled | 1 | 1 | == | True | histories=count (9); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 2 | 7/50 | 2 | 2 | pooled | 35166131/312500000 | 35166131/312500000 | == | True | histories=count (9); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 2 | 7/50 | 2 | 2 | pooled | 0 | 0 | == | True | histories=count (9) |
| prop3_share_recovered_vs_f/(2-f) | 2 | 7/50 | 2 | 2 | pooled | 1226267/6250000 | 651/4349 | >= | True | histories=count (9) |
| prop3_history_optimum | 2 | 7/50 | 2 | 2 | pooled | 35166131/312500000 | 35166131/312500000 | == | True | histories=full (16) |
| prop3_E[R|I=0] | 2 | 7/50 | 2 | 2 | pooled | 7/50 | 7/50 | == | True | histories=full (16) |
| prop3_every_history_with_I=0 | 2 | 7/50 | 2 | 2 | pooled | 1 | 1 | == | True | histories=full (16); count of distinct per-history optima |
| prop3_E[R|I=1] | 2 | 7/50 | 2 | 2 | pooled | 7/75 | 7/75 | == | True | histories=full (16) |
| prop3_every_history_with_I=1 | 2 | 7/50 | 2 | 2 | pooled | 1 | 1 | == | True | histories=full (16); count of distinct per-history optima |
| prop3_E[R|I=2] | 2 | 7/50 | 2 | 2 | pooled | 0 | 0 | == | True | histories=full (16) |
| prop3_every_history_with_I=2 | 2 | 7/50 | 2 | 2 | pooled | 1 | 1 | == | True | histories=full (16); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 2 | 7/50 | 2 | 2 | pooled | 35166131/312500000 | 35166131/312500000 | == | True | histories=full (16); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 2 | 7/50 | 2 | 2 | pooled | 0 | 0 | == | True | histories=full (16) |
| prop3_share_recovered_vs_f/(2-f) | 2 | 7/50 | 2 | 2 | pooled | 1226267/6250000 | 651/4349 | >= | True | histories=full (16) |
| prop3_full_vs_count_histories | 2 | 7/50 | 2 | 2 | pooled | 35166131/312500000 | 35166131/312500000 | == | True |  |
| prop3_history_optimum | 2 | 7/50 | 2 | 2 | per_copy | 12943/125000 | 12943/125000 | == | True | histories=count (9) |
| prop3_E[R|I=0] | 2 | 7/50 | 2 | 2 | per_copy | 7/50 | 7/50 | == | True | histories=count (9) |
| prop3_every_history_with_I=0 | 2 | 7/50 | 2 | 2 | per_copy | 1 | 1 | == | True | histories=count (9); count of distinct per-history optima |
| prop3_E[R|I=1] | 2 | 7/50 | 2 | 2 | per_copy | 7/100 | 7/100 | == | True | histories=count (9) |
| prop3_every_history_with_I=1 | 2 | 7/50 | 2 | 2 | per_copy | 1 | 1 | == | True | histories=count (9); count of distinct per-history optima |
| prop3_E[R|I=2] | 2 | 7/50 | 2 | 2 | per_copy | 0 | 0 | == | True | histories=count (9) |
| prop3_every_history_with_I=2 | 2 | 7/50 | 2 | 2 | per_copy | 1 | 1 | == | True | histories=count (9); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 2 | 7/50 | 2 | 2 | per_copy | 12943/125000 | 12943/125000 | == | True | histories=count (9); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 2 | 7/50 | 2 | 2 | per_copy | 0 | 0 | == | True | histories=count (9) |
| prop3_share_recovered | 2 | 7/50 | 2 | 2 | per_copy | 651/2500 | 651/2500 | == | True | histories=count (9) |
| prop3_history_optimum | 2 | 7/50 | 2 | 2 | per_copy | 12943/125000 | 12943/125000 | == | True | histories=full (16) |
| prop3_E[R|I=0] | 2 | 7/50 | 2 | 2 | per_copy | 7/50 | 7/50 | == | True | histories=full (16) |
| prop3_every_history_with_I=0 | 2 | 7/50 | 2 | 2 | per_copy | 1 | 1 | == | True | histories=full (16); count of distinct per-history optima |
| prop3_E[R|I=1] | 2 | 7/50 | 2 | 2 | per_copy | 7/100 | 7/100 | == | True | histories=full (16) |
| prop3_every_history_with_I=1 | 2 | 7/50 | 2 | 2 | per_copy | 1 | 1 | == | True | histories=full (16); count of distinct per-history optima |
| prop3_E[R|I=2] | 2 | 7/50 | 2 | 2 | per_copy | 0 | 0 | == | True | histories=full (16) |
| prop3_every_history_with_I=2 | 2 | 7/50 | 2 | 2 | per_copy | 1 | 1 | == | True | histories=full (16); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 2 | 7/50 | 2 | 2 | per_copy | 12943/125000 | 12943/125000 | == | True | histories=full (16); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 2 | 7/50 | 2 | 2 | per_copy | 0 | 0 | == | True | histories=full (16) |
| prop3_share_recovered | 2 | 7/50 | 2 | 2 | per_copy | 651/2500 | 651/2500 | == | True | histories=full (16) |
| prop3_full_vs_count_histories | 2 | 7/50 | 2 | 2 | per_copy | 12943/125000 | 12943/125000 | == | True |  |
| prop3_history_optimum | 2 | 7/50 | 3 | 2 | pooled | 234024958657/2343750000000 | 234024958657/2343750000000 | == | True | histories=count (16) |
| prop3_E[R|I=0] | 2 | 7/50 | 3 | 2 | pooled | 7/50 | 7/50 | == | True | histories=count (16) |
| prop3_every_history_with_I=0 | 2 | 7/50 | 3 | 2 | pooled | 1 | 1 | == | True | histories=count (16); count of distinct per-history optima |
| prop3_E[R|I=1] | 2 | 7/50 | 3 | 2 | pooled | 7/75 | 7/75 | == | True | histories=count (16) |
| prop3_every_history_with_I=1 | 2 | 7/50 | 3 | 2 | pooled | 1 | 1 | == | True | histories=count (16); count of distinct per-history optima |
| prop3_E[R|I=2] | 2 | 7/50 | 3 | 2 | pooled | 0 | 0 | == | True | histories=count (16) |
| prop3_every_history_with_I=2 | 2 | 7/50 | 3 | 2 | pooled | 1 | 1 | == | True | histories=count (16); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 2 | 7/50 | 3 | 2 | pooled | 234024958657/2343750000000 | 234024958657/2343750000000 | == | True | histories=count (16); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 2 | 7/50 | 3 | 2 | pooled | 0 | 0 | == | True | histories=count (16) |
| prop3_share_recovered_vs_f/(2-f) | 2 | 7/50 | 3 | 2 | pooled | 13442863049/46875000000 | 45493/204507 | >= | True | histories=count (16) |
| prop3_history_optimum | 2 | 7/50 | 3 | 2 | pooled | 234024958657/2343750000000 | 234024958657/2343750000000 | == | True | histories=full (64) |
| prop3_E[R|I=0] | 2 | 7/50 | 3 | 2 | pooled | 7/50 | 7/50 | == | True | histories=full (64) |
| prop3_every_history_with_I=0 | 2 | 7/50 | 3 | 2 | pooled | 1 | 1 | == | True | histories=full (64); count of distinct per-history optima |
| prop3_E[R|I=1] | 2 | 7/50 | 3 | 2 | pooled | 7/75 | 7/75 | == | True | histories=full (64) |
| prop3_every_history_with_I=1 | 2 | 7/50 | 3 | 2 | pooled | 1 | 1 | == | True | histories=full (64); count of distinct per-history optima |
| prop3_E[R|I=2] | 2 | 7/50 | 3 | 2 | pooled | 0 | 0 | == | True | histories=full (64) |
| prop3_every_history_with_I=2 | 2 | 7/50 | 3 | 2 | pooled | 1 | 1 | == | True | histories=full (64); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 2 | 7/50 | 3 | 2 | pooled | 234024958657/2343750000000 | 234024958657/2343750000000 | == | True | histories=full (64); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 2 | 7/50 | 3 | 2 | pooled | 0 | 0 | == | True | histories=full (64) |
| prop3_share_recovered_vs_f/(2-f) | 2 | 7/50 | 3 | 2 | pooled | 13442863049/46875000000 | 45493/204507 | >= | True | histories=full (64) |
| prop3_full_vs_count_histories | 2 | 7/50 | 3 | 2 | pooled | 234024958657/2343750000000 | 234024958657/2343750000000 | == | True |  |
| prop3_history_optimum | 2 | 7/50 | 3 | 2 | per_copy | 556549/6250000 | 556549/6250000 | == | True | histories=count (16) |
| prop3_E[R|I=0] | 2 | 7/50 | 3 | 2 | per_copy | 7/50 | 7/50 | == | True | histories=count (16) |
| prop3_every_history_with_I=0 | 2 | 7/50 | 3 | 2 | per_copy | 1 | 1 | == | True | histories=count (16); count of distinct per-history optima |
| prop3_E[R|I=1] | 2 | 7/50 | 3 | 2 | per_copy | 7/100 | 7/100 | == | True | histories=count (16) |
| prop3_every_history_with_I=1 | 2 | 7/50 | 3 | 2 | per_copy | 1 | 1 | == | True | histories=count (16); count of distinct per-history optima |
| prop3_E[R|I=2] | 2 | 7/50 | 3 | 2 | per_copy | 0 | 0 | == | True | histories=count (16) |
| prop3_every_history_with_I=2 | 2 | 7/50 | 3 | 2 | per_copy | 1 | 1 | == | True | histories=count (16); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 2 | 7/50 | 3 | 2 | per_copy | 556549/6250000 | 556549/6250000 | == | True | histories=count (16); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 2 | 7/50 | 3 | 2 | per_copy | 0 | 0 | == | True | histories=count (16) |
| prop3_share_recovered | 2 | 7/50 | 3 | 2 | per_copy | 45493/125000 | 45493/125000 | == | True | histories=count (16) |
| prop3_history_optimum | 2 | 7/50 | 3 | 2 | per_copy | 556549/6250000 | 556549/6250000 | == | True | histories=full (64) |
| prop3_E[R|I=0] | 2 | 7/50 | 3 | 2 | per_copy | 7/50 | 7/50 | == | True | histories=full (64) |
| prop3_every_history_with_I=0 | 2 | 7/50 | 3 | 2 | per_copy | 1 | 1 | == | True | histories=full (64); count of distinct per-history optima |
| prop3_E[R|I=1] | 2 | 7/50 | 3 | 2 | per_copy | 7/100 | 7/100 | == | True | histories=full (64) |
| prop3_every_history_with_I=1 | 2 | 7/50 | 3 | 2 | per_copy | 1 | 1 | == | True | histories=full (64); count of distinct per-history optima |
| prop3_E[R|I=2] | 2 | 7/50 | 3 | 2 | per_copy | 0 | 0 | == | True | histories=full (64) |
| prop3_every_history_with_I=2 | 2 | 7/50 | 3 | 2 | per_copy | 1 | 1 | == | True | histories=full (64); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 2 | 7/50 | 3 | 2 | per_copy | 556549/6250000 | 556549/6250000 | == | True | histories=full (64); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 2 | 7/50 | 3 | 2 | per_copy | 0 | 0 | == | True | histories=full (64) |
| prop3_share_recovered | 2 | 7/50 | 3 | 2 | per_copy | 45493/125000 | 45493/125000 | == | True | histories=full (64) |
| prop3_full_vs_count_histories | 2 | 7/50 | 3 | 2 | per_copy | 556549/6250000 | 556549/6250000 | == | True |  |
| prop3_history_optimum | 2 | 7/50 | 5 | 2 | pooled | 1135043500057010257/14648437500000000000 | 1135043500057010257/14648437500000000000 | == | True | histories=count (36) |
| prop3_E[R|I=0] | 2 | 7/50 | 5 | 2 | pooled | 7/50 | 7/50 | == | True | histories=count (36) |
| prop3_every_history_with_I=0 | 2 | 7/50 | 5 | 2 | pooled | 1 | 1 | == | True | histories=count (36); count of distinct per-history optima |
| prop3_E[R|I=1] | 2 | 7/50 | 5 | 2 | pooled | 7/75 | 7/75 | == | True | histories=count (36) |
| prop3_every_history_with_I=1 | 2 | 7/50 | 5 | 2 | pooled | 1 | 1 | == | True | histories=count (36); count of distinct per-history optima |
| prop3_E[R|I=2] | 2 | 7/50 | 5 | 2 | pooled | 0 | 0 | == | True | histories=count (36) |
| prop3_every_history_with_I=2 | 2 | 7/50 | 5 | 2 | pooled | 1 | 1 | == | True | histories=count (36); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 2 | 7/50 | 5 | 2 | pooled | 1135043500057010257/14648437500000000000 | 1135043500057010257/14648437500000000000 | == | True | histories=count (36); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 2 | 7/50 | 5 | 2 | pooled | 0 | 0 | == | True | histories=count (36) |
| prop3_share_recovered_vs_f/(2-f) | 2 | 7/50 | 5 | 2 | pooled | 130819678563284249/292968750000000000 | 165491557/459508443 | >= | True | histories=count (36) |
| prop3_history_optimum | 2 | 7/50 | 5 | 2 | per_copy | 1029059101/15625000000 | 1029059101/15625000000 | == | True | histories=count (36) |
| prop3_E[R|I=0] | 2 | 7/50 | 5 | 2 | per_copy | 7/50 | 7/50 | == | True | histories=count (36) |
| prop3_every_history_with_I=0 | 2 | 7/50 | 5 | 2 | per_copy | 1 | 1 | == | True | histories=count (36); count of distinct per-history optima |
| prop3_E[R|I=1] | 2 | 7/50 | 5 | 2 | per_copy | 7/100 | 7/100 | == | True | histories=count (36) |
| prop3_every_history_with_I=1 | 2 | 7/50 | 5 | 2 | per_copy | 1 | 1 | == | True | histories=count (36); count of distinct per-history optima |
| prop3_E[R|I=2] | 2 | 7/50 | 5 | 2 | per_copy | 0 | 0 | == | True | histories=count (36) |
| prop3_every_history_with_I=2 | 2 | 7/50 | 5 | 2 | per_copy | 1 | 1 | == | True | histories=count (36); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 2 | 7/50 | 5 | 2 | per_copy | 1029059101/15625000000 | 1029059101/15625000000 | == | True | histories=count (36); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 2 | 7/50 | 5 | 2 | per_copy | 0 | 0 | == | True | histories=count (36) |
| prop3_share_recovered | 2 | 7/50 | 5 | 2 | per_copy | 165491557/312500000 | 165491557/312500000 | == | True | histories=count (36) |
| prop1_oblivious_optimum | 3 | 1/2 |  | 3 | pooled | 3/4 | 3/4 | == | True | 560 orbits / 29824 schedules |
| prop1_posterior_optimum | 3 | 1/2 |  | 3 | pooled | 0 | 0 | == | True |  |
| prop1_hedge_all_A_max_R_over_realizations | 3 | 1/2 |  | 3 | pooled | 0 | 0 | == | True |  |
| prop1_oblivious_optimum | 3 | 1/2 |  | 3 | per_copy | 3/4 | 3/4 | == | True | 969 orbits / 21952 schedules |
| prop1_posterior_optimum | 3 | 1/2 |  | 3 | per_copy | 0 | 0 | == | True |  |
| prop1_hedge_all_A_max_R_over_realizations | 3 | 1/2 |  | 3 | per_copy | 0 | 0 | == | True |  |
| gap_c | 3 | 1/2 |  | 0 | pooled | 0 | 0 | == | True |  |
| gap_c_oblivious_optimum | 3 | 1/2 |  | 0 | pooled | 3/2 | 3/2 | == | True |  |
| gap_c_posterior_optimum | 3 | 1/2 |  | 0 | pooled | 3/2 | 3/2 | == | True |  |
| gap_c | 3 | 1/2 |  | 1 | pooled | 1/4 | 1/4 | == | True |  |
| gap_c_oblivious_optimum | 3 | 1/2 |  | 1 | pooled | 5/4 | 5/4 | == | True |  |
| gap_c_posterior_optimum | 3 | 1/2 |  | 1 | pooled | 1 | 1 | == | True |  |
| gap_c | 3 | 1/2 |  | 2 | pooled | 1/2 | 1/2 | == | True |  |
| gap_c_oblivious_optimum | 3 | 1/2 |  | 2 | pooled | 1 | 1 | == | True |  |
| gap_c_posterior_optimum | 3 | 1/2 |  | 2 | pooled | 1/2 | 1/2 | == | True |  |
| gap_c | 3 | 1/2 |  | 3 | pooled | 3/4 | 3/4 | == | True |  |
| gap_c_oblivious_optimum | 3 | 1/2 |  | 3 | pooled | 3/4 | 3/4 | == | True |  |
| gap_c_posterior_optimum | 3 | 1/2 |  | 3 | pooled | 0 | 0 | == | True |  |
| gap_c | 3 | 1/2 |  | 4 | pooled | 1/2 | 1/2 | == | True |  |
| gap_c_oblivious_optimum | 3 | 1/2 |  | 4 | pooled | 1/2 | 1/2 | == | True |  |
| gap_c_posterior_optimum | 3 | 1/2 |  | 4 | pooled | 0 | 0 | == | True |  |
| gap_c | 3 | 1/2 |  | 5 | pooled | 1/4 | 1/4 | == | True |  |
| gap_c_oblivious_optimum | 3 | 1/2 |  | 5 | pooled | 1/4 | 1/4 | == | True |  |
| gap_c_posterior_optimum | 3 | 1/2 |  | 5 | pooled | 0 | 0 | == | True |  |
| gap_c | 3 | 1/2 |  | 6 | pooled | 0 | 0 | == | True |  |
| gap_c_oblivious_optimum | 3 | 1/2 |  | 6 | pooled | 0 | 0 | == | True |  |
| gap_c_posterior_optimum | 3 | 1/2 |  | 6 | pooled | 0 | 0 | == | True |  |
| gap_c | 3 | 1/2 |  | 0 | per_copy | 0 | 0 | == | True |  |
| gap_c_oblivious_optimum | 3 | 1/2 |  | 0 | per_copy | 3/2 | 3/2 | == | True |  |
| gap_c_posterior_optimum | 3 | 1/2 |  | 0 | per_copy | 3/2 | 3/2 | == | True |  |
| gap_c | 3 | 1/2 |  | 3 | per_copy | 3/4 | 3/4 | == | True |  |
| gap_c_oblivious_optimum | 3 | 1/2 |  | 3 | per_copy | 3/4 | 3/4 | == | True |  |
| gap_c_posterior_optimum | 3 | 1/2 |  | 3 | per_copy | 0 | 0 | == | True |  |
| gap_c | 3 | 1/2 |  | 6 | per_copy | 0 | 0 | == | True |  |
| gap_c_oblivious_optimum | 3 | 1/2 |  | 6 | per_copy | 0 | 0 | == | True |  |
| gap_c_posterior_optimum | 3 | 1/2 |  | 6 | per_copy | 0 | 0 | == | True |  |
| prop3_history_optimum | 3 | 1/2 | 0 | 3 | pooled | 3/4 | 3/4 | == | True | histories=count (1) |
| prop3_E[R|I=0] | 3 | 1/2 | 0 | 3 | pooled | 3/4 | 3/4 | == | True | histories=count (1) |
| prop3_every_history_with_I=0 | 3 | 1/2 | 0 | 3 | pooled | 1 | 1 | == | True | histories=count (1); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 3 | 1/2 | 0 | 3 | pooled | 3/4 | 3/4 | == | True | histories=count (1); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 3 | 1/2 | 0 | 3 | pooled | 0 | 0 | == | True | histories=count (1) |
| prop3_share_recovered_vs_f/(2-f) | 3 | 1/2 | 0 | 3 | pooled | 0 | 0 | >= | True | histories=count (1) |
| prop3_M0_equals_prop1 | 3 | 1/2 | 0 | 3 | pooled | 3/4 | 3/4 | == | True | histories=count (1); closed_form column = enumerated Prop 1 |
| prop3_history_optimum | 3 | 1/2 | 0 | 3 | pooled | 3/4 | 3/4 | == | True | histories=full (1) |
| prop3_E[R|I=0] | 3 | 1/2 | 0 | 3 | pooled | 3/4 | 3/4 | == | True | histories=full (1) |
| prop3_every_history_with_I=0 | 3 | 1/2 | 0 | 3 | pooled | 1 | 1 | == | True | histories=full (1); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 3 | 1/2 | 0 | 3 | pooled | 3/4 | 3/4 | == | True | histories=full (1); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 3 | 1/2 | 0 | 3 | pooled | 0 | 0 | == | True | histories=full (1) |
| prop3_share_recovered_vs_f/(2-f) | 3 | 1/2 | 0 | 3 | pooled | 0 | 0 | >= | True | histories=full (1) |
| prop3_M0_equals_prop1 | 3 | 1/2 | 0 | 3 | pooled | 3/4 | 3/4 | == | True | histories=full (1); closed_form column = enumerated Prop 1 |
| prop3_full_vs_count_histories | 3 | 1/2 | 0 | 3 | pooled | 3/4 | 3/4 | == | True |  |
| prop3_history_optimum | 3 | 1/2 | 0 | 3 | per_copy | 3/4 | 3/4 | == | True | histories=count (1) |
| prop3_E[R|I=0] | 3 | 1/2 | 0 | 3 | per_copy | 3/4 | 3/4 | == | True | histories=count (1) |
| prop3_every_history_with_I=0 | 3 | 1/2 | 0 | 3 | per_copy | 1 | 1 | == | True | histories=count (1); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 3 | 1/2 | 0 | 3 | per_copy | 3/4 | 3/4 | == | True | histories=count (1); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 3 | 1/2 | 0 | 3 | per_copy | 0 | 0 | == | True | histories=count (1) |
| prop3_share_recovered | 3 | 1/2 | 0 | 3 | per_copy | 0 | 0 | == | True | histories=count (1) |
| prop3_M0_equals_prop1 | 3 | 1/2 | 0 | 3 | per_copy | 3/4 | 3/4 | == | True | histories=count (1); closed_form column = enumerated Prop 1 |
| prop3_history_optimum | 3 | 1/2 | 0 | 3 | per_copy | 3/4 | 3/4 | == | True | histories=full (1) |
| prop3_E[R|I=0] | 3 | 1/2 | 0 | 3 | per_copy | 3/4 | 3/4 | == | True | histories=full (1) |
| prop3_every_history_with_I=0 | 3 | 1/2 | 0 | 3 | per_copy | 1 | 1 | == | True | histories=full (1); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 3 | 1/2 | 0 | 3 | per_copy | 3/4 | 3/4 | == | True | histories=full (1); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 3 | 1/2 | 0 | 3 | per_copy | 0 | 0 | == | True | histories=full (1) |
| prop3_share_recovered | 3 | 1/2 | 0 | 3 | per_copy | 0 | 0 | == | True | histories=full (1) |
| prop3_M0_equals_prop1 | 3 | 1/2 | 0 | 3 | per_copy | 3/4 | 3/4 | == | True | histories=full (1); closed_form column = enumerated Prop 1 |
| prop3_full_vs_count_histories | 3 | 1/2 | 0 | 3 | per_copy | 3/4 | 3/4 | == | True |  |
| prop3_history_optimum | 3 | 1/2 | 1 | 3 | pooled | 147/320 | 147/320 | == | True | histories=count (8) |
| prop3_E[R|I=0] | 3 | 1/2 | 1 | 3 | pooled | 3/4 | 3/4 | == | True | histories=count (8) |
| prop3_every_history_with_I=0 | 3 | 1/2 | 1 | 3 | pooled | 1 | 1 | == | True | histories=count (8); count of distinct per-history optima |
| prop3_E[R|I=1] | 3 | 1/2 | 1 | 3 | pooled | 3/5 | 3/5 | == | True | histories=count (8) |
| prop3_every_history_with_I=1 | 3 | 1/2 | 1 | 3 | pooled | 1 | 1 | == | True | histories=count (8); count of distinct per-history optima |
| prop3_E[R|I=2] | 3 | 1/2 | 1 | 3 | pooled | 3/8 | 3/8 | == | True | histories=count (8) |
| prop3_every_history_with_I=2 | 3 | 1/2 | 1 | 3 | pooled | 1 | 1 | == | True | histories=count (8); count of distinct per-history optima |
| prop3_E[R|I=3] | 3 | 1/2 | 1 | 3 | pooled | 0 | 0 | == | True | histories=count (8) |
| prop3_every_history_with_I=3 | 3 | 1/2 | 1 | 3 | pooled | 1 | 1 | == | True | histories=count (8); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 3 | 1/2 | 1 | 3 | pooled | 147/320 | 147/320 | == | True | histories=count (8); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 3 | 1/2 | 1 | 3 | pooled | 0 | 0 | == | True | histories=count (8) |
| prop3_share_recovered_vs_f/(2-f) | 3 | 1/2 | 1 | 3 | pooled | 31/80 | 1/3 | >= | True | histories=count (8) |
| prop3_history_optimum | 3 | 1/2 | 1 | 3 | pooled | 147/320 | 147/320 | == | True | histories=full (8) |
| prop3_E[R|I=0] | 3 | 1/2 | 1 | 3 | pooled | 3/4 | 3/4 | == | True | histories=full (8) |
| prop3_every_history_with_I=0 | 3 | 1/2 | 1 | 3 | pooled | 1 | 1 | == | True | histories=full (8); count of distinct per-history optima |
| prop3_E[R|I=1] | 3 | 1/2 | 1 | 3 | pooled | 3/5 | 3/5 | == | True | histories=full (8) |
| prop3_every_history_with_I=1 | 3 | 1/2 | 1 | 3 | pooled | 1 | 1 | == | True | histories=full (8); count of distinct per-history optima |
| prop3_E[R|I=2] | 3 | 1/2 | 1 | 3 | pooled | 3/8 | 3/8 | == | True | histories=full (8) |
| prop3_every_history_with_I=2 | 3 | 1/2 | 1 | 3 | pooled | 1 | 1 | == | True | histories=full (8); count of distinct per-history optima |
| prop3_E[R|I=3] | 3 | 1/2 | 1 | 3 | pooled | 0 | 0 | == | True | histories=full (8) |
| prop3_every_history_with_I=3 | 3 | 1/2 | 1 | 3 | pooled | 1 | 1 | == | True | histories=full (8); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 3 | 1/2 | 1 | 3 | pooled | 147/320 | 147/320 | == | True | histories=full (8); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 3 | 1/2 | 1 | 3 | pooled | 0 | 0 | == | True | histories=full (8) |
| prop3_share_recovered_vs_f/(2-f) | 3 | 1/2 | 1 | 3 | pooled | 31/80 | 1/3 | >= | True | histories=full (8) |
| prop3_full_vs_count_histories | 3 | 1/2 | 1 | 3 | pooled | 147/320 | 147/320 | == | True |  |
| prop3_history_optimum | 3 | 1/2 | 1 | 3 | per_copy | 3/8 | 3/8 | == | True | histories=count (8) |
| prop3_E[R|I=0] | 3 | 1/2 | 1 | 3 | per_copy | 3/4 | 3/4 | == | True | histories=count (8) |
| prop3_every_history_with_I=0 | 3 | 1/2 | 1 | 3 | per_copy | 1 | 1 | == | True | histories=count (8); count of distinct per-history optima |
| prop3_E[R|I=1] | 3 | 1/2 | 1 | 3 | per_copy | 1/2 | 1/2 | == | True | histories=count (8) |
| prop3_every_history_with_I=1 | 3 | 1/2 | 1 | 3 | per_copy | 1 | 1 | == | True | histories=count (8); count of distinct per-history optima |
| prop3_E[R|I=2] | 3 | 1/2 | 1 | 3 | per_copy | 1/4 | 1/4 | == | True | histories=count (8) |
| prop3_every_history_with_I=2 | 3 | 1/2 | 1 | 3 | per_copy | 1 | 1 | == | True | histories=count (8); count of distinct per-history optima |
| prop3_E[R|I=3] | 3 | 1/2 | 1 | 3 | per_copy | 0 | 0 | == | True | histories=count (8) |
| prop3_every_history_with_I=3 | 3 | 1/2 | 1 | 3 | per_copy | 1 | 1 | == | True | histories=count (8); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 3 | 1/2 | 1 | 3 | per_copy | 3/8 | 3/8 | == | True | histories=count (8); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 3 | 1/2 | 1 | 3 | per_copy | 0 | 0 | == | True | histories=count (8) |
| prop3_share_recovered | 3 | 1/2 | 1 | 3 | per_copy | 1/2 | 1/2 | == | True | histories=count (8) |
| prop3_history_optimum | 3 | 1/2 | 1 | 3 | per_copy | 3/8 | 3/8 | == | True | histories=full (8) |
| prop3_E[R|I=0] | 3 | 1/2 | 1 | 3 | per_copy | 3/4 | 3/4 | == | True | histories=full (8) |
| prop3_every_history_with_I=0 | 3 | 1/2 | 1 | 3 | per_copy | 1 | 1 | == | True | histories=full (8); count of distinct per-history optima |
| prop3_E[R|I=1] | 3 | 1/2 | 1 | 3 | per_copy | 1/2 | 1/2 | == | True | histories=full (8) |
| prop3_every_history_with_I=1 | 3 | 1/2 | 1 | 3 | per_copy | 1 | 1 | == | True | histories=full (8); count of distinct per-history optima |
| prop3_E[R|I=2] | 3 | 1/2 | 1 | 3 | per_copy | 1/4 | 1/4 | == | True | histories=full (8) |
| prop3_every_history_with_I=2 | 3 | 1/2 | 1 | 3 | per_copy | 1 | 1 | == | True | histories=full (8); count of distinct per-history optima |
| prop3_E[R|I=3] | 3 | 1/2 | 1 | 3 | per_copy | 0 | 0 | == | True | histories=full (8) |
| prop3_every_history_with_I=3 | 3 | 1/2 | 1 | 3 | per_copy | 1 | 1 | == | True | histories=full (8); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 3 | 1/2 | 1 | 3 | per_copy | 3/8 | 3/8 | == | True | histories=full (8); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 3 | 1/2 | 1 | 3 | per_copy | 0 | 0 | == | True | histories=full (8) |
| prop3_share_recovered | 3 | 1/2 | 1 | 3 | per_copy | 1/2 | 1/2 | == | True | histories=full (8) |
| prop3_full_vs_count_histories | 3 | 1/2 | 1 | 3 | per_copy | 3/8 | 3/8 | == | True |  |
| prop3_history_optimum | 3 | 1/2 | 2 | 3 | pooled | 651/2560 | 651/2560 | == | True | histories=count (27) |
| prop3_E[R|I=0] | 3 | 1/2 | 2 | 3 | pooled | 3/4 | 3/4 | == | True | histories=count (27) |
| prop3_every_history_with_I=0 | 3 | 1/2 | 2 | 3 | pooled | 1 | 1 | == | True | histories=count (27); count of distinct per-history optima |
| prop3_E[R|I=1] | 3 | 1/2 | 2 | 3 | pooled | 3/5 | 3/5 | == | True | histories=count (27) |
| prop3_every_history_with_I=1 | 3 | 1/2 | 2 | 3 | pooled | 1 | 1 | == | True | histories=count (27); count of distinct per-history optima |
| prop3_E[R|I=2] | 3 | 1/2 | 2 | 3 | pooled | 3/8 | 3/8 | == | True | histories=count (27) |
| prop3_every_history_with_I=2 | 3 | 1/2 | 2 | 3 | pooled | 1 | 1 | == | True | histories=count (27); count of distinct per-history optima |
| prop3_E[R|I=3] | 3 | 1/2 | 2 | 3 | pooled | 0 | 0 | == | True | histories=count (27) |
| prop3_every_history_with_I=3 | 3 | 1/2 | 2 | 3 | pooled | 1 | 1 | == | True | histories=count (27); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 3 | 1/2 | 2 | 3 | pooled | 651/2560 | 651/2560 | == | True | histories=count (27); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 3 | 1/2 | 2 | 3 | pooled | 0 | 0 | == | True | histories=count (27) |
| prop3_share_recovered_vs_f/(2-f) | 3 | 1/2 | 2 | 3 | pooled | 423/640 | 3/5 | >= | True | histories=count (27) |
| prop3_history_optimum | 3 | 1/2 | 2 | 3 | pooled | 651/2560 | 651/2560 | == | True | histories=full (64) |
| prop3_E[R|I=0] | 3 | 1/2 | 2 | 3 | pooled | 3/4 | 3/4 | == | True | histories=full (64) |
| prop3_every_history_with_I=0 | 3 | 1/2 | 2 | 3 | pooled | 1 | 1 | == | True | histories=full (64); count of distinct per-history optima |
| prop3_E[R|I=1] | 3 | 1/2 | 2 | 3 | pooled | 3/5 | 3/5 | == | True | histories=full (64) |
| prop3_every_history_with_I=1 | 3 | 1/2 | 2 | 3 | pooled | 1 | 1 | == | True | histories=full (64); count of distinct per-history optima |
| prop3_E[R|I=2] | 3 | 1/2 | 2 | 3 | pooled | 3/8 | 3/8 | == | True | histories=full (64) |
| prop3_every_history_with_I=2 | 3 | 1/2 | 2 | 3 | pooled | 1 | 1 | == | True | histories=full (64); count of distinct per-history optima |
| prop3_E[R|I=3] | 3 | 1/2 | 2 | 3 | pooled | 0 | 0 | == | True | histories=full (64) |
| prop3_every_history_with_I=3 | 3 | 1/2 | 2 | 3 | pooled | 1 | 1 | == | True | histories=full (64); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 3 | 1/2 | 2 | 3 | pooled | 651/2560 | 651/2560 | == | True | histories=full (64); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 3 | 1/2 | 2 | 3 | pooled | 0 | 0 | == | True | histories=full (64) |
| prop3_share_recovered_vs_f/(2-f) | 3 | 1/2 | 2 | 3 | pooled | 423/640 | 3/5 | >= | True | histories=full (64) |
| prop3_full_vs_count_histories | 3 | 1/2 | 2 | 3 | pooled | 651/2560 | 651/2560 | == | True |  |
| prop3_history_optimum | 3 | 1/2 | 2 | 3 | per_copy | 3/16 | 3/16 | == | True | histories=count (27) |
| prop3_E[R|I=0] | 3 | 1/2 | 2 | 3 | per_copy | 3/4 | 3/4 | == | True | histories=count (27) |
| prop3_every_history_with_I=0 | 3 | 1/2 | 2 | 3 | per_copy | 1 | 1 | == | True | histories=count (27); count of distinct per-history optima |
| prop3_E[R|I=1] | 3 | 1/2 | 2 | 3 | per_copy | 1/2 | 1/2 | == | True | histories=count (27) |
| prop3_every_history_with_I=1 | 3 | 1/2 | 2 | 3 | per_copy | 1 | 1 | == | True | histories=count (27); count of distinct per-history optima |
| prop3_E[R|I=2] | 3 | 1/2 | 2 | 3 | per_copy | 1/4 | 1/4 | == | True | histories=count (27) |
| prop3_every_history_with_I=2 | 3 | 1/2 | 2 | 3 | per_copy | 1 | 1 | == | True | histories=count (27); count of distinct per-history optima |
| prop3_E[R|I=3] | 3 | 1/2 | 2 | 3 | per_copy | 0 | 0 | == | True | histories=count (27) |
| prop3_every_history_with_I=3 | 3 | 1/2 | 2 | 3 | per_copy | 1 | 1 | == | True | histories=count (27); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 3 | 1/2 | 2 | 3 | per_copy | 3/16 | 3/16 | == | True | histories=count (27); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 3 | 1/2 | 2 | 3 | per_copy | 0 | 0 | == | True | histories=count (27) |
| prop3_share_recovered | 3 | 1/2 | 2 | 3 | per_copy | 3/4 | 3/4 | == | True | histories=count (27) |
| prop3_history_optimum | 3 | 1/2 | 2 | 3 | per_copy | 3/16 | 3/16 | == | True | histories=full (64) |
| prop3_E[R|I=0] | 3 | 1/2 | 2 | 3 | per_copy | 3/4 | 3/4 | == | True | histories=full (64) |
| prop3_every_history_with_I=0 | 3 | 1/2 | 2 | 3 | per_copy | 1 | 1 | == | True | histories=full (64); count of distinct per-history optima |
| prop3_E[R|I=1] | 3 | 1/2 | 2 | 3 | per_copy | 1/2 | 1/2 | == | True | histories=full (64) |
| prop3_every_history_with_I=1 | 3 | 1/2 | 2 | 3 | per_copy | 1 | 1 | == | True | histories=full (64); count of distinct per-history optima |
| prop3_E[R|I=2] | 3 | 1/2 | 2 | 3 | per_copy | 1/4 | 1/4 | == | True | histories=full (64) |
| prop3_every_history_with_I=2 | 3 | 1/2 | 2 | 3 | per_copy | 1 | 1 | == | True | histories=full (64); count of distinct per-history optima |
| prop3_E[R|I=3] | 3 | 1/2 | 2 | 3 | per_copy | 0 | 0 | == | True | histories=full (64) |
| prop3_every_history_with_I=3 | 3 | 1/2 | 2 | 3 | per_copy | 1 | 1 | == | True | histories=full (64); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 3 | 1/2 | 2 | 3 | per_copy | 3/16 | 3/16 | == | True | histories=full (64); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 3 | 1/2 | 2 | 3 | per_copy | 0 | 0 | == | True | histories=full (64) |
| prop3_share_recovered | 3 | 1/2 | 2 | 3 | per_copy | 3/4 | 3/4 | == | True | histories=full (64) |
| prop3_full_vs_count_histories | 3 | 1/2 | 2 | 3 | per_copy | 3/16 | 3/16 | == | True |  |
| prop3_history_optimum | 3 | 1/2 | 3 | 3 | pooled | 2739/20480 | 2739/20480 | == | True | histories=count (64) |
| prop3_E[R|I=0] | 3 | 1/2 | 3 | 3 | pooled | 3/4 | 3/4 | == | True | histories=count (64) |
| prop3_every_history_with_I=0 | 3 | 1/2 | 3 | 3 | pooled | 1 | 1 | == | True | histories=count (64); count of distinct per-history optima |
| prop3_E[R|I=1] | 3 | 1/2 | 3 | 3 | pooled | 3/5 | 3/5 | == | True | histories=count (64) |
| prop3_every_history_with_I=1 | 3 | 1/2 | 3 | 3 | pooled | 1 | 1 | == | True | histories=count (64); count of distinct per-history optima |
| prop3_E[R|I=2] | 3 | 1/2 | 3 | 3 | pooled | 3/8 | 3/8 | == | True | histories=count (64) |
| prop3_every_history_with_I=2 | 3 | 1/2 | 3 | 3 | pooled | 1 | 1 | == | True | histories=count (64); count of distinct per-history optima |
| prop3_E[R|I=3] | 3 | 1/2 | 3 | 3 | pooled | 0 | 0 | == | True | histories=count (64) |
| prop3_every_history_with_I=3 | 3 | 1/2 | 3 | 3 | pooled | 1 | 1 | == | True | histories=count (64); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 3 | 1/2 | 3 | 3 | pooled | 2739/20480 | 2739/20480 | == | True | histories=count (64); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 3 | 1/2 | 3 | 3 | pooled | 0 | 0 | == | True | histories=count (64) |
| prop3_share_recovered_vs_f/(2-f) | 3 | 1/2 | 3 | 3 | pooled | 4207/5120 | 7/9 | >= | True | histories=count (64) |
| prop3_history_optimum | 3 | 1/2 | 3 | 3 | per_copy | 3/32 | 3/32 | == | True | histories=count (64) |
| prop3_E[R|I=0] | 3 | 1/2 | 3 | 3 | per_copy | 3/4 | 3/4 | == | True | histories=count (64) |
| prop3_every_history_with_I=0 | 3 | 1/2 | 3 | 3 | per_copy | 1 | 1 | == | True | histories=count (64); count of distinct per-history optima |
| prop3_E[R|I=1] | 3 | 1/2 | 3 | 3 | per_copy | 1/2 | 1/2 | == | True | histories=count (64) |
| prop3_every_history_with_I=1 | 3 | 1/2 | 3 | 3 | per_copy | 1 | 1 | == | True | histories=count (64); count of distinct per-history optima |
| prop3_E[R|I=2] | 3 | 1/2 | 3 | 3 | per_copy | 1/4 | 1/4 | == | True | histories=count (64) |
| prop3_every_history_with_I=2 | 3 | 1/2 | 3 | 3 | per_copy | 1 | 1 | == | True | histories=count (64); count of distinct per-history optima |
| prop3_E[R|I=3] | 3 | 1/2 | 3 | 3 | per_copy | 0 | 0 | == | True | histories=count (64) |
| prop3_every_history_with_I=3 | 3 | 1/2 | 3 | 3 | per_copy | 1 | 1 | == | True | histories=count (64); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 3 | 1/2 | 3 | 3 | per_copy | 3/32 | 3/32 | == | True | histories=count (64); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 3 | 1/2 | 3 | 3 | per_copy | 0 | 0 | == | True | histories=count (64) |
| prop3_share_recovered | 3 | 1/2 | 3 | 3 | per_copy | 7/8 | 7/8 | == | True | histories=count (64) |
| prop3_history_optimum | 3 | 1/2 | 5 | 3 | pooled | 45507/1310720 | 45507/1310720 | == | True | histories=count (216) |
| prop3_E[R|I=0] | 3 | 1/2 | 5 | 3 | pooled | 3/4 | 3/4 | == | True | histories=count (216) |
| prop3_every_history_with_I=0 | 3 | 1/2 | 5 | 3 | pooled | 1 | 1 | == | True | histories=count (216); count of distinct per-history optima |
| prop3_E[R|I=1] | 3 | 1/2 | 5 | 3 | pooled | 3/5 | 3/5 | == | True | histories=count (216) |
| prop3_every_history_with_I=1 | 3 | 1/2 | 5 | 3 | pooled | 1 | 1 | == | True | histories=count (216); count of distinct per-history optima |
| prop3_E[R|I=2] | 3 | 1/2 | 5 | 3 | pooled | 3/8 | 3/8 | == | True | histories=count (216) |
| prop3_every_history_with_I=2 | 3 | 1/2 | 5 | 3 | pooled | 1 | 1 | == | True | histories=count (216); count of distinct per-history optima |
| prop3_E[R|I=3] | 3 | 1/2 | 5 | 3 | pooled | 0 | 0 | == | True | histories=count (216) |
| prop3_every_history_with_I=3 | 3 | 1/2 | 5 | 3 | pooled | 1 | 1 | == | True | histories=count (216); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 3 | 1/2 | 5 | 3 | pooled | 45507/1310720 | 45507/1310720 | == | True | histories=count (216); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 3 | 1/2 | 5 | 3 | pooled | 0 | 0 | == | True | histories=count (216) |
| prop3_share_recovered_vs_f/(2-f) | 3 | 1/2 | 5 | 3 | pooled | 312511/327680 | 31/33 | >= | True | histories=count (216) |
| prop3_history_optimum | 3 | 1/2 | 5 | 3 | per_copy | 3/128 | 3/128 | == | True | histories=count (216) |
| prop3_E[R|I=0] | 3 | 1/2 | 5 | 3 | per_copy | 3/4 | 3/4 | == | True | histories=count (216) |
| prop3_every_history_with_I=0 | 3 | 1/2 | 5 | 3 | per_copy | 1 | 1 | == | True | histories=count (216); count of distinct per-history optima |
| prop3_E[R|I=1] | 3 | 1/2 | 5 | 3 | per_copy | 1/2 | 1/2 | == | True | histories=count (216) |
| prop3_every_history_with_I=1 | 3 | 1/2 | 5 | 3 | per_copy | 1 | 1 | == | True | histories=count (216); count of distinct per-history optima |
| prop3_E[R|I=2] | 3 | 1/2 | 5 | 3 | per_copy | 1/4 | 1/4 | == | True | histories=count (216) |
| prop3_every_history_with_I=2 | 3 | 1/2 | 5 | 3 | per_copy | 1 | 1 | == | True | histories=count (216); count of distinct per-history optima |
| prop3_E[R|I=3] | 3 | 1/2 | 5 | 3 | per_copy | 0 | 0 | == | True | histories=count (216) |
| prop3_every_history_with_I=3 | 3 | 1/2 | 5 | 3 | per_copy | 1 | 1 | == | True | histories=count (216); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 3 | 1/2 | 5 | 3 | per_copy | 3/128 | 3/128 | == | True | histories=count (216); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 3 | 1/2 | 5 | 3 | per_copy | 0 | 0 | == | True | histories=count (216) |
| prop3_share_recovered | 3 | 1/2 | 5 | 3 | per_copy | 31/32 | 31/32 | == | True | histories=count (216) |
| prop1_oblivious_optimum | 3 | 2/5 |  | 3 | pooled | 3/5 | 3/5 | == | True | 560 orbits / 29824 schedules |
| prop1_posterior_optimum | 3 | 2/5 |  | 3 | pooled | 0 | 0 | == | True |  |
| prop1_hedge_all_A_max_R_over_realizations | 3 | 2/5 |  | 3 | pooled | 0 | 0 | == | True |  |
| prop1_oblivious_optimum | 3 | 2/5 |  | 3 | per_copy | 3/5 | 3/5 | == | True | 969 orbits / 21952 schedules |
| prop1_posterior_optimum | 3 | 2/5 |  | 3 | per_copy | 0 | 0 | == | True |  |
| prop1_hedge_all_A_max_R_over_realizations | 3 | 2/5 |  | 3 | per_copy | 0 | 0 | == | True |  |
| gap_c | 3 | 2/5 |  | 0 | pooled | 0 | 0 | == | True |  |
| gap_c_oblivious_optimum | 3 | 2/5 |  | 0 | pooled | 6/5 | 6/5 | == | True |  |
| gap_c_posterior_optimum | 3 | 2/5 |  | 0 | pooled | 6/5 | 6/5 | == | True |  |
| gap_c | 3 | 2/5 |  | 1 | pooled | 1/5 | 1/5 | == | True |  |
| gap_c_oblivious_optimum | 3 | 2/5 |  | 1 | pooled | 1 | 1 | == | True |  |
| gap_c_posterior_optimum | 3 | 2/5 |  | 1 | pooled | 4/5 | 4/5 | == | True |  |
| gap_c | 3 | 2/5 |  | 2 | pooled | 2/5 | 2/5 | == | True |  |
| gap_c_oblivious_optimum | 3 | 2/5 |  | 2 | pooled | 4/5 | 4/5 | == | True |  |
| gap_c_posterior_optimum | 3 | 2/5 |  | 2 | pooled | 2/5 | 2/5 | == | True |  |
| gap_c | 3 | 2/5 |  | 3 | pooled | 3/5 | 3/5 | == | True |  |
| gap_c_oblivious_optimum | 3 | 2/5 |  | 3 | pooled | 3/5 | 3/5 | == | True |  |
| gap_c_posterior_optimum | 3 | 2/5 |  | 3 | pooled | 0 | 0 | == | True |  |
| gap_c | 3 | 2/5 |  | 4 | pooled | 2/5 | 2/5 | == | True |  |
| gap_c_oblivious_optimum | 3 | 2/5 |  | 4 | pooled | 2/5 | 2/5 | == | True |  |
| gap_c_posterior_optimum | 3 | 2/5 |  | 4 | pooled | 0 | 0 | == | True |  |
| gap_c | 3 | 2/5 |  | 5 | pooled | 1/5 | 1/5 | == | True |  |
| gap_c_oblivious_optimum | 3 | 2/5 |  | 5 | pooled | 1/5 | 1/5 | == | True |  |
| gap_c_posterior_optimum | 3 | 2/5 |  | 5 | pooled | 0 | 0 | == | True |  |
| gap_c | 3 | 2/5 |  | 6 | pooled | 0 | 0 | == | True |  |
| gap_c_oblivious_optimum | 3 | 2/5 |  | 6 | pooled | 0 | 0 | == | True |  |
| gap_c_posterior_optimum | 3 | 2/5 |  | 6 | pooled | 0 | 0 | == | True |  |
| gap_c | 3 | 2/5 |  | 0 | per_copy | 0 | 0 | == | True |  |
| gap_c_oblivious_optimum | 3 | 2/5 |  | 0 | per_copy | 6/5 | 6/5 | == | True |  |
| gap_c_posterior_optimum | 3 | 2/5 |  | 0 | per_copy | 6/5 | 6/5 | == | True |  |
| gap_c | 3 | 2/5 |  | 3 | per_copy | 3/5 | 3/5 | == | True |  |
| gap_c_oblivious_optimum | 3 | 2/5 |  | 3 | per_copy | 3/5 | 3/5 | == | True |  |
| gap_c_posterior_optimum | 3 | 2/5 |  | 3 | per_copy | 0 | 0 | == | True |  |
| gap_c | 3 | 2/5 |  | 6 | per_copy | 0 | 0 | == | True |  |
| gap_c_oblivious_optimum | 3 | 2/5 |  | 6 | per_copy | 0 | 0 | == | True |  |
| gap_c_posterior_optimum | 3 | 2/5 |  | 6 | per_copy | 0 | 0 | == | True |  |
| prop3_history_optimum | 3 | 2/5 | 0 | 3 | pooled | 3/5 | 3/5 | == | True | histories=count (1) |
| prop3_E[R|I=0] | 3 | 2/5 | 0 | 3 | pooled | 3/5 | 3/5 | == | True | histories=count (1) |
| prop3_every_history_with_I=0 | 3 | 2/5 | 0 | 3 | pooled | 1 | 1 | == | True | histories=count (1); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 3 | 2/5 | 0 | 3 | pooled | 3/5 | 3/5 | == | True | histories=count (1); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 3 | 2/5 | 0 | 3 | pooled | 0 | 0 | == | True | histories=count (1) |
| prop3_share_recovered_vs_f/(2-f) | 3 | 2/5 | 0 | 3 | pooled | 0 | 0 | >= | True | histories=count (1) |
| prop3_M0_equals_prop1 | 3 | 2/5 | 0 | 3 | pooled | 3/5 | 3/5 | == | True | histories=count (1); closed_form column = enumerated Prop 1 |
| prop3_history_optimum | 3 | 2/5 | 0 | 3 | pooled | 3/5 | 3/5 | == | True | histories=full (1) |
| prop3_E[R|I=0] | 3 | 2/5 | 0 | 3 | pooled | 3/5 | 3/5 | == | True | histories=full (1) |
| prop3_every_history_with_I=0 | 3 | 2/5 | 0 | 3 | pooled | 1 | 1 | == | True | histories=full (1); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 3 | 2/5 | 0 | 3 | pooled | 3/5 | 3/5 | == | True | histories=full (1); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 3 | 2/5 | 0 | 3 | pooled | 0 | 0 | == | True | histories=full (1) |
| prop3_share_recovered_vs_f/(2-f) | 3 | 2/5 | 0 | 3 | pooled | 0 | 0 | >= | True | histories=full (1) |
| prop3_M0_equals_prop1 | 3 | 2/5 | 0 | 3 | pooled | 3/5 | 3/5 | == | True | histories=full (1); closed_form column = enumerated Prop 1 |
| prop3_full_vs_count_histories | 3 | 2/5 | 0 | 3 | pooled | 3/5 | 3/5 | == | True |  |
| prop3_history_optimum | 3 | 2/5 | 0 | 3 | per_copy | 3/5 | 3/5 | == | True | histories=count (1) |
| prop3_E[R|I=0] | 3 | 2/5 | 0 | 3 | per_copy | 3/5 | 3/5 | == | True | histories=count (1) |
| prop3_every_history_with_I=0 | 3 | 2/5 | 0 | 3 | per_copy | 1 | 1 | == | True | histories=count (1); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 3 | 2/5 | 0 | 3 | per_copy | 3/5 | 3/5 | == | True | histories=count (1); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 3 | 2/5 | 0 | 3 | per_copy | 0 | 0 | == | True | histories=count (1) |
| prop3_share_recovered | 3 | 2/5 | 0 | 3 | per_copy | 0 | 0 | == | True | histories=count (1) |
| prop3_M0_equals_prop1 | 3 | 2/5 | 0 | 3 | per_copy | 3/5 | 3/5 | == | True | histories=count (1); closed_form column = enumerated Prop 1 |
| prop3_history_optimum | 3 | 2/5 | 0 | 3 | per_copy | 3/5 | 3/5 | == | True | histories=full (1) |
| prop3_E[R|I=0] | 3 | 2/5 | 0 | 3 | per_copy | 3/5 | 3/5 | == | True | histories=full (1) |
| prop3_every_history_with_I=0 | 3 | 2/5 | 0 | 3 | per_copy | 1 | 1 | == | True | histories=full (1); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 3 | 2/5 | 0 | 3 | per_copy | 3/5 | 3/5 | == | True | histories=full (1); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 3 | 2/5 | 0 | 3 | per_copy | 0 | 0 | == | True | histories=full (1) |
| prop3_share_recovered | 3 | 2/5 | 0 | 3 | per_copy | 0 | 0 | == | True | histories=full (1) |
| prop3_M0_equals_prop1 | 3 | 2/5 | 0 | 3 | per_copy | 3/5 | 3/5 | == | True | histories=full (1); closed_form column = enumerated Prop 1 |
| prop3_full_vs_count_histories | 3 | 2/5 | 0 | 3 | per_copy | 3/5 | 3/5 | == | True |  |
| prop3_history_optimum | 3 | 2/5 | 1 | 3 | pooled | 1323/3125 | 1323/3125 | == | True | histories=count (8) |
| prop3_E[R|I=0] | 3 | 2/5 | 1 | 3 | pooled | 3/5 | 3/5 | == | True | histories=count (8) |
| prop3_every_history_with_I=0 | 3 | 2/5 | 1 | 3 | pooled | 1 | 1 | == | True | histories=count (8); count of distinct per-history optima |
| prop3_E[R|I=1] | 3 | 2/5 | 1 | 3 | pooled | 12/25 | 12/25 | == | True | histories=count (8) |
| prop3_every_history_with_I=1 | 3 | 2/5 | 1 | 3 | pooled | 1 | 1 | == | True | histories=count (8); count of distinct per-history optima |
| prop3_E[R|I=2] | 3 | 2/5 | 1 | 3 | pooled | 3/10 | 3/10 | == | True | histories=count (8) |
| prop3_every_history_with_I=2 | 3 | 2/5 | 1 | 3 | pooled | 1 | 1 | == | True | histories=count (8); count of distinct per-history optima |
| prop3_E[R|I=3] | 3 | 2/5 | 1 | 3 | pooled | 0 | 0 | == | True | histories=count (8) |
| prop3_every_history_with_I=3 | 3 | 2/5 | 1 | 3 | pooled | 1 | 1 | == | True | histories=count (8); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 3 | 2/5 | 1 | 3 | pooled | 1323/3125 | 1323/3125 | == | True | histories=count (8); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 3 | 2/5 | 1 | 3 | pooled | 0 | 0 | == | True | histories=count (8) |
| prop3_share_recovered_vs_f/(2-f) | 3 | 2/5 | 1 | 3 | pooled | 184/625 | 1/4 | >= | True | histories=count (8) |
| prop3_history_optimum | 3 | 2/5 | 1 | 3 | pooled | 1323/3125 | 1323/3125 | == | True | histories=full (8) |
| prop3_E[R|I=0] | 3 | 2/5 | 1 | 3 | pooled | 3/5 | 3/5 | == | True | histories=full (8) |
| prop3_every_history_with_I=0 | 3 | 2/5 | 1 | 3 | pooled | 1 | 1 | == | True | histories=full (8); count of distinct per-history optima |
| prop3_E[R|I=1] | 3 | 2/5 | 1 | 3 | pooled | 12/25 | 12/25 | == | True | histories=full (8) |
| prop3_every_history_with_I=1 | 3 | 2/5 | 1 | 3 | pooled | 1 | 1 | == | True | histories=full (8); count of distinct per-history optima |
| prop3_E[R|I=2] | 3 | 2/5 | 1 | 3 | pooled | 3/10 | 3/10 | == | True | histories=full (8) |
| prop3_every_history_with_I=2 | 3 | 2/5 | 1 | 3 | pooled | 1 | 1 | == | True | histories=full (8); count of distinct per-history optima |
| prop3_E[R|I=3] | 3 | 2/5 | 1 | 3 | pooled | 0 | 0 | == | True | histories=full (8) |
| prop3_every_history_with_I=3 | 3 | 2/5 | 1 | 3 | pooled | 1 | 1 | == | True | histories=full (8); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 3 | 2/5 | 1 | 3 | pooled | 1323/3125 | 1323/3125 | == | True | histories=full (8); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 3 | 2/5 | 1 | 3 | pooled | 0 | 0 | == | True | histories=full (8) |
| prop3_share_recovered_vs_f/(2-f) | 3 | 2/5 | 1 | 3 | pooled | 184/625 | 1/4 | >= | True | histories=full (8) |
| prop3_full_vs_count_histories | 3 | 2/5 | 1 | 3 | pooled | 1323/3125 | 1323/3125 | == | True |  |
| prop3_history_optimum | 3 | 2/5 | 1 | 3 | per_copy | 9/25 | 9/25 | == | True | histories=count (8) |
| prop3_E[R|I=0] | 3 | 2/5 | 1 | 3 | per_copy | 3/5 | 3/5 | == | True | histories=count (8) |
| prop3_every_history_with_I=0 | 3 | 2/5 | 1 | 3 | per_copy | 1 | 1 | == | True | histories=count (8); count of distinct per-history optima |
| prop3_E[R|I=1] | 3 | 2/5 | 1 | 3 | per_copy | 2/5 | 2/5 | == | True | histories=count (8) |
| prop3_every_history_with_I=1 | 3 | 2/5 | 1 | 3 | per_copy | 1 | 1 | == | True | histories=count (8); count of distinct per-history optima |
| prop3_E[R|I=2] | 3 | 2/5 | 1 | 3 | per_copy | 1/5 | 1/5 | == | True | histories=count (8) |
| prop3_every_history_with_I=2 | 3 | 2/5 | 1 | 3 | per_copy | 1 | 1 | == | True | histories=count (8); count of distinct per-history optima |
| prop3_E[R|I=3] | 3 | 2/5 | 1 | 3 | per_copy | 0 | 0 | == | True | histories=count (8) |
| prop3_every_history_with_I=3 | 3 | 2/5 | 1 | 3 | per_copy | 1 | 1 | == | True | histories=count (8); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 3 | 2/5 | 1 | 3 | per_copy | 9/25 | 9/25 | == | True | histories=count (8); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 3 | 2/5 | 1 | 3 | per_copy | 0 | 0 | == | True | histories=count (8) |
| prop3_share_recovered | 3 | 2/5 | 1 | 3 | per_copy | 2/5 | 2/5 | == | True | histories=count (8) |
| prop3_history_optimum | 3 | 2/5 | 1 | 3 | per_copy | 9/25 | 9/25 | == | True | histories=full (8) |
| prop3_E[R|I=0] | 3 | 2/5 | 1 | 3 | per_copy | 3/5 | 3/5 | == | True | histories=full (8) |
| prop3_every_history_with_I=0 | 3 | 2/5 | 1 | 3 | per_copy | 1 | 1 | == | True | histories=full (8); count of distinct per-history optima |
| prop3_E[R|I=1] | 3 | 2/5 | 1 | 3 | per_copy | 2/5 | 2/5 | == | True | histories=full (8) |
| prop3_every_history_with_I=1 | 3 | 2/5 | 1 | 3 | per_copy | 1 | 1 | == | True | histories=full (8); count of distinct per-history optima |
| prop3_E[R|I=2] | 3 | 2/5 | 1 | 3 | per_copy | 1/5 | 1/5 | == | True | histories=full (8) |
| prop3_every_history_with_I=2 | 3 | 2/5 | 1 | 3 | per_copy | 1 | 1 | == | True | histories=full (8); count of distinct per-history optima |
| prop3_E[R|I=3] | 3 | 2/5 | 1 | 3 | per_copy | 0 | 0 | == | True | histories=full (8) |
| prop3_every_history_with_I=3 | 3 | 2/5 | 1 | 3 | per_copy | 1 | 1 | == | True | histories=full (8); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 3 | 2/5 | 1 | 3 | per_copy | 9/25 | 9/25 | == | True | histories=full (8); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 3 | 2/5 | 1 | 3 | per_copy | 0 | 0 | == | True | histories=full (8) |
| prop3_share_recovered | 3 | 2/5 | 1 | 3 | per_copy | 2/5 | 2/5 | == | True | histories=full (8) |
| prop3_full_vs_count_histories | 3 | 2/5 | 1 | 3 | per_copy | 9/25 | 9/25 | == | True |  |
| prop3_history_optimum | 3 | 2/5 | 2 | 3 | pooled | 109431/390625 | 109431/390625 | == | True | histories=count (27) |
| prop3_E[R|I=0] | 3 | 2/5 | 2 | 3 | pooled | 3/5 | 3/5 | == | True | histories=count (27) |
| prop3_every_history_with_I=0 | 3 | 2/5 | 2 | 3 | pooled | 1 | 1 | == | True | histories=count (27); count of distinct per-history optima |
| prop3_E[R|I=1] | 3 | 2/5 | 2 | 3 | pooled | 12/25 | 12/25 | == | True | histories=count (27) |
| prop3_every_history_with_I=1 | 3 | 2/5 | 2 | 3 | pooled | 1 | 1 | == | True | histories=count (27); count of distinct per-history optima |
| prop3_E[R|I=2] | 3 | 2/5 | 2 | 3 | pooled | 3/10 | 3/10 | == | True | histories=count (27) |
| prop3_every_history_with_I=2 | 3 | 2/5 | 2 | 3 | pooled | 1 | 1 | == | True | histories=count (27); count of distinct per-history optima |
| prop3_E[R|I=3] | 3 | 2/5 | 2 | 3 | pooled | 0 | 0 | == | True | histories=count (27) |
| prop3_every_history_with_I=3 | 3 | 2/5 | 2 | 3 | pooled | 1 | 1 | == | True | histories=count (27); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 3 | 2/5 | 2 | 3 | pooled | 109431/390625 | 109431/390625 | == | True | histories=count (27); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 3 | 2/5 | 2 | 3 | pooled | 0 | 0 | == | True | histories=count (27) |
| prop3_share_recovered_vs_f/(2-f) | 3 | 2/5 | 2 | 3 | pooled | 41648/78125 | 8/17 | >= | True | histories=count (27) |
| prop3_history_optimum | 3 | 2/5 | 2 | 3 | pooled | 109431/390625 | 109431/390625 | == | True | histories=full (64) |
| prop3_E[R|I=0] | 3 | 2/5 | 2 | 3 | pooled | 3/5 | 3/5 | == | True | histories=full (64) |
| prop3_every_history_with_I=0 | 3 | 2/5 | 2 | 3 | pooled | 1 | 1 | == | True | histories=full (64); count of distinct per-history optima |
| prop3_E[R|I=1] | 3 | 2/5 | 2 | 3 | pooled | 12/25 | 12/25 | == | True | histories=full (64) |
| prop3_every_history_with_I=1 | 3 | 2/5 | 2 | 3 | pooled | 1 | 1 | == | True | histories=full (64); count of distinct per-history optima |
| prop3_E[R|I=2] | 3 | 2/5 | 2 | 3 | pooled | 3/10 | 3/10 | == | True | histories=full (64) |
| prop3_every_history_with_I=2 | 3 | 2/5 | 2 | 3 | pooled | 1 | 1 | == | True | histories=full (64); count of distinct per-history optima |
| prop3_E[R|I=3] | 3 | 2/5 | 2 | 3 | pooled | 0 | 0 | == | True | histories=full (64) |
| prop3_every_history_with_I=3 | 3 | 2/5 | 2 | 3 | pooled | 1 | 1 | == | True | histories=full (64); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 3 | 2/5 | 2 | 3 | pooled | 109431/390625 | 109431/390625 | == | True | histories=full (64); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 3 | 2/5 | 2 | 3 | pooled | 0 | 0 | == | True | histories=full (64) |
| prop3_share_recovered_vs_f/(2-f) | 3 | 2/5 | 2 | 3 | pooled | 41648/78125 | 8/17 | >= | True | histories=full (64) |
| prop3_full_vs_count_histories | 3 | 2/5 | 2 | 3 | pooled | 109431/390625 | 109431/390625 | == | True |  |
| prop3_history_optimum | 3 | 2/5 | 2 | 3 | per_copy | 27/125 | 27/125 | == | True | histories=count (27) |
| prop3_E[R|I=0] | 3 | 2/5 | 2 | 3 | per_copy | 3/5 | 3/5 | == | True | histories=count (27) |
| prop3_every_history_with_I=0 | 3 | 2/5 | 2 | 3 | per_copy | 1 | 1 | == | True | histories=count (27); count of distinct per-history optima |
| prop3_E[R|I=1] | 3 | 2/5 | 2 | 3 | per_copy | 2/5 | 2/5 | == | True | histories=count (27) |
| prop3_every_history_with_I=1 | 3 | 2/5 | 2 | 3 | per_copy | 1 | 1 | == | True | histories=count (27); count of distinct per-history optima |
| prop3_E[R|I=2] | 3 | 2/5 | 2 | 3 | per_copy | 1/5 | 1/5 | == | True | histories=count (27) |
| prop3_every_history_with_I=2 | 3 | 2/5 | 2 | 3 | per_copy | 1 | 1 | == | True | histories=count (27); count of distinct per-history optima |
| prop3_E[R|I=3] | 3 | 2/5 | 2 | 3 | per_copy | 0 | 0 | == | True | histories=count (27) |
| prop3_every_history_with_I=3 | 3 | 2/5 | 2 | 3 | per_copy | 1 | 1 | == | True | histories=count (27); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 3 | 2/5 | 2 | 3 | per_copy | 27/125 | 27/125 | == | True | histories=count (27); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 3 | 2/5 | 2 | 3 | per_copy | 0 | 0 | == | True | histories=count (27) |
| prop3_share_recovered | 3 | 2/5 | 2 | 3 | per_copy | 16/25 | 16/25 | == | True | histories=count (27) |
| prop3_history_optimum | 3 | 2/5 | 2 | 3 | per_copy | 27/125 | 27/125 | == | True | histories=full (64) |
| prop3_E[R|I=0] | 3 | 2/5 | 2 | 3 | per_copy | 3/5 | 3/5 | == | True | histories=full (64) |
| prop3_every_history_with_I=0 | 3 | 2/5 | 2 | 3 | per_copy | 1 | 1 | == | True | histories=full (64); count of distinct per-history optima |
| prop3_E[R|I=1] | 3 | 2/5 | 2 | 3 | per_copy | 2/5 | 2/5 | == | True | histories=full (64) |
| prop3_every_history_with_I=1 | 3 | 2/5 | 2 | 3 | per_copy | 1 | 1 | == | True | histories=full (64); count of distinct per-history optima |
| prop3_E[R|I=2] | 3 | 2/5 | 2 | 3 | per_copy | 1/5 | 1/5 | == | True | histories=full (64) |
| prop3_every_history_with_I=2 | 3 | 2/5 | 2 | 3 | per_copy | 1 | 1 | == | True | histories=full (64); count of distinct per-history optima |
| prop3_E[R|I=3] | 3 | 2/5 | 2 | 3 | per_copy | 0 | 0 | == | True | histories=full (64) |
| prop3_every_history_with_I=3 | 3 | 2/5 | 2 | 3 | per_copy | 1 | 1 | == | True | histories=full (64); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 3 | 2/5 | 2 | 3 | per_copy | 27/125 | 27/125 | == | True | histories=full (64); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 3 | 2/5 | 2 | 3 | per_copy | 0 | 0 | == | True | histories=full (64) |
| prop3_share_recovered | 3 | 2/5 | 2 | 3 | per_copy | 16/25 | 16/25 | == | True | histories=full (64) |
| prop3_full_vs_count_histories | 3 | 2/5 | 2 | 3 | per_copy | 27/125 | 27/125 | == | True |  |
| prop3_history_optimum | 3 | 2/5 | 3 | 3 | pooled | 8701587/48828125 | 8701587/48828125 | == | True | histories=count (64) |
| prop3_E[R|I=0] | 3 | 2/5 | 3 | 3 | pooled | 3/5 | 3/5 | == | True | histories=count (64) |
| prop3_every_history_with_I=0 | 3 | 2/5 | 3 | 3 | pooled | 1 | 1 | == | True | histories=count (64); count of distinct per-history optima |
| prop3_E[R|I=1] | 3 | 2/5 | 3 | 3 | pooled | 12/25 | 12/25 | == | True | histories=count (64) |
| prop3_every_history_with_I=1 | 3 | 2/5 | 3 | 3 | pooled | 1 | 1 | == | True | histories=count (64); count of distinct per-history optima |
| prop3_E[R|I=2] | 3 | 2/5 | 3 | 3 | pooled | 3/10 | 3/10 | == | True | histories=count (64) |
| prop3_every_history_with_I=2 | 3 | 2/5 | 3 | 3 | pooled | 1 | 1 | == | True | histories=count (64); count of distinct per-history optima |
| prop3_E[R|I=3] | 3 | 2/5 | 3 | 3 | pooled | 0 | 0 | == | True | histories=count (64) |
| prop3_every_history_with_I=3 | 3 | 2/5 | 3 | 3 | pooled | 1 | 1 | == | True | histories=count (64); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 3 | 2/5 | 3 | 3 | pooled | 8701587/48828125 | 8701587/48828125 | == | True | histories=count (64); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 3 | 2/5 | 3 | 3 | pooled | 0 | 0 | == | True | histories=count (64) |
| prop3_share_recovered_vs_f/(2-f) | 3 | 2/5 | 3 | 3 | pooled | 6865096/9765625 | 49/76 | >= | True | histories=count (64) |
| prop3_history_optimum | 3 | 2/5 | 3 | 3 | per_copy | 81/625 | 81/625 | == | True | histories=count (64) |
| prop3_E[R|I=0] | 3 | 2/5 | 3 | 3 | per_copy | 3/5 | 3/5 | == | True | histories=count (64) |
| prop3_every_history_with_I=0 | 3 | 2/5 | 3 | 3 | per_copy | 1 | 1 | == | True | histories=count (64); count of distinct per-history optima |
| prop3_E[R|I=1] | 3 | 2/5 | 3 | 3 | per_copy | 2/5 | 2/5 | == | True | histories=count (64) |
| prop3_every_history_with_I=1 | 3 | 2/5 | 3 | 3 | per_copy | 1 | 1 | == | True | histories=count (64); count of distinct per-history optima |
| prop3_E[R|I=2] | 3 | 2/5 | 3 | 3 | per_copy | 1/5 | 1/5 | == | True | histories=count (64) |
| prop3_every_history_with_I=2 | 3 | 2/5 | 3 | 3 | per_copy | 1 | 1 | == | True | histories=count (64); count of distinct per-history optima |
| prop3_E[R|I=3] | 3 | 2/5 | 3 | 3 | per_copy | 0 | 0 | == | True | histories=count (64) |
| prop3_every_history_with_I=3 | 3 | 2/5 | 3 | 3 | per_copy | 1 | 1 | == | True | histories=count (64); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 3 | 2/5 | 3 | 3 | per_copy | 81/625 | 81/625 | == | True | histories=count (64); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 3 | 2/5 | 3 | 3 | per_copy | 0 | 0 | == | True | histories=count (64) |
| prop3_share_recovered | 3 | 2/5 | 3 | 3 | per_copy | 98/125 | 98/125 | == | True | histories=count (64) |
| prop3_history_optimum | 3 | 2/5 | 5 | 3 | pooled | 51754324923/762939453125 | 51754324923/762939453125 | == | True | histories=count (216) |
| prop3_E[R|I=0] | 3 | 2/5 | 5 | 3 | pooled | 3/5 | 3/5 | == | True | histories=count (216) |
| prop3_every_history_with_I=0 | 3 | 2/5 | 5 | 3 | pooled | 1 | 1 | == | True | histories=count (216); count of distinct per-history optima |
| prop3_E[R|I=1] | 3 | 2/5 | 5 | 3 | pooled | 12/25 | 12/25 | == | True | histories=count (216) |
| prop3_every_history_with_I=1 | 3 | 2/5 | 5 | 3 | pooled | 1 | 1 | == | True | histories=count (216); count of distinct per-history optima |
| prop3_E[R|I=2] | 3 | 2/5 | 5 | 3 | pooled | 3/10 | 3/10 | == | True | histories=count (216) |
| prop3_every_history_with_I=2 | 3 | 2/5 | 5 | 3 | pooled | 1 | 1 | == | True | histories=count (216); count of distinct per-history optima |
| prop3_E[R|I=3] | 3 | 2/5 | 5 | 3 | pooled | 0 | 0 | == | True | histories=count (216) |
| prop3_every_history_with_I=3 | 3 | 2/5 | 5 | 3 | pooled | 1 | 1 | == | True | histories=count (216); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 3 | 2/5 | 5 | 3 | pooled | 51754324923/762939453125 | 51754324923/762939453125 | == | True | histories=count (216); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 3 | 2/5 | 5 | 3 | pooled | 0 | 0 | == | True | histories=count (216) |
| prop3_share_recovered_vs_f/(2-f) | 3 | 2/5 | 5 | 3 | pooled | 135336448984/152587890625 | 1441/1684 | >= | True | histories=count (216) |
| prop3_history_optimum | 3 | 2/5 | 5 | 3 | per_copy | 729/15625 | 729/15625 | == | True | histories=count (216) |
| prop3_E[R|I=0] | 3 | 2/5 | 5 | 3 | per_copy | 3/5 | 3/5 | == | True | histories=count (216) |
| prop3_every_history_with_I=0 | 3 | 2/5 | 5 | 3 | per_copy | 1 | 1 | == | True | histories=count (216); count of distinct per-history optima |
| prop3_E[R|I=1] | 3 | 2/5 | 5 | 3 | per_copy | 2/5 | 2/5 | == | True | histories=count (216) |
| prop3_every_history_with_I=1 | 3 | 2/5 | 5 | 3 | per_copy | 1 | 1 | == | True | histories=count (216); count of distinct per-history optima |
| prop3_E[R|I=2] | 3 | 2/5 | 5 | 3 | per_copy | 1/5 | 1/5 | == | True | histories=count (216) |
| prop3_every_history_with_I=2 | 3 | 2/5 | 5 | 3 | per_copy | 1 | 1 | == | True | histories=count (216); count of distinct per-history optima |
| prop3_E[R|I=3] | 3 | 2/5 | 5 | 3 | per_copy | 0 | 0 | == | True | histories=count (216) |
| prop3_every_history_with_I=3 | 3 | 2/5 | 5 | 3 | per_copy | 1 | 1 | == | True | histories=count (216); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 3 | 2/5 | 5 | 3 | per_copy | 729/15625 | 729/15625 | == | True | histories=count (216); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 3 | 2/5 | 5 | 3 | per_copy | 0 | 0 | == | True | histories=count (216) |
| prop3_share_recovered | 3 | 2/5 | 5 | 3 | per_copy | 2882/3125 | 2882/3125 | == | True | histories=count (216) |
| prop1_oblivious_optimum | 3 | 7/50 |  | 3 | pooled | 21/100 | 21/100 | == | True | 560 orbits / 29824 schedules |
| prop1_posterior_optimum | 3 | 7/50 |  | 3 | pooled | 0 | 0 | == | True |  |
| prop1_hedge_all_A_max_R_over_realizations | 3 | 7/50 |  | 3 | pooled | 0 | 0 | == | True |  |
| prop1_oblivious_optimum | 3 | 7/50 |  | 3 | per_copy | 21/100 | 21/100 | == | True | 969 orbits / 21952 schedules |
| prop1_posterior_optimum | 3 | 7/50 |  | 3 | per_copy | 0 | 0 | == | True |  |
| prop1_hedge_all_A_max_R_over_realizations | 3 | 7/50 |  | 3 | per_copy | 0 | 0 | == | True |  |
| gap_c | 3 | 7/50 |  | 0 | pooled | 0 | 0 | == | True |  |
| gap_c_oblivious_optimum | 3 | 7/50 |  | 0 | pooled | 21/50 | 21/50 | == | True |  |
| gap_c_posterior_optimum | 3 | 7/50 |  | 0 | pooled | 21/50 | 21/50 | == | True |  |
| gap_c | 3 | 7/50 |  | 1 | pooled | 7/100 | 7/100 | == | True |  |
| gap_c_oblivious_optimum | 3 | 7/50 |  | 1 | pooled | 7/20 | 7/20 | == | True |  |
| gap_c_posterior_optimum | 3 | 7/50 |  | 1 | pooled | 7/25 | 7/25 | == | True |  |
| gap_c | 3 | 7/50 |  | 2 | pooled | 7/50 | 7/50 | == | True |  |
| gap_c_oblivious_optimum | 3 | 7/50 |  | 2 | pooled | 7/25 | 7/25 | == | True |  |
| gap_c_posterior_optimum | 3 | 7/50 |  | 2 | pooled | 7/50 | 7/50 | == | True |  |
| gap_c | 3 | 7/50 |  | 3 | pooled | 21/100 | 21/100 | == | True |  |
| gap_c_oblivious_optimum | 3 | 7/50 |  | 3 | pooled | 21/100 | 21/100 | == | True |  |
| gap_c_posterior_optimum | 3 | 7/50 |  | 3 | pooled | 0 | 0 | == | True |  |
| gap_c | 3 | 7/50 |  | 4 | pooled | 7/50 | 7/50 | == | True |  |
| gap_c_oblivious_optimum | 3 | 7/50 |  | 4 | pooled | 7/50 | 7/50 | == | True |  |
| gap_c_posterior_optimum | 3 | 7/50 |  | 4 | pooled | 0 | 0 | == | True |  |
| gap_c | 3 | 7/50 |  | 5 | pooled | 7/100 | 7/100 | == | True |  |
| gap_c_oblivious_optimum | 3 | 7/50 |  | 5 | pooled | 7/100 | 7/100 | == | True |  |
| gap_c_posterior_optimum | 3 | 7/50 |  | 5 | pooled | 0 | 0 | == | True |  |
| gap_c | 3 | 7/50 |  | 6 | pooled | 0 | 0 | == | True |  |
| gap_c_oblivious_optimum | 3 | 7/50 |  | 6 | pooled | 0 | 0 | == | True |  |
| gap_c_posterior_optimum | 3 | 7/50 |  | 6 | pooled | 0 | 0 | == | True |  |
| gap_c | 3 | 7/50 |  | 0 | per_copy | 0 | 0 | == | True |  |
| gap_c_oblivious_optimum | 3 | 7/50 |  | 0 | per_copy | 21/50 | 21/50 | == | True |  |
| gap_c_posterior_optimum | 3 | 7/50 |  | 0 | per_copy | 21/50 | 21/50 | == | True |  |
| gap_c | 3 | 7/50 |  | 3 | per_copy | 21/100 | 21/100 | == | True |  |
| gap_c_oblivious_optimum | 3 | 7/50 |  | 3 | per_copy | 21/100 | 21/100 | == | True |  |
| gap_c_posterior_optimum | 3 | 7/50 |  | 3 | per_copy | 0 | 0 | == | True |  |
| gap_c | 3 | 7/50 |  | 6 | per_copy | 0 | 0 | == | True |  |
| gap_c_oblivious_optimum | 3 | 7/50 |  | 6 | per_copy | 0 | 0 | == | True |  |
| gap_c_posterior_optimum | 3 | 7/50 |  | 6 | per_copy | 0 | 0 | == | True |  |
| prop3_history_optimum | 3 | 7/50 | 0 | 3 | pooled | 21/100 | 21/100 | == | True | histories=count (1) |
| prop3_E[R|I=0] | 3 | 7/50 | 0 | 3 | pooled | 21/100 | 21/100 | == | True | histories=count (1) |
| prop3_every_history_with_I=0 | 3 | 7/50 | 0 | 3 | pooled | 1 | 1 | == | True | histories=count (1); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 3 | 7/50 | 0 | 3 | pooled | 21/100 | 21/100 | == | True | histories=count (1); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 3 | 7/50 | 0 | 3 | pooled | 0 | 0 | == | True | histories=count (1) |
| prop3_share_recovered_vs_f/(2-f) | 3 | 7/50 | 0 | 3 | pooled | 0 | 0 | >= | True | histories=count (1) |
| prop3_M0_equals_prop1 | 3 | 7/50 | 0 | 3 | pooled | 21/100 | 21/100 | == | True | histories=count (1); closed_form column = enumerated Prop 1 |
| prop3_history_optimum | 3 | 7/50 | 0 | 3 | pooled | 21/100 | 21/100 | == | True | histories=full (1) |
| prop3_E[R|I=0] | 3 | 7/50 | 0 | 3 | pooled | 21/100 | 21/100 | == | True | histories=full (1) |
| prop3_every_history_with_I=0 | 3 | 7/50 | 0 | 3 | pooled | 1 | 1 | == | True | histories=full (1); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 3 | 7/50 | 0 | 3 | pooled | 21/100 | 21/100 | == | True | histories=full (1); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 3 | 7/50 | 0 | 3 | pooled | 0 | 0 | == | True | histories=full (1) |
| prop3_share_recovered_vs_f/(2-f) | 3 | 7/50 | 0 | 3 | pooled | 0 | 0 | >= | True | histories=full (1) |
| prop3_M0_equals_prop1 | 3 | 7/50 | 0 | 3 | pooled | 21/100 | 21/100 | == | True | histories=full (1); closed_form column = enumerated Prop 1 |
| prop3_full_vs_count_histories | 3 | 7/50 | 0 | 3 | pooled | 21/100 | 21/100 | == | True |  |
| prop3_history_optimum | 3 | 7/50 | 0 | 3 | per_copy | 21/100 | 21/100 | == | True | histories=count (1) |
| prop3_E[R|I=0] | 3 | 7/50 | 0 | 3 | per_copy | 21/100 | 21/100 | == | True | histories=count (1) |
| prop3_every_history_with_I=0 | 3 | 7/50 | 0 | 3 | per_copy | 1 | 1 | == | True | histories=count (1); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 3 | 7/50 | 0 | 3 | per_copy | 21/100 | 21/100 | == | True | histories=count (1); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 3 | 7/50 | 0 | 3 | per_copy | 0 | 0 | == | True | histories=count (1) |
| prop3_share_recovered | 3 | 7/50 | 0 | 3 | per_copy | 0 | 0 | == | True | histories=count (1) |
| prop3_M0_equals_prop1 | 3 | 7/50 | 0 | 3 | per_copy | 21/100 | 21/100 | == | True | histories=count (1); closed_form column = enumerated Prop 1 |
| prop3_history_optimum | 3 | 7/50 | 0 | 3 | per_copy | 21/100 | 21/100 | == | True | histories=full (1) |
| prop3_E[R|I=0] | 3 | 7/50 | 0 | 3 | per_copy | 21/100 | 21/100 | == | True | histories=full (1) |
| prop3_every_history_with_I=0 | 3 | 7/50 | 0 | 3 | per_copy | 1 | 1 | == | True | histories=full (1); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 3 | 7/50 | 0 | 3 | per_copy | 21/100 | 21/100 | == | True | histories=full (1); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 3 | 7/50 | 0 | 3 | per_copy | 0 | 0 | == | True | histories=full (1) |
| prop3_share_recovered | 3 | 7/50 | 0 | 3 | per_copy | 0 | 0 | == | True | histories=full (1) |
| prop3_M0_equals_prop1 | 3 | 7/50 | 0 | 3 | per_copy | 21/100 | 21/100 | == | True | histories=full (1); closed_form column = enumerated Prop 1 |
| prop3_full_vs_count_histories | 3 | 7/50 | 0 | 3 | per_copy | 21/100 | 21/100 | == | True |  |
| prop3_history_optimum | 3 | 7/50 | 1 | 3 | pooled | 23883447/125000000 | 23883447/125000000 | == | True | histories=count (8) |
| prop3_E[R|I=0] | 3 | 7/50 | 1 | 3 | pooled | 21/100 | 21/100 | == | True | histories=count (8) |
| prop3_every_history_with_I=0 | 3 | 7/50 | 1 | 3 | pooled | 1 | 1 | == | True | histories=count (8); count of distinct per-history optima |
| prop3_E[R|I=1] | 3 | 7/50 | 1 | 3 | pooled | 21/125 | 21/125 | == | True | histories=count (8) |
| prop3_every_history_with_I=1 | 3 | 7/50 | 1 | 3 | pooled | 1 | 1 | == | True | histories=count (8); count of distinct per-history optima |
| prop3_E[R|I=2] | 3 | 7/50 | 1 | 3 | pooled | 21/200 | 21/200 | == | True | histories=count (8) |
| prop3_every_history_with_I=2 | 3 | 7/50 | 1 | 3 | pooled | 1 | 1 | == | True | histories=count (8); count of distinct per-history optima |
| prop3_E[R|I=3] | 3 | 7/50 | 1 | 3 | pooled | 0 | 0 | == | True | histories=count (8) |
| prop3_every_history_with_I=3 | 3 | 7/50 | 1 | 3 | pooled | 1 | 1 | == | True | histories=count (8); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 3 | 7/50 | 1 | 3 | pooled | 23883447/125000000 | 23883447/125000000 | == | True | histories=count (8); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 3 | 7/50 | 1 | 3 | pooled | 0 | 0 | == | True | histories=count (8) |
| prop3_share_recovered_vs_f/(2-f) | 3 | 7/50 | 1 | 3 | pooled | 112693/1250000 | 7/93 | >= | True | histories=count (8) |
| prop3_history_optimum | 3 | 7/50 | 1 | 3 | pooled | 23883447/125000000 | 23883447/125000000 | == | True | histories=full (8) |
| prop3_E[R|I=0] | 3 | 7/50 | 1 | 3 | pooled | 21/100 | 21/100 | == | True | histories=full (8) |
| prop3_every_history_with_I=0 | 3 | 7/50 | 1 | 3 | pooled | 1 | 1 | == | True | histories=full (8); count of distinct per-history optima |
| prop3_E[R|I=1] | 3 | 7/50 | 1 | 3 | pooled | 21/125 | 21/125 | == | True | histories=full (8) |
| prop3_every_history_with_I=1 | 3 | 7/50 | 1 | 3 | pooled | 1 | 1 | == | True | histories=full (8); count of distinct per-history optima |
| prop3_E[R|I=2] | 3 | 7/50 | 1 | 3 | pooled | 21/200 | 21/200 | == | True | histories=full (8) |
| prop3_every_history_with_I=2 | 3 | 7/50 | 1 | 3 | pooled | 1 | 1 | == | True | histories=full (8); count of distinct per-history optima |
| prop3_E[R|I=3] | 3 | 7/50 | 1 | 3 | pooled | 0 | 0 | == | True | histories=full (8) |
| prop3_every_history_with_I=3 | 3 | 7/50 | 1 | 3 | pooled | 1 | 1 | == | True | histories=full (8); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 3 | 7/50 | 1 | 3 | pooled | 23883447/125000000 | 23883447/125000000 | == | True | histories=full (8); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 3 | 7/50 | 1 | 3 | pooled | 0 | 0 | == | True | histories=full (8) |
| prop3_share_recovered_vs_f/(2-f) | 3 | 7/50 | 1 | 3 | pooled | 112693/1250000 | 7/93 | >= | True | histories=full (8) |
| prop3_full_vs_count_histories | 3 | 7/50 | 1 | 3 | pooled | 23883447/125000000 | 23883447/125000000 | == | True |  |
| prop3_history_optimum | 3 | 7/50 | 1 | 3 | per_copy | 903/5000 | 903/5000 | == | True | histories=count (8) |
| prop3_E[R|I=0] | 3 | 7/50 | 1 | 3 | per_copy | 21/100 | 21/100 | == | True | histories=count (8) |
| prop3_every_history_with_I=0 | 3 | 7/50 | 1 | 3 | per_copy | 1 | 1 | == | True | histories=count (8); count of distinct per-history optima |
| prop3_E[R|I=1] | 3 | 7/50 | 1 | 3 | per_copy | 7/50 | 7/50 | == | True | histories=count (8) |
| prop3_every_history_with_I=1 | 3 | 7/50 | 1 | 3 | per_copy | 1 | 1 | == | True | histories=count (8); count of distinct per-history optima |
| prop3_E[R|I=2] | 3 | 7/50 | 1 | 3 | per_copy | 7/100 | 7/100 | == | True | histories=count (8) |
| prop3_every_history_with_I=2 | 3 | 7/50 | 1 | 3 | per_copy | 1 | 1 | == | True | histories=count (8); count of distinct per-history optima |
| prop3_E[R|I=3] | 3 | 7/50 | 1 | 3 | per_copy | 0 | 0 | == | True | histories=count (8) |
| prop3_every_history_with_I=3 | 3 | 7/50 | 1 | 3 | per_copy | 1 | 1 | == | True | histories=count (8); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 3 | 7/50 | 1 | 3 | per_copy | 903/5000 | 903/5000 | == | True | histories=count (8); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 3 | 7/50 | 1 | 3 | per_copy | 0 | 0 | == | True | histories=count (8) |
| prop3_share_recovered | 3 | 7/50 | 1 | 3 | per_copy | 7/50 | 7/50 | == | True | histories=count (8) |
| prop3_history_optimum | 3 | 7/50 | 1 | 3 | per_copy | 903/5000 | 903/5000 | == | True | histories=full (8) |
| prop3_E[R|I=0] | 3 | 7/50 | 1 | 3 | per_copy | 21/100 | 21/100 | == | True | histories=full (8) |
| prop3_every_history_with_I=0 | 3 | 7/50 | 1 | 3 | per_copy | 1 | 1 | == | True | histories=full (8); count of distinct per-history optima |
| prop3_E[R|I=1] | 3 | 7/50 | 1 | 3 | per_copy | 7/50 | 7/50 | == | True | histories=full (8) |
| prop3_every_history_with_I=1 | 3 | 7/50 | 1 | 3 | per_copy | 1 | 1 | == | True | histories=full (8); count of distinct per-history optima |
| prop3_E[R|I=2] | 3 | 7/50 | 1 | 3 | per_copy | 7/100 | 7/100 | == | True | histories=full (8) |
| prop3_every_history_with_I=2 | 3 | 7/50 | 1 | 3 | per_copy | 1 | 1 | == | True | histories=full (8); count of distinct per-history optima |
| prop3_E[R|I=3] | 3 | 7/50 | 1 | 3 | per_copy | 0 | 0 | == | True | histories=full (8) |
| prop3_every_history_with_I=3 | 3 | 7/50 | 1 | 3 | per_copy | 1 | 1 | == | True | histories=full (8); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 3 | 7/50 | 1 | 3 | per_copy | 903/5000 | 903/5000 | == | True | histories=full (8); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 3 | 7/50 | 1 | 3 | per_copy | 0 | 0 | == | True | histories=full (8) |
| prop3_share_recovered | 3 | 7/50 | 1 | 3 | per_copy | 7/50 | 7/50 | == | True | histories=full (8) |
| prop3_full_vs_count_histories | 3 | 7/50 | 1 | 3 | per_copy | 903/5000 | 903/5000 | == | True |  |
| prop3_history_optimum | 3 | 7/50 | 2 | 3 | pooled | 2696045059029/15625000000000 | 2696045059029/15625000000000 | == | True | histories=count (27) |
| prop3_E[R|I=0] | 3 | 7/50 | 2 | 3 | pooled | 21/100 | 21/100 | == | True | histories=count (27) |
| prop3_every_history_with_I=0 | 3 | 7/50 | 2 | 3 | pooled | 1 | 1 | == | True | histories=count (27); count of distinct per-history optima |
| prop3_E[R|I=1] | 3 | 7/50 | 2 | 3 | pooled | 21/125 | 21/125 | == | True | histories=count (27) |
| prop3_every_history_with_I=1 | 3 | 7/50 | 2 | 3 | pooled | 1 | 1 | == | True | histories=count (27); count of distinct per-history optima |
| prop3_E[R|I=2] | 3 | 7/50 | 2 | 3 | pooled | 21/200 | 21/200 | == | True | histories=count (27) |
| prop3_every_history_with_I=2 | 3 | 7/50 | 2 | 3 | pooled | 1 | 1 | == | True | histories=count (27); count of distinct per-history optima |
| prop3_E[R|I=3] | 3 | 7/50 | 2 | 3 | pooled | 0 | 0 | == | True | histories=count (27) |
| prop3_every_history_with_I=3 | 3 | 7/50 | 2 | 3 | pooled | 1 | 1 | == | True | histories=count (27); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 3 | 7/50 | 2 | 3 | pooled | 2696045059029/15625000000000 | 2696045059029/15625000000000 | == | True | histories=count (27); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 3 | 7/50 | 2 | 3 | pooled | 0 | 0 | == | True | histories=count (27) |
| prop3_share_recovered_vs_f/(2-f) | 3 | 7/50 | 2 | 3 | pooled | 27866901951/156250000000 | 651/4349 | >= | True | histories=count (27) |
| prop3_history_optimum | 3 | 7/50 | 2 | 3 | pooled | 2696045059029/15625000000000 | 2696045059029/15625000000000 | == | True | histories=full (64) |
| prop3_E[R|I=0] | 3 | 7/50 | 2 | 3 | pooled | 21/100 | 21/100 | == | True | histories=full (64) |
| prop3_every_history_with_I=0 | 3 | 7/50 | 2 | 3 | pooled | 1 | 1 | == | True | histories=full (64); count of distinct per-history optima |
| prop3_E[R|I=1] | 3 | 7/50 | 2 | 3 | pooled | 21/125 | 21/125 | == | True | histories=full (64) |
| prop3_every_history_with_I=1 | 3 | 7/50 | 2 | 3 | pooled | 1 | 1 | == | True | histories=full (64); count of distinct per-history optima |
| prop3_E[R|I=2] | 3 | 7/50 | 2 | 3 | pooled | 21/200 | 21/200 | == | True | histories=full (64) |
| prop3_every_history_with_I=2 | 3 | 7/50 | 2 | 3 | pooled | 1 | 1 | == | True | histories=full (64); count of distinct per-history optima |
| prop3_E[R|I=3] | 3 | 7/50 | 2 | 3 | pooled | 0 | 0 | == | True | histories=full (64) |
| prop3_every_history_with_I=3 | 3 | 7/50 | 2 | 3 | pooled | 1 | 1 | == | True | histories=full (64); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 3 | 7/50 | 2 | 3 | pooled | 2696045059029/15625000000000 | 2696045059029/15625000000000 | == | True | histories=full (64); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 3 | 7/50 | 2 | 3 | pooled | 0 | 0 | == | True | histories=full (64) |
| prop3_share_recovered_vs_f/(2-f) | 3 | 7/50 | 2 | 3 | pooled | 27866901951/156250000000 | 651/4349 | >= | True | histories=full (64) |
| prop3_full_vs_count_histories | 3 | 7/50 | 2 | 3 | pooled | 2696045059029/15625000000000 | 2696045059029/15625000000000 | == | True |  |
| prop3_history_optimum | 3 | 7/50 | 2 | 3 | per_copy | 38829/250000 | 38829/250000 | == | True | histories=count (27) |
| prop3_E[R|I=0] | 3 | 7/50 | 2 | 3 | per_copy | 21/100 | 21/100 | == | True | histories=count (27) |
| prop3_every_history_with_I=0 | 3 | 7/50 | 2 | 3 | per_copy | 1 | 1 | == | True | histories=count (27); count of distinct per-history optima |
| prop3_E[R|I=1] | 3 | 7/50 | 2 | 3 | per_copy | 7/50 | 7/50 | == | True | histories=count (27) |
| prop3_every_history_with_I=1 | 3 | 7/50 | 2 | 3 | per_copy | 1 | 1 | == | True | histories=count (27); count of distinct per-history optima |
| prop3_E[R|I=2] | 3 | 7/50 | 2 | 3 | per_copy | 7/100 | 7/100 | == | True | histories=count (27) |
| prop3_every_history_with_I=2 | 3 | 7/50 | 2 | 3 | per_copy | 1 | 1 | == | True | histories=count (27); count of distinct per-history optima |
| prop3_E[R|I=3] | 3 | 7/50 | 2 | 3 | per_copy | 0 | 0 | == | True | histories=count (27) |
| prop3_every_history_with_I=3 | 3 | 7/50 | 2 | 3 | per_copy | 1 | 1 | == | True | histories=count (27); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 3 | 7/50 | 2 | 3 | per_copy | 38829/250000 | 38829/250000 | == | True | histories=count (27); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 3 | 7/50 | 2 | 3 | per_copy | 0 | 0 | == | True | histories=count (27) |
| prop3_share_recovered | 3 | 7/50 | 2 | 3 | per_copy | 651/2500 | 651/2500 | == | True | histories=count (27) |
| prop3_history_optimum | 3 | 7/50 | 2 | 3 | per_copy | 38829/250000 | 38829/250000 | == | True | histories=full (64) |
| prop3_E[R|I=0] | 3 | 7/50 | 2 | 3 | per_copy | 21/100 | 21/100 | == | True | histories=full (64) |
| prop3_every_history_with_I=0 | 3 | 7/50 | 2 | 3 | per_copy | 1 | 1 | == | True | histories=full (64); count of distinct per-history optima |
| prop3_E[R|I=1] | 3 | 7/50 | 2 | 3 | per_copy | 7/50 | 7/50 | == | True | histories=full (64) |
| prop3_every_history_with_I=1 | 3 | 7/50 | 2 | 3 | per_copy | 1 | 1 | == | True | histories=full (64); count of distinct per-history optima |
| prop3_E[R|I=2] | 3 | 7/50 | 2 | 3 | per_copy | 7/100 | 7/100 | == | True | histories=full (64) |
| prop3_every_history_with_I=2 | 3 | 7/50 | 2 | 3 | per_copy | 1 | 1 | == | True | histories=full (64); count of distinct per-history optima |
| prop3_E[R|I=3] | 3 | 7/50 | 2 | 3 | per_copy | 0 | 0 | == | True | histories=full (64) |
| prop3_every_history_with_I=3 | 3 | 7/50 | 2 | 3 | per_copy | 1 | 1 | == | True | histories=full (64); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 3 | 7/50 | 2 | 3 | per_copy | 38829/250000 | 38829/250000 | == | True | histories=full (64); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 3 | 7/50 | 2 | 3 | per_copy | 0 | 0 | == | True | histories=full (64) |
| prop3_share_recovered | 3 | 7/50 | 2 | 3 | per_copy | 651/2500 | 651/2500 | == | True | histories=full (64) |
| prop3_full_vs_count_histories | 3 | 7/50 | 2 | 3 | per_copy | 38829/250000 | 38829/250000 | == | True |  |
| prop3_history_optimum | 3 | 7/50 | 3 | 3 | pooled | 302316492453923703/1953125000000000000 | 302316492453923703/1953125000000000000 | == | True | histories=count (64) |
| prop3_E[R|I=0] | 3 | 7/50 | 3 | 3 | pooled | 21/100 | 21/100 | == | True | histories=count (64) |
| prop3_every_history_with_I=0 | 3 | 7/50 | 3 | 3 | pooled | 1 | 1 | == | True | histories=count (64); count of distinct per-history optima |
| prop3_E[R|I=1] | 3 | 7/50 | 3 | 3 | pooled | 21/125 | 21/125 | == | True | histories=count (64) |
| prop3_every_history_with_I=1 | 3 | 7/50 | 3 | 3 | pooled | 1 | 1 | == | True | histories=count (64); count of distinct per-history optima |
| prop3_E[R|I=2] | 3 | 7/50 | 3 | 3 | pooled | 21/200 | 21/200 | == | True | histories=count (64) |
| prop3_every_history_with_I=2 | 3 | 7/50 | 3 | 3 | pooled | 1 | 1 | == | True | histories=count (64); count of distinct per-history optima |
| prop3_E[R|I=3] | 3 | 7/50 | 3 | 3 | pooled | 0 | 0 | == | True | histories=count (64) |
| prop3_every_history_with_I=3 | 3 | 7/50 | 3 | 3 | pooled | 1 | 1 | == | True | histories=count (64); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 3 | 7/50 | 3 | 3 | pooled | 302316492453923703/1953125000000000000 | 302316492453923703/1953125000000000000 | == | True | histories=count (64); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 3 | 7/50 | 3 | 3 | pooled | 0 | 0 | == | True | histories=count (64) |
| prop3_share_recovered_vs_f/(2-f) | 3 | 7/50 | 3 | 3 | pooled | 5135226549813157/19531250000000000 | 45493/204507 | >= | True | histories=count (64) |
| prop3_history_optimum | 3 | 7/50 | 3 | 3 | per_copy | 1669647/12500000 | 1669647/12500000 | == | True | histories=count (64) |
| prop3_E[R|I=0] | 3 | 7/50 | 3 | 3 | per_copy | 21/100 | 21/100 | == | True | histories=count (64) |
| prop3_every_history_with_I=0 | 3 | 7/50 | 3 | 3 | per_copy | 1 | 1 | == | True | histories=count (64); count of distinct per-history optima |
| prop3_E[R|I=1] | 3 | 7/50 | 3 | 3 | per_copy | 7/50 | 7/50 | == | True | histories=count (64) |
| prop3_every_history_with_I=1 | 3 | 7/50 | 3 | 3 | per_copy | 1 | 1 | == | True | histories=count (64); count of distinct per-history optima |
| prop3_E[R|I=2] | 3 | 7/50 | 3 | 3 | per_copy | 7/100 | 7/100 | == | True | histories=count (64) |
| prop3_every_history_with_I=2 | 3 | 7/50 | 3 | 3 | per_copy | 1 | 1 | == | True | histories=count (64); count of distinct per-history optima |
| prop3_E[R|I=3] | 3 | 7/50 | 3 | 3 | per_copy | 0 | 0 | == | True | histories=count (64) |
| prop3_every_history_with_I=3 | 3 | 7/50 | 3 | 3 | per_copy | 1 | 1 | == | True | histories=count (64); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 3 | 7/50 | 3 | 3 | per_copy | 1669647/12500000 | 1669647/12500000 | == | True | histories=count (64); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 3 | 7/50 | 3 | 3 | per_copy | 0 | 0 | == | True | histories=count (64) |
| prop3_share_recovered | 3 | 7/50 | 3 | 3 | per_copy | 45493/125000 | 45493/125000 | == | True | histories=count (64) |
| prop3_history_optimum | 3 | 7/50 | 5 | 3 | pooled | 3737998739037596014525200447/30517578125000000000000000000 | 3737998739037596014525200447/30517578125000000000000000000 | == | True | histories=count (216) |
| prop3_E[R|I=0] | 3 | 7/50 | 5 | 3 | pooled | 21/100 | 21/100 | == | True | histories=count (216) |
| prop3_every_history_with_I=0 | 3 | 7/50 | 5 | 3 | pooled | 1 | 1 | == | True | histories=count (216); count of distinct per-history optima |
| prop3_E[R|I=1] | 3 | 7/50 | 5 | 3 | pooled | 21/125 | 21/125 | == | True | histories=count (216) |
| prop3_every_history_with_I=1 | 3 | 7/50 | 5 | 3 | pooled | 1 | 1 | == | True | histories=count (216); count of distinct per-history optima |
| prop3_E[R|I=2] | 3 | 7/50 | 5 | 3 | pooled | 21/200 | 21/200 | == | True | histories=count (216) |
| prop3_every_history_with_I=2 | 3 | 7/50 | 5 | 3 | pooled | 1 | 1 | == | True | histories=count (216); count of distinct per-history optima |
| prop3_E[R|I=3] | 3 | 7/50 | 5 | 3 | pooled | 0 | 0 | == | True | histories=count (216) |
| prop3_every_history_with_I=3 | 3 | 7/50 | 5 | 3 | pooled | 1 | 1 | == | True | histories=count (216); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 3 | 7/50 | 5 | 3 | pooled | 3737998739037596014525200447/30517578125000000000000000000 | 3737998739037596014525200447/30517578125000000000000000000 | == | True | histories=count (216); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 3 | 7/50 | 5 | 3 | pooled | 0 | 0 | == | True | histories=count (216) |
| prop3_share_recovered_vs_f/(2-f) | 3 | 7/50 | 5 | 3 | pooled | 127175841295828761213085693/305175781250000000000000000 | 165491557/459508443 | >= | True | histories=count (216) |
| prop3_history_optimum | 3 | 7/50 | 5 | 3 | per_copy | 3087177303/31250000000 | 3087177303/31250000000 | == | True | histories=count (216) |
| prop3_E[R|I=0] | 3 | 7/50 | 5 | 3 | per_copy | 21/100 | 21/100 | == | True | histories=count (216) |
| prop3_every_history_with_I=0 | 3 | 7/50 | 5 | 3 | per_copy | 1 | 1 | == | True | histories=count (216); count of distinct per-history optima |
| prop3_E[R|I=1] | 3 | 7/50 | 5 | 3 | per_copy | 7/50 | 7/50 | == | True | histories=count (216) |
| prop3_every_history_with_I=1 | 3 | 7/50 | 5 | 3 | per_copy | 1 | 1 | == | True | histories=count (216); count of distinct per-history optima |
| prop3_E[R|I=2] | 3 | 7/50 | 5 | 3 | per_copy | 7/100 | 7/100 | == | True | histories=count (216) |
| prop3_every_history_with_I=2 | 3 | 7/50 | 5 | 3 | per_copy | 1 | 1 | == | True | histories=count (216); count of distinct per-history optima |
| prop3_E[R|I=3] | 3 | 7/50 | 5 | 3 | per_copy | 0 | 0 | == | True | histories=count (216) |
| prop3_every_history_with_I=3 | 3 | 7/50 | 5 | 3 | per_copy | 1 | 1 | == | True | histories=count (216); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 3 | 7/50 | 5 | 3 | per_copy | 3087177303/31250000000 | 3087177303/31250000000 | == | True | histories=count (216); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 3 | 7/50 | 5 | 3 | per_copy | 0 | 0 | == | True | histories=count (216) |
| prop3_share_recovered | 3 | 7/50 | 5 | 3 | per_copy | 165491557/312500000 | 165491557/312500000 | == | True | histories=count (216) |
| prop1_oblivious_optimum | 4 | 1/2 |  | 4 | pooled | 1 | 1 | == | True | 2200 orbits / 972032 schedules |
| prop1_posterior_optimum | 4 | 1/2 |  | 4 | pooled | 0 | 0 | == | True |  |
| prop1_hedge_all_A_max_R_over_realizations | 4 | 1/2 |  | 4 | pooled | 0 | 0 | == | True |  |
| prop1_oblivious_optimum | 4 | 1/2 |  | 4 | per_copy | 1 | 1 | == | True | 4845 orbits / 614656 schedules |
| prop1_posterior_optimum | 4 | 1/2 |  | 4 | per_copy | 0 | 0 | == | True |  |
| prop1_hedge_all_A_max_R_over_realizations | 4 | 1/2 |  | 4 | per_copy | 0 | 0 | == | True |  |
| gap_c | 4 | 1/2 |  | 0 | pooled | 0 | 0 | == | True |  |
| gap_c_oblivious_optimum | 4 | 1/2 |  | 0 | pooled | 2 | 2 | == | True |  |
| gap_c_posterior_optimum | 4 | 1/2 |  | 0 | pooled | 2 | 2 | == | True |  |
| gap_c | 4 | 1/2 |  | 1 | pooled | 1/4 | 1/4 | == | True |  |
| gap_c_oblivious_optimum | 4 | 1/2 |  | 1 | pooled | 7/4 | 7/4 | == | True |  |
| gap_c_posterior_optimum | 4 | 1/2 |  | 1 | pooled | 3/2 | 3/2 | == | True |  |
| gap_c | 4 | 1/2 |  | 2 | pooled | 1/2 | 1/2 | == | True |  |
| gap_c_oblivious_optimum | 4 | 1/2 |  | 2 | pooled | 3/2 | 3/2 | == | True |  |
| gap_c_posterior_optimum | 4 | 1/2 |  | 2 | pooled | 1 | 1 | == | True |  |
| gap_c | 4 | 1/2 |  | 3 | pooled | 3/4 | 3/4 | == | True |  |
| gap_c_oblivious_optimum | 4 | 1/2 |  | 3 | pooled | 5/4 | 5/4 | == | True |  |
| gap_c_posterior_optimum | 4 | 1/2 |  | 3 | pooled | 1/2 | 1/2 | == | True |  |
| gap_c | 4 | 1/2 |  | 4 | pooled | 1 | 1 | == | True |  |
| gap_c_oblivious_optimum | 4 | 1/2 |  | 4 | pooled | 1 | 1 | == | True |  |
| gap_c_posterior_optimum | 4 | 1/2 |  | 4 | pooled | 0 | 0 | == | True |  |
| gap_c | 4 | 1/2 |  | 5 | pooled | 3/4 | 3/4 | == | True |  |
| gap_c_oblivious_optimum | 4 | 1/2 |  | 5 | pooled | 3/4 | 3/4 | == | True |  |
| gap_c_posterior_optimum | 4 | 1/2 |  | 5 | pooled | 0 | 0 | == | True |  |
| gap_c | 4 | 1/2 |  | 6 | pooled | 1/2 | 1/2 | == | True |  |
| gap_c_oblivious_optimum | 4 | 1/2 |  | 6 | pooled | 1/2 | 1/2 | == | True |  |
| gap_c_posterior_optimum | 4 | 1/2 |  | 6 | pooled | 0 | 0 | == | True |  |
| gap_c | 4 | 1/2 |  | 7 | pooled | 1/4 | 1/4 | == | True |  |
| gap_c_oblivious_optimum | 4 | 1/2 |  | 7 | pooled | 1/4 | 1/4 | == | True |  |
| gap_c_posterior_optimum | 4 | 1/2 |  | 7 | pooled | 0 | 0 | == | True |  |
| gap_c | 4 | 1/2 |  | 8 | pooled | 0 | 0 | == | True |  |
| gap_c_oblivious_optimum | 4 | 1/2 |  | 8 | pooled | 0 | 0 | == | True |  |
| gap_c_posterior_optimum | 4 | 1/2 |  | 8 | pooled | 0 | 0 | == | True |  |
| gap_c | 4 | 1/2 |  | 0 | per_copy | 0 | 0 | == | True |  |
| gap_c_oblivious_optimum | 4 | 1/2 |  | 0 | per_copy | 2 | 2 | == | True |  |
| gap_c_posterior_optimum | 4 | 1/2 |  | 0 | per_copy | 2 | 2 | == | True |  |
| gap_c | 4 | 1/2 |  | 4 | per_copy | 1 | 1 | == | True |  |
| gap_c_oblivious_optimum | 4 | 1/2 |  | 4 | per_copy | 1 | 1 | == | True |  |
| gap_c_posterior_optimum | 4 | 1/2 |  | 4 | per_copy | 0 | 0 | == | True |  |
| gap_c | 4 | 1/2 |  | 8 | per_copy | 0 | 0 | == | True |  |
| gap_c_oblivious_optimum | 4 | 1/2 |  | 8 | per_copy | 0 | 0 | == | True |  |
| gap_c_posterior_optimum | 4 | 1/2 |  | 8 | per_copy | 0 | 0 | == | True |  |
| prop3_history_optimum | 4 | 1/2 | 0 | 4 | pooled | 1 | 1 | == | True | histories=count (1) |
| prop3_E[R|I=0] | 4 | 1/2 | 0 | 4 | pooled | 1 | 1 | == | True | histories=count (1) |
| prop3_every_history_with_I=0 | 4 | 1/2 | 0 | 4 | pooled | 1 | 1 | == | True | histories=count (1); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 4 | 1/2 | 0 | 4 | pooled | 1 | 1 | == | True | histories=count (1); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 4 | 1/2 | 0 | 4 | pooled | 0 | 0 | == | True | histories=count (1) |
| prop3_share_recovered_vs_f/(2-f) | 4 | 1/2 | 0 | 4 | pooled | 0 | 0 | >= | True | histories=count (1) |
| prop3_M0_equals_prop1 | 4 | 1/2 | 0 | 4 | pooled | 1 | 1 | == | True | histories=count (1); closed_form column = enumerated Prop 1 |
| prop3_history_optimum | 4 | 1/2 | 0 | 4 | pooled | 1 | 1 | == | True | histories=full (1) |
| prop3_E[R|I=0] | 4 | 1/2 | 0 | 4 | pooled | 1 | 1 | == | True | histories=full (1) |
| prop3_every_history_with_I=0 | 4 | 1/2 | 0 | 4 | pooled | 1 | 1 | == | True | histories=full (1); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 4 | 1/2 | 0 | 4 | pooled | 1 | 1 | == | True | histories=full (1); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 4 | 1/2 | 0 | 4 | pooled | 0 | 0 | == | True | histories=full (1) |
| prop3_share_recovered_vs_f/(2-f) | 4 | 1/2 | 0 | 4 | pooled | 0 | 0 | >= | True | histories=full (1) |
| prop3_M0_equals_prop1 | 4 | 1/2 | 0 | 4 | pooled | 1 | 1 | == | True | histories=full (1); closed_form column = enumerated Prop 1 |
| prop3_full_vs_count_histories | 4 | 1/2 | 0 | 4 | pooled | 1 | 1 | == | True |  |
| prop3_history_optimum | 4 | 1/2 | 0 | 4 | per_copy | 1 | 1 | == | True | histories=count (1) |
| prop3_E[R|I=0] | 4 | 1/2 | 0 | 4 | per_copy | 1 | 1 | == | True | histories=count (1) |
| prop3_every_history_with_I=0 | 4 | 1/2 | 0 | 4 | per_copy | 1 | 1 | == | True | histories=count (1); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 4 | 1/2 | 0 | 4 | per_copy | 1 | 1 | == | True | histories=count (1); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 4 | 1/2 | 0 | 4 | per_copy | 0 | 0 | == | True | histories=count (1) |
| prop3_share_recovered | 4 | 1/2 | 0 | 4 | per_copy | 0 | 0 | == | True | histories=count (1) |
| prop3_M0_equals_prop1 | 4 | 1/2 | 0 | 4 | per_copy | 1 | 1 | == | True | histories=count (1); closed_form column = enumerated Prop 1 |
| prop3_history_optimum | 4 | 1/2 | 0 | 4 | per_copy | 1 | 1 | == | True | histories=full (1) |
| prop3_E[R|I=0] | 4 | 1/2 | 0 | 4 | per_copy | 1 | 1 | == | True | histories=full (1) |
| prop3_every_history_with_I=0 | 4 | 1/2 | 0 | 4 | per_copy | 1 | 1 | == | True | histories=full (1); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 4 | 1/2 | 0 | 4 | per_copy | 1 | 1 | == | True | histories=full (1); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 4 | 1/2 | 0 | 4 | per_copy | 0 | 0 | == | True | histories=full (1) |
| prop3_share_recovered | 4 | 1/2 | 0 | 4 | per_copy | 0 | 0 | == | True | histories=full (1) |
| prop3_M0_equals_prop1 | 4 | 1/2 | 0 | 4 | per_copy | 1 | 1 | == | True | histories=full (1); closed_form column = enumerated Prop 1 |
| prop3_full_vs_count_histories | 4 | 1/2 | 0 | 4 | per_copy | 1 | 1 | == | True |  |
| prop3_history_optimum | 4 | 1/2 | 1 | 4 | pooled | 351/560 | 351/560 | == | True | histories=count (16) |
| prop3_E[R|I=0] | 4 | 1/2 | 1 | 4 | pooled | 1 | 1 | == | True | histories=count (16) |
| prop3_every_history_with_I=0 | 4 | 1/2 | 1 | 4 | pooled | 1 | 1 | == | True | histories=count (16); count of distinct per-history optima |
| prop3_E[R|I=1] | 4 | 1/2 | 1 | 4 | pooled | 6/7 | 6/7 | == | True | histories=count (16) |
| prop3_every_history_with_I=1 | 4 | 1/2 | 1 | 4 | pooled | 1 | 1 | == | True | histories=count (16); count of distinct per-history optima |
| prop3_E[R|I=2] | 4 | 1/2 | 1 | 4 | pooled | 2/3 | 2/3 | == | True | histories=count (16) |
| prop3_every_history_with_I=2 | 4 | 1/2 | 1 | 4 | pooled | 1 | 1 | == | True | histories=count (16); count of distinct per-history optima |
| prop3_E[R|I=3] | 4 | 1/2 | 1 | 4 | pooled | 2/5 | 2/5 | == | True | histories=count (16) |
| prop3_every_history_with_I=3 | 4 | 1/2 | 1 | 4 | pooled | 1 | 1 | == | True | histories=count (16); count of distinct per-history optima |
| prop3_E[R|I=4] | 4 | 1/2 | 1 | 4 | pooled | 0 | 0 | == | True | histories=count (16) |
| prop3_every_history_with_I=4 | 4 | 1/2 | 1 | 4 | pooled | 1 | 1 | == | True | histories=count (16); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 4 | 1/2 | 1 | 4 | pooled | 351/560 | 351/560 | == | True | histories=count (16); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 4 | 1/2 | 1 | 4 | pooled | 0 | 0 | == | True | histories=count (16) |
| prop3_share_recovered_vs_f/(2-f) | 4 | 1/2 | 1 | 4 | pooled | 209/560 | 1/3 | >= | True | histories=count (16) |
| prop3_history_optimum | 4 | 1/2 | 1 | 4 | pooled | 351/560 | 351/560 | == | True | histories=full (16) |
| prop3_E[R|I=0] | 4 | 1/2 | 1 | 4 | pooled | 1 | 1 | == | True | histories=full (16) |
| prop3_every_history_with_I=0 | 4 | 1/2 | 1 | 4 | pooled | 1 | 1 | == | True | histories=full (16); count of distinct per-history optima |
| prop3_E[R|I=1] | 4 | 1/2 | 1 | 4 | pooled | 6/7 | 6/7 | == | True | histories=full (16) |
| prop3_every_history_with_I=1 | 4 | 1/2 | 1 | 4 | pooled | 1 | 1 | == | True | histories=full (16); count of distinct per-history optima |
| prop3_E[R|I=2] | 4 | 1/2 | 1 | 4 | pooled | 2/3 | 2/3 | == | True | histories=full (16) |
| prop3_every_history_with_I=2 | 4 | 1/2 | 1 | 4 | pooled | 1 | 1 | == | True | histories=full (16); count of distinct per-history optima |
| prop3_E[R|I=3] | 4 | 1/2 | 1 | 4 | pooled | 2/5 | 2/5 | == | True | histories=full (16) |
| prop3_every_history_with_I=3 | 4 | 1/2 | 1 | 4 | pooled | 1 | 1 | == | True | histories=full (16); count of distinct per-history optima |
| prop3_E[R|I=4] | 4 | 1/2 | 1 | 4 | pooled | 0 | 0 | == | True | histories=full (16) |
| prop3_every_history_with_I=4 | 4 | 1/2 | 1 | 4 | pooled | 1 | 1 | == | True | histories=full (16); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 4 | 1/2 | 1 | 4 | pooled | 351/560 | 351/560 | == | True | histories=full (16); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 4 | 1/2 | 1 | 4 | pooled | 0 | 0 | == | True | histories=full (16) |
| prop3_share_recovered_vs_f/(2-f) | 4 | 1/2 | 1 | 4 | pooled | 209/560 | 1/3 | >= | True | histories=full (16) |
| prop3_full_vs_count_histories | 4 | 1/2 | 1 | 4 | pooled | 351/560 | 351/560 | == | True |  |
| prop3_history_optimum | 4 | 1/2 | 1 | 4 | per_copy | 1/2 | 1/2 | == | True | histories=count (16) |
| prop3_E[R|I=0] | 4 | 1/2 | 1 | 4 | per_copy | 1 | 1 | == | True | histories=count (16) |
| prop3_every_history_with_I=0 | 4 | 1/2 | 1 | 4 | per_copy | 1 | 1 | == | True | histories=count (16); count of distinct per-history optima |
| prop3_E[R|I=1] | 4 | 1/2 | 1 | 4 | per_copy | 3/4 | 3/4 | == | True | histories=count (16) |
| prop3_every_history_with_I=1 | 4 | 1/2 | 1 | 4 | per_copy | 1 | 1 | == | True | histories=count (16); count of distinct per-history optima |
| prop3_E[R|I=2] | 4 | 1/2 | 1 | 4 | per_copy | 1/2 | 1/2 | == | True | histories=count (16) |
| prop3_every_history_with_I=2 | 4 | 1/2 | 1 | 4 | per_copy | 1 | 1 | == | True | histories=count (16); count of distinct per-history optima |
| prop3_E[R|I=3] | 4 | 1/2 | 1 | 4 | per_copy | 1/4 | 1/4 | == | True | histories=count (16) |
| prop3_every_history_with_I=3 | 4 | 1/2 | 1 | 4 | per_copy | 1 | 1 | == | True | histories=count (16); count of distinct per-history optima |
| prop3_E[R|I=4] | 4 | 1/2 | 1 | 4 | per_copy | 0 | 0 | == | True | histories=count (16) |
| prop3_every_history_with_I=4 | 4 | 1/2 | 1 | 4 | per_copy | 1 | 1 | == | True | histories=count (16); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 4 | 1/2 | 1 | 4 | per_copy | 1/2 | 1/2 | == | True | histories=count (16); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 4 | 1/2 | 1 | 4 | per_copy | 0 | 0 | == | True | histories=count (16) |
| prop3_share_recovered | 4 | 1/2 | 1 | 4 | per_copy | 1/2 | 1/2 | == | True | histories=count (16) |
| prop3_history_optimum | 4 | 1/2 | 1 | 4 | per_copy | 1/2 | 1/2 | == | True | histories=full (16) |
| prop3_E[R|I=0] | 4 | 1/2 | 1 | 4 | per_copy | 1 | 1 | == | True | histories=full (16) |
| prop3_every_history_with_I=0 | 4 | 1/2 | 1 | 4 | per_copy | 1 | 1 | == | True | histories=full (16); count of distinct per-history optima |
| prop3_E[R|I=1] | 4 | 1/2 | 1 | 4 | per_copy | 3/4 | 3/4 | == | True | histories=full (16) |
| prop3_every_history_with_I=1 | 4 | 1/2 | 1 | 4 | per_copy | 1 | 1 | == | True | histories=full (16); count of distinct per-history optima |
| prop3_E[R|I=2] | 4 | 1/2 | 1 | 4 | per_copy | 1/2 | 1/2 | == | True | histories=full (16) |
| prop3_every_history_with_I=2 | 4 | 1/2 | 1 | 4 | per_copy | 1 | 1 | == | True | histories=full (16); count of distinct per-history optima |
| prop3_E[R|I=3] | 4 | 1/2 | 1 | 4 | per_copy | 1/4 | 1/4 | == | True | histories=full (16) |
| prop3_every_history_with_I=3 | 4 | 1/2 | 1 | 4 | per_copy | 1 | 1 | == | True | histories=full (16); count of distinct per-history optima |
| prop3_E[R|I=4] | 4 | 1/2 | 1 | 4 | per_copy | 0 | 0 | == | True | histories=full (16) |
| prop3_every_history_with_I=4 | 4 | 1/2 | 1 | 4 | per_copy | 1 | 1 | == | True | histories=full (16); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 4 | 1/2 | 1 | 4 | per_copy | 1/2 | 1/2 | == | True | histories=full (16); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 4 | 1/2 | 1 | 4 | per_copy | 0 | 0 | == | True | histories=full (16) |
| prop3_share_recovered | 4 | 1/2 | 1 | 4 | per_copy | 1/2 | 1/2 | == | True | histories=full (16) |
| prop3_full_vs_count_histories | 4 | 1/2 | 1 | 4 | per_copy | 1/2 | 1/2 | == | True |  |
| prop3_history_optimum | 4 | 1/2 | 2 | 4 | pooled | 3167/8960 | 3167/8960 | == | True | histories=count (81) |
| prop3_E[R|I=0] | 4 | 1/2 | 2 | 4 | pooled | 1 | 1 | == | True | histories=count (81) |
| prop3_every_history_with_I=0 | 4 | 1/2 | 2 | 4 | pooled | 1 | 1 | == | True | histories=count (81); count of distinct per-history optima |
| prop3_E[R|I=1] | 4 | 1/2 | 2 | 4 | pooled | 6/7 | 6/7 | == | True | histories=count (81) |
| prop3_every_history_with_I=1 | 4 | 1/2 | 2 | 4 | pooled | 1 | 1 | == | True | histories=count (81); count of distinct per-history optima |
| prop3_E[R|I=2] | 4 | 1/2 | 2 | 4 | pooled | 2/3 | 2/3 | == | True | histories=count (81) |
| prop3_every_history_with_I=2 | 4 | 1/2 | 2 | 4 | pooled | 1 | 1 | == | True | histories=count (81); count of distinct per-history optima |
| prop3_E[R|I=3] | 4 | 1/2 | 2 | 4 | pooled | 2/5 | 2/5 | == | True | histories=count (81) |
| prop3_every_history_with_I=3 | 4 | 1/2 | 2 | 4 | pooled | 1 | 1 | == | True | histories=count (81); count of distinct per-history optima |
| prop3_E[R|I=4] | 4 | 1/2 | 2 | 4 | pooled | 0 | 0 | == | True | histories=count (81) |
| prop3_every_history_with_I=4 | 4 | 1/2 | 2 | 4 | pooled | 1 | 1 | == | True | histories=count (81); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 4 | 1/2 | 2 | 4 | pooled | 3167/8960 | 3167/8960 | == | True | histories=count (81); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 4 | 1/2 | 2 | 4 | pooled | 0 | 0 | == | True | histories=count (81) |
| prop3_share_recovered_vs_f/(2-f) | 4 | 1/2 | 2 | 4 | pooled | 5793/8960 | 3/5 | >= | True | histories=count (81) |
| prop3_history_optimum | 4 | 1/2 | 2 | 4 | pooled | 3167/8960 | 3167/8960 | == | True | histories=full (256) |
| prop3_E[R|I=0] | 4 | 1/2 | 2 | 4 | pooled | 1 | 1 | == | True | histories=full (256) |
| prop3_every_history_with_I=0 | 4 | 1/2 | 2 | 4 | pooled | 1 | 1 | == | True | histories=full (256); count of distinct per-history optima |
| prop3_E[R|I=1] | 4 | 1/2 | 2 | 4 | pooled | 6/7 | 6/7 | == | True | histories=full (256) |
| prop3_every_history_with_I=1 | 4 | 1/2 | 2 | 4 | pooled | 1 | 1 | == | True | histories=full (256); count of distinct per-history optima |
| prop3_E[R|I=2] | 4 | 1/2 | 2 | 4 | pooled | 2/3 | 2/3 | == | True | histories=full (256) |
| prop3_every_history_with_I=2 | 4 | 1/2 | 2 | 4 | pooled | 1 | 1 | == | True | histories=full (256); count of distinct per-history optima |
| prop3_E[R|I=3] | 4 | 1/2 | 2 | 4 | pooled | 2/5 | 2/5 | == | True | histories=full (256) |
| prop3_every_history_with_I=3 | 4 | 1/2 | 2 | 4 | pooled | 1 | 1 | == | True | histories=full (256); count of distinct per-history optima |
| prop3_E[R|I=4] | 4 | 1/2 | 2 | 4 | pooled | 0 | 0 | == | True | histories=full (256) |
| prop3_every_history_with_I=4 | 4 | 1/2 | 2 | 4 | pooled | 1 | 1 | == | True | histories=full (256); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 4 | 1/2 | 2 | 4 | pooled | 3167/8960 | 3167/8960 | == | True | histories=full (256); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 4 | 1/2 | 2 | 4 | pooled | 0 | 0 | == | True | histories=full (256) |
| prop3_share_recovered_vs_f/(2-f) | 4 | 1/2 | 2 | 4 | pooled | 5793/8960 | 3/5 | >= | True | histories=full (256) |
| prop3_full_vs_count_histories | 4 | 1/2 | 2 | 4 | pooled | 3167/8960 | 3167/8960 | == | True |  |
| prop3_history_optimum | 4 | 1/2 | 2 | 4 | per_copy | 1/4 | 1/4 | == | True | histories=count (81) |
| prop3_E[R|I=0] | 4 | 1/2 | 2 | 4 | per_copy | 1 | 1 | == | True | histories=count (81) |
| prop3_every_history_with_I=0 | 4 | 1/2 | 2 | 4 | per_copy | 1 | 1 | == | True | histories=count (81); count of distinct per-history optima |
| prop3_E[R|I=1] | 4 | 1/2 | 2 | 4 | per_copy | 3/4 | 3/4 | == | True | histories=count (81) |
| prop3_every_history_with_I=1 | 4 | 1/2 | 2 | 4 | per_copy | 1 | 1 | == | True | histories=count (81); count of distinct per-history optima |
| prop3_E[R|I=2] | 4 | 1/2 | 2 | 4 | per_copy | 1/2 | 1/2 | == | True | histories=count (81) |
| prop3_every_history_with_I=2 | 4 | 1/2 | 2 | 4 | per_copy | 1 | 1 | == | True | histories=count (81); count of distinct per-history optima |
| prop3_E[R|I=3] | 4 | 1/2 | 2 | 4 | per_copy | 1/4 | 1/4 | == | True | histories=count (81) |
| prop3_every_history_with_I=3 | 4 | 1/2 | 2 | 4 | per_copy | 1 | 1 | == | True | histories=count (81); count of distinct per-history optima |
| prop3_E[R|I=4] | 4 | 1/2 | 2 | 4 | per_copy | 0 | 0 | == | True | histories=count (81) |
| prop3_every_history_with_I=4 | 4 | 1/2 | 2 | 4 | per_copy | 1 | 1 | == | True | histories=count (81); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 4 | 1/2 | 2 | 4 | per_copy | 1/4 | 1/4 | == | True | histories=count (81); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 4 | 1/2 | 2 | 4 | per_copy | 0 | 0 | == | True | histories=count (81) |
| prop3_share_recovered | 4 | 1/2 | 2 | 4 | per_copy | 3/4 | 3/4 | == | True | histories=count (81) |
| prop3_history_optimum | 4 | 1/2 | 2 | 4 | per_copy | 1/4 | 1/4 | == | True | histories=full (256) |
| prop3_E[R|I=0] | 4 | 1/2 | 2 | 4 | per_copy | 1 | 1 | == | True | histories=full (256) |
| prop3_every_history_with_I=0 | 4 | 1/2 | 2 | 4 | per_copy | 1 | 1 | == | True | histories=full (256); count of distinct per-history optima |
| prop3_E[R|I=1] | 4 | 1/2 | 2 | 4 | per_copy | 3/4 | 3/4 | == | True | histories=full (256) |
| prop3_every_history_with_I=1 | 4 | 1/2 | 2 | 4 | per_copy | 1 | 1 | == | True | histories=full (256); count of distinct per-history optima |
| prop3_E[R|I=2] | 4 | 1/2 | 2 | 4 | per_copy | 1/2 | 1/2 | == | True | histories=full (256) |
| prop3_every_history_with_I=2 | 4 | 1/2 | 2 | 4 | per_copy | 1 | 1 | == | True | histories=full (256); count of distinct per-history optima |
| prop3_E[R|I=3] | 4 | 1/2 | 2 | 4 | per_copy | 1/4 | 1/4 | == | True | histories=full (256) |
| prop3_every_history_with_I=3 | 4 | 1/2 | 2 | 4 | per_copy | 1 | 1 | == | True | histories=full (256); count of distinct per-history optima |
| prop3_E[R|I=4] | 4 | 1/2 | 2 | 4 | per_copy | 0 | 0 | == | True | histories=full (256) |
| prop3_every_history_with_I=4 | 4 | 1/2 | 2 | 4 | per_copy | 1 | 1 | == | True | histories=full (256); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 4 | 1/2 | 2 | 4 | per_copy | 1/4 | 1/4 | == | True | histories=full (256); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 4 | 1/2 | 2 | 4 | per_copy | 0 | 0 | == | True | histories=full (256) |
| prop3_share_recovered | 4 | 1/2 | 2 | 4 | per_copy | 3/4 | 3/4 | == | True | histories=full (256) |
| prop3_full_vs_count_histories | 4 | 1/2 | 2 | 4 | per_copy | 1/4 | 1/4 | == | True |  |
| prop3_history_optimum | 4 | 1/2 | 3 | 4 | pooled | 3849/20480 | 3849/20480 | == | True | histories=count (256) |
| prop3_E[R|I=0] | 4 | 1/2 | 3 | 4 | pooled | 1 | 1 | == | True | histories=count (256) |
| prop3_every_history_with_I=0 | 4 | 1/2 | 3 | 4 | pooled | 1 | 1 | == | True | histories=count (256); count of distinct per-history optima |
| prop3_E[R|I=1] | 4 | 1/2 | 3 | 4 | pooled | 6/7 | 6/7 | == | True | histories=count (256) |
| prop3_every_history_with_I=1 | 4 | 1/2 | 3 | 4 | pooled | 1 | 1 | == | True | histories=count (256); count of distinct per-history optima |
| prop3_E[R|I=2] | 4 | 1/2 | 3 | 4 | pooled | 2/3 | 2/3 | == | True | histories=count (256) |
| prop3_every_history_with_I=2 | 4 | 1/2 | 3 | 4 | pooled | 1 | 1 | == | True | histories=count (256); count of distinct per-history optima |
| prop3_E[R|I=3] | 4 | 1/2 | 3 | 4 | pooled | 2/5 | 2/5 | == | True | histories=count (256) |
| prop3_every_history_with_I=3 | 4 | 1/2 | 3 | 4 | pooled | 1 | 1 | == | True | histories=count (256); count of distinct per-history optima |
| prop3_E[R|I=4] | 4 | 1/2 | 3 | 4 | pooled | 0 | 0 | == | True | histories=count (256) |
| prop3_every_history_with_I=4 | 4 | 1/2 | 3 | 4 | pooled | 1 | 1 | == | True | histories=count (256); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 4 | 1/2 | 3 | 4 | pooled | 3849/20480 | 3849/20480 | == | True | histories=count (256); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 4 | 1/2 | 3 | 4 | pooled | 0 | 0 | == | True | histories=count (256) |
| prop3_share_recovered_vs_f/(2-f) | 4 | 1/2 | 3 | 4 | pooled | 16631/20480 | 7/9 | >= | True | histories=count (256) |
| prop3_history_optimum | 4 | 1/2 | 3 | 4 | per_copy | 1/8 | 1/8 | == | True | histories=count (256) |
| prop3_E[R|I=0] | 4 | 1/2 | 3 | 4 | per_copy | 1 | 1 | == | True | histories=count (256) |
| prop3_every_history_with_I=0 | 4 | 1/2 | 3 | 4 | per_copy | 1 | 1 | == | True | histories=count (256); count of distinct per-history optima |
| prop3_E[R|I=1] | 4 | 1/2 | 3 | 4 | per_copy | 3/4 | 3/4 | == | True | histories=count (256) |
| prop3_every_history_with_I=1 | 4 | 1/2 | 3 | 4 | per_copy | 1 | 1 | == | True | histories=count (256); count of distinct per-history optima |
| prop3_E[R|I=2] | 4 | 1/2 | 3 | 4 | per_copy | 1/2 | 1/2 | == | True | histories=count (256) |
| prop3_every_history_with_I=2 | 4 | 1/2 | 3 | 4 | per_copy | 1 | 1 | == | True | histories=count (256); count of distinct per-history optima |
| prop3_E[R|I=3] | 4 | 1/2 | 3 | 4 | per_copy | 1/4 | 1/4 | == | True | histories=count (256) |
| prop3_every_history_with_I=3 | 4 | 1/2 | 3 | 4 | per_copy | 1 | 1 | == | True | histories=count (256); count of distinct per-history optima |
| prop3_E[R|I=4] | 4 | 1/2 | 3 | 4 | per_copy | 0 | 0 | == | True | histories=count (256) |
| prop3_every_history_with_I=4 | 4 | 1/2 | 3 | 4 | per_copy | 1 | 1 | == | True | histories=count (256); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 4 | 1/2 | 3 | 4 | per_copy | 1/8 | 1/8 | == | True | histories=count (256); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 4 | 1/2 | 3 | 4 | per_copy | 0 | 0 | == | True | histories=count (256) |
| prop3_share_recovered | 4 | 1/2 | 3 | 4 | per_copy | 7/8 | 7/8 | == | True | histories=count (256) |
| prop3_history_optimum | 4 | 1/2 | 5 | 4 | pooled | 1806591/36700160 | 1806591/36700160 | == | True | histories=count (1296) |
| prop3_E[R|I=0] | 4 | 1/2 | 5 | 4 | pooled | 1 | 1 | == | True | histories=count (1296) |
| prop3_every_history_with_I=0 | 4 | 1/2 | 5 | 4 | pooled | 1 | 1 | == | True | histories=count (1296); count of distinct per-history optima |
| prop3_E[R|I=1] | 4 | 1/2 | 5 | 4 | pooled | 6/7 | 6/7 | == | True | histories=count (1296) |
| prop3_every_history_with_I=1 | 4 | 1/2 | 5 | 4 | pooled | 1 | 1 | == | True | histories=count (1296); count of distinct per-history optima |
| prop3_E[R|I=2] | 4 | 1/2 | 5 | 4 | pooled | 2/3 | 2/3 | == | True | histories=count (1296) |
| prop3_every_history_with_I=2 | 4 | 1/2 | 5 | 4 | pooled | 1 | 1 | == | True | histories=count (1296); count of distinct per-history optima |
| prop3_E[R|I=3] | 4 | 1/2 | 5 | 4 | pooled | 2/5 | 2/5 | == | True | histories=count (1296) |
| prop3_every_history_with_I=3 | 4 | 1/2 | 5 | 4 | pooled | 1 | 1 | == | True | histories=count (1296); count of distinct per-history optima |
| prop3_E[R|I=4] | 4 | 1/2 | 5 | 4 | pooled | 0 | 0 | == | True | histories=count (1296) |
| prop3_every_history_with_I=4 | 4 | 1/2 | 5 | 4 | pooled | 1 | 1 | == | True | histories=count (1296); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 4 | 1/2 | 5 | 4 | pooled | 1806591/36700160 | 1806591/36700160 | == | True | histories=count (1296); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 4 | 1/2 | 5 | 4 | pooled | 0 | 0 | == | True | histories=count (1296) |
| prop3_share_recovered_vs_f/(2-f) | 4 | 1/2 | 5 | 4 | pooled | 34893569/36700160 | 31/33 | >= | True | histories=count (1296) |
| prop3_history_optimum | 4 | 1/2 | 5 | 4 | per_copy | 1/32 | 1/32 | == | True | histories=count (1296) |
| prop3_E[R|I=0] | 4 | 1/2 | 5 | 4 | per_copy | 1 | 1 | == | True | histories=count (1296) |
| prop3_every_history_with_I=0 | 4 | 1/2 | 5 | 4 | per_copy | 1 | 1 | == | True | histories=count (1296); count of distinct per-history optima |
| prop3_E[R|I=1] | 4 | 1/2 | 5 | 4 | per_copy | 3/4 | 3/4 | == | True | histories=count (1296) |
| prop3_every_history_with_I=1 | 4 | 1/2 | 5 | 4 | per_copy | 1 | 1 | == | True | histories=count (1296); count of distinct per-history optima |
| prop3_E[R|I=2] | 4 | 1/2 | 5 | 4 | per_copy | 1/2 | 1/2 | == | True | histories=count (1296) |
| prop3_every_history_with_I=2 | 4 | 1/2 | 5 | 4 | per_copy | 1 | 1 | == | True | histories=count (1296); count of distinct per-history optima |
| prop3_E[R|I=3] | 4 | 1/2 | 5 | 4 | per_copy | 1/4 | 1/4 | == | True | histories=count (1296) |
| prop3_every_history_with_I=3 | 4 | 1/2 | 5 | 4 | per_copy | 1 | 1 | == | True | histories=count (1296); count of distinct per-history optima |
| prop3_E[R|I=4] | 4 | 1/2 | 5 | 4 | per_copy | 0 | 0 | == | True | histories=count (1296) |
| prop3_every_history_with_I=4 | 4 | 1/2 | 5 | 4 | per_copy | 1 | 1 | == | True | histories=count (1296); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 4 | 1/2 | 5 | 4 | per_copy | 1/32 | 1/32 | == | True | histories=count (1296); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 4 | 1/2 | 5 | 4 | per_copy | 0 | 0 | == | True | histories=count (1296) |
| prop3_share_recovered | 4 | 1/2 | 5 | 4 | per_copy | 31/32 | 31/32 | == | True | histories=count (1296) |
| prop1_oblivious_optimum | 4 | 2/5 |  | 4 | pooled | 4/5 | 4/5 | == | True | 2200 orbits / 972032 schedules |
| prop1_posterior_optimum | 4 | 2/5 |  | 4 | pooled | 0 | 0 | == | True |  |
| prop1_hedge_all_A_max_R_over_realizations | 4 | 2/5 |  | 4 | pooled | 0 | 0 | == | True |  |
| prop1_oblivious_optimum | 4 | 2/5 |  | 4 | per_copy | 4/5 | 4/5 | == | True | 4845 orbits / 614656 schedules |
| prop1_posterior_optimum | 4 | 2/5 |  | 4 | per_copy | 0 | 0 | == | True |  |
| prop1_hedge_all_A_max_R_over_realizations | 4 | 2/5 |  | 4 | per_copy | 0 | 0 | == | True |  |
| gap_c | 4 | 2/5 |  | 0 | pooled | 0 | 0 | == | True |  |
| gap_c_oblivious_optimum | 4 | 2/5 |  | 0 | pooled | 8/5 | 8/5 | == | True |  |
| gap_c_posterior_optimum | 4 | 2/5 |  | 0 | pooled | 8/5 | 8/5 | == | True |  |
| gap_c | 4 | 2/5 |  | 1 | pooled | 1/5 | 1/5 | == | True |  |
| gap_c_oblivious_optimum | 4 | 2/5 |  | 1 | pooled | 7/5 | 7/5 | == | True |  |
| gap_c_posterior_optimum | 4 | 2/5 |  | 1 | pooled | 6/5 | 6/5 | == | True |  |
| gap_c | 4 | 2/5 |  | 2 | pooled | 2/5 | 2/5 | == | True |  |
| gap_c_oblivious_optimum | 4 | 2/5 |  | 2 | pooled | 6/5 | 6/5 | == | True |  |
| gap_c_posterior_optimum | 4 | 2/5 |  | 2 | pooled | 4/5 | 4/5 | == | True |  |
| gap_c | 4 | 2/5 |  | 3 | pooled | 3/5 | 3/5 | == | True |  |
| gap_c_oblivious_optimum | 4 | 2/5 |  | 3 | pooled | 1 | 1 | == | True |  |
| gap_c_posterior_optimum | 4 | 2/5 |  | 3 | pooled | 2/5 | 2/5 | == | True |  |
| gap_c | 4 | 2/5 |  | 4 | pooled | 4/5 | 4/5 | == | True |  |
| gap_c_oblivious_optimum | 4 | 2/5 |  | 4 | pooled | 4/5 | 4/5 | == | True |  |
| gap_c_posterior_optimum | 4 | 2/5 |  | 4 | pooled | 0 | 0 | == | True |  |
| gap_c | 4 | 2/5 |  | 5 | pooled | 3/5 | 3/5 | == | True |  |
| gap_c_oblivious_optimum | 4 | 2/5 |  | 5 | pooled | 3/5 | 3/5 | == | True |  |
| gap_c_posterior_optimum | 4 | 2/5 |  | 5 | pooled | 0 | 0 | == | True |  |
| gap_c | 4 | 2/5 |  | 6 | pooled | 2/5 | 2/5 | == | True |  |
| gap_c_oblivious_optimum | 4 | 2/5 |  | 6 | pooled | 2/5 | 2/5 | == | True |  |
| gap_c_posterior_optimum | 4 | 2/5 |  | 6 | pooled | 0 | 0 | == | True |  |
| gap_c | 4 | 2/5 |  | 7 | pooled | 1/5 | 1/5 | == | True |  |
| gap_c_oblivious_optimum | 4 | 2/5 |  | 7 | pooled | 1/5 | 1/5 | == | True |  |
| gap_c_posterior_optimum | 4 | 2/5 |  | 7 | pooled | 0 | 0 | == | True |  |
| gap_c | 4 | 2/5 |  | 8 | pooled | 0 | 0 | == | True |  |
| gap_c_oblivious_optimum | 4 | 2/5 |  | 8 | pooled | 0 | 0 | == | True |  |
| gap_c_posterior_optimum | 4 | 2/5 |  | 8 | pooled | 0 | 0 | == | True |  |
| gap_c | 4 | 2/5 |  | 0 | per_copy | 0 | 0 | == | True |  |
| gap_c_oblivious_optimum | 4 | 2/5 |  | 0 | per_copy | 8/5 | 8/5 | == | True |  |
| gap_c_posterior_optimum | 4 | 2/5 |  | 0 | per_copy | 8/5 | 8/5 | == | True |  |
| gap_c | 4 | 2/5 |  | 4 | per_copy | 4/5 | 4/5 | == | True |  |
| gap_c_oblivious_optimum | 4 | 2/5 |  | 4 | per_copy | 4/5 | 4/5 | == | True |  |
| gap_c_posterior_optimum | 4 | 2/5 |  | 4 | per_copy | 0 | 0 | == | True |  |
| gap_c | 4 | 2/5 |  | 8 | per_copy | 0 | 0 | == | True |  |
| gap_c_oblivious_optimum | 4 | 2/5 |  | 8 | per_copy | 0 | 0 | == | True |  |
| gap_c_posterior_optimum | 4 | 2/5 |  | 8 | per_copy | 0 | 0 | == | True |  |
| prop3_history_optimum | 4 | 2/5 | 0 | 4 | pooled | 4/5 | 4/5 | == | True | histories=count (1) |
| prop3_E[R|I=0] | 4 | 2/5 | 0 | 4 | pooled | 4/5 | 4/5 | == | True | histories=count (1) |
| prop3_every_history_with_I=0 | 4 | 2/5 | 0 | 4 | pooled | 1 | 1 | == | True | histories=count (1); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 4 | 2/5 | 0 | 4 | pooled | 4/5 | 4/5 | == | True | histories=count (1); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 4 | 2/5 | 0 | 4 | pooled | 0 | 0 | == | True | histories=count (1) |
| prop3_share_recovered_vs_f/(2-f) | 4 | 2/5 | 0 | 4 | pooled | 0 | 0 | >= | True | histories=count (1) |
| prop3_M0_equals_prop1 | 4 | 2/5 | 0 | 4 | pooled | 4/5 | 4/5 | == | True | histories=count (1); closed_form column = enumerated Prop 1 |
| prop3_history_optimum | 4 | 2/5 | 0 | 4 | pooled | 4/5 | 4/5 | == | True | histories=full (1) |
| prop3_E[R|I=0] | 4 | 2/5 | 0 | 4 | pooled | 4/5 | 4/5 | == | True | histories=full (1) |
| prop3_every_history_with_I=0 | 4 | 2/5 | 0 | 4 | pooled | 1 | 1 | == | True | histories=full (1); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 4 | 2/5 | 0 | 4 | pooled | 4/5 | 4/5 | == | True | histories=full (1); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 4 | 2/5 | 0 | 4 | pooled | 0 | 0 | == | True | histories=full (1) |
| prop3_share_recovered_vs_f/(2-f) | 4 | 2/5 | 0 | 4 | pooled | 0 | 0 | >= | True | histories=full (1) |
| prop3_M0_equals_prop1 | 4 | 2/5 | 0 | 4 | pooled | 4/5 | 4/5 | == | True | histories=full (1); closed_form column = enumerated Prop 1 |
| prop3_full_vs_count_histories | 4 | 2/5 | 0 | 4 | pooled | 4/5 | 4/5 | == | True |  |
| prop3_history_optimum | 4 | 2/5 | 0 | 4 | per_copy | 4/5 | 4/5 | == | True | histories=count (1) |
| prop3_E[R|I=0] | 4 | 2/5 | 0 | 4 | per_copy | 4/5 | 4/5 | == | True | histories=count (1) |
| prop3_every_history_with_I=0 | 4 | 2/5 | 0 | 4 | per_copy | 1 | 1 | == | True | histories=count (1); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 4 | 2/5 | 0 | 4 | per_copy | 4/5 | 4/5 | == | True | histories=count (1); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 4 | 2/5 | 0 | 4 | per_copy | 0 | 0 | == | True | histories=count (1) |
| prop3_share_recovered | 4 | 2/5 | 0 | 4 | per_copy | 0 | 0 | == | True | histories=count (1) |
| prop3_M0_equals_prop1 | 4 | 2/5 | 0 | 4 | per_copy | 4/5 | 4/5 | == | True | histories=count (1); closed_form column = enumerated Prop 1 |
| prop3_history_optimum | 4 | 2/5 | 0 | 4 | per_copy | 4/5 | 4/5 | == | True | histories=full (1) |
| prop3_E[R|I=0] | 4 | 2/5 | 0 | 4 | per_copy | 4/5 | 4/5 | == | True | histories=full (1) |
| prop3_every_history_with_I=0 | 4 | 2/5 | 0 | 4 | per_copy | 1 | 1 | == | True | histories=full (1); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 4 | 2/5 | 0 | 4 | per_copy | 4/5 | 4/5 | == | True | histories=full (1); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 4 | 2/5 | 0 | 4 | per_copy | 0 | 0 | == | True | histories=full (1) |
| prop3_share_recovered | 4 | 2/5 | 0 | 4 | per_copy | 0 | 0 | == | True | histories=full (1) |
| prop3_M0_equals_prop1 | 4 | 2/5 | 0 | 4 | per_copy | 4/5 | 4/5 | == | True | histories=full (1); closed_form column = enumerated Prop 1 |
| prop3_full_vs_count_histories | 4 | 2/5 | 0 | 4 | per_copy | 4/5 | 4/5 | == | True |  |
| prop3_history_optimum | 4 | 2/5 | 1 | 4 | pooled | 62796/109375 | 62796/109375 | == | True | histories=count (16) |
| prop3_E[R|I=0] | 4 | 2/5 | 1 | 4 | pooled | 4/5 | 4/5 | == | True | histories=count (16) |
| prop3_every_history_with_I=0 | 4 | 2/5 | 1 | 4 | pooled | 1 | 1 | == | True | histories=count (16); count of distinct per-history optima |
| prop3_E[R|I=1] | 4 | 2/5 | 1 | 4 | pooled | 24/35 | 24/35 | == | True | histories=count (16) |
| prop3_every_history_with_I=1 | 4 | 2/5 | 1 | 4 | pooled | 1 | 1 | == | True | histories=count (16); count of distinct per-history optima |
| prop3_E[R|I=2] | 4 | 2/5 | 1 | 4 | pooled | 8/15 | 8/15 | == | True | histories=count (16) |
| prop3_every_history_with_I=2 | 4 | 2/5 | 1 | 4 | pooled | 1 | 1 | == | True | histories=count (16); count of distinct per-history optima |
| prop3_E[R|I=3] | 4 | 2/5 | 1 | 4 | pooled | 8/25 | 8/25 | == | True | histories=count (16) |
| prop3_every_history_with_I=3 | 4 | 2/5 | 1 | 4 | pooled | 1 | 1 | == | True | histories=count (16); count of distinct per-history optima |
| prop3_E[R|I=4] | 4 | 2/5 | 1 | 4 | pooled | 0 | 0 | == | True | histories=count (16) |
| prop3_every_history_with_I=4 | 4 | 2/5 | 1 | 4 | pooled | 1 | 1 | == | True | histories=count (16); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 4 | 2/5 | 1 | 4 | pooled | 62796/109375 | 62796/109375 | == | True | histories=count (16); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 4 | 2/5 | 1 | 4 | pooled | 0 | 0 | == | True | histories=count (16) |
| prop3_share_recovered_vs_f/(2-f) | 4 | 2/5 | 1 | 4 | pooled | 6176/21875 | 1/4 | >= | True | histories=count (16) |
| prop3_history_optimum | 4 | 2/5 | 1 | 4 | pooled | 62796/109375 | 62796/109375 | == | True | histories=full (16) |
| prop3_E[R|I=0] | 4 | 2/5 | 1 | 4 | pooled | 4/5 | 4/5 | == | True | histories=full (16) |
| prop3_every_history_with_I=0 | 4 | 2/5 | 1 | 4 | pooled | 1 | 1 | == | True | histories=full (16); count of distinct per-history optima |
| prop3_E[R|I=1] | 4 | 2/5 | 1 | 4 | pooled | 24/35 | 24/35 | == | True | histories=full (16) |
| prop3_every_history_with_I=1 | 4 | 2/5 | 1 | 4 | pooled | 1 | 1 | == | True | histories=full (16); count of distinct per-history optima |
| prop3_E[R|I=2] | 4 | 2/5 | 1 | 4 | pooled | 8/15 | 8/15 | == | True | histories=full (16) |
| prop3_every_history_with_I=2 | 4 | 2/5 | 1 | 4 | pooled | 1 | 1 | == | True | histories=full (16); count of distinct per-history optima |
| prop3_E[R|I=3] | 4 | 2/5 | 1 | 4 | pooled | 8/25 | 8/25 | == | True | histories=full (16) |
| prop3_every_history_with_I=3 | 4 | 2/5 | 1 | 4 | pooled | 1 | 1 | == | True | histories=full (16); count of distinct per-history optima |
| prop3_E[R|I=4] | 4 | 2/5 | 1 | 4 | pooled | 0 | 0 | == | True | histories=full (16) |
| prop3_every_history_with_I=4 | 4 | 2/5 | 1 | 4 | pooled | 1 | 1 | == | True | histories=full (16); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 4 | 2/5 | 1 | 4 | pooled | 62796/109375 | 62796/109375 | == | True | histories=full (16); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 4 | 2/5 | 1 | 4 | pooled | 0 | 0 | == | True | histories=full (16) |
| prop3_share_recovered_vs_f/(2-f) | 4 | 2/5 | 1 | 4 | pooled | 6176/21875 | 1/4 | >= | True | histories=full (16) |
| prop3_full_vs_count_histories | 4 | 2/5 | 1 | 4 | pooled | 62796/109375 | 62796/109375 | == | True |  |
| prop3_history_optimum | 4 | 2/5 | 1 | 4 | per_copy | 12/25 | 12/25 | == | True | histories=count (16) |
| prop3_E[R|I=0] | 4 | 2/5 | 1 | 4 | per_copy | 4/5 | 4/5 | == | True | histories=count (16) |
| prop3_every_history_with_I=0 | 4 | 2/5 | 1 | 4 | per_copy | 1 | 1 | == | True | histories=count (16); count of distinct per-history optima |
| prop3_E[R|I=1] | 4 | 2/5 | 1 | 4 | per_copy | 3/5 | 3/5 | == | True | histories=count (16) |
| prop3_every_history_with_I=1 | 4 | 2/5 | 1 | 4 | per_copy | 1 | 1 | == | True | histories=count (16); count of distinct per-history optima |
| prop3_E[R|I=2] | 4 | 2/5 | 1 | 4 | per_copy | 2/5 | 2/5 | == | True | histories=count (16) |
| prop3_every_history_with_I=2 | 4 | 2/5 | 1 | 4 | per_copy | 1 | 1 | == | True | histories=count (16); count of distinct per-history optima |
| prop3_E[R|I=3] | 4 | 2/5 | 1 | 4 | per_copy | 1/5 | 1/5 | == | True | histories=count (16) |
| prop3_every_history_with_I=3 | 4 | 2/5 | 1 | 4 | per_copy | 1 | 1 | == | True | histories=count (16); count of distinct per-history optima |
| prop3_E[R|I=4] | 4 | 2/5 | 1 | 4 | per_copy | 0 | 0 | == | True | histories=count (16) |
| prop3_every_history_with_I=4 | 4 | 2/5 | 1 | 4 | per_copy | 1 | 1 | == | True | histories=count (16); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 4 | 2/5 | 1 | 4 | per_copy | 12/25 | 12/25 | == | True | histories=count (16); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 4 | 2/5 | 1 | 4 | per_copy | 0 | 0 | == | True | histories=count (16) |
| prop3_share_recovered | 4 | 2/5 | 1 | 4 | per_copy | 2/5 | 2/5 | == | True | histories=count (16) |
| prop3_history_optimum | 4 | 2/5 | 1 | 4 | per_copy | 12/25 | 12/25 | == | True | histories=full (16) |
| prop3_E[R|I=0] | 4 | 2/5 | 1 | 4 | per_copy | 4/5 | 4/5 | == | True | histories=full (16) |
| prop3_every_history_with_I=0 | 4 | 2/5 | 1 | 4 | per_copy | 1 | 1 | == | True | histories=full (16); count of distinct per-history optima |
| prop3_E[R|I=1] | 4 | 2/5 | 1 | 4 | per_copy | 3/5 | 3/5 | == | True | histories=full (16) |
| prop3_every_history_with_I=1 | 4 | 2/5 | 1 | 4 | per_copy | 1 | 1 | == | True | histories=full (16); count of distinct per-history optima |
| prop3_E[R|I=2] | 4 | 2/5 | 1 | 4 | per_copy | 2/5 | 2/5 | == | True | histories=full (16) |
| prop3_every_history_with_I=2 | 4 | 2/5 | 1 | 4 | per_copy | 1 | 1 | == | True | histories=full (16); count of distinct per-history optima |
| prop3_E[R|I=3] | 4 | 2/5 | 1 | 4 | per_copy | 1/5 | 1/5 | == | True | histories=full (16) |
| prop3_every_history_with_I=3 | 4 | 2/5 | 1 | 4 | per_copy | 1 | 1 | == | True | histories=full (16); count of distinct per-history optima |
| prop3_E[R|I=4] | 4 | 2/5 | 1 | 4 | per_copy | 0 | 0 | == | True | histories=full (16) |
| prop3_every_history_with_I=4 | 4 | 2/5 | 1 | 4 | per_copy | 1 | 1 | == | True | histories=full (16); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 4 | 2/5 | 1 | 4 | per_copy | 12/25 | 12/25 | == | True | histories=full (16); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 4 | 2/5 | 1 | 4 | per_copy | 0 | 0 | == | True | histories=full (16) |
| prop3_share_recovered | 4 | 2/5 | 1 | 4 | per_copy | 2/5 | 2/5 | == | True | histories=full (16) |
| prop3_full_vs_count_histories | 4 | 2/5 | 1 | 4 | per_copy | 12/25 | 12/25 | == | True |  |
| prop3_history_optimum | 4 | 2/5 | 2 | 4 | pooled | 26386956/68359375 | 26386956/68359375 | == | True | histories=count (81) |
| prop3_E[R|I=0] | 4 | 2/5 | 2 | 4 | pooled | 4/5 | 4/5 | == | True | histories=count (81) |
| prop3_every_history_with_I=0 | 4 | 2/5 | 2 | 4 | pooled | 1 | 1 | == | True | histories=count (81); count of distinct per-history optima |
| prop3_E[R|I=1] | 4 | 2/5 | 2 | 4 | pooled | 24/35 | 24/35 | == | True | histories=count (81) |
| prop3_every_history_with_I=1 | 4 | 2/5 | 2 | 4 | pooled | 1 | 1 | == | True | histories=count (81); count of distinct per-history optima |
| prop3_E[R|I=2] | 4 | 2/5 | 2 | 4 | pooled | 8/15 | 8/15 | == | True | histories=count (81) |
| prop3_every_history_with_I=2 | 4 | 2/5 | 2 | 4 | pooled | 1 | 1 | == | True | histories=count (81); count of distinct per-history optima |
| prop3_E[R|I=3] | 4 | 2/5 | 2 | 4 | pooled | 8/25 | 8/25 | == | True | histories=count (81) |
| prop3_every_history_with_I=3 | 4 | 2/5 | 2 | 4 | pooled | 1 | 1 | == | True | histories=count (81); count of distinct per-history optima |
| prop3_E[R|I=4] | 4 | 2/5 | 2 | 4 | pooled | 0 | 0 | == | True | histories=count (81) |
| prop3_every_history_with_I=4 | 4 | 2/5 | 2 | 4 | pooled | 1 | 1 | == | True | histories=count (81); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 4 | 2/5 | 2 | 4 | pooled | 26386956/68359375 | 26386956/68359375 | == | True | histories=count (81); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 4 | 2/5 | 2 | 4 | pooled | 0 | 0 | == | True | histories=count (81) |
| prop3_share_recovered_vs_f/(2-f) | 4 | 2/5 | 2 | 4 | pooled | 7075136/13671875 | 8/17 | >= | True | histories=count (81) |
| prop3_history_optimum | 4 | 2/5 | 2 | 4 | pooled | 26386956/68359375 | 26386956/68359375 | == | True | histories=full (256) |
| prop3_E[R|I=0] | 4 | 2/5 | 2 | 4 | pooled | 4/5 | 4/5 | == | True | histories=full (256) |
| prop3_every_history_with_I=0 | 4 | 2/5 | 2 | 4 | pooled | 1 | 1 | == | True | histories=full (256); count of distinct per-history optima |
| prop3_E[R|I=1] | 4 | 2/5 | 2 | 4 | pooled | 24/35 | 24/35 | == | True | histories=full (256) |
| prop3_every_history_with_I=1 | 4 | 2/5 | 2 | 4 | pooled | 1 | 1 | == | True | histories=full (256); count of distinct per-history optima |
| prop3_E[R|I=2] | 4 | 2/5 | 2 | 4 | pooled | 8/15 | 8/15 | == | True | histories=full (256) |
| prop3_every_history_with_I=2 | 4 | 2/5 | 2 | 4 | pooled | 1 | 1 | == | True | histories=full (256); count of distinct per-history optima |
| prop3_E[R|I=3] | 4 | 2/5 | 2 | 4 | pooled | 8/25 | 8/25 | == | True | histories=full (256) |
| prop3_every_history_with_I=3 | 4 | 2/5 | 2 | 4 | pooled | 1 | 1 | == | True | histories=full (256); count of distinct per-history optima |
| prop3_E[R|I=4] | 4 | 2/5 | 2 | 4 | pooled | 0 | 0 | == | True | histories=full (256) |
| prop3_every_history_with_I=4 | 4 | 2/5 | 2 | 4 | pooled | 1 | 1 | == | True | histories=full (256); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 4 | 2/5 | 2 | 4 | pooled | 26386956/68359375 | 26386956/68359375 | == | True | histories=full (256); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 4 | 2/5 | 2 | 4 | pooled | 0 | 0 | == | True | histories=full (256) |
| prop3_share_recovered_vs_f/(2-f) | 4 | 2/5 | 2 | 4 | pooled | 7075136/13671875 | 8/17 | >= | True | histories=full (256) |
| prop3_full_vs_count_histories | 4 | 2/5 | 2 | 4 | pooled | 26386956/68359375 | 26386956/68359375 | == | True |  |
| prop3_history_optimum | 4 | 2/5 | 2 | 4 | per_copy | 36/125 | 36/125 | == | True | histories=count (81) |
| prop3_E[R|I=0] | 4 | 2/5 | 2 | 4 | per_copy | 4/5 | 4/5 | == | True | histories=count (81) |
| prop3_every_history_with_I=0 | 4 | 2/5 | 2 | 4 | per_copy | 1 | 1 | == | True | histories=count (81); count of distinct per-history optima |
| prop3_E[R|I=1] | 4 | 2/5 | 2 | 4 | per_copy | 3/5 | 3/5 | == | True | histories=count (81) |
| prop3_every_history_with_I=1 | 4 | 2/5 | 2 | 4 | per_copy | 1 | 1 | == | True | histories=count (81); count of distinct per-history optima |
| prop3_E[R|I=2] | 4 | 2/5 | 2 | 4 | per_copy | 2/5 | 2/5 | == | True | histories=count (81) |
| prop3_every_history_with_I=2 | 4 | 2/5 | 2 | 4 | per_copy | 1 | 1 | == | True | histories=count (81); count of distinct per-history optima |
| prop3_E[R|I=3] | 4 | 2/5 | 2 | 4 | per_copy | 1/5 | 1/5 | == | True | histories=count (81) |
| prop3_every_history_with_I=3 | 4 | 2/5 | 2 | 4 | per_copy | 1 | 1 | == | True | histories=count (81); count of distinct per-history optima |
| prop3_E[R|I=4] | 4 | 2/5 | 2 | 4 | per_copy | 0 | 0 | == | True | histories=count (81) |
| prop3_every_history_with_I=4 | 4 | 2/5 | 2 | 4 | per_copy | 1 | 1 | == | True | histories=count (81); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 4 | 2/5 | 2 | 4 | per_copy | 36/125 | 36/125 | == | True | histories=count (81); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 4 | 2/5 | 2 | 4 | per_copy | 0 | 0 | == | True | histories=count (81) |
| prop3_share_recovered | 4 | 2/5 | 2 | 4 | per_copy | 16/25 | 16/25 | == | True | histories=count (81) |
| prop3_history_optimum | 4 | 2/5 | 2 | 4 | per_copy | 36/125 | 36/125 | == | True | histories=full (256) |
| prop3_E[R|I=0] | 4 | 2/5 | 2 | 4 | per_copy | 4/5 | 4/5 | == | True | histories=full (256) |
| prop3_every_history_with_I=0 | 4 | 2/5 | 2 | 4 | per_copy | 1 | 1 | == | True | histories=full (256); count of distinct per-history optima |
| prop3_E[R|I=1] | 4 | 2/5 | 2 | 4 | per_copy | 3/5 | 3/5 | == | True | histories=full (256) |
| prop3_every_history_with_I=1 | 4 | 2/5 | 2 | 4 | per_copy | 1 | 1 | == | True | histories=full (256); count of distinct per-history optima |
| prop3_E[R|I=2] | 4 | 2/5 | 2 | 4 | per_copy | 2/5 | 2/5 | == | True | histories=full (256) |
| prop3_every_history_with_I=2 | 4 | 2/5 | 2 | 4 | per_copy | 1 | 1 | == | True | histories=full (256); count of distinct per-history optima |
| prop3_E[R|I=3] | 4 | 2/5 | 2 | 4 | per_copy | 1/5 | 1/5 | == | True | histories=full (256) |
| prop3_every_history_with_I=3 | 4 | 2/5 | 2 | 4 | per_copy | 1 | 1 | == | True | histories=full (256); count of distinct per-history optima |
| prop3_E[R|I=4] | 4 | 2/5 | 2 | 4 | per_copy | 0 | 0 | == | True | histories=full (256) |
| prop3_every_history_with_I=4 | 4 | 2/5 | 2 | 4 | per_copy | 1 | 1 | == | True | histories=full (256); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 4 | 2/5 | 2 | 4 | per_copy | 36/125 | 36/125 | == | True | histories=full (256); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 4 | 2/5 | 2 | 4 | per_copy | 0 | 0 | == | True | histories=full (256) |
| prop3_share_recovered | 4 | 2/5 | 2 | 4 | per_copy | 16/25 | 16/25 | == | True | histories=full (256) |
| prop3_full_vs_count_histories | 4 | 2/5 | 2 | 4 | per_copy | 36/125 | 36/125 | == | True |  |
| prop3_history_optimum | 4 | 2/5 | 3 | 4 | pooled | 1516193748/6103515625 | 1516193748/6103515625 | == | True | histories=count (256) |
| prop3_E[R|I=0] | 4 | 2/5 | 3 | 4 | pooled | 4/5 | 4/5 | == | True | histories=count (256) |
| prop3_every_history_with_I=0 | 4 | 2/5 | 3 | 4 | pooled | 1 | 1 | == | True | histories=count (256); count of distinct per-history optima |
| prop3_E[R|I=1] | 4 | 2/5 | 3 | 4 | pooled | 24/35 | 24/35 | == | True | histories=count (256) |
| prop3_every_history_with_I=1 | 4 | 2/5 | 3 | 4 | pooled | 1 | 1 | == | True | histories=count (256); count of distinct per-history optima |
| prop3_E[R|I=2] | 4 | 2/5 | 3 | 4 | pooled | 8/15 | 8/15 | == | True | histories=count (256) |
| prop3_every_history_with_I=2 | 4 | 2/5 | 3 | 4 | pooled | 1 | 1 | == | True | histories=count (256); count of distinct per-history optima |
| prop3_E[R|I=3] | 4 | 2/5 | 3 | 4 | pooled | 8/25 | 8/25 | == | True | histories=count (256) |
| prop3_every_history_with_I=3 | 4 | 2/5 | 3 | 4 | pooled | 1 | 1 | == | True | histories=count (256); count of distinct per-history optima |
| prop3_E[R|I=4] | 4 | 2/5 | 3 | 4 | pooled | 0 | 0 | == | True | histories=count (256) |
| prop3_every_history_with_I=4 | 4 | 2/5 | 3 | 4 | pooled | 1 | 1 | == | True | histories=count (256); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 4 | 2/5 | 3 | 4 | pooled | 1516193748/6103515625 | 1516193748/6103515625 | == | True | histories=count (256); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 4 | 2/5 | 3 | 4 | pooled | 0 | 0 | == | True | histories=count (256) |
| prop3_share_recovered_vs_f/(2-f) | 4 | 2/5 | 3 | 4 | pooled | 841654688/1220703125 | 49/76 | >= | True | histories=count (256) |
| prop3_history_optimum | 4 | 2/5 | 3 | 4 | per_copy | 108/625 | 108/625 | == | True | histories=count (256) |
| prop3_E[R|I=0] | 4 | 2/5 | 3 | 4 | per_copy | 4/5 | 4/5 | == | True | histories=count (256) |
| prop3_every_history_with_I=0 | 4 | 2/5 | 3 | 4 | per_copy | 1 | 1 | == | True | histories=count (256); count of distinct per-history optima |
| prop3_E[R|I=1] | 4 | 2/5 | 3 | 4 | per_copy | 3/5 | 3/5 | == | True | histories=count (256) |
| prop3_every_history_with_I=1 | 4 | 2/5 | 3 | 4 | per_copy | 1 | 1 | == | True | histories=count (256); count of distinct per-history optima |
| prop3_E[R|I=2] | 4 | 2/5 | 3 | 4 | per_copy | 2/5 | 2/5 | == | True | histories=count (256) |
| prop3_every_history_with_I=2 | 4 | 2/5 | 3 | 4 | per_copy | 1 | 1 | == | True | histories=count (256); count of distinct per-history optima |
| prop3_E[R|I=3] | 4 | 2/5 | 3 | 4 | per_copy | 1/5 | 1/5 | == | True | histories=count (256) |
| prop3_every_history_with_I=3 | 4 | 2/5 | 3 | 4 | per_copy | 1 | 1 | == | True | histories=count (256); count of distinct per-history optima |
| prop3_E[R|I=4] | 4 | 2/5 | 3 | 4 | per_copy | 0 | 0 | == | True | histories=count (256) |
| prop3_every_history_with_I=4 | 4 | 2/5 | 3 | 4 | per_copy | 1 | 1 | == | True | histories=count (256); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 4 | 2/5 | 3 | 4 | per_copy | 108/625 | 108/625 | == | True | histories=count (256); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 4 | 2/5 | 3 | 4 | per_copy | 0 | 0 | == | True | histories=count (256) |
| prop3_share_recovered | 4 | 2/5 | 3 | 4 | per_copy | 98/125 | 98/125 | == | True | histories=count (256) |
| prop3_history_optimum | 4 | 2/5 | 5 | 4 | pooled | 1597968912312396/16689300537109375 | 1597968912312396/16689300537109375 | == | True | histories=count (1296) |
| prop3_E[R|I=0] | 4 | 2/5 | 5 | 4 | pooled | 4/5 | 4/5 | == | True | histories=count (1296) |
| prop3_every_history_with_I=0 | 4 | 2/5 | 5 | 4 | pooled | 1 | 1 | == | True | histories=count (1296); count of distinct per-history optima |
| prop3_E[R|I=1] | 4 | 2/5 | 5 | 4 | pooled | 24/35 | 24/35 | == | True | histories=count (1296) |
| prop3_every_history_with_I=1 | 4 | 2/5 | 5 | 4 | pooled | 1 | 1 | == | True | histories=count (1296); count of distinct per-history optima |
| prop3_E[R|I=2] | 4 | 2/5 | 5 | 4 | pooled | 8/15 | 8/15 | == | True | histories=count (1296) |
| prop3_every_history_with_I=2 | 4 | 2/5 | 5 | 4 | pooled | 1 | 1 | == | True | histories=count (1296); count of distinct per-history optima |
| prop3_E[R|I=3] | 4 | 2/5 | 5 | 4 | pooled | 8/25 | 8/25 | == | True | histories=count (1296) |
| prop3_every_history_with_I=3 | 4 | 2/5 | 5 | 4 | pooled | 1 | 1 | == | True | histories=count (1296); count of distinct per-history optima |
| prop3_E[R|I=4] | 4 | 2/5 | 5 | 4 | pooled | 0 | 0 | == | True | histories=count (1296) |
| prop3_every_history_with_I=4 | 4 | 2/5 | 5 | 4 | pooled | 1 | 1 | == | True | histories=count (1296); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 4 | 2/5 | 5 | 4 | pooled | 1597968912312396/16689300537109375 | 1597968912312396/16689300537109375 | == | True | histories=count (1296); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 4 | 2/5 | 5 | 4 | pooled | 0 | 0 | == | True | histories=count (1296) |
| prop3_share_recovered_vs_f/(2-f) | 4 | 2/5 | 5 | 4 | pooled | 2938367879343776/3337860107421875 | 1441/1684 | >= | True | histories=count (1296) |
| prop3_history_optimum | 4 | 2/5 | 5 | 4 | per_copy | 972/15625 | 972/15625 | == | True | histories=count (1296) |
| prop3_E[R|I=0] | 4 | 2/5 | 5 | 4 | per_copy | 4/5 | 4/5 | == | True | histories=count (1296) |
| prop3_every_history_with_I=0 | 4 | 2/5 | 5 | 4 | per_copy | 1 | 1 | == | True | histories=count (1296); count of distinct per-history optima |
| prop3_E[R|I=1] | 4 | 2/5 | 5 | 4 | per_copy | 3/5 | 3/5 | == | True | histories=count (1296) |
| prop3_every_history_with_I=1 | 4 | 2/5 | 5 | 4 | per_copy | 1 | 1 | == | True | histories=count (1296); count of distinct per-history optima |
| prop3_E[R|I=2] | 4 | 2/5 | 5 | 4 | per_copy | 2/5 | 2/5 | == | True | histories=count (1296) |
| prop3_every_history_with_I=2 | 4 | 2/5 | 5 | 4 | per_copy | 1 | 1 | == | True | histories=count (1296); count of distinct per-history optima |
| prop3_E[R|I=3] | 4 | 2/5 | 5 | 4 | per_copy | 1/5 | 1/5 | == | True | histories=count (1296) |
| prop3_every_history_with_I=3 | 4 | 2/5 | 5 | 4 | per_copy | 1 | 1 | == | True | histories=count (1296); count of distinct per-history optima |
| prop3_E[R|I=4] | 4 | 2/5 | 5 | 4 | per_copy | 0 | 0 | == | True | histories=count (1296) |
| prop3_every_history_with_I=4 | 4 | 2/5 | 5 | 4 | per_copy | 1 | 1 | == | True | histories=count (1296); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 4 | 2/5 | 5 | 4 | per_copy | 972/15625 | 972/15625 | == | True | histories=count (1296); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 4 | 2/5 | 5 | 4 | per_copy | 0 | 0 | == | True | histories=count (1296) |
| prop3_share_recovered | 4 | 2/5 | 5 | 4 | per_copy | 2882/3125 | 2882/3125 | == | True | histories=count (1296) |
| prop1_oblivious_optimum | 4 | 7/50 |  | 4 | pooled | 7/25 | 7/25 | == | True | 2200 orbits / 972032 schedules |
| prop1_posterior_optimum | 4 | 7/50 |  | 4 | pooled | 0 | 0 | == | True |  |
| prop1_hedge_all_A_max_R_over_realizations | 4 | 7/50 |  | 4 | pooled | 0 | 0 | == | True |  |
| prop1_oblivious_optimum | 4 | 7/50 |  | 4 | per_copy | 7/25 | 7/25 | == | True | 4845 orbits / 614656 schedules |
| prop1_posterior_optimum | 4 | 7/50 |  | 4 | per_copy | 0 | 0 | == | True |  |
| prop1_hedge_all_A_max_R_over_realizations | 4 | 7/50 |  | 4 | per_copy | 0 | 0 | == | True |  |
| gap_c | 4 | 7/50 |  | 0 | pooled | 0 | 0 | == | True |  |
| gap_c_oblivious_optimum | 4 | 7/50 |  | 0 | pooled | 14/25 | 14/25 | == | True |  |
| gap_c_posterior_optimum | 4 | 7/50 |  | 0 | pooled | 14/25 | 14/25 | == | True |  |
| gap_c | 4 | 7/50 |  | 1 | pooled | 7/100 | 7/100 | == | True |  |
| gap_c_oblivious_optimum | 4 | 7/50 |  | 1 | pooled | 49/100 | 49/100 | == | True |  |
| gap_c_posterior_optimum | 4 | 7/50 |  | 1 | pooled | 21/50 | 21/50 | == | True |  |
| gap_c | 4 | 7/50 |  | 2 | pooled | 7/50 | 7/50 | == | True |  |
| gap_c_oblivious_optimum | 4 | 7/50 |  | 2 | pooled | 21/50 | 21/50 | == | True |  |
| gap_c_posterior_optimum | 4 | 7/50 |  | 2 | pooled | 7/25 | 7/25 | == | True |  |
| gap_c | 4 | 7/50 |  | 3 | pooled | 21/100 | 21/100 | == | True |  |
| gap_c_oblivious_optimum | 4 | 7/50 |  | 3 | pooled | 7/20 | 7/20 | == | True |  |
| gap_c_posterior_optimum | 4 | 7/50 |  | 3 | pooled | 7/50 | 7/50 | == | True |  |
| gap_c | 4 | 7/50 |  | 4 | pooled | 7/25 | 7/25 | == | True |  |
| gap_c_oblivious_optimum | 4 | 7/50 |  | 4 | pooled | 7/25 | 7/25 | == | True |  |
| gap_c_posterior_optimum | 4 | 7/50 |  | 4 | pooled | 0 | 0 | == | True |  |
| gap_c | 4 | 7/50 |  | 5 | pooled | 21/100 | 21/100 | == | True |  |
| gap_c_oblivious_optimum | 4 | 7/50 |  | 5 | pooled | 21/100 | 21/100 | == | True |  |
| gap_c_posterior_optimum | 4 | 7/50 |  | 5 | pooled | 0 | 0 | == | True |  |
| gap_c | 4 | 7/50 |  | 6 | pooled | 7/50 | 7/50 | == | True |  |
| gap_c_oblivious_optimum | 4 | 7/50 |  | 6 | pooled | 7/50 | 7/50 | == | True |  |
| gap_c_posterior_optimum | 4 | 7/50 |  | 6 | pooled | 0 | 0 | == | True |  |
| gap_c | 4 | 7/50 |  | 7 | pooled | 7/100 | 7/100 | == | True |  |
| gap_c_oblivious_optimum | 4 | 7/50 |  | 7 | pooled | 7/100 | 7/100 | == | True |  |
| gap_c_posterior_optimum | 4 | 7/50 |  | 7 | pooled | 0 | 0 | == | True |  |
| gap_c | 4 | 7/50 |  | 8 | pooled | 0 | 0 | == | True |  |
| gap_c_oblivious_optimum | 4 | 7/50 |  | 8 | pooled | 0 | 0 | == | True |  |
| gap_c_posterior_optimum | 4 | 7/50 |  | 8 | pooled | 0 | 0 | == | True |  |
| gap_c | 4 | 7/50 |  | 0 | per_copy | 0 | 0 | == | True |  |
| gap_c_oblivious_optimum | 4 | 7/50 |  | 0 | per_copy | 14/25 | 14/25 | == | True |  |
| gap_c_posterior_optimum | 4 | 7/50 |  | 0 | per_copy | 14/25 | 14/25 | == | True |  |
| gap_c | 4 | 7/50 |  | 4 | per_copy | 7/25 | 7/25 | == | True |  |
| gap_c_oblivious_optimum | 4 | 7/50 |  | 4 | per_copy | 7/25 | 7/25 | == | True |  |
| gap_c_posterior_optimum | 4 | 7/50 |  | 4 | per_copy | 0 | 0 | == | True |  |
| gap_c | 4 | 7/50 |  | 8 | per_copy | 0 | 0 | == | True |  |
| gap_c_oblivious_optimum | 4 | 7/50 |  | 8 | per_copy | 0 | 0 | == | True |  |
| gap_c_posterior_optimum | 4 | 7/50 |  | 8 | per_copy | 0 | 0 | == | True |  |
| prop3_history_optimum | 4 | 7/50 | 0 | 4 | pooled | 7/25 | 7/25 | == | True | histories=count (1) |
| prop3_E[R|I=0] | 4 | 7/50 | 0 | 4 | pooled | 7/25 | 7/25 | == | True | histories=count (1) |
| prop3_every_history_with_I=0 | 4 | 7/50 | 0 | 4 | pooled | 1 | 1 | == | True | histories=count (1); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 4 | 7/50 | 0 | 4 | pooled | 7/25 | 7/25 | == | True | histories=count (1); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 4 | 7/50 | 0 | 4 | pooled | 0 | 0 | == | True | histories=count (1) |
| prop3_share_recovered_vs_f/(2-f) | 4 | 7/50 | 0 | 4 | pooled | 0 | 0 | >= | True | histories=count (1) |
| prop3_M0_equals_prop1 | 4 | 7/50 | 0 | 4 | pooled | 7/25 | 7/25 | == | True | histories=count (1); closed_form column = enumerated Prop 1 |
| prop3_history_optimum | 4 | 7/50 | 0 | 4 | pooled | 7/25 | 7/25 | == | True | histories=full (1) |
| prop3_E[R|I=0] | 4 | 7/50 | 0 | 4 | pooled | 7/25 | 7/25 | == | True | histories=full (1) |
| prop3_every_history_with_I=0 | 4 | 7/50 | 0 | 4 | pooled | 1 | 1 | == | True | histories=full (1); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 4 | 7/50 | 0 | 4 | pooled | 7/25 | 7/25 | == | True | histories=full (1); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 4 | 7/50 | 0 | 4 | pooled | 0 | 0 | == | True | histories=full (1) |
| prop3_share_recovered_vs_f/(2-f) | 4 | 7/50 | 0 | 4 | pooled | 0 | 0 | >= | True | histories=full (1) |
| prop3_M0_equals_prop1 | 4 | 7/50 | 0 | 4 | pooled | 7/25 | 7/25 | == | True | histories=full (1); closed_form column = enumerated Prop 1 |
| prop3_full_vs_count_histories | 4 | 7/50 | 0 | 4 | pooled | 7/25 | 7/25 | == | True |  |
| prop3_history_optimum | 4 | 7/50 | 0 | 4 | per_copy | 7/25 | 7/25 | == | True | histories=count (1) |
| prop3_E[R|I=0] | 4 | 7/50 | 0 | 4 | per_copy | 7/25 | 7/25 | == | True | histories=count (1) |
| prop3_every_history_with_I=0 | 4 | 7/50 | 0 | 4 | per_copy | 1 | 1 | == | True | histories=count (1); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 4 | 7/50 | 0 | 4 | per_copy | 7/25 | 7/25 | == | True | histories=count (1); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 4 | 7/50 | 0 | 4 | per_copy | 0 | 0 | == | True | histories=count (1) |
| prop3_share_recovered | 4 | 7/50 | 0 | 4 | per_copy | 0 | 0 | == | True | histories=count (1) |
| prop3_M0_equals_prop1 | 4 | 7/50 | 0 | 4 | per_copy | 7/25 | 7/25 | == | True | histories=count (1); closed_form column = enumerated Prop 1 |
| prop3_history_optimum | 4 | 7/50 | 0 | 4 | per_copy | 7/25 | 7/25 | == | True | histories=full (1) |
| prop3_E[R|I=0] | 4 | 7/50 | 0 | 4 | per_copy | 7/25 | 7/25 | == | True | histories=full (1) |
| prop3_every_history_with_I=0 | 4 | 7/50 | 0 | 4 | per_copy | 1 | 1 | == | True | histories=full (1); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 4 | 7/50 | 0 | 4 | per_copy | 7/25 | 7/25 | == | True | histories=full (1); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 4 | 7/50 | 0 | 4 | per_copy | 0 | 0 | == | True | histories=full (1) |
| prop3_share_recovered | 4 | 7/50 | 0 | 4 | per_copy | 0 | 0 | == | True | histories=full (1) |
| prop3_M0_equals_prop1 | 4 | 7/50 | 0 | 4 | per_copy | 7/25 | 7/25 | == | True | histories=full (1); closed_form column = enumerated Prop 1 |
| prop3_full_vs_count_histories | 4 | 7/50 | 0 | 4 | per_copy | 7/25 | 7/25 | == | True |  |
| prop3_history_optimum | 4 | 7/50 | 1 | 4 | pooled | 199953999/781250000 | 199953999/781250000 | == | True | histories=count (16) |
| prop3_E[R|I=0] | 4 | 7/50 | 1 | 4 | pooled | 7/25 | 7/25 | == | True | histories=count (16) |
| prop3_every_history_with_I=0 | 4 | 7/50 | 1 | 4 | pooled | 1 | 1 | == | True | histories=count (16); count of distinct per-history optima |
| prop3_E[R|I=1] | 4 | 7/50 | 1 | 4 | pooled | 6/25 | 6/25 | == | True | histories=count (16) |
| prop3_every_history_with_I=1 | 4 | 7/50 | 1 | 4 | pooled | 1 | 1 | == | True | histories=count (16); count of distinct per-history optima |
| prop3_E[R|I=2] | 4 | 7/50 | 1 | 4 | pooled | 14/75 | 14/75 | == | True | histories=count (16) |
| prop3_every_history_with_I=2 | 4 | 7/50 | 1 | 4 | pooled | 1 | 1 | == | True | histories=count (16); count of distinct per-history optima |
| prop3_E[R|I=3] | 4 | 7/50 | 1 | 4 | pooled | 14/125 | 14/125 | == | True | histories=count (16) |
| prop3_every_history_with_I=3 | 4 | 7/50 | 1 | 4 | pooled | 1 | 1 | == | True | histories=count (16); count of distinct per-history optima |
| prop3_E[R|I=4] | 4 | 7/50 | 1 | 4 | pooled | 0 | 0 | == | True | histories=count (16) |
| prop3_every_history_with_I=4 | 4 | 7/50 | 1 | 4 | pooled | 1 | 1 | == | True | histories=count (16); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 4 | 7/50 | 1 | 4 | pooled | 199953999/781250000 | 199953999/781250000 | == | True | histories=count (16); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 4 | 7/50 | 1 | 4 | pooled | 0 | 0 | == | True | histories=count (16) |
| prop3_share_recovered_vs_f/(2-f) | 4 | 7/50 | 1 | 4 | pooled | 2685143/31250000 | 7/93 | >= | True | histories=count (16) |
| prop3_history_optimum | 4 | 7/50 | 1 | 4 | pooled | 199953999/781250000 | 199953999/781250000 | == | True | histories=full (16) |
| prop3_E[R|I=0] | 4 | 7/50 | 1 | 4 | pooled | 7/25 | 7/25 | == | True | histories=full (16) |
| prop3_every_history_with_I=0 | 4 | 7/50 | 1 | 4 | pooled | 1 | 1 | == | True | histories=full (16); count of distinct per-history optima |
| prop3_E[R|I=1] | 4 | 7/50 | 1 | 4 | pooled | 6/25 | 6/25 | == | True | histories=full (16) |
| prop3_every_history_with_I=1 | 4 | 7/50 | 1 | 4 | pooled | 1 | 1 | == | True | histories=full (16); count of distinct per-history optima |
| prop3_E[R|I=2] | 4 | 7/50 | 1 | 4 | pooled | 14/75 | 14/75 | == | True | histories=full (16) |
| prop3_every_history_with_I=2 | 4 | 7/50 | 1 | 4 | pooled | 1 | 1 | == | True | histories=full (16); count of distinct per-history optima |
| prop3_E[R|I=3] | 4 | 7/50 | 1 | 4 | pooled | 14/125 | 14/125 | == | True | histories=full (16) |
| prop3_every_history_with_I=3 | 4 | 7/50 | 1 | 4 | pooled | 1 | 1 | == | True | histories=full (16); count of distinct per-history optima |
| prop3_E[R|I=4] | 4 | 7/50 | 1 | 4 | pooled | 0 | 0 | == | True | histories=full (16) |
| prop3_every_history_with_I=4 | 4 | 7/50 | 1 | 4 | pooled | 1 | 1 | == | True | histories=full (16); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 4 | 7/50 | 1 | 4 | pooled | 199953999/781250000 | 199953999/781250000 | == | True | histories=full (16); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 4 | 7/50 | 1 | 4 | pooled | 0 | 0 | == | True | histories=full (16) |
| prop3_share_recovered_vs_f/(2-f) | 4 | 7/50 | 1 | 4 | pooled | 2685143/31250000 | 7/93 | >= | True | histories=full (16) |
| prop3_full_vs_count_histories | 4 | 7/50 | 1 | 4 | pooled | 199953999/781250000 | 199953999/781250000 | == | True |  |
| prop3_history_optimum | 4 | 7/50 | 1 | 4 | per_copy | 301/1250 | 301/1250 | == | True | histories=count (16) |
| prop3_E[R|I=0] | 4 | 7/50 | 1 | 4 | per_copy | 7/25 | 7/25 | == | True | histories=count (16) |
| prop3_every_history_with_I=0 | 4 | 7/50 | 1 | 4 | per_copy | 1 | 1 | == | True | histories=count (16); count of distinct per-history optima |
| prop3_E[R|I=1] | 4 | 7/50 | 1 | 4 | per_copy | 21/100 | 21/100 | == | True | histories=count (16) |
| prop3_every_history_with_I=1 | 4 | 7/50 | 1 | 4 | per_copy | 1 | 1 | == | True | histories=count (16); count of distinct per-history optima |
| prop3_E[R|I=2] | 4 | 7/50 | 1 | 4 | per_copy | 7/50 | 7/50 | == | True | histories=count (16) |
| prop3_every_history_with_I=2 | 4 | 7/50 | 1 | 4 | per_copy | 1 | 1 | == | True | histories=count (16); count of distinct per-history optima |
| prop3_E[R|I=3] | 4 | 7/50 | 1 | 4 | per_copy | 7/100 | 7/100 | == | True | histories=count (16) |
| prop3_every_history_with_I=3 | 4 | 7/50 | 1 | 4 | per_copy | 1 | 1 | == | True | histories=count (16); count of distinct per-history optima |
| prop3_E[R|I=4] | 4 | 7/50 | 1 | 4 | per_copy | 0 | 0 | == | True | histories=count (16) |
| prop3_every_history_with_I=4 | 4 | 7/50 | 1 | 4 | per_copy | 1 | 1 | == | True | histories=count (16); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 4 | 7/50 | 1 | 4 | per_copy | 301/1250 | 301/1250 | == | True | histories=count (16); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 4 | 7/50 | 1 | 4 | per_copy | 0 | 0 | == | True | histories=count (16) |
| prop3_share_recovered | 4 | 7/50 | 1 | 4 | per_copy | 7/50 | 7/50 | == | True | histories=count (16) |
| prop3_history_optimum | 4 | 7/50 | 1 | 4 | per_copy | 301/1250 | 301/1250 | == | True | histories=full (16) |
| prop3_E[R|I=0] | 4 | 7/50 | 1 | 4 | per_copy | 7/25 | 7/25 | == | True | histories=full (16) |
| prop3_every_history_with_I=0 | 4 | 7/50 | 1 | 4 | per_copy | 1 | 1 | == | True | histories=full (16); count of distinct per-history optima |
| prop3_E[R|I=1] | 4 | 7/50 | 1 | 4 | per_copy | 21/100 | 21/100 | == | True | histories=full (16) |
| prop3_every_history_with_I=1 | 4 | 7/50 | 1 | 4 | per_copy | 1 | 1 | == | True | histories=full (16); count of distinct per-history optima |
| prop3_E[R|I=2] | 4 | 7/50 | 1 | 4 | per_copy | 7/50 | 7/50 | == | True | histories=full (16) |
| prop3_every_history_with_I=2 | 4 | 7/50 | 1 | 4 | per_copy | 1 | 1 | == | True | histories=full (16); count of distinct per-history optima |
| prop3_E[R|I=3] | 4 | 7/50 | 1 | 4 | per_copy | 7/100 | 7/100 | == | True | histories=full (16) |
| prop3_every_history_with_I=3 | 4 | 7/50 | 1 | 4 | per_copy | 1 | 1 | == | True | histories=full (16); count of distinct per-history optima |
| prop3_E[R|I=4] | 4 | 7/50 | 1 | 4 | per_copy | 0 | 0 | == | True | histories=full (16) |
| prop3_every_history_with_I=4 | 4 | 7/50 | 1 | 4 | per_copy | 1 | 1 | == | True | histories=full (16); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 4 | 7/50 | 1 | 4 | per_copy | 301/1250 | 301/1250 | == | True | histories=full (16); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 4 | 7/50 | 1 | 4 | per_copy | 0 | 0 | == | True | histories=full (16) |
| prop3_share_recovered | 4 | 7/50 | 1 | 4 | per_copy | 7/50 | 7/50 | == | True | histories=full (16) |
| prop3_full_vs_count_histories | 4 | 7/50 | 1 | 4 | per_copy | 301/1250 | 301/1250 | == | True |  |
| prop3_history_optimum | 4 | 7/50 | 2 | 4 | pooled | 1134323885702399/4882812500000000 | 1134323885702399/4882812500000000 | == | True | histories=count (81) |
| prop3_E[R|I=0] | 4 | 7/50 | 2 | 4 | pooled | 7/25 | 7/25 | == | True | histories=count (81) |
| prop3_every_history_with_I=0 | 4 | 7/50 | 2 | 4 | pooled | 1 | 1 | == | True | histories=count (81); count of distinct per-history optima |
| prop3_E[R|I=1] | 4 | 7/50 | 2 | 4 | pooled | 6/25 | 6/25 | == | True | histories=count (81) |
| prop3_every_history_with_I=1 | 4 | 7/50 | 2 | 4 | pooled | 1 | 1 | == | True | histories=count (81); count of distinct per-history optima |
| prop3_E[R|I=2] | 4 | 7/50 | 2 | 4 | pooled | 14/75 | 14/75 | == | True | histories=count (81) |
| prop3_every_history_with_I=2 | 4 | 7/50 | 2 | 4 | pooled | 1 | 1 | == | True | histories=count (81); count of distinct per-history optima |
| prop3_E[R|I=3] | 4 | 7/50 | 2 | 4 | pooled | 14/125 | 14/125 | == | True | histories=count (81) |
| prop3_every_history_with_I=3 | 4 | 7/50 | 2 | 4 | pooled | 1 | 1 | == | True | histories=count (81); count of distinct per-history optima |
| prop3_E[R|I=4] | 4 | 7/50 | 2 | 4 | pooled | 0 | 0 | == | True | histories=count (81) |
| prop3_every_history_with_I=4 | 4 | 7/50 | 2 | 4 | pooled | 1 | 1 | == | True | histories=count (81); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 4 | 7/50 | 2 | 4 | pooled | 1134323885702399/4882812500000000 | 1134323885702399/4882812500000000 | == | True | histories=count (81); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 4 | 7/50 | 2 | 4 | pooled | 0 | 0 | == | True | histories=count (81) |
| prop3_share_recovered_vs_f/(2-f) | 4 | 7/50 | 2 | 4 | pooled | 33266230613943/195312500000000 | 651/4349 | >= | True | histories=count (81) |
| prop3_history_optimum | 4 | 7/50 | 2 | 4 | pooled | 1134323885702399/4882812500000000 | 1134323885702399/4882812500000000 | == | True | histories=full (256) |
| prop3_E[R|I=0] | 4 | 7/50 | 2 | 4 | pooled | 7/25 | 7/25 | == | True | histories=full (256) |
| prop3_every_history_with_I=0 | 4 | 7/50 | 2 | 4 | pooled | 1 | 1 | == | True | histories=full (256); count of distinct per-history optima |
| prop3_E[R|I=1] | 4 | 7/50 | 2 | 4 | pooled | 6/25 | 6/25 | == | True | histories=full (256) |
| prop3_every_history_with_I=1 | 4 | 7/50 | 2 | 4 | pooled | 1 | 1 | == | True | histories=full (256); count of distinct per-history optima |
| prop3_E[R|I=2] | 4 | 7/50 | 2 | 4 | pooled | 14/75 | 14/75 | == | True | histories=full (256) |
| prop3_every_history_with_I=2 | 4 | 7/50 | 2 | 4 | pooled | 1 | 1 | == | True | histories=full (256); count of distinct per-history optima |
| prop3_E[R|I=3] | 4 | 7/50 | 2 | 4 | pooled | 14/125 | 14/125 | == | True | histories=full (256) |
| prop3_every_history_with_I=3 | 4 | 7/50 | 2 | 4 | pooled | 1 | 1 | == | True | histories=full (256); count of distinct per-history optima |
| prop3_E[R|I=4] | 4 | 7/50 | 2 | 4 | pooled | 0 | 0 | == | True | histories=full (256) |
| prop3_every_history_with_I=4 | 4 | 7/50 | 2 | 4 | pooled | 1 | 1 | == | True | histories=full (256); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 4 | 7/50 | 2 | 4 | pooled | 1134323885702399/4882812500000000 | 1134323885702399/4882812500000000 | == | True | histories=full (256); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 4 | 7/50 | 2 | 4 | pooled | 0 | 0 | == | True | histories=full (256) |
| prop3_share_recovered_vs_f/(2-f) | 4 | 7/50 | 2 | 4 | pooled | 33266230613943/195312500000000 | 651/4349 | >= | True | histories=full (256) |
| prop3_full_vs_count_histories | 4 | 7/50 | 2 | 4 | pooled | 1134323885702399/4882812500000000 | 1134323885702399/4882812500000000 | == | True |  |
| prop3_history_optimum | 4 | 7/50 | 2 | 4 | per_copy | 12943/62500 | 12943/62500 | == | True | histories=count (81) |
| prop3_E[R|I=0] | 4 | 7/50 | 2 | 4 | per_copy | 7/25 | 7/25 | == | True | histories=count (81) |
| prop3_every_history_with_I=0 | 4 | 7/50 | 2 | 4 | per_copy | 1 | 1 | == | True | histories=count (81); count of distinct per-history optima |
| prop3_E[R|I=1] | 4 | 7/50 | 2 | 4 | per_copy | 21/100 | 21/100 | == | True | histories=count (81) |
| prop3_every_history_with_I=1 | 4 | 7/50 | 2 | 4 | per_copy | 1 | 1 | == | True | histories=count (81); count of distinct per-history optima |
| prop3_E[R|I=2] | 4 | 7/50 | 2 | 4 | per_copy | 7/50 | 7/50 | == | True | histories=count (81) |
| prop3_every_history_with_I=2 | 4 | 7/50 | 2 | 4 | per_copy | 1 | 1 | == | True | histories=count (81); count of distinct per-history optima |
| prop3_E[R|I=3] | 4 | 7/50 | 2 | 4 | per_copy | 7/100 | 7/100 | == | True | histories=count (81) |
| prop3_every_history_with_I=3 | 4 | 7/50 | 2 | 4 | per_copy | 1 | 1 | == | True | histories=count (81); count of distinct per-history optima |
| prop3_E[R|I=4] | 4 | 7/50 | 2 | 4 | per_copy | 0 | 0 | == | True | histories=count (81) |
| prop3_every_history_with_I=4 | 4 | 7/50 | 2 | 4 | per_copy | 1 | 1 | == | True | histories=count (81); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 4 | 7/50 | 2 | 4 | per_copy | 12943/62500 | 12943/62500 | == | True | histories=count (81); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 4 | 7/50 | 2 | 4 | per_copy | 0 | 0 | == | True | histories=count (81) |
| prop3_share_recovered | 4 | 7/50 | 2 | 4 | per_copy | 651/2500 | 651/2500 | == | True | histories=count (81) |
| prop3_history_optimum | 4 | 7/50 | 2 | 4 | per_copy | 12943/62500 | 12943/62500 | == | True | histories=full (256) |
| prop3_E[R|I=0] | 4 | 7/50 | 2 | 4 | per_copy | 7/25 | 7/25 | == | True | histories=full (256) |
| prop3_every_history_with_I=0 | 4 | 7/50 | 2 | 4 | per_copy | 1 | 1 | == | True | histories=full (256); count of distinct per-history optima |
| prop3_E[R|I=1] | 4 | 7/50 | 2 | 4 | per_copy | 21/100 | 21/100 | == | True | histories=full (256) |
| prop3_every_history_with_I=1 | 4 | 7/50 | 2 | 4 | per_copy | 1 | 1 | == | True | histories=full (256); count of distinct per-history optima |
| prop3_E[R|I=2] | 4 | 7/50 | 2 | 4 | per_copy | 7/50 | 7/50 | == | True | histories=full (256) |
| prop3_every_history_with_I=2 | 4 | 7/50 | 2 | 4 | per_copy | 1 | 1 | == | True | histories=full (256); count of distinct per-history optima |
| prop3_E[R|I=3] | 4 | 7/50 | 2 | 4 | per_copy | 7/100 | 7/100 | == | True | histories=full (256) |
| prop3_every_history_with_I=3 | 4 | 7/50 | 2 | 4 | per_copy | 1 | 1 | == | True | histories=full (256); count of distinct per-history optima |
| prop3_E[R|I=4] | 4 | 7/50 | 2 | 4 | per_copy | 0 | 0 | == | True | histories=full (256) |
| prop3_every_history_with_I=4 | 4 | 7/50 | 2 | 4 | per_copy | 1 | 1 | == | True | histories=full (256); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 4 | 7/50 | 2 | 4 | per_copy | 12943/62500 | 12943/62500 | == | True | histories=full (256); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 4 | 7/50 | 2 | 4 | per_copy | 0 | 0 | == | True | histories=full (256) |
| prop3_share_recovered | 4 | 7/50 | 2 | 4 | per_copy | 651/2500 | 651/2500 | == | True | histories=full (256) |
| prop3_full_vs_count_histories | 4 | 7/50 | 2 | 4 | per_copy | 12943/62500 | 12943/62500 | == | True |  |
| prop3_history_optimum | 4 | 7/50 | 3 | 4 | pooled | 6393114772202080423599/30517578125000000000000 | 6393114772202080423599/30517578125000000000000 | == | True | histories=count (256) |
| prop3_E[R|I=0] | 4 | 7/50 | 3 | 4 | pooled | 7/25 | 7/25 | == | True | histories=count (256) |
| prop3_every_history_with_I=0 | 4 | 7/50 | 3 | 4 | pooled | 1 | 1 | == | True | histories=count (256); count of distinct per-history optima |
| prop3_E[R|I=1] | 4 | 7/50 | 3 | 4 | pooled | 6/25 | 6/25 | == | True | histories=count (256) |
| prop3_every_history_with_I=1 | 4 | 7/50 | 3 | 4 | pooled | 1 | 1 | == | True | histories=count (256); count of distinct per-history optima |
| prop3_E[R|I=2] | 4 | 7/50 | 3 | 4 | pooled | 14/75 | 14/75 | == | True | histories=count (256) |
| prop3_every_history_with_I=2 | 4 | 7/50 | 3 | 4 | pooled | 1 | 1 | == | True | histories=count (256); count of distinct per-history optima |
| prop3_E[R|I=3] | 4 | 7/50 | 3 | 4 | pooled | 14/125 | 14/125 | == | True | histories=count (256) |
| prop3_every_history_with_I=3 | 4 | 7/50 | 3 | 4 | pooled | 1 | 1 | == | True | histories=count (256); count of distinct per-history optima |
| prop3_E[R|I=4] | 4 | 7/50 | 3 | 4 | pooled | 0 | 0 | == | True | histories=count (256) |
| prop3_every_history_with_I=4 | 4 | 7/50 | 3 | 4 | pooled | 1 | 1 | == | True | histories=count (256); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 4 | 7/50 | 3 | 4 | pooled | 6393114772202080423599/30517578125000000000000 | 6393114772202080423599/30517578125000000000000 | == | True | histories=count (256); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 4 | 7/50 | 3 | 4 | pooled | 0 | 0 | == | True | histories=count (256) |
| prop3_share_recovered_vs_f/(2-f) | 4 | 7/50 | 3 | 4 | pooled | 307401014685417082343/1220703125000000000000 | 45493/204507 | >= | True | histories=count (256) |
| prop3_history_optimum | 4 | 7/50 | 3 | 4 | per_copy | 556549/3125000 | 556549/3125000 | == | True | histories=count (256) |
| prop3_E[R|I=0] | 4 | 7/50 | 3 | 4 | per_copy | 7/25 | 7/25 | == | True | histories=count (256) |
| prop3_every_history_with_I=0 | 4 | 7/50 | 3 | 4 | per_copy | 1 | 1 | == | True | histories=count (256); count of distinct per-history optima |
| prop3_E[R|I=1] | 4 | 7/50 | 3 | 4 | per_copy | 21/100 | 21/100 | == | True | histories=count (256) |
| prop3_every_history_with_I=1 | 4 | 7/50 | 3 | 4 | per_copy | 1 | 1 | == | True | histories=count (256); count of distinct per-history optima |
| prop3_E[R|I=2] | 4 | 7/50 | 3 | 4 | per_copy | 7/50 | 7/50 | == | True | histories=count (256) |
| prop3_every_history_with_I=2 | 4 | 7/50 | 3 | 4 | per_copy | 1 | 1 | == | True | histories=count (256); count of distinct per-history optima |
| prop3_E[R|I=3] | 4 | 7/50 | 3 | 4 | per_copy | 7/100 | 7/100 | == | True | histories=count (256) |
| prop3_every_history_with_I=3 | 4 | 7/50 | 3 | 4 | per_copy | 1 | 1 | == | True | histories=count (256); count of distinct per-history optima |
| prop3_E[R|I=4] | 4 | 7/50 | 3 | 4 | per_copy | 0 | 0 | == | True | histories=count (256) |
| prop3_every_history_with_I=4 | 4 | 7/50 | 3 | 4 | per_copy | 1 | 1 | == | True | histories=count (256); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 4 | 7/50 | 3 | 4 | per_copy | 556549/3125000 | 556549/3125000 | == | True | histories=count (256); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 4 | 7/50 | 3 | 4 | per_copy | 0 | 0 | == | True | histories=count (256) |
| prop3_share_recovered | 4 | 7/50 | 3 | 4 | per_copy | 45493/125000 | 45493/125000 | == | True | histories=count (256) |
| prop3_history_optimum | 4 | 7/50 | 5 | 4 | pooled | 199616854876408997880969710828505999/1192092895507812500000000000000000000 | 199616854876408997880969710828505999/1192092895507812500000000000000000000 | == | True | histories=count (1296) |
| prop3_E[R|I=0] | 4 | 7/50 | 5 | 4 | pooled | 7/25 | 7/25 | == | True | histories=count (1296) |
| prop3_every_history_with_I=0 | 4 | 7/50 | 5 | 4 | pooled | 1 | 1 | == | True | histories=count (1296); count of distinct per-history optima |
| prop3_E[R|I=1] | 4 | 7/50 | 5 | 4 | pooled | 6/25 | 6/25 | == | True | histories=count (1296) |
| prop3_every_history_with_I=1 | 4 | 7/50 | 5 | 4 | pooled | 1 | 1 | == | True | histories=count (1296); count of distinct per-history optima |
| prop3_E[R|I=2] | 4 | 7/50 | 5 | 4 | pooled | 14/75 | 14/75 | == | True | histories=count (1296) |
| prop3_every_history_with_I=2 | 4 | 7/50 | 5 | 4 | pooled | 1 | 1 | == | True | histories=count (1296); count of distinct per-history optima |
| prop3_E[R|I=3] | 4 | 7/50 | 5 | 4 | pooled | 14/125 | 14/125 | == | True | histories=count (1296) |
| prop3_every_history_with_I=3 | 4 | 7/50 | 5 | 4 | pooled | 1 | 1 | == | True | histories=count (1296); count of distinct per-history optima |
| prop3_E[R|I=4] | 4 | 7/50 | 5 | 4 | pooled | 0 | 0 | == | True | histories=count (1296) |
| prop3_every_history_with_I=4 | 4 | 7/50 | 5 | 4 | pooled | 1 | 1 | == | True | histories=count (1296); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 4 | 7/50 | 5 | 4 | pooled | 199616854876408997880969710828505999/1192092895507812500000000000000000000 | 199616854876408997880969710828505999/1192092895507812500000000000000000000 | == | True | histories=count (1296); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 4 | 7/50 | 5 | 4 | pooled | 0 | 0 | == | True | histories=count (1296) |
| prop3_share_recovered_vs_f/(2-f) | 4 | 7/50 | 5 | 4 | pooled | 19167022266539786017004327024499143/47683715820312500000000000000000000 | 165491557/459508443 | >= | True | histories=count (1296) |
| prop3_history_optimum | 4 | 7/50 | 5 | 4 | per_copy | 1029059101/7812500000 | 1029059101/7812500000 | == | True | histories=count (1296) |
| prop3_E[R|I=0] | 4 | 7/50 | 5 | 4 | per_copy | 7/25 | 7/25 | == | True | histories=count (1296) |
| prop3_every_history_with_I=0 | 4 | 7/50 | 5 | 4 | per_copy | 1 | 1 | == | True | histories=count (1296); count of distinct per-history optima |
| prop3_E[R|I=1] | 4 | 7/50 | 5 | 4 | per_copy | 21/100 | 21/100 | == | True | histories=count (1296) |
| prop3_every_history_with_I=1 | 4 | 7/50 | 5 | 4 | per_copy | 1 | 1 | == | True | histories=count (1296); count of distinct per-history optima |
| prop3_E[R|I=2] | 4 | 7/50 | 5 | 4 | per_copy | 7/50 | 7/50 | == | True | histories=count (1296) |
| prop3_every_history_with_I=2 | 4 | 7/50 | 5 | 4 | per_copy | 1 | 1 | == | True | histories=count (1296); count of distinct per-history optima |
| prop3_E[R|I=3] | 4 | 7/50 | 5 | 4 | per_copy | 7/100 | 7/100 | == | True | histories=count (1296) |
| prop3_every_history_with_I=3 | 4 | 7/50 | 5 | 4 | per_copy | 1 | 1 | == | True | histories=count (1296); count of distinct per-history optima |
| prop3_E[R|I=4] | 4 | 7/50 | 5 | 4 | per_copy | 0 | 0 | == | True | histories=count (1296) |
| prop3_every_history_with_I=4 | 4 | 7/50 | 5 | 4 | per_copy | 1 | 1 | == | True | histories=count (1296); count of distinct per-history optima |
| prop3_identified_first_law_vs_class_optimum | 4 | 7/50 | 5 | 4 | per_copy | 1029059101/7812500000 | 1029059101/7812500000 | == | True | histories=count (1296); closed_form column = enumerated class optimum |
| prop3_identified_first_per_history_mismatches | 4 | 7/50 | 5 | 4 | per_copy | 0 | 0 | == | True | histories=count (1296) |
| prop3_share_recovered | 4 | 7/50 | 5 | 4 | per_copy | 165491557/312500000 | 165491557/312500000 | == | True | histories=count (1296) |
| I1_posterior_E[R]_units | 1 | 1/2 |  | 1 | pooled | 0 | 0 | == | True |  |
| I1_posterior_E[R]_kWh | 1 | 1/2 |  | 1 | pooled | 0 | 0 | == | True |  |
| I1_posterior_R_omega1 | 1 | 1/2 |  | 1 | pooled | 0 | 0 | == | True |  |
| I1_posterior_R_omega0 | 1 | 1/2 |  | 1 | pooled | 0 | 0 | == | True |  |
| I1_certainty_equivalent_E[R]_units | 1 | 1/2 |  | 1 | pooled | 1/2 | 1/2 | == | True |  |
| I1_certainty_equivalent_E[R]_kWh | 1 | 1/2 |  | 1 | pooled | 1/8 | 1/8 | == | True |  |
| I1_certainty_equivalent_R_omega1 | 1 | 1/2 |  | 1 | pooled | 0 | 0 | == | True |  |
| I1_certainty_equivalent_R_omega0 | 1 | 1/2 |  | 1 | pooled | 1 | 1 | == | True |  |
| I1_pessimistic_D_first_random_twin_E[R]_units | 1 | 1/2 |  | 1 | pooled | 1/4 | 1/4 | == | True |  |
| I1_pessimistic_D_first_random_twin_E[R]_kWh | 1 | 1/2 |  | 1 | pooled | 1/16 | 1/16 | == | True |  |
| I1_pessimistic_D_first_random_twin_R_omega1 | 1 | 1/2 |  | 1 | pooled | 0 | 0 | == | True |  |
| I1_pessimistic_D_first_random_twin_R_omega0 | 1 | 1/2 |  | 1 | pooled | 1/2 | 1/2 | == | True |  |
| I1_pessimistic_A_and_B_first_E[R]_units | 1 | 1/2 |  | 1 | pooled | 1 | 1 | == | True |  |
| I1_pessimistic_A_and_B_first_E[R]_kWh | 1 | 1/2 |  | 1 | pooled | 1/4 | 1/4 | == | True |  |
| I1_pessimistic_A_and_B_first_R_omega1 | 1 | 1/2 |  | 1 | pooled | 1 | 1 | == | True |  |
| I1_pessimistic_A_and_B_first_R_omega0 | 1 | 1/2 |  | 1 | pooled | 1 | 1 | == | True |  |
| I1_one_twin_slot0_at_random_E[R]_units | 1 | 1/2 |  | 1 | pooled | 1/4 | 1/4 | == | True |  |
| I1_one_twin_slot0_at_random_E[R]_kWh | 1 | 1/2 |  | 1 | pooled | 1/16 | 1/16 | == | True |  |
| I1_one_twin_slot0_at_random_R_omega1 | 1 | 1/2 |  | 1 | pooled | 0 | 0 | == | True |  |
| I1_one_twin_slot0_at_random_R_omega0 | 1 | 1/2 |  | 1 | pooled | 1/2 | 1/2 | == | True |  |
| I1_headroom_margin_m1_min_R_any_realization | 1 | 1/2 |  |  | pooled | 1 | 1 | >= | True | cap C' = 1 per slot |
| I1_headroom_margin_m1_min_E[R] | 1 | 1/2 |  |  | pooled | 1 | 1 | >= | True | cap C' = 1 per slot |
| I1_zero_residual_schedules_are_the_two_listed | 1 |  |  | 1 | pooled | 1 | 1 | == | True | 2 schedules |
| I1_sec35_swap_invariant_bound | 1 | 1/2 |  | 1 | pooled | 1/4 | 1/4 | == | True |  |
| I1_sec35_deterministic_oblivious_worst_case | 1 | 1/2 |  | 1 | pooled | 1/2 | 1/2 | == | True |  |
| I1_sec35_deadline_tightening_lower_bound | 1 | 1/2 |  | 1 | pooled | 1/4 | 1/4 | >= | True | any oblivious rule incl. tightening: enumerated class optimum >= 0.25 |
| prop3_pooled_share_K1000_closed_form_only | 1000 | 1/2 | 1 | 1000 | pooled | ~0.333481530858677 | 1/3 | within 1e-3 | True | closed form only, not enumerated |
| prop3_pooled_share_K1000_closed_form_only | 1000 | 1/2 | 2 | 1000 | pooled | ~0.600191992253941 | 3/5 | within 1e-3 | True | closed form only, not enumerated |
| prop3_pooled_share_K1000_closed_form_only | 1000 | 1/2 | 3 | 1000 | pooled | ~0.777931350272785 | 7/9 | within 1e-3 | True | closed form only, not enumerated |
| prop3_pooled_share_K1000_closed_form_only | 1000 | 1/2 | 5 | 1000 | pooled | ~0.939449101673301 | 31/33 | within 1e-3 | True | closed form only, not enumerated |
| prop3_pooled_share_K1000_closed_form_only | 1000 | 2/5 | 1 | 1000 | pooled | ~0.250117235116449 | 1/4 | within 1e-3 | True | closed form only, not enumerated |
| prop3_pooled_share_K1000_closed_form_only | 1000 | 2/5 | 2 | 1000 | pooled | ~0.470771453456220 | 8/17 | within 1e-3 | True | closed form only, not enumerated |
| prop3_pooled_share_K1000_closed_form_only | 1000 | 2/5 | 3 | 1000 | pooled | ~0.644925183283113 | 49/76 | within 1e-3 | True | closed form only, not enumerated |
| prop3_pooled_share_K1000_closed_form_only | 1000 | 2/5 | 5 | 1000 | pooled | ~0.855815212227515 | 1441/1684 | within 1e-3 | True | closed form only, not enumerated |
| prop3_pooled_share_K1000_closed_form_only | 1000 | 7/50 | 1 | 1000 | pooled | ~0.075306256800435 | 7/93 | within 1e-3 | True | closed form only, not enumerated |
| prop3_pooled_share_K1000_closed_form_only | 1000 | 7/50 | 2 | 1000 | pooled | ~0.149762785697343 | 651/4349 | within 1e-3 | True | closed form only, not enumerated |
| prop3_pooled_share_K1000_closed_form_only | 1000 | 7/50 | 3 | 1000 | pooled | ~0.222557810243347 | 45493/204507 | within 1e-3 | True | closed form only, not enumerated |
| prop3_pooled_share_K1000_closed_form_only | 1000 | 7/50 | 5 | 1000 | pooled | ~0.360305875882046 | 165491557/459508443 | within 1e-3 | True | closed form only, not enumerated |
| table39_f |  | 2/5 | 1 |  |  | 0.40 | 0.40 | rounds to | True |  |
| table39_share_per_copy_enumerated | 4 | 2/5 | 1 |  | per_copy | 0.40 | 0.40 | rounds to | True | exact 2/5 |
| table39_share_pooled_large_K | 1000 | 2/5 | 1 |  | pooled | 0.25 | 0.25 | rounds to | True | closed form only at K = 1000 |
| table39_share_pooled_limit_f/(2-f) |  | 2/5 | 1 |  | pooled | 0.25 | 0.25 | rounds to | True | limit, closed form only |
| plan7_f_two_decimals |  | 2/5 | 1 |  |  | 0.40 | 0.40 | rounds to | True |  |
| table39_f |  | 2/5 | 3 |  |  | 0.784 | 0.784 | rounds to | True |  |
| table39_share_per_copy_enumerated | 4 | 2/5 | 3 |  | per_copy | 0.78 | 0.78 | rounds to | True | exact 98/125 |
| table39_share_pooled_large_K | 1000 | 2/5 | 3 |  | pooled | 0.64 | 0.64 | rounds to | True | closed form only at K = 1000 |
| table39_share_pooled_limit_f/(2-f) |  | 2/5 | 3 |  | pooled | 0.64 | 0.64 | rounds to | True | limit, closed form only |
| plan7_f_two_decimals |  | 2/5 | 3 |  |  | 0.78 | 0.78 | rounds to | True |  |
| table39_f |  | 2/5 | 5 |  |  | 0.922 | 0.922 | rounds to | True |  |
| table39_share_per_copy_enumerated | 4 | 2/5 | 5 |  | per_copy | 0.92 | 0.92 | rounds to | True | exact 2882/3125 |
| table39_share_pooled_large_K | 1000 | 2/5 | 5 |  | pooled | 0.86 | 0.86 | rounds to | True | closed form only at K = 1000 |
| table39_share_pooled_limit_f/(2-f) |  | 2/5 | 5 |  | pooled | 0.86 | 0.86 | rounds to | True | limit, closed form only |
| plan7_f_two_decimals |  | 2/5 | 5 |  |  | 0.92 | 0.92 | rounds to | True |  |
| table39_f |  | 1/2 | 3 |  |  | 0.875 | 0.875 | rounds to | True |  |
| table39_share_per_copy_enumerated | 4 | 1/2 | 3 |  | per_copy | 0.88 | 0.88 | rounds to | True | exact 7/8 |
| table39_share_pooled_large_K | 1000 | 1/2 | 3 |  | pooled | 0.78 | 0.78 | rounds to | True | closed form only at K = 1000 |
| table39_share_pooled_limit_f/(2-f) |  | 1/2 | 3 |  | pooled | 0.78 | 0.78 | rounds to | True | limit, closed form only |
| kcopy_structure_failed_instances | 1 |  |  | 0 | per_copy | 0 | 0 | == | True | 60 instances (cells of KCOPY_CELLS rescaled to K x 5 seeds) |
| kcopy_structure_failed_instances | 1 |  |  | 1 | per_copy | 0 | 0 | == | True | 60 instances (cells of KCOPY_CELLS rescaled to K x 5 seeds) |
| kcopy_structure_failed_instances | 1 |  |  | 2 | per_copy | 0 | 0 | == | True | 60 instances (cells of KCOPY_CELLS rescaled to K x 5 seeds) |
| kcopy_structure_failed_instances | 1 |  |  | 0 | pooled | 0 | 0 | == | True | 60 instances (cells of KCOPY_CELLS rescaled to K x 5 seeds) |
| kcopy_structure_failed_instances | 1 |  |  | 1 | pooled | 0 | 0 | == | True | 60 instances (cells of KCOPY_CELLS rescaled to K x 5 seeds) |
| kcopy_structure_failed_instances | 1 |  |  | 2 | pooled | 0 | 0 | == | True | 60 instances (cells of KCOPY_CELLS rescaled to K x 5 seeds) |
| kcopy_structure_A_slot0_stuck_freq | 1 | 7/50 | 5 |  | pooled | 259/2000 | 7/50 | binomial p > 1e-4 | True | n = 2000, p = 0.186 |
| kcopy_structure_A_prior_stuck_freq | 1 | 7/50 | 5 |  | pooled | 679/5000 | 7/50 | binomial p > 1e-4 | True | n = 10000, p = 0.232 |
| kcopy_structure_A_slot0_stuck_freq | 1 | 2/5 | 5 |  | pooled | 413/1000 | 2/5 | binomial p > 1e-4 | True | n = 2000, p = 0.235 |
| kcopy_structure_A_prior_stuck_freq | 1 | 2/5 | 5 |  | pooled | 159/400 | 2/5 | binomial p > 1e-4 | True | n = 10000, p = 0.617 |
| kcopy_structure_A_slot0_stuck_freq | 1 | 1/2 | 5 |  | pooled | 101/200 | 1/2 | binomial p > 1e-4 | True | n = 2000, p = 0.671 |
| kcopy_structure_A_prior_stuck_freq | 1 | 1/2 | 5 |  | pooled | 99/200 | 1/2 | binomial p > 1e-4 | True | n = 10000, p = 0.322 |
| kcopy_structure_failed_instances | 2 |  |  | 0 | per_copy | 0 | 0 | == | True | 60 instances (cells of KCOPY_CELLS rescaled to K x 5 seeds) |
| kcopy_structure_failed_instances | 2 |  |  | 2 | per_copy | 0 | 0 | == | True | 60 instances (cells of KCOPY_CELLS rescaled to K x 5 seeds) |
| kcopy_structure_failed_instances | 2 |  |  | 4 | per_copy | 0 | 0 | == | True | 60 instances (cells of KCOPY_CELLS rescaled to K x 5 seeds) |
| kcopy_structure_failed_instances | 2 |  |  | 0 | pooled | 0 | 0 | == | True | 60 instances (cells of KCOPY_CELLS rescaled to K x 5 seeds) |
| kcopy_structure_failed_instances | 2 |  |  | 1 | pooled | 0 | 0 | == | True | 60 instances (cells of KCOPY_CELLS rescaled to K x 5 seeds) |
| kcopy_structure_failed_instances | 2 |  |  | 2 | pooled | 0 | 0 | == | True | 60 instances (cells of KCOPY_CELLS rescaled to K x 5 seeds) |
| kcopy_structure_failed_instances | 2 |  |  | 3 | pooled | 0 | 0 | == | True | 60 instances (cells of KCOPY_CELLS rescaled to K x 5 seeds) |
| kcopy_structure_failed_instances | 2 |  |  | 4 | pooled | 0 | 0 | == | True | 60 instances (cells of KCOPY_CELLS rescaled to K x 5 seeds) |
| kcopy_structure_A_slot0_stuck_freq | 2 | 7/50 | 5 |  | pooled | 71/500 | 7/50 | binomial p > 1e-4 | True | n = 2000, p = 0.797 |
| kcopy_structure_A_prior_stuck_freq | 2 | 7/50 | 5 |  | pooled | 1371/10000 | 7/50 | binomial p > 1e-4 | True | n = 10000, p = 0.411 |
| kcopy_structure_A_slot0_stuck_freq | 2 | 2/5 | 5 |  | pooled | 48/125 | 2/5 | binomial p > 1e-4 | True | n = 2000, p = 0.15 |
| kcopy_structure_A_prior_stuck_freq | 2 | 2/5 | 5 |  | pooled | 793/2000 | 2/5 | binomial p > 1e-4 | True | n = 10000, p = 0.481 |
| kcopy_structure_A_slot0_stuck_freq | 2 | 1/2 | 5 |  | pooled | 193/400 | 1/2 | binomial p > 1e-4 | True | n = 2000, p = 0.123 |
| kcopy_structure_A_prior_stuck_freq | 2 | 1/2 | 5 |  | pooled | 4993/10000 | 1/2 | binomial p > 1e-4 | True | n = 10000, p = 0.897 |
| kcopy_structure_failed_instances | 3 |  |  | 0 | per_copy | 0 | 0 | == | True | 60 instances (cells of KCOPY_CELLS rescaled to K x 5 seeds) |
| kcopy_structure_failed_instances | 3 |  |  | 3 | per_copy | 0 | 0 | == | True | 60 instances (cells of KCOPY_CELLS rescaled to K x 5 seeds) |
| kcopy_structure_failed_instances | 3 |  |  | 6 | per_copy | 0 | 0 | == | True | 60 instances (cells of KCOPY_CELLS rescaled to K x 5 seeds) |
| kcopy_structure_failed_instances | 3 |  |  | 0 | pooled | 0 | 0 | == | True | 60 instances (cells of KCOPY_CELLS rescaled to K x 5 seeds) |
| kcopy_structure_failed_instances | 3 |  |  | 3 | pooled | 0 | 0 | == | True | 60 instances (cells of KCOPY_CELLS rescaled to K x 5 seeds) |
| kcopy_structure_failed_instances | 3 |  |  | 6 | pooled | 0 | 0 | == | True | 60 instances (cells of KCOPY_CELLS rescaled to K x 5 seeds) |
| kcopy_structure_A_slot0_stuck_freq | 3 | 7/50 | 5 |  | pooled | 293/1998 | 7/50 | binomial p > 1e-4 | True | n = 1998, p = 0.384 |
| kcopy_structure_A_prior_stuck_freq | 3 | 7/50 | 5 |  | pooled | 707/4995 | 7/50 | binomial p > 1e-4 | True | n = 9990, p = 0.655 |
| kcopy_structure_A_slot0_stuck_freq | 3 | 2/5 | 5 |  | pooled | 394/999 | 2/5 | binomial p > 1e-4 | True | n = 1998, p = 0.616 |
| kcopy_structure_A_prior_stuck_freq | 3 | 2/5 | 5 |  | pooled | 3983/9990 | 2/5 | binomial p > 1e-4 | True | n = 9990, p = 0.799 |
| kcopy_structure_A_slot0_stuck_freq | 3 | 1/2 | 5 |  | pooled | 997/1998 | 1/2 | binomial p > 1e-4 | True | n = 1998, p = 0.946 |
| kcopy_structure_A_prior_stuck_freq | 3 | 1/2 | 5 |  | pooled | 4969/9990 | 1/2 | binomial p > 1e-4 | True | n = 9990, p = 0.61 |
| kcopy_structure_failed_instances | 4 |  |  | 0 | per_copy | 0 | 0 | == | True | 60 instances (cells of KCOPY_CELLS rescaled to K x 5 seeds) |
| kcopy_structure_failed_instances | 4 |  |  | 4 | per_copy | 0 | 0 | == | True | 60 instances (cells of KCOPY_CELLS rescaled to K x 5 seeds) |
| kcopy_structure_failed_instances | 4 |  |  | 8 | per_copy | 0 | 0 | == | True | 60 instances (cells of KCOPY_CELLS rescaled to K x 5 seeds) |
| kcopy_structure_failed_instances | 4 |  |  | 0 | pooled | 0 | 0 | == | True | 60 instances (cells of KCOPY_CELLS rescaled to K x 5 seeds) |
| kcopy_structure_failed_instances | 4 |  |  | 1 | pooled | 0 | 0 | == | True | 60 instances (cells of KCOPY_CELLS rescaled to K x 5 seeds) |
| kcopy_structure_failed_instances | 4 |  |  | 2 | pooled | 0 | 0 | == | True | 60 instances (cells of KCOPY_CELLS rescaled to K x 5 seeds) |
| kcopy_structure_failed_instances | 4 |  |  | 3 | pooled | 0 | 0 | == | True | 60 instances (cells of KCOPY_CELLS rescaled to K x 5 seeds) |
| kcopy_structure_failed_instances | 4 |  |  | 4 | pooled | 0 | 0 | == | True | 60 instances (cells of KCOPY_CELLS rescaled to K x 5 seeds) |
| kcopy_structure_failed_instances | 4 |  |  | 5 | pooled | 0 | 0 | == | True | 60 instances (cells of KCOPY_CELLS rescaled to K x 5 seeds) |
| kcopy_structure_failed_instances | 4 |  |  | 6 | pooled | 0 | 0 | == | True | 60 instances (cells of KCOPY_CELLS rescaled to K x 5 seeds) |
| kcopy_structure_failed_instances | 4 |  |  | 7 | pooled | 0 | 0 | == | True | 60 instances (cells of KCOPY_CELLS rescaled to K x 5 seeds) |
| kcopy_structure_failed_instances | 4 |  |  | 8 | pooled | 0 | 0 | == | True | 60 instances (cells of KCOPY_CELLS rescaled to K x 5 seeds) |
| kcopy_structure_A_slot0_stuck_freq | 4 | 7/50 | 5 |  | pooled | 27/200 | 7/50 | binomial p > 1e-4 | True | n = 2000, p = 0.54 |
| kcopy_structure_A_prior_stuck_freq | 4 | 7/50 | 5 |  | pooled | 709/5000 | 7/50 | binomial p > 1e-4 | True | n = 10000, p = 0.604 |
| kcopy_structure_A_slot0_stuck_freq | 4 | 2/5 | 5 |  | pooled | 789/2000 | 2/5 | binomial p > 1e-4 | True | n = 2000, p = 0.632 |
| kcopy_structure_A_prior_stuck_freq | 4 | 2/5 | 5 |  | pooled | 4029/10000 | 2/5 | binomial p > 1e-4 | True | n = 10000, p = 0.554 |
| kcopy_structure_A_slot0_stuck_freq | 4 | 1/2 | 5 |  | pooled | 993/2000 | 1/2 | binomial p > 1e-4 | True | n = 2000, p = 0.771 |
| kcopy_structure_A_prior_stuck_freq | 4 | 1/2 | 5 |  | pooled | 629/1250 | 1/2 | binomial p > 1e-4 | True | n = 10000, p = 0.529 |
| kcopy_structure_failed_instances | 8 |  |  | 0 | per_copy | 0 | 0 | == | True | 60 instances (cells of KCOPY_CELLS rescaled to K x 5 seeds) |
| kcopy_structure_failed_instances | 8 |  |  | 8 | per_copy | 0 | 0 | == | True | 60 instances (cells of KCOPY_CELLS rescaled to K x 5 seeds) |
| kcopy_structure_failed_instances | 8 |  |  | 16 | per_copy | 0 | 0 | == | True | 60 instances (cells of KCOPY_CELLS rescaled to K x 5 seeds) |
| kcopy_structure_failed_instances | 8 |  |  | 0 | pooled | 0 | 0 | == | True | 60 instances (cells of KCOPY_CELLS rescaled to K x 5 seeds) |
| kcopy_structure_failed_instances | 8 |  |  | 2 | pooled | 0 | 0 | == | True | 60 instances (cells of KCOPY_CELLS rescaled to K x 5 seeds) |
| kcopy_structure_failed_instances | 8 |  |  | 4 | pooled | 0 | 0 | == | True | 60 instances (cells of KCOPY_CELLS rescaled to K x 5 seeds) |
| kcopy_structure_failed_instances | 8 |  |  | 6 | pooled | 0 | 0 | == | True | 60 instances (cells of KCOPY_CELLS rescaled to K x 5 seeds) |
| kcopy_structure_failed_instances | 8 |  |  | 8 | pooled | 0 | 0 | == | True | 60 instances (cells of KCOPY_CELLS rescaled to K x 5 seeds) |
| kcopy_structure_failed_instances | 8 |  |  | 10 | pooled | 0 | 0 | == | True | 60 instances (cells of KCOPY_CELLS rescaled to K x 5 seeds) |
| kcopy_structure_failed_instances | 8 |  |  | 12 | pooled | 0 | 0 | == | True | 60 instances (cells of KCOPY_CELLS rescaled to K x 5 seeds) |
| kcopy_structure_failed_instances | 8 |  |  | 14 | pooled | 0 | 0 | == | True | 60 instances (cells of KCOPY_CELLS rescaled to K x 5 seeds) |
| kcopy_structure_failed_instances | 8 |  |  | 16 | pooled | 0 | 0 | == | True | 60 instances (cells of KCOPY_CELLS rescaled to K x 5 seeds) |
| kcopy_structure_A_slot0_stuck_freq | 8 | 7/50 | 5 |  | pooled | 271/2000 | 7/50 | binomial p > 1e-4 | True | n = 2000, p = 0.584 |
| kcopy_structure_A_prior_stuck_freq | 8 | 7/50 | 5 |  | pooled | 1443/10000 | 7/50 | binomial p > 1e-4 | True | n = 10000, p = 0.215 |
| kcopy_structure_A_slot0_stuck_freq | 8 | 2/5 | 5 |  | pooled | 197/500 | 2/5 | binomial p > 1e-4 | True | n = 2000, p = 0.6 |
| kcopy_structure_A_prior_stuck_freq | 8 | 2/5 | 5 |  | pooled | 4087/10000 | 2/5 | binomial p > 1e-4 | True | n = 10000, p = 0.0774 |
| kcopy_structure_A_slot0_stuck_freq | 8 | 1/2 | 5 |  | pooled | 487/1000 | 1/2 | binomial p > 1e-4 | True | n = 2000, p = 0.254 |
| kcopy_structure_A_prior_stuck_freq | 8 | 1/2 | 5 |  | pooled | 2507/5000 | 1/2 | binomial p > 1e-4 | True | n = 10000, p = 0.787 |
