"""Source provenance, complete finite-diagnostic reports, and uncertainty figures."""

import hashlib
import json
import os
import platform
import subprocess
from collections import Counter
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[3]


def capture_provenance() -> dict[str, object]:
    """Capture source state before creating output, with exact runtime dependency versions."""

    def git(*args: str) -> str:
        return subprocess.run(
            ["git", *args], cwd=REPO_ROOT, check=True, capture_output=True, text=True
        ).stdout.rstrip("\n")

    status = git("status", "--porcelain=v1", "--untracked-files=all")
    sources = list(Path(__file__).parent.glob("*.py")) + [Path(__file__).parent / ".gitignore"]
    sources += [
        REPO_ROOT / "cwt-sim/cwt/geometry" / name
        for name in ["psi.py", "metric.py", "curvature.py", "gauge.py"]
    ]
    sources += [
        REPO_ROOT / name
        for name in [
            "requirements.test.txt",
            "cwt-sim/pyproject.toml",
            ".taskmaster/docs/percolation-prospective-profile.json",
        ]
    ]
    return {
        "captured_utc": datetime.now(timezone.utc).isoformat(),
        "git_commit": git("rev-parse", "HEAD"),
        "git_dirty": bool(status),
        "git_status": status.splitlines(),
        "python": platform.python_version(),
        "packages": {
            name: version(name) for name in ["numpy", "scipy", "networkx", "pandas", "matplotlib", "typer"]
        },
        "source_sha256": {
            str(path.relative_to(REPO_ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(sources)
        },
    }


def write_checksums(output: Path) -> None:
    """Hash every retained file except this manifest, linked to the current run status."""
    status = json.loads((output / "STATUS.json").read_text())
    files = {
        str(path.relative_to(output)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(output.rglob("*"))
        if path.is_file() and path.name != "CHECKSUMS.json"
    }
    manifest = {
        "state": status["state"],
        "files": files,
        "protocol_sha256": (output / "protocol.sha256").read_text().strip(),
    }
    (output / "CHECKSUMS.json").write_text(json.dumps(manifest, sort_keys=True, allow_nan=False) + "\n")


def plot_connectivity(output: Path, records: list[dict[str, object]]) -> None:
    """Render two dimension panels with pointwise Wilson95 error bars using Agg."""
    previous = {name: os.environ.get(name) for name in ["MPLCONFIGDIR", "XDG_CACHE_HOME"]}
    os.environ["MPLCONFIGDIR"] = str(output / ".mpl-cache")
    os.environ["XDG_CACHE_HOME"] = str(output / ".cache")
    (output / ".cache").mkdir(exist_ok=True)
    try:
        from matplotlib.backends.backend_agg import FigureCanvasAgg
        from matplotlib.figure import Figure
    finally:
        for name, value in previous.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
    figure = Figure(figsize=(9, 3.8), layout="constrained")
    FigureCanvasAgg(figure)
    for axis, dimension in zip(figure.subplots(1, 2), [2, 3]):
        subset = [row for row in records if row["dimension"] == dimension]
        for p in sorted({row["p"] for row in subset}):
            rows = [row for row in subset if row["p"] == p]
            rates = np.array([row["rate"] for row in rows])
            lower, upper = np.array([row["ci95"] for row in rows]).T
            axis.errorbar(
                [row["radius"] for row in rows],
                rates,
                yerr=np.maximum(0.0, [rates - lower, upper - rates]),
                fmt="o-",
                capsize=3,
                label=f"p={p:g}",
            )
        axis.set(
            title=f"d={dimension}", xlabel="Box radius L", ylabel="P(origin reaches shell L)", ylim=(0, 1)
        )
        axis.grid(alpha=0.25)
        if subset:
            axis.legend()
        else:
            axis.text(0.5, 0.5, "No observations", transform=axis.transAxes, ha="center")
    figure.suptitle("Finite boxes: pointwise 95% Wilson intervals")
    figure.savefig(output / "connectivity.png", dpi=160)


def _range(values: list[float]) -> str:
    return f"{min(values):.6g}–{max(values):.6g}" if values else "excluded"


def write_report(
    output: Path,
    protocol: dict[str, object],
    records: list[dict[str, object]],
    controls: dict[str, object],
    provenance: dict[str, object],
) -> None:
    """Report every configuration, retained batch variability, exact controls, and source limits."""
    parameters = protocol["parameters"]
    expected = len(parameters["radii"]) * sum(
        len(parameters[f"probabilities_{d}d"]) for d in parameters["dimensions"]
    )
    lines = [
        "# Finite-size percolation",
        "",
        "Run status: complete.",
        "",
        protocol["limitations"],
        "",
        "The source theorem is θ(p_c)=0 for independent nearest-neighbor bond percolation on Z^d, "
        "d≥2. Newly resolved dimensions are 3–10; the 2D case was known. It gives neither exact "
        "3D thresholds nor critical exponents.",
        "",
        f"[Pinned primary release]({protocol['references']['proof']}) reports machine/kernel verification. "
        "It did not claim independent human review; this benchmark did not rerun the formal proof.",
        "",
        "2D p_c=0.5 is exact. The 3D reference ≈0.2488 is a numerical approximation, "
        "so this scan cannot test the exact-critical theorem. "
        "[Numerical reference](https://doi.org/10.1103/PhysRevE.87.052107).",
        "",
        f"Recorded {len(records)}/{expected} configurations. Frozen [protocol](protocol.json) SHA256: "
        f"`{(output / 'protocol.sha256').read_text().strip()}`; archived before sampling.",
        "",
        protocol["model"],
        protocol["event"],
        protocol["state"],
        protocol["chart"],
        protocol["streams"],
        protocol["coupling"],
        "",
        "Frozen sample profile:",
        "",
        "```json",
        json.dumps(parameters, sort_keys=True),
        "```",
        "",
        "Each rate has a pointwise Wilson95 interval from raw hits/trials; these are not simultaneous "
        "bands. Geometry uses independent batch streams and no smoothing. Real states have zero Ω; "
        "a nonzero metric measures encoding sensitivity. Ranges across accepted batches show sampling "
        "variation, not metric confidence intervals. Exclusions remain in [full raw records](records.json).",
        "",
        "![Origin-to-shell connectivity with pointwise uncertainty](connectivity.png)",
        "",
        "| d | L | p | hits/trials | rate | Wilson95 | Accepted batches | tr(g) range | Ω range | "
        "exclusions |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in records:
        batches = row["geometry"]
        accepted = [batch for batch in batches if batch["excluded_reason"] is None]
        exclusions = dict(Counter(batch["excluded_reason"] for batch in batches if batch["excluded_reason"]))
        lo, hi = row["ci95"]
        lines.append(
            f"| {row['dimension']} | {row['radius']} | {row['p']} | "
            f"{row['boundary_hits']}/{row['trials']} | {row['rate']:.5f} | [{lo:.5f}, {hi:.5f}] | "
            f"{len(accepted)}/{len(batches)} | {_range([batch['trace_g'] for batch in accepted])} | "
            f"{_range([batch['omega'] for batch in accepted])} | {exclusions} |"
        )
    lines += [
        "",
        "Exclusion reasons: chart_outside_open_domain, zero_bin, low_overlap, nonfinite_estimator. "
        "Per-corner raw histograms/support, actual/requested counts, overlap, and batch seeds are retained.",
        "",
        "Exact controls use the same encoding on the lattice-embedded chain "
        "(0,0)→(1,0)→(1,1)→(1,2): q=[1-u,u(1-v²),uv²], u=.4, v=.6, h=.0001. "
        "The metric has two positive diagonal entries and Ω=0.",
        "",
        "| tensor element | analytic | CGT estimator |",
        "| --- | --- | --- |",
    ]
    chain, diamond = controls["chain"], controls["diamond"]
    for name in ["g_uu", "g_uv", "g_vv", "omega"]:
        lines.append(f"| {name} | {chain['analytic'][name]:.8g} | {chain[name]:.8g} |")
    lines += [
        "",
        "Additive gluing: independent four-edge diamond, exhaustive 16 configurations. "
        f"Weights {diamond['weights']}; P(o↔b)={diamond['p_o_b']:.7g}, P(o↔A)={diamond['p_o_A']:.7g}, "
        f"t=max_a P(a↮b)={diamond['t']:.7g}; lower bound={diamond['bound']:.7g}, "
        f"slack={diamond['slack']:.7g}, passed={diamond['passed']}. "
        "This finite correctness check is not a general proof. [Control details](controls.json).",
        "",
        f"Source commit `{provenance['git_commit']}`; source dirty={provenance['git_dirty']}. "
        "[Provenance](provenance.json) includes source SHA256 values and pre-output Git status.",
        "",
        "```text",
        "\n".join(provenance["git_status"]) or "(clean)",
        "```",
        "",
        f"Python {provenance['python']}; versions: {json.dumps(provenance['packages'], sort_keys=True)}.",
        "[Artifact checksums](CHECKSUMS.json) include STATUS.json and retained files except this manifest.",
    ]
    (output / "REPORT.md").write_text("\n".join(lines) + "\n")
