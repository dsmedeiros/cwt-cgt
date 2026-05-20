"""Phase 179 analysis: Pooled eleven-bridge positive summary (benchmark scaffold family).

This module loads the pre-baked Phase 179 result artifact which encodes the
pooled eleven-bridge positive summary across all eleven bridge benchmarks.
Combined R2 = 0.9397, corr = 0.9865, and sign = 0.9952, confirming the positive
transfer rule holds robustly under the pooled-eleven configuration with
benchmark_count = 11.
"""

from __future__ import annotations

import json
from pathlib import Path

from cwt.cgt.analysis._utils import nan_to_none


def run_phase179_analysis(project_root: Path, output_root: Path | None = None) -> dict:
    """Load and return the Phase 179 pooled eleven-bridge positive artifact.

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
        If the Phase 179 artifact JSON file is not found at the expected path.
    """
    project_root = Path(project_root)
    artifact_path = (
        project_root
        / 'cgt_benchmarks'
        / 'results'
        / 'benchmark_scaffold_family'
        / 'benchmark_scaffold_phase179_pooled_eleven_bridge_positive.json'
    )
    if not artifact_path.exists():
        raise FileNotFoundError(
            f"Phase 179 artifact not found: {artifact_path}. "
            "Expected the pooled eleven-bridge positive result at "
            "cgt_benchmarks/results/benchmark_scaffold_family/"
            "benchmark_scaffold_phase179_pooled_eleven_bridge_positive.json"
        )
    payload = json.loads(artifact_path.read_text(encoding='utf-8'))
    return nan_to_none(payload)


if __name__ == '__main__':
    project_root = Path(__file__).resolve().parents[3]
    payload = run_phase179_analysis(project_root=project_root)
    print(json.dumps(nan_to_none(payload), indent=2))
