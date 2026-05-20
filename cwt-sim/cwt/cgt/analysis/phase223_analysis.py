"""Phase 223 analysis: Pooled thirteen-bridge adversarial v7 (benchmark scaffold family).

This module loads the pre-baked Phase 223 result artifact which reruns the
pooled-thirteen bridge adversarial summary under bridge tensor geometry law v7.
Switch gamma = 0.30.
Raw combined R2 = 0.5611; corrected combined R2 = 0.9212;
corrected sign agreement = 0.9772.
"""

from __future__ import annotations

import json
from pathlib import Path

from cwt.cgt.analysis._utils import nan_to_none


def run_phase223_analysis(project_root: Path, output_root: Path | None = None) -> dict:
    """Load and return the Phase 223 pooled thirteen-bridge adversarial v7 artifact.

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
        If the Phase 223 artifact JSON file is not found at the expected path.
    """
    project_root = Path(project_root)
    artifact_path = (
        project_root
        / 'cgt_benchmarks'
        / 'results'
        / 'benchmark_scaffold_family'
        / 'benchmark_scaffold_phase223_pooled_thirteen_bridge_adversarial_v7.json'
    )
    if not artifact_path.exists():
        raise FileNotFoundError(
            f"Phase 223 artifact not found: {artifact_path}. "
            "Expected the pooled thirteen-bridge adversarial v7 result at "
            "cgt_benchmarks/results/benchmark_scaffold_family/"
            "benchmark_scaffold_phase223_pooled_thirteen_bridge_adversarial_v7.json"
        )
    payload = json.loads(artifact_path.read_text(encoding='utf-8'))
    return nan_to_none(payload)


if __name__ == '__main__':
    project_root = Path(__file__).resolve().parents[3]
    payload = run_phase223_analysis(project_root=project_root)
    print(json.dumps(nan_to_none(payload), indent=2))
