"""Readout invariance study around a curvature hotspot."""

from __future__ import annotations

import argparse
import math
from dataclasses import dataclass
from typing import Mapping, Sequence

import numpy as np

from cwt.graph import factories
from cwt.graph.substrate import GraphSubstrate
from cwt.layers.readouts import (
    memory_uniform_charge,
    readout_percolation,
    readout_spiking,
    readout_stochastic,
)
from cwt.layers.state import LayersState
from cwt.orchestrator.param_path import ParameterPath
from cwt.orchestrator.scheduler import RunConfig, _psi_at, run_parameter_loop


@dataclass
class OrientationSummary:
    orientation: str
    phi_flux: float
    phi_missing: bool
    area: float
    kappa: float
    p_final: np.ndarray
    theta_final: np.ndarray


@dataclass
class ReadoutSummary:
    name: str
    ccw: OrientationSummary
    cw: OrientationSummary
    flip_error: float
    kappa: float
    readout_meta: Mapping[str, float | int | bool]


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


def _parse_axes(values: Sequence[str]) -> tuple[str, str]:
    if len(values) != 2:
        raise ValueError("two axes must be supplied")
    ax_i, ax_j = (str(axis).strip() for axis in values)
    if not ax_i or not ax_j:
        raise ValueError("axes entries must be non-empty")
    if ax_i == ax_j:
        raise ValueError("axes must be distinct")
    return ax_i, ax_j


def _loop_steps_for_extent(extent: float) -> int:
    magnitude = abs(float(extent))
    if magnitude <= 0.0:
        raise ValueError("extent must be positive")
    base_steps = 180
    scale = max(int(round(magnitude / 0.01)), 1)
    return base_steps * scale


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


def _phi_flux(record_steps: int, omega_tiles: Sequence[Mapping[str, float]]) -> tuple[float, bool]:
    total = 0.0
    tiles_present = False
    for tile in omega_tiles:
        if not isinstance(tile, Mapping):
            continue
        try:
            omega_val = float(tile.get("omega", 0.0))
            area_val = float(tile.get("tile_area", 0.0))
        except (TypeError, ValueError):
            continue
        if math.isfinite(omega_val) and math.isfinite(area_val):
            tiles_present = True
            total += omega_val * area_val
    if not tiles_present:
        return 0.0, True
    return float(total), False


def _orientation_run(
    substrate: GraphSubstrate,
    config: RunConfig,
    base_prob: np.ndarray,
    base_theta: np.ndarray,
    center: Mapping[str, float],
    axes: tuple[str, str],
    extent: float,
    orientation: str,
    seed: int,
) -> OrientationSummary:
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
    phi_flux, phi_missing = _phi_flux(path.steps, record.omega_tiles)
    kappa = float("nan")
    if not phi_missing and area != 0.0 and math.isfinite(phi_flux):
        kappa = phi_flux / area
    p_final = record.pQ_traj[-1].copy() if record.pQ_traj else base_prob.copy()
    theta_final = record.theta_traj[-1].copy() if record.theta_traj else base_theta.copy()
    return OrientationSummary(
        orientation=orientation,
        phi_flux=phi_flux,
        phi_missing=phi_missing,
        area=area,
        kappa=kappa,
        p_final=p_final,
        theta_final=theta_final,
    )


def _relative_flip_error(value_ccw: float, value_cw: float) -> float:
    if not (math.isfinite(value_ccw) and math.isfinite(value_cw)):
        return float("nan")
    denom = max(abs(value_ccw), 1e-12)
    return abs(value_cw + value_ccw) / denom


def _run_readout(
    name: str,
    *,
    substrate: GraphSubstrate,
    config: RunConfig,
    base_prob: np.ndarray,
    base_theta: np.ndarray,
    center: Mapping[str, float],
    axes: tuple[str, str],
    extent: float,
    seed: int,
) -> ReadoutSummary:
    ccw = _orientation_run(
        substrate,
        config,
        base_prob,
        base_theta,
        center,
        axes,
        extent,
        "CCW",
        seed,
    )
    cw = _orientation_run(
        substrate,
        config,
        base_prob,
        base_theta,
        center,
        axes,
        extent,
        "CW",
        seed + 1,
    )

    if ccw.phi_missing or cw.phi_missing:
        phi_flip = float("nan")
    else:
        phi_flip = _relative_flip_error(ccw.phi_flux, cw.phi_flux)

    readout_params = config.readout.get("params", {}) if isinstance(config.readout, Mapping) else {}
    try:
        target_index = int(readout_params.get("target", 0))
    except (TypeError, ValueError):
        target_index = 0

    memory_vec = memory_uniform_charge(
        ccw.phi_flux,
        pQ=ccw.p_final,
        mode="one_hot",
        target=target_index,
    )

    readout_meta: dict[str, float | int | bool]
    if name == "stochastic":
        choice, weights = readout_stochastic(ccw.p_final, memory_vec, T=0.6, eta=1.0, rng=seed)
        readout_meta = {
            "choice": int(choice),
            "entropy": float(-np.sum(weights * np.log(np.clip(weights, 1e-12, 1.0)))),
        }
    elif name == "percolation":
        payload = readout_percolation(ccw.p_final, p_crit=0.12, theta_perc=0.35, M_shift=0.0, G=substrate)
        readout_meta = {"fired": bool(payload["fired"]), "cluster_size": int(payload["size"])}
    elif name == "spiking":
        rng = np.random.default_rng(seed)
        payload = readout_spiking(
            ccw.p_final,
            np.ones_like(ccw.p_final),
            memory_vec,
            r0=18.0,
            c1=0.8,
            c2=0.2,
            c3=0.4,
            window=5,
            thresh=max(1, int(round(base_prob.size * 0.15))),
            rng=rng,
        )
        readout_meta = {"fired": bool(payload["fired"]), "spikes": int(payload["spikes_total"])}
    else:  # pragma: no cover - defensive
        readout_meta = {}

    return ReadoutSummary(
        name=name,
        ccw=ccw,
        cw=cw,
        flip_error=phi_flip,
        kappa=ccw.kappa,
        readout_meta=readout_meta,
    )


def _build_run_config(mode: str) -> RunConfig:
    memory_target = 0
    readout_params: dict[str, object] = {
        "mode": "one_hot",
        "target": memory_target,
        "pQ_source": "probability",
    }
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
            "params": readout_params,
        },
        noise={},
        fs_step_guard={},
    )


def run_ablation(
    *,
    center: Mapping[str, float],
    axes: tuple[str, str],
    extent: float,
    seed: int,
) -> list[ReadoutSummary]:
    substrate = factories.ring3_hetero()
    summaries: list[ReadoutSummary] = []
    for mode in ("stochastic", "percolation", "spiking"):
        config = _build_run_config(mode)
        base_prob, base_theta = _initial_state(substrate, center, config)
        summaries.append(
            _run_readout(
                mode,
                substrate=substrate,
                config=config,
                base_prob=base_prob,
                base_theta=base_theta,
                center=center,
                axes=axes,
                extent=extent,
                seed=seed,
            )
        )
    return summaries


def _print_summary(results: Sequence[ReadoutSummary]) -> None:
    header = f"{'readout':<14}{'κ₁ (CCW)':>12}{'flip err':>12}{'meta':>18}"
    print(header)
    print("-" * len(header))
    for summary in results:
        kappa = summary.kappa if math.isfinite(summary.kappa) else float("nan")
        meta_repr = ", ".join(f"{k}={v}" for k, v in summary.readout_meta.items())
        print(f"{summary.name:<14}{kappa:>12.5f}{summary.flip_error:>12.4f}  {meta_repr}")

    missing_labels = [
        summary.name for summary in results if summary.ccw.phi_missing or summary.cw.phi_missing
    ]
    if missing_labels:
        print()
        print("⚠️  Missing curvature tiles for runs: " + ", ".join(missing_labels))

    kappas = [res.kappa for res in results if math.isfinite(res.kappa)]
    if kappas:
        kappa_min = min(kappas)
        kappa_max = max(kappas)
        if kappa_min != 0.0:
            spread = abs(kappa_max - kappa_min) / abs(kappa_min)
        else:
            spread = float("nan")
        print()
        print(f"κ₁ spread across readouts: {spread * 100.0:.2f}%")


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Readout ablation at hotspot")
    parser.add_argument("--center", type=str, default="tau=0.8,zeta=0.0")
    parser.add_argument("--axes", nargs=2, default=["tau", "zeta"])
    parser.add_argument("--extents", type=float, default=0.02)
    parser.add_argument("--seed", type=int, default=7)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    args = _parse_args(argv)
    center = _parse_center(str(args.center))
    axes = _parse_axes(args.axes)
    extent = float(args.extents)
    results = run_ablation(center=center, axes=axes, extent=extent, seed=int(args.seed))
    _print_summary(results)


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    main()
