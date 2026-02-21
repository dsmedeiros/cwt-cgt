"""Tests for triage scoring invariants and bounded behavior."""

from __future__ import annotations

import networkx as nx
import numpy as np

from cwt.graph.substrate import build_substrate
from cwt.metrics.triage import TRIAGE_WEIGHTS, triage_score


def _make_cycle_substrate(n_nodes: int = 4):
    graph = nx.DiGraph()
    for node in range(n_nodes):
        graph.add_edge(node, (node + 1) % n_nodes, weight=1.0, delay=1.0)
    return build_substrate(graph)


def test_triage_weights_sum_to_one() -> None:
    assert np.isclose(sum(TRIAGE_WEIGHTS.values()), 1.0)


def test_triage_score_is_bounded_and_penalizes_bad_signals() -> None:
    substrate = _make_cycle_substrate()

    healthy_score = triage_score(
        substrate,
        curvature_bias=np.zeros(substrate.N),
        clip_counts=np.zeros(substrate.N, dtype=int),
        susceptibility=np.ones(substrate.N),
        geom_stats={"tr_g": 2.0, "det_g": 1.0, "omega": 0.5},
    )

    stressed_score = triage_score(
        substrate,
        curvature_bias=np.full(substrate.N, 1_000.0),
        clip_counts=np.full(substrate.N, 1_000, dtype=int),
        susceptibility=np.array([1.0, 0.0, 0.0, 0.0]),
        geom_stats={"tr_g": 0.0, "det_g": 0.0, "omega": 0.0},
    )

    assert 0.0 <= healthy_score <= 1.0
    assert 0.0 <= stressed_score <= 1.0
    assert healthy_score > stressed_score
