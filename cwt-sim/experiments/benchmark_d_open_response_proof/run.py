"""Standalone Typer CLI for the Benchmark D true-fixed response proof."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import typer

EXPERIMENT_DIR = Path(__file__).resolve().parent
SIM_ROOT = EXPERIMENT_DIR.parents[1]
if str(SIM_ROOT) not in sys.path:
    sys.path.insert(0, str(SIM_ROOT))

from experiments.benchmark_d_open_response_proof.artifacts import (  # noqa: E402
    verify_artifacts,
    write_artifacts,
)
from experiments.benchmark_d_open_response_proof.theorem import execute_program  # noqa: E402

app = typer.Typer(
    add_completion=False,
    help=(
        "Run or verify the internal synthetic Benchmark D true-fixed response proof. "
        "No empirical, external-data, physical-time, scheduler, or CGT-alignment execution exists."
    ),
)


@app.command()
def status() -> None:
    """Print the analytic disposition without writing artifacts."""

    summary, _records = execute_program()
    typer.echo(
        json.dumps(
            {
                "disposition": summary["disposition"],
                "evidence_status": summary["evidence_status"],
                "failed_gates": summary["failed_gates"],
            },
            sort_keys=True,
        )
    )
    if summary["failed_gates"]:
        raise typer.Exit(code=2)


@app.command("run")
def run_program() -> None:
    """Execute the deterministic authored proof harness and write isolated artifacts."""

    paths = write_artifacts()
    typer.echo("PASS_INTERNAL_ANALYTIC / NO_EMPIRICAL_EVIDENCE")
    for name, path in sorted(paths.items()):
        typer.echo(f"{name}: {path.relative_to(EXPERIMENT_DIR).as_posix()}")


@app.command()
def verify() -> None:
    """Recompute and verify the complete deterministic artifact closure."""

    result = verify_artifacts()
    typer.echo(f"{result['status']} / {result['evidence_status']}")
    typer.echo(f"artifacts={result['artifact_count']} sources={result['source_count']}")


if __name__ == "__main__":
    app()
