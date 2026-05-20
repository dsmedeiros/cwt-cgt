# Phase 232 — Externalization Status and Next Steps

## Status
The project has reached the point where the highest-value progress is not more internal variants; it is real-data externalization.

## Immediate next actions
1. Ingest Citi Bike station_information + one month of trips.
2. Build first event-graph pilot slice from Citi Bike.
3. Ingest OEDI IEEE123 topology + sensors.
4. Build first explicit-topology pilot slice.
5. Only after those two are clean, move to Chicago Traffic Tracker.

## Freeze rules
- Do not add more internal noisy scaffold benchmarks unless a real-data pilot fails for a reason that genuinely requires synthetic diagnosis.
- Prefer adapter improvements over new synthetic families.
