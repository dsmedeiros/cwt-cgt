"""Tests for baseline shared utilities."""

from __future__ import annotations

import importlib
from typing import Mapping

import pytest

import baselines.common as baselines_common


@pytest.fixture(autouse=True)
def reset_axis_map_cache() -> Mapping[str, object]:
    """Ensure axis map caching does not leak across tests."""

    importlib.reload(baselines_common)
    return baselines_common._load_axis_map_cache()


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
