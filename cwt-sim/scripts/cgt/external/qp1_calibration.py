from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

CWT_SIM_ROOT = Path(__file__).resolve().parents[3]
if str(CWT_SIM_ROOT) not in sys.path:
    sys.path.insert(0, str(CWT_SIM_ROOT))


def _derive_sign_map(
    analytic_integral: float,
    implementation_integral: float,
    *,
    magnitude_floor: float = 1.0e-12,
) -> float | None:
    """Return the sign multiplier mapping implementation to analytic convention."""

    analytic = float(analytic_integral)
    implementation = float(implementation_integral)
    floor = abs(float(magnitude_floor))
    if not np.isfinite(analytic) or not np.isfinite(implementation):
        return None
    if abs(analytic) <= floor or abs(implementation) <= floor:
        return None
    return float(np.sign(analytic / implementation))


def qp1_calibration(samples: int) -> dict[str, float | int | str | bool | None]:
    from cwt.geometry.curvature import curvature_tile
    from cwt.operator.biorth_geom import biorth_connection, biorth_curvature
    from cwt.operator.L_map import qp1_state, qp1_state_derivatives

    lam = {"x": 0.0, "y": 0.0}
    dy = 1.0 / float(samples)
    dx = min(1.0e-3, dy)
    analytic_integral = 0.0
    implementation_integral = 0.0

    for y in np.linspace(0.0, 1.0, samples, endpoint=False):
        lam["y"] = float(y)
        state = qp1_state(lam)
        d_x, d_y = qp1_state_derivatives(lam)
        a_x = biorth_connection(state, d_x)
        a_y = biorth_connection(state, d_y)
        d_a_x_dy = (np.pi**2) * np.sin(np.pi * y)
        omega_density = biorth_curvature(a_x, a_y, dA_i=0.0, dA_j=d_a_x_dy)
        analytic_integral += omega_density * dy

        x0 = 0.17
        psi0 = qp1_state({"x": x0, "y": float(y)})
        psi_i = qp1_state({"x": x0 + dx, "y": float(y)})
        psi_ij = qp1_state({"x": x0 + dx, "y": float(y + dy)})
        psi_j = qp1_state({"x": x0, "y": float(y + dy)})
        omega_impl, _ = curvature_tile(psi0, psi_i, psi_ij, psi_j, dx, dy)
        implementation_integral += omega_impl * dy

    expected = 2.0 * np.pi
    sign_map = _derive_sign_map(analytic_integral, implementation_integral)
    return {
        "calibration_kind": "sphere_chart",
        "x_periodic": True,
        "y_periodic": False,
        "samples": int(samples),
        "wilson_magnitude": float(abs(implementation_integral)),
        "analytic_magnitude": float(expected),
        "magnitude_error": float(abs(abs(implementation_integral) - expected)),
        "implementation_curvature_integral": float(implementation_integral),
        "analytic_curvature_integral": float(analytic_integral),
        "sign_map_analytic_from_impl": sign_map,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the QP-1 sphere-chart curvature calibration.")
    parser.add_argument("--samples", type=int, default=2048)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    payload = qp1_calibration(samples=max(int(args.samples), 4))
    text = json.dumps(payload, indent=2)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
