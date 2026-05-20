"""Phase 189 analysis: Sixth less-synthetic positive (benchmark FF mixed release delay).

This module loads the pre-baked Phase 189 result artifact which validates the
pooled eleven-bridge predictor rule on benchmark FF, a semisynthetic graph
benchmark with mixed release windows and delayed event thinning. The sixth
less-synthetic benchmark; switch-slice held-out R2 = 0.8942 and sign = 1.0,
confirming the positive transfer rule holds on this observation motif.
"""

from __future__ import annotations

import json
from pathlib import Path

from cwt.cgt.analysis._utils import nan_to_none


def run_phase189_analysis(project_root: Path, output_root: Path | None = None) -> dict:
    """Load and return the Phase 189 sixth less-synthetic positive artifact.

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
        If the Phase 189 artifact JSON file is not found at the expected path.
    """
    project_root = Path(project_root)
    artifact_path = (
        project_root
        / 'cgt_benchmarks'
        / 'results'
        / 'benchmark_FF_mixed_release_delay'
        / 'benchmark_ff_phase189_sixth_less_synthetic_positive.json'
    )
    if not artifact_path.exists():
        raise FileNotFoundError(
            f"Phase 189 artifact not found: {artifact_path}. "
            "Expected the sixth less-synthetic positive result at "
            "cgt_benchmarks/results/benchmark_FF_mixed_release_delay/"
            "benchmark_ff_phase189_sixth_less_synthetic_positive.json"
        )
    payload = json.loads(artifact_path.read_text(encoding='utf-8'))
    return nan_to_none(payload)


if __name__ == '__main__':
    project_root = Path(__file__).resolve().parents[3]
    payload = run_phase189_analysis(project_root=project_root)
    print(json.dumps(nan_to_none(payload), indent=2))
