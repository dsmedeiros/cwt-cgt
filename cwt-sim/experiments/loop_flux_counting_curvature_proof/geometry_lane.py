"""Actual stationary-branch SLD and mean-Uhlmann geometry lane."""

from __future__ import annotations

from fractions import Fraction
from functools import lru_cache

from .contract import MODEL_CONTRACT
from .exact import (
    IMAG_UNIT,
    ZERO,
    Gaussian,
    Matrix,
    Vector,
    conjugate_transpose,
    determinant,
    gaussian,
    matrix_multiply,
    real_fraction,
    solve,
    trace,
    unvec,
    vec,
    zeros,
)
from .generator import (
    N,
    branch_bundle,
    build_branch_bundle,
    cartesian_branch_bundle,
    chord,
    chord_derivatives,
    derivative_identities,
    drazin_identities,
    hamiltonian,
)

GEOMETRY_AUTHORITY = "actual_exact_stationary_branch_sld_only"


def _is_hermitian(matrix: Matrix) -> bool:
    return matrix == conjugate_transpose(matrix)


def _trace_product(left: Matrix, right: Matrix) -> Gaussian:
    return trace(matrix_multiply(left, right))


def _commutator(left: Matrix, right: Matrix) -> Matrix:
    from .exact import matrix_subtract

    return matrix_subtract(matrix_multiply(left, right), matrix_multiply(right, left))


def _sld(rho: Matrix, tangent: Matrix) -> Matrix:
    size = N * N
    system = zeros(size, size)
    for row in range(N):
        for column in range(N):
            output = row + N * column
            for inner in range(N):
                system[output][inner + N * column] += rho[row][inner] / 2
                system[output][row + N * inner] += rho[inner][column] / 2
    return unvec(solve(system, vec(tangent)), N)


def _gram_determinant(vectors: tuple[Vector, ...]) -> Fraction:
    gram = []
    for left in vectors:
        row = []
        for right in vectors:
            value = sum(
                (a.conjugate() * b for a, b in zip(left, right, strict=True)),
                ZERO,
            )
            row.append(value)
        gram.append(row)
    return real_fraction(determinant(gram), label="tangent Gram determinant")


def flux_record() -> dict[str, object]:
    bias, diffusion, t = MODEL_CONTRACT.center
    del bias
    value = chord(t)
    first, second = chord_derivatives(t)
    line = diffusion * MODEL_CONTRACT.line_coherent_scale
    wilson = gaussian(line * line) * value
    reverse = wilson.conjugate()
    cycle = MODEL_CONTRACT.loop_orientation
    gauge_exponents = [0 for _ in range(N)]
    for source, destination in zip(cycle[:-1], cycle[1:], strict=True):
        gauge_exponents[destination] += 1
        gauge_exponents[source] -= 1
    phases = (gaussian(1), IMAG_UNIT, gaussian(-1), -IMAG_UNIT, gaussian(1))
    h = hamiltonian(diffusion, t)
    gauged_wilson = gaussian(1)
    for source, destination in zip(cycle[:-1], cycle[1:], strict=True):
        gauged_wilson *= phases[destination] * h[destination][source] * phases[source].conjugate()
    b_low, b_high = MODEL_CONTRACT.b_bounds
    d_low, d_high = MODEL_CONTRACT.d_bounds
    t_low, t_high = MODEL_CONTRACT.t_bounds
    del b_low, b_high
    return {
        "authority": "exact_Cayley_chord_and_oriented_Wilson_product",
        "chart": "z(t)=r*(1+i*t)/(1-i*t)",
        "radius_squared": value.real * value.real + value.imag * value.imag,
        "radius_squared_expected": Fraction(1, 400),
        "center_z": value,
        "center_z_t": first,
        "center_z_tt": second,
        "center_expected_z": Gaussian(Fraction(3, 100), Fraction(1, 25)),
        "center_expected_z_t": Gaussian(Fraction(-8, 125), Fraction(6, 125)),
        "center_expected_z_tt": Gaussian(Fraction(-16, 625), Fraction(-88, 625)),
        "loop_orientation": MODEL_CONTRACT.loop_orientation,
        "matrix_index_convention": "H_destination_source",
        "oriented_cycle": "0_to_1_to_2_to_0",
        "Wilson_H10_H21_H02": wilson,
        "Wilson_expected": Gaussian(Fraction(243, 16_000_000), Fraction(81, 4_000_000)),
        "reverse_cycle_Wilson": reverse,
        "reverse_is_conjugate": reverse == wilson.conjugate(),
        "box_denominator_positive": 1 + t_low * t_low > 0 and 1 + t_high * t_high > 0,
        "box_imaginary_flux_positive": (
            d_low > 0 and d_high > 0 and t_low > 0 and MODEL_CONTRACT.chord_radius > 0
        ),
        "diagonal_gauge_exponent_coefficients": tuple(gauge_exponents),
        "diagonal_gauge_exponents_cancel": all(item == 0 for item in gauge_exponents),
        "constant_diagonal_gauge_Wilson": gauged_wilson,
        "constant_diagonal_gauge_Wilson_equal": gauged_wilson == wilson,
        "node_theta_coboundary_used": False,
        "raw_chord_phase_presented_as_invariant": False,
        "phase_phi_derivative_at_center": Fraction(8, 5),
    }


def floor_record() -> dict[str, object]:
    path_term = Fraction(49, 500)
    chord_term = Fraction(1, 10)
    jump_term = Fraction(98, 125)
    dephasing_term = Fraction(3)
    total = path_term + chord_term + jump_term + dephasing_term
    cutoff = Fraction(1, 40)
    series_parameter = total * cutoff
    series_majorant = series_parameter / (1 - series_parameter)
    spectral_distance = series_majorant / N
    point_floor = Fraction(1, N) - spectral_distance
    reset_factor = 1 - MODEL_CONTRACT.depolarizing_rate * cutoff
    stationary_floor = Fraction(3, 20) * MODEL_CONTRACT.depolarizing_rate * cutoff * reset_factor
    rate_min_forward = MODEL_CONTRACT.edge_rate * (MODEL_CONTRACT.d_bounds[0] + MODEL_CONTRACT.b_bounds[0])
    rate_min_reverse = MODEL_CONTRACT.edge_rate * (MODEL_CONTRACT.d_bounds[0] - MODEL_CONTRACT.b_bounds[1])
    return {
        "authority": "derived_operator_norm_series_and_depolarizing_reset_floor",
        "minimum_forward_rate": rate_min_forward,
        "minimum_reverse_rate": rate_min_reverse,
        "path_commutator_norm_bound": path_term,
        "chord_commutator_norm_bound": chord_term,
        "jump_norm_bound": jump_term,
        "dephasing_norm_bound": dephasing_term,
        "induced_operator_norm_budget": total,
        "time_cutoff": cutoff,
        "series_parameter": series_parameter,
        "series_parameter_less_than_one": series_parameter < 1,
        "exp_minus_one_majorant": series_majorant,
        "spectral_distance_from_identity_over_five": spectral_distance,
        "pointwise_floor": point_floor,
        "pointwise_floor_above_three_twentieths": point_floor > Fraction(3, 20),
        "reset_probability_lower": reset_factor,
        "stationary_full_rank_floor": stationary_floor,
        "trace_norm_contraction_rate": MODEL_CONTRACT.depolarizing_rate,
        "Drazin_trace_norm_bound": 1 / MODEL_CONTRACT.depolarizing_rate,
        "expected_exact_values": {
            "minimum_forward_rate": Fraction(43, 1000),
            "minimum_reverse_rate": Fraction(31, 1000),
            "induced_operator_norm_budget": Fraction(1991, 500),
            "series_parameter": Fraction(1991, 20000),
            "exp_minus_one_majorant": Fraction(1991, 18009),
            "spectral_distance": Fraction(1991, 90045),
            "pointwise_floor": Fraction(16018, 90045),
            "stationary_floor": Fraction(2997, 20_000_000),
            "contraction": Fraction(1, 25),
            "Drazin": Fraction(25),
        },
    }


def _constant_gauge(matrix: Matrix) -> Matrix:
    phases = (gaussian(1), IMAG_UNIT, gaussian(-1), -IMAG_UNIT, gaussian(1))
    return [
        [phases[row].conjugate() * matrix[row][column] * phases[column] for column in range(N)]
        for row in range(N)
    ]


def _geometry_summary(bundle) -> dict[str, object]:
    rho = unvec(bundle.stationary, N)
    tangents = tuple(unvec(item, N) for item in bundle.tangents)
    slds = tuple(_sld(rho, tangent) for tangent in tangents)
    metric = [
        [
            gaussian(
                real_fraction(
                    (
                        _trace_product(tangents[left], slds[right])
                        + _trace_product(tangents[right], slds[left])
                    )
                    / 2,
                    label="summary metric",
                )
            )
            for right in range(3)
        ]
        for left in range(3)
    ]
    curvature = [
        [
            real_fraction(
                _trace_product(rho, _commutator(slds[left], slds[right])) / (4 * IMAG_UNIT),
                label="summary curvature",
            )
            for right in range(3)
        ]
        for left in range(3)
    ]
    return {
        "metric_determinant": real_fraction(determinant(metric), label="summary determinant"),
        "curvature_vector": (curvature[1][2], curvature[2][0], curvature[0][1]),
    }


@lru_cache(maxsize=1)
def flux_conjugation_record() -> dict[str, object]:
    conjugate_center = (
        MODEL_CONTRACT.center[0],
        MODEL_CONTRACT.center[1],
        -MODEL_CONTRACT.center[2],
    )
    summary = _geometry_summary(build_branch_bundle(center=conjugate_center))
    canonical = geometry_record()
    return {
        "authority": "independent_exact_recompute_at_chord_conjugate_t_to_minus_t",
        "conjugate_center": conjugate_center,
        "Wilson_flux_reversed": chord(conjugate_center[2]) == chord(MODEL_CONTRACT.center[2]).conjugate(),
        "conjugate_metric_determinant": summary["metric_determinant"],
        "conjugate_mean_Uhlmann_vector": summary["curvature_vector"],
        "componentwise_oddness_assumed": False,
        "canonical_mean_Uhlmann_vector": canonical["mean_Uhlmann_vector"],
        "predeclared_rule": (
            "recompute the actual stationary branch after t->-t; only Wilson conjugation is assumed"
        ),
    }


@lru_cache(maxsize=1)
def geometry_record() -> dict[str, object]:
    bundle = branch_bundle()
    rho = unvec(bundle.stationary, N)
    tangents = tuple(unvec(item, N) for item in bundle.tangents)
    slds = tuple(_sld(rho, tangent) for tangent in tangents)
    metric: list[list[Gaussian]] = []
    curvature: list[list[Fraction]] = [[Fraction(0) for _ in range(3)] for _ in range(3)]
    for left in range(3):
        metric_row = []
        for right in range(3):
            sym = (
                _trace_product(tangents[left], slds[right]) + _trace_product(tangents[right], slds[left])
            ) / 2
            metric_row.append(gaussian(real_fraction(sym, label="SLD metric")))
            curvature[left][right] = real_fraction(
                _trace_product(rho, _commutator(slds[left], slds[right])) / (4 * IMAG_UNIT),
                label="mean Uhlmann curvature",
            )
        metric.append(metric_row)
    vector_order = (
        curvature[1][2],
        curvature[2][0],
        curvature[0][1],
    )
    gauged_rho = _constant_gauge(rho)
    gauged_tangents = tuple(_constant_gauge(item) for item in tangents)
    gauged_slds = tuple(_sld(gauged_rho, item) for item in gauged_tangents)
    gauged_metric = [
        [
            real_fraction(_trace_product(gauged_tangents[left], gauged_slds[right]), label="gauge metric")
            for right in range(3)
        ]
        for left in range(3)
    ]
    gauged_curvature = [
        [
            real_fraction(
                _trace_product(gauged_rho, _commutator(gauged_slds[left], gauged_slds[right]))
                / (4 * IMAG_UNIT),
                label="gauge curvature",
            )
            for right in range(3)
        ]
        for left in range(3)
    ]
    phase_first, _phase_second = chord_derivatives(MODEL_CONTRACT.center[2])
    cartesian_x = zeros(N, N)
    cartesian_y = zeros(N, N)
    cartesian_x[0][2] = cartesian_x[2][0] = gaussian(1)
    cartesian_y[0][2], cartesian_y[2][0] = IMAG_UNIT, -IMAG_UNIT
    from .exact import matrix_add, matrix_scale
    from .generator import _commutator_superoperator

    cartesian_pullback = matrix_add(
        matrix_scale(_commutator_superoperator(cartesian_x), phase_first.real),
        matrix_scale(_commutator_superoperator(cartesian_y), phase_first.imag),
    )
    ambient = cartesian_branch_bundle()
    ambient_tangents = tuple(unvec(item, N) for item in ambient.tangents)
    ambient_slds = tuple(_sld(rho, tangent) for tangent in ambient_tangents)
    ambient_curvature = [
        [
            real_fraction(
                _trace_product(rho, _commutator(ambient_slds[left], ambient_slds[right])) / (4 * IMAG_UNIT),
                label="ambient Cartesian mean Uhlmann curvature",
            )
            for right in range(4)
        ]
        for left in range(4)
    ]
    cartesian_to_t_pullback = (
        phase_first.real * ambient_curvature[1][2] + phase_first.imag * ambient_curvature[1][3],
        phase_first.real * ambient_curvature[2][0] + phase_first.imag * ambient_curvature[3][0],
        ambient_curvature[0][1],
    )
    cartesian_curvature_antisymmetric = all(
        ambient_curvature[left][right] == -ambient_curvature[right][left]
        for left in range(4)
        for right in range(4)
    )
    return {
        "authority": GEOMETRY_AUTHORITY,
        "stationary_trace": real_fraction(trace(rho), label="stationary trace"),
        "stationary_hermitian": _is_hermitian(rho),
        "tangents_hermitian": all(_is_hermitian(item) for item in tangents),
        "SLDs_hermitian": all(_is_hermitian(item) for item in slds),
        "tangent_traces_zero": all(trace(item).is_zero() for item in tangents),
        "drazin_identities": drazin_identities(bundle),
        "derivative_identities": derivative_identities(bundle),
        "tangent_Gram_determinant": _gram_determinant(bundle.tangents),
        "SLD_metric": metric,
        "SLD_metric_determinant": real_fraction(determinant(metric), label="SLD determinant"),
        "mean_Uhlmann_matrix": curvature,
        "mean_Uhlmann_vector_order": MODEL_CONTRACT.two_form_vector_order,
        "mean_Uhlmann_vector": vector_order,
        "mean_Uhlmann_signs": tuple(1 if item > 0 else -1 for item in vector_order),
        "all_mean_Uhlmann_components_nonzero": all(item != 0 for item in vector_order),
        "constant_diagonal_gauge_metric_equal": gauged_metric
        == [[item.real for item in row] for row in metric],
        "constant_diagonal_gauge_curvature_equal": gauged_curvature == curvature,
        "cartesian_quadrature_pullback_Wt_equal": cartesian_pullback == bundle.generator_first[2],
        "cartesian_control_order": ("b", "d", "x", "y"),
        "cartesian_chord_jacobian_dt": (phase_first.real, phase_first.imag),
        "cartesian_mean_Uhlmann_matrix": ambient_curvature,
        "cartesian_to_t_mean_Uhlmann_pullback": cartesian_to_t_pullback,
        "cartesian_to_t_mean_Uhlmann_pullback_equal": cartesian_to_t_pullback == vector_order,
        "cartesian_mean_Uhlmann_antisymmetric": cartesian_curvature_antisymmetric,
        "geometry_capability_fields": ("generator", "stationary", "tangents"),
        "geometry_received_current_or_response": False,
    }
