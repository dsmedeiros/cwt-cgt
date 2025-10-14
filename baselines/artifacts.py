"""Artifact helpers for lightweight baseline experiments."""

from __future__ import annotations

import json
import math
import numbers
import os
import time
from pathlib import Path
from typing import Mapping, Sequence

import numpy as np
import pandas as pd

from baselines.io import DEFAULT_AXIS_MAP_PATH, load_axis_map

__all__ = [
    "ensure_outdir",
    "write_heatmap_png",
    "write_top_tiles",
]


def ensure_outdir(
    model: str,
    out: Path | str | None,
    graph: str,
    seed: int | str,
) -> Path:
    """Create and return the output directory for a baseline run.

    Parameters
    ----------
    model:
        Name of the baseline model (e.g. ``"ising"``).
    out:
        Optional base output directory. When ``None`` the ``CWT_OUTPUT_DIR``
        environment variable is consulted and falls back to the repository-level
        ``artifacts`` directory when unset.
    graph:
        Identifier for the substrate graph used during the run.
    seed:
        Random seed associated with the run.
    """

    if not model:
        raise ValueError("model must be a non-empty string")
    if not graph:
        raise ValueError("graph must be a non-empty string")

    if out is not None:
        base = Path(out)
    else:
        env_value = os.environ.get("CWT_OUTPUT_DIR")
        if env_value:
            base = Path(env_value)
        else:
            base = Path(__file__).resolve().parents[1] / "artifacts"
    timestamp = time.strftime("%Y%m%dT%H%M%S", time.gmtime())
    run_dir = f"{timestamp}__graph={graph}__seed={seed}"
    target = base / "baselines" / model / run_dir
    target.mkdir(parents=True, exist_ok=True)
    return target


def write_heatmap_png(
    metrics_csv: Path | str,
    out_dir: Path | str,
    *,
    filename: str = "omega_abs_heatmap.png",
    axes: Sequence[str] | None = None,
    cmap: str = "magma",
    axis_map: Mapping[str, Mapping[str, str]] | None = None,
    value_column: str = "omega_abs",
    colorbar_label: str | None = None,
) -> Path:
    """Render a |Omega| heatmap from a metrics CSV file."""

    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    data = pd.read_csv(metrics_csv)

    axis_names = _resolve_axes(data, axes)
    specs = _axis_specs(data, axis_names)
    grid = _build_grid(data, specs, value_column=value_column)

    mapping = load_axis_map(DEFAULT_AXIS_MAP_PATH) if axis_map is None else axis_map
    axis_labels = _axis_labels(specs, mapping)
    label = colorbar_label or r"|Ω|"

    # Configure matplotlib lazily to keep import overhead low for CLI tooling.
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    try:  # pragma: no cover - optional dependency
        import seaborn as sns
    except ModuleNotFoundError:  # pragma: no cover - optional dependency
        sns = None

    figure_size = _figure_size(specs)
    fig, ax = plt.subplots(figsize=figure_size)

    mask = ~np.isfinite(grid)
    invert_y_axis = False
    if sns is not None:
        sns.heatmap(
            grid,
            ax=ax,
            cmap=cmap,
            mask=mask,
            xticklabels=[_format_tick(value) for value in specs[1]["values"]],
            yticklabels=[_format_tick(value) for value in specs[0]["values"]],
            cbar_kws={"label": label},
        )
        invert_y_axis = True
    else:
        im = ax.imshow(grid, cmap=cmap, aspect="auto", origin="lower")
        fig.colorbar(im, ax=ax, label=label)
        ax.set_xticks(range(specs[1]["size"]))
        ax.set_xticklabels(
            [_format_tick(value) for value in specs[1]["values"]],
            rotation=45,
            ha="right",
        )
        ax.set_yticks(range(specs[0]["size"]))
        ax.set_yticklabels([_format_tick(value) for value in specs[0]["values"]])

    ax.set_xlabel(axis_labels[specs[1]["name"]])
    ax.set_ylabel(axis_labels[specs[0]["name"]])
    title_text = f"{label} heatmap" if label else r"|Ω| heatmap"
    ax.set_title(title_text)
    if invert_y_axis:
        ax.invert_yaxis()
    fig.tight_layout()

    destination = out_path / filename
    fig.savefig(destination, dpi=150)
    plt.close(fig)
    return destination


def write_top_tiles(
    metrics_csv: Path | str,
    out_dir: Path | str,
    *,
    top_k: int = 10,
    axes: Sequence[str] | None = None,
    axis_map: Mapping[str, Mapping[str, str]] | None = None,
    filename: str = "top_omega_tiles.json",
    value_column: str = "omega_abs",
) -> Path:
    """Persist a JSON document describing the top-|Omega| tiles."""

    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    data = pd.read_csv(metrics_csv)
    axis_names = _resolve_axes(data, axes)
    specs = _axis_specs(data, axis_names)

    if value_column not in data.columns:
        raise KeyError(f"Metrics CSV must include a '{value_column}' column")

    omega_series = pd.to_numeric(data[value_column], errors="coerce")
    omega_array = omega_series.to_numpy(dtype=float)
    valid_mask = np.isfinite(omega_array)

    for spec in specs:
        index_col = spec["index_col"]
        index_series = pd.to_numeric(data[index_col], errors="coerce")
        index_array = index_series.to_numpy(dtype=float)
        valid_mask &= np.isfinite(index_array)

    ordered = data.loc[valid_mask].copy()
    entries: list[dict[str, object]] = []
    if valid_mask.any():
        ordered[value_column] = pd.to_numeric(ordered[value_column], errors="coerce")
        ordered = ordered.sort_values(value_column, ascending=False)
        limit = max(int(top_k), 0)
        if limit > 0:
            ordered = ordered.head(limit)
        else:
            ordered = ordered.iloc[0:0]
        for _, row in ordered.iterrows():
            indices: list[int] = []
            coordinates: dict[str, object] = {}
            for spec in specs:
                raw_index = row[spec["index_col"]]
                index_int = int(float(raw_index))
                indices.append(index_int)
                value = row.get(spec["name"], None)
                if value is None or (isinstance(value, float) and math.isnan(value)):
                    value = spec["values"][index_int]
                coordinates[str(spec["name"])] = _coerce_json_value(value)
            entries.append(
                {
                    "indices": indices,
                    "coordinates": coordinates,
                    "omega_abs": float(row[value_column]),
                }
            )

    mapping = load_axis_map(DEFAULT_AXIS_MAP_PATH) if axis_map is None else axis_map
    axis_metadata = _axis_metadata(specs, mapping)

    payload = {
        "metric": value_column,
        "axes": axis_metadata,
        "grid_shape": [spec["size"] for spec in specs],
        "top_tiles": entries,
    }

    if "omega_abs_proxy" in data.columns:
        proxy_series = pd.to_numeric(data["omega_abs_proxy"], errors="coerce")
        proxy_max = proxy_series.max()
        payload["omega_abs_proxy_max"] = float(proxy_max) if np.isfinite(proxy_max) else None
        for entry, (_, row) in zip(entries, ordered.iterrows()):
            proxy_raw = row.get("omega_abs_proxy", float("nan"))
            try:
                proxy_numeric = float(proxy_raw)
            except (TypeError, ValueError):
                proxy_numeric = float("nan")
            entry["omega_abs_proxy"] = proxy_numeric if np.isfinite(proxy_numeric) else None

    destination = out_path / filename
    with destination.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
    return destination


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _resolve_axes(frame: pd.DataFrame, axes: Sequence[str] | None) -> list[str]:
    if axes:
        if len(axes) != 2:
            raise ValueError("Exactly two axes must be specified")
        return list(axes)

    candidates: list[str] = []
    for column in frame.columns:
        if column.endswith("_index"):
            candidate = column[: -len("_index")]
            if candidate and candidate not in candidates:
                candidates.append(candidate)

    if len(candidates) < 2:
        raise ValueError("Metrics CSV must contain at least two indexed axes")

    return candidates[:2]


def _axis_specs(frame: pd.DataFrame, axes: Sequence[str]) -> list[dict[str, object]]:
    specs: list[dict[str, object]] = []
    for axis in axes:
        index_col = f"{axis}_index"
        if index_col not in frame.columns:
            raise KeyError(f"Missing index column '{index_col}' for axis '{axis}'")

        index_series = pd.to_numeric(frame[index_col], errors="coerce")
        finite_indices = index_series[np.isfinite(index_series)]
        if finite_indices.empty:
            raise ValueError(f"Axis '{axis}' has no finite index entries")

        max_index = int(finite_indices.max())
        size = max_index + 1
        values: list[object] = [None] * size

        if axis in frame.columns:
            for idx, value in (
                frame[[index_col, axis]]
                .dropna(subset=[index_col])
                .itertuples(index=False)
            ):
                index_int = int(float(idx))
                if 0 <= index_int < size:
                    values[index_int] = _coerce_json_value(value)
        for position in range(size):
            if values[position] is None:
                values[position] = position

        specs.append(
            {
                "name": axis,
                "index_col": index_col,
                "size": size,
                "values": values,
            }
        )
    return specs


def _build_grid(
    frame: pd.DataFrame,
    specs: Sequence[Mapping[str, object]],
    *,
    value_column: str,
) -> np.ndarray:
    shape = tuple(int(spec["size"]) for spec in specs)
    grid = np.full(shape, np.nan, dtype=float)

    if value_column not in frame.columns:
        raise KeyError(f"Metrics CSV must include a '{value_column}' column")

    for row in frame.itertuples(index=False):
        omega_value_raw = getattr(row, value_column, None)
        try:
            omega_value = float(omega_value_raw)
        except (TypeError, ValueError):
            continue
        if not math.isfinite(omega_value):
            continue

        coords: list[int] = []
        skip_row = False
        for spec in specs:
            idx_raw = getattr(row, spec["index_col"], None)
            try:
                idx = int(float(idx_raw))
            except (TypeError, ValueError):
                skip_row = True
                break
            if idx < 0 or idx >= int(spec["size"]):
                skip_row = True
                break
            coords.append(idx)
        if skip_row or len(coords) != len(specs):
            continue

        grid[tuple(coords)] = omega_value

    return grid


def _axis_labels(
    specs: Sequence[Mapping[str, object]], mapping: Mapping[str, Mapping[str, str]]
) -> dict[str, str]:
    axes_map = mapping.get("axes", {}) if isinstance(mapping, Mapping) else {}
    labels: dict[str, str] = {}
    for spec in specs:
        name = str(spec["name"])
        label = axes_map.get(name, name)
        labels[name] = str(label)
    return labels


def _axis_metadata(
    specs: Sequence[Mapping[str, object]],
    mapping: Mapping[str, Mapping[str, str]],
) -> list[dict[str, object]]:
    axes_map = mapping.get("axes", {}) if isinstance(mapping, Mapping) else {}
    metadata: list[dict[str, object]] = []
    for spec in specs:
        name = str(spec["name"])
        values = [_coerce_json_value(value) for value in spec["values"]]
        metadata.append(
            {
                "name": name,
                "label": str(axes_map.get(name, name)),
                "size": int(spec["size"]),
                "values": values,
            }
        )
    return metadata


def _format_tick(value: object) -> str:
    if isinstance(value, numbers.Real) and not isinstance(value, bool):
        if math.isnan(float(value)):
            return ""
        if float(value).is_integer():
            return f"{int(value)}"
        return f"{float(value):.3g}"
    return str(value)


def _figure_size(specs: Sequence[Mapping[str, object]]) -> tuple[float, float]:
    height = max(3.0, 1.0 + 0.5 * float(specs[0]["size"]))
    width = max(3.0, 1.0 + 0.5 * float(specs[1]["size"]))
    return (width, height)


def _coerce_json_value(value: object) -> object:
    if isinstance(value, (np.floating,)):
        value = float(value)
    if isinstance(value, (np.integer,)):
        value = int(value)
    if isinstance(value, numbers.Integral) and not isinstance(value, bool):
        return int(value)
    if isinstance(value, numbers.Real) and not isinstance(value, bool):
        if math.isnan(float(value)):
            return None
        return float(value)
    return value
