# Phase 228 — Externalization Gate

## Objective
Define when the project should stop adding internal synthetic variants and start spending most effort on public-data pilots.

## Gate decision
**Gate is open.**

The current state of the project is strong enough that further internal-only expansion should be secondary to public-data externalization.

## Entry requirements already met
- coherent/passive core is stable
- noisy scaffold rule transfers across multiple positive scaffold benchmarks
- bridge lane has enough breadth to support adapter design
- adversarial correction class exists and has some transfer value

## Externalization tracks

### Track A — Mobility event graphs
Target: Citi Bike, then Divvy.

### Track B — Road-segment traffic graphs
Target: Chicago Traffic Tracker, then NYC DOT Traffic Speeds.

### Track C — Explicit-topology infrastructure graphs
Target: OEDI IEEE123.

## Go / no-go rule
The next project energy should go to Track A and Track C first. Track B should begin once station/event ingestion and explicit-topology ingestion both exist.
