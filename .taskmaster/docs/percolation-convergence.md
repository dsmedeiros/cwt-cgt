# Percolation numerical convergence study

Authorization: user said Proceed to the recommendation of a PR followed by a frozen convergence study. Existing reviewed reference remains unchanged. No merge or new physical complex-state assumptions.

Milestones: publish existing draft PR; freeze protocol; implement paired aggregation; implement serial study CLI/report; independently review; execute/review fixed study; archive and publish results.

Protocol: geometry N=512,2048; h=.02,.01; radii2,4,6,8; original 2D/3D probability grids; five independent geometry batches; held-out master seed20261002; fixed measurement2048 trials in every child. State/chart/support/overlap rules unchanged; no smoothing. N shares uniform prefixes and h shares uniforms within batches. Repeated measurement data across four children are duplicates: verify equal and report once, never pool.

Primary comparisons: N512 vs2048 at h=.01; h=.02 vs.01 at N2048. Full symmetric tensor change2||B-A||F/(||A||F+||B||F); zero denominator indeterminate. Require all five jointly accepted pairs in both comparisons and five accepted fine batches. Limited variation at tested resolutions only if both medians<=.25 and maxima<=.50. Otherwise variation exceeds tolerance; missing/undefined pairs indeterminate. These tolerances and batch ranges are descriptive, not confidence intervals or proof of asymptotic convergence.

Report every case/exclusion. Different radii are different finite observables, not metric discretization convergence tests. No fitted exponents/ridges, theorem proof, Berry-curvature emergence, or CWT validation. Keep original reference separate. Serial execution bounds largest uniform array at227MB plus validation temporaries. Never silently reduce grid after failures.

Scope: cwt-sim/experiments/percolation_finite_size and owned tests; GATE-001/002/003, ADR-0001/0003/0005. No core/sampler/existing-runner API changes. Artifacts isolated; protocol/hash before children, immutable names, retain partial failures. Stage0 and meaningful paired-aggregation/CLI/artifact tests plus standard/red-team review required.

Checkpoints:1 strict aggregator+tests (planned165LOC, actual482LOC including strict count-integrity regressions);2a serial Typer CLI/protocol/status/minimal report+tests (<=300LOC);2b full report/chart/provenance/checksums+tests (<=300LOC). Recalibrated after strict schema tests grew; actual variance diagnostic. Preserve readable code and coverage and independent review at each checkpoint.
