"""Standalone CLI for the shared-generator counting-curvature proof."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import typer

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from experiments.shared_generator_counting_curvature_proof.artifacts import (  # type: ignore[import-not-found]
        ArtifactGenerationRefused,
        ArtifactVerificationError,
        require_semantic_pass,
        verify_artifacts,
        write_artifacts,
    )
    from experiments.shared_generator_counting_curvature_proof.theorem import (  # type: ignore[import-not-found]
        execute_program,
    )
else:
    from .artifacts import (
        ArtifactGenerationRefused,
        ArtifactVerificationError,
        require_semantic_pass,
        verify_artifacts,
        write_artifacts,
    )
    from .theorem import execute_program

app = typer.Typer(add_completion=False, no_args_is_help=True)


def _emit(payload: object) -> None:
    typer.echo(json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True))


@app.command()
def run() -> None:
    """Execute exact gates and transactionally publish one complete generation."""

    try:
        summary, records = execute_program()
        require_semantic_pass(summary, records)
        paths = write_artifacts()
        _emit({"status": summary["disposition"], "artifacts": sorted(paths)})
    except (ArtifactGenerationRefused, ArtifactVerificationError, RuntimeError, ValueError) as exc:
        typer.echo(f"REFUSED: {exc}", err=True)
        raise typer.Exit(code=1) from exc


@app.command()
def status() -> None:
    """Recover guarded state and verify the exact on-disk generation."""

    try:
        _emit(verify_artifacts())
    except (ArtifactGenerationRefused, ArtifactVerificationError, RuntimeError, ValueError) as exc:
        typer.echo(f"REFUSED: {exc}", err=True)
        raise typer.Exit(code=1) from exc


@app.command()
def verify() -> None:
    """Verify semantic status and the exact on-disk five-file closure."""

    try:
        _emit(verify_artifacts())
    except (ArtifactGenerationRefused, ArtifactVerificationError, RuntimeError, ValueError) as exc:
        typer.echo(f"REFUSED: {exc}", err=True)
        raise typer.Exit(code=1) from exc


if __name__ == "__main__":
    app()
