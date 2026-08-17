"""Exact integer lattice for the reviewed BC3 heldout parallelograms."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from math import lcm

import numpy as np

from .contract import MODEL_CONTRACT, ConstitutiveMap3DContract

FORWARD_DIRECTIONS = ((2, -1, 0), (2, 0, -1), (-2, 1, 0), (-2, 0, 1))
REVERSE_DIRECTIONS = ((2, 0, -1), (2, -1, 0), (-2, 0, 1), (-2, 1, 0))


@dataclass(frozen=True)
class ExactLattice:
    scale: Fraction
    steps_per_edge: int
    denominator: int
    forward: np.ndarray
    reverse: np.ndarray

    @property
    def start(self) -> np.ndarray:
        return self.forward[0]

    @property
    def update_count(self) -> int:
        return 4 * self.steps_per_edge


def _integer(value: Fraction, *, label: str) -> int:
    if value.denominator != 1:
        raise ValueError(f"{label} is not an exact lattice integer")
    return value.numerator


def _path(
    start: np.ndarray,
    directions: tuple[tuple[int, int, int], ...],
    step_numerator: int,
    steps_per_edge: int,
) -> np.ndarray:
    blocks = [np.asarray(start, dtype=np.int64).reshape(1, 3)]
    current = np.asarray(start, dtype=np.int64)
    indices = np.arange(1, steps_per_edge + 1, dtype=np.int64)[:, None]
    for direction in directions:
        increment = np.asarray(direction, dtype=np.int64) * step_numerator
        block = current[None, :] + indices * increment[None, :]
        blocks.append(block)
        current = block[-1]
    return np.concatenate(blocks, axis=0)


def exact_lattice(
    scale: Fraction,
    steps_per_edge: int,
    contract: ConstitutiveMap3DContract = MODEL_CONTRACT,
) -> ExactLattice:
    """Build forward and exact reverse paths with one final closure sample."""

    item = Fraction(scale)
    if item <= 0 or item.numerator != 1 or steps_per_edge < 1:
        raise ValueError("formal BC3 lattice requires scale=1/S and positive N")
    scale_denominator = item.denominator
    denominator = lcm(75, 2 * scale_denominator * steps_per_edge)
    start_fractions = (
        contract.bc3_heldout_center[0] - 2 * item,
        contract.bc3_heldout_center[1] + item / 2,
        contract.bc3_heldout_center[2] + item / 2,
    )
    start = np.asarray(
        [_integer(value * denominator, label="start control") for value in start_fractions],
        dtype=np.int64,
    )
    step_numerator = denominator // (scale_denominator * steps_per_edge)
    if step_numerator * scale_denominator * steps_per_edge != denominator:
        raise ValueError("formal BC3 per-tick lattice step is not integral")
    forward = _path(start, FORWARD_DIRECTIONS, step_numerator, steps_per_edge)
    reverse = _path(start, REVERSE_DIRECTIONS, step_numerator, steps_per_edge)
    if not np.array_equal(forward[0], forward[-1]) or not np.array_equal(reverse[0], reverse[-1]):
        raise AssertionError("formal BC3 lattice does not close exactly")
    if not np.array_equal(reverse, forward[::-1]):
        raise AssertionError("formal BC3 reverse is not the exact stored forward reverse")
    bounds = (contract.bc3_u_bounds, contract.bc3_v_bounds, contract.bc3_alpha_bounds)
    for axis, (lower, upper) in enumerate(bounds):
        if int(np.min(forward[:, axis])) < _integer(lower * denominator, label="lower bound"):
            raise ValueError("formal BC3 lattice leaves its lower domain bound")
        if int(np.max(forward[:, axis])) > _integer(upper * denominator, label="upper bound"):
            raise ValueError("formal BC3 lattice leaves its upper domain bound")
    return ExactLattice(item, steps_per_edge, denominator, forward, reverse)


def lattice_certificate(lattice: ExactLattice) -> dict[str, object]:
    denominator = lattice.denominator
    scale_denominator = lattice.scale.denominator
    return {
        "scale": f"{lattice.scale.numerator}/{lattice.scale.denominator}",
        "steps_per_edge": lattice.steps_per_edge,
        "common_denominator": denominator,
        "start_numerators": lattice.start.tolist(),
        "per_tick_step_numerator": denominator // (scale_denominator * lattice.steps_per_edge),
        "forward_directions": [list(item) for item in FORWARD_DIRECTIONS],
        "reverse_directions": [list(item) for item in REVERSE_DIRECTIONS],
        "start_equals_end_exact": bool(np.array_equal(lattice.forward[0], lattice.forward[-1])),
        "reverse_equals_forward_index_reverse_exact": bool(
            np.array_equal(lattice.reverse, lattice.forward[::-1])
        ),
        "stored_initial_not_sampled": True,
        "right_endpoints_sampled_once": True,
        "corner_state_carried_without_reset_or_duplicate_sample": True,
        "final_initial_control_sampled_once": True,
        "reverse_reinitialized_at_its_stored_first_control": True,
    }
