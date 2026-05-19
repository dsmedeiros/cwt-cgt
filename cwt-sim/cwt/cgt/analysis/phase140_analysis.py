"""Phase 140 analysis: Bridge correction comparison (benchmark scaffold family).

This module loads the pre-baked Phase 140 result artifact which compares the
older compactness correction candidate against the newer tensor/compactness
correction across all bridge benchmarks. Tensor/compactness corrected R2 = 0.8928
versus compactness candidate R2 = 0.8715 (gain = 0.0213), confirming the
tensor/compactness approach is preferred.
"""

from __future__ import annotations

import json
from pathlib import Path

from cwt.cgt.analysis._utils import nan_to_none


def run_phase140_analysis(project_root: Path, output_root: Path | None = None) -> dict:
    """Load and return the Phase 140 bridge correction comparison artifact.

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
        If the Phase 140 artifact JSON file is not found at the expected path.
    """
    project_root = Path(project_root)
    artifact_path = (
        project_root
        / 'cgt_benchmarks'
        / 'results'
        / 'benchmark_scaffold_family'
        / 'benchmark_scaffold_phase140_bridge_correction_comparison.json'
    )
    if not artifact_path.exists():
        raise FileNotFoundError(
            f"Phase 140 artifact not found: {artifact_path}. "
            "Expected the correction comparison artifact at "
            "cgt_benchmarks/results/benchmark_scaffold_family/"
            "benchmark_scaffold_phase140_bridge_correction_comparison.json"
        )
    payload = json.loads(artifact_path.read_text(encoding='utf-8'))
    return nan_to_none(payload)


if __name__ == '__main__':
    project_root = Path(__file__).resolve().parents[3]
    payload = run_phase140_analysis(project_root=project_root)
    print(json.dumps(nan_to_none(payload), indent=2))
