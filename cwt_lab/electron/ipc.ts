import { ipcMain } from 'electron';
import { promises as fs, existsSync, mkdirSync } from 'node:fs';
import path from 'node:path';
import { parse as parseYaml, stringify as stringifyYaml } from 'yaml';
import { v4 as uuidv4 } from 'uuid';
import { z } from 'zod';

import {
  detectPython,
  getEnvironmentConfig,
  setPythonPath,
  type PythonCandidate,
} from './runner/env';
import { RunManager, type RunMetadata } from './runner/runManager';

type Envelope<T> = { ok: true; data: T } | { ok: false; error: string; data?: T };

const repoRoot = path.resolve(__dirname, '..', '..');
const cwtSimRoot = path.join(repoRoot, 'cwt-sim');
const artifactsRoot = path.join(repoRoot, 'artifacts');
const registryPath = path.join(artifactsRoot, 'registry.sqlite');
const recipesPath = path.join(artifactsRoot, 'recipes.json');

const ensureDirSync = (dir: string) => {
  if (!existsSync(dir)) {
    mkdirSync(dir, { recursive: true });
  }
};

ensureDirSync(artifactsRoot);
ensureDirSync(path.dirname(registryPath));

const runManager = new RunManager({
  repoRoot,
  artifactsRoot,
  registryPath,
  pythonPathEntries: [cwtSimRoot],
});

const recipePayloadSchema = z.object({
  name: z.string().min(1, 'name is required'),
  params: z.record(z.string(), z.unknown()).optional().default({}),
  command: z.string().min(1, 'command is required'),
  seed: z.number().optional(),
  envInfo: z.unknown().optional(),
});

const wrap = async <T>(fn: () => Promise<T> | T): Promise<Envelope<T>> => {
  try {
    const data = await fn();
    return { ok: true as const, data };
  } catch (error) {
    return { ok: false as const, error: error instanceof Error ? error.message : String(error) };
  }
};

const buildArgsFromParams = (params: Record<string, unknown> | undefined): string[] => {
  if (!params) {
    return [];
  }

  const args: string[] = [];
  const toKebab = (key: string) =>
    key
      .replace(/([a-z0-9])([A-Z])/g, '$1-$2')
      .replace(/_/g, '-')
      .toLowerCase();

  for (const [rawKey, value] of Object.entries(params)) {
    if (value === undefined || value === null) {
      continue;
    }

    const flag = `--${toKebab(rawKey)}`;
    if (Array.isArray(value)) {
      const serialized = value.map((item) =>
        typeof item === 'object' && item !== null ? JSON.stringify(item) : String(item),
      );
      args.push(flag, ...serialized);
    } else if (typeof value === 'boolean') {
      const isNegatedFlag = /^no[A-Z_]/i.test(rawKey);
      if (isNegatedFlag) {
        if (value) {
          args.push(flag);
        }
      } else {
        args.push(flag, value ? 'true' : 'false');
      }
    } else if (typeof value === 'object') {
      args.push(flag, JSON.stringify(value));
    } else {
      args.push(flag, String(value));
    }
  }

  return args;
};

const loadRecipes = async (): Promise<any[]> => {
  if (!existsSync(recipesPath)) {
    return [];
  }

  const content = await fs.readFile(recipesPath, 'utf-8');
  try {
    const parsed = JSON.parse(content);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
};

const saveRecipes = async (recipes: any[]) => {
  await fs.writeFile(recipesPath, JSON.stringify(recipes, null, 2), 'utf-8');
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

ipcMain.handle('cwt:env:get-config', () => wrap(() => getEnvironmentConfig()));

ipcMain.handle('cwt:run:create', (_event, payload: { experiment: string; args?: Record<string, unknown>; workdir?: string }) =>
  wrap(async () => {
    if (!payload?.experiment) {
      throw new Error('experiment is required');
    }

    const args = buildArgsFromParams(payload.args);
    const cwd = payload.workdir ? path.resolve(payload.workdir) : cwtSimRoot;
    return runManager.createRun(payload.experiment, args, cwd, {
      experiment: payload.experiment,
    });
  }),
);

ipcMain.handle('cwt:run:abort', (_event, payload: { runId: string }) =>
  wrap(async () => {
    if (!payload?.runId) {
      throw new Error('runId is required');
    }
    await runManager.abort(payload.runId);
    return { runId: payload.runId };
  }),
);

ipcMain.handle('cwt:run:tail', (_event, payload: { runId: string; fromByte?: number }) =>
  wrap(async () => {
    if (!payload?.runId) {
      throw new Error('runId is required');
    }

    return runManager.tail(payload.runId, payload.fromByte ?? 0);
  }),
);

ipcMain.handle('cwt:run:open-artifacts', (_event, payload: { runId: string }) =>
  wrap(async () => {
    if (!payload?.runId) {
      throw new Error('runId is required');
    }

    return runManager.listArtifacts(payload.runId);
  }),
);

const launchPhase = (
  module: string,
  params: Record<string, unknown> | undefined,
  metadata: RunMetadata,
) => {
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

ipcMain.handle('cwt:phase3:loop-at-hotspot', (_event, params) =>
  wrap(() =>
    launchPhase('experiments.loop_at_hotspot.run', params, {
      phase: 'phase3',
      experiment: 'loop_at_hotspot',
      label: 'Loop at hotspot',
    }),
  ),
);

ipcMain.handle('cwt:phase3:guided-loop', (_event, params) =>
  wrap(async () => {
    const payload = params as Record<string, unknown> | undefined;
    if (!payload) {
      throw new Error('parameters are required for guided mode');
    }

    const { stepsList: rawSteps, minPhi: rawMinPhi, ...phaseParams } = payload as Record<string, unknown> & {
      stepsList?: unknown;
      minPhi?: unknown;
    };

    const stepsList = Array.isArray(rawSteps)
      ? rawSteps.map((value) => Number.parseInt(String(value), 10)).filter((value) => !Number.isNaN(value))
      : [];
    if (stepsList.length === 0) {
      throw new Error('stepsList must contain at least one integer value');
    }

    const minPhiRaw = rawMinPhi !== undefined ? Number(rawMinPhi) : null;
    const minPhi = Number.isFinite(minPhiRaw) ? minPhiRaw : null;
    const fsGuardRaw = phaseParams.fsGuard !== undefined ? Number(phaseParams.fsGuard) : null;
    const fsGuard = Number.isFinite(fsGuardRaw) ? fsGuardRaw : null;

    const runs: Array<{
      runId: string;
      steps: number;
      status: string;
      metrics: Record<string, number | null> | null;
    }> = [];
    let satisfied = false;

    for (const steps of stepsList) {
      const runParams = {
        ...phaseParams,
        steps,
      } as Record<string, unknown>;

      const { runId } = await runManager.createRun(
        'experiments.wilson_loop_3d.run',
        buildArgsFromParams(runParams),
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
        fsGuard === null || metrics.fs_p95 === undefined || metrics.fs_p95 === null || metrics.fs_p95 <= fsGuard;

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

const computePearson = (x: number[], y: number[]): number | null => {
  if (x.length !== y.length || x.length === 0) {
    return null;
  }

  const n = x.length;
  const meanX = x.reduce((acc, value) => acc + value, 0) / n;
  const meanY = y.reduce((acc, value) => acc + value, 0) / n;

  let numerator = 0;
  let denomX = 0;
  let denomY = 0;

  for (let i = 0; i < n; i += 1) {
    const dx = x[i] - meanX;
    const dy = y[i] - meanY;
    numerator += dx * dy;
    denomX += dx * dx;
    denomY += dy * dy;
  }

  const denominator = Math.sqrt(denomX * denomY);
  if (denominator === 0) {
    return null;
  }

  return numerator / denominator;
};

const computeAuc = (scores: number[], labels: number[]): number | null => {
  if (scores.length !== labels.length || scores.length === 0) {
    return null;
  }

  const paired = scores.map((score, index) => ({ score, label: labels[index] }));
  paired.sort((a, b) => b.score - a.score);

  let tp = 0;
  let fp = 0;
  let prevScore: number | null = null;
  const positives = labels.filter((label) => label > 0).length;
  const negatives = labels.length - positives;

  if (positives === 0 || negatives === 0) {
    return null;
  }

  let auc = 0;
  let lastTpRate = 0;
  let lastFpRate = 0;

  for (const { score, label } of paired) {
    if (prevScore !== null && score !== prevScore) {
      const tpRate = tp / positives;
      const fpRate = fp / negatives;
      auc += (fpRate - lastFpRate) * (tpRate + lastTpRate) * 0.5;
      lastTpRate = tpRate;
      lastFpRate = fpRate;
    }

    if (label > 0) {
      tp += 1;
    } else {
      fp += 1;
    }
    prevScore = score;
  }

  const finalTpRate = tp / positives;
  const finalFpRate = fp / negatives;
  auc += (finalFpRate - lastFpRate) * (finalTpRate + lastTpRate) * 0.5;
  return auc;
};

const parseMetricsFile = async (filePath: string): Promise<Record<string, number>[]> => {
  const ext = path.extname(filePath).toLowerCase();
  const content = await fs.readFile(filePath, 'utf-8');

  if (ext === '.json') {
    try {
      const parsed = JSON.parse(content);
      if (Array.isArray(parsed)) {
        return parsed.map((item) => flattenNumericFields(item));
      }
      return [flattenNumericFields(parsed)];
    } catch (error) {
      console.warn(`Failed to parse JSON metrics at ${filePath}:`, error);
      return [];
    }
  }

  if (ext === '.csv') {
    const rows = content
      .trim()
      .split(/\r?\n/)
      .filter((line) => line.length > 0);
    if (rows.length === 0) {
      return [];
    }

    const headers = rows[0].split(',').map((header) => header.trim());
    const records: Record<string, number>[] = [];

    for (let i = 1; i < rows.length; i += 1) {
      const values = rows[i].split(',');
      const record: Record<string, number> = {};
      headers.forEach((header, index) => {
        const value = Number.parseFloat(values[index]);
        if (!Number.isNaN(value)) {
          record[header] = value;
        }
      });
      records.push(record);
    }
    return records;
  }

  return [];
};

const flattenNumericFields = (value: unknown, prefix = ''): Record<string, number> => {
  if (value === null || value === undefined) {
    return {};
  }

  if (typeof value === 'number' && Number.isFinite(value)) {
    return { [prefix || 'value']: value };
  }

  if (typeof value !== 'object') {
    return {};
  }

  const entries: Record<string, number> = {};
  for (const [key, nested] of Object.entries(value as Record<string, unknown>)) {
    const pathKey = prefix ? `${prefix}.${key}` : key;
    Object.assign(entries, flattenNumericFields(nested, pathKey));
  }
  return entries;
};

ipcMain.handle(
  'cwt:phase2:correlate',
  (
    _event,
    payload: {
      metricsDirs: string[];
      thresholdMode?: 'absolute' | 'percentile';
      thresholdValue?: number;
      percentile?: number;
    },
  ) =>
    wrap(async () => {
      if (!payload?.metricsDirs || payload.metricsDirs.length === 0) {
        throw new Error('metricsDirs is required');
      }

      const dataset: Record<string, number>[] = [];

      for (const dir of payload.metricsDirs) {
        const absoluteDir = path.resolve(dir);
        if (!existsSync(absoluteDir)) {
          continue;
        }

        const files = await fs.readdir(absoluteDir);
        for (const file of files) {
          const filePath = path.join(absoluteDir, file);
          const stats = await parseMetricsFile(filePath);
          dataset.push(...stats);
        }
      }

      if (dataset.length === 0) {
        return { correlations: [], aucs: [] };
      }

      const metricKeys = Array.from(
        dataset.reduce((set, record) => {
          Object.keys(record).forEach((key) => set.add(key));
          return set;
        }, new Set<string>()),
      );

      const matrix: Array<{ metric: string; correlations: Record<string, number | null> }> = [];
      const labelKey = metricKeys.find((key) => key.toLowerCase().includes('label'));
      let labels = labelKey ? dataset.map((record) => record[labelKey] ?? 0) : [];

      let appliedThreshold: number | null = null;
      if (labelKey && payload.thresholdMode === 'absolute' && typeof payload.thresholdValue === 'number') {
        appliedThreshold = payload.thresholdValue;
        labels = dataset.map((record) => (record[labelKey] ?? 0) >= appliedThreshold! ? 1 : 0);
      } else if (labelKey && payload.thresholdMode === 'percentile' && typeof payload.percentile === 'number') {
        const sorted = [...labels].sort((a, b) => a - b);
        if (sorted.length > 0) {
          const rank = Math.min(
            sorted.length - 1,
            Math.max(0, Math.round((payload.percentile / 100) * (sorted.length - 1))),
          );
          appliedThreshold = sorted[rank] ?? null;
          labels = dataset.map((record) => (record[labelKey] ?? 0) >= (appliedThreshold ?? 0) ? 1 : 0);
        }
      }

      for (const metric of metricKeys) {
        const values = dataset.map((record) => record[metric] ?? 0);
        const correlations: Record<string, number | null> = {};
        for (const other of metricKeys) {
          const otherValues = dataset.map((record) => record[other] ?? 0);
          correlations[other] = computePearson(values, otherValues);
        }
        matrix.push({ metric, correlations });
      }

      const aucs = labelKey
        ? metricKeys
            .filter((metric) => metric !== labelKey)
            .map((metric) => ({
              metric,
              auc: computeAuc(
                dataset.map((record) => record[metric] ?? 0),
                labels.map((value) => (value >= 0.5 ? 1 : 0)),
              ),
            }))
        : [];

      return { correlations: matrix, aucs, labelKey: labelKey ?? null, threshold: appliedThreshold };
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

ipcMain.handle('cwt:registry:query', (_event, payload?: { phase?: string; experiment?: string; limit?: number }) =>
  wrap(() => runManager.fetchRegistry(payload ?? {})),
);

ipcMain.handle('cwt:recipes:list', () => wrap(async () => loadRecipes()));

ipcMain.handle('cwt:recipes:save', (_event, payload: unknown) =>
  wrap(async () => {
    const parsed = recipePayloadSchema.parse(payload ?? {});

    const recipes = await loadRecipes();
    const recipe = {
      id: uuidv4(),
      ...parsed,
      createdAt: Date.now(),
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

    const args = buildArgsFromParams(recipe.params);
    return runManager.createRun(recipe.command, args, cwtSimRoot, {
      experiment: recipe.command,
      label: `Recipe: ${recipe.name}`,
    });
  }),
);

ipcMain.handle('cwt:get-version', () => wrap(() => ({ version: '0.1.0' })));

ipcMain.handle('cwt:ping', (_event, payload: string) => wrap(() => ({ pong: payload })));
