"""Phase 52 analysis: Extreme perturbation family stress test (Benchmark K hub-weave).

This module loads the pre-baked Phase 52 result artifact which stress-tests the
pooled scaffold rule on benchmark K (hub-weave) using an extreme perturbation
shape family, probing the limits of scaffold generalization.
"""

from __future__ import annotations

import json
from pathlib import Path

from cwt.cgt.analysis._utils import nan_to_none


def run_phase52_analysis(project_root: Path, output_root: Path | None = None) -> dict:
    """Load and return the Phase 52 extreme perturbation family artifact.

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
        If the Phase 52 artifact JSON file is not found at the expected path.
    """
    project_root = Path(project_root)
    artifact_path = (
        project_root
        / 'cgt_benchmarks'
        / 'results'
        / 'benchmark_K_hub_weave'
        / 'benchmark_k_phase52_extreme_perturbation_family.json'
    )
    if not artifact_path.exists():
        raise FileNotFoundError(
            f"Phase 52 artifact not found: {artifact_path}. "
            "Expected the extreme perturbation family result at "
            "cgt_benchmarks/results/benchmark_K_hub_weave/"
            "benchmark_k_phase52_extreme_perturbation_family.json"
        )
    payload = json.loads(artifact_path.read_text(encoding='utf-8'))
    return nan_to_none(payload)


if __name__ == '__main__':
    project_root = Path(__file__).resolve().parents[3]
    payload = run_phase52_analysis(project_root=project_root)
    print(json.dumps(nan_to_none(payload), indent=2))
