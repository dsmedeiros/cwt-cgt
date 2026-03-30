from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable


def _fmt(value, digits: int = 6) -> str:
    if value is None:
        return 'None'
    if isinstance(value, bool):
        return 'true' if value else 'false'
    if isinstance(value, int):
        return str(value)
    try:
        numeric = float(value)
    except Exception:
        return str(value)
    if abs(numeric) >= 1e4 or (0 < abs(numeric) < 1e-4):
        return f'{numeric:.{digits}e}'
    return f'{numeric:.{digits}f}'


def load_json(path: Path) -> dict:
    with path.open() as fh:
        return json.load(fh)


def evaluate_benchmark(scan: dict, loops: dict) -> dict[str, str | bool]:
    benchmark = scan['benchmark']
    summary = loops['summary']
    trusted_pairs = int(summary.get('trusted_pair_count', 0))
    sign_flip = float(summary.get('sign_flip_fraction_r1', 0.0))
    flux_fit = summary.get('fit_response_vs_signed_flux', {})
    slope = flux_fit.get('slope')
    r2 = flux_fit.get('r2')
    orientation_gap_max = float(summary.get('orientation_gap_summary', {}).get('max') or 0.0)

    if benchmark == 'benchmark_c':
        passed = trusted_pairs >= 2 and sign_flip >= 0.75 and slope is not None and abs(float(slope)) > 1e-4 and r2 is not None and float(r2) > 0.95
        reason = 'positive signed-loop benchmark' if passed else 'positive benchmark not yet convincing'
    else:
        passed = trusted_pairs >= 2 and sign_flip <= 0.25 and (slope is None or abs(float(slope)) < 1e-3) and orientation_gap_max < 1e-6
        reason = 'null benchmark remains null-like' if passed else 'null benchmark shows suspicious loop structure'

    return {
        'passed': passed,
        'reason': reason,
        'trusted_pairs': trusted_pairs,
        'sign_flip_fraction_r1': sign_flip,
    }


def _branch_summary_text(scan: dict) -> str:
    branch = scan.get('branch_continuation', {})
    counts = branch.get('persistent_branch_counts', {})
    switch_count = int(branch.get('switch_tile_count', 0))
    if not counts:
        return 'No branch atlas metadata recorded.'
    counts_text = ', '.join(f'{key}:{value}' for key, value in sorted(counts.items()))
    return f'Persistent branch counts = {counts_text}. Ambiguous/switch tiles = {switch_count}.'


def _relative_image(report_path: Path, image_path: Path, alt_text: str) -> str:
    rel = Path(__import__('os').path.relpath(image_path, start=report_path.parent))
    return f'![{alt_text}]({rel.as_posix()})'


def write_benchmark_report(scan: dict, loops: dict, plots: dict[str, str], output_path: Path) -> dict[str, str | bool]:
    evaluation = evaluate_benchmark(scan, loops)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    metric = scan.get('metric_summary', {})
    curvature = scan.get('curvature_summary', {})
    regimes = scan.get('regime_summary', {})
    loop_summary = loops.get('summary', {})

    lines: list[str] = []
    lines.append(f"# {scan['benchmark']} benchmark report")
    lines.append('')
    lines.append(f"**Description:** {scan['description']}")
    lines.append(f"**Expected behavior:** {scan['expected_behavior']}")
    lines.append(f"**Observed verdict:** {'PASS' if evaluation['passed'] else 'REVIEW'} — {evaluation['reason']}")
    lines.append('')
    lines.append('## Scan summary')
    lines.append('')
    lines.append(f"- Regimes: {', '.join(f'{k}:{v}' for k, v in sorted(regimes.items()))}")
    lines.append(f"- Metric trace max/mean: {_fmt(metric.get('max'))} / {_fmt(metric.get('mean'))}")
    lines.append(f"- Curvature |F| max/mean: {_fmt(curvature.get('max'))} / {_fmt(curvature.get('mean'))}")
    lines.append(f"- Branch atlas: {_branch_summary_text(scan)}")
    lines.append('')
    lines.append('## Loop summary')
    lines.append('')
    lines.append(f"- Trusted pair count: {_fmt(loop_summary.get('trusted_pair_count'))}")
    lines.append(f"- Excluded pair count: {_fmt(loop_summary.get('excluded_pair_count'))}")
    lines.append(f"- Sign-flip fraction (R1): {_fmt(loop_summary.get('sign_flip_fraction_r1'))}")
    lines.append(f"- Fit slope vs signed flux: {_fmt(loop_summary.get('fit_response_vs_signed_flux', {}).get('slope'))}")
    lines.append(f"- Fit R² vs signed flux: {_fmt(loop_summary.get('fit_response_vs_signed_flux', {}).get('r2'))}")
    lines.append(f"- Orientation-gap max: {_fmt(loop_summary.get('orientation_gap_summary', {}).get('max'))}")
    lines.append('')
    lines.append('## Generated plots')
    lines.append('')

    ordered = [
        ('metric_heatmap', 'metric heatmap'),
        ('curvature_heatmap', 'curvature heatmap'),
        ('coherence_heatmap', 'coherence heatmap'),
        ('overlap_heatmap', 'overlap heatmap'),
        ('softness_heatmap', 'softness heatmap'),
        ('regime_map', 'regime map'),
        ('branch_map', 'branch map'),
        ('response_vs_flux', 'response vs signed flux'),
        ('response_vs_area', 'response vs signed area'),
        ('orientation_gap', 'orientation gap'),
    ]
    for key, alt in ordered:
        if key in plots:
            lines.append(_relative_image(output_path, Path(plots[key]), alt))
            lines.append('')

    output_path.write_text('\n'.join(lines))
    return evaluation


def write_aggregate_report(scans: Iterable[dict], loops_list: Iterable[dict], evaluations: dict[str, dict], output_path: Path) -> None:
    scans = list(scans)
    loops_by_id = {loops['benchmark']: loops for loops in loops_list}
    output_path.parent.mkdir(parents=True, exist_ok=True)

    lines: list[str] = []
    lines.append('# CWT-CGT benchmark acceptance report')
    lines.append('')
    lines.append('This report is generated from the current benchmark JSON artifacts and the plot/report automation layer.')
    lines.append('')
    for scan in scans:
        benchmark = scan['benchmark']
        loops = loops_by_id[benchmark]
        evaluation = evaluations[benchmark]
        summary = loops['summary']
        lines.append(f"## {benchmark}")
        lines.append('')
        lines.append(f"- Verdict: {'PASS' if evaluation['passed'] else 'REVIEW'} — {evaluation['reason']}")
        lines.append(f"- Regimes: {', '.join(f'{k}:{v}' for k, v in sorted(scan.get('regime_summary', {}).items()))}")
        lines.append(f"- Trusted pairs: {_fmt(summary.get('trusted_pair_count'))}")
        lines.append(f"- Sign-flip fraction (R1): {_fmt(summary.get('sign_flip_fraction_r1'))}")
        lines.append(f"- Flux-fit slope / R²: {_fmt(summary.get('fit_response_vs_signed_flux', {}).get('slope'))} / {_fmt(summary.get('fit_response_vs_signed_flux', {}).get('r2'))}")
        lines.append('')

    output_path.write_text('\n'.join(lines))
