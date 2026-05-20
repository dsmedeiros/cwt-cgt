"""Phase 147 analysis: Eighth bridge positive benchmark (benchmark AB thinned-window).

This module loads the pre-baked Phase 147 result artifact which validates the
pooled seven-bridge predictor rule on benchmark AB, a semisynthetic graph benchmark
with state-thinning plus event-window censoring. The eighth bridge benchmark adds a
new thinned-window observation-motif stress test; switch-slice held-out combined
R2 = 0.9176 and sign_agreement = 1.0, confirming the positive transfer rule holds
across eight distinct bridge benchmarks.
"""

from __future__ import annotations

import json
from pathlib import Path

from cwt.cgt.analysis._utils import nan_to_none


def run_phase147_analysis(project_root: Path, output_root: Path | None = None) -> dict:
    """Load and return the Phase 147 eighth bridge positive artifact.

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
        If the Phase 147 artifact JSON file is not found at the expected path.
    """
    project_root = Path(project_root)
    artifact_path = (
        project_root
        / 'cgt_benchmarks'
        / 'results'
        / 'benchmark_AB_thinned_window'
        / 'benchmark_ab_phase147_eighth_bridge_positive.json'
    )
    if not artifact_path.exists():
        raise FileNotFoundError(
            f"Phase 147 artifact not found: {artifact_path}. "
            "Expected the eighth bridge positive result at "
            "cgt_benchmarks/results/benchmark_AB_thinned_window/"
            "benchmark_ab_phase147_eighth_bridge_positive.json"
        )
    payload = json.loads(artifact_path.read_text(encoding='utf-8'))
    return nan_to_none(payload)


if __name__ == '__main__':
    project_root = Path(__file__).resolve().parents[3]
    payload = run_phase147_analysis(project_root=project_root)
    print(json.dumps(nan_to_none(payload), indent=2))
