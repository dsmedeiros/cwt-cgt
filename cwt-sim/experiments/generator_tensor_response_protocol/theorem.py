"""Pre-access theorem and source-gate composition; never invokes the broker."""

from __future__ import annotations

import sys
from fractions import Fraction
from pathlib import Path

from .anchors import anchor_record
from .authority import ACCESS_LEDGER_DIR
from .contract import (
    CALIBRATION_CENTERS,
    CHORD_RADIUS,
    COMPONENT_ORDER,
    CONTRACT_SHA256,
    GATE_REGISTRY_SHA256,
    MODEL_CONTRACT,
    NORMALIZED_CURVATURE_SCALES,
    ORDERED_GATES,
    ZERO_RADIUS,
    calibration_call_plan,
    contract_issues,
    contract_record,
)
from .firewall import source_firewall_record
from .geometry_plan import geometry_plan, geometry_plan_record
from .protocol import ProtocolSession, ProtocolState

PACKAGE_DIR = Path(__file__).resolve().parent
SIM_ROOT = PACKAGE_DIR.parents[1]
ADAPTER_SOURCE_LOCK_PATH = SIM_ROOT / "experiments/generator_tensor_response_protocol.SOURCE_LOCK.json"
ARTIFACTS_DIR = PACKAGE_DIR / "artifacts"


def _producer_modules_loaded() -> tuple[str, ...]:
    prefix = "experiments.loop_flux_counting_curvature_proof"
    return tuple(sorted(name for name in sys.modules if name == prefix or name.startswith(prefix + ".")))


def execute_program() -> tuple[dict[str, object], dict[str, object]]:
    """Recompute response-free adapter eligibility from locked source identities."""

    loaded_before = _producer_modules_loaded()
    anchors = anchor_record()
    plan = geometry_plan()
    geometry = geometry_plan_record()
    firewall = source_firewall_record()
    session = ProtocolSession(plan)
    loaded_after = _producer_modules_loaded()
    call_plan = calibration_call_plan()
    center_major = all(
        call_plan[2 * index] == (f"A{index + 1}", center, CHORD_RADIUS)
        and call_plan[2 * index + 1] == (f"A{index + 1}", center, ZERO_RADIUS)
        for index, center in enumerate(CALIBRATION_CENTERS)
    )
    source_lock_present = ADAPTER_SOURCE_LOCK_PATH.exists()
    artifacts_present = ARTIFACTS_DIR.exists()
    access_ledger_present = ACCESS_LEDGER_DIR.exists()
    gate_results = {
        ORDERED_GATES[0]: not contract_issues()
        and contract_record()["disposition"] == "PASS_INTERNAL_ANALYTIC"
        and anchors["predictor_source_commit_oid"] == MODEL_CONTRACT.predictor_source_commit_oid
        and anchors["predictor_metadata_commit_oid"] == MODEL_CONTRACT.predictor_metadata_commit_oid,
        ORDERED_GATES[1]: geometry["response_accessed"] is False
        and geometry["producer_capability_received"] is False
        and geometry["component_order"] == COMPONENT_ORDER
        and len(plan.calibration_matrices) == 6
        and len(plan.confirmation_matrices) == 2,
        ORDERED_GATES[2]: anchors["producer_source_lock_sha256"] == MODEL_CONTRACT.producer_source_lock_sha256
        and len(anchors["producer_callable_records"]) == 3
        and anchors["response_values_read"] is False
        and anchors["producer_modules_imported"] is False,
        ORDERED_GATES[3]: MODEL_CONTRACT.orientation == 1
        and type(MODEL_CONTRACT.orientation) is int
        and MODEL_CONTRACT.component_order == COMPONENT_ORDER
        and MODEL_CONTRACT.normalized_curvature_scales == NORMALIZED_CURVATURE_SCALES
        and NORMALIZED_CURVATURE_SCALES == (Fraction(1, 300), Fraction(1, 300), Fraction(1, 2500)),
        ORDERED_GATES[4]: len(call_plan) == 12
        and center_major
        and MODEL_CONTRACT.calibration_sample_call_count == 12,
        ORDERED_GATES[5]: MODEL_CONTRACT.coefficient_count == 3
        and MODEL_CONTRACT.calibration_equation_count == 18
        and not any(
            (
                MODEL_CONTRACT.intercept_allowed,
                MODEL_CONTRACT.normalization_allowed,
                MODEL_CONTRACT.sign_flip_allowed,
                MODEL_CONTRACT.weights_allowed,
                MODEL_CONTRACT.regularization_allowed,
                MODEL_CONTRACT.tolerance_allowed,
                MODEL_CONTRACT.fallback_allowed,
                MODEL_CONTRACT.orientation_averaging_allowed,
                MODEL_CONTRACT.extra_curvature_factor_allowed,
                MODEL_CONTRACT.degenerate_fit_prediction_allowed,
            )
        ),
        ORDERED_GATES[6]: session.state is ProtocolState.PREDICTOR_LOCKED
        and session.fit is None
        and session.predictions is None,
        ORDERED_GATES[7]: MODEL_CONTRACT.confirmation_center_count == 2
        and len(plan.confirmation_call_plan) == 4,
        ORDERED_GATES[8]: plan.heldout_area_vector == (1, -1, 3) and len(plan.heldout_call_plan) == 2,
        ORDERED_GATES[9]: session.incident_ledger == ()
        and session.state is ProtocolState.PREDICTOR_LOCKED
        and not access_ledger_present
        and MODEL_CONTRACT.local_ledger_grants_phase_authority is False
        and MODEL_CONTRACT.durable_outer_ledger_binding_required is True
        and MODEL_CONTRACT.durable_outer_ledger_outside_detached_worktree is True
        and MODEL_CONTRACT.durable_outer_ledger_keyed_by_authority_session_sequence is True
        and MODEL_CONTRACT.outer_provisions_and_verifies_durable_ledger is True
        and MODEL_CONTRACT.outer_refuses_launch_when_exact_ledger_key_exists is True
        and MODEL_CONTRACT.child_atomically_consumes_ledger_key_before_producer_import is True
        and MODEL_CONTRACT.durable_outer_ledger_process_controlled_not_cryptographic is True
        and MODEL_CONTRACT.durable_ledger_evidence_requires_later_external_commit is True
        and MODEL_CONTRACT.next_phase_requires_committed_external_outcome is True
        and MODEL_CONTRACT.external_outcome_delta_path_count == 2,
        ORDERED_GATES[10]: firewall["protected_role_firewalls_clean"] is True
        and loaded_before == ()
        and loaded_after == ()
        and MODEL_CONTRACT.authoritative_response_entrypoint
        == "outer_trusted_detached_launcher_to_fresh_isolated_whole_phase_child_only"
        and MODEL_CONTRACT.outer_trusted_orchestrator_is_sole_access_authority is True
        and MODEL_CONTRACT.child_argv_and_globals_are_defense_in_depth is True
        and MODEL_CONTRACT.arbitrary_same_process_memory_or_syscall_compromise_out_of_scope is True
        and MODEL_CONTRACT.detached_exact_lock_checkout_required is True
        and MODEL_CONTRACT.adjacent_python_cache_refused is True
        and MODEL_CONTRACT.external_empty_pycache_prefix_required is True
        and MODEL_CONTRACT.trusted_absolute_python_and_git_required is True
        and MODEL_CONTRACT.post_result_external_verification_required is True
        and MODEL_CONTRACT.inprocess_response_api_authoritative is False,
        ORDERED_GATES[11]: not artifacts_present
        and MODEL_CONTRACT.historical_unopened_claimed is False
        and MODEL_CONTRACT.evidence_status == "NO_EMPIRICAL_EVIDENCE"
        and MODEL_CONTRACT.relation_scope == "MODEL_SPECIFIC_RELATIONS_ONLY",
    }
    failed = tuple(name for name in ORDERED_GATES if gate_results.get(name) is not True)
    summary = {
        "experiment_id": MODEL_CONTRACT.experiment_id,
        "disposition": "PASS_INTERNAL_ANALYTIC" if not failed else "REFUSED",
        "evidence_status": MODEL_CONTRACT.evidence_status,
        "relation_scope": MODEL_CONTRACT.relation_scope,
        "claim_ceiling": MODEL_CONTRACT.claim_ceiling,
        "response_accessed": False,
        "producer_modules_loaded": loaded_after,
        "adapter_source_lock_present": source_lock_present,
        "artifacts_present": artifacts_present,
        "access_ledger_present": access_ledger_present,
        "protocol_state": session.state.value,
        "authoritative_response_entrypoint": MODEL_CONTRACT.authoritative_response_entrypoint,
        "local_ledger_grants_phase_authority": MODEL_CONTRACT.local_ledger_grants_phase_authority,
        "next_phase_requires_committed_external_outcome": (
            MODEL_CONTRACT.next_phase_requires_committed_external_outcome
        ),
        "gate_count": len(ORDERED_GATES),
        "passed_gate_count": len(ORDERED_GATES) - len(failed),
        "failed_gates": failed,
        "contract_sha256": CONTRACT_SHA256,
        "gate_registry_sha256": GATE_REGISTRY_SHA256,
        "geometry_plan_sha256": plan.plan_sha256,
        "criterion_sha256": plan.criterion_sha256,
    }
    records = {
        "contract": contract_record(),
        "anchors": anchors,
        "geometry_plan": geometry,
        "firewall": firewall,
        "preaccess_state": {
            "state": session.state.value,
            "incident_ledger": session.incident_ledger,
            "fit": None,
            "predictions": None,
            "response_stream": (),
            "output_stream": (),
            "access_ledger_present": access_ledger_present,
            "inprocess_response_api_authoritative": (MODEL_CONTRACT.inprocess_response_api_authoritative),
            "outer_trusted_orchestrator_is_sole_access_authority": (
                MODEL_CONTRACT.outer_trusted_orchestrator_is_sole_access_authority
            ),
            "child_argv_and_globals_are_defense_in_depth": (
                MODEL_CONTRACT.child_argv_and_globals_are_defense_in_depth
            ),
            "external_outcome_delta_path_count": MODEL_CONTRACT.external_outcome_delta_path_count,
            "durable_outer_ledger_binding_required": (MODEL_CONTRACT.durable_outer_ledger_binding_required),
            "durable_outer_ledger_outside_detached_worktree": (
                MODEL_CONTRACT.durable_outer_ledger_outside_detached_worktree
            ),
            "durable_outer_ledger_keyed_by_authority_session_sequence": (
                MODEL_CONTRACT.durable_outer_ledger_keyed_by_authority_session_sequence
            ),
            "outer_provisions_and_verifies_durable_ledger": (
                MODEL_CONTRACT.outer_provisions_and_verifies_durable_ledger
            ),
            "outer_refuses_launch_when_exact_ledger_key_exists": (
                MODEL_CONTRACT.outer_refuses_launch_when_exact_ledger_key_exists
            ),
            "child_atomically_consumes_ledger_key_before_producer_import": (
                MODEL_CONTRACT.child_atomically_consumes_ledger_key_before_producer_import
            ),
            "durable_outer_ledger_process_controlled_not_cryptographic": (
                MODEL_CONTRACT.durable_outer_ledger_process_controlled_not_cryptographic
            ),
            "durable_ledger_evidence_requires_later_external_commit": (
                MODEL_CONTRACT.durable_ledger_evidence_requires_later_external_commit
            ),
        },
        "gate_results": gate_results,
    }
    return summary, records
