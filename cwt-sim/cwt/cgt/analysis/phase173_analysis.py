"""Phase 173 analysis: Bridge LOO audit expanded to all pilots (benchmark scaffold family).

This module loads the pre-baked Phase 173 result artifact which audits the bridge
predictor rule via leave-one-out cross-validation across all four less-synthetic
pilot benchmarks: AA_less_synthetic, BB_sensor_gap, CC_delayed_release, and
DD_async_masked. Mean holdout R2 = 0.8879 with weakest benchmark BB_sensor_gap
at 0.8748, confirming uniform generalization with no outlier in the expanded
four-pilot set.
"""

from __future__ import annotations

import json
from pathlib import Path

from cwt.cgt.analysis._utils import nan_to_none


def run_phase173_analysis(project_root: Path, output_root: Path | None = None) -> dict:
    """Load and return the Phase 173 bridge LOO expanded pilots audit artifact.

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
        If the Phase 173 artifact JSON file is not found at the expected path.
    """
    project_root = Path(project_root)
    artifact_path = (
        project_root
        / 'cgt_benchmarks'
        / 'results'
        / 'benchmark_scaffold_family'
        / 'benchmark_scaffold_phase173_bridge_loo_all_pilots_expanded.json'
    )
    if not artifact_path.exists():
        raise FileNotFoundError(
            f"Phase 173 artifact not found: {artifact_path}. "
            "Expected the bridge LOO expanded pilots result at "
            "cgt_benchmarks/results/benchmark_scaffold_family/"
            "benchmark_scaffold_phase173_bridge_loo_all_pilots_expanded.json"
        )
    payload = json.loads(artifact_path.read_text(encoding='utf-8'))
    return nan_to_none(payload)


if __name__ == '__main__':
    project_root = Path(__file__).resolve().parents[3]
    payload = run_phase173_analysis(project_root=project_root)
    print(json.dumps(nan_to_none(payload), indent=2))
