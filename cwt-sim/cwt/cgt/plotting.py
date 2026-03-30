from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

_LABEL_TO_CODE = {
    "R1": 0,
    "R2": 1,
    "R3": 2,
    "R4": 3,
    "unresolved": 4,
}


def load_json(path: Path) -> dict:
    with path.open() as fh:
        return json.load(fh)


def _array(values) -> np.ndarray:
    return np.asarray(values, dtype=float)


def _extent(scan: dict) -> list[float]:
    grid_u = _array(scan["grid_u"])
    grid_v = _array(scan["grid_v"])
    return [float(grid_v[0]), float(grid_v[-1]), float(grid_u[0]), float(grid_u[-1])]


def _save_numeric_grid(values, scan: dict, title: str, outpath: Path, colorbar_label: str) -> None:
    arr = _array(values)
    fig, ax = plt.subplots(figsize=(6.2, 5.0))
    image = ax.imshow(arr, origin="lower", aspect="auto", extent=_extent(scan))
    ax.set_title(title)
    ax.set_xlabel(scan["control_names"][1])
    ax.set_ylabel(scan["control_names"][0])
    cbar = fig.colorbar(image, ax=ax)
    cbar.set_label(colorbar_label)
    fig.tight_layout()
    fig.savefig(outpath, dpi=160)
    plt.close(fig)


def _save_category_grid(
    labels: list[list[str]], scan: dict, title: str, outpath: Path, value_order: list[str]
) -> None:
    code_map = {label: idx for idx, label in enumerate(value_order)}
    arr = np.asarray([[code_map.get(cell, len(value_order)) for cell in row] for row in labels], dtype=float)
    fig, ax = plt.subplots(figsize=(6.2, 5.0))
    image = ax.imshow(
        arr,
        origin="lower",
        aspect="auto",
        extent=_extent(scan),
        cmap="tab10",
        vmin=0,
        vmax=max(len(value_order) - 1, 1),
    )
    ax.set_title(title)
    ax.set_xlabel(scan["control_names"][1])
    ax.set_ylabel(scan["control_names"][0])

    if arr.shape[0] <= 11 and arr.shape[1] <= 11:
        grid_u = _array(scan["grid_u"])
        grid_v = _array(scan["grid_v"])
        for i, u in enumerate(grid_u):
            for j, v in enumerate(grid_v):
                ax.text(float(v), float(u), str(labels[i][j]), ha="center", va="center", fontsize=6)

    cbar = fig.colorbar(image, ax=ax, ticks=list(range(len(value_order))))
    cbar.ax.set_yticklabels(value_order)
    fig.tight_layout()
    fig.savefig(outpath, dpi=160)
    plt.close(fig)


def _collect_loop_runs(loops: dict) -> list[dict]:
    rows: list[dict] = []
    for pair in loops.get("pair_results", []):
        for orientation in ("ccw", "cw"):
            run = dict(pair[orientation])
            run["pair_trusted_r1"] = bool(pair.get("pair_trusted_r1", False))
            rows.append(run)
    return rows


def _scatter_with_fit(
    x: np.ndarray,
    y: np.ndarray,
    trusted: np.ndarray,
    xlabel: str,
    ylabel: str,
    title: str,
    slope: float | None,
    outpath: Path,
) -> None:
    fig, ax = plt.subplots(figsize=(6.2, 5.0))
    trusted_mask = trusted.astype(bool)
    if np.any(trusted_mask):
        ax.scatter(x[trusted_mask], y[trusted_mask], label="trusted")
    if np.any(~trusted_mask):
        ax.scatter(x[~trusted_mask], y[~trusted_mask], marker="x", label="excluded")
    if slope is not None and x.size > 0:
        xlim = max(np.max(np.abs(x)), 1e-12)
        xs = np.linspace(-xlim, xlim, 200)
        ax.plot(xs, slope * xs, label="fit-through-origin")
    ax.axhline(0.0, linewidth=0.8)
    ax.axvline(0.0, linewidth=0.8)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    if x.size > 0:
        ax.legend()
    fig.tight_layout()
    fig.savefig(outpath, dpi=160)
    plt.close(fig)


def plot_metric_heatmap(scan: dict, outpath: Path) -> None:
    _save_numeric_grid(scan["metric_trace"], scan, "Metric trace", outpath, "tr(g)")


def plot_curvature_heatmap(scan: dict, outpath: Path) -> None:
    _save_numeric_grid(scan["curvature"], scan, "Curvature magnitude/sign", outpath, "F_uv")


def plot_coherence_heatmap(scan: dict, outpath: Path) -> None:
    _save_numeric_grid(scan["coherence"], scan, "Coherence", outpath, "coherence")


def plot_overlap_heatmap(scan: dict, outpath: Path) -> None:
    _save_numeric_grid(scan["avg_overlap"], scan, "Average overlap", outpath, "avg overlap")


def plot_softness_heatmap(scan: dict, outpath: Path) -> None:
    _save_numeric_grid(scan["operator_softness"], scan, "Operator softness", outpath, "softness")


def plot_regime_map(scan: dict, outpath: Path) -> None:
    _save_category_grid(
        scan["regime_map"], scan, "Regime map", outpath, ["R1", "R2", "R3", "R4", "unresolved"]
    )


def plot_branch_map(scan: dict, outpath: Path) -> bool:
    branch_data = scan.get("branch_continuation", {})
    labels = branch_data.get("persistent_branch_id_map")
    if labels is None:
        return False
    ordered = sorted({cell for row in labels for cell in row})
    _save_category_grid(labels, scan, "Persistent branch ID map", outpath, ordered)
    return True


def plot_response_vs_flux(loops: dict, outpath: Path) -> None:
    rows = _collect_loop_runs(loops)
    x = np.asarray([row["signed_flux"] for row in rows], dtype=float)
    y = np.asarray([row["response"] for row in rows], dtype=float)
    trusted = np.asarray([row["trusted_r1"] for row in rows], dtype=bool)
    slope = loops.get("summary", {}).get("fit_response_vs_signed_flux", {}).get("slope")
    _scatter_with_fit(x, y, trusted, "signed flux", "response", "Response vs signed flux", slope, outpath)


def plot_response_vs_area(loops: dict, outpath: Path) -> None:
    rows = _collect_loop_runs(loops)
    x = np.asarray([row["signed_area"] for row in rows], dtype=float)
    y = np.asarray([row["response"] for row in rows], dtype=float)
    trusted = np.asarray([row["trusted_r1"] for row in rows], dtype=bool)
    slope = loops.get("summary", {}).get("fit_response_vs_signed_area", {}).get("slope")
    _scatter_with_fit(x, y, trusted, "signed area", "response", "Response vs signed area", slope, outpath)


def plot_orientation_gap(loops: dict, outpath: Path) -> None:
    pairs = loops.get("pair_results", [])
    x = np.asarray([pair["flux_magnitude"] for pair in pairs], dtype=float)
    y = np.asarray([pair["orientation_gap"] for pair in pairs], dtype=float)
    trusted = np.asarray([pair.get("pair_trusted_r1", False) for pair in pairs], dtype=bool)
    fig, ax = plt.subplots(figsize=(6.2, 5.0))
    if np.any(trusted):
        ax.scatter(x[trusted], y[trusted], label="trusted pairs")
    if np.any(~trusted):
        ax.scatter(x[~trusted], y[~trusted], marker="x", label="excluded pairs")
    ax.axhline(0.0, linewidth=0.8)
    ax.set_xlabel("flux magnitude")
    ax.set_ylabel("orientation gap")
    ax.set_title("Orientation gap vs flux magnitude")
    if x.size > 0:
        ax.legend()
    fig.tight_layout()
    fig.savefig(outpath, dpi=160)
    plt.close(fig)


def generate_benchmark_plots(scan: dict, loops: dict, output_dir: Path) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    artifacts: dict[str, str] = {}

    metric_path = output_dir / "metric_heatmap.png"
    plot_metric_heatmap(scan, metric_path)
    artifacts["metric_heatmap"] = str(metric_path)

    curvature_path = output_dir / "curvature_heatmap.png"
    plot_curvature_heatmap(scan, curvature_path)
    artifacts["curvature_heatmap"] = str(curvature_path)

    coherence_path = output_dir / "coherence_heatmap.png"
    plot_coherence_heatmap(scan, coherence_path)
    artifacts["coherence_heatmap"] = str(coherence_path)

    overlap_path = output_dir / "overlap_heatmap.png"
    plot_overlap_heatmap(scan, overlap_path)
    artifacts["overlap_heatmap"] = str(overlap_path)

    softness_path = output_dir / "softness_heatmap.png"
    plot_softness_heatmap(scan, softness_path)
    artifacts["softness_heatmap"] = str(softness_path)

    regime_path = output_dir / "regime_map.png"
    plot_regime_map(scan, regime_path)
    artifacts["regime_map"] = str(regime_path)

    branch_path = output_dir / "branch_map.png"
    if plot_branch_map(scan, branch_path):
        artifacts["branch_map"] = str(branch_path)

    flux_path = output_dir / "response_vs_flux.png"
    plot_response_vs_flux(loops, flux_path)
    artifacts["response_vs_flux"] = str(flux_path)

    area_path = output_dir / "response_vs_area.png"
    plot_response_vs_area(loops, area_path)
    artifacts["response_vs_area"] = str(area_path)

    gap_path = output_dir / "orientation_gap.png"
    plot_orientation_gap(loops, gap_path)
    artifacts["orientation_gap"] = str(gap_path)

    return artifacts
