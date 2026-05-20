"""Phase 201 analysis: Bridge LOO holdout expanded v2 (benchmark scaffold family).

This module loads the pre-baked Phase 201 result artifact which encodes the
expanded bridge benchmark-holdout audit across bridge and pilot cases.
Eighteen benchmarks (T, U, V, W, X, Y, Z, AA, BB, AC, CC, DD, AE, EE, AF, FF, AG, GG)
were evaluated; mean held-out combined R2 = 0.8871; weakest benchmark = BB_sensor_gap.
"""

from __future__ import annotations

import json
from pathlib import Path

from cwt.cgt.analysis._utils import nan_to_none


def run_phase201_analysis(project_root: Path, output_root: Path | None = None) -> dict:
    """Load and return the Phase 201 bridge LOO holdout expanded v2 artifact.

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
        If the Phase 201 artifact JSON file is not found at the expected path.
    """
    project_root = Path(project_root)
    artifact_path = (
        project_root
        / 'cgt_benchmarks'
        / 'results'
        / 'benchmark_scaffold_family'
        / 'benchmark_scaffold_phase201_bridge_holdout_expanded_v2.json'
    )
    if not artifact_path.exists():
        raise FileNotFoundError(
            f"Phase 201 artifact not found: {artifact_path}. "
            "Expected the bridge LOO holdout expanded v2 result at "
            "cgt_benchmarks/results/benchmark_scaffold_family/"
            "benchmark_scaffold_phase201_bridge_holdout_expanded_v2.json"
        )
    payload = json.loads(artifact_path.read_text(encoding='utf-8'))
    return nan_to_none(payload)


if __name__ == '__main__':
    project_root = Path(__file__).resolve().parents[3]
    payload = run_phase201_analysis(project_root=project_root)
    print(json.dumps(nan_to_none(payload), indent=2))
