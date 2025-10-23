import { describe, expect, it } from 'vitest';

import { canonicalGraphId, GRAPH_ID_ALIASES } from '../graphs';

type AliasCase = [canonical: string, candidate: string];

const aliasCases: AliasCase[] = (() => {
  const cases: AliasCase[] = [];
  const seen = new Set<string>();

  const register = (canonical: string, candidate: string) => {
    const key = `${canonical}|${candidate}`;
    if (!seen.has(key)) {
      seen.add(key);
      cases.push([canonical, candidate]);
    }
  };

  for (const [canonical, aliases] of Object.entries(GRAPH_ID_ALIASES)) {
    for (const candidate of [canonical, ...aliases]) {
      register(canonical, candidate);
      register(canonical, candidate.toUpperCase());
      register(canonical, `phase1:${candidate}`);
    }
  }

  return cases;
})();

describe('canonicalGraphId', () => {
  it.each(aliasCases)('normalizes %s when provided %s', (expected, candidate) => {
    expect(canonicalGraphId(candidate)).toBe(expected);
    expect(canonicalGraphId({ id: candidate })).toBe(expected);
    expect(canonicalGraphId({ graph: candidate })).toBe(expected);
    expect(canonicalGraphId({ label: candidate })).toBe(expected);
    expect(canonicalGraphId({ name: candidate })).toBe(expected);
  });

  it('returns null for unknown identifiers', () => {
    expect(canonicalGraphId('')).toBeNull();
    expect(canonicalGraphId('unknown graph kind')).toBeNull();
    expect(canonicalGraphId({ id: 'phase1:unknown' })).toBeNull();
  });
});
