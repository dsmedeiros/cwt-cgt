"""Phase 214 analysis: Pooled thirteen-bridge adversarial v6 (benchmark scaffold family).

This module loads the pre-baked Phase 214 result artifact which validates the
bridge tensor geometry law v6 correction on the pooled thirteen-bridge adversarial
suite. Raw combined_r2 = 0.5611; corrected combined_r2 = 0.9194;
corrected sign_agreement = 0.9760; benchmark_count = 13.
"""

from __future__ import annotations

import json
from pathlib import Path

from cwt.cgt.analysis._utils import nan_to_none


def run_phase214_analysis(project_root: Path, output_root: Path | None = None) -> dict:
    """Load and return the Phase 214 pooled thirteen-bridge adversarial v6 artifact.

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
        If the Phase 214 artifact JSON file is not found at the expected path.
    """
    project_root = Path(project_root)
    artifact_path = (
        project_root
        / 'cgt_benchmarks'
        / 'results'
        / 'benchmark_scaffold_family'
        / 'benchmark_scaffold_phase214_pooled_thirteen_bridge_adversarial_v6.json'
    )
    if not artifact_path.exists():
        raise FileNotFoundError(
            f"Phase 214 artifact not found: {artifact_path}. "
            "Expected the pooled thirteen-bridge adversarial v6 result at "
            "cgt_benchmarks/results/benchmark_scaffold_family/"
            "benchmark_scaffold_phase214_pooled_thirteen_bridge_adversarial_v6.json"
        )
    payload = json.loads(artifact_path.read_text(encoding='utf-8'))
    return nan_to_none(payload)


if __name__ == '__main__':
    project_root = Path(__file__).resolve().parents[3]
    payload = run_phase214_analysis(project_root=project_root)
    print(json.dumps(nan_to_none(payload), indent=2))
