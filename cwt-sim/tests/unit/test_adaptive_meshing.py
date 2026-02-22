"""Tests for adaptive meshing helpers."""

from __future__ import annotations

import math

import pytest

from cwt.geometry.adapt_mesh import curvature_anytime, micro_plaquettes


def test_micro_plaquettes_halve_step_sizes():
    schedule = micro_plaquettes(lambda *_: None, 1.0, 2.0, 3)
    assert schedule == [
        (1.0, 2.0),
        (1.0, 2.0),
        (1.0, 2.0),
        (1.0, 2.0),
        (0.5, 1.0),
        (0.5, 1.0),
        (0.5, 1.0),
        (0.5, 1.0),
        (0.25, 0.5),
        (0.25, 0.5),
        (0.25, 0.5),
        (0.25, 0.5),
    ]


def test_curvature_anytime_collapses_ci(monkeypatch):
    calls = []

    def sampler(delta_i, delta_j):
        calls.append((delta_i, delta_j))
        return (None, None, None, None)

    responses = iter((0.123, 0.95) for _ in range(8))

    def stub_curvature(*args):
        omega, overlap = next(responses)
        return omega, {"min_overlap": overlap}

    monkeypatch.setattr("cwt.geometry.adapt_mesh.curvature_tile", stub_curvature)

    result = curvature_anytime(sampler, 1.0, 1.0, ci_tol=1e-6)

    assert math.isclose(result.omega_mean, 0.123, rel_tol=1e-6)
    assert result.omega_ci == pytest.approx((0.123, 0.123))
    assert result.depth_used == 1
    assert result.samples_used == 4
    assert len(calls) == 4


def test_curvature_anytime_refines_on_low_overlap(monkeypatch):
    samples = [
        (0.05, 0.95),
        (0.10, 0.95),
        (0.15, 0.95),
        (0.20, 0.40),
        (0.09, 0.92),
        (0.11, 0.93),
        (0.10, 0.91),
        (0.10, 0.92),
    ]
    responses = iter(samples)

    def stub_curvature(*args):
        try:
            omega, overlap = next(responses)
        except StopIteration as exc:  # pragma: no cover - defensive
            raise AssertionError("Too many curvature evaluations") from exc
        return omega, {"min_overlap": overlap}

    monkeypatch.setattr("cwt.geometry.adapt_mesh.curvature_tile", stub_curvature)

    calls = []

    def sampler(delta_i, delta_j):
        calls.append((delta_i, delta_j))
        return (None, None, None, None)

    result = curvature_anytime(sampler, 1.0, 1.0, s_min=0.6, ci_tol=0.05, max_levels=2)

    assert result.depth_used == 2
    assert result.samples_used == 7
    assert result.min_overlap == pytest.approx(0.40)
    lower, upper = result.omega_ci
    assert upper - lower <= 0.05
    assert result.omega_mean == pytest.approx(0.10)
    assert len(calls) == 8
    assert calls == [
        (1.0, 1.0),
        (1.0, 1.0),
        (1.0, 1.0),
        (1.0, 1.0),
        (0.5, 0.5),
        (0.5, 0.5),
        (0.5, 0.5),
        (0.5, 0.5),
    ]


def test_curvature_anytime_uses_direct_level_steps(monkeypatch):
    monkeypatch.setattr(
        "cwt.geometry.adapt_mesh.micro_plaquettes",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("should not be called")),
    )
    responses = iter((0.2, 0.95) for _ in range(4))

    def stub_curvature(*args):
        omega, overlap = next(responses)
        return omega, {"min_overlap": overlap}

    monkeypatch.setattr("cwt.geometry.adapt_mesh.curvature_tile", stub_curvature)

    result = curvature_anytime(lambda *_: (None, None, None, None), 1.0, 1.0, max_levels=1)

    assert result.samples_used == 4


def test_curvature_anytime_fallback_uses_neutral_tiebreak(monkeypatch):
    samples = [
        (1.0, 0.40),
        (-5.0, 0.40),
        (2.0, 0.30),
        (-4.0, 0.30),
    ]
    responses = iter(samples)

    def stub_curvature(*args):
        try:
            omega, overlap = next(responses)
        except StopIteration as exc:  # pragma: no cover - defensive
            raise AssertionError("Too many curvature evaluations") from exc
        return omega, {"min_overlap": overlap}

    monkeypatch.setattr("cwt.geometry.adapt_mesh.curvature_tile", stub_curvature)

    call_count = 0

    def sampler(delta_i, delta_j):
        nonlocal call_count
        call_count += 1
        return (None, None, None, None)

    result = curvature_anytime(sampler, 1.0, 1.0, s_min=0.6, ci_tol=0.05, max_levels=1)

    assert call_count == 4
    assert result.samples_used == 2
    assert result.fallback_used is True
    assert result.omega_mean == pytest.approx(-4.5)
    lower, upper = result.omega_ci
    assert lower < result.omega_mean < upper
    assert result.min_overlap == pytest.approx(0.30)


def test_curvature_anytime_marks_non_fallback_path(monkeypatch):
    responses = iter((0.2, 0.95) for _ in range(4))

    def stub_curvature(*args):
        omega, overlap = next(responses)
        return omega, {"min_overlap": overlap}

    monkeypatch.setattr("cwt.geometry.adapt_mesh.curvature_tile", stub_curvature)

    result = curvature_anytime(lambda *_: (None, None, None, None), 1.0, 1.0, max_levels=1)

    assert result.samples_used == 4
    assert result.fallback_used is False
