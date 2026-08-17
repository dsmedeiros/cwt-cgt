"""Non-authoritative live-core regression for the frozen local C0 formulas."""

from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np

from cwt.cgt.benchmarks import get_benchmark

from .bc3_primitives import frozen_c0_branch
from .contract import MODEL_CONTRACT, ConstitutiveMap3DContract

SIM_ROOT = Path(__file__).resolve().parents[2]
AUTHORED_PREDECESSOR_RELATIVE_PATH = "cwt/cgt/benchmarks.py"
REVIEWED_AUTHORED_PREDECESSOR_SHA256 = "eb713c61cb8b860c7011f823cdd4f531ba6dace5a63c1d306c6c5b7e974ef6d0"


def authored_predecessor_identity() -> dict[str, object]:
    path = SIM_ROOT.joinpath(*AUTHORED_PREDECESSOR_RELATIVE_PATH.split("/"))
    raw = path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        raise RuntimeError("authored predecessor unexpectedly contains a BOM")
    text = raw.decode("utf-8").replace("\r\n", "\n")
    if "\r" in text:
        raise RuntimeError("authored predecessor unexpectedly contains bare CR")
    actual = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return {
        "role": "authored_Benchmark_C_predecessor_only",
        "relative_path": AUTHORED_PREDECESSOR_RELATIVE_PATH,
        "hash_domain": "sha256_utf8_lf_v1",
        "sha256": actual,
        "reviewed_sha256": REVIEWED_AUTHORED_PREDECESSOR_SHA256,
        "authenticated": actual == REVIEWED_AUTHORED_PREDECESSOR_SHA256,
        "live_core_sample_comparison_is_acceptance": False,
    }


def live_core_sample_regression(
    contract: ConstitutiveMap3DContract = MODEL_CONTRACT,
) -> dict[str, object]:
    """Compare four samples only; this function owns no theorem acceptance gate."""

    benchmark = get_benchmark(contract.bc3_benchmark_id)
    points = ((0.05, 0.05), (0.10, 0.10), (0.12, 0.08), (0.15, 0.15))
    maximum = 0.0
    for u, v in points:
        candidate = benchmark.resolve_candidate_by_id(u, v, contract.bc3_branch_id)
        if candidate is None:
            raise RuntimeError("live core Benchmark-C C0 branch is absent")
        probability, theta, kernel = frozen_c0_branch(u, v, contract)
        maximum = max(
            maximum,
            float(np.max(np.abs(candidate.state.p - probability))),
            float(np.max(np.abs(candidate.state.theta - theta))),
            float(np.max(np.abs(candidate.state.kernel - kernel))),
        )
    return {
        "sample_points": [list(point) for point in points],
        "maximum_core_error": maximum,
        "acceptance_authority": False,
        "scope": "finite_live_core_regression_only_not_uniform_equivalence",
    }
