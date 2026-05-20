"""Phase 199 analysis: Seventh less-synthetic positive (benchmark GG windowed sparse release).

This module loads the pre-baked Phase 199 result artifact which validates the
pooled twelve-bridge predictor rule on benchmark GG, a less-synthetic graph
benchmark with mixed release windows and delayed event thinning.
Switch-slice held-out R2 = 0.8987, corr = 0.9732, sign = 0.9861, confirming
the positive transfer rule holds on the seventh less-synthetic pilot benchmark.
"""

from __future__ import annotations

import json
from pathlib import Path

from cwt.cgt.analysis._utils import nan_to_none


def run_phase199_analysis(project_root: Path, output_root: Path | None = None) -> dict:
    """Load and return the Phase 199 seventh less-synthetic positive artifact.

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
        If the Phase 199 artifact JSON file is not found at the expected path.
    """
    project_root = Path(project_root)
    artifact_path = (
        project_root
        / 'cgt_benchmarks'
        / 'results'
        / 'benchmark_GG_windowed_sparse_release'
        / 'benchmark_gg_phase199_seventh_less_synthetic_positive.json'
    )
    if not artifact_path.exists():
        raise FileNotFoundError(
            f"Phase 199 artifact not found: {artifact_path}. "
            "Expected the seventh less-synthetic positive result at "
            "cgt_benchmarks/results/benchmark_GG_windowed_sparse_release/"
            "benchmark_gg_phase199_seventh_less_synthetic_positive.json"
        )
    payload = json.loads(artifact_path.read_text(encoding='utf-8'))
    return nan_to_none(payload)


if __name__ == '__main__':
    project_root = Path(__file__).resolve().parents[3]
    payload = run_phase199_analysis(project_root=project_root)
    print(json.dumps(nan_to_none(payload), indent=2))
