"""Phase 165 analysis: Pooled nine-bridge adversarial summary (benchmark scaffold family).

This module loads the pre-baked Phase 165 result artifact which validates the
pooled nine-bridge predictor rule under adversarial conditions across five
adversarial benchmarks (V, W, Z, AB, AC). Under switch_gamma=0.3 adversarial
conditions the raw combined_r2 = 0.5631 while the corrected combined_r2 = 0.9079
and corrected sign_agreement = 0.9738, confirming the adversarial correction
mechanism generalizes across the full nine-bridge family.
"""

from __future__ import annotations

import json
from pathlib import Path

from cwt.cgt.analysis._utils import nan_to_none


def run_phase165_analysis(project_root: Path, output_root: Path | None = None) -> dict:
    """Load and return the Phase 165 pooled nine-bridge adversarial artifact.

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
        If the Phase 165 artifact JSON file is not found at the expected path.
    """
    project_root = Path(project_root)
    artifact_path = (
        project_root
        / 'cgt_benchmarks'
        / 'results'
        / 'benchmark_scaffold_family'
        / 'benchmark_scaffold_phase165_pooled_nine_bridge_adversarial.json'
    )
    if not artifact_path.exists():
        raise FileNotFoundError(
            f"Phase 165 artifact not found: {artifact_path}. "
            "Expected the pooled nine-bridge adversarial result at "
            "cgt_benchmarks/results/benchmark_scaffold_family/"
            "benchmark_scaffold_phase165_pooled_nine_bridge_adversarial.json"
        )
    payload = json.loads(artifact_path.read_text(encoding='utf-8'))
    return nan_to_none(payload)


if __name__ == '__main__':
    project_root = Path(__file__).resolve().parents[3]
    payload = run_phase165_analysis(project_root=project_root)
    print(json.dumps(nan_to_none(payload), indent=2))
