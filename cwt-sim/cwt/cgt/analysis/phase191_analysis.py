"""Phase 191 analysis: Bridge LOO holdout expanded (benchmark scaffold family).

This module loads the pre-baked Phase 191 result artifact which records the
leave-one-out holdout validation expanded to twelve bridge benchmarks and six
pilot benchmarks. Mean held-out combined_r2 = 0.8859; weakest benchmark is
FF_mixed_release_delay; bridge_count = 12; pilot_count = 6.
"""

from __future__ import annotations

import json
from pathlib import Path

from cwt.cgt.analysis._utils import nan_to_none


def run_phase191_analysis(project_root: Path, output_root: Path | None = None) -> dict:
    """Load and return the Phase 191 bridge LOO holdout expanded artifact.

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
        If the Phase 191 artifact JSON file is not found at the expected path.
    """
    project_root = Path(project_root)
    artifact_path = (
        project_root
        / 'cgt_benchmarks'
        / 'results'
        / 'benchmark_scaffold_family'
        / 'benchmark_scaffold_phase191_bridge_holdout_expanded.json'
    )
    if not artifact_path.exists():
        raise FileNotFoundError(
            f"Phase 191 artifact not found: {artifact_path}. "
            "Expected the bridge LOO holdout expanded result at "
            "cgt_benchmarks/results/benchmark_scaffold_family/"
            "benchmark_scaffold_phase191_bridge_holdout_expanded.json"
        )
    payload = json.loads(artifact_path.read_text(encoding='utf-8'))
    return nan_to_none(payload)


if __name__ == '__main__':
    project_root = Path(__file__).resolve().parents[3]
    payload = run_phase191_analysis(project_root=project_root)
    print(json.dumps(nan_to_none(payload), indent=2))
