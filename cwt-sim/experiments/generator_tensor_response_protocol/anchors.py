"""Source-inspection-only anchor validation; never imports response producers."""

from __future__ import annotations

import ast
import builtins
import dis
import hashlib
import inspect
import json
import stat
import sys
import threading
from importlib.machinery import ModuleSpec, SourceFileLoader
from pathlib import Path, PurePosixPath
from types import CodeType, FunctionType, ModuleType

from .contract import (
    PREDICTOR_METADATA_COMMIT_OID,
    PREDICTOR_METADATA_LOCK_SHA256,
    PREDICTOR_SOURCE_COMMIT_OID,
    PREDICTOR_SOURCE_TREE_OID,
    PRODUCER_CALLABLES,
    PRODUCER_SOURCE_LOCK_SHA256,
)
from .exact import canonical_sha256, strict_equal

PACKAGE_DIR = Path(__file__).resolve().parent
SIM_ROOT = PACKAGE_DIR.parents[1]
PREDICTOR_LOCK_PATH = SIM_ROOT / "experiments/generator_tensor_prediction_protocol.SOURCE_LOCK.json"
PRODUCER_PACKAGE = SIM_ROOT / "experiments/loop_flux_counting_curvature_proof"
PRODUCER_LOCK_PATH = PRODUCER_PACKAGE / "SOURCE_LOCK.json"

_PREDICTOR_LOCK_KEYS = {
    "entries",
    "entries_sha256",
    "git_object_format",
    "parent_commit_oid",
    "path_set_sha256",
    "schema",
    "source_bundle_sha256",
    "source_commit_oid",
    "source_tree_oid",
}
_PRODUCER_LOCK_KEYS = {
    "entries",
    "entries_sha256",
    "git_object_format",
    "parent_commit_oid",
    "path_set_sha256",
    "schema",
}
_ENTRY_KEYS = {"blob_oid", "mode", "path", "sha256_raw", "size"}
REVIEWED_ANCHOR_PAYLOAD_SHA256 = "f0c0cc9febde7fba10dab937855833cc90505141b9d75738d56626e0a9af2e3d"
_CALLABLE_RECORD_KEYS = {
    "blob_oid",
    "canonical_ast_sha256",
    "module",
    "qualname",
    "sha256_raw",
    "signature",
    "source_span_sha256",
    "transitive_call_graph_sha256",
}
_RUNTIME_MODULE_SNAPSHOTS: dict[str, tuple[tuple[str, int], ...]] = {}
_RUNTIME_SNAPSHOT_LOCK = threading.RLock()


def _has_reparse_attribute(path: Path) -> bool:
    if sys.platform != "win32":
        return path.is_symlink()
    return bool(path.lstat().st_file_attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT)


def _read_reviewed_file(path: Path) -> bytes:
    lexical = path.absolute()
    if SIM_ROOT not in lexical.parents or lexical == SIM_ROOT:
        raise RuntimeError("reviewed source path escaped SIM_ROOT")
    relative = lexical.relative_to(SIM_ROOT)
    cursor = SIM_ROOT
    for part in relative.parts:
        cursor = cursor / part
        if cursor.is_symlink() or _has_reparse_attribute(cursor):
            raise RuntimeError("reviewed source path contains a link/reparse point")
    if not path.is_file() or path.resolve(strict=True) != lexical:
        raise RuntimeError("reviewed source path is not an ordinary canonical file")
    with path.open("rb") as stream:
        return stream.read()


def _parse_lock(raw: bytes, *, expected_keys: set[str]) -> dict[str, object]:
    if raw.startswith(b"\xef\xbb\xbf") or b"\r" in raw or not raw.endswith(b"\n"):
        raise RuntimeError("source lock encoding refused")
    try:
        record = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError("source lock JSON refused") from exc
    if type(record) is not dict or set(record) != expected_keys:
        raise RuntimeError("source lock schema refused")
    entries = record["entries"]
    if type(entries) is not list or not entries:
        raise RuntimeError("source lock entries refused")
    for entry in entries:
        if (
            type(entry) is not dict
            or set(entry) != _ENTRY_KEYS
            or any(type(entry[key]) is not str for key in _ENTRY_KEYS - {"size"})
            or type(entry["size"]) is not int
            or type(entry["size"]) is bool
        ):
            raise RuntimeError("source lock entry schema refused")
    canonical = (
        json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False) + "\n"
    ).encode("utf-8")
    if canonical != raw:
        raise RuntimeError("source lock is not canonical JSON")
    return record


def _entry_by_path(record: dict[str, object], relative: str) -> dict[str, object]:
    matches = [entry for entry in record["entries"] if entry["path"] == relative]  # type: ignore[index]
    if len(matches) != 1:
        raise RuntimeError(f"source lock path binding refused: {relative}")
    return matches[0]


def _verify_locked_worktree(record: dict[str, object], *, label: str) -> None:
    """Bind every locked dependency entry to the current ordinary worktree bytes."""

    entries = record["entries"]
    if type(entries) is not list:
        raise RuntimeError(f"{label} lock entries refused")
    paths = tuple(entry["path"] for entry in entries)
    if len(set(paths)) != len(paths) or paths != tuple(sorted(paths)):
        raise RuntimeError(f"{label} lock path order refused")
    for entry in entries:
        relative = entry["path"]
        parsed = PurePosixPath(relative)
        if (
            type(relative) is not str
            or not relative.startswith("cwt-sim/")
            or parsed.as_posix() != relative
            or parsed.is_absolute()
            or "." in parsed.parts
            or ".." in parsed.parts
            or "\\" in relative
        ):
            raise RuntimeError(f"{label} lock path refused")
        raw = _read_reviewed_file(SIM_ROOT.joinpath(*parsed.parts[1:]))
        if (
            entry["mode"] != "100644"
            or len(entry["blob_oid"]) != 40
            or any(character not in "0123456789abcdef" for character in entry["blob_oid"])
            or len(entry["sha256_raw"]) != 64
            or any(character not in "0123456789abcdef" for character in entry["sha256_raw"])
            or entry["size"] != len(raw)
            or entry["sha256_raw"] != hashlib.sha256(raw).hexdigest()
            or raw.startswith(b"\xef\xbb\xbf")
            or b"\r" in raw
            or not raw.endswith(b"\n")
        ):
            raise RuntimeError(f"{label} locked worktree bytes refused: {relative}")


def _signature_descriptor(source: str, name: str) -> str:
    tree = ast.parse(source)
    matches = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == name]
    if len(matches) != 1:
        raise RuntimeError(f"producer callable definition refused: {name}")
    node = matches[0]
    arguments = node.args
    if arguments.posonlyargs or arguments.vararg is not None or arguments.kwarg is not None:
        raise RuntimeError(f"producer callable signature form refused: {name}")
    positional = ",".join(item.arg for item in arguments.args)
    keyword = ",".join(
        f"{item.arg}={ast.unparse(default)}"
        for item, default in zip(arguments.kwonlyargs, arguments.kw_defaults, strict=True)
    )
    body = positional
    if arguments.kwonlyargs:
        body = f"{body},*" if body else "*"
        body = f"{body},{keyword}" if keyword else body
    return_annotation = ast.unparse(node.returns).replace(" ", "") if node.returns else "None"
    return f"({body})->{return_annotation}"


def _function_node(source: str, name: str) -> ast.FunctionDef:
    tree = ast.parse(source)
    matches = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == name]
    if len(matches) != 1:
        raise RuntimeError(f"producer callable definition refused: {name}")
    return matches[0]


def _dotted(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _dotted(node.value)
        return None if parent is None else f"{parent}.{node.attr}"
    return None


def _call_graph_record(source: str, name: str) -> tuple[tuple[str, tuple[str, ...]], ...]:
    tree = ast.parse(source)
    local = {
        node.name: node for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    if name not in local:
        raise RuntimeError(f"producer call graph root refused: {name}")
    pending = [name]
    seen: set[str] = set()
    records: list[tuple[str, tuple[str, ...]]] = []
    while pending:
        current = pending.pop()
        if current in seen:
            continue
        seen.add(current)
        calls = tuple(
            sorted(
                {
                    dotted
                    for node in ast.walk(local[current])
                    if isinstance(node, ast.Call)
                    for dotted in (_dotted(node.func),)
                    if dotted is not None
                }
            )
        )
        records.append((current, calls))
        pending.extend(call for call in calls if call in local and call not in seen)
    return tuple(sorted(records))


def _callable_source_record(source: str, name: str) -> dict[str, str]:
    node = _function_node(source, name)
    segment = ast.get_source_segment(source, node)
    if segment is None:
        raise RuntimeError(f"producer source span refused: {name}")
    return {
        "signature": _signature_descriptor(source, name),
        "source_span_sha256": hashlib.sha256(segment.encode("utf-8")).hexdigest(),
        "canonical_ast_sha256": hashlib.sha256(ast.unparse(node).encode("utf-8")).hexdigest(),
        "transitive_call_graph_sha256": canonical_sha256(_call_graph_record(source, name)),
    }


def _constant_record(value: object) -> object:
    if value is None or type(value) in {bool, int, str}:
        return value
    if type(value) is bytes:
        return {"bytes_hex": value.hex()}
    if type(value) is float:
        return {"float_hex": value.hex()}
    if type(value) is tuple:
        return tuple(_constant_record(item) for item in value)
    if isinstance(value, CodeType):
        return _code_record(value)
    return {"type": type(value).__name__, "repr": repr(value)}


def _code_record(code: CodeType) -> dict[str, object]:
    return {
        "name": code.co_name,
        "argcount": code.co_argcount,
        "posonlyargcount": code.co_posonlyargcount,
        "kwonlyargcount": code.co_kwonlyargcount,
        "flags": code.co_flags,
        "names": code.co_names,
        "varnames": code.co_varnames,
        "freevars": code.co_freevars,
        "cellvars": code.co_cellvars,
        "bytecode_hex": code.co_code.hex(),
        "constants": tuple(_constant_record(item) for item in code.co_consts),
    }


def _compiled_function_code(source: str, path: Path, name: str) -> CodeType:
    module_code = compile(source, str(path), "exec", dont_inherit=True)
    matches = [item for item in module_code.co_consts if isinstance(item, CodeType) and item.co_name == name]
    if len(matches) != 1:
        raise RuntimeError(f"compiled producer callable refused: {name}")
    return matches[0]


def _resolve_qualname(root: object, qualname: str) -> object:
    if type(qualname) is not str or not qualname or "<locals>" in qualname:
        raise RuntimeError("runtime producer qualname refused")
    current = root
    for part in qualname.split("."):
        if not part.isidentifier():
            raise RuntimeError("runtime producer qualname refused")
        namespace = current.__dict__ if type(current) in {ModuleType, type} else None
        if type(namespace) is not dict or part not in namespace:
            raise RuntimeError("runtime producer module attribute refused")
        current = namespace[part]
    return current


def _literal_default(node: ast.AST) -> object:
    try:
        value = ast.literal_eval(node)
    except (ValueError, TypeError, SyntaxError, MemoryError, RecursionError) as exc:
        raise RuntimeError("runtime producer nonliteral default refused") from exc
    if value is None or type(value) in {bool, int, float, str, bytes}:
        return value
    if type(value) is tuple:
        return tuple(_literal_default(ast.Constant(item)) for item in value)
    raise RuntimeError("runtime producer default type refused")


def _reviewed_function_metadata(source: str, name: str) -> dict[str, object]:
    node = _function_node(source, name)
    positional_defaults = tuple(_literal_default(item) for item in node.args.defaults)
    keyword_defaults = {
        argument.arg: _literal_default(default)
        for argument, default in zip(node.args.kwonlyargs, node.args.kw_defaults, strict=True)
        if default is not None
    }
    annotations: dict[str, object] = {}
    for argument in (*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs):
        if argument.annotation is not None:
            annotations[argument.arg] = ast.unparse(argument.annotation)
    if node.returns is not None:
        annotations["return"] = ast.unparse(node.returns)
    return {
        "defaults": positional_defaults or None,
        "kwdefaults": keyword_defaults or None,
        "annotations": annotations,
        "closure_absent": True,
    }


def _runtime_function_metadata(function: FunctionType) -> dict[str, object]:
    return {
        "defaults": function.__defaults__,
        "kwdefaults": function.__kwdefaults__,
        "annotations": function.__annotations__,
        "closure_absent": function.__closure__ is None,
    }


def _global_names(code: CodeType) -> tuple[str, ...]:
    return tuple(
        sorted(
            {
                instruction.argval
                for instruction in dis.get_instructions(code)
                if instruction.opname in {"LOAD_GLOBAL", "LOAD_NAME"} and type(instruction.argval) is str
            }
        )
    )


def _runtime_module_source(module: ModuleType) -> tuple[Path, bytes, str]:
    module_name = module.__name__
    source_path = SIM_ROOT / (module_name.replace(".", "/") + ".py")
    raw = _read_reviewed_file(source_path)
    source = raw.decode("utf-8")
    spec = module.__spec__
    origin = None if type(spec) is not ModuleSpec else spec.origin
    loader = None if type(spec) is not ModuleSpec else spec.loader
    if (
        type(spec) is not ModuleSpec
        or spec.name != module_name
        or type(origin) is not str
        or type(loader) is not SourceFileLoader
        or module.__loader__ is not loader
        or module.__name__ != module_name
        or module.__package__ != module_name.rpartition(".")[0]
        or type(module.__file__) is not str
        or Path(module.__file__).resolve(strict=True) != source_path.resolve(strict=True)
        or Path(loader.get_filename(module_name)).resolve(strict=True) != source_path.resolve(strict=True)
        or loader.get_source(module_name) != source
        or Path(origin).resolve(strict=True) != source_path.resolve(strict=True)
    ):
        raise RuntimeError("runtime producer module origin refused")
    return source_path, raw, source


def _require_producer_module_lock(module_name: str, raw: bytes) -> None:
    if not module_name.startswith("experiments.loop_flux_counting_curvature_proof."):
        raise RuntimeError("runtime producer helper module scope refused")
    relative = f"cwt-sim/{module_name.replace('.', '/')}.py"
    producer_raw = _read_reviewed_file(PRODUCER_LOCK_PATH)
    if hashlib.sha256(producer_raw).hexdigest() != PRODUCER_SOURCE_LOCK_SHA256:
        raise RuntimeError("producer source lock raw hash refused")
    producer = _parse_lock(producer_raw, expected_keys=_PRODUCER_LOCK_KEYS)
    entry = _entry_by_path(producer, relative)
    if (
        entry["mode"] != "100644"
        or entry["size"] != len(raw)
        or entry["sha256_raw"] != hashlib.sha256(raw).hexdigest()
    ):
        raise RuntimeError("runtime producer imported helper source refused")


def _validate_external_global_binding(
    value: object,
    *,
    visited: set[tuple[str, str]],
) -> None:
    if type(value) is FunctionType:
        module = sys.modules.get(value.__module__)
        if (
            type(module) is not ModuleType
            or value.__globals__ is not module.__dict__
            or _resolve_qualname(module, value.__qualname__) is not value
            or value.__closure__ is not None
        ):
            raise RuntimeError("runtime producer imported helper binding refused")
        if value.__module__.startswith("experiments.loop_flux_counting_curvature_proof."):
            source_path, raw, source = _runtime_module_source(module)
            _require_producer_module_lock(module.__name__, raw)
            _bind_module_snapshot(module)
            _validate_runtime_function(
                value,
                module=module,
                source=source,
                source_path=source_path,
                name=value.__qualname__,
                visited=visited,
            )
            _bind_module_snapshot(module)
    elif type(value) is type:
        module = sys.modules.get(value.__module__)
        if type(module) is not ModuleType or _resolve_qualname(module, value.__qualname__) is not value:
            raise RuntimeError("runtime producer imported class binding refused")
    elif type(value) is ModuleType and sys.modules.get(value.__name__) is not value:
        raise RuntimeError("runtime producer imported module binding refused")


def _validate_runtime_function(
    function: object,
    *,
    module: ModuleType,
    source: str,
    source_path: Path,
    name: str,
    visited: set[tuple[str, str]] | None = None,
) -> FunctionType:
    if visited is None:
        visited = set()
    identity = (module.__name__, name)
    if identity in visited:
        if type(function) is not FunctionType or function is not _resolve_qualname(module, name):
            raise RuntimeError("runtime producer recursive callable binding refused")
        return function
    visited.add(identity)
    if (
        type(function) is not FunctionType
        or function is not _resolve_qualname(module, name)
        or function.__globals__ is not module.__dict__
        or function.__module__ != module.__name__
        or function.__qualname__ != name
        or function.__name__ != name.rsplit(".", 1)[-1]
        or function.__closure__ is not None
        or function.__code__.co_freevars
    ):
        raise RuntimeError("runtime producer callable identity refused")
    compiled = _compiled_function_code(source, source_path, name)
    if not strict_equal(_code_record(function.__code__), _code_record(compiled)) or not strict_equal(
        _runtime_function_metadata(function),
        _reviewed_function_metadata(source, name),
    ):
        raise RuntimeError("runtime producer callable metadata refused")
    for global_name in _global_names(function.__code__):
        if global_name in module.__dict__:
            _validate_external_global_binding(module.__dict__[global_name], visited=visited)
        elif global_name in builtins.__dict__:
            if module.__builtins__ is not builtins.__dict__:
                raise RuntimeError("runtime producer builtins binding refused")
        else:
            raise RuntimeError(f"runtime producer global binding absent: {global_name}")
    return function


def _module_snapshot(module: ModuleType) -> tuple[tuple[str, int], ...]:
    return tuple(sorted((name, id(value)) for name, value in module.__dict__.items()))


def _bind_module_snapshot(module: ModuleType) -> None:
    observed = _module_snapshot(module)
    with _RUNTIME_SNAPSHOT_LOCK:
        previous = _RUNTIME_MODULE_SNAPSHOTS.get(module.__name__)
        if previous is None:
            _RUNTIME_MODULE_SNAPSHOTS[module.__name__] = observed
        elif previous != observed:
            raise RuntimeError("runtime producer module dictionary drift refused")


def authenticate_runtime_callable(callable_: object, expected: object) -> None:
    """Bind a clean imported callable to the reviewed module bytes and compiled code."""

    if type(callable_) is not FunctionType or type(expected) not in {dict, type(PRODUCER_CALLABLES)}:
        raise RuntimeError("runtime producer callable type refused")
    expected = dict(expected)  # type: ignore[arg-type]
    if set(expected) != _CALLABLE_RECORD_KEYS:
        raise RuntimeError("runtime producer callable record refused")
    module_name = expected["module"]
    module = sys.modules.get(module_name)
    if (
        type(module) is not ModuleType
        or type(module_name) is not str
        or type(expected["qualname"]) is not str
    ):
        raise RuntimeError("runtime producer callable identity refused")
    source_path = SIM_ROOT / (module_name.replace(".", "/") + ".py")
    raw = _read_reviewed_file(source_path)
    source = raw.decode("utf-8")
    reviewed_path, reviewed_raw, reviewed_source = _runtime_module_source(module)
    if (
        reviewed_path.resolve(strict=True) != source_path.resolve(strict=True)
        or reviewed_raw != raw
        or reviewed_source != source
        or Path(callable_.__code__.co_filename).resolve(strict=True) != source_path.resolve(strict=True)
        or inspect.getsourcefile(callable_) is None
        or Path(inspect.getsourcefile(callable_)).resolve(strict=True) != source_path.resolve(strict=True)
    ):
        raise RuntimeError("runtime producer module origin refused")
    observed_source = {
        "module": module_name,
        "qualname": expected["qualname"],
        "sha256_raw": hashlib.sha256(raw).hexdigest(),
        **_callable_source_record(source, expected["qualname"]),
    }
    wanted_source = {
        key: expected[key]
        for key in (
            "module",
            "qualname",
            "sha256_raw",
            "signature",
            "source_span_sha256",
            "canonical_ast_sha256",
            "transitive_call_graph_sha256",
        )
    }
    if not strict_equal(observed_source, wanted_source):
        raise RuntimeError("runtime producer source/code binding refused")
    _bind_module_snapshot(module)
    call_graph = _call_graph_record(source, expected["qualname"])
    local_names = {name for name, _calls in call_graph}
    if expected["qualname"] not in local_names:
        raise RuntimeError("runtime producer call graph root refused")
    visited: set[tuple[str, str]] = set()
    for name in sorted(local_names):
        _validate_runtime_function(
            callable_ if name == expected["qualname"] else module.__dict__.get(name),
            module=module,
            source=source,
            source_path=source_path,
            name=name,
            visited=visited,
        )
    _bind_module_snapshot(module)


def anchor_record() -> dict[str, object]:
    """Validate immutable lock bytes and producer source text without importing it."""

    predictor_raw = _read_reviewed_file(PREDICTOR_LOCK_PATH)
    producer_raw = _read_reviewed_file(PRODUCER_LOCK_PATH)
    if hashlib.sha256(predictor_raw).hexdigest() != PREDICTOR_METADATA_LOCK_SHA256:
        raise RuntimeError("predictor metadata lock raw hash refused")
    if hashlib.sha256(producer_raw).hexdigest() != PRODUCER_SOURCE_LOCK_SHA256:
        raise RuntimeError("producer source lock raw hash refused")
    predictor = _parse_lock(predictor_raw, expected_keys=_PREDICTOR_LOCK_KEYS)
    producer = _parse_lock(producer_raw, expected_keys=_PRODUCER_LOCK_KEYS)
    if (
        predictor["schema"] != "git_commit_source_lock_v1"
        or predictor["source_commit_oid"] != PREDICTOR_SOURCE_COMMIT_OID
        or predictor["source_tree_oid"] != PREDICTOR_SOURCE_TREE_OID
        or predictor["git_object_format"] != "sha1"
    ):
        raise RuntimeError("predictor source chronology refused")
    _verify_locked_worktree(predictor, label="predictor")
    _verify_locked_worktree(producer, label="producer")

    callable_records = []
    loaded_sources: dict[str, tuple[bytes, str]] = {}
    for label, expected in PRODUCER_CALLABLES.items():
        module = expected["module"]
        relative = module.replace(".", "/") + ".py"
        source_path = SIM_ROOT / relative
        if relative not in loaded_sources:
            raw = _read_reviewed_file(source_path)
            loaded_sources[relative] = (raw, raw.decode("utf-8"))
        raw, text = loaded_sources[relative]
        locked = _entry_by_path(producer, f"cwt-sim/{relative}")
        observed = {
            "label": label,
            "module": module,
            "qualname": expected["qualname"],
            "blob_oid": locked["blob_oid"],
            "sha256_raw": hashlib.sha256(raw).hexdigest(),
            **_callable_source_record(text, expected["qualname"]),
        }
        wanted = {"label": label, **dict(expected)}
        if not strict_equal(observed, wanted):
            raise RuntimeError(f"producer callable anchor refused: {label}")
        if (
            locked["mode"] != "100644"
            or locked["size"] != len(raw)
            or locked["sha256_raw"] != hashlib.sha256(raw).hexdigest()
        ):
            raise RuntimeError(f"producer blob metadata refused: {label}")
        callable_records.append(observed)

    record = {
        "authority": "source_inspection_only_no_response_import",
        "predictor_source_commit_oid": PREDICTOR_SOURCE_COMMIT_OID,
        "predictor_source_tree_oid": PREDICTOR_SOURCE_TREE_OID,
        "predictor_metadata_commit_oid": PREDICTOR_METADATA_COMMIT_OID,
        "predictor_metadata_lock_sha256": hashlib.sha256(predictor_raw).hexdigest(),
        "producer_source_lock_sha256": hashlib.sha256(producer_raw).hexdigest(),
        "producer_callable_records": tuple(callable_records),
        "response_values_read": False,
        "producer_modules_imported": False,
    }
    record["anchor_payload_sha256"] = canonical_sha256(record)
    if record["anchor_payload_sha256"] != REVIEWED_ANCHOR_PAYLOAD_SHA256:
        raise RuntimeError("reviewed anchor payload digest refused")
    return record
