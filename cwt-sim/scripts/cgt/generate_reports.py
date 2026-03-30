from __future__ import annotations

import sys
from pathlib import Path

CODE_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = CODE_ROOT / 'src'
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from cwt.cgt.benchmarks import BENCHMARKS
from cwt.cgt.models import LoopConfig, ScanConfig
from cwt.cgt.plotting import generate_benchmark_plots
from cwt.cgt.reporting import write_aggregate_report, write_benchmark_report
from cwt.cgt.runner import run_benchmark_all


def main() -> None:
    project_root = CODE_ROOT.parent
    results_root = project_root / '03_benchmarks' / 'results'
    reports_root = project_root / '05_reports'
    plots_root = reports_root / 'plots'
    benchmark_reports_root = reports_root / 'benchmark_reports'

    scans = []
    loops_list = []
    evaluations = {}

    for benchmark_id in BENCHMARKS:
        payloads = run_benchmark_all(
            benchmark_id=benchmark_id,
            output_root=results_root,
            scan_config=ScanConfig(mesh=9),
            loop_config=LoopConfig(),
        )
        scan = payloads['scan']
        loops = payloads['loops']
        scans.append(scan)
        loops_list.append(loops)

        slug = BENCHMARKS[benchmark_id].slug
        plot_artifacts = generate_benchmark_plots(scan=scan, loops=loops, output_dir=plots_root / slug)
        report_path = benchmark_reports_root / f'{benchmark_id}_report.md'
        evaluations[benchmark_id] = write_benchmark_report(scan=scan, loops=loops, plots=plot_artifacts, output_path=report_path)
        print(f'generated {benchmark_id} -> {report_path}')

    write_aggregate_report(
        scans=scans,
        loops_list=loops_list,
        evaluations=evaluations,
        output_path=reports_root / 'CWT-CGT_Benchmark_Acceptance_Report.md',
    )
    print('aggregate report written')


if __name__ == '__main__':
    main()
