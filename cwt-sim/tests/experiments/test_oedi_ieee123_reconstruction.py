from __future__ import annotations

import json
import re
from pathlib import Path

import networkx as nx
import numpy as np
import pytest
from typer.testing import CliRunner

from experiments.oedi_ieee123_reconstruction import (
    prospective as prospective_module,
    prospective_confirm as confirm_module,
)
from experiments.oedi_ieee123_reconstruction.prospective import (
    EXPECTED_CALIBRATION_IDS,
    EXPECTED_CONFIRMATION_IDS,
    _loadshape_catalog,
    allocate_cluster_split,
    compute_source_inventory_hash,
    compute_split_manifest_hash,
    prepare_prospective,
)
from experiments.oedi_ieee123_reconstruction.prospective_confirm import (
    _load_admitted_profiles,
    execute_confirmation,
    qap_test,
    quarter_hour_residual,
)
from experiments.oedi_ieee123_reconstruction.retrospective import parse_transformer_metadata
from experiments.oedi_ieee123_reconstruction.run import app
from experiments.oedi_ieee123_reconstruction.source import (
    LoadDefinition,
    LoadShapeDefinition,
    SourceIntegrityError,
    canonical_json_sha256,
    parse_buscoord_labels,
    parse_load_definitions,
    sha256_file,
)

EXPERIMENT_DIR = Path(__file__).resolve().parents[2] / "experiments" / "oedi_ieee123_reconstruction"


def test_dss_parser_honors_inline_comments_continuations_and_like(tmp_path: Path) -> None:
    loads_path = tmp_path / "loads.dss"
    loads_path.write_text(
        "\n".join(
            [
                "// whole-line comment",
                "New Load.S1a Bus1=1.1 Phases=1 Conn=Wye kW=40 kvar=20 yearly=loadshape_S1a",
                "New Load.S48 Bus1=48 Phases=3 Conn=Wye kW=210 kvar=150 ! yearly=loadshape_S48",
                "New Load.S49c Bus1=49.3 Phases=1 Conn=Wye kW=35 kvar=20 ! note yearly=loadshape_S49c",
            ]
        ),
        encoding="utf-8",
    )
    loads = {load.load_id: load for load in parse_load_definitions(loads_path)}
    assert loads["S1a"].yearly == "loadshape_s1a"
    assert loads["S48"].yearly is None
    assert loads["S49c"].yearly is None
    assert loads["S1a"].conductors == ("1",)

    transformer_path = tmp_path / "transformers.dss"
    transformer_path.write_text(
        "\n".join(
            [
                "New Transformer.reg3a phases=1 windings=2 buses=[25.1 25r.1]",
                "New Transformer.reg3c like=reg3a buses=[25.3 25r.3]",
                "New Transformer.XFM1 phases=3 windings=2",
                "~ wdg=1 bus=61s conn=Delta",
                "~ wdg=2 bus=610 conn=Delta",
            ]
        ),
        encoding="utf-8",
    )
    transformers = {item["element_id"]: item for item in parse_transformer_metadata(transformer_path)}
    assert transformers["reg3c"]["phases"] == 1
    assert (transformers["reg3c"]["bus1"], transformers["reg3c"]["bus2"]) == (
        "25",
        "25r",
    )
    assert (transformers["xfm1"]["bus1"], transformers["xfm1"]["bus2"]) == (
        "61s",
        "610",
    )

    coords_path = tmp_path / "Buscoords.dss"
    coords_path.write_text("1 0 0\ns1a 1 1\n// ignored\n9r,2,2\n", encoding="utf-8")
    assert parse_buscoord_labels(coords_path) == ["1", "s1a", "9r"]


def test_canonical_blob_hash_is_line_ending_sensitive(tmp_path: Path) -> None:
    lf_path = tmp_path / "lf.dss"
    crlf_path = tmp_path / "crlf.dss"
    lf_path.write_bytes(b"New Line.L1 Bus1=1 Bus2=2\n")
    crlf_path.write_bytes(b"New Line.L1 Bus1=1 Bus2=2\r\n")
    assert sha256_file(lf_path) != sha256_file(crlf_path)


def _fixture_load(load_id: str) -> dict[str, object]:
    match = re.fullmatch(r"S(\d+)([abc])", load_id)
    assert match is not None
    phase = match.group(2).upper()
    return {"load_id": load_id, "base_bus": match.group(1), "phase": phase}


def test_clustered_split_matches_frozen_outcome_blind_membership() -> None:
    loads = [_fixture_load(load_id) for load_id in EXPECTED_CALIBRATION_IDS | EXPECTED_CONFIRMATION_IDS]
    split = allocate_cluster_split(loads)
    calibration_buses = set(split["calibration_buses"])
    observed_calibration = {load["load_id"] for load in loads if load["base_bus"] in calibration_buses}
    observed_confirmation = {load["load_id"] for load in loads} - observed_calibration
    assert observed_calibration == EXPECTED_CALIBRATION_IDS
    assert observed_confirmation == EXPECTED_CONFIRMATION_IDS
    assert split["calibration_target_bus_count"] == 16


def test_prepare_never_invokes_numeric_profile_loader(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    fake_loads = [
        LoadDefinition(
            load_id=f"S{index}{phase.lower()}",
            bus1=f"{index}.{conductor}",
            base_bus=str(index),
            conductors=(conductor,),
            phases=1,
            conn="wye",
            kw=1.0,
            kvar=0.0,
            yearly=f"shape_{index}",
        )
        for index, (phase, conductor) in enumerate(
            [("A", "1"), ("B", "2"), ("C", "3"), ("A", "1"), ("B", "2"), ("C", "3")],
            start=200,
        )
    ]
    fake_catalog = [
        {
            "shape_id": load.yearly,
            "profile_path": f"profiles/{load.load_id}.csv",
            "profile_exists": True,
            "sha256": f"hash-{load.load_id}",
            "byte_size": 1,
            "nonempty_row_count": 35_040,
            "declared_npts": 35_040,
            "declared_interval_hours": 0.25,
            "numeric_values_accessed": False,
            "git_blob_oid": None,
            "git_blob_byte_size": None,
        }
        for load in fake_loads
    ]
    graph = nx.path_graph([str(index) for index in range(200, 206)])
    monkeypatch.setattr(prospective_module, "verify_source", lambda *_args, **_kwargs: {"fixture": True})
    monkeypatch.setattr(prospective_module, "parse_load_definitions", lambda _path: fake_loads)
    monkeypatch.setattr(
        prospective_module,
        "_loadshape_catalog",
        lambda *_args, **_kwargs: (fake_catalog, {item["shape_id"]: item for item in fake_catalog}),
    )
    monkeypatch.setattr(
        prospective_module,
        "build_corrected_physical_graph",
        lambda *_args, **_kwargs: graph.copy(),
    )
    monkeypatch.setattr(prospective_module, "_line_edges", lambda _path: [])
    monkeypatch.setattr(prospective_module, "parse_transformer_metadata", lambda _path: [])
    monkeypatch.setattr(prospective_module, "derive_source_bus", lambda _path: "150")

    prepared = prepare_prospective(tmp_path, require_git=False, enforce_pinned_counts=False)
    assert prepared["nonlegacy_profile_values_or_statistics_accessed"] is False
    assert prepared["access_plan"]["prepare"]["numeric_profile_paths_allowed"] == []


def test_confirmation_rejects_wrong_digest_before_profile_access(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    accessed = []
    monkeypatch.setattr(
        "experiments.oedi_ieee123_reconstruction.prospective_confirm.load_numeric_profile",
        lambda path: accessed.append(path),
    )
    with pytest.raises(SourceIntegrityError, match="remains locked"):
        execute_confirmation(
            tmp_path,
            {"freeze_digest_sha256": "approved"},
            unlock_digest="wrong",
            approved_prepared_payload_sha256="not-reached",
            require_git=False,
        )
    assert accessed == []


def test_confirmation_rejects_tampered_prepared_payload_before_profile_access(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    accessed = []
    monkeypatch.setattr(
        "experiments.oedi_ieee123_reconstruction.prospective_confirm.load_numeric_profile",
        lambda path: accessed.append(path),
    )
    prepared = {"freeze_digest_sha256": "approved", "sentinel": "reviewed"}
    approved_hash = canonical_json_sha256(prepared)
    prepared["sentinel"] = "tampered"
    with pytest.raises(SourceIntegrityError, match="approved canonical payload hash"):
        execute_confirmation(
            tmp_path,
            prepared,
            unlock_digest="approved",
            approved_prepared_payload_sha256=approved_hash,
            require_git=False,
        )
    assert accessed == []


def test_profile_catalog_rejects_working_bytes_that_differ_from_canonical_blob(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    profile_path = tmp_path / "profiles" / "load.csv"
    profile_path.parent.mkdir()
    profile_path.write_bytes(b"1.0\n2.0\n")
    definition = LoadShapeDefinition(
        shape_id="shape_1",
        npts=35_040,
        interval_hours=0.25,
        profile_path="profiles/load.csv",
    )
    monkeypatch.setattr(prospective_module, "parse_loadshape_definitions", lambda _path: [definition])
    monkeypatch.setattr(
        prospective_module,
        "git_blob_metadata",
        lambda *_args: {
            "git_blob_oid": "0" * 40,
            "git_blob_byte_size": profile_path.stat().st_size,
            "canonical_git_blob_sha256": "0" * 64,
        },
    )
    with pytest.raises(SourceIntegrityError, match="do not match the canonical pinned Git blob"):
        _loadshape_catalog(tmp_path, include_git_metadata=True)


def test_failed_admitted_profile_attempts_remain_in_access_ledger(tmp_path: Path) -> None:
    short_path = tmp_path / "short.csv"
    short_path.write_text("1.0\n2.0\n", encoding="utf-8")
    admitted = [
        {
            "load_id": "Smissing",
            "membership": "calibration",
            "profile_path": "missing.csv",
            "profile_sha256": "0" * 64,
        },
        {
            "load_id": "Sshort",
            "membership": "confirmation",
            "profile_path": "short.csv",
            "profile_sha256": sha256_file(short_path),
        },
    ]
    profiles, invalid, access_log, ledger = _load_admitted_profiles(tmp_path, admitted)
    assert profiles == {}
    assert len(invalid) == 2
    assert access_log == []
    assert [record["status"] for record in ledger] == [
        "failed_hash_access",
        "failed_numeric_qc",
    ]
    assert ledger[0]["numeric_parse_attempted"] is False
    assert ledger[1]["numeric_parse_attempted"] is True


def test_post_access_statistic_failure_returns_durable_indeterminate_ledger(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    loads = []
    for index in range(60):
        phase = ("A", "B", "C")[index % 3]
        loads.append(
            {
                "load_id": f"S{index}{phase.lower()}",
                "base_bus": str(index + 1),
                "phase": phase,
                "profile_path": f"profiles/{index}.csv",
                "profile_sha256": "fixture-profile-hash",
                "mapping_status": "explicit_active_yearly_mapping",
                "profile_metadata_valid": True,
                "membership": "confirmation",
            }
        )
    prepared = {
        "freeze_digest_sha256": "pending",
        "source_inventory_sha256": canonical_json_sha256([]),
        "split_manifest_sha256": "pending",
        "loadshape_catalog": [],
        "loads": loads,
        "split": {"fixture": True},
        "mapping_amendment": {"fixture": True},
        "pre_outcome_status": "pass",
        "lateral_root_bus": "150",
    }
    prepared["split_manifest_sha256"] = compute_split_manifest_hash(prepared)
    source_hashes = {confirm_module.PROTOCOL_PATH.name: "hash"}
    versions = {"python": "fixture"}
    prepared["freeze_components"] = {
        "protocol_sha256": "hash",
        "source_code_hashes": source_hashes,
        "upstream_commit": confirm_module.PINNED_COMMIT,
        "source_inventory_sha256": prepared["source_inventory_sha256"],
        "split_manifest_sha256": prepared["split_manifest_sha256"],
        "runtime_versions": versions,
    }
    prepared["freeze_digest_sha256"] = canonical_json_sha256(prepared["freeze_components"])
    monkeypatch.setattr(confirm_module, "_source_code_hashes", lambda: source_hashes)
    monkeypatch.setattr(confirm_module, "runtime_versions", lambda: versions)
    monkeypatch.setattr(confirm_module, "verify_source", lambda *_args, **_kwargs: {"fixture": True})
    monkeypatch.setattr(confirm_module, "sha256_file", lambda _path: "fixture-profile-hash")
    values = np.arange(35_040, dtype=float)
    monkeypatch.setattr(confirm_module, "load_numeric_profile", lambda _path: values)
    monkeypatch.setattr(
        confirm_module,
        "_post_access_statistics",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(SourceIntegrityError("undefined fixture")),
    )

    approved_hash = canonical_json_sha256(prepared)
    summary, ledger = execute_confirmation(
        tmp_path,
        prepared,
        unlock_digest=prepared["freeze_digest_sha256"],
        approved_prepared_payload_sha256=approved_hash,
        require_git=False,
    )
    assert summary["status"] == "indeterminate"
    assert "post-access statistic undefined" in summary["reason"]
    assert len(ledger) == 60
    assert all(record["status"] == "success" for record in ledger)


def test_exact_qap_enumerates_unique_bus_bundle_allocations() -> None:
    graph = nx.path_graph(["1", "2", "3", "4"])
    loads = [{"load_id": f"S{bus}a", "base_bus": bus, "phase": "A"} for bus in ("1", "2", "3", "4")]
    vectors = {
        "S1a": np.asarray([0.0, 0.0, 1.0, 2.0, 4.0]),
        "S2a": np.asarray([0.0, 1.0, 1.0, 3.0, 5.0]),
        "S3a": np.asarray([2.0, 1.0, 0.0, 1.0, 4.0]),
        "S4a": np.asarray([4.0, 2.0, 1.0, 0.0, 0.0]),
    }
    result = qap_test(loads, graph, vectors, max_exact=100)
    assert result["method"] == "exact_unique_bus_bundle_enumeration"
    assert result["permutation_space_size"] == 24
    assert result["enumerated"] == 24
    assert result["observed_allocation_included_once"] is True


def test_full_year_residualization_is_deterministic_and_nonconstant() -> None:
    day = np.linspace(0.0, 1.0, 96)
    values = np.concatenate([day + 0.01 * index for index in range(365)])
    residual = quarter_hour_residual(values)
    assert residual.shape == (35_040,)
    assert np.var(residual) > 0.0
    np.testing.assert_allclose(np.median(residual.reshape(365, 96), axis=0), 0.0)


def test_cli_help_discloses_no_theory_support() -> None:
    result = CliRunner().invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "supplies no CGT evidence" in result.stdout
    assert "prepare" in result.stdout
    assert "confirm" in result.stdout


def test_tracked_retrospective_and_prepare_artifact_oracles() -> None:
    retrospective_dir = EXPERIMENT_DIR / "artifacts" / "retrospective"
    retrospective = json.loads((retrospective_dir / "summary.json").read_text(encoding="utf-8"))
    retrospective_provenance = json.loads((retrospective_dir / "PROVENANCE.json").read_text(encoding="utf-8"))
    assert retrospective["status"] == "pass"
    assert retrospective["historical_parser_metrics"]["oedi_graph_nodes"] == 214
    assert retrospective["historical_parser_metrics"]["isolate_count"] == 84
    assert retrospective["historical_parser_metrics"]["sensor_reachable_node_count"] == 130
    assert retrospective["alpha_interpretation"]["pv_greater_equal_0_2_mask_count"] == 15_098
    corrected = retrospective["corrected_physical_graph"]
    assert (corrected["node_count"], corrected["edge_count"]) == (130, 129)
    sensor = corrected["sensor_diagnostics_energized_graph"]
    assert sensor["unreachable_node_count"] == 0
    assert sensor["sensor_coverage_mean_hops"] == pytest.approx(0.4230769230769231)
    assert sensor["sensor_coverage_max_hops"] == 3.0
    assert sensor["sensor_degree_mean"] == pytest.approx(1.6823529411764706)
    assert sensor["nonsensor_degree_mean"] == pytest.approx(2.5555555555555554)
    assert sensor["sensor_betweenness_mean"] == pytest.approx(0.047335271317829455)
    assert sensor["nonsensor_betweenness_mean"] == pytest.approx(0.16731804478897502)
    assert retrospective_provenance["summary_canonical_json_sha256"] == canonical_json_sha256(retrospective)

    prepare_dir = EXPERIMENT_DIR / "artifacts" / "prospective_prepare"
    prepared = json.loads((prepare_dir / "summary.json").read_text(encoding="utf-8"))
    assert prepared["pre_outcome_status"] == "pass"
    assert len(prepared["loadshape_catalog"]) == 91
    assert all(item["git_blob_oid"] for item in prepared["loadshape_catalog"])
    assert all(item["canonical_git_blob_sha256"] == item["sha256"] for item in prepared["loadshape_catalog"])
    assert prepared["adequacy"]["confirmation_profile_count"] == 61
    assert prepared["adequacy"]["confirmation_phase_counts"] == {"A": 25, "B": 16, "C": 20}
    assert prepared["nonlegacy_profile_values_or_statistics_accessed"] is False
    assert prepared["access_plan"]["confirm"]["status"].startswith("locked")
    assert prepared["source_inventory_sha256"] == compute_source_inventory_hash(prepared)
    assert prepared["split_manifest_sha256"] == compute_split_manifest_hash(prepared)
    assert prepared["freeze_digest_sha256"] == canonical_json_sha256(prepared["freeze_components"])
    freeze_lock_path = prepare_dir / "FREEZE_LOCK.json"
    freeze_lock = json.loads(freeze_lock_path.read_text(encoding="utf-8"))
    assert freeze_lock["prepared_summary_file_sha256"] == sha256_file(prepare_dir / "summary.json")
    assert freeze_lock["prepared_summary_canonical_json_sha256"] == canonical_json_sha256(prepared)
    checksums = json.loads((prepare_dir / "CHECKSUMS.json").read_text(encoding="utf-8"))
    assert checksums["files"]["ACCESS_PLAN.json"] == sha256_file(prepare_dir / "ACCESS_PLAN.json")
