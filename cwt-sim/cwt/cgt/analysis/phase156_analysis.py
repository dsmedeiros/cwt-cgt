"""Phase 156 analysis: Pooled eight-bridge adversarial summary (benchmark scaffold family).

This module loads the pre-baked Phase 156 result artifact which builds the pooled
eight-bridge adversarial summary. Aggregate raw combined R2 = 0.5469 degrades under
adversarial perturbation; corrected combined R2 = 0.9026 and sign agreement = 0.9778
confirm recovery via tensor-law correction, supporting the pooled eight-bridge
adversarial result.
"""

from __future__ import annotations

import json
from pathlib import Path

from cwt.cgt.analysis._utils import nan_to_none


def run_phase156_analysis(project_root: Path, output_root: Path | None = None) -> dict:
    """Load and return the Phase 156 pooled eight-bridge adversarial artifact.

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
        If the Phase 156 artifact JSON file is not found at the expected path.
    """
    project_root = Path(project_root)
    artifact_path = (
        project_root
        / 'cgt_benchmarks'
        / 'results'
        / 'benchmark_scaffold_family'
        / 'benchmark_scaffold_phase156_pooled_eight_bridge_adversarial.json'
    )
    if not artifact_path.exists():
        raise FileNotFoundError(
            f"Phase 156 artifact not found: {artifact_path}. "
            "Expected the pooled eight-bridge adversarial result at "
            "cgt_benchmarks/results/benchmark_scaffold_family/"
            "benchmark_scaffold_phase156_pooled_eight_bridge_adversarial.json"
        )
    payload = json.loads(artifact_path.read_text(encoding='utf-8'))
    return nan_to_none(payload)


if __name__ == '__main__':
    project_root = Path(__file__).resolve().parents[3]
    payload = run_phase156_analysis(project_root=project_root)
    print(json.dumps(nan_to_none(payload), indent=2))
