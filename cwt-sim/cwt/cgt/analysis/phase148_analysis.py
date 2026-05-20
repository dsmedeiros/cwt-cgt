"""Phase 148 analysis: Pooled bridge family adversarial summary (benchmark scaffold family).

This module loads the pre-baked Phase 148 result artifact which builds a true pooled
bridge family adversarial summary across three adversarial families (event_burst,
less_synthetic, thinned_window). Aggregate raw combined R2 = 0.5487, corrected
combined R2 = 0.8994, corrected sign agreement = 0.975, confirming the tensor-
compactness correction holds across the expanded adversarial family pool.
"""

from __future__ import annotations

import json
from pathlib import Path

from cwt.cgt.analysis._utils import nan_to_none


def run_phase148_analysis(project_root: Path, output_root: Path | None = None) -> dict:
    """Load and return the Phase 148 pooled bridge family adversarial artifact.

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
        If the Phase 148 artifact JSON file is not found at the expected path.
    """
    project_root = Path(project_root)
    artifact_path = (
        project_root
        / 'cgt_benchmarks'
        / 'results'
        / 'benchmark_scaffold_family'
        / 'benchmark_scaffold_phase148_bridge_family_adversarial_pooled.json'
    )
    if not artifact_path.exists():
        raise FileNotFoundError(
            f"Phase 148 artifact not found: {artifact_path}. "
            "Expected the pooled bridge family adversarial result at "
            "cgt_benchmarks/results/benchmark_scaffold_family/"
            "benchmark_scaffold_phase148_bridge_family_adversarial_pooled.json"
        )
    payload = json.loads(artifact_path.read_text(encoding='utf-8'))
    return nan_to_none(payload)


if __name__ == '__main__':
    project_root = Path(__file__).resolve().parents[3]
    payload = run_phase148_analysis(project_root=project_root)
    print(json.dumps(nan_to_none(payload), indent=2))
