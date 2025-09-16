"""Test configuration helpers for the cwt-sim package."""

from __future__ import annotations

import pathlib
import sys

import pytest

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
TESTS_ROOT = pathlib.Path(__file__).resolve().parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def pytest_configure(config: pytest.Config) -> None:
    """Register commonly used markers for the test suite."""

    config.addinivalue_line(
        "markers",
        "unit: fast, deterministic unit tests for core functionality.",
    )
    config.addinivalue_line(
        "markers",
        "regression: deterministic regression checks on small synthetic graphs.",
    )


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Automatically tag tests based on their directory location."""

    del config

    for item in items:
        path = pathlib.Path(item.fspath).resolve()
        try:
            relative = path.relative_to(TESTS_ROOT)
        except ValueError:
            continue

        if not relative.parts:
            continue

        top_level = relative.parts[0]
        if top_level == "unit":
            item.add_marker(pytest.mark.unit)
        elif top_level == "regression":
            item.add_marker(pytest.mark.regression)
