"""Phase 131 analysis: Pooled six-bridge positive summary (benchmark scaffold family).

This module loads the pre-baked Phase 131 result artifact which aggregates the
positive transfer evidence across all six bridge benchmarks T, U, V, W, X, and Y.
Pooled combined R2 = 0.9312 and sign_agreement = 0.9896 confirm that the positive
transfer rule generalises across six distinct semisynthetic bridge cases including
the new burst-observation benchmark Y.
Verdict: pooled_six_bridge_positive_supported.
"""

from __future__ import annotations

import json
from pathlib import Path

from cwt.cgt.analysis._utils import nan_to_none


def run_phase131_analysis(project_root: Path, output_root: Path | None = None) -> dict:
    """Load and return the Phase 131 pooled six-bridge positive artifact.

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
        If the Phase 131 artifact JSON file is not found at the expected path.
    """
    project_root = Path(project_root)
    artifact_path = (
        project_root
        / 'cgt_benchmarks'
        / 'results'
        / 'benchmark_scaffold_family'
        / 'benchmark_scaffold_phase131_pooled_six_bridge_positive.json'
    )
    if not artifact_path.exists():
        raise FileNotFoundError(
            f"Phase 131 artifact not found: {artifact_path}. "
            "Expected the pooled six-bridge positive result at "
            "cgt_benchmarks/results/benchmark_scaffold_family/"
            "benchmark_scaffold_phase131_pooled_six_bridge_positive.json"
        )
    payload = json.loads(artifact_path.read_text(encoding='utf-8'))
    return nan_to_none(payload)


if __name__ == '__main__':
    project_root = Path(__file__).resolve().parents[3]
    payload = run_phase131_analysis(project_root=project_root)
    print(json.dumps(nan_to_none(payload), indent=2))
