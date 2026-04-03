# Theory / Implementation Alignment v31

## New alignment point
The implementation now includes a **Phase 41 pooled positive noisy scaffold rule**.

## What is implemented
- load benchmark C Phase 39 scaffold rows,
- load benchmark G Phase 40 scaffold rows,
- pool the square/circle train rows,
- derive one shared compactness-normalizer rule per dephasing level,
- evaluate held-out base/new families on both benchmarks without benchmark-specific refit.

## What is *not* claimed
- no external validation,
- no claim that the pooled rule is benchmark-independent in the wild,
- no claim that the noisy microscopic generator is final.

## Practical meaning
The code now supports a stronger scaffold-level statement:
there is a shared noisy positive scaffold rule across at least two designed positive scaffold benchmarks.
