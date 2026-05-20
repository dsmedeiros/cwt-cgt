"""Phase 208 analysis: Bridge holdout strict v5 vs minimal (benchmark scaffold family).

This module loads the pre-baked Phase 208 result artifact which validates the
tensor geometry law v5 under a strict holdout benchmark comparison protocol.
Strict holdout mean R2 (tensor v5) = 0.8934 vs minimal = 0.8792; mean gain = 0.0142.
Weakest benchmark: GG_windowed_sparse_release.
"""

from __future__ import annotations

import json
from pathlib import Path

from cwt.cgt.analysis._utils import nan_to_none


def run_phase208_analysis(project_root: Path, output_root: Path | None = None) -> dict:
    """Load and return the Phase 208 bridge holdout strict artifact.

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
        If the Phase 208 artifact JSON file is not found at the expected path.
    """
    project_root = Path(project_root)
    artifact_path = (
        project_root
        / 'cgt_benchmarks'
        / 'results'
        / 'benchmark_scaffold_family'
        / 'benchmark_scaffold_phase208_bridge_holdout_strict.json'
    )
    if not artifact_path.exists():
        raise FileNotFoundError(
            f"Phase 208 artifact not found: {artifact_path}. "
            "Expected the bridge holdout strict result at "
            "cgt_benchmarks/results/benchmark_scaffold_family/"
            "benchmark_scaffold_phase208_bridge_holdout_strict.json"
        )
    payload = json.loads(artifact_path.read_text(encoding='utf-8'))
    return nan_to_none(payload)


if __name__ == '__main__':
    project_root = Path(__file__).resolve().parents[3]
    payload = run_phase208_analysis(project_root=project_root)
    print(json.dumps(nan_to_none(payload), indent=2))
