# CWT-CGT Phase 13 — Local Mixed-State Susceptibility Atlas

## Goal

Replace the noisy lane’s single global mixed-state slope with a **local susceptibility atlas** estimated from the continuous-time Lindblad-style graph-local generator.

## What changed

- The mixed-state phase convention is now uniform across the benchmark set: each loop family is unwrapped over dephasing and sign-aligned against the pure-state flux gap at γ=0.
- Benchmark reporting is now patch-based. The basic unit is a **patch family** defined by loop shape × loop center, with side lengths providing the local fit samples.
- The noisy lane is now summarized with local patch slopes χ rather than one benchmark-wide coefficient.
- Control and exclusion benchmarks were rerun under the same convention so the noisy lane is reported uniformly across A, B, C, D, and F.

## Atlas definition

For a trusted patch family ℓ at control patch center λ₀ and branch b, the noisy loop law is now reported as

```text
ΔR_γ ≈ χ(λ₀, b, ℓ; γ) · Φ_mix(γ)
```

where χ is fit locally from trusted loop pairs, not assumed to be global over the whole benchmark domain.

## Phase 13 benchmark picture

- benchmark_a: verdict=null_like, switch γ=0.30, global R²=None, best patch=None, best patch R²=None, trusted=6, excluded=0
- benchmark_b: verdict=weak_control, switch γ=0.30, global R²=None, best patch=None, best patch R²=None, trusted=6, excluded=6
- benchmark_c: verdict=local_fragmented, switch γ=0.30, global R²=0.06176010627482531, best patch=square|(+0.00,+0.00), best patch R²=0.8751907407006734, trusted=12, excluded=0
- benchmark_d: verdict=null_like, switch γ=0.30, global R²=None, best patch=None, best patch R²=None, trusted=4, excluded=0
- benchmark_f: verdict=excluded_R4, switch γ=0.30, global R²=None, best patch=None, best patch R²=None, trusted=0, excluded=6

## Main implication

The noisy lane is no longer well-described by one global coefficient. It is better understood as a **local response atlas** with patch-to-patch magnitude changes and, in the positive ring benchmark, patch-to-patch sign fragmentation.