"""Independent finite-box connectivity checks for the percolation benchmark."""

from itertools import product

import numpy as np
import pytest

from experiments.percolation_finite_size.model import (
    build_box,
    cluster_radius,
    draw_uniforms,
    sample_shells,
    stable_seed,
    wilson95,
)


@pytest.mark.parametrize("dimension,radius", [(2, 1), (2, 2), (3, 1), (3, 2)])
def test_box_is_an_unwrapped_nearest_neighbor_lattice(dimension, radius):
    box = build_box(dimension, radius)

    assert len(box.vertices) == (2 * radius + 1) ** dimension
    assert len(box.edges) == dimension * (2 * radius) * (2 * radius + 1) ** (dimension - 1)
    assert len(box.adjacency[box.origin]) == 2 * dimension
    assert np.array_equal(box.vertices[box.origin], np.zeros(dimension))
    differences = box.vertices[box.edges[:, 1]] - box.vertices[box.edges[:, 0]]
    assert np.all(np.sum(np.abs(differences), axis=1) == 1)
    assert np.array_equal(np.argmax(differences, axis=1), box.edge_axes)


def test_handcrafted_cluster_radii_include_closed_open_and_two_step_path():
    box = build_box(2, 2)
    closed = np.zeros(len(box.edges), dtype=bool)
    path = closed.copy()
    for first, second in [((0, 0), (1, 0)), ((1, 0), (2, 0))]:
        for index, (a, b) in enumerate(box.edges):
            if tuple(box.vertices[a]) == first and tuple(box.vertices[b]) == second:
                path[index] = True

    assert cluster_radius(box, closed) == 0
    assert cluster_radius(box, np.ones(len(box.edges), dtype=bool)) == 2
    assert cluster_radius(box, path) == 2


@pytest.mark.parametrize("dimension,axis", [(2, 0), (2, 1), (3, 2)])
def test_axis_probability_uses_reusable_uniforms(dimension, axis):
    box = build_box(dimension, 1)
    uniforms = np.ones((1, len(box.edges))) * 0.9
    edge = next(edge for _, edge in box.adjacency[box.origin] if box.edge_axes[edge] == axis)
    uniforms[0, edge] = 0.25

    assert sample_shells(box, 0.5, 0.0, uniforms).boundary_hits == (axis == 0)
    assert sample_shells(box, 0.0, 0.5, uniforms).boundary_hits == (axis > 0)
    assert np.all(uniforms[0, np.arange(len(box.edges)) != edge] == 0.9)


@pytest.mark.parametrize("probability,radius", [(0.0, 0), (1.0, 2)])
def test_probability_endpoints_produce_exact_unsmoothed_histograms(probability, radius):
    box = build_box(2, 2)

    result = sample_shells(box, probability, probability, draw_uniforms(box, 4, 123))

    assert result.histogram.sum() == result.trials == 4
    assert result.histogram[radius] == 4


@pytest.mark.parametrize("dimension", [2, 3])
def test_radius_one_exhaustive_origin_star_matches_exact_probability(dimension):
    box = build_box(dimension, 1)
    patterns = np.asarray(list(product([False, True], repeat=2 * dimension)))
    uniforms = np.full((len(patterns), len(box.edges)), 0.75)
    uniforms[:, [edge for _, edge in box.adjacency[box.origin]]] = np.where(patterns, 0.25, 0.75)

    result = sample_shells(box, 0.5, 0.5, uniforms)

    assert result.boundary_hits == len(patterns) - 1
    assert result.trials == len(patterns)
    assert result.histogram.tolist() == [1, len(patterns) - 1]
    assert result.boundary_hits / result.trials == 1 - (1 - 0.5) ** (2 * dimension)


def test_keyed_seeds_and_samples_are_reproducible_under_order_changes():
    points = list(product([2, 3], [1, 2], [0.2, 0.5]))
    forward = {point: stable_seed(17, *point, "measurement") for point in points}
    reverse = {point: stable_seed(17, *point, "measurement") for point in reversed(points)}
    box = build_box(2, 1)

    assert forward == reverse
    assert len(set(forward.values())) == len(points)
    assert stable_seed(17, 2, 1, 0.5, "geometry") != forward[(2, 1, 0.5)]
    assert stable_seed(17, 2, 1, 0.5, "measurement", 1) != forward[(2, 1, 0.5)]
    assert np.array_equal(draw_uniforms(box, 5, 123), draw_uniforms(box, 5, 123))


@pytest.mark.parametrize("dimension,radius", [(1, 1), (4, 1), (2, 0), (2, 1.5)])
def test_invalid_box_domains_fail(dimension, radius):
    with pytest.raises(ValueError):
        build_box(dimension, radius)


@pytest.mark.parametrize("probability", [-0.01, 1.01, float("nan"), float("inf")])
def test_invalid_sampling_domains_fail(probability):
    box = build_box(2, 1)

    with pytest.raises(ValueError):
        sample_shells(box, probability, 0.5, draw_uniforms(box, 1, 123))


@pytest.mark.parametrize("shape,value", [((0, 12), 0.5), ((1, 11), 0.5), ((1, 12), np.nan), ((1, 12), 1.0)])
def test_invalid_full_uniform_arrays_fail(shape, value):
    with pytest.raises(ValueError):
        sample_shells(build_box(2, 1), 0.5, 0.5, np.full(shape, value))


def test_zero_samples_fail():
    box = build_box(2, 1)

    with pytest.raises(ValueError):
        draw_uniforms(box, 0, 123)


def test_wilson_interval_uses_unsmoothed_hits():
    assert wilson95(0, 10) == pytest.approx((0.0, 0.2775327999))
    assert wilson95(10, 10) == pytest.approx((0.7224672001, 1.0))
    assert wilson95(5, 10) == pytest.approx((0.2365930905, 0.7634069095))


@pytest.mark.parametrize("trials", [np.int32(24000), np.int64(10_000_000_000)])
def test_wilson_numpy_integer_counts_do_not_overflow(trials):
    z_squared = 3.8414588206941254

    with np.errstate(over="raise", invalid="raise"):
        interval = wilson95(type(trials)(0), trials)

    assert interval == pytest.approx((0, z_squared / (int(trials) + z_squared)), rel=1e-12, abs=1e-20)
