# CWT-CGT Theory — Hardened v50

This update extends the adversarial-boundary program. The pooled-seven positive noisy scaffold rule remains unchanged, and the same generator-side sign-robustness correction that improved benchmark L is now tested on a second adversarial family on a different positive scaffold benchmark, benchmark I (nonring ladder).

## Status change in this version
The noisy scaffold layer now has:
1. pooled-seven positive benchmark support,
2. an explicit adversarial sign-break boundary on benchmark L,
3. and a transferred generator-side sign correction on benchmark I.

## New phase result
At the switch slice γ = 0.30 on benchmark I:
- adversarial-family-only raw transfer: R² ≈ 0.2409, sign agreement ≈ 0.8333
- adversarial-family-only corrected transfer: R² ≈ 0.7399, sign agreement ≈ 0.9583
- combined raw transfer: R² ≈ 0.4661, sign agreement ≈ 0.9167
- combined corrected transfer: R² ≈ 0.8411, sign agreement ≈ 0.9792

## Interpretation
The correction transfers. That strengthens confidence in the noisy scaffold layer’s boundary repair mechanism, but it does not yet justify a claim that the noisy open-system construction is final or universal. The coherent, branch-resolved passive core remains the strongest part of the theory.
