"""Phase 172 analysis: Fourth less-synthetic adversarial (benchmark DD async masked).

This module loads the pre-baked Phase 172 result artifact which validates the
adversarial correction mechanism on benchmark DD, a less-synthetic graph benchmark
with asynchronous state masking. Under switch_gamma=0.3 adversarial conditions the
raw combined_r2 degrades to 0.4308, while the corrected combined_r2 = 0.8297 and
sign_agreement = 0.9604, confirming the correction holds on the fourth
less-synthetic adversarial benchmark.
"""

from __future__ import annotations

import json
from pathlib import Path

from cwt.cgt.analysis._utils import nan_to_none


def run_phase172_analysis(project_root: Path, output_root: Path | None = None) -> dict:
    """Load and return the Phase 172 fourth less-synthetic adversarial artifact.

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
        If the Phase 172 artifact JSON file is not found at the expected path.
    """
    project_root = Path(project_root)
    artifact_path = (
        project_root
        / 'cgt_benchmarks'
        / 'results'
        / 'benchmark_DD_async_masked'
        / 'benchmark_dd_phase172_fourth_less_synthetic_adversarial.json'
    )
    if not artifact_path.exists():
        raise FileNotFoundError(
            f"Phase 172 artifact not found: {artifact_path}. "
            "Expected the fourth less-synthetic adversarial result at "
            "cgt_benchmarks/results/benchmark_DD_async_masked/"
            "benchmark_dd_phase172_fourth_less_synthetic_adversarial.json"
        )
    payload = json.loads(artifact_path.read_text(encoding='utf-8'))
    return nan_to_none(payload)


if __name__ == '__main__':
    project_root = Path(__file__).resolve().parents[3]
    payload = run_phase172_analysis(project_root=project_root)
    print(json.dumps(nan_to_none(payload), indent=2))
