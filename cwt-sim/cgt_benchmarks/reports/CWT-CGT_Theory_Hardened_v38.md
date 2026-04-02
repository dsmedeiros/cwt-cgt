# CWT–CGT Hardened Theory v38

## Current core
The theory remains organized as a layered framework:

1. **Coherent branch-resolved passive core**  
   Stable branch states over exogenous controls define the primary geometry and the most trusted response law.

2. **Regime separation**  
   Smooth coherent response, mixed/open noisy response, explicit R4 branch switching, and auxiliary topology remain separated rather than collapsed into one universal claim.

3. **Noisy loop-side extension**  
   The noisy loop predictor is now built from local superoperator geometry, higher-order generator terms, and held-out transfer tests over a fixed broadened loop-family split.

## What changed in v38
This phase replaces the remaining shared train-mean normalization inside the compactness-share rule with a **local superoperator-geometry compactness normalizer**:
- raw compactness share: `share_geometry / local_area_share`
- local compactness normalizer: `sqrt(local_tensor_share * local_covariance_share) / sqrt(local_area_share)`
- local compactness exponent: `0.8 * (raw_compactness_share / local_compactness_normalizer)`

The broadened held-out family split is unchanged.

## Benchmark-C switch-slice result
At `γ = 0.30`:
- Phase 38 held-out new-family `R² ≈ 0.9321`
- Phase 39 held-out new-family `R² ≈ 0.9381`
- Phase 38 held-out combined `R² ≈ 0.9744`
- Phase 39 held-out combined `R² ≈ 0.9751`
- Combined correlation `≈ 0.9888`
- Sign agreement `= 1.0`

## Interpretation
This is another **derivational tightening** step. The noisy positive benchmark stays strong and slightly improves under the fixed broadened held-out split. The result still does not establish a universal noisy law, but it strengthens the case that the noisy loop-side correction is tracking a real local superoperator-geometry structure rather than only a loose fitted surrogate.

## Current confidence
- **High** that the hardening and layering decisions were correct.
- **Moderate to moderately high** in the coherent/passive branch-resolved core.
- **Moderate** in the noisy extension as a structured benchmarked layer.
- **Lower** in any claim that the present open-system scaffold is already the final microscopic theory.
