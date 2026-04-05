"""Smoke tests for CGT Phases 47 and 48 / Fifth positive noisy scaffold (Benchmark J)
and harder perturbation-family stress test result artifacts and analysis modules.

Covers:
- Existence and JSON-validity of the Phase 47 and Phase 48 benchmark J artifacts.
- Importability of the phase47_analysis and phase48_analysis modules.
- Structural integrity of both artifacts (including switch_metrics).
- Execution of run_phase47_analysis() and run_phase48_analysis() to verify correct output.

Phase 47 evaluates the structurally different non-ring bowtie-chain benchmark (J) under the
unchanged pooled four-positive noisy scaffold rule derived in Phase 45.  No benchmark-specific
coefficient refit is applied.

Phase 48 stress-tests the same benchmark J with a harder perturbation family (crescent,
chevron, hourglass shapes) under the same unchanged pooled rule.

Results live in:
  cgt_benchmarks/results/benchmark_J_bowtie_chain/ (Phases 47 and 48)
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
_BOWTIE_DIR = _PROJECT_ROOT / 'cgt_benchmarks' / 'results' / 'benchmark_J_bowtie_chain'
_PHASE47_ARTIFACT = _BOWTIE_DIR / 'benchmark_j_phase47_fifth_positive_noisy.json'
_PHASE48_ARTIFACT = _BOWTIE_DIR / 'benchmark_j_phase48_harder_perturbation_family.json'


# ---------------------------------------------------------------------------
# Phase 47 — a) Artifact existence and JSON validity
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_phase47_artifact_exists() -> None:
    """The Phase 47 benchmark J fifth positive noisy artifact must exist and parse as JSON."""
    path = _PHASE47_ARTIFACT
    assert path.exists(), f"Missing: {path}"
    data = json.loads(path.read_text(encoding='utf-8'))
    assert 'switch_metrics' in data, (
        f"Expected 'switch_metrics' key in Phase 47 artifact, "
        f"found keys: {sorted(data.keys())}"
    )
    assert 'verdict' in data, (
        f"Expected 'verdict' key in Phase 47 artifact, "
        f"found keys: {sorted(data.keys())}"
    )
    assert data['verdict'] == 'fifth_positive_noisy_scaffold_supported', (
        f"Unexpected verdict value: {data['verdict']!r}"
    )


# ---------------------------------------------------------------------------
# Phase 47 — b) Module importability
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_phase47_importable() -> None:
    """The phase47_analysis module must be importable and expose required callables."""
    mod = importlib.import_module('cwt.cgt.analysis.phase47_analysis')
    assert hasattr(mod, 'run_phase47_analysis'), (
        "phase47_analysis module is missing 'run_phase47_analysis'"
    )
    assert hasattr(mod, 'Phase47Config'), (
        "phase47_analysis module is missing 'Phase47Config'"
    )
    assert hasattr(mod, 'SHAPE_AREA'), (
        "phase47_analysis module is missing 'SHAPE_AREA' (required by phase48_analysis)"
    )
    assert hasattr(mod, 'SHAPE_SCALE'), (
        "phase47_analysis module is missing 'SHAPE_SCALE' (required by phase48_analysis)"
    )
    assert hasattr(mod, 'SHAPE_CURVATURE'), (
        "phase47_analysis module is missing 'SHAPE_CURVATURE' (required by phase48_analysis)"
    )


# ---------------------------------------------------------------------------
# Phase 47 — c) Artifact structural integrity
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_phase47_artifact_structure() -> None:
    """The Phase 47 artifact must contain required switch_metrics keys with passing thresholds."""
    path = _PHASE47_ARTIFACT
    assert path.exists(), f"Phase 47 artifact not found: {path}"

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

    assert heldout_new['r2'] is not None and heldout_new['r2'] > 0.97, (
        f"switch_metrics.heldout_new.r2 expected > 0.97, "
        f"got {heldout_new['r2']}"
    )
    assert heldout_combined['r2'] is not None and heldout_combined['r2'] > 0.97, (
        f"switch_metrics.heldout_combined.r2 expected > 0.97, "
        f"got {heldout_combined['r2']}"
    )


# ---------------------------------------------------------------------------
# Phase 47 — d) run_phase47_analysis() actually executes and produces correct output
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_phase47_analysis_runs(tmp_path: Path) -> None:
    """run_phase47_analysis must execute without error and return a conforming payload.

    Phase 45 must run first into tmp_path to produce the pooled scaffold artifact that
    Phase 47 reads from output_root.
    """
    from cwt.cgt.analysis.phase45_analysis import run_phase45_analysis
    from cwt.cgt.analysis.phase47_analysis import run_phase47_analysis

    # Phase 45 writes the pooled scaffold artifact into tmp_path
    run_phase45_analysis(project_root=_PROJECT_ROOT, output_root=tmp_path)

    # Phase 47 reads the pooled scaffold artifact from output_root=tmp_path
    payload = run_phase47_analysis(project_root=_PROJECT_ROOT, output_root=tmp_path)

    assert isinstance(payload, dict), 'run_phase47_analysis must return a dict'
    assert 'switch_metrics' in payload, (
        f"Payload missing 'switch_metrics'; keys: {sorted(payload.keys())}"
    )

    sm = payload['switch_metrics']
    assert isinstance(sm, dict), (
        f"Expected switch_metrics to be a dict, got {type(sm).__name__}"
    )

    heldout_new = sm['heldout_new']
    heldout_combined = sm['heldout_combined']

    assert heldout_new['r2'] is not None and heldout_new['r2'] > 0.97, (
        f"switch_metrics.heldout_new.r2 expected > 0.97, "
        f"got {heldout_new['r2']}"
    )
    assert heldout_combined['r2'] is not None and heldout_combined['r2'] > 0.97, (
        f"switch_metrics.heldout_combined.r2 expected > 0.97, "
        f"got {heldout_combined['r2']}"
    )
    assert payload['verdict'] == 'fifth_positive_noisy_scaffold_supported', (
        f"Expected verdict 'fifth_positive_noisy_scaffold_supported', "
        f"got {payload['verdict']!r}"
    )


# ---------------------------------------------------------------------------
# Phase 48 — a) Artifact existence and JSON validity
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_phase48_artifact_exists() -> None:
    """The Phase 48 benchmark J harder perturbation family artifact must exist and parse as JSON."""
    path = _PHASE48_ARTIFACT
    assert path.exists(), f"Missing: {path}"
    data = json.loads(path.read_text(encoding='utf-8'))
    assert 'switch_metrics' in data, (
        f"Expected 'switch_metrics' key in Phase 48 artifact, "
        f"found keys: {sorted(data.keys())}"
    )
    assert 'verdict' in data, (
        f"Expected 'verdict' key in Phase 48 artifact, "
        f"found keys: {sorted(data.keys())}"
    )
    assert data['verdict'] == 'fifth_benchmark_stronger_family_supported', (
        f"Unexpected verdict value: {data['verdict']!r}"
    )


# ---------------------------------------------------------------------------
# Phase 48 — b) Module importability
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_phase48_importable() -> None:
    """The phase48_analysis module must be importable and expose required callables."""
    mod = importlib.import_module('cwt.cgt.analysis.phase48_analysis')
    assert hasattr(mod, 'run_phase48_analysis'), (
        "phase48_analysis module is missing 'run_phase48_analysis'"
    )
    assert hasattr(mod, 'Phase48Config'), (
        "phase48_analysis module is missing 'Phase48Config'"
    )


# ---------------------------------------------------------------------------
# Phase 48 — c) Artifact structural integrity
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_phase48_artifact_structure() -> None:
    """The Phase 48 artifact must contain required switch_metrics keys with passing thresholds."""
    path = _PHASE48_ARTIFACT
    assert path.exists(), f"Phase 48 artifact not found: {path}"

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

    assert heldout_strong['r2'] is not None and heldout_strong['r2'] > 0.82, (
        f"switch_metrics.heldout_strong.r2 expected > 0.82, "
        f"got {heldout_strong['r2']}"
    )
    assert heldout_combined['r2'] is not None and heldout_combined['r2'] > 0.92, (
        f"switch_metrics.heldout_combined.r2 expected > 0.92, "
        f"got {heldout_combined['r2']}"
    )


# ---------------------------------------------------------------------------
# Phase 48 — d) run_phase48_analysis() actually executes and produces correct output
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_phase48_analysis_runs(tmp_path: Path) -> None:
    """run_phase48_analysis must execute without error and return a conforming payload.

    Phase 45 must run first into tmp_path to produce the pooled scaffold artifact that
    Phase 48 reads from output_root.
    """
    from cwt.cgt.analysis.phase45_analysis import run_phase45_analysis
    from cwt.cgt.analysis.phase48_analysis import run_phase48_analysis

    # Phase 45 writes the pooled scaffold artifact into tmp_path
    run_phase45_analysis(project_root=_PROJECT_ROOT, output_root=tmp_path)

    # Phase 48 reads the pooled scaffold artifact from output_root=tmp_path
    payload = run_phase48_analysis(project_root=_PROJECT_ROOT, output_root=tmp_path)

    assert isinstance(payload, dict), 'run_phase48_analysis must return a dict'
    assert 'switch_metrics' in payload, (
        f"Payload missing 'switch_metrics'; keys: {sorted(payload.keys())}"
    )

    sm = payload['switch_metrics']
    assert isinstance(sm, dict), (
        f"Expected switch_metrics to be a dict, got {type(sm).__name__}"
    )

    heldout_strong = sm['heldout_strong']
    heldout_combined = sm['heldout_combined']

    assert heldout_strong['r2'] is not None and heldout_strong['r2'] > 0.82, (
        f"switch_metrics.heldout_strong.r2 expected > 0.82, "
        f"got {heldout_strong['r2']}"
    )
    assert heldout_combined['r2'] is not None and heldout_combined['r2'] > 0.92, (
        f"switch_metrics.heldout_combined.r2 expected > 0.92, "
        f"got {heldout_combined['r2']}"
    )
    assert payload['verdict'] == 'fifth_benchmark_stronger_family_supported', (
        f"Expected verdict 'fifth_benchmark_stronger_family_supported', "
        f"got {payload['verdict']!r}"
    )
