"""Tests for baseline shared utilities."""

from __future__ import annotations

from pathlib import Path

import pytest

import baselines.common as baselines_common


@pytest.fixture(autouse=True)
def reset_axis_map_cache() -> None:
    """Ensure axis map caching does not leak across tests."""

    baselines_common.clear_axis_map_cache()


def test_map_axes_returns_canonical_axes() -> None:
    mapped = baselines_common.map_axes(
        {
            "temperature": 1.5,
            "steps": 10,
        },
        "ising",
    )

    assert mapped == {"tau": 1.5}


def test_map_axes_raises_for_missing_axis() -> None:
    with pytest.raises(KeyError):
        baselines_common.map_axes({"steps": 10}, "percolation")


def test_map_axes_caches_per_axis_map_path(tmp_path: Path) -> None:
    axis_map_path_a = tmp_path / "axis_map_a.yml"
    axis_map_path_b = tmp_path / "axis_map_b.yml"

    axis_map_path_a.write_text(
        """
models:
  ising:
    axes:
      tau: temperature
""".strip(),
        encoding="utf-8",
    )
    axis_map_path_b.write_text(
        """
models:
  ising:
    axes:
      tau: steps
""".strip(),
        encoding="utf-8",
    )

    model_axes = {"temperature": 1.5, "steps": 10}

    mapped_a = baselines_common.map_axes(model_axes, "ising", axis_map_path_a)
    mapped_b = baselines_common.map_axes(model_axes, "ising", axis_map_path_b)

    assert mapped_a == {"tau": 1.5}
    assert mapped_b == {"tau": 10.0}


def test_map_axes_uses_updated_axis_map_after_cache_clear(tmp_path: Path) -> None:
    axis_map_path = tmp_path / "axis_map.yml"
    axis_map_path.write_text(
        """
models:
  ising:
    axes:
      tau: temperature
""".strip(),
        encoding="utf-8",
    )

    first = baselines_common.map_axes(
        {
            "temperature": 1.5,
            "steps": 10,
        },
        "ising",
        axis_map_path,
    )
    assert first == {"tau": 1.5}

    axis_map_path.write_text(
        """
models:
  ising:
    axes:
      tau: steps
""".strip(),
        encoding="utf-8",
    )

    cached = baselines_common.map_axes(
        {
            "temperature": 1.5,
            "steps": 10,
        },
        "ising",
        axis_map_path,
    )
    assert cached == {"tau": 1.5}

    baselines_common.clear_axis_map_cache()

    updated = baselines_common.map_axes(
        {
            "temperature": 1.5,
            "steps": 10,
        },
        "ising",
        axis_map_path,
    )
    assert updated == {"tau": 10.0}
