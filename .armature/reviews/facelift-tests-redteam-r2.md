# Red Team Review: facelift-tests-redteam-r2

## Summary

Round 2 review of `tests/unit/test_cgt_phase16_to_39_smoke.py`. All three
Round 1 findings have been addressed. IMPORTABLE_PHASES now covers the full
16-39 range (24 modules, all confirmed on disk). The phase 39 structural test
now validates `switch_metrics` and its four R-squared sub-keys.  A new
parametrized `test_phase_artifact_has_expected_keys` test covers phases 25-39
for common schema keys. Total test count rose from 41 to 64. All 64 tests
pass.

## Critical Findings

None.

## Subtle Issues

1. **switch_metrics values are presence-checked but not type-checked**
   (line 152-162). The four R-squared keys are verified to exist in
   `switch_metrics`, but there is no assertion that their values are `float`
   (or at least numeric). A future bug that writes a string or `None` into
   one of these fields would pass the test.
   Severity: MEDIUM

2. **Schema consistency test covers phases 25-39 only, not 16-24**
   (line 169-171). The `_SCHEMA_PHASES` filter deliberately excludes
   phases 16-24 from the common-keys check. If those earlier artifacts drift
   away from the `{phase, benchmark, slug, verdict}` schema there is no
   regression net. This is acknowledged in the docstring, but the reasoning
   for the exclusion (do those artifacts genuinely lack `slug`?) is not
   documented in the test itself.
   Severity: MEDIUM

## Test Gaps

- No negative test verifying that a corrupted or truncated JSON artifact is
  correctly caught (the happy-path `json.load` test implicitly covers this,
  but an explicit negative test would be stronger).
- No test asserting that `PHASE_SUFFIX` and `IMPORTABLE_PHASES` stay in sync
  with the actual files on disk. If a new phase 40 module and artifact appear,
  the test file must be manually updated; there is no self-check.

## Semantic Drift Risks

- `IMPORTABLE_PHASES` on line 63 uses a slightly baroque construction
  (`list(range(16, 22)) + [22, 23, 24] + list(range(25, 40))`) instead of a
  single `list(range(16, 40))`. Both produce the same result (16-39 without
  duplicates), but the split form invites future editors to assume there is a
  meaningful gap between 21 and 22 when there is not.

## Verdict: PASS

All Round 1 findings are resolved. The remaining issues are MEDIUM severity
and do not block.

## Advisories:
- Add type assertions (`isinstance(v, (int, float))`) for the switch_metrics
  R-squared values.
- Consider extending the schema consistency test to phases 16-24, or document
  in-code why those phases are excluded.
- Simplify `IMPORTABLE_PHASES` to `list(range(16, 40))` to reduce confusion.
