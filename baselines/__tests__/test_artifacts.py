"""Tests for baseline artifact helper utilities."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from baselines import artifacts  # noqa: E402


def test_ensure_outdir_creates_expected_layout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(artifacts.time, "strftime", lambda fmt, _: "20240101T010203")
    out_dir = artifacts.ensure_outdir("ising", tmp_path, "ring3", seed=7)
    expected = tmp_path / "baselines" / "ising" / "20240101T010203__graph=ring3__seed=7"
    assert out_dir == expected
    assert out_dir.is_dir()


def test_ensure_outdir_prefers_env_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env_root = tmp_path / "experiment"
    monkeypatch.setenv("CWT_OUTPUT_DIR", str(env_root))
    monkeypatch.setattr(artifacts.time, "strftime", lambda fmt, _: "20240202T030405")

    out_dir = artifacts.ensure_outdir("ising", None, "ring3", seed=11)

    expected = env_root / "baselines" / "ising" / "20240202T030405__graph=ring3__seed=11"
    assert out_dir == expected
    assert out_dir.is_dir()


def test_write_outputs_from_metrics_csv(tmp_path: Path) -> None:
    frame = pd.DataFrame(
        [
            {
                "time_index": 0,
                "time": 0,
                "nodes_index": 0,
                "nodes": 5,
                "omega_abs": 0.1,
                "omega_abs_proxy": 0.05,
            },
            {
                "time_index": 0,
                "time": 0,
                "nodes_index": 1,
                "nodes": 10,
                "omega_abs": 0.9,
                "omega_abs_proxy": 0.85,
            },
            {
                "time_index": 1,
                "time": 1,
                "nodes_index": 0,
                "nodes": 5,
                "omega_abs": float("nan"),
                "omega_abs_proxy": float("nan"),
            },
            {
                "time_index": 1,
                "time": 1,
                "nodes_index": 1,
                "nodes": 10,
                "omega_abs": 0.5,
                "omega_abs_proxy": 0.45,
            },
        ]
    )
    csv_path = tmp_path / "metrics.csv"
    frame.to_csv(csv_path, index=False)

    heatmap_path = artifacts.write_heatmap_png(csv_path, tmp_path)
    assert heatmap_path.name == "omega_abs_heatmap.png"
    assert heatmap_path.exists()
    assert heatmap_path.stat().st_size > 0

    tiles_path = artifacts.write_top_tiles(csv_path, tmp_path, top_k=2)
    assert tiles_path.name == "top_omega_tiles.json"
    payload = json.loads(tiles_path.read_text(encoding="utf-8"))

    assert payload["metric"] == "omega_abs"
    assert payload["grid_shape"] == [2, 2]
    assert payload.get("omega_abs_proxy_max") == pytest.approx(0.85)

    axis_lookup = {axis["name"]: axis for axis in payload["axes"]}
    assert axis_lookup["time"]["label"] == "steps"
    assert axis_lookup["time"]["values"] == [0, 1]
    assert axis_lookup["nodes"]["label"] == "vertex"
    assert axis_lookup["nodes"]["values"] == [5, 10]

    top_tiles = payload["top_tiles"]
    assert len(top_tiles) == 2
    assert top_tiles[0]["indices"] == [0, 1]
    assert top_tiles[0]["coordinates"]["nodes"] == 10
    assert top_tiles[0]["omega_abs"] == pytest.approx(0.9)
    assert top_tiles[0]["omega_abs_proxy"] == pytest.approx(0.85)
    assert top_tiles[1]["indices"] == [1, 1]
    assert top_tiles[1]["omega_abs"] == pytest.approx(0.5)
