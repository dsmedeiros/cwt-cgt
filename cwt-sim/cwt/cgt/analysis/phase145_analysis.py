"""Phase 145 analysis: Pooled seven-bridge adversarial summary (benchmark scaffold family).

This module loads the pre-baked Phase 145 result artifact which updates the
pooled bridge-adversarial summary to include all seven bridge benchmarks (T/U/V/W/X/Y/Z).
Pooled seven-bridge adversarial corrected combined R2 = 0.8897, correlation = 0.9513,
sign_agreement = 0.9427, confirming the adversarial correction holds across seven benchmarks.
"""

from __future__ import annotations

import json
from pathlib import Path

from cwt.cgt.analysis._utils import nan_to_none


def run_phase145_analysis(project_root: Path, output_root: Path | None = None) -> dict:
    """Load and return the Phase 145 pooled seven-bridge adversarial artifact.

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
        If the Phase 145 artifact JSON file is not found at the expected path.
    """
    project_root = Path(project_root)
    artifact_path = (
        project_root
        / 'cgt_benchmarks'
        / 'results'
        / 'benchmark_scaffold_family'
        / 'benchmark_scaffold_phase145_pooled_seven_bridge_adversarial.json'
    )
    if not artifact_path.exists():
        raise FileNotFoundError(
            f"Phase 145 artifact not found: {artifact_path}. "
            "Expected the pooled seven-bridge adversarial result at "
            "cgt_benchmarks/results/benchmark_scaffold_family/"
            "benchmark_scaffold_phase145_pooled_seven_bridge_adversarial.json"
        )
    payload = json.loads(artifact_path.read_text(encoding='utf-8'))
    return nan_to_none(payload)


if __name__ == '__main__':
    project_root = Path(__file__).resolve().parents[3]
    payload = run_phase145_analysis(project_root=project_root)
    print(json.dumps(nan_to_none(payload), indent=2))
