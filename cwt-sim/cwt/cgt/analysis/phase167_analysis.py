"""Phase 167 analysis: Tenth bridge positive benchmark (benchmark AD bursty censor).

This module loads the pre-baked Phase 167 result artifact which validates the
pooled nine-bridge predictor rule on benchmark AD, a semisynthetic graph benchmark
with hidden-dropout plus bursty censor windows. Switch-slice held-out combined
R2 = 0.9226 and sign_agreement = 1.0, confirming the positive transfer rule holds
across ten distinct bridge benchmarks.
"""

from __future__ import annotations

import json
from pathlib import Path

from cwt.cgt.analysis._utils import nan_to_none


def run_phase167_analysis(project_root: Path, output_root: Path | None = None) -> dict:
    """Load and return the Phase 167 tenth bridge positive artifact.

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
        If the Phase 167 artifact JSON file is not found at the expected path.
    """
    project_root = Path(project_root)
    artifact_path = (
        project_root
        / 'cgt_benchmarks'
        / 'results'
        / 'benchmark_AD_bursty_censor'
        / 'benchmark_ad_phase167_tenth_bridge_positive.json'
    )
    if not artifact_path.exists():
        raise FileNotFoundError(
            f"Phase 167 artifact not found: {artifact_path}. "
            "Expected the tenth bridge positive result at "
            "cgt_benchmarks/results/benchmark_AD_bursty_censor/"
            "benchmark_ad_phase167_tenth_bridge_positive.json"
        )
    payload = json.loads(artifact_path.read_text(encoding='utf-8'))
    return nan_to_none(payload)


if __name__ == '__main__':
    project_root = Path(__file__).resolve().parents[3]
    payload = run_phase167_analysis(project_root=project_root)
    print(json.dumps(nan_to_none(payload), indent=2))
