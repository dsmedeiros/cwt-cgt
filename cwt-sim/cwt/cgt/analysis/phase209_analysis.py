"""Phase 209 analysis: Eighth less-synthetic positive (benchmark HH event gap release).

This module loads the pre-baked Phase 209 result artifact which validates the
pooled thirteen-bridge predictor rule on benchmark HH, a semisynthetic graph
benchmark with event-gap release and delayed partial snapshots. Held-out
R2 = 0.9018, corr = 0.9739, sign = 0.9875, confirming positive transfer to
the eighth less-synthetic benchmark.
"""

from __future__ import annotations

import json
from pathlib import Path

from cwt.cgt.analysis._utils import nan_to_none


def run_phase209_analysis(project_root: Path, output_root: Path | None = None) -> dict:
    """Load and return the Phase 209 eighth less-synthetic positive artifact.

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
        If the Phase 209 artifact JSON file is not found at the expected path.
    """
    project_root = Path(project_root)
    artifact_path = (
        project_root
        / 'cgt_benchmarks'
        / 'results'
        / 'benchmark_HH_event_gap_release'
        / 'benchmark_hh_phase209_eighth_less_synthetic_positive.json'
    )
    if not artifact_path.exists():
        raise FileNotFoundError(
            f"Phase 209 artifact not found: {artifact_path}. "
            "Expected the eighth less-synthetic positive result at "
            "cgt_benchmarks/results/benchmark_HH_event_gap_release/"
            "benchmark_hh_phase209_eighth_less_synthetic_positive.json"
        )
    payload = json.loads(artifact_path.read_text(encoding='utf-8'))
    return nan_to_none(payload)


if __name__ == '__main__':
    project_root = Path(__file__).resolve().parents[3]
    payload = run_phase209_analysis(project_root=project_root)
    print(json.dumps(nan_to_none(payload), indent=2))
