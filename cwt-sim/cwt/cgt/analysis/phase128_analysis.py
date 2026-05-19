"""Phase 128 analysis: Bridge boundary refresh (benchmark scaffold family).

This module loads the pre-baked Phase 128 result artifact which refreshes the
bridge lane boundary map after full adversarial coverage and compactness-candidate
correction across all five bridge benchmarks. The artifact records empirical bands
for positive transfer, adversarial raw, adversarial corrected, and bridge-specific
sub-bands. Bridge positive band = [0.9098, 0.9248]; bridge adversarial corrected
band = [0.8382, 0.8896]; weakest benchmark = T_semisynthetic_observed.
"""

from __future__ import annotations

import json
from pathlib import Path

from cwt.cgt.analysis._utils import nan_to_none


def run_phase128_analysis(project_root: Path, output_root: Path | None = None) -> dict:
    """Load and return the Phase 128 bridge boundary refresh artifact.

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
        If the Phase 128 artifact JSON file is not found at the expected path.
    """
    project_root = Path(project_root)
    artifact_path = (
        project_root
        / 'cgt_benchmarks'
        / 'results'
        / 'benchmark_scaffold_family'
        / 'benchmark_scaffold_phase128_bridge_boundary_refresh.json'
    )
    if not artifact_path.exists():
        raise FileNotFoundError(
            f"Phase 128 artifact not found: {artifact_path}. "
            "Expected the bridge boundary refresh result at "
            "cgt_benchmarks/results/benchmark_scaffold_family/"
            "benchmark_scaffold_phase128_bridge_boundary_refresh.json"
        )
    payload = json.loads(artifact_path.read_text(encoding='utf-8'))
    return nan_to_none(payload)


if __name__ == '__main__':
    project_root = Path(__file__).resolve().parents[3]
    payload = run_phase128_analysis(project_root=project_root)
    print(json.dumps(nan_to_none(payload), indent=2))
