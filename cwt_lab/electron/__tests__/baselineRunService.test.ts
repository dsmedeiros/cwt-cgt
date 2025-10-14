import { describe, expect, it, vi } from 'vitest';
import { EventEmitter } from 'node:events';
import { promises as fs } from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { PassThrough } from 'node:stream';
import type { ChildProcessWithoutNullStreams } from 'node:child_process';

import { baselineRunPayloadSchema, executeBaselineRun } from '../baselines/runService';
import { RunManager } from '../runner/runManager';

const pythonEnv = {
  executable: 'python',
  strategy: 'module' as const,
  version: '3.11.0',
};

const createArtifactsRoot = async () =>
  fs.mkdtemp(path.join(os.tmpdir(), 'baseline-artifacts-'));

const removeDir = async (dir: string) => fs.rm(dir, { recursive: true, force: true });

const createChildProcess = (
  onReady: (child: EventEmitter & { stdout: PassThrough; stderr: PassThrough }) => void,
): ChildProcessWithoutNullStreams => {
  const stdout = new PassThrough();
  const stderr = new PassThrough();
  const child = Object.assign(new EventEmitter(), { stdout, stderr });
  onReady(child);
  return child as unknown as ChildProcessWithoutNullStreams;
};

describe('executeBaselineRun', () => {
  it('validates payload structure and sanitises optional fields', () => {
    const parsed = baselineRunPayloadSchema.parse({
      model: 'ising',
      axisMap: '   ',
      outputDir: null,
      steps: '120',
      args: ['--flag'],
      env: { CWT_LOOP_FS_GUARD: 0.75, EMPTY: '  ', nullish: null },
    });
    expect(parsed.axisMap).toBeNull();
    expect(parsed.args).toEqual(['--flag']);
    expect(parsed.env).toEqual({ CWT_LOOP_FS_GUARD: '0.75', EMPTY: '  ' });

    expect(() => baselineRunPayloadSchema.parse({ model: 'unknown' } as unknown)).toThrow();
    expect(() => baselineRunPayloadSchema.parse({ model: 'ising', args: [null] } as unknown)).toThrow();
  });

  it('propagates process failures with non-zero exit codes', async () => {
    const artifactsRoot = await createArtifactsRoot();
    const spawnMock = vi.fn(() =>
      createChildProcess((child) => {
        setImmediate(() => {
          child.stderr.emit('data', Buffer.from('boom', 'utf-8'));
          child.emit('close', 2, null);
        });
      }),
    );

    const readDirs = vi.fn(async () => new Set<string>());
    const exits: Array<{ runId: string; code: number | null; signal: NodeJS.Signals | null }> = [];
    const errors: Array<{ runId: string; message: string }> = [];

    const payload = baselineRunPayloadSchema.parse({ model: 'ising' });

    try {
      await expect(
        executeBaselineRun(payload, {
          env: pythonEnv,
          artifactsRoot,
          spawnFn: spawnMock as unknown as typeof import('node:child_process').spawn,
          readRunDirs: readDirs,
          onExit: (event) => exits.push(event),
          onError: (event) => errors.push({ runId: event.runId, message: event.error.message }),
        }),
      ).rejects.toMatchObject({ message: 'Baseline run exited with code 2' });
    } finally {
      await removeDir(artifactsRoot);
    }

    expect(spawnMock).toHaveBeenCalledTimes(1);
    expect(readDirs).toHaveBeenCalledTimes(1);
    expect(exits).toHaveLength(1);
    expect(exits[0].code).toBe(2);
    expect(errors).toEqual([{ runId: exits[0].runId, message: 'Baseline run exited with code 2' }]);
  });

  it('scopes baseline artifacts to the run identifier when no output directory is provided', async () => {
    const runFolder = '20240101T120000__graph=grid__seed=1';
    const uuidFn = vi.fn(() => 'run-1234');
    const artifactsRoot = await createArtifactsRoot();
    const spawnMock = vi.fn(() =>
      createChildProcess((child) => {
        setImmediate(() => {
          child.stdout.emit('data', Buffer.from('ok', 'utf-8'));
          child.emit('close', 0, null);
        });
      }),
    );

    const readDirs = vi
      .fn(async () => new Set<string>())
      .mockResolvedValueOnce(new Set())
      .mockResolvedValueOnce(new Set([runFolder]));

    const payload = baselineRunPayloadSchema.parse({ model: 'ising' });

    try {
      const result = await executeBaselineRun(payload, {
        env: pythonEnv,
        artifactsRoot,
        spawnFn: spawnMock as unknown as typeof import('node:child_process').spawn,
        uuidFn,
        readRunDirs: readDirs,
      });

      expect(uuidFn).toHaveBeenCalledTimes(1);
      expect(result.runId).toBe('run-1234');
      expect(result.status).toBe('complete');
      expect(result.loopMetrics).toBeNull();

      const modelRoot = path.join(artifactsRoot, '_baseline_runs', 'run-1234', 'baselines', 'ising');
      expect(readDirs).toHaveBeenNthCalledWith(1, modelRoot);
      expect(readDirs).toHaveBeenNthCalledWith(2, modelRoot);
      expect(result.outputDir).toBe(path.join(modelRoot, runFolder));
      expect(result.artifactsDir).toBe(result.outputDir);

      const logPath = path.join(result.artifactsDir, '_runs', result.runId, 'stdout.log');
      const logContents = await fs.readFile(logPath, 'utf-8');
      expect(logContents).toContain('ok');
    } finally {
      await removeDir(artifactsRoot);
    }
  });

  it('merges custom environment variables into the spawned process', async () => {
    const artifactsRoot = await createArtifactsRoot();
    const spawnMock = vi.fn(() =>
      createChildProcess((child) => {
        setImmediate(() => {
          child.stdout.emit('data', Buffer.from('ok', 'utf-8'));
          child.emit('close', 0, null);
        });
      }),
    );

    const payload = baselineRunPayloadSchema.parse({
      model: 'ising',
      env: { CWT_LOOP_FS_GUARD: '0.9', EXTRA_FLAG: 'enabled' },
    });

    try {
      await executeBaselineRun(payload, {
        env: pythonEnv,
        artifactsRoot,
        spawnFn: spawnMock as unknown as typeof import('node:child_process').spawn,
      });
    } finally {
      await removeDir(artifactsRoot);
    }

    expect(spawnMock).toHaveBeenCalledTimes(1);
    const call = spawnMock.mock.calls[0];
    const options = call?.[2] as { env?: NodeJS.ProcessEnv } | undefined;
    expect(options?.env?.CWT_LOOP_FS_GUARD).toBe('0.9');
    expect(options?.env?.EXTRA_FLAG).toBe('enabled');
    expect(options?.env?.CWT_OUTPUT_DIR).toBeDefined();
  });

  it('records registry entries with loop metrics for baseline runs', async () => {
    const tmpRoot = await fs.mkdtemp(path.join(os.tmpdir(), 'baseline-registry-'));
    const artifactsRoot = path.join(tmpRoot, 'artifacts');
    await fs.mkdir(artifactsRoot, { recursive: true });

    const runFolder = '20240102T030405__graph=ring3__seed=7';
    const spawnMock = vi.fn(
      (_command, _args, options?: { env?: NodeJS.ProcessEnv }) =>
        createChildProcess((child) => {
          setImmediate(() => {
            void (async () => {
              const baseOutput = options?.env?.CWT_OUTPUT_DIR ?? artifactsRoot;
              const modelRoot = path.join(baseOutput, 'baselines', 'ising');
              const runDir = path.join(modelRoot, runFolder);
              await fs.mkdir(runDir, { recursive: true });
              await fs.writeFile(
                path.join(runDir, 'summary.json'),
                JSON.stringify({ fs_p95: 0.25, phi: 0.5 }),
                'utf-8',
              );
              const loopsDir = path.join(runDir, 'loops');
              await fs.mkdir(loopsDir, { recursive: true });
              await fs.writeFile(
                path.join(loopsDir, 'loop_tile.json'),
                JSON.stringify({
                  loop: { omega_abs: 0.8, fs_guard_triggered: false },
                  center: { omega: 0.6 },
                }),
                'utf-8',
              );
              child.stdout.emit('data', Buffer.from('loop log\n', 'utf-8'));
              child.emit('close', 0, null);
            })();
          });
        }),
    );

    const payload = baselineRunPayloadSchema.parse({ model: 'ising' });
    const result = await executeBaselineRun(payload, {
      env: pythonEnv,
      artifactsRoot,
      spawnFn: spawnMock as unknown as typeof import('node:child_process').spawn,
    });

    expect(result.status).toBe('complete');
    expect(result.loopMetrics?.loop_count).toBe(1);

    const registryPath = path.join(tmpRoot, 'registry.sqlite');
    let manager: RunManager | null = null;
    try {
      manager = new RunManager({
        repoRoot: tmpRoot,
        artifactsRoot,
        registryPath,
        pythonPathEntries: [],
      });
    } catch (error) {
      const code = (error as NodeJS.ErrnoException | null)?.code;
      if (code === 'ERR_DLOPEN_FAILED') {
        console.warn('Skipping baseline registry test – better-sqlite3 native module unavailable.');
        await removeDir(tmpRoot);
        return;
      }
      throw error;
    }

    try {
      const baseRecord = {
        id: result.runId,
        createdAt: result.startedAt,
        updatedAt: result.completedAt,
        status: result.status,
        command: result.command,
        args: result.args,
        cwd: result.cwd,
        phase: 'baseline',
        experiment: result.model,
        label: `${result.model} baseline`,
        artifactsDir: result.artifactsDir,
        metrics: result.loopMetrics,
      } as const;

      manager.recordExternalRun(baseRecord);
      const summaryMetrics = await manager.collectRunMetrics(result.runId);
      const combined = {
        ...(summaryMetrics ?? {}),
        ...(result.loopMetrics ?? {}),
      } as Record<string, number | null>;

      manager.recordExternalRun({
        ...baseRecord,
        updatedAt: Date.now(),
        metrics: combined,
      });

      const [record] = await manager.fetchRegistry({ id: result.runId });
      expect(record.phase).toBe('baseline');
      expect(record.experiment).toBe('ising');
      expect(record.metrics).toMatchObject({
        loop_count: 1,
        fs_p95: 0.25,
      });

      const tail = await manager.tail(result.runId, 0, 4_096);
      expect(tail.output).toContain('loop log');
    } finally {
      if (manager) {
        await manager.shutdown();
      }
      await removeDir(tmpRoot);
    }
  });
});
