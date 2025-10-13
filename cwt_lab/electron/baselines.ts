import path from 'node:path';

import type { PythonStrategy } from './runner/env';
import { formatCli, planModuleInvocation } from './runner/pythonInvoker';
import { cwtSimRoot, repoRoot } from './paths';

const MODEL_MODULES = {
  ising: 'baselines.ising.run',
  kuramoto: 'baselines.kuramoto.run',
  percolation: 'baselines.percolation.run',
  sis: 'baselines.sis.run',
} as const;

export type BaselineModel = keyof typeof MODEL_MODULES;

export type BaselineCommandOptions = {
  strategy: PythonStrategy;
  model: BaselineModel;
  axisMap?: string | null;
  outputDir?: string | null;
  steps?: number | string | null;
  seed?: number | string | null;
  args?: Array<string | number> | null;
};

export type BaselineInvocationPlan = {
  command: string;
  args: string[];
  cwd: string;
  pythonPath: string | null;
  cli: string;
};

const ensureNonEmptyString = (value: unknown): string | null => {
  if (value == null) {
    return null;
  }
  const stringValue = String(value).trim();
  return stringValue.length > 0 ? stringValue : null;
};

const toIntegerString = (value: unknown, label: string): string | null => {
  if (value == null || value === '') {
    return null;
  }

  const numeric = typeof value === 'number' ? value : Number(value);
  if (!Number.isFinite(numeric)) {
    throw new Error(`${label} must be numeric.`);
  }
  if (!Number.isInteger(numeric)) {
    throw new Error(`${label} must be an integer.`);
  }
  return Math.trunc(numeric).toString();
};

const normalisePath = (value: unknown): string | null => {
  const candidate = ensureNonEmptyString(value);
  if (!candidate) {
    return null;
  }
  return path.resolve(candidate);
};

export const cmdBaseline = (
  pythonExe: string,
  options: BaselineCommandOptions,
): BaselineInvocationPlan => {
  if (!pythonExe || pythonExe.trim().length === 0) {
    throw new Error('pythonExe is required');
  }

  const moduleName = MODEL_MODULES[options.model];
  if (!moduleName) {
    throw new Error(`Unsupported baseline model: ${options.model}`);
  }

  const moduleArgs: string[] = [];
  const axisMap = normalisePath(options.axisMap);
  if (axisMap) {
    moduleArgs.push('--axis-map', axisMap);
  }
  const outputDir = normalisePath(options.outputDir);
  if (outputDir) {
    moduleArgs.push('--output-dir', outputDir);
  }
  const steps = toIntegerString(options.steps, 'steps');
  if (steps) {
    moduleArgs.push('--steps', steps);
  }
  const seed = toIntegerString(options.seed, 'seed');
  if (seed) {
    moduleArgs.push('--seed', seed);
  }

  if (options.args) {
    const extras = options.args.filter((value) => value != null).map((value) => String(value));
    moduleArgs.push(...extras);
  }

  const pythonPathEntries = [repoRoot, cwtSimRoot];

  const invocation = planModuleInvocation({
    pythonExe,
    strategy: options.strategy,
    repoRoot,
    moduleName,
    args: moduleArgs,
    pythonPathEntries,
  });

  const cwd = repoRoot;
  const command = invocation.command;
  const args = [...invocation.args];
  const pythonPath =
    invocation.pythonPath ?? pythonPathEntries.filter(Boolean).join(path.delimiter);
  const cli = formatCli({ command, args, cwd, pythonPath });

  return {
    command,
    args,
    cwd,
    pythonPath,
    cli,
  } satisfies BaselineInvocationPlan;
};

export { MODEL_MODULES };
