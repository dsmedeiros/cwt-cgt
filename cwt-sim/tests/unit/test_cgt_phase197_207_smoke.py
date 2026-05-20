"""Smoke tests for CGT Phases 197-207 result artifacts and analysis modules.

Covers:
- Existence and JSON-validity of the Phase 197-207 artifacts.
- Importability of the phase analysis modules.
- Structural integrity of each artifact (top-level keys present).
- Metric thresholds derived from bundle reports and pinned to observed JSON values.
- Execution of run_phaseN_analysis() to verify correct output.

Benchmark layout:
  benchmark_AG_irregular_hidden_censor/   -- Phases 197, 198
  benchmark_GG_windowed_sparse_release/   -- Phases 199, 200
  benchmark_scaffold_family/              -- Phases 201, 202, 203, 204, 205, 206, 207

Phases with loaders (11):
  197, 198, 199, 200, 201, 202, 203, 204, 205, 206, 207.

Phases 197-207 constitute the "thirteenth-bridge and tensor-law v5" block
(bundle v7.9).
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
_AG_DIR = _PROJECT_ROOT / 'cgt_benchmarks' / 'results' / 'benchmark_AG_irregular_hidden_censor'
_GG_DIR = _PROJECT_ROOT / 'cgt_benchmarks' / 'results' / 'benchmark_GG_windowed_sparse_release'
_SCAFFOLD_DIR = _PROJECT_ROOT / 'cgt_benchmarks' / 'results' / 'benchmark_scaffold_family'

_P197 = _AG_DIR / 'benchmark_ag_phase197_thirteenth_bridge_positive.json'
_P198 = _AG_DIR / 'benchmark_ag_phase198_bridge_adversarial_tensor_v4.json'
_P199 = _GG_DIR / 'benchmark_gg_phase199_seventh_less_synthetic_positive.json'
_P200 = _GG_DIR / 'benchmark_gg_phase200_seventh_less_synthetic_adversarial.json'
_P201 = _SCAFFOLD_DIR / 'benchmark_scaffold_phase201_bridge_holdout_expanded_v2.json'
_P202 = _SCAFFOLD_DIR / 'benchmark_scaffold_phase202_bridge_correction_v4_vs_minimal_expanded.json'
_P203 = _SCAFFOLD_DIR / 'benchmark_scaffold_phase203_bridge_tensor_geometry_law_v5.json'
_P204 = _SCAFFOLD_DIR / 'benchmark_scaffold_phase204_pooled_thirteen_bridge_positive.json'
_P205 = _SCAFFOLD_DIR / 'benchmark_scaffold_phase205_pooled_thirteen_bridge_adversarial.json'
_P206 = _SCAFFOLD_DIR / 'benchmark_scaffold_phase206_bridge_boundary_refresh_v6.json'
_P207 = _SCAFFOLD_DIR / 'benchmark_scaffold_phase207_bridge_externalization_readiness_v3.json'


# ===========================================================================
# Phase 197 -- Thirteenth bridge positive (benchmark AG irregular hidden censor)
# ===========================================================================


@pytest.mark.unit
def test_phase197_artifact_exists() -> None:
    """Phase 197 artifact must exist on disk."""
    assert _P197.exists(), f"Missing: {_P197}"


@pytest.mark.unit
def test_phase197_artifact_json_valid() -> None:
    """Phase 197 artifact must be valid JSON."""
    assert _P197.exists(), f"Missing: {_P197}"
    data = json.loads(_P197.read_text(encoding='utf-8'))
    assert isinstance(data, dict), "Phase 197 artifact root must be a dict"


@pytest.mark.unit
def test_phase197_artifact_structure() -> None:
    """Phase 197 artifact must contain required top-level keys."""
    data = json.loads(_P197.read_text(encoding='utf-8'))
    for key in ('phase', 'benchmark', 'metrics'):
        assert key in data, f"Phase 197 artifact missing key: {key!r}"
    for subkey in ('r2', 'sign'):
        assert subkey in data['metrics'], f"Phase 197 metrics missing key: {subkey!r}"


@pytest.mark.unit
def test_phase197_metric_thresholds() -> None:
    """Phase 197 metrics must meet thirteenth-bridge acceptance bounds.

    Report: switch-slice held-out R2 = 0.9264; corr = 0.9861; sign = 1.0.
    """
    data = json.loads(_P197.read_text(encoding='utf-8'))
    assert data['metrics']['r2'] >= 0.92, (
        f"Phase 197 r2 expected >= 0.92, got {data['metrics']['r2']}"
    )
    assert data['metrics']['sign'] >= 0.99, (
        f"Phase 197 sign expected >= 0.99, got {data['metrics']['sign']}"
    )
    assert data['benchmark'] == 'AG_irregular_hidden_censor', (
        f"Unexpected benchmark: {data['benchmark']!r}"
    )


@pytest.mark.unit
def test_phase197_loader_importable() -> None:
    """phase197_analysis module must be importable and expose run_phase197_analysis."""
    mod = importlib.import_module('cwt.cgt.analysis.phase197_analysis')
    assert hasattr(mod, 'run_phase197_analysis'), (
        "phase197_analysis missing 'run_phase197_analysis'"
    )


@pytest.mark.unit
def test_phase197_loader_runs(tmp_path: Path) -> None:
    """run_phase197_analysis must return a non-empty dict."""
    from cwt.cgt.analysis.phase197_analysis import run_phase197_analysis

    payload = run_phase197_analysis(project_root=_PROJECT_ROOT, output_root=tmp_path)
    assert isinstance(payload, dict), 'run_phase197_analysis must return a dict'
    assert payload, 'run_phase197_analysis returned empty dict'
    assert payload['metrics']['r2'] >= 0.92


# ===========================================================================
# Phase 198 -- Thirteenth bridge adversarial tensor v4 (benchmark AG irregular hidden censor)
# ===========================================================================


@pytest.mark.unit
def test_phase198_artifact_exists() -> None:
    """Phase 198 artifact must exist on disk."""
    assert _P198.exists(), f"Missing: {_P198}"


@pytest.mark.unit
def test_phase198_artifact_json_valid() -> None:
    """Phase 198 artifact must be valid JSON."""
    assert _P198.exists(), f"Missing: {_P198}"
    data = json.loads(_P198.read_text(encoding='utf-8'))
    assert isinstance(data, dict), "Phase 198 artifact root must be a dict"


@pytest.mark.unit
def test_phase198_artifact_structure() -> None:
    """Phase 198 artifact must contain required top-level keys."""
    data = json.loads(_P198.read_text(encoding='utf-8'))
    for key in ('phase', 'raw', 'corrected', 'correction'):
        assert key in data, f"Phase 198 artifact missing key: {key!r}"
    for subkey in ('combined_r2', 'sign_agreement'):
        assert subkey in data['raw'], f"Phase 198 raw missing key: {subkey!r}"
    for subkey in ('combined_r2', 'sign_agreement'):
        assert subkey in data['corrected'], f"Phase 198 corrected missing key: {subkey!r}"


@pytest.mark.unit
def test_phase198_metric_thresholds() -> None:
    """Phase 198 corrected metrics must meet adversarial correction acceptance bounds.

    Report: raw combined_r2 = 0.5412; corrected combined_r2 = 0.8978;
    corrected sign_agreement = 0.9722.
    """
    data = json.loads(_P198.read_text(encoding='utf-8'))
    assert data['raw']['combined_r2'] < 0.60, (
        f"Phase 198 raw combined_r2 expected < 0.60, got {data['raw']['combined_r2']}"
    )
    assert data['corrected']['combined_r2'] >= 0.88, (
        f"Phase 198 corrected combined_r2 expected >= 0.88, "
        f"got {data['corrected']['combined_r2']}"
    )
    assert data['corrected']['sign_agreement'] >= 0.96, (
        f"Phase 198 corrected sign_agreement expected >= 0.96, "
        f"got {data['corrected']['sign_agreement']}"
    )


@pytest.mark.unit
def test_phase198_loader_importable() -> None:
    """phase198_analysis module must be importable and expose run_phase198_analysis."""
    mod = importlib.import_module('cwt.cgt.analysis.phase198_analysis')
    assert hasattr(mod, 'run_phase198_analysis'), (
        "phase198_analysis missing 'run_phase198_analysis'"
    )


@pytest.mark.unit
def test_phase198_loader_runs(tmp_path: Path) -> None:
    """run_phase198_analysis must return a non-empty dict."""
    from cwt.cgt.analysis.phase198_analysis import run_phase198_analysis

    payload = run_phase198_analysis(project_root=_PROJECT_ROOT, output_root=tmp_path)
    assert isinstance(payload, dict), 'run_phase198_analysis must return a dict'
    assert payload, 'run_phase198_analysis returned empty dict'
    assert payload['corrected']['combined_r2'] >= 0.88


# ===========================================================================
# Phase 199 -- Seventh less-synthetic positive (benchmark GG windowed sparse release)
# ===========================================================================


@pytest.mark.unit
def test_phase199_artifact_exists() -> None:
    """Phase 199 artifact must exist on disk."""
    assert _P199.exists(), f"Missing: {_P199}"


@pytest.mark.unit
def test_phase199_artifact_json_valid() -> None:
    """Phase 199 artifact must be valid JSON."""
    assert _P199.exists(), f"Missing: {_P199}"
    data = json.loads(_P199.read_text(encoding='utf-8'))
    assert isinstance(data, dict), "Phase 199 artifact root must be a dict"


@pytest.mark.unit
def test_phase199_artifact_structure() -> None:
    """Phase 199 artifact must contain required top-level keys."""
    data = json.loads(_P199.read_text(encoding='utf-8'))
    for key in ('phase', 'benchmark', 'metrics'):
        assert key in data, f"Phase 199 artifact missing key: {key!r}"
    for subkey in ('r2', 'sign'):
        assert subkey in data['metrics'], f"Phase 199 metrics missing key: {subkey!r}"


@pytest.mark.unit
def test_phase199_metric_thresholds() -> None:
    """Phase 199 less-synthetic positive R2 >= 0.88; sign >= 0.97.

    Report: held-out R2 = 0.8987; corr = 0.9732; sign = 0.9861.
    """
    data = json.loads(_P199.read_text(encoding='utf-8'))
    assert data['metrics']['r2'] >= 0.88, (
        f"Phase 199 r2 expected >= 0.88, got {data['metrics']['r2']}"
    )
    assert data['metrics']['sign'] >= 0.97, (
        f"Phase 199 sign expected >= 0.97, got {data['metrics']['sign']}"
    )
    assert data['benchmark'] == 'GG_windowed_sparse_release', (
        f"Unexpected benchmark: {data['benchmark']!r}"
    )


@pytest.mark.unit
def test_phase199_loader_importable() -> None:
    """phase199_analysis module must be importable and expose run_phase199_analysis."""
    mod = importlib.import_module('cwt.cgt.analysis.phase199_analysis')
    assert hasattr(mod, 'run_phase199_analysis'), (
        "phase199_analysis missing 'run_phase199_analysis'"
    )


@pytest.mark.unit
def test_phase199_loader_runs(tmp_path: Path) -> None:
    """run_phase199_analysis must return a non-empty dict."""
    from cwt.cgt.analysis.phase199_analysis import run_phase199_analysis

    payload = run_phase199_analysis(project_root=_PROJECT_ROOT, output_root=tmp_path)
    assert isinstance(payload, dict), 'run_phase199_analysis must return a dict'
    assert payload, 'run_phase199_analysis returned empty dict'
    assert payload['metrics']['r2'] >= 0.88


# ===========================================================================
# Phase 200 -- Seventh less-synthetic adversarial (benchmark GG windowed sparse release)
# ===========================================================================


@pytest.mark.unit
def test_phase200_artifact_exists() -> None:
    """Phase 200 artifact must exist on disk."""
    assert _P200.exists(), f"Missing: {_P200}"


@pytest.mark.unit
def test_phase200_artifact_json_valid() -> None:
    """Phase 200 artifact must be valid JSON."""
    assert _P200.exists(), f"Missing: {_P200}"
    data = json.loads(_P200.read_text(encoding='utf-8'))
    assert isinstance(data, dict), "Phase 200 artifact root must be a dict"


@pytest.mark.unit
def test_phase200_artifact_structure() -> None:
    """Phase 200 artifact must contain required top-level keys."""
    data = json.loads(_P200.read_text(encoding='utf-8'))
    for key in ('phase', 'benchmark', 'raw', 'corrected', 'correction'):
        assert key in data, f"Phase 200 artifact missing key: {key!r}"
    for subkey in ('combined_r2', 'sign_agreement'):
        assert subkey in data['raw'], f"Phase 200 raw missing key: {subkey!r}"
    for subkey in ('combined_r2', 'sign_agreement'):
        assert subkey in data['corrected'], f"Phase 200 corrected missing key: {subkey!r}"


@pytest.mark.unit
def test_phase200_metric_thresholds() -> None:
    """Phase 200 corrected combined_r2 >= 0.82; corrected sign_agreement >= 0.94.

    Report: raw combined_r2 = 0.4179; corrected combined_r2 = 0.8364;
    corrected sign_agreement = 0.9514.
    """
    data = json.loads(_P200.read_text(encoding='utf-8'))
    assert data['raw']['combined_r2'] < 0.45, (
        f"Phase 200 raw combined_r2 expected < 0.45, got {data['raw']['combined_r2']}"
    )
    assert data['corrected']['combined_r2'] >= 0.82, (
        f"Phase 200 corrected combined_r2 expected >= 0.82, "
        f"got {data['corrected']['combined_r2']}"
    )
    assert data['corrected']['sign_agreement'] >= 0.94, (
        f"Phase 200 corrected sign_agreement expected >= 0.94, "
        f"got {data['corrected']['sign_agreement']}"
    )


@pytest.mark.unit
def test_phase200_loader_importable() -> None:
    """phase200_analysis module must be importable and expose run_phase200_analysis."""
    mod = importlib.import_module('cwt.cgt.analysis.phase200_analysis')
    assert hasattr(mod, 'run_phase200_analysis'), (
        "phase200_analysis missing 'run_phase200_analysis'"
    )


@pytest.mark.unit
def test_phase200_loader_runs(tmp_path: Path) -> None:
    """run_phase200_analysis must return a non-empty dict."""
    from cwt.cgt.analysis.phase200_analysis import run_phase200_analysis

    payload = run_phase200_analysis(project_root=_PROJECT_ROOT, output_root=tmp_path)
    assert isinstance(payload, dict), 'run_phase200_analysis must return a dict'
    assert payload, 'run_phase200_analysis returned empty dict'
    assert payload['corrected']['combined_r2'] >= 0.82


# ===========================================================================
# Phase 201 -- Bridge LOO holdout expanded v2 (benchmark scaffold family)
# ===========================================================================


@pytest.mark.unit
def test_phase201_artifact_exists() -> None:
    """Phase 201 artifact must exist on disk."""
    assert _P201.exists(), f"Missing: {_P201}"


@pytest.mark.unit
def test_phase201_artifact_json_valid() -> None:
    """Phase 201 artifact must be valid JSON."""
    assert _P201.exists(), f"Missing: {_P201}"
    data = json.loads(_P201.read_text(encoding='utf-8'))
    assert isinstance(data, dict), "Phase 201 artifact root must be a dict"


@pytest.mark.unit
def test_phase201_artifact_structure() -> None:
    """Phase 201 artifact must contain required top-level keys."""
    data = json.loads(_P201.read_text(encoding='utf-8'))
    for key in ('phase', 'benchmarks', 'metrics'):
        assert key in data, f"Phase 201 artifact missing key: {key!r}"
    assert isinstance(data['benchmarks'], list), (
        "Phase 201 benchmarks must be a list"
    )
    for subkey in ('mean_combined_r2', 'min_combined_r2', 'max_combined_r2',
                   'weakest_benchmark'):
        assert subkey in data['metrics'], f"Phase 201 metrics missing key: {subkey!r}"


@pytest.mark.unit
def test_phase201_metric_thresholds() -> None:
    """Phase 201 mean LOO held-out combined_r2 >= 0.88; benchmark count = 18.

    Report: mean_combined_r2 = 0.8871; weakest = BB_sensor_gap; 18 benchmarks.
    """
    data = json.loads(_P201.read_text(encoding='utf-8'))
    assert data['metrics']['mean_combined_r2'] >= 0.88, (
        f"Phase 201 mean_combined_r2 expected >= 0.88, "
        f"got {data['metrics']['mean_combined_r2']}"
    )
    assert len(data['benchmarks']) == 18, (
        f"Phase 201 expected 18 benchmarks, got {len(data['benchmarks'])}"
    )
    assert data['metrics']['weakest_benchmark'] == 'BB_sensor_gap', (
        f"Phase 201 expected weakest = BB_sensor_gap, "
        f"got {data['metrics']['weakest_benchmark']!r}"
    )


@pytest.mark.unit
def test_phase201_loader_importable() -> None:
    """phase201_analysis module must be importable and expose run_phase201_analysis."""
    mod = importlib.import_module('cwt.cgt.analysis.phase201_analysis')
    assert hasattr(mod, 'run_phase201_analysis'), (
        "phase201_analysis missing 'run_phase201_analysis'"
    )


@pytest.mark.unit
def test_phase201_loader_runs(tmp_path: Path) -> None:
    """run_phase201_analysis must return a non-empty dict."""
    from cwt.cgt.analysis.phase201_analysis import run_phase201_analysis

    payload = run_phase201_analysis(project_root=_PROJECT_ROOT, output_root=tmp_path)
    assert isinstance(payload, dict), 'run_phase201_analysis must return a dict'
    assert payload, 'run_phase201_analysis returned empty dict'
    assert payload['metrics']['mean_combined_r2'] >= 0.88


# ===========================================================================
# Phase 202 -- Bridge correction v4 vs minimal expanded (benchmark scaffold family)
# ===========================================================================


@pytest.mark.unit
def test_phase202_artifact_exists() -> None:
    """Phase 202 artifact must exist on disk."""
    assert _P202.exists(), f"Missing: {_P202}"


@pytest.mark.unit
def test_phase202_artifact_json_valid() -> None:
    """Phase 202 artifact must be valid JSON."""
    assert _P202.exists(), f"Missing: {_P202}"
    data = json.loads(_P202.read_text(encoding='utf-8'))
    assert isinstance(data, dict), "Phase 202 artifact root must be a dict"


@pytest.mark.unit
def test_phase202_artifact_structure() -> None:
    """Phase 202 artifact must contain required top-level keys."""
    data = json.loads(_P202.read_text(encoding='utf-8'))
    for key in ('phase', 'minimal_rule', 'tensor_geometry_v4', 'winner'):
        assert key in data, f"Phase 202 artifact missing key: {key!r}"
    assert 'combined_r2' in data['minimal_rule'], (
        "Phase 202 minimal_rule missing 'combined_r2'"
    )
    assert 'combined_r2' in data['tensor_geometry_v4'], (
        "Phase 202 tensor_geometry_v4 missing 'combined_r2'"
    )


@pytest.mark.unit
def test_phase202_metric_thresholds() -> None:
    """Phase 202 tensor_geometry_v4 must outperform minimal_rule.

    Report: minimal combined_r2 = 0.8832; tensor v4 combined_r2 = 0.8964;
    winner = tensor_geometry_v4.
    """
    data = json.loads(_P202.read_text(encoding='utf-8'))
    assert data['tensor_geometry_v4']['combined_r2'] > data['minimal_rule']['combined_r2'], (
        "Phase 202 tensor_geometry_v4 must exceed minimal_rule combined_r2"
    )
    assert data['tensor_geometry_v4']['combined_r2'] >= 0.89, (
        f"Phase 202 tensor_geometry_v4 combined_r2 expected >= 0.89, "
        f"got {data['tensor_geometry_v4']['combined_r2']}"
    )
    assert data['winner'] == 'tensor_geometry_v4', (
        f"Phase 202 expected winner = tensor_geometry_v4, got {data['winner']!r}"
    )


@pytest.mark.unit
def test_phase202_loader_importable() -> None:
    """phase202_analysis module must be importable and expose run_phase202_analysis."""
    mod = importlib.import_module('cwt.cgt.analysis.phase202_analysis')
    assert hasattr(mod, 'run_phase202_analysis'), (
        "phase202_analysis missing 'run_phase202_analysis'"
    )


@pytest.mark.unit
def test_phase202_loader_runs(tmp_path: Path) -> None:
    """run_phase202_analysis must return a non-empty dict."""
    from cwt.cgt.analysis.phase202_analysis import run_phase202_analysis

    payload = run_phase202_analysis(project_root=_PROJECT_ROOT, output_root=tmp_path)
    assert isinstance(payload, dict), 'run_phase202_analysis must return a dict'
    assert payload, 'run_phase202_analysis returned empty dict'
    assert payload['tensor_geometry_v4']['combined_r2'] >= 0.89


# ===========================================================================
# Phase 203 -- Bridge tensor geometry law v5 (benchmark scaffold family)
# ===========================================================================


@pytest.mark.unit
def test_phase203_artifact_exists() -> None:
    """Phase 203 artifact must exist on disk."""
    assert _P203.exists(), f"Missing: {_P203}"


@pytest.mark.unit
def test_phase203_artifact_json_valid() -> None:
    """Phase 203 artifact must be valid JSON."""
    assert _P203.exists(), f"Missing: {_P203}"
    data = json.loads(_P203.read_text(encoding='utf-8'))
    assert isinstance(data, dict), "Phase 203 artifact root must be a dict"


@pytest.mark.unit
def test_phase203_artifact_structure() -> None:
    """Phase 203 artifact must contain required top-level keys."""
    data = json.loads(_P203.read_text(encoding='utf-8'))
    for key in ('phase', 'candidate', 'raw', 'prior_corrected', 'corrected'):
        assert key in data, f"Phase 203 artifact missing key: {key!r}"
    assert 'combined_r2' in data['raw'], "Phase 203 raw missing 'combined_r2'"
    assert 'combined_r2' in data['prior_corrected'], (
        "Phase 203 prior_corrected missing 'combined_r2'"
    )
    for subkey in ('combined_r2', 'sign_agreement'):
        assert subkey in data['corrected'], f"Phase 203 corrected missing key: {subkey!r}"


@pytest.mark.unit
def test_phase203_metric_thresholds() -> None:
    """Phase 203 v5 corrected combined_r2 >= 0.92; corrected sign_agreement >= 0.97.

    Report: raw combined_r2 = 0.5611; prior_corrected combined_r2 = 0.9217;
    v5 corrected combined_r2 = 0.9231; v5 corrected sign_agreement = 0.979.
    """
    data = json.loads(_P203.read_text(encoding='utf-8'))
    assert data['corrected']['combined_r2'] >= 0.92, (
        f"Phase 203 corrected combined_r2 expected >= 0.92, "
        f"got {data['corrected']['combined_r2']}"
    )
    assert data['corrected']['sign_agreement'] >= 0.97, (
        f"Phase 203 corrected sign_agreement expected >= 0.97, "
        f"got {data['corrected']['sign_agreement']}"
    )
    assert data['corrected']['combined_r2'] >= data['prior_corrected']['combined_r2'], (
        "Phase 203 v5 corrected must be >= prior_corrected combined_r2"
    )


@pytest.mark.unit
def test_phase203_loader_importable() -> None:
    """phase203_analysis module must be importable and expose run_phase203_analysis."""
    mod = importlib.import_module('cwt.cgt.analysis.phase203_analysis')
    assert hasattr(mod, 'run_phase203_analysis'), (
        "phase203_analysis missing 'run_phase203_analysis'"
    )


@pytest.mark.unit
def test_phase203_loader_runs(tmp_path: Path) -> None:
    """run_phase203_analysis must return a non-empty dict."""
    from cwt.cgt.analysis.phase203_analysis import run_phase203_analysis

    payload = run_phase203_analysis(project_root=_PROJECT_ROOT, output_root=tmp_path)
    assert isinstance(payload, dict), 'run_phase203_analysis must return a dict'
    assert payload, 'run_phase203_analysis returned empty dict'
    assert payload['corrected']['combined_r2'] >= 0.92


# ===========================================================================
# Phase 204 -- Pooled thirteen-bridge positive (benchmark scaffold family)
# ===========================================================================


@pytest.mark.unit
def test_phase204_artifact_exists() -> None:
    """Phase 204 artifact must exist on disk."""
    assert _P204.exists(), f"Missing: {_P204}"


@pytest.mark.unit
def test_phase204_artifact_json_valid() -> None:
    """Phase 204 artifact must be valid JSON."""
    assert _P204.exists(), f"Missing: {_P204}"
    data = json.loads(_P204.read_text(encoding='utf-8'))
    assert isinstance(data, dict), "Phase 204 artifact root must be a dict"


@pytest.mark.unit
def test_phase204_artifact_structure() -> None:
    """Phase 204 artifact must contain required top-level keys."""
    data = json.loads(_P204.read_text(encoding='utf-8'))
    for key in ('phase', 'rule', 'metrics', 'benchmark_count'):
        assert key in data, f"Phase 204 artifact missing key: {key!r}"
    for subkey in ('combined_r2', 'sign'):
        assert subkey in data['metrics'], f"Phase 204 metrics missing key: {subkey!r}"


@pytest.mark.unit
def test_phase204_metric_thresholds() -> None:
    """Phase 204 pooled thirteen-bridge positive combined_r2 >= 0.94; sign >= 0.99.

    Report: combined_r2 = 0.9417; corr = 0.9877; sign = 0.9959; benchmark_count = 13.
    """
    data = json.loads(_P204.read_text(encoding='utf-8'))
    assert data['metrics']['combined_r2'] >= 0.94, (
        f"Phase 204 combined_r2 expected >= 0.94, got {data['metrics']['combined_r2']}"
    )
    assert data['metrics']['sign'] >= 0.99, (
        f"Phase 204 sign expected >= 0.99, got {data['metrics']['sign']}"
    )
    assert data['benchmark_count'] == 13, (
        f"Phase 204 expected benchmark_count = 13, got {data['benchmark_count']}"
    )


@pytest.mark.unit
def test_phase204_loader_importable() -> None:
    """phase204_analysis module must be importable and expose run_phase204_analysis."""
    mod = importlib.import_module('cwt.cgt.analysis.phase204_analysis')
    assert hasattr(mod, 'run_phase204_analysis'), (
        "phase204_analysis missing 'run_phase204_analysis'"
    )


@pytest.mark.unit
def test_phase204_loader_runs(tmp_path: Path) -> None:
    """run_phase204_analysis must return a non-empty dict."""
    from cwt.cgt.analysis.phase204_analysis import run_phase204_analysis

    payload = run_phase204_analysis(project_root=_PROJECT_ROOT, output_root=tmp_path)
    assert isinstance(payload, dict), 'run_phase204_analysis must return a dict'
    assert payload, 'run_phase204_analysis returned empty dict'
    assert payload['metrics']['combined_r2'] >= 0.94


# ===========================================================================
# Phase 205 -- Pooled thirteen-bridge adversarial (benchmark scaffold family)
# ===========================================================================


@pytest.mark.unit
def test_phase205_artifact_exists() -> None:
    """Phase 205 artifact must exist on disk."""
    assert _P205.exists(), f"Missing: {_P205}"


@pytest.mark.unit
def test_phase205_artifact_json_valid() -> None:
    """Phase 205 artifact must be valid JSON."""
    assert _P205.exists(), f"Missing: {_P205}"
    data = json.loads(_P205.read_text(encoding='utf-8'))
    assert isinstance(data, dict), "Phase 205 artifact root must be a dict"


@pytest.mark.unit
def test_phase205_artifact_structure() -> None:
    """Phase 205 artifact must contain required top-level keys."""
    data = json.loads(_P205.read_text(encoding='utf-8'))
    for key in ('phase', 'rule', 'raw', 'corrected', 'correction', 'benchmark_count'):
        assert key in data, f"Phase 205 artifact missing key: {key!r}"
    for subkey in ('combined_r2', 'sign_agreement'):
        assert subkey in data['raw'], f"Phase 205 raw missing key: {subkey!r}"
    for subkey in ('combined_r2', 'sign_agreement'):
        assert subkey in data['corrected'], f"Phase 205 corrected missing key: {subkey!r}"


@pytest.mark.unit
def test_phase205_metric_thresholds() -> None:
    """Phase 205 corrected combined_r2 >= 0.91; corrected sign_agreement >= 0.97.

    Report: raw combined_r2 = 0.5611; corrected combined_r2 = 0.9162;
    corrected sign_agreement = 0.9751; benchmark_count = 13.
    """
    data = json.loads(_P205.read_text(encoding='utf-8'))
    assert data['raw']['combined_r2'] < 0.60, (
        f"Phase 205 raw combined_r2 expected < 0.60, got {data['raw']['combined_r2']}"
    )
    assert data['corrected']['combined_r2'] >= 0.91, (
        f"Phase 205 corrected combined_r2 expected >= 0.91, "
        f"got {data['corrected']['combined_r2']}"
    )
    assert data['corrected']['sign_agreement'] >= 0.97, (
        f"Phase 205 corrected sign_agreement expected >= 0.97, "
        f"got {data['corrected']['sign_agreement']}"
    )
    assert data['benchmark_count'] == 13, (
        f"Phase 205 expected benchmark_count = 13, got {data['benchmark_count']}"
    )


@pytest.mark.unit
def test_phase205_loader_importable() -> None:
    """phase205_analysis module must be importable and expose run_phase205_analysis."""
    mod = importlib.import_module('cwt.cgt.analysis.phase205_analysis')
    assert hasattr(mod, 'run_phase205_analysis'), (
        "phase205_analysis missing 'run_phase205_analysis'"
    )


@pytest.mark.unit
def test_phase205_loader_runs(tmp_path: Path) -> None:
    """run_phase205_analysis must return a non-empty dict."""
    from cwt.cgt.analysis.phase205_analysis import run_phase205_analysis

    payload = run_phase205_analysis(project_root=_PROJECT_ROOT, output_root=tmp_path)
    assert isinstance(payload, dict), 'run_phase205_analysis must return a dict'
    assert payload, 'run_phase205_analysis returned empty dict'
    assert payload['corrected']['combined_r2'] >= 0.91


# ===========================================================================
# Phase 206 -- Bridge boundary refresh v6 (benchmark scaffold family)
# ===========================================================================


@pytest.mark.unit
def test_phase206_artifact_exists() -> None:
    """Phase 206 artifact must exist on disk."""
    assert _P206.exists(), f"Missing: {_P206}"


@pytest.mark.unit
def test_phase206_artifact_json_valid() -> None:
    """Phase 206 artifact must be valid JSON."""
    assert _P206.exists(), f"Missing: {_P206}"
    data = json.loads(_P206.read_text(encoding='utf-8'))
    assert isinstance(data, dict), "Phase 206 artifact root must be a dict"


@pytest.mark.unit
def test_phase206_artifact_structure() -> None:
    """Phase 206 artifact must contain required top-level keys."""
    data = json.loads(_P206.read_text(encoding='utf-8'))
    for key in ('phase', 'positive_transfer_band', 'bridge_adversarial_corrected_band',
                'bridge_holdout_mean', 'weakest_bridge_benchmark'):
        assert key in data, f"Phase 206 artifact missing key: {key!r}"
    assert (isinstance(data['positive_transfer_band'], list)
            and len(data['positive_transfer_band']) == 2), (
        "Phase 206 positive_transfer_band must be a two-element list"
    )
    assert (isinstance(data['bridge_adversarial_corrected_band'], list)
            and len(data['bridge_adversarial_corrected_band']) == 2), (
        "Phase 206 bridge_adversarial_corrected_band must be a two-element list"
    )


@pytest.mark.unit
def test_phase206_metric_thresholds() -> None:
    """Phase 206 boundary bands must reflect thirteen-bridge sweep acceptance bounds.

    Report: positive_transfer_band = [0.8987, 0.9981];
    bridge_adversarial_corrected_band = [0.8364, 0.9162];
    bridge_holdout_mean = 0.8871.
    """
    data = json.loads(_P206.read_text(encoding='utf-8'))
    pos_lo, pos_hi = data['positive_transfer_band']
    adv_lo, adv_hi = data['bridge_adversarial_corrected_band']
    assert pos_lo >= 0.89, (
        f"Phase 206 positive_transfer_band lower expected >= 0.89, got {pos_lo}"
    )
    assert pos_hi >= 0.99, (
        f"Phase 206 positive_transfer_band upper expected >= 0.99, got {pos_hi}"
    )
    assert adv_lo >= 0.83, (
        f"Phase 206 bridge_adversarial_corrected_band lower expected >= 0.83, got {adv_lo}"
    )
    assert adv_hi >= 0.91, (
        f"Phase 206 bridge_adversarial_corrected_band upper expected >= 0.91, got {adv_hi}"
    )
    assert data['bridge_holdout_mean'] >= 0.88, (
        f"Phase 206 bridge_holdout_mean expected >= 0.88, got {data['bridge_holdout_mean']}"
    )


@pytest.mark.unit
def test_phase206_loader_importable() -> None:
    """phase206_analysis module must be importable and expose run_phase206_analysis."""
    mod = importlib.import_module('cwt.cgt.analysis.phase206_analysis')
    assert hasattr(mod, 'run_phase206_analysis'), (
        "phase206_analysis missing 'run_phase206_analysis'"
    )


@pytest.mark.unit
def test_phase206_loader_runs(tmp_path: Path) -> None:
    """run_phase206_analysis must return a non-empty dict."""
    from cwt.cgt.analysis.phase206_analysis import run_phase206_analysis

    payload = run_phase206_analysis(project_root=_PROJECT_ROOT, output_root=tmp_path)
    assert isinstance(payload, dict), 'run_phase206_analysis must return a dict'
    assert payload, 'run_phase206_analysis returned empty dict'
    pos_lo, pos_hi = payload['positive_transfer_band']
    assert pos_hi >= 0.99


# ===========================================================================
# Phase 207 -- Bridge externalization readiness v3 (benchmark scaffold family)
# ===========================================================================


@pytest.mark.unit
def test_phase207_artifact_exists() -> None:
    """Phase 207 artifact must exist on disk."""
    assert _P207.exists(), f"Missing: {_P207}"


@pytest.mark.unit
def test_phase207_artifact_json_valid() -> None:
    """Phase 207 artifact must be valid JSON."""
    assert _P207.exists(), f"Missing: {_P207}"
    data = json.loads(_P207.read_text(encoding='utf-8'))
    assert isinstance(data, dict), "Phase 207 artifact root must be a dict"


@pytest.mark.unit
def test_phase207_artifact_structure() -> None:
    """Phase 207 artifact must contain required top-level keys."""
    data = json.loads(_P207.read_text(encoding='utf-8'))
    for key in ('phase', 'readiness_score', 'readiness_bands', 'blocking_items'):
        assert key in data, f"Phase 207 artifact missing key: {key!r}"
    for subkey in ('coherent_core', 'noisy_scaffold', 'bridge_lane'):
        assert subkey in data['readiness_bands'], (
            f"Phase 207 readiness_bands missing key: {subkey!r}"
        )
    assert isinstance(data['blocking_items'], list), (
        "Phase 207 blocking_items must be a list"
    )


@pytest.mark.unit
def test_phase207_metric_thresholds() -> None:
    """Phase 207 readiness score and bands must meet v3 acceptance bounds.

    Report: readiness_score = 0.71; coherent_core = 0.89;
    noisy_scaffold = 0.81; bridge_lane = 0.63.
    """
    data = json.loads(_P207.read_text(encoding='utf-8'))
    assert data['readiness_score'] >= 0.70, (
        f"Phase 207 readiness_score expected >= 0.70, got {data['readiness_score']}"
    )
    assert data['readiness_bands']['coherent_core'] >= 0.88, (
        f"Phase 207 coherent_core expected >= 0.88, "
        f"got {data['readiness_bands']['coherent_core']}"
    )
    assert data['readiness_bands']['noisy_scaffold'] >= 0.80, (
        f"Phase 207 noisy_scaffold expected >= 0.80, "
        f"got {data['readiness_bands']['noisy_scaffold']}"
    )
    assert len(data['blocking_items']) >= 1, (
        "Phase 207 blocking_items must be non-empty"
    )


@pytest.mark.unit
def test_phase207_loader_importable() -> None:
    """phase207_analysis module must be importable and expose run_phase207_analysis."""
    mod = importlib.import_module('cwt.cgt.analysis.phase207_analysis')
    assert hasattr(mod, 'run_phase207_analysis'), (
        "phase207_analysis missing 'run_phase207_analysis'"
    )


@pytest.mark.unit
def test_phase207_loader_runs(tmp_path: Path) -> None:
    """run_phase207_analysis must return a non-empty dict."""
    from cwt.cgt.analysis.phase207_analysis import run_phase207_analysis

    payload = run_phase207_analysis(project_root=_PROJECT_ROOT, output_root=tmp_path)
    assert isinstance(payload, dict), 'run_phase207_analysis must return a dict'
    assert payload, 'run_phase207_analysis returned empty dict'
    assert payload['readiness_score'] >= 0.70
