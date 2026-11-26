# PROTOCOL_ACN amendment 3: Perth & Kinross for T1 only, date repair; T2-rep moves to Palo Alto (Varma 2026-11-26)

Amends amendments 1 and 2. Reason: the builder found (counts only, no T1 or T2 result computed) that (a) no Perth & Kinross site has 5 vehicles connected at 17:00 on any weekday (1–4 AC chargers per site), so T2 cannot run; (b) the file's ISO dates swap day and month for days 1–12 (dates fall outside the file's Sep 2018 – Aug 2019 coverage).

1. Perth & Kinross: run T1 only (amendment 1's T1 rules, AC filter of amendment 2). T2 is not run on this dataset.
2. Date repair (applied to Start Date and End Date before building timestamps): if a parsed date lies outside 2018-09-01..2019-08-31 and its day is 12 or less, swap day and month; if the result is still outside the range, drop the session (counted). If a swap makes the end precede the start, drop the session (counted).
3. T2-rep moves to the City of Palo Alto EV charging session data, run under a separate amendment registered before that data is pulled, and only if its licence permits research use and publication of derived statistics (verified on the official page).
