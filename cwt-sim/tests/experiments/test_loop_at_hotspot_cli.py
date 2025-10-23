import json
from pathlib import Path

import pytest

from cwt.graph import factories
from experiments.loop_at_hotspot import run


def _make_top_tiles(path: Path) -> None:
    payload = {
        "axes": ["tau", "zeta"],
        "top_tiles": [
            {
                "coordinates": {"tau": 0.01, "zeta": -0.02},
                "omega_abs": 0.42,
            }
        ],
        "graph": {
            "identifier": "small_world",
            "kwargs": {"seed": 17},
            "seed": 17,
        },
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_cli_uses_metadata_descriptor_for_phase1_substrate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    hotspots_path = tmp_path / "top_omega_tiles.json"
    _make_top_tiles(hotspots_path)

    captured: dict[str, object] = {}

    def _stub_build_substrate(descriptor):
        captured["descriptor"] = descriptor
        return factories.ring3()

    def _stub_evaluate_hotspot(index, spec, **kwargs):
        return run.HotspotSummary(index=index, spec=spec, extents=[], kappa_scale_errors=[])

    monkeypatch.setattr(run, "_build_substrate_from_descriptor", _stub_build_substrate)
    monkeypatch.setattr(run, "evaluate_hotspot", _stub_evaluate_hotspot)
    monkeypatch.setattr(run, "render_summary", lambda results: None)
    monkeypatch.setattr(run, "evaluate_acceptance", lambda results: (True, []))

    summary_path = tmp_path / "summary.json"

    exit_code = run.main(
        [
            "--hotspots",
            str(hotspots_path),
            "--extents",
            "0.01",
            "--graph",
            "ring3",
            "--seed",
            "23",
            "--save-summary",
            str(summary_path),
        ]
    )

    assert exit_code == 0
    descriptor = captured.get("descriptor")
    assert isinstance(descriptor, dict)
    assert descriptor.get("identifier") == "small_world"
    assert descriptor.get("seed") == 17

    saved = json.loads(summary_path.read_text(encoding="utf-8"))
    graph_block = saved.get("graph") or {}
    assert graph_block.get("identifier") == "small_world"
    assert graph_block.get("seed") == 17
