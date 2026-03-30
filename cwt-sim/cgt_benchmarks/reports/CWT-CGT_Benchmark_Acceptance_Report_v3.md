# CWT-CGT Benchmark Acceptance Report v3

## Coherent benchmark block

### benchmark_a

- regime summary: {'R1': 81}
- trusted pairs: 4
- sign-flip fraction: 0.000000
- verdict: PASS (null benchmark remains null-like)

### benchmark_b

- regime summary: {'R1': 81}
- trusted pairs: 4
- sign-flip fraction: 0.000000
- verdict: PASS (null benchmark remains null-like)

### benchmark_c

- regime summary: {'R1': 81}
- trusted pairs: 12
- sign-flip fraction: 1.000000
- fit response vs signed flux: slope=-0.003916, R²=0.822424
- verdict: PASS (positive coherent benchmark)

### benchmark_d

- regime summary: {'R1': 76, 'R3': 5}
- trusted pairs: 4
- sign-flip fraction: 0.000000
- verdict: PASS (near-null random-walk control)

## R4 / hysteresis benchmark block

### benchmark_f

- regime summary: {'R1': 40, 'R3': 6, 'R4': 35}
- switch tiles: 35
- ambiguous tiles: 35
- trusted pairs: 4
- excluded pairs: 5
- verdict: PASS (explicit branch-switching / exclusion benchmark)

## Noisy benchmark block

### benchmark_c noisy lane

- recommended switch dephasing: 0.30
- baseline mean coherence ratio: 0.920153
- switch-point mean coherence ratio: 0.430067
- verdict: PASS as an operational mixed-state lane, with patchwise loop fits preferred over a global fit.

## Auxiliary topology block

### benchmark_e

- representative lower-band Chern numbers: m=-1 -> -1, m=1 -> 1
- perturbed values remain nontrivial while the gap stays open.
- verdict: PASS as the legitimate periodic/gapped topology sector.

## Overall interpretation

The project now has:

1. a coherent passive benchmark suite,
2. an explicit R4 / branch-jump lane,
3. an operational noisy/CPTP lane,
4. a legitimate auxiliary topology lane.

The remaining open frontier is not more benchmark coverage. It is a deeper derivation of the noisy lane and a tighter connection between the auxiliary topology sector and graph-derived operators.
