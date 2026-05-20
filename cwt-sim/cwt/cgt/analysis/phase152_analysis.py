"""Phase 152 analysis: Second less-synthetic adversarial pilot (benchmark BB sensor-gap).

This module loads the pre-baked Phase 152 result artifact which applies the
tensor-compactness bridge correction to benchmark BB under adversarial conditions.
Raw combined R2 = 0.4011 degrades under adversarial perturbation; corrected
combined R2 = 0.8049 and sign agreement = 0.9444 confirm recovery, supporting
the second less-synthetic bridge adversarial result.
"""

from __future__ import annotations

import json
from pathlib import Path

from cwt.cgt.analysis._utils import nan_to_none


def run_phase152_analysis(project_root: Path, output_root: Path | None = None) -> dict:
    """Load and return the Phase 152 second less-synthetic adversarial artifact.

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
        If the Phase 152 artifact JSON file is not found at the expected path.
    """
    project_root = Path(project_root)
    artifact_path = (
        project_root
        / 'cgt_benchmarks'
        / 'results'
        / 'benchmark_BB_sensor_gap'
        / 'benchmark_bb_phase152_second_less_synthetic_adversarial.json'
    )
    if not artifact_path.exists():
        raise FileNotFoundError(
            f"Phase 152 artifact not found: {artifact_path}. "
            "Expected the second less-synthetic adversarial result at "
            "cgt_benchmarks/results/benchmark_BB_sensor_gap/"
            "benchmark_bb_phase152_second_less_synthetic_adversarial.json"
        )
    payload = json.loads(artifact_path.read_text(encoding='utf-8'))
    return nan_to_none(payload)


if __name__ == '__main__':
    project_root = Path(__file__).resolve().parents[3]
    payload = run_phase152_analysis(project_root=project_root)
    print(json.dumps(nan_to_none(payload), indent=2))
