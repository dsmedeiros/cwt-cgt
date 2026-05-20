# Phase 231 — Externalization Runbook

## First externalization sprint

### Sprint 1 — Citi Bike NYC
Deliverables:
- station graph from station_information
- trip-event table from one historical month
- observation/censoring table aligned to trips and station status
- first external event-graph pilot slice

### Sprint 2 — OEDI IEEE123
Deliverables:
- explicit feeder graph
- sensor-location observation table
- state/control split from load/PV time series
- first explicit-topology external pilot slice

### Sprint 3 — Chicago Traffic Tracker
Deliverables:
- segment graph builder
- segment state table
- historical holdout split
- first road-segment external pilot slice

## Success criteria
A pilot counts as successful if it produces the canonical schema cleanly and yields a nontrivial benchmark slice that can be run without manual data surgery after the first adapter pass.
