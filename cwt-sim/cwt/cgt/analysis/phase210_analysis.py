"""Phase 210 analysis: Eighth less-synthetic adversarial (benchmark HH event gap release).

This module loads the pre-baked Phase 210 result artifact which validates the
bridge tensor geometry law v5 correction on benchmark HH under adversarial
conditions. Raw combined_r2 = 0.4351; corrected combined_r2 = 0.8446;
corrected sign_agreement = 0.9569. Confirms adversarial correction effectiveness
on the eighth less-synthetic benchmark.
"""

from __future__ import annotations

import json
from pathlib import Path

from cwt.cgt.analysis._utils import nan_to_none


def run_phase210_analysis(project_root: Path, output_root: Path | None = None) -> dict:
    """Load and return the Phase 210 eighth less-synthetic adversarial artifact.

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
        If the Phase 210 artifact JSON file is not found at the expected path.
    """
    project_root = Path(project_root)
    artifact_path = (
        project_root
        / 'cgt_benchmarks'
        / 'results'
        / 'benchmark_HH_event_gap_release'
        / 'benchmark_hh_phase210_eighth_less_synthetic_adversarial.json'
    )
    if not artifact_path.exists():
        raise FileNotFoundError(
            f"Phase 210 artifact not found: {artifact_path}. "
            "Expected the eighth less-synthetic adversarial result at "
            "cgt_benchmarks/results/benchmark_HH_event_gap_release/"
            "benchmark_hh_phase210_eighth_less_synthetic_adversarial.json"
        )
    payload = json.loads(artifact_path.read_text(encoding='utf-8'))
    return nan_to_none(payload)


if __name__ == '__main__':
    project_root = Path(__file__).resolve().parents[3]
    payload = run_phase210_analysis(project_root=project_root)
    print(json.dumps(nan_to_none(payload), indent=2))
