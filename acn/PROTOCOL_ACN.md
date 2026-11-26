# PROTOCOL_ACN: registered rules for the ACN-Data tests (T1, T2, T3)

Frozen before any T1, T2 or T3 number is computed. Its sha256 is recorded in decisions.jsonl. Any change after the freeze is an amendment with its own hash and a stated reason, and results computed before the amendment are kept and reported.

## 0. Data
- Source: ACN-Data API, `/api/v1/sessions/<site>/ts`, sites `caltech`, `jpl`, `office001`. Connection time from 2019-11-01 00:00 to 2020-02-29 24:00 local (America/Los_Angeles). Files `data/acn_<site>.json.gz`; checksums in `data/PULL_SUMMARY.json`.
- Session cleaning, in order: drop if disconnect ≤ connection, duration > 24 h, kWh delivered < 0.1, or pilot or current series missing.
- Local time: each session's `timezone` field.
- Energy need of a session: the last `kWhRequested` in `userInputs` if present, else `kWhDelivered` (flag `need_source` = requested | delivered).
- Delivered energy up to time t: kWhDelivered × (∫ current up to t) / (∫ current over the session), current resampled to a 1-minute grid by carrying the last value forward.
- Site-day: a weekday (Monday–Friday) at one site with at least 10 cleaned sessions.

## 1. T1: how often the uncorrectable regime occurs (descriptive, claim C1)
- Event end time e: 17:00 local (primary); 15:00 and 19:00 (sensitivity).
- Population: sessions connected at e on a site-day, with remaining need (need − delivered by e) ≥ 0.25 kWh.
- Recovery window w = disconnect time − e.
- Regime indicator for δ ∈ {15, 30, 60} minutes: w < δ + 15 minutes.
- Outputs per site and pooled: share in regime; energy at risk = Σ remaining need of regime sessions / Σ remaining need of all population sessions. 95% intervals by bootstrap over site-days, 10,000 resamples, generator seed 710000.

## 2. T3: real failures to resume and per-user persistence (supports C2, C3)
- Grid: pilot and current resampled to 1 minute, last value carried forward, only while connected.
- Pause: pilot ≤ 6 A for at least 15 consecutive minutes.
- Resume event: the first minute after a pause where pilot ≥ 8 A, provided (a) `need_source = requested`, (b) remaining need at that minute ≥ 1 kWh, (c) the vehicle stays connected and the pilot stays ≥ 8 A for the next 15 minutes. Events failing (b) or (c) are not counted.
- Failure to resume: current ≤ 1 A in every minute of those 15 minutes. Otherwise success.
- Outputs: pooled and per-site failure rate per resume event with Wilson 95% intervals; number of events, sessions and users.
- Persistence (H3): users with userID and at least 5 resume events. Tarone's score test for binomial overdispersion against one common rate. H3 is supported when p < 0.05. Also report the beta-binomial maximum-likelihood (α, β) and intraclass correlation, as in `population_params.json` (same method).
- These are inferred failures (stated rule). Reported as such.

## 3. T2: the operator rule on real sessions (claim C3, H1)
- Instance for a site-day: event end e = 17:00; slots of 15 minutes from e; H = 24.
- Participants: sessions connected at e with remaining need ≥ 0.25 kWh and disconnect after e + 15 min. E_i = ceil(remaining need / 0.25 kWh) units of 1 kW·slot; P_i = 6 units per slot (6.6 kW at 208 V, 32 A, floored); a_i = 0; d_i = min(H, floor((disconnect − e) / 15 min)). Participants with d_i = 0 are dropped. Instances with fewer than 5 participants are dropped.
- Base load, limit and hidden variables follow the frozen F0R generator (`src/papere/generator.py`, release v1.0) with N, E, P, a, d replaced by the real values: base load `_base_load` with B0 = N; L = (Σ E / ρ + Σ b_mean) / H; failure classes, stuck probabilities, prior events (M) and chains drawn from the frozen population parameters (`population_params.json`); delays δ in slots.
- Seeds 700000–700199 (new block). Seed s picks a site-day uniformly with replacement from all eligible site-days (generator stream named `acn_day`) and draws hidden variables from the frozen streams.
- Cells: M ∈ {0, 3}; δ ∈ {0, 1, 2, 4}; ρ ∈ {0.95, 1.15}.
- Schedulers and settings: `ce_llf`, the shared-rate planner and the targeted planner exactly as in release v1.0 with `TUNING_FROZEN.json`; no retuning.
- Metric: avoidable residual R_avoid as in release v1.0.
- Primary (H1): share = (R_avoid[ce_llf] − R_avoid[shared]) / (R_avoid[ce_llf] − R_avoid[targeted]) at M = 3, δ = 2, ρ = 0.95, ratio of means over seeds; 95% paired bootstrap interval over seeds, 10,000 resamples, generator seed 711000. H1 supported when the lower end exceeds 0.5.
- Secondary: share at δ = 1 minus share at δ = 4, under ρ = 1.15, same bootstrap; reported with its interval, no threshold.
- T2-emp: same as T2 but stuck probabilities drawn from the T3 beta-binomial fit (all users pooled); reported beside T2, not a hypothesis test.
- Real-limit variant (descriptive): L set to the site's observed 99th-percentile aggregate charging power over the window, in units; reported if at least 50 instances are feasible.

## 4. Second-route check (orchestrator)
- Recompute the H1 share from the row file with an independent script (pandas-free, standard library), and recompute T1's pooled 30-minute share and T3's pooled rate from the raw files. Numbers must agree to 3 decimals before `claims.yaml` is filled.

## 5. Reporting
- All of T1, T2, T2-emp and T3 are reported whatever their outcome. If H1 fails, C3 is restated (soul amendment, Varma's gate). If H3 fails, the paper says per-user persistence is not supported in this field.
