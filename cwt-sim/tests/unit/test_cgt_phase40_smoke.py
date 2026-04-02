"""Smoke tests for CGT Phase 40 / Benchmark G result artifact and analysis module.

Covers:
- Existence and JSON-validity of the benchmark_G_skew_ring Phase 40 artifact.
- Importability of the phase40_analysis module.
- Structural integrity of the Phase 40 artifact (including switch_metrics).

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

    assert sm["heldout_new_r2"] > 0.85, (
        f"switch_metrics.heldout_new_r2 expected > 0.85, got {sm['heldout_new_r2']}"
    )
    assert sm["heldout_combined_r2"] > 0.90, (
        f"switch_metrics.heldout_combined_r2 expected > 0.90, got {sm['heldout_combined_r2']}"
    )
