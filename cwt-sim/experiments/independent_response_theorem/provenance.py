"""Portable source provenance for the independent-response theorem harness."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Mapping

SOURCE_TEXT_HASH_DOMAIN = "sha256_utf8_lf_v1"
SOURCE_TEXT_HASH_SPEC = {
    "id": SOURCE_TEXT_HASH_DOMAIN,
    "encoding": "strict UTF-8",
    "bom_policy": "reject UTF-8 BOM",
    "newline_policy": "replace CRLF with LF; reject every remaining bare CR",
    "other_normalization": "none",
}

SOURCE_PATHS = (
    "cwt/cgt/_geom_compat.py",
    "cwt/cgt/benchmarks.py",
    "cwt/cgt/continuation.py",
    "cwt/cgt/loop_protocols.py",
    "cwt/cgt/models.py",
    "cwt/geometry/berry.py",
    "cwt/geometry/branch_distance.py",
    "cwt/geometry/coherence.py",
    "cwt/geometry/psi.py",
    "cwt/geometry/stats.py",
    "experiments/independent_response_theorem/PROTOCOL_LOCK.md",
    "experiments/independent_response_theorem/provenance.py",
    "experiments/independent_response_theorem/response.py",
    "experiments/independent_response_theorem/run.py",
    "experiments/independent_response_theorem/theorem.py",
    "tests/experiments/test_independent_response_theorem.py",
)

PRE_CORRECTION_SOURCE_BUNDLE_SHA256 = "8f28a6910aace66bc577d766ea33a579bdede0e05f359ce4e67ab2320fb5657d"
PRE_CORRECTION_ARTIFACT_SHA256 = {
    "PROVENANCE.json": "f415d7814f33d8f9bcb460a4587e61383fe307921440728aeedef5f6d8fe6751",
    "REPORT.md": "64a90b357af34648f16c42dc671c473b0099c1e89b6fe1cea3916470430415a3",
    "records.json": "9d9abe277daf305014e52a7ace0517fb72f31037da630545521dd3daf125e2f7",
    "summary.json": "afc8923bd9c15de461c8b18a58c7249fc082bac2e746a668204a37b1d9d02b63",
}
PRE_CORRECTION_SEMANTIC_SHA256 = {
    "config": "38f353e188fedc2389b52e496d631ab88840aa72a1ccb06fa52322ac3e127de1",
    "gates": "ec907b15d54162bb566546e805140cd4aa307a7a3298ed7aa12601d79aa4575e",
    "metrics": "ed49d5268f5a874ec65ffde97b8de76b931f6e2f4c9184d8e49521cfd45dcd34",
    "records": "42e6a124bb3d604e571498164d73a2e156f8360fc98d3c7a76e1c50af6c3efd6",
    "report_text": "d5dff67e207d5dc5c165cc24a1dc2db72befcb878958cd9f5abef4f1199ea1a1",
    "summary": "ac784afb9d30f2fab70a7db3376baedbc2f0e9df3ff487145da027062d55ae36",
}

# These are the exact Windows execution-worktree bytes recorded in the
# pre-commit schema-v1 provenance. Each is reconstructed below from the
# canonical LF bytes to prove that CRLF expansion was the only difference.
PRE_CORRECTION_CRLF_EXECUTION = {
    "cwt/cgt/_geom_compat.py": {
        "sha256": "4236d137b37cdb5f129b63409cf0b54cc0bcf0e03844f7c16523f32d5aed2ae8",
        "size": 1080,
        "crlf_count": 42,
    },
    "cwt/cgt/benchmarks.py": {
        "sha256": "4f793fc625707e0e93bacda391374131bb582f6678d4c643c9ffde282b3b59fe",
        "size": 11416,
        "crlf_count": 275,
    },
    "cwt/cgt/continuation.py": {
        "sha256": "ddf6723c175fa930aaaaffd5345ceb9940de0afc8d4b62abe61cb8bfc649591e",
        "size": 11888,
        "crlf_count": 305,
    },
    "cwt/cgt/loop_protocols.py": {
        "sha256": "08d237e1601517a5ba14092dbb0250cc022a1608404e542d98aaf256e1a457bf",
        "size": 22397,
        "crlf_count": 542,
    },
    "cwt/cgt/models.py": {
        "sha256": "203d8d2eaf3ddbd708ec3eebd825630cf9cd31ede06343a69f9df67f8a6996c4",
        "size": 2668,
        "crlf_count": 85,
    },
    "cwt/geometry/berry.py": {
        "sha256": "97679cdb5712075e553caef56fddb069e32f3d81ff15118089789ce87bb14d5c",
        "size": 1816,
        "crlf_count": 56,
    },
    "cwt/geometry/branch_distance.py": {
        "sha256": "a3b49220dbdc8dc3b62ad7459266e2d75bbe8f2e48a17c14c0d1f8ddd37b503c",
        "size": 1476,
        "crlf_count": 39,
    },
    "cwt/geometry/coherence.py": {
        "sha256": "572cab21432105dfe31ed7b641fa17075e6f0d3f7b42858f5398165712c8508c",
        "size": 3108,
        "crlf_count": 79,
        "bare_lf_ordinals": [78],
    },
    "cwt/geometry/psi.py": {
        "sha256": "ba94c4008aae7de7ad48c00d9c8d7be28925e7568b8b10cdd84157a4508b3298",
        "size": 1714,
        "crlf_count": 57,
    },
    "cwt/geometry/stats.py": {
        "sha256": "67acacd17b8fa77f3383cec8ae56429d123a66b508edc8cad61a0a875c43bbd4",
        "size": 2173,
        "crlf_count": 62,
    },
}


class SourceTextIntegrityError(ValueError):
    """Raised when bytes do not satisfy the declared source-text domain."""


def canonical_json_sha256(payload: Any) -> str:
    """Hash strict, path-bound canonical JSON."""

    encoded = json.dumps(
        payload,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def canonical_source_text_bytes(raw: bytes) -> bytes:
    """Return strict UTF-8 LF bytes without applying any other normalization."""

    if raw.startswith(b"\xef\xbb\xbf"):
        raise SourceTextIntegrityError("UTF-8 BOM is forbidden by sha256_utf8_lf_v1")
    try:
        raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise SourceTextIntegrityError("source text is not strict UTF-8") from exc
    canonical = raw.replace(b"\r\n", b"\n")
    if b"\r" in canonical:
        raise SourceTextIntegrityError("bare CR is forbidden by sha256_utf8_lf_v1")
    return canonical


def source_text_sha256(raw: bytes) -> str:
    """Hash bytes in the versioned portable source-text domain."""

    return hashlib.sha256(canonical_source_text_bytes(raw)).hexdigest()


def git_blob_oid_sha1(payload: bytes) -> str:
    """Return the Git SHA-1 blob OID for exact payload bytes."""

    header = f"blob {len(payload)}\0".encode("ascii")
    return hashlib.sha1(header + payload).hexdigest()  # noqa: S324 - Git object identity


def build_source_manifest(
    sim_root: Path,
    source_paths: Iterable[str] = SOURCE_PATHS,
) -> dict[str, dict[str, Any]]:
    """Build a sorted, path-bound manifest in the portable LF domain."""

    normalized_paths = tuple(sorted(source_paths))
    if len(normalized_paths) != len(set(normalized_paths)):
        raise SourceTextIntegrityError("duplicate source dependency path")
    manifest: dict[str, dict[str, Any]] = {}
    for relative in normalized_paths:
        path = sim_root / relative
        canonical = canonical_source_text_bytes(path.read_bytes())
        manifest[relative] = {
            "git_blob_oid_sha1": git_blob_oid_sha1(canonical),
            "hash_domain": SOURCE_TEXT_HASH_DOMAIN,
            "sha256": hashlib.sha256(canonical).hexdigest(),
            "size_bytes": len(canonical),
        }
    return manifest


def source_bundle_payload(
    manifest: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Return a deterministic list whose digest binds every dependency path."""

    return [
        {
            "git_blob_oid_sha1": manifest[path]["git_blob_oid_sha1"],
            "hash_domain": manifest[path]["hash_domain"],
            "path": path,
            "sha256": manifest[path]["sha256"],
            "size_bytes": manifest[path]["size_bytes"],
        }
        for path in sorted(manifest)
    ]


def source_bundle_sha256(manifest: Mapping[str, Mapping[str, Any]]) -> str:
    """Hash the sorted, path-bound source dependency bundle."""

    return canonical_json_sha256(source_bundle_payload(manifest))


def verify_source_manifest(
    sim_root: Path,
    manifest: Mapping[str, Mapping[str, Any]],
    source_paths: Iterable[str] = SOURCE_PATHS,
) -> None:
    """Fail closed when a path, dependency, or canonical source byte differs."""

    expected_paths = tuple(sorted(source_paths))
    if tuple(sorted(manifest)) != expected_paths:
        raise SourceTextIntegrityError("source dependency path set differs")
    observed = build_source_manifest(sim_root, expected_paths)
    if observed != dict(manifest):
        raise SourceTextIntegrityError("source dependency manifest differs")


def build_correction_ledger(
    sim_root: Path,
    source_manifest: Mapping[str, Mapping[str, Any]],
    corrected_artifact_sha256: Mapping[str, str],
) -> dict[str, Any]:
    """Build the detached pre-commit provenance-format correction ledger."""

    affected: list[dict[str, Any]] = []
    if set(PRE_CORRECTION_CRLF_EXECUTION) - set(source_manifest):
        raise SourceTextIntegrityError("affected source missing from corrected manifest")
    for relative in sorted(PRE_CORRECTION_CRLF_EXECUTION):
        previous = PRE_CORRECTION_CRLF_EXECUTION[relative]
        canonical = canonical_source_text_bytes((sim_root / relative).read_bytes())
        bare_lf_ordinals = set(previous.get("bare_lf_ordinals", []))
        pieces = canonical.split(b"\n")
        reconstructed = bytearray()
        for ordinal, piece in enumerate(pieces):
            reconstructed.extend(piece)
            if ordinal < len(pieces) - 1:
                reconstructed.extend(b"\n" if ordinal in bare_lf_ordinals else b"\r\n")
        reconstructed_execution = bytes(reconstructed)
        if hashlib.sha256(reconstructed_execution).hexdigest() != previous["sha256"]:
            raise SourceTextIntegrityError(f"CRLF reconstruction hash differs for {relative}")
        if len(reconstructed_execution) != previous["size"]:
            raise SourceTextIntegrityError(f"CRLF reconstruction size differs for {relative}")
        if reconstructed_execution.count(b"\r\n") != previous["crlf_count"]:
            raise SourceTextIntegrityError(f"CRLF reconstruction count differs for {relative}")
        corrected = source_manifest[relative]
        affected.append(
            {
                "canonical_repository_text": corrected,
                "execution_worktree": {
                    "hash_domain": "sha256_raw_bytes_v1",
                    "sha256": previous["sha256"],
                    "size_bytes": previous["size"],
                },
                "path": relative,
                "transformation_proof": {
                    "bare_cr_count": 0,
                    "bare_lf_count": len(bare_lf_ordinals),
                    "bare_lf_ordinals": sorted(bare_lf_ordinals),
                    "crlf_count": previous["crlf_count"],
                    "operation": "CRLF_to_LF_only",
                    "reconstructed_execution_hash_and_size_match": True,
                },
            }
        )
    if len(affected) != 10:
        raise SourceTextIntegrityError("correction ledger must contain exactly ten paths")
    return {
        "schema_version": 1,
        "correction_status": "PACKAGING_CORRECTION_NO_NUMERIC_CHANGE",
        "correction_scope": "independent_response_theorem provenance format only",
        "discovery_timing": (
            "2026-08-15 after the numerical result and independent review, before first commit"
        ),
        "reason": (
            "Schema-v1 source hashes captured Windows CRLF checkout bytes for ten shared Python "
            "dependencies, while repository identity is the LF Git blob required by .gitattributes."
        ),
        "canonical_hashes_are_repository_identity_not_execution_bytes": True,
        "original_runtime_newline_representation": (
            "CRLF for nine files; coherence.py had 79 CRLF endings and one documented LF "
            "ending after the sign patch"
        ),
        "affected_paths": affected,
        "previous": {
            "artifact_sha256_raw_bytes": dict(sorted(PRE_CORRECTION_ARTIFACT_SHA256.items())),
            "provenance_sha256_raw_bytes": PRE_CORRECTION_ARTIFACT_SHA256["PROVENANCE.json"],
            "source_bundle_sha256_ambiguous_raw_checkout_domain": (PRE_CORRECTION_SOURCE_BUNDLE_SHA256),
        },
        "corrected": {
            "artifact_sha256_raw_bytes": dict(sorted(corrected_artifact_sha256.items())),
            "source_bundle_sha256": source_bundle_sha256(source_manifest),
            "source_hash_domain": SOURCE_TEXT_HASH_SPEC,
        },
        "semantic_equivalence": {
            "claim_text_unchanged": True,
            "config_unchanged": True,
            "decision_unchanged": True,
            "gates_and_thresholds_unchanged": True,
            "metrics_unchanged": True,
            "numeric_records_unchanged": True,
            "semantic_sha256": dict(sorted(PRE_CORRECTION_SEMANTIC_SHA256.items())),
        },
        "not_new_evidence": True,
        "no_new_empirical_or_confirmation_run": True,
        "deterministic_theorem_recomputed_for_packaging_or_validation": True,
        "parameters_numerical_gates_decision_hashes_identical": True,
        "cross_platform_byte_scope": (
            "Git checkouts and archives preserve the reviewed raw CRLF artifact snapshot via "
            "artifact-only -text attributes. Portable source identity and JSON semantic hashes "
            "are canonical; a host-native artifact regeneration is not claimed to reproduce raw "
            "newline bytes on every operating system."
        ),
    }
