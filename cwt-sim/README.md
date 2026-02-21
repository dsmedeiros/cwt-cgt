# cwt-sim

This repository hosts placeholder scaffolding for continuous wavelet transport simulations.

## Rectangle path area modes

`cwt.orchestrator.param_path.ParameterPath` supports two area-allocation modes for
`kind: rectangle` loops through `corner_area_mode`:

- `false` (default): distribute the signed rectangle area uniformly over all steps.
  This improves per-step consistency for geometric-coupling updates.
- `true`: preserve legacy behavior by concentrating area contributions at corner
  transitions. This is useful for backward-compatible reproductions.

Both modes preserve the same total signed area over one closed loop.
