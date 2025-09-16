"""Readout and memory primitives for the C-layer."""

from __future__ import annotations

from typing import Mapping, Sequence

import networkx as nx
import numpy as np

from ..graph.substrate import GraphSubstrate


def memory_uniform_charge(Phi: float, chi: np.ndarray | Sequence[float]) -> np.ndarray:
    r"""Uniform geometric charge memory.

    Parameters
    ----------
    Phi:
        Oriented loop flux :math:`\Phi_\gamma`.
    chi:
        Node-wise susceptibility weights ``\chi_n``.

    Returns
    -------
    numpy.ndarray
        ``Phi * chi`` broadcast to an array.
    """

    chi_arr = np.asarray(chi, dtype=float)
    return float(Phi) * chi_arr


def memory_direction_locked(
    Phi: float,
    s: np.ndarray | Sequence[float],
    t_loop: np.ndarray | Sequence[float] | float,
    grad_theta: np.ndarray,
) -> np.ndarray:
    r"""Direction-locked memory term.

    Implements :math:`M_n = \Phi_\gamma\, s_n\,(\mathbf{t}_\text{loop}\cdot \nabla\theta_n)`.

    Parameters
    ----------
    Phi:
        Oriented loop flux.
    s:
        Local coherence weights ``s_n`` in ``[0, 1]``.
    t_loop:
        Preferred transport direction on the control manifold.
    grad_theta:
        Phase gradients per node. ``grad_theta[n]`` must broadcast with
        ``t_loop`` so the directional derivative is defined.

    Returns
    -------
    numpy.ndarray
        Direction-locked memory per node.
    """

    s_arr = np.asarray(s, dtype=float)
    grad = np.asarray(grad_theta, dtype=float)
    t_vec = np.asarray(t_loop, dtype=float)

    if grad.ndim == 0:
        raise ValueError("grad_theta must have at least one dimension.")

    if grad.ndim == 1:
        # Degenerate case: treat t_loop as a scalar direction coefficient.
        if t_vec.ndim > 1 or (t_vec.ndim == 1 and t_vec.size not in (0, 1)):
            raise ValueError("t_loop must be scalar when grad_theta is 1-D.")
        scalar = 0.0 if t_vec.size == 0 else float(t_vec.reshape(()))
        direction = grad * scalar
    else:
        if t_vec.ndim == 0:
            direction = grad * float(t_vec)
        else:
            if grad.shape[-1] != t_vec.shape[0]:
                raise ValueError("Last axis of grad_theta must match the length of t_loop.")
            direction = np.tensordot(grad, t_vec, axes=([-1], [0]))

    direction = np.asarray(direction, dtype=float)
    if direction.shape != s_arr.shape:
        try:
            direction = np.broadcast_to(direction, s_arr.shape)
        except ValueError as exc:  # pragma: no cover - defensive programming
            raise ValueError("Shapes of coherence weights and directional gradients do not align.") from exc

    return float(Phi) * s_arr * direction


def memory_current_coupled(Phi: float, J_net: np.ndarray | Sequence[float]) -> np.ndarray:
    """Current-coupled memory term.

    Parameters
    ----------
    Phi:
        Oriented loop flux.
    J_net:
        Net outgoing current per node.

    Returns
    -------
    numpy.ndarray
        Normalised current memory scaled by ``Phi``.
    """

    currents = np.asarray(J_net, dtype=float)
    if currents.ndim == 0:
        currents = currents.reshape((1,))

    scale = np.max(np.abs(currents))
    if not np.isfinite(scale) or scale == 0.0:
        normalised = np.zeros_like(currents)
    else:
        normalised = currents / scale

    return float(Phi) * normalised


def readout_stochastic(
    pQ: np.ndarray | Sequence[float],
    M_n: np.ndarray | Sequence[float],
    T: float,
    eta: float,
) -> tuple[int, np.ndarray]:
    """Stochastic sampling readout.

    Draw an outcome according to ``P ∝ exp((log pQ + eta * M_n) / T)``.
    Deterministic in the ``T → 0`` limit and uniform as ``T → ∞``.
    """

    probs = np.asarray(pQ, dtype=float)
    memory = np.asarray(M_n, dtype=float)

    if probs.ndim != 1:
        raise ValueError("pQ must be a one-dimensional array.")
    if memory.shape != probs.shape:
        raise ValueError("M_n must have the same shape as pQ.")

    field = np.full_like(probs, -np.inf)
    positive = probs > 0.0
    field[positive] = np.log(probs[positive])
    field = field + float(eta) * memory

    finite_mask = np.isfinite(field)
    if not finite_mask.any():
        weights = np.full(probs.shape, 1.0 / probs.size, dtype=float)
        choice = int(np.random.choice(probs.size, p=weights))
        return choice, weights

    if T <= 0.0:
        choice = int(np.argmax(field))
        weights = np.zeros_like(probs, dtype=float)
        weights[choice] = 1.0
        return choice, weights

    scaled = field / float(T)
    finite_scaled = scaled[finite_mask]
    max_val = float(np.max(finite_scaled))

    logits = np.full_like(probs, -np.inf)
    logits[finite_mask] = scaled[finite_mask] - max_val

    exp_logits = np.zeros_like(probs, dtype=float)
    np.exp(logits, out=exp_logits, where=np.isfinite(logits))
    total = float(np.sum(exp_logits))
    if total <= 0.0 or not np.isfinite(total):  # pragma: no cover - defensive guard
        weights = np.full(probs.shape, 1.0 / probs.size, dtype=float)
    else:
        weights = exp_logits / total

    choice = int(np.random.choice(probs.size, p=weights))
    return choice, weights


def readout_percolation(
    pQ: np.ndarray | Sequence[float],
    p_crit: float,
    theta_perc: float,
    M_shift: float = 0.0,
    G: GraphSubstrate | nx.Graph | nx.DiGraph | None = None,
) -> dict[str, int | bool]:
    """Threshold/percolation readout.

    Nodes with ``pQ > p_crit - M_shift`` are considered active. The readout
    fires when the largest connected component among active nodes exceeds
    ``theta_perc * N``.
    """

    probs = np.asarray(pQ, dtype=float)
    if probs.ndim != 1:
        raise ValueError("pQ must be a one-dimensional array.")

    N = probs.size
    threshold = float(p_crit) - float(M_shift)
    active_mask = probs > threshold

    if G is None:
        largest = int(np.count_nonzero(active_mask))
    else:
        graph, node_to_index = _coerce_graph(G)
        if graph.number_of_nodes() != N:
            raise ValueError("Graph node count must match the length of pQ.")

        if graph.is_directed():
            undirected = graph.to_undirected(as_view=True)
        else:
            undirected = graph

        active_nodes = [node for node, idx in node_to_index.items() if active_mask[int(idx)]]

        if not active_nodes:
            largest = 0
        else:
            subgraph = undirected.subgraph(active_nodes)
            if subgraph.number_of_nodes() == 0:
                largest = 0
            else:
                largest = max(len(component) for component in nx.connected_components(subgraph))

    fired = bool(largest > float(theta_perc) * N)
    return {"fired": fired, "size": int(largest)}


def readout_spiking(
    pQ: np.ndarray | Sequence[float],
    s: np.ndarray | Sequence[float],
    M_n: np.ndarray | Sequence[float],
    r0: float,
    c1: float,
    c2: float,
    c3: float,
    window: int | float,
    thresh: int,
    rng,
) -> dict[str, int | bool]:
    """Spiking ensemble readout via Poisson sampling."""

    probs = np.asarray(pQ, dtype=float)
    signal = np.asarray(s, dtype=float)
    memory = np.asarray(M_n, dtype=float)

    if probs.ndim != 1:
        raise ValueError("pQ must be a one-dimensional array.")
    if signal.shape != probs.shape or memory.shape != probs.shape:
        raise ValueError("s and M_n must match the shape of pQ.")

    drive = c1 * probs + c2 * signal + c3 * memory
    drive = np.nan_to_num(drive, nan=0.0, neginf=0.0)
    positive_drive = np.clip(drive, 0.0, None)
    rates = float(r0) * positive_drive
    lam = rates * float(window)

    rng_obj = rng if rng is not None else np.random.default_rng()
    if not hasattr(rng_obj, "poisson"):
        raise TypeError("rng must provide a poisson method.")

    spikes = rng_obj.poisson(lam)
    spikes_total = int(np.sum(spikes))
    fired = bool(spikes_total >= int(thresh))

    return {"fired": fired, "spikes_total": spikes_total}


def edge_currents(S: GraphSubstrate, pQ: np.ndarray, theta: np.ndarray) -> np.ndarray:
    """Compute net outgoing phase currents per node.

    For each edge ``m → n`` the current is
    ``J_nm = W[n, m] * sqrt(p_n p_m) * sin(theta_m - theta_n)``. The returned
    value is ``sum_n J_nm - J_mn`` for every node ``m``.
    """

    if not isinstance(S, GraphSubstrate):
        raise TypeError("S must be a GraphSubstrate instance.")

    probs = np.asarray(pQ, dtype=float).reshape(-1)
    phases = np.asarray(theta, dtype=float).reshape(-1)

    if probs.shape != (S.N,) or phases.shape != (S.N,):
        raise ValueError("pQ and theta must have shape (S.N,).")

    sqrt_p = np.sqrt(np.clip(probs, 0.0, None))

    W = S.W.tocoo()
    rows = W.row
    cols = W.col
    weights = W.data

    phase_diff = phases[cols] - phases[rows]
    magnitude = weights * sqrt_p[rows] * sqrt_p[cols]
    edge_vals = magnitude * np.sin(phase_diff)

    outgoing = np.zeros(S.N, dtype=float)
    incoming = np.zeros(S.N, dtype=float)
    np.add.at(outgoing, cols, edge_vals)
    np.add.at(incoming, rows, edge_vals)

    return outgoing - incoming


def _coerce_graph(
    G: GraphSubstrate | nx.Graph | nx.DiGraph,
) -> tuple[nx.Graph | nx.DiGraph, Mapping[int, int]]:
    """Return a networkx graph and a node-to-index mapping."""

    if isinstance(G, GraphSubstrate):
        graph = G.G
        node_to_index: Mapping[int, int] = G.node_index
        return graph, node_to_index

    if not isinstance(G, (nx.Graph, nx.DiGraph)):
        raise TypeError("G must be a networkx graph or GraphSubstrate.")

    nodes = list(G.nodes())
    node_count = len(nodes)
    if node_count == 0:
        return G, {}

    if all(isinstance(node, (int, np.integer)) for node in nodes):
        unique_nodes = {int(node) for node in nodes}
        if unique_nodes == set(range(node_count)):
            node_to_index = {int(node): int(node) for node in nodes}
        else:
            sorted_nodes = sorted(unique_nodes)
            node_to_index = {node: idx for idx, node in enumerate(sorted_nodes)}
    else:
        try:
            ordered_nodes: Sequence[object] = sorted(nodes)
        except TypeError:
            ordered_nodes = list(nodes)
        node_to_index = {node: idx for idx, node in enumerate(ordered_nodes)}

    return G, node_to_index


__all__ = [
    "memory_uniform_charge",
    "memory_direction_locked",
    "memory_current_coupled",
    "readout_stochastic",
    "readout_percolation",
    "readout_spiking",
    "edge_currents",
]
