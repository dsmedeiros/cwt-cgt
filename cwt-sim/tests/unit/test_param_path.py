from __future__ import annotations

import math

from cwt.orchestrator.param_path import ParameterPath


def _total_area(path: ParameterPath) -> float:
    return sum(path.step(s)[2] for s in range(path.steps))


def test_rectangle_area_matches_geometry_and_orientation() -> None:
    extents = {"x": 0.3, "y": 0.2}
    center = {"x": 0.1, "y": -0.4}

    path_ccw = ParameterPath(
        kind="rectangle",
        center=center,
        extents=extents,
        steps=12,
        orientation="CCW",
        axes=("x", "y"),
    )
    width = 2.0 * abs(extents["x"])
    height = 2.0 * abs(extents["y"])
    expected_area = width * height

    total_ccw = _total_area(path_ccw)
    assert math.isclose(total_ccw, expected_area, rel_tol=1e-9, abs_tol=1e-9)

    path_cw = ParameterPath(
        kind="rectangle",
        center=center,
        extents=extents,
        steps=12,
        orientation="CW",
        axes=("x", "y"),
    )
    total_cw = _total_area(path_cw)
    assert math.isclose(total_cw, -expected_area, rel_tol=1e-9, abs_tol=1e-9)


def test_lissajous_area_elements_flip_sign_with_orientation() -> None:
    path_ccw = ParameterPath(
        kind="lissajous",
        center={"x": 0.1, "y": -0.2},
        extents={"x": 0.4, "y": 0.3},
        steps=96,
        orientation="CCW",
        axes=("x", "y"),
    )
    path_cw = ParameterPath(
        kind="lissajous",
        center={"x": 0.1, "y": -0.2},
        extents={"x": 0.4, "y": 0.3},
        steps=96,
        orientation="CW",
        axes=("x", "y"),
    )

    areas_ccw = [path_ccw.step(s)[2] for s in range(path_ccw.steps)]
    areas_cw = [path_cw.step(s)[2] for s in range(path_cw.steps)]

    for step_index, cw_area in enumerate(areas_cw):
        mirrored_index = (path_ccw.steps - step_index - 1) % path_ccw.steps
        assert math.isclose(cw_area, -areas_ccw[mirrored_index], rel_tol=1e-9, abs_tol=1e-9)
