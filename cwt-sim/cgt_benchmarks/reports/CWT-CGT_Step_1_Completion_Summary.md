# CWT-CGT Step 1 Completion Summary

Step 1 is complete: the project now has a working loop-family execution layer.

## Benchmark snapshot

- Benchmark A: sign-flip fraction = 0.000; orientation-gap mean abs = 0.000e+00
- Benchmark B: sign-flip fraction = 0.000; orientation-gap mean abs = 0.000e+00
- Benchmark C: sign-flip fraction = 1.000; response-vs-area R^2 = 0.999909
- Benchmark D: sign-flip fraction = 0.000; orientation-gap mean abs = 0.000e+00

## Interpretation

The loop runner now separates the null controls (A/D), the sensitivity-without-robust-pumping case (B), and the positive signed-loop case (C) in the way the hardened benchmark suite intended.

## Next steps

1. Add branch continuation and persistent branch IDs.
2. Add plotting/report-generation utilities.
3. Run the full acceptance pass and fill the benchmark report template.
4. Only then move into the modal upgrade lane.
