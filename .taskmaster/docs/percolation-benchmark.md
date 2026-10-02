# Percolation validation benchmark

User authorization: Following the article review, the user said "Okay, proceed" to baseline label/threshold corrections and a finite-size benchmark (2D calibration, 3D extension, frozen state encoding, real-state control).

Deliverables:
1. Correct square-lattice pure-bond p_c to 0.5; distinguish mixed site damage and heuristic thresholds. Preserve artifact/CLI compatibility and existing fixtures.
2. Describe S_mean as largest-component fraction and giant_fraction as a threshold-exceedance frequency. Label observable derivatives as proxies; do not call mixed scalar derivatives Wilson holonomy.
3. Add an isolated reproducible experiment for P(origin reaches distance L), Bernoulli bond sampling in d=2,3, radius/seed/probability sweeps, uncertainty, finite-size summaries, and co-located REPORT.md and provenance. Freeze protocol before main run. Do not infer theorem, exponents, or CGT validity from finite scans.
4. Use existing CGT estimators from experiments only, with a declared probability/state map; real square-root state control must permit a nonzero metric and zero Berry curvature. Keep independent measurement and geometry sampling streams. Report endpoint/support exclusions and sampling noise; no post-hoc ridge fitting.
5. Document source theorem, scope, reproducible commands, and primary-source review status. Review finite independent-edge additive gluing as a small exact analytical control if feasible within the scoped experiment.
6. Run meaningful deterministic correctness tests, affected regression suites, formatting/lint/type checks, standard compliance review and red-team review.

No remote write, push, merge, or publication requested. Follow Armature scoped implementation and review. Local acceptance commits permitted by repository workflow after review.
