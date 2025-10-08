import { describe, expect, it } from 'vitest';

import type { ArtifactFile } from '../../types/ipc';
import {
  findPhase1HeatmapGroups,
  formatPhase1GraphLabel,
  phase1HeatmapKinds,
} from '../artifacts';

describe('artifacts helpers', () => {
  it('groups heatmap files by graph name', () => {
    const artifacts: ArtifactFile[] = [
      { path: '/tmp/run/graphA', relativePath: 'graphA', updatedAt: 1, type: 'directory' },
      {
        path: '/tmp/run/graphA/heatmaps.png',
        relativePath: 'graphA/heatmaps.png',
        updatedAt: 2,
        type: 'file',
      },
      {
        path: '/tmp/run/graphA/omega_heatmap.png',
        relativePath: 'graphA/omega_heatmap.png',
        updatedAt: 3,
        type: 'file',
      },
      {
        path: '/tmp/run/group_b/heatmaps.png',
        relativePath: 'group_b/heatmaps.png',
        updatedAt: 4,
        type: 'file',
      },
    ];

    const groups = findPhase1HeatmapGroups(artifacts);
    expect(groups).toHaveLength(2);
    expect(groups[0].graph).toBe('graphA');
    expect(groups[0].files.heatmaps).toBe('graphA/heatmaps.png');
    expect(groups[0].files.omega_heatmap).toBe('graphA/omega_heatmap.png');
    expect(groups[1].graph).toBe('group_b');
    expect(groups[1].files.heatmaps).toBe('group_b/heatmaps.png');
  });

  it('provides sanitized graph labels', () => {
    expect(formatPhase1GraphLabel('graph_alpha')).toBe('graph alpha');
    expect(formatPhase1GraphLabel('  ')).toBe('Unnamed graph');
  });

  it('exposes the known heatmap kinds', () => {
    expect(Array.from(phase1HeatmapKinds)).toEqual(['heatmaps', 'omega_heatmap']);
  });
});
