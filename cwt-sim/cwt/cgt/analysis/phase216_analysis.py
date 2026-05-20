"""Phase 216 analysis: Bridge-pilot gap audit (benchmark scaffold family).

This module loads the pre-baked Phase 216 result artifact which quantifies
the performance gap between bridge benchmarks and pilot benchmarks.
Bridge positive R2 = 0.9397 vs pilot positive R2 = 0.8927 (positive_gap = 0.047).
Bridge adversarial R2 = 0.9194 vs pilot adversarial R2 = 0.8461
(adversarial_gap = 0.0733).
"""

from __future__ import annotations

import json
from pathlib import Path

from cwt.cgt.analysis._utils import nan_to_none


def run_phase216_analysis(project_root: Path, output_root: Path | None = None) -> dict:
    """Load and return the Phase 216 bridge-pilot gap audit artifact.

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
        If the Phase 216 artifact JSON file is not found at the expected path.
    """
    project_root = Path(project_root)
    artifact_path = (
        project_root
        / 'cgt_benchmarks'
        / 'results'
        / 'benchmark_scaffold_family'
        / 'benchmark_scaffold_phase216_bridge_pilot_gap_audit.json'
    )
    if not artifact_path.exists():
        raise FileNotFoundError(
            f"Phase 216 artifact not found: {artifact_path}. "
            "Expected the bridge-pilot gap audit result at "
            "cgt_benchmarks/results/benchmark_scaffold_family/"
            "benchmark_scaffold_phase216_bridge_pilot_gap_audit.json"
        )
    payload = json.loads(artifact_path.read_text(encoding='utf-8'))
    return nan_to_none(payload)


if __name__ == '__main__':
    project_root = Path(__file__).resolve().parents[3]
    payload = run_phase216_analysis(project_root=project_root)
    print(json.dumps(nan_to_none(payload), indent=2))
