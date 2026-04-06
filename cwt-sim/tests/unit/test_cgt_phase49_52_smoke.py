"""Smoke tests for CGT Phases 49-52 result artifacts and analysis modules.

Covers:
- Existence and JSON-validity of the Phase 49-52 artifacts.
- Importability of the phase49-52 analysis modules.
- Structural integrity of each artifact (including switch_metrics).
- Execution of run_phaseNN_analysis() to verify correct output.

Phase 49 evaluates the pooled five-positive noisy scaffold rule across five benchmarks
(C, G, H, I, J) without any benchmark-specific coefficient refit.

Phase 50 stress-tests the pooled five-positive noisy scaffold rule with a harder
perturbation family across the same five-benchmark pool.

Phase 51 evaluates the hub-weave topology (benchmark K) under the pooled positive noisy
scaffold rule — the sixth positive noisy scaffold benchmark.

Phase 52 stress-tests benchmark K (hub-weave) with an extreme perturbation family under
the same unchanged pooled scaffold rule.

Results live in:
  cgt_benchmarks/results/benchmark_scaffold_family/ (Phases 49 and 50)
  cgt_benchmarks/results/benchmark_K_hub_weave/ (Phases 51 and 52)
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
_HUB_WEAVE_DIR = _PROJECT_ROOT / 'cgt_benchmarks' / 'results' / 'benchmark_K_hub_weave'

_PHASE49_ARTIFACT = _SCAFFOLD_DIR / 'benchmark_scaffold_phase49_pooled_five_positive_noisy.json'
_PHASE50_ARTIFACT = _SCAFFOLD_DIR / 'benchmark_scaffold_phase50_pooled_five_harder_family.json'
_PHASE51_ARTIFACT = _HUB_WEAVE_DIR / 'benchmark_k_phase51_sixth_positive_noisy.json'
_PHASE52_ARTIFACT = _HUB_WEAVE_DIR / 'benchmark_k_phase52_extreme_perturbation_family.json'


# ---------------------------------------------------------------------------
# Phase 49 — a) Artifact existence and JSON validity
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_phase49_artifact_exists() -> None:
    """The Phase 49 pooled five-positive noisy scaffold artifact must exist and parse as JSON."""
    path = _PHASE49_ARTIFACT
    assert path.exists(), f"Missing: {path}"
    data = json.loads(path.read_text(encoding='utf-8'))
    assert 'switch_metrics' in data, (
        f"Expected 'switch_metrics' key in Phase 49 artifact, "
        f"found keys: {sorted(data.keys())}"
    )
    assert 'verdict' in data, (
        f"Expected 'verdict' key in Phase 49 artifact, "
        f"found keys: {sorted(data.keys())}"
    )
    assert data['verdict'] == 'pooled_five_positive_noisy_scaffold_supported', (
        f"Unexpected verdict value: {data['verdict']!r}"
    )


# ---------------------------------------------------------------------------
# Phase 49 — b) Module importability
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_phase49_importable() -> None:
    """The phase49_analysis module must be importable and expose required callables."""
    mod = importlib.import_module('cwt.cgt.analysis.phase49_analysis')
    assert hasattr(mod, 'run_phase49_analysis'), (
        "phase49_analysis module is missing 'run_phase49_analysis'"
    )


# ---------------------------------------------------------------------------
# Phase 49 — c) Artifact structural integrity
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_phase49_artifact_structure() -> None:
    """The Phase 49 artifact must contain required switch_metrics keys with passing thresholds."""
    path = _PHASE49_ARTIFACT
    assert path.exists(), f"Phase 49 artifact not found: {path}"

    data = json.loads(path.read_text(encoding='utf-8'))
    sm = data['switch_metrics']
    assert isinstance(sm, dict), (
        f"Expected switch_metrics to be a dict, got {type(sm).__name__}"
    )

    required_keys = ('pooled_scaffold', 'benchmark_j')
    for key in required_keys:
        assert key in sm, f"Missing switch_metrics.{key}"

    pooled_scaffold = sm['pooled_scaffold']
    benchmark_j = sm['benchmark_j']

    assert isinstance(pooled_scaffold, dict), (
        f"Expected switch_metrics.pooled_scaffold to be a dict, got {type(pooled_scaffold).__name__}"
    )
    assert isinstance(benchmark_j, dict), (
        f"Expected switch_metrics.benchmark_j to be a dict, got {type(benchmark_j).__name__}"
    )

    assert 'r2' in pooled_scaffold, "Missing switch_metrics.pooled_scaffold.r2"
    assert 'r2' in benchmark_j, "Missing switch_metrics.benchmark_j.r2"

    assert pooled_scaffold['r2'] is not None and pooled_scaffold['r2'] > 0.98, (
        f"switch_metrics.pooled_scaffold.r2 expected > 0.98, "
        f"got {pooled_scaffold['r2']}"
    )
    assert benchmark_j['r2'] is not None and benchmark_j['r2'] > 0.98, (
        f"switch_metrics.benchmark_j.r2 expected > 0.98, "
        f"got {benchmark_j['r2']}"
    )


# ---------------------------------------------------------------------------
# Phase 49 — d) run_phase49_analysis() actually executes and produces correct output
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_phase49_analysis_runs(tmp_path: Path) -> None:
    """run_phase49_analysis must execute without error and return a conforming payload."""
    from cwt.cgt.analysis.phase49_analysis import run_phase49_analysis

    payload = run_phase49_analysis(project_root=_PROJECT_ROOT, output_root=tmp_path)

    assert isinstance(payload, dict), 'run_phase49_analysis must return a dict'
    assert 'switch_metrics' in payload, (
        f"Payload missing 'switch_metrics'; keys: {sorted(payload.keys())}"
    )

    sm = payload['switch_metrics']
    assert isinstance(sm, dict), (
        f"Expected switch_metrics to be a dict, got {type(sm).__name__}"
    )

    pooled_scaffold = sm['pooled_scaffold']
    benchmark_j = sm['benchmark_j']

    assert pooled_scaffold['r2'] is not None and pooled_scaffold['r2'] > 0.98, (
        f"switch_metrics.pooled_scaffold.r2 expected > 0.98, "
        f"got {pooled_scaffold['r2']}"
    )
    assert benchmark_j['r2'] is not None and benchmark_j['r2'] > 0.98, (
        f"switch_metrics.benchmark_j.r2 expected > 0.98, "
        f"got {benchmark_j['r2']}"
    )
    assert payload['verdict'] == 'pooled_five_positive_noisy_scaffold_supported', (
        f"Expected verdict 'pooled_five_positive_noisy_scaffold_supported', "
        f"got {payload['verdict']!r}"
    )


# ---------------------------------------------------------------------------
# Phase 50 — a) Artifact existence and JSON validity
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_phase50_artifact_exists() -> None:
    """The Phase 50 pooled five-harder-family scaffold artifact must exist and parse as JSON."""
    path = _PHASE50_ARTIFACT
    assert path.exists(), f"Missing: {path}"
    data = json.loads(path.read_text(encoding='utf-8'))
    assert 'switch_metrics' in data, (
        f"Expected 'switch_metrics' key in Phase 50 artifact, "
        f"found keys: {sorted(data.keys())}"
    )
    assert 'verdict' in data, (
        f"Expected 'verdict' key in Phase 50 artifact, "
        f"found keys: {sorted(data.keys())}"
    )
    assert data['verdict'] == 'pooled_five_harder_family_supported', (
        f"Unexpected verdict value: {data['verdict']!r}"
    )


# ---------------------------------------------------------------------------
# Phase 50 — b) Module importability
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_phase50_importable() -> None:
    """The phase50_analysis module must be importable and expose required callables."""
    mod = importlib.import_module('cwt.cgt.analysis.phase50_analysis')
    assert hasattr(mod, 'run_phase50_analysis'), (
        "phase50_analysis module is missing 'run_phase50_analysis'"
    )


# ---------------------------------------------------------------------------
# Phase 50 — c) Artifact structural integrity
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_phase50_artifact_structure() -> None:
    """The Phase 50 artifact must contain required switch_metrics keys with passing thresholds."""
    path = _PHASE50_ARTIFACT
    assert path.exists(), f"Phase 50 artifact not found: {path}"

    data = json.loads(path.read_text(encoding='utf-8'))
    sm = data['switch_metrics']
    assert isinstance(sm, dict), (
        f"Expected switch_metrics to be a dict, got {type(sm).__name__}"
    )

    assert 'pooled_harder_family' in sm, "Missing switch_metrics.pooled_harder_family"

    pooled_harder_family = sm['pooled_harder_family']
    assert isinstance(pooled_harder_family, dict), (
        f"Expected switch_metrics.pooled_harder_family to be a dict, "
        f"got {type(pooled_harder_family).__name__}"
    )

    assert 'r2' in pooled_harder_family, "Missing switch_metrics.pooled_harder_family.r2"

    assert pooled_harder_family['r2'] is not None and pooled_harder_family['r2'] > 0.95, (
        f"switch_metrics.pooled_harder_family.r2 expected > 0.95, "
        f"got {pooled_harder_family['r2']}"
    )


# ---------------------------------------------------------------------------
# Phase 50 — d) run_phase50_analysis() actually executes and produces correct output
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_phase50_analysis_runs(tmp_path: Path) -> None:
    """run_phase50_analysis must execute without error and return a conforming payload."""
    from cwt.cgt.analysis.phase50_analysis import run_phase50_analysis

    payload = run_phase50_analysis(project_root=_PROJECT_ROOT, output_root=tmp_path)

    assert isinstance(payload, dict), 'run_phase50_analysis must return a dict'
    assert 'switch_metrics' in payload, (
        f"Payload missing 'switch_metrics'; keys: {sorted(payload.keys())}"
    )

    sm = payload['switch_metrics']
    pooled_harder_family = sm['pooled_harder_family']

    assert pooled_harder_family['r2'] is not None and pooled_harder_family['r2'] > 0.95, (
        f"switch_metrics.pooled_harder_family.r2 expected > 0.95, "
        f"got {pooled_harder_family['r2']}"
    )
    assert payload['verdict'] == 'pooled_five_harder_family_supported', (
        f"Expected verdict 'pooled_five_harder_family_supported', "
        f"got {payload['verdict']!r}"
    )


# ---------------------------------------------------------------------------
# Phase 51 — a) Artifact existence and JSON validity
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_phase51_artifact_exists() -> None:
    """The Phase 51 sixth positive noisy scaffold artifact must exist and parse as JSON."""
    path = _PHASE51_ARTIFACT
    assert path.exists(), f"Missing: {path}"
    data = json.loads(path.read_text(encoding='utf-8'))
    assert 'switch_metrics' in data, (
        f"Expected 'switch_metrics' key in Phase 51 artifact, "
        f"found keys: {sorted(data.keys())}"
    )
    assert 'verdict' in data, (
        f"Expected 'verdict' key in Phase 51 artifact, "
        f"found keys: {sorted(data.keys())}"
    )
    assert data['verdict'] == 'sixth_positive_noisy_scaffold_supported', (
        f"Unexpected verdict value: {data['verdict']!r}"
    )


# ---------------------------------------------------------------------------
# Phase 51 — b) Module importability
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_phase51_importable() -> None:
    """The phase51_analysis module must be importable and expose required callables."""
    mod = importlib.import_module('cwt.cgt.analysis.phase51_analysis')
    assert hasattr(mod, 'run_phase51_analysis'), (
        "phase51_analysis module is missing 'run_phase51_analysis'"
    )


# ---------------------------------------------------------------------------
# Phase 51 — c) Artifact structural integrity
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_phase51_artifact_structure() -> None:
    """The Phase 51 artifact must contain required switch_metrics keys with passing thresholds."""
    path = _PHASE51_ARTIFACT
    assert path.exists(), f"Phase 51 artifact not found: {path}"

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
# Phase 51 — d) run_phase51_analysis() actually executes and produces correct output
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_phase51_analysis_runs(tmp_path: Path) -> None:
    """run_phase51_analysis must execute without error and return a conforming payload."""
    from cwt.cgt.analysis.phase51_analysis import run_phase51_analysis

    payload = run_phase51_analysis(project_root=_PROJECT_ROOT, output_root=tmp_path)

    assert isinstance(payload, dict), 'run_phase51_analysis must return a dict'
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
    assert payload['verdict'] == 'sixth_positive_noisy_scaffold_supported', (
        f"Expected verdict 'sixth_positive_noisy_scaffold_supported', "
        f"got {payload['verdict']!r}"
    )


# ---------------------------------------------------------------------------
# Phase 52 — a) Artifact existence and JSON validity
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_phase52_artifact_exists() -> None:
    """The Phase 52 extreme perturbation family artifact must exist and parse as JSON."""
    path = _PHASE52_ARTIFACT
    assert path.exists(), f"Missing: {path}"
    data = json.loads(path.read_text(encoding='utf-8'))
    assert 'switch_metrics' in data, (
        f"Expected 'switch_metrics' key in Phase 52 artifact, "
        f"found keys: {sorted(data.keys())}"
    )
    assert 'verdict' in data, (
        f"Expected 'verdict' key in Phase 52 artifact, "
        f"found keys: {sorted(data.keys())}"
    )
    assert data['verdict'] == 'extreme_family_supportive_under_pooled_five', (
        f"Unexpected verdict value: {data['verdict']!r}"
    )


# ---------------------------------------------------------------------------
# Phase 52 — b) Module importability
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_phase52_importable() -> None:
    """The phase52_analysis module must be importable and expose required callables."""
    mod = importlib.import_module('cwt.cgt.analysis.phase52_analysis')
    assert hasattr(mod, 'run_phase52_analysis'), (
        "phase52_analysis module is missing 'run_phase52_analysis'"
    )


# ---------------------------------------------------------------------------
# Phase 52 — c) Artifact structural integrity
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_phase52_artifact_structure() -> None:
    """The Phase 52 artifact must contain required switch_metrics keys with passing thresholds."""
    path = _PHASE52_ARTIFACT
    assert path.exists(), f"Phase 52 artifact not found: {path}"

    data = json.loads(path.read_text(encoding='utf-8'))
    sm = data['switch_metrics']
    assert isinstance(sm, dict), (
        f"Expected switch_metrics to be a dict, got {type(sm).__name__}"
    )

    required_keys = ('heldout_extreme', 'heldout_combined')
    for key in required_keys:
        assert key in sm, f"Missing switch_metrics.{key}"

    heldout_extreme = sm['heldout_extreme']
    heldout_combined = sm['heldout_combined']

    assert isinstance(heldout_extreme, dict), (
        f"Expected switch_metrics.heldout_extreme to be a dict, got {type(heldout_extreme).__name__}"
    )
    assert isinstance(heldout_combined, dict), (
        f"Expected switch_metrics.heldout_combined to be a dict, got {type(heldout_combined).__name__}"
    )

    assert 'r2' in heldout_extreme, "Missing switch_metrics.heldout_extreme.r2"
    assert 'r2' in heldout_combined, "Missing switch_metrics.heldout_combined.r2"

    assert heldout_extreme['r2'] is not None and heldout_extreme['r2'] > 0.90, (
        f"switch_metrics.heldout_extreme.r2 expected > 0.90, "
        f"got {heldout_extreme['r2']}"
    )
    assert heldout_combined['r2'] is not None and heldout_combined['r2'] > 0.92, (
        f"switch_metrics.heldout_combined.r2 expected > 0.92, "
        f"got {heldout_combined['r2']}"
    )


# ---------------------------------------------------------------------------
# Phase 52 — d) run_phase52_analysis() actually executes and produces correct output
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_phase52_analysis_runs(tmp_path: Path) -> None:
    """run_phase52_analysis must execute without error and return a conforming payload."""
    from cwt.cgt.analysis.phase52_analysis import run_phase52_analysis

    payload = run_phase52_analysis(project_root=_PROJECT_ROOT, output_root=tmp_path)

    assert isinstance(payload, dict), 'run_phase52_analysis must return a dict'
    assert 'switch_metrics' in payload, (
        f"Payload missing 'switch_metrics'; keys: {sorted(payload.keys())}"
    )

    sm = payload['switch_metrics']
    heldout_extreme = sm['heldout_extreme']
    heldout_combined = sm['heldout_combined']

    assert heldout_extreme['r2'] is not None and heldout_extreme['r2'] > 0.90, (
        f"switch_metrics.heldout_extreme.r2 expected > 0.90, "
        f"got {heldout_extreme['r2']}"
    )
    assert heldout_combined['r2'] is not None and heldout_combined['r2'] > 0.92, (
        f"switch_metrics.heldout_combined.r2 expected > 0.92, "
        f"got {heldout_combined['r2']}"
    )
    assert payload['verdict'] == 'extreme_family_supportive_under_pooled_five', (
        f"Expected verdict 'extreme_family_supportive_under_pooled_five', "
        f"got {payload['verdict']!r}"
    )
