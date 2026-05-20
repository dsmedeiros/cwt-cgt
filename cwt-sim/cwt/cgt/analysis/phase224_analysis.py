"""Phase 224 analysis: Bridge-pilot positive summary (benchmark scaffold family).

This module loads the pre-baked Phase 224 result artifact which builds the first
pooled bridge+pilot positive summary to quantify the externalization gap directly.
Switch gamma = 0.30. Bridge count = 13, pilot count = 9.
Bridge positive mean R2 = 0.9341; pilot positive mean R2 = 0.8963;
bridge/pilot gap = 0.0378.
"""

from __future__ import annotations

import json
from pathlib import Path

from cwt.cgt.analysis._utils import nan_to_none


def run_phase224_analysis(project_root: Path, output_root: Path | None = None) -> dict:
    """Load and return the Phase 224 bridge-pilot positive summary artifact.

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
        If the Phase 224 artifact JSON file is not found at the expected path.
    """
    project_root = Path(project_root)
    artifact_path = (
        project_root
        / 'cgt_benchmarks'
        / 'results'
        / 'benchmark_scaffold_family'
        / 'benchmark_scaffold_phase224_bridge_pilot_positive_summary.json'
    )
    if not artifact_path.exists():
        raise FileNotFoundError(
            f"Phase 224 artifact not found: {artifact_path}. "
            "Expected the bridge-pilot positive summary result at "
            "cgt_benchmarks/results/benchmark_scaffold_family/"
            "benchmark_scaffold_phase224_bridge_pilot_positive_summary.json"
        )
    payload = json.loads(artifact_path.read_text(encoding='utf-8'))
    return nan_to_none(payload)


if __name__ == '__main__':
    project_root = Path(__file__).resolve().parents[3]
    payload = run_phase224_analysis(project_root=project_root)
    print(json.dumps(nan_to_none(payload), indent=2))
