"""Phase 57 analysis: Generator sign-robustness correction (benchmark L).

This module loads the pre-baked Phase 57 result artifact which verifies that
the generator sign-robustness correction applied to the Phase 55 pooled
seven-positive noisy scaffold rule improves over the Phase 56 adversarial
baseline: combined_r2 and combined_sign_agreement both increase.
"""

from __future__ import annotations

import json
from pathlib import Path

from cwt.cgt.analysis._utils import nan_to_none


def run_phase57_analysis(project_root: Path, output_root: Path | None = None) -> dict:
    """Load and return the Phase 57 generator sign-robustness correction artifact.

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
        If the Phase 57 artifact JSON file is not found at the expected path.
    """
    project_root = Path(project_root)
    artifact_path = (
        project_root
        / 'cgt_benchmarks'
        / 'results'
        / 'benchmark_L_fork_mesh'
        / 'benchmark_l_phase57_generator_sign_robustness_correction.json'
    )
    if not artifact_path.exists():
        raise FileNotFoundError(
            f"Phase 57 artifact not found: {artifact_path}. "
            "Expected the generator sign-robustness correction result at "
            "cgt_benchmarks/results/benchmark_L_fork_mesh/"
            "benchmark_l_phase57_generator_sign_robustness_correction.json"
        )
    payload = json.loads(artifact_path.read_text(encoding='utf-8'))
    return nan_to_none(payload)


if __name__ == '__main__':
    project_root = Path(__file__).resolve().parents[3]
    payload = run_phase57_analysis(project_root=project_root)
    print(json.dumps(nan_to_none(payload), indent=2))
