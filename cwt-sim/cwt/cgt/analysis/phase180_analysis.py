"""Phase 180 analysis: Pooled eleven-bridge adversarial summary (benchmark scaffold family).

This module loads the pre-baked Phase 180 result artifact which encodes the
pooled eleven-bridge adversarial summary. Raw combined R2 = 0.5561 and
sign_agreement = 0.8694 (adversarial degrades); corrected combined R2 = 0.9128
and corrected sign_agreement = 0.9728 via bridge_tensor_geometry_law_v2,
confirming the correction stack holds under the pooled-eleven adversarial regime
with benchmark_count = 11.
"""

from __future__ import annotations

import json
from pathlib import Path

from cwt.cgt.analysis._utils import nan_to_none


def run_phase180_analysis(project_root: Path, output_root: Path | None = None) -> dict:
    """Load and return the Phase 180 pooled eleven-bridge adversarial artifact.

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
        If the Phase 180 artifact JSON file is not found at the expected path.
    """
    project_root = Path(project_root)
    artifact_path = (
        project_root
        / 'cgt_benchmarks'
        / 'results'
        / 'benchmark_scaffold_family'
        / 'benchmark_scaffold_phase180_pooled_eleven_bridge_adversarial.json'
    )
    if not artifact_path.exists():
        raise FileNotFoundError(
            f"Phase 180 artifact not found: {artifact_path}. "
            "Expected the pooled eleven-bridge adversarial result at "
            "cgt_benchmarks/results/benchmark_scaffold_family/"
            "benchmark_scaffold_phase180_pooled_eleven_bridge_adversarial.json"
        )
    payload = json.loads(artifact_path.read_text(encoding='utf-8'))
    return nan_to_none(payload)


if __name__ == '__main__':
    project_root = Path(__file__).resolve().parents[3]
    payload = run_phase180_analysis(project_root=project_root)
    print(json.dumps(nan_to_none(payload), indent=2))
