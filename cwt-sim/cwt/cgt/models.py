from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Mapping

import numpy as np


@dataclass(frozen=True)
class BranchState:
    p: np.ndarray
    theta: np.ndarray
    kernel: np.ndarray
    extras: dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class CandidateBranch:
    branch_id: str
    state: BranchState
    metadata: dict[str, float | str] = field(default_factory=dict)


CandidateStatesFn = Callable[[float, float], list[CandidateBranch]]
SoftnessFn = Callable[[float, float], float]
SeedBranchFn = Callable[[tuple[float, float]], str | None]


@dataclass(frozen=True)
class BenchmarkDefinition:
    benchmark_id: str
    slug: str
    description: str
    expected_behavior: str
    expected_regime: str
    control_names: tuple[str, str]
    control_bounds: tuple[tuple[float, float], tuple[float, float]]
    candidate_states_fn: CandidateStatesFn
    primary_observable: str
    secondary_observable: str | None
    default_loop_centers: tuple[tuple[float, float], ...]
    default_loop_side_lengths: tuple[float, ...]
    softness_fn: SoftnessFn
    seed_branch_ids: Mapping[str, str]
    canonical_branch_id: str

    def branch_state_fn(self, u: float, v: float) -> BranchState:
        candidates = self.candidate_states_fn(float(u), float(v))
        for candidate in candidates:
            if candidate.branch_id == self.canonical_branch_id:
                return candidate.state
        return candidates[0].state

    def resolve_candidate_by_id(self, u: float, v: float, branch_id: str) -> CandidateBranch | None:
        for candidate in self.candidate_states_fn(float(u), float(v)):
            if candidate.branch_id == branch_id:
                return candidate
        return None


@dataclass(frozen=True)
class ScanConfig:
    mesh: int = 9
    overlap_floor: float = 0.94
    coherence_floor: float = 0.32
    branch_residual_max: float = 0.38
    branch_ambiguity_gap: float = 0.05
    branch_hysteresis_margin: float = 0.025


@dataclass(frozen=True)
class LoopConfig:
    shape: str = "square"
    steps_per_segment: int = 24
    phase_relaxation: float = 0.35
    current_phase_gain: float = 0.45
    use_excess_circulation: bool = True
    overlap_floor: float = 0.94
    coherence_floor: float = 0.32
    adiabatic_max: float = 0.28
    branch_residual_max: float = 0.38
    branch_ambiguity_gap: float = 0.05
    branch_hysteresis_margin: float = 0.025
    centers: tuple[tuple[float, float], ...] | None = None
    side_lengths: tuple[float, ...] | None = None
