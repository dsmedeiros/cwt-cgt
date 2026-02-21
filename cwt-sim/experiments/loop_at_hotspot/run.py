"""Loop orientation validation at curvature hotspots."""

from __future__ import annotations

import argparse
import json
import math
import numbers
import time
from dataclasses import dataclass, replace
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Mapping, Sequence

import numpy as np

from cwt.geometry.adapt_mesh import curvature_anytime
from cwt.graph import factories
from cwt.graph.substrate import GraphSubstrate
from cwt.io.config import run_config_from_sections
from cwt.layers.state import LayersState
from cwt.orchestrator.param_path import ParameterPath
from cwt.orchestrator.scheduler import (
    RunConfig,
    _direct_neighbor_state_factory,
    _psi_at,
    _psi_sampler_factory_direct,
    run_parameter_loop,
)

if TYPE_CHECKING:
    from cwt.orchestrator.scheduler import RunRecord


@dataclass
class HotspotSpec:
    """Curvature hotspot specification extracted from the atlas JSON."""

    center: dict[str, float]
    omega_abs: float | None
    metadata: dict[str, Any]


@dataclass(frozen=True)
class RectExtent:
    """Axis-aligned rectangle extents for a two-axis loop."""

    axes: tuple[str, str]
    values: tuple[float, float]

    def __post_init__(self) -> None:
        if len(self.axes) != 2:
            raise ValueError("RectExtent requires exactly two axes")
        axis_i, axis_j = (str(axis) for axis in self.axes)
        value_i, value_j = (float(self.values[0]), float(self.values[1]))
        if axis_i == axis_j:
            raise ValueError("RectExtent axes must be distinct")
        object.__setattr__(self, "axes", (axis_i, axis_j))
        object.__setattr__(self, "values", (value_i, value_j))

    @classmethod
    def from_scalar(cls, axes: tuple[str, str], value: float) -> "RectExtent":
        val = float(value)
        return cls(tuple(axes), (val, val))

    @classmethod
    def from_pair(cls, axes: tuple[str, str], values: tuple[float, float]) -> "RectExtent":
        return cls(tuple(axes), (float(values[0]), float(values[1])))

    def axis_value(self, axis: str) -> float:
        axis_norm = str(axis)
        if axis_norm == self.axes[0]:
            return self.values[0]
        if axis_norm == self.axes[1]:
            return self.values[1]
        raise KeyError(f"axis '{axis}' not present in RectExtent")

    def as_dict(self) -> dict[str, float]:
        return {self.axes[0]: self.values[0], self.axes[1]: self.values[1]}

    def max_abs(self) -> float:
        return max(abs(self.values[0]), abs(self.values[1]))

    def replace(self, *, axis: str | None = None, value: float | None = None) -> "RectExtent":
        if axis is None:
            raise ValueError("axis must be provided when replacing a RectExtent value")
        axis_norm = str(axis)
        new_values = list(self.values)
        if axis_norm == self.axes[0]:
            new_values[0] = float(value if value is not None else self.values[0])
        elif axis_norm == self.axes[1]:
            new_values[1] = float(value if value is not None else self.values[1])
        else:
            raise KeyError(f"axis '{axis}' not present in RectExtent")
        return RectExtent(self.axes, (new_values[0], new_values[1]))

    def scale_axis(self, axis: str, factor: float) -> "RectExtent":
        return self.replace(axis=axis, value=self.axis_value(axis) * float(factor))

    def clamp_axis(
        self,
        axis: str,
        *,
        lower: float | None = None,
        upper: float | None = None,
    ) -> "RectExtent":
        value = self.axis_value(axis)
        if lower is not None:
            value = max(float(lower), value)
        if upper is not None:
            value = min(float(upper), value)
        return self.replace(axis=axis, value=value)

    def scale(self, factor: float) -> "RectExtent":
        scale_val = float(factor)
        return RectExtent(
            self.axes,
            (self.values[0] * scale_val, self.values[1] * scale_val),
        )

    def clamp(self, *, lower: float | None = None, upper: float | None = None) -> "RectExtent":
        result = self
        for axis in self.axes:
            result = result.clamp_axis(axis, lower=lower, upper=upper)
        return result

    def is_close(
        self,
        other: "RectExtent",
        *,
        rel_tol: float = 1e-9,
        abs_tol: float = 1e-12,
    ) -> bool:
        if self.axes != other.axes:
            return False
        return all(
            math.isclose(
                self.axis_value(axis),
                other.axis_value(axis),
                rel_tol=rel_tol,
                abs_tol=abs_tol,
            )
            for axis in self.axes
        )


@dataclass
class OrientationRun:
    """Metrics recorded for a single loop orientation."""

    orientation: str
    extents: RectExtent
    steps: int
    area: float
    phi_flux: float
    phi_missing: bool
    kappa: float
    memory: list[float]
    fs_p95: float
    fs_guard_exceeded: bool
    fs_edge_counts: dict[str, int]
    fs_edge_exceedances: dict[str, int]
    fs_edge_max: dict[str, float]
    duration: float
    budget_limited: bool = False


@dataclass
class TimeBudgetTracker:
    """Track elapsed loop time against an optional wall-clock budget."""

    total: float | None
    consumed: float = 0.0

    def __post_init__(self) -> None:
        if self.total is None:
            return
        try:
            numeric = float(self.total)
        except (TypeError, ValueError):  # pragma: no cover - defensive guard
            object.__setattr__(self, "total", None)
            return
        if not math.isfinite(numeric) or numeric <= 0.0:
            object.__setattr__(self, "total", None)
        else:
            object.__setattr__(self, "total", numeric)

    def remaining(self) -> float | None:
        if self.total is None:
            return None
        return max(self.total - self.consumed, 0.0)

    def consume(self, duration: float) -> None:
        if self.total is None:
            return
        try:
            numeric = float(duration)
        except (TypeError, ValueError):  # pragma: no cover - defensive guard
            return
        if numeric > 0.0 and math.isfinite(numeric):
            self.consumed = min(self.total, self.consumed + numeric)


@dataclass
class ExtentSummary:
    """Paired CW/CCW loop statistics for a single extent."""

    extents: RectExtent
    ccw: OrientationRun
    cw: OrientationRun
    area_flip_error: float
    phi_flip_error: float


@dataclass
class HotspotSummary:
    """Aggregate results for a single hotspot centre."""

    index: int
    spec: HotspotSpec
    extents: list[ExtentSummary]
    kappa_scale_errors: list[float]


@dataclass
class AutoExtentDecision:
    """Record of a single auto-extent pilot evaluation."""

    iteration: int
    extents: RectExtent
    pilot_steps: int
    steps: int
    fs_p95: float
    fs_guard_exceeded: bool
    fs_edge_exceedances: dict[str, int]
    decision: str


@dataclass
class AutoExtentResult:
    """Summary of the auto-extent calibration loop."""

    extent: RectExtent
    accepted: bool
    iterations: int
    decisions: list[AutoExtentDecision]


def _relative_flip_error(value_ccw: float, value_cw: float) -> float:
    if not (math.isfinite(value_ccw) and math.isfinite(value_cw)):
        return float("nan")
    denom = max(abs(value_ccw), 1e-12)
    return abs(value_cw + value_ccw) / denom


def _relative_change(base: float, follow_up: float) -> float:
    if not (math.isfinite(base) and math.isfinite(follow_up)):
        return float("nan")
    denom = max(abs(base), 1e-12)
    return abs(follow_up - base) / denom


def _coerce_float(value: object) -> float | None:
    try:
        numeric = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return numeric if math.isfinite(numeric) else None


def _axis_bounds_from_metadata(
    metadata: Mapping[str, Any] | None, axes: Sequence[str]
) -> dict[str, tuple[float | None, float | None]]:
    if metadata is None:
        return {}

    axis_payload = metadata.get("axis_bounds") if isinstance(metadata, Mapping) else None
    if not isinstance(axis_payload, Mapping):
        return {}

    bounds: dict[str, tuple[float | None, float | None]] = {}
    for axis in axes:
        axis_key = str(axis)
        entry = axis_payload.get(axis_key)
        if not isinstance(entry, Mapping):
            continue
        lower = _coerce_float(entry.get("min"))
        upper = _coerce_float(entry.get("max"))
        bounds[axis_key] = (lower, upper)
    return bounds


def _clamp_loop_region(
    center: Mapping[str, float],
    extent: RectExtent,
    axes: tuple[str, str],
    axis_bounds: Mapping[str, tuple[float | None, float | None]] | None,
) -> tuple[dict[str, float], RectExtent]:
    if not axis_bounds:
        return dict(center), extent

    adjusted_center = {axis: float(center[axis]) for axis in axes}
    adjusted_extent = extent

    for axis in axes:
        bounds = axis_bounds.get(axis)
        if bounds is None:
            continue
        lower, upper = bounds
        try:
            amplitude = abs(adjusted_extent.axis_value(axis))
        except KeyError:
            continue

        center_value = adjusted_center.get(axis, 0.0)
        lower_edge = center_value - amplitude
        upper_edge = center_value + amplitude

        if lower is not None:
            lower_edge = max(lower_edge, lower)
            upper_edge = max(upper_edge, lower)
        if upper is not None:
            lower_edge = min(lower_edge, upper)
            upper_edge = min(upper_edge, upper)

        if upper_edge < lower_edge:
            midpoint = lower_edge
            amplitude_new = 0.0
        else:
            midpoint = 0.5 * (lower_edge + upper_edge)
            amplitude_new = max(0.5 * (upper_edge - lower_edge), 0.0)

        extent_value = adjusted_extent.axis_value(axis)
        sign = 1.0 if extent_value >= 0.0 else -1.0
        amplitude_new = min(amplitude_new, abs(extent_value))
        adjusted_center[axis] = midpoint
        adjusted_extent = adjusted_extent.replace(axis=axis, value=sign * amplitude_new)

    return adjusted_center, adjusted_extent


_INHERITED_METADATA_KEYS = (
    "graph",
    "graph_descriptor",
    "graphDescriptor",
    "graph_info",
    "graphInfo",
)


def _collect_entries(
    node: Any, *, meta: Mapping[str, Any] | None = None
) -> list[tuple[Mapping[str, Any], dict[str, Any]]]:
    """Return flattened hotspot entries from ``node`` preserving metadata."""

    meta_dict = dict(meta or {})
    entries: list[tuple[Mapping[str, Any], dict[str, Any]]] = []

    if isinstance(node, Mapping):
        name = node.get("name")
        if isinstance(name, str) and name:
            meta_dict.setdefault("graph", name)

        for key in _INHERITED_METADATA_KEYS:
            if key in meta_dict:
                continue
            value = node.get(key)
            if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
                continue
            if value is not None:
                meta_dict[key] = value

        if "graphs" in node:
            graph_seq = node["graphs"]
            if isinstance(graph_seq, Sequence) and not isinstance(graph_seq, (str, bytes)):
                for item in graph_seq:
                    entries.extend(_collect_entries(item, meta=meta_dict))

        for key in ("top_tiles", "hotspots", "entries"):
            if key in node:
                seq = node[key]
                if isinstance(seq, Sequence) and not isinstance(seq, (str, bytes)):
                    for item in seq:
                        entries.extend(_collect_entries(item, meta=meta_dict))

        if ("coordinates" in node or "center" in node) and not any(
            isinstance(node.get(flag), Sequence) and not isinstance(node.get(flag), (str, bytes))
            for flag in ("top_tiles", "hotspots", "entries", "graphs")
        ):
            entries.append((node, dict(meta_dict)))

    elif isinstance(node, Sequence) and not isinstance(node, (str, bytes)):
        for item in node:
            entries.extend(_collect_entries(item, meta=meta_dict))

    return entries


def load_hotspots(path: Path, axes: Sequence[str]) -> list[HotspotSpec]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    entries = _collect_entries(payload)
    if not entries:
        raise ValueError("no hotspot entries found in the supplied JSON")

    axes_tuple = tuple(str(axis) for axis in axes)
    hotspots: list[HotspotSpec] = []
    for entry, inherited_meta in entries:
        coords = entry.get("coordinates") or entry.get("center") or {}
        if not isinstance(coords, Mapping):
            continue

        center: dict[str, float] = {}
        missing: list[str] = []
        for axis in axes_tuple:
            if axis in coords:
                try:
                    center[axis] = float(coords[axis])
                except (TypeError, ValueError):
                    raise ValueError(f"non-numeric coordinate for axis '{axis}'") from None
            else:
                missing.append(axis)
        if missing:
            raise ValueError(f"hotspot entry missing coordinates for axes: {', '.join(missing)}")

        omega_val = entry.get("omega_abs")
        if omega_val is None:
            omega_val = entry.get("omega")
        if omega_val is not None:
            try:
                omega_abs = float(omega_val)
            except (TypeError, ValueError):
                omega_abs = float("nan")
        else:
            omega_abs = float("nan")

        meta = dict(inherited_meta)
        for key, value in entry.items():
            if key in {"coordinates", "center"}:
                continue
            meta[key] = value

        hotspots.append(HotspotSpec(center=center, omega_abs=omega_abs, metadata=meta))

    return hotspots


def _default_run_config(target_index: int) -> RunConfig:
    return run_config_from_sections(
        dynamics={"eta_q": 0.3, "zeta": 0.0, "omega_scale": 1.0},
        geometry={
            "s_min": 0.6,
            "smooth_window": 3,
            "compute_metric": False,
            "compute_curvature": True,
            "adapt_levels": 1,
            "ci_tol": 0.05,
            "sample_mode": "direct",
            "neighbor_steps": 1,
            "neighbor_settle_steps": 40,
            "delta_frac": {"tau": 0.01, "zeta": 0.01},
        },
        geometric_coupling={"alpha": 0.3, "beta": 1.0, "xi_kind": {"type": "static"}},
        readout={
            "final": True,
            "memory_form": "uniform_charge",
            "params": {"mode": "one_hot", "target": int(target_index), "pQ_source": "probability"},
        },
        noise={},
        fs_step_guard={},
    )


_GRAPH_ALIAS_MAP = {
    "ring3-hetero": "ring3_hetero",
    "ring3 hetero": "ring3_hetero",
    "ring3hetero": "ring3_hetero",
    "ring-3": "ring3",
    "ring_3": "ring3",
    "random_regular": "random_regular_digraph",
    "random-regular": "random_regular_digraph",
    "randomregular": "random_regular_digraph",
    "random_regular_digraph": "random_regular_digraph",
    "random-regular-digraph": "random_regular_digraph",
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

_KWARG_ALIAS_MAP = {
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

_PHASE1_IDENTIFIERS = {
    "small_world",
    "scale_free",
    "watts_strogatz_p0",
    "watts_strogatz_p001",
    "watts_strogatz_p010",
    "periodic_lattice",
    "erdos_renyi",
    "barabasi_albert",
}


def _canonical_graph_identifier(name: str) -> str:
    key = str(name).strip().lower()
    if ":" in key:
        key = key.split(":")[-1]
    return _GRAPH_ALIAS_MAP.get(key, key)


def _coerce_seed(*values: object | None) -> int | None:
    for candidate in values:
        if candidate is None:
            continue
        if isinstance(candidate, numbers.Integral):
            return int(candidate)
        if isinstance(candidate, numbers.Real):
            numeric = float(candidate)
            if math.isfinite(numeric):
                return int(numeric)
            continue
        if isinstance(candidate, str):
            stripped = candidate.strip()
            if not stripped:
                continue
            try:
                numeric = float(stripped)
            except ValueError:
                continue
            if math.isfinite(numeric):
                return int(numeric)
    return None


def _extract_raw_descriptor(source: object | None) -> Mapping[str, Any] | None:
    if source is None:
        return None
    if isinstance(source, Mapping):
        if "identifier" in source or "name" in source:
            return source
        for key in _INHERITED_METADATA_KEYS:
            if key in source:
                nested = _extract_raw_descriptor(source[key])
                if nested is not None:
                    return nested
        return None
    if isinstance(source, str):
        stripped = source.strip()
        if not stripped:
            return None
        return {"identifier": stripped}
    return None


def _apply_descriptor_defaults(descriptor: dict[str, Any], fallback_seed: int | None) -> dict[str, Any]:
    identifier = str(descriptor.get("identifier", ""))
    if not identifier:
        return descriptor

    kwargs_raw = descriptor.get("kwargs")
    kwargs: dict[str, Any] = {}
    if isinstance(kwargs_raw, Mapping):
        for raw_key, value in kwargs_raw.items():
            key = str(raw_key)
            canonical_key = _KWARG_ALIAS_MAP.get(key.lower(), key)
            kwargs[canonical_key] = value

    canonical = _canonical_graph_identifier(identifier)
    descriptor["identifier"] = canonical
    if kwargs:
        descriptor["kwargs"] = kwargs
    else:
        descriptor.pop("kwargs", None)

    if canonical in {"ring3", "ring3_hetero"}:
        descriptor.pop("seed", None)
        return descriptor

    if canonical == "random_regular_digraph":
        N_value = kwargs.get("N", 20)
        try:
            N_numeric = int(float(N_value))
        except (TypeError, ValueError):
            N_numeric = 20
        out_value = kwargs.get("out_degree", kwargs.get("degree", 3))
        try:
            out_numeric = int(float(out_value))
        except (TypeError, ValueError):
            out_numeric = 3
        seed_value = _coerce_seed(
            descriptor.get("seed"),
            kwargs.get("seed"),
            kwargs.get("graph_seed"),
            fallback_seed,
            13,
        )
        if seed_value is None:
            seed_value = 13
        descriptor["seed"] = int(seed_value)
        descriptor["kwargs"] = {
            "N": int(N_numeric),
            "out_degree": int(out_numeric),
            "seed": int(seed_value),
        }
        return descriptor

    if canonical in _PHASE1_IDENTIFIERS:
        seed_value = _coerce_seed(
            descriptor.get("seed"),
            kwargs.get("seed") if kwargs else None,
            kwargs.get("graph_seed") if kwargs else None,
            fallback_seed,
            7,
        )
        if seed_value is not None:
            descriptor["seed"] = int(seed_value)
            if kwargs is None:
                kwargs = {}
            kwargs["seed"] = int(seed_value)
            descriptor["kwargs"] = kwargs
        elif "kwargs" in descriptor and not descriptor["kwargs"]:
            descriptor.pop("kwargs", None)
        return descriptor

    if "seed" in descriptor and descriptor["seed"] is None:
        descriptor.pop("seed", None)
    if "kwargs" in descriptor and not descriptor["kwargs"]:
        descriptor.pop("kwargs", None)
    return descriptor


def _normalise_graph_descriptor(
    descriptor: Mapping[str, Any] | str | None,
    *,
    fallback_name: str,
    fallback_seed: int | None,
) -> dict[str, Any] | None:
    raw = _extract_raw_descriptor(descriptor)
    if raw is None:
        return None

    identifier_value = raw.get("identifier") or raw.get("name") or raw.get("graph")
    if isinstance(identifier_value, Mapping):
        return _normalise_graph_descriptor(
            identifier_value,
            fallback_name=fallback_name,
            fallback_seed=fallback_seed,
        )

    identifier = str(identifier_value).strip() if identifier_value is not None else ""
    if not identifier:
        identifier = str(fallback_name)

    result: dict[str, Any] = {"identifier": identifier}

    raw_kwargs = raw.get("kwargs")
    if isinstance(raw_kwargs, Mapping):
        kwargs: dict[str, Any] = {}
        for raw_key, value in raw_kwargs.items():
            key = str(raw_key)
            canonical_key = _KWARG_ALIAS_MAP.get(key.lower(), key)
            kwargs[canonical_key] = value
        if kwargs:
            result["kwargs"] = kwargs

    if "seed" in raw:
        result["seed"] = raw["seed"]

    return _apply_descriptor_defaults(result, fallback_seed)


def _graph_descriptor_for_summary(name: str, *, seed: int | None = None) -> dict[str, Any]:
    canonical = _canonical_graph_identifier(name)
    base: dict[str, Any] = {"identifier": canonical}
    if seed is not None:
        base["seed"] = seed
    descriptor = _normalise_graph_descriptor(base, fallback_name=name, fallback_seed=seed)
    if descriptor is None:
        return {"identifier": canonical}
    return descriptor


def _select_metadata_descriptor(
    hotspots: Sequence[HotspotSpec],
) -> Mapping[str, Any] | str | None:
    for spec in hotspots:
        descriptor = _extract_raw_descriptor(spec.metadata)
        if descriptor is not None:
            return descriptor
    return None


def _prepare_graph_descriptor(
    name: str,
    *,
    seed: int | None,
    descriptor: Mapping[str, Any] | str | None = None,
) -> dict[str, Any]:
    prepared = _normalise_graph_descriptor(
        descriptor,
        fallback_name=name,
        fallback_seed=seed,
    )
    if prepared is not None:
        return prepared

    fallback = _graph_descriptor_for_summary(name, seed=seed)
    prepared = _normalise_graph_descriptor(
        fallback,
        fallback_name=name,
        fallback_seed=seed,
    )
    if prepared is not None:
        return prepared
    raise ValueError(f"unsupported substrate '{name}'")


def _build_substrate_from_descriptor(descriptor: Mapping[str, Any]) -> GraphSubstrate:
    identifier = descriptor.get("identifier")
    if identifier is None:
        raise ValueError("graph descriptor is missing an identifier")

    kwargs_raw = descriptor.get("kwargs")
    kwargs = dict(kwargs_raw) if isinstance(kwargs_raw, Mapping) else {}
    seed_value = descriptor.get("seed")

    try:
        from experiments.adiabatic_boundary import run as adiabatic_run  # type: ignore
    except ImportError:  # pragma: no cover - defensive guard
        adiabatic_run = None

    if adiabatic_run is not None:
        return adiabatic_run._instantiate_graph_from_metadata(
            identifier,
            kwargs,
            seed_value=seed_value,
            source_description="Loop hotspot metadata",
        )

    canonical = _canonical_graph_identifier(identifier)
    if canonical == "ring3_hetero":
        return factories.ring3_hetero()
    if canonical == "ring3":
        return factories.ring3()
    if canonical == "random_regular_digraph":
        N_value = kwargs.get("N", 20)
        out_value = kwargs.get("out_degree", 3)
        seed_numeric = _coerce_seed(seed_value, kwargs.get("seed"), 13)
        if seed_numeric is None:
            seed_numeric = 13
        return factories.random_regular_digraph(
            N=int(N_value),
            out_degree=int(out_value),
            seed=int(seed_numeric),
        )
    raise ValueError(f"unsupported substrate '{identifier}'")


def _build_substrate(
    name: str,
    *,
    seed: int | None = None,
    descriptor: Mapping[str, Any] | str | None = None,
) -> GraphSubstrate:
    prepared = _prepare_graph_descriptor(name, seed=seed, descriptor=descriptor)
    return _build_substrate_from_descriptor(prepared)


def _initial_state(
    substrate: GraphSubstrate, center: Mapping[str, float], config: RunConfig
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    N = substrate.N
    if N <= 0:
        empty = np.zeros(0, dtype=float)
        return empty, empty, np.zeros(0, dtype=np.complex128)
    base_prob = np.full(N, 1.0 / N, dtype=float)
    base_theta = np.zeros(N, dtype=float)
    settle_steps = max(int(getattr(config, "neighbor_settle_steps", 20)), 1)
    psi_center = _psi_at(substrate, center, base_prob, base_theta, config, steps=settle_steps)
    prob = np.square(np.abs(psi_center)).astype(float, copy=False)
    theta = np.angle(psi_center).astype(float, copy=False)
    return prob, theta, psi_center


def _curvature_probe(
    substrate: GraphSubstrate,
    config: RunConfig,
    center: Mapping[str, float],
    axes: tuple[str, str],
    base_prob: np.ndarray,
    base_theta: np.ndarray,
    psi_center: np.ndarray,
    *,
    delta: float,
) -> float:
    geometry_cfg = config.geometry or {}
    neighbor_steps_raw = geometry_cfg.get("neighbor_steps", 1)
    try:
        neighbor_steps_cfg = max(int(neighbor_steps_raw), 1)
    except (TypeError, ValueError):
        neighbor_steps_cfg = 1
    settle_steps = max(int(getattr(config, "neighbor_settle_steps", 20)), 1)
    state_for = _direct_neighbor_state_factory(
        substrate,
        center,
        base_prob,
        base_theta,
        config,
        neighbor_steps=neighbor_steps_cfg,
        settle_steps=max(neighbor_steps_cfg, settle_steps),
    )
    sampler = _psi_sampler_factory_direct(
        psi_center,
        str(axes[0]),
        str(axes[1]),
        state_for,
    )
    plaquette = curvature_anytime(
        sampler,
        float(delta),
        float(delta),
        s_min=float(config.s_min),
        ci_tol=float(config.ci_tol),
        max_levels=max(int(config.adapt_levels), 1),
    )
    return float(plaquette.omega_mean)


def _micro_scan_candidates(
    substrate: GraphSubstrate,
    config: RunConfig,
    center: Mapping[str, float],
    axes: tuple[str, str],
    *,
    delta: float,
    grid: int = 5,
) -> tuple[dict[str, float], tuple[np.ndarray, np.ndarray], dict[str, Any]]:
    axis_i, axis_j = axes
    offsets = [float((index - grid // 2) * delta) for index in range(grid)]
    results: dict[tuple[int, int], dict[str, Any]] = {}

    for idx_i, offset_i in enumerate(offsets):
        for idx_j, offset_j in enumerate(offsets):
            candidate = dict(center)
            candidate[axis_i] = float(center[axis_i] + offset_i)
            candidate[axis_j] = float(center[axis_j] + offset_j)
            base_prob, base_theta, psi_center = _initial_state(substrate, candidate, config)
            omega_val = _curvature_probe(
                substrate,
                config,
                candidate,
                axes,
                base_prob,
                base_theta,
                psi_center,
                delta=delta,
            )
            results[(idx_i, idx_j)] = {
                "center": candidate,
                "omega": omega_val,
                "state": (base_prob, base_theta),
            }

    def gradient_and_consistency(index_i: int, index_j: int, omega_value: float) -> tuple[float, float]:
        neighbors: list[float] = []
        signs: list[int] = []
        base_sign = 0
        if math.isfinite(omega_value):
            if omega_value > 1e-9:
                base_sign = 1
            elif omega_value < -1e-9:
                base_sign = -1
        for delta_i, delta_j in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            key = (index_i + delta_i, index_j + delta_j)
            if key not in results:
                continue
            neighbor_omega = float(results[key]["omega"])
            if math.isfinite(omega_value) and math.isfinite(neighbor_omega):
                neighbors.append(abs(omega_value - neighbor_omega))
            if math.isfinite(neighbor_omega):
                if neighbor_omega > 1e-9:
                    signs.append(1)
                elif neighbor_omega < -1e-9:
                    signs.append(-1)
                else:
                    signs.append(0)
        if neighbors:
            grad = float(sum(neighbors) / len(neighbors))
        else:
            grad = 0.0
        if not signs:
            return grad, 1.0
        if base_sign == 0:
            consistency = sum(1 for sign in signs if sign == 0) / len(signs)
        else:
            consistency = sum(1 for sign in signs if sign == base_sign or sign == 0) / len(signs)
        return grad, float(consistency)

    best_key = None
    best_score = -float("inf")
    best_entry: dict[str, Any] | None = None
    for (idx_i, idx_j), entry in results.items():
        omega_value = float(entry["omega"])
        if not math.isfinite(omega_value):
            continue
        grad, consistency = gradient_and_consistency(idx_i, idx_j, omega_value)
        score = abs(omega_value) * consistency / (1.0 + grad)
        entry["gradient"] = grad
        entry["consistency"] = consistency
        entry["score"] = score
        if score > best_score:
            best_score = score
            best_key = (idx_i, idx_j)
            best_entry = entry

    if best_entry is None or best_key is None:
        # Fall back to the supplied centre if no finite candidates were available.
        fallback_prob, fallback_theta, _ = _initial_state(substrate, center, config)
        return (
            dict(center),
            (fallback_prob, fallback_theta),
            {
                "selected": dict(center),
                "omega": float("nan"),
                "score": float("nan"),
            },
        )

    selected_center = dict(best_entry["center"])
    base_prob_arr, base_theta_arr = best_entry["state"]
    scan_meta = {
        "selected": selected_center,
        "omega": float(best_entry["omega"]),
        "score": float(best_entry.get("score", float("nan"))),
        "gradient": float(best_entry.get("gradient", float("nan"))),
        "consistency": float(best_entry.get("consistency", float("nan"))),
    }
    return selected_center, (base_prob_arr, base_theta_arr), scan_meta


def _loop_steps_for_extent(extent: RectExtent, base_steps: int) -> int:
    magnitude = extent.max_abs()
    if magnitude == 0.0:
        raise ValueError("extent must be non-zero to form a loop region")
    scale = max(int(round(magnitude / 0.02)), 1)
    return max(16, base_steps * scale)


def _extract_readout(
    record_steps: int, readouts: Sequence[Mapping[str, Any]]
) -> tuple[float, list[float], bool]:
    phi_value = 0.0
    memory: list[float] = []
    missing = True
    for entry in readouts:
        if not isinstance(entry, Mapping):
            continue
        if int(entry.get("step", -1)) != record_steps:
            continue
        missing_flag = bool(entry.get("phi_flux_missing_tiles"))
        try:
            phi_raw = float(entry.get("phi_flux", float("nan")))
        except (TypeError, ValueError):
            phi_raw = float("nan")
        memory_seq = entry.get("memory")
        if isinstance(memory_seq, Sequence) and not isinstance(memory_seq, (str, bytes)):
            try:
                memory = [float(val) for val in memory_seq]
            except (TypeError, ValueError):
                memory = []
        missing = missing_flag or not math.isfinite(phi_raw)
        if not missing:
            phi_value = float(phi_raw)
        break
    if missing:
        return 0.0, memory, True
    return phi_value, memory, False


def _edge_axis(delta: Mapping[str, float], axes: tuple[str, str]) -> str | None:
    delta_i = float(delta.get(axes[0], 0.0))
    delta_j = float(delta.get(axes[1], 0.0))
    abs_i, abs_j = abs(delta_i), abs(delta_j)
    if abs_i > abs_j and abs_i > 0.0:
        return axes[0]
    if abs_j > abs_i and abs_j > 0.0:
        return axes[1]
    if abs_i > 0.0 and abs_j == abs_i:
        return axes[0]
    if abs_j > 0.0 and abs_i == abs_j:
        return axes[1]
    return None


def _fs_edge_statistics(
    record: "RunRecord",
    axes: tuple[str, str],
    guard_meta: Mapping[str, Any],
) -> tuple[dict[str, int], dict[str, int], dict[str, float]]:
    counts = {axis: 0 for axis in axes}
    exceedances = {axis: 0 for axis in axes}
    maxima = {axis: 0.0 for axis in axes}

    guard_limit: float | None = None
    if bool(guard_meta.get("enabled", False)):
        try:
            guard_limit = float(guard_meta.get("threshold"))
        except (TypeError, ValueError):
            guard_limit = None
        if guard_limit is None or not math.isfinite(guard_limit) or guard_limit <= 0.0:
            try:
                guard_limit = float(guard_meta.get("boundary"))
            except (TypeError, ValueError):
                guard_limit = None
        if guard_limit is not None and (not math.isfinite(guard_limit) or guard_limit <= 0.0):
            guard_limit = None

    for index, fs_step in enumerate(record.fs_steps):
        try:
            delta = record.delta_lambda[index]
        except IndexError:  # pragma: no cover - defensive guard
            delta = {}
        axis = _edge_axis(delta, axes)
        if axis is None:
            continue
        counts[axis] += 1
        if math.isfinite(fs_step):
            maxima[axis] = max(maxima[axis], float(fs_step))
            if guard_limit is not None and fs_step > guard_limit:
                exceedances[axis] += 1

    return counts, exceedances, maxima


def _run_loop_once(
    substrate: GraphSubstrate,
    config: RunConfig,
    base_prob: np.ndarray,
    base_theta: np.ndarray,
    center: Mapping[str, float],
    axes: tuple[str, str],
    extent: RectExtent,
    orientation: str,
    seed: int,
    *,
    steps: int,
    axis_bounds: Mapping[str, tuple[float | None, float | None]] | None = None,
    budget: TimeBudgetTracker | None = None,
) -> OrientationRun:
    center_dict, adjusted_extent = _clamp_loop_region(center, extent, axes, axis_bounds)
    extent_dict = adjusted_extent.as_dict()

    delta_frac = dict(getattr(config, "delta_frac", {}))
    for knob in extent_dict:
        # Ensure the scheduler recognises loop axes even when we rely on
        # delta_lambda fallbacks for their magnitudes.
        delta_frac.setdefault(knob, 0.0)
    config_local = replace(config, delta_frac=delta_frac)

    path = ParameterPath(
        kind="rectangle",
        center=center_dict,
        extents=extent_dict,
        steps=steps,
        orientation=orientation,
        axes=axes,
    )

    init_state = LayersState(pQ=base_prob.copy(), theta=base_theta.copy())
    start_time = time.perf_counter()
    record = run_parameter_loop(substrate, init_state, path, config_local, seed=seed)
    duration = time.perf_counter() - start_time
    if budget is not None:
        budget.consume(duration)

    area = float(sum(float(delta) for delta in record.delta_area))
    phi_flux, memory, phi_missing = _extract_readout(path.steps, record.readouts)
    if not phi_missing and area != 0.0 and math.isfinite(phi_flux):
        kappa = phi_flux / area
    else:
        kappa = float("nan")

    guard_meta = {}
    if isinstance(record.meta, Mapping):
        guard_meta = record.meta.get("fs_step_guard", {}) or {}
    try:
        fs_p95 = float(guard_meta.get("p95", float("nan")))
    except (TypeError, ValueError):
        fs_p95 = float("nan")
    early_abort = bool(guard_meta.get("early_abort", False))
    if early_abort:
        fs_p95 = float("nan")
    guard_exceeded = bool(guard_meta.get("boundary_exceeded", False) or early_abort)

    edge_counts, edge_exceedances, edge_max = _fs_edge_statistics(
        record,
        axes,
        guard_meta,
    )

    return OrientationRun(
        orientation=orientation,
        extents=adjusted_extent,
        steps=steps,
        area=area,
        phi_flux=phi_flux,
        phi_missing=phi_missing,
        kappa=kappa,
        memory=memory,
        fs_p95=fs_p95,
        fs_guard_exceeded=guard_exceeded,
        fs_edge_counts=edge_counts,
        fs_edge_exceedances=edge_exceedances,
        fs_edge_max=edge_max,
        duration=float(duration),
    )


def _run_loop(
    substrate: GraphSubstrate,
    config: RunConfig,
    base_prob: np.ndarray,
    base_theta: np.ndarray,
    center: Mapping[str, float],
    axes: tuple[str, str],
    extent: RectExtent,
    orientation: str,
    seed: int,
    base_steps: int,
    *,
    target_fs: float | None,
    pilot_frac: float | None,
    axis_bounds: Mapping[str, tuple[float | None, float | None]] | None = None,
    budget: TimeBudgetTracker | None = None,
) -> OrientationRun:
    _, extent_effective = _clamp_loop_region(center, extent, axes, axis_bounds)
    baseline_steps = _loop_steps_for_extent(extent_effective, base_steps)
    final_steps = baseline_steps
    pilot_result: OrientationRun | None = None
    budget_limited = False

    initial_remaining = budget.remaining() if budget is not None else None
    if initial_remaining is not None and initial_remaining <= 0.0:
        final_steps = max(16, min(final_steps, 16))
        budget_limited = True

    if (
        pilot_frac is not None
        and pilot_frac > 0.0
        and target_fs is not None
        and target_fs > 0.0
        and baseline_steps > 16
        and (initial_remaining is None or initial_remaining > 0.0)
    ):
        pilot_steps = int(pilot_frac * baseline_steps)
        pilot_steps = max(16, pilot_steps)
        pilot_steps = max(128, pilot_steps)
        pilot_steps = min(baseline_steps, pilot_steps)

        if pilot_steps < baseline_steps:
            pilot_result = _run_loop_once(
                substrate,
                config,
                base_prob,
                base_theta,
                center,
                axes,
                extent,
                orientation,
                seed,
                steps=pilot_steps,
                axis_bounds=axis_bounds,
                budget=budget,
            )
            fs_p95_pilot = pilot_result.fs_p95
            if math.isfinite(fs_p95_pilot) and fs_p95_pilot > 0.0 and not pilot_result.fs_guard_exceeded:
                safety_margin = 1.25
                predicted = int(math.ceil(pilot_steps * (fs_p95_pilot / float(target_fs)) * safety_margin))
                min_steps = 16
                max_steps = baseline_steps
                final_steps = max(min_steps, min(max_steps, predicted))
            else:
                final_steps = baseline_steps

            if budget is not None:
                remaining = budget.remaining()
                per_step = (
                    pilot_result.duration / float(max(pilot_result.steps, 1))
                    if pilot_result.steps > 0
                    else None
                )
                if remaining is not None and remaining > 0.0 and per_step and per_step > 0.0:
                    allowed_steps = int(math.floor(remaining / per_step))
                    if allowed_steps < final_steps:
                        final_steps = max(16, allowed_steps)
                        budget_limited = True

            if final_steps <= pilot_result.steps:
                if budget_limited:
                    return replace(pilot_result, budget_limited=True)
                return pilot_result

    if pilot_result is not None and pilot_result.steps == final_steps:
        return pilot_result

    result = _run_loop_once(
        substrate,
        config,
        base_prob,
        base_theta,
        center,
        axes,
        extent,
        orientation,
        seed,
        steps=final_steps,
        axis_bounds=axis_bounds,
        budget=budget,
    )

    if budget_limited:
        result = replace(result, budget_limited=True)

    return result


def _auto_calibrate_extent(
    substrate: GraphSubstrate,
    config: RunConfig,
    base_prob: np.ndarray,
    base_theta: np.ndarray,
    center: Mapping[str, float],
    axes: tuple[str, str],
    *,
    base_steps: int,
    extent_bracket: tuple[float, float],
    target_fs: float,
    pilot_frac: float,
    fs_margin: float,
    max_iters: int,
    seed: int,
    axis_bounds: Mapping[str, tuple[float | None, float | None]] | None = None,
    budget: TimeBudgetTracker | None = None,
) -> AutoExtentResult:
    lower, upper = float(extent_bracket[0]), float(extent_bracket[1])
    if not math.isfinite(lower) or not math.isfinite(upper):
        raise ValueError("extent bracket must contain finite values")
    if lower <= 0.0 or upper <= 0.0:
        raise ValueError("extent bracket must be positive")
    if lower >= upper:
        raise ValueError("extent bracket lower bound must be smaller than upper bound")
    if not math.isfinite(target_fs) or target_fs <= 0.0:
        raise ValueError("target-fs must be a positive finite value when auto-extent is enabled")
    fs_margin = max(0.0, float(fs_margin))
    pilot_frac = float(pilot_frac) if math.isfinite(float(pilot_frac)) else 0.0
    if pilot_frac <= 0.0:
        pilot_frac = 0.125
    max_iters = max(1, int(max_iters))

    extent = RectExtent.from_scalar(axes, math.sqrt(lower * upper)).clamp(lower=lower, upper=upper)
    decisions: list[AutoExtentDecision] = []
    best_safe: RectExtent | None = None
    accepted_flag = False

    lower_threshold = target_fs * (1.0 - fs_margin)
    upper_threshold = target_fs * (1.0 + fs_margin)

    sqrt_two = math.sqrt(2.0)
    inv_sqrt_two = 1.0 / sqrt_two

    for iteration in range(1, max_iters + 1):
        steps_full = _loop_steps_for_extent(extent, base_steps)
        pilot_steps = int(pilot_frac * steps_full)
        pilot_steps = max(128, pilot_steps)
        pilot_steps = min(steps_full, pilot_steps)

        if budget is not None:
            remaining = budget.remaining()
            if remaining is not None and remaining <= 0.0:
                decisions.append(
                    AutoExtentDecision(
                        iteration=iteration,
                        extents=extent,
                        pilot_steps=pilot_steps,
                        steps=steps_full,
                        fs_p95=float("nan"),
                        fs_guard_exceeded=False,
                        fs_edge_exceedances={axis: 0 for axis in axes},
                        decision="budget_exhausted",
                    )
                )
                break

        pilot_run = _run_loop_once(
            substrate,
            config,
            base_prob,
            base_theta,
            center,
            axes,
            extent,
            "CCW",
            seed,
            steps=pilot_steps,
            axis_bounds=axis_bounds,
            budget=budget,
        )
        fs95 = pilot_run.fs_p95
        guard_exceeded = pilot_run.fs_guard_exceeded
        edge_exceedances = {axis: int(pilot_run.fs_edge_exceedances.get(axis, 0)) for axis in axes}

        if not math.isfinite(fs95):
            guard_exceeded = True
        shrink_axes = {axis for axis, count in edge_exceedances.items() if count > 0}
        if guard_exceeded:
            shrink_axes.update(axes)

        within_window = (
            math.isfinite(fs95)
            and lower_threshold <= fs95 <= upper_threshold
            and not guard_exceeded
            and not shrink_axes
        )
        safe_extent = (
            math.isfinite(fs95) and fs95 <= upper_threshold and not guard_exceeded and not shrink_axes
        )
        if safe_extent:
            best_safe = extent

        decision_label: str
        grow_axes: set[str] = set()
        if within_window:
            decision_label = "accept"
        else:
            if not shrink_axes and math.isfinite(fs95) and fs95 > upper_threshold:
                shrink_axes.update(axes)
            if not shrink_axes and math.isfinite(fs95) and fs95 < lower_threshold:
                grow_axes.update(axes)

            if shrink_axes:
                if shrink_axes == set(axes):
                    decision_label = "shrink_all"
                else:
                    ordered = ",".join(str(axis) for axis in shrink_axes)
                    decision_label = f"shrink[{ordered}]"
            elif grow_axes:
                decision_label = "expand"
            else:
                decision_label = "hold"

        decisions.append(
            AutoExtentDecision(
                iteration=iteration,
                extents=extent,
                pilot_steps=pilot_steps,
                steps=steps_full,
                fs_p95=float(fs95) if math.isfinite(fs95) else float("nan"),
                fs_guard_exceeded=guard_exceeded,
                fs_edge_exceedances=edge_exceedances,
                decision=decision_label,
            )
        )

        if within_window:
            accepted_flag = True
            best_safe = extent
            break

        new_extent = extent
        changed = False
        if shrink_axes:
            for axis in axes:
                if axis not in shrink_axes:
                    continue
                current_val = extent.axis_value(axis)
                scaled = max(lower, current_val * inv_sqrt_two)
                if not math.isclose(scaled, current_val, rel_tol=1e-12, abs_tol=1e-12):
                    changed = True
                new_extent = new_extent.replace(axis=axis, value=scaled)
        elif grow_axes:
            for axis in axes:
                if axis not in grow_axes:
                    continue
                current_val = extent.axis_value(axis)
                scaled = min(upper, current_val * sqrt_two)
                if not math.isclose(scaled, current_val, rel_tol=1e-12, abs_tol=1e-12):
                    changed = True
                new_extent = new_extent.replace(axis=axis, value=scaled)

        new_extent = new_extent.clamp(lower=lower, upper=upper)

        if not changed or new_extent.is_close(extent):
            break

        extent = new_extent

    final_extent = best_safe if best_safe is not None else extent

    return AutoExtentResult(
        extent=final_extent,
        accepted=accepted_flag,
        iterations=len(decisions),
        decisions=decisions,
    )


def evaluate_hotspot(
    index: int,
    spec: HotspotSpec,
    *,
    substrate: GraphSubstrate,
    config: RunConfig,
    axes: tuple[str, str],
    extents: Sequence[RectExtent],
    seed: int,
    micro_scan: bool,
    base_steps: int,
    target_fs: float | None,
    pilot_frac: float | None,
    auto_extent: bool,
    extent_bracket: tuple[float, float] | None,
    fs_margin: float,
    max_extent_iters: int,
    budget: TimeBudgetTracker | None = None,
) -> HotspotSummary:
    center = dict(spec.center)
    axis_bounds = _axis_bounds_from_metadata(spec.metadata, axes)
    if micro_scan:
        center, state_pair, scan_meta = _micro_scan_candidates(
            substrate,
            config,
            center,
            axes,
            delta=0.01,
        )
        spec.center = center
        meta = spec.metadata.setdefault("micro_scan", {})
        meta.update(scan_meta)
        base_prob, base_theta = state_pair
    else:
        base_prob, base_theta, _ = _initial_state(substrate, center, config)
        spec.center = center
    extents_to_run = list(extents)
    if auto_extent:
        if target_fs is None:
            raise ValueError("target-fs must be provided when auto-extent is enabled")
        if extent_bracket is None:
            raise ValueError("extent-bracket must be provided when auto-extent is enabled")
        auto_result = _auto_calibrate_extent(
            substrate,
            config,
            base_prob,
            base_theta,
            spec.center,
            axes,
            base_steps=base_steps,
            extent_bracket=extent_bracket,
            target_fs=float(target_fs),
            pilot_frac=float(pilot_frac) if pilot_frac is not None else 0.0,
            fs_margin=float(fs_margin),
            max_iters=int(max_extent_iters),
            seed=seed,
            axis_bounds=axis_bounds,
            budget=budget,
        )
        if not extents_to_run:
            extents_to_run = [auto_result.extent]
        else:
            if not any(auto_result.extent.is_close(value) for value in extents_to_run):
                extents_to_run.append(auto_result.extent)
            extents_to_run.sort(key=lambda item: item.max_abs())
        meta = spec.metadata.setdefault("auto_extent", {})
        meta.update(
            {
                "accepted": bool(auto_result.accepted),
                "extent": auto_result.extent.as_dict(),
                "iterations": int(auto_result.iterations),
                "bracket": {"min": float(extent_bracket[0]), "max": float(extent_bracket[1])},
                "target_fs": float(target_fs),
                "fs_margin": float(fs_margin),
                "decisions": [
                    {
                        "iteration": decision.iteration,
                        "extents": decision.extents.as_dict(),
                        "pilot_steps": decision.pilot_steps,
                        "steps": decision.steps,
                        "fs_p95": decision.fs_p95,
                        "fs_guard_exceeded": decision.fs_guard_exceeded,
                        "fs_edge_exceedances": decision.fs_edge_exceedances,
                        "decision": decision.decision,
                    }
                    for decision in auto_result.decisions
                ],
            }
        )
    elif not extents_to_run:
        raise ValueError("at least one extent must be provided")

    summaries: list[ExtentSummary] = []
    for extent in extents_to_run:
        ccw = _run_loop(
            substrate,
            config,
            base_prob,
            base_theta,
            spec.center,
            axes,
            extent,
            "CCW",
            seed,
            base_steps,
            target_fs=None if auto_extent else target_fs,
            pilot_frac=pilot_frac if not auto_extent else None,
            axis_bounds=axis_bounds,
            budget=budget,
        )
        cw = _run_loop(
            substrate,
            config,
            base_prob,
            base_theta,
            spec.center,
            axes,
            extent,
            "CW",
            seed,
            base_steps,
            target_fs=None if auto_extent else target_fs,
            pilot_frac=pilot_frac if not auto_extent else None,
            axis_bounds=axis_bounds,
            budget=budget,
        )
        area_flip = _relative_flip_error(ccw.area, cw.area)
        if ccw.phi_missing or cw.phi_missing:
            phi_flip = float("nan")
        else:
            phi_flip = _relative_flip_error(ccw.phi_flux, cw.phi_flux)
        summaries.append(
            ExtentSummary(
                extents=extent,
                ccw=ccw,
                cw=cw,
                area_flip_error=area_flip,
                phi_flip_error=phi_flip,
            )
        )

    kappa_errors: list[float] = []
    if summaries:
        base_kappa = summaries[0].ccw.kappa
        for summary in summaries[1:]:
            kappa_errors.append(_relative_change(base_kappa, summary.ccw.kappa))

    return HotspotSummary(index=index, spec=spec, extents=summaries, kappa_scale_errors=kappa_errors)


def _format_memory(memory: Sequence[float]) -> str:
    if not memory:
        return "[]"
    return "[" + ", ".join(f"{value:.3f}" for value in memory) + "]"


def _format_extent(extent: RectExtent) -> str:
    axis_i, axis_j = extent.axes
    return f"{axis_i}={extent.axis_value(axis_i):+.4f}, {axis_j}={extent.axis_value(axis_j):+.4f}"


def render_summary(results: Sequence[HotspotSummary]) -> None:
    for summary in results:
        spec = summary.spec
        omega_text = "nan" if not math.isfinite(spec.omega_abs) else f"{spec.omega_abs:.6f}"
        center_repr = ", ".join(f"{axis}={spec.center[axis]:+.4f}" for axis in spec.center)
        print(f"Hotspot #{summary.index + 1}: {center_repr} (|Ω|={omega_text})")
        for extent_summary in summary.extents:
            extent = extent_summary.extents
            ccw = extent_summary.ccw
            cw = extent_summary.cw
            print(f"  extent=({_format_extent(extent)})")
            ccw_flag = " ⚠️ missing Ω" if ccw.phi_missing else ""
            cw_flag = " ⚠️ missing Ω" if cw.phi_missing else ""
            print(
                "    CCW: R={:+.6f}, Φ={:+.6f}{}, κ₁={:+.6f}, χ={}".format(
                    ccw.area,
                    ccw.phi_flux,
                    ccw_flag,
                    ccw.kappa,
                    _format_memory(ccw.memory),
                )
            )
            print(
                "           FS p95={:.3f} rad, guard_exceeded={}".format(
                    ccw.fs_p95 if math.isfinite(ccw.fs_p95) else float("nan"),
                    ccw.fs_guard_exceeded,
                )
            )
            print(
                "           steps={}, t={:.2f}s, budget_limited={}".format(
                    int(ccw.steps),
                    ccw.duration,
                    ccw.budget_limited,
                )
            )
            print(
                "    CW : R={:+.6f}, Φ={:+.6f}{}, κ₁={:+.6f}, χ={}".format(
                    cw.area,
                    cw.phi_flux,
                    cw_flag,
                    cw.kappa,
                    _format_memory(cw.memory),
                )
            )
            print(
                "           FS p95={:.3f} rad, guard_exceeded={}".format(
                    cw.fs_p95 if math.isfinite(cw.fs_p95) else float("nan"),
                    cw.fs_guard_exceeded,
                )
            )
            print(
                "           steps={}, t={:.2f}s, budget_limited={}".format(
                    int(cw.steps),
                    cw.duration,
                    cw.budget_limited,
                )
            )
            flip_area_pct = (
                extent_summary.area_flip_error * 100.0
                if math.isfinite(extent_summary.area_flip_error)
                else float("nan")
            )
            flip_phi_pct = (
                extent_summary.phi_flip_error * 100.0
                if math.isfinite(extent_summary.phi_flip_error)
                else float("nan")
            )
            print(f"    flip error: area={flip_area_pct:.2f}%  phi={flip_phi_pct:.2f}%")
        if summary.kappa_scale_errors:
            errors_pct = ", ".join(
                f"{err * 100.0:.2f}%" if math.isfinite(err) else "nan" for err in summary.kappa_scale_errors
            )
            print(f"  κ₁ scale change: {errors_pct}")
        print()


def evaluate_acceptance(
    results: Sequence[HotspotSummary],
    *,
    flip_tolerance: float = 0.05,
    kappa_tolerance: float = 0.20,
) -> tuple[bool, list[str]]:
    if len(results) < 3:
        return True, []

    failures: list[str] = []
    for summary in results:
        for extent_summary in summary.extents:
            if (
                math.isfinite(extent_summary.area_flip_error)
                and extent_summary.area_flip_error > flip_tolerance
            ):
                failures.append(
                    (
                        f"Hotspot {summary.index + 1} extent ({_format_extent(extent_summary.extents)}): "
                        f"area flip error {extent_summary.area_flip_error:.3f}"
                    )
                )
            if extent_summary.ccw.budget_limited or extent_summary.cw.budget_limited:
                failures.append(
                    (
                        f"Hotspot {summary.index + 1} extent ({_format_extent(extent_summary.extents)}): "
                        "loop truncated by time budget"
                    )
                )
            if (
                math.isfinite(extent_summary.phi_flip_error)
                and extent_summary.phi_flip_error > flip_tolerance
            ):
                failures.append(
                    (
                        f"Hotspot {summary.index + 1} extent ({_format_extent(extent_summary.extents)}): "
                        f"phi flip error {extent_summary.phi_flip_error:.3f}"
                    )
                )
        for idx, error in enumerate(summary.kappa_scale_errors, start=1):
            if math.isfinite(error) and error > kappa_tolerance:
                failures.append(f"Hotspot {summary.index + 1} κ₁ change #{idx} = {error:.3f}")

    return not failures, failures


def _float_or_none(value: Any) -> float | None:
    if isinstance(value, numbers.Real):
        numeric = float(value)
        return numeric if math.isfinite(numeric) else None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    return numeric if math.isfinite(numeric) else None


def _sanitize_for_json(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _sanitize_for_json(val) for key, val in value.items()}
    if isinstance(value, (list, tuple)):
        return [_sanitize_for_json(item) for item in value]
    if isinstance(value, numbers.Real):
        numeric = float(value)
        return numeric if math.isfinite(numeric) else None
    return value


def _rect_extent_to_json(extent: RectExtent) -> dict[str, Any]:
    return {
        "axes": [extent.axes[0], extent.axes[1]],
        "values": [float(extent.values[0]), float(extent.values[1])],
        "map": extent.as_dict(),
    }


def _orientation_run_to_json(run: OrientationRun) -> dict[str, Any]:
    return {
        "orientation": run.orientation,
        "steps": int(run.steps),
        "area": _float_or_none(run.area),
        "phi": _float_or_none(run.phi_flux),
        "phi_missing": bool(run.phi_missing),
        "kappa": _float_or_none(run.kappa),
        "memory": [_float_or_none(value) for value in run.memory],
        "fs_p95": _float_or_none(run.fs_p95),
        "fs_guard_exceeded": bool(run.fs_guard_exceeded),
        "fs_edge_counts": {axis: int(count) for axis, count in run.fs_edge_counts.items()},
        "fs_edge_exceedances": {axis: int(count) for axis, count in run.fs_edge_exceedances.items()},
        "fs_edge_max": {axis: _float_or_none(value) for axis, value in run.fs_edge_max.items()},
        "duration": _float_or_none(run.duration),
        "budget_limited": bool(run.budget_limited),
    }


def _extent_summary_to_json(summary: ExtentSummary) -> dict[str, Any]:
    return {
        "extents": _rect_extent_to_json(summary.extents),
        "ccw": _orientation_run_to_json(summary.ccw),
        "cw": _orientation_run_to_json(summary.cw),
        "area_flip_error": _float_or_none(summary.area_flip_error),
        "phi_flip_error": _float_or_none(summary.phi_flip_error),
    }


def _hotspot_summary_to_json(summary: HotspotSummary) -> dict[str, Any]:
    meta = _sanitize_for_json(summary.spec.metadata)
    omega_abs = _float_or_none(summary.spec.omega_abs)
    return {
        "index": int(summary.index),
        "center": {axis: float(value) for axis, value in summary.spec.center.items()},
        "omega_abs": omega_abs,
        "metadata": meta,
        "extents": [_extent_summary_to_json(extent) for extent in summary.extents],
        "kappa_scale_errors": [_float_or_none(value) for value in summary.kappa_scale_errors],
    }


def _build_summary_payload(
    *,
    axes: tuple[str, str],
    graph: Mapping[str, Any] | str,
    graph_descriptor: Mapping[str, Any] | str | None = None,
    fs_guard: float | None,
    config: RunConfig,
    base_steps: int,
    seed: int,
    limit: int | None,
    micro_scan: bool,
    auto_extent: bool,
    target_fs: float | None,
    pilot_frac: float | None,
    extent_bracket: tuple[float, float] | None,
    fs_margin: float,
    max_extent_iters: int,
    extents_input: Sequence[RectExtent],
    hotspots_path: Path,
    results: Sequence[HotspotSummary],
    accepted: bool,
    failures: Sequence[str],
    time_budget: float | None,
    time_consumed: float | None,
) -> dict[str, Any]:
    timestamp = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
    extent_bracket_payload = (
        {"min": float(extent_bracket[0]), "max": float(extent_bracket[1])}
        if extent_bracket is not None
        else None
    )
    return {
        "schema_version": 1,
        "created_at": timestamp,
        "axes": [axes[0], axes[1]],
        "graph": _normalise_graph_descriptor(
            graph_descriptor if graph_descriptor is not None else graph,
            fallback_name=(
                str(graph)
                if isinstance(graph, str)
                else str(getattr(graph, "get", lambda *_: "")("identifier", ""))
            ),
            fallback_seed=seed,
        )
        or _graph_descriptor_for_summary(
            str(graph) if isinstance(graph, str) else "",
            seed=seed,
        ),
        "fs_guard": _float_or_none(fs_guard),
        "neighbor_settle_steps": int(getattr(config, "neighbor_settle_steps", 0)),
        "base_steps": int(base_steps),
        "seed": int(seed),
        "limit": int(limit) if limit is not None else None,
        "micro_scan": bool(micro_scan),
        "auto_extent": {
            "enabled": bool(auto_extent),
            "target_fs": _float_or_none(target_fs),
            "pilot_frac": _float_or_none(pilot_frac),
            "fs_margin": float(fs_margin),
            "max_iters": int(max_extent_iters),
            "extent_bracket": extent_bracket_payload,
        },
        "extents_requested": [_rect_extent_to_json(extent) for extent in extents_input],
        "hotspots_path": str(hotspots_path),
        "hotspots": [_hotspot_summary_to_json(summary) for summary in results],
        "accepted": bool(accepted),
        "failures": [str(message) for message in failures],
        "time_budget_seconds": _float_or_none(time_budget),
        "time_consumed_seconds": _float_or_none(time_consumed),
    }


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Loop validation at curvature hotspots")
    parser.add_argument("--hotspots", type=Path, required=True, help="Path to the top_omega_tiles.json file")
    parser.add_argument(
        "--extents",
        type=float,
        nargs="+",
        required=False,
        help="Loop extents to evaluate (applied to both axes)",
    )
    parser.add_argument(
        "--axes",
        nargs=2,
        metavar=("AXIS_I", "AXIS_J"),
        default=("tau", "zeta"),
        help="Axes names to use when constructing the loop rectangle",
    )
    parser.add_argument(
        "--graph",
        default="ring3_hetero",
        help="Graph substrate to use for the validation loop (default: ring3_hetero)",
    )
    parser.add_argument(
        "--fs-guard",
        type=float,
        default=None,
        help="Optional FS guard threshold in radians (enables CLI enforcement when set)",
    )
    parser.add_argument(
        "--base-steps",
        type=int,
        default=2048,
        help="Baseline integration steps for a 0.02-extent loop; scaled up for larger loops.",
    )
    parser.add_argument(
        "--target-fs",
        type=float,
        default=0.10,
        help="Target FS guard p95 threshold in radians for adaptive step selection.",
    )
    parser.add_argument(
        "--pilot-frac",
        type=float,
        default=0.125,
        help="Fraction of baseline steps to use for the pilot run (set to 0 to disable).",
    )
    parser.add_argument(
        "--auto-extent",
        type=_parse_bool,
        default=False,
        metavar="true|false",
        help="Enable auto-tuning of the loop extent within the provided bracket.",
    )
    parser.add_argument(
        "--extent-bracket",
        type=float,
        nargs=2,
        default=(5e-4, 2e-2),
        metavar=("E_MIN", "E_MAX"),
        help="Search range for auto-extent calibration (ignored when auto-extent is disabled).",
    )
    parser.add_argument(
        "--fs-margin",
        type=float,
        default=0.05,
        help="Relative tolerance when comparing pilot FS against the target during auto-extent.",
    )
    parser.add_argument(
        "--max-extent-iters",
        type=int,
        default=6,
        help="Maximum number of auto-extent iterations before falling back to the best safe loop.",
    )
    parser.add_argument(
        "--time-budget",
        type=float,
        default=None,
        help=(
            "Optional wall-clock budget in seconds used to throttle loop resolution and "
            "terminate auto-calibration when exhausted."
        ),
    )
    parser.add_argument(
        "--micro-scan",
        type=_parse_bool,
        default=False,
        metavar="true|false",
        help="Enable the 5×5 micro-scan refinement around each hotspot centre",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional limit on the number of hotspots to evaluate",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=13,
        help="Seed controlling stochastic components of the loop integrator",
    )
    parser.add_argument(
        "--readout-target",
        type=int,
        default=0,
        help="Node index selected by the one-hot susceptibility vector",
    )
    parser.add_argument(
        "--neighbor-settle-steps",
        type=int,
        default=None,
        help="Override the settle steps used when relaxing neighbour samples",
    )
    parser.add_argument(
        "--adapt-levels",
        type=int,
        default=None,
        help="Maximum depth for adaptive curvature refinement",
    )
    parser.add_argument(
        "--save-summary",
        type=Path,
        default=None,
        help="Optional path where a structured Phase 3 summary will be written",
    )
    return parser.parse_args(argv)


def _parse_bool(text: str) -> bool:
    value = str(text).strip().lower()
    if value in {"true", "t", "1", "yes", "y"}:
        return True
    if value in {"false", "f", "0", "no", "n"}:
        return False
    raise argparse.ArgumentTypeError("expected a boolean flag (true|false)")


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    axes = (str(args.axes[0]), str(args.axes[1]))

    extents_input: list[RectExtent] = []
    if args.extents is not None:
        scalar_extents = sorted((float(value) for value in args.extents), key=abs)
        extents_input = [RectExtent.from_scalar(axes, value) for value in scalar_extents]

    auto_extent_enabled = bool(args.auto_extent)
    if not auto_extent_enabled and not extents_input:
        raise ValueError("at least one extent must be provided when auto-extent is disabled")

    extent_bracket: tuple[float, float] | None = None
    if args.extent_bracket is not None:
        extent_bracket = (float(args.extent_bracket[0]), float(args.extent_bracket[1]))

    hotspots = load_hotspots(args.hotspots, axes)
    if args.limit is not None:
        hotspots = hotspots[: max(int(args.limit), 0)]
    if not hotspots:
        raise ValueError("no hotspots available for evaluation")

    seed_value = int(args.seed)
    metadata_descriptor = _select_metadata_descriptor(hotspots)
    graph_descriptor = _prepare_graph_descriptor(
        str(args.graph),
        seed=seed_value,
        descriptor=metadata_descriptor,
    )
    substrate = _build_substrate_from_descriptor(graph_descriptor)
    config = _default_run_config(int(args.readout_target))
    if args.fs_guard is not None:
        config.fs_step_guard = {
            "threshold": float(args.fs_guard),
            "window": 64,
            "throttle": 0.9,
        }
    if args.neighbor_settle_steps is not None:
        if int(args.neighbor_settle_steps) <= 0:
            raise ValueError("neighbor-settle-steps must be positive")
        config.neighbor_settle_steps = int(args.neighbor_settle_steps)
    if args.adapt_levels is not None:
        if int(args.adapt_levels) <= 0:
            raise ValueError("adapt-levels must be positive")
        config.adapt_levels = int(args.adapt_levels)

    micro_scan_enabled = bool(args.micro_scan)
    target_fs_value = float(args.target_fs) if args.target_fs is not None else None
    pilot_frac_value = float(args.pilot_frac) if args.pilot_frac is not None else None
    fs_margin_value = float(args.fs_margin)
    max_iters_value = int(args.max_extent_iters)

    budget_tracker = TimeBudgetTracker(args.time_budget)

    results: list[HotspotSummary] = []
    for index, spec in enumerate(hotspots):
        summary = evaluate_hotspot(
            index,
            spec,
            substrate=substrate,
            config=config,
            axes=axes,
            extents=extents_input,
            seed=seed_value,
            micro_scan=micro_scan_enabled,
            base_steps=int(args.base_steps),
            target_fs=target_fs_value,
            pilot_frac=pilot_frac_value,
            auto_extent=auto_extent_enabled,
            extent_bracket=extent_bracket if auto_extent_enabled else None,
            fs_margin=fs_margin_value,
            max_extent_iters=max_iters_value,
            budget=budget_tracker,
        )
        results.append(summary)

    render_summary(results)
    accepted, failure_messages = evaluate_acceptance(results)
    if args.save_summary is not None:
        summary_path = Path(args.save_summary)
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        payload = _build_summary_payload(
            axes=axes,
            graph=str(args.graph),
            graph_descriptor=graph_descriptor,
            fs_guard=float(args.fs_guard) if args.fs_guard is not None else None,
            config=config,
            base_steps=int(args.base_steps),
            seed=seed_value,
            limit=int(args.limit) if args.limit is not None else None,
            micro_scan=micro_scan_enabled,
            auto_extent=auto_extent_enabled,
            target_fs=target_fs_value,
            pilot_frac=pilot_frac_value,
            extent_bracket=extent_bracket,
            fs_margin=fs_margin_value,
            max_extent_iters=max_iters_value,
            extents_input=extents_input,
            hotspots_path=Path(args.hotspots),
            results=results,
            accepted=accepted,
            failures=failure_messages,
            time_budget=budget_tracker.total,
            time_consumed=(budget_tracker.consumed if budget_tracker.total is not None else None),
        )
        with summary_path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
    if accepted:
        if len(results) >= 3:
            print("Acceptance criteria satisfied across evaluated hotspots.")
        return 0

    print("Acceptance criteria failed:")
    for message in failure_messages:
        print(f"  - {message}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
