---
scope: "cwt_lab/shared"
governs: "Cross-process validators (Zod schemas), type contracts, shared constants"
inherits: "AGENTS.md"
adrs: [ADR-0002, ADR-0006]
invariants: [IPC-002, LAB-001]
enforced-by:
  - cwt_lab/shared/__tests__/validators.test.ts
  - .github/workflows/cwt-lab-tests.yml
persona: implementer
authority: [read, write, test]
restricted: [cross-cutting-changes]
---

# Shared Contracts

## Overview

Zod-validated type schemas and constants shared between Electron main process and React renderer. This module is the single source of truth for IPC message shapes, ensuring runtime type safety across the process boundary.

## Behavioral Directives

- **Must:** Define all IPC message types as Zod schemas in this module.
- **Must:** Keep schemas backward-compatible when adding fields (use `.optional()` for new fields).
- **Must not:** Import from `electron/` or `renderer/` — shared is dependency-free within cwt_lab.
- **Always:** Add test cases when creating or modifying schemas.
- **Never:** Use `z.any()` or `z.unknown()` for fields that have known shapes.

## Change Expectations

- Preserve backward compatibility of existing schemas.
- Preserve the test coverage for all exported validators.
- Preserve the import boundary — shared is consumed by both electron and renderer but depends on neither.

## Cross-Links

- **Parent directives:** `AGENTS.md`
- **Governing ADRs:** ADR-0002 (IPC bridge), ADR-0006 (desktop lab architecture)
- **Related components:** `cwt_lab/electron/agents.md` (consumes schemas for validation), `cwt_lab/renderer/agents.md` (consumes schemas for type safety)
- **Invariants:** See `.armature/invariants/registry.yaml` for entries: IPC-002, LAB-001
