"""Phase 177 analysis: Eleventh bridge positive benchmark (benchmark AE state occluded irregular).

This module loads the pre-baked Phase 177 result artifact which validates the
pooled ten-bridge predictor rule on benchmark AE, a semisynthetic graph benchmark
with state occlusion combined with irregular release windows. The eleventh bridge
benchmark introduces a novel state-occluded irregular-release observation motif;
switch-slice held-out R2 = 0.9258 and sign = 1.0, confirming the positive transfer
rule holds across eleven distinct bridge benchmarks.
"""

from __future__ import annotations

import json
from pathlib import Path

from cwt.cgt.analysis._utils import nan_to_none


def run_phase177_analysis(project_root: Path, output_root: Path | None = None) -> dict:
    """Load and return the Phase 177 eleventh bridge positive artifact.

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
        If the Phase 177 artifact JSON file is not found at the expected path.
    """
    project_root = Path(project_root)
    artifact_path = (
        project_root
        / 'cgt_benchmarks'
        / 'results'
        / 'benchmark_AE_state_occluded_irregular'
        / 'benchmark_ae_phase177_eleventh_bridge_positive.json'
    )
    if not artifact_path.exists():
        raise FileNotFoundError(
            f"Phase 177 artifact not found: {artifact_path}. "
            "Expected the eleventh bridge positive result at "
            "cgt_benchmarks/results/benchmark_AE_state_occluded_irregular/"
            "benchmark_ae_phase177_eleventh_bridge_positive.json"
        )
    payload = json.loads(artifact_path.read_text(encoding='utf-8'))
    return nan_to_none(payload)


if __name__ == '__main__':
    project_root = Path(__file__).resolve().parents[3]
    payload = run_phase177_analysis(project_root=project_root)
    print(json.dumps(nan_to_none(payload), indent=2))
