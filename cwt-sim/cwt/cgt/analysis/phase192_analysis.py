"""Phase 192 analysis: Bridge correction v3 vs minimal expanded (benchmark scaffold family).

This module loads the pre-baked Phase 192 result artifact which compares the
bridge tensor geometry law v3 against the minimal rule across all twelve bridge
benchmarks. minimal_rule combined_r2 = 0.8821; tensor_law_v3 combined_r2 =
0.8958; improvement = 0.0137, confirming v3 outperforms minimal on the
expanded twelve-bridge scaffold.
"""

from __future__ import annotations

import json
from pathlib import Path

from cwt.cgt.analysis._utils import nan_to_none


def run_phase192_analysis(project_root: Path, output_root: Path | None = None) -> dict:
    """Load and return the Phase 192 bridge correction v3 vs minimal expanded artifact.

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
        If the Phase 192 artifact JSON file is not found at the expected path.
    """
    project_root = Path(project_root)
    artifact_path = (
        project_root
        / 'cgt_benchmarks'
        / 'results'
        / 'benchmark_scaffold_family'
        / 'benchmark_scaffold_phase192_bridge_correction_v3_vs_minimal_expanded.json'
    )
    if not artifact_path.exists():
        raise FileNotFoundError(
            f"Phase 192 artifact not found: {artifact_path}. "
            "Expected the bridge correction v3 vs minimal expanded result at "
            "cgt_benchmarks/results/benchmark_scaffold_family/"
            "benchmark_scaffold_phase192_bridge_correction_v3_vs_minimal_expanded.json"
        )
    payload = json.loads(artifact_path.read_text(encoding='utf-8'))
    return nan_to_none(payload)


if __name__ == '__main__':
    project_root = Path(__file__).resolve().parents[3]
    payload = run_phase192_analysis(project_root=project_root)
    print(json.dumps(nan_to_none(payload), indent=2))
