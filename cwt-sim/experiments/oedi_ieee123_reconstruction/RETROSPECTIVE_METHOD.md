# OEDI IEEE123 retrospective reconstruction method

## Status and exclusion boundary

This is a provenance-locked **retrospective reconstruction** of the numbers
archived in `CWT-CGT_External_First_Contact_OEDI_Metrics.json`. It was designed
after those numbers were known. It is not a preregistration, untouched
holdout, independent dataset, field-observation study, theory validation, or
prospective confirmation.

The upstream project describes an IEEE123 sample/example co-simulation
system. Its profiles are therefore labeled **profiles packaged with an external
public test-system dataset; measurement provenance unspecified**, not
evidence of field observations and not a basis for an unqualified "real data"
label. The source
is fixed to `openEDI/oedisi-ieee123` commit
`7c8bcca06708ea2dd54b822821d637814ef08dc4`; every executed source file is
checked against `UPSTREAM_MANIFEST.json` before analysis.

Prospective passive analysis is deliberately separate. This retrospective
runner never numerically parses any nonlegacy load-profile values or computes
an outcome statistic from them. The separate metadata-only preparation may
hash their bytes and count physical rows before freeze.

## Historical parser reproduced exactly

The historical reconstruction:

1. seeds the graph with all 212 non-comment unique labels in
   `qsts/Buscoords.dss` (82 `s*` device/plot labels and 130 physical labels),
   then allows the two Line endpoints `300_OPEN` and `94_OPEN` to bring the
   graph total to 214 nodes;
2. treats every `New Line.*` statement in `qsts/master.dss` as an undirected
   edge, including normally-open `Sw7` and `Sw8`;
3. strips phase suffixes from line endpoints and `sensors.json` entries;
4. omits transformer and redirected-regulator connectivity;
5. computes finite sensor distances only for nodes reachable from any sensor;
6. averages non-sensor centrality over every remaining Buscoords label,
   including isolates;
7. uses only load shapes `S1a`, `S19a`, `S47`, `S49a`, and `S65a` from the
   population of 91 declared loads;
8. computes ten pairwise shape correlations and correlates them with graph
   distance, even though those ten pairs reuse only five profiles; and
9. defines the Bus-49 alpha diagnostic as
   `mean(loadshape_S49a[pvshape_49 >= 0.2]) /
   mean(pvshape_49[pvshape_49 >= 0.2])`.

The last quantity is a dimensionless ratio chosen to zero its own mean
difference. It is tautological, ignores the 35 kW Load.S49a rating, the 50
kVA/Pmpp PVSystem.49 rating, and the temperature model, and is not a measured
response or physical net-power balance.

## Corrected diagnostics kept separate

The corrected physical graph:

- excludes `s*` plot/device labels from Buscoords nodes;
- excludes the `*_OPEN` pseudo-buses and normally-open `Sw7`/`Sw8` edges;
- retains closed line/switch edges;
- adds the inline `150-150r` source regulator and `61s-610` load transformer;
- adds redirected regulator connectivity `9-9r`, `25-25r`, and `160-160r`;
- collapses phase-parallel transformer connections in the unweighted graph;
- derives every selected load's base bus, phase count, connection, rating, and
  yearly shape from `IEEE123LoadsQsts.dss`, never from an ID suffix.

The report shows both the legacy active-only induced subgraph and this
corrected graph. It never substitutes either diagnostic into the archived
historical vector silently.

## Deterministic decision

The reconstruction passes only when all selected hashes and the Git source
revision match, every archived scalar/pairwise result is reproduced within
declared numerical tolerance, the 84-isolate/130-reachable defect is exposed,
the active-only sensor/non-sensor centrality reversal is reproduced, all 91
load definitions and the post-hoc five-profile selection are disclosed, and
the alpha diagnostic is labeled dimensionless, rating-ignorant, temperature-
unused, and tautological.

Passing means only that the archived vector has been reconstructed and its
interpretation corrected. It provides no support for CGT, active response,
passive ridge co-location, topology, causal/physical locality, or external
generalization.
