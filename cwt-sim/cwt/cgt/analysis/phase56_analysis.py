"""Phase 56 analysis: Pooled seven-adversarial boundary probe (benchmark L).

This module loads the pre-baked Phase 56 result artifact which stress-tests
benchmark L (fork-mesh) with a pooled seven-adversarial perturbation family.
The adversarial family is expected to produce a partial failure: combined_r2 < 0.5
and combined_sign_agreement < 0.95, exposing the generator sign boundary.
"""

from __future__ import annotations

import json
from pathlib import Path

from cwt.cgt.analysis._utils import nan_to_none


def run_phase56_analysis(project_root: Path, output_root: Path | None = None) -> dict:
    """Load and return the Phase 56 pooled seven-adversarial boundary artifact.

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
        If the Phase 56 artifact JSON file is not found at the expected path.
    """
    project_root = Path(project_root)
    artifact_path = (
        project_root
        / 'cgt_benchmarks'
        / 'results'
        / 'benchmark_L_fork_mesh'
        / 'benchmark_l_phase56_pooled_seven_adversarial.json'
    )
    if not artifact_path.exists():
        raise FileNotFoundError(
            f"Phase 56 artifact not found: {artifact_path}. "
            "Expected the pooled seven-adversarial boundary result at "
            "cgt_benchmarks/results/benchmark_L_fork_mesh/"
            "benchmark_l_phase56_pooled_seven_adversarial.json"
        )
    payload = json.loads(artifact_path.read_text(encoding='utf-8'))
    return nan_to_none(payload)


if __name__ == '__main__':
    project_root = Path(__file__).resolve().parents[3]
    payload = run_phase56_analysis(project_root=project_root)
    print(json.dumps(nan_to_none(payload), indent=2))
