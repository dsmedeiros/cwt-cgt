"""Smoke tests for CGT phase 16-39 result artifacts and analysis modules.

Covers:
- Existence and JSON-validity of every phase 16-39 benchmark_c artifact.
- Importability of self-contained analysis modules (phases 16-24, 25-39).
- Structural integrity of the phase 39 artifact (including switch_metrics).
- Schema consistency: common required keys present in all phase 25-39 artifacts.
"""

from __future__ import annotations

import importlib
import json
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_RESULTS_DIR = (
    Path(__file__).resolve().parents[2]
    / "cgt_benchmarks"
    / "results"
    / "benchmark_C_ring"
)

# ---------------------------------------------------------------------------
# Phase -> artifact suffix mapping (phases 16-39)
# ---------------------------------------------------------------------------

PHASE_SUFFIX: list[tuple[int, str]] = [
    (16, "superoperator_field"),
    (17, "frechet_field"),
    (18, "analytic_field"),
    (19, "loop_alignment"),
    (20, "path_order"),
    (21, "heldout_shape_transfer"),
    (22, "generator_moment_transfer"),
    (23, "broader_heldout_transfer"),
    (24, "clean_rerun_higher_order"),
    (25, "moment_derived_higher_order"),
    (26, "generator_normalized_transfer"),
    (27, "moment_normalized_transfer"),
    (28, "generator_geometry_share"),
    (29, "local_superoperator_area"),
    (30, "local_superoperator_anisotropy"),
    (31, "local_superoperator_covariance"),
    (32, "covariance_tensor_baseline"),
    (33, "local_superoperator_geometry_clip"),
    (34, "local_superoperator_moment_width"),
    (35, "local_superoperator_geometry_baseline"),
    (36, "local_superoperator_area_channel"),
    (37, "local_superoperator_compactness"),
    (38, "local_superoperator_compactness_share"),
    (39, "local_superoperator_compactness_normalizer"),
]

# Self-contained analysis modules that can be imported without heavy I/O.
# All phase analysis modules 16-24 and 25-39 are confirmed importable; the
# full set is included here.
IMPORTABLE_PHASES: list[int] = list(range(16, 22)) + [22, 23, 24] + list(range(25, 40))

# Parametrize IDs for readability in test output
_ARTIFACT_IDS = [f"phase{n}_{suffix}" for n, suffix in PHASE_SUFFIX]
_IMPORT_IDS = [f"phase{n}_analysis" for n in IMPORTABLE_PHASES]


# ---------------------------------------------------------------------------
# a) Artifact existence and JSON validity
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.parametrize(
    ("phase_num", "suffix"),
    PHASE_SUFFIX,
    ids=_ARTIFACT_IDS,
)
def test_phase_artifact_exists_and_is_valid_json(phase_num: int, suffix: str) -> None:
    """Each phase 16-39 benchmark_c result artifact must exist and parse as JSON."""
    artifact = _RESULTS_DIR / f"benchmark_c_phase{phase_num}_{suffix}.json"
    assert artifact.exists(), (
        f"Artifact not found: {artifact}\n"
        f"Expected path relative to cwt-sim: "
        f"cgt_benchmarks/results/benchmark_C_ring/{artifact.name}"
    )
    assert artifact.stat().st_size > 0, f"Artifact is empty: {artifact.name}"
    with artifact.open(encoding="utf-8") as fh:
        data = json.load(fh)
    assert isinstance(data, dict), (
        f"Expected a JSON object at top level, got {type(data).__name__}: {artifact.name}"
    )


# ---------------------------------------------------------------------------
# b) Analysis module importability (phases 22, 25-39)
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.parametrize(
    "phase_num",
    IMPORTABLE_PHASES,
    ids=_IMPORT_IDS,
)
def test_phase_analysis_module_importable(phase_num: int) -> None:
    """Each self-contained phase analysis module must be importable without error."""
    module_name = f"cwt.cgt.analysis.phase{phase_num}_analysis"
    mod = importlib.import_module(module_name)
    assert mod is not None, f"Import of {module_name} returned None"


# ---------------------------------------------------------------------------
# c) Phase 39 artifact structural integrity
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_phase39_artifact_structure() -> None:
    """The phase 39 result artifact must contain the required top-level keys."""
    artifact = _RESULTS_DIR / "benchmark_c_phase39_local_superoperator_compactness_normalizer.json"
    assert artifact.exists(), f"Phase 39 artifact not found: {artifact}"

    with artifact.open(encoding="utf-8") as fh:
        data = json.load(fh)

    required_keys = {"phase", "benchmark", "verdict", "switch_metrics"}
    missing = required_keys - data.keys()
    assert not missing, (
        f"Phase 39 artifact missing required keys: {sorted(missing)}\n"
        f"Present keys: {sorted(data.keys())}"
    )

    # The phase field is a descriptive string identifier, not a bare integer.
    assert isinstance(data["phase"], str) and "39" in data["phase"], (
        f"Expected phase string to contain '39', got {data['phase']!r}"
    )
    assert data["benchmark"] == "benchmark_c", (
        f"Expected benchmark='benchmark_c', got {data['benchmark']!r}"
    )
    assert isinstance(data["verdict"], str) and data["verdict"], (
        f"Expected a non-empty string verdict, got {data['verdict']!r}"
    )

    # switch_metrics must contain the four cross-phase R² keys.
    switch_metrics = data["switch_metrics"]
    assert isinstance(switch_metrics, dict), (
        f"Expected switch_metrics to be a dict, got {type(switch_metrics).__name__}"
    )
    required_switch_keys = {
        "phase38_heldout_new_r2",
        "phase39_heldout_new_r2",
        "phase38_heldout_combined_r2",
        "phase39_heldout_combined_r2",
    }
    missing_switch = required_switch_keys - switch_metrics.keys()
    assert not missing_switch, (
        f"switch_metrics missing keys: {sorted(missing_switch)}\n"
        f"Present switch_metrics keys: {sorted(switch_metrics.keys())}"
    )


# ---------------------------------------------------------------------------
# d) Schema consistency across phases 25-39
# ---------------------------------------------------------------------------

_SCHEMA_PHASES: list[tuple[int, str]] = [
    (n, suffix) for n, suffix in PHASE_SUFFIX if n >= 25
]
_SCHEMA_IDS = [f"phase{n}_{suffix}" for n, suffix in _SCHEMA_PHASES]

_COMMON_KEYS = {"phase", "benchmark", "slug", "verdict"}


@pytest.mark.unit
@pytest.mark.parametrize(
    ("phase_num", "suffix"),
    _SCHEMA_PHASES,
    ids=_SCHEMA_IDS,
)
def test_phase_artifact_has_expected_keys(phase_num: int, suffix: str) -> None:
    """Phase 25-39 artifacts must all carry the common top-level schema keys."""
    artifact = _RESULTS_DIR / f"benchmark_c_phase{phase_num}_{suffix}.json"
    assert artifact.exists(), f"Artifact not found: {artifact.name}"

    with artifact.open(encoding="utf-8") as fh:
        data = json.load(fh)

    missing = _COMMON_KEYS - data.keys()
    assert not missing, (
        f"phase{phase_num} artifact missing common keys: {sorted(missing)}\n"
        f"Present keys: {sorted(data.keys())}"
    )

    # Type-level spot-checks for the common fields.
    assert isinstance(data["phase"], str) and str(phase_num) in data["phase"], (
        f"phase{phase_num}: expected 'phase' string to contain '{phase_num}', "
        f"got {data['phase']!r}"
    )
    assert data["benchmark"] == "benchmark_c", (
        f"phase{phase_num}: expected benchmark='benchmark_c', got {data['benchmark']!r}"
    )
    assert isinstance(data["slug"], str) and data["slug"], (
        f"phase{phase_num}: expected a non-empty 'slug' string, got {data['slug']!r}"
    )
    assert isinstance(data["verdict"], str) and data["verdict"], (
        f"phase{phase_num}: expected a non-empty 'verdict' string, got {data['verdict']!r}"
    )
