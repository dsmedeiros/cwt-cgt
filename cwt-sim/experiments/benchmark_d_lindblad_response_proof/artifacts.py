"""Deterministic isolated artifacts for the Benchmark D Lindblad proof."""

from __future__ import annotations

import hashlib
import json
import platform
import subprocess
import sys
from pathlib import Path
from typing import Any, Mapping

import numpy as np
import typer

from .contract import EXPECTED_CASE_DISPOSITIONS, MODEL_CONTRACT
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

# This exact sorted path-bound set is replaced only after a clean CLI import audit.
CLEAN_CLI_LOCAL_MODULE_PATHS = (
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
    "experiments/benchmark_d_lindblad_response_proof/__init__.py",
    "experiments/benchmark_d_lindblad_response_proof/adapter.py",
    "experiments/benchmark_d_lindblad_response_proof/artifacts.py",
    "experiments/benchmark_d_lindblad_response_proof/certificates.py",
    "experiments/benchmark_d_lindblad_response_proof/contract.py",
    "experiments/benchmark_d_lindblad_response_proof/exact_math.py",
    "experiments/benchmark_d_lindblad_response_proof/run.py",
    "experiments/benchmark_d_lindblad_response_proof/theorem.py",
)
ADDITIONAL_MATERIAL_TEXT_PATHS = (
    "cgt_benchmarks/reports/CWT-CGT_Phase_11_Report.md",
    "cwt/cgt/analysis/phase11_analysis.py",
    "experiments/benchmark_d_lindblad_response_proof/MODEL_CONTRACT.md",
    "experiments/response_theorem_proof_program/THEOREM.md",
    "scripts/cgt/run_phase11_analysis.py",
    "tests/experiments/test_benchmark_d_lindblad_response_proof.py",
)
TEXT_SOURCE_RELATIVE_PATHS = tuple(
    sorted(set(CLEAN_CLI_LOCAL_MODULE_PATHS) | set(ADDITIONAL_MATERIAL_TEXT_PATHS))
)
PHASE11_IDENTITY_SPECS: Mapping[str, tuple[str, str]] = {
    "scripts/cgt/run_phase11_analysis.py": (
        "historical_phase11_entry_script_with_stale_04_code_src_and_module_path",
        SOURCE_HASH_DOMAIN,
    ),
    "cwt/cgt/analysis/phase11_analysis.py": (
        "current_phase11_recomputation_implementation_using_euler_projection_and_finite_branch_density",
        SOURCE_HASH_DOMAIN,
    ),
    "cgt_benchmarks/reports/phase11_summary.json": (
        "tracked_phase11_summary_artifact",
        RAW_HASH_DOMAIN,
    ),
    "cgt_benchmarks/reports/CWT-CGT_Phase_11_Report.md": (
        "tracked_phase11_interpretation_report",
        SOURCE_HASH_DOMAIN,
    ),
}


class ArtifactVerificationError(RuntimeError):
    """Raised when the deterministic artifact/source closure differs."""


class ArtifactGenerationRefused(RuntimeError):
    """Raised before writing when any semantic theorem gate is not passing."""


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def canonical_source_text_bytes(raw: bytes) -> bytes:
    """Return portable LF source identity with a strict and narrow transformation."""

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
    """Hash all material text in a path-bound, platform-independent domain."""

    return {
        relative: {
            "hash_domain": SOURCE_HASH_DOMAIN,
            "sha256": sha256_bytes(canonical_source_text_bytes((SIM_ROOT / relative).read_bytes())),
        }
        for relative in TEXT_SOURCE_RELATIVE_PATHS
    }


def phase11_identity_records() -> dict[str, dict[str, str]]:
    """Bind historical entry, implementation, artifact, and report without rerunning them."""

    records: dict[str, dict[str, str]] = {}
    for relative, (role, domain) in PHASE11_IDENTITY_SPECS.items():
        raw = (SIM_ROOT / relative).read_bytes()
        identity = canonical_source_text_bytes(raw) if domain == SOURCE_HASH_DOMAIN else raw
        records[relative] = {
            "role": role,
            "hash_domain": domain,
            "sha256": sha256_bytes(identity),
        }
    return records


_CLEAN_IMPORT_SCRIPT = r"""
import json
import pathlib
import sys

root = pathlib.Path.cwd().resolve()
import experiments.benchmark_d_lindblad_response_proof.run  # noqa: E402,F401

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
    completed = subprocess.run(
        [sys.executable, "-c", _CLEAN_IMPORT_SCRIPT],
        cwd=SIM_ROOT,
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
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
    """Refuse output unless gates, cases, claim tier, and evidence tier all agree."""

    gates = summary.get("gates")
    if (
        summary.get("disposition") != "PASS_INTERNAL_ANALYTIC"
        or summary.get("evidence_status") != "NO_EMPIRICAL_EVIDENCE"
        or summary.get("all_gates_pass") is not True
        or summary.get("failed_gates") != []
        or summary.get("case_dispositions") != EXPECTED_CASE_DISPOSITIONS
        or not isinstance(gates, list)
        or len(gates) != 26
        or any(gate.get("status") != "pass" for gate in gates)
    ):
        raise ArtifactGenerationRefused(
            f"semantic proof gates are not passing: disposition={summary.get('disposition')}, "
            f"failed={summary.get('failed_gates')}"
        )


def render_report(summary: Mapping[str, Any]) -> str:
    metrics = summary["metrics"]
    lines = [
        "# Benchmark D continuous Lindblad response proof report",
        "",
        f"- Analytic disposition: **{summary['disposition']}**",
        f"- Evidence status: **{summary['evidence_status']}**",
        "- Scope: internal authored five-state continuous Lindblad generator/readout only.",
        "- No empirical, physical-time, universal-CGT, or derived-CWT-continuum claim is made.",
        "- The proof and assumptions are in `../MODEL_CONTRACT.md`; interval numerics implement it.",
        "",
        "## Frozen specialization",
        "",
        "- Benchmark/branch: `benchmark_d` / `D0`; controls `b,d`",
        "- Box: `b∈[.01,.05]`, `d∈[.205,.245]`; center `(.03,.225)`",
        "- Core bindings: `lindblad_rhs`, `lindblad_superoperator`, named `mean_position` readout",
        "- Exact affine flow: `x_dot=[(1/5)(K^T-I)-(1/25)I]x+(1/125)1`",
        "- Actual dephasing `.30`; coherent and site-potential scales exactly zero",
        (
            "- Loop: CCW circle `s=.01`, exact reverse CW, equilibrium initialization, "
            "continuous model-time integral"
        ),
        (
            "- Slow clock: `u=t/T`, `lambda_+(t)=gamma_+(u)`, and "
            "`lambda_-(t)=lambda_+(T-t)=gamma_+(1-u)` for `0<=t<=T`"
        ),
        "- Units: rates are inverse model-time, `T` is model-time, the readout is a dimensionless",
        "  mean-position index, and `Q` is mean-position-index times model-time.",
        "- Physical interpretation requires external clock and readout calibration, which is absent here.",
        "- Euler stepping and PSD projection are forbidden on the theorem path",
        "",
        "## Exact response and analytic dynamic certificate",
        "",
        f"- `F_bd`: `{metrics['exact_response_curvature_fraction']}`",
        f"- `F_bd` decimal: `{metrics['exact_response_curvature_float']:.15g}`",
        f"- Uniform fixed-state eigenvalue floor: `{metrics['uniform_full_rank_floor']['fraction']}`",
        f"- Primary scale: `{metrics['primary_scale']['fraction']}`",
        f"- `C(s)`: `{metrics['primary_remainder_C']['float']:.15g}` readout·model-time²",
        (
            f"- Certified `L_min(s)`: `{metrics['primary_line_magnitude_lower']['float']:.15g}` "
            "readout·model-time"
        ),
        f"- `T0=2^ceil(log2(4C/L_min))`: `{metrics['primary_duration_T0']}`",
        "- Acceptance uses exact-rational directed intervals and `|Qanti-L|<=C/T`; no trajectory",
        "  or fitted slope determines PASS.",
        "",
        "## C1-C13",
        "",
    ]
    for case_id, disposition in summary["case_dispositions"].items():
        lines.append(f"- `{case_id}`: **{disposition}**")
    lines.extend(["", "## Gates", ""])
    for gate in summary["gates"]:
        lines.append(f"- **{gate['status'].upper()}** `{gate['name']}` — {gate['requirement']}")
    lines.extend(
        [
            "",
            "## Phase 11 supersession boundary",
            "",
            "The tracked Phase 11 entry script points to a stale `04_code/src` layout and stale",
            "module path. Its current implementation and tracked summary use finite Euler steps, PSD",
            "projection, cached finite-step branch densities, and mean/final-sample responses. They do",
            "not instantiate this theorem. This package supersedes only the narrow Benchmark-D analytic",
            "question under the explicit contract; it does not validate the Phase 11 global fits.",
            "",
            "## Projective no-go control",
            "",
            "The auxiliary smooth positive-real D0 map has exact `Omega_bd=0`, while the",
            "separately computed response has nonzero `F_bd`. It is channel-equivalent because",
            "`p` and `theta` are inactive under zero coherent/site terms, but it is not the current",
            "core helper `BranchState` geometry. This refutes only a universal",
            "contraction-implies-alignment inference; it is not substrate evidence.",
            "",
            "## Claim ceiling",
            "",
            str(summary["claim_ceiling"]),
            "",
        ]
    )
    return "\n".join(lines)


def expected_artifact_bytes() -> dict[str, bytes]:
    clean_modules = assert_clean_cli_source_closure()
    summary, records = execute_program()
    require_semantic_pass(summary)
    summary_bytes = strict_json_bytes(summary)
    records_bytes = strict_json_bytes(records)
    report_bytes = render_report(summary).encode("utf-8")
    provenance = {
        "schema_version": 1,
        "experiment_id": MODEL_CONTRACT.experiment_id,
        "artifact_kind": "internal_analytic_continuous_lindblad_response_proof",
        "disposition": summary["disposition"],
        "evidence_status": summary["evidence_status"],
        "central_empirical_external_claim_status": "PROOF_INCOMPLETE",
        "no_empirical_or_external_data": True,
        "no_trajectory_used_for_acceptance": True,
        "no_cgt_alignment_or_derived_cwt_continuum_claim": True,
        "units": {
            "time_domain": MODEL_CONTRACT.time_domain,
            "generator_rates": MODEL_CONTRACT.generator_rate_units,
            "duration": MODEL_CONTRACT.duration_units,
            "readout": MODEL_CONTRACT.readout_units,
            "integrated_response": MODEL_CONTRACT.integrated_response_units,
            "physical_calibration": MODEL_CONTRACT.physical_time_calibration_status,
        },
        "source_hash_domain": SOURCE_HASH_DOMAIN,
        "source_hash_domain_definition": SOURCE_HASH_DOMAIN_DEFINITION,
        "source_hashes": source_hashes(),
        "phase11_identity_records": phase11_identity_records(),
        "clean_cli_local_module_paths": list(clean_modules),
        "clean_cli_local_module_path_set_sha256": sha256_bytes(strict_json_bytes(list(clean_modules))),
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
            "experiments/benchmark_d_lindblad_response_proof/run.py run"
        ),
        "verification_command": (
            "cd cwt-sim && .venv/Scripts/python.exe "
            "experiments/benchmark_d_lindblad_response_proof/run.py verify"
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


def _write_lf(path: Path, payload: bytes) -> None:
    if b"\r" in payload:
        raise ValueError(f"artifact payload contains CR: {path.name}")
    path.write_bytes(payload)


def write_artifacts(output_dir: Path = ARTIFACTS_DIR) -> dict[str, Path]:
    expected = expected_artifact_bytes()
    output_dir.mkdir(parents=True, exist_ok=True)
    for name, payload in expected.items():
        _write_lf(output_dir / name, payload)
    verify_artifacts(output_dir)
    return {name: output_dir / name for name in sorted(expected)}


def verify_artifacts(output_dir: Path = ARTIFACTS_DIR) -> dict[str, object]:
    if not output_dir.is_dir():
        raise ArtifactVerificationError(f"artifact directory is missing: {output_dir}")
    actual_entries = {path.relative_to(output_dir).as_posix(): path for path in output_dir.rglob("*")}
    if set(actual_entries) != EXPECTED_ARTIFACT_NAMES:
        raise ArtifactVerificationError(
            f"artifact closure mismatch: expected {sorted(EXPECTED_ARTIFACT_NAMES)}, "
            f"found {sorted(actual_entries)}"
        )
    if any(not path.is_file() or path.is_symlink() for path in actual_entries.values()):
        raise ArtifactVerificationError("artifacts must be ordinary files with no nested entries")
    expected = expected_artifact_bytes()
    for name, expected_bytes in expected.items():
        actual = actual_entries[name].read_bytes()
        if b"\r" in actual:
            raise ArtifactVerificationError(f"artifact is not strict LF: {name}")
        if actual != expected_bytes:
            raise ArtifactVerificationError(f"artifact content mismatch: {name}")
        if name.endswith(".json"):
            parsed = json.loads(actual.decode("utf-8"))
            if strict_json_bytes(parsed) != actual:
                raise ArtifactVerificationError(f"artifact is not canonical strict JSON: {name}")
    summary, _records = execute_program()
    require_semantic_pass(summary)
    return {
        "status": summary["disposition"],
        "evidence_status": summary["evidence_status"],
        "artifact_count": len(expected),
        "source_count": len(TEXT_SOURCE_RELATIVE_PATHS),
        "clean_cli_local_module_count": len(CLEAN_CLI_LOCAL_MODULE_PATHS),
    }
