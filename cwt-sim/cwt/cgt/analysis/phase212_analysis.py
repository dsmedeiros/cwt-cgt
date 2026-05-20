"""Phase 212 analysis: Bridge tensor geometry law v6 (benchmark scaffold family).

This module loads the pre-baked Phase 212 result artifact which introduces the
tensor geometry law v6, constructed via benchmark holdout tensor localization.
Raw combined_r2 = 0.5611; corrected combined_r2 = 0.9262;
corrected sign_agreement = 0.9798. Incremental improvement over v5.
"""

from __future__ import annotations

import json
from pathlib import Path

from cwt.cgt.analysis._utils import nan_to_none


def run_phase212_analysis(project_root: Path, output_root: Path | None = None) -> dict:
    """Load and return the Phase 212 bridge tensor geometry law v6 artifact.

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
        If the Phase 212 artifact JSON file is not found at the expected path.
    """
    project_root = Path(project_root)
    artifact_path = (
        project_root
        / 'cgt_benchmarks'
        / 'results'
        / 'benchmark_scaffold_family'
        / 'benchmark_scaffold_phase212_bridge_tensor_geometry_law_v6.json'
    )
    if not artifact_path.exists():
        raise FileNotFoundError(
            f"Phase 212 artifact not found: {artifact_path}. "
            "Expected the bridge tensor geometry law v6 result at "
            "cgt_benchmarks/results/benchmark_scaffold_family/"
            "benchmark_scaffold_phase212_bridge_tensor_geometry_law_v6.json"
        )
    payload = json.loads(artifact_path.read_text(encoding='utf-8'))
    return nan_to_none(payload)


if __name__ == '__main__':
    project_root = Path(__file__).resolve().parents[3]
    payload = run_phase212_analysis(project_root=project_root)
    print(json.dumps(nan_to_none(payload), indent=2))
