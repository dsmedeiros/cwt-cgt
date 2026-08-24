"""Git-backed adapter-lock and monotone phase-authorization verification.

This module never issues authority.  It consumes immutable records already
committed by a separate process and verifies them against Git objects.  The
pre-lock source snapshot therefore cannot authorize any response access.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from .contract import (
    COMPONENT_ORDER,
    CONTRACT_SHA256,
    GEOMETRY_PLAN_SHA256,
    calibration_call_plan,
    confirmation_call_plan,
    heldout_call_plan,
)
from .exact import canonical_json_bytes, canonical_sha256, strict_equal

PACKAGE_DIR = Path(__file__).resolve().parent
SIM_ROOT = PACKAGE_DIR.parents[1]
REPO_ROOT = SIM_ROOT.parent

ADAPTER_SOURCE_LOCK_RELATIVE = "cwt-sim/experiments/generator_tensor_response_protocol.SOURCE_LOCK.json"
ADAPTER_SOURCE_LOCK_PATH = REPO_ROOT / ADAPTER_SOURCE_LOCK_RELATIVE
SOURCE_LOCK_SCHEMA = "generator_tensor_response_adapter_source_lock_v1"
PHASE_RECORD_SCHEMA = "generator_tensor_response_external_phase_record_v1"
PHASE_RECORD_RELATIVE = {
    "CAL": "cwt-sim/experiments/generator_tensor_response_protocol.AUTHORITY.CAL.json",
    "V": "cwt-sim/experiments/generator_tensor_response_protocol.AUTHORITY.V.json",
    "H": "cwt-sim/experiments/generator_tensor_response_protocol.AUTHORITY.H.json",
}
PHASE_OUTCOME_RELATIVE = {
    "CAL": "cwt-sim/experiments/generator_tensor_response_protocol.OUTCOME.CAL.json",
    "V": "cwt-sim/experiments/generator_tensor_response_protocol.OUTCOME.V.json",
    "H": "cwt-sim/experiments/generator_tensor_response_protocol.OUTCOME.H.json",
}
PHASE_RESULT_RELATIVE = {
    "CAL": "cwt-sim/experiments/generator_tensor_response_protocol.RESULT.CAL.json",
    "V": "cwt-sim/experiments/generator_tensor_response_protocol.RESULT.V.json",
    "H": "cwt-sim/experiments/generator_tensor_response_protocol.RESULT.H.json",
}
ACCESS_LEDGER_DIR = REPO_ROOT / "cwt-sim/experiments/.generator_tensor_response_protocol_access"
DURABLE_LEDGER_ROOT_ENV = "CWT_CGT_ADAPTER_DURABLE_LEDGER_ROOT"

REVIEWED_SOURCE_PATHS = (
    "cwt-sim/experiments/generator_tensor_response_protocol/MODEL_CONTRACT.md",
    "cwt-sim/experiments/generator_tensor_response_protocol/__init__.py",
    "cwt-sim/experiments/generator_tensor_response_protocol/anchors.py",
    "cwt-sim/experiments/generator_tensor_response_protocol/authority.py",
    "cwt-sim/experiments/generator_tensor_response_protocol/broker.py",
    "cwt-sim/experiments/generator_tensor_response_protocol/contract.py",
    "cwt-sim/experiments/generator_tensor_response_protocol/exact.py",
    "cwt-sim/experiments/generator_tensor_response_protocol/firewall.py",
    "cwt-sim/experiments/generator_tensor_response_protocol/fit.py",
    "cwt-sim/experiments/generator_tensor_response_protocol/geometry_plan.py",
    "cwt-sim/experiments/generator_tensor_response_protocol/protocol.py",
    "cwt-sim/experiments/generator_tensor_response_protocol/run.py",
    "cwt-sim/experiments/generator_tensor_response_protocol/theorem.py",
    "cwt-sim/tests/experiments/test_generator_tensor_response_protocol.py",
)

_LOCK_KEYS = {
    "schema",
    "source_commit_oid",
    "source_tree_oid",
    "source_parent_oid",
    "git_object_format",
    "entries",
    "path_set_sha256",
    "entries_sha256",
    "source_bundle_sha256",
}
_ENTRY_KEYS = {"path", "mode", "blob_oid", "size", "sha256_raw"}
_START_KEYS = {
    "schema",
    "state",
    "phase",
    "sequence",
    "session_id",
    "authority_commit_oid",
    "authority_record_sha256",
    "request_ids",
}
_OUTCOME_KEYS = {
    "schema",
    "phase",
    "sequence",
    "session_id",
    "authority_record_sha256",
    "outcome",
}
_PHASE_KEYS = {
    "schema",
    "phase",
    "sequence",
    "decision",
    "session_id",
    "adapter_source_lock_commit_oid",
    "adapter_source_lock_sha256",
    "adapter_source_commit_oid",
    "adapter_source_tree_oid",
    "plan_sha256",
    "contract_sha256",
    "prior_authority_commit_oid",
    "prior_record_sha256",
    "prior_state",
    "prediction_sha256",
    "prediction_record",
    "request_ids",
}
_EXTERNAL_OUTCOME_KEYS = {
    "schema",
    "phase",
    "sequence",
    "session_id",
    "phase_authority_commit_oid",
    "phase_authority_record_sha256",
    "response_result_sha256",
    "outcome",
    "prediction_sha256",
    "prediction_record",
}
_PHASE_RESULT_KEYS = {
    "schema",
    "phase",
    "sequence",
    "session_id",
    "authority_commit_oid",
    "authority_record_sha256",
    "request_ids",
    "sample_call_count",
    "normalized_excess_vectors",
    "heldout_scalar_projection",
    "direct_fcs_crosscheck_complete",
}
_VERIFIED_SEAL = object()
GIT_DIR_ENV = "CWT_CGT_ADAPTER_GIT_DIR"
GIT_INDEX_ENV = "CWT_CGT_ADAPTER_GIT_INDEX_FILE"
GIT_WORK_TREE_ENV = "CWT_CGT_ADAPTER_GIT_WORK_TREE"
GIT_EXECUTABLE_ENV = "CWT_CGT_ADAPTER_GIT_EXECUTABLE"
PYTHON_EXECUTABLE_ENV = "CWT_CGT_ADAPTER_PYTHON_EXECUTABLE"


class AuthorityVerificationError(RuntimeError):
    """An external Git-backed authority record failed closed."""


@dataclass(frozen=True)
class _VerifiedAdapterSourceLock:
    authority_commit_oid: str
    source_commit_oid: str
    source_tree_oid: str
    raw_sha256: str
    plan_sha256: str
    seal: object

    def authentic(self) -> bool:
        return type(self) is _VerifiedAdapterSourceLock and self.seal is _VERIFIED_SEAL


@dataclass(frozen=True)
class _VerifiedPhaseAuthorization:
    phase: str
    sequence: int
    session_id: str
    authority_commit_oid: str
    raw_sha256: str
    plan_sha256: str
    adapter_source_lock_commit_oid: str
    adapter_source_lock_sha256: str
    adapter_source_commit_oid: str
    adapter_source_tree_oid: str
    prior_authority_commit_oid: str
    prior_record_sha256: str
    prior_state: str
    prediction_sha256: str | None
    request_ids: tuple[str, ...]
    seal: object

    def authentic(self) -> bool:
        return type(self) is _VerifiedPhaseAuthorization and self.seal is _VERIFIED_SEAL


def _is_lower_hex(value: object, length: int) -> bool:
    return (
        type(value) is str
        and len(value) == length
        and all(character in "0123456789abcdef" for character in value)
    )


def _canonical_repo_path(value: object) -> str:
    if type(value) is not str:
        raise AuthorityVerificationError("authority path type refused")
    parsed = PurePosixPath(value)
    if (
        not value
        or parsed.is_absolute()
        or parsed.as_posix() != value
        or "." in parsed.parts
        or ".." in parsed.parts
        or "\\" in value
        or ":" in value
    ):
        raise AuthorityVerificationError("authority path is noncanonical")
    return value


def _ordinary_file(path: Path, *, label: str) -> Path:
    if not path.is_absolute():
        raise AuthorityVerificationError(f"{label} path is not absolute")
    current = Path(path.anchor)
    for part in path.parts[1:]:
        current /= part
        attributes = current.lstat().st_file_attributes if current.exists() and sys.platform == "win32" else 0
        reparse = bool(sys.platform == "win32" and attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT)
        if not current.exists() or current.is_symlink() or reparse:
            raise AuthorityVerificationError(f"{label} path is absent or linked")
        if os.path.islink(current):
            raise AuthorityVerificationError(f"{label} path is linked")
    if not path.is_file():
        raise AuthorityVerificationError(f"{label} is not an ordinary file")
    return path.resolve(strict=True)


def _git(arguments: list[str]) -> bytes:
    configured_executable = os.environ.get(GIT_EXECUTABLE_ENV)
    executable = configured_executable or shutil.which("git")
    if executable is None:
        raise AuthorityVerificationError("trusted Git executable is unavailable")
    executable_path = Path(executable)
    if configured_executable is not None and not executable_path.is_absolute():
        raise AuthorityVerificationError("trusted Git executable must be absolute")
    executable_path = _ordinary_file(executable_path.resolve(strict=True), label="trusted Git executable")
    environment = {key: value for key, value in os.environ.items() if not key.upper().startswith("GIT_")}
    environment["GIT_OPTIONAL_LOCKS"] = "0"
    configured_git_dir = os.environ.get(GIT_DIR_ENV)
    configured_index = os.environ.get(GIT_INDEX_ENV)
    configured_work_tree = os.environ.get(GIT_WORK_TREE_ENV)
    if configured_git_dir is None or configured_index is None or configured_work_tree is None:
        raise AuthorityVerificationError("authority requires explicit Git dir/index/worktree")
    git_dir = Path(configured_git_dir)
    index = Path(configured_index)
    work_tree = Path(configured_work_tree)
    if (
        not git_dir.is_absolute()
        or not git_dir.is_dir()
        or git_dir.is_symlink()
        or not index.is_absolute()
        or _ordinary_file(index.resolve(strict=True), label="explicit adapter Git index") != index.resolve()
        or not work_tree.is_absolute()
        or work_tree.resolve(strict=True) != REPO_ROOT.resolve(strict=True)
    ):
        raise AuthorityVerificationError("explicit adapter Git binding refused")
    environment["GIT_DIR"] = str(git_dir.resolve(strict=True))
    environment["GIT_INDEX_FILE"] = str(index.resolve(strict=True))
    environment["GIT_WORK_TREE"] = str(work_tree.resolve(strict=True))
    try:
        result = subprocess.run(
            [
                str(executable_path),
                "--no-replace-objects",
                "-c",
                f"safe.directory={REPO_ROOT}",
                *arguments,
            ],
            cwd=REPO_ROOT,
            env=environment,
            check=True,
            capture_output=True,
            timeout=30,
        )
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise AuthorityVerificationError("Git-backed authority is unavailable") from exc
    return result.stdout


def _parse_commit(oid: str) -> tuple[str, tuple[str, ...]]:
    if not _is_lower_hex(oid, 40):
        raise AuthorityVerificationError("authority commit OID refused")
    if _git(["cat-file", "-t", oid]).strip() != b"commit":
        raise AuthorityVerificationError("authority object is not a commit")
    try:
        header = _git(["cat-file", "-p", oid]).split(b"\n\n", 1)[0].decode("ascii")
    except UnicodeError as exc:
        raise AuthorityVerificationError("commit header is not ASCII") from exc
    tree: str | None = None
    parents: list[str] = []
    for line in header.splitlines():
        if line.startswith("tree "):
            tree = line[5:]
        elif line.startswith("parent "):
            parents.append(line[7:])
    if tree is None or not _is_lower_hex(tree, 40) or any(not _is_lower_hex(item, 40) for item in parents):
        raise AuthorityVerificationError("commit identity is malformed")
    return tree, tuple(parents)


def _blob_at(commit_oid: str, relative: str) -> tuple[str, bytes]:
    relative = _canonical_repo_path(relative)
    raw = _git(["ls-tree", "-z", commit_oid, "--", relative])
    records = tuple(item for item in raw.split(b"\0") if item)
    if len(records) != 1:
        raise AuthorityVerificationError("authority path is not one exact Git entry")
    try:
        metadata, encoded_path = records[0].split(b"\t", 1)
        mode, kind, oid = metadata.decode("ascii").split(" ")
        found_path = encoded_path.decode("utf-8")
    except (ValueError, UnicodeError) as exc:
        raise AuthorityVerificationError("Git entry is malformed") from exc
    if mode != "100644" or kind != "blob" or found_path != relative or not _is_lower_hex(oid, 40):
        raise AuthorityVerificationError("Git entry identity refused")
    return oid, _git(["cat-file", "blob", oid])


def _parse_canonical_json(raw: bytes, *, keys: set[str], label: str) -> dict[str, object]:
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise AuthorityVerificationError(f"{label} is not canonical JSON") from exc
    if type(payload) is not dict or set(payload) != keys or canonical_json_bytes(payload) != raw:
        raise AuthorityVerificationError(f"{label} schema or canonical bytes differ")
    return payload


def _canonical_fraction_json(value: object) -> bool:
    if type(value) is not dict or set(value) != {"denominator_hex", "numerator_hex"}:
        return False
    numerator = value["numerator_hex"]
    denominator = value["denominator_hex"]
    if type(numerator) is not str or type(denominator) is not str:
        return False
    unsigned = numerator[1:] if numerator.startswith("-") else numerator
    if (
        not unsigned
        or not denominator
        or any(character not in "0123456789abcdef" for character in unsigned)
        or any(character not in "0123456789abcdef" for character in denominator)
        or (numerator.startswith("-") and unsigned == "0")
        or (len(unsigned) > 1 and unsigned.startswith("0"))
        or (len(denominator) > 1 and denominator.startswith("0"))
    ):
        return False
    numerator_value = int(unsigned, 16) * (-1 if numerator.startswith("-") else 1)
    denominator_value = int(denominator, 16)
    if denominator_value <= 0:
        return False
    from fractions import Fraction

    reduced = Fraction(numerator_value, denominator_value)
    return reduced.numerator == numerator_value and reduced.denominator == denominator_value


def _canonical_vector_json(value: object) -> bool:
    return type(value) is list and len(value) == 3 and all(_canonical_fraction_json(item) for item in value)


def _validate_phase_result_payload(
    payload: object,
    *,
    phase_commit_oid: str,
    phase_payload: dict[str, object],
    phase_raw: bytes,
    prediction_payload: dict[str, object],
) -> bool:
    """Bind one committed response result to its authority and locked prediction."""

    if (
        type(payload) is not dict
        or set(payload) != _PHASE_RESULT_KEYS
        or payload["schema"] != "generator_tensor_response_phase_result_v1"
        or payload["phase"] != phase_payload["phase"]
        or type(payload["sequence"]) is not int
        or payload["sequence"] != phase_payload["sequence"]
        or payload["session_id"] != phase_payload["session_id"]
        or payload["authority_commit_oid"] != phase_commit_oid
        or payload["authority_record_sha256"] != hashlib.sha256(phase_raw).hexdigest()
        or not strict_equal(payload["request_ids"], phase_payload["request_ids"])
        or payload["direct_fcs_crosscheck_complete"] is not True
        or type(payload["direct_fcs_crosscheck_complete"]) is not bool
        or type(payload["sample_call_count"]) is not int
    ):
        return False
    phase = phase_payload["phase"]
    expected_counts = {"CAL": 12, "V": 4, "H": 2}
    expected_vectors = {"CAL": 6, "V": 2, "H": 0}
    vectors = payload["normalized_excess_vectors"]
    if (
        phase not in expected_counts
        or payload["sample_call_count"] != expected_counts[phase]
        or type(vectors) is not list
        or len(vectors) != expected_vectors[phase]
        or any(not _canonical_vector_json(vector) for vector in vectors)
    ):
        return False
    if phase == "CAL":
        fit_record = prediction_payload.get("fit_record")
        return (
            payload["heldout_scalar_projection"] is None
            and type(fit_record) is dict
            and strict_equal(vectors, fit_record.get("observed_deltas"))
        )
    if phase == "V":
        return payload["heldout_scalar_projection"] is None and strict_equal(
            vectors, prediction_payload.get("confirmation_vectors")
        )
    return (
        vectors == []
        and _canonical_fraction_json(payload["heldout_scalar_projection"])
        and strict_equal(
            payload["heldout_scalar_projection"],
            prediction_payload.get("heldout_scalar_projection"),
        )
    )


def _require_exact_commit_delta(commit_oid: str, parent_oid: str, expected_paths: tuple[str, ...]) -> None:
    raw = _git(
        [
            "diff-tree",
            "--no-commit-id",
            "--name-status",
            "-z",
            "-r",
            parent_oid,
            commit_oid,
            "--",
        ]
    )
    tokens = tuple(item for item in raw.split(b"\0") if item)
    try:
        records = tuple(
            (tokens[index].decode("ascii"), tokens[index + 1].decode("utf-8"))
            for index in range(0, len(tokens), 2)
        )
    except (IndexError, UnicodeError) as exc:
        raise AuthorityVerificationError("external outcome commit delta is malformed") from exc
    expected = tuple(("A", _canonical_repo_path(path)) for path in sorted(expected_paths))
    if len(tokens) % 2 or tuple(sorted(records)) != expected:
        raise AuthorityVerificationError("external outcome commit delta refused")


def _entry_records(source_commit_oid: str) -> tuple[dict[str, object], ...]:
    records: list[dict[str, object]] = []
    for relative in REVIEWED_SOURCE_PATHS:
        oid, raw = _blob_at(source_commit_oid, relative)
        path = REPO_ROOT.joinpath(*PurePosixPath(relative).parts)
        checked = _ordinary_file(path, label=f"reviewed source {relative}")
        with checked.open("rb") as stream:
            worktree_raw = stream.read()
        if worktree_raw != raw:
            raise AuthorityVerificationError(f"worktree/indexed source differs: {relative}")
        if b"\r" in raw or raw.startswith(b"\xef\xbb\xbf") or not raw.endswith(b"\n"):
            raise AuthorityVerificationError(f"reviewed source bytes are noncanonical: {relative}")
        records.append(
            {
                "blob_oid": oid,
                "mode": "100644",
                "path": relative,
                "sha256_raw": hashlib.sha256(raw).hexdigest(),
                "size": len(raw),
            }
        )
    return tuple(records)


def _source_bundle_sha256(payload: dict[str, object]) -> str:
    return canonical_sha256(
        {
            "schema": payload["schema"],
            "source_commit_oid": payload["source_commit_oid"],
            "source_tree_oid": payload["source_tree_oid"],
            "source_parent_oid": payload["source_parent_oid"],
            "git_object_format": payload["git_object_format"],
            "path_set_sha256": payload["path_set_sha256"],
            "entries_sha256": payload["entries_sha256"],
        }
    )


def verify_adapter_source_lock(
    authority_commit_oid: object, *, plan_sha256: str
) -> _VerifiedAdapterSourceLock:
    """Verify the future lock from Git; the current pre-lock tree always refuses."""

    if (
        not _is_lower_hex(authority_commit_oid, 40)
        or type(plan_sha256) is not str
        or plan_sha256 != GEOMETRY_PLAN_SHA256
    ):
        raise AuthorityVerificationError("adapter source-lock reference refused")
    authority_tree, authority_parents = _parse_commit(authority_commit_oid)
    _lock_blob_oid, committed_raw = _blob_at(authority_commit_oid, ADAPTER_SOURCE_LOCK_RELATIVE)
    checked_lock = _ordinary_file(ADAPTER_SOURCE_LOCK_PATH, label="adapter source lock")
    with checked_lock.open("rb") as stream:
        disk = stream.read()
    if disk != committed_raw:
        raise AuthorityVerificationError("adapter source lock disk/Git bytes differ")
    payload = _parse_canonical_json(committed_raw, keys=_LOCK_KEYS, label="adapter source lock")
    if payload["schema"] != SOURCE_LOCK_SCHEMA or payload["git_object_format"] != "sha1":
        raise AuthorityVerificationError("adapter source lock identity refused")
    source_oid = payload["source_commit_oid"]
    source_tree, source_parents = _parse_commit(source_oid) if type(source_oid) is str else ("", ())
    if (
        source_tree != payload["source_tree_oid"]
        or len(source_parents) != 1
        or source_parents[0] != payload["source_parent_oid"]
        or authority_parents != (source_oid,)
        or authority_tree == source_tree
    ):
        raise AuthorityVerificationError("adapter source-lock commit chronology refused")
    _require_exact_commit_delta(source_oid, source_parents[0], REVIEWED_SOURCE_PATHS)
    _require_exact_commit_delta(
        authority_commit_oid,
        source_oid,
        (ADAPTER_SOURCE_LOCK_RELATIVE,),
    )
    entries = payload["entries"]
    expected_entries = _entry_records(source_oid)
    if (
        type(entries) is not list
        or any(type(item) is not dict or set(item) != _ENTRY_KEYS for item in entries)
        or not strict_equal(entries, list(expected_entries))
        or payload["path_set_sha256"] != canonical_sha256(REVIEWED_SOURCE_PATHS)
        or payload["entries_sha256"] != canonical_sha256(expected_entries)
        or payload["source_bundle_sha256"] != _source_bundle_sha256(payload)
    ):
        raise AuthorityVerificationError("adapter source-lock closure refused")
    return _VerifiedAdapterSourceLock(
        authority_commit_oid=authority_commit_oid,
        source_commit_oid=source_oid,
        source_tree_oid=source_tree,
        raw_sha256=hashlib.sha256(committed_raw).hexdigest(),
        plan_sha256=plan_sha256,
        seal=_VERIFIED_SEAL,
    )


def phase_request_ids(phase: str) -> tuple[str, ...]:
    """Hash the exact phase, label, point, radius, orientation, and component order."""

    plans = {
        "CAL": calibration_call_plan(),
        "V": confirmation_call_plan(),
        "H": heldout_call_plan(),
    }
    if type(phase) is not str or phase not in plans:
        raise AuthorityVerificationError("phase request plan refused")
    return tuple(
        canonical_sha256(
            {
                "phase": phase,
                "label": label,
                "center": center,
                "radius": radius,
                "orientation": 1,
                "component_order": COMPONENT_ORDER,
            }
        )
        for label, center, radius in plans[phase]
    )


def _validated_phase_record(
    authority_commit_oid: str,
    *,
    phase: str,
    source_lock: _VerifiedAdapterSourceLock,
) -> tuple[dict[str, object], bytes]:
    """Validate the complete source-lock -> CAL -> V -> H Git ancestry."""

    rules = {
        "CAL": (1, "ADAPTER_SOURCE_LOCKED", None),
        "V": (2, "PREDICTIONS_COMMITTED", "CAL"),
        "H": (3, "V_PASS", "V"),
    }
    if phase not in rules:
        raise AuthorityVerificationError("phase lineage identity refused")
    sequence, prior_state, predecessor_phase = rules[phase]
    _tree, parents = _parse_commit(authority_commit_oid)
    if len(parents) != 1:
        raise AuthorityVerificationError("phase lineage is not one-parent")
    _require_exact_commit_delta(
        authority_commit_oid,
        parents[0],
        (PHASE_RECORD_RELATIVE[phase],),
    )
    _blob_oid, raw = _blob_at(authority_commit_oid, PHASE_RECORD_RELATIVE[phase])
    payload = _parse_canonical_json(raw, keys=_PHASE_KEYS, label=f"{phase} phase lineage")
    if (
        payload["schema"] != PHASE_RECORD_SCHEMA
        or payload["phase"] != phase
        or type(payload["sequence"]) is not int
        or payload["sequence"] != sequence
        or payload["decision"] != "ALLOW_EXACT_ONE_SHOT"
        or not _is_lower_hex(payload["session_id"], 64)
        or payload["adapter_source_lock_commit_oid"] != source_lock.authority_commit_oid
        or payload["adapter_source_lock_sha256"] != source_lock.raw_sha256
        or payload["adapter_source_commit_oid"] != source_lock.source_commit_oid
        or payload["adapter_source_tree_oid"] != source_lock.source_tree_oid
        or payload["plan_sha256"] != GEOMETRY_PLAN_SHA256
        or payload["contract_sha256"] != CONTRACT_SHA256
        or payload["prior_authority_commit_oid"] != parents[0]
        or payload["prior_state"] != prior_state
        or not strict_equal(payload["request_ids"], list(phase_request_ids(phase)))
    ):
        raise AuthorityVerificationError("phase lineage payload refused")
    prediction_payload = payload["prediction_record"]
    if phase == "CAL":
        if (
            parents[0] != source_lock.authority_commit_oid
            or payload["prior_record_sha256"] != source_lock.raw_sha256
            or payload["prediction_sha256"] is not None
            or prediction_payload is not None
        ):
            raise AuthorityVerificationError("CAL phase lineage refused")
    else:
        predecessor, predecessor_raw, outcome, outcome_raw = _validated_external_outcome_commit(
            parents[0], phase=predecessor_phase, source_lock=source_lock
        )
        if (
            payload["session_id"] != outcome["session_id"]
            or payload["prior_record_sha256"] != hashlib.sha256(outcome_raw).hexdigest()
            or not _is_lower_hex(payload["prediction_sha256"], 64)
            or type(prediction_payload) is not dict
            or hashlib.sha256(canonical_json_bytes(prediction_payload)).hexdigest()
            != payload["prediction_sha256"]
            or payload["prediction_sha256"] != outcome["prediction_sha256"]
            or not strict_equal(prediction_payload, outcome["prediction_record"])
        ):
            raise AuthorityVerificationError(f"{phase} prediction lineage refused")
        if phase == "H" and (
            payload["prediction_sha256"] != predecessor["prediction_sha256"]
            or not strict_equal(prediction_payload, predecessor["prediction_record"])
        ):
            raise AuthorityVerificationError("H prediction lineage differs from V")
    return payload, raw


def _validated_external_outcome_commit(
    outcome_commit_oid: str,
    *,
    phase: str,
    source_lock: _VerifiedAdapterSourceLock,
) -> tuple[dict[str, object], bytes, dict[str, object], bytes]:
    """Bind phase progress only to a separately committed external outcome."""

    if phase not in PHASE_OUTCOME_RELATIVE:
        raise AuthorityVerificationError("external phase outcome identity refused")
    _tree, parents = _parse_commit(outcome_commit_oid)
    if len(parents) != 1:
        raise AuthorityVerificationError("external phase outcome ancestry refused")
    _require_exact_commit_delta(
        outcome_commit_oid,
        parents[0],
        (PHASE_OUTCOME_RELATIVE[phase], PHASE_RESULT_RELATIVE[phase]),
    )
    phase_payload, phase_raw = _validated_phase_record(parents[0], phase=phase, source_lock=source_lock)
    _blob_oid, outcome_raw = _blob_at(outcome_commit_oid, PHASE_OUTCOME_RELATIVE[phase])
    _result_blob_oid, result_raw = _blob_at(outcome_commit_oid, PHASE_RESULT_RELATIVE[phase])
    outcome = _parse_canonical_json(
        outcome_raw,
        keys=_EXTERNAL_OUTCOME_KEYS,
        label=f"{phase} external outcome",
    )
    expected_prediction = phase_payload["prediction_sha256"]
    expected_prediction_record = phase_payload["prediction_record"]
    if phase == "CAL":
        expected_prediction = outcome["prediction_sha256"]
        expected_prediction_record = outcome["prediction_record"]
    from .fit import validate_canonical_prediction_payload

    if (
        outcome["schema"] != "generator_tensor_response_external_outcome_v1"
        or outcome["phase"] != phase
        or type(outcome["sequence"]) is not int
        or outcome["sequence"] != phase_payload["sequence"]
        or outcome["session_id"] != phase_payload["session_id"]
        or outcome["phase_authority_commit_oid"] != parents[0]
        or outcome["phase_authority_record_sha256"] != hashlib.sha256(phase_raw).hexdigest()
        or outcome["response_result_sha256"] != hashlib.sha256(result_raw).hexdigest()
        or outcome["outcome"] != f"{phase}_PASS"
        or not _is_lower_hex(outcome["prediction_sha256"], 64)
        or type(outcome["prediction_record"]) is not dict
        or hashlib.sha256(canonical_json_bytes(outcome["prediction_record"])).hexdigest()
        != outcome["prediction_sha256"]
        or outcome["prediction_sha256"] != expected_prediction
        or not strict_equal(outcome["prediction_record"], expected_prediction_record)
        or not validate_canonical_prediction_payload(
            outcome["prediction_record"], outcome["prediction_sha256"]
        )
    ):
        raise AuthorityVerificationError("external phase outcome binding refused")
    result = _parse_canonical_json(
        result_raw,
        keys=_PHASE_RESULT_KEYS,
        label=f"{phase} external result",
    )
    if not _validate_phase_result_payload(
        result,
        phase_commit_oid=parents[0],
        phase_payload=phase_payload,
        phase_raw=phase_raw,
        prediction_payload=outcome["prediction_record"],
    ):
        raise AuthorityVerificationError("external phase result binding refused")
    return phase_payload, phase_raw, outcome, outcome_raw


def verify_phase_authorization(
    authority_commit_oid: object,
    *,
    phase: str,
    sequence: int,
    source_lock: _VerifiedAdapterSourceLock,
    plan_sha256: str,
    prior_authority_commit_oid: str,
    prior_record_sha256: str,
    prior_state: str,
    prediction_sha256: str | None,
    prediction_record: dict[str, object] | None,
    request_ids: tuple[str, ...],
    session_id: str | None,
) -> _VerifiedPhaseAuthorization:
    """Consume one immutable, linearly chained phase record from Git."""

    if not source_lock.authentic() or phase not in PHASE_RECORD_RELATIVE:
        raise AuthorityVerificationError("phase source authority refused")
    rebound_source_lock = verify_adapter_source_lock(
        source_lock.authority_commit_oid,
        plan_sha256=plan_sha256,
    )
    if not strict_equal(
        (
            source_lock.authority_commit_oid,
            source_lock.source_commit_oid,
            source_lock.source_tree_oid,
            source_lock.raw_sha256,
            source_lock.plan_sha256,
        ),
        (
            rebound_source_lock.authority_commit_oid,
            rebound_source_lock.source_commit_oid,
            rebound_source_lock.source_tree_oid,
            rebound_source_lock.raw_sha256,
            rebound_source_lock.plan_sha256,
        ),
    ):
        raise AuthorityVerificationError("phase source authority binding refused")
    if not _is_lower_hex(authority_commit_oid, 40):
        raise AuthorityVerificationError("phase authority commit refused")
    payload, raw = _validated_phase_record(
        authority_commit_oid,
        phase=phase,
        source_lock=rebound_source_lock,
    )
    wanted_session = payload["session_id"] if session_id is None else session_id
    expected = {
        "schema": PHASE_RECORD_SCHEMA,
        "phase": phase,
        "sequence": sequence,
        "decision": "ALLOW_EXACT_ONE_SHOT",
        "session_id": wanted_session,
        "adapter_source_lock_commit_oid": source_lock.authority_commit_oid,
        "adapter_source_lock_sha256": source_lock.raw_sha256,
        "adapter_source_commit_oid": source_lock.source_commit_oid,
        "adapter_source_tree_oid": source_lock.source_tree_oid,
        "plan_sha256": plan_sha256,
        "contract_sha256": CONTRACT_SHA256,
        "prior_authority_commit_oid": prior_authority_commit_oid,
        "prior_record_sha256": prior_record_sha256,
        "prior_state": prior_state,
        "prediction_sha256": prediction_sha256,
        "prediction_record": prediction_record,
        "request_ids": list(request_ids),
    }
    if (
        type(payload["sequence"]) is not int
        or not _is_lower_hex(wanted_session, 64)
        or not _is_lower_hex(prior_record_sha256, 64)
        or type(request_ids) is not tuple
        or any(not _is_lower_hex(item, 64) for item in request_ids)
        or canonical_json_bytes(expected) != raw
    ):
        raise AuthorityVerificationError("phase authority payload refused")
    return _VerifiedPhaseAuthorization(
        phase=phase,
        sequence=sequence,
        session_id=wanted_session,
        authority_commit_oid=authority_commit_oid,
        raw_sha256=hashlib.sha256(raw).hexdigest(),
        plan_sha256=plan_sha256,
        adapter_source_lock_commit_oid=source_lock.authority_commit_oid,
        adapter_source_lock_sha256=source_lock.raw_sha256,
        adapter_source_commit_oid=source_lock.source_commit_oid,
        adapter_source_tree_oid=source_lock.source_tree_oid,
        prior_authority_commit_oid=prior_authority_commit_oid,
        prior_record_sha256=prior_record_sha256,
        prior_state=prior_state,
        prediction_sha256=prediction_sha256,
        request_ids=request_ids,
        seal=_VERIFIED_SEAL,
    )


def verify_phase_authority_commit(authority_commit_oid: object) -> _VerifiedPhaseAuthorization:
    """Resolve one exact phase from its immutable Git commit without caller-supplied plan data."""

    if not _is_lower_hex(authority_commit_oid, 40):
        raise AuthorityVerificationError("phase authority commit refused")
    _tree, parents = _parse_commit(authority_commit_oid)
    if len(parents) != 1:
        raise AuthorityVerificationError("phase authority ancestry refused")
    candidates: list[tuple[str, dict[str, object]]] = []
    for phase, relative in PHASE_RECORD_RELATIVE.items():
        try:
            _blob_oid, raw = _blob_at(authority_commit_oid, relative)
            payload = _parse_canonical_json(raw, keys=_PHASE_KEYS, label=f"{phase} phase authority")
        except AuthorityVerificationError:
            continue
        if payload["phase"] == phase and payload["prior_authority_commit_oid"] == parents[0]:
            candidates.append((phase, payload))
    if len(candidates) != 1:
        raise AuthorityVerificationError("phase authority commit is ambiguous")
    phase, payload = candidates[0]
    source_lock = verify_adapter_source_lock(
        payload["adapter_source_lock_commit_oid"],
        plan_sha256=GEOMETRY_PLAN_SHA256,
    )
    prediction_record = payload["prediction_record"]
    if prediction_record is not None and type(prediction_record) is not dict:
        raise AuthorityVerificationError("phase prediction record refused")
    session_id = payload["session_id"]
    if type(session_id) is not str:
        raise AuthorityVerificationError("phase session identity refused")
    return verify_phase_authorization(
        authority_commit_oid,
        phase=phase,
        sequence=payload["sequence"],
        source_lock=source_lock,
        plan_sha256=GEOMETRY_PLAN_SHA256,
        prior_authority_commit_oid=payload["prior_authority_commit_oid"],
        prior_record_sha256=payload["prior_record_sha256"],
        prior_state=payload["prior_state"],
        prediction_sha256=payload["prediction_sha256"],
        prediction_record=prediction_record,
        request_ids=phase_request_ids(phase),
        session_id=session_id,
    )


def reverify_phase_authorization(
    authorization: _VerifiedPhaseAuthorization,
) -> _VerifiedPhaseAuthorization:
    """Rebind an internal phase record to immutable Git objects before access."""

    if type(authorization) is not _VerifiedPhaseAuthorization or not authorization.authentic():
        raise AuthorityVerificationError("phase revalidation record refused")
    source_lock = verify_adapter_source_lock(
        authorization.adapter_source_lock_commit_oid,
        plan_sha256=authorization.plan_sha256,
    )
    payload, raw = _validated_phase_record(
        authorization.authority_commit_oid,
        phase=authorization.phase,
        source_lock=source_lock,
    )
    if hashlib.sha256(raw).hexdigest() != authorization.raw_sha256:
        raise AuthorityVerificationError("phase revalidation raw digest refused")
    expected_requests = phase_request_ids(authorization.phase)
    if (
        authorization.adapter_source_lock_sha256 != source_lock.raw_sha256
        or authorization.adapter_source_commit_oid != source_lock.source_commit_oid
        or authorization.adapter_source_tree_oid != source_lock.source_tree_oid
        or authorization.plan_sha256 != GEOMETRY_PLAN_SHA256
        or not strict_equal(authorization.request_ids, expected_requests)
        or payload["schema"] != PHASE_RECORD_SCHEMA
        or payload["phase"] != authorization.phase
        or type(payload["sequence"]) is not int
        or payload["sequence"] != authorization.sequence
        or payload["decision"] != "ALLOW_EXACT_ONE_SHOT"
        or payload["session_id"] != authorization.session_id
        or payload["adapter_source_lock_commit_oid"] != source_lock.authority_commit_oid
        or payload["adapter_source_lock_sha256"] != source_lock.raw_sha256
        or payload["adapter_source_commit_oid"] != source_lock.source_commit_oid
        or payload["adapter_source_tree_oid"] != source_lock.source_tree_oid
        or payload["plan_sha256"] != GEOMETRY_PLAN_SHA256
        or payload["contract_sha256"] != CONTRACT_SHA256
        or payload["prior_authority_commit_oid"] != authorization.prior_authority_commit_oid
        or payload["prior_record_sha256"] != authorization.prior_record_sha256
        or payload["prior_state"] != authorization.prior_state
        or payload["prediction_sha256"] != authorization.prediction_sha256
        or not strict_equal(payload["request_ids"], list(expected_requests))
    ):
        raise AuthorityVerificationError("phase revalidation payload refused")
    prediction_payload = payload["prediction_record"]
    if authorization.phase == "CAL":
        if authorization.prediction_sha256 is not None or prediction_payload is not None:
            raise AuthorityVerificationError("CAL prediction payload refused")
    elif (
        not _is_lower_hex(authorization.prediction_sha256, 64)
        or type(prediction_payload) is not dict
        or hashlib.sha256(canonical_json_bytes(prediction_payload)).hexdigest()
        != authorization.prediction_sha256
    ):
        raise AuthorityVerificationError("phase prediction payload binding refused")
    if authorization.phase != "CAL":
        from .fit import validate_canonical_prediction_payload

        if not validate_canonical_prediction_payload(prediction_payload, authorization.prediction_sha256):
            raise AuthorityVerificationError("phase prediction semantics refused")
    return authorization


def _ordinary_ledger_directory() -> Path:
    configured = os.environ.get(DURABLE_LEDGER_ROOT_ENV)
    if type(configured) is not str or not configured:
        raise AuthorityVerificationError("outer durable access-ledger binding is required")
    directory = Path(configured)
    if not directory.is_absolute():
        raise AuthorityVerificationError("outer durable access-ledger path refused")
    lexical = directory.absolute()
    current = Path(lexical.anchor)
    for part in lexical.parts[1:]:
        current /= part
        if not current.exists():
            raise AuthorityVerificationError("outer durable access-ledger path is absent")
        info = current.lstat()
        reparse = bool(
            sys.platform == "win32" and info.st_file_attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT
        )
        if current.is_symlink() or reparse:
            raise AuthorityVerificationError("outer durable access-ledger path contains a link")
    resolved = lexical.resolve(strict=True)
    repo = REPO_ROOT.resolve(strict=True)
    if resolved == repo or repo in resolved.parents or resolved in repo.parents:
        raise AuthorityVerificationError("durable access-ledger must be outside detached worktree")
    info = resolved.lstat()
    reparse = bool(sys.platform == "win32" and info.st_file_attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT)
    if not resolved.is_dir() or resolved.is_symlink() or reparse:
        raise AuthorityVerificationError("access-ledger directory refused")
    getuid = getattr(os, "getuid", None)
    if callable(getuid) and info.st_uid != getuid():
        raise AuthorityVerificationError("access-ledger ownership refused")
    return resolved


def _ledger_record_name(
    authorization: _VerifiedPhaseAuthorization,
    suffix: str,
) -> str:
    if suffix not in {"started", "outcome"}:
        raise AuthorityVerificationError("access-ledger record suffix refused")
    return (
        f"{authorization.sequence}.{authorization.phase}.{authorization.session_id}."
        f"{authorization.authority_commit_oid}.{suffix}.json"
    )


def _create_immutable_ledger_record(name: str, payload: dict[str, object]) -> None:
    if (
        type(name) is not str
        or not name
        or any(
            character not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-"
            for character in name
        )
    ):
        raise AuthorityVerificationError("access-ledger name refused")
    directory = _ordinary_ledger_directory()
    destination = directory / name
    raw = canonical_json_bytes(payload)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_BINARY"):
        flags |= os.O_BINARY
    try:
        descriptor = os.open(destination, flags, 0o600)
    except FileExistsError as exc:
        raise AuthorityVerificationError("phase authorization is already consumed") from exc
    try:
        with os.fdopen(descriptor, "wb", closefd=True) as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException:
        raise AuthorityVerificationError("access-ledger transaction failed") from None


def _publish_phase_result(
    authorization: _VerifiedPhaseAuthorization,
    payload: dict[str, object],
) -> str:
    """Publish one complete phase result atomically; a partial result is never authoritative."""

    authorization = reverify_phase_authorization(authorization)
    if type(payload) is not dict or payload.get("phase") != authorization.phase:
        raise AuthorityVerificationError("phase result payload refused")
    destination = REPO_ROOT.joinpath(*PurePosixPath(PHASE_RESULT_RELATIVE[authorization.phase]).parts)
    parent = destination.parent
    if parent.resolve(strict=True) != REPO_ROOT.joinpath("cwt-sim", "experiments").resolve(strict=True):
        raise AuthorityVerificationError("phase result parent refused")
    raw = canonical_json_bytes(payload)
    temporary = parent / f".{destination.name}.{authorization.session_id}.tmp"
    if temporary.exists() or destination.exists():
        raise AuthorityVerificationError("phase result already exists")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_BINARY"):
        flags |= os.O_BINARY
    descriptor: int | None = None
    try:
        descriptor = os.open(temporary, flags, 0o600)
        with os.fdopen(descriptor, "wb", closefd=True) as stream:
            descriptor = None
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, destination)
        temporary.unlink()
    except BaseException:
        if descriptor is not None:
            os.close(descriptor)
        try:
            if temporary.is_file() and not temporary.is_symlink():
                temporary.unlink()
        except OSError:
            pass
        raise AuthorityVerificationError("phase result transaction failed") from None
    return hashlib.sha256(raw).hexdigest()


def _start_payload(authorization: _VerifiedPhaseAuthorization) -> dict[str, object]:
    return {
        "schema": "generator_tensor_response_access_incident_v1",
        "state": "STARTED_TERMINAL_ON_INTERRUPTION",
        "phase": authorization.phase,
        "sequence": authorization.sequence,
        "session_id": authorization.session_id,
        "authority_commit_oid": authorization.authority_commit_oid,
        "authority_record_sha256": authorization.raw_sha256,
        "request_ids": authorization.request_ids,
    }


def _outcome_payload(
    authorization: _VerifiedPhaseAuthorization,
    outcome: str,
) -> dict[str, object]:
    return {
        "schema": "generator_tensor_response_access_outcome_v1",
        "phase": authorization.phase,
        "sequence": authorization.sequence,
        "session_id": authorization.session_id,
        "authority_record_sha256": authorization.raw_sha256,
        "outcome": outcome,
    }


def _read_exact_ledger_record(
    name: str,
    *,
    keys: set[str],
    expected: dict[str, object],
) -> None:
    checked = _ordinary_file(_ordinary_ledger_directory() / name, label="access-ledger record")
    with checked.open("rb") as stream:
        raw = stream.read()
    payload = _parse_canonical_json(raw, keys=keys, label="access-ledger record")
    if not strict_equal(payload, json.loads(canonical_json_bytes(expected))):
        raise AuthorityVerificationError("access-ledger record binding refused")


def _verify_local_phase_outcome_audit(
    phase_payload: dict[str, object],
    phase_raw: bytes,
    *,
    phase_commit_oid: str,
    expected_outcome: str,
) -> None:
    """Check local incident evidence; this function never grants phase authority."""

    phase = phase_payload["phase"]
    session_id = phase_payload["session_id"]
    sequence = phase_payload["sequence"]
    _read_exact_ledger_record(
        f"{sequence}.{phase}.{session_id}.{phase_commit_oid}.outcome.json",
        keys=_OUTCOME_KEYS,
        expected={
            "schema": "generator_tensor_response_access_outcome_v1",
            "phase": phase,
            "sequence": sequence,
            "session_id": session_id,
            "authority_record_sha256": hashlib.sha256(phase_raw).hexdigest(),
            "outcome": expected_outcome,
        },
    )


def consume_phase_authorization(authorization: _VerifiedPhaseAuthorization) -> None:
    """Persist a single-use marker before the first response-producing call."""

    authorization = reverify_phase_authorization(authorization)
    _create_immutable_ledger_record(
        _ledger_record_name(authorization, "started"),
        _start_payload(authorization),
    )


def record_phase_outcome(authorization: _VerifiedPhaseAuthorization, outcome: str) -> None:
    authorization = reverify_phase_authorization(authorization)
    if outcome not in {
        "CAL_BATCH_COMPLETE",
        "CAL_PASS",
        "CAL_FAIL",
        "CAL_INDETERMINATE",
        "V_BATCH_COMPLETE",
        "V_PASS",
        "V_FAIL",
        "V_INDETERMINATE",
        "H_BATCH_COMPLETE",
        "H_PASS",
        "H_FAIL",
        "H_INDETERMINATE",
        "TERMINAL_INCIDENT",
    }:
        raise AuthorityVerificationError("phase outcome refused")
    _read_exact_ledger_record(
        _ledger_record_name(authorization, "started"),
        keys=_START_KEYS,
        expected=_start_payload(authorization),
    )
    _create_immutable_ledger_record(
        _ledger_record_name(authorization, "outcome"),
        _outcome_payload(authorization, outcome),
    )


__all__ = [
    "ADAPTER_SOURCE_LOCK_PATH",
    "ADAPTER_SOURCE_LOCK_RELATIVE",
    "AuthorityVerificationError",
    "PHASE_RECORD_RELATIVE",
    "REVIEWED_SOURCE_PATHS",
    "phase_request_ids",
    "reverify_phase_authorization",
    "verify_adapter_source_lock",
    "verify_phase_authorization",
]
