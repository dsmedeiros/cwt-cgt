"""Standalone CLI for the fixed-tick independent-response theorem harness."""

from __future__ import annotations

import hashlib
import json
import platform
import subprocess
import sys
from pathlib import Path
from typing import Any

import numpy as np
import typer

EXPERIMENT_DIR = Path(__file__).resolve().parent
SIM_ROOT = EXPERIMENT_DIR.parents[1]
ARTIFACTS_DIR = EXPERIMENT_DIR / "artifacts"
PROTOCOL_PATH = EXPERIMENT_DIR / "PROTOCOL_LOCK.md"

if str(SIM_ROOT) not in sys.path:
    sys.path.insert(0, str(SIM_ROOT))

from experiments.independent_response_theorem.provenance import (  # noqa: E402
    PRE_CORRECTION_SEMANTIC_SHA256,
    SOURCE_TEXT_HASH_DOMAIN,
    SOURCE_TEXT_HASH_SPEC,
    build_correction_ledger,
    build_source_manifest,
    source_bundle_payload,
    source_bundle_sha256,
    source_text_sha256,
    verify_source_manifest,
)
from experiments.independent_response_theorem.theorem import DEFAULT_CONFIG, execute_protocol  # noqa: E402

app = typer.Typer(
    add_completion=False,
    help=(
        "Run the locked internal-synthetic benchmark-C fixed-tick geometry-blind-response "
        "theorem. Geometry-blind does not mean independent empirical validation, external "
        "evidence, or a physical transported-charge measurement."
    ),
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def _json_sha256(payload: Any) -> str:
    encoded = json.dumps(
        payload,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _git_value(*args: str) -> str:
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=SIM_ROOT,
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return "unavailable"
    if completed.returncode != 0:
        return "unavailable"
    return completed.stdout.strip() or "unavailable"


def build_provenance(summary: dict[str, Any], records: list[dict[str, Any]]) -> dict[str, Any]:
    """Build durable, strict provenance without claiming external validation."""

    source_manifest = build_source_manifest(SIM_ROOT)
    verify_source_manifest(SIM_ROOT, source_manifest)
    return {
        "schema_version": 2,
        "experiment_id": "independent_response_theorem",
        "evidence_tier": "internal_synthetic_analytic_fixture",
        "claim_scope": "explicit benchmark-C fixed-tick geometry-blind-response theorem",
        "central_empirical_external_claim_status": "proof_incomplete",
        "external_raw_data_runnable": False,
        "external_data_blocker": (
            "No auditable raw paired-loop dataset, frozen manifest/checksum, and independent "
            "measured response are tracked and runnable in this repository."
        ),
        "estimand": "discrete_cycle_sum_surrogate",
        "estimand_units": "circulation-current-ticks with dt=1",
        "fixed_tick_semantics": {
            "dt": 1,
            "phase_relaxation_per_tick": DEFAULT_CONFIG.phase_relaxation,
            "increasing_steps": "lengthens and slows the discrete cycle",
        },
        "discovery_disclosure": (
            "The cycle-sum estimand and numerical acceptance thresholds were selected after "
            "an exploratory center-(0,0) square refinement probe; all benchmark-C "
            "configurations are discovery/analytic fixtures."
        ),
        "two_dimensional_quotient_disclosure": (
            "Where Omega is nonzero, F_R/Omega exists algebraically because any two 2-forms "
            "in a two-dimensional parameter chart are pointwise proportional. Comparing it "
            "with Q_anti/Phi_anti is implementation consistency, not CGT-predictive evidence."
        ),
        "not_preregistered": True,
        "not_untouched_holdout": True,
        "not_external_evidence": True,
        "not_transported_charge_or_physical_pump": True,
        "no_seeds_or_uncertainty_intervals": True,
        "protocol_file": "../PROTOCOL_LOCK.md",
        "protocol_sha256": _sha256(PROTOCOL_PATH),
        "config_sha256": _json_sha256(summary["config"]),
        "summary_canonical_json_sha256": _json_sha256(summary),
        "records_canonical_json_sha256": _json_sha256(records),
        "canonical_json_hash_encoding": (
            "UTF-8 JSON with allow_nan=false, sort_keys=true, and separators=(',', ':')"
        ),
        "source_text_hash_domain": SOURCE_TEXT_HASH_SPEC,
        "source_text_hash_domain_id": SOURCE_TEXT_HASH_DOMAIN,
        "source_text_dependencies": source_manifest,
        "source_bundle_payload": source_bundle_payload(source_manifest),
        "source_bundle_sha256": source_bundle_sha256(source_manifest),
        "source_bundle_is_sorted_and_path_bound": True,
        "canonical_source_hashes_are_repository_identity_not_execution_bytes": True,
        "pre_commit_post_result_provenance_format_correction": {
            "ledger": "PROVENANCE_CORRECTION.json",
            "ledger_sidecar": "PROVENANCE_CORRECTION.sha256",
            "status": "PACKAGING_CORRECTION_NO_NUMERIC_CHANGE",
        },
        "repository_head": _git_value("rev-parse", "HEAD"),
        "repository_worktree": ("clean" if _git_value("status", "--porcelain") == "" else "dirty"),
        "python_version": platform.python_version(),
        "numpy_version": np.__version__,
        "reproduction_command": (
            "cd cwt-sim && .venv/Scripts/python.exe " "experiments/independent_response_theorem/run.py"
        ),
    }


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(
        json.dumps(payload, allow_nan=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def render_report(summary: dict[str, Any], provenance: dict[str, Any]) -> str:
    """Render the self-describing human-readable theorem report."""

    metrics = summary["metrics"]
    lines = [
        "# Geometry-blind-response discrete theorem report",
        "",
        "> **Evidence tier:** internal synthetic/analytic benchmark-C fixture. "
        "This is not external evidence, a preregistration, an untouched holdout, "
        "transported charge, or a physical-pump validation.",
        "",
        '> **Terminology:** the experiment directory\'s "independent response" means only '
        "that response is calculated without geometry/orientation inputs. It is not "
        "independent empirical validation.",
        "",
        f"**Scoped outcome:** `{summary['status'].upper()}` for the explicit fixed-tick theorem.  ",
        "**Central empirical/external CWT claim:** `PROOF INCOMPLETE`.",
        "",
        "The `discrete_cycle_sum_surrogate` and numerical acceptance thresholds were selected "
        "after an exploratory center-`(0, 0)` square refinement probe. All configurations here "
        "are discovery/analytic fixtures. The legacy mean `response` is unchanged.",
        "",
        "## Fixed semantics",
        "",
        "`dt=1`; `phase_relaxation=0.35` per current tick. Increasing steps lengthens and "
        "slows the cycle. `Q=sum(q_t)` has circulation-current-tick units. The explicitly "
        "duplicated closing endpoint is processed.",
        "",
        "The response calculator receives branch states/path, relaxation, and current gain only. "
        "Signed area, orientation metadata, curvature, and Wilson flux are computed separately "
        "afterward.",
        "",
        "## Numerical result",
        "",
        "| Quantity | Value |",
        "|---|---:|",
        f"| `F_R` at `(0,0)` | {metrics['response_curvature_center']:.12g} |",
        f"| `Omega` at `(0,0)` | {metrics['projective_curvature_center']:.12g} |",
        "| algebraic local two-form quotient `F_R/Omega` | "
        f"{metrics['local_two_form_quotient_center']:.12g} |",
        f"| legacy mean log-slope | {metrics['legacy_mean_log_slope']:.9g} |",
        f"| summed tangent-remainder log-slope | {metrics['summed_tangent_remainder_log_slope']:.9g} |",
        f"| finest `Q_anti/A` relative error | {metrics['finest_response_density_relative_error']:.9g} |",
        f"| finest `Phi_anti/A` relative error | {metrics['finest_flux_density_relative_error']:.9g} |",
        "| max finite-loop/local quotient consistency error | "
        f"{metrics['max_local_quotient_consistency_relative_error']:.9g} |",
        f"| local two-form quotient spread | {metrics['local_two_form_quotient_spread']:.9g} |",
        f"| max exact-null `|q_t|` | {metrics['max_exact_null_q_sample']:.9g} |",
        f"| finest `|Q_even/Q_anti|` | {metrics['orientation_even_fraction']:.9g} |",
        "",
        "In a 2D parameter chart, any two nonzero 2-forms are pointwise proportional. Thus "
        "`F_R/Omega` versus `Q_anti/Phi_anti` is only an algebraic quotient/implementation-"
        "consistency check and has no independent CGT-predictive content. The quotient also "
        "varies across centers, so it is not one common or universal coefficient.",
        "",
        "## Deterministic gates",
        "",
        "The protocol's 12 compound acceptance clauses map to the 16 executable gates below.",
        "",
        "| Gate | Status | Requirement |",
        "|---|---|---|",
    ]
    for gate in summary["gates"]:
        lines.append(f"| `{gate['name']}` | **{gate['status'].upper()}** | {gate['requirement']} |")
    lines.extend(
        [
            "",
            "No seeds, replicate inflation, confidence intervals, or pseudo-statistical claims are "
            "used. See [`PROTOCOL_LOCK.md`](../PROTOCOL_LOCK.md), `records.json`, `summary.json`, "
            "and `PROVENANCE.json` for formulas, raw deterministic records, gates, tracked source "
            "hashes, and canonical summary/records payload hashes.",
            "",
            "## External-data blocker",
            "",
            provenance["external_data_blocker"],
            "A future central-claim test still needs a frozen manifest/checksum, auditable raw "
            "paired loops, an independent response that never receives geometry/orientation, and "
            "a held-out analysis plan.",
            "",
        ]
    )
    return "\n".join(lines)


def _validate_locked_semantics(
    summary: dict[str, Any],
    records: list[dict[str, Any]],
    report: str,
) -> None:
    """Reject any change beyond the provenance-format packaging correction."""

    observed = {
        "config": _json_sha256(summary["config"]),
        "gates": _json_sha256(summary["gates"]),
        "metrics": _json_sha256(summary["metrics"]),
        "records": _json_sha256(records),
        "report_text": source_text_sha256(report.encode("utf-8")),
        "summary": _json_sha256(summary),
    }
    if observed != PRE_CORRECTION_SEMANTIC_SHA256:
        raise RuntimeError(
            "PACKAGING_CORRECTION_NUMERIC_OR_CLAIM_DELTA: "
            f"expected {PRE_CORRECTION_SEMANTIC_SHA256}, observed {observed}"
        )
    if summary["status"] != "pass":
        raise RuntimeError("PACKAGING_CORRECTION_DECISION_DELTA")


def verify_artifacts(output_dir: Path = ARTIFACTS_DIR) -> None:
    """Verify the corrected theorem artifact DAG without executing the theorem."""

    provenance_path = output_dir / "PROVENANCE.json"
    ledger_path = output_dir / "PROVENANCE_CORRECTION.json"
    sidecar_path = output_dir / "PROVENANCE_CORRECTION.sha256"
    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    summary = json.loads((output_dir / "summary.json").read_text(encoding="utf-8"))
    records = json.loads((output_dir / "records.json").read_text(encoding="utf-8"))
    report = (output_dir / "REPORT.md").read_text(encoding="utf-8")
    if provenance["schema_version"] != 2:
        raise RuntimeError("corrected provenance schema must be version 2")
    if provenance["source_text_hash_domain_id"] != SOURCE_TEXT_HASH_DOMAIN:
        raise RuntimeError("source-text hash domain differs")
    source_manifest = provenance["source_text_dependencies"]
    verify_source_manifest(SIM_ROOT, source_manifest)
    if provenance["source_bundle_sha256"] != source_bundle_sha256(source_manifest):
        raise RuntimeError("source bundle digest differs")
    if provenance["source_bundle_payload"] != source_bundle_payload(source_manifest):
        raise RuntimeError("source bundle payload is not sorted and path-bound")
    if ledger["correction_status"] != "PACKAGING_CORRECTION_NO_NUMERIC_CHANGE":
        raise RuntimeError("correction ledger status differs")
    corrected_hashes = ledger["corrected"]["artifact_sha256_raw_bytes"]
    for name, expected in corrected_hashes.items():
        if _sha256(output_dir / name) != expected:
            raise RuntimeError(f"corrected artifact hash differs for {name}")
    sidecar_parts = sidecar_path.read_text(encoding="utf-8").split()
    if sidecar_parts != [_sha256(ledger_path), ledger_path.name]:
        raise RuntimeError("correction ledger sidecar differs")
    _validate_locked_semantics(summary, records, report)


def write_artifacts(
    summary: dict[str, Any],
    records: list[dict[str, Any]],
    output_dir: Path = ARTIFACTS_DIR,
) -> dict[str, Path]:
    """Write the strict protocol artifacts to one isolated directory."""

    output_dir.mkdir(parents=True, exist_ok=True)
    provenance = build_provenance(summary, records)
    report = render_report(summary, provenance)
    _validate_locked_semantics(summary, records, report)
    paths = {
        "provenance": output_dir / "PROVENANCE.json",
        "records": output_dir / "records.json",
        "summary": output_dir / "summary.json",
        "report": output_dir / "REPORT.md",
        "provenance_correction": output_dir / "PROVENANCE_CORRECTION.json",
        "provenance_correction_sidecar": output_dir / "PROVENANCE_CORRECTION.sha256",
    }
    _write_json(paths["provenance"], provenance)
    _write_json(paths["records"], records)
    _write_json(paths["summary"], summary)
    paths["report"].write_text(report, encoding="utf-8")
    corrected_artifact_sha256 = {
        path.name: _sha256(path)
        for path in (
            paths["provenance"],
            paths["records"],
            paths["summary"],
            paths["report"],
        )
    }
    ledger = build_correction_ledger(
        SIM_ROOT,
        provenance["source_text_dependencies"],
        corrected_artifact_sha256,
    )
    _write_json(paths["provenance_correction"], ledger)
    ledger_sha256 = _sha256(paths["provenance_correction"])
    paths["provenance_correction_sidecar"].write_bytes(
        f"{ledger_sha256}  {paths['provenance_correction'].name}\n".encode("ascii")
    )
    verify_artifacts(output_dir)
    return paths


@app.command()
def main() -> None:
    """Run the internal-synthetic geometry-blind-response protocol.

    Geometry-blind response is not independent empirical validation, external
    evidence, transported charge, or a physical-pump measurement.
    """

    summary, records = execute_protocol(DEFAULT_CONFIG)
    paths = write_artifacts(summary, records, output_dir=ARTIFACTS_DIR)
    typer.echo(
        f"{summary['status'].upper()}: fixed-tick benchmark theorem; "
        "central empirical/external claim remains PROOF INCOMPLETE."
    )
    for name, path in paths.items():
        typer.echo(f"{name}: {path}")
    if summary["status"] != "pass":
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
