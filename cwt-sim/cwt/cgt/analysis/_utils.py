"""Shared helper utilities for CGT phase analysis modules.

These functions are used across phase40_analysis, phase41_analysis, and any
future phase analysis modules.  Centralising them here prevents drift between
copies and makes it easy to apply fixes (e.g. the float('inf') guard in
nan_to_none) in one place.
"""

from __future__ import annotations

import math


def safe_pow(base: float, exponent: float, max_log: float = 700.0) -> float:
    """Compute base**exponent clamped to prevent float overflow or underflow.

    Returns 0.0 for non-positive bases.  The exponent is applied via
    ``exp(log(base) * exponent)`` with the log-result clamped symmetrically to
    ``[-max_log, max_log]`` (default 700, well inside the ``math.exp`` safe
    range) so the return value is always a finite float in both the overflow
    and underflow directions.
    """
    if base <= 0.0:
        return 0.0
    log_result = math.log(base) * exponent
    clamped = min(max(log_result, -max_log), max_log)
    return math.exp(clamped)


def safe_float(v: object) -> float:
    """Convert *v* to float, returning NaN for None.

    All other values are passed through ``float()``.  This matches the
    convention used in prediction-summary helpers where None signals a missing
    metric that should be treated as NaN for plotting purposes.
    """
    return float('nan') if v is None else float(v)  # type: ignore[arg-type]


def nan_to_none(obj: object) -> object:
    """Recursively replace non-finite floats with None for JSON-safe serialization.

    Handles both ``float('nan')`` and ``float('inf')`` / ``float('-inf')``,
    both of which are illegal in JSON per RFC 8259.  Also handles numpy scalar
    types (e.g. ``np.float64``) and any other object that exposes ``__float__``
    but is not an ``int`` or ``bool``.  Works recursively on dicts and lists;
    all other types are returned unchanged.
    """
    if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
        return None
    if not isinstance(obj, (int, bool)) and hasattr(obj, '__float__'):
        try:
            f = float(obj)
            if math.isnan(f) or math.isinf(f):
                return None
        except (TypeError, ValueError, OverflowError):
            pass
    if isinstance(obj, dict):
        return {k: nan_to_none(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [nan_to_none(v) for v in obj]
    return obj
