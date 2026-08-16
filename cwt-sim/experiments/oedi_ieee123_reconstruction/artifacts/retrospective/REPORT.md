# OEDI IEEE123 retrospective reconstruction report

> **Correction and scope:** exact retrospective reconstruction from a pinned official source consistent with the archived vector. This does not prove which revision/parser the 2026 run used, restore its historical provenance, or support CGT.

> Dataset class: profiles packaged with an external public test-system dataset; measurement provenance unspecified; field-observation provenance is not established.

**Reconstruction status:** `PASS`.  
**Theory support:** `NONE`.

## Exact archived-vector reconstruction

| Quantity | Reconstructed value |
|---|---:|
| historical graph nodes after Line endpoints | 214 |
| Line edges including Sw7/Sw8 | 126 |
| Unique sensor buses | 85 |
| finite mean nearest-sensor hops | 0.415384615384615 |
| full-graph sensor degree mean | 1.67058823529412 |
| full-graph nonsensor degree mean | 0.852713178294574 |
| full-graph sensor betweenness mean | 0.00559472260868206 |
| full-graph nonsensor betweenness mean | 0.00520744279435081 |
| five-profile dependent pair Spearman | -0.309090909090909 |
| five-profile dependent pair Pearson | -0.353413576460395 |
| dimensionless PV>=0.2 shape-ratio alpha | 1.15727185400764 |

## Parser defect and corrected interpretation

Buscoords contributes 212 unique labels (82 `s*` plot/device labels plus 130 physical bus labels); the two Line endpoints `300_OPEN` and `94_OPEN` raise the historical graph to 214 nodes. The historical parser creates **84 isolates** and reports finite sensor distance for only **130** of 214 graph nodes. The isolates include 82 `s*` plot/device labels plus physical buses `150` and `610`, because transformer connectivity was omitted.

Removing those isolates reverses the claimed structural targeting:

| Active-only quantity | Sensor | Nonsensor |
|---|---:|---:|
| mean degree | 1.67058823529412 | 2.44444444444444 |
| mean betweenness | 0.0153001025991792 | 0.0408241817398794 |

The corrected primary graph has 130 physical buses and 129 unique edges, is connected=True, and has 0 isolates. Sw7/Sw8 are excluded only under the dataset-specific `*_OPEN` pseudo-terminal convention; their DSS Line objects are executable. Including both stubs leaves every load-bus distance exactly unchanged.

Corrected energized-graph sensor diagnostics also reverse the old interpretation: all 130 buses are reachable (mean/median/max hops 0.423076923076923/0/3); sensor versus nonsensor mean degree is 1.68235294117647 versus 2.55555555555556, and normalized betweenness is 0.0473352713178295 versus 0.167318044788975.

The ten pair records reuse only five selected profiles and are not ten independent observations. Alpha is a tautological dimensionless mean-zeroing ratio; it ignores S49a's 35 kW rating, PV49's 50 kVA/Pmpp rating, and the verified-but-unused temperature series. Its PV>=0.2 mask contains exactly 15,098 quarter-hours. It is not a physical net-power balance or response test.

## Bottom line

The old positive structural/sign-boundary interpretation is refuted. The only supported claim is reproducibility of the archived numeric vector from one pinned official source consistent with it. Historical provenance remains unproven. Chicago/Citi remain metadata-only; the central empirical/external CWT claim remains proof incomplete.
