"""Phase 174 analysis: Bridge holdout expanded comparison (benchmark scaffold family).

This module loads the pre-baked Phase 174 result artifact which compares the
bridge tensor predictor rule against the minimal counterfactual baseline on the
expanded held-out benchmark set including the fourth less-synthetic pilot DD.
The tensor rule achieves mean_holdout_r2 = 0.8921 vs. minimal 0.8783, confirming
the tensor geometry advantage persists after expanding the pilot set.
"""

from __future__ import annotations

import json
from pathlib import Path

from cwt.cgt.analysis._utils import nan_to_none


def run_phase174_analysis(project_root: Path, output_root: Path | None = None) -> dict:
    """Load and return the Phase 174 bridge holdout expanded comparison artifact.

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
        If the Phase 174 artifact JSON file is not found at the expected path.
    """
    project_root = Path(project_root)
    artifact_path = (
        project_root
        / 'cgt_benchmarks'
        / 'results'
        / 'benchmark_scaffold_family'
        / 'benchmark_scaffold_phase174_bridge_holdout_expanded_comparison.json'
    )
    if not artifact_path.exists():
        raise FileNotFoundError(
            f"Phase 174 artifact not found: {artifact_path}. "
            "Expected the bridge holdout expanded comparison result at "
            "cgt_benchmarks/results/benchmark_scaffold_family/"
            "benchmark_scaffold_phase174_bridge_holdout_expanded_comparison.json"
        )
    payload = json.loads(artifact_path.read_text(encoding='utf-8'))
    return nan_to_none(payload)


if __name__ == '__main__':
    project_root = Path(__file__).resolve().parents[3]
    payload = run_phase174_analysis(project_root=project_root)
    print(json.dumps(nan_to_none(payload), indent=2))
