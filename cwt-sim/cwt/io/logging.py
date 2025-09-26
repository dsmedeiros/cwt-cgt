"""Logging helpers for simulation runs."""

from __future__ import annotations

import logging
from typing import Any, Mapping

_LOGGER_NAME = "cwt.sim"
_LOGGER = logging.getLogger(_LOGGER_NAME)


def _ensure_logger_configured() -> None:
    """Attach a default stream handler if the caller did not configure one."""

    if _LOGGER.handlers:
        return

    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)
    _LOGGER.addHandler(handler)
    if _LOGGER.level == logging.NOTSET:
        _LOGGER.setLevel(logging.INFO)


def placeholder_logger(
    message: str,
    *,
    level: int = logging.INFO,
    extra: Mapping[str, Any] | None = None,
) -> None:
    """Log ``message`` using :mod:`logging` with optional structured metadata."""

    _ensure_logger_configured()

    if not isinstance(level, int):
        raise TypeError("level must be an integer compatible with logging levels.")

    if extra:
        suffix = " ".join(f"{key}={value}" for key, value in sorted(extra.items()))
        if suffix:
            message = f"{message} | {suffix}"

    _LOGGER.log(level, message)
