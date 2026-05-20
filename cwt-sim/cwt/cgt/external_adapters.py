"""External data source adapters for the CWT-CGT externalization workstream.

This module provides dataclasses describing external source specifications and
graph bundles, a manifest loader, stub adapter functions for ingesting CSV data
from known public sources (Citi Bike, Divvy, Chicago Traffic Tracker, NYC DOT,
OEDI), a proximity-based station-graph builder, and a factory for empty bundles.

None of the functions here import from cwt.layers, cwt.geometry, cwt.orchestrator,
cwt.experiments, cwt.baselines, or cwt_lab.  They are standalone ingestion
helpers that produce pandas DataFrames which upstream pipeline code may consume.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
import json
import pandas as pd


@dataclass
class ExternalSourceSpec:
    """Metadata describing one external dataset candidate.

    Attributes:
        name: Human-readable name of the dataset.
        domain: Thematic domain (e.g. ``"mobility_events"``, ``"power_grid"``).
        official_source: URL of the authoritative source.
        historical_access: Description of how historical data are accessed.
        realtime_access: Description of real-time or live-feed access, if any.
        priority: Prioritisation tier — ``"P1"`` (immediate) or ``"P2"`` (deferred).
        notes: Optional free-form notes.
    """

    name: str
    domain: str
    official_source: str
    historical_access: str
    realtime_access: Optional[str] = None
    priority: str = "P2"
    notes: Optional[str] = None


@dataclass
class ExternalGraphBundle:
    """Container holding all DataFrames that constitute an ingested external graph.

    Attributes:
        nodes: Node table (one row per station / sensor / bus).
        edges: Edge table (one row per physical link).
        states: Continuous state observations aligned to nodes.
        events: Discrete event records (e.g. trip departures/arrivals).
        observations: Aggregate or windowed observation snapshots.
        controls: Control-input series (e.g. signal timings, dispatch commands).
        metadata: Arbitrary key/value metadata from the original source.
    """

    nodes: pd.DataFrame
    edges: pd.DataFrame
    states: pd.DataFrame
    events: pd.DataFrame
    observations: pd.DataFrame
    controls: pd.DataFrame
    metadata: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Manifest loader
# ---------------------------------------------------------------------------

def load_manifest(path: str | Path) -> dict:
    """Load and return the externalization candidate manifest as a plain dict.

    Args:
        path: Filesystem path to the JSON manifest file.

    Returns:
        Parsed JSON object.  The top-level keys are ``generated_on``,
        ``purpose``, and ``candidates``.
    """
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Adapter stubs — one per candidate source
# ---------------------------------------------------------------------------

def load_citibike_trip_csv(path: str | Path) -> pd.DataFrame:
    """Load a Citi Bike NYC trip-history CSV into a DataFrame."""
    return pd.read_csv(path)


def load_divvy_trip_csv(path: str | Path) -> pd.DataFrame:
    """Load a Divvy Chicago trip-history CSV into a DataFrame."""
    return pd.read_csv(path)


def load_chicago_traffic_tracker_csv(path: str | Path) -> pd.DataFrame:
    """Load a Chicago Traffic Tracker historical-congestion CSV into a DataFrame."""
    return pd.read_csv(path)


def load_nyc_dot_traffic_csv(path: str | Path) -> pd.DataFrame:
    """Load a NYC DOT traffic-speeds CSV into a DataFrame."""
    return pd.read_csv(path)


def load_oedi_time_series_csv(path: str | Path) -> pd.DataFrame:
    """Load an OEDI time-series CSV (IEEE-123 load/PV) into a DataFrame."""
    return pd.read_csv(path)


# ---------------------------------------------------------------------------
# Graph construction helpers
# ---------------------------------------------------------------------------

def build_station_graph_from_coordinates(
    nodes: pd.DataFrame,
    radius_m: float = 500.0,
) -> pd.DataFrame:
    """Build a proximity-based edge table from a node table with coordinates.

    This is a placeholder implementation.  It returns an empty edge DataFrame
    with the canonical schema until a geospatial backend (e.g. BallTree or
    PostGIS) is chosen and integrated.

    Args:
        nodes: DataFrame with at least ``lat`` and ``lon`` columns.
        radius_m: Proximity radius in metres within which nodes are connected.

    Returns:
        Empty DataFrame with columns ``src``, ``dst``, ``weight``,
        ``edge_type``, and ``directed``.
    """
    return pd.DataFrame(columns=["src", "dst", "weight", "edge_type", "directed"])


def make_empty_bundle() -> ExternalGraphBundle:
    """Return an :class:`ExternalGraphBundle` whose every DataFrame is empty.

    Useful as a safe default when no data have been ingested yet, and as a
    fixture baseline in tests.
    """
    empty = pd.DataFrame()
    return ExternalGraphBundle(empty, empty, empty, empty, empty, empty, {})
