# Data provenance: ACN-Data for Paper E (SEGAN)

- Source: ACN-Data (Caltech Adaptive Charging Network), API `https://ev.caltech.edu/api/v1/sessions/<site>/ts`, registered token of Varma (Keychain `acn-data`; never stored). Cite: Z. J. Lee, T. Li, S. H. Low, "ACN-Data: Analysis and Applications of an Open EV Charging Dataset", ACM e-Energy 2019.
- Sites: caltech, jpl, office001. Connection time 2019-11-01 00:00 to 2020-02-29 24:00 America/Los_Angeles, pulled in weekly windows [start, end) of 25 sessions per page.
- Pulled 2026-11-26 (UTC) by `pull_acn.py`; counts and sha256 in `data/PULL_SUMMARY.json`:
  - caltech 3,087 sessions (2,837 with pilot and current series, 2,507 with userID)
  - jpl 5,592 (5,327; 5,428)
  - office001 463 (463; 45)
- A first pull without time series (`data_nots/`, list endpoint, inclusive window end) returned 3,090 / 5,594 / 463; the 5 extra sessions sit on week boundaries. Not used.
- Fields present: connectionTime, disconnectTime, doneChargingTime, kWhDelivered, userID, userInputs, stationID, spaceID, siteID, clusterID, timezone, pilotSignal {timestamps, pilot}, chargingCurrent {timestamps, current}.
- Terms: registration accepted by Varma 2026-11-25. Raw files are not committed or published; derived results may be published with the citation once the terms are read (open item).
- Rules for use: `PROTOCOL_ACN.md` (frozen, sha256 a2a8d057…).

## Second dataset (T2-rep): Perth & Kinross Council, EV Charge Station Use, Sep 2018 – Aug 2019
- File `data_pk/pk_2018_19.csv` from https://www.arcgis.com/sharing/rest/content/items/ca6cae3df2624832a2eaf678f2eabee8/data, pulled 2026-11-26, 32,711 rows, sha256 147df297…
- Licence: Open Government Licence v3.0; acknowledge Perth & Kinross Council as the source.
- Used: AC destination chargers only (amendment 2): 8,092 sessions across the four AC models.

## Third dataset (T2-rep): City of Palo Alto, EV Charging Station Usage (July 2011 – Dec 2020)
- File `data_pa/pa_download.bin` (CSV) from https://data.paloalto.gov/datasets/194693-electric-vehicle-charging-station-usage-july-2011-dec-2020.download/, pulled 2026-11-26, 85.4 MB, sha256 e65f5f5d…
- Licence basis: the official portal footer's Open Data badge linking the Open Data Commons PDDL (portal-wide, not dataset-specific).
- Fields include Station Name, Start/End Date with time-zone columns, Energy (kWh), Address 1, User ID. Rules: amendment 4.
