import { describe, expect, it, vi } from 'vitest';
import { EventEmitter } from 'node:events';
import { PassThrough } from 'node:stream';
import type { ChildProcessWithoutNullStreams } from 'node:child_process';

import { baselineRunPayloadSchema, executeBaselineRun } from '../baselines/runService';

const pythonEnv = {
  executable: 'python',
  strategy: 'module' as const,
  version: '3.11.0',
};

const artifactsRoot = '/tmp/artifacts';

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
    });
    expect(parsed.axisMap).toBeNull();
    expect(parsed.args).toEqual(['--flag']);

    expect(() => baselineRunPayloadSchema.parse({ model: 'unknown' } as unknown)).toThrow();
    expect(() => baselineRunPayloadSchema.parse({ model: 'ising', args: [null] } as unknown)).toThrow();
  });

  it('propagates process failures with non-zero exit codes', async () => {
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

    expect(spawnMock).toHaveBeenCalledTimes(1);
    expect(readDirs).toHaveBeenCalledTimes(1);
    expect(exits).toHaveLength(1);
    expect(exits[0].code).toBe(2);
    expect(errors).toEqual([{ runId: exits[0].runId, message: 'Baseline run exited with code 2' }]);
  });
});
