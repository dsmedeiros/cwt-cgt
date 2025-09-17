import math

import math

from cwt.orchestrator.param_path import ParameterPath


def _total_area(path: ParameterPath) -> float:
    return sum(path.step(s)[2] for s in range(path.steps))


def _loop_closure(path: ParameterPath, axis_i: str, axis_j: str) -> None:
    lam0, _, _ = path.step(0)
    accumulator = {axis_i: lam0.get(axis_i, 0.0), axis_j: lam0.get(axis_j, 0.0)}
    for s in range(path.steps):
        _, delta, _ = path.step(s)
        accumulator[axis_i] += float(delta.get(axis_i, 0.0))
        accumulator[axis_j] += float(delta.get(axis_j, 0.0))
    assert math.isclose(accumulator[axis_i], lam0.get(axis_i, 0.0), rel_tol=1e-9, abs_tol=1e-9)
    assert math.isclose(accumulator[axis_j], lam0.get(axis_j, 0.0), rel_tol=1e-9, abs_tol=1e-9)


def test_rectangle_tau_zeta_area_matches_orientation() -> None:
    center = {"tau": 0.8, "zeta": 0.0}
    extents = {"tau": 0.02, "zeta": 0.03}

    path_ccw = ParameterPath(
        kind="rectangle",
        center=center,
        extents=extents,
        steps=40,
        orientation="CCW",
        axes=("tau", "zeta"),
    )
    _loop_closure(path_ccw, "tau", "zeta")
    expected_area = 4.0 * extents["tau"] * extents["zeta"]
    assert math.isclose(_total_area(path_ccw), expected_area, rel_tol=1e-9, abs_tol=1e-9)

    path_cw = ParameterPath(
        kind="rectangle",
        center=center,
        extents=extents,
        steps=40,
        orientation="CW",
        axes=("tau", "zeta"),
    )
    _loop_closure(path_cw, "tau", "zeta")
    assert math.isclose(_total_area(path_cw), -expected_area, rel_tol=1e-9, abs_tol=1e-9)
