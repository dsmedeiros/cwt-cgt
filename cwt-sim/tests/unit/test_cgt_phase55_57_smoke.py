"""Smoke tests for CGT Phases 55-57 result artifacts and analysis modules.

Covers:
- Existence and JSON-validity of the Phase 55-57 artifacts.
- Importability of the phase55-57 analysis modules.
- Structural integrity of each artifact.
- Execution of run_phaseNN_analysis() to verify correct output.

Phase 55 evaluates the pooled seven-positive noisy scaffold rule (benchmarks
C, G, H, I, J, K, L) without any benchmark-specific coefficient refit.

Phase 56 stress-tests the pooled seven-positive noisy scaffold rule (from
Phase 55) against a pooled seven-adversarial perturbation family on benchmark
L (fork-mesh). The adversarial family is expected to produce a partial failure:
combined_r2 < 0.35 and combined_sign_agreement < 0.95.

Phase 57 applies a generator sign-robustness correction to the Phase 55 rule
and re-evaluates benchmark L. combined_r2 and combined_sign_agreement must
both strictly improve over the Phase 56 baseline.

Results live in:
  cgt_benchmarks/results/benchmark_scaffold_family/ (Phase 55)
  cgt_benchmarks/results/benchmark_L_fork_mesh/ (Phases 56 and 57)
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
_FORK_MESH_DIR = _PROJECT_ROOT / 'cgt_benchmarks' / 'results' / 'benchmark_L_fork_mesh'

_PHASE55_ARTIFACT = _SCAFFOLD_DIR / 'benchmark_scaffold_phase55_pooled_seven_positive_noisy.json'
_PHASE56_ARTIFACT = _FORK_MESH_DIR / 'benchmark_l_phase56_pooled_seven_adversarial.json'
_PHASE57_ARTIFACT = _FORK_MESH_DIR / 'benchmark_l_phase57_generator_sign_robustness_correction.json'


# ---------------------------------------------------------------------------
# Phase 55 — a) Artifact existence and JSON validity
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_phase55_artifact_exists() -> None:
    """The Phase 55 pooled seven-positive noisy scaffold artifact must exist and parse as JSON."""
    path = _PHASE55_ARTIFACT
    assert path.exists(), f"Missing: {path}"
    data = json.loads(path.read_text(encoding='utf-8'))
    assert 'pooled_positive_rule' in data, (
        f"Expected 'pooled_positive_rule' key in Phase 55 artifact, "
        f"found keys: {sorted(data.keys())}"
    )
    assert 'verdict' in data, (
        f"Expected 'verdict' key in Phase 55 artifact, "
        f"found keys: {sorted(data.keys())}"
    )
    assert data['verdict'] == 'pooled_seven_positive_noisy_supported', (
        f"Unexpected verdict value: {data['verdict']!r}"
    )


# ---------------------------------------------------------------------------
# Phase 55 — b) Module importability
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_phase55_importable() -> None:
    """The phase55_analysis module must be importable and expose required callables."""
    mod = importlib.import_module('cwt.cgt.analysis.phase55_analysis')
    assert hasattr(mod, 'run_phase55_analysis'), (
        "phase55_analysis module is missing 'run_phase55_analysis'"
    )


# ---------------------------------------------------------------------------
# Phase 55 — c) Artifact structural integrity
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_phase55_artifact_structure() -> None:
    """The Phase 55 artifact must contain pooled_positive_rule with passing thresholds."""
    path = _PHASE55_ARTIFACT
    assert path.exists(), f"Phase 55 artifact not found: {path}"

    data = json.loads(path.read_text(encoding='utf-8'))
    ppr = data['pooled_positive_rule']
    assert isinstance(ppr, dict), (
        f"Expected pooled_positive_rule to be a dict, got {type(ppr).__name__}"
    )

    assert 'heldout_combined_r2' in ppr, "Missing pooled_positive_rule.heldout_combined_r2"

    assert ppr['heldout_combined_r2'] is not None and ppr['heldout_combined_r2'] > 0.98, (
        f"pooled_positive_rule.heldout_combined_r2 expected > 0.98, "
        f"got {ppr['heldout_combined_r2']}"
    )


# ---------------------------------------------------------------------------
# Phase 55 — d) run_phase55_analysis() actually executes and produces correct output
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_phase55_analysis_runs(tmp_path: Path) -> None:
    """run_phase55_analysis must execute without error and return a conforming payload."""
    from cwt.cgt.analysis.phase55_analysis import run_phase55_analysis

    payload = run_phase55_analysis(project_root=_PROJECT_ROOT, output_root=tmp_path)

    assert isinstance(payload, dict), 'run_phase55_analysis must return a dict'
    assert 'pooled_positive_rule' in payload, (
        f"Payload missing 'pooled_positive_rule'; keys: {sorted(payload.keys())}"
    )

    ppr = payload['pooled_positive_rule']
    assert isinstance(ppr, dict), (
        f"Expected pooled_positive_rule to be a dict, got {type(ppr).__name__}"
    )

    assert ppr['heldout_combined_r2'] is not None and ppr['heldout_combined_r2'] > 0.98, (
        f"pooled_positive_rule.heldout_combined_r2 expected > 0.98, "
        f"got {ppr['heldout_combined_r2']}"
    )
    assert payload['verdict'] == 'pooled_seven_positive_noisy_supported', (
        f"Expected verdict 'pooled_seven_positive_noisy_supported', "
        f"got {payload['verdict']!r}"
    )


# ---------------------------------------------------------------------------
# Phase 56 — a) Artifact existence and JSON validity
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_phase56_artifact_exists() -> None:
    """The Phase 56 pooled seven-adversarial artifact must exist and parse as JSON."""
    path = _PHASE56_ARTIFACT
    assert path.exists(), f"Missing: {path}"
    data = json.loads(path.read_text(encoding='utf-8'))
    assert 'combined_r2' in data, (
        f"Expected 'combined_r2' key in Phase 56 artifact, "
        f"found keys: {sorted(data.keys())}"
    )
    assert 'verdict' in data, (
        f"Expected 'verdict' key in Phase 56 artifact, "
        f"found keys: {sorted(data.keys())}"
    )
    assert data['verdict'] == 'pooled_seven_adversarial_boundary_partial', (
        f"Unexpected verdict value: {data['verdict']!r}"
    )


# ---------------------------------------------------------------------------
# Phase 56 — b) Module importability
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_phase56_importable() -> None:
    """The phase56_analysis module must be importable and expose required callables."""
    mod = importlib.import_module('cwt.cgt.analysis.phase56_analysis')
    assert hasattr(mod, 'run_phase56_analysis'), (
        "phase56_analysis module is missing 'run_phase56_analysis'"
    )


# ---------------------------------------------------------------------------
# Phase 56 — c) Artifact structural integrity
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_phase56_artifact_structure() -> None:
    """The Phase 56 artifact must show partial failure (combined_r2 < 0.35, sign < 0.95)."""
    path = _PHASE56_ARTIFACT
    assert path.exists(), f"Phase 56 artifact not found: {path}"

    data = json.loads(path.read_text(encoding='utf-8'))

    assert 'combined_r2' in data, "Missing combined_r2"
    assert 'combined_sign_agreement' in data, "Missing combined_sign_agreement"

    assert data['combined_r2'] is not None and data['combined_r2'] < 0.35, (
        f"combined_r2 expected < 0.35 (adversarial boundary partial failure), "
        f"got {data['combined_r2']}"
    )
    assert data['combined_sign_agreement'] is not None and data['combined_sign_agreement'] < 0.95, (
        f"combined_sign_agreement expected < 0.95 (adversarial dilution), "
        f"got {data['combined_sign_agreement']}"
    )


# ---------------------------------------------------------------------------
# Phase 56 — d) run_phase56_analysis() actually executes and produces correct output
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_phase56_analysis_runs(tmp_path: Path) -> None:
    """run_phase56_analysis must execute without error and return a conforming payload."""
    from cwt.cgt.analysis.phase56_analysis import run_phase56_analysis

    payload = run_phase56_analysis(project_root=_PROJECT_ROOT, output_root=tmp_path)

    assert isinstance(payload, dict), 'run_phase56_analysis must return a dict'
    assert 'combined_r2' in payload, (
        f"Payload missing 'combined_r2'; keys: {sorted(payload.keys())}"
    )
    assert 'combined_sign_agreement' in payload, (
        f"Payload missing 'combined_sign_agreement'; keys: {sorted(payload.keys())}"
    )

    assert payload['combined_r2'] is not None and payload['combined_r2'] < 0.35, (
        f"combined_r2 expected < 0.35, got {payload['combined_r2']}"
    )
    assert payload['combined_sign_agreement'] is not None and payload['combined_sign_agreement'] < 0.95, (
        f"combined_sign_agreement expected < 0.95, got {payload['combined_sign_agreement']}"
    )
    assert payload['verdict'] == 'pooled_seven_adversarial_boundary_partial', (
        f"Expected verdict 'pooled_seven_adversarial_boundary_partial', "
        f"got {payload['verdict']!r}"
    )


# ---------------------------------------------------------------------------
# Phase 57 — a) Artifact existence and JSON validity
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_phase57_artifact_exists() -> None:
    """The Phase 57 generator sign-robustness correction artifact must exist and parse as JSON."""
    path = _PHASE57_ARTIFACT
    assert path.exists(), f"Missing: {path}"
    data = json.loads(path.read_text(encoding='utf-8'))
    assert 'combined_r2' in data, (
        f"Expected 'combined_r2' key in Phase 57 artifact, "
        f"found keys: {sorted(data.keys())}"
    )
    assert 'verdict' in data, (
        f"Expected 'verdict' key in Phase 57 artifact, "
        f"found keys: {sorted(data.keys())}"
    )
    assert data['verdict'] == 'generator_sign_robustness_correction_partially_supported', (
        f"Unexpected verdict value: {data['verdict']!r}"
    )


# ---------------------------------------------------------------------------
# Phase 57 — b) Module importability
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_phase57_importable() -> None:
    """The phase57_analysis module must be importable and expose required callables."""
    mod = importlib.import_module('cwt.cgt.analysis.phase57_analysis')
    assert hasattr(mod, 'run_phase57_analysis'), (
        "phase57_analysis module is missing 'run_phase57_analysis'"
    )


# ---------------------------------------------------------------------------
# Phase 57 — c) Artifact structural integrity
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_phase57_artifact_structure() -> None:
    """The Phase 57 artifact must contain combined_r2 and combined_sign_agreement."""
    path = _PHASE57_ARTIFACT
    assert path.exists(), f"Phase 57 artifact not found: {path}"

    data = json.loads(path.read_text(encoding='utf-8'))

    assert 'combined_r2' in data, "Missing combined_r2"
    assert 'combined_sign_agreement' in data, "Missing combined_sign_agreement"

    assert isinstance(data['combined_r2'], (int, float)), (
        f"Expected combined_r2 to be numeric, got {type(data['combined_r2']).__name__}"
    )
    assert isinstance(data['combined_sign_agreement'], (int, float)), (
        f"Expected combined_sign_agreement to be numeric, "
        f"got {type(data['combined_sign_agreement']).__name__}"
    )

    assert data['combined_r2'] > 0.6, (
        f"combined_r2 expected > 0.6 (generator sign-robustness correction improves fit), "
        f"got {data['combined_r2']}"
    )


# ---------------------------------------------------------------------------
# Phase 57 — d) run_phase57_analysis() actually executes and produces correct output
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_phase57_analysis_runs(tmp_path: Path) -> None:
    """run_phase57_analysis must execute without error and return a conforming payload."""
    from cwt.cgt.analysis.phase57_analysis import run_phase57_analysis

    payload = run_phase57_analysis(project_root=_PROJECT_ROOT, output_root=tmp_path)

    assert isinstance(payload, dict), 'run_phase57_analysis must return a dict'
    assert 'combined_r2' in payload, (
        f"Payload missing 'combined_r2'; keys: {sorted(payload.keys())}"
    )
    assert 'combined_sign_agreement' in payload, (
        f"Payload missing 'combined_sign_agreement'; keys: {sorted(payload.keys())}"
    )
    assert payload['verdict'] == 'generator_sign_robustness_correction_partially_supported', (
        f"Expected verdict 'generator_sign_robustness_correction_partially_supported', "
        f"got {payload['verdict']!r}"
    )


# ---------------------------------------------------------------------------
# Phase 57 — e) Comparative: Phase 57 must improve over Phase 56
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_phase57_improves_over_phase56() -> None:
    """Phase 57 combined_r2 and combined_sign_agreement must both exceed Phase 56 values."""
    p56_data = json.loads(_PHASE56_ARTIFACT.read_text(encoding='utf-8'))
    p57_data = json.loads(_PHASE57_ARTIFACT.read_text(encoding='utf-8'))

    p56_r2 = p56_data['combined_r2']
    p57_r2 = p57_data['combined_r2']
    assert p57_r2 > p56_r2, (
        f"Phase 57 combined_r2 ({p57_r2}) must exceed Phase 56 combined_r2 ({p56_r2}); "
        "generator sign-robustness correction should improve fit"
    )
    assert (p57_r2 - p56_r2) > 0.3, (
        f"Phase 57 combined_r2 improvement ({p57_r2 - p56_r2:.4f}) must exceed 0.3; "
        f"Phase 57 r2={p57_r2}, Phase 56 r2={p56_r2}"
    )

    p56_sign = p56_data['combined_sign_agreement']
    p57_sign = p57_data['combined_sign_agreement']
    assert p57_sign > p56_sign, (
        f"Phase 57 combined_sign_agreement ({p57_sign}) must exceed "
        f"Phase 56 combined_sign_agreement ({p56_sign}); "
        "generator sign-robustness correction should improve sign agreement"
    )
