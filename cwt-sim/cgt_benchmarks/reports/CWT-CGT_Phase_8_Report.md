# CWT-CGT Phase 8 Report

## Summary

Phase 8 adds a topology benchmark and an explicit multi-branch benchmark, while also repairing the live project tree so the code, reports, and theory documents are aligned.

## Benchmark F — explicit R4 / hysteresis

The new multi-branch benchmark is a four-node bistable line family.

Observed default result:

- scan regimes: R1 = 36, R4 = 45,
- persistent branch counts: left = 18, ambiguous = 45, right = 18,
- switch tiles: 45,
- loop pairs: 9 total,
- trusted pairs: 3,
- excluded pairs: 6,
- R4 pairs: 6,
- trusted flux fit: null-like.

Interpretation:

The benchmark succeeds because it demonstrates branch switching and loop exclusion by construction. It is not intended to generate a positive loop law.

## Benchmark E — topology on a real torus

The new topology benchmark is an auxiliary periodic two-band model on a control torus.

Representative gapped cases:

- \(m=-1,\varepsilon=0\): \(C=-1\), min gap \(\approx 2.0000\),
- \(m=-1,\varepsilon=0.15\): \(C=-1\), min gap \(\approx 2.0016\),
- \(m=1,\varepsilon=0\): \(C=+1\), min gap \(\approx 2.0000\),
- \(m=1,\varepsilon=0.15\): \(C=+1\), min gap \(\approx 1.9507\).

Interpretation:

This is the first benchmark in the project where integer topological language is actually warranted.

## Reporting refresh

The benchmark automation now includes benchmark F in the acceptance report, fixes branch-atlas summaries to use the live payload shape, and adds a dedicated topology report.

## Current state after Phase 8

The project now has:

1. passive branch geometry,
2. explicit Jacobian response geometry,
3. harmonized tangent holonomy,
4. mixed-state reporting lane,
5. explicit R4 benchmark,
6. auxiliary topology benchmark.

## Remaining highest-value next step

The next strongest move is not more topology. It is a better noisy dynamics layer: replace the current dephasing scaffold with a fuller CPTP/noisy evolution model, then revisit how the coherent and mixed-state lanes meet.
