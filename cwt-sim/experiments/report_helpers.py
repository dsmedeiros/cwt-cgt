from __future__ import annotations

import math
from typing import Sequence

import numpy as np


def fs_histogram(fs_steps: Sequence[float], bins: Sequence[float] | None = None) -> dict:
    """Return a histogram of Fubini–Study step sizes."""

    arr = np.asarray(list(fs_steps), dtype=float)
    if arr.size == 0:
        return {"bins": [], "counts": []}
    if bins is None:
        bins = np.linspace(0.0, 0.2, num=11)
    counts, edges = np.histogram(arr, bins=bins)
    return {"bins": [float(edge) for edge in edges], "counts": [int(x) for x in counts]}


def render_health_banner(
    pass_rate: float,
    fs_hist: dict,
    omega_ci_widths: Sequence[float] | None,
) -> list[str]:
    """Render a standard health summary banner for experiment reports."""

    lines = ["## Health summary", ""]

    if math.isnan(pass_rate):
        lines.append("- s_min pass rate: not available")
    else:
        lines.append(f"- s_min pass rate: {pass_rate:.3%}")

    bins = fs_hist.get("bins", []) if isinstance(fs_hist, dict) else []
    counts = fs_hist.get("counts", []) if isinstance(fs_hist, dict) else []
    if bins and counts:
        bin_str = ", ".join(f"{edge:.3f}" for edge in bins)
        count_str = ", ".join(str(int(c)) for c in counts)
        lines.append("- FS step histogram:")
        lines.append(f"  - bin edges: {bin_str}")
        lines.append(f"  - counts: {count_str}")
    else:
        lines.append("- FS step histogram: not available")

    widths = []
    if omega_ci_widths is not None:
        for value in omega_ci_widths:
            try:
                width = float(value)
            except (TypeError, ValueError):
                continue
            if math.isfinite(width):
                widths.append(width)
    if widths:
        arr = np.asarray(widths, dtype=float)
        mean_width = float(arr.mean())
        max_width = float(arr.max())
        lines.append(f"- Ω CI width mean: {mean_width:.3e} (max {max_width:.3e})")
    else:
        lines.append("- Ω CI widths: not collected")

    lines.append("")
    return lines


__all__ = ["fs_histogram", "render_health_banner"]
