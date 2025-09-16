"""Command-line interface for sweeping parameter grids."""

from __future__ import annotations

import json
from pathlib import Path

import typer

from cwt.io.config import load_config
from cwt.io.placeholders import fabricate_record
from cwt.io.registry import save_run

app = typer.Typer(help="Generate a series of placeholder runs for a parameter grid.")


@app.command()
def main(
    config: Path = typer.Option(..., "--config", "-c", help="Path to the YAML configuration file."),
    out: Path | None = typer.Option(None, "--out", help="Output directory for run bundles."),
    limit: int | None = typer.Option(None, "--limit", help="Restrict the number of generated runs."),
) -> None:
    """Load ``config`` and persist multiple placeholder runs."""

    app_config = load_config(config)
    if out is not None:
        app_config = app_config.model_copy(update={"out_dir": str(out)})

    total = limit if limit is not None else max(app_config.params.steps, 1)
    run_ids: list[str] = []

    for step_index in range(total):
        record = fabricate_record(
            app_config,
            label=f"{config.stem}_{step_index}",
            seed=app_config.seed + step_index,
            step_index=step_index,
        )
        run_id = save_run(record, app_config.out_dir)
        run_ids.append(run_id)

    typer.echo(json.dumps({"runs": run_ids, "count": len(run_ids)}))


def entrypoint() -> None:
    app()


if __name__ == "__main__":
    entrypoint()
