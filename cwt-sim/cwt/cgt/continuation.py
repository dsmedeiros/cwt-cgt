from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ._geom_compat import branch_distance
from .models import BenchmarkDefinition, CandidateBranch, LoopConfig, ScanConfig


@dataclass
class ContinuationChoice:
    candidate: CandidateBranch
    residual: float
    margin_gap: float
    candidate_ids: list[str]
    candidate_count: int
    used_preferred_id: bool


@dataclass
class SweepResult:
    branch_ids: list[list[str]]
    states: list[list]
    residuals: np.ndarray
    margin_gaps: np.ndarray
    candidate_counts: np.ndarray


def _candidate_residual(candidate: CandidateBranch, reference_states: list) -> float:
    if not reference_states:
        return 0.0
    distances = [branch_distance(candidate.state, ref_state) for ref_state in reference_states]
    return float(np.mean(distances))


def _choose_candidate(
    candidates: list[CandidateBranch],
    reference_states: list,
    preferred_branch_id: str | None,
    hysteresis_margin: float,
) -> ContinuationChoice:
    scored = [(candidate, _candidate_residual(candidate, reference_states)) for candidate in candidates]
    scored.sort(key=lambda item: (item[1], item[0].branch_id))
    best_candidate, best_residual = scored[0]
    second_residual = scored[1][1] if len(scored) > 1 else best_residual
    margin_gap = float(second_residual - best_residual)
    used_preferred_id = False

    if preferred_branch_id is not None:
        for candidate, residual in scored:
            if candidate.branch_id == preferred_branch_id and residual <= best_residual + hysteresis_margin:
                best_candidate = candidate
                best_residual = residual
                used_preferred_id = True
                break

    return ContinuationChoice(
        candidate=best_candidate,
        residual=float(best_residual),
        margin_gap=margin_gap,
        candidate_ids=[candidate.branch_id for candidate, _ in scored],
        candidate_count=len(scored),
        used_preferred_id=used_preferred_id,
    )


def _seed_branch_id(benchmark: BenchmarkDefinition, sweep: str) -> str:
    return benchmark.seed_branch_ids.get(sweep, benchmark.canonical_branch_id)


def _assigned_neighbor_states(
    states: list[list],
    i: int,
    j: int,
    direction: str,
) -> list:
    references = []
    rows = len(states)
    cols = len(states[0]) if rows else 0
    offsets = [(-1, 0), (0, -1)] if direction == "forward" else [(1, 0), (0, 1)]
    for di, dj in offsets:
        ii = i + di
        jj = j + dj
        if 0 <= ii < rows and 0 <= jj < cols:
            ref = states[ii][jj]
            if ref is not None:
                references.append(ref)
    return references


def _sweep_mesh(
    benchmark: BenchmarkDefinition,
    grid_u: np.ndarray,
    grid_v: np.ndarray,
    direction: str,
    config: ScanConfig,
) -> SweepResult:
    rows = grid_u.size
    cols = grid_v.size
    states: list[list] = [[None for _ in range(cols)] for _ in range(rows)]
    branch_ids: list[list[str]] = [["unresolved" for _ in range(cols)] for _ in range(rows)]
    residuals = np.full((rows, cols), np.nan, dtype=float)
    margin_gaps = np.full((rows, cols), np.nan, dtype=float)
    candidate_counts = np.zeros((rows, cols), dtype=int)

    order_i = range(rows) if direction == "forward" else range(rows - 1, -1, -1)
    order_j = range(cols) if direction == "forward" else range(cols - 1, -1, -1)
    seed_id = _seed_branch_id(benchmark, direction)

    for i in order_i:
        for j in order_j:
            u = float(grid_u[i])
            v = float(grid_v[j])
            candidates = benchmark.candidate_states_fn(u, v)
            refs = _assigned_neighbor_states(states, i, j, direction)
            preferred = None
            if refs:
                neighbor_ids = []
                for di, dj in [(-1, 0), (0, -1)] if direction == "forward" else [(1, 0), (0, 1)]:
                    ii = i + di
                    jj = j + dj
                    if 0 <= ii < rows and 0 <= jj < cols and states[ii][jj] is not None:
                        neighbor_ids.append(branch_ids[ii][jj])
                preferred = neighbor_ids[0] if neighbor_ids else None
            else:
                preferred = seed_id
            choice = _choose_candidate(
                candidates=candidates,
                reference_states=refs,
                preferred_branch_id=preferred,
                hysteresis_margin=config.branch_hysteresis_margin,
            )
            states[i][j] = choice.candidate.state
            branch_ids[i][j] = choice.candidate.branch_id
            residuals[i, j] = choice.residual
            margin_gaps[i, j] = choice.margin_gap
            candidate_counts[i, j] = choice.candidate_count

    return SweepResult(
        branch_ids=branch_ids,
        states=states,
        residuals=residuals,
        margin_gaps=margin_gaps,
        candidate_counts=candidate_counts,
    )


def build_branch_atlas(
    benchmark: BenchmarkDefinition,
    grid_u: np.ndarray,
    grid_v: np.ndarray,
    config: ScanConfig,
) -> dict:
    forward = _sweep_mesh(
        benchmark=benchmark, grid_u=grid_u, grid_v=grid_v, direction="forward", config=config
    )
    backward = _sweep_mesh(
        benchmark=benchmark, grid_u=grid_u, grid_v=grid_v, direction="backward", config=config
    )

    rows = grid_u.size
    cols = grid_v.size
    chosen_states: list[list] = [[None for _ in range(cols)] for _ in range(rows)]
    persistent_ids: list[list[str]] = [["unresolved" for _ in range(cols)] for _ in range(rows)]
    chosen_ids: list[list[str]] = [["unresolved" for _ in range(cols)] for _ in range(rows)]
    disagreement_map = [[False for _ in range(cols)] for _ in range(rows)]
    ambiguous_map = [[False for _ in range(cols)] for _ in range(rows)]
    residual_map = np.full((rows, cols), np.nan, dtype=float)
    ambiguity_score = np.full((rows, cols), np.nan, dtype=float)

    switch_tiles: list[dict[str, float | int | str]] = []

    for i in range(rows):
        for j in range(cols):
            f_id = forward.branch_ids[i][j]
            b_id = backward.branch_ids[i][j]
            f_res = float(forward.residuals[i, j])
            b_res = float(backward.residuals[i, j])
            f_gap = float(forward.margin_gaps[i, j])
            b_gap = float(backward.margin_gaps[i, j])
            candidate_count = int(max(forward.candidate_counts[i, j], backward.candidate_counts[i, j]))

            agree = f_id == b_id
            low_gap = candidate_count > 1 and min(f_gap, b_gap) < config.branch_ambiguity_gap
            high_residual = candidate_count > 1 and max(f_res, b_res) > config.branch_residual_max
            ambiguous = (not agree) or low_gap or high_residual
            disagreement_map[i][j] = not agree
            ambiguous_map[i][j] = ambiguous
            ambiguity_score[i, j] = (
                max(0.0, config.branch_ambiguity_gap - min(f_gap, b_gap)) if candidate_count > 1 else 0.0
            )

            if f_res <= b_res:
                chosen_states[i][j] = forward.states[i][j]
                chosen_ids[i][j] = f_id
                residual_map[i, j] = f_res
            else:
                chosen_states[i][j] = backward.states[i][j]
                chosen_ids[i][j] = b_id
                residual_map[i, j] = b_res

            persistent_ids[i][j] = f_id if agree and not ambiguous else "ambiguous"
            if ambiguous:
                switch_tiles.append(
                    {
                        "u_index": i,
                        "v_index": j,
                        "u": float(grid_u[i]),
                        "v": float(grid_v[j]),
                        "forward_branch_id": f_id,
                        "backward_branch_id": b_id,
                        "forward_residual": f_res,
                        "backward_residual": b_res,
                        "forward_margin_gap": f_gap,
                        "backward_margin_gap": b_gap,
                        "candidate_count": candidate_count,
                    }
                )

    return {
        "forward_branch_id_map": forward.branch_ids,
        "backward_branch_id_map": backward.branch_ids,
        "chosen_branch_id_map": chosen_ids,
        "persistent_branch_id_map": persistent_ids,
        "disagreement_map": disagreement_map,
        "ambiguous_map": ambiguous_map,
        "forward_residual_map": forward.residuals.tolist(),
        "backward_residual_map": backward.residuals.tolist(),
        "forward_margin_gap_map": forward.margin_gaps.tolist(),
        "backward_margin_gap_map": backward.margin_gaps.tolist(),
        "candidate_count_map": forward.candidate_counts.tolist(),
        "chosen_residual_map": residual_map.tolist(),
        "ambiguity_score_map": ambiguity_score.tolist(),
        "switch_tiles": switch_tiles,
        "seed_branches": dict(benchmark.seed_branch_ids),
        "chosen_states": chosen_states,
    }


def continue_path_with_branch_ids(
    benchmark: BenchmarkDefinition,
    path: list[tuple[float, float]],
    config: LoopConfig,
) -> dict:
    states = []
    branch_ids: list[str] = []
    step_log: list[dict] = []
    switch_markers: list[int] = []
    ambiguous_steps: list[int] = []

    previous_state = None
    previous_branch_id = None
    loop_seed_id = benchmark.seed_branch_ids.get("loop", benchmark.canonical_branch_id)

    for index, (u, v) in enumerate(path):
        candidates = benchmark.candidate_states_fn(float(u), float(v))
        refs = [] if previous_state is None else [previous_state]
        preferred = loop_seed_id if previous_state is None else previous_branch_id
        choice = _choose_candidate(
            candidates=candidates,
            reference_states=refs,
            preferred_branch_id=preferred,
            hysteresis_margin=config.branch_hysteresis_margin,
        )
        switched = previous_branch_id is not None and choice.candidate.branch_id != previous_branch_id
        ambiguous = choice.candidate_count > 1 and choice.margin_gap < config.branch_ambiguity_gap
        if choice.candidate_count > 1 and choice.residual > config.branch_residual_max:
            ambiguous = True
        if switched:
            switch_markers.append(index)
        if ambiguous:
            ambiguous_steps.append(index)
        states.append(choice.candidate.state)
        branch_ids.append(choice.candidate.branch_id)
        step_log.append(
            {
                "step_index": index,
                "u": float(u),
                "v": float(v),
                "selected_branch_id": choice.candidate.branch_id,
                "candidate_ids": choice.candidate_ids,
                "candidate_count": choice.candidate_count,
                "residual": float(choice.residual),
                "margin_gap": float(choice.margin_gap),
                "used_preferred_id": bool(choice.used_preferred_id),
                "switched": bool(switched),
                "ambiguous": bool(ambiguous),
            }
        )
        previous_state = choice.candidate.state
        previous_branch_id = choice.candidate.branch_id

    unique_branch_ids = sorted(set(branch_ids))
    return {
        "states": states,
        "branch_ids": branch_ids,
        "unique_branch_ids": unique_branch_ids,
        "switch_markers": switch_markers,
        "ambiguous_steps": ambiguous_steps,
        "step_log": step_log,
        "switch_count": len(switch_markers),
        "ambiguous_step_count": len(ambiguous_steps),
        "seed_branch_id": loop_seed_id,
    }
