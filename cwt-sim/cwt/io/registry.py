"""In-memory registry utilities for simulation runs."""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import asdict, is_dataclass
import hashlib
import json
from typing import Any, Mapping, TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:  # pragma: no cover - import cycle guard
    from ..orchestrator.scheduler import RunConfig, RunRecord
else:  # pragma: no cover - typing fallback
    RunConfig = Any
    RunRecord = Any


def _to_serialisable(obj: Any) -> Any:
    if is_dataclass(obj):
        obj = asdict(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, (np.floating, float)):
        return float(obj)
    if isinstance(obj, (np.integer, int)):
        return int(obj)
    if isinstance(obj, (list, tuple)):
        return [_to_serialisable(item) for item in obj]
    if isinstance(obj, Mapping):
        return {str(k): _to_serialisable(v) for k, v in sorted(obj.items(), key=lambda item: str(item[0]))}
    return obj


def make_run_id(config: Mapping[str, Any] | RunConfig, seed: int) -> str:
    """Return a deterministic digest derived from ``config`` and ``seed``."""

    payload = {"config": _to_serialisable(config), "seed": int(seed)}
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf8")
    digest = hashlib.sha256(encoded).hexdigest()
    return digest[:16]


class RunRegistry:
    """Simple append-only registry storing :class:`RunRecord` instances."""

    def __init__(self) -> None:
        self._records: "OrderedDict[str, RunRecord]" = OrderedDict()
        self._meta: dict[str, dict[str, Any]] = {}

    def add(self, run_id: str, record: RunRecord, *, meta: Mapping[str, Any] | None = None, overwrite: bool = False) -> None:
        if not overwrite and run_id in self._records:
            raise KeyError(f"Run id '{run_id}' already present; pass overwrite=True to replace it.")
        self._records[run_id] = record
        self._meta[run_id] = dict(meta or {})

    def get(self, run_id: str) -> RunRecord:
        try:
            return self._records[run_id]
        except KeyError as exc:  # pragma: no cover - delegated to caller
            raise KeyError(f"Unknown run id '{run_id}'.") from exc

    def meta(self, run_id: str) -> dict[str, Any]:
        return dict(self._meta.get(run_id, {}))

    def latest(self) -> tuple[str, RunRecord]:
        if not self._records:
            raise KeyError("Registry is empty.")
        run_id = next(reversed(self._records))
        return run_id, self._records[run_id]

    def ids(self) -> list[str]:
        return list(self._records.keys())

    def __contains__(self, run_id: object) -> bool:
        return run_id in self._records

    def __len__(self) -> int:
        return len(self._records)

    def summary(self) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for run_id, record in self._records.items():
            meta = self._meta.get(run_id, {})
            record_meta = getattr(record, "meta", {})
            items.append(
                {
                    "run_id": run_id,
                    "steps": int(record_meta.get("steps", len(getattr(record, "lambda_path", [])))),
                    "seed": record_meta.get("seed"),
                    "meta": {**record_meta, **meta},
                }
            )
        return items


DEFAULT_REGISTRY = RunRegistry()


def register_run(
    record: RunRecord,
    config: Mapping[str, Any] | RunConfig,
    *,
    seed: int,
    registry: RunRegistry | None = None,
    meta: Mapping[str, Any] | None = None,
    overwrite: bool = False,
) -> str:
    """Register ``record`` and return the generated run identifier."""

    registry_obj = registry or DEFAULT_REGISTRY
    run_id = make_run_id(config, seed)
    registry_obj.add(run_id, record, meta=meta, overwrite=overwrite)
    return run_id


__all__ = ["RunRegistry", "DEFAULT_REGISTRY", "make_run_id", "register_run"]
