"""Smoke tests for CGT Phases 45 and 46 / Pooled four-positive noisy scaffold and
broadened pooled stronger perturbation family result artifacts and analysis modules.

Covers:
- Existence and JSON-validity of the Phase 45 scaffold artifact and Phase 46 artifact.
- Importability of the phase45_analysis and phase46_analysis modules.
- Structural integrity of both artifacts (including switch_metrics).
- Execution of run_phase45_analysis() and run_phase46_analysis() to verify correct output.

Phase 45 derives a pooled positive-noisy scaffold rule from the train rows of FOUR
benchmarks (C, G, H, and I), then evaluates on held-out shape families across all four
benchmarks without any benchmark-specific refit.

Phase 46 evaluates the benchmark I stronger perturbation family under the Phase 45
broadened pooled four-positive noisy scaffold rule with no stronger-family refit.

Results live in:
  cgt_benchmarks/results/benchmark_scaffold_family/ (Phase 45)
  cgt_benchmarks/results/benchmark_I_nonring_ladder/ (Phase 46)
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
_SCAFFOLD_DIR = _PROJECT_ROOT / 'cgt_benchmarks' / 'results' / 'benchmark_scaffold_family'
_LADDER_DIR = _PROJECT_ROOT / 'cgt_benchmarks' / 'results' / 'benchmark_I_nonring_ladder'
_PHASE45_ARTIFACT = _SCAFFOLD_DIR / 'benchmark_scaffold_phase45_pooled_four_positive_noisy.json'
_PHASE46_ARTIFACT = _LADDER_DIR / 'benchmark_i_phase46_pooled_four_stronger_perturbation.json'


# ---------------------------------------------------------------------------
# Phase 45 — a) Artifact existence and JSON validity
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_phase45_artifact_exists() -> None:
    """The Phase 45 pooled four-positive noisy scaffold artifact must exist and parse as JSON."""
    path = _PHASE45_ARTIFACT
    assert path.exists(), f"Missing: {path}"
    data = json.loads(path.read_text(encoding='utf-8'))
    assert 'switch_metrics' in data, (
        f"Expected 'switch_metrics' key in Phase 45 artifact, "
        f"found keys: {sorted(data.keys())}"
    )
    assert 'verdict' in data, (
        f"Expected 'verdict' key in Phase 45 artifact, "
        f"found keys: {sorted(data.keys())}"
    )
    assert data['verdict'] == 'pooled_four_positive_noisy_scaffold_supported', (
        f"Unexpected verdict value: {data['verdict']!r}"
    )


# ---------------------------------------------------------------------------
# Phase 45 — b) Module importability
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_phase45_importable() -> None:
    """The phase45_analysis module must be importable and expose required callables."""
    mod = importlib.import_module('cwt.cgt.analysis.phase45_analysis')
    assert hasattr(mod, 'run_phase45_analysis'), (
        "phase45_analysis module is missing 'run_phase45_analysis'"
    )
    assert hasattr(mod, 'Phase45Config'), (
        "phase45_analysis module is missing 'Phase45Config'"
    )
    assert hasattr(mod, '_summary'), (
        "phase45_analysis module is missing '_summary' (required by phase46_analysis)"
    )
    assert hasattr(mod, '_predict_row'), (
        "phase45_analysis module is missing '_predict_row' (required by phase46_analysis)"
    )


# ---------------------------------------------------------------------------
# Phase 45 — c) Artifact structural integrity
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_phase45_artifact_structure() -> None:
    """The Phase 45 artifact must contain required switch_metrics keys with passing thresholds."""
    path = _PHASE45_ARTIFACT
    assert path.exists(), f"Phase 45 artifact not found: {path}"

    data = json.loads(path.read_text(encoding='utf-8'))
    sm = data['switch_metrics']
    assert isinstance(sm, dict), (
        f"Expected switch_metrics to be a dict, got {type(sm).__name__}"
    )

    required_keys = ('pooled_scaffold', 'benchmark_c', 'benchmark_g', 'benchmark_h', 'benchmark_i')
    for key in required_keys:
        assert key in sm, f"Missing switch_metrics.{key}"

    pooled = sm['pooled_scaffold']
    assert isinstance(pooled, dict), (
        f"Expected switch_metrics.pooled_scaffold to be a dict, got {type(pooled).__name__}"
    )
    assert 'r2' in pooled, "Missing switch_metrics.pooled_scaffold.r2"
    assert pooled['r2'] is not None and pooled['r2'] > 0.97, (
        f"switch_metrics.pooled_scaffold.r2 expected > 0.97, "
        f"got {pooled['r2']}"
    )


# ---------------------------------------------------------------------------
# Phase 45 — d) run_phase45_analysis() actually executes and produces correct output
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_phase45_analysis_runs(tmp_path: Path) -> None:
    """run_phase45_analysis must execute without error and return a conforming payload."""
    from cwt.cgt.analysis.phase45_analysis import run_phase45_analysis

    payload = run_phase45_analysis(project_root=_PROJECT_ROOT, output_root=tmp_path)

    assert isinstance(payload, dict), 'run_phase45_analysis must return a dict'
    assert 'switch_metrics' in payload, (
        f"Payload missing 'switch_metrics'; keys: {sorted(payload.keys())}"
    )

    sm = payload['switch_metrics']
    assert isinstance(sm, dict), (
        f"Expected switch_metrics to be a dict, got {type(sm).__name__}"
    )

    pooled = sm['pooled_scaffold']
    assert pooled['r2'] is not None and pooled['r2'] > 0.97, (
        f"switch_metrics.pooled_scaffold.r2 expected > 0.97, "
        f"got {pooled['r2']}"
    )
    assert payload['verdict'] == 'pooled_four_positive_noisy_scaffold_supported', (
        f"Expected verdict 'pooled_four_positive_noisy_scaffold_supported', "
        f"got {payload['verdict']!r}"
    )


# ---------------------------------------------------------------------------
# Phase 46 — a) Artifact existence and JSON validity
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_phase46_artifact_exists() -> None:
    """The Phase 46 benchmark_I_nonring_ladder artifact must exist and parse as JSON."""
    path = _PHASE46_ARTIFACT
    assert path.exists(), f"Missing: {path}"
    data = json.loads(path.read_text(encoding='utf-8'))
    assert 'switch_metrics' in data, (
        f"Expected 'switch_metrics' key in Phase 46 artifact, "
        f"found keys: {sorted(data.keys())}"
    )
    assert 'verdict' in data, (
        f"Expected 'verdict' key in Phase 46 artifact, "
        f"found keys: {sorted(data.keys())}"
    )
    assert data['verdict'] == 'broadened_pooled_stronger_family_supported', (
        f"Unexpected verdict value: {data['verdict']!r}"
    )


# ---------------------------------------------------------------------------
# Phase 46 — b) Module importability
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_phase46_importable() -> None:
    """The phase46_analysis module must be importable and expose required callables."""
    mod = importlib.import_module('cwt.cgt.analysis.phase46_analysis')
    assert hasattr(mod, 'run_phase46_analysis'), (
        "phase46_analysis module is missing 'run_phase46_analysis'"
    )
    assert hasattr(mod, 'Phase46Config'), (
        "phase46_analysis module is missing 'Phase46Config'"
    )


# ---------------------------------------------------------------------------
# Phase 46 — c) Artifact structural integrity
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_phase46_artifact_structure() -> None:
    """The Phase 46 artifact must contain required switch_metrics keys with passing thresholds."""
    path = _PHASE46_ARTIFACT
    assert path.exists(), f"Phase 46 artifact not found: {path}"

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

    assert heldout_strong['r2'] is not None and heldout_strong['r2'] > 0.92, (
        f"switch_metrics.heldout_strong.r2 expected > 0.92, "
        f"got {heldout_strong['r2']}"
    )
    assert heldout_combined['r2'] is not None and heldout_combined['r2'] > 0.96, (
        f"switch_metrics.heldout_combined.r2 expected > 0.96, "
        f"got {heldout_combined['r2']}"
    )


# ---------------------------------------------------------------------------
# Phase 46 — d) run_phase46_analysis() actually executes and produces correct output
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_phase46_analysis_runs(tmp_path: Path) -> None:
    """run_phase46_analysis must execute without error and return a conforming payload.

    Phase 45 must run first into tmp_path to produce the pooled scaffold artifact that
    Phase 46 reads from output_root.
    """
    from cwt.cgt.analysis.phase45_analysis import run_phase45_analysis
    from cwt.cgt.analysis.phase46_analysis import run_phase46_analysis

    # Phase 45 writes the pooled scaffold artifact into tmp_path
    run_phase45_analysis(project_root=_PROJECT_ROOT, output_root=tmp_path)

    # Phase 46 reads from output_root=tmp_path for the pooled artifact
    payload = run_phase46_analysis(project_root=_PROJECT_ROOT, output_root=tmp_path)

    assert isinstance(payload, dict), 'run_phase46_analysis must return a dict'
    assert 'switch_metrics' in payload, (
        f"Payload missing 'switch_metrics'; keys: {sorted(payload.keys())}"
    )

    sm = payload['switch_metrics']
    assert isinstance(sm, dict), (
        f"Expected switch_metrics to be a dict, got {type(sm).__name__}"
    )

    heldout_strong = sm['heldout_strong']
    heldout_combined = sm['heldout_combined']

    assert heldout_strong['r2'] is not None and heldout_strong['r2'] > 0.92, (
        f"switch_metrics.heldout_strong.r2 expected > 0.92, "
        f"got {heldout_strong['r2']}"
    )
    assert heldout_combined['r2'] is not None and heldout_combined['r2'] > 0.96, (
        f"switch_metrics.heldout_combined.r2 expected > 0.96, "
        f"got {heldout_combined['r2']}"
    )
    assert payload['verdict'] == 'broadened_pooled_stronger_family_supported', (
        f"Expected verdict 'broadened_pooled_stronger_family_supported', "
        f"got {payload['verdict']!r}"
    )
