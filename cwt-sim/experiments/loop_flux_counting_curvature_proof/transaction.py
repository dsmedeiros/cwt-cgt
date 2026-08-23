"""Local crash-safe transactional publisher for the five-file proof bundle."""

from __future__ import annotations

import hashlib
import json
import os
import stat
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Iterator, Mapping

EXPERIMENT_DIR = Path(__file__).resolve().parent
SIM_ROOT = EXPERIMENT_DIR.parents[1]
ARTIFACTS_DIR = EXPERIMENT_DIR / "artifacts"
EXPECTED_ARTIFACT_NAMES = {"CHECKSUMS.json", "PROVENANCE.json", "REPORT.md", "records.json", "summary.json"}
SOURCE_HASH_DOMAIN = "sha256_utf8_lf_v1"
RAW_HASH_DOMAIN = "sha256_raw_bytes_v1"
REVIEWED_MATERIAL_SOURCE_PATHS = (
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
PROTECTED_SOURCE_LOCK_RELATIVE_PATH = "experiments/loop_flux_counting_curvature_proof/SOURCE_LOCK.json"
PREDECESSOR_ARTIFACT_DIRS = {
    "shared_generator_counting_curvature_proof": SIM_ROOT
    / "experiments"
    / "shared_generator_counting_curvature_proof"
    / "artifacts",
    "constitutive_map_3d_proof": SIM_ROOT / "experiments" / "constitutive_map_3d_proof" / "artifacts",
    "curvature_identity_audit": SIM_ROOT / "experiments" / "curvature_identity_audit" / "artifacts",
}


def _material_file(relative: str) -> Path:
    parsed = PurePosixPath(relative)
    if parsed.is_absolute() or ".." in parsed.parts or parsed.as_posix() != relative:
        raise ArtifactVerificationError(f"noncanonical material path: {relative}")
    return _checked_path(
        SIM_ROOT.joinpath(*parsed.parts), SIM_ROOT, expected_kind="file", label=f"material source {relative}"
    )


class ArtifactVerificationError(RuntimeError):
    """Raised when deterministic content or its provenance closure differs."""


class ArtifactGenerationRefused(RuntimeError):
    """Raised before writing when the analytic program is not exactly passing."""


class ArtifactTransactionCrash(RuntimeError):
    """Test-only abrupt-stop simulation that intentionally leaves recovery state."""


FaultInjector = Callable[[str], None] | None


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def strict_json_bytes(payload: Any) -> bytes:
    return (
        json.dumps(
            payload,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def canonical_source_text_bytes(raw: bytes) -> bytes:
    """Apply only the declared portable source-text transformation."""

    if raw.startswith(b"\xef\xbb\xbf"):
        raise ValueError("UTF-8 BOM is forbidden")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("source text must be strict UTF-8") from exc
    text = text.replace("\r\n", "\n")
    if "\r" in text:
        raise ValueError("bare CR is forbidden")
    return text.encode("utf-8")


def _is_link_or_reparse(path: Path) -> bool:
    metadata = path.lstat()
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    return path.is_symlink() or bool(getattr(metadata, "st_file_attributes", 0) & reparse_flag)


def _absolute(path: Path) -> Path:
    return Path(os.path.abspath(os.fspath(path)))


def _windows_final_directory_path(path: Path) -> Path:
    """Return the normalized long DOS path for one existing Windows directory."""

    import ctypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    create_file = kernel32.CreateFileW
    create_file.argtypes = [
        ctypes.c_wchar_p,
        ctypes.c_uint32,
        ctypes.c_uint32,
        ctypes.c_void_p,
        ctypes.c_uint32,
        ctypes.c_uint32,
        ctypes.c_void_p,
    ]
    create_file.restype = ctypes.c_void_p
    get_final_path = kernel32.GetFinalPathNameByHandleW
    get_final_path.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_uint32, ctypes.c_uint32]
    get_final_path.restype = ctypes.c_uint32
    close_handle = kernel32.CloseHandle
    close_handle.argtypes = [ctypes.c_void_p]
    close_handle.restype = ctypes.c_int

    file_read_attributes = 0x80
    share_all = 0x1 | 0x2 | 0x4
    open_existing = 3
    backup_semantics = 0x02000000
    invalid_handle = ctypes.c_void_p(-1).value
    handle = create_file(
        os.fspath(path),
        file_read_attributes,
        share_all,
        None,
        open_existing,
        backup_semantics,
        None,
    )
    if handle == invalid_handle:
        error = ctypes.get_last_error()
        raise ArtifactVerificationError(f"cannot open artifact directory identity: {error}")
    try:
        required = get_final_path(handle, None, 0, 0)
        if required == 0:
            error = ctypes.get_last_error()
            raise ArtifactVerificationError(f"cannot size final artifact directory path: {error}")
        buffer = ctypes.create_unicode_buffer(required + 1)
        written = get_final_path(handle, buffer, len(buffer), 0)
        if written == 0 or written >= len(buffer):
            error = ctypes.get_last_error()
            raise ArtifactVerificationError(f"cannot read final artifact directory path: {error}")
        final = buffer.value
    finally:
        close_handle(handle)
    if final.startswith("\\\\?\\UNC\\"):
        final = "\\\\" + final[8:]
    elif final.startswith("\\\\?\\"):
        final = final[4:]
    return Path(final)


def _canonical_existing_directory(path: Path, *, label: str) -> Path:
    checked = _assert_no_reparse_from_volume_root(path, label=label, require_leaf=True)
    if not checked.is_dir():
        raise ArtifactVerificationError(f"{label} is not an ordinary directory: {checked}")
    canonical = _windows_final_directory_path(checked) if os.name == "nt" else checked.resolve(strict=True)
    canonical = _assert_no_reparse_from_volume_root(
        canonical,
        label=f"{label} canonical path",
        require_leaf=True,
    )
    try:
        if not os.path.samefile(checked, canonical):
            raise ArtifactVerificationError(f"{label} canonical identity differs")
    except OSError as exc:
        raise ArtifactVerificationError(f"cannot compare {label} canonical identity") from exc
    return canonical


def _assert_no_reparse_from_volume_root(
    path: Path,
    *,
    label: str,
    require_leaf: bool,
) -> Path:
    """Check every existing component from the filesystem root to the leaf."""

    candidate = _absolute(path)
    current = Path(candidate.anchor)
    if not os.path.lexists(current):
        raise ArtifactVerificationError(f"{label} filesystem root is missing: {current}")
    if _is_link_or_reparse(current):
        raise ArtifactVerificationError(f"{label} filesystem root is a link/reparse point")
    for part in candidate.parts[1:]:
        current /= part
        if not os.path.lexists(current):
            if require_leaf:
                raise ArtifactVerificationError(f"{label} is missing: {current}")
            break
        if _is_link_or_reparse(current):
            raise ArtifactVerificationError(f"{label} contains a link/reparse component: {current}")
    return candidate


def _checked_path(
    path: Path,
    trust_anchor: Path,
    *,
    expected_kind: str,
    label: str,
) -> Path:
    anchor = _assert_no_reparse_from_volume_root(
        trust_anchor,
        label=f"{label} trust anchor",
        require_leaf=True,
    )
    candidate = _assert_no_reparse_from_volume_root(
        path,
        label=label,
        require_leaf=True,
    )
    try:
        candidate.relative_to(anchor)
    except ValueError as exc:
        raise ArtifactVerificationError(f"{label} escapes trust anchor: {candidate}") from exc
    if expected_kind == "file" and not candidate.is_file():
        raise ArtifactVerificationError(f"{label} is not an ordinary file: {candidate}")
    if expected_kind == "directory" and not candidate.is_dir():
        raise ArtifactVerificationError(f"{label} is not an ordinary directory: {candidate}")
    try:
        candidate.resolve(strict=True).relative_to(anchor.resolve(strict=True))
    except (OSError, ValueError) as exc:
        raise ArtifactVerificationError(f"{label} resolves outside its trust anchor") from exc
    return candidate


def recursive_raw_inventory(
    root: Path,
    *,
    trust_anchor: Path,
) -> dict[str, object]:
    checked_root = _checked_path(
        root,
        trust_anchor,
        expected_kind="directory",
        label="recursive inventory root",
    )
    entries: dict[str, dict[str, str]] = {}

    def visit(directory: Path, prefix: PurePosixPath) -> None:
        with os.scandir(directory) as scanned:
            children = sorted(scanned, key=lambda item: item.name)
        for child in children:
            path = Path(child.path)
            relative = (prefix / child.name).as_posix()
            if _is_link_or_reparse(path):
                raise ArtifactVerificationError(f"closure contains link/reparse entry: {relative}")
            if child.is_dir(follow_symlinks=False):
                entries[relative] = {"type": "directory"}
                visit(path, PurePosixPath(relative))
            elif child.is_file(follow_symlinks=False):
                entries[relative] = {
                    "type": "file",
                    "hash_domain": RAW_HASH_DOMAIN,
                    "sha256": sha256_bytes(path.read_bytes()),
                }
            else:
                raise ArtifactVerificationError(f"closure has unsupported entry type: {relative}")

    visit(checked_root, PurePosixPath())
    if not entries or not any(item["type"] == "file" for item in entries.values()):
        raise ArtifactVerificationError(f"closure contains no files: {checked_root}")
    return {
        "closure": "recursive_path_and_type_bound_no_symlink_or_reparse",
        "entry_count": len(entries),
        "entries": entries,
        "inventory_sha256": sha256_bytes(strict_json_bytes(entries)),
    }


def _overlaps(left: Path, right: Path) -> bool:
    return left == right or left in right.parents or right in left.parents


def preflight_artifact_destination(output_dir: Path) -> dict[str, object]:
    """Reject unsafe output roots before any byte is written."""

    try:
        candidate = _assert_no_reparse_from_volume_root(
            output_dir,
            label="artifact destination",
            require_leaf=False,
        )
    except ArtifactVerificationError as exc:
        raise ArtifactGenerationRefused(str(exc)) from exc
    if candidate.exists() and not candidate.is_dir():
        raise ArtifactGenerationRefused(f"artifact destination is not a directory: {candidate}")
    canonical = _absolute(ARTIFACTS_DIR)
    if candidate != canonical and _overlaps(candidate, _absolute(EXPERIMENT_DIR)):
        raise ArtifactGenerationRefused("noncanonical output overlaps experiment source tree")
    protected_paths = [
        *((f"predecessor {name}", path) for name, path in PREDECESSOR_ARTIFACT_DIRS.items()),
        *(
            (f"material source {relative}", _material_file(relative))
            for relative in REVIEWED_MATERIAL_SOURCE_PATHS
        ),
        (
            "source lock",
            SIM_ROOT.joinpath(*PurePosixPath(PROTECTED_SOURCE_LOCK_RELATIVE_PATH).parts),
        ),
    ]
    candidate_resolved = candidate.resolve(strict=False)
    for label, protected in protected_paths:
        protected_absolute = _absolute(protected)
        if _overlaps(candidate, protected_absolute) or _overlaps(
            candidate_resolved,
            protected_absolute.resolve(strict=False),
        ):
            raise ArtifactGenerationRefused(f"artifact destination overlaps {label}")
    existing: list[str] = []
    if candidate.exists():
        with os.scandir(candidate) as scanned:
            children = sorted(scanned, key=lambda item: item.name)
        for child in children:
            path = Path(child.path)
            if _is_link_or_reparse(path) or not child.is_file(follow_symlinks=False):
                raise ArtifactGenerationRefused(f"artifact destination contains nonordinary entry: {path}")
            if child.name not in EXPECTED_ARTIFACT_NAMES:
                raise ArtifactGenerationRefused(f"artifact destination contains unexpected file: {path}")
            if path.lstat().st_nlink != 1:
                raise ArtifactGenerationRefused(f"artifact destination contains multiply-linked file: {path}")
            existing.append(child.name)
    return {
        "destination": candidate.as_posix(),
        "canonical_destination": candidate == canonical,
        "existing_expected_files": existing,
        "preflight_passed": True,
    }


@dataclass(frozen=True)
class ArtifactTransactionPaths:
    """Fixed sibling paths used by one artifact destination transaction."""

    target: Path
    parent: Path
    journal: Path
    journal_temp: Path
    stage: Path
    backup: Path


_TRANSACTION_SCHEMA_VERSION = 1
_TRANSACTION_STATES = {"prepared", "old_moved", "new_published", "verified"}
_TRANSACTION_PREFIX = ".cwt-cgt-artifacts-transaction-v1"
_RESERVED_TRANSACTION_LEAVES = (
    f"{_TRANSACTION_PREFIX}.journal.json",
    f"{_TRANSACTION_PREFIX}.journal.tmp",
    f"{_TRANSACTION_PREFIX}.stage",
    f"{_TRANSACTION_PREFIX}.backup",
)
_LOCK_WAIT_SECONDS = 30.0
_LOCK_POLL_SECONDS = 0.02
_THREAD_LOCK_REGISTRY_GUARD = threading.Lock()
_THREAD_LOCKS: dict[str, threading.Lock] = {}


def artifact_transaction_paths(output_dir: Path = ARTIFACTS_DIR) -> ArtifactTransactionPaths:
    """Return one physical-parent-scoped transaction namespace.

    An existing requested target is canonicalized to its actual directory entry,
    so long and DOS-short leaf aliases share both target and auxiliary paths.
    """

    requested = _absolute(output_dir)
    parent = _canonical_existing_directory(
        requested.parent,
        label="artifact transaction parent",
    )
    target = parent / requested.name
    if os.path.lexists(target):
        target = _canonical_existing_directory(target, label="artifact transaction target")
        try:
            if not os.path.samefile(target.parent, parent):
                raise ArtifactVerificationError("artifact transaction target parent differs")
        except OSError as exc:
            raise ArtifactVerificationError(
                "cannot compare artifact transaction target parent identity"
            ) from exc
    paths = ArtifactTransactionPaths(
        target=target,
        parent=parent,
        journal=parent / _RESERVED_TRANSACTION_LEAVES[0],
        journal_temp=parent / _RESERVED_TRANSACTION_LEAVES[1],
        stage=parent / _RESERVED_TRANSACTION_LEAVES[2],
        backup=parent / _RESERVED_TRANSACTION_LEAVES[3],
    )
    _reject_reserved_transaction_target(paths)
    return paths


def _transaction_leaf_identity(value: str) -> str:
    return os.path.normcase(value).casefold() if os.name == "nt" else value


def _reject_reserved_transaction_target(paths: ArtifactTransactionPaths) -> None:
    reserved = (paths.journal, paths.journal_temp, paths.stage, paths.backup)
    target_identity = _transaction_leaf_identity(paths.target.name)
    if target_identity in {_transaction_leaf_identity(path.name) for path in reserved}:
        raise ArtifactVerificationError("artifact target collides with the reserved transaction namespace")
    if not os.path.lexists(paths.target):
        return
    for path in reserved:
        if not os.path.lexists(path):
            continue
        try:
            if os.path.samefile(paths.target, path):
                raise ArtifactVerificationError(
                    "artifact target is physically equivalent to a reserved transaction path"
                )
        except OSError as exc:
            raise ArtifactVerificationError(
                "cannot compare artifact target with reserved transaction path"
            ) from exc


def _checkpoint(name: str, fault_injector: FaultInjector) -> None:
    if fault_injector is not None:
        fault_injector(name)


def _sync_file(handle: Any) -> None:
    handle.flush()
    os.fsync(handle.fileno())


def _sync_directory_metadata(path: Path) -> None:
    """Durably sync directory metadata where the host exposes that primitive.

    Windows directory replacements use ``MoveFileExW(..., WRITE_THROUGH)`` in
    :func:`_durable_replace`; regular files are flushed before publication.
    POSIX additionally fsyncs the containing directory descriptor.
    """

    if os.name == "nt":
        return
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    descriptor = os.open(path, flags)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _durable_replace(source: Path, destination: Path) -> None:
    """Atomically replace a same-parent path and request metadata durability."""

    if source.parent != destination.parent:
        raise ArtifactVerificationError("transaction rename must remain on one filesystem")
    if os.name == "nt":
        import ctypes

        move_file_ex = ctypes.windll.kernel32.MoveFileExW
        move_file_ex.argtypes = [ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_uint32]
        move_file_ex.restype = ctypes.c_int
        replace_existing = 0x1
        write_through = 0x8
        if not move_file_ex(
            os.fspath(source),
            os.fspath(destination),
            replace_existing | write_through,
        ):
            error = ctypes.get_last_error()
            raise OSError(error, f"durable replace failed: {source} -> {destination}")
        return
    os.replace(source, destination)
    _sync_directory_metadata(source.parent)


def _artifact_lock_key(target: Path) -> str:
    parent = _canonical_existing_directory(
        target.parent,
        label="artifact lock parent",
    )
    try:
        metadata = parent.stat()
    except OSError as exc:
        raise ArtifactVerificationError("cannot read artifact lock parent identity") from exc
    if not stat.S_ISDIR(metadata.st_mode) or metadata.st_ino <= 0 or metadata.st_dev < 0:
        raise ArtifactVerificationError("artifact lock parent has no stable filesystem identity")
    identity = {
        "parent_device": int(metadata.st_dev),
        "parent_inode": int(metadata.st_ino),
        "schema_version": 1,
    }
    return sha256_bytes(strict_json_bytes(identity))


def _thread_lock_for(key: str) -> threading.Lock:
    with _THREAD_LOCK_REGISTRY_GUARD:
        return _THREAD_LOCKS.setdefault(key, threading.Lock())


def _windows_mutex_name(key: str) -> str:
    return f"Global\\CWT_CGT_ARTIFACTS_{key}"


@contextmanager
def _windows_named_mutex(key: str, timeout_seconds: float) -> Iterator[None]:
    """Acquire a crash-releasing cross-session mutex without filesystem lock state."""

    import ctypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    create_mutex = kernel32.CreateMutexW
    create_mutex.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_wchar_p]
    create_mutex.restype = ctypes.c_void_p
    wait_for_single_object = kernel32.WaitForSingleObject
    wait_for_single_object.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
    wait_for_single_object.restype = ctypes.c_uint32
    release_mutex = kernel32.ReleaseMutex
    release_mutex.argtypes = [ctypes.c_void_p]
    release_mutex.restype = ctypes.c_int
    close_handle = kernel32.CloseHandle
    close_handle.argtypes = [ctypes.c_void_p]
    close_handle.restype = ctypes.c_int

    name = _windows_mutex_name(key)
    handle = create_mutex(None, False, name)
    if not handle:
        error = ctypes.get_last_error()
        raise ArtifactVerificationError(f"cannot create artifact process mutex: {error}")
    wait_milliseconds = min(0xFFFFFFFE, max(0, int(timeout_seconds * 1000 + 0.999)))
    wait_result = wait_for_single_object(handle, wait_milliseconds)
    acquired = wait_result in {0x00000000, 0x00000080}
    if not acquired:
        close_handle(handle)
        if wait_result == 0x00000102:
            raise ArtifactVerificationError("timed out waiting for artifact process lock")
        raise ArtifactVerificationError(f"artifact process mutex wait failed with status {wait_result}")
    try:
        yield
    finally:
        try:
            if not release_mutex(handle):
                error = ctypes.get_last_error()
                raise ArtifactVerificationError(f"cannot release artifact process mutex: {error}")
        finally:
            close_handle(handle)


@contextmanager
def _posix_parent_directory_lock(parent: Path, timeout_seconds: float) -> Iterator[None]:
    """Lock an existing parent-directory descriptor; the kernel releases it on crash."""

    import fcntl

    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    descriptor = os.open(parent, flags)
    deadline = time.monotonic() + timeout_seconds
    acquired = False
    try:
        while True:
            try:
                fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
                acquired = True
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    raise ArtifactVerificationError("timed out waiting for artifact process lock")
                time.sleep(_LOCK_POLL_SECONDS)
        yield
    finally:
        try:
            if acquired:
                fcntl.flock(descriptor, fcntl.LOCK_UN)
        finally:
            os.close(descriptor)


def _ordinary_transaction_entry(path: Path, *, kind: str, label: str) -> None:
    if not os.path.lexists(path):
        return
    if _is_link_or_reparse(path):
        raise ArtifactVerificationError(f"{label} is a link/reparse point: {path}")
    if kind == "file" and not path.is_file():
        raise ArtifactVerificationError(f"{label} is not an ordinary file: {path}")
    if kind == "directory" and not path.is_dir():
        raise ArtifactVerificationError(f"{label} is not an ordinary directory: {path}")


def _remove_plain_tree(
    path: Path,
    *,
    fault_injector: FaultInjector = None,
    checkpoint_prefix: str = "remove_tree",
    relative_root: Path | None = None,
) -> None:
    """Remove a validated transaction tree without following reparse entries."""

    if not os.path.lexists(path):
        return
    if _is_link_or_reparse(path) or not path.is_dir():
        raise ArtifactVerificationError(f"transaction tree is not an ordinary directory: {path}")
    root = path if relative_root is None else relative_root
    with os.scandir(path) as scanned:
        children = sorted(scanned, key=lambda item: item.name, reverse=True)
    for child in children:
        child_path = Path(child.path)
        relative = child_path.relative_to(root).as_posix().replace("/", "_")
        if _is_link_or_reparse(child_path):
            raise ArtifactVerificationError(f"transaction tree contains a link/reparse entry: {child_path}")
        if child.is_dir(follow_symlinks=False):
            _remove_plain_tree(
                child_path,
                fault_injector=fault_injector,
                checkpoint_prefix=checkpoint_prefix,
                relative_root=root,
            )
        elif child.is_file(follow_symlinks=False):
            _checkpoint(f"before_{checkpoint_prefix}_unlink_{relative}", fault_injector)
            child_path.unlink()
            _checkpoint(f"after_{checkpoint_prefix}_unlink_{relative}", fault_injector)
        else:
            raise ArtifactVerificationError(f"unsupported transaction entry: {child_path}")
    relative_directory = path.relative_to(root).as_posix().replace("/", "_")
    suffix = f"_{relative_directory}" if relative_directory != "." else ""
    _checkpoint(f"before_{checkpoint_prefix}_rmdir{suffix}", fault_injector)
    path.rmdir()
    _checkpoint(f"after_{checkpoint_prefix}_rmdir{suffix}", fault_injector)


def _write_bytes_durable(path: Path, payload: bytes) -> None:
    with path.open("xb") as handle:
        handle.write(payload)
        _sync_file(handle)


@contextmanager
def _artifact_process_lock(
    paths: ArtifactTransactionPaths,
    *,
    timeout_seconds: float = _LOCK_WAIT_SECONDS,
) -> Iterator[None]:
    """Serialize threads/processes with crash-releasing OS-held lock primitives."""

    _assert_no_reparse_from_volume_root(
        paths.parent,
        label="artifact transaction parent",
        require_leaf=True,
    )
    key = _artifact_lock_key(paths.target)
    thread_lock = _thread_lock_for(key)
    deadline = time.monotonic() + timeout_seconds
    if not thread_lock.acquire(timeout=max(0.0, timeout_seconds)):
        raise ArtifactVerificationError("timed out waiting for artifact process lock")
    try:
        remaining = max(0.0, deadline - time.monotonic())
        backend = _windows_named_mutex if os.name == "nt" else _posix_parent_directory_lock
        argument = key if os.name == "nt" else paths.parent
        with backend(argument, remaining):
            yield
    finally:
        thread_lock.release()


def _artifact_hash_manifest(expected: Mapping[str, bytes]) -> dict[str, str]:
    if set(expected) != EXPECTED_ARTIFACT_NAMES:
        raise ArtifactGenerationRefused("transaction payload does not contain the exact artifact set")
    return {name: sha256_bytes(expected[name]) for name in sorted(expected)}


def _generation_id(manifest: Mapping[str, str]) -> str:
    return sha256_bytes(strict_json_bytes(dict(manifest)))


def _artifact_entries(directory: Path) -> dict[str, Path]:
    absolute = _absolute(directory)
    trust_anchor = SIM_ROOT if SIM_ROOT in absolute.parents else absolute.parent
    inventory = recursive_raw_inventory(directory, trust_anchor=trust_anchor)
    entries = inventory["entries"]
    if any(item["type"] != "file" for item in entries.values()):
        raise ArtifactVerificationError("artifact directory must contain only ordinary files")
    return {name: directory.joinpath(*PurePosixPath(name).parts) for name in entries}


def _read_complete_artifact_generation(directory: Path) -> dict[str, bytes]:
    entries = _artifact_entries(directory)
    if set(entries) != EXPECTED_ARTIFACT_NAMES:
        raise ArtifactVerificationError("artifact generation does not contain the exact file set")
    payloads = {name: entries[name].read_bytes() for name in sorted(entries)}
    if any(b"\r" in payload for payload in payloads.values()):
        raise ArtifactVerificationError("artifact generation is not strict LF")
    try:
        checksums = json.loads(payloads["CHECKSUMS.json"].decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ArtifactVerificationError("artifact checksum manifest is malformed") from exc
    if strict_json_bytes(checksums) != payloads["CHECKSUMS.json"]:
        raise ArtifactVerificationError("artifact checksum manifest is not canonical JSON")
    expected_checksum_names = EXPECTED_ARTIFACT_NAMES - {"CHECKSUMS.json"}
    if (
        set(checksums) != {"files", "hash_domain", "schema_version"}
        or checksums.get("schema_version") != 1
        or checksums.get("hash_domain") != RAW_HASH_DOMAIN
        or set(checksums.get("files", {})) != expected_checksum_names
    ):
        raise ArtifactVerificationError("artifact checksum manifest has the wrong schema")
    for name, expected_hash in checksums["files"].items():
        if sha256_bytes(payloads[name]) != expected_hash:
            raise ArtifactVerificationError(f"artifact checksum mismatch: {name}")
    return payloads


def _validate_expected_generation(directory: Path, expected: Mapping[str, bytes]) -> None:
    actual = _read_complete_artifact_generation(directory)
    if actual != {name: expected[name] for name in sorted(expected)}:
        raise ArtifactVerificationError("artifact transaction generation bytes differ")


def _journal_record(
    paths: ArtifactTransactionPaths,
    manifest: Mapping[str, str],
    *,
    state: str,
    had_old_target: bool,
) -> dict[str, object]:
    if state not in _TRANSACTION_STATES:
        raise ArtifactVerificationError(f"unknown artifact transaction state: {state}")
    return {
        "backup_name": paths.backup.name,
        "expected_files": dict(manifest),
        "generation_id": _generation_id(manifest),
        "had_old_target": had_old_target,
        "journal_kind": "cwt_cgt_atomic_artifact_directory_swap_v1",
        "schema_version": _TRANSACTION_SCHEMA_VERSION,
        "stage_name": paths.stage.name,
        "state": state,
        "target_name": paths.target.name,
    }


def _validated_transaction_target_leaf(value: object) -> str:
    if not isinstance(value, str) or not value or value in {".", ".."}:
        raise ArtifactVerificationError("artifact transaction journal target leaf is malformed")
    if any(separator in value for separator in ("/", "\\", ":")):
        raise ArtifactVerificationError("artifact transaction journal target leaf is noncanonical")
    if Path(value).name != value or value.endswith((" ", ".")):
        raise ArtifactVerificationError("artifact transaction journal target leaf is noncanonical")
    if _transaction_leaf_identity(value) in {
        _transaction_leaf_identity(leaf) for leaf in _RESERVED_TRANSACTION_LEAVES
    }:
        raise ArtifactVerificationError(
            "artifact transaction journal target collides with its reserved namespace"
        )
    return value


def _validate_journal(
    paths: ArtifactTransactionPaths,
    payload: bytes,
    *,
    expected_target_name: str | None = None,
) -> dict[str, object]:
    try:
        record = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ArtifactVerificationError("artifact transaction journal is malformed") from exc
    if strict_json_bytes(record) != payload:
        raise ArtifactVerificationError("artifact transaction journal is not canonical JSON")
    required = {
        "backup_name",
        "expected_files",
        "generation_id",
        "had_old_target",
        "journal_kind",
        "schema_version",
        "stage_name",
        "state",
        "target_name",
    }
    if set(record) != required:
        raise ArtifactVerificationError("artifact transaction journal fields differ")
    target_name = _validated_transaction_target_leaf(record.get("target_name"))
    if (
        record.get("schema_version") != _TRANSACTION_SCHEMA_VERSION
        or record.get("journal_kind") != "cwt_cgt_atomic_artifact_directory_swap_v1"
        or record.get("stage_name") != paths.stage.name
        or record.get("backup_name") != paths.backup.name
        or record.get("state") not in _TRANSACTION_STATES
        or not isinstance(record.get("had_old_target"), bool)
    ):
        raise ArtifactVerificationError("artifact transaction journal path or state mismatch")
    if expected_target_name is not None and target_name != expected_target_name:
        raise ArtifactVerificationError("artifact transaction journal target differs")
    manifest = record.get("expected_files")
    if not isinstance(manifest, dict) or set(manifest) != EXPECTED_ARTIFACT_NAMES:
        raise ArtifactVerificationError("artifact transaction journal file set mismatch")
    if not all(
        isinstance(name, str)
        and isinstance(digest, str)
        and len(digest) == 64
        and all(character in "0123456789abcdef" for character in digest)
        for name, digest in manifest.items()
    ):
        raise ArtifactVerificationError("artifact transaction journal hashes are malformed")
    if record.get("generation_id") != _generation_id(manifest):
        raise ArtifactVerificationError("artifact transaction generation ID mismatch")
    return record


def _write_journal(
    paths: ArtifactTransactionPaths,
    record: Mapping[str, object],
    fault_injector: FaultInjector,
) -> None:
    state = str(record["state"])
    _checkpoint(f"before_journal_{state}", fault_injector)
    _ordinary_transaction_entry(
        paths.journal_temp,
        kind="file",
        label="artifact transaction journal temp",
    )
    if paths.journal_temp.exists():
        paths.journal_temp.unlink()
    _write_bytes_durable(paths.journal_temp, strict_json_bytes(dict(record)))
    _checkpoint(f"after_journal_temp_fsync_{state}", fault_injector)
    _durable_replace(paths.journal_temp, paths.journal)
    _checkpoint(f"after_journal_{state}", fault_injector)


def _remove_journal(paths: ArtifactTransactionPaths) -> None:
    for journal_path in (paths.journal_temp, paths.journal):
        _ordinary_transaction_entry(
            journal_path,
            kind="file",
            label="artifact transaction journal",
        )
        if journal_path.exists():
            journal_path.unlink()
    _sync_directory_metadata(paths.parent)


def _directory_matches_manifest(directory: Path, manifest: Mapping[str, str]) -> bool:
    if not directory.is_dir():
        return False
    try:
        payloads = _read_complete_artifact_generation(directory)
    except ArtifactVerificationError:
        return False
    return _artifact_hash_manifest(payloads) == dict(manifest)


def _recover_transaction_unlocked(
    paths: ArtifactTransactionPaths,
    *,
    prefer_rollback: bool = False,
    fault_injector: FaultInjector = None,
) -> str:
    """Recover one abandoned directory-swap transaction while holding the lock."""

    for path, kind, label in (
        (paths.journal, "file", "artifact transaction journal"),
        (paths.journal_temp, "file", "artifact transaction journal temp"),
        (paths.stage, "directory", "artifact transaction stage"),
        (paths.backup, "directory", "artifact transaction backup"),
    ):
        _ordinary_transaction_entry(path, kind=kind, label=label)

    if not paths.journal.exists():
        if paths.backup.exists():
            raise ArtifactVerificationError(
                "artifact transaction backup exists without its path-binding journal"
            )
        if paths.stage.exists():
            _remove_plain_tree(paths.stage)
        if paths.journal_temp.exists():
            paths.journal_temp.unlink()
        _sync_directory_metadata(paths.parent)
        return "NO_ACTIVE_TRANSACTION"

    record = _validate_journal(
        paths,
        paths.journal.read_bytes(),
        expected_target_name=paths.target.name,
    )
    manifest = dict(record["expected_files"])
    had_old = bool(record["had_old_target"])

    if prefer_rollback:
        if had_old:
            if paths.backup.exists():
                _read_complete_artifact_generation(paths.backup)
                if paths.target.exists():
                    _remove_plain_tree(paths.target)
                _durable_replace(paths.backup, paths.target)
            elif paths.target.exists():
                _read_complete_artifact_generation(paths.target)
            else:
                raise ArtifactVerificationError("rollback has neither old target nor backup")
        elif paths.target.exists():
            if not _directory_matches_manifest(paths.target, manifest):
                raise ArtifactVerificationError("new target is invalid during rollback")
            _remove_plain_tree(paths.target)
        if paths.stage.exists():
            _remove_plain_tree(paths.stage)
        _remove_journal(paths)
        return "ROLLED_BACK"

    if _directory_matches_manifest(paths.target, manifest):
        if paths.backup.exists():
            _remove_plain_tree(
                paths.backup,
                fault_injector=fault_injector,
                checkpoint_prefix="cleanup_backup",
            )
        if paths.stage.exists():
            _remove_plain_tree(paths.stage)
        _remove_journal(paths)
        return "COMMITTED_NEW"

    if paths.backup.exists():
        _read_complete_artifact_generation(paths.backup)
        if paths.target.exists():
            _remove_plain_tree(paths.target)
        _durable_replace(paths.backup, paths.target)
        if paths.stage.exists():
            _remove_plain_tree(paths.stage)
        _remove_journal(paths)
        return "ROLLED_BACK_OLD"

    if paths.target.exists():
        _read_complete_artifact_generation(paths.target)
        if paths.stage.exists():
            _remove_plain_tree(paths.stage)
        _remove_journal(paths)
        return "PRESERVED_OLD"
    if not had_old:
        if _directory_matches_manifest(paths.stage, manifest):
            _durable_replace(paths.stage, paths.target)
            _read_complete_artifact_generation(paths.target)
            _remove_journal(paths)
            return "COMMITTED_STAGED_INITIAL"
        if paths.stage.exists():
            _remove_plain_tree(paths.stage)
        _remove_journal(paths)
        return "ROLLED_BACK_EMPTY"
    raise ArtifactVerificationError("artifact transaction cannot recover a complete generation")


def _paths_for_transaction_target(
    paths: ArtifactTransactionPaths,
    target: Path,
) -> ArtifactTransactionPaths:
    return ArtifactTransactionPaths(
        target=target,
        parent=paths.parent,
        journal=paths.journal,
        journal_temp=paths.journal_temp,
        stage=paths.stage,
        backup=paths.backup,
    )


def _active_journal_paths(paths: ArtifactTransactionPaths) -> ArtifactTransactionPaths:
    record = _validate_journal(paths, paths.journal.read_bytes())
    leaf = _validated_transaction_target_leaf(record["target_name"])
    target = paths.parent / leaf
    if os.path.lexists(target):
        canonical = _canonical_existing_directory(
            target,
            label="active artifact transaction target",
        )
        if canonical.name != leaf:
            raise ArtifactVerificationError(
                "artifact transaction journal target is not the canonical directory entry"
            )
        target = canonical
    return _paths_for_transaction_target(paths, target)


def _recover_parent_transaction_for_request(
    paths: ArtifactTransactionPaths,
) -> tuple[ArtifactTransactionPaths, str]:
    """Recover the fixed parent journal before resolving the requested target alias."""

    _ordinary_transaction_entry(
        paths.journal,
        kind="file",
        label="artifact transaction journal",
    )
    if paths.journal.exists():
        active_paths = _active_journal_paths(paths)
        result = _recover_transaction_unlocked(active_paths)
    else:
        result = _recover_transaction_unlocked(paths)
    return artifact_transaction_paths(paths.target), result


@contextmanager
def artifact_access_guard(output_dir: Path = ARTIFACTS_DIR) -> Iterator[None]:
    """Serialize cooperating public APIs and recover before guarded access.

    Arbitrary filesystem readers that bypass this guard are outside the atomic
    publication contract and can observe the brief directory-swap interval.
    Windows cooperating APIs share a ``Global\\`` kernel mutex across sessions;
    inability to create or acquire it fails closed.
    """

    paths = artifact_transaction_paths(output_dir)
    with _artifact_process_lock(paths):
        _paths, _result = _recover_parent_transaction_for_request(paths)
        yield


def recover_artifact_transaction(output_dir: Path = ARTIFACTS_DIR) -> str:
    """Recover stale transaction state and return the selected complete generation."""

    paths = artifact_transaction_paths(output_dir)
    with _artifact_process_lock(paths):
        _paths, result = _recover_parent_transaction_for_request(paths)
        return result


def _publish_artifact_mapping(
    output_dir: Path,
    expected: Mapping[str, bytes],
    *,
    fault_injector: FaultInjector = None,
) -> None:
    """Publish a complete mapping for readers using :func:`artifact_access_guard`."""

    requested_paths = artifact_transaction_paths(output_dir)
    manifest = _artifact_hash_manifest(expected)
    with _artifact_process_lock(requested_paths):
        paths, _recovery = _recover_parent_transaction_for_request(requested_paths)
        preflight_artifact_destination(paths.target)
        if paths.stage.exists() or paths.backup.exists() or paths.journal.exists():
            raise ArtifactVerificationError("artifact transaction auxiliaries remain after recovery")
        had_old = paths.target.exists()
        if had_old:
            _read_complete_artifact_generation(paths.target)
        paths.stage.mkdir()
        _sync_directory_metadata(paths.parent)
        try:
            for name in sorted(expected):
                _checkpoint(f"before_stage_write_{name}", fault_injector)
                _write_bytes_durable(paths.stage / name, expected[name])
                _checkpoint(f"after_stage_write_{name}", fault_injector)
            _sync_directory_metadata(paths.stage)
            _checkpoint("after_stage_fsync", fault_injector)
            _validate_expected_generation(paths.stage, expected)
            _checkpoint("after_staging_verify", fault_injector)

            record = _journal_record(
                paths,
                manifest,
                state="prepared",
                had_old_target=had_old,
            )
            _write_journal(paths, record, fault_injector)
            if had_old:
                _checkpoint("before_old_to_backup", fault_injector)
                _durable_replace(paths.target, paths.backup)
                _checkpoint("after_old_to_backup", fault_injector)
                record = {**record, "state": "old_moved"}
                _write_journal(paths, record, fault_injector)

            _checkpoint("before_new_to_target", fault_injector)
            _durable_replace(paths.stage, paths.target)
            _checkpoint("after_new_to_target", fault_injector)
            record = {**record, "state": "new_published"}
            _write_journal(paths, record, fault_injector)
            _validate_expected_generation(paths.target, expected)
            _checkpoint("after_target_verify", fault_injector)
            record = {**record, "state": "verified"}
            _write_journal(paths, record, fault_injector)
            _checkpoint("before_cleanup", fault_injector)
            if paths.backup.exists():
                _remove_plain_tree(
                    paths.backup,
                    fault_injector=fault_injector,
                    checkpoint_prefix="cleanup_backup",
                )
            _remove_journal(paths)
            _checkpoint("after_cleanup", fault_injector)
        except ArtifactTransactionCrash:
            raise
        except BaseException:
            durably_verified = False
            if paths.journal.exists():
                try:
                    durable_record = _validate_journal(
                        paths,
                        paths.journal.read_bytes(),
                        expected_target_name=paths.target.name,
                    )
                except ArtifactVerificationError:
                    durable_record = {}
                durably_verified = durable_record.get("state") == "verified" and _directory_matches_manifest(
                    paths.target, manifest
                )
            _recover_transaction_unlocked(paths, prefer_rollback=not durably_verified)
            raise
