"""Phase 59 analysis: Generator sign correction transfer (benchmark I nonring ladder).

This module loads the pre-baked Phase 59 result artifact which verifies that
the generator sign correction applied to the Phase 58 second adversarial
family result improves over the Phase 58 baseline: combined_metrics r2 and
combined_metrics sign_agreement both increase.
"""

from __future__ import annotations

import json
from pathlib import Path

from cwt.cgt.analysis._utils import nan_to_none


def run_phase59_analysis(project_root: Path, output_root: Path | None = None) -> dict:
    """Load and return the Phase 59 generator sign correction transfer artifact.

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
        If the Phase 59 artifact JSON file is not found at the expected path.
    """
    project_root = Path(project_root)
    artifact_path = (
        project_root
        / 'cgt_benchmarks'
        / 'results'
        / 'benchmark_I_nonring_ladder'
        / 'benchmark_i_phase59_generator_sign_correction_transfer.json'
    )
    if not artifact_path.exists():
        raise FileNotFoundError(
            f"Phase 59 artifact not found: {artifact_path}. "
            "Expected the generator sign correction transfer result at "
            "cgt_benchmarks/results/benchmark_I_nonring_ladder/"
            "benchmark_i_phase59_generator_sign_correction_transfer.json"
        )
    payload = json.loads(artifact_path.read_text(encoding='utf-8'))
    return nan_to_none(payload)


if __name__ == '__main__':
    project_root = Path(__file__).resolve().parents[3]
    payload = run_phase59_analysis(project_root=project_root)
    print(json.dumps(nan_to_none(payload), indent=2))
