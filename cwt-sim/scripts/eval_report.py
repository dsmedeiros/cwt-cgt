"""Command-line interface for generating evaluation reports."""

from __future__ import annotations

import json
import math
from dataclasses import fields
from pathlib import Path
from typing import Any

import numpy as np
import typer

from cwt.metrics.eval_curves import LoopSummary, summarize_loop
from cwt.orchestrator.scheduler import RunRecord

app = typer.Typer(help="Summarise saved run bundles into a compact report.")


def _materialise(value: Any, run_dir: Path) -> Any:
    """Recursively materialise arrays referenced by ``meta.json``."""

    if isinstance(value, str):
        if value.endswith(".npy"):
            array_path = run_dir / value
            if array_path.exists():
                return np.load(array_path, allow_pickle=False)
        return value
    if isinstance(value, list):
        return [_materialise(item, run_dir) for item in value]
    if isinstance(value, dict):
        return {key: _materialise(val, run_dir) for key, val in value.items()}
    return value


def _load_run_record(run_dir: Path) -> RunRecord:
    """Load a :class:`RunRecord` from ``run_dir``."""

    meta_path = run_dir / "meta.json"
    if not meta_path.exists():
        raise FileNotFoundError(f"Missing meta.json in {run_dir}.")

    with meta_path.open("r", encoding="utf8") as handle:
        data = json.load(handle)

    payload = _materialise(data, run_dir)
    record_kwargs: dict[str, Any] = {}
    for field in fields(RunRecord):
        if field.name in payload:
            record_kwargs[field.name] = payload[field.name]
    return RunRecord(**record_kwargs)


def _extract_label(meta: Any, default: str) -> str:
    if isinstance(meta, dict):
        for key in ("label",):
            label = meta.get(key)
            if isinstance(label, str) and label.strip():
                return label.strip()
        nested = meta.get("meta")
        if isinstance(nested, dict):
            label = nested.get("label")
            if isinstance(label, str) and label.strip():
                return label.strip()
        config = meta.get("config")
        if isinstance(config, dict):
            label = config.get("label")
            if isinstance(label, str) and label.strip():
                return label.strip()
            meta_cfg = config.get("meta")
            if isinstance(meta_cfg, dict):
                label = meta_cfg.get("label")
                if isinstance(label, str) and label.strip():
                    return label.strip()
    return default


def _finite_or_none(value: float | None) -> float | None:
    if value is None:
        return None
    if not math.isfinite(value):
        return None
    return float(value)


def _sign(value: float) -> int:
    if not math.isfinite(value) or value == 0.0:
        return 0
    return 1 if value > 0.0 else -1


def _compute_sign_checks(entries: list[dict[str, Any]]) -> tuple[bool | None, dict[str, bool | None]]:
    statuses: dict[str, bool | None] = {entry["run_id"]: None for entry in entries}
    if not entries:
        return None, statuses

    orientation_map: dict[str, dict[str, Any]] = {}
    for entry in entries:
        orientation = str(entry["summary"].orientation or "").upper()
        if orientation and orientation not in orientation_map:
            orientation_map[orientation] = entry

    pair_ok: bool | None = None
    if {"CW", "CCW"}.issubset(orientation_map):
        cw_entry = orientation_map["CW"]
        ccw_entry = orientation_map["CCW"]
        sign_cw = _sign(cw_entry["summary"].R_bias)
        sign_ccw = _sign(ccw_entry["summary"].R_bias)
        if sign_cw == 0 or sign_ccw == 0:
            pair_ok = False
        else:
            pair_ok = sign_cw == -sign_ccw
        statuses[cw_entry["run_id"]] = pair_ok
        statuses[ccw_entry["run_id"]] = None
    else:
        base_sign = _sign(entries[0]["summary"].R_bias)
        for entry in entries[1:]:
            sign_entry = _sign(entry["summary"].R_bias)
            statuses[entry["run_id"]] = base_sign != 0 and sign_entry == -base_sign
        if len(entries) > 1:
            pair_ok = statuses[entries[-1]["run_id"]]

    return pair_ok, statuses


def _format_float(value: float | None) -> str:
    finite = _finite_or_none(value)
    if finite is None:
        return "nan"
    return f"{finite:.3e}"


def _build_markdown(
    entries: list[dict[str, Any]], statuses: dict[str, bool | None], pair_ok: bool | None
) -> str:
    lines = [
        "| Run | Label | Orientation | Φ | R | κ₁ | Flip? |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for entry in entries:
        summary: LoopSummary = entry["summary"]
        flip_state = statuses.get(entry["run_id"])
        if flip_state is None:
            flip_text = "–"
        else:
            flip_text = "✓" if flip_state else "✗"
        kappa1 = summary.fs_stats.get("kappa1")
        lines.append(
            "| {run} | {label} | {orient} | {phi} | {bias} | {kappa} | {flip} |".format(
                run=entry["run_id"],
                label=entry["label"],
                orient=summary.orientation,
                phi=_format_float(summary.phi_flux),
                bias=_format_float(summary.R_bias),
                kappa=_format_float(kappa1),
                flip=flip_text,
            )
        )
    if pair_ok is not None:
        verdict = "PASS" if pair_ok else "FAIL"
        lines.append("")
        lines.append(f"Sign flip verification: **{verdict}**.")
    return "\n".join(lines)


def _build_json(
    entries: list[dict[str, Any]], pair_ok: bool | None, statuses: dict[str, bool | None]
) -> dict[str, Any]:
    runs_payload: list[dict[str, Any]] = []
    for entry in entries:
        summary: LoopSummary = entry["summary"]
        stats = {key: _finite_or_none(value) for key, value in summary.fs_stats.items()}
        runs_payload.append(
            {
                "run_id": entry["run_id"],
                "label": entry["label"],
                "orientation": summary.orientation,
                "phi_flux": _finite_or_none(summary.phi_flux),
                "R_bias": _finite_or_none(summary.R_bias),
                "overlap_min": _finite_or_none(summary.overlaps_min),
                "fs_stats": stats,
                "sign_flip": statuses.get(entry["run_id"]),
            }
        )
    return {"count": len(runs_payload), "runs": runs_payload, "sign_flip_ok": pair_ok}


@app.command()
def main(
    runs: Path = typer.Argument(..., help="Directory containing saved run bundles."),
    format: str = typer.Option("json", "--format", "-f", help="Output format: json or markdown."),
    report: Path | None = typer.Option(
        None, "--report", "-r", help="Optional path to write Markdown output."
    ),
) -> None:
    """Aggregate saved runs and emit a JSON or Markdown report."""

    runs_dir = Path(runs)
    if not runs_dir.exists():
        raise typer.BadParameter(f"Directory '{runs_dir}' does not exist.")
    if not runs_dir.is_dir():
        raise typer.BadParameter(f"Path '{runs_dir}' is not a directory.")

    run_dirs = sorted(p for p in runs_dir.iterdir() if p.is_dir())
    entries: list[dict[str, Any]] = []
    for run_dir in run_dirs:
        try:
            record = _load_run_record(run_dir)
        except FileNotFoundError:
            continue
        summary = summarize_loop(record)
        label = _extract_label(record.meta, run_dir.name)
        entries.append({"run_id": run_dir.name, "label": label, "summary": summary})

    format_lower = format.lower()
    if not entries:
        if format_lower.startswith("json"):
            typer.echo(json.dumps({"runs": [], "count": 0, "sign_flip_ok": None}))
            raise typer.Exit(code=0)
        raise typer.BadParameter("No runs containing meta.json were found.")

    pair_ok, statuses = _compute_sign_checks(entries)

    if format_lower in {"json", "js"}:
        payload = _build_json(entries, pair_ok, statuses)
        typer.echo(json.dumps(payload))
        return

    if format_lower in {"markdown", "md"}:
        markdown = _build_markdown(entries, statuses, pair_ok)
        if report is not None:
            report.parent.mkdir(parents=True, exist_ok=True)
            report.write_text(markdown, encoding="utf8")
        typer.echo(markdown)
        return

    raise typer.BadParameter(f"Unsupported format '{format}'.")


def entrypoint() -> None:
    app()


if __name__ == "__main__":
    entrypoint()
