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

_LOCAL_ROOT = Path(__file__).resolve().parent
__path__ = list(getattr(_impl, "__path__", [str(_IMPLEMENTATION_ROOT)]))
if str(_LOCAL_ROOT) not in __path__:
    __path__.insert(0, str(_LOCAL_ROOT))
__all__ = getattr(_impl, "__all__", [])


def __getattr__(name: str) -> Any:
    return getattr(_impl, name)


if TYPE_CHECKING:  # pragma: no cover - assist static analysis
    from baselines import common, io, ising, kuramoto, percolation, sis  # noqa: F401


_LOCAL_COMMON = _LOCAL_ROOT / "common.py"
if _LOCAL_COMMON.exists():
    _common_spec = importlib.util.spec_from_file_location(
        "baselines.common", _LOCAL_COMMON
    )
    if (
        _common_spec is not None and _common_spec.loader is not None
    ):  # pragma: no cover - defensive guard
        _common_module = importlib.util.module_from_spec(_common_spec)
        sys.modules[_common_spec.name] = _common_module
        _common_spec.loader.exec_module(_common_module)
        setattr(sys.modules[__name__], "common", _common_module)
