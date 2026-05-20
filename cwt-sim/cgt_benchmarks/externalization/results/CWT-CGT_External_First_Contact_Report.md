# External first-contact test: OEDI IEEE123 + source ingestion status

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
