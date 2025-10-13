"""Common utilities shared across baseline experiments and scripts."""

from __future__ import annotations

import contextlib
import math
import random
import time
from itertools import product
from pathlib import Path
from typing import Callable, Iterator, Mapping, Sequence

import networkx as nx
import numpy as np

try:  # pragma: no cover - torch is optional
    import torch
except ModuleNotFoundError:  # pragma: no cover - torch is optional
    torch = None  # type: ignore[assignment]


def seed_everything(seed: int) -> None:
    """Seed random number generators for reproducibility."""

    random.seed(seed)
    np.random.seed(seed)
    if torch is not None:
        torch.manual_seed(seed)
        if torch.cuda.is_available():  # pragma: no cover - optional CUDA availability
            torch.cuda.manual_seed_all(seed)


def _build_ring3(n: int) -> nx.Graph:
    if n <= 0:
        raise ValueError("n must be positive for ring3 graphs")
    if n == 3:
        return nx.cycle_graph(3)
    return nx.cycle_graph(n)


def _build_erdos_renyi(n: int, p: float, *, seed: int | None, directed: bool) -> nx.Graph:
    if directed:
        return nx.erdos_renyi_graph(n, p, seed=seed, directed=True)
    return nx.erdos_renyi_graph(n, p, seed=seed)


def _build_random_regular(n: int, degree: int, *, seed: int | None) -> nx.Graph:
    if n * degree % 2 != 0:
        raise ValueError("n * degree must be even for random regular graphs")
    return nx.random_regular_graph(degree, n, seed=seed)


def _build_small_world(n: int, k: int, p: float, *, seed: int | None) -> nx.Graph:
    return nx.watts_strogatz_graph(n, k, p, seed=seed)


def _build_scale_free(n: int, *, seed: int | None) -> nx.Graph:
    G = nx.scale_free_graph(n, seed=seed)
    return nx.Graph(G)  # collapse multi-edges and directions


def _build_modular(communities: int, size: int, p_in: float, p_out: float, *, seed: int | None) -> nx.Graph:
    return nx.planted_partition_graph(communities, size, p_in, p_out, seed=seed)


def _build_lattice_2d(rows: int, cols: int) -> nx.Graph:
    return nx.grid_2d_graph(rows, cols)


_GRAPH_BUILDERS: dict[str, Callable[..., nx.Graph]] = {
    "ring3": _build_ring3,
    "erdos_renyi": _build_erdos_renyi,
    "random_regular": _build_random_regular,
    "small_world": _build_small_world,
    "scale_free": _build_scale_free,
    "modular": _build_modular,
    "lattice_2d": _build_lattice_2d,
}


def graph_factory(kind: str, *, seed: int | None = None, **kwargs: float | int | bool) -> nx.Graph:
    """Create a graph with sensible defaults for several common families."""

    try:
        builder = _GRAPH_BUILDERS[kind]
    except KeyError as exc:  # pragma: no cover - defensive
        raise ValueError(f"Unsupported graph kind: {kind}") from exc

    if kind == "ring3":
        n = int(kwargs.pop("n", 3))
        if kwargs:
            raise TypeError(f"Unexpected parameters for ring3: {sorted(kwargs)}")
        return builder(n)
    if kind == "erdos_renyi":
        n = int(kwargs.pop("n", 10))
        p = float(kwargs.pop("p", 0.2))
        directed = bool(kwargs.pop("directed", False))
        if kwargs:
            raise TypeError(f"Unexpected parameters for erdos_renyi: {sorted(kwargs)}")
        return builder(n, p, seed=seed, directed=directed)
    if kind == "random_regular":
        n = int(kwargs.pop("n", 10))
        degree = int(kwargs.pop("degree", 3))
        if kwargs:
            raise TypeError(f"Unexpected parameters for random_regular: {sorted(kwargs)}")
        return builder(n, degree, seed=seed)
    if kind == "small_world":
        n = int(kwargs.pop("n", 10))
        k = int(kwargs.pop("k", 4))
        p = float(kwargs.pop("p", 0.2))
        if kwargs:
            raise TypeError(f"Unexpected parameters for small_world: {sorted(kwargs)}")
        return builder(n, k, p, seed=seed)
    if kind == "scale_free":
        n = int(kwargs.pop("n", 10))
        if kwargs:
            raise TypeError(f"Unexpected parameters for scale_free: {sorted(kwargs)}")
        return builder(n, seed=seed)
    if kind == "modular":
        communities = int(kwargs.pop("communities", 2))
        size = int(kwargs.pop("size", 5))
        p_in = float(kwargs.pop("p_in", 0.5))
        p_out = float(kwargs.pop("p_out", 0.05))
        if kwargs:
            raise TypeError(f"Unexpected parameters for modular: {sorted(kwargs)}")
        return builder(communities, size, p_in, p_out, seed=seed)
    if kind == "lattice_2d":
        rows = int(kwargs.pop("rows", 3))
        cols = int(kwargs.pop("cols", 3))
        if kwargs:
            raise TypeError(f"Unexpected parameters for lattice_2d: {sorted(kwargs)}")
        return builder(rows, cols)
    raise AssertionError("Unhandled graph kind")  # pragma: no cover - safety net


def grid_points(
    ranges: Mapping[str, Sequence[float]],
    grid_size: Mapping[str, int],
    *,
    axes: Sequence[str] | None = None,
) -> dict[int, dict[str, float | int]]:
    """Generate a row-major enumeration of parameter grid values."""

    if axes is None:
        axes = list(ranges.keys())
    values = {}
    for axis in axes:
        if axis not in ranges:
            raise KeyError(f"Missing range specification for axis '{axis}'")
        if axis not in grid_size:
            raise KeyError(f"Missing grid size for axis '{axis}'")
        range_values = list(ranges[axis])
        if len(range_values) != 2:
            raise ValueError(
                f"Range specification for axis '{axis}' must contain exactly two values"
            )
        start, stop = (float(range_values[0]), float(range_values[1]))
        count = int(grid_size[axis])
        if count <= 0:
            raise ValueError(f"Grid size must be positive for axis '{axis}'")
        values[axis] = np.linspace(start, stop, count)

    result: dict[int, dict[str, float | int]] = {}
    index = 0
    index_ranges = [range(len(values[axis])) for axis in axes]
    for coordinate in product(*index_ranges):
        entry: dict[str, float | int] = {}
        for axis, axis_index in zip(axes, coordinate):
            entry[f"{axis}_index"] = axis_index
            entry[axis] = float(values[axis][axis_index])
        result[index] = entry
        index += 1
    return result


class Accumulator:
    """Collect tabular experiment metrics for later export."""

    def __init__(self) -> None:
        self._records: list[dict[str, object]] = []

    def add(self, record: Mapping[str, object] | None = None, **kwargs: object) -> None:
        """Append a record to the accumulator."""

        payload: dict[str, object] = {}
        if record is not None:
            payload.update(dict(record))
        payload.update(kwargs)
        self._records.append(payload)

    def to_dataframe(self):
        import pandas as pd

        return pd.DataFrame(self._records)

    def to_csv(self, path: str | Path, **kwargs: object) -> Path:
        dataframe = self.to_dataframe()
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        dataframe.to_csv(output_path, index=False, **kwargs)
        return output_path


@contextlib.contextmanager
def time_budget_guard(
    seconds: float,
    *,
    on_exceed: Callable[[float], None] | None = None,
    raise_on_exceed: bool = True,
) -> Iterator[None]:
    """Context manager that checks a block does not exceed a time budget."""

    start = time.perf_counter()
    try:
        yield
    finally:
        elapsed = time.perf_counter() - start
        if elapsed > seconds:
            if on_exceed is not None:
                on_exceed(elapsed)
            if raise_on_exceed:
                raise TimeoutError(
                    f"Operation exceeded time budget: {elapsed:.3f}s > {seconds:.3f}s"
                )


def finite_difference_gradient(
    func: Callable[[np.ndarray], float],
    point: Sequence[float],
    *,
    step: float = 1e-5,
    method: str = "central",
) -> np.ndarray:
    """Approximate the gradient of ``func`` at ``point`` using finite differences."""

    point_arr = np.asarray(point, dtype=float)
    gradient = np.zeros_like(point_arr)
    for index in range(point_arr.size):
        perturb = np.zeros_like(point_arr)
        perturb[index] = step
        if method == "central":
            f_plus = func(point_arr + perturb)
            f_minus = func(point_arr - perturb)
            gradient[index] = (f_plus - f_minus) / (2 * step)
        elif method == "forward":
            f_base = func(point_arr)
            f_plus = func(point_arr + perturb)
            gradient[index] = (f_plus - f_base) / step
        elif method == "backward":
            f_base = func(point_arr)
            f_minus = func(point_arr - perturb)
            gradient[index] = (f_base - f_minus) / step
        else:  # pragma: no cover - defensive branch
            raise ValueError(f"Unsupported finite difference method: {method}")
    return gradient


def pearson_correlation(x: Sequence[float], y: Sequence[float]) -> float:
    """Compute the Pearson correlation coefficient between two sequences."""

    x_arr = np.asarray(x, dtype=float)
    y_arr = np.asarray(y, dtype=float)
    if x_arr.size != y_arr.size:
        raise ValueError("x and y must have the same number of elements")
    if x_arr.size == 0:
        raise ValueError("x and y must be non-empty")
    x_centered = x_arr - x_arr.mean()
    y_centered = y_arr - y_arr.mean()
    denominator = np.linalg.norm(x_centered) * np.linalg.norm(y_centered)
    if denominator == 0:
        return math.nan
    return float(np.dot(x_centered, y_centered) / denominator)


def spearman_correlation(x: Sequence[float], y: Sequence[float]) -> float:
    """Compute the Spearman rank correlation coefficient between two sequences."""

    x_arr = np.asarray(x, dtype=float)
    y_arr = np.asarray(y, dtype=float)
    if x_arr.size != y_arr.size:
        raise ValueError("x and y must have the same number of elements")
    if x_arr.size == 0:
        raise ValueError("x and y must be non-empty")

    x_ranks = _rankdata(x_arr)
    y_ranks = _rankdata(y_arr)
    return pearson_correlation(x_ranks, y_ranks)


def _rankdata(values: np.ndarray) -> np.ndarray:
    sorter = np.argsort(values, kind="mergesort")
    ranks = np.empty_like(values, dtype=float)
    sorted_values = values[sorter]

    start = 0
    n = len(values)
    while start < n:
        end = start + 1
        while end < n and sorted_values[end] == sorted_values[start]:
            end += 1
        average_rank = 0.5 * ((start + 1) + end)
        ranks[sorter[start:end]] = average_rank
        start = end

    return ranks
