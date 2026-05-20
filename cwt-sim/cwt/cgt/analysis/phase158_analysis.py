"""Phase 158 analysis: Bridge family adversarial with AC (benchmark scaffold family).

This module loads the pre-baked Phase 158 result artifact which validates the
pooled eight-bridge predictor rule under adversarial conditions on the full
bridge family including benchmark AC. The adversarial stress-test uses
switch_gamma=0.3; raw combined_r2 degrades to 0.5588 while the corrected
combined_r2 = 0.9047 and corrected sign_agreement = 0.9724, confirming the
correction mechanism holds after extending the bridge family to nine benchmarks.
"""

from __future__ import annotations

import json
from pathlib import Path

from cwt.cgt.analysis._utils import nan_to_none


def run_phase158_analysis(project_root: Path, output_root: Path | None = None) -> dict:
    """Load and return the Phase 158 bridge family adversarial with AC artifact.

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
        If the Phase 158 artifact JSON file is not found at the expected path.
    """
    project_root = Path(project_root)
    artifact_path = (
        project_root
        / 'cgt_benchmarks'
        / 'results'
        / 'benchmark_scaffold_family'
        / 'benchmark_scaffold_phase158_bridge_family_adversarial_with_ac.json'
    )
    if not artifact_path.exists():
        raise FileNotFoundError(
            f"Phase 158 artifact not found: {artifact_path}. "
            "Expected the bridge family adversarial with AC result at "
            "cgt_benchmarks/results/benchmark_scaffold_family/"
            "benchmark_scaffold_phase158_bridge_family_adversarial_with_ac.json"
        )
    payload = json.loads(artifact_path.read_text(encoding='utf-8'))
    return nan_to_none(payload)


if __name__ == '__main__':
    project_root = Path(__file__).resolve().parents[3]
    payload = run_phase158_analysis(project_root=project_root)
    print(json.dumps(nan_to_none(payload), indent=2))
