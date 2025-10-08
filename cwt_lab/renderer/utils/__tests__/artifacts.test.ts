import { describe, expect, it } from 'vitest';

import type { ArtifactFile } from '../../types/ipc';
import {
  findPhase1HeatmapGroups,
  formatPhase1GraphLabel,
  formatPhase1SubstrateLabel,
  phase1HeatmapKinds,
} from '../artifacts';

describe('artifacts helpers', () => {
  it('groups heatmap files by substrate and graph name', () => {
    const artifacts: ArtifactFile[] = [
      {
        path: '/tmp/run/substrates/ring3/heatmaps.png',
        relativePath: 'substrates\\ring3\\heatmaps.png',
        updatedAt: 2,
        type: 'file',
      },
      {
        path: '/tmp/run/substrates/ring3/omega_heatmap.png',
        relativePath: 'substrates/ring3/omega_heatmap.png',
        updatedAt: 3,
        type: 'file',
      },
      {
        path: '/tmp/run/substrates/small_world/heatmaps.png',
        relativePath: 'substrates/small_world/heatmaps.png',
        updatedAt: 4,
        type: 'file',
      },
    ];

    const groups = findPhase1HeatmapGroups(artifacts);
    expect(groups).toHaveLength(2);
    expect(groups[0]).toEqual({
      substrate: 'ring3',
      graph: 'ring3',
      files: {
        heatmaps: 'substrates/ring3/heatmaps.png',
        omega_heatmap: 'substrates/ring3/omega_heatmap.png',
      },
    });
    expect(groups[1]).toEqual({
      substrate: 'small_world',
      graph: 'small_world',
      files: {
        heatmaps: 'substrates/small_world/heatmaps.png',
      },
    });
  });

  it('extracts substrates nested beneath experiment directories', () => {
    const artifacts: ArtifactFile[] = [
      {
        path: '/tmp/run/experiment/substrates/torus/heatmaps.png',
        relativePath: 'experiment/substrates/torus/heatmaps.png',
        updatedAt: 1,
        type: 'file',
      },
    ];

    const groups = findPhase1HeatmapGroups(artifacts);
    expect(groups).toHaveLength(1);
    expect(groups[0].substrate).toBe('torus');
    expect(groups[0].graph).toBe('torus');
    expect(groups[0].files.heatmaps).toBe('experiment/substrates/torus/heatmaps.png');
  });

  it('provides sanitized graph labels', () => {
    expect(formatPhase1GraphLabel('graph_alpha')).toBe('graph alpha');
    expect(formatPhase1GraphLabel('  ')).toBe('Unnamed graph');
  });

  it('provides sanitized substrate labels', () => {
    expect(formatPhase1SubstrateLabel('substrate_alpha')).toBe('substrate alpha');
    expect(formatPhase1SubstrateLabel('')).toBe('Unnamed substrate');
  });

  it('exposes the known heatmap kinds', () => {
    expect(Array.from(phase1HeatmapKinds)).toEqual(['heatmaps', 'omega_heatmap']);
  });
});
