"""Smoke tests for CGT Phases 121-136 result artifacts and analysis modules.

Covers:
- Existence and JSON-validity of the Phase 121-136 artifacts.
- Importability of the phase analysis modules.
- Structural integrity of each artifact (top-level keys present).
- Metric thresholds derived from bundle reports and pinned to observed JSON values.
- Execution of run_phaseN_analysis() to verify correct output.

Benchmark layout:
  benchmark_X_event_thinned/   — Phase 121 (fifth bridge positive)
  benchmark_U_partial_delay/   — Phase 122 (bridge adversarial completion for U)
  benchmark_scaffold_family/   — Phases 123-128, 131-136 (pooled / audit / refresh)
  benchmark_Y_burst_observed/  — Phases 129-130 (sixth bridge positive + adversarial)

Phases 121-136 constitute the "bridge benchmarks" block (bundle v7.2).
Phases 127-128 are report+JSON only (no bundle code stub); analysis modules
are written as real loaders alongside all other phases.
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
_X_DIR = _PROJECT_ROOT / 'cgt_benchmarks' / 'results' / 'benchmark_X_event_thinned'
_U_DIR = _PROJECT_ROOT / 'cgt_benchmarks' / 'results' / 'benchmark_U_partial_delay'
_Y_DIR = _PROJECT_ROOT / 'cgt_benchmarks' / 'results' / 'benchmark_Y_burst_observed'

_P121 = _X_DIR / 'benchmark_x_phase121_fifth_bridge_positive.json'
_P122 = _U_DIR / 'benchmark_u_phase122_bridge_adversarial_completion.json'
_P123 = _SCAFFOLD_DIR / 'benchmark_scaffold_phase123_pooled_five_bridge_positive.json'
_P124 = _SCAFFOLD_DIR / 'benchmark_scaffold_phase124_pooled_five_bridge_adversarial.json'
_P125 = _SCAFFOLD_DIR / 'benchmark_scaffold_phase125_bridge_compactness_correction_candidate.json'
_P126 = _SCAFFOLD_DIR / 'benchmark_scaffold_phase126_bridge_leave_one_benchmark_out.json'
_P127 = _SCAFFOLD_DIR / 'benchmark_scaffold_phase127_bridge_minimal_accepted_theory_pack.json'
_P128 = _SCAFFOLD_DIR / 'benchmark_scaffold_phase128_bridge_boundary_refresh.json'
_P129 = _Y_DIR / 'benchmark_y_phase129_sixth_bridge_positive.json'
_P130 = _Y_DIR / 'benchmark_y_phase130_sixth_bridge_adversarial.json'
_P131 = _SCAFFOLD_DIR / 'benchmark_scaffold_phase131_pooled_six_bridge_positive.json'
_P132 = _SCAFFOLD_DIR / 'benchmark_scaffold_phase132_pooled_six_bridge_adversarial.json'
_P133 = _SCAFFOLD_DIR / 'benchmark_scaffold_phase133_bridge_family_holdout.json'
_P134 = _SCAFFOLD_DIR / 'benchmark_scaffold_phase134_bridge_tensor_compactness_candidate.json'
_P135 = _SCAFFOLD_DIR / 'benchmark_scaffold_phase135_bridge_calibration_free_minimal.json'
_P136 = _SCAFFOLD_DIR / 'benchmark_scaffold_phase136_bridge_boundary_refresh2.json'


# ===========================================================================
# Phase 121 — Fifth bridge positive (benchmark X event-thinned)
# ===========================================================================


@pytest.mark.unit
def test_phase121_artifact_exists() -> None:
    """Phase 121 artifact must exist on disk."""
    assert _P121.exists(), f"Missing: {_P121}"


@pytest.mark.unit
def test_phase121_artifact_json_valid() -> None:
    """Phase 121 artifact must be valid JSON."""
    assert _P121.exists(), f"Missing: {_P121}"
    data = json.loads(_P121.read_text(encoding='utf-8'))
    assert isinstance(data, dict), "Phase 121 artifact root must be a dict"


@pytest.mark.unit
def test_phase121_artifact_structure() -> None:
    """Phase 121 artifact must contain required top-level keys."""
    data = json.loads(_P121.read_text(encoding='utf-8'))
    for key in ('phase', 'benchmark', 'heldout_combined_r2', 'sign_agreement', 'verdict'):
        assert key in data, f"Phase 121 artifact missing key: {key!r}"


@pytest.mark.unit
def test_phase121_metric_thresholds() -> None:
    """Phase 121 metrics must meet fifth-bridge acceptance bounds.

    Report: heldout_combined_r2 = 0.9248; sign_agreement = 0.9889.
    """
    data = json.loads(_P121.read_text(encoding='utf-8'))
    assert data['heldout_combined_r2'] >= 0.91, (
        f"Phase 121 heldout_combined_r2 expected >= 0.91, got {data['heldout_combined_r2']}"
    )
    assert data['sign_agreement'] >= 0.98, (
        f"Phase 121 sign_agreement expected >= 0.98, got {data['sign_agreement']}"
    )
    assert data['verdict'] == 'fifth_bridge_positive_supported', (
        f"Unexpected verdict: {data['verdict']!r}"
    )


@pytest.mark.unit
def test_phase121_loader_importable() -> None:
    """phase121_analysis module must be importable and expose run_phase121_analysis."""
    mod = importlib.import_module('cwt.cgt.analysis.phase121_analysis')
    assert hasattr(mod, 'run_phase121_analysis'), (
        "phase121_analysis missing 'run_phase121_analysis'"
    )


@pytest.mark.unit
def test_phase121_loader_runs(tmp_path: Path) -> None:
    """run_phase121_analysis must return a non-empty dict."""
    from cwt.cgt.analysis.phase121_analysis import run_phase121_analysis

    payload = run_phase121_analysis(project_root=_PROJECT_ROOT, output_root=tmp_path)
    assert isinstance(payload, dict), 'run_phase121_analysis must return a dict'
    assert payload, 'run_phase121_analysis returned empty dict'
    assert payload['heldout_combined_r2'] >= 0.91


# ===========================================================================
# Phase 122 — Bridge adversarial completion for benchmark U (partial delay)
# ===========================================================================


@pytest.mark.unit
def test_phase122_artifact_exists() -> None:
    """Phase 122 artifact must exist on disk."""
    assert _P122.exists(), f"Missing: {_P122}"


@pytest.mark.unit
def test_phase122_artifact_json_valid() -> None:
    """Phase 122 artifact must be valid JSON."""
    assert _P122.exists(), f"Missing: {_P122}"
    data = json.loads(_P122.read_text(encoding='utf-8'))
    assert isinstance(data, dict), "Phase 122 artifact root must be a dict"


@pytest.mark.unit
def test_phase122_artifact_structure() -> None:
    """Phase 122 artifact must contain required top-level keys."""
    data = json.loads(_P122.read_text(encoding='utf-8'))
    for key in ('phase', 'benchmark', 'raw_combined_r2', 'corrected_combined_r2', 'verdict'):
        assert key in data, f"Phase 122 artifact missing key: {key!r}"


@pytest.mark.unit
def test_phase122_metric_thresholds() -> None:
    """Phase 122 metrics must confirm adversarial degradation and correction recovery.

    Report: raw_combined_r2 = 0.4412; corrected_combined_r2 = 0.8725.
    """
    data = json.loads(_P122.read_text(encoding='utf-8'))
    assert data['raw_combined_r2'] < 0.5, (
        f"Phase 122 raw_combined_r2 expected < 0.5 (adversarial degrades), "
        f"got {data['raw_combined_r2']}"
    )
    assert data['corrected_combined_r2'] >= 0.86, (
        f"Phase 122 corrected_combined_r2 expected >= 0.86, got {data['corrected_combined_r2']}"
    )
    assert data['corrected_sign_agreement'] >= 0.95, (
        f"Phase 122 corrected_sign_agreement expected >= 0.95, "
        f"got {data['corrected_sign_agreement']}"
    )
    assert data['verdict'] == 'u_bridge_adversarial_corrected_supported', (
        f"Unexpected verdict: {data['verdict']!r}"
    )


@pytest.mark.unit
def test_phase122_loader_importable() -> None:
    """phase122_analysis module must be importable and expose run_phase122_analysis."""
    mod = importlib.import_module('cwt.cgt.analysis.phase122_analysis')
    assert hasattr(mod, 'run_phase122_analysis'), (
        "phase122_analysis missing 'run_phase122_analysis'"
    )


@pytest.mark.unit
def test_phase122_loader_runs(tmp_path: Path) -> None:
    """run_phase122_analysis must return a non-empty dict."""
    from cwt.cgt.analysis.phase122_analysis import run_phase122_analysis

    payload = run_phase122_analysis(project_root=_PROJECT_ROOT, output_root=tmp_path)
    assert isinstance(payload, dict), 'run_phase122_analysis must return a dict'
    assert payload, 'run_phase122_analysis returned empty dict'
    assert payload['corrected_combined_r2'] >= 0.86


# ===========================================================================
# Phase 123 — Pooled five-bridge positive (benchmark scaffold family)
# ===========================================================================


@pytest.mark.unit
def test_phase123_artifact_exists() -> None:
    """Phase 123 artifact must exist on disk."""
    assert _P123.exists(), f"Missing: {_P123}"


@pytest.mark.unit
def test_phase123_artifact_json_valid() -> None:
    """Phase 123 artifact must be valid JSON."""
    assert _P123.exists(), f"Missing: {_P123}"
    data = json.loads(_P123.read_text(encoding='utf-8'))
    assert isinstance(data, dict), "Phase 123 artifact root must be a dict"


@pytest.mark.unit
def test_phase123_artifact_structure() -> None:
    """Phase 123 artifact must contain required top-level keys."""
    data = json.loads(_P123.read_text(encoding='utf-8'))
    for key in ('phase', 'bridge_benchmarks', 'metrics', 'verdict'):
        assert key in data, f"Phase 123 artifact missing key: {key!r}"
    for mkey in ('pooled_bridge_positive_combined_r2', 'pooled_bridge_positive_sign_agreement'):
        assert mkey in data['metrics'], f"Phase 123 metrics missing key: {mkey!r}"


@pytest.mark.unit
def test_phase123_metric_thresholds() -> None:
    """Phase 123 pooled five-bridge positive R2 must be >= 0.92.

    Report: pooled combined R2 = 0.9297; sign_agreement = 0.9892.
    """
    data = json.loads(_P123.read_text(encoding='utf-8'))
    m = data['metrics']
    assert m['pooled_bridge_positive_combined_r2'] >= 0.92, (
        f"Phase 123 pooled_bridge_positive_combined_r2 expected >= 0.92, "
        f"got {m['pooled_bridge_positive_combined_r2']}"
    )
    assert m['pooled_bridge_positive_sign_agreement'] >= 0.98, (
        f"Phase 123 pooled_bridge_positive_sign_agreement expected >= 0.98, "
        f"got {m['pooled_bridge_positive_sign_agreement']}"
    )
    assert data['verdict'] == 'pooled_five_bridge_positive_supported', (
        f"Unexpected verdict: {data['verdict']!r}"
    )


@pytest.mark.unit
def test_phase123_loader_importable() -> None:
    """phase123_analysis module must be importable and expose run_phase123_analysis."""
    mod = importlib.import_module('cwt.cgt.analysis.phase123_analysis')
    assert hasattr(mod, 'run_phase123_analysis'), (
        "phase123_analysis missing 'run_phase123_analysis'"
    )


@pytest.mark.unit
def test_phase123_loader_runs(tmp_path: Path) -> None:
    """run_phase123_analysis must return a non-empty dict."""
    from cwt.cgt.analysis.phase123_analysis import run_phase123_analysis

    payload = run_phase123_analysis(project_root=_PROJECT_ROOT, output_root=tmp_path)
    assert isinstance(payload, dict), 'run_phase123_analysis must return a dict'
    assert payload, 'run_phase123_analysis returned empty dict'
    assert payload['metrics']['pooled_bridge_positive_combined_r2'] >= 0.92


# ===========================================================================
# Phase 124 — Pooled five-bridge adversarial (benchmark scaffold family)
# ===========================================================================


@pytest.mark.unit
def test_phase124_artifact_exists() -> None:
    """Phase 124 artifact must exist on disk."""
    assert _P124.exists(), f"Missing: {_P124}"


@pytest.mark.unit
def test_phase124_artifact_json_valid() -> None:
    """Phase 124 artifact must be valid JSON."""
    assert _P124.exists(), f"Missing: {_P124}"
    data = json.loads(_P124.read_text(encoding='utf-8'))
    assert isinstance(data, dict), "Phase 124 artifact root must be a dict"


@pytest.mark.unit
def test_phase124_artifact_structure() -> None:
    """Phase 124 artifact must contain required top-level keys."""
    data = json.loads(_P124.read_text(encoding='utf-8'))
    for key in ('phase', 'bridge_benchmarks', 'metrics', 'verdict'):
        assert key in data, f"Phase 124 artifact missing key: {key!r}"
    for mkey in ('pooled_bridge_adversarial_raw_r2', 'pooled_bridge_adversarial_corrected_r2'):
        assert mkey in data['metrics'], f"Phase 124 metrics missing key: {mkey!r}"


@pytest.mark.unit
def test_phase124_metric_thresholds() -> None:
    """Phase 124 pooled adversarial corrected R2 must recover from raw degradation.

    Report: raw_r2 = 0.4386; corrected_r2 = 0.8724.
    """
    data = json.loads(_P124.read_text(encoding='utf-8'))
    m = data['metrics']
    assert m['pooled_bridge_adversarial_raw_r2'] < 0.5, (
        f"Phase 124 raw_r2 expected < 0.5 (adversarial degrades), "
        f"got {m['pooled_bridge_adversarial_raw_r2']}"
    )
    assert m['pooled_bridge_adversarial_corrected_r2'] >= 0.86, (
        f"Phase 124 corrected_r2 expected >= 0.86, "
        f"got {m['pooled_bridge_adversarial_corrected_r2']}"
    )
    assert data['verdict'] == 'pooled_five_bridge_adversarial_corrected_supported', (
        f"Unexpected verdict: {data['verdict']!r}"
    )


@pytest.mark.unit
def test_phase124_loader_importable() -> None:
    """phase124_analysis module must be importable and expose run_phase124_analysis."""
    mod = importlib.import_module('cwt.cgt.analysis.phase124_analysis')
    assert hasattr(mod, 'run_phase124_analysis'), (
        "phase124_analysis missing 'run_phase124_analysis'"
    )


@pytest.mark.unit
def test_phase124_loader_runs(tmp_path: Path) -> None:
    """run_phase124_analysis must return a non-empty dict."""
    from cwt.cgt.analysis.phase124_analysis import run_phase124_analysis

    payload = run_phase124_analysis(project_root=_PROJECT_ROOT, output_root=tmp_path)
    assert isinstance(payload, dict), 'run_phase124_analysis must return a dict'
    assert payload, 'run_phase124_analysis returned empty dict'
    assert payload['metrics']['pooled_bridge_adversarial_corrected_r2'] >= 0.86


# ===========================================================================
# Phase 125 — Bridge compactness correction candidate (benchmark scaffold family)
# ===========================================================================


@pytest.mark.unit
def test_phase125_artifact_exists() -> None:
    """Phase 125 artifact must exist on disk."""
    assert _P125.exists(), f"Missing: {_P125}"


@pytest.mark.unit
def test_phase125_artifact_json_valid() -> None:
    """Phase 125 artifact must be valid JSON."""
    assert _P125.exists(), f"Missing: {_P125}"
    data = json.loads(_P125.read_text(encoding='utf-8'))
    assert isinstance(data, dict), "Phase 125 artifact root must be a dict"


@pytest.mark.unit
def test_phase125_artifact_structure() -> None:
    """Phase 125 artifact must contain required top-level keys."""
    data = json.loads(_P125.read_text(encoding='utf-8'))
    for key in ('phase', 'correction_type', 'metrics', 'verdict'):
        assert key in data, f"Phase 125 artifact missing key: {key!r}"
    for mkey in ('baseline_adversarial_corrected_r2', 'compactness_corrected_r2'):
        assert mkey in data['metrics'], f"Phase 125 metrics missing key: {mkey!r}"


@pytest.mark.unit
def test_phase125_metric_thresholds() -> None:
    """Phase 125 compactness correction must improve over Phase 124 baseline.

    Report: baseline_r2 = 0.8724; compactness_corrected_r2 = 0.8896.
    """
    data = json.loads(_P125.read_text(encoding='utf-8'))
    m = data['metrics']
    assert m['compactness_corrected_r2'] > m['baseline_adversarial_corrected_r2'], (
        "Phase 125 compactness_corrected_r2 must exceed baseline"
    )
    assert m['compactness_corrected_r2'] >= 0.88, (
        f"Phase 125 compactness_corrected_r2 expected >= 0.88, "
        f"got {m['compactness_corrected_r2']}"
    )
    assert data['verdict'] == 'bridge_compactness_correction_candidate_supported', (
        f"Unexpected verdict: {data['verdict']!r}"
    )


@pytest.mark.unit
def test_phase125_loader_importable() -> None:
    """phase125_analysis module must be importable and expose run_phase125_analysis."""
    mod = importlib.import_module('cwt.cgt.analysis.phase125_analysis')
    assert hasattr(mod, 'run_phase125_analysis'), (
        "phase125_analysis missing 'run_phase125_analysis'"
    )


@pytest.mark.unit
def test_phase125_loader_runs(tmp_path: Path) -> None:
    """run_phase125_analysis must return a non-empty dict."""
    from cwt.cgt.analysis.phase125_analysis import run_phase125_analysis

    payload = run_phase125_analysis(project_root=_PROJECT_ROOT, output_root=tmp_path)
    assert isinstance(payload, dict), 'run_phase125_analysis must return a dict'
    assert payload, 'run_phase125_analysis returned empty dict'
    assert payload['metrics']['compactness_corrected_r2'] >= 0.88


# ===========================================================================
# Phase 126 — Bridge leave-one-benchmark-out audit (benchmark scaffold family)
# ===========================================================================


@pytest.mark.unit
def test_phase126_artifact_exists() -> None:
    """Phase 126 artifact must exist on disk."""
    assert _P126.exists(), f"Missing: {_P126}"


@pytest.mark.unit
def test_phase126_artifact_json_valid() -> None:
    """Phase 126 artifact must be valid JSON."""
    assert _P126.exists(), f"Missing: {_P126}"
    data = json.loads(_P126.read_text(encoding='utf-8'))
    assert isinstance(data, dict), "Phase 126 artifact root must be a dict"


@pytest.mark.unit
def test_phase126_artifact_structure() -> None:
    """Phase 126 artifact must contain required top-level keys."""
    data = json.loads(_P126.read_text(encoding='utf-8'))
    for key in ('phase', 'audit_type', 'bridge_benchmarks', 'metrics', 'verdict'):
        assert key in data, f"Phase 126 artifact missing key: {key!r}"
    for mkey in ('mean_heldout_combined_r2', 'min_heldout_combined_r2', 'weakest_benchmark'):
        assert mkey in data['metrics'], f"Phase 126 metrics missing key: {mkey!r}"


@pytest.mark.unit
def test_phase126_metric_thresholds() -> None:
    """Phase 126 LOO min heldout R2 must be >= 0.84 (weakest = T_semisynthetic_observed).

    Report: mean_heldout_combined_r2 = 0.8867; min = 0.8489.
    """
    data = json.loads(_P126.read_text(encoding='utf-8'))
    m = data['metrics']
    assert m['mean_heldout_combined_r2'] >= 0.88, (
        f"Phase 126 mean_heldout_combined_r2 expected >= 0.88, "
        f"got {m['mean_heldout_combined_r2']}"
    )
    assert m['min_heldout_combined_r2'] >= 0.84, (
        f"Phase 126 min_heldout_combined_r2 expected >= 0.84, "
        f"got {m['min_heldout_combined_r2']}"
    )
    assert m['weakest_benchmark'] == 'T_semisynthetic_observed', (
        f"Phase 126 weakest_benchmark expected 'T_semisynthetic_observed', "
        f"got {m['weakest_benchmark']!r}"
    )
    assert data['verdict'] == 'bridge_leave_one_benchmark_out_supported', (
        f"Unexpected verdict: {data['verdict']!r}"
    )


@pytest.mark.unit
def test_phase126_loader_importable() -> None:
    """phase126_analysis module must be importable and expose run_phase126_analysis."""
    mod = importlib.import_module('cwt.cgt.analysis.phase126_analysis')
    assert hasattr(mod, 'run_phase126_analysis'), (
        "phase126_analysis missing 'run_phase126_analysis'"
    )


@pytest.mark.unit
def test_phase126_loader_runs(tmp_path: Path) -> None:
    """run_phase126_analysis must return a non-empty dict."""
    from cwt.cgt.analysis.phase126_analysis import run_phase126_analysis

    payload = run_phase126_analysis(project_root=_PROJECT_ROOT, output_root=tmp_path)
    assert isinstance(payload, dict), 'run_phase126_analysis must return a dict'
    assert payload, 'run_phase126_analysis returned empty dict'
    assert payload['metrics']['min_heldout_combined_r2'] >= 0.84


# ===========================================================================
# Phase 127 — Bridge minimal accepted theory pack (benchmark scaffold family)
# ===========================================================================


@pytest.mark.unit
def test_phase127_artifact_exists() -> None:
    """Phase 127 artifact must exist on disk."""
    assert _P127.exists(), f"Missing: {_P127}"


@pytest.mark.unit
def test_phase127_artifact_json_valid() -> None:
    """Phase 127 artifact must be valid JSON."""
    assert _P127.exists(), f"Missing: {_P127}"
    data = json.loads(_P127.read_text(encoding='utf-8'))
    assert isinstance(data, dict), "Phase 127 artifact root must be a dict"


@pytest.mark.unit
def test_phase127_artifact_structure() -> None:
    """Phase 127 artifact must contain required top-level keys."""
    data = json.loads(_P127.read_text(encoding='utf-8'))
    for key in ('phase', 'artifact', 'accepted_rule', 'coverage', 'verdict'):
        assert key in data, f"Phase 127 artifact missing key: {key!r}"
    for ckey in ('positive_benchmarks', 'adversarial_benchmarks'):
        assert ckey in data['coverage'], f"Phase 127 coverage missing key: {ckey!r}"


@pytest.mark.unit
def test_phase127_metric_thresholds() -> None:
    """Phase 127 must record the correct accepted rule and full benchmark coverage."""
    data = json.loads(_P127.read_text(encoding='utf-8'))
    assert data['accepted_rule'] == 'pooled_five_bridge_positive_plus_compactness_corrected_adversarial', (
        f"Phase 127 accepted_rule unexpected: {data['accepted_rule']!r}"
    )
    assert len(data['coverage']['positive_benchmarks']) == 5, (
        f"Phase 127 positive_benchmarks expected 5 entries, "
        f"got {len(data['coverage']['positive_benchmarks'])}"
    )
    assert len(data['coverage']['adversarial_benchmarks']) == 5, (
        f"Phase 127 adversarial_benchmarks expected 5 entries, "
        f"got {len(data['coverage']['adversarial_benchmarks'])}"
    )
    assert data['verdict'] == 'bridge_minimal_theory_pack_written', (
        f"Unexpected verdict: {data['verdict']!r}"
    )


@pytest.mark.unit
def test_phase127_loader_importable() -> None:
    """phase127_analysis module must be importable and expose run_phase127_analysis."""
    mod = importlib.import_module('cwt.cgt.analysis.phase127_analysis')
    assert hasattr(mod, 'run_phase127_analysis'), (
        "phase127_analysis missing 'run_phase127_analysis'"
    )


@pytest.mark.unit
def test_phase127_loader_runs(tmp_path: Path) -> None:
    """run_phase127_analysis must return a non-empty dict."""
    from cwt.cgt.analysis.phase127_analysis import run_phase127_analysis

    payload = run_phase127_analysis(project_root=_PROJECT_ROOT, output_root=tmp_path)
    assert isinstance(payload, dict), 'run_phase127_analysis must return a dict'
    assert payload, 'run_phase127_analysis returned empty dict'
    assert payload['verdict'] == 'bridge_minimal_theory_pack_written'


# ===========================================================================
# Phase 128 — Bridge boundary refresh (benchmark scaffold family)
# ===========================================================================


@pytest.mark.unit
def test_phase128_artifact_exists() -> None:
    """Phase 128 artifact must exist on disk."""
    assert _P128.exists(), f"Missing: {_P128}"


@pytest.mark.unit
def test_phase128_artifact_json_valid() -> None:
    """Phase 128 artifact must be valid JSON."""
    assert _P128.exists(), f"Missing: {_P128}"
    data = json.loads(_P128.read_text(encoding='utf-8'))
    assert isinstance(data, dict), "Phase 128 artifact root must be a dict"


@pytest.mark.unit
def test_phase128_artifact_structure() -> None:
    """Phase 128 artifact must contain required top-level keys."""
    data = json.loads(_P128.read_text(encoding='utf-8'))
    for key in ('phase', 'bands', 'summary'):
        assert key in data, f"Phase 128 artifact missing key: {key!r}"
    for bkey in ('bridge_positive_band', 'bridge_adversarial_corrected_band', 'weakest_bridge_benchmark'):
        assert bkey in data['bands'], f"Phase 128 bands missing key: {bkey!r}"


@pytest.mark.unit
def test_phase128_metric_thresholds() -> None:
    """Phase 128 boundary bands must be within expected ranges.

    Report: bridge_positive_band = [0.9098, 0.9248];
    bridge_adversarial_corrected_band = [0.8382, 0.8896].
    """
    data = json.loads(_P128.read_text(encoding='utf-8'))
    bands = data['bands']
    bp = bands['bridge_positive_band']
    ba = bands['bridge_adversarial_corrected_band']
    assert bp[0] >= 0.90, f"Phase 128 bridge_positive_band lower bound expected >= 0.90, got {bp[0]}"
    assert bp[1] <= 0.93, f"Phase 128 bridge_positive_band upper bound expected <= 0.93, got {bp[1]}"
    assert ba[0] >= 0.83, f"Phase 128 bridge_adversarial_corrected_band lower expected >= 0.83, got {ba[0]}"
    assert ba[1] >= 0.88, f"Phase 128 bridge_adversarial_corrected_band upper expected >= 0.88, got {ba[1]}"
    assert bands['weakest_bridge_benchmark'] == 'T_semisynthetic_observed', (
        f"Phase 128 weakest_bridge_benchmark unexpected: {bands['weakest_bridge_benchmark']!r}"
    )


@pytest.mark.unit
def test_phase128_loader_importable() -> None:
    """phase128_analysis module must be importable and expose run_phase128_analysis."""
    mod = importlib.import_module('cwt.cgt.analysis.phase128_analysis')
    assert hasattr(mod, 'run_phase128_analysis'), (
        "phase128_analysis missing 'run_phase128_analysis'"
    )


@pytest.mark.unit
def test_phase128_loader_runs(tmp_path: Path) -> None:
    """run_phase128_analysis must return a non-empty dict."""
    from cwt.cgt.analysis.phase128_analysis import run_phase128_analysis

    payload = run_phase128_analysis(project_root=_PROJECT_ROOT, output_root=tmp_path)
    assert isinstance(payload, dict), 'run_phase128_analysis must return a dict'
    assert payload, 'run_phase128_analysis returned empty dict'
    assert 'bands' in payload


# ===========================================================================
# Phase 129 — Sixth bridge positive (benchmark Y burst-observed)
# ===========================================================================


@pytest.mark.unit
def test_phase129_artifact_exists() -> None:
    """Phase 129 artifact must exist on disk."""
    assert _P129.exists(), f"Missing: {_P129}"


@pytest.mark.unit
def test_phase129_artifact_json_valid() -> None:
    """Phase 129 artifact must be valid JSON."""
    assert _P129.exists(), f"Missing: {_P129}"
    data = json.loads(_P129.read_text(encoding='utf-8'))
    assert isinstance(data, dict), "Phase 129 artifact root must be a dict"


@pytest.mark.unit
def test_phase129_artifact_structure() -> None:
    """Phase 129 artifact must contain required top-level keys."""
    data = json.loads(_P129.read_text(encoding='utf-8'))
    for key in ('phase', 'benchmark', 'heldout_combined_r2', 'sign_agreement', 'verdict'):
        assert key in data, f"Phase 129 artifact missing key: {key!r}"


@pytest.mark.unit
def test_phase129_metric_thresholds() -> None:
    """Phase 129 metrics must meet sixth-bridge acceptance bounds.

    Report: heldout_combined_r2 = 0.9199; sign_agreement = 0.9882.
    """
    data = json.loads(_P129.read_text(encoding='utf-8'))
    assert data['heldout_combined_r2'] >= 0.91, (
        f"Phase 129 heldout_combined_r2 expected >= 0.91, got {data['heldout_combined_r2']}"
    )
    assert data['sign_agreement'] >= 0.98, (
        f"Phase 129 sign_agreement expected >= 0.98, got {data['sign_agreement']}"
    )
    assert data['verdict'] == 'sixth_bridge_positive_supported', (
        f"Unexpected verdict: {data['verdict']!r}"
    )


@pytest.mark.unit
def test_phase129_loader_importable() -> None:
    """phase129_analysis module must be importable and expose run_phase129_analysis."""
    mod = importlib.import_module('cwt.cgt.analysis.phase129_analysis')
    assert hasattr(mod, 'run_phase129_analysis'), (
        "phase129_analysis missing 'run_phase129_analysis'"
    )


@pytest.mark.unit
def test_phase129_loader_runs(tmp_path: Path) -> None:
    """run_phase129_analysis must return a non-empty dict."""
    from cwt.cgt.analysis.phase129_analysis import run_phase129_analysis

    payload = run_phase129_analysis(project_root=_PROJECT_ROOT, output_root=tmp_path)
    assert isinstance(payload, dict), 'run_phase129_analysis must return a dict'
    assert payload, 'run_phase129_analysis returned empty dict'
    assert payload['heldout_combined_r2'] >= 0.91


# ===========================================================================
# Phase 130 — Sixth bridge adversarial (benchmark Y burst-observed)
# ===========================================================================


@pytest.mark.unit
def test_phase130_artifact_exists() -> None:
    """Phase 130 artifact must exist on disk."""
    assert _P130.exists(), f"Missing: {_P130}"


@pytest.mark.unit
def test_phase130_artifact_json_valid() -> None:
    """Phase 130 artifact must be valid JSON."""
    assert _P130.exists(), f"Missing: {_P130}"
    data = json.loads(_P130.read_text(encoding='utf-8'))
    assert isinstance(data, dict), "Phase 130 artifact root must be a dict"


@pytest.mark.unit
def test_phase130_artifact_structure() -> None:
    """Phase 130 artifact must contain required top-level keys."""
    data = json.loads(_P130.read_text(encoding='utf-8'))
    for key in ('phase', 'benchmark', 'raw_combined_r2', 'corrected_combined_r2', 'verdict'):
        assert key in data, f"Phase 130 artifact missing key: {key!r}"


@pytest.mark.unit
def test_phase130_metric_thresholds() -> None:
    """Phase 130 must show adversarial degradation and correction recovery on benchmark Y.

    Report: raw_combined_r2 = 0.4517; corrected_combined_r2 = 0.8812.
    """
    data = json.loads(_P130.read_text(encoding='utf-8'))
    assert data['raw_combined_r2'] < 0.5, (
        f"Phase 130 raw_combined_r2 expected < 0.5 (adversarial degrades), "
        f"got {data['raw_combined_r2']}"
    )
    assert data['corrected_combined_r2'] >= 0.87, (
        f"Phase 130 corrected_combined_r2 expected >= 0.87, got {data['corrected_combined_r2']}"
    )
    assert data['corrected_sign_agreement'] >= 0.96, (
        f"Phase 130 corrected_sign_agreement expected >= 0.96, "
        f"got {data['corrected_sign_agreement']}"
    )
    assert data['verdict'] == 'sixth_bridge_adversarial_corrected_supported', (
        f"Unexpected verdict: {data['verdict']!r}"
    )


@pytest.mark.unit
def test_phase130_loader_importable() -> None:
    """phase130_analysis module must be importable and expose run_phase130_analysis."""
    mod = importlib.import_module('cwt.cgt.analysis.phase130_analysis')
    assert hasattr(mod, 'run_phase130_analysis'), (
        "phase130_analysis missing 'run_phase130_analysis'"
    )


@pytest.mark.unit
def test_phase130_loader_runs(tmp_path: Path) -> None:
    """run_phase130_analysis must return a non-empty dict."""
    from cwt.cgt.analysis.phase130_analysis import run_phase130_analysis

    payload = run_phase130_analysis(project_root=_PROJECT_ROOT, output_root=tmp_path)
    assert isinstance(payload, dict), 'run_phase130_analysis must return a dict'
    assert payload, 'run_phase130_analysis returned empty dict'
    assert payload['corrected_combined_r2'] >= 0.87


# ===========================================================================
# Phase 131 — Pooled six-bridge positive (benchmark scaffold family)
# ===========================================================================


@pytest.mark.unit
def test_phase131_artifact_exists() -> None:
    """Phase 131 artifact must exist on disk."""
    assert _P131.exists(), f"Missing: {_P131}"


@pytest.mark.unit
def test_phase131_artifact_json_valid() -> None:
    """Phase 131 artifact must be valid JSON."""
    assert _P131.exists(), f"Missing: {_P131}"
    data = json.loads(_P131.read_text(encoding='utf-8'))
    assert isinstance(data, dict), "Phase 131 artifact root must be a dict"


@pytest.mark.unit
def test_phase131_artifact_structure() -> None:
    """Phase 131 artifact must contain required top-level keys."""
    data = json.loads(_P131.read_text(encoding='utf-8'))
    for key in ('phase', 'bridge_benchmarks', 'metrics', 'verdict'):
        assert key in data, f"Phase 131 artifact missing key: {key!r}"
    for mkey in ('pooled_six_bridge_positive_combined_r2', 'pooled_six_bridge_positive_sign_agreement'):
        assert mkey in data['metrics'], f"Phase 131 metrics missing key: {mkey!r}"


@pytest.mark.unit
def test_phase131_metric_thresholds() -> None:
    """Phase 131 pooled six-bridge positive R2 must be >= 0.92.

    Report: pooled combined R2 = 0.9312; sign_agreement = 0.9896.
    """
    data = json.loads(_P131.read_text(encoding='utf-8'))
    m = data['metrics']
    assert m['pooled_six_bridge_positive_combined_r2'] >= 0.92, (
        f"Phase 131 pooled_six_bridge_positive_combined_r2 expected >= 0.92, "
        f"got {m['pooled_six_bridge_positive_combined_r2']}"
    )
    assert m['pooled_six_bridge_positive_sign_agreement'] >= 0.98, (
        f"Phase 131 pooled_six_bridge_positive_sign_agreement expected >= 0.98, "
        f"got {m['pooled_six_bridge_positive_sign_agreement']}"
    )
    assert len(data['bridge_benchmarks']) == 6, (
        f"Phase 131 expected 6 bridge benchmarks, got {len(data['bridge_benchmarks'])}"
    )
    assert data['verdict'] == 'pooled_six_bridge_positive_supported', (
        f"Unexpected verdict: {data['verdict']!r}"
    )


@pytest.mark.unit
def test_phase131_loader_importable() -> None:
    """phase131_analysis module must be importable and expose run_phase131_analysis."""
    mod = importlib.import_module('cwt.cgt.analysis.phase131_analysis')
    assert hasattr(mod, 'run_phase131_analysis'), (
        "phase131_analysis missing 'run_phase131_analysis'"
    )


@pytest.mark.unit
def test_phase131_loader_runs(tmp_path: Path) -> None:
    """run_phase131_analysis must return a non-empty dict."""
    from cwt.cgt.analysis.phase131_analysis import run_phase131_analysis

    payload = run_phase131_analysis(project_root=_PROJECT_ROOT, output_root=tmp_path)
    assert isinstance(payload, dict), 'run_phase131_analysis must return a dict'
    assert payload, 'run_phase131_analysis returned empty dict'
    assert payload['metrics']['pooled_six_bridge_positive_combined_r2'] >= 0.92


# ===========================================================================
# Phase 132 — Pooled six-bridge adversarial (benchmark scaffold family)
# ===========================================================================


@pytest.mark.unit
def test_phase132_artifact_exists() -> None:
    """Phase 132 artifact must exist on disk."""
    assert _P132.exists(), f"Missing: {_P132}"


@pytest.mark.unit
def test_phase132_artifact_json_valid() -> None:
    """Phase 132 artifact must be valid JSON."""
    assert _P132.exists(), f"Missing: {_P132}"
    data = json.loads(_P132.read_text(encoding='utf-8'))
    assert isinstance(data, dict), "Phase 132 artifact root must be a dict"


@pytest.mark.unit
def test_phase132_artifact_structure() -> None:
    """Phase 132 artifact must contain required top-level keys."""
    data = json.loads(_P132.read_text(encoding='utf-8'))
    for key in ('phase', 'bridge_benchmarks', 'metrics', 'verdict'):
        assert key in data, f"Phase 132 artifact missing key: {key!r}"
    for mkey in ('pooled_six_bridge_adversarial_raw_r2', 'pooled_six_bridge_adversarial_corrected_r2'):
        assert mkey in data['metrics'], f"Phase 132 metrics missing key: {mkey!r}"


@pytest.mark.unit
def test_phase132_metric_thresholds() -> None:
    """Phase 132 pooled adversarial corrected R2 must recover from raw degradation.

    Report: raw_r2 = 0.4451; corrected_r2 = 0.8844; sign_agreement = 0.9701.
    """
    data = json.loads(_P132.read_text(encoding='utf-8'))
    m = data['metrics']
    assert m['pooled_six_bridge_adversarial_raw_r2'] < 0.5, (
        f"Phase 132 raw_r2 expected < 0.5, got {m['pooled_six_bridge_adversarial_raw_r2']}"
    )
    assert m['pooled_six_bridge_adversarial_corrected_r2'] >= 0.88, (
        f"Phase 132 corrected_r2 expected >= 0.88, "
        f"got {m['pooled_six_bridge_adversarial_corrected_r2']}"
    )
    assert m['pooled_six_bridge_adversarial_corrected_sign_agreement'] >= 0.96, (
        f"Phase 132 corrected_sign_agreement expected >= 0.96, "
        f"got {m['pooled_six_bridge_adversarial_corrected_sign_agreement']}"
    )
    assert data['verdict'] == 'pooled_six_bridge_adversarial_supported', (
        f"Unexpected verdict: {data['verdict']!r}"
    )


@pytest.mark.unit
def test_phase132_loader_importable() -> None:
    """phase132_analysis module must be importable and expose run_phase132_analysis."""
    mod = importlib.import_module('cwt.cgt.analysis.phase132_analysis')
    assert hasattr(mod, 'run_phase132_analysis'), (
        "phase132_analysis missing 'run_phase132_analysis'"
    )


@pytest.mark.unit
def test_phase132_loader_runs(tmp_path: Path) -> None:
    """run_phase132_analysis must return a non-empty dict."""
    from cwt.cgt.analysis.phase132_analysis import run_phase132_analysis

    payload = run_phase132_analysis(project_root=_PROJECT_ROOT, output_root=tmp_path)
    assert isinstance(payload, dict), 'run_phase132_analysis must return a dict'
    assert payload, 'run_phase132_analysis returned empty dict'
    assert payload['metrics']['pooled_six_bridge_adversarial_corrected_r2'] >= 0.88


# ===========================================================================
# Phase 133 — Bridge family holdout audit (benchmark scaffold family)
# ===========================================================================


@pytest.mark.unit
def test_phase133_artifact_exists() -> None:
    """Phase 133 artifact must exist on disk."""
    assert _P133.exists(), f"Missing: {_P133}"


@pytest.mark.unit
def test_phase133_artifact_json_valid() -> None:
    """Phase 133 artifact must be valid JSON."""
    assert _P133.exists(), f"Missing: {_P133}"
    data = json.loads(_P133.read_text(encoding='utf-8'))
    assert isinstance(data, dict), "Phase 133 artifact root must be a dict"


@pytest.mark.unit
def test_phase133_artifact_structure() -> None:
    """Phase 133 artifact must contain required top-level keys."""
    data = json.loads(_P133.read_text(encoding='utf-8'))
    for key in ('phase', 'audit_type', 'families', 'metrics', 'verdict'):
        assert key in data, f"Phase 133 artifact missing key: {key!r}"
    for mkey in ('mean_heldout_combined_r2', 'min_heldout_combined_r2', 'weakest_family'):
        assert mkey in data['metrics'], f"Phase 133 metrics missing key: {mkey!r}"


@pytest.mark.unit
def test_phase133_metric_thresholds() -> None:
    """Phase 133 family holdout min R2 >= 0.84; weakest family = observed.

    Report: mean = 0.8812; min = 0.8461.
    """
    data = json.loads(_P133.read_text(encoding='utf-8'))
    m = data['metrics']
    assert m['mean_heldout_combined_r2'] >= 0.87, (
        f"Phase 133 mean_heldout_combined_r2 expected >= 0.87, "
        f"got {m['mean_heldout_combined_r2']}"
    )
    assert m['min_heldout_combined_r2'] >= 0.84, (
        f"Phase 133 min_heldout_combined_r2 expected >= 0.84, "
        f"got {m['min_heldout_combined_r2']}"
    )
    assert m['weakest_family'] == 'observed', (
        f"Phase 133 weakest_family expected 'observed', got {m['weakest_family']!r}"
    )
    assert len(data['families']) == 6, (
        f"Phase 133 expected 6 families, got {len(data['families'])}"
    )
    assert data['verdict'] == 'bridge_family_holdout_supported', (
        f"Unexpected verdict: {data['verdict']!r}"
    )


@pytest.mark.unit
def test_phase133_loader_importable() -> None:
    """phase133_analysis module must be importable and expose run_phase133_analysis."""
    mod = importlib.import_module('cwt.cgt.analysis.phase133_analysis')
    assert hasattr(mod, 'run_phase133_analysis'), (
        "phase133_analysis missing 'run_phase133_analysis'"
    )


@pytest.mark.unit
def test_phase133_loader_runs(tmp_path: Path) -> None:
    """run_phase133_analysis must return a non-empty dict."""
    from cwt.cgt.analysis.phase133_analysis import run_phase133_analysis

    payload = run_phase133_analysis(project_root=_PROJECT_ROOT, output_root=tmp_path)
    assert isinstance(payload, dict), 'run_phase133_analysis must return a dict'
    assert payload, 'run_phase133_analysis returned empty dict'
    assert payload['metrics']['min_heldout_combined_r2'] >= 0.84


# ===========================================================================
# Phase 134 — Bridge tensor/compactness correction candidate (benchmark scaffold family)
# ===========================================================================


@pytest.mark.unit
def test_phase134_artifact_exists() -> None:
    """Phase 134 artifact must exist on disk."""
    assert _P134.exists(), f"Missing: {_P134}"


@pytest.mark.unit
def test_phase134_artifact_json_valid() -> None:
    """Phase 134 artifact must be valid JSON."""
    assert _P134.exists(), f"Missing: {_P134}"
    data = json.loads(_P134.read_text(encoding='utf-8'))
    assert isinstance(data, dict), "Phase 134 artifact root must be a dict"


@pytest.mark.unit
def test_phase134_artifact_structure() -> None:
    """Phase 134 artifact must contain required top-level keys."""
    data = json.loads(_P134.read_text(encoding='utf-8'))
    for key in ('phase', 'correction_type', 'metrics', 'verdict'):
        assert key in data, f"Phase 134 artifact missing key: {key!r}"
    for mkey in ('baseline_corrected_r2', 'tensor_compactness_corrected_r2'):
        assert mkey in data['metrics'], f"Phase 134 metrics missing key: {mkey!r}"


@pytest.mark.unit
def test_phase134_metric_thresholds() -> None:
    """Phase 134 tensor/compactness corrected R2 must exceed baseline.

    Report: baseline_r2 = 0.8844; tensor_compactness_corrected_r2 = 0.8968.
    """
    data = json.loads(_P134.read_text(encoding='utf-8'))
    m = data['metrics']
    assert m['tensor_compactness_corrected_r2'] > m['baseline_corrected_r2'], (
        "Phase 134 tensor_compactness_corrected_r2 must exceed baseline_corrected_r2"
    )
    assert m['tensor_compactness_corrected_r2'] >= 0.89, (
        f"Phase 134 tensor_compactness_corrected_r2 expected >= 0.89, "
        f"got {m['tensor_compactness_corrected_r2']}"
    )
    assert m['tensor_compactness_sign_agreement'] >= 0.97, (
        f"Phase 134 tensor_compactness_sign_agreement expected >= 0.97, "
        f"got {m['tensor_compactness_sign_agreement']}"
    )
    assert data['verdict'] == 'bridge_tensor_compactness_candidate_supported', (
        f"Unexpected verdict: {data['verdict']!r}"
    )


@pytest.mark.unit
def test_phase134_loader_importable() -> None:
    """phase134_analysis module must be importable and expose run_phase134_analysis."""
    mod = importlib.import_module('cwt.cgt.analysis.phase134_analysis')
    assert hasattr(mod, 'run_phase134_analysis'), (
        "phase134_analysis missing 'run_phase134_analysis'"
    )


@pytest.mark.unit
def test_phase134_loader_runs(tmp_path: Path) -> None:
    """run_phase134_analysis must return a non-empty dict."""
    from cwt.cgt.analysis.phase134_analysis import run_phase134_analysis

    payload = run_phase134_analysis(project_root=_PROJECT_ROOT, output_root=tmp_path)
    assert isinstance(payload, dict), 'run_phase134_analysis must return a dict'
    assert payload, 'run_phase134_analysis returned empty dict'
    assert payload['metrics']['tensor_compactness_corrected_r2'] >= 0.89


# ===========================================================================
# Phase 135 — Bridge calibration-free minimal (benchmark scaffold family)
# ===========================================================================


@pytest.mark.unit
def test_phase135_artifact_exists() -> None:
    """Phase 135 artifact must exist on disk."""
    assert _P135.exists(), f"Missing: {_P135}"


@pytest.mark.unit
def test_phase135_artifact_json_valid() -> None:
    """Phase 135 artifact must be valid JSON."""
    assert _P135.exists(), f"Missing: {_P135}"
    data = json.loads(_P135.read_text(encoding='utf-8'))
    assert isinstance(data, dict), "Phase 135 artifact root must be a dict"


@pytest.mark.unit
def test_phase135_artifact_structure() -> None:
    """Phase 135 artifact must contain required top-level keys."""
    data = json.loads(_P135.read_text(encoding='utf-8'))
    for key in ('phase', 'artifact', 'metrics', 'verdict'):
        assert key in data, f"Phase 135 artifact missing key: {key!r}"
    for mkey in ('calibration_free_bridge_positive_r2', 'calibration_free_bridge_adversarial_corrected_r2'):
        assert mkey in data['metrics'], f"Phase 135 metrics missing key: {mkey!r}"


@pytest.mark.unit
def test_phase135_metric_thresholds() -> None:
    """Phase 135 calibration-free metrics must be within accepted bridge bands.

    Report: positive_r2 = 0.9246; adversarial_corrected_r2 = 0.8789.
    """
    data = json.loads(_P135.read_text(encoding='utf-8'))
    m = data['metrics']
    assert m['calibration_free_bridge_positive_r2'] >= 0.91, (
        f"Phase 135 calibration_free_bridge_positive_r2 expected >= 0.91, "
        f"got {m['calibration_free_bridge_positive_r2']}"
    )
    assert m['calibration_free_bridge_adversarial_corrected_r2'] >= 0.87, (
        f"Phase 135 calibration_free_bridge_adversarial_corrected_r2 expected >= 0.87, "
        f"got {m['calibration_free_bridge_adversarial_corrected_r2']}"
    )
    assert data['verdict'] == 'bridge_calibration_free_minimal_supported', (
        f"Unexpected verdict: {data['verdict']!r}"
    )


@pytest.mark.unit
def test_phase135_loader_importable() -> None:
    """phase135_analysis module must be importable and expose run_phase135_analysis."""
    mod = importlib.import_module('cwt.cgt.analysis.phase135_analysis')
    assert hasattr(mod, 'run_phase135_analysis'), (
        "phase135_analysis missing 'run_phase135_analysis'"
    )


@pytest.mark.unit
def test_phase135_loader_runs(tmp_path: Path) -> None:
    """run_phase135_analysis must return a non-empty dict."""
    from cwt.cgt.analysis.phase135_analysis import run_phase135_analysis

    payload = run_phase135_analysis(project_root=_PROJECT_ROOT, output_root=tmp_path)
    assert isinstance(payload, dict), 'run_phase135_analysis must return a dict'
    assert payload, 'run_phase135_analysis returned empty dict'
    assert payload['metrics']['calibration_free_bridge_positive_r2'] >= 0.91


# ===========================================================================
# Phase 136 — Bridge boundary refresh 2 (benchmark scaffold family)
# ===========================================================================


@pytest.mark.unit
def test_phase136_artifact_exists() -> None:
    """Phase 136 artifact must exist on disk."""
    assert _P136.exists(), f"Missing: {_P136}"


@pytest.mark.unit
def test_phase136_artifact_json_valid() -> None:
    """Phase 136 artifact must be valid JSON."""
    assert _P136.exists(), f"Missing: {_P136}"
    data = json.loads(_P136.read_text(encoding='utf-8'))
    assert isinstance(data, dict), "Phase 136 artifact root must be a dict"


@pytest.mark.unit
def test_phase136_artifact_structure() -> None:
    """Phase 136 artifact must contain required top-level keys."""
    data = json.loads(_P136.read_text(encoding='utf-8'))
    for key in ('phase', 'bands', 'summary'):
        assert key in data, f"Phase 136 artifact missing key: {key!r}"
    for bkey in ('bridge_positive_band', 'bridge_adversarial_corrected_band',
                 'bridge_family_holdout_band', 'weakest_bridge_benchmark', 'weakest_bridge_family'):
        assert bkey in data['bands'], f"Phase 136 bands missing key: {bkey!r}"


@pytest.mark.unit
def test_phase136_metric_thresholds() -> None:
    """Phase 136 boundary bands must reflect six-benchmark bridge state.

    Report: positive_band = [0.9098, 0.9368]; adversarial_corrected = [0.8382, 0.8968];
    family_holdout = [0.8461, 0.9144].
    """
    data = json.loads(_P136.read_text(encoding='utf-8'))
    bands = data['bands']
    bp = bands['bridge_positive_band']
    ba = bands['bridge_adversarial_corrected_band']
    bfh = bands['bridge_family_holdout_band']
    assert bp[0] >= 0.90, f"Phase 136 positive_band lower expected >= 0.90, got {bp[0]}"
    assert bp[1] >= 0.93, f"Phase 136 positive_band upper expected >= 0.93, got {bp[1]}"
    assert ba[0] >= 0.83, f"Phase 136 adversarial_corrected_band lower expected >= 0.83, got {ba[0]}"
    assert ba[1] >= 0.89, f"Phase 136 adversarial_corrected_band upper expected >= 0.89, got {ba[1]}"
    assert bfh[0] >= 0.84, f"Phase 136 family_holdout_band lower expected >= 0.84, got {bfh[0]}"
    assert bfh[1] >= 0.91, f"Phase 136 family_holdout_band upper expected >= 0.91, got {bfh[1]}"
    assert bands['weakest_bridge_benchmark'] == 'T_semisynthetic_observed', (
        f"Phase 136 weakest_bridge_benchmark unexpected: {bands['weakest_bridge_benchmark']!r}"
    )
    assert bands['weakest_bridge_family'] == 'observed', (
        f"Phase 136 weakest_bridge_family expected 'observed', got {bands['weakest_bridge_family']!r}"
    )


@pytest.mark.unit
def test_phase136_loader_importable() -> None:
    """phase136_analysis module must be importable and expose run_phase136_analysis."""
    mod = importlib.import_module('cwt.cgt.analysis.phase136_analysis')
    assert hasattr(mod, 'run_phase136_analysis'), (
        "phase136_analysis missing 'run_phase136_analysis'"
    )


@pytest.mark.unit
def test_phase136_loader_runs(tmp_path: Path) -> None:
    """run_phase136_analysis must return a non-empty dict."""
    from cwt.cgt.analysis.phase136_analysis import run_phase136_analysis

    payload = run_phase136_analysis(project_root=_PROJECT_ROOT, output_root=tmp_path)
    assert isinstance(payload, dict), 'run_phase136_analysis must return a dict'
    assert payload, 'run_phase136_analysis returned empty dict'
    assert 'bands' in payload
