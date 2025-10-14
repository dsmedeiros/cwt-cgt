import { spawn, type ChildProcessWithoutNullStreams } from 'node:child_process';
import { promises as fs } from 'node:fs';
import path from 'node:path';

import { v4 as uuidv4 } from 'uuid';
import { z } from 'zod';

import { cmdBaseline, type BaselineCommandOptions, type BaselineModel } from '../baselines';
import type { PythonEnvironment } from '../runner/env';

const optionalPathSchema = z
  .union([z.string(), z.null(), z.undefined()])
  .transform((value) => {
    if (typeof value !== 'string') {
      return null;
    }
    const trimmed = value.trim();
    return trimmed.length > 0 ? trimmed : null;
  });

const optionalNumericSchema = z
  .union([z.string(), z.number(), z.null(), z.undefined()])
  .transform((value) => {
    if (value == null) {
      return null;
    }
    if (typeof value === 'number') {
      return Number.isFinite(value) ? value : null;
    }
    const trimmed = value.trim();
    return trimmed.length > 0 ? trimmed : null;
  });

const argsSchema = z
  .union([z.array(z.union([z.string(), z.number()])), z.null(), z.undefined()])
  .transform((value) => {
    if (!value) {
      return null;
    }
    return value.map((entry) => (typeof entry === 'number' ? entry : entry));
  });

const envSchema = z
  .union([z.record(z.union([z.string(), z.number(), z.boolean(), z.null()])), z.undefined(), z.null()])
  .transform((value) => {
    if (!value) {
      return null;
    }
    const entries: Record<string, string> = {};
    for (const [key, rawValue] of Object.entries(value)) {
      if (rawValue === null || rawValue === undefined) {
        continue;
      }
      const normalizedKey = key.trim();
      if (!normalizedKey) {
        continue;
      }
      entries[normalizedKey] = String(rawValue);
    }
    return Object.keys(entries).length > 0 ? entries : null;
  });

export const baselineRunPayloadSchema = z
  .object({
    model: z.enum(['ising', 'kuramoto', 'percolation', 'sis']),
    axisMap: optionalPathSchema,
    outputDir: optionalPathSchema,
    steps: optionalNumericSchema,
    seed: optionalNumericSchema,
    args: argsSchema,
    env: envSchema,
  })
  .transform((value) => ({
    model: value.model as BaselineModel,
    axisMap: value.axisMap,
    outputDir: value.outputDir,
    steps: value.steps,
    seed: value.seed,
    args: value.args,
    env: value.env,
  }));

export type BaselineRunPayload = z.infer<typeof baselineRunPayloadSchema>;

type RunDirsReader = (root: string) => Promise<Set<string>>;

const readRunDirectories: RunDirsReader = async (root) => {
  try {
    const entries = await fs.readdir(root, { withFileTypes: true });
    return new Set(entries.filter((entry) => entry.isDirectory()).map((entry) => entry.name));
  } catch (error) {
    const message = (error as NodeJS.ErrnoException).code;
    if (message === 'ENOENT') {
      return new Set();
    }
    throw error;
  }
};

const toUtf8 = (chunk: Buffer): string => chunk.toString('utf-8');

const WORKSPACE_ROOT = '_runs';
const LOG_FILENAME = 'stdout.log';

const parseFiniteNumber = (value: unknown): number | null => {
  if (typeof value === 'number' && Number.isFinite(value)) {
    return value;
  }
  if (typeof value === 'string') {
    const numeric = Number(value);
    if (Number.isFinite(numeric)) {
      return numeric;
    }
  }
  return null;
};

const readJsonFile = async (filePath: string): Promise<unknown | null> => {
  try {
    const raw = await fs.readFile(filePath, 'utf-8');
    return JSON.parse(raw) as unknown;
  } catch (error) {
    const code = (error as NodeJS.ErrnoException | null)?.code;
    if (code === 'ENOENT') {
      return null;
    }
    console.warn(`[baseline] Failed to read ${filePath}:`, error);
    return null;
  }
};

const normaliseRecord = (payload: unknown): Record<string, unknown> | null => {
  if (!payload || typeof payload !== 'object') {
    return null;
  }
  return payload as Record<string, unknown>;
};

const collectLoopReports = async (artifactsDir: string): Promise<Record<string, unknown>[]> => {
  const records: Record<string, unknown>[] = [];

  const loopReports = await readJsonFile(path.join(artifactsDir, 'loop_reports.json'));
  if (Array.isArray(loopReports)) {
    for (const entry of loopReports) {
      const record = normaliseRecord(entry);
      if (record) {
        records.push(record);
      }
    }
  } else {
    const record = normaliseRecord(loopReports);
    if (record) {
      records.push(record);
    }
  }

  const loopsDir = path.join(artifactsDir, 'loops');
  try {
    const files = await fs.readdir(loopsDir, { withFileTypes: true });
    const jsonFiles = files
      .filter((entry) => entry.isFile() && entry.name.toLowerCase().endsWith('.json'))
      .map((entry) => path.join(loopsDir, entry.name));
    for (const file of jsonFiles) {
      const data = await readJsonFile(file);
      const record = normaliseRecord(data);
      if (record) {
        records.push(record);
      }
    }
  } catch (error) {
    const code = (error as NodeJS.ErrnoException | null)?.code;
    if (code !== 'ENOENT') {
      console.warn(`[baseline] Failed to enumerate loops under ${loopsDir}:`, error);
    }
  }

  return records;
};

const extractLoopMetrics = (records: Record<string, unknown>[]): Record<string, number | null> | null => {
  if (records.length === 0) {
    return null;
  }

  let omegaAbsSum = 0;
  let omegaAbsCount = 0;
  let omegaAbsMax: number | null = null;
  let phiAbsMax: number | null = null;
  let guardHits = 0;
  let guardMin: number | null = null;
  let signFlipCount = 0;
  let trustworthyCount = 0;

  const toRecord = (value: unknown): Record<string, unknown> | null =>
    value && typeof value === 'object' ? (value as Record<string, unknown>) : null;

  for (const record of records) {
    const loop = toRecord(record.loop);
    const orientations = Array.isArray(record.orientations)
      ? (record.orientations as unknown[])
      : [];

    const omegaCandidates: Array<number | null> = [
      parseFiniteNumber(record.omega_abs),
      loop ? parseFiniteNumber(loop.omega_abs) : null,
    ];
    const omegaAbs = omegaCandidates.find((candidate) => candidate !== null) ?? null;
    if (omegaAbs !== null) {
      omegaAbsSum += omegaAbs;
      omegaAbsCount += 1;
      omegaAbsMax = omegaAbsMax === null ? omegaAbs : Math.max(omegaAbsMax, omegaAbs);
    }

    let phiAbs: number | null = parseFiniteNumber(record.phi_abs);
    if (loop) {
      const loopPhi = parseFiniteNumber(loop.phi_abs ?? loop.phi);
      if (loopPhi !== null) {
        phiAbs = phiAbs === null ? Math.abs(loopPhi) : Math.max(phiAbs, Math.abs(loopPhi));
      }
    }
    for (const entry of orientations) {
      const orientation = toRecord(entry);
      if (!orientation) {
        continue;
      }
      const phi = parseFiniteNumber(orientation.phi);
      if (phi !== null) {
        phiAbs = phiAbs === null ? Math.abs(phi) : Math.max(phiAbs, Math.abs(phi));
      }
      if (orientation.fs_guard_exceeded) {
        guardHits += 1;
      }
    }
    if (phiAbs !== null) {
      phiAbsMax = phiAbsMax === null ? phiAbs : Math.max(phiAbsMax, phiAbs);
    }

    const guardCandidates: Array<number | null> = [
      parseFiniteNumber(record.fs_guard),
      loop ? parseFiniteNumber(loop.fs_guard) : null,
    ];
    const guardValue = guardCandidates.find((candidate) => candidate !== null) ?? null;
    if (guardValue !== null) {
      guardMin = guardMin === null ? guardValue : Math.min(guardMin, guardValue);
    }

    const guardFlag = Boolean(
      record.fs_guard_exceeded ||
        record.fs_guard_triggered ||
        (loop && (loop.fs_guard_triggered || loop.fs_guard_exceeded)) ||
        record.status === 'rejected',
    );
    if (guardFlag) {
      guardHits += 1;
    }

    if (loop?.sign_flip_detected) {
      signFlipCount += 1;
    }

    const trusted =
      !guardFlag &&
      ((phiAbs !== null && phiAbs > 0.2) || (omegaAbs !== null && Math.abs(omegaAbs) > 0.2));
    if (trusted) {
      trustworthyCount += 1;
    }
  }

  const metrics: Record<string, number | null> = {
    loop_count: records.length,
  };

  if (omegaAbsCount > 0) {
    metrics.loop_omega_abs_mean = omegaAbsSum / omegaAbsCount;
  }
  if (omegaAbsMax !== null) {
    metrics.loop_omega_abs_max = omegaAbsMax;
  }
  if (phiAbsMax !== null) {
    metrics.loop_phi_abs_max = phiAbsMax;
  }
  if (guardMin !== null) {
    metrics.loop_fs_guard_min = guardMin;
  }
  if (guardHits > 0) {
    metrics.loop_fs_guard_violations = guardHits;
  }
  if (signFlipCount > 0) {
    metrics.loop_sign_flip_count = signFlipCount;
  }
  if (trustworthyCount > 0) {
    metrics.loop_trustworthy_count = trustworthyCount;
    metrics.loop_trustworthy_fraction = trustworthyCount / records.length;
  }

  return metrics;
};

const collectLoopMetrics = async (
  artifactsDir: string | null,
): Promise<Record<string, number | null> | null> => {
  if (!artifactsDir) {
    return null;
  }
  const records = await collectLoopReports(artifactsDir);
  return extractLoopMetrics(records);
};

const writeRunLog = async (artifactsDir: string, runId: string, buffer: Buffer) => {
  const workspaceDir = path.join(artifactsDir, WORKSPACE_ROOT, runId);
  await fs.mkdir(workspaceDir, { recursive: true });
  await fs.writeFile(path.join(workspaceDir, LOG_FILENAME), buffer);
};

export type BaselineRunHooks = {
  onStdout?: (event: { runId: string; chunk: string }) => void;
  onStderr?: (event: { runId: string; chunk: string }) => void;
  onExit?: (event: { runId: string; code: number | null; signal: NodeJS.Signals | null }) => void;
  onError?: (event: { runId: string; error: Error }) => void;
};

export type BaselineRunDependencies = BaselineRunHooks & {
  env: PythonEnvironment;
  artifactsRoot: string;
  spawnFn?: typeof spawn;
  uuidFn?: () => string;
  readRunDirs?: RunDirsReader;
};

export type BaselineRunResult = {
  runId: string;
  model: BaselineModel;
  outputDir: string | null;
  artifactsDir: string;
  command: string;
  args: string[];
  cwd: string;
  cli: string;
  status: 'complete';
  startedAt: number;
  completedAt: number;
  loopMetrics: Record<string, number | null> | null;
};

const toChildProcess = (child: ChildProcessWithoutNullStreams | null) => {
  if (!child) {
    throw new Error('Failed to spawn baseline process.');
  }
  return child;
};

const resolveOutputBase = (planArgs: string[], artifactsRoot: string): string => {
  const flagIndex = planArgs.findIndex((value) => value === '--output-dir');
  if (flagIndex >= 0 && planArgs.length > flagIndex + 1) {
    return planArgs[flagIndex + 1];
  }
  return artifactsRoot;
};

const pickLatestRunDir = (root: string, before: Set<string>, after: Set<string>): string | null => {
  const additions = [...after].filter((entry) => !before.has(entry));
  const candidates = additions.length > 0 ? additions : [...after];
  if (candidates.length === 0) {
    return null;
  }
  candidates.sort((a, b) => a.localeCompare(b));
  const latest = candidates[candidates.length - 1];
  return path.join(root, latest);
};

const BASELINE_RUNS_ROOT = '_baseline_runs';

export const executeBaselineRun = async (
  payload: BaselineRunPayload,
  deps: BaselineRunDependencies,
): Promise<BaselineRunResult> => {
  const { env, artifactsRoot } = deps;
  const spawnImpl = deps.spawnFn ?? spawn;
  const uuid = deps.uuidFn ?? uuidv4;
  const runId = uuid();
  const startedAt = Date.now();

  const runScopedOutputDir =
    payload.outputDir ?? path.join(artifactsRoot, BASELINE_RUNS_ROOT, runId);

  await fs.mkdir(runScopedOutputDir, { recursive: true });

  const options: BaselineCommandOptions = {
    strategy: env.strategy,
    model: payload.model,
    axisMap: payload.axisMap,
    outputDir: runScopedOutputDir,
    steps: payload.steps,
    seed: payload.seed,
    args: payload.args,
  };

  const plan = cmdBaseline(env.executable, options);
  const baseOutput = resolveOutputBase(plan.args, artifactsRoot);
  const readDirs = deps.readRunDirs ?? readRunDirectories;
  const modelRoot = path.join(baseOutput, 'baselines', payload.model);
  const before = await readDirs(modelRoot);

  const envVars: NodeJS.ProcessEnv = {
    ...process.env,
    PYTHONUNBUFFERED: '1',
    PYTHONIOENCODING: 'utf-8',
    CWT_OUTPUT_DIR: baseOutput,
  };
  if (plan.pythonPath) {
    envVars.PYTHONPATH = plan.pythonPath;
  }
  if (payload.env) {
    for (const [key, value] of Object.entries(payload.env)) {
      envVars[key] = value;
    }
  }

  const logChunks: Buffer[] = [];
  let artifactsDir = runScopedOutputDir;

  await new Promise<void>((resolve, reject) => {
    const child = toChildProcess(
      spawnImpl(plan.command, plan.args, {
        cwd: plan.cwd,
        env: envVars,
      }),
    );

    child.stdout.on('data', (chunk: Buffer) => {
      logChunks.push(chunk);
      deps.onStdout?.({ runId, chunk: toUtf8(chunk) });
    });

    child.stderr.on('data', (chunk: Buffer) => {
      logChunks.push(chunk);
      deps.onStderr?.({ runId, chunk: toUtf8(chunk) });
    });

    child.on('error', (error) => {
      deps.onError?.({ runId, error });
      reject(error);
    });

    child.on('close', (code, signal) => {
      deps.onExit?.({ runId, code, signal });
      if (code === 0) {
        resolve();
      } else {
        const error = new Error(`Baseline run exited with code ${code ?? 'unknown'}`);
        deps.onError?.({ runId, error });
        reject(error);
      }
    });
  });

  try {
    const after = await readDirs(modelRoot);
    const outputDir = pickLatestRunDir(modelRoot, before, after);
    const completedAt = Date.now();
    artifactsDir = outputDir ?? runScopedOutputDir;

    const loopMetrics = await collectLoopMetrics(outputDir);

    return {
      runId,
      model: payload.model,
      outputDir,
      artifactsDir,
      command: plan.command,
      args: [...plan.args],
      cwd: plan.cwd,
      cli: plan.cli,
      status: 'complete',
      startedAt,
      completedAt,
      loopMetrics,
    } satisfies BaselineRunResult;
  } finally {
    try {
      await writeRunLog(artifactsDir, runId, Buffer.concat(logChunks));
    } catch (error) {
      console.warn(`[baseline] Failed to persist stdout log for ${runId}:`, error);
    }
  }
};

export { readRunDirectories };
