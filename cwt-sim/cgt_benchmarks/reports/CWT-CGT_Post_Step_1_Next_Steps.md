# CWT-CGT Next Steps After Step 1

Step 1 is now complete: the project has a working loop-family execution layer.

## New baseline

The code can now:
- run mesh scans,
- run nested clockwise/counter-clockwise loops,
- compute signed loop areas,
- compute signed loop fluxes,
- compare orientation-reversed responses,
- write benchmark artifacts into the project results tree.

## Highest-priority next step

### Step 2 — Branch continuation and branch IDs

Add explicit continuation logic so the mesh and loop layers can distinguish:
- smooth branch following,
- branch switching,
- unresolved tiles,
- R4 hysteretic paths.

Deliverables:
- continuation seeds,
- branch matching rules,
- branch ID maps,
- switch markers,
- branch residual logs,
- R4-aware loop exclusions.

## After that

1. Plotting and visual diagnostics.
2. Benchmark acceptance reports.
3. Full A/B/C/D acceptance pass.
4. Modal upgrade lane.
