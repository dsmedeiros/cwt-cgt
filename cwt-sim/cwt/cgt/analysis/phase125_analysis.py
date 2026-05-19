"""Phase 125 analysis: Bridge compactness correction candidate (benchmark scaffold family).

This module loads the pre-baked Phase 125 result artifact which derives a
compactness-based correction candidate for the bridge adversarial lane from the
cross-lane compactness audit. The correction improves pooled adversarial corrected
R2 from 0.8724 (Phase 124 baseline) to 0.8896, with corrected correlation = 0.9581
and sign_agreement = 0.9729. This defines the bridge compactness correction
candidate and is used to construct the bridge minimal accepted theory pack.
Verdict: bridge_compactness_correction_candidate_supported.
"""

from __future__ import annotations

import json
from pathlib import Path

from cwt.cgt.analysis._utils import nan_to_none


def run_phase125_analysis(project_root: Path, output_root: Path | None = None) -> dict:
    """Load and return the Phase 125 bridge compactness correction candidate artifact.

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
        If the Phase 125 artifact JSON file is not found at the expected path.
    """
    project_root = Path(project_root)
    artifact_path = (
        project_root
        / 'cgt_benchmarks'
        / 'results'
        / 'benchmark_scaffold_family'
        / 'benchmark_scaffold_phase125_bridge_compactness_correction_candidate.json'
    )
    if not artifact_path.exists():
        raise FileNotFoundError(
            f"Phase 125 artifact not found: {artifact_path}. "
            "Expected the bridge compactness correction candidate result at "
            "cgt_benchmarks/results/benchmark_scaffold_family/"
            "benchmark_scaffold_phase125_bridge_compactness_correction_candidate.json"
        )
    payload = json.loads(artifact_path.read_text(encoding='utf-8'))
    return nan_to_none(payload)


if __name__ == '__main__':
    project_root = Path(__file__).resolve().parents[3]
    payload = run_phase125_analysis(project_root=project_root)
    print(json.dumps(nan_to_none(payload), indent=2))
