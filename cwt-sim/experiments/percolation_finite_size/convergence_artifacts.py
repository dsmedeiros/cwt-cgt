"""Complete paired-study disclosure and descriptive full-tensor figures."""

import hashlib
import json
import os
from pathlib import Path

import numpy as np

from experiments.percolation_finite_size import artifacts, run


def capture_provenance() -> dict:
    result = artifacts.capture_provenance()
    for name in ["percolation-convergence.md", "percolation-convergence-profile.json"]:
        path = artifacts.REPO_ROOT / ".taskmaster/docs" / name
        result["source_sha256"][str(path.relative_to(artifacts.REPO_ROOT))] = hashlib.sha256(
            path.read_bytes()
        ).hexdigest()
    return result


def write_checksums(output: Path) -> None:
    """Extend the existing recursive manifest to include retained child manifests themselves."""
    artifacts.write_checksums(output)
    path = output / "CHECKSUMS.json"
    manifest = json.loads(path.read_text())
    for child in sorted((output / "children").rglob("CHECKSUMS.json")):
        manifest["files"][str(child.relative_to(output))] = hashlib.sha256(child.read_bytes()).hexdigest()
    manifest["cache_policy"] = "Caches are retained and hashed as support files, not scientific results."
    path.write_text(json.dumps(manifest, sort_keys=True, allow_nan=False) + "\n")


def plot_variation(output: Path, rows: list[dict], profile: dict) -> None:
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
    figure = Figure(figsize=(11, 8), layout="constrained")
    FigureCanvasAgg(figure)
    required = profile["required_joint_batches"]
    names = ["N_at_fine_h", "h_at_fine_N"]
    titles = [
        f"N={min(profile['geometry_trials'])}→{max(profile['geometry_trials'])}, h={min(profile['steps'])}",
        f"h={max(profile['steps'])}→{min(profile['steps'])}, N={max(profile['geometry_trials'])}",
    ]
    for dimension, axes in zip([2, 3], figure.subplots(2, 2)):
        for axis, name, title in zip(axes, names, titles):
            subset = [row for row in rows if row["dimension"] == dimension]
            probabilities = sorted({row["p"] for row in subset})
            for index, p in enumerate(probabilities):
                series = sorted([row for row in subset if row["p"] == p], key=lambda row: row["radius"])
                color = f"C{index}"
                xs = [row["radius"] + 0.1 * (index - (len(probabilities) - 1) / 2) for row in series]
                medians = [row["comparisons"][name]["median"] for row in series]
                axis.plot(
                    xs,
                    [np.nan if value is None else value for value in medians],
                    color=color,
                    label=f"p={p:g}",
                )
                for x, row in zip(xs, series):
                    comparison = row["comparisons"][name]
                    defined = [value for value in comparison["changes"] if value is not None]
                    count = comparison["defined_pairs"]
                    y = comparison["median"] if defined else -0.08
                    if defined:
                        marker = "o" if count == required and row["fine_accepted"] == required else "^"
                        axis.errorbar(
                            x,
                            y,
                            yerr=[[y - min(defined)], [max(defined) - y]],
                            fmt=marker,
                            color=color,
                            capsize=3,
                        )
                    else:
                        axis.plot(x, y, "x", color=color)
                    axis.annotate(
                        f"{count}/{required}",
                        (x, y),
                        xytext=(0, 5 + 8 * index),
                        textcoords="offset points",
                        ha="center",
                        fontsize=7,
                        color=color,
                    )
            for limit, style in [
                (profile["median_change_tolerance"], "--"),
                (profile["maximum_change_tolerance"], ":"),
            ]:
                axis.axhline(limit, color="gray", linestyle=style, linewidth=1)
            axis.set(
                title=f"d={dimension}: {title}",
                xlabel="Box radius L (p curves slightly offset)",
                ylabel="Symmetric full-tensor relative change",
                ylim=(-0.15, 2.1),
                xticks=profile["radii"],
            )
            axis.grid(alpha=0.2)
            if subset:
                axis.legend(fontsize=8)
            else:
                axis.text(0.5, 0.5, "No observations", transform=axis.transAxes, ha="center")
    figure.suptitle(
        "Paired medians with descriptive min–max batch ranges (not confidence intervals)\n"
        "o: required support; △: partial support; ×: unsupported below zero; counts: defined/required\n"
        f"Operational limits: median ≤{profile['median_change_tolerance']}, "
        f"maximum ≤{profile['maximum_change_tolerance']}; "
        "no convergence proof",
        fontsize=11,
    )
    figure.savefig(output / "tensor_variation.png", dpi=150)


def _comparison(value: dict, required: int) -> str:
    defined = [change for change in value["changes"] if change is not None]
    interval = f"{min(defined):.6g}–{max(defined):.6g}" if defined else "undefined"
    median = f"{value['median']:.6g}" if defined else "undefined"
    return f"{value['defined_pairs']}/{required}; median {median}; range {interval}"


def write_report(output: Path, profile: dict, rows: list[dict], status: dict, provenance: dict) -> None:
    expected = len(profile["radii"]) * sum(len(profile[f"probabilities_{d}d"]) for d in profile["dimensions"])
    required = profile["required_joint_batches"]
    edges = max(
        d * 2 * radius * (2 * radius + 1) ** (d - 1)
        for d in profile["dimensions"]
        for radius in profile["radii"]
    )
    uniform_mb = max(profile["geometry_trials"]) * edges * 8 / 1e6
    lines = [
        "# Paired finite percolation study\n\nRun status: complete.\n",
        profile["interpretation"],
        "\nThe source theorem θ(p_c)=0 concerns infinite independent nearest-neighbor bond percolation "
        "on Z^d, d≥2, newly resolved for 3–10. Finite boxes provide no CWT validation. "
        f"[Pinned primary release]({run.PROOF}) reports machine verification, not independent human review; "
        "the proof kernel was not rerun here. It gives no exact 3D threshold or exponent.",
        "\n2D bond p_c=0.5 is exact only for the undamaged square lattice. "
        "3D ≈0.2488 is a rounded numerical reference, not exact criticality "
        "([source](https://doi.org/10.1103/PhysRevE.87.052107)).",
        "\nModel/event: independent Bernoulli nearest-neighbor edges in nonperiodic [-L,L]^d; "
        "the origin reaches Chebyshev shell L. Different radii are different finite observables, "
        "not discretization convergence tests. The real square-root shell state has Ω=0; "
        "metric changes measure encoding sensitivity, not Berry-curvature emergence.",
        "\nMeasurement duplicates are verified across four children, reported once, and never pool. "
        "Wilson95 intervals are pointwise, not simultaneous bands. Geometry uses no smoothing. "
        "Tensor change includes signed g_uv. Zero denominators and missing pairs are indeterminate. "
        "All required pairs in both comparisons and all fine batches must be accepted. "
        "Median .25 and maximum .50 are operational descriptive limits, not confidence intervals or proof.",
        f"\nRecorded {len(rows)}/{expected} cases. [Profile](profile.json) SHA256 "
        f"`{(output / 'profile.sha256').read_text().strip()}`; [protocol](protocol.json) SHA256 "
        f"`{(output / 'protocol.sha256').read_text().strip()}`; both frozen before children.",
        "\n```json\n" + json.dumps(profile, sort_keys=True) + "\n```",
        f"\nSerial execution bounds the largest uniform array near {uniform_mb:.3g} MB decimal, "
        "excluding validation temporaries. [STATUS.json](STATUS.json) retains per-child "
        "and total elapsed seconds through reporting, excluding final checksumming. "
        "Caches are support files only.",
        "\n![Paired full-tensor changes](tensor_variation.png)\n",
        "| d | L | p | hits/trials | rate | Wilson95 | N at fine h: pairs, median, range | "
        "h at fine N: pairs, median, range | fine accepted | disposition |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        m = row["measurement"]
        lo, hi = m["ci95"]
        values = [_comparison(row["comparisons"][name], required) for name in ["N_at_fine_h", "h_at_fine_N"]]
        lines.append(
            f"| {row['dimension']} | {row['radius']} | {row['p']} | {m['boundary_hits']}/{m['trials']} | "
            f"{m['rate']:.6g} | [{lo:.6g}, {hi:.6g}] | {values[0]} | {values[1]} | "
            f"{row['fine_accepted']}/{required} | {row['status']} |"
        )
    lines.extend(
        [
            "\nAll four levels and exclusions (including unsupported batches): "
            "[complete aggregate](aggregate.json). Raw histograms, overlaps, tensors, "
            "and seeds remain in children.\n",
            "| d | L | p | geometry N | h | accepted | Ω range | exclusions |",
            "| --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for row in rows:
        for level in row["levels"]:
            accepted = [b for b in level["geometry"] if b["excluded_reason"] is None]
            omega = [b.get("omega") for b in accepted if b.get("omega") is not None]
            limits = f"{min(omega):.6g}–{max(omega):.6g}" if omega else "undefined"
            lines.append(
                f"| {row['dimension']} | {row['radius']} | {row['p']} | {level['geometry_trials']} | "
                f"{level['step']} | {len(accepted)}/{len(level['geometry'])} | {limits} | "
                f"{level['exclusion_counts']} |"
            )
    for child in status["children"]:
        name = child["name"]
        lines.append(
            f"\n[{name}: raw diagnostics](children/{name}/records.json); "
            f"[controls and child report](children/{name}/REPORT.md); "
            f"elapsed {child['elapsed_seconds']:.3f}s."
        )
    lines.extend(
        [
            f"\nSource commit `{provenance['git_commit']}`; source dirty={provenance['git_dirty']}. "
            "[Provenance](provenance.json) archives pre-child Git status, source hashes, "
            "profile/protocol hashes, and runtime.",
            "\n```text\n" + ("\n".join(provenance["git_status"]) or "(clean)") + "\n```",
            f"\nPython {provenance['python']}; "
            f"packages {json.dumps(provenance['packages'], sort_keys=True)}.",
            "\n[Recursive checksums](CHECKSUMS.json) hash retained files, child manifests, and STATUS; "
            "only this root manifest excludes itself.",
        ]
    )
    (output / "REPORT.md").write_text("\n".join(lines) + "\n")
