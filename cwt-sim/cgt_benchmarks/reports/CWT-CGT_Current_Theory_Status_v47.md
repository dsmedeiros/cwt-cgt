# Current Theory Status v47

## Summary

The theory is strongest as a **layered, benchmarked scaffold framework**.

- The **coherent, branch-resolved passive core** remains the strongest layer.
- The **R4 branch-switching lane** remains explicit and separate.
- The **noisy scaffold layer** now transfers across seven positive scaffold benchmarks inside the program.
- The new **adversarial family** on benchmark L shows where sign robustness starts to weaken.

## Latest update

At the switch slice `γ = 0.30` under the unchanged pooled-five noisy scaffold rule:

- **Benchmark L (fork-mesh)**
  - train `R² ≈ 0.9896`
  - held-out base `R² ≈ 0.9912`
  - held-out new `R² ≈ 0.9642`
  - held-out combined `R² ≈ 0.9744`
  - sign agreement `= 1.0`

- **Benchmark L adversarial sign-break family**
  - adversarial-family `R² ≈ -1.0454`
  - adversarial-family sign agreement `≈ 0.7917`
  - combined `R² ≈ -0.0874`
  - combined sign agreement `≈ 0.9074`

## Confidence

- **High** confidence that the hardening direction is right.
- **Moderate to moderately high** confidence in the coherent/passive core.
- **Moderate, improving** confidence in the noisy scaffold layer.
- **Lower** confidence that the current noisy scaffold is already the final microscopic theory.

## Boundary

The adversarial family is now useful because it starts to expose a **sign-robustness boundary** rather than only reducing goodness-of-fit.
