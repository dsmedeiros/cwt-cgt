"""Phase 153 analysis: Bridge leave-one-benchmark-out audit including pilots.

This module loads the pre-baked Phase 153 result artifact which runs a
leave-one-benchmark-out (LOO) audit across the full bridge lane including the two
pilot benchmarks (AA and BB). Mean held-out combined R2 = 0.8798; weakest benchmark
is BB_sensor_gap at 0.8381, confirming broad robustness with a noted degradation
on the sensor-gap pilot.
"""

from __future__ import annotations

import json
from pathlib import Path

from cwt.cgt.analysis._utils import nan_to_none


def run_phase153_analysis(project_root: Path, output_root: Path | None = None) -> dict:
    """Load and return the Phase 153 bridge LOO with pilots artifact.

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
        If the Phase 153 artifact JSON file is not found at the expected path.
    """
    project_root = Path(project_root)
    artifact_path = (
        project_root
        / 'cgt_benchmarks'
        / 'results'
        / 'benchmark_scaffold_family'
        / 'benchmark_scaffold_phase153_bridge_loo_with_pilots.json'
    )
    if not artifact_path.exists():
        raise FileNotFoundError(
            f"Phase 153 artifact not found: {artifact_path}. "
            "Expected the bridge LOO with pilots result at "
            "cgt_benchmarks/results/benchmark_scaffold_family/"
            "benchmark_scaffold_phase153_bridge_loo_with_pilots.json"
        )
    payload = json.loads(artifact_path.read_text(encoding='utf-8'))
    return nan_to_none(payload)


if __name__ == '__main__':
    project_root = Path(__file__).resolve().parents[3]
    payload = run_phase153_analysis(project_root=project_root)
    print(json.dumps(nan_to_none(payload), indent=2))
