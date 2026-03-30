from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass(frozen=True)
class TopologyConfig:
    mesh: int = 41
    mass_values: tuple[float, ...] = tuple(np.linspace(-3.0, 3.0, 25))
    perturbation_values: tuple[float, ...] = (0.0, 0.15)
    representative_masses: tuple[float, ...] = (-2.5, -1.0, 1.0, 2.5)
    gap_floor: float = 0.25


@dataclass(frozen=True)
class BandCase:
    mass: float
    perturbation: float
    chern_number: float
    chern_rounded: int
    min_gap: float
    max_abs_curvature: float
    wilson_winding: float
    curvature: list[list[float]]
    gap_map: list[list[float]]
    wilson_phase_by_ky: list[float]
    grid_kx: list[float]
    grid_ky: list[float]


def _d_vector(kx: float, ky: float, mass: float, perturbation: float) -> np.ndarray:
    eps = float(perturbation)
    dx = np.sin(kx) + 0.10 * eps * np.sin(2.0 * kx) + 0.03 * eps * np.sin(kx + ky)
    dy = np.sin(ky) + 0.08 * eps * np.sin(2.0 * ky) - 0.02 * eps * np.sin(kx - ky)
    dz = mass + np.cos(kx) + np.cos(ky) + 0.15 * eps * np.cos(kx - ky)
    return np.asarray([dx, dy, dz], dtype=float)


def _hamiltonian(kx: float, ky: float, mass: float, perturbation: float) -> np.ndarray:
    dx, dy, dz = _d_vector(kx, ky, mass, perturbation)
    return np.asarray([[dz, dx - 1j * dy], [dx + 1j * dy, -dz]], dtype=complex)


def _lower_band_eigenvector(
    kx: float, ky: float, mass: float, perturbation: float
) -> tuple[np.ndarray, float]:
    h = _hamiltonian(kx, ky, mass, perturbation)
    evals, evecs = np.linalg.eigh(h)
    idx = int(np.argmin(evals))
    gap = float(np.real(evals[1] - evals[0]))
    vec = np.asarray(evecs[:, idx], dtype=complex)
    norm = np.linalg.norm(vec)
    if norm <= 0.0:
        vec = np.asarray([1.0 + 0.0j, 0.0 + 0.0j], dtype=complex)
    else:
        vec = vec / norm
    if abs(vec[0]) > 1e-12:
        vec = vec * np.exp(-1j * np.angle(vec[0]))
    return vec, gap


def _link(a: np.ndarray, b: np.ndarray) -> complex:
    ov = np.vdot(a, b)
    mag = abs(ov)
    if mag <= 1e-12:
        return 1.0 + 0.0j
    return ov / mag


def _band_grid(
    mesh: int, mass: float, perturbation: float
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    grid_kx = np.linspace(-np.pi, np.pi, mesh, endpoint=False, dtype=float)
    grid_ky = np.linspace(-np.pi, np.pi, mesh, endpoint=False, dtype=float)
    vecs = np.zeros((mesh, mesh, 2), dtype=complex)
    gaps = np.zeros((mesh, mesh), dtype=float)
    for i, kx in enumerate(grid_kx):
        for j, ky in enumerate(grid_ky):
            vec, gap = _lower_band_eigenvector(float(kx), float(ky), mass, perturbation)
            vecs[i, j] = vec
            gaps[i, j] = gap
    return grid_kx, grid_ky, vecs, gaps


def _fhs_curvature(vecs: np.ndarray) -> np.ndarray:
    mesh_x, mesh_y = vecs.shape[:2]
    curvature = np.zeros((mesh_x, mesh_y), dtype=float)
    for i in range(mesh_x):
        ip = (i + 1) % mesh_x
        for j in range(mesh_y):
            jp = (j + 1) % mesh_y
            ux = _link(vecs[i, j], vecs[ip, j])
            uy = _link(vecs[i, j], vecs[i, jp])
            ux_jp = _link(vecs[i, jp], vecs[ip, jp])
            uy_ip = _link(vecs[ip, j], vecs[ip, jp])
            curvature[i, j] = float(np.angle(ux * uy_ip * np.conj(ux_jp) * np.conj(uy)))
    return curvature


def _chern_number_from_curvature(curvature: np.ndarray) -> float:
    return float(np.sum(curvature) / (2.0 * np.pi))


def _wilson_phase_by_ky(vecs: np.ndarray) -> np.ndarray:
    mesh_x, mesh_y = vecs.shape[:2]
    phases = np.zeros(mesh_y, dtype=float)
    for j in range(mesh_y):
        prod = 1.0 + 0.0j
        for i in range(mesh_x):
            prod *= _link(vecs[i, j], vecs[(i + 1) % mesh_x, j])
        phases[j] = float(np.angle(prod))
    return np.unwrap(phases)


def _wilson_winding(phases: np.ndarray) -> float:
    if phases.size < 2:
        return 0.0
    return float(-(phases[-1] - phases[0]) / (2.0 * np.pi))


def compute_band_case(mesh: int, mass: float, perturbation: float) -> BandCase:
    grid_kx, grid_ky, vecs, gaps = _band_grid(mesh, mass, perturbation)
    curvature = _fhs_curvature(vecs)
    chern = _chern_number_from_curvature(curvature)
    rounded = int(np.rint(chern))
    wilson = _wilson_phase_by_ky(vecs)
    return BandCase(
        mass=float(mass),
        perturbation=float(perturbation),
        chern_number=float(chern),
        chern_rounded=rounded,
        min_gap=float(np.min(gaps)),
        max_abs_curvature=float(np.max(np.abs(curvature))),
        wilson_winding=float(_wilson_winding(wilson)),
        curvature=curvature.tolist(),
        gap_map=gaps.tolist(),
        wilson_phase_by_ky=wilson.tolist(),
        grid_kx=grid_kx.tolist(),
        grid_ky=grid_ky.tolist(),
    )


def _summarize_plateaus(
    mass_values: np.ndarray, chern_values: np.ndarray, gap_values: np.ndarray, gap_floor: float
) -> list[dict]:
    plateaus: list[dict] = []
    if mass_values.size == 0:
        return plateaus
    start = 0
    current = int(np.rint(chern_values[0]))
    for idx in range(1, mass_values.size + 1):
        changed = idx == mass_values.size or int(np.rint(chern_values[idx])) != current
        if changed:
            sl = slice(start, idx)
            plateaus.append(
                {
                    "chern_rounded": current,
                    "mass_min": float(mass_values[sl][0]),
                    "mass_max": float(mass_values[sl][-1]),
                    "min_gap": float(np.min(gap_values[sl])),
                    "gap_protected": bool(np.min(gap_values[sl]) > gap_floor),
                    "count": int(idx - start),
                }
            )
            if idx < mass_values.size:
                start = idx
                current = int(np.rint(chern_values[idx]))
    return plateaus


def topology_benchmark_payload(output_root: Path, config: TopologyConfig | None = None) -> dict:
    cfg = config or TopologyConfig()
    benchmark_dir = output_root / "benchmark_E_topology_torus"
    benchmark_dir.mkdir(parents=True, exist_ok=True)

    mass_values = np.asarray(cfg.mass_values, dtype=float)
    sweeps: list[dict] = []
    representative: dict[str, dict] = {}

    for perturbation in cfg.perturbation_values:
        cherns = []
        gaps = []
        rows = []
        for mass in mass_values:
            case = compute_band_case(cfg.mesh, float(mass), float(perturbation))
            cherns.append(case.chern_number)
            gaps.append(case.min_gap)
            rows.append(
                {
                    "mass": case.mass,
                    "chern_number": case.chern_number,
                    "chern_rounded": case.chern_rounded,
                    "min_gap": case.min_gap,
                    "wilson_winding": case.wilson_winding,
                }
            )
        sweeps.append(
            {
                "perturbation": float(perturbation),
                "rows": rows,
                "plateaus": _summarize_plateaus(
                    mass_values, np.asarray(cherns, dtype=float), np.asarray(gaps, dtype=float), cfg.gap_floor
                ),
            }
        )

    for perturbation in cfg.perturbation_values:
        for mass in cfg.representative_masses:
            case = compute_band_case(cfg.mesh, float(mass), float(perturbation))
            key = f"mass_{mass:+.1f}_eps_{perturbation:.2f}".replace("+", "p").replace("-", "m")
            representative[key] = {
                "mass": case.mass,
                "perturbation": case.perturbation,
                "chern_number": case.chern_number,
                "chern_rounded": case.chern_rounded,
                "min_gap": case.min_gap,
                "max_abs_curvature": case.max_abs_curvature,
                "wilson_winding": case.wilson_winding,
                "curvature": case.curvature,
                "gap_map": case.gap_map,
                "wilson_phase_by_ky": case.wilson_phase_by_ky,
                "grid_kx": case.grid_kx,
                "grid_ky": case.grid_ky,
            }

    payload = {
        "benchmark": "benchmark_e_topology",
        "slug": "benchmark_E_topology_torus",
        "description": "Auxiliary periodic two-band torus benchmark for legitimate topological claims.",
        "model": "Perturbed Qi-Wu-Zhang lower-band benchmark on (k_x, k_y) ∈ T².",
        "mesh": int(cfg.mesh),
        "gap_floor": float(cfg.gap_floor),
        "mass_values": mass_values.tolist(),
        "perturbation_values": [float(x) for x in cfg.perturbation_values],
        "sweeps": sweeps,
        "representative_cases": representative,
        "notes": [
            "Integer Chern claims are only reported in this periodic, gapped auxiliary-band sector.",
            "The discrete invariant uses the gauge-invariant Fukui-Hatsugai-Suzuki plaquette formula.",
            "Wilson-loop winding is included as a secondary topology diagnostic and should track the"
            " Chern number while the band gap remains open.",
        ],
    }
    (benchmark_dir / "benchmark_e_topology.json").write_text(json.dumps(payload, indent=2))
    return payload
