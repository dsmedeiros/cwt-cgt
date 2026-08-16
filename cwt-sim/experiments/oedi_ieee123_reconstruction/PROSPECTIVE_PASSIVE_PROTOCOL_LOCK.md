# OEDI IEEE123 passive association protocol lock

## Status, access boundary, and claim ceiling

This is a **prospective-from-freeze-date analysis specification for
retrospective pre-existing profiles**. The confirmation population is
"previously unanalysed in the tracked repository/current workflow and
prospectively specified for this analysis." It is not untouched data,
prospective collection, an independent dataset, a real-feeder observation,
cross-substrate replication, active response evidence, or theory-specific CGT
evidence.

The upstream title is *Sample IEEE123 Bus system for OEDI SI* (DOI
`10.25984/2228282`; <https://data.openei.org/submissions/5773>). We describe the
inputs as **profiles packaged with an external public test-system dataset;
measurement provenance unspecified**.

Before a signed unlock, `prepare` may read and SHA-256 hash bytes, count
nonempty rows without numeric conversion, compare all 91 working profile files
to their canonical pinned Git blob bytes/OIDs, and parse DSS metadata.
`reconstruct` may numerically parse only the five
legacy load profiles and PV49. No nonlegacy profile is numerically parsed and
no nonlegacy outcome statistic is computed before freeze. `confirm` requires
the exact frozen protocol/code/source/split/runtime digest, the independently
approved SHA-256 of detached `FREEZE_LOCK.json`, and explicit root plus
adversarial approval; it has not been executed at protocol publication.

The maximum supportive result is a **prespecified within-OEDI-package
association under a conditional bus-bundle random-label null**, a common
passive-locality diagnostic. It is not evidence for CGT, causality, physical
locality, an active loop response, transition ridges, topology, a population
effect, or generalization beyond this engineered test-system package.

## Pinned source and amendment

- Repository: `https://github.com/openEDI/oedisi-ieee123`
- Commit: `7c8bcca06708ea2dd54b822821d637814ef08dc4`
- Canonical bytes: Git blob bytes from a `core.autocrlf=false` checkout.
- Inventory: 91 LoadShape CSV blobs, 91 LoadShape declarations, and 91 Load
  declarations. Every path, SHA-256, Git blob OID, byte size, identifier,
  mapped bus, connection, phase count, and declared sample count is published
  by metadata-only `prepare`.
- Runtime closure: exact Python, NumPy, SciPy, NetworkX, and Typer versions are
  frozen with the protocol, manifest, `__init__.py`, and every executed module.
- Claim-bearing `REPORT.md`, `ACCESS_PLAN.json`, `records.json`, `summary.json`,
  and `PROVENANCE.json` have an acyclic detached checksum manifest. The freeze
  lock binds their hashes and the canonical prepared payload; its own SHA-256
  must be approved separately.

OpenDSS `!` ends an active statement and `~` continues the preceding active
statement. The first draft assumed every load had an active `yearly` token.
Before any nonlegacy numeric profile parse or outcome calculation, inspection
showed that `S48` and `S49c` place their apparent `yearly` text after `!`.
Versioned amendment: both are `no_explicit_active_yearly_mapping`; neither is
inferred from its identifier. They remain catalogued-but-unanalyzed. This gives
89 active mappings and 81 mapped one-phase Wye loads. `S48` is three-phase and
`S49c` belongs to forced discovery bus 49, so neither is confirmation-eligible.
An unmapped or multiply mapped nonlegacy candidate is indeterminate.

## Physical graph fixed before outcomes

Canonical bus identifiers are the active DSS `Bus1` base with conductor suffix
stripped, whitespace trimmed, case-folded, and no numeric coercion. Load phase,
phase count, and connection are taken only from active DSS fields, never an ID
suffix.

The primary unweighted graph contains active Lines and Transformer windings,
including redirected regulators. Loads, PV systems, sensors, and Buscoords
plot/device labels are not edges. Phase-parallel transformer connections are
collapsed. The pinned primary oracle is 124 Line objects (118 ordinary plus
Sw1--Sw6), eight transformer objects, 132 raw series elements, 130 physical
buses, 129 unique edges, and one tree.

`Sw7 -> 300_OPEN` and `Sw8 -> 94_OPEN` are excluded under this repository's
dataset-specific `*_OPEN` pseudo-terminal convention. This is not a general
OpenDSS rule: both are executable Line statements and no `Open` command exists.
Robustness includes both stubs, giving 132 buses and 131 unique edges. Every
admitted bus must be in the 130-bus graph, none may map to an `_OPEN` terminal,
and the complete admitted-pair distance vector must be exactly identical with
the stubs included or the result is indeterminate.

The topology-lateral robustness root is canonical bus `150`, derived from the
active `Circuit.ieee123 Bus1` property in `qsts/master.dss`. That property must
resolve to `150`, and the root must exist in the primary graph, or the result is
indeterminate.

## Eligibility and frozen clustered split

Confirmation eligibility requires an active one-phase Wye Load with exactly
one explicit active `yearly` token that resolves uniquely through LoadShape to
an existing headerless CSV declared as 35,040 samples at 0.25 hours. The seven
single-phase Delta loads (`S35a`, `S65a`, `S65b`, `S65c`, `S76a`, `S76b`,
`S76c`) and mapped three-phase `S47` are exploratory/ineligible. Unmapped `S48`
and `S49c` are excluded.

Legacy base buses `{1,19,47,49,65}` are wholly discovery-only, including every
sibling and ineligible load. This removes mapped Wye `S1a`, `S19a`, `S49a`, and
`S49b`, leaving 77 fresh mapped-Wye bus clusters with singleton signatures
`A32/B20/C25`.

For each remaining unique physical bus, define signature `(nA,nB,nC)`. Let
`N=77` and `K=ceil(0.20*N)=16`. Allocate K across signatures by deterministic
largest remainder; ties use lexicographic signature text. Within each signature
sort the exact UTF-8 SHA-256 inputs

```text
CWT-OEDI-PASSIVE-V1|7c8bcca06708ea2dd54b822821d637814ef08dc4|BUS|<canonical_base_bus>
```

and assign the lowest hashes to calibration. All loads at a bus inherit one
membership. There are no retries, salt changes, reallocation, or phase drops.
The locked allocation is calibration `A7/B4/C5` (16) and confirmation
`A25/B16/C20` (61). The machine-readable prepare artifact publishes every ID.

Pre-outcome adequacy requires at least 10 confirmation buses, at least 10
eligible profiles in each A/B/C phase, at least three distinct primary graph
distances in each phase, at least 50 valid confirmation profiles, and at least
one calibration bus carrying each phase. Every admitted bus must be connected.
Failure is indeterminate, with no split retry.

## Profile QC and primary estimand

Each admitted file must contain exactly 35,040 finite numeric headerless rows
(365 days times 96 quarter-hours), with no imputation. For each profile and
quarter-hour `q=t mod 96`, subtract that profile's median over all 365 days.
This is full-confirmation-year normalization, not trained or out-of-sample
normalization. Residual variance must be strictly positive.

For same-phase, distinct-bus profile pairs only, define

```text
D_ij = 1 - Pearson(residual_i, residual_j)
T = Spearman(primary_unweighted_graph_distance_ij, D_ij).
```

Pearson and Spearman use finite IEEE-754 doubles and average ranks for ties.
Every admitted calibration and confirmation profile is numerically checked
only after unlock. A single wrong row count, nonfinite value, constant
residual, hash mismatch, inaccessible file, invalid/multiple mapping, or other
QC failure is indeterminate; no admitted profile may be silently dropped.
Undefined coefficients, graph disconnection, or fewer than 50 valid
confirmation profiles are also indeterminate. Pair count is never a sample
size; this is one feeder package and no population confidence interval is
reported. The expected metadata-only pair count is 610
(`A300/B120/C190`).

The threshold `T>=0.10` was selected after the five-profile historical
exploration; it is post hoc to that discovery slice but prospective for the
frozen confirmation membership.

## Conditional bus-bundle QAP

The null exchanges complete bus bundles only among confirmation buses having
the same eligible phase-count signature. It never permutes phases, individual
profiles, pairs, or time cells. Cross-phase sibling dependence therefore stays
inside a bundle. The observed allocation is included once.

The admissible space is the product of factorial signature-group bus counts.
If it is at most 99,999, enumerate unique allocations exactly. Exact
`p = count(T_perm >= T_obs) / allocation_count`; fewer than 20 unique
allocations cannot resolve `p<=0.05` and is indeterminate. The comparator is
exactly `T_perm >= T_obs` with no numerical tolerance.

Otherwise draw 99,999 allocations with `numpy.random.PCG64` and

```text
seed = int.from_bytes(SHA256(b'CWT-OEDI-PASSIVE-V1|QAP')[:16], 'big')
p = (1 + count(T_perm >= T_obs)) / (B + 1).
```

Report a two-sided 99% Clopper-Pearson Monte Carlo interval for the extreme
probability. If it includes 0.05, extend the same RNG stream to 999,999 total
draws; if it still includes 0.05, the result is indeterminate. The pinned space
is `25!*16!*20! =
789568637724233695255040401494127477134458880000000000000`, so Monte Carlo is
expected.

## Non-rescuing robustness and controls

All are fixed before unlock:

1. Raw-profile and first-difference dissimilarity T must both be positive.
2. Apply the full-year residuals to four half-open day blocks
   `[0,91)`, `[91,182)`, `[182,273)`, `[273,365)`; at least three block T values
   must be positive.
3. Leave out each confirmation load in turn; no defined T may be negative.
4. A topology lateral is a source-rooted BFS edge leaving a node of undirected
   degree at least three. Remove each in turn, retain the source component, and
   evaluate only cases still having at least 50 profiles and 10 per phase. At
   least one must be evaluable and none may have negative T.
5. Report A/B/C T descriptively. Any future secondary p-values require Holm
   adjustment; none are silently promoted to primary.
6. Weighted distance is not primary and is unavailable unless one coherent
   comparable scale for Lines, switches, and transformer/regulator elements is
   justified. Phase awareness is already enforced by same-phase pairs.
7. Under the identical bus-bundle permutations, repeat the test using absolute
   numeric bus-ID distance and Buscoords file-order distance. The latter parses
   canonical noncomment whitespace rows, retains only labels present in the
   130-node primary graph, preserves first occurrence, requires exactly 130
   unique physical buses, and uses absolute zero-based ordinal distance. If either reaches
   `T>=0.10` and `p<=0.05`, the primary is indeterminate as an order-artifact
   specificity failure.
8. Deterministically circular-shift each whole profile by a load-ID-hashed
   whole-day count. The exact UTF-8 preimage is
   `CWT-OEDI-PASSIVE-V1|SHIFT|<load_id>`; take SHA-256, interpret the first eight
   digest bytes as an unsigned big-endian integer, and reduce modulo 365. Zero
   means no roll and remains explicitly reported. Report T as a warning
   control; it cannot rescue failure.

## Decision

- **Pass:** source/access/mapping/topology/QC integrity passes; `T>=0.10` and
  one-sided QAP `p<=0.05`; all required sign/stability rules pass; and neither
  order-artifact control triggers.
- **Fail:** integrity is adequate but `T<=0`, `T<0.10`, `p>0.05`, or a required
  non-rescuing sign/stability rule fails.
- **Indeterminate:** source, runtime, detached lock, or frozen digest mismatch;
  access before unlock; any admitted mapping/hash/numeric-QC failure;
  disconnection or undefined statistic; unresolved Monte Carlo
  interval, failed pre-outcome adequacy, order-artifact specificity trigger,
  protocol/code/split change, or any parser disagreement with the pinned
  compiled active statements.

Confirmation output may not be described as CGT validation regardless of the
decision.
