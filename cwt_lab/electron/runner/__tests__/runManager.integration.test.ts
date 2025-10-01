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
    throw new Error(`Python executable "${pythonExecutable}" is required for integration tests.`);
  }
};

describe('RunManager integration', () => {
  const tmpRoot = mkdtempSync(path.join(os.tmpdir(), 'run-manager-test-'));
  const artifactsRoot = path.join(tmpRoot, 'artifacts');
  const registryPath = path.join(tmpRoot, 'registry.sqlite');
  const scriptPath = path.join(tmpRoot, 'emit_metrics.py');
  const csvScriptPath = path.join(tmpRoot, 'emit_metrics_csv.py');
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

    writeFileSync(
      csvScriptPath,
      [
        'import csv',
        'import os',
        'import sys',
        '',
        "print('writing csv metrics')",
        'sys.stdout.flush()',
        'output_dir = os.environ.get("CWT_OUTPUT_DIR", ".")',
        'os.makedirs(output_dir, exist_ok=True)',
        'target_dir = os.path.join(output_dir, "graphA")',
        'os.makedirs(target_dir, exist_ok=True)',
        'with open(os.path.join(target_dir, "metrics.csv"), "w", newline="") as handle:',
        "    writer = csv.writer(handle)",
        "    writer.writerow(['spectral_gap', 'kuramoto_r'])",
        '    writer.writerow([1.0, 0.4])',
        '    writer.writerow([2.0, 0.6])',
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

    const resumed = new RunManager({
      repoRoot,
      artifactsRoot,
      registryPath,
      pythonPathEntries: [],
    });
    resumed.setPythonEnv({ executable: pythonExecutable, version: 'test', strategy: 'installed' });

    const tailChunk = await resumed.tail(runId, 0, 4_096);
    expect(tailChunk.status).toBe('complete');
    expect(tailChunk.failureDetails).toBeNull();
    expect(tailChunk.output).toContain('fs_p95=0.125');

    const artifacts = await resumed.listArtifacts(runId);
    expect(artifacts.some((entry) => entry.relativePath === 'summary.json')).toBe(true);
    const summary = await resumed.readArtifact(runId, 'summary.json');
    expect(summary.contents).toContain('"fs_p95"');

    await resumed.shutdown();

  });

  it('throws a descriptive error when the configured Python interpreter disappears', async () => {
    if (skipSuite) {
      return;
    }

    const artifactsRootMissing = path.join(tmpRoot, 'artifacts-missing');
    const registryMissing = path.join(tmpRoot, 'registry-missing.sqlite');
    const missingManager = new RunManager({
      repoRoot,
      artifactsRoot: artifactsRootMissing,
      registryPath: registryMissing,
      pythonPathEntries: [],
    });

    const missingInterpreterPath = path.join(tmpRoot, 'missing', 'python.exe');
    missingManager.setPythonEnv({ executable: missingInterpreterPath, version: null, strategy: 'module' });

    expect(() =>
      missingManager.previewCommand('experiments.fake', [], repoRoot),
    ).toThrowError(
      `Configured Python interpreter not found at ${missingInterpreterPath}. ` +
        'Re-run environment detection to select a valid interpreter.',
    );

    await missingManager.shutdown();
  });

  it('derives metrics from CSV artifacts when no summary is present', async () => {
    if (skipSuite || !manager) {
      return;
    }

    const { runId } = await manager.createRun(
      pythonExecutable,
      [csvScriptPath],
      repoRoot,
      { experiment: 'integration-test', label: 'csv metrics' },
    );

    const completion = await manager.waitForCompletion(runId);
    expect(completion.status).toBe('complete');

    const [run] = await manager.fetchRegistry({ id: runId });
    expect(run.metrics).not.toBeNull();
    expect(run.metrics?.spectral_gap ?? 0).toBeCloseTo(1.5, 6);
    expect(run.metrics?.kuramoto_r ?? 0).toBeCloseTo(0.5, 6);
  });
});
