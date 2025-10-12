"""Shim package to expose the ``cwt-sim`` baseline implementations at repository root."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

_IMPLEMENTATION_ROOT = Path(__file__).resolve().parent.parent / "cwt-sim" / "baselines"
if not _IMPLEMENTATION_ROOT.exists():  # pragma: no cover - safety guard
    raise ImportError("The cwt-sim baselines package is missing from the repository.")

spec = importlib.util.spec_from_file_location(
    "_cwt_sim_baselines",
    _IMPLEMENTATION_ROOT / "__init__.py",
    submodule_search_locations=[str(_IMPLEMENTATION_ROOT)],
)
if spec is None or spec.loader is None:  # pragma: no cover - defensive programming
    raise ImportError("Unable to load the cwt-sim baselines implementation.")

_impl = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = _impl
spec.loader.exec_module(_impl)

__path__ = list(getattr(_impl, "__path__", [str(_IMPLEMENTATION_ROOT)]))
__all__ = getattr(_impl, "__all__", [])

def __getattr__(name: str) -> Any:
    return getattr(_impl, name)


if TYPE_CHECKING:  # pragma: no cover - assist static analysis
    from baselines import common, io, ising, kuramoto, percolation, sis  # noqa: F401
