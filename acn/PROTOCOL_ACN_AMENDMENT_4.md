# PROTOCOL_ACN amendment 4: T2-rep on City of Palo Alto sessions (registered before that data is pulled)

Follows amendment 3. Licence basis: the official portal data.paloalto.gov carries an Open Data badge linking the Open Data Commons PDDL (http://opendatacommons.org/licenses/pddl/) in its footer (portal-wide, not dataset-specific; stated as such).

- Data: "Electric Vehicle Charging Station Usage (July 2011 - Dec 2020)", data.paloalto.gov dataset 194693, full download file. Window: sessions starting 2019-11-01 to 2020-02-29 local (same months as ACN).
- Local time America/Los_Angeles; use the file's own time-zone fields if present to build timestamps; otherwise treat the times as local wall time.
- Site: the station's street address (the address field; stations at the same address form one site). Energy need = session energy (kWh), need_source = delivered; delivered energy linear in time.
- Cleaning: base §0 rules without the pilot/current requirement; exact duplicate rows dropped; sessions with missing start, end or energy dropped (counted).
- T1: base §1 rules; bootstrap seed 730500.
- T2: base §3 rules (P_i = 6 units, H = 24, at least 5 participants, frozen ρ formula; no published site limits); seeds 730000–730199; bootstrap seed 731000. Primary share at M = 3, δ = 2, ρ = 0.95 and the secondary contrast, with intervals. Replication criterion as in amendment 1 (interval overlaps the ACN interval [−0.035, 0.312]; secondary contrast has the same sign).
- If fewer than 20 eligible T2 site-days exist, T2-rep is reported as not runnable on this dataset (counts given), with no pooling across sites.
