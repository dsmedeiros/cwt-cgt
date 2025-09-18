"""Loop orientation validation at curvature hotspots."""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from cwt.geometry.adapt_mesh import curvature_anytime
from cwt.graph import factories
from cwt.graph.substrate import GraphSubstrate
from cwt.layers.state import LayersState
from cwt.orchestrator.param_path import ParameterPath
from cwt.orchestrator.scheduler import (
    RunConfig,
    _direct_neighbor_state_factory,
    _psi_at,
    _psi_sampler_factory_direct,
    run_parameter_loop,
)


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
    phi_missing: bool
    kappa: float
    memory: list[float]
    fs_p95: float
    fs_guard_exceeded: bool


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


def _loop_steps_for_extent(extent: float, base_steps: int = 2048) -> int:
    magnitude = abs(float(extent))
    if magnitude == 0.0:
        raise ValueError("extent must be non-zero to form a loop region")
    scale = max(int(round(magnitude / 0.02)), 1)
    return base_steps * scale


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
    guard_exceeded = bool(guard_meta.get("boundary_exceeded", False))

    return OrientationRun(
        orientation=orientation,
        extent=float(extent),
        steps=steps,
        area=area,
        phi_flux=phi_flux,
        phi_missing=phi_missing,
        kappa=kappa,
        memory=memory,
        fs_p95=fs_p95,
        fs_guard_exceeded=guard_exceeded,
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
    micro_scan: bool,
) -> HotspotSummary:
    center = dict(spec.center)
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
    summaries: list[ExtentSummary] = []
    for extent in extents:
        ccw = _run_loop(substrate, config, base_prob, base_theta, spec.center, axes, extent, "CCW", seed)
        cw = _run_loop(substrate, config, base_prob, base_theta, spec.center, axes, extent, "CW", seed)
        area_flip = _relative_flip_error(ccw.area, cw.area)
        if ccw.phi_missing or cw.phi_missing:
            phi_flip = float("nan")
        else:
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
        "--fs-guard",
        type=float,
        default=None,
        help="Optional FS guard threshold in radians (enables CLI enforcement when set)",
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
    if args.fs_guard is not None:
        config.fs_step_guard = {
            "threshold": float(args.fs_guard),
            "window": 64,
            "throttle": 0.9,
        }

    micro_scan_enabled = bool(args.micro_scan)

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
            micro_scan=micro_scan_enabled,
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
