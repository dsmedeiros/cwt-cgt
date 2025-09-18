"""Operator-view curvature cross-check on a τ–ζ hotspot patch."""

from __future__ import annotations

import argparse
import math
import warnings
from dataclasses import dataclass
from typing import Mapping, Sequence

import numpy as np

from cwt.graph import factories
from cwt.layers.state import LayersState
from cwt.operator.biorth_geom import biorth_connection, biorth_curvature
from cwt.orchestrator.param_path import ParameterPath
from cwt.orchestrator.scheduler import RunConfig, _psi_at, run_parameter_loop


@dataclass
class CurvatureComparison:
    operator_grid: np.ndarray
    cgt_grid: np.ndarray


def _parse_center(text: str) -> dict[str, float]:
    center: dict[str, float] = {"tau": 0.0, "zeta": 0.0}
    parts = [item.strip() for item in text.split(",") if item.strip()]
    for part in parts:
        if "=" not in part:
            raise ValueError(f"malformed centre entry '{part}'")
        key, value = (token.strip() for token in part.split("=", 1))
        center[key] = float(value)
    return center


def _parse_axes(values: Sequence[str]) -> tuple[str, str]:
    if len(values) != 2:
        raise ValueError("two axes required")
    ax_i, ax_j = (str(axis).strip() for axis in values)
    if ax_i == ax_j:
        raise ValueError("axes must be distinct")
    return ax_i, ax_j


def _run_config() -> RunConfig:
    return RunConfig(
        eta_q=0.32,
        zeta=0.0,
        omega_scale=1.0,
        s_min=0.6,
        smooth_window=3,
        compute_metric=False,
        compute_curvature=True,
        adapt_levels=1,
        ci_tol=0.05,
        alpha=0.35,
        beta=1.0,
        neighbor_settle_steps=40,
        geometry={"sample_mode": "direct", "neighbor_steps": 1},
        delta_frac={"tau": 0.01, "zeta": 0.01},
        xi_kind={"type": "static"},
        readout={"final": True},
        noise={},
        fs_step_guard={},
    )


def _psi_state(substrate, lam: Mapping[str, float], config: RunConfig) -> np.ndarray:
    N = substrate.N
    base_prob = np.full(N, 1.0 / N, dtype=float)
    base_theta = np.zeros(N, dtype=float)
    settle_steps = max(int(getattr(config, "neighbor_settle_steps", 40)), 1)
    return _psi_at(substrate, lam, base_prob, base_theta, config, steps=settle_steps)


def _operator_curvature(
    substrate,
    config: RunConfig,
    center: Mapping[str, float],
    axes: tuple[str, str],
    delta_i: float,
    delta_j: float,
) -> float:
    axis_i, axis_j = axes
    lam0 = dict(center)
    lam_i = dict(lam0)
    lam_i[axis_i] = lam_i.get(axis_i, 0.0) + delta_i
    lam_j = dict(lam0)
    lam_j[axis_j] = lam_j.get(axis_j, 0.0) + delta_j
    lam_ij = dict(lam_i)
    lam_ij[axis_j] = lam_ij.get(axis_j, 0.0) + delta_j

    Psi0 = _psi_state(substrate, lam0, config)
    Psi_i = _psi_state(substrate, lam_i, config)
    Psi_j = _psi_state(substrate, lam_j, config)
    Psi_ij = _psi_state(substrate, lam_ij, config)

    delta_i = float(delta_i)
    delta_j = float(delta_j)
    if delta_i == 0.0 or delta_j == 0.0:
        raise ValueError("delta_i and delta_j must be non-zero for operator curvature")

    uL0 = np.conjugate(Psi0)
    du_i = (Psi_i - Psi0) / delta_i
    du_j = (Psi_j - Psi0) / delta_j
    A_i = biorth_connection(uL0, du_i)
    A_j = biorth_connection(uL0, du_j)

    uL_j = np.conjugate(Psi_j)
    du_i_at_j = (Psi_ij - Psi_j) / delta_i
    A_i_at_j = biorth_connection(uL_j, du_i_at_j)
    dA_i = (A_i_at_j - A_i) / delta_j

    uL_i = np.conjugate(Psi_i)
    du_j_at_i = (Psi_ij - Psi_i) / delta_j
    A_j_at_i = biorth_connection(uL_i, du_j_at_i)
    dA_j = (A_j_at_i - A_j) / delta_i

    return biorth_curvature(A_i, A_j, dA_i, dA_j)


def _initial_state(substrate, center: Mapping[str, float], config: RunConfig):
    N = substrate.N
    base_prob = np.full(N, 1.0 / N, dtype=float)
    base_theta = np.zeros(N, dtype=float)
    settle_steps = max(int(getattr(config, "neighbor_settle_steps", 40)), 1)
    psi_center = _psi_at(substrate, center, base_prob, base_theta, config, steps=settle_steps)
    return np.square(np.abs(psi_center)).astype(float), np.angle(psi_center).astype(float)


def _cgt_curvature(
    substrate,
    config: RunConfig,
    center: Mapping[str, float],
    axes: tuple[str, str],
    delta_i: float,
    delta_j: float,
    seed: int,
) -> float:
    base_prob, base_theta = _initial_state(substrate, center, config)
    path = ParameterPath(
        kind="rectangle",
        center={axes[0]: float(center.get(axes[0], 0.0)), axes[1]: float(center.get(axes[1], 0.0))},
        extents={axes[0]: float(delta_i), axes[1]: float(delta_j)},
        steps=120,
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
    phi_flux = 0.0
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
            phi_flux += omega_val * area_val
    phi_missing = not tiles_present
    if isinstance(record.meta, Mapping):
        phi_missing = phi_missing or bool(record.meta.get("phi_flux_missing_tiles"))
    if phi_missing:
        warnings.warn(
            "Missing curvature tiles during CGT sampling; φ flux forced to 0.",
            RuntimeWarning,
            stacklevel=2,
        )
        return 0.0
    return phi_flux / area if area else float("nan")


def evaluate_patch(
    center: Mapping[str, float],
    axes: tuple[str, str],
    extent: float,
    seed: int,
) -> CurvatureComparison:
    substrate = factories.ring3_hetero()
    config = _run_config()
    offsets = [-extent, 0.0, extent]
    delta_i = extent / 3.0
    delta_j = extent / 3.0
    operator_grid = np.zeros((3, 3), dtype=float)
    cgt_grid = np.zeros((3, 3), dtype=float)

    for row, dz in enumerate(offsets):
        for col, dt in enumerate(offsets):
            lam_center = dict(center)
            lam_center[axes[0]] = lam_center.get(axes[0], 0.0) + dt
            lam_center[axes[1]] = lam_center.get(axes[1], 0.0) + dz
            operator_grid[row, col] = _operator_curvature(
                substrate,
                config,
                lam_center,
                axes,
                delta_i,
                delta_j,
            )
            cgt_grid[row, col] = _cgt_curvature(
                substrate,
                config,
                lam_center,
                axes,
                delta_i,
                delta_j,
                seed=seed + row * 5 + col,
            )
    return CurvatureComparison(operator_grid=operator_grid, cgt_grid=cgt_grid)


def _print_grid(title: str, grid: np.ndarray) -> None:
    print(title)
    for row in grid:
        print("  " + " ".join(f"{val:+.5f}" for val in row))


def _print_summary(comparison: CurvatureComparison) -> None:
    _print_grid("Operator curvature (Ω₍ᵦᵢ₎)", comparison.operator_grid)
    print()
    _print_grid("CGT curvature (Ω₍CGT₎)", comparison.cgt_grid)
    print()
    center_op = comparison.operator_grid[1, 1]
    center_cgt = comparison.cgt_grid[1, 1]
    print(f"central sign agreement: {np.sign(center_op) == np.sign(center_cgt)}")
    delta = comparison.operator_grid - comparison.cgt_grid
    print(f"mean absolute deviation: {np.mean(np.abs(delta)):.5f}")


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Operator patch curvature cross-check")
    parser.add_argument("--center", type=str, default="tau=0.8,zeta=0.0")
    parser.add_argument("--axes", nargs=2, default=["tau", "zeta"])
    parser.add_argument("--extents", type=float, default=0.02)
    parser.add_argument("--seed", type=int, default=71)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    args = _parse_args(argv)
    center = _parse_center(str(args.center))
    axes = _parse_axes(args.axes)
    extent = float(args.extents)
    comparison = evaluate_patch(center=center, axes=axes, extent=extent, seed=int(args.seed))
    _print_summary(comparison)


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    main()
