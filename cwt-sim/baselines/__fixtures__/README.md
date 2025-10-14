# Baseline Test Fixtures

This directory hosts compact CSV grids used by the automated test suite and the
renderer mocks:

| File | Description |
| --- | --- |
| `tiny_grid_ising.csv` | 5×5 sweep of Ising (T, h) tiles highlighting the critical ridge near zero field. |
| `tiny_grid_kuramoto.csv` | 5×5 Kuramoto grid showcasing the coupling/disorder balance where synchronization emerges. |
| `tiny_grid_percolation.csv` | 5×5 bond-percolation scan around the square-lattice threshold. |
| `tiny_grid_sis.csv` | Synthetic SIS plane tracing the R₀ ≈ 1 alignment used for front-end previews. |

All fixtures keep column names consistent with the corresponding CLI metrics so
tests can exercise parsing logic without launching full simulations.
