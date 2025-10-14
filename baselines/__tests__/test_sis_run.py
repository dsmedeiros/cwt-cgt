from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from baselines.sis import run as sis_run  # noqa: E402


def _latest_metrics(root: Path) -> pd.DataFrame:
    """Return the metrics dataframe from the most recent SIS run under ``root``."""

    runs_root = root / "baselines" / "sis"
    runs = sorted(runs_root.glob("*")) if runs_root.exists() else []
    if not runs:
        raise AssertionError("no SIS runs were recorded")
    metrics_path = runs[-1] / "metrics.csv"
    data = pd.read_csv(metrics_path)
    if "index" in data.columns:
        data = data.sort_values("index").reset_index(drop=True)
    return data


def test_simulate_sis_deterministic_tile(tmp_path: Path) -> None:
    """Running the SIS CLI twice with the same seed yields identical metrics."""

    argv = [
        "--output-dir",
        str(tmp_path / "first"),
        "--grid-size",
        "2",
        "2",
        "--population",
        "32",
        "--steps",
        "4",
        "--warmup",
        "1",
        "--seed",
        "7",
    ]

    sis_run.main(argv)

    second_args = argv.copy()
    second_args[1] = str(tmp_path / "second")
    sis_run.main(second_args)

    first_metrics = _latest_metrics(tmp_path / "first")
    second_metrics = _latest_metrics(tmp_path / "second")

    pd.testing.assert_frame_equal(first_metrics, second_metrics, check_exact=True)
