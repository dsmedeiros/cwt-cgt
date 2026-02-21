"""Command-line interface for running simulation loops."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping
import numpy as np
import typer

import networkx as nx

from cwt.graph import factories
from cwt.graph.substrate import GraphSubstrate, build_substrate
from cwt.io.config import AppConfig, load_config, to_run_config
from cwt.io.placeholders import fabricate_record
from cwt.io.registry import save_run
from cwt.layers.state import LayersState
from cwt.orchestrator.param_path import ParameterPath
from cwt.orchestrator.scheduler import RunRecord, run_parameter_loop


def _build_substrate(app_config: AppConfig) -> GraphSubstrate:
    """Return a substrate matching the graph section of ``app_config``."""

    kind = app_config.graph.kind
    weight = float(app_config.graph.weights)
    delay_spec = app_config.graph.delays
    if isinstance(delay_spec, (list, tuple)):
        delay_values = [float(value) for value in delay_spec]
    else:
        delay_values = float(delay_spec)

    try:
        factory = getattr(factories, kind)
    except AttributeError as exc:  # pragma: no cover - defensive guard
        if kind.startswith("ring") and kind[4:].isdigit():
            size = int(kind[4:])
            if size <= 0:
                raise typer.BadParameter("Ring graphs must contain at least one node.") from exc
            G = nx.DiGraph()
            if isinstance(delay_values, list):
                base_delay = delay_values[0]
            else:
                base_delay = delay_values
            for node in range(size):
                nxt = (node + 1) % size
                G.add_edge(node, nxt, weight=weight, delay=float(base_delay))
            return build_substrate(G)
        raise typer.BadParameter(f"Unknown graph kind '{kind}'.") from exc

    kwargs = {"weight": weight}
    if isinstance(delay_values, list):
        kwargs["delays"] = delay_values
    else:
        kwargs["delay"] = delay_values

    try:
        return factory(**kwargs)
    except TypeError as exc:  # pragma: no cover - defensive guard
        raise typer.BadParameter(f"Graph factory '{kind}' does not accept the provided arguments.") from exc


def _initial_layers_state(substrate: GraphSubstrate) -> LayersState:
    """Construct a uniform initial state for the supplied substrate."""

    N = substrate.N
    if N <= 0:
        return LayersState(pQ=np.zeros(0, dtype=float), theta=np.zeros(0, dtype=float))
    probs = np.full(N, 1.0 / N, dtype=float)
    phases = np.zeros(N, dtype=float)
    return LayersState(pQ=probs, theta=phases)


def _build_parameter_path(config: AppConfig) -> ParameterPath:
    """Create a :class:`ParameterPath` from ``config``."""

    params = config.params
    centers: dict[str, float] = {}
    extents: dict[str, float] = {}
    extras = getattr(params, "model_extra", {}) or {}
    for knob in params.knobs:
        center_attr = f"{knob}_center"
        extent_attr = f"{knob}_extent"
        center_val: float | None = None
        extent_val: float | None = None

        knob_payload = extras.get(knob)
        if isinstance(knob_payload, Mapping):
            if "center" in knob_payload:
                try:
                    center_val = float(knob_payload["center"])
                except (TypeError, ValueError):
                    center_val = None
            if "extent" in knob_payload:
                try:
                    extent_val = float(knob_payload["extent"])
                except (TypeError, ValueError):
                    extent_val = None

        if center_val is None and hasattr(params, center_attr):
            center_val = float(getattr(params, center_attr, 0.0))
        if extent_val is None and hasattr(params, extent_attr):
            extent_val = float(getattr(params, extent_attr, 0.0))

        centers[knob] = float(center_val if center_val is not None else 0.0)
        extents[knob] = float(extent_val if extent_val is not None else 0.0)

    varying = sum(1 for value in extents.values() if abs(value) > 0.0)
    path_kind = "rectangle" if varying >= 2 else "line"

    axis_candidates: list[str] = []
    for knob in params.knobs:
        if knob not in axis_candidates and knob in centers:
            axis_candidates.append(knob)
    for knob in centers:
        if knob not in axis_candidates:
            axis_candidates.append(knob)
    if len(axis_candidates) >= 2:
        axes = (axis_candidates[0], axis_candidates[1])
    elif axis_candidates:
        axes = (axis_candidates[0], axis_candidates[0])
    else:
        axes = ("rho", "tau")

    return ParameterPath(
        kind=path_kind,
        center=centers,
        extents=extents,
        steps=max(int(params.steps), 1),
        corner_area_mode=bool(config.geometric_coupling.corner_area_mode),
        axes=axes,
    )


def _run_simulation(app_config: AppConfig, *, label: str) -> RunRecord:
    """Execute a small simulation loop and return the resulting record."""

    substrate = _build_substrate(app_config)
    init_state = _initial_layers_state(substrate)
    path = _build_parameter_path(app_config)
    run_config = to_run_config(app_config)

    record = run_parameter_loop(substrate, init_state, path, run_config, seed=app_config.seed)
    record.meta = {
        **record.meta,
        "label": label,
        "app_config": app_config.model_dump(mode="json"),
    }
    return record


app = typer.Typer(help="Validate configuration files and run short CGT simulations.")


@app.command()
def main(
    config: Path = typer.Option(..., "--config", "-c", help="Path to the YAML configuration file."),
    out: Path | None = typer.Option(None, "--out", help="Output directory for run bundles."),
    seed: int | None = typer.Option(None, "--seed", help="Override the configuration seed."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Validate configuration without writing outputs."),
    simulate: bool = typer.Option(
        True,
        "--simulate/--fabricate",
        help="Run a short simulation (default) or emit a placeholder record.",
    ),
) -> None:
    """Load ``config`` and persist either a simulation run or a placeholder bundle."""

    app_config = load_config(config)
    if seed is not None:
        app_config = app_config.model_copy(update={"seed": seed})
    if out is not None:
        app_config = app_config.model_copy(update={"out_dir": str(out)})

    if dry_run:
        typer.echo(app_config.model_dump_json(indent=2, sort_keys=True))
        raise typer.Exit(code=0)

    if simulate:
        record = _run_simulation(app_config, label=config.stem)
    else:
        record = fabricate_record(app_config, label=config.stem, seed=app_config.seed)
    run_id = save_run(record, app_config.out_dir)
    typer.echo(json.dumps({"run_id": run_id, "out_dir": str(Path(app_config.out_dir) / run_id)}))


def entrypoint() -> None:
    app()


if __name__ == "__main__":
    entrypoint()
