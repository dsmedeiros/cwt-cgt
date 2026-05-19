"""Phase 146 analysis: Bridge-to-pilot transfer summary (benchmark scaffold family).

This module loads the pre-baked Phase 146 result artifact which summarizes
bridge-to-less-synthetic-pilot transfer after the AA pilot benchmarks.
Pooled bridge positive R2 = 0.9335; pilot positive R2 = 0.8867; pilot adversarial
corrected R2 = 0.8124; combined bridge+pilot R2 = 0.9056. The verdict indicates
transfer is supportive but weaker than the full bridge ensemble.
"""

from __future__ import annotations

import json
from pathlib import Path

from cwt.cgt.analysis._utils import nan_to_none


def run_phase146_analysis(project_root: Path, output_root: Path | None = None) -> dict:
    """Load and return the Phase 146 bridge-to-pilot transfer summary artifact.

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
        If the Phase 146 artifact JSON file is not found at the expected path.
    """
    project_root = Path(project_root)
    artifact_path = (
        project_root
        / 'cgt_benchmarks'
        / 'results'
        / 'benchmark_scaffold_family'
        / 'benchmark_scaffold_phase146_bridge_pilot_transfer_summary.json'
    )
    if not artifact_path.exists():
        raise FileNotFoundError(
            f"Phase 146 artifact not found: {artifact_path}. "
            "Expected the bridge-to-pilot transfer summary at "
            "cgt_benchmarks/results/benchmark_scaffold_family/"
            "benchmark_scaffold_phase146_bridge_pilot_transfer_summary.json"
        )
    payload = json.loads(artifact_path.read_text(encoding='utf-8'))
    return nan_to_none(payload)


if __name__ == '__main__':
    project_root = Path(__file__).resolve().parents[3]
    payload = run_phase146_analysis(project_root=project_root)
    print(json.dumps(nan_to_none(payload), indent=2))
