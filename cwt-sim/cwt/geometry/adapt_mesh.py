"""Adaptive meshing utilities for curvature estimation."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable, Sequence

import numpy as np

from .curvature import curvature_tile

PlaquetteSample = tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]


@dataclass(slots=True)
class PlaquetteResult:
    """Summary statistics gathered from adaptive plaquette refinement."""

    omega_mean: float
    omega_ci: tuple[float, float]
    min_overlap: float
    depth_used: int
    samples_used: int
    fallback_used: bool = False


def micro_plaquettes(
    Psi_sampler: Callable[[float, float], PlaquetteSample],
    delta_i: float,
    delta_j: float,
    levels: int,
) -> list[tuple[float, float]]:
    """Return the schedule of micro-plaquette step sizes for the requested depth."""

    if levels <= 0:
        return []

    step_i = float(delta_i)
    step_j = float(delta_j)
    if not math.isfinite(step_i) or not math.isfinite(step_j):
        raise ValueError("delta_i and delta_j must be finite scalars.")

    schedule: list[tuple[float, float]] = []
    current_i = step_i
    current_j = step_j
    for _ in range(levels):
        schedule.extend((current_i, current_j) for _ in range(4))
        current_i *= 0.5
        current_j *= 0.5
    return schedule


def _level_steps(delta_i: float, delta_j: float, level: int):
    """Yield the four sub-plaquette step sizes for a refinement level."""

    scale = 0.5 ** (level - 1)
    level_step = (delta_i * scale, delta_j * scale)
    for _ in range(4):
        yield level_step


def _mean_and_ci(samples: Sequence[float]) -> tuple[float, tuple[float, float]]:
    if not samples:
        return float("nan"), (float("nan"), float("nan"))

    count = len(samples)
    mean_val = float(sum(samples) / count)
    if count == 1:
        return mean_val, (mean_val, mean_val)

    variance = sum((value - mean_val) ** 2 for value in samples) / (count - 1)
    variance = max(variance, 0.0)
    std_dev = math.sqrt(variance)
    margin = 1.96 * std_dev / math.sqrt(count)
    return mean_val, (mean_val - margin, mean_val + margin)


def _ci_width(interval: tuple[float, float]) -> float:
    lower, upper = interval
    if not (math.isfinite(lower) and math.isfinite(upper)):
        return float("inf")
    return upper - lower


def curvature_anytime(
    Psi_sampler: Callable[[float, float], PlaquetteSample],
    delta_i: float,
    delta_j: float,
    s_min: float = 0.6,
    ci_tol: float = 0.05,
    max_levels: int = 2,
    max_samples: int = 32,
) -> PlaquetteResult:
    """Iteratively refine plaquette samples until the curvature CI stabilises."""

    if max_levels < 1:
        raise ValueError("max_levels must be at least 1 for adaptive refinement.")

    step_i = float(delta_i)
    step_j = float(delta_j)
    if not math.isfinite(step_i) or step_i == 0.0:
        raise ValueError("delta_i must be a finite non-zero scalar.")
    if not math.isfinite(step_j) or step_j == 0.0:
        raise ValueError("delta_j must be a finite non-zero scalar.")

    min_required = 1 if max_samples < 4 else 4

    accepted: list[float] = []
    attempted: list[tuple[float, float]] = []
    min_overlap = float("inf")
    depth_used = 0

    for level in range(1, max_levels + 1):
        depth_used = level
        for sub_step_i, sub_step_j in _level_steps(step_i, step_j, level):
            if len(accepted) >= max_samples:
                break

            Psi0, Psi_i, Psi_ij, Psi_j = Psi_sampler(sub_step_i, sub_step_j)
            omega, stats = curvature_tile(Psi0, Psi_i, Psi_ij, Psi_j, sub_step_i, sub_step_j)

            overlap = float(stats.get("min_overlap", float("nan")))
            if math.isfinite(overlap):
                min_overlap = min(min_overlap, overlap)
            attempted.append((float(omega), overlap))

            if math.isfinite(overlap) and overlap >= s_min:
                accepted.append(float(omega))

            if len(accepted) >= max_samples:
                break

        if len(accepted) >= min_required:
            _, interval = _mean_and_ci(accepted)
            if _ci_width(interval) <= ci_tol:
                break
        if len(accepted) >= max_samples:
            break

    if math.isinf(min_overlap):
        min_overlap = float("nan")

    samples_used = len(accepted)
    fallback_used = False
    if accepted:
        omega_mean, omega_ci = _mean_and_ci(accepted)
    elif attempted:
        scored = [
            (idx, overlap if math.isfinite(overlap) else -float("inf"), float(omega))
            for idx, (omega, overlap) in enumerate(attempted)
        ]
        scored.sort(key=lambda item: (item[1], abs(item[2]), -item[0]), reverse=True)

        fallback_count = min(len(scored), max(min_required, 1))

        grouped: dict[int, list[tuple[float, float, int, float]]] = {1: [], -1: [], 0: []}
        for idx, overlap, omega in scored:
            if not math.isfinite(omega) or omega == 0.0:
                sign = 0
            elif omega > 0.0:
                sign = 1
            else:
                sign = -1
            grouped[sign].append((overlap, abs(omega), idx, omega))

        def _group_score(items: list[tuple[float, float, int, float]]) -> tuple[float, int]:
            if not items:
                return (-float("inf"), 0)
            weight = sum(max(overlap, 0.0) for overlap, *_ in items)
            return (weight, len(items))

        def _group_tiebreak(
            items: list[tuple[float, float, int, float]],
        ) -> tuple[float, tuple[tuple[float, float, int], ...]]:
            abs_weight = sum(max(overlap, 0.0) * abs_omega for overlap, abs_omega, *_ in items)
            neutral_profile = tuple(
                sorted(((overlap, abs_omega, -idx) for overlap, abs_omega, idx, _ in items), reverse=True)
            )
            return (abs_weight, neutral_profile)

        group_scores = {sign: _group_score(items) for sign, items in grouped.items()}
        best_score = max(group_scores.values())
        candidate_signs = [sign for sign, score in group_scores.items() if score == best_score]
        best_sign = max(candidate_signs, key=lambda sign: _group_tiebreak(grouped[sign]))
        best_items = grouped[best_sign]

        fallback_samples: list[float] = []
        if best_items:
            best_items.sort(key=lambda item: (item[0], item[1], -item[2]), reverse=True)
            fallback_samples = [omega for *_, omega in best_items[:fallback_count]]

        if fallback_samples:
            omega_mean, omega_ci = _mean_and_ci(fallback_samples)
            samples_used = len(fallback_samples)
            fallback_used = True
        else:
            best = scored[0][2]
            omega_mean = best
            omega_ci = (-float("inf"), float("inf"))
            samples_used = 0
            fallback_used = True
    else:
        omega_mean, omega_ci = float("nan"), (float("nan"), float("nan"))

    return PlaquetteResult(
        omega_mean=float(omega_mean),
        omega_ci=(float(omega_ci[0]), float(omega_ci[1])),
        min_overlap=min_overlap,
        depth_used=depth_used,
        samples_used=samples_used,
        fallback_used=fallback_used,
    )


__all__ = ["PlaquetteResult", "micro_plaquettes", "curvature_anytime"]
