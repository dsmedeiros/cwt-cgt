"""Phase 195 analysis: Pooled twelve-bridge adversarial (benchmark scaffold family).

This module loads the pre-baked Phase 195 result artifact which records the
pooled twelve-bridge adversarial result with bridge tensor geometry law v4
correction. Raw combined_r2 = 0.5584; corrected combined_r2 = 0.9146;
corrected sign_agreement = 0.9739; benchmark_count = 12. Confirms the v4
correction holds across the expanded twelve-bridge scaffold under adversarial
conditions.
"""

from __future__ import annotations

import json
from pathlib import Path

from cwt.cgt.analysis._utils import nan_to_none


def run_phase195_analysis(project_root: Path, output_root: Path | None = None) -> dict:
    """Load and return the Phase 195 pooled twelve-bridge adversarial artifact.

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
        If the Phase 195 artifact JSON file is not found at the expected path.
    """
    project_root = Path(project_root)
    artifact_path = (
        project_root
        / 'cgt_benchmarks'
        / 'results'
        / 'benchmark_scaffold_family'
        / 'benchmark_scaffold_phase195_pooled_twelve_bridge_adversarial.json'
    )
    if not artifact_path.exists():
        raise FileNotFoundError(
            f"Phase 195 artifact not found: {artifact_path}. "
            "Expected the pooled twelve-bridge adversarial result at "
            "cgt_benchmarks/results/benchmark_scaffold_family/"
            "benchmark_scaffold_phase195_pooled_twelve_bridge_adversarial.json"
        )
    payload = json.loads(artifact_path.read_text(encoding='utf-8'))
    return nan_to_none(payload)


if __name__ == '__main__':
    project_root = Path(__file__).resolve().parents[3]
    payload = run_phase195_analysis(project_root=project_root)
    print(json.dumps(nan_to_none(payload), indent=2))
