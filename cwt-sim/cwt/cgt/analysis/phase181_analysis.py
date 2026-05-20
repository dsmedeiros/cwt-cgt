"""Phase 181 analysis: Fifth less-synthetic positive benchmark (benchmark EE sparse release).

This module loads the pre-baked Phase 181 result artifact which validates the
pooled eleven-bridge predictor rule on benchmark EE, a semisynthetic graph benchmark
with delayed release combined with event-thinning sparse observations. The fifth
less-synthetic benchmark stress-tests sparse-release dynamics; held-out R2 = 0.8906,
corr = 0.9558, and sign = 1.0, confirming the positive transfer rule holds under
the pooled-eleven configuration.
"""

from __future__ import annotations

import json
from pathlib import Path

from cwt.cgt.analysis._utils import nan_to_none


def run_phase181_analysis(project_root: Path, output_root: Path | None = None) -> dict:
    """Load and return the Phase 181 fifth less-synthetic positive artifact.

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
        If the Phase 181 artifact JSON file is not found at the expected path.
    """
    project_root = Path(project_root)
    artifact_path = (
        project_root
        / 'cgt_benchmarks'
        / 'results'
        / 'benchmark_EE_sparse_release'
        / 'benchmark_ee_phase181_fifth_less_synthetic_positive.json'
    )
    if not artifact_path.exists():
        raise FileNotFoundError(
            f"Phase 181 artifact not found: {artifact_path}. "
            "Expected the fifth less-synthetic positive result at "
            "cgt_benchmarks/results/benchmark_EE_sparse_release/"
            "benchmark_ee_phase181_fifth_less_synthetic_positive.json"
        )
    payload = json.loads(artifact_path.read_text(encoding='utf-8'))
    return nan_to_none(payload)


if __name__ == '__main__':
    project_root = Path(__file__).resolve().parents[3]
    payload = run_phase181_analysis(project_root=project_root)
    print(json.dumps(nan_to_none(payload), indent=2))
