"""Serial paired study using the immutable reviewed convergence profile."""

import hashlib
import json
import re
from itertools import product
from pathlib import Path
from time import perf_counter

import typer

from experiments.percolation_finite_size import convergence_artifacts as study_artifacts, run
from experiments.percolation_finite_size.convergence import aggregate

ARTIFACT_ROOT = Path(__file__).resolve().parent / "artifacts"
PROFILE_PATH = Path(__file__).resolve().parents[3] / ".taskmaster/docs/percolation-convergence-profile.json"
FROZEN_SHA256 = "0138edc16711597088cf10811eda2017dc3227cf4cf04112bb7e2b73e38b2e7c"
app = typer.Typer(help="Run the frozen paired percolation study serially; no parameter overrides.")


def _json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n")


def _reserve(name: str) -> Path:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}", name):
        raise typer.BadParameter("run-name must be one safe component, 1 to 64 characters")
    if any(path.is_symlink() for path in [ARTIFACT_ROOT, *ARTIFACT_ROOT.parents]):
        raise typer.BadParameter("artifact directory and its ancestors must not be symlinks")
    output = ARTIFACT_ROOT / name
    if output.exists() or output.is_symlink():
        raise typer.BadParameter("run already exists; no resume or overwrite")
    ARTIFACT_ROOT.mkdir(parents=True, exist_ok=True)
    output.mkdir()
    return output


def _report(output: Path, status: dict, summaries: list[dict], profile: dict) -> None:
    lines = [
        f"# Paired percolation study\n\nRun status: {status['state']}.\n",
        profile["interpretation"],
        "\nRepeated measurements require verification across four children; report once and never pool. "
        "Wilson95 intervals are pointwise. All child records and excluded batches remain archived.\n",
        "| child | state | raw records |",
        "| --- | --- | --- |",
    ]
    for child in status["children"]:
        name = child["name"]
        lines.append(f"| {name} | {child['state']} | [records](children/{name}/records.json) |")
    lines.extend(
        [
            "\n| d | L | p | hits/trials | rate | Wilson95 | paired disposition |",
            "| --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for row in summaries:
        measurement = row["measurement"]
        lines.append(
            f"| {row['dimension']} | {row['radius']} | {row['p']} | "
            f"{measurement['boundary_hits']}/{measurement['trials']} | {measurement['rate']:.6g} | "
            f"{measurement['ci95']} | {row['status']} |"
        )
    if status["error"]:
        lines.append(f"\nFailure: {status['error']}. Completed child diagnostics remain available above.")
    if not summaries:
        lines.append("\nPaired aggregation has not completed; duplicate measurements are not yet verified.")
    lines.append(
        "\n[Aggregated tensors and all four levels](aggregate.json); profile/protocol frozen before children."
    )
    (output / "REPORT.md").write_text("\n".join(lines) + "\n")


def _child(output: Path, plan: dict, profile: dict) -> None:
    # The existing runner has a fixed artifact root; bind it only for this serial call.
    original = run.ARTIFACT_ROOT
    run.ARTIFACT_ROOT = output / "children"
    try:
        run.main(
            run_name=plan["name"],
            dimensions=",".join(map(str, profile["dimensions"])),
            radii=",".join(map(str, profile["radii"])),
            probabilities_2d=",".join(map(str, profile["probabilities_2d"])),
            probabilities_3d=",".join(map(str, profile["probabilities_3d"])),
            samples=profile["measurement_trials"],
            geometry_samples=plan["geometry_trials"],
            batches=profile["geometry_batches"],
            step=plan["step"],
            min_overlap=profile["min_overlap"],
            seed=profile["seed"],
        )
    finally:
        run.ARTIFACT_ROOT = original


@app.command()
def main(run_name: str = typer.Option(...)) -> None:
    """Execute exactly the reviewed profile, preserving every incomplete child on failure."""
    started = perf_counter()
    source = PROFILE_PATH.read_bytes()
    if hashlib.sha256(source).hexdigest() != FROZEN_SHA256:
        raise typer.BadParameter("frozen profile SHA256 mismatch; no study started")
    profile = json.loads(source)
    plans = [
        dict(name=f"n{n}_h{h:g}", geometry_trials=n, step=h)
        for n, h in sorted(product(profile["geometry_trials"], profile["steps"]))
    ]
    provenance = study_artifacts.capture_provenance()
    output = _reserve(run_name)
    (output / "profile.json").write_bytes(source)
    (output / "profile.sha256").write_text(FROZEN_SHA256 + "\n")
    _json(output / "protocol.json", dict(schema_version=1, profile=profile, children=plans))
    (output / "protocol.sha256").write_text(
        hashlib.sha256((output / "protocol.json").read_bytes()).hexdigest() + "\n"
    )
    status = dict(state="incomplete", error=None, children=[dict(**plan, state="pending") for plan in plans])
    _json(output / "STATUS.json", status)
    children, summaries = {}, []
    try:
        provenance.update(
            profile_sha256=FROZEN_SHA256, protocol_sha256=(output / "protocol.sha256").read_text().strip()
        )
        _json(output / "provenance.json", provenance)
        for plan in status["children"]:
            plan["state"] = "running"
            _json(output / "STATUS.json", status)
            child_started = perf_counter()
            try:
                _child(output, plan, profile)
            finally:
                plan["elapsed_seconds"] = perf_counter() - child_started
            child_output = output / "children" / plan["name"]
            if json.loads((child_output / "STATUS.json").read_text())["state"] != "complete":
                raise RuntimeError(f"child {plan['name']} did not complete")
            children[(plan["geometry_trials"], plan["step"])] = json.loads(
                (child_output / "records.json").read_text()
            )
            plan["state"] = "complete"
            _json(output / "STATUS.json", status)
        summaries = aggregate(children, profile)
        _json(output / "aggregate.json", summaries)
        study_artifacts.plot_variation(output, summaries, profile)
        status["state"] = "complete"
        study_artifacts.write_report(output, profile, summaries, status, provenance)
        status["elapsed_seconds"] = perf_counter() - started
        _json(output / "STATUS.json", status)
        study_artifacts.write_checksums(output)
    except Exception as exc:
        for plan in status["children"]:
            if plan["state"] == "running":
                plan["state"] = "incomplete"
        status.update(state="incomplete", error=str(exc))
        status["elapsed_seconds"] = perf_counter() - started
        _json(output / "STATUS.json", status)
        _report(output, status, summaries, profile)
        try:
            study_artifacts.write_checksums(output)
        except Exception as checksum_error:
            manifest = output / "CHECKSUMS.json"
            if manifest.exists():
                manifest.rename(output / "CHECKSUMS.partial.json")
            _json(output / "CHECKSUMS_FAILURE.json", dict(state="incomplete", error=str(checksum_error)))
        raise
    typer.echo(str(output))


if __name__ == "__main__":
    app()
