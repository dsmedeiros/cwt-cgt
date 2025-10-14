import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest';
import { promises as fs } from 'node:fs';
import os from 'node:os';
import path from 'node:path';

import type { RunManager } from '../runner/runManager';
import { runAdiabaticBoundary } from '../adiabaticBoundary';

vi.mock('uuid', () => ({ v4: () => 'test-run-id' }));

const writeArtifacts = async (outputDir: string) => {
  const surfacePath = path.join(outputDir, 'kappa_surface.csv');
  const histogramPath = path.join(outputDir, 'fs_histograms.json');
  const boundaryPath = path.join(outputDir, 'boundary.csv');

  await fs.mkdir(outputDir, { recursive: true });
  await fs.writeFile(
    surfacePath,
    [
      'extent,steps,flux,area,kappa1,readout,fs_mean,fs_p95',
      '0.02,120,1.0,2.0,0.5,0.1,0.05,0.03',
    ].join('\n'),
    'utf-8',
  );
  await fs.writeFile(
    histogramPath,
    JSON.stringify({ 'extent=0.02|steps=120': [1, 0, 2] }),
    'utf-8',
  );
  await fs.writeFile(
    boundaryPath,
    [
      'extent,boundary_steps,reference_kappa,boundary_kappa,fs_p95',
      '0.02,120,0.5,0.4,0.03',
    ].join('\n'),
    'utf-8',
  );
};

describe('runAdiabaticBoundary', () => {
  let artifactsRoot: string;
  let runArgs: string[];
  let capturedOutputDir: string | null;

  beforeEach(async () => {
    artifactsRoot = await fs.mkdtemp(path.join(os.tmpdir(), 'adiabatic-boundary-'));
    runArgs = [];
    capturedOutputDir = null;
  });

  afterEach(async () => {
    await fs.rm(artifactsRoot, { recursive: true, force: true });
  });

  it('filters metadata parameters before building CLI arguments', async () => {
    const runManager = {
      createRun: vi.fn(async (_command: string, args: string[]) => {
        runArgs = args;
        const outputDirFlag = args.indexOf('--output-dir');
        if (outputDirFlag >= 0 && outputDirFlag + 1 < args.length) {
          capturedOutputDir = args[outputDirFlag + 1];
        }
        return { runId: 'mock-run' };
      }),
      waitForCompletion: vi.fn(async () => {
        if (!capturedOutputDir) {
          throw new Error('output dir not captured');
        }
        await writeArtifacts(capturedOutputDir);
        return {
          runId: 'mock-run',
          status: 'complete',
          exitCode: 0,
          signal: null,
          error: null,
        };
      }),
    } satisfies Pick<RunManager, 'createRun' | 'waitForCompletion'>;

    const result = await runAdiabaticBoundary(
      runManager as RunManager,
      '/tmp/cwt-sim',
      artifactsRoot,
      {
        center: 'tau=0.8,zeta=0.0',
        extents: [0.02, 0.04],
        steps: [120],
        gridSize: 6,
        hotspotId: 'hotspot-1',
        graphId: 'graph-1',
      },
    );

    expect(runManager.createRun).toHaveBeenCalledWith(
      'experiments.adiabatic_boundary.run',
      expect.any(Array),
      '/tmp/cwt-sim',
      expect.any(Object),
      expect.any(Object),
    );
    expect(runArgs).not.toContain('--hotspot-id');
    expect(runArgs).not.toContain('--graph-id');
    expect(runArgs).toContain('--center');
    expect(runArgs).toContain('--extents');
    expect(runArgs).toContain('--steps');
    expect(result.runId).toBe('mock-run');
    expect(result.surface).toHaveLength(1);
    expect(result.boundary).toHaveLength(1);
  });
});
