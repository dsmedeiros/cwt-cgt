"""Deterministic, LF-only artifacts for the blocked active-loop design template."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from .schema import canonical_schema_bytes
from .template_model import TemplateState, ValidationReport, validate_template

EXPERIMENT_DIR = Path(__file__).resolve().parent
DEFAULT_TEMPLATE_PATH = EXPERIMENT_DIR / "protocol_template.json"
SCHEMA_PATH = EXPERIMENT_DIR / "protocol_template.schema.json"
PROTOCOL_PATH = EXPERIMENT_DIR / "PROTOCOL_TEMPLATE.md"
SUBSTRATE_SCREEN_PATH = EXPERIMENT_DIR / "SUBSTRATE_SCREEN.md"
DEFAULT_ARTIFACT_DIR = EXPERIMENT_DIR / "artifacts" / "template"

SOURCE_PATHS = (
    EXPERIMENT_DIR / "__init__.py",
    EXPERIMENT_DIR / "artifacts.py",
    EXPERIMENT_DIR / "run.py",
    EXPERIMENT_DIR / "schema.py",
    EXPERIMENT_DIR / "template_model.py",
    PROTOCOL_PATH,
    SUBSTRATE_SCREEN_PATH,
    SCHEMA_PATH,
    DEFAULT_TEMPLATE_PATH,
)

ARTIFACT_FILENAMES = (
    "REPORT.md",
    "PROVENANCE.json",
    "TEMPLATE_LOCK.json",
    "CHECKSUMS.json",
)


class ArtifactVerificationError(RuntimeError):
    """Raised when the deterministic template artifact closure differs."""


def _strict_json_loads(raw: bytes) -> Any:
    def reject_constant(value: str) -> None:
        raise ValueError(f"non-finite JSON constant is forbidden: {value}")

    return json.loads(raw.decode("utf-8"), parse_constant=reject_constant)


def load_template(path: Path = DEFAULT_TEMPLATE_PATH) -> dict[str, Any]:
    """Load only the explicit metadata template; never follow payload paths."""

    payload = _strict_json_loads(path.read_bytes())
    if not isinstance(payload, dict):
        raise ValueError("template root must be a JSON object")
    return payload


def verify_checked_schema() -> None:
    """Require the checked JSON schema to equal the canonical schema generator."""

    if SCHEMA_PATH.read_bytes() != canonical_schema_bytes():
        raise ArtifactVerificationError("protocol_template.schema.json differs from schema.py")


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def canonical_source_text_bytes(raw: bytes) -> bytes:
    """Return strict UTF-8/LF source identity; reject BOM, bare CR, and non-UTF8."""

    if raw.startswith(b"\xef\xbb\xbf"):
        raise ValueError("UTF-8 BOM is forbidden in source-text identity")
    text = raw.decode("utf-8")
    normalized = text.replace("\r\n", "\n")
    if "\r" in normalized:
        raise ValueError("bare or mixed carriage returns are forbidden in source text")
    return normalized.encode("utf-8")


def source_text_sha256(path: Path) -> str:
    return sha256_bytes(canonical_source_text_bytes(path.read_bytes()))


def canonical_json_bytes(payload: Any) -> bytes:
    text = json.dumps(payload, allow_nan=False, indent=2, sort_keys=True) + "\n"
    return text.encode("utf-8")


def _write_lf(path: Path, payload: bytes) -> None:
    if b"\r" in payload:
        raise ValueError(f"LF-only artifact contains a carriage return: {path.name}")
    if not payload.endswith(b"\n"):
        raise ValueError(f"Text artifact must end in LF: {path.name}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)


def _relative_source_hashes() -> dict[str, str]:
    return {
        path.relative_to(EXPERIMENT_DIR).as_posix(): source_text_sha256(path) for path in sorted(SOURCE_PATHS)
    }


def _report_text(report: ValidationReport) -> str:
    issue_codes = sorted({issue.code for issue in report.issues})
    lines = [
        "# Active-loop confirmation design-template report",
        "",
        "> **Current state: `BLOCKED_NO_SUBSTRATE`.** This is a deterministic design-template",
        "> freeze, not a study preregistration, an implemented analysis, or evidence.",
        "",
        "No substrate, raw outcome, empirical value, source-specific power calculation, SESOI,",
        "decision margin, or remainder constant is present. The package has no confirmation",
        "command, outcome loader, numerical response reducer, or result directory.",
        "",
        "## What is frozen",
        "",
        "The template fixes the G0-G12 design contract: an immutable active physical source;",
        "at least three independently actuated controls and the repository sign convention; a blinded",
        "physical-time response integral; a complete on/zero by positive/negative quartet;",
        "whole-cluster splitting; tangent/remainder validation; a calibration-only, full-rank",
        "three-dimensional prediction; conjunctive inference; controls; and recovery rules.",
        "",
        "It freezes no source-specific numerical threshold. Those fields remain explicitly null",
        "and cannot be filled without a named qualified substrate and a new reviewed lock.",
        "The metadata-only `SUBSTRATE_SCREEN.md` is non-exhaustive and found no qualifying",
        "public source. Small official structural payloads were inspected during screening,",
        "but no candidate outcome analysis was conducted, no candidate data were retained,",
        "and this package has no raw-data or outcome path.",
        "",
        "## Metadata validation",
        "",
        f"- State: `{report.state.value}`",
        f"- Unresolved metadata gates: `{len(report.issues)}`",
        "- Strongest reachable code state: `METADATA_VERIFIED_PENDING_IMPLEMENTATION`",
        "- Outcome execution available: `false`",
        "- Study decision available: `false`",
        "",
        "Unresolved issue-code classes:",
        "",
    ]
    lines.extend(f"- `{code}`" for code in issue_codes)
    lines.extend(
        [
            "",
            "## Claim ceiling",
            "",
            "This artifact contributes no empirical support. Even a later valid study result would",
            "be limited to its named substrate, control region, branch, coupling, readout, time",
            "regime, and loop family. It could not establish universal CWT/CGT, topology or",
            "topological protection, passive ridges, strict locality, population generalization,",
            "or transported charge without calibrated current-time units.",
            "",
            "See `../../PROTOCOL_TEMPLATE.md` for the complete design and exact equations.",
            "",
        ]
    )
    return "\n".join(lines)


def _provenance_payload(report: ValidationReport) -> dict[str, Any]:
    return {
        "schema_version": 2,
        "template_id": "active-loop-confirmation-v2",
        "artifact_kind": "metadata_only_design_template_freeze",
        "template_state": report.state.value,
        "maximum_reachable_code_state": (TemplateState.METADATA_VERIFIED_PENDING_IMPLEMENTATION.value),
        "design_freeze_not_study_preregistration": True,
        "evidence_contribution": "none",
        "substrate_selected": False,
        "outcome_execution_available": False,
        "raw_data_access_available": False,
        "analysis_implementation_available": False,
        "confirmation_command_available": False,
        "result_directory_available": False,
        "candidate_screening_disclosure": (
            "small official structural payloads were inspected; no candidate outcome "
            "analysis was conducted; no candidate data were retained; this package has "
            "no raw-data or outcome path"
        ),
        "source_specific_values_frozen": False,
        "source_specific_nulls": [
            "source identity and qualification",
            "coordinate realization and physical clock",
            "response signal, units, baseline, and reducer",
            "cluster membership and achieved-path realization",
            "power, SESOI, equivalence/tensor/loss margins",
            "remainder constants and condition-number threshold",
        ],
        "artifact_hash_domain": "sha256_raw_bytes",
        "source_hash_domain": ("sha256_utf8_lf_v1: reject BOM/non-UTF8/bare CR; convert CRLF to LF only"),
        "text_encoding": "strict UTF-8 with LF line endings",
        "source_hashes": _relative_source_hashes(),
        "validation_issue_count": len(report.issues),
        "validation_issue_codes": sorted({issue.code for issue in report.issues}),
        "deterministic_reproduction_command": (
            "cd cwt-sim && .venv/Scripts/python.exe "
            "experiments/active_loop_confirmation/run.py freeze-template"
        ),
        "verification_command": (
            "cd cwt-sim && .venv/Scripts/python.exe "
            "experiments/active_loop_confirmation/run.py verify-template"
        ),
    }


def _expected_artifact_bytes(report: ValidationReport) -> dict[str, bytes]:
    """Build the exact acyclic artifact closure without writing it."""

    report_bytes = _report_text(report).encode("utf-8")
    provenance_bytes = canonical_json_bytes(_provenance_payload(report))
    lock = {
        "schema_version": 2,
        "lock_kind": "design_template_only_no_study_or_outcome_lock",
        "template_id": "active-loop-confirmation-v2",
        "template_state": report.state.value,
        "artifact_hash_domain": "sha256_raw_bytes",
        "source_hash_domain": ("sha256_utf8_lf_v1: reject BOM/non-UTF8/bare CR; convert CRLF to LF only"),
        "inputs": _relative_source_hashes(),
        "generated_claim_artifacts": {
            "PROVENANCE.json": sha256_bytes(provenance_bytes),
            "REPORT.md": sha256_bytes(report_bytes),
        },
        "substrate_digest": None,
        "outcome_digest": None,
        "prediction_digest": None,
        "study_authorization_digest": None,
        "not_a_study_preregistration": True,
        "not_evidence": True,
    }
    lock_bytes = canonical_json_bytes(lock)
    checksums_bytes = canonical_json_bytes(
        {
            "schema_version": 2,
            "artifact_hash_domain": "sha256_raw_bytes",
            "files": {
                "PROVENANCE.json": sha256_bytes(provenance_bytes),
                "REPORT.md": sha256_bytes(report_bytes),
                "TEMPLATE_LOCK.json": sha256_bytes(lock_bytes),
            },
            "self_hash_excluded_to_keep_the_closure_acyclic": True,
        }
    )
    return {
        "REPORT.md": report_bytes,
        "PROVENANCE.json": provenance_bytes,
        "TEMPLATE_LOCK.json": lock_bytes,
        "CHECKSUMS.json": checksums_bytes,
    }


def write_template_artifacts(
    template_path: Path = DEFAULT_TEMPLATE_PATH,
    output_dir: Path = DEFAULT_ARTIFACT_DIR,
) -> dict[str, Path]:
    """Freeze the blocked design template without evaluating a substrate or outcome."""

    verify_checked_schema()
    payload = load_template(template_path)
    report = validate_template(payload)
    if report.state is not TemplateState.BLOCKED_NO_SUBSTRATE:
        raise ValueError("only the checked-in BLOCKED_NO_SUBSTRATE design may be frozen")

    paths = {
        "report": output_dir / "REPORT.md",
        "provenance": output_dir / "PROVENANCE.json",
        "lock": output_dir / "TEMPLATE_LOCK.json",
        "checksums": output_dir / "CHECKSUMS.json",
    }
    expected = _expected_artifact_bytes(report)
    for path in paths.values():
        _write_lf(path, expected[path.name])
    return paths


def verify_template_artifacts(
    template_path: Path = DEFAULT_TEMPLATE_PATH,
    output_dir: Path = DEFAULT_ARTIFACT_DIR,
) -> dict[str, Any]:
    """Verify the acyclic LF artifact closure and current blocked state."""

    verify_checked_schema()
    missing = [name for name in ARTIFACT_FILENAMES if not (output_dir / name).is_file()]
    if missing:
        raise ArtifactVerificationError(f"missing template artifacts: {missing}")

    payload = load_template(template_path)
    report = validate_template(payload)
    if report.state is not TemplateState.BLOCKED_NO_SUBSTRATE:
        raise ArtifactVerificationError("checked-in template is no longer BLOCKED_NO_SUBSTRATE")

    entries = list(output_dir.rglob("*"))
    actual_files: set[str] = set()
    unexpected: list[str] = []
    for path in entries:
        relative = path.relative_to(output_dir).as_posix()
        if path.is_symlink() or path.is_dir() or relative not in ARTIFACT_FILENAMES:
            unexpected.append(relative)
        elif path.is_file():
            actual_files.add(relative)
        else:
            unexpected.append(relative)
    if unexpected or actual_files != set(ARTIFACT_FILENAMES):
        raise ArtifactVerificationError(
            "unexpected template artifact inventory: "
            f"files={sorted(actual_files)} unexpected={sorted(unexpected)}"
        )

    expected = _expected_artifact_bytes(report)
    for name in ARTIFACT_FILENAMES:
        raw = (output_dir / name).read_bytes()
        if b"\r" in raw or not raw.endswith(b"\n"):
            raise ArtifactVerificationError(f"{name} is not strict LF text")
        if raw != expected[name]:
            raise ArtifactVerificationError(f"artifact bytes differ from generator: {name}")

    provenance = _strict_json_loads((output_dir / "PROVENANCE.json").read_bytes())
    lock = _strict_json_loads((output_dir / "TEMPLATE_LOCK.json").read_bytes())
    checksums = _strict_json_loads((output_dir / "CHECKSUMS.json").read_bytes())
    expected_sources = _relative_source_hashes()
    if provenance.get("source_hashes") != expected_sources or lock.get("inputs") != expected_sources:
        raise ArtifactVerificationError("source hash closure differs")
    for name, expected in checksums.get("files", {}).items():
        if sha256_file(output_dir / name) != expected:
            raise ArtifactVerificationError(f"artifact checksum differs: {name}")
    if lock.get("generated_claim_artifacts") != {
        "PROVENANCE.json": sha256_file(output_dir / "PROVENANCE.json"),
        "REPORT.md": sha256_file(output_dir / "REPORT.md"),
    }:
        raise ArtifactVerificationError("lock claim-artifact hashes differ")
    if (EXPERIMENT_DIR / "artifacts" / "results").exists():
        raise ArtifactVerificationError("a result directory exists in a metadata-only package")
    return {
        "status": "TEMPLATE_VERIFIED_BLOCKED_NO_SUBSTRATE",
        "artifact_count": len(ARTIFACT_FILENAMES),
        "source_count": len(expected_sources),
        "template_state": report.state.value,
        "outcome_execution_available": False,
    }


def validation_json(report: ValidationReport) -> str:
    """Return deterministic one-line JSON for CLI status output."""

    return json.dumps(report.as_dict(), allow_nan=False, separators=(",", ":"), sort_keys=True)


def source_hashes() -> Mapping[str, str]:
    """Expose a copy for focused portability tests."""

    return dict(_relative_source_hashes())
