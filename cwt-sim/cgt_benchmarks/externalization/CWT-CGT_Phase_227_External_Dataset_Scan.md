# Phase 227 — External Dataset Scan

## Goal
Move the project out of purely internal scaffold/bridge benchmarking and into public-data externalization.

## Selection criteria
Each candidate is scored on:
1. graph availability
2. temporal richness
3. observation realism
4. control/exogenous proxy richness
5. access friction
6. reproducibility / licensing clarity

Scores are heuristic and meant for sequencing, not as scientific claims.

## Candidate matrix

| Candidate | Domain | Graph availability | Time structure | Observation mode | Access | Priority |
|---|---|---:|---|---|---|---|
| Citi Bike NYC | mobility events | explicit station graph via GBFS + trips | event-level + realtime GBFS | partial station trips, station status | public | P1 |
| Divvy Chicago | mobility events | explicit station graph via GBFS + trips | event-level + realtime GBFS | partial station trips, station status | public | P1 |
| Chicago Traffic Tracker | traffic speeds/congestion | road segments; graph built from segment adjacency | historical segment congestion | partial segment speeds | public | P1 |
| OEDI IEEE123 | power grid | explicit feeder topology + sensors | time series load/PV + sensor locations | partial instrumented measurements | public | P1 |
| NYC DOT Traffic Speeds | traffic speeds | implicit road-endpoint graph | average speeds between endpoints | partial endpoint/path observations | public | P2 |
| TfL Unified API / cycling feeds | multimodal transport | explicit stations/stops | live + downloadable feeds | partial operational observations | registration for live feeds | P2 |

## Immediate recommendation
Start with three external pilots in this order:
1. **Citi Bike NYC** — easiest real event-based graph pilot.
2. **OEDI IEEE123** — easiest explicit-topology non-mobility pilot.
3. **Chicago Traffic Tracker** — easiest road-segment historical pilot.

## Why this ordering
- Citi Bike gives the cleanest first test of event-stream externalization.
- OEDI gives the cleanest first test of explicit topology + sensor placement.
- Chicago Traffic Tracker gives the cleanest first test of segment-level road dynamics.
