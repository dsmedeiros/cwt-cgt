"""Deterministic five-file closure and transactional publication."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from functools import lru_cache
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, Sequence

from experiments.constitutive_map_3d_proof.artifacts import (
    _RESERVED_TRANSACTION_LEAVES,
    ArtifactGenerationRefused,
    ArtifactTransactionCrash,
    ArtifactVerificationError,
    _checked_path,
    _is_link_or_reparse,
    _publish_artifact_mapping,
    artifact_access_guard,
    artifact_transaction_paths,
    canonical_source_text_bytes,
    preflight_artifact_destination,
    recover_artifact_transaction,
    recursive_raw_inventory,
)

from .contract import MODEL_CONTRACT, canonical_registry_record
from .theorem import execute_program, jsonable

EXPERIMENT_DIR = Path(__file__).resolve().parent
SIM_ROOT = EXPERIMENT_DIR.parents[1]
REPO_ROOT = SIM_ROOT.parent
ARTIFACTS_DIR = EXPERIMENT_DIR / "artifacts"
EXPECTED_ARTIFACT_NAMES = frozenset(
    {"CHECKSUMS.json", "PROVENANCE.json", "REPORT.md", "records.json", "summary.json"}
)
SOURCE_HASH_DOMAIN = "sha256_utf8_lf_v1_CRLF_to_LF_only_no_BOM_no_bare_CR"
RAW_HASH_DOMAIN = "sha256_raw_bytes_v1"
REVIEWED_DEPENDENCY_POLICY_PATH = "requirements.test.txt"
DEPENDENCY_POLICY_PATH = REVIEWED_DEPENDENCY_POLICY_PATH
REVIEWED_DEPENDENCY_POLICY_SHA256 = "11cc1302a3896ed8af355bcfad65bc7aeec70ceeac2cec2c3a70ea456c507539"
REVIEWED_DEPENDENCY_POLICY_REQUIREMENTS = (
    "numpy>=1.24",
    "scipy>=1.10",
    "networkx>=3.1",
    "pandas>=2.0",
    "matplotlib>=3.7",
    "pytest>=7.4",
    "pydantic>=2.4",
    "pyyaml>=6.0",
    "typer>=0.9",
    "black==24.10.0",
    "mypy==1.11.2",
    "ruff==0.7.3",
)
REVIEWED_DEPENDENCY_POLICY_RECORD_SHA256 = "9bb568329235a52d9e9fb0adad92c378c1ea672569633b4269b6992b534b2a7c"

REVIEWED_CLEAN_CLI_LOCAL_MODULE_PATHS = (
    "cwt/__init__.py",
    "cwt/cgt/__init__.py",
    "cwt/cgt/_geom_compat.py",
    "cwt/cgt/benchmarks.py",
    "cwt/cgt/continuation.py",
    "cwt/cgt/lindblad.py",
    "cwt/cgt/loop_protocols.py",
    "cwt/cgt/models.py",
    "cwt/cgt/open_system.py",
    "cwt/cgt/runner.py",
    "cwt/geometry/berry.py",
    "cwt/geometry/branch_distance.py",
    "cwt/geometry/coherence.py",
    "cwt/geometry/mixed_state.py",
    "cwt/geometry/psi.py",
    "cwt/geometry/stats.py",
    "experiments/__init__.py",
    "experiments/constitutive_map_3d_proof/__init__.py",
    "experiments/constitutive_map_3d_proof/artifacts.py",
    "experiments/constitutive_map_3d_proof/bc3_core_regression.py",
    "experiments/constitutive_map_3d_proof/bc3_interval_model.py",
    "experiments/constitutive_map_3d_proof/bc3_lattice.py",
    "experiments/constitutive_map_3d_proof/bc3_midpoint_prediction.py",
    "experiments/constitutive_map_3d_proof/bc3_primitives.py",
    "experiments/constitutive_map_3d_proof/bc3_remainder.py",
    "experiments/constitutive_map_3d_proof/benchmark_c_alpha.py",
    "experiments/constitutive_map_3d_proof/binary64_interval.py",
    "experiments/constitutive_map_3d_proof/classifier.py",
    "experiments/constitutive_map_3d_proof/contract.py",
    "experiments/constitutive_map_3d_proof/exact.py",
    "experiments/constitutive_map_3d_proof/firewall.py",
    "experiments/constitutive_map_3d_proof/pipeline.py",
    "experiments/constitutive_map_3d_proof/qp1_ambient.py",
    "experiments/constitutive_map_3d_proof/qp1_geometry.py",
    "experiments/constitutive_map_3d_proof/qp1_kubo.py",
    "experiments/constitutive_map_3d_proof/response_oracle.py",
    "experiments/constitutive_map_3d_proof/theorem.py",
    "experiments/shared_generator_counting_curvature_proof/__init__.py",
    "experiments/shared_generator_counting_curvature_proof/artifacts.py",
    "experiments/shared_generator_counting_curvature_proof/contract.py",
    "experiments/shared_generator_counting_curvature_proof/core_binding.py",
    "experiments/shared_generator_counting_curvature_proof/counting_lane.py",
    "experiments/shared_generator_counting_curvature_proof/exact.py",
    "experiments/shared_generator_counting_curvature_proof/firewall.py",
    "experiments/shared_generator_counting_curvature_proof/generator.py",
    "experiments/shared_generator_counting_curvature_proof/geometry_lane.py",
    "experiments/shared_generator_counting_curvature_proof/oracle_lane.py",
    "experiments/shared_generator_counting_curvature_proof/pipeline.py",
    "experiments/shared_generator_counting_curvature_proof/run.py",
    "experiments/shared_generator_counting_curvature_proof/theorem.py",
)
REVIEWED_CLEAN_CLI_PATH_SET_SHA256 = "e708a74edcbdad8aa2b122bd06bdce4b314159ac8364d53416be08f5141c1b7c"
REVIEWED_MATERIAL_SOURCE_PATHS = tuple(
    sorted(
        REVIEWED_CLEAN_CLI_LOCAL_MODULE_PATHS
        + (
            "experiments/response_theorem_proof_program/THEOREM.md",
            "experiments/shared_generator_counting_curvature_proof/MODEL_CONTRACT.md",
            "tests/experiments/test_shared_generator_counting_curvature_proof.py",
        )
    )
)
REVIEWED_MATERIAL_SOURCE_PATHS_SHA256 = "c24ada0f17b1b30d6bd87eac33f7517231eabeb85b17b4fa9b5a62a981d2d014"

PREDECESSOR_ARTIFACT_DIRS = {
    "benchmark_d_lindblad_response_proof": SIM_ROOT
    / "experiments"
    / "benchmark_d_lindblad_response_proof"
    / "artifacts",
    "constitutive_map_3d_proof": SIM_ROOT / "experiments" / "constitutive_map_3d_proof" / "artifacts",
    "response_theorem_proof_program": SIM_ROOT
    / "experiments"
    / "response_theorem_proof_program"
    / "artifacts",
}
REVIEWED_PREDECESSOR_ROLE_PATHS = (
    (
        "benchmark_d_lindblad_response_proof",
        "experiments/benchmark_d_lindblad_response_proof/artifacts",
    ),
    ("constitutive_map_3d_proof", "experiments/constitutive_map_3d_proof/artifacts"),
    (
        "response_theorem_proof_program",
        "experiments/response_theorem_proof_program/artifacts",
    ),
)
REVIEWED_PREDECESSOR_ROLE_PATHS_SHA256 = "ca099a38e51199b0649467f362d12b6526b46171aab5771ba8133988807b1d51"


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def strict_json_bytes(payload: Any) -> bytes:
    return (
        json.dumps(
            jsonable(payload),
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def canonical_text_bytes(payload: bytes) -> bytes:
    return canonical_source_text_bytes(payload)


def _dependency_policy_file() -> Path:
    relative = DEPENDENCY_POLICY_PATH
    if type(relative) is not str or relative != REVIEWED_DEPENDENCY_POLICY_PATH:
        raise ArtifactVerificationError("dependency policy path differs from reviewed lexical path")
    parsed = PurePosixPath(relative)
    if (
        parsed.is_absolute()
        or parsed.as_posix() != relative
        or "." in parsed.parts
        or ".." in parsed.parts
        or len(parsed.parts) != 1
    ):
        raise ArtifactVerificationError("dependency policy path is not canonical PurePosixPath")
    return _checked_path(
        REPO_ROOT.joinpath(*parsed.parts),
        REPO_ROOT,
        expected_kind="file",
        label="dependency policy",
    )


def validate_dependency_policy_record(record: object) -> None:
    """Validate a producer result against the independently reviewed policy record."""
    canonical_source = canonical_text_bytes(_dependency_policy_file().read_bytes())
    actual_source_sha256 = sha256_bytes(canonical_source)
    if actual_source_sha256 != REVIEWED_DEPENDENCY_POLICY_SHA256:
        raise ArtifactVerificationError("dependency-policy source hash differs from reviewed identity")
    actual_requirements = tuple(
        line.strip()
        for line in canonical_source.decode("utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    )
    if actual_requirements != REVIEWED_DEPENDENCY_POLICY_REQUIREMENTS:
        raise ArtifactVerificationError("dependency policy source requirements differ from reviewed values")
    if type(record) is not dict:
        raise ArtifactVerificationError("dependency policy record is not an exact dictionary")
    expected_keys = {
        "authority",
        "path",
        "hash_domain",
        "sha256",
        "declared_requirements",
        "live_python_version_in_acceptance_bytes",
        "live_typer_version_in_acceptance_bytes",
    }
    if any(type(key) is not str for key in record) or set(record) != expected_keys:
        raise ArtifactVerificationError("dependency policy record keys differ from reviewed schema")
    for key in ("authority", "path", "hash_domain", "sha256"):
        if type(record[key]) is not str:
            raise ArtifactVerificationError(f"dependency policy field {key} has the wrong type")
    if record["authority"] != "deterministic_source_bound_dependency_declaration":
        raise ArtifactVerificationError("dependency policy authority differs from reviewed value")
    if record["path"] != REVIEWED_DEPENDENCY_POLICY_PATH:
        raise ArtifactVerificationError("dependency policy record path differs from reviewed value")
    if record["hash_domain"] != SOURCE_HASH_DOMAIN:
        raise ArtifactVerificationError("dependency policy hash domain differs from reviewed value")
    if record["sha256"] != actual_source_sha256:
        raise ArtifactVerificationError("dependency policy source hash differs from reviewed identity")
    requirements = record["declared_requirements"]
    if type(requirements) is not list or any(type(item) is not str for item in requirements):
        raise ArtifactVerificationError("dependency policy requirements have the wrong type")
    if tuple(requirements) != REVIEWED_DEPENDENCY_POLICY_REQUIREMENTS:
        raise ArtifactVerificationError("dependency policy requirements differ from reviewed values")
    for key in (
        "live_python_version_in_acceptance_bytes",
        "live_typer_version_in_acceptance_bytes",
    ):
        if type(record[key]) is not bool or record[key] is not False:
            raise ArtifactVerificationError(f"dependency policy field {key} is not exact false")
    if sha256_bytes(strict_json_bytes(record)) != REVIEWED_DEPENDENCY_POLICY_RECORD_SHA256:
        raise ArtifactVerificationError("dependency policy record digest differs from reviewed identity")


def dependency_policy_record() -> dict[str, object]:
    """Return the reviewed dependency declaration without live runtime versions."""
    path = _dependency_policy_file()
    canonical = canonical_text_bytes(path.read_bytes())
    digest = sha256_bytes(canonical)
    if digest != REVIEWED_DEPENDENCY_POLICY_SHA256:
        raise ArtifactVerificationError("dependency-policy source hash differs from reviewed identity")
    requirements = tuple(
        line.strip()
        for line in canonical.decode("utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    )
    record = {
        "authority": "deterministic_source_bound_dependency_declaration",
        "path": REVIEWED_DEPENDENCY_POLICY_PATH,
        "hash_domain": SOURCE_HASH_DOMAIN,
        "sha256": digest,
        "declared_requirements": list(requirements),
        "live_python_version_in_acceptance_bytes": False,
        "live_typer_version_in_acceptance_bytes": False,
    }
    validate_dependency_policy_record(record)
    return record


def _validate_provenance_dependency_policy(payload: bytes) -> None:
    try:
        provenance = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ArtifactVerificationError("PROVENANCE.json is not valid UTF-8 JSON") from exc
    if type(provenance) is not dict or "dependency_policy" not in provenance:
        raise ArtifactVerificationError("PROVENANCE.json lacks the dependency policy record")
    if provenance.get("dependency_policy_record_sha256") != REVIEWED_DEPENDENCY_POLICY_RECORD_SHA256:
        raise ArtifactVerificationError("PROVENANCE.json dependency policy digest is not reviewed")
    validate_dependency_policy_record(provenance["dependency_policy"])


def _material_file(relative: str) -> Path:
    parsed = PurePosixPath(relative)
    if not relative or parsed.is_absolute() or ".." in parsed.parts or parsed.as_posix() != relative:
        raise ArtifactVerificationError(f"noncanonical material source path: {relative}")
    return _checked_path(
        SIM_ROOT.joinpath(*parsed.parts),
        SIM_ROOT,
        expected_kind="file",
        label=f"material source {relative}",
    )


_CLEAN_IMPORT_SCRIPT = r"""
import json
import pathlib
import sys

root = pathlib.Path.cwd().resolve()
import experiments.shared_generator_counting_curvature_proof.run  # noqa: E402,F401

paths = set()
for module in tuple(sys.modules.values()):
    source = getattr(module, "__file__", None)
    if not source:
        continue
    try:
        resolved = pathlib.Path(source).resolve()
        relative = resolved.relative_to(root)
    except (OSError, ValueError):
        continue
    if resolved.suffix == ".py" and ".venv" not in relative.parts:
        paths.add(relative.as_posix())
print(json.dumps(sorted(paths), separators=(",", ":")))
"""


def clean_cli_local_module_paths() -> tuple[str, ...]:
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    completed = subprocess.run(
        [sys.executable, "-c", _CLEAN_IMPORT_SCRIPT],
        cwd=SIM_ROOT,
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
        env=environment,
    )
    parsed = json.loads(completed.stdout.strip())
    if not isinstance(parsed, list) or not all(isinstance(item, str) for item in parsed):
        raise ArtifactVerificationError("clean CLI local-module inventory is malformed")
    if parsed != sorted(set(parsed)):
        raise ArtifactVerificationError("clean CLI local-module inventory is not canonical")
    actual = tuple(parsed)
    if actual != REVIEWED_CLEAN_CLI_LOCAL_MODULE_PATHS:
        raise ArtifactVerificationError("clean CLI local-module path set differs from reviewed closure")
    if sha256_bytes(strict_json_bytes(list(actual))) != REVIEWED_CLEAN_CLI_PATH_SET_SHA256:
        raise ArtifactVerificationError("clean CLI local-module path-set fingerprint mismatch")
    return actual


def _package_source_paths() -> tuple[str, ...]:
    relative_paths: list[str] = []
    for child in sorted(EXPERIMENT_DIR.iterdir(), key=lambda item: item.name):
        if child.name in {"__pycache__", "artifacts"}:
            continue
        if _is_link_or_reparse(child):
            raise ArtifactVerificationError(f"package source is a link/reparse entry: {child.name}")
        if child.is_dir():
            inventory = recursive_raw_inventory(child, trust_anchor=SIM_ROOT)
            relative_paths.extend(
                (child / PurePosixPath(relative)).relative_to(SIM_ROOT).as_posix()
                for relative, item in inventory["entries"].items()
                if item["type"] == "file"
            )
        elif child.is_file():
            relative_paths.append(child.relative_to(SIM_ROOT).as_posix())
        else:
            raise ArtifactVerificationError(f"package source has unsupported type: {child.name}")
    return tuple(sorted(relative_paths))


def material_source_paths() -> tuple[str, ...]:
    actual = tuple(
        sorted(
            set(clean_cli_local_module_paths())
            | set(_package_source_paths())
            | {
                "experiments/response_theorem_proof_program/THEOREM.md",
                "tests/experiments/test_shared_generator_counting_curvature_proof.py",
            }
        )
    )
    if actual != REVIEWED_MATERIAL_SOURCE_PATHS:
        raise ArtifactVerificationError("material-source path set differs from reviewed closure")
    if sha256_bytes(strict_json_bytes(list(actual))) != REVIEWED_MATERIAL_SOURCE_PATHS_SHA256:
        raise ArtifactVerificationError("material-source path-set fingerprint mismatch")
    for relative in actual:
        _material_file(relative)
    return actual


def source_hashes(paths: Sequence[str]) -> dict[str, dict[str, str]]:
    return {
        relative: {
            "hash_domain": SOURCE_HASH_DOMAIN,
            "sha256": sha256_bytes(canonical_text_bytes(_material_file(relative).read_bytes())),
        }
        for relative in paths
    }


def predecessor_inventories() -> dict[str, dict[str, object]]:
    roles = tuple(
        (name, path.relative_to(SIM_ROOT).as_posix())
        for name, path in sorted(PREDECESSOR_ARTIFACT_DIRS.items())
    )
    if roles != REVIEWED_PREDECESSOR_ROLE_PATHS:
        raise ArtifactVerificationError("predecessor role/path set mismatch")
    if sha256_bytes(strict_json_bytes(list(roles))) != REVIEWED_PREDECESSOR_ROLE_PATHS_SHA256:
        raise ArtifactVerificationError("predecessor role/path-set fingerprint mismatch")
    return {
        name: recursive_raw_inventory(path, trust_anchor=SIM_ROOT)
        for name, path in sorted(PREDECESSOR_ARTIFACT_DIRS.items())
    }


def _overlaps(left: Path, right: Path) -> bool:
    return left == right or left in right.parents or right in left.parents


def preflight_destination(output_dir: Path) -> dict[str, object]:
    prior = preflight_artifact_destination(output_dir)
    candidate = output_dir.resolve(strict=False)
    canonical = ARTIFACTS_DIR.resolve(strict=False)
    if candidate != canonical and _overlaps(candidate, EXPERIMENT_DIR.resolve(strict=True)):
        raise ArtifactGenerationRefused("noncanonical output overlaps current experiment source tree")
    for role, predecessor in PREDECESSOR_ARTIFACT_DIRS.items():
        if _overlaps(candidate, predecessor.resolve(strict=True)):
            raise ArtifactGenerationRefused(f"output overlaps predecessor artifacts: {role}")
    return {**prior, "current_experiment_preflight": True}


@lru_cache(maxsize=1)
def _canonical_semantic_bytes() -> tuple[bytes, bytes]:
    summary, records = execute_program()
    return strict_json_bytes(summary), strict_json_bytes(records)


def require_semantic_pass(
    summary: Mapping[str, Any], records: Sequence[Mapping[str, Any]] | None = None
) -> None:
    expected_summary, expected_records = _canonical_semantic_bytes()
    candidate_records = json.loads(expected_records) if records is None else list(records)
    gates = [item for item in candidate_records if item.get("record_type") == "gate"]
    if (
        strict_json_bytes(dict(summary)) != expected_summary
        or strict_json_bytes(candidate_records) != expected_records
        or len(gates) != 14
        or [item.get("gate_id") for item in gates] != [f"G{index}" for index in range(14)]
        or len({item.get("gate_id") for item in gates}) != 14
        or any(item.get("natural_status") != "pass" or item.get("status") != "pass" for item in gates)
        or summary.get("disposition") != MODEL_CONTRACT.disposition
        or summary.get("formal_disposition") != MODEL_CONTRACT.disposition
        or summary.get("evidence_status") != MODEL_CONTRACT.evidence_status
        or summary.get("relation_scope") != MODEL_CONTRACT.relation_scope
        or summary.get("claim_ceiling") != MODEL_CONTRACT.claim_ceiling
        or summary.get("registry") != canonical_registry_record()
        or summary.get("failed_gates") != []
    ):
        raise ArtifactGenerationRefused("semantic shared-generator proof record refused")


def render_report(summary: Mapping[str, Any], records: Sequence[Mapping[str, Any]]) -> str:
    require_semantic_pass(summary, records)
    lines = [
        "# Shared-generator counting-curvature proof",
        "",
        f"- Disposition: **{summary['disposition']}**",
        f"- Evidence: **{summary['evidence_status']}**",
        f"- Scope: **{summary['relation_scope']}**",
        "- Acceptance authority: exact rational and Gaussian-rational algebra only.",
        "- Float core comparisons and finite differences are non-authoritative regressions.",
        "",
        "## T0 classical D0",
        "",
        "The actual diagonal stationary branch has rank two, projective/Uhlmann curvature zero,",
        "and exact nonzero counted-current response curvature in `(b,d,delta)`.",
        "The derived delta-box norm terms `4 h_max d_max`, `16 a d_max`, and",
        "`10 gamma_deph` sum to `3931/1000` at `t0=1/40`. Together with the",
        "induced spectral-operator-norm series bound `exp(x)-1<=x/(1-x)`, this",
        "gives inner-semigroup floor `32138/180345 > 3/20`. The exact positive",
        "jump/dephasing rates and no-reset lower factor `1997/2000` then",
        "give full-rank floor `5991/80000000`, contraction at least `1/50`,",
        "uniqueness, and Drazin bound `50`. At the center these are `1/25` and `25`.",
        "Classification: `SAME_GENERATOR_CLASSICAL_THREE_CONTROL_ZERO_SET_OBSTRUCTION`.",
        "",
        "## T1 coherent D0",
        "",
        "The complete requested h-box has exact stationary floor `2997/20000000`.",
        "The same induced-norm series bound, positive Lindblad rates, and no-reset lower",
        "factor `999/1000` certify contraction `1/25`, uniqueness, and Drazin bound `25`.",
        "The SLD metric is rank three. A fixed gauge makes rho, tangents, and SLDs real",
        "symmetric, hence mean Uhlmann curvature is zero while counted curvature is nonzero.",
        "Classification: `SAME_GENERATOR_COHERENT_THREE_CONTROL_ZERO_SET_OBSTRUCTION`.",
        "",
        "## T2 FCS eigenbundle",
        "",
        "For the tilted same-generator eigenbundle, `B=-partial_q A|0` and",
        "`F_R=-partial_q dA|0` exactly. The first q jet and independent parameter curl",
        "are computed algebraically. This normal counting-field jet is distinct from state CGT.",
        "The reversed counting orientation independently reruns the exact response and",
        "recomputes both `B` and `F`; both are the exact negatives of the forward values.",
        "Classification: `FCS_EXTENDED_EIGENBUNDLE_RESPONSE_IDENTITY_DISTINCT_FROM_STATE_CGT`.",
        "",
        "## Positive-map decision",
        "",
        "T0 is rank two and T1 has state curvature zero with nonzero response. This refutes",
        "only SAME_CURVATURE and frozen zero-preserving homogeneous Omega-only maps for the",
        "declared state geometry. Affine, nonlinear, and generator-dependent maps remain open.",
        "No fabricated heldout prediction is used.",
        "",
        "## Units and orientation scope",
        "",
        "`B_i` is count per control and `F_ij` is count per control-area; delta/h carry",
        "inverse model-time units. Qanti is half the exact orientation difference.",
        "Acceptance makes no finite-time loop, remainder, asymptotic-rate, or physical-time claim.",
        "The oracle capability authenticates the canonical criterion and primitive digests but",
        "carries no raw prediction values. Any unreviewed rule, non-Boolean flag, or prohibited",
        "positive-inference criterion is refused before prediction lock or oracle use.",
        "The reviewed callable and exact Fraction result schema are bound independently, and",
        "G8/G9 compare oracle B/F to separately frozen formal values. Independent record digests",
        "prevent a patched runtime certificate producer from redefining its acceptance reference.",
        "Deterministic provenance binds the canonical `requirements.test.txt` dependency policy;",
        "installed Python and Typer versions are excluded from artifact acceptance bytes.",
        "",
        "## Gates",
        "",
    ]
    for record in records:
        lines.append(f"- **{record['status'].upper()}** `{record['gate_id']}` — {record['name']}")
    lines.extend(
        [
            "",
            "## Claim ceiling",
            "",
            str(summary["claim_ceiling"]),
            "",
            "No universal, full-CWT, physical, empirical, or positive alignment claim is made.",
            "",
        ]
    )
    return "\n".join(lines)


def expected_artifact_bytes(
    *, predecessor_before: Mapping[str, Mapping[str, object]] | None = None
) -> dict[str, bytes]:
    paths = material_source_paths()
    predecessors = predecessor_inventories() if predecessor_before is None else dict(predecessor_before)
    summary, records = execute_program()
    require_semantic_pass(summary, records)
    summary_bytes = strict_json_bytes(summary)
    records_bytes = strict_json_bytes(records)
    report_bytes = render_report(summary, records).encode("utf-8")
    dependency_policy = dependency_policy_record()
    validate_dependency_policy_record(dependency_policy)
    predecessor_after = predecessor_inventories()
    if predecessors != predecessor_after:
        raise ArtifactGenerationRefused("predecessor artifacts changed during payload construction")
    provenance = {
        "schema_version": 1,
        "experiment_id": MODEL_CONTRACT.experiment_id,
        "artifact_kind": "internal_analytic_shared_generator_counting_curvature_proof",
        "disposition": summary["disposition"],
        "evidence_status": summary["evidence_status"],
        "relation_scope": summary["relation_scope"],
        "claim_ceiling": summary["claim_ceiling"],
        "exact_theorem_authority": True,
        "float_or_finite_difference_used_for_acceptance": False,
        "same_curvature_or_frozen_zero_preserving_homogeneous_Omega_map_claimed": False,
        "affine_nonlinear_generator_dependent_map_status": "OPEN",
        "finite_time_loop_or_remainder_claimed": False,
        "empirical_or_physical_evidence": False,
        "G2_floor_and_contraction_premises_derived": True,
        "G2_induced_norm_exponential_series_floor_derived": True,
        "nested_certificate_types_bound_by_canonical_JSON_bytes": True,
        "authoritative_certificate_records_bound_by_independent_reviewed_digests": True,
        "oracle_exact_Fraction_schema_and_callable_identity_bound": True,
        "oracle_B_and_F_compared_to_independently_frozen_formal_values": True,
        "reverse_count_B_and_F_recomputed_independently": True,
        "oracle_capability_canonical_payload_authenticated": True,
        "prohibited_positive_criterion_refused_before_lock": True,
        "canonical_registry": canonical_registry_record(),
        "source_hash_domain": SOURCE_HASH_DOMAIN,
        "source_path_set_sha256": REVIEWED_MATERIAL_SOURCE_PATHS_SHA256,
        "source_hashes": source_hashes(paths),
        "clean_cli_local_module_paths": list(REVIEWED_CLEAN_CLI_LOCAL_MODULE_PATHS),
        "clean_cli_local_module_path_set_sha256": REVIEWED_CLEAN_CLI_PATH_SET_SHA256,
        "predecessor_role_paths": [list(item) for item in REVIEWED_PREDECESSOR_ROLE_PATHS],
        "predecessor_role_paths_sha256": REVIEWED_PREDECESSOR_ROLE_PATHS_SHA256,
        "predecessor_artifact_inventories": predecessors,
        "predecessor_nonmutation": {
            "method": (
                "recursive_raw_inventory_before_and_after_payload_construction_plus_"
                "transactional_precommit_publication_check"
            ),
            "unchanged": predecessors == predecessor_after,
        },
        "payload_sha256": {
            "REPORT.md": sha256_bytes(report_bytes),
            "records.json": sha256_bytes(records_bytes),
            "summary.json": sha256_bytes(summary_bytes),
        },
        "dependency_policy": dependency_policy,
        "dependency_policy_record_sha256": REVIEWED_DEPENDENCY_POLICY_RECORD_SHA256,
        "run_command": (
            "cd cwt-sim && .venv/Scripts/python.exe "
            "experiments/shared_generator_counting_curvature_proof/run.py run"
        ),
        "verify_command": (
            "cd cwt-sim && .venv/Scripts/python.exe "
            "experiments/shared_generator_counting_curvature_proof/run.py verify"
        ),
    }
    provenance_bytes = strict_json_bytes(provenance)
    checksums = {
        "schema_version": 1,
        "hash_domain": RAW_HASH_DOMAIN,
        "files": {
            "PROVENANCE.json": sha256_bytes(provenance_bytes),
            "REPORT.md": sha256_bytes(report_bytes),
            "records.json": sha256_bytes(records_bytes),
            "summary.json": sha256_bytes(summary_bytes),
        },
    }
    return {
        "CHECKSUMS.json": strict_json_bytes(checksums),
        "PROVENANCE.json": provenance_bytes,
        "REPORT.md": report_bytes,
        "records.json": records_bytes,
        "summary.json": summary_bytes,
    }


def write_artifacts(
    output_dir: Path = ARTIFACTS_DIR,
    *,
    _fault_injector=None,
) -> dict[str, Path]:
    preflight_destination(output_dir)
    predecessor_before = predecessor_inventories()
    expected = expected_artifact_bytes(predecessor_before=predecessor_before)
    if any(b"\r" in payload for payload in expected.values()):
        raise ArtifactGenerationRefused("artifact payload is not strict LF")

    def publication_check(checkpoint: str) -> None:
        if checkpoint == "after_target_verify" and predecessor_inventories() != predecessor_before:
            raise ArtifactVerificationError("predecessor artifacts changed during publication")
        if _fault_injector is not None:
            _fault_injector(checkpoint)

    _publish_artifact_mapping(output_dir, expected, fault_injector=publication_check)
    paths = artifact_transaction_paths(output_dir)
    return {name: paths.target / name for name in sorted(expected)}


def _read_generation(output_dir: Path) -> dict[str, bytes]:
    paths = artifact_transaction_paths(output_dir)
    inventory = recursive_raw_inventory(paths.target, trust_anchor=paths.parent)
    entries = inventory["entries"]
    if set(entries) != EXPECTED_ARTIFACT_NAMES or any(item["type"] != "file" for item in entries.values()):
        raise ArtifactVerificationError("artifact closure differs from the exact five-file mapping")
    return {name: (paths.target / name).read_bytes() for name in sorted(entries)}


def verify_artifacts(output_dir: Path = ARTIFACTS_DIR) -> dict[str, object]:
    with artifact_access_guard(output_dir):
        actual = _read_generation(output_dir)
        _validate_provenance_dependency_policy(actual["PROVENANCE.json"])
        expected = expected_artifact_bytes()
        if actual != expected:
            differing = sorted(name for name in expected if actual.get(name) != expected[name])
            raise ArtifactVerificationError(f"artifact content mismatch: {differing}")
        summary, records = execute_program()
        require_semantic_pass(summary, records)
        return {
            "status": summary["disposition"],
            "evidence_status": summary["evidence_status"],
            "relation_scope": summary["relation_scope"],
            "artifact_count": len(expected),
            "source_count": len(material_source_paths()),
            "clean_cli_local_module_count": len(clean_cli_local_module_paths()),
            "predecessor_count": len(PREDECESSOR_ARTIFACT_DIRS),
        }


__all__ = [
    "ARTIFACTS_DIR",
    "ArtifactGenerationRefused",
    "ArtifactTransactionCrash",
    "ArtifactVerificationError",
    "_RESERVED_TRANSACTION_LEAVES",
    "artifact_access_guard",
    "artifact_transaction_paths",
    "clean_cli_local_module_paths",
    "dependency_policy_record",
    "validate_dependency_policy_record",
    "expected_artifact_bytes",
    "material_source_paths",
    "predecessor_inventories",
    "preflight_destination",
    "recover_artifact_transaction",
    "require_semantic_pass",
    "verify_artifacts",
    "write_artifacts",
]
