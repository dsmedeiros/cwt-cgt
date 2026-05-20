"""Phase 197 analysis: Thirteenth bridge positive (benchmark AG irregular hidden censor).

This module loads the pre-baked Phase 197 result artifact which validates the
pooled twelve-bridge predictor rule on benchmark AG, a semisynthetic graph
benchmark with irregular hidden-state lag plus asynchronous censoring. The
thirteenth bridge benchmark introduces an irregular hidden-state lag combined
with asynchronous censoring observation motif; switch-slice held-out R2 = 0.9264,
corr = 0.9861, sign = 1.0, confirming the positive transfer rule holds across
thirteen distinct bridge benchmarks.
"""

from __future__ import annotations

import json
from pathlib import Path

from cwt.cgt.analysis._utils import nan_to_none


def run_phase197_analysis(project_root: Path, output_root: Path | None = None) -> dict:
    """Load and return the Phase 197 thirteenth bridge positive artifact.

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
        If the Phase 197 artifact JSON file is not found at the expected path.
    """
    project_root = Path(project_root)
    artifact_path = (
        project_root
        / 'cgt_benchmarks'
        / 'results'
        / 'benchmark_AG_irregular_hidden_censor'
        / 'benchmark_ag_phase197_thirteenth_bridge_positive.json'
    )
    if not artifact_path.exists():
        raise FileNotFoundError(
            f"Phase 197 artifact not found: {artifact_path}. "
            "Expected the thirteenth bridge positive result at "
            "cgt_benchmarks/results/benchmark_AG_irregular_hidden_censor/"
            "benchmark_ag_phase197_thirteenth_bridge_positive.json"
        )
    payload = json.loads(artifact_path.read_text(encoding='utf-8'))
    return nan_to_none(payload)


if __name__ == '__main__':
    project_root = Path(__file__).resolve().parents[3]
    payload = run_phase197_analysis(project_root=project_root)
    print(json.dumps(nan_to_none(payload), indent=2))
