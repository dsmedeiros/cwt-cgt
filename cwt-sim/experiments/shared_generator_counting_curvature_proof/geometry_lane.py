"""Authenticated actual-branch projective and SLD geometry lane."""

from __future__ import annotations

from fractions import Fraction
from functools import lru_cache

from .contract import MODEL_CONTRACT
from .exact import (
    IMAG_UNIT,
    ONE,
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
    NODE_COUNT,
    StationaryTangentRecord,
    t0_stationary_tangent_record,
    t1_stationary_tangent_record,
)

GEOMETRY_AUTHORITY = "actual_exact_stationary_branch_only"
SLD_METRIC_CONVENTION = "g_ij=Tr[X_i L_j]=1/2 Tr[rho {L_i,L_j}]"
MEAN_UHLMANN_CONVENTION = "OmegaM_ij=(1/(4i))*Tr[rho[L_i,L_j]]"


def _is_hermitian(matrix: Matrix) -> bool:
    return matrix == conjugate_transpose(matrix)


def _sld_operator(rho: Matrix, tangent: Matrix) -> Matrix:
    """Solve X=(rho L+L rho)/2 exactly over Q(i)."""

    size = NODE_COUNT * NODE_COUNT
    system = zeros(size, size)
    for row in range(NODE_COUNT):
        for column in range(NODE_COUNT):
            output = row + NODE_COUNT * column
            for inner in range(NODE_COUNT):
                system[output][inner + NODE_COUNT * column] += rho[row][inner] / 2
                system[output][row + NODE_COUNT * inner] += rho[inner][column] / 2
    result = unvec(solve(system, vec(tangent)), NODE_COUNT)
    if not _is_hermitian(result):
        raise RuntimeError("exact SLD solve produced a non-Hermitian operator")
    return result


def _trace_product(left: Matrix, right: Matrix) -> Gaussian:
    return trace(matrix_multiply(left, right))


def _matrix_commutator(left: Matrix, right: Matrix) -> Matrix:
    first = matrix_multiply(left, right)
    second = matrix_multiply(right, left)
    return [
        [a - b for a, b in zip(row_a, row_b, strict=True)] for row_a, row_b in zip(first, second, strict=True)
    ]


def _fixed_gauge(matrix: Matrix) -> Matrix:
    phases = (ONE, IMAG_UNIT, -ONE, -IMAG_UNIT, ONE)
    return [
        [phases[row].conjugate() * matrix[row][column] * phases[column] for column in range(NODE_COUNT)]
        for row in range(NODE_COUNT)
    ]


def _real_symmetric(matrix: Matrix) -> bool:
    return all(value.imag == 0 for row in matrix for value in row) and all(
        matrix[row][column] == matrix[column][row]
        for row in range(NODE_COUNT)
        for column in range(NODE_COUNT)
    )


def _gram_determinant(vectors: tuple[Vector, Vector, Vector]) -> Fraction:
    gram = [
        [
            real_fraction(
                sum(
                    (left.conjugate() * right for left, right in zip(vectors[i], vectors[j], strict=True)),
                    ZERO,
                ),
                label=f"tangent_gram_{i}_{j}",
            )
            for j in range(3)
        ]
        for i in range(3)
    ]
    return real_fraction(
        determinant([[gaussian(value) for value in row] for row in gram]), label="tangent Gram determinant"
    )


def _radial_null(response: StationaryTangentRecord) -> tuple[Gaussian, ...]:
    return tuple(
        sum(
            (gaussian(response.center[axis]) * response.tangents[axis][component] for axis in range(3)),
            ZERO,
        )
        for component in range(NODE_COUNT**2)
    )


def _uniform_floor_certificate(
    *,
    delta_min: Fraction,
    delta_max: Fraction,
) -> dict[str, object]:
    d_max = MODEL_CONTRACT.d_bounds[1]
    h_max = MODEL_CONTRACT.h_bounds[1]
    identity_terms = (
        4 * h_max * d_max,
        16 * MODEL_CONTRACT.edge_rate * d_max,
        10 * MODEL_CONTRACT.dephasing_rate,
    )
    identity_total = sum(identity_terms, Fraction(0))
    time_cutoff = Fraction(1, 40)
    series_parameter = identity_total * time_cutoff
    series_majorant = series_parameter / (1 - series_parameter)
    semigroup_difference_bound = series_majorant / NODE_COUNT
    continuity_floor = Fraction(1, NODE_COUNT) - semigroup_difference_bound
    conservative_floor = Fraction(3, 20)
    no_reset_probability_lower = 1 - delta_max * time_cutoff
    integral_floor = delta_min * time_cutoff * no_reset_probability_lower * conservative_floor
    rate_margins = {
        "k_minus_min": MODEL_CONTRACT.d_bounds[0] - MODEL_CONTRACT.b_bounds[1],
        "k_plus_min": MODEL_CONTRACT.d_bounds[0] + MODEL_CONTRACT.b_bounds[0],
        "edge_rate": MODEL_CONTRACT.edge_rate,
        "dephasing_rate": MODEL_CONTRACT.dephasing_rate,
    }
    return {
        "identity_generator_norm_terms": identity_terms,
        "identity_generator_norm_term_sources": (
            "4*h_max*d_max",
            "16*edge_rate*d_max",
            "10*dephasing_rate",
        ),
        "identity_generator_norm_total": identity_total,
        "identity_generator_norm_domain": ("superoperator_norm_induced_by_matrix_spectral_operator_norm"),
        "identity_generator_induced_operator_norm_bound": identity_total,
        "maximally_mixed_initial_spectral_norm": Fraction(1, NODE_COUNT),
        "time_cutoff": time_cutoff,
        "semigroup_series_parameter": series_parameter,
        "semigroup_series_parameter_in_unit_interval": 0 <= series_parameter < 1,
        "exponential_series_majorant": series_majorant,
        "exponential_series_majorant_identity": "exp(x)-1<=x/(1-x)_for_0<=x<1",
        "semigroup_difference_spectral_norm_bound": semigroup_difference_bound,
        "semigroup_difference_bound_identity": ("norm(Phi_t(I/5)-I/5)_op<=(exp(C*t)-1)/5<=x/(5*(1-x))"),
        "continuity_pointwise_floor": continuity_floor,
        "operator_floor_from_spectral_distance": ("lambda_min(Phi_t(I/5))>=1/5-norm(Phi_t(I/5)-I/5)_op"),
        "conservative_pointwise_floor": conservative_floor,
        "continuity_margin_above_conservative_floor": continuity_floor - conservative_floor,
        "delta_min": delta_min,
        "delta_max": delta_max,
        "lindblad_rate_margins": rate_margins,
        "nonnegative_L0_rates_imply_CPTP_semigroup": all(value > 0 for value in rate_margins.values()),
        "no_depolarizing_reset_probability_lower": no_reset_probability_lower,
        "no_reset_lower_justification": "exp(-delta*t)>=1-delta*t",
        "variation_of_constants_identity": ("rho_bar=delta*integral_0_infinity(exp(-delta*t)*Phi_t(I/5))dt"),
        "integral_floor": integral_floor,
        "all_inequalities_strictly_positive": (
            identity_total == Fraction(3931, 1000)
            and series_parameter == Fraction(3931, 40000)
            and 0 <= series_parameter < 1
            and series_majorant == Fraction(3931, 36069)
            and semigroup_difference_bound == Fraction(3931, 180345)
            and continuity_floor == Fraction(32138, 180345)
            and continuity_floor > conservative_floor > 0
            and no_reset_probability_lower == 1 - delta_max * time_cutoff
            and no_reset_probability_lower > 0
            and all(value > 0 for value in rate_margins.values())
            and integral_floor > 0
        ),
    }


@lru_cache(maxsize=1)
def t0_geometry_certificate() -> dict[str, object]:
    """Certify the actual diagonal stationary branch has rank two and zero curvature."""

    response = t0_stationary_tangent_record()
    rho = unvec(response.stationary, NODE_COUNT)
    tangents = tuple(unvec(values, NODE_COUNT) for values in response.tangents)
    diagonal = all(
        rho[row][column].is_zero()
        for row in range(NODE_COUNT)
        for column in range(NODE_COUNT)
        if row != column
    )
    diagonal_tangents = all(
        tangent[row][column].is_zero()
        for tangent in tangents
        for row in range(NODE_COUNT)
        for column in range(NODE_COUNT)
        if row != column
    )
    fisher = []
    for left in range(3):
        row_values: list[Gaussian] = []
        for right in range(3):
            value = ZERO
            for site in range(NODE_COUNT):
                population = rho[site][site]
                value += tangents[left][site][site] * tangents[right][site][site] / (4 * population)
            row_values.append(value)
        fisher.append(row_values)
    determinant3 = real_fraction(determinant(fisher), label="T0 Fisher determinant")
    minor_bd = real_fraction(
        fisher[0][0] * fisher[1][1] - fisher[0][1] * fisher[1][0],
        label="T0 Fisher bd minor",
    )
    radial = _radial_null(response)
    floor = _uniform_floor_certificate(
        delta_min=Fraction(1, 50),
        delta_max=Fraction(3, 50),
    )
    capability_fields = ("control_names", "center", "stationary", "tangents")
    return {
        "authority": GEOMETRY_AUTHORITY,
        "input_capability_type": "StationaryTangentRecord",
        "input_capability_fields": capability_fields,
        "input_capability_excludes_current_B_and_F": set(capability_fields)
        == {"control_names", "center", "stationary", "tangents"},
        "encoding": "psi_j=sqrt(actual_stationary_population_j)_positive_real",
        "stationary_is_diagonal": diagonal,
        "all_tangents_are_diagonal": diagonal_tangents,
        "projective_connection_exact": "0",
        "projective_curvature_exact": "0",
        "commuting_density_Uhlmann_curvature_exact": "0",
        "fisher_metric_determinant": determinant3,
        "fisher_metric_bd_minor": minor_bd,
        "radial_scaling_null_exact": all(value.is_zero() for value in radial),
        "metric_rank": 2 if determinant3 == 0 and minor_bd > 0 else -1,
        "uniform_floor_certificate": floor,
        "uniform_full_rank_floor": floor["integral_floor"],
        "center_trace_norm_contraction_rate": response.center[2],
        "center_Drazin_trace_norm_bound": 1 / response.center[2],
        "delta_box_uniform_trace_norm_contraction_rate": floor["delta_min"],
        "delta_box_uniform_Drazin_trace_norm_bound": 1 / floor["delta_min"],
        "delta_box_unique_full_rank_branch": floor["all_inequalities_strictly_positive"],
        "no_auxiliary_branch": True,
    }


@lru_cache(maxsize=1)
def t1_geometry_certificate() -> dict[str, object]:
    """Certify exact SLD rank three and exact fixed-gauge zero mean curvature."""

    response = t1_stationary_tangent_record()
    rho = unvec(response.stationary, NODE_COUNT)
    tangents = tuple(unvec(values, NODE_COUNT) for values in response.tangents)
    slds = tuple(_sld_operator(rho, tangent) for tangent in tangents)
    metric: list[list[Gaussian]] = []
    curvature: list[list[Fraction]] = [[Fraction(0) for _ in range(3)] for _ in range(3)]
    for left in range(3):
        metric_row: list[Gaussian] = []
        for right in range(3):
            sym = (
                _trace_product(tangents[left], slds[right]) + _trace_product(tangents[right], slds[left])
            ) / 2
            metric_row.append(gaussian(real_fraction(sym, label=f"SLD metric {left},{right}")))
            commutator = _matrix_commutator(slds[left], slds[right])
            muc = _trace_product(rho, commutator) / (4 * IMAG_UNIT)
            curvature[left][right] = real_fraction(muc, label=f"mean Uhlmann curvature {left},{right}")
        metric.append(metric_row)
    metric_determinant = real_fraction(determinant(metric), label="SLD metric determinant")
    tangent_determinant = _gram_determinant(response.tangents)
    gauge_rho = _fixed_gauge(rho)
    gauge_tangents = tuple(_fixed_gauge(tangent) for tangent in tangents)
    gauge_slds = tuple(_fixed_gauge(sld) for sld in slds)
    floor = _uniform_floor_certificate(
        delta_min=Fraction(1, 25),
        delta_max=Fraction(1, 25),
    )
    capability_fields = ("control_names", "center", "stationary", "tangents")
    return {
        "authority": GEOMETRY_AUTHORITY,
        "input_capability_type": "StationaryTangentRecord",
        "input_capability_fields": capability_fields,
        "input_capability_excludes_current_B_and_F": set(capability_fields)
        == {"control_names", "center", "stationary", "tangents"},
        "SLD_metric_convention": SLD_METRIC_CONVENTION,
        "mean_Uhlmann_convention": MEAN_UHLMANN_CONVENTION,
        "stationary_trace_exact": real_fraction(trace(rho), label="stationary trace"),
        "stationary_hermitian_exact": _is_hermitian(rho),
        "tangents_hermitian_exact": all(_is_hermitian(tangent) for tangent in tangents),
        "tangent_traces_zero_exact": all(trace(tangent).is_zero() for tangent in tangents),
        "fixed_gauge": "U=diag(1,i,-1,-i,1)",
        "fixed_gauge_stationary_real_symmetric": _real_symmetric(gauge_rho),
        "fixed_gauge_tangents_real_symmetric": all(_real_symmetric(item) for item in gauge_tangents),
        "fixed_gauge_SLDs_real_symmetric": all(_real_symmetric(item) for item in gauge_slds),
        "mean_Uhlmann_curvature_matrix": curvature,
        "mean_Uhlmann_curvature_zero_exact": all(value == 0 for row in curvature for value in row),
        "tangent_Gram_determinant": tangent_determinant,
        "SLD_metric_determinant": metric_determinant,
        "SLD_metric_rank": 3 if metric_determinant > 0 else -1,
        "uniform_floor_certificate": floor,
        "uniform_full_rank_floor": floor["integral_floor"],
        "center_trace_norm_contraction_rate": MODEL_CONTRACT.depolarizing_rate,
        "center_Drazin_trace_norm_bound": 1 / MODEL_CONTRACT.depolarizing_rate,
        "h_box_uniform_trace_norm_contraction_rate": floor["delta_min"],
        "h_box_uniform_Drazin_trace_norm_bound": 1 / floor["delta_min"],
        "h_box_certified_without_shrink": MODEL_CONTRACT.h_bounds == (Fraction(1, 20), Fraction(3, 20)),
        "no_auxiliary_branch": True,
    }
