"""Standalone finite-box benchmark with a protocol frozen before sampling."""

import hashlib
import json
import re
from pathlib import Path

import numpy as np
import typer

from experiments.percolation_finite_size import model
from experiments.percolation_finite_size.geometry import controls, sample_geometry

ARTIFACT_ROOT = Path(__file__).resolve().parent / "artifacts"
PROOF_COMMIT = "795efb86f191735c5481675763537cfb4ff37e55"
PROOF = f"https://github.com/anthropics/formal-math/blob/{PROOF_COMMIT}/percolation/README.md"
LIMITATIONS = (
    "Finite reference diagnostic only; no theorem, ridge, exponent, or CWT validation. "
    "The approximate 3D reference cannot evaluate the exact-critical theorem. "
    "Wilson95 intervals are pointwise; finite radius and sampling noise limit inference. "
    "Real square-root encoding has zero Berry curvature; no smoothing or ridge fitting."
)
app = typer.Typer(help="Measure origin-to-shell connectivity and real shell-state geometry.")


def _json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n")


def _reserve(run_name: str) -> Path:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}", run_name):
        raise typer.BadParameter("run-name must be one safe component, 1 to 64 characters")
    if any(path.is_symlink() for path in [ARTIFACT_ROOT, *ARTIFACT_ROOT.parents]):
        raise typer.BadParameter("artifact directory and its ancestors must not be symlinks")
    output = ARTIFACT_ROOT / run_name
    if output.exists() or output.is_symlink():
        raise typer.BadParameter("run already exists; choose a new run-name (no resume or overwrite)")
    ARTIFACT_ROOT.mkdir(parents=True, exist_ok=True)
    output.mkdir()
    return output


def _report(output: Path, records: list[dict[str, object]], state: str) -> None:
    lines = [
        f"# Finite-size percolation\n\nRun status: {state}.\n\n{LIMITATIONS}\n",
        "| d | L | p | boundary hits/trials | rate | Wilson95 | geometry batches retained |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in records:
        lo, hi = row["ci95"]
        lines.append(
            f"| {row['dimension']} | {row['radius']} | {row['p']} | "
            f"{row['boundary_hits']}/{row['trials']} | {row['rate']:.4f} | "
            f"[{lo:.4f}, {hi:.4f}] | {len(row['geometry'])} |"
        )
    lines.append(
        "\nRaw histograms, geometry estimates, support exclusions, and seeds: records.json. "
        f"Protocol hashed before sampling.\n\nProof source: {PROOF}\n"
        "3D numerical reference: https://doi.org/10.1103/PhysRevE.87.052107"
    )
    (output / "REPORT.md").write_text("\n".join(lines) + "\n")


@app.command()
def main(
    run_name: str = typer.Option(...),
    dimensions: str = "2,3",
    radii: str = "2,4,8",
    probabilities_2d: str = "0.4,0.5,0.6",
    probabilities_3d: str = "0.2,0.2488,0.3",
    samples: int = typer.Option(512, min=1),
    geometry_samples: int = typer.Option(512, min=1),
    batches: int = typer.Option(3, min=1),
    step: float = 0.02,
    min_overlap: float = 0.9,
    seed: int = typer.Option(20261001, min=0),
) -> None:
    """Run sorted unique configurations with separate keyed measurement and geometry streams."""
    try:
        ds = sorted({int(value) for value in dimensions.split(",")})
        ls = sorted({int(value) for value in radii.split(",")})
        grids = {
            2: sorted({float(value) + 0.0 for value in probabilities_2d.split(",")}),
            3: sorted({float(value) + 0.0 for value in probabilities_3d.split(",")}),
        }
    except ValueError as exc:
        raise typer.BadParameter("dimensions/radii/probabilities must be comma-separated numbers") from exc
    if any(d not in (2, 3) for d in ds) or min(ls) < 1:
        raise typer.BadParameter("dimensions must be 2/3 and radii positive integers")
    if any(not np.isfinite(p) or not 0 <= p <= 1 for grid in grids.values() for p in grid):
        raise typer.BadParameter("probabilities must be finite and in [0, 1]")
    area = step * step
    if not np.all(np.isfinite([area, min_overlap])) or step <= 0 or area <= 0 or not 0 <= min_overlap <= 1:
        raise typer.BadParameter("step must have positive finite area; min-overlap must be in [0, 1]")
    protocol = {
        "schema_version": 1,
        "parameters": {
            "dimensions": ds,
            "radii": ls,
            "probabilities_2d": grids[2],
            "probabilities_3d": grids[3],
            "samples": samples,
            "geometry_samples": geometry_samples,
            "batches": batches,
            "step": step,
            "min_overlap": min_overlap,
            "seed": seed,
        },
        "model": "Independent nearest-neighbor Bernoulli bonds in nonperiodic [-L,L]^d; no site damage",
        "event": "Origin cluster reaches Chebyshev shell L",
        "state": "sqrt(raw P(R=r)), r=0..L; phase zero",
        "chart": "u on axis0; v on other axes; corners (p,p),(p+h,p),(p+h,p+h),(p,p+h)",
        "streams": "SHA256(base,d,L,p.hex,stream,batch)->PCG64; measurement batch0; independent geometry",
        "coupling": "Within each geometry batch, reuse a full independent-edge uniform array across corners",
        "exclusions": ["chart_outside_open_domain", "zero_bin", "low_overlap", "nonfinite_estimator"],
        "references": {
            "2D_p_c": 0.5,
            "2D_status": "exact",
            "3D_p_c": 0.2488118,
            "3D_status": "numerical estimate",
            "doi": "10.1103/PhysRevE.87.052107",
            "proof": PROOF,
        },
        "proof_review": "Release claims kernel verification; human review not claimed; kernel not rerun here",
        "limitations": LIMITATIONS,
    }
    output = _reserve(run_name)
    records: list[dict[str, object]] = []
    _json(output / "protocol.json", protocol)
    (output / "protocol.sha256").write_text(
        hashlib.sha256((output / "protocol.json").read_bytes()).hexdigest() + "\n"
    )
    _json(output / "STATUS.json", {"state": "incomplete", "error": None})
    _json(output / "records.json", records)
    try:
        _json(output / "controls.json", controls())
        for dimension in ds:
            for radius in ls:
                box = model.build_box(dimension, radius)
                for p in grids[dimension]:
                    measurement_seed = model.stable_seed(seed, dimension, radius, p, "measurement")
                    counts = model.sample_shells(
                        box, p, p, model.draw_uniforms(box, samples, measurement_seed)
                    )
                    row = {
                        "dimension": dimension,
                        "radius": radius,
                        "p": p,
                        "measurement_seed": measurement_seed,
                        "histogram": counts.histogram.tolist(),
                        "boundary_hits": counts.boundary_hits,
                        "trials": counts.trials,
                        "rate": counts.boundary_hits / counts.trials,
                        "ci95": list(model.wilson95(counts.boundary_hits, counts.trials)),
                        "geometry": [],
                    }
                    records.append(row)
                    _json(output / "records.json", records)
                    for batch in range(batches):
                        geometry_seed = model.stable_seed(seed, dimension, radius, p, "geometry", batch)
                        uniforms = model.draw_uniforms(box, geometry_samples, geometry_seed)
                        tile = sample_geometry(box, p, p, step, uniforms, min_overlap)
                        del uniforms
                        row["geometry"].append(
                            {
                                "batch": batch,
                                "seed": geometry_seed,
                                "requested_trials": geometry_samples,
                                **tile,
                            }
                        )
                        _json(output / "records.json", records)
        _report(output, records, "complete")
        _json(output / "STATUS.json", {"state": "complete", "error": None})
    except Exception as exc:
        _json(output / "STATUS.json", {"state": "incomplete", "error": str(exc)})
        _report(output, records, "incomplete")
        raise
    typer.echo(str(output))


if __name__ == "__main__":
    app()
