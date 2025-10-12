"""Susceptible-Infected-Susceptible model baseline entry point."""
from __future__ import annotations

__all__ = ["get_parser", "main"]


def __getattr__(name: str):
    if name in __all__:
        from . import run

        value = getattr(run, name)
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
