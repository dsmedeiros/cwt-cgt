"""Common-origin pullback theorem and obstruction certificates."""

from __future__ import annotations

from .contract import MODEL_CONTRACT, CurvatureAuditContract


def common_origin_certificate(
    contract: CurvatureAuditContract = MODEL_CONTRACT,
) -> dict[str, object]:
    """Encode the exact pullback criterion without claiming universal alignment."""

    return {
        "branch_graph": "sigma:Lambda->N",
        "projective_map": "P:N->CP^(n-1)",
        "response_one_form": "beta_R in Omega^1(N)",
        "alignment_coefficient": contract.alignment_coefficient_type,
        "local_berry_connection": "a_B in Omega^1(V) with d a_B=omega_FS on a gauge patch V",
        "berry_two_form": "omega_FS in Omega^2(CP^(n-1))",
        "response_one_form_pullback": "B_R=sigma^*beta_R in Omega^1(Lambda)",
        "berry_connection_pullback": "A_Lambda=sigma^*P^*a_B in Omega^1(U)",
        "response_pullback": "F_R=dB_R=sigma^*(d beta_R)",
        "berry_pullback": "Omega=dA_Lambda=sigma^*(P^*omega_FS)",
        "necessary_and_sufficient_condition": contract.pullback_condition,
        "branch_tangent_form": (
            "for every lambda and v,w in T_lambda Lambda, "
            "d beta_R_(sigma(lambda))(d sigma v,d sigma w)-kappa(lambda) "
            "omega_FS_(P(sigma(lambda)))(d(P sigma)v,d(P sigma)w)=0"
        ),
        "necessary": True,
        "sufficient": True,
        "ambient_equality_not_required": True,
        "off_branch_normal_components_unconstrained": True,
    }


def obstruction_certificate(
    contract: CurvatureAuditContract = MODEL_CONTRACT,
) -> dict[str, object]:
    """Freeze local-potential, period, and Chern qualifications."""

    return {
        "constant_kappa_local_statement": (
            "for constant kappa, F_R=kappa*Omega iff d(B_R-kappa*A_Lambda)=0; only on a "
            "contractible branch chart does this imply B_R-kappa*A_Lambda=d chi"
        ),
        "variable_kappa_warning": (
            "d(B_R-kappa*A_Lambda)=F_R-kappa*Omega-dkappa wedge A_Lambda; "
            "the constant-kappa potential statement cannot be reused"
        ),
        "noncontractible_period_condition": (
            "all pulled-back periods integral_gamma(B_R-kappa*A_Lambda) must vanish before an "
            "exact chi exists"
        ),
        "global_chern_obstruction": (
            "nonzero pulled-back Chern flux forbids one global smooth A_Lambda; if B_R is global "
            "and kappa is a nonzero constant, integral_closed_surface dB_R=0 conflicts with "
            "kappa integral Omega"
        ),
        "local_scope_id": contract.local_potential_scope,
        "global_scope_id": contract.global_obstruction_scope,
        "periods_required": True,
        "chern_flux_required": True,
        "global_smooth_connection_claimed": False,
    }


def refusal_certificate(
    contract: CurvatureAuditContract = MODEL_CONTRACT,
) -> dict[str, object]:
    """Return the finite fail-closed matrix for invalid alignment arguments."""

    refused = {
        "pointwise_F_over_Omega_fit": not contract.fitted_or_pointwise_normalization_allowed,
        "two_dimensional_quotient_as_prediction": not contract.two_dimensional_quotient_is_predictive,
        "unfrozen_tensor_or_coordinate_map": not contract.unfrozen_tensor_map_allowed,
        "finite_limit_to_ontology_upgrade": not contract.limit_or_ontology_upgrade_allowed,
        "auxiliary_state_substitution": True,
        "separately_authored_readout_called_same_origin": True,
    }
    return {
        "refused": refused,
        "all_refused": all(refused.values()),
        "two_dimensional_reason": (
            "the two-form space is one-dimensional, so a pointwise quotient is algebraic and "
            "has no held-out tensor-direction content"
        ),
    }


def future_alignment_requirements(
    contract: CurvatureAuditContract = MODEL_CONTRACT,
) -> dict[str, object]:
    """Define the minimum non-tautological future CWT alignment test."""

    return {
        "minimum_full_rank_area_directions": contract.future_minimum_full_rank_area_directions,
        "heldout_oblique_direction_required": contract.future_heldout_oblique_required,
        "pointwise_division_forbidden": contract.future_pointwise_division_forbidden,
        "tensor_map_frozen_before_response": contract.future_tensor_map_must_be_frozen,
        "current_audit_supplies_future_alignment_pass": False,
        "future_status": "NOT_INSTANTIATED",
    }
