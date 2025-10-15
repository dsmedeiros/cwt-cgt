"""Unit tests for substrate loading in the adiabatic boundary experiment."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from cwt.graph.factories import random_regular_digraph, ring3_hetero
from experiments.adiabatic_boundary.run import _load_substrate_artifact


def _write_summary(directory: Path, payload: dict) -> Path:
    path = directory / "phase3_loop_summary.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _edge_payload(substrate) -> dict[tuple[int, int], tuple[float, float]]:
    graph = substrate.G
    payload: dict[tuple[int, int], tuple[float, float]] = {}
    for source, target, data in graph.edges(data=True):
        weight = float(data.get("weight", 1.0))
        delay = float(data.get("delay", 1.0))
        payload[(int(source), int(target))] = (weight, delay)
    return payload


def _assert_equivalent_substrates(actual, expected) -> None:
    assert actual.N == expected.N
    assert actual.node_index == expected.node_index

    actual_edges = _edge_payload(actual)
    expected_edges = _edge_payload(expected)
    assert actual_edges.keys() == expected_edges.keys()
    for edge in actual_edges:
        weight, delay = actual_edges[edge]
        exp_weight, exp_delay = expected_edges[edge]
        assert weight == pytest.approx(exp_weight)
        assert delay == pytest.approx(exp_delay)


def test_load_substrate_from_phase3_summary_ring3(tmp_path: Path) -> None:
    """Fallback rebuilds ring3_hetero substrates from summary metadata."""

    _write_summary(
        tmp_path,
        {
            "graph": {"identifier": "ring3_hetero"},
            "seed": 17,
        },
    )

    loaded = _load_substrate_artifact(tmp_path)
    expected = ring3_hetero()

    _assert_equivalent_substrates(loaded, expected)


def test_load_substrate_from_phase3_summary_random_regular(tmp_path: Path) -> None:
    """Random regular substrates honour the recorded seed in the summary."""

    summary_payload = {
        "schema_version": 1,
        "created_at": "2024-05-19T12:34:56Z",
        "axes": ["tau", "zeta"],
        "graph": {
            "identifier": "random_regular_digraph",
            "kwargs": {
                "N": 20,
                "out_degree": 3,
                "seed": 23,
            },
            "label": "Random regular (20 nodes)",
        },
        "fs_guard": 0.12,
        "neighbor_settle_steps": 40,
        "seed": 23,
        "steps_list": [400, 200, 120],
        "hotspots": [
            {
                "label": "Guided hotspot",
                "center": {"tau": 0.02, "zeta": -0.01},
                "extents": [
                    {
                        "axes": ["tau", "zeta"],
                        "values": [0.04, 0.03],
                        "ccw": {"phi": 0.42, "steps": 400},
                    }
                ],
                "metadata": {"id": "hs-1"},
                "omega_abs": 0.015,
            }
        ],
        "accepted": True,
        "failures": [],
        "source": "guided_loop",
        "runs": [
            {
                "run_id": "loop-400",
                "steps": 400,
                "status": "complete",
                "metrics": {"phi": 0.42, "fs_p95": 0.11},
            }
        ],
    }
    _write_summary(tmp_path, summary_payload)

    loaded = _load_substrate_artifact(tmp_path)
    expected = random_regular_digraph(N=20, out_degree=3, seed=23)

    _assert_equivalent_substrates(loaded, expected)
