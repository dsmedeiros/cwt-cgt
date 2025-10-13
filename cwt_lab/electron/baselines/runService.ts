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

export const baselineRunPayloadSchema = z
  .object({
    model: z.enum(['ising', 'kuramoto', 'percolation', 'sis']),
    axisMap: optionalPathSchema,
    outputDir: optionalPathSchema,
    steps: optionalNumericSchema,
    seed: optionalNumericSchema,
    args: argsSchema,
  })
  .transform((value) => ({
    model: value.model as BaselineModel,
    axisMap: value.axisMap,
    outputDir: value.outputDir,
    steps: value.steps,
    seed: value.seed,
    args: value.args,
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
  command: string;
  args: string[];
  cli: string;
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

export const executeBaselineRun = async (
  payload: BaselineRunPayload,
  deps: BaselineRunDependencies,
): Promise<BaselineRunResult> => {
  const { env, artifactsRoot } = deps;
  const spawnImpl = deps.spawnFn ?? spawn;
  const uuid = deps.uuidFn ?? uuidv4;
  const runId = uuid();

  const options: BaselineCommandOptions = {
    strategy: env.strategy,
    model: payload.model,
    axisMap: payload.axisMap,
    outputDir: payload.outputDir,
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

  await new Promise<void>((resolve, reject) => {
    const child = toChildProcess(
      spawnImpl(plan.command, plan.args, {
        cwd: plan.cwd,
        env: envVars,
      }),
    );

    child.stdout.on('data', (chunk: Buffer) => {
      deps.onStdout?.({ runId, chunk: toUtf8(chunk) });
    });

    child.stderr.on('data', (chunk: Buffer) => {
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

  const after = await readDirs(modelRoot);
  const outputDir = pickLatestRunDir(modelRoot, before, after);

  return {
    runId,
    model: payload.model,
    outputDir,
    command: plan.command,
    args: [...plan.args],
    cli: plan.cli,
  } satisfies BaselineRunResult;
};

export { readRunDirectories };
