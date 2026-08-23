"""Fail-closed role firewall and complete source-only material inventory."""

from __future__ import annotations

import ast
import hashlib
import re
from pathlib import Path, PurePosixPath

from .exact import canonical_exact_sha256, freeze_exact_record

PACKAGE_DIR = Path(__file__).resolve().parent
SIM_ROOT = PACKAGE_DIR.parents[1]
_RUNTIME_MODULE_PATH = Path(__file__).resolve(strict=True)
if (
    _RUNTIME_MODULE_PATH != PACKAGE_DIR / "firewall.py"
    or PACKAGE_DIR != _RUNTIME_MODULE_PATH.parent
    or SIM_ROOT != PACKAGE_DIR.parents[1]
):
    raise RuntimeError("firewall runtime roots do not match the loaded module path")
CURRENT_PACKAGE = "experiments.generator_tensor_prediction_protocol"

ROLE_FILES = {
    "model": ("exact.py", "model.py"),
    "geometry": ("geometry.py", "krylov_no_go.py", "connection_eligibility.py"),
    "protocol": ("contract.py", "protocol.py", "response_reader_sentinel.py"),
    "composition": ("__init__.py", "theorem.py", "run.py"),
    "firewall_authority": ("firewall.py",),
    "focused_test": ("../../tests/experiments/test_generator_tensor_prediction_protocol.py",),
}

EXPECTED_PACKAGE_FILE_NAMES = (
    "MODEL_CONTRACT.md",
    "__init__.py",
    "connection_eligibility.py",
    "contract.py",
    "exact.py",
    "firewall.py",
    "geometry.py",
    "krylov_no_go.py",
    "model.py",
    "protocol.py",
    "response_reader_sentinel.py",
    "run.py",
    "theorem.py",
)

PACKAGE_RELATIVE = "experiments/generator_tensor_prediction_protocol"
MATERIAL_FILES = (
    *(
        (
            role,
            (
                "tests/experiments/test_generator_tensor_prediction_protocol.py"
                if role == "focused_test"
                else f"{PACKAGE_RELATIVE}/{name}"
            ),
            "python",
        )
        for role, names in ROLE_FILES.items()
        for name in names
    ),
    ("contract_document", f"{PACKAGE_RELATIVE}/MODEL_CONTRACT.md", "markdown"),
)
REVIEWED_MATERIAL_RELATIVE_PATHS = frozenset(relative for _, relative, _ in MATERIAL_FILES)
REVIEWED_AUTHORITY_ROOT_ASSIGNMENTS = {
    "PACKAGE_DIR": (7, "ed10545926d92a772b9b9c84495a3ad8f152060349296ce862070d1409326db5"),
    "SIM_ROOT": (8, "ea0311ef42d7de03d6d9cd303ddbae32c87a3db411bd7db778eae9d07ff4bd89"),
    "_RUNTIME_MODULE_PATH": (
        9,
        "97fedd9d5196b1e559d9b4da92280f3ab28e6c3206ea3ab765063e8138339add",
    ),
    "CURRENT_PACKAGE": (
        11,
        "5a67c562f9a88208ffc8d85dd13556b28d6fb017ee6b914cb5b803afda6b2d64",
    ),
    "ROLE_FILES": (12, "7618faa8323fd92157299b1f2237b700d61f099b6ef70ea2dff8900a7cbabdd9"),
    "EXPECTED_PACKAGE_FILE_NAMES": (
        13,
        "bd3168da4b2a6f9982de9fea8d00254e4f9714ff6640235d2875c146f501e28a",
    ),
    "PACKAGE_RELATIVE": (
        14,
        "ef78aa9b32e089f145328ff9c03ced36abfc35a62e506d148f2d9ef09ffdc2e4",
    ),
    "MATERIAL_FILES": (
        15,
        "8c084f957ef4b1d9094e984d1edd7164b69241ceff68c75908b9134d45e66b57",
    ),
    "REVIEWED_MATERIAL_RELATIVE_PATHS": (
        16,
        "f9dcf175c6169707d54727ea4911dc3b30c2950267adb72981d6af23c748c595",
    ),
}
REVIEWED_RUNTIME_ROOT_ASSERTION = (
    10,
    "dac7c293c842c2ca84e3139feeb0ec17f20062df80c28ddbd9794e06e7d6805b",
)
REVIEWED_MATERIAL_PATH_SET_SHA256 = "c0f4c5bdd84a8f340ed50fac29e00727dcea7193dadc0780e91779ad17b065b2"
REVIEWED_AUTHORITY_FUNCTION_AST_SHA256 = {
    "_is_reparse": "43407343f7908eddd8722bfb12ec8d0d09c90c9463bc0803bbf32c717b0212f8",
    "_material_path": "8b762ed7931766b8f4e9f00dcfd26523bce65dfcd0941bbb976c4884ec65c09e",
    "_scan_material_snapshot": "10064c8d016e5b39831ce31d53054068f81c3abc807ae7932be6996c744dd956",
    "analyze_reviewed_source": "3a8d1437e0684863c99bc4ce343310e2c6b4ca8a9e06f571430b6e756f5e68ad",
    "source_firewall_record": "df5ff92caad0c40f9a118caef78e5fc76b754fe7dc8f7a241f0ba5262bac1df5",
}
REVIEWED_CONSTRUCTOR_USE_STATEMENT_SHA256 = {
    "composition_path_bootstrap": "1e52ed03724306d91353b3f433d5c339997202deb8b9196b89ad2d6809ba4d8f",
    "authority_package_dir": "ed10545926d92a772b9b9c84495a3ad8f152060349296ce862070d1409326db5",
    "authority_sim_root": "ea0311ef42d7de03d6d9cd303ddbae32c87a3db411bd7db778eae9d07ff4bd89",
    "focused_runner_assignment": "7eca68eace27ca64e9d2a2abf7bd9dc597fe3d05cf891bf3c3cb9dc176932f45",
    "focused_status_invoke": "dc3e14d7e9428ece92c0cfd4745de69762b737ef801947855b60280aa35f2c79",
    "focused_verify_invoke": "bd0ed946f70293858908cb72f04e1d0bf3d05bbb269c8197acac648df3a7042e",
    "focused_material_path_refusal": "8425fe42280bcd7a0cc2b80c55dfdd6eb4b0205652496b381a9a2ae0739a0be5",
}
REVIEWED_CONSTRUCTOR_CONTEXT = {
    "composition_path_bootstrap": (
        6,
        "59881dc830d13ed347e3d965c85e4a2c6b8096f6f9fafe358a60d27dc14f1778",
    ),
    "focused_runner_assignment": (
        16,
        "7eca68eace27ca64e9d2a2abf7bd9dc597fe3d05cf891bf3c3cb9dc176932f45",
    ),
    "focused_material_path_refusal": (
        0,
        "test_material_path_runtime_membership_rejects_predecessor_even_when_canonical",
        "9f84af4d6a0959ceb5900db0dd295e86f166b7c6dae35c328cf473f390a7c52b",
    ),
    "focused_status_invoke": (
        0,
        "test_cli_status_and_verify_source_are_response_free",
        "65445a940e8290967bdeb7c2671bfc19a6be418d490c92ccfe282b674026251c",
    ),
    "focused_verify_invoke": (
        3,
        "test_cli_status_and_verify_source_are_response_free",
        "65445a940e8290967bdeb7c2671bfc19a6be418d490c92ccfe282b674026251c",
    ),
}
CONSTRUCTED_RECEIVER_TYPES = {
    "pathlib.Path": "path",
    "pathlib.PurePosixPath": "path",
    "typer.testing.CliRunner": "cli_runner",
}
KNOWN_BUILTIN_REFERENCES = frozenset(
    {
        "ArithmeticError",
        "AssertionError",
        "AttributeError",
        "BaseException",
        "BaseExceptionGroup",
        "BlockingIOError",
        "BrokenPipeError",
        "BufferError",
        "BytesWarning",
        "ChildProcessError",
        "ConnectionAbortedError",
        "ConnectionError",
        "ConnectionRefusedError",
        "ConnectionResetError",
        "DeprecationWarning",
        "EOFError",
        "Ellipsis",
        "EncodingWarning",
        "EnvironmentError",
        "Exception",
        "ExceptionGroup",
        "False",
        "FileExistsError",
        "FileNotFoundError",
        "FloatingPointError",
        "FutureWarning",
        "GeneratorExit",
        "IOError",
        "ImportError",
        "ImportWarning",
        "IndentationError",
        "IndexError",
        "InterruptedError",
        "IsADirectoryError",
        "KeyError",
        "KeyboardInterrupt",
        "LookupError",
        "MemoryError",
        "ModuleNotFoundError",
        "NameError",
        "None",
        "NotADirectoryError",
        "NotImplemented",
        "NotImplementedError",
        "OSError",
        "OverflowError",
        "PendingDeprecationWarning",
        "PermissionError",
        "ProcessLookupError",
        "RecursionError",
        "ReferenceError",
        "ResourceWarning",
        "RuntimeError",
        "RuntimeWarning",
        "StopAsyncIteration",
        "StopIteration",
        "SyntaxError",
        "SyntaxWarning",
        "SystemError",
        "SystemExit",
        "TabError",
        "TimeoutError",
        "True",
        "TypeError",
        "UnboundLocalError",
        "UnicodeDecodeError",
        "UnicodeEncodeError",
        "UnicodeError",
        "UnicodeTranslateError",
        "UnicodeWarning",
        "UserWarning",
        "ValueError",
        "Warning",
        "WindowsError",
        "ZeroDivisionError",
        "__build_class__",
        "__debug__",
        "__doc__",
        "__import__",
        "__loader__",
        "__name__",
        "__package__",
        "__spec__",
        "abs",
        "aiter",
        "all",
        "anext",
        "any",
        "ascii",
        "bin",
        "bool",
        "breakpoint",
        "bytearray",
        "bytes",
        "callable",
        "chr",
        "classmethod",
        "compile",
        "complex",
        "copyright",
        "credits",
        "delattr",
        "dict",
        "dir",
        "divmod",
        "enumerate",
        "eval",
        "exec",
        "exit",
        "filter",
        "float",
        "format",
        "frozenset",
        "getattr",
        "globals",
        "hasattr",
        "hash",
        "help",
        "hex",
        "id",
        "input",
        "int",
        "isinstance",
        "issubclass",
        "iter",
        "len",
        "license",
        "list",
        "locals",
        "map",
        "max",
        "memoryview",
        "min",
        "next",
        "object",
        "oct",
        "open",
        "ord",
        "pow",
        "print",
        "property",
        "quit",
        "range",
        "repr",
        "reversed",
        "round",
        "set",
        "setattr",
        "slice",
        "sorted",
        "staticmethod",
        "str",
        "sum",
        "super",
        "tuple",
        "type",
        "zip",
        "vars",
        "zip",
    }
)
ALLOWED_BUILTIN_REFERENCES_BY_ROLE = {
    "model": {
        "RuntimeError",
        "TypeError",
        "ValueError",
        "ZeroDivisionError",
        "abs",
        "all",
        "any",
        "bool",
        "bytes",
        "classmethod",
        "dict",
        "enumerate",
        "int",
        "len",
        "list",
        "max",
        "next",
        "object",
        "range",
        "str",
        "sum",
        "tuple",
        "type",
        "zip",
        "zip",
    },
    "geometry": {
        "RuntimeError",
        "TypeError",
        "abs",
        "all",
        "any",
        "dict",
        "int",
        "len",
        "list",
        "max",
        "object",
        "range",
        "str",
        "sum",
        "tuple",
        "type",
        "zip",
    },
    "protocol": {
        "RuntimeError",
        "TypeError",
        "ValueError",
        "all",
        "any",
        "bool",
        "dict",
        "enumerate",
        "int",
        "len",
        "list",
        "object",
        "str",
        "tuple",
        "type",
        "zip",
    },
    "composition": {
        "KeyError",
        "TypeError",
        "__name__",
        "__package__",
        "all",
        "any",
        "bool",
        "dict",
        "int",
        "len",
        "list",
        "object",
        "range",
        "set",
        "sorted",
        "str",
        "sum",
        "tuple",
        "type",
        "zip",
    },
    "firewall_authority": {
        "IndexError",
        "KeyError",
        "OSError",
        "RuntimeError",
        "SyntaxError",
        "TypeError",
        "ValueError",
        "all",
        "any",
        "bool",
        "bytes",
        "complex",
        "dict",
        "float",
        "frozenset",
        "id",
        "int",
        "isinstance",
        "len",
        "list",
        "object",
        "range",
        "set",
        "sorted",
        "str",
        "tuple",
        "type",
        "zip",
    },
    "focused_test": {
        "RuntimeError",
        "TypeError",
        "ValueError",
        "all",
        "any",
        "bool",
        "bytes",
        "dict",
        "enumerate",
        "len",
        "list",
        "next",
        "object",
        "range",
        "reversed",
        "set",
        "str",
        "sum",
        "tuple",
        "type",
        "zip",
    },
}
ALLOWED_BUILTIN_CALLS_BY_ROLE = {
    "model": {
        "RuntimeError",
        "TypeError",
        "ValueError",
        "ZeroDivisionError",
        "abs",
        "all",
        "any",
        "enumerate",
        "len",
        "list",
        "max",
        "next",
        "range",
        "sum",
        "tuple",
        "type",
        "zip",
    },
    "geometry": {
        "RuntimeError",
        "TypeError",
        "abs",
        "all",
        "any",
        "dict",
        "len",
        "list",
        "max",
        "range",
        "sum",
        "tuple",
        "type",
        "zip",
    },
    "protocol": {
        "RuntimeError",
        "TypeError",
        "ValueError",
        "all",
        "any",
        "bool",
        "enumerate",
        "len",
        "str",
        "tuple",
        "type",
        "zip",
    },
    "composition": {
        "all",
        "any",
        "bool",
        "dict",
        "len",
        "list",
        "range",
        "set",
        "sorted",
        "str",
        "sum",
        "tuple",
        "type",
        "zip",
    },
    "firewall_authority": {
        "RuntimeError",
        "TypeError",
        "ValueError",
        "all",
        "any",
        "frozenset",
        "id",
        "isinstance",
        "len",
        "range",
        "set",
        "sorted",
        "tuple",
        "type",
        "zip",
    },
    "focused_test": {
        "all",
        "any",
        "dict",
        "enumerate",
        "len",
        "list",
        "next",
        "object",
        "range",
        "reversed",
        "set",
        "sum",
        "tuple",
        "type",
        "zip",
    },
}
REVIEWED_ID_CALL_SHA256 = frozenset(
    {
        "afbca3cfd7ca6b59ee2fa91284f3b23e8e47697bd52bd8400efd20c2356e3919",
        "ae636081cf37fb3996f187a2ab96899d0b4e6bc3c709aef71b9cea73cf24bc0b",
        "6726f79b9043ff18bf07ec3f873dd857304696536c8a9d817f32109bb1f8d033",
        "714274435820dc66760c642913a002414a813f17786f305db8fb6b64f99f9a7d",
    }
)


def _canonical_ast_payload(value: object) -> object:
    """Return a Python-minor-neutral, exact payload for parsed source syntax.

    Python 3.13 changed ``ast.dump`` so empty fields are hidden by default, and
    newer grammar nodes may add empty compatibility fields (currently
    ``type_params``).  The reviewed domain below walks the public AST fields
    directly and ignores only an empty compatibility field.  All other fields,
    including empty argument/call lists, remain part of the authenticated
    syntax.
    """

    if isinstance(value, ast.AST):
        fields = []
        for name, member in ast.iter_fields(value):
            if name == "type_params" and member == []:
                continue
            fields.append((name, _canonical_ast_payload(member)))
        return ("AST", type(value).__name__, tuple(fields))
    if type(value) is list:
        return ("list", tuple(_canonical_ast_payload(member) for member in value))
    if type(value) is tuple:
        return ("tuple", tuple(_canonical_ast_payload(member) for member in value))
    if value is None:
        return ("none",)
    if type(value) is bool:
        return ("bool", value)
    if type(value) is int:
        return ("int", value)
    if type(value) is str:
        return ("str", value)
    if type(value) is bytes:
        return ("bytes", value.hex())
    if type(value) is float:
        return ("float", value.hex())
    if type(value) is complex:
        return ("complex", value.real.hex(), value.imag.hex())
    if value is ...:
        return ("ellipsis",)
    raise TypeError(f"unsupported AST field value: {type(value).__name__}")


def _canonical_ast_sha256(value: ast.AST) -> str:
    """Hash parsed syntax in the reviewed Python-minor-neutral AST domain."""

    return canonical_exact_sha256(_canonical_ast_payload(value))


def _canonical_source_ast_sha256(text: str) -> str:
    """Hash a complete source string in the reviewed canonical AST domain."""

    if type(text) is not str:
        raise TypeError("canonical source AST hashing requires an exact string")
    return _canonical_ast_sha256(ast.parse(text))


FORBIDDEN_IMPORT_PARTS = (
    "countinglane",
    "fcslane",
    "loopfluxcountingcurvatureproof",
    "oraclelane",
    "responseoracle",
)
FORBIDDEN_CALL_PARTS = (
    "currentrow",
    "currentderivatives",
    "countedqjet",
    "exactoraclerecord",
    "expectedartifactbytes",
)
FORBIDDEN_CAPABILITY_MODULES = {
    "aiohttp",
    "builtins",
    "ctypes",
    "http",
    "importlib",
    "io",
    "marshal",
    "operator",
    "os",
    "pickle",
    "pkgutil",
    "requests",
    "runpy",
    "socket",
    "subprocess",
    "urllib",
}
REFLECTION_NAMES = {
    "__getattribute__",
    "__import__",
    "attrgetter",
    "compile",
    "eval",
    "exec",
    "getattr",
    "globals",
    "hasattr",
    "itemgetter",
    "locals",
    "methodcaller",
    "setattr",
    "vars",
}
FORBIDDEN_BUILTIN_REFERENCES = {
    "__import__",
    "breakpoint",
    "compile",
    "eval",
    "exec",
    "getattr",
    "globals",
    "hasattr",
    "input",
    "locals",
    "open",
    "setattr",
    "vars",
}
HIGHER_ORDER_TRANSPORT_NAMES = {"filter", "iter", "map", "next"}
FORBIDDEN_CAPABILITY_ATTRIBUTES = {
    "__builtins__",
    "__dict__",
    "__globals__",
    "__subclasses__",
    "absolute",
    "argv",
    "buffer",
    "chdir",
    "edit",
    "environ",
    "environb",
    "exists",
    "expanduser",
    "get_text_stream",
    "getenv",
    "_getframe",
    "glob",
    "group",
    "hardlink_to",
    "home",
    "input",
    "is_dir",
    "is_file",
    "is_symlink",
    "iterdir",
    "launch",
    "load",
    "lstat",
    "mkdir",
    "open",
    "owner",
    "partial",
    "popen",
    "prompt",
    "read",
    "read_bytes",
    "read_text",
    "readlink",
    "rename",
    "replace",
    "resolve",
    "rglob",
    "rmdir",
    "run",
    "samefile",
    "stat",
    "stderr",
    "stdin",
    "stdout",
    "system",
    "symlink_to",
    "chmod",
    "touch",
    "unlink",
    "write",
    "write_bytes",
    "write_text",
}
ALLOWED_DUNDER_NAMES = {
    "__add__",
    "__all__",
    "__file__",
    "__future__",
    "__main__",
    "__mul__",
    "__name__",
    "__package__",
    "__radd__",
    "__rmul__",
}
ALLOWED_IMPORT_MODULES_BY_ROLE = {
    "model": {
        "__future__",
        "dataclasses",
        "fractions",
        "functools",
        "hashlib",
        "types",
        "typing",
        f"{CURRENT_PACKAGE}.contract",
        f"{CURRENT_PACKAGE}.exact",
    },
    "geometry": {
        "__future__",
        "dataclasses",
        "fractions",
        "functools",
        "types",
        f"{CURRENT_PACKAGE}.connection_eligibility",
        f"{CURRENT_PACKAGE}.contract",
        f"{CURRENT_PACKAGE}.exact",
        f"{CURRENT_PACKAGE}.geometry",
        f"{CURRENT_PACKAGE}.krylov_no_go",
        f"{CURRENT_PACKAGE}.model",
    },
    "protocol": {
        "__future__",
        "dataclasses",
        "enum",
        "fractions",
        "hashlib",
        "json",
        "types",
        f"{CURRENT_PACKAGE}.contract",
        f"{CURRENT_PACKAGE}.exact",
        f"{CURRENT_PACKAGE}.protocol",
        f"{CURRENT_PACKAGE}.response_reader_sentinel",
    },
    "composition": {
        "__future__",
        "fractions",
        "json",
        "pathlib",
        "sys",
        "typer",
        "types",
        f"{CURRENT_PACKAGE}.connection_eligibility",
        f"{CURRENT_PACKAGE}.contract",
        f"{CURRENT_PACKAGE}.exact",
        f"{CURRENT_PACKAGE}.firewall",
        f"{CURRENT_PACKAGE}.krylov_no_go",
        f"{CURRENT_PACKAGE}.model",
        f"{CURRENT_PACKAGE}.protocol",
        f"{CURRENT_PACKAGE}.response_reader_sentinel",
        f"{CURRENT_PACKAGE}.theorem",
    },
    "firewall_authority": {
        "__future__",
        "ast",
        "hashlib",
        "pathlib",
        "re",
        f"{CURRENT_PACKAGE}.exact",
    },
    "focused_test": {
        "__future__",
        "dataclasses",
        "fractions",
        "pytest",
        "typer.testing",
        "types",
        f"{CURRENT_PACKAGE}.connection_eligibility",
        f"{CURRENT_PACKAGE}.contract",
        f"{CURRENT_PACKAGE}.exact",
        f"{CURRENT_PACKAGE}.firewall",
        f"{CURRENT_PACKAGE}.krylov_no_go",
        f"{CURRENT_PACKAGE}.protocol",
        f"{CURRENT_PACKAGE}.response_reader_sentinel",
        f"{CURRENT_PACKAGE}.run",
        f"{CURRENT_PACKAGE}.theorem",
    },
}
ALLOWED_DIRECT_IMPORTS_BY_ROLE = {
    "model": {"hashlib"},
    "geometry": set(),
    "protocol": {"hashlib", "json"},
    "composition": {"json", "sys", "typer"},
    "firewall_authority": {"ast", "hashlib", "re"},
    "focused_test": {"pytest"},
}
ALLOWED_FROM_IMPORT_SYMBOLS_BY_ROLE = {
    "model": {
        "__future__": {"annotations"},
        "dataclasses": {"dataclass"},
        "fractions": {"Fraction"},
        "functools": {"lru_cache"},
        "types": {"MappingProxyType"},
        "typing": {"Iterable", "Sequence"},
        f"{CURRENT_PACKAGE}.contract": {"MODEL_CONTRACT", "Point"},
        f"{CURRENT_PACKAGE}.exact": {
            "Gaussian",
            "IMAG_UNIT",
            "Matrix",
            "ONE",
            "Vector",
            "ZERO",
            "dot",
            "gaussian",
            "identity",
            "inverse",
            "matrix_add",
            "matrix_multiply",
            "matrix_scale",
            "matrix_subtract",
            "matrix_vector",
            "outer",
            "solve",
            "vector_add",
            "vector_scale",
            "zeros",
        },
    },
    "geometry": {
        "__future__": {"annotations"},
        "dataclasses": {"dataclass"},
        "fractions": {"Fraction"},
        "functools": {"lru_cache"},
        "types": {"MappingProxyType"},
        f"{CURRENT_PACKAGE}.contract": {
            "A_CENTERS",
            "HELDOUT_AREA_VECTOR",
            "HELDOUT_CENTER",
            "MODEL_CONTRACT",
            "Point",
            "RESERVATION_STATUS",
            "V_CENTERS",
        },
        f"{CURRENT_PACKAGE}.exact": {
            "IMAG_UNIT",
            "Matrix",
            "RationalMatrix",
            "canonical_exact_sha256",
            "fraction_vector_sha256",
            "freeze_exact_record",
            "matrix_add",
            "matrix_multiply",
            "matrix_scale",
            "matrix_subtract",
            "matrix_vector",
            "rational_determinant",
            "rational_inverse",
            "real_fraction",
            "solve",
            "trace",
            "unvec",
            "vec",
            "vector_add",
            "zeros",
        },
        f"{CURRENT_PACKAGE}.geometry": {
            "GeometryJet",
            "RationalVector",
            "dimensionless_endomorphism",
            "geometry_jet",
            "normalized_omega",
            "normalized_omega_derivatives",
            "normalized_purity_derivative",
            "purity_jet",
            "rational_matrix_add",
            "rational_matrix_multiply",
            "rational_matrix_scale",
            "rational_matrix_vector",
            "two_form_pullback",
            "two_form_pullback_derivative",
            "wilson_scalar_jet",
        },
        f"{CURRENT_PACKAGE}.model": {"BranchBundle", "N", "branch_bundle"},
    },
    "protocol": {
        "__future__": {"annotations"},
        "dataclasses": {"asdict", "dataclass"},
        "enum": {"Enum"},
        "fractions": {"Fraction"},
        "types": {"MappingProxyType"},
        f"{CURRENT_PACKAGE}.contract": {
            "A_CENTERS",
            "EXPOSURE_REGISTRY",
            "HELDOUT_AREA_VECTOR",
            "HELDOUT_CENTER",
            "Point",
            "RESERVATION_STATUS",
            "V_CENTERS",
            "exposure_registry_issues",
            "exposure_registry_sha256",
        },
        f"{CURRENT_PACKAGE}.exact": {"canonical_exact_sha256"},
    },
    "composition": {
        "__future__": {"annotations"},
        "fractions": {"Fraction"},
        "pathlib": {"Path"},
        "types": {"MappingProxyType"},
        f"{CURRENT_PACKAGE}.connection_eligibility": {
            "connection_basis",
            "connection_eligibility_certificate",
            "p0_acceptance_payload",
            "predictor_curvature",
            "predictor_one_form",
        },
        f"{CURRENT_PACKAGE}.contract": {
            "A_CENTERS",
            "CASE_GATE_MAP",
            "EXPECTED_CASE_DISPOSITIONS",
            "HELDOUT_AREA_VECTOR",
            "HELDOUT_CENTER",
            "MODEL_CONTRACT",
            "ORDERED_GATES",
            "RESERVATION_STATUS",
            "V_CENTERS",
            "contract_issues",
            "exposure_registry_issues",
        },
        f"{CURRENT_PACKAGE}.exact": {
            "canonical_exact_sha256",
            "fraction_vector_sha256",
            "rational_determinant",
        },
        f"{CURRENT_PACKAGE}.firewall": {
            "EXPECTED_PACKAGE_FILE_NAMES",
            "MATERIAL_FILES",
            "ROLE_FILES",
            "source_firewall_record",
        },
        f"{CURRENT_PACKAGE}.krylov_no_go": {
            "closure_coefficients",
            "krylov_no_go_certificate",
            "n0_acceptance_payload",
        },
        f"{CURRENT_PACKAGE}.model": {"branch_bundle", "branch_identity_record"},
        f"{CURRENT_PACKAGE}.protocol": {"canonical_protocol_record"},
        f"{CURRENT_PACKAGE}.response_reader_sentinel": {"sentinel_record"},
        f"{CURRENT_PACKAGE}.theorem": {"execute_program"},
    },
    "firewall_authority": {
        "__future__": {"annotations"},
        "pathlib": {"Path", "PurePosixPath"},
        f"{CURRENT_PACKAGE}.exact": {"canonical_exact_sha256", "freeze_exact_record"},
    },
    "focused_test": {
        "__future__": {"annotations"},
        "dataclasses": {"replace"},
        "fractions": {"Fraction"},
        "typer.testing": {"CliRunner"},
        "types": {"MappingProxyType"},
        f"{CURRENT_PACKAGE}.connection_eligibility": {
            "EXPECTED_GRAM_DETERMINANT_SHA256",
            "EXPECTED_HELDOUT_DENSITY_SHA256",
            "EXPECTED_P0_CERTIFICATE_SHA256",
            "connection_basis",
            "connection_eligibility_certificate",
            "predictor_curvature",
            "predictor_one_form",
        },
        f"{CURRENT_PACKAGE}.contract": {
            "A_CENTERS",
            "CASE_GATE_MAP",
            "EXPECTED_CASE_DISPOSITIONS",
            "EXPOSURE_REGISTRY",
            "HELDOUT_CENTER",
            "MODEL_CONTRACT",
            "ORDERED_GATES",
            "RESERVATION_STATUS",
            "REVIEWED_EXPOSURE_REGISTRY_SHA256",
            "V_CENTERS",
            "contract_issues",
            "exposure_registry_issues",
            "exposure_registry_sha256",
        },
        f"{CURRENT_PACKAGE}.exact": {
            "fraction_vector_sha256",
            "freeze_exact_record",
            "rational_determinant",
        },
        f"{CURRENT_PACKAGE}.firewall": {
            "ALLOWED_BUILTIN_REFERENCES_BY_ROLE",
            "KNOWN_BUILTIN_REFERENCES",
            "MATERIAL_FILES",
            "REVIEWED_MATERIAL_PATH_SET_SHA256",
            "_analyze_source_semantics",
            "_canonical_source_ast_sha256",
            "_material_path",
            "_scan_material_snapshot",
            "analyze_reviewed_source",
            "analyze_source_text",
            "source_firewall_record",
        },
        f"{CURRENT_PACKAGE}.krylov_no_go": {
            "EXPECTED_CLOSURE_DETERMINANT_SHA256",
            "EXPECTED_N0_CERTIFICATE_SHA256",
            "krylov_no_go_certificate",
        },
        f"{CURRENT_PACKAGE}.protocol": {
            "FalsificationCriterion",
            "ProtocolSession",
            "REVIEWED_CRITERION_SHA256",
            "canonical_protocol_record",
            "criterion_issues",
            "criterion_sha256",
        },
        f"{CURRENT_PACKAGE}.response_reader_sentinel": {
            "ResponseAccessBlocked",
            "blocked_response_reader",
            "sentinel_record",
        },
        f"{CURRENT_PACKAGE}.run": {"app"},
        f"{CURRENT_PACKAGE}.theorem": {"build_certificates", "execute_program", "gate_results"},
    },
}
FORBIDDEN_IO_PROCESS_CALLS = {
    "absolute",
    "chdir",
    "exists",
    "expanduser",
    "getenv",
    "glob",
    "input",
    "is_dir",
    "is_file",
    "is_symlink",
    "iterdir",
    "lstat",
    "open",
    "popen",
    "read",
    "read_bytes",
    "read_text",
    "resolve",
    "rglob",
    "run",
    "stat",
    "system",
    "write",
    "write_bytes",
    "write_text",
}
ALLOWED_IO_PROCESS_CALLS_BY_ROLE = {
    "model": set(),
    "geometry": set(),
    "protocol": set(),
    "composition": {"resolve"},
    "firewall_authority": {
        "is_dir",
        "is_file",
        "is_symlink",
        "iterdir",
        "read_bytes",
        "resolve",
    },
    "focused_test": set(),
}
SAFE_CAPABILITY_CALLS_BY_ROLE = {
    "model": set(),
    "geometry": set(),
    "protocol": set(),
    "composition": set(),
    "firewall_authority": set(),
    "focused_test": {"dataclasses.replace"},
}
CONTROLLED_NAMESPACE_ATTRIBUTES_BY_ROLE = {
    "model": set(),
    "geometry": set(),
    "protocol": {"json.dumps"},
    "composition": {
        "json.dumps",
        "sys.path",
        "sys.path.insert",
        "typer.Exit",
        "typer.Typer",
        "typer.echo",
    },
    "firewall_authority": set(),
    "focused_test": {"pytest.mark", "pytest.mark.parametrize", "pytest.raises"},
}
CONTROLLED_NAMESPACE_ROOTS = {"json", "pathlib", "pytest", "sys", "typer"}


def _compact(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.casefold())


def _contains_forbidden(value: str) -> bool:
    compact = _compact(value)
    return any(part in compact for part in (*FORBIDDEN_IMPORT_PARTS, *FORBIDDEN_CALL_PARTS))


def _static_string(node: ast.AST, values: dict[str, str] | None = None) -> str | None:
    if isinstance(node, ast.Constant) and type(node.value) is str:
        return node.value
    if isinstance(node, ast.Name) and values is not None:
        return values.get(node.id)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        left = _static_string(node.left, values)
        right = _static_string(node.right, values)
        return left + right if left is not None and right is not None else None
    if isinstance(node, ast.JoinedStr):
        pieces = []
        for item in node.values:
            if isinstance(item, ast.Constant) and type(item.value) is str:
                pieces.append(item.value)
            elif isinstance(item, ast.FormattedValue):
                rendered = _static_string(item.value, values)
                if rendered is None:
                    return None
                pieces.append(rendered)
            else:
                return None
        return "".join(pieces)
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
        if node.func.attr == "join" and len(node.args) == 1 and not node.keywords:
            separator = _static_string(node.func.value, values)
            sequence = node.args[0]
            if separator is None or not isinstance(sequence, (ast.List, ast.Tuple)):
                return None
            items = [_static_string(item, values) for item in sequence.elts]
            return separator.join(items) if all(item is not None for item in items) else None
        if node.func.attr == "format":
            template = _static_string(node.func.value, values)
            arguments = [_static_string(item, values) for item in node.args]
            if template is None or any(item is None for item in arguments) or node.keywords:
                return None
            try:
                return template.format(*arguments)
            except (IndexError, KeyError, ValueError):
                return None
    return None


def _dotted(node: ast.AST, aliases: dict[str, str]) -> str | None:
    if isinstance(node, ast.Name):
        return aliases.get(node.id, node.id)
    if isinstance(node, ast.Attribute):
        parent = _dotted(node.value, aliases)
        return f"{parent}.{node.attr}" if parent else node.attr
    return None


def _assigned_names(node: ast.Assign | ast.AnnAssign) -> tuple[str, ...]:
    targets = node.targets if isinstance(node, ast.Assign) else [node.target]
    return tuple(target.id for target in targets if isinstance(target, ast.Name))


def _canonical_text(raw: bytes) -> str:
    if raw.startswith(b"\xef\xbb\xbf"):
        raise ValueError("UTF-8 BOM forbidden")
    text = raw.decode("utf-8")
    if "\r" in text or not text.endswith("\n"):
        raise ValueError("strict LF with final newline required")
    return text


def _resolved_from_module(node: ast.ImportFrom) -> str:
    if node.level == 0:
        return node.module or ""
    suffix = node.module or ""
    return CURRENT_PACKAGE + (f".{suffix}" if suffix else "")


def _import_records(tree: ast.AST) -> tuple[tuple[str, str], ...]:
    records = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            records.extend((alias.name, alias.name) for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            module = _resolved_from_module(node)
            records.extend((module, f"{module}.{alias.name}") for alias in node.names)
    return tuple(sorted(set(records)))


def _import_issues(tree: ast.AST, *, role: str) -> list[str]:
    issues = []
    allowed_modules = ALLOWED_IMPORT_MODULES_BY_ROLE[role]
    allowed_from_symbols = ALLOWED_FROM_IMPORT_SYMBOLS_BY_ROLE[role]
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            records = ((alias.name, alias.name, None) for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            module = _resolved_from_module(node)
            records = ((module, f"{module}.{alias.name}", alias.name) for alias in node.names)
        else:
            continue
        for module, target, imported_symbol in records:
            if target.endswith(".*"):
                issues.append(f"STAR_IMPORT_FORBIDDEN:{module}")
            if _contains_forbidden(target):
                issues.append(f"FORBIDDEN_IMPORT_TARGET:{target}")
            root = module.split(".", 1)[0]
            if root in FORBIDDEN_CAPABILITY_MODULES:
                issues.append(f"IMPORT_CAPABILITY_MODULE_FORBIDDEN:{module}")
            if module not in allowed_modules:
                issues.append(f"IMPORT_NOT_ALLOWLISTED:{module}")
            if imported_symbol is None and module not in ALLOWED_DIRECT_IMPORTS_BY_ROLE[role]:
                issues.append(f"DIRECT_IMPORT_NOT_ALLOWLISTED:{module}")
            if imported_symbol is not None and imported_symbol not in allowed_from_symbols.get(module, set()):
                issues.append(f"IMPORTED_SYMBOL_NOT_ALLOWLISTED:{target}")
    return issues


def _analyze_source_semantics(text: str, *, role: str) -> tuple[str, ...]:
    if role not in ROLE_FILES:
        return ("UNKNOWN_ROLE",)
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return ("SYNTAX_ERROR",)
    issues = _import_issues(tree, role=role)
    aliases: dict[str, str] = {}
    imported_bindings: set[str] = set()
    import_binding_counts: dict[str, int] = {}
    import_binding_targets: dict[str, set[str]] = {}
    static_strings: dict[str, str] = {}
    ambiguous_aliases: set[str] = set()
    ambiguous_static_strings: set[str] = set()
    tainted: set[str] = set()
    parents = {child: parent for parent in ast.walk(tree) for child in ast.iter_child_nodes(parent)}

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                local = alias.asname or alias.name.split(".")[0]
                aliases[local] = alias.name
                imported_bindings.add(local)
                import_binding_counts[local] = import_binding_counts.get(local, 0) + 1
                import_binding_targets.setdefault(local, set()).add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            module = _resolved_from_module(node)
            for alias in node.names:
                local = alias.asname or alias.name
                aliases[local] = f"{module}.{alias.name}"
                imported_bindings.add(local)
                import_binding_counts[local] = import_binding_counts.get(local, 0) + 1
                import_binding_targets.setdefault(local, set()).add(f"{module}.{alias.name}")

    changed = True
    while changed:
        changed = False
        for node in ast.walk(tree):
            if not isinstance(node, (ast.Assign, ast.AnnAssign)) or node.value is None:
                continue
            rendered = _static_string(node.value, static_strings)
            if rendered is not None:
                for name in _assigned_names(node):
                    if name in ambiguous_static_strings:
                        continue
                    existing = static_strings.get(name)
                    if existing is None:
                        static_strings[name] = rendered
                        changed = True
                    elif existing != rendered:
                        static_strings.pop(name, None)
                        ambiguous_static_strings.add(name)
                        changed = True
            resolved = _dotted(node.value, aliases)
            if resolved is not None:
                for name in _assigned_names(node):
                    if name in ambiguous_aliases:
                        continue
                    existing = aliases.get(name)
                    if existing is None:
                        aliases[name] = resolved
                        changed = True
                    elif existing != resolved:
                        aliases.pop(name, None)
                        ambiguous_aliases.add(name)
                        changed = True

    scope_nodes = (
        ast.FunctionDef,
        ast.AsyncFunctionDef,
        ast.Lambda,
        ast.ListComp,
        ast.SetComp,
        ast.DictComp,
        ast.GeneratorExp,
    )

    def scope_owner(node: ast.AST) -> ast.AST:
        current = node
        while current is not tree:
            if isinstance(current, scope_nodes):
                return current
            parent = parents.get(current)
            if parent is None:
                break
            current = parent
        return tree

    receiver_kinds: dict[tuple[int, str], str] = {}
    callable_return_kinds: dict[tuple[int, str], str] = {}

    def receiver_name_kind(node: ast.Name) -> str | None:
        local = receiver_kinds.get((id(scope_owner(node)), node.id))
        if local is not None:
            return local
        global_kind = receiver_kinds.get((id(tree), node.id))
        if global_kind is not None:
            return global_kind
        if role == "firewall_authority" and node.id in {
            "PACKAGE_DIR",
            "SIM_ROOT",
            "_RUNTIME_MODULE_PATH",
        }:
            return "path"
        return CONSTRUCTED_RECEIVER_TYPES.get(_dotted(node, aliases) or "")

    def callable_name_kind(node: ast.Name) -> str | None:
        local = callable_return_kinds.get((id(scope_owner(node)), node.id))
        if local is not None:
            return local
        return callable_return_kinds.get((id(tree), node.id))

    def receiver_kind(node: ast.AST) -> str | None:
        if isinstance(node, ast.Name):
            return receiver_name_kind(node)
        if isinstance(node, ast.Attribute):
            kind = receiver_kind(node.value)
            if kind == "cli_result":
                return "cli_runner" if node.attr == "runner" else None
            return kind
        if isinstance(node, ast.Subscript):
            kind = receiver_kind(node.value)
            return kind.removesuffix("_collection") if kind else None
        if isinstance(node, ast.NamedExpr):
            return receiver_kind(node.value)
        if isinstance(node, ast.Starred):
            return receiver_kind(node.value)
        if isinstance(node, (ast.Await, ast.Yield, ast.YieldFrom)):
            return receiver_kind(node.value) if node.value is not None else None
        if isinstance(node, ast.IfExp):
            left = receiver_kind(node.body)
            right = receiver_kind(node.orelse)
            if left is None:
                return right
            if right is None:
                return left
            return left if left == right else "mixed_constructed"
        if isinstance(node, ast.BoolOp):
            kinds = {receiver_kind(member) for member in node.values}
            kinds.discard(None)
            if not kinds:
                return None
            first = kinds.pop()
            return first if not kinds else "mixed_constructed"
        if isinstance(node, ast.BinOp):
            return receiver_kind(node.left) or receiver_kind(node.right)
        if isinstance(node, ast.Call):
            called = _dotted(node.func, aliases) or ""
            constructed = CONSTRUCTED_RECEIVER_TYPES.get(called)
            if constructed is not None:
                return constructed
            if called.rsplit(".", 1)[-1] == "_material_path":
                return "path"
            if isinstance(node.func, ast.Name):
                returned = callable_name_kind(node.func)
                if returned is not None:
                    return returned
            if called in {"enumerate", "frozenset", "iter", "list", "reversed", "set", "sorted", "tuple"}:
                for argument in node.args:
                    kind = receiver_kind(argument)
                    if kind is not None:
                        return kind if kind.endswith("_collection") else f"{kind}_collection"
                return None
            if isinstance(node.func, ast.Attribute):
                kind = receiver_kind(node.func.value)
                if kind is None:
                    return None
                if kind.removesuffix("_collection") == "cli_runner" and node.func.attr == "invoke":
                    return "cli_result"
                if node.func.attr in {"glob", "iterdir", "rglob", "walk"}:
                    return kind if kind.endswith("_collection") else f"{kind}_collection"
                return kind
            return None
        if isinstance(node, (ast.List, ast.Set, ast.Tuple)):
            for element in node.elts:
                kind = receiver_kind(element)
                if kind is not None:
                    return kind if kind.endswith("_collection") else f"{kind}_collection"
            return None
        if isinstance(node, ast.Dict):
            for key, member in zip(node.keys, node.values, strict=True):
                kind = (receiver_kind(key) if key is not None else None) or receiver_kind(member)
                if kind is not None:
                    return kind if kind.endswith("_collection") else f"{kind}_collection"
            return None
        if isinstance(node, (ast.ListComp, ast.SetComp, ast.GeneratorExp)):
            kind = receiver_kind(node.elt)
            return kind if kind is None or kind.endswith("_collection") else f"{kind}_collection"
        if isinstance(node, ast.DictComp):
            kind = receiver_kind(node.key) or receiver_kind(node.value)
            return kind if kind is None or kind.endswith("_collection") else f"{kind}_collection"
        return None

    def bind_receiver_name(target: ast.AST, kind: str) -> bool:
        if isinstance(target, (ast.Name, ast.arg)):
            name = target.id if isinstance(target, ast.Name) else target.arg
            key = (id(scope_owner(target)), name)
            existing = receiver_kinds.get(key)
            if existing is None:
                receiver_kinds[key] = kind
                return True
            if existing == kind:
                return False
            existing_base = existing.removesuffix("_collection")
            kind_base = kind.removesuffix("_collection")
            if existing_base == kind_base:
                merged = (
                    f"{existing_base}_collection"
                    if existing.endswith("_collection") or kind.endswith("_collection")
                    else existing_base
                )
            else:
                merged = "mixed_constructed"
            if existing != merged:
                receiver_kinds[key] = merged
                return True
        elif isinstance(target, (ast.Tuple, ast.List)):
            element_kind = kind.removesuffix("_collection")
            updated = False
            for element in target.elts:
                updated = bind_receiver_name(element, element_kind) or updated
            return updated
        return False

    def bind_callable_name(target: ast.AST, kind: str, *, owner: ast.AST | None = None) -> bool:
        if not isinstance(target, ast.Name):
            return False
        key = (id(owner if owner is not None else scope_owner(target)), target.id)
        existing = callable_return_kinds.get(key)
        if existing is None:
            callable_return_kinds[key] = kind
            return True
        if existing == kind:
            return False
        existing_base = existing.removesuffix("_collection")
        kind_base = kind.removesuffix("_collection")
        merged = existing_base if existing_base == kind_base else "mixed_constructed"
        if existing != merged:
            callable_return_kinds[key] = merged
            return True
        return False

    changed = True
    while changed:
        changed = False
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for argument in (*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs):
                    annotation = argument.annotation
                    if annotation is None:
                        continue
                    kind = CONSTRUCTED_RECEIVER_TYPES.get(_dotted(annotation, aliases) or "")
                    if kind is not None:
                        changed = bind_receiver_name(argument, kind) or changed
                returned_kinds = {
                    receiver_kind(candidate.value)
                    for candidate in ast.walk(node)
                    if isinstance(candidate, ast.Return)
                    and candidate.value is not None
                    and scope_owner(candidate) is node
                }
                returned_kinds.discard(None)
                if returned_kinds:
                    merged = returned_kinds.pop()
                    if returned_kinds:
                        merged = "mixed_constructed"
                    definition_parent = parents.get(node)
                    definition_owner = (
                        scope_owner(definition_parent) if definition_parent is not None else tree
                    )
                    changed = (
                        bind_callable_name(
                            ast.Name(id=node.name, ctx=ast.Store()), merged, owner=definition_owner
                        )
                        or changed
                    )
            elif isinstance(node, (ast.Assign, ast.AnnAssign)) and node.value is not None:
                targets = node.targets if isinstance(node, ast.Assign) else (node.target,)
                callable_kind = None
                if isinstance(node.value, ast.Lambda):
                    callable_kind = receiver_kind(node.value.body)
                elif isinstance(node.value, ast.Name):
                    callable_kind = callable_name_kind(node.value)
                if callable_kind is not None:
                    for target in targets:
                        changed = bind_callable_name(target, callable_kind) or changed
                kind = receiver_kind(node.value)
                if kind is None:
                    continue
                for target in targets:
                    changed = bind_receiver_name(target, kind) or changed
            elif isinstance(node, (ast.For, ast.AsyncFor)):
                kind = receiver_kind(node.iter)
                if kind is not None:
                    changed = bind_receiver_name(node.target, kind.removesuffix("_collection")) or changed
            elif isinstance(node, ast.comprehension):
                kind = receiver_kind(node.iter)
                if kind is not None:
                    changed = bind_receiver_name(node.target, kind.removesuffix("_collection")) or changed

    def enclosing_statement(node: ast.AST) -> ast.stmt | None:
        current: ast.AST | None = node
        while current is not None:
            if isinstance(current, ast.stmt):
                return current
            current = parents.get(current)
        return None

    def statement_sha256(node: ast.AST) -> str | None:
        statement = enclosing_statement(node)
        if statement is None:
            return None
        return _canonical_ast_sha256(statement)

    def module_statement(node: ast.AST) -> ast.stmt | None:
        current: ast.AST | None = node
        while current is not None and parents.get(current) is not tree:
            current = parents.get(current)
        return current if isinstance(current, ast.stmt) else None

    def reviewed_module_context(node: ast.AST, index: int, digest: str) -> bool:
        statement = module_statement(node)
        return (
            statement is not None
            and 0 <= index < len(tree.body)
            and tree.body[index] is statement
            and _canonical_ast_sha256(statement) == digest
        )

    def reviewed_function_statement_context(
        node: ast.AST,
        *,
        function_name: str,
        function_digest: str,
        statement_index: int,
    ) -> bool:
        function = enclosing_function(node)
        return (
            function is not None
            and function.name == function_name
            and parents.get(function) is tree
            and _canonical_ast_sha256(function) == function_digest
            and 0 <= statement_index < len(function.body)
            and function.body[statement_index] is enclosing_statement(node)
        )

    def reviewed_authority_root_definition(node: ast.Name) -> bool:
        expected = REVIEWED_AUTHORITY_ROOT_ASSIGNMENTS.get(node.id)
        return (
            role == "firewall_authority"
            and expected is not None
            and reviewed_module_context(node, expected[0], expected[1])
        )

    reserved_runtime_names = {
        "__builtins__",
        "__file__",
        "__loader__",
        "__name__",
        "__package__",
        "__spec__",
    }
    reserved_authority_roots = set(REVIEWED_AUTHORITY_ROOT_ASSIGNMENTS)
    reserved_bindings = imported_bindings | reserved_runtime_names | reserved_authority_roots
    for binding in ast.walk(tree):
        if isinstance(binding, ast.Name) and isinstance(binding.ctx, (ast.Store, ast.Del)):
            if binding.id in reserved_bindings and not reviewed_authority_root_definition(binding):
                issues.append(f"RESERVED_NAME_REBINDING_FORBIDDEN:{binding.id}")
        elif isinstance(binding, ast.arg) and binding.arg in reserved_bindings:
            issues.append(f"RESERVED_NAME_ARGUMENT_SHADOW_FORBIDDEN:{binding.arg}")
        elif isinstance(binding, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if binding.name in reserved_bindings:
                issues.append(f"RESERVED_NAME_DEFINITION_FORBIDDEN:{binding.name}")
        elif isinstance(binding, (ast.Global, ast.Nonlocal)):
            for name in binding.names:
                if name in reserved_bindings:
                    issues.append(f"RESERVED_NAME_SCOPE_DECLARATION_FORBIDDEN:{name}")
        elif isinstance(binding, ast.ExceptHandler) and binding.name in reserved_bindings:
            issues.append(f"RESERVED_NAME_EXCEPTION_BINDING_FORBIDDEN:{binding.name}")
        elif isinstance(binding, ast.MatchAs) and binding.name in reserved_bindings:
            issues.append(f"RESERVED_NAME_PATTERN_BINDING_FORBIDDEN:{binding.name}")
        elif isinstance(binding, ast.MatchStar) and binding.name in reserved_bindings:
            issues.append(f"RESERVED_NAME_PATTERN_BINDING_FORBIDDEN:{binding.name}")
        elif isinstance(binding, ast.MatchMapping) and binding.rest in reserved_bindings:
            issues.append(f"RESERVED_NAME_PATTERN_BINDING_FORBIDDEN:{binding.rest}")
        elif isinstance(binding, ast.alias):
            local = binding.asname or binding.name.split(".")[0]
            parent = parents.get(binding)
            reviewed_root_import = (
                isinstance(parent, ast.ImportFrom)
                and _resolved_from_module(parent) == f"{CURRENT_PACKAGE}.firewall"
                and binding.asname is None
                and binding.name == local
                and local
                in ALLOWED_FROM_IMPORT_SYMBOLS_BY_ROLE[role].get(f"{CURRENT_PACKAGE}.firewall", set())
            )
            if (local in reserved_runtime_names or local in reserved_authority_roots) and not (
                reviewed_root_import
            ):
                issues.append(f"RESERVED_NAME_IMPORT_BINDING_FORBIDDEN:{local}")
            if (
                import_binding_counts.get(local, 0) != 1
                and len(import_binding_targets.get(local, set())) != 1
            ):
                issues.append(f"DUPLICATE_IMPORT_BINDING_FORBIDDEN:{local}")

    def builtin_call_name(call: ast.Call) -> str | None:
        called = _dotted(call.func, aliases) or ""
        return called if called in KNOWN_BUILTIN_REFERENCES else None

    def reviewed_sensitive_builtin_call(call: ast.Call, name: str) -> bool:
        if name == "id":
            return role == "firewall_authority" and _canonical_ast_sha256(call) in REVIEWED_ID_CALL_SHA256
        if name != "type" or len(call.args) != 1 or call.keywords:
            return False
        parent = parents.get(call)
        if isinstance(parent, ast.Compare):
            return all(
                isinstance(operator, (ast.In, ast.Is, ast.IsNot, ast.NotIn)) for operator in parent.ops
            )
        return isinstance(parent, ast.Attribute) and parent.attr == "__name__"

    def reviewed_builtin_name_reference(node: ast.Name, name: str) -> bool:
        if name not in {"id", "type"}:
            return True
        parent = parents.get(node)
        return (
            isinstance(parent, ast.Call)
            and parent.func is node
            and reviewed_sensitive_builtin_call(parent, name)
        )

    def enclosing_function(node: ast.AST) -> ast.FunctionDef | ast.AsyncFunctionDef | None:
        current = parents.get(node)
        while current is not None:
            if isinstance(current, (ast.FunctionDef, ast.AsyncFunctionDef)):
                return current
            current = parents.get(current)
        return None

    def reviewed_constructed_receiver_use(node: ast.AST, kind: str) -> bool:
        digest = statement_sha256(node)
        if role == "composition" and kind == "path":
            index, context_digest = REVIEWED_CONSTRUCTOR_CONTEXT["composition_path_bootstrap"]
            return digest == REVIEWED_CONSTRUCTOR_USE_STATEMENT_SHA256[
                "composition_path_bootstrap"
            ] and reviewed_module_context(node, index, context_digest)
        if role == "focused_test" and kind == "cli_runner":
            if digest == REVIEWED_CONSTRUCTOR_USE_STATEMENT_SHA256["focused_runner_assignment"]:
                index, context_digest = REVIEWED_CONSTRUCTOR_CONTEXT["focused_runner_assignment"]
                return reviewed_module_context(node, index, context_digest)
            for key in ("focused_status_invoke", "focused_verify_invoke"):
                if digest != REVIEWED_CONSTRUCTOR_USE_STATEMENT_SHA256[key]:
                    continue
                statement_index, function_name, function_digest = REVIEWED_CONSTRUCTOR_CONTEXT[key]
                return reviewed_function_statement_context(
                    node,
                    function_name=function_name,
                    function_digest=function_digest,
                    statement_index=statement_index,
                )
            return False
        if role == "focused_test" and kind == "path":
            if digest != REVIEWED_CONSTRUCTOR_USE_STATEMENT_SHA256["focused_material_path_refusal"]:
                return False
            _, function_name, function_digest = REVIEWED_CONSTRUCTOR_CONTEXT["focused_material_path_refusal"]
            function = enclosing_function(node)
            statement = enclosing_statement(node)
            return (
                function is not None
                and function.name == function_name
                and parents.get(function) is tree
                and _canonical_ast_sha256(function) == function_digest
                and len(function.body) == 1
                and isinstance(function.body[0], ast.With)
                and len(function.body[0].body) == 1
                and function.body[0].body[0] is statement
            )
        if role != "firewall_authority" or kind != "path":
            return False
        function = enclosing_function(node)
        if function is not None:
            reviewed = REVIEWED_AUTHORITY_FUNCTION_AST_SHA256.get(function.name)
            return reviewed is not None and _canonical_ast_sha256(function) == reviewed
        if any(
            reviewed_module_context(node, index, root_digest)
            for index, root_digest in REVIEWED_AUTHORITY_ROOT_ASSIGNMENTS.values()
        ):
            return True
        assertion_index, assertion_digest = REVIEWED_RUNTIME_ROOT_ASSERTION
        return reviewed_module_context(node, assertion_index, assertion_digest)

    def reviewed_constructor_symbol_reference(node: ast.Name, kind: str) -> bool:
        parent = parents.get(node)
        if isinstance(parent, ast.Call) and parent.func is node:
            return reviewed_constructed_receiver_use(parent, kind)
        if role != "firewall_authority":
            return False
        function = enclosing_function(node)
        if function is None:
            return False
        reviewed = REVIEWED_AUTHORITY_FUNCTION_AST_SHA256.get(function.name)
        if reviewed is None or _canonical_ast_sha256(function) != reviewed:
            return False
        current: ast.AST = node
        while current is not function:
            annotation_parent = parents.get(current)
            if annotation_parent is None:
                return False
            if isinstance(annotation_parent, ast.arg) and annotation_parent.annotation is current:
                return True
            if (
                annotation_parent is function
                and isinstance(function, (ast.FunctionDef, ast.AsyncFunctionDef))
                and function.returns is current
            ):
                return True
            current = annotation_parent
        return False

    def receiver_base_kind(kind: str | None) -> str | None:
        return kind.removesuffix("_collection") if kind is not None else None

    def attribute_receiver_kind(node: ast.Attribute) -> str | None:
        kind = receiver_base_kind(receiver_kind(node.value))
        if kind == "cli_result":
            return "cli_result" if node.attr == "runner" else None
        return kind

    def call_receiver_kind(node: ast.Call) -> str | None:
        called = _dotted(node.func, aliases) or ""
        constructed = CONSTRUCTED_RECEIVER_TYPES.get(called)
        if constructed is not None:
            return constructed
        if called.rsplit(".", 1)[-1] == "_material_path":
            return "path"
        if isinstance(node.func, ast.Attribute):
            return attribute_receiver_kind(node.func)
        if isinstance(node.func, ast.Name):
            return receiver_base_kind(receiver_name_kind(node.func))
        return None

    def reviewed_authority_filesystem_call(call: ast.Call) -> bool:
        if role != "firewall_authority":
            return False
        function = enclosing_function(call)
        if function is not None:
            reviewed = REVIEWED_AUTHORITY_FUNCTION_AST_SHA256.get(function.name)
            if reviewed is None:
                return False
            observed = _canonical_ast_sha256(function)
            return observed == reviewed
        if any(
            reviewed_module_context(call, index, root_digest)
            for index, root_digest in REVIEWED_AUTHORITY_ROOT_ASSIGNMENTS.values()
        ):
            return True
        assertion_index, assertion_digest = REVIEWED_RUNTIME_ROOT_ASSERTION
        if reviewed_module_context(call, assertion_index, assertion_digest):
            return True
        parent = parents.get(call)
        grandparent = parents.get(parent) if parent is not None else None
        return (
            isinstance(call.func, ast.Attribute)
            and call.func.attr == "resolve"
            and isinstance(call.func.value, ast.Call)
            and (_dotted(call.func.value.func, aliases) or "") == "pathlib.Path"
            and len(call.func.value.args) == 1
            and isinstance(call.func.value.args[0], ast.Name)
            and call.func.value.args[0].id == "__file__"
            and not call.func.value.keywords
            and isinstance(parent, ast.Attribute)
            and parent.attr == "parent"
            and isinstance(grandparent, ast.Assign)
            and len(grandparent.targets) == 1
            and isinstance(grandparent.targets[0], ast.Name)
            and grandparent.targets[0].id == "PACKAGE_DIR"
        )

    def allowed_capability_call(call: ast.Call) -> bool:
        called = _dotted(call.func, aliases)
        if called is None:
            return False
        if called in SAFE_CAPABILITY_CALLS_BY_ROLE[role]:
            return True
        tail = called.rsplit(".", 1)[-1]
        if tail not in FORBIDDEN_CAPABILITY_ATTRIBUTES:
            return True
        if tail not in ALLOWED_IO_PROCESS_CALLS_BY_ROLE[role]:
            return False
        if role == "firewall_authority":
            return reviewed_authority_filesystem_call(call)
        if role == "composition" and tail == "resolve":
            return reviewed_constructed_receiver_use(call, "path")
        return True

    def controlled_namespace_attribute_allowed(node: ast.Attribute, resolved: str) -> bool:
        if resolved not in CONTROLLED_NAMESPACE_ATTRIBUTES_BY_ROLE[role]:
            return False
        if resolved not in {"sys.path", "sys.path.insert"}:
            return True
        return role == "composition" and reviewed_constructed_receiver_use(node, "path")

    def capability_reference(expression: ast.AST) -> bool:
        for item in ast.walk(expression):
            if isinstance(item, ast.Name):
                if (
                    item.id in {"__builtins__", "builtins"}
                    or item.id in FORBIDDEN_BUILTIN_REFERENCES
                    or item.id in tainted
                ):
                    return True
                resolved_name = aliases.get(item.id, item.id)
                parent = parents.get(item)
                if resolved_name in CONTROLLED_NAMESPACE_ROOTS and not (
                    isinstance(parent, ast.Attribute) and parent.value is item
                ):
                    return True
                if (
                    item.id.startswith("__")
                    and item.id.endswith("__")
                    and item.id not in ALLOWED_DUNDER_NAMES
                ):
                    return True
            if isinstance(item, ast.Attribute):
                parent = parents.get(item)
                direct_call = isinstance(parent, ast.Call) and parent.func is item
                constructed_kind = attribute_receiver_kind(item)
                if constructed_kind is not None and not reviewed_constructed_receiver_use(
                    item, constructed_kind
                ):
                    return True
                if item.attr in REFLECTION_NAMES:
                    return True
                if (
                    item.attr.startswith("__")
                    and item.attr.endswith("__")
                    and item.attr not in ALLOWED_DUNDER_NAMES
                ):
                    return True
                if item.attr in FORBIDDEN_CAPABILITY_ATTRIBUTES and not (
                    direct_call and allowed_capability_call(parent)
                ):
                    return True
                resolved = _dotted(item, aliases) or ""
                if resolved.split(".", 1)[
                    0
                ] in CONTROLLED_NAMESPACE_ROOTS and not controlled_namespace_attribute_allowed(
                    item, resolved
                ):
                    return True
                if resolved.casefold() == "sys.modules" or resolved.casefold().startswith(
                    ("sys.argv", "sys.stdin", "sys.stdout", "sys.stderr")
                ):
                    return True
            if isinstance(item, ast.Call):
                constructed_kind = call_receiver_kind(item)
                if constructed_kind is not None and not reviewed_constructed_receiver_use(
                    item, constructed_kind
                ):
                    return True
                resolved = _dotted(item.func, aliases) or ""
                tail = resolved.rsplit(".", 1)[-1]
                if (
                    tail in REFLECTION_NAMES
                    or _compact(resolved).endswith("importmodule")
                    or (tail in FORBIDDEN_CAPABILITY_ATTRIBUTES and not allowed_capability_call(item))
                ):
                    return True
                if tail in HIGHER_ORDER_TRANSPORT_NAMES and any(
                    capability_reference(argument)
                    for argument in (*item.args, *(keyword.value for keyword in item.keywords))
                ):
                    return True
        return False

    changed = True
    while changed:
        changed = False
        for node in ast.walk(tree):
            if not isinstance(node, (ast.Assign, ast.AnnAssign)) or node.value is None:
                continue
            rendered = _static_string(node.value, static_strings)
            if capability_reference(node.value) or (rendered is not None and _contains_forbidden(rendered)):
                for name in _assigned_names(node):
                    if name not in tainted:
                        tainted.add(name)
                        changed = True

    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            resolved_constructor = _dotted(node, aliases) or ""
            constructed_symbol_kind = CONSTRUCTED_RECEIVER_TYPES.get(resolved_constructor)
            if constructed_symbol_kind is not None and not reviewed_constructor_symbol_reference(
                node, constructed_symbol_kind
            ):
                issues.append(f"CONSTRUCTOR_CAPABILITY_SYMBOL_FORBIDDEN:{resolved_constructor}")
            resolved_builtin = _dotted(node, aliases) or node.id
            builtin_name = resolved_builtin if resolved_builtin in KNOWN_BUILTIN_REFERENCES else None
            if builtin_name is not None:
                if builtin_name not in ALLOWED_BUILTIN_REFERENCES_BY_ROLE[role]:
                    issues.append(f"BUILTIN_REFERENCE_NOT_ALLOWLISTED:{builtin_name}")
                elif not reviewed_builtin_name_reference(node, builtin_name):
                    issues.append(f"BUILTIN_VALUE_CONTEXT_NOT_ALLOWLISTED:{builtin_name}")
            if node.id in {"__builtins__", "builtins"}:
                issues.append(f"REFLECTIVE_NAMESPACE_FORBIDDEN:{node.id}")
            if node.id in FORBIDDEN_BUILTIN_REFERENCES:
                issues.append(f"BUILTIN_CAPABILITY_REFERENCE_FORBIDDEN:{node.id}")
            if node.id in tainted:
                issues.append(f"TAINTED_VALUE_REFERENCE_FORBIDDEN:{node.id}")
            resolved_name = aliases.get(node.id, node.id)
            parent = parents.get(node)
            if resolved_name in CONTROLLED_NAMESPACE_ROOTS and not (
                isinstance(parent, ast.Attribute) and parent.value is node
            ):
                issues.append(f"CONTROLLED_NAMESPACE_VALUE_FORBIDDEN:{resolved_name}")
            if node.id.startswith("__") and node.id.endswith("__") and node.id not in ALLOWED_DUNDER_NAMES:
                issues.append(f"DUNDER_REFLECTION_FORBIDDEN:{node.id}")
        elif isinstance(node, ast.Attribute):
            parent = parents.get(node)
            direct_call = isinstance(parent, ast.Call) and parent.func is node
            constructed_kind = attribute_receiver_kind(node)
            if constructed_kind is not None and not reviewed_constructed_receiver_use(node, constructed_kind):
                issues.append(f"CONSTRUCTED_RECEIVER_ATTRIBUTE_FORBIDDEN:{constructed_kind}:{node.attr}")
            if node.attr in REFLECTION_NAMES:
                issues.append(f"REFLECTION_ATTRIBUTE_FORBIDDEN:{node.attr}")
            if (
                node.attr.startswith("__")
                and node.attr.endswith("__")
                and node.attr not in ALLOWED_DUNDER_NAMES
            ):
                issues.append(f"DUNDER_REFLECTION_FORBIDDEN:{node.attr}")
            if node.attr in FORBIDDEN_CAPABILITY_ATTRIBUTES and not (
                direct_call and allowed_capability_call(parent)
            ):
                issues.append(f"CAPABILITY_ATTRIBUTE_REFERENCE_FORBIDDEN:{node.attr}")
            resolved = (_dotted(node, aliases) or "").casefold()
            if resolved.split(".", 1)[
                0
            ] in CONTROLLED_NAMESPACE_ROOTS and not controlled_namespace_attribute_allowed(
                node, _dotted(node, aliases) or ""
            ):
                issues.append(f"CONTROLLED_NAMESPACE_ATTRIBUTE_FORBIDDEN:{resolved}")
            if resolved == "sys.modules":
                issues.append("GLOBAL_MODULE_TABLE_FORBIDDEN:sys.modules")
            if resolved.startswith(("sys.argv", "sys.stdin", "sys.stdout", "sys.stderr")):
                issues.append(f"PROCESS_STREAM_OR_ARGUMENT_FORBIDDEN:{resolved}")
        elif isinstance(node, ast.Subscript):
            if capability_reference(node.value):
                issues.append("REFLECTIVE_SUBSCRIPT_FORBIDDEN")
            rendered = _static_string(node.slice, static_strings)
            if rendered is not None and (
                _contains_forbidden(rendered)
                or _compact(rendered) in {_compact(name) for name in REFLECTION_NAMES}
            ):
                issues.append(f"FORBIDDEN_SUBSCRIPT_TARGET:{rendered}")
        elif isinstance(node, ast.Call):
            constructed_kind = call_receiver_kind(node)
            if constructed_kind is not None and not reviewed_constructed_receiver_use(node, constructed_kind):
                issues.append(f"CONSTRUCTED_RECEIVER_CALL_FORBIDDEN:{constructed_kind}")
            called = _dotted(node.func, aliases)
            if called is None:
                issues.append("DYNAMIC_CALL_TARGET_FORBIDDEN")
            else:
                builtin_name = builtin_call_name(node)
                if builtin_name is not None:
                    if builtin_name not in ALLOWED_BUILTIN_CALLS_BY_ROLE[role]:
                        issues.append(f"BUILTIN_CALL_NOT_ALLOWLISTED:{builtin_name}")
                    elif builtin_name in {"id", "type"} and not reviewed_sensitive_builtin_call(
                        node, builtin_name
                    ):
                        issues.append(f"BUILTIN_CALL_CONTEXT_NOT_ALLOWLISTED:{builtin_name}")
                tail = called.rsplit(".", 1)[-1]
                if tail in REFLECTION_NAMES or _compact(called).endswith("importmodule"):
                    issues.append(f"REFLECTION_CALL_FORBIDDEN:{called}")
                if tail in FORBIDDEN_IO_PROCESS_CALLS and not allowed_capability_call(node):
                    issues.append(f"IO_PROCESS_CALL_FORBIDDEN:{called}")
                if tail in FORBIDDEN_CAPABILITY_ATTRIBUTES and not allowed_capability_call(node):
                    issues.append(f"CAPABILITY_CALL_FORBIDDEN:{called}")
                if _contains_forbidden(called):
                    issues.append(f"FORBIDDEN_CALL:{called}")
                if isinstance(node.func, ast.Name) and node.func.id in tainted:
                    issues.append(f"TAINTED_CALLABLE_FORBIDDEN:{node.func.id}")
                if tail in HIGHER_ORDER_TRANSPORT_NAMES and any(
                    capability_reference(argument)
                    for argument in (*node.args, *(keyword.value for keyword in node.keywords))
                ):
                    issues.append(f"HIGHER_ORDER_CAPABILITY_TRANSPORT_FORBIDDEN:{called}")
                if tail in {"asend", "send"} and any(
                    receiver_kind(argument) is not None
                    for argument in (*node.args, *(keyword.value for keyword in node.keywords))
                ):
                    issues.append(f"CONTROLLED_GENERATOR_SEND_FORBIDDEN:{called}")
            for argument in (*node.args, *(keyword.value for keyword in node.keywords)):
                rendered = _static_string(argument, static_strings)
                if (
                    role not in {"firewall_authority", "focused_test"}
                    and rendered is not None
                    and _contains_forbidden(rendered)
                ):
                    issues.append(f"FORBIDDEN_STRING_TARGET:{rendered}")
        elif isinstance(node, (ast.Yield, ast.YieldFrom)):
            if node.value is not None and receiver_kind(node.value) is not None:
                issues.append("CONTROLLED_VALUE_YIELD_FORBIDDEN")
        elif isinstance(node, ast.Return):
            if node.value is not None and receiver_kind(node.value) is not None:
                function = enclosing_function(node)
                reviewed_authority_return = (
                    role == "firewall_authority"
                    and function is not None
                    and function.name
                    in {
                        "_is_reparse",
                        "_material_path",
                        "_scan_material_snapshot",
                    }
                    and _canonical_ast_sha256(function)
                    == REVIEWED_AUTHORITY_FUNCTION_AST_SHA256[function.name]
                )
                if not reviewed_authority_return:
                    owner_name = function.name if function is not None else "MODULE"
                    issues.append(f"CONTROLLED_VALUE_RETURN_FORBIDDEN:{owner_name}")
        elif isinstance(node, ast.Lambda):
            if receiver_kind(node.body) is not None:
                issues.append("CONTROLLED_VALUE_LAMBDA_RETURN_FORBIDDEN")
        elif isinstance(node, ast.ClassDef):
            for base in node.bases:
                resolved_base = _dotted(base, aliases) or ""
                if resolved_base in CONSTRUCTED_RECEIVER_TYPES or receiver_base_kind(receiver_kind(base)) in {
                    "path",
                    "cli_runner",
                }:
                    issues.append(f"CAPABILITY_CONSTRUCTOR_SUBCLASS_FORBIDDEN:{resolved_base}")
        elif (
            role not in {"firewall_authority", "focused_test"}
            and isinstance(node, ast.Constant)
            and type(node.value) is str
            and _contains_forbidden(node.value)
        ):
            issues.append("FORBIDDEN_STRING_LITERAL")
    for name in tainted:
        issues.append(f"REFLECTIVE_VALUE_FLOW_FORBIDDEN:{name}")
    return tuple(sorted(set(issues)))


def analyze_source_text(
    text: str,
    *,
    role: str,
) -> tuple[str, ...]:
    """Refuse publication authority for arbitrary caller-supplied source.

    The guarded material inventory reads reviewed disk paths itself and invokes
    the private semantic analyzer.  Callers cannot turn synthetic bytes or a
    self-declared digest into reviewed source identity.
    """

    return ("UNREVIEWED_SOURCE_IDENTITY",)


def _is_reparse(path: Path) -> bool:
    reviewed_components = {
        SIM_ROOT.joinpath(*PurePosixPath(relative).parts[:depth])
        for relative in REVIEWED_MATERIAL_RELATIVE_PATHS
        for depth in range(1, len(PurePosixPath(relative).parts) + 1)
    }
    if path not in reviewed_components:
        raise ValueError("reparse check path is outside reviewed material components")
    return path.is_symlink() or path.resolve(strict=True) != (path.parent.resolve(strict=True) / path.name)


def _material_path(relative: str) -> Path:
    if type(relative) is not str or relative not in REVIEWED_MATERIAL_RELATIVE_PATHS:
        raise ValueError("material path is not an exact reviewed inventory member")
    pure = PurePosixPath(relative)
    if pure.is_absolute() or not pure.parts or any(part in {"", ".", ".."} for part in pure.parts):
        raise ValueError("material path must be canonical SIM-root-relative POSIX")
    lexical = SIM_ROOT.joinpath(*pure.parts)
    current = SIM_ROOT
    for part in pure.parts:
        current = current / part
        if _is_reparse(current):
            raise ValueError(f"material path contains reparse component: {relative}")
    resolved = lexical.resolve(strict=True)
    resolved.relative_to(SIM_ROOT.resolve(strict=True))
    return resolved


def analyze_reviewed_source(relative: str, *, role: str) -> tuple[str, ...]:
    """Analyze only an exact inventory-owned disk source.

    Callers provide neither source bytes nor a digest nor a capability token.
    This is non-authoritative defense-in-depth: dual-reviewer raw hashes and the
    later external Git-index SOURCE_LOCK bind publication source identity.
    """

    if type(relative) is not str or type(role) is not str:
        return ("UNREVIEWED_SOURCE_IDENTITY",)
    if (role, relative, "python") not in MATERIAL_FILES:
        return ("UNREVIEWED_SOURCE_IDENTITY",)
    try:
        path = _material_path(relative)
        raw = path.read_bytes()
        text = _canonical_text(raw)
    except (OSError, RuntimeError, TypeError, ValueError):
        return ("UNREVIEWED_SOURCE_IDENTITY",)
    return _analyze_source_semantics(text, role=role)


def _scan_material_snapshot(
    path: Path,
    *,
    role: str,
    kind: str,
) -> tuple[bytes, tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
    """Read once and derive every content-dependent result from that snapshot."""

    raw = path.read_bytes()
    text = _canonical_text(raw)
    import_targets: tuple[str, ...] = ()
    import_issues: tuple[str, ...] = ()
    firewall_issues: tuple[str, ...] = ()
    if kind == "python":
        tree = ast.parse(text)
        import_targets = tuple(target for _, target in _import_records(tree))
        import_issues = tuple(sorted(set(_import_issues(tree, role=role))))
        firewall_issues = _analyze_source_semantics(text, role=role)
    return raw, import_targets, import_issues, firewall_issues


def source_firewall_record(*, _loaded_module_path: Path = _RUNTIME_MODULE_PATH) -> object:
    actual_runtime_path = Path(__file__).resolve(strict=True)
    if (
        type(_loaded_module_path) is not type(actual_runtime_path)
        or type(PACKAGE_DIR) is not type(actual_runtime_path)
        or type(SIM_ROOT) is not type(actual_runtime_path)
        or _loaded_module_path != actual_runtime_path
        or _RUNTIME_MODULE_PATH != actual_runtime_path
        or actual_runtime_path != PACKAGE_DIR / "firewall.py"
        or PACKAGE_DIR != actual_runtime_path.parent
        or SIM_ROOT != PACKAGE_DIR.parents[1]
    ):
        raise RuntimeError("material authority roots changed before inventory read")
    if type(MATERIAL_FILES) is not tuple or not all(
        type(item) is tuple and len(item) == 3 and all(type(member) is str for member in item)
        for item in MATERIAL_FILES
    ):
        raise RuntimeError("material inventory schema changed before inventory read")
    path_payload = tuple((role, relative, kind) for role, relative, kind in MATERIAL_FILES)
    if canonical_exact_sha256(path_payload) != (
        "c0f4c5bdd84a8f340ed50fac29e00727dcea7193dadc0780e91779ad17b065b2"
    ):
        raise RuntimeError("material inventory digest changed before inventory read")
    if (
        type(REVIEWED_MATERIAL_RELATIVE_PATHS) is not frozenset
        or not all(type(relative) is str for relative in REVIEWED_MATERIAL_RELATIVE_PATHS)
        or canonical_exact_sha256(tuple(sorted(REVIEWED_MATERIAL_RELATIVE_PATHS)))
        != "6679ec48ba6dab899f18654dedcc2105dcd631d6915bfb27201707afc80fad83"
    ):
        raise RuntimeError("reviewed material membership changed before inventory read")
    if type(ROLE_FILES) is not dict or not all(
        type(role) is str and type(names) is tuple and all(type(name) is str for name in names)
        for role, names in ROLE_FILES.items()
    ):
        raise RuntimeError("role inventory schema changed before inventory read")
    if canonical_exact_sha256(tuple((role, names) for role, names in ROLE_FILES.items())) != (
        "70aff81b5e9f5d5d82b9bae952c5d78634219d29e00d717812df642c5e1d74e6"
    ):
        raise RuntimeError("role inventory digest changed before inventory read")
    if (
        type(EXPECTED_PACKAGE_FILE_NAMES) is not tuple
        or not all(type(name) is str for name in EXPECTED_PACKAGE_FILE_NAMES)
        or canonical_exact_sha256(EXPECTED_PACKAGE_FILE_NAMES)
        != "c876c998e2c7574f86dede2f73c4f4169109cd50888b45a1308b4f075e9fbf98"
    ):
        raise RuntimeError("package inventory changed before inventory read")
    path_digest = canonical_exact_sha256(path_payload)
    records = []
    role_import_targets: dict[str, set[str]] = {role: set() for role in ROLE_FILES}
    for role, relative, kind in MATERIAL_FILES:
        path = _material_path(relative)
        raw, import_targets, import_issues, firewall_issues = _scan_material_snapshot(
            path,
            role=role,
            kind=kind,
        )
        syntax_issues: tuple[str, ...] = ()
        if kind == "python":
            role_import_targets[role].update(import_targets)
        records.append(
            {
                "role": role,
                "relative_path": relative,
                "kind": kind,
                "ordinary_file": path.is_file() and not _is_reparse(path),
                "size": len(raw),
                "sha256_raw": hashlib.sha256(raw).hexdigest(),
                "syntax_issues": syntax_issues,
                "import_targets": import_targets,
                "import_issues": import_issues,
                "firewall_issues": firewall_issues,
            }
        )
    package_entries = tuple(PACKAGE_DIR.iterdir())
    package_file_names = tuple(sorted(item.name for item in package_entries if item.is_file()))
    package_directory_names = tuple(sorted(item.name for item in package_entries if item.is_dir()))
    missing_package_files = tuple(
        name for name in EXPECTED_PACKAGE_FILE_NAMES if name not in package_file_names
    )
    unexpected_package_files = tuple(
        name for name in package_file_names if name not in EXPECTED_PACKAGE_FILE_NAMES
    )
    unexpected_package_directories = tuple(
        name for name in package_directory_names if name not in {"__pycache__", "artifacts"}
    )
    role_import_target_records = tuple(
        {
            "role": role,
            "import_targets": tuple(sorted(role_import_targets[role])),
            "import_targets_sha256": canonical_exact_sha256(tuple(sorted(role_import_targets[role]))),
        }
        for role in ROLE_FILES
    )
    record = {
        "authority": "complete_source_only_path_type_hash_inventory_plus_normalized_AST_role_firewalls",
        "content_authentication_scope": "raw_hash_inventory_nonauthoritative_until_git_index_source_lock",
        "material_path_set": path_payload,
        "material_path_set_sha256": path_digest,
        "reviewed_material_path_set_sha256": REVIEWED_MATERIAL_PATH_SET_SHA256,
        "material_path_set_matches": path_digest == REVIEWED_MATERIAL_PATH_SET_SHA256,
        "expected_package_file_names": EXPECTED_PACKAGE_FILE_NAMES,
        "package_file_names": package_file_names,
        "package_file_set_sha256": canonical_exact_sha256(package_file_names),
        "missing_package_files": missing_package_files,
        "unexpected_package_files": unexpected_package_files,
        "unexpected_package_directories": unexpected_package_directories,
        "package_file_set_matches": (
            package_file_names == EXPECTED_PACKAGE_FILE_NAMES and not unexpected_package_directories
        ),
        "artifact_directory_present": "artifacts" in package_directory_names,
        "source_lock_present": "SOURCE_LOCK.json" in package_file_names,
        "file_records": tuple(records),
        "role_import_target_records": role_import_target_records,
        "all_material_files_present_and_canonical": all(
            item["ordinary_file"] is True and not item["syntax_issues"] for item in records
        ),
        "all_python_import_closures_clean": all(not item["import_issues"] for item in records),
        "protected_role_firewalls_clean": all(not item["firewall_issues"] for item in records),
    }
    return freeze_exact_record(record)
