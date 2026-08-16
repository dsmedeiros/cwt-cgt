"""Narrow adapter binding the theorem fixture to the named core open-system map."""

from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from pathlib import Path

import numpy as np

from cwt.cgt.benchmarks import get_benchmark
from cwt.cgt.models import BranchState
from cwt.cgt.open_system import (
    OpenSystemConfig,
    apply_local_open_step,
    effective_branch_density,
    fixed_point_density,
    local_kraus_operators,
    observable_operator,
)
from cwt.geometry.psi import build_psi

from .contract import MODEL_CONTRACT, ModelContract

SIM_ROOT = Path(__file__).resolve().parents[2]
PHASE10_ARTIFACT_PATH = (
    SIM_ROOT / "cgt_benchmarks" / "results" / "benchmark_C_ring" / "benchmark_c_phase10.json"
)
PHASE10_HISTORICAL_ENTRY_PATH = SIM_ROOT / "scripts" / "cgt" / "run_phase10_analysis.py"
PHASE10_CURRENT_IMPLEMENTATION_PATH = SIM_ROOT / "cwt" / "cgt" / "analysis" / "phase10_analysis.py"


def core_config(
    contract: ModelContract = MODEL_CONTRACT,
    *,
    depolarizing: float | None = None,
) -> OpenSystemConfig:
    """Return the exact frozen core configuration."""

    return OpenSystemConfig(
        dt=float(contract.dt),
        coherent_scale=float(contract.coherent_scale),
        edge_jump_scale=float(contract.edge_jump_scale),
        site_potential_scale=float(contract.site_potential_scale),
        depolarizing=(float(contract.depolarizing) if depolarizing is None else depolarizing),
        branch_steps=3,
        fixed_point_max_iter=5000,
        fixed_point_tol=1e-13,
        dephasing_values=(float(contract.dephasing),),
    )


def analytic_d0_kernel(bias: float, diffusion: float) -> np.ndarray:
    """Return the unclipped D0 kernel on the certified interior box."""

    k_plus = diffusion + bias
    k_minus = diffusion - bias
    kernel = np.zeros((5, 5), dtype=float)
    kernel[0, 0] = 1.0 - k_plus
    kernel[0, 1] = k_plus
    for node in range(1, 4):
        kernel[node, node - 1] = k_minus
        kernel[node, node + 1] = k_plus
        kernel[node, node] = 1.0 - k_plus - k_minus
    kernel[4, 3] = k_minus
    kernel[4, 4] = 1.0 - k_minus
    return kernel


def core_d0_state(bias: float, diffusion: float) -> BranchState:
    """Resolve the authored D0 state only for kernel/provenance cross-checks."""

    benchmark = get_benchmark(MODEL_CONTRACT.benchmark_id)
    candidate = benchmark.resolve_candidate_by_id(bias, diffusion, MODEL_CONTRACT.branch_id)
    if candidate is None:
        raise ValueError("Benchmark D D0 is unavailable at the requested controls")
    return candidate.state


def theorem_d0_state(bias: float, diffusion: float) -> BranchState:
    """Build the theorem state from the D0 kernel without an authored stationary vector."""

    return BranchState(
        p=np.full(MODEL_CONTRACT.node_count, 1.0 / MODEL_CONTRACT.node_count),
        theta=np.zeros(MODEL_CONTRACT.node_count, dtype=float),
        kernel=analytic_d0_kernel(bias, diffusion),
        extras={"b": float(bias), "d": float(diffusion)},
    )


def mean_position_operator(state: BranchState | None = None) -> np.ndarray:
    """Return the named geometry-blind Hermitian readout from the core API."""

    benchmark = get_benchmark(MODEL_CONTRACT.benchmark_id)
    if state is None:
        state = theorem_d0_state(
            float(MODEL_CONTRACT.center_bias),
            float(MODEL_CONTRACT.center_diffusion),
        )
    return observable_operator(benchmark, state, MODEL_CONTRACT.observable_name)


def core_readout_certificate() -> dict[str, object]:
    """Bind the executed response reducer to the named core observable exactly."""

    operator = mean_position_operator()
    expected = np.diag(np.arange(1, MODEL_CONTRACT.node_count + 1, dtype=float))
    return {
        "observable_name": MODEL_CONTRACT.observable_name,
        "core_function": "cwt.cgt.open_system.observable_operator",
        "expected_diagonal": list(range(1, MODEL_CONTRACT.node_count + 1)),
        "maximum_absolute_error": float(np.max(np.abs(operator - expected))),
        "hermiticity_error": float(np.linalg.norm(operator - operator.conj().T, ord=2)),
    }


def constant_projective_reference_certificate() -> dict[str, object]:
    """Certify the separate channel-equivalent constant normalized state map.

    The authored D0 stationary probability is discontinuous and is not used as a
    projective branch here.  With the frozen zero coherent/site-potential terms,
    the channel is insensitive to ``p`` and ``theta``.  We therefore declare the
    exact constant reference ``p_j=1/5, theta_j=0`` only as a no-go control.
    """

    exact_definition = {
        "p": ["1/5"] * MODEL_CONTRACT.node_count,
        "theta_radians": ["0/1"] * MODEL_CONTRACT.node_count,
    }
    definition_bytes = (json.dumps(exact_definition, sort_keys=True, separators=(",", ":")) + "\n").encode(
        "utf-8"
    )
    points = (
        (float(MODEL_CONTRACT.box.bias_min), float(MODEL_CONTRACT.box.diffusion_min)),
        (float(MODEL_CONTRACT.box.bias_min), float(MODEL_CONTRACT.box.diffusion_max)),
        (float(MODEL_CONTRACT.box.bias_max), float(MODEL_CONTRACT.box.diffusion_min)),
        (float(MODEL_CONTRACT.box.bias_max), float(MODEL_CONTRACT.box.diffusion_max)),
        (float(MODEL_CONTRACT.center_bias), float(MODEL_CONTRACT.center_diffusion)),
    )
    states = [theorem_d0_state(bias, diffusion) for bias, diffusion in points]
    psis = [build_psi(state.p, state.theta) for state in states]
    declared_p = np.full(MODEL_CONTRACT.node_count, 1.0 / MODEL_CONTRACT.node_count)
    declared_theta = np.zeros(MODEL_CONTRACT.node_count, dtype=float)
    declared_psi = build_psi(declared_p, declared_theta)
    declared_projector = np.outer(declared_psi, declared_psi.conj())

    def gauge_aligned_error(psi: np.ndarray) -> float:
        overlap = np.vdot(declared_psi, psi)
        if abs(overlap) == 0.0:
            return float(np.linalg.norm(psi - declared_psi))
        aligned = psi * np.exp(-1j * np.angle(overlap))
        return float(np.linalg.norm(aligned - declared_psi))

    return {
        "definition_sha256": hashlib.sha256(definition_bytes).hexdigest(),
        "exact_definition": exact_definition,
        "maximum_probability_variation": float(
            max(np.max(np.abs(state.p - states[0].p)) for state in states)
        ),
        "maximum_phase_variation": float(
            max(np.max(np.abs(state.theta - states[0].theta)) for state in states)
        ),
        "maximum_normalized_psi_variation": float(max(np.max(np.abs(psi - psis[0])) for psi in psis)),
        "psi_norm_error": float(max(abs(np.linalg.norm(psi) - 1.0) for psi in psis)),
        "maximum_executed_p_to_declared_error": float(
            max(np.max(np.abs(state.p - declared_p)) for state in states)
        ),
        "maximum_executed_theta_to_declared_error": float(
            max(np.max(np.abs(state.theta - declared_theta)) for state in states)
        ),
        "maximum_executed_psi_to_declared_gauge_aligned_error": max(gauge_aligned_error(psi) for psi in psis),
        "maximum_executed_projector_to_declared_error": float(
            max(np.linalg.norm(np.outer(psi, psi.conj()) - declared_projector, ord=2) for psi in psis)
        ),
        "omega_bd_exact_fraction": "0/1",
        "omega_reason": "constant normalized projective reference has exact zero derivatives",
        "authored_stationary_probability_used_as_projective_branch": False,
        "channel_equivalence_error": authored_probability_inactivity(),
    }


def affine_population_components(
    bias: float,
    diffusion: float,
    contract: ModelContract = MODEL_CONTRACT,
) -> tuple[np.ndarray, np.ndarray]:
    """Return ``x' = M x + c`` for the invariant diagonal density subspace."""

    kernel = analytic_d0_kernel(bias, diffusion)
    jump = float(contract.jump_probability_scale)
    transition = (1.0 - jump) * np.eye(contract.node_count) + jump * kernel
    contraction = float(contract.contraction_factor)
    matrix = contraction * transition.T
    offset = np.full(contract.node_count, float(contract.depolarizing_floor), dtype=float)
    return matrix, offset


def affine_population_step(
    population: np.ndarray,
    bias: float,
    diffusion: float,
    contract: ModelContract = MODEL_CONTRACT,
) -> np.ndarray:
    """Apply the exact diagonal affine reduction."""

    matrix, offset = affine_population_components(bias, diffusion, contract)
    return matrix @ np.asarray(population, dtype=float) + offset


def raw_core_step(
    rho: np.ndarray,
    state: BranchState,
    config: OpenSystemConfig,
    dephasing: float,
) -> np.ndarray:
    """Evaluate the core Kraus/depolarizing expression before numerical projection."""

    updated = np.zeros_like(rho, dtype=complex)
    for operator in local_kraus_operators(state, config, dephasing):
        updated += operator @ rho @ operator.conj().T
    if config.depolarizing > 0.0:
        n = rho.shape[0]
        updated = (1.0 - config.depolarizing) * updated + config.depolarizing * np.eye(n) / n
    return updated


def core_affine_equivalence() -> dict[str, float]:
    """Cross-check kernels, Kraus output, projection inactivity, and fixed-point API."""

    contract = MODEL_CONTRACT
    config = core_config(contract)
    grid = (
        (float(contract.box.bias_min), float(contract.box.diffusion_min)),
        (float(contract.box.bias_min), float(contract.box.diffusion_max)),
        (float(contract.box.bias_max), float(contract.box.diffusion_min)),
        (float(contract.box.bias_max), float(contract.box.diffusion_max)),
        (float(contract.center_bias), float(contract.center_diffusion)),
    )
    populations = (
        np.full(5, 0.2),
        np.asarray((0.40, 0.10, 0.20, 0.15, 0.15)),
        np.asarray((0.05, 0.20, 0.25, 0.30, 0.20)),
    )
    max_kernel_error = 0.0
    max_affine_error = 0.0
    max_projection_delta = 0.0
    max_tp_error = 0.0
    max_fixed_api_error = 0.0
    for bias, diffusion in grid:
        authored_state = core_d0_state(bias, diffusion)
        state = theorem_d0_state(bias, diffusion)
        max_kernel_error = max(
            max_kernel_error,
            float(np.max(np.abs(authored_state.kernel - state.kernel))),
        )
        kraus = local_kraus_operators(state, config, float(contract.dephasing))
        completeness = sum((op.conj().T @ op for op in kraus), np.zeros((5, 5), dtype=complex))
        max_tp_error = max(max_tp_error, float(np.linalg.norm(completeness - np.eye(5), ord=2)))
        for population in populations:
            rho = np.diag(population).astype(complex)
            raw = raw_core_step(rho, state, config, float(contract.dephasing))
            projected = apply_local_open_step(rho, state, config, float(contract.dephasing))
            affine = affine_population_step(population, bias, diffusion, contract)
            max_affine_error = max(
                max_affine_error,
                float(np.max(np.abs(np.diag(raw).real - affine))),
                float(np.linalg.norm(raw - np.diag(np.diag(raw)), ord="fro")),
            )
            max_projection_delta = max(
                max_projection_delta,
                float(np.linalg.norm(projected - raw, ord="fro")),
            )
        matrix, offset = affine_population_components(bias, diffusion, contract)
        solved = np.linalg.solve(np.eye(5) - matrix, offset)
        core_fixed = fixed_point_density(state, config, float(contract.dephasing))
        max_fixed_api_error = max(
            max_fixed_api_error,
            float(np.linalg.norm(core_fixed - np.diag(solved), ord="fro")),
        )
    return {
        "max_kernel_error": max_kernel_error,
        "max_affine_error": max_affine_error,
        "max_projection_delta": max_projection_delta,
        "max_kraus_tp_error": max_tp_error,
        "max_fixed_point_api_error": max_fixed_api_error,
    }


def authored_probability_inactivity() -> float:
    """Show that suppressed Hamiltonian/site terms make authored ``p`` irrelevant here."""

    contract = MODEL_CONTRACT
    bias, diffusion = float(contract.center_bias), float(contract.center_diffusion)
    state = theorem_d0_state(bias, diffusion)
    altered = BranchState(
        p=np.asarray((0.04, 0.11, 0.19, 0.27, 0.39)),
        theta=np.zeros(5),
        kernel=state.kernel.copy(),
        extras=dict(state.extras),
    )
    rho = np.diag(np.asarray((0.05, 0.20, 0.25, 0.30, 0.20))).astype(complex)
    config = core_config(contract)
    left = raw_core_step(rho, state, config, float(contract.dephasing))
    right = raw_core_step(rho, altered, config, float(contract.dephasing))
    return float(np.linalg.norm(left - right, ord="fro"))


def benchmark_d_three_step_diagnostics() -> dict[str, float | int | str]:
    """Quantify a separate Benchmark-D three-step diagnostic, not Phase 10."""

    contract = MODEL_CONTRACT
    state = core_d0_state(float(contract.center_bias), float(contract.center_diffusion))
    config = core_config(contract)
    surrogate = effective_branch_density(state, config, float(contract.dephasing))
    advanced = apply_local_open_step(surrogate, state, config, float(contract.dephasing))
    true_fixed = fixed_point_density(state, config, float(contract.dephasing))
    return {
        "benchmark_id": "benchmark_d",
        "branch_id": "D0",
        "branch_steps": config.branch_steps,
        "surrogate_fixed_residual_fro": float(np.linalg.norm(advanced - surrogate, ord="fro")),
        "surrogate_to_true_fixed_fro": float(np.linalg.norm(surrogate - true_fixed, ord="fro")),
        "relationship_to_tracked_phase10": "separate_diagnostic_not_validation",
    }


def phase10_benchmark_c_two_step_diagnostics() -> dict[str, object]:
    """Recompute the tracked Phase10 two-step Benchmark-C surrogate limitation."""

    payload = json.loads(PHASE10_ARTIFACT_PATH.read_text(encoding="utf-8"))
    recorded = payload["open_system_config"]
    gamma = float(payload["recommended_mixed_state_switch_gamma"])
    config = OpenSystemConfig(
        dt=float(recorded["dt"]),
        coherent_scale=float(recorded["coherent_scale"]),
        edge_jump_scale=float(recorded["edge_jump_scale"]),
        site_potential_scale=float(recorded["site_potential_scale"]),
        depolarizing=float(recorded["depolarizing"]),
        branch_steps=int(recorded["branch_steps"]),
        fixed_point_max_iter=int(recorded["fixed_point_max_iter"]),
        fixed_point_tol=float(recorded["fixed_point_tol"]),
    )
    benchmark = get_benchmark("benchmark_c")
    candidate = benchmark.resolve_candidate_by_id(0.0, 0.0, "C0")
    if candidate is None:
        raise AssertionError("Benchmark C C0 disappeared at the Phase10 diagnostic center")
    state = candidate.state
    surrogate = effective_branch_density(state, config, gamma)
    advanced = apply_local_open_step(surrogate, state, config, gamma)
    true_fixed = fixed_point_density(state, config, gamma)
    return {
        "tracked_artifact": PHASE10_ARTIFACT_PATH.relative_to(SIM_ROOT).as_posix(),
        "historical_entry_script": PHASE10_HISTORICAL_ENTRY_PATH.relative_to(SIM_ROOT).as_posix(),
        "current_recomputation_implementation": PHASE10_CURRENT_IMPLEMENTATION_PATH.relative_to(
            SIM_ROOT
        ).as_posix(),
        "benchmark_id": payload["benchmark"],
        "branch_id": "C0",
        "center": [0.0, 0.0],
        "recorded_branch_steps": int(recorded["branch_steps"]),
        "historical_entry_explicit_branch_steps": (
            2 if "branch_steps=2" in PHASE10_HISTORICAL_ENTRY_PATH.read_text(encoding="utf-8") else None
        ),
        "current_library_default_branch_steps": OpenSystemConfig().branch_steps,
        "recorded_dephasing_gamma": gamma,
        "recorded_open_system_config": recorded,
        "surrogate_fixed_residual_fro": float(np.linalg.norm(advanced - surrogate, ord="fro")),
        "surrogate_to_true_fixed_fro": float(np.linalg.norm(surrogate - true_fixed, ord="fro")),
        "historical_provenance_claim": "tracked_config_bound_recomputation_not_original_run_proof",
    }


def config_without_depolarizing() -> OpenSystemConfig:
    """Return the exact counterfactual config used only for refusal testing."""

    return replace(core_config(), depolarizing=0.0)
