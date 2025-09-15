"""Registry helpers for simulation configurations and runs."""

from __future__ import annotations


def placeholder_registry() -> dict[str, str]:
    """Return a trivial registry mapping."""
    return {"default": "placeholder"}
