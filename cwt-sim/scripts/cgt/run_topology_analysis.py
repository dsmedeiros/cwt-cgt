#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

CODE_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = CODE_ROOT / 'src'
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from cwt.cgt.topology import TopologyConfig, topology_benchmark_payload


def _sweep_arrays(payload: dict, perturbation: float) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    for sweep in payload['sweeps']:
        if abs(float(sweep['perturbation']) - float(perturbation)) <= 1e-12:
            masses = np.asarray([row['mass'] for row in sweep['rows']], dtype=float)
            cherns = np.asarray([row['chern_number'] for row in sweep['rows']], dtype=float)
            rounded = np.asarray([row['chern_rounded'] for row in sweep['rows']], dtype=float)
            gaps = np.asarray([row['min_gap'] for row in sweep['rows']], dtype=float)
            return masses, cherns, rounded, gaps
    raise KeyError(f'No sweep found for perturbation={perturbation}')


def _plot_chern_vs_mass(payload: dict, outpath: Path) -> None:
    fig, ax = plt.subplots(figsize=(6.4, 4.8))
    for perturbation in payload['perturbation_values']:
        masses, cherns, rounded, _ = _sweep_arrays(payload, float(perturbation))
        ax.plot(masses, cherns, label=f'Chern (eps={perturbation:.2f})')
        ax.scatter(masses, rounded, s=14, label=f'rounded (eps={perturbation:.2f})')
    ax.axhline(0.0, linewidth=0.8)
    ax.set_xlabel('mass parameter m')
    ax.set_ylabel('Chern number')
    ax.set_title('Topology benchmark: Chern number vs mass')
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(outpath, dpi=160)
    plt.close(fig)


def _plot_gap_vs_mass(payload: dict, outpath: Path) -> None:
    fig, ax = plt.subplots(figsize=(6.4, 4.8))
    for perturbation in payload['perturbation_values']:
        masses, _, _, gaps = _sweep_arrays(payload, float(perturbation))
        ax.plot(masses, gaps, label=f'eps={perturbation:.2f}')
    ax.axhline(float(payload['gap_floor']), linewidth=0.8, linestyle='--', label='gap floor')
    ax.set_xlabel('mass parameter m')
    ax.set_ylabel('minimum direct gap')
    ax.set_title('Topology benchmark: minimum band gap vs mass')
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(outpath, dpi=160)
    plt.close(fig)


def _plot_curvature(case: dict, outpath: Path, title: str) -> None:
    arr = np.asarray(case['curvature'], dtype=float)
    grid_kx = np.asarray(case['grid_kx'], dtype=float)
    grid_ky = np.asarray(case['grid_ky'], dtype=float)
    extent = [float(grid_ky[0]), float(grid_ky[-1]), float(grid_kx[0]), float(grid_kx[-1])]
    fig, ax = plt.subplots(figsize=(6.0, 5.0))
    image = ax.imshow(arr, origin='lower', aspect='auto', extent=extent)
    ax.set_xlabel('$k_y$')
    ax.set_ylabel('$k_x$')
    ax.set_title(title)
    cbar = fig.colorbar(image, ax=ax)
    cbar.set_label('plaquette Berry curvature')
    fig.tight_layout()
    fig.savefig(outpath, dpi=160)
    plt.close(fig)


def _plot_wilson(case: dict, outpath: Path, title: str) -> None:
    ky = np.asarray(case['grid_ky'], dtype=float)
    phases = np.asarray(case['wilson_phase_by_ky'], dtype=float)
    fig, ax = plt.subplots(figsize=(6.0, 4.5))
    ax.plot(ky, phases)
    ax.set_xlabel('$k_y$')
    ax.set_ylabel('unwrapped Wilson phase')
    ax.set_title(title)
    fig.tight_layout()
    fig.savefig(outpath, dpi=160)
    plt.close(fig)


def _write_report(payload: dict, plot_paths: dict[str, Path], output_path: Path) -> None:
    lines: list[str] = []
    lines.append('# CWT-CGT topology benchmark report')
    lines.append('')
    lines.append('This report covers the auxiliary periodic, gapped two-band benchmark used to earn later topological claims. Integer invariants are interpreted only in this toroidal, gapped sector.')
    lines.append('')
    lines.append(f"- Mesh: {payload['mesh']}")
    lines.append(f"- Gap floor for protected plateaus: {payload['gap_floor']}")
    lines.append('')
    for sweep in payload['sweeps']:
        lines.append(f"## perturbation = {sweep['perturbation']:.2f}")
        lines.append('')
        for plateau in sweep['plateaus']:
            lines.append(
                f"- C ≈ {plateau['chern_rounded']} on m ∈ [{plateau['mass_min']:.2f}, {plateau['mass_max']:.2f}] with min gap {plateau['min_gap']:.4f} and gap_protected={plateau['gap_protected']}"
            )
        lines.append('')
    lines.append('## Representative cases')
    lines.append('')
    for key, case in payload['representative_cases'].items():
        lines.append(
            f"- {key}: C = {case['chern_rounded']} (raw {case['chern_number']:.6f}), min gap = {case['min_gap']:.6f}, Wilson winding ≈ {case['wilson_winding']:.6f}"
        )
    lines.append('')
    for key in ['chern_vs_mass', 'gap_vs_mass', 'curvature_topological', 'curvature_topological_perturbed', 'wilson_topological']:
        rel = plot_paths[key].relative_to(output_path.parent)
        lines.append(f'![{key}]({rel.as_posix()})')
        lines.append('')
    output_path.write_text('\n'.join(lines))


def main() -> None:
    parser = argparse.ArgumentParser(description='Run the topology benchmark and generate report artifacts.')
    parser.add_argument('--output-root', type=Path, required=True)
    parser.add_argument('--report-root', type=Path, required=True)
    args = parser.parse_args()

    payload = topology_benchmark_payload(args.output_root, config=TopologyConfig())
    plot_dir = args.report_root / 'plots' / 'topology' / 'benchmark_e'
    plot_dir.mkdir(parents=True, exist_ok=True)

    plot_paths = {
        'chern_vs_mass': plot_dir / 'chern_vs_mass.png',
        'gap_vs_mass': plot_dir / 'gap_vs_mass.png',
        'curvature_topological': plot_dir / 'curvature_mass_m1p0_eps_0p00.png',
        'curvature_topological_perturbed': plot_dir / 'curvature_mass_m1p0_eps_0p15.png',
        'wilson_topological': plot_dir / 'wilson_mass_m1p0_eps_0p00.png',
    }
    _plot_chern_vs_mass(payload, plot_paths['chern_vs_mass'])
    _plot_gap_vs_mass(payload, plot_paths['gap_vs_mass'])
    topological = payload['representative_cases']['mass_m1.0_eps_0.00']
    perturbed = payload['representative_cases']['mass_m1.0_eps_0.15']
    _plot_curvature(topological, plot_paths['curvature_topological'], 'Topology benchmark: curvature map (m=-1.0, eps=0.00)')
    _plot_curvature(perturbed, plot_paths['curvature_topological_perturbed'], 'Topology benchmark: curvature map (m=-1.0, eps=0.15)')
    _plot_wilson(topological, plot_paths['wilson_topological'], 'Topology benchmark: Wilson phase (m=-1.0, eps=0.00)')
    _write_report(payload, plot_paths, args.report_root / 'CWT-CGT_Topology_Benchmark_Report.md')


if __name__ == '__main__':
    main()
