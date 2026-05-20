"""Phase 184 analysis: Bridge correction v2 versus minimal rule comparison (benchmark scaffold family).

This module loads the pre-baked Phase 184 result artifact which encodes the
direct comparison between the minimal bridge rule and the tensor geometry law v2
correction. Minimal rule combined R2 = 0.8802; tensor_law_v2 combined R2 = 0.8934;
improvement = 0.0132, confirming that the v2 correction consistently outperforms
the minimal rule across the full bridge benchmark suite.
"""

from __future__ import annotations

import json
from pathlib import Path

from cwt.cgt.analysis._utils import nan_to_none


def run_phase184_analysis(project_root: Path, output_root: Path | None = None) -> dict:
    """Load and return the Phase 184 bridge correction v2 vs minimal comparison artifact.

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
        If the Phase 184 artifact JSON file is not found at the expected path.
    """
    project_root = Path(project_root)
    artifact_path = (
        project_root
        / 'cgt_benchmarks'
        / 'results'
        / 'benchmark_scaffold_family'
        / 'benchmark_scaffold_phase184_bridge_correction_v2_vs_minimal.json'
    )
    if not artifact_path.exists():
        raise FileNotFoundError(
            f"Phase 184 artifact not found: {artifact_path}. "
            "Expected the bridge correction v2 vs minimal result at "
            "cgt_benchmarks/results/benchmark_scaffold_family/"
            "benchmark_scaffold_phase184_bridge_correction_v2_vs_minimal.json"
        )
    payload = json.loads(artifact_path.read_text(encoding='utf-8'))
    return nan_to_none(payload)


if __name__ == '__main__':
    project_root = Path(__file__).resolve().parents[3]
    payload = run_phase184_analysis(project_root=project_root)
    print(json.dumps(nan_to_none(payload), indent=2))
