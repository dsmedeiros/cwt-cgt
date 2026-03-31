from __future__ import annotations

import numpy as np

from ._geom_compat import normalize_probabilities
from .models import BenchmarkDefinition, BranchState, CandidateBranch


def stationary_from_row_stochastic(kernel: np.ndarray) -> np.ndarray:
    eigvals, eigvecs = np.linalg.eig(kernel.T)
    idx = int(np.argmin(np.abs(eigvals - 1.0)))
    vec = np.real(eigvecs[:, idx])
    vec = np.maximum(vec, 1e-12)
    return normalize_probabilities(vec)


def _make_line_kernel(k_left: float, k_right: float) -> np.ndarray:
    k_left = float(np.clip(k_left, 0.04, 0.44))
    k_right = float(np.clip(k_right, 0.04, 0.44))
    return np.array(
        [
            [1.0 - k_left, k_left, 0.0],
            [k_left, 1.0 - k_left - k_right, k_right],
            [0.0, k_right, 1.0 - k_right],
        ],
        dtype=float,
    )


def _branch_a(u: float, v: float) -> BranchState:
    a = float(np.clip(0.18 + 0.10 * u, 0.04, 0.42))
    b = float(np.clip(0.18 - 0.10 * u, 0.04, 0.42))
    kernel = np.array([[1.0 - a, a], [b, 1.0 - b]], dtype=float)
    p = stationary_from_row_stochastic(kernel)
    theta = np.array([v, v], dtype=float)
    return BranchState(p=p, theta=theta, kernel=kernel, extras={"u": float(u), "v": float(v)})


def _branch_b_variant(u: float, v: float, *, phase_sign: float = 1.0, tilt_shift: float = 0.0) -> BranchState:
    k_left = float(np.clip(0.22 + 0.08 * v + 0.08 * u, 0.04, 0.44))
    k_right = float(np.clip(0.22 + 0.08 * v - 0.08 * u, 0.04, 0.44))
    kernel = _make_line_kernel(k_left, k_right)
    base = stationary_from_row_stochastic(kernel)
    tilt = np.exp(
        np.array(
            [
                0.42 * u + 0.28 * v + tilt_shift,
                -0.08 * u - 0.05 * v,
                -0.34 * u - 0.23 * v - tilt_shift,
            ],
            dtype=float,
        )
    )
    p = normalize_probabilities(base * tilt)
    phi = phase_sign * 0.18 * u * (1.0 + 0.30 * v) + 0.04 * tilt_shift
    theta = np.array([-phi, 0.0, phi], dtype=float)
    return BranchState(
        p=p, theta=theta, kernel=kernel,
        extras={"u": float(u), "v": float(v), "tilt_shift": float(tilt_shift)},
    )


def _branch_c_variant(u: float, v: float, *, chirality: float = 1.0, tilt_shift: float = 0.0) -> BranchState:
    k_cw = float(np.clip(0.18 + 0.10 * u, 0.04, 0.40))
    k_ccw = float(np.clip(0.18 - 0.10 * u, 0.04, 0.40))
    kernel = np.zeros((3, 3), dtype=float)
    for node in range(3):
        kernel[node, node] = 1.0 - k_cw - k_ccw
        kernel[node, (node + 1) % 3] = k_cw
        kernel[node, (node - 1) % 3] = k_ccw
    base = stationary_from_row_stochastic(kernel)
    tilt = np.exp(
        np.array(
            [
                0.85 * u + 0.50 * v + tilt_shift,
                -0.70 * u + 0.35 * u * v,
                -0.55 * v - 0.25 * u * v - tilt_shift,
            ],
            dtype=float,
        )
    )
    p = normalize_probabilities(base * tilt)
    phi = chirality * (0.70 * v + 0.45 * u * v + 0.15 * u) + 0.06 * tilt_shift
    theta = np.array([phi, 0.0, -phi], dtype=float)
    return BranchState(
        p=p, theta=theta, kernel=kernel,
        extras={"u": float(u), "v": float(v), "chirality": float(chirality)},
    )


def _branch_d(bias: float, diffusion: float) -> BranchState:
    k_plus = float(np.clip(diffusion + bias, 0.02, 0.46))
    k_minus = float(np.clip(diffusion - bias, 0.02, 0.46))
    kernel = np.zeros((5, 5), dtype=float)
    kernel[0, 0] = 1.0 - k_plus
    kernel[0, 1] = k_plus
    for node in range(1, 4):
        kernel[node, node - 1] = k_minus
        kernel[node, node + 1] = k_plus
        kernel[node, node] = 1.0 - k_plus - k_minus
    kernel[4, 3] = k_minus
    kernel[4, 4] = 1.0 - k_minus
    p = stationary_from_row_stochastic(kernel)
    theta = np.zeros(5, dtype=float)
    return BranchState(p=p, theta=theta, kernel=kernel, extras={"b": float(bias), "d": float(diffusion)})


def _branch_f_variant(u: float, v: float, *, sign: float) -> BranchState:
    k_left = float(np.clip(0.20 + 0.04 * v + 0.03 * np.tanh(u), 0.04, 0.44))
    k_right = float(np.clip(0.20 + 0.04 * v - 0.03 * np.tanh(u), 0.04, 0.44))
    kernel = _make_line_kernel(k_left, k_right)
    base = stationary_from_row_stochastic(kernel)
    amp = 0.75 + 0.35 * max(float(v), 0.0) + 0.20 * abs(float(u))
    shift = 0.10 * float(u)
    tilt = np.exp(np.array([sign * amp + shift, 0.0, -sign * amp - shift], dtype=float))
    p = normalize_probabilities(base * tilt)
    phi = sign * (0.28 + 0.25 * max(float(v), 0.0)) + 0.08 * float(u)
    theta = np.array([-phi, 0.0, phi], dtype=float)
    return BranchState(
        p=p, theta=theta, kernel=kernel,
        extras={"u": float(u), "v": float(v), "sign": float(sign)},
    )


def _softness_from_metric_scale(base: float, slope: float, u: float, v: float) -> float:
    return float(base + slope * (abs(u) + abs(v) + 0.5 * abs(u * v)))


def _candidate(branch_id: str, state: BranchState, **metadata: float | str) -> CandidateBranch:
    return CandidateBranch(branch_id=branch_id, state=state, metadata=dict(metadata))


def _candidates_a(u: float, v: float) -> list[CandidateBranch]:
    return [_candidate("A0", _branch_a(u, v), family="dimer")]


def _candidates_b(u: float, v: float) -> list[CandidateBranch]:
    candidates = [
        _candidate("B0", _branch_b_variant(u, v, phase_sign=1.0, tilt_shift=0.0), family="line_main")
    ]
    if v >= 0.18:
        alpha = float(np.clip((v - 0.18) / 0.42, 0.0, 1.0))
        candidates.append(
            _candidate(
                "B1",
                _branch_b_variant(u, v, phase_sign=-0.60 + 0.10 * alpha, tilt_shift=0.06 + 0.08 * alpha),
                family="line_upper",
                alpha=alpha,
            )
        )
    return candidates


def _candidates_c(u: float, v: float) -> list[CandidateBranch]:
    candidates = [
        _candidate("C0", _branch_c_variant(u, v, chirality=1.0, tilt_shift=0.0), family="ring_main")
    ]
    if v >= 0.22:
        alpha = float(np.clip((v - 0.22) / 0.40, 0.0, 1.0))
        candidates.append(
            _candidate(
                "C1",
                _branch_c_variant(u, v, chirality=0.82 + 0.05 * alpha, tilt_shift=0.05 + 0.10 * alpha),
                family="ring_upper",
                alpha=alpha,
            )
        )
    return candidates


def _candidates_d(u: float, v: float) -> list[CandidateBranch]:
    return [_candidate("D0", _branch_d(u, v), family="walk")]


def _candidates_f(u: float, v: float) -> list[CandidateBranch]:
    return [
        _candidate("F_left", _branch_f_variant(u, v, sign=+1.0), family="bistable_left"),
        _candidate("F_right", _branch_f_variant(u, v, sign=-1.0), family="bistable_right"),
    ]


BENCHMARKS: dict[str, BenchmarkDefinition] = {
    "benchmark_a": BenchmarkDefinition(
        benchmark_id="benchmark_a",
        slug="benchmark_A_dimer",
        description="Two-node dimer zero-curvature sanity check.",
        expected_behavior="Metric active, curvature suppressed, no signed loop law.",
        expected_regime="R1",
        control_names=("u", "v"),
        control_bounds=((-0.8, 0.8), (-0.5, 0.5)),
        candidate_states_fn=_candidates_a,
        primary_observable="final_p1",
        secondary_observable=None,
        default_loop_centers=((0.0, 0.0),),
        default_loop_side_lengths=(0.10, 0.16, 0.22, 0.28),
        softness_fn=lambda u, v: _softness_from_metric_scale(8.33, 0.30, u, v),
        seed_branch_ids={"forward": "A0", "backward": "A0", "loop": "A0"},
        canonical_branch_id="A0",
    ),
    "benchmark_b": BenchmarkDefinition(
        benchmark_id="benchmark_b",
        slug="benchmark_B_line",
        description="Three-node line sensitivity without robust pumping.",
        expected_behavior="Metric hotspots, weak or patchy curvature, no strong loop law.",
        expected_regime="R1",
        control_names=("u", "v"),
        control_bounds=((-0.8, 0.8), (-0.6, 0.6)),
        candidate_states_fn=_candidates_b,
        primary_observable="final_p3",
        secondary_observable="edge_current_23",
        default_loop_centers=((0.0, 0.0), (0.0, 0.20)),
        default_loop_side_lengths=(0.10, 0.16, 0.22),
        softness_fn=lambda u, v: _softness_from_metric_scale(18.0, 8.0, u, v),
        seed_branch_ids={"forward": "B0", "backward": "B1", "loop": "B0"},
        canonical_branch_id="B0",
    ),
    "benchmark_c": BenchmarkDefinition(
        benchmark_id="benchmark_c",
        slug="benchmark_C_ring",
        description="Three-node ring first positive signed-loop benchmark.",
        expected_behavior="Nonzero curvature on a trusted patch and signed loop response.",
        expected_regime="R1",
        control_names=("u", "v"),
        control_bounds=((-0.7, 0.7), (-0.7, 0.7)),
        candidate_states_fn=_candidates_c,
        primary_observable="excess_circulation",
        secondary_observable="final_p1",
        default_loop_centers=((0.0, 0.0), (0.18, 0.0)),
        default_loop_side_lengths=(0.10, 0.16, 0.22),
        softness_fn=lambda u, v: _softness_from_metric_scale(9.0, 6.0, u, v),
        seed_branch_ids={"forward": "C0", "backward": "C1", "loop": "C0"},
        canonical_branch_id="C0",
    ),
    "benchmark_d": BenchmarkDefinition(
        benchmark_id="benchmark_d",
        slug="benchmark_D_random_walk",
        description="Five-node biased random walk with uniform phase.",
        expected_behavior="Metric active, curvature suppressed, no signed loop law.",
        expected_regime="R1",
        control_names=("b", "d"),
        control_bounds=((-0.08, 0.08), (0.10, 0.35)),
        candidate_states_fn=_candidates_d,
        primary_observable="mean_position",
        secondary_observable="final_p5",
        default_loop_centers=((0.0, 0.225), (0.03, 0.225)),
        default_loop_side_lengths=(0.04, 0.06, 0.08),
        softness_fn=lambda u, v: _softness_from_metric_scale(50.0, 150.0, u, 0.0),
        seed_branch_ids={"forward": "D0", "backward": "D0", "loop": "D0"},
        canonical_branch_id="D0",
    ),
    "benchmark_f": BenchmarkDefinition(
        benchmark_id="benchmark_f",
        slug="benchmark_F_bistable_line",
        description="Explicit bistable line benchmark for branch switching and R4 exclusion.",
        expected_behavior="Multi-branch / hysteretic atlas with excluded loop families in the central band.",
        expected_regime="R4",
        control_names=("u", "v"),
        control_bounds=((-0.9, 0.9), (-0.2, 0.8)),
        candidate_states_fn=_candidates_f,
        primary_observable="final_p3",
        secondary_observable="final_p1",
        default_loop_centers=((0.0, 0.0), (0.70, 0.0), (-0.70, 0.0)),
        default_loop_side_lengths=(0.18, 0.30),
        softness_fn=lambda u, v: _softness_from_metric_scale(22.0, 11.0, u, v),
        seed_branch_ids={"forward": "F_left", "backward": "F_right", "loop": "F_left"},
        canonical_branch_id="F_left",
    ),
}


def get_benchmark(benchmark_id: str) -> BenchmarkDefinition:
    try:
        return BENCHMARKS[benchmark_id]
    except KeyError as exc:
        raise KeyError(f"Unknown benchmark: {benchmark_id}") from exc
