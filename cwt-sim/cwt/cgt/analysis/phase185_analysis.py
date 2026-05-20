"""Phase 185 analysis: Bridge tensor geometry law v3 candidate (benchmark scaffold family).

This module loads the pre-baked Phase 185 result artifact which encodes the
bridge tensor geometry law v3 candidate. Raw combined R2 = 0.5561 (adversarial
degrades); prior-corrected (v2) combined R2 = 0.9128; tensor-geometry v3 corrected
combined R2 = 0.9189 and corrected sign_agreement = 0.9769, confirming v3 improves
incrementally over the prior v2 correction law.
"""

from __future__ import annotations

import json
from pathlib import Path

from cwt.cgt.analysis._utils import nan_to_none


def run_phase185_analysis(project_root: Path, output_root: Path | None = None) -> dict:
    """Load and return the Phase 185 bridge tensor geometry law v3 artifact.

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
        If the Phase 185 artifact JSON file is not found at the expected path.
    """
    project_root = Path(project_root)
    artifact_path = (
        project_root
        / 'cgt_benchmarks'
        / 'results'
        / 'benchmark_scaffold_family'
        / 'benchmark_scaffold_phase185_bridge_tensor_geometry_law_v3.json'
    )
    if not artifact_path.exists():
        raise FileNotFoundError(
            f"Phase 185 artifact not found: {artifact_path}. "
            "Expected the bridge tensor geometry law v3 result at "
            "cgt_benchmarks/results/benchmark_scaffold_family/"
            "benchmark_scaffold_phase185_bridge_tensor_geometry_law_v3.json"
        )
    payload = json.loads(artifact_path.read_text(encoding='utf-8'))
    return nan_to_none(payload)


if __name__ == '__main__':
    project_root = Path(__file__).resolve().parents[3]
    payload = run_phase185_analysis(project_root=project_root)
    print(json.dumps(nan_to_none(payload), indent=2))
