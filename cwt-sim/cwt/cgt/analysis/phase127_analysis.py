"""Phase 127 analysis: Bridge minimal accepted theory pack (benchmark scaffold family).

This module loads the pre-baked Phase 127 result artifact which records the
bridge minimal accepted theory pack — the formal analogue to the scaffold minimal
accepted summary. The accepted rule is 'pooled_five_bridge_positive_plus_compactness_corrected_adversarial',
covering positive and adversarial transfer across all five bridge benchmarks T,
U, V, W, X. This artifact is the governance record confirming the bridge lane
has reached its first minimal accepted state.
Verdict: bridge_minimal_theory_pack_written.
"""

from __future__ import annotations

import json
from pathlib import Path

from cwt.cgt.analysis._utils import nan_to_none


def run_phase127_analysis(project_root: Path, output_root: Path | None = None) -> dict:
    """Load and return the Phase 127 bridge minimal accepted theory pack artifact.

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
        If the Phase 127 artifact JSON file is not found at the expected path.
    """
    project_root = Path(project_root)
    artifact_path = (
        project_root
        / 'cgt_benchmarks'
        / 'results'
        / 'benchmark_scaffold_family'
        / 'benchmark_scaffold_phase127_bridge_minimal_accepted_theory_pack.json'
    )
    if not artifact_path.exists():
        raise FileNotFoundError(
            f"Phase 127 artifact not found: {artifact_path}. "
            "Expected the bridge minimal accepted theory pack result at "
            "cgt_benchmarks/results/benchmark_scaffold_family/"
            "benchmark_scaffold_phase127_bridge_minimal_accepted_theory_pack.json"
        )
    payload = json.loads(artifact_path.read_text(encoding='utf-8'))
    return nan_to_none(payload)


if __name__ == '__main__':
    project_root = Path(__file__).resolve().parents[3]
    payload = run_phase127_analysis(project_root=project_root)
    print(json.dumps(nan_to_none(payload), indent=2))
