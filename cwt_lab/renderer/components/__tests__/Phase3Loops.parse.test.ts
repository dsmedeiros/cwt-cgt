import { describe, expect, it, vi } from 'vitest';

vi.mock('../AdiabaticBoundaryViewer', () => ({
  __esModule: true,
  default: vi.fn(() => null),
}));

import { parsePhase1Hotspots } from '../Phase3Loops';

describe('parsePhase1Hotspots', () => {
  it('extracts graph metadata from top omega tiles payload', () => {
    const payload = {
      axes: ['rho', 'tau'],
      top_tiles: [
        {
          coordinates: {
            rho: 0.92,
            tau: 1.08,
            kappa: 1.0,
          },
          omega_abs: 2.41,
        },
      ],
      graph: {
        identifier: 'random_regular',
        kwargs: { degree: 4 },
        seed: 99,
      },
    };

    const entries = parsePhase1Hotspots(JSON.stringify(payload));
    expect(entries).toHaveLength(1);
    const [entry] = entries;
    expect(entry.graph).toEqual({ identifier: 'random_regular', kwargs: { degree: 4 } });
    expect(entry.graphSeed).toBe(99);
  });

  it('preserves string graph descriptors and falls back when metadata is missing', () => {
    const payload = {
      axes: ['rho', 'tau'],
      top_tiles: [
        {
          coordinates: {
            rho: 0.91,
            tau: 1.07,
            kappa: 1.0,
          },
          omega_abs: 2.11,
        },
      ],
      graph: 'ring3',
    };

    const entries = parsePhase1Hotspots(JSON.stringify(payload));
    expect(entries).toHaveLength(1);
    expect(entries[0].graph).toBe('ring3');
    expect(entries[0].graphSeed).toBeNull();
  });
});
