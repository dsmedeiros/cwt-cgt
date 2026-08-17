"""Independently sealed BC3 midpoint and center-form prediction intervals."""

from __future__ import annotations

from .bc3_interval_model import midpoint_line_interval
from .bc3_lattice import exact_lattice, lattice_certificate
from .benchmark_c_alpha import directed_form_intervals
from .contract import MODEL_CONTRACT, ConstitutiveMap3DContract


def locked_midpoint_predictions(
    contract: ConstitutiveMap3DContract = MODEL_CONTRACT,
) -> dict[str, object]:
    """Build response-blind intervals before an oracle capability exists."""

    center = directed_form_intervals(
        contract.bc3_heldout_center[0],
        contract.bc3_heldout_center[1],
        contract.bc3_heldout_center[2],
        contract.bc3_gain,
    )["heldout_density"]
    rows = []
    for scale, steps in zip(contract.bc3_scales, contract.bc3_steps_per_edge, strict=True):
        lattice = exact_lattice(scale, steps, contract)
        line = midpoint_line_interval(lattice.forward, lattice.denominator)
        rows.append(
            {
                "lattice": lattice_certificate(lattice),
                "midpoint_line_interval": line.jsonable_scalar(),
            }
        )
    return {
        "method": "independent_binary64_outward_midpoint_beta_integral_before_oracle",
        "center_form_interval": center.jsonable(),
        "rows": rows,
        "response_oracle_imported": False,
        "heldout_response_used": False,
    }
