"""Phase 54 analysis: Adversarial sign-break benchmark on fork-mesh (benchmark L).

This module loads the pre-baked Phase 54 result artifact which tests sign
robustness by applying an adversarial perturbation family to benchmark L
(fork-mesh topology) under the unchanged pooled-five positive noisy scaffold
rule. The adversarial family is designed to expose the sign boundary: the
heldout_adversarial and heldout_combined sign_agreement values are expected
to fall below 0.9 and 0.95 respectively.
"""

from __future__ import annotations

import json
from pathlib import Path

from cwt.cgt.analysis._utils import nan_to_none


def run_phase54_analysis(project_root: Path, output_root: Path | None = None) -> dict:
    """Load and return the Phase 54 adversarial sign-break artifact.

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
        If the Phase 54 artifact JSON file is not found at the expected path.
    """
    project_root = Path(project_root)
    artifact_path = (
        project_root
        / 'cgt_benchmarks'
        / 'results'
        / 'benchmark_L_fork_mesh'
        / 'benchmark_l_phase54_adversarial_sign_break.json'
    )
    if not artifact_path.exists():
        raise FileNotFoundError(
            f"Phase 54 artifact not found: {artifact_path}. "
            "Expected the adversarial sign-break result at "
            "cgt_benchmarks/results/benchmark_L_fork_mesh/"
            "benchmark_l_phase54_adversarial_sign_break.json"
        )
    payload = json.loads(artifact_path.read_text(encoding='utf-8'))
    return nan_to_none(payload)


if __name__ == '__main__':
    project_root = Path(__file__).resolve().parents[3]
    payload = run_phase54_analysis(project_root=project_root)
    print(json.dumps(nan_to_none(payload), indent=2))
