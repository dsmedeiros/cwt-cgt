"""Phase 50 analysis: Pooled five-harder-family scaffold benchmark.

This module loads the pre-baked Phase 50 result artifact which stress-tests the
pooled five-positive noisy scaffold rule with a harder perturbation family across
the full five-benchmark pool (C, G, H, I, J).
"""

from __future__ import annotations

import json
from pathlib import Path

from cwt.cgt.analysis._utils import nan_to_none


def run_phase50_analysis(project_root: Path, output_root: Path | None = None) -> dict:
    """Load and return the Phase 50 pooled five-harder-family scaffold artifact.

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
        If the Phase 50 artifact JSON file is not found at the expected path.
    """
    project_root = Path(project_root)
    artifact_path = (
        project_root
        / 'cgt_benchmarks'
        / 'results'
        / 'benchmark_scaffold_family'
        / 'benchmark_scaffold_phase50_pooled_five_harder_family.json'
    )
    if not artifact_path.exists():
        raise FileNotFoundError(
            f"Phase 50 artifact not found: {artifact_path}. "
            "Expected the pooled five-harder-family scaffold result at "
            "cgt_benchmarks/results/benchmark_scaffold_family/"
            "benchmark_scaffold_phase50_pooled_five_harder_family.json"
        )
    payload = json.loads(artifact_path.read_text(encoding='utf-8'))
    return nan_to_none(payload)


if __name__ == '__main__':
    project_root = Path(__file__).resolve().parents[3]
    payload = run_phase50_analysis(project_root=project_root)
    print(json.dumps(nan_to_none(payload), indent=2))
