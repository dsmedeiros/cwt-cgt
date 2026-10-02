"""Paired full-tensor diagnostics, strict support requirements, and child identity."""

import json
from copy import deepcopy
from itertools import product

import numpy as np
import pytest

from experiments.percolation_finite_size.convergence import aggregate, tensor_change, variation_status
from experiments.percolation_finite_size.model import stable_seed, wilson95


@pytest.fixture
def study():
    profile = dict(
        dimensions=[2],
        radii=[2],
        probabilities_2d=[0.4],
        geometry_trials=[512, 2048],
        steps=[0.01, 0.02],
        geometry_batches=5,
        measurement_trials=2048,
        seed=20261002,
        required_joint_batches=5,
        median_change_tolerance=0.25,
        maximum_change_tolerance=0.5,
    )
    children = {}
    for trials, step in product(profile["geometry_trials"], profile["steps"]):
        batches = [
            dict(
                batch=batch,
                seed=stable_seed(profile["seed"], 2, 2, 0.4, "geometry", batch),
                trials=trials,
                requested_trials=trials,
                excluded_reason=None,
                g_uu=1.0,
                g_uv=0.0,
                g_vv=1.0,
            )
            for batch in range(5)
        ]
        children[(trials, step)] = [
            dict(
                dimension=2,
                radius=2,
                p=0.4,
                trials=2048,
                measurement_seed=stable_seed(profile["seed"], 2, 2, 0.4, "measurement"),
                histogram=[1024, 512, 512],
                boundary_hits=512,
                rate=0.25,
                ci95=list(wilson95(512, 2048)),
                geometry=batches,
            )
        ]
    return children, profile


def test_verified_measurement_is_reported_once_and_all_four_levels_are_retained(study):
    children, profile = study
    before = deepcopy(children)

    result = aggregate(children, profile)[0]

    assert result["measurement"]["trials"] == 2048
    assert result["measurement_duplicates_verified"] == 4
    assert len(result["levels"]) == 4 and sum(len(level["geometry"]) for level in result["levels"]) == 20
    assert result["status"] == "limited_variation" and result["fine_accepted"] == 5
    assert children == before


@pytest.mark.parametrize(
    "first,second", [([[1, 0.5], [0.5, 1]], [[1, -0.5], [-0.5, 1]]), ([[1, 0], [0, 3]], [[3, 0], [0, 1]])]
)
@pytest.mark.parametrize("scale", [1e-308, 1.0, 1e307])
def test_equal_traces_do_not_hide_signed_cross_or_diagonal_tensor_changes(first, second, scale):
    with np.errstate(over="raise", invalid="raise"):
        change = tensor_change(np.array(first) * scale, np.array(second) * scale)

    assert change == pytest.approx(np.sqrt(0.8))


def test_zero_denominator_is_indeterminate_but_zero_to_nonzero_is_defined():
    assert tensor_change(np.zeros((2, 2)), np.zeros((2, 2))) is None
    assert tensor_change(np.zeros((2, 2)), np.eye(2)) == 2


@pytest.mark.parametrize("invalid", [np.ones((3, 3)), [[1, 2], [3, 1]], [[np.inf, 0], [0, 1]]])
def test_malformed_or_nonfinite_tensors_fail_explicitly(invalid):
    with pytest.raises(ValueError, match="finite symmetric"):
        tensor_change(np.asarray(invalid), np.eye(2))


def test_primary_comparisons_pair_the_frozen_levels_and_include_signed_cross_terms(study):
    children, profile = study
    for level, rows in children.items():
        for batch in rows[0]["geometry"]:
            batch["g_uv"] = 0.5 if level == (512, 0.01) else -0.5

    result = aggregate(children, profile)[0]

    assert result["status"] == "variation_exceeds_tolerance"
    assert result["comparisons"]["N_at_fine_h"]["changes"] == pytest.approx([np.sqrt(0.8)] * 5)
    assert result["comparisons"]["h_at_fine_N"]["changes"] == [0.0] * 5


@pytest.mark.parametrize(
    "changes,fine,status",
    [
        ([0, 0, 0.25, 0.5, 0.5], 5, "limited_variation"),
        ([0.26] * 5, 5, "variation_exceeds_tolerance"),
        ([0, 0, 0, 0, 0.51], 5, "variation_exceeds_tolerance"),
        ([0] * 5, 4, "indeterminate"),
        ([0] * 4, 5, "indeterminate"),
        ([0, 0, 0, 0, None], 5, "indeterminate"),
    ],
)
def test_frozen_inclusive_tolerances_require_all_five_pairs_and_fine_batches(changes, fine, status):
    assert variation_status([changes, [0] * 5], fine) == status


@pytest.mark.parametrize(
    "problem",
    [
        "missing_level",
        "missing_case",
        "duplicate_case",
        "missing_batch",
        "duplicate_batch",
        "malformed_batch",
        "geometry_seed",
        "geometry_trials",
        "measurement_seed",
        "measurement",
        "duplicate_ci",
    ],
)
def test_incomplete_or_misaligned_children_fail_before_measurement_deduplication(study, problem):
    children, profile = study
    row = children[(512, 0.01)][0]
    if problem == "missing_level":
        children.pop((512, 0.02))
    elif problem == "missing_case":
        children[(512, 0.01)] = []
    elif problem == "duplicate_case":
        children[(512, 0.01)].append(deepcopy(row))
    elif problem == "missing_batch":
        row["geometry"].pop()
    elif problem == "duplicate_batch":
        row["geometry"][0]["batch"] = 1
    elif problem == "malformed_batch":
        row["geometry"][0] = None
    elif problem == "geometry_seed":
        row["geometry"][0]["seed"] += 1
    elif problem == "geometry_trials":
        row["geometry"][0]["requested_trials"] += 1
    elif problem == "measurement_seed":
        row["measurement_seed"] += 1
    elif problem == "duplicate_ci":
        row["ci95"][0] += 0.01
    else:
        row["boundary_hits"] += 1

    with pytest.raises(ValueError):
        aggregate(children, profile)


@pytest.mark.parametrize(
    "problem",
    ["missing_ci", "outside_rate_ci", "wrong_wilson_ci", "malformed_ci", "missing_status", "unknown_status"],
)
def test_consistently_malformed_children_are_rejected_before_deduplication(study, problem):
    children, profile = study
    for rows in children.values():
        row = rows[0]
        if problem == "missing_ci":
            row.pop("ci95")
        elif problem == "outside_rate_ci":
            row["ci95"] = [0.8, 0.9]
        elif problem == "wrong_wilson_ci":
            row["ci95"] = [0.2, 0.3]
        elif problem == "malformed_ci":
            row["ci95"] = [np.nan, 0.3]
        else:
            for batch in row["geometry"]:
                if problem == "missing_status":
                    batch.pop("excluded_reason")
                else:
                    batch["excluded_reason"] = "accepted"

    with pytest.raises(ValueError):
        aggregate(children, profile)


@pytest.mark.parametrize(
    "histogram",
    [
        [2**63 - 1, 2**63 - 1, 0, 1538, 512],
        [2**100, 0, 0, 1536, 512],
        [False, 0, 0, 1536, 512],
        [0.0, 0, 0, 1536, 512],
        [-1, 0, 0, 1537, 512],
        [2049, -513, 0, 0, 512],
    ],
)
def test_raw_histogram_counts_reject_overflow_and_invalid_json_integers(study, histogram):
    children, profile = study
    profile["radii"] = [4]
    for rows in children.values():
        row = rows[0]
        row.update(
            radius=4,
            histogram=histogram,
            measurement_seed=stable_seed(profile["seed"], 2, 4, 0.4, "measurement"),
        )
        for batch in row["geometry"]:
            batch["seed"] = stable_seed(profile["seed"], 2, 4, 0.4, "geometry", batch["batch"])

    with pytest.raises(ValueError):
        aggregate(children, profile)


def test_valid_fixed_width_counts_are_normalized_to_json_python_integers(study):
    children, profile = study
    for rows in children.values():
        row = rows[0]
        for name in ["trials", "boundary_hits"]:
            row[name] = np.int32(row[name])
        row["histogram"] = [np.int32(value) for value in row["histogram"]]

    result = aggregate(children, profile)[0]

    assert type(result["measurement"]["trials"]) is int
    assert type(result["measurement"]["boundary_hits"]) is int
    assert all(type(value) is int for value in result["measurement"]["histogram"])
    json.dumps(result, allow_nan=False)


@pytest.mark.parametrize(
    "field,value",
    [("trials", 2048.0), ("boundary_hits", 512.0), ("trials", True), ("boundary_hits", True)],
)
def test_raw_trial_and_hit_counts_require_integer_types(study, field, value):
    children, profile = study
    for rows in children.values():
        rows[0][field] = value

    with pytest.raises(ValueError, match="counts must be integers"):
        aggregate(children, profile)


@pytest.mark.parametrize("problem", ["support", "missing_tensor", "zero_tensor"])
def test_excluded_missing_or_undefined_tensors_make_a_complete_case_indeterminate(study, problem):
    children, profile = study
    batch = children[(2048, 0.01)][0]["geometry"][0]
    if problem == "support":
        batch["excluded_reason"] = "zero_bin"
    elif problem == "missing_tensor":
        batch.pop("g_uv")
    else:
        for row in children.values():
            row[0]["geometry"][0].update(g_uu=0, g_uv=0, g_vv=0)

    result = aggregate(children, profile)[0]

    assert result["status"] == "indeterminate"
    assert result["comparisons"]["N_at_fine_h"]["changes"][0] is None
    if problem == "support":
        level = next(
            level for level in result["levels"] if level["geometry_trials"] == 2048 and level["step"] == 0.01
        )
        assert level["exclusion_counts"] == {"zero_bin": 1}
