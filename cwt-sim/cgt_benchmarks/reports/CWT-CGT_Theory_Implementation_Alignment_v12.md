# CWT-CGT Theory / Implementation Alignment — v12

## What is now aligned

The implementation now matches the theory’s new noisy-lane statement in three ways:

1. The noisy object is a **smoothed local field**, not a benchmark-wide slope.
2. That field is estimated from **generator-driven minimal plaquettes**, not only from a few selected loop families.
3. Reporting is still regime-aware: A and D stay null-like, B stays weak, C stays positive, and F stays excluded by R4.

## What Phase 14 actually computes

For each benchmark and dephasing level, the code:

- builds the branch atlas on the scan grid,
- computes branch densities from the Lindblad-style generator,
- evaluates minimal CCW/CW plaquette responses,
- forms local χ = ΔR / ΔΦ_mix values only where the aligned holonomy clears a floor,
- robustly clips those local χ values,
- smooths them into a field over plaquette centers,
- and records sign consistency, effective support, and zero-crossing structure.

## Boundaries that remain

- This is more local than the Phase 13 patch atlas, but it is still a coarse-grained reconstruction rather than a closed-form derivation from the nonlinear graph update rule.
- The smoothed field is implementation-backed for the benchmark scaffold, not yet a universal theorem.
- The mixed-state lane still does not support a global single-slope claim.
