"""Narrow adapter from the exact proof model to the named core Lindblad APIs."""

from __future__ import annotations

from dataclasses import asdict
from fractions import Fraction

import numpy as np

from cwt.cgt.benchmarks import get_benchmark
from cwt.cgt.lindblad import (
    LindbladConfig,
    lindblad_rhs,
    lindblad_superoperator,
    unvec_density,
    vec_density,
)
from cwt.cgt.models import BranchState
from cwt.cgt.open_system import observable_operator
from cwt.geometry.coherence import projective_metric_trace_and_curvature

from .contract import MODEL_CONTRACT, LindbladProofContract
from .exact_math import (
    affine_population_generator,
    affine_source,
    authored_d0_population,
    d0_kernel_fraction,
)


def core_config(contract: LindbladProofContract = MODEL_CONTRACT) -> LindbladConfig:
    """Construct the exact reviewed core configuration without relying on defaults."""

    return LindbladConfig(
        dt=float(contract.dt),
        integration_steps=contract.integration_steps,
        coherent_scale=float(contract.coherent_scale),
        edge_jump_scale=float(contract.edge_jump_scale),
        site_potential_scale=float(contract.site_potential_scale),
        depolarizing_rate=float(contract.depolarizing_rate),
        dephasing_values=tuple(float(value) for value in contract.dephasing_values),
        coherence_switch_floor=float(contract.coherence_switch_floor),
        scan_mesh=contract.scan_mesh,
    )


def analytic_d0_kernel(bias: float, diffusion: float) -> np.ndarray:
    """Return the unclipped D0 kernel on the frozen interior control box."""

    return np.asarray(
        d0_kernel_fraction(Fraction(str(bias)), Fraction(str(diffusion))),
        dtype=float,
    )


def theorem_d0_state(bias: float, diffusion: float) -> BranchState:
    """Build the theorem state explicitly; no continuation or stationary helper is used."""

    exact_p = authored_d0_population(Fraction(str(bias)), Fraction(str(diffusion)))
    return BranchState(
        p=np.asarray(exact_p, dtype=float),
        theta=np.zeros(MODEL_CONTRACT.node_count, dtype=float),
        kernel=analytic_d0_kernel(bias, diffusion),
        extras={"b": float(bias), "d": float(diffusion)},
    )


def core_d0_state(bias: float, diffusion: float) -> BranchState:
    """Resolve the named core D0 branch only for the adapter cross-check."""

    benchmark = get_benchmark(MODEL_CONTRACT.benchmark_id)
    candidate = benchmark.resolve_candidate_by_id(bias, diffusion, MODEL_CONTRACT.branch_id)
    if candidate is None:
        raise ValueError("Benchmark D D0 is unavailable at the requested controls")
    return candidate.state


def mean_position_operator(state: BranchState | None = None) -> np.ndarray:
    """Invoke the named core readout used by the theorem response path."""

    if state is None:
        state = theorem_d0_state(
            float(MODEL_CONTRACT.center_bias),
            float(MODEL_CONTRACT.center_diffusion),
        )
    benchmark = get_benchmark(MODEL_CONTRACT.benchmark_id)
    return observable_operator(benchmark, state, MODEL_CONTRACT.observable_name)


def core_binding_certificate() -> dict[str, object]:
    """Cross-check D0, its unclipped support, config, and named readout."""

    box = MODEL_CONTRACT.box
    points = (
        (box.bias_min, box.diffusion_min),
        (box.bias_min, box.diffusion_max),
        (box.bias_max, box.diffusion_min),
        (box.bias_max, box.diffusion_max),
        (MODEL_CONTRACT.center_bias, MODEL_CONTRACT.center_diffusion),
    )
    kernel_errors: list[float] = []
    probability_errors: list[float] = []
    phase_errors: list[float] = []
    for bias, diffusion in points:
        theorem = theorem_d0_state(float(bias), float(diffusion))
        core = core_d0_state(float(bias), float(diffusion))
        kernel_errors.append(float(np.max(np.abs(theorem.kernel - core.kernel))))
        probability_errors.append(float(np.max(np.abs(theorem.p - core.p))))
        phase_errors.append(float(np.max(np.abs(theorem.theta - core.theta))))

    operator = mean_position_operator()
    expected_operator = np.diag(np.arange(1, MODEL_CONTRACT.node_count + 1)).astype(complex)
    config = core_config()
    expected_config = {
        "dt": float(MODEL_CONTRACT.dt),
        "integration_steps": MODEL_CONTRACT.integration_steps,
        "coherent_scale": float(MODEL_CONTRACT.coherent_scale),
        "edge_jump_scale": float(MODEL_CONTRACT.edge_jump_scale),
        "site_potential_scale": float(MODEL_CONTRACT.site_potential_scale),
        "depolarizing_rate": float(MODEL_CONTRACT.depolarizing_rate),
        "dephasing_values": tuple(float(value) for value in MODEL_CONTRACT.dephasing_values),
        "coherence_switch_floor": float(MODEL_CONTRACT.coherence_switch_floor),
        "scan_mesh": MODEL_CONTRACT.scan_mesh,
    }
    actual_config = asdict(config)
    config_matches = all(actual_config[key] == value for key, value in expected_config.items())

    k_minus_min = box.diffusion_min - box.bias_max
    k_plus_max = box.diffusion_max + box.bias_max
    interior_hold_min = 1 - 2 * box.diffusion_max
    return {
        "core_benchmark_id": get_benchmark(MODEL_CONTRACT.benchmark_id).benchmark_id,
        "core_branch_id": MODEL_CONTRACT.branch_id,
        "maximum_kernel_error": max(kernel_errors),
        "maximum_core_helper_p_vs_explicit_smooth_d0_map_difference": max(probability_errors),
        "core_helper_probability_used_by_theorem_generator": False,
        "probability_scope": (
            "zero coherent/site terms make the Lindblad generator independent of p/theta; "
            "the auxiliary smooth closed-form D0 map is channel-equivalent but is not the "
            "current core helper BranchState geometry and is used only for the projective no-go control"
        ),
        "maximum_phase_error": max(phase_errors),
        "observable_name": MODEL_CONTRACT.observable_name,
        "observable_maximum_absolute_error": float(np.max(np.abs(operator - expected_operator))),
        "observable_hermiticity_error": float(np.linalg.norm(operator - operator.conj().T, ord=2)),
        "all_config_fields_explicit_and_equal": config_matches,
        "config": actual_config,
        "minimum_positive_transition_rate": float(k_minus_min),
        "minimum_interior_hold_probability": float(interior_hold_min),
        "lower_clip_support_margin": float(k_minus_min - Fraction(1, 50)),
        "upper_clip_support_margin": float(Fraction(23, 50) - k_plus_max),
        "clipping_inactive_on_box": k_minus_min > Fraction(1, 50) and k_plus_max < Fraction(23, 50),
    }


def _float_affine_components(bias: float, diffusion: float) -> tuple[np.ndarray, np.ndarray]:
    matrix = np.asarray(
        affine_population_generator(Fraction(str(bias)), Fraction(str(diffusion))),
        dtype=float,
    )
    source = np.asarray(affine_source(), dtype=float)
    return matrix, source


def core_affine_equivalence_certificate() -> dict[str, object]:
    """Bind the affine model on the complete diagonal invariant subspace."""

    config = core_config()
    dephasing = float(MODEL_CONTRACT.actual_dephasing)
    box = MODEL_CONTRACT.box
    points = (
        (float(box.bias_min), float(box.diffusion_min)),
        (float(box.bias_min), float(box.diffusion_max)),
        (float(box.bias_max), float(box.diffusion_min)),
        (float(box.bias_max), float(box.diffusion_max)),
        (float(MODEL_CONTRACT.center_bias), float(MODEL_CONTRACT.center_diffusion)),
    )
    diagonal_population_basis = tuple(
        np.eye(MODEL_CONTRACT.node_count, dtype=float)[index] for index in range(MODEL_CONTRACT.node_count)
    )
    traceless_diagonal_basis = tuple(
        np.eye(MODEL_CONTRACT.node_count, dtype=float)[index]
        - np.eye(MODEL_CONTRACT.node_count, dtype=float)[-1]
        for index in range(MODEL_CONTRACT.node_count - 1)
    )
    rhs_errors: list[float] = []
    offdiagonal_errors: list[float] = []
    trace_errors: list[float] = []
    superoperator_errors: list[float] = []
    source_errors: list[float] = []
    control_point_errors: list[dict[str, object]] = []
    for bias, diffusion in points:
        rhs_start = len(rhs_errors)
        superoperator_start = len(superoperator_errors)
        state = theorem_d0_state(bias, diffusion)
        matrix, source = _float_affine_components(bias, diffusion)
        superoperator = lindblad_superoperator(state, config, dephasing)
        zero = np.zeros((MODEL_CONTRACT.node_count, MODEL_CONTRACT.node_count), dtype=complex)
        source_core = lindblad_rhs(zero, state, config, dephasing)
        source_errors.append(float(np.max(np.abs(source_core - np.diag(source)))))
        for population in diagonal_population_basis:
            rho = np.diag(population).astype(complex)
            core_rhs = lindblad_rhs(rho, state, config, dephasing)
            exact_rhs = matrix @ population + source
            rhs_errors.append(float(np.max(np.abs(np.diag(core_rhs) - exact_rhs))))
            offdiagonal = core_rhs - np.diag(np.diag(core_rhs))
            offdiagonal_errors.append(float(np.max(np.abs(offdiagonal))))
            trace_errors.append(float(abs(np.trace(core_rhs))))
        for deviation in traceless_diagonal_basis:
            core_linear = unvec_density(
                superoperator @ vec_density(np.diag(deviation)),
                MODEL_CONTRACT.node_count,
            )
            exact_linear = matrix @ deviation
            superoperator_errors.append(float(np.max(np.abs(core_linear - np.diag(exact_linear)))))
        control_point_errors.append(
            {
                "bias": bias,
                "diffusion": diffusion,
                "maximum_diagonal_rhs_error": max(rhs_errors[rhs_start:]),
                "maximum_superoperator_deviation_error": max(superoperator_errors[superoperator_start:]),
            }
        )
    return {
        "semantic_scope": "complete_diagonal_invariant_subspace_not_full_superoperator",
        "core_rhs_function": "cwt.cgt.lindblad.lindblad_rhs",
        "core_superoperator_function": "cwt.cgt.lindblad.lindblad_superoperator",
        "control_points": [[bias, diffusion] for bias, diffusion in points],
        "control_point_errors": control_point_errors,
        "control_point_count": len(points),
        "diagonal_population_basis_count": len(diagonal_population_basis),
        "traceless_diagonal_deviation_basis_count": len(traceless_diagonal_basis),
        "maximum_diagonal_rhs_error": max(rhs_errors),
        "maximum_offdiagonal_rhs_error": max(offdiagonal_errors),
        "maximum_trace_preservation_error": max(trace_errors),
        "maximum_superoperator_deviation_error": max(superoperator_errors),
        "maximum_affine_source_error": max(source_errors),
        "affine_source_required_norm": float(np.linalg.norm(affine_source(), ord=1)),
    }


def explicit_projective_no_go_certificate(step: float = 1e-5) -> dict[str, object]:
    """Certify the auxiliary smooth positive-real D0 Psi and Omega_bd=0."""

    center_b = float(MODEL_CONTRACT.center_bias)
    center_d = float(MODEL_CONTRACT.center_diffusion)

    def psi(bias: float, diffusion: float) -> np.ndarray:
        population = np.asarray(
            authored_d0_population(Fraction(str(bias)), Fraction(str(diffusion))),
            dtype=float,
        )
        return np.sqrt(population).astype(complex)

    psi0 = psi(center_b, center_d)
    metric_trace, curvature = projective_metric_trace_and_curvature(
        psi0,
        psi(center_b + step, center_d),
        psi(center_b - step, center_d),
        psi(center_b, center_d + step),
        psi(center_b, center_d - step),
        step,
        step,
    )
    box = MODEL_CONTRACT.box
    corner_populations = [
        authored_d0_population(bias, diffusion)
        for bias in (box.bias_min, box.bias_max)
        for diffusion in (box.diffusion_min, box.diffusion_max)
    ]
    return {
        "state_map": "auxiliary psi_j=sqrt(p_j)>0 with p_j proportional to ((d+b)/(d-b))^j",
        "closed_form_population": "p_j proportional to ((d+b)/(d-b))^j",
        "channel_equivalent_under_frozen_generator": True,
        "channel_equivalence_reason": (
            "p and theta are inactive because coherent_scale=site_potential_scale=0"
        ),
        "is_current_core_helper_branch_state_geometry": False,
        "scope_note": (
            "auxiliary no-universal-alignment map only; not the current core helper BranchState geometry"
        ),
        "stationary_eigenvector_helper_used": False,
        "minimum_exact_corner_probability": float(min(map(min, corner_populations))),
        "psi_norm_error": float(abs(np.vdot(psi0, psi0).real - 1.0)),
        "all_sampled_psi_components_real": bool(np.all(np.imag(psi0) == 0.0)),
        "projective_metric_trace": metric_trace,
        "numerical_projective_curvature_bd": curvature,
        "projective_curvature_bd_exact_fraction": "0/1",
        "exact_zero_reason": "the normalized state and both parameter derivatives are real",
    }


def benchmark_c_unital_null_certificate() -> dict[str, object]:
    """Check the true Benchmark-C fixed density I/3 and its zero centered response."""

    benchmark = get_benchmark("benchmark_c")
    config = core_config()
    uniform = np.eye(3, dtype=complex) / 3.0
    controls = ((0.0, 0.0), (0.18, 0.0), (-0.18, 0.10), (0.12, -0.12))
    rhs_errors: list[float] = []
    readout_values: list[float] = []
    for u, v in controls:
        state = benchmark.branch_state_fn(u, v)
        rhs_errors.append(
            float(
                np.max(
                    np.abs(
                        lindblad_rhs(
                            uniform,
                            state,
                            config,
                            float(MODEL_CONTRACT.actual_dephasing),
                        )
                    )
                )
            )
        )
        observable = observable_operator(benchmark, state, benchmark.primary_observable)
        readout_values.append(float(np.real(np.trace(observable @ uniform))))
    return {
        "fixed_density": "I/3",
        "maximum_fixed_rhs_error": max(rhs_errors),
        "maximum_centered_readout_absolute_value": max(map(abs, readout_values)),
        "response_curvature_exact_fraction": "0/1",
    }
