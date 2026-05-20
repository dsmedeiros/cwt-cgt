"""Phase 211 analysis: Bridge externalization audit with HH (benchmark scaffold family).

This module loads the pre-baked Phase 211 result artifact which extends the
bridge externalization audit to include benchmark HH. Pilot count = 8,
bridge count = 13. Positive mean R2 = 0.8896; adversarial mean R2 = 0.8478.
Weakest pilot: GG_windowed_sparse_release; weakest bridge: BB_sensor_gap.
"""

from __future__ import annotations

import json
from pathlib import Path

from cwt.cgt.analysis._utils import nan_to_none


def run_phase211_analysis(project_root: Path, output_root: Path | None = None) -> dict:
    """Load and return the Phase 211 bridge externalization audit with HH artifact.

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
        If the Phase 211 artifact JSON file is not found at the expected path.
    """
    project_root = Path(project_root)
    artifact_path = (
        project_root
        / 'cgt_benchmarks'
        / 'results'
        / 'benchmark_scaffold_family'
        / 'benchmark_scaffold_phase211_bridge_externalization_audit_with_hh.json'
    )
    if not artifact_path.exists():
        raise FileNotFoundError(
            f"Phase 211 artifact not found: {artifact_path}. "
            "Expected the bridge externalization audit with HH result at "
            "cgt_benchmarks/results/benchmark_scaffold_family/"
            "benchmark_scaffold_phase211_bridge_externalization_audit_with_hh.json"
        )
    payload = json.loads(artifact_path.read_text(encoding='utf-8'))
    return nan_to_none(payload)


if __name__ == '__main__':
    project_root = Path(__file__).resolve().parents[3]
    payload = run_phase211_analysis(project_root=project_root)
    print(json.dumps(nan_to_none(payload), indent=2))
