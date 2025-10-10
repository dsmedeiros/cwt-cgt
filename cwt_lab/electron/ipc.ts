import { app, ipcMain, dialog, BrowserWindow } from 'electron';
import { spawn } from 'node:child_process';
import { promises as fs, existsSync, mkdirSync } from 'node:fs';
import path from 'node:path';
import type { FSWatcher } from 'chokidar';
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
import type { GuidedLoopArgs, GuidedLoopSummary, LoopAtHotspotPayload } from '../renderer/types/ipc';
import { runAdiabaticBoundary } from './adiabaticBoundary';
import { cmdGraphFamily } from './graphFamily';
import cmdInverseDesign from './inverseDesign';
import cmdGateCRobust from './noiseRobust';
import runCouplingTuner from './couplingTuner';
import { buildArgsFromParams } from './runner/args';
import { correlate as correlatePhase2 } from '../../electron/runner/phase2';
import { scanArtifacts, watchArtifacts, type ArtifactChangeEvent } from './runner/files';

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

type ArtifactsWatchPayload = {
  under?: string;
  depth?: number;
};

type ArtifactsUnwatchPayload = {
  id: number;
};

type ArtifactsWatcher = {
  watcher: FSWatcher;
  senderId: number;
  onDestroyed: () => void;
};

const artifactWatchers = new Map<number, ArtifactsWatcher>();
let nextArtifactsWatcherId = 1;

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

ipcMain.handle(
  'cwt:run:read-artifact',
  (
    _event,
    payload: { runId: string; relativePath: string; encoding?: 'utf-8' | 'base64' },
  ) =>
  wrap(async () => {
    if (!payload?.runId) {
      throw new Error('runId is required');
    }
    if (!payload?.relativePath || typeof payload.relativePath !== 'string') {
      throw new Error('relativePath is required');
    }
    const encoding = payload.encoding ?? 'utf-8';
    if (encoding !== 'utf-8' && encoding !== 'base64') {
      throw new Error('Unsupported encoding requested');
    }

    return runManager.readArtifact(payload.runId, payload.relativePath, encoding);
  }, { label: 'cwt:run:read-artifact' }),
);

const launchPhase = (
  module: string,
  params: Record<string, unknown> | undefined,
  metadata: RunMetadata,
  options: { artifactsDir?: string | null } = {},
) => {
  ensurePythonEnvironment();
  const args = buildArgsFromParams(params);
  return runManager.createRun(module, args, cwtSimRoot, metadata, options);
};

type GuidedSummaryRequest = {
  path: string;
  axes: [string, string];
  extents: [number, number];
  center: Record<string, number>;
  label: string;
  metadata: Record<string, unknown>;
  omegaAbs: number | null;
};

const sanitizeSummaryMetadata = (value: unknown): Record<string, unknown> => {
  if (!value || typeof value !== 'object') {
    return {};
  }

  const result: Record<string, unknown> = {};
  Object.entries(value as Record<string, unknown>).forEach(([rawKey, rawValue]) => {
    const key = typeof rawKey === 'string' ? rawKey.trim() : '';
    if (!key) {
      return;
    }
    if (
      rawValue === null ||
      typeof rawValue === 'string' ||
      typeof rawValue === 'number' ||
      typeof rawValue === 'boolean'
    ) {
      result[key] = rawValue;
    }
  });
  return result;
};

const parseGuidedSummaryRequest = (
  raw: unknown,
  fallback: {
    axes: [string, string];
    amplitudes: [number, number];
    center: [number, number];
    label: string;
  },
): GuidedSummaryRequest | null => {
  if (raw === undefined || raw === null) {
    return null;
  }
  if (typeof raw !== 'object') {
    throw new Error('summary must be an object when provided');
  }

  const record = raw as GuidedLoopSummary & Record<string, unknown>;
  const pathRaw = typeof record.path === 'string' ? record.path.trim() : '';
  if (!pathRaw) {
    throw new Error('summary.path must be a non-empty string');
  }

  const axesRaw = Array.isArray(record.axes) ? record.axes : fallback.axes;
  const axisA = String(axesRaw[0] ?? '').trim();
  const axisB = String(axesRaw[1] ?? '').trim();
  if (!axisA || !axisB) {
    throw new Error('summary.axes must contain two axis names');
  }

  const extentsRaw = Array.isArray(record.extents) ? record.extents : fallback.amplitudes;
  const extentA = Number(extentsRaw[0] ?? fallback.amplitudes[0]);
  const extentB = Number(extentsRaw[1] ?? fallback.amplitudes[1]);
  if (!Number.isFinite(extentA) || !Number.isFinite(extentB)) {
    throw new Error('summary.extents must contain numeric values');
  }

  const centerRaw = record.center;
  const center: Record<string, number> = {};
  if (centerRaw && typeof centerRaw === 'object') {
    Object.entries(centerRaw as Record<string, unknown>).forEach(([rawKey, rawValue]) => {
      const key = typeof rawKey === 'string' ? rawKey.trim() : '';
      if (!key) {
        return;
      }
      const numeric = Number(rawValue);
      if (Number.isFinite(numeric)) {
        center[key] = numeric;
      }
    });
  }
  if (Object.keys(center).length === 0) {
    center[axisA] = fallback.center[0];
    center[axisB] = fallback.center[1];
  }

  const labelRaw = typeof record.label === 'string' ? record.label.trim() : '';
  const label = labelRaw || fallback.label;

  const omegaCandidate = record.omegaAbs ?? record.omega_abs;
  const omegaNumeric = Number(omegaCandidate);
  const omegaAbs = Number.isFinite(omegaNumeric) ? omegaNumeric : null;

  const summaryPath = path.resolve(pathRaw);

  return {
    path: summaryPath,
    axes: [axisA, axisB],
    extents: [Math.abs(extentA), Math.abs(extentB)],
    center,
    label,
    metadata: sanitizeSummaryMetadata(record.metadata),
    omegaAbs,
  };
};

const pickMetricValue = (
  metrics: Record<string, number | null> | null | undefined,
  key: string,
): number | null => {
  if (!metrics) {
    return null;
  }

  const candidates = Array.from(
    new Set([
      key,
      key.replace(/_/g, '-'),
      key.replace(/-/g, '_'),
      key.toLowerCase(),
      key.toUpperCase(),
    ]),
  );

  for (const candidate of candidates) {
    if (candidate in metrics) {
      const rawValue = metrics[candidate];
      if (rawValue === null || rawValue === undefined) {
        return null;
      }
      const numeric = Number(rawValue);
      if (Number.isFinite(numeric)) {
        return numeric;
      }
    }
  }

  return null;
};

const guidedAxisLabels: Record<string, string> = {
  rho: 'ρ',
  tau: 'τ',
  zeta: 'ζ',
  zeta_phase: 'ζ_phase',
  kappa: 'κ',
};

const normalizeGuidedAxis = (value: string): keyof typeof guidedAxisLabels | null => {
  const normalized = value.trim().toLowerCase().replace(/[-\s]+/g, '_');
  switch (normalized) {
    case 'rho':
    case 'ρ':
      return 'rho';
    case 'tau':
    case 'τ':
      return 'tau';
    case 'zeta':
    case 'ζ':
      return 'zeta';
    case 'zeta_phase':
    case 'zeta-phase':
    case 'zetaphase':
    case 'ζ_phase':
    case 'ζφ':
      return 'zeta_phase';
    case 'kappa':
    case 'κ':
      return 'kappa';
    default:
      return null;
  }
};

const formatGuidedAxisLabel = (value: string): string => {
  const normalized = normalizeGuidedAxis(value);
  if (normalized) {
    return guidedAxisLabels[normalized];
  }
  return value;
};

const writeGuidedSummary = async (
  request: GuidedSummaryRequest,
  options: {
    graph: string;
    fsGuard: number | null;
    settle: number | null;
    seed: number | null;
    runs: Array<{
      runId: string;
      steps: number;
      status: string;
      metrics: Record<string, number | null> | null;
    }>;
    stepsList: number[];
    satisfied: boolean;
    minPhi: number | null;
  },
) => {
  const axisALabel = formatGuidedAxisLabel(request.axes[0]);
  const axisBLabel = formatGuidedAxisLabel(request.axes[1]);
  const timestamp = new Date().toISOString().replace(/\.\d{3}Z$/, 'Z');
  const finalRun = options.runs[options.runs.length - 1] ?? null;
  const finalMetrics = finalRun?.metrics ?? null;
  const extentEntry: Record<string, unknown> = {
    axes: request.axes,
    values: request.extents,
  };

  if (finalRun && finalMetrics) {
    const ccw: Record<string, unknown> = {};
    const fsP95 = pickMetricValue(finalMetrics, 'fs_p95');
    if (fsP95 !== null) {
      ccw.fs_p95 = fsP95;
    }
    const phi = pickMetricValue(finalMetrics, 'phi');
    if (phi !== null) {
      ccw.phi = phi;
    }
    const rValue = pickMetricValue(finalMetrics, 'R') ?? pickMetricValue(finalMetrics, 'r');
    if (rValue !== null) {
      ccw.R = rValue;
    }
    const overlap = pickMetricValue(finalMetrics, 'overlap_min');
    if (overlap !== null) {
      ccw.overlap_min = overlap;
    }
    const kappaDelta = pickMetricValue(finalMetrics, 'kappa1_delta');
    if (kappaDelta !== null) {
      ccw.kappa1_delta = kappaDelta;
    }
    if (Object.keys(ccw).length > 0) {
      ccw.steps = finalRun.steps;
      extentEntry.ccw = ccw;
    }
  }

  const metricsForFailure =
    finalMetrics ?? options.runs.find((run) => run.metrics)?.metrics ?? null;
  const failures: string[] = [];
  if (!options.satisfied) {
    const phi = pickMetricValue(metricsForFailure, 'phi');
    const fsP95 = pickMetricValue(metricsForFailure, 'fs_p95');
    const fsExceeded = pickMetricValue(metricsForFailure, 'fs_guard_exceeded');

    if (options.minPhi !== null && (phi === null || phi < options.minPhi)) {
      failures.push(
        `Guided loop φ=${
          phi === null ? 'n/a' : phi.toFixed(4)
        } did not reach minimum ${options.minPhi.toFixed(4)}. Try increasing ${axisALabel}/${axisBLabel} amplitudes, loosening the Φ threshold, or revisiting the selected ${axisALabel}/${axisBLabel} axes/extents per the troubleshooting guidance.`,
      );
    }
    if (
      options.fsGuard !== null &&
      ((fsP95 !== null && fsP95 > options.fsGuard) || (fsExceeded !== null && fsExceeded > 0))
    ) {
      failures.push(
        `Guided loop FS guard threshold ${options.fsGuard.toFixed(4)} was exceeded (p95=${
          fsP95 === null ? 'n/a' : fsP95.toFixed(4)
        }).`,
      );
    }
    if (failures.length === 0) {
      failures.push('Guided loop criteria were not satisfied.');
    }
  }

  const hotspotEntry: Record<string, unknown> = {
    label: request.label,
    center: request.center,
    extents: [extentEntry],
  };

  if (Object.keys(request.metadata).length > 0) {
    hotspotEntry.metadata = request.metadata;
  }
  if (request.omegaAbs !== null) {
    hotspotEntry.omega_abs = request.omegaAbs;
  }

  const payload: Record<string, unknown> = {
    schema_version: 1,
    created_at: timestamp,
    axes: request.axes,
    graph: options.graph,
    fs_guard: options.fsGuard,
    neighbor_settle_steps: options.settle,
    seed: options.seed,
    steps_list: options.stepsList,
    hotspots: [hotspotEntry],
    accepted: options.satisfied,
    failures,
    source: 'guided_loop',
  };

  if (options.minPhi !== null) {
    payload.min_phi = options.minPhi;
  }
  if (options.runs.length > 0) {
    payload.runs = options.runs.map((run) => ({
      run_id: run.runId,
      steps: run.steps,
      status: run.status,
      metrics: run.metrics,
    }));
  }

  await fs.mkdir(path.dirname(request.path), { recursive: true });
  await fs.writeFile(request.path, `${JSON.stringify(payload, null, 2)}\n`, 'utf-8');
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
    const experimentDirRaw =
      typeof passthrough.experimentDir === 'string' ? passthrough.experimentDir.trim() : '';
    delete passthrough.experimentDir;
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
      const summaryPathRaw = typeof payload.saveSummary === 'string' ? payload.saveSummary.trim() : '';
      if (!summaryPathRaw) {
        throw new Error('saveSummary must be a non-empty string path when provided');
      }
      passthrough.saveSummary = path.resolve(summaryPathRaw);
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

    const resolvedArtifactsDir = experimentDirRaw ? path.resolve(experimentDirRaw) : null;

    return launchPhase('experiments.loop_at_hotspot.run', runParams, {
      phase: 'phase3',
      experiment: 'loop_at_hotspot',
      label: 'Loop at hotspot',
    }, { artifactsDir: resolvedArtifactsDir });
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
      experimentDir: rawExperimentDir,
      summary: rawSummary,
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

    const centerValues = Array.isArray(rawCenter) ? rawCenter.map((value) => Number(value)) : [];
    if (centerValues.length !== 3 || centerValues.some((value) => !Number.isFinite(value))) {
      throw new Error('center must contain three numeric coordinates');
    }
    const center: [number, number, number] = [
      centerValues[0],
      centerValues[1],
      centerValues[2],
    ];

    const amplitudes = Array.isArray(rawAmplitudes)
      ? rawAmplitudes.map((value) => Number(value))
      : [];
    if (amplitudes.length !== 3 || amplitudes.some((value) => !Number.isFinite(value))) {
      throw new Error('amplitudes must contain three numeric values');
    }

    const summaryRequest = parseGuidedSummaryRequest(rawSummary, {
      axes: [axes3[1], axes3[2]],
      amplitudes: [amplitudes[1], amplitudes[2]],
      center: [center[1], center[2]],
      label: 'Guided hotspot',
    });

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

    const resolvedArtifactsDir =
      typeof rawExperimentDir === 'string' && rawExperimentDir.trim().length > 0
        ? path.resolve(rawExperimentDir.trim())
        : null;

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
        { artifactsDir: resolvedArtifactsDir },
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

      const phiCandidates: Array<number | null> = [
        typeof metrics.phi === 'number' ? Math.abs(metrics.phi) : null,
        typeof metrics.phi_flux === 'number' ? Math.abs(metrics.phi_flux) : null,
        typeof metrics.phi_value === 'number' ? Math.abs(metrics.phi_value) : null,
        typeof metrics.phi_forward === 'number' ? Math.abs(metrics.phi_forward) : null,
        typeof metrics.phiForward === 'number' ? Math.abs(metrics.phiForward) : null,
        typeof metrics.phi_reverse === 'number' ? Math.abs(metrics.phi_reverse) : null,
        typeof metrics.phiReverse === 'number' ? Math.abs(metrics.phiReverse) : null,
        typeof metrics.phi_sum === 'number' ? Math.abs(metrics.phi_sum) : null,
        typeof metrics.phiSum === 'number' ? Math.abs(metrics.phiSum) : null,
      ];
      const phiMag = phiCandidates
        .filter((value): value is number => value != null && Number.isFinite(value))
        .reduce((current, value) => Math.max(current, value), Number.NEGATIVE_INFINITY);
      const phiCriterion = minPhi === null || (Number.isFinite(phiMag) && phiMag >= minPhi);
      const fsExceeded = metrics.fs_guard_exceeded ?? null;
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

    if (summaryRequest && runs.length > 0) {
      await writeGuidedSummary(summaryRequest, {
        graph,
        fsGuard,
        settle,
        seed,
        runs,
        stepsList,
        satisfied,
        minPhi,
      });
    }

    return { runs, satisfied };
  }),
);

ipcMain.handle('cwt:phase3:adiabatic-boundary', (_event, payload) =>
  wrap(() => {
    if (!payload || typeof payload !== 'object') {
      throw new Error('parameters are required for adiabatic-boundary');
    }

    const { outDir: rawOutDir, experimentDir: rawExperimentDir, ...rest } =
      payload as { outDir?: unknown; experimentDir?: unknown } & Record<string, unknown>;

    const experimentDirRaw = typeof rawExperimentDir === 'string' ? rawExperimentDir.trim() : '';
    const resolvedExperimentDir = experimentDirRaw ? path.resolve(experimentDirRaw) : null;

    let outDir = typeof rawOutDir === 'string' ? rawOutDir.trim() : '';
    if (!outDir) {
      const root = resolvedExperimentDir ?? artifactsRoot;
      const segments = resolvedExperimentDir ? ['phase3', 'adiabatic_boundary'] : ['adiabatic_boundary'];
      outDir = path.join(root, ...segments, uuidv4());
    }

    const runParams: Record<string, unknown> = {
      ...rest,
      outputDir: outDir,
    };

    return launchPhase(
      'experiments.adiabatic_boundary.run',
      runParams,
      {
        phase: 'phase3',
        experiment: 'adiabatic_boundary',
        label: 'Adiabatic boundary sweep',
      },
      { artifactsDir: resolvedExperimentDir },
    );
  }),
);

ipcMain.handle('cwt:phase3:adiabatic-boundary:analyze', (_event, params) =>
  wrap(() => {
    ensurePythonEnvironment();
    const rawParams = (params ?? {}) as Record<string, unknown>;
    const sanitizedParams = { ...rawParams };
    const experimentDirRaw =
      typeof rawParams.experimentDir === 'string' ? rawParams.experimentDir.trim() : '';
    let resolvedExperimentDir: string | null = null;
    if (experimentDirRaw) {
      resolvedExperimentDir = path.resolve(experimentDirRaw);
      delete sanitizedParams.experimentDir;
    }

    return runAdiabaticBoundary(runManager, cwtSimRoot, artifactsRoot, sanitizedParams, {
      experimentDir: resolvedExperimentDir,
    });
  }),
);

ipcMain.handle('cwt:phase4:wilson3d', (_event, params) =>
  wrap(() => {
    const rawParams = (params ?? {}) as Record<string, unknown>;
    const sanitizedParams = { ...rawParams };
    const experimentDirRaw =
      typeof rawParams.experimentDir === 'string' ? rawParams.experimentDir.trim() : '';
    if (experimentDirRaw) {
      delete sanitizedParams.experimentDir;
    }
    const resolvedArtifactsDir = experimentDirRaw ? path.resolve(experimentDirRaw) : null;

    return launchPhase(
      'experiments.wilson_loop_3d.run',
      sanitizedParams,
      {
        phase: 'phase4',
        experiment: 'wilson_loop_3d',
        label: 'Wilson loop 3D sweep',
      },
      { artifactsDir: resolvedArtifactsDir },
    );
  }),
);

ipcMain.handle('cwt:phase4:torus-plateau', (_event, params) =>
  wrap(() => {
    const rawParams = (params ?? {}) as Record<string, unknown>;
    const sanitizedParams = { ...rawParams };
    const experimentDirRaw =
      typeof rawParams.experimentDir === 'string' ? rawParams.experimentDir.trim() : '';
    if (experimentDirRaw) {
      delete sanitizedParams.experimentDir;
    }
    const resolvedArtifactsDir = experimentDirRaw ? path.resolve(experimentDirRaw) : null;

    return launchPhase(
      'experiments.torus_plateau.run',
      sanitizedParams,
      {
        phase: 'phase4',
        experiment: 'torus_plateau',
        label: 'Torus plateau survey',
      },
      { artifactsDir: resolvedArtifactsDir },
    );
  }),
);

ipcMain.handle('cwt:phase5:graph-family', (_event, params) =>
  wrap(() => {
    const rawParams = (params ?? {}) as Record<string, unknown>;
    const sanitizedParams = { ...rawParams };
    const experimentDirRaw =
      typeof rawParams.experimentDir === 'string' ? rawParams.experimentDir.trim() : '';
    if (experimentDirRaw) {
      delete sanitizedParams.experimentDir;
    }
    const resolvedArtifactsDir = experimentDirRaw ? path.resolve(experimentDirRaw) : null;

    return launchPhase(
      'experiments.graph_family.run',
      sanitizedParams,
      {
        phase: 'phase5',
        experiment: 'graph_family',
        label: 'Graph family sweep',
      },
      { artifactsDir: resolvedArtifactsDir },
    );
  }),
);

ipcMain.handle('cwt:phase5:graph-family:analyze', (_event, payload) =>
  wrap(async () => {
    const env = ensurePythonEnvironment();

    const experimentDirRaw =
      typeof payload?.experimentDir === 'string' ? payload.experimentDir.trim() : '';
    const resolvedExperimentDir = experimentDirRaw ? path.resolve(experimentDirRaw) : null;

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

    const root = resolvedExperimentDir ?? artifactsRoot;
    const segments = resolvedExperimentDir
      ? ['phase5', 'graph_family', uuidv4()]
      : ['graph_family', uuidv4()];
    const outDir = path.join(root, ...segments);
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

    const experimentDirRaw =
      typeof payload?.experimentDir === 'string' ? payload.experimentDir.trim() : '';
    const resolvedExperimentDir = experimentDirRaw ? path.resolve(experimentDirRaw) : null;

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

    const root = resolvedExperimentDir ?? artifactsRoot;
    const segments = resolvedExperimentDir
      ? ['phase5', 'inverse_design', uuidv4()]
      : ['inverse_design', uuidv4()];
    const outDir = path.join(root, ...segments);
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

    const experimentDirRaw =
      typeof payload?.experimentDir === 'string' ? payload.experimentDir.trim() : '';
    const resolvedExperimentDir = experimentDirRaw ? path.resolve(experimentDirRaw) : null;

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

    const root = resolvedExperimentDir ?? artifactsRoot;
    const segments = resolvedExperimentDir
      ? ['phase5', 'noise_robust', uuidv4()]
      : ['noise_robust', uuidv4()];
    const outDir = path.join(root, ...segments);
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
  wrap(() => {
    const rawParams = (params ?? {}) as Record<string, unknown>;
    const sanitizedParams = { ...rawParams };
    const experimentDirRaw =
      typeof rawParams.experimentDir === 'string' ? rawParams.experimentDir.trim() : '';
    if (experimentDirRaw) {
      delete sanitizedParams.experimentDir;
    }
    const resolvedArtifactsDir = experimentDirRaw ? path.resolve(experimentDirRaw) : null;

    return launchPhase(
      'experiments.inverse_design.run',
      sanitizedParams,
      {
        phase: 'phase5',
        experiment: 'inverse_design',
        label: 'Inverse design',
      },
      { artifactsDir: resolvedArtifactsDir },
    );
  }),
);

ipcMain.handle('cwt:phase5:noise-robust', (_event, params) =>
  wrap(() => {
    const rawParams = (params ?? {}) as Record<string, unknown>;
    const sanitizedParams = { ...rawParams };
    const experimentDirRaw =
      typeof rawParams.experimentDir === 'string' ? rawParams.experimentDir.trim() : '';
    if (experimentDirRaw) {
      delete sanitizedParams.experimentDir;
    }
    const resolvedArtifactsDir = experimentDirRaw ? path.resolve(experimentDirRaw) : null;

    return launchPhase(
      'experiments.gateC_topology_robust.run',
      sanitizedParams,
      {
        phase: 'phase5',
        experiment: 'gateC_topology_robust',
        label: 'Noise robustness sweep',
      },
      { artifactsDir: resolvedArtifactsDir },
    );
  }),
);

ipcMain.handle('cwt:phase5:beta-sweep', (_event, params) =>
  wrap(async () => {
    const payload = (params ?? {}) as Record<string, unknown>;

    const configPathRaw = typeof payload.configPath === 'string' ? payload.configPath.trim() : '';
    if (!configPathRaw) {
      throw new Error('configPath is required for β sweep runs.');
    }

    const betasRaw = Array.isArray(payload.betas) ? payload.betas : [];
    const betas = betasRaw.map((value, index) => {
      const numeric = Number(value);
      if (!Number.isFinite(numeric)) {
        throw new Error(`beta entry ${index + 1} must be numeric.`);
      }
      return numeric;
    });
    if (betas.length === 0) {
      throw new Error('At least one beta value is required.');
    }

    const experimentDirRaw =
      typeof payload.experimentDir === 'string' ? payload.experimentDir.trim() : '';
    const resolvedExperimentDir = experimentDirRaw ? path.resolve(experimentDirRaw) : null;

    const basePath = path.resolve(configPathRaw);
    const baseContent = await fs.readFile(basePath, 'utf-8');
    const baseConfig = parseYaml(baseContent);
    if (typeof baseConfig !== 'object' || baseConfig === null) {
      throw new Error('config file must contain a YAML object');
    }

    ensurePythonEnvironment();

    const root = resolvedExperimentDir ?? artifactsRoot;
    const segments = resolvedExperimentDir
      ? ['phase5', 'beta_sweep', uuidv4()]
      : ['beta_sweep', uuidv4()];
    const stagingDir = path.join(root, ...segments);
    await fs.mkdir(stagingDir, { recursive: true });

    const runs: Array<{ beta: number; runId: string; status: string }> = [];

    for (const beta of betas) {
      const mutated = JSON.parse(JSON.stringify(baseConfig)) as Record<string, unknown>;
      const existingCoupling =
        typeof mutated['geometric_coupling'] === 'object' && mutated['geometric_coupling'] !== null
          ? (mutated['geometric_coupling'] as Record<string, unknown>)
          : {};
      mutated['geometric_coupling'] = {
        ...existingCoupling,
        beta,
      };

      const configPath = path.join(stagingDir, `beta_${beta}.yaml`);
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
        resolvedExperimentDir ? { artifactsDir: resolvedExperimentDir } : undefined,
      );

      const completion = await runManager.waitForCompletion(runId);
      runs.push({ beta, runId, status: completion.status });
    }

    return { runs, tempDir: stagingDir, stagingDir };
  }),
);

ipcMain.handle('cwt:phase5:coupling-tuner', (_event, payload: Record<string, unknown> | undefined) =>
  wrap(async () => {
    const env = ensurePythonEnvironment();

    const experimentDirRaw =
      typeof payload?.experimentDir === 'string' ? payload.experimentDir.trim() : '';
    const resolvedExperimentDir = experimentDirRaw ? path.resolve(experimentDirRaw) : null;

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

    const root = resolvedExperimentDir ?? artifactsRoot;
    const segments = resolvedExperimentDir
      ? ['phase5', 'coupling_tuner', uuidv4()]
      : ['coupling_tuner', uuidv4()];
    const outDir = path.join(root, ...segments);
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

ipcMain.handle('cwt:artifacts:watch', (event, payload: ArtifactsWatchPayload) =>
  wrap(async () => {
    const target = payload?.under ? path.resolve(payload.under) : artifactsRoot;
    const depthRaw = payload?.depth;
    const depth = typeof depthRaw === 'number' && depthRaw >= 0 ? depthRaw : undefined;

    const id = nextArtifactsWatcherId++;
    const sender = event.sender;
    let closed = false;
    let watcher: FSWatcher | null = null;

    const closeWatcher = async () => {
      if (closed) {
        return;
      }
      closed = true;
      const entry = artifactWatchers.get(id);
      if (entry) {
        artifactWatchers.delete(id);
        sender.removeListener('destroyed', entry.onDestroyed);
      }
      try {
        if (watcher) {
          await watcher.close();
        }
      } catch (error) {
        console.warn('Failed to close artifacts watcher:', error);
      }
    };

    watcher = watchArtifacts(
      target,
      (change: ArtifactChangeEvent) => {
        if (sender.isDestroyed()) {
          void closeWatcher();
          return;
        }
        sender.send('cwt:artifacts:changed', { id, ...change });
      },
      { depth },
    );

    const onDestroyed = () => {
      void closeWatcher();
    };

    sender.once('destroyed', onDestroyed);
    artifactWatchers.set(id, { watcher, senderId: sender.id, onDestroyed });

    return { id };
  }, { label: 'cwt:artifacts:watch' }),
);

ipcMain.handle('cwt:artifacts:unwatch', (event, payload: ArtifactsUnwatchPayload) =>
  wrap(async () => {
    const idRaw = payload?.id;
    const id = typeof idRaw === 'number' ? idRaw : Number(idRaw);
    if (!Number.isInteger(id)) {
      throw new Error('id is required');
    }

    const entry = artifactWatchers.get(id);
    if (!entry) {
      return { id };
    }

    if (entry.senderId !== event.sender.id) {
      throw new Error('Cannot unwatch artifacts created by another renderer process.');
    }

    artifactWatchers.delete(id);
    event.sender.removeListener('destroyed', entry.onDestroyed);
    try {
      await entry.watcher.close();
    } catch (error) {
      console.warn('Failed to close artifacts watcher:', error);
    }

    return { id };
  }, { label: 'cwt:artifacts:unwatch' }),
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

ipcMain.handle('cwt:recipes:run', (_event, payload: { id: string; experimentDir?: string }) =>
  wrap(async () => {
    if (!payload?.id) {
      throw new Error('id is required');
    }

    const experimentDirRaw =
      typeof payload.experimentDir === 'string' ? payload.experimentDir.trim() : '';
    const resolvedArtifactsDir = experimentDirRaw ? path.resolve(experimentDirRaw) : null;

    const recipes = await loadRecipes();
    const recipe = recipes.find((item) => item.id === payload.id);
    if (!recipe) {
      throw new Error(`Recipe ${payload.id} not found`);
    }

    ensurePythonEnvironment();
    const args = buildArgsFromParams(recipe.params);
    return runManager.createRun(
      recipe.command,
      args,
      cwtSimRoot,
      {
        experiment: recipe.command,
        label: `Recipe: ${recipe.name}`,
      },
      { artifactsDir: resolvedArtifactsDir },
    );
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
