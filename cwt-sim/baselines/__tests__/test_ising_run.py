import math
import sys
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from baselines.ising import run as ising_run  # noqa: E402


def test_simulate_ising_statistics() -> None:
    """A tiny two-spin system produces bounded observables."""

    adjacency = np.array([[0.0, 1.0], [1.0, 0.0]], dtype=float)
    result = ising_run.simulate_ising(
        adjacency,
        temperature=2.0,
        field=0.1,
        coupling=1.0,
        warmup_sweeps=2,
        sample_sweeps=5,
        seed=42,
    )
    assert -1.0 <= result.magnetization_mean <= 1.0
    assert result.samples == 5
    assert result.energy_std >= 0.0 or math.isnan(result.energy_std)


def test_simulate_ising_deterministic() -> None:
    """Ising simulations with the same seed reproduce identical observables."""

    adjacency = np.array([[0.0, 1.0], [1.0, 0.0]], dtype=float)
    first = ising_run.simulate_ising(
        adjacency,
        temperature=2.5,
        field=0.0,
        coupling=1.0,
        warmup_sweeps=4,
        sample_sweeps=6,
        seed=123,
    )
    second = ising_run.simulate_ising(
        adjacency,
        temperature=2.5,
        field=0.0,
        coupling=1.0,
        warmup_sweeps=4,
        sample_sweeps=6,
        seed=123,
    )

    assert first == second


def test_cli_produces_artifacts(tmp_path: Path) -> None:
    """Running the CLI with a small grid writes metrics and artifacts."""

    argv = [
        "--output-dir",
        str(tmp_path),
        "--axes",
        "T",
        "h",
        "--grid-size",
        "2",
        "2",
        "--range",
        "T",
        "1.5",
        "2.0",
        "--range",
        "h",
        "-0.2",
        "0.2",
        "--lattice-size",
        "2",
        "2",
        "--warmup-sweeps",
        "1",
        "--steps",
        "2",
        "--top-k",
        "2",
        "--seed",
        "123",
    ]
    ising_run.main(argv)

    runs_root = tmp_path / "baselines" / "ising"
    runs = sorted(runs_root.glob("*")) if runs_root.exists() else []
    assert runs, "expected an experiment directory to be created"
    run_dir = runs[-1]

    metrics = run_dir / "metrics.csv"
    assert metrics.exists()
    content = metrics.read_text(encoding="utf-8")
    assert "omega_abs" in content
    assert "M_mean" in content

    heatmap = run_dir / "omega_abs_heatmap.png"
    assert heatmap.exists()

    top_tiles = run_dir / "top_omega_tiles.json"
    payload = top_tiles.read_text(encoding="utf-8")
    assert "top_tiles" in payload
