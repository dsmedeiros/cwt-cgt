"""Adiabatic boundary finder across loop step/extent combinations.

This experiment sweeps a rectangular loop in the :math:`(\\tau, \\zeta)` plane
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
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping, Sequence

import networkx as nx
import numpy as np

from cwt.geometry.curvature import curvature_tile
from cwt.geometry.fs_distance import fs_distance
from cwt.geometry.psi import build_psi
from cwt.graph.factories import from_edgelist, ring3_hetero
from cwt.graph.substrate import GraphSubstrate, build_substrate
from cwt.layers.state import LayersState, wrap_angles
from cwt.orchestrator.param_path import ParameterPath

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


# ---------------------------------------------------------------------------
# Synthetic state helpers
# ---------------------------------------------------------------------------


def _synthetic_state(S: GraphSubstrate, tau: float, zeta: float) -> LayersState:
    """Return a smooth, parameter-dependent state for the substrate."""

    N = S.N
    if N == 0:
        return LayersState(pQ=np.zeros((0,), dtype=float), theta=np.zeros((0,), dtype=float))

    idx = np.arange(N, dtype=float)

    base = 1.0 + 0.18 * np.sin(0.7 * tau * (idx + 1)) + 0.12 * np.cos(0.9 * zeta * (idx + 0.5))
    base = np.clip(base, 0.05, None)
    pQ = base / float(base.sum())

    theta = 0.32 * tau * (idx / max(N - 1, 1)) + 0.27 * zeta * np.sin(math.pi * idx / max(N - 1, 1))
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
) -> float:
    tau_edges = _grid_edges(center["tau"], extent["tau"], grid_size)
    zeta_edges = _grid_edges(center["zeta"], extent["zeta"], grid_size)

    psi_cache: dict[tuple[int, int], np.ndarray] = {}

    def psi_at(i: int, j: int) -> np.ndarray:
        key = (i, j)
        if key not in psi_cache:
            state = _synthetic_state(
                S,
                tau=float(tau_edges[i]),
                zeta=float(zeta_edges[j]),
            )
            psi_cache[key] = build_psi(state.pQ, state.theta)
        return psi_cache[key]

    flux = 0.0
    for i in range(grid_size):
        for j in range(grid_size):
            psi0 = psi_at(i, j)
            psi_i = psi_at(i + 1, j)
            psi_ij = psi_at(i + 1, j + 1)
            psi_j = psi_at(i, j + 1)

            delta_tau = float(tau_edges[i + 1] - tau_edges[i])
            delta_zeta = float(zeta_edges[j + 1] - zeta_edges[j])

            omega, _ = curvature_tile(psi0, psi_i, psi_ij, psi_j, delta_tau, delta_zeta)
            flux += float(omega) * delta_tau * delta_zeta

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
                raise ValueError(
                    "CSV substrate artifact must include 'source' and 'target' columns"
                )
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


def _load_substrate_artifact(path: Path) -> GraphSubstrate:
    """Load a substrate artifact from a file or directory."""

    candidate = path.expanduser()
    if not candidate.exists():
        raise FileNotFoundError(f"substrate artifact {candidate} does not exist")

    if candidate.is_file():
        return _load_substrate_file(candidate)

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

    for name in search_order:
        target = candidate / name
        if target.exists():
            return _load_substrate_file(target)

    for child in sorted(candidate.iterdir()):
        if child.is_file():
            try:
                return _load_substrate_file(child)
            except ValueError:
                continue

    raise FileNotFoundError(f"Could not locate a substrate artifact inside {candidate}")


def _run_sample(
    S: GraphSubstrate,
    center: Mapping[str, float],
    extent: float,
    steps: int,
    *,
    grid_size: int,
) -> SampleResult:
    loop = ParameterPath(
        kind="rectangle",
        center=center,
        extents={"tau": extent, "zeta": extent},
        steps=steps,
        orientation="CCW",
        axes=("tau", "zeta"),
    )

    psi_traj: list[np.ndarray] = []
    for idx in range(loop.steps):
        lambda_state, _, _ = loop.step(idx)
        state = _synthetic_state(S, tau=lambda_state["tau"], zeta=lambda_state["zeta"])
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

    flux = _compute_flux(S, center, {"tau": extent, "zeta": extent}, grid_size=grid_size)
    area = 4.0 * abs(extent) * abs(extent)

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


def _parse_center(text: str) -> dict[str, float]:
    center: dict[str, float] = {"tau": 0.0, "zeta": 0.0}
    if not text:
        return center
    parts = [item.strip() for item in text.split(",") if item.strip()]
    for part in parts:
        if "=" not in part:
            raise ValueError(f"malformed centre entry '{part}'")
        key, value = (token.strip() for token in part.split("=", 1))
        if key not in {"tau", "zeta"}:
            raise ValueError(f"unsupported centre knob '{key}'")
        try:
            center[key] = float(value)
        except ValueError as exc:  # pragma: no cover - defensive
            raise ValueError(f"non-numeric centre value '{value}'") from exc
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
    parser = argparse.ArgumentParser(description="Map the adiabatic boundary in τ–ζ space")
    parser.add_argument("--output-dir", type=Path, default=Path("runs/adiabatic_boundary"))
    parser.add_argument("--center", type=str, default="tau=0.8,zeta=0.0")
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
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    args = _parse_args(argv)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    center = _parse_center(str(args.center))
    extent_values = _parse_float_list(args.extents)
    step_values = _parse_int_list(args.steps)

    if args.substrate_dir is not None:
        substrate = _load_substrate_artifact(Path(args.substrate_dir))
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
    main()
