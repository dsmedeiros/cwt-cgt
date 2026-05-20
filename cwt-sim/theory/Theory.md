# Theory Pointers

The full derivations and conceptual background live in the top-level [theory.md](../../theory.md) document. This note just acts as a waypoint and maps the major sections to the implementation modules inside `cwt-sim`.

## Section → Implementation map

- **§2.1 Graph substrate** → `cwt.graph.substrate`, `cwt.graph.factories`
- **§2.2 Layer fields** → `cwt.layers.state`, `cwt.layers.q_update`, `cwt.layers.theta_update`
- **§2.3 Complex state / Ψ build** → `cwt.geometry.psi`
- **§4 CGT estimators** → `cwt.geometry.metric`, `cwt.geometry.curvature`, `cwt.geometry.adapt_mesh`
- **§5 Dynamics & geometric corrections** → `cwt.orchestrator.scheduler`, `cwt.orchestrator.with_geom`
- **§6 Parameter paths & control** → `cwt.orchestrator.param_path`, `cwt.geometry.adapt_mesh`
- **§7 Observables / readouts** → `cwt.layers.readouts`, `cwt.metrics.eval_curves`

Refer back to the main theory document for equations, derivations, and the motivations behind each component.

## Current empirical status

- CWT-CGT separates a passive diagnostic layer (`g`, `Omega`) from an active geometric-control layer that applies connection/curvature-derived loop terms.
- The active phase-kick branch is the validated external path today: OEDI and Chicago real-data-derived substrates support the `R_kuramoto` loop law with orientation reversal.
- Passive `tr(g)` transition-ridge claims are regime-dependent Gate B claims, not universal claims. They are confirmed on OEDI and null on overlap-safe Chicago.
- QP-1 calibration fixes magnitude and orientation reversal while requiring an explicit sign map: `Omega_analytic = -Omega_impl`.
- Noise robustness uses the OEDI phase-noise result: sign flips appear around `s_bar ~= 0.88`; high-noise runs are non-adiabatic and excluded from the leading-order active-loop claim.
- Direct `Omega`-bias coupling remains unvalidated pending high-coupling tests; current scramble evidence validates the phase-kick/connection branch.
