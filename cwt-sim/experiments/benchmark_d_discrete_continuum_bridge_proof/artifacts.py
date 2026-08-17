"""Deterministic isolated artifacts for the Benchmark-D rational bridge proof."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
import sys
from pathlib import Path
from typing import Any, Mapping

import numpy as np
import typer

from .contract import CASE_GATE_MAP, EXPECTED_CASE_DISPOSITIONS, MODEL_CONTRACT
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

# Replaced after a clean standalone-CLI import audit; its exact equality is a gate.
CLEAN_CLI_LOCAL_MODULE_PATHS = (
    "cwt/__init__.py",
    "cwt/cgt/__init__.py",
    "cwt/cgt/_geom_compat.py",
    "cwt/cgt/benchmarks.py",
    "cwt/cgt/continuation.py",
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
    "experiments/benchmark_d_discrete_continuum_bridge_proof/__init__.py",
    "experiments/benchmark_d_discrete_continuum_bridge_proof/adapter.py",
    "experiments/benchmark_d_discrete_continuum_bridge_proof/artifacts.py",
    "experiments/benchmark_d_discrete_continuum_bridge_proof/contract.py",
    "experiments/benchmark_d_discrete_continuum_bridge_proof/exact_math.py",
    "experiments/benchmark_d_discrete_continuum_bridge_proof/run.py",
    "experiments/benchmark_d_discrete_continuum_bridge_proof/theorem.py",
)
ADDITIONAL_MATERIAL_TEXT_PATHS = (
    "experiments/benchmark_d_discrete_continuum_bridge_proof/MODEL_CONTRACT.md",
    "experiments/response_theorem_proof_program/THEOREM.md",
    "tests/experiments/test_benchmark_d_discrete_continuum_bridge_proof.py",
)
TEXT_SOURCE_RELATIVE_PATHS = tuple(
    sorted(set(CLEAN_CLI_LOCAL_MODULE_PATHS) | set(ADDITIONAL_MATERIAL_TEXT_PATHS))
)


class ArtifactVerificationError(RuntimeError):
    """Raised when deterministic artifact/source closure differs."""


class ArtifactGenerationRefused(RuntimeError):
    """Raised before writing when a semantic theorem gate is not passing."""


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def canonical_source_text_bytes(raw: bytes) -> bytes:
    """Return portable LF source identity under a strict narrow transform."""

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


def strict_json_bytes(payload: Any) -> bytes:
    return (json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n").encode(
        "utf-8"
    )


def source_hashes() -> dict[str, dict[str, str]]:
    """Hash every material text dependency in the portable canonical domain."""

    return {
        relative: {
            "hash_domain": SOURCE_HASH_DOMAIN,
            "sha256": sha256_bytes(canonical_source_text_bytes((SIM_ROOT / relative).read_bytes())),
        }
        for relative in TEXT_SOURCE_RELATIVE_PATHS
    }


_CLEAN_IMPORT_SCRIPT = r"""
import json
import pathlib
import sys

root = pathlib.Path.cwd().resolve()
import experiments.benchmark_d_discrete_continuum_bridge_proof.run  # noqa: E402,F401

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
        absent = sorted(set(CLEAN_CLI_LOCAL_MODULE_PATHS) - set(actual))
        undeclared = sorted(set(actual) - set(CLEAN_CLI_LOCAL_MODULE_PATHS))
        raise ArtifactVerificationError(
            f"clean CLI source closure mismatch: absent={absent}, undeclared={undeclared}"
        )
    return actual


def require_semantic_pass(summary: Mapping[str, Any]) -> None:
    gates = summary.get("gates")
    if (
        summary.get("disposition") != "PASS_INTERNAL_ANALYTIC"
        or summary.get("evidence_status") != "NO_EMPIRICAL_EVIDENCE"
        or summary.get("all_gates_pass") is not True
        or summary.get("failed_gates") != []
        or summary.get("case_dispositions") != EXPECTED_CASE_DISPOSITIONS
        or not isinstance(gates, list)
        or len(gates) != len({name for names in CASE_GATE_MAP.values() for name in names})
        or any(item.get("status") != "pass" for item in gates)
    ):
        raise ArtifactGenerationRefused(
            f"semantic bridge gates are not passing: disposition={summary.get('disposition')}, "
            f"failed={summary.get('failed_gates')}"
        )


def render_report(summary: Mapping[str, Any]) -> str:
    metrics = summary["metrics"]
    lines = [
        "# Benchmark D rational discrete/continuous bridge proof",
        "",
        f"- Analytic disposition: **{summary['disposition']}**",
        f"- Evidence status: **{summary['evidence_status']}**",
        "- Scope: authored five-state D0 diagonal population sector and named mean-position readout.",
        (
            "- No full-density, scheduler, calibrated physical-time, empirical, "
            "CGT-alignment, or general-CWT claim."
        ),
        "- The proof and assumptions are in `../MODEL_CONTRACT.md`; finite ladders do not establish PASS.",
        "",
        "## Exact primary family",
        "",
        "- Abstract exact-Fraction family: `q_h=(1/25)h`, rational `0<h<=1/5`; `a=1/5`.",
        "- `M_h=(1-delta*h)(I+h*a*(K^T-I))=I+h*A_h`.",
        "- `c_h=h*(delta/5)1`; `A_h=a(1-delta*h)(K^T-I)-delta*I`.",
        "- Exact stationary branch `xbar_h=-A_h^-1*c`; no iterative branch/fixed helper.",
        (
            "- Finite core calls are provenance/regression only on the frozen representable "
            "domain `1/10^12<=h<=1/5`; they do not prove uniform runtime equivalence."
        ),
        "- Uniformity comes only from the exact symbolic affine identity, not sampled core calls.",
        "",
        "## Exact response bridge",
        "",
        "- `h*B_h=B_CT(a_h)+h*d(H*xbar_h)`; the added term is an exact gradient.",
        "- `h*F_h=F_CT(a_h)` exactly on closed loops.",
        f"- Center continuous curvature: `{metrics['continuous_center_curvature']['fraction']}`.",
        f"- First h coefficient: `{metrics['first_h_coefficient']['fraction']}`.",
        (
            "- Directed derivative enclosure: "
            f"`{metrics['curvature_derivative_absolute_upper']['float']:.15g}<88`; "
            "therefore `|hF_h-F_CT|<88h`."
        ),
        "",
        "## Fixed-time integrated response",
        "",
        "- Exact rational scale domain `0<s<=1/100`; the registered report uses `s=1/100`.",
        "- At `s=1/100`, exact extrema leave `1/100` to every D0 box face.",
        (
            "- Common affine clock, positive-integer `N=T/h`, right endpoints, one closing "
            "endpoint, exact reverse, and exact discrete/continuous equilibria are frozen."
        ),
        "- `S_h=sum H[x_n-xbar_h(lambda_n)]`; `Q_h=h*S_h` has model-time units.",
        "- `|Q_h-Q_CT|<=h[(214/25)T+120*pi*s]` for each orientation and Qanti.",
        "- With `pi<=355/113`, the circle coefficient is exactly `42600/113`.",
        (
            "- The certificate recomputes every fixed-time coefficient/premise; formula strings "
            "cannot self-attest PASS."
        ),
        (
            "- Primary order: `h->0` at fixed `T,s`, then `T->infinity`, then optional "
            "`s->0` within the declared domain."
        ),
        (
            "- Limit interchangeability is not claimed; the stated joint conditions are "
            "only sufficient conditions."
        ),
        "",
        "## Prior-artifact boundary",
        "",
        "- The discrete `h=9/50,q=1/125` proof is off-family because `(1/25)h=9/1250`.",
        "- The continuous Lindblad proof is a hash-bound target context, not new or empirical evidence.",
        (
            "- Both prior trees are recursively path-bound; nested additions, omissions, "
            "path/type substitutions, symlinks, and reparse entries are rejected."
        ),
        "- Neither prior artifact tree is regenerated or used as numerical acceptance data here.",
        "",
        "## C1-C12",
        "",
    ]
    for case_id, disposition in summary["case_dispositions"].items():
        lines.append(f"- `{case_id}`: **{disposition}**")
    lines.extend(["", "## Gates", ""])
    for item in summary["gates"]:
        lines.append(f"- **{item['status'].upper()}** `{item['name']}` — {item['requirement']}")
    lines.extend(["", "## Claim ceiling", "", str(summary["claim_ceiling"]), ""])
    return "\n".join(lines)


def expected_artifact_bytes() -> dict[str, bytes]:
    clean_modules = assert_clean_cli_source_closure()
    summary, records = execute_program()
    require_semantic_pass(summary)
    summary_bytes = strict_json_bytes(summary)
    records_bytes = strict_json_bytes(records)
    report_bytes = render_report(summary).encode("utf-8")
    context = next(
        item["value"]
        for item in records
        if item.get("record_type") == "certificate" and item.get("name") == "context"
    )
    provenance = {
        "schema_version": 1,
        "experiment_id": MODEL_CONTRACT.experiment_id,
        "artifact_kind": "internal_analytic_rational_discrete_continuum_bridge_proof",
        "disposition": summary["disposition"],
        "evidence_status": summary["evidence_status"],
        "no_empirical_or_external_data": True,
        "no_full_density_or_scheduler_bridge_claim": True,
        "no_physical_time_or_cgt_alignment_claim": True,
        "trajectory_or_finite_ladder_used_for_acceptance": False,
        "theorem_family_scope": MODEL_CONTRACT.theorem_family_scope,
        "finite_core_regression_scope": MODEL_CONTRACT.core_regression_scope,
        "finite_core_samples_prove_uniform_runtime_equivalence": False,
        "scale_domain": MODEL_CONTRACT.scale_domain,
        "predecessor_context_closure": ("recursive_path_bound_ordinary_files_no_symlink_or_reparse"),
        "source_hash_domain": SOURCE_HASH_DOMAIN,
        "source_hash_domain_definition": SOURCE_HASH_DOMAIN_DEFINITION,
        "source_hashes": source_hashes(),
        "clean_cli_local_module_paths": list(clean_modules),
        "clean_cli_local_module_path_set_sha256": sha256_bytes(strict_json_bytes(list(clean_modules))),
        "prior_artifact_context_raw_hashes": {
            "benchmark_d_open_response_proof": context["open_artifacts"]["raw_file_sha256"],
            "benchmark_d_lindblad_response_proof": context["lindblad_artifacts"]["raw_file_sha256"],
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
            "cd cwt-sim && .venv/Scripts/python.exe "
            "experiments/benchmark_d_discrete_continuum_bridge_proof/run.py run"
        ),
        "verification_command": (
            "cd cwt-sim && .venv/Scripts/python.exe "
            "experiments/benchmark_d_discrete_continuum_bridge_proof/run.py verify"
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
    expected = expected_artifact_bytes()
    output_dir.mkdir(parents=True, exist_ok=True)
    for name, payload in expected.items():
        if b"\r" in payload:
            raise ValueError(f"artifact payload contains CR: {name}")
        (output_dir / name).write_bytes(payload)
    verify_artifacts(output_dir)
    return {name: output_dir / name for name in sorted(expected)}


def verify_artifacts(output_dir: Path = ARTIFACTS_DIR) -> dict[str, object]:
    if not output_dir.is_dir():
        raise ArtifactVerificationError(f"artifact directory is missing: {output_dir}")
    entries = {path.relative_to(output_dir).as_posix(): path for path in output_dir.rglob("*")}
    if set(entries) != EXPECTED_ARTIFACT_NAMES:
        raise ArtifactVerificationError(
            f"artifact closure mismatch: expected={sorted(EXPECTED_ARTIFACT_NAMES)}, "
            f"actual={sorted(entries)}"
        )
    if any(not path.is_file() or path.is_symlink() for path in entries.values()):
        raise ArtifactVerificationError("artifacts must be ordinary top-level files")
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
    summary, _ = execute_program()
    require_semantic_pass(summary)
    return {
        "status": summary["disposition"],
        "evidence_status": summary["evidence_status"],
        "artifact_count": len(expected),
        "source_count": len(TEXT_SOURCE_RELATIVE_PATHS),
        "clean_cli_local_module_count": len(CLEAN_CLI_LOCAL_MODULE_PATHS),
    }
