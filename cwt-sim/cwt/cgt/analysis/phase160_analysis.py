"""Phase 160 analysis: Third less-synthetic pilot benchmark (benchmark CC delayed release).

This module loads the pre-baked Phase 160 result artifact which validates the
pooled eight-bridge predictor rule on benchmark CC, a less-synthetic graph benchmark
with state-thinning plus delayed release. Switch-slice held-out combined R2 = 0.8819
and sign_agreement = 1.0, confirming the positive transfer rule holds on a third
distinct less-synthetic benchmark.
"""

from __future__ import annotations

import json
from pathlib import Path

from cwt.cgt.analysis._utils import nan_to_none


def run_phase160_analysis(project_root: Path, output_root: Path | None = None) -> dict:
    """Load and return the Phase 160 third less-synthetic positive artifact.

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
        If the Phase 160 artifact JSON file is not found at the expected path.
    """
    project_root = Path(project_root)
    artifact_path = (
        project_root
        / 'cgt_benchmarks'
        / 'results'
        / 'benchmark_CC_delayed_release'
        / 'benchmark_cc_phase160_third_less_synthetic_positive.json'
    )
    if not artifact_path.exists():
        raise FileNotFoundError(
            f"Phase 160 artifact not found: {artifact_path}. "
            "Expected the third less-synthetic positive result at "
            "cgt_benchmarks/results/benchmark_CC_delayed_release/"
            "benchmark_cc_phase160_third_less_synthetic_positive.json"
        )
    payload = json.loads(artifact_path.read_text(encoding='utf-8'))
    return nan_to_none(payload)


if __name__ == '__main__':
    project_root = Path(__file__).resolve().parents[3]
    payload = run_phase160_analysis(project_root=project_root)
    print(json.dumps(nan_to_none(payload), indent=2))
