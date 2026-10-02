"""Paired finite-resolution tensor diagnostics; no asymptotic convergence claims."""

from collections import Counter
from copy import deepcopy
from itertools import product
from numbers import Integral

import numpy as np

from experiments.percolation_finite_size.model import stable_seed, wilson95

MEASUREMENT_FIELDS = ("measurement_seed", "histogram", "boundary_hits", "trials", "rate", "ci95")
EXCLUSION_REASONS = ("chart_outside_open_domain", "zero_bin", "low_overlap", "nonfinite_estimator")


def _count(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, Integral):
        raise ValueError("raw measurement counts must be integers, excluding booleans")
    return int(value)


def tensor_change(first: np.ndarray, second: np.ndarray) -> float | None:
    """Return symmetric full-tensor relative change, or None for a zero denominator."""
    matrices = [np.asarray(matrix, dtype=float) for matrix in [first, second]]
    if any(
        matrix.shape != (2, 2) or not np.all(np.isfinite(matrix)) or not np.array_equal(matrix, matrix.T)
        for matrix in matrices
    ):
        raise ValueError("tensors must be finite symmetric 2x2 matrices")
    scale = max(float(np.max(np.abs(matrix))) for matrix in matrices)
    if scale == 0:
        return None
    a, b = [matrix / scale for matrix in matrices]
    return float(2 * np.linalg.norm(b - a) / (np.linalg.norm(a) + np.linalg.norm(b)))


def variation_status(
    comparisons: list[list[float | None]],
    fine_accepted: int,
    required: int = 5,
    median_limit: float = 0.25,
    maximum_limit: float = 0.5,
) -> str:
    """Apply frozen inclusive descriptive limits only with every required pair and fine batch."""
    if (
        len(comparisons) != 2
        or fine_accepted != required
        or any(len(values) != required or None in values for values in comparisons)
    ):
        return "indeterminate"
    values = np.asarray(comparisons, dtype=float)
    if not np.all(np.isfinite(values)):
        return "indeterminate"
    return (
        "limited_variation"
        if np.all(np.median(values, axis=1) <= median_limit)
        and np.all(np.max(values, axis=1) <= maximum_limit)
        else "variation_exceeds_tolerance"
    )


def _tensor(batch: dict[str, object]) -> np.ndarray | None:
    entries = [batch.get(name) for name in ["g_uu", "g_uv", "g_vv"]]
    if batch["excluded_reason"] is not None or None in entries:
        return None
    uu, uv, vv = np.asarray(entries, dtype=float)
    return np.array([[uu, uv], [uv, vv]]) if np.all(np.isfinite([uu, uv, vv])) else None


def aggregate(
    children: dict[tuple[int, float], list[dict[str, object]]],
    profile: dict[str, object],
) -> list[dict[str, object]]:
    """Verify complete paired children before deduplicating measurements and classifying variation."""
    if len(profile["geometry_trials"]) != 2 or len(profile["steps"]) != 2:
        raise ValueError("study requires two sample counts and two step sizes")
    levels = sorted(product(profile["geometry_trials"], profile["steps"]))
    if len(levels) != 4 or len(set(levels)) != 4 or set(children) != set(levels):
        raise ValueError("study requires exactly the four frozen N/h levels")
    expected = {
        (d, radius, p)
        for d in profile["dimensions"]
        for radius in profile["radii"]
        for p in profile[f"probabilities_{d}d"]
    }
    indexed = {}
    for level, rows in children.items():
        cases = [(row.get("dimension"), row.get("radius"), row.get("p")) for row in rows]
        if len(cases) != len(expected) or set(cases) != expected:
            raise ValueError("each child must contain every frozen case exactly once")
        indexed[level] = dict(zip(cases, rows))
    summaries = []
    fine = (max(profile["geometry_trials"]), min(profile["steps"]))
    pairs = {
        "N_at_fine_h": ((min(profile["geometry_trials"]), fine[1]), fine),
        "h_at_fine_N": ((fine[0], max(profile["steps"])), fine),
    }
    for dimension, radius, p in sorted(expected):
        tensors, retained, measurement = {}, [], None
        for level in levels:
            row = indexed[level][(dimension, radius, p)]
            current = {name: row.get(name) for name in MEASUREMENT_FIELDS}
            raw_histogram = current["histogram"]
            if not isinstance(raw_histogram, (list, tuple)) or len(raw_histogram) != radius + 1:
                raise ValueError("child histogram must contain one raw count per shell")
            histogram = [_count(value) for value in raw_histogram]
            trials, hits = [_count(current[name]) for name in ["trials", "boundary_hits"]]
            current.update(histogram=histogram, trials=trials, boundary_hits=hits)
            if (
                trials <= 0
                or trials != profile["measurement_trials"]
                or not 0 <= hits <= trials
                or any(not 0 <= value <= trials for value in histogram)
                or sum(histogram) != trials
                or hits != histogram[-1]
                or current["rate"] != hits / trials
                or current["measurement_seed"]
                != stable_seed(profile["seed"], dimension, radius, p, "measurement")
            ):
                raise ValueError("child measurement counts/seed do not match the frozen profile")
            interval = np.asarray(current["ci95"], dtype=float)
            if (
                interval.shape != (2,)
                or not np.all(np.isfinite(interval))
                or np.any((interval < 0) | (interval > 1))
                or not interval[0] <= current["rate"] <= interval[1]
                or not np.allclose(
                    interval, wilson95(current["boundary_hits"], current["trials"]), rtol=1e-10, atol=1e-12
                )
            ):
                raise ValueError(
                    "child ci95 must be a finite rate-containing Wilson95 interval from raw counts"
                )
            if measurement is not None and current != measurement:
                raise ValueError("repeated child measurements differ; never pool duplicates")
            measurement = current
            batches = row.get("geometry")
            count = profile["geometry_batches"]
            if (
                not isinstance(batches, list)
                or len(batches) != count
                or any(not isinstance(batch, dict) for batch in batches)
                or {b.get("batch") for b in batches} != set(range(count))
            ):
                raise ValueError("every child case must have each frozen batch exactly once")
            batches = sorted(batches, key=lambda batch: batch["batch"])
            for batch in batches:
                if "excluded_reason" not in batch:
                    raise ValueError("every geometry batch requires an explicit excluded_reason")
                reason = batch["excluded_reason"]
                if reason is not None and (not isinstance(reason, str) or reason not in EXCLUSION_REASONS):
                    raise ValueError("excluded_reason must be null or a recognized exclusion reason")
                seed = stable_seed(profile["seed"], dimension, radius, p, "geometry", batch["batch"])
                if (
                    batch.get("seed") != seed
                    or batch.get("requested_trials") != level[0]
                    or batch.get("trials") != (0 if reason == "chart_outside_open_domain" else level[0])
                ):
                    raise ValueError("geometry seed/trial counts do not align across the four levels")
            tensors[level] = [_tensor(batch) for batch in batches]
            retained.append(
                {
                    "geometry_trials": level[0],
                    "step": level[1],
                    "geometry": deepcopy(batches),
                    "exclusion_counts": dict(
                        Counter(b["excluded_reason"] for b in batches if b.get("excluded_reason"))
                    ),
                }
            )
        comparisons = {}
        for name, (left, right) in pairs.items():
            changes = [
                tensor_change(a, b) if a is not None and b is not None else None
                for a, b in zip(tensors[left], tensors[right])
            ]
            defined = [change for change in changes if change is not None]
            comparisons[name] = {
                "changes": changes,
                "defined_pairs": len(defined),
                "joint_accepted": sum(
                    a is not None and b is not None for a, b in zip(tensors[left], tensors[right])
                ),
                "median": float(np.median(defined)) if defined else None,
                "maximum": max(defined) if defined else None,
            }
        fine_accepted = sum(tensor is not None for tensor in tensors[fine])
        status = variation_status(
            [comparison["changes"] for comparison in comparisons.values()],
            fine_accepted,
            profile["required_joint_batches"],
            profile["median_change_tolerance"],
            profile["maximum_change_tolerance"],
        )
        summaries.append(
            {
                "dimension": dimension,
                "radius": radius,
                "p": p,
                "measurement": deepcopy(measurement),
                "measurement_duplicates_verified": len(levels),
                "levels": retained,
                "comparisons": comparisons,
                "fine_accepted": fine_accepted,
                "status": status,
            }
        )
    return summaries
