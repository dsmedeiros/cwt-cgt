"""Phase 162 analysis: Bridge leave-one-out audit over all pilot benchmarks.

This module loads the pre-baked Phase 162 result artifact which audits the
bridge predictor rule via leave-one-out (LOO) cross-validation across the three
less-synthetic pilot benchmarks: AA_less_synthetic, BB_sensor_gap, and
CC_delayed_release. Mean holdout R2 = 0.8864 with weakest benchmark BB_sensor_gap
at 0.8748, confirming uniform generalization with no outlier pilot.
"""

from __future__ import annotations

import json
from pathlib import Path

from cwt.cgt.analysis._utils import nan_to_none


def run_phase162_analysis(project_root: Path, output_root: Path | None = None) -> dict:
    """Load and return the Phase 162 bridge LOO all-pilots audit artifact.

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
        If the Phase 162 artifact JSON file is not found at the expected path.
    """
    project_root = Path(project_root)
    artifact_path = (
        project_root
        / 'cgt_benchmarks'
        / 'results'
        / 'benchmark_scaffold_family'
        / 'benchmark_scaffold_phase162_bridge_loo_all_pilots.json'
    )
    if not artifact_path.exists():
        raise FileNotFoundError(
            f"Phase 162 artifact not found: {artifact_path}. "
            "Expected the bridge LOO all-pilots result at "
            "cgt_benchmarks/results/benchmark_scaffold_family/"
            "benchmark_scaffold_phase162_bridge_loo_all_pilots.json"
        )
    payload = json.loads(artifact_path.read_text(encoding='utf-8'))
    return nan_to_none(payload)


if __name__ == '__main__':
    project_root = Path(__file__).resolve().parents[3]
    payload = run_phase162_analysis(project_root=project_root)
    print(json.dumps(nan_to_none(payload), indent=2))
