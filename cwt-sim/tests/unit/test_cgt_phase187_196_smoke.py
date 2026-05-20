"""Smoke tests for CGT Phases 187-196 result artifacts and analysis modules.

Covers:
- Existence and JSON-validity of the Phase 187-196 artifacts.
- Importability of the phase analysis modules.
- Structural integrity of each artifact (top-level keys present).
- Metric thresholds derived from bundle reports and pinned to observed JSON values.
- Execution of run_phaseN_analysis() to verify correct output.

Benchmark layout:
  benchmark_AF_async_burst_lag/        — Phases 187, 188
  benchmark_FF_mixed_release_delay/    — Phases 189, 190
  benchmark_scaffold_family/           — Phases 191, 192, 193, 194, 195, 196

Phases with loaders (10):
  187, 188, 189, 190, 191, 192, 193, 194, 195, 196.

Phases 187-196 constitute the "twelfth-bridge and tensor-law v4" block
(bundle v7.8).
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
_AF_DIR = _PROJECT_ROOT / 'cgt_benchmarks' / 'results' / 'benchmark_AF_async_burst_lag'
_FF_DIR = _PROJECT_ROOT / 'cgt_benchmarks' / 'results' / 'benchmark_FF_mixed_release_delay'
_SCAFFOLD_DIR = _PROJECT_ROOT / 'cgt_benchmarks' / 'results' / 'benchmark_scaffold_family'

_P187 = _AF_DIR / 'benchmark_af_phase187_twelfth_bridge_positive.json'
_P188 = _AF_DIR / 'benchmark_af_phase188_bridge_adversarial_tensor_v3.json'
_P189 = _FF_DIR / 'benchmark_ff_phase189_sixth_less_synthetic_positive.json'
_P190 = _FF_DIR / 'benchmark_ff_phase190_sixth_less_synthetic_adversarial.json'
_P191 = _SCAFFOLD_DIR / 'benchmark_scaffold_phase191_bridge_holdout_expanded.json'
_P192 = _SCAFFOLD_DIR / 'benchmark_scaffold_phase192_bridge_correction_v3_vs_minimal_expanded.json'
_P193 = _SCAFFOLD_DIR / 'benchmark_scaffold_phase193_bridge_tensor_geometry_law_v4.json'
_P194 = _SCAFFOLD_DIR / 'benchmark_scaffold_phase194_pooled_twelve_bridge_positive.json'
_P195 = _SCAFFOLD_DIR / 'benchmark_scaffold_phase195_pooled_twelve_bridge_adversarial.json'
_P196 = _SCAFFOLD_DIR / 'benchmark_scaffold_phase196_bridge_boundary_refresh_v5.json'


# ===========================================================================
# Phase 187 — Twelfth bridge positive (benchmark AF async burst lag)
# ===========================================================================


@pytest.mark.unit
def test_phase187_artifact_exists() -> None:
    """Phase 187 artifact must exist on disk."""
    assert _P187.exists(), f"Missing: {_P187}"


@pytest.mark.unit
def test_phase187_artifact_json_valid() -> None:
    """Phase 187 artifact must be valid JSON."""
    assert _P187.exists(), f"Missing: {_P187}"
    data = json.loads(_P187.read_text(encoding='utf-8'))
    assert isinstance(data, dict), "Phase 187 artifact root must be a dict"


@pytest.mark.unit
def test_phase187_artifact_structure() -> None:
    """Phase 187 artifact must contain required top-level keys."""
    data = json.loads(_P187.read_text(encoding='utf-8'))
    for key in ('phase', 'benchmark', 'metrics'):
        assert key in data, f"Phase 187 artifact missing key: {key!r}"
    for subkey in ('r2', 'sign'):
        assert subkey in data['metrics'], f"Phase 187 metrics missing key: {subkey!r}"


@pytest.mark.unit
def test_phase187_metric_thresholds() -> None:
    """Phase 187 metrics must meet twelfth-bridge acceptance bounds.

    Report: switch-slice held-out R2 = 0.9271; sign = 1.0.
    """
    data = json.loads(_P187.read_text(encoding='utf-8'))
    assert data['metrics']['r2'] >= 0.92, (
        f"Phase 187 r2 expected >= 0.92, got {data['metrics']['r2']}"
    )
    assert data['metrics']['sign'] >= 0.99, (
        f"Phase 187 sign expected >= 0.99, got {data['metrics']['sign']}"
    )
    assert data['benchmark'] == 'AF_async_burst_lag', (
        f"Unexpected benchmark: {data['benchmark']!r}"
    )


@pytest.mark.unit
def test_phase187_loader_importable() -> None:
    """phase187_analysis module must be importable and expose run_phase187_analysis."""
    mod = importlib.import_module('cwt.cgt.analysis.phase187_analysis')
    assert hasattr(mod, 'run_phase187_analysis'), (
        "phase187_analysis missing 'run_phase187_analysis'"
    )


@pytest.mark.unit
def test_phase187_loader_runs(tmp_path: Path) -> None:
    """run_phase187_analysis must return a non-empty dict."""
    from cwt.cgt.analysis.phase187_analysis import run_phase187_analysis

    payload = run_phase187_analysis(project_root=_PROJECT_ROOT, output_root=tmp_path)
    assert isinstance(payload, dict), 'run_phase187_analysis must return a dict'
    assert payload, 'run_phase187_analysis returned empty dict'
    assert payload['metrics']['r2'] >= 0.92


# ===========================================================================
# Phase 188 — Twelfth bridge adversarial tensor v3 (benchmark AF async burst lag)
# ===========================================================================


@pytest.mark.unit
def test_phase188_artifact_exists() -> None:
    """Phase 188 artifact must exist on disk."""
    assert _P188.exists(), f"Missing: {_P188}"


@pytest.mark.unit
def test_phase188_artifact_json_valid() -> None:
    """Phase 188 artifact must be valid JSON."""
    assert _P188.exists(), f"Missing: {_P188}"
    data = json.loads(_P188.read_text(encoding='utf-8'))
    assert isinstance(data, dict), "Phase 188 artifact root must be a dict"


@pytest.mark.unit
def test_phase188_artifact_structure() -> None:
    """Phase 188 artifact must contain required top-level keys."""
    data = json.loads(_P188.read_text(encoding='utf-8'))
    for key in ('phase', 'raw', 'corrected', 'correction'):
        assert key in data, f"Phase 188 artifact missing key: {key!r}"
    for subkey in ('combined_r2', 'sign_agreement'):
        assert subkey in data['raw'], f"Phase 188 raw missing key: {subkey!r}"
    for subkey in ('combined_r2', 'sign_agreement'):
        assert subkey in data['corrected'], f"Phase 188 corrected missing key: {subkey!r}"


@pytest.mark.unit
def test_phase188_metric_thresholds() -> None:
    """Phase 188 corrected metrics must meet adversarial correction acceptance bounds.

    Report: raw combined_r2 = 0.5478; corrected combined_r2 = 0.8956;
    corrected sign_agreement = 0.9688.
    """
    data = json.loads(_P188.read_text(encoding='utf-8'))
    assert data['raw']['combined_r2'] < 0.60, (
        f"Phase 188 raw combined_r2 expected < 0.60, got {data['raw']['combined_r2']}"
    )
    assert data['corrected']['combined_r2'] >= 0.88, (
        f"Phase 188 corrected combined_r2 expected >= 0.88, "
        f"got {data['corrected']['combined_r2']}"
    )
    assert data['corrected']['sign_agreement'] >= 0.96, (
        f"Phase 188 corrected sign_agreement expected >= 0.96, "
        f"got {data['corrected']['sign_agreement']}"
    )


@pytest.mark.unit
def test_phase188_loader_importable() -> None:
    """phase188_analysis module must be importable and expose run_phase188_analysis."""
    mod = importlib.import_module('cwt.cgt.analysis.phase188_analysis')
    assert hasattr(mod, 'run_phase188_analysis'), (
        "phase188_analysis missing 'run_phase188_analysis'"
    )


@pytest.mark.unit
def test_phase188_loader_runs(tmp_path: Path) -> None:
    """run_phase188_analysis must return a non-empty dict."""
    from cwt.cgt.analysis.phase188_analysis import run_phase188_analysis

    payload = run_phase188_analysis(project_root=_PROJECT_ROOT, output_root=tmp_path)
    assert isinstance(payload, dict), 'run_phase188_analysis must return a dict'
    assert payload, 'run_phase188_analysis returned empty dict'
    assert payload['corrected']['combined_r2'] >= 0.88


# ===========================================================================
# Phase 189 — Sixth less-synthetic positive (benchmark FF mixed release delay)
# ===========================================================================


@pytest.mark.unit
def test_phase189_artifact_exists() -> None:
    """Phase 189 artifact must exist on disk."""
    assert _P189.exists(), f"Missing: {_P189}"


@pytest.mark.unit
def test_phase189_artifact_json_valid() -> None:
    """Phase 189 artifact must be valid JSON."""
    assert _P189.exists(), f"Missing: {_P189}"
    data = json.loads(_P189.read_text(encoding='utf-8'))
    assert isinstance(data, dict), "Phase 189 artifact root must be a dict"


@pytest.mark.unit
def test_phase189_artifact_structure() -> None:
    """Phase 189 artifact must contain required top-level keys."""
    data = json.loads(_P189.read_text(encoding='utf-8'))
    for key in ('phase', 'benchmark', 'metrics'):
        assert key in data, f"Phase 189 artifact missing key: {key!r}"
    for subkey in ('r2', 'sign'):
        assert subkey in data['metrics'], f"Phase 189 metrics missing key: {subkey!r}"


@pytest.mark.unit
def test_phase189_metric_thresholds() -> None:
    """Phase 189 less-synthetic positive R2 >= 0.88; sign >= 0.99.

    Report: held-out R2 = 0.8942; corr = 0.9648; sign = 1.0.
    """
    data = json.loads(_P189.read_text(encoding='utf-8'))
    assert data['metrics']['r2'] >= 0.88, (
        f"Phase 189 r2 expected >= 0.88, got {data['metrics']['r2']}"
    )
    assert data['metrics']['sign'] >= 0.99, (
        f"Phase 189 sign expected >= 0.99, got {data['metrics']['sign']}"
    )
    assert data['benchmark'] == 'FF_mixed_release_delay', (
        f"Unexpected benchmark: {data['benchmark']!r}"
    )


@pytest.mark.unit
def test_phase189_loader_importable() -> None:
    """phase189_analysis module must be importable and expose run_phase189_analysis."""
    mod = importlib.import_module('cwt.cgt.analysis.phase189_analysis')
    assert hasattr(mod, 'run_phase189_analysis'), (
        "phase189_analysis missing 'run_phase189_analysis'"
    )


@pytest.mark.unit
def test_phase189_loader_runs(tmp_path: Path) -> None:
    """run_phase189_analysis must return a non-empty dict."""
    from cwt.cgt.analysis.phase189_analysis import run_phase189_analysis

    payload = run_phase189_analysis(project_root=_PROJECT_ROOT, output_root=tmp_path)
    assert isinstance(payload, dict), 'run_phase189_analysis must return a dict'
    assert payload, 'run_phase189_analysis returned empty dict'
    assert payload['metrics']['r2'] >= 0.88


# ===========================================================================
# Phase 190 — Sixth less-synthetic adversarial (benchmark FF mixed release delay)
# ===========================================================================


@pytest.mark.unit
def test_phase190_artifact_exists() -> None:
    """Phase 190 artifact must exist on disk."""
    assert _P190.exists(), f"Missing: {_P190}"


@pytest.mark.unit
def test_phase190_artifact_json_valid() -> None:
    """Phase 190 artifact must be valid JSON."""
    assert _P190.exists(), f"Missing: {_P190}"
    data = json.loads(_P190.read_text(encoding='utf-8'))
    assert isinstance(data, dict), "Phase 190 artifact root must be a dict"


@pytest.mark.unit
def test_phase190_artifact_structure() -> None:
    """Phase 190 artifact must contain required top-level keys."""
    data = json.loads(_P190.read_text(encoding='utf-8'))
    for key in ('phase', 'benchmark', 'raw', 'corrected', 'correction'):
        assert key in data, f"Phase 190 artifact missing key: {key!r}"
    for subkey in ('combined_r2', 'sign_agreement'):
        assert subkey in data['raw'], f"Phase 190 raw missing key: {subkey!r}"
    for subkey in ('combined_r2', 'sign_agreement'):
        assert subkey in data['corrected'], f"Phase 190 corrected missing key: {subkey!r}"


@pytest.mark.unit
def test_phase190_metric_thresholds() -> None:
    """Phase 190 corrected combined_r2 >= 0.82; corrected sign_agreement >= 0.93.

    Report: raw combined_r2 = 0.4214; corrected combined_r2 = 0.8317;
    corrected sign_agreement = 0.9342.
    """
    data = json.loads(_P190.read_text(encoding='utf-8'))
    assert data['raw']['combined_r2'] < 0.45, (
        f"Phase 190 raw combined_r2 expected < 0.45, got {data['raw']['combined_r2']}"
    )
    assert data['corrected']['combined_r2'] >= 0.82, (
        f"Phase 190 corrected combined_r2 expected >= 0.82, "
        f"got {data['corrected']['combined_r2']}"
    )
    assert data['corrected']['sign_agreement'] >= 0.93, (
        f"Phase 190 corrected sign_agreement expected >= 0.93, "
        f"got {data['corrected']['sign_agreement']}"
    )


@pytest.mark.unit
def test_phase190_loader_importable() -> None:
    """phase190_analysis module must be importable and expose run_phase190_analysis."""
    mod = importlib.import_module('cwt.cgt.analysis.phase190_analysis')
    assert hasattr(mod, 'run_phase190_analysis'), (
        "phase190_analysis missing 'run_phase190_analysis'"
    )


@pytest.mark.unit
def test_phase190_loader_runs(tmp_path: Path) -> None:
    """run_phase190_analysis must return a non-empty dict."""
    from cwt.cgt.analysis.phase190_analysis import run_phase190_analysis

    payload = run_phase190_analysis(project_root=_PROJECT_ROOT, output_root=tmp_path)
    assert isinstance(payload, dict), 'run_phase190_analysis must return a dict'
    assert payload, 'run_phase190_analysis returned empty dict'
    assert payload['corrected']['combined_r2'] >= 0.82


# ===========================================================================
# Phase 191 — Bridge LOO holdout expanded (benchmark scaffold family)
# ===========================================================================


@pytest.mark.unit
def test_phase191_artifact_exists() -> None:
    """Phase 191 artifact must exist on disk."""
    assert _P191.exists(), f"Missing: {_P191}"


@pytest.mark.unit
def test_phase191_artifact_json_valid() -> None:
    """Phase 191 artifact must be valid JSON."""
    assert _P191.exists(), f"Missing: {_P191}"
    data = json.loads(_P191.read_text(encoding='utf-8'))
    assert isinstance(data, dict), "Phase 191 artifact root must be a dict"


@pytest.mark.unit
def test_phase191_artifact_structure() -> None:
    """Phase 191 artifact must contain required top-level keys."""
    data = json.loads(_P191.read_text(encoding='utf-8'))
    for key in ('phase', 'mean_heldout_combined_r2', 'weakest_benchmark',
                'pilot_count', 'bridge_count'):
        assert key in data, f"Phase 191 artifact missing key: {key!r}"


@pytest.mark.unit
def test_phase191_metric_thresholds() -> None:
    """Phase 191 mean LOO held-out combined_r2 >= 0.88; bridge_count = 12.

    Report: mean_heldout_combined_r2 = 0.8859; weakest = FF_mixed_release_delay;
    pilot_count = 6; bridge_count = 12.
    """
    data = json.loads(_P191.read_text(encoding='utf-8'))
    assert data['mean_heldout_combined_r2'] >= 0.88, (
        f"Phase 191 mean_heldout_combined_r2 expected >= 0.88, "
        f"got {data['mean_heldout_combined_r2']}"
    )
    assert data['bridge_count'] == 12, (
        f"Phase 191 expected bridge_count = 12, got {data['bridge_count']}"
    )
    assert data['pilot_count'] == 6, (
        f"Phase 191 expected pilot_count = 6, got {data['pilot_count']}"
    )


@pytest.mark.unit
def test_phase191_loader_importable() -> None:
    """phase191_analysis module must be importable and expose run_phase191_analysis."""
    mod = importlib.import_module('cwt.cgt.analysis.phase191_analysis')
    assert hasattr(mod, 'run_phase191_analysis'), (
        "phase191_analysis missing 'run_phase191_analysis'"
    )


@pytest.mark.unit
def test_phase191_loader_runs(tmp_path: Path) -> None:
    """run_phase191_analysis must return a non-empty dict."""
    from cwt.cgt.analysis.phase191_analysis import run_phase191_analysis

    payload = run_phase191_analysis(project_root=_PROJECT_ROOT, output_root=tmp_path)
    assert isinstance(payload, dict), 'run_phase191_analysis must return a dict'
    assert payload, 'run_phase191_analysis returned empty dict'
    assert payload['mean_heldout_combined_r2'] >= 0.88


# ===========================================================================
# Phase 192 — Bridge correction v3 vs minimal expanded (benchmark scaffold family)
# ===========================================================================


@pytest.mark.unit
def test_phase192_artifact_exists() -> None:
    """Phase 192 artifact must exist on disk."""
    assert _P192.exists(), f"Missing: {_P192}"


@pytest.mark.unit
def test_phase192_artifact_json_valid() -> None:
    """Phase 192 artifact must be valid JSON."""
    assert _P192.exists(), f"Missing: {_P192}"
    data = json.loads(_P192.read_text(encoding='utf-8'))
    assert isinstance(data, dict), "Phase 192 artifact root must be a dict"


@pytest.mark.unit
def test_phase192_artifact_structure() -> None:
    """Phase 192 artifact must contain required top-level keys."""
    data = json.loads(_P192.read_text(encoding='utf-8'))
    for key in ('phase', 'minimal_rule', 'tensor_law_v3', 'improvement'):
        assert key in data, f"Phase 192 artifact missing key: {key!r}"
    assert 'combined_r2' in data['minimal_rule'], (
        "Phase 192 minimal_rule missing 'combined_r2'"
    )
    assert 'combined_r2' in data['tensor_law_v3'], (
        "Phase 192 tensor_law_v3 missing 'combined_r2'"
    )


@pytest.mark.unit
def test_phase192_metric_thresholds() -> None:
    """Phase 192 tensor_law_v3 must outperform minimal_rule by >= 0.01.

    Report: minimal_rule combined_r2 = 0.8821; tensor_law_v3 combined_r2 = 0.8958;
    improvement = 0.0137.
    """
    data = json.loads(_P192.read_text(encoding='utf-8'))
    assert data['tensor_law_v3']['combined_r2'] > data['minimal_rule']['combined_r2'], (
        "Phase 192 tensor_law_v3 must exceed minimal_rule combined_r2"
    )
    assert data['improvement'] >= 0.01, (
        f"Phase 192 improvement expected >= 0.01, got {data['improvement']}"
    )
    assert data['tensor_law_v3']['combined_r2'] >= 0.89, (
        f"Phase 192 tensor_law_v3 combined_r2 expected >= 0.89, "
        f"got {data['tensor_law_v3']['combined_r2']}"
    )


@pytest.mark.unit
def test_phase192_loader_importable() -> None:
    """phase192_analysis module must be importable and expose run_phase192_analysis."""
    mod = importlib.import_module('cwt.cgt.analysis.phase192_analysis')
    assert hasattr(mod, 'run_phase192_analysis'), (
        "phase192_analysis missing 'run_phase192_analysis'"
    )


@pytest.mark.unit
def test_phase192_loader_runs(tmp_path: Path) -> None:
    """run_phase192_analysis must return a non-empty dict."""
    from cwt.cgt.analysis.phase192_analysis import run_phase192_analysis

    payload = run_phase192_analysis(project_root=_PROJECT_ROOT, output_root=tmp_path)
    assert isinstance(payload, dict), 'run_phase192_analysis must return a dict'
    assert payload, 'run_phase192_analysis returned empty dict'
    assert payload['tensor_law_v3']['combined_r2'] >= 0.89


# ===========================================================================
# Phase 193 — Bridge tensor geometry law v4 (benchmark scaffold family)
# ===========================================================================


@pytest.mark.unit
def test_phase193_artifact_exists() -> None:
    """Phase 193 artifact must exist on disk."""
    assert _P193.exists(), f"Missing: {_P193}"


@pytest.mark.unit
def test_phase193_artifact_json_valid() -> None:
    """Phase 193 artifact must be valid JSON."""
    assert _P193.exists(), f"Missing: {_P193}"
    data = json.loads(_P193.read_text(encoding='utf-8'))
    assert isinstance(data, dict), "Phase 193 artifact root must be a dict"


@pytest.mark.unit
def test_phase193_artifact_structure() -> None:
    """Phase 193 artifact must contain required top-level keys."""
    data = json.loads(_P193.read_text(encoding='utf-8'))
    for key in ('phase', 'candidate', 'raw', 'prior_corrected', 'corrected'):
        assert key in data, f"Phase 193 artifact missing key: {key!r}"
    assert 'combined_r2' in data['raw'], "Phase 193 raw missing 'combined_r2'"
    assert 'combined_r2' in data['prior_corrected'], (
        "Phase 193 prior_corrected missing 'combined_r2'"
    )
    for subkey in ('combined_r2', 'sign_agreement'):
        assert subkey in data['corrected'], f"Phase 193 corrected missing key: {subkey!r}"


@pytest.mark.unit
def test_phase193_metric_thresholds() -> None:
    """Phase 193 v4 corrected combined_r2 >= 0.92; corrected sign_agreement >= 0.97.

    Report: raw combined_r2 = 0.5572; prior_corrected combined_r2 = 0.9189;
    v4 corrected combined_r2 = 0.9217; v4 corrected sign_agreement = 0.9778.
    """
    data = json.loads(_P193.read_text(encoding='utf-8'))
    assert data['corrected']['combined_r2'] >= 0.92, (
        f"Phase 193 corrected combined_r2 expected >= 0.92, "
        f"got {data['corrected']['combined_r2']}"
    )
    assert data['corrected']['sign_agreement'] >= 0.97, (
        f"Phase 193 corrected sign_agreement expected >= 0.97, "
        f"got {data['corrected']['sign_agreement']}"
    )
    assert data['corrected']['combined_r2'] > data['prior_corrected']['combined_r2'], (
        "Phase 193 v4 corrected must exceed prior_corrected combined_r2"
    )


@pytest.mark.unit
def test_phase193_loader_importable() -> None:
    """phase193_analysis module must be importable and expose run_phase193_analysis."""
    mod = importlib.import_module('cwt.cgt.analysis.phase193_analysis')
    assert hasattr(mod, 'run_phase193_analysis'), (
        "phase193_analysis missing 'run_phase193_analysis'"
    )


@pytest.mark.unit
def test_phase193_loader_runs(tmp_path: Path) -> None:
    """run_phase193_analysis must return a non-empty dict."""
    from cwt.cgt.analysis.phase193_analysis import run_phase193_analysis

    payload = run_phase193_analysis(project_root=_PROJECT_ROOT, output_root=tmp_path)
    assert isinstance(payload, dict), 'run_phase193_analysis must return a dict'
    assert payload, 'run_phase193_analysis returned empty dict'
    assert payload['corrected']['combined_r2'] >= 0.92


# ===========================================================================
# Phase 194 — Pooled twelve-bridge positive (benchmark scaffold family)
# ===========================================================================


@pytest.mark.unit
def test_phase194_artifact_exists() -> None:
    """Phase 194 artifact must exist on disk."""
    assert _P194.exists(), f"Missing: {_P194}"


@pytest.mark.unit
def test_phase194_artifact_json_valid() -> None:
    """Phase 194 artifact must be valid JSON."""
    assert _P194.exists(), f"Missing: {_P194}"
    data = json.loads(_P194.read_text(encoding='utf-8'))
    assert isinstance(data, dict), "Phase 194 artifact root must be a dict"


@pytest.mark.unit
def test_phase194_artifact_structure() -> None:
    """Phase 194 artifact must contain required top-level keys."""
    data = json.loads(_P194.read_text(encoding='utf-8'))
    for key in ('phase', 'rule', 'metrics', 'benchmark_count'):
        assert key in data, f"Phase 194 artifact missing key: {key!r}"
    for subkey in ('combined_r2', 'sign'):
        assert subkey in data['metrics'], f"Phase 194 metrics missing key: {subkey!r}"


@pytest.mark.unit
def test_phase194_metric_thresholds() -> None:
    """Phase 194 pooled twelve-bridge positive combined_r2 >= 0.94; sign >= 0.99.

    Report: combined_r2 = 0.9409; corr = 0.9871; sign = 0.9956; benchmark_count = 12.
    """
    data = json.loads(_P194.read_text(encoding='utf-8'))
    assert data['metrics']['combined_r2'] >= 0.94, (
        f"Phase 194 combined_r2 expected >= 0.94, got {data['metrics']['combined_r2']}"
    )
    assert data['metrics']['sign'] >= 0.99, (
        f"Phase 194 sign expected >= 0.99, got {data['metrics']['sign']}"
    )
    assert data['benchmark_count'] == 12, (
        f"Phase 194 expected benchmark_count = 12, got {data['benchmark_count']}"
    )


@pytest.mark.unit
def test_phase194_loader_importable() -> None:
    """phase194_analysis module must be importable and expose run_phase194_analysis."""
    mod = importlib.import_module('cwt.cgt.analysis.phase194_analysis')
    assert hasattr(mod, 'run_phase194_analysis'), (
        "phase194_analysis missing 'run_phase194_analysis'"
    )


@pytest.mark.unit
def test_phase194_loader_runs(tmp_path: Path) -> None:
    """run_phase194_analysis must return a non-empty dict."""
    from cwt.cgt.analysis.phase194_analysis import run_phase194_analysis

    payload = run_phase194_analysis(project_root=_PROJECT_ROOT, output_root=tmp_path)
    assert isinstance(payload, dict), 'run_phase194_analysis must return a dict'
    assert payload, 'run_phase194_analysis returned empty dict'
    assert payload['metrics']['combined_r2'] >= 0.94


# ===========================================================================
# Phase 195 — Pooled twelve-bridge adversarial (benchmark scaffold family)
# ===========================================================================


@pytest.mark.unit
def test_phase195_artifact_exists() -> None:
    """Phase 195 artifact must exist on disk."""
    assert _P195.exists(), f"Missing: {_P195}"


@pytest.mark.unit
def test_phase195_artifact_json_valid() -> None:
    """Phase 195 artifact must be valid JSON."""
    assert _P195.exists(), f"Missing: {_P195}"
    data = json.loads(_P195.read_text(encoding='utf-8'))
    assert isinstance(data, dict), "Phase 195 artifact root must be a dict"


@pytest.mark.unit
def test_phase195_artifact_structure() -> None:
    """Phase 195 artifact must contain required top-level keys."""
    data = json.loads(_P195.read_text(encoding='utf-8'))
    for key in ('phase', 'rule', 'raw', 'corrected', 'correction', 'benchmark_count'):
        assert key in data, f"Phase 195 artifact missing key: {key!r}"
    for subkey in ('combined_r2', 'sign_agreement'):
        assert subkey in data['raw'], f"Phase 195 raw missing key: {subkey!r}"
    for subkey in ('combined_r2', 'sign_agreement'):
        assert subkey in data['corrected'], f"Phase 195 corrected missing key: {subkey!r}"


@pytest.mark.unit
def test_phase195_metric_thresholds() -> None:
    """Phase 195 corrected combined_r2 >= 0.91; corrected sign_agreement >= 0.97.

    Report: raw combined_r2 = 0.5584; corrected combined_r2 = 0.9146;
    corrected sign_agreement = 0.9739; benchmark_count = 12.
    """
    data = json.loads(_P195.read_text(encoding='utf-8'))
    assert data['raw']['combined_r2'] < 0.60, (
        f"Phase 195 raw combined_r2 expected < 0.60, got {data['raw']['combined_r2']}"
    )
    assert data['corrected']['combined_r2'] >= 0.91, (
        f"Phase 195 corrected combined_r2 expected >= 0.91, "
        f"got {data['corrected']['combined_r2']}"
    )
    assert data['corrected']['sign_agreement'] >= 0.97, (
        f"Phase 195 corrected sign_agreement expected >= 0.97, "
        f"got {data['corrected']['sign_agreement']}"
    )
    assert data['benchmark_count'] == 12, (
        f"Phase 195 expected benchmark_count = 12, got {data['benchmark_count']}"
    )


@pytest.mark.unit
def test_phase195_loader_importable() -> None:
    """phase195_analysis module must be importable and expose run_phase195_analysis."""
    mod = importlib.import_module('cwt.cgt.analysis.phase195_analysis')
    assert hasattr(mod, 'run_phase195_analysis'), (
        "phase195_analysis missing 'run_phase195_analysis'"
    )


@pytest.mark.unit
def test_phase195_loader_runs(tmp_path: Path) -> None:
    """run_phase195_analysis must return a non-empty dict."""
    from cwt.cgt.analysis.phase195_analysis import run_phase195_analysis

    payload = run_phase195_analysis(project_root=_PROJECT_ROOT, output_root=tmp_path)
    assert isinstance(payload, dict), 'run_phase195_analysis must return a dict'
    assert payload, 'run_phase195_analysis returned empty dict'
    assert payload['corrected']['combined_r2'] >= 0.91


# ===========================================================================
# Phase 196 — Bridge boundary refresh v5 (benchmark scaffold family)
# ===========================================================================


@pytest.mark.unit
def test_phase196_artifact_exists() -> None:
    """Phase 196 artifact must exist on disk."""
    assert _P196.exists(), f"Missing: {_P196}"


@pytest.mark.unit
def test_phase196_artifact_json_valid() -> None:
    """Phase 196 artifact must be valid JSON."""
    assert _P196.exists(), f"Missing: {_P196}"
    data = json.loads(_P196.read_text(encoding='utf-8'))
    assert isinstance(data, dict), "Phase 196 artifact root must be a dict"


@pytest.mark.unit
def test_phase196_artifact_structure() -> None:
    """Phase 196 artifact must contain required top-level keys."""
    data = json.loads(_P196.read_text(encoding='utf-8'))
    for key in ('phase', 'positive_band', 'adversarial_corrected_band',
                'weakest_positive', 'weakest_adversarial_corrected'):
        assert key in data, f"Phase 196 artifact missing key: {key!r}"
    assert isinstance(data['positive_band'], list) and len(data['positive_band']) == 2, (
        "Phase 196 positive_band must be a two-element list"
    )
    assert (isinstance(data['adversarial_corrected_band'], list)
            and len(data['adversarial_corrected_band']) == 2), (
        "Phase 196 adversarial_corrected_band must be a two-element list"
    )


@pytest.mark.unit
def test_phase196_metric_thresholds() -> None:
    """Phase 196 boundary bands must reflect twelve-bridge sweep acceptance bounds.

    Report: positive_band = [0.8748, 0.9409];
    adversarial_corrected_band = [0.8197, 0.9217].
    """
    data = json.loads(_P196.read_text(encoding='utf-8'))
    pos_lo, pos_hi = data['positive_band']
    adv_lo, adv_hi = data['adversarial_corrected_band']
    assert pos_lo >= 0.87, (
        f"Phase 196 positive_band lower bound expected >= 0.87, got {pos_lo}"
    )
    assert pos_hi >= 0.94, (
        f"Phase 196 positive_band upper bound expected >= 0.94, got {pos_hi}"
    )
    assert adv_lo >= 0.81, (
        f"Phase 196 adversarial_corrected_band lower bound expected >= 0.81, got {adv_lo}"
    )
    assert adv_hi >= 0.92, (
        f"Phase 196 adversarial_corrected_band upper bound expected >= 0.92, got {adv_hi}"
    )


@pytest.mark.unit
def test_phase196_loader_importable() -> None:
    """phase196_analysis module must be importable and expose run_phase196_analysis."""
    mod = importlib.import_module('cwt.cgt.analysis.phase196_analysis')
    assert hasattr(mod, 'run_phase196_analysis'), (
        "phase196_analysis missing 'run_phase196_analysis'"
    )


@pytest.mark.unit
def test_phase196_loader_runs(tmp_path: Path) -> None:
    """run_phase196_analysis must return a non-empty dict."""
    from cwt.cgt.analysis.phase196_analysis import run_phase196_analysis

    payload = run_phase196_analysis(project_root=_PROJECT_ROOT, output_root=tmp_path)
    assert isinstance(payload, dict), 'run_phase196_analysis must return a dict'
    assert payload, 'run_phase196_analysis returned empty dict'
    pos_lo, pos_hi = payload['positive_band']
    assert pos_hi >= 0.94
