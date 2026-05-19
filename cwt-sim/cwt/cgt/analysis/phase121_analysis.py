"""Phase 121 analysis: Fifth bridge positive benchmark (benchmark X event-thinned).

This module loads the pre-baked Phase 121 result artifact which validates the
pooled positive rule on benchmark X, a semisynthetic graph benchmark with
event-triggered/state-thinned observations. The fifth bridge benchmark adds a
new observation-regime stress test; held-out combined R2 = 0.9248 and
sign_agreement = 0.9889, confirming the positive transfer rule holds across
five distinct bridge benchmarks.
"""

from __future__ import annotations

import json
from pathlib import Path

from cwt.cgt.analysis._utils import nan_to_none


def run_phase121_analysis(project_root: Path, output_root: Path | None = None) -> dict:
    """Load and return the Phase 121 fifth bridge positive artifact.

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
        If the Phase 121 artifact JSON file is not found at the expected path.
    """
    project_root = Path(project_root)
    artifact_path = (
        project_root
        / 'cgt_benchmarks'
        / 'results'
        / 'benchmark_X_event_thinned'
        / 'benchmark_x_phase121_fifth_bridge_positive.json'
    )
    if not artifact_path.exists():
        raise FileNotFoundError(
            f"Phase 121 artifact not found: {artifact_path}. "
            "Expected the fifth bridge positive result at "
            "cgt_benchmarks/results/benchmark_X_event_thinned/"
            "benchmark_x_phase121_fifth_bridge_positive.json"
        )
    payload = json.loads(artifact_path.read_text(encoding='utf-8'))
    return nan_to_none(payload)


if __name__ == '__main__':
    project_root = Path(__file__).resolve().parents[3]
    payload = run_phase121_analysis(project_root=project_root)
    print(json.dumps(nan_to_none(payload), indent=2))
