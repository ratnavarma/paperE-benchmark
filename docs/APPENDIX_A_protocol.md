# Appendix A of the PGAI4E note, draft 8: protocol audit trail

This is Appendix A of the PGAI4E note, draft 8 ("One Failure Rate, and That Is Most of What You Need"). It is part of the code release and is reached through the paper's Data and code section. The paper points here in three places: the correctability split, the failed control rules and the seed hygiene of the build.

The text below is copied verbatim from draft 7 (paper/note.md at commit 5a17467), where it appeared in the body. Numbers are as the build printed them in draft 7 (paper/build/note_filled.md) from the result files named in the paper. The source key of each number is listed under its paragraph. Bracketed keys such as [chen2021sllf] refer to the paper's reference list.

## A.1 The correctability split (E2): the two readings

From Study design, Endpoints:

> The correctability split (E2) divides R_avoid into uncorrectable and correctable parts. Shortfall traced to setpoints that Proposition 2 rules out of correction is uncorrectable. Some of it may be forced by the shared cap anyway, so the uncorrectable part has two estimates. The first reading uses the traced shortfall. The second subtracts the cap's coupling shortfall from it. In each reading the two parts sum to R_avoid. The split predicts that the gain of the planner that learns who fails sits in the uncorrectable part under both readings.

From Results, Pre-declared outcomes:

> The correctability split is not supported. Under the first reading at ρ = 0.95, the contrast is 0.78 [0.53, 1.03] in the uncorrectable part and −0.47 [−0.94, −0.01] in the correctable part.

Keys: `e2/M3_rho0.95/contrast/readingA/gain_uncorr`, `e2/M3_rho0.95/contrast/readingA/gain_corr`.

> At δ = 2, though, the gain sits in the correctable part under both limits: 0.72 [0.23, 1.21] at ρ = 0.95 and 1.56 [0.99, 2.13] at ρ = 1.15. The second reading assigns zero to every scheduler in contested cells, because its coupling term swamps the traced shortfall. The rule required both readings and our endpoint definition was flawed.

Keys: `e2/M3_rho0.95/dA2/readingA/gain_corr`, `e2/M3_rho1.15/dA2/readingA/gain_corr`.

In draft 8 "the planner that learns who fails" is named Targeted MPC.

## A.2 The three control rules that failed

From Results, Theory tracking and controls:

> Three control rules failed, though the plan required every control to pass before the development runs. The two zero-residual controls failed because our plan left base-load noise in. With exact base load every planning scheduler reaches zero on all 50 seeds. The greedy rules do not, consistent with LLF failing feasible instances under a shared limit [chen2021sllf].

> The homogeneous-failure control failed on interval width at 50 and at 250 seeds. One cell inside the band showed the planner that learns who fails slightly worse, with an interval excluding zero.

The full control report is docs/NC_REPORT.md.

## A.3 Seed hygiene during the build

From Limitations:

> - During the build, tests and probes ran policies on development seeds 61000 to 61099 and checked rough performance there. A unit test compared validation residuals with theory on the validation seeds. A pilot on seeds 60050 to 60059 informed the guard of the planner that learns who fails. No tuned setting was chosen on development seeds.

The seed ranges and their uses are recorded in docs/SEED_LEDGER.md.
