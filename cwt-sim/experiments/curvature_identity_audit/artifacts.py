"""Deterministic isolated artifacts and source closure for the audit."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import stat
import subprocess
import sys
from pathlib import Path, PurePosixPath
from typing import Any, Mapping

import numpy as np
import typer

from .classifier import registry_gate_names
from .contract import MODEL_CONTRACT, canonical_registry_record, expected_case_dispositions
from .theorem import execute_program

EXPERIMENT_DIR = Path(__file__).resolve().parent
SIM_ROOT = EXPERIMENT_DIR.parents[1]
REPO_ROOT = SIM_ROOT.parent
ARTIFACTS_DIR = EXPERIMENT_DIR / "artifacts"
EXPECTED_ARTIFACT_NAMES = {
    "CHECKSUMS.json",
    "PROVENANCE.json",
    "REPORT.md",
    "records.json",
    "summary.json",
}
SOURCE_HASH_DOMAIN = "sha256_utf8_lf_v1"
SOURCE_HASH_DOMAIN_DEFINITION = (
    "strict UTF-8 with BOM forbidden; CRLF maps to LF only; remaining bare CR is rejected; "
    "no whitespace, Unicode, or other normalization"
)
RAW_HASH_DOMAIN = "sha256_raw_bytes_v1"

CLEAN_CLI_LOCAL_MODULE_PATHS = (
    "cwt/__init__.py",
    "cwt/cgt/__init__.py",
    "cwt/cgt/_geom_compat.py",
    "cwt/cgt/benchmarks.py",
    "cwt/cgt/continuation.py",
    "cwt/cgt/geometry.py",
    "cwt/cgt/lindblad.py",
    "cwt/cgt/loop_protocols.py",
    "cwt/cgt/models.py",
    "cwt/cgt/open_system.py",
    "cwt/cgt/runner.py",
    "cwt/geometry/berry.py",
    "cwt/geometry/branch_distance.py",
    "cwt/geometry/coherence.py",
    "cwt/geometry/curvature.py",
    "cwt/geometry/mixed_state.py",
    "cwt/geometry/psi.py",
    "cwt/geometry/stats.py",
    "cwt/operator/L_map.py",
    "experiments/__init__.py",
    "experiments/benchmark_d_lindblad_response_proof/__init__.py",
    "experiments/benchmark_d_lindblad_response_proof/adapter.py",
    "experiments/benchmark_d_lindblad_response_proof/certificates.py",
    "experiments/benchmark_d_lindblad_response_proof/contract.py",
    "experiments/benchmark_d_lindblad_response_proof/exact_math.py",
    "experiments/curvature_identity_audit/__init__.py",
    "experiments/curvature_identity_audit/artifacts.py",
    "experiments/curvature_identity_audit/benchmark_c.py",
    "experiments/curvature_identity_audit/benchmark_d.py",
    "experiments/curvature_identity_audit/classifier.py",
    "experiments/curvature_identity_audit/common_origin.py",
    "experiments/curvature_identity_audit/contract.py",
    "experiments/curvature_identity_audit/exact.py",
    "experiments/curvature_identity_audit/qp1.py",
    "experiments/curvature_identity_audit/run.py",
    "experiments/curvature_identity_audit/theorem.py",
    "experiments/independent_response_theorem/__init__.py",
    "experiments/independent_response_theorem/response.py",
    "experiments/independent_response_theorem/theorem.py",
)
ADDITIONAL_MATERIAL_TEXT_PATHS = (
    "experiments/curvature_identity_audit/MODEL_CONTRACT.md",
    "experiments/independent_response_theorem/PROTOCOL_LOCK.md",
    "experiments/response_theorem_proof_program/THEOREM.md",
    "tests/experiments/test_curvature_identity_audit.py",
)

PREDECESSOR_ARTIFACT_DIRS = {
    "benchmark_c_independent_response": (
        SIM_ROOT / "experiments" / "independent_response_theorem" / "artifacts"
    ),
    "generic_response_theorem": (SIM_ROOT / "experiments" / "response_theorem_proof_program" / "artifacts"),
    "benchmark_d_lindblad_response": (
        SIM_ROOT / "experiments" / "benchmark_d_lindblad_response_proof" / "artifacts"
    ),
}
CURRENT_AUTHORITY_PATHS = (
    REPO_ROOT / "theory.md",
    SIM_ROOT / "theory" / "Theory.md",
    SIM_ROOT / "cgt_benchmarks" / "reports" / "CWT-CGT_Proof_Status_v1.md",
    SIM_ROOT / "cgt_benchmarks" / "reports" / "PROJECT_INDEX.md",
)


class ArtifactVerificationError(RuntimeError):
    """Raised when deterministic artifact or provenance closure differs."""


class ArtifactGenerationRefused(RuntimeError):
    """Raised before writing when any analytic gate is not passing."""


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def strict_json_bytes(payload: Any) -> bytes:
    return (json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n").encode(
        "utf-8"
    )


def canonical_source_text_bytes(raw: bytes) -> bytes:
    """Apply only the declared portable source-text transform."""

    if raw.startswith(b"\xef\xbb\xbf"):
        raise ValueError("UTF-8 BOM is forbidden")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("source text must be strict UTF-8") from exc
    text = text.replace("\r\n", "\n")
    if "\r" in text:
        raise ValueError("bare CR is forbidden")
    return text.encode("utf-8")


def _is_link_or_reparse(path: Path) -> bool:
    metadata = path.lstat()
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    return path.is_symlink() or bool(getattr(metadata, "st_file_attributes", 0) & reparse_flag)


def _lexical_absolute(path: Path) -> Path:
    return Path(os.path.abspath(os.fspath(path)))


def _ordinary_path_from_trust_anchor(
    path: Path,
    trust_anchor: Path,
    *,
    expected_kind: str,
    label: str,
) -> Path:
    """Reject lexical escape, ancestor links/reparse points, and resolved escape."""

    anchor = _lexical_absolute(trust_anchor)
    candidate = _lexical_absolute(path)
    try:
        relative = candidate.relative_to(anchor)
    except ValueError as exc:
        raise ArtifactVerificationError(f"{label} escapes fixed trust anchor: {candidate}") from exc
    current = anchor
    for part in (None, *relative.parts):
        if part is not None:
            current /= part
        if not os.path.lexists(current):
            raise ArtifactVerificationError(f"{label} path component is missing: {current}")
        if _is_link_or_reparse(current):
            raise ArtifactVerificationError(f"{label} ancestor is a link/reparse point: {current}")
    if expected_kind == "file" and not candidate.is_file():
        raise ArtifactVerificationError(f"{label} is not an ordinary file: {candidate}")
    if expected_kind == "directory" and not candidate.is_dir():
        raise ArtifactVerificationError(f"{label} is not an ordinary directory: {candidate}")
    try:
        candidate.resolve(strict=True).relative_to(anchor.resolve(strict=True))
    except (OSError, ValueError) as exc:
        raise ArtifactVerificationError(
            f"{label} resolved path escapes fixed trust anchor: {candidate}"
        ) from exc
    return candidate


def _canonical_relative_path(relative: str) -> PurePosixPath:
    parsed = PurePosixPath(relative)
    if parsed.is_absolute() or ".." in parsed.parts or parsed.as_posix() != relative or not relative:
        raise ArtifactVerificationError(f"noncanonical relative path: {relative}")
    return parsed


def _ordinary_material_file(relative: str) -> Path:
    parsed = _canonical_relative_path(relative)
    path = SIM_ROOT.joinpath(*parsed.parts)
    return _ordinary_path_from_trust_anchor(
        path,
        SIM_ROOT,
        expected_kind="file",
        label=f"material source {relative}",
    )


def text_source_relative_paths() -> tuple[str, ...]:
    return tuple(sorted(set(CLEAN_CLI_LOCAL_MODULE_PATHS) | set(ADDITIONAL_MATERIAL_TEXT_PATHS)))


def source_hashes() -> dict[str, dict[str, str]]:
    """Hash every material source in the canonical UTF-8/LF domain."""

    return {
        relative: {
            "hash_domain": SOURCE_HASH_DOMAIN,
            "sha256": sha256_bytes(
                canonical_source_text_bytes(_ordinary_material_file(relative).read_bytes())
            ),
        }
        for relative in text_source_relative_paths()
    }


_CLEAN_IMPORT_SCRIPT = r"""
import json
import pathlib
import sys

root = pathlib.Path.cwd().resolve()
import experiments.curvature_identity_audit.run  # noqa: E402,F401

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
    return tuple(parsed)


def assert_clean_cli_source_closure() -> tuple[str, ...]:
    actual = clean_cli_local_module_paths()
    if actual != CLEAN_CLI_LOCAL_MODULE_PATHS:
        raise ArtifactVerificationError(
            "clean CLI source closure mismatch: "
            f"absent={sorted(set(CLEAN_CLI_LOCAL_MODULE_PATHS)-set(actual))}, "
            f"undeclared={sorted(set(actual)-set(CLEAN_CLI_LOCAL_MODULE_PATHS))}"
        )
    return actual


def recursive_raw_inventory(
    root: Path,
    *,
    trust_anchor: Path | None = None,
) -> dict[str, object]:
    """Inventory path/type-bound ordinary files without following links."""

    root = _ordinary_path_from_trust_anchor(
        root,
        root.parent if trust_anchor is None else trust_anchor,
        expected_kind="directory",
        label="recursive inventory root",
    )
    entries: dict[str, dict[str, str]] = {}

    def visit(directory: Path, prefix: PurePosixPath) -> None:
        with os.scandir(directory) as scanned:
            children = sorted(scanned, key=lambda item: item.name)
        for child in children:
            relative = (prefix / child.name).as_posix()
            path = Path(child.path)
            if _is_link_or_reparse(path):
                raise ArtifactVerificationError(
                    f"predecessor closure contains link/reparse entry: {relative}"
                )
            if child.is_dir(follow_symlinks=False):
                entries[relative] = {"type": "directory"}
                visit(path, PurePosixPath(relative))
            elif child.is_file(follow_symlinks=False):
                entries[relative] = {
                    "type": "file",
                    "hash_domain": RAW_HASH_DOMAIN,
                    "sha256": sha256_bytes(path.read_bytes()),
                }
            else:
                raise ArtifactVerificationError(f"unsupported predecessor entry type: {relative}")

    visit(root, PurePosixPath())
    if not entries or not any(value["type"] == "file" for value in entries.values()):
        raise ArtifactVerificationError(f"predecessor closure contains no files: {root}")
    return {
        "closure": "recursive_path_and_type_bound_no_symlink_or_reparse",
        "entry_count": len(entries),
        "entries": entries,
        "inventory_sha256": sha256_bytes(strict_json_bytes(entries)),
    }


def predecessor_inventories() -> dict[str, dict[str, object]]:
    return {
        name: recursive_raw_inventory(path, trust_anchor=SIM_ROOT)
        for name, path in sorted(PREDECESSOR_ARTIFACT_DIRS.items())
    }


def _path_overlap(left: Path, right: Path) -> bool:
    return left == right or left in right.parents or right in left.parents


def _reject_reparse_in_existing_ancestor_chain(path: Path, *, label: str) -> Path:
    candidate = _lexical_absolute(path)
    current = Path(candidate.anchor)
    for part in candidate.parts[1:]:
        current /= part
        if not os.path.lexists(current):
            break
        if _is_link_or_reparse(current):
            raise ArtifactGenerationRefused(f"{label} contains a link/reparse ancestor: {current}")
    return candidate


def _preflight_existing_destination_entries(candidate: Path) -> tuple[str, ...]:
    """Reject unsafe or unexpected existing entries before any artifact byte is written."""

    if not candidate.exists():
        return ()
    with os.scandir(candidate) as scanned:
        children = sorted(scanned, key=lambda item: item.name)
    names = []
    for child in children:
        path = Path(child.path)
        if _is_link_or_reparse(path):
            raise ArtifactGenerationRefused(f"artifact destination contains a link/reparse entry: {path}")
        if not child.is_file(follow_symlinks=False):
            raise ArtifactGenerationRefused(f"artifact destination contains a non-file entry: {path}")
        if child.name not in EXPECTED_ARTIFACT_NAMES:
            raise ArtifactGenerationRefused(f"artifact destination contains an unexpected file: {path}")
        if path.lstat().st_nlink != 1:
            raise ArtifactGenerationRefused(f"artifact destination contains a multiply-linked file: {path}")
        names.append(child.name)
    return tuple(names)


def preflight_artifact_destination(output_dir: Path) -> dict[str, object]:
    """Prove destination disjointness before directory creation or byte writes."""

    candidate = _reject_reparse_in_existing_ancestor_chain(
        output_dir,
        label="artifact destination",
    )
    if candidate.exists() and not candidate.is_dir():
        raise ArtifactGenerationRefused(f"artifact destination is not a directory: {candidate}")
    canonical_destination = _lexical_absolute(ARTIFACTS_DIR)
    material_sources = [_ordinary_material_file(relative) for relative in text_source_relative_paths()]
    protected: list[tuple[str, Path]] = [
        *(("material_source", path) for path in material_sources),
        ("experiment_source_tree", EXPERIMENT_DIR),
        *(("predecessor_artifacts", path) for path in PREDECESSOR_ARTIFACT_DIRS.values()),
        *(("current_authority", path) for path in CURRENT_AUTHORITY_PATHS),
        ("canonical_artifact_root", ARTIFACTS_DIR),
    ]
    for role, raw_protected in protected:
        protected_path = _lexical_absolute(raw_protected)
        if candidate == canonical_destination and role in {
            "experiment_source_tree",
            "canonical_artifact_root",
        }:
            continue
        if _path_overlap(candidate, protected_path):
            raise ArtifactGenerationRefused(
                f"artifact destination overlaps {role}: destination={candidate}, protected={protected_path}"
            )
        if _path_overlap(candidate.resolve(strict=False), protected_path.resolve(strict=False)):
            raise ArtifactGenerationRefused(
                "artifact destination resolves to overlap a protected path: "
                f"destination={candidate}, protected={protected_path}"
            )
    existing_entries = _preflight_existing_destination_entries(candidate)
    return {
        "destination": candidate.as_posix(),
        "canonical_destination": candidate == canonical_destination,
        "existing_ordinary_expected_files": list(existing_entries),
        "protected_path_count": len(protected),
        "preflight_passed": True,
    }


def predecessor_nonmutation_record(
    before: Mapping[str, Mapping[str, object]],
    after: Mapping[str, Mapping[str, object]],
) -> dict[str, object]:
    """Derive, rather than assert, whether every predecessor closure stayed byte/type identical."""

    before_hashes = {name: item["inventory_sha256"] for name, item in sorted(before.items())}
    after_hashes = {name: item["inventory_sha256"] for name, item in sorted(after.items())}
    return {
        "method": "recursive_raw_inventory_before_and_after_payload_construction",
        "before_inventory_sha256": before_hashes,
        "after_inventory_sha256": after_hashes,
        "unchanged": dict(before) == dict(after),
    }


def require_semantic_pass(
    summary: Mapping[str, Any],
    records: list[Mapping[str, Any]] | None = None,
) -> None:
    """Require the exact canonical semantic record, not merely 25 passing-looking rows."""

    gates = summary.get("gates")
    expected_summary_keys = {
        "experiment_id",
        "disposition",
        "evidence_status",
        "all_gates_pass",
        "failed_gates",
        "case_dispositions",
        "canonical_registry",
        "claim_ceiling",
        "metrics",
        "gates",
    }
    expected_gate_keys = {"name", "status", "natural_status", "requirement", "observed"}
    expected_names = registry_gate_names()
    gate_rows_are_mappings = isinstance(gates, list) and all(isinstance(item, Mapping) for item in gates)
    gate_row_keys_exact = gate_rows_are_mappings and all(set(item) == expected_gate_keys for item in gates)
    actual_names = tuple(item.get("name") for item in gates) if gate_rows_are_mappings else ()
    gate_statuses_pass = gate_rows_are_mappings and all(
        item.get("status") == "pass" and item.get("natural_status") == "pass" for item in gates
    )
    expected_cases = expected_case_dispositions()
    actual_cases = summary.get("case_dispositions")
    gate_rows_by_name = {str(item.get("name")): item for item in gates} if gate_rows_are_mappings else {}
    claim_gate = gate_rows_by_name.get("claim_ceiling", {})
    claim_gate_observed_exact = claim_gate.get("observed") == {
        "issues": [],
        "claim_ceiling": MODEL_CONTRACT.claim_ceiling,
    }
    records_exact = True
    if records is not None:
        record_rows_are_mappings = isinstance(records, list) and all(
            isinstance(item, Mapping) for item in records
        )
        contract_records = (
            [item for item in records if item.get("record_type") == "contract"]
            if record_rows_are_mappings
            else []
        )
        gate_records = (
            [item for item in records if item.get("record_type") == "gate"]
            if record_rows_are_mappings
            else []
        )
        certificate_records = (
            [item for item in records if item.get("record_type") == "certificate"]
            if record_rows_are_mappings
            else []
        )
        duplicate_semantic_keys = {
            "claim_ceiling",
            "disposition",
            "evidence_status",
            "status",
            "natural_status",
        }

        def has_duplicate_semantic_key(value: Any) -> bool:
            if isinstance(value, Mapping):
                return bool(set(value) & duplicate_semantic_keys) or any(
                    has_duplicate_semantic_key(item) for item in value.values()
                )
            if isinstance(value, list):
                return any(has_duplicate_semantic_key(item) for item in value)
            return False

        expected_gate_records = (
            [{"record_type": "gate", **dict(item)} for item in gates] if gate_rows_are_mappings else []
        )
        records_exact = (
            record_rows_are_mappings
            and all(item.get("record_type") in {"contract", "certificate", "gate"} for item in records)
            and contract_records == [{"record_type": "contract", "value": MODEL_CONTRACT.jsonable()}]
            and gate_records == expected_gate_records
            and not any(has_duplicate_semantic_key(item) for item in certificate_records)
        )
    if (
        set(summary) != expected_summary_keys
        or summary.get("experiment_id") != MODEL_CONTRACT.experiment_id
        or summary.get("disposition") != MODEL_CONTRACT.disposition
        or summary.get("evidence_status") != MODEL_CONTRACT.evidence_status
        or summary.get("claim_ceiling") != MODEL_CONTRACT.claim_ceiling
        or summary.get("all_gates_pass") is not True
        or summary.get("failed_gates") != []
        or actual_cases != expected_cases
        or not isinstance(actual_cases, Mapping)
        or tuple(actual_cases) != tuple(expected_cases)
        or summary.get("canonical_registry") != canonical_registry_record()
        or not gate_rows_are_mappings
        or not gate_row_keys_exact
        or actual_names != expected_names
        or len(actual_names) != len(set(actual_names))
        or not gate_statuses_pass
        or not claim_gate_observed_exact
        or not records_exact
    ):
        raise ArtifactGenerationRefused(
            "semantic curvature-audit record refused; " f"failed_gates={summary.get('failed_gates')}"
        )


def render_report(summary: Mapping[str, Any]) -> str:
    require_semantic_pass(summary)
    metrics = summary["metrics"]
    lines = [
        "# CGT/response curvature identity audit",
        "",
        f"- Analytic disposition: **{summary['disposition']}**",
        f"- Evidence status: **{summary['evidence_status']}**",
        "- Scope: three internal authored analytic cases; no empirical or physical evidence.",
        (
            "- Exact proofs own acceptance; numerical spectral/finite-difference/Wilson checks "
            "are regressions only."
        ),
        "",
        "## Common-origin result",
        "",
        "- `B_R=sigma^*beta_R`; on a local Berry gauge, `A_Lambda=sigma^*P^*a_B`.",
        "- `kappa` is a smooth real scalar on `Lambda`.",
        "- Exact branch condition: `sigma^*(d beta_R)-kappa sigma^*(P^*omega_FS)=0`.",
        (
            "- The condition is necessary and sufficient only on branch tangents; ambient equality "
            "is not required."
        ),
        (
            "- For constant kappa, `d(B_R-kappa A_Lambda)=0`; only on a contractible chart is "
            "`B_R-kappa A_Lambda=dchi`."
        ),
        "- Noncontractible periods are periods of the pulled-back form; Chern obstructions remain.",
        "- A pointwise 2D quotient is tautological, not a prediction.",
        "",
        "## QP-1 calibration",
        "",
        "- Classification: `SAME_CURVATURE_CALIBRATION_ONLY`.",
        "- `A_x=2*pi*sin(pi*y/2)^2`, `A_y=0`, `Omega_xy=-pi^2*sin(pi*y)`.",
        "- `O_i=+partial_i H` gives `+Omega`; `O_i=-partial_i H` gives `-Omega`.",
        "- Full antisymmetrization is exactly twice the half convention.",
        f"- Chern number: `{metrics['qp1_chern_number']}`; no global smooth connection.",
        "- This is not a finite-speed or live-CWT response result.",
        "",
        "## Benchmark C same-primitives separation",
        "",
        "- Classification: `SAME_PRIMITIVE_MANIFOLD_DIFFERENT_CONNECTIONS_DERIVED_MIXED_HESSIAN`.",
        f"- `Omega_uv(0,0)={metrics['benchmark_c_omega_center']['fraction']}`.",
        f"- `F_uv(0,0)={metrics['benchmark_c_response_center']['fraction']}`.",
        "- Exactly `d beta_R=-m dJ_x wedge dtheta` with `dJ_x=J_xp dp+J_xx dtheta+J_xK dK`.",
        "- `d^2theta` and symmetric `J_xx` cancel; mixed `J_xp` and `J_xK` terms remain.",
        "- Exact quotient gradient: `"
        + ", ".join(item["fraction"] for item in metrics["benchmark_c_quotient_gradient"])
        + "`; the relation is not constant.",
        "- Gain zero and alpha one null the response while leaving projective curvature nonzero.",
        "- The theorem statistic is the fixed-tick cycle sum, not the legacy sample mean.",
        "",
        "## Benchmark D zero-set obstruction",
        "",
        "- Classification: `SAME_MODEL_ZERO_SET_OBSTRUCTION`.",
        "- The exact affine stationary branch `xbar=-A^-1c` supplies `psi_j=sqrt(xbar_j)` with no floor.",
        f"- Projective curvature: `{metrics['benchmark_d_projective_curvature']}`.",
        f"- Response curvature: `{metrics['benchmark_d_response_curvature']['fraction']}`.",
        (
            "- Identical A,c,O provenance plus `Omega=0,F!=0` rules out finite scalar "
            "`F=kappa Omega` and frozen zero-preserving homogeneous linear tensor maps here."
        ),
        "- Arbitrary nonlinear or affine Omega-only maps are not ruled out by this zero-set argument.",
        "- The separate commuting diagonal mixed-density Uhlmann-null statement is not the projective proof.",
        "",
        "## Cases",
        "",
    ]
    for case_id, disposition in summary["case_dispositions"].items():
        lines.append(f"- `{case_id}`: **{disposition}**")
    lines.extend(["", "## Gates", ""])
    for item in summary["gates"]:
        lines.append(f"- **{item['status'].upper()}** `{item['name']}` — {item['requirement']}")
    lines.extend(["", "## Claim ceiling", "", str(summary["claim_ceiling"]), ""])
    return "\n".join(lines)


def expected_artifact_bytes(
    *,
    predecessor_before: Mapping[str, Mapping[str, object]] | None = None,
) -> dict[str, bytes]:
    clean_modules = assert_clean_cli_source_closure()
    predecessors = predecessor_inventories() if predecessor_before is None else dict(predecessor_before)
    summary, records = execute_program()
    require_semantic_pass(summary, records)
    summary_bytes = strict_json_bytes(summary)
    records_bytes = strict_json_bytes(records)
    report_bytes = render_report(summary).encode("utf-8")
    predecessor_after = predecessor_inventories()
    nonmutation = predecessor_nonmutation_record(predecessors, predecessor_after)
    if nonmutation["unchanged"] is not True:
        raise ArtifactGenerationRefused("predecessor artifacts changed during payload construction")
    provenance = {
        "schema_version": 1,
        "experiment_id": MODEL_CONTRACT.experiment_id,
        "artifact_kind": "internal_analytic_curvature_identity_audit",
        "disposition": summary["disposition"],
        "evidence_status": summary["evidence_status"],
        "no_empirical_or_external_data": True,
        "no_physical_or_universal_cwt_claim": True,
        "no_general_alignment_claim": True,
        "numerical_regressions_used_as_analytic_proof": False,
        "source_hash_domain": SOURCE_HASH_DOMAIN,
        "source_hash_domain_definition": SOURCE_HASH_DOMAIN_DEFINITION,
        "source_hashes": source_hashes(),
        "canonical_registry": canonical_registry_record(),
        "clean_cli_local_module_paths": list(clean_modules),
        "clean_cli_local_module_path_set_sha256": sha256_bytes(strict_json_bytes(list(clean_modules))),
        "predecessor_artifact_inventories": predecessors,
        "predecessor_nonmutation_evidence": nonmutation,
        "raw_artifact_payload_sha256": {
            "REPORT.md": sha256_bytes(report_bytes),
            "records.json": sha256_bytes(records_bytes),
            "summary.json": sha256_bytes(summary_bytes),
        },
        "runtime": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "typer": typer.__version__,
        },
        "reproduction_command": (
            "cd cwt-sim && .venv/Scripts/python.exe experiments/curvature_identity_audit/run.py run"
        ),
        "verification_command": (
            "cd cwt-sim && .venv/Scripts/python.exe experiments/curvature_identity_audit/run.py verify"
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


def write_artifacts(output_dir: Path = ARTIFACTS_DIR) -> dict[str, Path]:
    preflight_artifact_destination(output_dir)
    predecessor_before = predecessor_inventories()
    expected = expected_artifact_bytes(predecessor_before=predecessor_before)
    for name, payload in expected.items():
        if b"\r" in payload:
            raise ValueError(f"artifact payload contains CR: {name}")
    if predecessor_inventories() != predecessor_before:
        raise ArtifactGenerationRefused("predecessor artifacts changed before artifact write")
    output_dir.mkdir(parents=True, exist_ok=True)
    for name, payload in expected.items():
        (output_dir / name).write_bytes(payload)
    if predecessor_inventories() != predecessor_before:
        raise ArtifactVerificationError("predecessor artifacts changed during artifact write")
    verify_artifacts(output_dir)
    return {name: output_dir / name for name in sorted(expected)}


def _artifact_entries(output_dir: Path) -> dict[str, Path]:
    absolute = _lexical_absolute(output_dir)
    try:
        absolute.relative_to(_lexical_absolute(SIM_ROOT))
        trust_anchor = SIM_ROOT
    except ValueError:
        trust_anchor = Path(absolute.anchor)
    inventory = recursive_raw_inventory(output_dir, trust_anchor=trust_anchor)
    entries = inventory["entries"]
    if any(value["type"] != "file" for value in entries.values()):
        raise ArtifactVerificationError("artifact directory must contain only ordinary top-level files")
    return {name: output_dir.joinpath(*PurePosixPath(name).parts) for name in entries}


def verify_artifacts(output_dir: Path = ARTIFACTS_DIR) -> dict[str, object]:
    if not output_dir.is_dir():
        raise ArtifactVerificationError(f"artifact directory is missing: {output_dir}")
    entries = _artifact_entries(output_dir)
    if set(entries) != EXPECTED_ARTIFACT_NAMES:
        raise ArtifactVerificationError(
            f"artifact closure mismatch: expected={sorted(EXPECTED_ARTIFACT_NAMES)}, actual={sorted(entries)}"
        )
    expected = expected_artifact_bytes()
    for name, payload in expected.items():
        actual = entries[name].read_bytes()
        if b"\r" in actual:
            raise ArtifactVerificationError(f"artifact is not strict LF: {name}")
        if actual != payload:
            raise ArtifactVerificationError(f"artifact content mismatch: {name}")
        if name.endswith(".json"):
            parsed = json.loads(actual.decode("utf-8"))
            if strict_json_bytes(parsed) != actual:
                raise ArtifactVerificationError(f"artifact is not canonical strict JSON: {name}")
    summary, records = execute_program()
    require_semantic_pass(summary, records)
    return {
        "status": summary["disposition"],
        "evidence_status": summary["evidence_status"],
        "artifact_count": len(expected),
        "source_count": len(text_source_relative_paths()),
        "clean_cli_local_module_count": len(CLEAN_CLI_LOCAL_MODULE_PATHS),
        "predecessor_count": len(PREDECESSOR_ARTIFACT_DIRS),
    }
