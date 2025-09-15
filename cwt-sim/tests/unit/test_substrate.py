"""Unit tests for graph substrate construction utilities."""

from __future__ import annotations

import numpy as np
import pytest

import networkx as nx

from cwt.graph import factories
from cwt.graph.substrate import build_substrate


def test_ring3_substrate_structure() -> None:
    substrate = factories.ring3(weight=2.0, delay=3.0)

    assert substrate.N == 3
    assert substrate.W.shape == (3, 3)
    assert substrate.Tau.shape == (3, 3)
    assert substrate.W.nnz == 3
    assert substrate.Tau.nnz == 3
    assert substrate.node_index == {0: 0, 1: 1, 2: 2}
    np.testing.assert_array_equal(substrate.out_deg, np.ones(3, dtype=np.int64))

    W_dense = substrate.W.toarray()
    Tau_dense = substrate.Tau.toarray()
    assert W_dense[1, 0] == pytest.approx(2.0)
    assert W_dense[2, 1] == pytest.approx(2.0)
    assert W_dense[0, 2] == pytest.approx(2.0)
    assert Tau_dense[1, 0] == pytest.approx(3.0)
    assert Tau_dense[2, 1] == pytest.approx(3.0)
    assert Tau_dense[0, 2] == pytest.approx(3.0)


def test_from_edgelist_single_edge() -> None:
    substrate = factories.from_edgelist([(0, 1, 5.0, 7.0)])

    assert substrate.N == 2
    assert substrate.W.nnz == 1
    assert substrate.Tau.nnz == 1
    assert substrate.out_deg.tolist() == [1, 0]
    assert substrate.W.toarray()[1, 0] == pytest.approx(5.0)
    assert substrate.Tau.toarray()[1, 0] == pytest.approx(7.0)


def test_non_int_node_labels_sorted() -> None:
    G = nx.DiGraph()
    G.add_edge("b", "c", weight=1.0, delay=2.0)
    G.add_edge("a", "b", weight=1.0, delay=2.0)

    substrate = build_substrate(G)

    assert substrate.N == 3
    assert substrate.node_index == {"a": 0, "b": 1, "c": 2}
    assert substrate.W.toarray()[1, 0] == pytest.approx(1.0)
    assert substrate.W.toarray()[2, 1] == pytest.approx(1.0)


def test_negative_weight_raises() -> None:
    G = nx.DiGraph()
    G.add_edge(0, 1, weight=-1.0, delay=1.0)

    with pytest.raises(ValueError):
        build_substrate(G)


def test_non_positive_delay_raises() -> None:
    G = nx.DiGraph()
    G.add_edge(0, 1, weight=1.0, delay=0.0)

    with pytest.raises(ValueError):
        build_substrate(G)
