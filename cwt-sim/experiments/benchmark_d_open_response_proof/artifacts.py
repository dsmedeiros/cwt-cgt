"""Deterministic isolated artifacts for the Benchmark D response proof."""

from __future__ import annotations

import hashlib
import json
import platform
import subprocess
import sys
from pathlib import Path
from typing import Any, Mapping

import numpy as np

from .contract import EXPECTED_CASE_DISPOSITIONS
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
MODEL_EXPERIMENT_ID = "benchmark_d_open_response_proof"

# Exact clean-process local import closure for this standalone CLI entrypoint.
# It is sorted and path-bound; import order, stdlib, site-packages, bytecode, and
# cache state are deliberately outside the provenance domain.
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
    "experiments/benchmark_d_open_response_proof/__init__.py",
    "experiments/benchmark_d_open_response_proof/adapter.py",
    "experiments/benchmark_d_open_response_proof/artifacts.py",
    "experiments/benchmark_d_open_response_proof/contract.py",
    "experiments/benchmark_d_open_response_proof/exact_oracle.py",
    "experiments/benchmark_d_open_response_proof/fixed_branch.py",
    "experiments/benchmark_d_open_response_proof/response.py",
    "experiments/benchmark_d_open_response_proof/run.py",
    "experiments/benchmark_d_open_response_proof/theorem.py",
)
ADDITIONAL_MATERIAL_TEXT_PATHS = (
    "cwt/cgt/analysis/phase10_analysis.py",
    "experiments/benchmark_d_open_response_proof/MODEL_CONTRACT.md",
    "experiments/response_theorem_proof_program/THEOREM.md",
    "scripts/cgt/run_phase10_analysis.py",
    "tests/experiments/test_benchmark_d_open_response_proof.py",
)
TEXT_SOURCE_RELATIVE_PATHS = tuple(
    sorted(set(CLEAN_CLI_LOCAL_MODULE_PATHS) | set(ADDITIONAL_MATERIAL_TEXT_PATHS))
)
SOURCE_PATHS = tuple(SIM_ROOT / relative for relative in TEXT_SOURCE_RELATIVE_PATHS)
SOURCE_HASH_DOMAIN = "sha256_utf8_lf_v1"
SOURCE_HASH_DOMAIN_DEFINITION = (
    "strict UTF-8 with BOM forbidden; map CRLF to LF only; reject any remaining bare CR; "
    "no whitespace or Unicode normalization"
)
RAW_HASH_DOMAIN = "sha256_raw_bytes_v1"
PHASE10_IDENTITY_SPECS: Mapping[str, tuple[str, str]] = {
    "cgt_benchmarks/results/benchmark_C_ring/benchmark_c_phase10.json": (
        "tracked_historical_phase10_result_json_with_branch_steps_2",
        RAW_HASH_DOMAIN,
    ),
    "cwt/cgt/analysis/phase10_analysis.py": (
        "current_phase10_recomputation_implementation_module",
        SOURCE_HASH_DOMAIN,
    ),
    "scripts/cgt/run_phase10_analysis.py": (
        "historical_phase10_entry_script_explicitly_selecting_branch_steps_2",
        SOURCE_HASH_DOMAIN,
    ),
}


class ArtifactVerificationError(RuntimeError):
    """Raised when the isolated deterministic artifact closure differs."""


class ArtifactGenerationRefused(RuntimeError):
    """Raised before writing when any semantic theorem gate is not passing."""


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def canonical_source_text_bytes(raw: bytes) -> bytes:
    """Produce portable repository-text identity without semantic normalization."""

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


def source_hashes() -> dict[str, str]:
    """Return sorted, path-bound canonical hashes of every material source dependency."""

    return {
        relative: sha256_bytes(canonical_source_text_bytes((SIM_ROOT / relative).read_bytes()))
        for relative in TEXT_SOURCE_RELATIVE_PATHS
    }


def _git_index_blob(relative: str) -> tuple[str, bytes]:
    """Return the staged Git blob OID and bytes for one repository-relative dependency."""

    repository_path = f"cwt-sim/{relative}"
    try:
        oid = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "rev-parse", f":{repository_path}"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        blob = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "cat-file", "blob", oid],
            check=True,
            capture_output=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError) as exc:
        raise ArtifactVerificationError(
            f"cannot resolve Git index blob for Phase10 dependency: {relative}"
        ) from exc
    if len(oid) != 40 or any(character not in "0123456789abcdef" for character in oid):
        raise ArtifactVerificationError(f"invalid Git blob OID for Phase10 dependency: {relative}")
    return oid, blob


def _canonical_text_identity_bytes(raw: bytes, index_blob: bytes, relative: str) -> bytes:
    """Require canonical worktree text to equal the exact staged LF blob."""

    canonical = canonical_source_text_bytes(raw)
    if canonical_source_text_bytes(index_blob) != index_blob:
        raise ArtifactVerificationError(f"Git index blob is not canonical UTF-8 LF text: {relative}")
    if canonical != index_blob:
        raise ArtifactVerificationError(f"canonical Phase10 text differs from Git index blob: {relative}")
    return canonical


def phase10_identity_records() -> dict[str, dict[str, object]]:
    """Bind the three Phase10 identities in explicit, portable byte domains."""

    records: dict[str, dict[str, object]] = {}
    for relative, (role, hash_domain) in PHASE10_IDENTITY_SPECS.items():
        raw = (SIM_ROOT / relative).read_bytes()
        oid, index_blob = _git_index_blob(relative)
        if hash_domain == SOURCE_HASH_DOMAIN:
            identity_bytes = _canonical_text_identity_bytes(raw, index_blob, relative)
        elif hash_domain == RAW_HASH_DOMAIN:
            if raw != index_blob:
                raise ArtifactVerificationError(
                    f"raw Phase10 dependency differs from Git index blob: {relative}"
                )
            identity_bytes = raw
        else:  # pragma: no cover - closed constant registry
            raise ArtifactVerificationError(f"unknown Phase10 identity hash domain: {hash_domain}")
        records[relative] = {
            "role": role,
            "hash_domain": hash_domain,
            "sha256": sha256_bytes(identity_bytes),
            "git_blob_oid": oid,
            "identity_bytes_equal_git_index_blob": True,
        }
    return records


_CLEAN_IMPORT_SCRIPT = r"""
import json
import pathlib
import sys

root = pathlib.Path.cwd().resolve()
import experiments.benchmark_d_open_response_proof.run  # noqa: E402,F401

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
    """Collect the local-module closure in a fresh process under the CLI entrypoint."""

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
    """Reject undeclared or absent local modules loaded by a clean CLI import."""

    actual = clean_cli_local_module_paths()
    if actual != CLEAN_CLI_LOCAL_MODULE_PATHS:
        absent = sorted(set(CLEAN_CLI_LOCAL_MODULE_PATHS) - set(actual))
        undeclared = sorted(set(actual) - set(CLEAN_CLI_LOCAL_MODULE_PATHS))
        raise ArtifactVerificationError(
            f"clean CLI source closure mismatch: absent={absent}, undeclared={undeclared}"
        )
    return actual


def strict_json_bytes(payload: Any) -> bytes:
    return (json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n").encode(
        "utf-8"
    )


def require_semantic_pass(summary: Mapping[str, Any]) -> None:
    """Fail closed before artifact generation on any gate/case inconsistency."""

    failed = summary.get("failed_gates")
    cases = summary.get("case_dispositions")
    gates = summary.get("gates")
    if (
        summary.get("disposition") != "PASS_INTERNAL_ANALYTIC"
        or summary.get("evidence_status") != "NO_EMPIRICAL_EVIDENCE"
        or summary.get("all_gates_pass") is not True
        or failed != []
        or cases != EXPECTED_CASE_DISPOSITIONS
        or not isinstance(gates, list)
        or not gates
        or any(gate.get("status") != "pass" for gate in gates)
    ):
        raise ArtifactGenerationRefused(
            f"semantic proof gates are not passing: disposition={summary.get('disposition')}, "
            f"failed={failed}, cases={cases}"
        )


def render_report(summary: Mapping[str, Any]) -> str:
    """Render a self-scoped human-readable report from the deterministic summary."""

    metrics = summary["metrics"]
    lines = [
        "# Benchmark D true-fixed open-response proof report",
        "",
        f"- Analytic disposition: **{summary['disposition']}**",
        f"- Evidence status: **{summary['evidence_status']}**",
        "- Scope: internal synthetic authored five-state fixed-tick channel/readout only.",
        "- This is not empirical evidence, physical time, the full scheduler, or CGT alignment.",
        "- Numerical gates exercise the implementation; the proof is in `../MODEL_CONTRACT.md`.",
        "",
        "## Frozen specialization",
        "",
        "- Core map: `cwt.cgt.open_system.apply_local_open_step`",
        "- Benchmark/branch: `benchmark_d` / fixed `D0` (no continuation)",
        "- Controls: `b in [0.01,0.05]`, `d in [0.205,0.245]`; center `(0.03,0.225)`",
        "- Readout: centered geometry-blind `mean_position=diag(1,2,3,4,5)`",
        "- Channel: `dt=.18`, edge jump `.20`, depolarizing `.008=1/125`, dephasing `.30`,",
        "  coherent/site-potential scales zero",
        "- Cycle: right-endpoint update then sample; CW is the exact stored-sequence reverse",
        "",
        "The diagonal invariant subspace obeys `x' = Mx+c`, with",
        "`M=(124/125)[(1-9/250)I+(9/250)K]^T` and `c=(1/625)1`.",
        "The true fixed branch is solved as `[I-M]^-1 c`.",
        "",
        "## Exact result",
        "",
        f"- `F_bd` fraction: `{metrics['exact_response_curvature_fraction']}`",
        f"- `F_bd` decimal: `{metrics['exact_response_curvature_float']:.15g}`",
        f"- Independent analytic float: `{metrics['analytic_response_curvature_float']:.15g}`",
        f"- Central-difference curl: `{metrics['numerical_response_curvature_float']:.15g}`",
        f"- Fixed-loop tail log slope: `{metrics['fixed_loop_tail_log_slope']:.12g}`",
        (
            "- Shrinking-loop finest area-density relative error: "
            f"`{metrics['shrinking_finest_relative_density_error']:.12g}`"
        ),
        (
            "- Exact global full-rank eigenvalue floor from depolarization: "
            f"`{metrics['exact_global_fixed_eigenvalue_floor']:.12g}`"
        ),
        (
            "- Sampled minimum fixed eigenvalue on the 5x5 diagnostic mesh: "
            f"`{metrics['sampled_fixed_branch_minimum_eigenvalue']:.12g}`"
        ),
        (
            "- Sampled fixed-branch variation on that mesh: "
            f"`{metrics['sampled_fixed_branch_variation_l2']:.12g}`"
        ),
        (
            "- Maximum fixed-solver centering budget / observed density error: "
            f"`{metrics['shrinking_max_centering_budget_ratio']:.12g}`"
        ),
        "",
        "The shrinking ladder doubles `N*s`; holding `N*s` fixed is not accepted because the",
        "generic equilibrium-reset remainder is `O(s/N)`. Its 0.60 ratio and 0.10 final-error",
        "thresholds were selected during internal harness development, after the ladder design;",
        "they are deterministic regression checks, not preregistered evidence.",
        "",
        "## Frozen case dispositions",
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
            "## Historical surrogate limitation",
            "",
            "The historical entry script explicitly set `branch_steps=2`; the tracked Phase10",
            "Benchmark-C JSON records that value and recommended `gamma=0.2`. The current library",
            "default is 3, while `cwt/cgt/analysis/phase10_analysis.py` is the current recomputation",
            "implementation. Recomputing C0 from the explicit tracked configuration gives a",
            "nonzero fixed residual, so it is a finite-step surrogate rather than a stationary",
            "density. A separate Benchmark-D three-step diagnostic is reported only as a distinct",
            "limitation check and does not validate the tracked Benchmark-C artifact.",
            "",
            "## Projective reference control",
            "",
            "The authored stationary-probability D0 geometry is not used as a smooth projective",
            "branch. Instead the frozen zero coherent/site terms make a separately declared",
            "constant normalized reference `p_j=1/5, theta_j=0` channel-equivalent. Its derivatives",
            "and `Omega_bd` are exactly zero. Together with nonzero response curvature this is only",
            "a constant-reference no-go control; it supplies no CGT alignment evidence.",
            "",
            "## Claim ceiling",
            "",
            str(summary["claim_ceiling"]),
            "The exact-zero constant reference and nonzero response instantiate only the statement",
            "that response curvature does not by itself imply a universal CGT alignment law.",
            "",
        ]
    )
    return "\n".join(lines)


def expected_artifact_bytes() -> dict[str, bytes]:
    """Recompute the complete artifact closure without reading existing outputs."""

    clean_modules = assert_clean_cli_source_closure()
    summary, records = execute_program()
    require_semantic_pass(summary)
    summary_bytes = strict_json_bytes(summary)
    records_bytes = strict_json_bytes(records)
    report_bytes = render_report(summary).encode("utf-8")
    provenance = {
        "schema_version": 2,
        "experiment_id": MODEL_EXPERIMENT_ID,
        "artifact_kind": "internal_synthetic_analytic_true_fixed_response_proof",
        "disposition": summary["disposition"],
        "evidence_status": summary["evidence_status"],
        "central_empirical_external_claim_status": "PROOF_INCOMPLETE",
        "no_empirical_or_external_data": True,
        "no_full_scheduler_or_physical_time_claim": True,
        "no_cgt_alignment_claim": True,
        "source_hash_domain": SOURCE_HASH_DOMAIN,
        "source_hash_domain_definition": SOURCE_HASH_DOMAIN_DEFINITION,
        "source_hashes": source_hashes(),
        "phase10_identity_records": phase10_identity_records(),
        "clean_cli_local_module_paths": list(clean_modules),
        "clean_cli_local_module_path_set_sha256": sha256_bytes(strict_json_bytes(list(clean_modules))),
        "raw_artifact_payload_sha256": {
            "REPORT.md": sha256_bytes(report_bytes),
            "records.json": sha256_bytes(records_bytes),
            "summary.json": sha256_bytes(summary_bytes),
        },
        "runtime": {"python": platform.python_version(), "numpy": np.__version__},
        "reproduction_command": (
            "cd cwt-sim && .venv/Scripts/python.exe " "experiments/benchmark_d_open_response_proof/run.py run"
        ),
        "verification_command": (
            "cd cwt-sim && .venv/Scripts/python.exe "
            "experiments/benchmark_d_open_response_proof/run.py verify"
        ),
    }
    provenance_bytes = strict_json_bytes(provenance)
    checksums = {
        "schema_version": 1,
        "hash_domain": "raw_artifact_bytes_sha256",
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
    """Write only the experiment-local deterministic artifact set."""

    expected = expected_artifact_bytes()
    output_dir.mkdir(parents=True, exist_ok=True)
    for name, payload in expected.items():
        _write_lf(output_dir / name, payload)
    verify_artifacts(output_dir)
    return {name: output_dir / name for name in sorted(expected)}


def verify_artifacts(output_dir: Path = ARTIFACTS_DIR) -> dict[str, object]:
    """Verify exact bytes, strict JSON/LF, and recursive isolated closure."""

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
        "source_count": len(SOURCE_PATHS),
        "clean_cli_local_module_count": len(CLEAN_CLI_LOCAL_MODULE_PATHS),
    }
