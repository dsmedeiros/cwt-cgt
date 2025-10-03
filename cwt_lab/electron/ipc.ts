import { app, ipcMain, dialog, BrowserWindow } from 'electron';
import { spawn } from 'node:child_process';
import { promises as fs, existsSync, mkdirSync } from 'node:fs';
import path from 'node:path';
import { parse as parseYaml, stringify as stringifyYaml } from 'yaml';
import { v4 as uuidv4 } from 'uuid';
import { z } from 'zod';

import {
  detectPython,
  getBundledPythonPathEntries,
  getEnvironmentConfig,
  setPhase2MetricsRoot,
  setPythonPath,
  type PythonCandidate,
} from './runner/env';
import { RunManager, type RunMetadata } from './runner/runManager';
import { artifactsRoot, cwtSimRoot, repoRoot } from './paths';
import type { GuidedLoopArgs, LoopAtHotspotPayload } from '../renderer/types/ipc';
import { runAdiabaticBoundary } from './adiabaticBoundary';
import { cmdGraphFamily } from './graphFamily';
import cmdInverseDesign from './inverseDesign';
import cmdGateCRobust from './noiseRobust';
import runCouplingTuner from './couplingTuner';
import { buildArgsFromParams } from './runner/args';
import { correlate as correlatePhase2 } from '../../electron/runner/phase2';
import { scanArtifacts } from './runner/files';

type Envelope<T> = { ok: true; data: T } | { ok: false; error: string; data?: T };

const registryPath = path.join(artifactsRoot, 'registry.sqlite');
const recipesPath = path.join(artifactsRoot, 'recipes.json');
const exportsRoot = path.join(artifactsRoot, '_exports');

const ensureDirSync = (dir: string) => {
  if (!existsSync(dir)) {
    mkdirSync(dir, { recursive: true });
  }
};

ensureDirSync(artifactsRoot);
ensureDirSync(path.dirname(registryPath));
ensureDirSync(exportsRoot);

const pythonPathEntries = [cwtSimRoot, ...getBundledPythonPathEntries()].filter(
  (entry) => entry && entry.length > 0,
);

const runManager = new RunManager({
  repoRoot,
  artifactsRoot,
  registryPath,
  pythonPathEntries,
});

const ensurePythonEnvironment = () => {
  const existing = runManager.getPythonEnv();
  if (existing) {
    return existing;
  }

  const detection = detectPython();
  if (detection.environment) {
    runManager.setPythonEnv(detection.environment);
    return detection.environment;
  }

  runManager.setPythonEnv(null);
  throw new Error(detection.error ?? 'Python environment not configured. Run env.detect() first.');
};

let shuttingDown = false;
const requestRunnerShutdown = async () => {
  if (shuttingDown) {
    return;
  }
  shuttingDown = true;
  try {
    await runManager.shutdown();
  } catch (error) {
    console.warn('Failed to shut down run manager gracefully:', error);
  }
};

app.on('before-quit', () => {
  void requestRunnerShutdown();
});

['SIGINT', 'SIGTERM', 'SIGHUP'].forEach((signal) => {
  process.once(signal as NodeJS.Signals, () => {
    void requestRunnerShutdown().finally(() => {
      app.quit();
      setTimeout(() => {
        process.exit(0);
      }, 500).unref();
    });
  });
});

process.once('exit', () => {
  if (!shuttingDown) {
    void runManager.shutdown();
  }
});

const recipePayloadSchema = z.object({
  name: z.string().min(1, 'name is required'),
  description: z.string().optional().default(''),
  basedOnRunId: z.string().optional().nullable(),
  params: z.record(z.string(), z.unknown()).optional().default({}),
  command: z.string().min(1, 'command is required'),
  seed: z.number().nullable().optional(),
  envInfo: z.unknown().optional(),
});

const wrap = async <T>(
  fn: () => Promise<T> | T,
  options: { label?: string } = {},
): Promise<Envelope<T>> => {
  try {
    const data = await fn();
    return { ok: true as const, data };
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    if (options.label) {
      console.error(`[IPC:${options.label}] handler failed:`, error);
    } else {
      console.error('[IPC] handler failed:', error);
    }
    return { ok: false as const, error: message };
  }
};

type StoredRecipe = {
  id: string;
  name: string;
  description: string;
  basedOnRunId: string | null;
  params: Record<string, unknown>;
  command: string;
  seed: number | null;
  envInfo: unknown;
  createdAt: string;
};

const normalizeRecipe = (input: any): StoredRecipe => {
  const id = typeof input?.id === 'string' ? input.id : uuidv4();
  const name = typeof input?.name === 'string' ? input.name : 'Untitled recipe';
  const description = typeof input?.description === 'string' ? input.description : '';
  const basedOnRunId =
    typeof input?.basedOnRunId === 'string'
      ? input.basedOnRunId
      : typeof input?.based_on_run_id === 'string'
      ? input.based_on_run_id
      : null;
  const params =
    input && typeof input.params === 'object' && input.params !== null
      ? (input.params as Record<string, unknown>)
      : input && typeof input.params_json === 'object' && input.params_json !== null
      ? (input.params_json as Record<string, unknown>)
      : {};
  const command = typeof input?.command === 'string' ? input.command : '';
  const seed = Number.isFinite(input?.seed) ? Number(input.seed) : null;
  const envInfo = input?.envInfo ?? input?.envInfo_json ?? null;
  const createdAt =
    typeof input?.createdAt === 'string'
      ? input.createdAt
      : typeof input?.created_at === 'string'
      ? input.created_at
      : new Date().toISOString();

  return { id, name, description, basedOnRunId, params, command, seed, envInfo, createdAt };
};

const loadRecipes = async (): Promise<StoredRecipe[]> => {
  if (!existsSync(recipesPath)) {
    return [];
  }

  const content = await fs.readFile(recipesPath, 'utf-8');
  try {
    const parsed = JSON.parse(content);
    const records = Array.isArray(parsed) ? parsed : [];
    return records.map((entry) => normalizeRecipe(entry));
  } catch {
    return [];
  }
};

const saveRecipes = async (recipes: StoredRecipe[]) => {
  await fs.writeFile(recipesPath, JSON.stringify(recipes, null, 2), 'utf-8');
};

const parseFiniteNumber = (value: unknown): number | null => {
  if (typeof value === 'number') {
    return Number.isFinite(value) ? value : null;
  }
  if (typeof value === 'string') {
    const trimmed = value.trim();
    if (!trimmed) {
      return null;
    }
    const parsed = Number(trimmed);
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
};

const formatNumber = (value: number): string => {
  const abs = Math.abs(value);
  if ((abs > 0 && abs < 0.0001) || abs >= 1000) {
    return value.toExponential(2);
  }
  const decimals = abs >= 1 ? 3 : 4;
  return value.toFixed(decimals).replace(/0+$/, '').replace(/\.$/, '');
};

const formatPercent = (value: number | null): string | null => {
  if (value == null) {
    return null;
  }
  const percent = value * 100;
  if (!Number.isFinite(percent)) {
    return null;
  }
  const digits = Math.abs(percent) >= 10 ? 0 : 1;
  return percent.toFixed(digits).replace(/\.0$/, '');
};

const loadRunMeta = async (artifactsDir: string): Promise<Record<string, unknown> | null> => {
  const metaPath = path.join(artifactsDir, 'meta.json');
  if (!existsSync(metaPath)) {
    return null;
  }
  try {
    const raw = await fs.readFile(metaPath, 'utf-8');
    const parsed = JSON.parse(raw);
    return parsed && typeof parsed === 'object' ? (parsed as Record<string, unknown>) : null;
  } catch {
    return null;
  }
};

const loadSummaryMetrics = async (
  artifactsDir: string,
): Promise<Record<string, number | null> | null> => {
  const summaryPath = path.join(artifactsDir, 'summary.json');
  if (!existsSync(summaryPath)) {
    return null;
  }
  try {
    const raw = await fs.readFile(summaryPath, 'utf-8');
    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== 'object') {
      return null;
    }
    const metrics: Record<string, number | null> = {};
    for (const [key, value] of Object.entries(parsed as Record<string, unknown>)) {
      if (typeof value === 'number') {
        metrics[key] = Number.isFinite(value) ? value : null;
      } else if (typeof value === 'boolean') {
        metrics[key] = value ? 1 : 0;
      }
    }
    return Object.keys(metrics).length > 0 ? metrics : null;
  } catch {
    return null;
  }
};

type GuardSummary = {
  threshold: number | null;
  boundary: number | null;
  fraction: number | null;
};

const extractGuardSummary = (
  meta: Record<string, unknown> | null,
  metrics: Record<string, number | null> | null,
): GuardSummary => {
  let guardMeta: Record<string, unknown> | null = null;
  if (meta && typeof meta.meta === 'object' && meta.meta !== null) {
    const nested = (meta.meta as Record<string, unknown>).fs_step_guard;
    if (nested && typeof nested === 'object') {
      guardMeta = nested as Record<string, unknown>;
    }
  }

  const summary: GuardSummary = {
    threshold: guardMeta ? parseFiniteNumber(guardMeta.threshold) : null,
    boundary: guardMeta ? parseFiniteNumber(guardMeta.boundary) : null,
    fraction: guardMeta ? parseFiniteNumber(guardMeta.fraction) : null,
  };

  if (summary.threshold == null && guardMeta) {
    summary.threshold = parseFiniteNumber(guardMeta.guard_threshold ?? guardMeta.max);
  }

  if (summary.threshold == null && metrics) {
    const threshold = metrics['fs_guard'] ?? metrics['fs_threshold'];
    if (typeof threshold === 'number' && Number.isFinite(threshold)) {
      summary.threshold = threshold;
    }
  }

  if (summary.boundary == null && metrics) {
    const boundary = metrics['fs_boundary'];
    if (typeof boundary === 'number' && Number.isFinite(boundary)) {
      summary.boundary = boundary;
    }
  }

  return summary;
};

const formatGuardSummary = (summary: GuardSummary): string => {
  const parts: string[] = [];
  if (summary.threshold != null) {
    parts.push(`${formatNumber(summary.threshold)} rad threshold`);
  }
  if (summary.boundary != null) {
    parts.push(`${formatNumber(summary.boundary)} rad boundary`);
  }
  const fraction = formatPercent(summary.fraction);
  if (fraction) {
    parts.push(`fraction ${fraction}%`);
  }
  return parts.length > 0 ? parts.join(', ') : 'n/a';
};

const formatHeadlineMetrics = (metrics: Record<string, number | null> | null): string => {
  if (!metrics) {
    return 'n/a';
  }

  const pickMetric = (keys: string[]): number | null => {
    for (const key of keys) {
      const value = metrics[key];
      if (typeof value === 'number' && Number.isFinite(value)) {
        return value;
      }
    }
    return null;
  };

  const parts: string[] = [];

  const phi = pickMetric(['phi_flux', 'phi_sum', 'phi_value', 'phi']);
  if (phi != null) {
    parts.push(`Φ=${formatNumber(phi)}`);
  } else {
    const phiForward = pickMetric(['phi_forward']);
    const phiReverse = pickMetric(['phi_reverse']);
    if (phiForward != null && phiReverse != null) {
      parts.push(`Φ=${formatNumber(phiForward + phiReverse)}`);
    } else if (phiForward != null) {
      parts.push(`Φ₊=${formatNumber(phiForward)}`);
    } else if (phiReverse != null) {
      parts.push(`Φ₋=${formatNumber(phiReverse)}`);
    }
  }

  const rValue = pickMetric(['r_value', 'kuramoto_r', 'r']);
  if (rValue != null) {
    parts.push(`R=${formatNumber(rValue)}`);
  }

  const fsP95 = pickMetric(['fs_p95', 'fs95', 'fs_mean']);
  if (fsP95 != null) {
    parts.push(`FS p95=${formatNumber(fsP95)}`);
  }

  const fsBoundary = pickMetric(['fs_boundary']);
  if (fsBoundary != null) {
    parts.push(`FS boundary=${formatNumber(fsBoundary)}`);
  }

  const guardExceeded = metrics['fs_guard_exceeded'];
  if (typeof guardExceeded === 'number') {
    parts.push(guardExceeded >= 0.5 ? 'guard exceeded' : 'guard ok');
  }

  return parts.length > 0 ? parts.join(', ') : 'n/a';
};

const exportRecipeBundle = async (recipe: StoredRecipe) => {
  const exportId = `${recipe.id}-${Date.now()}`;
  const bundleDir = path.join(exportsRoot, exportId);
  await fs.mkdir(bundleDir, { recursive: true });

  let originPhase: string | null = null;
  let originCommand: string | null = null;
  let guardSummary = 'n/a';
  let metricsSummary = 'n/a';
  let originRunArtifacts: string | null = null;
  let originMetrics: Record<string, number | null> | null = null;

  if (recipe.basedOnRunId) {
    const runs = await runManager.fetchRegistry({ id: recipe.basedOnRunId, limit: 1 });
    const runRecord = runs[0];
    if (runRecord) {
      originPhase = runRecord.phase ?? null;
      originCommand = runRecord.command ?? null;
      originRunArtifacts = runRecord.artifactsDir ?? null;
      originMetrics = runRecord.metrics ?? null;
    }
  }

  let runMeta: Record<string, unknown> | null = null;
  if (originRunArtifacts && existsSync(originRunArtifacts)) {
    runMeta = await loadRunMeta(originRunArtifacts);
    const summaryMetrics = await loadSummaryMetrics(originRunArtifacts);
    if (summaryMetrics) {
      originMetrics = originMetrics ? { ...summaryMetrics, ...originMetrics } : summaryMetrics;
    }
  }

  guardSummary = formatGuardSummary(extractGuardSummary(runMeta, originMetrics));
  metricsSummary = formatHeadlineMetrics(originMetrics);

  const scriptCandidate = originCommand && originCommand.trim() ? originCommand : null;
  const recipeCommand = recipe.command && recipe.command.trim() ? recipe.command : null;
  const scriptLine = scriptCandidate ?? recipeCommand ?? 'n/a';
  const readmeLines = [
    '# Research Pack',
    '',
    '## Summary',
    `- Recipe: ${recipe.name}`,
    `- Description: ${recipe.description || '(none)'}`,
    `- Created at: ${recipe.createdAt}`,
    `- Command: ${recipe.command}`,
    `- Seed: ${recipe.seed ?? 'n/a'}`,
    `- Based on run: ${recipe.basedOnRunId ?? 'n/a'}`,
    `- Phase: ${originPhase ?? 'n/a'}`,
    `- Script: ${scriptLine}`,
    `- Guard limit: ${guardSummary}`,
    `- Metrics: ${metricsSummary}`,
    '',
  ];
  await fs.writeFile(path.join(bundleDir, 'README.md'), readmeLines.join('\n'), 'utf-8');
  await fs.writeFile(path.join(bundleDir, 'command.txt'), `${recipe.command}\n`, 'utf-8');
  await fs.writeFile(path.join(bundleDir, 'params.json'), JSON.stringify(recipe.params ?? {}, null, 2), 'utf-8');

  const env = runManager.getPythonEnv();
  const envPayload = {
    pythonExecutable: env?.executable ?? null,
    strategy: env?.strategy ?? null,
    platform: process.platform,
    envInfo: recipe.envInfo ?? null,
  };
  await fs.writeFile(path.join(bundleDir, 'env.json'), JSON.stringify(envPayload, null, 2), 'utf-8');

  if (env?.executable) {
    const freezePath = path.join(bundleDir, 'pip-freeze.txt');
    try {
      await new Promise<void>((resolve) => {
        const child = spawn(env.executable, ['-m', 'pip', 'freeze'], { cwd: cwtSimRoot });
        const chunks: Buffer[] = [];
        child.stdout.on('data', (chunk: Buffer) => chunks.push(chunk));
        child.on('error', () => resolve());
        child.on('close', async (code) => {
          if (code === 0) {
            await fs.writeFile(freezePath, Buffer.concat(chunks).toString('utf-8'), 'utf-8');
          }
          resolve();
        });
      });
    } catch {
      /* ignore pip-freeze failures */
    }
  }

  const copiedFiles: string[] = [];
  if (originRunArtifacts && existsSync(originRunArtifacts)) {
    const entries = await scanArtifacts(originRunArtifacts);
    const interesting = entries.filter(
      (entry) =>
        entry.type === 'file' &&
        /report|heatmap|plateau|loop|summary/i.test(entry.relativePath) &&
        (entry.relativePath.endsWith('.png') || entry.relativePath.endsWith('.md') || entry.relativePath.endsWith('.json')),
    );
    if (interesting.length > 0) {
      const artifactsDir = path.join(bundleDir, 'artifacts');
      await fs.mkdir(artifactsDir, { recursive: true });
      for (const file of interesting.slice(0, 12)) {
        const target = path.join(artifactsDir, path.basename(file.relativePath));
        await fs.copyFile(file.path, target);
        copiedFiles.push(path.basename(file.relativePath));
      }
    }
  }

  const zipName = `${exportId}.zip`;
  await new Promise<void>((resolve, reject) => {
    const child = spawn('zip', ['-r', zipName, exportId], { cwd: exportsRoot });
    child.on('error', reject);
    child.on('close', (code) => {
      if (code === 0) {
        resolve();
      } else {
        reject(new Error(`zip exited with code ${code ?? 'unknown'}`));
      }
    });
  });

  await fs.rm(bundleDir, { recursive: true, force: true });

  return {
    zipPath: path.join(exportsRoot, zipName),
    attachments: copiedFiles,
  };
};

const listDirectoryTree = async (root: string, base: string) => {
  const entries = await fs.readdir(root, { withFileTypes: true });
  const result: Array<{
    name: string;
    path: string;
    type: 'file' | 'directory';
    relativePath: string;
    children?: unknown[];
  }> = [];

  for (const entry of entries) {
    const entryPath = path.join(root, entry.name);
    const relativePath = path.relative(base, entryPath);
    if (entry.isDirectory()) {
      result.push({
        name: entry.name,
        path: entryPath,
        type: 'directory',
        relativePath,
        children: await listDirectoryTree(entryPath, base),
      });
    } else {
      result.push({
        name: entry.name,
        path: entryPath,
        type: 'file',
        relativePath,
      });
    }
  }

  result.sort((a, b) => a.name.localeCompare(b.name));
  return result;
};

ipcMain.handle('cwt:env:detect', () => {
  const result = detectPython();
  const payload = {
    candidates: result.candidates,
    selected: result.selected,
  } satisfies {
    candidates: PythonCandidate[];
    selected: PythonCandidate | null;
  };

  if (result.environment) {
    runManager.setPythonEnv(result.environment);
    return { ok: true as const, data: payload } satisfies Envelope<typeof payload>;
  }

  runManager.setPythonEnv(null);
  return {
    ok: false as const,
    error: result.error ?? 'No usable Python interpreter found.',
    data: payload,
  } satisfies Envelope<typeof payload>;
});

ipcMain.handle('cwt:env:set-python-path', (_event, executable: string) =>
  wrap(() => {
    const { candidate, environment } = setPythonPath(executable);
    runManager.setPythonEnv(environment);
    return candidate;
  }),
);

ipcMain.handle('cwt:env:set-phase2-root', (_event, payload?: { path?: unknown }) =>
  wrap(() => {
    const raw = payload?.path;
    const value = typeof raw === 'string' ? raw : null;
    const result = setPhase2MetricsRoot(value);
    return { path: result } satisfies { path: string | null };
  }),
);

ipcMain.handle('cwt:env:get-config', () => wrap(() => getEnvironmentConfig()));

ipcMain.handle('cwt:env:browse-python', () =>
  wrap(async () => {
    const window = BrowserWindow.getFocusedWindow() ?? BrowserWindow.getAllWindows()[0];
    const filters = process.platform === 'win32'
      ? [{ name: 'Python executables', extensions: ['exe'] }]
      : undefined;
    const { canceled, filePaths } = await dialog.showOpenDialog(window ?? undefined, {
      title: 'Select Python executable',
      properties: ['openFile'],
      buttonLabel: 'Use interpreter',
      filters,
    });

    return {
      canceled,
      path: canceled || filePaths.length === 0 ? null : filePaths[0],
    };
  }),
);

ipcMain.handle(
  'cwt:run:create',
  (
    _event,
    payload: { experiment: string; args?: Record<string, unknown>; workdir?: string; timeoutMs?: number },
  ) =>
    wrap(async () => {
      if (!payload?.experiment) {
        throw new Error('experiment is required');
      }

      ensurePythonEnvironment();
      const args = buildArgsFromParams(payload.args);
      const cwd = payload.workdir ? path.resolve(payload.workdir) : cwtSimRoot;
      return runManager.createRun(
        payload.experiment,
        args,
        cwd,
        {
          experiment: payload.experiment,
        },
        { timeoutMs: payload.timeoutMs },
      );
    }, { label: 'cwt:run:create' }),
);

ipcMain.handle(
  'cwt:run:preview',
  (
    _event,
    payload: { experiment: string; args?: Record<string, unknown>; workdir?: string },
  ) =>
    wrap(() => {
      if (!payload?.experiment) {
        throw new Error('experiment is required');
      }

      ensurePythonEnvironment();
      const args = buildArgsFromParams(payload.args);
      const cwd = payload.workdir ? path.resolve(payload.workdir) : cwtSimRoot;
      return runManager.previewCommand(payload.experiment, args, cwd);
    }, { label: 'cwt:run:preview' }),
);

ipcMain.handle('cwt:run:abort', (_event, payload: { runId: string }) =>
  wrap(async () => {
    if (!payload?.runId) {
      throw new Error('runId is required');
    }
    await runManager.abort(payload.runId);
    return { runId: payload.runId };
  }, { label: 'cwt:run:abort' }),
);

ipcMain.handle('cwt:run:tail', (_event, payload: { runId: string; fromByte?: number }) =>
  wrap(async () => {
    if (!payload?.runId) {
      throw new Error('runId is required');
    }

    return runManager.tail(payload.runId, payload.fromByte ?? 0, (payload as { maxBytes?: number }).maxBytes);
  }, { label: 'cwt:run:tail' }),
);

ipcMain.handle('cwt:run:open-artifacts', (_event, payload: { runId: string }) =>
  wrap(async () => {
    if (!payload?.runId) {
      throw new Error('runId is required');
    }

    return runManager.listArtifacts(payload.runId);
  }, { label: 'cwt:run:open-artifacts' }),
);

ipcMain.handle('cwt:run:collect-diagnostics', (_event, payload: { runId: string }) =>
  wrap(async () => {
    if (!payload?.runId) {
      throw new Error('runId is required');
    }

    return runManager.collectDiagnosticsBundle(payload.runId);
  }, { label: 'cwt:run:collect-diagnostics' }),
);

ipcMain.handle('cwt:run:delete', (_event, payload: { runId: string }) =>
  wrap(async () => {
    if (!payload?.runId) {
      throw new Error('runId is required');
    }

    return runManager.deleteRun(payload.runId);
  }, { label: 'cwt:run:delete' }),
);

ipcMain.handle('cwt:run:read-artifact', (_event, payload: { runId: string; relativePath: string }) =>
  wrap(async () => {
    if (!payload?.runId) {
      throw new Error('runId is required');
    }
    if (!payload?.relativePath || typeof payload.relativePath !== 'string') {
      throw new Error('relativePath is required');
    }

    return runManager.readArtifact(payload.runId, payload.relativePath);
  }, { label: 'cwt:run:read-artifact' }),
);

const launchPhase = (
  module: string,
  params: Record<string, unknown> | undefined,
  metadata: RunMetadata,
) => {
  ensurePythonEnvironment();
  const args = buildArgsFromParams(params);
  return runManager.createRun(module, args, cwtSimRoot, metadata);
};

ipcMain.handle('cwt:phase1:map', (_event, params) =>
  wrap(() =>
    launchPhase('experiments.gateB_ridge_finder.run', params, {
      phase: 'phase1',
      experiment: 'gateB_ridge_finder',
      label: 'Ridge finder grid scan',
    }),
  ),
);

ipcMain.handle('cwt:phase3:browse-hotspots', () =>
  wrap(
    async () => {
      const window = BrowserWindow.getFocusedWindow() ?? BrowserWindow.getAllWindows()[0];
      const { canceled, filePaths } = await dialog.showOpenDialog(window ?? undefined, {
        title: 'Select Phase 1 ridge map',
        properties: ['openFile'],
        buttonLabel: 'Load hotspots',
        filters: [
          { name: 'Phase 1 ridge map (top_omega_tiles.json)', extensions: ['json'] },
          { name: 'JSON files', extensions: ['json'] },
        ],
      });

      if (canceled || filePaths.length === 0) {
        return { canceled: true, path: null, contents: null };
      }

      const filePath = path.resolve(filePaths[0]);
      const contents = await fs.readFile(filePath, 'utf-8');
      return { canceled: false, path: filePath, contents };
    },
    { label: 'cwt:phase3:browse-hotspots' },
  ),
);

ipcMain.handle('cwt:phase3:loop-at-hotspot', (_event, params) =>
  wrap(async () => {
    if (!params || typeof params !== 'object') {
      throw new Error('parameters are required for loop-at-hotspot');
    }

    const payload = params as LoopAtHotspotPayload & Record<string, unknown>;
    const hotspotsRaw =
      typeof payload.hotspotsJson === 'string' ? payload.hotspotsJson.trim() : '';
    if (!hotspotsRaw) {
      throw new Error('hotspotsJson must be a non-empty string or JSON payload');
    }

    let hotspotsPath = hotspotsRaw;
    if (hotspotsRaw.startsWith('{') || hotspotsRaw.startsWith('[')) {
      let parsed: unknown;
      try {
        parsed = JSON.parse(hotspotsRaw);
      } catch (error) {
        throw new Error('hotspotsJson must be valid JSON when provided inline');
      }

      const inlineDir = path.join(artifactsRoot, '_temp', 'phase3_hotspots');
      ensureDirSync(inlineDir);
      hotspotsPath = path.join(inlineDir, `hotspots-${uuidv4()}.json`);
      await fs.writeFile(hotspotsPath, JSON.stringify(parsed, null, 2), 'utf8');
    }

    const axesRaw = Array.isArray(payload.axes) ? payload.axes : [];
    if (axesRaw.length !== 2) {
      throw new Error('axes must contain exactly two axis names');
    }
    const axes = axesRaw.map((axis, index) => {
      const value = String(axis).trim();
      if (!value) {
        throw new Error(`axis ${index + 1} must be a non-empty string`);
      }
      return value;
    }) as [string, string];

    const extentsRaw = Array.isArray(payload.extents) ? payload.extents : [];
    if (extentsRaw.length === 0) {
      throw new Error('extents must contain at least one numeric value');
    }
    const extents = extentsRaw.map((value, index) => {
      const numeric = Number(value);
      if (!Number.isFinite(numeric)) {
        throw new Error(`extent ${index + 1} must be a finite number`);
      }
      return numeric;
    });

    const fsGuard = Number(payload.fsGuard);
    if (!Number.isFinite(fsGuard)) {
      throw new Error('fsGuard must be a finite number');
    }

    const graph = typeof payload.graph === 'string' ? payload.graph.trim() : '';
    if (!graph) {
      throw new Error('graph must be a non-empty string');
    }

    const limit = Number(payload.limit);
    if (!Number.isInteger(limit) || limit <= 0) {
      throw new Error('limit must be a positive integer');
    }

    const seed = Number(payload.seed);
    if (!Number.isInteger(seed)) {
      throw new Error('seed must be an integer');
    }

    const passthrough = { ...(payload as Record<string, unknown>) };
    delete passthrough.hotspotsJson;
    delete passthrough.axes;
    delete passthrough.extents;
    delete passthrough.fsGuard;
    delete passthrough.graph;
    delete passthrough.limit;
    delete passthrough.seed;
    delete passthrough.microScan;
    delete passthrough.readoutTarget;
    delete passthrough.neighborSettleSteps;
    delete passthrough.adaptLevels;

    if (payload.saveSummary !== undefined) {
      const summaryPath = typeof payload.saveSummary === 'string' ? payload.saveSummary.trim() : '';
      if (!summaryPath) {
        throw new Error('saveSummary must be a non-empty string path when provided');
      }
      passthrough.saveSummary = summaryPath;
    }

    let microScan: boolean | undefined;
    const rawMicroScan = (params as { microScan?: unknown }).microScan;
    if (rawMicroScan !== undefined) {
      if (typeof rawMicroScan === 'string') {
        const normalized = rawMicroScan.trim().toLowerCase();
        if (['true', 't', '1', 'yes', 'y'].includes(normalized)) {
          microScan = true;
        } else if (['false', 'f', '0', 'no', 'n'].includes(normalized)) {
          microScan = false;
        } else {
          throw new Error('microScan must be a boolean value');
        }
      } else {
        microScan = Boolean(rawMicroScan);
      }
    }

    const readoutTargetRaw = (params as { readoutTarget?: unknown }).readoutTarget;
    let readoutTarget: number | null = null;
    if (readoutTargetRaw !== undefined && readoutTargetRaw !== null) {
      readoutTarget = Number(readoutTargetRaw);
      if (!Number.isInteger(readoutTarget)) {
        throw new Error('readoutTarget must be an integer when provided');
      }
    }

    const settleRaw = (params as { neighborSettleSteps?: unknown }).neighborSettleSteps;
    let neighborSettleSteps: number | null = null;
    if (settleRaw !== undefined && settleRaw !== null) {
      const parsed = Number(settleRaw);
      if (!Number.isInteger(parsed) || parsed <= 0) {
        throw new Error('neighborSettleSteps must be a positive integer when provided');
      }
      neighborSettleSteps = parsed;
    }

    const adaptRaw = (params as { adaptLevels?: unknown }).adaptLevels;
    let adaptLevels: number | null = null;
    if (adaptRaw !== undefined && adaptRaw !== null) {
      const parsed = Number(adaptRaw);
      if (!Number.isInteger(parsed) || parsed <= 0) {
        throw new Error('adaptLevels must be a positive integer when provided');
      }
      adaptLevels = parsed;
    }

    const runParams: Record<string, unknown> = {
      ...passthrough,
      hotspots: hotspotsPath,
      axes,
      extents,
      graph,
      fsGuard,
      limit,
      seed,
    };

    if (microScan !== undefined) {
      runParams.microScan = microScan;
    }
    if (readoutTarget !== null) {
      runParams.readoutTarget = readoutTarget;
    }
    if (neighborSettleSteps !== null) {
      runParams.neighborSettleSteps = neighborSettleSteps;
    }
    if (adaptLevels !== null) {
      runParams.adaptLevels = adaptLevels;
    }

    return launchPhase('experiments.loop_at_hotspot.run', runParams, {
      phase: 'phase3',
      experiment: 'loop_at_hotspot',
      label: 'Loop at hotspot',
    });
  }),
);

ipcMain.handle('cwt:phase3:guided-loop', (_event, params) =>
  wrap(async () => {
    if (!params || typeof params !== 'object') {
      throw new Error('parameters are required for guided mode');
    }

    const payload = params as GuidedLoopArgs & Record<string, unknown>;
    const {
      stepsList: rawSteps,
      minPhi: rawMinPhi,
      axes3: rawAxes,
      center: rawCenter,
      amplitudes: rawAmplitudes,
      fsGuard: rawFsGuard,
      settle: rawSettle,
      handleSteps: rawHandle,
      graph: rawGraph,
      seed: rawSeed,
      ...otherParams
    } = payload;

    const stepsList = Array.isArray(rawSteps)
      ? rawSteps
          .map((value, index) => {
            const parsed = Number.parseInt(String(value), 10);
            if (!Number.isFinite(parsed)) {
              throw new Error(`stepsList entry #${index + 1} must be an integer`);
            }
            if (parsed <= 0) {
              throw new Error(`stepsList entry #${index + 1} must be positive`);
            }
            return parsed;
          })
      : [];
    if (stepsList.length === 0) {
      throw new Error('stepsList must contain at least one integer value');
    }

    const minPhiRaw = rawMinPhi !== undefined && rawMinPhi !== null ? Number(rawMinPhi) : null;
    const minPhi = minPhiRaw !== null && Number.isFinite(minPhiRaw) ? minPhiRaw : null;
    if (rawMinPhi !== undefined && minPhi === null) {
      throw new Error('minPhi must be a finite number when provided');
    }

    const axes3 = Array.isArray(rawAxes) ? rawAxes.map((axis) => String(axis).trim()) : [];
    if (axes3.length !== 3) {
      throw new Error('axes3 must contain exactly three axis names');
    }
    if (axes3.some((axis) => !axis)) {
      throw new Error('axes3 entries must be non-empty strings');
    }
    if (new Set(axes3).size !== axes3.length) {
      throw new Error('axes3 entries must be distinct');
    }

    const center = Array.isArray(rawCenter) ? rawCenter.map((value) => Number(value)) : [];
    if (center.length !== 3 || center.some((value) => !Number.isFinite(value))) {
      throw new Error('center must contain three numeric coordinates');
    }

    const amplitudes = Array.isArray(rawAmplitudes)
      ? rawAmplitudes.map((value) => Number(value))
      : [];
    if (amplitudes.length !== 3 || amplitudes.some((value) => !Number.isFinite(value))) {
      throw new Error('amplitudes must contain three numeric values');
    }

    const fsGuardRaw = rawFsGuard !== undefined && rawFsGuard !== null ? Number(rawFsGuard) : null;
    const fsGuard = fsGuardRaw !== null && Number.isFinite(fsGuardRaw) ? fsGuardRaw : null;
    if (rawFsGuard !== undefined && fsGuard === null) {
      throw new Error('fsGuard must be a finite number when provided');
    }

    const settleRaw = rawSettle !== undefined && rawSettle !== null ? Number(rawSettle) : null;
    const settle = settleRaw !== null && Number.isInteger(settleRaw) && settleRaw > 0 ? settleRaw : null;
    if (rawSettle !== undefined && settle === null) {
      throw new Error('settle must be a positive integer when provided');
    }

    const handleRaw = rawHandle !== undefined && rawHandle !== null ? Number(rawHandle) : null;
    const handleSteps =
      handleRaw !== null && Number.isInteger(handleRaw) && handleRaw > 0 ? handleRaw : null;
    if (rawHandle !== undefined && handleSteps === null) {
      throw new Error('handleSteps must be a positive integer when provided');
    }

    const graph = typeof rawGraph === 'string' ? rawGraph.trim() : '';
    if (!graph) {
      throw new Error('graph must be a non-empty string');
    }

    const seedRaw = rawSeed !== undefined && rawSeed !== null ? Number(rawSeed) : null;
    const seed = seedRaw !== null && Number.isInteger(seedRaw) ? seedRaw : null;
    if (rawSeed !== undefined && seed === null) {
      throw new Error('seed must be an integer when provided');
    }

    const baseRunParams: Record<string, unknown> = {
      ...otherParams,
      axes3,
      center,
      amplitudes,
      graph,
    };

    if (fsGuard !== null) {
      baseRunParams.fsGuard = fsGuard;
    }
    if (settle !== null) {
      baseRunParams.settle = settle;
    }
    if (handleSteps !== null) {
      baseRunParams.handleSteps = handleSteps;
    }
    if (seed !== null) {
      baseRunParams.seed = seed;
    }

    ensurePythonEnvironment();
    const runs: Array<{
      runId: string;
      steps: number;
      status: string;
      metrics: Record<string, number | null> | null;
    }> = [];
    let satisfied = false;

    for (const steps of stepsList) {
      const currentParams = {
        ...baseRunParams,
        steps,
      } as Record<string, unknown>;

      const { runId } = await runManager.createRun(
        'experiments.wilson_loop_3d.run',
        buildArgsFromParams(currentParams),
        cwtSimRoot,
        {
          phase: 'phase3',
          experiment: 'wilson_loop_3d_guided',
          label: `Guided Wilson loop (${steps} steps)`,
        },
      );

      const completion = await runManager.waitForCompletion(runId);
      const metrics = await runManager.collectRunMetrics(runId);

      runs.push({
        runId,
        steps,
        status: completion.status,
        metrics,
      });

      if (completion.status !== 'complete' || !metrics) {
        continue;
      }

      const phiSum = metrics.phi_sum ?? metrics.phiForward ?? metrics.phi_forward ?? null;
      const fsExceeded = metrics.fs_guard_exceeded ?? null;

      const phiCriterion =
        minPhi === null ||
        (typeof phiSum === 'number' && Number.isFinite(phiSum) && phiSum >= minPhi);
      const guardCriterion =
        fsGuard === null ||
        metrics.fs_p95 === undefined ||
        metrics.fs_p95 === null ||
        metrics.fs_p95 <= fsGuard;

      if (phiCriterion && guardCriterion) {
        satisfied = true;
        break;
      }

      if (
        fsGuard !== null &&
        ((typeof metrics.fs_p95 === 'number' && metrics.fs_p95 > fsGuard) ||
          (typeof fsExceeded === 'number' && fsExceeded > 0))
      ) {
        continue;
      }
    }

    return { runs, satisfied };
  }),
);

ipcMain.handle('cwt:phase3:adiabatic-boundary', (_event, payload) =>
  wrap(() => {
    if (!payload || typeof payload !== 'object') {
      throw new Error('parameters are required for adiabatic-boundary');
    }

    const { outDir: rawOutDir, ...rest } = payload as { outDir?: unknown } & Record<string, unknown>;
    const outDir = typeof rawOutDir === 'string' ? rawOutDir.trim() : '';
    if (!outDir) {
      throw new Error('outDir must be a non-empty string path');
    }

    const runParams: Record<string, unknown> = {
      ...rest,
      outputDir: outDir,
    };

    return launchPhase('experiments.adiabatic_boundary.run', runParams, {
      phase: 'phase3',
      experiment: 'adiabatic_boundary',
      label: 'Adiabatic boundary sweep',
    });
  }),
);

ipcMain.handle('cwt:phase3:adiabatic-boundary:analyze', (_event, params) =>
  wrap(() => {
    ensurePythonEnvironment();
    return runAdiabaticBoundary(
      runManager,
      cwtSimRoot,
      artifactsRoot,
      params as Record<string, unknown> | undefined,
    );
  }),
);

ipcMain.handle('cwt:phase4:wilson3d', (_event, params) =>
  wrap(() =>
    launchPhase('experiments.wilson_loop_3d.run', params, {
      phase: 'phase4',
      experiment: 'wilson_loop_3d',
      label: 'Wilson loop 3D sweep',
    }),
  ),
);

ipcMain.handle('cwt:phase4:torus-plateau', (_event, params) =>
  wrap(() =>
    launchPhase('experiments.torus_plateau.run', params, {
      phase: 'phase4',
      experiment: 'torus_plateau',
      label: 'Torus plateau survey',
    }),
  ),
);

ipcMain.handle('cwt:phase5:graph-family', (_event, params) =>
  wrap(() =>
    launchPhase('experiments.graph_family.run', params, {
      phase: 'phase5',
      experiment: 'graph_family',
      label: 'Graph family sweep',
    }),
  ),
);

ipcMain.handle('cwt:phase5:graph-family:analyze', (_event, payload) =>
  wrap(async () => {
    const env = ensurePythonEnvironment();

    const familiesRaw = Array.isArray(payload?.families)
      ? payload?.families
      : typeof payload?.families === 'string'
        ? payload?.families.split(',')
        : ['ring', 'rr', 'sw', 'sf', 'mod'];
    const families = familiesRaw
      .map((entry: unknown) => String(entry ?? '').trim())
      .filter((entry: string): entry is string => entry.length > 0);
    if (families.length === 0) {
      throw new Error('Select at least one graph family.');
    }

    const axesRaw = Array.isArray(payload?.axes) ? payload.axes : [];
    if (axesRaw.length !== 2) {
      throw new Error('axes must contain exactly two entries.');
    }
    const axes = axesRaw.map((axis: unknown) => String(axis ?? '').trim()) as [string, string];
    if (!axes[0] || !axes[1]) {
      throw new Error('axes entries must be non-empty strings.');
    }
    if (axes[0].toLowerCase() === axes[1].toLowerCase()) {
      throw new Error('axes must be distinct.');
    }

    const gridSizeValue = payload?.gridSize ?? payload?.grid_size ?? 21;
    const gridSize = Number(gridSizeValue);
    if (!Number.isInteger(gridSize) || gridSize <= 0) {
      throw new Error('gridSize must be a positive integer.');
    }

    const extentValue = payload?.extents ?? payload?.extent ?? 0.02;
    const extent = Number(extentValue);
    if (!Number.isFinite(extent) || extent <= 0) {
      throw new Error('extents must be a positive number.');
    }

    const seedValue = payload?.seed ?? 123;
    const seed = Number(seedValue);
    if (!Number.isFinite(seed)) {
      throw new Error('seed must be numeric.');
    }

    const outDir = path.join(artifactsRoot, 'graph_family', uuidv4());
    await fs.mkdir(outDir, { recursive: true });

    return cmdGraphFamily(env.executable, {
      families,
      axes,
      gridSize,
      extents: extent,
      seed: Math.trunc(seed),
      outDir,
      strategy: env.strategy,
    });
  }),
);

ipcMain.handle('cwt:phase5:inverse-design:command', (_event, payload: Record<string, unknown> | undefined) =>
  wrap(async () => {
    const env = ensurePythonEnvironment();

    const axesRaw = Array.isArray(payload?.axes) ? payload.axes : [];
    if (axesRaw.length !== 2) {
      throw new Error('axes must contain exactly two entries.');
    }
    const axes = axesRaw.map((axis: unknown) => String(axis ?? '').trim()) as [string, string];
    if (!axes[0] || !axes[1]) {
      throw new Error('axes entries must be non-empty strings.');
    }

    const centerRaw = Array.isArray(payload?.center) ? payload.center : [];
    if (centerRaw.length !== 2) {
      throw new Error('center must contain exactly two numeric entries.');
    }
    const center = centerRaw.map((value, index) => {
      const numeric = Number(value);
      if (!Number.isFinite(numeric)) {
        throw new Error(`center entry ${index + 1} must be numeric.`);
      }
      return numeric;
    }) as [number, number];

    const extentRaw = Array.isArray(payload?.extentPair) ? payload.extentPair : [];
    if (extentRaw.length !== 2) {
      throw new Error('extentPair must contain exactly two numeric entries.');
    }
    const extentPair = extentRaw.map((value, index) => {
      const numeric = Number(value);
      if (!Number.isFinite(numeric) || numeric === 0) {
        throw new Error(`extent entry ${index + 1} must be numeric.`);
      }
      return numeric;
    }) as [number, number];

    const budgetSteps = payload?.budgetSteps == null ? undefined : Number(payload.budgetSteps);
    if (budgetSteps != null && (!Number.isInteger(budgetSteps) || budgetSteps <= 0)) {
      throw new Error('budgetSteps must be a positive integer when provided.');
    }
    const maxFs = payload?.maxFs == null ? undefined : Number(payload.maxFs);
    if (maxFs != null && (!Number.isFinite(maxFs) || maxFs <= 0)) {
      throw new Error('maxFs must be a positive number when provided.');
    }
    const targetIndex = payload?.targetIndex == null ? undefined : Number(payload.targetIndex);
    if (targetIndex != null && !Number.isInteger(targetIndex)) {
      throw new Error('targetIndex must be an integer when provided.');
    }

    const outDir = path.join(artifactsRoot, 'inverse_design', uuidv4());
    await fs.mkdir(outDir, { recursive: true });

    return cmdInverseDesign(env.executable, {
      axes,
      center,
      extentPair,
      budgetSteps: budgetSteps == null ? undefined : Math.trunc(budgetSteps),
      maxFs: maxFs == null ? undefined : maxFs,
      targetIndex: targetIndex == null ? undefined : Math.trunc(targetIndex),
      outDir,
      strategy: env.strategy,
    });
  }),
);

ipcMain.handle('cwt:phase5:noise-robust:command', (_event, payload: Record<string, unknown> | undefined) =>
  wrap(async () => {
    const env = ensurePythonEnvironment();

    const toNumericArray = (value: unknown): number[] => {
      if (!Array.isArray(value)) {
        return [];
      }
      return (value as unknown[])
        .map((entry) => Number(entry))
        .filter((entry) => Number.isFinite(entry));
    };

    const phaseStd = toNumericArray(payload?.phaseStd ?? payload?.phase_std);
    const ampStd = toNumericArray(payload?.ampStd ?? payload?.amp_std);
    const delayStd = toNumericArray(payload?.delayStd ?? payload?.delay_std);

    const numTrials = payload?.numTrials == null ? undefined : Number(payload.numTrials);
    if (numTrials != null && (!Number.isInteger(numTrials) || numTrials <= 0)) {
      throw new Error('numTrials must be a positive integer when provided.');
    }
    const loopSteps = payload?.loopSteps == null ? undefined : Number(payload.loopSteps);
    if (loopSteps != null && (!Number.isInteger(loopSteps) || loopSteps <= 0)) {
      throw new Error('loopSteps must be a positive integer when provided.');
    }
    const gridSize = payload?.gridSize == null ? undefined : Number(payload.gridSize);
    if (gridSize != null && (!Number.isInteger(gridSize) || gridSize <= 0)) {
      throw new Error('gridSize must be a positive integer when provided.');
    }

    const axesRaw = Array.isArray(payload?.axes) ? payload.axes : undefined;
    const axes =
      axesRaw && axesRaw.length === 2
        ? (axesRaw.map((axis: unknown) => String(axis ?? '').trim()) as [string, string])
        : undefined;
    if (axes && (!axes[0] || !axes[1])) {
      throw new Error('axes entries must be non-empty strings.');
    }

    const outDir = path.join(artifactsRoot, 'noise_robust', uuidv4());
    await fs.mkdir(outDir, { recursive: true });

    return cmdGateCRobust(env.executable, {
      phaseStd,
      ampStd,
      delayStd,
      numTrials: numTrials == null ? undefined : Math.trunc(numTrials),
      loopSteps: loopSteps == null ? undefined : Math.trunc(loopSteps),
      gridSize: gridSize == null ? undefined : Math.trunc(gridSize),
      axes,
      outDir,
      strategy: env.strategy,
    });
  }),
);

ipcMain.handle('cwt:phase5:inverse-design', (_event, params) =>
  wrap(() =>
    launchPhase('experiments.inverse_design.run', params, {
      phase: 'phase5',
      experiment: 'inverse_design',
      label: 'Inverse design',
    }),
  ),
);

ipcMain.handle('cwt:phase5:noise-robust', (_event, params) =>
  wrap(() =>
    launchPhase('experiments.gateC_topology_robust.run', params, {
      phase: 'phase5',
      experiment: 'gateC_topology_robust',
      label: 'Noise robustness sweep',
    }),
  ),
);

ipcMain.handle('cwt:phase5:beta-sweep', (_event, params: { configPath: string; betas: number[] }) =>
  wrap(async () => {
    if (!params?.configPath || !Array.isArray(params.betas) || params.betas.length === 0) {
      throw new Error('configPath and betas are required');
    }

    const basePath = path.resolve(params.configPath);
    const baseContent = await fs.readFile(basePath, 'utf-8');
    const baseConfig = parseYaml(baseContent);
    if (typeof baseConfig !== 'object' || baseConfig === null) {
      throw new Error('config file must contain a YAML object');
    }

    ensurePythonEnvironment();
    const tempDir = await fs.mkdtemp(path.join(artifactsRoot, 'beta-sweep-'));
    const runs: Array<{ beta: number; runId: string; status: string }> = [];

    for (const betaValue of params.betas) {
      const beta = Number(betaValue);
      if (!Number.isFinite(beta)) {
        throw new Error('beta values must be numeric');
      }

      const mutated = JSON.parse(JSON.stringify(baseConfig)) as Record<string, unknown>;
      const existingCoupling =
        typeof mutated['geometric_coupling'] === 'object' && mutated['geometric_coupling'] !== null
          ? (mutated['geometric_coupling'] as Record<string, unknown>)
          : {};
      mutated['geometric_coupling'] = {
        ...existingCoupling,
        beta,
      };

      const configPath = path.join(tempDir, `beta_${beta}.yaml`);
      await fs.writeFile(configPath, stringifyYaml(mutated), 'utf-8');

      const { runId } = await runManager.createRun(
        'scripts.run_loop',
        ['--config', configPath],
        cwtSimRoot,
        {
          phase: 'phase5',
          experiment: 'beta_sweep',
          label: `β sweep (β=${beta})`,
        },
      );

      const completion = await runManager.waitForCompletion(runId);
      runs.push({ beta, runId, status: completion.status });
    }

    return { runs, tempDir };
  }),
);

ipcMain.handle('cwt:phase5:coupling-tuner', (_event, payload: Record<string, unknown> | undefined) =>
  wrap(async () => {
    const env = ensurePythonEnvironment();

    const configPathRaw = typeof payload?.configPath === 'string' ? payload.configPath.trim() : '';
    if (!configPathRaw) {
      throw new Error('configPath is required.');
    }

    const betasRaw = Array.isArray(payload?.betas) ? payload?.betas : [];
    const betas = betasRaw
      .map((value, index) => {
        const numeric = Number(value);
        if (!Number.isFinite(numeric)) {
          throw new Error(`beta entry ${index + 1} must be numeric.`);
        }
        return numeric;
      })
      .filter((value) => Number.isFinite(value));
    if (betas.length === 0) {
      throw new Error('At least one beta value is required.');
    }

    let etaQ: number | number[] | undefined;
    if (Array.isArray(payload?.etaQ)) {
      const values = (payload?.etaQ as unknown[])
        .map((value, index) => {
          const numeric = Number(value);
          if (!Number.isFinite(numeric)) {
            throw new Error(`etaQ entry ${index + 1} must be numeric.`);
          }
          return numeric;
        })
        .filter((value) => Number.isFinite(value));
      etaQ = values.length > 0 ? values : undefined;
    } else if (payload?.etaQ != null) {
      const numeric = Number(payload.etaQ);
      if (!Number.isFinite(numeric)) {
        throw new Error('etaQ must be numeric when provided.');
      }
      etaQ = numeric;
    }

    const outDir = path.join(artifactsRoot, 'coupling_tuner', uuidv4());
    await fs.mkdir(outDir, { recursive: true });

    return runCouplingTuner(env.executable, {
      configPath: configPathRaw,
      betas,
      etaQ,
      outDir,
      strategy: env.strategy,
    });
  }),
);


ipcMain.handle('cwt:phase2:browse-metrics-dirs', () =>
  wrap(
    async () => {
      const window = BrowserWindow.getFocusedWindow() ?? BrowserWindow.getAllWindows()[0];
      const { canceled, filePaths } = await dialog.showOpenDialog(window ?? undefined, {
        title: 'Select Phase-1 output directories',
        properties: ['openDirectory', 'multiSelections'],
        buttonLabel: 'Use directories',
      });

      return {
        canceled,
        directories: canceled ? [] : filePaths.map((entry) => path.resolve(entry)),
      } satisfies { canceled: boolean; directories: string[] };
    },
    { label: 'cwt:phase2:browse-metrics-dirs' },
  ),
);

ipcMain.handle(
  'cwt:phase2:correlate',
  (
    _event,
    payload?: {
      metricsDirs?: unknown[];
      thresholdMode?: 'absolute' | 'percentile';
      thresholdValue?: unknown;
      percentile?: unknown;
    },
  ) =>
    wrap(async () => {
      const dirs = Array.isArray(payload?.metricsDirs)
        ? (payload?.metricsDirs as unknown[])
            .map((entry) => (typeof entry === 'string' ? entry.trim() : ''))
            .filter((entry) => entry.length > 0)
        : [];

      if (dirs.length === 0) {
        throw new Error('metricsDirs is required');
      }

      const thresholdMode = payload?.thresholdMode === 'percentile' ? 'percentile' : 'absolute';

      const rawValue =
        thresholdMode === 'absolute' ? payload?.thresholdValue ?? 0 : payload?.percentile ?? 0;
      const numericValue = Number(rawValue);

      if (!Number.isFinite(numericValue)) {
        throw new Error(thresholdMode === 'absolute' ? 'thresholdValue must be numeric' : 'percentile must be numeric');
      }

      const uniqueDirs = Array.from(new Set(dirs.map((dir) => path.resolve(dir))));

      const result = correlatePhase2({
        metricsDirs: uniqueDirs,
        threshold: { mode: thresholdMode, value: numericValue },
      });

      return result;
    }),
);

ipcMain.handle('cwt:phase2:save-snapshot', (_event, payload?: unknown) =>
  wrap(async () => {
    if (!payload || typeof payload !== 'object') {
      throw new Error('payload is required');
    }

    const snapshotDir = path.join(artifactsRoot, '_ui');
    ensureDirSync(snapshotDir);

    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    const filePath = path.join(snapshotDir, `features_${timestamp}.json`);

    const snapshot = {
      savedAt: new Date().toISOString(),
      ...payload,
    };

    await fs.writeFile(filePath, JSON.stringify(snapshot, null, 2), 'utf-8');

    return { path: filePath };
  }),
);

ipcMain.handle('cwt:artifacts:list', (_event, payload: { under?: string }) =>
  wrap(async () => {
    const target = payload?.under ? path.resolve(payload.under) : artifactsRoot;
    if (!existsSync(target)) {
      return [];
    }
    return listDirectoryTree(target, target);
  }),
);

ipcMain.handle('cwt:artifacts:read-file', (_event, payload: { path?: string }) =>
  wrap(async () => {
    const target = payload?.path ? path.resolve(payload.path) : '';
    if (!target) {
      throw new Error('path is required');
    }
    if (!existsSync(target)) {
      throw new Error('File not found.');
    }
    const contents = await fs.readFile(target, 'utf-8');
    return { path: target, contents };
  }),
);

ipcMain.handle('cwt:registry:query', (_event, payload?: { phase?: string; experiment?: string; limit?: number }) =>
  wrap(() => runManager.fetchRegistry(payload ?? {})),
);

ipcMain.handle('cwt:recipes:list', () =>
  wrap(async () => {
    const recipes = await loadRecipes();
    recipes.sort((a, b) => b.createdAt.localeCompare(a.createdAt));
    return recipes;
  }),
);

ipcMain.handle('cwt:recipes:save', (_event, payload: unknown) =>
  wrap(async () => {
    const parsed = recipePayloadSchema.parse(payload ?? {});

    const recipes = await loadRecipes();
    const recipe: StoredRecipe = {
      id: uuidv4(),
      name: parsed.name,
      description: parsed.description ?? '',
      basedOnRunId: parsed.basedOnRunId ?? null,
      params: parsed.params ?? {},
      command: parsed.command,
      seed: parsed.seed ?? null,
      envInfo: parsed.envInfo ?? null,
      createdAt: new Date().toISOString(),
    };
    recipes.push(recipe);
    await saveRecipes(recipes);
    return recipe;
  }),
);

ipcMain.handle('cwt:recipes:run', (_event, payload: { id: string }) =>
  wrap(async () => {
    if (!payload?.id) {
      throw new Error('id is required');
    }

    const recipes = await loadRecipes();
    const recipe = recipes.find((item) => item.id === payload.id);
    if (!recipe) {
      throw new Error(`Recipe ${payload.id} not found`);
    }

    ensurePythonEnvironment();
    const args = buildArgsFromParams(recipe.params);
    return runManager.createRun(recipe.command, args, cwtSimRoot, {
      experiment: recipe.command,
      label: `Recipe: ${recipe.name}`,
    });
  }, { label: 'cwt:recipes:run' }),
);

ipcMain.handle('cwt:recipes:export', (_event, payload: { id: string }) =>
  wrap(async () => {
    if (!payload?.id) {
      throw new Error('id is required');
    }

    const recipes = await loadRecipes();
    const recipe = recipes.find((item) => item.id === payload.id);
    if (!recipe) {
      throw new Error(`Recipe ${payload.id} not found`);
    }

    return exportRecipeBundle(recipe);
  }),
);

ipcMain.handle('cwt:get-version', () => wrap(() => ({ version: '0.1.0' })));

ipcMain.handle('cwt:ping', (_event, payload: string) => wrap(() => ({ pong: payload })));
