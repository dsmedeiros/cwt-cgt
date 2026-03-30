from __future__ import annotations

import sys
from pathlib import Path

CODE_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = CODE_ROOT / 'src'
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from cwt.cgt.models import LoopConfig, ScanConfig
from cwt.cgt.open_system import OpenSystemConfig
from cwt.cgt.phase10_analysis import Phase10Config, phase10_payload, phase10_report


def main() -> None:
    project_root = CODE_ROOT.parents[1]
    benchmark_root = project_root / '03_benchmarks' / 'results'
    payload = phase10_payload(
        output_root=benchmark_root,
        phase10_config=Phase10Config(),
        scan_config=ScanConfig(mesh=9),
        loop_config=LoopConfig(steps_per_segment=20),
        open_config=OpenSystemConfig(scan_mesh=9, branch_steps=2),
    )
    phase10_report(benchmark_root, payload)
    print('Phase 10 artifacts generated.')


if __name__ == '__main__':
    main()
