"""Smoke tests for CGT Phases 147-156 result artifacts and analysis modules.

Covers:
- Existence and JSON-validity of the Phase 147-156 artifacts.
- Importability of the phase analysis modules.
- Structural integrity of each artifact (top-level keys present).
- Metric thresholds derived from bundle reports and pinned to observed JSON values.
- Execution of run_phaseN_analysis() to verify correct output.

Benchmark layout:
  benchmark_AB_thinned_window/ — Phases 147 (eighth bridge positive) and 149 (adversarial)
  benchmark_BB_sensor_gap/     — Phases 151 (second less-synthetic positive) and 152 (adversarial)
  benchmark_scaffold_family/   — Phases 148, 150, 153, 154, 155, 156

Phase 141 was report-only (no JSON artifact, carried from v7.3).
Phases 147-156 constitute the "eighth-bridge and tensor-law" block (bundle v7.4).
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
_AB_DIR = _PROJECT_ROOT / 'cgt_benchmarks' / 'results' / 'benchmark_AB_thinned_window'
_BB_DIR = _PROJECT_ROOT / 'cgt_benchmarks' / 'results' / 'benchmark_BB_sensor_gap'

_P147 = _AB_DIR / 'benchmark_ab_phase147_eighth_bridge_positive.json'
_P148 = _SCAFFOLD_DIR / 'benchmark_scaffold_phase148_bridge_family_adversarial_pooled.json'
_P149 = _AB_DIR / 'benchmark_ab_phase149_bridge_adversarial_tensor_compactness.json'
_P150 = _SCAFFOLD_DIR / 'benchmark_scaffold_phase150_bridge_correction_comparison.json'
_P151 = _BB_DIR / 'benchmark_bb_phase151_second_less_synthetic_positive.json'
_P152 = _BB_DIR / 'benchmark_bb_phase152_second_less_synthetic_adversarial.json'
_P153 = _SCAFFOLD_DIR / 'benchmark_scaffold_phase153_bridge_loo_with_pilots.json'
_P154 = _SCAFFOLD_DIR / 'benchmark_scaffold_phase154_bridge_tensor_law_candidate.json'
_P155 = _SCAFFOLD_DIR / 'benchmark_scaffold_phase155_pooled_eight_bridge_positive.json'
_P156 = _SCAFFOLD_DIR / 'benchmark_scaffold_phase156_pooled_eight_bridge_adversarial.json'


# ===========================================================================
# Phase 147 — Eighth bridge positive (benchmark AB thinned-window)
# ===========================================================================


@pytest.mark.unit
def test_phase147_artifact_exists() -> None:
    """Phase 147 artifact must exist on disk."""
    assert _P147.exists(), f"Missing: {_P147}"


@pytest.mark.unit
def test_phase147_artifact_json_valid() -> None:
    """Phase 147 artifact must be valid JSON."""
    assert _P147.exists(), f"Missing: {_P147}"
    data = json.loads(_P147.read_text(encoding='utf-8'))
    assert isinstance(data, dict), "Phase 147 artifact root must be a dict"


@pytest.mark.unit
def test_phase147_artifact_structure() -> None:
    """Phase 147 artifact must contain required top-level keys."""
    data = json.loads(_P147.read_text(encoding='utf-8'))
    for key in ('phase', 'benchmark', 'heldout', 'verdict'):
        assert key in data, f"Phase 147 artifact missing key: {key!r}"
    for subkey in ('combined_r2', 'sign_agreement'):
        assert subkey in data['heldout'], f"Phase 147 heldout missing key: {subkey!r}"


@pytest.mark.unit
def test_phase147_metric_thresholds() -> None:
    """Phase 147 metrics must meet eighth-bridge acceptance bounds.

    Report: switch-slice held-out combined R2 = 0.9176; sign_agreement = 1.0.
    """
    data = json.loads(_P147.read_text(encoding='utf-8'))
    assert data['heldout']['combined_r2'] >= 0.91, (
        f"Phase 147 heldout combined_r2 expected >= 0.91, "
        f"got {data['heldout']['combined_r2']}"
    )
    assert data['heldout']['sign_agreement'] >= 0.99, (
        f"Phase 147 sign_agreement expected >= 0.99, "
        f"got {data['heldout']['sign_agreement']}"
    )
    assert data['verdict'] == 'eighth_bridge_positive_supported', (
        f"Unexpected verdict: {data['verdict']!r}"
    )


@pytest.mark.unit
def test_phase147_loader_importable() -> None:
    """phase147_analysis module must be importable and expose run_phase147_analysis."""
    mod = importlib.import_module('cwt.cgt.analysis.phase147_analysis')
    assert hasattr(mod, 'run_phase147_analysis'), (
        "phase147_analysis missing 'run_phase147_analysis'"
    )


@pytest.mark.unit
def test_phase147_loader_runs(tmp_path: Path) -> None:
    """run_phase147_analysis must return a non-empty dict."""
    from cwt.cgt.analysis.phase147_analysis import run_phase147_analysis

    payload = run_phase147_analysis(project_root=_PROJECT_ROOT, output_root=tmp_path)
    assert isinstance(payload, dict), 'run_phase147_analysis must return a dict'
    assert payload, 'run_phase147_analysis returned empty dict'
    assert payload['heldout']['combined_r2'] >= 0.91


# ===========================================================================
# Phase 148 — Pooled bridge family adversarial summary (benchmark scaffold family)
# ===========================================================================


@pytest.mark.unit
def test_phase148_artifact_exists() -> None:
    """Phase 148 artifact must exist on disk."""
    assert _P148.exists(), f"Missing: {_P148}"


@pytest.mark.unit
def test_phase148_artifact_json_valid() -> None:
    """Phase 148 artifact must be valid JSON."""
    assert _P148.exists(), f"Missing: {_P148}"
    data = json.loads(_P148.read_text(encoding='utf-8'))
    assert isinstance(data, dict), "Phase 148 artifact root must be a dict"


@pytest.mark.unit
def test_phase148_artifact_structure() -> None:
    """Phase 148 artifact must contain required top-level keys."""
    data = json.loads(_P148.read_text(encoding='utf-8'))
    for key in ('phase', 'families', 'aggregate'):
        assert key in data, f"Phase 148 artifact missing key: {key!r}"
    for family in ('event_burst', 'less_synthetic', 'thinned_window'):
        assert family in data['families'], (
            f"Phase 148 families missing entry: {family!r}"
        )
    for subkey in ('raw_combined_r2', 'corrected_combined_r2', 'corrected_sign_agreement'):
        assert subkey in data['aggregate'], (
            f"Phase 148 aggregate missing key: {subkey!r}"
        )


@pytest.mark.unit
def test_phase148_metric_thresholds() -> None:
    """Phase 148 pooled bridge adversarial: raw degrades, corrected recovers.

    Report: aggregate raw_combined_r2 = 0.5487; corrected_combined_r2 = 0.8994;
    corrected_sign_agreement = 0.975.
    """
    data = json.loads(_P148.read_text(encoding='utf-8'))
    assert data['aggregate']['raw_combined_r2'] < 0.62, (
        f"Phase 148 raw_combined_r2 expected < 0.62 (adversarial degrades), "
        f"got {data['aggregate']['raw_combined_r2']}"
    )
    assert data['aggregate']['corrected_combined_r2'] >= 0.88, (
        f"Phase 148 corrected_combined_r2 expected >= 0.88, "
        f"got {data['aggregate']['corrected_combined_r2']}"
    )
    assert data['aggregate']['corrected_sign_agreement'] >= 0.96, (
        f"Phase 148 corrected_sign_agreement expected >= 0.96, "
        f"got {data['aggregate']['corrected_sign_agreement']}"
    )


@pytest.mark.unit
def test_phase148_loader_importable() -> None:
    """phase148_analysis module must be importable and expose run_phase148_analysis."""
    mod = importlib.import_module('cwt.cgt.analysis.phase148_analysis')
    assert hasattr(mod, 'run_phase148_analysis'), (
        "phase148_analysis missing 'run_phase148_analysis'"
    )


@pytest.mark.unit
def test_phase148_loader_runs(tmp_path: Path) -> None:
    """run_phase148_analysis must return a non-empty dict."""
    from cwt.cgt.analysis.phase148_analysis import run_phase148_analysis

    payload = run_phase148_analysis(project_root=_PROJECT_ROOT, output_root=tmp_path)
    assert isinstance(payload, dict), 'run_phase148_analysis must return a dict'
    assert payload, 'run_phase148_analysis returned empty dict'
    assert payload['aggregate']['corrected_combined_r2'] >= 0.88


# ===========================================================================
# Phase 149 — Eighth bridge adversarial on benchmark AB (thinned-window)
# ===========================================================================


@pytest.mark.unit
def test_phase149_artifact_exists() -> None:
    """Phase 149 artifact must exist on disk."""
    assert _P149.exists(), f"Missing: {_P149}"


@pytest.mark.unit
def test_phase149_artifact_json_valid() -> None:
    """Phase 149 artifact must be valid JSON."""
    assert _P149.exists(), f"Missing: {_P149}"
    data = json.loads(_P149.read_text(encoding='utf-8'))
    assert isinstance(data, dict), "Phase 149 artifact root must be a dict"


@pytest.mark.unit
def test_phase149_artifact_structure() -> None:
    """Phase 149 artifact must contain required top-level keys."""
    data = json.loads(_P149.read_text(encoding='utf-8'))
    for key in ('phase', 'benchmark', 'raw', 'corrected', 'verdict'):
        assert key in data, f"Phase 149 artifact missing key: {key!r}"
    for subkey in ('combined_r2', 'sign_agreement'):
        assert subkey in data['raw'], f"Phase 149 raw missing key: {subkey!r}"
    for subkey in ('combined_r2', 'sign_agreement'):
        assert subkey in data['corrected'], f"Phase 149 corrected missing key: {subkey!r}"


@pytest.mark.unit
def test_phase149_metric_thresholds() -> None:
    """Phase 149 must show adversarial degradation and correction recovery on benchmark AB.

    Report: raw combined_r2 = 0.5224; corrected combined_r2 = 0.8871;
    corrected sign_agreement = 0.9722.
    """
    data = json.loads(_P149.read_text(encoding='utf-8'))
    assert data['raw']['combined_r2'] < 0.60, (
        f"Phase 149 raw combined_r2 expected < 0.60 (adversarial degrades), "
        f"got {data['raw']['combined_r2']}"
    )
    assert data['corrected']['combined_r2'] >= 0.88, (
        f"Phase 149 corrected combined_r2 expected >= 0.88, "
        f"got {data['corrected']['combined_r2']}"
    )
    assert data['corrected']['sign_agreement'] >= 0.96, (
        f"Phase 149 corrected sign_agreement expected >= 0.96, "
        f"got {data['corrected']['sign_agreement']}"
    )
    assert data['verdict'] == 'eighth_bridge_adversarial_corrected_supported', (
        f"Unexpected verdict: {data['verdict']!r}"
    )


@pytest.mark.unit
def test_phase149_loader_importable() -> None:
    """phase149_analysis module must be importable and expose run_phase149_analysis."""
    mod = importlib.import_module('cwt.cgt.analysis.phase149_analysis')
    assert hasattr(mod, 'run_phase149_analysis'), (
        "phase149_analysis missing 'run_phase149_analysis'"
    )


@pytest.mark.unit
def test_phase149_loader_runs(tmp_path: Path) -> None:
    """run_phase149_analysis must return a non-empty dict."""
    from cwt.cgt.analysis.phase149_analysis import run_phase149_analysis

    payload = run_phase149_analysis(project_root=_PROJECT_ROOT, output_root=tmp_path)
    assert isinstance(payload, dict), 'run_phase149_analysis must return a dict'
    assert payload, 'run_phase149_analysis returned empty dict'
    assert payload['corrected']['combined_r2'] >= 0.88


# ===========================================================================
# Phase 150 — Bridge correction comparison: tensor/compactness vs minimal
# ===========================================================================


@pytest.mark.unit
def test_phase150_artifact_exists() -> None:
    """Phase 150 artifact must exist on disk."""
    assert _P150.exists(), f"Missing: {_P150}"


@pytest.mark.unit
def test_phase150_artifact_json_valid() -> None:
    """Phase 150 artifact must be valid JSON."""
    assert _P150.exists(), f"Missing: {_P150}"
    data = json.loads(_P150.read_text(encoding='utf-8'))
    assert isinstance(data, dict), "Phase 150 artifact root must be a dict"


@pytest.mark.unit
def test_phase150_artifact_structure() -> None:
    """Phase 150 artifact must contain required top-level keys."""
    data = json.loads(_P150.read_text(encoding='utf-8'))
    for key in ('phase', 'minimal_calibration_free', 'tensor_compactness', 'winner'):
        assert key in data, f"Phase 150 artifact missing key: {key!r}"
    for subkey in ('corrected_combined_r2',):
        assert subkey in data['minimal_calibration_free'], (
            f"Phase 150 minimal_calibration_free missing key: {subkey!r}"
        )
        assert subkey in data['tensor_compactness'], (
            f"Phase 150 tensor_compactness missing key: {subkey!r}"
        )


@pytest.mark.unit
def test_phase150_metric_thresholds() -> None:
    """Phase 150 tensor/compactness must outperform minimal calibration-free.

    Report: minimal = 0.8612; tensor_compactness = 0.8994; winner = tensor_compactness.
    """
    data = json.loads(_P150.read_text(encoding='utf-8'))
    assert (
        data['tensor_compactness']['corrected_combined_r2']
        > data['minimal_calibration_free']['corrected_combined_r2']
    ), "Phase 150 tensor_compactness must exceed minimal_calibration_free"
    assert data['tensor_compactness']['corrected_combined_r2'] >= 0.88, (
        f"Phase 150 tensor_compactness corrected_combined_r2 expected >= 0.88, "
        f"got {data['tensor_compactness']['corrected_combined_r2']}"
    )
    assert data['winner'] == 'tensor_compactness', (
        f"Unexpected winner: {data['winner']!r}"
    )


@pytest.mark.unit
def test_phase150_loader_importable() -> None:
    """phase150_analysis module must be importable and expose run_phase150_analysis."""
    mod = importlib.import_module('cwt.cgt.analysis.phase150_analysis')
    assert hasattr(mod, 'run_phase150_analysis'), (
        "phase150_analysis missing 'run_phase150_analysis'"
    )


@pytest.mark.unit
def test_phase150_loader_runs(tmp_path: Path) -> None:
    """run_phase150_analysis must return a non-empty dict."""
    from cwt.cgt.analysis.phase150_analysis import run_phase150_analysis

    payload = run_phase150_analysis(project_root=_PROJECT_ROOT, output_root=tmp_path)
    assert isinstance(payload, dict), 'run_phase150_analysis must return a dict'
    assert payload, 'run_phase150_analysis returned empty dict'
    assert payload['tensor_compactness']['corrected_combined_r2'] >= 0.88


# ===========================================================================
# Phase 151 — Second less-synthetic positive pilot (benchmark BB sensor-gap)
# ===========================================================================


@pytest.mark.unit
def test_phase151_artifact_exists() -> None:
    """Phase 151 artifact must exist on disk."""
    assert _P151.exists(), f"Missing: {_P151}"


@pytest.mark.unit
def test_phase151_artifact_json_valid() -> None:
    """Phase 151 artifact must be valid JSON."""
    assert _P151.exists(), f"Missing: {_P151}"
    data = json.loads(_P151.read_text(encoding='utf-8'))
    assert isinstance(data, dict), "Phase 151 artifact root must be a dict"


@pytest.mark.unit
def test_phase151_artifact_structure() -> None:
    """Phase 151 artifact must contain required top-level keys."""
    data = json.loads(_P151.read_text(encoding='utf-8'))
    for key in ('phase', 'benchmark', 'heldout', 'verdict'):
        assert key in data, f"Phase 151 artifact missing key: {key!r}"
    for subkey in ('combined_r2', 'sign_agreement'):
        assert subkey in data['heldout'], f"Phase 151 heldout missing key: {subkey!r}"


@pytest.mark.unit
def test_phase151_metric_thresholds() -> None:
    """Phase 151 less-synthetic positive R2 >= 0.87; sign_agreement >= 0.99.

    Report: switch-slice held-out combined R2 = 0.8748; sign_agreement = 1.0.
    """
    data = json.loads(_P151.read_text(encoding='utf-8'))
    assert data['heldout']['combined_r2'] >= 0.87, (
        f"Phase 151 heldout combined_r2 expected >= 0.87, "
        f"got {data['heldout']['combined_r2']}"
    )
    assert data['heldout']['sign_agreement'] >= 0.99, (
        f"Phase 151 sign_agreement expected >= 0.99, "
        f"got {data['heldout']['sign_agreement']}"
    )
    assert data['verdict'] == 'second_less_synthetic_bridge_positive_supported', (
        f"Unexpected verdict: {data['verdict']!r}"
    )


@pytest.mark.unit
def test_phase151_loader_importable() -> None:
    """phase151_analysis module must be importable and expose run_phase151_analysis."""
    mod = importlib.import_module('cwt.cgt.analysis.phase151_analysis')
    assert hasattr(mod, 'run_phase151_analysis'), (
        "phase151_analysis missing 'run_phase151_analysis'"
    )


@pytest.mark.unit
def test_phase151_loader_runs(tmp_path: Path) -> None:
    """run_phase151_analysis must return a non-empty dict."""
    from cwt.cgt.analysis.phase151_analysis import run_phase151_analysis

    payload = run_phase151_analysis(project_root=_PROJECT_ROOT, output_root=tmp_path)
    assert isinstance(payload, dict), 'run_phase151_analysis must return a dict'
    assert payload, 'run_phase151_analysis returned empty dict'
    assert payload['heldout']['combined_r2'] >= 0.87


# ===========================================================================
# Phase 152 — Second less-synthetic adversarial pilot (benchmark BB sensor-gap)
# ===========================================================================


@pytest.mark.unit
def test_phase152_artifact_exists() -> None:
    """Phase 152 artifact must exist on disk."""
    assert _P152.exists(), f"Missing: {_P152}"


@pytest.mark.unit
def test_phase152_artifact_json_valid() -> None:
    """Phase 152 artifact must be valid JSON."""
    assert _P152.exists(), f"Missing: {_P152}"
    data = json.loads(_P152.read_text(encoding='utf-8'))
    assert isinstance(data, dict), "Phase 152 artifact root must be a dict"


@pytest.mark.unit
def test_phase152_artifact_structure() -> None:
    """Phase 152 artifact must contain required top-level keys."""
    data = json.loads(_P152.read_text(encoding='utf-8'))
    for key in ('phase', 'benchmark', 'raw', 'corrected', 'verdict'):
        assert key in data, f"Phase 152 artifact missing key: {key!r}"
    for subkey in ('combined_r2', 'sign_agreement'):
        assert subkey in data['raw'], f"Phase 152 raw missing key: {subkey!r}"
    for subkey in ('combined_r2', 'sign_agreement'):
        assert subkey in data['corrected'], f"Phase 152 corrected missing key: {subkey!r}"


@pytest.mark.unit
def test_phase152_metric_thresholds() -> None:
    """Phase 152 must show adversarial degradation and correction recovery on benchmark BB.

    Report: raw combined_r2 = 0.4011; corrected combined_r2 = 0.8049;
    corrected sign_agreement = 0.9444.
    """
    data = json.loads(_P152.read_text(encoding='utf-8'))
    assert data['raw']['combined_r2'] < 0.45, (
        f"Phase 152 raw combined_r2 expected < 0.45 (adversarial degrades), "
        f"got {data['raw']['combined_r2']}"
    )
    assert data['corrected']['combined_r2'] >= 0.80, (
        f"Phase 152 corrected combined_r2 expected >= 0.80, "
        f"got {data['corrected']['combined_r2']}"
    )
    assert data['corrected']['sign_agreement'] >= 0.93, (
        f"Phase 152 corrected sign_agreement expected >= 0.93, "
        f"got {data['corrected']['sign_agreement']}"
    )
    assert data['verdict'] == 'second_less_synthetic_bridge_adversarial_supported', (
        f"Unexpected verdict: {data['verdict']!r}"
    )


@pytest.mark.unit
def test_phase152_loader_importable() -> None:
    """phase152_analysis module must be importable and expose run_phase152_analysis."""
    mod = importlib.import_module('cwt.cgt.analysis.phase152_analysis')
    assert hasattr(mod, 'run_phase152_analysis'), (
        "phase152_analysis missing 'run_phase152_analysis'"
    )


@pytest.mark.unit
def test_phase152_loader_runs(tmp_path: Path) -> None:
    """run_phase152_analysis must return a non-empty dict."""
    from cwt.cgt.analysis.phase152_analysis import run_phase152_analysis

    payload = run_phase152_analysis(project_root=_PROJECT_ROOT, output_root=tmp_path)
    assert isinstance(payload, dict), 'run_phase152_analysis must return a dict'
    assert payload, 'run_phase152_analysis returned empty dict'
    assert payload['corrected']['combined_r2'] >= 0.80


# ===========================================================================
# Phase 153 — Bridge leave-one-benchmark-out audit with pilots
# ===========================================================================


@pytest.mark.unit
def test_phase153_artifact_exists() -> None:
    """Phase 153 artifact must exist on disk."""
    assert _P153.exists(), f"Missing: {_P153}"


@pytest.mark.unit
def test_phase153_artifact_json_valid() -> None:
    """Phase 153 artifact must be valid JSON."""
    assert _P153.exists(), f"Missing: {_P153}"
    data = json.loads(_P153.read_text(encoding='utf-8'))
    assert isinstance(data, dict), "Phase 153 artifact root must be a dict"


@pytest.mark.unit
def test_phase153_artifact_structure() -> None:
    """Phase 153 artifact must contain required top-level keys."""
    data = json.loads(_P153.read_text(encoding='utf-8'))
    for key in ('phase', 'leave_one_benchmark_out', 'mean_heldout_combined_r2',
                'weakest_benchmark'):
        assert key in data, f"Phase 153 artifact missing key: {key!r}"
    assert len(data['leave_one_benchmark_out']) == 8, (
        f"Phase 153 LOO expected 8 entries, got {len(data['leave_one_benchmark_out'])}"
    )


@pytest.mark.unit
def test_phase153_metric_thresholds() -> None:
    """Phase 153 bridge LOO mean held-out combined R2 >= 0.87; weakest = BB_sensor_gap.

    Report: mean_heldout_combined_r2 = 0.8798; weakest_benchmark = BB_sensor_gap.
    All individual LOO R2 values >= 0.83.
    """
    data = json.loads(_P153.read_text(encoding='utf-8'))
    assert data['mean_heldout_combined_r2'] >= 0.87, (
        f"Phase 153 mean_heldout_combined_r2 expected >= 0.87, "
        f"got {data['mean_heldout_combined_r2']}"
    )
    assert data['weakest_benchmark'] == 'BB_sensor_gap', (
        f"Phase 153 weakest_benchmark expected 'BB_sensor_gap', "
        f"got {data['weakest_benchmark']!r}"
    )
    for bench, r2 in data['leave_one_benchmark_out'].items():
        assert r2 >= 0.83, (
            f"Phase 153 LOO R2 for {bench!r} expected >= 0.83, got {r2}"
        )


@pytest.mark.unit
def test_phase153_loader_importable() -> None:
    """phase153_analysis module must be importable and expose run_phase153_analysis."""
    mod = importlib.import_module('cwt.cgt.analysis.phase153_analysis')
    assert hasattr(mod, 'run_phase153_analysis'), (
        "phase153_analysis missing 'run_phase153_analysis'"
    )


@pytest.mark.unit
def test_phase153_loader_runs(tmp_path: Path) -> None:
    """run_phase153_analysis must return a non-empty dict."""
    from cwt.cgt.analysis.phase153_analysis import run_phase153_analysis

    payload = run_phase153_analysis(project_root=_PROJECT_ROOT, output_root=tmp_path)
    assert isinstance(payload, dict), 'run_phase153_analysis must return a dict'
    assert payload, 'run_phase153_analysis returned empty dict'
    assert payload['mean_heldout_combined_r2'] >= 0.87


# ===========================================================================
# Phase 154 — Bridge tensor-law candidate (benchmark scaffold family)
# ===========================================================================


@pytest.mark.unit
def test_phase154_artifact_exists() -> None:
    """Phase 154 artifact must exist on disk."""
    assert _P154.exists(), f"Missing: {_P154}"


@pytest.mark.unit
def test_phase154_artifact_json_valid() -> None:
    """Phase 154 artifact must be valid JSON."""
    assert _P154.exists(), f"Missing: {_P154}"
    data = json.loads(_P154.read_text(encoding='utf-8'))
    assert isinstance(data, dict), "Phase 154 artifact root must be a dict"


@pytest.mark.unit
def test_phase154_artifact_structure() -> None:
    """Phase 154 artifact must contain required top-level keys."""
    data = json.loads(_P154.read_text(encoding='utf-8'))
    for key in ('phase', 'baseline_corrected_r2', 'tensor_law_corrected_r2',
                'tensor_law_sign_agreement', 'verdict'):
        assert key in data, f"Phase 154 artifact missing key: {key!r}"


@pytest.mark.unit
def test_phase154_metric_thresholds() -> None:
    """Phase 154 tensor-law candidate must improve over baseline corrected R2.

    Report: baseline_corrected_r2 = 0.8994; tensor_law_corrected_r2 = 0.9088;
    tensor_law_sign_agreement = 0.979.
    """
    data = json.loads(_P154.read_text(encoding='utf-8'))
    assert data['tensor_law_corrected_r2'] > data['baseline_corrected_r2'], (
        "Phase 154 tensor_law_corrected_r2 must exceed baseline_corrected_r2"
    )
    assert data['tensor_law_corrected_r2'] >= 0.90, (
        f"Phase 154 tensor_law_corrected_r2 expected >= 0.90, "
        f"got {data['tensor_law_corrected_r2']}"
    )
    assert data['tensor_law_sign_agreement'] >= 0.97, (
        f"Phase 154 tensor_law_sign_agreement expected >= 0.97, "
        f"got {data['tensor_law_sign_agreement']}"
    )
    assert data['verdict'] == 'bridge_tensor_law_candidate_supported', (
        f"Unexpected verdict: {data['verdict']!r}"
    )


@pytest.mark.unit
def test_phase154_loader_importable() -> None:
    """phase154_analysis module must be importable and expose run_phase154_analysis."""
    mod = importlib.import_module('cwt.cgt.analysis.phase154_analysis')
    assert hasattr(mod, 'run_phase154_analysis'), (
        "phase154_analysis missing 'run_phase154_analysis'"
    )


@pytest.mark.unit
def test_phase154_loader_runs(tmp_path: Path) -> None:
    """run_phase154_analysis must return a non-empty dict."""
    from cwt.cgt.analysis.phase154_analysis import run_phase154_analysis

    payload = run_phase154_analysis(project_root=_PROJECT_ROOT, output_root=tmp_path)
    assert isinstance(payload, dict), 'run_phase154_analysis must return a dict'
    assert payload, 'run_phase154_analysis returned empty dict'
    assert payload['tensor_law_corrected_r2'] >= 0.90


# ===========================================================================
# Phase 155 — Pooled eight-bridge positive summary (benchmark scaffold family)
# ===========================================================================


@pytest.mark.unit
def test_phase155_artifact_exists() -> None:
    """Phase 155 artifact must exist on disk."""
    assert _P155.exists(), f"Missing: {_P155}"


@pytest.mark.unit
def test_phase155_artifact_json_valid() -> None:
    """Phase 155 artifact must be valid JSON."""
    assert _P155.exists(), f"Missing: {_P155}"
    data = json.loads(_P155.read_text(encoding='utf-8'))
    assert isinstance(data, dict), "Phase 155 artifact root must be a dict"


@pytest.mark.unit
def test_phase155_artifact_structure() -> None:
    """Phase 155 artifact must contain required top-level keys."""
    data = json.loads(_P155.read_text(encoding='utf-8'))
    for key in ('phase', 'rule', 'heldout'):
        assert key in data, f"Phase 155 artifact missing key: {key!r}"
    for subkey in ('combined_r2', 'harder_family_combined_r2', 'sign_agreement'):
        assert subkey in data['heldout'], f"Phase 155 heldout missing key: {subkey!r}"


@pytest.mark.unit
def test_phase155_metric_thresholds() -> None:
    """Phase 155 pooled eight-bridge positive R2 >= 0.93; sign_agreement >= 0.99.

    Report: heldout combined_r2 = 0.9351; harder_family_combined_r2 = 0.9682;
    sign_agreement = 0.9926.
    """
    data = json.loads(_P155.read_text(encoding='utf-8'))
    assert data['heldout']['combined_r2'] >= 0.93, (
        f"Phase 155 heldout combined_r2 expected >= 0.93, "
        f"got {data['heldout']['combined_r2']}"
    )
    assert data['heldout']['harder_family_combined_r2'] >= 0.96, (
        f"Phase 155 harder_family_combined_r2 expected >= 0.96, "
        f"got {data['heldout']['harder_family_combined_r2']}"
    )
    assert data['heldout']['sign_agreement'] >= 0.99, (
        f"Phase 155 sign_agreement expected >= 0.99, "
        f"got {data['heldout']['sign_agreement']}"
    )
    assert data['rule'] == 'pooled_eight_bridge_positive', (
        f"Unexpected rule: {data['rule']!r}"
    )


@pytest.mark.unit
def test_phase155_loader_importable() -> None:
    """phase155_analysis module must be importable and expose run_phase155_analysis."""
    mod = importlib.import_module('cwt.cgt.analysis.phase155_analysis')
    assert hasattr(mod, 'run_phase155_analysis'), (
        "phase155_analysis missing 'run_phase155_analysis'"
    )


@pytest.mark.unit
def test_phase155_loader_runs(tmp_path: Path) -> None:
    """run_phase155_analysis must return a non-empty dict."""
    from cwt.cgt.analysis.phase155_analysis import run_phase155_analysis

    payload = run_phase155_analysis(project_root=_PROJECT_ROOT, output_root=tmp_path)
    assert isinstance(payload, dict), 'run_phase155_analysis must return a dict'
    assert payload, 'run_phase155_analysis returned empty dict'
    assert payload['heldout']['combined_r2'] >= 0.93


# ===========================================================================
# Phase 156 — Pooled eight-bridge adversarial summary (benchmark scaffold family)
# ===========================================================================


@pytest.mark.unit
def test_phase156_artifact_exists() -> None:
    """Phase 156 artifact must exist on disk."""
    assert _P156.exists(), f"Missing: {_P156}"


@pytest.mark.unit
def test_phase156_artifact_json_valid() -> None:
    """Phase 156 artifact must be valid JSON."""
    assert _P156.exists(), f"Missing: {_P156}"
    data = json.loads(_P156.read_text(encoding='utf-8'))
    assert isinstance(data, dict), "Phase 156 artifact root must be a dict"


@pytest.mark.unit
def test_phase156_artifact_structure() -> None:
    """Phase 156 artifact must contain required top-level keys."""
    data = json.loads(_P156.read_text(encoding='utf-8'))
    for key in ('phase', 'rule', 'raw', 'corrected', 'verdict'):
        assert key in data, f"Phase 156 artifact missing key: {key!r}"
    for subkey in ('combined_r2',):
        assert subkey in data['raw'], f"Phase 156 raw missing key: {subkey!r}"
    for subkey in ('combined_r2', 'sign_agreement'):
        assert subkey in data['corrected'], f"Phase 156 corrected missing key: {subkey!r}"


@pytest.mark.unit
def test_phase156_metric_thresholds() -> None:
    """Phase 156 pooled eight-bridge adversarial: raw degrades, corrected recovers.

    Report: raw combined_r2 = 0.5469; corrected combined_r2 = 0.9026;
    corrected sign_agreement = 0.9778.
    """
    data = json.loads(_P156.read_text(encoding='utf-8'))
    assert data['raw']['combined_r2'] < 0.60, (
        f"Phase 156 raw combined_r2 expected < 0.60 (adversarial degrades), "
        f"got {data['raw']['combined_r2']}"
    )
    assert data['corrected']['combined_r2'] >= 0.90, (
        f"Phase 156 corrected combined_r2 expected >= 0.90, "
        f"got {data['corrected']['combined_r2']}"
    )
    assert data['corrected']['sign_agreement'] >= 0.97, (
        f"Phase 156 corrected sign_agreement expected >= 0.97, "
        f"got {data['corrected']['sign_agreement']}"
    )
    assert data['verdict'] == 'pooled_eight_bridge_adversarial_supported', (
        f"Unexpected verdict: {data['verdict']!r}"
    )


@pytest.mark.unit
def test_phase156_loader_importable() -> None:
    """phase156_analysis module must be importable and expose run_phase156_analysis."""
    mod = importlib.import_module('cwt.cgt.analysis.phase156_analysis')
    assert hasattr(mod, 'run_phase156_analysis'), (
        "phase156_analysis missing 'run_phase156_analysis'"
    )


@pytest.mark.unit
def test_phase156_loader_runs(tmp_path: Path) -> None:
    """run_phase156_analysis must return a non-empty dict."""
    from cwt.cgt.analysis.phase156_analysis import run_phase156_analysis

    payload = run_phase156_analysis(project_root=_PROJECT_ROOT, output_root=tmp_path)
    assert isinstance(payload, dict), 'run_phase156_analysis must return a dict'
    assert payload, 'run_phase156_analysis returned empty dict'
    assert payload['corrected']['combined_r2'] >= 0.90
