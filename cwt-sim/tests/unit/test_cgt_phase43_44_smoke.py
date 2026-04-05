"""Smoke tests for CGT Phases 43 and 44 / Non-ring ladder positive noisy scaffold result artifacts and analysis modules.

Covers:
- Existence and JSON-validity of the benchmark_I_nonring_ladder Phase 43 and Phase 44 artifacts.
- Importability of the phase43_analysis and phase44_analysis modules.
- Structural integrity of the Phase 43 and Phase 44 artifacts (including switch_metrics).
- Execution of run_phase43_analysis() and run_phase44_analysis() to verify correct output.

Phase 43 evaluates the five-node non-ring ladder (benchmark I) under the frozen pooled
positive-noisy scaffold rule from Phase 41, without any benchmark-specific coefficient refit.

Phase 44 extends Phase 43 with a stronger perturbation-family tier (superellipse, teardrop,
peanut) that has curvature values far above the training range, stress-testing the rule's
robustness to distribution shift.

Results live in cgt_benchmarks/results/benchmark_I_nonring_ladder/.
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
_RESULTS_DIR = _PROJECT_ROOT / 'cgt_benchmarks' / 'results' / 'benchmark_I_nonring_ladder'
_PHASE43_ARTIFACT = _RESULTS_DIR / 'benchmark_i_phase43_nonring_positive_noisy.json'
_PHASE44_ARTIFACT = _RESULTS_DIR / 'benchmark_i_phase44_stronger_perturbation_family.json'


# ---------------------------------------------------------------------------
# Phase 43 — a) Artifact existence and JSON validity
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_phase43_artifact_exists() -> None:
    """The Phase 43 benchmark_I_nonring_ladder artifact must exist and parse as JSON."""
    path = _PHASE43_ARTIFACT
    assert path.exists(), f"Missing: {path}"
    data = json.loads(path.read_text(encoding='utf-8'))
    assert 'switch_metrics' in data, (
        f"Expected 'switch_metrics' key in Phase 43 artifact, "
        f"found keys: {sorted(data.keys())}"
    )
    assert 'verdict' in data, (
        f"Expected 'verdict' key in Phase 43 artifact, "
        f"found keys: {sorted(data.keys())}"
    )
    assert data['verdict'] == 'nonring_positive_noisy_scaffold_supported', (
        f"Unexpected verdict value: {data['verdict']!r}"
    )


# ---------------------------------------------------------------------------
# Phase 43 — b) Module importability
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_phase43_importable() -> None:
    """The phase43_analysis module must be importable and expose required callables."""
    mod = importlib.import_module('cwt.cgt.analysis.phase43_analysis')
    assert hasattr(mod, 'run_phase43_analysis'), (
        "phase43_analysis module is missing 'run_phase43_analysis'"
    )
    assert hasattr(mod, 'Phase43Config'), (
        "phase43_analysis module is missing 'Phase43Config'"
    )


# ---------------------------------------------------------------------------
# Phase 43 — c) Artifact structural integrity
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_phase43_artifact_structure() -> None:
    """The Phase 43 artifact must contain required switch_metrics keys with passing thresholds."""
    path = _PHASE43_ARTIFACT
    assert path.exists(), f"Phase 43 artifact not found: {path}"

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
    assert heldout_combined['r2'] is not None and heldout_combined['r2'] > 0.97, (
        f"switch_metrics.heldout_combined.r2 expected > 0.97, "
        f"got {heldout_combined['r2']}"
    )


# ---------------------------------------------------------------------------
# Phase 43 — d) run_phase43_analysis() actually executes and produces correct output
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_phase43_analysis_runs(tmp_path: Path) -> None:
    """run_phase43_analysis must execute without error and return a conforming payload."""
    from cwt.cgt.analysis.phase43_analysis import run_phase43_analysis

    payload = run_phase43_analysis(project_root=_PROJECT_ROOT, output_root=tmp_path)

    assert isinstance(payload, dict), 'run_phase43_analysis must return a dict'
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
    assert heldout_combined['r2'] is not None and heldout_combined['r2'] > 0.97, (
        f"switch_metrics.heldout_combined.r2 expected > 0.97, "
        f"got {heldout_combined['r2']}"
    )
    assert payload['verdict'] == 'nonring_positive_noisy_scaffold_supported', (
        f"Expected verdict 'nonring_positive_noisy_scaffold_supported', "
        f"got {payload['verdict']!r}"
    )


# ---------------------------------------------------------------------------
# Phase 44 — a) Artifact existence and JSON validity
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_phase44_artifact_exists() -> None:
    """The Phase 44 benchmark_I_nonring_ladder artifact must exist and parse as JSON."""
    path = _PHASE44_ARTIFACT
    assert path.exists(), f"Missing: {path}"
    data = json.loads(path.read_text(encoding='utf-8'))
    assert 'switch_metrics' in data, (
        f"Expected 'switch_metrics' key in Phase 44 artifact, "
        f"found keys: {sorted(data.keys())}"
    )
    assert 'verdict' in data, (
        f"Expected 'verdict' key in Phase 44 artifact, "
        f"found keys: {sorted(data.keys())}"
    )
    assert data['verdict'] == 'stronger_perturbation_family_supported', (
        f"Unexpected verdict value: {data['verdict']!r}"
    )


# ---------------------------------------------------------------------------
# Phase 44 — b) Module importability
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_phase44_importable() -> None:
    """The phase44_analysis module must be importable and expose required callables."""
    mod = importlib.import_module('cwt.cgt.analysis.phase44_analysis')
    assert hasattr(mod, 'run_phase44_analysis'), (
        "phase44_analysis module is missing 'run_phase44_analysis'"
    )
    assert hasattr(mod, 'Phase44Config'), (
        "phase44_analysis module is missing 'Phase44Config'"
    )


# ---------------------------------------------------------------------------
# Phase 44 — c) Artifact structural integrity
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_phase44_artifact_structure() -> None:
    """The Phase 44 artifact must contain required switch_metrics keys with passing thresholds."""
    path = _PHASE44_ARTIFACT
    assert path.exists(), f"Phase 44 artifact not found: {path}"

    data = json.loads(path.read_text(encoding='utf-8'))
    sm = data['switch_metrics']
    assert isinstance(sm, dict), (
        f"Expected switch_metrics to be a dict, got {type(sm).__name__}"
    )

    required_keys = ('heldout_strong', 'heldout_combined')
    for key in required_keys:
        assert key in sm, f"Missing switch_metrics.{key}"

    heldout_strong = sm['heldout_strong']
    heldout_combined = sm['heldout_combined']

    assert isinstance(heldout_strong, dict), (
        f"Expected switch_metrics.heldout_strong to be a dict, got {type(heldout_strong).__name__}"
    )
    assert isinstance(heldout_combined, dict), (
        f"Expected switch_metrics.heldout_combined to be a dict, got {type(heldout_combined).__name__}"
    )

    assert 'r2' in heldout_strong, "Missing switch_metrics.heldout_strong.r2"
    assert 'r2' in heldout_combined, "Missing switch_metrics.heldout_combined.r2"

    assert heldout_strong['r2'] is not None and heldout_strong['r2'] > 0.88, (
        f"switch_metrics.heldout_strong.r2 expected > 0.88, "
        f"got {heldout_strong['r2']}"
    )
    assert heldout_combined['r2'] is not None and heldout_combined['r2'] > 0.93, (
        f"switch_metrics.heldout_combined.r2 expected > 0.93, "
        f"got {heldout_combined['r2']}"
    )


# ---------------------------------------------------------------------------
# Phase 44 — d) run_phase44_analysis() actually executes and produces correct output
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_phase44_analysis_runs(tmp_path: Path) -> None:
    """run_phase44_analysis must execute without error and return a conforming payload."""
    from cwt.cgt.analysis.phase44_analysis import run_phase44_analysis

    payload = run_phase44_analysis(project_root=_PROJECT_ROOT, output_root=tmp_path)

    assert isinstance(payload, dict), 'run_phase44_analysis must return a dict'
    assert 'switch_metrics' in payload, (
        f"Payload missing 'switch_metrics'; keys: {sorted(payload.keys())}"
    )

    sm = payload['switch_metrics']
    assert isinstance(sm, dict), (
        f"Expected switch_metrics to be a dict, got {type(sm).__name__}"
    )

    heldout_strong = sm['heldout_strong']
    heldout_combined = sm['heldout_combined']

    assert heldout_strong['r2'] is not None and heldout_strong['r2'] > 0.88, (
        f"switch_metrics.heldout_strong.r2 expected > 0.88, "
        f"got {heldout_strong['r2']}"
    )
    assert heldout_combined['r2'] is not None and heldout_combined['r2'] > 0.93, (
        f"switch_metrics.heldout_combined.r2 expected > 0.93, "
        f"got {heldout_combined['r2']}"
    )
    assert payload['verdict'] == 'stronger_perturbation_family_supported', (
        f"Expected verdict 'stronger_perturbation_family_supported', "
        f"got {payload['verdict']!r}"
    )
