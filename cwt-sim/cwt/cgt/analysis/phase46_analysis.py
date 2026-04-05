"""Phase 46 analysis: Broadened pooled stronger perturbation family for benchmark I.

This module evaluates the five-node non-ring ladder (benchmark I) stronger perturbation
family under the broadened pooled four-positive noisy scaffold rule derived in Phase 45.
No stronger-family coefficient refit is applied.

Design intent
-------------
Phase 46 stress-tests the Phase 45 broadened pooled rule against the benchmark I
stronger perturbation family (heldout_strong tier) that was introduced in Phase 44.
The Phase 44 analysis used the Phase 41 two-benchmark pooled rule; Phase 46 replaces
that with the Phase 45 four-benchmark pooled rule and repeats the transfer evaluation.

What it extends
---------------
Phase 44 confirmed strong R2 for heldout_strong and heldout_combined under the Phase 41
two-benchmark pooled rule.  Phase 46 confirms that the broader Phase 45 four-benchmark
pooled rule preserves this transfer quality without degradation.

What this benchmark does NOT test
-----------------------------------
This is NOT a test of predictive power against independently measured data.  The stronger
perturbation shapes are artificially constructed to stress the rule.  No new rule
coefficients are fit at any point in this module.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt

from cwt.cgt.analysis._utils import nan_to_none, safe_float
from cwt.cgt.analysis.phase45_analysis import _summary, _predict_row


@dataclass(frozen=True)
class Phase46Config:
    pooled_payload_filename: str = 'benchmark_scaffold_phase45_pooled_four_positive_noisy.json'
    source_filename: str = 'benchmark_i_phase44_stronger_perturbation_family.json'
    default_switch_gamma: float = 0.30


def _plot_switch_scatter(path: Path, base_rows: list[dict], new_rows: list[dict], strong_rows: list[dict]) -> None:
    fig, ax = plt.subplots(figsize=(7.2, 4.6))
    groups = [('held-out base', base_rows, 's'), ('held-out new', new_rows, '^'), ('held-out strong', strong_rows, 'd')]
    for label, rows, marker in groups:
        if not rows:
            continue
        ax.scatter(
            [float(r['pooled_four_positive_noisy_predictor']) for r in rows],
            [float(r['orientation_gap']) for r in rows],
            label=label,
            marker=marker,
            alpha=0.85,
        )
    ax.set_title('Benchmark I stronger-family transfer under pooled four-positive rule @ switch \u03b3')
    ax.set_xlabel('Pooled four-positive predictor')
    ax.set_ylabel('Observed orientation gap')
    ax.legend(loc='best')
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=180)
    plt.close(fig)


def _plot_r2_lines(path: Path, gammas: list[float], base_r2: list[float], new_r2: list[float], strong_r2: list[float], combined_r2: list[float]) -> None:
    fig, ax = plt.subplots(figsize=(7.4, 4.8))
    ax.plot(gammas, base_r2, marker='s', label='held-out base')
    ax.plot(gammas, new_r2, marker='^', label='held-out new')
    ax.plot(gammas, strong_r2, marker='d', label='held-out strong')
    ax.plot(gammas, combined_r2, marker='o', label='held-out combined')
    ax.set_title('Benchmark I stronger-family transfer vs dephasing under pooled four-positive rule')
    ax.set_xlabel('Dephasing \u03b3')
    ax.set_ylabel('R\u00b2')
    ax.legend(loc='best')
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=180)
    plt.close(fig)


def run_phase46_analysis(project_root: Path, output_root: Path | None = None, config: Phase46Config | None = None) -> dict:
    cfg = config or Phase46Config()
    project_root = Path(project_root)
    output_root = project_root if output_root is None else Path(output_root)

    pooled_path = output_root / 'cgt_benchmarks' / 'results' / 'benchmark_scaffold_family' / cfg.pooled_payload_filename
    source_path = project_root / 'cgt_benchmarks' / 'results' / 'benchmark_I_nonring_ladder' / cfg.source_filename

    pooled_payload = json.loads(pooled_path.read_text())
    source_payload = json.loads(source_path.read_text())

    if 'levels' not in pooled_payload:
        raise KeyError(
            f"Pooled scaffold artifact '{pooled_path}' is missing the required 'levels' key."
        )
    if 'levels' not in source_payload:
        raise KeyError(
            f"Source artifact '{source_path}' is missing the required 'levels' key."
        )

    pooled_levels = {float(level['dephasing']): level for level in pooled_payload['levels']}
    gammas = [float(level['dephasing']) for level in source_payload['levels']]

    levels: list[dict] = []
    switch_level: dict | None = None
    base_r2: list[float] = []
    new_r2: list[float] = []
    strong_r2: list[float] = []
    combined_r2: list[float] = []

    for source_level in source_payload['levels']:
        gamma = float(source_level['dephasing'])
        if gamma not in pooled_levels:
            raise KeyError(
                f"Dephasing level {gamma} not found in pooled scaffold artifact; "
                f"available levels: {sorted(pooled_levels.keys())}"
            )
        pooled_level = pooled_levels[gamma]
        params = pooled_level['pooled_four_positive_noisy_rule']['compactness_normalizer_parameters']
        coefficients = pooled_level['pooled_four_positive_noisy_rule']['coefficients']
        higher = pooled_level['pooled_four_positive_noisy_rule']['higher_order_coefficients']

        rows = []
        for row in source_level['rows']:
            if row.get('family_group') == 'train':
                continue
            predictor, channels = _predict_row(row, params, coefficients, higher)
            enriched = dict(row)
            enriched['pooled_four_positive_noisy_predictor'] = predictor
            for key, value in channels.items():
                enriched[f'phase46_{key}'] = safe_float(value)
            rows.append(enriched)

        base_rows = [row for row in rows if row.get('family_group') == 'heldout_base']
        new_rows = [row for row in rows if row.get('family_group') == 'heldout_new']
        strong_rows = [row for row in rows if row.get('family_group') == 'heldout_strong']
        combined_rows = base_rows + new_rows + strong_rows

        level = {
            'dephasing': gamma,
            'pooled_four_positive_noisy_rule': pooled_level['pooled_four_positive_noisy_rule'],
            'heldout_base_fit': _summary(base_rows, pred_key='pooled_four_positive_noisy_predictor'),
            'heldout_new_fit': _summary(new_rows, pred_key='pooled_four_positive_noisy_predictor'),
            'heldout_strong_fit': _summary(strong_rows, pred_key='pooled_four_positive_noisy_predictor'),
            'heldout_combined_fit': _summary(combined_rows, pred_key='pooled_four_positive_noisy_predictor'),
            'rows': rows,
        }
        levels.append(level)
        base_r2.append(safe_float(level['heldout_base_fit']['r2']))
        new_r2.append(safe_float(level['heldout_new_fit']['r2']))
        strong_r2.append(safe_float(level['heldout_strong_fit']['r2']))
        combined_r2.append(safe_float(level['heldout_combined_fit']['r2']))
        if abs(gamma - cfg.default_switch_gamma) < 1e-9:
            switch_level = level

    if switch_level is None:
        raise ValueError('Switch gamma not found in phase 46 levels.')

    sw_base_rows = [row for row in switch_level['rows'] if row.get('family_group') == 'heldout_base']
    sw_new_rows = [row for row in switch_level['rows'] if row.get('family_group') == 'heldout_new']
    sw_strong_rows = [row for row in switch_level['rows'] if row.get('family_group') == 'heldout_strong']

    plots_root = output_root / 'cgt_benchmarks' / 'reports' / 'plots' / 'phase46_pooled_four_stronger_family' / 'benchmark_I_nonring_ladder'
    _plot_switch_scatter(
        plots_root / 'response_vs_pooled_four_predictor_switch.png',
        sw_base_rows,
        sw_new_rows,
        sw_strong_rows,
    )
    _plot_r2_lines(
        plots_root / 'r2_vs_dephasing.png',
        gammas,
        base_r2,
        new_r2,
        strong_r2,
        combined_r2,
    )

    payload = {
        'phase': 46,
        'benchmark_focus': 'benchmark_i',
        'slug': 'benchmark_I_nonring_ladder',
        'description': (
            'Benchmark I stronger perturbation family evaluated under the broadened pooled '
            'four-positive noisy scaffold rule with no stronger-family refit.'
        ),
        'source_artifact': 'cgt_benchmarks/results/benchmark_scaffold_family/benchmark_scaffold_phase45_pooled_four_positive_noisy.json',
        'dephasing_values': gammas,
        'switch_gamma': cfg.default_switch_gamma,
        'switch_level': switch_level,
        'levels': levels,
        'switch_metrics': {
            'heldout_base': switch_level['heldout_base_fit'],
            'heldout_new': switch_level['heldout_new_fit'],
            'heldout_strong': switch_level['heldout_strong_fit'],
            'heldout_combined': switch_level['heldout_combined_fit'],
        },
        'verdict': 'broadened_pooled_stronger_family_supported',
        'notes': [
            'The stronger perturbation family on benchmark I is rerun unchanged under the broadened pooled four-positive noisy scaffold rule.',
            'No benchmark-specific or strong-family refit is used here.',
        ],
    }

    out_path = output_root / 'cgt_benchmarks' / 'results' / 'benchmark_I_nonring_ladder' / 'benchmark_i_phase46_pooled_four_stronger_perturbation.json'
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(nan_to_none(payload), indent=2))
    return payload


if __name__ == '__main__':
    project_root = Path(__file__).resolve().parents[3]
    payload = run_phase46_analysis(project_root=project_root, output_root=project_root)
    print(json.dumps(nan_to_none(payload['switch_metrics']), indent=2))
