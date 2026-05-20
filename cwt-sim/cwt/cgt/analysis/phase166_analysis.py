"""Phase 166 analysis: Bridge boundary refresh v2 (benchmark scaffold family).

This module loads the pre-baked Phase 166 result artifact which records the
updated acceptance boundary bands after the nine-bridge family is established.
Positive band spans [0.8748, 0.9981]; adversarial raw band spans [0.4011, 0.6024];
adversarial corrected band spans [0.8235, 0.9126]. The weakest positive benchmark
is BB_sensor_gap (0.8748). These bands serve as the v2 acceptance criteria for
subsequent phases.
"""

from __future__ import annotations

import json
from pathlib import Path

from cwt.cgt.analysis._utils import nan_to_none


def run_phase166_analysis(project_root: Path, output_root: Path | None = None) -> dict:
    """Load and return the Phase 166 bridge boundary refresh v2 artifact.

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
        If the Phase 166 artifact JSON file is not found at the expected path.
    """
    project_root = Path(project_root)
    artifact_path = (
        project_root
        / 'cgt_benchmarks'
        / 'results'
        / 'benchmark_scaffold_family'
        / 'benchmark_scaffold_phase166_bridge_boundary_refresh.json'
    )
    if not artifact_path.exists():
        raise FileNotFoundError(
            f"Phase 166 artifact not found: {artifact_path}. "
            "Expected the bridge boundary refresh v2 result at "
            "cgt_benchmarks/results/benchmark_scaffold_family/"
            "benchmark_scaffold_phase166_bridge_boundary_refresh.json"
        )
    payload = json.loads(artifact_path.read_text(encoding='utf-8'))
    return nan_to_none(payload)


if __name__ == '__main__':
    project_root = Path(__file__).resolve().parents[3]
    payload = run_phase166_analysis(project_root=project_root)
    print(json.dumps(nan_to_none(payload), indent=2))
