import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { promises as fs } from 'node:fs';
import type { PathLike } from 'node:fs';
import os from 'node:os';
import path from 'node:path';

vi.mock('electron', () => {
  const handlers = new Map<string, (...args: any[]) => any>();
  return {
    app: {
      on: vi.fn(),
      once: vi.fn(),
      quit: vi.fn(),
    },
    ipcMain: {
      handle: vi.fn((channel: string, listener: (...args: any[]) => any) => {
        handlers.set(channel, listener);
      }),
      __handlers: handlers,
    },
    dialog: {
      showOpenDialog: vi.fn(async () => ({ canceled: true, filePaths: [] })),
    },
    BrowserWindow: {
      getFocusedWindow: vi.fn(() => null),
      getAllWindows: vi.fn(() => [] as unknown[]),
    },
  };
});

vi.mock('../runner/env', () => ({
  detectPython: vi.fn(() => ({ environment: null, candidates: [], selected: null })),
  getBundledPythonPathEntries: vi.fn(() => [] as string[]),
  getEnvironmentConfig: vi.fn(async () => ({})),
  setPhase2MetricsRoot: vi.fn(),
  setPythonPath: vi.fn(),
}));

vi.mock('../runner/runManager', () => {
  class MockRunManager {
    #pythonEnv: unknown = null;

    constructor(_config: unknown) {}

    getPythonEnv() {
      return this.#pythonEnv;
    }

    setPythonEnv(env: unknown) {
      this.#pythonEnv = env;
    }

    async shutdown() {}

    async fetchRegistry() {
      return [] as unknown[];
    }

    async createRun() {
      return { runId: 'mock-run' };
    }

    async previewCommand() {
      return { command: 'mock', args: [] as string[] };
    }

    recordExternalRun() {}

    async collectRunMetrics() {
      return {};
    }

    async abort() {}

    async tail() {
      return { output: '', nextFromByte: 0, startFromByte: 0, totalBytes: 0, hasMoreBefore: false, status: 'complete' };
    }

    async listArtifacts() {
      return [] as unknown[];
    }

    async collectDiagnosticsBundle() {
      return {};
    }

    async deleteRun() {}

    async readArtifact() {
      return null;
    }

    async waitForCompletion() {
      return { status: 'complete' };
    }
  }

  return { RunManager: MockRunManager };
});

vi.mock('../runner/files', () => ({
  scanArtifacts: vi.fn(async () => []),
  watchArtifacts: vi.fn(() => ({ close: vi.fn() })),
}));

vi.mock('../baselines/runService', () => ({
  baselineRunPayloadSchema: { parse: vi.fn((value: unknown) => value) },
  executeBaselineRun: vi.fn(async () => ({ runId: 'baseline-run' })),
}));

vi.mock('../baselines/alignment', () => ({
  runBaselineAlignment: vi.fn(async () => ({ runs: [], zipPath: '' })),
}));

vi.mock('../runner/summaryMetrics', () => ({
  flattenSummaryMetrics: vi.fn((value: unknown) => value),
}));

vi.mock('../adiabaticBoundary', () => ({
  runAdiabaticBoundary: vi.fn(async () => ({})),
}));

vi.mock('../graphFamily', () => ({
  cmdGraphFamily: vi.fn(async () => ({})),
}));

vi.mock('../inverseDesign', () => ({
  default: vi.fn(async () => ({})),
}));

vi.mock('../noiseRobust', () => ({
  default: vi.fn(async () => ({})),
}));

vi.mock('../couplingTuner', () => ({
  default: vi.fn(async () => ({})),
}));

vi.mock('../runner/args', () => ({
  buildArgsFromParams: vi.fn(() => [] as string[]),
}));

vi.mock('../../electron/runner/phase2', () => ({
  correlate: vi.fn(async () => ({})),
}));

const removeDir = async (dir: string) => fs.rm(dir, { recursive: true, force: true });

describe("ipcMain.handle('cwt:artifacts:list')", () => {
  const tempDirs: string[] = [];

  beforeEach(() => {
    vi.resetModules();
    vi.clearAllMocks();
  });

  afterEach(async () => {
    for (const dir of tempDirs.splice(0, tempDirs.length)) {
      await removeDir(dir);
    }
  });

  it('returns an empty payload when the directory disappears before readdir completes', async () => {
    const tempRoot = await fs.mkdtemp(path.join(os.tmpdir(), 'ipc-artifacts-'));
    tempDirs.push(tempRoot);

    await fs.mkdir(path.join(tempRoot, 'subdir'), { recursive: true });

    await import('../ipc');
    const { ipcMain } = await import('electron');
    const handler = (ipcMain as unknown as { __handlers: Map<string, (...args: any[]) => any> }).__handlers.get(
      'cwt:artifacts:list',
    );
    expect(handler).toBeTypeOf('function');

    const originalReaddir = fs.readdir.bind(fs);
    const readdirSpy = vi.spyOn(fs, 'readdir').mockImplementation(async (dir: PathLike, options?: any) => {
      if (typeof dir === 'string' && path.resolve(dir) === path.resolve(tempRoot)) {
        const error = new Error('not found');
        (error as NodeJS.ErrnoException).code = 'ENOENT';
        throw error;
      }
      return originalReaddir(dir, options);
    });

    try {
      const result = await handler?.(undefined, { under: tempRoot });
      expect(result).toEqual({ ok: true, data: [] });
    } finally {
      readdirSpy.mockRestore();
    }
  });
});
