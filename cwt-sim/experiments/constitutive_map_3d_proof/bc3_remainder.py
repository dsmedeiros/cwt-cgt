"""Exact Benchmark-C heldout remainder and sign certificate."""

from __future__ import annotations

from fractions import Fraction
from typing import Mapping, Sequence

import numpy as np

from .binary64_interval import Float64Interval
from .contract import MODEL_CONTRACT, ConstitutiveMap3DContract
from .exact import fraction_item

C1 = Fraction(1064329, 4800000)
C2 = Fraction(2290661581, 720000000)
MIDPOINT_QUADRATURE = Fraction(27863, 32000)
LOCAL_CURVATURE_COEFFICIENT = Fraction(14)
LAG_MU = Fraction(7, 3)
TANGENT_PHASE_BOUNDS = (Fraction(169, 400), Fraction(87, 200))
TV_C_COEFFICIENTS = (Fraction(1421, 200), Fraction(271, 15))
LAG_SECOND_ORDER = Fraction(202979, 360000)
TAYLOR_SECOND_ORDER = Fraction(70096509, 80000000)
QUADRATURE_SECOND_ORDER = Fraction(27863, 16000)
RESPONSE_TUBE_BOUND = Fraction(107, 8000)
RESPONSE_CENTER_BOUND = Fraction(1, 200)
RESPONSE_DERIVATIVE_BOUNDS = (Fraction(4, 5), Fraction(7, 8))
DENSITY_DERIVATIVE_BOUNDS = (Fraction(9613, 450), Fraction(446251, 14400))
CENTER_DENSITY_UPPER = Fraction(-3, 20)
FORMAL_SCALES = (
    Fraction(1, 400),
    Fraction(1, 800),
    Fraction(1, 1600),
    Fraction(1, 3200),
)
FORMAL_STEPS_PER_EDGE = (1024, 4096, 16384, 65536)
FORMAL_ENVELOPE_CEILINGS = (
    Fraction(63911, 512000),
    Fraction(126231, 2048000),
    Fraction(250871, 8192000),
    Fraction(500151, 32768000),
)


def density_envelope(scale: Fraction, steps_per_edge: int) -> Fraction:
    return Fraction(111, 500) / (scale * steps_per_edge) + Fraction(1591, 500 * steps_per_edge) + 14 * scale


def exact_remainder_certificate(
    contract: ConstitutiveMap3DContract = MODEL_CONTRACT,
) -> dict[str, object]:
    """Return the reviewed exact lag/Taylor/quadrature envelope."""

    rows = []
    for index, (scale, steps, reviewed_ceiling) in enumerate(
        zip(
            FORMAL_SCALES,
            FORMAL_STEPS_PER_EDGE,
            FORMAL_ENVELOPE_CEILINGS,
            strict=True,
        )
    ):
        envelope = density_envelope(scale, steps)
        rows.append(
            {
                "scale": fraction_item(scale),
                "steps_per_edge": steps,
                "s_times_N": fraction_item(scale * steps),
                "density_envelope": fraction_item(envelope),
                "reviewed_ceiling": fraction_item(reviewed_ceiling),
                "envelope_at_or_below_reviewed_ceiling": envelope <= reviewed_ceiling,
                "row_role": ("development_regression" if index < 2 else "locked_synthetic_holdout"),
            }
        )
    center_interval = (
        CENTER_DENSITY_UPPER - FORMAL_ENVELOPE_CEILINGS[0],
        CENTER_DENSITY_UPPER + FORMAL_ENVELOPE_CEILINGS[0],
    )
    return {
        "lag_recurrence": {
            "delta_n": "r_n*delta_(n-1)-r_n*d_n",
            "c_n": "m_n*d_n",
            "z_n": "delta_n+c_n",
            "z_recurrence": "z_n=r_n*z_(n-1)+r_n*(c_n-c_(n-1))",
            "equilibrium_initial_values": "delta_0=c_0=0",
            "rho": fraction_item(Fraction(7, 10)),
            "mu": fraction_item(LAG_MU),
            "sum_z_bound": "mu*(abs(c_1)+sum_from_2_to_4N(abs(c_n-c_(n-1))))",
            "corner_transients_included": True,
        },
        "exact_constants": {
            "C1": fraction_item(C1),
            "C2": fraction_item(C2),
            "midpoint_quadrature": fraction_item(MIDPOINT_QUADRATURE),
            "local_curvature_coefficient": fraction_item(LOCAL_CURVATURE_COEFFICIENT),
            "tangent_phase_bounds": [fraction_item(item) for item in TANGENT_PHASE_BOUNDS],
            "TV_c_coefficients": [fraction_item(item) for item in TV_C_COEFFICIENTS],
            "C_lag2": fraction_item(LAG_SECOND_ORDER),
            "C_Taylor": fraction_item(TAYLOR_SECOND_ORDER),
            "C_quad": fraction_item(QUADRATURE_SECOND_ORDER),
            "response_center_bound": fraction_item(RESPONSE_CENTER_BOUND),
            "response_tube_bound": fraction_item(RESPONSE_TUBE_BOUND),
            "response_derivative_bounds": [fraction_item(item) for item in RESPONSE_DERIVATIVE_BOUNDS],
            "density_derivative_bounds": [fraction_item(item) for item in DENSITY_DERIVATIVE_BOUNDS],
        },
        "density_envelope_formula": "111/(500*s*N)+1591/(500*N)+14*s",
        "center_density_directed_upper": fraction_item(CENTER_DENSITY_UPPER),
        "first_row_center_plus_envelope_interval": [fraction_item(item) for item in center_interval],
        "rows": rows,
        "all_envelopes_within_reviewed_ceilings": all(
            row["envelope_at_or_below_reviewed_ceiling"] for row in rows
        ),
        "s_times_N_strictly_doubles": all(
            right["s_times_N"]["fraction"] == str(2 * Fraction(left["s_times_N"]["fraction"]))
            for left, right in zip(rows[:-1], rows[1:], strict=True)
        ),
        "orientation_remainder_cancellation_assumed": False,
        "ordinary_difference_equals_two_q_anti": True,
        "contract_ladder_matches": (
            contract.bc3_scales == FORMAL_SCALES and contract.bc3_steps_per_edge == FORMAL_STEPS_PER_EDGE
        ),
        "oracle_enclosure_status": "REQUIRES_POST_ORACLE_CONJUNCTIVE_ASSESSMENT",
    }


def _fraction(record: Mapping[str, object]) -> Fraction:
    return Fraction(str(record["fraction"]))


def _float_interval(record: Mapping[str, object]) -> Float64Interval:
    return Float64Interval(np.asarray(float(record["lower"])), np.asarray(float(record["upper"])))


def _subset_of_symmetric(interval: Float64Interval, bound: Fraction) -> bool:
    return (
        Fraction.from_float(float(interval.lower)) >= -bound
        and Fraction.from_float(float(interval.upper)) <= bound
    )


def assess_oracle_enclosures(
    locked_prediction: Mapping[str, object] | None,
    oracle_rows: Sequence[Mapping[str, object]] | None,
) -> dict[str, object]:
    """Recompute all four reviewed row conjuncts from locked and oracle intervals."""

    if locked_prediction is None or oracle_rows is None:
        return {
            "status": "INDETERMINATE_MISSING_AUTHENTICATED_ENCLOSURE",
            "rows": [],
            "all_rows_pass": False,
        }
    try:
        prediction_rows = locked_prediction["rows"]
        center_record = locked_prediction["center_form_interval"]
        if not isinstance(prediction_rows, list) or not isinstance(center_record, Mapping):
            raise TypeError("locked prediction enclosure has the wrong structure")
        if len(prediction_rows) != 4 or len(oracle_rows) != 4:
            raise ValueError("reviewed BC3 enclosure requires exactly four rows")
        center = Float64Interval(
            np.asarray(float(_fraction(center_record["lower"]))),  # type: ignore[arg-type]
            np.asarray(float(_fraction(center_record["upper"]))),  # type: ignore[arg-type]
        )
        rows = []
        for index, (prediction_row, oracle_row, scale, steps) in enumerate(
            zip(
                prediction_rows,
                oracle_rows,
                FORMAL_SCALES,
                FORMAL_STEPS_PER_EDGE,
                strict=True,
            )
        ):
            if not isinstance(prediction_row, Mapping) or not isinstance(oracle_row, Mapping):
                raise TypeError("BC3 enclosure row is not a record")
            line = _float_interval(prediction_row["midpoint_line_interval"])  # type: ignore[arg-type]
            q_anti = _float_interval(oracle_row["q_anti_interval"])  # type: ignore[arg-type]
            density = _float_interval(oracle_row["density_interval"])  # type: ignore[arg-type]
            if prediction_row["lattice"] != oracle_row["lattice"]:
                raise ValueError("prediction/oracle lattice records differ")
            dynamic_error = C1 * scale / steps + C2 * scale * scale / steps
            local_remainder = 14 * scale + Fraction(27863, 32000 * steps)
            density_bound = density_envelope(scale, steps)
            q_minus_line = q_anti - line
            line_density_minus_center = line / (scale * scale) - center
            density_minus_center = density - center
            width = Fraction.from_float(float(density.upper)) - Fraction.from_float(float(density.lower))
            conjuncts = {
                "density_width_at_most_1e_minus_6": width <= Fraction(1, 1_000_000),
                "density_upper_strictly_negative": float(density.upper) < 0.0,
                "q_anti_minus_midpoint_within_dynamic_error": _subset_of_symmetric(
                    q_minus_line, dynamic_error
                ),
                "midpoint_density_minus_center_within_local_remainder": _subset_of_symmetric(
                    line_density_minus_center,
                    local_remainder,
                ),
                "density_minus_center_within_total_envelope": _subset_of_symmetric(
                    density_minus_center,
                    density_bound,
                ),
            }
            rows.append(
                {
                    "row_index": index,
                    "row_role": ("development_regression" if index < 2 else "locked_synthetic_holdout"),
                    "scale": fraction_item(scale),
                    "steps_per_edge": steps,
                    "density_interval": density.jsonable_scalar(),
                    "midpoint_line_interval": line.jsonable_scalar(),
                    "center_form_interval": center.jsonable_scalar(),
                    "dynamic_error": fraction_item(dynamic_error),
                    "local_remainder": fraction_item(local_remainder),
                    "total_density_envelope": fraction_item(density_bound),
                    "conjuncts": conjuncts,
                    "passed": all(conjuncts.values()),
                }
            )
    except (KeyError, TypeError, ValueError, ZeroDivisionError, FloatingPointError) as exc:
        return {
            "status": f"FAIL_INVALID_OR_VIOLATING_ENCLOSURE:{type(exc).__name__}",
            "rows": [],
            "all_rows_pass": False,
        }
    all_rows_pass = all(row["passed"] for row in rows)
    return {
        "status": (
            "AUTHENTICATED_DIRECTED_ENCLOSURES_PASS" if all_rows_pass else "FAIL_DIRECTED_ENCLOSURE_CONJUNCT"
        ),
        "rows": rows,
        "all_rows_pass": all_rows_pass,
    }
