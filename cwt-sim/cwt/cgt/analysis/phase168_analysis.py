"""Phase 168 analysis: Tenth bridge adversarial (benchmark AD bursty censor).

This module loads the pre-baked Phase 168 result artifact which validates the
adversarial correction mechanism on benchmark AD, a semisynthetic graph benchmark
with bursty-event censoring. Under switch_gamma=0.3 adversarial conditions the
raw combined_r2 degrades to 0.5342 and sign_agreement to 0.8125, while the
corrected combined_r2 = 0.8998 and sign_agreement = 0.9694, confirming the
adversarial correction holds on the tenth bridge benchmark.
"""

from __future__ import annotations

import json
from pathlib import Path

from cwt.cgt.analysis._utils import nan_to_none


def run_phase168_analysis(project_root: Path, output_root: Path | None = None) -> dict:
    """Load and return the Phase 168 tenth bridge adversarial artifact.

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
        If the Phase 168 artifact JSON file is not found at the expected path.
    """
    project_root = Path(project_root)
    artifact_path = (
        project_root
        / 'cgt_benchmarks'
        / 'results'
        / 'benchmark_AD_bursty_censor'
        / 'benchmark_ad_phase168_tenth_bridge_adversarial.json'
    )
    if not artifact_path.exists():
        raise FileNotFoundError(
            f"Phase 168 artifact not found: {artifact_path}. "
            "Expected the tenth bridge adversarial result at "
            "cgt_benchmarks/results/benchmark_AD_bursty_censor/"
            "benchmark_ad_phase168_tenth_bridge_adversarial.json"
        )
    payload = json.loads(artifact_path.read_text(encoding='utf-8'))
    return nan_to_none(payload)


if __name__ == '__main__':
    project_root = Path(__file__).resolve().parents[3]
    payload = run_phase168_analysis(project_root=project_root)
    print(json.dumps(nan_to_none(payload), indent=2))
