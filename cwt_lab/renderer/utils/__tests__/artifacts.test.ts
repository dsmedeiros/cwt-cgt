import { describe, expect, it } from 'vitest';

import type { ArtifactFile } from '../../types/ipc';
import {
  findPhase1HeatmapGroups,
  formatPhase1GraphLabel,
  formatPhase1SubstrateLabel,
  extractPhase1TopologyFromMetrics,
  phase1HeatmapKinds,
  sanitizePhase1TopologySummary,
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
        heatmaps: {
          relativePath: 'substrates\\ring3\\heatmaps.png',
          normalizedPath: 'substrates/ring3/heatmaps.png',
        },
        omega_heatmap: {
          relativePath: 'substrates/ring3/omega_heatmap.png',
          normalizedPath: 'substrates/ring3/omega_heatmap.png',
        },
      },
    });
    expect(groups[1]).toEqual({
      substrate: 'small_world',
      graph: 'small_world',
      files: {
        heatmaps: {
          relativePath: 'substrates/small_world/heatmaps.png',
          normalizedPath: 'substrates/small_world/heatmaps.png',
        },
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
    expect(groups[0].files.heatmaps).toEqual({
      relativePath: 'experiment/substrates/torus/heatmaps.png',
      normalizedPath: 'experiment/substrates/torus/heatmaps.png',
    });
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

  it('extracts topology descriptors from flattened metrics', () => {
    const summaries = extractPhase1TopologyFromMetrics({
      'graphs.ring.topology_clustering': 0.42,
      'graphs.ring.topology_path_length': 2.5,
      'ring.topology_assortativity': -0.11,
      'graphs.square.topology_degree_variance': 1.2,
      'graphs.square.topology_clustering': null,
      unrelated: 9.9,
    });

    expect(Object.keys(summaries)).toEqual(['ring', 'square']);
    expect(summaries.ring).toEqual({
      clustering: 0.42,
      pathLength: 2.5,
      degreeVariance: null,
      assortativity: -0.11,
    });
    expect(summaries.square).toEqual({
      clustering: null,
      pathLength: null,
      degreeVariance: 1.2,
      assortativity: null,
    });
  });

  it('sanitizes topology summaries loaded from artifacts', () => {
    expect(
      sanitizePhase1TopologySummary({
        clustering: '0.314',
        path_length: 1.8,
        degree_variance: 'not-a-number',
        assortativity: Infinity,
      }),
    ).toEqual({
      clustering: 0.314,
      pathLength: 1.8,
      degreeVariance: null,
      assortativity: null,
    });

    expect(sanitizePhase1TopologySummary({})).toBeNull();
    expect(sanitizePhase1TopologySummary(null)).toBeNull();
  });
});
