"""Nearest-neighbor bond percolation on nonperiodic boxes [-L, L]^d."""

import hashlib
import json
from collections import deque
from dataclasses import dataclass
from itertools import product
from numbers import Integral

import numpy as np


@dataclass(frozen=True)
class Box:
    """Canonical lexicographic vertices and vertex-major, axis-major edges."""

    dimension: int
    radius: int
    vertices: np.ndarray
    edges: np.ndarray
    edge_axes: np.ndarray
    adjacency: tuple[tuple[tuple[int, int], ...], ...]
    origin: int
    shell_radii: np.ndarray


@dataclass(frozen=True)
class ShellCounts:
    """Raw counts of capped origin-cluster radius, without smoothing."""

    histogram: np.ndarray
    boundary_hits: int
    trials: int


def _integer(value: int, minimum: int, name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, Integral) or value < minimum:
        raise ValueError(f"{name} must be an integer >= {minimum}; got {value!r}")


def _box_domain(dimension: int, radius: int) -> None:
    _integer(dimension, 2, "dimension")
    if dimension not in (2, 3):
        raise ValueError("dimension must be 2 or 3")
    _integer(radius, 1, "radius")


def _probability(value: float) -> None:
    if not np.isfinite(value) or not 0 <= value <= 1:
        raise ValueError(f"probability must be finite and in [0, 1]; got {value!r}")


def build_box(dimension: int, radius: int) -> Box:
    """Build a box with adjacency entries (neighbor index, edge index)."""
    _box_domain(dimension, radius)
    vertices = np.asarray(list(product(range(-radius, radius + 1), repeat=dimension)))
    lookup = {tuple(vertex): index for index, vertex in enumerate(vertices)}
    edges, axes = [], []
    adjacency: list[list[tuple[int, int]]] = [[] for _ in vertices]
    for source, vertex in enumerate(vertices):
        for axis in range(dimension):
            if vertex[axis] == radius:
                continue
            neighbor = vertex.copy()
            neighbor[axis] += 1
            target = lookup[tuple(neighbor)]
            edge = len(edges)
            edges.append((source, target))
            axes.append(axis)
            adjacency[source].append((target, edge))
            adjacency[target].append((source, edge))
    return Box(
        dimension,
        radius,
        vertices,
        np.asarray(edges),
        np.asarray(axes),
        tuple(tuple(entries) for entries in adjacency),
        lookup[(0,) * dimension],
        np.max(np.abs(vertices), axis=1),
    )


def cluster_radius(box: Box, open_edges: np.ndarray) -> int:
    """Return the Chebyshev radius of the origin cluster, capped at L."""
    open_edges = np.asarray(open_edges)
    if open_edges.shape != (len(box.edges),) or open_edges.dtype != np.bool_:
        raise ValueError("open_edges must be a boolean array with one entry per box edge")
    visited, queue, maximum = {box.origin}, deque([box.origin]), 0
    while queue:
        vertex = queue.popleft()
        maximum = max(maximum, int(box.shell_radii[vertex]))
        if maximum == box.radius:
            return maximum
        for neighbor, edge in box.adjacency[vertex]:
            if open_edges[edge] and neighbor not in visited:
                visited.add(neighbor)
                queue.append(neighbor)
    return maximum


def draw_uniforms(box: Box, samples: int, seed: int) -> np.ndarray:
    """Pre-sample every edge using explicit PCG64, reusable across chart points."""
    _integer(samples, 1, "samples")
    _integer(seed, 0, "seed")
    return np.random.Generator(np.random.PCG64(seed)).random((samples, len(box.edges)))


def sample_shells(box: Box, u: float, v: float, uniforms: np.ndarray) -> ShellCounts:
    """Count radii with independent axis-0 bonds at u and all other bonds at v."""
    _probability(u)
    _probability(v)
    uniforms = np.asarray(uniforms)
    if uniforms.ndim != 2 or uniforms.shape[1] != len(box.edges) or len(uniforms) == 0:
        raise ValueError("uniforms must have shape (positive samples, number of box edges)")
    if not np.all(np.isfinite(uniforms)) or np.any((uniforms < 0) | (uniforms >= 1)):
        raise ValueError("uniforms must be finite values in [0, 1)")
    thresholds = np.where(box.edge_axes == 0, u, v)
    histogram = np.zeros(box.radius + 1, dtype=np.int64)
    for sample in uniforms:
        histogram[cluster_radius(box, sample < thresholds)] += 1
    return ShellCounts(histogram, int(histogram[-1]), len(uniforms))


def stable_seed(
    base_seed: int,
    dimension: int,
    radius: int,
    probability: float,
    stream: str,
    batch: int = 0,
) -> int:
    """Key a PCG64 seed by configuration instead of traversal order or Python hash."""
    _integer(base_seed, 0, "base_seed")
    _box_domain(dimension, radius)
    _probability(probability)
    _integer(batch, 0, "batch")
    if not isinstance(stream, str) or not stream:
        raise ValueError("stream must be a nonempty string")
    key = json.dumps(
        [int(base_seed), int(dimension), int(radius), float(probability).hex(), stream, int(batch)],
        separators=(",", ":"),
    ).encode("utf-8")
    return int.from_bytes(hashlib.sha256(key).digest(), "little")


def wilson95(hits: int, trials: int) -> tuple[float, float]:
    """Return a two-sided 95% Wilson score interval from unsmoothed binomial counts."""
    _integer(trials, 1, "trials")
    _integer(hits, 0, "hits")
    hits, trials = int(hits), int(trials)
    if hits > trials:
        raise ValueError("hits must not exceed trials")
    z = 1.959963984540054
    rate, adjustment = hits / trials, z * z / trials
    center = (rate + adjustment / 2) / (1 + adjustment)
    half = z * np.sqrt(rate * (1 - rate) / trials + z * z / (4 * trials * trials))
    half /= 1 + adjustment
    return max(0.0, float(center - half)), min(1.0, float(center + half))
