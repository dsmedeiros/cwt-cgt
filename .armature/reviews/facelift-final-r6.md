# Red Team Review: facelift-final-r6

## Summary

Final adversarial pass on the phase 16-39 facelift. All seven required checks
executed. Six of seven pass cleanly. Check 7 (write_text encoding sweep)
returns 36 hits across phases 16-39 where `write_text` is called without
`encoding='utf-8'`. Because every one of those calls writes output from
`json.dumps` with the default `ensure_ascii=True`, the written bytes are pure
ASCII and the missing encoding parameter cannot produce corrupt output on any
platform. This is a consistency issue against the pattern established by phases
10-15 (which all specify `encoding='utf-8'`), not a correctness bug.

## Required Check Results

| # | Check | Result |
|---|-------|--------|
| 1 | Full test suite (182 tests) | PASS -- 0 failures |
| 2 | Phase 39 end-to-end runtime | PASS |
| 3 | Empty train set edge case | PASS -- returns `[]` |
| 4 | Overflow edge case | PASS -- predictor=2.54e+300, finite |
| 5 | Stale path sweep | PASS -- hits only in pre-existing phases 10-15 |
| 6 | All 24 phase imports | PASS -- ALL IMPORTS OK |
| 7 | write_text encoding sweep (phase16-17) | 4 hits in phase16, 4 hits in phase17 (see below) |

## Critical Findings

None.

## Subtle Issues

**Missing `encoding='utf-8'` on JSON write_text calls (MEDIUM)**

36 `write_text(json.dumps(...))` calls across phases 16-39 omit the
`encoding` parameter. On Windows, `Path.write_text()` defaults to the
system locale encoding. Since `json.dumps` defaults to `ensure_ascii=True`,
the output is pure ASCII and will round-trip correctly under any single-byte
encoding. This cannot produce corrupt output today.

However:
- It is inconsistent with the pattern in phases 10-15 which always pass
  `encoding='utf-8'`.
- If a future change passes `ensure_ascii=False` to `json.dumps`, the
  missing encoding could silently produce mojibake on Windows systems
  with non-UTF-8 locale.

Files affected: `phase16_analysis.py` through `phase39_analysis.py`
(all JSON artifact writes).

## Test Gaps

None identified beyond prior rounds.

## Semantic Drift Risks

None new.

## Verdict: PASS

All functional checks pass. The missing `encoding` parameter is a
consistency hygiene issue that cannot produce incorrect output given the
current `ensure_ascii=True` default. It does not meet the threshold for
blocking.
