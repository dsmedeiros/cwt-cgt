"""Fail-closed pre-response theorem program for N0 and P0."""

from __future__ import annotations

from fractions import Fraction
from types import MappingProxyType

from .connection_eligibility import (
    connection_basis,
    connection_eligibility_certificate,
    p0_acceptance_payload,
    predictor_curvature,
    predictor_one_form,
)
from .contract import (
    A_CENTERS,
    CASE_GATE_MAP,
    EXPECTED_CASE_DISPOSITIONS,
    HELDOUT_AREA_VECTOR,
    HELDOUT_CENTER,
    MODEL_CONTRACT,
    ORDERED_GATES,
    RESERVATION_STATUS,
    V_CENTERS,
    contract_issues,
    exposure_registry_issues,
)
from .exact import canonical_exact_sha256, fraction_vector_sha256, rational_determinant
from .firewall import (
    EXPECTED_PACKAGE_FILE_NAMES,
    MATERIAL_FILES,
    ROLE_FILES,
    source_firewall_record,
)
from .krylov_no_go import closure_coefficients, krylov_no_go_certificate, n0_acceptance_payload
from .model import branch_bundle, branch_identity_record
from .protocol import canonical_protocol_record
from .response_reader_sentinel import sentinel_record

N0_DETERMINANT_SHA256 = "0d0b3dff9d30fc49c8aef954a3b90aba4fa483c1d70dd2c43366476298bfad63"
P0_GRAM_SHA256 = "650243385ad8d2bac5d32b8890b8b0dcb931a2b08611bca995de68eb5f1a650d"
P0_HELDOUT_SHA256 = "23f59845f3a860ca2823e6c190eaaa4ad94e469d33694a15c5086be9d9201aa6"
REVIEWED_N0_CERTIFICATE_SHA256 = "6e0566cfd47da888358f0af7165bf622e359cdcbf8ac511513e2a0c66e882868"
REVIEWED_P0_CERTIFICATE_SHA256 = "dd25364e1211a6a671049c51e8ad32a7793e01b38a7a2575dd19747ef57b93a4"
REVIEWED_EXPOSURE_REGISTRY_SHA256 = "ec13af5208b2ba2d3a8d7806d04df95877394abaf42e6676c7dbce2a049fd509"
REVIEWED_CRITERION_SHA256 = "ab5cc7a9ec39d33a096643a03b65aa5654200c1c00907bd76a8005490f37a6e7"
REVIEWED_MATERIAL_PATH_SET_SHA256 = "c0f4c5bdd84a8f340ed50fac29e00727dcea7193dadc0780e91779ad17b065b2"
REVIEWED_PACKAGE_FILE_SET_SHA256 = "c876c998e2c7574f86dede2f73c4f4169109cd50888b45a1308b4f075e9fbf98"
REVIEWED_ROLE_IMPORT_TARGETS_SHA256 = MappingProxyType(
    {
        "model": "0d744b2593d0006f284d618e4aace50d501814f940abb8863e7f3f58e13bf48c",
        "geometry": "a9142b99ffde73f8a5cc1e988ff88b4ef9f6b081cc7893edf9f4dcb09b3531d7",
        "protocol": "e144ede217b14fb1de1bca9f0b0c0043bdab8e2f8dd8d636cace5b2d53c44e37",
        "composition": "37a493e0c50bf07f3cab701774ed0d9f10750dd13482613c88132fde1dc7ef4f",
        "firewall_authority": "83707db1881897596cd5a3716d7c241849562bfa14b467b47d086325e24e1bc8",
        "focused_test": "b2ba389e7d61f99836e80abec7fc2d34256accb83fdf18300e7f23b696af1d45",
    }
)
REVIEWED_FIREWALL_SOURCE_SHA256 = "2823a662b7969e152dc0bea36084cb6499f526bc8132dc7642f286f5821c80ac"
REVIEWED_FOCUSED_TEST_SOURCE_SHA256 = "25474f1521cf9647f6d1aa0e19521c2d4186f97e24d435a8817a410c691002fe"


def _strict_equal(left: object, right: object) -> bool:
    if type(left) is not type(right):
        return False
    if type(left) in {tuple, list}:
        return len(left) == len(right) and all(  # type: ignore[arg-type]
            _strict_equal(a, b) for a, b in zip(left, right, strict=True)  # type: ignore[arg-type]
        )
    if type(left) is dict:
        return tuple(left) == tuple(right) and all(  # type: ignore[arg-type]
            _strict_equal(left[key], right[key]) for key in left  # type: ignore[index,union-attr]
        )
    if type(left) is MappingProxyType:
        return tuple(left) == tuple(right) and all(  # type: ignore[arg-type]
            _strict_equal(left[key], right[key]) for key in left  # type: ignore[index,union-attr]
        )
    return bool(left == right)


def _n0_record_valid(record: object) -> bool:
    if type(record) is not MappingProxyType:
        return False
    try:
        payload = n0_acceptance_payload(record)
    except (TypeError, KeyError):
        return False
    rows = record.get("closure_rows")
    if (
        type(rows) is not tuple
        or len(rows) != 3
        or any(
            type(row) is not tuple or len(row) != 3 or any(type(value) is not Fraction for value in row)
            for row in rows
        )
    ):
        return False
    expected_centers = A_CENTERS[:3]
    expected_rows = tuple(closure_coefficients(center) for center in expected_centers)
    determinant = rational_determinant([list(row) for row in rows])
    return (
        _strict_equal(record.get("centers"), expected_centers)
        and _strict_equal(rows, expected_rows)
        and type(record.get("closure_determinant")) is Fraction
        and _strict_equal(record["closure_determinant"], determinant)
        and fraction_vector_sha256((determinant,)) == N0_DETERMINANT_SHA256
        and canonical_exact_sha256(payload) == REVIEWED_N0_CERTIFICATE_SHA256
        and _strict_equal(record.get("certificate_sha256"), REVIEWED_N0_CERTIFICATE_SHA256)
        and record.get("reviewed_certificate_sha256_matches") is True
    )


def _p0_design_valid(record: object) -> bool:
    if type(record) is not MappingProxyType:
        return False
    try:
        payload = p0_acceptance_payload(record)
    except (TypeError, KeyError):
        return False
    matrices = record.get("calibration_basis_matrices")
    if (
        type(matrices) is not tuple
        or len(matrices) != 6
        or any(
            type(matrix) is not tuple
            or len(matrix) != 3
            or any(
                type(row) is not tuple or len(row) != 3 or any(type(value) is not Fraction for value in row)
                for row in matrix
            )
            for matrix in matrices
        )
    ):
        return False
    expected_matrices = tuple(
        tuple(tuple(row) for row in zip(*connection_basis(center), strict=True)) for center in A_CENTERS
    )
    expected_confirmation_matrices = tuple(
        tuple(tuple(row) for row in zip(*connection_basis(center), strict=True)) for center in V_CENTERS
    )
    expected_heldout_basis = connection_basis(HELDOUT_CENTER)
    expected_heldout_densities = tuple(
        sum(Fraction(area) * component for area, component in zip(HELDOUT_AREA_VECTOR, basis, strict=True))
        for basis in expected_heldout_basis
    )
    rows = [list(row) for matrix in matrices for row in matrix]
    gram = [[sum(row[i] * row[j] for row in rows) for j in range(3)] for i in range(3)]
    determinant = rational_determinant(gram)
    sigma = record.get("sigma_predictor_record")
    sigma_valid = (
        type(sigma) is MappingProxyType
        and type(sigma.get("coefficients")) is tuple
        and _strict_equal(sigma.get("center"), A_CENTERS[0])
        and _strict_equal(sigma.get("sigma_values"), (-1, 0, 1))
        and _strict_equal(
            sigma.get("positive_one_form"),
            predictor_one_form(A_CENTERS[0], sigma["coefficients"], 1),
        )
        and _strict_equal(
            sigma.get("positive_curvature"),
            predictor_curvature(A_CENTERS[0], sigma["coefficients"], 1),
        )
        and _strict_equal(
            sigma.get("negative_one_form"),
            tuple(-value for value in sigma["positive_one_form"]),
        )
        and _strict_equal(
            sigma.get("negative_curvature"),
            tuple(-value for value in sigma["positive_curvature"]),
        )
        and _strict_equal(sigma.get("zero_one_form"), (Fraction(0),) * 3)
        and _strict_equal(sigma.get("zero_curvature"), (Fraction(0),) * 3)
    )
    return (
        _strict_equal(record.get("calibration_centers"), A_CENTERS)
        and _strict_equal(matrices, expected_matrices)
        and _strict_equal(record.get("confirmation_centers"), V_CENTERS)
        and _strict_equal(record.get("confirmation_basis_matrices"), expected_confirmation_matrices)
        and _strict_equal(record.get("heldout_center"), HELDOUT_CENTER)
        and _strict_equal(record.get("heldout_area_vector"), HELDOUT_AREA_VECTOR)
        and _strict_equal(record.get("heldout_basis"), expected_heldout_basis)
        and _strict_equal(record.get("heldout_basis_densities"), expected_heldout_densities)
        and sigma_valid
        and type(record.get("gram_determinant")) is Fraction
        and _strict_equal(record["gram_determinant"], determinant)
        and fraction_vector_sha256((determinant,)) == P0_GRAM_SHA256
        and fraction_vector_sha256(expected_heldout_densities) == P0_HELDOUT_SHA256
        and canonical_exact_sha256(payload) == REVIEWED_P0_CERTIFICATE_SHA256
        and _strict_equal(record.get("certificate_sha256"), REVIEWED_P0_CERTIFICATE_SHA256)
        and record.get("reviewed_certificate_sha256_matches") is True
    )


def _firewall_record_valid(record: object) -> bool:
    if type(record) is not MappingProxyType:
        return False
    expected_keys = (
        "authority",
        "content_authentication_scope",
        "material_path_set",
        "material_path_set_sha256",
        "reviewed_material_path_set_sha256",
        "material_path_set_matches",
        "expected_package_file_names",
        "package_file_names",
        "package_file_set_sha256",
        "missing_package_files",
        "unexpected_package_files",
        "unexpected_package_directories",
        "package_file_set_matches",
        "artifact_directory_present",
        "source_lock_present",
        "file_records",
        "role_import_target_records",
        "all_material_files_present_and_canonical",
        "all_python_import_closures_clean",
        "protected_role_firewalls_clean",
    )
    if tuple(record) != expected_keys:
        return False
    file_records = record.get("file_records")
    if type(file_records) is not tuple or len(file_records) != len(MATERIAL_FILES):
        return False
    observed_import_targets: dict[str, set[str]] = {role: set() for role in ROLE_FILES}
    for observed, expected in zip(file_records, MATERIAL_FILES, strict=True):
        if type(observed) is not MappingProxyType or tuple(observed) != (
            "role",
            "relative_path",
            "kind",
            "ordinary_file",
            "size",
            "sha256_raw",
            "syntax_issues",
            "import_targets",
            "import_issues",
            "firewall_issues",
        ):
            return False
        if not _strict_equal(
            (observed["role"], observed["relative_path"], observed["kind"]),
            expected,
        ):
            return False
        if (
            observed["ordinary_file"] is not True
            or type(observed["size"]) is not int
            or observed["size"] <= 0
            or type(observed["sha256_raw"]) is not str
            or len(observed["sha256_raw"]) != 64
            or any(character not in "0123456789abcdef" for character in observed["sha256_raw"])
            or not _strict_equal(observed["syntax_issues"], ())
            or type(observed["import_targets"]) is not tuple
            or any(type(target) is not str for target in observed["import_targets"])
            or not _strict_equal(observed["import_issues"], ())
            or not _strict_equal(observed["firewall_issues"], ())
        ):
            return False
        if observed["kind"] == "python":
            if observed["role"] not in ROLE_FILES:
                return False
            observed_import_targets[observed["role"]].update(observed["import_targets"])
        elif not _strict_equal(observed["import_targets"], ()):
            return False
    raw_hashes = {item["relative_path"]: item["sha256_raw"] for item in file_records}
    if not _strict_equal(
        raw_hashes.get("experiments/generator_tensor_prediction_protocol/firewall.py"),
        REVIEWED_FIREWALL_SOURCE_SHA256,
    ) or not _strict_equal(
        raw_hashes.get("tests/experiments/test_generator_tensor_prediction_protocol.py"),
        REVIEWED_FOCUSED_TEST_SOURCE_SHA256,
    ):
        return False
    role_records = record.get("role_import_target_records")
    if type(role_records) is not tuple or len(role_records) != len(ROLE_FILES):
        return False
    for observed, role in zip(role_records, ROLE_FILES, strict=True):
        if type(observed) is not MappingProxyType or tuple(observed) != (
            "role",
            "import_targets",
            "import_targets_sha256",
        ):
            return False
        if (
            not _strict_equal(observed["role"], role)
            or type(observed["import_targets"]) is not tuple
            or any(type(target) is not str for target in observed["import_targets"])
            or not _strict_equal(
                observed["import_targets"],
                tuple(sorted(observed_import_targets[role])),
            )
            or not _strict_equal(
                observed["import_targets_sha256"],
                canonical_exact_sha256(observed["import_targets"]),
            )
            or not _strict_equal(
                observed["import_targets_sha256"],
                REVIEWED_ROLE_IMPORT_TARGETS_SHA256[role],
            )
        ):
            return False
    return (
        _strict_equal(
            record.get("authority"),
            "complete_source_only_path_type_hash_inventory_plus_normalized_AST_role_firewalls",
        )
        and _strict_equal(
            record.get("content_authentication_scope"),
            "raw_hash_inventory_nonauthoritative_until_git_index_source_lock",
        )
        and _strict_equal(record.get("material_path_set"), MATERIAL_FILES)
        and _strict_equal(record.get("material_path_set_sha256"), REVIEWED_MATERIAL_PATH_SET_SHA256)
        and _strict_equal(
            record.get("reviewed_material_path_set_sha256"),
            REVIEWED_MATERIAL_PATH_SET_SHA256,
        )
        and record.get("material_path_set_matches") is True
        and _strict_equal(record.get("expected_package_file_names"), EXPECTED_PACKAGE_FILE_NAMES)
        and _strict_equal(record.get("package_file_names"), EXPECTED_PACKAGE_FILE_NAMES)
        and _strict_equal(
            record.get("package_file_set_sha256"),
            canonical_exact_sha256(EXPECTED_PACKAGE_FILE_NAMES),
        )
        and _strict_equal(
            record.get("package_file_set_sha256"),
            REVIEWED_PACKAGE_FILE_SET_SHA256,
        )
        and _strict_equal(record.get("missing_package_files"), ())
        and _strict_equal(record.get("unexpected_package_files"), ())
        and _strict_equal(record.get("unexpected_package_directories"), ())
        and record.get("package_file_set_matches") is True
        and record.get("artifact_directory_present") is False
        and record.get("source_lock_present") is False
        and record.get("all_material_files_present_and_canonical") is True
        and record.get("all_python_import_closures_clean") is True
        and record.get("protected_role_firewalls_clean") is True
    )


def _protocol_record_valid(record: object) -> bool:
    if type(record) is not dict or tuple(record) != (
        "authority",
        "state",
        "event_log",
        "exposure_registry_sha256",
        "criterion_sha256",
        "reservation_status",
        "source_lock_present",
        "cryptographically_proven_unopened",
        "response_accessed",
        "response_unlock_command_exists",
    ):
        return False
    return (
        _strict_equal(record["authority"], "typed_pre_response_state_machine_without_unlock_transition")
        and _strict_equal(record["state"], "SOURCE_REVIEW_READY")
        and _strict_equal(
            record["event_log"],
            ("INIT", "EXPOSURE_FROZEN", "CRITERION_FROZEN", "SOURCE_REVIEW_READY"),
        )
        and _strict_equal(record["exposure_registry_sha256"], REVIEWED_EXPOSURE_REGISTRY_SHA256)
        and _strict_equal(record["criterion_sha256"], REVIEWED_CRITERION_SHA256)
        and _strict_equal(record["reservation_status"], RESERVATION_STATUS)
        and record["source_lock_present"] is False
        and record["cryptographically_proven_unopened"] is False
        and record["response_accessed"] is False
        and record["response_unlock_command_exists"] is False
    )


def build_certificates() -> dict[str, object]:
    n0 = krylov_no_go_certificate()
    p0 = connection_eligibility_certificate()
    return {
        "contract_issues": contract_issues(),
        "exposure_registry_issues": exposure_registry_issues(),
        "branch_identity": branch_identity_record(branch_bundle(n0["centers"][0])),
        "N0": n0,
        "P0": p0,
        "firewall": source_firewall_record(),
        "sentinel": sentinel_record(),
        "protocol": canonical_protocol_record(),
    }


def gate_results(certificates: dict[str, object]) -> MappingProxyType:
    n0 = certificates["N0"]
    p0 = certificates["P0"]
    firewall = certificates["firewall"]
    sentinel = certificates["sentinel"]
    protocol = certificates["protocol"]
    branch = certificates["branch_identity"]
    results = {
        ORDERED_GATES[0]: (
            certificates["contract_issues"] == ()
            and certificates["exposure_registry_issues"] == ()
            and MODEL_CONTRACT.response_accessed is False
            and MODEL_CONTRACT.response_unlock_available is False
        ),
        ORDERED_GATES[1]: (
            type(branch) is dict and all(type(value) is bool and value for value in branch.values())
        ),
        ORDERED_GATES[2]: (
            type(n0) is MappingProxyType
            and _n0_record_valid(n0)
            and n0.get("response_accessed") is False
            and n0.get("reviewed_certificate_sha256_matches") is True
            and _strict_equal(n0.get("closure_determinant_sha256"), N0_DETERMINANT_SHA256)
            and all(
                type(value) is tuple and len(value) == 3 and all(type(item) is Fraction for item in value)
                for value in n0.get("closure_rows", ())
            )
        ),
        ORDERED_GATES[3]: (
            _strict_equal(n0.get("closure_rank"), 3)
            and type(n0.get("closure_rank")) is int
            and _strict_equal(n0.get("closure_nullity"), 0)
            and type(n0.get("closure_nullity")) is int
            and n0.get("closure_determinant_positive") is True
        ),
        ORDERED_GATES[4]: (
            _strict_equal(n0.get("classification"), "NO_NONTRIVIAL_CLOSED_MEMBER")
            and _strict_equal(n0.get("disposition"), "INELIGIBLE_NOT_CLOSED")
            and _strict_equal(n0.get("only_closed_coefficient_vector"), (0, 0, 0))
            and n0.get("retrospective_diagnostic_used_for_acceptance") is False
        ),
        ORDERED_GATES[5]: (
            _strict_equal(p0.get("global_coefficient_count"), 3)
            and type(p0.get("global_coefficient_count")) is int
            and p0.get("pointwise_coefficients_forbidden") is True
            and _strict_equal(
                p0.get("gauge_invariant_scalar_inputs"),
                ("Re_Wilson", "Im_Wilson", "Tr_rho2"),
            )
        ),
        ORDERED_GATES[6]: (
            p0.get("basis_exterior_derivative_is_structurally_closed") is True
            and p0.get("coordinate_covariance_exact") is True
            and p0.get("zero_chord_Wilson_jet_zero") is True
            and p0.get("conjugate_bases_rank_three") is True
            and p0.get("simple_flux_conjugation_parity_holds") is False
            and p0.get("simple_flux_conjugation_parity_claimed") is False
            and _strict_equal(
                p0.get("flux_conjugation_scope"),
                "exact_conjugate_recompute_only; no unproved fixed-parity response law",
            )
            and _strict_equal(
                p0.get("count_reversal_rule"),
                "sigma_to_minus_sigma_negates_Bhat_and_Fhat",
            )
            and _strict_equal(
                p0.get("zero_current_rule"),
                "sigma_zero_gives_Bhat_zero_and_Fhat_zero",
            )
            and _strict_equal(
                p0.get("units"),
                MappingProxyType(
                    {
                        "u_v_p": "dimensionless",
                        "basis_two_forms": "dimensionless",
                        "kappa": "count",
                        "Fhat": "count",
                    }
                ),
            )
        ),
        ORDERED_GATES[7]: (
            _p0_design_valid(p0)
            and _strict_equal(p0.get("calibration_design_shape"), (18, 3))
            and _strict_equal(p0.get("calibration_rank"), 3)
            and type(p0.get("calibration_rank")) is int
            and _strict_equal(p0.get("calibration_overdetermination"), 15)
            and p0.get("all_local_basis_determinants_positive") is True
            and p0.get("gram_determinant_positive") is True
            and p0.get("reviewed_certificate_sha256_matches") is True
            and p0.get("gram_determinant_sha256") == P0_GRAM_SHA256
            and p0.get("basis_scope") == "exact_frozen_rational_points_only"
            and p0.get("uniform_purity_bias_derivative_box_proved") is False
            and type(p0.get("exact_gram_infinity_condition")) is Fraction
            and p0.get("exact_gram_infinity_condition") < 20
        ),
        ORDERED_GATES[8]: (
            p0.get("confirmation_points_eligible") is True
            and p0.get("heldout_basis_densities_nonzero") is True
            and p0.get("reviewed_certificate_sha256_matches") is True
            and p0.get("heldout_basis_density_sha256") == P0_HELDOUT_SHA256
            and p0.get("response_accessed") is False
            and p0.get("coefficients_fitted") is False
            and p0.get("confirmation_prediction_run") is False
            and p0.get("heldout_prediction_run") is False
        ),
        ORDERED_GATES[9]: (
            _firewall_record_valid(firewall)
            and sentinel.get("sentinel_refused") is True
            and sentinel.get("response_accessed") is False
            and sentinel.get("response_unlock_command_exists") is False
        ),
        ORDERED_GATES[10]: (_protocol_record_valid(protocol)),
        ORDERED_GATES[11]: (
            MODEL_CONTRACT.disposition == "PASS_INTERNAL_ANALYTIC"
            and MODEL_CONTRACT.evidence_status == "NO_EMPIRICAL_EVIDENCE"
            and MODEL_CONTRACT.relation_scope == "MODEL_SPECIFIC_RELATIONS_ONLY"
            and "successful-heldout" in MODEL_CONTRACT.claim_ceiling
        ),
    }
    return MappingProxyType(results)


def execute_program() -> tuple[dict[str, object], dict[str, object]]:
    certificates = build_certificates()
    gates = gate_results(certificates)
    failed = tuple(name for name, passed in gates.items() if passed is not True)
    cases = {}
    for name, owned_gates in CASE_GATE_MAP.items():
        natural = EXPECTED_CASE_DISPOSITIONS[name]
        cases[name] = {
            "owned_gates": owned_gates,
            "status": natural if not any(gate in failed for gate in owned_gates) else "FAIL",
            "natural_status": natural,
        }
    summary = {
        "experiment_id": MODEL_CONTRACT.experiment_id,
        "disposition": "PASS_INTERNAL_ANALYTIC" if not failed else "FAIL_INTERNAL_ANALYTIC",
        "evidence_status": MODEL_CONTRACT.evidence_status,
        "relation_scope": MODEL_CONTRACT.relation_scope,
        "claim_ceiling": MODEL_CONTRACT.claim_ceiling,
        "gate_count": len(gates),
        "passed_gate_count": sum(value is True for value in gates.values()),
        "failed_gates": failed,
        "gates": dict(gates),
        "cases": cases,
        "response_accessed": False,
        "source_lock_present": False,
        "artifacts_generated": False,
    }
    return summary, certificates
