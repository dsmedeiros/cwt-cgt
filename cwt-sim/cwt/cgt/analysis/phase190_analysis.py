"""Phase 190 analysis: Sixth less-synthetic adversarial (benchmark FF mixed release delay).

This module loads the pre-baked Phase 190 result artifact which validates the
bridge tensor geometry law v3 correction on benchmark FF under adversarial
conditions. Raw combined_r2 = 0.4214; corrected combined_r2 = 0.8317;
corrected sign_agreement = 0.9342, confirming the v3 correction holds on the
sixth less-synthetic benchmark.
"""

from __future__ import annotations

import json
from pathlib import Path

from cwt.cgt.analysis._utils import nan_to_none


def run_phase190_analysis(project_root: Path, output_root: Path | None = None) -> dict:
    """Load and return the Phase 190 sixth less-synthetic adversarial artifact.

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
        If the Phase 190 artifact JSON file is not found at the expected path.
    """
    project_root = Path(project_root)
    artifact_path = (
        project_root
        / 'cgt_benchmarks'
        / 'results'
        / 'benchmark_FF_mixed_release_delay'
        / 'benchmark_ff_phase190_sixth_less_synthetic_adversarial.json'
    )
    if not artifact_path.exists():
        raise FileNotFoundError(
            f"Phase 190 artifact not found: {artifact_path}. "
            "Expected the sixth less-synthetic adversarial result at "
            "cgt_benchmarks/results/benchmark_FF_mixed_release_delay/"
            "benchmark_ff_phase190_sixth_less_synthetic_adversarial.json"
        )
    payload = json.loads(artifact_path.read_text(encoding='utf-8'))
    return nan_to_none(payload)


if __name__ == '__main__':
    project_root = Path(__file__).resolve().parents[3]
    payload = run_phase190_analysis(project_root=project_root)
    print(json.dumps(nan_to_none(payload), indent=2))
