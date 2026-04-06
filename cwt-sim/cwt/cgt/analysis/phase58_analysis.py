"""Phase 58 analysis: Second adversarial family benchmark (benchmark I nonring ladder).

This module loads the pre-baked Phase 58 result artifact which stress-tests the
pooled seven-positive noisy scaffold rule (from Phase 55) against a second
adversarial perturbation family on benchmark I (nonring ladder). The adversarial
family is expected to produce a partial failure: combined_metrics r2 < 0.5 and
adversarial_family_metrics sign_agreement < 0.9.
"""

from __future__ import annotations

import json
from pathlib import Path

from cwt.cgt.analysis._utils import nan_to_none


def run_phase58_analysis(project_root: Path, output_root: Path | None = None) -> dict:
    """Load and return the Phase 58 second adversarial family artifact.

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
        If the Phase 58 artifact JSON file is not found at the expected path.
    """
    project_root = Path(project_root)
    artifact_path = (
        project_root
        / 'cgt_benchmarks'
        / 'results'
        / 'benchmark_I_nonring_ladder'
        / 'benchmark_i_phase58_second_adversarial_family.json'
    )
    if not artifact_path.exists():
        raise FileNotFoundError(
            f"Phase 58 artifact not found: {artifact_path}. "
            "Expected the second adversarial family result at "
            "cgt_benchmarks/results/benchmark_I_nonring_ladder/"
            "benchmark_i_phase58_second_adversarial_family.json"
        )
    payload = json.loads(artifact_path.read_text(encoding='utf-8'))
    return nan_to_none(payload)


if __name__ == '__main__':
    project_root = Path(__file__).resolve().parents[3]
    payload = run_phase58_analysis(project_root=project_root)
    print(json.dumps(nan_to_none(payload), indent=2))
