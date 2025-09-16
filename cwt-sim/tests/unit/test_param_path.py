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
    )
    total_cw = _total_area(path_cw)
    assert math.isclose(total_cw, -expected_area, rel_tol=1e-9, abs_tol=1e-9)
