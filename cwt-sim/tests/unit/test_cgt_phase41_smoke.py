"""Smoke tests for CGT Phase 41 / Pooled Positive Noisy Scaffold result artifact and analysis module.

Covers:
- Existence and JSON-validity of the benchmark_scaffold_family Phase 41 artifact.
- Importability of the phase41_analysis module.
- Structural integrity of the Phase 41 artifact (including switch_metrics).
- Execution of run_phase41_analysis() to verify the function produces correct output.
- Pooled rule provenance check: Phase 41 pooled coefficients must differ from Phase 39
  single-benchmark coefficients, proving that pooling C+G train rows changed the fit.

Phase 41 lives in the benchmark_scaffold_family/ results directory because it derives a
single pooled rule from benchmarks C and G rather than belonging to either benchmark alone.
"""

from __future__ import annotations

import importlib
import json
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_RESULTS_DIR = (
    Path(__file__).resolve().parents[2]
    / "cgt_benchmarks"
    / "results"
    / "benchmark_C_ring"
)

_SCAFFOLD_FAMILY_DIR = _RESULTS_DIR.parent / "benchmark_scaffold_family"
_PHASE41_ARTIFACT = _SCAFFOLD_FAMILY_DIR / "benchmark_scaffold_phase41_pooled_positive_noisy.json"

# project_root is the cwt-sim/ directory (where cgt_benchmarks/ lives)
_PROJECT_ROOT = Path(__file__).resolve().parents[2]


# ---------------------------------------------------------------------------
# a) Artifact existence and JSON validity
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_phase41_artifact_exists() -> None:
    """The Phase 41 benchmark_scaffold_family artifact must exist and parse as JSON."""
    path = _PHASE41_ARTIFACT
    assert path.exists(), f"Missing: {path}"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert "switch_metrics" in data, (
        f"Expected 'switch_metrics' key in Phase 41 artifact, "
        f"found keys: {sorted(data.keys())}"
    )
    assert "verdict" in data, (
        f"Expected 'verdict' key in Phase 41 artifact, "
        f"found keys: {sorted(data.keys())}"
    )
    assert data["verdict"] == "pooled_positive_noisy_scaffold_supported", (
        f"Unexpected verdict value: {data['verdict']!r}"
    )


# ---------------------------------------------------------------------------
# b) Module importability
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_phase41_importable() -> None:
    """The phase41_analysis module must be importable and expose required callables."""
    mod = importlib.import_module("cwt.cgt.analysis.phase41_analysis")
    assert hasattr(mod, "run_phase41_analysis"), (
        "phase41_analysis module is missing 'run_phase41_analysis'"
    )
    assert hasattr(mod, "Phase41Config"), (
        "phase41_analysis module is missing 'Phase41Config'"
    )


# ---------------------------------------------------------------------------
# c) Artifact structural integrity
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_phase41_artifact_structure() -> None:
    """The Phase 41 artifact must contain required switch_metrics keys with passing thresholds."""
    path = _PHASE41_ARTIFACT
    assert path.exists(), f"Phase 41 artifact not found: {path}"

    data = json.loads(path.read_text(encoding="utf-8"))
    sm = data["switch_metrics"]
    assert isinstance(sm, dict), (
        f"Expected switch_metrics to be a dict, got {type(sm).__name__}"
    )

    required_keys = (
        "benchmark_c_heldout_combined_r2",
        "benchmark_g_heldout_combined_r2",
        "pooled_heldout_combined_r2",
        "pooled_heldout_new_r2",
    )
    for key in required_keys:
        assert key in sm, f"Missing switch_metrics.{key}"

    assert sm["benchmark_c_heldout_combined_r2"] >= 0.90, (
        f"switch_metrics.benchmark_c_heldout_combined_r2 expected >= 0.90, "
        f"got {sm['benchmark_c_heldout_combined_r2']}"
    )
    assert sm["benchmark_g_heldout_combined_r2"] >= 0.90, (
        f"switch_metrics.benchmark_g_heldout_combined_r2 expected >= 0.90, "
        f"got {sm['benchmark_g_heldout_combined_r2']}"
    )
    assert sm["pooled_heldout_combined_r2"] >= 0.93, (
        f"switch_metrics.pooled_heldout_combined_r2 expected >= 0.93, "
        f"got {sm['pooled_heldout_combined_r2']}"
    )


# ---------------------------------------------------------------------------
# d) run_phase41_analysis() actually executes and produces correct output
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_phase41_analysis_runs(tmp_path: Path) -> None:
    """run_phase41_analysis must execute without error and return a conforming payload."""
    from cwt.cgt.analysis.phase41_analysis import run_phase41_analysis

    payload = run_phase41_analysis(project_root=_PROJECT_ROOT, output_root=tmp_path)

    assert isinstance(payload, dict), "run_phase41_analysis must return a dict"
    assert "switch_metrics" in payload, (
        f"Payload missing 'switch_metrics'; keys: {sorted(payload.keys())}"
    )

    sm = payload["switch_metrics"]
    assert sm["benchmark_c_heldout_combined_r2"] >= 0.90, (
        f"switch_metrics.benchmark_c_heldout_combined_r2 expected >= 0.90, "
        f"got {sm['benchmark_c_heldout_combined_r2']}"
    )
    assert sm["benchmark_g_heldout_combined_r2"] >= 0.90, (
        f"switch_metrics.benchmark_g_heldout_combined_r2 expected >= 0.90, "
        f"got {sm['benchmark_g_heldout_combined_r2']}"
    )
    assert sm["pooled_heldout_combined_r2"] >= 0.93, (
        f"switch_metrics.pooled_heldout_combined_r2 expected >= 0.93, "
        f"got {sm['pooled_heldout_combined_r2']}"
    )
    assert payload["verdict"] == "pooled_positive_noisy_scaffold_supported", (
        f"Expected verdict 'pooled_positive_noisy_scaffold_supported', "
        f"got {payload['verdict']!r}"
    )


# ---------------------------------------------------------------------------
# e) Pooled rule provenance check
# ---------------------------------------------------------------------------

_PHASE39_ARTIFACT = _RESULTS_DIR / "benchmark_c_phase39_local_superoperator_compactness_normalizer.json"


@pytest.mark.unit
def test_phase41_pooled_coefficients_differ_from_phase39(tmp_path: Path) -> None:
    """Phase 41 pooled rule coefficients must differ from Phase 39 single-benchmark coefficients.

    This proves that pooling benchmark C and G train rows actually changed the fitted
    coefficients compared to using benchmark C alone (the Phase 39 source). If the
    coefficients were identical it would indicate the pooling had no effect, which
    would contradict the design intent of Phase 41.
    """
    from cwt.cgt.analysis.phase41_analysis import run_phase41_analysis

    # Load Phase 39 single-benchmark coefficients indexed by dephasing level
    assert _PHASE39_ARTIFACT.exists(), f"Phase 39 source artifact missing: {_PHASE39_ARTIFACT}"
    phase39_data = json.loads(_PHASE39_ARTIFACT.read_text(encoding="utf-8"))

    phase39_rules: dict[float, dict] = {}
    for level in phase39_data["levels"]:
        gamma = float(level["dephasing"])
        phase39_rules[gamma] = level["local_superoperator_compactness_normalizer"]

    # Run Phase 41 analysis to obtain the fresh pooled payload
    payload = run_phase41_analysis(project_root=_PROJECT_ROOT, output_root=tmp_path)

    # For the switch level, compare the pooled_positive_noisy_scaffold_rule coefficients
    # against the Phase 39 single-benchmark rule at the same dephasing value.
    switch_level = payload["switch_level"]
    gamma = float(switch_level["dephasing"])

    assert gamma in phase39_rules, (
        f"Phase 41 switch level uses dephasing={gamma} but Phase 39 has no matching level; "
        f"available: {sorted(phase39_rules)}"
    )

    p39_rule = phase39_rules[gamma]
    p41_rule = switch_level["pooled_positive_noisy_scaffold_rule"]

    p39_coeff = p39_rule["coefficients"]
    p41_coeff = p41_rule["coefficients"]

    # At least one coefficient must differ — pooling changed the fit
    any_differ = any(
        p41_coeff.get(k) != p39_coeff.get(k)
        for k in set(p39_coeff) | set(p41_coeff)
    )
    assert any_differ, (
        f"At dephasing={gamma}: Phase 41 pooled coefficients are identical to Phase 39 "
        f"single-benchmark coefficients. Pooling C+G train rows should have changed the fit.\n"
        f"  Phase 39: {p39_coeff}\n"
        f"  Phase 41: {p41_coeff}"
    )
