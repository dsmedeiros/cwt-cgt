"""Phase 149 analysis: Eighth bridge adversarial on benchmark AB (thinned-window).

This module loads the pre-baked Phase 149 result artifact which applies the
tensor-compactness bridge correction to benchmark AB under adversarial conditions.
Raw combined R2 = 0.5224 degrades under adversarial perturbation; corrected
combined R2 = 0.8871 and sign agreement = 0.9722 confirm recovery, supporting
the eighth bridge adversarial corrected result.
"""

from __future__ import annotations

import json
from pathlib import Path

from cwt.cgt.analysis._utils import nan_to_none


def run_phase149_analysis(project_root: Path, output_root: Path | None = None) -> dict:
    """Load and return the Phase 149 eighth bridge adversarial artifact.

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
        If the Phase 149 artifact JSON file is not found at the expected path.
    """
    project_root = Path(project_root)
    artifact_path = (
        project_root
        / 'cgt_benchmarks'
        / 'results'
        / 'benchmark_AB_thinned_window'
        / 'benchmark_ab_phase149_bridge_adversarial_tensor_compactness.json'
    )
    if not artifact_path.exists():
        raise FileNotFoundError(
            f"Phase 149 artifact not found: {artifact_path}. "
            "Expected the eighth bridge adversarial tensor-compactness result at "
            "cgt_benchmarks/results/benchmark_AB_thinned_window/"
            "benchmark_ab_phase149_bridge_adversarial_tensor_compactness.json"
        )
    payload = json.loads(artifact_path.read_text(encoding='utf-8'))
    return nan_to_none(payload)


if __name__ == '__main__':
    project_root = Path(__file__).resolve().parents[3]
    payload = run_phase149_analysis(project_root=project_root)
    print(json.dumps(nan_to_none(payload), indent=2))
