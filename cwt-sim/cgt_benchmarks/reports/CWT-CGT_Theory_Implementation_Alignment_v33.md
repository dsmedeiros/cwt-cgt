# Theory / Implementation Alignment v33

This pass adds two scaffold-level updates:

1. **Phase 43** introduces benchmark I, a non-ring ladder positive noisy scaffold benchmark.
2. **Phase 44** keeps the pooled positive-noisy scaffold rule fixed and adds a stronger perturbation family on benchmark I.

Important alignment notes:
- Benchmark I is still a **designed scaffold benchmark**, not an external empirical case.
- The pooled noisy rule is transferred from the earlier pooled scaffold derivation; benchmark I does not refit the rule.
- The stronger perturbation-family test stresses transfer on the same benchmark without changing the rule.
- The project copy `CWT-CGT_Project_v5_4` is a small self-contained writable copy containing the source pooled payload, the new phase analysis code, the new benchmark outputs, and smoke tests.
