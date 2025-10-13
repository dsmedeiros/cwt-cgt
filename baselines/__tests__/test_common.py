"""Unit tests for baseline common utilities."""

from __future__ import annotations

import sys
from pathlib import Path

import networkx as nx
import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from baselines.common import graph_factory, grid_points, spearman_correlation  # noqa: E402


@pytest.mark.parametrize(
    "kind,kwargs,expected_nodes",
    [
        ("ring3", {}, 3),
        ("erdos_renyi", {"n": 5, "p": 0.5, "seed": 4}, 5),
        ("random_regular", {"n": 6, "degree": 2, "seed": 1}, 6),
        ("small_world", {"n": 8, "k": 2, "p": 0.1, "seed": 5}, 8),
        ("scale_free", {"n": 7, "seed": 3}, 7),
        ("modular", {"communities": 2, "size": 4, "p_in": 0.9, "p_out": 0.1, "seed": 2}, 8),
    ],
)
def test_graph_factory_supported_graphs(kind: str, kwargs: dict[str, int | float], expected_nodes: int) -> None:
    parameters = dict(kwargs)
    seed = parameters.pop("seed", 0)
    graph = graph_factory(kind, seed=seed, **parameters)
    assert isinstance(graph, nx.Graph)
    assert graph.number_of_nodes() == expected_nodes


def test_graph_factory_lattice_2d_shape() -> None:
    graph = graph_factory("lattice_2d", rows=2, cols=3)
    assert graph.number_of_nodes() == 6
    assert graph.has_edge((0, 0), (0, 1))
    assert graph.has_edge((0, 0), (1, 0))


def test_grid_points_row_major_iteration() -> None:
    ranges = {"x": (0.0, 1.0), "y": (10.0, 12.0)}
    sizes = {"x": 2, "y": 3}
    grid = grid_points(ranges, sizes, axes=["x", "y"])
    assert len(grid) == 6
    assert grid[0] == {"x": 0.0, "x_index": 0, "y": 10.0, "y_index": 0}
    assert grid[1]["y_index"] == 1
    assert grid[2]["y_index"] == 2
    assert grid[3]["x_index"] == 1
    assert grid[3]["y_index"] == 0


def test_grid_points_requires_complete_specification() -> None:
    ranges = {"x": (0.0, 1.0)}
    sizes = {"x": 2}
    grid = grid_points(ranges, sizes)
    assert len(grid) == 2
    assert grid[1]["x"] == pytest.approx(1.0)

    with pytest.raises(KeyError):
        grid_points({"x": (0.0, 1.0)}, {"y": 2})

    with pytest.raises(ValueError):
        grid_points({"x": (0.0, 1.0, 2.0)}, {"x": 2})

    with pytest.raises(ValueError):
        grid_points({"x": (0.0, 1.0)}, {"x": 0})


def test_spearman_correlation_with_ties() -> None:
    x = [1.0, 1.0, 2.0]
    y = [3.0, 4.0, 4.0]
    assert spearman_correlation(x, y) == pytest.approx(0.5)
