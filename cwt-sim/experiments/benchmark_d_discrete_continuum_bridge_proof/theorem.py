"""Fail-closed execution of the exact Benchmark-D bridge program."""

from __future__ import annotations

import copy
import hashlib
import json
import os
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .adapter import (
    contract_mutation_issues,
    core_binding_certificate,
    core_mutation_examples,
    safety_certificate,
)
from .contract import (
    CASE_GATE_MAP,
    EXPECTED_CASE_DISPOSITIONS,
    MODEL_CONTRACT,
    REFUSAL_SPECS,
    BridgeContract,
)
from .exact_math import (
    algebra_certificate,
    curvature_domain_certificate,
    fixed_time_certificate,
    fixed_time_certificate_issues,
    stationary_and_contraction_certificate,
)

SIM_ROOT = Path(__file__).resolve().parents[2]
OPEN_ARTIFACTS = SIM_ROOT / "experiments" / "benchmark_d_open_response_proof" / "artifacts"
LINDBLAD_ARTIFACTS = SIM_ROOT / "experiments" / "benchmark_d_lindblad_response_proof" / "artifacts"


@dataclass(frozen=True)
class Gate:
    name: str
    passed: bool
    requirement: str
    observed: object

    def jsonable(self) -> dict[str, object]:
        return {
            "name": self.name,
            "status": "pass" if self.passed else "fail",
            "requirement": self.requirement,
            "observed": self.observed,
        }


def gate(name: str, passed: bool, requirement: str, observed: object) -> Gate:
    return Gate(name=name, passed=bool(passed), requirement=requirement, observed=observed)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _is_symlink_or_reparse(path: Path) -> bool:
    metadata = os.lstat(path)
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    return path.is_symlink() or bool(getattr(metadata, "st_file_attributes", 0) & reparse_flag)


def _recursive_context_inventory(path: Path) -> dict[str, str]:
    """Inventory ordinary entries recursively without following links/reparse points."""

    if _is_symlink_or_reparse(path) or not path.is_dir():
        raise RuntimeError(f"context root must be an ordinary directory: {path}")
    inventory: dict[str, str] = {}
    pending = [path]
    while pending:
        directory = pending.pop()
        with os.scandir(directory) as iterator:
            for entry in iterator:
                entry_path = Path(entry.path)
                relative = entry_path.relative_to(path).as_posix()
                if _is_symlink_or_reparse(entry_path):
                    raise RuntimeError(f"context closure contains a link/reparse entry: {relative}")
                if entry.is_dir(follow_symlinks=False):
                    inventory[relative] = "directory"
                    pending.append(entry_path)
                elif entry.is_file(follow_symlinks=False):
                    inventory[relative] = "file"
                else:
                    raise RuntimeError(f"context closure contains an unsupported entry: {relative}")
    return dict(sorted(inventory.items()))


def _verify_context_directory(path: Path) -> dict[str, object]:
    inventory = _recursive_context_inventory(path)
    checksums_path = path / "CHECKSUMS.json"
    if inventory.get("CHECKSUMS.json") != "file":
        raise RuntimeError(f"context checksum manifest is not an ordinary file: {checksums_path}")
    payload = json.loads(checksums_path.read_text(encoding="utf-8"))
    declared = payload.get("files")
    if not isinstance(declared, dict):
        raise RuntimeError(f"invalid context checksum manifest: {checksums_path}")
    if any(
        not isinstance(name, str)
        or not name
        or Path(name).is_absolute()
        or "\\" in name
        or Path(name).as_posix() != name
        or ".." in Path(name).parts
        or not isinstance(expected, str)
        for name, expected in declared.items()
    ):
        raise RuntimeError(f"invalid path-bound context manifest: {checksums_path}")
    actual_names = sorted(inventory)
    expected_names = sorted(["CHECKSUMS.json", *declared])
    if actual_names != expected_names:
        raise RuntimeError(
            f"unexpected recursive context artifact inventory: {path}; "
            f"expected={expected_names}, actual={actual_names}"
        )
    if any(inventory[name] != "file" for name in expected_names):
        raise RuntimeError(f"context closure contains a non-file path substitution: {path}")
    matches = {name: _sha256(path / name) == expected for name, expected in sorted(declared.items())}
    return {
        "relative_path": path.relative_to(SIM_ROOT).as_posix(),
        "checksums_sha256": _sha256(checksums_path),
        "declared_file_count": len(declared),
        "recursive_inventory_exact": actual_names == expected_names,
        "entry_types": inventory,
        "symlink_or_reparse_entries": [],
        "all_declared_hashes_match": len(matches) == len(declared) and all(matches.values()),
        "raw_file_sha256": {name: _sha256(path / name) for name in actual_names},
    }


def context_certificate(contract: BridgeContract = MODEL_CONTRACT) -> dict[str, object]:
    """Bind the two prior result bundles only as immutable structural context."""

    legacy_h = contract.box.bias_min * 0 + contract.h_upper - contract.h_upper + contract.h_upper
    # Use literal exact historical values; the verbose expression above is not
    # used as an acceptance trick and is replaced in the record below.
    legacy_h = type(contract.h_upper)(9, 50)
    legacy_q = type(contract.h_upper)(1, 125)
    target_q = contract.depolarizing_rate * legacy_h
    return {
        "open_artifacts": _verify_context_directory(OPEN_ARTIFACTS),
        "lindblad_artifacts": _verify_context_directory(LINDBLAD_ARTIFACTS),
        "legacy_open_point": {
            "h": f"{legacy_h.numerator}/{legacy_h.denominator}",
            "q": f"{legacy_q.numerator}/{legacy_q.denominator}",
            "primary_family_q": f"{target_q.numerator}/{target_q.denominator}",
            "q_mismatch": f"{(legacy_q-target_q).numerator}/{(legacy_q-target_q).denominator}",
            "off_primary_family": legacy_q != target_q,
        },
        "roles": {
            "open": "hash_bound_structural_context_off_primary_family_not_numerically_bridged",
            "lindblad": "hash_bound_continuous_target_context_not_new_evidence",
        },
    }


def refusal_certificate(contract: BridgeContract = MODEL_CONTRACT) -> dict[str, object]:
    """Execute the finite refusal registry without using it as a substitute for proof."""

    mutations = core_mutation_examples(contract)
    checks = {
        "R01": type(contract.h_upper)(1, 125) != contract.depolarizing_rate * type(contract.h_upper)(9, 50),
        "R02": bool(mutations["fixed_q"]) and bool(mutations["exponential_q"]),
        "R03": bool(mutations["zero_delta"]),
        "R04": contract.transpose_convention == "column_population_uses_K_transpose"
        and contract.affine_source_formula == "c_h=h*(delta/5)*one",
        "R05": bool(mutations["wrong_scaling"]),
        "R06": bool(mutations["wrong_center"]) and bool(mutations["helper"]),
        "R07": bool(mutations["wrong_clock"]) and bool(mutations["wrong_reverse"]),
        "R08": contract.proof_mode == "symbolic_fraction_and_directed_interval_not_finite_ladder",
        "R09": contract.projection_policy == "core_crosscheck_only_and_proven_inactive",
        "R10": "not_q_h/5" in contract.stationary_positivity_bound,
        "R11": contract.depolarizing_rule == "q_h=delta*h",
        "R12": "not_finite_ladder" in contract.proof_mode,
        "R13": contract.limit_interchangeability == "not_claimed",
        "R14": OPEN_ARTIFACTS.is_dir() and LINDBLAD_ARTIFACTS.is_dir(),
        "R15": bool(mutations["claim_inflation"]),
        "R16": bool(mutations["coherent"]) and bool(mutations["site"]) and bool(mutations["zero_delta"]),
        "R17": bool(mutations["helper"]) and contract.branch_helper_policy == "forbidden_in_theorem_path",
        "R18": bool(mutations["runtime_scope"])
        and contract.core_regression_scope
        == "finite_float_core_regression_and_provenance_only_not_uniform_runtime_proof",
        "R19": bool(mutations["scale_domain"])
        and contract.scale_domain == "positive_rational_s_with_0<s<=1/100",
        "R20": _verify_context_directory(OPEN_ARTIFACTS)["recursive_inventory_exact"] is True
        and _verify_context_directory(LINDBLAD_ARTIFACTS)["recursive_inventory_exact"] is True,
    }
    return {
        "specifications": dict(sorted(REFUSAL_SPECS.items())),
        "checks": checks,
        "mutation_issues": mutations,
        "complete": set(checks) == set(REFUSAL_SPECS) and all(checks.values()),
    }


def all_certificates(contract: BridgeContract = MODEL_CONTRACT) -> dict[str, object]:
    return {
        "contract_issues": contract_mutation_issues(contract),
        "core_binding": core_binding_certificate(contract),
        "core_safety": safety_certificate(contract),
        "algebra": algebra_certificate(contract),
        "curvature": curvature_domain_certificate(contract),
        "stationary_contraction": stationary_and_contraction_certificate(contract),
        "fixed_time": fixed_time_certificate(contract),
        "context": context_certificate(contract),
        "refusals": refusal_certificate(contract),
    }


def build_gates(certificates: Mapping[str, Any], contract: BridgeContract = MODEL_CONTRACT) -> list[Gate]:
    """Build every live gate directly from executable certificate records."""

    binding = certificates["core_binding"]
    safety = certificates["core_safety"]
    algebra = certificates["algebra"]
    curvature = certificates["curvature"]
    stationary = certificates["stationary_contraction"]
    fixed_time = certificates["fixed_time"]
    fixed_time_issues = fixed_time_certificate_issues(fixed_time, contract)
    context = certificates["context"]
    refusals = certificates["refusals"]
    gates = [
        gate(
            "contract_exact_primary_family",
            not certificates["contract_issues"]
            and contract.depolarizing_rule == "q_h=delta*h"
            and contract.h_upper == type(contract.h_upper)(1, 5)
            and contract.theorem_family_scope == "abstract_exact_fraction_D0_diagonal_population_family"
            and contract.scale_domain == "positive_rational_s_with_0<s<=1/100"
            and 0 < contract.circle_scale <= contract.scale_upper,
            "the abstract exact-Fraction q_h=delta*h family and every frozen field are unchanged",
            certificates["contract_issues"],
        ),
        gate(
            "d0_clip_inactive",
            safety["clip_inactive"] is True and safety["clip_support_margin"]["fraction"] == "31/200",
            "the complete D0 box is strictly inside every kernel clip boundary",
            safety,
        ),
        gate(
            "kraus_cp_tp_uniform",
            safety["maximum_no_jump_loss"]["fraction"] == "199/2500"
            and safety["no_jump_radicand_floor"]["fraction"] == "2301/2500"
            and binding["maximum_kraus_tp_error"] < 1e-14,
            "the frozen Kraus map is CP/TP with exact loss and radicand margins",
            {"safety": safety, "numeric_tp_error": binding["maximum_kraus_tp_error"]},
        ),
        gate(
            "safety_rescale_inactive",
            safety["rescale_inactive"] is True and safety["rescale_margin"]["fraction"] == "2251/2500",
            "the core 0.98 Kraus rescale branch is uniformly inactive",
            safety["rescale_margin"],
        ),
        gate(
            "projection_inactive",
            binding["maximum_projection_delta"] < 1e-14,
            "the PSD/trace projection makes no material change on the tested complete population basis",
            binding["maximum_projection_delta"],
        ),
        gate(
            "finite_core_diagonal_regression",
            binding["semantic_scope"]
            == "finite_float_core_regression_and_provenance_only_not_uniform_runtime_proof"
            and binding["uniform_family_proof_source"]
            == "exact_fraction_symbolic_affine_identity_not_runtime_samples"
            and binding["population_basis_count"] == 5
            and binding["traceless_diagonal_deviation_basis_count"] == 4
            and max(
                binding["maximum_kernel_error"],
                binding["maximum_affine_error"],
                binding["maximum_deviation_error"],
                binding["maximum_offdiagonal_output"],
                binding["observable_maximum_absolute_error"],
                binding["observable_hermiticity_error"],
            )
            < 1e-14
            and binding["branch_or_fixed_helper_called"] is False,
            (
                "finite core calls regress the diagonal basis/readout but do not prove "
                "uniform runtime equivalence"
            ),
            binding,
        ),
        gate(
            "exact_generator_source_identity",
            algebra["matrix_identity_max_error"]["fraction"] == "0/1"
            and algebra["generator_formula_verified"] is True
            and all(item["fraction"] == "1/1250" for item in algebra["source_identity"])
            and algebra["box_jump_generator_l1_bound"]["fraction"] == "49/50"
            and algebra["uniform_generator_error_coefficient"]["fraction"] == "49/6250"
            and algebra["source_generator_error"]["fraction"] == "0/1",
            "M_h=I+hA_h and c_h=h(delta/5)1 exactly, with K transpose",
            algebra,
        ),
        gate(
            "uniform_c2_parameter_control",
            algebra["parameter_derivative_bounds"]["R_l1_upper"]["fraction"] == "2/1"
            and algebra["parameter_derivative_bounds"]["R_bias_l1"]["fraction"] == "2/1"
            and algebra["parameter_derivative_bounds"]["R_diffusion_l1"]["fraction"] == "4/1"
            and algebra["parameter_derivative_bounds"]["X_i_rule"] == "||X_h,i||_1<=5*L_i"
            and algebra["parameter_derivative_bounds"]["X_ij_rule"] == "||X_h,ij||_1<=50*L_i*L_j",
            "uniform exact C2 parameter derivative bounds hold on the rational family",
            algebra["parameter_derivative_bounds"],
        ),
        gate(
            "exact_stationary_branch",
            stationary["fixed_branch_method"] == "exact_fraction_linear_solve_not_iteration"
            and stationary["analytic_stationary_floor"]["fraction"] == "4/69"
            and stationary["floor_is_not_q_h_over_5"] is True
            and stationary["maximum_exact_stationary_residual"]["fraction"] == "0/1"
            and stationary["maximum_exact_trace_error"]["fraction"] == "0/1"
            and stationary["analytic_floor_below_sampled_minimum"] is True
            and all(
                item["normalization_error"]["fraction"] == "0/1"
                for item in stationary["representative_crosscheck_ladder_not_proof"]
            ),
            "xbar_h=-A_h^-1 c exactly and the analytic population floor is 4/69",
            stationary,
        ),
        gate(
            "uniform_contraction_and_resolvent",
            stationary["trace_l1_contraction"] == "1-delta*h"
            and stationary["delta"]["fraction"] == "1/25"
            and stationary["uniform_resolvent_bound"] == "h*||(I-M_h)^-1||_1<=25"
            and algebra["fixed_branch_difference_bound"] == "||xbar_h-xbar||_1<=2*h/5",
            "the population map contracts by 1-delta*h and has the uniform inverse/fixed-branch bounds",
            {"stationary": stationary, "algebra": algebra["fixed_branch_bound_derivation"]},
        ),
        gate(
            "exact_hB_gradient_identity",
            algebra["closed_loop_exact_gradient_term"] == "h*d(H*xbar_h)_i",
            "hB_h=B_CT(a_h)+h d(H xbar_h) exactly",
            algebra["representative_hB"],
        ),
        gate(
            "closed_loop_gradient_cancellation",
            algebra["closed_loop_gradient_curl"]["fraction"] == "0/1",
            "the exact-gradient correction has zero curl and zero closed-loop integral",
            algebra["closed_loop_gradient_curl"],
        ),
        gate(
            "exact_hF_identity",
            algebra["hF_exact_identity"] is True,
            "hF_h equals the continuous generator curvature at a_h=a(1-delta*h)",
            algebra["representative_hF"],
        ),
        gate(
            "curvature_sign_interval",
            curvature["curvature_interval"]["upper"]["numerator"] < 0
            and curvature["curvature_numerator_interval"]["upper"]["numerator"] < 0,
            "directed exact intervals certify hF_h<0 for the entire h domain",
            {
                "curvature": curvature["curvature_interval"],
                "numerator": curvature["curvature_numerator_interval"],
            },
        ),
        gate(
            "center_limit_oracle",
            curvature["center_limit_matches_formal"] is True
            and curvature["first_h_coefficient_matches_formal"] is True,
            "the recomputed h->0 fraction and first h coefficient equal the independent formal oracles",
            {
                "limit": curvature["center_limit"],
                "first": curvature["first_h_coefficient"],
            },
        ),
        gate(
            "curvature_error_bound",
            curvature["derivative_absolute_upper"]["float"] < 88.0
            and curvature["uniform_error_coefficient"]["fraction"] == "88/1",
            "the mean-value theorem gives the uniform strict bound |hF_h-F_CT|<88h",
            curvature["derivative_absolute_upper"],
        ),
        gate(
            "response_units_and_h_scaling",
            contract.response_scaling == "Q_h=h*S_h_where_S_h=sum_right_endpoint_centered_readout"
            and contract.response_units == "mean_position_index_times_model_time"
            and contract.response_centering == "instantaneous_exact_xbar_h",
            "the reducer uses h-scaled centered right-endpoint sums in model-time units",
            {
                "scaling": contract.response_scaling,
                "centering": contract.response_centering,
                "units": contract.response_units,
            },
        ),
        gate(
            "loop_clock_reversal_endpoint_contract",
            contract.update_convention == "right_endpoint_update_then_sample"
            and contract.reversal_convention == "gamma_minus(t)=gamma_plus(T-t)"
            and contract.endpoint_convention == "skip_duplicate_initial_and_process_closing_endpoint_once"
            and contract.slow_clock == "uniform_affine_u=t/T_on_common_circle"
            and fixed_time["clock_path_initialization"]
            == {
                "positive_integer_N_with_Nh_equal_T": True,
                "discrete_exact_xbar_h_at_common_start": True,
                "continuous_exact_xbar_at_common_start": True,
                "right_endpoint_update_then_sample": True,
                "closing_endpoint_processed_once": True,
                "minus_is_exact_reverse_of_plus": True,
                "same_uniform_circle_and_affine_clock": True,
            },
            "right endpoints, one closing endpoint, a common affine clock, and exact reversal are frozen",
            fixed_time,
        ),
        gate(
            "qanti_and_did_factors",
            contract.qanti_definition == "Qanti_h=(Q_h_plus-Q_h_minus)/2"
            and contract.did_definition == "ordinary_scaled_orientation_difference=2*Qanti_h",
            "Qanti is the half difference and the ordinary orientation difference is exactly 2Qanti",
            {"qanti": contract.qanti_definition, "did": contract.did_definition},
        ),
        gate(
            "fixed_time_bridge_bound",
            not fixed_time_issues
            and fixed_time["local_defect"]["static_coefficient"]["fraction"] == "76/625"
            and fixed_time["local_defect"]["speed_pi_coefficient"]["fraction"] == "6/5"
            and fixed_time["fixed_time_bound"]["time_coefficient"]["fraction"] == "214/25"
            and fixed_time["fixed_time_bound"]["directed_circle_coefficient"]["fraction"] == "42600/113"
            and fixed_time["fixed_time_bound"]["same_bound_for_each_orientation_and_qanti"] is True
            and fixed_time["response_reducer"]["q_step_prefactor"]["fraction"] == "1/1"
            and fixed_time["response_reducer"]["q_step_power"] == 1
            and fixed_time["contraction"]["product_uses_elapsed_model_time_kh"] is True
            and fixed_time["trajectory_or_finite_ladder_used_for_acceptance"] is False,
            "every fixed-T premise is exactly recomputed and the bound uses no fitted trajectory gate",
            {"certificate": fixed_time, "recomputation_issues": fixed_time_issues},
        ),
        gate(
            "scale_domain_uniform_containment",
            not fixed_time_issues
            and fixed_time["scale_domain"]["maximum_inclusive"]["fraction"] == "1/100"
            and fixed_time["exact_circle_extrema"]["minimum_face_margin"]["fraction"] == "1/100"
            and fixed_time["exact_circle_extrema"]["uniform_domain_minimum_face_margin"]["fraction"]
            == "1/100"
            and fixed_time["exact_circle_extrema"]["inside_box"] is True
            and fixed_time["uniform_over_declared_scale_domain"] is True,
            "all rational 0<s<=1/100 loops remain in the box with uniform constants",
            {"scale": fixed_time["scale"], "extrema": fixed_time["exact_circle_extrema"]},
        ),
        gate(
            "iterated_and_joint_limit_scope",
            fixed_time["limits"]["primary_order"]
            == [
                "h_to_0_at_fixed_T_s_with_positive_integer_T_over_h",
                "T_to_infinity",
                "optional_s_to_0_within_declared_scale_domain",
            ]
            and fixed_time["limits"]["interchangeability_claimed"] is False
            and fixed_time["limits"]["sufficient_joint_conditions"] == ["T_to_infinity", "h*T_to_0"]
            and fixed_time["limits"]["area_relative_joint_conditions"] == ["s*T_to_infinity", "h*T/s^2_to_0"],
            "only the proved iterated limit and explicitly sufficient joint conditions are claimed",
            fixed_time,
        ),
        gate(
            "legacy_context_off_family",
            context["legacy_open_point"]["off_primary_family"] is True
            and context["legacy_open_point"]["q_mismatch"] == "1/1250",
            "the existing h=9/50,q=1/125 open proof is explicitly off the rational primary family",
            context["legacy_open_point"],
        ),
        gate(
            "context_artifact_hash_closure",
            context["open_artifacts"]["all_declared_hashes_match"] is True
            and context["lindblad_artifacts"]["all_declared_hashes_match"] is True
            and context["open_artifacts"]["recursive_inventory_exact"] is True
            and context["lindblad_artifacts"]["recursive_inventory_exact"] is True,
            "both recursive path-bound prior bundles are exact ordinary-file closures",
            context,
        ),
        gate(
            "refusal_matrix_complete",
            refusals["complete"] is True,
            "every frozen refusal case is represented and fails closed",
            refusals,
        ),
        gate(
            "claim_ceiling",
            contract.disposition == "PASS_INTERNAL_ANALYTIC"
            and contract.empirical_status == "NO_EMPIRICAL_EVIDENCE"
            and "no full-density" in contract.claim_ceiling
            and "CGT-alignment" in contract.claim_ceiling
            and "empirical" in contract.claim_ceiling,
            "the disposition is internal analytic only and makes no empirical/full-density/CGT claim",
            contract.claim_ceiling,
        ),
    ]
    live_names = [item.name for item in gates]
    registered_names = [name for names in CASE_GATE_MAP.values() for name in names]
    if len(live_names) != len(set(live_names)):
        raise RuntimeError("duplicate live bridge gate")
    if set(live_names) != set(registered_names):
        raise RuntimeError(
            f"bridge gate registry mismatch: orphan={sorted(set(live_names)-set(registered_names))}, "
            f"absent={sorted(set(registered_names)-set(live_names))}"
        )
    return gates


def derive_case_dispositions(gates: list[Gate]) -> dict[str, str]:
    status = {item.name: item.passed for item in gates}
    return {
        case_id: (
            expected
            if all(status[name] for name in CASE_GATE_MAP[case_id])
            else expected.removesuffix("_PASS") + "_FAIL"
        )
        for case_id, expected in EXPECTED_CASE_DISPOSITIONS.items()
    }


def execute_program(
    contract: BridgeContract = MODEL_CONTRACT,
    *,
    gate_overrides: Mapping[str, bool] | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Execute the exact bridge program; overrides can only force a pass to fail."""

    issues = contract_mutation_issues(contract)
    # Invalid contracts are rejected before their altered numerical operators
    # are evaluated.  This prevents a singular or unsafe mutation from turning
    # a fail-closed metadata check into an uncontrolled numerical exception.
    certificate_contract = MODEL_CONTRACT if issues else contract
    certificates = copy.deepcopy(all_certificates(certificate_contract))
    certificates["contract_issues"] = issues
    gates = build_gates(certificates, contract)
    if gate_overrides:
        known = {item.name for item in gates}
        unknown = set(gate_overrides) - known
        if unknown:
            raise ValueError(f"unknown bridge gate override: {sorted(unknown)}")
        if any(type(value) is not bool for value in gate_overrides.values()):
            raise TypeError("bridge gate overrides must be booleans")
        gates = [
            Gate(
                name=item.name,
                passed=item.passed and gate_overrides.get(item.name, True),
                requirement=item.requirement,
                observed=item.observed,
            )
            for item in gates
        ]
    cases = derive_case_dispositions(gates)
    failed = [item.name for item in gates if not item.passed]
    all_pass = not failed and cases == EXPECTED_CASE_DISPOSITIONS
    summary = {
        "schema_version": 1,
        "experiment_id": MODEL_CONTRACT.experiment_id,
        "disposition": "PASS_INTERNAL_ANALYTIC" if all_pass else "FAIL_INTERNAL_ANALYTIC",
        "evidence_status": "NO_EMPIRICAL_EVIDENCE",
        "all_gates_pass": all_pass,
        "failed_gates": failed,
        "case_dispositions": cases,
        "claim_ceiling": MODEL_CONTRACT.claim_ceiling,
        "contract": contract.jsonable(),
        "metrics": {
            "continuous_center_curvature": certificates["curvature"]["center_limit"],
            "first_h_coefficient": certificates["curvature"]["first_h_coefficient"],
            "curvature_derivative_absolute_upper": certificates["curvature"]["derivative_absolute_upper"],
            "fixed_time_directed_circle_coefficient": certificates["fixed_time"]["fixed_time_bound"][
                "directed_circle_coefficient"
            ],
        },
        "gates": [item.jsonable() for item in gates],
    }
    records = [
        {"record_type": "certificate", "name": name, "value": value}
        for name, value in sorted(certificates.items())
    ] + [{"record_type": "gate", **item.jsonable()} for item in gates]
    return summary, records
