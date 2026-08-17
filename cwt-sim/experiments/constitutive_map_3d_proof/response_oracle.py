"""Geometry-blind Benchmark-C variable-alpha response oracle."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np

from .bc3_interval_model import path_response_interval
from .bc3_lattice import exact_lattice, lattice_certificate
from .bc3_primitives import frozen_centered_readout, frozen_phase_and_coefficient_arrays
from .binary64_interval import runtime_contract
from .contract import MODEL_CONTRACT, ConstitutiveMap3DContract
from .pipeline import OracleAccess

DIAGNOSTIC_DENSITY_CEILING = 1.0e-6


def _distance_to_interval(value: float, lower: float, upper: float) -> float:
    return max(lower - value, 0.0, value - upper)


def scalar_diagnostic_record(
    scalar_q: float,
    scale: float,
    q_interval: tuple[float, float],
    density_interval: tuple[float, float],
) -> dict[str, object]:
    """Describe the legacy scalar result without granting it theorem authority."""

    q_lower, q_upper = q_interval
    density_lower, density_upper = density_interval
    scalar_density = scalar_q / (scale * scale)
    scalar_finite = bool(np.isfinite(scalar_q) and np.isfinite(scalar_density))
    q_distance = _distance_to_interval(scalar_q, q_lower, q_upper) if scalar_finite else None
    density_distance = (
        _distance_to_interval(scalar_density, density_lower, density_upper) if scalar_finite else None
    )
    return {
        "authority": "NON_AUTHORITATIVE_DIAGNOSTIC",
        "evaluates_different_float_control_and_libm_path": True,
        "used_by_formal_pass": False,
        "unioned_into_authoritative_interval": False,
        "q_anti": scalar_q if scalar_finite else None,
        "density": scalar_density if scalar_finite else None,
        "q_inside_authoritative_interval": (q_lower <= scalar_q <= q_upper if scalar_finite else False),
        "density_inside_authoritative_interval": (
            density_lower <= scalar_density <= density_upper if scalar_finite else False
        ),
        "q_signed_residual_from_interval_midpoint": (
            scalar_q - 0.5 * (q_lower + q_upper) if scalar_finite else None
        ),
        "density_signed_residual_from_interval_midpoint": (
            scalar_density - 0.5 * (density_lower + density_upper) if scalar_finite else None
        ),
        "q_distance_to_authoritative_interval": q_distance,
        "density_distance_to_authoritative_interval": density_distance,
        "development_selected_density_ceiling": DIAGNOSTIC_DENSITY_CEILING,
        "diagnostic_status": (
            "PASS_NONAUTHORITATIVE_REGRESSION"
            if scalar_finite
            and density_distance is not None
            and density_distance <= DIAGNOSTIC_DENSITY_CEILING
            else "BLOCKED_DIAGNOSTIC_DRIFT"
        ),
    }


def assess_scalar_diagnostics(rows: Sequence[dict[str, object]]) -> dict[str, object]:
    """Recompute the drift sentinel and reject diagnostic self-attestation."""

    assessed_rows = []
    all_pass = True
    for index, row in enumerate(rows):
        scale = float(row["scale"])
        q_payload = row["q_anti_interval"]
        density_payload = row["density_interval"]
        if not isinstance(q_payload, dict) or not isinstance(density_payload, dict):
            raise ValueError("diagnostic rows require authoritative interval mappings")
        observed = row.get("scalar_diagnostic")
        if not isinstance(observed, dict):
            expected = scalar_diagnostic_record(
                float("nan"),
                scale,
                (float(q_payload["lower"]), float(q_payload["upper"])),
                (float(density_payload["lower"]), float(density_payload["upper"])),
            )
        else:
            q_value = observed.get("q_anti")
            expected = scalar_diagnostic_record(
                float(q_value) if isinstance(q_value, (int, float)) else float("nan"),
                scale,
                (float(q_payload["lower"]), float(q_payload["upper"])),
                (float(density_payload["lower"]), float(density_payload["upper"])),
            )
        record_matches = observed == expected
        row_pass = record_matches and expected["diagnostic_status"] == ("PASS_NONAUTHORITATIVE_REGRESSION")
        all_pass = all_pass and row_pass
        assessed_rows.append(
            {
                "row_index": index,
                "record_matches_recomputation": record_matches,
                "diagnostic_status": (
                    "PASS_NONAUTHORITATIVE_REGRESSION" if row_pass else "BLOCKED_DIAGNOSTIC_DRIFT"
                ),
                "density_distance_to_authoritative_interval": expected[
                    "density_distance_to_authoritative_interval"
                ],
            }
        )
    return {
        "authority": "NON_AUTHORITATIVE_DIAGNOSTIC",
        "used_by_formal_pass": False,
        "unioned_into_authoritative_interval": False,
        "development_selected_density_ceiling": DIAGNOSTIC_DENSITY_CEILING,
        "diagnostic_status": ("PASS_NONAUTHORITATIVE_REGRESSION" if all_pass else "BLOCKED_DIAGNOSTIC_DRIFT"),
        "rows": assessed_rows,
    }


def parallelogram_controls(
    center: Sequence[float],
    tangent_1: Sequence[float],
    tangent_2: Sequence[float],
    scale: float,
    steps_per_edge: int,
) -> np.ndarray:
    """Store one closed positive t1-then-t2 loop including each endpoint once."""

    c = np.asarray(center, dtype=float)
    t1 = np.asarray(tangent_1, dtype=float)
    t2 = np.asarray(tangent_2, dtype=float)
    if c.shape != (3,) or t1.shape != (3,) or t2.shape != (3,):
        raise ValueError("BC3 loop controls and tangents must be three-dimensional")
    if not np.isfinite(scale) or scale <= 0.0 or steps_per_edge < 1:
        raise ValueError("BC3 loop scale and resolution must be positive")
    corners = (
        c - 0.5 * scale * t1 - 0.5 * scale * t2,
        c + 0.5 * scale * t1 - 0.5 * scale * t2,
        c + 0.5 * scale * t1 + 0.5 * scale * t2,
        c - 0.5 * scale * t1 + 0.5 * scale * t2,
        c - 0.5 * scale * t1 - 0.5 * scale * t2,
    )
    rows = [corners[0]]
    for start, stop in zip(corners[:-1], corners[1:], strict=True):
        for step in range(1, steps_per_edge + 1):
            rows.append(start + (stop - start) * (step / steps_per_edge))
    return np.asarray(rows, dtype=float)


def exact_reverse(controls: np.ndarray) -> np.ndarray:
    return np.asarray(controls, dtype=float)[::-1].copy()


def domain_margins(
    controls: np.ndarray,
    contract: ConstitutiveMap3DContract = MODEL_CONTRACT,
) -> dict[str, float]:
    value = np.asarray(controls, dtype=float)
    bounds = (contract.bc3_u_bounds, contract.bc3_v_bounds, contract.bc3_alpha_bounds)
    margins = {}
    for axis, name in enumerate(("u", "v", "alpha")):
        lower, upper = (float(item) for item in bounds[axis])
        margins[f"{name}_lower"] = float(np.min(value[:, axis] - lower))
        margins[f"{name}_upper"] = float(np.min(upper - value[:, axis]))
    return margins


def response_sum(
    controls: np.ndarray,
    oracle_access: OracleAccess,
    gain: float = float(MODEL_CONTRACT.bc3_gain),
    contract: ConstitutiveMap3DContract = MODEL_CONTRACT,
) -> float:
    """Run the unwrapped right-endpoint update/sample recurrence."""

    value = np.asarray(controls, dtype=float)
    if value.ndim != 2 or value.shape[1] != 3 or len(value) < 2:
        raise ValueError("BC3 response controls must have shape (n,3) with n>=2")
    oracle_access.require_current()
    if any(margin < -1.0e-14 for margin in domain_margins(value, contract).values()):
        raise ValueError("BC3 response controls leave the frozen domain")
    phases, coefficients = frozen_phase_and_coefficient_arrays(value[:, 0], value[:, 1], contract)
    actual_phase = float(phases[0])
    total = 0.0
    for index in range(1, len(value)):
        branch_phase = float(phases[index])
        actual_phase += float(value[index, 2]) * (branch_phase - actual_phase)
        total += frozen_centered_readout(
            actual_phase,
            branch_phase,
            float(coefficients[index]),
            gain,
        )
    return float(total)


def antisymmetric_pair(
    controls: np.ndarray,
    oracle_access: OracleAccess,
    contract: ConstitutiveMap3DContract = MODEL_CONTRACT,
) -> dict[str, float]:
    forward = response_sum(controls, oracle_access, contract=contract)
    reverse = response_sum(exact_reverse(controls), oracle_access, contract=contract)
    return {
        "forward": forward,
        "reverse": reverse,
        "q_anti": 0.5 * (forward - reverse),
        "ordinary_difference": forward - reverse,
    }


def ladder_certificate(
    oracle_access: OracleAccess,
    contract: ConstitutiveMap3DContract = MODEL_CONTRACT,
) -> dict[str, object]:
    center = [float(item) for item in contract.bc3_heldout_center]
    rows = []
    for scale, steps in zip(contract.bc3_scales, contract.bc3_steps_per_edge, strict=True):
        lattice = exact_lattice(scale, steps, contract)
        controls = lattice.forward.astype(float) / lattice.denominator
        pair = antisymmetric_pair(controls, oracle_access, contract)
        forward_interval = path_response_interval(lattice.forward, lattice.denominator)
        reverse_interval = path_response_interval(lattice.reverse, lattice.denominator)
        q_anti_interval = (forward_interval - reverse_interval) / 2
        density_interval = q_anti_interval / (scale * scale)
        scalar_q = pair["q_anti"]
        q_lower = float(q_anti_interval.lower)
        q_upper = float(q_anti_interval.upper)
        density_lower = float(density_interval.lower)
        density_upper = float(density_interval.upper)
        rows.append(
            {
                "scale": float(scale),
                "steps_per_edge": steps,
                "updates": int(len(controls) - 1),
                "s_times_updates": float(scale) * (len(controls) - 1),
                "domain_margins": domain_margins(controls, contract),
                "lattice": lattice_certificate(lattice),
                "forward_response_interval": forward_interval.jsonable_scalar(),
                "reverse_response_interval": reverse_interval.jsonable_scalar(),
                "q_anti_interval": q_anti_interval.jsonable_scalar(),
                "density_interval": density_interval.jsonable_scalar(),
                "scalar_diagnostic": scalar_diagnostic_record(
                    scalar_q,
                    float(scale),
                    (q_lower, q_upper),
                    (density_lower, density_upper),
                ),
            }
        )
    fixed_rows = []
    fixed_scale = float(contract.bc3_scales[0])
    for steps in contract.bc3_fixed_scale_steps_per_edge:
        controls = parallelogram_controls(
            center,
            contract.bc3_tangent_1,
            contract.bc3_tangent_2,
            fixed_scale,
            steps,
        )
        fixed_rows.append(
            {
                "steps_per_edge": steps,
                **antisymmetric_pair(controls, oracle_access, contract),
            }
        )
    alpha_only = np.asarray(
        (
            (center[0], center[1], 0.31),
            (center[0], center[1], 0.39),
            (center[0], center[1], 0.31),
        ),
        dtype=float,
    )
    diagnostic_assessment = assess_scalar_diagnostics(rows)
    return {
        "prediction_lock_sha256": oracle_access.require_current().lock_sha256,
        "binary64_interval_runtime": runtime_contract(),
        "scalar_diagnostic_policy": {
            "authority": "NON_AUTHORITATIVE_DIAGNOSTIC",
            "used_by_formal_pass": False,
            "unioned_into_authoritative_interval": False,
            "development_selected_density_ceiling": DIAGNOSTIC_DENSITY_CEILING,
        },
        "theorem": "generic_compact_C3_contraction_remainder_O(s/N);area_relative_requires_sN_to_infinity",
        "rows": rows,
        "fixed_loop_rows": fixed_rows,
        "s_times_updates_strictly_increasing": all(
            right["s_times_updates"] > left["s_times_updates"]
            for left, right in zip(rows[:-1], rows[1:], strict=True)
        ),
        "all_loops_inside_domain": all(
            all(value >= -1.0e-14 for value in row["domain_margins"].values()) for row in rows
        ),
        "pure_alpha_loop_absolute_response": abs(response_sum(alpha_only, oracle_access, contract=contract)),
        "predictor_or_geometry_imported": False,
        "orientation_label_received": False,
        "right_endpoint_update_then_sample": True,
        "equilibrium_initialization": True,
        "exact_reverse_used": True,
        "scalar_diagnostic_assessment": diagnostic_assessment,
        "diagnostic_status": diagnostic_assessment["diagnostic_status"],
    }
