import json
from typing import Any

import numpy as np

from experiments.wilson_loop_3d import run


class _StubSubstrate:
    def __init__(self, size: int) -> None:
        self.N = size


def test_summary_sanitizes_non_finite_statistics(monkeypatch, tmp_path):
    artifacts_dir = tmp_path / "artifacts"

    monkeypatch.setattr(run, "_build_substrate", lambda graph, seed: _StubSubstrate(1))
    monkeypatch.setattr(run, "_psi_at", lambda *args, **kwargs: np.array([1.0], dtype=float))

    def fake_wilson_phase(psis: Any):
        return float("nan"), [complex(float("nan"), 0.0)]

    monkeypatch.setattr(run, "_wilson_phase", fake_wilson_phase)
    monkeypatch.setattr(
        run,
        "_fs_statistics",
        lambda psis: ([float("nan")], float("nan"), float("nan")),
    )

    run.main(
        [
            "--output-dir",
            str(artifacts_dir),
            "--steps",
            "2",
            "--handle-steps",
            "2",
            "--settle",
            "1",
        ]
    )

    summary_path = artifacts_dir / "summary.json"
    assert summary_path.exists()

    data = json.loads(summary_path.read_text(encoding="utf-8"))

    assert data["fs_mean"] is None
    assert data["fs_p95"] is None
    assert data["phi_forward"] is None
    assert data["phi_reverse"] is None
    assert data["phi_sum"] is None
    assert data["overlap_min"] is None
    assert data["overlap_max"] is None
    assert data["overlap_product_abs"] is None
    assert data["fs_steps"] == [None]
