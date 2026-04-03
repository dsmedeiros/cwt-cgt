# Current Theory Status v40

## Snapshot
The theory now has:
- two positive noisy scaffold benchmarks: **C** and **G**,
- a **pooled positive noisy scaffold rule** derived from their combined train rows,
- held-out support on both benchmarks under the same pooled rule.

## Switch result (`γ = 0.30`)
- benchmark C held-out combined: `R² ≈ 0.9412`
- benchmark G held-out combined: `R² ≈ 0.9277`
- pooled held-out combined across C and G: `R² ≈ 0.9380`
- pooled held-out new-family across C and G: `R² ≈ 0.9191`
- pooled held-out combined correlation: `≈ 0.9788`
- sign agreement: `1.0`

## Read
This is the strongest noisy-scaffold result so far. It indicates that the noisy extension is not limited to a single positive benchmark or a one-way transfer. A common scaffold-level rule now survives on both positive noisy scaffold systems.

## Confidence
- coherent core: **moderate to moderately high**
- noisy extension inside scaffold: **moderate to moderately high**
- final microscopic completeness: **lower**

## Verdict
`pooled_positive_noisy_scaffold_supported`
