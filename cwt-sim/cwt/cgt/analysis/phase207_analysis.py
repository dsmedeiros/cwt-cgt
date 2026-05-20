"""Phase 207 analysis: Bridge externalization readiness v3 (benchmark scaffold family).

This module loads the pre-baked Phase 207 result artifact which encodes the
bridge externalization readiness summary v3. Readiness score = 0.71.
Readiness bands: coherent_core = 0.89, noisy_scaffold = 0.81, bridge_lane = 0.63.
Blocking items: additional less-synthetic bridge evidence; benchmark-holdout
comparison of tensor v5 vs minimal; local bridge tensor geometry compression
beyond pooled summaries.
"""

from __future__ import annotations

import json
from pathlib import Path

from cwt.cgt.analysis._utils import nan_to_none


def run_phase207_analysis(project_root: Path, output_root: Path | None = None) -> dict:
    """Load and return the Phase 207 bridge externalization readiness v3 artifact.

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
        If the Phase 207 artifact JSON file is not found at the expected path.
    """
    project_root = Path(project_root)
    artifact_path = (
        project_root
        / 'cgt_benchmarks'
        / 'results'
        / 'benchmark_scaffold_family'
        / 'benchmark_scaffold_phase207_bridge_externalization_readiness_v3.json'
    )
    if not artifact_path.exists():
        raise FileNotFoundError(
            f"Phase 207 artifact not found: {artifact_path}. "
            "Expected the bridge externalization readiness v3 result at "
            "cgt_benchmarks/results/benchmark_scaffold_family/"
            "benchmark_scaffold_phase207_bridge_externalization_readiness_v3.json"
        )
    payload = json.loads(artifact_path.read_text(encoding='utf-8'))
    return nan_to_none(payload)


if __name__ == '__main__':
    project_root = Path(__file__).resolve().parents[3]
    payload = run_phase207_analysis(project_root=project_root)
    print(json.dumps(nan_to_none(payload), indent=2))
