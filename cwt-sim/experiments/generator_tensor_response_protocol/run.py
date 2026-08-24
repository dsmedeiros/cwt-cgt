"""Standalone source-only CLI for the sealed response-adapter protocol."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import typer

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


def _execute_source_program() -> tuple[dict[str, object], dict[str, object]]:
    from experiments.generator_tensor_response_protocol.theorem import execute_program

    return execute_program()


app = typer.Typer(add_completion=False, no_args_is_help=False)

ACCESS_REFUSAL = "REFUSED: exact adapter SOURCE_LOCK and separately reviewed phase authorization are absent"


@app.command()
def status() -> None:
    """Print response-free source status."""

    summary, _ = _execute_source_program()
    typer.echo(json.dumps(summary, sort_keys=True))
    if summary["disposition"] != "PASS_INTERNAL_ANALYTIC":
        raise typer.Exit(code=1)


@app.command("verify-source")
def verify_source() -> None:
    """Verify response-free source gates only."""

    summary, _ = _execute_source_program()
    if summary["disposition"] != "PASS_INTERNAL_ANALYTIC":
        typer.echo(f"REFUSED: {summary['failed_gates']}", err=True)
        raise typer.Exit(code=1)
    typer.echo(
        f"PASS {summary['passed_gate_count']}/{summary['gate_count']} "
        "response_accessed=false "
        f"adapter_source_lock_present={str(summary['adapter_source_lock_present']).lower()}"
    )


def _refuse_access() -> None:
    typer.echo(ACCESS_REFUSAL, err=True)
    raise typer.Exit(code=1)


@app.command()
def calibrate() -> None:
    """Reserved future command; unavailable in the source-only phase."""

    _refuse_access()


@app.command()
def confirm() -> None:
    """Reserved future command; unavailable before a passing calibration."""

    _refuse_access()


@app.command()
def heldout() -> None:
    """Reserved future command; unavailable before atomic V1/V2 PASS."""

    _refuse_access()


@app.command("phase-child", hidden=True)
def phase_child(authority_commit_oid: str) -> None:
    """Execute one externally authorized fixed phase in a fresh isolated process."""

    try:
        from experiments.generator_tensor_response_protocol.broker import (
            _execute_reviewed_phase_child,
        )

        summary = _execute_reviewed_phase_child(authority_commit_oid)
    except BaseException:
        typer.echo("REFUSED: authoritative whole-phase execution failed closed", err=True)
        raise typer.Exit(code=1) from None
    typer.echo(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    app()
