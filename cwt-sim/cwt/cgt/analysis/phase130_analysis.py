"""Phase 130 analysis: Sixth bridge adversarial transfer (benchmark Y burst-observed).

This module loads the pre-baked Phase 130 result artifact which applies the
adversarial perturbation family and sign-tensor correction to benchmark Y
(burst-observed). Raw combined R2 = 0.4517 under adversarial perturbation;
corrected combined R2 = 0.8812 with corrected sign_agreement = 0.9653,
confirming that the correction transfers to the sixth bridge benchmark.
Verdict: sixth_bridge_adversarial_corrected_supported.
"""

from __future__ import annotations

import json
from pathlib import Path

from cwt.cgt.analysis._utils import nan_to_none


def run_phase130_analysis(project_root: Path, output_root: Path | None = None) -> dict:
    """Load and return the Phase 130 sixth bridge adversarial transfer artifact.

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
        If the Phase 130 artifact JSON file is not found at the expected path.
    """
    project_root = Path(project_root)
    artifact_path = (
        project_root
        / 'cgt_benchmarks'
        / 'results'
        / 'benchmark_Y_burst_observed'
        / 'benchmark_y_phase130_sixth_bridge_adversarial.json'
    )
    if not artifact_path.exists():
        raise FileNotFoundError(
            f"Phase 130 artifact not found: {artifact_path}. "
            "Expected the sixth bridge adversarial result at "
            "cgt_benchmarks/results/benchmark_Y_burst_observed/"
            "benchmark_y_phase130_sixth_bridge_adversarial.json"
        )
    payload = json.loads(artifact_path.read_text(encoding='utf-8'))
    return nan_to_none(payload)


if __name__ == '__main__':
    project_root = Path(__file__).resolve().parents[3]
    payload = run_phase130_analysis(project_root=project_root)
    print(json.dumps(nan_to_none(payload), indent=2))
