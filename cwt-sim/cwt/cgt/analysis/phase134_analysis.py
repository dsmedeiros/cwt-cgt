"""Phase 134 analysis: Bridge tensor/compactness correction candidate (benchmark scaffold family).

This module loads the pre-baked Phase 134 result artifact which derives a more
localised tensor/compactness correction candidate for the bridge adversarial lane,
improving over the Phase 125 compactness candidate. Baseline corrected R2 = 0.8844
(Phase 132); tensor/compactness corrected R2 = 0.8968 with correlation = 0.9604
and sign_agreement = 0.9737. This defines the current best bridge correction
candidate across all six bridge benchmarks.
Verdict: bridge_tensor_compactness_candidate_supported.
"""

from __future__ import annotations

import json
from pathlib import Path

from cwt.cgt.analysis._utils import nan_to_none


def run_phase134_analysis(project_root: Path, output_root: Path | None = None) -> dict:
    """Load and return the Phase 134 bridge tensor/compactness correction candidate artifact.

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
        If the Phase 134 artifact JSON file is not found at the expected path.
    """
    project_root = Path(project_root)
    artifact_path = (
        project_root
        / 'cgt_benchmarks'
        / 'results'
        / 'benchmark_scaffold_family'
        / 'benchmark_scaffold_phase134_bridge_tensor_compactness_candidate.json'
    )
    if not artifact_path.exists():
        raise FileNotFoundError(
            f"Phase 134 artifact not found: {artifact_path}. "
            "Expected the bridge tensor/compactness correction candidate result at "
            "cgt_benchmarks/results/benchmark_scaffold_family/"
            "benchmark_scaffold_phase134_bridge_tensor_compactness_candidate.json"
        )
    payload = json.loads(artifact_path.read_text(encoding='utf-8'))
    return nan_to_none(payload)


if __name__ == '__main__':
    project_root = Path(__file__).resolve().parents[3]
    payload = run_phase134_analysis(project_root=project_root)
    print(json.dumps(nan_to_none(payload), indent=2))
