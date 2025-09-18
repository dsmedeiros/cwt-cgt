"""Tests for phi_flux aggregation without area fallback."""

from __future__ import annotations

import math

import networkx as nx
import numpy as np

from cwt.graph.substrate import build_substrate
from cwt.layers.state import LayersState
from cwt.orchestrator.param_path import ParameterPath
from cwt.orchestrator.scheduler import RunConfig, run_parameter_loop


def _make_substrate() -> tuple:
    graph = nx.DiGraph()
    graph.add_edge(0, 1, weight=1.0, delay=1.0)
    graph.add_edge(1, 2, weight=1.0, delay=1.0)
    graph.add_edge(2, 0, weight=1.0, delay=1.0)
    substrate = build_substrate(graph)
    init_state = LayersState(
        pQ=np.full(substrate.N, 1.0 / substrate.N),
        theta=np.zeros(substrate.N),
    )
    return substrate, init_state


def test_omega_tiles_include_tile_area() -> None:
    substrate, init_state = _make_substrate()
    path = ParameterPath(
        kind="rectangle",
        center={"rho": 0.5, "tau": 0.75},
        extents={"rho": 0.1, "tau": 0.15},
        steps=4,
    )
    config = RunConfig(
        compute_curvature=True,
        delta_frac={"rho": 0.05, "tau": 0.05},
        neighbor_settle_steps=1,
        readout={"final": True},
    )

    record = run_parameter_loop(substrate, init_state, path, config, seed=123)

    assert record.omega_tiles
    for tile in record.omega_tiles:
        assert "tile_area" in tile
        area_val = tile["tile_area"]
        assert isinstance(area_val, float)
        assert math.isfinite(area_val)
        assert area_val >= 0.0


def test_line_path_flux_is_zero_without_omega_tiles() -> None:
    substrate, init_state = _make_substrate()
    path = ParameterPath(
        kind="line",
        center={"rho": 0.4, "tau": 1.1},
        extents={"rho": 0.2, "tau": 0.0},
        steps=6,
    )
    config = RunConfig(
        compute_curvature=False,
        readout={"final": True},
    )

    record = run_parameter_loop(substrate, init_state, path, config, seed=321)

    assert record.readouts
    final_entry = record.readouts[-1]
    assert final_entry.get("step") == path.steps
    assert final_entry.get("phi_flux") == 0.0
