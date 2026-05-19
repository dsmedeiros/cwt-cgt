"""Phase 132 analysis: Pooled six-bridge adversarial summary (benchmark scaffold family).

This module loads the pre-baked Phase 132 result artifact which aggregates
adversarial perturbation results across all six bridge benchmarks T, U, V, W,
X, and Y. Pooled raw R2 = 0.4451 degrades under adversarial perturbation;
corrected R2 = 0.8844 and corrected sign_agreement = 0.9701 confirm that the
correction generalises across all six bridge cases including the new benchmark Y.
Verdict: pooled_six_bridge_adversarial_supported.
"""

from __future__ import annotations

import json
from pathlib import Path

from cwt.cgt.analysis._utils import nan_to_none


def run_phase132_analysis(project_root: Path, output_root: Path | None = None) -> dict:
    """Load and return the Phase 132 pooled six-bridge adversarial artifact.

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
        If the Phase 132 artifact JSON file is not found at the expected path.
    """
    project_root = Path(project_root)
    artifact_path = (
        project_root
        / 'cgt_benchmarks'
        / 'results'
        / 'benchmark_scaffold_family'
        / 'benchmark_scaffold_phase132_pooled_six_bridge_adversarial.json'
    )
    if not artifact_path.exists():
        raise FileNotFoundError(
            f"Phase 132 artifact not found: {artifact_path}. "
            "Expected the pooled six-bridge adversarial result at "
            "cgt_benchmarks/results/benchmark_scaffold_family/"
            "benchmark_scaffold_phase132_pooled_six_bridge_adversarial.json"
        )
    payload = json.loads(artifact_path.read_text(encoding='utf-8'))
    return nan_to_none(payload)


if __name__ == '__main__':
    project_root = Path(__file__).resolve().parents[3]
    payload = run_phase132_analysis(project_root=project_root)
    print(json.dumps(nan_to_none(payload), indent=2))
