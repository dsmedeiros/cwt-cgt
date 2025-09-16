"""Command-line interface for running simulation loops."""

from __future__ import annotations

import json
from pathlib import Path
import numpy as np
import typer

import networkx as nx

from cwt.graph import factories
from cwt.graph.substrate import GraphSubstrate, build_substrate
from cwt.io.config import AppConfig, load_config
from cwt.io.placeholders import fabricate_record
from cwt.io.registry import save_run
from cwt.layers.state import LayersState
from cwt.orchestrator.param_path import ParameterPath
from cwt.orchestrator.scheduler import RunConfig, RunRecord, run_parameter_loop


def _build_substrate(app_config: AppConfig) -> GraphSubstrate:
    """Return a substrate matching the graph section of ``app_config``."""

    kind = app_config.graph.kind
    weight = float(app_config.graph.weights)
    delay = float(app_config.graph.delays)

    try:
        factory = getattr(factories, kind)
    except AttributeError as exc:  # pragma: no cover - defensive guard
        if kind.startswith("ring") and kind[4:].isdigit():
            size = int(kind[4:])
            if size <= 0:
                raise typer.BadParameter("Ring graphs must contain at least one node.") from exc
            G = nx.DiGraph()
            for node in range(size):
                nxt = (node + 1) % size
                G.add_edge(node, nxt, weight=weight, delay=delay)
            return build_substrate(G)
        raise typer.BadParameter(f"Unknown graph kind '{kind}'.") from exc

    try:
        return factory(weight=weight, delay=delay)
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
    for knob in params.knobs:
        center_attr = f"{knob}_center"
        extent_attr = f"{knob}_extent"
        centers[knob] = float(getattr(params, center_attr, 0.0))
        extents[knob] = float(getattr(params, extent_attr, 0.0))

    varying = sum(1 for value in extents.values() if abs(value) > 0.0)
    path_kind = "rectangle" if varying >= 2 else "line"

    return ParameterPath(
        kind=path_kind,
        center=centers,
        extents=extents,
        steps=max(int(params.steps), 1),
        corner_area_mode=bool(config.geometric_coupling.corner_area_mode),
    )


def _build_run_config(config: AppConfig) -> RunConfig:
    """Translate :class:`AppConfig` values into a :class:`RunConfig`."""

    geometry = config.geometry
    dynamics = config.dynamics
    coupling = config.geometric_coupling

    geometry_settings = {
        "sample_mode": geometry.sample_mode,
        "neighbor_steps": geometry.neighbor_steps,
    }

    return RunConfig(
        eta_q=dynamics.eta_q,
        zeta=dynamics.zeta,
        omega_scale=dynamics.omega_scale,
        s_min=geometry.s_min,
        smooth_window=geometry.smooth_window,
        compute_metric=geometry.compute_metric,
        compute_curvature=geometry.compute_curvature,
        adapt_levels=geometry.adapt_levels,
        ci_tol=geometry.ci_tol,
        alpha=coupling.alpha,
        beta=coupling.beta,
        geometry=geometry_settings,
        delta_frac=dict(geometry.delta_frac),
        xi_kind=dict(coupling.xi_kind),
        readout=config.readout.model_dump(),
        noise=config.noise.model_dump(),
    )


def _run_simulation(app_config: AppConfig, *, label: str) -> RunRecord:
    """Execute a small simulation loop and return the resulting record."""

    substrate = _build_substrate(app_config)
    init_state = _initial_layers_state(substrate)
    path = _build_parameter_path(app_config)
    run_config = _build_run_config(app_config)

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
