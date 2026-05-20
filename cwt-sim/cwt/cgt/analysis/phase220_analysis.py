"""Phase 220 analysis: Ninth less-synthetic adversarial (benchmark II partial obs spike).

This module loads the pre-baked Phase 220 result artifact which applies the bridge
tensor correction to the adversarial family on pilot II. Switch gamma = 0.30.
Raw combined R2 = 0.4387; corrected combined R2 = 0.8539;
corrected sign agreement = 0.9597.
"""

from __future__ import annotations

import json
from pathlib import Path

from cwt.cgt.analysis._utils import nan_to_none


def run_phase220_analysis(project_root: Path, output_root: Path | None = None) -> dict:
    """Load and return the Phase 220 ninth less-synthetic adversarial artifact.

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
        If the Phase 220 artifact JSON file is not found at the expected path.
    """
    project_root = Path(project_root)
    artifact_path = (
        project_root
        / 'cgt_benchmarks'
        / 'results'
        / 'benchmark_II_partial_obs_spike'
        / 'benchmark_ii_phase220_ninth_less_synthetic_adversarial.json'
    )
    if not artifact_path.exists():
        raise FileNotFoundError(
            f"Phase 220 artifact not found: {artifact_path}. "
            "Expected the ninth less-synthetic adversarial result at "
            "cgt_benchmarks/results/benchmark_II_partial_obs_spike/"
            "benchmark_ii_phase220_ninth_less_synthetic_adversarial.json"
        )
    payload = json.loads(artifact_path.read_text(encoding='utf-8'))
    return nan_to_none(payload)


if __name__ == '__main__':
    project_root = Path(__file__).resolve().parents[3]
    payload = run_phase220_analysis(project_root=project_root)
    print(json.dumps(nan_to_none(payload), indent=2))
