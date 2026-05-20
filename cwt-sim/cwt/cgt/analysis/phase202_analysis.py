"""Phase 202 analysis: Bridge correction v4 vs minimal expanded (benchmark scaffold family).

This module loads the pre-baked Phase 202 result artifact which compares
tensor geometry law v4 directly against the minimal calibration-free bridge
rule under the expanded holdout split. Minimal combined R2 = 0.8832;
tensor v4 combined R2 = 0.8964; winner = tensor_geometry_v4.
"""

from __future__ import annotations

import json
from pathlib import Path

from cwt.cgt.analysis._utils import nan_to_none


def run_phase202_analysis(project_root: Path, output_root: Path | None = None) -> dict:
    """Load and return the Phase 202 bridge correction v4 vs minimal expanded artifact.

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
        If the Phase 202 artifact JSON file is not found at the expected path.
    """
    project_root = Path(project_root)
    artifact_path = (
        project_root
        / 'cgt_benchmarks'
        / 'results'
        / 'benchmark_scaffold_family'
        / 'benchmark_scaffold_phase202_bridge_correction_v4_vs_minimal_expanded.json'
    )
    if not artifact_path.exists():
        raise FileNotFoundError(
            f"Phase 202 artifact not found: {artifact_path}. "
            "Expected the bridge correction v4 vs minimal expanded result at "
            "cgt_benchmarks/results/benchmark_scaffold_family/"
            "benchmark_scaffold_phase202_bridge_correction_v4_vs_minimal_expanded.json"
        )
    payload = json.loads(artifact_path.read_text(encoding='utf-8'))
    return nan_to_none(payload)


if __name__ == '__main__':
    project_root = Path(__file__).resolve().parents[3]
    payload = run_phase202_analysis(project_root=project_root)
    print(json.dumps(nan_to_none(payload), indent=2))
