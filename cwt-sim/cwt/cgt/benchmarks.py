from __future__ import annotations

import math

import numpy as np

from ._geom_compat import normalize_probabilities
from .models import BenchmarkDefinition, BranchState, CandidateBranch


def stationary_from_row_stochastic(kernel: np.ndarray) -> np.ndarray:
    eigvals, eigvecs = np.linalg.eig(kernel.T)
    idx = int(np.argmin(np.abs(eigvals - 1.0)))
    vec = np.real(eigvecs[:, idx])
    vec = np.maximum(vec, 1e-12)
    return normalize_probabilities(vec)


def _clip_prob(value: float, low: float, high: float) -> float:
    return float(min(max(value, low), high))


def _line_kernel(length: int, k_plus: float, k_minus: float) -> np.ndarray:
    kernel = np.zeros((length, length), dtype=float)
    kernel[0, 0] = 1.0 - k_plus
    kernel[0, 1] = k_plus
    for node in range(1, length - 1):
        kernel[node, node - 1] = k_minus
        kernel[node, node + 1] = k_plus
        kernel[node, node] = 1.0 - k_plus - k_minus
    kernel[length - 1, length - 2] = k_minus
    kernel[length - 1, length - 1] = 1.0 - k_minus
    return kernel


def _single_candidate(branch_id: str, state: BranchState) -> list[CandidateBranch]:
    return [CandidateBranch(branch_id=branch_id, state=state, metadata={"branch_id": branch_id})]


def _branch_a(u: float, v: float) -> BranchState:
    a = _clip_prob(0.18 + 0.10 * u, 0.04, 0.42)
    b = _clip_prob(0.18 - 0.10 * u, 0.04, 0.42)
    kernel = np.array([[1.0 - a, a], [b, 1.0 - b]], dtype=float)
    p = stationary_from_row_stochastic(kernel)
    theta = np.array([v, v], dtype=float)
    return BranchState(p=p, theta=theta, kernel=kernel, extras={"u": float(u), "v": float(v)})


def _branch_b(u: float, v: float) -> BranchState:
    k_left = _clip_prob(0.22 + 0.08 * v + 0.08 * u, 0.04, 0.44)
    k_right = _clip_prob(0.22 + 0.08 * v - 0.08 * u, 0.04, 0.44)
    stay_mid = max(1.0 - k_left - k_right, 0.04)
    # renormalize middle-row rates if clipping pushed them over budget.
    scale = (1.0 - stay_mid) / max(k_left + k_right, 1e-12)
    k_left *= scale
    k_right *= scale
    kernel = np.array(
        [
            [1.0 - k_left, k_left, 0.0],
            [k_left, 1.0 - k_left - k_right, k_right],
            [0.0, k_right, 1.0 - k_right],
        ],
        dtype=float,
    )
    p = stationary_from_row_stochastic(kernel)
    phi = 0.18 * u * (1.0 + 0.35 * v)
    theta = np.array([-phi, 0.0, phi], dtype=float)
    return BranchState(p=p, theta=theta, kernel=kernel, extras={"u": float(u), "v": float(v)})


def _branch_c(u: float, v: float) -> BranchState:
    k_cw = _clip_prob(0.18 + 0.10 * u, 0.04, 0.38)
    k_ccw = _clip_prob(0.18 - 0.10 * u, 0.04, 0.38)
    kernel = np.zeros((3, 3), dtype=float)
    for node in range(3):
        kernel[node, node] = 1.0 - k_cw - k_ccw
        kernel[node, (node + 1) % 3] = k_cw
        kernel[node, (node - 1) % 3] = k_ccw
    base = stationary_from_row_stochastic(kernel)
    tilt = np.exp(
        np.array(
            [
                0.85 * u + 0.50 * v,
                -0.70 * u + 0.35 * u * v,
                -0.55 * v - 0.25 * u * v,
            ],
            dtype=float,
        )
    )
    p = normalize_probabilities(base * tilt)
    phi = 0.70 * v + 0.45 * u * v + 0.15 * u
    theta = np.array([phi, 0.0, -phi], dtype=float)
    return BranchState(p=p, theta=theta, kernel=kernel, extras={"u": float(u), "v": float(v)})


def _branch_d(bias: float, diffusion: float) -> BranchState:
    k_plus = _clip_prob(diffusion + bias, 0.02, 0.44)
    k_minus = _clip_prob(diffusion - bias, 0.02, 0.44)
    if k_plus + k_minus >= 0.96:
        scale = 0.96 / (k_plus + k_minus)
        k_plus *= scale
        k_minus *= scale
    kernel = _line_kernel(5, k_plus=k_plus, k_minus=k_minus)
    p = stationary_from_row_stochastic(kernel)
    theta = np.zeros(5, dtype=float)
    return BranchState(p=p, theta=theta, kernel=kernel, extras={"b": float(bias), "d": float(diffusion)})


def _branch_f(u: float, v: float, sign: float) -> BranchState:
    # A deliberately wide bistable band: branches are very close near the origin and separate away from it.
    center_closeness = math.exp(-((u / 0.48) ** 2 + (v / 0.58) ** 2))
    separation = 0.010 + 0.040 * (1.0 - center_closeness)
    diffusion = 0.14 + 0.06 * (v + 0.8) / 1.6
    diffusion = _clip_prob(diffusion, 0.08, 0.28)
    bias = 0.012 * u + 0.010 * v + sign * separation
    k_plus = _clip_prob(diffusion + bias, 0.03, 0.44)
    k_minus = _clip_prob(diffusion - bias, 0.03, 0.44)
    if k_plus + k_minus >= 0.96:
        scale = 0.96 / (k_plus + k_minus)
        k_plus *= scale
        k_minus *= scale
    kernel = _line_kernel(4, k_plus=k_plus, k_minus=k_minus)
    base = stationary_from_row_stochastic(kernel)
    tilt_strength = (0.20 + 0.70 * (1.0 - center_closeness)) * float(sign)
    tilt = np.exp(
        np.array(
            [1.00 * tilt_strength, 0.30 * tilt_strength, -0.30 * tilt_strength, -1.00 * tilt_strength],
            dtype=float,
        )
    )
    p = normalize_probabilities(base * tilt)
    phase_amp = float(sign) * (0.18 + 0.30 * (1.0 - center_closeness) + 0.10 * abs(v))
    theta = np.array([phase_amp, 0.35 * phase_amp, -0.35 * phase_amp, -phase_amp], dtype=float)
    return BranchState(
        p=p,
        theta=theta,
        kernel=kernel,
        extras={
            "u": float(u),
            "v": float(v),
            "branch_sign": float(sign),
            "center_closeness": float(center_closeness),
        },
    )


def _candidate_states_a(u: float, v: float) -> list[CandidateBranch]:
    return _single_candidate("main", _branch_a(u, v))


def _candidate_states_b(u: float, v: float) -> list[CandidateBranch]:
    return _single_candidate("main", _branch_b(u, v))


def _candidate_states_c(u: float, v: float) -> list[CandidateBranch]:
    return _single_candidate("main", _branch_c(u, v))


def _candidate_states_d(u: float, v: float) -> list[CandidateBranch]:
    return _single_candidate("main", _branch_d(u, v))


def _candidate_states_f(u: float, v: float) -> list[CandidateBranch]:
    minus = _branch_f(u, v, sign=-1.0)
    plus = _branch_f(u, v, sign=+1.0)
    return [
        CandidateBranch(branch_id="minus", state=minus, metadata={"branch_sign": -1.0}),
        CandidateBranch(branch_id="plus", state=plus, metadata={"branch_sign": +1.0}),
    ]


def _softness_from_metric_scale(base: float, slope: float, u: float, v: float) -> float:
    return float(base + slope * (abs(u) + abs(v) + 0.5 * abs(u * v)))


BENCHMARKS: dict[str, BenchmarkDefinition] = {
    "benchmark_a": BenchmarkDefinition(
        benchmark_id="benchmark_a",
        slug="benchmark_A_dimer",
        description="Two-node dimer zero-curvature sanity check.",
        expected_behavior="Metric active, curvature suppressed, no signed loop law.",
        expected_regime="R1",
        control_names=("u", "v"),
        control_bounds=((-0.8, 0.8), (-0.5, 0.5)),
        candidate_states_fn=_candidate_states_a,
        primary_observable="final_p1",
        secondary_observable=None,
        default_loop_centers=((0.0, 0.0),),
        default_loop_side_lengths=(0.10, 0.16, 0.22, 0.28),
        softness_fn=lambda u, v: _softness_from_metric_scale(8.33, 0.30, u, v),
        seed_branch_ids={"forward": "main", "backward": "main", "loop": "main"},
        canonical_branch_id="main",
    ),
    "benchmark_b": BenchmarkDefinition(
        benchmark_id="benchmark_b",
        slug="benchmark_B_line",
        description="Three-node line sensitivity without robust pumping.",
        expected_behavior="Metric hotspots, weak or patchy curvature, no strong loop law.",
        expected_regime="R1",
        control_names=("u", "v"),
        control_bounds=((-0.8, 0.8), (-0.6, 0.6)),
        candidate_states_fn=_candidate_states_b,
        primary_observable="final_p3",
        secondary_observable="final_p1",
        default_loop_centers=((0.0, 0.0),),
        default_loop_side_lengths=(0.10, 0.16, 0.22, 0.28),
        softness_fn=lambda u, v: _softness_from_metric_scale(18.0, 8.0, u, v),
        seed_branch_ids={"forward": "main", "backward": "main", "loop": "main"},
        canonical_branch_id="main",
    ),
    "benchmark_c": BenchmarkDefinition(
        benchmark_id="benchmark_c",
        slug="benchmark_C_ring",
        description="Three-node ring first positive signed-loop benchmark.",
        expected_behavior="Nonzero curvature on a trusted patch and signed loop response.",
        expected_regime="R1",
        control_names=("u", "v"),
        control_bounds=((-0.7, 0.7), (-0.7, 0.7)),
        candidate_states_fn=_candidate_states_c,
        primary_observable="excess_circulation",
        secondary_observable="final_p1",
        default_loop_centers=((0.0, 0.0),),
        default_loop_side_lengths=(0.10, 0.16, 0.22, 0.28),
        softness_fn=lambda u, v: _softness_from_metric_scale(9.0, 6.0, u, v),
        seed_branch_ids={"forward": "main", "backward": "main", "loop": "main"},
        canonical_branch_id="main",
    ),
    "benchmark_d": BenchmarkDefinition(
        benchmark_id="benchmark_d",
        slug="benchmark_D_random_walk",
        description="Five-node biased random walk with uniform phase.",
        expected_behavior="Metric active, curvature suppressed, no signed loop law.",
        expected_regime="R1",
        control_names=("b", "d"),
        control_bounds=((-0.08, 0.08), (0.10, 0.35)),
        candidate_states_fn=_candidate_states_d,
        primary_observable="mean_position",
        secondary_observable="final_p1",
        default_loop_centers=((0.0, 0.225),),
        default_loop_side_lengths=(0.04, 0.06, 0.08, 0.10),
        softness_fn=lambda u, v: _softness_from_metric_scale(50.0, 150.0, u, 0.0),
        seed_branch_ids={"forward": "main", "backward": "main", "loop": "main"},
        canonical_branch_id="main",
    ),
    "benchmark_f": BenchmarkDefinition(
        benchmark_id="benchmark_f",
        slug="benchmark_F_bistable_line",
        description="Four-node explicitly bistable line benchmark for branch-switching and hysteresis.",
        expected_behavior=(
            "Wide R4 bistable band, forward/backward branch disagreement,"
            " and loop exclusions by construction."
        ),
        expected_regime="R4",
        control_names=("u", "v"),
        control_bounds=((-1.0, 1.0), (-0.8, 0.8)),
        candidate_states_fn=_candidate_states_f,
        primary_observable="final_p4",
        secondary_observable="final_p1",
        default_loop_centers=((0.0, 0.0), (0.7, 0.0), (-0.7, 0.0)),
        default_loop_side_lengths=(0.18, 0.30, 0.42),
        softness_fn=lambda u, v: _softness_from_metric_scale(24.0, 18.0, u, v),
        seed_branch_ids={"forward": "minus", "backward": "plus", "loop": "minus"},
        canonical_branch_id="minus",
    ),
}


def get_benchmark(benchmark_id: str) -> BenchmarkDefinition:
    try:
        return BENCHMARKS[benchmark_id]
    except KeyError as exc:
        raise KeyError(f"Unknown benchmark: {benchmark_id}") from exc
