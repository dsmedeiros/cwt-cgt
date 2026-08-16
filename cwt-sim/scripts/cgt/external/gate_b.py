from __future__ import annotations

import sys
from pathlib import Path

PROVENANCE_WARNING = (
    "WARNING: gate_b.py dispatches the repository's synthetic/generated Gate B "
    "experiment. It does not ingest or validate an external dataset."
)

CWT_SIM_ROOT = Path(__file__).resolve().parents[3]
if str(CWT_SIM_ROOT) not in sys.path:
    sys.path.insert(0, str(CWT_SIM_ROOT))


def _warn_synthetic_wrapper() -> None:
    print(PROVENANCE_WARNING, file=sys.stderr)


if __name__ == "__main__":
    from experiments.gateB_ridge_finder.run import main

    _warn_synthetic_wrapper()
    main()
