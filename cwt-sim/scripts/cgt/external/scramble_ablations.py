from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

CWT_SIM_ROOT = Path(__file__).resolve().parents[3]
if str(CWT_SIM_ROOT) not in sys.path:
    sys.path.insert(0, str(CWT_SIM_ROOT))

DEFAULT_VECTORS = {
    "baseline_ccw": "0.40,0.30",
    "baseline_cw": "-0.40,-0.30",
    "a_zero_ccw": "0.01,0.00",
    "a_zero_cw": "-0.01,0.00",
    "a_signflip_ccw": "-0.40,-0.30",
    "a_signflip_cw": "0.40,0.30",
}


def _parse_floats(raw: str) -> list[float]:
    return [float(part.strip()) for part in raw.split(",") if part.strip()]


def main() -> None:
    from cwt.metrics.eval_curves import (
        orientation_antisymmetry_statistic,
        scramble_response_summary,
    )

    parser = argparse.ArgumentParser(
        description=(
            "Summarize supplied phase-kick scramble vectors. This utility does not load "
            "or verify an external dataset; its defaults are illustrative synthetic values."
        )
    )
    parser.add_argument("--baseline-ccw", default=DEFAULT_VECTORS["baseline_ccw"])
    parser.add_argument("--baseline-cw", default=DEFAULT_VECTORS["baseline_cw"])
    parser.add_argument("--a-zero-ccw", default=DEFAULT_VECTORS["a_zero_ccw"])
    parser.add_argument("--a-zero-cw", default=DEFAULT_VECTORS["a_zero_cw"])
    parser.add_argument("--a-signflip-ccw", default=DEFAULT_VECTORS["a_signflip_ccw"])
    parser.add_argument("--a-signflip-cw", default=DEFAULT_VECTORS["a_signflip_cw"])
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    baseline_ccw = _parse_floats(args.baseline_ccw)
    baseline_cw = _parse_floats(args.baseline_cw)
    a_zero_ccw = _parse_floats(args.a_zero_ccw)
    a_zero_cw = _parse_floats(args.a_zero_cw)
    a_signflip_ccw = _parse_floats(args.a_signflip_ccw)
    a_signflip_cw = _parse_floats(args.a_signflip_cw)
    raw_vectors = {
        "baseline_ccw": args.baseline_ccw,
        "baseline_cw": args.baseline_cw,
        "a_zero_ccw": args.a_zero_ccw,
        "a_zero_cw": args.a_zero_cw,
        "a_signflip_ccw": args.a_signflip_ccw,
        "a_signflip_cw": args.a_signflip_cw,
    }
    payload = {
        "input_provenance": (
            "illustrative_synthetic_defaults" if raw_vectors == DEFAULT_VECTORS else "unverified_cli_values"
        ),
        "is_external_evidence": False,
        "evidence_limit": "No dataset manifest or external result artifact is loaded by this script.",
        "baseline_antisymmetry": orientation_antisymmetry_statistic(
            baseline_ccw,
            baseline_cw,
        ),
        "scramble_summary": scramble_response_summary(
            baseline_ccw,
            baseline_cw,
            a_zero_ccw,
            a_zero_cw,
            a_signflip_ccw,
            a_signflip_cw,
        ),
    }
    text = json.dumps(payload, indent=2)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
