"""Non-authoritative live-core regression and exact source binding."""

from __future__ import annotations

import hashlib
from dataclasses import asdict
from fractions import Fraction
from pathlib import Path

import numpy as np

from cwt.cgt.lindblad import LindbladConfig, lindblad_rhs
from cwt.cgt.models import BranchState

from .contract import MODEL_CONTRACT
from .generator import NODE_COUNT, d0_kernel, liouvillian

SIM_ROOT = Path(__file__).resolve().parents[2]
CORE_SOURCE_PATHS = (
    "cwt/cgt/lindblad.py",
    "cwt/cgt/open_system.py",
    "cwt/cgt/benchmarks.py",
    "cwt/cgt/models.py",
)


def _state(bias: Fraction, diffusion: Fraction) -> BranchState:
    return BranchState(
        p=np.full(NODE_COUNT, 1.0 / NODE_COUNT),
        theta=np.zeros(NODE_COUNT),
        kernel=np.asarray(d0_kernel(bias, diffusion), dtype=float),
        extras={"b": float(bias), "d": float(diffusion)},
    )


def _config(coherent_scale: Fraction) -> LindbladConfig:
    return LindbladConfig(
        dt=0.02,
        integration_steps=30,
        coherent_scale=float(coherent_scale),
        edge_jump_scale=float(MODEL_CONTRACT.edge_rate),
        site_potential_scale=float(MODEL_CONTRACT.site_potential_scale),
        depolarizing_rate=float(MODEL_CONTRACT.depolarizing_rate),
        dephasing_values=(float(MODEL_CONTRACT.dephasing_rate),),
        coherence_switch_floor=0.20,
        scan_mesh=9,
    )


def source_bindings() -> dict[str, dict[str, object]]:
    records: dict[str, dict[str, object]] = {}
    for relative in CORE_SOURCE_PATHS:
        payload = (SIM_ROOT / relative).read_bytes()
        if payload.startswith(b"\xef\xbb\xbf"):
            raise RuntimeError(f"core source has a forbidden UTF-8 BOM: {relative}")
        payload.decode("utf-8")
        canonical = payload.replace(b"\r\n", b"\n")
        if b"\r" in canonical:
            raise RuntimeError(f"core source has a bare CR: {relative}")
        records[relative] = {
            "sha256_utf8_lf": hashlib.sha256(canonical).hexdigest(),
            "hash_domain": "sha256_utf8_lf_v1_CRLF_to_LF_only_no_BOM_no_bare_CR",
            "role": "live_core_semantic_binding",
        }
    return records


def core_regression_certificate() -> dict[str, object]:
    """Compare the exact family against live float RHS on a complete matrix basis.

    This is provenance/drift detection only.  Exact theorem acceptance never
    depends on the floating-point errors recorded here.
    """

    points = (
        (MODEL_CONTRACT.b_bounds[0], MODEL_CONTRACT.d_bounds[0], MODEL_CONTRACT.h_bounds[0]),
        (MODEL_CONTRACT.b_bounds[0], MODEL_CONTRACT.d_bounds[1], MODEL_CONTRACT.h_bounds[1]),
        (MODEL_CONTRACT.b_bounds[1], MODEL_CONTRACT.d_bounds[0], MODEL_CONTRACT.h_bounds[1]),
        (MODEL_CONTRACT.b_bounds[1], MODEL_CONTRACT.d_bounds[1], MODEL_CONTRACT.h_bounds[0]),
        MODEL_CONTRACT.t1_center,
    )
    errors: list[float] = []
    for bias, diffusion, coherent_scale in points:
        state = _state(bias, diffusion)
        config = _config(coherent_scale)
        exact = np.asarray(
            [
                [complex(float(item.real), float(item.imag)) for item in row]
                for row in liouvillian(
                    bias,
                    diffusion,
                    coherent_scale,
                    MODEL_CONTRACT.depolarizing_rate,
                )
            ],
            dtype=complex,
        )
        zero = np.zeros((NODE_COUNT, NODE_COUNT), dtype=complex)
        affine_source = lindblad_rhs(zero, state, config, float(MODEL_CONTRACT.dephasing_rate))
        for row in range(NODE_COUNT):
            for column in range(NODE_COUNT):
                basis = np.zeros_like(zero)
                basis[row, column] = 1.0
                core = lindblad_rhs(basis, state, config, float(MODEL_CONTRACT.dephasing_rate))
                if row != column:
                    core = core - affine_source
                exact_column = exact[:, row + NODE_COUNT * column].reshape(
                    (NODE_COUNT, NODE_COUNT), order="F"
                )
                errors.append(float(np.max(np.abs(core - exact_column))))
    return {
        "authority": "NON_AUTHORITATIVE_FLOAT_CORE_REGRESSION",
        "used_by_theorem_pass": False,
        "points": [[str(item) for item in point] for point in points],
        "complete_complex_matrix_basis_count_per_point": NODE_COUNT**2,
        "maximum_absolute_error": max(errors),
        "all_LindbladConfig_fields_explicit": len(asdict(_config(MODEL_CONTRACT.h_bounds[0]))) == 9,
        "core_source_bindings": source_bindings(),
    }
