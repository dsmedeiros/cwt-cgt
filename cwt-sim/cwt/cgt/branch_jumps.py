from __future__ import annotations

import json
from pathlib import Path

from ._geom_compat import summarize, summarize_abs
from .benchmarks import get_benchmark
from .loop_protocols import run_benchmark_loops
from .models import LoopConfig, ScanConfig
from .runner import run_benchmark_scan


def branch_jump_payload(
    benchmark_id: str,
    output_root: Path,
    scan_config: ScanConfig | None = None,
    loop_config: LoopConfig | None = None,
) -> dict:
    benchmark = get_benchmark(benchmark_id)
    scan_payload = run_benchmark_scan(benchmark_id, output_root=output_root, config=scan_config)
    loop_payload = run_benchmark_loops(benchmark_id, output_root=output_root, config=loop_config)

    pair_rows = []
    for pair in loop_payload["pair_results"]:
        pair_rows.append(
            {
                "center": pair["center"],
                "side_length": float(pair["side_length"]),
                "pair_trusted_r1": bool(pair["pair_trusted_r1"]),
                "pair_r4": bool(pair["pair_r4"]),
                "switch_count_total": int(pair["switch_count_total"]),
                "net_branch_jump_difference": float(pair["net_branch_jump_difference"]),
                "orientation_gap": float(pair["orientation_gap"]),
                "excluded_reason": pair["excluded_reason"],
                "ccw_branch_ids": pair["ccw"]["unique_branch_ids"],
                "cw_branch_ids": pair["cw"]["unique_branch_ids"],
                "ccw_dwell": pair["ccw"]["branch_dwell_fractions"],
                "cw_dwell": pair["cw"]["branch_dwell_fractions"],
            }
        )

    trusted = [row for row in pair_rows if row["pair_trusted_r1"]]
    excluded = [row for row in pair_rows if not row["pair_trusted_r1"]]
    atlas = scan_payload["branch_continuation"]
    payload = {
        "benchmark": benchmark.benchmark_id,
        "description": benchmark.description,
        "scan_branch_atlas": {
            "persistent_branch_counts": atlas["persistent_branch_counts"],
            "chosen_branch_counts": atlas["chosen_branch_counts"],
            "switch_tile_count": atlas["switch_tile_count"],
            "ambiguous_tile_count": atlas["ambiguous_tile_count"],
            "residual_summary": atlas["residual_summary"],
            "ambiguity_score_summary": atlas["ambiguity_score_summary"],
        },
        "pair_rows": pair_rows,
        "summary": {
            "pair_count": int(len(pair_rows)),
            "trusted_pair_count": int(len(trusted)),
            "excluded_pair_count": int(len(excluded)),
            "r4_pair_count": int(sum(1 for row in pair_rows if row["pair_r4"])),
            "switch_count_total_summary": summarize(row["switch_count_total"] for row in pair_rows),
            "net_branch_jump_difference_summary": summarize(
                row["net_branch_jump_difference"] for row in pair_rows
            ),
            "orientation_gap_summary": summarize_abs(row["orientation_gap"] for row in pair_rows),
        },
        "notes": [
            "Branch-jump observables are primary in benchmark F: they are meant to expose switching and"
            " exclusion, not a positive signed-flux law.",
            "Trusted pairs should remain null-like while excluded pairs localize near the explicit"
            " R4/hysteretic band.",
        ],
    }
    out_dir = output_root / benchmark.slug
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"{benchmark.benchmark_id}_branch_jumps.json").write_text(json.dumps(payload, indent=2))
    return payload
