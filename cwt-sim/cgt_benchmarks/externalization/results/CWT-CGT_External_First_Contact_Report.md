# SUPERSEDED interpretation: OEDI IEEE123 first-contact report

> **Current correction (2026-08-15):** The numeric vector below has now been
> reconstructed exactly from canonical bytes at official upstream commit
> `7c8bcca06708ea2dd54b822821d637814ef08dc4`, a source consistent with the
> archived vector. This does **not** prove which source revision or parser the
> original run used. See
> [`experiments/oedi_ieee123_reconstruction/artifacts/retrospective/REPORT.md`](../../../experiments/oedi_ieee123_reconstruction/artifacts/retrospective/REPORT.md)
> and [`CWT-CGT_Proof_Status_v1.md`](../../reports/CWT-CGT_Proof_Status_v1.md).

> The old positive interpretation is refuted. Buscoords supplies 212 labels;
> the historical Line-only parser adds two `_OPEN` endpoints, creates 84
> isolates, omits transformer/regulator connectivity, and averages nonsensor
> centrality over those isolates. On the active-only and corrected 130-bus
> graphs, nonsensor degree and betweenness exceed sensor values. The ten pair
> records reuse only five post-hoc profiles. Alpha `1.157...` is a tautological
> ratio of dimensionless shapes that ignores the 35 kW load rating, 50 kVA/Pmpp
> PV rating, and verified-but-unused temperature. It is not a physical
> sign-boundary response.

> **Frozen passive-result correction:** The separately locked same-package
> diagnostic was executed after exact-digest review. All 77 admitted files (16
> calibration, 61 confirmation) passed QC, but the primary association was
> `T=0.013066368743938832<0.10` with one-sided conditional bus-bundle QAP
> `p=0.39696` and 99% Clopper-Pearson Monte Carlo interval for the
> permutation-tail probability
> `[0.39296862162223856,0.4009491374352013]` (99,999 draws, no extension).
> The conditional random-label null was not rejected, the minimum-effect
> threshold was unmet, and leave-one/lateral sign stability failed. This
> supplies no support for the auxiliary passive locality diagnostic, but does
> not prove exact absence and neither validates nor falsifies CGT/CWT. It is not
> active-loop, ridge, topology, noise, physical/field, independent-replication,
> population, or generalization evidence. See the frozen
> [confirmation report](../../../experiments/oedi_ieee123_reconstruction/artifacts/prospective_confirmation/REPORT.md),
> [aborted-no-result ledger](../../../experiments/oedi_ieee123_reconstruction/artifacts/execution_incidents/attempt_001_aborted_no_result.json)
> (`SHA-256 ba58eb84f715ebf50cb2935dc6ba616c5c0a4a8f169f774a3b9c35d80b6cbd28`),
> and [authorized recovery ledger](../../../experiments/oedi_ieee123_reconstruction/artifacts/execution_incidents/attempt_002_completed_protocol_decision.json)
> (`SHA-256 080a357e9ff2657f7486e7e08e4ea409bf5d3463606c72bd6e334fd16aff3cc8`).
> No post-hoc OEDI rescue analysis is authorized by this result.

> Upstream describes an IEEE123 test/example co-simulation system. The correct
> label is **profiles packaged with an external public test-system dataset;
> measurement provenance unspecified**. Field-observation provenance is not
> established, so the old unqualified "real data" label is unsupported. This
> report supplies no support for CGT, active loop response, passive ridge
> co-location, topology, causal/physical locality, or external generalization.
> The original text is retained below only as a superseded historical artifact.

# Historical first-contact text (superseded)

## What was ingested successfully
- OEDI IEEE123 repository files:
  - `sensors.json`
  - `qsts/master.dss`
  - `qsts/Buscoords.dss`
  - load profiles: S1a, S19a, S47, S49a, S65a
  - PV profile: 49
  - temperature series

## Quantitative results
- Graph nodes: **214**
- Graph edges: **126**
- Sensor-covered nodes: **85**
- Mean hops to nearest sensor: **0.415**
- Median hops to nearest sensor: **0.000**
- Max hops to nearest sensor: **2**
- Mean degree, sensor nodes: **1.671**
- Mean degree, non-sensor nodes: **0.853**
- Mean betweenness, sensor nodes: **0.005595**
- Mean betweenness, non-sensor nodes: **0.005207**
- Pairwise load-shape distance/correlation Spearman: **-0.309**
- Pairwise load-shape distance/correlation Pearson: **-0.353**
- Bus 49a daylight PV/load sign-boundary alpha: **1.157**

## Interpretation
### What appears to survive contact
1. **Graph-local observability structure**  
   Sensors are dense enough that the mean node is only about 0.42 hops from a sensor, and no node in the parsed graph is more than 2 hops away.
2. **Structural targeting of measurements**  
   Sensor nodes have a noticeably higher mean degree than non-sensor nodes (1.67 vs 0.85), which is consistent with the theory's emphasis on structurally informative nodes.
3. **A real external sign-boundary phenomenon**  
   For bus 49a, scaling the real PV profile against the real load profile yields a daylight sign crossing at alpha ≈ 1.16, giving a real-data analog of the theory's sign-boundary idea.

### What does **not** yet survive strongly enough
1. **A clean locality law from load-shape similarity**  
   Across the small ingested set of real OEDI load profiles, distance-similarity decay is weak (-0.31 Spearman). That is too weak to claim a robust external locality law from this slice alone.
2. **Loop-response and noisy sign-correction layers**  
   This OEDI slice does not provide the kind of externally driven control-loop observations needed to test the theory's loop-side noisy correction machinery.

## Bottom line
This first real-data contact is **partially supportive**:
- the theory's **structural / topological / sign-boundary** intuitions survive,
- but the stronger **loop-response** claims remain untested here,
- and even the simpler **distance-to-similarity** story is only weakly supported in this first slice.
