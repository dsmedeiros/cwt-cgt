"""Utilities for persisting run records to disk."""

from __future__ import annotations

import json
import uuid
from dataclasses import fields, is_dataclass
from pathlib import Path
from typing import Any, Mapping

import numpy as np

from ..orchestrator.scheduler import RunRecord


def _normalise_scalar(value: Any) -> Any:
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, Path):
        return str(value)
    return value


class _ArrayWriter:
    def __init__(self, run_dir: Path) -> None:
        self._run_dir = run_dir
        self._counters: dict[str, int] = {}

    def save(self, array: np.ndarray, prefix: str) -> str:
        key = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in prefix) or "array"
        index = self._counters.get(key, 0)
        suffix = f"_{index}" if index else ""
        filename = f"{key}{suffix}.npy"
        self._counters[key] = index + 1
        np.save(self._run_dir / filename, array, allow_pickle=False)
        return filename


def _serialise(value: Any, writer: _ArrayWriter, prefix: str) -> Any:
    if isinstance(value, np.ndarray):
        return writer.save(value, prefix)
    if isinstance(value, Mapping):
        return {str(k): _serialise(v, writer, f"{prefix}_{k}") for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_serialise(item, writer, f"{prefix}_{index}") for index, item in enumerate(value)]
    if is_dataclass(value):
        return {
            field.name: _serialise(getattr(value, field.name), writer, f"{prefix}_{field.name}")
            for field in fields(value)
        }
    if hasattr(value, "model_dump"):
        return _serialise(value.model_dump(), writer, prefix)
    return _normalise_scalar(value)


def _record_to_mapping(record: RunRecord | Mapping[str, Any]) -> Mapping[str, Any]:
    if is_dataclass(record):
        return {field.name: getattr(record, field.name) for field in fields(record)}
    if isinstance(record, Mapping):
        return record
    raise TypeError("record must be a dataclass or mapping")


def save_run(record: RunRecord | Mapping[str, Any], out_dir: str | Path) -> str:
    """Persist ``record`` to ``out_dir`` and return a UUID identifier."""

    base_dir = Path(out_dir)
    base_dir.mkdir(parents=True, exist_ok=True)

    run_id = uuid.uuid4().hex
    run_dir = base_dir / run_id
    run_dir.mkdir(parents=True, exist_ok=False)

    writer = _ArrayWriter(run_dir)
    record_mapping = _record_to_mapping(record)

    metadata: dict[str, Any] = {}
    for key, value in record_mapping.items():
        metadata[key] = _serialise(value, writer, key)
    metadata["run_id"] = run_id

    meta_path = run_dir / "meta.json"
    with meta_path.open("w", encoding="utf8") as handle:
        json.dump(metadata, handle, indent=2, sort_keys=True)

    return run_id


__all__ = ["save_run"]
