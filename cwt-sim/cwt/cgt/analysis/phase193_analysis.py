"""Phase 193 analysis: Bridge tensor geometry law v4 (benchmark scaffold family).

This module loads the pre-baked Phase 193 result artifact which records the
bridge tensor geometry law v4 candidate across all twelve bridge benchmarks.
Raw combined_r2 = 0.5572; prior_corrected (v3) combined_r2 = 0.9189; v4
corrected combined_r2 = 0.9217; v4 corrected sign_agreement = 0.9778,
confirming v4 improves upon v3 on the twelve-bridge scaffold.
"""

from __future__ import annotations

import json
from pathlib import Path

from cwt.cgt.analysis._utils import nan_to_none


def run_phase193_analysis(project_root: Path, output_root: Path | None = None) -> dict:
    """Load and return the Phase 193 bridge tensor geometry law v4 artifact.

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
        If the Phase 193 artifact JSON file is not found at the expected path.
    """
    project_root = Path(project_root)
    artifact_path = (
        project_root
        / 'cgt_benchmarks'
        / 'results'
        / 'benchmark_scaffold_family'
        / 'benchmark_scaffold_phase193_bridge_tensor_geometry_law_v4.json'
    )
    if not artifact_path.exists():
        raise FileNotFoundError(
            f"Phase 193 artifact not found: {artifact_path}. "
            "Expected the bridge tensor geometry law v4 result at "
            "cgt_benchmarks/results/benchmark_scaffold_family/"
            "benchmark_scaffold_phase193_bridge_tensor_geometry_law_v4.json"
        )
    payload = json.loads(artifact_path.read_text(encoding='utf-8'))
    return nan_to_none(payload)


if __name__ == '__main__':
    project_root = Path(__file__).resolve().parents[3]
    payload = run_phase193_analysis(project_root=project_root)
    print(json.dumps(nan_to_none(payload), indent=2))
