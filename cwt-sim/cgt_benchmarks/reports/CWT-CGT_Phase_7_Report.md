# Phase 7 Report — Holonomy, Sign Harmonization, and Mixed-State Lane

## Holonomy refinement

- sign harmonization factor: -1.0
- raw tangent vs state curvature correlation: -1.0
- harmonized tangent vs state curvature correlation: 1.0
- harmonized Jacobian vs state curvature correlation: 0.9377180674018161
- response vs harmonized tangent phase R^2: 0.9999442535881575
- tangent phase vs state signed flux R^2: 1.0

## Mixed-state lane

- recommended switch dephasing: 0.2

| dephasing | mixed curvature scale | mixed curvature corr | response vs Uhlmann phase R^2 | response vs pure flux R^2 | mean mixed coherence |
|---:|---:|---:|---:|---:|---:|
| 0.00 | 0.999998 | 1.000000 | 0.999944 | 0.999944 | 0.998832 |
| 0.20 | 0.670103 | 0.999834 | 0.999966 | 0.999944 | 0.799066 |
| 0.40 | 0.396126 | 0.999193 | 0.999962 | 0.999944 | 0.599299 |
| 0.60 | 0.185849 | 0.997732 | 0.999922 | 0.999944 | 0.399533 |
| 0.80 | 0.049317 | 0.994761 | 0.999834 | 0.999944 | 0.199766 |

## Interpretation

- The old weak Jacobian modal phase is replaced by a projective tangent-holonomy phase built from Jacobian-derived response tangents.
- In the current benchmark C implementation, the raw tangent holonomy carries the opposite orientation sign relative to the state plaquette convention, and a single global factor of -1 harmonizes them.
- Under dephasing, the mixed-state curvature map keeps the same geometry but its magnitude collapses. That is why the mixed-state lane is the right object for reporting dephased geometric magnitude even when pure signed flux remains empirically correlated.
