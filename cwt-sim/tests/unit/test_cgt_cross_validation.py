"""Cross-validation tests: compat shim vs canonical geometry implementations.

Verifies that cwt.cgt._geom_compat delegates correctly to cwt.geometry,
and that core density-matrix geometry (Bures, fidelity, trace) is consistent.
"""

from __future__ import annotations

import numpy as np
import pytest

import cwt.cgt._geom_compat as compat
import cwt.geometry.psi as psi_mod
from cwt.cgt.benchmarks import get_benchmark
from cwt.cgt.models import BranchState
from cwt.geometry.mixed_state import (
    bures_distance_sq,
    density_from_state,
    fidelity,
)


# ---------------------------------------------------------------------------
# a) overlap vs inner
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_overlap_matches_inner_abs_for_random_vectors() -> None:
    """compat.overlap(a, b) == |inner(a, b)| for 10 random complex vectors."""
    rng = np.random.default_rng(42)
    n = 6
    for _ in range(10):
        a = rng.standard_normal(n) + 1j * rng.standard_normal(n)
        b = rng.standard_normal(n) + 1j * rng.standard_normal(n)
        a /= np.linalg.norm(a)
        b /= np.linalg.norm(b)

        got = compat.overlap(a, b)
        expected = float(abs(psi_mod.inner(a, b)))
        assert abs(got - expected) < 1e-12, (
            f"overlap={got!r} != |inner|={expected!r}"
        )


@pytest.mark.unit
def test_overlap_self_equals_one() -> None:
    """overlap(psi, psi) == 1.0 for any unit-norm vector."""
    rng = np.random.default_rng(42)
    for _ in range(5):
        psi = rng.standard_normal(4) + 1j * rng.standard_normal(4)
        psi /= np.linalg.norm(psi)
        assert abs(compat.overlap(psi, psi) - 1.0) < 1e-12


# ---------------------------------------------------------------------------
# b) psi_from_parts consistency
# ---------------------------------------------------------------------------

@pytest.mark.unit
@pytest.mark.parametrize(
    'p, theta',
    [
        ([0.5, 0.5], [0.0, 0.0]),
        ([0.3, 0.4, 0.3], [0.1, -0.2, 0.3]),
        ([0.25, 0.25, 0.25, 0.25], [np.pi / 4, np.pi / 2, 3 * np.pi / 4, np.pi]),
        ([1.0, 0.0], [0.0, 0.0]),
        ([0.1, 0.7, 0.2], [-1.0, 0.5, 2.0]),
    ],
)
def test_psi_from_parts_unit_norm(p, theta) -> None:
    """psi_from_parts produces a unit-norm vector for valid (p, theta) pairs."""
    p_arr = np.array(p, dtype=float)
    theta_arr = np.array(theta, dtype=float)
    psi = compat.psi_from_parts(p_arr, theta_arr)
    norm = float(np.linalg.norm(psi))
    np.testing.assert_allclose(norm, 1.0, atol=1e-12, err_msg="psi_from_parts must return a unit-norm vector")


@pytest.mark.unit
@pytest.mark.parametrize(
    'p, theta',
    [
        ([0.5, 0.5], [0.0, 0.0]),
        ([0.3, 0.4, 0.3], [0.1, -0.2, 0.3]),
        ([0.25, 0.25, 0.25, 0.25], [np.pi / 4, np.pi / 2, 3 * np.pi / 4, np.pi]),
    ],
)
def test_psi_from_parts_self_overlap_is_one(p, theta) -> None:
    """overlap(psi, psi) == 1.0 for a unit-norm psi built by psi_from_parts."""
    p_arr = np.array(p, dtype=float)
    theta_arr = np.array(theta, dtype=float)
    psi = compat.psi_from_parts(p_arr, theta_arr)
    got = compat.overlap(psi, psi)
    np.testing.assert_allclose(got, 1.0, atol=1e-12)


# ---------------------------------------------------------------------------
# c) mixed_state density_from_state roundtrip
# ---------------------------------------------------------------------------

def _make_branch_state(p: list[float], theta: list[float]) -> BranchState:
    import numpy as np
    p_arr = np.array(p, dtype=float)
    p_arr /= p_arr.sum()
    theta_arr = np.array(theta, dtype=float)
    n = p_arr.size
    kernel = np.eye(n, dtype=float)
    return BranchState(p=p_arr, theta=theta_arr, kernel=kernel)


@pytest.mark.unit
@pytest.mark.parametrize(
    'p, theta',
    [
        ([0.5, 0.5], [0.0, 0.0]),
        ([0.3, 0.4, 0.3], [0.1, -0.2, 0.3]),
        ([0.25, 0.25, 0.25, 0.25], [np.pi / 6, np.pi / 3, np.pi / 2, 2 * np.pi / 3]),
    ],
)
def test_density_from_state_trace_one(p, theta) -> None:
    """density_from_state returns rho with trace == 1.0."""
    state = _make_branch_state(p, theta)
    rho = density_from_state(state)
    trace = float(np.real(np.trace(rho)))
    np.testing.assert_allclose(trace, 1.0, atol=1e-12, err_msg="rho must have unit trace")


@pytest.mark.unit
@pytest.mark.parametrize(
    'p, theta',
    [
        ([0.5, 0.5], [0.0, 0.0]),
        ([0.3, 0.4, 0.3], [0.1, -0.2, 0.3]),
        ([0.25, 0.25, 0.25, 0.25], [np.pi / 6, np.pi / 3, np.pi / 2, 2 * np.pi / 3]),
    ],
)
def test_density_from_state_hermitian(p, theta) -> None:
    """density_from_state returns a Hermitian matrix (rho == rho†)."""
    state = _make_branch_state(p, theta)
    rho = density_from_state(state)
    np.testing.assert_allclose(
        rho, rho.conj().T, atol=1e-12, err_msg="rho must be Hermitian"
    )


@pytest.mark.unit
@pytest.mark.parametrize(
    'p, theta',
    [
        ([0.5, 0.5], [0.0, 0.0]),
        ([0.3, 0.4, 0.3], [0.1, -0.2, 0.3]),
        ([0.25, 0.25, 0.25, 0.25], [np.pi / 6, np.pi / 3, np.pi / 2, 2 * np.pi / 3]),
    ],
)
def test_density_from_state_positive_semidefinite(p, theta) -> None:
    """density_from_state returns a PSD matrix (all eigenvalues >= 0)."""
    state = _make_branch_state(p, theta)
    rho = density_from_state(state)
    evals = np.linalg.eigvalsh(rho)
    assert np.all(evals >= -1e-12), (
        f"rho has negative eigenvalue(s): {evals[evals < 0]}"
    )


# ---------------------------------------------------------------------------
# d) Bures distance self-distance
# ---------------------------------------------------------------------------

@pytest.mark.unit
@pytest.mark.parametrize(
    'p, theta',
    [
        ([0.5, 0.5], [0.0, 0.0]),
        ([0.3, 0.4, 0.3], [0.1, -0.2, 0.3]),
        ([0.1, 0.8, 0.1], [1.0, 0.0, -1.0]),
    ],
)
def test_bures_distance_self_is_zero(p, theta) -> None:
    """bures_distance_sq(rho, rho) == 0.0 for any valid density matrix."""
    state = _make_branch_state(p, theta)
    rho = density_from_state(state)
    dist_sq = bures_distance_sq(rho, rho)
    assert abs(dist_sq) < 1e-10, f"Expected 0 self-distance, got {dist_sq!r}"


# ---------------------------------------------------------------------------
# e) Fidelity self-fidelity
# ---------------------------------------------------------------------------

@pytest.mark.unit
@pytest.mark.parametrize(
    'p, theta',
    [
        ([0.5, 0.5], [0.0, 0.0]),
        ([0.3, 0.4, 0.3], [0.1, -0.2, 0.3]),
        ([0.1, 0.8, 0.1], [1.0, 0.0, -1.0]),
    ],
)
def test_fidelity_self_is_one(p, theta) -> None:
    """fidelity(rho, rho) == 1.0 for any valid density matrix."""
    state = _make_branch_state(p, theta)
    rho = density_from_state(state)
    f = fidelity(rho, rho)
    np.testing.assert_allclose(f, 1.0, atol=1e-10, err_msg=f"Expected self-fidelity 1.0, got {f!r}")


@pytest.mark.unit
def test_fidelity_symmetry_random() -> None:
    """fidelity(rho, sigma) == fidelity(sigma, rho) for random states."""
    rng = np.random.default_rng(42)
    for _ in range(5):
        p1 = rng.dirichlet(np.ones(3))
        p2 = rng.dirichlet(np.ones(3))
        theta1 = rng.uniform(-np.pi, np.pi, size=3)
        theta2 = rng.uniform(-np.pi, np.pi, size=3)
        s1 = _make_branch_state(p1.tolist(), theta1.tolist())
        s2 = _make_branch_state(p2.tolist(), theta2.tolist())
        rho = density_from_state(s1)
        sigma = density_from_state(s2)
        f_rs = fidelity(rho, sigma)
        f_sr = fidelity(sigma, rho)
        np.testing.assert_allclose(
            f_rs, f_sr, atol=1e-10,
            err_msg="fidelity must be symmetric"
        )
