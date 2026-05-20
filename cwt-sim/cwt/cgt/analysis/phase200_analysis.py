"""Phase 200 analysis: Seventh less-synthetic adversarial (benchmark GG windowed sparse release).

This module loads the pre-baked Phase 200 result artifact which validates the
bridge tensor geometry law v4 correction on the adversarial transfer over
benchmark GG (windowed sparse release). Raw combined R2 = 0.4179;
corrected combined R2 = 0.8364; corrected sign agreement = 0.9514.
"""

from __future__ import annotations

import json
from pathlib import Path

from cwt.cgt.analysis._utils import nan_to_none


def run_phase200_analysis(project_root: Path, output_root: Path | None = None) -> dict:
    """Load and return the Phase 200 seventh less-synthetic adversarial artifact.

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
        If the Phase 200 artifact JSON file is not found at the expected path.
    """
    project_root = Path(project_root)
    artifact_path = (
        project_root
        / 'cgt_benchmarks'
        / 'results'
        / 'benchmark_GG_windowed_sparse_release'
        / 'benchmark_gg_phase200_seventh_less_synthetic_adversarial.json'
    )
    if not artifact_path.exists():
        raise FileNotFoundError(
            f"Phase 200 artifact not found: {artifact_path}. "
            "Expected the seventh less-synthetic adversarial result at "
            "cgt_benchmarks/results/benchmark_GG_windowed_sparse_release/"
            "benchmark_gg_phase200_seventh_less_synthetic_adversarial.json"
        )
    payload = json.loads(artifact_path.read_text(encoding='utf-8'))
    return nan_to_none(payload)


if __name__ == '__main__':
    project_root = Path(__file__).resolve().parents[3]
    payload = run_phase200_analysis(project_root=project_root)
    print(json.dumps(nan_to_none(payload), indent=2))
