# Current Theory Status v48

## Summary

The theory is strongest as a **layered, benchmarked scaffold framework**.

- The **coherent, branch-resolved passive core** remains the strongest layer.
- The **R4 branch-switching lane** remains explicit and separate.
- The **noisy scaffold layer** now transfers across seven positive scaffold benchmarks inside the program.
- The **adversarial family** on benchmark L remains the cleanest sign-robustness failure boundary.
- A **generator-side sign correction** can partially repair that boundary, but it does not erase it.

## Latest update

At the switch slice `γ = 0.30`:

### Pooled-seven positive noisy scaffold rule
- held-out combined `R² ≈ 0.9864`
- held-out combined correlation `≈ 0.9932`
- held-out combined sign agreement `≈ 0.9921`

### Benchmark L adversarial family under pooled-seven unchanged
- adversarial-family `R² ≈ -0.2148`
- adversarial-family sign agreement `≈ 0.8333`
- combined `R² ≈ 0.2147`
- combined sign agreement `≈ 0.9375`

### Generator sign-robustness correction on the same adversarial rows
- adversarial-family `R² ≈ 0.5216`
- adversarial-family sign agreement `≈ 0.9167`
- combined `R² ≈ 0.6812`
- combined correlation `≈ 0.8764`
- combined sign agreement `≈ 0.9583`

## Confidence

- **High** confidence that the hardening direction is right.
- **Moderate to moderately high** confidence in the coherent/passive core.
- **Moderate, improving** confidence in the noisy scaffold layer.
- **Lower** confidence that the current noisy scaffold is already the final microscopic theory.

## Boundary

The adversarial family remains useful because it exposes a **sign-robustness boundary**. The new correction improves that boundary, but the need for a correction is itself evidence that the current noisy rule is not yet universally complete.
