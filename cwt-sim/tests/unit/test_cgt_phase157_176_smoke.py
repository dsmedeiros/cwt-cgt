"""Smoke tests for CGT Phases 157-176 result artifacts and analysis modules.

Covers:
- Existence and JSON-validity of the Phase 157-176 artifacts (phases with JSONs only).
- Importability of the phase analysis modules.
- Structural integrity of each artifact (top-level keys present).
- Metric thresholds derived from bundle reports and pinned to observed JSON values.
- Execution of run_phaseN_analysis() to verify correct output.

Benchmark layout:
  benchmark_AC_hidden_dropout_batching/ — Phase 157 (ninth bridge positive)
  benchmark_CC_delayed_release/         — Phases 160, 161
  benchmark_scaffold_family/            — Phases 158, 159, 162, 163, 164, 165, 166,
                                          169, 170, 173, 174, 175, 176
  benchmark_AD_bursty_censor/           — Phases 167, 168
  benchmark_DD_async_masked/            — Phases 171, 172

Phases with loaders (20):
  157, 158, 159, 160, 161, 162, 163, 164, 165, 166,
  167, 168, 169, 170, 171, 172, 173, 174, 175, 176.

Phases 157-176 constitute the "ninth- and tenth-bridge and tensor-law v2" block
(bundle v7.6).
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
_AC_DIR = _PROJECT_ROOT / 'cgt_benchmarks' / 'results' / 'benchmark_AC_hidden_dropout_batching'
_CC_DIR = _PROJECT_ROOT / 'cgt_benchmarks' / 'results' / 'benchmark_CC_delayed_release'
_AD_DIR = _PROJECT_ROOT / 'cgt_benchmarks' / 'results' / 'benchmark_AD_bursty_censor'
_DD_DIR = _PROJECT_ROOT / 'cgt_benchmarks' / 'results' / 'benchmark_DD_async_masked'

_P157 = _AC_DIR / 'benchmark_ac_phase157_ninth_bridge_positive.json'
_P158 = _SCAFFOLD_DIR / 'benchmark_scaffold_phase158_bridge_family_adversarial_with_ac.json'
_P159 = _SCAFFOLD_DIR / 'benchmark_scaffold_phase159_bridge_holdout_rule_comparison.json'
_P160 = _CC_DIR / 'benchmark_cc_phase160_third_less_synthetic_positive.json'
_P161 = _CC_DIR / 'benchmark_cc_phase161_third_less_synthetic_adversarial.json'
_P162 = _SCAFFOLD_DIR / 'benchmark_scaffold_phase162_bridge_loo_all_pilots.json'
_P163 = _SCAFFOLD_DIR / 'benchmark_scaffold_phase163_bridge_tensor_geometry_law.json'
_P164 = _SCAFFOLD_DIR / 'benchmark_scaffold_phase164_pooled_nine_bridge_positive.json'
_P165 = _SCAFFOLD_DIR / 'benchmark_scaffold_phase165_pooled_nine_bridge_adversarial.json'
_P166 = _SCAFFOLD_DIR / 'benchmark_scaffold_phase166_bridge_boundary_refresh.json'
_P167 = _AD_DIR / 'benchmark_ad_phase167_tenth_bridge_positive.json'
_P168 = _AD_DIR / 'benchmark_ad_phase168_tenth_bridge_adversarial.json'
_P169 = _SCAFFOLD_DIR / 'benchmark_scaffold_phase169_pooled_ten_bridge_positive.json'
_P170 = _SCAFFOLD_DIR / 'benchmark_scaffold_phase170_pooled_ten_bridge_adversarial.json'
_P171 = _DD_DIR / 'benchmark_dd_phase171_fourth_less_synthetic_positive.json'
_P172 = _DD_DIR / 'benchmark_dd_phase172_fourth_less_synthetic_adversarial.json'
_P173 = _SCAFFOLD_DIR / 'benchmark_scaffold_phase173_bridge_loo_all_pilots_expanded.json'
_P174 = _SCAFFOLD_DIR / 'benchmark_scaffold_phase174_bridge_holdout_expanded_comparison.json'
_P175 = _SCAFFOLD_DIR / 'benchmark_scaffold_phase175_bridge_tensor_geometry_law_v2.json'
_P176 = _SCAFFOLD_DIR / 'benchmark_scaffold_phase176_bridge_boundary_refresh_v3.json'


# ===========================================================================
# Phase 157 — Ninth bridge positive (benchmark AC hidden dropout batching)
# ===========================================================================


@pytest.mark.unit
def test_phase157_artifact_exists() -> None:
    """Phase 157 artifact must exist on disk."""
    assert _P157.exists(), f"Missing: {_P157}"


@pytest.mark.unit
def test_phase157_artifact_json_valid() -> None:
    """Phase 157 artifact must be valid JSON."""
    assert _P157.exists(), f"Missing: {_P157}"
    data = json.loads(_P157.read_text(encoding='utf-8'))
    assert isinstance(data, dict), "Phase 157 artifact root must be a dict"


@pytest.mark.unit
def test_phase157_artifact_structure() -> None:
    """Phase 157 artifact must contain required top-level keys."""
    data = json.loads(_P157.read_text(encoding='utf-8'))
    for key in ('phase', 'benchmark', 'metrics'):
        assert key in data, f"Phase 157 artifact missing key: {key!r}"
    for subkey in ('heldout_combined_r2', 'sign_agreement'):
        assert subkey in data['metrics'], f"Phase 157 metrics missing key: {subkey!r}"


@pytest.mark.unit
def test_phase157_metric_thresholds() -> None:
    """Phase 157 metrics must meet ninth-bridge acceptance bounds.

    Report: switch-slice held-out combined R2 = 0.9238; sign_agreement = 1.0.
    """
    data = json.loads(_P157.read_text(encoding='utf-8'))
    assert data['metrics']['heldout_combined_r2'] >= 0.92, (
        f"Phase 157 heldout_combined_r2 expected >= 0.92, "
        f"got {data['metrics']['heldout_combined_r2']}"
    )
    assert data['metrics']['sign_agreement'] >= 0.99, (
        f"Phase 157 sign_agreement expected >= 0.99, "
        f"got {data['metrics']['sign_agreement']}"
    )
    assert data['benchmark'] == 'AC_hidden_dropout_batching', (
        f"Unexpected benchmark: {data['benchmark']!r}"
    )


@pytest.mark.unit
def test_phase157_loader_importable() -> None:
    """phase157_analysis module must be importable and expose run_phase157_analysis."""
    mod = importlib.import_module('cwt.cgt.analysis.phase157_analysis')
    assert hasattr(mod, 'run_phase157_analysis'), (
        "phase157_analysis missing 'run_phase157_analysis'"
    )


@pytest.mark.unit
def test_phase157_loader_runs(tmp_path: Path) -> None:
    """run_phase157_analysis must return a non-empty dict."""
    from cwt.cgt.analysis.phase157_analysis import run_phase157_analysis

    payload = run_phase157_analysis(project_root=_PROJECT_ROOT, output_root=tmp_path)
    assert isinstance(payload, dict), 'run_phase157_analysis must return a dict'
    assert payload, 'run_phase157_analysis returned empty dict'
    assert payload['metrics']['heldout_combined_r2'] >= 0.92


# ===========================================================================
# Phase 160 — Third less-synthetic pilot (benchmark CC delayed release)
# ===========================================================================


@pytest.mark.unit
def test_phase160_artifact_exists() -> None:
    """Phase 160 artifact must exist on disk."""
    assert _P160.exists(), f"Missing: {_P160}"


@pytest.mark.unit
def test_phase160_artifact_json_valid() -> None:
    """Phase 160 artifact must be valid JSON."""
    assert _P160.exists(), f"Missing: {_P160}"
    data = json.loads(_P160.read_text(encoding='utf-8'))
    assert isinstance(data, dict), "Phase 160 artifact root must be a dict"


@pytest.mark.unit
def test_phase160_artifact_structure() -> None:
    """Phase 160 artifact must contain required top-level keys."""
    data = json.loads(_P160.read_text(encoding='utf-8'))
    for key in ('phase', 'benchmark', 'metrics'):
        assert key in data, f"Phase 160 artifact missing key: {key!r}"
    for subkey in ('heldout_combined_r2', 'sign_agreement'):
        assert subkey in data['metrics'], f"Phase 160 metrics missing key: {subkey!r}"


@pytest.mark.unit
def test_phase160_metric_thresholds() -> None:
    """Phase 160 less-synthetic positive R2 >= 0.88; sign_agreement >= 0.99.

    Report: switch-slice held-out combined R2 = 0.8819; sign_agreement = 1.0.
    """
    data = json.loads(_P160.read_text(encoding='utf-8'))
    assert data['metrics']['heldout_combined_r2'] >= 0.88, (
        f"Phase 160 heldout_combined_r2 expected >= 0.88, "
        f"got {data['metrics']['heldout_combined_r2']}"
    )
    assert data['metrics']['sign_agreement'] >= 0.99, (
        f"Phase 160 sign_agreement expected >= 0.99, "
        f"got {data['metrics']['sign_agreement']}"
    )
    assert data['benchmark'] == 'CC_delayed_release', (
        f"Unexpected benchmark: {data['benchmark']!r}"
    )


@pytest.mark.unit
def test_phase160_loader_importable() -> None:
    """phase160_analysis module must be importable and expose run_phase160_analysis."""
    mod = importlib.import_module('cwt.cgt.analysis.phase160_analysis')
    assert hasattr(mod, 'run_phase160_analysis'), (
        "phase160_analysis missing 'run_phase160_analysis'"
    )


@pytest.mark.unit
def test_phase160_loader_runs(tmp_path: Path) -> None:
    """run_phase160_analysis must return a non-empty dict."""
    from cwt.cgt.analysis.phase160_analysis import run_phase160_analysis

    payload = run_phase160_analysis(project_root=_PROJECT_ROOT, output_root=tmp_path)
    assert isinstance(payload, dict), 'run_phase160_analysis must return a dict'
    assert payload, 'run_phase160_analysis returned empty dict'
    assert payload['metrics']['heldout_combined_r2'] >= 0.88


# ===========================================================================
# Phase 164 — Pooled nine-bridge positive summary (benchmark scaffold family)
# ===========================================================================


@pytest.mark.unit
def test_phase164_artifact_exists() -> None:
    """Phase 164 artifact must exist on disk."""
    assert _P164.exists(), f"Missing: {_P164}"


@pytest.mark.unit
def test_phase164_artifact_json_valid() -> None:
    """Phase 164 artifact must be valid JSON."""
    assert _P164.exists(), f"Missing: {_P164}"
    data = json.loads(_P164.read_text(encoding='utf-8'))
    assert isinstance(data, dict), "Phase 164 artifact root must be a dict"


@pytest.mark.unit
def test_phase164_artifact_structure() -> None:
    """Phase 164 artifact must contain required top-level keys."""
    data = json.loads(_P164.read_text(encoding='utf-8'))
    for key in ('phase', 'rule', 'benchmarks', 'metrics'):
        assert key in data, f"Phase 164 artifact missing key: {key!r}"
    for subkey in ('combined_r2', 'sign_agreement'):
        assert subkey in data['metrics'], f"Phase 164 metrics missing key: {subkey!r}"
    assert len(data['benchmarks']) == 9, (
        f"Phase 164 expected 9 benchmarks, got {len(data['benchmarks'])}"
    )


@pytest.mark.unit
def test_phase164_metric_thresholds() -> None:
    """Phase 164 pooled nine-bridge positive R2 >= 0.93; sign_agreement >= 0.99.

    Report: pooled-nine positive combined R2 = 0.9374; sign_agreement = 0.9951.
    """
    data = json.loads(_P164.read_text(encoding='utf-8'))
    assert data['metrics']['combined_r2'] >= 0.93, (
        f"Phase 164 combined_r2 expected >= 0.93, "
        f"got {data['metrics']['combined_r2']}"
    )
    assert data['metrics']['sign_agreement'] >= 0.99, (
        f"Phase 164 sign_agreement expected >= 0.99, "
        f"got {data['metrics']['sign_agreement']}"
    )
    assert data['rule'] == 'pooled_nine_bridge_positive', (
        f"Unexpected rule: {data['rule']!r}"
    )


@pytest.mark.unit
def test_phase164_loader_importable() -> None:
    """phase164_analysis module must be importable and expose run_phase164_analysis."""
    mod = importlib.import_module('cwt.cgt.analysis.phase164_analysis')
    assert hasattr(mod, 'run_phase164_analysis'), (
        "phase164_analysis missing 'run_phase164_analysis'"
    )


@pytest.mark.unit
def test_phase164_loader_runs(tmp_path: Path) -> None:
    """run_phase164_analysis must return a non-empty dict."""
    from cwt.cgt.analysis.phase164_analysis import run_phase164_analysis

    payload = run_phase164_analysis(project_root=_PROJECT_ROOT, output_root=tmp_path)
    assert isinstance(payload, dict), 'run_phase164_analysis must return a dict'
    assert payload, 'run_phase164_analysis returned empty dict'
    assert payload['metrics']['combined_r2'] >= 0.93


# ===========================================================================
# Phase 167 — Tenth bridge positive (benchmark AD bursty censor)
# ===========================================================================


@pytest.mark.unit
def test_phase167_artifact_exists() -> None:
    """Phase 167 artifact must exist on disk."""
    assert _P167.exists(), f"Missing: {_P167}"


@pytest.mark.unit
def test_phase167_artifact_json_valid() -> None:
    """Phase 167 artifact must be valid JSON."""
    assert _P167.exists(), f"Missing: {_P167}"
    data = json.loads(_P167.read_text(encoding='utf-8'))
    assert isinstance(data, dict), "Phase 167 artifact root must be a dict"


@pytest.mark.unit
def test_phase167_artifact_structure() -> None:
    """Phase 167 artifact must contain required top-level keys."""
    data = json.loads(_P167.read_text(encoding='utf-8'))
    for key in ('phase', 'benchmark', 'metrics'):
        assert key in data, f"Phase 167 artifact missing key: {key!r}"
    for subkey in ('r2', 'sign'):
        assert subkey in data['metrics'], f"Phase 167 metrics missing key: {subkey!r}"


@pytest.mark.unit
def test_phase167_metric_thresholds() -> None:
    """Phase 167 metrics must meet tenth-bridge acceptance bounds.

    Report: switch-slice held-out combined R2 = 0.9226; sign_agreement = 1.0.
    """
    data = json.loads(_P167.read_text(encoding='utf-8'))
    assert data['metrics']['r2'] >= 0.92, (
        f"Phase 167 r2 expected >= 0.92, "
        f"got {data['metrics']['r2']}"
    )
    assert data['metrics']['sign'] >= 0.99, (
        f"Phase 167 sign expected >= 0.99, "
        f"got {data['metrics']['sign']}"
    )
    assert data['benchmark'] == 'AD_bursty_censor', (
        f"Unexpected benchmark: {data['benchmark']!r}"
    )


@pytest.mark.unit
def test_phase167_loader_importable() -> None:
    """phase167_analysis module must be importable and expose run_phase167_analysis."""
    mod = importlib.import_module('cwt.cgt.analysis.phase167_analysis')
    assert hasattr(mod, 'run_phase167_analysis'), (
        "phase167_analysis missing 'run_phase167_analysis'"
    )


@pytest.mark.unit
def test_phase167_loader_runs(tmp_path: Path) -> None:
    """run_phase167_analysis must return a non-empty dict."""
    from cwt.cgt.analysis.phase167_analysis import run_phase167_analysis

    payload = run_phase167_analysis(project_root=_PROJECT_ROOT, output_root=tmp_path)
    assert isinstance(payload, dict), 'run_phase167_analysis must return a dict'
    assert payload, 'run_phase167_analysis returned empty dict'
    assert payload['metrics']['r2'] >= 0.92


# ===========================================================================
# Phase 169 — Pooled ten-bridge positive summary (benchmark scaffold family)
# ===========================================================================


@pytest.mark.unit
def test_phase169_artifact_exists() -> None:
    """Phase 169 artifact must exist on disk."""
    assert _P169.exists(), f"Missing: {_P169}"


@pytest.mark.unit
def test_phase169_artifact_json_valid() -> None:
    """Phase 169 artifact must be valid JSON."""
    assert _P169.exists(), f"Missing: {_P169}"
    data = json.loads(_P169.read_text(encoding='utf-8'))
    assert isinstance(data, dict), "Phase 169 artifact root must be a dict"


@pytest.mark.unit
def test_phase169_artifact_structure() -> None:
    """Phase 169 artifact must contain required top-level keys."""
    data = json.loads(_P169.read_text(encoding='utf-8'))
    for key in ('phase', 'rule', 'benchmarks', 'metrics'):
        assert key in data, f"Phase 169 artifact missing key: {key!r}"
    for subkey in ('r2', 'sign'):
        assert subkey in data['metrics'], f"Phase 169 metrics missing key: {subkey!r}"
    assert len(data['benchmarks']) == 10, (
        f"Phase 169 expected 10 benchmarks, got {len(data['benchmarks'])}"
    )


@pytest.mark.unit
def test_phase169_metric_thresholds() -> None:
    """Phase 169 pooled ten-bridge positive R2 >= 0.93; sign >= 0.99.

    Report: pooled-ten positive combined R2 = 0.9386; sign_agreement = 0.9956.
    """
    data = json.loads(_P169.read_text(encoding='utf-8'))
    assert data['metrics']['r2'] >= 0.93, (
        f"Phase 169 r2 expected >= 0.93, "
        f"got {data['metrics']['r2']}"
    )
    assert data['metrics']['sign'] >= 0.99, (
        f"Phase 169 sign expected >= 0.99, "
        f"got {data['metrics']['sign']}"
    )
    assert data['rule'] == 'pooled_ten_bridge_positive', (
        f"Unexpected rule: {data['rule']!r}"
    )


@pytest.mark.unit
def test_phase169_loader_importable() -> None:
    """phase169_analysis module must be importable and expose run_phase169_analysis."""
    mod = importlib.import_module('cwt.cgt.analysis.phase169_analysis')
    assert hasattr(mod, 'run_phase169_analysis'), (
        "phase169_analysis missing 'run_phase169_analysis'"
    )


@pytest.mark.unit
def test_phase169_loader_runs(tmp_path: Path) -> None:
    """run_phase169_analysis must return a non-empty dict."""
    from cwt.cgt.analysis.phase169_analysis import run_phase169_analysis

    payload = run_phase169_analysis(project_root=_PROJECT_ROOT, output_root=tmp_path)
    assert isinstance(payload, dict), 'run_phase169_analysis must return a dict'
    assert payload, 'run_phase169_analysis returned empty dict'
    assert payload['metrics']['r2'] >= 0.93


# ===========================================================================
# Phase 170 — Pooled ten-bridge adversarial summary (benchmark scaffold family)
# ===========================================================================


@pytest.mark.unit
def test_phase170_artifact_exists() -> None:
    """Phase 170 artifact must exist on disk."""
    assert _P170.exists(), f"Missing: {_P170}"


@pytest.mark.unit
def test_phase170_artifact_json_valid() -> None:
    """Phase 170 artifact must be valid JSON."""
    assert _P170.exists(), f"Missing: {_P170}"
    data = json.loads(_P170.read_text(encoding='utf-8'))
    assert isinstance(data, dict), "Phase 170 artifact root must be a dict"


@pytest.mark.unit
def test_phase170_artifact_structure() -> None:
    """Phase 170 artifact must contain required top-level keys."""
    data = json.loads(_P170.read_text(encoding='utf-8'))
    for key in ('phase', 'rule', 'raw', 'corrected'):
        assert key in data, f"Phase 170 artifact missing key: {key!r}"
    for subkey in ('combined_r2',):
        assert subkey in data['raw'], f"Phase 170 raw missing key: {subkey!r}"
    for subkey in ('combined_r2', 'sign_agreement'):
        assert subkey in data['corrected'], f"Phase 170 corrected missing key: {subkey!r}"


@pytest.mark.unit
def test_phase170_metric_thresholds() -> None:
    """Phase 170 pooled ten-bridge adversarial: raw degrades, corrected recovers.

    Report: raw combined_r2 = 0.5667; corrected combined_r2 = 0.9104;
    corrected sign_agreement = 0.9742.
    """
    data = json.loads(_P170.read_text(encoding='utf-8'))
    assert data['raw']['combined_r2'] < 0.62, (
        f"Phase 170 raw combined_r2 expected < 0.62 (adversarial degrades), "
        f"got {data['raw']['combined_r2']}"
    )
    assert data['corrected']['combined_r2'] >= 0.91, (
        f"Phase 170 corrected combined_r2 expected >= 0.91, "
        f"got {data['corrected']['combined_r2']}"
    )
    assert data['corrected']['sign_agreement'] >= 0.97, (
        f"Phase 170 corrected sign_agreement expected >= 0.97, "
        f"got {data['corrected']['sign_agreement']}"
    )
    assert data['rule'] == 'pooled_ten_bridge_adversarial', (
        f"Unexpected rule: {data['rule']!r}"
    )


@pytest.mark.unit
def test_phase170_loader_importable() -> None:
    """phase170_analysis module must be importable and expose run_phase170_analysis."""
    mod = importlib.import_module('cwt.cgt.analysis.phase170_analysis')
    assert hasattr(mod, 'run_phase170_analysis'), (
        "phase170_analysis missing 'run_phase170_analysis'"
    )


@pytest.mark.unit
def test_phase170_loader_runs(tmp_path: Path) -> None:
    """run_phase170_analysis must return a non-empty dict."""
    from cwt.cgt.analysis.phase170_analysis import run_phase170_analysis

    payload = run_phase170_analysis(project_root=_PROJECT_ROOT, output_root=tmp_path)
    assert isinstance(payload, dict), 'run_phase170_analysis must return a dict'
    assert payload, 'run_phase170_analysis returned empty dict'
    assert payload['corrected']['combined_r2'] >= 0.91


# ===========================================================================
# Phase 171 — Fourth less-synthetic pilot (benchmark DD async masked)
# ===========================================================================


@pytest.mark.unit
def test_phase171_artifact_exists() -> None:
    """Phase 171 artifact must exist on disk."""
    assert _P171.exists(), f"Missing: {_P171}"


@pytest.mark.unit
def test_phase171_artifact_json_valid() -> None:
    """Phase 171 artifact must be valid JSON."""
    assert _P171.exists(), f"Missing: {_P171}"
    data = json.loads(_P171.read_text(encoding='utf-8'))
    assert isinstance(data, dict), "Phase 171 artifact root must be a dict"


@pytest.mark.unit
def test_phase171_artifact_structure() -> None:
    """Phase 171 artifact must contain required top-level keys."""
    data = json.loads(_P171.read_text(encoding='utf-8'))
    for key in ('phase', 'benchmark', 'metrics'):
        assert key in data, f"Phase 171 artifact missing key: {key!r}"
    for subkey in ('r2', 'sign'):
        assert subkey in data['metrics'], f"Phase 171 metrics missing key: {subkey!r}"


@pytest.mark.unit
def test_phase171_metric_thresholds() -> None:
    """Phase 171 fourth less-synthetic positive R2 >= 0.88; sign >= 0.99.

    Report: held-out combined R2 = 0.8875; sign_agreement = 1.0.
    """
    data = json.loads(_P171.read_text(encoding='utf-8'))
    assert data['metrics']['r2'] >= 0.88, (
        f"Phase 171 r2 expected >= 0.88, "
        f"got {data['metrics']['r2']}"
    )
    assert data['metrics']['sign'] >= 0.99, (
        f"Phase 171 sign expected >= 0.99, "
        f"got {data['metrics']['sign']}"
    )
    assert data['benchmark'] == 'DD_async_masked', (
        f"Unexpected benchmark: {data['benchmark']!r}"
    )


@pytest.mark.unit
def test_phase171_loader_importable() -> None:
    """phase171_analysis module must be importable and expose run_phase171_analysis."""
    mod = importlib.import_module('cwt.cgt.analysis.phase171_analysis')
    assert hasattr(mod, 'run_phase171_analysis'), (
        "phase171_analysis missing 'run_phase171_analysis'"
    )


@pytest.mark.unit
def test_phase171_loader_runs(tmp_path: Path) -> None:
    """run_phase171_analysis must return a non-empty dict."""
    from cwt.cgt.analysis.phase171_analysis import run_phase171_analysis

    payload = run_phase171_analysis(project_root=_PROJECT_ROOT, output_root=tmp_path)
    assert isinstance(payload, dict), 'run_phase171_analysis must return a dict'
    assert payload, 'run_phase171_analysis returned empty dict'
    assert payload['metrics']['r2'] >= 0.88


# ===========================================================================
# Phase 175 — Bridge tensor geometry law v2 (benchmark scaffold family)
# ===========================================================================


@pytest.mark.unit
def test_phase175_artifact_exists() -> None:
    """Phase 175 artifact must exist on disk."""
    assert _P175.exists(), f"Missing: {_P175}"


@pytest.mark.unit
def test_phase175_artifact_json_valid() -> None:
    """Phase 175 artifact must be valid JSON."""
    assert _P175.exists(), f"Missing: {_P175}"
    data = json.loads(_P175.read_text(encoding='utf-8'))
    assert isinstance(data, dict), "Phase 175 artifact root must be a dict"


@pytest.mark.unit
def test_phase175_artifact_structure() -> None:
    """Phase 175 artifact must contain required top-level keys."""
    data = json.loads(_P175.read_text(encoding='utf-8'))
    for key in ('phase', 'candidate', 'raw', 'prior_corrected', 'corrected'):
        assert key in data, f"Phase 175 artifact missing key: {key!r}"
    for subkey in ('combined_r2',):
        assert subkey in data['raw'], f"Phase 175 raw missing key: {subkey!r}"
    for subkey in ('combined_r2',):
        assert subkey in data['prior_corrected'], (
            f"Phase 175 prior_corrected missing key: {subkey!r}"
        )
    for subkey in ('combined_r2', 'sign_agreement'):
        assert subkey in data['corrected'], f"Phase 175 corrected missing key: {subkey!r}"


@pytest.mark.unit
def test_phase175_metric_thresholds() -> None:
    """Phase 175 tensor geometry law v2 must improve over prior corrected.

    Report: raw combined_r2 = 0.5667; prior_corrected combined_r2 = 0.9104;
    corrected combined_r2 = 0.9152; corrected sign_agreement = 0.9751.
    """
    data = json.loads(_P175.read_text(encoding='utf-8'))
    assert data['raw']['combined_r2'] < 0.62, (
        f"Phase 175 raw combined_r2 expected < 0.62 (adversarial degrades), "
        f"got {data['raw']['combined_r2']}"
    )
    assert (
        data['corrected']['combined_r2'] > data['prior_corrected']['combined_r2']
    ), "Phase 175 v2 corrected must exceed prior_corrected"
    assert data['corrected']['combined_r2'] >= 0.91, (
        f"Phase 175 corrected combined_r2 expected >= 0.91, "
        f"got {data['corrected']['combined_r2']}"
    )
    assert data['corrected']['sign_agreement'] >= 0.97, (
        f"Phase 175 corrected sign_agreement expected >= 0.97, "
        f"got {data['corrected']['sign_agreement']}"
    )
    assert data['candidate'] == 'bridge_tensor_geometry_law_v2', (
        f"Unexpected candidate: {data['candidate']!r}"
    )


@pytest.mark.unit
def test_phase175_loader_importable() -> None:
    """phase175_analysis module must be importable and expose run_phase175_analysis."""
    mod = importlib.import_module('cwt.cgt.analysis.phase175_analysis')
    assert hasattr(mod, 'run_phase175_analysis'), (
        "phase175_analysis missing 'run_phase175_analysis'"
    )


@pytest.mark.unit
def test_phase175_loader_runs(tmp_path: Path) -> None:
    """run_phase175_analysis must return a non-empty dict."""
    from cwt.cgt.analysis.phase175_analysis import run_phase175_analysis

    payload = run_phase175_analysis(project_root=_PROJECT_ROOT, output_root=tmp_path)
    assert isinstance(payload, dict), 'run_phase175_analysis must return a dict'
    assert payload, 'run_phase175_analysis returned empty dict'
    assert payload['corrected']['combined_r2'] >= 0.91


# ===========================================================================
# Phase 158 — Bridge family adversarial with AC (benchmark scaffold family)
# ===========================================================================


@pytest.mark.unit
def test_phase158_artifact_exists() -> None:
    """Phase 158 artifact must exist on disk."""
    assert _P158.exists(), f"Missing: {_P158}"


@pytest.mark.unit
def test_phase158_artifact_json_valid() -> None:
    """Phase 158 artifact must be valid JSON."""
    assert _P158.exists(), f"Missing: {_P158}"
    data = json.loads(_P158.read_text(encoding='utf-8'))
    assert isinstance(data, dict), "Phase 158 artifact root must be a dict"


@pytest.mark.unit
def test_phase158_artifact_structure() -> None:
    """Phase 158 artifact must contain required top-level keys."""
    data = json.loads(_P158.read_text(encoding='utf-8'))
    for key in ('phase', 'summary', 'raw', 'corrected'):
        assert key in data, f"Phase 158 artifact missing key: {key!r}"
    for subkey in ('combined_r2', 'sign_agreement'):
        assert subkey in data['corrected'], f"Phase 158 corrected missing key: {subkey!r}"


@pytest.mark.unit
def test_phase158_metric_thresholds() -> None:
    """Phase 158 adversarial: raw degrades, corrected recovers >= 0.90.

    Report: raw combined_r2 = 0.5588; corrected combined_r2 = 0.9047;
    corrected sign_agreement = 0.9724.
    """
    data = json.loads(_P158.read_text(encoding='utf-8'))
    assert data['raw']['combined_r2'] < 0.62, (
        f"Phase 158 raw combined_r2 expected < 0.62 (adversarial degrades), "
        f"got {data['raw']['combined_r2']}"
    )
    assert data['corrected']['combined_r2'] >= 0.90, (
        f"Phase 158 corrected combined_r2 expected >= 0.90, "
        f"got {data['corrected']['combined_r2']}"
    )
    assert data['corrected']['sign_agreement'] >= 0.97, (
        f"Phase 158 corrected sign_agreement expected >= 0.97, "
        f"got {data['corrected']['sign_agreement']}"
    )
    assert data['summary'] == 'bridge_family_adversarial_with_ac', (
        f"Unexpected summary: {data['summary']!r}"
    )


@pytest.mark.unit
def test_phase158_loader_importable() -> None:
    """phase158_analysis module must be importable and expose run_phase158_analysis."""
    mod = importlib.import_module('cwt.cgt.analysis.phase158_analysis')
    assert hasattr(mod, 'run_phase158_analysis'), (
        "phase158_analysis missing 'run_phase158_analysis'"
    )


@pytest.mark.unit
def test_phase158_loader_runs(tmp_path: Path) -> None:
    """run_phase158_analysis must return a non-empty dict."""
    from cwt.cgt.analysis.phase158_analysis import run_phase158_analysis

    payload = run_phase158_analysis(project_root=_PROJECT_ROOT, output_root=tmp_path)
    assert isinstance(payload, dict), 'run_phase158_analysis must return a dict'
    assert payload, 'run_phase158_analysis returned empty dict'
    assert payload['corrected']['combined_r2'] >= 0.90


# ===========================================================================
# Phase 159 — Bridge holdout rule comparison (benchmark scaffold family)
# ===========================================================================


@pytest.mark.unit
def test_phase159_artifact_exists() -> None:
    """Phase 159 artifact must exist on disk."""
    assert _P159.exists(), f"Missing: {_P159}"


@pytest.mark.unit
def test_phase159_artifact_json_valid() -> None:
    """Phase 159 artifact must be valid JSON."""
    assert _P159.exists(), f"Missing: {_P159}"
    data = json.loads(_P159.read_text(encoding='utf-8'))
    assert isinstance(data, dict), "Phase 159 artifact root must be a dict"


@pytest.mark.unit
def test_phase159_artifact_structure() -> None:
    """Phase 159 artifact must contain required top-level keys."""
    data = json.loads(_P159.read_text(encoding='utf-8'))
    for key in ('phase', 'comparison', 'minimal', 'tensor', 'benchmarks'):
        assert key in data, f"Phase 159 artifact missing key: {key!r}"
    for subkey in ('mean_holdout_r2', 'mean_sign_agreement'):
        assert subkey in data['tensor'], f"Phase 159 tensor missing key: {subkey!r}"


@pytest.mark.unit
def test_phase159_metric_thresholds() -> None:
    """Phase 159 tensor rule must outperform minimal on holdout R2 and sign.

    Report: tensor mean_holdout_r2 = 0.8898 vs. minimal 0.8749;
    tensor mean_sign_agreement = 0.9691 vs. minimal 0.9562.
    """
    data = json.loads(_P159.read_text(encoding='utf-8'))
    assert data['tensor']['mean_holdout_r2'] > data['minimal']['mean_holdout_r2'], (
        "Phase 159 tensor mean_holdout_r2 must exceed minimal"
    )
    assert data['tensor']['mean_holdout_r2'] >= 0.88, (
        f"Phase 159 tensor mean_holdout_r2 expected >= 0.88, "
        f"got {data['tensor']['mean_holdout_r2']}"
    )
    assert data['tensor']['mean_sign_agreement'] >= 0.96, (
        f"Phase 159 tensor mean_sign_agreement expected >= 0.96, "
        f"got {data['tensor']['mean_sign_agreement']}"
    )
    assert len(data['benchmarks']) == 11, (
        f"Phase 159 expected 11 benchmarks, got {len(data['benchmarks'])}"
    )


@pytest.mark.unit
def test_phase159_loader_importable() -> None:
    """phase159_analysis module must be importable and expose run_phase159_analysis."""
    mod = importlib.import_module('cwt.cgt.analysis.phase159_analysis')
    assert hasattr(mod, 'run_phase159_analysis'), (
        "phase159_analysis missing 'run_phase159_analysis'"
    )


@pytest.mark.unit
def test_phase159_loader_runs(tmp_path: Path) -> None:
    """run_phase159_analysis must return a non-empty dict."""
    from cwt.cgt.analysis.phase159_analysis import run_phase159_analysis

    payload = run_phase159_analysis(project_root=_PROJECT_ROOT, output_root=tmp_path)
    assert isinstance(payload, dict), 'run_phase159_analysis must return a dict'
    assert payload, 'run_phase159_analysis returned empty dict'
    assert payload['tensor']['mean_holdout_r2'] >= 0.88


# ===========================================================================
# Phase 161 — Third less-synthetic adversarial (benchmark CC delayed release)
# ===========================================================================


@pytest.mark.unit
def test_phase161_artifact_exists() -> None:
    """Phase 161 artifact must exist on disk."""
    assert _P161.exists(), f"Missing: {_P161}"


@pytest.mark.unit
def test_phase161_artifact_json_valid() -> None:
    """Phase 161 artifact must be valid JSON."""
    assert _P161.exists(), f"Missing: {_P161}"
    data = json.loads(_P161.read_text(encoding='utf-8'))
    assert isinstance(data, dict), "Phase 161 artifact root must be a dict"


@pytest.mark.unit
def test_phase161_artifact_structure() -> None:
    """Phase 161 artifact must contain required top-level keys."""
    data = json.loads(_P161.read_text(encoding='utf-8'))
    for key in ('phase', 'benchmark', 'raw', 'corrected'):
        assert key in data, f"Phase 161 artifact missing key: {key!r}"
    for subkey in ('combined_r2', 'sign_agreement'):
        assert subkey in data['corrected'], f"Phase 161 corrected missing key: {subkey!r}"


@pytest.mark.unit
def test_phase161_metric_thresholds() -> None:
    """Phase 161 adversarial: raw degrades severely, corrected recovers.

    Report: raw combined_r2 = 0.4176; corrected combined_r2 = 0.8235;
    corrected sign_agreement = 0.9583.
    """
    data = json.loads(_P161.read_text(encoding='utf-8'))
    assert data['raw']['combined_r2'] < 0.45, (
        f"Phase 161 raw combined_r2 expected < 0.45 (adversarial degrades), "
        f"got {data['raw']['combined_r2']}"
    )
    assert data['corrected']['combined_r2'] >= 0.82, (
        f"Phase 161 corrected combined_r2 expected >= 0.82, "
        f"got {data['corrected']['combined_r2']}"
    )
    assert data['corrected']['sign_agreement'] >= 0.95, (
        f"Phase 161 corrected sign_agreement expected >= 0.95, "
        f"got {data['corrected']['sign_agreement']}"
    )
    assert data['benchmark'] == 'CC_delayed_release', (
        f"Unexpected benchmark: {data['benchmark']!r}"
    )


@pytest.mark.unit
def test_phase161_loader_importable() -> None:
    """phase161_analysis module must be importable and expose run_phase161_analysis."""
    mod = importlib.import_module('cwt.cgt.analysis.phase161_analysis')
    assert hasattr(mod, 'run_phase161_analysis'), (
        "phase161_analysis missing 'run_phase161_analysis'"
    )


@pytest.mark.unit
def test_phase161_loader_runs(tmp_path: Path) -> None:
    """run_phase161_analysis must return a non-empty dict."""
    from cwt.cgt.analysis.phase161_analysis import run_phase161_analysis

    payload = run_phase161_analysis(project_root=_PROJECT_ROOT, output_root=tmp_path)
    assert isinstance(payload, dict), 'run_phase161_analysis must return a dict'
    assert payload, 'run_phase161_analysis returned empty dict'
    assert payload['corrected']['combined_r2'] >= 0.82


# ===========================================================================
# Phase 162 — Bridge LOO all-pilots audit (benchmark scaffold family)
# ===========================================================================


@pytest.mark.unit
def test_phase162_artifact_exists() -> None:
    """Phase 162 artifact must exist on disk."""
    assert _P162.exists(), f"Missing: {_P162}"


@pytest.mark.unit
def test_phase162_artifact_json_valid() -> None:
    """Phase 162 artifact must be valid JSON."""
    assert _P162.exists(), f"Missing: {_P162}"
    data = json.loads(_P162.read_text(encoding='utf-8'))
    assert isinstance(data, dict), "Phase 162 artifact root must be a dict"


@pytest.mark.unit
def test_phase162_artifact_structure() -> None:
    """Phase 162 artifact must contain required top-level keys."""
    data = json.loads(_P162.read_text(encoding='utf-8'))
    for key in ('phase', 'audit', 'mean_holdout_r2', 'weakest_benchmark',
                'weakest_r2', 'included_pilots'):
        assert key in data, f"Phase 162 artifact missing key: {key!r}"
    assert len(data['included_pilots']) == 3, (
        f"Phase 162 expected 3 included_pilots, got {len(data['included_pilots'])}"
    )


@pytest.mark.unit
def test_phase162_metric_thresholds() -> None:
    """Phase 162 LOO audit: mean holdout R2 >= 0.88, weakest >= 0.87.

    Report: mean_holdout_r2 = 0.8864; weakest BB_sensor_gap r2 = 0.8748.
    """
    data = json.loads(_P162.read_text(encoding='utf-8'))
    assert data['mean_holdout_r2'] >= 0.88, (
        f"Phase 162 mean_holdout_r2 expected >= 0.88, "
        f"got {data['mean_holdout_r2']}"
    )
    assert data['weakest_r2'] >= 0.87, (
        f"Phase 162 weakest_r2 expected >= 0.87, "
        f"got {data['weakest_r2']}"
    )
    assert data['audit'] == 'bridge_loo_all_pilots', (
        f"Unexpected audit: {data['audit']!r}"
    )


@pytest.mark.unit
def test_phase162_loader_importable() -> None:
    """phase162_analysis module must be importable and expose run_phase162_analysis."""
    mod = importlib.import_module('cwt.cgt.analysis.phase162_analysis')
    assert hasattr(mod, 'run_phase162_analysis'), (
        "phase162_analysis missing 'run_phase162_analysis'"
    )


@pytest.mark.unit
def test_phase162_loader_runs(tmp_path: Path) -> None:
    """run_phase162_analysis must return a non-empty dict."""
    from cwt.cgt.analysis.phase162_analysis import run_phase162_analysis

    payload = run_phase162_analysis(project_root=_PROJECT_ROOT, output_root=tmp_path)
    assert isinstance(payload, dict), 'run_phase162_analysis must return a dict'
    assert payload, 'run_phase162_analysis returned empty dict'
    assert payload['mean_holdout_r2'] >= 0.88


# ===========================================================================
# Phase 163 — Bridge tensor geometry law v1 (benchmark scaffold family)
# ===========================================================================


@pytest.mark.unit
def test_phase163_artifact_exists() -> None:
    """Phase 163 artifact must exist on disk."""
    assert _P163.exists(), f"Missing: {_P163}"


@pytest.mark.unit
def test_phase163_artifact_json_valid() -> None:
    """Phase 163 artifact must be valid JSON."""
    assert _P163.exists(), f"Missing: {_P163}"
    data = json.loads(_P163.read_text(encoding='utf-8'))
    assert isinstance(data, dict), "Phase 163 artifact root must be a dict"


@pytest.mark.unit
def test_phase163_artifact_structure() -> None:
    """Phase 163 artifact must contain required top-level keys."""
    data = json.loads(_P163.read_text(encoding='utf-8'))
    for key in ('phase', 'candidate', 'raw', 'prior_corrected', 'corrected'):
        assert key in data, f"Phase 163 artifact missing key: {key!r}"
    for subkey in ('combined_r2',):
        assert subkey in data['corrected'], f"Phase 163 corrected missing key: {subkey!r}"
    assert 'sign_agreement' in data['corrected'], (
        "Phase 163 corrected missing key: 'sign_agreement'"
    )


@pytest.mark.unit
def test_phase163_metric_thresholds() -> None:
    """Phase 163 tensor geometry law v1 must improve over prior corrected.

    Report: raw combined_r2 = 0.5588; prior_corrected combined_r2 = 0.9047;
    corrected combined_r2 = 0.9126; corrected sign_agreement = 0.9732.
    """
    data = json.loads(_P163.read_text(encoding='utf-8'))
    assert data['raw']['combined_r2'] < 0.62, (
        f"Phase 163 raw combined_r2 expected < 0.62, got {data['raw']['combined_r2']}"
    )
    assert (
        data['corrected']['combined_r2'] > data['prior_corrected']['combined_r2']
    ), "Phase 163 corrected must exceed prior_corrected"
    assert data['corrected']['combined_r2'] >= 0.91, (
        f"Phase 163 corrected combined_r2 expected >= 0.91, "
        f"got {data['corrected']['combined_r2']}"
    )
    assert data['candidate'] == 'bridge_tensor_geometry_law', (
        f"Unexpected candidate: {data['candidate']!r}"
    )


@pytest.mark.unit
def test_phase163_loader_importable() -> None:
    """phase163_analysis module must be importable and expose run_phase163_analysis."""
    mod = importlib.import_module('cwt.cgt.analysis.phase163_analysis')
    assert hasattr(mod, 'run_phase163_analysis'), (
        "phase163_analysis missing 'run_phase163_analysis'"
    )


@pytest.mark.unit
def test_phase163_loader_runs(tmp_path: Path) -> None:
    """run_phase163_analysis must return a non-empty dict."""
    from cwt.cgt.analysis.phase163_analysis import run_phase163_analysis

    payload = run_phase163_analysis(project_root=_PROJECT_ROOT, output_root=tmp_path)
    assert isinstance(payload, dict), 'run_phase163_analysis must return a dict'
    assert payload, 'run_phase163_analysis returned empty dict'
    assert payload['corrected']['combined_r2'] >= 0.91


# ===========================================================================
# Phase 165 — Pooled nine-bridge adversarial (benchmark scaffold family)
# ===========================================================================


@pytest.mark.unit
def test_phase165_artifact_exists() -> None:
    """Phase 165 artifact must exist on disk."""
    assert _P165.exists(), f"Missing: {_P165}"


@pytest.mark.unit
def test_phase165_artifact_json_valid() -> None:
    """Phase 165 artifact must be valid JSON."""
    assert _P165.exists(), f"Missing: {_P165}"
    data = json.loads(_P165.read_text(encoding='utf-8'))
    assert isinstance(data, dict), "Phase 165 artifact root must be a dict"


@pytest.mark.unit
def test_phase165_artifact_structure() -> None:
    """Phase 165 artifact must contain required top-level keys."""
    data = json.loads(_P165.read_text(encoding='utf-8'))
    for key in ('phase', 'rule', 'raw', 'corrected', 'benchmarks'):
        assert key in data, f"Phase 165 artifact missing key: {key!r}"
    for subkey in ('combined_r2', 'sign_agreement'):
        assert subkey in data['corrected'], f"Phase 165 corrected missing key: {subkey!r}"


@pytest.mark.unit
def test_phase165_metric_thresholds() -> None:
    """Phase 165 nine-bridge adversarial: raw degrades, corrected recovers >= 0.90.

    Report: raw combined_r2 = 0.5631; corrected combined_r2 = 0.9079;
    corrected sign_agreement = 0.9738.
    """
    data = json.loads(_P165.read_text(encoding='utf-8'))
    assert data['raw']['combined_r2'] < 0.62, (
        f"Phase 165 raw combined_r2 expected < 0.62, got {data['raw']['combined_r2']}"
    )
    assert data['corrected']['combined_r2'] >= 0.90, (
        f"Phase 165 corrected combined_r2 expected >= 0.90, "
        f"got {data['corrected']['combined_r2']}"
    )
    assert data['corrected']['sign_agreement'] >= 0.97, (
        f"Phase 165 corrected sign_agreement expected >= 0.97, "
        f"got {data['corrected']['sign_agreement']}"
    )
    assert data['rule'] == 'pooled_nine_bridge_adversarial', (
        f"Unexpected rule: {data['rule']!r}"
    )


@pytest.mark.unit
def test_phase165_loader_importable() -> None:
    """phase165_analysis module must be importable and expose run_phase165_analysis."""
    mod = importlib.import_module('cwt.cgt.analysis.phase165_analysis')
    assert hasattr(mod, 'run_phase165_analysis'), (
        "phase165_analysis missing 'run_phase165_analysis'"
    )


@pytest.mark.unit
def test_phase165_loader_runs(tmp_path: Path) -> None:
    """run_phase165_analysis must return a non-empty dict."""
    from cwt.cgt.analysis.phase165_analysis import run_phase165_analysis

    payload = run_phase165_analysis(project_root=_PROJECT_ROOT, output_root=tmp_path)
    assert isinstance(payload, dict), 'run_phase165_analysis must return a dict'
    assert payload, 'run_phase165_analysis returned empty dict'
    assert payload['corrected']['combined_r2'] >= 0.90


# ===========================================================================
# Phase 166 — Bridge boundary refresh v2 (benchmark scaffold family)
# ===========================================================================


@pytest.mark.unit
def test_phase166_artifact_exists() -> None:
    """Phase 166 artifact must exist on disk."""
    assert _P166.exists(), f"Missing: {_P166}"


@pytest.mark.unit
def test_phase166_artifact_json_valid() -> None:
    """Phase 166 artifact must be valid JSON."""
    assert _P166.exists(), f"Missing: {_P166}"
    data = json.loads(_P166.read_text(encoding='utf-8'))
    assert isinstance(data, dict), "Phase 166 artifact root must be a dict"


@pytest.mark.unit
def test_phase166_artifact_structure() -> None:
    """Phase 166 artifact must contain required top-level keys."""
    data = json.loads(_P166.read_text(encoding='utf-8'))
    for key in ('phase', 'summary', 'bands'):
        assert key in data, f"Phase 166 artifact missing key: {key!r}"
    for subkey in ('positive_band', 'adversarial_raw_band', 'adversarial_corrected_band',
                   'weakest_positive'):
        assert subkey in data['bands'], f"Phase 166 bands missing key: {subkey!r}"


@pytest.mark.unit
def test_phase166_metric_thresholds() -> None:
    """Phase 166 v2 boundary bands must be consistent with nine-bridge evidence.

    Report: positive_band = [0.8748, 0.9981]; adv_raw_band = [0.4011, 0.6024];
    adv_corr_band = [0.8235, 0.9126]; weakest = BB_sensor_gap.
    """
    data = json.loads(_P166.read_text(encoding='utf-8'))
    assert data['bands']['positive_band'][0] >= 0.87, (
        f"Phase 166 positive_band lower bound expected >= 0.87, "
        f"got {data['bands']['positive_band'][0]}"
    )
    assert data['bands']['adversarial_corrected_band'][1] >= 0.90, (
        f"Phase 166 adversarial_corrected_band upper bound expected >= 0.90, "
        f"got {data['bands']['adversarial_corrected_band'][1]}"
    )
    assert data['summary'] == 'bridge_boundary_refresh_v2', (
        f"Unexpected summary: {data['summary']!r}"
    )


@pytest.mark.unit
def test_phase166_loader_importable() -> None:
    """phase166_analysis module must be importable and expose run_phase166_analysis."""
    mod = importlib.import_module('cwt.cgt.analysis.phase166_analysis')
    assert hasattr(mod, 'run_phase166_analysis'), (
        "phase166_analysis missing 'run_phase166_analysis'"
    )


@pytest.mark.unit
def test_phase166_loader_runs(tmp_path: Path) -> None:
    """run_phase166_analysis must return a non-empty dict."""
    from cwt.cgt.analysis.phase166_analysis import run_phase166_analysis

    payload = run_phase166_analysis(project_root=_PROJECT_ROOT, output_root=tmp_path)
    assert isinstance(payload, dict), 'run_phase166_analysis must return a dict'
    assert payload, 'run_phase166_analysis returned empty dict'
    assert payload['bands']['positive_band'][0] >= 0.87


# ===========================================================================
# Phase 168 — Tenth bridge adversarial (benchmark AD bursty censor)
# ===========================================================================


@pytest.mark.unit
def test_phase168_artifact_exists() -> None:
    """Phase 168 artifact must exist on disk."""
    assert _P168.exists(), f"Missing: {_P168}"


@pytest.mark.unit
def test_phase168_artifact_json_valid() -> None:
    """Phase 168 artifact must be valid JSON."""
    assert _P168.exists(), f"Missing: {_P168}"
    data = json.loads(_P168.read_text(encoding='utf-8'))
    assert isinstance(data, dict), "Phase 168 artifact root must be a dict"


@pytest.mark.unit
def test_phase168_artifact_structure() -> None:
    """Phase 168 artifact must contain required top-level keys."""
    data = json.loads(_P168.read_text(encoding='utf-8'))
    for key in ('phase', 'benchmark', 'raw', 'corrected'):
        assert key in data, f"Phase 168 artifact missing key: {key!r}"
    for subkey in ('combined_r2', 'sign_agreement'):
        assert subkey in data['corrected'], f"Phase 168 corrected missing key: {subkey!r}"


@pytest.mark.unit
def test_phase168_metric_thresholds() -> None:
    """Phase 168 tenth bridge adversarial: raw degrades, corrected recovers >= 0.89.

    Report: raw combined_r2 = 0.5342; corrected combined_r2 = 0.8998;
    corrected sign_agreement = 0.9694.
    """
    data = json.loads(_P168.read_text(encoding='utf-8'))
    assert data['raw']['combined_r2'] < 0.55, (
        f"Phase 168 raw combined_r2 expected < 0.55 (adversarial degrades), "
        f"got {data['raw']['combined_r2']}"
    )
    assert data['corrected']['combined_r2'] >= 0.89, (
        f"Phase 168 corrected combined_r2 expected >= 0.89, "
        f"got {data['corrected']['combined_r2']}"
    )
    assert data['corrected']['sign_agreement'] >= 0.96, (
        f"Phase 168 corrected sign_agreement expected >= 0.96, "
        f"got {data['corrected']['sign_agreement']}"
    )
    assert data['benchmark'] == 'AD_bursty_censor', (
        f"Unexpected benchmark: {data['benchmark']!r}"
    )


@pytest.mark.unit
def test_phase168_loader_importable() -> None:
    """phase168_analysis module must be importable and expose run_phase168_analysis."""
    mod = importlib.import_module('cwt.cgt.analysis.phase168_analysis')
    assert hasattr(mod, 'run_phase168_analysis'), (
        "phase168_analysis missing 'run_phase168_analysis'"
    )


@pytest.mark.unit
def test_phase168_loader_runs(tmp_path: Path) -> None:
    """run_phase168_analysis must return a non-empty dict."""
    from cwt.cgt.analysis.phase168_analysis import run_phase168_analysis

    payload = run_phase168_analysis(project_root=_PROJECT_ROOT, output_root=tmp_path)
    assert isinstance(payload, dict), 'run_phase168_analysis must return a dict'
    assert payload, 'run_phase168_analysis returned empty dict'
    assert payload['corrected']['combined_r2'] >= 0.89


# ===========================================================================
# Phase 172 — Fourth less-synthetic adversarial (benchmark DD async masked)
# ===========================================================================


@pytest.mark.unit
def test_phase172_artifact_exists() -> None:
    """Phase 172 artifact must exist on disk."""
    assert _P172.exists(), f"Missing: {_P172}"


@pytest.mark.unit
def test_phase172_artifact_json_valid() -> None:
    """Phase 172 artifact must be valid JSON."""
    assert _P172.exists(), f"Missing: {_P172}"
    data = json.loads(_P172.read_text(encoding='utf-8'))
    assert isinstance(data, dict), "Phase 172 artifact root must be a dict"


@pytest.mark.unit
def test_phase172_artifact_structure() -> None:
    """Phase 172 artifact must contain required top-level keys."""
    data = json.loads(_P172.read_text(encoding='utf-8'))
    for key in ('phase', 'benchmark', 'raw', 'corrected'):
        assert key in data, f"Phase 172 artifact missing key: {key!r}"
    for subkey in ('combined_r2', 'sign_agreement'):
        assert subkey in data['corrected'], f"Phase 172 corrected missing key: {subkey!r}"


@pytest.mark.unit
def test_phase172_metric_thresholds() -> None:
    """Phase 172 fourth less-synthetic adversarial: raw degrades, corrected recovers.

    Report: raw combined_r2 = 0.4308; corrected combined_r2 = 0.8297;
    corrected sign_agreement = 0.9604.
    """
    data = json.loads(_P172.read_text(encoding='utf-8'))
    assert data['raw']['combined_r2'] < 0.45, (
        f"Phase 172 raw combined_r2 expected < 0.45 (adversarial degrades), "
        f"got {data['raw']['combined_r2']}"
    )
    assert data['corrected']['combined_r2'] >= 0.82, (
        f"Phase 172 corrected combined_r2 expected >= 0.82, "
        f"got {data['corrected']['combined_r2']}"
    )
    assert data['corrected']['sign_agreement'] >= 0.95, (
        f"Phase 172 corrected sign_agreement expected >= 0.95, "
        f"got {data['corrected']['sign_agreement']}"
    )
    assert data['benchmark'] == 'DD_async_masked', (
        f"Unexpected benchmark: {data['benchmark']!r}"
    )


@pytest.mark.unit
def test_phase172_loader_importable() -> None:
    """phase172_analysis module must be importable and expose run_phase172_analysis."""
    mod = importlib.import_module('cwt.cgt.analysis.phase172_analysis')
    assert hasattr(mod, 'run_phase172_analysis'), (
        "phase172_analysis missing 'run_phase172_analysis'"
    )


@pytest.mark.unit
def test_phase172_loader_runs(tmp_path: Path) -> None:
    """run_phase172_analysis must return a non-empty dict."""
    from cwt.cgt.analysis.phase172_analysis import run_phase172_analysis

    payload = run_phase172_analysis(project_root=_PROJECT_ROOT, output_root=tmp_path)
    assert isinstance(payload, dict), 'run_phase172_analysis must return a dict'
    assert payload, 'run_phase172_analysis returned empty dict'
    assert payload['corrected']['combined_r2'] >= 0.82


# ===========================================================================
# Phase 173 — Bridge LOO expanded pilots audit (benchmark scaffold family)
# ===========================================================================


@pytest.mark.unit
def test_phase173_artifact_exists() -> None:
    """Phase 173 artifact must exist on disk."""
    assert _P173.exists(), f"Missing: {_P173}"


@pytest.mark.unit
def test_phase173_artifact_json_valid() -> None:
    """Phase 173 artifact must be valid JSON."""
    assert _P173.exists(), f"Missing: {_P173}"
    data = json.loads(_P173.read_text(encoding='utf-8'))
    assert isinstance(data, dict), "Phase 173 artifact root must be a dict"


@pytest.mark.unit
def test_phase173_artifact_structure() -> None:
    """Phase 173 artifact must contain required top-level keys."""
    data = json.loads(_P173.read_text(encoding='utf-8'))
    for key in ('phase', 'audit', 'mean_holdout_r2', 'weakest_benchmark',
                'weakest_r2', 'included_pilots'):
        assert key in data, f"Phase 173 artifact missing key: {key!r}"
    assert len(data['included_pilots']) == 4, (
        f"Phase 173 expected 4 included_pilots, got {len(data['included_pilots'])}"
    )


@pytest.mark.unit
def test_phase173_metric_thresholds() -> None:
    """Phase 173 expanded LOO audit: mean holdout R2 >= 0.88, weakest >= 0.87.

    Report: mean_holdout_r2 = 0.8879; weakest BB_sensor_gap r2 = 0.8748.
    """
    data = json.loads(_P173.read_text(encoding='utf-8'))
    assert data['mean_holdout_r2'] >= 0.88, (
        f"Phase 173 mean_holdout_r2 expected >= 0.88, "
        f"got {data['mean_holdout_r2']}"
    )
    assert data['weakest_r2'] >= 0.87, (
        f"Phase 173 weakest_r2 expected >= 0.87, "
        f"got {data['weakest_r2']}"
    )
    assert data['audit'] == 'bridge_loo_all_pilots_expanded', (
        f"Unexpected audit: {data['audit']!r}"
    )


@pytest.mark.unit
def test_phase173_loader_importable() -> None:
    """phase173_analysis module must be importable and expose run_phase173_analysis."""
    mod = importlib.import_module('cwt.cgt.analysis.phase173_analysis')
    assert hasattr(mod, 'run_phase173_analysis'), (
        "phase173_analysis missing 'run_phase173_analysis'"
    )


@pytest.mark.unit
def test_phase173_loader_runs(tmp_path: Path) -> None:
    """run_phase173_analysis must return a non-empty dict."""
    from cwt.cgt.analysis.phase173_analysis import run_phase173_analysis

    payload = run_phase173_analysis(project_root=_PROJECT_ROOT, output_root=tmp_path)
    assert isinstance(payload, dict), 'run_phase173_analysis must return a dict'
    assert payload, 'run_phase173_analysis returned empty dict'
    assert payload['mean_holdout_r2'] >= 0.88


# ===========================================================================
# Phase 174 — Bridge holdout expanded comparison (benchmark scaffold family)
# ===========================================================================


@pytest.mark.unit
def test_phase174_artifact_exists() -> None:
    """Phase 174 artifact must exist on disk."""
    assert _P174.exists(), f"Missing: {_P174}"


@pytest.mark.unit
def test_phase174_artifact_json_valid() -> None:
    """Phase 174 artifact must be valid JSON."""
    assert _P174.exists(), f"Missing: {_P174}"
    data = json.loads(_P174.read_text(encoding='utf-8'))
    assert isinstance(data, dict), "Phase 174 artifact root must be a dict"


@pytest.mark.unit
def test_phase174_artifact_structure() -> None:
    """Phase 174 artifact must contain required top-level keys."""
    data = json.loads(_P174.read_text(encoding='utf-8'))
    for key in ('phase', 'comparison', 'minimal', 'tensor'):
        assert key in data, f"Phase 174 artifact missing key: {key!r}"
    for subkey in ('mean_holdout_r2',):
        assert subkey in data['tensor'], f"Phase 174 tensor missing key: {subkey!r}"
    assert 'mean_holdout_r2' in data['minimal'], (
        "Phase 174 minimal missing key: 'mean_holdout_r2'"
    )


@pytest.mark.unit
def test_phase174_metric_thresholds() -> None:
    """Phase 174 expanded comparison: tensor must exceed minimal holdout R2.

    Report: tensor mean_holdout_r2 = 0.8921 vs. minimal 0.8783.
    """
    data = json.loads(_P174.read_text(encoding='utf-8'))
    assert data['tensor']['mean_holdout_r2'] > data['minimal']['mean_holdout_r2'], (
        "Phase 174 tensor mean_holdout_r2 must exceed minimal"
    )
    assert data['tensor']['mean_holdout_r2'] >= 0.89, (
        f"Phase 174 tensor mean_holdout_r2 expected >= 0.89, "
        f"got {data['tensor']['mean_holdout_r2']}"
    )
    assert data['comparison'] == 'bridge_tensor_vs_minimal_cf_expanded_holdout', (
        f"Unexpected comparison: {data['comparison']!r}"
    )


@pytest.mark.unit
def test_phase174_loader_importable() -> None:
    """phase174_analysis module must be importable and expose run_phase174_analysis."""
    mod = importlib.import_module('cwt.cgt.analysis.phase174_analysis')
    assert hasattr(mod, 'run_phase174_analysis'), (
        "phase174_analysis missing 'run_phase174_analysis'"
    )


@pytest.mark.unit
def test_phase174_loader_runs(tmp_path: Path) -> None:
    """run_phase174_analysis must return a non-empty dict."""
    from cwt.cgt.analysis.phase174_analysis import run_phase174_analysis

    payload = run_phase174_analysis(project_root=_PROJECT_ROOT, output_root=tmp_path)
    assert isinstance(payload, dict), 'run_phase174_analysis must return a dict'
    assert payload, 'run_phase174_analysis returned empty dict'
    assert payload['tensor']['mean_holdout_r2'] >= 0.89


# ===========================================================================
# Phase 176 — Bridge boundary refresh v3 (benchmark scaffold family)
# ===========================================================================


@pytest.mark.unit
def test_phase176_artifact_exists() -> None:
    """Phase 176 artifact must exist on disk."""
    assert _P176.exists(), f"Missing: {_P176}"


@pytest.mark.unit
def test_phase176_artifact_json_valid() -> None:
    """Phase 176 artifact must be valid JSON."""
    assert _P176.exists(), f"Missing: {_P176}"
    data = json.loads(_P176.read_text(encoding='utf-8'))
    assert isinstance(data, dict), "Phase 176 artifact root must be a dict"


@pytest.mark.unit
def test_phase176_artifact_structure() -> None:
    """Phase 176 artifact must contain required top-level keys."""
    data = json.loads(_P176.read_text(encoding='utf-8'))
    for key in ('phase', 'summary', 'bands'):
        assert key in data, f"Phase 176 artifact missing key: {key!r}"
    for subkey in ('positive', 'raw', 'corr', 'weakest'):
        assert subkey in data['bands'], f"Phase 176 bands missing key: {subkey!r}"


@pytest.mark.unit
def test_phase176_metric_thresholds() -> None:
    """Phase 176 v3 boundary bands must reflect expanded ten-bridge evidence.

    Report: positive = [0.8748, 0.9981]; raw = [0.4011, 0.6024];
    corr = [0.8235, 0.9152]; weakest = BB_sensor_gap.
    """
    data = json.loads(_P176.read_text(encoding='utf-8'))
    assert data['bands']['positive'][0] >= 0.87, (
        f"Phase 176 positive lower bound expected >= 0.87, "
        f"got {data['bands']['positive'][0]}"
    )
    assert data['bands']['corr'][1] >= 0.91, (
        f"Phase 176 corr upper bound expected >= 0.91, "
        f"got {data['bands']['corr'][1]}"
    )
    assert data['summary'] == 'bridge_boundary_refresh_v3', (
        f"Unexpected summary: {data['summary']!r}"
    )


@pytest.mark.unit
def test_phase176_loader_importable() -> None:
    """phase176_analysis module must be importable and expose run_phase176_analysis."""
    mod = importlib.import_module('cwt.cgt.analysis.phase176_analysis')
    assert hasattr(mod, 'run_phase176_analysis'), (
        "phase176_analysis missing 'run_phase176_analysis'"
    )


@pytest.mark.unit
def test_phase176_loader_runs(tmp_path: Path) -> None:
    """run_phase176_analysis must return a non-empty dict."""
    from cwt.cgt.analysis.phase176_analysis import run_phase176_analysis

    payload = run_phase176_analysis(project_root=_PROJECT_ROOT, output_root=tmp_path)
    assert isinstance(payload, dict), 'run_phase176_analysis must return a dict'
    assert payload, 'run_phase176_analysis returned empty dict'
    assert payload['bands']['corr'][1] >= 0.91
