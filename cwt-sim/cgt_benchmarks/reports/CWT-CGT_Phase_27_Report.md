# CWT-CGT Phase 27 Report

## Summary

Phase 27 replaces the remaining fixed lower-order structural normalizers with generator-moment normalizers and reruns the same broadened held-out family set unchanged.

## Switch-slice metrics (benchmark C, γ = 0.30)

- baseline held-out new-family `R² ≈ 0.7937`
- Phase 25 held-out new-family `R² ≈ 0.8459`
- Phase 26 held-out new-family `R² ≈ 0.8673`
- Phase 27 held-out new-family `R² ≈ 0.8691`
- baseline held-out combined `R² ≈ 0.8862`
- Phase 25 held-out combined `R² ≈ 0.9286`
- Phase 26 held-out combined `R² ≈ 0.9249`
- Phase 27 held-out combined `R² ≈ 0.9254`
- Phase 27 combined correlation `≈ 0.9623`
- Phase 27 sign agreement `= 1.0`

## Interpretation

The broadened held-out transfer survives after removing the older fixed lower-order structural normalizers. The improvement over Phase 26 is small but positive, so this phase mainly strengthens the **derivation** rather than changing the qualitative story.

## Accepted verdict

`moment_normalizer_transfer_supported`
