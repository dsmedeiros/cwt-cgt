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
