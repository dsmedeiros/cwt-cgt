"""Phase 154 analysis: Bridge tensor-law candidate (benchmark scaffold family).

This module loads the pre-baked Phase 154 result artifact which starts a bridge
tensor-law candidate evaluation. The tensor-law correction improves pooled bridge
adversarial corrected R2 from the baseline 0.8994 to 0.9088, with sign agreement
= 0.979, supporting the bridge tensor-law candidate as a viable improvement over
the standard tensor-compactness correction.
"""

from __future__ import annotations

import json
from pathlib import Path

from cwt.cgt.analysis._utils import nan_to_none


def run_phase154_analysis(project_root: Path, output_root: Path | None = None) -> dict:
    """Load and return the Phase 154 bridge tensor-law candidate artifact.

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
        If the Phase 154 artifact JSON file is not found at the expected path.
    """
    project_root = Path(project_root)
    artifact_path = (
        project_root
        / 'cgt_benchmarks'
        / 'results'
        / 'benchmark_scaffold_family'
        / 'benchmark_scaffold_phase154_bridge_tensor_law_candidate.json'
    )
    if not artifact_path.exists():
        raise FileNotFoundError(
            f"Phase 154 artifact not found: {artifact_path}. "
            "Expected the bridge tensor-law candidate result at "
            "cgt_benchmarks/results/benchmark_scaffold_family/"
            "benchmark_scaffold_phase154_bridge_tensor_law_candidate.json"
        )
    payload = json.loads(artifact_path.read_text(encoding='utf-8'))
    return nan_to_none(payload)


if __name__ == '__main__':
    project_root = Path(__file__).resolve().parents[3]
    payload = run_phase154_analysis(project_root=project_root)
    print(json.dumps(nan_to_none(payload), indent=2))
