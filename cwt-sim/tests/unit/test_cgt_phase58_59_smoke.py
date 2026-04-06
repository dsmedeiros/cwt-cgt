"""Smoke tests for CGT Phases 58-59 result artifacts and analysis modules.

Covers:
- Existence and JSON-validity of the Phase 58-59 artifacts.
- Importability of the phase58-59 analysis modules.
- Structural integrity of each artifact.
- Execution of run_phaseNN_analysis() to verify correct output.

Phase 58 stress-tests the pooled seven-positive noisy scaffold rule (from
Phase 55) against a second adversarial perturbation family on benchmark I
(nonring ladder). The adversarial family is expected to produce a partial
failure: combined_metrics r2 < 0.5 and adversarial_family_metrics
sign_agreement < 0.9.

Phase 59 applies a generator sign correction (same correction class as
benchmark L Phase 57) to the Phase 58 adversarial result on benchmark I.
combined_metrics r2 and combined_metrics sign_agreement must both strictly
improve over the Phase 58 baseline.

Results live in:
  cgt_benchmarks/results/benchmark_I_nonring_ladder/ (Phases 58 and 59)
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
_LADDER_DIR = _PROJECT_ROOT / 'cgt_benchmarks' / 'results' / 'benchmark_I_nonring_ladder'

_PHASE58_ARTIFACT = _LADDER_DIR / 'benchmark_i_phase58_second_adversarial_family.json'
_PHASE59_ARTIFACT = _LADDER_DIR / 'benchmark_i_phase59_generator_sign_correction_transfer.json'


# ---------------------------------------------------------------------------
# Phase 58 — a) Artifact existence and JSON validity
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_phase58_artifact_exists() -> None:
    """The Phase 58 second adversarial family artifact must exist and parse as JSON."""
    path = _PHASE58_ARTIFACT
    assert path.exists(), f"Missing: {path}"
    data = json.loads(path.read_text(encoding='utf-8'))
    assert 'combined_metrics' in data, (
        f"Expected 'combined_metrics' key in Phase 58 artifact, "
        f"found keys: {sorted(data.keys())}"
    )
    assert 'verdict' in data, (
        f"Expected 'verdict' key in Phase 58 artifact, "
        f"found keys: {sorted(data.keys())}"
    )
    assert data['verdict'] == 'second_adversarial_boundary_detected', (
        f"Unexpected verdict value: {data['verdict']!r}"
    )


# ---------------------------------------------------------------------------
# Phase 58 — b) Module importability
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_phase58_importable() -> None:
    """The phase58_analysis module must be importable and expose required callables."""
    mod = importlib.import_module('cwt.cgt.analysis.phase58_analysis')
    assert hasattr(mod, 'run_phase58_analysis'), (
        "phase58_analysis module is missing 'run_phase58_analysis'"
    )


# ---------------------------------------------------------------------------
# Phase 58 — c) Artifact structural integrity
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_phase58_artifact_structure() -> None:
    """The Phase 58 artifact must show partial failure (combined r2 < 0.5, adv sign < 0.9)."""
    path = _PHASE58_ARTIFACT
    assert path.exists(), f"Phase 58 artifact not found: {path}"

    data = json.loads(path.read_text(encoding='utf-8'))

    assert 'combined_metrics' in data, "Missing combined_metrics"
    assert 'adversarial_family_metrics' in data, "Missing adversarial_family_metrics"

    combined = data['combined_metrics']
    adversarial = data['adversarial_family_metrics']

    assert 'r2' in combined, "Missing combined_metrics.r2"
    assert 'sign_agreement' in adversarial, "Missing adversarial_family_metrics.sign_agreement"

    assert combined['r2'] is not None and combined['r2'] > 0.4, (
        f"combined_metrics.r2 expected > 0.4 (base family still fits), "
        f"got {combined['r2']}"
    )
    assert combined['r2'] < 0.5, (
        f"combined_metrics.r2 expected < 0.5 (adversarial family degrades fit), "
        f"got {combined['r2']}"
    )
    assert adversarial['sign_agreement'] is not None and adversarial['sign_agreement'] < 0.9, (
        f"adversarial_family_metrics.sign_agreement expected < 0.9 "
        f"(adversarial perturbation degrades sign agreement), "
        f"got {adversarial['sign_agreement']}"
    )


# ---------------------------------------------------------------------------
# Phase 58 — d) run_phase58_analysis() actually executes and produces correct output
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_phase58_analysis_runs(tmp_path: Path) -> None:
    """run_phase58_analysis must execute without error and return a conforming payload."""
    from cwt.cgt.analysis.phase58_analysis import run_phase58_analysis

    payload = run_phase58_analysis(project_root=_PROJECT_ROOT, output_root=tmp_path)

    assert isinstance(payload, dict), 'run_phase58_analysis must return a dict'
    assert 'combined_metrics' in payload, (
        f"Payload missing 'combined_metrics'; keys: {sorted(payload.keys())}"
    )
    assert 'adversarial_family_metrics' in payload, (
        f"Payload missing 'adversarial_family_metrics'; keys: {sorted(payload.keys())}"
    )

    combined = payload['combined_metrics']
    adversarial = payload['adversarial_family_metrics']

    assert combined['r2'] is not None and combined['r2'] > 0.4, (
        f"combined_metrics.r2 expected > 0.4, got {combined['r2']}"
    )
    assert combined['r2'] < 0.5, (
        f"combined_metrics.r2 expected < 0.5 (adversarial family degrades fit), "
        f"got {combined['r2']}"
    )
    assert adversarial['sign_agreement'] is not None and adversarial['sign_agreement'] < 0.9, (
        f"adversarial_family_metrics.sign_agreement expected < 0.9, "
        f"got {adversarial['sign_agreement']}"
    )
    assert payload['verdict'] == 'second_adversarial_boundary_detected', (
        f"Expected verdict 'second_adversarial_boundary_detected', "
        f"got {payload['verdict']!r}"
    )


# ---------------------------------------------------------------------------
# Phase 59 — a) Artifact existence and JSON validity
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_phase59_artifact_exists() -> None:
    """The Phase 59 generator sign correction transfer artifact must exist and parse as JSON."""
    path = _PHASE59_ARTIFACT
    assert path.exists(), f"Missing: {path}"
    data = json.loads(path.read_text(encoding='utf-8'))
    assert 'combined_metrics' in data, (
        f"Expected 'combined_metrics' key in Phase 59 artifact, "
        f"found keys: {sorted(data.keys())}"
    )
    assert 'verdict' in data, (
        f"Expected 'verdict' key in Phase 59 artifact, "
        f"found keys: {sorted(data.keys())}"
    )
    assert data['verdict'] == 'generator_sign_correction_transfer_supported', (
        f"Unexpected verdict value: {data['verdict']!r}"
    )


# ---------------------------------------------------------------------------
# Phase 59 — b) Module importability
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_phase59_importable() -> None:
    """The phase59_analysis module must be importable and expose required callables."""
    mod = importlib.import_module('cwt.cgt.analysis.phase59_analysis')
    assert hasattr(mod, 'run_phase59_analysis'), (
        "phase59_analysis module is missing 'run_phase59_analysis'"
    )


# ---------------------------------------------------------------------------
# Phase 59 — c) Artifact structural integrity
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_phase59_artifact_structure() -> None:
    """The Phase 59 artifact must contain combined_metrics with r2 and sign_agreement."""
    path = _PHASE59_ARTIFACT
    assert path.exists(), f"Phase 59 artifact not found: {path}"

    data = json.loads(path.read_text(encoding='utf-8'))

    assert 'combined_metrics' in data, "Missing combined_metrics"

    combined = data['combined_metrics']
    assert 'r2' in combined, "Missing combined_metrics.r2"
    assert 'sign_agreement' in combined, "Missing combined_metrics.sign_agreement"

    assert isinstance(combined['r2'], (int, float)), (
        f"Expected combined_metrics.r2 to be numeric, got {type(combined['r2']).__name__}"
    )
    assert isinstance(combined['sign_agreement'], (int, float)), (
        f"Expected combined_metrics.sign_agreement to be numeric, "
        f"got {type(combined['sign_agreement']).__name__}"
    )

    assert combined['r2'] > 0.75, (
        f"combined_metrics.r2 expected > 0.75 (generator sign correction improves fit), "
        f"got {combined['r2']}"
    )
    assert combined['sign_agreement'] > 0.95, (
        f"combined_metrics.sign_agreement expected > 0.95 (generator sign correction restores agreement), "
        f"got {combined['sign_agreement']}"
    )


# ---------------------------------------------------------------------------
# Phase 59 — d) run_phase59_analysis() actually executes and produces correct output
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_phase59_analysis_runs(tmp_path: Path) -> None:
    """run_phase59_analysis must execute without error and return a conforming payload."""
    from cwt.cgt.analysis.phase59_analysis import run_phase59_analysis

    payload = run_phase59_analysis(project_root=_PROJECT_ROOT, output_root=tmp_path)

    assert isinstance(payload, dict), 'run_phase59_analysis must return a dict'
    assert 'combined_metrics' in payload, (
        f"Payload missing 'combined_metrics'; keys: {sorted(payload.keys())}"
    )

    combined = payload['combined_metrics']
    assert 'r2' in combined, (
        f"combined_metrics missing 'r2'; keys: {sorted(combined.keys())}"
    )
    assert 'sign_agreement' in combined, (
        f"combined_metrics missing 'sign_agreement'; keys: {sorted(combined.keys())}"
    )
    assert payload['verdict'] == 'generator_sign_correction_transfer_supported', (
        f"Expected verdict 'generator_sign_correction_transfer_supported', "
        f"got {payload['verdict']!r}"
    )


# ---------------------------------------------------------------------------
# Phase 59 — e) Comparative: Phase 59 must improve over Phase 58
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_phase59_improves_over_phase58() -> None:
    """Phase 59 combined_metrics r2 and sign_agreement must both exceed Phase 58 values."""
    p58_data = json.loads(_PHASE58_ARTIFACT.read_text(encoding='utf-8'))
    p59_data = json.loads(_PHASE59_ARTIFACT.read_text(encoding='utf-8'))

    p58_r2 = p58_data['combined_metrics']['r2']
    p59_r2 = p59_data['combined_metrics']['r2']
    assert p59_r2 > p58_r2, (
        f"Phase 59 combined_metrics.r2 ({p59_r2}) must exceed "
        f"Phase 58 combined_metrics.r2 ({p58_r2}); "
        "generator sign correction should improve fit"
    )
    assert (p59_r2 - p58_r2) > 0.2, (
        f"Phase 59 combined_metrics.r2 improvement ({p59_r2 - p58_r2:.4f}) must exceed 0.2; "
        f"Phase 59 r2={p59_r2}, Phase 58 r2={p58_r2}"
    )

    p58_sign = p58_data['combined_metrics']['sign_agreement']
    p59_sign = p59_data['combined_metrics']['sign_agreement']
    assert p59_sign > p58_sign, (
        f"Phase 59 combined_metrics.sign_agreement ({p59_sign}) must exceed "
        f"Phase 58 combined_metrics.sign_agreement ({p58_sign}); "
        "generator sign correction should improve sign agreement"
    )
