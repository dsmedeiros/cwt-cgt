"""Narrow core adapter for the D0 diagonal rational bridge family."""

from __future__ import annotations

from dataclasses import replace
from fractions import Fraction

import numpy as np

from cwt.cgt.benchmarks import get_benchmark
from cwt.cgt.models import BranchState
from cwt.cgt.open_system import (
    OpenSystemConfig,
    apply_local_open_step,
    local_kraus_operators,
    observable_operator,
)

from .contract import MODEL_CONTRACT, BridgeContract
from .exact_math import bridge_components, d0_kernel_fraction, fraction_item


def theorem_state(bias: float, diffusion: float) -> BranchState:
    """Build only the D0 kernel; p/theta are inactive under the frozen channel."""

    return BranchState(
        p=np.full(MODEL_CONTRACT.node_count, 1.0 / MODEL_CONTRACT.node_count),
        theta=np.zeros(MODEL_CONTRACT.node_count, dtype=float),
        kernel=np.asarray(
            d0_kernel_fraction(Fraction(str(bias)), Fraction(str(diffusion))),
            dtype=float,
        ),
        extras={"b": bias, "d": diffusion},
    )


def core_config(h: Fraction, contract: BridgeContract = MODEL_CONTRACT) -> OpenSystemConfig:
    """Return a finite-float core regression config on its frozen runtime domain."""

    if not isinstance(h, Fraction):
        raise TypeError("core regression h must be an exact Fraction")
    if not contract.core_runtime_h_min <= h <= contract.core_runtime_h_max:
        raise ValueError(
            "core regression h must satisfy the frozen representable runtime domain " "1/10^12<=h<=1/5"
        )
    runtime_h = float(h)
    runtime_q = float(contract.depolarizing_rate * h)
    if runtime_h <= 0.0 or runtime_q <= 0.0:
        raise ValueError("core regression float conversion underflowed")

    return OpenSystemConfig(
        dt=runtime_h,
        coherent_scale=float(contract.coherent_scale),
        edge_jump_scale=float(contract.edge_jump_scale),
        site_potential_scale=float(contract.site_potential_scale),
        depolarizing=runtime_q,
        branch_steps=contract.branch_steps_unused,
        fixed_point_max_iter=contract.fixed_point_max_iter_unused,
        fixed_point_tol=float(contract.fixed_point_tol_unused),
        dephasing_values=tuple(float(value) for value in contract.dephasing_values),
        coherence_switch_floor=float(contract.coherence_switch_floor),
        scan_mesh=contract.scan_mesh,
    )


def mean_position_operator(state: BranchState | None = None) -> np.ndarray:
    """Resolve the named geometry-blind core observable."""

    benchmark = get_benchmark(MODEL_CONTRACT.benchmark_id)
    if state is None:
        state = theorem_state(
            float(MODEL_CONTRACT.center_bias),
            float(MODEL_CONTRACT.center_diffusion),
        )
    return observable_operator(benchmark, state, MODEL_CONTRACT.observable_name)


def raw_core_step(
    rho: np.ndarray,
    state: BranchState,
    config: OpenSystemConfig,
    dephasing: float,
) -> np.ndarray:
    """Evaluate the exact core Kraus/depolarizing expression before PSD projection."""

    updated = np.zeros_like(rho, dtype=complex)
    for operator in local_kraus_operators(state, config, dephasing):
        updated += operator @ rho @ operator.conj().T
    if config.depolarizing > 0:
        updated = (1 - config.depolarizing) * updated + config.depolarizing * np.eye(5) / 5
    return updated


def affine_population_step(
    population: np.ndarray,
    h: Fraction,
    bias: Fraction,
    diffusion: Fraction,
    contract: BridgeContract = MODEL_CONTRACT,
) -> np.ndarray:
    matrix, source, _ = bridge_components(h, bias, diffusion, contract)
    return np.asarray(matrix, dtype=float) @ np.asarray(population, dtype=float) + np.asarray(
        source, dtype=float
    )


def _control_points(contract: BridgeContract) -> tuple[tuple[Fraction, Fraction], ...]:
    return (
        (contract.box.bias_min, contract.box.diffusion_min),
        (contract.box.bias_min, contract.box.diffusion_max),
        (contract.box.bias_max, contract.box.diffusion_min),
        (contract.box.bias_max, contract.box.diffusion_max),
        (contract.center_bias, contract.center_diffusion),
    )


def core_binding_certificate(contract: BridgeContract = MODEL_CONTRACT) -> dict[str, object]:
    """Run finite core provenance regressions; these do not prove uniform identity."""

    h_values = (Fraction(1, 5), Fraction(1, 10), Fraction(1, 20))
    basis = tuple(np.eye(contract.node_count)[index] for index in range(contract.node_count))
    uniform = np.full(contract.node_count, 1.0 / contract.node_count)
    deviations = tuple(
        np.eye(contract.node_count)[index] - np.eye(contract.node_count)[-1]
        for index in range(contract.node_count - 1)
    )
    epsilon = 0.05
    maximum_kernel_error = 0.0
    maximum_affine_error = 0.0
    maximum_deviation_error = 0.0
    maximum_projection_delta = 0.0
    maximum_tp_error = 0.0
    maximum_offdiagonal_output = 0.0
    benchmark = get_benchmark(contract.benchmark_id)

    for bias, diffusion in _control_points(contract):
        state = theorem_state(float(bias), float(diffusion))
        candidate = benchmark.resolve_candidate_by_id(float(bias), float(diffusion), contract.branch_id)
        if candidate is None:
            raise RuntimeError("core Benchmark-D D0 candidate is missing")
        maximum_kernel_error = max(
            maximum_kernel_error,
            float(np.max(np.abs(np.asarray(candidate.state.kernel) - state.kernel))),
        )
        for h in h_values:
            config = core_config(h, contract)
            kraus = local_kraus_operators(state, config, float(contract.actual_dephasing))
            completeness = sum(
                (operator.conj().T @ operator for operator in kraus),
                np.zeros((contract.node_count, contract.node_count), dtype=complex),
            )
            maximum_tp_error = max(
                maximum_tp_error,
                float(np.linalg.norm(completeness - np.eye(contract.node_count), ord=2)),
            )
            for population in basis:
                rho = np.diag(population).astype(complex)
                raw = raw_core_step(rho, state, config, float(contract.actual_dephasing))
                projected = apply_local_open_step(
                    rho,
                    state,
                    config,
                    float(contract.actual_dephasing),
                )
                affine = affine_population_step(population, h, bias, diffusion, contract)
                maximum_affine_error = max(
                    maximum_affine_error,
                    float(np.max(np.abs(np.diag(raw).real - affine))),
                )
                maximum_offdiagonal_output = max(
                    maximum_offdiagonal_output,
                    float(np.max(np.abs(raw - np.diag(np.diag(raw))))),
                )
                maximum_projection_delta = max(
                    maximum_projection_delta,
                    float(np.linalg.norm(projected - raw, ord="fro")),
                )
            raw_uniform = raw_core_step(
                np.diag(uniform).astype(complex),
                state,
                config,
                float(contract.actual_dephasing),
            )
            affine_uniform = affine_population_step(uniform, h, bias, diffusion, contract)
            for deviation in deviations:
                perturbed = uniform + epsilon * deviation
                raw_perturbed = raw_core_step(
                    np.diag(perturbed).astype(complex),
                    state,
                    config,
                    float(contract.actual_dephasing),
                )
                observed = (np.diag(raw_perturbed).real - np.diag(raw_uniform).real) / epsilon
                expected = (
                    affine_population_step(perturbed, h, bias, diffusion, contract) - affine_uniform
                ) / epsilon
                maximum_deviation_error = max(
                    maximum_deviation_error,
                    float(np.max(np.abs(observed - expected))),
                )

    operator = mean_position_operator()
    expected_operator = np.diag(np.arange(1, contract.node_count + 1, dtype=float))
    return {
        "semantic_scope": contract.core_regression_scope,
        "uniform_family_proof_source": "exact_fraction_symbolic_affine_identity_not_runtime_samples",
        "runtime_h_domain": {
            "minimum": fraction_item(contract.core_runtime_h_min),
            "maximum": fraction_item(contract.core_runtime_h_max),
        },
        "control_points": [
            [fraction_item(bias), fraction_item(diffusion)] for bias, diffusion in _control_points(contract)
        ],
        "h_crosscheck_values_not_proof": [fraction_item(value) for value in h_values],
        "population_basis_count": len(basis),
        "traceless_diagonal_deviation_basis_count": len(deviations),
        "maximum_kernel_error": maximum_kernel_error,
        "maximum_affine_error": maximum_affine_error,
        "maximum_deviation_error": maximum_deviation_error,
        "maximum_projection_delta": maximum_projection_delta,
        "maximum_kraus_tp_error": maximum_tp_error,
        "maximum_offdiagonal_output": maximum_offdiagonal_output,
        "observable_name": contract.observable_name,
        "observable_maximum_absolute_error": float(np.max(np.abs(operator - expected_operator))),
        "observable_hermiticity_error": float(np.linalg.norm(operator - operator.conj().T, ord=2)),
        "branch_or_fixed_helper_called": False,
    }


def safety_certificate(contract: BridgeContract = MODEL_CONTRACT) -> dict[str, object]:
    """Return the exact uniform Kraus/support margins before numerical cross-checks."""

    maximum_kernel_plus = contract.box.diffusion_max + contract.box.bias_max
    minimum_kernel_minus = contract.box.diffusion_min - contract.box.bias_max
    maximum_outgoing_jump_rate = 2 * contract.box.diffusion_max * contract.edge_jump_scale
    maximum_loss = contract.h_upper * (contract.actual_dephasing + maximum_outgoing_jump_rate)
    radicand_floor = 1 - maximum_loss
    return {
        "kernel_plus_maximum": fraction_item(maximum_kernel_plus),
        "kernel_minus_minimum": fraction_item(minimum_kernel_minus),
        "clip_support_margin": fraction_item(min(minimum_kernel_minus, 1 - maximum_kernel_plus)),
        "maximum_no_jump_loss": fraction_item(maximum_loss),
        "formal_maximum_no_jump_loss": fraction_item(Fraction(199, 2500)),
        "no_jump_radicand_floor": fraction_item(radicand_floor),
        "formal_no_jump_radicand_floor": fraction_item(Fraction(2301, 2500)),
        "core_rescale_threshold": fraction_item(Fraction(49, 50)),
        "rescale_margin": fraction_item(Fraction(49, 50) - maximum_loss),
        "clip_inactive": minimum_kernel_minus > 0 and maximum_kernel_plus < 1,
        "rescale_inactive": maximum_loss < Fraction(49, 50),
        "projection_inactive_required": True,
    }


def contract_mutation_issues(contract: BridgeContract) -> list[str]:
    """Return fail-closed contract deviations; no variant can inherit the proof."""

    issues: list[str] = []
    for field in (
        "experiment_id",
        "benchmark_id",
        "branch_id",
        "node_count",
        "control_names",
        "box",
        "center_bias",
        "center_diffusion",
        "theorem_family_scope",
        "h_domain",
        "h_upper",
        "core_regression_scope",
        "core_runtime_h_min",
        "core_runtime_h_max",
        "edge_jump_scale",
        "depolarizing_rate",
        "depolarizing_rule",
        "coherent_scale",
        "site_potential_scale",
        "actual_dephasing",
        "branch_steps_unused",
        "fixed_point_max_iter_unused",
        "fixed_point_tol_unused",
        "dephasing_values",
        "coherence_switch_floor",
        "scan_mesh",
        "branch_helper_policy",
        "fixed_point_helper_policy",
        "projection_policy",
        "transpose_convention",
        "population_map_formula",
        "affine_source_formula",
        "effective_generator_formula",
        "exact_fixed_branch_formula",
        "stationary_positivity_bound",
        "derivative_proof_mode",
        "proof_mode",
        "observable_name",
        "response_centering",
        "response_scaling",
        "response_units",
        "update_convention",
        "reversal_convention",
        "endpoint_convention",
        "slow_clock",
        "initialization",
        "scale_domain",
        "scale_upper",
        "circle_scale",
        "qanti_definition",
        "did_definition",
        "fixed_time",
        "pi_enclosure",
        "primary_limit_order",
        "joint_limit_scope",
        "limit_interchangeability",
        "legacy_discrete_context",
        "legacy_continuous_context",
        "exponential_context",
        "empirical_status",
        "disposition",
        "claim_ceiling",
    ):
        if getattr(contract, field) != getattr(MODEL_CONTRACT, field):
            issues.append(f"{field}: outside frozen bridge contract")
    return issues


def core_mutation_examples(contract: BridgeContract = MODEL_CONTRACT) -> dict[str, list[str]]:
    """Materialize representative forbidden variants for the refusal matrix."""

    return {
        "fixed_q": contract_mutation_issues(replace(contract, depolarizing_rule="q_h=1/125")),
        "exponential_q": contract_mutation_issues(replace(contract, depolarizing_rule="q_h=1-exp(-delta*h)")),
        "zero_delta": contract_mutation_issues(replace(contract, depolarizing_rate=Fraction(0))),
        "coherent": contract_mutation_issues(replace(contract, coherent_scale=Fraction(1, 10))),
        "site": contract_mutation_issues(replace(contract, site_potential_scale=Fraction(1, 10))),
        "wrong_scaling": contract_mutation_issues(
            replace(contract, response_scaling="Q=sum_right_endpoint_centered_readout")
        ),
        "wrong_center": contract_mutation_issues(
            replace(contract, response_centering="continuous_xbar_instead_of_xbar_h")
        ),
        "wrong_clock": contract_mutation_issues(replace(contract, slow_clock="arbitrary_clock")),
        "wrong_reverse": contract_mutation_issues(
            replace(contract, reversal_convention="independent_clockwise_path")
        ),
        "helper": contract_mutation_issues(
            replace(contract, fixed_point_helper_policy="iterative_fixed_point_allowed")
        ),
        "runtime_scope": contract_mutation_issues(
            replace(contract, core_regression_scope="finite_samples_prove_uniform_runtime_identity")
        ),
        "scale_domain": contract_mutation_issues(replace(contract, circle_scale=Fraction(1, 50))),
        "claim_inflation": contract_mutation_issues(
            replace(contract, claim_ceiling="universal empirical CGT proof")
        ),
    }
