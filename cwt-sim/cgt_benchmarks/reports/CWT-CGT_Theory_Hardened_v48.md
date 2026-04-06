# Theory v48

The theory remains strongest as a **layered, benchmarked research framework**.

Latest extension:
- built a **pooled-seven positive noisy scaffold rule** across C, G, H, I, J, K, and L
- reran the **adversarial sign-break family** on benchmark L under that pooled-seven rule unchanged
- then added a **generator-side sign-robustness correction** to test whether the sign boundary can be partially repaired without benchmark-specific response refit

Switch-slice highlights at `γ = 0.30`:
- pooled-seven held-out combined `R² ≈ 0.9864`
- pooled-seven held-out sign agreement `≈ 0.9921`
- adversarial family under pooled-seven unchanged: combined `R² ≈ 0.2147`, sign agreement `≈ 0.9375`
- generator sign-robustness correction on the same adversarial rows: combined `R² ≈ 0.6812`, sign agreement `≈ 0.9583`

Interpretation:
The noisy scaffold layer now supports a shared pooled rule across **seven** positive scaffold benchmarks. The adversarial family still exposes a real failure boundary, but a generator-side sign correction recovers a meaningful part of that lost sign robustness without changing the underlying pooled scaffold rule.
