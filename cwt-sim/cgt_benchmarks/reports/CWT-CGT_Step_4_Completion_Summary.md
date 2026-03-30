# CWT-CGT Step 4 Completion Summary

## What this step covered

This step completed the next block after the passive benchmark reports:

1. repaired the broken code contract in the runnable project,
2. added held-out loop-family and off-center robustness protocols,
3. regenerated the benchmark outputs from the repaired package,
4. added a Phase 5 modal-extension spec and implementation scaffold.

## Important repair

A real package inconsistency was found and fixed.
The project had already moved its datamodel to candidate-state / branch-continuation semantics, but `benchmarks.py` still used the older constructor contract.
That meant the package did not import cleanly until this step repaired the benchmark definitions.

## Current benchmark status

### Passive block

- Benchmark A: null-like, all trusted default loops remain null.
- Benchmark B: null-like, with an R4 upper-band scan region.
- Benchmark C: positive signed-loop benchmark, trusted default loops show sign-flip fraction 1.0.
- Benchmark D: null-like, all trusted default loops remain null.

### Robustness block

- A: 4/4 robustness protocols pass.
- B: 4/4 robustness protocols pass.
- C: 4/4 robustness protocols pass.
- D: 4/4 robustness protocols pass.

The main nuance is Benchmark C: pooled off-center fits have lower global R² because the local susceptibility changes from center to center, but each center separately retains a clean positive signed-flux law.
That is now treated as a theory refinement rather than a failure.

## New artifacts added

- robustness JSON outputs per benchmark,
- robustness markdown reports and aggregate report,
- updated plotting/report generation,
- `modal.py` scaffold,
- Phase 5 modal-extension spec,
- hardened theory v3 and implementation-alignment v2 notes.

## Validation status

- package imports cleanly,
- smoke tests pass,
- benchmark and robustness reports regenerate from the repaired codebase.

## What changed conceptually

This step sharpened one theoretical point:

\[
\Delta R_\gamma \approx \chi(\lambda_0,b)\,\Phi_\gamma
\]

should be interpreted **locally within a trusted branch patch**.
The sign law is robust across trusted patches, but the fitted slope can vary with location.

That refinement is now the bridge to Phase 5, whose job is to explain the patchwise coefficient \(\chi(\lambda,b)\) in modal/operator terms.
