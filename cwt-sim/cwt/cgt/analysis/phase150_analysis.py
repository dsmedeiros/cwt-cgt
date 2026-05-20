"""Phase 150 analysis: Bridge correction comparison — tensor/compactness vs minimal.

This module loads the pre-baked Phase 150 result artifact which compares the
tensor-compactness correction to the minimal calibration-free rule under the same
bridge family adversarial split. Tensor/compactness achieves corrected combined
R2 = 0.8994 versus minimal calibration-free R2 = 0.8612, confirming
tensor/compactness as the preferred correction method.
"""

from __future__ import annotations

import json
from pathlib import Path

from cwt.cgt.analysis._utils import nan_to_none


def run_phase150_analysis(project_root: Path, output_root: Path | None = None) -> dict:
    """Load and return the Phase 150 bridge correction comparison artifact.

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
        If the Phase 150 artifact JSON file is not found at the expected path.
    """
    project_root = Path(project_root)
    artifact_path = (
        project_root
        / 'cgt_benchmarks'
        / 'results'
        / 'benchmark_scaffold_family'
        / 'benchmark_scaffold_phase150_bridge_correction_comparison.json'
    )
    if not artifact_path.exists():
        raise FileNotFoundError(
            f"Phase 150 artifact not found: {artifact_path}. "
            "Expected the bridge correction comparison result at "
            "cgt_benchmarks/results/benchmark_scaffold_family/"
            "benchmark_scaffold_phase150_bridge_correction_comparison.json"
        )
    payload = json.loads(artifact_path.read_text(encoding='utf-8'))
    return nan_to_none(payload)


if __name__ == '__main__':
    project_root = Path(__file__).resolve().parents[3]
    payload = run_phase150_analysis(project_root=project_root)
    print(json.dumps(nan_to_none(payload), indent=2))
