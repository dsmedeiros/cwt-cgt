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
import type { GuidedLoopArgs, LoopAtHotspotPayload } from '../renderer/types/ipc';
import { runAdiabaticBoundary } from './adiabaticBoundary';
import { buildArgsFromParams } from './runner/args';

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
  wrap(() => {
    if (!params || typeof params !== 'object') {
      throw new Error('parameters are required for loop-at-hotspot');
    }

    const payload = params as LoopAtHotspotPayload & Record<string, unknown>;
    const hotspotsPath =
      typeof payload.hotspotsJson === 'string' ? payload.hotspotsJson.trim() : '';
    if (!hotspotsPath) {
      throw new Error('hotspotsJson must be a non-empty string path');
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
  wrap(() => runAdiabaticBoundary(runManager, cwtSimRoot, artifactsRoot, params as Record<string, unknown> | undefined)),
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
