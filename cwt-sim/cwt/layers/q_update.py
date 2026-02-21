"""Probability transport updates for the Q layer."""

from __future__ import annotations

from typing import Dict

import numpy as np
import scipy.sparse as sp

from .state import normalize_prob


def q_step(
    pQ: np.ndarray,
    K: sp.csr_matrix,
    eta: float,
    geom_bias: np.ndarray | None = None,
    clip_floor: float = 0.0,
    validate_kernel: bool = False,
) -> tuple[np.ndarray, Dict[str, int | float | bool]]:
    """Advance the Q-layer probabilities by one explicit step.

    Parameters
    ----------
    pQ:
        Current probability vector. The array is treated as immutable and is
        not modified in-place.
    K:
        Column-stochastic transport kernel represented as a CSR matrix.
    eta:
        Mixing coefficient in :math:`(0, 1]` controlling the interpolation
        between the previous state and the transported mass.
    geom_bias:
        Optional additive bias that captures geometric corrections before
        clipping/normalisation.
    clip_floor:
        Minimum allowed value for the pre-normalised probabilities. Values
        below this floor are clipped to preserve positivity before
        normalisation.
    validate_kernel:
        If ``True``, assert that each transport-kernel column is stochastic
        (sum close to one). The check allows explicitly handled degenerate
        columns used by some nonstandard kernels: empty (zero-support)
        columns and pure self-loop columns.

    Returns
    -------
    tuple[numpy.ndarray, dict]
        ``(pQ_next, stats)`` where ``pQ_next`` is the renormalised probability
        vector and ``stats`` records diagnostic information about clipping and
        post-normalisation repairs.
    """

    if eta < 0 or eta > 1:
        raise ValueError("eta must lie in the interval [0, 1].")

    if clip_floor < 0:
        raise ValueError("clip_floor must be non-negative.")

    if not sp.isspmatrix_csr(K):
        raise TypeError("K must be a CSR sparse matrix.")

    p_arr = np.asarray(pQ, dtype=float).copy()
    if p_arr.ndim != 1:
        raise ValueError("pQ must be a one-dimensional array.")

    N = p_arr.size

    if K.shape != (N, N):
        raise ValueError("K must be a square matrix with side length matching pQ.")

    if validate_kernel:
        K_csc = K.tocsc(copy=False)
        col_sums = np.asarray(K_csc.sum(axis=0)).ravel()
        col_nnz = np.diff(K_csc.indptr)
        tol = 1e-8

        columns = np.arange(N)
        is_zero_support = col_nnz == 0
        is_self_loop = np.zeros(N, dtype=bool)

        single_entry = np.where(col_nnz == 1)[0]
        for col in single_entry:
            start, end = K_csc.indptr[col], K_csc.indptr[col + 1]
            is_self_loop[col] = bool(K_csc.indices[start:end][0] == col)

        exempt_columns = is_zero_support | is_self_loop
        stochastic_columns = ~exempt_columns
        off_columns = stochastic_columns & ~np.isclose(col_sums, 1.0, atol=tol, rtol=0.0)

        assert not np.any(off_columns), (
            "K must be column-stochastic outside explicit zero-support/self-loop "
            f"columns; offending columns={columns[off_columns].tolist()}, "
            f"sums={col_sums[off_columns].tolist()}"
        )

    transported = K.dot(p_arr)

    if geom_bias is not None:
        bias = np.asarray(geom_bias, dtype=float)
        if bias.shape != (N,):
            raise ValueError("geom_bias must have the same shape as pQ.")
    else:
        bias = None

    provisional = (1.0 - eta) * p_arr + eta * transported
    if bias is not None:
        provisional = provisional + bias

    neg_before = int(np.count_nonzero(provisional < 0.0))

    clipped = np.maximum(provisional, clip_floor)
    clipped_count = int(np.count_nonzero(provisional < clip_floor))

    p_next, norm_stats = normalize_prob(clipped, return_stats=True)

    stats: Dict[str, int | float | bool] = {
        "clipped_count": clipped_count,
        "neg_before_clip": neg_before,
        "norm_neg_clamped_count": int(norm_stats["neg_clamped_count"]),
        "norm_neg_clamped_mass": float(norm_stats["neg_clamped_mass"]),
        "norm_uniform_fallback": bool(norm_stats["uniform_fallback"]),
    }

    return p_next, stats
