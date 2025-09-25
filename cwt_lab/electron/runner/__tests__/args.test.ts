import { describe, expect, it } from 'vitest';

import { buildArgsFromParams } from '../args';

describe('buildArgsFromParams', () => {
  it('returns an empty list when params are undefined', () => {
    expect(buildArgsFromParams(undefined)).toEqual([]);
  });

  it('converts camelCase and snake_case keys to kebab-case flags', () => {
    const args = buildArgsFromParams({ phaseCount: 4, fs_guard: 0.25 });
    expect(args).toEqual(['--phase-count', '4', '--fs-guard', '0.25']);
  });

  it('serialises array and object values', () => {
    const args = buildArgsFromParams({ axes: ['rho', 'tau'], metadata: { seed: 42 } });
    expect(args).toEqual(['--axes', 'rho', 'tau', '--metadata', JSON.stringify({ seed: 42 })]);
  });

  it('omits nullish values and handles negated boolean switches', () => {
    const args = buildArgsFromParams({ enableHotStart: true, disableCooling: false, noAutosave: true, skip: null });
    expect(args).toEqual(['--enable-hot-start', 'true', '--disable-cooling', 'false', '--no-autosave']);
  });
});
