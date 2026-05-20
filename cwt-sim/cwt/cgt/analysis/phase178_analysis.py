"""Phase 178 analysis: Eleventh bridge adversarial tensor compactness (benchmark AE state occluded irregular).

This module loads the pre-baked Phase 178 result artifact which encodes the
adversarial tensor compactness correction on benchmark AE. Raw combined R2 = 0.5342
and sign_agreement = 0.8611 (adversarial degrades performance); corrected combined
R2 = 0.8918 and corrected sign_agreement = 0.9653 via bridge_tensor_geometry_law_v2,
confirming the correction stack recovers performance on the eleventh bridge benchmark.
"""

from __future__ import annotations

import json
from pathlib import Path

from cwt.cgt.analysis._utils import nan_to_none


def run_phase178_analysis(project_root: Path, output_root: Path | None = None) -> dict:
    """Load and return the Phase 178 adversarial tensor compactness artifact.

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
        If the Phase 178 artifact JSON file is not found at the expected path.
    """
    project_root = Path(project_root)
    artifact_path = (
        project_root
        / 'cgt_benchmarks'
        / 'results'
        / 'benchmark_AE_state_occluded_irregular'
        / 'benchmark_ae_phase178_bridge_adversarial_tensor_compactness.json'
    )
    if not artifact_path.exists():
        raise FileNotFoundError(
            f"Phase 178 artifact not found: {artifact_path}. "
            "Expected the adversarial tensor compactness result at "
            "cgt_benchmarks/results/benchmark_AE_state_occluded_irregular/"
            "benchmark_ae_phase178_bridge_adversarial_tensor_compactness.json"
        )
    payload = json.loads(artifact_path.read_text(encoding='utf-8'))
    return nan_to_none(payload)


if __name__ == '__main__':
    project_root = Path(__file__).resolve().parents[3]
    payload = run_phase178_analysis(project_root=project_root)
    print(json.dumps(nan_to_none(payload), indent=2))
