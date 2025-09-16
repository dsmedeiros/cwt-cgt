"""Command-line interface for generating evaluation reports."""

from __future__ import annotations

import json
from pathlib import Path

import typer

app = typer.Typer(help="Summarise saved run bundles into a compact report.")


@app.command()
def main(
    runs: Path = typer.Argument(..., help="Directory containing saved run bundles."),
) -> None:
    """Aggregate the ``meta.json`` files under ``runs`` and print a JSON summary."""

    runs_dir = Path(runs)
    if not runs_dir.exists():
        raise typer.BadParameter(f"Directory '{runs_dir}' does not exist.")
    if not runs_dir.is_dir():
        raise typer.BadParameter(f"Path '{runs_dir}' is not a directory.")

    summary: list[dict[str, object]] = []
    for run_dir in sorted(p for p in runs_dir.iterdir() if p.is_dir()):
        meta_path = run_dir / "meta.json"
        if not meta_path.exists():
            continue
        with meta_path.open("r", encoding="utf8") as handle:
            data = json.load(handle)
        summary.append(
            {
                "run_id": data.get("run_id", run_dir.name),
                "steps": len(data.get("lambda_path", [])),
                "label": data.get("meta", {}).get("label"),
            }
        )

    typer.echo(json.dumps({"runs": summary, "count": len(summary)}))


def entrypoint() -> None:
    app()


if __name__ == "__main__":
    entrypoint()
