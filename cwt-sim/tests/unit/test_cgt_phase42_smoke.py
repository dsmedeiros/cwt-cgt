"""Smoke tests for CGT Phase 42 / Third Positive Noisy Scaffold result artifact and analysis module.

Covers:
- Existence and JSON-validity of the benchmark_H_offset_ring Phase 42 artifact.
- Importability of the phase42_analysis module.
- Structural integrity of the Phase 42 artifact (including switch_metrics).
- Execution of run_phase42_analysis() to verify the function produces correct output.

Phase 42 evaluates the five-node offset ring (benchmark H) under the frozen pooled
positive-noisy scaffold rule from Phase 41, without any benchmark-specific coefficient
refit. Results live in cgt_benchmarks/results/benchmark_H_offset_ring/.
"""

from __future__ import annotations

import importlib
import json
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_RESULTS_DIR = _PROJECT_ROOT / 'cgt_benchmarks' / 'results' / 'benchmark_H_offset_ring'
_PHASE42_ARTIFACT = _RESULTS_DIR / 'benchmark_h_phase42_third_positive_noisy.json'


# ---------------------------------------------------------------------------
# a) Artifact existence and JSON validity
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_phase42_artifact_exists() -> None:
    """The Phase 42 benchmark_H_offset_ring artifact must exist and parse as JSON."""
    path = _PHASE42_ARTIFACT
    assert path.exists(), f"Missing: {path}"
    data = json.loads(path.read_text(encoding='utf-8'))
    assert 'switch_metrics' in data, (
        f"Expected 'switch_metrics' key in Phase 42 artifact, "
        f"found keys: {sorted(data.keys())}"
    )
    assert 'verdict' in data, (
        f"Expected 'verdict' key in Phase 42 artifact, "
        f"found keys: {sorted(data.keys())}"
    )
    assert data['verdict'] == 'third_positive_noisy_scaffold_supported', (
        f"Unexpected verdict value: {data['verdict']!r}"
    )


# ---------------------------------------------------------------------------
# b) Module importability
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_phase42_importable() -> None:
    """The phase42_analysis module must be importable and expose required callables."""
    mod = importlib.import_module('cwt.cgt.analysis.phase42_analysis')
    assert hasattr(mod, 'run_phase42_analysis'), (
        "phase42_analysis module is missing 'run_phase42_analysis'"
    )
    assert hasattr(mod, 'Phase42Config'), (
        "phase42_analysis module is missing 'Phase42Config'"
    )


# ---------------------------------------------------------------------------
# c) Artifact structural integrity
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_phase42_artifact_structure() -> None:
    """The Phase 42 artifact must contain required switch_metrics keys with passing thresholds."""
    path = _PHASE42_ARTIFACT
    assert path.exists(), f"Phase 42 artifact not found: {path}"

    data = json.loads(path.read_text(encoding='utf-8'))
    sm = data['switch_metrics']
    assert isinstance(sm, dict), (
        f"Expected switch_metrics to be a dict, got {type(sm).__name__}"
    )

    required_keys = ('heldout_new', 'heldout_combined')
    for key in required_keys:
        assert key in sm, f"Missing switch_metrics.{key}"

    heldout_new = sm['heldout_new']
    heldout_combined = sm['heldout_combined']

    assert isinstance(heldout_new, dict), (
        f"Expected switch_metrics.heldout_new to be a dict, got {type(heldout_new).__name__}"
    )
    assert isinstance(heldout_combined, dict), (
        f"Expected switch_metrics.heldout_combined to be a dict, got {type(heldout_combined).__name__}"
    )

    assert 'r2' in heldout_new, "Missing switch_metrics.heldout_new.r2"
    assert 'r2' in heldout_combined, "Missing switch_metrics.heldout_combined.r2"

    assert heldout_new['r2'] is not None and heldout_new['r2'] > 0.95, (
        f"switch_metrics.heldout_new.r2 expected > 0.95, "
        f"got {heldout_new['r2']}"
    )
    assert heldout_combined['r2'] is not None and heldout_combined['r2'] > 0.96, (
        f"switch_metrics.heldout_combined.r2 expected > 0.96, "
        f"got {heldout_combined['r2']}"
    )


# ---------------------------------------------------------------------------
# d) run_phase42_analysis() actually executes and produces correct output
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_phase42_analysis_runs(tmp_path: Path) -> None:
    """run_phase42_analysis must execute without error and return a conforming payload."""
    from cwt.cgt.analysis.phase42_analysis import run_phase42_analysis

    payload = run_phase42_analysis(project_root=_PROJECT_ROOT, output_root=tmp_path)

    assert isinstance(payload, dict), 'run_phase42_analysis must return a dict'
    assert 'switch_metrics' in payload, (
        f"Payload missing 'switch_metrics'; keys: {sorted(payload.keys())}"
    )

    sm = payload['switch_metrics']
    assert isinstance(sm, dict), (
        f"Expected switch_metrics to be a dict, got {type(sm).__name__}"
    )

    heldout_new = sm['heldout_new']
    heldout_combined = sm['heldout_combined']

    assert heldout_new['r2'] is not None and heldout_new['r2'] > 0.95, (
        f"switch_metrics.heldout_new.r2 expected > 0.95, "
        f"got {heldout_new['r2']}"
    )
    assert heldout_combined['r2'] is not None and heldout_combined['r2'] > 0.96, (
        f"switch_metrics.heldout_combined.r2 expected > 0.96, "
        f"got {heldout_combined['r2']}"
    )
    assert payload['verdict'] == 'third_positive_noisy_scaffold_supported', (
        f"Expected verdict 'third_positive_noisy_scaffold_supported', "
        f"got {payload['verdict']!r}"
    )
