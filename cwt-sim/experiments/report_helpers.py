from __future__ import annotations

import math
from dataclasses import dataclass
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


@dataclass(frozen=True)
class ReportHeaderMetrics:
    """Aggregate metrics rendered in the universal report header."""

    min_overlap: float | None = None
    mean_overlap: float | None = None
    pass_rate: float | None = None
    fs_mean: float | None = None
    fs_p95: float | None = None
    omega_ci_mean: float | None = None
    omega_abs_mean: float | None = None
    omega_abs_median: float | None = None
    trace_mean: float | None = None
    trace_min: float | None = None
    trace_max: float | None = None
    phi_flux: float | None = None
    geom_area: float | None = None
    extents: Sequence[str] | None = None
    steps: float | None = None
    R_cw: float | None = None
    R_ccw: float | None = None
    flip_error: float | None = None
    observed_response_per_flux_mean: float | None = None
    observed_response_per_flux_ci: tuple[float, float] | None = None
    spectral_gap: float | None = None
    grad_r: float | None = None


def _format_value(value: float | None, *, precision: str = ".3e") -> str:
    if value is None:
        return "n/a"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "n/a"
    if not math.isfinite(number):
        return "n/a"
    if precision == "percent":
        return f"{number:.3%}"
    if precision == "integer":
        return f"{int(round(number))}"
    return f"{number:{precision}}"


def _format_ci(ci: tuple[float, float] | None) -> str:
    if not ci:
        return "n/a"
    lower, upper = ci
    lower_text = _format_value(lower)
    upper_text = _format_value(upper)
    return f"[{lower_text}, {upper_text}]"


def render_report_header(metrics: ReportHeaderMetrics) -> list[str]:
    """Render the universal diagnostics header for experiment reports."""

    extent_text = "n/a"
    if metrics.extents:
        extent_text = ", ".join(str(item) for item in metrics.extents if str(item).strip())
        if not extent_text:
            extent_text = "n/a"

    lines = [
        "## Universal diagnostics",
        "",
        (
            "Health — min overlap: "
            f"{_format_value(metrics.min_overlap)}, "
            f"mean overlap: {_format_value(metrics.mean_overlap)}, "
            f"tiles ≥ s_min: {_format_value(metrics.pass_rate, precision='percent')}, "
            f"FS step mean: {_format_value(metrics.fs_mean)}, "
            f"p95: {_format_value(metrics.fs_p95)}, "
            f"Ω CI mean width: {_format_value(metrics.omega_ci_mean)}"
        ),
        (
            "Geometry — |Ω| mean/median: "
            f"{_format_value(metrics.omega_abs_mean)} / {_format_value(metrics.omega_abs_median)}, "
            "tr(g) mean/min/max: "
            f"{_format_value(metrics.trace_mean)} / {_format_value(metrics.trace_min)} / "
            f"{_format_value(metrics.trace_max)}"
        ),
        (
            "Loop — Φ: "
            f"{_format_value(metrics.phi_flux)}, area: {_format_value(metrics.geom_area)}, "
            f"extents: {extent_text}, steps: {_format_value(metrics.steps, precision='integer')}"
        ),
    ]

    readout_values = (
        metrics.R_cw,
        metrics.R_ccw,
        metrics.flip_error,
        metrics.observed_response_per_flux_mean,
    )
    if any(value is not None for value in readout_values):
        readout = (
            "Readout — R_CW: "
            f"{_format_value(metrics.R_cw)}, R_CCW: {_format_value(metrics.R_ccw)}, "
            f"flip error: {_format_value(metrics.flip_error)}"
        )
        if metrics.observed_response_per_flux_mean is not None:
            readout += (
                ", observed R/Φ (flux-conditioned): "
                f"{_format_value(metrics.observed_response_per_flux_mean)} "
                f"(CI {_format_ci(metrics.observed_response_per_flux_ci)})"
            )
        lines.append(readout)

    lines.extend(
        [
            (
                "Markers — spectral gap(P): "
                f"{_format_value(metrics.spectral_gap)}, |∇r|: {_format_value(metrics.grad_r)}"
            ),
            "",
        ]
    )
    return lines


__all__ = [
    "fs_histogram",
    "render_health_banner",
    "ReportHeaderMetrics",
    "render_report_header",
]
