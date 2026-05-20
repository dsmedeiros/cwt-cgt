"""Phase 213 analysis: Bridge correction v6 comparison (benchmark scaffold family).

This module loads the pre-baked Phase 213 result artifact which compares the
minimal rule, tensor v5, and tensor v6 correction strategies across the full
bridge benchmark suite. Tensor v6 combined_r2 = 0.9262 vs v5 = 0.9231 vs
minimal = 0.8821. Tensor v6 sign_agreement = 0.9798.
"""

from __future__ import annotations

import json
from pathlib import Path

from cwt.cgt.analysis._utils import nan_to_none


def run_phase213_analysis(project_root: Path, output_root: Path | None = None) -> dict:
    """Load and return the Phase 213 bridge correction v6 comparison artifact.

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
        If the Phase 213 artifact JSON file is not found at the expected path.
    """
    project_root = Path(project_root)
    artifact_path = (
        project_root
        / 'cgt_benchmarks'
        / 'results'
        / 'benchmark_scaffold_family'
        / 'benchmark_scaffold_phase213_bridge_correction_v6_compare.json'
    )
    if not artifact_path.exists():
        raise FileNotFoundError(
            f"Phase 213 artifact not found: {artifact_path}. "
            "Expected the bridge correction v6 compare result at "
            "cgt_benchmarks/results/benchmark_scaffold_family/"
            "benchmark_scaffold_phase213_bridge_correction_v6_compare.json"
        )
    payload = json.loads(artifact_path.read_text(encoding='utf-8'))
    return nan_to_none(payload)


if __name__ == '__main__':
    project_root = Path(__file__).resolve().parents[3]
    payload = run_phase213_analysis(project_root=project_root)
    print(json.dumps(nan_to_none(payload), indent=2))
