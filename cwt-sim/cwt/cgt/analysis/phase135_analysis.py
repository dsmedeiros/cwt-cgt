"""Phase 135 analysis: Bridge calibration-free minimal rule comparison (benchmark scaffold family).

This module loads the pre-baked Phase 135 result artifact which compares the
bridge calibration-free minimal rule against the bridge adversarial lane. The
calibration-free bridge positive R2 = 0.9246 and calibration-free adversarial
corrected R2 = 0.8789 are both within the accepted bridge bands, validating
that the bridge rule is not sensitive to calibration choices.
Verdict: bridge_calibration_free_minimal_supported.
"""

from __future__ import annotations

import json
from pathlib import Path

from cwt.cgt.analysis._utils import nan_to_none


def run_phase135_analysis(project_root: Path, output_root: Path | None = None) -> dict:
    """Load and return the Phase 135 bridge calibration-free minimal comparison artifact.

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
        If the Phase 135 artifact JSON file is not found at the expected path.
    """
    project_root = Path(project_root)
    artifact_path = (
        project_root
        / 'cgt_benchmarks'
        / 'results'
        / 'benchmark_scaffold_family'
        / 'benchmark_scaffold_phase135_bridge_calibration_free_minimal.json'
    )
    if not artifact_path.exists():
        raise FileNotFoundError(
            f"Phase 135 artifact not found: {artifact_path}. "
            "Expected the bridge calibration-free minimal comparison result at "
            "cgt_benchmarks/results/benchmark_scaffold_family/"
            "benchmark_scaffold_phase135_bridge_calibration_free_minimal.json"
        )
    payload = json.loads(artifact_path.read_text(encoding='utf-8'))
    return nan_to_none(payload)


if __name__ == '__main__':
    project_root = Path(__file__).resolve().parents[3]
    payload = run_phase135_analysis(project_root=project_root)
    print(json.dumps(nan_to_none(payload), indent=2))
