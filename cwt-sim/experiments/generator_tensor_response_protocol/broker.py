"""Refusal-only in-process facade plus the isolated whole-phase worker."""

from __future__ import annotations

import os
import stat
import sys
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path

from .anchors import anchor_record, authenticate_runtime_callable
from .authority import (
    DURABLE_LEDGER_ROOT_ENV,
    GIT_DIR_ENV,
    GIT_EXECUTABLE_ENV,
    GIT_INDEX_ENV,
    GIT_WORK_TREE_ENV,
    PYTHON_EXECUTABLE_ENV,
    _publish_phase_result,
    consume_phase_authorization,
    record_phase_outcome,
    verify_phase_authority_commit,
)
from .contract import (
    COMPONENT_ORDER,
    GEOMETRY_PLAN_SHA256,
    HELDOUT_AREA_VECTOR,
    NORMALIZED_CURVATURE_SCALES,
    PRODUCER_CALLABLES,
    calibration_call_plan,
    confirmation_call_plan,
    heldout_call_plan,
)
from .exact import Vector, require_fraction, require_vector, strict_equal

PACKAGE_DIR = Path(__file__).resolve().parent
SIM_ROOT = PACKAGE_DIR.parents[1]
_IMPORT_ROOTS = (
    PACKAGE_DIR,
    SIM_ROOT / "experiments/generator_tensor_prediction_protocol",
    SIM_ROOT / "experiments/loop_flux_counting_curvature_proof",
)
_FORBIDDEN_PYTHON_ENV = {
    "PYTHONHOME",
    "PYTHONINSPECT",
    "PYTHONPATH",
    "PYTHONSTARTUP",
    "PYTHONUSERBASE",
}


class TerminalAccessIncident(RuntimeError):
    """A response access began and the entire session is now terminal."""


def _assert_cache_free_import_roots() -> None:
    if (SIM_ROOT.parent / ".git").exists():
        raise PermissionError("detached response worktree contains Git metadata")
    for root in _IMPORT_ROOTS:
        if not root.is_dir() or root.is_symlink():
            raise PermissionError("detached response import root refused")
        for path in root.rglob("*"):
            info = path.lstat()
            reparse = bool(
                sys.platform == "win32" and info.st_file_attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT
            )
            if path.is_symlink() or reparse:
                raise PermissionError("detached response import root contains a link")
            if path.name == "__pycache__" or path.suffix == ".pyc":
                raise PermissionError("detached response import root contains Python cache")


def _assert_isolated_runtime_paths() -> None:
    allowed_roots = tuple(
        Path(item).resolve(strict=True) for item in {SIM_ROOT, Path(sys.prefix), Path(sys.base_prefix)}
    )
    if not sys.path or Path(sys.path[0]).resolve(strict=True) != SIM_ROOT.resolve(strict=True):
        raise PermissionError("detached response sys.path root refused")
    for item in sys.path:
        if type(item) is not str or not item or not Path(item).is_absolute():
            raise PermissionError("detached response sys.path entry refused")
        lexical = Path(item).absolute()
        if not any(lexical == root or root in lexical.parents for root in allowed_roots):
            raise PermissionError("detached response sys.path escaped reviewed roots")


@dataclass(frozen=True)
class ResponseSample:
    label: str
    center: tuple[Fraction, Fraction, Fraction]
    radius: Fraction
    orientation: int
    component_order: tuple[str, str, str]
    direct_response_one_form: Vector
    fcs_normal_connection_one_form: Vector
    raw_direct_response_curl: Vector
    raw_independent_fcs_curl: Vector
    normalized_direct_response_curl: Vector
    normalized_independent_fcs_curl: Vector


@dataclass(frozen=True)
class ExcessResponse:
    label: str
    center: tuple[Fraction, Fraction, Fraction]
    raw_direct_delta: Vector
    raw_fcs_delta: Vector
    normalized_direct_delta: Vector
    normalized_fcs_delta: Vector


_DIRECT_RECORD_KEYS = {
    "direct_response_one_form",
    "direct_response_derivative_matrix",
    "direct_response_curl_order",
    "direct_response_curl",
    "direct_response_curl_signs",
    "all_direct_response_curl_components_nonzero",
    "orientation",
}
_FCS_RECORD_KEYS = {
    "fcs_left_q_eigenvector_equation",
    "fcs_right_q_eigenvector_equation",
    "fcs_left_q_gauge",
    "fcs_right_q_gauge",
    "fcs_minus_partial_q_connection_one_form",
    "fcs_normal_connection_derivative_matrix",
    "fcs_normal_connection_curl_order",
    "fcs_normal_connection_curl",
    "fcs_normal_connection_curl_signs",
}


def _require_fraction_matrix(value: object, *, label: str) -> tuple[tuple[Fraction, ...], ...]:
    if type(value) is not list or len(value) != 3:
        raise TypeError(f"{label} matrix schema refused")
    if len({id(row) for row in value}) != 3:
        raise RuntimeError(f"{label} matrix rows alias")
    rows: list[tuple[Fraction, ...]] = []
    for row in value:
        if type(row) is not list or len(row) != 3 or any(type(item) is not Fraction for item in row):
            raise TypeError(f"{label} matrix values refused")
        rows.append(tuple(row))
    return tuple(rows)


def _numeric_container_ids(record: dict[str, object], keys: tuple[str, ...]) -> set[int]:
    result: set[int] = set()
    for key in keys:
        value = record[key]
        if type(value) in {tuple, list}:
            result.add(id(value))
            if type(value) is list:
                result.update(id(item) for item in value if type(item) in {tuple, list})
    return result


def _direct_curl_from_derivatives(matrix: tuple[tuple[Fraction, ...], ...]) -> Vector:
    return (
        matrix[2][1] - matrix[1][2],
        matrix[0][2] - matrix[2][0],
        matrix[1][0] - matrix[0][1],
    )


def _fcs_curl_from_derivatives(matrix: tuple[tuple[Fraction, ...], ...]) -> Vector:
    return (
        matrix[1][2] - matrix[2][1],
        matrix[2][0] - matrix[0][2],
        matrix[0][1] - matrix[1][0],
    )


def _validate_producer_records(
    direct_record: object,
    fcs_record: object,
    *,
    orientation: int,
) -> tuple[Vector, Vector, Vector, Vector]:
    if (
        type(direct_record) is not dict
        or set(direct_record) != _DIRECT_RECORD_KEYS
        or type(fcs_record) is not dict
        or set(fcs_record) != _FCS_RECORD_KEYS
    ):
        raise TypeError("producer record schema refused")
    if direct_record is fcs_record:
        raise RuntimeError("direct and FCS producer records alias")
    if type(direct_record["orientation"]) is not int or direct_record["orientation"] != orientation:
        raise TypeError("direct response orientation refused")
    if (
        type(direct_record["direct_response_curl_order"]) is not tuple
        or not strict_equal(direct_record["direct_response_curl_order"], COMPONENT_ORDER)
        or type(fcs_record["fcs_normal_connection_curl_order"]) is not tuple
        or not strict_equal(fcs_record["fcs_normal_connection_curl_order"], COMPONENT_ORDER)
    ):
        raise TypeError("producer curvature component order refused")
    direct_one_form = require_vector(
        direct_record["direct_response_one_form"], length=3, label="producer direct B"
    )
    direct_curl = require_vector(direct_record["direct_response_curl"], length=3, label="producer direct F")
    fcs_one_form = require_vector(
        fcs_record["fcs_minus_partial_q_connection_one_form"],
        length=3,
        label="producer FCS B",
    )
    fcs_curl = require_vector(fcs_record["fcs_normal_connection_curl"], length=3, label="producer FCS F")
    direct_derivatives = _require_fraction_matrix(
        direct_record["direct_response_derivative_matrix"], label="direct derivative"
    )
    fcs_derivatives = _require_fraction_matrix(
        fcs_record["fcs_normal_connection_derivative_matrix"], label="FCS derivative"
    )
    if not strict_equal(direct_curl, _direct_curl_from_derivatives(direct_derivatives)):
        raise RuntimeError("direct curl does not equal the antisymmetric derivative")
    if not strict_equal(fcs_curl, _fcs_curl_from_derivatives(fcs_derivatives)):
        raise RuntimeError("FCS curl does not equal the normal-connection derivative")
    direct_signs = direct_record["direct_response_curl_signs"]
    fcs_signs = fcs_record["fcs_normal_connection_curl_signs"]
    wanted_direct_signs = tuple(1 if item > 0 else -1 for item in direct_curl)
    wanted_fcs_signs = tuple(1 if item > 0 else -1 for item in fcs_curl)
    if (
        type(direct_signs) is not tuple
        or any(type(item) is not int for item in direct_signs)
        or not strict_equal(direct_signs, wanted_direct_signs)
        or type(fcs_signs) is not tuple
        or any(type(item) is not int for item in fcs_signs)
        or not strict_equal(fcs_signs, wanted_fcs_signs)
        or type(direct_record["all_direct_response_curl_components_nonzero"]) is not bool
        or direct_record["all_direct_response_curl_components_nonzero"]
        is not all(item != 0 for item in direct_curl)
    ):
        raise TypeError("producer sign/nonzero record refused")
    for key in (
        "fcs_left_q_eigenvector_equation",
        "fcs_right_q_eigenvector_equation",
        "fcs_left_q_gauge",
        "fcs_right_q_gauge",
    ):
        if type(fcs_record[key]) is not bool or fcs_record[key] is not True:
            raise RuntimeError("independent FCS eigendata identities refused")
    direct_ids = _numeric_container_ids(
        direct_record,
        (
            "direct_response_one_form",
            "direct_response_derivative_matrix",
            "direct_response_curl",
            "direct_response_curl_signs",
        ),
    )
    fcs_ids = _numeric_container_ids(
        fcs_record,
        (
            "fcs_minus_partial_q_connection_one_form",
            "fcs_normal_connection_derivative_matrix",
            "fcs_normal_connection_curl",
            "fcs_normal_connection_curl_signs",
        ),
    )
    if direct_ids & fcs_ids:
        raise RuntimeError("direct and FCS nested result containers alias")
    return direct_one_form, fcs_one_form, direct_curl, fcs_curl


def normalize_curvature(raw: object) -> Vector:
    raw = require_vector(raw, length=3, label="raw curvature")
    return tuple(raw[index] * NORMALIZED_CURVATURE_SCALES[index] for index in range(3))


def _validate_sample(
    sample: object,
    *,
    label: str,
    center: tuple[Fraction, Fraction, Fraction],
    radius: Fraction,
) -> ResponseSample:
    if type(sample) is not ResponseSample:
        raise TypeError("producer sample type refused")
    if (
        type(sample.label) is not str
        or sample.label != label
        or type(sample.center) is not tuple
        or not strict_equal(sample.center, center)
        or type(sample.radius) is not Fraction
        or sample.radius != radius
        or type(sample.orientation) is not int
        or sample.orientation != 1
        or not strict_equal(sample.component_order, COMPONENT_ORDER)
    ):
        raise TypeError("producer sample identity refused")
    direct_one_form = require_vector(sample.direct_response_one_form, length=3, label="direct B=j R X")
    fcs_one_form = require_vector(
        sample.fcs_normal_connection_one_form,
        length=3,
        label="FCS minus partial-q connection",
    )
    direct = require_vector(sample.raw_direct_response_curl, length=3, label="direct F=dB")
    fcs = require_vector(
        sample.raw_independent_fcs_curl,
        length=3,
        label="independent FCS F=-partial_q(dA)",
    )
    normalized_direct = require_vector(
        sample.normalized_direct_response_curl,
        length=3,
        label="normalized direct curvature",
    )
    normalized_fcs = require_vector(
        sample.normalized_independent_fcs_curl,
        length=3,
        label="normalized FCS curvature",
    )
    if (
        sample.direct_response_one_form is sample.fcs_normal_connection_one_form
        or sample.raw_direct_response_curl is sample.raw_independent_fcs_curl
        or sample.normalized_direct_response_curl is sample.normalized_independent_fcs_curl
    ):
        raise RuntimeError("direct and FCS lanes reused one result object")
    if not strict_equal(direct_one_form, fcs_one_form):
        raise RuntimeError("direct and independent FCS one-forms differ")
    if not strict_equal(direct, fcs):
        raise RuntimeError("direct and independent FCS curls differ")
    if (
        not strict_equal(normalized_direct, normalize_curvature(direct))
        or not strict_equal(normalized_fcs, normalize_curvature(fcs))
        or not strict_equal(normalized_direct, normalized_fcs)
    ):
        raise RuntimeError("normalized-chart curvature pullback differs")
    return sample


class LockedProducerCallable:
    """Nonauthoritative in-process placeholder; per-sample execution is impossible."""

    __slots__ = ()

    def __setattr__(self, name: str, value: object) -> None:
        del name, value
        raise AttributeError("locked producer fields are read-only")

    def __call__(self, *args: object, **kwargs: object) -> None:
        del args, kwargs
        raise PermissionError("producer execution requires the fresh whole-phase child process")

    def _call_authorized(self, *args: object, **kwargs: object) -> None:
        del args, kwargs
        raise PermissionError("in-process producer authorization is nonauthoritative")


class OneShotResponseBroker:
    """Nonauthoritative facade; only the isolated whole-phase child may execute."""

    __slots__ = ("_plan_sha256",)

    def __init__(self, *, plan_sha256: str) -> None:
        if type(plan_sha256) is not str or plan_sha256 != GEOMETRY_PLAN_SHA256:
            raise TypeError("broker construction refused")
        object.__setattr__(self, "_plan_sha256", plan_sha256)

    def __setattr__(self, name: str, value: object) -> None:
        del name, value
        raise AttributeError("response broker fields are read-only")

    @property
    def terminal(self) -> bool:
        return True

    @property
    def call_count(self) -> int:
        return 0

    @property
    def phase_call_counts(self) -> tuple[tuple[str, int], ...]:
        return ()

    def calibration_deltas(self, authorization: object) -> None:
        del authorization
        raise PermissionError("in-process broker is nonauthoritative; use the whole-phase child")

    def confirmation_deltas(self, authorization: object) -> None:
        del authorization
        raise PermissionError("in-process broker is nonauthoritative; use the whole-phase child")

    def heldout_scalar(self, authorization: object) -> None:
        del authorization
        raise PermissionError("in-process broker is nonauthoritative; use the whole-phase child")


def _execute_reviewed_phase_child(authority_commit_oid: object) -> dict[str, object]:
    """Defense-in-depth child body; only the trusted outer launcher grants authority."""

    configured_python = os.environ.get(PYTHON_EXECUTABLE_ENV)
    if (
        type(authority_commit_oid) is not str
        or sys.flags.isolated != 1
        or sys.dont_write_bytecode is not True
        or len(sys.argv) != 3
        or sys.argv[1] != "phase-child"
        or sys.argv[2] != authority_commit_oid
        or not sys.argv[0].replace("\\", "/").endswith("/generator_tensor_response_protocol/run.py")
        or any(name in os.environ for name in _FORBIDDEN_PYTHON_ENV)
        or os.environ.get("PYTHONDONTWRITEBYTECODE") != "1"
        or os.environ.get("PYTHONNOUSERSITE") != "1"
        or type(os.environ.get("PYTHONPYCACHEPREFIX")) is not str
        or type(configured_python) is not str
        or not Path(configured_python).is_absolute()
        or Path(configured_python).resolve(strict=True) != Path(sys.executable).resolve(strict=True)
        or any(
            type(os.environ.get(name)) is not str
            for name in (GIT_DIR_ENV, GIT_INDEX_ENV, GIT_WORK_TREE_ENV, GIT_EXECUTABLE_ENV)
        )
        or type(os.environ.get(DURABLE_LEDGER_ROOT_ENV)) is not str
    ):
        raise PermissionError("authoritative response execution requires a fresh isolated phase child")
    pycache_prefix = Path(os.environ["PYTHONPYCACHEPREFIX"])
    if (
        not pycache_prefix.is_absolute()
        or not pycache_prefix.is_dir()
        or pycache_prefix.is_symlink()
        or any(pycache_prefix.iterdir())
    ):
        raise PermissionError("authoritative response cache prefix refused")
    _assert_cache_free_import_roots()
    _assert_isolated_runtime_paths()
    prefix = "experiments.loop_flux_counting_curvature_proof"
    if any(name == prefix or name.startswith(prefix + ".") for name in sys.modules):
        raise PermissionError("authoritative phase child was not response-clean")
    authorization = verify_phase_authority_commit(authority_commit_oid)
    plans = {
        "CAL": calibration_call_plan(),
        "V": confirmation_call_plan(),
        "H": heldout_call_plan(),
    }
    call_plan = plans[authorization.phase]
    consume_phase_authorization(authorization)
    try:
        anchor_record()
        from experiments.loop_flux_counting_curvature_proof.counting_lane import (
            _direct_response_curl_record,
            _fcs_normal_connection_jet_record,
        )
        from experiments.loop_flux_counting_curvature_proof.generator import build_branch_bundle

        runtime_callables = (
            (build_branch_bundle, PRODUCER_CALLABLES["build_branch_bundle"]),
            (_direct_response_curl_record, PRODUCER_CALLABLES["direct_response_curl"]),
            (_fcs_normal_connection_jet_record, PRODUCER_CALLABLES["fcs_normal_connection_curl"]),
        )
        for callable_, expected in runtime_callables:
            authenticate_runtime_callable(callable_, expected)

        def sample(
            label: str,
            center: tuple[Fraction, Fraction, Fraction],
            radius: Fraction,
        ) -> ResponseSample:
            bundle = build_branch_bundle(center=center, radius=radius)
            direct_record = _direct_response_curl_record(bundle, orientation=1)
            fcs_record = _fcs_normal_connection_jet_record(bundle)
            direct_b, fcs_b, direct_f, fcs_f = _validate_producer_records(
                direct_record, fcs_record, orientation=1
            )
            direct_tuple = tuple(item for item in direct_f)
            fcs_tuple = tuple(item for item in fcs_f)
            return _validate_sample(
                ResponseSample(
                    label=label,
                    center=center,
                    radius=radius,
                    orientation=1,
                    component_order=COMPONENT_ORDER,
                    direct_response_one_form=tuple(item for item in direct_b),
                    fcs_normal_connection_one_form=tuple(item for item in fcs_b),
                    raw_direct_response_curl=direct_tuple,
                    raw_independent_fcs_curl=fcs_tuple,
                    normalized_direct_response_curl=normalize_curvature(direct_tuple),
                    normalized_independent_fcs_curl=normalize_curvature(fcs_tuple),
                ),
                label=label,
                center=center,
                radius=radius,
            )

        excess: list[ExcessResponse] = []
        sample_count = 0
        for offset in range(0, len(call_plan), 2):
            positive_spec, zero_spec = call_plan[offset : offset + 2]
            positive = sample(*positive_spec)
            zero = sample(*zero_spec)
            sample_count += 2
            raw_direct = tuple(
                a - b
                for a, b in zip(positive.raw_direct_response_curl, zero.raw_direct_response_curl, strict=True)
            )
            raw_fcs = tuple(
                a - b
                for a, b in zip(positive.raw_independent_fcs_curl, zero.raw_independent_fcs_curl, strict=True)
            )
            normalized_direct = normalize_curvature(raw_direct)
            normalized_fcs = normalize_curvature(raw_fcs)
            if not strict_equal(raw_direct, raw_fcs) or not strict_equal(normalized_direct, normalized_fcs):
                raise RuntimeError("whole-phase direct/FCS excess mismatch")
            excess.append(
                ExcessResponse(
                    label=positive.label,
                    center=positive.center,
                    raw_direct_delta=raw_direct,
                    raw_fcs_delta=raw_fcs,
                    normalized_direct_delta=normalized_direct,
                    normalized_fcs_delta=normalized_fcs,
                )
            )
        if sample_count != len(call_plan) or sample_count != len(authorization.request_ids):
            raise RuntimeError("whole-phase sample count refused")
        _assert_cache_free_import_roots()
        if any(pycache_prefix.iterdir()):
            raise RuntimeError("authoritative response cache appeared during execution")
        published_vectors = (
            () if authorization.phase == "H" else tuple(item.normalized_direct_delta for item in excess)
        )
        heldout_scalar = None
        if authorization.phase == "H":
            heldout_scalar = require_fraction(
                sum(
                    Fraction(area) * component
                    for area, component in zip(
                        HELDOUT_AREA_VECTOR,
                        excess[0].normalized_direct_delta,
                        strict=True,
                    )
                ),
                label="heldout scalar projection",
            )
        payload = {
            "schema": "generator_tensor_response_phase_result_v1",
            "phase": authorization.phase,
            "sequence": authorization.sequence,
            "session_id": authorization.session_id,
            "authority_commit_oid": authorization.authority_commit_oid,
            "authority_record_sha256": authorization.raw_sha256,
            "request_ids": authorization.request_ids,
            "sample_call_count": sample_count,
            "normalized_excess_vectors": published_vectors,
            "heldout_scalar_projection": heldout_scalar,
            "direct_fcs_crosscheck_complete": True,
        }
        result_sha256 = _publish_phase_result(authorization, payload)
        record_phase_outcome(authorization, f"{authorization.phase}_BATCH_COMPLETE")
    except BaseException:
        try:
            record_phase_outcome(authorization, "TERMINAL_INCIDENT")
        except BaseException:
            pass
        raise TerminalAccessIncident("whole-phase response access terminated") from None
    return {
        "phase": authorization.phase,
        "sample_call_count": sample_count,
        "result_sha256": result_sha256,
        "response_accessed": True,
        "requires_external_outcome_commit": True,
    }
