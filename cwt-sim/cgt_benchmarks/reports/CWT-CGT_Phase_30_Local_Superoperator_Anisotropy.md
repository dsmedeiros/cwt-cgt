# CWT-CGT Phase 30 — Local Superoperator Anisotropy / Tensor Rule

## Goal

Replace the scalar local superoperator-area share from Phase 29 with a fuller **local superoperator anisotropy / tensor rule** while keeping the broadened held-out family set fixed.

## Accepted construction

For canonical train rows, define:
- `generator_var_ratio = |generator_var_mean| / mean_abs(generator_var_mean)_train`
- `boundary_ratio = |boundary_distance_u| / mean_abs(boundary_distance_u)_train`
- `boundary_transport_ratio = |m2_gap_boundary| / mean_abs(m2_gap_boundary)_train`
- `tensor_cross = sqrt(generator_var_ratio * boundary_transport_ratio)`
- `tensor_anisotropy = sqrt((generator_var_ratio - boundary_ratio)^2 + 4 * tensor_cross^2) / (generator_var_ratio + boundary_ratio)`

Then set:
- `alpha_tensor = alpha_gap`
- `beta_boundary = 1 - boundary_compactness`
- `mean_train_anisotropy = mean(tensor_anisotropy)_train`

and use:
- `local_tensor_share = clip((1 + alpha_tensor * (tensor_anisotropy - mean_train_anisotropy)) * (1 - beta_boundary * (boundary_ratio - 1)), 0.65, 1.35)`

Apply that share only to the area term of the accepted noisy-loop predictor.

## Result

At benchmark C, switch slice `γ = 0.30`:
- Phase 29 held-out new-family `R² ≈ 0.9006`
- Phase 30 held-out new-family `R² ≈ 0.9089`
- Phase 29 held-out combined `R² ≈ 0.9468`
- Phase 30 held-out combined `R² ≈ 0.9668`
- combined correlation `≈ 0.9873`
- sign agreement `= 1.0`

## Interpretation

This phase strengthens the noisy loop-side layer because the broadened held-out transfer survives after replacing the scalar local area share with a fuller tensor-like anisotropy rule. The remaining boundary is that the off-diagonal tensor channel is still a compact geometric-mean construction rather than a direct local superoperator covariance rule.
