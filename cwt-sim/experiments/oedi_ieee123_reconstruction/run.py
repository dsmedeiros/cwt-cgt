"""Standalone provenance-locked OEDI IEEE123 reconstruction and protocol CLI."""

from __future__ import annotations

import importlib.metadata
import json
import platform
import sys
from pathlib import Path
from typing import Any

import networkx as nx
import numpy as np
import scipy
import typer

EXPERIMENT_DIR = Path(__file__).resolve().parent
SIM_ROOT = EXPERIMENT_DIR.parents[1]
ARTIFACTS_DIR = EXPERIMENT_DIR / "artifacts"

if str(SIM_ROOT) not in sys.path:
    sys.path.insert(0, str(SIM_ROOT))

from experiments.oedi_ieee123_reconstruction.prospective import (  # noqa: E402
    PROTOCOL_PATH,
    _source_code_hashes,
    prepare_prospective,
)
from experiments.oedi_ieee123_reconstruction.prospective_confirm import (  # noqa: E402
    execute_confirmation,
)
from experiments.oedi_ieee123_reconstruction.retrospective import (  # noqa: E402
    execute_retrospective,
)
from experiments.oedi_ieee123_reconstruction.source import (  # noqa: E402
    EXPERIMENT_DIR,
    PINNED_COMMIT,
    UPSTREAM_MANIFEST_PATH,
    SourceIntegrityError,
    acquire_pinned_source,
    canonical_json_sha256,
    load_upstream_manifest,
    sha256_file,
)

app = typer.Typer(
    add_completion=False,
    help=(
        "Reconstruct the post-hoc OEDI IEEE123 first-contact vector and prepare a separate "
        "digest-locked passive association protocol. Passing reconstruction restores no "
        "historical provenance and supplies no CGT evidence."
    ),
)


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(
        json.dumps(payload, allow_nan=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _artifact_provenance(
    *,
    mode: str,
    summary: dict[str, Any],
    records: list[dict[str, Any]],
    source_verification: dict[str, Any],
) -> dict[str, Any]:
    source_hashes = _source_code_hashes()
    return {
        "schema_version": 1,
        "experiment_id": "oedi_ieee123_reconstruction",
        "mode": mode,
        "dataset_title": "Sample IEEE123 Bus system for OEDI SI",
        "dataset_doi": "10.25984/2228282",
        "dataset_landing_page": "https://data.openei.org/submissions/5773",
        "dataset_classification": (
            "profiles packaged with an external public test-system dataset; measurement "
            "provenance unspecified"
        ),
        "pinned_upstream_commit": PINNED_COMMIT,
        "source_verification": source_verification,
        "source_access_roles": {
            "catalogued_verified": ("bytes/OID/size verified; content does not affect the named metric"),
            "catalogued_verified_context_only": (
                "bytes/OID/size verified as source context; not parsed or metric-affecting"
            ),
            "parsed_metadata": "active metadata parsed; no numeric profile execution implied",
            "numerically_executed_retrospective": (
                "numeric values contribute to the post-hoc retrospective vector"
            ),
            "metric_affecting": "field on each pinned-file record, not inferred from closure",
        },
        "summary_canonical_json_sha256": canonical_json_sha256(summary),
        "records_canonical_json_sha256": canonical_json_sha256(records),
        "canonical_json_encoding": ("UTF-8, allow_nan=false, sort_keys=true, separators=(',', ':')"),
        "source_code_hashes_sha256": source_hashes,
        "source_code_bundle_sha256": canonical_json_sha256(source_hashes),
        "upstream_manifest_sha256": sha256_file(UPSTREAM_MANIFEST_PATH),
        "protocol_sha256": sha256_file(PROTOCOL_PATH),
        "python_version": platform.python_version(),
        "numpy_version": np.__version__,
        "scipy_version": scipy.__version__,
        "networkx_version": nx.__version__,
        "typer_version": importlib.metadata.version("typer"),
        "not_historical_provenance_proof": True,
        "not_cgt_validation": True,
    }


def _write_bundle(
    output_dir: Path,
    *,
    mode: str,
    summary: dict[str, Any],
    records: list[dict[str, Any]],
    report: str,
    source_verification: dict[str, Any],
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    provenance = _artifact_provenance(
        mode=mode,
        summary=summary,
        records=records,
        source_verification=source_verification,
    )
    paths = {
        "summary": output_dir / "summary.json",
        "records": output_dir / "records.json",
        "provenance": output_dir / "PROVENANCE.json",
        "report": output_dir / "REPORT.md",
    }
    _write_json(paths["summary"], summary)
    _write_json(paths["records"], records)
    _write_json(paths["provenance"], provenance)
    paths["report"].write_text(report, encoding="utf-8")
    checksum_path = output_dir / "CHECKSUMS.json"
    _write_json(
        checksum_path,
        {
            "schema_version": 1,
            "algorithm": "sha256",
            "acyclic_detached_manifest": True,
            "files": {
                path.name: sha256_file(path)
                for path in (
                    paths["summary"],
                    paths["records"],
                    paths["provenance"],
                    paths["report"],
                )
            },
        },
    )
    paths["checksums"] = checksum_path
    return paths


def _retrospective_report(summary: dict[str, Any]) -> str:
    historical = summary["historical_parser_metrics"]
    active = summary["active_only_diagnostic"]
    corrected = summary["corrected_physical_graph"]
    corrected_sensor = corrected["sensor_diagnostics_energized_graph"]
    lines = [
        "# OEDI IEEE123 retrospective reconstruction report",
        "",
        "> **Correction and scope:** exact retrospective reconstruction from a pinned official "
        "source consistent with the archived vector. This does not prove which revision/parser "
        "the 2026 run used, restore its historical provenance, or support CGT.",
        "",
        "> Dataset class: profiles packaged with an external public test-system dataset; "
        "measurement provenance unspecified; field-observation provenance is not established.",
        "",
        f"**Reconstruction status:** `{summary['status'].upper()}`.  ",
        "**Theory support:** `NONE`.",
        "",
        "## Exact archived-vector reconstruction",
        "",
        "| Quantity | Reconstructed value |",
        "|---|---:|",
        f"| historical graph nodes after Line endpoints | {historical['oedi_graph_nodes']} |",
        f"| Line edges including Sw7/Sw8 | {historical['oedi_graph_edges']} |",
        f"| Unique sensor buses | {historical['oedi_sensor_nodes']} |",
        f"| finite mean nearest-sensor hops | {historical['oedi_sensor_coverage_mean_hops']:.15g} |",
        f"| full-graph sensor degree mean | {historical['sensor_degree_mean']:.15g} |",
        f"| full-graph nonsensor degree mean | {historical['nonsensor_degree_mean']:.15g} |",
        f"| full-graph sensor betweenness mean | {historical['sensor_betweenness_mean']:.15g} |",
        f"| full-graph nonsensor betweenness mean | {historical['nonsensor_betweenness_mean']:.15g} |",
        f"| five-profile dependent pair Spearman | {historical['distance_corr_spearman']:.15g} |",
        f"| five-profile dependent pair Pearson | {historical['distance_corr_pearson']:.15g} |",
        "| dimensionless PV>=0.2 shape-ratio alpha | "
        f"{historical['pv_load_midday_sign_boundary_alpha']:.15g} |",
        "",
        "## Parser defect and corrected interpretation",
        "",
        "Buscoords contributes 212 unique labels (82 `s*` plot/device labels plus 130 physical "
        "bus labels); the two Line endpoints `300_OPEN` and `94_OPEN` raise the historical "
        "graph to 214 nodes. "
        f"The historical parser creates **{historical['isolate_count']} isolates** and reports "
        f"finite sensor distance for only **{historical['sensor_reachable_node_count']}** of "
        "214 graph nodes. The isolates include 82 `s*` plot/device labels plus physical buses `150` "
        "and `610`, because transformer connectivity was omitted.",
        "",
        "Removing those isolates reverses the claimed structural targeting:",
        "",
        "| Active-only quantity | Sensor | Nonsensor |",
        "|---|---:|---:|",
        f"| mean degree | {active['sensor_degree_mean']:.15g} | {active['nonsensor_degree_mean']:.15g} |",
        f"| mean betweenness | {active['sensor_betweenness_mean']:.15g} | "
        f"{active['nonsensor_betweenness_mean']:.15g} |",
        "",
        f"The corrected primary graph has {corrected['node_count']} physical buses and "
        f"{corrected['edge_count']} unique edges, is connected={corrected['connected']}, and "
        f"has {corrected['isolate_count']} isolates. Sw7/Sw8 are excluded only under the "
        "dataset-specific `*_OPEN` pseudo-terminal convention; their DSS Line objects are "
        "executable. Including both stubs leaves every load-bus distance exactly unchanged.",
        "",
        "Corrected energized-graph sensor diagnostics also reverse the old interpretation: "
        f"all 130 buses are reachable (mean/median/max hops "
        f"{corrected_sensor['sensor_coverage_mean_hops']:.15g}/"
        f"{corrected_sensor['sensor_coverage_median_hops']:.15g}/"
        f"{corrected_sensor['sensor_coverage_max_hops']:.15g}); sensor versus nonsensor mean "
        f"degree is {corrected_sensor['sensor_degree_mean']:.15g} versus "
        f"{corrected_sensor['nonsensor_degree_mean']:.15g}, and normalized betweenness is "
        f"{corrected_sensor['sensor_betweenness_mean']:.15g} versus "
        f"{corrected_sensor['nonsensor_betweenness_mean']:.15g}.",
        "",
        "The ten pair records reuse only five selected profiles and are not ten independent "
        "observations. Alpha is a tautological dimensionless mean-zeroing ratio; it ignores "
        "S49a's 35 kW rating, PV49's 50 kVA/Pmpp rating, and the verified-but-unused "
        f"temperature series. Its PV>=0.2 mask contains exactly "
        f"{summary['alpha_interpretation']['pv_greater_equal_0_2_mask_count']:,} "
        "quarter-hours. It is not "
        "a physical net-power balance or response test.",
        "",
        "## Bottom line",
        "",
        "The old positive structural/sign-boundary interpretation is refuted. The only supported "
        "claim is reproducibility of the archived numeric vector from one pinned official source "
        "consistent with it. Historical provenance remains unproven. Chicago/Citi remain "
        "metadata-only; the central empirical/external CWT claim remains proof incomplete.",
        "",
    ]
    return "\n".join(lines)


def _prepare_report(prepared: dict[str, Any]) -> str:
    population = prepared["population"]
    adequacy = prepared["adequacy"]
    calibration_profile_count = sum(item["membership"] == "calibration" for item in prepared["loads"])
    return "\n".join(
        [
            "# OEDI IEEE123 prospective passive prepare report",
            "",
            "> **PREPARED, NOT EXECUTED. Confirmation remains digest-locked.** Byte hashing, "
            "row counting, Git-blob checks, and DSS metadata parsing occurred; no nonlegacy "
            "profile was numerically parsed and no nonlegacy outcome statistic was computed.",
            "",
            "This is a prospective-from-freeze-date analysis of retrospective pre-existing "
            "profiles in the same public test-system package, not prospective collection, an "
            "independent dataset, real-feeder evidence, or CGT validation.",
            "Field-observation provenance is not established.",
            "",
            f"- Pre-outcome adequacy: `{prepared['pre_outcome_status'].upper()}`",
            f"- Frozen digest: `{prepared['freeze_digest_sha256']}`",
            f"- Load/shape files: {population['load_count']}/{population['loadshape_catalog_count']}",
            f"- Active yearly mappings: {population['explicit_active_mapping_count']} (S48/S49c unmapped)",
            f"- Fresh mapped Wye: {population['fresh_mapped_wye_count']}",
            f"- Calibration buses/profiles: "
            f"{len(prepared['split']['calibration_buses'])}/{calibration_profile_count}",
            f"- Confirmation buses/profiles: {adequacy['confirmation_bus_count']}/"
            f"{adequacy['confirmation_profile_count']}",
            f"- Confirmation phases: {adequacy['confirmation_phase_counts']}",
            "",
            "The `T>=0.10` threshold was chosen after the five-profile exploration but before "
            "this frozen confirmation. Full-year quarter-hour medians are not trained or "
            "out-of-sample normalization. After unlock, every admitted calibration and "
            "confirmation file must pass strict numeric QC; one failure makes the result "
            "indeterminate. Exact runtime versions are frozen. Detached checksums bind the "
            "report, access plan, records, summary, and provenance.",
            "",
            "See the protocol and machine-readable access plan for the access boundary.",
            "",
            "Do not run `confirm` until root and adversarial review approve this exact digest.",
            "",
        ]
    )


@app.command()
def acquire(
    destination: Path = typer.Argument(..., help="New directory for canonical pinned checkout")
) -> None:
    """Clone the official repository with core.autocrlf=false and verify it."""

    acquire_pinned_source(destination)
    typer.echo(f"Pinned source acquired and verified at {destination.resolve()}")


@app.command()
def reconstruct(
    source_dir: Path = typer.Option(..., exists=True, file_okay=False, dir_okay=True),
) -> None:
    """Reconstruct only the known post-hoc five-profile historical vector."""

    summary, records = execute_retrospective(source_dir, require_git=True)
    paths = _write_bundle(
        ARTIFACTS_DIR / "retrospective",
        mode="retrospective_post_hoc_reconstruction",
        summary=summary,
        records=records,
        report=_retrospective_report(summary),
        source_verification=summary["source_verification"],
    )
    typer.echo(
        f"{summary['status'].upper()}: archived vector reconstructed; historical provenance "
        "unproven; theory support NONE."
    )
    for name, path in paths.items():
        typer.echo(f"{name}: {path}")
    if summary["status"] != "pass":
        raise typer.Exit(code=1)


@app.command()
def prepare(
    source_dir: Path = typer.Option(..., exists=True, file_okay=False, dir_okay=True),
) -> None:
    """Freeze metadata, source hashes, clustered membership, and access plan only."""

    prepared = prepare_prospective(source_dir, require_git=True)
    records = prepared["loads"]
    paths = _write_bundle(
        ARTIFACTS_DIR / "prospective_prepare",
        mode="metadata_only_prepare_confirmation_locked",
        summary=prepared,
        records=records,
        report=_prepare_report(prepared),
        source_verification=prepared["source_verification"],
    )
    access_path = ARTIFACTS_DIR / "prospective_prepare" / "ACCESS_PLAN.json"
    _write_json(access_path, prepared["access_plan"])
    paths["access_plan"] = access_path
    claim_paths = (
        paths["summary"],
        paths["records"],
        paths["provenance"],
        paths["report"],
        access_path,
    )
    claim_hashes = {path.name: sha256_file(path) for path in claim_paths}
    _write_json(
        paths["checksums"],
        {
            "schema_version": 1,
            "algorithm": "sha256",
            "acyclic_detached_manifest": True,
            "files": claim_hashes,
        },
    )
    freeze_lock_path = ARTIFACTS_DIR / "prospective_prepare" / "FREEZE_LOCK.json"
    _write_json(
        freeze_lock_path,
        {
            "schema_version": 1,
            "confirmation_status": "locked_pending_root_and_adversarial_approval",
            "freeze_digest_sha256": prepared["freeze_digest_sha256"],
            "prepared_summary_canonical_json_sha256": canonical_json_sha256(prepared),
            "prepared_summary_file_sha256": claim_hashes["summary.json"],
            "claim_artifact_sha256": claim_hashes,
            "confirmation_requires_separately_approved_freeze_lock_file_sha256": True,
            "self_hash_excluded_to_keep_manifest_acyclic": True,
        },
    )
    paths["freeze_lock"] = freeze_lock_path
    typer.echo(
        f"{prepared['pre_outcome_status'].upper()}: metadata-only freeze; confirmation LOCKED; "
        f"digest={prepared['freeze_digest_sha256']}"
    )
    for name, path in paths.items():
        typer.echo(f"{name}: {path}")
    typer.echo(f"freeze_lock_sha256: {sha256_file(freeze_lock_path)}")
    if prepared["pre_outcome_status"] != "pass":
        raise typer.Exit(code=1)


@app.command()
def confirm(
    source_dir: Path = typer.Option(..., exists=True, file_okay=False, dir_okay=True),
    prepared_summary: Path = typer.Option(
        ARTIFACTS_DIR / "prospective_prepare" / "summary.json",
        exists=True,
        dir_okay=False,
    ),
    freeze_lock: Path = typer.Option(
        ARTIFACTS_DIR / "prospective_prepare" / "FREEZE_LOCK.json",
        exists=True,
        dir_okay=False,
        help="Detached reviewer-approved lock for the exact prepared artifacts",
    ),
    approved_freeze_lock_sha256: str = typer.Option(
        ...,
        help="Exact SHA-256 of FREEZE_LOCK.json approved outside the prepared bundle",
    ),
    unlock_digest: str = typer.Option(..., help="Exact reviewer-approved frozen digest"),
    approval_acknowledgement: bool = typer.Option(
        False,
        "--root-and-adversarial-approved",
        help="Required explicit acknowledgement; never infer approval from a matching digest",
    ),
) -> None:
    """Run the frozen confirmation only after explicit reviewer unlock."""

    if not approval_acknowledgement:
        raise SourceIntegrityError(
            "Confirmation locked: root and adversarial approval acknowledgement is required"
        )
    if sha256_file(freeze_lock) != approved_freeze_lock_sha256:
        raise SourceIntegrityError(
            "Detached freeze-lock file differs from the independently approved SHA-256"
        )
    lock = json.loads(freeze_lock.read_text(encoding="utf-8"))
    if sha256_file(prepared_summary) != lock["prepared_summary_file_sha256"]:
        raise SourceIntegrityError("Prepared summary file differs from the detached freeze lock")
    for filename, expected_sha256 in lock["claim_artifact_sha256"].items():
        path = prepared_summary.parent / filename
        if not path.is_file() or sha256_file(path) != expected_sha256:
            raise SourceIntegrityError(f"Claim artifact {filename} differs from the detached freeze lock")
    prepared = json.loads(prepared_summary.read_text(encoding="utf-8"))
    if lock["freeze_digest_sha256"] != unlock_digest:
        raise SourceIntegrityError("Unlock digest differs from the detached freeze lock")
    if canonical_json_sha256(prepared) != lock["prepared_summary_canonical_json_sha256"]:
        raise SourceIntegrityError("Prepared canonical payload differs from the detached freeze lock")
    summary, records = execute_confirmation(
        source_dir,
        prepared,
        unlock_digest=unlock_digest,
        approved_prepared_payload_sha256=lock["prepared_summary_canonical_json_sha256"],
        require_git=True,
    )
    paths = _write_bundle(
        ARTIFACTS_DIR / "prospective_confirmation",
        mode="digest_unlocked_confirmation",
        summary=summary,
        records=records,
        report=(
            "# OEDI IEEE123 prospective passive confirmation\n\n"
            f"Status: **{summary['status'].upper()}**.\n\n"
            "Claim ceiling: prespecified within-package conditional bus-bundle random-label "
            "association only; not CGT, causal, real-feeder, or generalization evidence.\n"
        ),
        source_verification=prepared["source_verification"],
    )
    typer.echo(f"{summary['status'].upper()}: conditional within-package passive association")
    for name, path in paths.items():
        typer.echo(f"{name}: {path}")
    if summary["status"] != "pass":
        raise typer.Exit(code=1)


@app.command("manifest")
def show_manifest() -> None:
    """Print the tracked upstream manifest without accessing a source checkout."""

    typer.echo(json.dumps(load_upstream_manifest(), allow_nan=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    app()
