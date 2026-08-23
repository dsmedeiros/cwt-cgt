"""Deterministic five-file closure and local transactional publication."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, Sequence

from .contract import (
    MODEL_CONTRACT,
    REVIEWED_RECORD_AGGREGATE_SHA256,
    REVIEWED_RECORD_DIGESTS,
    REVIEWED_REGISTRY_SHA256,
)
from .exact import Gaussian
from .theorem import execute_program, require_semantic_pass as require_theorem_semantic_pass
from .transaction import (
    ArtifactGenerationRefused,
    ArtifactTransactionCrash,
    ArtifactVerificationError,
    _assert_no_reparse_from_volume_root,
    _checked_path,
    _publish_artifact_mapping,
    artifact_access_guard,
    artifact_transaction_paths,
    canonical_source_text_bytes,
    preflight_artifact_destination,
    recursive_raw_inventory,
)

EXPERIMENT_DIR = Path(__file__).resolve().parent
SIM_ROOT = EXPERIMENT_DIR.parents[1]
REPO_ROOT = SIM_ROOT.parent
REVIEWED_REPO_ROOT = REPO_ROOT
ARTIFACTS_DIR = EXPERIMENT_DIR / "artifacts"
EXPECTED_ARTIFACT_NAMES = frozenset(
    {"CHECKSUMS.json", "PROVENANCE.json", "REPORT.md", "records.json", "summary.json"}
)
SOURCE_HASH_DOMAIN = "sha256_utf8_lf_v1_CRLF_to_LF_only_no_BOM_no_bare_CR"
RAW_HASH_DOMAIN = "sha256_raw_bytes_v1"
SOURCE_BLOB_HASH_DOMAIN = "sha256_raw_git_index_blob_v1"
SOURCE_LOCK_HASH_DOMAIN = "sha256_raw_bytes_v1"
SOURCE_LOCK_RELATIVE_PATH = "cwt-sim/experiments/loop_flux_counting_curvature_proof/SOURCE_LOCK.json"
_REVIEWED_SUBPROCESS_RUN = subprocess.run
_REVIEWED_PYTHON_EXECUTABLE = str(Path(sys.executable).resolve(strict=True))
_DISCOVERED_GIT_EXECUTABLE = shutil.which("git")
if not _DISCOVERED_GIT_EXECUTABLE:
    raise RuntimeError("trusted Git executable is unavailable")
_REVIEWED_GIT_EXECUTABLE = str(Path(_DISCOVERED_GIT_EXECUTABLE).resolve(strict=True))
_GIT_EXECUTABLE_ENV = "CWT_CGT_GIT_EXECUTABLE"
_REVIEWED_SOURCE_LOCK_SCHEMA = "git_index_source_lock_v1"
_REVIEWED_SOURCE_LOCK_PARENT = "7b0412ea06ff0b61bf6efa1fc1aae57a913ceac1"
_REVIEWED_SOURCE_LOCK_OBJECT_FORMAT = "sha1"
_REVIEWED_SOURCE_LOCK_PATH_SET_SHA256 = "03e571326d2d777a00828e917a9f275b047d9b2776e57f9d1f70dd4c2bbc587f"
_SOURCE_AUTHORITY_BOOTSTRAP_PATHS = (
    "cwt-sim/experiments/loop_flux_counting_curvature_proof/source_lock.py",
    "cwt-sim/experiments/loop_flux_counting_curvature_proof/transaction.py",
)

REVIEWED_DEPENDENCY_POLICY_PATH = "requirements.test.txt"
DEPENDENCY_POLICY_PATH = REVIEWED_DEPENDENCY_POLICY_PATH
REVIEWED_DEPENDENCY_POLICY_SHA256 = "11cc1302a3896ed8af355bcfad65bc7aeec70ceeac2cec2c3a70ea456c507539"
REVIEWED_DEPENDENCY_POLICY_REQUIREMENTS = (
    "numpy>=1.24",
    "scipy>=1.10",
    "networkx>=3.1",
    "pandas>=2.0",
    "matplotlib>=3.7",
    "pytest>=7.4",
    "pydantic>=2.4",
    "pyyaml>=6.0",
    "typer>=0.9",
    "black==24.10.0",
    "mypy==1.11.2",
    "ruff==0.7.3",
)
REVIEWED_DEPENDENCY_POLICY_RECORD_SHA256 = "9bb568329235a52d9e9fb0adad92c378c1ea672569633b4269b6992b534b2a7c"

REVIEWED_CLEAN_CLI_LOCAL_MODULE_PATHS = (
    "experiments/__init__.py",
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
    "experiments/loop_flux_counting_curvature_proof/theorem.py",
    "experiments/loop_flux_counting_curvature_proof/transaction.py",
)
REVIEWED_CLEAN_CLI_PATH_SET_SHA256 = "c66c8fdedadbd2845fcdaef9b8e4a2ea3374b456ef1d6bd5e890640656f407d6"
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
REVIEWED_MATERIAL_SOURCE_PATH_SET_SHA256 = "732858be9d86201ff8680a27bfb463950234c217be55b039b9aad144495f48cf"
_REVIEWED_SOURCE_LOCK_REPO_PATHS = tuple(f"cwt-sim/{path}" for path in REVIEWED_MATERIAL_SOURCE_PATHS)
REVIEWED_PREDECESSOR_INVENTORY_DIGESTS = {
    "constitutive_map_3d_proof": {
        "entry_count": 5,
        "inventory_sha256": "c619df9f5eefc2d05b52fc19847a68a0662026ee5050389e94b6cf151a15faa3",
    },
    "curvature_identity_audit": {
        "entry_count": 5,
        "inventory_sha256": "01333a0414fb82eeb73e8b9a072f7ed43815afd6af9497ec1672f6870cd0d85c",
    },
    "shared_generator_counting_curvature_proof": {
        "entry_count": 5,
        "inventory_sha256": "5e843e42ea9dfd0872b6ecd8e06c42bd6477190d33bf45ccafcdce6ff1e35ca0",
    },
}
REVIEWED_PREDECESSOR_INVENTORY_DIGESTS_SHA256 = (
    "3f962f11c5b274cf9e7c65ffb6d5c3c57803d6b021f9469f43f5d3dfd2bcc039"
)

PREDECESSOR_ARTIFACT_DIRS = {
    "constitutive_map_3d_proof": SIM_ROOT / "experiments" / "constitutive_map_3d_proof" / "artifacts",
    "curvature_identity_audit": SIM_ROOT / "experiments" / "curvature_identity_audit" / "artifacts",
    "shared_generator_counting_curvature_proof": SIM_ROOT
    / "experiments"
    / "shared_generator_counting_curvature_proof"
    / "artifacts",
}
REVIEWED_PREDECESSOR_ROLE_PATHS = (
    ("constitutive_map_3d_proof", "experiments/constitutive_map_3d_proof/artifacts"),
    ("curvature_identity_audit", "experiments/curvature_identity_audit/artifacts"),
    (
        "shared_generator_counting_curvature_proof",
        "experiments/shared_generator_counting_curvature_proof/artifacts",
    ),
)
REVIEWED_PREDECESSOR_ROLE_PATHS_SHA256 = "9eb29652acbf83b1861e79dfccf5d08c934b470462d197b617b398662f1d7fb1"


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def jsonable(value: Any) -> Any:
    from fractions import Fraction

    if type(value) is Fraction:
        return {
            "fraction": f"{value.numerator}/{value.denominator}",
            "numerator": value.numerator,
            "denominator": value.denominator,
            "float": float(value),
        }
    if type(value) is Gaussian:
        return {"real": jsonable(value.real), "imag": jsonable(value.imag)}
    if isinstance(value, tuple):
        return [jsonable(item) for item in value]
    if isinstance(value, list):
        return [jsonable(item) for item in value]
    if isinstance(value, dict):
        return {str(key): jsonable(item) for key, item in value.items()}
    if value is None or type(value) in {bool, int, float, str}:
        return value
    raise TypeError(f"unsupported artifact value: {type(value).__name__}")


def strict_json_bytes(payload: Any) -> bytes:
    return (
        json.dumps(
            jsonable(payload),
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _canonical_relative(relative: str) -> PurePosixPath:
    parsed = PurePosixPath(relative)
    if (
        type(relative) is not str
        or not relative
        or parsed.is_absolute()
        or parsed.as_posix() != relative
        or "." in parsed.parts
        or ".." in parsed.parts
    ):
        raise ArtifactVerificationError(f"noncanonical relative source path: {relative}")
    return parsed


def _source_file(relative: str) -> Path:
    parsed = _canonical_relative(relative)
    path = SIM_ROOT.joinpath(*parsed.parts)
    return _checked_path(
        path,
        SIM_ROOT,
        expected_kind="file",
        label=f"material source {relative}",
    )


def dependency_policy_record() -> dict[str, object]:
    relative = DEPENDENCY_POLICY_PATH
    path = _dependency_policy_file()
    raw = path.read_bytes()
    digest = sha256_bytes(canonical_source_text_bytes(raw))
    requirements = tuple(
        line.strip()
        for line in canonical_source_text_bytes(raw).decode("utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    )
    record = {
        "authority": "deterministic_source_bound_dependency_declaration",
        "path": relative,
        "hash_domain": SOURCE_HASH_DOMAIN,
        "sha256": digest,
        "declared_requirements": list(requirements),
        "live_python_version_in_acceptance_bytes": False,
        "live_typer_version_in_acceptance_bytes": False,
    }
    if digest != REVIEWED_DEPENDENCY_POLICY_SHA256:
        raise ArtifactVerificationError("dependency policy source hash differs")
    if requirements != REVIEWED_DEPENDENCY_POLICY_REQUIREMENTS:
        raise ArtifactVerificationError("dependency policy requirements differ")
    validate_dependency_policy_record(record)
    return record


def _dependency_policy_file() -> Path:
    relative = DEPENDENCY_POLICY_PATH
    if type(relative) is not str or relative != REVIEWED_DEPENDENCY_POLICY_PATH:
        raise ArtifactVerificationError("dependency policy path differs from reviewed lexical path")
    parsed = PurePosixPath(relative)
    if (
        parsed.as_posix() != relative
        or parsed.is_absolute()
        or "." in parsed.parts
        or ".." in parsed.parts
        or len(parsed.parts) != 1
    ):
        raise ArtifactVerificationError("dependency policy path is noncanonical")
    if REPO_ROOT != REVIEWED_REPO_ROOT:
        raise ArtifactVerificationError("dependency policy repository root differs")
    return _checked_path(
        REPO_ROOT.joinpath(*parsed.parts),
        REVIEWED_REPO_ROOT,
        expected_kind="file",
        label="dependency policy",
    )


def validate_dependency_policy_record(record: object) -> None:
    """Validate a producer result against the independent reviewed policy."""

    raw = _dependency_policy_file().read_bytes()
    canonical = canonical_source_text_bytes(raw)
    digest = sha256_bytes(canonical)
    requirements = tuple(
        line.strip()
        for line in canonical.decode("utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    )
    if digest != REVIEWED_DEPENDENCY_POLICY_SHA256:
        raise ArtifactVerificationError("dependency policy source hash differs")
    if requirements != REVIEWED_DEPENDENCY_POLICY_REQUIREMENTS:
        raise ArtifactVerificationError("dependency policy requirements differ")
    if type(record) is not dict:
        raise ArtifactVerificationError("dependency policy record is not an exact dictionary")
    expected_keys = {
        "authority",
        "path",
        "hash_domain",
        "sha256",
        "declared_requirements",
        "live_python_version_in_acceptance_bytes",
        "live_typer_version_in_acceptance_bytes",
    }
    if any(type(key) is not str for key in record) or set(record) != expected_keys:
        raise ArtifactVerificationError("dependency policy record keys differ from reviewed schema")
    for key in ("authority", "path", "hash_domain", "sha256"):
        if type(record[key]) is not str:
            raise ArtifactVerificationError(f"dependency policy field {key} has the wrong type")
    if record["authority"] != "deterministic_source_bound_dependency_declaration":
        raise ArtifactVerificationError("dependency policy authority differs")
    if record["path"] != REVIEWED_DEPENDENCY_POLICY_PATH:
        raise ArtifactVerificationError("dependency policy record path differs")
    if record["hash_domain"] != SOURCE_HASH_DOMAIN or record["sha256"] != digest:
        raise ArtifactVerificationError("dependency policy record hash differs")
    declared = record["declared_requirements"]
    if type(declared) is not list or any(type(item) is not str for item in declared):
        raise ArtifactVerificationError("dependency policy requirements have the wrong type")
    if tuple(declared) != REVIEWED_DEPENDENCY_POLICY_REQUIREMENTS:
        raise ArtifactVerificationError("dependency policy record requirements differ")
    for key in (
        "live_python_version_in_acceptance_bytes",
        "live_typer_version_in_acceptance_bytes",
    ):
        if type(record[key]) is not bool or record[key] is not False:
            raise ArtifactVerificationError(f"dependency policy field {key} is not exact false")
    if sha256_bytes(strict_json_bytes(record)) != REVIEWED_DEPENDENCY_POLICY_RECORD_SHA256:
        raise ArtifactVerificationError("dependency policy record digest differs")


_CLEAN_IMPORT_SCRIPT = r"""
import json
import pathlib
import sys

root = pathlib.Path.cwd().resolve()
import experiments.loop_flux_counting_curvature_proof.run  # noqa: E402,F401

paths = set()
for module in tuple(sys.modules.values()):
    source = getattr(module, "__file__", None)
    if not source:
        continue
    try:
        resolved = pathlib.Path(source).resolve()
        relative = resolved.relative_to(root)
    except (OSError, ValueError):
        continue
    if resolved.suffix == ".py" and ".venv" not in relative.parts:
        paths.add(relative.as_posix())
print(json.dumps(sorted(paths), separators=(",", ":")))
"""


def _discover_clean_cli_local_module_paths() -> tuple[str, ...]:
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    completed = subprocess.run(
        [sys.executable, "-c", _CLEAN_IMPORT_SCRIPT],
        cwd=SIM_ROOT,
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
        env=environment,
    )
    parsed = json.loads(completed.stdout.strip())
    if type(parsed) is not list or not all(type(item) is str for item in parsed):
        raise ArtifactVerificationError("clean CLI local-module inventory is malformed")
    actual = tuple(parsed)
    if actual != tuple(sorted(set(actual))):
        raise ArtifactVerificationError("clean CLI local-module inventory is not canonical")
    return actual


def clean_cli_local_module_paths() -> tuple[str, ...]:
    actual = _discover_clean_cli_local_module_paths()
    if actual != REVIEWED_CLEAN_CLI_LOCAL_MODULE_PATHS:
        raise ArtifactVerificationError("clean CLI module path set differs")
    if sha256_bytes(strict_json_bytes(actual)) != REVIEWED_CLEAN_CLI_PATH_SET_SHA256:
        raise ArtifactVerificationError("clean CLI module path-set fingerprint differs")
    return actual


def material_source_paths() -> tuple[str, ...]:
    modules = clean_cli_local_module_paths()
    package = tuple(path.relative_to(SIM_ROOT).as_posix() for path in sorted(EXPERIMENT_DIR.glob("*.py")))
    extra = (
        "experiments/loop_flux_counting_curvature_proof/MODEL_CONTRACT.md",
        "experiments/response_theorem_proof_program/THEOREM.md",
        "tests/experiments/test_loop_flux_counting_curvature_proof.py",
    )
    actual = tuple(sorted(set(modules) | set(package) | set(extra)))
    if actual != REVIEWED_MATERIAL_SOURCE_PATHS:
        raise ArtifactVerificationError("material source path set differs")
    if sha256_bytes(strict_json_bytes(actual)) != REVIEWED_MATERIAL_SOURCE_PATH_SET_SHA256:
        raise ArtifactVerificationError("material source path-set fingerprint differs")
    return actual


def _exact_json_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if type(key) is not str or key in result:
            raise ArtifactVerificationError("source-authority subprocess output has duplicate keys")
        result[key] = value
    return result


@dataclass(frozen=True)
class _ArtifactGitBinding:
    git_dir: Path
    index_file: Path
    work_tree: Path
    explicit: bool


@dataclass(frozen=True)
class _VerifiedSourceAuthority:
    record: dict[str, object]
    raw_sha256: str
    bundle_sha256: str
    source_hashes: dict[str, dict[str, object]]


def _canonical_lock_json_bytes(payload: object) -> bytes:
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


def _ordinary_absolute_path(path: Path, *, kind: str, label: str) -> Path:
    if not path.is_absolute():
        raise ArtifactVerificationError(f"{label} is not absolute")
    checked = _assert_no_reparse_from_volume_root(path, label=label, require_leaf=True)
    if kind == "directory" and not checked.is_dir():
        raise ArtifactVerificationError(f"{label} is not an ordinary directory")
    if kind == "file" and not checked.is_file():
        raise ArtifactVerificationError(f"{label} is not an ordinary file")
    return checked


def _checked_subprocess_run(*arguments, **keywords):
    if subprocess.run is not _REVIEWED_SUBPROCESS_RUN:
        raise ArtifactVerificationError("subprocess runner identity differs")
    return _REVIEWED_SUBPROCESS_RUN(*arguments, **keywords)


def _git_environment(binding: _ArtifactGitBinding | None = None) -> dict[str, str]:
    environment = {key: value for key, value in os.environ.items() if not key.upper().startswith("GIT_")}
    environment["GIT_OPTIONAL_LOCKS"] = "0"
    environment[_GIT_EXECUTABLE_ENV] = _REVIEWED_GIT_EXECUTABLE
    if binding is not None:
        environment.update(
            {
                "GIT_DIR": str(binding.git_dir),
                "GIT_INDEX_FILE": str(binding.index_file),
                "GIT_WORK_TREE": str(binding.work_tree),
            }
        )
    return environment


def _run_authority_git(
    arguments: Sequence[str],
    *,
    binding: _ArtifactGitBinding | None = None,
) -> bytes:
    work_tree = binding.work_tree if binding is not None else REPO_ROOT
    try:
        completed = _checked_subprocess_run(
            [
                _REVIEWED_GIT_EXECUTABLE,
                "--no-replace-objects",
                "-c",
                f"safe.directory={work_tree}",
                *arguments,
            ],
            cwd=work_tree,
            env=_git_environment(binding),
            check=True,
            capture_output=True,
            timeout=30,
        )
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise ArtifactVerificationError("Git-index bootstrap authority is unavailable") from exc
    return completed.stdout


def _git_output_path(raw: bytes, *, label: str) -> Path:
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


def _resolve_artifact_git_binding() -> _ArtifactGitBinding:
    names = ("GIT_DIR", "GIT_INDEX_FILE", "GIT_WORK_TREE")
    values = tuple(os.environ.get(name) for name in names)
    if any(value is not None for value in values):
        if not all(type(value) is str and value for value in values):
            raise ArtifactVerificationError("explicit Git-index binding is incomplete")
        return _ArtifactGitBinding(
            _ordinary_absolute_path(Path(values[0]), kind="directory", label="Git directory"),
            _ordinary_absolute_path(Path(values[1]), kind="file", label="Git index"),
            _ordinary_absolute_path(Path(values[2]), kind="directory", label="Git worktree"),
            True,
        )

    top = _ordinary_absolute_path(
        _git_output_path(
            _run_authority_git(["-C", str(REPO_ROOT), "rev-parse", "--show-toplevel"]),
            label="Git worktree",
        ),
        kind="directory",
        label="Git worktree",
    )
    if top != _ordinary_absolute_path(REPO_ROOT, kind="directory", label="repository root"):
        raise ArtifactVerificationError("repository Git worktree differs")
    git_dir = _ordinary_absolute_path(
        _git_output_path(
            _run_authority_git(["-C", str(REPO_ROOT), "rev-parse", "--absolute-git-dir"]),
            label="Git directory",
        ),
        kind="directory",
        label="Git directory",
    )
    index_file = _ordinary_absolute_path(
        _git_output_path(
            _run_authority_git(["-C", str(REPO_ROOT), "rev-parse", "--git-path", "index"]),
            label="Git index",
        ),
        kind="file",
        label="Git index",
    )
    return _ArtifactGitBinding(git_dir, index_file, top, False)


def _source_lock_file(binding: _ArtifactGitBinding) -> Path:
    override = os.environ.get("CWT_CGT_SOURCE_LOCK_FILE")
    if override is None:
        path = binding.work_tree.joinpath(*PurePosixPath(SOURCE_LOCK_RELATIVE_PATH).parts)
    else:
        if not binding.explicit or type(override) is not str or not override:
            raise ArtifactVerificationError("source lock override requires explicit Git-index binding")
        path = Path(override)
        if not path.is_absolute():
            raise ArtifactVerificationError("source lock override is not absolute")
    return _ordinary_absolute_path(path, kind="file", label="source lock")


def _parse_parent_source_lock(raw: bytes) -> _VerifiedSourceAuthority:
    if raw.startswith(b"\xef\xbb\xbf") or b"\r" in raw:
        raise ArtifactVerificationError("source lock is not strict UTF-8/LF")
    try:
        record = json.loads(raw.decode("utf-8"), object_pairs_hook=_exact_json_object)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ArtifactVerificationError("source lock is unreadable") from exc
    if raw != _canonical_lock_json_bytes(record) or type(record) is not dict:
        raise ArtifactVerificationError("source lock bytes are noncanonical")
    if tuple(record) != (
        "entries",
        "entries_sha256",
        "git_object_format",
        "parent_commit_oid",
        "path_set_sha256",
        "schema",
    ):
        raise ArtifactVerificationError("source lock top-level schema differs")
    if (
        type(record["schema"]) is not str
        or record["schema"] != _REVIEWED_SOURCE_LOCK_SCHEMA
        or type(record["parent_commit_oid"]) is not str
        or record["parent_commit_oid"] != _REVIEWED_SOURCE_LOCK_PARENT
        or type(record["git_object_format"]) is not str
        or record["git_object_format"] != _REVIEWED_SOURCE_LOCK_OBJECT_FORMAT
        or not _is_sha256(record["path_set_sha256"])
        or record["path_set_sha256"] != _REVIEWED_SOURCE_LOCK_PATH_SET_SHA256
        or not _is_sha256(record["entries_sha256"])
    ):
        raise ArtifactVerificationError("source lock identity fields differ")
    entries = record["entries"]
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
        paths.append(path)
        if (
            type(entry["mode"]) is not str
            or entry["mode"] != "100644"
            or type(entry["blob_oid"]) is not str
            or len(entry["blob_oid"]) != 40
            or any(character not in "0123456789abcdef" for character in entry["blob_oid"])
            or type(entry["size"]) is not int
            or type(entry["size"]) is bool
            or entry["size"] < 0
            or not _is_sha256(entry["sha256_raw"])
        ):
            raise ArtifactVerificationError(f"source lock entry identity differs: {path}")
    if tuple(paths) != _REVIEWED_SOURCE_LOCK_REPO_PATHS or len(set(paths)) != len(paths):
        raise ArtifactVerificationError("source lock path set/order differs")
    if record["path_set_sha256"] != sha256_bytes(_canonical_lock_json_bytes(paths)):
        raise ArtifactVerificationError("source lock path-set digest differs")
    if record["entries_sha256"] != sha256_bytes(_canonical_lock_json_bytes(entries)):
        raise ArtifactVerificationError("source lock entries digest differs")
    bundle_record = {
        "schema": record["schema"],
        "parent_commit_oid": record["parent_commit_oid"],
        "git_object_format": record["git_object_format"],
        "path_set_sha256": record["path_set_sha256"],
        "entries_sha256": record["entries_sha256"],
    }
    source_hashes = {
        entry["path"]: {
            "type": "file",
            "hash_domain": SOURCE_BLOB_HASH_DOMAIN,
            "mode": entry["mode"],
            "blob_oid": entry["blob_oid"],
            "size": entry["size"],
            "sha256": entry["sha256_raw"],
        }
        for entry in entries
    }
    return _VerifiedSourceAuthority(
        record=record,
        raw_sha256=sha256_bytes(raw),
        bundle_sha256=sha256_bytes(_canonical_lock_json_bytes(bundle_record)),
        source_hashes=source_hashes,
    )


def _verify_bootstrap_index_entries(binding: _ArtifactGitBinding) -> None:
    output = _run_authority_git(
        ["ls-files", "--stage", "-z", "--", *_SOURCE_AUTHORITY_BOOTSTRAP_PATHS],
        binding=binding,
    )
    observed: list[str] = []
    for raw_record in output.split(b"\0"):
        if not raw_record:
            continue
        try:
            metadata, raw_path = raw_record.split(b"\t", 1)
            mode, _oid, stage = metadata.decode("ascii").split(" ", 2)
            path = raw_path.decode("utf-8")
        except (ValueError, UnicodeError) as exc:
            raise ArtifactVerificationError("bootstrap Git index entry is malformed") from exc
        if mode != "100644" or stage != "0":
            raise ArtifactVerificationError("bootstrap Git index entry mode/stage differs")
        observed.append(_canonical_repo_path(path))
    if tuple(observed) != _SOURCE_AUTHORITY_BOOTSTRAP_PATHS:
        raise ArtifactVerificationError("bootstrap Git index path set/order differs")


def _checkout_index_verifier(binding: _ArtifactGitBinding, root: Path) -> Path:
    checked_root = _ordinary_absolute_path(root, kind="directory", label="verifier checkout root")
    if checked_root == REPO_ROOT or checked_root.is_relative_to(REPO_ROOT):
        raise ArtifactVerificationError("verifier checkout is not external to the repository")
    if (checked_root / ".git").exists():
        raise ArtifactVerificationError("verifier checkout unexpectedly contains Git metadata")
    _verify_bootstrap_index_entries(binding)
    _run_authority_git(
        [
            "checkout-index",
            "--force",
            f"--prefix={checked_root.as_posix()}/",
            "--",
            *_SOURCE_AUTHORITY_BOOTSTRAP_PATHS,
        ],
        binding=binding,
    )
    actual: list[str] = []
    for path in sorted(checked_root.rglob("*")):
        if path.is_file() or path.is_symlink():
            checked = _assert_no_reparse_from_volume_root(
                path,
                label="index verifier source",
                require_leaf=True,
            )
            if not checked.is_file():
                raise ArtifactVerificationError("index verifier source is not an ordinary file")
            raw = checked.read_bytes()
            if raw != canonical_source_text_bytes(raw):
                raise ArtifactVerificationError("index verifier source is not strict UTF-8/LF")
            actual.append(checked.relative_to(checked_root).as_posix())
    if tuple(actual) != _SOURCE_AUTHORITY_BOOTSTRAP_PATHS:
        raise ArtifactVerificationError("index verifier checkout path set differs")
    source_lock_path = checked_root.joinpath(
        *PurePosixPath("cwt-sim/experiments/loop_flux_counting_curvature_proof/source_lock.py").parts
    )
    return _ordinary_absolute_path(source_lock_path, kind="file", label="index source-lock verifier")


def _parse_source_authority_output(raw: bytes) -> dict[str, object]:
    if raw.startswith(b"\xef\xbb\xbf") or b"\r" in raw:
        raise ArtifactVerificationError("source-authority subprocess output is noncanonical")
    try:
        payload = json.loads(raw.decode("utf-8"), object_pairs_hook=_exact_json_object)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ArtifactVerificationError("source-authority subprocess output is unreadable") from exc
    if (
        raw != _canonical_lock_json_bytes(payload)
        or type(payload) is not dict
        or tuple(payload)
        != (
            "bundle_sha256",
            "raw_sha256",
            "record",
            "source_hashes",
        )
    ):
        raise ArtifactVerificationError("source-authority subprocess schema differs")
    return payload


def _verified_source_lock() -> _VerifiedSourceAuthority:
    """Run a defense-in-depth in-process precheck with index-extracted code.

    Publication authority belongs to the outer staged audit and fresh CLI
    process.  This helper intentionally makes no claim after arbitrary current-
    process memory, syscall-wrapper, interpreter, binary, or admin compromise.
    """

    binding = _resolve_artifact_git_binding()
    lock_path = _source_lock_file(binding)
    parent_authority = _parse_parent_source_lock(lock_path.read_bytes())
    expected_payload = {
        "bundle_sha256": parent_authority.bundle_sha256,
        "raw_sha256": parent_authority.raw_sha256,
        "record": parent_authority.record,
        "source_hashes": parent_authority.source_hashes,
    }
    if sys.executable != _REVIEWED_PYTHON_EXECUTABLE:
        raise ArtifactVerificationError("Python executable identity differs")
    with tempfile.TemporaryDirectory(prefix="cwt-loop-flux-index-verifier-") as temporary:
        verifier = _checkout_index_verifier(binding, Path(temporary).absolute())
        environment = _git_environment(binding)
        environment.update(
            {
                "CWT_CGT_SOURCE_LOCK_FILE": str(lock_path),
                "PYTHONDONTWRITEBYTECODE": "1",
                "PYTHONNOUSERSITE": "1",
            }
        )
        try:
            completed = _checked_subprocess_run(
                [_REVIEWED_PYTHON_EXECUTABLE, "-I", str(verifier), "verify-json"],
                cwd=verifier.parents[3],
                env=environment,
                check=True,
                capture_output=True,
                timeout=60,
            )
        except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
            raise ArtifactVerificationError("clean Git-index source authority refused") from exc
        observed_payload = _parse_source_authority_output(completed.stdout)
    if observed_payload != expected_payload:
        raise ArtifactVerificationError("index verifier and parent source authority differ")
    return parent_authority


def source_hashes(paths: Sequence[str]) -> dict[str, dict[str, object]]:
    if type(paths) not in {tuple, list} or tuple(paths) != REVIEWED_MATERIAL_SOURCE_PATHS:
        raise ArtifactVerificationError("source paths differ from reviewed material closure")
    authority = _verified_source_lock()
    if tuple(authority.source_hashes) != _REVIEWED_SOURCE_LOCK_REPO_PATHS:
        raise ArtifactVerificationError("source lock hash path set/order differs")
    return authority.source_hashes


def _source_lock_provenance(authority: _VerifiedSourceAuthority) -> dict[str, object]:
    record = authority.record
    return {
        "path": SOURCE_LOCK_RELATIVE_PATH,
        "hash_domain": SOURCE_LOCK_HASH_DOMAIN,
        "sha256_raw": authority.raw_sha256,
        "bundle_sha256": authority.bundle_sha256,
        "schema": record["schema"],
        "parent_commit_oid": record["parent_commit_oid"],
        "git_object_format": record["git_object_format"],
        "path_set_sha256": record["path_set_sha256"],
        "entries_sha256": record["entries_sha256"],
    }


def _is_sha256(value: object) -> bool:
    return (
        type(value) is str
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _validate_predecessor_inventory_record(name: str, record: object) -> dict[str, object]:
    if type(record) is not dict or tuple(record) != (
        "closure",
        "entry_count",
        "entries",
        "inventory_sha256",
    ):
        raise ArtifactVerificationError(f"predecessor inventory schema differs: {name}")
    if (
        type(record["closure"]) is not str
        or record["closure"] != "recursive_path_and_type_bound_no_symlink_or_reparse"
        or type(record["entry_count"]) is not int
        or type(record["entries"]) is not dict
        or not _is_sha256(record["inventory_sha256"])
    ):
        raise ArtifactVerificationError(f"predecessor inventory identity differs: {name}")
    entries = record["entries"]
    for relative, entry in entries.items():
        if type(relative) is not str or _canonical_relative(relative).as_posix() != relative:
            raise ArtifactVerificationError(f"predecessor inventory path differs: {name}")
        if type(entry) is not dict or type(entry.get("type")) is not str:
            raise ArtifactVerificationError(f"predecessor inventory entry schema differs: {name}")
        if entry["type"] == "directory":
            if tuple(entry) != ("type",):
                raise ArtifactVerificationError(f"predecessor directory identity fields differ: {name}")
        elif entry["type"] == "file":
            if (
                tuple(entry) != ("type", "hash_domain", "sha256")
                or type(entry["hash_domain"]) is not str
                or entry["hash_domain"] != RAW_HASH_DOMAIN
                or not _is_sha256(entry["sha256"])
            ):
                raise ArtifactVerificationError(f"predecessor file identity differs: {name}")
        else:
            raise ArtifactVerificationError(f"predecessor entry type differs: {name}")
    if record["entry_count"] != len(entries):
        raise ArtifactVerificationError(f"predecessor inventory count differs: {name}")
    if record["inventory_sha256"] != sha256_bytes(strict_json_bytes(entries)):
        raise ArtifactVerificationError(f"predecessor inventory content digest differs: {name}")
    return record


def predecessor_inventories() -> dict[str, dict[str, object]]:
    roles = tuple(
        (name, path.relative_to(SIM_ROOT).as_posix())
        for name, path in sorted(PREDECESSOR_ARTIFACT_DIRS.items())
    )
    if roles != REVIEWED_PREDECESSOR_ROLE_PATHS:
        raise ArtifactVerificationError("predecessor role/path set differs")
    if sha256_bytes(strict_json_bytes(roles)) != REVIEWED_PREDECESSOR_ROLE_PATHS_SHA256:
        raise ArtifactVerificationError("predecessor role/path fingerprint differs")
    observed = {
        name: recursive_raw_inventory(path, trust_anchor=SIM_ROOT)
        for name, path in sorted(PREDECESSOR_ARTIFACT_DIRS.items())
    }
    for name, record in observed.items():
        _validate_predecessor_inventory_record(name, record)
    digests = {
        name: {
            "entry_count": record["entry_count"],
            "inventory_sha256": record["inventory_sha256"],
        }
        for name, record in observed.items()
    }
    if type(REVIEWED_PREDECESSOR_INVENTORY_DIGESTS) is not dict or tuple(
        REVIEWED_PREDECESSOR_INVENTORY_DIGESTS
    ) != tuple(name for name, _ in REVIEWED_PREDECESSOR_ROLE_PATHS):
        raise ArtifactVerificationError("reviewed predecessor role/order differs")
    for name, reviewed in REVIEWED_PREDECESSOR_INVENTORY_DIGESTS.items():
        if (
            type(name) is not str
            or type(reviewed) is not dict
            or tuple(reviewed) != ("entry_count", "inventory_sha256")
            or type(reviewed["entry_count"]) is not int
            or not _is_sha256(reviewed["inventory_sha256"])
        ):
            raise ArtifactVerificationError(f"reviewed predecessor identity differs: {name}")
    if digests != REVIEWED_PREDECESSOR_INVENTORY_DIGESTS:
        raise ArtifactVerificationError("predecessor recursive inventory digest differs")
    if sha256_bytes(strict_json_bytes(digests)) != REVIEWED_PREDECESSOR_INVENTORY_DIGESTS_SHA256:
        raise ArtifactVerificationError("predecessor inventory aggregate differs")
    return observed


def render_report(summary: Mapping[str, Any], records: Mapping[str, Any]) -> str:
    require_semantic_pass(summary, records)
    omega = records["geometry"]["mean_Uhlmann_vector"]
    response = records["counting"]["response_curvature"]
    lines = [
        "# One-Chord Loop-Flux Counting-Curvature Proof",
        "",
        f"- Status: `{summary['disposition']}`",
        f"- Evidence: `{summary['evidence_status']}`",
        f"- Scope: `{summary['relation_scope']}`",
        f"- Classification: `{summary['classification']}`",
        "",
        "## Exact result",
        "",
        f"- Mean-Uhlmann `(dt,tb,bd)`: `{[str(item) for item in omega]}`",
        f"- Counted response `(dt,tb,bd)`: `{[str(item) for item in response]}`",
        "- Both are nonzero. Exact sign noncollinearity refutes SAME_CURVATURE and finite scalar kappa.",
        "- General linear, affine, nonlinear, and generator-dependent maps remain open; "
        "this center is not held out.",
        "",
        "## Ceiling",
        "",
        summary["claim_ceiling"],
        "",
        "No finite-time pumping, physical-clock calibration, empirical evidence, or "
        "universal/full-CWT alignment is claimed.",
        "",
        "## Provenance authority",
        "",
        "Publication acceptance requires an outer staged-index audit and fresh `python -I` CLI "
        "verification from an exact index-materialized checkout with explicit absolute Git bindings. "
        "In-process checks are defense-in-depth diagnostics, not authority after arbitrary process or "
        "binary compromise.",
        "",
    ]
    return "\n".join(lines)


def require_semantic_pass(summary: object, records: object) -> None:
    require_theorem_semantic_pass(summary, records)


def expected_artifact_bytes() -> dict[str, bytes]:
    summary, records = execute_program()
    require_semantic_pass(summary, records)
    material_source_paths()
    source_authority = _verified_source_lock()
    if tuple(source_authority.source_hashes) != _REVIEWED_SOURCE_LOCK_REPO_PATHS:
        raise ArtifactVerificationError("source lock hash path set/order differs")
    predecessors = predecessor_inventories()
    dependency_policy = dependency_policy_record()
    validate_dependency_policy_record(dependency_policy)
    provenance = {
        "schema_version": 1,
        "experiment_id": MODEL_CONTRACT.experiment_id,
        "claim_ceiling": MODEL_CONTRACT.claim_ceiling,
        "dependency_policy": dependency_policy,
        "reviewed_registry_sha256": REVIEWED_REGISTRY_SHA256,
        "reviewed_record_digests": dict(REVIEWED_RECORD_DIGESTS),
        "reviewed_record_aggregate_sha256": REVIEWED_RECORD_AGGREGATE_SHA256,
        "source_hash_domain": SOURCE_BLOB_HASH_DOMAIN,
        "source_paths": _REVIEWED_SOURCE_LOCK_REPO_PATHS,
        "source_hashes": source_authority.source_hashes,
        "source_lock": _source_lock_provenance(source_authority),
        "provenance_acceptance_boundary": records["scope"]["provenance_authority"],
        "predecessor_artifacts": predecessors,
        "reviewed_predecessor_inventory_digests": REVIEWED_PREDECESSOR_INVENTORY_DIGESTS,
        "reviewed_predecessor_inventory_digests_sha256": (REVIEWED_PREDECESSOR_INVENTORY_DIGESTS_SHA256),
        "runtime_versions_in_acceptance": False,
        "transaction_auxiliaries_committed": False,
    }
    payloads = {
        "summary.json": strict_json_bytes(summary),
        "records.json": strict_json_bytes(records),
        "PROVENANCE.json": strict_json_bytes(provenance),
        "REPORT.md": render_report(summary, records).encode("utf-8"),
    }
    checksums = {
        "schema_version": 1,
        "hash_domain": RAW_HASH_DOMAIN,
        "files": {name: sha256_bytes(payload) for name, payload in sorted(payloads.items())},
    }
    payloads["CHECKSUMS.json"] = strict_json_bytes(checksums)
    return {name: payloads[name] for name in sorted(payloads)}


def write_artifacts(
    output_dir: Path = ARTIFACTS_DIR,
    *,
    fault_injector=None,
) -> dict[str, Path]:
    preflight_artifact_destination(output_dir)
    before = predecessor_inventories()
    expected = expected_artifact_bytes()
    if predecessor_inventories() != before:
        raise ArtifactGenerationRefused("predecessor artifacts changed before publication")

    def publication_check(checkpoint: str) -> None:
        if checkpoint == "after_target_verify" and predecessor_inventories() != before:
            raise ArtifactVerificationError("predecessor artifacts changed during publication")
        if fault_injector is not None:
            fault_injector(checkpoint)

    _publish_artifact_mapping(output_dir, expected, fault_injector=publication_check)
    verify_artifacts(output_dir)
    return {name: output_dir / name for name in sorted(expected)}


def verify_artifacts(output_dir: Path = ARTIFACTS_DIR) -> dict[str, object]:
    with artifact_access_guard(output_dir):
        if not output_dir.is_dir() or output_dir.is_symlink():
            raise ArtifactVerificationError("artifact directory is missing or nonordinary")
        actual_names = {path.name for path in output_dir.iterdir()}
        if actual_names != EXPECTED_ARTIFACT_NAMES:
            raise ArtifactVerificationError("artifact file set differs")
        for name in sorted(actual_names):
            _checked_path(
                output_dir / name,
                output_dir,
                expected_kind="file",
                label=f"artifact file {name}",
            )
        try:
            disk_provenance = json.loads((output_dir / "PROVENANCE.json").read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ArtifactVerificationError("artifact provenance is unreadable") from exc
        if type(disk_provenance) is not dict or "dependency_policy" not in disk_provenance:
            raise ArtifactVerificationError("artifact dependency policy is missing")
        validate_dependency_policy_record(disk_provenance["dependency_policy"])
        source_authority = _verified_source_lock()
        if disk_provenance.get("source_lock") != _source_lock_provenance(source_authority):
            raise ArtifactVerificationError("artifact source-lock provenance differs")
        if disk_provenance.get("source_hashes") != source_authority.source_hashes:
            raise ArtifactVerificationError("artifact source-lock entries differ")
        expected = expected_artifact_bytes()
        for name, payload in expected.items():
            if (output_dir / name).read_bytes() != payload:
                raise ArtifactVerificationError(f"artifact content mismatch: {name}")
        paths = artifact_transaction_paths(output_dir)
        auxiliaries = [paths.journal, paths.journal_temp, paths.stage, paths.backup]
        if any(path.exists() for path in auxiliaries):
            raise ArtifactVerificationError("transaction auxiliaries remain")
        summary = json.loads((output_dir / "summary.json").read_text(encoding="utf-8"))
        return {
            "status": summary["disposition"],
            "files": len(EXPECTED_ARTIFACT_NAMES),
            "sources": len(REVIEWED_MATERIAL_SOURCE_PATHS),
            "predecessors": len(PREDECESSOR_ARTIFACT_DIRS),
            "record_digests": len(REVIEWED_RECORD_DIGESTS),
        }


__all__ = [
    "ARTIFACTS_DIR",
    "ArtifactGenerationRefused",
    "ArtifactTransactionCrash",
    "ArtifactVerificationError",
    "expected_artifact_bytes",
    "require_semantic_pass",
    "verify_artifacts",
    "write_artifacts",
]
