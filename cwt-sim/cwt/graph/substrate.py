"""Graph substrate definitions for continuous wavelet transport simulations."""

from __future__ import annotations


class GraphSubstrate:
    """Placeholder for graph substrate implementation."""

    def __init__(self) -> None:
        self.nodes = []
        self.edges = []

    def add_node(self, node_id: int) -> None:
        """Add a node to the substrate placeholder."""
        self.nodes.append(node_id)

    def add_edge(self, source: int, target: int) -> None:
        """Add an edge to the substrate placeholder."""
        self.edges.append((source, target))
