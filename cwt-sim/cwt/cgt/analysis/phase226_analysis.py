"""Phase 226 analysis: Externalization plateau summary (benchmark scaffold family).

This module loads the pre-baked Phase 226 result artifact which writes the plateau
and stop-rule summary for the bridge-only internal tuning lane.
Status: positive_progress_flattening.
Last holdout gains: [0.0202, 0.0142, 0.0109].
Last tensor-law gains: [0.0037, 0.0014, 0.0025].
Decision: stop internal bridge tuning after v7 and prioritize externalization.
"""

from __future__ import annotations

import json
from pathlib import Path

from cwt.cgt.analysis._utils import nan_to_none


def run_phase226_analysis(project_root: Path, output_root: Path | None = None) -> dict:
    """Load and return the Phase 226 externalization plateau summary artifact.

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
        If the Phase 226 artifact JSON file is not found at the expected path.
    """
    project_root = Path(project_root)
    artifact_path = (
        project_root
        / 'cgt_benchmarks'
        / 'results'
        / 'benchmark_scaffold_family'
        / 'benchmark_scaffold_phase226_externalization_plateau_summary.json'
    )
    if not artifact_path.exists():
        raise FileNotFoundError(
            f"Phase 226 artifact not found: {artifact_path}. "
            "Expected the externalization plateau summary result at "
            "cgt_benchmarks/results/benchmark_scaffold_family/"
            "benchmark_scaffold_phase226_externalization_plateau_summary.json"
        )
    payload = json.loads(artifact_path.read_text(encoding='utf-8'))
    return nan_to_none(payload)


if __name__ == '__main__':
    project_root = Path(__file__).resolve().parents[3]
    payload = run_phase226_analysis(project_root=project_root)
    print(json.dumps(nan_to_none(payload), indent=2))
