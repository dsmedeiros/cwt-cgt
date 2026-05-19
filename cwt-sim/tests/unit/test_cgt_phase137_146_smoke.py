"""Smoke tests for CGT Phases 137-146 result artifacts and analysis modules.

Covers:
- Existence and JSON-validity of the Phase 137-146 artifacts.
- Importability of the phase analysis modules.
- Structural integrity of each artifact (top-level keys present).
- Metric thresholds derived from bundle reports and pinned to observed JSON values.
- Execution of run_phaseN_analysis() to verify correct output.

Benchmark layout:
  benchmark_Z_event_burst/     — Phases 137-138 (seventh bridge positive + adversarial)
  benchmark_scaffold_family/   — Phases 139-140, 144-146 (family audit / comparison / pooled seven)
  benchmark_AA_less_synthetic/ — Phases 142-143 (less-synthetic pilot positive + adversarial)

Phase 141 is a bridge boundary/failure pack write-up (report only, no JSON artifact).
Phases 137-146 constitute the "seven-bridge and pilot" block (bundle v7.3).
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
_Z_DIR = _PROJECT_ROOT / 'cgt_benchmarks' / 'results' / 'benchmark_Z_event_burst'
_AA_DIR = _PROJECT_ROOT / 'cgt_benchmarks' / 'results' / 'benchmark_AA_less_synthetic'

_P137 = _Z_DIR / 'benchmark_z_phase137_seventh_bridge_positive.json'
_P138 = _Z_DIR / 'benchmark_z_phase138_bridge_adversarial.json'
_P139 = _SCAFFOLD_DIR / 'benchmark_scaffold_phase139_bridge_family_adversarial_summary.json'
_P140 = _SCAFFOLD_DIR / 'benchmark_scaffold_phase140_bridge_correction_comparison.json'
_P142 = _AA_DIR / 'benchmark_aa_phase142_less_synthetic_bridge_positive.json'
_P143 = _AA_DIR / 'benchmark_aa_phase143_less_synthetic_bridge_adversarial.json'
_P144 = _SCAFFOLD_DIR / 'benchmark_scaffold_phase144_pooled_seven_bridge_positive.json'
_P145 = _SCAFFOLD_DIR / 'benchmark_scaffold_phase145_pooled_seven_bridge_adversarial.json'
_P146 = _SCAFFOLD_DIR / 'benchmark_scaffold_phase146_bridge_pilot_transfer_summary.json'


# ===========================================================================
# Phase 137 — Seventh bridge positive (benchmark Z event-burst)
# ===========================================================================


@pytest.mark.unit
def test_phase137_artifact_exists() -> None:
    """Phase 137 artifact must exist on disk."""
    assert _P137.exists(), f"Missing: {_P137}"


@pytest.mark.unit
def test_phase137_artifact_json_valid() -> None:
    """Phase 137 artifact must be valid JSON."""
    assert _P137.exists(), f"Missing: {_P137}"
    data = json.loads(_P137.read_text(encoding='utf-8'))
    assert isinstance(data, dict), "Phase 137 artifact root must be a dict"


@pytest.mark.unit
def test_phase137_artifact_structure() -> None:
    """Phase 137 artifact must contain required top-level keys."""
    data = json.loads(_P137.read_text(encoding='utf-8'))
    for key in ('phase', 'benchmark', 'r2', 'sign', 'verdict'):
        assert key in data, f"Phase 137 artifact missing key: {key!r}"


@pytest.mark.unit
def test_phase137_metric_thresholds() -> None:
    """Phase 137 metrics must meet seventh-bridge acceptance bounds.

    Report: held-out combined R2 = 0.9285; sign agreement = 1.0.
    """
    data = json.loads(_P137.read_text(encoding='utf-8'))
    assert data['r2'] >= 0.92, (
        f"Phase 137 r2 expected >= 0.92, got {data['r2']}"
    )
    assert data['sign'] >= 0.99, (
        f"Phase 137 sign expected >= 0.99, got {data['sign']}"
    )
    assert data['verdict'] == 'supportive_bridge_positive', (
        f"Unexpected verdict: {data['verdict']!r}"
    )


@pytest.mark.unit
def test_phase137_loader_importable() -> None:
    """phase137_analysis module must be importable and expose run_phase137_analysis."""
    mod = importlib.import_module('cwt.cgt.analysis.phase137_analysis')
    assert hasattr(mod, 'run_phase137_analysis'), (
        "phase137_analysis missing 'run_phase137_analysis'"
    )


@pytest.mark.unit
def test_phase137_loader_runs(tmp_path: Path) -> None:
    """run_phase137_analysis must return a non-empty dict."""
    from cwt.cgt.analysis.phase137_analysis import run_phase137_analysis

    payload = run_phase137_analysis(project_root=_PROJECT_ROOT, output_root=tmp_path)
    assert isinstance(payload, dict), 'run_phase137_analysis must return a dict'
    assert payload, 'run_phase137_analysis returned empty dict'
    assert payload['r2'] >= 0.92


# ===========================================================================
# Phase 138 — Bridge adversarial on benchmark Z (event-burst)
# ===========================================================================


@pytest.mark.unit
def test_phase138_artifact_exists() -> None:
    """Phase 138 artifact must exist on disk."""
    assert _P138.exists(), f"Missing: {_P138}"


@pytest.mark.unit
def test_phase138_artifact_json_valid() -> None:
    """Phase 138 artifact must be valid JSON."""
    assert _P138.exists(), f"Missing: {_P138}"
    data = json.loads(_P138.read_text(encoding='utf-8'))
    assert isinstance(data, dict), "Phase 138 artifact root must be a dict"


@pytest.mark.unit
def test_phase138_artifact_structure() -> None:
    """Phase 138 artifact must contain required top-level keys."""
    data = json.loads(_P138.read_text(encoding='utf-8'))
    for key in ('phase', 'benchmark', 'raw', 'corrected', 'verdict'):
        assert key in data, f"Phase 138 artifact missing key: {key!r}"
    for subkey in ('r2', 'sign'):
        assert subkey in data['raw'], f"Phase 138 raw missing key: {subkey!r}"
    for subkey in ('r2', 'sign', 'corr'):
        assert subkey in data['corrected'], f"Phase 138 corrected missing key: {subkey!r}"


@pytest.mark.unit
def test_phase138_metric_thresholds() -> None:
    """Phase 138 must show adversarial degradation and correction recovery on benchmark Z.

    Report: raw R2 = 0.5762; corrected R2 = 0.9031; corrected sign = 0.9583.
    """
    data = json.loads(_P138.read_text(encoding='utf-8'))
    assert data['raw']['r2'] < 0.65, (
        f"Phase 138 raw r2 expected < 0.65 (adversarial degrades), "
        f"got {data['raw']['r2']}"
    )
    assert data['corrected']['r2'] >= 0.89, (
        f"Phase 138 corrected r2 expected >= 0.89, got {data['corrected']['r2']}"
    )
    assert data['corrected']['sign'] >= 0.94, (
        f"Phase 138 corrected sign expected >= 0.94, got {data['corrected']['sign']}"
    )
    assert data['verdict'] == 'supportive_after_tensor_compactness_correction', (
        f"Unexpected verdict: {data['verdict']!r}"
    )


@pytest.mark.unit
def test_phase138_loader_importable() -> None:
    """phase138_analysis module must be importable and expose run_phase138_analysis."""
    mod = importlib.import_module('cwt.cgt.analysis.phase138_analysis')
    assert hasattr(mod, 'run_phase138_analysis'), (
        "phase138_analysis missing 'run_phase138_analysis'"
    )


@pytest.mark.unit
def test_phase138_loader_runs(tmp_path: Path) -> None:
    """run_phase138_analysis must return a non-empty dict."""
    from cwt.cgt.analysis.phase138_analysis import run_phase138_analysis

    payload = run_phase138_analysis(project_root=_PROJECT_ROOT, output_root=tmp_path)
    assert isinstance(payload, dict), 'run_phase138_analysis must return a dict'
    assert payload, 'run_phase138_analysis returned empty dict'
    assert payload['corrected']['r2'] >= 0.89


# ===========================================================================
# Phase 139 — Bridge family adversarial summary (benchmark scaffold family)
# ===========================================================================


@pytest.mark.unit
def test_phase139_artifact_exists() -> None:
    """Phase 139 artifact must exist on disk."""
    assert _P139.exists(), f"Missing: {_P139}"


@pytest.mark.unit
def test_phase139_artifact_json_valid() -> None:
    """Phase 139 artifact must be valid JSON."""
    assert _P139.exists(), f"Missing: {_P139}"
    data = json.loads(_P139.read_text(encoding='utf-8'))
    assert isinstance(data, dict), "Phase 139 artifact root must be a dict"


@pytest.mark.unit
def test_phase139_artifact_structure() -> None:
    """Phase 139 artifact must contain required top-level keys."""
    data = json.loads(_P139.read_text(encoding='utf-8'))
    for key in ('phase', 'families', 'aggregate_raw', 'aggregate_corr', 'aggregate_sign', 'verdict'):
        assert key in data, f"Phase 139 artifact missing key: {key!r}"
    for family in ('observed', 'partial_delay', 'topology_like', 'censored', 'event_burst'):
        assert family in data['families'], f"Phase 139 families missing entry: {family!r}"


@pytest.mark.unit
def test_phase139_metric_thresholds() -> None:
    """Phase 139 family-grouped adversarial corrected aggregate R2 >= 0.88.

    Report: raw = 0.5529; corrected = 0.8928; sign = 0.9208.
    """
    data = json.loads(_P139.read_text(encoding='utf-8'))
    assert data['aggregate_raw'] < 0.65, (
        f"Phase 139 aggregate_raw expected < 0.65, got {data['aggregate_raw']}"
    )
    assert data['aggregate_corr'] >= 0.88, (
        f"Phase 139 aggregate_corr expected >= 0.88, got {data['aggregate_corr']}"
    )
    assert data['aggregate_sign'] >= 0.90, (
        f"Phase 139 aggregate_sign expected >= 0.90, got {data['aggregate_sign']}"
    )
    assert data['verdict'] == 'family_grouping_supportive_after_correction', (
        f"Unexpected verdict: {data['verdict']!r}"
    )


@pytest.mark.unit
def test_phase139_loader_importable() -> None:
    """phase139_analysis module must be importable and expose run_phase139_analysis."""
    mod = importlib.import_module('cwt.cgt.analysis.phase139_analysis')
    assert hasattr(mod, 'run_phase139_analysis'), (
        "phase139_analysis missing 'run_phase139_analysis'"
    )


@pytest.mark.unit
def test_phase139_loader_runs(tmp_path: Path) -> None:
    """run_phase139_analysis must return a non-empty dict."""
    from cwt.cgt.analysis.phase139_analysis import run_phase139_analysis

    payload = run_phase139_analysis(project_root=_PROJECT_ROOT, output_root=tmp_path)
    assert isinstance(payload, dict), 'run_phase139_analysis must return a dict'
    assert payload, 'run_phase139_analysis returned empty dict'
    assert payload['aggregate_corr'] >= 0.88


# ===========================================================================
# Phase 140 — Bridge correction comparison (benchmark scaffold family)
# ===========================================================================


@pytest.mark.unit
def test_phase140_artifact_exists() -> None:
    """Phase 140 artifact must exist on disk."""
    assert _P140.exists(), f"Missing: {_P140}"


@pytest.mark.unit
def test_phase140_artifact_json_valid() -> None:
    """Phase 140 artifact must be valid JSON."""
    assert _P140.exists(), f"Missing: {_P140}"
    data = json.loads(_P140.read_text(encoding='utf-8'))
    assert isinstance(data, dict), "Phase 140 artifact root must be a dict"


@pytest.mark.unit
def test_phase140_artifact_structure() -> None:
    """Phase 140 artifact must contain required top-level keys."""
    data = json.loads(_P140.read_text(encoding='utf-8'))
    for key in ('phase', 'compactness_corr', 'tensor_compactness_corr', 'gain', 'verdict'):
        assert key in data, f"Phase 140 artifact missing key: {key!r}"


@pytest.mark.unit
def test_phase140_metric_thresholds() -> None:
    """Phase 140 tensor/compactness must outperform compactness-only correction.

    Report: compactness_corr = 0.8715; tensor_compactness_corr = 0.8928; gain = 0.0213.
    """
    data = json.loads(_P140.read_text(encoding='utf-8'))
    assert data['tensor_compactness_corr'] > data['compactness_corr'], (
        "Phase 140 tensor_compactness_corr must exceed compactness_corr"
    )
    assert data['tensor_compactness_corr'] >= 0.88, (
        f"Phase 140 tensor_compactness_corr expected >= 0.88, got {data['tensor_compactness_corr']}"
    )
    assert data['gain'] >= 0.02, (
        f"Phase 140 gain expected >= 0.02, got {data['gain']}"
    )
    assert data['verdict'] == 'tensor_compactness_preferred', (
        f"Unexpected verdict: {data['verdict']!r}"
    )


@pytest.mark.unit
def test_phase140_loader_importable() -> None:
    """phase140_analysis module must be importable and expose run_phase140_analysis."""
    mod = importlib.import_module('cwt.cgt.analysis.phase140_analysis')
    assert hasattr(mod, 'run_phase140_analysis'), (
        "phase140_analysis missing 'run_phase140_analysis'"
    )


@pytest.mark.unit
def test_phase140_loader_runs(tmp_path: Path) -> None:
    """run_phase140_analysis must return a non-empty dict."""
    from cwt.cgt.analysis.phase140_analysis import run_phase140_analysis

    payload = run_phase140_analysis(project_root=_PROJECT_ROOT, output_root=tmp_path)
    assert isinstance(payload, dict), 'run_phase140_analysis must return a dict'
    assert payload, 'run_phase140_analysis returned empty dict'
    assert payload['tensor_compactness_corr'] >= 0.88


# ===========================================================================
# Phase 142 — Less-synthetic bridge positive pilot (benchmark AA)
# ===========================================================================


@pytest.mark.unit
def test_phase142_artifact_exists() -> None:
    """Phase 142 artifact must exist on disk."""
    assert _P142.exists(), f"Missing: {_P142}"


@pytest.mark.unit
def test_phase142_artifact_json_valid() -> None:
    """Phase 142 artifact must be valid JSON."""
    assert _P142.exists(), f"Missing: {_P142}"
    data = json.loads(_P142.read_text(encoding='utf-8'))
    assert isinstance(data, dict), "Phase 142 artifact root must be a dict"


@pytest.mark.unit
def test_phase142_artifact_structure() -> None:
    """Phase 142 artifact must contain required top-level keys."""
    data = json.loads(_P142.read_text(encoding='utf-8'))
    for key in ('phase', 'benchmark', 'r2', 'corr', 'sign', 'verdict'):
        assert key in data, f"Phase 142 artifact missing key: {key!r}"


@pytest.mark.unit
def test_phase142_metric_thresholds() -> None:
    """Phase 142 less-synthetic positive R2 >= 0.88; sign_agreement >= 0.98.

    Report: heldout combined R2 = 0.8867; sign = 0.9917.
    """
    data = json.loads(_P142.read_text(encoding='utf-8'))
    assert data['r2'] >= 0.88, (
        f"Phase 142 r2 expected >= 0.88, got {data['r2']}"
    )
    assert data['sign'] >= 0.98, (
        f"Phase 142 sign expected >= 0.98, got {data['sign']}"
    )
    assert data['verdict'] == 'supportive_less_synthetic_positive', (
        f"Unexpected verdict: {data['verdict']!r}"
    )


@pytest.mark.unit
def test_phase142_loader_importable() -> None:
    """phase142_analysis module must be importable and expose run_phase142_analysis."""
    mod = importlib.import_module('cwt.cgt.analysis.phase142_analysis')
    assert hasattr(mod, 'run_phase142_analysis'), (
        "phase142_analysis missing 'run_phase142_analysis'"
    )


@pytest.mark.unit
def test_phase142_loader_runs(tmp_path: Path) -> None:
    """run_phase142_analysis must return a non-empty dict."""
    from cwt.cgt.analysis.phase142_analysis import run_phase142_analysis

    payload = run_phase142_analysis(project_root=_PROJECT_ROOT, output_root=tmp_path)
    assert isinstance(payload, dict), 'run_phase142_analysis must return a dict'
    assert payload, 'run_phase142_analysis returned empty dict'
    assert payload['r2'] >= 0.88


# ===========================================================================
# Phase 143 — Less-synthetic bridge adversarial pilot (benchmark AA)
# ===========================================================================


@pytest.mark.unit
def test_phase143_artifact_exists() -> None:
    """Phase 143 artifact must exist on disk."""
    assert _P143.exists(), f"Missing: {_P143}"


@pytest.mark.unit
def test_phase143_artifact_json_valid() -> None:
    """Phase 143 artifact must be valid JSON."""
    assert _P143.exists(), f"Missing: {_P143}"
    data = json.loads(_P143.read_text(encoding='utf-8'))
    assert isinstance(data, dict), "Phase 143 artifact root must be a dict"


@pytest.mark.unit
def test_phase143_artifact_structure() -> None:
    """Phase 143 artifact must contain required top-level keys."""
    data = json.loads(_P143.read_text(encoding='utf-8'))
    for key in ('phase', 'benchmark', 'raw', 'corrected', 'verdict'):
        assert key in data, f"Phase 143 artifact missing key: {key!r}"
    for subkey in ('r2', 'sign'):
        assert subkey in data['raw'], f"Phase 143 raw missing key: {subkey!r}"
    for subkey in ('r2', 'sign', 'corr'):
        assert subkey in data['corrected'], f"Phase 143 corrected missing key: {subkey!r}"


@pytest.mark.unit
def test_phase143_metric_thresholds() -> None:
    """Phase 143 less-synthetic adversarial must degrade raw and recover corrected.

    Report: raw R2 = 0.3715; corrected R2 = 0.8124; corrected sign = 0.9444.
    """
    data = json.loads(_P143.read_text(encoding='utf-8'))
    assert data['raw']['r2'] < 0.45, (
        f"Phase 143 raw r2 expected < 0.45 (adversarial degrades), "
        f"got {data['raw']['r2']}"
    )
    assert data['corrected']['r2'] >= 0.80, (
        f"Phase 143 corrected r2 expected >= 0.80, got {data['corrected']['r2']}"
    )
    assert data['corrected']['sign'] >= 0.93, (
        f"Phase 143 corrected sign expected >= 0.93, got {data['corrected']['sign']}"
    )
    assert data['verdict'] == 'less_synthetic_adversarial_supportive_after_correction', (
        f"Unexpected verdict: {data['verdict']!r}"
    )


@pytest.mark.unit
def test_phase143_loader_importable() -> None:
    """phase143_analysis module must be importable and expose run_phase143_analysis."""
    mod = importlib.import_module('cwt.cgt.analysis.phase143_analysis')
    assert hasattr(mod, 'run_phase143_analysis'), (
        "phase143_analysis missing 'run_phase143_analysis'"
    )


@pytest.mark.unit
def test_phase143_loader_runs(tmp_path: Path) -> None:
    """run_phase143_analysis must return a non-empty dict."""
    from cwt.cgt.analysis.phase143_analysis import run_phase143_analysis

    payload = run_phase143_analysis(project_root=_PROJECT_ROOT, output_root=tmp_path)
    assert isinstance(payload, dict), 'run_phase143_analysis must return a dict'
    assert payload, 'run_phase143_analysis returned empty dict'
    assert payload['corrected']['r2'] >= 0.80


# ===========================================================================
# Phase 144 — Pooled seven-bridge positive (benchmark scaffold family)
# ===========================================================================


@pytest.mark.unit
def test_phase144_artifact_exists() -> None:
    """Phase 144 artifact must exist on disk."""
    assert _P144.exists(), f"Missing: {_P144}"


@pytest.mark.unit
def test_phase144_artifact_json_valid() -> None:
    """Phase 144 artifact must be valid JSON."""
    assert _P144.exists(), f"Missing: {_P144}"
    data = json.loads(_P144.read_text(encoding='utf-8'))
    assert isinstance(data, dict), "Phase 144 artifact root must be a dict"


@pytest.mark.unit
def test_phase144_artifact_structure() -> None:
    """Phase 144 artifact must contain required top-level keys."""
    data = json.loads(_P144.read_text(encoding='utf-8'))
    for key in ('phase', 'r2', 'corr', 'sign', 'benchmarks', 'verdict'):
        assert key in data, f"Phase 144 artifact missing key: {key!r}"


@pytest.mark.unit
def test_phase144_metric_thresholds() -> None:
    """Phase 144 pooled seven-bridge positive R2 >= 0.93; sign >= 0.99.

    Report: pooled R2 = 0.9335; sign = 0.9961. Seven benchmarks: T/U/V/W/X/Y/Z.
    """
    data = json.loads(_P144.read_text(encoding='utf-8'))
    assert data['r2'] >= 0.93, (
        f"Phase 144 r2 expected >= 0.93, got {data['r2']}"
    )
    assert data['sign'] >= 0.99, (
        f"Phase 144 sign expected >= 0.99, got {data['sign']}"
    )
    assert len(data['benchmarks']) == 7, (
        f"Phase 144 expected 7 benchmarks, got {len(data['benchmarks'])}"
    )
    assert data['verdict'] == 'pooled_seven_bridge_positive_supportive', (
        f"Unexpected verdict: {data['verdict']!r}"
    )


@pytest.mark.unit
def test_phase144_loader_importable() -> None:
    """phase144_analysis module must be importable and expose run_phase144_analysis."""
    mod = importlib.import_module('cwt.cgt.analysis.phase144_analysis')
    assert hasattr(mod, 'run_phase144_analysis'), (
        "phase144_analysis missing 'run_phase144_analysis'"
    )


@pytest.mark.unit
def test_phase144_loader_runs(tmp_path: Path) -> None:
    """run_phase144_analysis must return a non-empty dict."""
    from cwt.cgt.analysis.phase144_analysis import run_phase144_analysis

    payload = run_phase144_analysis(project_root=_PROJECT_ROOT, output_root=tmp_path)
    assert isinstance(payload, dict), 'run_phase144_analysis must return a dict'
    assert payload, 'run_phase144_analysis returned empty dict'
    assert payload['r2'] >= 0.93


# ===========================================================================
# Phase 145 — Pooled seven-bridge adversarial (benchmark scaffold family)
# ===========================================================================


@pytest.mark.unit
def test_phase145_artifact_exists() -> None:
    """Phase 145 artifact must exist on disk."""
    assert _P145.exists(), f"Missing: {_P145}"


@pytest.mark.unit
def test_phase145_artifact_json_valid() -> None:
    """Phase 145 artifact must be valid JSON."""
    assert _P145.exists(), f"Missing: {_P145}"
    data = json.loads(_P145.read_text(encoding='utf-8'))
    assert isinstance(data, dict), "Phase 145 artifact root must be a dict"


@pytest.mark.unit
def test_phase145_artifact_structure() -> None:
    """Phase 145 artifact must contain required top-level keys."""
    data = json.loads(_P145.read_text(encoding='utf-8'))
    for key in ('phase', 'r2', 'corr', 'sign', 'benchmarks', 'verdict'):
        assert key in data, f"Phase 145 artifact missing key: {key!r}"


@pytest.mark.unit
def test_phase145_metric_thresholds() -> None:
    """Phase 145 pooled seven-bridge adversarial corrected R2 >= 0.88; sign >= 0.93.

    Report: pooled adversarial corrected R2 = 0.8897; sign = 0.9427. Seven benchmarks.
    """
    data = json.loads(_P145.read_text(encoding='utf-8'))
    assert data['r2'] >= 0.88, (
        f"Phase 145 r2 expected >= 0.88, got {data['r2']}"
    )
    assert data['sign'] >= 0.93, (
        f"Phase 145 sign expected >= 0.93, got {data['sign']}"
    )
    assert len(data['benchmarks']) == 7, (
        f"Phase 145 expected 7 benchmarks, got {len(data['benchmarks'])}"
    )
    assert data['verdict'] == 'pooled_seven_bridge_adversarial_supportive_after_correction', (
        f"Unexpected verdict: {data['verdict']!r}"
    )


@pytest.mark.unit
def test_phase145_loader_importable() -> None:
    """phase145_analysis module must be importable and expose run_phase145_analysis."""
    mod = importlib.import_module('cwt.cgt.analysis.phase145_analysis')
    assert hasattr(mod, 'run_phase145_analysis'), (
        "phase145_analysis missing 'run_phase145_analysis'"
    )


@pytest.mark.unit
def test_phase145_loader_runs(tmp_path: Path) -> None:
    """run_phase145_analysis must return a non-empty dict."""
    from cwt.cgt.analysis.phase145_analysis import run_phase145_analysis

    payload = run_phase145_analysis(project_root=_PROJECT_ROOT, output_root=tmp_path)
    assert isinstance(payload, dict), 'run_phase145_analysis must return a dict'
    assert payload, 'run_phase145_analysis returned empty dict'
    assert payload['r2'] >= 0.88


# ===========================================================================
# Phase 146 — Bridge-to-pilot transfer summary (benchmark scaffold family)
# ===========================================================================


@pytest.mark.unit
def test_phase146_artifact_exists() -> None:
    """Phase 146 artifact must exist on disk."""
    assert _P146.exists(), f"Missing: {_P146}"


@pytest.mark.unit
def test_phase146_artifact_json_valid() -> None:
    """Phase 146 artifact must be valid JSON."""
    assert _P146.exists(), f"Missing: {_P146}"
    data = json.loads(_P146.read_text(encoding='utf-8'))
    assert isinstance(data, dict), "Phase 146 artifact root must be a dict"


@pytest.mark.unit
def test_phase146_artifact_structure() -> None:
    """Phase 146 artifact must contain required top-level keys."""
    data = json.loads(_P146.read_text(encoding='utf-8'))
    for key in (
        'phase', 'bridge_pooled_pos', 'pilot_pos', 'pilot_adv_corr',
        'combined_bridge_plus_pilot', 'verdict',
    ):
        assert key in data, f"Phase 146 artifact missing key: {key!r}"


@pytest.mark.unit
def test_phase146_metric_thresholds() -> None:
    """Phase 146 transfer summary must confirm bridge superiority over pilot.

    Report: bridge_pooled_pos = 0.9335; pilot_pos = 0.8867;
    pilot_adv_corr = 0.8124; combined = 0.9056.
    """
    data = json.loads(_P146.read_text(encoding='utf-8'))
    assert data['bridge_pooled_pos'] >= 0.93, (
        f"Phase 146 bridge_pooled_pos expected >= 0.93, got {data['bridge_pooled_pos']}"
    )
    assert data['pilot_pos'] >= 0.88, (
        f"Phase 146 pilot_pos expected >= 0.88, got {data['pilot_pos']}"
    )
    assert data['pilot_adv_corr'] >= 0.80, (
        f"Phase 146 pilot_adv_corr expected >= 0.80, got {data['pilot_adv_corr']}"
    )
    assert data['bridge_pooled_pos'] > data['pilot_pos'], (
        "Phase 146 bridge_pooled_pos must exceed pilot_pos"
    )
    assert data['combined_bridge_plus_pilot'] >= 0.90, (
        f"Phase 146 combined_bridge_plus_pilot expected >= 0.90, "
        f"got {data['combined_bridge_plus_pilot']}"
    )
    assert data['verdict'] == 'bridge_to_less_synthetic_transfer_supportive_but_weaker', (
        f"Unexpected verdict: {data['verdict']!r}"
    )


@pytest.mark.unit
def test_phase146_loader_importable() -> None:
    """phase146_analysis module must be importable and expose run_phase146_analysis."""
    mod = importlib.import_module('cwt.cgt.analysis.phase146_analysis')
    assert hasattr(mod, 'run_phase146_analysis'), (
        "phase146_analysis missing 'run_phase146_analysis'"
    )


@pytest.mark.unit
def test_phase146_loader_runs(tmp_path: Path) -> None:
    """run_phase146_analysis must return a non-empty dict."""
    from cwt.cgt.analysis.phase146_analysis import run_phase146_analysis

    payload = run_phase146_analysis(project_root=_PROJECT_ROOT, output_root=tmp_path)
    assert isinstance(payload, dict), 'run_phase146_analysis must return a dict'
    assert payload, 'run_phase146_analysis returned empty dict'
    assert payload['combined_bridge_plus_pilot'] >= 0.90
