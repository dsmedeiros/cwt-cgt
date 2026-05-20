from __future__ import annotations

import sys
from pathlib import Path

CWT_SIM_ROOT = Path(__file__).resolve().parents[3]
if str(CWT_SIM_ROOT) not in sys.path:
    sys.path.insert(0, str(CWT_SIM_ROOT))

if __name__ == "__main__":
    from experiments.gateB_ridge_finder.run import main

    main()
