"""Phase 151 analysis: Second less-synthetic positive pilot (benchmark BB sensor-gap).

This module loads the pre-baked Phase 151 result artifact which validates the
pooled seven-bridge predictor on benchmark BB, a semisynthetic graph benchmark
with sensor-gap masking. Switch-slice held-out combined R2 = 0.8748 and
sign_agreement = 1.0, confirming the positive transfer rule holds on a second
less-synthetic pilot benchmark.
"""

from __future__ import annotations

import json
from pathlib import Path

from cwt.cgt.analysis._utils import nan_to_none


def run_phase151_analysis(project_root: Path, output_root: Path | None = None) -> dict:
    """Load and return the Phase 151 second less-synthetic positive artifact.

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
        If the Phase 151 artifact JSON file is not found at the expected path.
    """
    project_root = Path(project_root)
    artifact_path = (
        project_root
        / 'cgt_benchmarks'
        / 'results'
        / 'benchmark_BB_sensor_gap'
        / 'benchmark_bb_phase151_second_less_synthetic_positive.json'
    )
    if not artifact_path.exists():
        raise FileNotFoundError(
            f"Phase 151 artifact not found: {artifact_path}. "
            "Expected the second less-synthetic positive result at "
            "cgt_benchmarks/results/benchmark_BB_sensor_gap/"
            "benchmark_bb_phase151_second_less_synthetic_positive.json"
        )
    payload = json.loads(artifact_path.read_text(encoding='utf-8'))
    return nan_to_none(payload)


if __name__ == '__main__':
    project_root = Path(__file__).resolve().parents[3]
    payload = run_phase151_analysis(project_root=project_root)
    print(json.dumps(nan_to_none(payload), indent=2))
