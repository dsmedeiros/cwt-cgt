# CWT-CGT Post-Step-3 Next Steps

The foundation / benchmark block is now complete enough to support the next lane of work.

## Recommended immediate next steps

1. **Robustness expansion**
   - run held-out loop families (circles, off-center loops, multiple centers),
   - confirm the null/positive pattern survives those protocol changes.

2. **Modal upgrade preparation**
   - draft the Phase 5 modal extension note,
   - define the operator-mode objects and acceptance tests before coding them.

3. **Operator-backed acceptance tightening**
   - tie metric hotspots and signed-loop behavior more explicitly to the operator backbone quantities,
   - add held-out pass/fail gates rather than relying only on the default loop family.

4. **Mixed-state lane planning**
   - keep this separate from the coherent modal lane,
   - do not merge it into the baseline claim prematurely.

## Main rule going forward

New extensions should be added as separate layers with their own tests. They should not be allowed to reinterpret the already-completed passive benchmark block after the fact.
