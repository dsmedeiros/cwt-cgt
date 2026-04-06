# Theory / Implementation Alignment v36

The theory documents are aligned to the current scaffold implementation as follows:

- pooled positive noisy scaffold rules are treated as **scaffold-level transfer laws**, not general laws
- adversarial-family runs are treated as **boundary probes**, not regressions to be optimized away
- the new sign-robustness correction is described as a **generator-side partial repair**, not as a final universal mechanism

The current implementation therefore supports a stronger boundary map for the noisy layer than before, but not a claim of completed universality.
