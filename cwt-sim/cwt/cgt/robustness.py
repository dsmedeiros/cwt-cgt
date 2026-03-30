from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .benchmarks import get_benchmark
from .loop_protocols import run_benchmark_loops
from .models import LoopConfig


@dataclass(frozen=True)
class RobustnessProtocol:
    name: str
    description: str
    config: LoopConfig
    filename: str
    expectation: str


_OFFCENTER_CENTERS: dict[str, tuple[tuple[float, float], ...]] = {
    'benchmark_a': ((-0.24, 0.16), (0.24, -0.16)),
    'benchmark_b': ((-0.24, -0.18), (0.24, 0.00)),
    'benchmark_c': ((-0.22, -0.18), (0.18, 0.02)),
    'benchmark_d': ((-0.03, 0.18), (0.03, 0.26)),
}


def protocol_suite(benchmark_id: str) -> list[RobustnessProtocol]:
    benchmark = get_benchmark(benchmark_id)
    offcenter = _OFFCENTER_CENTERS[benchmark_id]
    default_sides = benchmark.default_loop_side_lengths
    return [
        RobustnessProtocol(
            name='baseline_square_default',
            description='Baseline square loops at the canonical default center set.',
            config=LoopConfig(shape='square', centers=benchmark.default_loop_centers, side_lengths=default_sides),
            filename=f'{benchmark.benchmark_id}_loops_baseline_square.json',
            expectation='positive' if benchmark_id == 'benchmark_c' else 'null',
        ),
        RobustnessProtocol(
            name='heldout_circle_default',
            description='Held-out circular loops at the same center set and side ladder.',
            config=LoopConfig(shape='circle', centers=benchmark.default_loop_centers, side_lengths=default_sides),
            filename=f'{benchmark.benchmark_id}_loops_heldout_circle.json',
            expectation='positive' if benchmark_id == 'benchmark_c' else 'null',
        ),
        RobustnessProtocol(
            name='offcenter_square',
            description='Square loops shifted away from the canonical center to test spatial robustness.',
            config=LoopConfig(shape='square', centers=offcenter, side_lengths=default_sides),
            filename=f'{benchmark.benchmark_id}_loops_offcenter_square.json',
            expectation='positive' if benchmark_id == 'benchmark_c' else 'null',
        ),
        RobustnessProtocol(
            name='offcenter_circle',
            description='Held-out circular loops on the off-center set.',
            config=LoopConfig(shape='circle', centers=offcenter, side_lengths=default_sides),
            filename=f'{benchmark.benchmark_id}_loops_offcenter_circle.json',
            expectation='positive' if benchmark_id == 'benchmark_c' else 'null',
        ),
    ]


def _evaluate_payload(benchmark_id: str, payload: dict) -> dict[str, str | bool | int | float | None]:
    summary = payload['summary']
    protocol_name = summary.get('protocol_name', '')
    trusted_pairs = int(summary.get('trusted_pair_count', 0))
    sign_flip = float(summary.get('sign_flip_fraction_r1', 0.0))
    flux_fit = summary.get('fit_response_vs_signed_flux', {})
    slope = flux_fit.get('slope')
    r2 = flux_fit.get('r2')
    orientation_gap_max = float(summary.get('orientation_gap_summary', {}).get('max') or 0.0)
    center_fits = summary.get('fit_response_vs_signed_flux_by_center', [])

    if benchmark_id == 'benchmark_c' and protocol_name.startswith('offcenter_'):
        valid_centers = [item for item in center_fits if item.get('trusted_pair_count', 0) >= 2]
        center_signs = []
        center_r2s = []
        for item in valid_centers:
            fit = item.get('fit_response_vs_signed_flux', {})
            center_slope = fit.get('slope')
            center_r2 = fit.get('r2')
            if center_slope is None or abs(float(center_slope)) <= 1e-4:
                continue
            center_signs.append(1 if float(center_slope) > 0.0 else -1)
            if center_r2 is not None:
                center_r2s.append(float(center_r2))
        consistent_sign = bool(center_signs) and len(set(center_signs)) == 1
        strong_centerwise_fit = bool(center_r2s) and min(center_r2s) > 0.95
        passed = trusted_pairs >= 4 and sign_flip >= 0.75 and consistent_sign and strong_centerwise_fit
        reason = 'positive loop law persists with center-dependent local susceptibility' if passed else 'off-center protocol does not yet show a stable centerwise positive law'
    elif benchmark_id == 'benchmark_c':
        passed = trusted_pairs >= 2 and sign_flip >= 0.75 and slope is not None and abs(float(slope)) > 1e-4 and r2 is not None and float(r2) > 0.90
        reason = 'positive loop law persists under this protocol' if passed else 'positive loop law weak or not yet stable under this protocol'
    else:
        passed = trusted_pairs >= 2 and sign_flip <= 0.25 and (slope is None or abs(float(slope)) < 1e-3) and orientation_gap_max < 1e-6
        reason = 'null-like benchmark remains null under this protocol' if passed else 'null-like benchmark shows suspicious signed-loop structure'

    return {
        'passed': passed,
        'reason': reason,
        'trusted_pairs': trusted_pairs,
        'sign_flip_fraction_r1': sign_flip,
        'slope_vs_flux': None if slope is None else float(slope),
        'r2_vs_flux': None if r2 is None else float(r2),
    }


def run_robustness_suite(benchmark_id: str, output_root: Path) -> dict:
    benchmark = get_benchmark(benchmark_id)
    protocol_payloads: list[dict] = []
    protocol_reports: list[dict] = []

    for protocol in protocol_suite(benchmark_id):
        payload = run_benchmark_loops(
            benchmark_id=benchmark_id,
            output_root=output_root,
            config=protocol.config,
            protocol_name=protocol.name,
            filename=protocol.filename,
        )
        evaluation = _evaluate_payload(benchmark_id=benchmark_id, payload=payload)
        protocol_payloads.append(payload)
        protocol_reports.append(
            {
                'protocol_name': protocol.name,
                'description': protocol.description,
                'expectation': protocol.expectation,
                'filename': protocol.filename,
                'evaluation': evaluation,
                'summary': payload['summary'],
            }
        )

    suite_pass = all(item['evaluation']['passed'] for item in protocol_reports)
    payload = {
        'benchmark': benchmark.benchmark_id,
        'description': benchmark.description,
        'expected_behavior': benchmark.expected_behavior,
        'protocols': protocol_reports,
        'summary': {
            'protocol_count': len(protocol_reports),
            'passed_protocol_count': sum(1 for item in protocol_reports if item['evaluation']['passed']),
            'suite_passed': suite_pass,
        },
        'notes': [
            'Robustness protocols are held-out loop families and off-center center sets evaluated on top of the passive benchmark block.',
            'These protocols do not alter the branch geometry itself; they only change the loop family used to probe the same state manifold.',
        ],
    }

    benchmark_dir = output_root / benchmark.slug
    benchmark_dir.mkdir(parents=True, exist_ok=True)
    output_path = benchmark_dir / f'{benchmark.benchmark_id}_robustness.json'
    output_path.write_text(json.dumps(payload, indent=2))
    return payload
