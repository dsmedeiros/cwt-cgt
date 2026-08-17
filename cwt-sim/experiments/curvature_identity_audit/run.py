"""Standalone Typer CLI for the curvature identity audit."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import typer

EXPERIMENT_DIR = Path(__file__).resolve().parent
SIM_ROOT = EXPERIMENT_DIR.parents[1]
if str(SIM_ROOT) not in sys.path:
    sys.path.insert(0, str(SIM_ROOT))

from experiments.curvature_identity_audit.artifacts import (  # noqa: E402
    ArtifactGenerationRefused,
    require_semantic_pass,
    verify_artifacts,
    write_artifacts,
)
from experiments.curvature_identity_audit.theorem import execute_program  # noqa: E402

app = typer.Typer(
    add_completion=False,
    help=(
        "Run or verify the internal analytic curvature-identity audit. "
        "No empirical, physical, universal-CWT, or alignment execution exists."
    ),
)


@app.command()
def status() -> None:
    """Print the fail-closed analytic disposition without writing artifacts."""

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
                "failed_gates": summary["failed_gates"],
                "case_dispositions": summary["case_dispositions"],
            },
            sort_keys=True,
        )
    )


@app.command("run")
def run_program() -> None:
    """Execute the audit and write only its deterministic isolated artifacts."""

    paths = write_artifacts()
    typer.echo("PASS_INTERNAL_ANALYTIC / NO_EMPIRICAL_EVIDENCE")
    for name, path in sorted(paths.items()):
        typer.echo(f"{name}: {path.relative_to(EXPERIMENT_DIR).as_posix()}")


@app.command()
def verify() -> None:
    """Recompute and verify the semantic, source, predecessor, and artifact closure."""

    result = verify_artifacts()
    typer.echo(f"{result['status']} / {result['evidence_status']}")
    typer.echo(
        f"artifacts={result['artifact_count']} sources={result['source_count']} "
        f"clean_modules={result['clean_cli_local_module_count']} predecessors={result['predecessor_count']}"
    )


if __name__ == "__main__":
    app()
