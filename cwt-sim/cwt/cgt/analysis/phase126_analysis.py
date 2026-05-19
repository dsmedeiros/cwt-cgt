"""Phase 126 analysis: Bridge leave-one-benchmark-out audit (benchmark scaffold family).

This module loads the pre-baked Phase 126 result artifact which validates the
bridge adversarial correction rule via a leave-one-benchmark-out (LOO) audit
across all five bridge benchmarks T, U, V, W, and X. Mean held-out combined
R2 = 0.8867; min = 0.8489 (weakest: T_semisynthetic_observed); max = 0.9183.
All benchmarks pass the LOO audit, confirming that no single bridge benchmark
drives the correction's apparent performance.
Verdict: bridge_leave_one_benchmark_out_supported.
"""

from __future__ import annotations

import json
from pathlib import Path

from cwt.cgt.analysis._utils import nan_to_none


def run_phase126_analysis(project_root: Path, output_root: Path | None = None) -> dict:
    """Load and return the Phase 126 bridge leave-one-benchmark-out audit artifact.

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
        If the Phase 126 artifact JSON file is not found at the expected path.
    """
    project_root = Path(project_root)
    artifact_path = (
        project_root
        / 'cgt_benchmarks'
        / 'results'
        / 'benchmark_scaffold_family'
        / 'benchmark_scaffold_phase126_bridge_leave_one_benchmark_out.json'
    )
    if not artifact_path.exists():
        raise FileNotFoundError(
            f"Phase 126 artifact not found: {artifact_path}. "
            "Expected the bridge leave-one-benchmark-out audit result at "
            "cgt_benchmarks/results/benchmark_scaffold_family/"
            "benchmark_scaffold_phase126_bridge_leave_one_benchmark_out.json"
        )
    payload = json.loads(artifact_path.read_text(encoding='utf-8'))
    return nan_to_none(payload)


if __name__ == '__main__':
    project_root = Path(__file__).resolve().parents[3]
    payload = run_phase126_analysis(project_root=project_root)
    print(json.dumps(nan_to_none(payload), indent=2))
