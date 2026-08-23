"""Source-first tests for the response-sealed generator-tensor protocol."""

from __future__ import annotations

from dataclasses import replace
from fractions import Fraction
from types import MappingProxyType

import pytest
from typer.testing import CliRunner

from experiments.generator_tensor_prediction_protocol.connection_eligibility import (
    EXPECTED_GRAM_DETERMINANT_SHA256,
    EXPECTED_HELDOUT_DENSITY_SHA256,
    EXPECTED_P0_CERTIFICATE_SHA256,
    connection_basis,
    connection_eligibility_certificate,
    predictor_curvature,
    predictor_one_form,
)
from experiments.generator_tensor_prediction_protocol.contract import (
    A_CENTERS,
    CASE_GATE_MAP,
    EXPECTED_CASE_DISPOSITIONS,
    EXPOSURE_REGISTRY,
    HELDOUT_CENTER,
    MODEL_CONTRACT,
    ORDERED_GATES,
    RESERVATION_STATUS,
    REVIEWED_EXPOSURE_REGISTRY_SHA256,
    V_CENTERS,
    contract_issues,
    exposure_registry_issues,
    exposure_registry_sha256,
)
from experiments.generator_tensor_prediction_protocol.exact import (
    fraction_vector_sha256,
    freeze_exact_record,
    rational_determinant,
)
from experiments.generator_tensor_prediction_protocol.firewall import (
    ALLOWED_BUILTIN_REFERENCES_BY_ROLE,
    KNOWN_BUILTIN_REFERENCES,
    MATERIAL_FILES,
    REVIEWED_MATERIAL_PATH_SET_SHA256,
    _analyze_source_semantics,
    _canonical_source_ast_sha256,
    _material_path,
    _scan_material_snapshot,
    analyze_reviewed_source,
    analyze_source_text,
    source_firewall_record,
)
from experiments.generator_tensor_prediction_protocol.krylov_no_go import (
    EXPECTED_CLOSURE_DETERMINANT_SHA256,
    EXPECTED_N0_CERTIFICATE_SHA256,
    krylov_no_go_certificate,
)
from experiments.generator_tensor_prediction_protocol.protocol import (
    REVIEWED_CRITERION_SHA256,
    FalsificationCriterion,
    ProtocolSession,
    canonical_protocol_record,
    criterion_issues,
    criterion_sha256,
)
from experiments.generator_tensor_prediction_protocol.response_reader_sentinel import (
    ResponseAccessBlocked,
    blocked_response_reader,
    sentinel_record,
)
from experiments.generator_tensor_prediction_protocol.run import app as run_app
from experiments.generator_tensor_prediction_protocol.theorem import (
    build_certificates,
    execute_program,
    gate_results,
)

runner = CliRunner()


def _thaw(value: object) -> object:
    if type(value) in {dict, MappingProxyType}:
        return {key: _thaw(member) for key, member in value.items()}  # type: ignore[union-attr]
    if type(value) is tuple:
        return tuple(_thaw(member) for member in value)
    return value


def _replace_record_field(record: object, name: str, value: object) -> object:
    mutable = _thaw(record)
    assert type(mutable) is dict
    mutable[name] = value
    return freeze_exact_record(mutable)


def test_contract_and_exposure_registry_are_exact_and_response_sealed() -> None:
    assert contract_issues() == ()
    assert exposure_registry_issues() == ()
    assert MODEL_CONTRACT.response_accessed is False
    assert MODEL_CONTRACT.response_unlock_available is False
    assert tuple(EXPOSURE_REGISTRY)[-9:] == (
        "A1",
        "A2",
        "A3",
        "A4",
        "A5",
        "A6",
        "V1",
        "V2",
        "H",
    )
    for name in tuple(EXPOSURE_REGISTRY)[-9:]:
        assert EXPOSURE_REGISTRY[name]["status"] == RESERVATION_STATUS
    for name in ("D1", "D2", "D3", "D4"):
        assert EXPOSURE_REGISTRY[name]["status"] == "EXPOSED_INELIGIBLE_DIAGNOSTIC"
    assert exposure_registry_sha256() == REVIEWED_EXPOSURE_REGISTRY_SHA256


@pytest.mark.parametrize(
    ("name", "field", "value"),
    (
        ("A1", "role", "reserved_heldout_oblique"),
        ("A2", "point", HELDOUT_CENTER),
        ("V1", "status", "EXPOSED_INELIGIBLE_DIAGNOSTIC"),
        ("D1", "status", RESERVATION_STATUS),
    ),
)
def test_exposure_registry_relabel_point_and_status_mutations_fail(
    name: str,
    field: str,
    value: object,
) -> None:
    forged = {key: MappingProxyType(dict(entry)) for key, entry in EXPOSURE_REGISTRY.items()}
    changed = dict(forged[name])
    changed[field] = value
    forged[name] = MappingProxyType(changed)
    assert exposure_registry_issues(MappingProxyType(forged))


@pytest.mark.parametrize(
    "mutation",
    (
        {"response_accessed": 0},
        {"response_unlock_available": True},
        {"node_count": 5.0},
        {"coordinate_scales": (Fraction(1, 50), Fraction(1, 50), 1 / 6)},
    ),
)
def test_contract_refuses_exact_type_and_value_mutations(mutation: dict) -> None:
    assert contract_issues(replace(MODEL_CONTRACT, **mutation))


def test_registry_and_gate_ownership_are_immutable_and_complete() -> None:
    assert type(EXPOSURE_REGISTRY) is MappingProxyType
    assert type(CASE_GATE_MAP) is MappingProxyType
    assert len(ORDERED_GATES) == len(set(ORDERED_GATES)) == 12
    assert set(gate for gates in CASE_GATE_MAP.values() for gate in gates) == set(ORDERED_GATES)
    assert EXPECTED_CASE_DISPOSITIONS == {
        "N0_KRYLOV3_NO_GO": "INELIGIBLE_NOT_CLOSED",
        "P0_CONNECTION_GEOMETRY_ELIGIBILITY": "ELIGIBLE_PRE_RESPONSE_ONLY",
    }


def test_krylov3_exact_closure_rank_and_reviewed_digest() -> None:
    record = krylov_no_go_certificate()
    assert type(record) is MappingProxyType
    rows = record["closure_rows"]
    determinant = rational_determinant([list(row) for row in rows])
    assert determinant > 0
    assert record["closure_rank"] == 3
    assert record["closure_nullity"] == 0
    assert record["only_closed_coefficient_vector"] == (0, 0, 0)
    assert record["classification"] == "NO_NONTRIVIAL_CLOSED_MEMBER"
    assert record["disposition"] == "INELIGIBLE_NOT_CLOSED"
    assert fraction_vector_sha256((determinant,)) == EXPECTED_CLOSURE_DETERMINANT_SHA256
    assert record["certificate_sha256"] == EXPECTED_N0_CERTIFICATE_SHA256
    assert record["reviewed_certificate_sha256_matches"] is True
    assert record["response_accessed"] is False


def test_krylov3_diagnostic_is_exposed_and_never_acceptance_authority() -> None:
    record = krylov_no_go_certificate()
    assert record["retrospective_unrestricted_3x3_status"] == "EXPOSED_INELIGIBLE_DIAGNOSTIC"
    assert record["retrospective_diagnostic_used_for_acceptance"] is False


def test_reviewed_rank_certificates_refuse_singular_systems_instead_of_fallback_labels() -> None:
    assert krylov_no_go_certificate()["closure_rank"] == 3
    assert krylov_no_go_certificate()["closure_nullity"] == 0
    assert connection_eligibility_certificate()["calibration_rank"] == 3


def test_connection_exact_rank_condition_and_digests() -> None:
    record = connection_eligibility_certificate()
    assert type(record) is MappingProxyType
    assert record["calibration_centers"] == A_CENTERS
    assert record["calibration_design_shape"] == (18, 3)
    assert record["calibration_rank"] == 3
    assert record["calibration_overdetermination"] == 15
    assert record["all_local_basis_determinants_positive"] is True
    assert record["gram_determinant"] > 0
    assert record["gram_determinant_sha256"] == EXPECTED_GRAM_DETERMINANT_SHA256
    assert record["certificate_sha256"] == EXPECTED_P0_CERTIFICATE_SHA256
    assert record["reviewed_certificate_sha256_matches"] is True
    assert record["exact_gram_infinity_condition"] < 20
    assert record["response_accessed"] is False
    assert record["coefficients_fitted"] is False


def test_certificate_records_are_fresh_and_recursively_immutable() -> None:
    first_n0 = krylov_no_go_certificate()
    second_n0 = krylov_no_go_certificate()
    first_p0 = connection_eligibility_certificate()
    second_p0 = connection_eligibility_certificate()
    assert first_n0 is not second_n0
    assert first_p0 is not second_p0
    assert type(first_p0["flux_conjugation_records"][0]) is MappingProxyType
    assert type(first_p0["calibration_basis_matrices"]) is tuple
    with pytest.raises(TypeError):
        first_n0["authority"] = "FORGED"  # type: ignore[index]
    with pytest.raises(TypeError):
        first_p0["flux_conjugation_records"][0]["center"] = HELDOUT_CENTER  # type: ignore[index]


def test_connection_basis_is_exact_rank_three_at_every_reserved_point() -> None:
    for center in (*A_CENTERS, *V_CENTERS, HELDOUT_CENTER):
        matrix = [list(row) for row in zip(*connection_basis(center), strict=True)]
        assert rational_determinant(matrix) > 0
    record = connection_eligibility_certificate()
    assert record["heldout_basis_densities_nonzero"] is True
    assert record["heldout_basis_density_sha256"] == EXPECTED_HELDOUT_DENSITY_SHA256


def test_connection_closure_covariance_units_and_nulls_are_scoped() -> None:
    record = connection_eligibility_certificate()
    assert record["basis_exterior_derivative_is_structurally_closed"] is True
    assert record["coordinate_covariance_exact"] is True
    assert record["zero_chord_Wilson_jet_zero"] is True
    assert record["count_reversal_rule"].startswith("sigma_to_minus_sigma")
    assert record["zero_current_rule"].startswith("sigma_zero")
    assert record["conjugate_bases_rank_three"] is True
    assert record["simple_flux_conjugation_parity_holds"] is False
    assert record["simple_flux_conjugation_parity_claimed"] is False
    assert len(record["flux_conjugation_records"]) == 9
    assert record["basis_scope"] == "exact_frozen_rational_points_only"
    assert record["uniform_purity_bias_derivative_box_proved"] is False
    assert record["units"]["kappa"] == "count"


def test_sigma_orientation_and_zero_current_predictor_rules_are_executable() -> None:
    record = connection_eligibility_certificate()
    sigma = record["sigma_predictor_record"]
    coefficients = sigma["coefficients"]
    center = sigma["center"]
    positive_one_form = predictor_one_form(center, coefficients, 1)
    positive_curvature = predictor_curvature(center, coefficients, 1)
    assert sigma["positive_one_form"] == positive_one_form
    assert sigma["positive_curvature"] == positive_curvature
    assert predictor_one_form(center, coefficients, -1) == tuple(-value for value in positive_one_form)
    assert predictor_curvature(center, coefficients, -1) == tuple(-value for value in positive_curvature)
    assert predictor_one_form(center, coefficients, 0) == (Fraction(0),) * 3
    assert predictor_curvature(center, coefficients, 0) == (Fraction(0),) * 3
    with pytest.raises(TypeError):
        predictor_curvature(center, coefficients, True)


def test_protocol_has_only_pre_response_transitions_and_exact_event_log() -> None:
    record = canonical_protocol_record()
    assert record["state"] == "SOURCE_REVIEW_READY"
    assert record["event_log"] == (
        "INIT",
        "EXPOSURE_FROZEN",
        "CRITERION_FROZEN",
        "SOURCE_REVIEW_READY",
    )
    assert record["source_lock_present"] is False
    assert record["cryptographically_proven_unopened"] is False
    assert record["response_accessed"] is False
    assert record["exposure_registry_sha256"] == REVIEWED_EXPOSURE_REGISTRY_SHA256
    assert record["criterion_sha256"] == REVIEWED_CRITERION_SHA256


def test_protocol_poisoning_and_criterion_types_fail_closed() -> None:
    session = ProtocolSession()
    with pytest.raises(RuntimeError, match="transition order"):
        session.mark_source_review_ready()
    assert session.record()["state"] == "POISONED"
    fresh = ProtocolSession()
    fresh.freeze_exposure_registry()
    with pytest.raises(TypeError, match="criterion type"):
        fresh.freeze_criterion(object())  # type: ignore[arg-type]
    assert fresh.record()["state"] == "POISONED"
    forged = replace(FalsificationCriterion(), response_accessed=True)
    fresh = ProtocolSession()
    fresh.freeze_exposure_registry()
    with pytest.raises(ValueError, match="criterion schema"):
        fresh.freeze_criterion(forged)


@pytest.mark.parametrize(
    "criterion",
    (
        replace(FalsificationCriterion(), heldout_area_vector=(True, -1, 3)),
        replace(FalsificationCriterion(), heldout_area_vector=(0, 0, 0)),
        replace(FalsificationCriterion(), predictor_family="pointwise fitted response tensor"),
        replace(FalsificationCriterion(), calibration_centers=V_CENTERS * 3),
        replace(FalsificationCriterion(), exact_calibration_consistency_required=1),
        replace(FalsificationCriterion(), response_accessed=True),
    ),
)
def test_criterion_exact_types_values_centers_family_and_area_are_bound(
    criterion: FalsificationCriterion,
) -> None:
    assert criterion_issues(criterion)
    with pytest.raises(ValueError, match="criterion schema"):
        criterion_sha256(criterion)
    session = ProtocolSession()
    session.freeze_exposure_registry()
    with pytest.raises(ValueError, match="criterion schema"):
        session.freeze_criterion(criterion)
    assert session.record()["state"] == "POISONED"


def test_response_reader_sentinel_always_refuses() -> None:
    with pytest.raises(ResponseAccessBlocked, match="unavailable"):
        blocked_response_reader(A_CENTERS[0])
    record = sentinel_record()
    assert record["sentinel_refused"] is True
    assert record["response_accessed"] is False
    assert record["response_unlock_command_exists"] is False


@pytest.mark.parametrize(
    ("role", "source"),
    (
        ("geometry", "from x import current_row\ncurrent_row()"),
        ("geometry", "import x.counting_lane as lane\nlane.read()"),
        (
            "geometry",
            "from experiments.loop_flux_counting_curvature_proof import counting_lane as lane",
        ),
        ("model", "from x.fcs_lane import q_jet"),
        ("protocol", "from x.oracle_lane import exact_oracle_record"),
        ("geometry", "obj.current_derivatives()"),
        ("geometry", "import importlib\ngetattr(importlib, 'import_module')"),
        ("model", "loader=__import__('x.'+'counting_lane')"),
        ("model", "loader=__builtins__['__im'+'port__']"),
        ("model", "import operator\nloader=operator.itemgetter('__im'+'port__')(__builtins__)"),
        ("protocol", "table=globals()\nloader=table['__im'+'port__']"),
        ("geometry", "loader=module.__getattribute__('current_'+'row')\nloader()"),
        (
            "geometry",
            "name=''.join(['response_','oracle'])\nloader(name)",
        ),
        (
            "geometry",
            "name='{}_{}'.format('counting','lane')\nloader(name)",
        ),
        (
            "geometry",
            "name=f\"{'fcs'}_{'lane'}\"\nloader(name)",
        ),
        (
            "geometry",
            "from pathlib import Path\n"
            "Path('../loop_flux_counting_curvature_proof/artifacts/certificate_records.json').read_bytes()",
        ),
        (
            "protocol",
            "from pathlib import Path as P\n"
            "P('../loop_flux_counting_curvature_proof/artifacts/summary.json').read_text()",
        ),
        (
            "geometry",
            "from experiments.loop_flux_counting_curvature_proof.run "
            "import expected_artifact_bytes\nexpected_artifact_bytes()",
        ),
        (
            "protocol",
            "from experiments.loop_flux_counting_curvature_proof import run as lane\n"
            "lane.expected_artifact_bytes()",
        ),
        (
            "geometry",
            "open('../loop_flux_counting_curvature_proof/artifacts/summary.json', 'rb').read()",
        ),
        ("protocol", "input('response path')"),
        ("geometry", "import io\nio.open('response.bin', 'rb')"),
        ("geometry", "from pathlib import Path\nPath('.').glob('*.json')"),
        ("protocol", "from pathlib import Path\nPath('response.bin').stat()"),
        ("protocol", "import subprocess\nsubprocess.run(['response-reader'])"),
        ("geometry", "import os\nos.getenv('RESPONSE_PATH')"),
        ("geometry", "import urllib.request\nurllib.request.urlopen('https://example.invalid')"),
        (
            "geometry",
            "import pathlib as p\n" "reader=getattr(p.Path('response.bin'), 'read_'+'bytes')\nreader()",
        ),
        (
            "focused_test",
            "from experiments.loop_flux_counting_curvature_proof.run "
            "import expected_artifact_bytes\nexpected_artifact_bytes()",
        ),
        (
            "focused_test",
            "from pathlib import Path\nPath('response.bin').read_bytes()",
        ),
        ("firewall_authority", "import subprocess\nsubprocess.run(['response-reader'])"),
        (
            "firewall_authority",
            "from pathlib import Path\n"
            "Path('../loop_flux_counting_curvature_proof/artifacts/certificate_records.json').read_bytes()",
        ),
        (
            "firewall_authority",
            "from pathlib import Path\n"
            "target='../loop_flux_counting_'+'curvature_proof/artifacts/summary.json'\n"
            "Path(target).read_bytes()",
        ),
        (
            "firewall_authority",
            "from pathlib import Path\npath=Path('../loop_flux_counting_curvature_proof')\n"
            "reader=path.read_bytes\nreader()",
        ),
        ("geometry", "reader=open"),
        ("protocol", "reader=input"),
        ("model", "compiler=compile"),
        ("geometry", "evaluator=eval"),
        ("protocol", "executor=exec"),
        ("model", "loader=__import__"),
        ("geometry", "lookup=getattr"),
        ("protocol", "setter=setattr"),
        ("geometry", "probe=hasattr"),
        ("protocol", "namespace=globals"),
        ("geometry", "namespace=locals"),
        ("protocol", "namespace=vars"),
        ("geometry", "x=object.__subclasses__"),
        ("protocol", "x=function.__globals__"),
        ("geometry", "x=function.__builtins__"),
        ("model", "import functools\nwrapper=functools.partial"),
        ("model", "from functools import partial"),
        ("composition", "from pathlib import os"),
        ("composition", "import sys\nargs=sys.argv"),
        ("composition", "import sys\nstream=sys.stdin"),
        ("composition", "import sys\nbuffer=sys.stdout.buffer"),
        ("protocol", "import json\nrecord=json.load(stream)"),
        ("protocol", "from json import load"),
        ("composition", "import typer\nvalue=typer.prompt('x')"),
        ("composition", "import typer\nstream=typer.get_text_stream('stdin')"),
        ("composition", "import typer\ntyper.launch('https://example.invalid')"),
        ("composition", "import typer\ntyper.edit('response')"),
        ("composition", "from pathlib import Path\nPath('response').open()"),
        ("composition", "from pathlib import Path\nPath('response').read_text()"),
        ("composition", "from pathlib import Path\nPath('.').rglob('*')"),
        ("composition", "from pathlib import Path\nPath('response').lstat()"),
        ("geometry", "handlers=[open]\nitems=iter(handlers)\nreader=next(items)"),
        ("geometry", "reader=next(iter([open]))"),
        ("geometry", "readers=list(map(lambda value: value, [open]))"),
        ("geometry", "readers=list(filter(None, [open]))"),
        ("composition", "from pathlib import Path\nreader=Path.read_bytes"),
        (
            "composition",
            "from pathlib import Path\nreaders=[Path.read_bytes]\nreaders[0](Path('response'))",
        ),
    ),
)
def test_firewall_rejects_response_and_current_imports_or_calls(role: str, source: str) -> None:
    assert _analyze_source_semantics(source, role=role)


@pytest.mark.parametrize(
    ("role", "source"),
    (
        (
            "geometry",
            "reader=next(map(open,('neutral.txt',)))\npayload=tuple(reader)",
        ),
        (
            "geometry",
            "payload=next(map(eval,(\"open('neutral.txt').read()\",)))",
        ),
        (
            "geometry",
            "payload=[f(\"open('neutral.txt').read()\") for f in (eval,)]",
        ),
        (
            "composition",
            "from pathlib import Path\n" "payload=tuple(map(Path.read_bytes,(Path('neutral.bin'),)))",
        ),
        (
            "model",
            "from functools import partial\n"
            "load=partial(open,'neutral.txt')\nreader=load()\npayload=tuple(reader)",
        ),
        ("geometry", "classes=object.__subclasses__()"),
        (
            "geometry",
            "def marker(): pass\n"
            "load=marker.__globals__['__builtins__']['open']\n"
            "reader=load('neutral.txt')\npayload=tuple(reader)",
        ),
        ("composition", "import sys\npayload=sys.argv[1]"),
        ("composition", "import sys\npayload=sys.stdin.readline()"),
        ("composition", "import sys\npayload=sys.stdin.buffer.read1()"),
        ("composition", "import sys\npayload=next(iter(sys.stdin))"),
        ("composition", "import json,sys\npayload=json.load(sys.stdin)"),
        ("composition", "import typer\npayload=typer.prompt('value')"),
        (
            "composition",
            "import typer\npayload=typer.get_text_stream('stdin').readline()",
        ),
        (
            "composition",
            "from pathlib import os\nresult=tuple(map(os.system,('neutral-command',)))",
        ),
        ("composition", "from pathlib import Path\nPath('a').rename('b')"),
        ("composition", "import typer\ntyper.launch('https://example.invalid')"),
        ("composition", "import typer\ntyper.edit('seed')"),
        (
            "composition",
            "import sys\nloader=sys._getframe().f_builtins['open']\n"
            "reader=loader('neutral.txt')\npayload=tuple(reader)",
        ),
        ("composition", "import sys\npayload=sys.__stdin__.readline()"),
        ("geometry", "breakpoint()"),
        (
            "firewall_authority",
            "from pathlib import Path\n"
            "Path('../loop_flux_counting_curvature_proof/artifacts/certificate_records.json').read_bytes()",
        ),
        ("geometry", "cap=open"),
        ("composition", "from pathlib import Path\ncap=Path.read_bytes"),
        ("composition", "import sys\ncap=sys.stdin"),
        ("geometry", "cap=eval"),
        ("geometry", "payload=sorted(('neutral',),key=open)"),
        ("geometry", "payload=tuple(filter(open,('neutral',)))"),
        ("geometry", "payload=any(map(open,('neutral',)))"),
        ("geometry", "payload=__import__('builtins').open"),
        ("composition", "from pathlib import Path\npayload=getattr(Path,'read_bytes')"),
        (
            "geometry",
            "import operator\npayload=operator.methodcaller('read_bytes')",
        ),
        ("geometry", "import pickle\npayload=pickle.loads(blob)"),
        ("geometry", "import marshal\npayload=marshal.loads(blob)"),
        ("geometry", "import runpy\npayload=runpy.run_path('response.py')"),
        (
            "geometry",
            "import importlib\npayload=importlib.import_module('response_oracle')",
        ),
        ("geometry", "import os\npayload=os.environ"),
        ("geometry", "import socket\npayload=socket.socket()"),
        ("geometry", "import urllib.request\npayload=urllib.request.urlopen('https://x')"),
        ("geometry", "import http.client\npayload=http.client.HTTPConnection('x')"),
        (
            "firewall_authority",
            "def source_firewall_record():\n"
            " for role,relative,kind in MATERIAL_FILES: pass\n"
            " relative=bytes((101,120,112)).decode()\n"
            " path=_material_path(relative)\n return path.read_bytes()",
        ),
        ("firewall_authority", "from pathlib import Path\nPath('../x').is_file()"),
        ("firewall_authority", "from pathlib import Path\nPath('../x').is_dir()"),
        ("firewall_authority", "from pathlib import Path\nPath('../x').is_symlink()"),
        ("firewall_authority", "from pathlib import Path\nPath('../x').iterdir()"),
        ("firewall_authority", "from pathlib import Path\nPath('../x').resolve()"),
        (
            "firewall_authority",
            "from pathlib import Path as P\n"
            "target='../loop_flux_'+'counting_curvature_proof'\n"
            "path=P(target)\nchecker=path.is_file\nchecker()",
        ),
        (
            "firewall_authority",
            "from pathlib import Path as P\n"
            "target='../loop_flux_'+'counting_curvature_proof'\n"
            "path=P(target)\nlister=path.iterdir\ntuple(lister())",
        ),
        (
            "firewall_authority",
            "from pathlib import Path as P\n"
            "target='../loop_flux_'+'counting_curvature_proof'\n"
            "path=P(target)\nresolver=path.resolve\nresolver()",
        ),
        ("composition", "import typer\npayload=tuple(typer.open_file('response.bin'))"),
        ("composition", "import typer\npayload=typer.get_binary_stream('stdin')"),
        ("composition", "import typer\npayload=typer.getchar()"),
        ("composition", "import typer\npayload=typer.confirm('x')"),
        ("composition", "import typer\ntyper.pause()"),
        (
            "composition",
            "import sys\nloader=sys.path_importer_cache[sys.path[0]]\n"
            "payload=loader.get_data('response.bin')",
        ),
        ("composition", "import sys\npayload=sys.path"),
        ("composition", "import sys\npayload=sys.executable"),
        ("composition", "from pathlib import Path\npayload=Path.home()"),
        ("composition", "from pathlib import Path\npayload=Path.cwd()"),
        ("composition", "from pathlib import Path\npayload=Path('response-link').readlink()"),
        ("composition", "from pathlib import Path\npayload=Path('a').samefile('b')"),
        ("composition", "from pathlib import Path\npayload=Path('a').owner()"),
        ("focused_test", "import pytest\nstatus=pytest.main(['response_test.py'])"),
        ("focused_test", "import pytest\nstatus=pytest.console_main()"),
        ("focused_test", "import pytest\npytest.importorskip('response_oracle')"),
    ),
)
def test_firewall_rejects_capability_references_and_higher_order_transport(
    role: str,
    source: str,
) -> None:
    assert _analyze_source_semantics(source, role=role)


@pytest.mark.parametrize(
    ("role", "source"),
    (
        ("composition", "from pathlib import Path\npayload=tuple(Path('response').walk())"),
        ("composition", "from pathlib import Path\nPath('response').lchmod(0)"),
        (
            "composition",
            "from pathlib import Path\npayload=Path('x').parser.os.listdir('.')",
        ),
        (
            "composition",
            "from pathlib import Path\npayload=Path('x').parser.os.scandir('.')",
        ),
        (
            "composition",
            "from pathlib import Path\nPath('x').parser.os.remove('target')",
        ),
        ("composition", "from pathlib import Path\npayload=Path('x').parser.os.getcwd()"),
        (
            "composition",
            "from pathlib import Path\nPath('x').parser.os.startfile('target')",
        ),
        (
            "composition",
            "from pathlib import Path\nPath('x').parser.os.putenv('K','V')",
        ),
        (
            "composition",
            "from pathlib import Path\nPath('x').parser.os.spawnv(0,'x',('x',))",
        ),
        (
            "composition",
            "from pathlib import Path as P\np=P('x')\nq=p\npayload=tuple(q.walk())",
        ),
        (
            "composition",
            "from pathlib import Path\np=Path('x')\nmodule=p.parser\nmodule.os.listdir('.')",
        ),
        (
            "composition",
            "from pathlib import Path\nmaker=Path\np=maker('x')\np.lchmod(0)",
        ),
        (
            "composition",
            "from pathlib import Path\n"
            "p=bytes((46,46,47,108,111,111,112,95,102,108,117,120,95,99,111,117,110,116,105,110,103,95,99,117,114,118,97,116,117,114,101,95,112,114,111,111,102)).decode()\n"
            "value=Path(p).resolve(strict=True)",
        ),
        ("composition", "import sys\nsys.path.insert(0,'neutral')"),
        (
            "firewall_authority",
            "from pathlib import Path\npayload=Path('x').parser.os.listdir('.')",
        ),
        (
            "firewall_authority",
            "from pathlib import PurePosixPath\n" "payload=PurePosixPath('x').parser.os.listdir('.')",
        ),
        (
            "firewall_authority",
            "from pathlib import Path as P\np=P('x')\nmodule=p.parser\nmodule.os.scandir('.')",
        ),
        (
            "focused_test",
            "from typer.testing import CliRunner\n"
            "with CliRunner().isolated_filesystem(temp_dir='response-dir'):\n pass",
        ),
        (
            "focused_test",
            "from typer.testing import CliRunner as Runner\n"
            "runner=Runner()\nctx=runner.isolated_filesystem(temp_dir='response-dir')",
        ),
        (
            "focused_test",
            "from typer.testing import CliRunner\n"
            "runner=CliRunner()\nmethod=runner.isolated_filesystem\nmethod()",
        ),
    ),
)
def test_firewall_rejects_unreviewed_constructed_receiver_chains(
    role: str,
    source: str,
) -> None:
    assert _analyze_source_semantics(source, role=role)


@pytest.mark.parametrize(
    "source",
    (
        "payload=help()",
        "payload=help('modules')",
        "payload=license()",
        "payload=credits()",
        "exit()",
        "quit()",
        "payload=dir(object)",
        "payload=type(object)",
        "cap=help",
        "cap=type",
        "payload=tuple(map(type,(object,)))",
        "payload=copyright",
        "payload=callable",
        "payload=memoryview",
        "payload=print",
        "payload=repr",
        "payload=super",
        "payload=vars",
    ),
)
def test_composition_builtin_capability_calls_and_values_are_fail_closed(source: str) -> None:
    assert _analyze_source_semantics(source, role="composition")


def test_every_nonapproved_known_builtin_reference_is_fail_closed() -> None:
    syntax_constants = {"False", "None", "True"}
    forbidden = (
        KNOWN_BUILTIN_REFERENCES - ALLOWED_BUILTIN_REFERENCES_BY_ROLE["composition"] - syntax_constants
    )
    assert {"credits", "dir", "exit", "help", "license", "quit"} <= forbidden
    for name in forbidden:
        assert _analyze_source_semantics(f"payload={name}\n", role="composition"), name


@pytest.mark.parametrize(
    ("role", "source"),
    (
        (
            "composition",
            "from pathlib import Path\n" "class Q(Path): pass\n" "payload=tuple(Q('response').walk())",
        ),
        (
            "focused_test",
            "from typer.testing import CliRunner\n"
            "class Q(CliRunner): pass\n"
            "with Q().isolated_filesystem(): pass",
        ),
        (
            "firewall_authority",
            "from pathlib import PurePosixPath\n"
            "class Q(PurePosixPath): pass\n"
            "payload=Q('x').parser.os.listdir('.')",
        ),
    ),
)
def test_firewall_forbids_subclassing_controlled_capability_constructors(
    role: str,
    source: str,
) -> None:
    assert _analyze_source_semantics(source, role=role)


@pytest.mark.parametrize(
    ("role", "source"),
    (
        (
            "composition",
            "from pathlib import Path\n"
            "def factory(): return Path\n"
            "Q=factory()\np=Q('response')\npayload=tuple(p.walk())",
        ),
        (
            "composition",
            "from pathlib import Path\n"
            "factory=lambda: Path\nQ=factory()\npayload=tuple(Q('response').walk())",
        ),
        (
            "composition",
            "from pathlib import Path\n"
            "constructors={'x':Path}\nQ=constructors['x']\npayload=tuple(Q('response').walk())",
        ),
        (
            "composition",
            "from pathlib import Path as P\nconstructors=(P,)\nconstructors[0]('x').walk()",
        ),
        (
            "focused_test",
            "from typer.testing import CliRunner\n"
            "def factory(): return CliRunner\n"
            "Q=factory()\nQ().isolated_filesystem()",
        ),
        (
            "focused_test",
            "from typer.testing import CliRunner\n"
            "factory=lambda: CliRunner\nfactory()().isolated_filesystem()",
        ),
        (
            "firewall_authority",
            "from pathlib import PurePosixPath\n"
            "def factory(): return PurePosixPath\n"
            "Q=factory()\nQ('x').parser.os.listdir('.')",
        ),
        (
            "firewall_authority",
            "from pathlib import Path\nconstructors={'x':Path}\n"
            "constructors['x']('x').parser.os.scandir('.')",
        ),
    ),
)
def test_firewall_forbids_controlled_constructor_class_value_escape(
    role: str,
    source: str,
) -> None:
    assert _analyze_source_semantics(source, role=role)


@pytest.mark.parametrize(
    ("role", "source"),
    (
        (
            "composition",
            "import sys\nfrom pathlib import Path\n"
            "__file__='C:/attacker/a/b/run.py'\n"
            "sys.path.insert(0, str(Path(__file__).resolve().parents[2]))\n"
            "from experiments.generator_tensor_prediction_protocol.theorem import execute_program",
        ),
        ("composition", "__package__=None"),
        ("composition", "import sys\nsys=object()"),
        ("composition", "import sys\ndel sys"),
        ("composition", "import sys\nvalue=(sys:=object())"),
        (
            "composition",
            "import sys\ndef mutate():\n global sys\n sys=object()",
        ),
        (
            "composition",
            "from pathlib import Path\nPath=object",
        ),
        (
            "firewall_authority",
            "from pathlib import Path, PurePosixPath\n"
            "__file__='C:/attacker/cwt-sim/experiments/"
            "generator_tensor_prediction_protocol/firewall.py'\n"
            "PACKAGE_DIR = Path(__file__).resolve().parent\n"
            "SIM_ROOT = PACKAGE_DIR.parents[1]",
        ),
        ("firewall_authority", "PACKAGE_DIR='attacker'"),
        ("firewall_authority", "SIM_ROOT='attacker'"),
        ("firewall_authority", "def f(PACKAGE_DIR):\n return PACKAGE_DIR"),
        ("firewall_authority", "global SIM_ROOT"),
    ),
)
def test_firewall_forbids_reserved_runtime_import_and_authority_root_rebinding(
    role: str,
    source: str,
) -> None:
    assert _analyze_source_semantics(source, role=role)


@pytest.mark.parametrize(
    "source",
    (
        "match 'x':\n case __file__: pass",
        "match ['x']:\n case [*MATERIAL_FILES]: pass",
        "match {'x':1}:\n case {'x':x, **SIM_ROOT}: pass",
        "import hashlib as PACKAGE_DIR",
        "from pathlib import Path as SIM_ROOT",
        "from pathlib import PurePosixPath as PACKAGE_DIR",
        "import sys\nmatch []:\n case [*sys]: pass",
        "import sys\nmatch {}:\n case {**sys}: pass",
        "target='nosj.sdrocer_etacifitrec/stcafitra/foorp_erutavruc_gnitnuoc_xulf_pool/"
        "stnemirepxe'[::-1]\n"
        "payload=((('contract_document',target,'markdown'),),{target})\n"
        "match payload:\n"
        " case (MATERIAL_FILES, REVIEWED_MATERIAL_RELATIVE_PATHS): pass",
    ),
)
def test_authority_firewall_rejects_pattern_and_import_alias_reserved_bindings(
    source: str,
) -> None:
    assert _analyze_source_semantics(source, role="firewall_authority")


@pytest.mark.parametrize(
    "source",
    (
        "from typer.testing import CliRunner\n"
        "runner=CliRunner()\n"
        "def factory(): return runner\n"
        "q=factory()\nq.isolated_filesystem()",
        "from typer.testing import CliRunner\n"
        "runner=CliRunner()\nbox={'r':runner}\n"
        "q=box['r']\nq.isolated_filesystem()",
        "from typer.testing import CliRunner\n"
        "from experiments.generator_tensor_prediction_protocol.run import app as run_app\n"
        "runner=CliRunner()\nstatus_result=runner.invoke(run_app,['status'])\n"
        "box={'r':status_result}\nbox['r'].runner.isolated_filesystem()",
        "from typer.testing import CliRunner\n"
        "from experiments.generator_tensor_prediction_protocol.run import app as run_app\n"
        "runner=CliRunner()\nstatus_result=runner.invoke(run_app,['status'])\n"
        "def factory(): return status_result\nfactory().runner.isolated_filesystem()",
        "from typer.testing import CliRunner\n"
        "runner=CliRunner()\nfactory=lambda: runner\nfactory().isolated_filesystem()",
        "from typer.testing import CliRunner\n"
        "runner=CliRunner()\nbox={'outer':{'inner':runner}}\n"
        "box['outer']['inner'].isolated_filesystem()",
    ),
)
def test_focused_firewall_propagates_controlled_instances_and_results_through_returns_and_dicts(
    source: str,
) -> None:
    assert _analyze_source_semantics(source, role="focused_test")


@pytest.mark.parametrize(
    ("role", "source"),
    (
        (
            "firewall_authority",
            "q=PACKAGE_DIR if True else SIM_ROOT\npayload=q.parser.os.listdir('.')",
        ),
        (
            "firewall_authority",
            "q=PACKAGE_DIR or SIM_ROOT\npayload=q.parser.os.listdir('.')",
        ),
        (
            "firewall_authority",
            "bag=frozenset((PACKAGE_DIR,))\n" "for q in iter(bag): payload=q.parser.os.listdir('.')",
        ),
        (
            "firewall_authority",
            "def factory(): return PACKAGE_DIR if True else SIM_ROOT\n" "factory().parser.os.listdir('.')",
        ),
        (
            "focused_test",
            "from typer.testing import CliRunner\nrunner=CliRunner()\n"
            "r=runner if True else runner\nwith r.isolated_filesystem(): pass",
        ),
        (
            "focused_test",
            "from typer.testing import CliRunner\nrunner=CliRunner()\n"
            "r=runner and runner\nr.isolated_filesystem()",
        ),
        (
            "focused_test",
            "from typer.testing import CliRunner\nrunner=CliRunner()\n"
            "def factory(): return runner if True else runner\n"
            "factory().isolated_filesystem()",
        ),
    ),
)
def test_firewall_propagates_controlled_instances_through_conditional_and_iterable_forms(
    role: str,
    source: str,
) -> None:
    assert _analyze_source_semantics(source, role=role)


@pytest.mark.parametrize(
    ("role", "source"),
    (
        (
            "firewall_authority",
            "def escape():\n yield PACKAGE_DIR\n" "for q in escape(): payload=q.parser.os.listdir('.')",
        ),
        (
            "firewall_authority",
            "def escape():\n yield from (PACKAGE_DIR,)\n"
            "for q in escape(): payload=q.parser.os.listdir('.')",
        ),
        (
            "firewall_authority",
            "async def escape():\n yield PACKAGE_DIR\n"
            "async def use():\n async for q in escape(): q.parser.os.listdir('.')",
        ),
        (
            "focused_test",
            "from typer.testing import CliRunner\nrunner=CliRunner()\n"
            "def escape():\n yield runner\n"
            "for q in escape(): q.isolated_filesystem()",
        ),
        (
            "focused_test",
            "from typer.testing import CliRunner\nrunner=CliRunner()\n"
            "def escape():\n yield from (runner,)\n"
            "for q in escape(): q.isolated_filesystem()",
        ),
        (
            "firewall_authority",
            "def echo():\n q=yield\n yield q\n"
            "g=echo()\ng.send(None)\nq=g.send(PACKAGE_DIR)\n"
            "payload=q.parser.os.listdir('.')",
        ),
        (
            "focused_test",
            "from typer.testing import CliRunner\nrunner=CliRunner()\n"
            "def echo():\n q=yield\n yield q\n"
            "g=echo()\ng.send(None)\ng.send(runner)",
        ),
    ),
)
def test_firewall_rejects_controlled_generator_yield_and_send_channels(
    role: str,
    source: str,
) -> None:
    assert _analyze_source_semantics(source, role=role)


@pytest.mark.parametrize(
    ("role", "source"),
    (
        (
            "firewall_authority",
            "class Holder:\n def path(self): return PACKAGE_DIR\n"
            "q=Holder().path()\npayload=q.parser.os.listdir('.')",
        ),
        (
            "firewall_authority",
            "def path(): return PACKAGE_DIR\nclass Holder: accessor=path\n"
            "q=Holder().accessor()\npayload=q.parser.os.listdir('.')",
        ),
        (
            "firewall_authority",
            "class Holder:\n accessor=lambda self: PACKAGE_DIR\n"
            "Holder().accessor().parser.os.listdir('.')",
        ),
        (
            "focused_test",
            "from typer.testing import CliRunner\nrunner=CliRunner()\n"
            "class Holder:\n def get(self): return runner\n"
            "Holder().get().isolated_filesystem()",
        ),
    ),
)
def test_firewall_rejects_controlled_method_and_descriptor_returns(
    role: str,
    source: str,
) -> None:
    assert _analyze_source_semantics(source, role=role)


def test_reviewed_ast_hash_domain_is_minor_version_neutral_and_syntax_sensitive() -> None:
    source = "def f(value: int = 1):\n    return value + 2\n"
    reviewed = "4422dad5f67d43b3e1afe7732ad223c174386fc621c4923dd2559e6ee88b9563"
    assert _canonical_source_ast_sha256(source) == reviewed
    mutated_source = "def f(value: int = 1):\n    return value + 3\n"
    assert _canonical_source_ast_sha256(mutated_source) != reviewed


def test_public_arbitrary_text_analyzer_is_permanently_nonauthoritative() -> None:
    source = "value=1\n"
    assert analyze_source_text(source, role="geometry") == ("UNREVIEWED_SOURCE_IDENTITY",)
    token = object()
    with pytest.raises(TypeError):
        analyze_source_text(  # type: ignore[call-arg]
            source,
            role="geometry",
            source_identity=(
                "experiments/generator_tensor_prediction_protocol/geometry.py",
                "0" * 64,
            ),
            _source_record_capability=token,
            _reviewed_authority=token,
        )
    assert _analyze_source_semantics(
        "from experiments.generator_tensor_prediction_protocol.firewall "
        "import _SOURCE_RECORD_CAPABILITY\n",
        role="focused_test",
    )


@pytest.mark.parametrize(
    ("relative", "role"),
    (
        ("./experiments/generator_tensor_prediction_protocol/geometry.py", "geometry"),
        ("experiments/generator_tensor_prediction_protocol/../geometry.py", "geometry"),
        ("experiments\\generator_tensor_prediction_protocol\\geometry.py", "geometry"),
        ("C:/attacker/geometry.py", "geometry"),
        ("experiments/generator_tensor_prediction_protocol/geometry.py", "protocol"),
        (
            "experiments/loop_flux_counting_curvature_proof/artifacts/certificate_records.json",
            "geometry",
        ),
    ),
)
def test_reviewed_source_analyzer_refuses_alias_foreign_and_wrong_role_identity(
    relative: str,
    role: str,
) -> None:
    assert analyze_reviewed_source(relative, role=role) == ("UNREVIEWED_SOURCE_IDENTITY",)


def test_reviewed_source_analyzer_accepts_only_disk_owned_reviewed_identity() -> None:
    relative = "experiments/generator_tensor_prediction_protocol/geometry.py"
    assert analyze_reviewed_source(relative, role="geometry") == ()
    with pytest.raises(TypeError):
        analyze_reviewed_source(  # type: ignore[call-arg]
            relative,
            role="geometry",
            source="value=1\n",
            sha256_raw="0" * 64,
            token=object(),
        )


def test_material_snapshot_scan_reads_once_and_rejects_malicious_first_bytes() -> None:
    malicious = b"payload = open('secret')\n"
    clean = b"value = 1\n"

    class TwoVersionPath:
        def __init__(self) -> None:
            self.calls = 0

        def read_bytes(self) -> bytes:
            self.calls += 1
            return malicious if self.calls == 1 else clean

    path = TwoVersionPath()
    raw, import_targets, import_issues, firewall_issues = _scan_material_snapshot(
        path,  # type: ignore[arg-type]
        role="geometry",
        kind="python",
    )
    assert path.calls == 1
    assert raw == malicious
    assert import_targets == ()
    assert import_issues == ()
    assert firewall_issues
    assert any("open" in issue.casefold() for issue in firewall_issues)


@pytest.mark.parametrize(
    "source",
    (
        "from experiments.generator_tensor_prediction_protocol import run\n"
        "run.typer.open_file('response.bin','rb')",
        "from experiments.generator_tensor_prediction_protocol import run\n"
        "run.typer.get_binary_stream('stdin')",
        "from experiments.generator_tensor_prediction_protocol import run\n"
        "run.Path('x').parser.os.listdir('.')",
        "from experiments.generator_tensor_prediction_protocol import run\n"
        "payload=tuple(run.Path('x').walk())",
        "from experiments.generator_tensor_prediction_protocol import run\n" "payload=run.sys.path",
        "from typer.testing import CliRunner\n"
        "from experiments.generator_tensor_prediction_protocol.run import app as run_app\n"
        "runner = CliRunner()\n"
        "status_result = runner.invoke(run_app, ['status'])\n"
        "status_result.runner.isolated_filesystem()",
    ),
)
def test_focused_test_rejects_module_reexports_and_runner_return_capabilities(
    source: str,
) -> None:
    assert _analyze_source_semantics(source, role="focused_test")


def test_material_path_runtime_membership_rejects_predecessor_even_when_canonical() -> None:
    with pytest.raises(ValueError, match="exact reviewed inventory member"):
        _material_path("experiments/loop_flux_counting_curvature_proof/artifacts/certificate_records.json")


def test_live_role_sources_pass_firewall_and_have_no_forbidden_imports() -> None:
    record = source_firewall_record()
    assert record["material_path_set"] == MATERIAL_FILES
    assert record["material_path_set_sha256"] == REVIEWED_MATERIAL_PATH_SET_SHA256
    assert record["material_path_set_matches"] is True
    assert record["all_material_files_present_and_canonical"] is True
    assert record["all_python_import_closures_clean"] is True
    assert record["protected_role_firewalls_clean"] is True
    assert record["package_file_set_matches"] is True
    assert record["missing_package_files"] == ()
    assert record["unexpected_package_files"] == ()
    assert record["unexpected_package_directories"] == ()
    assert record["artifact_directory_present"] is False
    assert record["source_lock_present"] is False
    assert len(record["role_import_target_records"]) == 6
    assert all(item["import_targets"] for item in record["role_import_target_records"])
    assert len(record["file_records"]) == 14
    assert {entry["relative_path"] for entry in record["file_records"]} >= {
        "experiments/generator_tensor_prediction_protocol/firewall.py",
        "experiments/generator_tensor_prediction_protocol/MODEL_CONTRACT.md",
        "tests/experiments/test_generator_tensor_prediction_protocol.py",
    }


def test_firewall_preserves_benign_statically_resolved_math_attributes() -> None:
    source = "from fractions import Fraction\nx=Fraction(1,2)\ny=x.numerator\n"
    assert _analyze_source_semantics(source, role="geometry") == ()


def test_theorem_all_gates_and_case_dispositions_pass_pre_response() -> None:
    summary, records = execute_program()
    assert summary["disposition"] == "PASS_INTERNAL_ANALYTIC"
    assert summary["passed_gate_count"] == summary["gate_count"] == 12
    assert summary["failed_gates"] == ()
    assert summary["response_accessed"] is False
    assert summary["source_lock_present"] is False
    assert summary["artifacts_generated"] is False
    assert records["N0"]["disposition"] == "INELIGIBLE_NOT_CLOSED"
    assert records["P0"]["disposition"] == "ELIGIBLE_PRE_RESPONSE_ONLY"
    for name, expected in EXPECTED_CASE_DISPOSITIONS.items():
        assert summary["cases"][name]["status"] == expected
        assert summary["cases"][name]["natural_status"] == expected


@pytest.mark.parametrize(
    ("path", "value", "failed_gate"),
    (
        (("N0", "closure_rank"), 0, ORDERED_GATES[3]),
        (("N0", "closure_determinant_sha256"), "0" * 64, ORDERED_GATES[2]),
        (("N0", "retrospective_diagnostic_used_for_acceptance"), True, ORDERED_GATES[4]),
        (("P0", "calibration_rank"), 0, ORDERED_GATES[7]),
        (("P0", "gram_determinant_sha256"), "0" * 64, ORDERED_GATES[7]),
        (("P0", "response_accessed"), True, ORDERED_GATES[8]),
        (("P0", "coordinate_covariance_exact"), False, ORDERED_GATES[6]),
        (("protocol", "response_accessed"), True, ORDERED_GATES[10]),
        (("protocol", "criterion_sha256"), "0" * 64, ORDERED_GATES[10]),
        (("protocol", "exposure_registry_sha256"), "0" * 64, ORDERED_GATES[10]),
        (("firewall", "file_records"), (), ORDERED_GATES[9]),
        (("firewall", "role_import_target_records"), (), ORDERED_GATES[9]),
        (("firewall", "unexpected_package_files"), ("response.py",), ORDERED_GATES[9]),
        (("firewall", "artifact_directory_present"), True, ORDERED_GATES[9]),
        (("sentinel", "sentinel_refused"), False, ORDERED_GATES[9]),
    ),
)
def test_single_gate_mutations_fail_only_their_owning_path(
    path: tuple[str, str], value: object, failed_gate: str
) -> None:
    certificates = dict(build_certificates())
    if path[0] in {"N0", "P0", "firewall"}:
        certificates[path[0]] = _replace_record_field(certificates[path[0]], path[1], value)
    else:
        record = dict(certificates[path[0]])
        record[path[1]] = value
        certificates[path[0]] = record
    results = gate_results(certificates)
    assert results[failed_gate] is False


def test_fraction_subclass_and_basis_record_forgery_fail_closed() -> None:
    class EqualFraction(Fraction):
        def __eq__(self, _other: object) -> bool:
            return True

    certificates = dict(build_certificates())
    n0 = _thaw(certificates["N0"])
    assert type(n0) is dict
    row = list(n0["closure_rows"][0])
    row[0] = EqualFraction(row[0])
    rows = list(n0["closure_rows"])
    rows[0] = tuple(row)
    n0["closure_rows"] = tuple(rows)
    # Bypass the canonical freezer deliberately so the theorem gate sees the
    # adversarial subclass rather than relying only on producer-side refusal.
    certificates["N0"] = MappingProxyType(n0)
    assert gate_results(certificates)[ORDERED_GATES[2]] is False

    certificates = dict(build_certificates())
    p0 = _thaw(certificates["P0"])
    assert type(p0) is dict
    matrices = [[list(row) for row in matrix] for matrix in p0["calibration_basis_matrices"]]
    matrices[0][0][0] += Fraction(1)
    p0["calibration_basis_matrices"] = tuple(tuple(tuple(row) for row in matrix) for matrix in matrices)
    certificates["P0"] = freeze_exact_record(p0)
    assert gate_results(certificates)[ORDERED_GATES[7]] is False


def test_firewall_authority_hash_and_import_capability_records_are_bound() -> None:
    original = build_certificates()["firewall"]
    assert type(original) is MappingProxyType
    for relative_path in (
        "experiments/generator_tensor_prediction_protocol/firewall.py",
        "tests/experiments/test_generator_tensor_prediction_protocol.py",
    ):
        forged = _thaw(original)
        assert type(forged) is dict
        records = list(forged["file_records"])
        index = next(
            position for position, item in enumerate(records) if item["relative_path"] == relative_path
        )
        records[index]["sha256_raw"] = "0" * 64
        forged["file_records"] = tuple(records)
        certificates = dict(build_certificates())
        certificates["firewall"] = freeze_exact_record(forged)
        assert gate_results(certificates)[ORDERED_GATES[9]] is False

    forged = _thaw(original)
    assert type(forged) is dict
    role_records = list(forged["role_import_target_records"])
    role_records[0]["import_targets"] = (*role_records[0]["import_targets"], "subprocess")
    forged["role_import_target_records"] = tuple(role_records)
    certificates = dict(build_certificates())
    certificates["firewall"] = freeze_exact_record(forged)
    assert gate_results(certificates)[ORDERED_GATES[9]] is False


def test_n0_full_reviewed_certificate_refuses_metadata_and_unimodular_row_mutations() -> None:
    original = krylov_no_go_certificate()
    mutations = {
        "centers": tuple(reversed(original["centers"])),
        "family": "arbitrary retrospective 3x3 tensor",
        "closure_row_order": tuple(reversed(original["closure_row_order"])),
        "authority": "producer_self_attestation",
        "closure_derivative_convention": "dA omitted",
        "wedge_action_convention": "det(A)*inverse(A)",
    }
    for field, value in mutations.items():
        certificates = dict(build_certificates())
        certificates["N0"] = _replace_record_field(original, field, value)
        assert gate_results(certificates)[ORDERED_GATES[2]] is False

    forged = _thaw(original)
    assert type(forged) is dict
    rows = [list(row) for row in forged["closure_rows"]]
    rows[1] = [left + right for left, right in zip(rows[1], rows[0], strict=True)]
    forged["closure_rows"] = tuple(tuple(row) for row in rows)
    assert rational_determinant(rows) == original["closure_determinant"]
    certificates = dict(build_certificates())
    certificates["N0"] = freeze_exact_record(forged)
    assert gate_results(certificates)[ORDERED_GATES[2]] is False


def test_p0_full_reviewed_certificate_refuses_geometry_and_metadata_forgery() -> None:
    original = connection_eligibility_certificate()
    mutations = {
        "calibration_centers": tuple(reversed(A_CENTERS)),
        "confirmation_centers": tuple(reversed(V_CENTERS)),
        "heldout_center": A_CENTERS[0],
        "heldout_area_vector": (0, 0, 0),
        "heldout_basis_densities": (Fraction(0),) * 3,
        "basis_order": tuple(reversed(original["basis_order"])),
        "connection_family": "response-selected basis",
        "curvature_family": "arbitrary fitted response tensor",
        "authority": "producer_self_attestation",
        "flux_conjugation_records": (),
    }
    for field, value in mutations.items():
        certificates = dict(build_certificates())
        certificates["P0"] = _replace_record_field(original, field, value)
        assert gate_results(certificates)[ORDERED_GATES[7]] is False
    certificates = dict(build_certificates())
    certificates["P0"] = _replace_record_field(
        original,
        "heldout_area_vector",
        (True, -1, 3),
    )
    assert gate_results(certificates)[ORDERED_GATES[7]] is False

    forged = _thaw(original)
    assert type(forged) is dict
    matrices = [[list(row) for row in matrix] for matrix in forged["calibration_basis_matrices"]]
    matrices[0][0] = [-value for value in matrices[0][0]]
    forged["calibration_basis_matrices"] = tuple(tuple(tuple(row) for row in matrix) for matrix in matrices)
    rows = [row for matrix in matrices for row in matrix]
    gram = [[sum(row[i] * row[j] for row in rows) for j in range(3)] for i in range(3)]
    assert rational_determinant(gram) == original["gram_determinant"]
    certificates = dict(build_certificates())
    certificates["P0"] = freeze_exact_record(forged)
    assert gate_results(certificates)[ORDERED_GATES[7]] is False


def test_cli_status_and_verify_source_are_response_free() -> None:
    status_result = runner.invoke(run_app, ["status"])
    assert status_result.exit_code == 0, status_result.output
    assert '"response_accessed": false' in status_result.output
    verify_result = runner.invoke(run_app, ["verify-source"])
    assert verify_result.exit_code == 0, verify_result.output
    assert "PASS 12/12" in verify_result.output
    assert "source_lock_present=false" in verify_result.output


def test_source_phase_has_no_artifacts_or_source_lock() -> None:
    record = source_firewall_record()
    assert record["artifact_directory_present"] is False
    assert record["source_lock_present"] is False
    assert record["unexpected_package_files"] == ()
