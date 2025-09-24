import { spawn } from 'node:child_process';
import { promises as fs } from 'node:fs';
import path from 'node:path';

import type { PythonStrategy } from './runner/env';

export type NoiseSweepParams = {
  phaseStd?: number[];
  ampStd?: number[];
  delayStd?: number[];
  numTrials?: number;
  loopSteps?: number;
  gridSize?: number;
  axes?: [string, string];
  outDir: string;
  strategy: PythonStrategy;
};

export type NoiseSweepTrial = {
  seed: number;
  rGamma: number | null;
  overlapAverage: number | null;
  minOverlap: number | null;
  fsSteps: number[];
};

export type NoiseSweepPoint = {
  phaseStd: number;
  ampStd: number;
  delayStd: number;
  signPersistence: number | null;
  overlapMean: number | null;
  coherenceMean: number | null;
  quantized: boolean;
  trials: NoiseSweepTrial[];
  fsP95: number | null;
  fsMax: number | null;
};

export type NoiseSweepGraph = {
  name: string;
  axes: [string, string];
  flux: number | null;
  overlapThreshold: number | null;
  coherenceThreshold: number | null;
  points: NoiseSweepPoint[];
};

export type NoiseSweepResult = {
  stdout: string;
  stderr: string;
  recordsPath: string;
  reportPath: string | null;
  outputDir: string;
  graphs: NoiseSweepGraph[];
};

const repoRoot = path.resolve(__dirname, '..', '..');
const cwtSimRoot = path.join(repoRoot, 'cwt-sim');

const ensureDir = async (dir: string) => {
  await fs.mkdir(dir, { recursive: true });
};

const buildPythonPath = (strategy: PythonStrategy): string | undefined => {
  const entries = new Set<string>();
  const current = process.env.PYTHONPATH ?? '';
  if (current) {
    for (const part of current.split(path.delimiter)) {
      const trimmed = part.trim();
      if (trimmed.length > 0) {
        entries.add(trimmed);
      }
    }
  }

  if (strategy === 'py_path') {
    entries.add(cwtSimRoot);
  }

  const values = Array.from(entries);
  if (values.length === 0) {
    return undefined;
  }
  return values.join(path.delimiter);
};

const appendArgs = (args: string[], flag: string, values: number[] | undefined) => {
  if (!values || values.length === 0) {
    return;
  }
  args.push(flag, ...values.map((value) => value.toString()));
};

const percentile = (values: number[], percentileValue: number): number | null => {
  if (values.length === 0) {
    return null;
  }
  const sorted = [...values].sort((a, b) => a - b);
  const index = (percentileValue / 100) * (sorted.length - 1);
  const lower = Math.floor(index);
  const upper = Math.ceil(index);
  if (lower === upper) {
    return sorted[lower];
  }
  const weight = index - lower;
  return sorted[lower] * (1 - weight) + sorted[upper] * weight;
};

const parseTrial = (input: Record<string, unknown>): NoiseSweepTrial => {
  const fsSteps = Array.isArray(input.fs_steps)
    ? (input.fs_steps as unknown[])
        .map((value) => Number(value))
        .filter((value) => Number.isFinite(value))
    : [];
  return {
    seed: Number(input.seed ?? NaN),
    rGamma: Number.isFinite(Number(input.R_gamma)) ? Number(input.R_gamma) : null,
    overlapAverage: Number.isFinite(Number(input.overlap_avg)) ? Number(input.overlap_avg) : null,
    minOverlap: Number.isFinite(Number(input.min_overlap)) ? Number(input.min_overlap) : null,
    fsSteps,
  };
};

const parsePoint = (input: Record<string, unknown>): NoiseSweepPoint => {
  const trialsRaw = Array.isArray(input.trials) ? (input.trials as Record<string, unknown>[]) : [];
  const trials = trialsRaw.map(parseTrial);
  const fsSamples = trials.flatMap((trial) => trial.fsSteps);
  return {
    phaseStd: Number(input.phase_std ?? 0),
    ampStd: Number(input.amp_std ?? 0),
    delayStd: Number(input.delay_std ?? 0),
    signPersistence: Number.isFinite(Number(input.sign_persistence))
      ? Number(input.sign_persistence)
      : null,
    overlapMean: Number.isFinite(Number(input.overlap_mean)) ? Number(input.overlap_mean) : null,
    coherenceMean: Number.isFinite(Number(input.s_bar_mean)) ? Number(input.s_bar_mean) : null,
    quantized: Boolean(input.quantized),
    trials,
    fsP95: percentile(fsSamples, 95),
    fsMax: fsSamples.length > 0 ? Math.max(...fsSamples) : null,
  };
};

const parseGraph = (input: Record<string, unknown>): NoiseSweepGraph => {
  const pointsRaw = Array.isArray(input.noise_points)
    ? (input.noise_points as Record<string, unknown>[])
    : [];
  return {
    name: String(input.name ?? 'unknown'),
    axes: Array.isArray(input.axes) && input.axes.length === 2
      ? [String(input.axes[0]), String(input.axes[1])]
      : ['tau', 'zeta'],
    flux: Number.isFinite(Number(input.flux)) ? Number(input.flux) : null,
    overlapThreshold: Number.isFinite(Number(input.overlap_threshold))
      ? Number(input.overlap_threshold)
      : null,
    coherenceThreshold: Number.isFinite(Number(input.coherence_threshold))
      ? Number(input.coherence_threshold)
      : null,
    points: pointsRaw.map(parsePoint),
  };
};

export const cmdGateCRobust = async (
  pythonExe: string,
  params: NoiseSweepParams,
): Promise<NoiseSweepResult> => {
  if (!pythonExe) {
    throw new Error('pythonExe is required');
  }
  await ensureDir(params.outDir);

  const args = [
    '-m',
    'experiments.gateC_topology_robust.run',
    '--output-dir',
    params.outDir,
  ];

  if (params.numTrials != null) {
    if (!Number.isInteger(params.numTrials) || params.numTrials <= 0) {
      throw new Error('numTrials must be a positive integer when provided');
    }
    args.push('--num-trials', Math.trunc(params.numTrials).toString());
  }
  if (params.loopSteps != null) {
    if (!Number.isInteger(params.loopSteps) || params.loopSteps <= 0) {
      throw new Error('loopSteps must be a positive integer when provided');
    }
    args.push('--loop-steps', Math.trunc(params.loopSteps).toString());
  }
  if (params.gridSize != null) {
    if (!Number.isInteger(params.gridSize) || params.gridSize <= 0) {
      throw new Error('gridSize must be a positive integer when provided');
    }
    args.push('--grid-size', Math.trunc(params.gridSize).toString());
  }
  if (params.axes && params.axes.length === 2) {
    args.push('--axes', params.axes[0], params.axes[1]);
  }

  appendArgs(args, '--phase-std', params.phaseStd);
  appendArgs(args, '--amp-std', params.ampStd);
  appendArgs(args, '--delay-std', params.delayStd);

  const env: NodeJS.ProcessEnv = {
    ...process.env,
    PYTHONUNBUFFERED: '1',
  };
  const pythonPath = buildPythonPath(params.strategy);
  if (pythonPath) {
    env.PYTHONPATH = pythonPath;
  }

  let stdout = '';
  let stderr = '';

  await new Promise<void>((resolve, reject) => {
    const child = spawn(pythonExe, args, { cwd: cwtSimRoot, env });
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
        const err = new Error(`noise-robust command failed with exit code ${code ?? 'unknown'}`);
        (err as Error & { stdout?: string }).stdout = stdout;
        (err as Error & { stderr?: string }).stderr = stderr;
        reject(err);
      }
    });
  });

  const recordsPath = path.join(params.outDir, 'records.json');
  const reportPath = path.join(params.outDir, 'REPORT.md');
  const content = await fs.readFile(recordsPath, 'utf-8');
  const parsed = JSON.parse(content) as {
    graphs?: Record<string, unknown>[];
    num_trials?: number;
    loop_steps?: number;
  };
  const graphs = Array.isArray(parsed.graphs)
    ? parsed.graphs.map((entry) => parseGraph(entry as Record<string, unknown>))
    : [];
  const numTrials = Number(parsed.num_trials);
  const loopSteps = Number(parsed.loop_steps);

  const stdoutPath = path.join(params.outDir, 'stdout.log');
  const stderrPath = path.join(params.outDir, 'stderr.log');
  await fs.writeFile(stdoutPath, stdout, 'utf-8');
  if (stderr.trim().length > 0) {
    await fs.writeFile(stderrPath, stderr, 'utf-8');
  }

  return {
    stdout,
    stderr,
    recordsPath,
    reportPath: await fs
      .access(reportPath)
      .then(() => reportPath)
      .catch(() => null),
    outputDir: params.outDir,
    graphs,
    numTrials: Number.isFinite(numTrials) ? numTrials : undefined,
    loopSteps: Number.isFinite(loopSteps) ? loopSteps : undefined,
  };
};

export default cmdGateCRobust;
