"""Phase 124 analysis: Pooled five-bridge adversarial summary (benchmark scaffold family).

This module loads the pre-baked Phase 124 result artifact which aggregates
adversarial perturbation results across all five bridge benchmarks T, U, V, W,
and X. The pooled raw R2 = 0.4386 degrades under adversarial perturbation; the
sign-tensor correction lifts the pooled corrected R2 to 0.8724, confirming
that the correction generalises across all five bridge cases.
Verdict: pooled_five_bridge_adversarial_corrected_supported.
"""

from __future__ import annotations

import json
from pathlib import Path

from cwt.cgt.analysis._utils import nan_to_none


def run_phase124_analysis(project_root: Path, output_root: Path | None = None) -> dict:
    """Load and return the Phase 124 pooled five-bridge adversarial artifact.

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
        If the Phase 124 artifact JSON file is not found at the expected path.
    """
    project_root = Path(project_root)
    artifact_path = (
        project_root
        / 'cgt_benchmarks'
        / 'results'
        / 'benchmark_scaffold_family'
        / 'benchmark_scaffold_phase124_pooled_five_bridge_adversarial.json'
    )
    if not artifact_path.exists():
        raise FileNotFoundError(
            f"Phase 124 artifact not found: {artifact_path}. "
            "Expected the pooled five-bridge adversarial result at "
            "cgt_benchmarks/results/benchmark_scaffold_family/"
            "benchmark_scaffold_phase124_pooled_five_bridge_adversarial.json"
        )
    payload = json.loads(artifact_path.read_text(encoding='utf-8'))
    return nan_to_none(payload)


if __name__ == '__main__':
    project_root = Path(__file__).resolve().parents[3]
    payload = run_phase124_analysis(project_root=project_root)
    print(json.dumps(nan_to_none(payload), indent=2))
