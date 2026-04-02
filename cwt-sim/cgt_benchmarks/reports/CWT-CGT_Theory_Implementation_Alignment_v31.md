# Theory / Implementation Alignment v31

The implementation now includes a second positive noisy scaffold benchmark, benchmark G.

## Alignment
- The theory now explicitly distinguishes:
  - validated coherent/passive scaffold behavior,
  - explicit R4 exclusion behavior,
  - auxiliary topology behavior,
  - noisy scaffold transfer behavior.
- Benchmark G is treated as a **designed scaffold benchmark**. The theory text does not present it as an empirical or external validation benchmark.

## Remaining mismatch
The current noisy rule still reuses coefficients learned or accepted from benchmark C and transfers them into benchmark G. That is enough to strengthen scaffold-level confidence, but it is not yet a benchmark-family-free microscopic derivation.
