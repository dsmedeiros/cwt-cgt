"""Standalone source-only CLI; no response or publication command exists."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import typer

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from experiments.generator_tensor_prediction_protocol.theorem import (
        execute_program,
    )
else:
    from .theorem import execute_program

app = typer.Typer(add_completion=False, no_args_is_help=False)


@app.command()
def status() -> None:
    """Recompute and print the pre-response source status."""

    summary, _ = execute_program()
    typer.echo(json.dumps(summary, sort_keys=True, default=str))
    if summary["disposition"] != "PASS_INTERNAL_ANALYTIC":
        raise typer.Exit(code=1)


@app.command("verify-source")
def verify_source() -> None:
    """Fail unless all response-free source gates pass."""

    summary, _ = execute_program()
    if summary["disposition"] != "PASS_INTERNAL_ANALYTIC":
        typer.echo(f"REFUSED: {summary['failed_gates']}", err=True)
        raise typer.Exit(code=1)
    typer.echo(
        f"PASS {summary['passed_gate_count']}/{summary['gate_count']} "
        "response_accessed=false source_lock_present=false"
    )


if __name__ == "__main__":
    app()
