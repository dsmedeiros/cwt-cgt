"""Helper utilities for generating placeholder run records."""

from __future__ import annotations

from typing import Any

import numpy as np

from .config import AppConfig
from ..orchestrator.scheduler import RunRecord


def fabricate_record(
    config: AppConfig,
    *,
    label: str,
    seed: int,
    step_index: int = 0,
) -> RunRecord:
    """Create a light-weight :class:`RunRecord` based on ``config``."""

    knobs = list(config.params.knobs or ["rho"])
    size = max(len(knobs), 1)

    pQ = np.full(size, 1.0 / size, dtype=float)
    theta = np.zeros(size, dtype=float)
    psi = np.zeros(size, dtype=complex)
    phase = np.zeros(size, dtype=float)

    lambda_state = {knob: float(step_index + index) for index, knob in enumerate(knobs)}
    delta_lambda = {knob: 0.0 for knob in knobs}

    meta: dict[str, Any] = {
        "config": config.model_dump(mode="json"),
        "label": label,
        "seed": int(seed),
        "step": int(step_index),
    }

    return RunRecord(
        meta=meta,
        lambda_path=[lambda_state],
        delta_lambda=[delta_lambda],
        delta_area=[0.0],
        pQ_traj=[pQ],
        theta_traj=[theta],
        psi_traj=[psi],
        overlaps_min=[0.0],
        g_tiles=[{}],
        omega_tiles=[{}],
        phase_kicks=[phase],
        curvature_biases=[phase],
        clip_counts=[0],
        readouts=[{}],
    )


__all__ = ["fabricate_record"]
