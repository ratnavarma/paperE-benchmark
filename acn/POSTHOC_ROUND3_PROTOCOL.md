# Post hoc round 3 (external review of draft 3): rules fixed before running

Labelled post hoc and explanatory in the paper. Base protocol and amendments are unchanged.

## M6: guard ablation
- Targeted MPC with its frozen tuned settings versus the same planner with γ = 0 (guard off), everything else equal. The running minimum is structural (it keeps unit values non-increasing and the LP integral) and is not ablated; the paper explains why.
- Cells: reference cell (M = 3, δ = 2 slots, ρ = 0.95) and tight cell (ρ = 1.15, δ = 2).
- Data: synthetic development seeds 61000–61099; ACN and Palo Alto real T2 instances with seeds 760000–760199 (new block).
- Output: mean avoidable residual (kWh per 100) and avoidable deadline misses per 100, guard on minus guard off, paired bootstrap 95% intervals (10,000, seed 760500; site-day clustered for real data).

## M3: failure persistence
- Failure classes as frozen (one third q = 0.40, two thirds q = 0.01). Before each of the M = 3 prior events and the scored event, each participant's class is redrawn with probability s ∈ {0, 0.2, 0.5} (s = 0 is the frozen model). A fourth setting draws each participant's q once from a Beta distribution with the frozen beta-binomial fit (α = 0.289, β = 1.811; mean 0.138), persistent across events.
- Schedulers: CE-LLF, shared-rate MPC, targeted MPC, frozen settings (the planners' beliefs are not changed: they still assume persistence).
- Cells: reference cell (ρ = 0.95, δ = 2) and tight cell (ρ = 1.15, δ = 4).
- Data: ACN and Palo Alto real T2 instances, seeds 770000–770199; synthetic development seeds 61000–61099.
- Output per setting: targeted gain over CE-LLF and over shared-rate MPC (kWh per 100), with paired 95% intervals (clustered for real data, seed 770500). Reported whatever the outcome; the paper states where the targeted advantage disappears, if it does.
