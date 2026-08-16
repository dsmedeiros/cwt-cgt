from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

CWT_SIM_ROOT = Path(__file__).resolve().parents[3]
if str(CWT_SIM_ROOT) not in sys.path:
    sys.path.insert(0, str(CWT_SIM_ROOT))

DEFAULT_S_BARS = "0.99,0.95,0.90,0.88,0.84"
DEFAULT_RESPONSES = "1.00,0.95,0.81,-0.20,-0.45"


def _parse_floats(raw: str) -> list[float]:
    return [float(part.strip()) for part in raw.split(",") if part.strip()]


def main() -> None:
    from cwt.metrics.eval_curves import log_log_slope, noise_threshold_report

    parser = argparse.ArgumentParser(
        description=(
            "Summarize supplied phase-noise values. This utility does not load or verify "
            "an external dataset; its defaults are illustrative synthetic numbers."
        )
    )
    parser.add_argument(
        "--s-bars",
        default=DEFAULT_S_BARS,
        help="Comma-separated coherence values; the default is illustrative synthetic data.",
    )
    parser.add_argument(
        "--responses",
        default=DEFAULT_RESPONSES,
        help="Comma-separated responses; the default is illustrative synthetic data.",
    )
    parser.add_argument("--mild-s-bar-floor", type=float, default=0.95)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    s_bars = _parse_floats(args.s_bars)
    responses = _parse_floats(args.responses)
    report = noise_threshold_report(
        s_bars,
        responses,
        mild_s_bar_floor=args.mild_s_bar_floor,
    )
    mild_pairs = [
        (s_bar, abs(response)) for s_bar, response in zip(s_bars, responses) if s_bar >= args.mild_s_bar_floor
    ]
    slope = log_log_slope(
        [item[0] for item in mild_pairs],
        [item[1] for item in mild_pairs],
    )
    payload = {
        "input_provenance": (
            "illustrative_synthetic_defaults"
            if args.s_bars == DEFAULT_S_BARS and args.responses == DEFAULT_RESPONSES
            else "unverified_cli_values"
        ),
        "is_external_evidence": False,
        "evidence_limit": "No dataset manifest or external result artifact is loaded by this script.",
        "noise_threshold": report,
        "mild_noise_log_log_slope": slope,
    }
    text = json.dumps(payload, indent=2)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
