# CWT-CGT Step 2 Completion Summary

Step 2 is complete: the project now has a branch-continuation layer with persistent branch IDs.

## What was added

- dual-sweep mesh continuation,
- persistent branch-ID maps,
- chosen-branch maps and ambiguity maps,
- switch-tile logs and residual/gap maps,
- pathwise branch continuation for loops,
- loop-level switch markers and ambiguity markers,
- R4-aware loop exclusion from the signed-loop fit.

## New code modules

- `04_code/src/cwt_cgt/geometry.py`
- `04_code/src/cwt_cgt/models.py`
- `04_code/src/cwt_cgt/continuation.py`
- updated `benchmarks.py`, `runner.py`, `loop_protocols.py`

## Benchmark snapshot

### Default benchmark suite

- Benchmark A: `R1=81`, switch tiles = `0`, branch IDs = `A0` only.
- Benchmark B: `R1=67`, `R3=2`, `R4=12`; upper-band ambiguity resolves into `B_minus | ambiguous | B_plus` structure.
- Benchmark C: `R1=66`, `R3=6`, `R4=9`; center loops remain trusted and preserve the signed-loop law.
- Benchmark D: `R1=81`, switch tiles = `0`, branch IDs = `D0` only.

### Loop suite snapshot

- Benchmark A: trusted pairs = `4`, excluded pairs = `0`, sign-flip fraction = `0.000`.
- Benchmark B: trusted pairs = `4`, excluded pairs = `0`, sign-flip fraction = `0.000`.
- Benchmark C: trusted pairs = `4`, excluded pairs = `0`, sign-flip fraction = `1.000`, response-vs-flux `R^2 ≈ 0.99939`.
- Benchmark D: trusted pairs = `4`, excluded pairs = `0`, sign-flip fraction = `0.000`.

## R4 exclusion demos

Two extra demo artifacts now show the exclusion logic explicitly:

- `03_benchmarks/results/benchmark_B_line/benchmark_b_loops_r4_demo.json`
- `03_benchmarks/results/benchmark_C_ring/benchmark_c_loops_r4_demo.json`

These loop families are centered in the continuation-ambiguous upper band. All pairs are excluded from fitting because every run is labeled `R4`.

## Interpretation

The project can now distinguish:
- smooth branch following,
- continuation ambiguity on the mesh,
- pathwise branch ambiguity on loops,
- trusted R1 loops used for signed-loop fits,
- excluded R4 loops that would otherwise contaminate the benchmark law.

This is the point where the regime atlas becomes operational rather than purely descriptive.

## Next step

Build plotting and report-generation utilities so every benchmark can emit branch maps, regime maps, curvature figures, and a filled report skeleton.
