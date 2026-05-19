"""Phase 142 analysis: Less-synthetic bridge positive pilot (benchmark AA).

This module loads the pre-baked Phase 142 result artifact which validates the
bridge positive rule on benchmark AA, a less hand-crafted (less-synthetic)
semisynthetic graph benchmark. Held-out combined R2 = 0.8867 and
sign_agreement = 0.9917, confirming transfer to less-synthetic conditions.
"""

from __future__ import annotations

import json
from pathlib import Path

from cwt.cgt.analysis._utils import nan_to_none


def run_phase142_analysis(project_root: Path, output_root: Path | None = None) -> dict:
    """Load and return the Phase 142 less-synthetic bridge positive artifact.

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
        If the Phase 142 artifact JSON file is not found at the expected path.
    """
    project_root = Path(project_root)
    artifact_path = (
        project_root
        / 'cgt_benchmarks'
        / 'results'
        / 'benchmark_AA_less_synthetic'
        / 'benchmark_aa_phase142_less_synthetic_bridge_positive.json'
    )
    if not artifact_path.exists():
        raise FileNotFoundError(
            f"Phase 142 artifact not found: {artifact_path}. "
            "Expected the AA less-synthetic positive result at "
            "cgt_benchmarks/results/benchmark_AA_less_synthetic/"
            "benchmark_aa_phase142_less_synthetic_bridge_positive.json"
        )
    payload = json.loads(artifact_path.read_text(encoding='utf-8'))
    return nan_to_none(payload)


if __name__ == '__main__':
    project_root = Path(__file__).resolve().parents[3]
    payload = run_phase142_analysis(project_root=project_root)
    print(json.dumps(nan_to_none(payload), indent=2))
