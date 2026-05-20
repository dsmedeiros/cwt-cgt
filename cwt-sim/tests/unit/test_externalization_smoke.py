"""Smoke tests for the externalization workstream.

Covers:
- Manifest file existence at the expected repository-relative path.
- JSON parses successfully and carries required top-level keys.
- Each candidate has required keys; at least one P1 candidate present.
- load_manifest() returns a dict.
- make_empty_bundle() returns an ExternalGraphBundle with empty DataFrames.
- ExternalSourceSpec dataclass: required fields accepted; default priority "P2".
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from cwt.cgt.external_adapters import (
    ExternalGraphBundle,
    ExternalSourceSpec,
    load_manifest,
    make_empty_bundle,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[3]  # cwt-sim/ -> repo root is one above
# tests/unit/test_externalization_smoke.py
#   parents[0] = tests/unit/
#   parents[1] = tests/
#   parents[2] = cwt-sim/
CWTSIM_ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = (
    CWTSIM_ROOT
    / "cgt_benchmarks"
    / "externalization"
    / "CWT-CGT_Phase_230_External_Metadata_Manifest.json"
)

_REQUIRED_CANDIDATE_KEYS = {"name", "domain", "official_source", "priority"}
_REQUIRED_MANIFEST_KEYS = {"generated_on", "purpose", "candidates"}


# ---------------------------------------------------------------------------
# Manifest file and JSON structure
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_manifest_file_exists() -> None:
    """The Phase-230 manifest JSON exists at the expected path."""
    assert MANIFEST_PATH.exists(), f"Manifest not found at {MANIFEST_PATH}"


@pytest.mark.unit
def test_manifest_parses_as_json() -> None:
    """The manifest file parses without error."""
    with open(MANIFEST_PATH, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    assert isinstance(data, dict)


@pytest.mark.unit
def test_manifest_top_level_keys() -> None:
    """Manifest contains the required top-level keys."""
    with open(MANIFEST_PATH, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    missing = _REQUIRED_MANIFEST_KEYS - data.keys()
    assert not missing, f"Manifest missing keys: {missing}"


@pytest.mark.unit
def test_manifest_candidates_have_required_keys() -> None:
    """Every candidate entry has the required fields."""
    with open(MANIFEST_PATH, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    for candidate in data["candidates"]:
        missing = _REQUIRED_CANDIDATE_KEYS - candidate.keys()
        assert not missing, f"Candidate {candidate.get('name')} missing keys: {missing}"


@pytest.mark.unit
def test_manifest_has_at_least_one_p1_candidate() -> None:
    """At least one candidate must carry priority P1."""
    with open(MANIFEST_PATH, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    p1 = [c for c in data["candidates"] if c.get("priority") == "P1"]
    assert len(p1) >= 1, "Expected at least one P1 candidate in manifest"


# ---------------------------------------------------------------------------
# load_manifest()
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_load_manifest_returns_dict() -> None:
    """load_manifest() returns a plain dict."""
    result = load_manifest(MANIFEST_PATH)
    assert isinstance(result, dict)


@pytest.mark.unit
def test_load_manifest_candidate_count() -> None:
    """Manifest contains at least three candidates."""
    data = load_manifest(MANIFEST_PATH)
    assert len(data.get("candidates", [])) >= 3


# ---------------------------------------------------------------------------
# make_empty_bundle()
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_make_empty_bundle_returns_correct_type() -> None:
    """make_empty_bundle() returns an ExternalGraphBundle instance."""
    bundle = make_empty_bundle()
    assert isinstance(bundle, ExternalGraphBundle)


@pytest.mark.unit
def test_make_empty_bundle_dataframes_are_empty() -> None:
    """All DataFrames in the empty bundle have zero rows."""
    import pandas as pd

    bundle = make_empty_bundle()
    for attr in ("nodes", "edges", "states", "events", "observations", "controls"):
        df = getattr(bundle, attr)
        assert isinstance(df, pd.DataFrame), f"{attr} is not a DataFrame"
        assert len(df) == 0, f"{attr} should be empty but has {len(df)} rows"


@pytest.mark.unit
def test_make_empty_bundle_metadata_is_empty_dict() -> None:
    """The metadata field of an empty bundle is an empty dict."""
    bundle = make_empty_bundle()
    assert bundle.metadata == {}


# ---------------------------------------------------------------------------
# ExternalSourceSpec dataclass
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_external_source_spec_required_fields() -> None:
    """ExternalSourceSpec can be instantiated with the four required fields."""
    spec = ExternalSourceSpec(
        name="Test Source",
        domain="test_domain",
        official_source="https://example.com",
        historical_access="downloadable CSV",
    )
    assert spec.name == "Test Source"
    assert spec.domain == "test_domain"
    assert spec.official_source == "https://example.com"
    assert spec.historical_access == "downloadable CSV"


@pytest.mark.unit
def test_external_source_spec_default_priority() -> None:
    """ExternalSourceSpec defaults priority to P2 when not specified."""
    spec = ExternalSourceSpec(
        name="Default Priority Source",
        domain="mobility_events",
        official_source="https://example.com/data",
        historical_access="monthly archive",
    )
    assert spec.priority == "P2"


@pytest.mark.unit
def test_external_source_spec_explicit_priority() -> None:
    """ExternalSourceSpec accepts an explicit priority override."""
    spec = ExternalSourceSpec(
        name="High Priority Source",
        domain="power_grid",
        official_source="https://example.com/grid",
        historical_access="hourly CSV",
        priority="P1",
    )
    assert spec.priority == "P1"


@pytest.mark.unit
def test_external_source_spec_optional_fields_default_to_none() -> None:
    """Optional fields realtime_access and notes default to None."""
    spec = ExternalSourceSpec(
        name="Minimal",
        domain="road_segments",
        official_source="https://example.com",
        historical_access="annual dump",
    )
    assert spec.realtime_access is None
    assert spec.notes is None
