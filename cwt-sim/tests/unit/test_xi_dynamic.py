"""Unit tests for dynamic susceptibility helpers."""

from __future__ import annotations

import networkx as nx
import numpy as np

from cwt.graph.substrate import GraphSubstrate, build_substrate
from cwt.metrics.triage import xi_dynamic, xi_update_ema


def _two_node_chain() -> GraphSubstrate:
    G = nx.DiGraph()
    G.add_edge(0, 1, weight=1.0, delay=1.0)
    S = build_substrate(G)
    return S


def test_xi_dynamic_theta_component_highlights_inflow():
    S = _two_node_chain()

    Psi = np.ones(S.N, dtype=complex)
    pQ = np.ones(S.N, dtype=float)
    theta = np.array([0.0, 0.5 * np.pi])

    xi = xi_dynamic(S, Psi, pQ, theta, g1=0.0, g2=1.0, g3=0.0, g4=0.0)

    assert xi.shape == (S.N,)
    assert np.allclose(xi.sum(), 1.0)
    assert np.allclose(xi, np.array([0.0, 1.0]))


def test_xi_dynamic_probability_conservation_from_amplitude():
    G = nx.DiGraph()
    G.add_nodes_from([0, 1])
    S = build_substrate(G)

    Psi = np.array([1.0 + 0.0j, 2.0 + 0.0j])
    pQ = np.ones(S.N, dtype=float)
    theta = np.zeros(S.N, dtype=float)

    xi = xi_dynamic(S, Psi, pQ, theta, g1=1.0, g2=0.0, g3=0.0, g4=0.0)

    assert np.allclose(xi.sum(), 1.0)
    assert np.all(xi >= 0.0)
    expected = np.array([1.0, 4.0]) / 5.0
    assert np.allclose(xi, expected)


def test_xi_dynamic_incorporates_pressure_and_order_terms():
    G = nx.DiGraph()
    G.add_edge(0, 1, weight=1.0, delay=1.0)
    G.add_edge(2, 1, weight=2.0, delay=1.0)
    S = build_substrate(G)

    Psi = np.ones(S.N, dtype=complex)
    pQ = np.array([1.0, 0.25, 4.0], dtype=float)
    theta = np.array([0.0, 1.0, 0.0], dtype=float)

    xi_pressure = xi_dynamic(S, Psi, pQ, theta, g1=0.0, g2=0.0, g3=1.0, g4=0.0)
    assert np.allclose(xi_pressure, np.array([0.0, 1.0, 0.0]))

    theta_near = np.array([0.0, 1.0, 0.0], dtype=float)
    xi_order = xi_dynamic(S, Psi, pQ, theta_near, g1=0.0, g2=0.0, g3=0.0, g4=1.0)
    assert np.allclose(xi_order, np.array([0.0, 1.0, 0.0]))


def test_xi_update_ema_converges_with_small_kappa():
    prev = np.array([0.7, 0.3])
    target = np.array([0.2, 0.8])

    distance_prev = np.linalg.norm(prev - target, ord=1)
    xi = prev

    for _ in range(6):
        xi = xi_update_ema(xi, target, kappa=0.1)
        assert np.allclose(xi.sum(), 1.0)
        assert np.all(xi >= 0.0)

        distance = np.linalg.norm(xi - target, ord=1)
        assert distance <= distance_prev + 1e-12
        distance_prev = distance

    assert distance_prev < np.linalg.norm(prev - target, ord=1)
