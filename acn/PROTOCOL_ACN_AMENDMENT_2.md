# PROTOCOL_ACN amendment 2: restrict T2-rep to AC destination chargers (before any T2-rep result)

Amends amendment 1 (sha256 f372324f…). Reason: the Perth & Kinross file mixes rapid DC chargers (sessions of about 20–30 minutes, where deferring charge for demand response does not apply) with AC destination chargers. Amendment 1 assumed 7 kW AC charging. Seen before this amendment: the file header, two rows and the count of sessions per charger model. No T1 or T2 number was computed.

Change: keep only sessions whose Model is one of "APT 22kW Dual Outlet", "APT 22kW Raption", "Siemens 7 kW Dual Outlet", "APT 7kW Dual Outlet" (AC destination chargers). Exclude "APT Triple Rapid Charger", "Siemens Triple Rapid Charger" and "Siemens Semi-Rapid". P_i stays 6 units, as in the base protocol, for comparability; stated in the paper. All other rules of amendment 1 stand.
