import { describe, expect, it, vi } from 'vitest';
import { promises as fs } from 'node:fs';
import os from 'node:os';
import path from 'node:path';

import JSZip from 'jszip';

import { runBaselineAlignment } from '../baselines/alignment';
import type { BaselineAlignmentProgressEvent, BaselineRunPayload } from '../../renderer/types/ipc';

const pythonEnv = {
  executable: 'python',
  strategy: 'module' as const,
  version: '3.11.0',
};

const createArtifactsRoot = async () => {
  const root = await fs.mkdtemp(path.join(os.tmpdir(), 'alignment-bundle-'));
  const artifactsDir = path.join(root, 'artifacts');
  await fs.mkdir(artifactsDir, { recursive: true });
  return { root, artifactsDir } as const;
};

const removeDir = async (dir: string) => fs.rm(dir, { recursive: true, force: true });

describe('runBaselineAlignment', () => {
  it('launches deterministic baseline runs and packages the alignment bundle', async () => {
    const { root, artifactsDir } = await createArtifactsRoot();

    const runBaseline = vi.fn(async (payload: BaselineRunPayload, _options?: unknown) => {
      const model = payload.model;
      const invocationIndex = runBaseline.mock.calls.length;
      const runId = `${model}-run-${invocationIndex + 1}`;
      const modelRoot = path.join(artifactsDir, 'baselines', model);
      const folderName = `2024010${invocationIndex + 1}T010203__seed=${payload.seed ?? '0'}`;
      const runDir = path.join(modelRoot, folderName);
      await fs.mkdir(runDir, { recursive: true });
      await fs.writeFile(path.join(runDir, 'omega_abs_heatmap.png'), `heatmap-${model}`);
      await fs.writeFile(
        path.join(runDir, 'metrics.csv'),
        `model,seed\n${model},${payload.seed ?? ''}\n`,
        'utf-8',
      );
      return {
        runId,
        model,
        outputDir: runDir,
        artifactsDir: runDir,
        command: 'python',
        args: ['-m', `baselines.${model}.run`],
        cwd: '/tmp',
        cli: `python -m baselines.${model}.run`,
        status: 'complete' as const,
        startedAt: 1,
        completedAt: 2,
        loopMetrics: null,
      };
    });

    const events: BaselineAlignmentProgressEvent[] = [];

    try {
      const result = await runBaselineAlignment({
        env: pythonEnv,
        artifactsRoot: artifactsDir,
        onProgress: (event) => events.push(event),
        runBaseline,
        timestampFn: () => Date.UTC(2024, 0, 2, 3, 4, 5),
        zipFactory: () => new JSZip(),
      });

      expect(runBaseline).toHaveBeenCalledTimes(4);
      expect(result.exportId).toBe('baselines_alignment_20240102T030405Z');
      expect(result.zipPath).toBe(path.join(artifactsDir, '_exports', `${result.exportId}.zip`));
      expect(result.runs.map((run) => run.seed)).toEqual([1101, 2202, 3303, 4404]);

      expect(events[0]).toMatchObject({ kind: 'start', totalRuns: 4 });
      expect(events.some((event) => event.kind === 'packing')).toBe(true);
      expect(events.filter((event) => event.kind === 'run-start')).toHaveLength(4);
      expect(events.filter((event) => event.kind === 'run-complete')).toHaveLength(4);
      const completionEvent = [...events].reverse().find((event) => event.kind === 'complete');
      expect(completionEvent).toMatchObject({ kind: 'complete', zipPath: result.zipPath });

      const zipBuffer = await fs.readFile(result.zipPath);
      const zip = await JSZip.loadAsync(zipBuffer);
      const entries = Object.keys(zip.files);
      expect(entries).toContain(`${result.exportId}/README.md`);
      for (const summary of result.runs) {
        const heatmapEntry = `${result.exportId}/${summary.relativePath}/omega_abs_heatmap.png`;
        const metricsEntry = `${result.exportId}/${summary.relativePath}/metrics.csv`;
        expect(entries).toContain(heatmapEntry);
        expect(entries).toContain(metricsEntry);
        const metricsContents = await zip.file(metricsEntry)?.async('string');
        expect(metricsContents).toContain(summary.model);
      }
      const readme = await zip.file(`${result.exportId}/README.md`)?.async('string');
      expect(readme).toBeDefined();
      expect(readme).toContain('four deterministic baseline sweeps');
      expect(readme).toContain('15×15');
    } finally {
      await removeDir(root);
    }
  });
});
