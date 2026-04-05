# PRD: CWT-CGT Phases 43–48 Integration

## Motivation

The project-facelift directories (5.4, 5.5, 5.6) contain six new benchmark analysis phases that extend the positive noisy scaffold validation framework. These phases must be integrated into cwt-sim following the established Phase 42 pattern. Each version builds monotonically on the previous.

## Deliverables by Version

### v5.4 — Phases 43–44 (Non-Ring Transfer + Stress Test)

**Phase 43**: Benchmark I (five-node skew ladder, non-ring geometry). Transfers the Phase 41 pooled rule to a non-ring scaffold without refit.
- Analysis module: `phase43_analysis.py` → `cwt-sim/cwt/cgt/analysis/phase43_analysis.py`
- Runner script: `run_phase43_analysis.py` → `cwt-sim/scripts/cgt/run_phase43_analysis.py`
- Artifact (generated): `benchmark_i_phase43_nonring_positive_noisy.json` → `cwt-sim/cgt_benchmarks/results/benchmark_I_nonring_ladder/`
- Verdict: `nonring_positive_noisy_scaffold_supported`

**Phase 44**: Stronger perturbation family on benchmark I under same pooled rule.
- Analysis module: `phase44_analysis.py` → `cwt-sim/cwt/cgt/analysis/phase44_analysis.py`
- Runner script: `run_phase44_analysis.py` → `cwt-sim/scripts/cgt/run_phase44_analysis.py`
- Artifact: `benchmark_i_phase44_stronger_perturbation_family.json` → `cwt-sim/cgt_benchmarks/results/benchmark_I_nonring_ladder/`
- Adds `heldout_strong` family (stronger perturbation shapes)

**Reports** (5 files → `cwt-sim/cgt_benchmarks/reports/`):
- CWT-CGT_Phase_43_Nonring_Positive_Noisy_Scaffold.md
- CWT-CGT_Phase_44_Report.md
- CWT-CGT_Phase_44_Stronger_Perturbation_Family.md
- CWT-CGT_Benchmark_Acceptance_Report_v37.md
- CWT-CGT_Theory_Hardened_v42.md
- CWT-CGT_Current_Theory_Status_v42.md
- CWT-CGT_Theory_Implementation_Alignment_v33.md

**Smoke tests**: 2 tests (phase43 R² > 0.95/0.97, phase44 strong R² > 0.88, combined > 0.93)

### v5.5 — Phases 45–46 (Broader Pooled Rule + Stress Revalidation)

**Phase 45**: Pools train rows from four benchmarks (C, G, H, I) into one broader rule. Re-evaluates held-out families on all four benchmarks.
- Analysis module: `phase45_analysis.py` → `cwt-sim/cwt/cgt/analysis/phase45_analysis.py`
- Runner script: `run_phase45_analysis.py` → `cwt-sim/scripts/cgt/run_phase45_analysis.py`
- Artifact: `benchmark_scaffold_phase45_pooled_four_positive_noisy.json` → `cwt-sim/cgt_benchmarks/results/benchmark_scaffold_family/`
- Depends on: Phase 39 (C), Phase 40 (G), Phase 42 (H), Phase 43 (I) artifacts
- Verdict: `pooled_four_positive_noisy_supported`

**Phase 46**: Reruns stronger perturbation family on benchmark I under the broader Phase 45 pooled rule.
- Analysis module: `phase46_analysis.py` → `cwt-sim/cwt/cgt/analysis/phase46_analysis.py`
- Runner script: `run_phase46_analysis.py` → `cwt-sim/scripts/cgt/run_phase46_analysis.py`
- Artifact: `benchmark_i_phase46_pooled_four_stronger_perturbation.json` → `cwt-sim/cgt_benchmarks/results/benchmark_I_nonring_ladder/`
- Depends on: Phase 45 pooled rule + Phase 44 stronger perturbation data
- Imports from phase45_analysis: `_summary`, `_predict_row`

**Reports** (6 files → `cwt-sim/cgt_benchmarks/reports/`):
- CWT-CGT_Phase_45_Pooled_Four_Positive_Noisy_Scaffold.md
- CWT-CGT_Phase_45_Report.md
- CWT-CGT_Phase_46_Broadened_Pooled_Stronger_Family.md
- CWT-CGT_Phase_46_Report.md
- CWT-CGT_Benchmark_Acceptance_Report_v38.md
- CWT-CGT_Theory_Hardened_v43.md

**Smoke tests**: 2 tests (phase45 pooled R² > 0.97, phase46 strong R² > 0.92)

### v5.6 — Phases 47–48 (Fifth Benchmark + Harder Stress)

**Phase 47**: Benchmark J (bowtie-chain, non-ring). Transfers Phase 45 pooled four-positive rule unchanged.
- Analysis module: `phase47_analysis.py` → `cwt-sim/cwt/cgt/analysis/phase47_analysis.py`
- Runner script: `run_phase47_analysis.py` → `cwt-sim/scripts/cgt/run_phase47_analysis.py`
- Artifact: `benchmark_j_phase47_fifth_positive_noisy.json` → `cwt-sim/cgt_benchmarks/results/benchmark_J_bowtie_chain/`
- Depends on: Phase 45 pooled rule
- Verdict: `fifth_positive_noisy_scaffold_supported`

**Phase 48**: Harder perturbation family on benchmark J. Adds crescent/chevron/hourglass shapes.
- Analysis module: `phase48_analysis.py` → `cwt-sim/cwt/cgt/analysis/phase48_analysis.py`
- Runner script: `run_phase48_analysis.py` → `cwt-sim/scripts/cgt/run_phase48_analysis.py`
- Artifact: `benchmark_j_phase48_harder_perturbation_family.json` → `cwt-sim/cgt_benchmarks/results/benchmark_J_bowtie_chain/`
- Depends on: Phase 45 pooled rule
- Imports from phase45_analysis: `_summary`, `_predict_row`
- Imports from phase47_analysis: shape data
- Verdict: `fifth_benchmark_stronger_family_supported`

**Reports** (7 files → `cwt-sim/cgt_benchmarks/reports/`):
- CWT-CGT_Phase_47_Fifth_Positive_Noisy_Scaffold.md
- CWT-CGT_Phase_47_Report.md
- CWT-CGT_Phase_48_Harder_Perturbation_Family.md
- CWT-CGT_Phase_48_Report.md
- CWT-CGT_Benchmark_Acceptance_Report_v39.md
- CWT-CGT_Current_Theory_Status_v44.md
- CWT-CGT_Theory_Hardened_v44.md
- CWT-CGT_Post_Step_48_Next_Steps.md

**Smoke tests**: 4 tests (phase45-48, thresholds per version)

## Adaptation Rules (Apply to All Phases)

All analysis modules require the same adaptations as Phase 42:

1. **Imports**: Add `from cwt.cgt.analysis._utils import nan_to_none, safe_float, safe_pow`
2. **Paths**: Replace `03_benchmarks/` → `cgt_benchmarks/`, `05_reports/` → `cgt_benchmarks/reports/`
3. **Cross-module imports**: Fix `cwt_cgt.phaseNN` → `cwt.cgt.analysis.phaseNN`
4. **JSON safety**: Wrap output payloads with `nan_to_none()`
5. **Main block**: Add `if __name__ == '__main__':` matching phase41 pattern (parents[3])
6. **Runner scripts**: Match run_phase41_analysis.py pattern (parents[2], no argparse)
7. **Test files**: Follow test_cgt_phase42_smoke.py pattern (@pytest.mark.unit, path constants, detailed assertions)
8. **Red team fixes**: Apply KeyError guards for source artifact keys, document trusted_pair filter decisions

## Dependency Graph

```
Phase 41 pooled rule (existing)
  ├── Phase 43 (benchmark I transfer)
  │     └── Phase 44 (stronger perturbation on I)
  │
  Phase 39(C) + 40(G) + 42(H) + 43(I) artifacts
  └── Phase 45 (four-benchmark pooled rule)
        ├── Phase 46 (stronger perturbation under broader rule)
        ├── Phase 47 (benchmark J transfer)
        │     └── Phase 48 (harder perturbation on J)
        └── (Phase 46 also uses Phase 44 data)
```

## Implementation Order

1. v5.4: Phases 43, 44 (must complete before v5.5 since Phase 45 reads Phase 43 artifact)
2. v5.5: Phases 45, 46 (must complete before v5.6 since Phases 47-48 read Phase 45 artifact)
3. v5.6: Phases 47, 48

## Armature Workflow per Version

1. Orchestrator delegates to cwt-core-impl
2. cwt-core-impl implements all modules, scripts, artifacts, reports, tests
3. Reviewer checks invariant compliance
4. Red team reviewer hunts for subtle bugs
5. cwt-core-impl fixes findings
6. Orchestrator commits after final PASS

## Invariants

- GEOM-001: Analysis modules must not import from layers/, orchestrator/, experiments/, baselines/
- No existing files should be modified (all new additions)
