"""Phase 143 analysis: Less-synthetic bridge adversarial pilot (benchmark AA).

This module loads the pre-baked Phase 143 result artifact which validates the
tensor/compactness correction on benchmark AA under adversarial distortion.
Raw adversarial R2 = 0.3715; corrected R2 = 0.8124 with sign_agreement = 0.9444,
confirming the correction remains effective on less-synthetic conditions.
"""

from __future__ import annotations

import json
from pathlib import Path

from cwt.cgt.analysis._utils import nan_to_none


def run_phase143_analysis(project_root: Path, output_root: Path | None = None) -> dict:
    """Load and return the Phase 143 less-synthetic adversarial artifact.

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
        If the Phase 143 artifact JSON file is not found at the expected path.
    """
    project_root = Path(project_root)
    artifact_path = (
        project_root
        / 'cgt_benchmarks'
        / 'results'
        / 'benchmark_AA_less_synthetic'
        / 'benchmark_aa_phase143_less_synthetic_bridge_adversarial.json'
    )
    if not artifact_path.exists():
        raise FileNotFoundError(
            f"Phase 143 artifact not found: {artifact_path}. "
            "Expected the AA less-synthetic adversarial result at "
            "cgt_benchmarks/results/benchmark_AA_less_synthetic/"
            "benchmark_aa_phase143_less_synthetic_bridge_adversarial.json"
        )
    payload = json.loads(artifact_path.read_text(encoding='utf-8'))
    return nan_to_none(payload)


if __name__ == '__main__':
    project_root = Path(__file__).resolve().parents[3]
    payload = run_phase143_analysis(project_root=project_root)
    print(json.dumps(nan_to_none(payload), indent=2))
