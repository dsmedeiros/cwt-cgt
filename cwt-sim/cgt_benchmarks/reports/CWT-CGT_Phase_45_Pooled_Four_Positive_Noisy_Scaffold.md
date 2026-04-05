# Phase 45 — Pooled Four-Positive Noisy Scaffold

Goal: replace the earlier narrower pooled noisy scaffold rule with a broader pooled rule built from the train rows of **C, G, H, and I**.

Method:
- collect the train rows (`square`, `circle`) from the four positive noisy scaffold benchmarks,
- recompute the compactness-normalizer parameters from that pooled train set,
- fit one pooled linear rule on the standard scaffold feature set,
- evaluate held-out regular families on each benchmark with no benchmark-specific refit.

This phase strengthens the noisy scaffold layer by moving from pairwise / narrower pooling to a broader positive-scaffold pool.
