"""Fail-closed exact theorem orchestrator for the one-chord model."""

from __future__ import annotations

from dataclasses import asdict
from fractions import Fraction

from .contract import (
    CASE_GATE_MAP,
    EXPECTED_CASE_DISPOSITIONS,
    MODEL_CONTRACT,
    ORDERED_GATES,
    canonical_bytes,
    contract_issues,
    record_digest_issues,
    registry_issues,
    sha256_record,
)
from .counting_lane import counting_record, fcs_record, null_record
from .exact import (
    IMAG_UNIT,
    ONE,
    ZERO,
    Matrix,
    conjugate_transpose,
    matrix_multiply,
    matrix_subtract,
    matrix_vector,
    trace,
    unvec,
    vec,
    zeros,
)
from .firewall import authenticated_role_sources
from .generator import N, branch_bundle, d0_kernel, hamiltonian, trace_row
from .geometry_lane import floor_record, flux_conjugation_record, flux_record, geometry_record
from .oracle_lane import exact_oracle_record
from .pipeline import REVIEWED_CRITERION, PipelineSession


def _authored_rhs(rho: Matrix) -> Matrix:
    """Independent matrix-action evaluation of the frozen Lindblad RHS."""

    bias, diffusion, t = MODEL_CONTRACT.center
    h = hamiltonian(diffusion, t)
    result = matrix_subtract(
        matrix_multiply(h, rho),
        matrix_multiply(rho, h),
    )
    result = [[-IMAG_UNIT * item for item in row] for row in result]
    kernel = d0_kernel(bias, diffusion)
    for source in range(N):
        for destination in range(N):
            if source == destination:
                continue
            rate = MODEL_CONTRACT.edge_rate * kernel[source][destination]
            result[destination][destination] += rate * rho[source][source]
            for column in range(N):
                result[source][column] -= rate * rho[source][column] / 2
            for row in range(N):
                result[row][source] -= rate * rho[row][source] / 2
    for site in range(N):
        rate = MODEL_CONTRACT.dephasing_rate
        result[site][site] += rate * rho[site][site]
        for column in range(N):
            result[site][column] -= rate * rho[site][column] / 2
        for row in range(N):
            result[row][site] -= rate * rho[row][site] / 2
    state_trace = trace(rho)
    for row in range(N):
        for column in range(N):
            result[row][column] -= MODEL_CONTRACT.depolarizing_rate * rho[row][column]
        result[row][row] += MODEL_CONTRACT.depolarizing_rate * state_trace / N
    return result


def _generator_record() -> dict[str, object]:
    bundle = branch_bundle()
    h = hamiltonian(MODEL_CONTRACT.center[1], MODEL_CONTRACT.center[2])
    basis_equal = []
    for row in range(N):
        for column in range(N):
            basis = zeros(N, N)
            basis[row][column] = ONE
            observed = [bundle.generator[out][row + N * column] for out in range(N * N)]
            basis_equal.append(observed == vec(_authored_rhs(basis)))
    trace_preserving = all(
        sum(
            (trace_row()[row] * bundle.generator[row][column] for row in range(N * N)),
            ZERO,
        ).is_zero()
        for column in range(N * N)
    )
    return {
        "authority": "exact_labeled_channel_construction_and_independent_basis_action",
        "generator_sha256": sha256_record(bundle.generator),
        "Hamiltonian_sha256": sha256_record(h),
        "Hamiltonian_hermitian": h == conjugate_transpose(h),
        "trace_linear_reset_source_included": True,
        "trace_preserving": trace_preserving,
        "complete_matrix_basis_count": N * N,
        "complete_matrix_basis_RHS_equal": all(basis_equal),
        "path_jump_channels_only": True,
        "coherent_chord_only_0_2": True,
        "all_box_jump_rates_nonnegative": (
            MODEL_CONTRACT.d_bounds[0] - MODEL_CONTRACT.b_bounds[1] > 0
            and MODEL_CONTRACT.d_bounds[0] + MODEL_CONTRACT.b_bounds[0] > 0
        ),
        "core_lindblad_superoperator_used_as_acceptance": False,
        "Euler_or_projection_branch_used": False,
        "unlabeled_zip_channels_used": False,
    }


def _branch_record() -> dict[str, object]:
    bundle = branch_bundle()
    rho = unvec(bundle.stationary, N)
    from .generator import derivative_identities, drazin_identities

    return {
        "authority": "exact_stationary_solve_group_inverse_and_parameter_derivatives",
        "stationary_sha256": sha256_record(bundle.stationary),
        "Drazin_sha256": sha256_record(bundle.drazin),
        "tangents_sha256": sha256_record(bundle.tangents),
        "second_tangents_sha256": sha256_record(bundle.second_tangents),
        "Drazin_derivatives_sha256": sha256_record(bundle.drazin_derivatives),
        "stationary_residual_zero": all(
            item.is_zero() for item in matrix_vector(bundle.generator, bundle.stationary)
        ),
        "stationary_trace_one": trace(rho).real == 1 and trace(rho).imag == 0,
        "stationary_hermitian": rho == conjugate_transpose(rho),
        "Drazin_identities": drazin_identities(bundle),
        "derivative_identities": derivative_identities(bundle),
        "actual_branch_only": True,
        "iterative_or_auxiliary_branch_used": False,
    }


def _pipeline_record() -> dict[str, object]:
    session = PipelineSession()
    lock = session.lock_prediction(REVIEWED_CRITERION)
    capability = session.capability()
    oracle = exact_oracle_record(capability)
    session.accept_oracle(capability, oracle)
    session.verify()
    record = session.record()
    record["prediction_lock_sha256"] = sha256_record(asdict(lock))
    record["authenticated_role_sources"] = authenticated_role_sources()
    return record


def _scope_record(
    geometry: dict[str, object],
    counting: dict[str, object],
) -> dict[str, object]:
    omega = geometry["mean_Uhlmann_vector"]
    response = counting["direct_response_curl"]
    assert type(omega) is tuple and type(response) is tuple
    minor = response[0] * omega[1] - response[1] * omega[0]
    return {
        "classification": MODEL_CONTRACT.classification,
        "both_curvatures_nonzero": all(item != 0 for item in omega) and all(item != 0 for item in response),
        "exact_noncollinearity_minor": minor,
        "exact_noncollinearity_minor_nonzero": minor != 0,
        "dt_requires_positive_kappa": omega[0] < 0 and response[0] < 0,
        "tb_requires_negative_kappa": omega[1] > 0 and response[1] < 0,
        "same_curvature_refuted": response != omega,
        "finite_scalar_kappa_refuted": minor != 0,
        "generic_linear_map_refuted": False,
        "affine_map_refuted": False,
        "nonlinear_map_refuted": False,
        "generator_dependent_map_open": True,
        "heldout_prediction_claimed": False,
        "one_center_is_calibration_counterexample_not_holdout": True,
        "future_positive_protocol": (
            "predeclared covariant tensor law; >=3 independent calibration Omega vectors and preferably "
            ">=4 centers; conditioning/nonzero gates; fresh uninspected rational center plus "
            "oblique bivector; "
            "sealed response oracle; K_-j=-K_j, K_0=0, d(K Omega)=0"
        ),
        "units": {
            "b_d_t_q": "dimensionless",
            "W_and_J": "inverse_model_time",
            "Drazin_R": "model_time",
            "B": "count_per_control",
            "F": "count_per_control_area",
            "Omega": "dimensionless_per_control_area",
        },
        "phase_chart_dphi_dt_center": Fraction(8, 5),
        "cartesian_chord_jacobian_dt": geometry["cartesian_chord_jacobian_dt"],
        "cartesian_geometry_pullback_equal": geometry["cartesian_to_t_mean_Uhlmann_pullback_equal"],
        "cartesian_response_pullback_equal": counting["cartesian_to_t_response_pullback_equal"],
        "cartesian_geometry_and_response_jacobians_equal": (
            geometry["cartesian_chord_jacobian_dt"] == counting["cartesian_response"]["chord_jacobian_dt"]
        ),
        "local_curvature_definition": "F_equals_dB_at_the_reviewed_center_from_exact_branch_jets",
        "third_jet_or_dF_closure_claimed": False,
        "global_Chern_or_graph_topology_claimed": False,
        "finite_time_or_O1_over_T_claimed": False,
        "claim_ceiling": MODEL_CONTRACT.claim_ceiling,
        "disposition": MODEL_CONTRACT.disposition,
        "evidence_status": MODEL_CONTRACT.evidence_status,
        "relation_scope": MODEL_CONTRACT.relation_scope,
        "provenance_authority": {
            "schema": "fresh_index_process_publication_authority_v1",
            "authority": ("fresh_OS_process_from_exact_index_materialized_checkout_plus_outer_staged_audit"),
            "exact_index_materialized_checkout_required": True,
            "explicit_absolute_GIT_DIR_required": True,
            "explicit_absolute_GIT_INDEX_FILE_required": True,
            "explicit_absolute_GIT_WORK_TREE_required": True,
            "checkout_contains_dot_git": False,
            "python_isolated_flag": "-I",
            "python_user_site_enabled": False,
            "trusted_absolute_git_executable_required": True,
            "trusted_absolute_python_executable_required": True,
            "git_replace_objects_enabled": False,
            "post_generation_fresh_CLI_verify_required": True,
            "outer_staged_index_audit_is_publication_authority": True,
            "in_process_helpers_authoritative": False,
            "in_process_runner_identity_checks": "defense_in_depth_diagnostics_only",
            "arbitrary_process_memory_syscall_binary_or_admin_compromise": "outside_claimed_boundary",
        },
    }


def build_records() -> dict[str, object]:
    geometry = dict(geometry_record())
    counting = dict(counting_record())
    bundle = branch_bundle()
    binding = {
        "generator_sha256": sha256_record(bundle.generator),
        "stationary_sha256": sha256_record(bundle.stationary),
        "tangents_sha256": sha256_record(bundle.tangents),
    }
    geometry["shared_branch_binding"] = binding
    counting["shared_branch_binding"] = binding
    fcs = dict(fcs_record())
    fcs["shared_branch_binding"] = binding
    pipeline = _pipeline_record()
    oracle = pipeline["oracle"]
    assert type(oracle) is dict
    pipeline["shared_branch_binding"] = binding
    return {
        "contract": asdict(MODEL_CONTRACT),
        "generator": _generator_record(),
        "flux": flux_record(),
        "floor": floor_record(),
        "branch": _branch_record(),
        "geometry": geometry,
        "counting": counting,
        "fcs": fcs,
        "nulls": {**null_record(), "flux_conjugation": flux_conjugation_record()},
        "pipeline": pipeline,
        "scope": _scope_record(geometry, counting),
    }


def natural_gate_results(records: dict[str, object]) -> dict[str, bool]:
    generator = records["generator"]
    flux = records["flux"]
    floor = records["floor"]
    branch = records["branch"]
    geometry = records["geometry"]
    counting = records["counting"]
    fcs = records["fcs"]
    nulls = records["nulls"]
    pipeline = records["pipeline"]
    scope = records["scope"]
    assert all(
        type(item) is dict
        for item in (generator, flux, floor, branch, geometry, counting, fcs, nulls, pipeline, scope)
    )
    expected_floor = floor["expected_exact_values"]
    assert type(expected_floor) is dict
    role_sources = pipeline["authenticated_role_sources"]
    oracle = pipeline["oracle"]
    assert type(role_sources) is dict and type(oracle) is dict
    direct_B = counting.get("direct_response_one_form")
    direct_F = counting.get("direct_response_curl")
    fcs_B = fcs.get("fcs_minus_partial_q_connection_one_form")
    fcs_F = fcs.get("fcs_normal_connection_curl")
    oracle_B = oracle.get("B")
    oracle_F = oracle.get("F")
    direct_order = counting.get("direct_response_curl_order")
    fcs_order = fcs.get("fcs_normal_connection_curl_order")
    direct_signs = counting.get("direct_response_curl_signs")
    fcs_signs = fcs.get("fcs_normal_connection_curl_signs")
    expected_order = MODEL_CONTRACT.two_form_vector_order
    expected_signs = (-1, -1, -1)
    exact_direct_B = (
        type(direct_B) is tuple and len(direct_B) == 3 and all(type(item) is Fraction for item in direct_B)
    )
    exact_direct_F = (
        type(direct_F) is tuple and len(direct_F) == 3 and all(type(item) is Fraction for item in direct_F)
    )
    exact_fcs_B = type(fcs_B) is tuple and len(fcs_B) == 3 and all(type(item) is Fraction for item in fcs_B)
    exact_fcs_F = type(fcs_F) is tuple and len(fcs_F) == 3 and all(type(item) is Fraction for item in fcs_F)
    exact_oracle_B = (
        type(oracle_B) is tuple and len(oracle_B) == 3 and all(type(item) is Fraction for item in oracle_B)
    )
    exact_oracle_F = (
        type(oracle_F) is tuple and len(oracle_F) == 3 and all(type(item) is Fraction for item in oracle_F)
    )
    exact_direct_order = (
        type(direct_order) is tuple
        and len(direct_order) == 3
        and all(type(item) is str for item in direct_order)
        and direct_order == expected_order
    )
    exact_fcs_order = (
        type(fcs_order) is tuple
        and len(fcs_order) == 3
        and all(type(item) is str for item in fcs_order)
        and fcs_order == expected_order
    )
    exact_direct_signs = (
        type(direct_signs) is tuple
        and len(direct_signs) == 3
        and all(type(item) is int for item in direct_signs)
        and direct_signs == expected_signs
    )
    exact_fcs_signs = (
        type(fcs_signs) is tuple
        and len(fcs_signs) == 3
        and all(type(item) is int for item in fcs_signs)
        and fcs_signs == expected_signs
    )
    results = {
        "G0_exact_config": not contract_issues(),
        "G1_generator_source_identity": (
            generator["Hamiltonian_hermitian"] is True
            and generator["trace_linear_reset_source_included"] is True
            and generator["trace_preserving"] is True
            and generator["complete_matrix_basis_count"] == 25
            and generator["complete_matrix_basis_RHS_equal"] is True
            and generator["all_box_jump_rates_nonnegative"] is True
            and generator["core_lindblad_superoperator_used_as_acceptance"] is False
            and generator["Euler_or_projection_branch_used"] is False
        ),
        "G2_flux_and_gauge_covariance": (
            flux["radius_squared"] == Fraction(1, 400)
            and flux["center_z"] == flux["center_expected_z"]
            and flux["center_z_t"] == flux["center_expected_z_t"]
            and flux["center_z_tt"] == flux["center_expected_z_tt"]
            and flux["Wilson_H10_H21_H02"] == flux["Wilson_expected"]
            and flux["matrix_index_convention"] == "H_destination_source"
            and flux["oriented_cycle"] == "0_to_1_to_2_to_0"
            and flux["loop_orientation"] == (0, 1, 2, 0)
            and flux["reverse_is_conjugate"] is True
            and flux["box_imaginary_flux_positive"] is True
            and flux["diagonal_gauge_exponent_coefficients"] == (0, 0, 0, 0, 0)
            and flux["diagonal_gauge_exponents_cancel"] is True
            and flux["constant_diagonal_gauge_Wilson_equal"] is True
            and flux["node_theta_coboundary_used"] is False
        ),
        "G3_branch_floor_and_gap": (
            floor["minimum_forward_rate"] == Fraction(43, 1000)
            and floor["minimum_reverse_rate"] == Fraction(31, 1000)
            and floor["induced_operator_norm_budget"] == Fraction(1991, 500)
            and floor["series_parameter"] == Fraction(1991, 20000)
            and floor["exp_minus_one_majorant"] == Fraction(1991, 18009)
            and floor["spectral_distance_from_identity_over_five"] == Fraction(1991, 90045)
            and floor["pointwise_floor"] == Fraction(16018, 90045)
            and floor["pointwise_floor_above_three_twentieths"] is True
            and floor["stationary_full_rank_floor"] == Fraction(2997, 20_000_000)
            and floor["trace_norm_contraction_rate"] == Fraction(1, 25)
            and floor["Drazin_trace_norm_bound"] == 25
            and expected_floor["stationary_floor"] == floor["stationary_full_rank_floor"]
        ),
        "G4_drazin_derivatives_and_rank": (
            branch["stationary_residual_zero"] is True
            and branch["stationary_trace_one"] is True
            and branch["stationary_hermitian"] is True
            and all(branch["Drazin_identities"].values())
            and all(branch["derivative_identities"].values())
            and geometry["tangent_Gram_determinant"] > 0
            and geometry["SLD_metric_determinant"] > 0
            and branch["actual_branch_only"] is True
        ),
        "G5_sld_mean_uhlmann_curvature": (
            geometry["stationary_hermitian"] is True
            and geometry["tangents_hermitian"] is True
            and geometry["SLDs_hermitian"] is True
            and geometry["tangent_traces_zero"] is True
            and geometry["mean_Uhlmann_signs"] == (-1, 1, -1)
            and geometry["all_mean_Uhlmann_components_nonzero"] is True
            and geometry["constant_diagonal_gauge_metric_equal"] is True
            and geometry["constant_diagonal_gauge_curvature_equal"] is True
            and geometry["cartesian_quadrature_pullback_Wt_equal"] is True
            and geometry["cartesian_to_t_mean_Uhlmann_pullback_equal"] is True
        ),
        "G6_counting_and_fcs_identity": (
            counting["forward_gain_rate"] == Fraction(51, 1000)
            and counting["reverse_gain_rate"] == Fraction(39, 1000)
            and counting["first_q_jet_only_counted_gains"] is True
            and counting["losses_unchanged_by_q"] is True
            and counting["current_equals_trace_q_jet"] is True
            and exact_direct_order
            and exact_direct_signs
            and counting["all_direct_response_curl_components_nonzero"] is True
            and fcs["fcs_left_q_eigenvector_equation"] is True
            and fcs["fcs_right_q_eigenvector_equation"] is True
            and fcs["fcs_left_q_gauge"] is True
            and fcs["fcs_right_q_gauge"] is True
            and exact_fcs_order
            and exact_fcs_signs
            and exact_direct_B
            and exact_direct_F
            and exact_fcs_B
            and exact_fcs_F
            and exact_oracle_B
            and exact_oracle_F
            and fcs_B == direct_B
            and fcs_B is not direct_B
            and fcs_F == direct_F
            and fcs_F is not direct_F
            and oracle_B == direct_B
            and oracle_B is not direct_B
            and oracle_B is not fcs_B
            and oracle_F == direct_F
            and oracle_F is not direct_F
            and oracle_F is not fcs_F
        ),
        "G7_scalar_noncollinearity_obstruction": (
            scope["both_curvatures_nonzero"] is True
            and scope["exact_noncollinearity_minor_nonzero"] is True
            and scope["dt_requires_positive_kappa"] is True
            and scope["tb_requires_negative_kappa"] is True
            and scope["finite_scalar_kappa_refuted"] is True
        ),
        "G8_covariance_units_and_local_curvature": (
            scope["phase_chart_dphi_dt_center"] == Fraction(8, 5)
            and scope["cartesian_chord_jacobian_dt"]
            == (
                Fraction(-8, 125),
                Fraction(6, 125),
            )
            and scope["cartesian_geometry_pullback_equal"] is True
            and scope["cartesian_response_pullback_equal"] is True
            and scope["cartesian_geometry_and_response_jacobians_equal"] is True
            and geometry["cartesian_mean_Uhlmann_antisymmetric"] is True
            and counting["cartesian_response"]["response_curvature_antisymmetric"] is True
            and scope["local_curvature_definition"]
            == "F_equals_dB_at_the_reviewed_center_from_exact_branch_jets"
            and scope["third_jet_or_dF_closure_claimed"] is False
            and scope["global_Chern_or_graph_topology_claimed"] is False
            and scope["finite_time_or_O1_over_T_claimed"] is False
        ),
        "G9_reverse_count_and_null_controls": (
            nulls["reverse_count_negates_B"] is True
            and nulls["reverse_count_negates_F"] is True
            and nulls["zero_current_B_and_F_zero"] is True
            and nulls["zero_current_operator_constructed_independently"] is True
            and nulls["zero_current_response_recomputed"] is True
            and nulls["zero_chord_t_tangent_zero"] is True
            and nulls["zero_chord_t_response_zero"] is True
            and nulls["zero_chord_t_curvature_components_zero"] is True
            and nulls["flux_conjugation"]["Wilson_flux_reversed"] is True
            and nulls["flux_conjugation"]["componentwise_oddness_assumed"] is False
        ),
        "G10_lane_firewalls_and_lock": (
            pipeline["state"] == "VERIFIED"
            and pipeline["event_log_exact"] is True
            and pipeline["general_map_or_heldout_requested"] is False
            and oracle["prediction_or_geometry_payload_received"] is False
            and all(record["authenticated"] is True for record in role_sources.values())
            and len({item["sha256_utf8_lf"] for item in role_sources.values()}) == 3
        ),
        "G11_general_map_refusal": (
            scope["generic_linear_map_refuted"] is False
            and scope["affine_map_refuted"] is False
            and scope["nonlinear_map_refuted"] is False
            and scope["generator_dependent_map_open"] is True
            and scope["heldout_prediction_claimed"] is False
            and scope["one_center_is_calibration_counterexample_not_holdout"] is True
        ),
        "G12_provenance_registry_and_claim_ceiling": (
            not registry_issues()
            and scope["claim_ceiling"] == MODEL_CONTRACT.claim_ceiling
            and scope["disposition"] == "PASS_INTERNAL_ANALYTIC"
            and scope["evidence_status"] == "NO_EMPIRICAL_EVIDENCE"
            and scope["relation_scope"] == "MODEL_SPECIFIC_RELATIONS_ONLY"
            and scope["provenance_authority"]
            == {
                "schema": "fresh_index_process_publication_authority_v1",
                "authority": (
                    "fresh_OS_process_from_exact_index_materialized_checkout_plus_outer_staged_audit"
                ),
                "exact_index_materialized_checkout_required": True,
                "explicit_absolute_GIT_DIR_required": True,
                "explicit_absolute_GIT_INDEX_FILE_required": True,
                "explicit_absolute_GIT_WORK_TREE_required": True,
                "checkout_contains_dot_git": False,
                "python_isolated_flag": "-I",
                "python_user_site_enabled": False,
                "trusted_absolute_git_executable_required": True,
                "trusted_absolute_python_executable_required": True,
                "git_replace_objects_enabled": False,
                "post_generation_fresh_CLI_verify_required": True,
                "outer_staged_index_audit_is_publication_authority": True,
                "in_process_helpers_authoritative": False,
                "in_process_runner_identity_checks": "defense_in_depth_diagnostics_only",
                "arbitrary_process_memory_syscall_binary_or_admin_compromise": "outside_claimed_boundary",
            }
            and not record_digest_issues(records)
        ),
    }
    return results


def execute_program(
    *,
    gate_overrides: dict[str, bool] | None = None,
) -> tuple[dict[str, object], dict[str, object]]:
    records = build_records()
    natural = natural_gate_results(records)
    if tuple(natural) != ORDERED_GATES:
        raise RuntimeError("live gates differ from reviewed order")
    overrides = {} if gate_overrides is None else gate_overrides
    unknown = set(overrides) - set(ORDERED_GATES)
    if unknown:
        raise ValueError(f"unknown gate overrides: {sorted(unknown)}")
    if any(type(value) is not bool for value in overrides.values()):
        raise TypeError("gate overrides must be exact booleans")
    gates = {name: bool(natural[name] and overrides.get(name, True)) for name in ORDERED_GATES}
    cases = {
        name: {
            "status": "PASS" if all(gates[gate] for gate in owned) else "FAIL",
            "natural_status": "PASS" if all(natural[gate] for gate in owned) else "FAIL",
            "gates": owned,
        }
        for name, owned in CASE_GATE_MAP.items()
    }
    all_pass = all(gates.values()) and all(
        item["status"] == EXPECTED_CASE_DISPOSITIONS[name] for name, item in cases.items()
    )
    record_sha256: dict[str, str] = {}
    for name, value in records.items():
        try:
            record_sha256[name] = sha256_record(value)
        except (TypeError, ValueError, OverflowError):
            record_sha256[name] = "NONCANONICAL"
    summary = {
        "experiment_id": MODEL_CONTRACT.experiment_id,
        "status": "PASS" if all_pass else "FAIL",
        "disposition": MODEL_CONTRACT.disposition if all_pass else "FAIL_INTERNAL_ANALYTIC",
        "evidence_status": MODEL_CONTRACT.evidence_status,
        "relation_scope": MODEL_CONTRACT.relation_scope,
        "classification": MODEL_CONTRACT.classification,
        "claim_ceiling": MODEL_CONTRACT.claim_ceiling,
        "gates": gates,
        "natural_gates": natural,
        "failed_gates": [name for name, value in gates.items() if not value],
        "cases": cases,
        "record_sha256": record_sha256,
    }
    return summary, records


def semantic_issues(summary: object, records: object) -> list[str]:
    if type(summary) is not dict or type(records) is not dict:
        return ["summary and records must be exact mappings"]
    expected_summary, expected_records = execute_program()
    issues = []
    try:
        if canonical_bytes(summary) != canonical_bytes(expected_summary):
            issues.append("summary differs from semantic recomputation")
        if canonical_bytes(records) != canonical_bytes(expected_records):
            issues.append("records differ from semantic recomputation")
    except (TypeError, ValueError, OverflowError) as exc:
        issues.append(f"noncanonical semantic payload: {exc}")
    if summary.get("status") != "PASS" or summary.get("disposition") != "PASS_INTERNAL_ANALYTIC":
        issues.append("semantic status is not PASS_INTERNAL_ANALYTIC")
    return issues


def require_semantic_pass(summary: object, records: object) -> None:
    issues = semantic_issues(summary, records)
    if issues:
        raise RuntimeError("; ".join(issues))
