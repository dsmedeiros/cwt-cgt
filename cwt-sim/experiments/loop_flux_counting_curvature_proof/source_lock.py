"""Git-index authority for the semantic proof-source closure.

The lock is generated from index entries and Git object blobs, never from a
worktree-only inventory.  Runtime validation additionally requires every
semantic worktree file to equal its indexed blob byte for byte.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Mapping, Sequence

if __package__ in {None, ""}:
    transaction_path = Path(__file__).resolve().with_name("transaction.py")
    transaction_spec = importlib.util.spec_from_file_location(
        "_loop_flux_source_lock_transaction",
        transaction_path,
    )
    if transaction_spec is None or transaction_spec.loader is None:
        raise RuntimeError("source-lock transaction dependency is unavailable")
    transaction_module = importlib.util.module_from_spec(transaction_spec)
    sys.modules[transaction_spec.name] = transaction_module
    transaction_spec.loader.exec_module(transaction_module)
    ArtifactVerificationError = transaction_module.ArtifactVerificationError
    _assert_no_reparse_from_volume_root = transaction_module._assert_no_reparse_from_volume_root
    canonical_source_text_bytes = transaction_module.canonical_source_text_bytes
else:
    from .transaction import (
        ArtifactVerificationError,
        _assert_no_reparse_from_volume_root,
        canonical_source_text_bytes,
    )

EXPERIMENT_DIR = Path(__file__).resolve().parent
SIM_ROOT = EXPERIMENT_DIR.parents[1]
REPO_ROOT = SIM_ROOT.parent

SOURCE_LOCK_SCHEMA = "git_index_source_lock_v1"
SOURCE_LOCK_HASH_DOMAIN = "sha256_raw_bytes_v1"
SOURCE_BLOB_HASH_DOMAIN = "sha256_raw_git_index_blob_v1"
SOURCE_LOCK_RELATIVE_PATH = "cwt-sim/experiments/loop_flux_counting_curvature_proof/SOURCE_LOCK.json"
SOURCE_LOCK_PATH = REPO_ROOT / SOURCE_LOCK_RELATIVE_PATH
SOURCE_LOCK_ENV = "CWT_CGT_SOURCE_LOCK_FILE"
GIT_EXECUTABLE_ENV = "CWT_CGT_GIT_EXECUTABLE"

REVIEWED_PARENT_COMMIT_OID = "7b0412ea06ff0b61bf6efa1fc1aae57a913ceac1"
REVIEWED_GIT_OBJECT_FORMAT = "sha1"
REVIEWED_SEMANTIC_SOURCE_PATHS = (
    "experiments/__init__.py",
    "experiments/loop_flux_counting_curvature_proof/MODEL_CONTRACT.md",
    "experiments/loop_flux_counting_curvature_proof/__init__.py",
    "experiments/loop_flux_counting_curvature_proof/artifacts.py",
    "experiments/loop_flux_counting_curvature_proof/contract.py",
    "experiments/loop_flux_counting_curvature_proof/counting_lane.py",
    "experiments/loop_flux_counting_curvature_proof/exact.py",
    "experiments/loop_flux_counting_curvature_proof/firewall.py",
    "experiments/loop_flux_counting_curvature_proof/generator.py",
    "experiments/loop_flux_counting_curvature_proof/geometry_lane.py",
    "experiments/loop_flux_counting_curvature_proof/oracle_lane.py",
    "experiments/loop_flux_counting_curvature_proof/pipeline.py",
    "experiments/loop_flux_counting_curvature_proof/run.py",
    "experiments/loop_flux_counting_curvature_proof/source_lock.py",
    "experiments/loop_flux_counting_curvature_proof/theorem.py",
    "experiments/loop_flux_counting_curvature_proof/transaction.py",
    "experiments/response_theorem_proof_program/THEOREM.md",
    "tests/experiments/test_loop_flux_counting_curvature_proof.py",
)
REVIEWED_GIT_INDEX_SOURCE_PATHS = tuple(f"cwt-sim/{path}" for path in REVIEWED_SEMANTIC_SOURCE_PATHS)
REVIEWED_PARENT_TRACKED_DEPENDENCY_PATHS = (
    "cwt-sim/experiments/__init__.py",
    "cwt-sim/experiments/response_theorem_proof_program/THEOREM.md",
)
REVIEWED_GIT_INDEX_ADDED_PATHS = tuple(
    path for path in REVIEWED_GIT_INDEX_SOURCE_PATHS if path not in REVIEWED_PARENT_TRACKED_DEPENDENCY_PATHS
)
# Recomputed from the exact ordered path tuple whenever that reviewed inventory changes.
REVIEWED_GIT_INDEX_PATH_SET_SHA256 = "03e571326d2d777a00828e917a9f275b047d9b2776e57f9d1f70dd4c2bbc587f"
REVIEWED_GIT_INDEX_ADDED_PATH_SET_SHA256 = "ddc64a892a63938efccc2f1689357e32e17073491cb83c0c9463db7537cc8cc1"
REVIEWED_FINAL_PUBLICATION_PATHS = tuple(
    sorted(
        REVIEWED_GIT_INDEX_ADDED_PATHS
        + (
            SOURCE_LOCK_RELATIVE_PATH,
            "cwt-sim/experiments/loop_flux_counting_curvature_proof/artifacts/CHECKSUMS.json",
            "cwt-sim/experiments/loop_flux_counting_curvature_proof/artifacts/PROVENANCE.json",
            "cwt-sim/experiments/loop_flux_counting_curvature_proof/artifacts/REPORT.md",
            "cwt-sim/experiments/loop_flux_counting_curvature_proof/artifacts/records.json",
            "cwt-sim/experiments/loop_flux_counting_curvature_proof/artifacts/summary.json",
        )
    )
)
REVIEWED_FINAL_PUBLICATION_PATH_SET_SHA256 = (
    "81f3acd44aa6bf2d79d584f334b983242755bb6a83c5d297866bdd385d93ddfa"
)


@dataclass(frozen=True)
class GitIndexBinding:
    """Explicit worktree, Git directory, and index used as source authority."""

    git_dir: Path
    index_file: Path
    work_tree: Path
    explicit: bool


@dataclass(frozen=True)
class VerifiedSourceLock:
    """Validated lock plus its independently recomputed index identities."""

    record: dict[str, object]
    raw_sha256: str
    bundle_sha256: str
    source_hashes: dict[str, dict[str, object]]


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _canonical_json_bytes(payload: object) -> bytes:
    try:
        return (
            json.dumps(
                payload,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=True,
                allow_nan=False,
            )
            + "\n"
        ).encode("utf-8")
    except (TypeError, ValueError, OverflowError) as exc:
        raise ArtifactVerificationError("source lock is not canonical JSON") from exc


def _canonical_repo_path(value: object) -> str:
    if type(value) is not str:
        raise ArtifactVerificationError("source lock path has the wrong type")
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
        raise ArtifactVerificationError(f"source lock path is noncanonical: {value!r}")
    return value


def _is_hex_oid(value: object, object_format: str) -> bool:
    length = {"sha1": 40, "sha256": 64}.get(object_format)
    return (
        type(value) is str
        and length is not None
        and len(value) == length
        and all(character in "0123456789abcdef" for character in value)
    )


def _is_sha256(value: object) -> bool:
    return (
        type(value) is str
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _sanitized_git_environment(binding: GitIndexBinding | None = None) -> dict[str, str]:
    environment = {key: value for key, value in os.environ.items() if not key.upper().startswith("GIT_")}
    environment["GIT_OPTIONAL_LOCKS"] = "0"
    if binding is not None:
        environment.update(
            {
                "GIT_DIR": str(binding.git_dir),
                "GIT_INDEX_FILE": str(binding.index_file),
                "GIT_WORK_TREE": str(binding.work_tree),
            }
        )
    return environment


def _run_git(
    arguments: Sequence[str],
    *,
    binding: GitIndexBinding | None = None,
    cwd: Path | None = None,
) -> bytes:
    safe_worktree = binding.work_tree if binding is not None else REPO_ROOT
    configured_git = os.environ.get(GIT_EXECUTABLE_ENV)
    if configured_git is not None:
        git_executable = Path(configured_git)
        if not git_executable.is_absolute() or not git_executable.is_file():
            raise ArtifactVerificationError("trusted Git executable is not an absolute ordinary file")
        git_executable = git_executable.resolve(strict=True)
    else:
        discovered_git = shutil.which("git")
        if not discovered_git:
            raise ArtifactVerificationError("trusted Git executable is unavailable")
        git_executable = Path(discovered_git).resolve(strict=True)
    try:
        completed = subprocess.run(
            [
                str(git_executable),
                "--no-replace-objects",
                "-c",
                f"safe.directory={safe_worktree}",
                *arguments,
            ],
            cwd=cwd or (binding.work_tree if binding is not None else REPO_ROOT),
            env=_sanitized_git_environment(binding),
            check=True,
            capture_output=True,
            timeout=30,
        )
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise ArtifactVerificationError("Git-index source authority is unavailable") from exc
    return completed.stdout


def _absolute_existing_path(path: Path, *, kind: str, label: str) -> Path:
    if not path.is_absolute():
        raise ArtifactVerificationError(f"{label} is not an absolute path")
    checked = _assert_no_reparse_from_volume_root(path, label=label, require_leaf=True)
    if kind == "directory" and not checked.is_dir():
        raise ArtifactVerificationError(f"{label} is not an ordinary directory")
    if kind == "file" and not checked.is_file():
        raise ArtifactVerificationError(f"{label} is not an ordinary file")
    return checked


def _validated_binding(binding: GitIndexBinding) -> GitIndexBinding:
    if type(binding) is not GitIndexBinding or type(binding.explicit) is not bool:
        raise ArtifactVerificationError("Git-index binding schema differs")
    if not all(isinstance(path, Path) for path in (binding.git_dir, binding.index_file, binding.work_tree)):
        raise ArtifactVerificationError("Git-index binding paths have the wrong type")
    return GitIndexBinding(
        _absolute_existing_path(binding.git_dir, kind="directory", label="Git directory"),
        _absolute_existing_path(binding.index_file, kind="file", label="Git index"),
        _absolute_existing_path(binding.work_tree, kind="directory", label="Git worktree"),
        binding.explicit,
    )


def _path_from_git_output(raw: bytes, *, label: str) -> Path:
    try:
        value = raw.decode("utf-8").strip()
    except UnicodeError as exc:
        raise ArtifactVerificationError(f"{label} is not UTF-8") from exc
    if not value:
        raise ArtifactVerificationError(f"{label} is empty")
    path = Path(value)
    if not path.is_absolute():
        path = (REPO_ROOT / path).absolute()
    return path


def resolve_git_index_binding() -> GitIndexBinding:
    """Resolve an all-explicit binding or the exact repository index.

    Partial ambient Git metadata and parent-directory discovery are refused.
    An external checkout therefore has no worktree-only fallback.
    """

    names = ("GIT_DIR", "GIT_INDEX_FILE", "GIT_WORK_TREE")
    values = tuple(os.environ.get(name) for name in names)
    if any(value is not None for value in values):
        if not all(type(value) is str and value for value in values):
            raise ArtifactVerificationError("explicit Git-index binding is incomplete")
        git_dir = _absolute_existing_path(Path(values[0]), kind="directory", label="explicit Git directory")
        index_file = _absolute_existing_path(Path(values[1]), kind="file", label="explicit Git index")
        work_tree = _absolute_existing_path(Path(values[2]), kind="directory", label="explicit Git worktree")
        return GitIndexBinding(git_dir, index_file, work_tree, True)

    expected_root = _absolute_existing_path(REPO_ROOT, kind="directory", label="repository root")
    top = _absolute_existing_path(
        _path_from_git_output(
            _run_git(["-C", str(REPO_ROOT), "rev-parse", "--show-toplevel"]),
            label="Git worktree",
        ),
        kind="directory",
        label="Git worktree",
    )
    if top != expected_root:
        raise ArtifactVerificationError("repository Git worktree differs from the package root")
    git_dir = _absolute_existing_path(
        _path_from_git_output(
            _run_git(["-C", str(REPO_ROOT), "rev-parse", "--absolute-git-dir"]),
            label="Git directory",
        ),
        kind="directory",
        label="Git directory",
    )
    index_file = _absolute_existing_path(
        _path_from_git_output(
            _run_git(["-C", str(REPO_ROOT), "rev-parse", "--git-path", "index"]),
            label="Git index",
        ),
        kind="file",
        label="Git index",
    )
    return GitIndexBinding(git_dir, index_file, top, False)


def _discover_index_entries(binding: GitIndexBinding) -> list[dict[str, object]]:
    output = _run_git(
        ["ls-files", "--stage", "-z", "--", *REVIEWED_GIT_INDEX_SOURCE_PATHS],
        binding=binding,
    )
    parsed: dict[str, tuple[str, str]] = {}
    for raw_record in output.split(b"\0"):
        if not raw_record:
            continue
        try:
            metadata, raw_path = raw_record.split(b"\t", 1)
            mode_raw, oid_raw, stage_raw = metadata.split(b" ", 2)
            path = raw_path.decode("utf-8")
            mode = mode_raw.decode("ascii")
            oid = oid_raw.decode("ascii")
            stage = stage_raw.decode("ascii")
        except (ValueError, UnicodeError) as exc:
            raise ArtifactVerificationError("Git index entry is malformed") from exc
        path = _canonical_repo_path(path)
        if path in parsed:
            raise ArtifactVerificationError(f"duplicate Git index entry: {path}")
        if stage != "0":
            raise ArtifactVerificationError(f"unmerged Git index entry: {path}")
        parsed[path] = (mode, oid)

    if tuple(parsed) != REVIEWED_GIT_INDEX_SOURCE_PATHS:
        raise ArtifactVerificationError("Git index semantic source path set/order differs")

    object_format = _git_object_format(binding)
    entries: list[dict[str, object]] = []
    for path in REVIEWED_GIT_INDEX_SOURCE_PATHS:
        mode, oid = parsed[path]
        if mode != "100644":
            raise ArtifactVerificationError(f"Git index mode is not 100644: {path}")
        if not _is_hex_oid(oid, object_format):
            raise ArtifactVerificationError(f"Git index blob OID is malformed: {path}")
        if _run_git(["cat-file", "-t", oid], binding=binding).strip() != b"blob":
            raise ArtifactVerificationError(f"Git index object is not a blob: {path}")
        raw = _run_git(["cat-file", "blob", oid], binding=binding)
        try:
            canonical = canonical_source_text_bytes(raw)
        except ValueError as exc:
            raise ArtifactVerificationError(f"Git index source is not strict UTF-8/LF: {path}") from exc
        if raw != canonical:
            raise ArtifactVerificationError(f"Git index source is not strict UTF-8/LF: {path}")
        worktree_path = binding.work_tree.joinpath(*PurePosixPath(path).parts)
        worktree_path = _assert_no_reparse_from_volume_root(
            worktree_path,
            label=f"semantic worktree source {path}",
            require_leaf=True,
        )
        if not worktree_path.is_file():
            raise ArtifactVerificationError(f"semantic worktree source is not an ordinary file: {path}")
        if worktree_path.read_bytes() != raw:
            raise ArtifactVerificationError(f"semantic worktree source differs from Git index: {path}")
        entries.append(
            {
                "path": path,
                "mode": mode,
                "blob_oid": oid,
                "size": len(raw),
                "sha256_raw": _sha256(raw),
            }
        )
    return entries


def _selected_index_delta(binding: GitIndexBinding) -> list[tuple[str, str]]:
    output = _run_git(
        [
            "diff-index",
            "--cached",
            "--name-status",
            "-z",
            "--no-renames",
            REVIEWED_PARENT_COMMIT_OID,
            "--",
        ],
        binding=binding,
    )
    tokens = output.split(b"\0")
    if not tokens or tokens[-1] != b"" or len(tokens[:-1]) % 2:
        raise ArtifactVerificationError("selected Git index delta is malformed")
    observed: list[tuple[str, str]] = []
    seen: set[str] = set()
    for offset in range(0, len(tokens) - 1, 2):
        try:
            status = tokens[offset].decode("ascii")
            path = _canonical_repo_path(tokens[offset + 1].decode("utf-8"))
        except UnicodeError as exc:
            raise ArtifactVerificationError("selected Git index delta is not canonical text") from exc
        if path in seen:
            raise ArtifactVerificationError(f"duplicate selected Git index delta path: {path}")
        seen.add(path)
        observed.append((status, path))
    return observed


def _verify_exact_index_delta(
    binding: GitIndexBinding,
    expected_paths: Sequence[str],
    expected_path_set_sha256: str,
    *,
    label: str,
) -> None:
    """Require the entire selected index delta to be one reviewed A-path set."""

    observed = _selected_index_delta(binding)
    expected = [("A", path) for path in expected_paths]
    if observed != expected:
        raise ArtifactVerificationError(f"selected Git index has an unreviewed {label} delta")
    if _path_set_sha256(expected_paths) != expected_path_set_sha256:
        raise ArtifactVerificationError(f"reviewed Git-index {label} path fingerprint differs")


def _verify_source_generation_index_delta(binding: GitIndexBinding) -> None:
    _verify_exact_index_delta(
        binding,
        REVIEWED_GIT_INDEX_ADDED_PATHS,
        REVIEWED_GIT_INDEX_ADDED_PATH_SET_SHA256,
        label="source-generation",
    )


def verify_final_publication_index_delta(
    binding: GitIndexBinding | None = None,
) -> dict[str, object]:
    """Verify the precommit 22-path publication delta; never a runtime PASS gate."""

    selected = _validated_binding(binding or resolve_git_index_binding())
    _verify_parent_object(selected, REVIEWED_PARENT_COMMIT_OID)
    _verify_exact_index_delta(
        selected,
        REVIEWED_FINAL_PUBLICATION_PATHS,
        REVIEWED_FINAL_PUBLICATION_PATH_SET_SHA256,
        label="final-publication",
    )
    return {
        "parent_commit_oid": REVIEWED_PARENT_COMMIT_OID,
        "path_count": len(REVIEWED_FINAL_PUBLICATION_PATHS),
        "path_set_sha256": REVIEWED_FINAL_PUBLICATION_PATH_SET_SHA256,
    }


def _git_object_format(binding: GitIndexBinding) -> str:
    try:
        value = _run_git(["rev-parse", "--show-object-format"], binding=binding).decode("ascii").strip()
    except UnicodeError as exc:
        raise ArtifactVerificationError("Git object format is malformed") from exc
    if value != REVIEWED_GIT_OBJECT_FORMAT:
        raise ArtifactVerificationError("Git object format differs from reviewed authority")
    return value


def _verify_parent_object(binding: GitIndexBinding, parent_oid: str) -> None:
    if not _is_hex_oid(parent_oid, REVIEWED_GIT_OBJECT_FORMAT):
        raise ArtifactVerificationError("source lock parent commit OID is malformed")
    if _run_git(["cat-file", "-t", parent_oid], binding=binding).strip() != b"commit":
        raise ArtifactVerificationError("source lock parent authority is not a Git commit")


def _path_set_sha256(paths: Sequence[str]) -> str:
    return _sha256(_canonical_json_bytes(list(paths)))


def _entries_sha256(entries: Sequence[Mapping[str, object]]) -> str:
    return _sha256(_canonical_json_bytes(list(entries)))


def _bundle_sha256(record: Mapping[str, object]) -> str:
    payload = {
        "schema": record["schema"],
        "parent_commit_oid": record["parent_commit_oid"],
        "git_object_format": record["git_object_format"],
        "path_set_sha256": record["path_set_sha256"],
        "entries_sha256": record["entries_sha256"],
    }
    return _sha256(_canonical_json_bytes(payload))


def build_source_lock_record(binding: GitIndexBinding, *, require_parent_head: bool) -> dict[str, object]:
    """Build the strict lock solely from the selected index and object database."""

    binding = _validated_binding(binding)
    object_format = _git_object_format(binding)
    _verify_parent_object(binding, REVIEWED_PARENT_COMMIT_OID)
    if require_parent_head:
        head = _run_git(["rev-parse", "HEAD"], binding=binding).decode("ascii").strip()
        if head != REVIEWED_PARENT_COMMIT_OID:
            raise ArtifactVerificationError("source lock generation parent differs")
    if _path_set_sha256(REVIEWED_GIT_INDEX_SOURCE_PATHS) != REVIEWED_GIT_INDEX_PATH_SET_SHA256:
        raise ArtifactVerificationError("reviewed Git-index path-set fingerprint differs")
    if require_parent_head:
        _verify_source_generation_index_delta(binding)
    entries = _discover_index_entries(binding)
    return {
        "schema": SOURCE_LOCK_SCHEMA,
        "parent_commit_oid": REVIEWED_PARENT_COMMIT_OID,
        "git_object_format": object_format,
        "entries": entries,
        "path_set_sha256": _path_set_sha256(REVIEWED_GIT_INDEX_SOURCE_PATHS),
        "entries_sha256": _entries_sha256(entries),
    }


def build_source_lock_bytes(binding: GitIndexBinding | None = None) -> bytes:
    """Build canonical lock bytes for an explicitly staged source index."""

    selected = _validated_binding(binding or resolve_git_index_binding())
    return _canonical_json_bytes(build_source_lock_record(selected, require_parent_head=True))


def _exact_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if type(key) is not str or key in result:
            raise ArtifactVerificationError("source lock contains duplicate or invalid keys")
        result[key] = value
    return result


def parse_source_lock(raw: bytes) -> dict[str, object]:
    """Parse and strictly type-check one canonical source lock."""

    if raw.startswith(b"\xef\xbb\xbf") or b"\r" in raw:
        raise ArtifactVerificationError("source lock is not strict UTF-8/LF")
    try:
        payload = json.loads(raw.decode("utf-8"), object_pairs_hook=_exact_object)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ArtifactVerificationError("source lock is unreadable") from exc
    if type(payload) is not dict or raw != _canonical_json_bytes(payload):
        raise ArtifactVerificationError("source lock bytes are noncanonical")
    if tuple(payload) != (
        "entries",
        "entries_sha256",
        "git_object_format",
        "parent_commit_oid",
        "path_set_sha256",
        "schema",
    ):
        raise ArtifactVerificationError("source lock top-level schema differs")
    if type(payload["schema"]) is not str or payload["schema"] != SOURCE_LOCK_SCHEMA:
        raise ArtifactVerificationError("source lock schema authority differs")
    if (
        type(payload["git_object_format"]) is not str
        or payload["git_object_format"] != REVIEWED_GIT_OBJECT_FORMAT
        or not _is_hex_oid(payload["parent_commit_oid"], REVIEWED_GIT_OBJECT_FORMAT)
        or type(payload["path_set_sha256"]) is not str
        or not _is_sha256(payload["path_set_sha256"])
        or type(payload["entries_sha256"]) is not str
        or not _is_sha256(payload["entries_sha256"])
    ):
        raise ArtifactVerificationError("source lock identity fields differ")
    entries = payload["entries"]
    if type(entries) is not list:
        raise ArtifactVerificationError("source lock entries are not an exact list")
    paths: list[str] = []
    for entry in entries:
        if type(entry) is not dict or tuple(entry) != (
            "blob_oid",
            "mode",
            "path",
            "sha256_raw",
            "size",
        ):
            raise ArtifactVerificationError("source lock entry schema differs")
        path = _canonical_repo_path(entry["path"])
        if path in paths:
            raise ArtifactVerificationError(f"duplicate source lock path: {path}")
        paths.append(path)
        if (
            type(entry["mode"]) is not str
            or entry["mode"] != "100644"
            or not _is_hex_oid(entry["blob_oid"], REVIEWED_GIT_OBJECT_FORMAT)
            or type(entry["size"]) is not int
            or type(entry["size"]) is bool
            or entry["size"] < 0
            or not _is_sha256(entry["sha256_raw"])
        ):
            raise ArtifactVerificationError(f"source lock entry identity differs: {path}")
    if tuple(paths) != REVIEWED_GIT_INDEX_SOURCE_PATHS:
        raise ArtifactVerificationError("source lock path set/order differs")
    if payload["path_set_sha256"] != _path_set_sha256(paths):
        raise ArtifactVerificationError("source lock path-set digest differs")
    if payload["entries_sha256"] != _entries_sha256(entries):
        raise ArtifactVerificationError("source lock entries digest differs")
    return payload


def _source_lock_file(binding: GitIndexBinding) -> Path:
    override = os.environ.get(SOURCE_LOCK_ENV)
    if override is None:
        path = binding.work_tree.joinpath(*PurePosixPath(SOURCE_LOCK_RELATIVE_PATH).parts)
    else:
        if not binding.explicit or type(override) is not str or not override:
            raise ArtifactVerificationError("source lock override requires explicit Git-index binding")
        path = Path(override)
        if not path.is_absolute():
            raise ArtifactVerificationError("source lock override is not absolute")
    checked = _assert_no_reparse_from_volume_root(
        path,
        label="source lock",
        require_leaf=True,
    )
    if not checked.is_file():
        raise ArtifactVerificationError("source lock is missing or nonordinary")
    return checked


def verify_source_lock(binding: GitIndexBinding | None = None) -> VerifiedSourceLock:
    """Verify the lock, selected index blobs, and exact worktree/index equality."""

    if binding is None and os.environ.get(SOURCE_LOCK_ENV) is not None:
        explicit_names = ("GIT_DIR", "GIT_INDEX_FILE", "GIT_WORK_TREE")
        explicit_values = tuple(os.environ.get(name) for name in explicit_names)
        if not all(
            type(value) is str and value  # noqa: E721 - exact type is contractual
            for value in explicit_values
        ):
            raise ArtifactVerificationError("source lock override requires explicit Git-index binding")
    selected = binding or resolve_git_index_binding()
    raw = _source_lock_file(selected).read_bytes()
    observed = parse_source_lock(raw)
    expected = build_source_lock_record(selected, require_parent_head=False)
    if observed != expected:
        raise ArtifactVerificationError("source lock differs from selected Git index authority")
    _verify_parent_object(selected, observed["parent_commit_oid"])
    hashes = {
        entry["path"]: {
            "type": "file",
            "hash_domain": SOURCE_BLOB_HASH_DOMAIN,
            "mode": entry["mode"],
            "blob_oid": entry["blob_oid"],
            "size": entry["size"],
            "sha256": entry["sha256_raw"],
        }
        for entry in observed["entries"]
    }
    return VerifiedSourceLock(
        record=observed,
        raw_sha256=_sha256(raw),
        bundle_sha256=_bundle_sha256(observed),
        source_hashes=hashes,
    )


def _verify_json_main(arguments: Sequence[str]) -> int:
    if tuple(arguments) != ("verify-json",):
        raise ArtifactVerificationError("source-lock entrypoint command differs")
    authority = verify_source_lock()
    sys.stdout.buffer.write(
        _canonical_json_bytes(
            {
                "bundle_sha256": authority.bundle_sha256,
                "raw_sha256": authority.raw_sha256,
                "record": authority.record,
                "source_hashes": authority.source_hashes,
            }
        )
    )
    return 0


__all__ = [
    "GIT_EXECUTABLE_ENV",
    "GitIndexBinding",
    "REVIEWED_GIT_INDEX_SOURCE_PATHS",
    "REVIEWED_SEMANTIC_SOURCE_PATHS",
    "SOURCE_LOCK_PATH",
    "SOURCE_LOCK_RELATIVE_PATH",
    "VerifiedSourceLock",
    "build_source_lock_bytes",
    "build_source_lock_record",
    "parse_source_lock",
    "resolve_git_index_binding",
    "verify_final_publication_index_delta",
    "verify_source_lock",
]


if __name__ == "__main__":
    try:
        raise SystemExit(_verify_json_main(sys.argv[1:]))
    except ArtifactVerificationError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1) from exc
