from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

CWT_SIM_ROOT = Path(__file__).resolve().parents[3]
if str(CWT_SIM_ROOT) not in sys.path:
    sys.path.insert(0, str(CWT_SIM_ROOT))


def _parse_floats(raw: str) -> list[float]:
    return [float(part.strip()) for part in raw.split(",") if part.strip()]


def main() -> None:
    from cwt.metrics.eval_curves import (
        orientation_antisymmetry_statistic,
        scramble_response_summary,
    )

    parser = argparse.ArgumentParser(description="Summarize phase-kick scramble ablations.")
    parser.add_argument("--baseline-ccw", default="0.40,0.30")
    parser.add_argument("--baseline-cw", default="-0.40,-0.30")
    parser.add_argument("--a-zero-ccw", default="0.01,0.00")
    parser.add_argument("--a-zero-cw", default="-0.01,0.00")
    parser.add_argument("--a-signflip-ccw", default="-0.40,-0.30")
    parser.add_argument("--a-signflip-cw", default="0.40,0.30")
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    baseline_ccw = _parse_floats(args.baseline_ccw)
    baseline_cw = _parse_floats(args.baseline_cw)
    a_zero_ccw = _parse_floats(args.a_zero_ccw)
    a_zero_cw = _parse_floats(args.a_zero_cw)
    a_signflip_ccw = _parse_floats(args.a_signflip_ccw)
    a_signflip_cw = _parse_floats(args.a_signflip_cw)
    payload = {
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
