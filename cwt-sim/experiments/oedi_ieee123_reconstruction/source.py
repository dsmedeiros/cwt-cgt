"""Pinned-source parsing and verification for the OEDI IEEE123 reconstruction.

The parser deliberately keeps OpenDSS comment semantics: an exclamation mark
ends the active statement.  That matters because the pinned load file has two
trailing ``yearly=`` tokens inside comments; they are catalogued as unmapped
rather than inferred from load identifiers.
"""

from __future__ import annotations

import hashlib
import json
import posixpath
import re
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

import numpy as np

PINNED_COMMIT = "7c8bcca06708ea2dd54b822821d637814ef08dc4"
UPSTREAM_URL = "https://github.com/openEDI/oedisi-ieee123"
EXPERIMENT_DIR = Path(__file__).resolve().parent
UPSTREAM_MANIFEST_PATH = EXPERIMENT_DIR / "UPSTREAM_MANIFEST.json"


class SourceIntegrityError(RuntimeError):
    """Raised when a pinned source or metadata invariant does not match."""


@dataclass(frozen=True)
class DssObject:
    """One active OpenDSS object statement."""

    object_id: str
    properties: dict[str, str]
    active_text: str


@dataclass(frozen=True)
class LoadDefinition:
    """Metadata declared by one active ``New Load`` statement."""

    load_id: str
    bus1: str
    base_bus: str
    conductors: tuple[str, ...]
    phases: int
    conn: str
    kw: float
    kvar: float
    yearly: str | None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["conductors"] = list(self.conductors)
        return payload


@dataclass(frozen=True)
class LoadShapeDefinition:
    """Metadata declared by one active ``New LoadShape`` statement."""

    shape_id: str
    npts: int
    interval_hours: float
    profile_path: str


def sha256_file(path: Path) -> str:
    """Return the lower-case SHA-256 digest of a file."""

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json_sha256(payload: Any) -> str:
    """Hash strict canonical JSON used by frozen manifests."""

    encoded = json.dumps(
        payload,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def canonical_bus(bus1: str) -> str:
    """Canonicalize an OpenDSS bus without numerically coercing its identifier."""

    return bus1.strip().casefold().split(".", maxsplit=1)[0]


def bus_conductors(bus1: str) -> tuple[str, ...]:
    """Return explicitly declared conductor suffixes from a bus token."""

    pieces = [piece.strip().casefold() for piece in bus1.strip().split(".")]
    return tuple(piece for piece in pieces[1:] if piece)


def _strip_dss_comment(line: str) -> str:
    if line.lstrip().startswith("//"):
        return ""
    return line.split("!", maxsplit=1)[0].strip()


def iter_dss_statements(text: str) -> Iterable[str]:
    """Yield active OpenDSS statements with ``~`` continuations joined."""

    current: str | None = None
    for raw_line in text.splitlines():
        active = _strip_dss_comment(raw_line)
        if not active:
            continue
        if active.startswith("~"):
            if current is None:
                raise SourceIntegrityError("OpenDSS continuation appeared before a statement")
            current = f"{current} {active[1:].strip()}"
            continue
        if current is not None:
            yield current
        current = active
    if current is not None:
        yield current


_PROPERTY_PATTERN = re.compile(r"(?i)(?<![\w.])([a-z%][a-z0-9_%]*)\s*=\s*(\[[^\]]*\]|\([^)]*\)|[^\s]+)")


def parse_properties(statement: str) -> dict[str, str]:
    """Parse the final active value for each property in a DSS statement."""

    return {match.group(1).casefold(): match.group(2) for match in _PROPERTY_PATTERN.finditer(statement)}


def parse_dss_objects(path: Path, object_class: str) -> list[DssObject]:
    """Parse active objects of one OpenDSS class."""

    pattern = re.compile(rf"(?i)^new\s+(?:object=)?{re.escape(object_class)}\.([^\s]+)\s*(.*)$")
    objects: list[DssObject] = []
    for statement in iter_dss_statements(path.read_text(encoding="utf-8-sig")):
        match = pattern.match(statement)
        if match is None:
            continue
        objects.append(
            DssObject(
                object_id=match.group(1),
                properties=parse_properties(match.group(2)),
                active_text=statement,
            )
        )
    return objects


def parse_load_definitions(path: Path) -> list[LoadDefinition]:
    """Parse the 91 pinned load definitions without opening profile values."""

    loads: list[LoadDefinition] = []
    for item in parse_dss_objects(path, "load"):
        props = item.properties
        required = ("bus1", "phases", "conn", "kw", "kvar")
        missing = [name for name in required if name not in props]
        if missing:
            raise SourceIntegrityError(f"Load {item.object_id} is missing active properties {missing}")
        bus1 = props["bus1"]
        loads.append(
            LoadDefinition(
                load_id=item.object_id,
                bus1=bus1,
                base_bus=canonical_bus(bus1),
                conductors=bus_conductors(bus1),
                phases=int(props["phases"]),
                conn=props["conn"].casefold(),
                kw=float(props["kw"]),
                kvar=float(props["kvar"]),
                yearly=props.get("yearly", None).casefold() if props.get("yearly") else None,
            )
        )
    return loads


_FILE_PATTERN = re.compile(r"(?i)file\s*=\s*([^\s)]+)")


def parse_loadshape_definitions(path: Path) -> list[LoadShapeDefinition]:
    """Parse declared load-shape metadata without numerically loading a CSV."""

    shapes: list[LoadShapeDefinition] = []
    for item in parse_dss_objects(path, "loadshape"):
        props = item.properties
        mult = props.get("mult", "")
        file_match = _FILE_PATTERN.search(mult)
        if file_match is None:
            raise SourceIntegrityError(f"LoadShape {item.object_id} has no active mult file")
        raw_path = file_match.group(1).replace("\\", "/")
        # Load-shape paths are relative to qsts/, not to this experiment.
        normalized = posixpath.normpath(posixpath.join("qsts", raw_path))
        shapes.append(
            LoadShapeDefinition(
                shape_id=item.object_id.casefold(),
                npts=int(props["npts"]),
                interval_hours=float(props["interval"]),
                profile_path=normalized,
            )
        )
    return shapes


def parse_buscoord_labels(path: Path) -> list[str]:
    """Parse every non-comment Buscoords label, including historical device labels."""

    labels: list[str] = []
    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith(("!", "//")):
            continue
        token = re.split(r"[\s,]+", stripped, maxsplit=1)[0]
        labels.append(token.casefold())
    return labels


def parse_sensor_buses(path: Path) -> set[str]:
    """Parse unique base buses from phase-qualified sensor locations."""

    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list) or not all(isinstance(value, str) for value in payload):
        raise SourceIntegrityError("sensors.json must be a list of strings")
    return {canonical_bus(value) for value in payload}


def count_nonempty_rows_bytes(path: Path) -> int:
    """Count physical data rows without converting profile bytes to numbers."""

    return sum(1 for line in path.read_bytes().splitlines() if line.strip())


def load_numeric_profile(path: Path, expected_count: int = 35_040) -> np.ndarray:
    """Open one explicitly authorized numeric profile and enforce strict QC."""

    try:
        values = np.loadtxt(path, dtype=float, ndmin=1)
    except (OSError, ValueError) as exc:
        raise SourceIntegrityError(f"Could not parse numeric profile {path}: {exc}") from exc
    values = np.asarray(values, dtype=float).reshape(-1)
    if values.size != expected_count:
        raise SourceIntegrityError(f"Profile {path} has {values.size} values; expected {expected_count}")
    if not np.all(np.isfinite(values)):
        raise SourceIntegrityError(f"Profile {path} contains non-finite values")
    return values


def load_upstream_manifest() -> dict[str, Any]:
    """Load the tracked pinned-file manifest."""

    return json.loads(UPSTREAM_MANIFEST_PATH.read_text(encoding="utf-8"))


def _git_value(source_dir: Path, *args: str) -> str:
    resolved = source_dir.resolve().as_posix()
    completed = subprocess.run(
        ["git", "-c", f"safe.directory={resolved}", "-C", str(source_dir), *args],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if completed.returncode != 0:
        raise SourceIntegrityError(completed.stderr.strip() or "git provenance command failed")
    return completed.stdout.strip()


def git_blob_metadata(source_dir: Path, relative_path: str) -> dict[str, Any]:
    """Return canonical pinned Git-blob identity without opening numeric values."""

    oid = _git_value(source_dir, "rev-parse", f"{PINNED_COMMIT}:{relative_path}")
    size = int(_git_value(source_dir, "cat-file", "-s", oid))
    completed = subprocess.run(
        [
            "git",
            "-c",
            f"safe.directory={source_dir.resolve().as_posix()}",
            "-C",
            str(source_dir),
            "cat-file",
            "blob",
            oid,
        ],
        check=False,
        capture_output=True,
        timeout=30,
    )
    if completed.returncode != 0:
        raise SourceIntegrityError(
            completed.stderr.decode("utf-8", errors="replace").strip()
            or f"Could not read canonical Git blob {oid}"
        )
    if len(completed.stdout) != size:
        raise SourceIntegrityError(
            f"Canonical Git blob {oid} returned {len(completed.stdout)} bytes; expected {size}"
        )
    return {
        "git_blob_oid": oid,
        "git_blob_byte_size": size,
        "canonical_git_blob_sha256": hashlib.sha256(completed.stdout).hexdigest(),
    }


def verify_source(source_dir: Path, *, require_git: bool = True) -> dict[str, Any]:
    """Verify the pinned Git revision and every tracked selected-file digest."""

    source_dir = source_dir.resolve()
    manifest = load_upstream_manifest()
    file_results: list[dict[str, Any]] = []
    for record in manifest["files"]:
        path = source_dir / Path(record["path"])
        if not path.is_file():
            raise SourceIntegrityError(f"Missing pinned source file: {record['path']}")
        observed = sha256_file(path)
        expected = record["sha256"].casefold()
        if observed != expected:
            raise SourceIntegrityError(
                f"SHA-256 mismatch for {record['path']}: expected {expected}, observed {observed}"
            )
        if path.stat().st_size != record["byte_size"]:
            raise SourceIntegrityError(
                f"Byte-size mismatch for {record['path']}: expected {record['byte_size']}, "
                f"observed {path.stat().st_size}. Use a core.autocrlf=false checkout."
            )
        file_results.append(
            {
                "path": record["path"],
                "sha256": observed,
                "byte_size": path.stat().st_size,
                "git_blob_oid": record["git_blob_oid"],
                "git_blob_byte_size": record["byte_size"],
                "canonical_git_blob_sha256": record["sha256"],
                "access_level": record["access_level"],
                "metric_affecting": record["metric_affecting"],
                "verified": True,
            }
        )

    git_result: dict[str, Any]
    if require_git:
        head = _git_value(source_dir, "rev-parse", "HEAD")
        remote = _git_value(source_dir, "remote", "get-url", "origin").removesuffix(".git")
        if head != PINNED_COMMIT:
            raise SourceIntegrityError(f"Expected Git HEAD {PINNED_COMMIT}, observed {head}")
        if remote.casefold() != UPSTREAM_URL.casefold():
            raise SourceIntegrityError(f"Expected origin {UPSTREAM_URL}, observed {remote}")
        git_result = {"head": head, "origin": remote, "verified": True}
        for record in manifest["files"]:
            blob = git_blob_metadata(source_dir, record["path"])
            if blob["git_blob_oid"] != record["git_blob_oid"]:
                raise SourceIntegrityError(
                    f"Git blob mismatch for {record['path']}: expected "
                    f"{record['git_blob_oid']}, observed {blob['git_blob_oid']}"
                )
            if blob["canonical_git_blob_sha256"] != record["sha256"]:
                raise SourceIntegrityError(
                    f"Canonical Git-blob SHA-256 mismatch for {record['path']}: expected "
                    f"{record['sha256']}, observed {blob['canonical_git_blob_sha256']}"
                )
    else:
        git_result = {"head": "fixture_not_checked", "origin": "fixture_not_checked", "verified": False}

    return {
        "dataset_id": manifest["dataset_id"],
        "pinned_commit": PINNED_COMMIT,
        "repository_url": UPSTREAM_URL,
        "git": git_result,
        "files": file_results,
    }


def acquire_pinned_source(destination: Path) -> None:
    """Clone and detach the exact upstream revision into a new directory."""

    destination = destination.resolve()
    if destination.exists():
        raise SourceIntegrityError(f"Acquisition destination already exists: {destination}")
    subprocess.run(
        ["git", "-c", "core.autocrlf=false", "clone", UPSTREAM_URL, str(destination)],
        check=True,
        timeout=300,
    )
    subprocess.run(
        [
            "git",
            "-c",
            f"safe.directory={destination.as_posix()}",
            "-C",
            str(destination),
            "config",
            "core.autocrlf",
            "false",
        ],
        check=True,
        timeout=30,
    )
    subprocess.run(
        [
            "git",
            "-c",
            f"safe.directory={destination.as_posix()}",
            "-C",
            str(destination),
            "checkout",
            "--detach",
            PINNED_COMMIT,
        ],
        check=True,
        timeout=120,
    )
    verify_source(destination, require_git=True)
