"""Phase 222 analysis: Bridge holdout v7 comparison (benchmark scaffold family).

This module loads the pre-baked Phase 222 result artifact which compares minimal,
tensor-law v6, and tensor-law v7 under the same expanded holdout split.
Switch gamma = 0.30. Pilot count = 9.
Minimal mean R2 = 0.8804; tensor v6 mean R2 = 0.9006; tensor v7 mean R2 = 0.9031;
gain v7 over v6 = 0.0025; weakest benchmark: GG_windowed_sparse_release.
"""

from __future__ import annotations

import json
from pathlib import Path

from cwt.cgt.analysis._utils import nan_to_none


def run_phase222_analysis(project_root: Path, output_root: Path | None = None) -> dict:
    """Load and return the Phase 222 bridge holdout v7 comparison artifact.

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
        If the Phase 222 artifact JSON file is not found at the expected path.
    """
    project_root = Path(project_root)
    artifact_path = (
        project_root
        / 'cgt_benchmarks'
        / 'results'
        / 'benchmark_scaffold_family'
        / 'benchmark_scaffold_phase222_bridge_holdout_v7_comparison.json'
    )
    if not artifact_path.exists():
        raise FileNotFoundError(
            f"Phase 222 artifact not found: {artifact_path}. "
            "Expected the bridge holdout v7 comparison result at "
            "cgt_benchmarks/results/benchmark_scaffold_family/"
            "benchmark_scaffold_phase222_bridge_holdout_v7_comparison.json"
        )
    payload = json.loads(artifact_path.read_text(encoding='utf-8'))
    return nan_to_none(payload)


if __name__ == '__main__':
    project_root = Path(__file__).resolve().parents[3]
    payload = run_phase222_analysis(project_root=project_root)
    print(json.dumps(nan_to_none(payload), indent=2))
