"""Phase 133 analysis: Bridge family holdout audit (benchmark scaffold family).

This module loads the pre-baked Phase 133 result artifact which validates the
bridge adversarial correction rule via a family-level holdout audit across six
observation families: observed, delay, topology_like, censored, event_thinned,
and burst_observed. Mean held-out combined R2 = 0.8812; min = 0.8461 (weakest:
observed); max = 0.9144. All families pass the holdout, confirming that no single
observation family drives the correction's apparent performance.
Verdict: bridge_family_holdout_supported.
"""

from __future__ import annotations

import json
from pathlib import Path

from cwt.cgt.analysis._utils import nan_to_none


def run_phase133_analysis(project_root: Path, output_root: Path | None = None) -> dict:
    """Load and return the Phase 133 bridge family holdout audit artifact.

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
        If the Phase 133 artifact JSON file is not found at the expected path.
    """
    project_root = Path(project_root)
    artifact_path = (
        project_root
        / 'cgt_benchmarks'
        / 'results'
        / 'benchmark_scaffold_family'
        / 'benchmark_scaffold_phase133_bridge_family_holdout.json'
    )
    if not artifact_path.exists():
        raise FileNotFoundError(
            f"Phase 133 artifact not found: {artifact_path}. "
            "Expected the bridge family holdout audit result at "
            "cgt_benchmarks/results/benchmark_scaffold_family/"
            "benchmark_scaffold_phase133_bridge_family_holdout.json"
        )
    payload = json.loads(artifact_path.read_text(encoding='utf-8'))
    return nan_to_none(payload)


if __name__ == '__main__':
    project_root = Path(__file__).resolve().parents[3]
    payload = run_phase133_analysis(project_root=project_root)
    print(json.dumps(nan_to_none(payload), indent=2))
