"""Phase 136 analysis: Bridge boundary refresh 2 (benchmark scaffold family).

This module loads the pre-baked Phase 136 result artifact which refreshes the
bridge lane boundary map after the sixth bridge benchmark (Y), family-holdout
audit, and tensor/compactness correction candidate. Bridge positive band =
[0.9098, 0.9368]; bridge adversarial raw band = [0.3926, 0.4877]; bridge
adversarial corrected band = [0.8382, 0.8968]; bridge family holdout band =
[0.8461, 0.9144]. Weakest bridge benchmark = T_semisynthetic_observed;
weakest family = observed.
"""

from __future__ import annotations

import json
from pathlib import Path

from cwt.cgt.analysis._utils import nan_to_none


def run_phase136_analysis(project_root: Path, output_root: Path | None = None) -> dict:
    """Load and return the Phase 136 bridge boundary refresh 2 artifact.

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
        If the Phase 136 artifact JSON file is not found at the expected path.
    """
    project_root = Path(project_root)
    artifact_path = (
        project_root
        / 'cgt_benchmarks'
        / 'results'
        / 'benchmark_scaffold_family'
        / 'benchmark_scaffold_phase136_bridge_boundary_refresh2.json'
    )
    if not artifact_path.exists():
        raise FileNotFoundError(
            f"Phase 136 artifact not found: {artifact_path}. "
            "Expected the bridge boundary refresh 2 result at "
            "cgt_benchmarks/results/benchmark_scaffold_family/"
            "benchmark_scaffold_phase136_bridge_boundary_refresh2.json"
        )
    payload = json.loads(artifact_path.read_text(encoding='utf-8'))
    return nan_to_none(payload)


if __name__ == '__main__':
    project_root = Path(__file__).resolve().parents[3]
    payload = run_phase136_analysis(project_root=project_root)
    print(json.dumps(nan_to_none(payload), indent=2))
