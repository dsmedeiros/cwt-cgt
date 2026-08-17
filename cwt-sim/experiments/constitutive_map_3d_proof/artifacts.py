"""Deterministic isolated artifacts and provenance for the 3D proof program."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import stat
import subprocess
import sys
from functools import lru_cache
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, Sequence

import numpy as np
import typer

from .contract import MODEL_CONTRACT, canonical_registry_record, expected_case_dispositions
from .theorem import execute_program

_CANONICAL_EXECUTE_PROGRAM = execute_program

EXPERIMENT_DIR = Path(__file__).resolve().parent
SIM_ROOT = EXPERIMENT_DIR.parents[1]
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

ADDITIONAL_MATERIAL_TEXT_PATHS = (
    "experiments/constitutive_map_3d_proof/MODEL_CONTRACT.md",
    "experiments/curvature_identity_audit/MODEL_CONTRACT.md",
    "experiments/curvature_identity_audit/common_origin.py",
    "experiments/curvature_identity_audit/benchmark_c.py",
    "experiments/curvature_identity_audit/qp1.py",
    "experiments/independent_response_theorem/PROTOCOL_LOCK.md",
    "experiments/response_theorem_proof_program/THEOREM.md",
    "experiments/response_theorem_proof_program/forms.py",
    "tests/experiments/test_constitutive_map_3d_proof.py",
)
PREDECESSOR_ARTIFACT_DIRS = {
    "curvature_identity_audit": SIM_ROOT / "experiments" / "curvature_identity_audit" / "artifacts",
    "independent_response_theorem": SIM_ROOT / "experiments" / "independent_response_theorem" / "artifacts",
    "response_theorem_proof_program": SIM_ROOT
    / "experiments"
    / "response_theorem_proof_program"
    / "artifacts",
}

REVIEWED_CLEAN_CLI_LOCAL_MODULE_PATHS = (
    "cwt/__init__.py",
    "cwt/cgt/__init__.py",
    "cwt/cgt/_geom_compat.py",
    "cwt/cgt/benchmarks.py",
    "cwt/cgt/continuation.py",
    "cwt/cgt/loop_protocols.py",
    "cwt/cgt/models.py",
    "cwt/cgt/runner.py",
    "cwt/geometry/berry.py",
    "cwt/geometry/branch_distance.py",
    "cwt/geometry/coherence.py",
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
    "experiments/constitutive_map_3d_proof/run.py",
    "experiments/constitutive_map_3d_proof/theorem.py",
)
REVIEWED_CLEAN_CLI_PATH_SET_SHA256 = "28fd6e882d722be0b44068a6766ec686fcc10aca6110ea84bb83323677e133a9"
REVIEWED_MATERIAL_SOURCE_PATHS = tuple(
    sorted(set(REVIEWED_CLEAN_CLI_LOCAL_MODULE_PATHS) | set(ADDITIONAL_MATERIAL_TEXT_PATHS))
)
REVIEWED_MATERIAL_SOURCE_PATH_SET_SHA256 = "2ef61bdd1074b04fc88e5df350bdc5f7712520fae22bbaa0a2e05da0b2e69dec"
REVIEWED_PREDECESSOR_ROLE_PATHS = (
    ("curvature_identity_audit", "experiments/curvature_identity_audit/artifacts"),
    ("independent_response_theorem", "experiments/independent_response_theorem/artifacts"),
    ("response_theorem_proof_program", "experiments/response_theorem_proof_program/artifacts"),
)
REVIEWED_PREDECESSOR_ROLE_PATHS_SHA256 = "39d440db38af4cd4d30bf5a233404eb6c5e76eedabaf7056ce1f123893b6c4d8"


class ArtifactVerificationError(RuntimeError):
    """Raised when deterministic content or its provenance closure differs."""


class ArtifactGenerationRefused(RuntimeError):
    """Raised before writing when the analytic program is not exactly passing."""


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def strict_json_bytes(payload: Any) -> bytes:
    return (
        json.dumps(
            payload,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def canonical_source_text_bytes(raw: bytes) -> bytes:
    """Apply only the declared portable source-text transformation."""

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


def _absolute(path: Path) -> Path:
    return Path(os.path.abspath(os.fspath(path)))


def _assert_no_reparse_from_volume_root(
    path: Path,
    *,
    label: str,
    require_leaf: bool,
) -> Path:
    """Check every existing component from the filesystem root to the leaf."""

    candidate = _absolute(path)
    current = Path(candidate.anchor)
    if not os.path.lexists(current):
        raise ArtifactVerificationError(f"{label} filesystem root is missing: {current}")
    if _is_link_or_reparse(current):
        raise ArtifactVerificationError(f"{label} filesystem root is a link/reparse point")
    for part in candidate.parts[1:]:
        current /= part
        if not os.path.lexists(current):
            if require_leaf:
                raise ArtifactVerificationError(f"{label} is missing: {current}")
            break
        if _is_link_or_reparse(current):
            raise ArtifactVerificationError(f"{label} contains a link/reparse component: {current}")
    return candidate


def _checked_path(
    path: Path,
    trust_anchor: Path,
    *,
    expected_kind: str,
    label: str,
) -> Path:
    anchor = _assert_no_reparse_from_volume_root(
        trust_anchor,
        label=f"{label} trust anchor",
        require_leaf=True,
    )
    candidate = _assert_no_reparse_from_volume_root(
        path,
        label=label,
        require_leaf=True,
    )
    try:
        candidate.relative_to(anchor)
    except ValueError as exc:
        raise ArtifactVerificationError(f"{label} escapes trust anchor: {candidate}") from exc
    if expected_kind == "file" and not candidate.is_file():
        raise ArtifactVerificationError(f"{label} is not an ordinary file: {candidate}")
    if expected_kind == "directory" and not candidate.is_dir():
        raise ArtifactVerificationError(f"{label} is not an ordinary directory: {candidate}")
    try:
        candidate.resolve(strict=True).relative_to(anchor.resolve(strict=True))
    except (OSError, ValueError) as exc:
        raise ArtifactVerificationError(f"{label} resolves outside its trust anchor") from exc
    return candidate


def _canonical_relative_path(relative: str) -> PurePosixPath:
    parsed = PurePosixPath(relative)
    if not relative or parsed.is_absolute() or ".." in parsed.parts or parsed.as_posix() != relative:
        raise ArtifactVerificationError(f"noncanonical relative path: {relative}")
    return parsed


def _material_file(relative: str) -> Path:
    parsed = _canonical_relative_path(relative)
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
import experiments.constitutive_map_3d_proof.run  # noqa: E402,F401

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


def material_source_relative_paths(
    clean_modules: Sequence[str] | None = None,
) -> tuple[str, ...]:
    modules = clean_cli_local_module_paths() if clean_modules is None else tuple(clean_modules)
    package_sources = tuple(
        path.relative_to(SIM_ROOT).as_posix() for path in sorted(EXPERIMENT_DIR.glob("*.py"))
    )
    actual = tuple(sorted(set(modules) | set(package_sources) | set(ADDITIONAL_MATERIAL_TEXT_PATHS)))
    if actual != REVIEWED_MATERIAL_SOURCE_PATHS:
        raise ArtifactVerificationError("material-source path set differs from reviewed closure")
    if sha256_bytes(strict_json_bytes(list(actual))) != REVIEWED_MATERIAL_SOURCE_PATH_SET_SHA256:
        raise ArtifactVerificationError("material-source path-set fingerprint mismatch")
    return actual


def source_hashes(paths: Sequence[str]) -> dict[str, dict[str, str]]:
    return {
        relative: {
            "hash_domain": SOURCE_HASH_DOMAIN,
            "sha256": sha256_bytes(canonical_source_text_bytes(_material_file(relative).read_bytes())),
        }
        for relative in paths
    }


def recursive_raw_inventory(
    root: Path,
    *,
    trust_anchor: Path,
) -> dict[str, object]:
    checked_root = _checked_path(
        root,
        trust_anchor,
        expected_kind="directory",
        label="recursive inventory root",
    )
    entries: dict[str, dict[str, str]] = {}

    def visit(directory: Path, prefix: PurePosixPath) -> None:
        with os.scandir(directory) as scanned:
            children = sorted(scanned, key=lambda item: item.name)
        for child in children:
            path = Path(child.path)
            relative = (prefix / child.name).as_posix()
            if _is_link_or_reparse(path):
                raise ArtifactVerificationError(f"closure contains link/reparse entry: {relative}")
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
                raise ArtifactVerificationError(f"closure has unsupported entry type: {relative}")

    visit(checked_root, PurePosixPath())
    if not entries or not any(item["type"] == "file" for item in entries.values()):
        raise ArtifactVerificationError(f"closure contains no files: {checked_root}")
    return {
        "closure": "recursive_path_and_type_bound_no_symlink_or_reparse",
        "entry_count": len(entries),
        "entries": entries,
        "inventory_sha256": sha256_bytes(strict_json_bytes(entries)),
    }


def predecessor_inventories() -> dict[str, dict[str, object]]:
    actual_roles = tuple(
        (name, path.relative_to(SIM_ROOT).as_posix())
        for name, path in sorted(PREDECESSOR_ARTIFACT_DIRS.items())
    )
    if actual_roles != REVIEWED_PREDECESSOR_ROLE_PATHS:
        raise ArtifactVerificationError("predecessor role/path set differs from reviewed closure")
    if sha256_bytes(strict_json_bytes(list(actual_roles))) != REVIEWED_PREDECESSOR_ROLE_PATHS_SHA256:
        raise ArtifactVerificationError("predecessor role/path-set fingerprint mismatch")
    return {
        name: recursive_raw_inventory(path, trust_anchor=SIM_ROOT)
        for name, path in sorted(PREDECESSOR_ARTIFACT_DIRS.items())
    }


def _overlaps(left: Path, right: Path) -> bool:
    return left == right or left in right.parents or right in left.parents


def preflight_artifact_destination(output_dir: Path) -> dict[str, object]:
    """Reject unsafe output roots before any byte is written."""

    try:
        candidate = _assert_no_reparse_from_volume_root(
            output_dir,
            label="artifact destination",
            require_leaf=False,
        )
    except ArtifactVerificationError as exc:
        raise ArtifactGenerationRefused(str(exc)) from exc
    if candidate.exists() and not candidate.is_dir():
        raise ArtifactGenerationRefused(f"artifact destination is not a directory: {candidate}")
    canonical = _absolute(ARTIFACTS_DIR)
    if candidate != canonical and _overlaps(candidate, _absolute(EXPERIMENT_DIR)):
        raise ArtifactGenerationRefused("noncanonical output overlaps experiment source tree")
    protected_paths = [
        *((f"predecessor {name}", path) for name, path in PREDECESSOR_ARTIFACT_DIRS.items()),
        *(
            (f"material source {relative}", _material_file(relative))
            for relative in REVIEWED_MATERIAL_SOURCE_PATHS
        ),
    ]
    candidate_resolved = candidate.resolve(strict=False)
    for label, protected in protected_paths:
        protected_absolute = _absolute(protected)
        if _overlaps(candidate, protected_absolute) or _overlaps(
            candidate_resolved,
            protected_absolute.resolve(strict=False),
        ):
            raise ArtifactGenerationRefused(f"artifact destination overlaps {label}")
    existing: list[str] = []
    if candidate.exists():
        with os.scandir(candidate) as scanned:
            children = sorted(scanned, key=lambda item: item.name)
        for child in children:
            path = Path(child.path)
            if _is_link_or_reparse(path) or not child.is_file(follow_symlinks=False):
                raise ArtifactGenerationRefused(f"artifact destination contains nonordinary entry: {path}")
            if child.name not in EXPECTED_ARTIFACT_NAMES:
                raise ArtifactGenerationRefused(f"artifact destination contains unexpected file: {path}")
            if path.lstat().st_nlink != 1:
                raise ArtifactGenerationRefused(f"artifact destination contains multiply-linked file: {path}")
            existing.append(child.name)
    return {
        "destination": candidate.as_posix(),
        "canonical_destination": candidate == canonical,
        "existing_expected_files": existing,
        "preflight_passed": True,
    }


@lru_cache(maxsize=1)
def _canonical_semantic_bytes() -> tuple[bytes, bytes]:
    summary, records = _CANONICAL_EXECUTE_PROGRAM()
    return strict_json_bytes(summary), strict_json_bytes(records)


def require_semantic_pass(
    summary: Mapping[str, Any],
    records: Sequence[Mapping[str, Any]] | None = None,
) -> None:
    """Require byte-for-structure equivalence to the canonical analytic result."""

    expected_summary_bytes, expected_records_bytes = _canonical_semantic_bytes()
    expected_records = json.loads(expected_records_bytes)
    candidate_records = expected_records if records is None else list(records)
    gates = [
        item for item in candidate_records if isinstance(item, Mapping) and item.get("record_type") == "gate"
    ]
    gate_names = tuple(item.get("name") for item in gates)
    gates_exact = (
        gate_names == tuple(item["name"] for item in expected_records if item.get("record_type") == "gate")
        and len(gate_names) == len(set(gate_names))
        and all(item.get("status") == "pass" and item.get("natural_status") == "pass" for item in gates)
    )
    if (
        strict_json_bytes(dict(summary)) != expected_summary_bytes
        or strict_json_bytes(candidate_records) != expected_records_bytes
        or not gates_exact
        or summary.get("disposition") != MODEL_CONTRACT.disposition
        or summary.get("formal_disposition") != MODEL_CONTRACT.disposition
        or summary.get("evidence_status") != MODEL_CONTRACT.evidence_status
        or summary.get("relation_scope") != MODEL_CONTRACT.relation_scope
        or summary.get("claim_ceiling") != MODEL_CONTRACT.claim_ceiling
        or summary.get("case_dispositions") != expected_case_dispositions()
        or summary.get("registry") != canonical_registry_record()
        or summary.get("failed_gates") != []
        or summary.get("indeterminate_gates") != []
        or summary.get("publication_blockers") != []
        or summary.get("metrics", {})
        .get("bc3_scalar_non_authoritative_diagnostic", {})
        .get("assessment", {})
        .get("diagnostic_status")
        != "PASS_NONAUTHORITATIVE_REGRESSION"
    ):
        raise ArtifactGenerationRefused(
            "semantic constitutive-map record refused; " f"failed_gates={summary.get('failed_gates')}"
        )


def render_report(
    summary: Mapping[str, Any],
    records: Sequence[Mapping[str, Any]] | None = None,
) -> str:
    require_semantic_pass(summary, records)
    gate_records = [item for item in (records or []) if item.get("record_type") == "gate"]
    metrics = summary["metrics"]
    scalar_rows = metrics["bc3_scalar_non_authoritative_diagnostic"]["rows"]
    maximum_scalar_density_distance = max(
        row["density_distance_to_authoritative_interval"] for row in scalar_rows
    )
    lines = [
        "# Three-dimensional constitutive-map proof program",
        "",
        f"- Analytic disposition: **{summary['disposition']}**",
        f"- Evidence status: **{summary['evidence_status']}**",
        f"- Relation scope: **{summary['relation_scope']}**",
        "- Scope: two internal authored analytic model checks; no empirical or physical evidence.",
        "- Exact derivations own acceptance; numerical checks are regressions only.",
        "",
        "## BC3 kinetic-control separation",
        "",
        f"- Classification: `{summary['case_dispositions']['BC3']}`.",
        "- Controls are `(u,v,alpha)`; gain is fixed and is not a third control.",
        "- `beta=-((1-alpha)/alpha) eta` and " "`F=alpha^-2 d alpha wedge eta-((1-alpha)/alpha)d eta`.",
        "- Component order is `(F_v_alpha,F_alpha_u,F_uv)`.",
        "- Geometry is alpha-independent rank one, while the response changes across the alpha fiber.",
        (
            "- The heldout oblique area vector `(1,2,2)`, midpoint lines, and center interval "
            "are locked before the response oracle runs."
        ),
        f"- Prediction lock: `{metrics['bc3_prediction_lock_sha256']}`.",
        (
            "- Exact-lattice no-libm binary64 intervals conjunctively certify all four formal "
            "remainder rows; the last two are locked synthetic holdouts."
        ),
        "- Missing authenticated enclosures are INDETERMINATE and any finite conjunct violation is FAIL.",
        (
            "- The scalar float recurrence is `NON_AUTHORITATIVE_DIAGNOSTIC`: it is never "
            "unioned into or used to widen the exact-lattice interval and is not a formal PASS input."
        ),
        (
            "- Its development-selected drift ceiling is `1/1000000` density units; the current "
            f"maximum interval distance is `{maximum_scalar_density_distance}` "
            "and the diagnostic status is `PASS_NONAUTHORITATIVE_REGRESSION`."
        ),
        (
            "- Nonfinite or over-ceiling scalar drift leaves the formal theorem gates unchanged "
            "but blocks publication as `BLOCKED_DIAGNOSTIC_DRIFT`."
        ),
        "",
        "## QP3 ambient calibration",
        "",
        f"- Classification: `{summary['case_dispositions']['QP3']}`.",
        "- `P+=(I+n.sigma)/2`, `H=3/5 I+2/5 P+`, gap `2/5` on a contractible tube away from zero.",
        "- `Omega_ij=epsilon_ijk lambda_k/(2|lambda|^3)`.",
        (
            "- Independent spectral Kubo `O_i=+partial_i H` gives `+Omega`; "
            "conventional `-partial_i H` gives `-Omega`."
        ),
        "- Full antisymmetrization is exactly twice the half convention.",
        "- Centers `e1,e2,e3` span rank three; heldout `(1,2,2)/3` has density exactly `1/2`.",
        (
            "- Exact Pauli/projector and north/south patch algebra own acceptance; numerical "
            "spectral rows are regressions only."
        ),
        "- This is a calibration-only same-operator identity, not finite-speed CWT response.",
        "",
        "## Claim ceiling",
        "",
        str(summary["claim_ceiling"]),
        "",
        "No universal, full-CWT, physical, empirical, or general alignment claim is made.",
        "",
        "## Cases",
        "",
    ]
    for case_id, disposition in summary["case_dispositions"].items():
        lines.append(f"- `{case_id}`: **{disposition}**")
    lines.extend(["", "## Gates", ""])
    for item in gate_records:
        lines.append(f"- **{str(item['status']).upper()}** `{item['name']}` — {item['requirement']}")
    lines.append("")
    return "\n".join(lines)


def expected_artifact_bytes(
    *,
    predecessor_before: Mapping[str, Mapping[str, object]] | None = None,
) -> dict[str, bytes]:
    clean_modules = clean_cli_local_module_paths()
    source_paths = material_source_relative_paths(clean_modules)
    predecessors = predecessor_inventories() if predecessor_before is None else dict(predecessor_before)
    summary, records = execute_program()
    require_semantic_pass(summary, records)
    summary_bytes = strict_json_bytes(summary)
    records_bytes = strict_json_bytes(records)
    report_bytes = render_report(summary, records).encode("utf-8")
    predecessor_after = predecessor_inventories()
    predecessor_unchanged = predecessors == predecessor_after
    if not predecessor_unchanged:
        raise ArtifactGenerationRefused("predecessor artifacts changed during payload construction")
    provenance = {
        "schema_version": 1,
        "experiment_id": MODEL_CONTRACT.experiment_id,
        "artifact_kind": "internal_analytic_constitutive_map_3d_proof",
        "disposition": summary["disposition"],
        "evidence_status": summary["evidence_status"],
        "relation_scope": summary["relation_scope"],
        "claim_ceiling": summary["claim_ceiling"],
        "no_empirical_or_external_data": True,
        "no_physical_or_universal_cwt_claim": True,
        "no_general_alignment_claim": True,
        "numerical_regressions_used_as_analytic_proof": False,
        "formal_disposition": summary["formal_disposition"],
        "publication_blockers": summary["publication_blockers"],
        "scalar_diagnostic_policy": summary["metrics"]["bc3_scalar_non_authoritative_diagnostic"]["policy"],
        "scalar_diagnostic_status": summary["metrics"]["bc3_scalar_non_authoritative_diagnostic"][
            "assessment"
        ]["diagnostic_status"],
        "source_hash_domain": SOURCE_HASH_DOMAIN,
        "source_hash_domain_definition": SOURCE_HASH_DOMAIN_DEFINITION,
        "source_hashes": source_hashes(source_paths),
        "canonical_registry": canonical_registry_record(),
        "clean_cli_local_module_paths": list(clean_modules),
        "clean_cli_local_module_path_set_sha256": sha256_bytes(strict_json_bytes(list(clean_modules))),
        "reviewed_clean_cli_local_module_path_set_sha256": REVIEWED_CLEAN_CLI_PATH_SET_SHA256,
        "reviewed_material_source_path_set_sha256": REVIEWED_MATERIAL_SOURCE_PATH_SET_SHA256,
        "reviewed_predecessor_role_paths": [list(item) for item in REVIEWED_PREDECESSOR_ROLE_PATHS],
        "reviewed_predecessor_role_paths_sha256": REVIEWED_PREDECESSOR_ROLE_PATHS_SHA256,
        "predecessor_artifact_inventories": predecessors,
        "predecessor_nonmutation_evidence": {
            "method": "recursive_raw_inventory_before_and_after_payload_construction",
            "before_inventory_sha256": {
                name: item["inventory_sha256"] for name, item in sorted(predecessors.items())
            },
            "after_inventory_sha256": {
                name: item["inventory_sha256"] for name, item in sorted(predecessor_after.items())
            },
            "unchanged": predecessor_unchanged,
        },
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
            "cd cwt-sim && .venv/Scripts/python.exe " "experiments/constitutive_map_3d_proof/run.py run"
        ),
        "verification_command": (
            "cd cwt-sim && .venv/Scripts/python.exe " "experiments/constitutive_map_3d_proof/run.py verify"
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
    if any(b"\r" in payload for payload in expected.values()):
        raise ArtifactGenerationRefused("artifact payload is not strict LF")
    if predecessor_inventories() != predecessor_before:
        raise ArtifactGenerationRefused("predecessor artifacts changed before write")
    output_dir.mkdir(parents=True, exist_ok=True)
    for name, payload in expected.items():
        (output_dir / name).write_bytes(payload)
    if predecessor_inventories() != predecessor_before:
        raise ArtifactVerificationError("predecessor artifacts changed during write")
    verify_artifacts(output_dir)
    return {name: output_dir / name for name in sorted(expected)}


def _artifact_entries(output_dir: Path) -> dict[str, Path]:
    absolute = _absolute(output_dir)
    trust_anchor = SIM_ROOT if SIM_ROOT in absolute.parents else absolute.parent
    inventory = recursive_raw_inventory(output_dir, trust_anchor=trust_anchor)
    entries = inventory["entries"]
    if any(item["type"] != "file" for item in entries.values()):
        raise ArtifactVerificationError("artifact directory must contain only ordinary top-level files")
    return {name: output_dir.joinpath(*PurePosixPath(name).parts) for name in entries}


def verify_artifacts(output_dir: Path = ARTIFACTS_DIR) -> dict[str, object]:
    if not output_dir.is_dir():
        raise ArtifactVerificationError(f"artifact directory is missing: {output_dir}")
    entries = _artifact_entries(output_dir)
    if set(entries) != EXPECTED_ARTIFACT_NAMES:
        raise ArtifactVerificationError(
            "artifact closure mismatch: "
            f"expected={sorted(EXPECTED_ARTIFACT_NAMES)}, actual={sorted(entries)}"
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
        "relation_scope": summary["relation_scope"],
        "artifact_count": len(expected),
        "source_count": len(material_source_relative_paths(clean_cli_local_module_paths())),
        "clean_cli_local_module_count": len(clean_cli_local_module_paths()),
        "predecessor_count": len(PREDECESSOR_ARTIFACT_DIRS),
    }
