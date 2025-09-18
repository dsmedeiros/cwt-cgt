"""Wilson loop experiment exploring three control parameters."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Sequence

import networkx as nx
import numpy as np

from cwt.geometry.fs_distance import fs_distance
from cwt.geometry.psi import inner
from cwt.graph.factories import random_regular_digraph
from cwt.graph.substrate import GraphSubstrate, build_substrate
from cwt.orchestrator.scheduler import RunConfig, _psi_at

VALID_AXES = ("rho", "tau", "zeta", "zeta_phase", "kappa")
DEFAULT_BASE = {"rho": 1.5, "tau": 1.75, "zeta": 1.2, "zeta_phase": 0.0, "kappa": 1.0}


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _initial_state(substrate: GraphSubstrate) -> tuple[np.ndarray, np.ndarray]:
    N = substrate.N
    if N == 0:
        return np.zeros((0,), dtype=float), np.zeros((0,), dtype=float)
    p0 = np.full(N, 1.0 / float(N), dtype=float)
    theta0 = np.zeros(N, dtype=float)
    return p0, theta0


def _build_substrate(name: str, seed: int) -> GraphSubstrate:
    key = name.lower()
    if key == "ring3":
        graph = nx.DiGraph()
        edges = [
            (0, 1, 1.0, 0.6),
            (1, 2, 1.0, 1.1),
            (2, 0, 1.0, 1.8),
        ]
        for u, v, weight, delay in edges:
            graph.add_edge(u, v, weight=weight, delay=delay)
        return build_substrate(graph)

    if key == "random_regular":
        base = random_regular_digraph(N=20, out_degree=3, seed=seed)
        graph = nx.DiGraph()
        rng = np.random.default_rng(seed)
        for u, v, data in base.G.edges(data=True):
            weight = float(data.get("weight", 1.0)) * (0.9 + 0.2 * rng.random())
            delay = float(data.get("delay", 1.0)) * (0.5 + rng.random())
            graph.add_edge(u, v, weight=weight, delay=delay)
        return build_substrate(graph)

    raise ValueError(f"Unsupported graph kind: {name}")


def _loop_keypoints(center: Sequence[float], amplitudes: Sequence[float]) -> list[np.ndarray]:
    center_vec = np.asarray(center, dtype=float)
    amp_vec = np.asarray(amplitudes, dtype=float)
    if center_vec.shape != (3,) or amp_vec.shape != (3,):
        raise ValueError("center and amplitudes must be triples aligned with the axes")

    a0, a1, a2 = amp_vec
    offsets = [
        np.array([0.0, -a1, -a2], dtype=float),
        np.array([0.0, +a1, -a2], dtype=float),
        np.array([0.0, +a1, +a2], dtype=float),
        np.array([0.0, -a1, +a2], dtype=float),
        np.array([0.0, -a1, -a2], dtype=float),
        np.array([+a0, -a1, -a2], dtype=float),
        np.array([+a0, 0.0, 0.0], dtype=float),
        np.array([0.0, 0.0, 0.0], dtype=float),
        np.array([0.0, -a1, -a2], dtype=float),
    ]
    return [center_vec + offset for offset in offsets]


def _interpolate_points(
    keypoints: Sequence[np.ndarray],
    *,
    axis_template: dict[str, float],
    axes: Sequence[str],
    steps: int,
    handle_steps: int,
) -> list[dict[str, float]]:
    if len(keypoints) < 2:
        raise ValueError("Need at least two keypoints to construct a loop")

    def _to_lambda(vec: np.ndarray) -> dict[str, float]:
        lam = dict(axis_template)
        for axis, value in zip(axes, vec):
            lam[axis] = float(value)
        return lam

    steps_main = max(int(steps), 2)
    steps_handle = max(int(handle_steps), 2)

    points: list[dict[str, float]] = []
    for idx in range(len(keypoints) - 1):
        start = keypoints[idx]
        end = keypoints[idx + 1]
        seg_steps = steps_main if idx < 4 else steps_handle
        include_start = idx == 0
        direction = end - start
        for step in range(seg_steps):
            if step == 0 and not include_start:
                continue
            t = step / float(seg_steps)
            vec = start + direction * t
            points.append(_to_lambda(vec))
    points.append(_to_lambda(keypoints[-1]))
    return points


def _lambda_key(lam: dict[str, float]) -> tuple[tuple[str, float], ...]:
    return tuple(sorted((key, round(float(value), 12)) for key, value in lam.items()))


def _wilson_phase(psis: Sequence[np.ndarray]) -> tuple[float, list[complex]]:
    if len(psis) < 2:
        raise ValueError("At least two states are required to evaluate the Wilson loop")

    aligned: list[np.ndarray] = [np.asarray(psis[0], dtype=np.complex128)]
    overlaps: list[complex] = []

    for psi in psis[1:]:
        current = aligned[-1]
        candidate = np.asarray(psi, dtype=np.complex128)
        overlap = inner(current, candidate)
        magnitude = float(np.abs(overlap))
        if magnitude > 1e-12:
            phase = np.exp(-1j * np.angle(overlap))
            candidate = candidate * phase
        aligned.append(candidate)
        overlaps.append(inner(current, candidate))

    overlaps.append(inner(aligned[-1], aligned[0]))
    product = complex(1.0, 0.0)
    for value in overlaps:
        product *= value
    return float(np.angle(product)), overlaps


def _fs_statistics(psis: Sequence[np.ndarray]) -> tuple[list[float], float, float]:
    distances: list[float] = []
    for a, b in zip(psis, psis[1:]):
        distances.append(fs_distance(a, b))
    distances.append(fs_distance(psis[-1], psis[0]))
    arr = np.asarray(distances, dtype=float)
    finite = arr[np.isfinite(arr)]
    mean = float(finite.mean()) if finite.size else float("nan")
    p95 = float(np.percentile(finite, 95)) if finite.size else float("nan")
    return distances, mean, p95


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="3D Wilson loop experiment")
    parser.add_argument("--axes3", type=str, nargs=3, choices=VALID_AXES, default=("rho", "tau", "zeta"))
    parser.add_argument(
        "--center", type=float, nargs=3, default=(1.5, 1.75, 1.2), help="Loop centre for the selected axes"
    )
    parser.add_argument(
        "--amplitudes",
        type=float,
        nargs=3,
        default=(0.1, 0.15, 0.12),
        help="Half-width of the loop along each axis",
    )
    parser.add_argument("--steps", type=int, default=24, help="Samples per rectangle edge")
    parser.add_argument("--handle-steps", type=int, default=None, help="Samples along the rho handle")
    parser.add_argument("--settle", type=int, default=40, help="Relaxation steps per sample")
    parser.add_argument("--graph", type=str, choices=("ring3", "random_regular"), default="ring3")
    parser.add_argument("--seed", type=int, default=7, help="Random seed for synthetic graphs")
    parser.add_argument("--eta-q", type=float, default=0.5, help="Q-layer mixing coefficient")
    parser.add_argument("--zeta", type=float, default=0.0, help="Theta coupling strength")
    parser.add_argument("--omega-scale", type=float, default=1.0, help="Scaling applied to intrinsic delays")
    parser.add_argument("--fs-guard", type=float, default=0.2, help="Target p95 bound for Fubini-Study steps")
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).resolve().parent / "artifacts")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    axes = tuple(str(axis) for axis in args.axes3)
    if len(set(axes)) != 3:
        raise ValueError("axes3 must contain three distinct parameter names")

    output_dir = Path(args.output_dir)
    ensure_dir(output_dir)

    substrate = _build_substrate(args.graph, args.seed)
    p0, theta0 = _initial_state(substrate)
    config = RunConfig(eta_q=args.eta_q, zeta=args.zeta, omega_scale=args.omega_scale)

    template = dict(DEFAULT_BASE)
    for axis, value in zip(axes, args.center):
        template[axis] = float(value)

    handle_steps = args.handle_steps if args.handle_steps is not None else max(args.steps // 2, 2)
    keypoints = _loop_keypoints(args.center, args.amplitudes)
    lambda_points = _interpolate_points(
        keypoints,
        axis_template=template,
        axes=axes,
        steps=args.steps,
        handle_steps=handle_steps,
    )

    psi_cache: dict[tuple[tuple[str, float], ...], np.ndarray] = {}
    psi_sequence: list[np.ndarray] = []
    for lam in lambda_points:
        key = _lambda_key(lam)
        if key not in psi_cache:
            psi_cache[key] = _psi_at(substrate, lam, p0, theta0, config, steps=args.settle)
        psi_sequence.append(psi_cache[key])

    phi_forward, overlaps_forward = _wilson_phase(psi_sequence)
    phi_reverse, overlaps_reverse = _wilson_phase(list(reversed(psi_sequence)))

    overlap_magnitudes = [float(np.abs(val)) for val in overlaps_forward]
    min_overlap = float(min(overlap_magnitudes)) if overlap_magnitudes else float("nan")
    max_overlap = float(max(overlap_magnitudes)) if overlap_magnitudes else float("nan")
    distances, fs_mean, fs_p95 = _fs_statistics(psi_sequence)
    guard_exceeded = bool(math.isfinite(fs_p95) and fs_p95 > float(args.fs_guard))

    summary = {
        "axes": list(axes),
        "center": [float(val) for val in args.center],
        "amplitudes": [float(val) for val in args.amplitudes],
        "graph": str(args.graph),
        "seed": int(args.seed),
        "steps_per_edge": int(max(args.steps, 2)),
        "handle_steps": int(max(handle_steps, 2)),
        "settle_steps": int(max(args.settle, 1)),
        "eta_q": float(args.eta_q),
        "zeta": float(args.zeta),
        "omega_scale": float(args.omega_scale),
        "phi_forward": float(phi_forward),
        "phi_reverse": float(phi_reverse),
        "phi_sum": float(phi_forward + phi_reverse),
        "fs_mean": fs_mean,
        "fs_p95": fs_p95,
        "fs_guard": float(args.fs_guard),
        "fs_guard_exceeded": guard_exceeded,
        "overlap_min": min_overlap,
        "overlap_max": max_overlap,
        "overlap_product_abs": float(np.abs(np.prod(overlaps_forward))) if overlaps_forward else float("nan"),
        "loop_points": lambda_points,
        "fs_steps": distances,
        "overlaps_forward": [
            {"magnitude": float(np.abs(val)), "phase": float(np.angle(val))} for val in overlaps_forward
        ],
        "overlaps_reverse": [
            {"magnitude": float(np.abs(val)), "phase": float(np.angle(val))} for val in overlaps_reverse
        ],
    }

    summary_path = output_dir / "summary.json"
    with summary_path.open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2)

    report_lines = [
        "# Wilson loop in three dimensions",
        "",
        f"Axes: {', '.join(axes)}",
        f"Forward Wilson phase: {phi_forward:.6f} rad",
        f"Reverse Wilson phase: {phi_reverse:.6f} rad",
        f"FS mean: {fs_mean:.5f} rad",
        f"FS p95: {fs_p95:.5f} rad (guard {float(args.fs_guard):.5f})",
        f"Guard exceeded: {'yes' if guard_exceeded else 'no'}",
        f"Min overlap magnitude: {min_overlap:.6f}",
        f"Max overlap magnitude: {max_overlap:.6f}",
    ]

    report_path = output_dir / "REPORT.md"
    report_path.write_text("\n".join(report_lines), encoding="utf-8")

    print(f"Forward Wilson phase: {phi_forward:.6f} rad")
    print(f"Reverse Wilson phase: {phi_reverse:.6f} rad")
    print(f"FS p95: {fs_p95:.6f} rad (guard {float(args.fs_guard):.6f})")
    if guard_exceeded:
        print("Warning: FS step guard exceeded.")


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    main()
