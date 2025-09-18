"""Loop orientation validation at curvature hotspots."""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from cwt.graph import factories
from cwt.graph.substrate import GraphSubstrate
from cwt.layers.state import LayersState
from cwt.orchestrator.param_path import ParameterPath
from cwt.orchestrator.scheduler import RunConfig, _psi_at, run_parameter_loop


@dataclass
class HotspotSpec:
    """Curvature hotspot specification extracted from the atlas JSON."""

    center: dict[str, float]
    omega_abs: float | None
    metadata: dict[str, Any]


@dataclass
class OrientationRun:
    """Metrics recorded for a single loop orientation."""

    orientation: str
    extent: float
    steps: int
    area: float
    phi_flux: float
    kappa: float
    memory: list[float]


@dataclass
class ExtentSummary:
    """Paired CW/CCW loop statistics for a single extent."""

    extent: float
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
    return RunConfig(
        eta_q=0.3,
        zeta=0.0,
        omega_scale=1.0,
        s_min=0.6,
        smooth_window=3,
        compute_metric=False,
        compute_curvature=True,
        adapt_levels=1,
        ci_tol=0.05,
        alpha=0.3,
        beta=1.0,
        neighbor_settle_steps=40,
        geometry={"sample_mode": "direct", "neighbor_steps": 1},
        delta_frac={"tau": 0.01, "zeta": 0.01},
        xi_kind={"type": "static"},
        readout={
            "final": True,
            "memory_form": "uniform_charge",
            "params": {
                "mode": "one_hot",
                "target": int(target_index),
                "pQ_source": "probability",
            },
        },
        noise={},
        fs_step_guard={},
    )


def _build_substrate(name: str) -> GraphSubstrate:
    key = name.lower()
    if key in {"ring3_hetero", "ring3-h", "ring3-hetero"}:
        return factories.ring3_hetero()
    if key == "ring3":
        return factories.ring3()
    raise ValueError(f"unsupported substrate '{name}'")


def _initial_state(
    substrate: GraphSubstrate, center: Mapping[str, float], config: RunConfig
) -> tuple[np.ndarray, np.ndarray]:
    N = substrate.N
    if N <= 0:
        return np.zeros(0, dtype=float), np.zeros(0, dtype=float)
    base_prob = np.full(N, 1.0 / N, dtype=float)
    base_theta = np.zeros(N, dtype=float)
    settle_steps = max(int(getattr(config, "neighbor_settle_steps", 20)), 1)
    psi_center = _psi_at(substrate, center, base_prob, base_theta, config, steps=settle_steps)
    prob = np.square(np.abs(psi_center)).astype(float, copy=False)
    theta = np.angle(psi_center).astype(float, copy=False)
    return prob, theta


def _loop_steps_for_extent(extent: float, base_steps: int = 2048) -> int:
    magnitude = abs(float(extent))
    if magnitude == 0.0:
        raise ValueError("extent must be non-zero to form a loop region")
    scale = max(int(round(magnitude / 0.02)), 1)
    return base_steps * scale


def _extract_readout(record_steps: int, readouts: Sequence[Mapping[str, Any]]) -> tuple[float, list[float]]:
    phi = float("nan")
    memory: list[float] = []
    for entry in readouts:
        if not isinstance(entry, Mapping):
            continue
        if int(entry.get("step", -1)) != record_steps:
            continue
        try:
            phi = float(entry.get("phi_flux", float("nan")))
        except (TypeError, ValueError):
            phi = float("nan")
        memory_seq = entry.get("memory")
        if isinstance(memory_seq, Sequence) and not isinstance(memory_seq, (str, bytes)):
            try:
                memory = [float(val) for val in memory_seq]
            except (TypeError, ValueError):
                memory = []
        break
    return phi, memory


def _run_loop(
    substrate: GraphSubstrate,
    config: RunConfig,
    base_prob: np.ndarray,
    base_theta: np.ndarray,
    center: Mapping[str, float],
    axes: tuple[str, str],
    extent: float,
    orientation: str,
    seed: int,
) -> OrientationRun:
    steps = _loop_steps_for_extent(extent)
    center_dict = {axis: float(center[axis]) for axis in axes}
    extent_dict = {axis: float(extent) for axis in axes}

    path = ParameterPath(
        kind="rectangle",
        center=center_dict,
        extents=extent_dict,
        steps=steps,
        orientation=orientation,
        axes=axes,
    )

    init_state = LayersState(pQ=base_prob.copy(), theta=base_theta.copy())
    record = run_parameter_loop(substrate, init_state, path, config, seed=seed)

    area = float(sum(float(delta) for delta in record.delta_area))
    phi_flux, memory = _extract_readout(path.steps, record.readouts)
    if area != 0.0 and math.isfinite(phi_flux):
        kappa = phi_flux / area
    else:
        kappa = float("nan")

    return OrientationRun(
        orientation=orientation,
        extent=float(extent),
        steps=steps,
        area=area,
        phi_flux=phi_flux,
        kappa=kappa,
        memory=memory,
    )


def evaluate_hotspot(
    index: int,
    spec: HotspotSpec,
    *,
    substrate: GraphSubstrate,
    config: RunConfig,
    axes: tuple[str, str],
    extents: Sequence[float],
    seed: int,
) -> HotspotSummary:
    base_prob, base_theta = _initial_state(substrate, spec.center, config)
    summaries: list[ExtentSummary] = []
    for extent in extents:
        ccw = _run_loop(substrate, config, base_prob, base_theta, spec.center, axes, extent, "CCW", seed)
        cw = _run_loop(substrate, config, base_prob, base_theta, spec.center, axes, extent, "CW", seed)
        area_flip = _relative_flip_error(ccw.area, cw.area)
        phi_flip = _relative_flip_error(ccw.phi_flux, cw.phi_flux)
        summaries.append(
            ExtentSummary(
                extent=float(extent),
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


def render_summary(results: Sequence[HotspotSummary]) -> None:
    for summary in results:
        spec = summary.spec
        omega_text = "nan" if not math.isfinite(spec.omega_abs) else f"{spec.omega_abs:.6f}"
        center_repr = ", ".join(f"{axis}={spec.center[axis]:+.4f}" for axis in spec.center)
        print(f"Hotspot #{summary.index + 1}: {center_repr} (|Ω|={omega_text})")
        for extent_summary in summary.extents:
            extent = extent_summary.extent
            ccw = extent_summary.ccw
            cw = extent_summary.cw
            print(f"  extent={extent:+.4f}")
            print(
                "    CCW: R={:+.6f}, Φ={:+.6f}, κ₁={:+.6f}, χ={}".format(
                    ccw.area,
                    ccw.phi_flux,
                    ccw.kappa,
                    _format_memory(ccw.memory),
                )
            )
            print(
                "    CW : R={:+.6f}, Φ={:+.6f}, κ₁={:+.6f}, χ={}".format(
                    cw.area,
                    cw.phi_flux,
                    cw.kappa,
                    _format_memory(cw.memory),
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
                        f"Hotspot {summary.index + 1} extent {extent_summary.extent:+.4f}: "
                        f"area flip error {extent_summary.area_flip_error:.3f}"
                    )
                )
            if (
                math.isfinite(extent_summary.phi_flip_error)
                and extent_summary.phi_flip_error > flip_tolerance
            ):
                failures.append(
                    (
                        f"Hotspot {summary.index + 1} extent {extent_summary.extent:+.4f}: "
                        f"phi flip error {extent_summary.phi_flip_error:.3f}"
                    )
                )
        for idx, error in enumerate(summary.kappa_scale_errors, start=1):
            if math.isfinite(error) and error > kappa_tolerance:
                failures.append(f"Hotspot {summary.index + 1} κ₁ change #{idx} = {error:.3f}")

    return not failures, failures


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Loop validation at curvature hotspots")
    parser.add_argument("--hotspots", type=Path, required=True, help="Path to the top_omega_tiles.json file")
    parser.add_argument(
        "--extents",
        type=float,
        nargs="+",
        required=True,
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
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    axes = (str(args.axes[0]), str(args.axes[1]))

    extents = sorted((float(value) for value in args.extents), key=abs)
    if not extents:
        raise ValueError("at least one extent must be provided")

    hotspots = load_hotspots(args.hotspots, axes)
    if args.limit is not None:
        hotspots = hotspots[: max(int(args.limit), 0)]
    if not hotspots:
        raise ValueError("no hotspots available for evaluation")

    substrate = _build_substrate(str(args.graph))
    config = _default_run_config(int(args.readout_target))

    results: list[HotspotSummary] = []
    for index, spec in enumerate(hotspots):
        summary = evaluate_hotspot(
            index,
            spec,
            substrate=substrate,
            config=config,
            axes=axes,
            extents=extents,
            seed=int(args.seed),
        )
        results.append(summary)

    render_summary(results)
    accepted, failure_messages = evaluate_acceptance(results)
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
