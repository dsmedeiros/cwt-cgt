"""Adversarial red-team tests for facelift-utilities changeset.

Targets: lindblad.py new functions, geometry.py, mixed_state_geometry.py,
analytic_tangents.py, loop_protocols.py new loop shapes.
"""
from __future__ import annotations

import math

import numpy as np
import pytest

from cwt.cgt.models import BranchState
from cwt.cgt.lindblad import (
    LindbladConfig,
    lindblad_operators,
    lindblad_operator_family,
    lindblad_superoperator,
    lindblad_superoperator_frechet,
    lindblad_rhs,
    vec_density,
    unvec_density,
    _expectation,
    generator_projection,
    loop_generator_gap,
    second_magnus_projection,
    third_order_path_projection,
)
from cwt.cgt.geometry import (
    normalize_probabilities,
    wrap_phase,
    canonicalize_phase,
    psi_from_parts,
    psi_from_state,
    overlap,
    phase_coherence,
    berry_loop_flux,
    polygon_signed_area,
    branch_distance,
    summarize,
    summarize_abs,
    projective_metric_trace_and_curvature,
)
from cwt.cgt.mixed_state_geometry import (
    density_from_state,
    project_to_density,
    matrix_sqrt_psd,
    matrix_inv_sqrt_psd,
    fidelity,
    bures_distance_sq,
    offdiag_norm,
    purity,
    polar_unitary,
    uhlmann_link_unitary,
    mixed_loop_holonomy_phase,
    mixed_plaquette_curvature,
)
from cwt.cgt.loop_protocols import build_loop_path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_state(n: int, *, uniform: bool = True, seed: int = 42) -> BranchState:
    """Create a minimal BranchState for testing."""
    rng = np.random.RandomState(seed)
    if uniform:
        p = np.ones(n, dtype=float) / n
        theta = np.zeros(n, dtype=float)
    else:
        p = np.abs(rng.randn(n)) + 0.01
        p /= p.sum()
        theta = rng.randn(n)
    kernel = np.abs(rng.randn(n, n)) * 0.1
    np.fill_diagonal(kernel, 0.0)
    row_sums = kernel.sum(axis=1, keepdims=True)
    kernel = kernel / np.maximum(row_sums, 1e-12) * 0.3
    np.fill_diagonal(kernel, 1.0 - kernel.sum(axis=1))
    return BranchState(p=p, theta=theta, kernel=kernel, extras={})


def _pure_density(n: int) -> np.ndarray:
    psi = np.zeros(n, dtype=complex)
    psi[0] = 1.0
    return np.outer(psi, psi.conj())


def _maximally_mixed(n: int) -> np.ndarray:
    return np.eye(n, dtype=complex) / n


# ---------------------------------------------------------------------------
# geometry.py tests
# ---------------------------------------------------------------------------

class TestNormalizeProbabilities:
    def test_all_zeros(self):
        result = normalize_probabilities(np.zeros(4))
        assert np.allclose(result, 0.25)
        assert abs(result.sum() - 1.0) < 1e-12

    def test_negative_values_clamped(self):
        result = normalize_probabilities(np.array([-1.0, -2.0, 3.0]))
        assert np.all(result >= 0.0)
        assert abs(result.sum() - 1.0) < 1e-12

    def test_single_element(self):
        result = normalize_probabilities(np.array([5.0]))
        assert abs(result[0] - 1.0) < 1e-12

    def test_empty_array(self):
        """Empty probability array -- returns empty array without crashing."""
        result = normalize_probabilities(np.array([]))
        assert result.size == 0


class TestWrapPhase:
    def test_scalar(self):
        result = wrap_phase(4.0 * np.pi + 0.1)
        assert abs(result - 0.1) < 1e-10

    def test_array(self):
        vals = np.array([-4 * np.pi, 0.0, 4 * np.pi])
        result = wrap_phase(vals)
        assert np.allclose(result, [0.0, 0.0, 0.0], atol=1e-10)

    def test_boundary_minus_pi(self):
        """Wrapping exactly -pi should produce -pi (or pi), not crash."""
        result = wrap_phase(-np.pi)
        assert abs(abs(result) - np.pi) < 1e-10


class TestPsiFromParts:
    def test_zero_probability(self):
        """All-zero p should produce a valid normalized state."""
        psi = psi_from_parts(np.zeros(3), np.zeros(3))
        assert abs(np.linalg.norm(psi) - 1.0) < 1e-10

    def test_single_site(self):
        psi = psi_from_parts(np.array([1.0]), np.array([0.5]))
        assert abs(np.linalg.norm(psi) - 1.0) < 1e-10


class TestOverlap:
    def test_orthogonal(self):
        a = np.array([1, 0], dtype=complex)
        b = np.array([0, 1], dtype=complex)
        assert abs(overlap(a, b)) < 1e-12

    def test_identical(self):
        a = np.array([1, 1j], dtype=complex) / np.sqrt(2)
        assert abs(overlap(a, a) - 1.0) < 1e-12


class TestBerryLoopFlux:
    def test_single_state(self):
        """Fewer than 2 states should return 0."""
        state = _make_state(3)
        assert berry_loop_flux([state]) == 0.0

    def test_empty_list(self):
        assert berry_loop_flux([]) == 0.0


class TestPolygonSignedArea:
    def test_fewer_than_three_points(self):
        assert polygon_signed_area([]) == 0.0
        assert polygon_signed_area([(0, 0)]) == 0.0
        assert polygon_signed_area([(0, 0), (1, 0)]) == 0.0

    def test_unit_square_ccw(self):
        path = [(0, 0), (1, 0), (1, 1), (0, 1), (0, 0)]
        assert abs(polygon_signed_area(path) - 1.0) < 1e-12

    def test_unit_square_cw(self):
        path = [(0, 0), (0, 1), (1, 1), (1, 0), (0, 0)]
        assert abs(polygon_signed_area(path) - (-1.0)) < 1e-12


class TestBranchDistance:
    def test_same_state(self):
        state = _make_state(3, uniform=False, seed=7)
        assert abs(branch_distance(state, state)) < 1e-10

    def test_no_kernel(self):
        """States without kernel attr should still work (kernel_term=0)."""
        class Bare:
            pass
        a = Bare()
        a.p = np.array([0.5, 0.5])
        a.theta = np.array([0.0, 0.0])
        b = Bare()
        b.p = np.array([0.5, 0.5])
        b.theta = np.array([0.0, 0.0])
        assert abs(branch_distance(a, b)) < 1e-10


class TestSummarize:
    def test_empty(self):
        result = summarize([])
        assert result['count'] == 0
        assert result['mean'] is None

    def test_with_nan(self):
        result = summarize([1.0, float('nan'), 3.0])
        assert result['count'] == 2

    def test_all_nan(self):
        result = summarize([float('nan'), float('nan')])
        assert result['count'] == 0


# ---------------------------------------------------------------------------
# mixed_state_geometry.py tests
# ---------------------------------------------------------------------------

class TestProjectToDensity:
    def test_negative_eigenvalue_matrix(self):
        """A matrix with negative eigenvalues should be projected to PSD."""
        rho = np.array([[0.8, 0.5], [0.5, -0.3]], dtype=complex)
        result = project_to_density(rho)
        evals = np.linalg.eigvalsh(result)
        assert np.all(evals >= -1e-12)
        assert abs(np.trace(result).real - 1.0) < 1e-12

    def test_zero_matrix(self):
        """All-zero matrix should produce maximally mixed."""
        result = project_to_density(np.zeros((3, 3), dtype=complex))
        assert abs(np.trace(result).real - 1.0) < 1e-12

    def test_pure_state_idempotent(self):
        rho = _pure_density(3)
        result = project_to_density(rho)
        assert np.allclose(result, rho, atol=1e-10)


class TestFidelity:
    def test_same_state(self):
        rho = _pure_density(2)
        assert abs(fidelity(rho, rho) - 1.0) < 1e-10

    def test_maximally_mixed_vs_pure(self):
        rho = _pure_density(2)
        sigma = _maximally_mixed(2)
        f = fidelity(rho, sigma)
        assert 0.0 < f < 1.0

    def test_orthogonal_pure_states(self):
        psi0 = np.array([1, 0], dtype=complex)
        psi1 = np.array([0, 1], dtype=complex)
        rho = np.outer(psi0, psi0.conj())
        sigma = np.outer(psi1, psi1.conj())
        assert fidelity(rho, sigma) < 1e-10

    def test_symmetry(self):
        rng = np.random.RandomState(123)
        A = rng.randn(3, 3) + 1j * rng.randn(3, 3)
        rho = project_to_density(A)
        B = rng.randn(3, 3) + 1j * rng.randn(3, 3)
        sigma = project_to_density(B)
        assert abs(fidelity(rho, sigma) - fidelity(sigma, rho)) < 1e-8


class TestBuresDistanceSq:
    def test_same_state_zero(self):
        rho = _pure_density(2)
        assert bures_distance_sq(rho, rho) < 1e-10

    def test_non_negative(self):
        rho = _pure_density(2)
        sigma = _maximally_mixed(2)
        assert bures_distance_sq(rho, sigma) >= 0.0


class TestPurity:
    def test_pure(self):
        rho = _pure_density(3)
        assert abs(purity(rho) - 1.0) < 1e-10

    def test_maximally_mixed(self):
        n = 4
        rho = _maximally_mixed(n)
        assert abs(purity(rho) - 1.0 / n) < 1e-10


class TestPolarUnitary:
    def test_zero_matrix(self):
        result = polar_unitary(np.zeros((3, 3), dtype=complex))
        assert np.allclose(result, np.eye(3))

    def test_unitary_input(self):
        u = np.array([[0, 1], [1, 0]], dtype=complex)
        result = polar_unitary(u)
        assert np.allclose(result @ result.conj().T, np.eye(2), atol=1e-10)


class TestMixedLoopHolonomyPhase:
    def test_single_state(self):
        assert mixed_loop_holonomy_phase([_pure_density(2)]) == 0.0

    def test_closed_trivial_loop(self):
        rho = _pure_density(2)
        phase = mixed_loop_holonomy_phase([rho, rho, rho, rho])
        assert abs(phase) < 1e-10


class TestMixedPlaquetteCurvature:
    def test_zero_area_guard(self):
        """Area=0 should not cause division by zero."""
        rho = _pure_density(2)
        result = mixed_plaquette_curvature(rho, rho, rho, rho, area=0.0)
        assert np.isfinite(result)

    def test_identical_corners(self):
        rho = _pure_density(2)
        result = mixed_plaquette_curvature(rho, rho, rho, rho, area=1.0)
        assert abs(result) < 1e-10


# ---------------------------------------------------------------------------
# lindblad.py tests
# ---------------------------------------------------------------------------

class TestVecUnvec:
    def test_roundtrip(self):
        rho = np.array([[1, 2], [3, 4]], dtype=complex)
        v = vec_density(rho)
        assert v.shape == (4,)
        recovered = unvec_density(v, 2)
        assert np.allclose(recovered, rho)

    def test_column_major_order(self):
        """vec should stack columns, not rows (Fortran order)."""
        rho = np.array([[1, 2], [3, 4]], dtype=complex)
        v = vec_density(rho)
        # Column-major: col0 then col1 -> [1, 3, 2, 4]
        assert np.allclose(v, [1, 3, 2, 4])


class TestLindbladSuperoperator:
    def test_trace_preserving(self):
        """The superoperator applied to vec(rho) should preserve trace.

        For trace preservation: sum_i L_ii = 0 for the Lindblad generator
        in the appropriate basis. We test by applying to a density matrix.
        """
        state = _make_state(3)
        config = LindbladConfig(depolarizing_rate=0.0)
        L = lindblad_superoperator(state, config, dephasing=0.1)
        rho = _pure_density(3)
        vec = vec_density(rho)
        drho_vec = L @ vec
        drho = unvec_density(drho_vec, 3)
        # Trace of drho should be zero (trace preserving generator)
        assert abs(np.trace(drho).real) < 1e-10, f"Trace not preserved: {np.trace(drho)}"

    def test_zero_dephasing(self):
        """Zero dephasing with only edge jumps should still be valid."""
        state = _make_state(2)
        config = LindbladConfig(depolarizing_rate=0.0)
        L = lindblad_superoperator(state, config, dephasing=0.0)
        assert L.shape == (4, 4)
        assert np.all(np.isfinite(L))

    def test_shape(self):
        state = _make_state(4)
        config = LindbladConfig()
        L = lindblad_superoperator(state, config, dephasing=0.05)
        assert L.shape == (16, 16)


class TestLindbladOperatorFamily:
    def test_fixed_length(self):
        """Operator family should have n*(n-1) + n operators regardless of rates."""
        state = _make_state(3)
        config = LindbladConfig()
        _, ops0 = lindblad_operator_family(state, config, dephasing=0.0)
        _, ops1 = lindblad_operator_family(state, config, dephasing=0.5)
        # n=3: 3*2=6 jump + 3 dephasing = 9
        assert len(ops0) == 9
        assert len(ops1) == 9

    def test_zero_dephasing_has_zero_ops(self):
        """With dephasing=0, dephasing operators should be zero matrices."""
        state = _make_state(3)
        config = LindbladConfig()
        _, ops = lindblad_operator_family(state, config, dephasing=0.0)
        # Last 3 are dephasing operators
        for op in ops[-3:]:
            assert np.allclose(op, 0.0)


class TestLindbladSuperoperatorFrechet:
    def test_zero_perturbation_is_zero(self):
        state = _make_state(2)
        config = LindbladConfig()
        h, ops = lindblad_operator_family(state, config, dephasing=0.1)
        dh = np.zeros_like(h)
        dops = [np.zeros_like(op) for op in ops]
        result = lindblad_superoperator_frechet(h, ops, dh, dops)
        assert np.allclose(result, 0.0)

    def test_mismatched_operator_list_length(self):
        """If ops and dops have different lengths, zip silently truncates."""
        state = _make_state(2)
        config = LindbladConfig()
        h, ops = lindblad_operator_family(state, config, dephasing=0.1)
        dh = np.zeros_like(h)
        # Fewer dops than ops -- zip truncates silently, potentially wrong result
        dops = [np.zeros_like(op) for op in ops[:1]]
        # This should ideally raise, but we just verify it doesn't crash
        result = lindblad_superoperator_frechet(h, ops, dh, dops)
        assert result.shape == (4, 4)


class TestExpectation:
    def test_identity_operator(self):
        rho = _pure_density(3)
        result = _expectation(np.eye(3, dtype=complex), rho)
        assert abs(result - 1.0) < 1e-10

    def test_zero_operator(self):
        rho = _pure_density(3)
        result = _expectation(np.zeros((3, 3), dtype=complex), rho)
        assert abs(result) < 1e-12


class TestGeneratorProjection:
    def test_empty_states(self):
        assert generator_projection([], None, LindbladConfig(), 0.0) == 0.0


class TestLoopGeneratorGap:
    def test_same_states_zero_gap(self):
        """CCW == CW should give zero gap."""
        state = _make_state(3)
        from cwt.cgt.benchmarks import get_benchmark
        benchmark = get_benchmark('benchmark_c')
        config = LindbladConfig()
        gap = loop_generator_gap(
            [state], [state], benchmark, config, 0.1
        )
        assert abs(gap) < 1e-10


class TestSecondMagnusProjection:
    def test_fewer_than_two(self):
        """Should return 0 for < 2 superoperators."""
        assert second_magnus_projection([], _pure_density(2), np.eye(2, dtype=complex), 0.01) == 0.0
        L = np.eye(4, dtype=complex)
        assert second_magnus_projection([L], _pure_density(2), np.eye(2, dtype=complex), 0.01) == 0.0

    def test_commuting_superoperators(self):
        """Commuting operators should give zero second Magnus term."""
        n = 2
        L = 0.1 * np.eye(n * n, dtype=complex)
        supers = [L, L, L]
        rho0 = _pure_density(n)
        op = np.eye(n, dtype=complex)
        result = second_magnus_projection(supers, rho0, op, 0.01)
        assert abs(result) < 1e-14


class TestThirdOrderPathProjection:
    def test_fewer_than_three(self):
        """Should return 0 for < 3 superoperators."""
        L = np.eye(4, dtype=complex)
        rho0 = _pure_density(2)
        op = np.eye(2, dtype=complex)
        assert third_order_path_projection([], rho0, op, 0.01) == 0.0
        assert third_order_path_projection([L], rho0, op, 0.01) == 0.0
        assert third_order_path_projection([L, L], rho0, op, 0.01) == 0.0


# ---------------------------------------------------------------------------
# loop_protocols.py -- new loop shapes
# ---------------------------------------------------------------------------

class TestLoopShapesClosed:
    """Every loop shape must produce a closed path (first == last)."""

    @pytest.mark.parametrize("shape", [
        "square", "circle", "diamond", "rounded_square",
        "ellipse", "stadium", "hexagon",
    ])
    def test_path_is_closed(self, shape: str):
        path = build_loop_path(
            center=(0.0, 0.0), side=0.2, orientation="ccw",
            shape=shape, steps_per_segment=8,
        )
        assert len(path) >= 3, f"Shape {shape} produced too few points"
        first = path[0]
        last = path[-1]
        assert abs(first[0] - last[0]) < 1e-12, f"{shape}: u mismatch {first[0]} vs {last[0]}"
        assert abs(first[1] - last[1]) < 1e-12, f"{shape}: v mismatch {first[1]} vs {last[1]}"

    @pytest.mark.parametrize("shape", [
        "square", "circle", "diamond", "rounded_square",
        "ellipse", "stadium", "hexagon",
    ])
    def test_cw_path_is_closed(self, shape: str):
        path = build_loop_path(
            center=(0.0, 0.0), side=0.2, orientation="cw",
            shape=shape, steps_per_segment=8,
        )
        first = path[0]
        last = path[-1]
        assert abs(first[0] - last[0]) < 1e-12, f"{shape} CW: u mismatch"
        assert abs(first[1] - last[1]) < 1e-12, f"{shape} CW: v mismatch"

    @pytest.mark.parametrize("shape", [
        "square", "circle", "diamond", "rounded_square",
        "ellipse", "stadium", "hexagon",
    ])
    def test_nonzero_signed_area(self, shape: str):
        """Every shape should enclose nonzero area."""
        path = build_loop_path(
            center=(0.0, 0.0), side=0.4, orientation="ccw",
            shape=shape, steps_per_segment=16,
        )
        area = polygon_signed_area(path)
        assert abs(area) > 1e-6, f"{shape}: signed area too small ({area})"

    @pytest.mark.parametrize("shape", [
        "square", "circle", "diamond", "rounded_square",
        "ellipse", "stadium", "hexagon",
    ])
    def test_orientation_reversal_flips_area_sign(self, shape: str):
        path_ccw = build_loop_path(
            center=(0.0, 0.0), side=0.3, orientation="ccw",
            shape=shape, steps_per_segment=12,
        )
        path_cw = build_loop_path(
            center=(0.0, 0.0), side=0.3, orientation="cw",
            shape=shape, steps_per_segment=12,
        )
        area_ccw = polygon_signed_area(path_ccw)
        area_cw = polygon_signed_area(path_cw)
        # Areas should have opposite signs (or both near-zero, which we've excluded above)
        if abs(area_ccw) > 1e-6:
            assert area_ccw * area_cw < 0, (
                f"{shape}: CCW area={area_ccw:.6f}, CW area={area_cw:.6f} -- same sign!"
            )


class TestLoopShapeEdgeCases:
    def test_unknown_shape_raises(self):
        with pytest.raises(ValueError, match="Unsupported loop shape"):
            build_loop_path(
                center=(0.0, 0.0), side=0.2, orientation="ccw",
                shape="nonexistent", steps_per_segment=8,
            )

    def test_very_small_side(self):
        """Tiny side length should not crash."""
        path = build_loop_path(
            center=(0.0, 0.0), side=1e-10, orientation="ccw",
            shape="circle", steps_per_segment=8,
        )
        assert len(path) >= 3

    def test_steps_per_segment_one(self):
        """Minimal steps_per_segment should still produce a closed path."""
        path = build_loop_path(
            center=(0.0, 0.0), side=0.2, orientation="ccw",
            shape="square", steps_per_segment=1,
        )
        assert path[0] == path[-1]


# ---------------------------------------------------------------------------
# projective_metric_trace_and_curvature edge cases
# ---------------------------------------------------------------------------

class TestProjectiveMetric:
    def test_identical_neighbors_zero_curvature(self):
        psi = np.array([1, 0, 0], dtype=complex)
        trace, curv = projective_metric_trace_and_curvature(
            psi, psi, psi, psi, psi, du=0.01, dv=0.01,
        )
        assert abs(curv) < 1e-10
        assert abs(trace) < 1e-10

    def test_zero_du_produces_nan_silently(self):
        """du=0 causes silent NaN via 0/0 division -- no exception raised.

        This is a finding: the function silently produces NaN rather than
        raising or returning a sentinel. Documented in the red-team report.
        """
        psi = np.array([1, 0], dtype=complex)
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            trace, curv = projective_metric_trace_and_curvature(
                psi, psi, psi, psi, psi, du=0.0, dv=0.01,
            )
        assert math.isnan(trace) or math.isnan(curv)


# ---------------------------------------------------------------------------
# matrix_sqrt_psd / matrix_inv_sqrt_psd edge cases
# ---------------------------------------------------------------------------

class TestMatrixSqrt:
    def test_identity(self):
        result = matrix_sqrt_psd(np.eye(3, dtype=complex))
        assert np.allclose(result, np.eye(3), atol=1e-10)

    def test_zero_matrix(self):
        result = matrix_sqrt_psd(np.zeros((2, 2), dtype=complex))
        assert np.allclose(result, 0.0)

    def test_inv_sqrt_with_zero_eigenvalue(self):
        """matrix_inv_sqrt_psd should handle near-zero eigenvalues via floor."""
        m = np.array([[1.0, 0], [0, 0]], dtype=complex)
        result = matrix_inv_sqrt_psd(m, floor=1e-12)
        assert np.all(np.isfinite(result))
