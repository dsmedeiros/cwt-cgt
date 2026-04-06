# PRD: CWT-CGT Phases 49–59 Integration

## Motivation

Project-facelift directories 5.8, 5.9, 6.0, 6.1 contain 11 new phases (49–59) extending the positive noisy scaffold validation to two new benchmarks (K hub-weave, L fork-mesh), upgrading from a pooled-five to a pooled-seven scaffold rule, and introducing adversarial-family / sign-correction patterns.

## Key Structural Difference From Prior Phases

Phases 49–59 are **pure JSON loader stubs**. Unlike phases 42–48 which contained synthetic row generators (`_generate_rows_for_gamma`, `_predict_row`, `_compute_phase41_channels`), these phases simply read pre-computed JSON artifacts and return their payloads. This dramatically simplifies the integration:

- **No `_generate_rows_for_gamma`** — data is pre-baked in JSON
- **No `_compute_phase41_channels`** — feature engineering already done
- **No `_fit_rule` / lstsq calls** — coefficients already in source artifacts
- **No matplotlib plot generation** — these are validation loaders only

## Adaptation Rules

Apply the same conventions established in phases 42–48:

1. **Function signature**: All modules export `run_phaseNN_analysis(project_root: Path, output_root: Path | None = None) -> dict` for consistency, even though `output_root` is unused. (Source v6.0+ uses `load_payload()` — normalize to the established `run_phaseNN_analysis` name to match the rest of the codebase.)
2. **Paths**: Replace `03_benchmarks/` → `cgt_benchmarks/` in any path constants
3. **JSON safety**: Wrap returned payloads with `nan_to_none()` from `cwt.cgt.analysis._utils`
4. **Module docstring**: Brief description of what the phase loads and what it validates
5. **KeyError guards**: Source artifact key access guarded with descriptive `ValueError`
6. **`if __name__ == '__main__':`** block at bottom (parents[3] for project_root)
7. **Runner scripts** (where source provides them): Match `run_phase42_analysis.py` pattern (parents[2], `nan_to_none`, no argparse). For phases 49–50 (no source runner), create them anyway for consistency.
8. **Smoke tests**: Follow `test_cgt_phase42_smoke.py` pattern with `@pytest.mark.unit`

## Deliverables by Version

### v5.8 — Phases 49–52 (Pooled-Five + Benchmark K Hub-Weave)

**Phases 49–50**: Pooled-five positive-noisy scaffold rule (extends Phase 45's pooled-four) and pooled-five harder family. Benchmark slug: `benchmark_scaffold_family`.

**Phases 51–52**: Benchmark K (hub-weave, new topology). Sixth positive noisy scaffold + extreme perturbation family. Benchmark slug: `benchmark_K_hub_weave`.

**New artifacts** → `cwt-sim/cgt_benchmarks/results/`:
- `benchmark_scaffold_family/benchmark_scaffold_phase49_pooled_five_positive_noisy.json`
- `benchmark_scaffold_family/benchmark_scaffold_phase50_pooled_five_harder_family.json`
- `benchmark_I_nonring_ladder/benchmark_i_phase50_pooled_five_stronger_perturbation.json`
- `benchmark_J_bowtie_chain/benchmark_j_phase50_pooled_five_harder_perturbation.json`
- `benchmark_K_hub_weave/benchmark_k_phase51_sixth_positive_noisy.json`
- `benchmark_K_hub_weave/benchmark_k_phase52_extreme_perturbation_family.json`

**Code** → `cwt-sim/cwt/cgt/analysis/`:
- phase49_analysis.py, phase50_analysis.py, phase51_analysis.py, phase52_analysis.py

**Runners** → `cwt-sim/scripts/cgt/`:
- run_phase49_analysis.py, run_phase50_analysis.py (NEW — not in source), run_phase51_analysis.py, run_phase52_analysis.py

**Reports** (8 → `cwt-sim/cgt_benchmarks/reports/`):
- CWT-CGT_Phase_51_Report.md, CWT-CGT_Phase_51_Sixth_Positive_Noisy_Scaffold.md
- CWT-CGT_Phase_52_Report.md, CWT-CGT_Phase_52_Extreme_Perturbation_Family.md
- CWT-CGT_Benchmark_Acceptance_Report_v41.md
- CWT-CGT_Current_Theory_Status_v46.md
- CWT-CGT_Theory_Hardened_v46.md
- CWT-CGT_Theory_Implementation_Alignment_v37.md

**Smoke tests** → `cwt-sim/tests/unit/test_cgt_phase49_52_smoke.py`:
- phase49: pooled_scaffold R² > 0.98, benchmark_j R² > 0.98
- phase50: pooled_harder_family R² > 0.95
- phase51: heldout_new R² > 0.95, heldout_combined R² > 0.96
- phase52: heldout_extreme R² > 0.90, heldout_combined R² > 0.92

### v5.9 — Phases 53–54 (Benchmark L Fork-Mesh + Adversarial Sign Break)

**Phase 53**: Benchmark L (fork-mesh, NEW topology). Seventh positive noisy scaffold under existing pooled-five rule.

**Phase 54**: Adversarial sign break on L. Tests sign agreement breakdown at adversarial boundary (NEW: introduces `sign_agreement` metric assertions).

**New artifacts** → `cwt-sim/cgt_benchmarks/results/benchmark_L_fork_mesh/`:
- `benchmark_l_phase53_seventh_positive_noisy.json`
- `benchmark_l_phase54_adversarial_sign_break.json`

**Code** → `cwt-sim/cwt/cgt/analysis/`: phase53_analysis.py, phase54_analysis.py
**Runners** → `cwt-sim/scripts/cgt/`: run_phase53_analysis.py, run_phase54_analysis.py

**Reports** (5 → `cwt-sim/cgt_benchmarks/reports/`):
- CWT-CGT_Phase_53_Report.md, CWT-CGT_Phase_54_Report.md
- CWT-CGT_Benchmark_Acceptance_Report_v42.md (5.9 version)
- CWT-CGT_Current_Theory_Status_v47.md
- CWT-CGT_Theory_Hardened_v47.md

**Smoke tests** → `cwt-sim/tests/unit/test_cgt_phase53_54_smoke.py`:
- phase53: heldout_new R² > 0.95, heldout_combined R² > 0.96
- phase54: heldout_adversarial sign_agreement < 0.9, heldout_combined sign_agreement < 0.95

### v6.0 — Phases 55–57 (Pooled-Seven + Generator Sign Correction)

**Phase 55**: Pooled-seven positive-noisy scaffold rule (upgrade from pooled-five). Slug: `benchmark_scaffold_family`.

**Phase 56**: Benchmark L under pooled-seven rule with adversarial family — partial failure expected (combined R² < 0.5).

**Phase 57**: Generator-side sign-robustness correction applied to phase 56 rows. Improvement assertion: phase57 metrics > phase56 metrics.

**New artifacts**:
- `cwt-sim/cgt_benchmarks/results/benchmark_scaffold_family/benchmark_scaffold_phase55_pooled_seven_positive_noisy.json`
- `cwt-sim/cgt_benchmarks/results/benchmark_L_fork_mesh/benchmark_l_phase56_pooled_seven_adversarial.json`
- `cwt-sim/cgt_benchmarks/results/benchmark_L_fork_mesh/benchmark_l_phase57_generator_sign_robustness_correction.json`

**Code** → `cwt-sim/cwt/cgt/analysis/`: phase55_analysis.py, phase56_analysis.py, phase57_analysis.py
**Runners**: run_phase55_analysis.py, run_phase56_analysis.py, run_phase57_analysis.py

**Reports** (7 → `cwt-sim/cgt_benchmarks/reports/`):
- CWT-CGT_Phase_55_Report.md, CWT-CGT_Phase_56_Report.md, CWT-CGT_Phase_57_Report.md
- CWT-CGT_Benchmark_Acceptance_Report_v42.md (6.0 version, OVERWRITES 5.9 version)
- CWT-CGT_Current_Theory_Status_v48.md
- CWT-CGT_Theory_Hardened_v48.md
- CWT-CGT_Theory_Implementation_Alignment_v36.md
- CWT-CGT_Post_Step_57_Next_Steps.md

**Smoke tests** → `cwt-sim/tests/unit/test_cgt_phase55_57_smoke.py`:
- phase55: pooled_positive_rule heldout_combined_r2 > 0.98
- phase56: combined_r2 < 0.5, combined_sign_agreement < 0.95
- phase57: r2 > phase56 r2, sign_agreement > phase56 sign_agreement

### v6.1 — Phases 58–59 (Second Adversarial + Transfer)

**Phase 58**: Second adversarial family on benchmark I (non-ring ladder). Tests pooled-seven rule against second adversarial topology.

**Phase 59**: Transferred generator sign correction. Demonstrates the phase 57 fix generalizes to benchmark I.

**New artifacts** → `cwt-sim/cgt_benchmarks/results/benchmark_I_nonring_ladder/`:
- `benchmark_i_phase58_second_adversarial_family.json`
- `benchmark_i_phase59_generator_sign_correction_transfer.json`

**Code** → `cwt-sim/cwt/cgt/analysis/`: phase58_analysis.py, phase59_analysis.py
**Runners**: run_phase58_analysis.py, run_phase59_analysis.py

**Reports** (8 → `cwt-sim/cgt_benchmarks/reports/`):
- CWT-CGT_Phase_58_Report.md, CWT-CGT_Phase_58_Second_Adversarial_Family.md
- CWT-CGT_Phase_59_Report.md, CWT-CGT_Phase_59_Generator_Sign_Correction_Transfer.md
- CWT-CGT_Benchmark_Acceptance_Report_v44.md
- CWT-CGT_Current_Theory_Status_v50.md
- CWT-CGT_Theory_Hardened_v50.md
- CWT-CGT_Theory_Implementation_Alignment_v38.md
- CWT-CGT_Post_Step_59_Next_Steps.md

**Smoke tests** → `cwt-sim/tests/unit/test_cgt_phase58_59_smoke.py`:
- phase58: combined_metrics r2 > 0.4, adversarial_family_metrics sign_agreement < 0.9
- phase59: combined_metrics r2 > phase58 r2, sign_agreement > phase58 sign_agreement

## New Benchmark Directories

- `cwt-sim/cgt_benchmarks/results/benchmark_K_hub_weave/`
- `cwt-sim/cgt_benchmarks/results/benchmark_L_fork_mesh/`

## Dependency Graph

```
Phase 45 pooled-four (existing)
  └── Phase 49 pooled-five (extends)
        ├── Phase 50 pooled-five harder family
        ├── Phase 51 (benchmark K)
        │     └── Phase 52 (extreme perturbation on K)
        ├── Phase 53 (benchmark L)
        │     └── Phase 54 (adversarial sign break on L)
        └── Phase 55 pooled-SEVEN (further extension)
              ├── Phase 56 (L under pooled-seven adversarial)
              │     └── Phase 57 (generator sign correction on L)
              └── Phase 58 (I under pooled-seven adversarial)
                    └── Phase 59 (sign correction transfer to I)
```

## Implementation Order

1. v5.8: Phases 49–52
2. v5.9: Phases 53–54
3. v6.0: Phases 55–57 (overwrites v42 acceptance report)
4. v6.1: Phases 58–59

## Armature Workflow

Per version:
1. Orchestrator delegates to cwt-core-impl
2. cwt-core-impl creates loader modules, runners, artifacts, reports, tests
3. Reviewer checks invariant compliance
4. Red team adversarial review
5. Fixes if needed
6. Commit

## Constraints

- Do NOT modify any existing files
- All paths must use `cgt_benchmarks/` convention
- Fix stale `03_benchmarks` references in JSON artifacts
- Normalize to `run_phaseNN_analysis` function name
- Add KeyError guards for source artifact key access
- All loader modules return `nan_to_none()`-wrapped payload

## Invariants

- GEOM-001: Analysis modules must not import from layers/, orchestrator/, experiments/, baselines/
- No existing files modified (all new additions)
