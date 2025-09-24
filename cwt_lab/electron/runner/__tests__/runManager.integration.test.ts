import { spawnSync } from 'node:child_process';
import { existsSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import os from 'node:os';

import { afterAll, beforeAll, describe, expect, it } from 'vitest';

import { RunManager } from '../runManager';

const pythonExecutable = process.env.CWT_TEST_PYTHON ?? 'python3';

const ensurePythonAvailable = () => {
  const probe = spawnSync(pythonExecutable, ['--version']);
  if (probe.error || probe.status !== 0) {
    throw new Error(`Python executable \"${pythonExecutable}\" is required for integration tests.`);
  }
};

describe('RunManager integration', () => {
  const tmpRoot = mkdtempSync(path.join(os.tmpdir(), 'run-manager-test-'));
  const artifactsRoot = path.join(tmpRoot, 'artifacts');
  const registryPath = path.join(tmpRoot, 'registry.sqlite');
  const scriptPath = path.join(tmpRoot, 'emit_metrics.py');
  const repoRoot = tmpRoot;

let manager: RunManager | null = null;
let skipSuite = false;

  beforeAll(() => {
    ensurePythonAvailable();

    writeFileSync(
      scriptPath,
      [
        'import json',
        'import os',
        'import sys',
        '',
        "print('fs_p95=0.125 phi=0.456 R=0.789 overlap=0.654 kappa1=2.5')",
        'sys.stdout.flush()',
        'output_dir = os.environ.get("CWT_OUTPUT_DIR", ".")',
        'os.makedirs(output_dir, exist_ok=True)',
        'summary = {"fs_p95": 0.125, "phi": 0.456, "R": 0.789}',
        'with open(os.path.join(output_dir, "summary.json"), "w", encoding="utf-8") as handle:',
        '    json.dump(summary, handle)',
      ].join('\n'),
      'utf-8',
    );

    try {
      manager = new RunManager({
        repoRoot,
        artifactsRoot,
        registryPath,
        pythonPathEntries: [],
      });
      manager.setPythonEnv({ executable: pythonExecutable, version: 'test', strategy: 'installed' });
    } catch (error) {
      const code = (error as NodeJS.ErrnoException)?.code;
      if (code === 'ERR_DLOPEN_FAILED') {
        skipSuite = true;
        console.warn('Skipping RunManager integration tests – better-sqlite3 native module unavailable.');
      } else {
        throw error;
      }
    }
  });

  afterAll(async () => {
    if (manager) {
      await manager.shutdown();
    }
    rmSync(tmpRoot, { recursive: true, force: true });
  });

  it('executes runs, records registry entries, and collects diagnostics bundles', async () => {
    if (skipSuite || !manager) {
      return;
    }

    const { runId } = await manager.createRun(
      pythonExecutable,
      [scriptPath],
      repoRoot,
      { experiment: 'integration-test', label: 'diagnostics' },
    );

    const completion = await manager.waitForCompletion(runId);
    expect(completion.status).toBe('complete');
    expect(completion.exitCode).toBe(0);

    const runs = await manager.fetchRegistry({ id: runId });
    expect(runs).toHaveLength(1);
    const [run] = runs;
    expect(run.metrics).toEqual({ fs_p95: 0.125, phi: 0.456, R: 0.789 });

    const diagnostics = JSON.parse(
      readFileSync(path.join(run.artifactsDir, 'diagnostics.json'), 'utf-8'),
    ) as { status: string; command: string };
    expect(diagnostics.status).toBe('complete');
    expect(diagnostics.command).toBe(pythonExecutable);

    const bundle = await manager.collectDiagnosticsBundle(runId);
    expect(bundle.files).toEqual(
      expect.arrayContaining([
        path.join(run.artifactsDir, 'stdout.log'),
        path.join(run.artifactsDir, 'diagnostics.json'),
      ]),
    );
    expect(bundle.zipPath).toMatch(/diagnostics-\d+\.zip$/);
    expect(existsSync(bundle.zipPath)).toBe(true);
  });
});
