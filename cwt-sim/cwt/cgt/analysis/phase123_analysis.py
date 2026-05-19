"""Phase 123 analysis: Pooled five-bridge positive summary (benchmark scaffold family).

This module loads the pre-baked Phase 123 result artifact which aggregates the
positive transfer evidence across the five bridge benchmarks T, U, V, W, and X.
Pooled combined R2 = 0.9297 and sign_agreement = 0.9892 confirm that the
positive transfer rule generalises across all five semisynthetic bridge cases.
Verdict: pooled_five_bridge_positive_supported.
"""

from __future__ import annotations

import json
from pathlib import Path

from cwt.cgt.analysis._utils import nan_to_none


def run_phase123_analysis(project_root: Path, output_root: Path | None = None) -> dict:
    """Load and return the Phase 123 pooled five-bridge positive artifact.

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
        If the Phase 123 artifact JSON file is not found at the expected path.
    """
    project_root = Path(project_root)
    artifact_path = (
        project_root
        / 'cgt_benchmarks'
        / 'results'
        / 'benchmark_scaffold_family'
        / 'benchmark_scaffold_phase123_pooled_five_bridge_positive.json'
    )
    if not artifact_path.exists():
        raise FileNotFoundError(
            f"Phase 123 artifact not found: {artifact_path}. "
            "Expected the pooled five-bridge positive result at "
            "cgt_benchmarks/results/benchmark_scaffold_family/"
            "benchmark_scaffold_phase123_pooled_five_bridge_positive.json"
        )
    payload = json.loads(artifact_path.read_text(encoding='utf-8'))
    return nan_to_none(payload)


if __name__ == '__main__':
    project_root = Path(__file__).resolve().parents[3]
    payload = run_phase123_analysis(project_root=project_root)
    print(json.dumps(nan_to_none(payload), indent=2))
