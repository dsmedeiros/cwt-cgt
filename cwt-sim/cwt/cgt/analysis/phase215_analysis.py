"""Phase 215 analysis: Pilot-only summary (benchmark scaffold family).

This module loads the pre-baked Phase 215 result artifact which summarizes
performance across the eight pilot benchmarks only. Pilot count = 8.
Positive combined_r2 = 0.8927; adversarial_corrected combined_r2 = 0.8461.
Weakest pilot: GG_windowed_sparse_release; strongest pilot: AA_less_synthetic.
"""

from __future__ import annotations

import json
from pathlib import Path

from cwt.cgt.analysis._utils import nan_to_none


def run_phase215_analysis(project_root: Path, output_root: Path | None = None) -> dict:
    """Load and return the Phase 215 pilot-only summary artifact.

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
        If the Phase 215 artifact JSON file is not found at the expected path.
    """
    project_root = Path(project_root)
    artifact_path = (
        project_root
        / 'cgt_benchmarks'
        / 'results'
        / 'benchmark_scaffold_family'
        / 'benchmark_scaffold_phase215_pilot_only_summary.json'
    )
    if not artifact_path.exists():
        raise FileNotFoundError(
            f"Phase 215 artifact not found: {artifact_path}. "
            "Expected the pilot-only summary result at "
            "cgt_benchmarks/results/benchmark_scaffold_family/"
            "benchmark_scaffold_phase215_pilot_only_summary.json"
        )
    payload = json.loads(artifact_path.read_text(encoding='utf-8'))
    return nan_to_none(payload)


if __name__ == '__main__':
    project_root = Path(__file__).resolve().parents[3]
    payload = run_phase215_analysis(project_root=project_root)
    print(json.dumps(nan_to_none(payload), indent=2))
