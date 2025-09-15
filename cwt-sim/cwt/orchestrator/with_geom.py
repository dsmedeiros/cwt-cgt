"""Context helpers for running loops with geometry instrumentation."""

from __future__ import annotations
from contextlib import contextmanager
from typing import Iterator


@contextmanager
def with_geometry() -> Iterator[None]:
    """Yield control with a placeholder geometry context."""
    yield
