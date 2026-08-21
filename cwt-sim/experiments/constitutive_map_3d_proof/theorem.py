"""Orchestrate the two exact 3D cases and derive every disposition."""

from __future__ import annotations

import json
from dataclasses import replace
from fractions import Fraction
from functools import lru_cache
from typing import Any, Mapping

import numpy as np

from .bc3_core_regression import authored_predecessor_identity
from .bc3_midpoint_prediction import locked_midpoint_predictions
from .bc3_remainder import assess_oracle_enclosures, exact_remainder_certificate
from .benchmark_c_alpha import (
    directed_form_intervals,
    factorization_certificate,
    line_integral_beta,
)
from .classifier import apply_fail_only_overrides, case_dispositions, registry_gate_names
from .contract import (
    MODEL_CONTRACT,
    ConstitutiveMap3DContract,
    canonical_registry_record,
    contract_issues,
    expected_case_dispositions,
)
from .exact import strict_cross
from .firewall import reviewed_role_path_set, source_authentication_records
from .pipeline import PipelineSession, PredictionAccess
from .qp1_geometry import curvature_tensor, geometry_certificate
from .qp1_kubo import kubo_certificate, spectral_kubo_tensor
from .response_oracle import ladder_certificate, parallelogram_controls


def _jsonable(value: Any) -> Any:
    """Convert analytic records to strict JSON without discarding complex components."""

    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if isinstance(value, np.ndarray):
        return _jsonable(value.tolist())
    if isinstance(value, np.generic):
        return _jsonable(value.item())
    if isinstance(value, complex):
        return {"real": float(value.real), "imag": float(value.imag)}
    if isinstance(value, Fraction):
        return {
            "fraction": f"{value.numerator}/{value.denominator}",
            "numerator": value.numerator,
            "denominator": value.denominator,
            "float": float(value),
        }
    return value


def _conjunctive_status(*values: bool | None) -> bool | None:
    if any(value is False for value in values):
        return False
    if any(value is None for value in values):
        return None
    return True


def publication_disposition(
    formal_disposition: str,
    diagnostic_status: str,
) -> tuple[str, list[str]]:
    """Block publication on engineering drift without rewriting the formal theorem result."""

    if formal_disposition != MODEL_CONTRACT.disposition:
        return formal_disposition, []
    if diagnostic_status != "PASS_NONAUTHORITATIVE_REGRESSION":
        return "BLOCKED_DIAGNOSTIC_DRIFT", ["bc3_scalar_non_authoritative_diagnostic"]
    return formal_disposition, []


def refusal_certificate(contract: ConstitutiveMap3DContract = MODEL_CONTRACT) -> dict[str, object]:
    refused = {
        "two_dimensional_pointwise_quotient": not contract.pointwise_fit_allowed,
        "P1_beta_equals_two_A_circular_oracle": True,
        "gain_or_readout_scaling_as_third_control": not contract.gain_as_control_allowed,
        "private_tilt_or_chirality_branch_knobs": not contract.auxiliary_branch_allowed,
        "auxiliary_or_finite_step_branch": not contract.auxiliary_branch_allowed,
        "geometry_fed_response": not contract.geometry_fed_response_allowed,
        "heldout_response_or_identifier_leakage": not contract.heldout_response_fit_allowed,
        "arbitrary_response_tensor_fit": not contract.pointwise_fit_allowed,
        "same_center_basis_then_oblique_pseudoholdout": True,
        "forged_status_claim_or_registry": True,
        "universal_full_cwt_physical_or_empirical_upgrade": not contract.universal_claim_allowed,
    }
    return {"refused": refused, "all_refused": all(refused.values())}


def _build_prediction(
    access: PredictionAccess,
    contract: ConstitutiveMap3DContract,
) -> dict[str, object]:
    access.require_current()
    prediction = factorization_certificate(access, contract)
    prediction["formal_remainder_certificate"] = exact_remainder_certificate(contract)
    prediction["locked_midpoint_predictions"] = locked_midpoint_predictions(contract)
    prediction["authored_predecessor_identity"] = authored_predecessor_identity()
    prediction["authenticated_role_sources"] = source_authentication_records()
    center = [float(item) for item in contract.bc3_heldout_center]
    prediction["shrinking_loop_line_integrals"] = []
    for scale, steps in zip(contract.bc3_scales, contract.bc3_steps_per_edge, strict=True):
        controls = parallelogram_controls(
            center,
            contract.bc3_tangent_1,
            contract.bc3_tangent_2,
            float(scale),
            steps,
        )
        prediction["shrinking_loop_line_integrals"].append(
            {
                "scale": float(scale),
                "steps_per_edge": steps,
                "line_integral": line_integral_beta(controls, float(contract.bc3_gain)),
            }
        )
    prediction["fixed_loop_line_integrals"] = []
    for steps in contract.bc3_fixed_scale_steps_per_edge:
        controls = parallelogram_controls(
            center,
            contract.bc3_tangent_1,
            contract.bc3_tangent_2,
            float(contract.bc3_scales[0]),
            steps,
        )
        prediction["fixed_loop_line_integrals"].append(
            {
                "scale": float(contract.bc3_scales[0]),
                "steps_per_edge": steps,
                "line_integral": line_integral_beta(controls, float(contract.bc3_gain)),
            }
        )
    return prediction


def _build_certificates(contract: ConstitutiveMap3DContract) -> dict[str, object]:
    session = PipelineSession(contract)
    prediction = session.build_prediction(lambda access: _build_prediction(access, contract))
    prediction_lock = session.lock_prediction(prediction)
    oracle = session.run_oracle(
        prediction_lock,
        lambda oracle_access: ladder_certificate(oracle_access, contract),
    )
    final_event_log = session.verify(prediction_lock)
    session.require_verified()
    enclosure_assessment = assess_oracle_enclosures(
        prediction["locked_midpoint_predictions"],
        oracle["rows"],
    )
    authenticated_sources = prediction["authenticated_role_sources"]
    return {
        "contract_issues": contract_issues(contract),
        "registry": canonical_registry_record(),
        "bc3_authored_predecessor": authored_predecessor_identity(),
        "bc3_prediction": prediction,
        "bc3_prediction_lock": prediction_lock.jsonable(),
        "bc3_pipeline_final_state": session.state.value,
        "bc3_pipeline_event_log": list(final_event_log),
        "bc3_oracle": oracle,
        "bc3_directed_enclosure_assessment": enclosure_assessment,
        "authenticated_role_sources": authenticated_sources,
        "qp3_geometry": geometry_certificate(contract),
        "qp3_kubo": kubo_certificate(contract),
        "refusals": refusal_certificate(contract),
    }


@lru_cache(maxsize=1)
def _canonical_certificate_bytes() -> bytes:
    return json.dumps(
        _jsonable(_build_certificates(MODEL_CONTRACT)),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


def build_certificates(
    contract: ConstitutiveMap3DContract = MODEL_CONTRACT,
) -> dict[str, object]:
    """Return a fresh record; canonical expensive intervals are evaluated once per process."""

    if contract == MODEL_CONTRACT:
        return json.loads(_canonical_certificate_bytes())
    refused = json.loads(_canonical_certificate_bytes())
    refused["contract_issues"] = contract_issues(contract)
    return refused


def natural_gate_inputs(
    certificates: Mapping[str, object],
    contract: ConstitutiveMap3DContract = MODEL_CONTRACT,
) -> dict[str, tuple[bool | None, str, Any]]:
    predecessor = certificates["bc3_authored_predecessor"]
    prediction = certificates["bc3_prediction"]
    oracle = certificates["bc3_oracle"]
    enclosure_assessment = certificates.get("bc3_directed_enclosure_assessment")
    authenticated_sources = certificates["authenticated_role_sources"]
    geometry = certificates["qp3_geometry"]
    kubo = certificates["qp3_kubo"]
    heldout = np.asarray([float(item) for item in contract.qp3_heldout], dtype=float)
    geometry_points = [np.asarray(center, dtype=float) for center in contract.qp3_centers] + [heldout]
    positive_errors = [
        float(np.max(np.abs(spectral_kubo_tensor(point, +1.0) - curvature_tensor(point))))
        for point in geometry_points
    ]
    conventional_errors = [
        float(np.max(np.abs(spectral_kubo_tensor(point, -1.0) + curvature_tensor(point))))
        for point in geometry_points
    ]
    pipeline_event_log = certificates["bc3_pipeline_event_log"]
    pipeline_lock = certificates["bc3_prediction_lock"]
    branch_box = prediction["branch_box_certificate"]
    exact_global = geometry["exact_global_certificate"]
    exact_spectral = kubo["exact_spectral_certificate"]
    exact_nulls = prediction["exact_null_and_factor_identities"]
    intervals = directed_form_intervals(Fraction(3, 25), Fraction(2, 25), Fraction(1, 3))
    ownership = certificates["registry"]["gate_ownership"]
    expected_ownership = canonical_registry_record()["gate_ownership"]
    expected_source_roles = {role for role, _, _ in reviewed_role_path_set()}
    all_source_roles_authenticated = set(authenticated_sources) == expected_source_roles and all(
        item["authenticated"] is True and item["issues"] == [] for item in authenticated_sources.values()
    )
    enclosure_status = (
        None
        if not isinstance(enclosure_assessment, Mapping)
        or str(enclosure_assessment.get("status", "")).startswith("INDETERMINATE")
        else enclosure_assessment.get("status") == "AUTHENTICATED_DIRECTED_ENCLOSURES_PASS"
    )
    natural = {
        "bc3_contract_and_domain": (
            not certificates["contract_issues"]
            and strict_cross(contract.bc3_tangent_1, contract.bc3_tangent_2) == contract.bc3_area_vector
            and contract.bc3_u_bounds == (Fraction(1, 20), Fraction(3, 20))
            and contract.bc3_v_bounds == (Fraction(1, 20), Fraction(3, 20))
            and contract.bc3_alpha_bounds == (Fraction(3, 10), Fraction(2, 5)),
            "the frozen 3D domain, heldout tangents, area vector, and exact contract must match",
            {"issues": certificates["contract_issues"], "area": list(contract.bc3_area_vector)},
        ),
        "bc3_local_c0_and_predecessor_binding": (
            predecessor["authenticated"] is True
            and all_source_roles_authenticated
            and predecessor["live_core_sample_comparison_is_acceptance"] is False
            and branch_box["clip_margin"] == "1/8"
            and branch_box["clip_inactive_everywhere"] is True
            and branch_box["wrap_inactive_everywhere"] is True
            and branch_box["branch_construction"] == "frozen_experiment_local_exact_C0_formulas"
            and branch_box["auxiliary_or_continuation_branch_present"] is False,
            (
                "the theorem must use the source-bound experiment-local exact C0 formulas; "
                "full-box clip/wrap margins are analytic and core samples are regression-only"
            ),
            {"predecessor": predecessor, "branch_box": branch_box},
        ),
        "bc3_dynamics_contraction_and_conventions": (
            contract.bc3_contraction_max == Fraction(7, 10)
            and all(
                row["lattice"]["right_endpoints_sampled_once"] is True
                and row["lattice"]["reverse_equals_forward_index_reverse_exact"] is True
                and row["lattice"]["reverse_reinitialized_at_its_stored_first_control"] is True
                for row in oracle["rows"]
            ),
            (
                "variable-alpha dynamics must have rho<=7/10, equilibrium init, "
                "right-endpoint sampling, and exact reverse"
            ),
            {
                "rho_max": str(contract.bc3_contraction_max),
                "right_endpoint": oracle["right_endpoint_update_then_sample"],
                "equilibrium_init": oracle["equilibrium_initialization"],
                "exact_reverse": oracle["exact_reverse_used"],
            },
        ),
        "bc3_exact_factorization_and_covariance": (
            prediction["formula"] == contract.bc3_formula
            and prediction["derived_area_vector"] == list(contract.bc3_area_vector)
            and prediction["global_phase_invariant"] is True
            and prediction["closed_by_exterior_derivative_squared"] is True
            and prediction["coordinate_covariant_two_form"] is True
            and prediction["prediction_uses_response"] is False,
            (
                "F must be the frozen exterior derivative factorization with closure, "
                "covariance, and no response fit"
            ),
            {
                "formula": prediction["formula"],
                "area": prediction["derived_area_vector"],
                "prediction_uses_response": prediction["prediction_uses_response"],
            },
        ),
        "bc3_directed_interval_nonzero_margins": (
            prediction["all_response_components_nonzero"] is True
            and prediction["heldout_density_nonzero"] is True
            and all(
                intervals[name].excludes_zero
                for name in ("F_v_alpha", "F_alpha_u", "F_u_v", "heldout_density")
            ),
            (
                "directed rational interval enclosures must prove every heldout response "
                "component and density nonzero"
            ),
            prediction["directed_intervals"],
        ),
        "bc3_geometry_rank1_and_alpha_fiber_separation": (
            prediction["geometry_rank"] == 1
            and prediction["alpha_endpoint_omega_intervals_equal"] is True
            and prediction["alpha_endpoint_fiber_response_separated"] is True
            and prediction["scalar_omega_only_map_possible"] is False,
            "Omega must be alpha-independent rank-one while response changes across the alpha fiber",
            {
                "geometry_vector": prediction["geometry_vector"],
                "fiber_response_separated": prediction["alpha_endpoint_fiber_response_separated"],
            },
        ),
        "bc3_prediction_lock_and_heldout_split": (
            certificates["bc3_pipeline_final_state"] == "VERIFIED"
            and pipeline_event_log == ["INIT", "PREDICTION_LOCKED", "ORACLE_RUN", "VERIFIED"]
            and len(pipeline_lock["prediction_sha256"]) == 64
            and len(pipeline_lock["lock_sha256"]) == 64
            and oracle["prediction_lock_sha256"] == pipeline_lock["lock_sha256"]
            and contract.bc3_heldout_center
            not in (
                (Fraction(1, 20), Fraction(1, 10), Fraction(3, 10)),
                (Fraction(1, 10), Fraction(1, 20), Fraction(7, 20)),
                (Fraction(3, 20), Fraction(3, 20), Fraction(2, 5)),
            ),
            (
                "the immutable prediction and distinct heldout center must pass the exact "
                "INIT->PREDICTION_LOCKED->ORACLE_RUN->VERIFIED sequence"
            ),
            {
                "lock": pipeline_lock,
                "event_log": pipeline_event_log,
                "heldout": prediction["heldout_center"],
            },
        ),
        "bc3_response_oracle_firewall": (
            authenticated_sources["bc3_predictor"]["authenticated"] is True
            and authenticated_sources["bc3_response_oracle"]["authenticated"] is True
            and authenticated_sources["bc3_predictor"]["issues"] == []
            and authenticated_sources["bc3_response_oracle"]["issues"] == []
            and all(
                authenticated_sources[role]["authenticated"] is True
                for role in (
                    "binary64_interval_kernel",
                    "bc3_lattice",
                    "bc3_interval_kernel",
                    "bc3_primitives",
                    "bc3_midpoint_predictor",
                )
            )
            and oracle["predictor_or_geometry_imported"] is False
            and oracle["orientation_label_received"] is False,
            (
                "the response oracle must receive no geometry, prediction, area, orientation "
                "label, outcome, or heldout fit"
            ),
            {
                "predictor": authenticated_sources["bc3_predictor"],
                "oracle": authenticated_sources["bc3_response_oracle"],
            },
        ),
        "bc3_generic_ladder_and_nulls": (
            _conjunctive_status(
                enclosure_status,
                oracle["binary64_interval_runtime"]["passed"] is True,
                oracle["s_times_updates_strictly_increasing"] is True,
                oracle["all_loops_inside_domain"] is True,
                exact_nulls["pure_alpha_loop_is_null_because_beta_alpha_zero"] is True,
                exact_nulls["ordinary_difference_equals_two_q_anti_by_definition"] is True,
                exact_nulls["gain_zero_annuls_all_response_components"] is True,
                exact_nulls["alpha_one_annuls_u_v_component_because_m_zero"] is True,
            ),
            (
                "the generic O(s/N) ladder must stay in-domain with sN increasing and "
                "exact scoped nulls/factor two"
            ),
            {
                "theorem": oracle["theorem"],
                "sN": [row["s_times_updates"] for row in oracle["rows"]],
                "numerical_regressions_are_acceptance_proof": False,
                "exact_null_and_factor_identities": exact_nulls,
                "directed_enclosure_assessment": enclosure_assessment,
                "binary64_interval_runtime": oracle["binary64_interval_runtime"],
            },
        ),
        "qp3_same_operator_projector_and_gap": (
            contract.qp3_gap == Fraction(2, 5)
            and exact_global["projector_idempotence_exact"] is True
            and exact_spectral["scale_divided_by_gap"]["fraction"] == "1/1"
            and kubo["existing_qp1_builder_claimed"] is False,
            (
                "experiment-local P+, H, eigenvalues, gap, and spectral projector must "
                "agree without claiming the old 2D builder"
            ),
            {
                "gap": str(contract.qp3_gap),
                "exact_projector": exact_global["projector_idempotence_exact"],
                "numerical_rows_are_regressions_only": kubo["rows"],
            },
        ),
        "qp3_monopole_geometry": (
            geometry["formula"] == "Omega_ij=epsilon_ijk*lambda_k/(2*abs(lambda)^3)"
            and geometry["response_lane_imported"] is False
            and exact_global["projector_idempotence_exact"] is True
            and authenticated_sources["qp3_geometry"]["authenticated"] is True
            and authenticated_sources["qp3_geometry"]["issues"] == [],
            "geometry must independently compute the ambient monopole curvature from the shared projector",
            geometry,
        ),
        "qp3_kubo_sign_and_factor": (
            exact_spectral["same_connection_identity_exact"] is True
            and exact_spectral["positive_observable_half_coefficient"] == 1
            and exact_spectral["conventional_observable_half_coefficient"] == -1
            and exact_spectral["full_to_half_antisymmetrization_factor"] == 2
            and exact_spectral["external_tensor_or_response_input_used"] is False
            and authenticated_sources["qp3_kubo"]["authenticated"] is True
            and authenticated_sources["qp3_kubo"]["issues"] == [],
            "+dH must give +Omega, -dH must give -Omega, and full antisymmetrization must equal twice half",
            {
                "positive_max_error": max(positive_errors),
                "conventional_max_error": max(conventional_errors),
                "factor_error": kubo["maximum_full_factor_error"],
                "numerical_comparisons_are_regressions_only": True,
                "exact": exact_spectral,
            },
        ),
        "qp3_rank3_centers_and_heldout": (
            exact_global["center_vector_rank"] == 3
            and exact_spectral["center_vector_rank"] == 3
            and exact_global["center_vector_determinant"] == "1/8"
            and exact_spectral["center_vector_determinant"] == "1/8"
            and exact_global["heldout_density"]["fraction"] == "1/2"
            and exact_spectral["heldout_density"]["fraction"] == "1/2",
            "e1,e2,e3 two-form vectors must span rank three and predict heldout h density exactly one half",
            {
                "exact_projective_rank": exact_global["center_vector_rank"],
                "exact_spectral_rank": exact_spectral["center_vector_rank"],
                "exact_projective_density": exact_global["heldout_density"],
                "exact_spectral_density": exact_spectral["heldout_density"],
                "numerical_densities_are_regressions_only": {
                    "projective": geometry["heldout_density"],
                    "spectral": kubo["heldout_density"],
                },
            },
        ),
        "qp3_gauge_coordinate_closure_and_chern": (
            exact_global["patch_transition_exact"] is True
            and exact_global["patch_curvatures_equal"] is True
            and exact_global["dOmega_exact_zero"] is True
            and exact_global["sphere_flux_pi_coefficient"] == "2"
            and exact_global["chern_number"] == 1
            and exact_global["global_smooth_connection_exists"] is False,
            (
                "the tensor must be gauge invariant, coordinate covariant, closed off the "
                "origin, and retain its Chern obstruction"
            ),
            {
                "exact_global": exact_global,
                "coordinate_covariance_regression_only": geometry["proper_rotation_covariance"],
            },
        ),
        "qp3_constant_projector_and_nonscalar_refusals": (
            exact_global["constant_projector_null_exact"] is True
            and exact_spectral["constant_projector_null_computed"] is True
            and exact_global["nonscalar_map_closed"] is False
            and exact_global["nonscalar_divergence_at_h"]["fraction"] == "1/3",
            "constant projectors must be null and the declared nonscalar K must fail closure",
            {
                "constant_projective_tensor": exact_global["constant_projector_tensor"],
                "constant_spectral_tensor": exact_spectral["constant_projector_tensor"],
                "nonscalar_divergence": exact_global["nonscalar_divergence_at_h"],
            },
        ),
        "ineligible_and_circular_control_matrix": (
            certificates["refusals"]["all_refused"] is True,
            "every tautological, circular, auxiliary, fitted, and claim-inflating control must be refused",
            certificates["refusals"],
        ),
        "claim_ceiling_and_evidence_scope": (
            not certificates["contract_issues"]
            and contract.disposition == "PASS_INTERNAL_ANALYTIC"
            and contract.evidence_status == "NO_EMPIRICAL_EVIDENCE"
            and contract.relation_scope == "MODEL_SPECIFIC_RELATIONS_ONLY"
            and contract.universal_claim_allowed is False
            and ownership == expected_ownership
            and expected_case_dispositions()["BC3"] == contract.bc3_disposition
            and expected_case_dispositions()["QP3"] == contract.qp3_disposition,
            (
                "status, evidence, model-specific ceiling, immutable ownership, and "
                "dispositions must match the contract"
            ),
            {
                "disposition": contract.disposition,
                "evidence_status": contract.evidence_status,
                "relation_scope": contract.relation_scope,
                "claim_ceiling": contract.claim_ceiling,
            },
        ),
    }
    if set(natural) != set(registry_gate_names()):
        raise RuntimeError("natural gate construction does not match immutable registry")
    return natural


def execute_program(
    contract: ConstitutiveMap3DContract = MODEL_CONTRACT,
    gate_overrides: Mapping[str, bool] | None = None,
) -> tuple[dict[str, object], list[dict[str, object]]]:
    certificates = build_certificates(contract)
    natural = natural_gate_inputs(certificates, contract)
    gates = apply_fail_only_overrides(natural, gate_overrides)
    cases = case_dispositions(gates)
    failed = [gate.name for gate in gates if gate.status == "fail"]
    indeterminate = [gate.name for gate in gates if gate.status == "indeterminate"]
    all_expected = cases == expected_case_dispositions()
    if failed:
        formal_disposition = "FAIL_INTERNAL_ANALYTIC"
    elif indeterminate:
        formal_disposition = "INDETERMINATE_INTERNAL_ANALYTIC"
    else:
        formal_disposition = contract.disposition if all_expected else "FAIL_INTERNAL_ANALYTIC"
    disposition, publication_blockers = publication_disposition(
        formal_disposition,
        str(certificates["bc3_oracle"].get("diagnostic_status", "MISSING")),
    )
    summary = {
        "experiment_id": contract.experiment_id,
        "disposition": disposition,
        "formal_disposition": formal_disposition,
        "evidence_status": contract.evidence_status,
        "relation_scope": contract.relation_scope,
        "claim_ceiling": contract.claim_ceiling,
        "case_dispositions": cases,
        "failed_gates": failed,
        "indeterminate_gates": indeterminate,
        "publication_blockers": publication_blockers,
        "gate_count": len(gates),
        "registry": certificates["registry"],
        "contract": contract.jsonable(),
        "metrics": {
            "bc3_prediction_lock_sha256": certificates["bc3_prediction_lock"]["lock_sha256"],
            "bc3_heldout_density_regression": certificates["bc3_prediction"]["regression_float_view"][
                "heldout_density"
            ],
            "bc3_directed_density_intervals": [
                row["density_interval"] for row in certificates["bc3_directed_enclosure_assessment"]["rows"]
            ],
            "bc3_scalar_non_authoritative_diagnostic": {
                "policy": certificates["bc3_oracle"]["scalar_diagnostic_policy"],
                "assessment": certificates["bc3_oracle"]["scalar_diagnostic_assessment"],
                "rows": [row["scalar_diagnostic"] for row in certificates["bc3_oracle"]["rows"]],
            },
            "qp3_heldout_density": certificates["qp3_kubo"]["heldout_density"],
            "qp3_center_rank": certificates["qp3_kubo"]["center_vector_rank"],
        },
    }
    records = [
        {"record_type": "certificate", "name": name, "payload": payload}
        for name, payload in certificates.items()
    ] + [{"record_type": "gate", **gate.jsonable()} for gate in gates]
    return _jsonable(summary), _jsonable(records)


def contract_mutation(field_name: str, value: Any) -> ConstitutiveMap3DContract:
    """Small test helper that never mutates the frozen canonical instance."""

    return replace(MODEL_CONTRACT, **{field_name: value})
