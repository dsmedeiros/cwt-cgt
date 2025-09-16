"""Command-line interface for running simulation loops."""

from __future__ import annotations

import json
from pathlib import Path

import typer

from cwt.io.config import load_config
from cwt.io.placeholders import fabricate_record
from cwt.io.registry import save_run

app = typer.Typer(help="Validate configuration files and persist dummy run records.")


@app.command()
def main(
    config: Path = typer.Option(
        ..., "--config", "-c", help="Path to the YAML configuration file."
    ),
    out: Path | None = typer.Option(
        None, "--out", help="Output directory for run bundles."
    ),
    seed: int | None = typer.Option(
        None, "--seed", help="Override the configuration seed."
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Validate configuration without writing outputs."
    ),
) -> None:
    """Load ``config`` and optionally persist a placeholder run record."""

    app_config = load_config(config)
    if seed is not None:
        app_config = app_config.model_copy(update={"seed": seed})
    if out is not None:
        app_config = app_config.model_copy(update={"out_dir": str(out)})

    if dry_run:
        typer.echo(app_config.model_dump_json(indent=2, sort_keys=True))
        raise typer.Exit(code=0)

    record = fabricate_record(app_config, label=config.stem, seed=app_config.seed)
    run_id = save_run(record, app_config.out_dir)
    typer.echo(
        json.dumps(
            {"run_id": run_id, "out_dir": str(Path(app_config.out_dir) / run_id)}
        )
    )


def entrypoint() -> None:
    app()


if __name__ == "__main__":
    entrypoint()
