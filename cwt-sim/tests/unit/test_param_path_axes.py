from __future__ import annotations

import math
from typing import Tuple

import pytest

from cwt.orchestrator.param_path import ParameterPath


def _total_area(path: ParameterPath) -> float:
    return sum(path.step(s)[2] for s in range(path.steps))


def _loop_closure(path: ParameterPath, axis_i: str, axis_j: str) -> None:
    lam0, _, _ = path.step(0)
    accumulator = {axis_i: lam0.get(axis_i, 0.0), axis_j: lam0.get(axis_j, 0.0)}
    for step_index in range(path.steps):
        _, delta, _ = path.step(step_index)
        accumulator[axis_i] += float(delta.get(axis_i, 0.0))
        accumulator[axis_j] += float(delta.get(axis_j, 0.0))
    assert math.isclose(accumulator[axis_i], lam0.get(axis_i, 0.0), rel_tol=1e-9, abs_tol=1e-9)
    assert math.isclose(accumulator[axis_j], lam0.get(axis_j, 0.0), rel_tol=1e-9, abs_tol=1e-9)


@pytest.mark.parametrize(
    ("axes", "center", "extents"),
    (
        (("tau", "zeta"), {"tau": 0.8, "zeta": 0.0}, {"tau": 0.02, "zeta": 0.03}),
        (
            ("tau", "zeta_phase"),
            {"tau": 0.8, "zeta_phase": 0.0},
            {"tau": 0.02, "zeta_phase": 0.02},
        ),
    ),
)
def test_rectangle_tau_axes_area_matches_orientation(
    axes: Tuple[str, str], center: dict[str, float], extents: dict[str, float]
) -> None:
    path_ccw = ParameterPath(
        kind="rectangle",
        center=center,
        extents=extents,
        steps=40,
        orientation="CCW",
        axes=axes,
    )
    axis_i, axis_j = axes
    _loop_closure(path_ccw, axis_i, axis_j)
    expected_area = 4.0 * extents[axis_i] * extents[axis_j]
    assert math.isclose(_total_area(path_ccw), expected_area, rel_tol=1e-9, abs_tol=1e-9)

    path_cw = ParameterPath(
        kind="rectangle",
        center=center,
        extents=extents,
        steps=40,
        orientation="CW",
        axes=axes,
    )
    _loop_closure(path_cw, axis_i, axis_j)
    assert math.isclose(_total_area(path_cw), -expected_area, rel_tol=1e-9, abs_tol=1e-9)


def test_torus_loop_area_elements_flip_sign_with_orientation() -> None:
    kwargs = {
        "kind": "torus_loop",
        "center": {"tau": 0.85, "zeta": 0.35},
        "extents": {"tau": 0.07, "zeta": 0.06},
        "steps": 120,
        "axes": ("tau", "zeta"),
        "periodic": {"tau": True, "zeta": False},
    }
    path_ccw = ParameterPath(**kwargs, orientation="CCW")
    path_cw = ParameterPath(**kwargs, orientation="CW")

    _loop_closure(path_ccw, "tau", "zeta")
    _loop_closure(path_cw, "tau", "zeta")

    areas_ccw = [path_ccw.step(s)[2] for s in range(path_ccw.steps)]
    areas_cw = [path_cw.step(s)[2] for s in range(path_cw.steps)]

    for step_index, cw_area in enumerate(areas_cw):
        mirrored_index = (path_ccw.steps - step_index - 1) % path_ccw.steps
        assert math.isclose(cw_area, -areas_ccw[mirrored_index], rel_tol=1e-9, abs_tol=1e-9)

    assert math.isclose(_total_area(path_cw), -_total_area(path_ccw), rel_tol=1e-9, abs_tol=1e-9)
