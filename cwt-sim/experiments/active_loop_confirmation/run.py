"""Standalone metadata-only CLI for the active-loop design template."""

from __future__ import annotations

import sys
from pathlib import Path

import typer

EXPERIMENT_DIR = Path(__file__).resolve().parent
SIM_ROOT = EXPERIMENT_DIR.parents[1]

if str(SIM_ROOT) not in sys.path:
    sys.path.insert(0, str(SIM_ROOT))

from experiments.active_loop_confirmation.artifacts import (  # noqa: E402
    DEFAULT_TEMPLATE_PATH,
    load_template,
    validation_json,
    verify_template_artifacts,
    write_template_artifacts,
)
from experiments.active_loop_confirmation.template_model import validate_template  # noqa: E402

app = typer.Typer(
    add_completion=False,
    help=(
        "Validate or freeze the metadata-only active-loop design template. "
        "No substrate, raw-data, response, result, or confirmation execution is available."
    ),
)


@app.command()
def status() -> None:
    """Print current metadata status; blocked is an intentional nonzero state."""

    report = validate_template(load_template())
    typer.echo(validation_json(report))
    if not report.metadata_verified:
        raise typer.Exit(code=2)


@app.command("validate-template")
def validate_template_command(
    template: Path = typer.Option(
        DEFAULT_TEMPLATE_PATH,
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        resolve_path=True,
        help="Metadata template JSON only; payload paths are never followed.",
    ),
) -> None:
    """Validate metadata only and stop before any substrate/outcome adapter exists."""

    report = validate_template(load_template(template))
    typer.echo(validation_json(report))
    if not report.metadata_verified:
        raise typer.Exit(code=2)


@app.command("freeze-template")
def freeze_template_command() -> None:
    """Write a deterministic blocked design freeze, not a study lock or result."""

    paths = write_template_artifacts()
    typer.echo("BLOCKED_NO_SUBSTRATE: deterministic design-template artifacts written")
    for name, path in sorted(paths.items()):
        typer.echo(f"{name}: {path.relative_to(EXPERIMENT_DIR).as_posix()}")


@app.command("verify-template")
def verify_template_command() -> None:
    """Verify the LF/hash closure without loading or executing any outcome."""

    result = verify_template_artifacts()
    typer.echo(result["status"])
    typer.echo(f"artifacts={result['artifact_count']} sources={result['source_count']}")


if __name__ == "__main__":
    app()
