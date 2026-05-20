"""Smoke tests for CGT Phases 177-186 result artifacts and analysis modules.

Covers:
- Existence and JSON-validity of the Phase 177-186 artifacts (phases with JSONs only).
- Importability of the phase analysis modules.
- Structural integrity of each artifact (top-level keys present).
- Metric thresholds derived from bundle reports and pinned to observed JSON values.
- Execution of run_phaseN_analysis() to verify correct output.

Benchmark layout:
  benchmark_AE_state_occluded_irregular/ — Phases 177, 178
  benchmark_EE_sparse_release/           — Phases 181, 182
  benchmark_scaffold_family/             — Phases 179, 180, 183, 184, 185, 186

Phases with loaders (10):
  177, 178, 179, 180, 181, 182, 183, 184, 185, 186.

Phases 177-186 constitute the "eleventh-bridge and tensor-law v3" block
(bundle v7.7).
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
_AE_DIR = _PROJECT_ROOT / 'cgt_benchmarks' / 'results' / 'benchmark_AE_state_occluded_irregular'
_EE_DIR = _PROJECT_ROOT / 'cgt_benchmarks' / 'results' / 'benchmark_EE_sparse_release'

_P177 = _AE_DIR / 'benchmark_ae_phase177_eleventh_bridge_positive.json'
_P178 = _AE_DIR / 'benchmark_ae_phase178_bridge_adversarial_tensor_compactness.json'
_P179 = _SCAFFOLD_DIR / 'benchmark_scaffold_phase179_pooled_eleven_bridge_positive.json'
_P180 = _SCAFFOLD_DIR / 'benchmark_scaffold_phase180_pooled_eleven_bridge_adversarial.json'
_P181 = _EE_DIR / 'benchmark_ee_phase181_fifth_less_synthetic_positive.json'
_P182 = _EE_DIR / 'benchmark_ee_phase182_fifth_less_synthetic_adversarial.json'
_P183 = _SCAFFOLD_DIR / 'benchmark_scaffold_phase183_bridge_loo_with_all_pilots_and_ae.json'
_P184 = _SCAFFOLD_DIR / 'benchmark_scaffold_phase184_bridge_correction_v2_vs_minimal.json'
_P185 = _SCAFFOLD_DIR / 'benchmark_scaffold_phase185_bridge_tensor_geometry_law_v3.json'
_P186 = _SCAFFOLD_DIR / 'benchmark_scaffold_phase186_bridge_boundary_refresh_v4.json'


# ===========================================================================
# Phase 177 — Eleventh bridge positive (benchmark AE state occluded irregular)
# ===========================================================================


@pytest.mark.unit
def test_phase177_artifact_exists() -> None:
    """Phase 177 artifact must exist on disk."""
    assert _P177.exists(), f"Missing: {_P177}"


@pytest.mark.unit
def test_phase177_artifact_json_valid() -> None:
    """Phase 177 artifact must be valid JSON."""
    assert _P177.exists(), f"Missing: {_P177}"
    data = json.loads(_P177.read_text(encoding='utf-8'))
    assert isinstance(data, dict), "Phase 177 artifact root must be a dict"


@pytest.mark.unit
def test_phase177_artifact_structure() -> None:
    """Phase 177 artifact must contain required top-level keys."""
    data = json.loads(_P177.read_text(encoding='utf-8'))
    for key in ('phase', 'benchmark', 'metrics'):
        assert key in data, f"Phase 177 artifact missing key: {key!r}"
    for subkey in ('r2', 'sign'):
        assert subkey in data['metrics'], f"Phase 177 metrics missing key: {subkey!r}"


@pytest.mark.unit
def test_phase177_metric_thresholds() -> None:
    """Phase 177 metrics must meet eleventh-bridge acceptance bounds.

    Report: switch-slice held-out R2 = 0.9258; sign = 1.0.
    """
    data = json.loads(_P177.read_text(encoding='utf-8'))
    assert data['metrics']['r2'] >= 0.92, (
        f"Phase 177 r2 expected >= 0.92, got {data['metrics']['r2']}"
    )
    assert data['metrics']['sign'] >= 0.99, (
        f"Phase 177 sign expected >= 0.99, got {data['metrics']['sign']}"
    )
    assert data['benchmark'] == 'AE_state_occluded_irregular', (
        f"Unexpected benchmark: {data['benchmark']!r}"
    )


@pytest.mark.unit
def test_phase177_loader_importable() -> None:
    """phase177_analysis module must be importable and expose run_phase177_analysis."""
    mod = importlib.import_module('cwt.cgt.analysis.phase177_analysis')
    assert hasattr(mod, 'run_phase177_analysis'), (
        "phase177_analysis missing 'run_phase177_analysis'"
    )


@pytest.mark.unit
def test_phase177_loader_runs(tmp_path: Path) -> None:
    """run_phase177_analysis must return a non-empty dict."""
    from cwt.cgt.analysis.phase177_analysis import run_phase177_analysis

    payload = run_phase177_analysis(project_root=_PROJECT_ROOT, output_root=tmp_path)
    assert isinstance(payload, dict), 'run_phase177_analysis must return a dict'
    assert payload, 'run_phase177_analysis returned empty dict'
    assert payload['metrics']['r2'] >= 0.92


# ===========================================================================
# Phase 178 — Eleventh bridge adversarial (benchmark AE state occluded irregular)
# ===========================================================================


@pytest.mark.unit
def test_phase178_artifact_exists() -> None:
    """Phase 178 artifact must exist on disk."""
    assert _P178.exists(), f"Missing: {_P178}"


@pytest.mark.unit
def test_phase178_artifact_json_valid() -> None:
    """Phase 178 artifact must be valid JSON."""
    assert _P178.exists(), f"Missing: {_P178}"
    data = json.loads(_P178.read_text(encoding='utf-8'))
    assert isinstance(data, dict), "Phase 178 artifact root must be a dict"


@pytest.mark.unit
def test_phase178_artifact_structure() -> None:
    """Phase 178 artifact must contain required top-level keys."""
    data = json.loads(_P178.read_text(encoding='utf-8'))
    for key in ('phase', 'benchmark', 'raw', 'corrected', 'correction'):
        assert key in data, f"Phase 178 artifact missing key: {key!r}"
    for subkey in ('combined_r2', 'sign_agreement'):
        assert subkey in data['raw'], f"Phase 178 raw missing key: {subkey!r}"
    for subkey in ('combined_r2', 'sign_agreement'):
        assert subkey in data['corrected'], f"Phase 178 corrected missing key: {subkey!r}"


@pytest.mark.unit
def test_phase178_metric_thresholds() -> None:
    """Phase 178 corrected metrics must meet adversarial correction acceptance bounds.

    Report: raw combined_r2 = 0.5342; corrected combined_r2 = 0.8918; corrected
    sign_agreement = 0.9653.
    """
    data = json.loads(_P178.read_text(encoding='utf-8'))
    assert data['raw']['combined_r2'] < 0.60, (
        f"Phase 178 raw combined_r2 expected < 0.60, got {data['raw']['combined_r2']}"
    )
    assert data['corrected']['combined_r2'] >= 0.88, (
        f"Phase 178 corrected combined_r2 expected >= 0.88, "
        f"got {data['corrected']['combined_r2']}"
    )
    assert data['corrected']['sign_agreement'] >= 0.96, (
        f"Phase 178 corrected sign_agreement expected >= 0.96, "
        f"got {data['corrected']['sign_agreement']}"
    )


@pytest.mark.unit
def test_phase178_loader_importable() -> None:
    """phase178_analysis module must be importable and expose run_phase178_analysis."""
    mod = importlib.import_module('cwt.cgt.analysis.phase178_analysis')
    assert hasattr(mod, 'run_phase178_analysis'), (
        "phase178_analysis missing 'run_phase178_analysis'"
    )


@pytest.mark.unit
def test_phase178_loader_runs(tmp_path: Path) -> None:
    """run_phase178_analysis must return a non-empty dict."""
    from cwt.cgt.analysis.phase178_analysis import run_phase178_analysis

    payload = run_phase178_analysis(project_root=_PROJECT_ROOT, output_root=tmp_path)
    assert isinstance(payload, dict), 'run_phase178_analysis must return a dict'
    assert payload, 'run_phase178_analysis returned empty dict'
    assert payload['corrected']['combined_r2'] >= 0.88


# ===========================================================================
# Phase 179 — Pooled eleven-bridge positive (benchmark scaffold family)
# ===========================================================================


@pytest.mark.unit
def test_phase179_artifact_exists() -> None:
    """Phase 179 artifact must exist on disk."""
    assert _P179.exists(), f"Missing: {_P179}"


@pytest.mark.unit
def test_phase179_artifact_json_valid() -> None:
    """Phase 179 artifact must be valid JSON."""
    assert _P179.exists(), f"Missing: {_P179}"
    data = json.loads(_P179.read_text(encoding='utf-8'))
    assert isinstance(data, dict), "Phase 179 artifact root must be a dict"


@pytest.mark.unit
def test_phase179_artifact_structure() -> None:
    """Phase 179 artifact must contain required top-level keys."""
    data = json.loads(_P179.read_text(encoding='utf-8'))
    for key in ('phase', 'rule', 'metrics', 'benchmark_count'):
        assert key in data, f"Phase 179 artifact missing key: {key!r}"
    for subkey in ('combined_r2', 'sign'):
        assert subkey in data['metrics'], f"Phase 179 metrics missing key: {subkey!r}"


@pytest.mark.unit
def test_phase179_metric_thresholds() -> None:
    """Phase 179 pooled eleven-bridge positive combined_r2 >= 0.93; sign >= 0.99.

    Report: combined_r2 = 0.9397; corr = 0.9865; sign = 0.9952; benchmark_count = 11.
    """
    data = json.loads(_P179.read_text(encoding='utf-8'))
    assert data['metrics']['combined_r2'] >= 0.93, (
        f"Phase 179 combined_r2 expected >= 0.93, got {data['metrics']['combined_r2']}"
    )
    assert data['metrics']['sign'] >= 0.99, (
        f"Phase 179 sign expected >= 0.99, got {data['metrics']['sign']}"
    )
    assert data['benchmark_count'] == 11, (
        f"Phase 179 expected benchmark_count = 11, got {data['benchmark_count']}"
    )


@pytest.mark.unit
def test_phase179_loader_importable() -> None:
    """phase179_analysis module must be importable and expose run_phase179_analysis."""
    mod = importlib.import_module('cwt.cgt.analysis.phase179_analysis')
    assert hasattr(mod, 'run_phase179_analysis'), (
        "phase179_analysis missing 'run_phase179_analysis'"
    )


@pytest.mark.unit
def test_phase179_loader_runs(tmp_path: Path) -> None:
    """run_phase179_analysis must return a non-empty dict."""
    from cwt.cgt.analysis.phase179_analysis import run_phase179_analysis

    payload = run_phase179_analysis(project_root=_PROJECT_ROOT, output_root=tmp_path)
    assert isinstance(payload, dict), 'run_phase179_analysis must return a dict'
    assert payload, 'run_phase179_analysis returned empty dict'
    assert payload['metrics']['combined_r2'] >= 0.93


# ===========================================================================
# Phase 180 — Pooled eleven-bridge adversarial (benchmark scaffold family)
# ===========================================================================


@pytest.mark.unit
def test_phase180_artifact_exists() -> None:
    """Phase 180 artifact must exist on disk."""
    assert _P180.exists(), f"Missing: {_P180}"


@pytest.mark.unit
def test_phase180_artifact_json_valid() -> None:
    """Phase 180 artifact must be valid JSON."""
    assert _P180.exists(), f"Missing: {_P180}"
    data = json.loads(_P180.read_text(encoding='utf-8'))
    assert isinstance(data, dict), "Phase 180 artifact root must be a dict"


@pytest.mark.unit
def test_phase180_artifact_structure() -> None:
    """Phase 180 artifact must contain required top-level keys."""
    data = json.loads(_P180.read_text(encoding='utf-8'))
    for key in ('phase', 'rule', 'raw', 'corrected', 'correction', 'benchmark_count'):
        assert key in data, f"Phase 180 artifact missing key: {key!r}"
    for subkey in ('combined_r2', 'sign_agreement'):
        assert subkey in data['raw'], f"Phase 180 raw missing key: {subkey!r}"
    for subkey in ('combined_r2', 'sign_agreement'):
        assert subkey in data['corrected'], f"Phase 180 corrected missing key: {subkey!r}"


@pytest.mark.unit
def test_phase180_metric_thresholds() -> None:
    """Phase 180 corrected combined_r2 >= 0.91; corrected sign_agreement >= 0.97.

    Report: raw combined_r2 = 0.5561; corrected combined_r2 = 0.9128;
    corrected sign_agreement = 0.9728; benchmark_count = 11.
    """
    data = json.loads(_P180.read_text(encoding='utf-8'))
    assert data['raw']['combined_r2'] < 0.60, (
        f"Phase 180 raw combined_r2 expected < 0.60, got {data['raw']['combined_r2']}"
    )
    assert data['corrected']['combined_r2'] >= 0.91, (
        f"Phase 180 corrected combined_r2 expected >= 0.91, "
        f"got {data['corrected']['combined_r2']}"
    )
    assert data['corrected']['sign_agreement'] >= 0.97, (
        f"Phase 180 corrected sign_agreement expected >= 0.97, "
        f"got {data['corrected']['sign_agreement']}"
    )
    assert data['benchmark_count'] == 11, (
        f"Phase 180 expected benchmark_count = 11, got {data['benchmark_count']}"
    )


@pytest.mark.unit
def test_phase180_loader_importable() -> None:
    """phase180_analysis module must be importable and expose run_phase180_analysis."""
    mod = importlib.import_module('cwt.cgt.analysis.phase180_analysis')
    assert hasattr(mod, 'run_phase180_analysis'), (
        "phase180_analysis missing 'run_phase180_analysis'"
    )


@pytest.mark.unit
def test_phase180_loader_runs(tmp_path: Path) -> None:
    """run_phase180_analysis must return a non-empty dict."""
    from cwt.cgt.analysis.phase180_analysis import run_phase180_analysis

    payload = run_phase180_analysis(project_root=_PROJECT_ROOT, output_root=tmp_path)
    assert isinstance(payload, dict), 'run_phase180_analysis must return a dict'
    assert payload, 'run_phase180_analysis returned empty dict'
    assert payload['corrected']['combined_r2'] >= 0.91


# ===========================================================================
# Phase 181 — Fifth less-synthetic positive (benchmark EE sparse release)
# ===========================================================================


@pytest.mark.unit
def test_phase181_artifact_exists() -> None:
    """Phase 181 artifact must exist on disk."""
    assert _P181.exists(), f"Missing: {_P181}"


@pytest.mark.unit
def test_phase181_artifact_json_valid() -> None:
    """Phase 181 artifact must be valid JSON."""
    assert _P181.exists(), f"Missing: {_P181}"
    data = json.loads(_P181.read_text(encoding='utf-8'))
    assert isinstance(data, dict), "Phase 181 artifact root must be a dict"


@pytest.mark.unit
def test_phase181_artifact_structure() -> None:
    """Phase 181 artifact must contain required top-level keys."""
    data = json.loads(_P181.read_text(encoding='utf-8'))
    for key in ('phase', 'benchmark', 'metrics'):
        assert key in data, f"Phase 181 artifact missing key: {key!r}"
    for subkey in ('r2', 'sign'):
        assert subkey in data['metrics'], f"Phase 181 metrics missing key: {subkey!r}"


@pytest.mark.unit
def test_phase181_metric_thresholds() -> None:
    """Phase 181 less-synthetic positive R2 >= 0.88; sign >= 0.99.

    Report: held-out R2 = 0.8906; corr = 0.9558; sign = 1.0.
    """
    data = json.loads(_P181.read_text(encoding='utf-8'))
    assert data['metrics']['r2'] >= 0.88, (
        f"Phase 181 r2 expected >= 0.88, got {data['metrics']['r2']}"
    )
    assert data['metrics']['sign'] >= 0.99, (
        f"Phase 181 sign expected >= 0.99, got {data['metrics']['sign']}"
    )
    assert data['benchmark'] == 'EE_sparse_release', (
        f"Unexpected benchmark: {data['benchmark']!r}"
    )


@pytest.mark.unit
def test_phase181_loader_importable() -> None:
    """phase181_analysis module must be importable and expose run_phase181_analysis."""
    mod = importlib.import_module('cwt.cgt.analysis.phase181_analysis')
    assert hasattr(mod, 'run_phase181_analysis'), (
        "phase181_analysis missing 'run_phase181_analysis'"
    )


@pytest.mark.unit
def test_phase181_loader_runs(tmp_path: Path) -> None:
    """run_phase181_analysis must return a non-empty dict."""
    from cwt.cgt.analysis.phase181_analysis import run_phase181_analysis

    payload = run_phase181_analysis(project_root=_PROJECT_ROOT, output_root=tmp_path)
    assert isinstance(payload, dict), 'run_phase181_analysis must return a dict'
    assert payload, 'run_phase181_analysis returned empty dict'
    assert payload['metrics']['r2'] >= 0.88


# ===========================================================================
# Phase 182 — Fifth less-synthetic adversarial (benchmark EE sparse release)
# ===========================================================================


@pytest.mark.unit
def test_phase182_artifact_exists() -> None:
    """Phase 182 artifact must exist on disk."""
    assert _P182.exists(), f"Missing: {_P182}"


@pytest.mark.unit
def test_phase182_artifact_json_valid() -> None:
    """Phase 182 artifact must be valid JSON."""
    assert _P182.exists(), f"Missing: {_P182}"
    data = json.loads(_P182.read_text(encoding='utf-8'))
    assert isinstance(data, dict), "Phase 182 artifact root must be a dict"


@pytest.mark.unit
def test_phase182_artifact_structure() -> None:
    """Phase 182 artifact must contain required top-level keys."""
    data = json.loads(_P182.read_text(encoding='utf-8'))
    for key in ('phase', 'benchmark', 'raw', 'corrected', 'correction'):
        assert key in data, f"Phase 182 artifact missing key: {key!r}"
    for subkey in ('combined_r2', 'sign_agreement'):
        assert subkey in data['raw'], f"Phase 182 raw missing key: {subkey!r}"
    for subkey in ('combined_r2', 'sign_agreement'):
        assert subkey in data['corrected'], f"Phase 182 corrected missing key: {subkey!r}"


@pytest.mark.unit
def test_phase182_metric_thresholds() -> None:
    """Phase 182 corrected combined_r2 >= 0.81; corrected sign_agreement >= 0.94.

    Report: raw combined_r2 = 0.4098; corrected combined_r2 = 0.8197;
    corrected sign_agreement = 0.9431.
    """
    data = json.loads(_P182.read_text(encoding='utf-8'))
    assert data['raw']['combined_r2'] < 0.45, (
        f"Phase 182 raw combined_r2 expected < 0.45, got {data['raw']['combined_r2']}"
    )
    assert data['corrected']['combined_r2'] >= 0.81, (
        f"Phase 182 corrected combined_r2 expected >= 0.81, "
        f"got {data['corrected']['combined_r2']}"
    )
    assert data['corrected']['sign_agreement'] >= 0.94, (
        f"Phase 182 corrected sign_agreement expected >= 0.94, "
        f"got {data['corrected']['sign_agreement']}"
    )


@pytest.mark.unit
def test_phase182_loader_importable() -> None:
    """phase182_analysis module must be importable and expose run_phase182_analysis."""
    mod = importlib.import_module('cwt.cgt.analysis.phase182_analysis')
    assert hasattr(mod, 'run_phase182_analysis'), (
        "phase182_analysis missing 'run_phase182_analysis'"
    )


@pytest.mark.unit
def test_phase182_loader_runs(tmp_path: Path) -> None:
    """run_phase182_analysis must return a non-empty dict."""
    from cwt.cgt.analysis.phase182_analysis import run_phase182_analysis

    payload = run_phase182_analysis(project_root=_PROJECT_ROOT, output_root=tmp_path)
    assert isinstance(payload, dict), 'run_phase182_analysis must return a dict'
    assert payload, 'run_phase182_analysis returned empty dict'
    assert payload['corrected']['combined_r2'] >= 0.81


# ===========================================================================
# Phase 183 — Bridge LOO all pilots and AE (benchmark scaffold family)
# ===========================================================================


@pytest.mark.unit
def test_phase183_artifact_exists() -> None:
    """Phase 183 artifact must exist on disk."""
    assert _P183.exists(), f"Missing: {_P183}"


@pytest.mark.unit
def test_phase183_artifact_json_valid() -> None:
    """Phase 183 artifact must be valid JSON."""
    assert _P183.exists(), f"Missing: {_P183}"
    data = json.loads(_P183.read_text(encoding='utf-8'))
    assert isinstance(data, dict), "Phase 183 artifact root must be a dict"


@pytest.mark.unit
def test_phase183_artifact_structure() -> None:
    """Phase 183 artifact must contain required top-level keys."""
    data = json.loads(_P183.read_text(encoding='utf-8'))
    for key in ('phase', 'mean_heldout_combined_r2', 'weakest_benchmark',
                'pilot_count', 'bridge_count'):
        assert key in data, f"Phase 183 artifact missing key: {key!r}"


@pytest.mark.unit
def test_phase183_metric_thresholds() -> None:
    """Phase 183 mean LOO held-out combined_r2 >= 0.88; bridge_count = 11.

    Report: mean_heldout_combined_r2 = 0.8838; weakest = BB_sensor_gap;
    pilot_count = 5; bridge_count = 11.
    """
    data = json.loads(_P183.read_text(encoding='utf-8'))
    assert data['mean_heldout_combined_r2'] >= 0.88, (
        f"Phase 183 mean_heldout_combined_r2 expected >= 0.88, "
        f"got {data['mean_heldout_combined_r2']}"
    )
    assert data['bridge_count'] == 11, (
        f"Phase 183 expected bridge_count = 11, got {data['bridge_count']}"
    )
    assert data['pilot_count'] == 5, (
        f"Phase 183 expected pilot_count = 5, got {data['pilot_count']}"
    )


@pytest.mark.unit
def test_phase183_loader_importable() -> None:
    """phase183_analysis module must be importable and expose run_phase183_analysis."""
    mod = importlib.import_module('cwt.cgt.analysis.phase183_analysis')
    assert hasattr(mod, 'run_phase183_analysis'), (
        "phase183_analysis missing 'run_phase183_analysis'"
    )


@pytest.mark.unit
def test_phase183_loader_runs(tmp_path: Path) -> None:
    """run_phase183_analysis must return a non-empty dict."""
    from cwt.cgt.analysis.phase183_analysis import run_phase183_analysis

    payload = run_phase183_analysis(project_root=_PROJECT_ROOT, output_root=tmp_path)
    assert isinstance(payload, dict), 'run_phase183_analysis must return a dict'
    assert payload, 'run_phase183_analysis returned empty dict'
    assert payload['mean_heldout_combined_r2'] >= 0.88


# ===========================================================================
# Phase 184 — Bridge correction v2 versus minimal (benchmark scaffold family)
# ===========================================================================


@pytest.mark.unit
def test_phase184_artifact_exists() -> None:
    """Phase 184 artifact must exist on disk."""
    assert _P184.exists(), f"Missing: {_P184}"


@pytest.mark.unit
def test_phase184_artifact_json_valid() -> None:
    """Phase 184 artifact must be valid JSON."""
    assert _P184.exists(), f"Missing: {_P184}"
    data = json.loads(_P184.read_text(encoding='utf-8'))
    assert isinstance(data, dict), "Phase 184 artifact root must be a dict"


@pytest.mark.unit
def test_phase184_artifact_structure() -> None:
    """Phase 184 artifact must contain required top-level keys."""
    data = json.loads(_P184.read_text(encoding='utf-8'))
    for key in ('phase', 'minimal_rule', 'tensor_law_v2', 'improvement'):
        assert key in data, f"Phase 184 artifact missing key: {key!r}"
    assert 'combined_r2' in data['minimal_rule'], (
        "Phase 184 minimal_rule missing 'combined_r2'"
    )
    assert 'combined_r2' in data['tensor_law_v2'], (
        "Phase 184 tensor_law_v2 missing 'combined_r2'"
    )


@pytest.mark.unit
def test_phase184_metric_thresholds() -> None:
    """Phase 184 tensor_law_v2 must outperform minimal_rule by >= 0.01.

    Report: minimal_rule combined_r2 = 0.8802; tensor_law_v2 combined_r2 = 0.8934;
    improvement = 0.0132.
    """
    data = json.loads(_P184.read_text(encoding='utf-8'))
    assert data['tensor_law_v2']['combined_r2'] > data['minimal_rule']['combined_r2'], (
        "Phase 184 tensor_law_v2 must exceed minimal_rule combined_r2"
    )
    assert data['improvement'] >= 0.01, (
        f"Phase 184 improvement expected >= 0.01, got {data['improvement']}"
    )
    assert data['tensor_law_v2']['combined_r2'] >= 0.89, (
        f"Phase 184 tensor_law_v2 combined_r2 expected >= 0.89, "
        f"got {data['tensor_law_v2']['combined_r2']}"
    )


@pytest.mark.unit
def test_phase184_loader_importable() -> None:
    """phase184_analysis module must be importable and expose run_phase184_analysis."""
    mod = importlib.import_module('cwt.cgt.analysis.phase184_analysis')
    assert hasattr(mod, 'run_phase184_analysis'), (
        "phase184_analysis missing 'run_phase184_analysis'"
    )


@pytest.mark.unit
def test_phase184_loader_runs(tmp_path: Path) -> None:
    """run_phase184_analysis must return a non-empty dict."""
    from cwt.cgt.analysis.phase184_analysis import run_phase184_analysis

    payload = run_phase184_analysis(project_root=_PROJECT_ROOT, output_root=tmp_path)
    assert isinstance(payload, dict), 'run_phase184_analysis must return a dict'
    assert payload, 'run_phase184_analysis returned empty dict'
    assert payload['tensor_law_v2']['combined_r2'] >= 0.89


# ===========================================================================
# Phase 185 — Bridge tensor geometry law v3 (benchmark scaffold family)
# ===========================================================================


@pytest.mark.unit
def test_phase185_artifact_exists() -> None:
    """Phase 185 artifact must exist on disk."""
    assert _P185.exists(), f"Missing: {_P185}"


@pytest.mark.unit
def test_phase185_artifact_json_valid() -> None:
    """Phase 185 artifact must be valid JSON."""
    assert _P185.exists(), f"Missing: {_P185}"
    data = json.loads(_P185.read_text(encoding='utf-8'))
    assert isinstance(data, dict), "Phase 185 artifact root must be a dict"


@pytest.mark.unit
def test_phase185_artifact_structure() -> None:
    """Phase 185 artifact must contain required top-level keys."""
    data = json.loads(_P185.read_text(encoding='utf-8'))
    for key in ('phase', 'candidate', 'raw', 'prior_corrected', 'corrected'):
        assert key in data, f"Phase 185 artifact missing key: {key!r}"
    assert 'combined_r2' in data['raw'], "Phase 185 raw missing 'combined_r2'"
    assert 'combined_r2' in data['prior_corrected'], (
        "Phase 185 prior_corrected missing 'combined_r2'"
    )
    for subkey in ('combined_r2', 'sign_agreement'):
        assert subkey in data['corrected'], f"Phase 185 corrected missing key: {subkey!r}"


@pytest.mark.unit
def test_phase185_metric_thresholds() -> None:
    """Phase 185 v3 corrected combined_r2 >= 0.91; corrected sign_agreement >= 0.97.

    Report: raw combined_r2 = 0.5561; prior_corrected combined_r2 = 0.9128;
    v3 corrected combined_r2 = 0.9189; v3 corrected sign_agreement = 0.9769.
    """
    data = json.loads(_P185.read_text(encoding='utf-8'))
    assert data['corrected']['combined_r2'] >= 0.91, (
        f"Phase 185 corrected combined_r2 expected >= 0.91, "
        f"got {data['corrected']['combined_r2']}"
    )
    assert data['corrected']['sign_agreement'] >= 0.97, (
        f"Phase 185 corrected sign_agreement expected >= 0.97, "
        f"got {data['corrected']['sign_agreement']}"
    )
    assert data['corrected']['combined_r2'] > data['prior_corrected']['combined_r2'], (
        "Phase 185 v3 corrected must exceed prior_corrected combined_r2"
    )


@pytest.mark.unit
def test_phase185_loader_importable() -> None:
    """phase185_analysis module must be importable and expose run_phase185_analysis."""
    mod = importlib.import_module('cwt.cgt.analysis.phase185_analysis')
    assert hasattr(mod, 'run_phase185_analysis'), (
        "phase185_analysis missing 'run_phase185_analysis'"
    )


@pytest.mark.unit
def test_phase185_loader_runs(tmp_path: Path) -> None:
    """run_phase185_analysis must return a non-empty dict."""
    from cwt.cgt.analysis.phase185_analysis import run_phase185_analysis

    payload = run_phase185_analysis(project_root=_PROJECT_ROOT, output_root=tmp_path)
    assert isinstance(payload, dict), 'run_phase185_analysis must return a dict'
    assert payload, 'run_phase185_analysis returned empty dict'
    assert payload['corrected']['combined_r2'] >= 0.91


# ===========================================================================
# Phase 186 — Bridge boundary refresh v4 (benchmark scaffold family)
# ===========================================================================


@pytest.mark.unit
def test_phase186_artifact_exists() -> None:
    """Phase 186 artifact must exist on disk."""
    assert _P186.exists(), f"Missing: {_P186}"


@pytest.mark.unit
def test_phase186_artifact_json_valid() -> None:
    """Phase 186 artifact must be valid JSON."""
    assert _P186.exists(), f"Missing: {_P186}"
    data = json.loads(_P186.read_text(encoding='utf-8'))
    assert isinstance(data, dict), "Phase 186 artifact root must be a dict"


@pytest.mark.unit
def test_phase186_artifact_structure() -> None:
    """Phase 186 artifact must contain required top-level keys."""
    data = json.loads(_P186.read_text(encoding='utf-8'))
    for key in ('phase', 'positive_band', 'adversarial_corrected_band',
                'weakest_positive', 'weakest_adversarial_corrected'):
        assert key in data, f"Phase 186 artifact missing key: {key!r}"
    assert isinstance(data['positive_band'], list) and len(data['positive_band']) == 2, (
        "Phase 186 positive_band must be a two-element list"
    )
    assert (isinstance(data['adversarial_corrected_band'], list)
            and len(data['adversarial_corrected_band']) == 2), (
        "Phase 186 adversarial_corrected_band must be a two-element list"
    )


@pytest.mark.unit
def test_phase186_metric_thresholds() -> None:
    """Phase 186 boundary bands must reflect eleven-bridge sweep acceptance bounds.

    Report: positive_band = [0.8748, 0.9397];
    adversarial_corrected_band = [0.8197, 0.9189].
    """
    data = json.loads(_P186.read_text(encoding='utf-8'))
    pos_lo, pos_hi = data['positive_band']
    adv_lo, adv_hi = data['adversarial_corrected_band']
    assert pos_lo >= 0.87, (
        f"Phase 186 positive_band lower bound expected >= 0.87, got {pos_lo}"
    )
    assert pos_hi >= 0.93, (
        f"Phase 186 positive_band upper bound expected >= 0.93, got {pos_hi}"
    )
    assert adv_lo >= 0.81, (
        f"Phase 186 adversarial_corrected_band lower bound expected >= 0.81, got {adv_lo}"
    )
    assert adv_hi >= 0.91, (
        f"Phase 186 adversarial_corrected_band upper bound expected >= 0.91, got {adv_hi}"
    )


@pytest.mark.unit
def test_phase186_loader_importable() -> None:
    """phase186_analysis module must be importable and expose run_phase186_analysis."""
    mod = importlib.import_module('cwt.cgt.analysis.phase186_analysis')
    assert hasattr(mod, 'run_phase186_analysis'), (
        "phase186_analysis missing 'run_phase186_analysis'"
    )


@pytest.mark.unit
def test_phase186_loader_runs(tmp_path: Path) -> None:
    """run_phase186_analysis must return a non-empty dict."""
    from cwt.cgt.analysis.phase186_analysis import run_phase186_analysis

    payload = run_phase186_analysis(project_root=_PROJECT_ROOT, output_root=tmp_path)
    assert isinstance(payload, dict), 'run_phase186_analysis must return a dict'
    assert payload, 'run_phase186_analysis returned empty dict'
    pos_lo, pos_hi = payload['positive_band']
    assert pos_hi >= 0.93
