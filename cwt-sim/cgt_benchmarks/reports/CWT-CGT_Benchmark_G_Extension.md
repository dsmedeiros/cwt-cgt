# Benchmark G Extension

Benchmark G is a **designed second positive noisy scaffold benchmark** added to test whether the accepted noisy loop-side rule from benchmark C transfers to a distinct non-null benchmark without refitting the rule itself.

It is intentionally framed as a scaffold-level benchmark rather than an empirical validation case.

## Design intent
- Keep the same shape split: `square|circle` for train, `diamond|rounded_square` for held-out base, `ellipse|stadium|hexagon` for held-out new.
- Reuse the accepted Phase 39 noisy rule from benchmark C unchanged.
- Shift the sign-boundary location and local share geometry enough that benchmark G is not just a trivial clone of benchmark C.

## Interpretation boundary
A successful transfer here strengthens confidence that the noisy rule is not only a one-benchmark artifact **within the scaffold**.
It does **not** by itself prove generality outside the scaffold.
