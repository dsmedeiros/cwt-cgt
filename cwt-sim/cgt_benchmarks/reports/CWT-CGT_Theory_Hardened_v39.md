# CWT-CGT Theory v39

This revision adds **Benchmark G**, a designed second positive noisy scaffold benchmark, and evaluates it under the **accepted Phase 39 noisy loop-side rule** reused unchanged from benchmark C.

## What changed
- The project now tests whether the current noisy rule survives beyond benchmark C.
- Benchmark G keeps the same loop-family split:
  - train: `square`, `circle`
  - held-out base: `diamond`, `rounded_square`
  - held-out new: `ellipse`, `stadium`, `hexagon`
- No rule refit is performed in this phase. The accepted benchmark-C Phase 39 coefficients, higher-order terms, and compactness-normalizer rule are transferred as-is.

## Benchmark G result
At the switch slice `γ = 0.30`:
- train `R² ≈ 0.9971`
- held-out base `R² ≈ 0.9909`
- held-out new `R² ≈ 0.8779`
- held-out combined `R² ≈ 0.9154`
- held-out combined correlation `≈ 0.9889`
- sign agreement `= 1.0`

## Interpretation
This **does not** make the noisy theory universal. It **does** strengthen the theory inside the scaffold:

1. The noisy loop-side law is no longer only a one-benchmark success.
2. A second positive noisy benchmark can be supported under the same accepted rule family.
3. The remaining gap is now less about internal consistency and more about breadth of positive cases and how benchmark-specific the construction still is.

## Confidence update
- **High**: the hardening direction remains correct.
- **Moderate to moderately high**: the coherent, branch-resolved passive core.
- **Moderate**: the noisy extension as a real structured scaffold layer.
- **Lower**: the current open-system scaffold as a final microscopic theory.

As a rough estimate:
- about **84–87% complete** as a disciplined benchmarked framework
- about **58–62% complete** as a broadly convincing general theory

## Boundary
Benchmark G is a **designed scaffold benchmark**, not an external empirical validation system.
