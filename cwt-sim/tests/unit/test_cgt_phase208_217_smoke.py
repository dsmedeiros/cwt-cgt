"""Smoke tests for CGT Phases 208-217 result artifacts and analysis modules.

Covers:
- Existence and JSON-validity of the Phase 208-217 artifacts.
- Importability of the phase analysis modules.
- Structural integrity of each artifact (top-level keys present).
- Metric thresholds derived from bundle reports and pinned to observed JSON values.
- Execution of run_phaseN_analysis() to verify correct output.

Benchmark layout:
  benchmark_scaffold_family/              -- Phases 208, 211, 212, 213, 214, 215, 216, 217
  benchmark_HH_event_gap_release/         -- Phases 209, 210

Phases with loaders (10):
  208, 209, 210, 211, 212, 213, 214, 215, 216, 217.

Phases 208-217 constitute the "HH-eighth-bridge and tensor-law v6" block
(bundle v8.0).
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
_HH_DIR = _PROJECT_ROOT / 'cgt_benchmarks' / 'results' / 'benchmark_HH_event_gap_release'

_P208 = _SCAFFOLD_DIR / 'benchmark_scaffold_phase208_bridge_holdout_strict.json'
_P209 = _HH_DIR / 'benchmark_hh_phase209_eighth_less_synthetic_positive.json'
_P210 = _HH_DIR / 'benchmark_hh_phase210_eighth_less_synthetic_adversarial.json'
_P211 = _SCAFFOLD_DIR / 'benchmark_scaffold_phase211_bridge_externalization_audit_with_hh.json'
_P212 = _SCAFFOLD_DIR / 'benchmark_scaffold_phase212_bridge_tensor_geometry_law_v6.json'
_P213 = _SCAFFOLD_DIR / 'benchmark_scaffold_phase213_bridge_correction_v6_compare.json'
_P214 = _SCAFFOLD_DIR / 'benchmark_scaffold_phase214_pooled_thirteen_bridge_adversarial_v6.json'
_P215 = _SCAFFOLD_DIR / 'benchmark_scaffold_phase215_pilot_only_summary.json'
_P216 = _SCAFFOLD_DIR / 'benchmark_scaffold_phase216_bridge_pilot_gap_audit.json'
_P217 = _SCAFFOLD_DIR / 'benchmark_scaffold_phase217_externalization_readiness_refresh.json'


# ===========================================================================
# Phase 208 -- Bridge holdout strict v5 vs minimal (benchmark scaffold family)
# ===========================================================================


@pytest.mark.unit
def test_phase208_artifact_exists() -> None:
    """Phase 208 artifact must exist on disk."""
    assert _P208.exists(), f"Missing: {_P208}"


@pytest.mark.unit
def test_phase208_artifact_json_valid() -> None:
    """Phase 208 artifact must be valid JSON."""
    assert _P208.exists(), f"Missing: {_P208}"
    data = json.loads(_P208.read_text(encoding='utf-8'))
    assert isinstance(data, dict), "Phase 208 artifact root must be a dict"


@pytest.mark.unit
def test_phase208_artifact_structure() -> None:
    """Phase 208 artifact must contain required top-level keys."""
    data = json.loads(_P208.read_text(encoding='utf-8'))
    for key in ('rule', 'minimal_mean_r2', 'tensor_v5_mean_r2', 'mean_gain',
                'weakest_benchmark'):
        assert key in data, f"Phase 208 artifact missing key: {key!r}"


@pytest.mark.unit
def test_phase208_metric_thresholds() -> None:
    """Phase 208 tensor v5 mean R2 >= 0.89; gain > 0; weakest = GG_windowed_sparse_release.

    Report: minimal_mean_r2 = 0.8792; tensor_v5_mean_r2 = 0.8934; mean_gain = 0.0142.
    """
    data = json.loads(_P208.read_text(encoding='utf-8'))
    assert data['tensor_v5_mean_r2'] >= 0.89, (
        f"Phase 208 tensor_v5_mean_r2 expected >= 0.89, got {data['tensor_v5_mean_r2']}"
    )
    assert data['tensor_v5_mean_r2'] > data['minimal_mean_r2'], (
        "Phase 208 tensor v5 must outperform minimal"
    )
    assert data['mean_gain'] > 0.0, (
        f"Phase 208 mean_gain must be positive, got {data['mean_gain']}"
    )
    assert data['weakest_benchmark'] == 'GG_windowed_sparse_release', (
        f"Phase 208 expected weakest = GG_windowed_sparse_release, "
        f"got {data['weakest_benchmark']!r}"
    )


@pytest.mark.unit
def test_phase208_loader_importable() -> None:
    """phase208_analysis module must be importable and expose run_phase208_analysis."""
    mod = importlib.import_module('cwt.cgt.analysis.phase208_analysis')
    assert hasattr(mod, 'run_phase208_analysis'), (
        "phase208_analysis missing 'run_phase208_analysis'"
    )


@pytest.mark.unit
def test_phase208_loader_runs(tmp_path: Path) -> None:
    """run_phase208_analysis must return a non-empty dict."""
    from cwt.cgt.analysis.phase208_analysis import run_phase208_analysis

    payload = run_phase208_analysis(project_root=_PROJECT_ROOT, output_root=tmp_path)
    assert isinstance(payload, dict), 'run_phase208_analysis must return a dict'
    assert payload, 'run_phase208_analysis returned empty dict'
    assert payload['tensor_v5_mean_r2'] >= 0.89


# ===========================================================================
# Phase 209 -- Eighth less-synthetic positive (benchmark HH event gap release)
# ===========================================================================


@pytest.mark.unit
def test_phase209_artifact_exists() -> None:
    """Phase 209 artifact must exist on disk."""
    assert _P209.exists(), f"Missing: {_P209}"


@pytest.mark.unit
def test_phase209_artifact_json_valid() -> None:
    """Phase 209 artifact must be valid JSON."""
    assert _P209.exists(), f"Missing: {_P209}"
    data = json.loads(_P209.read_text(encoding='utf-8'))
    assert isinstance(data, dict), "Phase 209 artifact root must be a dict"


@pytest.mark.unit
def test_phase209_artifact_structure() -> None:
    """Phase 209 artifact must contain required top-level keys."""
    data = json.loads(_P209.read_text(encoding='utf-8'))
    for key in ('phase', 'benchmark', 'metrics'):
        assert key in data, f"Phase 209 artifact missing key: {key!r}"
    for subkey in ('r2', 'sign'):
        assert subkey in data['metrics'], f"Phase 209 metrics missing key: {subkey!r}"


@pytest.mark.unit
def test_phase209_metric_thresholds() -> None:
    """Phase 209 eighth less-synthetic positive R2 >= 0.90; sign >= 0.98.

    Report: held-out R2 = 0.9018; corr = 0.9739; sign = 0.9875.
    """
    data = json.loads(_P209.read_text(encoding='utf-8'))
    assert data['metrics']['r2'] >= 0.90, (
        f"Phase 209 r2 expected >= 0.90, got {data['metrics']['r2']}"
    )
    assert data['metrics']['sign'] >= 0.98, (
        f"Phase 209 sign expected >= 0.98, got {data['metrics']['sign']}"
    )
    assert data['benchmark'] == 'HH_event_gap_release', (
        f"Unexpected benchmark: {data['benchmark']!r}"
    )


@pytest.mark.unit
def test_phase209_loader_importable() -> None:
    """phase209_analysis module must be importable and expose run_phase209_analysis."""
    mod = importlib.import_module('cwt.cgt.analysis.phase209_analysis')
    assert hasattr(mod, 'run_phase209_analysis'), (
        "phase209_analysis missing 'run_phase209_analysis'"
    )


@pytest.mark.unit
def test_phase209_loader_runs(tmp_path: Path) -> None:
    """run_phase209_analysis must return a non-empty dict."""
    from cwt.cgt.analysis.phase209_analysis import run_phase209_analysis

    payload = run_phase209_analysis(project_root=_PROJECT_ROOT, output_root=tmp_path)
    assert isinstance(payload, dict), 'run_phase209_analysis must return a dict'
    assert payload, 'run_phase209_analysis returned empty dict'
    assert payload['metrics']['r2'] >= 0.90


# ===========================================================================
# Phase 210 -- Eighth less-synthetic adversarial (benchmark HH event gap release)
# ===========================================================================


@pytest.mark.unit
def test_phase210_artifact_exists() -> None:
    """Phase 210 artifact must exist on disk."""
    assert _P210.exists(), f"Missing: {_P210}"


@pytest.mark.unit
def test_phase210_artifact_json_valid() -> None:
    """Phase 210 artifact must be valid JSON."""
    assert _P210.exists(), f"Missing: {_P210}"
    data = json.loads(_P210.read_text(encoding='utf-8'))
    assert isinstance(data, dict), "Phase 210 artifact root must be a dict"


@pytest.mark.unit
def test_phase210_artifact_structure() -> None:
    """Phase 210 artifact must contain required top-level keys."""
    data = json.loads(_P210.read_text(encoding='utf-8'))
    for key in ('phase', 'benchmark', 'raw', 'corrected', 'correction'):
        assert key in data, f"Phase 210 artifact missing key: {key!r}"
    for subkey in ('combined_r2', 'sign_agreement'):
        assert subkey in data['raw'], f"Phase 210 raw missing key: {subkey!r}"
    for subkey in ('combined_r2', 'sign_agreement'):
        assert subkey in data['corrected'], f"Phase 210 corrected missing key: {subkey!r}"


@pytest.mark.unit
def test_phase210_metric_thresholds() -> None:
    """Phase 210 corrected combined_r2 >= 0.84; corrected sign_agreement >= 0.95.

    Report: raw combined_r2 = 0.4351; corrected combined_r2 = 0.8446;
    corrected sign_agreement = 0.9569.
    """
    data = json.loads(_P210.read_text(encoding='utf-8'))
    assert data['raw']['combined_r2'] < 0.45, (
        f"Phase 210 raw combined_r2 expected < 0.45, got {data['raw']['combined_r2']}"
    )
    assert data['corrected']['combined_r2'] >= 0.84, (
        f"Phase 210 corrected combined_r2 expected >= 0.84, "
        f"got {data['corrected']['combined_r2']}"
    )
    assert data['corrected']['sign_agreement'] >= 0.95, (
        f"Phase 210 corrected sign_agreement expected >= 0.95, "
        f"got {data['corrected']['sign_agreement']}"
    )


@pytest.mark.unit
def test_phase210_loader_importable() -> None:
    """phase210_analysis module must be importable and expose run_phase210_analysis."""
    mod = importlib.import_module('cwt.cgt.analysis.phase210_analysis')
    assert hasattr(mod, 'run_phase210_analysis'), (
        "phase210_analysis missing 'run_phase210_analysis'"
    )


@pytest.mark.unit
def test_phase210_loader_runs(tmp_path: Path) -> None:
    """run_phase210_analysis must return a non-empty dict."""
    from cwt.cgt.analysis.phase210_analysis import run_phase210_analysis

    payload = run_phase210_analysis(project_root=_PROJECT_ROOT, output_root=tmp_path)
    assert isinstance(payload, dict), 'run_phase210_analysis must return a dict'
    assert payload, 'run_phase210_analysis returned empty dict'
    assert payload['corrected']['combined_r2'] >= 0.84


# ===========================================================================
# Phase 211 -- Bridge externalization audit with HH (benchmark scaffold family)
# ===========================================================================


@pytest.mark.unit
def test_phase211_artifact_exists() -> None:
    """Phase 211 artifact must exist on disk."""
    assert _P211.exists(), f"Missing: {_P211}"


@pytest.mark.unit
def test_phase211_artifact_json_valid() -> None:
    """Phase 211 artifact must be valid JSON."""
    assert _P211.exists(), f"Missing: {_P211}"
    data = json.loads(_P211.read_text(encoding='utf-8'))
    assert isinstance(data, dict), "Phase 211 artifact root must be a dict"


@pytest.mark.unit
def test_phase211_artifact_structure() -> None:
    """Phase 211 artifact must contain required top-level keys."""
    data = json.loads(_P211.read_text(encoding='utf-8'))
    for key in ('rule', 'positive_mean_r2', 'adversarial_mean_r2',
                'pilot_count', 'bridge_count', 'pilot_weakest', 'bridge_weakest'):
        assert key in data, f"Phase 211 artifact missing key: {key!r}"


@pytest.mark.unit
def test_phase211_metric_thresholds() -> None:
    """Phase 211 positive_mean_r2 >= 0.88; adversarial_mean_r2 >= 0.84;
    pilot_count = 8; bridge_count = 13.

    Report: positive_mean_r2 = 0.8896; adversarial_mean_r2 = 0.8478;
    pilot_weakest = GG_windowed_sparse_release; bridge_weakest = BB_sensor_gap.
    """
    data = json.loads(_P211.read_text(encoding='utf-8'))
    assert data['positive_mean_r2'] >= 0.88, (
        f"Phase 211 positive_mean_r2 expected >= 0.88, got {data['positive_mean_r2']}"
    )
    assert data['adversarial_mean_r2'] >= 0.84, (
        f"Phase 211 adversarial_mean_r2 expected >= 0.84, got {data['adversarial_mean_r2']}"
    )
    assert data['pilot_count'] == 8, (
        f"Phase 211 expected pilot_count = 8, got {data['pilot_count']}"
    )
    assert data['bridge_count'] == 13, (
        f"Phase 211 expected bridge_count = 13, got {data['bridge_count']}"
    )
    assert data['pilot_weakest'] == 'GG_windowed_sparse_release', (
        f"Phase 211 expected pilot_weakest = GG_windowed_sparse_release, "
        f"got {data['pilot_weakest']!r}"
    )


@pytest.mark.unit
def test_phase211_loader_importable() -> None:
    """phase211_analysis module must be importable and expose run_phase211_analysis."""
    mod = importlib.import_module('cwt.cgt.analysis.phase211_analysis')
    assert hasattr(mod, 'run_phase211_analysis'), (
        "phase211_analysis missing 'run_phase211_analysis'"
    )


@pytest.mark.unit
def test_phase211_loader_runs(tmp_path: Path) -> None:
    """run_phase211_analysis must return a non-empty dict."""
    from cwt.cgt.analysis.phase211_analysis import run_phase211_analysis

    payload = run_phase211_analysis(project_root=_PROJECT_ROOT, output_root=tmp_path)
    assert isinstance(payload, dict), 'run_phase211_analysis must return a dict'
    assert payload, 'run_phase211_analysis returned empty dict'
    assert payload['positive_mean_r2'] >= 0.88


# ===========================================================================
# Phase 212 -- Bridge tensor geometry law v6 (benchmark scaffold family)
# ===========================================================================


@pytest.mark.unit
def test_phase212_artifact_exists() -> None:
    """Phase 212 artifact must exist on disk."""
    assert _P212.exists(), f"Missing: {_P212}"


@pytest.mark.unit
def test_phase212_artifact_json_valid() -> None:
    """Phase 212 artifact must be valid JSON."""
    assert _P212.exists(), f"Missing: {_P212}"
    data = json.loads(_P212.read_text(encoding='utf-8'))
    assert isinstance(data, dict), "Phase 212 artifact root must be a dict"


@pytest.mark.unit
def test_phase212_artifact_structure() -> None:
    """Phase 212 artifact must contain required top-level keys."""
    data = json.loads(_P212.read_text(encoding='utf-8'))
    for key in ('phase', 'candidate', 'raw', 'corrected'):
        assert key in data, f"Phase 212 artifact missing key: {key!r}"
    assert 'combined_r2' in data['raw'], "Phase 212 raw missing 'combined_r2'"
    for subkey in ('combined_r2', 'sign_agreement'):
        assert subkey in data['corrected'], f"Phase 212 corrected missing key: {subkey!r}"


@pytest.mark.unit
def test_phase212_metric_thresholds() -> None:
    """Phase 212 v6 corrected combined_r2 >= 0.926; corrected sign_agreement >= 0.979.

    Report: raw combined_r2 = 0.5611; corrected combined_r2 = 0.9262;
    corrected sign_agreement = 0.9798.
    """
    data = json.loads(_P212.read_text(encoding='utf-8'))
    assert data['corrected']['combined_r2'] >= 0.926, (
        f"Phase 212 corrected combined_r2 expected >= 0.926, "
        f"got {data['corrected']['combined_r2']}"
    )
    assert data['corrected']['sign_agreement'] >= 0.979, (
        f"Phase 212 corrected sign_agreement expected >= 0.979, "
        f"got {data['corrected']['sign_agreement']}"
    )
    assert data['candidate'] == 'bridge_tensor_geometry_law_v6', (
        f"Phase 212 expected candidate = bridge_tensor_geometry_law_v6, "
        f"got {data['candidate']!r}"
    )


@pytest.mark.unit
def test_phase212_loader_importable() -> None:
    """phase212_analysis module must be importable and expose run_phase212_analysis."""
    mod = importlib.import_module('cwt.cgt.analysis.phase212_analysis')
    assert hasattr(mod, 'run_phase212_analysis'), (
        "phase212_analysis missing 'run_phase212_analysis'"
    )


@pytest.mark.unit
def test_phase212_loader_runs(tmp_path: Path) -> None:
    """run_phase212_analysis must return a non-empty dict."""
    from cwt.cgt.analysis.phase212_analysis import run_phase212_analysis

    payload = run_phase212_analysis(project_root=_PROJECT_ROOT, output_root=tmp_path)
    assert isinstance(payload, dict), 'run_phase212_analysis must return a dict'
    assert payload, 'run_phase212_analysis returned empty dict'
    assert payload['corrected']['combined_r2'] >= 0.926


# ===========================================================================
# Phase 213 -- Bridge correction v6 comparison (benchmark scaffold family)
# ===========================================================================


@pytest.mark.unit
def test_phase213_artifact_exists() -> None:
    """Phase 213 artifact must exist on disk."""
    assert _P213.exists(), f"Missing: {_P213}"


@pytest.mark.unit
def test_phase213_artifact_json_valid() -> None:
    """Phase 213 artifact must be valid JSON."""
    assert _P213.exists(), f"Missing: {_P213}"
    data = json.loads(_P213.read_text(encoding='utf-8'))
    assert isinstance(data, dict), "Phase 213 artifact root must be a dict"


@pytest.mark.unit
def test_phase213_artifact_structure() -> None:
    """Phase 213 artifact must contain required top-level keys."""
    data = json.loads(_P213.read_text(encoding='utf-8'))
    for key in ('phase', 'minimal', 'tensor_v5', 'tensor_v6'):
        assert key in data, f"Phase 213 artifact missing key: {key!r}"
    for rule in ('minimal', 'tensor_v5', 'tensor_v6'):
        for subkey in ('combined_r2', 'sign_agreement'):
            assert subkey in data[rule], f"Phase 213 {rule} missing key: {subkey!r}"


@pytest.mark.unit
def test_phase213_metric_thresholds() -> None:
    """Phase 213 tensor_v6 must outperform v5 which must outperform minimal.

    Report: minimal combined_r2 = 0.8821; tensor_v5 combined_r2 = 0.9231;
    tensor_v6 combined_r2 = 0.9262.
    """
    data = json.loads(_P213.read_text(encoding='utf-8'))
    assert data['tensor_v6']['combined_r2'] >= data['tensor_v5']['combined_r2'], (
        "Phase 213 tensor_v6 must be >= tensor_v5 combined_r2"
    )
    assert data['tensor_v5']['combined_r2'] > data['minimal']['combined_r2'], (
        "Phase 213 tensor_v5 must exceed minimal combined_r2"
    )
    assert data['tensor_v6']['combined_r2'] >= 0.926, (
        f"Phase 213 tensor_v6 combined_r2 expected >= 0.926, "
        f"got {data['tensor_v6']['combined_r2']}"
    )
    assert data['minimal']['combined_r2'] >= 0.88, (
        f"Phase 213 minimal combined_r2 expected >= 0.88, "
        f"got {data['minimal']['combined_r2']}"
    )


@pytest.mark.unit
def test_phase213_loader_importable() -> None:
    """phase213_analysis module must be importable and expose run_phase213_analysis."""
    mod = importlib.import_module('cwt.cgt.analysis.phase213_analysis')
    assert hasattr(mod, 'run_phase213_analysis'), (
        "phase213_analysis missing 'run_phase213_analysis'"
    )


@pytest.mark.unit
def test_phase213_loader_runs(tmp_path: Path) -> None:
    """run_phase213_analysis must return a non-empty dict."""
    from cwt.cgt.analysis.phase213_analysis import run_phase213_analysis

    payload = run_phase213_analysis(project_root=_PROJECT_ROOT, output_root=tmp_path)
    assert isinstance(payload, dict), 'run_phase213_analysis must return a dict'
    assert payload, 'run_phase213_analysis returned empty dict'
    assert payload['tensor_v6']['combined_r2'] >= 0.926


# ===========================================================================
# Phase 214 -- Pooled thirteen-bridge adversarial v6 (benchmark scaffold family)
# ===========================================================================


@pytest.mark.unit
def test_phase214_artifact_exists() -> None:
    """Phase 214 artifact must exist on disk."""
    assert _P214.exists(), f"Missing: {_P214}"


@pytest.mark.unit
def test_phase214_artifact_json_valid() -> None:
    """Phase 214 artifact must be valid JSON."""
    assert _P214.exists(), f"Missing: {_P214}"
    data = json.loads(_P214.read_text(encoding='utf-8'))
    assert isinstance(data, dict), "Phase 214 artifact root must be a dict"


@pytest.mark.unit
def test_phase214_artifact_structure() -> None:
    """Phase 214 artifact must contain required top-level keys."""
    data = json.loads(_P214.read_text(encoding='utf-8'))
    for key in ('phase', 'rule', 'raw', 'corrected', 'correction', 'benchmark_count'):
        assert key in data, f"Phase 214 artifact missing key: {key!r}"
    for subkey in ('combined_r2', 'sign_agreement'):
        assert subkey in data['raw'], f"Phase 214 raw missing key: {subkey!r}"
    for subkey in ('combined_r2', 'sign_agreement'):
        assert subkey in data['corrected'], f"Phase 214 corrected missing key: {subkey!r}"


@pytest.mark.unit
def test_phase214_metric_thresholds() -> None:
    """Phase 214 corrected combined_r2 >= 0.919; corrected sign_agreement >= 0.975.

    Report: raw combined_r2 = 0.5611; corrected combined_r2 = 0.9194;
    corrected sign_agreement = 0.9760; benchmark_count = 13.
    """
    data = json.loads(_P214.read_text(encoding='utf-8'))
    assert data['raw']['combined_r2'] < 0.60, (
        f"Phase 214 raw combined_r2 expected < 0.60, got {data['raw']['combined_r2']}"
    )
    assert data['corrected']['combined_r2'] >= 0.919, (
        f"Phase 214 corrected combined_r2 expected >= 0.919, "
        f"got {data['corrected']['combined_r2']}"
    )
    assert data['corrected']['sign_agreement'] >= 0.975, (
        f"Phase 214 corrected sign_agreement expected >= 0.975, "
        f"got {data['corrected']['sign_agreement']}"
    )
    assert data['benchmark_count'] == 13, (
        f"Phase 214 expected benchmark_count = 13, got {data['benchmark_count']}"
    )


@pytest.mark.unit
def test_phase214_loader_importable() -> None:
    """phase214_analysis module must be importable and expose run_phase214_analysis."""
    mod = importlib.import_module('cwt.cgt.analysis.phase214_analysis')
    assert hasattr(mod, 'run_phase214_analysis'), (
        "phase214_analysis missing 'run_phase214_analysis'"
    )


@pytest.mark.unit
def test_phase214_loader_runs(tmp_path: Path) -> None:
    """run_phase214_analysis must return a non-empty dict."""
    from cwt.cgt.analysis.phase214_analysis import run_phase214_analysis

    payload = run_phase214_analysis(project_root=_PROJECT_ROOT, output_root=tmp_path)
    assert isinstance(payload, dict), 'run_phase214_analysis must return a dict'
    assert payload, 'run_phase214_analysis returned empty dict'
    assert payload['corrected']['combined_r2'] >= 0.919


# ===========================================================================
# Phase 215 -- Pilot-only summary (benchmark scaffold family)
# ===========================================================================


@pytest.mark.unit
def test_phase215_artifact_exists() -> None:
    """Phase 215 artifact must exist on disk."""
    assert _P215.exists(), f"Missing: {_P215}"


@pytest.mark.unit
def test_phase215_artifact_json_valid() -> None:
    """Phase 215 artifact must be valid JSON."""
    assert _P215.exists(), f"Missing: {_P215}"
    data = json.loads(_P215.read_text(encoding='utf-8'))
    assert isinstance(data, dict), "Phase 215 artifact root must be a dict"


@pytest.mark.unit
def test_phase215_artifact_structure() -> None:
    """Phase 215 artifact must contain required top-level keys."""
    data = json.loads(_P215.read_text(encoding='utf-8'))
    for key in ('phase', 'pilot_count', 'positive', 'adversarial_corrected',
                'weakest_pilot', 'strongest_pilot'):
        assert key in data, f"Phase 215 artifact missing key: {key!r}"
    for subkey in ('combined_r2', 'sign'):
        assert subkey in data['positive'], f"Phase 215 positive missing key: {subkey!r}"
    for subkey in ('combined_r2', 'sign'):
        assert subkey in data['adversarial_corrected'], (
            f"Phase 215 adversarial_corrected missing key: {subkey!r}"
        )


@pytest.mark.unit
def test_phase215_metric_thresholds() -> None:
    """Phase 215 positive combined_r2 >= 0.89; adversarial_corrected combined_r2 >= 0.84;
    pilot_count = 8.

    Report: positive combined_r2 = 0.8927; adversarial_corrected combined_r2 = 0.8461;
    weakest_pilot = GG_windowed_sparse_release; strongest_pilot = AA_less_synthetic.
    """
    data = json.loads(_P215.read_text(encoding='utf-8'))
    assert data['positive']['combined_r2'] >= 0.89, (
        f"Phase 215 positive combined_r2 expected >= 0.89, "
        f"got {data['positive']['combined_r2']}"
    )
    assert data['adversarial_corrected']['combined_r2'] >= 0.84, (
        f"Phase 215 adversarial_corrected combined_r2 expected >= 0.84, "
        f"got {data['adversarial_corrected']['combined_r2']}"
    )
    assert data['pilot_count'] == 8, (
        f"Phase 215 expected pilot_count = 8, got {data['pilot_count']}"
    )
    assert data['weakest_pilot'] == 'GG_windowed_sparse_release', (
        f"Phase 215 expected weakest_pilot = GG_windowed_sparse_release, "
        f"got {data['weakest_pilot']!r}"
    )


@pytest.mark.unit
def test_phase215_loader_importable() -> None:
    """phase215_analysis module must be importable and expose run_phase215_analysis."""
    mod = importlib.import_module('cwt.cgt.analysis.phase215_analysis')
    assert hasattr(mod, 'run_phase215_analysis'), (
        "phase215_analysis missing 'run_phase215_analysis'"
    )


@pytest.mark.unit
def test_phase215_loader_runs(tmp_path: Path) -> None:
    """run_phase215_analysis must return a non-empty dict."""
    from cwt.cgt.analysis.phase215_analysis import run_phase215_analysis

    payload = run_phase215_analysis(project_root=_PROJECT_ROOT, output_root=tmp_path)
    assert isinstance(payload, dict), 'run_phase215_analysis must return a dict'
    assert payload, 'run_phase215_analysis returned empty dict'
    assert payload['positive']['combined_r2'] >= 0.89


# ===========================================================================
# Phase 216 -- Bridge-pilot gap audit (benchmark scaffold family)
# ===========================================================================


@pytest.mark.unit
def test_phase216_artifact_exists() -> None:
    """Phase 216 artifact must exist on disk."""
    assert _P216.exists(), f"Missing: {_P216}"


@pytest.mark.unit
def test_phase216_artifact_json_valid() -> None:
    """Phase 216 artifact must be valid JSON."""
    assert _P216.exists(), f"Missing: {_P216}"
    data = json.loads(_P216.read_text(encoding='utf-8'))
    assert isinstance(data, dict), "Phase 216 artifact root must be a dict"


@pytest.mark.unit
def test_phase216_artifact_structure() -> None:
    """Phase 216 artifact must contain required top-level keys."""
    data = json.loads(_P216.read_text(encoding='utf-8'))
    for key in ('phase', 'bridge_positive_r2', 'pilot_positive_r2',
                'bridge_adversarial_r2', 'pilot_adversarial_r2',
                'positive_gap', 'adversarial_gap'):
        assert key in data, f"Phase 216 artifact missing key: {key!r}"


@pytest.mark.unit
def test_phase216_metric_thresholds() -> None:
    """Phase 216 bridge positive R2 >= 0.939; pilot positive R2 >= 0.892;
    gaps must be positive (bridge outperforms pilot).

    Report: bridge_positive_r2 = 0.9397; pilot_positive_r2 = 0.8927;
    positive_gap = 0.047; adversarial_gap = 0.0733.
    """
    data = json.loads(_P216.read_text(encoding='utf-8'))
    assert data['bridge_positive_r2'] >= 0.939, (
        f"Phase 216 bridge_positive_r2 expected >= 0.939, "
        f"got {data['bridge_positive_r2']}"
    )
    assert data['pilot_positive_r2'] >= 0.892, (
        f"Phase 216 pilot_positive_r2 expected >= 0.892, "
        f"got {data['pilot_positive_r2']}"
    )
    assert data['positive_gap'] > 0.0, (
        f"Phase 216 positive_gap must be positive, got {data['positive_gap']}"
    )
    assert data['adversarial_gap'] > 0.0, (
        f"Phase 216 adversarial_gap must be positive, got {data['adversarial_gap']}"
    )


@pytest.mark.unit
def test_phase216_loader_importable() -> None:
    """phase216_analysis module must be importable and expose run_phase216_analysis."""
    mod = importlib.import_module('cwt.cgt.analysis.phase216_analysis')
    assert hasattr(mod, 'run_phase216_analysis'), (
        "phase216_analysis missing 'run_phase216_analysis'"
    )


@pytest.mark.unit
def test_phase216_loader_runs(tmp_path: Path) -> None:
    """run_phase216_analysis must return a non-empty dict."""
    from cwt.cgt.analysis.phase216_analysis import run_phase216_analysis

    payload = run_phase216_analysis(project_root=_PROJECT_ROOT, output_root=tmp_path)
    assert isinstance(payload, dict), 'run_phase216_analysis must return a dict'
    assert payload, 'run_phase216_analysis returned empty dict'
    assert payload['bridge_positive_r2'] >= 0.939


# ===========================================================================
# Phase 217 -- Externalization readiness refresh (benchmark scaffold family)
# ===========================================================================


@pytest.mark.unit
def test_phase217_artifact_exists() -> None:
    """Phase 217 artifact must exist on disk."""
    assert _P217.exists(), f"Missing: {_P217}"


@pytest.mark.unit
def test_phase217_artifact_json_valid() -> None:
    """Phase 217 artifact must be valid JSON."""
    assert _P217.exists(), f"Missing: {_P217}"
    data = json.loads(_P217.read_text(encoding='utf-8'))
    assert isinstance(data, dict), "Phase 217 artifact root must be a dict"


@pytest.mark.unit
def test_phase217_artifact_structure() -> None:
    """Phase 217 artifact must contain required top-level keys."""
    data = json.loads(_P217.read_text(encoding='utf-8'))
    for key in ('phase', 'externalization_readiness', 'bridge_tensor_law',
                'recommendation', 'support'):
        assert key in data, f"Phase 217 artifact missing key: {key!r}"
    for subkey in ('bridge_holdout_mean_r2', 'pilot_positive_r2',
                   'pilot_adversarial_r2', 'bridge_pilot_positive_gap',
                   'bridge_pilot_adversarial_gap'):
        assert subkey in data['support'], f"Phase 217 support missing key: {subkey!r}"


@pytest.mark.unit
def test_phase217_metric_thresholds() -> None:
    """Phase 217 bridge holdout mean R2 >= 0.893; pilot positive R2 >= 0.892;
    bridge tensor law = v6_current_best.

    Report: bridge_holdout_mean_r2 = 0.8934; pilot_positive_r2 = 0.8927;
    externalization_readiness = improving_but_not_ready.
    """
    data = json.loads(_P217.read_text(encoding='utf-8'))
    assert data['support']['bridge_holdout_mean_r2'] >= 0.893, (
        f"Phase 217 bridge_holdout_mean_r2 expected >= 0.893, "
        f"got {data['support']['bridge_holdout_mean_r2']}"
    )
    assert data['support']['pilot_positive_r2'] >= 0.892, (
        f"Phase 217 pilot_positive_r2 expected >= 0.892, "
        f"got {data['support']['pilot_positive_r2']}"
    )
    assert data['bridge_tensor_law'] == 'v6_current_best', (
        f"Phase 217 expected bridge_tensor_law = v6_current_best, "
        f"got {data['bridge_tensor_law']!r}"
    )
    assert data['externalization_readiness'] == 'improving_but_not_ready', (
        f"Phase 217 expected externalization_readiness = improving_but_not_ready, "
        f"got {data['externalization_readiness']!r}"
    )


@pytest.mark.unit
def test_phase217_loader_importable() -> None:
    """phase217_analysis module must be importable and expose run_phase217_analysis."""
    mod = importlib.import_module('cwt.cgt.analysis.phase217_analysis')
    assert hasattr(mod, 'run_phase217_analysis'), (
        "phase217_analysis missing 'run_phase217_analysis'"
    )


@pytest.mark.unit
def test_phase217_loader_runs(tmp_path: Path) -> None:
    """run_phase217_analysis must return a non-empty dict."""
    from cwt.cgt.analysis.phase217_analysis import run_phase217_analysis

    payload = run_phase217_analysis(project_root=_PROJECT_ROOT, output_root=tmp_path)
    assert isinstance(payload, dict), 'run_phase217_analysis must return a dict'
    assert payload, 'run_phase217_analysis returned empty dict'
    assert payload['support']['bridge_holdout_mean_r2'] >= 0.893
