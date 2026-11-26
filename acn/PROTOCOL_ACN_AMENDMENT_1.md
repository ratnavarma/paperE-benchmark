# PROTOCOL_ACN amendment 1: T2-rep on a second dataset (registered before that data is pulled)

Base protocol: PROTOCOL_ACN.md, sha256 a2a8d0570a3ac33429395ca1b06e8319f9acc129d8c124f700f238290f91828a. Nothing in the base protocol changes. Results of the base run are kept as reported.

Reason: the approved plan (v3) includes a replication of T1 and T2 on a second public dataset. The ACN results were seen before this amendment; this amendment fixes the second dataset's rules without reference to them, using the base protocol's rules wherever they apply.

## Dataset
- Perth & Kinross Council, "EV Charge Station Use" (ChargePlace Scotland), Sep 2018 – Aug 2019 file: `https://www.arcgis.com/sharing/rest/content/items/ca6cae3df2624832a2eaf678f2eabee8/data`. Open Government Licence v3.0; source acknowledged as Perth & Kinross Council.
- Fields: CP ID, Connector, Start Date, Start Time, End Date, End Time, Total kWh, Site, Model.
- Public car parks and park-and-ride sites (not workplaces); stated as such in the paper.
- No pilot or current series and no requested energy: T3 does not apply; energy need = Total kWh (need_source = delivered); delivered energy by time t is taken as linear in time over the session.

## Rules (base protocol rules, adapted only where the data differ)
- Local time Europe/London; Start and End are local wall times; DST resolved by the zone database.
- Cleaning: drop if end ≤ start, duration > 24 h, Total kWh < 0.1, exact duplicate rows (all fields equal).
- Site-day: weekday at one Site with at least 10 cleaned sessions.
- T1: as base §1 (e = 17:00 primary, 15:00 and 19:00; δ ∈ {15, 30, 60} min; regime w < δ + 15 min; remaining need ≥ 0.25 kWh; bootstrap over site-days, 10,000 resamples, seed 720500).
- T2: as base §3 with these site data; feeder limit by the frozen ρ formula (no published site limits); P_i = 6 units (as base; 7 kW chargers floored); seeds 720000–720199; bootstrap seed 721000. Primary share at M = 3, δ = 2, ρ = 0.95 and the secondary contrast, reported with intervals. Replication criterion (descriptive, stated before running): the share's interval overlaps the ACN interval [−0.035, 0.312] and the secondary contrast has the same sign.
- Real-limit and T2-emp variants: not run.
- Second route: the T2 share and the pooled T1 30-minute share recomputed by independent code.
