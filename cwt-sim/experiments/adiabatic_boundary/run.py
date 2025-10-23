"""Adiabatic boundary finder across loop step/extent combinations.

This experiment sweeps a rectangular loop in a user-selected control plane
with varying spatial extent and path discretisation.  For each configuration we
estimate the curvature flux ``Φ`` and a synthetic readout ``R_γ`` that obeys the
adiabatic scaling ``R ∝ Φ`` only while Fubini–Study steps remain small.  The
resulting map allows us to locate the boundary where ``κ₁ = R_γ / Φ`` deviates
from its calibrated value by more than 20%.

Artefacts written by the script:

* ``kappa_surface.csv`` – tabulated metrics per (extent, steps) sample.
* ``fs_histograms.json`` – discretised FS step distributions for each sample.
* ``boundary.csv`` – monotone boundary where ``κ₁`` leaves the adiabatic band.
"""

from __future__ import annotations

import argparse
import csv
import inspect
import json
import math
import numbers
import sys
from collections import deque
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

import networkx as nx
import numpy as np

import cwt.graph.factories as graph_factories
from cwt.geometry.curvature import curvature_tile
from cwt.geometry.fs_distance import fs_distance
from cwt.geometry.psi import build_psi
from cwt.graph.factories import from_edgelist, ring3_hetero
from cwt.graph.substrate import GraphSubstrate, build_substrate
from cwt.layers.state import LayersState, wrap_angles
from cwt.orchestrator.param_path import ParameterPath

PHASE1_DEFAULT_SEED = 7

# ---------------------------------------------------------------------------
# Data containers
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SampleResult:
    """Statistics recorded for a single (extent, steps) configuration."""

    extent: float
    steps: int
    flux: float
    area: float
    kappa: float
    readout: float
    fs_mean: float
    fs_p95: float
    fs_hist: list[float]


@dataclass(frozen=True)
class BoundaryPoint:
    """Represents the boundary location for a fixed extent."""

    extent: float
    boundary_steps: int | None
    reference_kappa: float
    boundary_kappa: float | None
    boundary_fs_p95: float | None


@dataclass(frozen=True)
class GraphFactoryOverride:
    """User-specified metadata for constructing a graph substrate."""

    identifier: str
    kwargs: Mapping[str, object] | None = None

    def as_kwargs(self) -> dict[str, object]:
        if self.kwargs is None:
            return {}
        if not isinstance(self.kwargs, Mapping):
            raise TypeError("GraphFactoryOverride.kwargs must be a mapping")
        return {str(key): value for key, value in self.kwargs.items()}


# ---------------------------------------------------------------------------
# Synthetic state helpers
# ---------------------------------------------------------------------------


def _synthetic_state(S: GraphSubstrate, knobs: Mapping[str, float]) -> LayersState:
    """Return a smooth, parameter-dependent state for the substrate."""

    N = S.N
    if N == 0:
        return LayersState(pQ=np.zeros((0,), dtype=float), theta=np.zeros((0,), dtype=float))

    idx = np.arange(N, dtype=float)

    tau = float(knobs.get("tau", 0.0))
    zeta = float(knobs.get("zeta", 0.0))
    rho = float(knobs.get("rho", 0.0))
    zeta_phase = float(knobs.get("zeta_phase", 0.0))
    kappa = float(knobs.get("kappa", 0.0))

    base = (
        1.0
        + 0.18 * np.sin(0.7 * tau * (idx + 1))
        + 0.12 * np.cos(0.9 * zeta * (idx + 0.5))
        + 0.08 * np.sin(0.5 * rho * (idx + 1))
        + 0.06 * np.cos(0.6 * zeta_phase * (idx + 0.5))
    )
    base = np.clip(base + 0.05 * np.tanh(0.4 * kappa), 0.05, None)
    pQ = base / float(base.sum())

    theta = (
        0.32 * tau * (idx / max(N - 1, 1))
        + 0.27 * zeta * np.sin(math.pi * idx / max(N - 1, 1))
        + 0.22 * rho * np.cos(math.pi * idx / max(N - 1, 1))
        + 0.18 * kappa * (idx / max(N, 1))
        + 0.15 * zeta_phase * np.sin(0.5 * math.pi * idx / max(N, 1))
    )
    theta = wrap_angles(theta)

    return LayersState(pQ=pQ, theta=theta)


def _grid_edges(center: float, extent: float, grid_size: int) -> np.ndarray:
    if grid_size <= 0:
        raise ValueError("grid_size must be positive")
    span = abs(float(extent))
    if span == 0.0:
        raise ValueError("extent must be non-zero to form a loop region")
    edges = np.linspace(-1.0, 1.0, num=grid_size + 1)
    return center + span * edges


def _compute_flux(
    S: GraphSubstrate,
    center: Mapping[str, float],
    extent: Mapping[str, float],
    *,
    grid_size: int,
    axes: tuple[str, str],
) -> float:
    axis_i, axis_j = axes
    axis_i_edges = _grid_edges(center[axis_i], extent[axis_i], grid_size)
    axis_j_edges = _grid_edges(center[axis_j], extent[axis_j], grid_size)

    psi_cache: dict[tuple[int, int], np.ndarray] = {}

    def psi_at(i: int, j: int) -> np.ndarray:
        key = (i, j)
        if key not in psi_cache:
            knob_state = dict(center)
            knob_state[axis_i] = float(axis_i_edges[i])
            knob_state[axis_j] = float(axis_j_edges[j])
            state = _synthetic_state(S, knob_state)
            psi_cache[key] = build_psi(state.pQ, state.theta)
        return psi_cache[key]

    flux = 0.0
    for i in range(grid_size):
        for j in range(grid_size):
            psi0 = psi_at(i, j)
            psi_i = psi_at(i + 1, j)
            psi_ij = psi_at(i + 1, j + 1)
            psi_j = psi_at(i, j + 1)

            delta_i = float(axis_i_edges[i + 1] - axis_i_edges[i])
            delta_j = float(axis_j_edges[j + 1] - axis_j_edges[j])

            omega, _ = curvature_tile(psi0, psi_i, psi_ij, psi_j, delta_i, delta_j)
            flux += float(omega) * delta_i * delta_j

    return float(flux)


# ---------------------------------------------------------------------------
# Measurement helpers
# ---------------------------------------------------------------------------


def _fs_histogram(samples: Iterable[float], *, bins: int = 40) -> list[float]:
    arr = np.asarray([float(val) for val in samples if math.isfinite(val)], dtype=float)
    if arr.size == 0:
        return [0.0 for _ in range(bins)]
    hist, _ = np.histogram(arr, bins=bins, range=(0.0, max(0.4, float(arr.max()))))
    total = float(hist.sum())
    if total <= 0.0:
        return [0.0 for _ in hist]
    return [float(count) / total for count in hist]


def _adiabatic_factor(fs_p95: float, steps: int, extent: float) -> float:
    """Return a phenomenological decay factor for ``R ∝ Φ`` validity."""

    if not math.isfinite(fs_p95):
        return 0.0
    smooth = math.exp(-((fs_p95 / 0.12) ** 2))
    discretisation = 1.0 / (1.0 + 0.015 * max(0, steps - 80))
    spread = 1.0 / (1.0 + 180.0 * abs(extent))
    return float(np.clip(smooth * discretisation * spread, 0.0, 1.0))


def _maybe_cast_node(label: object) -> int | str:
    """Attempt to interpret a node label as an integer when reasonable."""

    if isinstance(label, (int, np.integer)):
        return int(label)
    if isinstance(label, str):
        stripped = label.strip()
        if stripped:
            try:
                return int(stripped)
            except ValueError:
                return stripped
    return str(label)


def _load_substrate_file(path: Path) -> GraphSubstrate:
    """Load a graph substrate from a supported artifact file."""

    suffix = path.suffix.lower()
    if suffix in {".graphml", ".gml", ".gexf"}:
        read_fn = {
            ".graphml": nx.read_graphml,
            ".gml": nx.read_gml,
            ".gexf": nx.read_gexf,
        }[suffix]
        G = read_fn(path)
        for _, _, data in G.edges(data=True):
            data.setdefault("weight", 1.0)
            data.setdefault("delay", 1.0)
        return build_substrate(nx.DiGraph(G))

    if suffix in {".gpickle", ".pickle"}:
        G = nx.read_gpickle(path)
        for _, _, data in G.edges(data=True):
            data.setdefault("weight", 1.0)
            data.setdefault("delay", 1.0)
        return build_substrate(nx.DiGraph(G))

    if suffix in {".edgelist", ".txt"}:
        edges: list[tuple[int | str, int | str, float, float]] = []
        with path.open("r", encoding="utf-8") as handle:
            for raw_line in handle:
                line = raw_line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split()
                if len(parts) < 2:
                    continue
                source = _maybe_cast_node(parts[0])
                target = _maybe_cast_node(parts[1])
                weight = float(parts[2]) if len(parts) >= 3 else 1.0
                delay = float(parts[3]) if len(parts) >= 4 else 1.0
                edges.append((source, target, weight, delay))
        if not edges:
            raise ValueError(f"No edges found in {path}")
        return from_edgelist(edges)

    if suffix == ".csv":
        edges = []
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            if not reader.fieldnames or {"source", "target"}.difference(reader.fieldnames):
                raise ValueError("CSV substrate artifact must include 'source' and 'target' columns")
            for row in reader:
                source = _maybe_cast_node(row["source"])
                target = _maybe_cast_node(row["target"])
                weight_raw = row.get("weight", "")
                delay_raw = row.get("delay", "")
                weight = float(weight_raw) if weight_raw not in {None, ""} else 1.0
                delay = float(delay_raw) if delay_raw not in {None, ""} else 1.0
                edges.append((source, target, weight, delay))
        if not edges:
            raise ValueError(f"No edges found in {path}")
        return from_edgelist(edges)

    if suffix == ".json":
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)

        if isinstance(payload, dict):
            if "links" in payload:
                try:
                    G = nx.node_link_graph(payload, directed=True, multigraph=False)
                except Exception as exc:
                    raise ValueError(f"Unsupported node-link JSON format in {path}") from exc
                for _, _, data in G.edges(data=True):
                    data.setdefault("weight", 1.0)
                    data.setdefault("delay", 1.0)
                return build_substrate(nx.DiGraph(G))

            edges_payload = payload.get("edges")
            if isinstance(edges_payload, list):
                edges: list[tuple[int | str, int | str, float, float]] = []
                for entry in edges_payload:
                    source: int | str
                    target: int | str
                    weight = 1.0
                    delay = 1.0
                    if isinstance(entry, dict):
                        try:
                            source = _maybe_cast_node(entry["source"])
                            target = _maybe_cast_node(entry["target"])
                        except KeyError as exc:  # pragma: no cover - defensive
                            raise ValueError(
                                f"Edge dictionary missing {exc.args[0]!r} key in {path}"
                            ) from exc
                        weight = float(entry.get("weight", 1.0))
                        delay = float(entry.get("delay", 1.0))
                    elif isinstance(entry, (list, tuple)) and len(entry) >= 2:
                        source = _maybe_cast_node(entry[0])
                        target = _maybe_cast_node(entry[1])
                        if len(entry) >= 3:
                            weight = float(entry[2])
                        if len(entry) >= 4:
                            delay = float(entry[3])
                    else:
                        raise ValueError(f"Unsupported edge entry {entry!r} in {path}")
                    edges.append((source, target, weight, delay))
                if edges:
                    return from_edgelist(edges)

        raise ValueError(f"Unsupported JSON substrate format in {path}")

    if suffix == ".npz":
        with np.load(path, allow_pickle=True) as payload:
            if "edges" in payload:
                edges_array = payload["edges"]
                edges = []
                for item in edges_array:
                    if len(item) < 2:
                        continue
                    source = _maybe_cast_node(item[0])
                    target = _maybe_cast_node(item[1])
                    weight = float(item[2]) if len(item) >= 3 else 1.0
                    delay = float(item[3]) if len(item) >= 4 else 1.0
                    edges.append((source, target, weight, delay))
                if edges:
                    return from_edgelist(edges)

    raise ValueError(f"Unrecognised substrate artifact format: {path}")


def _coerce_summary_value(value: object) -> object:
    """Attempt to cast JSON scalar values to numerics when reasonable."""

    if isinstance(value, bool):
        return value
    if isinstance(value, numbers.Integral):
        return int(value)
    if isinstance(value, numbers.Real):
        return float(value)
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return value
        try:
            return int(stripped)
        except ValueError:
            try:
                numeric = float(stripped)
            except ValueError:
                return stripped
            else:
                if numeric.is_integer():
                    return int(numeric)
                return numeric
    if isinstance(value, list):
        return [_coerce_summary_value(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_coerce_summary_value(item) for item in value)
    return value


def _normalise_phase1_seed(seed: object | None) -> int:
    """Return an integer seed for Phase 1 substrate factories."""

    if seed is None:
        return PHASE1_DEFAULT_SEED
    if isinstance(seed, numbers.Integral):
        return int(seed)
    if isinstance(seed, numbers.Real):
        numeric = float(seed)
        if not math.isfinite(numeric):
            raise ValueError("Phase 1 substrate seed must be finite")
        return int(numeric)
    if isinstance(seed, str):
        stripped = seed.strip()
        if not stripped:
            return PHASE1_DEFAULT_SEED
        try:
            numeric = float(stripped)
        except ValueError as exc:  # pragma: no cover - defensive guard
            raise ValueError(f"Invalid Phase 1 substrate seed: {seed!r}") from exc
        if not math.isfinite(numeric):
            raise ValueError("Phase 1 substrate seed must be finite")
        return int(numeric)
    raise ValueError(f"Unsupported seed type for Phase 1 substrate: {type(seed)!r}")


def _make_phase1_factory(identifier: str) -> Callable[[int | None], GraphSubstrate]:
    """Create a factory that rebuilds Phase 1 substrates on demand."""

    def factory(seed: int | None = None) -> GraphSubstrate:
        try:
            from experiments.gateB_ridge_finder import run as phase1_run
        except ImportError as exc:  # pragma: no cover - defensive guard
            raise ValueError(
                f"Phase 1 substrate factory '{identifier}' is unavailable"
            ) from exc

        base_seed = _normalise_phase1_seed(seed)
        try:
            built = phase1_run.build_substrates([identifier], seed=base_seed)
        except Exception as exc:  # pragma: no cover - defensive guard
            raise ValueError(
                f"Failed to rebuild Phase 1 substrate '{identifier}' with seed {base_seed}"
            ) from exc

        if not built:
            raise ValueError(
                f"Phase 1 substrate factory '{identifier}' produced no substrate"
            )

        _, substrate = built[0]
        return substrate

    factory.__name__ = f"phase1_{identifier}_factory"
    return factory


_PHASE1_SUBSTRATE_FACTORIES: dict[str, Callable[[int | None], GraphSubstrate]] = {
    name: _make_phase1_factory(name)
    for name in (
        "small_world",
        "scale_free",
        "watts_strogatz_p0",
        "watts_strogatz_p001",
        "watts_strogatz_p010",
        "periodic_lattice",
        "erdos_renyi",
        "barabasi_albert",
    )
}


def _resolve_graph_factory(identifier: str):
    """Return a graph factory callable for the identifier or raise ``ValueError``."""

    key = identifier.strip().lower()
    if not key:
        raise ValueError("Graph identifier is empty")

    if ":" in key:
        key = key.split(":")[-1]

    alias_map = {
        "ring3-hetero": "ring3_hetero",
        "ring3 hetero": "ring3_hetero",
        "ring3hetero": "ring3_hetero",
        "ring3": "ring3",
        "random_regular": "random_regular_digraph",
        "random-regular": "random_regular_digraph",
        "random_regular_digraph": "random_regular_digraph",
        "random-regular-digraph": "random_regular_digraph",
        "dimer": "dimer",
        "line3": "line3",
        "small_world": "small_world",
        "small-world": "small_world",
        "smallworld": "small_world",
        "scale_free": "scale_free",
        "scale-free": "scale_free",
        "scalefree": "scale_free",
        "watts_strogatz_p0": "watts_strogatz_p0",
        "watts-strogatz-p0": "watts_strogatz_p0",
        "wattsstrogatzp0": "watts_strogatz_p0",
        "watts_strogatz_p001": "watts_strogatz_p001",
        "watts-strogatz-p001": "watts_strogatz_p001",
        "wattsstrogatzp001": "watts_strogatz_p001",
        "watts_strogatz_p010": "watts_strogatz_p010",
        "watts-strogatz-p010": "watts_strogatz_p010",
        "wattsstrogatzp010": "watts_strogatz_p010",
        "periodic_lattice": "periodic_lattice",
        "periodic-lattice": "periodic_lattice",
        "periodiclattice": "periodic_lattice",
        "erdos_renyi": "erdos_renyi",
        "erdos-renyi": "erdos_renyi",
        "erdosrenyi": "erdos_renyi",
        "barabasi_albert": "barabasi_albert",
        "barabasi-albert": "barabasi_albert",
        "barabasialbert": "barabasi_albert",
    }
    factory_name = alias_map.get(key, key)

    if factory_name in _PHASE1_SUBSTRATE_FACTORIES:
        return _PHASE1_SUBSTRATE_FACTORIES[factory_name]

    try:
        factory = getattr(graph_factories, factory_name)
    except AttributeError as exc:  # pragma: no cover - defensive guard
        raise ValueError(f"Unknown graph factory identifier: {identifier}") from exc

    if not callable(factory):
        raise ValueError(f"Graph factory {factory_name!r} is not callable")

    return factory


def _instantiate_graph_from_metadata(
    identifier: str,
    graph_kwargs: Mapping[str, object] | None,
    *,
    seed_value: int | None,
    source_description: str,
) -> GraphSubstrate:
    factory = _resolve_graph_factory(str(identifier))
    signature = inspect.signature(factory)
    alias_map = {
        "n": "N",
        "nodes": "N",
        "num_nodes": "N",
        "node_count": "N",
        "k": "out_degree",
        "degree": "out_degree",
        "outdegree": "out_degree",
        "out_degree": "out_degree",
        "graph_seed": "seed",
        "graphseed": "seed",
    }

    normalised_kwargs: dict[str, object] = {}
    if graph_kwargs:
        for raw_key, value in graph_kwargs.items():
            key = str(raw_key)
            canonical = alias_map.get(key.lower(), key)
            normalised_kwargs.setdefault(canonical, _coerce_summary_value(value))

    filtered_kwargs: dict[str, object] = {}
    for param_name in signature.parameters:
        if param_name in normalised_kwargs:
            filtered_kwargs[param_name] = normalised_kwargs[param_name]

    if (
        seed_value is not None
        and "seed" in signature.parameters
        and "seed" not in filtered_kwargs
    ):
        filtered_kwargs["seed"] = seed_value

    required_kinds = {
        inspect.Parameter.POSITIONAL_ONLY,
        inspect.Parameter.POSITIONAL_OR_KEYWORD,
        inspect.Parameter.KEYWORD_ONLY,
    }
    required_params = [
        name
        for name, parameter in signature.parameters.items()
        if parameter.kind in required_kinds and parameter.default is inspect._empty
    ]

    missing = [name for name in required_params if name not in filtered_kwargs]
    if missing:
        missing_list = ", ".join(sorted(missing))
        raise ValueError(
            f"{source_description} for graph '{identifier}' is missing required parameters: {missing_list}"
        )

    return factory(**filtered_kwargs)


def _load_substrate_from_summary(
    summary_path: Path,
    *,
    graph_override: GraphFactoryOverride | None = None,
) -> GraphSubstrate:
    """Construct a substrate from a Phase 3 loop summary artifact."""

    with summary_path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    if not isinstance(payload, Mapping):
        raise ValueError("Phase 3 summary must contain a JSON object")

    def _maybe_use_override_from_error(exc: Exception) -> GraphSubstrate | None:
        if graph_override is None:
            return None
        message = str(exc).lower()
        triggers = (
            "missing graph descriptor",
            "missing graph identifier",
            "graph descriptor in summary lacks an identifier",
            "graph descriptor in summary has an empty identifier",
        )
        if any(trigger in message for trigger in triggers):
            return _instantiate_graph_from_metadata(
                graph_override.identifier,
                graph_override.as_kwargs(),
                seed_value=None,
                source_description="Graph override",
            )
        return None

    try:
        candidate_keys = (
            "graph",
            "graph_descriptor",
            "graphDescriptor",
            "graph_info",
            "graphInfo",
        )
        graph_info: object | None = None

        def _select_graph_block(source: Mapping[str, object]) -> object | None:
            for candidate_key in candidate_keys:
                if candidate_key not in source:
                    continue
                candidate = source[candidate_key]
                if candidate is None:
                    continue
                if isinstance(candidate, str) and not candidate.strip():
                    continue
                if isinstance(candidate, Mapping) and not candidate:
                    continue
                if (
                    isinstance(candidate, Sequence)
                    and not isinstance(candidate, (str, bytes, bytearray))
                    and not candidate
                ):
                    continue
                return candidate
            return None

        graph_info = _select_graph_block(payload)

        if graph_info is None:
            graphs_block = payload.get("graphs")
            if isinstance(graphs_block, Mapping):
                graph_info = []
                for name, descriptor in graphs_block.items():
                    if isinstance(descriptor, Mapping):
                        merged: dict[str, object] = {str(k): v for k, v in descriptor.items()}
                        merged.setdefault("identifier", name)
                        graph_info.append(merged)
                    else:
                        graph_info.append(descriptor)
            elif isinstance(graphs_block, Sequence) and not isinstance(
                graphs_block, (str, bytes, bytearray)
            ):
                graph_info = list(graphs_block)

        if graph_info is None and isinstance(payload, Mapping):
            meta_block = payload.get("meta")
            if isinstance(meta_block, Mapping):
                graph_info = _select_graph_block(meta_block)

        identifier: str | None = None
        graph_kwargs: dict[str, object] = {}

        def _ingest_mapping(
            descriptor: Mapping[str, object],
            *,
            require_identifier: bool,
        ) -> tuple[str | None, dict[str, object]]:
            raw_identifier = (
                descriptor.get("identifier")
                or descriptor.get("id")
                or descriptor.get("name")
                or descriptor.get("kind")
                or descriptor.get("type")
            )
            if raw_identifier is None:
                alt_identifier = descriptor.get("graph")
                if isinstance(alt_identifier, str) and alt_identifier.strip():
                    raw_identifier = alt_identifier
                else:
                    alt_identifier = descriptor.get("factory") or descriptor.get("graph_factory")
                    if isinstance(alt_identifier, str) and alt_identifier.strip():
                        raw_identifier = alt_identifier

            identifier_value: str | None = None
            if raw_identifier is not None:
                identifier_value = str(raw_identifier).strip()
                if not identifier_value:
                    identifier_value = None

            kwargs: dict[str, object] = {}
            kwargs_block = descriptor.get("kwargs")
            if isinstance(kwargs_block, Mapping):
                for key, value in kwargs_block.items():
                    kwargs.setdefault(str(key), value)

            for key, value in descriptor.items():
                if key in {"identifier", "id", "name", "kind", "type", "kwargs"}:
                    continue
                kwargs.setdefault(str(key), value)

            if require_identifier and not identifier_value:
                raise ValueError("Graph descriptor in summary lacks an identifier")

            return identifier_value, kwargs

        if isinstance(graph_info, str):
            identifier = graph_info.strip()
            if not identifier:
                raise ValueError("Graph descriptor in summary has an empty identifier")
        elif isinstance(graph_info, Mapping):
            identifier, graph_kwargs = _ingest_mapping(graph_info, require_identifier=True)
            if identifier is None:
                raise ValueError("Graph descriptor in summary lacks an identifier")
        elif isinstance(graph_info, Sequence) and not isinstance(graph_info, (str, bytes, bytearray)):
            def _extract_seed_candidate(descriptor: Mapping[str, object]) -> object | None:
                for seed_key in ("seed", "graph_seed", "graphSeed"):
                    if seed_key in descriptor:
                        return descriptor[seed_key]
                kwargs_block = descriptor.get("kwargs")
                if isinstance(kwargs_block, Mapping):
                    for seed_key in ("seed", "graph_seed", "graphSeed"):
                        if seed_key in kwargs_block:
                            return kwargs_block[seed_key]
                return None

            last_error: Exception | None = None
            for entry in graph_info:
                if entry is None:
                    continue
                if isinstance(entry, str):
                    candidate = entry.strip()
                    if candidate and identifier is None:
                        identifier = candidate
                    continue
                if isinstance(entry, Mapping):
                    candidate_identifier, candidate_kwargs = _ingest_mapping(
                        entry, require_identifier=False
                    )
                    if candidate_identifier and identifier is None:
                        identifier = candidate_identifier
                    for key, value in candidate_kwargs.items():
                        graph_kwargs.setdefault(str(key), value)
                    if "seed" not in graph_kwargs:
                        seed_candidate = _extract_seed_candidate(entry)
                        if seed_candidate is not None:
                            graph_kwargs.setdefault("seed", seed_candidate)
                    continue
                last_error = ValueError(
                    f"Unsupported graph descriptor entry type: {type(entry).__name__}"
                )

            if identifier is None:
                if last_error is not None:
                    raise ValueError("Phase 3 summary missing graph identifier") from last_error
                raise ValueError("Phase 3 summary missing graph identifier")
        else:
            raise ValueError(
                "Phase 3 summary missing graph descriptor; expected a 'graph' string/object, "
                "a graph descriptor sequence, or a 'graphs' collection"
            )

        if identifier is None:
            raise ValueError("Phase 3 summary missing graph identifier")
        identifier = identifier.strip()
        if not identifier:
            raise ValueError("Phase 3 summary missing graph identifier")

        seed_candidates: list[object] = []
        for container in (payload, graph_info if isinstance(graph_info, Mapping) else {}):
            if not isinstance(container, Mapping):
                continue
            for key in ("seed", "graph_seed", "graphSeed"):
                if key in container:
                    seed_candidates.append(container[key])
        seed_value: int | None = None
        for candidate in seed_candidates:
            if isinstance(candidate, numbers.Integral):
                seed_value = int(candidate)
                break
            if isinstance(candidate, numbers.Real):
                seed_value = int(candidate)
                break
            if isinstance(candidate, str):
                stripped = candidate.strip()
                if not stripped:
                    continue
                try:
                    seed_value = int(stripped)
                    break
                except ValueError:
                    try:
                        numeric = float(stripped)
                    except ValueError:
                        continue
                    else:
                        seed_value = int(numeric)
                        break

        return _instantiate_graph_from_metadata(
            identifier,
            graph_kwargs,
            seed_value=seed_value,
            source_description="Phase 3 summary",
        )
    except ValueError as exc:
        override_substrate = _maybe_use_override_from_error(exc)
        if override_substrate is not None:
            return override_substrate
        raise


def _load_substrate_artifact(
    path: Path,
    *,
    graph_override: GraphFactoryOverride | None = None,
) -> GraphSubstrate:
    """Load a substrate artifact from a file or directory."""

    candidate = path.expanduser()
    if not candidate.exists():
        raise FileNotFoundError(f"substrate artifact {candidate} does not exist")

    if candidate.is_file():
        try:
            return _load_substrate_file(candidate)
        except ValueError:
            if graph_override is not None:
                return _instantiate_graph_from_metadata(
                    graph_override.identifier,
                    graph_override.as_kwargs(),
                    seed_value=None,
                    source_description="Graph override",
                )
            raise

    search_order = [
        "substrate.json",
        "graph.json",
        "graph.graphml",
        "graph.gml",
        "graph.gexf",
        "graph.gpickle",
        "edges.csv",
        "edges.json",
        "edges.npz",
    ]

    # Some generated artifacts place the actual substrate inside nested directories.
    # We perform a breadth-first search so that well-known filenames close to the
    # root are discovered first, while still handling deeper layouts.
    summary_filenames = {"phase3_loop_summary.json", "summary.json"}

    queue: deque[Path] = deque([candidate])
    visited: set[Path] = set()
    summary_candidates: list[Path] = []

    while queue:
        current = queue.popleft()
        if current in visited:
            continue
        visited.add(current)

        if current.is_file():
            if current.name in summary_filenames:
                summary_candidates.append(current)
                continue
            try:
                return _load_substrate_file(current)
            except ValueError:
                # Ignore files that do not contain a supported substrate
                continue

        if not current.is_dir():
            continue

        for name in search_order:
            target = current / name
            if target.is_file():
                return _load_substrate_file(target)

        for child in sorted(current.iterdir()):
            if child.is_file():
                if child.name in summary_filenames:
                    summary_candidates.append(child)
                    continue
                try:
                    return _load_substrate_file(child)
                except ValueError:
                    continue
            elif child.is_dir():
                queue.append(child)

    last_summary_error: Exception | None = None
    last_summary_path: Path | None = None

    for summary_path in summary_candidates:
        try:
            return _load_substrate_from_summary(
                summary_path,
                graph_override=graph_override,
            )
        except (ValueError, TypeError, KeyError) as exc:
            last_summary_error = exc
            last_summary_path = summary_path
            continue

    if last_summary_error is not None:
        summary_list = ", ".join(str(path) for path in summary_candidates)
        error_message = str(last_summary_error) or last_summary_error.__class__.__name__
        if graph_override is not None:
            return _instantiate_graph_from_metadata(
                graph_override.identifier,
                graph_override.as_kwargs(),
                seed_value=None,
                source_description="Graph override",
            )
        raise ValueError(
            "Failed to construct a substrate from summary artifacts "
            f"({summary_list}); last error from {last_summary_path}: {error_message}"
        ) from last_summary_error

    if graph_override is not None:
        return _instantiate_graph_from_metadata(
            graph_override.identifier,
            graph_override.as_kwargs(),
            seed_value=None,
            source_description="Graph override",
        )

    raise FileNotFoundError(f"Could not locate a substrate artifact inside {candidate}")


def _run_sample(
    S: GraphSubstrate,
    center: Mapping[str, float],
    extent: float,
    steps: int,
    *,
    grid_size: int,
    axes: tuple[str, str],
) -> SampleResult:
    axis_i, axis_j = axes
    loop_center = dict(center)
    extent_map = {axis_i: extent, axis_j: extent}
    loop = ParameterPath(
        kind="rectangle",
        center=loop_center,
        extents=extent_map,
        steps=steps,
        orientation="CCW",
        axes=axes,
    )

    psi_traj: list[np.ndarray] = []
    for idx in range(loop.steps):
        lambda_state, _, _ = loop.step(idx)
        state = _synthetic_state(S, lambda_state)
        psi_traj.append(build_psi(state.pQ, state.theta))

    fs_steps: list[float] = []
    if psi_traj:
        cyc = list(psi_traj)
        cyc.append(psi_traj[0])
        for psi_a, psi_b in zip(cyc, cyc[1:]):
            try:
                fs_steps.append(float(fs_distance(psi_a, psi_b)))
            except ValueError:
                fs_steps.append(float("nan"))

    fs_arr = np.asarray([val for val in fs_steps if math.isfinite(val)], dtype=float)
    fs_mean = float(fs_arr.mean()) if fs_arr.size else float("nan")
    fs_p95 = float(np.percentile(fs_arr, 95)) if fs_arr.size else float("nan")

    flux = _compute_flux(S, loop_center, extent_map, grid_size=grid_size, axes=axes)
    area = 4.0 * abs(extent_map[axis_i]) * abs(extent_map[axis_j])

    factor = _adiabatic_factor(fs_p95, steps, extent)
    readout = float(flux * factor)
    kappa = readout / flux if flux else float("nan")

    return SampleResult(
        extent=float(extent),
        steps=int(steps),
        flux=float(flux),
        area=float(area),
        kappa=float(kappa),
        readout=float(readout),
        fs_mean=fs_mean,
        fs_p95=fs_p95,
        fs_hist=_fs_histogram(fs_steps),
    )


def _determine_boundary(
    samples: Sequence[SampleResult],
    *,
    extent_values: Sequence[float],
    step_values: Sequence[int],
    reference_kappa: float,
) -> list[BoundaryPoint]:
    by_extent: dict[float, list[SampleResult]] = {float(ext): [] for ext in extent_values}
    for sample in samples:
        by_extent.setdefault(sample.extent, []).append(sample)

    boundary: list[BoundaryPoint] = []
    for extent in extent_values:
        candidates = sorted(by_extent.get(float(extent), []), key=lambda s: s.steps, reverse=True)
        boundary_sample: SampleResult | None = None
        for sample in candidates:
            if not math.isfinite(sample.kappa):
                continue
            delta = abs(sample.kappa - reference_kappa)
            if reference_kappa != 0.0:
                delta /= abs(reference_kappa)
            if delta > 0.2:
                boundary_sample = sample
                break
        if boundary_sample is None:
            boundary.append(
                BoundaryPoint(
                    extent=float(extent),
                    boundary_steps=None,
                    reference_kappa=reference_kappa,
                    boundary_kappa=None,
                    boundary_fs_p95=None,
                )
            )
        else:
            boundary.append(
                BoundaryPoint(
                    extent=float(extent),
                    boundary_steps=int(boundary_sample.steps),
                    reference_kappa=reference_kappa,
                    boundary_kappa=float(boundary_sample.kappa),
                    boundary_fs_p95=float(boundary_sample.fs_p95),
                )
            )
    return boundary


# ---------------------------------------------------------------------------
# Command-line interface
# ---------------------------------------------------------------------------


SUPPORTED_AXES = ("rho", "tau", "zeta", "zeta_phase", "kappa")


def _parse_center(text: str, allowed_axes: Sequence[str]) -> dict[str, float]:
    normalized_axes = [axis.strip() for axis in allowed_axes if str(axis).strip()]
    center: dict[str, float] = {axis: 0.0 for axis in SUPPORTED_AXES}
    if not text:
        return center
    parts = [item.strip() for item in text.split(",") if item.strip()]
    for part in parts:
        if "=" not in part:
            raise ValueError(f"malformed centre entry '{part}'")
        key, value = (token.strip() for token in part.split("=", 1))
        if key not in center:
            raise ValueError(f"unsupported centre knob '{key}'")
        try:
            center[key] = float(value)
        except ValueError as exc:  # pragma: no cover - defensive
            raise ValueError(f"non-numeric centre value '{value}'") from exc

    for axis in normalized_axes:
        if axis not in center:
            raise ValueError(f"unsupported centre knob '{axis}'")

    return center


def _parse_float_list(values: Sequence[str]) -> list[float]:
    if not values:
        raise ValueError("at least one value must be supplied")
    parsed: list[float] = []
    for entry in values:
        try:
            parsed.append(float(entry))
        except ValueError as exc:  # pragma: no cover - defensive
            raise ValueError(f"invalid float value '{entry}'") from exc
    return parsed


def _parse_int_list(values: Sequence[str]) -> list[int]:
    if not values:
        raise ValueError("at least one value must be supplied")
    parsed: list[int] = []
    for entry in values:
        try:
            parsed.append(int(entry))
        except ValueError as exc:  # pragma: no cover - defensive
            raise ValueError(f"invalid integer value '{entry}'") from exc
    return parsed


def _write_surface(path: Path, samples: Sequence[SampleResult]) -> None:
    header = [
        "extent",
        "steps",
        "flux",
        "area",
        "kappa1",
        "readout",
        "fs_mean",
        "fs_p95",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        for sample in sorted(samples, key=lambda s: (s.extent, s.steps)):
            writer.writerow(
                [
                    f"{sample.extent:.6f}",
                    sample.steps,
                    f"{sample.flux:.6e}",
                    f"{sample.area:.6e}",
                    f"{sample.kappa:.6f}" if math.isfinite(sample.kappa) else "nan",
                    f"{sample.readout:.6e}",
                    f"{sample.fs_mean:.6f}" if math.isfinite(sample.fs_mean) else "nan",
                    f"{sample.fs_p95:.6f}" if math.isfinite(sample.fs_p95) else "nan",
                ]
            )


def _write_histograms(path: Path, samples: Sequence[SampleResult]) -> None:
    payload = {}
    for sample in samples:
        key = f"extent={sample.extent:.4f}|steps={sample.steps}"
        payload[key] = sample.fs_hist
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def _write_boundary(path: Path, boundary: Sequence[BoundaryPoint]) -> None:
    header = ["extent", "boundary_steps", "reference_kappa", "boundary_kappa", "fs_p95"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        for point in boundary:
            writer.writerow(
                [
                    f"{point.extent:.6f}",
                    point.boundary_steps if point.boundary_steps is not None else "",
                    f"{point.reference_kappa:.6f}",
                    f"{point.boundary_kappa:.6f}" if point.boundary_kappa is not None else "",
                    f"{point.boundary_fs_p95:.6f}" if point.boundary_fs_p95 is not None else "",
                ]
            )


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Map the adiabatic boundary across a chosen control plane",
    )
    parser.add_argument("--output-dir", type=Path, default=Path("runs/adiabatic_boundary"))
    parser.add_argument("--center", type=str, default="tau=0.8,zeta=0.0")
    parser.add_argument(
        "--axes",
        nargs=2,
        default=["tau", "zeta"],
        help="Two control knobs defining the sweep plane (e.g. 'tau zeta').",
    )
    parser.add_argument("--extents", nargs="+", default=["0.02", "0.04", "0.08"])
    parser.add_argument("--steps", nargs="+", default=["400", "200", "120", "80"])
    parser.add_argument("--grid-size", type=int, default=6)
    parser.add_argument(
        "--substrate-dir",
        type=Path,
        default=None,
        help=(
            "Optional path to a substrate artifact directory or file. When provided, "
            "the graph substrate is loaded from this location instead of using the "
            "default ring3_hetero substrate."
        ),
    )
    parser.add_argument(
        "--graph-id",
        type=str,
        default=None,
        help=(
            "Override the graph factory identifier when substrate metadata is missing."
        ),
    )
    parser.add_argument(
        "--graph-params",
        type=str,
        default=None,
        help=(
            "JSON object providing keyword arguments for the overridden graph factory."
        ),
    )

    args = parser.parse_args(argv)

    if args.graph_params and not args.graph_id:
        parser.error("--graph-params requires --graph-id to be specified")

    if args.graph_id is not None:
        args.graph_id = str(args.graph_id).strip()
        if not args.graph_id:
            parser.error("--graph-id must not be empty")

    if args.graph_params is not None:
        try:
            parsed_params = json.loads(args.graph_params)
        except json.JSONDecodeError as exc:
            parser.error(f"--graph-params must contain valid JSON: {exc.msg}")
        if not isinstance(parsed_params, Mapping):
            parser.error("--graph-params must describe a JSON object mapping parameter names to values")
        args.graph_params = dict(parsed_params)
    else:
        args.graph_params = None

    return args


def main(argv: Sequence[str] | None = None) -> None:
    args = _parse_args(argv)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    graph_override: GraphFactoryOverride | None = None
    if args.graph_id:
        graph_override = GraphFactoryOverride(
            identifier=args.graph_id,
            kwargs=args.graph_params,
        )

    axes_values = [str(axis).strip().lower() for axis in args.axes]
    if len(axes_values) != 2:
        raise ValueError("axes must specify exactly two control knobs")
    if len({axes_values[0], axes_values[1]}) != 2:
        raise ValueError("axes must refer to two distinct control knobs")
    for axis in axes_values:
        if axis not in SUPPORTED_AXES:
            raise ValueError(f"unsupported control knob '{axis}'")

    axes = (axes_values[0], axes_values[1])

    center = _parse_center(str(args.center), axes)
    extent_values = _parse_float_list(args.extents)
    step_values = _parse_int_list(args.steps)

    if args.substrate_dir is not None:
        substrate = _load_substrate_artifact(
            Path(args.substrate_dir),
            graph_override=graph_override,
        )
    else:
        substrate = ring3_hetero()

    samples: list[SampleResult] = []
    for extent in extent_values:
        for steps in step_values:
            samples.append(
                _run_sample(
                    substrate,
                    center,
                    extent=float(extent),
                    steps=int(steps),
                    grid_size=int(args.grid_size),
                    axes=axes,
                )
            )

    baseline_candidates = [
        sample
        for sample in samples
        if math.isfinite(sample.kappa)
        and math.isclose(sample.extent, min(extent_values))
        and sample.steps == max(step_values)
    ]
    if not baseline_candidates:
        raise RuntimeError("could not establish a baseline κ₁ value")
    reference_kappa = float(baseline_candidates[0].kappa)

    boundary = _determine_boundary(
        samples,
        extent_values=extent_values,
        step_values=step_values,
        reference_kappa=reference_kappa,
    )

    _write_surface(output_dir / "kappa_surface.csv", samples)
    _write_histograms(output_dir / "fs_histograms.json", samples)
    _write_boundary(output_dir / "boundary.csv", boundary)


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    try:
        main()
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(2)

