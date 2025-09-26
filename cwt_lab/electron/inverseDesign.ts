import { spawn } from 'node:child_process';
import { promises as fs } from 'node:fs';
import path from 'node:path';

import type { PythonStrategy } from './runner/env';
import { planModuleInvocation } from './runner/pythonInvoker';

export type InverseDesignParams = {
  axes: [string, string];
  center: [number, number];
  extentPair: [number, number];
  budgetSteps?: number;
  maxFs?: number;
  targetIndex?: number;
  outDir: string;
  strategy: PythonStrategy;
};

export type InverseDesignControlPoint = {
  index: number;
  axisA: number;
  axisB: number;
};

export type InverseDesignPathSummary = {
  magnitude: number | null;
  guardFraction: number | null;
  length: number | null;
  phiMissing: boolean;
};

export type InverseDesignOptimisedSummary = InverseDesignPathSummary & {
  improvement: number | null;
  controlPoints: InverseDesignControlPoint[];
};

export type InverseDesignResult = {
  stdout: string;
  stderr: string;
  outputDir: string;
  command: string;
  args: string[];
  cli: string;
  baseline: InverseDesignPathSummary | null;
  optimised: InverseDesignOptimisedSummary | null;
  acceptance: string | null;
};

const repoRoot = path.resolve(__dirname, '..', '..');
const cwtSimRoot = path.join(repoRoot, 'cwt-sim');

const ensureDir = async (dir: string) => {
  await fs.mkdir(dir, { recursive: true });
};

const parseScalar = (value: string | undefined): number | null => {
  if (!value) {
    return null;
  }
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric : null;
};

const parseBaseline = (stdout: string): InverseDesignPathSummary | null => {
  const baselineRegex = /Baseline rectangle:[\s\S]*?\|R\|=([^\s]+)\s+guard_fraction=([^\s]+)\s+length=([^\s]+)/;
  const missingRegex = /Baseline rectangle:[\s\S]*?Missing curvature tiles/;
  const match = stdout.match(baselineRegex);
  if (!match) {
    return null;
  }
  return {
    magnitude: parseScalar(match[1]),
    guardFraction: parseScalar(match[2]),
    length: parseScalar(match[3]),
    phiMissing: missingRegex.test(stdout),
  };
};

const parseControlPoints = (stdout: string): InverseDesignControlPoint[] => {
  const controlRegex = /v(\d+):\s+Δ[^=]+=([^,]+),\s+Δ[^=]+=([^\s]+)/g;
  const points: InverseDesignControlPoint[] = [];
  let result: RegExpExecArray | null;
  while ((result = controlRegex.exec(stdout)) !== null) {
    const index = Number.parseInt(result[1], 10);
    const axisA = parseScalar(result[2]) ?? 0;
    const axisB = parseScalar(result[3]) ?? 0;
    points.push({ index, axisA, axisB });
  }
  points.sort((a, b) => a.index - b.index);
  return points;
};

const parseOptimised = (stdout: string): InverseDesignOptimisedSummary | null => {
  const optRegex = /Optimised control polygon:[\s\S]*?\|R\|=([^\s]+)\s+guard_fraction=([^\s]+)\s+length=([^\s]+)\s+improvement=([^\s]+)x/;
  const missingRegex = /Optimised control polygon:[\s\S]*?Missing curvature tiles/;
  const match = stdout.match(optRegex);
  if (!match) {
    return null;
  }

  return {
    magnitude: parseScalar(match[1]),
    guardFraction: parseScalar(match[2]),
    length: parseScalar(match[3]),
    improvement: parseScalar(match[4]),
    phiMissing: missingRegex.test(stdout),
    controlPoints: parseControlPoints(stdout),
  };
};

export const cmdInverseDesign = async (
  pythonExe: string,
  params: InverseDesignParams,
): Promise<InverseDesignResult> => {
  const { axes, center, extentPair, budgetSteps, maxFs, targetIndex, outDir, strategy } = params;

  if (!pythonExe) {
    throw new Error('pythonExe is required');
  }
  if (!Array.isArray(axes) || axes.length !== 2) {
    throw new Error('axes must contain exactly two entries');
  }
  if (!Array.isArray(center) || center.length !== 2) {
    throw new Error('center must contain exactly two numeric entries');
  }
  if (!Array.isArray(extentPair) || extentPair.length !== 2) {
    throw new Error('extentPair must contain exactly two numeric entries');
  }

  await ensureDir(outDir);

  const moduleArgs = [
    '--axes',
    axes[0],
    axes[1],
    '--center',
    center[0].toString(),
    center[1].toString(),
    '--extent',
    Math.abs(extentPair[0]).toString(),
    Math.abs(extentPair[1]).toString(),
  ];

  if (budgetSteps != null) {
    if (!Number.isInteger(budgetSteps) || budgetSteps <= 0) {
      throw new Error('budgetSteps must be a positive integer when provided');
    }
    moduleArgs.push('--budget-steps', Math.trunc(budgetSteps).toString());
  }
  if (maxFs != null) {
    if (!Number.isFinite(maxFs) || maxFs <= 0) {
      throw new Error('maxFs must be a positive number when provided');
    }
    moduleArgs.push('--max-fs', maxFs.toString());
  }
  if (targetIndex != null) {
    if (!Number.isInteger(targetIndex)) {
      throw new Error('targetIndex must be an integer when provided');
    }
    moduleArgs.push('--target-index', Math.trunc(targetIndex).toString());
  }

  const env: NodeJS.ProcessEnv = {
    ...process.env,
    PYTHONUNBUFFERED: '1',
    PYTHONIOENCODING: 'utf-8',
  };

  const invocation = planModuleInvocation({
    pythonExe,
    strategy,
    repoRoot,
    moduleName: 'experiments.inverse_design.run',
    args: moduleArgs,
    pythonPathEntries: [cwtSimRoot],
  });

  if (invocation.pythonPath) {
    env.PYTHONPATH = invocation.pythonPath;
  }

  let stdout = '';
  let stderr = '';

  await new Promise<void>((resolve, reject) => {
    const child = spawn(invocation.command, invocation.args, { cwd: invocation.cwd, env });
    child.stdout.on('data', (chunk: Buffer) => {
      stdout += chunk.toString('utf-8');
    });
    child.stderr.on('data', (chunk: Buffer) => {
      stderr += chunk.toString('utf-8');
    });
    child.on('error', (error) => reject(error));
    child.on('close', (code) => {
      if (code === 0) {
        resolve();
      } else {
        const err = new Error(`inverse-design command failed with exit code ${code ?? 'unknown'}`);
        (err as Error & { stdout?: string }).stdout = stdout;
        (err as Error & { stderr?: string }).stderr = stderr;
        reject(err);
      }
    });
  });

  const stdoutPath = path.join(outDir, 'stdout.log');
  const stderrPath = path.join(outDir, 'stderr.log');
  await fs.writeFile(stdoutPath, stdout, 'utf-8');
  if (stderr.trim().length > 0) {
    await fs.writeFile(stderrPath, stderr, 'utf-8');
  }

  const baseline = parseBaseline(stdout);
  const optimised = parseOptimised(stdout);
  const acceptanceMatch = stdout.match(/(Acceptance criterion met:[^\n]+|Warning:[^\n]+)/);

  return {
    stdout,
    stderr,
    outputDir: outDir,
    command: invocation.command,
    args: invocation.args,
    cli: invocation.cli,
    baseline,
    optimised,
    acceptance: acceptanceMatch ? acceptanceMatch[1].trim() : null,
  };
};

export default cmdInverseDesign;
