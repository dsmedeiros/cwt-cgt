"""Phase 183 analysis: Bridge LOO with all pilots and AE (benchmark scaffold family).

This module loads the pre-baked Phase 183 result artifact which encodes the
leave-one-out cross-validation of the bridge rule across all pilot benchmarks
plus benchmark AE, with five pilots and eleven bridges. Mean held-out combined
R2 = 0.8838; weakest benchmark is BB_sensor_gap. Results confirm that the
bridge predictor generalises across the full expanded pilot-and-bridge set.
"""

from __future__ import annotations

import json
from pathlib import Path

from cwt.cgt.analysis._utils import nan_to_none


def run_phase183_analysis(project_root: Path, output_root: Path | None = None) -> dict:
    """Load and return the Phase 183 bridge LOO all-pilots-and-AE artifact.

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
        If the Phase 183 artifact JSON file is not found at the expected path.
    """
    project_root = Path(project_root)
    artifact_path = (
        project_root
        / 'cgt_benchmarks'
        / 'results'
        / 'benchmark_scaffold_family'
        / 'benchmark_scaffold_phase183_bridge_loo_with_all_pilots_and_ae.json'
    )
    if not artifact_path.exists():
        raise FileNotFoundError(
            f"Phase 183 artifact not found: {artifact_path}. "
            "Expected the bridge LOO all-pilots-and-AE result at "
            "cgt_benchmarks/results/benchmark_scaffold_family/"
            "benchmark_scaffold_phase183_bridge_loo_with_all_pilots_and_ae.json"
        )
    payload = json.loads(artifact_path.read_text(encoding='utf-8'))
    return nan_to_none(payload)


if __name__ == '__main__':
    project_root = Path(__file__).resolve().parents[3]
    payload = run_phase183_analysis(project_root=project_root)
    print(json.dumps(nan_to_none(payload), indent=2))
