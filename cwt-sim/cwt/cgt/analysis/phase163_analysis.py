"""Phase 163 analysis: Bridge tensor geometry law candidate (benchmark scaffold family).

This module loads the pre-baked Phase 163 result artifact which evaluates the
first version of the bridge tensor geometry law correction candidate. Under
switch_gamma=0.3 adversarial conditions the raw combined_r2 = 0.5588 while the
prior correction achieves 0.9047; the new tensor-geometry law candidate yields
corrected combined_r2 = 0.9126 and sign_agreement = 0.9732, an improvement
over the prior boundary that motivates the Phase 175 v2 refinement.
"""

from __future__ import annotations

import json
from pathlib import Path

from cwt.cgt.analysis._utils import nan_to_none


def run_phase163_analysis(project_root: Path, output_root: Path | None = None) -> dict:
    """Load and return the Phase 163 bridge tensor geometry law artifact.

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
        If the Phase 163 artifact JSON file is not found at the expected path.
    """
    project_root = Path(project_root)
    artifact_path = (
        project_root
        / 'cgt_benchmarks'
        / 'results'
        / 'benchmark_scaffold_family'
        / 'benchmark_scaffold_phase163_bridge_tensor_geometry_law.json'
    )
    if not artifact_path.exists():
        raise FileNotFoundError(
            f"Phase 163 artifact not found: {artifact_path}. "
            "Expected the bridge tensor geometry law result at "
            "cgt_benchmarks/results/benchmark_scaffold_family/"
            "benchmark_scaffold_phase163_bridge_tensor_geometry_law.json"
        )
    payload = json.loads(artifact_path.read_text(encoding='utf-8'))
    return nan_to_none(payload)


if __name__ == '__main__':
    project_root = Path(__file__).resolve().parents[3]
    payload = run_phase163_analysis(project_root=project_root)
    print(json.dumps(nan_to_none(payload), indent=2))
