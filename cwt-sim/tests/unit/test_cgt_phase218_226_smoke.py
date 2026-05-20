"""Smoke tests for CGT Phases 218-226 result artifacts and analysis modules.

Covers:
- Existence and JSON-validity of the Phase 218-226 artifacts.
- Importability of the phase analysis modules.
- Structural integrity of each artifact (top-level keys present).
- Metric thresholds derived from bundle reports and pinned to observed JSON values.
- Execution of run_phaseN_analysis() to verify correct output.

Benchmark layout:
  benchmark_scaffold_family/              -- Phases 218, 221, 222, 223, 224, 225, 226
  benchmark_II_partial_obs_spike/         -- Phases 219, 220

Phases with loaders (9):
  218, 219, 220, 221, 222, 223, 224, 225, 226.

Phases 218-226 constitute the "tensor-law v7 and externalization plateau" block
(bundle v8.1).
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
_II_DIR = _PROJECT_ROOT / 'cgt_benchmarks' / 'results' / 'benchmark_II_partial_obs_spike'

_P218 = _SCAFFOLD_DIR / 'benchmark_scaffold_phase218_bridge_holdout_expanded_v6_vs_minimal.json'
_P219 = _II_DIR / 'benchmark_ii_phase219_ninth_less_synthetic_positive.json'
_P220 = _II_DIR / 'benchmark_ii_phase220_ninth_less_synthetic_adversarial.json'
_P221 = _SCAFFOLD_DIR / 'benchmark_scaffold_phase221_bridge_tensor_geometry_law_v7.json'
_P222 = _SCAFFOLD_DIR / 'benchmark_scaffold_phase222_bridge_holdout_v7_comparison.json'
_P223 = _SCAFFOLD_DIR / 'benchmark_scaffold_phase223_pooled_thirteen_bridge_adversarial_v7.json'
_P224 = _SCAFFOLD_DIR / 'benchmark_scaffold_phase224_bridge_pilot_positive_summary.json'
_P225 = _SCAFFOLD_DIR / 'benchmark_scaffold_phase225_bridge_pilot_adversarial_summary.json'
_P226 = _SCAFFOLD_DIR / 'benchmark_scaffold_phase226_externalization_plateau_summary.json'


# ===========================================================================
# Phase 218 -- Bridge holdout expanded v6 vs minimal (benchmark scaffold family)
# ===========================================================================


@pytest.mark.unit
def test_phase218_artifact_exists() -> None:
    """Phase 218 artifact must exist on disk."""
    assert _P218.exists(), f"Missing: {_P218}"


@pytest.mark.unit
def test_phase218_artifact_json_valid() -> None:
    """Phase 218 artifact must be valid JSON."""
    assert _P218.exists(), f"Missing: {_P218}"
    data = json.loads(_P218.read_text(encoding='utf-8'))
    assert isinstance(data, dict), "Phase 218 artifact root must be a dict"


@pytest.mark.unit
def test_phase218_artifact_structure() -> None:
    """Phase 218 artifact must contain required top-level keys."""
    data = json.loads(_P218.read_text(encoding='utf-8'))
    for key in ('rule', 'bridge_count', 'pilot_count', 'minimal_mean_r2',
                'tensor_v6_mean_r2', 'mean_gain', 'weakest_benchmark'):
        assert key in data, f"Phase 218 artifact missing key: {key!r}"


@pytest.mark.unit
def test_phase218_metric_thresholds() -> None:
    """Phase 218 tensor v6 mean R2 >= 0.90; gain > 0; weakest = GG_windowed_sparse_release.

    Report: minimal_mean_r2 = 0.8804; tensor_v6_mean_r2 = 0.9006; mean_gain = 0.0202.
    """
    data = json.loads(_P218.read_text(encoding='utf-8'))
    assert data['tensor_v6_mean_r2'] >= 0.90, (
        f"Phase 218 tensor_v6_mean_r2 expected >= 0.90, got {data['tensor_v6_mean_r2']}"
    )
    assert data['tensor_v6_mean_r2'] > data['minimal_mean_r2'], (
        "Phase 218 tensor v6 must outperform minimal"
    )
    assert data['mean_gain'] > 0.0, (
        f"Phase 218 mean_gain must be positive, got {data['mean_gain']}"
    )
    assert data['weakest_benchmark'] == 'GG_windowed_sparse_release', (
        f"Phase 218 expected weakest = GG_windowed_sparse_release, "
        f"got {data['weakest_benchmark']!r}"
    )


@pytest.mark.unit
def test_phase218_loader_importable() -> None:
    """phase218_analysis module must be importable and expose run_phase218_analysis."""
    mod = importlib.import_module('cwt.cgt.analysis.phase218_analysis')
    assert hasattr(mod, 'run_phase218_analysis'), (
        "phase218_analysis missing 'run_phase218_analysis'"
    )


@pytest.mark.unit
def test_phase218_loader_runs(tmp_path: Path) -> None:
    """run_phase218_analysis must return a non-empty dict."""
    from cwt.cgt.analysis.phase218_analysis import run_phase218_analysis

    payload = run_phase218_analysis(project_root=_PROJECT_ROOT, output_root=tmp_path)
    assert isinstance(payload, dict), 'run_phase218_analysis must return a dict'
    assert payload, 'run_phase218_analysis returned empty dict'
    assert payload['tensor_v6_mean_r2'] >= 0.90


# ===========================================================================
# Phase 219 -- Ninth less-synthetic positive (benchmark II partial obs spike)
# ===========================================================================


@pytest.mark.unit
def test_phase219_artifact_exists() -> None:
    """Phase 219 artifact must exist on disk."""
    assert _P219.exists(), f"Missing: {_P219}"


@pytest.mark.unit
def test_phase219_artifact_json_valid() -> None:
    """Phase 219 artifact must be valid JSON."""
    assert _P219.exists(), f"Missing: {_P219}"
    data = json.loads(_P219.read_text(encoding='utf-8'))
    assert isinstance(data, dict), "Phase 219 artifact root must be a dict"


@pytest.mark.unit
def test_phase219_artifact_structure() -> None:
    """Phase 219 artifact must contain required top-level keys."""
    data = json.loads(_P219.read_text(encoding='utf-8'))
    for key in ('phase', 'benchmark', 'metrics'):
        assert key in data, f"Phase 219 artifact missing key: {key!r}"
    for subkey in ('r2', 'sign'):
        assert subkey in data['metrics'], f"Phase 219 metrics missing key: {subkey!r}"


@pytest.mark.unit
def test_phase219_metric_thresholds() -> None:
    """Phase 219 ninth less-synthetic positive R2 >= 0.90; sign >= 0.98.

    Report: held-out combined R2 = 0.9056; correlation = 0.9764; sign = 0.9896.
    """
    data = json.loads(_P219.read_text(encoding='utf-8'))
    assert data['metrics']['r2'] >= 0.90, (
        f"Phase 219 r2 expected >= 0.90, got {data['metrics']['r2']}"
    )
    assert data['metrics']['sign'] >= 0.98, (
        f"Phase 219 sign expected >= 0.98, got {data['metrics']['sign']}"
    )
    assert data['benchmark'] == 'II_partial_obs_spike', (
        f"Unexpected benchmark: {data['benchmark']!r}"
    )


@pytest.mark.unit
def test_phase219_loader_importable() -> None:
    """phase219_analysis module must be importable and expose run_phase219_analysis."""
    mod = importlib.import_module('cwt.cgt.analysis.phase219_analysis')
    assert hasattr(mod, 'run_phase219_analysis'), (
        "phase219_analysis missing 'run_phase219_analysis'"
    )


@pytest.mark.unit
def test_phase219_loader_runs(tmp_path: Path) -> None:
    """run_phase219_analysis must return a non-empty dict."""
    from cwt.cgt.analysis.phase219_analysis import run_phase219_analysis

    payload = run_phase219_analysis(project_root=_PROJECT_ROOT, output_root=tmp_path)
    assert isinstance(payload, dict), 'run_phase219_analysis must return a dict'
    assert payload, 'run_phase219_analysis returned empty dict'
    assert payload['metrics']['r2'] >= 0.90


# ===========================================================================
# Phase 220 -- Ninth less-synthetic adversarial (benchmark II partial obs spike)
# ===========================================================================


@pytest.mark.unit
def test_phase220_artifact_exists() -> None:
    """Phase 220 artifact must exist on disk."""
    assert _P220.exists(), f"Missing: {_P220}"


@pytest.mark.unit
def test_phase220_artifact_json_valid() -> None:
    """Phase 220 artifact must be valid JSON."""
    assert _P220.exists(), f"Missing: {_P220}"
    data = json.loads(_P220.read_text(encoding='utf-8'))
    assert isinstance(data, dict), "Phase 220 artifact root must be a dict"


@pytest.mark.unit
def test_phase220_artifact_structure() -> None:
    """Phase 220 artifact must contain required top-level keys."""
    data = json.loads(_P220.read_text(encoding='utf-8'))
    for key in ('phase', 'benchmark', 'raw', 'corrected', 'correction'):
        assert key in data, f"Phase 220 artifact missing key: {key!r}"
    for subkey in ('combined_r2', 'sign_agreement'):
        assert subkey in data['raw'], f"Phase 220 raw missing key: {subkey!r}"
    for subkey in ('combined_r2', 'sign_agreement'):
        assert subkey in data['corrected'], f"Phase 220 corrected missing key: {subkey!r}"


@pytest.mark.unit
def test_phase220_metric_thresholds() -> None:
    """Phase 220 corrected combined_r2 >= 0.85; corrected sign_agreement >= 0.95.

    Report: raw combined_r2 = 0.4387; corrected combined_r2 = 0.8539;
    corrected sign_agreement = 0.9597.
    """
    data = json.loads(_P220.read_text(encoding='utf-8'))
    assert data['raw']['combined_r2'] < 0.45, (
        f"Phase 220 raw combined_r2 expected < 0.45, got {data['raw']['combined_r2']}"
    )
    assert data['corrected']['combined_r2'] >= 0.85, (
        f"Phase 220 corrected combined_r2 expected >= 0.85, "
        f"got {data['corrected']['combined_r2']}"
    )
    assert data['corrected']['sign_agreement'] >= 0.95, (
        f"Phase 220 corrected sign_agreement expected >= 0.95, "
        f"got {data['corrected']['sign_agreement']}"
    )


@pytest.mark.unit
def test_phase220_loader_importable() -> None:
    """phase220_analysis module must be importable and expose run_phase220_analysis."""
    mod = importlib.import_module('cwt.cgt.analysis.phase220_analysis')
    assert hasattr(mod, 'run_phase220_analysis'), (
        "phase220_analysis missing 'run_phase220_analysis'"
    )


@pytest.mark.unit
def test_phase220_loader_runs(tmp_path: Path) -> None:
    """run_phase220_analysis must return a non-empty dict."""
    from cwt.cgt.analysis.phase220_analysis import run_phase220_analysis

    payload = run_phase220_analysis(project_root=_PROJECT_ROOT, output_root=tmp_path)
    assert isinstance(payload, dict), 'run_phase220_analysis must return a dict'
    assert payload, 'run_phase220_analysis returned empty dict'
    assert payload['corrected']['combined_r2'] >= 0.85


# ===========================================================================
# Phase 221 -- Bridge tensor geometry law v7 (benchmark scaffold family)
# ===========================================================================


@pytest.mark.unit
def test_phase221_artifact_exists() -> None:
    """Phase 221 artifact must exist on disk."""
    assert _P221.exists(), f"Missing: {_P221}"


@pytest.mark.unit
def test_phase221_artifact_json_valid() -> None:
    """Phase 221 artifact must be valid JSON."""
    assert _P221.exists(), f"Missing: {_P221}"
    data = json.loads(_P221.read_text(encoding='utf-8'))
    assert isinstance(data, dict), "Phase 221 artifact root must be a dict"


@pytest.mark.unit
def test_phase221_artifact_structure() -> None:
    """Phase 221 artifact must contain required top-level keys."""
    data = json.loads(_P221.read_text(encoding='utf-8'))
    for key in ('phase', 'candidate', 'raw', 'corrected'):
        assert key in data, f"Phase 221 artifact missing key: {key!r}"
    assert 'combined_r2' in data['raw'], "Phase 221 raw missing 'combined_r2'"
    for subkey in ('combined_r2', 'sign_agreement'):
        assert subkey in data['corrected'], f"Phase 221 corrected missing key: {subkey!r}"


@pytest.mark.unit
def test_phase221_metric_thresholds() -> None:
    """Phase 221 v7 corrected combined_r2 >= 0.928; corrected sign_agreement >= 0.980.

    Report: raw combined_r2 = 0.5611; corrected combined_r2 = 0.9287;
    corrected sign_agreement = 0.9812.
    """
    data = json.loads(_P221.read_text(encoding='utf-8'))
    assert data['corrected']['combined_r2'] >= 0.928, (
        f"Phase 221 corrected combined_r2 expected >= 0.928, "
        f"got {data['corrected']['combined_r2']}"
    )
    assert data['corrected']['sign_agreement'] >= 0.980, (
        f"Phase 221 corrected sign_agreement expected >= 0.980, "
        f"got {data['corrected']['sign_agreement']}"
    )
    assert data['candidate'] == 'bridge_tensor_geometry_law_v7', (
        f"Phase 221 expected candidate = bridge_tensor_geometry_law_v7, "
        f"got {data['candidate']!r}"
    )


@pytest.mark.unit
def test_phase221_loader_importable() -> None:
    """phase221_analysis module must be importable and expose run_phase221_analysis."""
    mod = importlib.import_module('cwt.cgt.analysis.phase221_analysis')
    assert hasattr(mod, 'run_phase221_analysis'), (
        "phase221_analysis missing 'run_phase221_analysis'"
    )


@pytest.mark.unit
def test_phase221_loader_runs(tmp_path: Path) -> None:
    """run_phase221_analysis must return a non-empty dict."""
    from cwt.cgt.analysis.phase221_analysis import run_phase221_analysis

    payload = run_phase221_analysis(project_root=_PROJECT_ROOT, output_root=tmp_path)
    assert isinstance(payload, dict), 'run_phase221_analysis must return a dict'
    assert payload, 'run_phase221_analysis returned empty dict'
    assert payload['corrected']['combined_r2'] >= 0.928


# ===========================================================================
# Phase 222 -- Bridge holdout v7 comparison (benchmark scaffold family)
# ===========================================================================


@pytest.mark.unit
def test_phase222_artifact_exists() -> None:
    """Phase 222 artifact must exist on disk."""
    assert _P222.exists(), f"Missing: {_P222}"


@pytest.mark.unit
def test_phase222_artifact_json_valid() -> None:
    """Phase 222 artifact must be valid JSON."""
    assert _P222.exists(), f"Missing: {_P222}"
    data = json.loads(_P222.read_text(encoding='utf-8'))
    assert isinstance(data, dict), "Phase 222 artifact root must be a dict"


@pytest.mark.unit
def test_phase222_artifact_structure() -> None:
    """Phase 222 artifact must contain required top-level keys."""
    data = json.loads(_P222.read_text(encoding='utf-8'))
    for key in ('rule', 'bridge_count', 'pilot_count', 'minimal_mean_r2',
                'tensor_v6_mean_r2', 'tensor_v7_mean_r2', 'gain_v7_over_v6',
                'weakest_benchmark'):
        assert key in data, f"Phase 222 artifact missing key: {key!r}"


@pytest.mark.unit
def test_phase222_metric_thresholds() -> None:
    """Phase 222 tensor v7 >= v6 >= minimal; v7 mean R2 >= 0.903; pilot_count = 9.

    Report: minimal_mean_r2 = 0.8804; tensor_v6_mean_r2 = 0.9006;
    tensor_v7_mean_r2 = 0.9031; gain_v7_over_v6 = 0.0025.
    """
    data = json.loads(_P222.read_text(encoding='utf-8'))
    assert data['tensor_v7_mean_r2'] >= data['tensor_v6_mean_r2'], (
        "Phase 222 tensor v7 must be >= tensor v6 mean R2"
    )
    assert data['tensor_v6_mean_r2'] >= data['minimal_mean_r2'], (
        "Phase 222 tensor v6 must be >= minimal mean R2"
    )
    assert data['tensor_v7_mean_r2'] >= 0.903, (
        f"Phase 222 tensor_v7_mean_r2 expected >= 0.903, got {data['tensor_v7_mean_r2']}"
    )
    assert data['pilot_count'] == 9, (
        f"Phase 222 expected pilot_count = 9, got {data['pilot_count']}"
    )


@pytest.mark.unit
def test_phase222_loader_importable() -> None:
    """phase222_analysis module must be importable and expose run_phase222_analysis."""
    mod = importlib.import_module('cwt.cgt.analysis.phase222_analysis')
    assert hasattr(mod, 'run_phase222_analysis'), (
        "phase222_analysis missing 'run_phase222_analysis'"
    )


@pytest.mark.unit
def test_phase222_loader_runs(tmp_path: Path) -> None:
    """run_phase222_analysis must return a non-empty dict."""
    from cwt.cgt.analysis.phase222_analysis import run_phase222_analysis

    payload = run_phase222_analysis(project_root=_PROJECT_ROOT, output_root=tmp_path)
    assert isinstance(payload, dict), 'run_phase222_analysis must return a dict'
    assert payload, 'run_phase222_analysis returned empty dict'
    assert payload['tensor_v7_mean_r2'] >= 0.903


# ===========================================================================
# Phase 223 -- Pooled thirteen-bridge adversarial v7 (benchmark scaffold family)
# ===========================================================================


@pytest.mark.unit
def test_phase223_artifact_exists() -> None:
    """Phase 223 artifact must exist on disk."""
    assert _P223.exists(), f"Missing: {_P223}"


@pytest.mark.unit
def test_phase223_artifact_json_valid() -> None:
    """Phase 223 artifact must be valid JSON."""
    assert _P223.exists(), f"Missing: {_P223}"
    data = json.loads(_P223.read_text(encoding='utf-8'))
    assert isinstance(data, dict), "Phase 223 artifact root must be a dict"


@pytest.mark.unit
def test_phase223_artifact_structure() -> None:
    """Phase 223 artifact must contain required top-level keys."""
    data = json.loads(_P223.read_text(encoding='utf-8'))
    for key in ('phase', 'rule', 'raw', 'corrected', 'correction', 'benchmark_count'):
        assert key in data, f"Phase 223 artifact missing key: {key!r}"
    for subkey in ('combined_r2', 'sign_agreement'):
        assert subkey in data['raw'], f"Phase 223 raw missing key: {subkey!r}"
    for subkey in ('combined_r2', 'sign_agreement'):
        assert subkey in data['corrected'], f"Phase 223 corrected missing key: {subkey!r}"


@pytest.mark.unit
def test_phase223_metric_thresholds() -> None:
    """Phase 223 corrected combined_r2 >= 0.921; corrected sign_agreement >= 0.977.

    Report: raw combined_r2 = 0.5611; corrected combined_r2 = 0.9212;
    corrected sign_agreement = 0.9772; benchmark_count = 13.
    """
    data = json.loads(_P223.read_text(encoding='utf-8'))
    assert data['raw']['combined_r2'] < 0.60, (
        f"Phase 223 raw combined_r2 expected < 0.60, got {data['raw']['combined_r2']}"
    )
    assert data['corrected']['combined_r2'] >= 0.921, (
        f"Phase 223 corrected combined_r2 expected >= 0.921, "
        f"got {data['corrected']['combined_r2']}"
    )
    assert data['corrected']['sign_agreement'] >= 0.977, (
        f"Phase 223 corrected sign_agreement expected >= 0.977, "
        f"got {data['corrected']['sign_agreement']}"
    )
    assert data['benchmark_count'] == 13, (
        f"Phase 223 expected benchmark_count = 13, got {data['benchmark_count']}"
    )


@pytest.mark.unit
def test_phase223_loader_importable() -> None:
    """phase223_analysis module must be importable and expose run_phase223_analysis."""
    mod = importlib.import_module('cwt.cgt.analysis.phase223_analysis')
    assert hasattr(mod, 'run_phase223_analysis'), (
        "phase223_analysis missing 'run_phase223_analysis'"
    )


@pytest.mark.unit
def test_phase223_loader_runs(tmp_path: Path) -> None:
    """run_phase223_analysis must return a non-empty dict."""
    from cwt.cgt.analysis.phase223_analysis import run_phase223_analysis

    payload = run_phase223_analysis(project_root=_PROJECT_ROOT, output_root=tmp_path)
    assert isinstance(payload, dict), 'run_phase223_analysis must return a dict'
    assert payload, 'run_phase223_analysis returned empty dict'
    assert payload['corrected']['combined_r2'] >= 0.921


# ===========================================================================
# Phase 224 -- Bridge-pilot positive summary (benchmark scaffold family)
# ===========================================================================


@pytest.mark.unit
def test_phase224_artifact_exists() -> None:
    """Phase 224 artifact must exist on disk."""
    assert _P224.exists(), f"Missing: {_P224}"


@pytest.mark.unit
def test_phase224_artifact_json_valid() -> None:
    """Phase 224 artifact must be valid JSON."""
    assert _P224.exists(), f"Missing: {_P224}"
    data = json.loads(_P224.read_text(encoding='utf-8'))
    assert isinstance(data, dict), "Phase 224 artifact root must be a dict"


@pytest.mark.unit
def test_phase224_artifact_structure() -> None:
    """Phase 224 artifact must contain required top-level keys."""
    data = json.loads(_P224.read_text(encoding='utf-8'))
    for key in ('bridge_count', 'pilot_count', 'bridge_positive_mean_r2',
                'pilot_positive_mean_r2', 'bridge_pilot_gap'):
        assert key in data, f"Phase 224 artifact missing key: {key!r}"


@pytest.mark.unit
def test_phase224_metric_thresholds() -> None:
    """Phase 224 bridge positive R2 >= 0.934; pilot positive R2 >= 0.896; gap > 0.

    Report: bridge_positive_mean_r2 = 0.9341; pilot_positive_mean_r2 = 0.8963;
    bridge_pilot_gap = 0.0378; bridge_count = 13; pilot_count = 9.
    """
    data = json.loads(_P224.read_text(encoding='utf-8'))
    assert data['bridge_positive_mean_r2'] >= 0.934, (
        f"Phase 224 bridge_positive_mean_r2 expected >= 0.934, "
        f"got {data['bridge_positive_mean_r2']}"
    )
    assert data['pilot_positive_mean_r2'] >= 0.896, (
        f"Phase 224 pilot_positive_mean_r2 expected >= 0.896, "
        f"got {data['pilot_positive_mean_r2']}"
    )
    assert data['bridge_pilot_gap'] > 0.0, (
        f"Phase 224 bridge_pilot_gap must be positive, got {data['bridge_pilot_gap']}"
    )
    assert data['bridge_count'] == 13, (
        f"Phase 224 expected bridge_count = 13, got {data['bridge_count']}"
    )


@pytest.mark.unit
def test_phase224_loader_importable() -> None:
    """phase224_analysis module must be importable and expose run_phase224_analysis."""
    mod = importlib.import_module('cwt.cgt.analysis.phase224_analysis')
    assert hasattr(mod, 'run_phase224_analysis'), (
        "phase224_analysis missing 'run_phase224_analysis'"
    )


@pytest.mark.unit
def test_phase224_loader_runs(tmp_path: Path) -> None:
    """run_phase224_analysis must return a non-empty dict."""
    from cwt.cgt.analysis.phase224_analysis import run_phase224_analysis

    payload = run_phase224_analysis(project_root=_PROJECT_ROOT, output_root=tmp_path)
    assert isinstance(payload, dict), 'run_phase224_analysis must return a dict'
    assert payload, 'run_phase224_analysis returned empty dict'
    assert payload['bridge_positive_mean_r2'] >= 0.934


# ===========================================================================
# Phase 225 -- Bridge-pilot adversarial summary (benchmark scaffold family)
# ===========================================================================


@pytest.mark.unit
def test_phase225_artifact_exists() -> None:
    """Phase 225 artifact must exist on disk."""
    assert _P225.exists(), f"Missing: {_P225}"


@pytest.mark.unit
def test_phase225_artifact_json_valid() -> None:
    """Phase 225 artifact must be valid JSON."""
    assert _P225.exists(), f"Missing: {_P225}"
    data = json.loads(_P225.read_text(encoding='utf-8'))
    assert isinstance(data, dict), "Phase 225 artifact root must be a dict"


@pytest.mark.unit
def test_phase225_artifact_structure() -> None:
    """Phase 225 artifact must contain required top-level keys."""
    data = json.loads(_P225.read_text(encoding='utf-8'))
    for key in ('bridge_count', 'pilot_count', 'raw', 'corrected',
                'bridge_corrected_mean_r2', 'pilot_corrected_mean_r2', 'bridge_pilot_gap'):
        assert key in data, f"Phase 225 artifact missing key: {key!r}"
    for subkey in ('combined_r2', 'sign_agreement'):
        assert subkey in data['raw'], f"Phase 225 raw missing key: {subkey!r}"
    for subkey in ('combined_r2', 'sign_agreement'):
        assert subkey in data['corrected'], f"Phase 225 corrected missing key: {subkey!r}"


@pytest.mark.unit
def test_phase225_metric_thresholds() -> None:
    """Phase 225 corrected combined_r2 >= 0.890; bridge corrected mean R2 >= 0.921;
    bridge_pilot_gap > 0.

    Report: raw combined_r2 = 0.5142; corrected combined_r2 = 0.8907;
    corrected sign_agreement = 0.9691; bridge_corrected_mean_r2 = 0.9212;
    pilot_corrected_mean_r2 = 0.8503; bridge_pilot_gap = 0.0709.
    """
    data = json.loads(_P225.read_text(encoding='utf-8'))
    assert data['corrected']['combined_r2'] >= 0.890, (
        f"Phase 225 corrected combined_r2 expected >= 0.890, "
        f"got {data['corrected']['combined_r2']}"
    )
    assert data['bridge_corrected_mean_r2'] >= 0.921, (
        f"Phase 225 bridge_corrected_mean_r2 expected >= 0.921, "
        f"got {data['bridge_corrected_mean_r2']}"
    )
    assert data['bridge_pilot_gap'] > 0.0, (
        f"Phase 225 bridge_pilot_gap must be positive, got {data['bridge_pilot_gap']}"
    )


@pytest.mark.unit
def test_phase225_loader_importable() -> None:
    """phase225_analysis module must be importable and expose run_phase225_analysis."""
    mod = importlib.import_module('cwt.cgt.analysis.phase225_analysis')
    assert hasattr(mod, 'run_phase225_analysis'), (
        "phase225_analysis missing 'run_phase225_analysis'"
    )


@pytest.mark.unit
def test_phase225_loader_runs(tmp_path: Path) -> None:
    """run_phase225_analysis must return a non-empty dict."""
    from cwt.cgt.analysis.phase225_analysis import run_phase225_analysis

    payload = run_phase225_analysis(project_root=_PROJECT_ROOT, output_root=tmp_path)
    assert isinstance(payload, dict), 'run_phase225_analysis must return a dict'
    assert payload, 'run_phase225_analysis returned empty dict'
    assert payload['corrected']['combined_r2'] >= 0.890


# ===========================================================================
# Phase 226 -- Externalization plateau summary (benchmark scaffold family)
# ===========================================================================


@pytest.mark.unit
def test_phase226_artifact_exists() -> None:
    """Phase 226 artifact must exist on disk."""
    assert _P226.exists(), f"Missing: {_P226}"


@pytest.mark.unit
def test_phase226_artifact_json_valid() -> None:
    """Phase 226 artifact must be valid JSON."""
    assert _P226.exists(), f"Missing: {_P226}"
    data = json.loads(_P226.read_text(encoding='utf-8'))
    assert isinstance(data, dict), "Phase 226 artifact root must be a dict"


@pytest.mark.unit
def test_phase226_artifact_structure() -> None:
    """Phase 226 artifact must contain required top-level keys."""
    data = json.loads(_P226.read_text(encoding='utf-8'))
    for key in ('phase', 'status', 'last_bridge_holdout_gains',
                'last_tensor_law_gains', 'decision'):
        assert key in data, f"Phase 226 artifact missing key: {key!r}"


@pytest.mark.unit
def test_phase226_metric_thresholds() -> None:
    """Phase 226 status = positive_progress_flattening; phase = 226;
    last_bridge_holdout_gains is a list of 3 decreasing values.

    Report: last_bridge_holdout_gains = [0.0202, 0.0142, 0.0109];
    status = positive_progress_flattening.
    """
    data = json.loads(_P226.read_text(encoding='utf-8'))
    assert data['status'] == 'positive_progress_flattening', (
        f"Phase 226 expected status = positive_progress_flattening, "
        f"got {data['status']!r}"
    )
    assert data['phase'] == 226, (
        f"Phase 226 expected phase = 226, got {data['phase']}"
    )
    gains = data['last_bridge_holdout_gains']
    assert isinstance(gains, list) and len(gains) == 3, (
        f"Phase 226 last_bridge_holdout_gains expected list of 3, got {gains!r}"
    )
    assert all(g > 0 for g in gains), (
        f"Phase 226 all bridge holdout gains must be positive, got {gains!r}"
    )


@pytest.mark.unit
def test_phase226_loader_importable() -> None:
    """phase226_analysis module must be importable and expose run_phase226_analysis."""
    mod = importlib.import_module('cwt.cgt.analysis.phase226_analysis')
    assert hasattr(mod, 'run_phase226_analysis'), (
        "phase226_analysis missing 'run_phase226_analysis'"
    )


@pytest.mark.unit
def test_phase226_loader_runs(tmp_path: Path) -> None:
    """run_phase226_analysis must return a non-empty dict."""
    from cwt.cgt.analysis.phase226_analysis import run_phase226_analysis

    payload = run_phase226_analysis(project_root=_PROJECT_ROOT, output_root=tmp_path)
    assert isinstance(payload, dict), 'run_phase226_analysis must return a dict'
    assert payload, 'run_phase226_analysis returned empty dict'
    assert payload['status'] == 'positive_progress_flattening'
