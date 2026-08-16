# Active-loop substrate screen (metadata only)

Date: 2026-08-15
Disposition: **no reviewed public source clears G0-G12**
Template state: **`BLOCKED_NO_SUBSTRATE`**

> This is a broad, non-exhaustive metadata-level screen. Small official
> structural payloads were inspected during candidate screening, but no
> candidate outcome analysis was conducted, no candidate data were retained,
> and this package has no raw-data or outcome path. A near-miss is not a
> qualified substrate, study preregistration, empirical result, or evidence for
> or against CWT/CGT.

## Reviewed public candidates

| Candidate and primary record | Metadata-level strengths | Blocking gaps |
|---|---|---|
| [RoboLoc-G version record](https://zenodo.org/records/15857197); [latest immutable record DOI](https://doi.org/10.5281/zenodo.15989282) | Strongest adapter scaffold reviewed: three-axis gantry, G-code command, achieved `xyz`, independent sensors, and CC BY 4.0 metadata (26 files; 2.103 GB). | Only one documented clockwise `xy` circle at fixed `z`; no paired counterclockwise traversal, resets, full-rank noncoplanar normals, or adequate independent cluster count. |
| [Even et al., coupled pendulums, v1.0.0](https://doi.org/10.5281/zenodo.15299253) | Strongest retrospective near-miss: CC BY 4.0; 16 raw timestamped CSV files; 12 principal runs include clockwise/counterclockwise conditions, Hall sensing, and drive voltage. | Two-dimensional control, one run per cell, achieved parameters reconstructed rather than directly logged, no independent state/response sensor separation, no separate exact zero-coupling condition, and retrospective outcome-aware reuse. |
| [Focused-ultrasound haptic circle](https://zenodo.org/records/7686561) | Randomized orientation and CC BY 4.0 metadata. | Circle pilot has one participant and a behavioral table, with no achieved-path telemetry or full-rank three-control design. |
| [Hubbard-Thouless pump](https://www.nature.com/articles/s41567-023-02145-w) | Closest screened parameter-cycle physics. | Public figure data from one apparatus and one two-dimensional parameter plane; no raw command/achievement pair or independent reset/block ledger meeting the template. |
| [Cichlid optomotor data](https://doi.org/10.5061/dryad.3j9kd51x3) | Randomized clockwise/counterclockwise stimulus assignment. | One-parameter stimulus and endpoint outcomes; no raw waveform/timing closure or full-rank tensor design. |
| [Capillary-ratchet data](https://doi.org/10.5061/dryad.sf7m0cgnq) | Physical repeated measurements. | Clockwise/counterclockwise denotes device chirality, while the drive is a scalar up/down retrace; only two devices, so the independent-unit requirement also fails. |

RoboLoc-G is the closest engineering scaffold in this limited screen, not a
qualified study source. The screen does not authorize an adapter, raw-data
access, or outcome implementation.

## Prospective collection outline (preliminary)

A purpose-built candidate could use coupled magnetic rotors driven by three-axis
coils, Hall-probe measurement of achieved controls, and a separate calibrated
torque response. The loop family would include `xy`, `yz`, and `zx` planes plus
an oblique held-out normal, with complete on/zero by positive/negative quartets
inside independently randomized, washed-out reset blocks.

A preliminary planning estimate is 12 calibration reset blocks and 40-48
confirmation reset blocks. This is not a frozen sample size or power result. It
is subject to a calibration-only power analysis for every conjunctive gate,
including the 0.90 power requirement, SESOI, equivalence/tensor/loss margins,
remainder validation, attrition, and the requirement of at least 20 genuinely
independent blocks. Until those values and a real apparatus/source manifest are
reviewed, the only valid state remains `BLOCKED_NO_SUBSTRATE`.
