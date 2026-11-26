# Registered ACN-Data results (run registered_2026-11-26, PROTOCOL_ACN sha256 a2a8d057…)

Second-route check (second_route.py, independent code): H1 share, T1 pooled 30-minute share and T3 counts match the build exactly.

## T1 (claim C1): regime frequency — supported as a measurement
Event end 17:00, pooled over 151 site-days: 1,052 of 2,542 sessions needing energy (41.4%) cannot be corrected with a 30-minute confirmation delay. Caltech: 22.5% at 15 min, 31.8% [29.2, 34.4] at 30 min, 53.3% [50.5, 56.0] at 60 min; energy at risk 30.3% [26.4, 34.3] at 30 min. Event end 15:00 (sensitivity), 30 min: Caltech 5.4%; pooled 13.6% (577 of 4,246). Corrected 2026-11-26: an earlier version of this line gave only the Caltech value without saying so.

## T2 (claim C3, H1): NOT supported
Reference cell (M=3, δ=30 min, ρ=0.95), 200 reserved seeds: share 0.163 [−0.035, 0.312]; H1 required the lower end above 0.5. Mean avoidable residual (kWh per 100 participants per event): CE-LLF 19.13, shared-rate MPC 17.59, targeted MPC 9.65. Total gain of targeted over CE-LLF 9.48 [7.23, 11.85].
Secondary (ρ=1.15): share at 15 min 0.42 [0.30, 0.52], at 60 min −0.10 [−0.44, 0.13]; drop 0.53 [0.35, 0.78] — same direction as the synthetic C5.

## T3 (supports C2/C3): rule-based failures — measurement not valid
275 resume events, 211 inferred failures (76.7% [71.4, 81.3]); H3 overdispersion p = 1.3e−11 on 11 users.
POST HOC diagnostic (posthoc_t3_diag.py, explains only): 204 of 211 "failures" never draw current again in the session; median delivered/requested energy 0.51. The rule cannot tell a full battery (overstated request) from a failure to resume. T3 and T2-emp are reported as invalid measurements, not evidence.

## Replications (amendments 3 and 4), second route matches
- Palo Alto (public garages, Nov 2019 – Feb 2020, 82 T2 site-days, seeds 730000–730199):
  - T1 at 17:00: 15 min 22.1% [20.0, 24.3]; 30 min 37.1% [34.5, 39.6] (597 of 1,610); 60 min 57.5% [54.9, 60.0].
  - T2 share 0.587 [0.206, 0.872]; avoidable residual CE-LLF 15.01, shared-rate 10.88, targeted 7.99 kWh per 100. Secondary contrast 0.676 [0.236, 1.673] (same sign as ACN and synthetic).
  - Registered replication criterion (interval overlaps ACN [−0.035, 0.312], same-sign contrast): met, but the point estimates differ (0.59 vs 0.16): the shared-rate share is site-dependent.
- Perth & Kinross (public car parks, AC chargers, T1 only): 34 sessions needing energy at 17:00 across 54 site-days; 30 min 82.4% [70.0, 95.2]. Too few sessions to weigh; reported as such.
