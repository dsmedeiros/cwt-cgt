"""Smoke tests for CGT Phases 53-54 result artifacts and analysis modules.

Covers:
- Existence and JSON-validity of the Phase 53-54 artifacts.
- Importability of the phase53-54 analysis modules.
- Structural integrity of each artifact (including switch_metrics).
- Execution of run_phaseNN_analysis() to verify correct output.

Phase 53 evaluates the seventh structurally different positive noisy scaffold
benchmark (benchmark L, fork-mesh topology) under the unchanged pooled-five
positive noisy scaffold rule.

Phase 54 stress-tests benchmark L (fork-mesh) with an adversarial perturbation
family designed to expose the sign boundary under the same unchanged pooled-five
scaffold rule. The adversarial family is expected to break sign agreement:
heldout_adversarial sign_agreement < 0.9 and heldout_combined sign_agreement < 0.95.

Results live in:
  cgt_benchmarks/results/benchmark_L_fork_mesh/
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
_FORK_MESH_DIR = _PROJECT_ROOT / 'cgt_benchmarks' / 'results' / 'benchmark_L_fork_mesh'

_PHASE53_ARTIFACT = _FORK_MESH_DIR / 'benchmark_l_phase53_seventh_positive_noisy.json'
_PHASE54_ARTIFACT = _FORK_MESH_DIR / 'benchmark_l_phase54_adversarial_sign_break.json'


# ---------------------------------------------------------------------------
# Phase 53 — a) Artifact existence and JSON validity
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_phase53_artifact_exists() -> None:
    """The Phase 53 seventh positive noisy scaffold artifact must exist and parse as JSON."""
    path = _PHASE53_ARTIFACT
    assert path.exists(), f"Missing: {path}"
    data = json.loads(path.read_text(encoding='utf-8'))
    assert 'switch_metrics' in data, (
        f"Expected 'switch_metrics' key in Phase 53 artifact, "
        f"found keys: {sorted(data.keys())}"
    )
    assert 'verdict' in data, (
        f"Expected 'verdict' key in Phase 53 artifact, "
        f"found keys: {sorted(data.keys())}"
    )
    assert data['verdict'] == 'seventh_positive_noisy_scaffold_supported', (
        f"Unexpected verdict value: {data['verdict']!r}"
    )


# ---------------------------------------------------------------------------
# Phase 53 — b) Module importability
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_phase53_importable() -> None:
    """The phase53_analysis module must be importable and expose required callables."""
    mod = importlib.import_module('cwt.cgt.analysis.phase53_analysis')
    assert hasattr(mod, 'run_phase53_analysis'), (
        "phase53_analysis module is missing 'run_phase53_analysis'"
    )


# ---------------------------------------------------------------------------
# Phase 53 — c) Artifact structural integrity
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_phase53_artifact_structure() -> None:
    """The Phase 53 artifact must contain required switch_metrics keys with passing thresholds."""
    path = _PHASE53_ARTIFACT
    assert path.exists(), f"Phase 53 artifact not found: {path}"

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
# Phase 53 — d) run_phase53_analysis() actually executes and produces correct output
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_phase53_analysis_runs(tmp_path: Path) -> None:
    """run_phase53_analysis must execute without error and return a conforming payload."""
    from cwt.cgt.analysis.phase53_analysis import run_phase53_analysis

    payload = run_phase53_analysis(project_root=_PROJECT_ROOT, output_root=tmp_path)

    assert isinstance(payload, dict), 'run_phase53_analysis must return a dict'
    assert 'switch_metrics' in payload, (
        f"Payload missing 'switch_metrics'; keys: {sorted(payload.keys())}"
    )

    sm = payload['switch_metrics']
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
    assert payload['verdict'] == 'seventh_positive_noisy_scaffold_supported', (
        f"Expected verdict 'seventh_positive_noisy_scaffold_supported', "
        f"got {payload['verdict']!r}"
    )


# ---------------------------------------------------------------------------
# Phase 54 — a) Artifact existence and JSON validity
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_phase54_artifact_exists() -> None:
    """The Phase 54 adversarial sign-break artifact must exist and parse as JSON."""
    path = _PHASE54_ARTIFACT
    assert path.exists(), f"Missing: {path}"
    data = json.loads(path.read_text(encoding='utf-8'))
    assert 'switch_metrics' in data, (
        f"Expected 'switch_metrics' key in Phase 54 artifact, "
        f"found keys: {sorted(data.keys())}"
    )
    assert 'verdict' in data, (
        f"Expected 'verdict' key in Phase 54 artifact, "
        f"found keys: {sorted(data.keys())}"
    )
    assert data['verdict'] == 'adversarial_sign_boundary_exposed', (
        f"Unexpected verdict value: {data['verdict']!r}"
    )


# ---------------------------------------------------------------------------
# Phase 54 — b) Module importability
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_phase54_importable() -> None:
    """The phase54_analysis module must be importable and expose required callables."""
    mod = importlib.import_module('cwt.cgt.analysis.phase54_analysis')
    assert hasattr(mod, 'run_phase54_analysis'), (
        "phase54_analysis module is missing 'run_phase54_analysis'"
    )


# ---------------------------------------------------------------------------
# Phase 54 — c) Artifact structural integrity
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_phase54_artifact_structure() -> None:
    """The Phase 54 artifact must contain required switch_metrics keys.

    The adversarial family is expected to break sign agreement, so assertions
    use less-than thresholds to verify the sign boundary is exposed.
    """
    path = _PHASE54_ARTIFACT
    assert path.exists(), f"Phase 54 artifact not found: {path}"

    data = json.loads(path.read_text(encoding='utf-8'))
    sm = data['switch_metrics']
    assert isinstance(sm, dict), (
        f"Expected switch_metrics to be a dict, got {type(sm).__name__}"
    )

    required_keys = ('heldout_adversarial', 'heldout_combined')
    for key in required_keys:
        assert key in sm, f"Missing switch_metrics.{key}"

    heldout_adversarial = sm['heldout_adversarial']
    heldout_combined = sm['heldout_combined']

    assert isinstance(heldout_adversarial, dict), (
        f"Expected switch_metrics.heldout_adversarial to be a dict, "
        f"got {type(heldout_adversarial).__name__}"
    )
    assert isinstance(heldout_combined, dict), (
        f"Expected switch_metrics.heldout_combined to be a dict, "
        f"got {type(heldout_combined).__name__}"
    )

    assert 'sign_agreement' in heldout_adversarial, (
        "Missing switch_metrics.heldout_adversarial.sign_agreement"
    )
    assert 'sign_agreement' in heldout_combined, (
        "Missing switch_metrics.heldout_combined.sign_agreement"
    )

    assert heldout_adversarial['sign_agreement'] is not None and heldout_adversarial['sign_agreement'] < 0.9, (
        f"switch_metrics.heldout_adversarial.sign_agreement expected < 0.9 "
        f"(adversarial family should break sign boundary), "
        f"got {heldout_adversarial['sign_agreement']}"
    )
    assert heldout_combined['sign_agreement'] is not None and heldout_combined['sign_agreement'] < 0.93, (
        f"switch_metrics.heldout_combined.sign_agreement expected < 0.93 "
        f"(adversarial dilution of combined pool), "
        f"got {heldout_combined['sign_agreement']}"
    )


# ---------------------------------------------------------------------------
# Phase 54 — d) run_phase54_analysis() actually executes and produces correct output
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_phase54_analysis_runs(tmp_path: Path) -> None:
    """run_phase54_analysis must execute without error and return a conforming payload."""
    from cwt.cgt.analysis.phase54_analysis import run_phase54_analysis

    payload = run_phase54_analysis(project_root=_PROJECT_ROOT, output_root=tmp_path)

    assert isinstance(payload, dict), 'run_phase54_analysis must return a dict'
    assert 'switch_metrics' in payload, (
        f"Payload missing 'switch_metrics'; keys: {sorted(payload.keys())}"
    )

    sm = payload['switch_metrics']
    heldout_adversarial = sm['heldout_adversarial']
    heldout_combined = sm['heldout_combined']

    assert heldout_adversarial['sign_agreement'] is not None and heldout_adversarial['sign_agreement'] < 0.9, (
        f"switch_metrics.heldout_adversarial.sign_agreement expected < 0.9, "
        f"got {heldout_adversarial['sign_agreement']}"
    )
    assert heldout_combined['sign_agreement'] is not None and heldout_combined['sign_agreement'] < 0.93, (
        f"switch_metrics.heldout_combined.sign_agreement expected < 0.93, "
        f"got {heldout_combined['sign_agreement']}"
    )
    assert payload['verdict'] == 'adversarial_sign_boundary_exposed', (
        f"Expected verdict 'adversarial_sign_boundary_exposed', "
        f"got {payload['verdict']!r}"
    )
