"""Phase 196 analysis: Bridge boundary refresh v5 (benchmark scaffold family).

This module loads the pre-baked Phase 196 result artifact which encodes the
bridge boundary refresh v5 — the updated positive and adversarial corrected
performance bands across all twelve bridge benchmarks. Positive band spans
[0.8748, 0.9409]; adversarial corrected band spans [0.8197, 0.9217]; bridge_count = 12;
pilot_count = 6. The weakest positive benchmark is BB_sensor_gap; the weakest
adversarial corrected benchmark is EE_sparse_release. Recommendation: shift
toward externalization after limited further bridge compression.
"""

from __future__ import annotations

import json
from pathlib import Path

from cwt.cgt.analysis._utils import nan_to_none


def run_phase196_analysis(project_root: Path, output_root: Path | None = None) -> dict:
    """Load and return the Phase 196 bridge boundary refresh v5 artifact.

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
        If the Phase 196 artifact JSON file is not found at the expected path.
    """
    project_root = Path(project_root)
    artifact_path = (
        project_root
        / 'cgt_benchmarks'
        / 'results'
        / 'benchmark_scaffold_family'
        / 'benchmark_scaffold_phase196_bridge_boundary_refresh_v5.json'
    )
    if not artifact_path.exists():
        raise FileNotFoundError(
            f"Phase 196 artifact not found: {artifact_path}. "
            "Expected the bridge boundary refresh v5 result at "
            "cgt_benchmarks/results/benchmark_scaffold_family/"
            "benchmark_scaffold_phase196_bridge_boundary_refresh_v5.json"
        )
    payload = json.loads(artifact_path.read_text(encoding='utf-8'))
    return nan_to_none(payload)


if __name__ == '__main__':
    project_root = Path(__file__).resolve().parents[3]
    payload = run_phase196_analysis(project_root=project_root)
    print(json.dumps(nan_to_none(payload), indent=2))
