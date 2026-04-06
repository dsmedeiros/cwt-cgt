"""Phase 53 analysis: Seventh positive noisy scaffold benchmark (fork-mesh).

This module loads the pre-baked Phase 53 result artifact which validates the
seventh structurally different positive noisy scaffold benchmark (benchmark L,
fork-mesh topology) under the unchanged pooled-five positive noisy scaffold rule.
"""

from __future__ import annotations

import json
from pathlib import Path

from cwt.cgt.analysis._utils import nan_to_none


def run_phase53_analysis(project_root: Path, output_root: Path | None = None) -> dict:
    """Load and return the Phase 53 seventh positive noisy scaffold artifact.

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
        If the Phase 53 artifact JSON file is not found at the expected path.
    """
    project_root = Path(project_root)
    artifact_path = (
        project_root
        / 'cgt_benchmarks'
        / 'results'
        / 'benchmark_L_fork_mesh'
        / 'benchmark_l_phase53_seventh_positive_noisy.json'
    )
    if not artifact_path.exists():
        raise FileNotFoundError(
            f"Phase 53 artifact not found: {artifact_path}. "
            "Expected the seventh positive noisy scaffold result at "
            "cgt_benchmarks/results/benchmark_L_fork_mesh/"
            "benchmark_l_phase53_seventh_positive_noisy.json"
        )
    payload = json.loads(artifact_path.read_text(encoding='utf-8'))
    return nan_to_none(payload)


if __name__ == '__main__':
    project_root = Path(__file__).resolve().parents[3]
    payload = run_phase53_analysis(project_root=project_root)
    print(json.dumps(nan_to_none(payload), indent=2))
