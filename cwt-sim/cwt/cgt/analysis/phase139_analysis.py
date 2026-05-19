"""Phase 139 analysis: Bridge family adversarial summary (benchmark scaffold family).

This module loads the pre-baked Phase 139 result artifact which summarizes
adversarial transfer results grouped by bridge observation family across all
seven bridge benchmarks (T/U/V/W/X/Y/Z). Aggregate corrected R2 = 0.8928 and
sign_agreement = 0.9208, confirming family-grouped correction is supportive.
"""

from __future__ import annotations

import json
from pathlib import Path

from cwt.cgt.analysis._utils import nan_to_none


def run_phase139_analysis(project_root: Path, output_root: Path | None = None) -> dict:
    """Load and return the Phase 139 family adversarial summary artifact.

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
        If the Phase 139 artifact JSON file is not found at the expected path.
    """
    project_root = Path(project_root)
    artifact_path = (
        project_root
        / 'cgt_benchmarks'
        / 'results'
        / 'benchmark_scaffold_family'
        / 'benchmark_scaffold_phase139_bridge_family_adversarial_summary.json'
    )
    if not artifact_path.exists():
        raise FileNotFoundError(
            f"Phase 139 artifact not found: {artifact_path}. "
            "Expected the family adversarial summary at "
            "cgt_benchmarks/results/benchmark_scaffold_family/"
            "benchmark_scaffold_phase139_bridge_family_adversarial_summary.json"
        )
    payload = json.loads(artifact_path.read_text(encoding='utf-8'))
    return nan_to_none(payload)


if __name__ == '__main__':
    project_root = Path(__file__).resolve().parents[3]
    payload = run_phase139_analysis(project_root=project_root)
    print(json.dumps(nan_to_none(payload), indent=2))
