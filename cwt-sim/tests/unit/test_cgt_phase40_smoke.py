"""Smoke tests for CGT Phase 40 / Benchmark G result artifact and analysis module.

Covers:
- Existence and JSON-validity of the benchmark_G_skew_ring Phase 40 artifact.
- Importability of the phase40_analysis module.
- Structural integrity of the Phase 40 artifact (including switch_metrics).
- Execution of run_phase40_analysis() to verify the function produces correct output.
- Coefficient provenance check: Phase 40 must use Phase 39 coefficients without refit.

Phase 40 lives in a separate benchmark directory (benchmark_G_skew_ring/) rather
than benchmark_C_ring/, so it is kept in its own focused test file.
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

_BENCHMARK_G_DIR = _RESULTS_DIR.parent / "benchmark_G_skew_ring"
_PHASE40_ARTIFACT = _BENCHMARK_G_DIR / "benchmark_g_phase40_second_positive_noisy.json"

# ---------------------------------------------------------------------------
# a) Benchmark G artifact existence and JSON validity
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_benchmark_g_artifact_exists() -> None:
    """The Phase 40 benchmark_G_skew_ring artifact must exist and parse as JSON."""
    path = _PHASE40_ARTIFACT
    assert path.exists(), f"Missing: {path}"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert "switch_metrics" in data, (
        f"Expected 'switch_metrics' key in Phase 40 artifact, "
        f"found keys: {sorted(data.keys())}"
    )
    assert "suite_verdicts" in data, (
        f"Expected 'suite_verdicts' key in Phase 40 artifact, "
        f"found keys: {sorted(data.keys())}"
    )
    assert data["suite_verdicts"]["benchmark_g"] == "second_positive_noisy_scaffold_supported", (
        f"Unexpected suite_verdicts.benchmark_g value: "
        f"{data['suite_verdicts'].get('benchmark_g')!r}"
    )


# ---------------------------------------------------------------------------
# b) Phase 40 analysis module importability
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_phase40_importable() -> None:
    """The phase40_analysis module must be importable and expose required callables."""
    mod = importlib.import_module("cwt.cgt.analysis.phase40_analysis")
    assert hasattr(mod, "run_phase40_analysis"), (
        "phase40_analysis module is missing 'run_phase40_analysis'"
    )
    assert hasattr(mod, "Phase40Config"), (
        "phase40_analysis module is missing 'Phase40Config'"
    )


# ---------------------------------------------------------------------------
# c) Phase 40 artifact structural integrity
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_phase40_artifact_structure() -> None:
    """The Phase 40 artifact must contain required switch_metrics keys with passing thresholds."""
    path = _PHASE40_ARTIFACT
    assert path.exists(), f"Phase 40 artifact not found: {path}"

    data = json.loads(path.read_text(encoding="utf-8"))
    sm = data["switch_metrics"]
    assert isinstance(sm, dict), (
        f"Expected switch_metrics to be a dict, got {type(sm).__name__}"
    )

    required_keys = ("train_r2", "heldout_base_r2", "heldout_new_r2", "heldout_combined_r2")
    for key in required_keys:
        assert key in sm, f"Missing switch_metrics.{key}"

    assert sm["heldout_new_r2"] >= 0.85, (
        f"switch_metrics.heldout_new_r2 expected >= 0.85, got {sm['heldout_new_r2']}"
    )
    assert sm["heldout_combined_r2"] >= 0.90, (
        f"switch_metrics.heldout_combined_r2 expected >= 0.90, got {sm['heldout_combined_r2']}"
    )


# ---------------------------------------------------------------------------
# d) run_phase40_analysis() actually executes and produces correct output
# ---------------------------------------------------------------------------

# project_root is the cwt-sim/ directory (where cgt_benchmarks/ lives)
_PROJECT_ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.unit
def test_phase40_analysis_runs(tmp_path: Path) -> None:
    """run_phase40_analysis must execute without error and return a conforming payload."""
    from cwt.cgt.analysis.phase40_analysis import run_phase40_analysis

    payload = run_phase40_analysis(project_root=_PROJECT_ROOT, output_root=tmp_path)

    assert isinstance(payload, dict), "run_phase40_analysis must return a dict"
    assert "switch_metrics" in payload, (
        f"Payload missing 'switch_metrics'; keys: {sorted(payload.keys())}"
    )

    sm = payload["switch_metrics"]
    assert sm["heldout_new_r2"] >= 0.85, (
        f"switch_metrics.heldout_new_r2 expected >= 0.85, got {sm['heldout_new_r2']}"
    )
    assert sm["heldout_combined_r2"] >= 0.90, (
        f"switch_metrics.heldout_combined_r2 expected >= 0.90, got {sm['heldout_combined_r2']}"
    )
    assert payload["verdict"] == "second_positive_noisy_scaffold_supported", (
        f"Expected verdict 'second_positive_noisy_scaffold_supported', "
        f"got {payload['verdict']!r}"
    )


# ---------------------------------------------------------------------------
# e) Phase 40 coefficients must match Phase 39 source (no refit)
# ---------------------------------------------------------------------------

_PHASE39_ARTIFACT = _RESULTS_DIR / "benchmark_c_phase39_local_superoperator_compactness_normalizer.json"


@pytest.mark.unit
def test_phase40_coefficients_match_phase39_source(tmp_path: Path) -> None:
    """Coefficients embedded in the Phase 40 output must equal the Phase 39 source.

    This proves that run_phase40_analysis() reads and reuses the accepted Phase 39
    rule without refitting any coefficients.
    """
    from cwt.cgt.analysis.phase40_analysis import run_phase40_analysis

    # Load the Phase 39 source artifact
    assert _PHASE39_ARTIFACT.exists(), f"Phase 39 source artifact missing: {_PHASE39_ARTIFACT}"
    phase39_data = json.loads(_PHASE39_ARTIFACT.read_text(encoding="utf-8"))

    # Build a lookup of dephasing -> derivation from Phase 39 levels
    phase39_rules: dict[float, dict] = {}
    for level in phase39_data["levels"]:
        gamma = float(level["dephasing"])
        phase39_rules[gamma] = level["local_superoperator_compactness_normalizer"]

    # Run the analysis to produce a fresh Phase 40 payload
    payload = run_phase40_analysis(project_root=_PROJECT_ROOT, output_root=tmp_path)

    # For each level in the Phase 40 output, the accepted_phase39_rule must
    # contain coefficients that are identical to the Phase 39 source.
    for level in payload["levels"]:
        gamma = float(level["dephasing"])
        assert gamma in phase39_rules, (
            f"Phase 40 uses dephasing={gamma} but Phase 39 has no matching level; "
            f"available: {sorted(phase39_rules)}"
        )
        p39_rule = phase39_rules[gamma]
        p40_rule = level["accepted_phase39_rule"]

        # Coefficients must be identical (not merely close -- no refit means exact equality)
        assert p40_rule["coefficients"] == p39_rule["coefficients"], (
            f"At dephasing={gamma}: Phase 40 coefficients differ from Phase 39 source.\n"
            f"  Phase 39: {p39_rule['coefficients']}\n"
            f"  Phase 40: {p40_rule['coefficients']}"
        )
        assert p40_rule["higher_order_coefficients"] == p39_rule["higher_order_coefficients"], (
            f"At dephasing={gamma}: Phase 40 higher_order_coefficients differ from Phase 39 source.\n"
            f"  Phase 39: {p39_rule['higher_order_coefficients']}\n"
            f"  Phase 40: {p40_rule['higher_order_coefficients']}"
        )
        assert p40_rule["compactness_normalizer_parameters"] == p39_rule["compactness_normalizer_parameters"], (
            f"At dephasing={gamma}: Phase 40 compactness_normalizer_parameters differ from Phase 39 source.\n"
            f"  Phase 39: {p39_rule['compactness_normalizer_parameters']}\n"
            f"  Phase 40: {p40_rule['compactness_normalizer_parameters']}"
        )
