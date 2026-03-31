"""Smoke tests for the CGT benchmark scaffold.

Covers benchmark construction, scan output keys, branch atlas ambiguity,
and phase-alignment helpers.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from cwt.cgt.analysis.phase13_analysis import Phase13Config, phase13_payload
from cwt.cgt.analysis.phase14_analysis import Phase14Config, phase14_payload
from cwt.cgt.analysis.phase15_analysis import Phase15Config, phase15_payload, phase15_report
from cwt.cgt.benchmarks import get_benchmark
from cwt.cgt.continuation import build_branch_atlas
from cwt.cgt.models import BranchState, ScanConfig
from cwt.cgt.open_system import observable_operator
from cwt.cgt.runner import run_benchmark_scan
from cwt.geometry.mixed_state import phase_alignment_sign, unwrap_phase_sequence

# ---------------------------------------------------------------------------
# a) Benchmark construction
# ---------------------------------------------------------------------------

BENCHMARK_IDS = ["benchmark_a", "benchmark_b", "benchmark_c", "benchmark_d", "benchmark_f"]


@pytest.mark.unit
@pytest.mark.parametrize("benchmark_id", BENCHMARK_IDS)
def test_benchmark_instantiation(benchmark_id: str) -> None:
    """get_benchmark returns a BenchmarkDefinition for every known benchmark."""
    benchmark = get_benchmark(benchmark_id)
    assert benchmark.benchmark_id == benchmark_id
    assert benchmark.slug
    assert benchmark.candidate_states_fn is not None


@pytest.mark.unit
@pytest.mark.parametrize("benchmark_id", BENCHMARK_IDS)
def test_branch_state_fn_returns_valid_state(benchmark_id: str) -> None:
    """branch_state_fn(0.5, 0.5) returns a BranchState with valid p, theta, kernel."""
    benchmark = get_benchmark(benchmark_id)
    state = benchmark.branch_state_fn(0.5, 0.5)

    assert isinstance(state, BranchState)

    # p sums to ~1 and all entries are non-negative
    assert state.p.ndim == 1
    assert np.all(state.p >= 0.0), f"{benchmark_id}: p has negative entries"
    np.testing.assert_allclose(
        np.sum(state.p),
        1.0,
        atol=1e-10,
        err_msg=f"{benchmark_id}: p does not sum to 1",
    )

    # theta has same shape as p
    assert state.theta.shape == state.p.shape, f"{benchmark_id}: theta shape mismatch"

    # kernel is square with matching dimension
    n = state.p.size
    assert state.kernel.shape == (n, n), f"{benchmark_id}: kernel shape mismatch"


@pytest.mark.unit
def test_benchmark_known_key_error() -> None:
    """get_benchmark raises KeyError for an unknown benchmark id."""
    with pytest.raises(KeyError):
        get_benchmark("benchmark_unknown_xyz")


# ---------------------------------------------------------------------------
# b) Benchmark A scan produces expected keys
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_benchmark_a_scan_keys(tmp_path: pytest.TempPathFactory) -> None:
    """run_benchmark_scan returns a dict with all required top-level keys."""
    config = ScanConfig(mesh=5)
    result = run_benchmark_scan("benchmark_a", output_root=tmp_path, config=config)

    required_keys = {
        "benchmark",
        "grid_u",
        "grid_v",
        "metric_trace",
        "curvature",
    }
    for key in required_keys:
        assert key in result, f"Missing key in scan result: {key!r}"

    assert result["benchmark"] == "benchmark_a"
    assert len(result["grid_u"]) == 5
    assert len(result["grid_v"]) == 5


@pytest.mark.unit
def test_benchmark_a_scan_output_file(tmp_path: pytest.TempPathFactory) -> None:
    """run_benchmark_scan writes a JSON file to the expected location."""
    config = ScanConfig(mesh=5)
    run_benchmark_scan("benchmark_a", output_root=tmp_path, config=config)

    benchmark = get_benchmark("benchmark_a")
    output_file = tmp_path / benchmark.slug / f"{benchmark.benchmark_id}_scan.json"
    assert output_file.exists(), f"Expected output file not found: {output_file}"
    assert output_file.stat().st_size > 0


# ---------------------------------------------------------------------------
# c) Benchmark F branch atlas has ambiguous points
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_benchmark_f_atlas_has_ambiguous_points() -> None:
    """build_branch_atlas for benchmark_f produces ambiguous tiles by construction."""
    benchmark = get_benchmark("benchmark_f")
    mesh = 9
    grid_u = np.linspace(benchmark.control_bounds[0][0], benchmark.control_bounds[0][1], mesh)
    grid_v = np.linspace(benchmark.control_bounds[1][0], benchmark.control_bounds[1][1], mesh)
    config = ScanConfig()

    atlas = build_branch_atlas(benchmark, grid_u, grid_v, config)

    assert "ambiguous_map" in atlas
    ambiguous_map = atlas["ambiguous_map"]
    ambiguity_count = sum(ambiguous_map[i][j] for i in range(mesh) for j in range(mesh))

    assert ambiguity_count > 0, (
        "benchmark_f is designed to have bistable (ambiguous) tiles; "
        f"expected ambiguity_count > 0 but got {ambiguity_count}"
    )


# ---------------------------------------------------------------------------
# d) Phase alignment helpers
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_unwrap_phase_sequence_monotone() -> None:
    """unwrap_phase_sequence handles a monotone ramp without jumps."""
    phases = [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0]
    result = unwrap_phase_sequence(phases)
    assert result.shape == (len(phases),)
    np.testing.assert_allclose(result, phases, atol=1e-12)


@pytest.mark.unit
def test_unwrap_phase_sequence_wraps_correctly() -> None:
    """unwrap_phase_sequence removes 2*pi discontinuities."""
    phases = np.array([0.0, np.pi / 2, np.pi, -np.pi + 0.1, -np.pi / 2])
    result = unwrap_phase_sequence(phases)
    # Result should be monotone (no backward jumps greater than pi)
    diffs = np.diff(result)
    assert np.all(diffs > -np.pi), "unwrap_phase_sequence produced a backward jump > pi"


@pytest.mark.unit
def test_unwrap_phase_sequence_empty() -> None:
    """unwrap_phase_sequence handles an empty input gracefully."""
    result = unwrap_phase_sequence([])
    assert result.size == 0


@pytest.mark.unit
def test_phase_alignment_sign_same_direction() -> None:
    """phase_alignment_sign returns +1 when reference and target align."""
    reference = [1.0, 2.0, 3.0]
    target = [0.5, 1.0, 1.5]
    sign = phase_alignment_sign(reference, target)
    assert sign == 1.0


@pytest.mark.unit
def test_phase_alignment_sign_opposite_direction() -> None:
    """phase_alignment_sign returns -1 when target is anti-parallel to reference."""
    reference = [1.0, 2.0, 3.0]
    target = [-1.0, -2.0, -3.0]
    sign = phase_alignment_sign(reference, target)
    assert sign == -1.0


@pytest.mark.unit
def test_phase_alignment_sign_all_nan() -> None:
    """phase_alignment_sign falls back to +1.0 when no finite overlap exists."""
    reference = [float("nan"), float("nan")]
    target = [float("nan"), float("nan")]
    sign = phase_alignment_sign(reference, target)
    assert sign == 1.0


@pytest.mark.unit
def test_phase13_smoke(tmp_path: Path) -> None:
    payload = phase13_payload(
        output_root=tmp_path,
        reports_dir=tmp_path / "reports",
        phase13_config=Phase13Config(
            benchmark_ids=("benchmark_c",),
            benchmark_focus="benchmark_c",
            scan_mesh=5,
            dephasing_values=(0.0, 0.30),
        ),
    )
    assert "benchmark_c" in payload["benchmark_summaries"]
    assert payload["benchmark_summaries"]["benchmark_c"]["benchmark"] == "benchmark_c"


@pytest.mark.unit
def test_phase14_smoke(tmp_path: Path) -> None:
    phase13_payload(
        output_root=tmp_path,
        reports_dir=tmp_path / "reports",
        phase13_config=Phase13Config(
            benchmark_ids=("benchmark_c",),
            benchmark_focus="benchmark_c",
            scan_mesh=5,
            dephasing_values=(0.0, 0.30),
        ),
    )
    payload = phase14_payload(
        output_root=tmp_path,
        reports_dir=tmp_path / "reports",
        phase14_config=Phase14Config(
            benchmark_ids=("benchmark_c",),
            benchmark_focus="benchmark_c",
            scan_mesh=5,
            dephasing_values=(0.0, 0.30),
        ),
    )
    assert "benchmark_c" in payload["benchmark_summaries"]
    assert payload["benchmark_summaries"]["benchmark_c"]["benchmark"] == "benchmark_c"
    bench_payload = payload["benchmark_payloads"]["benchmark_c"]
    assert bench_payload["phase13_reference"]["available"] is True
    assert bench_payload["phase13_reference"]["switch_by_center"]
    assert bench_payload["switch_level"]["sampled_centers"]


@pytest.mark.unit
def test_phase15_smoke(tmp_path: Path) -> None:
    payload = phase15_payload(
        output_root=tmp_path,
        phase15_config=Phase15Config(
            benchmark_ids=("benchmark_c",),
            benchmark_focus="benchmark_c",
            scan_mesh=5,
            dense_mesh_focus=7,
            focus_dephasing_values=(0.0, 0.30),
        ),
    )
    assert "benchmark_c" in payload["benchmark_summaries"]
    summary = payload["benchmark_summaries"]["benchmark_c"]
    assert summary["benchmark"] == "benchmark_c"
    assert summary["valid_cell_count"] > 0, "expected at least one valid cell"
    assert summary["structural_amplitude"] > 0.0, "structural amplitude should be positive"
    bench = payload["benchmark_payloads"]["benchmark_c"]
    assert bench["tangent_field"]["raw_point_count"] > 0


@pytest.mark.unit
def test_phase15_report_respects_reports_dir(tmp_path: Path) -> None:
    reports_dir = tmp_path / "reports"
    payload = phase15_payload(
        output_root=tmp_path,
        reports_dir=reports_dir,
        phase15_config=Phase15Config(
            benchmark_ids=("benchmark_c",),
            benchmark_focus="benchmark_c",
            scan_mesh=5,
            dense_mesh_focus=7,
            focus_dephasing_values=(0.0, 0.30),
        ),
    )
    plots = phase15_report(output_root=tmp_path, payload=payload, reports_dir=reports_dir)
    report_path = plots["phase15_report"]
    assert report_path.exists()
    assert report_path.parent == reports_dir


@pytest.mark.unit
def test_observable_operator_index_observables_fallback_on_small_state() -> None:
    benchmark = get_benchmark("benchmark_f")
    state = benchmark.branch_state_fn(0.5, 0.5)
    assert state.p.size < 4

    op_p4 = observable_operator(benchmark, state, observable_name="final_p4")
    op_p5 = observable_operator(benchmark, state, observable_name="final_p5")

    np.testing.assert_allclose(op_p4, np.eye(state.p.size, dtype=complex))
    np.testing.assert_allclose(op_p5, np.eye(state.p.size, dtype=complex))


@pytest.mark.unit
def test_phase15_nan_sanitization(tmp_path: Path) -> None:
    """Benchmark F produces untrusted cells with NaN; verify JSON is clean."""
    import json

    payload = phase15_payload(
        output_root=tmp_path,
        phase15_config=Phase15Config(
            benchmark_ids=("benchmark_f",),
            benchmark_focus="benchmark_f",
            scan_mesh=5,
            dense_mesh_focus=7,
            focus_dephasing_values=(0.0, 0.30),
        ),
    )
    text = json.dumps(payload)
    assert "NaN" not in text
    assert "Infinity" not in text
