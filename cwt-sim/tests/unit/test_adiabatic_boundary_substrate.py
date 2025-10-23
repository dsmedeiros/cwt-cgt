"""Unit tests for substrate loading in the adiabatic boundary experiment."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from cwt.graph.factories import random_regular_digraph, ring3_hetero
from experiments.adiabatic_boundary.run import (
    _instantiate_graph_from_metadata,
    _load_substrate_artifact,
)
from experiments.gateB_ridge_finder import run as phase1_run
from experiments.loop_at_hotspot.run import _build_summary_payload, _default_run_config


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


def _build_phase1_substrate(name: str, seed: int | None = None):
    base_seed = 7 if seed is None else int(seed)
    built = phase1_run.build_substrates([name], seed=base_seed)
    if not built:
        raise AssertionError(f"Phase 1 factory '{name}' returned no substrate")
    return built[0].substrate


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


def test_cli_summary_random_regular_descriptor(tmp_path: Path) -> None:
    """CLI-generated summaries include graph metadata usable for reconstruction."""

    config = _default_run_config(0)
    summary_payload = _build_summary_payload(
        axes=("tau", "zeta"),
        graph="random_regular",
        fs_guard=None,
        config=config,
        base_steps=2048,
        seed=23,
        limit=None,
        micro_scan=False,
        auto_extent=False,
        target_fs=None,
        pilot_frac=None,
        extent_bracket=None,
        fs_margin=0.05,
        max_extent_iters=6,
        extents_input=[],
        hotspots_path=tmp_path / "hotspots.json",
        results=[],
        accepted=True,
        failures=[],
        time_budget=None,
        time_consumed=None,
    )

    path = _write_summary(tmp_path, summary_payload)
    saved_payload = json.loads(path.read_text(encoding="utf-8"))
    descriptor = saved_payload.get("graph")

    assert descriptor["identifier"] == "random_regular_digraph"
    kwargs = descriptor.get("kwargs") or {}
    assert kwargs["N"] == 20
    assert kwargs["out_degree"] == 3
    assert kwargs["seed"] == 23

    rebuilt = _instantiate_graph_from_metadata(
        descriptor["identifier"],
        kwargs,
        seed_value=saved_payload.get("seed"),
        source_description="CLI summary",
    )
    expected = random_regular_digraph(N=20, out_degree=3, seed=23)

    _assert_equivalent_substrates(rebuilt, expected)


@pytest.mark.parametrize(
    ("identifier", "seed"),
    [
        ("small_world", 11),
        ("scale_free", 13),
        ("watts_strogatz_p0", 17),
        ("watts_strogatz_p001", 19),
        ("watts_strogatz_p010", 23),
        ("periodic_lattice", 29),
        ("erdos_renyi", 31),
        ("barabasi_albert", 37),
    ],
)
def test_instantiate_phase1_substrates(identifier: str, seed: int) -> None:
    rebuilt = _instantiate_graph_from_metadata(
        identifier,
        {"seed": seed},
        seed_value=None,
        source_description="Phase 1 summary",
    )
    expected = _build_phase1_substrate(identifier, seed=seed)

    _assert_equivalent_substrates(rebuilt, expected)


def test_instantiate_phase1_substrate_accepts_graph_seed_alias() -> None:
    identifier = "small_world"
    rebuilt = _instantiate_graph_from_metadata(
        identifier,
        {"graph_seed": 41},
        seed_value=None,
        source_description="Phase 1 summary",
    )
    expected = _build_phase1_substrate(identifier, seed=41)

    _assert_equivalent_substrates(rebuilt, expected)


def test_instantiate_phase1_substrate_uses_summary_seed() -> None:
    identifier = "scale_free"
    rebuilt = _instantiate_graph_from_metadata(
        identifier,
        {},
        seed_value=43,
        source_description="Phase 1 summary",
    )
    expected = _build_phase1_substrate(identifier, seed=43)

    _assert_equivalent_substrates(rebuilt, expected)


def test_instantiate_phase1_substrate_defaults_to_cli_seed() -> None:
    identifier = "periodic_lattice"
    rebuilt = _instantiate_graph_from_metadata(
        identifier,
        {},
        seed_value=None,
        source_description="Phase 1 summary",
    )
    expected = _build_phase1_substrate(identifier, seed=7)

    _assert_equivalent_substrates(rebuilt, expected)
