"""Phase 198 analysis: Thirteenth bridge adversarial tensor v4 (benchmark AG irregular hidden censor).

This module loads the pre-baked Phase 198 result artifact which validates the
bridge tensor geometry law v4 correction on the adversarial transfer over
benchmark AG (irregular hidden-state lag plus asynchronous censoring).
Raw combined R2 = 0.5412; corrected combined R2 = 0.8978;
corrected sign agreement = 0.9722.
"""

from __future__ import annotations

import json
from pathlib import Path

from cwt.cgt.analysis._utils import nan_to_none


def run_phase198_analysis(project_root: Path, output_root: Path | None = None) -> dict:
    """Load and return the Phase 198 thirteenth bridge adversarial tensor v4 artifact.

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
        If the Phase 198 artifact JSON file is not found at the expected path.
    """
    project_root = Path(project_root)
    artifact_path = (
        project_root
        / 'cgt_benchmarks'
        / 'results'
        / 'benchmark_AG_irregular_hidden_censor'
        / 'benchmark_ag_phase198_bridge_adversarial_tensor_v4.json'
    )
    if not artifact_path.exists():
        raise FileNotFoundError(
            f"Phase 198 artifact not found: {artifact_path}. "
            "Expected the thirteenth bridge adversarial tensor v4 result at "
            "cgt_benchmarks/results/benchmark_AG_irregular_hidden_censor/"
            "benchmark_ag_phase198_bridge_adversarial_tensor_v4.json"
        )
    payload = json.loads(artifact_path.read_text(encoding='utf-8'))
    return nan_to_none(payload)


if __name__ == '__main__':
    project_root = Path(__file__).resolve().parents[3]
    payload = run_phase198_analysis(project_root=project_root)
    print(json.dumps(nan_to_none(payload), indent=2))
