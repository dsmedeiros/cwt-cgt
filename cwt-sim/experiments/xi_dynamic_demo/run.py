"""Susceptibility feedback demo contrasting static and dynamic Ξ."""

from __future__ import annotations

import argparse
import math
from dataclasses import dataclass
from typing import Mapping, Sequence

import numpy as np

from cwt.graph import factories
from cwt.layers.state import LayersState
from cwt.orchestrator.param_path import ParameterPath
from cwt.orchestrator.scheduler import RunConfig, _psi_at, run_parameter_loop


@dataclass
class XiRunSummary:
    mode: str
    phi_flux: float
    phi_missing: bool
    area: float
    kappa: float
    kappa_ci: tuple[float, float] | None
    xi_deltas: np.ndarray


def _parse_center(text: str) -> dict[str, float]:
    center: dict[str, float] = {"tau": 0.0, "zeta": 0.0}
    if not text:
        return center
    parts = [item.strip() for item in text.split(",") if item.strip()]
    for part in parts:
        if "=" not in part:
            raise ValueError(f"malformed centre entry '{part}'")
        key, value = (token.strip() for token in part.split("=", 1))
        try:
            center[key] = float(value)
        except ValueError as exc:  # pragma: no cover - defensive
            raise ValueError(f"non-numeric centre value '{value}'") from exc
    return center


def _parse_axes(values: Sequence[str]) -> tuple[str, str]:
    if len(values) != 2:
        raise ValueError("exactly two axes are required")
    ax_i, ax_j = (str(axis).strip() for axis in values)
    if not ax_i or not ax_j:
        raise ValueError("axes entries must be non-empty")
    if ax_i == ax_j:
        raise ValueError("axes must be distinct")
    return ax_i, ax_j


def _loop_steps(extent: float) -> int:
    magnitude = abs(float(extent))
    if magnitude <= 0.0:
        raise ValueError("extent must be positive")
    base = 200
    scale = max(int(round(magnitude / 0.01)), 1)
    return base * scale


def _initial_state(
    substrate, center: Mapping[str, float], config: RunConfig
) -> tuple[np.ndarray, np.ndarray]:
    N = substrate.N
    base_prob = np.full(N, 1.0 / N, dtype=float)
    base_theta = np.zeros(N, dtype=float)
    settle_steps = max(int(getattr(config, "neighbor_settle_steps", 40)), 1)
    psi_center = _psi_at(substrate, center, base_prob, base_theta, config, steps=settle_steps)
    return np.square(np.abs(psi_center)).astype(float), np.angle(psi_center).astype(float)


def _phi_flux(record) -> tuple[float, bool]:
    total = 0.0
    tiles_present = False
    for tile in record.omega_tiles:
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


def _kappa_ci(record, total_area: float) -> tuple[float, float] | None:
    if not math.isfinite(total_area) or total_area == 0.0:
        return None
    lower_flux = 0.0
    upper_flux = 0.0
    have_ci = False
    for tile in record.omega_tiles:
        if not isinstance(tile, Mapping):
            continue
        try:
            area_val = float(tile.get("tile_area", 0.0))
            omega_val = float(tile.get("omega", 0.0))
        except (TypeError, ValueError):
            continue
        if not (math.isfinite(area_val) and math.isfinite(omega_val)):
            continue
        ci_val = tile.get("ci")
        if (
            isinstance(ci_val, Sequence)
            and len(ci_val) == 2
            and all(isinstance(x, (float, int)) for x in ci_val)
        ):
            have_ci = True
            lower_flux += float(ci_val[0]) * area_val
            upper_flux += float(ci_val[1]) * area_val
        else:
            lower_flux += omega_val * area_val
            upper_flux += omega_val * area_val
    if not have_ci:
        return None
    return (lower_flux / total_area, upper_flux / total_area)


def _xi_norm_deltas(traj: Sequence[np.ndarray]) -> np.ndarray:
    if len(traj) < 2:
        return np.zeros(0, dtype=float)
    deltas: list[float] = []
    for prev, curr in zip(traj[:-1], traj[1:]):
        prev_norm = np.asarray(prev, dtype=float)
        curr_norm = np.asarray(curr, dtype=float)
        if prev_norm.size:
            prev_norm = prev_norm / max(prev_norm.sum(), 1e-12)
        if curr_norm.size:
            curr_norm = curr_norm / max(curr_norm.sum(), 1e-12)
        diff = curr_norm - prev_norm
        deltas.append(float(np.linalg.norm(diff)))
    return np.asarray(deltas, dtype=float)


def _build_config(xi_type: str) -> RunConfig:
    return RunConfig(
        eta_q=0.35,
        zeta=0.0,
        omega_scale=1.0,
        s_min=0.6,
        smooth_window=4,
        compute_metric=False,
        compute_curvature=True,
        adapt_levels=1,
        ci_tol=0.05,
        alpha=0.4,
        beta=1.0,
        neighbor_settle_steps=50,
        geometry={"sample_mode": "direct", "neighbor_steps": 1},
        delta_frac={"tau": 0.01, "zeta": 0.01},
        xi_kind={"type": xi_type},
        readout={"final": True},
        noise={},
        fs_step_guard={},
    )


def _run_mode(
    xi_type: str,
    *,
    center: Mapping[str, float],
    axes: tuple[str, str],
    extent: float,
    seed: int,
) -> XiRunSummary:
    config = _build_config(xi_type)
    substrate = factories.ring3_hetero()
    base_prob, base_theta = _initial_state(substrate, center, config)

    steps = _loop_steps(extent)
    center_dict = {axis: float(center.get(axis, 0.0)) for axis in axes}
    extent_dict = {axis: float(extent) for axis in axes}

    path = ParameterPath(
        kind="rectangle",
        center=center_dict,
        extents=extent_dict,
        steps=steps,
        orientation="CCW",
        axes=axes,
    )

    record = run_parameter_loop(
        substrate,
        LayersState(pQ=base_prob.copy(), theta=base_theta.copy()),
        path,
        config,
        seed=seed,
    )

    area = float(sum(float(delta) for delta in record.delta_area))
    phi_flux, phi_missing = _phi_flux(record)
    kappa = float("nan")
    if not phi_missing and area != 0.0 and math.isfinite(phi_flux):
        kappa = phi_flux / area
    xi_deltas = _xi_norm_deltas(record.pQ_traj)
    return XiRunSummary(
        mode=xi_type,
        phi_flux=phi_flux,
        phi_missing=phi_missing,
        area=area,
        kappa=kappa,
        kappa_ci=None if phi_missing else _kappa_ci(record, area),
        xi_deltas=xi_deltas,
    )


def _print_summary(static_run: XiRunSummary, dynamic_run: XiRunSummary) -> None:
    def _format_ci(ci: tuple[float, float] | None) -> str:
        if ci is None:
            return "n/a"
        lower, upper = ci
        return f"[{lower:.4f}, {upper:.4f}]"

    print("Ξ feedback comparison")
    print("----------------------")
    print(
        "static  κ₁={kappa:.5f}  φ={phi:.5f}  CI={ci}".format(
            kappa=static_run.kappa,
            phi=static_run.phi_flux,
            ci=_format_ci(static_run.kappa_ci),
        )
    )
    print(
        "dynamic κ₁={kappa:.5f}  φ={phi:.5f}  CI={ci}".format(
            kappa=dynamic_run.kappa,
            phi=dynamic_run.phi_flux,
            ci=_format_ci(dynamic_run.kappa_ci),
        )
    )
    missing_modes = [run.mode for run in (static_run, dynamic_run) if getattr(run, "phi_missing", False)]
    if missing_modes:
        print("⚠️  Missing curvature tiles for: " + ", ".join(sorted(set(missing_modes))))
    shift = dynamic_run.kappa - static_run.kappa
    print(f"κ₁ shift (dynamic-static): {shift:+.5f}")

    if dynamic_run.xi_deltas.size:
        norms = dynamic_run.xi_deltas
        print()
        print("‖ΔΞ‖ trajectory (first 10 steps):")
        preview = " ".join(f"{val:.4f}" for val in norms[:10])
        print(preview)
        print(f"median={np.median(norms):.4f}  max={np.max(norms):.4f}  final={norms[-1]:.4f}")
    else:
        print("no susceptibility evolution captured")


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Dynamic Ξ feedback demo")
    parser.add_argument("--center", type=str, default="tau=0.8,zeta=0.0")
    parser.add_argument("--axes", nargs=2, default=["tau", "zeta"])
    parser.add_argument("--extents", type=float, default=0.02)
    parser.add_argument("--kappa", type=float, default=0.1)
    parser.add_argument("--gains", nargs=4, default=["1.0", "0.2", "0.2", "0.2"])
    parser.add_argument("--seed", type=int, default=11)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    args = _parse_args(argv)
    center = _parse_center(str(args.center))
    center.setdefault("kappa", float(args.kappa))
    axes = _parse_axes(args.axes)
    extent = float(args.extents)

    static_run = _run_mode("static", center=center, axes=axes, extent=extent, seed=int(args.seed))
    dynamic_run = _run_mode("dynamic", center=center, axes=axes, extent=extent, seed=int(args.seed) + 1)

    print(f"gains supplied: {', '.join(str(val) for val in args.gains)}")
    _print_summary(static_run, dynamic_run)


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    main()
