"""Authenticated normalized AST firewalls for the four proof lanes."""

from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

EXPERIMENT_DIR = Path(__file__).resolve().parent
SIM_ROOT = EXPERIMENT_DIR.parents[1]
SOURCE_HASH_DOMAIN = "sha256_utf8_lf_v1"


def _compact(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.casefold())


def _canonical_source_bytes(raw: bytes) -> bytes:
    if raw.startswith(b"\xef\xbb\xbf"):
        raise ValueError("UTF-8 BOM is forbidden")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("source must be strict UTF-8") from exc
    text = text.replace("\r\n", "\n")
    if "\r" in text:
        raise ValueError("bare CR is forbidden")
    return text.encode("utf-8")


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _fingerprint(payload: object) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return _sha256(encoded)


@dataclass(frozen=True)
class SourcePolicy:
    role: str
    relative_path: str
    module_name: str
    forbidden_import_fragments: tuple[str, ...]
    forbidden_identifier_fragments: tuple[str, ...]


ROLE_POLICIES = (
    SourcePolicy(
        role="binary64_interval_kernel",
        relative_path="experiments/constitutive_map_3d_proof/binary64_interval.py",
        module_name="experiments.constitutive_map_3d_proof.binary64_interval",
        forbidden_import_fragments=("geometry", "predictor", "oracle", "kubo", "response"),
        forbidden_identifier_fragments=("geometry", "predictor", "oracle", "kubo"),
    ),
    SourcePolicy(
        role="bc3_lattice",
        relative_path="experiments/constitutive_map_3d_proof/bc3_lattice.py",
        module_name="experiments.constitutive_map_3d_proof.bc3_lattice",
        forbidden_import_fragments=("geometry", "predictor", "oracle", "kubo", "response"),
        forbidden_identifier_fragments=("geometry", "predictor", "oracle", "kubo", "response"),
    ),
    SourcePolicy(
        role="bc3_interval_kernel",
        relative_path="experiments/constitutive_map_3d_proof/bc3_interval_model.py",
        module_name="experiments.constitutive_map_3d_proof.bc3_interval_model",
        forbidden_import_fragments=("geometry", "predictor", "oracle", "kubo", "response"),
        forbidden_identifier_fragments=("geometry", "predictor", "oracle", "kubo"),
    ),
    SourcePolicy(
        role="bc3_primitives",
        relative_path="experiments/constitutive_map_3d_proof/bc3_primitives.py",
        module_name="experiments.constitutive_map_3d_proof.bc3_primitives",
        forbidden_import_fragments=("geometry", "predictor", "oracle", "kubo"),
        forbidden_identifier_fragments=("geometry", "predictor", "oracle", "omega"),
    ),
    SourcePolicy(
        role="bc3_predictor",
        relative_path="experiments/constitutive_map_3d_proof/benchmark_c_alpha.py",
        module_name="experiments.constitutive_map_3d_proof.benchmark_c_alpha",
        forbidden_import_fragments=("response", "oracle", "geometry", "kubo"),
        forbidden_identifier_fragments=(
            "response",
            "oracle",
            "omega",
            "phi",
            "orientation",
            "outcome",
            "heldout",
        ),
    ),
    SourcePolicy(
        role="bc3_midpoint_predictor",
        relative_path="experiments/constitutive_map_3d_proof/bc3_midpoint_prediction.py",
        module_name="experiments.constitutive_map_3d_proof.bc3_midpoint_prediction",
        forbidden_import_fragments=("response", "oracle", "geometry", "kubo"),
        forbidden_identifier_fragments=(
            "response",
            "oracle",
            "omega",
            "phi",
            "orientation",
            "outcome",
            "heldout",
        ),
    ),
    SourcePolicy(
        role="bc3_response_oracle",
        relative_path="experiments/constitutive_map_3d_proof/response_oracle.py",
        module_name="experiments.constitutive_map_3d_proof.response_oracle",
        forbidden_import_fragments=("benchmarkcalpha", "geometry", "kubo"),
        forbidden_identifier_fragments=(
            "geometry",
            "predictor",
            "omega",
            "phi",
            "area",
            "orientation",
            "heldout",
            "outcome",
        ),
    ),
    SourcePolicy(
        role="qp3_geometry",
        relative_path="experiments/constitutive_map_3d_proof/qp1_geometry.py",
        module_name="experiments.constitutive_map_3d_proof.qp1_geometry",
        forbidden_import_fragments=("kubo", "response", "oracle"),
        forbidden_identifier_fragments=("kubo", "response", "oracle", "readout"),
    ),
    SourcePolicy(
        role="qp3_kubo",
        relative_path="experiments/constitutive_map_3d_proof/qp1_kubo.py",
        module_name="experiments.constitutive_map_3d_proof.qp1_kubo",
        forbidden_import_fragments=("geometry", "curvature", "berry", "response", "oracle"),
        forbidden_identifier_fragments=(
            "geometry",
            "curvature",
            "berry",
            "connection",
            "omega",
            "phi",
            "area",
            "orientation",
        ),
    ),
)

ALLOWED_IMPORT_MODULES_BY_ROLE = {
    "binary64_interval_kernel": (
        "__future__",
        "dataclasses",
        "fractions",
        "math",
        "numpy",
        "sys",
    ),
    "bc3_lattice": (
        "__future__",
        "dataclasses",
        "experiments.constitutive_map_3d_proof.contract",
        "fractions",
        "math",
        "numpy",
    ),
    "bc3_interval_kernel": (
        "__future__",
        "experiments.constitutive_map_3d_proof.binary64_interval",
        "fractions",
        "numpy",
    ),
    "bc3_primitives": (
        "__future__",
        "experiments.constitutive_map_3d_proof.contract",
        "fractions",
        "math",
        "numpy",
    ),
    "bc3_predictor": (
        "__future__",
        "experiments.constitutive_map_3d_proof.bc3_primitives",
        "experiments.constitutive_map_3d_proof.contract",
        "experiments.constitutive_map_3d_proof.exact",
        "experiments.constitutive_map_3d_proof.pipeline",
        "fractions",
        "math",
        "numpy",
        "typing",
    ),
    "bc3_midpoint_predictor": (
        "__future__",
        "experiments.constitutive_map_3d_proof.bc3_interval_model",
        "experiments.constitutive_map_3d_proof.bc3_lattice",
        "experiments.constitutive_map_3d_proof.benchmark_c_alpha",
        "experiments.constitutive_map_3d_proof.contract",
    ),
    "bc3_response_oracle": (
        "__future__",
        "collections.abc",
        "experiments.constitutive_map_3d_proof.bc3_interval_model",
        "experiments.constitutive_map_3d_proof.bc3_lattice",
        "experiments.constitutive_map_3d_proof.bc3_primitives",
        "experiments.constitutive_map_3d_proof.binary64_interval",
        "experiments.constitutive_map_3d_proof.contract",
        "experiments.constitutive_map_3d_proof.pipeline",
        "numpy",
    ),
    "qp3_geometry": (
        "__future__",
        "experiments.constitutive_map_3d_proof.contract",
        "experiments.constitutive_map_3d_proof.exact",
        "experiments.constitutive_map_3d_proof.qp1_ambient",
        "fractions",
        "numpy",
    ),
    "qp3_kubo": (
        "__future__",
        "experiments.constitutive_map_3d_proof.contract",
        "experiments.constitutive_map_3d_proof.exact",
        "experiments.constitutive_map_3d_proof.qp1_ambient",
        "fractions",
        "numpy",
    ),
}
REVIEWED_IMPORT_ALLOWLISTS_SHA256 = "14aa9e92b71ee99faa9594b32d843cf83c9a306652af51afffc5755133e63845"

# These are reviewed source identities, intentionally independent of live file objects.
# They are replaced only when the corresponding reviewed source is deliberately revised.
REVIEWED_ROLE_SOURCE_SHA256 = {
    "binary64_interval_kernel": "17f73afca6be1606c3bfa2e83e01bbb0121e524385f4c4d65608cf25818d2338",
    "bc3_lattice": "5304622c9cbd731d97dc3b35d86022d0d2bfb4782cde4174e069e7202b39966a",
    "bc3_interval_kernel": "3457b4a25b22b939948162e9b1cb9bf190d74ab9d762f4d04ca49f80748240d0",
    "bc3_primitives": "d268526df93719418931688ea28672596329ea697b35d6f5bc34bedd4dab8604",
    "bc3_predictor": "947403e54ef6ca284dc4da92723ce08c75a723088a02eb1778ecb11f52131214",
    "bc3_midpoint_predictor": "c8ada42ba81107a50cade330a541da7f928d10cc7ed598531e27c80ce5edcab8",
    "bc3_response_oracle": "48305d5a4ffb2187aef69d5baebe1d3609ffce6d820edd172705a59431f22c77",
    "qp3_geometry": "458951bce3093a3a2f6ae02f909cbed48dbf8293e30d4aa157b51006320ea4bf",
    "qp3_kubo": "97333f0f3d44e34d3a2d17fcc1124a5ebf68b98a2df896256fbf30ef44f49884",
}
REVIEWED_ROLE_PATH_SET_SHA256 = "ed4e68f6badc012119c4081d9a4626cd212b41f7dbbe180eb9c23904d19a92e8"


def _resolve_relative_import(module_name: str, level: int, imported: str | None) -> str:
    package = module_name.rsplit(".", 1)[0]
    request = "." * level + (imported or "")
    return importlib.util.resolve_name(request, package)


def _dotted(node: ast.AST, aliases: dict[str, str]) -> str | None:
    if isinstance(node, ast.Name):
        return aliases.get(node.id, node.id)
    if isinstance(node, ast.Attribute):
        parent = _dotted(node.value, aliases)
        return f"{parent}.{node.attr}" if parent else node.attr
    return None


def _contains_fragment(value: str, fragments: Iterable[str]) -> bool:
    compact = _compact(value)
    return any(_compact(fragment) in compact for fragment in fragments)


_REFLECTION_CALL_NAMES = frozenset(
    {
        "getattr",
        "getattr_static",
        "hasattr",
        "setattr",
        "attrgetter",
        "itemgetter",
        "methodcaller",
        "__getattribute__",
        "globals",
        "locals",
        "vars",
        "eval",
        "exec",
        "__import__",
        "compile",
    }
)
_REFLECTIVE_NAMESPACE_NAMES = frozenset({"__builtins__", "builtins"})
_FORBIDDEN_IMPORT_CAPABILITY_ROOTS = frozenset(
    {
        "builtins",
        "ctypes",
        "importlib",
        "marshal",
        "operator",
        "pickle",
        "pkgutil",
        "runpy",
    }
)
_ALLOWED_DUNDER_ATTRIBUTES = frozenset({"__setattr__"})
_ALLOWED_DUNDER_NAMES = frozenset({"__add__", "__mul__", "__radd__", "__rmul__"})
_SAFE_BUILTIN_CALLS = frozenset(
    {
        "ValueError",
        "AssertionError",
        "FloatingPointError",
        "RuntimeError",
        "TypeError",
        "ZeroDivisionError",
        "abs",
        "all",
        "any",
        "bool",
        "complex",
        "dict",
        "enumerate",
        "float",
        "int",
        "isinstance",
        "len",
        "list",
        "max",
        "min",
        "range",
        "reversed",
        "round",
        "set",
        "sorted",
        "str",
        "sum",
        "tuple",
        "zip",
        "cls",
    }
)


def _call_tail(value: str) -> str:
    return value.rsplit(".", 1)[-1].casefold()


def _static_string(node: ast.AST, values: dict[str, str] | None = None) -> str | None:
    """Resolve only literal string composition; never evaluate source code."""

    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.Name) and values is not None:
        return values.get(node.id)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        left = _static_string(node.left, values)
        right = _static_string(node.right, values)
        return left + right if left is not None and right is not None else None
    if isinstance(node, ast.JoinedStr):
        pieces = []
        for value in node.values:
            if isinstance(value, ast.Constant) and isinstance(value.value, str):
                pieces.append(value.value)
            elif isinstance(value, ast.FormattedValue):
                rendered = _static_string(value.value, values)
                if rendered is None:
                    return None
                pieces.append(rendered)
            else:
                return None
        return "".join(pieces)
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
        if node.func.attr == "join" and not node.keywords and len(node.args) == 1:
            separator = _static_string(node.func.value, values)
            sequence = node.args[0]
            if separator is None or not isinstance(sequence, (ast.List, ast.Tuple)):
                return None
            items = [_static_string(item, values) for item in sequence.elts]
            return separator.join(items) if all(item is not None for item in items) else None
        if node.func.attr == "format":
            template = _static_string(node.func.value, values)
            arguments = [_static_string(item, values) for item in node.args]
            keywords = {
                item.arg: _static_string(item.value, values) for item in node.keywords if item.arg is not None
            }
            if (
                template is None
                or any(item is None for item in arguments)
                or any(item is None for item in keywords.values())
            ):
                return None
            try:
                return template.format(*arguments, **keywords)
            except (IndexError, KeyError, ValueError):
                return None
    return None


def _expression_uses_tainted_name(node: ast.AST, tainted: set[str]) -> bool:
    return any(isinstance(item, ast.Name) and item.id in tainted for item in ast.walk(node))


def _reflection_or_dynamic_expression(
    node: ast.AST,
    aliases: dict[str, str],
    tainted: set[str],
) -> bool:
    if _expression_uses_tainted_name(node, tainted):
        return True
    for item in ast.walk(node):
        if isinstance(item, ast.Name):
            if item.id in _REFLECTIVE_NAMESPACE_NAMES:
                return True
            if item.id.startswith("__") and item.id.endswith("__") and item.id not in _ALLOWED_DUNDER_NAMES:
                return True
        if isinstance(item, (ast.Name, ast.Attribute)):
            resolved = _dotted(item, aliases)
            if resolved is not None:
                tail = _call_tail(resolved)
                compact = _compact(resolved)
                if (
                    tail in _REFLECTION_CALL_NAMES
                    or compact.endswith("importmodule")
                    or resolved.casefold() == "sys.modules"
                ):
                    return True
        if isinstance(item, ast.Attribute):
            if item.attr == "__dict__":
                return True
            if (
                item.attr.startswith("__")
                and item.attr.endswith("__")
                and item.attr not in _ALLOWED_DUNDER_ATTRIBUTES
            ):
                return True
        if isinstance(item, ast.Call):
            called = _dotted(item.func, aliases) or "<dynamic_expression>"
            tail = _call_tail(called)
            compact = _compact(called)
            if tail in _REFLECTION_CALL_NAMES or compact.endswith("importmodule"):
                return True
    return False


def _assigned_names(node: ast.Assign | ast.AnnAssign) -> tuple[str, ...]:
    targets = node.targets if isinstance(node, ast.Assign) else [node.target]
    return tuple(target.id for target in targets if isinstance(target, ast.Name))


def analyze_source_text(source: str, policy: SourcePolicy) -> dict[str, object]:
    """Analyze normalized imports, calls, aliases, parameters, and locals."""

    tree = ast.parse(source)
    aliases: dict[str, str] = {}
    imports: list[str] = []
    import_modules: list[str] = []
    calls: list[str] = []
    identifiers: set[str] = set()
    defined_callables: set[str] = set()
    issues: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported = alias.name
                imports.append(imported)
                import_modules.append(imported)
                aliases[alias.asname or imported.split(".")[0]] = imported
        elif isinstance(node, ast.ImportFrom):
            imported_module = _resolve_relative_import(
                policy.module_name,
                node.level,
                node.module,
            )
            import_modules.append(imported_module)
            for alias in node.names:
                if alias.name == "*":
                    issues.append("STAR_IMPORT_FORBIDDEN")
                    imports.append(f"{imported_module}.*")
                    continue
                target = f"{imported_module}.{alias.name}"
                imports.append(target)
                aliases[alias.asname or alias.name] = target
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            identifiers.add(node.name)
            defined_callables.add(node.name)
            arguments = list(node.args.posonlyargs) + list(node.args.args) + list(node.args.kwonlyargs)
            if node.args.vararg:
                arguments.append(node.args.vararg)
            if node.args.kwarg:
                arguments.append(node.args.kwarg)
            identifiers.update(argument.arg for argument in arguments)
        elif isinstance(node, ast.ClassDef):
            identifiers.add(node.name)
            defined_callables.add(node.name)
        elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            identifiers.add(node.id)

    string_values: dict[str, str] = {}
    changed = True
    while changed:
        changed = False
        for node in ast.walk(tree):
            if not isinstance(node, (ast.Assign, ast.AnnAssign)) or node.value is None:
                continue
            value = _static_string(node.value, string_values)
            if value is None:
                continue
            for name in _assigned_names(node):
                if string_values.get(name) != value:
                    string_values[name] = value
                    changed = True

    changed = True
    while changed:
        changed = False
        for node in ast.walk(tree):
            if not isinstance(node, (ast.Assign, ast.AnnAssign)):
                continue
            value = node.value
            resolved = _dotted(value, aliases) if value is not None else None
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            if resolved is None:
                continue
            for target in targets:
                if isinstance(target, ast.Name) and target.id not in aliases:
                    aliases[target.id] = resolved
                    changed = True

    tainted: set[str] = set()
    changed = True
    while changed:
        changed = False
        for node in ast.walk(tree):
            if not isinstance(node, (ast.Assign, ast.AnnAssign)) or node.value is None:
                continue
            if not _reflection_or_dynamic_expression(node.value, aliases, tainted):
                continue
            for name in _assigned_names(node):
                if name not in tainted:
                    tainted.add(name)
                    changed = True

    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            if node.id in _REFLECTIVE_NAMESPACE_NAMES:
                issues.append(f"REFLECTIVE_NAMESPACE_FORBIDDEN:{node.id}")
            if node.id.startswith("__") and node.id.endswith("__") and node.id not in _ALLOWED_DUNDER_NAMES:
                issues.append(f"DUNDER_REFLECTION_FORBIDDEN:{node.id}")
        if isinstance(node, ast.Attribute):
            if node.attr == "__dict__":
                issues.append("MODULE_DICTIONARY_REFLECTION_FORBIDDEN")
            if (
                node.attr.startswith("__")
                and node.attr.endswith("__")
                and node.attr not in _ALLOWED_DUNDER_ATTRIBUTES
            ):
                issues.append(f"DUNDER_REFLECTION_FORBIDDEN:{node.attr}")
            if (_dotted(node, aliases) or "").casefold() == "sys.modules":
                issues.append("GLOBAL_MODULE_TABLE_FORBIDDEN:sys.modules")
        if isinstance(node, ast.Subscript):
            reflective_subscript = _reflection_or_dynamic_expression(
                node.value,
                aliases,
                tainted,
            )
            if reflective_subscript:
                issues.append("REFLECTIVE_SUBSCRIPT_FORBIDDEN")
            target = _static_string(node.slice, string_values)
            if (
                reflective_subscript
                and target is not None
                and (
                    _contains_fragment(target, policy.forbidden_import_fragments)
                    or _contains_fragment(target, policy.forbidden_identifier_fragments)
                )
            ):
                issues.append(f"DYNAMIC_FORBIDDEN_TARGET:{target}")
            if target is not None and _compact(target) in {_compact(name) for name in _REFLECTION_CALL_NAMES}:
                issues.append(f"REFLECTION_NAME_RECOVERY_FORBIDDEN:{target}")
        if not isinstance(node, ast.Call):
            continue
        called = _dotted(node.func, aliases) or "<dynamic_expression>"
        calls.append(called)
        compact_call = _compact(called)
        tail = _call_tail(called)
        if tail in _REFLECTION_CALL_NAMES:
            issues.append(f"REFLECTION_CALL_FORBIDDEN:{called}")
        if called == "<dynamic_expression>":
            issues.append("DYNAMIC_CALL_TARGET_FORBIDDEN")
        if (
            isinstance(node.func, ast.Name)
            and node.func.id not in aliases
            and node.func.id not in defined_callables
            and node.func.id not in _SAFE_BUILTIN_CALLS
            and node.func.id not in tainted
        ):
            issues.append(f"UNKNOWN_CALL_TARGET_FORBIDDEN:{node.func.id}")
        if compact_call.endswith("importmodule") or compact_call == "import":
            issues.append("DYNAMIC_IMPORT_FORBIDDEN")
        if _reflection_or_dynamic_expression(node.func, aliases, tainted):
            issues.append(f"REFLECTIVE_CALLABLE_RECOVERY_FORBIDDEN:{called}")
        for argument in (*node.args, *(keyword.value for keyword in node.keywords)):
            target = _static_string(argument, string_values)
            if target is not None and (
                _contains_fragment(target, policy.forbidden_import_fragments)
                or _contains_fragment(target, policy.forbidden_identifier_fragments)
            ):
                issues.append(f"DYNAMIC_FORBIDDEN_TARGET:{target}")
        if _contains_fragment(called, policy.forbidden_import_fragments):
            issues.append(f"FORBIDDEN_CALL:{called}")

    for name in sorted(tainted):
        issues.append(f"REFLECTIVE_VALUE_FLOW_FORBIDDEN:{name}")

    for imported in imports:
        if _contains_fragment(imported, policy.forbidden_import_fragments):
            issues.append(f"FORBIDDEN_IMPORT:{imported}")
    allowed_modules = set(ALLOWED_IMPORT_MODULES_BY_ROLE[policy.role])
    for imported_module in import_modules:
        root = imported_module.split(".", 1)[0].casefold()
        if imported_module not in allowed_modules:
            issues.append(f"IMPORT_NOT_ALLOWLISTED:{imported_module}")
        if root in _FORBIDDEN_IMPORT_CAPABILITY_ROOTS:
            issues.append(f"IMPORT_CAPABILITY_MODULE_FORBIDDEN:{imported_module}")
    for identifier in identifiers:
        if _contains_fragment(identifier, policy.forbidden_identifier_fragments):
            issues.append(f"FORBIDDEN_IDENTIFIER:{identifier}")

    return {
        "role": policy.role,
        "relative_path": policy.relative_path,
        "module_name": policy.module_name,
        "allowed_import_modules": list(ALLOWED_IMPORT_MODULES_BY_ROLE[policy.role]),
        "imports": sorted(set(imports)),
        "import_modules": sorted(set(import_modules)),
        "calls": sorted(set(calls)),
        "identifiers": sorted(identifiers),
        "issues": sorted(set(issues)),
    }


def reviewed_role_path_set() -> tuple[tuple[str, str, str], ...]:
    return tuple((policy.role, policy.relative_path, policy.module_name) for policy in ROLE_POLICIES)


def source_authentication_records() -> dict[str, dict[str, object]]:
    path_set = reviewed_role_path_set()
    if _fingerprint(path_set) != REVIEWED_ROLE_PATH_SET_SHA256:
        raise RuntimeError("reviewed role/path/module set fingerprint mismatch")
    if set(ALLOWED_IMPORT_MODULES_BY_ROLE) != {policy.role for policy in ROLE_POLICIES}:
        raise RuntimeError("per-role import allowlists do not cover the reviewed roles exactly")
    if _fingerprint(ALLOWED_IMPORT_MODULES_BY_ROLE) != REVIEWED_IMPORT_ALLOWLISTS_SHA256:
        raise RuntimeError("per-role import allowlist fingerprint mismatch")
    records: dict[str, dict[str, object]] = {}
    for policy in ROLE_POLICIES:
        path = SIM_ROOT.joinpath(*policy.relative_path.split("/"))
        raw = path.read_bytes()
        canonical = _canonical_source_bytes(raw)
        analysis = analyze_source_text(canonical.decode("utf-8"), policy)
        actual_sha = _sha256(canonical)
        expected_sha = REVIEWED_ROLE_SOURCE_SHA256[policy.role]
        records[policy.role] = {
            **analysis,
            "hash_domain": SOURCE_HASH_DOMAIN,
            "source_sha256": actual_sha,
            "reviewed_source_sha256": expected_sha,
            "authenticated": actual_sha == expected_sha and analysis["issues"] == [],
        }
    return records
