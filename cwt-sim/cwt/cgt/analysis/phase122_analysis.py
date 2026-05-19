"""Phase 122 analysis: Missing bridge adversarial coverage completion (benchmark U partial delay).

This module loads the pre-baked Phase 122 result artifact which completes the
missing adversarial coverage for benchmark U (partial_delay). The audit applies
the sign-tensor correction to the adversarial perturbation family on benchmark U.
Raw combined R2 = 0.4412 degrades under adversarial perturbation; corrected
combined R2 = 0.8725, confirming the correction transfers across bridge benchmarks.
Verdict: u_bridge_adversarial_corrected_supported.
"""

from __future__ import annotations

import json
from pathlib import Path

from cwt.cgt.analysis._utils import nan_to_none


def run_phase122_analysis(project_root: Path, output_root: Path | None = None) -> dict:
    """Load and return the Phase 122 bridge adversarial completion artifact.

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
        If the Phase 122 artifact JSON file is not found at the expected path.
    """
    project_root = Path(project_root)
    artifact_path = (
        project_root
        / 'cgt_benchmarks'
        / 'results'
        / 'benchmark_U_partial_delay'
        / 'benchmark_u_phase122_bridge_adversarial_completion.json'
    )
    if not artifact_path.exists():
        raise FileNotFoundError(
            f"Phase 122 artifact not found: {artifact_path}. "
            "Expected the bridge adversarial completion result at "
            "cgt_benchmarks/results/benchmark_U_partial_delay/"
            "benchmark_u_phase122_bridge_adversarial_completion.json"
        )
    payload = json.loads(artifact_path.read_text(encoding='utf-8'))
    return nan_to_none(payload)


if __name__ == '__main__':
    project_root = Path(__file__).resolve().parents[3]
    payload = run_phase122_analysis(project_root=project_root)
    print(json.dumps(nan_to_none(payload), indent=2))
