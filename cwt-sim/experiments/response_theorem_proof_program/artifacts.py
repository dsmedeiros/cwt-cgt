"""Deterministic strict-LF artifacts for the internal analytic proof program."""

from __future__ import annotations

import hashlib
import json
import platform
from pathlib import Path
from typing import Any, Mapping

import numpy as np

from .theorem import execute_program

EXPERIMENT_DIR = Path(__file__).resolve().parent
ARTIFACTS_DIR = EXPERIMENT_DIR / "artifacts"
EXPECTED_ARTIFACT_NAMES = {
    "CHECKSUMS.json",
    "PROVENANCE.json",
    "REPORT.md",
    "records.json",
    "summary.json",
}
SOURCE_PATHS = (
    EXPERIMENT_DIR / "THEOREM.md",
    EXPERIMENT_DIR / "__init__.py",
    EXPERIMENT_DIR / "artifacts.py",
    EXPERIMENT_DIR / "contracts.py",
    EXPERIMENT_DIR / "counterexamples.py",
    EXPERIMENT_DIR / "forms.py",
    EXPERIMENT_DIR / "models.py",
    EXPERIMENT_DIR / "run.py",
    EXPERIMENT_DIR / "theorem.py",
)
SOURCE_HASH_DOMAIN = "sha256_utf8_lf_v1: reject BOM/non-UTF8/bare CR; convert CRLF to LF only"


class ArtifactVerificationError(RuntimeError):
    """Raised when a generated proof-program artifact is missing or changed."""


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def canonical_source_text_bytes(raw: bytes) -> bytes:
    """Canonicalize repository text without changing any semantic character."""

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


def source_text_sha256(path: Path) -> str:
    return sha256_bytes(canonical_source_text_bytes(path.read_bytes()))


def source_hashes() -> dict[str, str]:
    """Return the path-bound canonical source identity."""

    return {
        path.relative_to(EXPERIMENT_DIR).as_posix(): source_text_sha256(path) for path in sorted(SOURCE_PATHS)
    }


def strict_json_bytes(payload: Any) -> bytes:
    """Return deterministic JSON and fail on non-finite floats."""

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


def render_report(summary: Mapping[str, Any]) -> str:
    """Render the claim-scoped human-readable analytic report."""

    metrics = summary["metrics"]
    lines = [
        "# Contractive response theorem proof-program report",
        "",
        f"- Analytic disposition: **{summary['disposition']}**",
        f"- Evidence status: **{summary['evidence_status']}**",
        "- This is a finite-dimensional proof plus deterministic authored fixtures.",
        "- It is not a study PASS, empirical evidence, external validation, or a proof of CWT/CGT alignment.",
        "- Numerical checks exercise the implementation; the analytic proof is in `../THEOREM.md`.",
        "",
        "## Main result",
        "",
        "For a smooth centered update-then-sample response on a uniformly contractive fixed branch,",
        "`Q_c = integral B_c + O(1/N)` with `B_i=-H(I-M)^-1 M X_i`. The on/zero interaction",
        "uses `B^D=B_on-B_0`, its orientation half-difference is `D`, and ordinary DID is `2D`.",
        "Equilibrium-reset scaled loops have the generic bound `C1*s/N+C2*s^2/N`; the stronger",
        "periodic/endpoint-flat bound `C1*s^2/N+C2*s/N^2` requires its separately stated",
        "cancellation assumptions.",
        "The stable-ODE corollary additionally requires a uniformly bounded frozen-branch",
        "inverse and a uniform branch-linearized driven propagator bound. It defines",
        "`Q=integral_0^T r dt`, freezes equilibrium versus periodic/matched initialization,",
        "and uses exact time reversal with one endpoint convention. Propagator decay alone",
        "does not justify `J^-1`; the scalar singular-J counterexample is an executable gate.",
        "",
        "## Exact no-go result",
        "",
        "The linear contraction `x_n=rho*x_(n-1)+(1-rho)*lambda_n` with the declared centered",
        "readout realizes any smooth response one-form `B=beta`, independently of a normalized",
        "projective state map. Therefore contraction and smoothness do not imply `F_R^D=kappa*Omega`.",
        "Neither `Omega != 0 => response` nor `response => Omega` is valid without extra structure.",
        "",
        "## Deterministic metrics",
        "",
        f"- Generic fixed-loop slope: `{metrics['generic_fixed_loop_slope']:.12g}`",
        f"- Periodic fixture slope: `{metrics['periodic_fixed_loop_slope']:.12g}`",
        f"- Maximum generic scaled-bound ratio: `{metrics['max_generic_scaled_bound_ratio']:.12g}`",
        f"- Maximum periodic scaled-bound ratio: `{metrics['max_periodic_scaled_bound_ratio']:.12g}`",
        f"- Nonzero-baseline interaction relative error: `{metrics['interaction_relative_error']:.12g}`",
        f"- Exact realizability identity error: `{metrics['no_go_identity_error']:.12g}`",
        (
            "- Continuous equilibrium/periodic slopes: "
            f"`{metrics['continuous_generic_slope']:.12g}` / "
            f"`{metrics['continuous_periodic_slope']:.12g}`"
        ),
        "",
        "## Frozen cases",
        "",
    ]
    for case_id, disposition in summary["case_dispositions"].items():
        lines.append(f"- `{case_id}`: **{disposition}**")
    lines.extend(
        [
            "",
            "C8 is this program's `proof_program_similarity_family_v1` three-dimensional",
            "similarity construction. It is not the adversarial review's separate projector",
            "example; only the qualitative non-Hermitian scope warning is shared. The computed",
            "`-2+2i` value belongs only to this program's fixture.",
        ]
    )
    lines.extend(["", "## Gates", ""])
    for gate in summary["gates"]:
        lines.append(f"- **{gate['status'].upper()}** `{gate['name']}` — {gate['requirement']}")
    lines.extend(
        [
            "",
            "## Claim ceiling",
            "",
            "The program proves only the declared contractive-class response reduction and the exact",
            "realizability/no-go statement. P1 is a deliberately aligned oracle/positive implementation",
            "control, not an independently measured response; C5 is a 2D",
            "tautology, and C8 is outside the pure-state scope. The repository still has no qualifying",
            "external active-loop substrate or empirical evidence for a CGT/readout alignment law.",
            "",
        ]
    )
    return "\n".join(lines)


def expected_artifact_bytes() -> dict[str, bytes]:
    """Recompute all deterministic artifacts without reading existing outputs."""

    summary, records = execute_program()
    summary_bytes = strict_json_bytes(summary)
    records_bytes = strict_json_bytes(records)
    report_bytes = render_report(summary).encode("utf-8")
    sources = source_hashes()
    provenance = {
        "schema_version": 1,
        "experiment_id": "response_theorem_proof_program",
        "artifact_kind": "internal_analytic_proof_program",
        "disposition": summary["disposition"],
        "evidence_status": summary["evidence_status"],
        "numerics_are_not_the_proof": True,
        "no_empirical_or_external_data": True,
        "source_hash_domain": SOURCE_HASH_DOMAIN,
        "source_hashes": sources,
        "payload_sha256": {
            "REPORT.md": sha256_bytes(report_bytes),
            "records.json": sha256_bytes(records_bytes),
            "summary.json": sha256_bytes(summary_bytes),
        },
        "runtime": {
            "python": platform.python_version(),
            "numpy": np.__version__,
        },
        "reproduction_command": (
            "cd cwt-sim && .venv/Scripts/python.exe " "experiments/response_theorem_proof_program/run.py run"
        ),
        "verification_command": (
            "cd cwt-sim && .venv/Scripts/python.exe "
            "experiments/response_theorem_proof_program/run.py verify"
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

    output_dir.mkdir(parents=True, exist_ok=True)
    expected = expected_artifact_bytes()
    for name, payload in expected.items():
        _write_lf(output_dir / name, payload)
    verify_artifacts(output_dir)
    return {name: output_dir / name for name in sorted(expected)}


def verify_artifacts(output_dir: Path = ARTIFACTS_DIR) -> dict[str, object]:
    """Verify exact contents, strict JSON, LF bytes, and recursive closure."""

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
    return {
        "status": "PASS_INTERNAL_ANALYTIC",
        "evidence_status": "NO_EMPIRICAL_EVIDENCE",
        "artifact_count": len(expected),
        "source_count": len(SOURCE_PATHS),
    }
