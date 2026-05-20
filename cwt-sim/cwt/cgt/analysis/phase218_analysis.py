"""Phase 218 analysis: Bridge holdout expanded v6 vs minimal (benchmark scaffold family).

This module loads the pre-baked Phase 218 result artifact which performs a strict
expanded benchmark-holdout comparison of the minimal bridge rule vs tensor-law v6
on the full bridge + pilot set. Switch gamma = 0.30.
Minimal mean held-out R2 = 0.8804; tensor-law v6 mean held-out R2 = 0.9006;
mean gain = 0.0202; weakest benchmark: GG_windowed_sparse_release.
"""

from __future__ import annotations

import json
from pathlib import Path

from cwt.cgt.analysis._utils import nan_to_none


def run_phase218_analysis(project_root: Path, output_root: Path | None = None) -> dict:
    """Load and return the Phase 218 bridge holdout expanded v6 vs minimal artifact.

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
        If the Phase 218 artifact JSON file is not found at the expected path.
    """
    project_root = Path(project_root)
    artifact_path = (
        project_root
        / 'cgt_benchmarks'
        / 'results'
        / 'benchmark_scaffold_family'
        / 'benchmark_scaffold_phase218_bridge_holdout_expanded_v6_vs_minimal.json'
    )
    if not artifact_path.exists():
        raise FileNotFoundError(
            f"Phase 218 artifact not found: {artifact_path}. "
            "Expected the bridge holdout expanded v6 vs minimal result at "
            "cgt_benchmarks/results/benchmark_scaffold_family/"
            "benchmark_scaffold_phase218_bridge_holdout_expanded_v6_vs_minimal.json"
        )
    payload = json.loads(artifact_path.read_text(encoding='utf-8'))
    return nan_to_none(payload)


if __name__ == '__main__':
    project_root = Path(__file__).resolve().parents[3]
    payload = run_phase218_analysis(project_root=project_root)
    print(json.dumps(nan_to_none(payload), indent=2))
