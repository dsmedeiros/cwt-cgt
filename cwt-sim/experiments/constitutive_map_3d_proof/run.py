"""Standalone Typer CLI for the 3D constitutive-map proof program."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import typer

EXPERIMENT_DIR = Path(__file__).resolve().parent
SIM_ROOT = EXPERIMENT_DIR.parents[1]
if str(SIM_ROOT) not in sys.path:
    sys.path.insert(0, str(SIM_ROOT))

from experiments.constitutive_map_3d_proof.artifacts import (  # noqa: E402
    ArtifactGenerationRefused,
    artifact_access_guard,
    require_semantic_pass,
    verify_artifacts,
    write_artifacts,
)
from experiments.constitutive_map_3d_proof.theorem import execute_program  # noqa: E402

app = typer.Typer(
    add_completion=False,
    help=(
        "Run or verify the internal analytic 3D constitutive-map proof. "
        "No empirical, physical, universal-CWT, or general alignment execution exists."
    ),
)


@app.command()
def status() -> None:
    """Recover guarded publication state, then print the analytic disposition."""

    with artifact_access_guard():
        summary, records = execute_program()
    try:
        require_semantic_pass(summary, records)
    except ArtifactGenerationRefused as exc:
        typer.echo(f"SEMANTIC_VALIDATION_FAILED: {exc}", err=True)
        raise typer.Exit(code=2) from exc
    typer.echo(
        json.dumps(
            {
                "disposition": summary["disposition"],
                "evidence_status": summary["evidence_status"],
                "relation_scope": summary["relation_scope"],
                "failed_gates": summary["failed_gates"],
                "case_dispositions": summary["case_dispositions"],
            },
            sort_keys=True,
        )
    )


@app.command("run")
def run_program() -> None:
    """Execute the proof and write only its deterministic isolated artifacts."""

    paths = write_artifacts()
    typer.echo("PASS_INTERNAL_ANALYTIC / NO_EMPIRICAL_EVIDENCE / " "MODEL_SPECIFIC_RELATIONS_ONLY")
    for name, path in sorted(paths.items()):
        typer.echo(f"{name}: {path.relative_to(EXPERIMENT_DIR).as_posix()}")


@app.command()
def verify() -> None:
    """Recompute and verify semantic, source, predecessor, and artifact closure."""

    result = verify_artifacts()
    typer.echo(f"{result['status']} / {result['evidence_status']} / {result['relation_scope']}")
    typer.echo(
        f"artifacts={result['artifact_count']} sources={result['source_count']} "
        f"clean_modules={result['clean_cli_local_module_count']} "
        f"predecessors={result['predecessor_count']}"
    )


if __name__ == "__main__":
    app()
