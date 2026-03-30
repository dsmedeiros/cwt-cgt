---
scope: "cwt-sim/baselines"
governs: "Canonical model runners (Ising, Kuramoto, percolation, SIS) for validation against known physics"
inherits: "AGENTS.md"
adrs: [ADR-0001, ADR-0004]
invariants: [BASE-001, BASE-002, BASE-003]
enforced-by:
  - cwt-sim/baselines/__tests__/test_sis_run.py
  - cwt-sim/baselines/__tests__/test_ising_run.py
  - cwt-sim/baselines/__tests__/test_kuramoto_run.py
  - cwt-sim/baselines/__tests__/test_percolation_run.py
  - .github/workflows/tests.yml
persona: implementer
authority: [read, write, test]
restricted: [cross-cutting-changes, modify-fixtures]
---

# Baseline Model Runners

## Overview

Independent reference implementations of canonical physics models (Ising, Kuramoto, percolation, SIS) used to validate CWT simulation outputs. Each model has a runner in its own sub-package with fixture data in `__fixtures__/` for regression anchoring.

## Behavioral Directives

- **Must:** Expose a `run()` function with consistent return schema (BASE-001).
- **Must not:** Import from `cwt/` modules — baselines are independent reference models (BASE-003).
- **Never:** Modify existing fixture CSV files without explicit ADR amendment (BASE-002).
- **Always:** Add fixture data for new baseline models.
- **Always:** Test against fixture baselines for regression detection.

## Change Expectations

- Preserve the `run()` function interface for all existing runners.
- Preserve fixture CSV data integrity.
- Preserve independence from the CWT core engine.

## Cross-Links

- **Parent directives:** `AGENTS.md`
- **Governing ADRs:** ADR-0001 (three-layer model context), ADR-0004 (baseline runners)
- **Related components:** `cwt-sim/cwt/agents.md` (outputs compared against baselines)
- **Invariants:** See `.armature/invariants/registry.yaml` for entries: BASE-001, BASE-002, BASE-003
