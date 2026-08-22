"""Independent exact response oracle with a generator-primitives-only capability."""

from __future__ import annotations

from fractions import Fraction

from .contract import MODEL_CONTRACT, sha256_payload
from .exact import (
    dot,
    matrix_add,
    matrix_multiply,
    matrix_scale,
    matrix_subtract,
    matrix_vector,
    outer,
    real_fraction,
    vector_add,
    vector_scale,
)
from .generator import (
    current_row,
    drazin_inverse,
    liouvillian,
    parameter_derivatives,
    row_derivatives,
    stationary_state,
    trace_row,
)
from .pipeline import OracleCapability

ORACLE_AUTHORITY = "independent_exact_stationary_Drazin_response_from_generator_primitives"


def _t0_generator(bias: Fraction, diffusion: Fraction, depolarizing: Fraction):
    return liouvillian(bias, diffusion, Fraction(0), depolarizing)


def _t1_generator(bias: Fraction, diffusion: Fraction, coherent: Fraction):
    return liouvillian(bias, diffusion, coherent, Fraction(1, 25))


def _frozen_current(bias: Fraction, diffusion: Fraction, _third: Fraction):
    return current_row(bias, diffusion)


def _oracle_response(case: str, center):
    """Independently derive B and dB without the counting response implementation."""

    if case == "T0":
        generator = _t0_generator(*center)
        generator_first, generator_second = parameter_derivatives(_t0_generator, center)
    elif case == "T1":
        generator = _t1_generator(*center)
        generator_first, generator_second = parameter_derivatives(_t1_generator, center)
    else:
        raise RuntimeError("unknown oracle case")
    stationary = stationary_state(generator)
    drazin = drazin_inverse(generator, stationary)
    tangents = tuple(
        vector_scale(matrix_vector(drazin, matrix_vector(derivative, stationary)), -1)
        for derivative in generator_first
    )
    second_tangents = [[[] for _ in range(3)] for _ in range(3)]
    for left in range(3):
        for right in range(3):
            rhs = vector_add(
                matrix_vector(generator_second[left][right], stationary),
                vector_add(
                    matrix_vector(generator_first[left], tangents[right]),
                    matrix_vector(generator_first[right], tangents[left]),
                ),
            )
            second_tangents[left][right] = vector_scale(matrix_vector(drazin, rhs), -1)

    projector = outer(stationary, trace_row())
    inverse_shifted = matrix_add(drazin, projector)
    drazin_derivatives = []
    for axis in range(3):
        shifted_derivative = matrix_add(
            generator_first[axis],
            outer(tangents[axis], trace_row()),
        )
        inverse_derivative = matrix_scale(
            matrix_multiply(
                matrix_multiply(inverse_shifted, shifted_derivative),
                inverse_shifted,
            ),
            -1,
        )
        drazin_derivatives.append(matrix_subtract(inverse_derivative, outer(tangents[axis], trace_row())))

    current = _frozen_current(*center)
    current_derivatives = row_derivatives(_frozen_current, center)
    lag = tuple(matrix_vector(drazin, tangent) for tangent in tangents)
    response = tuple(
        real_fraction(dot(current, value), label=f"oracle_B_{axis}") for axis, value in enumerate(lag)
    )
    derivatives = [[Fraction(0) for _ in range(3)] for _ in range(3)]
    for component in range(3):
        for axis in range(3):
            derivative_lag = vector_add(
                matrix_vector(drazin_derivatives[axis], tangents[component]),
                matrix_vector(drazin, second_tangents[component][axis]),
            )
            derivatives[component][axis] = real_fraction(
                dot(current_derivatives[axis], lag[component]) + dot(current, derivative_lag),
                label=f"oracle_partial_{axis}_B_{component}",
            )
    curvature = (
        derivatives[2][1] - derivatives[1][2],
        derivatives[0][2] - derivatives[2][0],
        derivatives[1][0] - derivatives[0][1],
    )
    return {"B": response, "F": curvature}


def exact_oracle_record(capability: OracleCapability) -> dict[str, object]:
    if (
        capability.experiment_id != "shared_generator_counting_curvature_proof"
        or capability.capability != "frozen_generator_primitives_only"
        or capability.primitive_contract_sha256 != sha256_payload(MODEL_CONTRACT.jsonable())
        or not capability.authentic()
    ):
        raise RuntimeError("oracle capability is invalid")
    t0 = _oracle_response(
        "T0",
        (Fraction(3, 100), Fraction(9, 40), Fraction(1, 25)),
    )
    t1 = _oracle_response(
        "T1",
        (Fraction(3, 100), Fraction(9, 40), Fraction(1, 10)),
    )
    return {
        "authority": ORACLE_AUTHORITY,
        "accepted_inputs": "typed_generator_primitives_plus_authenticated_criterion_digest",
        "capability_payload_sha256": capability.payload_sha256,
        "capability_payload_authenticated": capability.authentic(),
        "criterion_digest_received": True,
        "raw_prediction_values_or_geometry_payload_received": False,
        "T0": t0,
        "T1": t1,
    }
