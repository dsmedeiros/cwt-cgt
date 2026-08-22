"""Static lane separation and authenticated source records."""

from __future__ import annotations

import ast
import hashlib
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
ROLE_PATHS = {
    "geometry": "geometry_lane.py",
    "counting": "counting_lane.py",
    "oracle": "oracle_lane.py",
}
FORBIDDEN_IMPORTS = {
    "geometry": ("counting_lane", "oracle_lane", "theorem"),
    "counting": ("geometry_lane", "oracle_lane", "theorem"),
    "oracle": ("geometry_lane", "counting_lane", "theorem"),
}
FORBIDDEN_CALL_TOKENS = {
    "geometry": ("current_row", "counted_gain", "oracle"),
    "counting": ("geometry_certificate", "sld_operator", "curvature_tensor"),
    "oracle": ("geometry_certificate", "counting_certificate", "omega", "phi"),
}
ROLE_MODULES = {
    "geometry": "experiments.shared_generator_counting_curvature_proof.geometry_lane",
    "counting": "experiments.shared_generator_counting_curvature_proof.counting_lane",
    "oracle": "experiments.shared_generator_counting_curvature_proof.oracle_lane",
}
ALLOWED_IMPORT_MODULES = {
    "geometry": {
        "__future__",
        "fractions",
        "functools",
        "experiments.shared_generator_counting_curvature_proof.exact",
        "experiments.shared_generator_counting_curvature_proof.contract",
        "experiments.shared_generator_counting_curvature_proof.generator",
    },
    "counting": {
        "__future__",
        "fractions",
        "functools",
        "experiments.shared_generator_counting_curvature_proof.exact",
        "experiments.shared_generator_counting_curvature_proof.generator",
    },
    "oracle": {
        "__future__",
        "fractions",
        "functools",
        "experiments.shared_generator_counting_curvature_proof.contract",
        "experiments.shared_generator_counting_curvature_proof.exact",
        "experiments.shared_generator_counting_curvature_proof.generator",
        "experiments.shared_generator_counting_curvature_proof.pipeline",
    },
}
REFLECTION_CALLS = {
    "__import__",
    "compile",
    "eval",
    "exec",
    "getattr",
    "globals",
    "locals",
    "setattr",
    "vars",
}
FORBIDDEN_CAPABILITY_ROOTS = {
    "builtins",
    "ctypes",
    "importlib",
    "marshal",
    "operator",
    "pickle",
    "pkgutil",
    "runpy",
    "sys",
}
SAFE_BUILTIN_CALLS = {
    "all",
    "any",
    "bool",
    "dict",
    "enumerate",
    "len",
    "list",
    "range",
    "set",
    "str",
    "sum",
    "tuple",
    "zip",
    "RuntimeError",
}
SAFE_LOCAL_PARAMETER_CALLS: set[str] = set()
SAFE_INSTANCE_METHOD_CALLS = {"conjugate", "is_zero"}


def _resolve_import(role: str, node: ast.ImportFrom) -> str:
    if node.level == 0:
        return node.module or ""
    base = ROLE_MODULES[role].split(".")[: -node.level]
    if node.module:
        base.extend(node.module.split("."))
    return ".".join(base)


def _dotted(node: ast.AST, aliases: dict[str, str]) -> str | None:
    if isinstance(node, ast.Name):
        return aliases.get(node.id, node.id)
    if isinstance(node, ast.Attribute):
        prefix = _dotted(node.value, aliases)
        return None if prefix is None else f"{prefix}.{node.attr}"
    return None


def analyze_role_source(role: str, source: str) -> list[str]:
    if role not in ROLE_PATHS:
        return ["UNKNOWN_ROLE"]
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return ["SOURCE_SYNTAX_INVALID"]
    issues: list[str] = []
    aliases: dict[str, str] = {}
    defined = {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
    }
    forbidden_imports = FORBIDDEN_IMPORTS[role]
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names = [alias.name for alias in node.names]
            for alias in node.names:
                aliases[alias.asname or alias.name.split(".")[0]] = alias.name
        elif isinstance(node, ast.ImportFrom):
            module = _resolve_import(role, node)
            names = [module]
            for alias in node.names:
                if alias.name == "*":
                    issues.append("STAR_IMPORT_FORBIDDEN")
                else:
                    aliases[alias.asname or alias.name] = f"{module}.{alias.name}"
        else:
            names = []
        for name in names:
            root = name.split(".", 1)[0].casefold()
            if name not in ALLOWED_IMPORT_MODULES[role]:
                issues.append(f"IMPORT_NOT_ALLOWLISTED:{name}")
            if root in FORBIDDEN_CAPABILITY_ROOTS:
                issues.append(f"IMPORT_CAPABILITY_FORBIDDEN:{name}")
            if any(token in name for token in forbidden_imports):
                issues.append(f"FORBIDDEN_IMPORT:{name}")
        if isinstance(node, ast.Name):
            if node.id == "__builtins__":
                issues.append("BUILTINS_TABLE_FORBIDDEN")
            if node.id.startswith("__") and node.id.endswith("__") and node.id != "__name__":
                issues.append(f"DUNDER_REFLECTION_FORBIDDEN:{node.id}")
        if isinstance(node, ast.Attribute):
            if node.attr == "__dict__":
                issues.append("MODULE_DICTIONARY_REFLECTION_FORBIDDEN")
            if node.attr.startswith("__") and node.attr.endswith("__"):
                issues.append(f"DUNDER_REFLECTION_FORBIDDEN:{node.attr}")
        if isinstance(node, ast.Subscript):
            base = _dotted(node.value, aliases) or ""
            if base in {"__builtins__", "builtins", "globals", "locals"} or base.endswith(".__dict__"):
                issues.append("REFLECTIVE_SUBSCRIPT_FORBIDDEN")
        if isinstance(node, ast.Call):
            dotted = _dotted(node.func, aliases)
            instance_method = node.func.attr if isinstance(node.func, ast.Attribute) else ""
            target = dotted or (f"<instance>.{instance_method}" if instance_method else "<dynamic>")
            tail = target.rsplit(".", 1)[-1]
            if dotted is None and instance_method not in SAFE_INSTANCE_METHOD_CALLS:
                issues.append("DYNAMIC_CALL_TARGET_FORBIDDEN")
            if tail in REFLECTION_CALLS or tail in {"import_module", "itemgetter"}:
                issues.append(f"REFLECTION_CALL_FORBIDDEN:{target}")
            if isinstance(node.func, ast.Name) and node.func.id not in (
                set(aliases) | defined | SAFE_BUILTIN_CALLS | SAFE_LOCAL_PARAMETER_CALLS
            ):
                issues.append(f"UNKNOWN_CALL_TARGET_FORBIDDEN:{node.func.id}")
            if any(root in target.casefold().split(".") for root in FORBIDDEN_CAPABILITY_ROOTS):
                issues.append(f"CAPABILITY_CALL_FORBIDDEN:{target}")
            if tail in {"format", "join"} and any(
                isinstance(argument, (ast.Constant, ast.JoinedStr, ast.BinOp)) for argument in node.args
            ):
                issues.append(f"DYNAMIC_STRING_CONSTRUCTION_FORBIDDEN:{target}")
            if any(token in target.lower() for token in FORBIDDEN_CALL_TOKENS[role]):
                issues.append(f"FORBIDDEN_CALL:{target}")
    return sorted(set(issues))


def authenticated_role_sources() -> dict[str, dict[str, object]]:
    records: dict[str, dict[str, object]] = {}
    for role, relative in ROLE_PATHS.items():
        path = PACKAGE_DIR / relative
        payload = path.read_bytes()
        if b"\r" in payload or payload.startswith(b"\xef\xbb\xbf"):
            raise RuntimeError(f"role source is not strict UTF-8 LF: {relative}")
        text = payload.decode("utf-8")
        issues = analyze_role_source(role, text)
        records[role] = {
            "path": f"experiments/shared_generator_counting_curvature_proof/{relative}",
            "sha256_utf8_lf": hashlib.sha256(payload).hexdigest(),
            "firewall_issues": issues,
            "authenticated": not issues,
        }
    return records
