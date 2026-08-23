"""Independent exact counted-response oracle with no geometry dependency."""

from __future__ import annotations

from fractions import Fraction

from .exact import dot, matrix_vector, real_fraction, vector_add
from .generator import branch_bundle, current_derivatives, current_row
from .pipeline import OracleCapability


def _independent_response() -> tuple[tuple[Fraction, ...], tuple[Fraction, ...]]:
    bundle = branch_bundle()
    bias, diffusion, _t = bundle.center
    current = current_row(bias, diffusion)
    current_first = current_derivatives()
    lags = tuple(matrix_vector(bundle.drazin, tangent) for tangent in bundle.tangents)
    one_form = tuple(real_fraction(dot(current, lag), label="oracle B") for lag in lags)
    derivatives = [[Fraction(0) for _ in range(3)] for _ in range(3)]
    for component in range(3):
        for axis in range(3):
            derivative_lag = vector_add(
                matrix_vector(bundle.drazin_derivatives[axis], bundle.tangents[component]),
                matrix_vector(bundle.drazin, bundle.second_tangents[component][axis]),
            )
            derivatives[component][axis] = real_fraction(
                dot(current_first[axis], lags[component]) + dot(current, derivative_lag),
                label="oracle derivative",
            )
    curvature = (
        derivatives[2][1] - derivatives[1][2],
        derivatives[0][2] - derivatives[2][0],
        derivatives[1][0] - derivatives[0][1],
    )
    return one_form, curvature


def exact_oracle_record(capability: OracleCapability) -> dict[str, object]:
    if type(capability) is not OracleCapability or not capability.authentic():
        raise RuntimeError("oracle requires an authentic exact capability")
    one_form, curvature = _independent_response()
    return {
        "authority": "independent_exact_generator_Drazin_oracle",
        "accepted_inputs": "generator_primitives_plus_authenticated_criterion_digest",
        "capability_payload_sha256": capability.payload_sha256,
        "capability_payload_authenticated": True,
        "prediction_or_geometry_payload_received": False,
        "B": one_form,
        "F": curvature,
    }
