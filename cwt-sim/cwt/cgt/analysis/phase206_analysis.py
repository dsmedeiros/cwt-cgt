"""Phase 206 analysis: Bridge boundary refresh v6 (benchmark scaffold family).

This module loads the pre-baked Phase 206 result artifact which encodes the
bridge boundary refresh v6 — updated positive and adversarial corrected
performance bands across all thirteen bridge benchmarks plus seven less-synthetic
pilots. Positive transfer band = [0.8987, 0.9981]; adversarial raw band = [0.4179, 0.6024];
adversarial corrected band = [0.8364, 0.9162]; bridge holdout mean = 0.8871;
weakest bridge benchmark = GG_windowed_sparse_release.
"""

from __future__ import annotations

import json
from pathlib import Path

from cwt.cgt.analysis._utils import nan_to_none


def run_phase206_analysis(project_root: Path, output_root: Path | None = None) -> dict:
    """Load and return the Phase 206 bridge boundary refresh v6 artifact.

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
        If the Phase 206 artifact JSON file is not found at the expected path.
    """
    project_root = Path(project_root)
    artifact_path = (
        project_root
        / 'cgt_benchmarks'
        / 'results'
        / 'benchmark_scaffold_family'
        / 'benchmark_scaffold_phase206_bridge_boundary_refresh_v6.json'
    )
    if not artifact_path.exists():
        raise FileNotFoundError(
            f"Phase 206 artifact not found: {artifact_path}. "
            "Expected the bridge boundary refresh v6 result at "
            "cgt_benchmarks/results/benchmark_scaffold_family/"
            "benchmark_scaffold_phase206_bridge_boundary_refresh_v6.json"
        )
    payload = json.loads(artifact_path.read_text(encoding='utf-8'))
    return nan_to_none(payload)


if __name__ == '__main__':
    project_root = Path(__file__).resolve().parents[3]
    payload = run_phase206_analysis(project_root=project_root)
    print(json.dumps(nan_to_none(payload), indent=2))
