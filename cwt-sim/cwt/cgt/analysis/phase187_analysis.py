"""Phase 187 analysis: Twelfth bridge positive (benchmark AF async burst lag).

This module loads the pre-baked Phase 187 result artifact which validates the
pooled eleven-bridge predictor rule on benchmark AF, a semisynthetic graph
benchmark with asynchronous burst censoring and hidden state lag. The twelfth
bridge benchmark introduces an asynchronous-burst-lag observation motif;
switch-slice held-out R2 = 0.9271 and sign = 1.0, confirming the positive
transfer rule holds across twelve distinct bridge benchmarks.
"""

from __future__ import annotations

import json
from pathlib import Path

from cwt.cgt.analysis._utils import nan_to_none


def run_phase187_analysis(project_root: Path, output_root: Path | None = None) -> dict:
    """Load and return the Phase 187 twelfth bridge positive artifact.

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
        If the Phase 187 artifact JSON file is not found at the expected path.
    """
    project_root = Path(project_root)
    artifact_path = (
        project_root
        / 'cgt_benchmarks'
        / 'results'
        / 'benchmark_AF_async_burst_lag'
        / 'benchmark_af_phase187_twelfth_bridge_positive.json'
    )
    if not artifact_path.exists():
        raise FileNotFoundError(
            f"Phase 187 artifact not found: {artifact_path}. "
            "Expected the twelfth bridge positive result at "
            "cgt_benchmarks/results/benchmark_AF_async_burst_lag/"
            "benchmark_af_phase187_twelfth_bridge_positive.json"
        )
    payload = json.loads(artifact_path.read_text(encoding='utf-8'))
    return nan_to_none(payload)


if __name__ == '__main__':
    project_root = Path(__file__).resolve().parents[3]
    payload = run_phase187_analysis(project_root=project_root)
    print(json.dumps(nan_to_none(payload), indent=2))
