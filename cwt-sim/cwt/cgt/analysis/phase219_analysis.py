"""Phase 219 analysis: Ninth less-synthetic positive (benchmark II partial obs spike).

This module loads the pre-baked Phase 219 result artifact which adds the ninth
less-synthetic pilot benchmark II and evaluates the pooled-thirteen bridge positive
rule unchanged. Switch gamma = 0.30.
Held-out combined R2 = 0.9056; correlation = 0.9764; sign agreement = 0.9896.
"""

from __future__ import annotations

import json
from pathlib import Path

from cwt.cgt.analysis._utils import nan_to_none


def run_phase219_analysis(project_root: Path, output_root: Path | None = None) -> dict:
    """Load and return the Phase 219 ninth less-synthetic positive artifact.

    Parameters
    ----------
    project_root:
        Root of the cwt-sim project (contains cgt_benchmarks/).
    output_root:
        Unused for this loader stub; accepted for interface consistency.

    Returns
    -------
    dict
        Parsed JSON payload with nan/inf values replaced by None.

    Raises
    ------
    FileNotFoundError
        If the Phase 219 artifact JSON file is not found at the expected path.
    """
    project_root = Path(project_root)
    artifact_path = (
        project_root
        / 'cgt_benchmarks'
        / 'results'
        / 'benchmark_II_partial_obs_spike'
        / 'benchmark_ii_phase219_ninth_less_synthetic_positive.json'
    )
    if not artifact_path.exists():
        raise FileNotFoundError(
            f"Phase 219 artifact not found: {artifact_path}. "
            "Expected the ninth less-synthetic positive result at "
            "cgt_benchmarks/results/benchmark_II_partial_obs_spike/"
            "benchmark_ii_phase219_ninth_less_synthetic_positive.json"
        )
    payload = json.loads(artifact_path.read_text(encoding='utf-8'))
    return nan_to_none(payload)


if __name__ == '__main__':
    project_root = Path(__file__).resolve().parents[3]
    payload = run_phase219_analysis(project_root=project_root)
    print(json.dumps(nan_to_none(payload), indent=2))
