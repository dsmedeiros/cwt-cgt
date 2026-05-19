"""Phase 129 analysis: Sixth bridge positive benchmark (benchmark Y burst-observed).

This module loads the pre-baked Phase 129 result artifact which validates the
pooled positive rule on benchmark Y, a semisynthetic graph benchmark with a
burst-observation bottleneck. The sixth bridge benchmark extends the bridge lane
to a new observation-regime stress test. Held-out combined R2 = 0.9199 and
sign_agreement = 0.9882, confirming the positive transfer rule holds across six
distinct bridge benchmarks.
Verdict: sixth_bridge_positive_supported.
"""

from __future__ import annotations

import json
from pathlib import Path

from cwt.cgt.analysis._utils import nan_to_none


def run_phase129_analysis(project_root: Path, output_root: Path | None = None) -> dict:
    """Load and return the Phase 129 sixth bridge positive artifact.

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
        If the Phase 129 artifact JSON file is not found at the expected path.
    """
    project_root = Path(project_root)
    artifact_path = (
        project_root
        / 'cgt_benchmarks'
        / 'results'
        / 'benchmark_Y_burst_observed'
        / 'benchmark_y_phase129_sixth_bridge_positive.json'
    )
    if not artifact_path.exists():
        raise FileNotFoundError(
            f"Phase 129 artifact not found: {artifact_path}. "
            "Expected the sixth bridge positive result at "
            "cgt_benchmarks/results/benchmark_Y_burst_observed/"
            "benchmark_y_phase129_sixth_bridge_positive.json"
        )
    payload = json.loads(artifact_path.read_text(encoding='utf-8'))
    return nan_to_none(payload)


if __name__ == '__main__':
    project_root = Path(__file__).resolve().parents[3]
    payload = run_phase129_analysis(project_root=project_root)
    print(json.dumps(nan_to_none(payload), indent=2))
